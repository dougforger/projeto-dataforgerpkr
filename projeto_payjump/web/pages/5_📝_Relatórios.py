import pandas as pd
import streamlit as st

from utils.analise_geo import (
    _inferir_id_investigacao,
    _inferir_titulo_investigacao,
    detectar_alertas_dispositivos,
    detectar_alertas_gps,
    detectar_alertas_ip,
    gerar_pdf_dispositivos,
    gerar_pdf_geo,
    preparar_df_dispositivos,
    preparar_df_gps,
    preparar_df_ip,
    resumo_gps,
    resumo_ip,
)
from utils.arquivo_utils import carregar_xlsx, corrigir_xlsx_memoria
from utils.geolocation import buscar_geocodificacao_reversa, buscar_localizacao_ips
from utils.mapa_utils import exibir_mapa_folium

st.set_page_config(page_title='Relatórios', page_icon='📝', layout='wide')
st.title('📝 Relatórios')
st.markdown('---')

# -----------------------------------------------------
# SESSION STATE
# -----------------------------------------------------
_CHAVES_CACHE  = ('cache_ips', 'cache_geo')
_CHAVES_DADOS  = ('df_ip_resultado', 'df_gps_resultado', 'alertas_ip', 'alertas_gps',
                  'pdf_bytes', 'pdf_nome')
_CHAVES_MANUAL = ('df_manual_resultado', 'tipo_manual_resultado')
_CHAVES_DISP   = ('lista_dispositivos', 'alertas_dispositivos',
                  'pdf_bytes_disp', 'pdf_nome_disp')

for chave in _CHAVES_CACHE:
    if chave not in st.session_state:
        st.session_state[chave] = {}
for chave in _CHAVES_DADOS + _CHAVES_MANUAL + _CHAVES_DISP:
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


def _detectar_tipo_dispositivo(df: pd.DataFrame) -> bool:
    '''Retorna True se o DataFrame parecer um arquivo "Same Data With Players".'''
    return 'Machine Code' in df.columns and 'Players' in df.columns


def exibir_alertas_dispositivos(alertas: dict) -> None:
    '''Exibe contas que aparecem nos dispositivos de mais de um arquivo investigado.'''
    df_cruzadas = alertas.get('contas_cruzadas', pd.DataFrame())
    if df_cruzadas.empty:
        st.success('✅ Nenhuma conta em comum entre os arquivos investigados.')
        return
    st.error(
        f'🔴 **{len(df_cruzadas)} conta(s)** aparecem nos dispositivos de múltiplos arquivos'
    )
    st.dataframe(
        df_cruzadas.rename(columns={'CONTA': 'Conta', 'ARQUIVOS': 'Aparece nos arquivos'}),
        width='stretch', hide_index=True,
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
            st.dataframe(d, width='stretch', hide_index=True)
        if not df_ips.empty:
            st.error(f'🔴 **{len(df_ips)} IP(s)** compartilhado(s) entre jogadores distintos')
            d = df_ips.copy()
            d['JOGADORES'] = d['JOGADORES'].apply(', '.join)
            st.dataframe(d, width='stretch', hide_index=True)
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
            st.dataframe(d, width='stretch', hide_index=True)
        if not df_disp.empty:
            st.error(f'🔴 **{len(df_disp)} dispositivo(s)** compartilhado(s) entre jogadores distintos')
            d = df_disp.copy()
            d['JOGADORES'] = d['JOGADORES'].apply(', '.join)
            st.dataframe(d, width='stretch', hide_index=True)


# -----------------------------------------------------
# ABAS
# -----------------------------------------------------
tab_manual, tab_planilha, tab_dispositivos = st.tabs(
    ['🔍 IP/GPS - Consulta Manual', '📂 IP/GPS - Importar Planilhas', '📱 Dispositivos']
)


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
        st.dataframe(df_man[cols_exibir], width='stretch', hide_index=True)
        exibir_mapa_folium(df_man, f'manual_{tipo_manual.lower()}')


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
                              width='stretch')

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
                width='stretch',
            )
            st.success('✅ Arquivo PDF pronto para download. Cliquei novamente para baixar.')
        else:
            # PDF ainda não gerado → botão de geração
            if st.button('📄 Gerar PDF', key='btn_gerar_pdf',
                         disabled=_df_gen is None, width='stretch'):
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
        st.dataframe(df_resumo, width='stretch', hide_index=True)

        # Tabela completa
        with st.expander('📋 Tabela completa', expanded=False):
            st.dataframe(df_exibir, width='stretch', hide_index=True)

        # Mapa
        with st.expander('🗺️ Mapa', expanded=True):
            exibir_mapa_folium(df_exibir, 'planilha')

        # Alertas
        tem_alertas = any(not v.empty for v in alertas_exibir.values()) if alertas_exibir else False
        with st.expander(
            '⚠️ Alertas detectados' if tem_alertas else '✅ Alertas',
            expanded=tem_alertas,
        ):
            if alertas_exibir:
                exibir_alertas(alertas_exibir, tipo_resultado)


