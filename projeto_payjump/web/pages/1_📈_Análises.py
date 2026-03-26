import pandas as pd
import streamlit as st
from pathlib import Path

from utils.arquivo_utils import carregar_xlsx
from utils.analise_backend import analisar_cash, analisar_torneios, detalhar_torneio, gerar_pdf
from utils.imagem_utils import gerar_imagem_df
from utils.analise_snowflake import (
    preprocessar_dados,
    resumo_por_jogador,
    detectar_mesas_comuns,
    detectar_dispositivos_compartilhados,
    detectar_ips_compartilhados,
    gerar_pdf_snowflake,
)
from utils.geolocation import buscar_localizacao_ips, buscar_geocodificacao_reversa
from utils.mapa_utils import exibir_mapa_folium
from utils.pdf_config import MULTIPLICADOR_MOEDA

BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# -----------------------------------------------------
st.set_page_config(
    page_title='Análises',
    page_icon='📈',
    layout='wide',
    initial_sidebar_state='collapsed',
)

st.title('📈 Análises')
st.markdown('---')


# -----------------------------------------------------
# FUNÇÕES DE APOIO
# -----------------------------------------------------
@st.cache_data
def carregar_dados(arquivo):
    return pd.read_csv(arquivo)


@st.dialog('📄 Relatório', width='large')
def gerar_relatorio(torneio_selecionado, resumo_torneio, df_torneio):
    if torneio_selecionado is None or resumo_torneio.empty:
        st.warning('Nenhum torneio selecionado ou sem dados de torneio.')
        return

    relatorio  = f'#### Game ID: {torneio_selecionado}\n\n'
    relatorio += '| Jogador | Clube | Prize | KOs | Total |\n'
    relatorio += '|---------|-------|-------|-----|-------|\n'
    for _, row in resumo_torneio.iterrows():
        relatorio += rf"| {row['Player Name']} | {row['Club Name']} | {row['Prize']:.2f} | {row['KO\'s']:.2f} | {row['Total']:.2f} |"
        relatorio += '\n'

    relatorio += '\n'
    relatorio += '| Jogador | Clube | Evento | Ganhos |\n'
    relatorio += '|---------|-------|--------|--------|\n'
    for _, row in df_torneio.iterrows():
        relatorio += f"| {row['Player Name']} | {row['Club Name']} | {row['Event']} | {row['chip change']:.2f} |\n"

    st.code(relatorio, language='text')
    observacoes = st.text_area('Adicione suas observações aqui')
    if observacoes:
        st.code(relatorio + '\n---\n### Observações:\n' + observacoes, language='text')


# -----------------------------------------------------
# ABAS
# -----------------------------------------------------
aba_backend, aba_snowflake = st.tabs(['Backend', 'Snowflake'])


