import html
import re
from datetime import date
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use('Agg')
from matplotlib import font_manager as _mpl_font_manager
from matplotlib.font_manager import FontProperties

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import TableStyle

# -----------------------------------------------------
# CAMINHOS
# -----------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
FONT_DIR = BASE_DIR / 'fonts'

# -----------------------------------------------------
# FONTES
# -----------------------------------------------------
FONTE_NORMAL          = 'CalibriLight'
FONTE_NEGRITO         = 'CalibriLight-Bold'
FONTE_ITALICO         = 'CalibriLight-Italic'
FONTE_NEGRITO_ITALICO = 'CalibriLight-BoldItalic'

pdfmetrics.registerFont(TTFont(FONTE_NORMAL,          FONT_DIR / 'calibril.ttf'))
pdfmetrics.registerFont(TTFont(FONTE_NEGRITO,         FONT_DIR / 'calibrib.ttf'))
pdfmetrics.registerFont(TTFont(FONTE_ITALICO,         FONT_DIR / 'calibrili.ttf'))
pdfmetrics.registerFont(TTFont(FONTE_NEGRITO_ITALICO, FONT_DIR / 'calibriz.ttf'))
registerFontFamily(
    FONTE_NORMAL,
    normal=FONTE_NORMAL,
    bold=FONTE_NEGRITO,
    italic=FONTE_ITALICO,
    boldItalic=FONTE_NEGRITO_ITALICO,
)

# Fonte CJK (chinês, japonês, coreano) — built-in do ReportLab, sem arquivo externo
FONTE_CJK = 'STSong-Light'
pdfmetrics.registerFont(UnicodeCIDFont(FONTE_CJK))

# Padrão Unicode para blocos CJK mais comuns
_RE_CJK = re.compile(
    r'[\u4e00-\u9fff'    # CJK Unified Ideographs (chinês/japonês/coreano)
    r'\u3400-\u4dbf'     # CJK Extension A
    r'\uac00-\ud7af'     # Hangul (coreano)
    r'\u3040-\u309f'     # Hiragana
    r'\u30a0-\u30ff'     # Katakana
    r'\uff00-\uffef]+'   # Halfwidth/Fullwidth Forms
)


def aplicar_fonte_cjk(texto: str) -> str:
    """Envolve trechos CJK em tags <font> para STSong-Light; escapa o restante para XML."""
    partes = []
    ultimo = 0
    for m in _RE_CJK.finditer(texto):
        if m.start() > ultimo:
            partes.append(html.escape(texto[ultimo:m.start()]))
        partes.append(f'<font name="{FONTE_CJK}">{m.group()}</font>')
        ultimo = m.end()
    if ultimo < len(texto):
        partes.append(html.escape(texto[ultimo:]))
    return ''.join(partes)


def tem_cjk(texto: str) -> bool:
    """Retorna True se o texto contiver algum caractere CJK."""
    return bool(_RE_CJK.search(texto))


# Fonte para símbolos de naipes (♠ ♥ ♦ ♣) — Segoe UI Symbol
FONTE_NAIPES = 'SegoeUISymbol'
pdfmetrics.registerFont(TTFont(FONTE_NAIPES, FONT_DIR / 'seguisym.ttf'))

_NAIPES_VERMELHOS = frozenset('♥♦')
_RE_NAIPES = re.compile(r'[♠♥♦♣]')


def tem_naipes(texto: str) -> bool:
    """Retorna True se o texto contiver algum símbolo de naipe."""
    return bool(_RE_NAIPES.search(texto))


def aplicar_fonte_naipes(texto: str) -> str:
    """Envolve ♠♥♦♣ em tags <font> para SegoeUISymbol com cor adequada;
    escapa o restante para XML (compatível com Paragraph do ReportLab)."""
    partes = []
    ultimo = 0
    for m in _RE_NAIPES.finditer(texto):
        if m.start() > ultimo:
            partes.append(html.escape(texto[ultimo:m.start()]))
        simbolo = m.group()
        cor = '#CC0000' if simbolo in _NAIPES_VERMELHOS else '#1C1C1C'
        partes.append(f'<font name="{FONTE_NAIPES}" color="{cor}">{simbolo}</font>')
        ultimo = m.end()
    if ultimo < len(texto):
        partes.append(html.escape(texto[ultimo:]))
    return ''.join(partes)


