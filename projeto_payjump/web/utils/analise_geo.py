'''
Análise e geração de PDF para a página de Geolocalização.

Funções de preparação de dados, detecção de alertas, tabelas resumo
e exportação PDF (com mapa estático e suporte a landscape) para
consultas de geolocalização por IP e GPS.

# Convenção de nomes:
# Funções e variáveis com prefixo '_' são de uso INTERNO deste módulo —
# elas não devem ser chamadas de outros arquivos. É uma convenção Python
# para sinalizar "detalhe de implementação, não faz parte da API pública".
# Exceção: _encontrar_ids_compartilhados é importada por analise_snowflake.py.
'''

import io
import re

import pandas as pd
from reportlab.platypus import Image as RLImage, Paragraph, Spacer

from .pdf_builder import (
    adicionar_tabela,
    calcular_larguras_proporcional,
    finalizar_pdf,
    inicializar_pdf,
)
from .pdf_config import (
    ESTILO_CABECALHO_CELULA,
    ESTILO_CABECALHO_CELULA_NOWRAP,
    ESTILO_CELULA,
    ESTILO_LEGENDA,
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

# -----------------------------------------------------
# ESTILOS DE CÉLULA (aliases dos estilos compartilhados de pdf_config)
# -----------------------------------------------------
# Quando uma célula usa Paragraph, o ReportLab ignora as regras de fonte do
# ESTILO_TABELA. Os aliases abaixo apontam para os estilos compartilhados
# de pdf_config, garantindo consistência visual em todos os PDFs.
_ESTILO_CELULA    = ESTILO_CELULA
_ESTILO_CABECALHO = ESTILO_CABECALHO_CELULA_NOWRAP


# -----------------------------------------------------
# PALETA
# -----------------------------------------------------

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

    Valida que as colunas obrigatórias existam, renomeia para o padrão interno,
    descarta colunas sem dados úteis e retorna DataFrame pronto para geolocalização.

    Raises:
        ValueError: Se alguma coluna obrigatória estiver ausente no arquivo.
    '''
    colunas_obrigatorias = {'Player Name', 'Player ID', 'IP address'}
    faltando             = colunas_obrigatorias - set(df_bruto.columns)
    if faltando:
        raise ValueError(
            f'Arquivo inválido para tipo IP. Colunas não encontradas: {", ".join(sorted(faltando))}. '
            f'Verifique se o arquivo exportado é do tipo correto (Relatório de IP).'
        )
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

    Valida que as colunas obrigatórias existam, renomeia coordenadas, dados de jogador
    e dispositivo para o padrão interno. Descarta colunas "undefined" e Unnamed.

    Raises:
        ValueError: Se alguma coluna obrigatória estiver ausente no arquivo.
    '''
    colunas_obrigatorias = {'Player Name', 'Player ID', 'Coordinate X', 'GPS coordinate Y'}
    faltando             = colunas_obrigatorias - set(df_bruto.columns)
    if faltando:
        raise ValueError(
            f'Arquivo inválido para tipo GPS. Colunas não encontradas: {", ".join(sorted(faltando))}. '
            f'Verifique se o arquivo exportado é do tipo correto (Relatório de GPS).'
        )
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

def _encontrar_ids_compartilhados(
    df: pd.DataFrame,
    coluna_grupo: str,
    coluna_jogador: str,
) -> list:
    '''
    Retorna lista de valores em `coluna_grupo` usados por mais de 1 jogador único.

    Exemplo: `_encontrar_ids_compartilhados(df, 'IP', 'JOGADOR')` retorna os IPs
    que aparecem para mais de um jogador distinto.

    Prefixo '_': função de uso interno. Exceção: importada por analise_snowflake.py.
    '''
    contagem = df.groupby(coluna_grupo)[coluna_jogador].nunique()
    return contagem[contagem > 1].index.tolist()


def detectar_alertas_ip(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    '''
    Detecta situações suspeitas no dataset de IPs.

    Returns:
        dict com chaves:
        - 'multiplos_paises': jogadores com mais de 1 país distinto
        - 'ips_compartilhados': IPs usados por mais de 1 jogador
    '''
    alertas: dict[str, pd.DataFrame] = {}

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
        ips_partilhados = _encontrar_ids_compartilhados(df, 'IP', 'JOGADOR')
        jogadores_por_ip = (
            df.groupby('IP')['JOGADOR']
            .apply(lambda s: sorted(s.dropna().unique().tolist()))
            .reset_index()
            .rename(columns={'JOGADOR': 'JOGADORES'})
        )
        alertas['ips_compartilhados'] = jogadores_por_ip[
            jogadores_por_ip['IP'].isin(ips_partilhados)
        ].copy()
    else:
        alertas['ips_compartilhados'] = pd.DataFrame()

    return alertas


def detectar_alertas_gps(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    '''
    Detecta situações suspeitas no dataset de GPS.

    Returns:
        dict com chaves:
        - 'multiplas_cidades': jogadores com mais de 1 cidade distinta
        - 'dispositivos_compartilhados': Device Codes usados por mais de 1 jogador
    '''
    alertas: dict[str, pd.DataFrame] = {}

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
        dispositivos_partilhados = _encontrar_ids_compartilhados(df, 'DISPOSITIVO', 'JOGADOR')
        jogadores_por_disp = (
            df.groupby('DISPOSITIVO')['JOGADOR']
            .apply(lambda s: sorted(s.dropna().unique().tolist()))
            .reset_index()
            .rename(columns={'JOGADOR': 'JOGADORES'})
        )
        alertas['dispositivos_compartilhados'] = jogadores_por_disp[
            jogadores_por_disp['DISPOSITIVO'].isin(dispositivos_partilhados)
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
# GERAÇÃO DE PDF — cabeçalhos de tabela
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


# -----------------------------------------------------
# GERAÇÃO DE PDF — funções auxiliares (internas)
# -----------------------------------------------------

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


def gerar_elementos_mapa_pdf(
    df: pd.DataFrame,
    largura_util: float,
    largura_img: int = 1000,
    altura_img: int = 500,
) -> list:
    '''Gera lista de elementos ReportLab (imagem + legenda) para embutir em qualquer PDF.

    Espera colunas: JOGADOR_ID, LATITUDE, LONGITUDE.
    Retorna lista vazia se não houver coordenadas ou se staticmap não estiver instalado.
    '''
    df_mapa = df.dropna(subset=['LATITUDE', 'LONGITUDE'])
    if df_mapa.empty or 'JOGADOR_ID' not in df_mapa.columns:
        return []
    cores_hex         = mapa_cores_hex_por_id(df_mapa['JOGADOR_ID'].tolist())
    buffer_mapa, erro = _gerar_imagem_mapa(df_mapa, cores_hex, largura=largura_img, altura=altura_img)
    if not buffer_mapa:
        return [Paragraph(f'⚠ Mapa não disponível: {erro}', styles['Normal'])]
    proporcao = altura_img / largura_img
    return [
        RLImage(buffer_mapa, width=largura_util, height=largura_util * proporcao),
        Spacer(1, 6),
        _legenda_pdf(df_mapa),
        Spacer(1, 16),
    ]


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
        larguras = calcular_larguras_proporcional(df_temp, ['JOGADOR', 'PAISES'], cabecalhos, largura_util)
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
        larguras = calcular_larguras_proporcional(df_temp, ['IP', 'JOGADORES'], cabecalhos, largura_util)
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
        larguras = calcular_larguras_proporcional(df_temp, ['JOGADOR', 'CIDADES'], cabecalhos, largura_util)
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
        larguras = calcular_larguras_proporcional(df_temp, ['DISPOSITIVO', 'JOGADORES'], cabecalhos, largura_util)
        adicionar_tabela(story, _montar_linhas_alerta(cabecalhos, dados), larguras)
    else:
        story.append(_paragrafo_ok('Nenhum dispositivo compartilhado entre jogadores.'))


# -----------------------------------------------------
# GERAÇÃO DE PDF — função principal
# -----------------------------------------------------

def gerar_pdf_geo(
    titulo: str,
    df_ip: pd.DataFrame | None = None,
    df_gps: pd.DataFrame | None = None,
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

        df_resumo_ip = resumo_ip(df_ip)
        colunas      = [c for c in _HEADERS_IP if c in df_resumo_ip.columns]
        cabecalhos   = [_HEADERS_IP[c] for c in colunas]
        larguras     = calcular_larguras_proporcional(df_resumo_ip, colunas, cabecalhos, largura_util)
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
            elif erro:
                story_mapas.append(Paragraph(f'⚠ Mapa não disponível: {erro}', styles['Normal']))

    # ── Seção GPS ─────────────────────────────────────────
    if tem_gps:
        story.append(Paragraph('Geolocalização por GPS', styles['Heading2']))

        df_resumo_gps = resumo_gps(df_gps)
        colunas       = [c for c in _HEADERS_GPS if c in df_resumo_gps.columns]
        cabecalhos    = [_HEADERS_GPS[c] for c in colunas]
        larguras      = calcular_larguras_proporcional(df_resumo_gps, colunas, cabecalhos, largura_util)
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
            elif erro:
                story_mapas.append(Paragraph(f'⚠ Mapa não disponível: {erro}', styles['Normal']))

    # Mapas sempre ao final do documento
    story.extend(story_mapas)

    return finalizar_pdf(buffer, doc, story).read()


# =====================================================================
# DISPOSITIVOS — preparação, alertas e PDF
# =====================================================================

def censurar_codigo_dispositivo(codigo: str) -> str:
    '''
    Censura código de dispositivo preservando apenas o primeiro segmento UUID.

    Para UUIDs padrão (XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX) mantém os
    primeiros 8 caracteres e substitui o restante por ●, conferindo aparência
    profissional ao relatório sem expor o identificador completo.
    '''
    if not isinstance(codigo, str) or not codigo.strip():
        return '●●●●●●●●-●●●●-●●●●-●●●●-●●●●●●●●●●●●'
    codigo = codigo.strip()
    partes = codigo.split('-')
    if len(partes) == 5:
        sufixo = partes[4][-4:]
        return f'{partes[0]}-●●●●-●●●●-●●●●-●●●●●●●●{sufixo}'
    # Não-UUID: mostra primeiros 8 chars e censura o resto
    sufixo = codigo[-4:] if len(codigo) > 12 else ''
    return codigo[:min(8, len(codigo))] + '-●●●●-●●●●' + sufixo


def _parsear_jogadores(texto: str) -> list[tuple[str, str]]:
    '''Extrai pares (nome, id) do campo Players: "Nome(ID) / Nome2(ID2) / "'''
    matches = re.findall(r'([^/(]+)\s*\((\d+)\)', str(texto))
    return [(nome.strip(), id_) for nome, id_ in matches if nome.strip()]


def _formatar_jogadores(jogadores: list[tuple[str, str]]) -> str:
    return ', '.join(f'{nome} ({id_})' for nome, id_ in jogadores)


def preparar_df_dispositivos(df_bruto: pd.DataFrame) -> pd.DataFrame:
    '''
    Normaliza colunas do arquivo "Same Data With Players" exportado do backend.

    Valida colunas obrigatórias, parseia o campo Players em lista de contas,
    censura o Machine Code e renomeia colunas para o padrão interno.

    Raises:
        ValueError: Se alguma coluna obrigatória estiver ausente.
    '''
    colunas_obrigatorias = {'Machine Code', 'Players'}
    faltando = colunas_obrigatorias - set(df_bruto.columns)
    if faltando:
        raise ValueError(
            f'Arquivo inválido para tipo Dispositivos. Colunas não encontradas: '
            f'{", ".join(sorted(faltando))}. '
            f'Verifique se o arquivo exportado é do tipo "Same Data With Players".'
        )
    df = df_bruto.copy()
    df = df.drop(columns=[c for c in df.columns if str(c).startswith('Unnamed')], errors='ignore')

    df['CODIGO_ORIGINAL']  = df['Machine Code'].astype(str)
    df['CODIGO_CENSURADO'] = df['CODIGO_ORIGINAL'].apply(censurar_codigo_dispositivo)

    df['_JOGADORES_LISTA'] = df['Players'].apply(_parsear_jogadores)
    df['CONTAS']           = df['_JOGADORES_LISTA'].apply(_formatar_jogadores)
    df['N_CONTAS']         = df['_JOGADORES_LISTA'].apply(len)
    df = df.drop(columns=['_JOGADORES_LISTA'])

    renomear = {
        'OS Version':  'VERSAO_OS',
        'Device':      'DISPOSITIVO',
        'Model':       'MODELO',
        'SysOS':       'SISTEMA',
        'Repetitions': 'REPETICOES',
        '模擬器':      'SIMULADOR',
    }
    df = df.rename(columns={k: v for k, v in renomear.items() if k in df.columns})

    if 'SIMULADOR' in df.columns:
        df['SIMULADOR'] = df['SIMULADOR'].map({'NO': 'Não', 'YES': 'Sim'}).fillna('—')

    for col in ('DISPOSITIVO', 'MODELO', 'VERSAO_OS'):
        if col in df.columns:
            df[col] = df[col].fillna('—')

    return df.drop_duplicates(subset=['CODIGO_ORIGINAL']).reset_index(drop=True)


def _extrair_nome_id_de_contas(contas_str: str) -> list[tuple[str, str]]:
    '''Parseia CONTAS formatado "Nome (ID), Nome2 (ID2)" → [(nome, id), ...].'''
    pairs = re.findall(r'([^,]+?)\s*\((\d+)\)', str(contas_str))
    return [(nome.strip(), id_) for nome, id_ in pairs if nome.strip()]


def _inferir_id_investigacao(df: pd.DataFrame) -> str:
    '''Retorna apenas o ID numérico da conta investigada (sem o nome).'''
    m = re.search(r'\((\d+)\)', _inferir_titulo_investigacao(df))
    return m.group(1) if m else ''


def _inferir_titulo_investigacao(df: pd.DataFrame) -> str:
    '''
    Retorna "Nome (ID)" da conta presente em todos os dispositivos do arquivo.

    Identifica o "dono" da investigação como o ID que aparece em 100% das linhas,
    pois cada arquivo "Same Data With Players" é gerado para uma conta específica.
    Retorna string vazia se nenhuma conta comum for encontrada (fallback no chamador).
    '''
    if df.empty or 'CONTAS' not in df.columns:
        return ''
    sets_ids = [
        {id_ for _, id_ in _extrair_nome_id_de_contas(str(c))}
        for c in df['CONTAS']
    ]
    ids_comuns = set.intersection(*sets_ids) if sets_ids else set()
    if not ids_comuns:
        return ''
    id_dono = sorted(ids_comuns)[0]
    for contas_str in df['CONTAS']:
        for nome, id_ in _extrair_nome_id_de_contas(str(contas_str)):
            if id_ == id_dono:
                return f'{nome} ({id_})'
    return ''


def detectar_alertas_dispositivos(
    lista_nome_df: list[tuple[str, pd.DataFrame]],
) -> dict[str, pd.DataFrame]:
    '''
    Detecta contas que aparecem nos dispositivos de mais de um arquivo.

    Cada arquivo representa a investigação de um ID específico. O alerta é
    gerado quando uma conta está presente nas listas de dispositivos de dois
    arquivos distintos — indicando conexão entre os investigados.

    Args:
        lista_nome_df: Lista de (nome_arquivo, df) retornados por preparar_df_dispositivos.

    Returns:
        dict com chave 'contas_cruzadas': DataFrame com CONTA e ARQUIVOS,
        ou DataFrame vazio se nenhuma conta cruzada for encontrada.
    '''
    conta_para_arquivos: dict[str, set] = {}
    conta_para_nome:     dict[str, str] = {}

    for nome_arquivo, df in lista_nome_df:
        for contas_str in df['CONTAS']:
            for nome_conta, id_conta in _extrair_nome_id_de_contas(str(contas_str)):
                conta_para_arquivos.setdefault(id_conta, set()).add(nome_arquivo)
                conta_para_nome[id_conta] = nome_conta

    cruzadas = [
        {
            'CONTA':    f'{conta_para_nome[id_]} ({id_})',
            'ARQUIVOS': ', '.join(sorted(arqs)),
        }
        for id_, arqs in conta_para_arquivos.items()
        if len(arqs) > 1
    ]
    df_c = (
        pd.DataFrame(cruzadas)
        if cruzadas
        else pd.DataFrame(columns=['CONTA', 'ARQUIVOS'])
    )
    return {'contas_cruzadas': df_c}


# Cabeçalhos para o PDF de dispositivos
_HEADERS_DISP = {
    'CODIGO_CENSURADO': 'Cód. Dispositivo',
    'SISTEMA':          'Sistema',
    'DISPOSITIVO':      'Tipo',
    'MODELO':           'Modelo',
    'VERSAO_OS':        'Versão OS',
    'SIMULADOR':        'Emulador',
    'REPETICOES':       'Repetições',
    'N_CONTAS':         'Nº Contas',
    'CONTAS':           'Contas',
}


def _secao_alertas_dispositivos(story: list, alertas: dict, largura_util: float) -> None:
    '''Adiciona ao story a seção de alertas de contas cruzadas entre arquivos.'''
    story.append(Paragraph('Alertas — Dispositivos em Comum', styles['Heading2']))

    df_cruzadas = alertas.get('contas_cruzadas', pd.DataFrame())
    if not df_cruzadas.empty:
        story.append(_paragrafo_alerta(
            f'{len(df_cruzadas)} conta(s) aparecem nos dispositivos de múltiplos arquivos investigados.'
        ))
        cabecalhos = ['Conta', 'Aparece nos arquivos']
        dados = [
            [str(row['CONTA']), str(row['ARQUIVOS'])]
            for _, row in df_cruzadas.iterrows()
        ]
        df_temp  = pd.DataFrame(dados, columns=['CONTA', 'ARQUIVOS'])
        larguras = calcular_larguras_proporcional(df_temp, list(df_temp.columns), cabecalhos, largura_util)
        adicionar_tabela(story, _montar_linhas_alerta(cabecalhos, dados), larguras)
    else:
        story.append(_paragrafo_ok('Nenhum dispositivo em comum entre os jogadores investigados.'))


def gerar_pdf_dispositivos(
    titulo: str,
    lista_nome_df: list[tuple[str, pd.DataFrame]],
    alertas: dict,
) -> bytes:
    '''
    Gera relatório PDF de dispositivos (landscape A4).

    Estrutura:
    - Uma seção por arquivo (subtítulo + tabela de dispositivos)
    - Seção de alertas cruzados ao final

    Args:
        lista_nome_df: Lista de (nome_arquivo, df) processados por preparar_df_dispositivos.

    Returns:
        bytes do PDF pronto para download.
    '''
    buffer, doc, story = inicializar_pdf('', paisagem=True, titulo_completo=titulo)
    largura_util = doc.width

    story.append(Paragraph('Dispositivos', styles['Heading2']))

    for i, (_, df) in enumerate(lista_nome_df):
        titulo_secao = _inferir_titulo_investigacao(df) or f'Investigação {i + 1}'
        story.append(Paragraph(titulo_secao, styles['Heading3']))
        story.append(Paragraph(
            'Relação de dispositivos identificados na investigação. '
            'Os identificadores de dispositivo são parcialmente censurados para garantir '
            'conformidade com os padrões de proteção de dados. '
            'Cada linha representa um dispositivo único com as respectivas contas que o acessaram.',
            ESTILO_LEGENDA,
        ))
        colunas    = [c for c in _HEADERS_DISP if c in df.columns]
        cabecalhos = [_HEADERS_DISP[c] for c in colunas]
        larguras   = calcular_larguras_proporcional(df, colunas, cabecalhos, largura_util)
        linhas     = _montar_linhas(df, colunas, cabecalhos)
        adicionar_tabela(story, linhas, larguras)
        story.append(Spacer(1, 8))

    story.append(Spacer(1, 8))
    _secao_alertas_dispositivos(story, alertas, largura_util)

    return finalizar_pdf(buffer, doc, story).read()
