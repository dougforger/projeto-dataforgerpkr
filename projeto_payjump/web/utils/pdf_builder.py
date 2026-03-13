import io

import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table

from .pdf_config import (
    LOGO_DEITADO, styles,
    LARGURA_PAGINA, ALTURA_PAGINA,
    COR_BORDA, COR_DESTAQUE, COR_DESTAQUE_ESCURO, COR_TEXTO_SUAVE,
    ESTILO_CELULA, ESTILO_TABELA, FONTE_NORMAL,
)

# Margens do documento (consistentes com LARGURA_PAGINA = A4[0] - 4*cm)
_MARGEM_ESQUERDA  = 2 * cm
_MARGEM_DIREITA   = 2 * cm
_MARGEM_SUPERIOR  = 2.8 * cm   # espaço reservado para o cabeçalho
_MARGEM_INFERIOR  = 2.2 * cm   # espaço reservado para o rodapé

# Altura do logo no cabeçalho (largura calculada proporcionalmente em tempo de execução)
_LOGO_ALTURA = 1.2 * cm


def calcular_larguras_proporcional(
    df: pd.DataFrame,
    colunas: list,
    cabecalhos: list,
    largura_total: float,
    proporcao_minima: float = 0.06,
) -> list:
    '''
    Calcula larguras de coluna proporcionais ao comprimento máximo do conteúdo.

    Para cada coluna, mede o texto mais longo entre o cabeçalho e os dados da coluna.
    A proporção de cada coluna é: comprimento_maximo / total_caracteres.
    `proporcao_minima` garante que nenhuma coluna fique estreita demais (padrão: 6% da largura).
    A soma das larguras retornadas é sempre exatamente `largura_total`.

    Args:
        df: DataFrame com os dados da tabela (usado para medir o conteúdo).
        colunas: Nomes das colunas no DataFrame, na mesma ordem dos cabecalhos.
        cabecalhos: Textos de cabeçalho exibidos na tabela.
        largura_total: Largura total disponível para a tabela (em pontos ReportLab).
        proporcao_minima: Menor fração da largura que uma coluna pode receber (padrão: 6%).

    Returns:
        Lista de larguras em pontos, uma por coluna, somando `largura_total`.
    '''
    comprimentos_maximos = [
        max(len(cab), int(df[col].fillna('—').astype(str).str.len().max()))
        for col, cab in zip(colunas, cabecalhos)
    ]
    total_caracteres  = sum(comprimentos_maximos)
    proporcoes_brutas = [max(proporcao_minima, comp / total_caracteres)
                         for comp in comprimentos_maximos]
    soma_proporcoes   = sum(proporcoes_brutas)
    return [largura_total * prop / soma_proporcoes for prop in proporcoes_brutas]


def _callback_cabecalho_rodape(canvas, doc):
    """Desenha cabeçalho (logo) e rodapé (site + e-mail) em todas as páginas."""
    canvas.saveState()

    pagina_largura, pagina_altura = canvas._pagesize
    x_esq = _MARGEM_ESQUERDA
    x_dir = pagina_largura - _MARGEM_DIREITA

    # ── CABEÇALHO — logo proporcional no canto superior esquerdo ────────────
    img_largura_px, img_altura_px = LOGO_DEITADO.getSize()
    logo_largura = _LOGO_ALTURA * img_largura_px / img_altura_px   # mantém proporção
    logo_y       = pagina_altura - _MARGEM_SUPERIOR + 0.4 * cm     # dentro da margem superior

    canvas.drawImage(
        LOGO_DEITADO,
        x=x_esq,
        y=logo_y,
        width=logo_largura,
        height=_LOGO_ALTURA,
        mask='auto',
    )

    # Linha separadora âmbar abaixo do cabeçalho
    sep_y_cabecalho = pagina_altura - _MARGEM_SUPERIOR + 0.1 * cm
    canvas.setStrokeColor(COR_DESTAQUE)
    canvas.setLineWidth(1)
    canvas.line(x_esq, sep_y_cabecalho, x_dir, sep_y_cabecalho)

    # ── RODAPÉ — duas linhas de texto no canto inferior esquerdo ────────────
    # Linha separadora cinza acima do rodapé
    sep_y_rodape = _MARGEM_INFERIOR - 0.3 * cm
    canvas.setStrokeColor(COR_BORDA)
    canvas.setLineWidth(0.5)
    canvas.line(x_esq, sep_y_rodape, x_dir, sep_y_rodape)

    canvas.setFont(FONTE_NORMAL, 8)
    canvas.setFillColor(COR_TEXTO_SUAVE)
    canvas.drawString(x_esq, _MARGEM_INFERIOR - 0.9 * cm, 'Site: securitypkr.com.br')
    canvas.drawString(x_esq, _MARGEM_INFERIOR - 1.4 * cm, 'E-mail: security@suprema.group')

    canvas.restoreState()


