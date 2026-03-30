import datetime

import matplotlib.pyplot as plt
import seaborn as sns
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

    data_inicial = st.date_input(
        'Data inicial:',
        DATA_PRIMEIRO_CARD,
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
    # isin() retorna False para NaN — só aplica o filtro se for seleção parcial
    if set(categorias_selecionadas) < set(CATEGORIAS):
        mask &= df_total['categoria'].isin(categorias_selecionadas)
    if set(tipos_selecionados) < set(TIPOS):
        mask &= df_total['tipo'].isin(tipos_selecionados)
    if set(resultados_selecionados) < set(RESULTADOS):
        mask &= df_total['resultado'].isin(resultados_selecionados)
    if set(analistas_selecionados) < set(ANALISTAS):
        mask &= df_total['analista'].isin(analistas_selecionados)

    df = df_total[mask].copy()

    if df.empty:
        st.warning(f'Nenhum protocolo encontrado. {len(df_total):,} cards carregados no total — verifique os filtros.')
        st.stop()

    with st.expander('👀 Visualização dos dados', expanded = False):
        st.dataframe(
            df
        )

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
    m2.metric('Positivos vs Total', f'{n_pos:,}', f'{pct_pos:.1f}%', delta_color='off', delta_arrow='off')
    m3.metric('Internos vs Positivos', f'{n_internos_pos:,}', f'{pct_int:.1f}%', delta_color='off', delta_arrow='off')

    st.markdown('---')

    sns.set_theme(style='whitegrid', font_scale=1.05)

    # -- Gráfico 1: Negativo × Positivo ------------------------------------------
    pct_neg = n_neg / total * 100 if total else 0

    fig_res, ax_res = plt.subplots(figsize=(12, 2))
    ax_res.barh([''], [pct_neg], color='#95A5A6', label=f'Negativos  ({n_neg:,})')
    ax_res.barh([''], [pct_pos], left=[pct_neg], color='#F0A64D', label=f'Positivos  ({n_pos:,})')
    if pct_neg > 5:
        ax_res.text(pct_neg / 2, 0, f'{pct_neg:.1f}%',
                    ha='center', va='center', color='white', fontsize=13, fontweight='bold')
    if pct_pos > 5:
        ax_res.text(pct_neg + pct_pos / 2, 0, f'{pct_pos:.1f}%',
                    ha='center', va='center', color='white', fontsize=13, fontweight='bold')
    ax_res.set_xlim(0, 100)
    ax_res.set_xlabel('%')
    ax_res.set_yticklabels([])
    ax_res.tick_params(left=False)
    ax_res.set_title('Resultado das Análises', fontsize=13, fontweight='bold', loc='left', pad=12)
    ax_res.legend(loc='lower center', bbox_to_anchor=(0.5, 1.08), ncol=2, frameon=False)
    ax_res.spines[['top', 'right', 'left']].set_visible(False)
    fig_res.tight_layout()
    st.pyplot(fig_res, use_container_width=True)
    plt.close(fig_res)

    # -- Gráfico 2: Por Categoria ------------------------------------------------
    cat_counts = df['categoria'].value_counts().reset_index()
    cat_counts.columns = ['Categoria', 'Quantidade']
    cat_counts['%'] = (cat_counts['Quantidade'] / total * 100).round(1)
    cat_counts = cat_counts.sort_values('Quantidade', ascending=True)

    fig_cat, ax_cat = plt.subplots(figsize=(12, max(3, len(cat_counts) * 0.55)))
    sns.barplot(data=cat_counts, y='Categoria', x='%', ax=ax_cat, color='#2980B9')
    for bar, (_, row) in zip(ax_cat.patches, cat_counts.iterrows()):
        ax_cat.text(bar.get_width() + 0.4, bar.get_y() + bar.get_height() / 2,
                    f'{row["%"]:.1f}%  ({row["Quantidade"]:,})', va='center', fontsize=10)
    ax_cat.set_xlim(0, cat_counts['%'].max() * 1.25)
    ax_cat.set_title('Quantidade por Categoria', fontsize=13, fontweight='bold', loc='left', pad=12)
    ax_cat.set_xlabel('%')
    ax_cat.set_ylabel('')
    ax_cat.spines[['top', 'right']].set_visible(False)
    fig_cat.tight_layout()
    st.pyplot(fig_cat, use_container_width=True)
    plt.close(fig_cat)

    # -- Gráfico 3: Por Analista -------------------------------------------------
    analista_counts = df['analista'].dropna().value_counts().reset_index()
    analista_counts.columns = ['Analista', 'Quantidade']
    analista_counts = analista_counts.sort_values('Quantidade', ascending=True)

    fig_ana, ax_ana = plt.subplots(figsize=(12, max(3, len(analista_counts) * 0.55)))
    sns.barplot(data=analista_counts, y='Analista', x='Quantidade', ax=ax_ana, color='#8E44AD')
    for bar, (_, row) in zip(ax_ana.patches, analista_counts.iterrows()):
        ax_ana.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                    str(row['Quantidade']), va='center', fontsize=10)
    ax_ana.set_xlim(0, analista_counts['Quantidade'].max() * 1.15)
    ax_ana.set_title('Quantidade por Analista', fontsize=13, fontweight='bold', loc='left', pad=12)
    ax_ana.set_xlabel('Quantidade')
    ax_ana.set_ylabel('')
    ax_ana.spines[['top', 'right']].set_visible(False)
    fig_ana.tight_layout()
    st.pyplot(fig_ana, use_container_width=True)
    plt.close(fig_ana)

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
