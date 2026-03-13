import pandas as pd
from reportlab.platypus import PageBreak, Paragraph, Spacer

from .pdf_builder import (
    adicionar_tabela,
    finalizar_pdf,
    inicializar_pdf,
    montar_tabela_comuns,
)
from .pdf_config import COLS_3, COLS_4, COLS_5, COLS_6, ESTILO_LEGENDA, ESTILO_PARAGRAFO, styles


# -----------------------------------------------------
# ANÁLISE DE CASH GAME
# -----------------------------------------------------

def analisar_cash(df: pd.DataFrame):
    """Calcula resumo por jogador, pares e mesas em comum para Cash Game.
    Retorna (resumo_cash, df_pares_cash, mesas_comuns_cash)."""
    resumo_cash = df.groupby(['Player ID', 'Player Name', 'Club Name']).agg(
        Total_Mesas    =('Game ID',       'nunique'),
        Ganhos_Liquido =('chip change',   'sum'),
        Rake           =('Game Fee change','sum'),
    ).reset_index()
    resumo_cash.columns = ['Player ID', 'Player Name', 'Club Name', 'Total de Mesas', 'Ganhos (R$)', 'Rake (R$)']

    mesas_por_jogador = df.groupby('Player ID')['Game ID'].nunique().reset_index()
    mesas_por_jogador.columns = ['Player ID', 'Total de Mesas']
    maos_por_jogador  = df.groupby('Player ID')['Hand ID'].apply(set)
    jogadores         = resumo_cash['Player ID'].unique().tolist()

    pares              = []
    mesas_comuns_total = set()

    for i in range(len(jogadores)):
        for j in range(i + 1, len(jogadores)):
            a, b         = jogadores[i], jogadores[j]
            maos_comuns  = maos_por_jogador[a] & maos_por_jogador[b]
            mesas_comuns = df[df['Hand ID'].isin(maos_comuns)]['Game ID'].unique()
            if len(mesas_comuns) == 0:
                continue
            mesas_comuns_total |= set(mesas_comuns)
            total_comuns = len(mesas_comuns)
            total_a = mesas_por_jogador.loc[mesas_por_jogador['Player ID'] == a, 'Total de Mesas'].values[0]
            total_b = mesas_por_jogador.loc[mesas_por_jogador['Player ID'] == b, 'Total de Mesas'].values[0]
            pares.append({
                'Jogador A':      df.loc[df['Player ID'] == a, 'Player Name'].values[0],
                'Jogador B':      df.loc[df['Player ID'] == b, 'Player Name'].values[0],
                'Mesas em Comum': total_comuns,
                '% do Jogador A': round(total_comuns / total_a * 100, 1),
                '% do Jogador B': round(total_comuns / total_b * 100, 1),
            })

    return resumo_cash, pd.DataFrame(pares), mesas_comuns_total


# -----------------------------------------------------
# ANÁLISE DE TORNEIOS (MTT)
# -----------------------------------------------------

def analisar_torneios(df: pd.DataFrame):
    """Calcula resumo por jogador, pares e torneios em comum.
    Retorna (resumo_mtt, df_pares_mtt, torneios_comuns)."""
    resumo_mtt = df.groupby(['Player ID', 'Player Name', 'Club Name'])['Game ID'].nunique().reset_index()
    resumo_mtt.columns = ['Player ID', 'Player Name', 'Club Name', 'Total de Torneios']

    mesas_por_jogador = df.groupby('Player Name')['Game ID'].apply(set)
    jogadores         = resumo_mtt['Player Name'].unique().tolist()
    pares             = []
    torneios_comuns   = set()

    if len(jogadores) > 1:
        for i in range(len(jogadores)):
            for j in range(i + 1, len(jogadores)):
                a, b   = jogadores[i], jogadores[j]
                comuns = mesas_por_jogador[a] & mesas_por_jogador[b]
                torneios_comuns |= comuns
                total_comuns = len(comuns)
                total_a = resumo_mtt.loc[resumo_mtt['Player Name'] == a, 'Total de Torneios'].values[0]
                total_b = resumo_mtt.loc[resumo_mtt['Player Name'] == b, 'Total de Torneios'].values[0]
                pares.append({
                    'Jogador A':         df.loc[df['Player Name'] == a, 'Player Name'].values[0],
                    'Jogador B':         df.loc[df['Player Name'] == b, 'Player Name'].values[0],
                    'Torneios em Comum': total_comuns,
                    '% do Jogador A':    round(total_comuns / total_a * 100, 1),
                    '% do Jogador B':    round(total_comuns / total_b * 100, 1),
                })

    return resumo_mtt, pd.DataFrame(pares), torneios_comuns


