"""Geração do PDF do Dashboard Pipefy — Security PKR.

Segue o padrão do projeto: ReportLab + pdf_config.py (fontes Calibri Light,
ESTILO_LEGENDA, LOGO_DEITADO, ESTILO_TABELA). Sem código Streamlit.
"""
import io
import textwrap

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from reportlab.lib.units import cm
from reportlab.platypus import Image as RLImage, Paragraph, Spacer, Table

from .pdf_builder import adicionar_tabela, finalizar_pdf, inicializar_pdf
from .pdf_config import (
    COR_DESTAQUE_HEX,
    ESTILO_LEGENDA,
    ESTILO_SECAO,
    ESTILO_TABELA,
    LARGURA_PAGINA,
)

OPCOES_GRAFICOS = [
    'Resultado das Análises',
    'Internos × Denúncias',
    'Quantidade por Categoria',
    'Tabela Resumo por Categoria',
    'Quantidade por Analista',
]

OPCOES_METRICAS = [
    'Total de Protocolos',
    'Positivos vs Total',
    'Internos vs Positivos',
    'Investigações Internas',
    'Denúncias',
    'Média por Dia',
]

# Cores institucionais dos gráficos
_COR_NEGATIVO = '#95A5A6'   # cinza neutro — sem infração confirmada
_COR_ANALISTA = '#8E44AD'


# -----------------------------------------------------
# HELPERS
# -----------------------------------------------------

