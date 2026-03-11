import time
import requests
import io
import streamlit as st
import pandas as pd
from pathlib import Path

from utils.arquivo_utils import carregar_xlsx
# -----------------------------------------------------
# BIBLIOTECAS PARA GERAR O PDF DO RELATÓRIO
# -----------------------------------------------------
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont

# -----------------------------------------------------
# CAMINHOS DOS DIRETÓRIOS
# -----------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
FONT_DIR = BASE_DIR / 'fonts'

print(FONT_DIR)

# -----------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# -----------------------------------------------------
st.set_page_config(
    page_title='Análises',
    page_icon='📈',
    layout='wide',
    initial_sidebar_state='collapsed'
)

st.title('📈 Análises')
st.markdown('---')

# -----------------------------------------------------
# PERSONALIZAÇÃO DO PDF
# -----------------------------------------------------
pdfmetrics.registerFont(TTFont('CalibriLight', FONT_DIR / 'calibril.ttf'))
pdfmetrics.registerFont(TTFont('CalibriLight-Bold', FONT_DIR / 'calibrib.ttf'))
pdfmetrics.registerFont(TTFont('CalibriLight-Italic', FONT_DIR / 'calibrili.ttf'))
pdfmetrics.registerFont(TTFont('CalibriLight-BoldItalic', FONT_DIR / 'calibriz.ttf'))
registerFontFamily('CalibriLight',
                   normal='CalibriLight',
                   bold='CalibriLight-Bold',
                   italic='CalibriLight-Italic',
                   boldItalic='CalibriLight-BoldItalic')

styles = getSampleStyleSheet()
largura_pagina = A4[0] - 4*cm
altura_pagina = A4[1] - 3*cm
tabela_2_colunas = [largura_pagina * 0.5, largura_pagina * 0.5]
tabela_3_colunas = [largura_pagina * 0.3, largura_pagina * 0.3, largura_pagina * 0.4]
tabela_5_colunas = [largura_pagina * 0.2, largura_pagina * 0.2, largura_pagina * 0.2, largura_pagina * 0.2, largura_pagina * 0.2]

estilo_paragrafo = ParagraphStyle(
    'paragrafo_custom',
    parent=styles['Normal'],
    alignment=TA_JUSTIFY,
    spaceAfter=8,
    spaceBefore=8,
    firstLineIndent=20,
    wordWrap='LTR',
    fontName='CalibriLight'
)

estilo_tabela1 = TableStyle([
    ('FONTNAME', (0, 0), (-1, 0), 'CalibriLight-BoldItalic'),
    ('FONTNAME', (0, 1), (-1, -1), 'CalibriLight'),
    ('BACKGROUND', (0, 0), (-1,0), colors.grey),
    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
    ('GRID', (0,0), (-1,-1), 0.5, colors.black),
    ('VALIGN', (0, 0), (-1, -1), 'TOP')
])

styles['Title'].alignment = TA_LEFT

img = ImageReader(BASE_DIR / 'img' / 'LOGO PRETO.png')
# -----------------------------------------------------
# FUNÇÕES DE APOIO.
# -----------------------------------------------------

# Função que guarda os dados em cache para o csv
@st.cache_data
def carregar_dados(arquivo):
    return pd.read_csv(arquivo)
@st.dialog('📄 Relatório', width='large')

