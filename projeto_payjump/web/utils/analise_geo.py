'''
Análise e geração de PDF para a página de Geolocalização.

Funções de preparação de dados, detecção de alertas, tabelas resumo
e exportação PDF (com mapa estático e suporte a landscape) para
consultas de geolocalização por IP e GPS.

# Convenção de nomes:
# Funções e variáveis com prefixo '_' são de uso INTERNO deste módulo —
# elas não devem ser chamadas de outros arquivos. É uma convenção Python
# para sinalizar "detalhe de implementação, não faz parte da API pública".
'''

import io

import pandas as pd
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Image as RLImage, Paragraph, Spacer

from .pdf_builder import adicionar_tabela, finalizar_pdf, inicializar_pdf
from .pdf_config import (
    ESTILO_LEGENDA,
    FONTE_NEGRITO_ITALICO,
    FONTE_NORMAL,
    styles,
)

# Paleta de até 10 cores para marcadores (hex, usada no staticmap e na legenda)
PALETA_HEX = [
    '#E31A1C',  # vermelho
    '#33A02C',  # verde
    '#1F78B4',  # azul
    '#FF7F00',  # laranja
    '#6A3D9A',  # roxo
    '#B15928',  # marrom
    '#A6CEE3',  # azul claro
    '#B2DF8A',  # verde claro
    '#FB9A99',  # rosa
    '#FDBF6F',  # amarelo
]

# Mesma paleta em RGBA (mantida para compatibilidade futura)
PALETA_RGBA = [
    [227, 26,  28,  200],
    [51,  160, 44,  200],
    [31,  120, 180, 200],
    [255, 127, 0,   200],
    [106, 61,  154, 200],
    [177, 89,  40,  200],
    [166, 206, 227, 200],
    [178, 223, 138, 200],
    [251, 154, 153, 200],
    [253, 191, 111, 200],
]

# -----------------------------------------------------
# ESTILOS DE CÉLULA (internos — prefixo '_')
# -----------------------------------------------------
# Quando uma célula de tabela usa Paragraph, o ReportLab ignora as regras de
# fonte do ESTILO_TABELA (que só funcionam para strings simples). Por isso,
# é necessário definir fontName diretamente em cada estilo de Paragraph.

# Estilo para células de DADOS: Calibri Light, tamanho 8, quebra de linha automática.
_ESTILO_CELULA = ParagraphStyle(
    'celula_geo',
    parent=styles['Normal'],
    fontName=FONTE_NORMAL,
    wordWrap='LTR',
    fontSize=8,
)

# Estilo para células de CABEÇALHO: negrito itálico, igual ao que o ESTILO_TABELA
# aplicava antes (quando o cabeçalho era uma string simples).
_ESTILO_CABECALHO = ParagraphStyle(
    'cabecalho_geo',
    parent=styles['Normal'],
    fontName=FONTE_NEGRITO_ITALICO,
    wordWrap='LTR',
    fontSize=8,
)


# -----------------------------------------------------
# PALETA
# -----------------------------------------------------

def mapa_cores_por_id(ids: list) -> dict:
    '''Mapeia IDs ordenados para cores RGBA da paleta.'''
    ids_ordenados = sorted(set(ids))
    return {id_: PALETA_RGBA[i % len(PALETA_RGBA)] for i, id_ in enumerate(ids_ordenados)}


def mapa_cores_hex_por_id(ids: list) -> dict:
    '''Mapeia IDs ordenados para cores HEX da paleta (uso no staticmap / legenda).'''
    ids_ordenados = sorted(set(ids))
    return {id_: PALETA_HEX[i % len(PALETA_HEX)] for i, id_ in enumerate(ids_ordenados)}


# -----------------------------------------------------
# PREPARAÇÃO DE DADOS
# -----------------------------------------------------

def preparar_df_ip(df_bruto: pd.DataFrame) -> pd.DataFrame:
    '''
    Normaliza colunas do arquivo IP exportado do backend.

    Renomeia colunas para o padrão interno, descarta colunas sem dados úteis
    (incluindo colunas Unnamed geradas pelo Excel) e retorna DataFrame pronto
    para geolocalização.
    '''
    df = df_bruto.copy()
    df = df.drop(columns=[c for c in df.columns if str(c).startswith('Unnamed')], errors='ignore')
    df = df.rename(columns={
        'Player Name': 'JOGADOR',
        'Player ID':   'JOGADOR_ID',
        'IP address':  'IP',
        'Area code':   'PAIS_AREA',
    })
    df = df.drop(columns=[c for c in ('VPN', 'IP-City') if c in df.columns])
    return df


