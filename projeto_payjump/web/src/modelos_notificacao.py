# ──────────────────────────────────────────────────────────────────────────────
# CABEÇALHOS
#
# Três variantes de título:
#   'notificacao' → *Notificação / Security PKR Notification / Notificación*
#   'comunicado'  → *Comunicado / Security PKR Notice / Aviso*
#   'aliciamento' → *Aliciamento - Suprema Poker* (uso exclusivo para casos de rakeback)
#
# CABECALHOS (sem tipo) é a variante 'notificacao' — mantida para compatibilidade
# com o import direto que a página já faz.
# ──────────────────────────────────────────────────────────────────────────────

CABECALHOS = {
    'português': (
        '*Notificação Security PKR*\n\n'
        'Protocolo: *#{protocolo}*\n'
        'Clube: *{nome_clube} ({id_clube})*\n'
        'Liga: *{nome_liga} ({id_liga})*\n'
        'Data: *{data}*\n\n'
    ),
    'inglês': (
        '*Security PKR Notification*\n\n'
        'Protocol: *#{protocolo}*\n'
        'Club: *{nome_clube} ({id_clube})*\n'
        'Union: *{nome_liga} ({id_liga})*\n'
        'Date: *{data}*\n\n'
    ),
    'espanhol': (
        '*Notificación Security PKR*\n\n'
        'Protocolo: *#{protocolo}*\n'
        'Club: *{nome_clube} ({id_clube})*\n'
        'Unión: *{nome_liga} ({id_liga})*\n'
        'Fecha: *{data}*\n\n'
    ),
}

CABECALHOS_COMUNICADO = {
    'português': (
        '*Comunicado Security PKR*\n\n'
        'Protocolo: *#{protocolo}*\n'
        'Clube: *{nome_clube} ({id_clube})*\n'
        'Liga: *{nome_liga} ({id_liga})*\n'
        'Data: *{data}*\n\n'
    ),
    'inglês': (
        '*Security PKR Notice*\n\n'
        'Protocol: *#{protocolo}*\n'
        'Club: *{nome_clube} ({id_clube})*\n'
        'Union: *{nome_liga} ({id_liga})*\n'
        'Date: *{data}*\n\n'
    ),
    'espanhol': (
        '*Aviso de Security PKR*\n\n'
        'Protocolo: *#{protocolo}*\n'
        'Club: *{nome_clube} ({id_clube})*\n'
        'Unión: *{nome_liga} ({id_liga})*\n'
        'Fecha: *{data}*\n\n'
    ),
}

CABECALHOS_ALICIAMENTO = {
    'português': (
        '*Aliciamento - Suprema Poker*\n\n'
        'Protocolo: *#{protocolo}*\n'
        'Clube: *{nome_clube} ({id_clube})*\n'
        'Liga: *{nome_liga} ({id_liga})*\n'
        'Data: *{data}*\n\n'
    ),
    'inglês': (
        '*Enticement - Suprema Poker*\n\n'
        'Protocol: *#{protocolo}*\n'
        'Club: *{nome_clube} ({id_clube})*\n'
        'Union: *{nome_liga} ({id_liga})*\n'
        'Date: *{data}*\n\n'
    ),
    'espanhol': (
        '*Incitación - Suprema Poker*\n\n'
        'Protocolo: *#{protocolo}*\n'
        'Club: *{nome_clube} ({id_clube})*\n'
        'Unión: *{nome_liga} ({id_liga})*\n'
        'Fecha: *{data}*\n\n'
    ),
}

_CABECALHOS_MAP = {
    'notificacao': CABECALHOS,
    'comunicado':  CABECALHOS_COMUNICADO,
    'aliciamento': CABECALHOS_ALICIAMENTO,
}

# ──────────────────────────────────────────────────────────────────────────────
# RODAPÉS
#
# 'notificacao' / 'comunicado' → Atenciosamente / Regards / Saludos + Security PKR
# 'aliciamento'                → Atenciosamente + Suprema Poker
# 'simples'                    → apenas *Security PKR* (sem saudação — ex: Abuso de Chat)
# ──────────────────────────────────────────────────────────────────────────────

RODAPES = {
    'português': '\n\nAtenciosamente,\n\n*Security PKR*',
    'inglês':    '\n\nRegards,\n\n*Security PKR*',
    'espanhol':  '\n\nSaludos,\n\n*Security PKR*',
}