# Função para gerar relatório em markdown
def gerar_relatorio(pares_cash, resumo_cash, pares_mtt, resumo_mtt, torneio_selecionado, resumo_mesa_mtt):
    relatorio = '### Cruzamento de Cash Game: \n'

    if not pares_cash.empty:
        relatorio += '| Jogador | Total de Mesas | Clube | Ganhos (R$) | Rake (R$) |\n|---------|---------------|---------|---------|---------|\n'
        for _, row in resumo_cash.iterrows():
            relatorio += f'| {row['Player Name']} | {row['Club Name']} | {row['Total de Mesas']} | {row['Ganhos (R$)']:.2f} | {row['Rake (R$)']:.2f} |\n'
        relatorio += '\n'
        relatorio += '| Jogador A | Jogador B | Mesas em Comum | % Jogador A | % Jogador B |\n'
        relatorio += '|-----------|-----------|----------------|-------------|-------------|\n'
        for _, row in pares_cash.iterrows():
            relatorio += f"| {row['Jogador A']} | {row['Jogador B']} | {row['Mesas em Comum']} | {row['% do Jogador A']}% | {row['% do Jogador B']}% |\n"
    else:
        relatorio += 'Sem registros em mesas de cash game.\n'

    relatorio += '\n---\n### Cruzamento de Torneios:\n'
    if not pares_mtt.empty:
        relatorio += '| Jogador | Total de Torneios | Clube | Ganhos (R$) | Rake (R$) |\n|---------|---------------|---------|---------|---------|\n'
        for _, row in resumo_mtt.iterrows():
            relatorio += f'| {row['Player Name']} | {row['Club Name']} | {row['Total de Torneios']} | {row['Ganhos (R$)']:.2f} | {row['Rake (R$)']:.2f} |\n'
        relatorio += '\n'
        relatorio += '| Jogador A | Jogador B | Torneios em Comum | % Jogador A | % Jogador B |\n'
        relatorio += '|-----------|-----------|-------------------|-------------|-------------|\n'
        for _, row in pares_mtt.iterrows():
            relatorio += f"| {row['Jogador A']} | {row['Jogador B']} | {row['Torneios em Comum']} | {row['% do Jogador A']}% | {row['% do Jogador B']}% |\n"
        relatorio += f'\n#### Detalhamento do Game ID: {torneio_selecionado}\n'
        relatorio += '| Player Name | Club Name | Prize | KOs | Total |\n'
        relatorio += '|-------------|-----------|-------|-----|-------|\n'
        for _, row in resumo_mesa_mtt.iterrows():
            relatorio += f'| {row['Player Name']} | {row['Club Name']} | {row['Prize']:.2f} | {row['KO\'s']:.2f} | {row['Total']:.2f} |\n'
    else:
        relatorio += 'Sem registros de torneios.\n'

    st.code(relatorio, language='text')
    obesrvacoes = st.text_area('Adicione suas obsevações aqui')

    if obesrvacoes:
        relatorio += '\n---\n### Observações:\n'
        relatorio_final = relatorio + obesrvacoes
        st.code(relatorio_final, language='text')

def montar_tabela_comuns(df, mesas_comuns):
    dados = [['ID Mesa', 'Jogadores', 'Link']]
    for mesa in sorted(mesas_comuns, reverse=True):
        df_mesa = df[df['Game ID'] == mesa]
        ids_jogadores = df_mesa['Player ID'].unique().tolist()
        player_ids_url = '&'.join([str(id) for id in ids_jogadores])
        link = f'https://console.supremapoker.net/game/GameDetail?backupOnly=0&dateFilter=16&matchID={mesa}&page=1&pageSize=100&playerIDs={player_ids_url}'
        dados.append([Paragraph(str(mesa), styles['Normal']),
                      Paragraph(', '.join([str(id) for id in ids_jogadores]), styles['Normal']),
                      Paragraph(f'<a href="{link}" color="blue"><u>Link para o Hand History</u></a>', styles['Normal'])
                      ])
    return dados

def criar_marca_dagua(img):
    def marca_dagua(canvas, doc):
        canvas.saveState()
        canvas.setFillAlpha(0.1)
        pag_largura, pag_altura = A4
        x = (pag_largura - largura_pagina) / 2
        y = (pag_altura - altura_pagina) / 2
        canvas.drawImage(img, x, y, width=largura_pagina, height=altura_pagina, mask='auto', preserveAspectRatio=True)
        canvas.restoreState()
    return marca_dagua

