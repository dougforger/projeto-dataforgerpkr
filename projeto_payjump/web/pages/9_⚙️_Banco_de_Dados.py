import pandas as pd
import streamlit as st

from utils.arquivo_utils import corrigir_xlsx_memoria
from utils.clubes_db import carregar_clubes, sincronizar_clubes
from utils.ligas_db import carregar_ligas, inserir_liga, sincronizar_ligas_csv
from utils.supabase_client import exibir_status_conexao

st.set_page_config(
    page_title='Banco de Dados',
    page_icon='⚙️',
    layout='wide',
    initial_sidebar_state='expanded',
)

with st.sidebar:
    exibir_status_conexao()

st.title('⚙️ Banco de Dados')
st.markdown('---')

col_clubes, col_ligas = st.columns(2)

# ── Coluna de Clubes ──────────────────────────────────────────────────────────

with col_clubes:
    st.markdown('### 🏠 Clubes')
    st.caption(
        'Faça upload da planilha exportada pelo sistema (aba **Sheet1**) para '
        'atualizar a lista de clubes no Supabase. Apenas clubes pertencentes às '
        'ligas cadastradas são importados.'
    )

    arquivo_clubes = st.file_uploader(
        'Selecione a planilha de clubes (.xlsx)',
        type=['xlsx', 'xls'],
        key='uploader_clubes',
    )

    if arquivo_clubes is not None:
        if st.button('⚙️ Processar e sincronizar clubes', use_container_width=True):
            try:
                with st.spinner('Lendo planilha...'):
                    buffer = corrigir_xlsx_memoria(arquivo_clubes)
                    abas = pd.ExcelFile(buffer).sheet_names
                    aba_alvo = next((a for a in abas if a.lower() == 'sheet1'), None)
                    if aba_alvo is None:
                        st.error(f'Aba "Sheet1" não encontrada. Abas disponíveis: {abas}')
                        st.stop()
                    buffer.seek(0)
                    df_raw = pd.read_excel(buffer, sheet_name=aba_alvo, engine='openpyxl')

                with st.spinner('Filtrando clubes pelas ligas cadastradas...'):
                    lista_ligas = carregar_ligas()
                    ligas_validas = lista_ligas['liga_id'].unique().tolist()

                    df_filtrado = df_raw[df_raw['Union ID'].isin(ligas_validas)].copy()
                    df_filtrado = df_filtrado[['Club ID', 'Name', 'Union ID']].rename(columns={
                        'Club ID':  'clube_id',
                        'Name':     'clube_nome',
                        'Union ID': 'liga_id',
                    })
                    df_filtrado['clube_id']   = df_filtrado['clube_id'].astype(int)
                    df_filtrado['liga_id']    = df_filtrado['liga_id'].astype(int)
                    df_filtrado['clube_nome'] = df_filtrado['clube_nome'].astype(str)
                    df_filtrado = df_filtrado.merge(
                        lista_ligas[['liga_id', 'liga_nome']], on='liga_id', how='left'
                    )
                    df_filtrado = df_filtrado[['clube_id', 'clube_nome', 'liga_id', 'liga_nome']]
                    df_filtrado = df_filtrado.drop_duplicates(subset=['clube_id'])

                with st.spinner('Sincronizando com o Supabase...'):
                    inseridos, atualizados = sincronizar_clubes(df_filtrado)

                st.success(
                    f'✅ Sincronização concluída!\n\n'
                    f'**{inseridos}** clubes inseridos  \n'
                    f'**{atualizados}** clubes atualizados  \n'
                    f'**{len(df_filtrado)}** clubes no total'
                )
                st.cache_data.clear()

            except Exception as e:
                st.error(f'Erro durante a sincronização: {e}')

    st.markdown('---')
    st.markdown('#### Clubes cadastrados no banco')

    try:
        df_clubes = carregar_clubes()
        if df_clubes.empty:
            st.info('Nenhum clube cadastrado. Faça a sincronização acima.')
        else:
            col_busca, col_liga_filtro = st.columns(2)
            with col_busca:
                busca = st.text_input('Buscar por nome', placeholder='Digite parte do nome...')
            with col_liga_filtro:
                ligas_disponiveis = sorted(df_clubes['liga_nome'].dropna().unique())
                liga_filtro = st.multiselect('Filtrar por liga', ligas_disponiveis, default=ligas_disponiveis)

            df_exibir = df_clubes.copy()
            if busca:
                df_exibir = df_exibir[df_exibir['clube_nome'].str.contains(busca, case=False, na=False)]
            if liga_filtro:
                df_exibir = df_exibir[df_exibir['liga_nome'].isin(liga_filtro)]

            st.caption(f'{len(df_exibir):,} clubes exibidos de {len(df_clubes):,} no total')
            st.dataframe(df_exibir, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f'Erro ao carregar clubes: {e}')