# ======================================================
# ABA BACKEND
# ======================================================
with aba_backend:
    if 'df_backend' not in st.session_state:
        st.session_state.df_backend = None

    col_upload_backend, col_limpa_backend = st.columns([4, 1], vertical_alignment='bottom')
    with col_upload_backend:
        upload_files = st.file_uploader(
            'Selecione o(s) arquivo(s) para fazer o upload e carregar os dados.',
            type=['xls', 'xlsx'],
            accept_multiple_files=True,
        )
    with col_limpa_backend:
        if st.button('🗑️ Limpar dados', key='backend-limpa-cache'):
            st.session_state.df_backend = None
            st.cache_data.clear()
            st.rerun()

    if upload_files:
        df_backend = carregar_xlsx(upload_files)
        df_backend[['Game ID']] = df_backend['Association'].str.extract(r'Game ID: (\d+)')
        df_backend[['Hand ID']] = df_backend['Association'].str.extract(r'Hand ID: (\d+)')
        # Satélites têm Association no formato 'XXXXX_GAMEID' — extrair segunda parte como Game ID
        sat_mask = (
            df_backend['Game ID'].isna() &
            df_backend['Association'].str.match(r'^\d+_\d+$', na=False)
        )
        df_backend.loc[sat_mask, 'Game ID'] = (
            df_backend.loc[sat_mask, 'Association'].str.extract(r'^\d+_(\d+)$')[0]
        )
        colunas_uteis = [
            'Player ID', 'Player Name', 'Club ID', 'Club Name', 'Union ID', 'Union Name',
            'Event', 'Association', 'Game ID', 'Hand ID', 'chip change', 'Game Fee change',
            'Record time',
        ]
        df_backend = df_backend[colunas_uteis].copy()

        # Conversão para R$: (moeda local / handicap) * 5
        df_ligas_map = pd.read_csv(BASE_DIR / 'data' / 'ligas.csv')[['liga_id', 'handicap']]
        df_ligas_map['liga_id'] = df_ligas_map['liga_id'].astype(int)
        df_ligas_map['handicap'] = df_ligas_map['handicap'].astype(float)
        df_backend['Union ID']  = df_backend['Union ID'].astype(int)
        handicap_map = df_ligas_map.set_index('liga_id')['handicap'].to_dict()
        handicap_series = df_backend['Union ID'].map(handicap_map).fillna(1)
        df_backend['chip change']     = (df_backend['chip change']     / handicap_series) * MULTIPLICADOR_MOEDA
        df_backend['Game Fee change'] = (df_backend['Game Fee change'] / handicap_series) * MULTIPLICADOR_MOEDA

        st.session_state.df_backend = df_backend
        st.success(f'✅ {len(upload_files)} arquivo(s) carregado(s)! {len(st.session_state.df_backend)} linhas encontradas. Valores convertidos para R$.')

    if st.session_state.df_backend is not None:
        with st.expander('👀 Visualizar arquivo carregado'):
            st.dataframe(st.session_state.df_backend, hide_index=True, width='stretch')

    # Defaults (garantem que os botões sempre tenham variáveis definidas)
    df_cash            = pd.DataFrame()
    df_pares_cash      = pd.DataFrame()
    resumo_cash        = pd.DataFrame()
    mesas_comuns_cash  = set()
    df_mtt             = pd.DataFrame()
    df_pares_mtt       = pd.DataFrame()
    resumo_mtt         = pd.DataFrame()
    torneios_comuns    = set()
    mesas_selecionada_mtt = None
    df_mesa_mtt_resumo = pd.DataFrame()
    df_mesa_mtt        = pd.DataFrame()

    if st.session_state.df_backend is not None:
        col_cash, col_mtt = st.columns(2)

        with col_cash:
            st.subheader('Cash Game')
            df_cash = st.session_state.df_backend[st.session_state.df_backend['Event'] == 'gameResult'].copy()
            st.info(f'🎯 {len(df_cash)} mãos em cash game encontradas.')

            if not df_cash.empty:
                st.dataframe(df_cash.head())
                resumo_cash, df_pares_cash, mesas_comuns_cash = analisar_cash(df_cash)

                st.dataframe(resumo_cash, hide_index=True, width='stretch',
                             column_config={
                                 'Ganhos (R$)': st.column_config.NumberColumn(format='localized'),
                                 'Rake (R$)':   st.column_config.NumberColumn(format='localized'),
                             })

                lista_jogadores = ['Todos'] + sorted(df_cash['Player Name'].unique().tolist())
                col_filtro_a, col_filtro_b = st.columns(2)
                with col_filtro_a:
                    filtro_a = st.selectbox('Jogador A', lista_jogadores)
                with col_filtro_b:
                    filtro_b = st.selectbox('Jogador B', lista_jogadores)

                df_pares_filtrado = df_pares_cash.copy()
                if filtro_a != 'Todos':
                    df_pares_filtrado = df_pares_filtrado[
                        (df_pares_filtrado['Jogador A'] == filtro_a) |
                        (df_pares_filtrado['Jogador B'] == filtro_a)
                    ]
                if filtro_b != 'Todos':
                    df_pares_filtrado = df_pares_filtrado[
                        (df_pares_filtrado['Jogador A'] == filtro_b) |
                        (df_pares_filtrado['Jogador B'] == filtro_b)
                    ]
                st.dataframe(df_pares_filtrado, hide_index=True, width='stretch')

                if mesas_comuns_cash:
                    st.markdown('---')
                    st.subheader('Detalhamento por mesa')
                    mesa_selecionada_cash = st.selectbox('Selecione uma mesa', sorted(mesas_comuns_cash, reverse=True))
                    _ids_cash = df_cash[df_cash['Game ID'] == mesa_selecionada_cash]['Player ID'].unique()
                    _url_cash = (
                        f'https://console.supremapoker.net/game/GameDetail'
                        f'?backupOnly=0&dateFilter=16&matchID={mesa_selecionada_cash}'
                        f'&page=1&pageSize=100&playerIDs={"&".join(str(p) for p in _ids_cash)}'
                    )
                    st.link_button('🔗 Acessar Hand History', _url_cash)
                    _df_mesa_cash_all = df_cash[df_cash['Game ID'] == mesa_selecionada_cash]
                    _maos_compartilhadas_cash = (
                        _df_mesa_cash_all.groupby('Hand ID')['Player ID']
                        .nunique()
                        .pipe(lambda s: s[s > 1].index)
                    )
                    df_mesa_cash = (
                        _df_mesa_cash_all[_df_mesa_cash_all['Hand ID'].isin(_maos_compartilhadas_cash)]
                        .copy().sort_values(['Hand ID', 'Player ID'])
                    )
                    df_mesa_cash_resumo = df_mesa_cash.groupby(['Player ID', 'Player Name', 'Club Name']).agg(
                        Ganhos   =('chip change',    'sum'),
                        Rake     =('Game Fee change', 'sum'),
                        Qnt_Maos =('Hand ID',         'count'),
                    ).reset_index()
                    st.dataframe(df_mesa_cash_resumo, hide_index=True, width='stretch',
                                 column_config={
                                     'Ganhos': st.column_config.NumberColumn(format='localized'),
                                     'Rake':   st.column_config.NumberColumn(format='localized'),
                                 })
                    st.dataframe(
                        df_mesa_cash.drop(columns=['Event', 'Association'], errors='ignore'),
                        hide_index=True, width='stretch',
                    )

        with col_mtt:
            st.subheader('Torneios')
            df_mtt = st.session_state.df_backend[
                st.session_state.df_backend['Event'].isin(['MttPrize', 'SAT MTT Prize'])
            ].copy()
            st.info(f'🏆 {len(df_mtt)} torneios finalizados.')

            if not df_mtt.empty:
                resumo_mtt, df_pares_mtt, torneios_comuns = analisar_torneios(df_mtt)
                st.dataframe(resumo_mtt, hide_index=True, width='stretch',
                             column_config={
                                 'Ganhos (R$)': st.column_config.NumberColumn(format='localized'),
                                 'Rake (R$)':   st.column_config.NumberColumn(format='localized'),
                             })

                if not df_pares_mtt.empty:
                    st.dataframe(df_pares_mtt, hide_index=True, width='stretch')

                    if torneios_comuns:
                        st.markdown('---')
                        st.subheader('Detalhamento por Torneio')
                        mesas_selecionada_mtt = st.selectbox('Selecione um Torneio', sorted(torneios_comuns, reverse=True))
                        _ids_mtt = df_mtt[df_mtt['Game ID'] == mesas_selecionada_mtt]['Player ID'].unique()
                        _url_mtt = (
                            f'https://console.supremapoker.net/game/GameDetail'
                            f'?backupOnly=0&dateFilter=16&matchID={mesas_selecionada_mtt}'
                            f'&page=1&pageSize=100&playerIDs={"&".join(str(p) for p in _ids_mtt)}'
                        )
                        st.link_button('🔗 Acessar Hand History', _url_mtt)
                        df_mesa_mtt_resumo, df_mesa_mtt = detalhar_torneio(st.session_state.df_backend, mesas_selecionada_mtt)

                        total_row = pd.DataFrame([{
                            'Player ID':   'TOTAL',
                            'Player Name': '',
                            'Club Name':   '',
                            'Prize':       df_mesa_mtt_resumo['Prize'].sum(),
                            "KO's":        df_mesa_mtt_resumo["KO's"].sum(),
                            'Total':       df_mesa_mtt_resumo['Total'].sum(),
                        }])
                        df_mesa_mtt_resumo_display = pd.concat([df_mesa_mtt_resumo, total_row], ignore_index=True)
                        df_mesa_mtt_resumo_display['Jogador'] = df_mesa_mtt_resumo_display.apply(
                            lambda r: f'{r["Player Name"]} ({r["Player ID"]})' if str(r['Player ID']) != 'TOTAL' else 'TOTAL',
                            axis=1,
                        )

                        df_torneio_display = (
                            df_mesa_mtt_resumo_display[['Jogador', 'Club Name', 'Prize', "KO's", 'Total']]
                            .rename(columns={'Club Name': 'Clube', 'Prize': 'Prêmio', "KO's": 'KO'})
                        )
                        st.dataframe(
                            df_torneio_display,
                            hide_index=True, width='stretch',
                            column_config={
                                'Prêmio': st.column_config.NumberColumn(format='localized'),
                                'KO':     st.column_config.NumberColumn(format='localized'),
                                'Total':  st.column_config.NumberColumn(format='localized'),
                            })
                        st.download_button(
                            label='📷 Exportar tabela como imagem',
                            data=gerar_imagem_df(
                                df_torneio_display,
                                formatar_colunas=['Prêmio', 'KO', 'Total'],
                                titulo=f'Torneio {mesas_selecionada_mtt}',
                            ),
                            file_name=f'PREMIO-{mesas_selecionada_mtt}.png',
                            mime='image/png',
                        )

                        df_mesa_mtt_display = df_mesa_mtt.copy()
                        df_mesa_mtt_display.insert(
                            0, 'Conta',
                            df_mesa_mtt_display['Player Name'] + ' (' + df_mesa_mtt_display['Player ID'].astype(str) + ')',
                        )
                        st.dataframe(
                            df_mesa_mtt_display.drop(columns=['Player ID', 'Player Name']),
                            hide_index=True, width='stretch',
                        )
                else:
                    st.info(f'Somente a conta {resumo_mtt["Player Name"].iloc[0]} possui registro em torneios.')

    protocolo = st.text_input('Número do Protocolo', value='', placeholder='Ex: 1305308689')
    col_btn_relatorio, col_btn_pdf = st.columns(2)

    with col_btn_relatorio:
        if st.button('📄 Gerar Relatório', width='stretch'):
            gerar_relatorio(mesas_selecionada_mtt, df_mesa_mtt_resumo, df_mesa_mtt)

    with col_btn_pdf:
        if st.session_state.df_backend is not None:
            pdf = gerar_pdf(
                protocolo,
                df_pares_cash, df_pares_mtt,
                df_cash, df_mtt,
                mesas_comuns_cash, torneios_comuns,
                resumo_cash, resumo_mtt,
                mesas_selecionada_mtt,
                df_mesa_mtt_resumo,
                df_mesa_mtt,
            )
            st.download_button(
                label='📄 Baixar Relatório em PDF',
                data=pdf,
                file_name=f'MESAS-{protocolo}.pdf',
                mime='application/pdf',
                width='stretch',
            )


