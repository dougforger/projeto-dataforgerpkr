import streamlit as st
import pandas as pd
from pathlib import Path
import math

from utils.arquivo_utils import carregar_xlsx

st.set_page_config(
    page_title = 'Calculadora de Payjump',
    page_icon='📊',
    layout='wide'
)

with st.sidebar:
    st.markdown("### 🔒 Doug Forger PKR")
    st.markdown("**Sistema de Segurança**")
    st.markdown("---")
    st.info("""
    Desenvolvido para análise de dados
    a fim de garantir a integridade em
    plataformas de poker online.
    """)
    
st.title('📊 Calculadora de Payjump')
st.markdown('Cálculo automatizado de ressarcimentos em torneios de poker online')
st.markdown('---')

# Upload de arquivo
col_upload, col_cache = st.columns([4,1])
with col_upload:
    uploaded_file = st.file_uploader(
        'Faça o upload da planilha do torneio.',
        type=['xlsx', 'xls'],
        help='Selecione o arquivo Excel exportado do sistema. Esse arquivo deve começar com o nome "MTT Player List". Ele pode ser exportado da página "Game Information > MTT Player List" inserindo o GameID do evento desejado.'
    )
with col_cache:
    st.space()
    if st.button('🗑️ Limpar dados', key='backend-limpa-cache'):
        df = None
        st.cache_data.clear()
        st.rerun()

