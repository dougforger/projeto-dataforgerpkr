import datetime

import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from utils.pipefy_api import buscar_todos_os_cards, testar_conexao
from utils.pipefy_pdf import gerar_pdf_dashboard

# -----------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# -----------------------------------------------------
st.set_page_config(
    page_title='Pipefy',
    page_icon='🔗',
    layout='wide',
    initial_sidebar_state='collapsed',
)

st.title('🔗 Pipefy — Security PKR')
st.markdown('---')

DATA_PRIMEIRO_CARD = datetime.date(2021, 10, 1)

# -----------------------------------------------------
# CONSTANTES DOS FILTROS
# -----------------------------------------------------
CATEGORIAS = ['Collusion', 'Software Ilegal (BOT)', 'Abuso de Chat', 'Chip Dumping', 'Aliciamento', 'Fraude']
TIPOS = ['Investigação interna', 'Denúncia']
RESULTADOS = ['Positivo', 'Negativo']
ANALISTAS = ['Eduardo Da Silva', 'Bruno Zangief', 'Frederyk Matos Santana', 'Douglas Ferreira', 'José Aureomar Chaves Wolff Neto', 'Luiz Benedito Souto Mendes Santos', 'Thiago Reis de Oliveira']

# -----------------------------------------------------
# DADOS (cache de 1 hora)
# -----------------------------------------------------
@st.cache_data(ttl=3600, show_spinner='Carregando cards do Pipefy...')
def carregar_cards():
    return buscar_todos_os_cards()

# -----------------------------------------------------
# LAYOUT
# -----------------------------------------------------
col_filtros, col_dashboard = st.columns([1, 6])

