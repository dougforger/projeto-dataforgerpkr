CABECALHOS = {
    'português': (
        '*Notificação Security PKR*\n\n'
        'Protocolo: *#{protocolo}*\n'
        'Clube: *{nome_clube} ({id_clube})*\n'
        'Liga: *{nome_liga} ({id_liga})*\n'
        'Data: *{data}*\n\n'
    ),
    'inglês': (
        '*Notification Security PKR*\n\n'
        'Protocol: *#{protocolo}*\n'
        'Club: *{nome_clube} ({id_clube})*\n'
        'Union: *{nome_liga} ({id_liga})*\n'
        'Date: *{data}*\n\n'
    ),
    'espanhol': (
        '*Notificación Security PKR*\n\n'
        'Protocolo: *#{protocolo}*\n'
        'Clube: *{nome_clube} ({id_clube})*\n'
        'Liga: *{nome_liga} ({id_liga})*\n'
        'Fecha: *{data}*\n\n'
    )
}

RODAPES = {
    'português': '\n\n*Security PKR*',
    'inglês': '\n\n*Security PKR*',
    'espanhol': '\n\n*Security PKR*'
}

# ──────────────────────────────────────────────────────────────
# MODELOS DE NOTIFICAÇÃO
# 
# Cada template tem:
#   - categoria:  texto exibido no selectbox
#   - campos: lista de campos dinâmicos que o usuário preenche
#       cada campo tem: key, label, tipo ('text' | 'number' | 'textarea')
#   - corpo:  dicionário com o texto por idioma (use {key} para os campos)
#
# Exemplo de como adicionar um template:
#
# {
#     'categoria': 'Suspensão de Chat',
#     'campos': [
#         {'key': 'jogador', 'label': 'Jogador (usuário + ID)', 'tipo': 'text'},
#         {'key': 'motivo',  'label': 'Motivo',                 'tipo': 'text'},
#         {'key': 'dias',    'label': 'Duração (dias)',         'tipo': 'number'},
#     ],
#     'corpo': {
#         'português': 'Foi identificada violação... jogador {jogador}... por {dias} dias.',
#         'inglês':    'A violation was identified... player {jogador}... for {dias} days.',
#         'espanhol':  'Se identificó una violación... jugador {jogador}... por {dias} días.',
#     }
# },
#
# ──────────────────────────────────────────────────────────────

MODELOS = [
    # Adicione os modelos aqui
]

def montar_cabecalho(idioma: str, protocolo: int, nome_clube: str, id_clube: int, nome_liga: str, id_liga: int, data: str) -> str:
    if idioma not in CABECALHOS:
        raise ValueError(f'⚠️ Idioma {idioma} não suportado! Idiomas disponíveis: {list(CABECALHOS.keys())}')
    
    modelo = CABECALHOS[idioma]
    modelo_formatado = modelo.format(
        protocolo = protocolo,
        nome_clube = nome_clube,
        id_clube = id_clube,
        nome_liga = nome_liga,
        id_liga = id_liga,
        data = data
    )
    return modelo_formatado

def montar_rodape(idioma) -> str:
    return RODAPES.get(idioma, '\n\n*Security PKR*')

def montar_notificacao(idioma, cabecalho, modelo, campos_preenchidos) -> str:
    '''
    Monta a mensagem completa para notificação: cabeçalho + corpo + rodapé

    :param idioma:              idioma do clube.
    :param cabecalho:           string já montada por montar_cabecalho().
    :param modelo:              dict do modelo selecionado.
    :param campos_preenchidos:  dict {key: valor} com os campos dinâmicos.
    '''
    
    corpo = modelo['corpo'].get(idioma, modelo['corpo'].get('português', ''))
    corpo_formatado = corpo.format(**campos_preenchidos)
    rodape = montar_rodape(idioma)

    return f'{cabecalho}{corpo_formatado}{rodape}'