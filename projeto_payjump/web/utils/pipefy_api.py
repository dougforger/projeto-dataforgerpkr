import requests

PIPEFY_TOKEN = 'eyJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJQaXBlZnkiLCJpYXQiOjE3NzE1MTU2MzQsImp0aSI6ImExZTQxNjY3LTlmNGQtNGU0Ny1hZWM4LWNhYmFhYTBjNzI0OCIsInN1YiI6MzAyMjM1NzMwLCJ1c2VyIjp7ImlkIjozMDIyMzU3MzAsImVtYWlsIjoiZG91Z2xhcy5mZXJyZWlyYUBzdXByZW1hLmdyb3VwIn0sInVzZXJfdHlwZSI6ImF1dGhlbnRpY2F0ZWQifQ.wXLsgrlHDT37xUooO-E7Zi2d1hu_kjzNqdvNDXGYCTppBZVHa5Tl5PUHf7nv8jK300zsZQBT5yYBnJ9zzvaCXA'
PIPEFY_API_URL = 'https://api.pipefy.com/graphql'

_HEADERS = {
    'Authorization': f'Bearer {PIPEFY_TOKEN}',
    'Content-Type': 'application/json',
}


def testar_conexao() -> dict:
    """Testa a conexão com a API do Pipefy retornando os dados do usuário autenticado.

    Returns:
        dict com 'id', 'name' e 'email' do usuário.

    Raises:
        RuntimeError: se a resposta contiver erros GraphQL ou a requisição falhar.
    """
    query = '{ me { id name email } }'
    resposta = requests.post(PIPEFY_API_URL, json={'query': query}, headers=_HEADERS, timeout=15)
    resposta.raise_for_status()
    dados = resposta.json()
    if 'errors' in dados:
        mensagens = '; '.join(e.get('message', str(e)) for e in dados['errors'])
        raise RuntimeError(mensagens)
    return dados['data']['me']
