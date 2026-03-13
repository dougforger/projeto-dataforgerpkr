import pandas as pd
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Spacer

from .pdf_builder import (
    adicionar_alerta_compartilhamento,
    adicionar_tabela,
    finalizar_pdf,
    inicializar_pdf,
    montar_tabela_comuns,
)
from .pdf_config import (
    COLS_3,
    COLS_4,
    COLS_5,
    COLS_6,
    ESTILO_LEGENDA,
    LIMITE_MODALIDADE_CASH,
    MULTIPLICADOR_MOEDA,
    styles,
)


# -----------------------------------------------------
# PRÉ-PROCESSAMENTO
# -----------------------------------------------------

def preprocessar_dados(
    df_bruto: pd.DataFrame,
    df_clubes: pd.DataFrame,
    df_ligas: pd.DataFrame,
):
    """Faz merge com clubes e ligas, aplica multiplicador de moeda e remove
    linhas de torneio (ID_MODALIDADE > LIMITE_MODALIDADE_CASH).
    Retorna (df_processado, qtd_linhas_removidas)."""
    df = df_bruto.merge(
        df_clubes[['clube_id', 'clube_nome', 'liga_id', 'liga_nome']],
        left_on='ID_CLUBE',
        right_on='clube_id',
        how='left',
    ).drop(columns=['clube_id'])

    df = df.merge(
        df_ligas[['liga_id', 'handicap', 'moeda']],
        on='liga_id',
        how='left',
    )

    df = df.rename(columns={
        'clube_nome': 'NOME_CLUBE',
        'liga_id':    'ID_LIGA',
        'liga_nome':  'NOME_LIGA',
        'handicap':   'HANDICAP',
        'moeda':      'MOEDA',
    })

    df['HANDICAP']          = df['HANDICAP'].astype(float)
    df[['GANHOS', 'RAKE']]  = df[['GANHOS', 'RAKE']].mul(MULTIPLICADOR_MOEDA)

    qtd_antes = len(df)
    df        = df[df['ID_MODALIDADE'] <= LIMITE_MODALIDADE_CASH]
    return df, qtd_antes - len(df)


# -----------------------------------------------------
# ANÁLISE DE JOGADORES E MESAS
# -----------------------------------------------------

def resumo_por_jogador(df: pd.DataFrame) -> pd.DataFrame:
    """Agrupa por jogador e agrega mesas únicas, ganhos e rake.
    Retorna df com colunas ['Jogador ID', 'Jogador Nome', 'Clube Nome',
    'Total de Mesas', 'Ganhos (R$)', 'Rake (R$)']."""
    resumo = (
        df.groupby(['ID_JOGADOR', 'NOME_JOGADOR'])
        .agg(**{
            'Total de Mesas': ('ID_MESA', 'nunique'),
            'Ganhos (R$)':    ('GANHOS',  'sum'),
            'Rake (R$)':      ('RAKE',    'sum'),
        })
        .reset_index()
    )
    clube_por_jogador = (
        df.groupby('ID_JOGADOR')['NOME_CLUBE']
        .agg(lambda x: x.mode()[0] if not x.empty else '')
        .reset_index()
    )
    resumo = resumo.merge(clube_por_jogador, on='ID_JOGADOR', how='left')
    resumo = resumo.rename(columns={
        'ID_JOGADOR':   'Jogador ID',
        'NOME_JOGADOR': 'Jogador Nome',
        'NOME_CLUBE':   'Clube Nome',
    })
    return resumo[['Jogador ID', 'Jogador Nome', 'Clube Nome', 'Total de Mesas', 'Ganhos (R$)', 'Rake (R$)']]


