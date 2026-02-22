from arquivo_utils import carregar_excel
from processamento import (
    adicionar_clube_name,
    ajustar_prize,
    adicionar_knockouts,
    distribuir_knockouts,
    calcula_ressarcimento,
    calcular_payjump
)
from io_utils import (
    coletar_jogadores_eliminados,
    adicionar_knockouts_input,
    gerar_string_ressarcimento
)

def main():
    '''
    Função principal do programa que executa o fluxo completo de cálculo do payjump.
    '''

    # 1. Carrega o arquivo Excel
    df = carregar_excel()
    if df is None:
        return print('Não foi possível carregar o arquivo.')
    else:
        print("Arquivo carregado com sucesso! Processando os dados...")
    colunas_uteis = ['Player ID', 'Name', 'Club ID', 'Union ID', 'Rank', 'prize']
    df = df[colunas_uteis]

    # 2. Adiciona o nome dos clubes
    df = adicionar_clube_name(df)

    # 3. Ajusta o prize (GU ou Liga Principal)
    df = ajustar_prize(df)

    # 4. Coleta os jogadores eliminados
    jogadores_eliminados = coletar_jogadores_eliminados()
    prize_eliminados = df[df['Player ID'].isin(jogadores_eliminados)]['prize'].sum()

    # 5. Adiciona os KOs dos jogadores eliminados
    ko_dict = adicionar_knockouts_input(jogadores_eliminados)
    df = adicionar_knockouts(df, ko_dict)

    # 6. Calcula o total de KO e o rank mínimo dos jogadores eliminados antes de removê-los.
    total_ko = df[df['Player ID'].isin(jogadores_eliminados)]['KO'].sum() if 'KO' in df.columns else 0
    rank_minimo = df[df['Player ID'].isin(jogadores_eliminados)]['Rank'].min()

    # 7. Calcula o payjump para os jogadores remanescentes.
    df = calcular_payjump(df, jogadores_eliminados)

    # 8. Distribui os KO proporcionalmente
    df = distribuir_knockouts(df, rank_minimo, total_ko)

    # 9. Calcula o ressarcimento
    df = calcula_ressarcimento(df)

    # 10. Gera a string de ressarcimentos
    string_ressarcimento = gerar_string_ressarcimento(df)

    # 11. Validação
    total_ressacimento = df['Refund'].sum()
    print(
        f'Total a redistribuir: {prize_eliminados + total_ko:.2f}'
        f'\nTotal de ressarcimento: {total_ressacimento:.2f}'
        )
    if abs(total_ressacimento - (prize_eliminados + total_ko)) < 0.3:
        print("✅ Validação bem-sucedida: O total de ressarcimento é consistente com o valor a redistribuir.")
    else:
        print("⚠️ Validação falhou: O total de ressarcimento não é consistente com o valor a redistribuir.")

if __name__ == "__main__":
    df_final = main()