# -----------------------------------------------------
# PALETA DE CORES INSTITUCIONAL
# Cor principal: #F0A64D (âmbar Suprema)
# Contraste texto escuro sobre âmbar: ~6.9:1  (WCAG AA ✓)
# -----------------------------------------------------
COR_DESTAQUE        = colors.HexColor('#F0A64D')   # Âmbar institucional — fundo do cabeçalho
COR_DESTAQUE_ESCURO = colors.HexColor('#C47E20')   # Âmbar escuro — separador sob cabeçalho
COR_DESTAQUE_CLARO  = colors.HexColor('#FEF6E8')   # Âmbar muito claro — linhas pares (zebra)
COR_TEXTO           = colors.HexColor('#1C1C1C')   # Quase preto — texto principal
COR_TEXTO_SUAVE     = colors.HexColor('#555555')   # Cinza médio — legendas e texto secundário
COR_BORDA           = colors.HexColor('#DDDDDD')   # Cinza claro — borda externa e separadores

# -----------------------------------------------------
# DIMENSÕES DE PÁGINA
# -----------------------------------------------------
styles = getSampleStyleSheet()
styles['Title'].alignment = TA_LEFT

LARGURA_PAGINA = A4[0] - 4 * cm
ALTURA_PAGINA  = A4[1] - 3 * cm

# -----------------------------------------------------
# ESTILOS DE TABELA
# Design moderno: cabeçalho âmbar, sem grade densa,
# faixas alternadas (zebra) e mais espaço interno.
# -----------------------------------------------------
ESTILO_TABELA = TableStyle([
    # ── Cabeçalho ──────────────────────────────────────────────────
    ('FONTNAME',        (0, 0), (-1,  0), FONTE_NEGRITO),
    ('FONTSIZE',        (0, 0), (-1,  0), 10),
    ('BACKGROUND',      (0, 0), (-1,  0), COR_DESTAQUE),
    ('TEXTCOLOR',       (0, 0), (-1,  0), COR_TEXTO),
    ('LINEBELOW',       (0, 0), (-1,  0), 1.5, COR_DESTAQUE_ESCURO),
    # ── Corpo ──────────────────────────────────────────────────────
    ('FONTNAME',        (0, 1), (-1, -1), FONTE_NORMAL),
    ('FONTSIZE',        (0, 1), (-1, -1), 9),
    ('TEXTCOLOR',       (0, 1), (-1, -1), COR_TEXTO),
    ('ROWBACKGROUNDS',  (0, 1), (-1, -1), [colors.white, COR_DESTAQUE_CLARO]),
    ('LINEBELOW',       (0, 1), (-1, -2), 0.25, COR_BORDA),
    # ── Layout ─────────────────────────────────────────────────────
    ('ALIGN',           (0, 0), (-1, -1), 'LEFT'),
    ('VALIGN',          (0, 0), (-1, -1), 'MIDDLE'),
    ('LEFTPADDING',     (0, 0), (-1, -1), 8),
    ('RIGHTPADDING',    (0, 0), (-1, -1), 8),
    ('TOPPADDING',      (0, 0), (-1, -1), 6),
    ('BOTTOMPADDING',   (0, 0), (-1, -1), 6),
    # ── Borda externa ──────────────────────────────────────────────
    ('BOX',             (0, 0), (-1, -1), 0.75, COR_BORDA),
])

# Variante compacta — fontes e espaçamentos menores para tabelas densas (8+ colunas)
ESTILO_TABELA_COMPACTO = TableStyle([
    # ── Cabeçalho ──────────────────────────────────────────────────
    ('FONTNAME',        (0, 0), (-1,  0), FONTE_NEGRITO),
    ('FONTSIZE',        (0, 0), (-1,  0), 8),
    ('BACKGROUND',      (0, 0), (-1,  0), COR_DESTAQUE),
    ('TEXTCOLOR',       (0, 0), (-1,  0), COR_TEXTO),
    ('LINEBELOW',       (0, 0), (-1,  0), 1.5, COR_DESTAQUE_ESCURO),
    # ── Corpo ──────────────────────────────────────────────────────
    ('FONTNAME',        (0, 1), (-1, -1), FONTE_NORMAL),
    ('FONTSIZE',        (0, 1), (-1, -1), 8),
    ('TEXTCOLOR',       (0, 1), (-1, -1), COR_TEXTO),
    ('ROWBACKGROUNDS',  (0, 1), (-1, -1), [colors.white, COR_DESTAQUE_CLARO]),
    ('LINEBELOW',       (0, 1), (-1, -2), 0.25, COR_BORDA),
    # ── Layout ─────────────────────────────────────────────────────
    ('ALIGN',           (0, 0), (-1, -1), 'LEFT'),
    ('VALIGN',          (0, 0), (-1, -1), 'MIDDLE'),
    ('LEFTPADDING',     (0, 0), (-1, -1), 6),
    ('RIGHTPADDING',    (0, 0), (-1, -1), 6),
    ('TOPPADDING',      (0, 0), (-1, -1), 4),
    ('BOTTOMPADDING',   (0, 0), (-1, -1), 4),
    # ── Borda externa ──────────────────────────────────────────────
    ('BOX',             (0, 0), (-1, -1), 0.75, COR_BORDA),
])