RODAPES_ALICIAMENTO = {
    'português': '\n\nAtenciosamente,\n\n*Suprema Poker*',
    'inglês':    '\n\nRegards,\n\n*Suprema Poker*',
    'espanhol':  '\n\nSaludos,\n\n*Suprema Poker*',
}

RODAPES_SIMPLES = {
    'português': '\n\n*Security PKR*',
    'inglês':    '\n\n*Security PKR*',
    'espanhol':  '\n\n*Security PKR*',
}

_RODAPES_MAP = {
    'notificacao': RODAPES,
    'comunicado':  RODAPES,
    'aliciamento': RODAPES_ALICIAMENTO,
    'simples':     RODAPES_SIMPLES,
}

# ──────────────────────────────────────────────────────────────────────────────
# MODELOS DE NOTIFICAÇÃO
#
# Cada modelo tem:
#   categoria        texto exibido no selectbox
#   campos           lista de campos dinâmicos que o usuário preenche
#                      cada campo: key, label, tipo ('text' | 'number' | 'textarea')
#   corpo            dict {idioma: texto} — use {key} para substituições
#   tipo_cabecalho   (opcional) 'notificacao' (padrão) | 'comunicado' | 'aliciamento'
#   tipo_rodape      (opcional) herda tipo_cabecalho por padrão; use 'simples' para
#                      suprimir a saudação (Atenciosamente/Regards/Saludos)
#   sem_cabecalho    (opcional) True → monta apenas o corpo, sem cabeçalho e rodapé
#                      (ex: "ID sem Restrição", "Ressarcimento SX")
#
# Campos base disponíveis em todos os corpos via dados_base (não precisam ser
# declarados em 'campos'):
#   {protocolo}, {nome_clube}, {id_clube}, {nome_liga}, {id_liga}, {data}
# ──────────────────────────────────────────────────────────────────────────────

