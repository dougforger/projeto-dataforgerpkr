"""Página de análise de Chip Dumping.

Fluxo:
1. Upload dos arquivos "Player chips transaction record" de cada jogador
2. Filtro pelo Game ID investigado
3. Cálculo automático: chip change, rake, mãos jogadas por jogador
4. Visualização hand-a-hand e tabela resumo
5. (futuro) Geração do laudo em PDF
"""

import re

import pandas as pd
import streamlit as st

from utils.arquivo_utils import corrigir_xlsx_memoria

st.set_page_config(
    page_title='Chip Dumping',
    page_icon='🎰',
    layout='wide',
    initial_sidebar_state='collapsed',
)

st.title('🎰 Chip Dumping')
st.markdown('Análise de transferência intencional de fichas entre contas.')
st.markdown('---')

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extrair_game_id(texto: str) -> str | None:
    """Extrai o Game ID do campo Association ('Game ID: XXXXX Hand ID: YYYYY')."""
    if pd.isna(texto):
        return None
    m = re.search(r'Game ID[:\s]+(\d+)', str(texto), re.IGNORECASE)
    return m.group(1) if m else None


def _extrair_hand_id(texto: str) -> str | None:
    """Extrai o Hand ID do campo Association."""
    if pd.isna(texto):
        return None
    m = re.search(r'Hand ID[:\s]+(\d+)', str(texto), re.IGNORECASE)
    return m.group(1) if m else None


def _link_hand(hand_id: str) -> str:
    """Monta o link de replay da mão no formato PT."""
    # O refID exportado está no formato XXXXXXXXXXXX002en → substituir por 002pt
    base = str(hand_id).replace('002en', '002pt')
    return f'https://r.supremapoker.net/?t={base}'


@st.cache_data
def _carregar_planilha(arquivo) -> pd.DataFrame:
    """Lê e normaliza um arquivo de transação do backend."""
    buf = corrigir_xlsx_memoria(arquivo)
    df  = pd.read_excel(buf, engine='openpyxl')

    # Normaliza nomes de colunas: remove espaços extras
    df.columns = [c.strip() for c in df.columns]

    # Colunas numéricas obrigatórias
    for col in ['chip change', 'Total Fee change', 'Game Fee change']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Extrai Game ID e Hand ID do campo Association
    if 'Association' in df.columns:
        df['_game_id'] = df['Association'].apply(_extrair_game_id)
        df['_hand_id'] = df['Association'].apply(_extrair_hand_id)

    # Timestamp
    if 'Record time' in df.columns:
        df['Record time'] = pd.to_datetime(df['Record time'], errors='coerce')

    return df


