"""
Parser de arquivos HTML de Hand History exportados do backend da Suprema Poker.

Responsabilidades deste módulo:
- Separar o arquivo HTML em blocos individuais (uma mão por bloco)
- Extrair metadados, ações por rodada e resultado financeiro de cada mão
- Formatar valores numéricos no padrão brasileiro
- Gerar relatório PDF com índice navegável e tabelas de ações/resultados

Convenção: funções com prefixo '_' são auxiliares internas.
Exceção: _aplicar_emoji_naipes é usada diretamente pela página de UI.

Não contém código Streamlit — todas as funções são testáveis isoladamente.
"""

import re

import pandas as pd
from bs4 import BeautifulSoup
from reportlab.platypus import AnchorFlowable, PageBreak, Paragraph, Spacer, Table, TableStyle

from .pdf_builder import (
    adicionar_tabela,
    calcular_larguras_proporcional,
    finalizar_pdf,
    inicializar_pdf,
)
from .pdf_config import (
    ESTILO_CELULA, ESTILO_LEGENDA, ESTILO_PARAGRAFO, ESTILO_TABELA_COMPACTO,
    FONTE_NAIPES, FONTE_NEGRITO, FONTE_NORMAL,
    COR_DESTAQUE, COR_DESTAQUE_ESCURO, COR_TEXTO, COR_DESTAQUE_CLARO, COR_BORDA,
    aplicar_fonte_naipes, styles,
)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────

# Marcador que o backend insere entre mãos consecutivas no arquivo HTML
SEPARADOR = '<P /><hr /><P /><P /><hr /><P />'

# Representa carta oculta na interface Streamlit (emoji de baralho)
CARTA_OCULTA = '🃏'

# Mapeamento de símbolos de naipe para versão emoji (exibição Streamlit/HTML)
# No PDF, os naipes são renderizados com a fonte SegoeUISymbol em vez de emojis
_EMOJI_NAIPES = {'♠': '♠️', '♥': '♥️', '♦': '♦️', '♣': '♣️'}


# ─────────────────────────────────────────────────────────────────────────────
# FORMATAÇÃO
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_br(valor: float, decimais: int = 0, sinal: bool = False) -> str:
    """Formata número no padrão brasileiro: '.' para milhar, ',' para decimal.

    Exemplos:
        _fmt_br(1234.5)           → '1.234'
        _fmt_br(1234.5, 2)        → '1.234,50'
        _fmt_br(-50, sinal=True)  → '-50'
        _fmt_br(50, sinal=True)   → '+50'
    """
    fmt = f'{valor:+,.{decimais}f}' if sinal else f'{valor:,.{decimais}f}'
    # Troca vírgula ↔ ponto via caractere intermediário 'X' para evitar conflito
    return fmt.replace(',', 'X').replace('.', ',').replace('X', '.')


def _aplicar_emoji_naipes(texto: str) -> str:
    """Substitui símbolos de naipe pelos equivalentes emoji para exibição Streamlit."""
    for orig, emoji in _EMOJI_NAIPES.items():
        texto = texto.replace(orig, emoji)
    return texto


def renderizar_cartas(lista_cartas: list, revelar: bool) -> str:
    """Renderiza cartas para exibição na interface Streamlit.

    - Reveladas: símbolo+naipe em emoji (ex: 'A♠️ K♥️')
    - Ocultas: um ícone CARTA_OCULTA por carta (ex: '🃏 🃏')
    """
    if not lista_cartas:
        return ''
    if revelar:
        return _aplicar_emoji_naipes(' '.join(lista_cartas))
    return ' '.join([CARTA_OCULTA] * len(lista_cartas))


def _cartas_para_pdf(lista_cartas: list, revelar: bool) -> str:
    """Versão PDF das cartas: mantém ♠♥♦♣ (SegoeUISymbol suporta esses símbolos).

    Cartas ocultas são representadas como '[?]' — mais legível em fonte tipográfica
    do que um emoji que pode não renderizar corretamente no PDF.
    """
    if not lista_cartas:
        return ''
    if not revelar:
        return ' '.join(['[?]'] * len(lista_cartas))
    return ' '.join(lista_cartas)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DE NOME E ID
