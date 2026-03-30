import datetime
import time

import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

from utils.pipefy_api import buscar_contagem_cards, buscar_todos_os_cards, testar_conexao
from utils.pipefy_pdf import OPCOES_GRAFICOS, aplicar_fonte_mpl, gerar_pdf_dashboard

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
# DADOS (cache manual no session_state — TTL de 1 hora)
# -----------------------------------------------------
_TTL = 3600

def _cache_expirado() -> bool:
    ts = st.session_state.get('pipefy_ts')
    return ts is None or (time.time() - ts) > _TTL

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

    if st.button('🔄 Atualizar dados', width='stretch'):
        st.session_state.pop('pipefy_df', None)
        st.session_state.pop('pipefy_ts', None)
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
    if _cache_expirado() or 'pipefy_df' not in st.session_state:
        try:
            total_cards = buscar_contagem_cards()
        except Exception:
            total_cards = 0

        texto_base = 'Carregando cards do Pipefy...'
        barra = st.progress(0, text=texto_base)

        def _on_progress(n: int) -> None:
            if total_cards > 0:
                pct = min(n / total_cards, 1.0)
                barra.progress(pct, text=f'{texto_base}  {n:,} / {total_cards:,}')
            else:
                barra.progress(0, text=f'{texto_base}  {n:,} carregados')

        df_carregado = buscar_todos_os_cards(on_progress=_on_progress)
        barra.progress(1.0, text=f'✅ {len(df_carregado):,} cards carregados.')
        st.session_state['pipefy_df'] = df_carregado
        st.session_state['pipefy_ts'] = time.time()

    df_total = st.session_state['pipefy_df']

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
    aplicar_fonte_mpl()

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
    st.pyplot(fig_res, width='stretch')
    plt.close(fig_res)

    # -- Gráfico 2: Por Categoria (stacked positivo/negativo) -------------------
    cat_res = df.groupby('categoria')['resultado'].value_counts().unstack(fill_value=0)
    for col in ['Positivo', 'Negativo']:
        if col not in cat_res.columns:
            cat_res[col] = 0
    cat_res['Total'] = cat_res['Positivo'] + cat_res['Negativo']
    cat_res = cat_res.sort_values('Total', ascending=True)  # ascending → maior no topo (barh)

    cats = cat_res.index.tolist()
    neg_vals = cat_res['Negativo'].tolist()
    pos_vals = cat_res['Positivo'].tolist()

    fig_cat, ax_cat = plt.subplots(figsize=(12, max(3, len(cats) * 0.65)))
    ax_cat.barh(cats, neg_vals, color='#95A5A6', label='Negativos')
    ax_cat.barh(cats, pos_vals, left=neg_vals, color='#F0A64D', label='Positivos')
    grand_total_cat = sum(neg_vals) + sum(pos_vals)
    max_x_cat = max((n + p) for n, p in zip(neg_vals, pos_vals)) if cats else 1
    ax_cat.set_xlim(0, max_x_cat * 1.40)

    for i, (neg, pos) in enumerate(zip(neg_vals, pos_vals)):
        if neg > 0:
            ax_cat.text(neg / 2, i, str(neg), ha='center', va='center',
                        color='white', fontsize=9, fontweight='bold')
        if pos > 0:
            ax_cat.text(neg + pos / 2, i, str(pos), ha='center', va='center',
                        color='white', fontsize=9, fontweight='bold')
        # label externo: total + %
        total_bar = neg + pos
        pct_bar = total_bar / grand_total_cat * 100 if grand_total_cat else 0
        ax_cat.text(total_bar + max_x_cat * 0.03, i, f'{total_bar:,} ({pct_bar:.1f}%)',
                    va='center', fontsize=9)

    ax_cat.set_title('Quantidade por Categoria', fontsize=13, fontweight='bold', loc='left', pad=12)
    ax_cat.legend(loc='lower right', frameon=False)
    ax_cat.set_xlabel('Quantidade')
    ax_cat.set_ylabel('')
    ax_cat.spines[['top', 'right']].set_visible(False)
    fig_cat.tight_layout()
    st.pyplot(fig_cat, width='stretch')
    plt.close(fig_cat)

    # Tabela resumo de categorias
    df_cat_tabela = cat_res[['Negativo', 'Positivo', 'Total']].copy()
    df_cat_tabela['%'] = (df_cat_tabela['Total'] / grand_total_cat * 100).round(1).map('{:.1f}%'.format)
    df_cat_tabela = df_cat_tabela.sort_values('Total', ascending=False)
    df_cat_tabela.index.name = 'Categoria'
    df_cat_tabela = df_cat_tabela.rename(columns={'Negativo': 'Negativos', 'Positivo': 'Positivos'})
    df_cat_tabela = df_cat_tabela.reset_index()
    st.dataframe(df_cat_tabela, width='stretch', hide_index=True)

    # -- Gráfico 3: Por Analista -------------------------------------------------
    analista_counts = df['analista'].dropna().value_counts().reset_index()
    analista_counts.columns = ['Analista', 'Quantidade']
    analista_counts = analista_counts.sort_values('Quantidade', ascending=True)  # ascending → maior no topo (barh)

    fig_ana, ax_ana = plt.subplots(figsize=(12, max(3, len(analista_counts) * 0.65)))
    bars = ax_ana.barh(analista_counts['Analista'], analista_counts['Quantidade'], color='#F0A64D')
    for bar, val in zip(bars, analista_counts['Quantidade']):
        ax_ana.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                    str(val), va='center', fontsize=10)
    ax_ana.set_xlim(0, analista_counts['Quantidade'].max() * 1.15)
    ax_ana.set_title('Quantidade por Analista', fontsize=13, fontweight='bold', loc='left', pad=12)
    ax_ana.set_xlabel('Quantidade')
    ax_ana.set_ylabel('')
    ax_ana.spines[['top', 'right']].set_visible(False)
    fig_ana.tight_layout()
    st.pyplot(fig_ana, width='stretch')
    plt.close(fig_ana)

    # -- Export PDF -------------------------------------------------------------
    st.markdown('---')
    graficos_pdf = st.multiselect(
        'Gráficos a incluir no PDF:',
        OPCOES_GRAFICOS,
        default=OPCOES_GRAFICOS,
        key='graficos-pdf',
    )
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
            pdf_bytes = gerar_pdf_dashboard(df, filtros, graficos=graficos_pdf)
        nome_arquivo = f'Relatório_Security_PKR_{data_inicial}_{data_final}.pdf'
        st.download_button(
            label='⬇️ Baixar PDF',
            data=pdf_bytes,
            file_name=nome_arquivo,
            mime='application/pdf',
        )
