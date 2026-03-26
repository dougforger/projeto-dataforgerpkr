from io import BytesIO
from pathlib import Path

import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle

_BASE_DIR  = Path(__file__).parent.parent
_FONTS_DIR = _BASE_DIR / 'fonts'
_IMG_DIR   = _BASE_DIR / 'img'

_FONT_LIGHT = _FONTS_DIR / 'calibril.ttf'
_FONT_BOLD  = _FONTS_DIR / 'calibrib.ttf'
_LOGO_PATH  = _IMG_DIR / 'LOGO PRETO DEITADO.png'

try:
    font_manager.fontManager.addfont(str(_FONT_LIGHT))
    font_manager.fontManager.addfont(str(_FONT_BOLD))
except Exception:
    pass

_COR_AMBER       = '#F0A64D'
_COR_AMBER_ESC   = '#C47E20'
_COR_AMBER_CLARO = '#FEF6E8'
_COR_BORDA       = '#DDDDDD'
_COR_TEXTO       = '#1C1C1C'
_COR_SUAVE       = '#777777'


def _fp(bold: bool = False, size: int = 11) -> FontProperties:
    try:
        fname = str(_FONT_BOLD if bold else _FONT_LIGHT)
        return FontProperties(fname=fname, size=size)
    except Exception:
        return FontProperties(family='sans-serif', weight='bold' if bold else 'normal', size=size)


def _col_widths(cols: list, rows: list) -> list[float]:
    """Larguras normalizadas baseadas no comprimento máximo do conteúdo de cada coluna."""
    lens = []
    for j, col in enumerate(cols):
        ml = max(len(str(col)), *(len(str(r[j])) for r in rows), 3)
        lens.append(ml)
    total = sum(lens)
    return [l / total for l in lens]