# ── Coluna de Ligas ───────────────────────────────────────────────────────────

with col_ligas:
    st.markdown('### 🏆 Ligas')

    st.markdown('#### Sincronizar pelo ligas.csv')
    st.caption(
        'Lê o arquivo **ligas.csv** local e faz upsert de todas as ligas no Supabase. '
        'Ligas existentes são atualizadas; novas são inseridas.'
    )

    if st.button('⚙️ Sincronizar ligas do CSV', use_container_width=False):
        try:
            with st.spinner('Sincronizando ligas...'):
                inseridas, atualizadas = sincronizar_ligas_csv()
            st.success(
                f'✅ Sincronização concluída!\n\n'
                f'**{inseridas}** ligas inseridas  \n'
                f'**{atualizadas}** ligas atualizadas'
            )
            st.cache_data.clear()
        except Exception as e:
            st.error(f'Erro: {e}')

    st.markdown('---')
    st.markdown('#### Adicionar / atualizar liga manualmente')
    st.caption('Preencha os campos abaixo para inserir ou atualizar uma liga individualmente.')

    with st.form('form_nova_liga', clear_on_submit=True):
        form_col1, form_col2 = st.columns(2)
        with form_col1:
            nova_liga_id   = st.number_input('Liga ID *', min_value=1, step=1, value=None, placeholder='Ex: 220')
            nova_liga_nome = st.text_input('Nome da liga *', placeholder='Ex: Suprema Brasil')
            novo_idioma    = st.selectbox('Idioma', ['português', 'inglês', 'espanhol'], index=None, placeholder='Selecione...')
        with form_col2:
            novo_handicap  = st.number_input('Handicap', min_value=0.0, step=0.1, value=None, placeholder='Ex: 5.0')
            nova_moeda     = st.selectbox('Moeda', ['BRL', 'USD', 'MXN', 'SOL', 'BOL', 'KZT', 'INR'], index=None, placeholder='Selecione...')
            nova_taxa      = st.number_input('Taxa da liga', min_value=0.0, max_value=1.0, step=0.01, value=None, placeholder='Ex: 0.18')

        submitted = st.form_submit_button('💾 Salvar liga', use_container_width=True)

    if submitted:
        if not nova_liga_id or not nova_liga_nome:
            st.warning('Liga ID e Nome da liga são obrigatórios.')
        else:
            try:
                inserir_liga(
                    liga_id=int(nova_liga_id),
                    liga_nome=nova_liga_nome,
                    idioma=novo_idioma,
                    handicap=novo_handicap,
                    moeda=nova_moeda,
                    taxa_liga=nova_taxa,
                )
                st.success(f'✅ Liga **{nova_liga_nome}** (ID {nova_liga_id}) salva com sucesso!')
                st.cache_data.clear()
            except Exception as e:
                st.error(f'Erro ao salvar liga: {e}')

    st.markdown('---')
    st.markdown('#### Ligas cadastradas no banco')

    try:
        df_ligas = carregar_ligas()
        if df_ligas.empty:
            st.info('Nenhuma liga cadastrada. Sincronize pelo CSV ou adicione manualmente.')
        else:
            st.caption(f'{len(df_ligas):,} ligas cadastradas')
            st.dataframe(df_ligas, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f'Erro ao carregar ligas: {e}')