# ─────────────────────────────────────────────────────────────────────────────

def _limpar_nome(nome_raw: str, id_jogador: str) -> str:
    """Remove caracteres fora das faixas ASCII, latinas estendidas e cirílicas.

    O backend pode incluir emojis, símbolos ou caracteres de controle no nome.
    Se o nome ficar vazio após a limpeza, usa 'Jogador_<ID>' como fallback.
    """
    nome_limpo = re.sub(r'[^\x00-\x7F\u00C0-\u024F\u0400-\u04FF]', '', nome_raw).strip()
    return nome_limpo if nome_limpo else f'Jogador_{id_jogador}'


def _extrair_nome_id(nome_completo: str) -> tuple:
    """Separa 'Nome Sobrenome(12345)' em (nome_limpo, id_str).

    O backend formata o campo de jogador com o ID numérico entre parênteses
    imediatamente após o nome (sem espaço). Exemplo: 'JogadorABC(99801)'.
    Retorna (nome_original, None) se o padrão não for encontrado.
    """
    match = re.match(r'^(.*)\((\d+)\)$', nome_completo.strip())
    if match:
        nome_raw  = match.group(1).strip()
        id_jogador = match.group(2)
        return _limpar_nome(nome_raw, id_jogador), id_jogador
    return nome_completo.strip(), None


def _formatar_jogador(nome: str, id_jogador: str | None) -> str:
    """Concatena nome e ID no formato 'Nome (ID)' para exibição."""
    if id_jogador:
        return f'{nome} ({id_jogador})'
    return nome


def _nome_base(nome_formatado: str) -> str:
    """Remove o sufixo ' (ID)' adicionado por _formatar_jogador.

    Usado quando precisa do nome puro para exibição sem o ID.
    """
    return re.sub(r' \(\d+\)$', '', nome_formatado).strip()


# ─────────────────────────────────────────────────────────────────────────────
# PARSER — CHIP CHANGE E CARTAS
# ─────────────────────────────────────────────────────────────────────────────

def parse_chip_change(texto: str) -> dict:
    """Extrai resultado líquido, rake e investido da célula 'Chip Change'.

    O backend formata o campo como: (resultado_líquido) [rake] {investido}
    Todos os valores são floats. Retorna zeros se o padrão não casar.

    Exemplo: '(-1500) [30.00] {1500}' → resultado=-1500, rake=30.0, investido=1500
    """
    padrao = r'\((-?[\d.]+)\)\s*\[(-?[\d.]+)\]\s*\{(-?[\d.]+)\}'
    match = re.search(padrao, texto.strip())
    if match:
        return {
            'resultado_liquido': float(match.group(1)),
            'rake':              float(match.group(2)),
            'investido':         float(match.group(3)),
        }
    return {'resultado_liquido': 0.0, 'rake': 0.0, 'investido': 0.0}


def parse_cartas(celula_td) -> list:
    """Extrai lista de strings de carta de uma célula <td> do HTML.

    O backend renderiza cada carta como um <span> folha (sem filhos span),
    com o texto no formato 'A♠' ou 'K♥'. Spans com filhos são contêineres
    estruturais e são ignorados para evitar duplicatas.
    """
    cartas = []
    for span in celula_td.find_all('span'):
        # Ignora spans que são apenas contêineres (possuem spans filhos)
        if not span.find('span'):
            texto = span.get_text(strip=True)
            if texto:
                cartas.append(texto)
    return cartas


# ─────────────────────────────────────────────────────────────────────────────
# PARSER — METADADOS DA MÃO
# ─────────────────────────────────────────────────────────────────────────────