def preparar_df_gps(df_bruto: pd.DataFrame) -> pd.DataFrame:
    '''
    Normaliza colunas do arquivo GPS exportado do backend.

    Renomeia coordenadas, dados de jogador e dispositivo para o padrão interno.
    Descarta colunas "undefined" e Unnamed geradas pelo Excel.
    '''
    df = df_bruto.copy()
    df = df.drop(columns=[c for c in df.columns if str(c).startswith('Unnamed')], errors='ignore')
    df = df.rename(columns={
        'Player Name':      'JOGADOR',
        'Player ID':        'JOGADOR_ID',
        'Coordinate X':     'LATITUDE',
        'GPS coordinate Y': 'LONGITUDE',
        'Record time':      'DATA',
        'Device Code':      'DISPOSITIVO',
        'Area code':        'PAIS_AREA',
    })
    df = df.drop(columns=[c for c in ('undefined',) if c in df.columns])
    return df


# -----------------------------------------------------
# TABELAS RESUMO
# -----------------------------------------------------

def resumo_ip(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Deduplica registros de IP descartando PAIS_AREA (redundante) e coordenadas.
    Cada combinação única de (ID Jogador, Jogador, IP, localização) vira uma linha.
    '''
    colunas_resumo = [c for c in ('JOGADOR_ID', 'JOGADOR', 'IP', 'CIDADE', 'ESTADO', 'PAIS')
                      if c in df.columns]
    return df[colunas_resumo].drop_duplicates().reset_index(drop=True)


def resumo_gps(df: pd.DataFrame) -> pd.DataFrame:
    '''
    Deduplica registros de GPS removendo Hand ID, DATA e coordenadas brutas
    (únicos por mão). Mantém combinações únicas de jogador + localização + dispositivo.
    '''
    colunas_drop   = [c for c in ('Hand ID', 'DATA', 'LATITUDE', 'LONGITUDE') if c in df.columns]
    colunas_resumo = [c for c in df.columns if c not in colunas_drop]
    return df[colunas_resumo].drop_duplicates().reset_index(drop=True)


# -----------------------------------------------------
# DETECÇÃO DE ALERTAS
# -----------------------------------------------------

def detectar_alertas_ip(df: pd.DataFrame) -> dict:
    '''
    Detecta situações suspeitas no dataset de IPs.

    Returns:
        dict com chaves:
        - 'multiplos_paises': jogadores com mais de 1 país distinto
        - 'ips_compartilhados': IPs usados por mais de 1 jogador
    '''
    alertas = {}

    if 'PAIS' in df.columns and 'JOGADOR' in df.columns:
        paises_por_jogador = (
            df.groupby('JOGADOR')['PAIS']
            .apply(lambda s: sorted(s.dropna().unique().tolist()))
            .reset_index()
            .rename(columns={'PAIS': 'PAÍSES'})
        )
        alertas['multiplos_paises'] = paises_por_jogador[
            paises_por_jogador['PAÍSES'].apply(len) > 1
        ].copy()
    else:
        alertas['multiplos_paises'] = pd.DataFrame()

    if 'IP' in df.columns and 'JOGADOR' in df.columns:
        jogadores_por_ip = (
            df.groupby('IP')['JOGADOR']
            .apply(lambda s: sorted(s.dropna().unique().tolist()))
            .reset_index()
            .rename(columns={'JOGADOR': 'JOGADORES'})
        )
        alertas['ips_compartilhados'] = jogadores_por_ip[
            jogadores_por_ip['JOGADORES'].apply(len) > 1
        ].copy()
    else:
        alertas['ips_compartilhados'] = pd.DataFrame()

    return alertas


def detectar_alertas_gps(df: pd.DataFrame) -> dict:
    '''
    Detecta situações suspeitas no dataset de GPS.

    Returns:
        dict com chaves:
        - 'multiplas_cidades': jogadores com mais de 1 cidade distinta
        - 'dispositivos_compartilhados': Device Codes usados por mais de 1 jogador
    '''
    alertas = {}

    if 'CIDADE' in df.columns and 'JOGADOR' in df.columns:
        cidades_por_jogador = (
            df.groupby('JOGADOR')['CIDADE']
            .apply(lambda s: sorted(s.dropna().unique().tolist()))
            .reset_index()
            .rename(columns={'CIDADE': 'CIDADES'})
        )
        alertas['multiplas_cidades'] = cidades_por_jogador[
            cidades_por_jogador['CIDADES'].apply(len) > 1
        ].copy()
    else:
        alertas['multiplas_cidades'] = pd.DataFrame()

    if 'DISPOSITIVO' in df.columns and 'JOGADOR' in df.columns:
        jogadores_por_disp = (
            df.groupby('DISPOSITIVO')['JOGADOR']
            .apply(lambda s: sorted(s.dropna().unique().tolist()))
            .reset_index()
            .rename(columns={'JOGADOR': 'JOGADORES'})
        )
        alertas['dispositivos_compartilhados'] = jogadores_por_disp[
            jogadores_por_disp['JOGADORES'].apply(len) > 1
        ].copy()
    else:
        alertas['dispositivos_compartilhados'] = pd.DataFrame()

    return alertas


# -----------------------------------------------------
# MAPA ESTÁTICO (staticmap → PNG → PDF)
# -----------------------------------------------------

def _gerar_imagem_mapa(
    df_pontos: pd.DataFrame,
    cores_hex: dict,
    largura: int = 800,
    altura: int = 400,
) -> tuple[io.BytesIO | None, str | None]:
    '''
    Renderiza mapa OSM com marcadores coloridos por JOGADOR_ID via staticmap.

    Returns:
        (buffer_png, None) em caso de sucesso.
        (None, mensagem_de_erro) em caso de falha.
    '''
    try:
        from staticmap import StaticMap, CircleMarker  # type: ignore
    except ImportError:
        return None, 'staticmap não instalado. Rode: pip install staticmap'

    try:
        mapa = StaticMap(largura, altura)
        for _, linha in df_pontos.dropna(subset=['LATITUDE', 'LONGITUDE']).iterrows():
            cor = cores_hex.get(linha.get('JOGADOR_ID'), '#E31A1C')
            mapa.add_marker(CircleMarker(
                (float(linha['LONGITUDE']), float(linha['LATITUDE'])), cor, 12
            ))
        imagem = mapa.render()
        buffer = io.BytesIO()
        imagem.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer, None
    except Exception as erro:
        return None, str(erro)


# -----------------------------------------------------
# GERAÇÃO DE PDF — funções auxiliares (internas)
# -----------------------------------------------------

_HEADERS_IP = {
    'JOGADOR_ID': 'ID Jogador',
    'JOGADOR':    'Jogador',
    'IP':         'IP',
    'CIDADE':     'Cidade',
    'ESTADO':     'Estado',
    'PAIS':       'País',
}

_HEADERS_GPS = {
    'JOGADOR_ID':  'ID Jogador',
    'JOGADOR':     'Jogador',
    'DATA':        'Data',
    'CIDADE':      'Cidade',
    'ESTADO':      'Estado',
    'PAIS':        'País',
    'DISPOSITIVO': 'Dispositivo',
}


def _calcular_larguras_proporcional(
    df: pd.DataFrame,
    colunas: list,
    cabecalhos: list,
    largura_total: float,
    proporcao_minima: float = 0.06,
) -> list:
    '''
    Calcula larguras de coluna proporcionais ao comprimento máximo do conteúdo.

    Para cada coluna, encontra o texto mais longo (entre cabeçalho e dados).
    A proporção de cada coluna é: comprimento_maximo / total_caracteres.
    `proporcao_minima` garante que nenhuma coluna fique estreita demais (padrão: 6% da largura total).
    A soma das larguras retornadas é sempre exatamente `largura_total`.

    Prefixo '_': função de uso interno do módulo.
    '''
    comprimentos_maximos = []
    for coluna, cabecalho in zip(colunas, cabecalhos):
        valores            = df[coluna].fillna('—').astype(str)
        comprimento_maximo = max(len(cabecalho), int(valores.str.len().max()))
        comprimentos_maximos.append(comprimento_maximo)

    total_caracteres  = sum(comprimentos_maximos)
    proporcoes_brutas = [max(proporcao_minima, comp / total_caracteres)
                         for comp in comprimentos_maximos]
    soma_proporcoes   = sum(proporcoes_brutas)
    return [largura_total * prop / soma_proporcoes for prop in proporcoes_brutas]


def _paragrafo_alerta(texto: str) -> Paragraph:
    return Paragraph(f'<font color="red">⚠ {texto}</font>', styles['Normal'])


def _paragrafo_ok(texto: str) -> Paragraph:
    return Paragraph(f'<font color="green">✓ {texto}</font>', styles['Normal'])


def _legenda_pdf(df: pd.DataFrame) -> Paragraph:
    '''
    Parágrafo com ■ colorido por jogador para inserir após o mapa no PDF.
    Cada entrada mostra: ■ NomeJogador (ID: X)
    '''
    if 'JOGADOR_ID' not in df.columns:
        return Spacer(1, 1)
    ids = sorted(df['JOGADOR_ID'].dropna().unique().tolist())
    if not ids:
        return Spacer(1, 1)
    cores = mapa_cores_hex_por_id(ids)
    id_para_nome: dict = {}
    if 'JOGADOR' in df.columns:
        id_para_nome = (
            df.drop_duplicates('JOGADOR_ID')
              .set_index('JOGADOR_ID')['JOGADOR']
              .to_dict()
        )
    partes = [
        f'<font color="{cores[id_]}">■ <b>{id_para_nome.get(id_, id_)}</b></font> (ID: {id_})'
        for id_ in ids
    ]
    return Paragraph('&nbsp;&nbsp;&nbsp;'.join(partes), styles['Normal'])


def _montar_linhas(df: pd.DataFrame, colunas: list, cabecalhos: list) -> list:
    '''
    Monta linhas da tabela com word wrap em TODAS as células (cabeçalho e dados).

    Usar Paragraph tanto no cabeçalho quanto nos dados garante que nenhuma célula
    ultrapasse sua largura alocada — o texto quebra em vez de extrapolar a margem.
    Prefixo '_': função de uso interno do módulo.
    '''
    linhas = [
        [Paragraph(cab, _ESTILO_CABECALHO) for cab in cabecalhos]  # linha de cabeçalho
    ]
    for _, linha in df.iterrows():
        linhas.append([
            Paragraph(str(linha.get(col, '—') or '—'), _ESTILO_CELULA)
            for col in colunas
        ])
    return linhas


def _montar_linhas_alerta(cabecalhos: list, dados: list) -> list:
    '''
    Monta linhas de tabela de alertas com word wrap em cabeçalho e células de dados.

    Diferente de `_montar_linhas`, recebe os dados como lista de listas (não DataFrame),
    pois os alertas já são construídos linha a linha antes de chamar esta função.
    Prefixo '_': função de uso interno do módulo.
    '''
    linhas = [
        [Paragraph(cab, _ESTILO_CABECALHO) for cab in cabecalhos]
    ]
    for linha in dados:
        linhas.append([Paragraph(str(valor), _ESTILO_CELULA) for valor in linha])
    return linhas


def _secao_alertas_ip(story: list, alertas: dict, largura_util: float) -> None:
    '''Adiciona ao story a seção de alertas de IP com tabelas de largura proporcional.'''
    story.append(Paragraph('Alertas — IP', styles['Heading2']))

    df_paises = alertas.get('multiplos_paises', pd.DataFrame())
    if not df_paises.empty:
        story.append(_paragrafo_alerta(
            f'{len(df_paises)} jogador(es) com registros em múltiplos países. Possível usuário de VPN!'
        ))
        cabecalhos = ['Jogador', 'Países']
        dados = [
            [str(row['JOGADOR']), ', '.join(map(str, row['PAÍSES']))]
            for _, row in df_paises.iterrows()
        ]
        df_temp  = pd.DataFrame(dados, columns=['JOGADOR', 'PAISES'])
        larguras = _calcular_larguras_proporcional(df_temp, ['JOGADOR', 'PAISES'], cabecalhos, largura_util)
        adicionar_tabela(story, _montar_linhas_alerta(cabecalhos, dados), larguras)
    else:
        story.append(_paragrafo_ok('Nenhum jogador com múltiplos países.'))

    story.append(Spacer(1, 8))

    df_ips = alertas.get('ips_compartilhados', pd.DataFrame())
    if not df_ips.empty:
        story.append(_paragrafo_alerta(
            f'{len(df_ips)} IP(s) compartilhado(s) entre jogadores distintos.'
        ))
        cabecalhos = ['IP', 'Jogadores']
        dados = [
            [str(row['IP']), ', '.join(map(str, row['JOGADORES']))]
            for _, row in df_ips.iterrows()
        ]
        df_temp  = pd.DataFrame(dados, columns=['IP', 'JOGADORES'])
        larguras = _calcular_larguras_proporcional(df_temp, ['IP', 'JOGADORES'], cabecalhos, largura_util)
        adicionar_tabela(story, _montar_linhas_alerta(cabecalhos, dados), larguras)
    else:
        story.append(_paragrafo_ok('Nenhum IP compartilhado entre jogadores.'))


def _secao_alertas_gps(story: list, alertas: dict, largura_util: float) -> None:
    '''Adiciona ao story a seção de alertas de GPS com tabelas de largura proporcional.'''
    story.append(Paragraph('Alertas — GPS', styles['Heading2']))

    df_cidades = alertas.get('multiplas_cidades', pd.DataFrame())
    if not df_cidades.empty:
        story.append(_paragrafo_alerta(
            f'{len(df_cidades)} jogador(es) com registros em múltiplas cidades.'
        ))
        cabecalhos = ['Jogador', 'Cidades']
        dados = [
            [str(row['JOGADOR']), ', '.join(map(str, row['CIDADES']))]
            for _, row in df_cidades.iterrows()
        ]
        df_temp  = pd.DataFrame(dados, columns=['JOGADOR', 'CIDADES'])
        larguras = _calcular_larguras_proporcional(df_temp, ['JOGADOR', 'CIDADES'], cabecalhos, largura_util)
        adicionar_tabela(story, _montar_linhas_alerta(cabecalhos, dados), larguras)
    else:
        story.append(_paragrafo_ok('Nenhum jogador com múltiplas cidades.'))

    story.append(Spacer(1, 8))

    df_disp = alertas.get('dispositivos_compartilhados', pd.DataFrame())
    if not df_disp.empty:
        story.append(_paragrafo_alerta(
            f'{len(df_disp)} dispositivo(s) compartilhado(s) entre jogadores distintos.'
        ))
        cabecalhos = ['Dispositivo', 'Jogadores']
        dados = [
            [str(row['DISPOSITIVO']), ', '.join(map(str, row['JOGADORES']))]
            for _, row in df_disp.iterrows()
        ]
        df_temp  = pd.DataFrame(dados, columns=['DISPOSITIVO', 'JOGADORES'])
        larguras = _calcular_larguras_proporcional(df_temp, ['DISPOSITIVO', 'JOGADORES'], cabecalhos, largura_util)
        adicionar_tabela(story, _montar_linhas_alerta(cabecalhos, dados), larguras)
    else:
        story.append(_paragrafo_ok('Nenhum dispositivo compartilhado entre jogadores.'))


# -----------------------------------------------------
# GERAÇÃO DE PDF — função principal
# -----------------------------------------------------

def gerar_pdf_geo(
    titulo: str,
    df_ip=None,
    df_gps=None,
    alertas_ip: dict | None = None,
    alertas_gps: dict | None = None,
) -> bytes:
    '''
    Gera relatório PDF de geolocalização.

    Estrutura do PDF:
    1. Tabelas resumo e alertas (IP e/ou GPS)
    2. Mapas estáticos com legenda de cores (ao final)

    - Seção IP em portrait.
    - Seção GPS em landscape.
    - Parâmetros df_ip e df_gps são opcionais.

    Returns:
        bytes do PDF pronto para download.
    '''
    tem_gps            = df_gps is not None and not df_gps.empty
    buffer, doc, story = inicializar_pdf('', paisagem=tem_gps, titulo_completo=titulo)
    largura_util       = doc.width  # largura real do conteúdo, respeitando as margens do doc

    # Imagens de mapa são coletadas aqui e adicionadas ao final do PDF
    story_mapas: list = []

    # ── Seção IP ──────────────────────────────────────────
    if df_ip is not None and not df_ip.empty:
        story.append(Paragraph('Geolocalização por IP', styles['Heading2']))

        # Tabela resumo com larguras automáticas e word wrap em todas as células
        df_resumo_ip = resumo_ip(df_ip)
        colunas      = [c for c in _HEADERS_IP if c in df_resumo_ip.columns]
        cabecalhos   = [_HEADERS_IP[c] for c in colunas]
        larguras     = _calcular_larguras_proporcional(df_resumo_ip, colunas, cabecalhos, largura_util)
        linhas       = _montar_linhas(df_resumo_ip, colunas, cabecalhos)
        story.append(Paragraph(
            'Registros únicos de endereços IP por conta, com localização geográfica estimada. '
            'Cada linha representa uma combinação distinta de jogador e endereço IP.',
            ESTILO_LEGENDA,
        ))
        story.append(Paragraph(
            'O registro de IP pode indicar uma localização diferente do local real do usuário, '
            'pois a geolocalização de IP é apenas uma estimativa baseada em bases de dados que '
            'associam faixas de IP a determinadas regiões. Dependendo do provedor de internet, '
            'do tipo de conexão (como redes móveis), do roteamento do tráfego por servidores em '
            'outras cidades ou do uso de VPNs e proxies, o endereço pode ser identificado em uma '
            'localidade distinta da posição física do usuário.',
            ESTILO_LEGENDA,
        ))
        story.append(Spacer(1, 8))
        adicionar_tabela(story, linhas, larguras)

        if alertas_ip:
            _secao_alertas_ip(story, alertas_ip, largura_util)

        story.append(Spacer(1, 16))

        # Mapa → story_mapas (adicionado ao final do PDF)
        df_mapa_ip = df_ip.dropna(subset=['LATITUDE', 'LONGITUDE'])
        if not df_mapa_ip.empty and 'JOGADOR_ID' in df_mapa_ip.columns:
            cores_hex          = mapa_cores_hex_por_id(df_mapa_ip['JOGADOR_ID'].tolist())
            buffer_mapa, erro  = _gerar_imagem_mapa(df_mapa_ip, cores_hex, largura=1000, altura=500)
            if buffer_mapa:
                story_mapas.append(Paragraph('Mapa — IP', styles['Heading3']))
                story_mapas.append(RLImage(buffer_mapa, width=largura_util, height=largura_util * 0.5))
                story_mapas.append(Spacer(1, 6))
                story_mapas.append(_legenda_pdf(df_ip))
                story_mapas.append(Spacer(1, 16))

    # ── Seção GPS ─────────────────────────────────────────
    if tem_gps:
        story.append(Paragraph('Geolocalização por GPS', styles['Heading2']))

        # Tabela resumo GPS com larguras automáticas e word wrap em todas as células
        df_resumo_gps = resumo_gps(df_gps)
        colunas       = [c for c in _HEADERS_GPS if c in df_resumo_gps.columns]
        cabecalhos    = [_HEADERS_GPS[c] for c in colunas]
        larguras      = _calcular_larguras_proporcional(df_resumo_gps, colunas, cabecalhos, largura_util)
        linhas        = _montar_linhas(df_resumo_gps, colunas, cabecalhos)
        story.append(Paragraph(
            'Registros únicos de localização por coordenadas GPS, deduplificados por jogador, '
            'cidade e dispositivo. Data e coordenadas brutas são omitidas nesta visão.',
            ESTILO_LEGENDA,
        ))
        adicionar_tabela(story, linhas, larguras)

        if alertas_gps:
            _secao_alertas_gps(story, alertas_gps, largura_util)

        # Mapa → story_mapas (adicionado ao final do PDF)
        df_mapa_gps = df_gps.dropna(subset=['LATITUDE', 'LONGITUDE'])
        if not df_mapa_gps.empty and 'JOGADOR_ID' in df_mapa_gps.columns:
            cores_hex          = mapa_cores_hex_por_id(df_mapa_gps['JOGADOR_ID'].tolist())
            buffer_mapa, erro  = _gerar_imagem_mapa(df_mapa_gps, cores_hex, largura=1400, altura=600)
            if buffer_mapa:
                story_mapas.append(Paragraph('Mapa — GPS', styles['Heading3']))
                story_mapas.append(RLImage(buffer_mapa, width=largura_util, height=largura_util * 0.43))
                story_mapas.append(Spacer(1, 6))
                story_mapas.append(_legenda_pdf(df_gps))

    # Mapas sempre ao final do documento
    story.extend(story_mapas)

    return finalizar_pdf(buffer, doc, story).read()
