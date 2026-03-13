import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from utils.analise_geo import (
    detectar_alertas_gps,
    detectar_alertas_ip,
    gerar_pdf_geo,
    mapa_cores_hex_por_id,
    preparar_df_gps,
    preparar_df_ip,
    resumo_gps,
    resumo_ip,
)
from utils.arquivo_utils import carregar_xlsx
from utils.geolocation import buscar_geocodificacao_reversa, buscar_localizacao_ips

st.set_page_config(page_title='Geolocalização', page_icon='🌍', layout='wide')
st.title('🌍 Geolocalização')
st.markdown('---')

# -----------------------------------------------------
# SESSION STATE
# -----------------------------------------------------
_CHAVES_CACHE  = ('cache_ips', 'cache_geo')
_CHAVES_DADOS  = ('df_ip_resultado', 'df_gps_resultado', 'alertas_ip', 'alertas_gps',
                  'pdf_bytes', 'pdf_nome')
_CHAVES_MANUAL = ('df_manual_resultado', 'tipo_manual_resultado')

for chave in _CHAVES_CACHE:
    if chave not in st.session_state:
        st.session_state[chave] = {}
for chave in _CHAVES_DADOS + _CHAVES_MANUAL:
    if chave not in st.session_state:
        st.session_state[chave] = None


# -----------------------------------------------------
# HELPERS
# -----------------------------------------------------

def _detectar_tipo_arquivo(df: pd.DataFrame) -> str | None:
    '''Infere o tipo do arquivo exportado com base nas colunas presentes.'''
    if 'IP address' in df.columns:
        return 'IP'
    if 'Coordinate X' in df.columns or 'GPS coordinate Y' in df.columns:
        return 'GPS'
    return None


def _exibir_mapa_folium(df: pd.DataFrame, key: str) -> None:
    '''Exibe mapa folium com marcadores coloridos por JOGADOR_ID e layer control.

    O layer control (🗺️ Ruas / 🛰️ Satélite) é JavaScript puro no browser —
    não causa rerun do Streamlit, então os dados permanecem na tela.
    '''
    colunas_mapa = ['LATITUDE', 'LONGITUDE'] + [
        c for c in ('JOGADOR', 'JOGADOR_ID', 'CIDADE', 'ESTADO', 'PAIS') if c in df.columns
    ]
    df_mapa = df[colunas_mapa].dropna(subset=['LATITUDE', 'LONGITUDE'])

    if df_mapa.empty:
        st.info('Sem coordenadas para exibir no mapa.')
        return

    lat_c = float(df_mapa['LATITUDE'].mean())
    lon_c = float(df_mapa['LONGITUDE'].mean())

    ids       = df_mapa['JOGADOR_ID'].dropna().unique().tolist() if 'JOGADOR_ID' in df_mapa.columns else []
    cores_hex = mapa_cores_hex_por_id(ids) if ids else {}

    m = folium.Map(location=[lat_c, lon_c], zoom_start=4, tiles=None)

    folium.TileLayer('OpenStreetMap', name='🗺️ Ruas').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Tiles &copy; Esri &mdash; Source: Esri, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP',
        name='🛰️ Satélite',
        show=False,
    ).add_to(m)

    for _, row in df_mapa.iterrows():
        id_  = row.get('JOGADOR_ID')
        cor  = cores_hex.get(id_, '#E31A1C') if ids else '#E31A1C'
        nome = row.get('JOGADOR', f'{row["LATITUDE"]:.4f}, {row["LONGITUDE"]:.4f}')
        popup_html = (
            f'<b>{nome}</b><br>'
            f'{row.get("CIDADE", "")} — {row.get("ESTADO", "")} — {row.get("PAIS", "")}'
        )
        folium.CircleMarker(
            location=[float(row['LATITUDE']), float(row['LONGITUDE'])],
            radius=8,
            color=cor,
            fill=True,
            fill_color=cor,
            fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=nome,
        ).add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m, use_container_width=True, height=450, key=key, returned_objects=[])
    _exibir_legenda(df_mapa)


