# projeto_payjump/web/pages/2_💲_Ressarcimento.py
import math
import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title='Ressarcimento',
    page_icon='💲',
    layout='wide'
)

st.title('💲 Ressarcimento')
st.markdown('Cálculo de ressarcimentos para mãos influenciadas por contas suspeitas')
st.markdown('---')

# ===== UPLOAD DO ARQUIVO =====
st.subheader('📂 Upload do Arquivo Exportado')
uploaded_file = st.file_uploader(
    'Selecione o arquivo CSV exportado do Snowflake',
    type=['csv'],
    help='Arquivo gerado pela query de análise de bots do Snowflake.'
)

def calcular_saldo_por_bot(df, bot_id, df_clubes):
    """
    Calcula o saldo líquido de cada jogador (não-bot) contra um bot específico.
    
    Args:
        df: DataFrame completo com todas as mãos
        bot_id: ID do bot para analisar
        df_clubes: DataFrame com informações dos clubes

    Returns:
        DataFrame com colunas: player_id, player_name, club_id, nome_clube, saldo_liquido
    """
    # Filtrar apenas as mãos onde o bot estava presente
    maos_do_bot = df[df['HAND_ID'].isin(
        df[df['PLAYER_ID'] == bot_id]['HAND_ID']
    )]

    # Filtrar apenas jogadores não-bot nessas mãos
    jogadores = maos_do_bot[maos_do_bot['IS_BOT'] == False]

    # Calcular saldo líquido de cada jogador
    saldos = jogadores.groupby(['PLAYER_ID', 'PLAYER_NAME', 'CLUB_ID']).agg({
        'GANHOS_REAIS': 'sum'
    }).reset_index()

    saldos.columns = ['player_id', 'player_name', 'club_id', 'saldo_liquido']

    # Adicionar nome do clube
    saldos = saldos.merge(
        df_clubes[['id-clube', 'nome-clube']],
        left_on='club_id',
        right_on='id-clube',
        how='left'
    )

    # Reorganizar colunas
    saldos = saldos[['player_id', 'player_name', 'club_id', 'nome-clube', 'saldo_liquido']]
    saldos.columns = ['player_id', 'player_name', 'club_id', 'club_name', 'saldo_liquido']

    # Filtrar apenas quem teve saldo negativo (perdeu)
    vitimas = saldos[saldos['saldo_liquido'] < 0].copy()

    return vitimas

def distribuir_ressarcimento(vitimas, valor_disponivel):
    """
    Distribui o valor retido do bot proporcionalmente entre as vítimas.
    
    Args:
        vitimas: DataFrame com player_id, player_name, club_id, saldo_liquido
        valor_disponivel: Valor total disponível para ressarcir (em reais)
        
    Returns:
        DataFrame com coluna adicional: ressarcimento
    """
    if len(vitimas) == 0 or valor_disponivel <= 0:
        vitimas['ressarcimento'] = 0.0
        return vitimas

    # Calcular total de perdas
    total_perdas = vitimas['saldo_liquido'].abs().sum()

    # Calcular proporção de cada vítima
    vitimas['proporcao'] = vitimas['saldo_liquido'].abs() / total_perdas

    # Calcular ressarcimento bruto (proporcional)
    vitimas['ressarcimento_bruto'] = vitimas['proporcao'] * valor_disponivel

    # Aplicar teto: ninguém recebe mais do que perdeu
    vitimas['ressarcimento'] = vitimas.apply(
        lambda row: min(row['ressarcimento_bruto'], abs(row['saldo_liquido'])),
        axis=1
    )

    # Arredondar para 2 casa decimais (truncar)
    vitimas['ressarcimento'] = vitimas['ressarcimento'].apply(
        lambda x:math.floor(x * 100) / 100
    )
    return vitimas

