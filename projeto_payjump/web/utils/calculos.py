'''
Cálculos de negócio para ressarcimentos.

Funções puras de cálculo e exportação, sem dependência do Streamlit.
Reutilizáveis em qualquer página ou contexto.
'''

import io
import math
import re

import pandas as pd


def calcular_saldo_por_fraudador(df, id_fraudador, df_clubes, ids_fraudadores=[]):
    '''
    Calcula o saldo líquido de cada jogador (não fraudador) contra um fraudador específico.

    Args:
        df (DataFrame): DataFrame completo com todas as mãos.
        id_fraudador (int): ID do fraudador para analisar.
        df_clubes (DataFrame): DataFrame com informações dos clubes.
        ids_fraudadores (list): Lista de IDs de fraudadores a excluir do cálculo.

    Returns:
        DataFrame com colunas: jogador_id, jogador_nome, clube_id, clube_nome, saldo_liquido.
        Contém apenas jogadores com saldo negativo (vítimas).
    '''
    # Filtrar apenas as mãos onde o fraudador estava presente
    maos_fraudador = df[df['MAO_ID'].isin(
        df[df['JOGADOR_ID'] == id_fraudador]['MAO_ID']
    )]

    # Filtrar apenas jogadores não fraudadores nessas mãos
    jogadores = maos_fraudador[maos_fraudador['FRAUDADOR'] == False]

    # Excluir outros fraudadores conhecidos do cálculo
    if len(ids_fraudadores) > 0:
        jogadores = jogadores[~jogadores['JOGADOR_ID'].isin(ids_fraudadores)]

    # Calcular saldo líquido de cada jogador
    saldos = jogadores.groupby(['JOGADOR_ID', 'JOGADOR_NOME', 'CLUBE_ID']).agg({
        'GANHOS_REAIS': 'sum'
    }).reset_index()

    saldos.columns = ['jogador_id', 'jogador_nome', 'clube_id', 'saldo_liquido']

    # Adicionar nome do clube
    saldos = saldos.merge(
        df_clubes[['clube_id', 'clube_nome']],
        on='clube_id',
        how='left'
    )

    saldos = saldos[['jogador_id', 'jogador_nome', 'clube_id', 'clube_nome', 'saldo_liquido']]

    # Retornar apenas quem teve saldo negativo (perdeu)
    return saldos[saldos['saldo_liquido'] < 0].copy()


def distribuir_ressarcimento(vitimas, valor_disponivel):
    '''
    Distribui o valor retido do fraudador proporcionalmente entre as vítimas.

    Aplica um teto: nenhuma vítima recebe mais do que perdeu.
    Os valores são truncados em 2 casas decimais (sem arredondamento).

    Args:
        vitimas (DataFrame): DataFrame com jogador_id, jogador_nome, clube_id, saldo_liquido.
        valor_disponivel (float): Valor total disponível para ressarcir (em reais).

    Returns:
        DataFrame com coluna adicional: ressarcimento.
    '''
    if len(vitimas) == 0 or valor_disponivel <= 0:
        vitimas['ressarcimento'] = 0.0
        return vitimas

    total_perdas = vitimas['saldo_liquido'].abs().sum()

    vitimas['proporcao'] = vitimas['saldo_liquido'].abs() / total_perdas
    vitimas['ressarcimento_bruto'] = vitimas['proporcao'] * valor_disponivel

    # Teto: ninguém recebe mais do que perdeu
    vitimas['ressarcimento'] = vitimas.apply(
        lambda row: min(row['ressarcimento_bruto'], abs(row['saldo_liquido'])),
        axis=1
    )

    # Truncar em 2 casas decimais
    vitimas['ressarcimento'] = vitimas['ressarcimento'].apply(
        lambda x: math.floor(x * 100) / 100
    )

    return vitimas