def inicializar_pdf(protocolo: str, paisagem: bool = False, titulo_completo: str | None = None):
    """Cria buffer, doc e story com título e margens configurados para cabeçalho/rodapé.

    Args:
        protocolo: Número do protocolo exibido no título (ignorado se titulo_completo fornecido).
        paisagem: Se True, usa orientação landscape (A4 horizontal).
        titulo_completo: Quando fornecido, substitui o título padrão 'Protocolo #xxx'.
    """
    from reportlab.lib.pagesizes import landscape
    for style in styles.byName.values():
        style.fontName = FONTE_NORMAL

    buffer   = io.BytesIO()
    pagesize = landscape(A4) if paisagem else A4
    doc      = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        leftMargin=_MARGEM_ESQUERDA,
        rightMargin=_MARGEM_DIREITA,
        topMargin=_MARGEM_SUPERIOR,
        bottomMargin=_MARGEM_INFERIOR,
    )
    titulo_texto = titulo_completo if titulo_completo is not None else f'Protocolo #{protocolo}'
    story = [
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


def montar_tabela_comuns(
    df,
    mesas_comuns: set,
    coluna_nome: str | None = None,
    largura_total: float | None = None,
) -> tuple[list, list]:
    """Monta linhas e larguras de tabela de mesas/torneios em comum.

    Retorna (linhas, larguras) para uso direto em adicionar_tabela().
    As larguras são calculadas proporcionalmente ao conteúdo quando `largura_total` é fornecido.

    Args:
        df: DataFrame original com os dados de hands/torneios.
        mesas_comuns: Conjunto de Game IDs a incluir na tabela.
        coluna_nome: Nome da coluna em df com o nome da mesa (ex: 'NOME_MESA').
                     Quando fornecido, adiciona segunda coluna com o nome da mesa.
        largura_total: Largura total disponível (em pontos ReportLab). Quando fornecido,
                       calcula larguras proporcionais. Sem este parâmetro, distribui igualmente.
    """
    cabecalhos = (
        ['ID Mesa', 'Nome da Mesa', 'Jogadores', 'Link para Hand History']
        if coluna_nome
        else ['ID Mesa', 'Jogadores', 'Link para Hand History']
    )

    dados_texto: list[list] = []   # versão texto: usada para calcular larguras proporcionais
    linhas_celulas: list    = [cabecalhos]   # linhas reais da tabela (com Paragraph)

    for id_mesa in sorted(mesas_comuns, reverse=True):
        df_mesa       = df[df['Game ID'] == id_mesa]
        ids_jogadores = df_mesa['Player ID'].unique().tolist()
        ids_url       = '&'.join(str(pid) for pid in ids_jogadores)
        link_url      = (
            f'https://console.supremapoker.net/game/GameDetail'
            f'?backupOnly=0&dateFilter=16&matchID={id_mesa}'
            f'&page=1&pageSize=100&playerIDs={ids_url}'
        )
        jogadores_str = ', '.join(str(pid) for pid in ids_jogadores)

        linha_texto   = [str(id_mesa)]
        linha_celulas = [Paragraph(str(id_mesa), ESTILO_CELULA)]

        if coluna_nome:
            nome = df_mesa[coluna_nome].iloc[0] if not df_mesa.empty else '—'
            linha_texto.append(str(nome))
            linha_celulas.append(Paragraph(str(nome), ESTILO_CELULA))

        linha_texto.extend([jogadores_str, 'Link para o Hand History'])
        linha_celulas.extend([
            Paragraph(jogadores_str, ESTILO_CELULA),
            Paragraph(f'<a href="{link_url}" color="blue"><u>Link</u></a>', ESTILO_CELULA),
        ])

        dados_texto.append(linha_texto)
        linhas_celulas.append(linha_celulas)

    if largura_total and dados_texto:
        df_temp  = pd.DataFrame(dados_texto, columns=cabecalhos)
        larguras = calcular_larguras_proporcional(df_temp, cabecalhos, cabecalhos, largura_total)
    else:
        # Fallback: distribuição igual entre as colunas
        numero_colunas = len(cabecalhos)
        larguras       = [LARGURA_PAGINA / numero_colunas] * numero_colunas

    return linhas_celulas, larguras


def finalizar_pdf(buffer: io.BytesIO, doc, story: list, logo=None) -> io.BytesIO:
    """Finaliza o PDF com cabeçalho/rodapé institucionais e retorna o buffer."""
    doc.build(story, onFirstPage=_callback_cabecalho_rodape, onLaterPages=_callback_cabecalho_rodape)
    buffer.seek(0)
    return buffer
