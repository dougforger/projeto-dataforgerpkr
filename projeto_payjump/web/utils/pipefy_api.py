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


def buscar_opcoes_campos(pipe_id: int) -> dict:
    """Retorna dict {field_id: [opcoes]} para campos select do start_form.

    Campos de fase (PhaseField) não suportam inline fragments por tipo na API
    do Pipefy, então apenas start_form_fields são consultados dinamicamente.
    """
    query = """
    query($pipe_id: ID!) {
      pipe(id: $pipe_id) {
        start_form_fields {
          id
          ... on SelectField { options }
        }
      }
    }
    """
    pipe = _post(query, {'pipe_id': pipe_id})['pipe']

    opcoes = {}
    for campo in pipe['start_form_fields']:
        if 'options' in campo:
            opcoes[campo['id']] = campo['options']
    return opcoes
