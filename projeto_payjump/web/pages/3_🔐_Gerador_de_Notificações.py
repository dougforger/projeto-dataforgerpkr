import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date
from src.modelos_notificacao import CABECALHOS, montar_cabecalho

# -----------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# -----------------------------------------------------

st.set_page_config(
    page_title='Gerador de Notificações Security PKR',
    page_icon='🔒',
    layout='wide'
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'

# -----------------------------------------------------
# CARREGAMENTO DOS DADOS
# -----------------------------------------------------

@st.cache_data
def carregar_dados() -> pd.DataFrame:
    clubes = pd.read_csv(DATA_DIR / 'clubes.csv')
    ligas = pd.read_csv(DATA_DIR / 'ligas.csv')
    
    clubes['liga_id'] = clubes['liga_id'].astype(int)
    ligas['liga_id'] = ligas['liga_id'].astype(int)

    clubes = clubes.merge(ligas[['liga_id', 'idioma']], on='liga_id', how='left')
    clubes = clubes.set_index('clube_id')
    return clubes

lista_clubes = carregar_dados()
# st.dataframe(clubes.head())

# -----------------------------------------------------
# HEADER DA PÁGINA
# -----------------------------------------------------

st.markdown('## 🔐 Notificações Security PKR')
st.markdown('---')

# -----------------------------------------------------
# BLOCO 1 — PROTOCOLO E CLUBE
# Sempre visível. Ao encontrar o clube, salva no session_state.
# -----------------------------------------------------

col1, col2 = st.columns(2)
with col1:
    protocolo_input = st.text_input(label='Entre com o número do protocolo.', placeholder='1297462992')
with col2:
    clube_input = st.text_input(label='Entre com o ID do clube.', placeholder='123456')

if protocolo_input and clube_input:
    try:
        protocolo = int(protocolo_input)
        id_clube = int(clube_input)
        
        if id_clube not in lista_clubes.index:
            st.error('❌ Clube não encontrado! Verifique o ID.')
            st.stop()

        st.session_state['clube'] = lista_clubes.loc[id_clube]
        st.session_state['protocolo'] = protocolo

    except ValueError:
        st.error('❌ Protocolo e ID devem ser números!')
        st.stop()

# Interrompe a execução se o clube ainda não foi identificado
if 'clube' not in st.session_state:
    st.info('Preencha o protocolo e o ID do clube para continuar.')
    st.stop()

clube = st.session_state['clube']
protocolo = st.session_state['protocolo']
idioma = clube['idioma']
data_hoje = date.today().strftime('%d/%m/%Y')

# -----------------------------------------------------
# CRIAÇÃO DO CABEÇALHO
# -----------------------------------------------------

col3, col4 = st.columns(2)
with col3:
    st.text(f'Clube: {clube['clube_nome']} ({clube.name})')
    st.text(f'Liga: {clube['liga_nome']} ({clube['liga_id']})')
with col4:
    st.text(f'Data: {data_hoje}')
    st.text(f'Idioma: {idioma}')

cabecalho = montar_cabecalho(
    idioma=idioma,
    protocolo=protocolo,
    nome_clube=clube['clube_nome'],
    id_clube=clube.name,
    nome_liga=clube['liga_nome'],
    id_liga=clube['liga_id'],
    data=data_hoje
)

with st.expander('Previsualização do cabeçalho'):
    st.code(cabecalho, language='text')