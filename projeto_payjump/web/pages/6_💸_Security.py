import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta

st.set_page_config(
    page_title='Security — Relatório',
    page_icon='💸',
    layout='wide'
)

DESPESAS_PATH = r"C:\Users\DouglasArmandoFerrei\OneDrive - Suprema\Suprema\Despesas.xlsx"

NOMES_MESES = {
    1: 'janeiro', 2: 'fevereiro', 3: 'março', 4: 'abril',
    5: 'maio', 6: 'junho', 7: 'julho', 8: 'agosto',
    9: 'setembro', 10: 'outubro', 11: 'novembro', 12: 'dezembro'
}


@st.cache_data
def load_data():
    df = pd.read_excel(DESPESAS_PATH, sheet_name='Despesas')
    df['Dia Fechamento'] = pd.to_datetime(df['Dia Fechamento'])
    return df


def fmt_brl(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def ultimo_domingo() -> date:
    hoje = date.today()
    dias = (hoje.weekday() + 1) % 7  # Mon=0..Sun=6 → dias desde o último domingo
    if dias == 0:
        dias = 7
    return hoje - timedelta(days=dias)


# ── Carregamento ──────────────────────────────────────────────────────────────
try:
    df = load_data()
except FileNotFoundError:
    st.error(f'Arquivo não encontrado: `{DESPESAS_PATH}`')
    st.stop()
except Exception as e:
    st.error(f'Erro ao carregar planilha: {e}')
    st.stop()

# ── Filtro na sidebar ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('### 📅 Dia Fechamento')
    ano_atual = date.today().year
    data_inicio = st.date_input('De', value=date(ano_atual, 1, 5))
    data_fim = st.date_input('Até', value=ultimo_domingo())

    if data_inicio > data_fim:
        st.error('Data inicial deve ser anterior à data final.')
        st.stop()

# ── Filtragem ─────────────────────────────────────────────────────────────────
df_filtrado = df[
    (df['Dia Fechamento'].dt.date >= data_inicio) &
    (df['Dia Fechamento'].dt.date <= data_fim)
].copy()

st.title('💸 Security — Relatório Semanal')
st.markdown('---')

if df_filtrado.empty:
    st.warning('Nenhum lançamento encontrado para o período selecionado.')
    st.stop()

# ── Período de referência (última semana no intervalo selecionado) ─────────────
ultimo_fechamento = df_filtrado['Dia Fechamento'].max()
mes_ref = ultimo_fechamento.month
ano_ref = ultimo_fechamento.year

# ── Cálculo dos saldos ────────────────────────────────────────────────────────
saldo_semanal = df_filtrado[
    df_filtrado['Dia Fechamento'] == ultimo_fechamento
]['Valor'].sum()

saldo_mensal = df_filtrado[
    (df_filtrado['Dia Fechamento'].dt.month == mes_ref) &
    (df_filtrado['Dia Fechamento'].dt.year == ano_ref)
]['Valor'].sum()

df_ano = df_filtrado[df_filtrado['Dia Fechamento'].dt.year == ano_ref]
saldo_anual = df_ano['Valor'].sum()

saldo_total = df_filtrado['Valor'].sum()

# ── Layout ────────────────────────────────────────────────────────────────────
col_kpi, col_chart = st.columns([1, 2])

with col_kpi:
    inicio_semana = ultimo_fechamento - timedelta(days=6)
    label_semana = (
        f"{inicio_semana.strftime('%d/%m/%Y')} a {ultimo_fechamento.strftime('%d/%m/%Y')}"
    )

    st.metric(f'Saldo Semanal — {label_semana}', fmt_brl(saldo_semanal))
    st.markdown('')
    st.metric(f'Saldo Mensal — {NOMES_MESES[mes_ref]}/{ano_ref}', fmt_brl(saldo_mensal))
    st.markdown('')
    st.metric(f'Saldo Anual — {ano_ref}', fmt_brl(saldo_anual))
    st.markdown('')
    st.metric('Saldo Total', fmt_brl(saldo_total))

with col_chart:
    df_chart = df_ano.copy()
    df_chart['Mês Num'] = df_chart['Dia Fechamento'].dt.month
    df_chart['Mês Nome'] = df_chart['Mês Num'].map(NOMES_MESES)

    df_agg = (
        df_chart
        .groupby(['Mês Num', 'Mês Nome'])['Valor']
        .sum()
        .reset_index()
        .sort_values('Mês Num')
    )
    df_agg['Label'] = df_agg['Valor'].apply(fmt_brl)

    ordem_meses = [NOMES_MESES[m] for m in sorted(df_agg['Mês Num'].unique())]

    fig = px.bar(
        df_agg,
        x='Valor',
        y='Mês Nome',
        orientation='h',
        text='Label',
        title=f'Saldo ao longo de {ano_ref}',
        labels={'Valor': 'Saldo', 'Mês Nome': 'Meses'},
        color_discrete_sequence=['#1F77B4'],
    )
    fig.update_traces(textposition='outside', cliponaxis=False)
    fig.update_layout(
        showlegend=False,
        yaxis={'categoryorder': 'array', 'categoryarray': ordem_meses},
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=10, r=120, t=50, b=10),
    )

    st.plotly_chart(fig, use_container_width=True)