def _exibir_legenda(df_mapa: pd.DataFrame) -> None:
    '''Renderiza legenda de cores abaixo do mapa.'''
    if 'JOGADOR_ID' not in df_mapa.columns:
        return
    ids = df_mapa['JOGADOR_ID'].dropna().unique().tolist()
    if not ids:
        return
    cores_hex = mapa_cores_hex_por_id(ids)
    st.caption('**Legenda**')
    cols = st.columns(min(len(ids), 5))
    for i, id_ in enumerate(sorted(ids)):
        nome = (
            df_mapa[df_mapa['JOGADOR_ID'] == id_]['JOGADOR'].iloc[0]
            if 'JOGADOR' in df_mapa.columns
            else str(id_)
        )
        hex_cor = cores_hex[id_]
        cols[i % 5].markdown(
            f'<span style="color:{hex_cor};font-size:1.3em">■</span> **{nome}**<br>'
            f'<small>ID: {id_}</small>',
            unsafe_allow_html=True,
        )


def exibir_alertas(alertas: dict, tipo: str) -> None:
    '''Exibe seção de alertas com mensagens coloridas e tabelas de detalhes.'''
    if tipo == 'ip':
        df_paises = alertas.get('multiplos_paises', pd.DataFrame())
        df_ips    = alertas.get('ips_compartilhados', pd.DataFrame())
        if df_paises.empty and df_ips.empty:
            st.success('✅ Nenhuma inconsistência detectada.')
            return
        if not df_paises.empty:
            st.error(f'🔴 **{len(df_paises)} jogador(es)** com registros em múltiplos países — Possível uso de VPN!')
            d = df_paises.copy()
            d['PAÍSES'] = d['PAÍSES'].apply(', '.join)
            st.dataframe(d, use_container_width=True, hide_index=True)
        if not df_ips.empty:
            st.error(f'🔴 **{len(df_ips)} IP(s)** compartilhado(s) entre jogadores distintos')
            d = df_ips.copy()
            d['JOGADORES'] = d['JOGADORES'].apply(', '.join)
            st.dataframe(d, use_container_width=True, hide_index=True)
    else:
        df_cidades = alertas.get('multiplas_cidades', pd.DataFrame())
        df_disp    = alertas.get('dispositivos_compartilhados', pd.DataFrame())
        if df_cidades.empty and df_disp.empty:
            st.success('✅ Nenhuma inconsistência detectada.')
            return
        if not df_cidades.empty:
            st.error(f'🔴 **{len(df_cidades)} jogador(es)** com registros em múltiplas cidades')
            d = df_cidades.copy()
            d['CIDADES'] = d['CIDADES'].apply(', '.join)
            st.dataframe(d, use_container_width=True, hide_index=True)
        if not df_disp.empty:
            st.error(f'🔴 **{len(df_disp)} dispositivo(s)** compartilhado(s) entre jogadores distintos')
            d = df_disp.copy()
            d['JOGADORES'] = d['JOGADORES'].apply(', '.join)
            st.dataframe(d, use_container_width=True, hide_index=True)


# -----------------------------------------------------
# ABAS
# -----------------------------------------------------
tab_manual, tab_planilha = st.tabs(['🔍 Consulta Manual', '📂 Importar Planilhas'])


