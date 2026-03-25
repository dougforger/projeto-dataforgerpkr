import streamlit as st

from utils.pipefy_api import testar_conexao

# -----------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# -----------------------------------------------------
st.set_page_config(
    page_title='Pipefy',
    page_icon='🔗',
    layout='wide',
    initial_sidebar_state='collapsed',
)

st.title('🔗 Pipefy')
st.markdown('---')

# -----------------------------------------------------
# TESTE DE CONEXÃO
# -----------------------------------------------------
if st.button('Testar Conexão'):
    with st.spinner('Conectando à API do Pipefy...'):
        try:
            usuario = testar_conexao()
            st.success(
                f'Conexão estabelecida com sucesso! '
                f'Autenticado como **{usuario["name"]}** ({usuario["email"]})'
            )
        except Exception as e:
            st.error(f'Falha na conexão: {e}')
