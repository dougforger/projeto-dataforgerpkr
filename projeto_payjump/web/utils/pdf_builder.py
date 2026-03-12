import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table

from .pdf_config import (
    LOGO, styles,
    LARGURA_PAGINA, ALTURA_PAGINA,
    ESTILO_TABELA, FONTE_NORMAL,
)


def _callback_marca_dagua(logo):
    def _desenhar(canvas, doc):
        canvas.saveState()
        canvas.setFillAlpha(0.1)
        larg_pag, alt_pag = A4
        x = (larg_pag - LARGURA_PAGINA) / 2
        y = (alt_pag  - ALTURA_PAGINA)  / 2
        canvas.drawImage(
            logo, x, y,
            width=LARGURA_PAGINA, height=ALTURA_PAGINA,
            mask='auto', preserveAspectRatio=True,
        )
        canvas.restoreState()
    return _desenhar


def inicializar_pdf(protocolo: str):
    """Cria buffer, doc e story com título e fonte padrão já configurados."""
    for style in styles.byName.values():
        style.fontName = FONTE_NORMAL
    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4)
    story  = [
        Paragraph(f'Protocolo #{protocolo}', styles['Title']),
        Spacer(1, 12),
    ]
    return buffer, doc, story


def adicionar_tabela(story: list, linhas: list, larguras_colunas: list, espacamento: int = 12):
    """Cria Table com estilo padrão e adiciona ao story."""
    tabela = Table(linhas, colWidths=larguras_colunas)
    tabela.setStyle(ESTILO_TABELA)
    story.append(tabela)
    story.append(Spacer(1, espacamento))


def adicionar_alerta_compartilhamento(
    story: list,
    df,
    coluna_grupo: str,
    coluna_jogador: str,
    msg_alerta: str,
    msg_ok: str,
):
    """Detecta itens compartilhados (groupby > 1) e adiciona parágrafo de alerta ou sucesso.
    Use {n} em msg_alerta para incluir a contagem de itens compartilhados."""
    contagem       = df.groupby(coluna_grupo)[coluna_jogador].nunique()
    compartilhados = contagem[contagem > 1]
    if not compartilhados.empty:
        story.append(Paragraph(msg_alerta.format(n=len(compartilhados)), styles['Normal']))
    else:
        story.append(Paragraph(msg_ok, styles['Normal']))


def montar_tabela_comuns(df, mesas_comuns: set) -> list:
    """Monta as linhas de tabela com ID da mesa, jogadores e link para hand history."""
    estilo_celula = ParagraphStyle('celula', parent=styles['Normal'], wordWrap='LTR')
    dados = [['ID Mesa', 'Jogadores', 'Link']]
    for mesa in sorted(mesas_comuns, reverse=True):
        df_mesa       = df[df['Game ID'] == mesa]
        ids_jogadores = df_mesa['Player ID'].unique().tolist()
        ids_url       = '&'.join(str(pid) for pid in ids_jogadores)
        link = (
            f'https://console.supremapoker.net/game/GameDetail'
            f'?backupOnly=0&dateFilter=16&matchID={mesa}'
            f'&page=1&pageSize=100&playerIDs={ids_url}'
        )
        dados.append([
            Paragraph(str(mesa), estilo_celula),
            Paragraph(', '.join(str(pid) for pid in ids_jogadores), estilo_celula),
            Paragraph(f'<a href="{link}" color="blue"><u>Link para o Hand History</u></a>', estilo_celula),
        ])
    return dados


def finalizar_pdf(buffer: io.BytesIO, doc, story: list, logo=None) -> io.BytesIO:
    """Finaliza o PDF com marca d'água e retorna o buffer pronto para download."""
    logo  = logo or LOGO
    marca = _callback_marca_dagua(logo)
    doc.build(story, onFirstPage=marca, onLaterPages=marca)
    buffer.seek(0)
    return buffer