def criar_excel_ressarcimento(resultados_por_bot, ressarcimentos_imediatos, ressarcimentos_futuros, bots_editado, valor_minimo):
    '''
    Cria um arquivo Excel com múltiplas abas contendo todos os dados de ressarcimento

    Returns:
        bytes: Arquivo Excel em bytes para download
    '''
    from io import BytesIO
    import pandas as pd
    import re

    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # ===== ABA 1: RESUMO GERAL =====
        dados_resumo = {
            'Métrica': [
                'Total de Bots Analisados',
                'Bots com Valor Retido',
                'Total Disponível para Ressarcimento',
                'Total de Ressarcimentos Imediatos',
                'Total de Ressarcimentos Futuros',
                'Quantidade de Vítimas (Imediato)',
                'Quantidade de Vítimas (Futuro)',
                'Valor Mínimo Configurado'
            ],
            'Valor': [
                len(bots_editado),
                len([r for r in resultados_por_bot.values() if r['total_ressarcido'] > 0]),
                f'R$ {sum([r['valor_disponivel'] for r in resultados_por_bot.values()]):,.2f}',
                f'R$ {sum([r['ressarcimento_total'] for r in ressarcimentos_imediatos]):,.2f}' if len(ressarcimentos_imediatos) > 0 else 'R$ 0.00',
                f'R$ {sum([r['ressarcimento_total'] for r in ressarcimentos_futuros]):,.2f}' if len(ressarcimentos_futuros) > 0 else 'R$ 0.00',
                len(ressarcimentos_imediatos),
                len(ressarcimentos_futuros),
                f'R$ {valor_minimo:.2f}'
            ]
        }
        df_resumo = pd.DataFrame(dados_resumo)
        df_resumo.to_excel(writer, sheet_name='Resumo', index=False)

        # ===== ABA 2: RESSARCIMENTOS IMEDIATOS =====
        if len(ressarcimentos_imediatos) > 0:
            df_imediatos = pd.DataFrame(ressarcimentos_imediatos)
            df_imediatos = df_imediatos[['player_id', 'player_name', 'club_id', 'club_name', 'ressarcimento_novo', 'acumulado_anterior', 'ressarcimento_total']]
            df_imediatos.columns = ['ID Jogador', 'Nome Jogador', 'ID Clube', 'Nome Clube', 'Ressarcimento Novo (R$)', 'Acumulado Anterior (R$)', 'Total (R$)']
            df_imediatos.to_excel(writer, sheet_name='Ressarcimentos Imediatos', index=False)

        # ===== ABA 3: RESSARCIMENTOS FUTUROS =====
        if len(ressarcimentos_futuros) > 0:
            df_futuros = pd.DataFrame(ressarcimentos_futuros)
            df_futuros = df_futuros[['player_id', 'player_name', 'club_id', 'club_name', 'ressarcimento_novo', 'acumulado_anterior', 'ressarcimento_total']]
            df_futuros.columns = ['ID Jogador', 'Nome Jogador', 'ID Clube', 'Nome Clube', 'Ressarcimento Novo (R$)', 'Acumulado Anterior (R$)', 'Total (R$)']
            df_futuros.to_excel(writer, sheet_name='Ressarcimentos futuros', index=False)

        # ===== ABAS POR BOT =====
        for bot_id, resultado in resultados_por_bot.items():
            if len(resultado['vitimas']) > 0:
                bot_nome = resultado['bot_nome']

                # Remover caracteres inválidos para nome de aba do Excel
                # Caracteres proibidos: / \ * ? : [ ]

                bot_nome_limpo = re.sub(r'[/\\*?:\[\]]', '', bot_nome)
                # Limitar nome da aba a 31 caracteres (limite do Excel
                sheet_name = f'Bot {bot_nome_limpo} ({bot_id})'[:31]

                df_bot = resultado['vitimas'][[
                    'player_id', 'player_name', 'club_id', 'club_name', 'saldo_liquido', 'ressarcimento', 'status'
                ]].copy()

                df_bot.columns = ['ID Jogador', 'Nome Jogador', 'ID Clube', 'Nome Clube', 'Perda Líquida (R$)', 'Ressarcimento Novo (R$)', 'Status']

                df_bot.to_excel(writer, sheet_name=sheet_name, index=False)

    output.seek(0)
    return output.getvalue()

