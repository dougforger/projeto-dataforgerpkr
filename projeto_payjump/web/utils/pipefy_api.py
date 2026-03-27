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
    r = requests.post(PIPEFY_API_URL, json=payload, headers=_HEADERS, timeout=15)
    r.raise_for_status()
    dados = r.json()
    if 'errors' in dados:
        msgs = '; '.join(e.get('message', str(e)) for e in dados['errors'])
        raise RuntimeError(msgs)
    return dados['data']


def testar_conexao() -> dict:
    """Retorna id, name e email do usuário autenticado."""
    return _post('{ me { id name email } }')['me']


def buscar_todos_os_cards(pipe_id: int = PIPE_ID) -> pd.DataFrame:
    """Busca todos os cards do pipe via paginação cursor-based.

    Returns:
        DataFrame com colunas: id, criado_em (date), categoria, tipo, resultado, analista.
    """
    _CAMPOS = {
        'categoria_category',
        'tipo_de_ocorr_ncia',
        'resultado_da_an_lise',
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
    registros = []
    cursor = None
    while True:
        dados = _post(query, {'pipe_id': str(pipe_id), 'cursor': cursor})
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
                'tipo': campos.get('tipo_de_ocorr_ncia'),
                'resultado': campos.get('resultado_da_an_lise'),
                'analista': campos.get('respons_vel_pela_an_lise'),
            })
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
    return df