def detectar_mesas_comuns(df: pd.DataFrame, resumo: pd.DataFrame):
    """Compara todos os pares de jogadores e detecta mesas em comum.
    Retorna (df_pares_com_percentual, conjunto_mesas_comuns)."""
    mesas_por_jogador = df.groupby('ID_JOGADOR')['ID_MESA'].apply(set)
    jogadores         = resumo['Jogador ID'].tolist()
    pares             = []
    mesas_comuns_total = set()

    for i in range(len(jogadores)):
        for j in range(i + 1, len(jogadores)):
            a, b         = jogadores[i], jogadores[j]
            mesas_comuns = mesas_por_jogador[a] & mesas_por_jogador[b]
            mesas_comuns_total |= mesas_comuns
            total_comuns = len(mesas_comuns)
            total_a = resumo.loc[resumo['Jogador ID'] == a, 'Total de Mesas'].values[0]
            total_b = resumo.loc[resumo['Jogador ID'] == b, 'Total de Mesas'].values[0]
            pares.append({
                'Jogador A':      df.loc[df['ID_JOGADOR'] == a, 'NOME_JOGADOR'].values[0],
                'Jogador B':      df.loc[df['ID_JOGADOR'] == b, 'NOME_JOGADOR'].values[0],
                'Mesas em Comum': total_comuns,
                '% do Jogador A': round(total_comuns / total_a * 100, 1) if total_a else 0,
                '% do Jogador B': round(total_comuns / total_b * 100, 1) if total_b else 0,
            })

    return pd.DataFrame(pares), mesas_comuns_total


def detectar_dispositivos_compartilhados(df: pd.DataFrame):
    """Retorna (df_dispositivos_unicos, codigos_compartilhados)."""
    df_disp               = df[['NOME_JOGADOR', 'CODIGO_DISPOSITIVO', 'DISPOSITIVO', 'SISTEMA']].drop_duplicates()
    contagem              = df.groupby('CODIGO_DISPOSITIVO')['ID_JOGADOR'].nunique()
    codigos_compartilhados = contagem[contagem > 1].index.tolist()
    return df_disp, codigos_compartilhados


def detectar_ips_compartilhados(df: pd.DataFrame):
    """Retorna (df_ips_unicos, ips_compartilhados)."""
    df_ips             = df[['NOME_JOGADOR', 'IP']].drop_duplicates()
    contagem           = df.groupby('IP')['ID_JOGADOR'].nunique()
    ips_compartilhados = contagem[contagem > 1].index.tolist()
    return df_ips, ips_compartilhados


# -----------------------------------------------------
# GERAÇÃO DE PDF
# -----------------------------------------------------

