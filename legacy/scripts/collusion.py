import os
import pandas as pd

# --- TESTE DE IMPORTAÇÃO ---
def teste_import():
    print("Importação bem-sucedida do pandas!")

# ---------------------------

# --- COLLUSION ---

def collusion(caminho_csv):
    """
        Gera um DataFrame a partir de um arquivo CSV.
        Este DataFrame contém informações sobre jogadores, clubes e mãos jogadas.
        Ele é usado para analisar a porcentagem de mesas nas quais os jogadores participaram em comum a fim de avaliar a prática de collusion entre esses jogadores.
        
        ### Parâmetros:
        caminho_csv (str): Caminho do arquivo CSV a ser lido.
    """
    # --- Ler CSV e gerar o DataFrame ---
    csv_path = os.path.join(os.path.dirname(__file__), caminho_csv)
    df = pd.read_csv(csv_path)

    # -- Exibir o resumo do DataFrame ---
    print("\nColunas do DataFrame:", df.columns.tolist())
    print("Número de linhase e colunas:", df.shape)
    print("\nPrimeiras 5 linhas do DataFrame:")
    print(df.head())

    # # --- Gera um resumo com algumas informações úteis do DataFrame ---
    # resumo_agrupado = (
    #     df.groupby(["ID_JOGADOR", "NOME_JOGADOR", "ID_CLUBE", "ID_LIGA"], as_index=False)
    #         .agg(
    #             mesas_jogadas = ("ID_MESA", "nunique"),
    #             maos_jogadas = ("ID_MAO", "nunique"),
    #             ganhos_totais = ("GANHOS", "sum"),
    #             rake_total = ("RAKE", "sum")
    #         )
    #         .sort_values(["ID_JOGADOR"])
    # )

    # # --- Imprimir o resumo ---
    # print("\nResumo do Agrupado:")
    # print(resumo_agrupado)

    # # --- Agrupar os jogadores por mesa com a quantidade mãos jogadas em cada uma ---
    # resumo_jogador_mesa = (
    #     df.groupby(["ID_JOGADOR", "ID_MESA"], as_index=False)
    #         .agg(maos_jogadas = ("ID_MAO", "count"))
    # )
    
    # print("\nAgrupado Jogador - Mesa > Qnt de mãos")
    # print(resumo_jogador_mesa.head(5))

    # pares_jogadores = resumo_jogador_mesa.merge(
    #     resumo_jogador_mesa,
    #     on = "ID_MESA",
    #     suffixes = ("_1", "_2")
    # )

    # pares_jogadores = pares_jogadores[pares_jogadores["ID_JOGADOR_1"] < pares_jogadores["ID_JOGADOR_2"]]

    # print(pares_jogadores)
    return df