# =====================================================
# ABA DISPOSITIVOS
# =====================================================
with tab_dispositivos:
    st.caption(
        'Faça upload dos arquivos **Same Data With Players** exportados do backend. '
        'Aceita múltiplos arquivos — os dados serão combinados automaticamente.'
    )

    col_up_disp, col_limpa_disp = st.columns([4, 1], vertical_alignment='bottom')
    with col_up_disp:
        arquivos_disp = st.file_uploader(
            'Selecione os arquivos de dispositivos',
            type=['xlsx'],
            accept_multiple_files=True,
            key='uploader_dispositivos',
        )
    with col_limpa_disp:
        if st.button('🗑️ Limpar dados', key='disp-limpa-cache'):
            for chave in _CHAVES_DISP:
                st.session_state[chave] = None
            st.rerun()

    if arquivos_disp:
        st.caption(f'{len(arquivos_disp)} arquivo(s) selecionado(s)')

    col_proc_disp, col_pdf_disp = st.columns([1, 1])
    with col_proc_disp:
        processar_disp = st.button(
            '⚙️ Processar', key='btn_processar_disp',
            disabled=not arquivos_disp, width='stretch',
        )

    if processar_disp and arquivos_disp:
        lista_processada = []
        erros_arquivos   = []
        with st.spinner('Carregando e corrigindo arquivos...'):
            for arquivo in arquivos_disp:
                try:
                    import io as _io
                    buf      = corrigir_xlsx_memoria(_io.BytesIO(arquivo.read()))
                    df_bruto = pd.read_excel(buf)
                    if not _detectar_tipo_dispositivo(df_bruto):
                        erros_arquivos.append(
                            f'`{arquivo.name}` não possui as colunas esperadas '
                            f'(Machine Code e Players) — ignorado.'
                        )
                        continue
                    df_proc = preparar_df_dispositivos(df_bruto)
                    lista_processada.append((arquivo.name, df_proc))
                except ValueError as e:
                    erros_arquivos.append(f'`{arquivo.name}`: {e}')

        for msg in erros_arquivos:
            st.warning(f'⚠️ {msg}')

        if lista_processada:
            alertas_disp = detectar_alertas_dispositivos(lista_processada)
            st.session_state.lista_dispositivos  = lista_processada
            st.session_state.alertas_dispositivos = alertas_disp
            st.session_state.pdf_bytes_disp       = None
            st.session_state.pdf_nome_disp        = None
            total_disp = sum(len(df) for _, df in lista_processada)
            st.success(
                f'✅ {len(lista_processada)} arquivo(s) processado(s) — '
                f'{total_disp} dispositivo(s) no total.'
            )
        elif not erros_arquivos:
            st.error('❌ Nenhum arquivo válido encontrado.')

    # Botão PDF — mesmo padrão estado-máquina das outras abas
    _lista_disp     = st.session_state.lista_dispositivos
    _alertas_disp   = st.session_state.alertas_dispositivos
    _pdf_bytes_disp = st.session_state.get('pdf_bytes_disp')
    _pdf_nome_disp  = st.session_state.get('pdf_nome_disp') or 'dispositivos.pdf'

    with col_pdf_disp:
        if _pdf_bytes_disp is not None:
            st.download_button(
                label='📥 Baixar PDF',
                data=_pdf_bytes_disp,
                file_name=_pdf_nome_disp,
                mime='application/pdf',
                key='btn_baixar_pdf_disp',
                width='stretch',
            )
            st.success('✅ Arquivo PDF pronto para download.')
        else:
            if st.button('📄 Gerar PDF', key='btn_gerar_pdf_disp',
                         disabled=not _lista_disp, width='stretch'):
                with st.spinner('Gerando PDF...'):
                    st.session_state.pdf_bytes_disp = gerar_pdf_dispositivos(
                        titulo='Relatório de Dispositivos',
                        lista_nome_df=_lista_disp,
                        alertas=_alertas_disp or {},
                    )
                _ids_pdf = [_inferir_id_investigacao(df) for _, df in _lista_disp]
                _ids_str = '_'.join(i for i in _ids_pdf if i) or 'relatorio'
                st.session_state.pdf_nome_disp = f'dispositivos_{_ids_str}.pdf'
                st.rerun()

    # Resultados — uma tabela por arquivo
    if _lista_disp:
        st.markdown('---')

        _cols_resumo = ('CODIGO_CENSURADO', 'SISTEMA', 'DISPOSITIVO', 'MODELO',
                        'VERSAO_OS', 'SIMULADOR', 'REPETICOES', 'N_CONTAS', 'CONTAS')
        _renomear_resumo = {
            'CODIGO_CENSURADO': 'Código (Censurado)',
            'SISTEMA':          'Sistema',
            'DISPOSITIVO':      'Tipo',
            'MODELO':           'Modelo',
            'VERSAO_OS':        'Versão OS',
            'SIMULADOR':        'Emulador',
            'REPETICOES':       'Repetições',
            'N_CONTAS':         'Nº Contas',
            'CONTAS':           'Contas',
        }

        st.subheader('📊 Dispositivos')
        for i, (_, df_arq) in enumerate(_lista_disp):
            titulo_arq = _inferir_titulo_investigacao(df_arq) or f'Investigação {i + 1}'
            st.markdown(f'**{titulo_arq}**')
            cols_exibir = [c for c in _cols_resumo if c in df_arq.columns]
            st.dataframe(
                df_arq[cols_exibir].rename(columns=_renomear_resumo),
                width='stretch', hide_index=True,
            )

        # Alertas cruzados
        _tem_alertas_disp = (
            _alertas_disp is not None
            and not _alertas_disp.get('contas_cruzadas', pd.DataFrame()).empty
        )
        with st.expander(
            '⚠️ Alertas detectados' if _tem_alertas_disp else '✅ Alertas',
            expanded=_tem_alertas_disp,
        ):
            if _alertas_disp:
                exibir_alertas_dispositivos(_alertas_disp)