def criar_excel_ressarcimento(resultados_por_fraudador, ressarcimentos_imediatos, ressarcimentos_futuros, fraudadores_editados, valor_minimo):
    '''
    Cria um arquivo Excel com múltiplas abas contendo todos os dados de ressarcimento.

    Args:
        resultados_por_fraudador (dict): Resultados por fraudador_id.
        ressarcimentos_imediatos (list[dict]): Ressarcimentos acima do valor mínimo.
        ressarcimentos_futuros (list[dict]): Ressarcimentos abaixo do valor mínimo (acumulados).
        fraudadores_editados (DataFrame): DataFrame com os fraudadores e valores configurados.
        valor_minimo (float): Valor mínimo configurado para ressarcimento imediato.

    Returns:
        bytes: Arquivo Excel em bytes para download.
    '''
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # ===== ABA 1: RESUMO GERAL =====
        dados_resumo = {
            'Métrica': [
                'Total de Fraudadores Analisados',
                'Fraudadores com Valor Retido',
                'Total Disponível para Ressarcimento',
                'Total de Ressarcimentos Imediatos',
                'Total de Ressarcimentos Futuros',
                'Quantidade de Vítimas (Imediato)',
                'Quantidade de Vítimas (Futuro)',
                'Valor Mínimo Configurado'
            ],
            'Valor': [
                len(fraudadores_editados),
                len([r for r in resultados_por_fraudador.values() if r['total_ressarcido'] > 0]),
                f'R$ {sum([r["valor_disponivel"] for r in resultados_por_fraudador.values()]):,.2f}',
                f'R$ {sum([r["ressarcimento_total"] for r in ressarcimentos_imediatos]):,.2f}' if ressarcimentos_imediatos else 'R$ 0.00',
                f'R$ {sum([r["ressarcimento_total"] for r in ressarcimentos_futuros]):,.2f}' if ressarcimentos_futuros else 'R$ 0.00',
                len(ressarcimentos_imediatos),
                len(ressarcimentos_futuros),
                f'R$ {valor_minimo:.2f}'
            ]
        }
        pd.DataFrame(dados_resumo).to_excel(writer, sheet_name='Resumo', index=False)

        # ===== ABA 2: RESSARCIMENTOS IMEDIATOS =====
        if ressarcimentos_imediatos:
            df_imediatos = pd.DataFrame(ressarcimentos_imediatos)
            df_imediatos = df_imediatos[['jogador_id', 'jogador_nome', 'clube_id', 'clube_nome', 'ressarcimento_novo', 'acumulado_anterior', 'ressarcimento_total']]
            df_imediatos.columns = ['ID Jogador', 'Nome Jogador', 'ID Clube', 'Nome Clube', 'Ressarcimento Novo (R$)', 'Acumulado Anterior (R$)', 'Total (R$)']
            df_imediatos.to_excel(writer, sheet_name='Ressarcimentos Imediatos', index=False)

        # ===== ABA 3: RESSARCIMENTOS FUTUROS =====
        if ressarcimentos_futuros:
            df_futuros = pd.DataFrame(ressarcimentos_futuros)
            df_futuros = df_futuros[['jogador_id', 'jogador_nome', 'clube_id', 'clube_nome', 'ressarcimento_novo', 'acumulado_anterior', 'ressarcimento_total']]
            df_futuros.columns = ['ID Jogador', 'Nome Jogador', 'ID Clube', 'Nome Clube', 'Ressarcimento Novo (R$)', 'Acumulado Anterior (R$)', 'Total (R$)']
            df_futuros.to_excel(writer, sheet_name='Ressarcimentos Futuros', index=False)

        # ===== ABAS POR FRAUDADOR =====
        for fraudador_id, resultado in resultados_por_fraudador.items():
            if len(resultado['vitimas']) > 0:
                fraudador_nome = resultado['fraudador_nome']
                fraudador_nome_limpo = re.sub(r'[/\\*?:\[\]]', '', fraudador_nome)
                sheet_name = f'Fraudador {fraudador_nome_limpo} ({fraudador_id})'[:31]

                df_fraudador = resultado['vitimas'][[
                    'jogador_id', 'jogador_nome', 'clube_id', 'clube_nome', 'saldo_liquido', 'ressarcimento', 'status'
                ]].copy()
                df_fraudador.columns = ['ID Jogador', 'Nome Jogador', 'ID Clube', 'Nome Clube', 'Perda Líquida (R$)', 'Ressarcimento Novo (R$)', 'Status']
                df_fraudador.to_excel(writer, sheet_name=sheet_name, index=False)

    output.seek(0)
    return output.getvalue()
