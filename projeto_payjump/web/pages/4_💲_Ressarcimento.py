# projeto_payjump/web/pages/4_💲_Ressarcimento.py
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date, datetime

from utils.calculos import (
    calcular_saldo_por_fraudador,
    distribuir_ressarcimento,
    criar_excel_ressarcimento,
    processar_planilhas_backend,
    gerar_pdf_pontual,
)
from utils.arquivo_utils import carregar_xlsx
from utils.clubes_db import carregar_clubes
from utils.ligas_db import carregar_ligas

# ===== IMPORTS DO BANCO DE DADOS =====
from utils.database import (
    # Fraudadores
    get_ids_fraudadores,
    get_fraudadores_completo,
    adicionar_fraudadores_lote,

    # Histórico
    salvar_ressarcimentos_lote,
    get_historico_completo,
    get_estatisticas_historico,

    # Acumulados
    get_acumulados,
    atualizar_acumulados,
    get_estatisticas_acumulados
)

st.set_page_config(
    page_title='Ressarcimento',
    page_icon='💲',
    layout='wide'
)

st.title('💲 Ressarcimento')
st.markdown('Cálculo de ressarcimentos para mãos influenciadas por contas suspeitas')
st.markdown('---')

tab_lote, tab_pontual = st.tabs(['📦 Ressarcimento por Lote', '🎯 Ressarcimento Pontual'])

