import pyperclip
import math

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

def adicionar_knockouts_input(jogadores_eliminados):
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
        return knockouts
    return None

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