# ======================================================
# ABA SNOWFLAKE
# ======================================================
with aba_snowflake:
    if 'df_snowflake' not in st.session_state:
        st.session_state.df_snowflake = None

    col_upload_sf, col_limpa_sf = st.columns([4, 1], vertical_alignment='bottom')
    with col_upload_sf:
        upload_file = st.file_uploader(
            'Selecione o arquivo para fazer o upload e carregar os dados.',
            type='csv',
        )
    with col_limpa_sf:
        if st.button('🗑️ Limpar dados', key='snowflake-limpa-cache'):
            st.session_state.df_snowflake = None
            st.cache_data.clear()
            st.rerun()

    if upload_file is not None:
        df_bruto  = carregar_dados(upload_file)
        df_clubes = pd.read_csv(BASE_DIR / 'data' / 'clubes.csv')
        df_ligas  = pd.read_csv(BASE_DIR / 'data' / 'ligas.csv')

        df_processado, qtd_removidas = preprocessar_dados(df_bruto, df_clubes, df_ligas)
        st.session_state.df_snowflake = df_processado

        msg = f'✅ Arquivo carregado! {len(df_processado)} linhas encontradas. Valores já convertidos para a moeda local de acordo com a liga.'
        if qtd_removidas > 0:
            msg += f' {qtd_removidas} linha(s) de torneio removidas (ID_MODALIDADE ≥ 100).'
        st.success(msg)

    if st.session_state.df_snowflake is not None:
        with st.expander('👀 Visualizar arquivo carregado'):
            st.dataframe(st.session_state.df_snowflake, hide_index=True, width='stretch')

    st.markdown('---')

    # Defaults
    df_pares_sf            = pd.DataFrame()
    mesas_comuns_sf        = set()
    resumo_sf              = pd.DataFrame()
    df_dispositivos        = pd.DataFrame()
    df_ips_com_localizacao = pd.DataFrame()
    df_geo                 = pd.DataFrame()

    if st.session_state.df_snowflake is not None:
        df_sf = st.session_state.df_snowflake
        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader('Resumo dos jogadores')
            resumo_jogadores = resumo_por_jogador(df_sf)
            resumo_jogadores_display = resumo_jogadores.copy()
            resumo_jogadores_display.insert(
                0, 'Conta',
                resumo_jogadores_display['Jogador Nome'] + ' (' + resumo_jogadores_display['Jogador ID'].astype(str) + ')',
            )
            st.dataframe(
                resumo_jogadores_display[['Conta', 'Clube Nome', 'Total de Mesas', 'Ganhos (R$)', 'Rake (R$)']],
                hide_index=True, width='stretch',
                column_config={
                    'Ganhos (R$)': st.column_config.NumberColumn(format='localized'),
                    'Rake (R$)':   st.column_config.NumberColumn(format='localized'),
                })

            st.subheader('Mesas em comum')
            df_pares_sf, mesas_comuns_sf = detectar_mesas_comuns(df_sf, resumo_jogadores)
            st.dataframe(df_pares_sf, hide_index=True, width='stretch')

        with col2:
            st.subheader('Dispositivos')
            df_dispositivos, codigos_compartilhados = detectar_dispositivos_compartilhados(df_sf)
            df_disp_display = df_dispositivos.copy()
            df_disp_display['Jogador'] = df_disp_display['NOME_JOGADOR'] + ' (' + df_disp_display['ID_JOGADOR'].astype(str) + ')'
            st.dataframe(
                df_disp_display[['Jogador', 'CODIGO_DISPOSITIVO', 'DISPOSITIVO', 'SISTEMA']].rename(columns={
                    'CODIGO_DISPOSITIVO':'Cód. Dispositivo',
                    'DISPOSITIVO':       'Dispositivo',
                    'SISTEMA':           'Sistema',
                }),
                hide_index=True, width='stretch',
            )
            if codigos_compartilhados:
                st.warning(f'⚠️ {len(codigos_compartilhados)} dispositivo(s) compartilhado(s) entre os jogadores.')
            else:
                st.success('✅ Nenhum dispositivo compartilhado.')

            st.subheader('Endereços IP')
            df_ips_bruto, ips_compartilhados = detectar_ips_compartilhados(df_sf)
            if 'ip_cache' not in st.session_state:
                st.session_state.ip_cache = {}
            df_ips_com_localizacao = buscar_localizacao_ips(df_ips_bruto, st.session_state.ip_cache)
            df_ips_display = df_ips_com_localizacao.copy()
            df_ips_display['Jogador'] = df_ips_display['NOME_JOGADOR'] + ' (' + df_ips_display['ID_JOGADOR'].astype(str) + ')'
            st.dataframe(
                df_ips_display[['Jogador', 'IP', 'CIDADE', 'ESTADO', 'PAIS']].rename(columns={
                    'CIDADE': 'Cidade',
                    'ESTADO': 'Estado',
                    'PAIS':   'País',
                }),
                hide_index=True, width='stretch',
            )
            if ips_compartilhados:
                st.warning(f'⚠️ {len(ips_compartilhados)} IP(s) compartilhado(s) entre os jogadores.')
            else:
                st.success('✅ Nenhum IP compartilhado.')
            if not df_ips_com_localizacao.empty:
                with st.expander('🗺️ Mapa de IPs', expanded=True):
                    exibir_mapa_folium(
                        df_ips_com_localizacao.rename(columns={'ID_JOGADOR': 'JOGADOR_ID', 'NOME_JOGADOR': 'JOGADOR'}),
                        key='ip_analise_sf',
                    )

        with col3:
            st.subheader('Geolocalização')
            df_coords = (
                df_sf[['NOME_JOGADOR', 'ID_MESA', 'NOME_MESA', 'LATITUDE', 'LONGITUDE']]
                .dropna(subset=['LATITUDE', 'LONGITUDE'])
                .drop_duplicates()
                .copy()
            )
            df_coords['LATITUDE']     = df_coords['LATITUDE'].astype(float).round(3)
            df_coords['LONGITUDE']    = df_coords['LONGITUDE'].astype(float).round(3)
            df_coords['NOME_JOGADOR'] = df_coords['NOME_JOGADOR'].str.strip()

            if 'geo_cache' not in st.session_state:
                st.session_state.geo_cache = {}

            df_geo = buscar_geocodificacao_reversa(df_coords, st.session_state.geo_cache)
            df_geo = df_geo.merge(
                df_sf[['NOME_JOGADOR', 'ID_JOGADOR']].drop_duplicates(),
                on='NOME_JOGADOR', how='left',
            ).sort_values('ID_JOGADOR')

            if df_geo.empty:
                st.info('Jogadores sem registro de localização por GPS.')
            else:
                df_geo_display = df_geo[['ID_JOGADOR', 'NOME_JOGADOR', 'CIDADE', 'ESTADO', 'PAIS']].drop_duplicates().copy()
                df_geo_display['Jogador'] = df_geo_display['NOME_JOGADOR'] + ' (' + df_geo_display['ID_JOGADOR'].astype(str) + ')'
                st.dataframe(
                    df_geo_display[['Jogador', 'CIDADE', 'ESTADO', 'PAIS']].rename(columns={
                        'CIDADE': 'Cidade',
                        'ESTADO': 'Estado',
                        'PAIS':   'País',
                    }),
                    hide_index=True, width='stretch',
                )

            cidades_comuns = df_geo.groupby('CIDADE')['NOME_JOGADOR'].nunique()
            cidades_comuns = cidades_comuns[cidades_comuns > 1].index.tolist()
            if cidades_comuns:
                st.warning(f'⚠️ Jogadores na mesma cidade: {", ".join(cidades_comuns)}')
            else:
                st.success('✅ Nenhuma localização em comum.')
            if not df_geo.empty:
                with st.expander('🗺️ Mapa de GPS', expanded=True):
                    exibir_mapa_folium(
                        df_geo.rename(columns={'ID_JOGADOR': 'JOGADOR_ID', 'NOME_JOGADOR': 'JOGADOR'}),
                        key='gps_analise_sf',
                    )

        # --------------------------------------------------
        # Detalhamento por mesa
        # --------------------------------------------------
        st.markdown('---')
        st.subheader('Detalhamento por mesa')
        mesas_ordenadas  = sorted(mesas_comuns_sf, reverse=True)
        mesa_selecionada = st.selectbox('Selecione uma mesa para mais detalhes.', mesas_ordenadas)
        _ids_sf = df_sf[df_sf['ID_MESA'] == mesa_selecionada]['ID_JOGADOR'].unique()
        _url_sf = (
            f'https://console.supremapoker.net/game/GameDetail'
            f'?backupOnly=0&dateFilter=16&matchID={mesa_selecionada}'
            f'&page=1&pageSize=100&playerIDs={"&".join(str(p) for p in _ids_sf)}'
        )
        st.link_button('🔗 Acessar Hand History', _url_sf)

        # Apenas mãos onde mais de um jogador do dataset participou
        _df_mesa_all = df_sf[df_sf['ID_MESA'] == mesa_selecionada]
        maos_compartilhadas = (
            _df_mesa_all.groupby('ID_MAO')['ID_JOGADOR']
            .nunique()
            .pipe(lambda s: s[s > 1].index)
        )
        df_mesa_base = _df_mesa_all[_df_mesa_all['ID_MAO'].isin(maos_compartilhadas)]

        df_mesa_resumo = (
            df_mesa_base
            .groupby(['ID_JOGADOR','NOME_JOGADOR', 'NOME_CLUBE', 'ID_MESA'])
            .agg(
                TOTAL_GANHOS=('GANHOS', 'sum'),
                TOTAL_RAKE  =('RAKE',   'sum'),
                QNT_MAOS    =('ID_MAO', 'count'),
            ).reset_index()
        )
        df_mesa_resumo_display = df_mesa_resumo.copy()
        df_mesa_resumo_display.insert(
            0, 'Conta',
            df_mesa_resumo_display['NOME_JOGADOR'] + ' (' + df_mesa_resumo_display['ID_JOGADOR'].astype(str) + ')',
        )
        df_mesa_resumo_img = (
            df_mesa_resumo_display[['Conta', 'NOME_CLUBE', 'TOTAL_GANHOS', 'TOTAL_RAKE', 'QNT_MAOS']]
            .rename(columns={
                'Conta':        'Jogador',
                'NOME_CLUBE':   'Clube',
                'TOTAL_GANHOS': 'Ganhos (R$)',
                'TOTAL_RAKE':   'Rake (R$)',
                'QNT_MAOS':     'Qtd. Mãos',
            })
        )
        st.dataframe(
            df_mesa_resumo_img,
            hide_index=True, width='stretch',
            column_config={
                'Ganhos (R$)': st.column_config.NumberColumn(format='localized'),
                'Rake (R$)':   st.column_config.NumberColumn(format='localized'),
            },
        )
        st.download_button(
            label='📷 Exportar tabela como imagem',
            data=gerar_imagem_df(
                df_mesa_resumo_img,
                formatar_colunas=['Ganhos (R$)', 'Rake (R$)'],
                titulo=f'Mesa {mesa_selecionada}',
            ),
            file_name=f'mesa-{mesa_selecionada}.png',
            mime='image/png',
        )
        df_mesa = df_mesa_base.sort_values(['ID_MAO', 'ID_JOGADOR']).copy()
        df_mesa.insert(0, 'Conta', df_mesa['NOME_JOGADOR'] + ' (' + df_mesa['ID_JOGADOR'].astype(str) + ')')
        st.dataframe(
            df_mesa[['DATA', 'Conta', 'NOME_CLUBE', 'ID_MAO', 'GANHOS', 'RAKE', 'IP', 'IP_PAIS']]
            .rename(columns={
                'DATA':      'Data',
                'NOME_CLUBE':'Clube',
                'ID_MAO':    'ID Mão',
                'GANHOS':    'Ganhos (R$)',
                'RAKE':      'Rake (R$)',
                'IP_PAIS':   'País (IP)',
            }),
            hide_index=True, width='stretch',
            column_config={
                'Ganhos (R$)': st.column_config.NumberColumn(format='localized'),
                'Rake (R$)':   st.column_config.NumberColumn(format='localized'),
            },
        )

        # --------------------------------------------------
        # PDF
        # --------------------------------------------------
        resumo_sf = (
            df_sf.groupby(['ID_JOGADOR','NOME_JOGADOR', 'NOME_CLUBE']).agg(
                **{
                    'Total de Mesas': ('ID_MESA', 'nunique'),
                    'Ganhos (R$)':    ('GANHOS',  'sum'),
                    'Rake (R$)':      ('RAKE',    'sum'),
                }
            ).reset_index()
            .rename(columns={'ID_JOGADOR': 'Player ID','NOME_JOGADOR': 'Player Name', 'NOME_CLUBE': 'Club Name'})
        )
        df_sf_norm = df_sf.rename(columns={'ID_MESA': 'Game ID', 'ID_JOGADOR': 'Player ID', 'NOME_JOGADOR': 'Player Name'})

        st.markdown('---')
        protocolo_sf = st.text_input(
            'Número do Protocolo', value='', placeholder='Ex: 1305308689',
            key='protocolo_snowflake',
        )
        pdf_sf = gerar_pdf_snowflake(
            protocolo_sf,
            df_pares_sf, df_sf_norm, mesas_comuns_sf, resumo_sf,
            df_dispositivos, df_ips_com_localizacao, df_geo,
        )
        st.download_button(
            label='📄 Baixar Relatório em PDF',
            data=pdf_sf,
            file_name=f'MESAS-{protocolo_sf}.pdf',
            mime='application/pdf',
            width='stretch',
        )