# ============================================================
# ABA 1 — RESSARCIMENTO POR LOTE (conteúdo original)
# ============================================================
with tab_lote:

    # ===== UPLOAD DO ARQUIVO =====
    st.subheader('📂 Upload do Arquivo Exportado')
    uploaded_file = st.file_uploader(
        'Selecione o arquivo CSV exportado do Snowflake',
        type=['csv'],
        help='Arquivo gerado pela query de análise de fraudadores do Snowflake.'
    )

    if uploaded_file is not None:
        # Carregar o CSV
        df = pd.read_csv(uploaded_file)

        # Validação das colunas necessárias
        # colunas_necessarias = ['PLAYER_ID', 'PLAYER_NAME', 'CLUB_ID', 'UNION_ID', 'HAND_ID', 'GANHOS_REAIS', 'IS_FRAUDADOR']
        colunas_necessarias = ['JOGADOR_ID','JOGADOR_NOME','CLUBE_ID','LIGA_ID','MESA_ID','MAO_ID','GANHOS_REAIS','FRAUDADOR']
        colunas_faltando = [col for col in colunas_necessarias if col not in df.columns]

        if colunas_faltando:
            st.error(f'❌ Colunas faltando no arquivo: {", ".join(colunas_faltando)}')
            st.info(f'ℹ️ Colunas esperadas: {", ".join(colunas_necessarias)}')
            st.stop()

        st.success(f'✅ Arquivo carregado com sucesso! {len(df)} linhas encontradas.')

        # Mostrar prévia dos dados
        with st.expander('👀 Prévia dos Dados'):
            st.dataframe(df.head(10))

        # ===== UPLOAD DE ACUMULADOS ANTERIORES =====
        st.markdown('---')
        st.subheader('🗄️ Dados do Banco')

        col_upload_1, col_upload_2 = st.columns([1, 1])
        with col_upload_1:
            st.markdown('#### 🚫 Fraudadores Conhecidos')

            # Carregar automaticamente do banco
            ids_fraudadores = get_ids_fraudadores()

            if len(ids_fraudadores) > 0:
                st.success(f'✅ {len(ids_fraudadores)} fraudador(es) carregado(s) automaticamente')

                # Mostrar lista de fraudadores
                with st.expander('👀 Ver a Lista de Fraudadores'):
                    df_fraudadores_lista = pd.DataFrame(get_fraudadores_completo())
                    st.dataframe(
                        df_fraudadores_lista,
                        hide_index=True,
                        width='stretch',
                        column_config={
                            'jogador_id': 'ID Jogador',
                            'jogador_nome': 'Nome Jogador',
                            'clube_id': 'ID Clube',
                            'clube_nome': 'Nome Clube',
                            'data_identificacao': 'Data Identificação',
                            'protocolo': 'Protocolo',
                            'valor_total_retido': st.column_config.NumberColumn(
                                'Valor Retido (R$)',
                                format='%.2f'
                            )
                        }
                    )
            else:
                st.info('ℹ️ Nenhum fraudador no banco. Todos os jogadores serão elegíveis para ressarcimento.')

        with col_upload_2:
            st.markdown('#### ⏳ Acumulados Pendentes')

            # Carregar automaticamente do banco
            acumulados_anteriores = get_acumulados()
            df_acumulados_antigos = pd.DataFrame(acumulados_anteriores)

            if len(df_acumulados_antigos) > 0:
                # Estatísticas rápidas
                stats_acumulados = get_estatisticas_acumulados()
                st.success(f'✅ {len(df_acumulados_antigos)} acumulado(s) carregado(s) — Total: R$ {stats_acumulados["valor_total_acumulado"]:.2f}')

                # Mostrar lista de acumulados
                with st.expander('👀 Ver a Lista de Acumulados'):
                    st.dataframe(
                        df_acumulados_antigos,
                        hide_index=True,
                        width='stretch',
                        column_config={
                            'jogador_id': 'ID Jogador',
                            'jogador_nome': 'Nome Jogador',
                            'clube_id': 'ID Clube',
                            'clube_nome': 'Nome Clube',
                            'ressarcimento_acumulado': st.column_config.NumberColumn(
                                'Acumulado (R$)',
                                format='%.2f'
                            ),
                            'data_ultima_atualizacao': 'Última Atualização'
                        }
                    )
            else:
                # DataFrame vazio para não quebrar o código
                df_acumulados_antigos = pd.DataFrame(columns=[
                    'jogador_id', 'jogador_nome', 'clube_id', 'clube_nome', 'ressarcimento_acumulado', 'data_ultima_atualizacao'
                ])
                st.info('ℹ️ Nenhum acumulado pendente.')

        st.markdown('---')

        # ===== CARREGAR INFORMAÇÕES DE CLUBES E LIGAS ======
        df_clubes = carregar_clubes()
        df_ligas = carregar_ligas()

        # ===== IDENTIFICAÇÃO DOS FRAUDADORES =====
        st.subheader('⚙️ Configuração dos Retidos por Fraudador')

        # Filtrar apenas os fraudadores
        df_fraudadores = df[df['FRAUDADOR'] == True].groupby('JOGADOR_ID').agg({
            'JOGADOR_NOME': 'first',
            'CLUBE_ID': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0],
            'LIGA_ID': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0]
        }).reset_index()

        # Merge com os clubes
        df_fraudadores = df_fraudadores.merge(
            df_clubes[['clube_id', 'clube_nome']],
            left_on='CLUBE_ID',
            right_on='clube_id',
            how='left'
        )

        # Merge com as ligas
        df_fraudadores = df_fraudadores.merge(
            df_ligas[['liga_id', 'liga_nome', 'moeda', 'handicap', 'taxa-liga']],
            left_on='LIGA_ID',
            right_on='liga_id',
            how='left'
        )

        # Limpar e renomear colunas
        df_fraudadores = df_fraudadores[[
            'JOGADOR_ID', 'JOGADOR_NOME', 'clube_id', 'clube_nome', 'liga_id', 'liga_nome', 'moeda', 'handicap'
        ]]
        df_fraudadores.columns = [
            'fraudador_id', 'fraudador_nome', 'clube_id', 'nome_clube', 'liga_id', 'nome_liga', 'moeda', 'handicap'
        ]
        df_fraudadores = df_fraudadores.sort_values('fraudador_id')

        # Adicionar coluna editável para valor retido
        df_fraudadores['valor_retido'] = 0.0
        df_fraudadores['rake_retido'] = 0.0

        # Verificar se há fraudadores em múltiplas ligas
        fraudadores_multiplas_ligas = df[df['FRAUDADOR'] == True].groupby('JOGADOR_ID')['LIGA_ID'].nunique()
        fraudadores_multiplas_ligas = fraudadores_multiplas_ligas[fraudadores_multiplas_ligas > 1]

        if len(fraudadores_multiplas_ligas) > 0:
            st.warning(f'⚠️ {len(fraudadores_multiplas_ligas)} fraudador(es) jogaram em mais de uma liga. Utilizando a liga mais frequente.')

        st.info(f'🚫 Encontrados **{len(df_fraudadores)}** fraudadores no arquivo. Insira o valor retido (em moeda local) para cada um:')

        # ===== TABELA UNIFICADA =====
        # Invalidar session state se o arquivo mudou
        file_id = uploaded_file.name + str(uploaded_file.size)
        if st.session_state.get('editor_file_id') != file_id:
            df_fraudadores['valor_retido'] = 0.0
            df_fraudadores['rake_retido'] = 0.0
            df_fraudadores['valor_reais'] = 0.0
            df_fraudadores['rake_reais'] = 0.0
            st.session_state['editor_df'] = df_fraudadores.copy()
            st.session_state['editor_file_id'] = file_id

        editor_base = st.session_state['editor_df']

        placeholder_metricas = st.empty()

        fraudadores_editados = st.data_editor(
            editor_base,
            column_order=['fraudador_id', 'fraudador_nome', 'nome_clube', 'nome_liga', 'moeda',
                          'valor_retido', 'rake_retido', 'valor_reais', 'rake_reais'],
            disabled=['fraudador_id', 'fraudador_nome', 'nome_clube', 'nome_liga', 'moeda',
                      'valor_reais', 'rake_reais'],
            hide_index=True,
            width='stretch',
            column_config={
                'fraudador_id': st.column_config.NumberColumn('ID', width='small'),
                'fraudador_nome': st.column_config.TextColumn('Nome', width='small'),
                'nome_clube': st.column_config.TextColumn('Clube', width='small'),
                'nome_liga': st.column_config.TextColumn('Liga', width='small'),
                'moeda': st.column_config.TextColumn('Moeda', width='small'),
                'valor_retido': st.column_config.NumberColumn(
                    'Retido (Local)',
                    help='Valor retido do fraudador na moeda local referente à liga a qual o clube pertence.',
                    min_value=0.0, format='%.2f', width='medium', required=True
                ),
                'rake_retido': st.column_config.NumberColumn(
                    'Rake (Local)',
                    help='Valor do rake gerado pelo fraudador na moeda local referente à liga a qual o clube pertence.',
                    min_value=0.0, format='%.2f', width='medium', required=True
                ),
                'valor_reais': st.column_config.NumberColumn('Retido (R$)', format='%.2f', width='medium'),
                'rake_reais': st.column_config.NumberColumn('Rake (R$)', format='%.2f', width='medium'),
            }
        )

        # ===== NORMALIZAR SEPARADORES DECIMAIS =====
        for col in ['valor_retido', 'rake_retido']:
            if col in fraudadores_editados.columns:
                fraudadores_editados[col] = fraudadores_editados[col].apply(
                    lambda x: float(str(x).replace(',', '.')) if pd.notna(x) else 0.0
                )

        # ===== CONVERTER OS VALORES PARA REAL =====
        fraudadores_editados['valor_reais'] = (fraudadores_editados['valor_retido'].astype(float) / fraudadores_editados['handicap'].astype(float)) * 5
        fraudadores_editados['rake_reais'] = (fraudadores_editados['rake_retido'].astype(float) / fraudadores_editados['handicap'].astype(float)) * 5

        # ===== MÉTRICAS ACIMA DA TABELA =====
        total_retido = fraudadores_editados['valor_reais'].sum() + fraudadores_editados['rake_reais'].sum()
        fraudadores_com_valor = len(fraudadores_editados[fraudadores_editados['valor_retido'] > 0])
        with placeholder_metricas.container():
            col_m1, col_m2 = st.columns(2)
            col_m1.metric('Total Disponível (R$)', f'R$ {total_retido:,.2f}')
            col_m2.metric('Fraudadores com Valor', f'{fraudadores_com_valor} / {len(fraudadores_editados)}')

        # ===== ATUALIZAR SESSION STATE E RERUN SE REAIS MUDARAM =====
        reais_changed = not (
            fraudadores_editados['valor_reais'].equals(editor_base['valor_reais']) and
            fraudadores_editados['rake_reais'].equals(editor_base['rake_reais'])
        )
        st.session_state['editor_df'] = fraudadores_editados.copy()
        if reais_changed:
            st.rerun()

        st.markdown('---')

        # ===== CONFIGURAÇÃO DE VALOR MÍNIMO =====

        st.subheader('🔄 Calcular Ressarcimentos')
        col_config_1, col_config_2 = st.columns(2, vertical_alignment='bottom')
        with col_config_1:
            valor_minimo = st.number_input(
                'Valor Mínimo para Ressarcimento (R$)',
                min_value=0.0,
                value=10.00,
                step=5.0,
                format='%.2f',
                help='Ressarcimentos abaixo deste valor serão acumulados para futuros ressarcimentos'
            )
            st.info(f'ℹ️ Jogadores com ressarcimento abaixo de R$ {valor_minimo} serão guardados para ressarcimentos futuros.')
        with col_config_2:
            calcular = st.button(
                '🔄 Calcular Ressarcimentos',
                type='primary',
                width='stretch'
            )
            # Validar se todos os valores foram preenchidos
            valores_zerados = fraudadores_editados[fraudadores_editados['valor_retido'] == 0.0]
            if len(valores_zerados) > 0:
                st.warning(f'⚠️ {len(valores_zerados)} fraudador(es) ainda com valor zero. Confira o valor antes de prosseguir.')
            else:
                st.success('✅ Todos os fraudadores com valor preenchido.')

        # Lista separadas para ressarcimentos imediatos e futuros
        ressarcimentos_imediatos = []
        ressarcimentos_futuros = []

        # Dicionário para armazenar resultados de cada fraudador
        resultados_por_fraudador = {}

        if calcular:
            # Informar sobre fraudadores (se houver)
            if len(ids_fraudadores) > 0:
                st.info(f'ℹ️ {len(ids_fraudadores)} fraudador(es) conhecido(s) serão automaticamente excluídos dos cálculos. O valor será redistribuído entre vítimas legítimas.')
            with st.spinner('Processando ressarcimentos...'):
                st.markdown('---')
                st.subheader('📊 Resultados dos Ressarcimentos')

                # Barra de progresso
                progress_bar = st.progress(0)
                status_text = st.empty()

                # Lista ÚNICA para TODOS os ressarcimentos (antes de consolidar)
                todos_ressarcimentos_brutos = []

                # Processar cada fraudador
                for idx, fraudador in fraudadores_editados.iterrows():
                    fraudador_id = fraudador['fraudador_id']
                    fraudador_nome = fraudador['fraudador_nome']
                    valor_disponivel = fraudador['valor_reais'] + fraudador['rake_reais']

                    # Atualizar progresso
                    progress = (idx + 1) / len(fraudadores_editados)
                    progress_bar.progress(progress)
                    status_text.text(f'Processando Fraudador {fraudador_nome} ({fraudador_id})...')

                    # Se não tiver valor retido, pular
                    if valor_disponivel <= 0:
                        resultados_por_fraudador[fraudador_id] = {
                            'fraudador_nome': fraudador_nome,
                            'valor_disponivel': 0,
                            'vitimas': pd.DataFrame(),
                            'total_ressarcido': 0,
                            'mensagem': 'Fraudador sem valor retido'
                        }
                        continue

                    # Calcular saldos das vítimas
                    vitimas = calcular_saldo_por_fraudador(df, fraudador_id, df_clubes, ids_fraudadores)

                    # Se não há vítimas, pular
                    if len(vitimas) == 0:
                        resultados_por_fraudador[fraudador_id] = {
                            'fraudador_nome': fraudador_nome,
                            'valor_disponivel': valor_disponivel,
                            'vitimas': pd.DataFrame(),
                            'total_ressarcido': 0,
                            'mensagem': 'Nenhuma vítima identificada'
                        }
                        continue

                    # Distribuir ressarcimento
                    vitimas = distribuir_ressarcimento(vitimas, valor_disponivel)

                    # Separar ressarcimentos imediatos e futuros
                    vitimas['status'] = vitimas['ressarcimento'].apply(
                        lambda x: 'Imediato' if x >= valor_minimo else 'Futuro'
                    )

                    # Armazenar resultado
                    total_ressarcido_imediato = vitimas[vitimas['status'] == 'Imediato']['ressarcimento'].sum()
                    total_ressarcido_futuro = vitimas[vitimas['status'] == 'Futuro']['ressarcimento'].sum()
                    total_ressarcido = vitimas['ressarcimento'].sum()

                    resultados_por_fraudador[fraudador_id] = {
                        'fraudador_nome': fraudador_nome,
                        'valor_disponivel': valor_disponivel,
                        'vitimas': vitimas,
                        'total_ressarcido': total_ressarcido,
                        'total_imediato': vitimas[vitimas['status'] == 'Imediato']['ressarcimento'].sum(),
                        'total_futuro': vitimas[vitimas['status'] == 'Futuro']['ressarcimento'].sum(),
                        'mensagem': 'Processado com sucesso'
                    }

                    # Adiciona à lista BRUTA (sem consolidar ainda)
                    for _, vitima in vitimas.iterrows():
                        todos_ressarcimentos_brutos.append({
                            'jogador_id': int(vitima['jogador_id']),
                            'jogador_nome': vitima['jogador_nome'],
                            'clube_id': int(vitima['clube_id']),
                            'clube_nome': vitima['clube_nome'],
                            'ressarcimento': vitima['ressarcimento']
                        })

                    # Limpar progresso
                    progress_bar.empty()
                    status_text.empty()

                # ===== CONSOLIDAÇÃO: AGRUPAR POR JOGADOR_ID + CLUBE_ID =====
                if len(todos_ressarcimentos_brutos) > 0:
                    df_brutos = pd.DataFrame(todos_ressarcimentos_brutos)

                    # Agrupar por jogador_id + clube_id (somando ressarcimentos)
                    df_consolidado = df_brutos.groupby(['jogador_id', 'clube_id']).agg({
                        'jogador_nome': 'first',
                        'clube_nome': 'first',
                        'ressarcimento': 'sum'
                    }).reset_index()

                    df_consolidado.rename(columns={'ressarcimento': 'ressarcimento_novo'}, inplace=True)

                    # ===== ADICIONAR ACUMULADOS ANTERIORES =====
                    df_consolidado['acumulado_anterior'] = 0.0

                    if len(df_acumulados_antigos) > 0:
                        # Merge com acumulados anteriores
                        df_consolidado = df_consolidado.merge(
                            df_acumulados_antigos[['jogador_id', 'clube_id', 'ressarcimento_acumulado']],
                            on=['jogador_id', 'clube_id'],
                            how='left'
                        )
                        # Preencher NaN com 0
                        df_consolidado['ressarcimento_acumulado'] = df_consolidado['ressarcimento_acumulado'].fillna(0.0)
                        df_consolidado['acumulado_anterior'] = df_consolidado['ressarcimento_acumulado']
                        df_consolidado.drop(columns=['ressarcimento_acumulado'], inplace=True)

                    # Calcular total (novo + acumulado)
                    df_consolidado['ressarcimento_total'] = (
                        df_consolidado['ressarcimento_novo'] + df_consolidado['acumulado_anterior']
                    )

                    # ===== SEPARAR IMEDIATOS E FUTUROS =====

                    df_imediatos = df_consolidado[df_consolidado['ressarcimento_total'] >= valor_minimo].copy()
                    df_futuros = df_consolidado[df_consolidado['ressarcimento_total'] < valor_minimo].copy()

                    # Converter para lista de dicionários
                    ressarcimentos_imediatos = df_imediatos.to_dict('records')
                    ressarcimentos_futuros = df_futuros.to_dict('records')

                else:
                    ressarcimentos_imediatos = []
                    ressarcimentos_futuros = []

                # ===== SALVAR RESULTADOS NO SESSION STATE =====
                st.session_state['resultados_calculados'] = True
                st.session_state['resultados_por_fraudador'] = resultados_por_fraudador
                st.session_state['ressarcimentos_imediatos'] = ressarcimentos_imediatos
                st.session_state['ressarcimentos_futuros'] = ressarcimentos_futuros
                st.session_state['fraudadores_editados'] = fraudadores_editados
                st.session_state['valor_minimo'] = valor_minimo
                st.session_state['todos_ressarcimentos_brutos'] = todos_ressarcimentos_brutos

            st.success('✅ Processamento concluído!')

        if st.session_state.get('resultados_calculados', False):
            # Carregar resultados do session state
            resultados_por_fraudador = st.session_state['resultados_por_fraudador']
            ressarcimentos_imediatos = st.session_state['ressarcimentos_imediatos']
            ressarcimentos_futuros = st.session_state['ressarcimentos_futuros']
            fraudadores_editados = st.session_state['fraudadores_editados']
            valor_minimo = st.session_state['valor_minimo']

            # ===== RESUMO GERAL =====
            st.markdown('---')
            st.subheader('📈 Resumo Geral')

            # Calcular métricas gerais
            total_fraudadores_processados = len([r for r in resultados_por_fraudador.values() if r['total_ressarcido'] > 0])
            total_disponivel = sum([r['valor_disponivel'] for r in resultados_por_fraudador.values()])
            total_ressarcido_imediato = sum([r['total_imediato'] for r in resultados_por_fraudador.values()])
            total_ressarcido_futuro = sum([r['total_futuro'] for r in resultados_por_fraudador.values()])
            total_vitimas_imediatas = len(ressarcimentos_imediatos)
            total_vitimas_futuras = len(ressarcimentos_futuros)
            total_ressarcimento = total_ressarcido_imediato + total_ressarcido_futuro
            total_vitimas = total_vitimas_imediatas + total_vitimas_futuras
            # Mostrar métricas
            col_ressarcimento_1, col_ressarcimento_2, col_ressarcimento_3, col_ressarcimento_4 = st.columns(4)
            with col_ressarcimento_1:
                st.metric('Total Disponível', rf'R\$ {total_disponivel:,.2f}')
                st.metric('Fraudadores Processados', f'{total_fraudadores_processados} / {len(fraudadores_editados)}')
            with col_ressarcimento_2:
                st.metric('Ressarcimento Imediato', rf'R\$ {total_ressarcido_imediato:,.2f}')
                st.metric('Vítimas (Imediato)', total_vitimas_imediatas)
            with col_ressarcimento_3:
                st.metric('Ressarcimento Futuro', rf'R\$ {total_ressarcido_futuro:,.2f}')
                st.metric('Vítimas (Futuro)', total_vitimas_futuras)
            with col_ressarcimento_4:
                st.metric('Ressarcimento Total', rf'R\$ {total_ressarcimento:,.2f}')
                st.metric('Vítimas Totais', total_vitimas)

            # Mostrar diferença (se houver)
            diferenca = total_disponivel - total_ressarcido_imediato - total_ressarcido_futuro
            if diferenca > 0:
                st.info(f'ℹ️ Diferença de R$ {diferenca:,.2f} não foi distribuída (tetos individuais aplicados)')
            else:
                st.error('❌ O saldo para ressarcimento é maior que o saldo retido! Verifique novamente.')

            st.markdown('---')

            # ===== TABELAS CONSOLIDADAS =====
            st.subheader('📊 Ressarcimentos Consolidados')

            col_imediato, col_futuro = st.columns(2)
            with col_imediato:
                st.markdown('### 💰 Ressarcimentos Imediatos')

                if len(ressarcimentos_imediatos) > 0:
                    df_imediatos = pd.DataFrame(ressarcimentos_imediatos)
                    df_imediatos = df_imediatos.sort_values('ressarcimento_total', ascending=False)

                    st.dataframe(
                        df_imediatos,
                        hide_index=True,
                        width='stretch',
                        column_config={
                            'jogador_id': st.column_config.NumberColumn('ID Jogador', width='small'),
                            'jogador_nome': st.column_config.TextColumn('Nome Jogador', width='medium'),
                            'clube_id': st.column_config.NumberColumn('ID Clube', width='small'),
                            'clube_nome': st.column_config.TextColumn('Nome Clube', width='medium'),
                            'ressarcimento_novo': st.column_config.NumberColumn(
                                'Novo (R$)',
                                format='R$ %.2f',
                                width='medium',
                                help='Ressarcimento calculado esta semana'
                            ),
                            'acumulado_anterior': st.column_config.NumberColumn(
                                'Acumulado (R$)',
                                format='R$ %.2f',
                                width='medium',
                                help='Valor pendente de semanas anteriores'
                            ),
                            'ressarcimento_total': st.column_config.NumberColumn(
                                'Total (R$)',
                                format='R$ %.2f',
                                width='medium',
                                help='Soma do novo + acumulado'
                            )
                        }
                    )

                    total_imediato = df_imediatos['ressarcimento_total'].sum()
                    st.success(rf'✅ {len(df_imediatos)} ressarcimentos a processar agora (≥ R\$ {valor_minimo:.2f}): R\$ {total_imediato:,.2f}')
                else:
                    st.info('ℹ️ Nenhum ressarcimento imediato')

            with col_futuro:
                st.markdown('### ⏳ Ressarcimentos Futuros')

                if len(ressarcimentos_futuros) > 0:
                    df_futuros = pd.DataFrame(ressarcimentos_futuros)
                    df_futuros = df_futuros.sort_values('ressarcimento_total', ascending=False)

                    st.dataframe(
                        df_futuros,
                        hide_index=True,
                        width='stretch',
                        column_config={
                            'jogador_id': st.column_config.NumberColumn('ID Jogador', width='small'),
                            'jogador_nome': st.column_config.TextColumn('Nome Jogador', width='medium'),
                            'clube_id': st.column_config.NumberColumn('ID Clube', width='small'),
                            'clube_nome': st.column_config.TextColumn('Nome Clube', width='medium'),
                            'ressarcimento_novo': st.column_config.NumberColumn(
                                'Novo (R$)',
                                format='R$ %.2f',
                                width='medium',
                                help='Ressarcimento calculado esta semana'
                            ),
                            'acumulado_anterior': st.column_config.NumberColumn(
                                'Acumulado (R$)',
                                format='R$ %.2f',
                                width='medium',
                                help='Valor pendente de semanas anteriores'
                            ),
                            'ressarcimento_total': st.column_config.NumberColumn(
                                'Total (R$)',
                                format='R$ %.2f',
                                width='medium',
                                help='Soma do novo + acumulado'
                            )
                        }
                    )

                    total_futuro = df_futuros['ressarcimento_total'].sum()
                    st.warning(rf'⚠️ {len(df_futuros)} ressarcimentos acumulados para o futuro (< R\$ {valor_minimo:.2f}): R\$ {total_futuro:,.2f}')
                else:
                    st.info('ℹ️ Nenhum ressarcimento futuro')

            # ===== VALIDAÇÃO DE CONSOLIDAÇÃO (DEBUG) =====
            todos_ressarcimentos_brutos = st.session_state.get('todos_ressarcimentos_brutos', [])
            if st.toggle('🔍 Mostrar validação da consolidação', value=False):
                if len(todos_ressarcimentos_brutos) > 0:
                    df_brutos = pd.DataFrame(todos_ressarcimentos_brutos)
                    df_brutos_display = df_brutos.copy().sort_values(['jogador_id', 'clube_id'])

                    st.markdown('#### Antes da Consolidação')
                    st.caption('Cada ressarcimento individual por fraudador. Jogadores que enfrentaram múltiplos fraudadores aparecem várias vezes.')
                    st.dataframe(
                        df_brutos_display,
                        hide_index=True,
                        width='stretch',
                        column_config={
                            'jogador_id': 'ID Jogador', 'jogador_nome': 'Nome Jogador',
                            'clube_id': 'ID Clube', 'clube_nome': 'Nome Clube',
                            'ressarcimento': st.column_config.NumberColumn('Ressarcimento (R$)', format='R$ %.2f')
                        }
                    )
                    col_d1, col_d2 = st.columns(2)
                    col_d1.metric('Linhas (com duplicadas)', len(df_brutos))
                    col_d2.metric('Soma Bruta', f'R$ {df_brutos["ressarcimento"].sum():.2f}')

                    st.markdown('---')

                    duplicatas = df_brutos_display.groupby(['jogador_id', 'clube_id']).size().reset_index(name='quantidade')
                    duplicatas = duplicatas[duplicatas['quantidade'] > 1]
                    if len(duplicatas) > 0:
                        with st.expander('Jogadores com múltiplos ressarcimentos (enfrentaram mais de 1 fraudador)', expanded=False):
                            for _, dup in duplicatas.iterrows():
                                entradas = df_brutos[(df_brutos['jogador_id'] == dup['jogador_id']) & (df_brutos['clube_id'] == dup['clube_id'])]
                                jogador_nome = entradas.iloc[0]['jogador_nome']
                                clube_nome = entradas.iloc[0]['clube_nome']
                                total = entradas['ressarcimento'].sum()
                                st.markdown(f'**{jogador_nome} ({dup["jogador_id"]})** - {clube_nome}')
                                col_d1, col_d2 = st.columns([3, 1])
                                with col_d1:
                                    detalhes = ' + '.join([f'R$ {e["ressarcimento"]:.2f}' for _, e in entradas.iterrows()])
                                    st.text(detalhes)
                                col_d2.metric('Total', f'R$ {total:.2f}')
                    else:
                        st.info('✅ Nenhum jogador enfrentou múltiplos fraudadores')

                    st.markdown('---')

                    st.markdown('#### Depois da Consolidação')
                    st.caption('Cada jogador aparece apenas uma vez, com a soma de todos os ressarcimentos.')
                    df_consolidado_debug = df_brutos.groupby(['jogador_id', 'clube_id']).agg(
                        {'jogador_nome': 'first', 'clube_nome': 'first', 'ressarcimento': 'sum'}
                    ).reset_index().sort_values('ressarcimento', ascending=False)
                    st.dataframe(
                        df_consolidado_debug,
                        hide_index=True,
                        width='stretch',
                        column_config={
                            'jogador_id': 'ID Jogador', 'jogador_nome': 'Nome Jogador',
                            'clube_id': 'ID Clube', 'clube_nome': 'Nome Clube',
                            'ressarcimento': st.column_config.NumberColumn('Ressarcimento (R$)', format='R$ %.2f')
                        }
                    )
                    col_d1, col_d2 = st.columns(2)
                    col_d1.metric('Linhas (após consolidação)', len(df_consolidado_debug))
                    col_d2.metric('Soma Consolidada', f'R$ {df_consolidado_debug["ressarcimento"].sum():.2f}')

                    soma_bruta = df_brutos['ressarcimento'].sum()
                    soma_consolidada = df_consolidado_debug['ressarcimento'].sum()
                    if abs(soma_bruta - soma_consolidada) < 0.01:
                        st.success(f'✅ Consolidação correta! Soma bruta = Soma consolidada (R$ {soma_bruta:.2f})')
                    else:
                        st.error(f'❌ ERRO na consolidação! Soma bruta (R$ {soma_bruta:.2f}) ≠ Soma consolidada (R$ {soma_consolidada:.2f})')
                else:
                    st.info('ℹ️ Nenhum dado disponível para validação.')

        st.markdown('---')

        # ===== SALVAR NO BANCO DE DADOS =====
        st.subheader('💾 Salvar no Banco de Dados')
        st.info('''
            **IMPORTANTE:** Salve os dados no banco para:
            - Adicionar fraudadores à lista (evita ressarcimentos futuros)
            - Registar ressarcimentos no histórico (rastreabilidade)
            - Atualizar acumulados automaticamente (continuidade entre semanas)
        ''')

        # Validação: protocolo é obrigatório para salvar
        protocolo = st.number_input(
            'Protocolo',
            value=None,
            step=None,
            placeholder='Ex: 123456789',
            help='Número do Protocolo do caso a ser ressarcido.'
        )

        if not protocolo or protocolo is None:
            st.warning('⚠️ Digite o **Número do Protocolo** acima para habilitar o salvamento no banco')
            st.stop()

        # Referência (opcional, gera automático se vazio)
        referencia_padrao = f'Semana {date.today().strftime("%d/%m/%Y")}'
        referencia = st.text_input(
            'Referência (Opcional)',
            value=referencia_padrao,
            help='Descrição do período/lote de ressarcimento',
            max_chars=200
        )

        st.markdown('---')

        # ===== OPÇÕES PARA SALVAMENTO ======
        col_salvamento_1, col_salvamento_2, col_salvamento_3 = st.columns(3)

        with col_salvamento_1:
            salvar_fraudadores = st.checkbox(
                '🚫 Salvar Fraudadores',
                value=True,
                help='Adiciona os fraudadores desta apuração à lista'
            )

        with col_salvamento_2:
            salvar_historico = st.checkbox(
                '📊 Salvar Histórico',
                value=True,
                help='Registra os ressarcimentos imediados no histórico'
            )

        with col_salvamento_3:
            salvar_acumulados_db = st.checkbox(
                '⏳ Atualizar Acumulados',
                value=True,
                help='Atualiza a tabela de acumulados pendentes'
            )

        st.markdown('---')
        # ===== BOTÃO DE SALVAR =====
        if st.button('💾 Salvar Tudo no Banco', type='primary', width='stretch'):

            with st.spinner('Salvando no banco de dados...'):
                resultados_salvamento = {
                    'fraudadores': 0,
                    'historico': 0,
                    'acumulados': 0,
                    'erros': []
                }

                # 1. SALVAR FRAUDADORES
                if salvar_fraudadores:
                    try:
                        fraudadores_para_salvar = []

                        for _, fraudador in fraudadores_editados.iterrows():
                            fraudadores_para_salvar.append({
                                'jogador_id': int(fraudador['fraudador_id']),
                                'jogador_nome': fraudador['fraudador_nome'],
                                'clube_id': fraudador['clube_id'],
                                'clube_nome': fraudador['nome_clube'],
                                'protocolo': protocolo,
                                'valor_total_retido': fraudador['valor_reais'] + fraudador['rake_reais']
                            })

                        count = adicionar_fraudadores_lote(fraudadores_para_salvar)
                        resultados_salvamento['fraudadores'] = count

                    except Exception as e:
                        resultados_salvamento['erros'].append(f'Erro ao salvar fraudadores: {e}')

                # 2. SALVAR HISTÓRICO
                if salvar_historico and len(ressarcimentos_imediatos) > 0:
                    try:
                        count = salvar_ressarcimentos_lote(
                            ressarcimentos=ressarcimentos_imediatos,
                            protocolo=protocolo,
                            referencia=referencia
                        )
                        resultados_salvamento['historico'] = count

                    except Exception as e:
                        resultados_salvamento['erros'].append(f'Erro ao salvar histórico: {e}')

                # 3. ATUALIZAR ACUMULADOS
                if salvar_acumulados_db:
                    try:
                        if len(ressarcimentos_futuros) > 0:
                            count = atualizar_acumulados(ressarcimentos_futuros)
                            resultados_salvamento['acumulados'] = count
                        else:
                            # Se não houver acumulados novos, limpar tabela
                            from utils.database import limpar_acumulados
                            limpar_acumulados()
                            resultados_salvamento['acumulados'] = 0

                    except Exception as e:
                        resultados_salvamento['erros'].append(f'Erro ao atualizar acumulados: {e}')

            # ===== MOSTRAR RESULTADOS =====
            st.markdown('---')

            if len(resultados_salvamento['erros']) == 0:
                st.success('✅ Dados salvos com sucesso no banco de dados!')

                # Resumo do que foi salvo
                col1, col2, col3 = st.columns(3)

                with col1:
                    if salvar_fraudadores:
                        st.metric('Fraudadores Salvos', resultados_salvamento['fraudadores'])

                with col2:
                    if salvar_historico:
                        st.metric('Ressarcimentos Registrados', resultados_salvamento['historico'])

                with col3:
                    if salvar_acumulados_db:
                        st.metric('Acumulados Atualizados', resultados_salvamento['acumulados'])

                # Informação Importante
                st.info(f'''
                - 📝 **Protocolo:** {protocolo:.0f}
                - 📅 **Referência:** {referencia}
                - 🕛 **Data/Hora:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}
                ''')

            else:
                st.error('❌ Ocorreram erros ao salvar os dados:')
                for erro in resultados_salvamento['erros']:
                    st.error(f'- {erro}')

        col_export_1, col_export_2 = st.columns(2)

        with col_export_1:
            # ===== STRING DE RESSARCIMENTO =====
            st.subheader('📝 String de Ressarcimento para o Sistema')

            if len(ressarcimentos_imediatos) > 0:
                import math
                st.info('''
                **String formatada para prodessar ressarcimentos no sistema.**
                Copie e cole esta string no sistema de pagamentos.

                Formato: `jogador_id - clube_id - valor;`

                Para copiar o texto todo utilize o botão no canto superior direito da caixa abaixo:
                ''')

                # Gerar string formatada
                string_ressarcimento = ''
                for ressarcimento in ressarcimentos_imediatos:
                    jogador_id = int(ressarcimento['jogador_id'])
                    clube_id = int(ressarcimento['clube_id'])
                    valor = ressarcimento['ressarcimento_total']

                    # Truncar para 2 casa decimais (sem arredondar)
                    valor_truncado = math.floor(valor * 100) / 100

                    string_ressarcimento += f'{jogador_id} - {clube_id} - {valor_truncado}; '

                # Mostrar a string em uma caixa de código
                st.code(
                    string_ressarcimento,
                    language='text',
                    line_numbers=False,
                    height=100,
                    width='stretch'
                )

            else:
                st.warning('⚠️ Nenhum ressarcimento imediato para processar')

        with col_export_2:
            # ===== EXPORTAR PARA EXCEL =====
            st.subheader('💾 Exportar Relatório Completo')
            st.info('''
            **Download do relatório completo em Excel** contendo:

            - Resumo Geral
            - Ressarcimentos imediatos
            - Ressarcimentos futuros
            - Detalhamento por fraudador (uma aba para cada)
            ''')

            try:
                excel_bytes = criar_excel_ressarcimento(
                    resultados_por_fraudador,
                    ressarcimentos_imediatos,
                    ressarcimentos_futuros,
                    fraudadores_editados,
                    valor_minimo
                )

                st.download_button(
                    label='📥 Baixar Relatório Completo em Excel',
                    data=excel_bytes,
                    file_name=f'ressarcimento_fraudadores_{date.today().strftime("%Y-%m-%d")}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    type='primary',
                    width='stretch'
                )

                st.success('✅ Relatório Excel pronto para download')
            except Exception as e:
                st.error(f'❌ Erro ao gerar Excel: {e}')

        # ===== DETALHAMENTO POR FRAUDADOR =====
        if st.session_state.get('resultados_calculados', False):
            resultados_por_fraudador = st.session_state['resultados_por_fraudador']
            with st.expander('📝 Detalhamento por ID', expanded=False):
                for fraudador_id, resultado in resultados_por_fraudador.items():
                    fraudador_nome = resultado['fraudador_nome']
                    valor_disponivel = resultado['valor_disponivel']
                    total_ressarcido = resultado['total_ressarcido']
                    vitimas = resultado['vitimas']
                    mensagem = resultado['mensagem']

                    if total_ressarcido > 0:
                        titulo = rf'🚫 {fraudador_nome} ({fraudador_id}) | Ressarcido: R\$ {total_ressarcido:,.2f} de R\$ {valor_disponivel:,.2f}'
                    else:
                        titulo = f'⚠️ {fraudador_nome} ({fraudador_id}) | {mensagem}'

                    with st.expander(titulo, expanded=False):
                        col1, col2, col3 = st.columns(3)
                        col1.metric('Valor Disponível', f'R$ {valor_disponivel:,.2f}')
                        col2.metric('Valor Ressarcido', f'R$ {total_ressarcido:,.2f}')
                        col3.metric('Quantidade de Vítimas', len(vitimas))

                        if len(vitimas) == 0:
                            st.warning(f'⚠️ {mensagem}')
                            continue

                        st.markdown('**Vítimas e Ressarcimentos:**')
                        vitimas_display = vitimas[['jogador_id', 'jogador_nome', 'clube_id', 'clube_nome', 'saldo_liquido', 'ressarcimento', 'status']].copy()
                        vitimas_display.columns = ['ID Jogador', 'Nome', 'Clube ID', 'Nome Clube', 'Perda Líquida', 'Ressarcimento', 'Status']
                        st.dataframe(
                            vitimas_display,
                            hide_index=True,
                            width='stretch',
                            column_config={
                                'ID Jogador': st.column_config.NumberColumn('ID Jogador', width='small'),
                                'Nome': st.column_config.TextColumn('Nome', width='medium'),
                                'Clube ID': st.column_config.NumberColumn('Clube ID', width='small'),
                                'Nome Clube': st.column_config.TextColumn('Nome Clube', width='medium'),
                                'Perda Líquida': st.column_config.NumberColumn('Perda Líquida (R$)', format='R$ %.2f', width='small'),
                                'Ressarcimento': st.column_config.NumberColumn('Ressarcimento (R$)', format='R$ %.2f', width='small'),
                                'Status': st.column_config.TextColumn('Status', width='small')
                            }
                        )

        st.markdown('---')
    else:
        st.info('👆 Faça o upload do arquivo CSV para começar.')
        st.markdown("""
            **O arquivo deve conter as seguintes colunas:**
            - `JOGADOR_ID`: ID do jogador
            - `JOGADOR_NOME`: Nome do jogador
            - `CLUBE_ID`: ID do clube
            - `LIGA_ID`: ID da liga
            - `MAO_ID`: ID da mão
            - `GANHOS_REAIS`: Ganho/Perda em reais
            - `FRAUDADOR`: Indica se está na lista de fraudadores (TRUE/FALSE)
        """)