def _resumo_jogador(df: pd.DataFrame) -> dict:
    return {
        'jogador_id':   df['Player ID'].iloc[0]    if 'Player ID'   in df.columns else '—',
        'jogador_nome': df['Player Name'].iloc[0]  if 'Player Name' in df.columns else '—',
        'clube_nome':   df['Club Name'].iloc[0]    if 'Club Name'   in df.columns else '—',
        'maos':         len(df),
        'chip_change':  df['chip change'].sum(),
        'rake':         df['Total Fee change'].sum(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Upload dos arquivos
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('### 📂 Upload das planilhas')
st.caption(
    'Faça upload dos arquivos **Player chips transaction record** exportados do backend, '
    'um por jogador investigado. Mínimo 2, sem limite máximo.'
)

arquivos = st.file_uploader(
    'Selecione os arquivos (.xlsx)',
    type=['xlsx', 'xls'],
    accept_multiple_files=True,
    key='uploader_dumping',
)

if not arquivos:
    st.info('Faça upload de ao menos dois arquivos para iniciar a análise.')
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Carrega e valida os arquivos
# ─────────────────────────────────────────────────────────────────────────────

dfs_brutos: list[pd.DataFrame] = []
for arq in arquivos:
    try:
        dfs_brutos.append(_carregar_planilha(arq))
    except Exception as e:
        st.error(f'Erro ao ler **{arq.name}**: {e}')
        st.stop()

# Valida que cada arquivo tem um jogador diferente
ids_jogadores = []
for df in dfs_brutos:
    if 'Player ID' not in df.columns:
        st.error('Coluna "Player ID" não encontrada. Verifique se o arquivo correto foi enviado.')
        st.stop()
    ids_jogadores.append(df['Player ID'].iloc[0])

if len(set(ids_jogadores)) < len(ids_jogadores):
    st.warning('⚠️ Dois ou mais arquivos parecem ser do mesmo jogador.')

# ─────────────────────────────────────────────────────────────────────────────
# Seleção do Game ID investigado
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('---')
st.markdown('### 🎮 Filtro por Game ID')

# Coleta todos os Game IDs presentes nos arquivos
todos_game_ids: set[str] = set()
for df in dfs_brutos:
    if '_game_id' in df.columns:
        todos_game_ids.update(df['_game_id'].dropna().unique())

if not todos_game_ids:
    st.error('Nenhum Game ID encontrado nos arquivos. Verifique o campo "Association".')
    st.stop()

game_ids_ordenados = sorted(todos_game_ids, key=lambda x: int(x) if x.isdigit() else 0)

col_sel, col_proto = st.columns([2, 2])
with col_sel:
    game_id_sel = st.selectbox('Game ID investigado', game_ids_ordenados)
with col_proto:
    protocolo_input = st.text_input('Número do protocolo', placeholder='1329374652')

# ─────────────────────────────────────────────────────────────────────────────
# Filtra cada df pelo Game ID selecionado
# ─────────────────────────────────────────────────────────────────────────────

dfs_filtrados = [df[df['_game_id'] == game_id_sel].copy() for df in dfs_brutos]
dfs_filtrados = [df for df in dfs_filtrados if not df.empty]

if not dfs_filtrados:
    st.warning(f'Nenhum registro encontrado para o Game ID **{game_id_sel}** nos arquivos enviados.')
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# Layout principal — Análise
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('---')
st.markdown(f'### 📊 Análise — Game ID {game_id_sel}')

resumos = [_resumo_jogador(df) for df in dfs_filtrados]

# ── Métricas por jogador ──────────────────────────────────────────────────────

colunas_metricas = st.columns(len(resumos))
for col, r in zip(colunas_metricas, resumos):
    delta_color = 'normal' if r['chip_change'] >= 0 else 'inverse'
    col.metric(
        label=f"**{r['jogador_nome']}** ({r['jogador_id']})",
        value=f"{r['chip_change']:+,.2f} chips",
        delta=f"{r['maos']} mãos · rake {r['rake']:,.2f}",
        delta_color='off',
    )
    col.caption(r['clube_nome'])

# ── Tabela resumo ─────────────────────────────────────────────────────────────

st.markdown('#### Resumo')

df_resumo = pd.DataFrame(resumos).rename(columns={
    'jogador_id':   'ID',
    'jogador_nome': 'Jogador',
    'clube_nome':   'Clube',
    'maos':         'Mãos',
    'chip_change':  'Chip Change',
    'rake':         'Rake',
})
df_resumo = df_resumo[['ID', 'Jogador', 'Clube', 'Mãos', 'Chip Change', 'Rake']]

# Totaliza
total_chips = df_resumo['Chip Change'].sum()
total_rake  = df_resumo['Rake'].sum()
total_maos  = df_resumo['Mãos'].max()  # mãos jogadas em comum (máx entre jogadores)

t1, t2, t3 = st.columns(3)
t1.metric('Total de mãos', f'{total_maos:,}')
t2.metric('Chip change líquido', f'{total_chips:+,.2f}', help='Deve ser próximo de zero (chips transferidos + rake)')
t3.metric('Rake total arrecadado', f'{total_rake:,.2f}')

st.dataframe(
    df_resumo.style.format({'Chip Change': '{:+,.2f}', 'Rake': '{:,.2f}'}),
    use_container_width=True,
    hide_index=True,
)

# ── Histórico hand-a-hand ────────────────────────────────────────────────────

st.markdown('#### Histórico hand-a-hand')

df_combined = pd.concat(dfs_filtrados, ignore_index=True)

if 'Record time' in df_combined.columns:
    df_combined = df_combined.sort_values('Record time')

colunas_exibir = [c for c in [
    'Record time', 'Player Name', 'Player ID',
    '_hand_id', '_game_id',
    'chip change', 'Total Fee change',
    'Chips(Before)', 'Chip(After)',
] if c in df_combined.columns]

df_exibir = df_combined[colunas_exibir].rename(columns={
    'Record time':       'Hora',
    'Player Name':       'Jogador',
    'Player ID':         'ID',
    '_hand_id':          'Hand ID',
    '_game_id':          'Game ID',
    'chip change':       'Chip Change',
    'Total Fee change':  'Rake',
    'Chips(Before)':     'Stack Antes',
    'Chip(After)':       'Stack Depois',
})

st.dataframe(
    df_exibir.style.format({
        'Chip Change': '{:+,.2f}',
        'Rake':        '{:,.2f}',
        'Stack Antes': '{:,.2f}',
        'Stack Depois':'{:,.2f}',
    }),
    use_container_width=True,
    hide_index=True,
)

# ── Links de evidência ────────────────────────────────────────────────────────

if 'refID' in df_combined.columns:
    st.markdown('#### 🔗 Links de evidência')
    st.caption('Hand IDs extraídos dos registros. Clique para abrir o replay.')

    ref_ids = df_combined['refID'].dropna().unique()
    links   = [_link_hand(r) for r in ref_ids[:20]]  # limita a 20 para não poluir

    col_links = st.columns(min(4, len(links)))
    for i, (col, link) in enumerate(zip(col_links * ((len(links) // 4) + 1), links)):
        col.markdown(f'[Hand {i+1}]({link})')