def gerar_pdf(protocolo, pares_cash, pares_mtt, df_cash, df_mtt, mesas_comuns_cash, mesas_comuns_mtt):
    for style in styles.byName.values():
        style.fontName = 'CalibriLight'

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    # styles = getSampleStyleSheet()
    story = []
    # Título
    story.append(Paragraph(f'Protocolo #{protocolo}', styles['Title']))
    story.append(Spacer(1, 12))

    # Estilo das tabelas

    # Cruzamento em Cash Game
    story.append(Paragraph('Cruzamento em Cash Games', styles['Heading1']))
    if not pares_cash.empty:
        # Tabela do resumo (jogador, total de mesas)
        dados_resumo_cash = [['Jogador', 'Clube', 'Total de Mesas', 'Ganhos (R$)', 'Rake (R$)']]
        for _, row in resumo_cash.iterrows():
            dados_resumo_cash.append([row['Player Name'], row['Club Name'], row['Total de Mesas'], f'R$ {row['Ganhos (R$)']:.2f}', f'R$ {row['Rake (R$)']:.2f}'])
        tabela_resumo_cash = Table(dados_resumo_cash, colWidths=tabela_5_colunas)
        tabela_resumo_cash.setStyle(estilo_tabela1)
        story.append(tabela_resumo_cash)
        story.append(Spacer(1, 12))
        
        # Tabela de pares (jogador a - jogador b - mesas comum - % de a - % de b)
        dados_cash = [['Jogador A', 'Jogador B', 'Mesas em Comum', '% do Jogador A', '% do Jogador B']]
        for _, row in pares_cash.iterrows():
            dados_cash.append([row['Jogador A'], row['Jogador B'], row['Mesas em Comum'], f'{row['% do Jogador A']:.2f}%', f'{row['% do Jogador B']:.2f}%'])
        tabela_cash = Table(dados_cash, colWidths=tabela_5_colunas)
        tabela_cash.setStyle(estilo_tabela1)
        story.append(tabela_cash)
        story.append(Spacer(1, 12))
        
        # Tabela de mesas comuns (mesa - jogadores - link)
        dados_mesa_cash = montar_tabela_comuns(df_cash, mesas_comuns_cash)
        tabela_mesas_cash = Table(dados_mesa_cash, colWidths=tabela_3_colunas)
        tabela_mesas_cash.setStyle(estilo_tabela1)
        story.append(tabela_mesas_cash)
    else:
        story.append(Paragraph('Sem registro de cash game', styles['Normal']))
    
    story.append(Spacer(1, 12))

    # Cruzamento em Torneios
    story.append(PageBreak())
    story.append(Paragraph('Cruzamento em Torneios', styles['Heading1']))
    if not pares_mtt.empty:
        story.append(Paragraph('''
                               O cruzamento de torneios leva em consideração os torneios em comum onde as contas se registraram. 
                               Não necessariamente considera que as contas jogaram na mesma mesa. Para mais detalhes dos torneios comuns, 
                               comparar as contas na aba "Player Information > Cheating investigation > Search Same Data With Players" adicionando os ID\'s e buscando por "Game".
                               ''',
                               estilo_paragrafo))
        story.append(Spacer(1, 12))
        
        dados_resumo_mtt = [['Jogador', 'Clube', 'Total de Torneios']]
        for _, row in resumo_mtt.iterrows():
            dados_resumo_mtt.append([row['Player Name'], row['Club Name'], row['Total de Torneios']])
        tabela_resumo_mtt = Table(dados_resumo_mtt, colWidths=tabela_3_colunas)
        tabela_resumo_mtt.setStyle(estilo_tabela1)
        story.append(tabela_resumo_mtt)
        story.append(Spacer(1, 12))
        
        dados_mtt = [['Jogador A', 'Jogador B', 'Torneios em Comum', '% do Jogador A', '% do Jogador B']]
        for _,row in pares_mtt.iterrows():
            dados_mtt.append([row['Jogador A'], row['Jogador B'], row['Torneios em Comum'], f'{row['% do Jogador A']:.2f}%', f'{row['% do Jogador B']:.2f}%'])
        tabela_mtt = Table(dados_mtt, colWidths=tabela_5_colunas)
        tabela_mtt.setStyle(estilo_tabela1)
        story.append(tabela_mtt)
        story.append(Spacer(1, 12))

        dados_mesas_mtt = montar_tabela_comuns(df_mtt, mesas_comuns_mtt)
        tabela_mesas_mtt = Table(dados_mesas_mtt, colWidths=tabela_3_colunas)
        tabela_mesas_mtt.setStyle(estilo_tabela1)
        story.append(tabela_mesas_mtt)
    else:
        story.append(Paragraph('Sem registros de torneios.', styles['Normal']))

    story.append(Spacer(1, 12))

    doc.build(story, onFirstPage=criar_marca_dagua(img), onLaterPages=criar_marca_dagua(img))
    buffer.seek(0)
    return buffer