# -----------------------------------------------------
# ESTILOS DE PARÁGRAFO
# -----------------------------------------------------

# Parágrafo de corpo — alinhamento à esquerda, espaçamento fluido
ESTILO_PARAGRAFO = ParagraphStyle(
    'paragrafo_custom',
    parent=styles['Normal'],
    alignment=TA_LEFT,
    fontSize=11,
    leading=15,
    spaceAfter=8,
    spaceBefore=8,
    fontName=FONTE_NORMAL,
    textColor=COR_TEXTO,
)

# Legenda explicativa — itálico pequeno acima de cada tabela
ESTILO_LEGENDA = ParagraphStyle(
    'legenda_tabela',
    parent=styles['Normal'],
    alignment=TA_LEFT,
    fontName=FONTE_ITALICO,
    fontSize=9,
    leading=12,
    textColor=COR_TEXTO_SUAVE,
    spaceBefore=6,
    spaceAfter=3,
)

# Célula de dados — usado em Paragraph() dentro de células de tabela
# (necessário porque ESTILO_TABELA não aplica fonte a objetos Paragraph)
ESTILO_CELULA = ParagraphStyle(
    'celula_tabela',
    parent=styles['Normal'],
    fontName=FONTE_NORMAL,
    fontSize=9,
    leading=12,
    textColor=COR_TEXTO,
    wordWrap='LTR',
)

# Variante sem quebra de linha — para colunas de ID numérico, datas, etc.
ESTILO_CELULA_NOWRAP = ParagraphStyle(
    'celula_tabela_nowrap',
    parent=ESTILO_CELULA,
    wordWrap=None,
    splitLongWords=0,
)

# Célula de cabeçalho — usado quando o cabeçalho é montado com Paragraph()
ESTILO_CABECALHO_CELULA = ParagraphStyle(
    'cabecalho_celula',
    parent=styles['Normal'],
    fontName=FONTE_NEGRITO,
    fontSize=10,
    leading=13,
    textColor=COR_TEXTO,
    wordWrap='LTR',
)

# Variante sem quebra de linha — para cabeçalhos que não devem quebrar
ESTILO_CABECALHO_CELULA_NOWRAP = ParagraphStyle(
    'cabecalho_celula_nowrap',
    parent=ESTILO_CABECALHO_CELULA,
    wordWrap=None,
    splitLongWords=0,
)

LOGO_DEITADO = ImageReader(BASE_DIR / 'img' / 'LOGO PRETO DEITADO.png')

# -----------------------------------------------------
# MATPLOTLIB — FontProperties e cores hex
# Usados por qualquer módulo que gere figuras matplotlib
# (despesas_pdf, analise_geo, etc.)
# -----------------------------------------------------
_FP_LIGHT_PATH = FONT_DIR / 'calibril.ttf'
_FP_BOLD_PATH  = FONT_DIR / 'calibrib.ttf'

for _fp in (_FP_LIGHT_PATH, _FP_BOLD_PATH):
    if _fp.exists():
        _mpl_font_manager.fontManager.addfont(str(_fp))

FP_LIGHT_9  = FontProperties(fname=str(_FP_LIGHT_PATH), size=9)  if _FP_LIGHT_PATH.exists() else None
FP_LIGHT_11 = FontProperties(fname=str(_FP_LIGHT_PATH), size=11) if _FP_LIGHT_PATH.exists() else None
FP_LIGHT_13 = FontProperties(fname=str(_FP_LIGHT_PATH), size=13) if _FP_LIGHT_PATH.exists() else None
FP_BOLD_14  = FontProperties(fname=str(_FP_BOLD_PATH),  size=14) if _FP_BOLD_PATH.exists()  else None
FP_BOLD_24  = FontProperties(fname=str(_FP_BOLD_PATH),  size=24) if _FP_BOLD_PATH.exists()  else None

# Hex strings para matplotlib (mesmos valores da paleta ReportLab acima)
COR_DESTAQUE_HEX        = '#F0A64D'
COR_DESTAQUE_ESCURO_HEX = '#C47E20'
COR_TEXTO_HEX           = '#1C1C1C'
COR_TEXTO_SUAVE_HEX     = '#555555'
COR_BORDA_HEX           = '#DDDDDD'
# Cores específicas de gráficos financeiros
COR_AZUL_CREDITO_HEX    = '#1F77B4'
COR_VERMELHO_DEB_HEX    = '#D62728'