if uploaded_file is not None:
    # Valida a leitura do arquivo.
    if not uploaded_file.name.startswith('MTT Player List'):
        st.error("❌ Arquivo inválido! O nome da planilhadeve começar com 'MTT Player List'")
        st.stop()
    try:
        # Lê o arquivo.
        df = carregar_xlsx(uploaded_file)

        # st.write("Colunas encontradas:", df.columns.tolist())

        # Exibe informações básicas
        st.success(f'✅ Arquivo carregado com sucesso! {len(df)} jogadores encontrados.')

        # Exibe uma prévia dos dados
        st.subheader('Prévia do Torneio (Exibindo os 10 primeiros jogadores):')
        st.dataframe(df, width='stretch')

        # Seleciona as colunas úteis para o cálculo
        colunas_uteis = ['Player ID', 'Name', 'Club ID', 'Union ID', 'Rank', 'prize']
        df = df[colunas_uteis]

        # Carrega dados dos clubes
        BASE_DIR = Path(__file__).resolve().parent.parent
        DATA_DIR = BASE_DIR / 'data'

        df_clubes = pd.read_csv(DATA_DIR / 'clubes.csv')

        # Merge com os clubes
        df['Club ID'] = df['Club ID'].astype(int)
        df_clubes['clube_id'] = df_clubes['clube_id'].astype(int)

        df = df.merge(
            df_clubes[['clube_id', 'clube_nome']],
            left_on = 'Club ID',
            right_on = 'clube_id',
            how = 'left')

        df = df.rename(columns={'clube_nome': 'Club Name'})
        df = df.drop(columns=['clube_id'])
        df = df[['Player ID', 'Name', 'Club ID', 'Club Name', 'Union ID', 'Rank', 'prize']]

        # Verifica clubes sem nome
        clubes_sem_nome = df[df['Club Name'].isna()]
        if len(clubes_sem_nome) > 0:
            st.warning(f'⚠️ {len(clubes_sem_nome)} jogadores sem clubes cadastrados.')
            st.dataframe(
                clubes_sem_nome[['Player ID', 'Club ID']],
                width='stretch'
            )

        # st.markdown('---')
        # st.subheader('Ajuste da premiação')

        # Verifica se o torneio é da GU ou Liga Principal
        if df['Union ID'].nunique() == 1 and df['Union ID'].iloc[0] == 107:
            st.info("🏆 Torneio da Liga Principal - Prize já em reais")
        else:
            df['prize'] = df['prize'] * 5
            st.info("🏆 Torneio da GU - Prize será convertido para reais (multiplicado por 5)")

        st.markdown('---')
        col1, col2 = st.columns([1.25,1])
        with col1:
            # Coleta os jogadores eliminados junto de seus ko
            # st.markdown('---')
            st.subheader('Jogadores Eliminados e KOs')
            st.info('Digite os IDs dos jogadores eliminados e seus respectivos KOs na tabela abaixo:')
            
            kos_dict = {}
            jogadores_eliminados = []
            
            # Cria um DataFrame inicial vazio para o editor
            if 'df_eliminados_input' not in st.session_state:
                st.session_state.df_eliminados_input = pd.DataFrame({
                    'Player ID': [0, 0, 0],
                    'Valor do KO': [0.0, 0.0, 0.0]
                })

            # Editor de dados
            df_editado = st.data_editor(
                st.session_state.df_eliminados_input,
                num_rows='dynamic',
                width='stretch',
                hide_index=True,
            )
            
            # Botão para processar os jogadores eliminados
            if st.button('🔄 Processar Eliminados', type='primary'):
                # Remove linhas com Player ID iguais a 0
                df_editado = df_editado[df_editado['Player ID'] != 0]

                if len(df_editado) > 0:
                    jogadores_eliminados = df_editado['Player ID'].tolist()
                    kos_dict = df_editado.set_index('Player ID')['Valor do KO'].to_dict()
                    
                    st.success(f'✅ {len(jogadores_eliminados)} jogador(es) marcado(s) para eliminação.')
                    
                    # Mostra jogadores eliminados e seus KOs
                    df_eliminados = df[df['Player ID'].isin(jogadores_eliminados)].copy()
                    df_eliminados['KO'] = df_eliminados['Player ID'].map(kos_dict).fillna(0)
                    df_eliminados = df_eliminados.rename(columns={
                        'Player ID': 'ID do Jogador',
                        'Name': 'Nome do Jogador',
                        'Club ID': 'ID do Clube',
                        'Club Name': 'Nome do Clube',
                        'Union ID': 'ID da Liga',
                        'Rank': 'Posição Final',
                        'prize': 'Premiação (R$)',
                        'KO': 'Valor do KO (R$)'
                    })

                    st.dataframe(
                        df_eliminados[['ID do Jogador', 'Nome do Jogador', 'ID do Clube', 'Nome do Clube', 'ID da Liga','Posição Final', 'Premiação (R$)', 'Valor do KO (R$)']],
                        hide_index=True,
                        width='stretch')
                else:
                    st.warning('⚠️ Nenhum jogador marcado para eliminação.')
            
        with col2:
            # st.markdown('---')
            st.subheader('Cálculo do Payjump')

            # Adiciona a coluna de KO ao DataFrame principal
            df['KO'] = df['Player ID'].map(kos_dict).fillna(0)

            #Calcula totais antes de eliminar os jogadores
            premiacao_eliminados = df[df['Player ID'].isin(jogadores_eliminados)]['prize'].sum()
            total_ko = df[df['Player ID'].isin(jogadores_eliminados)]['KO'].sum()
            rank_minimo = df[df['Player ID'].isin(jogadores_eliminados)]['Rank'].min()

            # Reakiza o payjump
            premiacao_por_rank = df.sort_values('Rank')['prize'].reset_index(drop=True)
            df_remanescentes = df[~df['Player ID'].isin(jogadores_eliminados)].sort_values('Rank').reset_index(drop=True).copy()
            df_remanescentes['Nova Premiação (R$)'] = premiacao_por_rank[:len(df_remanescentes)].values

            st.success(f'💰 Total a redistribuir: R$ {premiacao_eliminados + total_ko:.2f}')

            # Distribuição dos KOs proporcionalmente
            if 'KO' in df_remanescentes.columns and total_ko > 0:
                mask = df_remanescentes['Rank'] >= rank_minimo
                premiacao_proporcional = df_remanescentes.loc[mask, 'Nova Premiação (R$)'].sum()

                df_remanescentes['KO Proporcional (R$)'] = 0.0
                df_remanescentes.loc[mask, 'KO Proporcional (R$)'] = (
                    total_ko * df_remanescentes.loc[mask, 'Nova Premiação (R$)'] / premiacao_proporcional
                ).apply(lambda x: math.floor(x * 100) / 100) # Trunca em 2 casas decimais

            # Calcula ressarcimento
            if 'KO Proporcional (R$)' in df_remanescentes.columns:
                df_remanescentes['Ressarcimento (R$)'] = (
                    df_remanescentes['Nova Premiação (R$)'] +
                    df_remanescentes['KO Proporcional (R$)'] -
                    df_remanescentes['prize']
                )
            else:
                df_remanescentes['Ressarcimento (R$)'] = df_remanescentes['Nova Premiação (R$)'] - df_remanescentes['prize']

            # Validação
            total_ressarcimento = df_remanescentes['Ressarcimento (R$)'].sum()
            diferenca = abs((premiacao_eliminados + total_ko) - total_ressarcimento)

            #subcol1, subcol2, subcol3 = st.columns(3)
            #with subcol1:
            st.metric('Total a Redistribuir', f'R$ {premiacao_eliminados + total_ko:.2f}')
            #with subcol2:
            st.metric('Total de Ressarcimento', f'R$ {total_ressarcimento:.2f}')
            #with subcol3:
            if diferenca < 0.3:
                st.metric("Validação", "✅ OK", delta=f'R$ {diferenca:.2f}')
            else:
                st.metric("Validação", "⚠️ Divergência", delta=f'R$ {diferenca:.2f}')
        
        renomear_colunas = {
            'Player ID': 'ID do Jogador',
            'Name': 'Nome do Jogador',
            'Club ID': 'ID do Clube',
            'Club Name': 'Nome do Clube',
            'Union ID': 'ID da Liga',
            'Rank': 'Posição Final',
            'prize': 'Premiação Antiga(R$)',
            'Nova Premiação (R$)': 'Nova Premiação (R$)',
            'KO': 'Valor do KO (R$)',
            #'KO Proporcional (R$)': 'KO Proporcional (R$)',
            'Ressarcimento (R$)': 'Ressarcimento (R$)'
        }

        if 'KO Proporcional (R$)' in df_remanescentes.columns:
            renomear_colunas['KO Proporcional (R$)'] = 'KO Proporcional (R$)'
        df_remanescentes = df_remanescentes.rename(columns=renomear_colunas)

        exibir_colunas = ['ID do Jogador', 'Nome do Jogador', 'Nome do Clube', 'Premiação Antiga(R$)', 'Nova Premiação (R$)', 'Ressarcimento (R$)']
        if 'KO Proporcional (R$)' in df_remanescentes.columns:
            exibir_colunas.insert(-1, 'KO Proporcional (R$)')
        
        st.markdown('---')
        st.subheader('Dados Processados:')
        st.dataframe(df_remanescentes[exibir_colunas],
                     hide_index=True,
                     width='stretch')
        
        st.markdown('---')
        st.subheader('String de Ressarcimento:')
        
        df_ressarcimento = df_remanescentes[df_remanescentes['Ressarcimento (R$)'] > 0]        
        resultado = ''
        for _, row in df_ressarcimento.iterrows():
            valor = math.floor(row['Ressarcimento (R$)'] * 100) / 100  # Trunca em 2 casas decimais
            resultado += f'{row["ID do Jogador"]} - {row["ID do Clube"]} - {valor:.2f};'
        
        st.info('O texto abaixo contém os jogadores que devem ser ressarcidos, seus respectivos clubes e o valor do ressarcimento.\n'
                'Copie e cole no sistema para processar os ressarcimentos automaticamente.')
        
        # Exibe a string formatada
        st.code(resultado,
                language='text',
                wrap_lines=True,
                height=200)

    except Exception as e:
        st.error(f'❌ Erro ao processar o arquivo: {e}')

else:
    st.info('👆 Faça o upload da planilha do torneio para começar.')
    