import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
from io import BytesIO
from pathlib import Path
from datetime import date, timedelta
from matplotlib import font_manager
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle

_FONTS_DIR  = Path(__file__).parent.parent / 'fonts'
_FONT_LIGHT = _FONTS_DIR / 'calibril.ttf'
_FONT_BOLD  = _FONTS_DIR / 'calibrib.ttf'
_IMG_DIR    = Path(__file__).parent.parent / 'img'
_LOGO_PATH  = _IMG_DIR / 'LOGO PRETO DEITADO.png'
font_manager.fontManager.addfont(str(_FONT_LIGHT))
font_manager.fontManager.addfont(str(_FONT_BOLD))

st.set_page_config(
    page_title='Security — Relatório',
    page_icon='💸',
    layout='wide'
)

DESCONTO = -2215952.00
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
    dias = (hoje.weekday() + 1) % 7
    if dias == 0:
        dias = 7
    return hoje - timedelta(days=dias)


def gerar_imagem_export(kpis: list, df_agg: pd.DataFrame, data_inicio: date, data_fim: date, ano_ref: int) -> bytes:
    # ── Paleta institucional (mesma do pdf_config.py) ──────────────────────────
    COR_AMBER      = '#F0A64D'
    COR_TEXT       = '#1C1C1C'
    COR_TEXT_SUAVE = '#555555'
    COR_BORDA      = '#DDDDDD'

    fp_l9  = FontProperties(fname=str(_FONT_LIGHT), size=9)
    fp_l13 = FontProperties(fname=str(_FONT_LIGHT), size=13)
    fp_l14 = FontProperties(fname=str(_FONT_LIGHT), size=14)
    fp_l16 = FontProperties(fname=str(_FONT_LIGHT), size=16)
    fp_b22 = FontProperties(fname=str(_FONT_BOLD),  size=22)
    fp_b28 = FontProperties(fname=str(_FONT_BOLD),  size=28)

    fig = plt.figure(figsize=(18, 10), facecolor='white')

    # ── Cabeçalho ─────────────────────────────────────────────────────────────
    # Logo Security (canto superior esquerdo)
    try:
        logo_img = plt.imread(str(_LOGO_PATH))
        ax_logo = fig.add_axes([0.03, 0.872, 0.085, 0.108])
        ax_logo.imshow(logo_img)
        ax_logo.axis('off')
    except Exception:
        pass

    # Linha âmbar abaixo do logo
    fig.add_artist(Rectangle(
        (0.03, 0.858), 0.94, 0.001,
        transform=fig.transFigure, color=COR_AMBER, clip_on=False, zorder=10,
    ))

    # Título do relatório — alinhado à esquerda, abaixo da linha âmbar
    fig.text(
        0.03, 0.840, 'Relatório Semanal',
        ha='left', va='top', fontproperties=fp_b22, color=COR_TEXT,
    )

    # ── Métricas ──────────────────────────────────────────────────────────────
    ax_kpi = fig.add_axes([0.03, 0.13, 0.30, 0.68])
    ax_kpi.axis('off')
    for i, (label, valor) in enumerate(kpis):
        y_base = 0.75 - i * 0.25
        ax_kpi.text(0, y_base + 0.13, label, color=COR_TEXT_SUAVE,
                    fontproperties=fp_l13, transform=ax_kpi.transAxes)
        ax_kpi.text(0, y_base, valor, color=COR_TEXT,
                    fontproperties=fp_b28, transform=ax_kpi.transAxes)

    # ── Gráfico ───────────────────────────────────────────────────────────────
    ax_bar = fig.add_axes([0.38, 0.16, 0.58, 0.65])
    bars = ax_bar.barh(df_agg['Mês Nome'], df_agg['Valor'], color='#1F77B4')
    ax_bar.invert_yaxis()
    ax_bar.set_xlabel('Saldo', fontproperties=fp_l14, color=COR_TEXT_SUAVE)
    ax_bar.set_title(f'Saldo ao longo de {ano_ref}', fontproperties=fp_l16, pad=12, color=COR_TEXT)
    plt.setp(ax_bar.get_yticklabels(), fontproperties=fp_l14, color=COR_TEXT)
    plt.setp(ax_bar.get_xticklabels(), fontproperties=fp_l13, color=COR_TEXT_SUAVE)
    max_val = df_agg['Valor'].max()
    ax_bar.set_xlim(0, max_val * 1.35)
    for bar, label in zip(bars, df_agg['Label']):
        ax_bar.text(
            bar.get_width() + max_val * 0.02,
            bar.get_y() + bar.get_height() / 2,
            label, va='center', fontproperties=fp_l14, color=COR_TEXT,
        )
    ax_bar.tick_params(colors=COR_TEXT_SUAVE)
    ax_bar.spines['top'].set_visible(False)
    ax_bar.spines['right'].set_visible(False)
    ax_bar.spines['left'].set_color(COR_BORDA)
    ax_bar.spines['bottom'].set_color(COR_BORDA)
    ax_bar.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x/1000:.0f} Mil"))

    # ── Rodapé ────────────────────────────────────────────────────────────────
    # Linha cinza claro
    fig.add_artist(Rectangle(
        (0.03, 0.092), 0.94, 0.001,
        transform=fig.transFigure, color=COR_BORDA, clip_on=False, zorder=10,
    ))
    fig.text(0.03, 0.080, 'Site: securitypkr.com.br',
             ha='left', va='top', fontproperties=fp_l9, color=COR_TEXT_SUAVE)
    fig.text(0.03, 0.060, 'E-mail: security@suprema.group',
             ha='left', va='top', fontproperties=fp_l9, color=COR_TEXT_SUAVE)

    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', pad_inches=0.3)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ── Carregamento ──────────────────────────────────────────────────────────────
