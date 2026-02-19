# --- LIMPAR TERMINAL ---
import os
import platform

if platform.system() == "Windows":
    os.system('cls')   
else:
    os.system('clear')

# ------------------------

# --- DIRETÓRIO DO PROJETO ---
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from scripts.collusion import teste_import, collusion
# ----------------------------

print("Iniciando o script...")
teste_import()
caminho_csv = '../data/player_detail.csv'
collusion(caminho_csv)