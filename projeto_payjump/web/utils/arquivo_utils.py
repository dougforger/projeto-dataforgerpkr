'''
Utilitários para leitura e correção de arquivos.

Funções reutilizáveis entre páginas para lidar com arquivos XLSX malformados
exportados do sistema (erro no styles.xml).
'''

import io
import zipfile
import pandas as pd


def corrigir_xlsx_memoria(arquivo):
    '''
    Corrige arquivos XLSX malformados sem salvar em disco.

    Alguns arquivos exportados do sistema contêm um erro no styles.xml
    (atributo rgb com prefixo "#" inválido). Esta função corrige o arquivo
    em memória antes de passá-lo para o pandas.

    Args:
        arquivo: Arquivo enviado via st.file_uploader ou similar.

    Returns:
        BytesIO: Buffer com o arquivo corrigido, pronto para leitura.
    '''
    bytes_original = arquivo.read()
    buffer_corrigido = io.BytesIO()

    with zipfile.ZipFile(io.BytesIO(bytes_original), 'r') as z:
        conteudos = {nome: z.read(nome) for nome in z.namelist()}

    if 'xl/styles.xml' in conteudos:
        styles = conteudos['xl/styles.xml'].decode('utf-8')
        styles = styles.replace('rgb="#', 'rgb="')
        conteudos['xl/styles.xml'] = styles.encode('utf-8')

    with zipfile.ZipFile(buffer_corrigido, 'w', zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in conteudos.items():
            z.writestr(nome, conteudo)

    buffer_corrigido.seek(0)
    return buffer_corrigido


def carregar_xlsx(arquivos):
    '''
    Carrega um ou mais arquivos XLSX, corrigindo malformações automaticamente.

    Aceita tanto um arquivo único quanto uma lista de arquivos.
    Quando múltiplos arquivos são passados, os DataFrames são concatenados.

    Args:
        arquivos: Arquivo único ou lista de arquivos (st.file_uploader).

    Returns:
        DataFrame: Dados carregados e concatenados.
    '''
    if not isinstance(arquivos, list):
        arquivos = [arquivos]

    dfs = []
    for arquivo in arquivos:
        arquivo_corrigido = corrigir_xlsx_memoria(arquivo)
        df_temp = pd.read_excel(arquivo_corrigido, engine='openpyxl')
        dfs.append(df_temp)

    return pd.concat(dfs, ignore_index=True)
