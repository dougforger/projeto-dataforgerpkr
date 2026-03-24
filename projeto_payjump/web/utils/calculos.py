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


def processar_planilhas_backend(df) -> tuple:
    '''
    Processa DataFrame combinado de planilhas "Player chips transaction record" do backend.

    Identifica as mãos onde TODAS as contas carregadas aparecem juntas e calcula:
    1. Soma total por conta (consolidando todas as mesas em comum).
    2. Totais por mesa (Association) para cada conta.
    3. Registros individuais de cada mão em comum.

    Args:
        df (DataFrame): DataFrame combinado de múltiplos arquivos XLSX do backend.

    Returns:
        tuple: (soma_total, por_mesa, maos_comuns) — três DataFrames com os resultados.
    '''
    df = df[df['Event'] == 'gameResult'].copy()

    # Extrair mesa (Game ID) e mão (Hand ID) do campo Association.
    # Formato do backend: "Game ID: 42090762Hand ID: 954159535"
    df['_mesa_id'] = pd.to_numeric(
        df['Association'].astype(str).str.extract(r'Game ID:\s*(\d+)', expand=False),
        errors='coerce',
    )
    df['_mao_id'] = pd.to_numeric(
        df['Association'].astype(str).str.extract(r'Hand ID:\s*(\d+)', expand=False),
        errors='coerce',
    )
    df = df.dropna(subset=['_mesa_id', '_mao_id'])

    n_contas = df['Player ID'].nunique()
    contagem = df.groupby('_mao_id')['Player ID'].nunique()
    ids_comuns = contagem[contagem == n_contas].index
    df_comuns = df[df['_mao_id'].isin(ids_comuns)].copy()

    # 1. Soma total por conta (grand total)
    soma_total = df_comuns.groupby(
        ['Player ID', 'Player Name', 'Club Name']
    ).agg(
        chip_change=('chip change', 'sum'),
        fee_change=('Total Fee change', 'sum'),
        n_maos=('_mao_id', 'nunique')
    ).reset_index()
    soma_total.columns = ['ID Jogador', 'Nome', 'Clube', 'Ganhos', 'Rake', 'Mãos em Comum']

    # 2. Totais por mesa para cada conta
    por_mesa = df_comuns.groupby(
        ['Player ID', 'Player Name', 'Club Name', '_mesa_id']
    ).agg(
        chip_change=('chip change', 'sum'),
        fee_change=('Total Fee change', 'sum'),
        n_maos=('_mao_id', 'nunique')
    ).reset_index()
    por_mesa.columns = ['ID Jogador', 'Nome', 'Clube', 'Mesa (Game ID)', 'Ganhos', 'Rake', 'Mãos em Comum']

    # 3. Registros individuais de mãos em comum
    maos_comuns = df_comuns[
        ['Player ID', 'Player Name', 'Club Name', '_mesa_id', '_mao_id', 'chip change', 'Total Fee change']
    ].sort_values(['_mao_id', 'Player ID']).copy()
    maos_comuns.columns = ['ID Jogador', 'Nome', 'Clube', 'Mesa (Game ID)', 'Hand ID', 'Ganhos', 'Rake']

    return soma_total, por_mesa, maos_comuns


def gerar_pdf_pontual(protocolo: str, soma_total, por_mesa, maos_comuns) -> bytes:
    '''
    Gera PDF de apuração pontual com três seções: soma total, por mesa e mãos em comum.

    Args:
        protocolo (str): Número do protocolo (usado no título e no nome do arquivo).
        soma_total (DataFrame): Totais por conta em todas as mesas em comum.
        por_mesa (DataFrame): Totais por conta por mesa (Association).
        maos_comuns (DataFrame): Registros individuais de mãos em comum.

    Returns:
        bytes: Conteúdo do PDF gerado.
    '''
    from reportlab.platypus import Paragraph
    from utils.pdf_builder import (
        inicializar_pdf, finalizar_pdf, adicionar_tabela,
        calcular_larguras_proporcional,
    )
    from utils.pdf_config import (
        ESTILO_LEGENDA, ESTILO_CELULA, ESTILO_CELULA_NOWRAP,
        ESTILO_TABELA_COMPACTO, LARGURA_PAGINA,
    )

    def _linhas(df, nowrap_cols=None):
        '''Converte DataFrame em lista de linhas para tabela ReportLab.'''
        nowrap_cols = nowrap_cols or []
        cab = list(df.columns)
        rows = [cab]
        for _, row in df.iterrows():
            r = []
            for col in cab:
                v = row[col]
                if isinstance(v, float):
                    r.append(f'{v:,.2f}')
                elif isinstance(v, int):
                    r.append(str(v))
                else:
                    estilo = ESTILO_CELULA_NOWRAP if col in nowrap_cols else ESTILO_CELULA
                    r.append(Paragraph(str(v) if v is not None else '—', estilo))
            rows.append(r)
        return rows

    buffer, doc, story = inicializar_pdf(
        protocolo, titulo_completo=f'Apuração #{protocolo}'
    )

    # ── Seção 1: Soma total ──────────────────────────────────────────────────
    story.append(Paragraph(
        'Resultado consolidado por conta ao longo de todas as mesas em comum.',
        ESTILO_LEGENDA,
    ))
    cols1 = list(soma_total.columns)
    larguras1 = calcular_larguras_proporcional(soma_total, cols1, cols1, LARGURA_PAGINA)
    adicionar_tabela(story, _linhas(soma_total, nowrap_cols=['ID Jogador']), larguras1)

    # ── Seção 2: Por mesa ────────────────────────────────────────────────────
    for mesa_id in sorted(por_mesa['Mesa (Game ID)'].unique()):
        df_mesa = por_mesa[por_mesa['Mesa (Game ID)'] == mesa_id].drop(columns=['Mesa (Game ID)']).copy()
        story.append(Paragraph(
            f'Mesa {mesa_id} — resultado por conta.',
            ESTILO_LEGENDA,
        ))
        cols2 = list(df_mesa.columns)
        larguras2 = calcular_larguras_proporcional(df_mesa, cols2, cols2, LARGURA_PAGINA)
        adicionar_tabela(story, _linhas(df_mesa, nowrap_cols=['ID Jogador']), larguras2)

    # ── Seção 3: Mãos em comum ───────────────────────────────────────────────
    story.append(Paragraph(
        'Todas as mãos jogadas em comum entre as contas investigadas.',
        ESTILO_LEGENDA,
    ))
    cols3 = list(maos_comuns.columns)
    larguras3 = calcular_larguras_proporcional(maos_comuns, cols3, cols3, LARGURA_PAGINA)
    nowrap3 = ['ID Jogador', 'Mesa (Game ID)', 'Hand ID']
    adicionar_tabela(
        story,
        _linhas(maos_comuns, nowrap_cols=nowrap3),
        larguras3,
        estilo=ESTILO_TABELA_COMPACTO,
    )

    return finalizar_pdf(buffer, doc, story).read()