def parse_metadados(container_div) -> dict:
    """Extrai metadados da mão a partir do <div class='container'>.

    O backend renderiza os metadados como pares sequenciais de <div>:
    div[0] = chave, div[1] = valor, div[2] = chave, div[3] = valor, ...

    Retorna dict com chaves padronizadas:
        hand_id, hand_number, game_id, game_type, data, hora, blinds, ante, fee_rate
    """
    divs = container_div.find_all('div', recursive=False)
    dados = {}
    for i in range(0, len(divs) - 1, 2):
        # Normaliza chave para snake_case sem espaços
        chave = divs[i].get_text(strip=True).rstrip(':').strip().lower().replace(' ', '_')
        valor = divs[i + 1].get_text(strip=True)
        if chave:
            dados[chave] = valor

    def _f(chave, default=0.0):
        """Converte valor do dict para float, removendo formatação não numérica."""
        try:
            return float(re.sub(r'[^\d.]', '', dados.get(chave, str(default))))
        except (ValueError, TypeError):
            return default

    return {
        'hand_id':     dados.get('hand_id', ''),
        'hand_number': dados.get('hand_number', ''),
        'game_id':     dados.get('game_id', ''),
        'game_type':   dados.get('game_type', ''),
        'data':        dados.get('date', ''),
        'hora':        dados.get('time', ''),
        'blinds':      _f('blinds'),
        'ante':        _f('ante'),
        'fee_rate':    _f('fee_rate'),
    }


# ─────────────────────────────────────────────────────────────────────────────
# PARSER — HELPERS DE TABELA
# ─────────────────────────────────────────────────────────────────────────────

def _headers_diretos(tabela) -> list:
    """Retorna textos dos <th> que pertencem diretamente a esta tabela.

    Ignora <th> de tabelas aninhadas para evitar confundir cabeçalhos da inner
    table com os da outer table (relevante na seção de resultados de pote).
    """
    headers = []
    for th in tabela.find_all('th'):
        in_nested = any(p.name == 'table' for p in th.parents if p != tabela)
        if not in_nested:
            headers.append(th.get_text(strip=True).lower())
    return headers


def _is_top_level_gridtable(tabela) -> bool:
    """Retorna True se a tabela não estiver aninhada dentro de outra tabela.

    O HTML do backend possui tabelas dentro de tabelas para resultados de pote.
    Só processamos as tabelas de nível raiz neste passo inicial.
    """
    return not any(p.name == 'table' for p in tabela.parents)


# ─────────────────────────────────────────────────────────────────────────────
# PARSER — RODADAS (PREFLOP / FLOP / TURN / RIVER)
# ─────────────────────────────────────────────────────────────────────────────

