import streamlit as st
import datetime

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
# CONSTANTES DOS FILTROS
# -----------------------------------------------------
CATEGORIAS = ['Collusion', 'Software Ilegal (BOT)', 'Abuso de Chat', 'Chip Dumping', 'Aliciamento', 'Fraude']
TIPOS = ['Investigação interna', 'Denúncia']
RESULTADOS = ['Positivo', 'Negativo']

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
    categorias_selecionadas = st.multiselect(
        'Categoria:',
        CATEGORIAS,
        default=CATEGORIAS,
    )

    # -- Filtro de tipo de ocorrência ------------------------------------------
    tipos_selecionados = st.multiselect(
        'Tipo de ocorrência:',
        TIPOS,
        default=TIPOS,
    )

    # -- Filtro de resultado da análise ----------------------------------------
    resultados_selecionados = st.multiselect(
        'Resultado da análise:',
        RESULTADOS,
        default=RESULTADOS,
    )

with col_dashboard:
    st.info('Aqui será montado o dash.')
