import shutil
import zipfile
import tkinter as tk
import pandas as pd
from tkinter import filedialog

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

    return df