# =====================================================
# ABA MANUAL
# =====================================================
with tab_manual:
    tipo_manual = st.radio(
        'Tipo de consulta',
        ['IP', 'GPS'],
        horizontal=True,
        key='radio_manual',
    )

    if tipo_manual == 'IP':
        ips_texto = st.text_area(
            'Endereços IP (um por linha)',
            placeholder='8.8.8.8\n1.1.1.1\n200.100.50.25',
            height=120,
        )
        if st.button('Consultar', key='btn_consultar_ip', width='stretch'):
            ips = [ip.strip() for ip in ips_texto.splitlines() if ip.strip()]
            if not ips:
                st.warning('Informe ao menos um endereço IP.')
            else:
                with st.spinner(f'Consultando ip-api.com para {len(ips)} IP(s)...'):
                    df_single = pd.DataFrame({
                        'IP':        ips,
                        'JOGADOR':   ips,
                        'JOGADOR_ID': list(range(len(ips))),
                    })
                    resultado = buscar_localizacao_ips(df_single, st.session_state.cache_ips)
                st.session_state.df_manual_resultado   = resultado
                st.session_state.tipo_manual_resultado = 'IP'

    else:  # GPS
        st.caption('Insira as coordenadas, uma por linha no formato: **latitude,longitude**')
        coords_texto = st.text_area(
            'Coordenadas',
            placeholder='-23.5505,-46.6333\n-15.7801,-47.9292',
            height=120,
        )
        if st.button('Consultar', key='btn_consultar_gps'):
            linhas_validas = []
            for linha in coords_texto.splitlines():
                linha = linha.strip()
                if not linha:
                    continue
                try:
                    lat, lon = map(float, linha.split(','))
                    linhas_validas.append({
                        'LATITUDE':   lat,
                        'LONGITUDE':  lon,
                        'JOGADOR':    linha,
                        'JOGADOR_ID': len(linhas_validas),
                    })
                except ValueError:
                    st.warning(f'Linha ignorada (formato inválido): `{linha}`')

            if not linhas_validas:
                st.warning('Nenhuma coordenada válida encontrada.')
            else:
                df_single = pd.DataFrame(linhas_validas)
                with st.spinner(f'Consultando Nominatim para {len(df_single)} ponto(s)...'):
                    resultado = buscar_geocodificacao_reversa(df_single, st.session_state.cache_geo)
                st.session_state.df_manual_resultado   = resultado
                st.session_state.tipo_manual_resultado = 'GPS'

    # Exibição persistida em session_state (sobrevive a reruns)
    if (st.session_state.df_manual_resultado is not None
            and st.session_state.tipo_manual_resultado == tipo_manual):
        df_man = st.session_state.df_manual_resultado
        if tipo_manual == 'IP':
            cols_exibir = [c for c in ('IP', 'CIDADE', 'ESTADO', 'PAIS') if c in df_man.columns]
        else:
            cols_exibir = [c for c in ('LATITUDE', 'LONGITUDE', 'CIDADE', 'ESTADO', 'PAIS')
                           if c in df_man.columns]
        st.dataframe(df_man[cols_exibir], use_container_width=True, hide_index=True)
        _exibir_mapa_folium(df_man, f'manual_{tipo_manual.lower()}')


