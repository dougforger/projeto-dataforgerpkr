import zipfile
import shutil
import pandas as pd

caminho = "c:\\Users\\DouglasArmandoFerrei\\OneDrive - Suprema\\Suprema\\#1293454414\\MTT Player List(2026-02-13 15：35：31).xlsx"  # substitui pelo caminho real

def corrigir_xlsx(caminho):
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

# with zipfile.ZipFile(caminho, 'r') as z:
#     for nome in z.namelist():
#         print(nome)

# with zipfile.ZipFile(caminho, 'r') as z:
#     styles = z.read('xl/styles.xml').decode('utf-8')
#     print(styles[:3000])  # primeiros 3000 caracteres

df = pd.read_excel(corrigir_xlsx(caminho), sheet_name="sheet1", engine='openpyxl')
print(df.head())