# -----------------------------------------------------
# CRIAÇÃO DAS ABAS DA PÁGINA
# -----------------------------------------------------
aba_backend, aba_snowflake = st.tabs(['Backend', 'Snowflake'])
with aba_backend:
    if 'df_backend' not in st.session_state:
        st.session_state.df_backend = None

    # -----------------------------------------------------
    # CARREGAMENTO DOS ARQUIVOS
    # -----------------------------------------------------
    col_upload_backend, col_limpacash_backend = st.columns([4,1])
    with col_upload_backend:
        upload_files = st.file_uploader(
            'Selecione o(s) arquivo(s) para fazer o upload e carregar os dados.',
            type=['xls', 'xlsx'],
            accept_multiple_files=True
        )
    
    with col_limpacash_backend:
        st.space()
        if st.button('🗑️ Limpar dados', key='backend-limpa-cache'):
            st.session_state.df_backend = None
            st.cache_data.clear()
            st.rerun()

    if upload_files:
        st.session_state.df_backend = carregar_xlsx(upload_files)
        st.session_state.df_backend[['Game ID']] = st.session_state.df_backend['Association'].str.extract(r'Game ID: (\d+)')
        st.session_state.df_backend[['Hand ID']] = st.session_state.df_backend['Association'].str.extract(r'Hand ID: (\d+)')
        colunas_uteis = ['Player ID', 'Player Name', 'Club ID', 'Club Name', 'Union ID', 'Union Name', 'Event', 'Association', 'Game ID', 'Hand ID', 'chip change', 'Game Fee change']
        st.session_state.df_backend = st.session_state.df_backend[colunas_uteis]
        st.success(f'✅ {len(upload_files)} arquivo(s) carregado(s)! {len(st.session_state.df_backend)} linhas encontradas')
        # st.dataframe(st.session_state.df_backend.head())
    
    # Definição dos DataFrames vazios.
    df_cash = pd.DataFrame()
    df_pares_cash = pd.DataFrame()
    resumo_cash = pd.DataFrame()
    mesas_comuns_cash = pd.DataFrame()
    total_mesas_comuns_cash = set()
    df_mtt =pd.DataFrame()
    df_pares_mtt = pd.DataFrame()
    resumo_mtt = pd.DataFrame()
    total_mesas_comuns_mtt = pd.DataFrame()
    mesas_comuns_mtt = pd.DataFrame()
    mesas_selecionada_mtt = ()
    df_mesa_mtt_resumo = pd.DataFrame()

    if st.session_state.df_backend is None:
        st.empty()
        
    else:
        col_cash, col_mtt = st.columns(2)
        with col_cash:
            st.subheader('Cash Game')

            df_cash = st.session_state.df_backend[st.session_state.df_backend['Event'] == 'gameResult'].copy()
            st.info(f'🎯 {len(df_cash)} mãos em cash game encontradas.')

            if not df_cash.empty:
                st.dataframe(df_cash.head())

                resumo_cash = df_cash.groupby(['Player ID', 'Player Name', 'Club Name']).agg(
                    Total_Mesas = ('Game ID', 'nunique'),
                    Ganhos_Liquido = ('chip change', 'sum'),
                    Rake = ('Game Fee change', 'sum')
                ).reset_index()

                resumo_cash.columns = ['Player ID', 'Player Name', 'Club Name', 'Total de Mesas', 'Ganhos (R$)', 'Rake (R$)']
                st.dataframe(resumo_cash,
                             hide_index=True,
                             width='stretch',
                             column_config = {
                                 'Ganhos (R$)': st.column_config.NumberColumn(format='localized'),
                                 'Rake (R$)': st.column_config.NumberColumn(format='localized')
                             })
                
                mesas_por_jogador_cash = df_cash.groupby('Player ID')['Game ID'].nunique().reset_index()
                mesas_por_jogador_cash.columns = ['Player ID', 'Total de Mesas']
                # print(mesas_por_jogador_cash)
                maos_por_jogador_cash = df_cash.groupby('Player ID')['Hand ID'].apply(set)
                jogadores_cash = resumo_cash['Player ID'].unique().tolist()

                lista_jogadores_cash = ['Todos'] + sorted(df_cash['Player Name'].unique().tolist())

                # print(jogadores_cash)
                pares_cash = []

                for i in range(len(jogadores_cash)):
                    for j in range(i + 1, len(jogadores_cash)):
                        a = jogadores_cash[i]
                        b = jogadores_cash[j]
                        maos_comuns_cash = maos_por_jogador_cash[a] & maos_por_jogador_cash[b]
                        mesas_comuns_cash = df_cash[df_cash['Hand ID'].isin(maos_comuns_cash)]['Game ID'].unique()
                        if len(mesas_comuns_cash) == 0:
                            continue
                        total_mesas_comuns_cash |= set(mesas_comuns_cash)
                        # total_mesas_comuns_cash |= mesas_comuns_cash
                        total_comuns = len(mesas_comuns_cash)
                        total_a = mesas_por_jogador_cash.loc[mesas_por_jogador_cash['Player ID'] == a, 'Total de Mesas'].values[0]
                        total_b = mesas_por_jogador_cash.loc[mesas_por_jogador_cash['Player ID'] == b, 'Total de Mesas'].values[0]
                        pares_cash.append({
                            'Jogador A': df_cash.loc[df_cash['Player ID'] == a, 'Player Name'].values[0],
                            'Jogador B': df_cash.loc[df_cash['Player ID'] == b, 'Player Name'].values[0],
                            'Mesas em Comum': total_comuns,
                            '% do Jogador A': round(total_comuns / total_a * 100, 1),
                            '% do Jogador B': round(total_comuns / total_b * 100, 1),
                })
                        
                df_pares_cash = pd.DataFrame(pares_cash)

                col_filtro_a, col_filtro_b = st.columns(2)
                with col_filtro_a:
                    filtro_a = st.selectbox('Jogador A', lista_jogadores_cash)
                with col_filtro_b:
                    filtro_b = st.selectbox('Jogador B', lista_jogadores_cash)

                df_pares_cash_filtrado = df_pares_cash.copy()

                if filtro_a != 'Todos':
                    df_pares_cash_filtrado = df_pares_cash_filtrado[
                        (df_pares_cash_filtrado['Jogador A'] == filtro_a) |
                        (df_pares_cash_filtrado['Jogador B'] == filtro_a)
                    ]
                if filtro_b != 'Todos':
                    df_pares_cash_filtrado = df_pares_cash_filtrado[
                        (df_pares_cash_filtrado['Jogador A'] == filtro_a) |
                        (df_pares_cash_filtrado['Jogador B'] == filtro_b)
                    ]
                    
                st.dataframe(df_pares_cash_filtrado, hide_index=True, width='stretch')

                if len(total_mesas_comuns_cash) > 0:
                    st.markdown('---')
                    st.subheader('Detalhamento por mesa')
            
                    mesas_ordenadas_cash = sorted(mesas_comuns_cash, reverse=True)
                    mesa_selecionada_cash = st.selectbox('Selecione uma mesa', sorted(total_mesas_comuns_cash, reverse=True))
                    df_mesa_cash = df_cash[df_cash['Game ID'] == mesa_selecionada_cash].copy()
                    df_mesa_cash = df_mesa_cash.sort_values(['Hand ID', 'Player ID'])
                    df_mesa_cash_resumo = df_mesa_cash.groupby(['Player ID', 'Player Name', 'Club Name']).agg(
                        Ganhos = ('chip change', 'sum'),
                        Rake = ('Game Fee change', 'sum'),
                        Qnt_Maos = ('Hand ID', 'count')
                    ).reset_index()
                    st.dataframe(df_mesa_cash_resumo,
                                hide_index=True,
                                width='stretch',
                                column_config={
                                    'Ganhos': st.column_config.NumberColumn(format='localized'),
                                    'Rake': st.column_config.NumberColumn(format='localized')
                                })
                    st.dataframe(df_mesa_cash, hide_index=True, width='stretch')
        
        with col_mtt:
            st.subheader('Torneios')
            df_mtt = st.session_state.df_backend[st.session_state.df_backend['Event'] == ('MttPrize')].copy()
            st.info(f'🏆 {len(df_mtt)} torneios finalizados.')

            if not df_mtt.empty:
                # st.dataframe(df_mtt.head())

                resumo_mtt = df_mtt.groupby(['Player ID', 'Player Name', 'Club Name'])['Game ID'].nunique().reset_index()
                resumo_mtt.columns = ['Player ID', 'Player Name', 'Club Name', 'Total de Torneios']

                st.dataframe(resumo_mtt, hide_index=True, width='stretch')
                mesas_por_jogador_mtt = df_mtt.groupby('Player Name')['Game ID'].apply(set)

                jogadores_mtt = resumo_mtt['Player Name'].unique().tolist()
                # print(jogadores_mtt)
                pares_mtt = []

                if len(jogadores_mtt) > 1:    
                    for i in range(len(jogadores_mtt)):
                        for j in range(i + 1, len(jogadores_mtt)):
                            a = jogadores_mtt[i]
                            b = jogadores_mtt[j]
                            total_mesas_comuns_mtt = mesas_por_jogador_mtt[a] & mesas_por_jogador_mtt[b]
                            # total_mesas_comuns_mtt |= mesas_comuns_mtt
                            total_comuns = len(total_mesas_comuns_mtt)
                            total_a = resumo_mtt.loc[resumo_mtt['Player Name'] == a, 'Total de Torneios'].values[0]
                            total_b = resumo_mtt.loc[resumo_mtt['Player Name'] == b, 'Total de Torneios'].values[0]
                            pares_mtt.append({
                                'Jogador A': df_mtt.loc[df_mtt['Player Name'] == a, 'Player Name'].values[0],
                                'Jogador B': df_mtt.loc[df_mtt['Player Name'] == b, 'Player Name'].values[0],
                                'Torneios em Comum': total_comuns,
                                '% do Jogador A': round(total_comuns / total_a * 100, 1),
                                '% do Jogador B': round(total_comuns / total_b * 100, 1)
                            })

                    df_pares_mtt = pd.DataFrame(pares_mtt)
                    st.dataframe(df_pares_mtt, hide_index=True, width='stretch')

                    if len(total_mesas_comuns_mtt) > 0:
                        st.markdown('---')
                        st.subheader('Detalhamento por Torneio')

                    mesas_ordenadas_mtt = sorted(total_mesas_comuns_mtt, reverse=True)
                    mesas_selecionada_mtt = st.selectbox('Selecione um Torneio', mesas_ordenadas_mtt)
                    df_mesa_mtt = st.session_state.df_backend[
                        (st.session_state.df_backend['Game ID'] == mesas_selecionada_mtt) &
                        (st.session_state.df_backend['Event'].isin(['MttPrize', 'MttKOPrize']))
                    ].copy()
                    df_mesa_mtt = df_mesa_mtt.sort_values('Game ID')
                    
                    df_mtt_prize = df_mesa_mtt[df_mesa_mtt['Event'] == 'MttPrize'].groupby(['Player ID', 'Player Name', 'Club Name'])['chip change'].sum().reset_index().rename(columns={'chip change': 'Prize'})
                    df_mtt_koprize = df_mesa_mtt[df_mesa_mtt['Event'] == 'MttKOPrize'].groupby(['Player ID', 'Player Name', 'Club Name'])['chip change'].sum().reset_index().rename(columns={'chip change': 'KO\'s'})
                    df_mesa_mtt_resumo = df_mtt_prize.merge(df_mtt_koprize, on=['Player Name', 'Club Name'], how='left').fillna(0)
                    df_mesa_mtt_resumo['Total'] = df_mesa_mtt_resumo['Prize'] + df_mesa_mtt_resumo['KO\'s']

                    st.dataframe(df_mesa_mtt_resumo, 
                                hide_index=True,
                                width='stretch',
                                column_config={
                                    'Prize': st.column_config.NumberColumn(format='localized'),
                                    'KO\'s': st.column_config.NumberColumn(format='localized'),
                                    'Total': st.column_config.NumberColumn(format='localized')
                                })  
                    st.dataframe(df_mesa_mtt, hide_index=True, width='stretch')
                else:
                    st.info(f'Somente a conta {jogadores_mtt[0]} possui registro em torneios.')

    protocolo = '1305308689'
    if df_pares_cash is not None:
        pdf = gerar_pdf(protocolo, df_pares_cash, df_pares_mtt, df_cash, df_mtt, total_mesas_comuns_cash, total_mesas_comuns_mtt)
        
    _, col_centro, _ = st.columns([2,1,2])
    with col_centro:
        if st.button('📄 Gerar Relatório'):
            gerar_relatorio(df_pares_cash, resumo_cash, df_pares_mtt, resumo_mtt, mesas_selecionada_mtt, df_mesa_mtt_resumo)

        st.download_button(
            label='📄 Baixar Relatório em PDF',
            data=pdf,
            file_name=f'#{protocolo}.pdf',
            mime='application/pdf'
        )