def gerar_imagem_df(
    df: pd.DataFrame,
    formatar_colunas: list[str] | None = None,
    titulo: str | None = None,
) -> bytes:
    """Exporta um DataFrame como PNG branded com identidade visual da Suprema.

    Estrutura vertical: logo · linha âmbar · título · tabela · linha cinza · rodapé.
    Todos os elementos são posicionados em coordenadas absolutas (polegadas) para
    garantir espaçamento preciso, independentemente do número de linhas da tabela.
    """
    # ── Preparar dados ────────────────────────────────────────────────────────
    df_fmt = df.copy()
    if formatar_colunas:
        for col in formatar_colunas:
            if col in df_fmt.columns:
                df_fmt[col] = df_fmt[col].apply(
                    lambda v: f'{v:,.2f}' if pd.notna(v) and v != '' else (str(v) if pd.notna(v) else '')
                )

    cols   = list(df_fmt.columns)
    rows   = [list(row) for _, row in df_fmt.iterrows()]
    n_rows = len(rows)

    # ── Constantes de layout (polegadas) ─────────────────────────────────────
    fig_w      = 10.5   # largura da figura
    _pad_x     = 0.05   # margem horizontal (fração da figura)

    _top_m     = 0.20   # margem superior
    _logo_h    = 0.50   # altura do logo
    _gap_la    = 0.18   # logo → linha âmbar
    _gap_at    = 0.14   # linha âmbar → título
    _title_h   = 0.30   # altura da linha de título
    _gap_tt    = 0.22   # título → tabela
    _head_h    = 0.54   # altura da linha de cabeçalho da tabela
    _row_h     = 0.52   # altura de cada linha de dados
    _gap_tg    = 0.22   # tabela → linha cinza
    _gap_gf    = 0.14   # linha cinza → rodapé
    _ftr_h     = 0.40   # altura do bloco de rodapé (2 linhas)
    _bot_m     = 0.16   # margem inferior

    tbl_h = _head_h + n_rows * _row_h

    # Altura total da figura (soma de todos os segmentos)
    fig_h = (_top_m + _logo_h + _gap_la + _gap_at + _title_h +
             _gap_tt + tbl_h + _gap_tg + _gap_gf + _ftr_h + _bot_m)

    # ── Posições absolutas (em polegadas a partir da base da figura) ──────────
    # Calculadas de baixo para cima.
    def n(y_in: float) -> float:
        """Converte polegadas (base=0) para coordenada normalizada da figura."""
        return y_in / fig_h

    p_ftr_bot   = _bot_m
    p_gray      = p_ftr_bot + _ftr_h + _gap_gf
    p_tbl_bot   = p_gray + _gap_tg
    p_tbl_top   = p_tbl_bot + tbl_h
    p_title_bot = p_tbl_top + _gap_tt
    p_amber     = p_title_bot + _title_h + _gap_at
    p_logo_bot  = p_amber + _gap_la
    p_logo_top  = p_logo_bot + _logo_h

    fig = plt.figure(figsize=(fig_w, fig_h), facecolor='white')

    # ── Logo ──────────────────────────────────────────────────────────────────
    try:
        logo_img        = plt.imread(str(_LOGO_PATH))
        lr, lc          = logo_img.shape[:2]
        logo_w_fig_frac = (_logo_h / fig_h) * (lc / lr) * (fig_h / fig_w)
        ax_logo = fig.add_axes([
            _pad_x,
            n(p_logo_bot),
            logo_w_fig_frac,
            n(_logo_h),
        ])
        ax_logo.imshow(logo_img)
        ax_logo.axis('off')
    except Exception:
        pass

    # ── Linha âmbar ───────────────────────────────────────────────────────────
    fig.add_artist(Rectangle(
        (_pad_x, n(p_amber)),
        1.0 - 2 * _pad_x,
        0.004,
        transform=fig.transFigure,
        color=_COR_AMBER,
        clip_on=False,
        zorder=10,
    ))

    # ── Título ────────────────────────────────────────────────────────────────
    if titulo:
        fig.text(
            _pad_x,
            n(p_title_bot + _title_h * 0.5),
            titulo,
            ha='left', va='center',
            fontproperties=_fp(bold=True, size=14),
            color=_COR_TEXTO,
            transform=fig.transFigure,
        )

    # ── Tabela ────────────────────────────────────────────────────────────────
    ax = fig.add_axes([
        _pad_x,
        n(p_tbl_bot),
        1.0 - 2 * _pad_x,
        n(tbl_h),
    ])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, n_rows + 1)   # +1 para linha de cabeçalho
    ax.axis('off')

    widths   = _col_widths(cols, rows)
    x_starts = [sum(widths[:i]) for i in range(len(cols))]
    _px      = 0.014   # padding horizontal interno nas células

    # Cabeçalho
    ax.add_patch(Rectangle((0, n_rows), 1, 1,
                            facecolor=_COR_AMBER, edgecolor='none', zorder=1))
    ax.axhline(n_rows, color=_COR_AMBER_ESC, lw=1.5, zorder=3)
    for col, x0 in zip(cols, x_starts):
        ax.text(x0 + _px, n_rows + 0.5, str(col),
                ha='left', va='center', color=_COR_TEXTO,
                fontproperties=_fp(bold=True, size=11), zorder=2)

    # Linhas de dados
    for i, row in enumerate(rows):
        y_top = n_rows - i
        y_bot = y_top - 1
        bg = _COR_AMBER_CLARO if i % 2 == 1 else 'white'
        ax.add_patch(Rectangle((0, y_bot), 1, 1,
                                facecolor=bg, edgecolor='none', zorder=1))
        if i < n_rows - 1:
            ax.axhline(y_bot, color=_COR_BORDA, lw=0.5, zorder=3)
        for val, x0 in zip(row, x_starts):
            ax.text(x0 + _px, y_bot + 0.5, str(val) if pd.notna(val) else '',
                    ha='left', va='center', color=_COR_TEXTO,
                    fontproperties=_fp(bold=False, size=10), zorder=2)

    # ── Linha cinza ───────────────────────────────────────────────────────────
    fig.add_artist(Rectangle(
        (_pad_x, n(p_gray)),
        1.0 - 2 * _pad_x,
        0.003,
        transform=fig.transFigure,
        color=_COR_BORDA,
        clip_on=False,
        zorder=10,
    ))

    # ── Rodapé ────────────────────────────────────────────────────────────────
    fp_ftr   = _fp(bold=False, size=9)
    line_gap = n(0.18)
    ftr_mid  = n(p_ftr_bot + _ftr_h * 0.5)

    fig.text(_pad_x, ftr_mid + line_gap * 0.5,
             'Site: securitypkr.com.br',
             ha='left', va='center',
             fontproperties=fp_ftr, color=_COR_SUAVE,
             transform=fig.transFigure)
    fig.text(_pad_x, ftr_mid - line_gap * 0.5,
             'E-mail: security@suprema.group',
             ha='left', va='center',
             fontproperties=fp_ftr, color=_COR_SUAVE,
             transform=fig.transFigure)

    # ── Exportar ──────────────────────────────────────────────────────────────
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', pad_inches=0.15)
    plt.close(fig)
    buf.seek(0)
    return buf.read()