def detalhar_torneio(df: pd.DataFrame, game_id):
    """Filtra por Game ID, separa MttPrize e KOPrize, agrega e calcula Total.
    Retorna (resumo_torneio, detalhe_torneio)."""
    df_torneio = df[
        (df['Game ID'] == game_id) &
        (df['Event'].isin(['MttPrize', 'MttKOPrize', 'SAT MTT Prize']))
    ].copy().sort_values('Game ID')

    df_prize = (
        df_torneio[(df_torneio['Event'] == 'MttPrize') | (df_torneio['Event'] == 'SAT MTT Prize')]
        .groupby(['Player ID', 'Player Name', 'Club Name'])['chip change']
        .sum().reset_index()
        .rename(columns={'chip change': 'Prize'})
    )
    df_ko = (
        df_torneio[df_torneio['Event'] == 'MttKOPrize']
        .groupby(['Player ID', 'Player Name', 'Club Name'])['chip change']
        .sum().reset_index()
        .rename(columns={'chip change': "KO's"})
    )

    resumo_torneio          = df_prize.merge(df_ko, on=['Player ID', 'Player Name', 'Club Name'], how='left').fillna(0)
    resumo_torneio['Total'] = resumo_torneio['Prize'] + resumo_torneio["KO's"]
    return resumo_torneio, df_torneio


# -----------------------------------------------------
# GERAÇÃO DE PDF
# -----------------------------------------------------