with col_filtros:
    st.markdown('#### 🔍 Filtros')
    hoje = datetime.date.today()
    primeiro_dia_mes = hoje.replace(day=1)

    data_inicial = st.date_input(
        'Data inicial:',
        primeiro_dia_mes,
        min_value=DATA_PRIMEIRO_CARD,
        max_value=hoje,
        key='filtro-data-inicial',
    )
    data_final = st.date_input(
        'Data final:',
        hoje,
        min_value=DATA_PRIMEIRO_CARD,
        max_value=hoje,
        key='filtro-data-final',
    )
    if data_inicial > data_final:
        st.warning('⚠️ A data inicial é após a data final.')
        st.stop()

    categorias_selecionadas = st.multiselect(
        'Categoria:',
        CATEGORIAS,
        default=CATEGORIAS,
    )
    tipos_selecionados = st.multiselect(
        'Tipo de ocorrência:',
        TIPOS,
        default=TIPOS,
    )
    resultados_selecionados = st.multiselect(
        'Resultado da análise:',
        RESULTADOS,
        default=RESULTADOS,
    )
    analistas_selecionados = st.multiselect(
        'Analistas:',
        ANALISTAS,
        default=ANALISTAS,
    )

    st.markdown('---')

    if st.button('🔄 Atualizar dados', use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Diagnóstico
    with st.expander('🔧 Diagnóstico de conexão'):
        if st.button('Testar Conexão'):
            with st.spinner('Conectando...'):
                try:
                    usuario = testar_conexao()
                    st.success(
                        f'Autenticado como **{usuario["name"]}** ({usuario["email"]})'
                    )
                except Exception as e:
                    st.error(f'Falha: {e}')

# -----------------------------------------------------
# CARREGA E FILTRA OS DADOS
# -----------------------------------------------------
with col_dashboard:
    df_total = carregar_cards()

    mask = (df_total['criado_em'] >= data_inicial) & (df_total['criado_em'] <= data_final)
    if categorias_selecionadas:
        mask &= df_total['categoria'].isin(categorias_selecionadas)
    if tipos_selecionados:
        mask &= df_total['tipo'].isin(tipos_selecionados)
    if resultados_selecionados:
        mask &= df_total['resultado'].isin(resultados_selecionados)
    if analistas_selecionados:
        mask &= df_total['analista'].isin(analistas_selecionados)

    df = df_total[mask].copy()

    if df.empty:
        st.warning('Nenhum protocolo encontrado com os filtros selecionados.')
        st.stop()

    # -- Métricas ----------------------------------------------------------------
    total = len(df)
    n_pos = (df['resultado'] == 'Positivo').sum()
    n_neg = (df['resultado'] == 'Negativo').sum()
    n_internos_pos = (
        (df['tipo'] == 'Investigação interna') & (df['resultado'] == 'Positivo')
    ).sum()
    pct_pos = n_pos / total * 100 if total else 0
    pct_int = n_internos_pos / n_pos * 100 if n_pos else 0

    st.markdown('#### 📊 Dashboard')
    m1, m2, m3 = st.columns(3)
    m1.metric('Total de Protocolos', f'{total:,}')
    m2.metric('Positivos vs Total', f'{n_pos:,}', f'{pct_pos:.1f}%', delta_color='off')
    m3.metric('Internos vs Positivos', f'{n_internos_pos:,}', f'{pct_int:.1f}%', delta_color='off')

    st.markdown('---')

    # -- Gráfico 1: Negativo × Positivo ------------------------------------------
    pct_neg = n_neg / total * 100 if total else 0

    fig_resultado = go.Figure()
    fig_resultado.add_trace(go.Bar(
        name=f'Negativos ({n_neg:,})',
        y=['Resultado'],
        x=[pct_neg],
        orientation='h',
        marker_color='#C0392B',
        text=f'{pct_neg:.1f}%',
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(color='white', size=14),
    ))
    fig_resultado.add_trace(go.Bar(
        name=f'Positivos ({n_pos:,})',
        y=['Resultado'],
        x=[pct_pos],
        orientation='h',
        marker_color='#27AE60',
        text=f'{pct_pos:.1f}%',
        textposition='inside',
        insidetextanchor='middle',
        textfont=dict(color='white', size=14),
    ))
    fig_resultado.update_layout(
        barmode='stack',
        height=100,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(range=[0, 100], tickformat='.0f', ticksuffix='%', showgrid=False),
        yaxis=dict(showticklabels=False),
        legend=dict(orientation='h', yanchor='bottom', y=1.05, xanchor='right', x=1),
        plot_bgcolor='white',
    )
    st.plotly_chart(fig_resultado, use_container_width=True)

    # -- Gráficos 2 e 3 lado a lado ---------------------------------------------
    g_col1, g_col2 = st.columns(2)

    # Gráfico 2: Por Categoria
    with g_col1:
        cat_counts = df['categoria'].value_counts().reset_index()
        cat_counts.columns = ['Categoria', 'Quantidade']
        cat_counts['%'] = (cat_counts['Quantidade'] / total * 100).round(1)
        cat_counts = cat_counts.sort_values('Quantidade', ascending=True)

        fig_cat = px.bar(
            cat_counts,
            y='Categoria',
            x='%',
            orientation='h',
            text=cat_counts['%'].map(lambda x: f'{x:.1f}%'),
            color_discrete_sequence=['#2980B9'],
            title='Quantidade por Categoria',
        )
        fig_cat.update_traces(textposition='outside')
        fig_cat.update_layout(
            margin=dict(l=0, r=40, t=40, b=0),
            xaxis_title='%',
            yaxis_title='',
            plot_bgcolor='white',
            showlegend=False,
        )
        st.plotly_chart(fig_cat, use_container_width=True)

    # Gráfico 3: Por Analista
    with g_col2:
        analista_counts = df['analista'].dropna().value_counts().reset_index()
        analista_counts.columns = ['Analista', 'Quantidade']
        analista_counts = analista_counts.sort_values('Quantidade', ascending=True)

        fig_analista = px.bar(
            analista_counts,
            y='Analista',
            x='Quantidade',
            orientation='h',
            text='Quantidade',
            color_discrete_sequence=['#8E44AD'],
            title='Quantidade por Analista',
        )
        fig_analista.update_traces(textposition='outside')
        fig_analista.update_layout(
            margin=dict(l=0, r=40, t=40, b=0),
            xaxis_title='Quantidade',
            yaxis_title='',
            plot_bgcolor='white',
            showlegend=False,
        )
        st.plotly_chart(fig_analista, use_container_width=True)

    # -- Export PDF -------------------------------------------------------------
    st.markdown('---')
    if st.button('📄 Exportar PDF', use_container_width=False):
        with st.spinner('Gerando PDF...'):
            filtros = {
                'data_inicial': data_inicial,
                'data_final': data_final,
                'categorias': categorias_selecionadas,
                'tipos': tipos_selecionados,
                'resultados': resultados_selecionados,
                'analistas': analistas_selecionados,
                'ref_categorias': CATEGORIAS,
                'ref_tipos': TIPOS,
                'ref_resultados': RESULTADOS,
                'ref_analistas': ANALISTAS,
            }
            pdf_bytes = gerar_pdf_dashboard(df, filtros)
        nome_arquivo = f'dashboard_security_pkr_{data_inicial}_{data_final}.pdf'
        st.download_button(
            label='⬇️ Baixar PDF',
            data=pdf_bytes,
            file_name=nome_arquivo,
            mime='application/pdf',
        )