# -----------------------------------------------------
# ESTILOS EXTRAS
# -----------------------------------------------------

# Título de seção (equivalente a Heading2 com fonte institucional)
ESTILO_SECAO = ParagraphStyle(
    'secao_titulo',
    parent=styles['Heading2'],
    fontName=FONTE_NORMAL,
    fontSize=12,
    textColor=COR_TEXTO,
    spaceBefore=10,
    spaceAfter=4,
)

# Célula compacta com word-wrap — para colunas de conteúdo longo em tabelas densas
ESTILO_CELULA_COMPACTO = ParagraphStyle(
    'celula_compacto',
    parent=ESTILO_CELULA,
    fontSize=8,
    leading=11,
)

# Tabela de índice navegável (usado no Hand History PDF)
ESTILO_TABELA_INDICE = TableStyle([
    ('SPAN',           (0, 0), (-1, 0)),
    ('FONTNAME',       (0, 0), (-1, 0), FONTE_NEGRITO),
    ('FONTSIZE',       (0, 0), (-1, 0), 10),
    ('BACKGROUND',     (0, 0), (-1, 0), COR_DESTAQUE),
    ('TEXTCOLOR',      (0, 0), (-1, 0), COR_TEXTO),
    ('ALIGN',          (0, 0), (-1, 0), 'CENTER'),
    ('LINEBELOW',      (0, 0), (-1, 0), 1.5, COR_DESTAQUE_ESCURO),
    ('FONTNAME',       (0, 1), (-1, -1), FONTE_NORMAL),
    ('FONTSIZE',       (0, 1), (-1, -1), 8),
    ('TEXTCOLOR',      (0, 1), (-1, -1), COR_TEXTO),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [COR_DESTAQUE_CLARO, COR_DESTAQUE_CLARO]),
    ('ALIGN',          (0, 1), (-1, -1), 'CENTER'),
    ('VALIGN',         (0, 0), (-1, -1), 'MIDDLE'),
    ('LEFTPADDING',    (0, 0), (-1, -1), 6),
    ('RIGHTPADDING',   (0, 0), (-1, -1), 6),
    ('TOPPADDING',     (0, 0), (-1, -1), 4),
    ('BOTTOMPADDING',  (0, 0), (-1, -1), 4),
    ('BOX',            (0, 0), (-1, -1), 0.75, COR_BORDA),
    ('INNERGRID',      (0, 1), (-1, -1), 0.25, COR_BORDA),
])

# -----------------------------------------------------
# FUNÇÕES DE FORMATAÇÃO
# Centralizar aqui garante consistência em todos os PDFs
# -----------------------------------------------------

def formatar_brl(valor: float) -> str:
    """Formata um número como moeda brasileira: R$ 1.234,56."""
    return f'R$ {valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def fmt_br(valor: float, decimais: int = 0, sinal: bool = False) -> str:
    """Formata número no padrão brasileiro sem prefixo de moeda.

    Exemplos:
        fmt_br(1234.5)           → '1.234'
        fmt_br(1234.5, 2)        → '1.234,50'
        fmt_br(-50, sinal=True)  → '-50'
        fmt_br(50, sinal=True)   → '+50'
    """
    fmt = f'{valor:+,.{decimais}f}' if sinal else f'{valor:,.{decimais}f}'
    return fmt.replace(',', 'X').replace('.', ',').replace('X', '.')


def formatar_data(valor) -> str:
    """Retorna data no formato dd/mm/aaaa, ou '—' se ausente."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return '—'
    if isinstance(valor, (date, pd.Timestamp)):
        return pd.Timestamp(valor).strftime('%d/%m/%Y')
    return str(valor)


def texto_ou_traco(valor) -> str:
    """Retorna o valor como string ou '—' se ausente/nulo."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return '—'
    texto = str(valor).strip()
    return texto if texto else '—'


# -----------------------------------------------------
# APIs EXTERNAS
# -----------------------------------------------------
URL_IP_API           = 'http://ip-api.com/batch'
URL_NOMINATIM        = 'https://nominatim.openstreetmap.org/reverse'
USER_AGENT_NOMINATIM = 'DougForgerPKR/1.0'

TIMEOUT_IP_API    = 15
TIMEOUT_NOMINATIM = 10
DELAY_NOMINATIM   = 1

LOTE_IP_API = 100

# -----------------------------------------------------
# PROCESSAMENTO DE DADOS
# -----------------------------------------------------
MULTIPLICADOR_MOEDA    = 5
LIMITE_MODALIDADE_CASH = 99