def gerar_pdf(
    protocolo: str,
    df_pares_cash: pd.DataFrame,
    df_pares_mtt: pd.DataFrame,
    df_cash: pd.DataFrame,
    df_mtt: pd.DataFrame,
    mesas_comuns_cash: set,
    torneios_comuns: set,
    resumo_cash: pd.DataFrame,
    resumo_mtt: pd.DataFrame,
    torneio_selecionado=None,
    resumo_torneio: pd.DataFrame = None,
    df_torneio: pd.DataFrame = None,
) -> bytes:
    """Gera o PDF do relatório Backend com seções de Cash Game e Torneios."""
    buffer, doc, story = inicializar_pdf(protocolo)

    # --------------------------------------------------
    # Cruzamento em Cash Games
    # --------------------------------------------------
    story.append(Paragraph('Cruzamento em Cash Games', styles['Heading1']))

    if not df_pares_cash.empty:
        linhas_resumo = [['ID', 'Jogador', 'Clube', 'Total de Mesas', 'Ganhos (R$)', 'Rake (R$)']]
        for _, row in resumo_cash.iterrows():
            linhas_resumo.append([
                row['Player ID'], row['Player Name'], row['Club Name'], row['Total de Mesas'],
                f'R$ {row["Ganhos (R$)"]:.2f}', f'R$ {row["Rake (R$)"]:.2f}',
            ])
        story.append(Paragraph('Ganhos líquidos e rake gerado por cada conta nas mesas de cash game identificadas.', ESTILO_LEGENDA))
        adicionar_tabela(story, linhas_resumo, COLS_6)

        linhas_pares = [['Jogador A', 'Jogador B', 'Mesas em Comum', '% do Jogador A', '% do Jogador B']]
        for _, row in df_pares_cash.iterrows():
            linhas_pares.append([
                row['Jogador A'], row['Jogador B'], row['Mesas em Comum'],
                f'{row["% do Jogador A"]:.2f}%', f'{row["% do Jogador B"]:.2f}%',
            ])
        story.append(Paragraph('Cruzamento par a par: número de mesas compartilhadas e percentual em relação ao total de cada conta.', ESTILO_LEGENDA))
        adicionar_tabela(story, linhas_pares, COLS_5)
        story.append(Paragraph('Mesas de cash game em comum, com IDs dos jogadores e link para o histórico de mãos.', ESTILO_LEGENDA))
        adicionar_tabela(story, montar_tabela_comuns(df_cash, mesas_comuns_cash), COLS_3)
    else:
        story.append(Paragraph('Sem registro de cash game', styles['Normal']))

    story.append(Spacer(1, 12))

    # --------------------------------------------------
    # Cruzamento em Torneios
    # --------------------------------------------------
    story.append(PageBreak())
    story.append(Paragraph('Cruzamento em Torneios', styles['Heading1']))

    if not df_pares_mtt.empty:
        story.append(Paragraph(
            "O cruzamento de torneios leva em consideração os torneios em comum onde as contas se registraram. "
            "Não necessariamente considera que as contas jogaram na mesma mesa. Para mais detalhes dos torneios comuns, "
            "comparar as contas na aba \"Player Information > Cheating investigation > Search Same Data With Players\" "
            "adicionando os ID's e buscando por \"Game\".",
            ESTILO_PARAGRAFO,
        ))
        story.append(Spacer(1, 12))

        linhas_resumo_mtt = [['ID', 'Jogador', 'Clube', 'Total de Torneios']]
        for _, row in resumo_mtt.iterrows():
            linhas_resumo_mtt.append([row['Player ID'], row['Player Name'], row['Club Name'], row['Total de Torneios']])
        story.append(Paragraph('Quantidade de torneios em que cada conta participou no período analisado.', ESTILO_LEGENDA))
        adicionar_tabela(story, linhas_resumo_mtt, COLS_4)

        linhas_pares_mtt = [['Jogador A', 'Jogador B', 'Torneios em Comum', '% do Jogador A', '% do Jogador B']]
        for _, row in df_pares_mtt.iterrows():
            linhas_pares_mtt.append([
                row['Jogador A'], row['Jogador B'], row['Torneios em Comum'],
                f'{row["% do Jogador A"]:.2f}%', f'{row["% do Jogador B"]:.2f}%',
            ])
        story.append(Paragraph('Cruzamento par a par: número de torneios com inscrição simultânea e percentual em relação ao total de cada conta.', ESTILO_LEGENDA))
        adicionar_tabela(story, linhas_pares_mtt, COLS_5)
        story.append(Paragraph('Torneios com inscrição simultânea das contas analisadas, com link para verificação no sistema.', ESTILO_LEGENDA))
        adicionar_tabela(story, montar_tabela_comuns(df_mtt, torneios_comuns), COLS_3)
    else:
        story.append(Paragraph('Sem registros de torneios.', styles['Normal']))

    # --------------------------------------------------
    # Detalhamento do torneio selecionado
    # --------------------------------------------------
    if torneio_selecionado is not None and resumo_torneio is not None and not resumo_torneio.empty:
        story.append(PageBreak())
        story.append(Paragraph(f'Detalhamento do Torneio: {torneio_selecionado}', styles['Heading2']))
        story.append(Spacer(1, 6))

        linhas_resumo_torneio = [['Jogador', 'Clube', 'Prize', "KO's", 'Total']]
        for _, row in resumo_torneio.iterrows():
            linhas_resumo_torneio.append([
                row['Player Name'], row['Club Name'],
                f'{row["Prize"]:.2f}', f'{row["KO\'s"]:.2f}', f'{row["Total"]:.2f}',
            ])
        story.append(Paragraph('Prêmio, eliminações (KO) e total recebido por cada conta no torneio selecionado.', ESTILO_LEGENDA))
        adicionar_tabela(story, linhas_resumo_torneio, COLS_5)

        if df_torneio is not None and not df_torneio.empty:
            tem_horario = 'Record time' in df_torneio.columns
            df_detalhe = df_torneio.sort_values('Record time') if tem_horario else df_torneio
            linhas_detalhe = [['Horário (SP)', 'Jogador', 'Clube', 'Evento', 'Ganhos'] if tem_horario else ['Jogador', 'Clube', 'Evento', 'Ganhos']]
            for _, row in df_detalhe.iterrows():
                if tem_horario:
                    horario = pd.to_datetime(row['Record time']) - pd.Timedelta(hours=11)
                    horario_str = horario.strftime('%d/%m/%Y %H:%M')
                    linhas_detalhe.append([
                        horario_str,
                        row['Player Name'], row['Club Name'],
                        row['Event'], f'{row["chip change"]:.2f}',
                    ])
                else:
                    linhas_detalhe.append([
                        row['Player Name'], row['Club Name'],
                        row['Event'], f'{row["chip change"]:.2f}',
                    ])
            story.append(Paragraph('Registro linha a linha dos eventos de premiação no torneio selecionado, ordenados por horário (fuso São Paulo).', ESTILO_LEGENDA))
            adicionar_tabela(story, linhas_detalhe, COLS_5 if tem_horario else COLS_4)

    story.append(Spacer(1, 12))

    return finalizar_pdf(buffer, doc, story)
