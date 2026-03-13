from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape as _landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
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

# -----------------------------------------------------
# ESTILOS
# -----------------------------------------------------
styles = getSampleStyleSheet()
styles['Title'].alignment = TA_LEFT

LARGURA_PAGINA          = A4[0] - 4 * cm
ALTURA_PAGINA           = A4[1] - 3 * cm
LARGURA_PAGINA_PAISAGEM = _landscape(A4)[0] - 4 * cm

COLS_2 = [LARGURA_PAGINA * 0.50] * 2
COLS_3 = [LARGURA_PAGINA * 0.30, LARGURA_PAGINA * 0.30, LARGURA_PAGINA * 0.40]
COLS_4 = [LARGURA_PAGINA * 0.25] * 4
COLS_5 = [LARGURA_PAGINA * 0.20] * 5
COLS_6 = [LARGURA_PAGINA * 0.125, LARGURA_PAGINA * 0.125, LARGURA_PAGINA * 0.3,
          LARGURA_PAGINA * 0.15, LARGURA_PAGINA * 0.15, LARGURA_PAGINA * 0.15] 

ESTILO_TABELA = TableStyle([
    ('FONTNAME',   (0, 0), (-1,  0), FONTE_NEGRITO_ITALICO),
    ('FONTNAME',   (0, 1), (-1, -1), FONTE_NORMAL),
    ('BACKGROUND', (0, 0), (-1,  0), colors.grey),
    ('TEXTCOLOR',  (0, 0), (-1,  0), colors.whitesmoke),
    ('GRID',       (0, 0), (-1, -1), 0.5, colors.black),
    ('VALIGN',     (0, 0), (-1, -1), 'TOP'),
])

ESTILO_PARAGRAFO = ParagraphStyle(
    'paragrafo_custom',
    parent=styles['Normal'],
    alignment=TA_JUSTIFY,
    spaceAfter=8,
    spaceBefore=8,
    firstLineIndent=20,
    wordWrap='LTR',
    fontName=FONTE_NORMAL,
)

ESTILO_LEGENDA = ParagraphStyle(
    'legenda_tabela',
    parent=styles['Normal'],
    alignment=TA_JUSTIFY,
    fontName=FONTE_ITALICO,
    fontSize=10,
    textColor=colors.HexColor('#555555'),
    spaceBefore=4,
    spaceAfter=2,
)

LOGO = ImageReader(BASE_DIR / 'img' / 'LOGO PRETO.png')

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