with aba_snowflake: 
    # -----------------------------------------------------
    # CARREGAMENTO DO ARQUIVO
    # -----------------------------------------------------
    if 'df_snowflake' not in st.session_state:
        st.session_state.df_snowflake = None
    
    col_upload_snowflake, col_limpacash_snowflake = st.columns([4,1])
    with col_upload_snowflake:
        upload_file = st.file_uploader(
            'Selecione o arquivo para fazer o upload e carregar os dados.',
            type='csv'
        )

    with col_limpacash_snowflake:
        st.space()
        if st.button('🗑️ Limpar dados', key='snowflake-limpa-cache'):
            st.session_state.df_snowflake = None
            st.cache_data.clear()
            st.rerun()

    if upload_file is not None:
        df = carregar_dados(upload_file)

        BASE_DIR = Path(__file__).resolve().parent.parent
        df_clube = pd.read_csv(BASE_DIR / 'data' / 'clubes.csv')
        df_liga = pd.read_csv(BASE_DIR / 'data' / 'ligas.csv')

        df = df.merge(
            df_clube[['clube_id', 'clube_nome', 'liga_id', 'liga_nome']],
            left_on='ID_CLUBE',
            right_on='clube_id',
            how='left'
        ).drop(columns=['clube_id'])

        df = df.merge(
            df_liga[['liga_id','handicap', 'moeda']],
            on='liga_id',
            how='left'
        )

        df = df.rename(columns={
            'clube_nome': 'NOME_CLUBE',
            'liga_id': 'ID_LIGA',
            'liga_nome': 'NOME_LIGA',
            'handicap': 'HANDICAP',
            'moeda': 'MOEDA'
        })

        valores = ['GANHOS', 'RAKE']
        df['HANDICAP'] = df['HANDICAP'].astype(float)
        df[valores] = df[valores].mul(5, axis=0)

        st.session_state.df_snowflake = df
        st.success(f'✅ Arquivo carregado! {len(df)} linhas encontradas. Valores já convertido para a moeda local de acordo com a liga.')
        # st.dataframe(df.head())
 
    # st.markdown('---')
    if st.session_state.df_snowflake is None:
        st.empty()
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            # -----------------------------------------------------
            # ENCONTRANDO JOGADORES
            # -----------------------------------------------------

            if st.session_state.df_snowflake is None:
                st.stop()
            st.subheader('Jogadores encontrados no arquivo')


            resumo = st.session_state.df_snowflake.groupby(['ID_JOGADOR', 'NOME_JOGADOR'])['ID_MESA'].nunique().reset_index()
            resumo.columns = ['ID', 'Nome', 'Total de Mesas']

            st.dataframe(resumo, hide_index=True, width='stretch')

            # -----------------------------------------------------
            # ENCONTRANDO MESAS EM COMUM
            # -----------------------------------------------------
            st.subheader('Mesas em comum')

            mesas_por_jogador = st.session_state.df_snowflake.groupby('ID_JOGADOR')['ID_MESA'].apply(set)

            jogadores = resumo['ID'].tolist()
            pares = []

            for i in range(len(jogadores)):
                for j in range(i+1, len(jogadores)):
                    a = jogadores[i]
                    b = jogadores[j]
                    mesas_comuns = mesas_por_jogador[a] & mesas_por_jogador[b] # Retorna a interseção entre dois dicionários.
                    total_comuns = len(mesas_comuns)
                    total_a = resumo.loc[resumo['ID'] == a, 'Total de Mesas'].values[0]
                    total_b = resumo.loc[resumo['ID'] == b, 'Total de Mesas'].values[0]
                    pares.append({
                        'Jogador A': st.session_state.df_snowflake.loc[st.session_state.df_snowflake['ID_JOGADOR'] == a, 'NOME_JOGADOR'].values[0],
                        'Jogador B': st.session_state.df_snowflake.loc[st.session_state.df_snowflake['ID_JOGADOR'] == b, 'NOME_JOGADOR'].values[0],
                        'Mesas em Comum': total_comuns,
                        '% do Jogador A': round(total_comuns / total_a * 100, 1),
                        '% do Jogador B': round(total_comuns / total_b * 100, 1)
                    })

            df_pares = pd.DataFrame(pares)
            st.dataframe(df_pares, hide_index=True, width='stretch')

        with col2:
            st.subheader('Dispositivos')

            df_dispositivos = st.session_state.df_snowflake[['NOME_JOGADOR', 'CODIGO_DISPOSITIVO', 'DISPOSITIVO', 'SISTEMA']].drop_duplicates()
            st.dataframe(df_dispositivos, hide_index=True, width='stretch')

            dispositivos_comuns = st.session_state.df_snowflake.groupby('CODIGO_DISPOSITIVO')['ID_JOGADOR'].nunique()
            dispositivos_comuns = dispositivos_comuns[dispositivos_comuns > 1].index.tolist()

            if dispositivos_comuns:
                st.warning(f'⚠️ {len(dispositivos_comuns)} dispositivo(s) compartilhado(s) entre os jogadores.')
            else:
                st.success('✅ Nenhum dispositivo compartilhado.')

            st.subheader('IP\'s')

            df_ips = st.session_state.df_snowflake[['NOME_JOGADOR', 'IP']].drop_duplicates()

            ips_comuns = st.session_state.df_snowflake.groupby('IP')['ID_JOGADOR'].nunique()
            ips_comuns = ips_comuns[ips_comuns > 1].index.tolist()


            if 'ip_cache' not in st.session_state:
                st.session_state.ip_cache = {}
            
            ips_unicos = st.session_state.df_snowflake['IP'].dropna().unique().tolist()
            ips_novos = [ip for ip in ips_unicos if ip not in st.session_state.ip_cache]

            if ips_novos:
                for ip in ips_novos:
                    try:
                        resp = requests.get(
                            f'http://ip-api.com/json/{ip}?fields=city,regionName,country',
                            timeout=10
                        )
                        data = resp.json()
                        st.session_state.ip_cache[ip] = {
                            'CIDADE': data.get('city'),
                            'ESTADO': data.get('regionName'),
                            'PAIS': data.get('country')
                        }
                    except:
                        st.session_state.ip_cache[ip] = {
                            'CIDADE': None,
                            'ESTADO': None,
                            'PAIS': None
                        }
            
            df_ips['CIDADE'] = df_ips['IP'].map(lambda x: st.session_state.ip_cache.get(x, {}).get('CIDADE'))
            df_ips['ESTADO'] = df_ips['IP'].map(lambda x: st.session_state.ip_cache.get(x, {}).get('ESTADO'))
            df_ips['PAIS'] = df_ips['IP'].map(lambda x: st.session_state.ip_cache.get(x, {}).get('PAIS'))
            
            st.dataframe(df_ips, hide_index=True, width='stretch')
            if ips_comuns:
                st.warning(f'⚠️ {len(ips_comuns)} IP(s) compartilhado(s) entre os jogadores.')
            else:
                st.success('✅ Nenhum IP compartilhado')

        with col3:
            st.subheader('Geolocalização')

            df_geo = st.session_state.df_snowflake[['NOME_JOGADOR', 'ID_MESA', 'NOME_MESA', 'LATITUDE', 'LONGITUDE']].dropna(subset=['LATITUDE', 'LONGITUDE']).drop_duplicates()
            
            df_geo['LATITUDE'] = df_geo['LATITUDE'].astype(float).round(3)
            df_geo['LONGITUDE'] = df_geo['LONGITUDE'].astype(float).round(3)
            df_geo['NOME_JOGADOR'] = df_geo['NOME_JOGADOR'].str.strip()
            
            if 'geo_cache' not in st.session_state:
                st.session_state.geo_cache = {}
            
            coords_unicas = df_geo[['LATITUDE', 'LONGITUDE']].drop_duplicates()
            coords_novas = coords_unicas[
                ~coords_unicas.apply(lambda r: (r['LATITUDE'], r['LONGITUDE']) in st.session_state.geo_cache, axis=1)
            ]

            if not coords_novas.empty:
                for _, row in coords_novas.iterrows():
                    lat, lon = row['LATITUDE'], row['LONGITUDE']
                    try:
                        resp = requests.get(
                            f'https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}',
                            headers={'User-Agent': 'DougForgerPKR/1.0'},
                            timeout=10
                        )
                        data = resp.json()
                        addr = data.get('address', {})
                        st.session_state.geo_cache[(lat, lon)] = {
                            'CIDADE': addr.get('city') or addr.get('town') or addr.get('village'),
                            'ESTADO': addr.get('state'),
                            'PAIS': addr.get('country')
                        }
                    except:
                        st.session_state.geo_cache[(lat, lon)] = {'CIDADE': None, 'ESTADO': None, 'PAIS': None}
                    time.sleep(1)
            
            df_geo['CIDADE'] = df_geo.apply(lambda r: st.session_state.geo_cache.get((r['LATITUDE'], r['LONGITUDE']), {}).get('CIDADE'), axis=1)
            df_geo['ESTADO'] = df_geo.apply(lambda r: st.session_state.geo_cache.get((r['LATITUDE'], r['LONGITUDE']), {}).get('ESTADO'), axis=1)
            df_geo['PAIS'] = df_geo.apply(lambda r: st.session_state.geo_cache.get((r['LATITUDE'], r['LONGITUDE']), {}).get('PAIS'), axis=1)

            if df_geo.empty:
                st.info('Jogadores sem registro de localização por GPS.')
            else:
                st.dataframe(df_geo[['NOME_JOGADOR', 'CIDADE', 'ESTADO', 'PAIS']].drop_duplicates(), hide_index=True, width='stretch')

            cidades_comuns = df_geo.groupby('CIDADE')['NOME_JOGADOR'].nunique()
            cidades_comuns = cidades_comuns[cidades_comuns > 1].index.tolist()

            if cidades_comuns:
                st.warning(f'⚠️ Jogadores na mesma cidade: {", ".join(cidades_comuns)}')
            else:
                st.success('✅ Nenhuma localização em comum.')
            
        # -----------------------------------------------------
        # DETALHANDO MESAS EM COMUM
        # -----------------------------------------------------
        st.markdown('---')
        st.subheader('Detalhamento por mesa')

        mesas_ordenadas = sorted(mesas_comuns, reverse=True)
        mesa_selecionada = st.selectbox('Selecione uma mesa para mais detalhes.', mesas_ordenadas)

        df_mesa_resumo = st.session_state.df_snowflake[st.session_state.df_snowflake['ID_MESA'] == mesa_selecionada]
        df_mesa_resumo = df_mesa_resumo.groupby(['NOME_JOGADOR', 'NOME_CLUBE', 'ID_MESA']).agg(
            TOTAL_GANHOS = ('GANHOS', 'sum'),
            TOTAL_RAKE = ('RAKE', 'sum'),
            QNT_MAOS = ('ID_MAO', 'count')
        ).reset_index()
        st.dataframe(
            df_mesa_resumo[['NOME_JOGADOR', 'NOME_CLUBE', 'TOTAL_GANHOS', 'TOTAL_RAKE', 'QNT_MAOS']],
            hide_index=True,
            width='stretch'
        )

        df_mesa = st.session_state.df_snowflake[st.session_state.df_snowflake['ID_MESA'] == mesa_selecionada].sort_values(['ID_MAO', 'ID_JOGADOR']).copy()
        st.dataframe(
            df_mesa[['DATA', 'NOME_JOGADOR', 'NOME_CLUBE', 'ID_MAO', 'GANHOS', 'RAKE', 'IP', 'IP_PAIS']],
            hide_index=True,
            width='stretch'
        )
