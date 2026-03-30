"""Geração do PDF do Dashboard Pipefy — Security PKR.

Segue o padrão do projeto: ReportLab + pdf_config.py (fontes Calibri Light,
ESTILO_LEGENDA, LOGO_DEITADO, ESTILO_TABELA). Sem código Streamlit.
"""
import io

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from reportlab.lib.units import cm
from reportlab.platypus import Image as RLImage, Paragraph, Spacer

from .pdf_builder import adicionar_tabela, finalizar_pdf, inicializar_pdf
from .pdf_config import (
    ESTILO_LEGENDA,
    ESTILO_TABELA,
    LARGURA_PAGINA,
    styles,
)

# Cores institucionais dos gráficos (alinhadas com a página)
_COR_NEGATIVO = '#95A5A6'   # cinza neutro — sem infração confirmada
_COR_POSITIVO = '#F0A64D'   # âmbar Suprema — infração confirmada
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
# GRÁFICOS
# -----------------------------------------------------

def _grafico_resultado(df: pd.DataFrame, largura: float) -> list:
    """Barra horizontal 100% stacked: Negativo × Positivo."""
    total = len(df)
    n_neg = (df['resultado'] == 'Negativo').sum()
    n_pos = (df['resultado'] == 'Positivo').sum()
    pct_neg = n_neg / total * 100 if total else 0
    pct_pos = n_pos / total * 100 if total else 0

    fig, ax = plt.subplots(figsize=(10, 1.4))
    ax.barh([''], [pct_neg], color=_COR_NEGATIVO, label=f'Negativos ({n_neg:,})')
    ax.barh([''], [pct_pos], left=[pct_neg], color=_COR_POSITIVO, label=f'Positivos ({n_pos:,})')

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
    ax.barh(cats, pos_vals, left=neg_vals, color=_COR_POSITIVO, label='Positivos')

    for i, (neg, pos) in enumerate(zip(neg_vals, pos_vals)):
        if neg > 0:
            ax.text(neg / 2, i, str(neg), ha='center', va='center',
                    color='white', fontsize=8, fontweight='bold')
        if pos > 0:
            ax.text(neg + pos / 2, i, str(pos), ha='center', va='center',
                    color='white', fontsize=8, fontweight='bold')

    ax.legend(loc='lower right', fontsize=8, frameon=False)
    ax.set_xlabel('Quantidade', fontsize=9)
    ax.spines[['top', 'right']].set_visible(False)
    ax.tick_params(labelsize=9)
    fig.tight_layout()

    return [_fig_para_rl_image(fig, largura), Spacer(1, 10)]


def _grafico_analista(df: pd.DataFrame, largura: float) -> list:
    """Barra horizontal por analista com contagem."""
    contagem = df['analista'].dropna().value_counts()
    # value_counts() → descrescente; [::-1] inverte para ascending (barh: maior no topo)
    analistas = contagem.index.tolist()[::-1]
    vals = contagem.values.tolist()[::-1]

    altura = max(2.5, len(analistas) * 0.55)
    fig, ax = plt.subplots(figsize=(10, altura))
    bars = ax.barh(analistas, vals, color=_COR_ANALISTA)

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

def gerar_pdf_dashboard(df: pd.DataFrame, filtros: dict) -> bytes:
    """Gera PDF do dashboard Pipefy Security PKR.

    Args:
        df: DataFrame filtrado com colunas [id, criado_em, categoria, tipo, resultado, analista].
        filtros: dict com chaves:
            data_inicial, data_final (datetime.date)
            categorias, tipos, resultados, analistas (listas selecionadas)
            ref_categorias, ref_tipos, ref_resultados, ref_analistas (listas completas, para 'Todos')

    Returns:
        Bytes do PDF gerado.
    """
    sns.set_theme(style='whitegrid', font_scale=1.0)

    buffer, doc, story = inicializar_pdf(
        protocolo='',
        titulo_completo='Dashboard — Security PKR',
    )

    # -- Seção de filtros -------------------------------------------------------
    story.append(Paragraph('Filtros Aplicados', styles['h2']))
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
    pct_pos = n_pos / total * 100 if total else 0
    pct_int = n_internos_pos / n_pos * 100 if n_pos else 0

    story.append(Paragraph('Métricas Gerais', styles['h2']))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        'Resumo quantitativo dos protocolos no período e filtros selecionados.', ESTILO_LEGENDA
    ))
    linhas_metricas = [
        ['Total de Protocolos', 'Positivos vs Total', 'Internos vs Positivos'],
        [
            f'{total:,}',
            f'{n_pos:,}  ({pct_pos:.1f}%)',
            f'{n_internos_pos:,}  ({pct_int:.1f}%)',
        ],
    ]
    adicionar_tabela(story, linhas_metricas, [LARGURA_PAGINA / 3] * 3)
    story.append(Spacer(1, 16))

    # -- Gráfico: Resultado -----------------------------------------------------
    story.append(Paragraph('Resultado das Análises', styles['h2']))
    story.append(Paragraph(
        'Distribuição percentual entre análises com resultado Negativo e Positivo.',
        ESTILO_LEGENDA,
    ))
    story.extend(_grafico_resultado(df, LARGURA_PAGINA))
    story.append(Spacer(1, 16))

    # -- Gráfico: Categoria -----------------------------------------------------
    story.append(Paragraph('Quantidade por Categoria', styles['h2']))
    story.append(Paragraph(
        'Distribuição dos protocolos por categoria de infração analisada, ordenada por volume.',
        ESTILO_LEGENDA,
    ))
    story.extend(_grafico_categoria(df, LARGURA_PAGINA))
    story.append(Spacer(1, 16))

    # -- Gráfico: Analista ------------------------------------------------------
    story.append(Paragraph('Quantidade por Analista', styles['h2']))
    story.append(Paragraph(
        'Quantidade de protocolos atribuídos por analista no período selecionado.',
        ESTILO_LEGENDA,
    ))
    story.extend(_grafico_analista(df, LARGURA_PAGINA))

    return finalizar_pdf(buffer, doc, story).read()