try:
    df = load_data()
except FileNotFoundError:
    st.error(f'Arquivo não encontrado: `{DESPESAS_PATH}`')
    st.stop()
except Exception as e:
    st.error(f'Erro ao carregar planilha: {e}')
    st.stop()

# ── Layout: coluna de filtros + coluna de conteúdo ────────────────────────────
col_filtros, col_conteudo = st.columns([1, 4])

with col_filtros:
    st.markdown('## 🔍 Filtros')
    st.markdown('### 📅 Dia Fechamento')
    ano_atual = date.today().year
    data_inicio = st.date_input('De', value=date(2021, 10, 25))
    data_fim = st.date_input('Até', value=ultimo_domingo())

    if data_inicio > data_fim:
        st.error('Data inicial deve ser anterior à data final.')
        st.stop()

# ── Filtragem ─────────────────────────────────────────────────────────────────
df_filtrado = df[
    (df['Dia Fechamento'].dt.date >= data_inicio) &
    (df['Dia Fechamento'].dt.date <= data_fim)
].copy()

# ── Conteúdo principal ────────────────────────────────────────────────────────
with col_conteudo:
    aba_relatorio, aba_analises = st.tabs(['Relatório Semanal', 'Análises'])

    # ── ABA: RELATÓRIO SEMANAL ─────────────────────────────────────────────────
    with aba_relatorio:
        st.title('💸 Security — Relatório Semanal')
        st.markdown(
            '<style>'
            '.stMetric label { font-size: 1rem !important; }'
            '[data-testid="stMetricValue"] { font-size: 2rem !important; }'
            '</style>',
            unsafe_allow_html=True,
        )
        st.markdown('---')

        if df_filtrado.empty:
            st.warning('Nenhum lançamento encontrado para o período selecionado.')
            st.stop()

        ultimo_fechamento = df_filtrado['Dia Fechamento'].max()
        mes_ref = ultimo_fechamento.month
        ano_ref = ultimo_fechamento.year

        saldo_semanal = abs(df_filtrado[
            df_filtrado['Dia Fechamento'] == ultimo_fechamento
        ]['Valor'].sum())

        saldo_mensal = abs(df_filtrado[
            (df_filtrado['Dia Fechamento'].dt.month == mes_ref) &
            (df_filtrado['Dia Fechamento'].dt.year == ano_ref)
        ]['Valor'].sum())

        df_ano = df_filtrado[df_filtrado['Dia Fechamento'].dt.year == ano_ref]
        saldo_anual = abs(df_ano['Valor'].sum())
        saldo_total = abs(df['Valor'].sum() - DESCONTO)

        df_chart = df_ano.copy()
        df_chart['Mês Num'] = df_chart['Dia Fechamento'].dt.month
        df_chart['Mês Nome'] = df_chart['Mês Num'].map(NOMES_MESES)

        df_agg = (
            df_chart
            .groupby(['Mês Num', 'Mês Nome'])['Valor']
            .sum().reset_index().sort_values('Mês Num')
        )
        df_agg['Valor'] = df_agg['Valor'].abs()
        df_agg['Label'] = df_agg['Valor'].apply(fmt_brl)
        ordem_meses = [NOMES_MESES[m] for m in sorted(df_agg['Mês Num'].unique())]
        max_valor = df_agg['Valor'].max()

        col_kpi, col_chart_rel = st.columns([1, 2])

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

        with col_chart_rel:
            fig = px.bar(
                df_agg, x='Valor', y='Mês Nome', orientation='h', text='Label',
                title=f'Saldo ao longo de {ano_ref}',
                labels={'Valor': 'Saldo', 'Mês Nome': 'Meses'},
                color_discrete_sequence=['#1F77B4'],
            )
            fig.update_traces(textposition='outside', cliponaxis=False, insidetextanchor='middle')
            fig.update_layout(
                showlegend=False, font=dict(size=15), bargap=0.45,
                yaxis={'categoryorder': 'array', 'categoryarray': ordem_meses},
                xaxis=dict(range=[0, max_valor * 1.35]),
                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=20, t=60, b=10),
            )
            st.plotly_chart(fig, width='stretch')

        st.markdown('---')
        kpis_export = [
            (f'Saldo Semanal — {label_semana}', fmt_brl(saldo_semanal)),
            (f'Saldo Mensal — {NOMES_MESES[mes_ref]}/{ano_ref}', fmt_brl(saldo_mensal)),
            (f'Saldo Anual — {ano_ref}', fmt_brl(saldo_anual)),
            ('Saldo Total', fmt_brl(saldo_total)),
        ]
        png_bytes = gerar_imagem_export(kpis_export, df_agg, inicio_semana, ultimo_fechamento, ano_ref)
        st.download_button(
            label='⬇️ Exportar como imagem',
            data=png_bytes,
            file_name=f'security_relatorio_{data_fim.strftime("%Y%m%d")}.png',
            mime='image/png',
        )

    # ── ABA: ANÁLISES ──────────────────────────────────────────────────────────
    with aba_analises:
        # Session state para drill down
        if 'drill_level' not in st.session_state:
            st.session_state.drill_level = 'ano'
        if 'drill_contexto' not in st.session_state:
            st.session_state.drill_contexto = {}
        if 'drill_semana' not in st.session_state:
            st.session_state.drill_semana = None       # label 'dd/mm/yyyy' da semana selecionada
        if 'ultima_selecao_semana' not in st.session_state:
            st.session_state.ultima_selecao_semana = None  # evita reprocessar o mesmo evento

        nivel = st.session_state.drill_level
        ctx = st.session_state.drill_contexto

        # Filtragem pelo contexto do drill
        df_drill = df_filtrado.copy()
        if 'ano' in ctx:
            df_drill = df_drill[df_drill['Dia Fechamento'].dt.year == ctx['ano']]
        if 'mes' in ctx:
            df_drill = df_drill[df_drill['Dia Fechamento'].dt.month == ctx['mes']]
        # Filtragem adicional quando uma semana está selecionada
        if nivel == 'semana' and st.session_state.drill_semana:
            df_drill = df_drill[
                df_drill['Dia Fechamento'].dt.strftime('%d/%m/%Y') == st.session_state.drill_semana
            ]

        # ── Métricas ──────────────────────────────────────────────────────────
        saldo_total_geral = abs(df['Valor'].sum() - DESCONTO)
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric('Total em Caixa', fmt_brl(saldo_total_geral))
        with col_m2:
            st.metric('Lançamentos', f'{len(df_drill):,}'.replace(',', '.'))
        with col_m3:
            st.metric('Saldo Filtrado', fmt_brl(abs(df_drill['Valor'].sum())))

        st.markdown('---')

        # ── Tabelas ───────────────────────────────────────────────────────────
        colunas_tabela = ['Protocolo', 'Data', 'Clube', 'Liga', 'Valor']
        col_res, col_mul = st.columns(2)

        with col_res:
            df_res = df_drill[df_drill['Valor'] > 0][colunas_tabela].copy()
            st.subheader(f'Ressarcimentos — {fmt_brl(df_res["Valor"].sum())}')
            st.dataframe(df_res, width='stretch', hide_index=True)

        with col_mul:
            df_mul = df_drill[df_drill['Valor'] < 0][colunas_tabela].copy()
            df_mul['Valor'] = df_mul['Valor'].abs()
            st.subheader(f'Multas — {fmt_brl(df_mul["Valor"].sum())}')
            st.dataframe(df_mul, width='stretch', hide_index=True)

        st.markdown('---')

        # ── Navegação do drill ────────────────────────────────────────────────
        nivel_labels = {'ano': 'Ano', 'mes': 'Mês', 'semana': 'Semana'}
        col_nav1, col_nav2, col_nav3 = st.columns([1, 1, 4])

        with col_nav1:
            if nivel != 'ano':
                if st.button('⬆️ Subir nível'):
                    if nivel == 'mes':
                        st.session_state.drill_level = 'ano'
                        st.session_state.drill_contexto = {}
                        st.session_state.drill_semana = None
                    elif nivel == 'semana':
                        st.session_state.drill_level = 'mes'
                        st.session_state.drill_contexto.pop('mes', None)
                        st.session_state.drill_semana = None
                    st.rerun()

        with col_nav2:
            if nivel == 'semana' and st.session_state.drill_semana:
                if st.button('✖️ Limpar seleção'):
                    # Marca a seleção atual como "já processada" para o próximo evento
                    # não reativar a semana que ainda pode estar selecionada no gráfico
                    st.session_state.ultima_selecao_semana = st.session_state.drill_semana
                    st.session_state.drill_semana = None
                    st.rerun()

        with col_nav3:
            breadcrumb = 'Todos os anos'
            if 'ano' in ctx:
                breadcrumb += f' › {ctx["ano"]}'
            if 'mes' in ctx:
                breadcrumb += f' › {NOMES_MESES[ctx["mes"]]}'
            if nivel == 'semana' and st.session_state.drill_semana:
                breadcrumb += f' › semana {st.session_state.drill_semana}'
                hint = ' &nbsp;|&nbsp; Clique em uma barra para selecionar / ✖️ para limpar'
            elif nivel == 'semana':
                hint = ' &nbsp;|&nbsp; Clique em uma barra para filtrar os dados'
            else:
                hint = ' &nbsp;|&nbsp; Clique em uma barra para detalhar'
            st.markdown(f'**Nível:** {nivel_labels[nivel]} &nbsp;|&nbsp; {breadcrumb}{hint}')

        # ── Agregação conforme nível ──────────────────────────────────────────
        # Para o gráfico, sempre sem o filtro de semana selecionada
        df_drill_grafico = df_filtrado.copy()
        if 'ano' in ctx:
            df_drill_grafico = df_drill_grafico[df_drill_grafico['Dia Fechamento'].dt.year == ctx['ano']]
        if 'mes' in ctx:
            df_drill_grafico = df_drill_grafico[df_drill_grafico['Dia Fechamento'].dt.month == ctx['mes']]

        if nivel == 'ano':
            df_agg_drill = (
                df_filtrado
                .groupby(df_filtrado['Dia Fechamento'].dt.year.rename('Período'))['Valor']
                .sum().reset_index()
            )
            df_agg_drill['Período'] = df_agg_drill['Período'].astype(str)
            titulo_drill = 'Saldo por Ano'

        elif nivel == 'mes':
            df_ano_sel = df_filtrado[df_filtrado['Dia Fechamento'].dt.year == ctx['ano']]
            df_agg_drill = (
                df_ano_sel
                .groupby(df_ano_sel['Dia Fechamento'].dt.month)['Valor']
                .sum().reset_index()
            )
            df_agg_drill.columns = ['Mês Num', 'Valor']
            df_agg_drill['Período'] = df_agg_drill['Mês Num'].map(NOMES_MESES)
            df_agg_drill = df_agg_drill.sort_values('Mês Num')
            titulo_drill = f'Saldo por Mês — {ctx["ano"]}'

        else:  # semana
            df_agg_drill = (
                df_drill_grafico
                .groupby('Dia Fechamento')['Valor']
                .sum().reset_index()
            )
            df_agg_drill['Período'] = df_agg_drill['Dia Fechamento'].dt.strftime('%d/%m/%Y')
            titulo_drill = f'Saldo por Semana — {NOMES_MESES[ctx["mes"]]}/{ctx["ano"]}'

        df_agg_drill['Tipo'] = df_agg_drill['Valor'].apply(
            lambda x: 'Crédito' if x >= 0 else 'Débito'
        )
        df_agg_drill['Label'] = df_agg_drill['Valor'].apply(lambda v: fmt_brl(abs(v)))


        has_neg = (df_agg_drill['Valor'] < 0).any()
        has_pos = (df_agg_drill['Valor'] > 0).any()
        max_abs = df_agg_drill['Valor'].abs().max()
        if has_neg and has_pos:
            yrange = [df_agg_drill['Valor'].min() * 1.30, df_agg_drill['Valor'].max() * 1.30]
        elif has_neg:
            yrange = [df_agg_drill['Valor'].min() * 1.30, max_abs * 0.15]
        else:
            yrange = [0, max_abs * 1.30]

        ordem_periodos = df_agg_drill['Período'].tolist()

        fig_drill = px.bar(
            df_agg_drill, x='Período', y='Valor', color='Tipo', text='Label',
            color_discrete_map={'Crédito': '#1F77B4', 'Débito': '#D62728'},
            title=titulo_drill, labels={'Valor': 'Saldo', 'Período': ''},
            category_orders={'Período': ordem_periodos},
        )
        fig_drill.update_traces(textposition='outside', cliponaxis=False)
        if nivel == 'semana' and st.session_state.drill_semana:
            semana_sel = st.session_state.drill_semana
            for trace in fig_drill.data:
                trace.marker.line.color = 'black'
                trace.marker.line.width = [
                    3 if x == semana_sel else 0 for x in trace.x
                ]
        fig_drill.update_layout(
            font=dict(size=13), bargap=0.35,
            yaxis=dict(range=yrange),
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            showlegend=True, margin=dict(l=10, r=20, t=60, b=10),
        )

        event = st.plotly_chart(
            fig_drill, on_select='rerun', key='drill_chart', width='stretch',
        )

        # ── Drill down / seleção ao clicar ────────────────────────────────────
        if event and event.selection is not None:
            points = event.selection.points
            # Clique com barra selecionada
            if points:
                label_clicado = points[0].get('x')
                if nivel == 'ano' and label_clicado:
                    st.session_state.drill_level = 'mes'
                    st.session_state.drill_contexto = {'ano': int(label_clicado)}
                    st.session_state.drill_semana = None
                    st.session_state.ultima_selecao_semana = None
                    st.rerun()
                elif nivel == 'mes' and label_clicado:
                    mes_num = next((k for k, v in NOMES_MESES.items() if v == label_clicado), None)
                    if mes_num:
                        st.session_state.drill_level = 'semana'
                        st.session_state.drill_contexto['mes'] = mes_num
                        st.session_state.drill_semana = None
                        st.session_state.ultima_selecao_semana = None
                        st.rerun()
                elif nivel == 'semana' and label_clicado:
                    # Só processa se for um clique novo (não um evento "eco" do rerun anterior)
                    if label_clicado != st.session_state.ultima_selecao_semana:
                        st.session_state.drill_semana = label_clicado
                        st.session_state.ultima_selecao_semana = label_clicado
                        st.rerun()
            # Pontos vazios são ignorados: o Plotly emite on_select com points=[]
            # ao re-renderizar o gráfico após st.rerun(), não representa deseleção do usuário.
            # Para deselecionar, usar o botão "✖️ Limpar seleção".