# ============================================================
# ABA 2 — RESSARCIMENTO PONTUAL (planilhas do backend)
# ============================================================
with tab_pontual:

    st.subheader('📂 Upload das Planilhas do Backend')
    st.markdown(
        'Carregue uma planilha por conta investigada. '
        'Formato esperado: **Player chips transaction record** exportado pelo backend.'
    )

    arquivos_pontual = st.file_uploader(
        'Selecione as planilhas',
        type=['xlsx'],
        accept_multiple_files=True,
        key='uploader_pontual',
        help='Carregue um arquivo por conta investigada. Múltiplos arquivos são concatenados automaticamente.',
    )

    if arquivos_pontual:
        df_pontual_bruto = carregar_xlsx(arquivos_pontual)

        if 'Player ID' not in df_pontual_bruto.columns:
            st.error('❌ Coluna "Player ID" não encontrada. Verifique se os arquivos são do tipo correto.')
        else:
            n_contas_pontual = df_pontual_bruto['Player ID'].nunique()
            ids_contas = df_pontual_bruto['Player ID'].unique().tolist()
            ids_str = ', '.join(str(i) for i in sorted(ids_contas))
            st.success(f'✅ {len(arquivos_pontual)} arquivo(s) carregado(s) — {n_contas_pontual} conta(s): {ids_str}')

            if n_contas_pontual < 2:
                st.warning('⚠️ Carregue planilhas de pelo menos 2 contas para identificar mãos em comum.')

            if st.button('🔄 Calcular', key='btn_calcular_pontual', type='primary', width = 'stretch'):
                with st.spinner('Processando...'):
                    soma_total_p, por_mesa_p, maos_comuns_p = processar_planilhas_backend(df_pontual_bruto)
                    st.session_state['pontual_soma_total'] = soma_total_p
                    st.session_state['pontual_por_mesa'] = por_mesa_p
                    st.session_state['pontual_maos_comuns'] = maos_comuns_p

    if 'pontual_soma_total' in st.session_state:
        soma_total_p = st.session_state['pontual_soma_total']
        por_mesa_p = st.session_state['pontual_por_mesa']
        maos_comuns_p = st.session_state['pontual_maos_comuns']

        if len(maos_comuns_p) == 0:
            st.warning('⚠️ Nenhuma mão em comum encontrada entre as contas.')
        else:
            mesas_ids = sorted(por_mesa_p['Mesa (Game ID)'].unique().tolist())
            n_maos = maos_comuns_p['Hand ID'].nunique()
            st.success(f'✅ {n_maos} mão(s) em comum encontrada(s) em {len(mesas_ids)} mesa(s).')

            st.markdown('---')

            # ── 1. Soma Total das Mesas ──────────────────────────────────────
            st.subheader('📊 Soma Total das Mesas')
            st.dataframe(
                soma_total_p,
                hide_index=True,
                width='stretch',
                column_config={
                    'ID Jogador': st.column_config.NumberColumn('ID Jogador', width='small'),
                    'Nome': st.column_config.TextColumn('Nome', width='medium'),
                    'Clube': st.column_config.TextColumn('Clube', width='medium'),
                    'Ganhos': st.column_config.NumberColumn('Ganhos', format='%.2f'),
                    'Rake': st.column_config.NumberColumn('Rake', format='%.2f'),
                    'Mãos em Comum': st.column_config.NumberColumn('Mãos em Comum', width='small'),
                },
            )

            st.markdown('---')

            # ── 2. Mesas Individualizadas ────────────────────────────────────
            st.subheader('🃏 Mesas Individualizadas')
            for mesa_id in mesas_ids:
                df_mesa_display = (
                    por_mesa_p[por_mesa_p['Mesa (Game ID)'] == mesa_id]
                    .drop(columns=['Mesa (Game ID)'])
                    .copy()
                )
                st.markdown(f'**Mesa {mesa_id}**')
                st.dataframe(
                    df_mesa_display,
                    hide_index=True,
                    width='stretch',
                    column_config={
                        'ID Jogador': st.column_config.NumberColumn('ID Jogador', width='small'),
                        'Nome': st.column_config.TextColumn('Nome', width='medium'),
                        'Clube': st.column_config.TextColumn('Clube', width='medium'),
                        'Ganhos': st.column_config.NumberColumn('Ganhos', format='%.2f'),
                        'Rake': st.column_config.NumberColumn('Rake', format='%.2f'),
                        'Mãos em Comum': st.column_config.NumberColumn('Mãos em Comum', width='small'),
                    },
                )

            st.markdown('---')

            # ── 3. Mãos Jogadas em Comum ─────────────────────────────────────
            st.subheader('🤝 Mãos Jogadas em Comum')
            st.dataframe(
                maos_comuns_p,
                hide_index=True,
                width='stretch',
                column_config={
                    'ID Jogador': st.column_config.NumberColumn('ID Jogador', width='small'),
                    'Nome': st.column_config.TextColumn('Nome', width='medium'),
                    'Clube': st.column_config.TextColumn('Clube', width='medium'),
                    'Mesa (Game ID)': st.column_config.NumberColumn('Mesa (Game ID)', width='small'),
                    'Hand ID': st.column_config.NumberColumn('Hand ID', width='small'),
                    'Ganhos': st.column_config.NumberColumn('Ganhos', format='%.2f'),
                    'Rake': st.column_config.NumberColumn('Rake', format='%.2f'),
                },
            )

            st.markdown('---')

            # ── Exportar PDF ─────────────────────────────────────────────────
            st.subheader('📄 Exportar PDF')
            protocolo_pontual = st.text_input(
                'Número do Protocolo',
                key='protocolo_pontual',
                placeholder='Ex: 1320845303',
                help='O arquivo será nomeado APURACAO-{protocolo}.pdf',
            )

            if protocolo_pontual:
                try:
                    pdf_bytes = gerar_pdf_pontual(
                        protocolo_pontual, soma_total_p, por_mesa_p, maos_comuns_p
                    )
                    st.download_button(
                        label='📥 Baixar PDF',
                        data=pdf_bytes,
                        file_name=f'APURACAO-{protocolo_pontual}.pdf',
                        mime='application/pdf',
                        type='primary',
                        width='stretch',
                    )
                except Exception as e:
                    st.error(f'❌ Erro ao gerar PDF: {e}')

    elif not arquivos_pontual:
        st.info('👆 Faça o upload das planilhas do backend para começar.')
        st.markdown("""
            **Formato esperado:** Player chips transaction record (exportado pelo backend Suprema Poker)

            **Colunas utilizadas:** Player ID, Player Name, Club Name, Association, Hands, chip change, Total Fee change, Event
        """)