if uploaded_file is not None:
    # Carregar o CSV
    df = pd.read_csv(uploaded_file)
    
    # Validação das colunas necessárias
    colunas_necessarais = ['PLAYER_ID', 'PLAYER_NAME', 'CLUB_ID', 'UNION_ID', 'HAND_ID', 'GANHOS_REAIS', 'IS_BOT']
    colunas_faltando = [col for col in colunas_necessarais if col not in df.columns]
    
    if colunas_faltando:
        st.error(f'❌ Colunas faltando no arquivo: {', '.join(colunas_faltando)}')
        st.stop()
    
    st.success(f'✅ Arquivo carregado com sucesso! {len(df)} linhas encontradas.')

    # Mostrar prévia dos dados
    with st.expander('👀 Prévia dos Dados'):
        st.dataframe(df.head(10))
    
    st.markdown('---')

    # ===== UPLOAD DE ACUMULADOS ANTERIORES =====
    col_upload_1, col_upload_2 = st.columns([1, 2])
    with col_upload_1:
        st.subheader('📝 Ressarcimentos Acumulados (Opcional)')
    with col_upload_2:
        st.info('''
        **Se houver jogadores com ressarcimentos pendentes de semanas anteriores**,
        faça o upload do arquivo CSV de acumulados aqui. Esses valores serão somados aos novos cálculos desta semana.
        ''')
    with st.expander('📤 Upload do Arquivo'):
        uploaded_acumulados = st.file_uploader(
            'Upload de Acumulados Anteriores (CSV)',
            type=['csv'],
            help='Arquivo baixado no final do cálculo da semana anterior'
        )

        # Carregar acumulados se houver
        if uploaded_acumulados is not None:
            try:
                df_acumulados_antigos = pd.read_csv(uploaded_acumulados)

                # Validar colunas esperadas
                colunas_esperadas = ['player_id', 'player_name', 'club_id', 'club_name', 'ressarcimento_acumulado', 'data_ultima_atualizacao']

                if all(col in df_acumulados_antigos.columns for col in colunas_esperadas):
                    st.success(f'✅ Acumulados carregados: {len(df_acumulados_antigos)} jogador(es) com valor(es) pendente(s)')

                    with st.expander('👀 Prévia dos Acumulados'):
                        st.dataframe(
                            df_acumulados_antigos,
                            hide_index=True,
                            width='stretch',
                            column_config={
                                'player_id': 'ID Jogador',
                                'player_name': 'Nome Jogador',
                                'club_id': 'ID Clbue',
                                'nome_clube': 'Nome Clube',
                                'ressarcimento_acumulado': st.column_config.NumberColumn('Acumulado (R$)', format='%.2f'),
                                'data_ultima_atualizacao': 'Última Atualização'
                            }
                        )
                else:
                    st.error('❌ Arquivo de acumulados com formato inválido! Verifique as colunas.')
                    df_acumulados_antigos = pd.DataFrame()
            except Exception as e:
                st.error(f'❌ Erro ao carregar acumulados: {e}')
                df_acumulados_antigos = pd.DataFrame()
        else:
            # Se não houver uploado, cria DataFrame vazio
            df_acumulados_antigos = pd.DataFrame(columns=[
                'player_id', 'player_name', 'club_id', 'nome_clube', 'ressarcimento_acumulado', 'data_ultima_atualizacao'
            ])
            st.info('ℹ️ Nenhum acumulado anterior. Os cálculos começarão do zero.')

    st.markdown('---')

    # ===== CARREGAR INFORMAÇÕES DE CLUBES E LIGAS ======
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / 'data'

    df_clubes = pd.read_csv(DATA_DIR / 'clubes.csv')
    df_ligas = pd.read_csv(DATA_DIR / 'ligas.csv')

    # ===== IDENTIFICADO DOS BOTS =====
    st.subheader('⚙️ Configuração dos Valores Máximos por Bot')
    
    # Filtrar apenas os bots, pegar 
    # df_bots = df[df['IS_BOT'] == True].groupby(['PLAYER_ID', 'PLAYER_NAME']).agg({
    #     'GANHOS_REAIS': 'sum'
    # }).reset_index()
    df_bots = df[df['IS_BOT'] == True].groupby('PLAYER_ID').agg({
        'PLAYER_NAME': 'first',
        'CLUB_ID': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0],
        'UNION_ID': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0]
    }).reset_index()

    # Merge com os clubes
    df_bots = df_bots.merge(
        df_clubes[['id-clube', 'nome-clube']],
        left_on='CLUB_ID',
        right_on='id-clube',
        how='left'
    )

    # Merge com as ligas
    df_bots = df_bots.merge(
        df_ligas[['id-liga', 'nome-liga', 'moeda', 'handicap', 'taxa-liga']],
        left_on='UNION_ID',
        right_on='id-liga',
        how='left'
    )

    # Limpar e renomear colunas
    df_bots = df_bots[[
        'PLAYER_ID', 'PLAYER_NAME', 'CLUB_ID', 'nome-clube', 'UNION_ID', 'nome-liga', 'moeda', 'handicap'
    ]]
    df_bots.columns = [
        'id_bot', 'nome_bot', 'clube_id', 'nome_clube', 'liga_id', 'nome_liga', 'moeda', 'handicap'
    ]
    df_bots = df_bots.sort_values('id_bot')

    # Adicionar coluna editável para valor retido
    df_bots['valor_retido'] = 0.0
    df_bots['rake_retido'] = 0.0

    # df_bots.columns = ['PLAYER_ID', 'PLAYER_NAME', 'RESULTADO_LIQUIDO']
    # df_bots['VALOR_RETIDO'] = 0.0

    # Verificar se há bots em múltiplas ligas
    bots_multiplas_ligas = df[df['IS_BOT'] == True].groupby('PLAYER_ID')['UNION_ID'].nunique()
    bots_multiplas_ligas = bots_multiplas_ligas[bots_multiplas_ligas > 1]

    if len(bots_multiplas_ligas) > 0:
        st.warning(f'⚠️ {len(bots_multiplas_ligas)} bot(s) jogaram em mais de uma liga. Utilizando a liga mais frequente.')

    st.info(f'🤖 Encontrados **{len(df_bots)}** bots no arquivo. Insira o valor retido (em moeda local) para cada um:')

    # ===== TABELA EDITÁVEL =====
    bots_editados = st.data_editor(
        df_bots,
        disabled=['id_bot', 'nome_bot', 'clube_id', 'nome_clube', 'liga_id', 'nome_liga', 'moeda', 'handicap'],
        hide_index=True,
        width='stretch',
        column_config={
            'id_bot': st.column_config.NumberColumn(
                'ID Bot',
                width='small'
            ),
            'nome_bot': st.column_config.TextColumn(
                'Nome Bot',
                width='medium'
            ),
            'clube_id': st.column_config.NumberColumn(
                'Clube ID',
                width='small'
            ),
            'nome_clube': st.column_config.TextColumn(
                'Nome Clube',
                width='medium'
            ),
            'liga_id': st.column_config.NumberColumn(
                'ID Liga',
                width='small'
            ),
            'nome_liga': st.column_config.TextColumn(
                'Nome Liga',
                width='medium'
            ),
            'moeda': st.column_config.TextColumn(
                'Moeda',
                width='small'
            ),
            'handicap': st.column_config.NumberColumn(
                'Handicap',
                width='small',
                format='%.1f'
            ),
            'valor_retido': st.column_config.NumberColumn(
                'Valor Retido (Moeda Local)',
                help='Valor retido do bot na moeda local referente à liga a qual o clube pertence.',
                min_value=0.0,
                format='%.2f',
                width='medium',
                required=True
            ),
            'rake_retido': st.column_config.NumberColumn(
                'Rake Retido (Moeda Local)',
                help='Valor do rake gerado pelo bot na moeda local referente à liga a qual o clube pertence.',
                min_value=0.0,
                format='%.2f',
                width='medium',
                required=True
            )
        }
    )

    # ===== CONVERTER OS VALORES PARA REAL =====
    bots_editados['valor_reais'] = (bots_editados['valor_retido'].astype(float) / bots_editados['handicap'].astype(float)) * 5
    bots_editados['rake_reais'] = (bots_editados['rake_retido'].astype(float) / bots_editados['handicap'].astype(float)) * 5
    
    # Mostrar resumo
    st.markdown('---')
    st.subheader('📝 Resumo dos valores')

    col_resumo_1, col_resumo_2 = st.columns(2)
    with col_resumo_1:
        total_retido = bots_editados['valor_reais'].sum() + bots_editados['rake_reais'].sum()
        st.metric('Total Disponível para Ressarcimento', f'R$ {total_retido:,.2f}')
    with col_resumo_2:
        bots_com_valor = len(bots_editados[bots_editados['valor_retido'] > 0])
        st.metric('Bots com Valor Retido', f'{bots_com_valor} / {len(bots_editados)}')

    # Mostrar tabela com valores convertidos
    st.dataframe(
        bots_editados[['id_bot', 'nome_bot', 'nome_clube', 'moeda', 'valor_retido', 'rake_retido', 'valor_reais', 'rake_reais']],
        hide_index=True,
        column_config={
            'id_bot': 'ID Bot',
            'nome_bot': 'Nome Bot',
            'nome_clube': 'Nome Clube',
            'moeda': 'Moeda',
            'valor_retido': st.column_config.NumberColumn(
                'Valor Retido (Local)',
                format='%.2f'
            ),
            'rake_retido': st.column_config.NumberColumn(
                'Rake Retido (Local)',
                format='%.2f'
            ),
            'valor_reais': st.column_config.NumberColumn(
                'Valor Retido (R$)',
                format='%.2f'
            ),
            'rake_reais': st.column_config.NumberColumn(
                'Rake Retido (R$)',
                format='%.2f'
            )
        }
    )
    st.markdown('---')

    # ===== CONFIGURAÇÃO DE VALOR MÍNIMO =====
    
    st.subheader('⚙️ Configuração adicional')
    # col_config_1, col_config_2 = st.columns(2, width=1250)
    col_config_1, col_config_2, col_config_3, col_config_4, col_config_5 = st.columns([0.05, 0.425, 0.05, 0.425, 0.05], vertical_alignment='bottom')
    with col_config_1: st.empty()
    with col_config_2:
        valor_minimo = st.number_input(
            'Valor Mínimo para Ressarcimento (R$)',
            min_value=0.0,
            value=10.00,
            step=5.0,
            format='%.2f',
            help='Ressarcimentos abaixo deste valor serão acumulados para futuros ressarcimentos'
        )
        st.info(f'ℹ️ Jogadores com ressarcimento abaixo de R$ {valor_minimo} serão guardados para ressarcimentos futuros.')
    with col_config_3: st.empty()
    with col_config_4:
        
        # ===== BOTÃO DE CALCULAR =====
        # Botão para calcular
        calcular = st.button(
            '🔄 Calcular Ressarcimentos',
            type='primary',
            width='stretch'
        )
        # Validar se todos os valores foram preenchidos
        valores_zerados = bots_editados[bots_editados['valor_retido'] == 0.0]
        if len(valores_zerados) > 0:
            st.warning(f'⚠️ {len(valores_zerados)} bot(s) ainda com valor zero. Confira o valor antes de prosseguir.')
        else:
            st.success('✅ Todos os bots com valor preenchido.')
    with col_config_5: st.empty()

    # Lista separadas para ressarcimentos imediatos e futuros
    ressarcimentos_imediatos = []
    ressarcimentos_futuros = []

    # Dicionário para armazenar resultados de cada bot
    resultados_por_bot = {}
    
    if calcular:

        with st.spinner('Processando ressarcimentos...'):
            st.markdown('---')
            st.subheader('📊 Resultados dos Ressarcimentos')

            # Barra de progresso
            progress_bar = st.progress(0)
            status_text = st.empty()

            # Processar cada bot
            for idx, bot in bots_editados.iterrows():
                bot_id = bot['id_bot']
                bot_nome = bot['nome_bot']
                valor_disponivel = bot['valor_reais'] + bot['rake_reais']

                # Arualizar progresso
                progress = (idx + 1) / len(bots_editados)
                progress_bar.progress(progress)
                status_text.text(f'Processando Bot {bot_nome} ({bot_id})...')

                # Se não tiver valor retido, pular
                if valor_disponivel <= 0:
                    resultados_por_bot[bot_id] = {
                        'bot_nome': bot_nome,
                        'valor_disponivel': 0,
                        'vitimas': pd.DataFrame(),
                        'total_ressarcido': 0,
                        'mensagem': 'Bot sem valor retido'
                    }
                    continue

                # Calcular saldos das vítimas
                vitimas = calcular_saldo_por_bot(df, bot_id, df_clubes)

                # Se não há vítimas, pulas
                if len(vitimas) == 0:
                    resultados_por_bot[bot_id] = {
                        'bot_nome': bot_nome,
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

                resultados_por_bot[bot_id] = {
                    'bot_nome': bot_nome,
                    'valor_disponivel': valor_disponivel,
                    'vitimas': vitimas,
                    'total_ressarcido': total_ressarcido_imediato + total_ressarcido_futuro,
                    'total_imediato': total_ressarcido_imediato,
                    'total_futuro': total_ressarcido_futuro,
                    'mensagem': 'Processado com sucesso'
                }

                # Adiciona às listas separadas
                for _, vitima in vitimas.iterrows():
                    # Verificar se há acumulado anterior para este jogador
                    acumulado_anterior = 0.0
                    if len(df_acumulados_antigos) > 0:
                        match = df_acumulados_antigos[
                            (df_acumulados_antigos['player_id'] == vitima['player_id']) &
                            (df_acumulados_antigos['club_id'] == vitima['club_id'])
                        ]
                        if len(match) > 0:
                            acumulado_anterior = match.iloc[0]['ressarcimento_acumulado']

                    # Somar com acumulado anterior
                    ressarcimento_total = vitima['ressarcimento'] + acumulado_anterior

                    dados_ressarcimento = {
                        'player_id': int(vitima['player_id']),
                        'player_name': vitima['player_name'],
                        'club_id': int(vitima['club_id']),
                        'club_name': vitima['club_name'],
                        'ressarcimento_novo': vitima['ressarcimento'], # Apenas desta semana
                        'acumulado_anterior': acumulado_anterior,
                        'ressarcimento_total': ressarcimento_total
                    }

                    # Decidir se é imediato ou futuro baseado no total
                    if ressarcimento_total >= valor_minimo:
                        ressarcimentos_imediatos.append(dados_ressarcimento)
                    else:
                        ressarcimentos_futuros.append(dados_ressarcimento)

            # Limpar progresso
            progress_bar.empty()
            status_text.empty()

            # ===== SALVAR RESULTADOS NO SESSION STATE =====
            st.session_state['resultados_calculados'] = True
            st.session_state['resultados_por_bot'] = resultados_por_bot
            st.session_state['ressarcimentos_imediatos'] = ressarcimentos_imediatos
            st.session_state['ressarcimentos_futuros'] = ressarcimentos_futuros
            st.session_state['bots_editados'] = bots_editados
            st.session_state['valor_minimo'] = valor_minimo

        st.success('✅ Processamento concluído!')

    if st.session_state.get('resultados_calculados', False):
        # Carregar resultados do session state
        resultados_por_bot = st.session_state['resultados_por_bot']
        ressarcimentos_imediatos = st.session_state['ressarcimentos_imediatos']
        ressarcimentos_futuros = st.session_state['ressarcimentos_futuros']
        bots_editados = st.session_state['bots_editados']
        valor_minimo = st.session_state['valor_minimo']

        # ===== RESUMO GERAL =====
        st.markdown('---')
        st.subheader('📈 Resumo Geral')

        # Calcular métricas gerais
        total_bots_processados = len([r for r in resultados_por_bot.values() if r['total_ressarcido'] > 0])
        total_disponivel = sum([r['valor_disponivel'] for r in resultados_por_bot.values()])
        total_ressarcido_imediato = sum([r['total_imediato'] for r in resultados_por_bot.values()])
        total_ressarcido_futuro = sum([r['total_futuro'] for r in resultados_por_bot.values()])
        total_vitimas_imediatas = len(ressarcimentos_imediatos)
        total_vitimas_futuras = len(ressarcimentos_futuros)
        total_ressarcimento = total_ressarcido_imediato + total_ressarcido_futuro
        total_vitimas = total_vitimas_imediatas + total_vitimas_futuras
        # Mostrar métricas
        col_ressarcimento_1, col_ressarcimento_2, col_ressarcimento_3, col_ressarcimento_4 = st.columns(4)
        with col_ressarcimento_1:
            st.metric('Total Disponível', f'R$ {total_disponivel:,.2f}')
            st.metric('Bots Processados', f'{total_bots_processados} / {len(bots_editados)}')
        with col_ressarcimento_2:
            st.metric('Ressarcimento Imediato', f'R$ {total_ressarcido_imediato:,.2f}')
            st.metric('Vítimas (Imediato)', total_vitimas_imediatas)
        with col_ressarcimento_3:
            st.metric('Ressarcimento Futuro', f'R$ {total_ressarcido_futuro:,.2f}')
            st.metric('Vítimas (Futuro)', total_vitimas_futuras)
        with col_ressarcimento_4:
            st.metric('Ressarcimento Total', f'R$ {total_ressarcimento:,.2f}')
            st.metric('Vítimas Totais', total_vitimas)

        # Mostrar diferença (se houver)
        diferenca = total_disponivel - total_ressarcido_imediato - total_ressarcido_futuro
        if diferenca > 0:
            st.info(f'ℹ️ Diferença de R$ {diferenca:,.2f} não foi distribuída (tetos individuais aplicados)')
        else:
            st.error('❌ O saldo para ressarcimento é maior que o saldo retido! Verifique novamente.')

        st.markdown('---')

        # ===== DETALHAMENTO POR BOT =====
        st.subheader('📝 Detalhamento por Bot')

        for bot_id, resultado in resultados_por_bot.items():
            bot_nome = resultado['bot_nome']
            valor_disponivel = resultado['valor_disponivel']
            total_ressarcido = resultado['total_ressarcido']
            vitimas = resultado['vitimas']
            mensagem = resultado['mensagem']

            # Título do expander com resumo
            if total_ressarcido > 0:
                titulo = f'🤖 Bot {bot_nome} ({bot_id}) | Ressarcido: R$ {total_ressarcido:,.2f} de R$ {valor_disponivel:,.2f}'
                expanded = False # Começa fechado
            else:
                titulo = f'⚠️ Bot {bot_nome} ({bot_id}) | {mensagem}'
                expanded = False

            with st.expander(titulo, expanded=expanded):
                # Métricas do bot
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric('Valor Disponível', f'R$ {valor_disponivel:,.2f}')
                with col2:
                    st.metric('Valor Ressarcido', f'R$ {total_ressarcido:,.2f}')
                with col3:
                    st.metric('Quantidade de Vítimas', len(vitimas))

                # Se não tem vítimas, mostrar mensagem e continuar
                if len(vitimas) == 0:
                    st.warning(f'⚠️ {mensagem}')
                    continue

                # Mostrar tabela de vítimas
                st.markdown('**Vítimas e Ressarcimentos:**')

                # Preparar tabela para exibição
                vitimas_display = vitimas[[
                    'player_id', 'player_name', 'club_id', 'club_name', 'saldo_liquido', 'ressarcimento', 'status'
                ]].copy()

                vitimas_display.columns = ['ID Jogador', 'Nome', 'Clube ID', 'Nome Clube', 'Perda Líquida', 'Ressarcimento', 'Status']

                st.dataframe(
                    vitimas_display,
                    hide_index=True,
                    width='stretch',
                    column_config={
                        'ID Jogador': st.column_config.NumberColumn(
                            'ID Jogador',
                            width='small'
                        ),
                        'Nome': st.column_config.TextColumn(
                            'Nome',
                            width='medium'
                        ),
                        'Clube ID': st.column_config.NumberColumn(
                            'Clube ID',
                            width='small'
                        ),
                        'Nome Clube': st.column_config.TextColumn(
                            'Nome Clube',
                            width='medium'
                        ),
                        'Perda Líquida': st.column_config.NumberColumn(
                            'Perda Líquida (R$)',
                            format='R$ %.2f',
                            width='small'
                        ),
                        'Ressarcimento': st.column_config.NumberColumn(
                            'Ressarcimento (R$)',
                            format='R$ %.2f',
                            width='small'
                        ),
                        'Status': st.column_config.TextColumn(
                            'Status',
                            width='small'
                        )
                    }
                )

                # Botão para baixar Excel deste bot específico
                # Será implementado
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
                        'player_id': st.column_config.NumberColumn('ID Jogador', width='small'),
                        'player_name': st.column_config.TextColumn('Nome Jogador', width='medium'),
                        'club_id': st.column_config.NumberColumn('ID Clube', width='small'),
                        'club_name': st.column_config.TextColumn('Nome Clube', width='medium'),
                        'ressarcimento_novo': st.column_config.NumberColumn(
                            'Novo (R$)',
                            format='R$ %.2f',
                            width='medium',
                            help='Ressarcimento calculado esta semana'
                        ),
                        'ressarcimento_anterior': st.column_config.NumberColumn(
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
                st.success(f'✅ {len(df_imediatos)} ressarcimentos a processar agora (≥ R\$ {valor_minimo:.2f}): R\$ {total_imediato:,.2f}')
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
                        'player_id': st.column_config.NumberColumn('ID Jogador', width='small'),
                        'player_name': st.column_config.TextColumn('Nome Jogador', width='medium'),
                        'club_id': st.column_config.NumberColumn('ID Clube', width='small'),
                        'club_name': st.column_config.TextColumn('Nome Clube', width='medium'),
                        'ressarcimento_novo': st.column_config.NumberColumn(
                            'Novo (R$)',
                            format='R$ %.2f',
                            width='medium',
                            help='Ressarcimento calculado esta semana'
                        ),
                        'ressarcimento_anterior': st.column_config.NumberColumn(
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
                st.warning(f'⚠️ {len(df_futuros)} ressarcimentos acumulados para o futuro (< R\$ {valor_minimo:.2f}): R\$ {total_futuro:,.2f}')
            else:
                st.info('ℹ️ Nenhum ressarcimento futuro')

    st.markdown('---')
    
    col_export_1, col_export_2, col_export_3 = st.columns(3)
        
    with col_export_1:
        # ===== DOWNLOAD DE ACUMULADOS ATUALIZADOS =====
        st.subheader('💾 Salvar Acumulados')

        st.info('''
        **IMPORTANTE:** Baixe o arquivo de acumulados atualizados para usar no próximo ressarcimento!
        
        Esse arquivo contém os jogaodres que ainda não atingiram o valor mínimo.
        ''')
            
        if len(ressarcimentos_futuros) > 0:

            # Prepara DataFrame para download
            from datetime import date

            df_download = df_futuros[[
                'player_id', 'player_name', 'club_id', 'club_name', 'ressarcimento_total'
            ]].copy()

            df_download['data_ultima_atualizacao'] = date.today().strftime('%Y-%m-%d')

            df_download.columns = ['player_id', 'player_name', 'club_id', 'club_name', 'ressarcimento_acumulado', 'data_ultima_atualizacao']

            # Converter para CSV
            csv = df_download.to_csv(index=False, encoding='utf-8-sig')

            # Botão de download
            st.download_button(
                label='📥 Baixar Acumulados Atualizados',
                data=csv,
                file_name=f'ressarcimentos_acumulados_{date.today().strftime('%Y-%m-%d')}.csv',
                mime='text/csv',
                type='primary',
                width='stretch'
            )

            st.success(f'✅ Arquivo pronto: {len(df_download)} jogador(es) com valores acumulados')
        else:
            st.info('ℹ️ Nenhum acumulado para salvar (todos os ressarcimentos serão processados)')
    
    with col_export_2:
        # ===== STRING DE RESSARCIMENTO =====
        st.subheader('📝 String de Ressarcimento para o Sistema')

        if len(ressarcimentos_imediatos) > 0:
            st.info('''
            **String formatada para prodessar ressarcimentos no sistema.**
            Copie e cole esta string no sistema de pagamentos.
                    
            Formato: `player_id - club_id - valor;`
                    
            Para copiar o texto todo utilize o botão no canto superior direito da caixa abaixo:
            ''')
        
            # Gerar string formatada
            string_ressarcimento = ''
            for ressarcimento in ressarcimentos_imediatos:
                player_id = int(ressarcimento['player_id'])
                club_id = int(ressarcimento['club_id'])
                valor = ressarcimento['ressarcimento_total']

                # Truncar para 2 casa decimais (sem arredondar)
                valor_truncado = math.floor(valor * 100) / 100

                string_ressarcimento += f'{player_id} - {club_id} - {valor_truncado}; '
            
            # Mostrar a string em uma caixa de código
            st.code(
                string_ressarcimento,
                language='text',
                line_numbers=False,
                height=100,
                width='stretch'
            )

            # # Botão para copiar (usadno clipboard)
            # col_string_1, col_string_2 = st.columns([3, 1])
            # with col_string_1:
            #     st.text_input(
            #         'String completa (clique para selecionar tudo)',
            #         value=string_ressarcimento,
            #         label_visibility='collapsed',
            #         key='string_ressarcimento'
            #     )
            
            # with col_string_2:
            #     if st.button('📝 Copiar', width='stretch'):
            #         st.success('✅ Copiado!')
            
            # # Estatísticas da string
            # total_string = sum([r['ressarcimento_total'] for r in ressarcimentos_imediatos])
            # st.metric('Total a Processar', f'R$ {total_string:,.2f}')

        else:
            st.warning('⚠️ Nenhum ressarcimento imediato para processar')

    with col_export_3:
        # ===== EXPORTAR PARA EXCEL =====
        st.subheader('💾 Exportar Relatório Completo')
        st.info('''
        **Download do relatório completo em Excel** contendo:
                
        - Resumo Geral
        - Ressarcimentos imediatos
        - Ressarcimentos futuros
        - Detalhamento por bot (uma aba para cada)
        ''')

        try:
            from datetime import date

            excel_bytes = criar_excel_ressarcimento(
                resultados_por_bot,
                ressarcimentos_imediatos,
                ressarcimentos_futuros,
                bots_editados,
                valor_minimo
            )

            st.download_button(
                label='📥 Baixar Relatório Completo em Excel',
                data=excel_bytes,
                file_name=f'ressarcimento_bots_{date.today().strftime('%Y-%m-%d')}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                type='primary',
                width='stretch'
            )

            st.success('✅ Relatório Excel pronto para download')
        except Exception as e:
            st.error(f'❌ Erro ao gerar Excel: {e}')

    st.markdown('---')
else:
    st.info('👆 Faça o upload do arquivo CSV para começar.')
    st.markdown("""
        **O arquivo deve conter as seguintes colunas:**
        - `PLAYER_ID`: ID do jogador
        - `PLAYER_NAME`: Nome do jogador
        - `CLUB_ID`: ID do clube
        - `union_id`: ID da liga
        - `game_id`: ID do mesa
        - `HAND_ID`: ID da mão
        - `GANHOS_REAIS`: Ganho/Perda em reais
        - `rake_reais`: Rake gerado em reais
        - `blind_reais`: Valor do big blind em reais
        - `ante_por_jogador_reais`: Valor do ante em reais
        - `jogador_na_hand`: Quantidade de jogadores em cada mão
        - `limite_calculado_reais`: Valor mínimo que é considerado para o bot ter influenciado na mão
        - `IS_BOT`: Indica se está na lista de bots (TRUE/FALSE)
    """)