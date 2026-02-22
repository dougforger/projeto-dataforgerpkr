import os
import math
import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

def adicionar_clube_name(df):
    """
    Faz o merge com o CSV de clubes e avisa sobre clubes sem nome cadastrado.
    """
    # Lê o CSV de clubes
    caminho_csv = os.path.join(DATA_DIR, 'clubes.csv')
    df_clubes = pd.read_csv(caminho_csv)

    # Garante que o tipo de Club ID seja o mesmo nos dois df's
    df['Club ID'] = df['Club ID'].astype(int)
    df_clubes['id-clube'] = df_clubes['id-clube'].astype(int)

    # Merge
    df = df.merge(df_clubes[['id-clube', 'nome-clube']], left_on='Club ID', right_on='id-clube', how='left')

    # Reordena as colunas para que Club Name fique à esquerda de Club ID
    df = df[['Player ID', 'Name', 'Club ID', 'nome-clube', 'Union ID', 'Rank', 'prize']]
    
    # Avisa se houver clubes sem nome na lista
    clubes_novos = df[df['nome-clube'].isna()]['Club ID'].unique()
    if len(clubes_novos) > 0:
            print("Clubes sem nome cadastrado: ", clubes_novos)
    
    return df

def ajustar_prize(df):
    """
    Verifica se o torneio é da Liga Principal ou da GU e ajusta o prize em reais.
    """
    # Verifica se o torneio é da Liga Principal conferindo se todos os Union ID são iguais a 107
    if df['Union ID'].nunique() == 1 and df['Union ID'].iloc[0] == 107:
        print("Torneio da Liga Principal, prize já em reais.")
    else:
        df['prize'] = df['prize'] * 5
        print("Torneio da GU, prize corrigido para reais.")
    return df

def distribuir_knockouts(df, rank_minimo, total_ko):
    """
    Soma os KOs dos jogadores eliminados e distribui proporcionalmente ao novo prize
    de cada jogador remanescente a partir do rank mínimo dos eliminados.
    
    :param df: DataFrame com os dados da premiação após remoção dos eliminados.
    :param rank_minimo: Rank mínimo dos jogadores eliminados.
    :param total_ko: Soma dos KOs dos jogadores eliminados.
    """
    if 'KO' not in df.columns or total_ko == 0:
        return df  # Se não houver KOs, retorna o DataFrame sem alterações
    
    mask = df['Rank'] >= rank_minimo
    total_prize = df.loc[mask, 'new prize'].sum()

    # Distribui proporcionalmente
    df['KO Bonus'] = 0.0
    df.loc[mask, 'KO Bonus'] = (df.loc[mask, 'new prize'] / total_prize * total_ko).apply(lambda x: math.floor(x * 100) / 100)

    return df

def calcula_ressarcimento(df):
    """
    Calcula o ressarcimento para cada jogador remanescente, considerando o novo prize, o prize original e o bônus de KOs (se houver).
    
    :param df: DataFrame com os dados da premiação original.
    """
    if 'KO Bonus' in df.columns:
        df['Refund'] = df['new prize'] + df['KO Bonus'] - df['prize']
    else:
        df['Refund'] = df['new prize'] - df['prize']
    
    return df

def calcular_payjump(df, jogadores_eliminados):
    """
    Guarda a lista original da premiação de acordo com o ranking.
    Remove os jogadores eliminados subindo a lista da premiação e calcula a diferença entre a nova e antiga premiação.
    
    :param df: DataFrame com os dados da premiação original.
    :param jogadores_eliminados: Lista de Player IDs dos jogadores eliminados.
    """
    # Separa a cluna de prizes ordenada por rank.
    prizes_por_rank = df.sort_values('Rank')['prize'].reset_index(drop=True)

    # Remove os eliminados e reseta o index
    df_remanescentes = df[~df['Player ID'].isin(jogadores_eliminados)].sort_values('Rank').reset_index(drop=True)

    # Atribui o novo prize baseado na nova premiação
    df_remanescentes['new prize'] = prizes_por_rank[:len(df_remanescentes)].values

    return df_remanescentes

def adicionar_knockouts(df, knockouts_dict):
    """
    Confere se o torneio tem KOs e adiciona a coluna de KOs ao DataFrame, perguntando o valor de cada KO para os jogadores eliminados.
    """
    # Pergunta se o torneio tem KOs e, se sim, pede o valor de cada KO para os jogadores eliminados
    if knockouts_dict is not None:
        df['KO'] = df['Player ID'].map(knockouts_dict).fillna(0)
    return df