"""
Página de visualização de Hand History.

Permite importar o arquivo HTML de hand history exportado pelo backend da Suprema,
visualizar cada mão com filtros por conta e modo de exibição de cartas, e exportar
um relatório PDF com índice navegável.

Todo o parsing e geração de PDF estão em utils/hand_history_parser.py.
Esta página contém exclusivamente a camada de interface Streamlit.
"""

import pandas as pd
import streamlit as st

from utils.hand_history_parser import (
    _aplicar_emoji_naipes,
    _fmt_br,
    _formatar_jogador,
    coletar_jogadores,
    gerar_pdf_hand_history,
    ids_contas_na_mao,
    parse_arquivo_html,
    renderizar_cartas,
)

st.set_page_config(
    page_title='Hand History Viewer',
    page_icon='🃏',
    layout='wide',
)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
# Streamlit re-executa o script inteiro a cada interação do usuário.
# O session_state é o único mecanismo para persistir dados entre reruns.
for chave, padrao in [
    ('maos_parseadas',         None),   # lista de mãos parseadas
    ('jogadores_disponiveis',  {}),     # {id: nome_base} de todos os jogadores
    ('pdf_hh_bytes',           None),   # bytes do último PDF gerado
    ('pdf_hh_nome',            ''),     # nome sugerido para o arquivo PDF
]:
    if chave not in st.session_state:
        st.session_state[chave] = padrao

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — Upload e Filtros
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header('Importar Hand History')
    arquivo = st.file_uploader('Arquivo HTML', type=['html'])

    if arquivo:
        conteudo = arquivo.read().decode('utf-8', errors='replace')
        maos, n_erros = parse_arquivo_html(conteudo)
        st.session_state.maos_parseadas       = maos
        st.session_state.jogadores_disponiveis = coletar_jogadores(maos)
        st.session_state.pdf_hh_bytes         = None  # invalida PDF anterior ao trocar arquivo

        msg = f'{len(maos)} mão(s) encontrada(s).'
        if n_erros:
            msg += f' ({n_erros} bloco(s) ignorado(s) por erro de parse.)'
        st.success(msg)

    # Controles de filtro — só aparecem quando há dados carregados
    contas_selecionadas = []
    modo_cartas         = 'Revelar minhas contas'
    apenas_minhas       = False

    if st.session_state.maos_parseadas:
        jogadores     = st.session_state.jogadores_disponiveis
        ids_ordenados = sorted(jogadores, key=lambda x: jogadores[x].lower())

        st.divider()
        st.subheader('Minhas Contas')
        contas_selecionadas = st.multiselect(
            'Selecionar contas para revelar cartas:',
            options=ids_ordenados,
            format_func=lambda x: f"{jogadores[x]} (ID: {x})",
        )

        st.divider()
        st.subheader('Filtros')
        modo_cartas = st.radio(
            'Exibição de cartas:',
            ['Revelar minhas contas', 'Revelar todos', 'Ocultar todos'],
        )
        apenas_minhas = st.checkbox('Apenas mãos com minhas contas')

# ─────────────────────────────────────────────────────────────────────────────
# ÁREA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
st.title('🃏 Poker Hand History Viewer')

if not st.session_state.maos_parseadas:
    st.info('Faça o upload de um arquivo HTML de hand history na barra lateral.')
    st.stop()

maos: list = st.session_state.maos_parseadas

# ── Filtro de "apenas minhas mãos" ──────────────────────────────────────────
if apenas_minhas and contas_selecionadas:
    ids_set        = set(contas_selecionadas)
    maos_filtradas = [m for m in maos if ids_set & ids_contas_na_mao(m)]
else:
    maos_filtradas = maos

# ── Exportação PDF (sidebar — posicionado após calcular maos_filtradas) ──────
with st.sidebar:
    if maos_filtradas:
        st.divider()
        st.subheader('Exportar')

        if st.button('📄 Gerar PDF das mãos exibidas', use_container_width=True):
            game_id = maos_filtradas[0]['metadados'].get('game_id', 'HH')
            with st.spinner('Gerando PDF...'):
                st.session_state.pdf_hh_bytes = gerar_pdf_hand_history(
                    maos_filtradas,
                    contas_selecionadas,
                    modo_cartas,
                    game_id,
                )
                st.session_state.pdf_hh_nome = f'hand-history-{game_id}.pdf'

        if st.session_state.pdf_hh_bytes:
            st.download_button(
                label='📥 Baixar PDF',
                data=st.session_state.pdf_hh_bytes,
                file_name=st.session_state.pdf_hh_nome,
                mime='application/pdf',
                use_container_width=True,
                type='primary',
            )

# ── Guard: nenhuma mão após filtro ──────────────────────────────────────────
if not maos_filtradas:
    st.warning('Nenhuma mão corresponde aos filtros aplicados.')
    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# FUNÇÃO AUXILIAR DE ESTILO
# ─────────────────────────────────────────────────────────────────────────────

def _estilizar_resultado(row):
    """Aplica fundo verde/vermelho na linha conforme o resultado do jogador na mão."""
    resultado = row['Resultado']
    if resultado > 0:
        cor = 'background-color: #1a4731; color: #4ade80'
    elif resultado < 0:
        cor = 'background-color: #3b1212; color: #f87171'
    else:
        cor = ''
    return [cor] * len(row)


# ─────────────────────────────────────────────────────────────────────────────
# EXIBIÇÃO DAS MÃOS
# ─────────────────────────────────────────────────────────────────────────────

# cumulativo_st rastreia o resultado líquido acumulado por ID ao longo
# da sessão de visualização (reiniciado a cada rerun completo)
cumulativo_st: dict[str, float] = {}