def _fig_para_rl_image(fig, largura: float) -> RLImage:
    """Salva figura matplotlib como PNG em memória e retorna RLImage."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=150, facecolor='white')
    plt.close(fig)
    buf.seek(0)
    # Calcula altura proporcional à figura (figsize é em polegadas, ratio w/h)
    fig_w, fig_h = fig.get_size_inches()
    altura = largura * (fig_h / fig_w)
    return RLImage(buf, width=largura, height=altura)


def _fmt_lista(selecionados: list, todos: list) -> str:
    """Retorna 'Todos' se tudo foi selecionado, ou os itens separados por vírgula."""
    if set(selecionados) >= set(todos):
        return 'Todos'
    return ', '.join(selecionados) if selecionados else '—'


# -----------------------------------------------------
# MÉTRICAS E GRÁFICOS
# -----------------------------------------------------

def _metricas_como_cards(itens: list[dict], largura: float) -> list:
    """Renderiza métricas como cards estilo Streamlit (label + valor + delta) em matplotlib."""
    n = len(itens)
    if not n:
        return []

    fig, axes = plt.subplots(1, n, figsize=(10, 1.8), facecolor='white')
    if n == 1:
        axes = [axes]

    for ax, item in zip(axes, itens):
        ax.set_facecolor('white')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        # Acento âmbar no topo
        ax.plot([0.04, 0.96], [0.97, 0.97], color='#F0A64D', linewidth=2.5,
                transform=ax.transAxes, clip_on=False, solid_capstyle='butt')
        # Label — com wrapping para caber em 2 linhas se necessário
        label_wrapped = '\n'.join(textwrap.wrap(item['label'], width=16))
        ax.text(0.06, 0.88, label_wrapped, transform=ax.transAxes,
                fontsize=10, color='#777777', va='top', ha='left', linespacing=1.2)
        # Valor
        ax.text(0.06, 0.44, item['valor'], transform=ax.transAxes,
                fontsize=20, fontweight='bold', color='#1C1C1C', va='center', ha='left')
        # Delta
        if item.get('delta'):
            ax.text(0.06, 0.10, item['delta'], transform=ax.transAxes,
                    fontsize=9, color='#777777', va='bottom', ha='left')

    fig.subplots_adjust(wspace=0.10, left=0.01, right=0.99, top=0.90, bottom=0.06)
    return [_fig_para_rl_image(fig, largura), Spacer(1, 8)]


def _grafico_tipo(df: pd.DataFrame, largura: float) -> list:
    """Barra horizontal 100% stacked: Denúncias (cinza) × Investigações Internas (âmbar)."""
    total = len(df)
    n_interno = (df['tipo'] == 'Investigação interna').sum()
    n_denuncia = (df['tipo'] == 'Denúncia').sum()
    pct_denuncia = n_denuncia / total * 100 if total else 0
    pct_interno = n_interno / total * 100 if total else 0

    fig, ax = plt.subplots(figsize=(10, 1.4))
    ax.barh([''], [pct_denuncia], color=_COR_NEGATIVO, label=f'Denúncias ({n_denuncia:,})')
    ax.barh([''], [pct_interno], left=[pct_denuncia], color=COR_DESTAQUE_HEX,
            label=f'Investigações Internas ({n_interno:,})')

    if pct_denuncia > 6:
        ax.text(pct_denuncia / 2, 0, f'{pct_denuncia:.1f}%',
                ha='center', va='center', color='white', fontsize=12, fontweight='bold')
    if pct_interno > 6:
        ax.text(pct_denuncia + pct_interno / 2, 0, f'{pct_interno:.1f}%',
                ha='center', va='center', color='white', fontsize=12, fontweight='bold')

    ax.set_xlim(0, 100)
    ax.set_xlabel('%', fontsize=9)
    ax.legend(loc='upper right', fontsize=9, frameon=False)
    ax.spines[['top', 'right', 'left']].set_visible(False)
    ax.tick_params(left=False, labelsize=9)
    ax.set_yticklabels([])
    fig.tight_layout()

    return [_fig_para_rl_image(fig, largura), Spacer(1, 10)]


def _grafico_resultado(df: pd.DataFrame, largura: float) -> list:
    """Barra horizontal 100% stacked: Negativo × Positivo."""
    total = len(df)
    n_neg = (df['resultado'] == 'Negativo').sum()
    n_pos = (df['resultado'] == 'Positivo').sum()
    pct_neg = n_neg / total * 100 if total else 0
    pct_pos = n_pos / total * 100 if total else 0

    fig, ax = plt.subplots(figsize=(10, 1.4))
    ax.barh([''], [pct_neg], color=_COR_NEGATIVO, label=f'Negativos ({n_neg:,})')
    ax.barh([''], [pct_pos], left=[pct_neg], color=COR_DESTAQUE_HEX, label=f'Positivos ({n_pos:,})')

    if pct_neg > 6:
        ax.text(pct_neg / 2, 0, f'{pct_neg:.1f}%',
                ha='center', va='center', color='white', fontsize=12, fontweight='bold')
    if pct_pos > 6:
        ax.text(pct_neg + pct_pos / 2, 0, f'{pct_pos:.1f}%',
                ha='center', va='center', color='white', fontsize=12, fontweight='bold')

    ax.set_xlim(0, 100)
    ax.set_xlabel('%', fontsize=9)
    ax.legend(loc='upper right', fontsize=9, frameon=False)
    ax.spines[['top', 'right', 'left']].set_visible(False)
    ax.tick_params(left=False, labelsize=9)
    ax.set_yticklabels([])
    fig.tight_layout()

    return [_fig_para_rl_image(fig, largura), Spacer(1, 10)]


def _grafico_categoria(df: pd.DataFrame, largura: float) -> list:
    """Barra horizontal stacked positivo/negativo por categoria."""
    cat_res = df.groupby('categoria')['resultado'].value_counts().unstack(fill_value=0)
    for col in ['Positivo', 'Negativo']:
        if col not in cat_res.columns:
            cat_res[col] = 0
    cat_res['Total'] = cat_res['Positivo'] + cat_res['Negativo']
    cat_res = cat_res.sort_values('Total', ascending=True)  # ascending → maior no topo (barh)

    cats = cat_res.index.tolist()
    neg_vals = cat_res['Negativo'].tolist()
    pos_vals = cat_res['Positivo'].tolist()

    altura = max(2.5, len(cats) * 0.6)
    fig, ax = plt.subplots(figsize=(10, altura))
    ax.barh(cats, neg_vals, color=_COR_NEGATIVO, label='Negativos')
    ax.barh(cats, pos_vals, left=neg_vals, color=COR_DESTAQUE_HEX, label='Positivos')

    grand_total = sum(neg_vals) + sum(pos_vals)
    max_x = max((n + p) for n, p in zip(neg_vals, pos_vals)) if cats else 1
    ax.set_xlim(0, max_x * 1.40)

    for i, (neg, pos) in enumerate(zip(neg_vals, pos_vals)):
        if neg > 0:
            ax.text(neg / 2, i, str(neg), ha='center', va='center',
                    color='white', fontsize=8, fontweight='bold')
        if pos > 0:
            ax.text(neg + pos / 2, i, str(pos), ha='center', va='center',
                    color='white', fontsize=8, fontweight='bold')
        # label externo: total + %
        total_bar = neg + pos
        pct = total_bar / grand_total * 100 if grand_total else 0
        ax.text(total_bar + max_x * 0.03, i, f'{total_bar:,} ({pct:.1f}%)',
                va='center', fontsize=8)

    ax.legend(loc='lower right', fontsize=8, frameon=False)
    ax.set_xlabel('Quantidade', fontsize=9)
    ax.spines[['top', 'right']].set_visible(False)
    ax.tick_params(labelsize=9)
    fig.tight_layout()

    return [_fig_para_rl_image(fig, largura), Spacer(1, 10)]


def _tabela_categoria_pdf(df: pd.DataFrame, largura: float) -> list:
    """Tabela ReportLab: Categoria | Negativos | Positivos | Total | %"""
    cat_res = df.groupby('categoria')['resultado'].value_counts().unstack(fill_value=0)
    for col in ['Positivo', 'Negativo']:
        if col not in cat_res.columns:
            cat_res[col] = 0
    cat_res['Total'] = cat_res['Positivo'] + cat_res['Negativo']
    grand = cat_res['Total'].sum()
    cat_res['%'] = (cat_res['Total'] / grand * 100).round(1)
    cat_res = cat_res.sort_values('Total', ascending=False)

    cabecalho = ['Categoria', 'Negativos', 'Positivos', 'Total', '%']
    linhas = [cabecalho]
    for cat, row in cat_res.iterrows():
        linhas.append([
            str(cat),
            str(int(row['Negativo'])),
            str(int(row['Positivo'])),
            str(int(row['Total'])),
            f"{row['%']:.1f}%",
        ])

    col_widths = [
        largura * 0.40,
        largura * 0.15,
        largura * 0.15,
        largura * 0.15,
        largura * 0.15,
    ]
    tabela = Table(linhas, colWidths=col_widths)
    tabela.setStyle(ESTILO_TABELA)
    return [tabela, Spacer(1, 10)]


def _grafico_analista(df: pd.DataFrame, largura: float) -> list:
    """Barra horizontal por analista com contagem."""
    contagem = df['analista'].dropna().value_counts()
    # value_counts() → descrescente; [::-1] inverte para ascending (barh: maior no topo)
    analistas = contagem.index.tolist()[::-1]
    vals = contagem.values.tolist()[::-1]

    altura = max(2.5, len(analistas) * 0.55)
    fig, ax = plt.subplots(figsize=(10, altura))
    bars = ax.barh(analistas, vals, color=COR_DESTAQUE_HEX)

    for bar, val in zip(bars, vals):
        ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                str(val), va='center', fontsize=9)

    ax.set_xlim(0, max(vals) * 1.15 if vals else 10)
    ax.set_xlabel('Quantidade', fontsize=9)
    ax.spines[['top', 'right']].set_visible(False)
    ax.tick_params(labelsize=9)
    fig.tight_layout()

    return [_fig_para_rl_image(fig, largura), Spacer(1, 10)]


# -----------------------------------------------------
# FUNÇÃO PRINCIPAL
# -----------------------------------------------------

def gerar_pdf_dashboard(
    df: pd.DataFrame,
    filtros: dict,
    graficos: list[str] | None = None,
    metricas: list[str] | None = None,
) -> bytes:
    """Gera PDF do dashboard Pipefy Security PKR.

    Args:
        df: DataFrame filtrado com colunas [id, criado_em, categoria, tipo, resultado, analista].
        filtros: dict com chaves:
            data_inicial, data_final (datetime.date)
            categorias, tipos, resultados, analistas (listas selecionadas)
            ref_categorias, ref_tipos, ref_resultados, ref_analistas (listas completas, para 'Todos')
        graficos: lista de seções a incluir (usa OPCOES_GRAFICOS se None).

    Returns:
        Bytes do PDF gerado.
    """
    graficos_ativos = set(graficos if graficos is not None else OPCOES_GRAFICOS)
    metricas_ativas = set(metricas if metricas is not None else OPCOES_METRICAS)
    sns.set_theme(style='whitegrid', font_scale=1.0)

    buffer, doc, story = inicializar_pdf(
        protocolo='',
        titulo_completo='Relatório de Casos — Security PKR',
    )

    # -- Seção de filtros -------------------------------------------------------
    story.append(Paragraph('Filtros Aplicados', ESTILO_SECAO))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        'Parâmetros utilizados para a geração deste relatório.', ESTILO_LEGENDA
    ))

    data_ini = filtros['data_inicial'].strftime('%d/%m/%Y')
    data_fim = filtros['data_final'].strftime('%d/%m/%Y')

    linhas_filtros = [
        ['Filtro', 'Selecionado'],
        ['Período', f'{data_ini}  →  {data_fim}'],
        ['Categoria', _fmt_lista(filtros['categorias'], filtros['ref_categorias'])],
        ['Tipo de ocorrência', _fmt_lista(filtros['tipos'], filtros['ref_tipos'])],
        ['Resultado', _fmt_lista(filtros['resultados'], filtros['ref_resultados'])],
        ['Analistas', _fmt_lista(filtros['analistas'], filtros['ref_analistas'])],
    ]
    adicionar_tabela(story, linhas_filtros, [5 * cm, LARGURA_PAGINA - 5 * cm])
    story.append(Spacer(1, 16))

    # -- Métricas ---------------------------------------------------------------
    total = len(df)
    n_pos = (df['resultado'] == 'Positivo').sum()
    n_neg = (df['resultado'] == 'Negativo').sum()
    n_internos_pos = (
        (df['tipo'] == 'Investigação interna') & (df['resultado'] == 'Positivo')
    ).sum()
    n_interno = (df['tipo'] == 'Investigação interna').sum()
    n_denuncia = (df['tipo'] == 'Denúncia').sum()
    period_days = max(1, (filtros['data_final'] - filtros['data_inicial']).days + 1)
    media_por_dia = total / period_days
    pct_pos = n_pos / total * 100 if total else 0
    pct_int = n_internos_pos / n_pos * 100 if n_pos else 0
    pct_interno = n_interno / total * 100 if total else 0
    pct_denuncia = n_denuncia / total * 100 if total else 0

    _METRICAS_DISPONIVEIS = {
        'Total de Protocolos':   {'label': 'Total de Protocolos',   'valor': f'{total:,}',              'delta': None},
        'Positivos vs Total':    {'label': 'Positivos vs Total',    'valor': f'{n_pos:,}',              'delta': f'{pct_pos:.1f}% do total'},
        'Internos vs Positivos': {'label': 'Internos vs Positivos', 'valor': f'{n_internos_pos:,}',     'delta': f'{pct_int:.1f}% dos positivos'},
        'Investigações Internas':{'label': 'Inv. Internas',         'valor': f'{n_interno:,}',          'delta': f'{pct_interno:.1f}% do total'},
        'Denúncias':             {'label': 'Denúncias',             'valor': f'{n_denuncia:,}',         'delta': f'{pct_denuncia:.1f}% do total'},
        'Média por Dia':         {'label': 'Média por Dia',         'valor': f'{media_por_dia:.1f}',    'delta': 'casos/dia'},
    }

    itens_metricas = [
        _METRICAS_DISPONIVEIS[m] for m in OPCOES_METRICAS if m in metricas_ativas
    ]
    if itens_metricas:
        story.append(Paragraph('Métricas Gerais', ESTILO_SECAO))
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            'Resumo quantitativo dos protocolos no período e filtros selecionados.', ESTILO_LEGENDA
        ))
        story.extend(_metricas_como_cards(itens_metricas, LARGURA_PAGINA))
        story.append(Spacer(1, 16))

    # -- Gráfico: Resultado -----------------------------------------------------
    if 'Resultado das Análises' in graficos_ativos:
        story.append(Paragraph('Resultado das Análises', ESTILO_SECAO))
        story.append(Paragraph(
            'Distribuição percentual entre análises com resultado Negativo e Positivo.',
            ESTILO_LEGENDA,
        ))
        story.extend(_grafico_resultado(df, LARGURA_PAGINA))
        story.append(Spacer(1, 16))

    # -- Gráfico: Internos × Denúncias ------------------------------------------
    if 'Internos × Denúncias' in graficos_ativos:
        story.append(Paragraph('Internos × Denúncias', ESTILO_SECAO))
        story.append(Paragraph(
            'Distribuição percentual entre investigações internas e denúncias externas.',
            ESTILO_LEGENDA,
        ))
        story.extend(_grafico_tipo(df, LARGURA_PAGINA))
        story.append(Spacer(1, 16))

    # -- Gráfico: Categoria -----------------------------------------------------
    tem_categoria = 'Quantidade por Categoria' in graficos_ativos
    tem_tabela_cat = 'Tabela Resumo por Categoria' in graficos_ativos
    # if tem_categoria or tem_tabela_cat:
    #     story.append(PageBreak())
    if tem_categoria:
        story.append(Paragraph('Quantidade por Categoria', ESTILO_SECAO))
        story.append(Paragraph(
            'Distribuição dos protocolos por categoria de infração analisada, ordenada por volume.',
            ESTILO_LEGENDA,
        ))
        story.extend(_grafico_categoria(df, LARGURA_PAGINA))
        story.append(Spacer(1, 16))
    if tem_tabela_cat:
        story.append(Paragraph('Detalhamento por Categoria', ESTILO_SECAO))
        story.append(Paragraph(
            'Resumo quantitativo por categoria: negativos, positivos, total e participação percentual.',
            ESTILO_LEGENDA,
        ))
        story.extend(_tabela_categoria_pdf(df, LARGURA_PAGINA))
        story.append(Spacer(1, 16))

    # -- Gráfico: Analista ------------------------------------------------------
    if 'Quantidade por Analista' in graficos_ativos:
        story.append(Paragraph('Quantidade por Analista', ESTILO_SECAO))
        story.append(Paragraph(
            'Quantidade de protocolos atribuídos por analista no período selecionado.',
            ESTILO_LEGENDA,
        ))
        story.extend(_grafico_analista(df, LARGURA_PAGINA))

    return finalizar_pdf(buffer, doc, story).read()