def parse_tabela_rodada(tabela) -> dict:
    """Extrai ações de uma rodada (preflop/flop/turn/river) de sua <table>.

    Estrutura esperada das colunas da <tbody>:
        0: posição  1: nome(ID)  3: ação  4: valor bet
        5: tempo    6: cartas    7: fichas restantes    10: tipo_op (opcional)

    O <tfoot> contém o pote acumulado ao final da rodada e as cartas comunitárias.
    """
    caption = tabela.find('caption')
    nome_rodada = caption.get_text(strip=True).lower() if caption else ''

    acoes = []
    tbody = tabela.find('tbody')
    rows = tbody.find_all('tr') if tbody else []
    for tr in rows:
        cols = tr.find_all('td')
        if len(cols) < 8:
            continue  # Linha malformada ou subtotal — ignora
        nome_completo = cols[1].get_text(strip=True)
        nome_exib, id_jog = _extrair_nome_id(nome_completo)
        acoes.append({
            'posicao':    cols[0].get_text(strip=True),
            'nome':       _formatar_jogador(nome_exib, id_jog),
            'id':         id_jog,
            'acao':       cols[3].get_text(strip=True),
            'bet':        cols[4].get_text(strip=True),
            'tempo':      cols[5].get_text(strip=True),
            'cartas':     parse_cartas(cols[6]),
            'fichas_rest': cols[7].get_text(strip=True),
            # Col 10 pode não existir em versões mais antigas do backend
            'tipo_op':    cols[10].get_text(strip=True) if len(cols) > 10 else '',
        })

    # ── Rodapé: cartas comunitárias e pote ao final da rodada ───────────────
    cartas_publicas = []
    pote_final = 0.0
    tfoot = tabela.find('tfoot')
    if tfoot:
        texto_rodape = tfoot.get_text(' ', strip=True)
        m_pote = re.search(r'Pot:\s*([\d.,]+)', texto_rodape)
        if m_pote:
            # O pote pode vir formatado com vírgula (ex: "1,234")
            # Pega apenas os dígitos do primeiro número antes da vírgula
            primeiro_num = m_pote.group(1).split(',')[0]
            try:
                pote_final = float(primeiro_num)
            except ValueError:
                pass
        td_rodape = tfoot.find('td')
        if td_rodape:
            cartas_publicas = parse_cartas(td_rodape)

    return {
        'nome':            nome_rodada,
        'acoes':           acoes,
        'cartas_publicas': cartas_publicas,
        'pote_final':      pote_final,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PARSER — RESULTADO (DISTRIBUIÇÃO DE POTE)
# ─────────────────────────────────────────────────────────────────────────────

def parse_inner_pot_table(tabela) -> list:
    """Extrai resultado por jogador da tabela interna de distribuição de pote.

    Estrutura esperada das colunas:
        0: posição   1: nome(ID)   2: chip_change "(res)[rake]{inv}"
        3: spoils (ganho bruto)    4: fee    6: winning_pattern    7: cartas
    """
    jogadores = []
    tbody = tabela.find('tbody')
    rows = tbody.find_all('tr') if tbody else tabela.find_all('tr')
    for tr in rows:
        cols = tr.find_all('td')
        if len(cols) < 9:
            continue
        nome_completo = cols[1].get_text(strip=True)
        nome_exib, id_jog = _extrair_nome_id(nome_completo)
        chip = parse_chip_change(cols[2].get_text(strip=True))
        nome_exib = _formatar_jogador(nome_exib, id_jog)

        # Converte campos numéricos com fallback para 0.0
        try:
            spoils = float(re.sub(r'[^\d.]', '', cols[3].get_text(strip=True)) or '0')
        except ValueError:
            spoils = 0.0
        try:
            fee = float(re.sub(r'[^\d.]', '', cols[4].get_text(strip=True)) or '0')
        except ValueError:
            fee = 0.0

        jogadores.append({
            'posicao':           cols[0].get_text(strip=True),
            'nome':              nome_exib,
            'id':                id_jog,
            'resultado_liquido': chip['resultado_liquido'],
            'rake':              chip['rake'],
            'investido':         chip['investido'],
            'spoils':            spoils,
            'fee':               fee,
            'cartas':            parse_cartas(cols[7]),
            'winning_pattern':   cols[6].get_text(strip=True),
        })
    return jogadores


def parse_pot_outer_table(tabela) -> dict:
    """Extrai dados do pote a partir da outer table de resultado.

    A outer table contém: número do pote, valor total e uma inner table
    com os dados individuais de cada jogador. A inner table é identificada
    pelo cabeçalho 'chip change'.
    """
    # Coleta textos de <td> que não pertencem a tabelas aninhadas
    outer_tds = []
    for td in tabela.find_all('td'):
        if td.find('table'):
            continue  # Este td contém uma inner table — ignora seu texto direto
        in_nested = any(p.name == 'table' for p in td.parents if p != tabela)
        if not in_nested:
            outer_tds.append(td.get_text(strip=True))

    pot_numero = outer_tds[0] if outer_tds else '?'
    pot_valor = 0.0
    if len(outer_tds) >= 2:
        try:
            pot_valor = float(re.sub(r'[^\d.]', '', outer_tds[1]))
        except ValueError:
            pass

    # Localiza a inner table pelo cabeçalho 'chip change'
    inner_table = None
    for nested in tabela.find_all('table'):
        ths = [th.get_text(strip=True).lower() for th in nested.find_all('th')]
        if 'chip change' in ths:
            inner_table = nested
            break

    return {
        'numero':      pot_numero,
        'valor_total': pot_valor,
        'jogadores':   parse_inner_pot_table(inner_table) if inner_table else [],
    }


# ─────────────────────────────────────────────────────────────────────────────
# PARSER — MÃO INDIVIDUAL E ARQUIVO COMPLETO
# ─────────────────────────────────────────────────────────────────────────────

def parse_mao(html_bloco: str) -> dict:
    """Faz o parse completo de um bloco HTML que corresponde a uma única mão.

    Retorna dict com:
        'metadados': hand_id, hand_number, game_id, game_type, data, hora, blinds...
        'rodadas':   lista de rodadas (preflop/flop/turn/river) com ações e cartas
        'resultado': dict com lista de potes e resultado financeiro por jogador
    """
    soup = BeautifulSoup(html_bloco, 'html.parser')

    container = soup.find('div', class_='container')
    metadados = parse_metadados(container) if container else {}

    rodadas = []
    resultado_potes = []

    for tabela in soup.find_all('table', class_='gridtable'):
        # Processa apenas tabelas de nível raiz (ignora aninhadas)
        if not _is_top_level_gridtable(tabela):
            continue
        caption = tabela.find('caption')
        caption_texto = caption.get_text(strip=True).lower() if caption else ''

        if caption_texto in ('preflop', 'flop', 'turn', 'river'):
            rodadas.append(parse_tabela_rodada(tabela))
        elif 'pot number' in _headers_diretos(tabela):
            # Tabela de resultado de pote (pode haver múltiplos potes/side pots)
            resultado_potes.append(parse_pot_outer_table(tabela))

    return {
        'metadados': metadados,
        'rodadas':   rodadas,
        'resultado': {'potes': resultado_potes},
    }


def parse_arquivo_html(conteudo_html: str) -> tuple[list, int]:
    """Divide o arquivo HTML em blocos e faz o parse de cada mão.

    O arquivo exportado pelo backend contém todas as mãos concatenadas,
    separadas pelo marcador SEPARADOR. Blocos sem '.container' são ignorados
    (cabeçalho, rodapé ou blocos vazios do arquivo).

    Returns:
        (lista_de_maos, n_erros): n_erros é o total de blocos que falharam
        no parse e foram descartados. A lista pode ter menos mãos que blocos.
    """
    blocos = conteudo_html.split(SEPARADOR)
    maos = []
    n_erros = 0
    for bloco in blocos:
        if '<div class="container">' not in bloco:
            continue  # Bloco sem mão (cabeçalho, rodapé, vazio)
        try:
            maos.append(parse_mao(bloco))
        except Exception:
            n_erros += 1  # Conta mãos malformadas sem interromper o processamento
    return maos, n_erros


def coletar_jogadores(lista_maos: list) -> dict:
    """Constrói mapa {id_jogador: nome_base} percorrendo todas as mãos.

    Itera tanto pelas ações das rodadas quanto pelos resultados dos potes,
    garantindo que jogadores que foldaram antes de qualquer ação (e só aparecem
    no resultado) também sejam incluídos no mapa.
    """
    jogadores = {}
    for mao in lista_maos:
        for rodada in mao.get('rodadas', []):
            for acao in rodada.get('acoes', []):
                if acao['id']:
                    jogadores[acao['id']] = _nome_base(acao['nome'])
        for pote in mao.get('resultado', {}).get('potes', []):
            for jog in pote.get('jogadores', []):
                if jog['id']:
                    jogadores[jog['id']] = _nome_base(jog['nome'])
    return jogadores


def ids_contas_na_mao(mao: dict) -> set:
    """Retorna o conjunto de IDs de jogadores presentes nas ações desta mão.

    Útil para filtrar mãos por conta selecionada e marcar mãos no índice do PDF.
    Considera apenas jogadores com ID numérico definido (ignora None).
    """
    return {
        a['id']
        for r in mao.get('rodadas', [])
        for a in r.get('acoes', [])
        if a['id']
    }


# ─────────────────────────────────────────────────────────────────────────────
# GERAÇÃO DE PDF
# ─────────────────────────────────────────────────────────────────────────────

def gerar_pdf_hand_history(
    maos: list,
    contas_selecionadas: list,
    modo_cartas: str,
    game_id: str,
) -> bytes:
    """Gera PDF do histórico de mãos seguindo o padrão institucional do projeto.

    Estrutura do PDF:
        1. Parágrafo introdutório com estatísticas gerais (total de mãos,
           mãos com as contas selecionadas)
        2. Índice clicável (6 células por linha) com todas as mãos —
           mãos com contas selecionadas são marcadas com ★
        3. Uma página por mão:
           - Cabeçalho (número, tipo, data/hora, blinds)
           - Resultado líquido das contas selecionadas (+ acumulado)
           - Rodadas com tabela de ações e cartas comunitárias
           - Tabela de resultado final por pote
           - Link "↑ Voltar ao índice"

    Args:
        maos:               Lista de mãos parseadas por parse_arquivo_html.
        contas_selecionadas: IDs das contas "minhas" — revelam cartas e marcam no índice.
        modo_cartas:        'Revelar todos' | 'Revelar minhas contas' | 'Ocultar todos'
        game_id:            ID do game para o título do PDF e nome do arquivo.

    Returns:
        bytes do PDF pronto para download.
    """
    contas_set = set(contas_selecionadas)

    buffer, doc, story = inicializar_pdf(
        '',
        titulo_completo=f'Hand History — Game {game_id}',
    )
    largura_util = doc.width

    # ── Parágrafo introdutório ───────────────────────────────────────────────
    story.append(AnchorFlowable('topo'))
    n_maos    = len(maos)
    n_minhas  = sum(1 for m in maos if contas_set & ids_contas_na_mao(m))

    intro_linhas = [
        f'Este relatório contém {n_maos} mão(s) do Game #{game_id}.',
        'Navegação: o índice abaixo lista todas as mãos — clique em qualquer célula para ir diretamente '
        'à posição correspondente no documento. No final de cada mão há um link "↑ Voltar ao índice".',
    ]
    if contas_set and n_minhas:
        intro_linhas.append(
            f'Mãos marcadas com <font name="{FONTE_NAIPES}">★</font> ({n_minhas} no total) '
            f'contêm pelo menos uma das contas indicadas.'
        )
    for linha in intro_linhas:
        story.append(Paragraph(linha, ESTILO_PARAGRAFO))
    story.append(Spacer(1, 8))

    # ── Índice de mãos ───────────────────────────────────────────────────────
    # 6 células por linha; primeira linha tem o título mesclado ocupando todas as colunas
    _COLS_INDICE = 6
    _ESTILO_INDICE = TableStyle([
        # Cabeçalho mesclado
        ('SPAN',           (0, 0), (-1, 0)),
        ('FONTNAME',       (0, 0), (-1, 0), FONTE_NEGRITO),
        ('FONTSIZE',       (0, 0), (-1, 0), 10),
        ('BACKGROUND',     (0, 0), (-1, 0), COR_DESTAQUE),
        ('TEXTCOLOR',      (0, 0), (-1, 0), COR_TEXTO),
        ('ALIGN',          (0, 0), (-1, 0), 'CENTER'),
        ('LINEBELOW',      (0, 0), (-1, 0), 1.5, COR_DESTAQUE_ESCURO),
        # Corpo (células de link)
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

    # Monta linhas do índice agrupando 6 mãos por linha
    linhas_indice: list = [
        [f'Índice de Mãos — Game #{game_id} ({n_maos} mãos)'] + [''] * (_COLS_INDICE - 1)
    ]
    linha_atual: list = []
    for i, mao in enumerate(maos):
        meta        = mao.get('metadados', {})
        hand_number = meta.get('hand_number', '?')
        tem_conta   = bool(contas_set & ids_contas_na_mao(mao))
        prefixo     = f'<font name="{FONTE_NAIPES}">★</font> ' if tem_conta else ''
        linha_atual.append(Paragraph(
            f'<a href="#mao_{i}">{prefixo}Mão #{hand_number}</a>',
            ESTILO_CELULA,
        ))
        if len(linha_atual) == _COLS_INDICE:
            linhas_indice.append(linha_atual)
            linha_atual = []

    # Preenche células vazias na última linha incompleta
    if linha_atual:
        while len(linha_atual) < _COLS_INDICE:
            linha_atual.append('')
        linhas_indice.append(linha_atual)

    larg_col = largura_util / _COLS_INDICE
    tabela_indice = Table(linhas_indice, colWidths=[larg_col] * _COLS_INDICE)
    tabela_indice.setStyle(_ESTILO_INDICE)
    story.append(tabela_indice)
    story.append(Spacer(1, 12))
    story.append(PageBreak())

    # ── Conteúdo página por página ───────────────────────────────────────────
    # cumulativo_pdf rastreia o resultado líquido acumulado por ID de conta
    # ao longo de todas as mãos do relatório
    cumulativo_pdf: dict[str, float] = {}

    for i, mao in enumerate(maos):
        if i > 0:
            story.append(PageBreak())

        # Âncora para o link do índice "#mao_<i>"
        story.append(AnchorFlowable(f'mao_{i}'))

        meta        = mao.get('metadados', {})
        rodadas     = mao.get('rodadas', [])
        potes       = mao.get('resultado', {}).get('potes', [])
        hand_number = meta.get('hand_number', '?')
        hand_id     = meta.get('hand_id', '?')
        game_type   = meta.get('game_type', '')
        data_hora   = f"{meta.get('data', '')} {meta.get('hora', '')}".strip()
        blinds      = meta.get('blinds', 0.0)

        # Título da mão
        story.append(Paragraph(
            f'Mão #{hand_number} — {game_type} — {data_hora} — Blinds: {_fmt_br(blinds)}',
            styles['Heading2'],
        ))
        story.append(Paragraph(f'Hand ID: {hand_id}', ESTILO_LEGENDA))
        story.append(Spacer(1, 6))

        # ── Resultado das contas selecionadas nesta mão ──────────────────────
        # Soma resultado_liquido por ID entre todos os potes (para side pots)
        resultado_por_conta: dict = {}
        for pote in potes:
            for jog in pote.get('jogadores', []):
                if jog['id'] in contas_set:
                    resultado_por_conta[jog['id']] = (
                        resultado_por_conta.get(jog['id'], 0.0) + jog['resultado_liquido']
                    )

        if resultado_por_conta:
            # Atualiza acumulado total
            for iid, res in resultado_por_conta.items():
                cumulativo_pdf[iid] = cumulativo_pdf.get(iid, 0.0) + res

            # Exibe uma linha por conta: resultado desta mão + acumulado entre parênteses
            # Itera pelos potes para recuperar o nome completo sem duplicatas (set 'seen')
            seen: set = set()
            for pote in potes:
                for jog in pote.get('jogadores', []):
                    iid = jog['id']
                    if iid in resultado_por_conta and iid not in seen:
                        seen.add(iid)
                        res = resultado_por_conta[iid]
                        cum = cumulativo_pdf[iid]
                        texto = (
                            f"{_nome_base(jog['nome'])}: {_fmt_br(res, sinal=True)}"
                            f"  ({_fmt_br(cum, sinal=True)})"
                        )
                        story.append(Paragraph(texto, ESTILO_PARAGRAFO))

        story.append(Spacer(1, 4))

        # ── Rodadas (preflop, flop, turn, river) ────────────────────────────
        for rodada in rodadas:
            story.append(Paragraph(rodada['nome'].upper(), styles['Heading3']))

            if rodada['cartas_publicas']:
                # Formata naipes dos cards comunitários com a fonte SegoeUISymbol
                texto_comuns = 'Cartas comunitárias: ' + '  '.join(rodada['cartas_publicas'])
                story.append(Paragraph(aplicar_fonte_naipes(texto_comuns), ESTILO_PARAGRAFO))

            cab_rodada = ['Posição', 'Jogador', 'Ação', 'Valor', 'Tempo (s)', 'Operação', 'Cartas', 'Fichas Rest.']
            linhas_rodada = [cab_rodada]
            for acao in rodada['acoes']:
                revelar = (
                    modo_cartas == 'Revelar todos'
                    or (modo_cartas == 'Revelar minhas contas' and acao['id'] in contas_set)
                )
                linhas_rodada.append([
                    acao['posicao'],
                    acao['nome'],
                    acao['acao'],
                    acao['bet'],
                    acao['tempo'],
                    acao['tipo_op'],
                    _cartas_para_pdf(acao['cartas'], revelar),
                    acao['fichas_rest'],
                ])

            if len(linhas_rodada) > 1:
                df_r   = pd.DataFrame(linhas_rodada[1:], columns=cab_rodada)
                larg_r = calcular_larguras_proporcional(df_r, cab_rodada, cab_rodada, largura_util)
                story.append(Paragraph('Ações desta rodada.', ESTILO_LEGENDA))
                adicionar_tabela(story, linhas_rodada, larg_r, estilo=ESTILO_TABELA_COMPACTO)

            if rodada['pote_final']:
                story.append(Paragraph(
                    f'Pote ao final da rodada: {_fmt_br(rodada["pote_final"])}',
                    ESTILO_LEGENDA,
                ))

        # ── Resultado final (distribuição dos potes) ─────────────────────────
        story.append(Paragraph('RESULTADO', styles['Heading3']))

        for pote in potes:
            if len(potes) > 1:
                # Mostra identificação do pote quando há side pots
                story.append(Paragraph(
                    f'Pote {pote["numero"]} — Total: {_fmt_br(pote["valor_total"])}',
                    ESTILO_LEGENDA,
                ))

            cab_res = ['Posição', 'Jogador', 'Resultado', 'Rake', 'Investido', 'Ganho Bruto', 'Cartas', 'Combinação']
            linhas_res = [cab_res]
            for jog in pote.get('jogadores', []):
                revelar = (
                    modo_cartas == 'Revelar todos'
                    or (modo_cartas == 'Revelar minhas contas' and jog['id'] in contas_set)
                )
                linhas_res.append([
                    jog['posicao'],
                    jog['nome'],
                    _fmt_br(jog['resultado_liquido'], sinal=True),
                    _fmt_br(jog['rake'], decimais=2),
                    _fmt_br(jog['investido']),
                    _fmt_br(jog['spoils']),
                    _cartas_para_pdf(jog['cartas'], revelar),
                    jog['winning_pattern'],
                ])

            if len(linhas_res) > 1:
                df_res   = pd.DataFrame(linhas_res[1:], columns=cab_res)
                larg_res = calcular_larguras_proporcional(df_res, cab_res, cab_res, largura_util)
                story.append(Paragraph('Resultado de cada jogador na mão.', ESTILO_LEGENDA))
                adicionar_tabela(story, linhas_res, larg_res, estilo=ESTILO_TABELA_COMPACTO)

        # Link de volta ao índice (âncora 'topo' definida no início do PDF)
        story.append(Paragraph('<a href="#topo">↑ Voltar ao índice</a>', ESTILO_LEGENDA))

    return finalizar_pdf(buffer, doc, story).read()