for mao in maos_filtradas:
    meta    = mao.get('metadados', {})
    rodadas = mao.get('rodadas', [])
    potes   = mao.get('resultado', {}).get('potes', [])

    hand_number = meta.get('hand_number', '?')
    hand_id     = meta.get('hand_id', '?')
    game_type   = meta.get('game_type', '')
    data_hora   = f"{meta.get('data', '')} {meta.get('hora', '')}".strip()
    blinds      = meta.get('blinds', 0.0)

    # IDs das contas selecionadas presentes nesta mão específica
    minhas_contas_na_mao = ids_contas_na_mao(mao) & set(contas_selecionadas)

    # Marca o expander com ★ se a mão contiver alguma conta selecionada
    label_expander = (
        f"{'★ ' if minhas_contas_na_mao else ''}"
        f"Mão #{hand_number}  |  Hand ID: {hand_id}  |  {game_type}  |  "
        f"{data_hora}  |  Blinds: {_fmt_br(blinds)}"
    )

    with st.expander(label_expander, expanded=False):

        st.markdown(
            f"### ═══ Mão #{hand_number}  |  Hand ID: {hand_id}  |  "
            f"{game_type}  |  {data_hora}  |  Blinds: {_fmt_br(blinds)} ═══"
        )

        # ── Métricas gerais da mão ───────────────────────────────────────────
        pote_total    = max((r.get('pote_final', 0.0) for r in rodadas), default=0.0)
        rake_total    = sum(j.get('rake', 0.0) for p in potes for j in p.get('jogadores', []))
        num_jogadores = len(ids_contas_na_mao(mao))

        col1, col2, col3, col4 = st.columns(4)
        col1.metric('Pote Total',  _fmt_br(pote_total))
        col2.metric('Rake Total',  _fmt_br(rake_total, decimais=2))
        col3.metric('Jogadores',   num_jogadores)
        col4.metric('Rodadas',     len(rodadas))

        # ── Resultado das contas selecionadas ────────────────────────────────
        if minhas_contas_na_mao:
            resultado_por_conta: dict = {}
            for pote in potes:
                for jog in pote.get('jogadores', []):
                    if jog['id'] in minhas_contas_na_mao:
                        resultado_por_conta[jog['id']] = (
                            resultado_por_conta.get(jog['id'], 0.0) + jog['resultado_liquido']
                        )

            if resultado_por_conta:
                # Atualiza acumulado e exibe uma métrica por conta selecionada
                for iid, res in resultado_por_conta.items():
                    cumulativo_st[iid] = cumulativo_st.get(iid, 0.0) + res

                delta_cols = st.columns(len(resultado_por_conta))
                for idx, (iid, resultado) in enumerate(resultado_por_conta.items()):
                    nome = _formatar_jogador(
                        st.session_state.jogadores_disponiveis.get(iid, iid), iid
                    )
                    cum = cumulativo_st[iid]
                    delta_cols[idx].metric(nome, _fmt_br(resultado, sinal=True))
                    delta_cols[idx].caption(f'Acumulado: {_fmt_br(cum, sinal=True)}')

        st.divider()

        # ── Rodadas (preflop, flop, turn, river) ────────────────────────────
        for rodada in rodadas:
            st.markdown(f'#### {rodada["nome"].upper()}')

            if rodada['cartas_publicas']:
                st.markdown('**Cartas comunitárias:** ' + '  '.join(
                    _aplicar_emoji_naipes(c) for c in rodada['cartas_publicas']
                ))

            linhas = []
            for acao in rodada['acoes']:
                revelar = (
                    modo_cartas == 'Revelar todos'
                    or (modo_cartas == 'Revelar minhas contas' and acao['id'] in contas_selecionadas)
                )
                linhas.append({
                    'Posição':     acao['posicao'],
                    'Jogador':     acao['nome'],
                    'Ação':        acao['acao'],
                    'Valor':       acao['bet'],
                    'Tempo (s)':   acao['tempo'],
                    'Operação':    acao['tipo_op'],
                    'Cartas':      renderizar_cartas(acao['cartas'], revelar),
                    'Fichas Rest.': acao['fichas_rest'],
                })
            if linhas:
                st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)
            if rodada['pote_final']:
                st.caption(f"Pote: {_fmt_br(rodada['pote_final'])}")

        # ── Resultado final ──────────────────────────────────────────────────
        st.divider()
        st.markdown('#### RESULTADO')

        for pote in potes:
            if len(potes) > 1:
                # Identifica o pote quando há side pots
                st.markdown(f"**Pote {pote['numero']}** — Total: {_fmt_br(pote['valor_total'])}")

            linhas_res = []
            for jog in pote.get('jogadores', []):
                revelar = (
                    modo_cartas == 'Revelar todos'
                    or (modo_cartas == 'Revelar minhas contas' and jog['id'] in contas_selecionadas)
                )
                linhas_res.append({
                    'Posição':    jog['posicao'],
                    'Jogador':    jog['nome'],
                    'Resultado':  jog['resultado_liquido'],
                    'Rake':       jog['rake'],
                    'Investido':  jog['investido'],
                    'Ganho Bruto': jog['spoils'],
                    'Cartas':     renderizar_cartas(jog['cartas'], revelar),
                    'Combinação': jog['winning_pattern'],
                })

            if linhas_res:
                df_res = pd.DataFrame(linhas_res)
                st.dataframe(
                    df_res.style.apply(_estilizar_resultado, axis=1).format({
                        'Resultado':   lambda x: _fmt_br(x, sinal=True),
                        'Rake':        lambda x: _fmt_br(x, decimais=2),
                        'Investido':   lambda x: _fmt_br(x),
                        'Ganho Bruto': lambda x: _fmt_br(x),
                    }),
                    use_container_width=True,
                    hide_index=True,
                )