MODELOS = [

    # ── CHIP DUMPING ──────────────────────────────────────────────────────────

    {
        'categoria': 'Chip Dumping - Abertura de Investigação',
        'campos': [
            {'key': 'contas', 'label': 'Contas envolvidas (um ID por linha)', 'tipo': 'textarea'},
        ],
        'corpo': {
            'português': (
                'Foi identificada a prática de _chip dumping_ envolvendo as contas abaixo:\n\n'
                '{contas}\n\n'
                'Solicitamos que as fichas fiquem congeladas até a finalização do caso e, também que '
                '*não seja(m) feito(s) nenhum envio, saque ou pagamento para os jogadores em questão*.'
            ),
            'inglês': (
                'The practice of _chip dumping_ involving the following accounts has been identified:\n\n'
                '{contas}\n\n'
                'We request that the chips remain frozen until the case is finalized and also that '
                '*no remittance, withdrawal or payment is made to the players in question*.'
            ),
            'espanhol': (
                'Se ha identificado la práctica de _chip dumping_ que implica a las siguientes cuentas:\n\n'
                '{contas}\n\n'
                'Solicitamos que las fichas sean congeladas hasta que el caso finalice y también que '
                '*no se realicen remesas, retiros o pagos a los jugadores en cuestión*.'
            ),
        },
    },

    {
        'categoria': 'Chip Dumping - Laudo Positivo',
        'campos': [],
        'corpo': {
            'português': (
                'Foi identificada a prática de _chip dumping_ envolvendo contas de seu clube. '
                'Os detalhes da investigação se encontram no laudo em anexo.'
            ),
            'inglês': (
                "The practice of _chip dumping_ involving your club's accounts has been identified. "
                'Details of the investigation can be found in the attached report.'
            ),
            'espanhol': (
                'Se identificó la práctica de _chip dumping_ en las cuentas de su club. '
                'Los detalles de la investigación se encuentran en el informe adjunto.'
            ),
        },
    },

    {
        'categoria': 'Chip Dumping - Análise Negativa',
        'campos': [
            {'key': 'nick_id', 'label': 'Nick e ID do jogador  ex: JohnDoe (123456)', 'tipo': 'text'},
        ],
        'corpo': {
            'português': (
                'Informamos que a investigação realizada com o protocolo acima foi finalizada. '
                'O resultado da análise foi *NEGATIVO*. '
                'O jogador *{nick_id}* teve seu acesso reestabelecido e qualquer saldo que possa '
                'ter sido removido da conta foi restituído, dessa forma o jogador pode continuar '
                'normalmente com suas atividades nas mesas da plataforma da Suprema.'
            ),
            'espanhol': (
                'Informamos de que la investigación relacionada con el protocolo ha finalizado. '
                'El resultado del análisis fue *NEGATIVO*, por lo que no fue necesario tomar ninguna '
                'otra medida. El jugador *{nick_id}* tiene su acceso restablecido y puede continuar '
                'sus actividades normalmente en las mesas de la plataforma Suprema APP.'
            ),
        },
    },

    # ── MTT ───────────────────────────────────────────────────────────────────

    {
        'categoria': 'MTT - Protocolo Positivo',
        'campos': [
            {'key': 'evento', 'label': 'ID / Nome do Evento', 'tipo': 'text'},
        ],
        'corpo': {
            'português': (
                'Informamos que a investigação vinculada ao protocolo indicado, do Evento *{evento}*, foi concluída.\n\n'
                'O resultado da análise foi *POSITIVO*, determinando o banimento definitivo dos IDs '
                'relatados na denúncia em anexo, por violação das Regras da Comunidade e Termos de '
                'Serviço do App Suprema (Softplay/Conluio), com retenção dos ganhos no evento em '
                'questão, conforme laudo.'
            ),
            'inglês': (
                'Please be advised that the investigation linked to the indicated protocol, '
                'for Event *{evento}*, has been concluded.\n\n'
                'The result of the analysis was *POSITIVE*, determining the definitive ban of the '
                'IDs reported in the attached report, for violation of the Community Rules and Terms '
                'of Service of App Suprema (Softplay/Collusion), with retention of the winnings in '
                'the event in question, according to the report.'
            ),
            'espanhol': (
                'Le informamos que la investigación vinculada al protocolo del Evento *{evento}*, ha finalizado.\n\n'
                'El resultado de las análisis fue *POSITIVO*, determinando el baneo definitivo de los '
                'IDs denunciados en la queja adjunta, por violación de las Reglas de la Comunidad y '
                'Términos de Servicio de la App Suprema (Softplay/Colusión), con retención de '
                'ganancias en el evento en cuestión, de acuerdo con el informe.'
            ),
        },
    },

    # ── MULTA ─────────────────────────────────────────────────────────────────

    {
        'categoria': 'Protocolo Positivo com Multa',
        'tipo_cabecalho': 'comunicado',
        'campos': [
            {'key': 'detalhes_multa', 'label': 'Detalhes da Multa (agência, valor, etc.)', 'tipo': 'textarea'},
        ],
        'corpo': {
            'português': (
                'Comunicamos que a investigação vinculada ao protocolo listado foi concluído. '
                'O resultado da análise foi positivo, sendo determinado o banimento das agências/jogadores '
                'informados abaixo, por violação das Regras da Comunidade e Termos de Serviço do '
                'Suprema App, bem como *aplicação de multa referente ao rake no período de apuração '
                'e retenção das fichas em conta*. Desse modo os valores que serão cobrados no próximo '
                'fechamento, serão os seguintes:\n\n{detalhes_multa}'
            ),
            'inglês': (
                'We communicate that the investigation linked to the listed protocol has been completed. '
                'The result of the analysis was positive, being determined the definitive banishment '
                'of the agencies and their respective downlines previously informed, for violation of '
                'the Community Rules and Terms of Service of the Suprema App, as well as the '
                '*imposition of a fine referring to the chips withdrawn from the accounts and rake of '
                'the same(s) in the calculation period*. The amounts that will be charged at the next '
                'closing are as follows:\n\n{detalhes_multa}'
            ),
            'espanhol': (
                'Comunicamos que la investigación vinculada al protocolo ha concluido. '
                'El resultado del análisis fue positivo, determinándose el baneo definitivo de las '
                'agencias y sus respectivas líneas de descarga previamente informadas, por violación '
                'a las Normas de la Comunidad y Términos de Servicio de la App de Suprema, así como '
                'la *imposición de una multa referente a las ganancias y rake de la(s) misma(s) en '
                'el periodo de cálculo*. Los importes que se cobrarán en el próximo cierre son los '
                'siguientes:\n\n{detalhes_multa}'
            ),
        },
    },

    {
        'categoria': 'Protocolo Positivo sem Multa',
        'tipo_cabecalho': 'comunicado',
        'campos': [],
        'corpo': {
            'português': (
                'Comunicamos que a investigação vinculada ao protocolo listado foi concluída. '
                'O resultado da análise foi *POSITIVO*. Sem ocorrência de multa.'
            ),
            'inglês': (
                'We would like to inform you that the investigation linked to the protocol listed '
                'has been concluded, according to the attached report. '
                'The result of the analysis was *POSITIVE*. No fines were incurred.'
            ),
            'espanhol': (
                'Nos gustaría informarle de que la investigación relacionada con el protocolo '
                'indicado ha finalizado. El resultado del análisis ha sido *POSITIVO*. No hay multas.'
            ),
        },
    },

    # ── CHAT ──────────────────────────────────────────────────────────────────

    {
        'categoria': 'Abuso de Chat',
        'tipo_rodape': 'simples',
        'campos': [
            {'key': 'conta_id', 'label': 'Conta (Nick + ID)  ex: JohnDoe (123456)', 'tipo': 'text'},
            {'key': 'dias',     'label': 'Dias de suspensão do chat',                'tipo': 'number'},
        ],
        'corpo': {
            'português': (
                'Foi identificada violação dos termos de conduta envolvendo a conta *{conta_id}*, '
                'por abuso de chat, desse modo a conta em questão teve o chat suspenso por *{dias} dias*. '
                'Ao término do prazo o jogador deverá enviar email para security@suprema.group '
                'solicitando o reestabelecimento do chat.'
            ),
        },
    },

    # ── FINANCEIRO ────────────────────────────────────────────────────────────

    {
        'categoria': 'Envio de Fichas',
        'tipo_cabecalho': 'comunicado',
        'campos': [
            {'key': 'fichas',  'label': 'Quantidade de Fichas',      'tipo': 'number'},
            {'key': 'jogador', 'label': 'Jogador (Nick + ID)',        'tipo': 'text'},
        ],
        'corpo': {
            'português': (
                'Comunicamos ao clube que foram enviadas *{fichas} fichas* ao jogador *{jogador}*, '
                'conforme imagem em anexo.\n\n'
                '_Os valores serão condicionados no próximo fechamento do clube._'
            ),
        },
    },

    # ── INFORMATIVO ───────────────────────────────────────────────────────────

    {
        'categoria': 'ID sem Restrição',
        'sem_cabecalho': True,
        'campos': [],
        'corpo': {
            'português': (
                'Esse ID não tem restrição junto à Security.\n\n'
                'Caso esteja com problemas para acessar a plataforma no seu smartphone, '
                'recomendamos que realize a limpeza de cache do seu dispositivo para corrigir o problema.\n\n'
                'Para dispositivo Android:\n'
                '1. Va em *Configurações do Sistema*\n'
                '2. *Armazenamento* ou *Apps*\n'
                '3. Selecione o aplicativo *Suprema Poker*\n'
                '4. *Limpar Cache* ou *Apagar App* (neste caso será necessário reinstalar o aplicativo em seguida).\n\n'
                'Para dispositivo iOS:\n'
                '1. Va em *Ajustes*\n'
                '2. *Geral*\n'
                '3. *Armazenamento do iPhone*\n'
                '4. Selecione o aplicativo *Suprema Poker*\n'
                '5. *Apagar Cache* ou *Apagar App* (neste caso será necessário reinstalar o aplicativo em seguida).'
            ),
        },
    },

    {
        'categoria': 'Notificação de Aliciamento',
        'tipo_cabecalho': 'aliciamento',
        'campos': [],
        # {nome_clube} vem de dados_base — não precisa ser preenchido pelo usuário
        'corpo': {
            'português': (
                'Comunicamos que o clube *{nome_clube}* atuou em ocorrência de oferta de rakeback, '
                'conforme laudo em anexo, violando diretamente o estatuto da suprema, praticando '
                'aliciamento de agente.'
            ),
        },
    },

    {
        'categoria': 'Ressarcimento SX',
        'sem_cabecalho': True,
        'campos': [],
        # {data} vem de dados_base — não precisa ser preenchido pelo usuário
        'corpo': {
            'português': (
                '*Notificação Security PKR*\n\n'
                'Segue a relação dos IDs que receberam ressarcimentos através da Security no dia *{data}*.\n\n'
                'Nela são encontrados qual o torneio, a data do ocorrido e o protocolo que foi vinculado '
                'junto à Security, assim como a relação de IDs, clubes e valores que foram enviados.\n\n'
                'Caso o clube queira conferir, basta procurar no histórico de movimentação do Suprema App '
                'filtrando pela conta da *Security ADM (37704)*.\n\n'
                'Todos os valores já foram lançados e serão creditados aos clubes no próximo fechamento.\n\n'
                'Atenciosamente,\n\n'
                '*Security PKR*'
            ),
        },
    },

    # ── ABERTURA DE INVESTIGAÇÃO ───────────────────────────────────────────────────────────

    {
        'categoria': 'Abertura de Investigação - Collusion/Conluio',
        'campos': [
            {'key': 'contas', 'label': 'Contas envolvidas (um ID por linha)', 'tipo': 'textarea'},
        ],
        'corpo': {
            'português': (
                'Notificamos que os jogadores abaixo estão sob investigação por violação das '
                'Regras da Comunidade e Termos de Serviço do Suprema App (Collusion).\n\n'
                '{contas}\n\n'
                'Solicitamos que as fichas fiquem congeladas até a finalização do caso e, também que'
                '*não seja(m) feito(s) nenhum envio, saque ou pagamento para os jogadores em questão*.'
            ),
            'inglês': (

            ),
            'espanhol': (

            ),
        },
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# FUNÇÕES AUXILIARES
# ──────────────────────────────────────────────────────────────────────────────

def montar_cabecalho(
    idioma: str,
    protocolo: int,
    nome_clube: str,
    id_clube: int,
    nome_liga: str,
    id_liga: int,
    data: str,
    tipo: str = 'notificacao',
) -> str:
    cabecalhos = _CABECALHOS_MAP.get(tipo, CABECALHOS)
    if idioma not in cabecalhos:
        raise ValueError(
            f'⚠️ Idioma "{idioma}" não suportado! Idiomas disponíveis: {list(cabecalhos.keys())}'
        )
    return cabecalhos[idioma].format(
        protocolo=protocolo,
        nome_clube=nome_clube,
        id_clube=id_clube,
        nome_liga=nome_liga,
        id_liga=id_liga,
        data=data,
    )


def montar_rodape(idioma: str, tipo: str = 'notificacao') -> str:
    rodapes = _RODAPES_MAP.get(tipo, RODAPES)
    return rodapes.get(idioma, '\n\nAtenciosamente,\n\n*Security PKR*')


def montar_notificacao(
    idioma: str,
    cabecalho: str,
    modelo: dict,
    campos_preenchidos: dict,
    dados_base: dict | None = None,
) -> str:
    '''
    Monta a mensagem completa: cabeçalho + corpo + rodapé.

    :param idioma:             idioma do clube.
    :param cabecalho:          string já montada por montar_cabecalho().
    :param modelo:             dict do modelo selecionado em MODELOS.
    :param campos_preenchidos: dict {key: valor} com os campos dinâmicos preenchidos pelo usuário.
    :param dados_base:         dict com os campos do cabeçalho (protocolo, nome_clube, id_clube,
                               nome_liga, id_liga, data) disponíveis para interpolação no corpo.
                               Necessário para modelos que referenciam {nome_clube} ou {data} no corpo
                               (ex: Aliciamento, Ressarcimento SX).
    '''
    corpo = modelo['corpo'].get(idioma, modelo['corpo'].get('português', ''))
    context = {**(dados_base or {}), **campos_preenchidos}
    corpo_formatado = corpo.format(**context)

    if modelo.get('sem_cabecalho', False):
        return corpo_formatado

    tipo_cabecalho = modelo.get('tipo_cabecalho', 'notificacao')
    tipo_rodape    = modelo.get('tipo_rodape', tipo_cabecalho)
    rodape = montar_rodape(idioma, tipo_rodape)

    return f'{cabecalho}{corpo_formatado}{rodape}'
