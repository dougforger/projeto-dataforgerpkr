import json
import time

import pandas as pd
import requests

PIPEFY_TOKEN = 'eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJQaXBlZnkiLCJpYXQiOjE3NzE1MTU2MzQsImp0aSI6ImExZTQxNjY3LTlmNGQtNGU0Ny1hZWM4LWNhYmFhYTBjNzI0OCIsInN1YiI6MzAyMjM1NzMwLCJ1c2VyIjp7ImlkIjozMDIyMzU3MzAsImVtYWlsIjoiZG91Z2xhcy5mZXJyZWlyYUBzdXByZW1hLmdyb3VwIn0sInVzZXJfdHlwZSI6ImF1dGhlbnRpY2F0ZWQifQ.wXLsgrlHDT37xUooO-E7Zi2d1hu_kjzNqdvNDXGYCTppBZVHa5Tl5PUHf7nv8jK300zsZQBT5yYBnJ9zzvaCXA'
PIPEFY_API_URL = 'https://api.pipefy.com/graphql'
PIPE_ID = 301867388  # Security PKR

_HEADERS = {
    'Authorization': f'Bearer {PIPEFY_TOKEN}',
    'Content-Type': 'application/json',
}


def _post(query: str, variables: dict | None = None) -> dict:
    payload = {'query': query}
    if variables:
        payload['variables'] = variables
    r = requests.post(PIPEFY_API_URL, json=payload, headers=_HEADERS, timeout=60)
    r.raise_for_status()
    dados = r.json()
    if 'errors' in dados:
        msgs = '; '.join(e.get('message', str(e)) for e in dados['errors'])
        raise RuntimeError(msgs)
    return dados['data']


def _parse_tipo(valor: str | None) -> str:
    """investiga_o_interna (checklist_vertical): '["Sim"]' ou '[]' → interno; None → denúncia."""
    if not valor:
        return 'Denúncia'
    if '"Sim"' in valor or valor.strip() == '[]':
        return 'Investigação interna'
    return 'Denúncia'


def _parse_analista(valor: str | None) -> str | None:
    """respons_vel_pela_an_lise chega como '["Nome"]' — extrai o primeiro elemento."""
    if not valor:
        return None
    try:
        parsed = json.loads(valor)
        if isinstance(parsed, list) and parsed:
            return parsed[0]
    except (json.JSONDecodeError, ValueError):
        pass
    return valor


def testar_conexao() -> dict:
    """Retorna id, name e email do usuário autenticado."""
    return _post('{ me { id name email } }')['me']


def buscar_contagem_cards(pipe_id: int = PIPE_ID) -> int:
    """Retorna o total de cards no pipe (usado para a barra de progresso)."""
    dados = _post(
        'query($id: ID!) { pipe(id: $id) { cards_count } }',
        {'id': str(pipe_id)},
    )
    return dados['pipe']['cards_count']


def buscar_todos_os_cards(pipe_id: int = PIPE_ID, on_progress=None) -> pd.DataFrame:
    """Busca todos os cards do pipe via paginação cursor-based.

    Returns:
        DataFrame com colunas: id, criado_em (date), categoria, tipo, resultado, analista.
    """
    _CAMPOS = {
        'categoria_category',
        'investiga_o_interna',
        'status_final',
        'respons_vel_pela_an_lise',
    }
    query = """
    query($pipe_id: ID!, $cursor: String) {
      cards(pipe_id: $pipe_id, first: 50, after: $cursor) {
        pageInfo { hasNextPage endCursor }
        edges {
          node {
            id
            createdAt
            fields {
              field { id }
              value
            }
          }
        }
      }
    }
    """
    _MAX_TENTATIVAS = 3

    registros = []
    cursor = None
    while True:
        for tentativa in range(_MAX_TENTATIVAS):
            try:
                dados = _post(query, {'pipe_id': str(pipe_id), 'cursor': cursor})
                break
            except Exception:
                if tentativa < _MAX_TENTATIVAS - 1:
                    time.sleep(2 * (tentativa + 1))
                else:
                    raise
        pagina = dados['cards']
        for edge in pagina['edges']:
            no = edge['node']
            campos = {
                f['field']['id']: f['value']
                for f in no['fields']
                if f['field']['id'] in _CAMPOS
            }
            registros.append({
                'id': no['id'],
                'criado_em': no['createdAt'],
                'categoria': campos.get('categoria_category'),
                'tipo': _parse_tipo(campos.get('investiga_o_interna')),
                'resultado': campos.get('status_final') or None,
                'analista': _parse_analista(campos.get('respons_vel_pela_an_lise')),
            })
        if on_progress:
            on_progress(len(registros))
        if not pagina['pageInfo']['hasNextPage']:
            break
        cursor = pagina['pageInfo']['endCursor']

    df = pd.DataFrame(registros) if registros else pd.DataFrame(
        columns=['id', 'criado_em', 'categoria', 'tipo', 'resultado', 'analista']
    )
    if not df.empty:
        df['criado_em'] = (
            pd.to_datetime(df['criado_em'], utc=True)
            .dt.tz_convert('America/Sao_Paulo')
            .dt.date
        )
        # Cards sem status_final: internos → Positivo, denúncias → Negativo
        mask_sem = df['resultado'].isna()
        df.loc[mask_sem & (df['tipo'] == 'Investigação interna'), 'resultado'] = 'Positivo'
        df.loc[mask_sem & (df['tipo'] != 'Investigação interna'), 'resultado'] = 'Negativo'
    return df


