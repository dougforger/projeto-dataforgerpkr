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
        from reportlab.lib.units import cm as _cm
        larg_pag, alt_pag = doc.pagesize
        larg = larg_pag - 4 * _cm
        alt  = alt_pag  - 3 * _cm
        x    = (larg_pag - larg) / 2
        y    = (alt_pag  - alt)  / 2
        canvas.drawImage(
            logo, x, y,
            width=larg, height=alt,
            mask='auto', preserveAspectRatio=True,
        )
        canvas.restoreState()
    return _desenhar


def inicializar_pdf(protocolo: str, paisagem: bool = False, titulo_completo: str | None = None):
    """Cria buffer, doc e story com título e fonte padrão já configurados.

    Args:
        protocolo: Número do protocolo exibido no título (ignorado se titulo_completo fornecido).
        paisagem: Se True, usa orientação landscape (A4 horizontal).
        titulo_completo: Quando fornecido, substitui o título padrão 'Protocolo #xxx'.
    """
    from reportlab.lib.pagesizes import landscape
    for style in styles.byName.values():
        style.fontName = FONTE_NORMAL
    buffer       = io.BytesIO()
    pagesize     = landscape(A4) if paisagem else A4
    doc          = SimpleDocTemplate(buffer, pagesize=pagesize)
    titulo_texto = titulo_completo if titulo_completo is not None else f'Protocolo #{protocolo}'
    story        = [
        Paragraph(titulo_texto, styles['Title']),
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


def montar_tabela_comuns(df, mesas_comuns: set, coluna_nome: str | None = None) -> list:
    """Monta as linhas de tabela com ID da mesa, jogadores e link para hand history.
    Se coluna_nome for fornecida, adiciona uma coluna com o nome da mesa como segunda coluna."""
    estilo_celula = ParagraphStyle('celula', parent=styles['Normal'], wordWrap='LTR')
    header = (['ID Mesa', 'Nome da Mesa', 'Jogadores', 'Link'] if coluna_nome
              else ['ID Mesa', 'Jogadores', 'Link'])
    dados = [header]
    for id_mesa in sorted(mesas_comuns, reverse=True):
        df_mesa       = df[df['Game ID'] == id_mesa]
        ids_jogadores = df_mesa['Player ID'].unique().tolist()
        ids_url       = '&'.join(str(pid) for pid in ids_jogadores)
        link = (
            f'https://console.supremapoker.net/game/GameDetail'
            f'?backupOnly=0&dateFilter=16&matchID={id_mesa}'
            f'&page=1&pageSize=100&playerIDs={ids_url}'
        )
        linha = []
        linha.append(Paragraph(str(id_mesa), estilo_celula))
        if coluna_nome:
            nome = df_mesa[coluna_nome].iloc[0] if not df_mesa.empty else '—'
            linha.append(Paragraph(str(nome), estilo_celula))
        linha.extend([
            Paragraph(', '.join(str(pid) for pid in ids_jogadores), estilo_celula),
            Paragraph(f'<a href="{link}" color="blue"><u>Link para o Hand History</u></a>', estilo_celula),
        ])
        dados.append(linha)
    return dados


def finalizar_pdf(buffer: io.BytesIO, doc, story: list, logo=None) -> io.BytesIO:
    """Finaliza o PDF com marca d'água e retorna o buffer pronto para download."""
    logo  = logo or LOGO
    marca = _callback_marca_dagua(logo)
    doc.build(story, onFirstPage=marca, onLaterPages=marca)
    buffer.seek(0)
    return buffer
