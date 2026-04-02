import streamlit as st
import pandas as pd
from datetime import date
from utils.clubes_db import carregar_clubes
from utils.ligas_db import carregar_ligas
from src.modelos_notificacao import (
    CABECALHOS, MODELOS,
    montar_cabecalho, montar_notificacao,
)

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÃO DA PÁGINA
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title='Gerador de Notificações Security PKR',
    page_icon='🔒',
    layout='wide',
)

# ──────────────────────────────────────────────────────────────────────────────
# CARREGAMENTO DOS DADOS
# ──────────────────────────────────────────────────────────────────────────────

@st.cache_data
def carregar_dados() -> pd.DataFrame:
    clubes = carregar_clubes()
    ligas  = carregar_ligas()

    clubes['liga_id'] = clubes['liga_id'].astype(int)
    ligas['liga_id']  = ligas['liga_id'].astype(int)

    clubes = clubes.merge(ligas[['liga_id', 'idioma']], on='liga_id', how='left')
    clubes = clubes.set_index('clube_id')
    return clubes

lista_clubes = carregar_dados()

# ──────────────────────────────────────────────────────────────────────────────
# HEADER DA PÁGINA
# ──────────────────────────────────────────────────────────────────────────────

st.markdown('## 🔐 Notificações Security PKR')
st.markdown('---')

# ──────────────────────────────────────────────────────────────────────────────
# BLOCO 1 — PROTOCOLO E CLUBE
# ──────────────────────────────────────────────────────────────────────────────

col1, col2 = st.columns(2)
with col1:
    protocolo_input = st.text_input(
        label='Número do protocolo',
        placeholder='1297462992',
    )
with col2:
    clube_input = st.text_input(
        label='ID do clube',
        placeholder='123456',
    )

if protocolo_input and clube_input:
    try:
        protocolo = int(protocolo_input)
        id_clube  = int(clube_input)

        if id_clube not in lista_clubes.index:
            st.error('❌ Clube não encontrado. Verifique o ID.')
            st.stop()

        st.session_state['clube']     = lista_clubes.loc[id_clube]
        st.session_state['protocolo'] = protocolo

    except ValueError:
        st.error('❌ Protocolo e ID devem ser números inteiros.')
        st.stop()

if 'clube' not in st.session_state:
    st.info('Preencha o protocolo e o ID do clube para continuar.')
    st.stop()

clube     = st.session_state['clube']
protocolo = st.session_state['protocolo']
idioma    = clube['idioma']
data_hoje = date.today().strftime('%d/%m/%Y')

# Info do clube (linha compacta abaixo dos inputs)
ci1, ci2, ci3, ci4 = st.columns(4)
ci1.metric('Clube',    f"{clube['clube_nome']} ({clube.name})")
ci2.metric('Liga',     f"{clube['liga_nome']} ({clube['liga_id']})")
ci3.metric('Idioma',   idioma.capitalize())
ci4.metric('Data',     data_hoje)

st.markdown('---')

# ──────────────────────────────────────────────────────────────────────────────
# SELETOR DE MODELO
# ──────────────────────────────────────────────────────────────────────────────

categorias = [m['categoria'] for m in MODELOS]
categoria_sel = st.selectbox('Tipo de notificação', categorias, label_visibility='visible')

modelo = next(m for m in MODELOS if m['categoria'] == categoria_sel)

# dados_base disponíveis para interpolação no corpo (ex: {nome_clube} em Aliciamento)
dados_base = {
    'protocolo': protocolo,
    'nome_clube': clube['clube_nome'],
    'id_clube':   clube.name,
    'nome_liga':  clube['liga_nome'],
    'id_liga':    clube['liga_id'],
    'data':       data_hoje,
}

# Monta o cabeçalho com o tipo correto para este modelo
tipo_cabecalho = modelo.get('tipo_cabecalho', 'notificacao')
cabecalho = '' if modelo.get('sem_cabecalho', False) else montar_cabecalho(
    idioma=idioma,
    protocolo=protocolo,
    nome_clube=clube['clube_nome'],
    id_clube=clube.name,
    nome_liga=clube['liga_nome'],
    id_liga=clube['liga_id'],
    data=data_hoje,
    tipo=tipo_cabecalho,
)

st.markdown('---')

# ──────────────────────────────────────────────────────────────────────────────
# LAYOUT PRINCIPAL — FORMULÁRIO (esq.) | PRÉVIA (dir.)
# ──────────────────────────────────────────────────────────────────────────────

col_form, col_preview = st.columns(2, gap='large')

# ── COLUNA ESQUERDA: campos dinâmicos ────────────────────────────────────────

with col_form:
    st.markdown('#### Campos')

    campos_preenchidos = {}

    if not modelo['campos']:
        st.info('Esta notificação não requer campos adicionais.')
    else:
        for campo in modelo['campos']:
            # Namespace no key para resetar ao trocar de modelo
            widget_key = f'{categoria_sel}__{campo["key"]}'
            label      = campo['label']
            tipo       = campo['tipo']

            if tipo == 'textarea':
                valor = st.text_area(label, key=widget_key, height=120)
            elif tipo == 'number':
                valor = st.number_input(label, min_value=0, value=0, step=1, key=widget_key)
            else:
                valor = st.text_input(label, key=widget_key)

            campos_preenchidos[campo['key']] = valor

# ── COLUNA DIREITA: prévia em tempo real ────────────────────────────────────

with col_preview:
    st.markdown('#### Prévia')

    try:
        notificacao = montar_notificacao(
            idioma=idioma,
            cabecalho=cabecalho,
            modelo=modelo,
            campos_preenchidos=campos_preenchidos,
            dados_base=dados_base,
        )
    except KeyError as e:
        notificacao = f'⚠️ Campo ausente na montagem: {e}'
    except Exception as e:
        notificacao = f'⚠️ Erro ao montar notificação: {e}'

    st.code(notificacao, language='text')
