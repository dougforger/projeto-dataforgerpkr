import pandas as pd
from pathlib import Path
from arquivo_utils import carregar_excel

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

def atualizar_clubes():
    '''
    Atualiza o arquivo clubes.csv a partir de uma planilha Excel.
    Filtra apenas os clubes das ligas cadastradas e adiciona o nome da liga.
    '''

    ## Carrega dados
    lista_clubes = carregar_excel()
    if lista_clubes is None:
        print("❌ Erro ao carregar arquivo de clubes")
        return
    
    lista_ligas = pd.read_csv(DATA_DIR / "ligas.csv")
    ligas = lista_ligas['id-liga'].unique().tolist()
    
    ## Filtra os clubes de acordo com as ligas cadastradas.
    clubes = lista_clubes[lista_clubes['Union ID'].isin(ligas)]
    
    ## Seleciona as colunas desejadas e as renomeia.
    clubes = clubes[['Name', 'Club ID', 'Union ID']].rename(columns={
        'Club ID': 'id-clube',
        'Name': 'nome-clube',
        'Union ID': 'id-liga'})
    
    ## Converte os tipos para garantir compatibilidade.
    clubes['nome-clube'] = clubes['nome-clube'].astype(str)
    clubes['id-clube'] = clubes['id-clube'].astype(int)
    clubes['id-liga'] = clubes['id-liga'].astype(int)

    ## Adicona o nome da liga.
    clubes = clubes.merge(lista_ligas[['id-liga', 'nome-liga']], on='id-liga', how='left')
    
    ## Reordena as colunas.
    clubes = clubes[['id-clube', 'nome-clube', 'id-liga', 'nome-liga']]

    ## Remove duplicados caso existam
    clubes = clubes.drop_duplicates(subset=['id-clube'])

    ## Salva o novo arquivo clubes.csv
    clubes.to_csv(DATA_DIR / "clubes.csv", index=False, encoding='utf-8-sig')
    print(f"✅ Arquivo atualizado com {len(clubes)} clubes!")

    return clubes

if __name__ == "__main__":
    clubes_atualizados = atualizar_clubes()