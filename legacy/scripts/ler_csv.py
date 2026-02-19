import os
import platform
import sys
import pandas as pd

# Adicionar o diretório do script ao caminho do sistema para importar os modelos
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Importar os modelos dentro do script
from scripts.models import Jogador, Clube, Mao

# Limpar o Terminal antes de executar o script
if platform.system() == "Windows":
    os.system('cls')
else:
    os.system('clear')

# Caminho do CSV
csv_path = os.path.join(os.path.dirname(__file__), '../data/BUSCAR_JOGOS.csv')

# Ler o CSV
df = pd.read_csv(csv_path)

# Criação dos objetos a partir da leitura do csv.
jogadores = {}
clubes = {}

for _, row in df.iterrows():

    # --- Criação dos Clubes ---
    
    if row["ID_CLUBE"] not in clubes:
        clubes[row["ID_CLUBE"]] = Clube(
            id_clube=row["ID_CLUBE"],
            id_liga = row["ID_LIGA"]
        )
    clube = clubes[row["ID_CLUBE"]]

    # --- Criação dos Jogadores ---

    if row["ID_JOGADOR"] not in jogadores:
        jogadores[row["ID_JOGADOR"]] = Jogador(
            id_jogador = row["ID_JOGADOR"],
            nome_jogador = row["NOME_JOGADOR"],
        )
    jogador = jogadores[row["ID_JOGADOR"]]

    # --- Criação das Mãos ---

    mao = Mao(
        data = row["DATA_FORMATADA"],
        jogador = jogador,
        id_mao = row["ID_MAO"],
        id_mesa = row["ID_MESA"],
        nome_mesa = row["NOME_MESA"],
        ganhos = row["GANHOS"],
        rake = row["RAKE"],
        clube = clube
    )

    # Relaciona a mão ao jogador
    jogador.adicionar_mao(mao)

# --- Exibir jogadores com suas mãos ---
for jogador in list(jogadores.values()):
    print("\n", jogador)
    for mao in jogador.maos[:3]:  # Exibe apenas as 3 primeiras mãos de cada jogador
        print("  ", mao)

# --- Mostrar informações gerais do arquivo lido ---
print("\nColunas do CSV:", df.columns.tolist())
print("Número de linhas:", df.shape)
print("\nPrimeiras 5 linhas do arquivo:")
print(df.head())

# --- Agrupar os dados por jogaodr e mesa ---
agrupado = (
    df.groupby(["ID_JOGADOR", "NOME_JOGADOR", "ID_MESA"])
        .agg(
            maos_jogadas = ("ID_MAO", "count"),
            ganhos = ("GANHOS", "sum"),
            rake = ("RAKE", "sum")
        )
        .reset_index()
)

# --- Exibir os resultados do agrupamento ---
for jogador_id, grupo in agrupado.groupby("ID_JOGADOR"):
    print(f"Jogador {row["NOME_JOGADOR"]} ({jogador_id}):")
    for _, row in grupo.iterrows():
        print(f"Mesa {row['ID_MESA']} | {row['maos_jogadas']} mãos | "
              f"{row['ganhos']:.2f} | {row['rake']:.2f}")
    print()

# --- Cálculo das mãos jogadas em comum entre os jogadores ---
jogador_maos = df.groupby("ID_JOGADOR")["ID_MAO"].apply(set).to_dict()

for id_jogador, maos_jogadas in jogador_maos.items():
    nome_jogador = df.loc[df["ID_JOGADOR"] == id_jogador, "NOME_JOGADOR"].iloc[0]

    # Todas as mãos em comum com qualquer outro jogador
    maos_comuns = set()
    for outro_id, outras_maos in jogador_maos.items():
        if outro_id != id_jogador:
            maos_comuns |= (maos_jogadas & outras_maos) # união das interseções

    total_maos = len(maos_jogadas)
    total_comuns = len(maos_comuns)
    percent_comum = (total_comuns / total_maos * 100) if total_maos > 0 else 0

    print(f"{nome_jogador} ({id_jogador}):")
    print(f"  {total_comuns} | {total_maos} | {percent_comum:.2f}%")

# Filtrar linhas com ID_HAND duplicados
# maos_duplicadas = df[df.duplicated(subset='ID_MAO', keep=False)]
# maos_duplicadas_sorted = maos_duplicadas.sort_values(by='ID_MAO')

# print("\nLinhas com ID_MAO duplicados:", len(maos_duplicadas))
# print(maos_duplicadas_sorted.head(10)) # mostra as primeiras 10 linhas duplicadas