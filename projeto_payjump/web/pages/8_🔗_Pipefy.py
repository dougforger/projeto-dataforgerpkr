import streamlit as st
import datetime

from utils.pipefy_api import testar_conexao, buscar_opcoes_campos, PIPE_ID

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

DATA_PRIMEIRO_CARD = datetime.date(2021, 10, 1)

# -----------------------------------------------------
# DIAGNÓSTICO (escondido por padrão)
# -----------------------------------------------------
with st.expander('🔧 Diagnóstico de conexão'):
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

# -----------------------------------------------------
# OPÇÕES DINÂMICAS (cache de 1 hora)
# -----------------------------------------------------
@st.cache_data(ttl=3600)
def carregar_opcoes():
    return buscar_opcoes_campos(PIPE_ID)

opcoes = carregar_opcoes()

# -----------------------------------------------------
# LAYOUT
# -----------------------------------------------------
col_filtros, col_dashboard = st.columns([1, 6])

with col_filtros:
    hoje = datetime.date.today()
    primeiro_dia_mes = hoje.replace(day=1)

    # -- Filtro de data --------------------------------------------------------
    data_inicial = st.date_input(
        'Data inicial:',
        primeiro_dia_mes,
        min_value=DATA_PRIMEIRO_CARD,
        max_value=hoje,
        key='filtro-data-inicial',
    )
    data_final = st.date_input(
        'Data final:',
        hoje,
        min_value=DATA_PRIMEIRO_CARD,
        max_value=hoje,
        key='filtro-data-final',
    )
    if data_inicial > data_final:
        st.warning('⚠️ A data inicial é após a data final.')
        st.stop()

    # -- Filtro de categoria ---------------------------------------------------
    categorias = opcoes.get('categoria_category', [])
    categorias_selecionadas = st.multiselect(
        'Categoria:',
        categorias,
        default=categorias,
    )

    # -- Filtro de tipo de ocorrência ------------------------------------------
    tipos = opcoes.get('tipo_de_ocorr_ncia', [])
    tipos_selecionados = st.multiselect(
        'Tipo de ocorrência:',
        tipos,
        default=tipos,
    )

    # -- Filtro de resultado da análise ----------------------------------------
    resultados = opcoes.get('resultado_da_an_lise', [])
    resultados_selecionados = st.multiselect(
        'Resultado da análise:',
        resultados,
        default=resultados,
    )

with col_dashboard:
    st.info('Aqui será montado o dash.')