def gerar_pdf_snowflake(
    protocolo: str,
    df_pares: pd.DataFrame,
    df_sf_norm: pd.DataFrame,
    mesas_comuns: set,
    resumo_sf: pd.DataFrame,
    df_dispositivos: pd.DataFrame,
    df_ips: pd.DataFrame,
    df_geo: pd.DataFrame,
) -> bytes:
    """Gera o PDF do relatório Snowflake com seções de cash, dispositivos, IPs e geolocalização."""
    buffer, doc, story = inicializar_pdf(protocolo)

    # --------------------------------------------------
    # Cruzamento em Cash Games
    # --------------------------------------------------
    story.append(Paragraph('Cruzamento em Cash Games', styles['Heading1']))

    if not df_pares.empty:
        linhas_resumo = [['ID', 'Jogador', 'Clube', 'Total de Mesas', 'Ganhos (R$)', 'Rake (R$)']]
        for _, row in resumo_sf.iterrows():
            linhas_resumo.append([
                row['Player ID'], row['Player Name'], row['Club Name'],
                row['Total de Mesas'],
                f'R$ {row["Ganhos (R$)"]:.2f}',
                f'R$ {row["Rake (R$)"]:.2f}',
            ])
        story.append(Paragraph('Ganhos líquidos e rake gerado por cada conta nas mesas de cash game identificadas.', ESTILO_LEGENDA))
        adicionar_tabela(story, linhas_resumo, COLS_6)

        linhas_pares = [['Jogador A', 'Jogador B', 'Mesas em Comum', '% do Jogador A', '% do Jogador B']]
        for _, row in df_pares.iterrows():
            linhas_pares.append([
                row['Jogador A'], row['Jogador B'], row['Mesas em Comum'],
                f'{row["% do Jogador A"]:.2f}%', f'{row["% do Jogador B"]:.2f}%',
            ])
        story.append(Paragraph('Cruzamento par a par: número de mesas compartilhadas e percentual em relação ao total de cada conta.', ESTILO_LEGENDA))
        adicionar_tabela(story, linhas_pares, COLS_5)
        story.append(Paragraph('Mesas de cash game em comum, com nome da mesa, IDs dos jogadores e link para o histórico de mãos.', ESTILO_LEGENDA))
        adicionar_tabela(story, montar_tabela_comuns(df_sf_norm, mesas_comuns, coluna_nome='NOME_MESA'), COLS_4)
    else:
        story.append(Paragraph('Sem registro de cash game.', styles['Normal']))

    # --------------------------------------------------
    # Dispositivos
    # --------------------------------------------------
    story.append(Spacer(1, 20))
    story.append(Paragraph('Dispositivos', styles['Heading1']))
    story.append(Spacer(1, 6))

    estilo_wrap  = ParagraphStyle('wrap', parent=styles['Normal'], wordWrap='LTR', fontSize=8)
    linhas_disp  = [['Jogador', 'Cód. Dispositivo', 'Dispositivo', 'Sistema']]
    for _, row in df_dispositivos.iterrows():
        linhas_disp.append([
            row['NOME_JOGADOR'],
            Paragraph(str(row['CODIGO_DISPOSITIVO']), estilo_wrap),
            str(row['DISPOSITIVO']),
            str(row['SISTEMA']),
        ])
    story.append(Paragraph('Dispositivos únicos registrados por cada conta. Dispositivos compartilhados entre contas distintas são sinalizados abaixo.', ESTILO_LEGENDA))
    adicionar_tabela(story, linhas_disp, COLS_4, espacamento=8)
    adicionar_alerta_compartilhamento(
        story, df_dispositivos,
        coluna_grupo='CODIGO_DISPOSITIVO', coluna_jogador='NOME_JOGADOR',
        msg_alerta='<b>⚠️ {n} dispositivo(s) compartilhado(s) entre os jogadores.</b>',
        msg_ok='✅ Nenhum dispositivo compartilhado.',
    )

    # --------------------------------------------------
    # Endereços IP
    # --------------------------------------------------
    story.append(Spacer(1, 20))
    story.append(Paragraph('Endereços IP', styles['Heading1']))
    story.append(Spacer(1, 6))

    linhas_ip = [['Jogador', 'IP', 'Cidade', 'Estado', 'País']]
    for _, row in df_ips.iterrows():
        linhas_ip.append([
            row['NOME_JOGADOR'], str(row['IP']),
            str(row.get('CIDADE') or '—'),
            str(row.get('ESTADO') or '—'),
            str(row.get('PAIS')   or '—'),
        ])
    story.append(Paragraph('Endereços IP únicos por conta com localização geográfica estimada. IPs compartilhados entre contas distintas são sinalizados abaixo.', ESTILO_LEGENDA))
    adicionar_tabela(story, linhas_ip, COLS_5, espacamento=8)
    adicionar_alerta_compartilhamento(
        story, df_ips,
        coluna_grupo='IP', coluna_jogador='NOME_JOGADOR',
        msg_alerta='<b>⚠️ {n} IP(s) compartilhado(s) entre os jogadores.</b>',
        msg_ok='✅ Nenhum IP compartilhado.',
    )

    # --------------------------------------------------
    # Geolocalização (GPS)
    # --------------------------------------------------
    story.append(Spacer(1, 20))
    story.append(Paragraph('Geolocalização (GPS)', styles['Heading1']))
    story.append(Spacer(1, 6))

    df_geo_dedup = (
        df_geo[['NOME_JOGADOR', 'CIDADE', 'ESTADO', 'PAIS']].drop_duplicates()
        if not df_geo.empty else pd.DataFrame()
    )
    if df_geo_dedup.empty:
        story.append(Paragraph('Sem registros de geolocalização.', styles['Normal']))
    else:
        linhas_geo = [['Jogador', 'Cidade', 'Estado', 'País']]
        for _, row in df_geo_dedup.iterrows():
            linhas_geo.append([
                row['NOME_JOGADOR'],
                str(row.get('CIDADE') or '—'),
                str(row.get('ESTADO') or '—'),
                str(row.get('PAIS')   or '—'),
            ])
        story.append(Paragraph('Localização geográfica das contas obtida via coordenadas GPS registradas nos dispositivos.', ESTILO_LEGENDA))
        adicionar_tabela(story, linhas_geo, COLS_4, espacamento=8)

        cidades_comuns = df_geo_dedup.groupby('CIDADE')['NOME_JOGADOR'].nunique()
        cidades_comuns = cidades_comuns[cidades_comuns > 1].index.tolist()
        if cidades_comuns:
            story.append(Paragraph(
                f'<b>⚠️ Jogadores na mesma cidade: {", ".join(cidades_comuns)}</b>',
                styles['Normal'],
            ))
        else:
            story.append(Paragraph('✅ Nenhuma localização em comum.', styles['Normal']))

    return finalizar_pdf(buffer, doc, story)