# =====================================================
# ABA PLANILHAS
# =====================================================
with tab_planilha:
    tipo_arquivo = st.radio(
        'Tipo de arquivo',
        ['IP', 'GPS'],
        horizontal=True,
        key='radio_planilha',
    )

    col_upload, col_limpa = st.columns([4, 1], vertical_alignment='bottom')
    with col_upload:
        arquivos = st.file_uploader(
            'Selecione os arquivos (um por jogador)',
            type=['xlsx'],
            accept_multiple_files=True,
            key='uploader_planilha',
        )
    with col_limpa:
        if st.button('🗑️ Limpar dados', key='geo-limpa-cache'):
            for chave in _CHAVES_CACHE:
                st.session_state[chave] = {}
            for chave in _CHAVES_DADOS + _CHAVES_MANUAL:
                st.session_state[chave] = None
            st.rerun()

    if arquivos:
        st.caption(f'{len(arquivos)} arquivo(s) selecionado(s)')

    # col_pdf é preenchida APÓS o bloco de processamento para que os dados
    # do session_state já estejam atualizados quando o botão for renderizado.
    col_proc, col_pdf = st.columns([1, 1])
    with col_proc:
        processar = st.button('⚙️ Processar', key='btn_processar', disabled=not arquivos,
                              use_container_width=True)

    if processar and arquivos:
        with st.spinner('Carregando e corrigindo arquivos...'):
            df_bruto = carregar_xlsx(arquivos)

        # Detecção de tipo e alerta de mismatch
        tipo_detectado = _detectar_tipo_arquivo(df_bruto)
        if tipo_detectado and tipo_detectado != tipo_arquivo:
            st.error(
                f'⚠️ O arquivo parece ser do tipo **{tipo_detectado}**, '
                f'mas o seletor está em **{tipo_arquivo}**. '
                f'Corrija a seleção antes de processar.'
            )
            st.stop()

        try:
            if tipo_arquivo == 'IP':
                df_prep = preparar_df_ip(df_bruto)
                with st.spinner('Buscando geolocalização dos IPs...'):
                    df_resultado = buscar_localizacao_ips(df_prep, st.session_state.cache_ips)
                alertas = detectar_alertas_ip(df_resultado)
                st.session_state.df_ip_resultado  = df_resultado
                st.session_state.df_gps_resultado = None
                st.session_state.alertas_ip       = alertas
                st.session_state.alertas_gps      = None
                st.success(f'✅ {len(df_resultado)} registro(s) de IP processado(s).')
            else:
                df_prep = preparar_df_gps(df_bruto)
                with st.spinner('Buscando geocodificação reversa...'):
                    df_resultado = buscar_geocodificacao_reversa(df_prep, st.session_state.cache_geo)
                alertas = detectar_alertas_gps(df_resultado)
                st.session_state.df_gps_resultado = df_resultado
                st.session_state.df_ip_resultado  = None
                st.session_state.alertas_gps      = alertas
                st.session_state.alertas_ip       = None
                st.success(f'✅ {len(df_resultado)} registro(s) de GPS processado(s).')

            # Novo processamento invalida PDF anterior
            st.session_state.pdf_bytes = None
            st.session_state.pdf_nome  = None

        except ValueError as erro_validacao:
            st.error(f'❌ {erro_validacao}')
            st.stop()

    # ── Botão PDF — estado-máquina: gerar → rerun → baixar ──────────────
    # Leitura APÓS o bloco de processamento: session_state já atualizado.
    _df_ip_gen  = st.session_state.df_ip_resultado
    _df_gps_gen = st.session_state.df_gps_resultado
    _df_gen     = _df_ip_gen if _df_ip_gen is not None else _df_gps_gen
    _pdf_bytes  = st.session_state.get('pdf_bytes')
    _pdf_nome   = st.session_state.get('pdf_nome') or 'geolocalizacao.pdf'

    with col_pdf:
        if _pdf_bytes is not None:
            # PDF pronto → download direto (um clique)
            st.download_button(
                label='📥 Baixar PDF',
                data=_pdf_bytes,
                file_name=_pdf_nome,
                mime='application/pdf',
                key='btn_baixar_pdf',
                use_container_width=True,
            )
            st.success('✅ Arquivo PDF pronto para download. Cliquei novamente para baixar.')
        else:
            # PDF ainda não gerado → botão de geração
            if st.button('📄 Gerar PDF', key='btn_gerar_pdf',
                         disabled=_df_gen is None, use_container_width=True):
                _ids_lista = sorted(_df_gen['JOGADOR_ID'].dropna().unique().tolist())
                _ids_str   = '_'.join(str(i) for i in _ids_lista)
                _tipo_pdf  = 'ip' if _df_ip_gen is not None else 'gps'
                _titulo    = (f'Geolocalização {_tipo_pdf.upper()} — '
                              f'Jogadores: {", ".join(str(i) for i in _ids_lista)}')
                _nome      = f'geolocalizacao_{_tipo_pdf}_{_ids_str}.pdf'
                with st.spinner('Gerando PDF...'):
                    st.session_state.pdf_bytes = gerar_pdf_geo(
                        titulo=_titulo,
                        df_ip=_df_ip_gen,
                        df_gps=_df_gps_gen,
                        alertas_ip=st.session_state.alertas_ip,
                        alertas_gps=st.session_state.alertas_gps,
                    )
                st.session_state.pdf_nome = _nome
                st.rerun()  # re-renderiza com st.download_button ativo

    # ── Resultados (persistidos no session_state) ──
    df_ip_res      = st.session_state.df_ip_resultado
    df_gps_res     = st.session_state.df_gps_resultado
    df_exibir      = df_ip_res if df_ip_res is not None else df_gps_res
    alertas_exibir = st.session_state.alertas_ip if df_ip_res is not None else st.session_state.alertas_gps
    tipo_resultado = 'ip' if df_ip_res is not None else 'gps'

    if df_exibir is not None:
        st.markdown('---')

        # Resumo sem duplicatas (fora de expander, antes da tabela completa)
        df_resumo = resumo_ip(df_exibir) if tipo_resultado == 'ip' else resumo_gps(df_exibir)
        st.subheader('📊 Resumo')
        st.dataframe(df_resumo, use_container_width=True, hide_index=True)

        # Tabela completa
        with st.expander('📋 Tabela completa', expanded=False):
            st.dataframe(df_exibir, use_container_width=True, hide_index=True)

        # Mapa
        with st.expander('🗺️ Mapa', expanded=True):
            _exibir_mapa_folium(df_exibir, 'planilha')

        # Alertas
        tem_alertas = any(not v.empty for v in alertas_exibir.values()) if alertas_exibir else False
        with st.expander(
            '⚠️ Alertas detectados' if tem_alertas else '✅ Alertas',
            expanded=tem_alertas,
        ):
            if alertas_exibir:
                exibir_alertas(alertas_exibir, tipo_resultado)

