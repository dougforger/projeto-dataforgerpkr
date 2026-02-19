import shutil
import zipfile
import os
import math
import pyperclip
import pandas as pd
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

# import warnings
# warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

# Função para corrigir o arquivo xlsx com problema no styles.xml
def corrigir_xlsx(caminho):
    """
    Corrige o arquivo .xlsx com problema de cores inválidas no styles.xml.
    """
    caminho_corrigido = caminho.replace('.xlsx', '_corrigido.xlsx')
    shutil.copy(caminho, caminho_corrigido)

    with zipfile.ZipFile(caminho_corrigido, 'r') as z:
        conteudos = {nome: z.read(nome) for nome in z.namelist()}

    if 'xl/styles.xml' in conteudos:
        styles = conteudos['xl/styles.xml'].decode('utf-8')
        styles = styles.replace('rgb="#', 'rgb="')  # remove o # inválido
        conteudos['xl/styles.xml'] = styles.encode('utf-8')

    with zipfile.ZipFile(caminho_corrigido, 'w', zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in conteudos.items():
            z.writestr(nome, conteudo)

    return caminho_corrigido

def carregar_excel():
    """
    Abre o file dialog, corrige e carrega o Excel retornando o DataFrame.
    """
    # Abre a janela do exploer para escolher o arquivo.
    root = tk.Tk()
    root.withdraw() # Esconde a janela principal do tkinter

    caminho_excel = filedialog.askopenfilename(
        title="Selecione o arquivo Excel",
        filetypes=[("Arquivos Excel", ".xlsx *.xls")]
    )
    caminho_corrigido = corrigir_xlsx(caminho_excel)

    # Pega todas a abas e procura "sheet1" ignorando maiúsculas/minúsculas
    abas = pd.ExcelFile(caminho_corrigido).sheet_names
    aba_alvo = next((a for a in abas if a.lower() == "sheet1"), None)

    if aba_alvo is None:
        print("Aba 'sheet1' não encontrada! Abas disponíveis: ", abas)
        return None
    else:
        df = pd.read_excel(caminho_corrigido, sheet_name="sheet1", engine='openpyxl')

        # Seleciona apenas as colunas úteis
        colunas_uteis = ['Player ID', 'Name', 'Club ID', 'Union ID', 'Rank', 'prize']
        return df[colunas_uteis]

def adicionar_clube_name(df):
    """
    Faz o merge com o CSV de clubes e avisa sobre clubes sem nome cadastrado.
    """
    # Lê o CSV de clubes
    caminho_csv = os.path.join(DATA_DIR, 'clubes.csv')
    df_clubes = pd.read_csv(caminho_csv)

    # Garante que o tipo de Club ID seja o mesmo nos dois df's
    df['Club ID'] = df['Club ID'].astype(int)
    df_clubes['Club ID'] = df_clubes['Club ID'].astype(int)

    # Merge
    df = df.merge(df_clubes[['Club ID', 'Club Name']], on='Club ID', how='left')

    # Reordena as colunas para que Club Name fique à esquerda de Club ID
    df = df[['Player ID', 'Name', 'Club ID', 'Club Name', 'Union ID', 'Rank', 'prize']]
    
    # Avisa se houver clubes sem nome na lista
    clubes_novos = df[df['Club Name'].isna()]['Club ID'].unique()
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

def coletar_jogadores_eliminados():
    """
    Gera a lista de jogadores que serão eliminados da premiação.
    """
    jogadores_eliminados = []
    print("Digite os jogadores que serão eliminados da premiação (deixe o Player ID em branco para encerrar):")
    while True:
        player_id = input("Player ID: ").strip()
        if player_id == "":
            break
        jogadores_eliminados.append(int(player_id))
    return jogadores_eliminados

def adicionar_knockouts(df, jogadores_eliminados):
    """
    Confere se o torneio tem KOs e adiciona a coluna de KOs ao DataFrame, perguntando o valor de cada KO para os jogadores eliminados.
    """
    # Pergunta se o torneio tem KOs e, se sim, pede o valor de cada KO para os jogadores eliminados
    isKO = input("O torneio tem KOs? (s/n): ").strip().lower()
    if isKO == "s":
        knockouts = {}
        for jogador in jogadores_eliminados:
            valor = input(f"Valor do KO para {jogador}: ").strip()
            knockouts[int(jogador)] = float(valor)
        df['KO'] = df['Player ID'].map(knockouts).fillna(0)
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

def gerar_string_ressarcimento(df):
    """
    Gera uma string formatada com com os jogadores que receberão ressarcimento no formato:

    'id jogador - id clube - valor'
    
    :param df: DataFrame com os dados da premiação após cálculo do ressarcimento.
    """
    df_ressarcimento = df[df['Refund'] > 0]
    
    resultado = ''
    for _, row in df_ressarcimento.iterrows():
        valor = math.floor(row['Refund'] * 100) / 100  # Arredonda para baixo com 2 casas decimais
        resultado += f"{int(row['Player ID'])} - {int(row['Club ID'])} - {valor:.2f};"
    
    pyperclip.copy(resultado)  # Copia o resultado para a área de transferência
    # print(resultado)
    print("✅ Ressarcimento copiado para a área de transferência!")
    return resultado

if __name__ == "__main__":
    df = carregar_excel()
    if df is not None:
        df = adicionar_clube_name(df)
        df = ajustar_prize(df)

        jogadores_eliminados = coletar_jogadores_eliminados()
        prize_eliminados = df[df['Player ID'].isin(jogadores_eliminados)]['prize'].sum()

        df = adicionar_knockouts(df, jogadores_eliminados)

        # Calcula total_ko antes de remover os eliminados
        total_ko = df[df['Player ID'].isin(jogadores_eliminados)]['KO'].sum() if 'KO' in df.columns else 0
        rank_minimo = df[df['Player ID'].isin(jogadores_eliminados)]['Rank'].min()

        df = calcular_payjump(df, jogadores_eliminados)
        df = distribuir_knockouts(df, rank_minimo, total_ko)
        df = calcula_ressarcimento(df)
        ressarcimentos = gerar_string_ressarcimento(df)
       
        # Validação
        total_ressarcimento = df['Refund'].sum()
        print(f"Total a redistribuir: {prize_eliminados + total_ko:.2f}")
        print(f"Soma do ressarcimento: {total_ressarcimento:.2f}")
        if abs(total_ressarcimento - (prize_eliminados + total_ko)) < 0.3:  # Permite uma pequena margem de erro devido ao arredondamento
            print("Validação bem-sucedida: O total a redistribuir é igual à soma do ressarcimento.")