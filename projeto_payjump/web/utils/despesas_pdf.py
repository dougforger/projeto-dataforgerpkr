"""Gerador de PDF para o Relatório Financeiro de despesas Security.

Estrutura do PDF gerado:
  1. Cabeçalho institucional (logo + linha âmbar) — renderizado pelo callback
     do pdf_builder em todas as páginas.
  2. Título e período de referência.
  3. Seção "Filtros Aplicados" — tabela de 2 colunas (Filtro | Selecionado).
  4. Seção "Resumo" — imagem matplotlib com 4 cards de métricas visuais:
     linha âmbar, rótulo cinza, valor em destaque, sub-rótulo percentual.
  5. Seção "Saldo do Período" — gráfico de barras horizontais com saldo
     por Dia de Fechamento (uma barra por semana/período), gerado com
     matplotlib e embutido como PNG.
  6. Seção "Por Clube" — tabela agregada por Clube com Nº de Lançamentos
     e Saldo Total, ordenada do maior débito (saldo mais negativo) para
     o maior crédito.
  7. Rodapé institucional (site + e-mail) — renderizado pelo callback.

Convenção de estilo:
  - Toda tabela deve ser precedida de um Paragraph com ESTILO_LEGENDA
    (itálico 9pt cinza). Isso é padrão em todos os PDFs do sistema.
  - Fontes: CalibriLight (normal) e CalibriLight-Bold (cabeçalho de tabela).
  - Paleta institucional âmbar (#F0A64D) para cabeçalhos de tabela e linhas.
"""

from __future__ import annotations

import io
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from reportlab.platypus import Image, PageBreak, Paragraph, Spacer

from .pdf_builder import (
    adicionar_tabela,
    finalizar_pdf,
    inicializar_pdf,
)
from .pdf_config import (
    ESTILO_CELULA,
    ESTILO_CELULA_NOWRAP,
    ESTILO_LEGENDA,
    ESTILO_PARAGRAFO,
    ESTILO_SECAO,
    LARGURA_PAGINA,
    COR_AZUL_CREDITO_HEX,
    COR_BORDA_HEX,
    COR_DESTAQUE_HEX,
    COR_TEXTO_HEX,
    COR_TEXTO_SUAVE_HEX,
    COR_VERMELHO_DEB_HEX,
    FP_BOLD_24,
    FP_LIGHT_9,
    FP_LIGHT_11,
    formatar_brl,
    formatar_data,
    texto_ou_traco,
)


# ─────────────────────────────────────────────────────────────────────────────
# Seção 1: Filtros Aplicados — tabela 2 colunas (Filtro | Selecionado)
# ─────────────────────────────────────────────────────────────────────────────

def _secao_filtros_aplicados(
    story: list,
    data_inicio: date,
    data_fim: date,
    filtro_tipo: str,
    filtro_clubes: list[str],
    filtro_categorias: list[str],
) -> None:
    """Adiciona ao story uma tabela 2 colunas com os filtros aplicados.

    Estrutura da tabela:
      Cabeçalho: Filtro | Selecionado
      Linhas:    Período | dd/mm/aaaa → dd/mm/aaaa
                 Tipo    | Todos / Créditos / Débitos
                 Clube / Liga | valor ou "Todos"
                 Categoria    | valor ou "Todas"

    Args:
        story:              Lista de elementos ReportLab (modificada in-place).
        data_inicio:        Data inicial do filtro de período.
        data_fim:           Data final do filtro de período.
        filtro_tipo:        String descritiva do tipo: 'Todos', 'Créditos', 'Débitos'.
        filtro_clubes:      Lista de clubes selecionados (vazia = todos).
        filtro_categorias:  Lista de categorias selecionadas (vazia = todas).
    """
    story.append(Paragraph('Filtros Aplicados', ESTILO_SECAO))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        'Critérios de filtragem utilizados na geração deste relatório.',
        ESTILO_LEGENDA,
    ))

    # Valores formatados para cada filtro
    periodo_selecionado = f'{formatar_data(data_inicio)} → {formatar_data(data_fim)}'
    clube_selecionado   = ', '.join(filtro_clubes) if filtro_clubes else 'Todos'
    cat_selecionada     = ', '.join(filtro_categorias) if filtro_categorias else 'Todas'

    # Montagem das linhas: cabeçalho + 4 linhas de dados
    linhas_filtros = [
        ['Filtro', 'Selecionado'],
        ['Período',     periodo_selecionado],
        ['Tipo',        filtro_tipo],
        ['Clube / Liga', clube_selecionado],
        ['Categoria',   cat_selecionada],
    ]

    # Converter cada célula em Paragraph para controle tipográfico
    linhas_paragrafos = [
        [Paragraph(celula, ESTILO_CELULA) for celula in linha]
        for linha in linhas_filtros
    ]

    # Larguras: 35% para a coluna "Filtro", 65% para "Selecionado"
    larguras_filtros = [LARGURA_PAGINA * 0.35, LARGURA_PAGINA * 0.65]

    adicionar_tabela(story, linhas_paragrafos, larguras_filtros, espacamento=16)


# ─────────────────────────────────────────────────────────────────────────────
# Seção 2: Resumo — cards de métricas visuais (matplotlib image)
# ─────────────────────────────────────────────────────────────────────────────

def _gerar_imagem_metricas(
    metricas: list[tuple[str, str, str]],
    largura_pts: float,
) -> io.BytesIO:
    """Gera uma imagem matplotlib com cards de métricas lado a lado.

    Cada card exibe:
      - Linha âmbar (#F0A64D) no topo do card como elemento de destaque.
      - Rótulo pequeno em cinza (Calibri Light 9pt) — nome da métrica.
      - Valor grande em negrito (Calibri Bold 24pt) — valor principal.
      - Sub-rótulo opcional em cinza (Calibri Light 9pt) — ex: percentual.

    Args:
        metricas:    Lista de tuplas (rotulo, valor_principal, sub_rotulo).
                     sub_rotulo pode ser string vazia.
        largura_pts: Largura disponível em pontos ReportLab (72 pt = 1 polegada).

    Returns:
        BytesIO com a imagem PNG pronta para embutir no PDF.
    """
    quantidade_cards = len(metricas)
    largura_inches   = largura_pts / 72
    # Altura fixa suficiente para os 3 elementos de texto + linha âmbar
    # Aumentada para evitar sobreposição de texto
    altura_inches    = 1.6

    fig, eixos = plt.subplots(
        1, quantidade_cards,
        figsize=(largura_inches, altura_inches),
        facecolor='white',
    )

    # Garantir que eixos seja sempre uma lista, mesmo com 1 card
    if quantidade_cards == 1:
        eixos = [eixos]

    for eixo, (rotulo, valor_principal, sub_rotulo) in zip(eixos, metricas):
        eixo.set_facecolor('white')
        eixo.set_xlim(0, 1)
        eixo.set_ylim(0, 1)
        eixo.axis('off')

        # Linha âmbar horizontal no topo do card (destaque visual)
        eixo.axhline(y=0.93, xmin=0.03, xmax=0.97, color=COR_DESTAQUE_HEX, linewidth=3)

        # Rótulo da métrica — pequeno, cinza, acima do valor
        kwargs_rotulo = dict(
            x=0.5, y=0.80,
            s=rotulo,
            ha='center', va='top',
            color=COR_TEXTO_SUAVE_HEX,
        )
        if FP_LIGHT_9:
            kwargs_rotulo['fontproperties'] = FP_LIGHT_9
        else:
            kwargs_rotulo['fontsize'] = 9
        eixo.text(**kwargs_rotulo)

        # Valor principal — grande, negrito, cor do texto
        kwargs_valor = dict(
            x=0.5, y=0.50,
            s=valor_principal,
            ha='center', va='center',
            color=COR_TEXTO_HEX,
        )
        if FP_BOLD_24:
            kwargs_valor['fontproperties'] = FP_BOLD_24
        else:
            kwargs_valor['fontsize'] = 20
            kwargs_valor['fontweight'] = 'bold'
        eixo.text(**kwargs_valor)

        # Sub-rótulo opcional — percentual ou informação secundária
        if sub_rotulo:
            kwargs_sub = dict(
                x=0.5, y=0.12,
                s=sub_rotulo,
                ha='center', va='bottom',
                color=COR_TEXTO_SUAVE_HEX,
            )
            if FP_LIGHT_9:
                kwargs_sub['fontproperties'] = FP_LIGHT_9
            else:
                kwargs_sub['fontsize'] = 9
            eixo.text(**kwargs_sub)

    fig.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.02, wspace=0.08)

    buffer_imagem = io.BytesIO()
    fig.savefig(buffer_imagem, format='png', dpi=150, bbox_inches='tight',
                facecolor='white')
    plt.close(fig)
    buffer_imagem.seek(0)
    return buffer_imagem


def _secao_resumo_metricas(
    story: list,
    df_filtrado: pd.DataFrame,
) -> None:
    """Adiciona ao story uma seção visual com 4 cards de métricas financeiras.

    Os 4 cards exibidos são:
      - Total de Lançamentos: contagem de linhas no DataFrame filtrado.
      - Créditos (Ressarcimentos): soma dos valores positivos, com percentual.
      - Débitos (Multas): soma absoluta dos valores negativos, com percentual.
      - Saldo Líquido: soma algébrica de todos os valores.

    Args:
        story:        Lista de elementos ReportLab (modificada in-place).
        df_filtrado:  DataFrame já filtrado conforme critérios do usuário.
    """
    story.append(Paragraph('Resumo', ESTILO_SECAO))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        'Métricas calculadas sobre o conjunto de lançamentos filtrado.',
        ESTILO_LEGENDA,
    ))

    total_lancamentos = len(df_filtrado)
    soma_creditos     = df_filtrado.loc[df_filtrado['Valor'] > 0, 'Valor'].sum()
    soma_debitos      = abs(df_filtrado.loc[df_filtrado['Valor'] < 0, 'Valor'].sum())
    saldo_liquido     = abs(df_filtrado['Valor'].sum())

    # Cálculo dos percentuais em relação ao total movimentado (créditos + débitos)
    total_movimentado = soma_creditos + soma_debitos
    pct_creditos      = (soma_creditos / total_movimentado * 100) if total_movimentado else 0.0
    pct_debitos       = (soma_debitos  / total_movimentado * 100) if total_movimentado else 0.0

    # 2 linhas de 2 cards: linha 1 = totais gerais, linha 2 = créditos/débitos
    grupos_metricas = [
        [
            ('Total de Lançamentos', str(total_lancamentos),       ''),
            ('Saldo Líquido',        formatar_brl(saldo_liquido), ''),
        ],
        [
            ('Créditos', formatar_brl(soma_creditos), f'{pct_creditos:.1f}% do total'),
            ('Débitos',  formatar_brl(soma_debitos),  f'{pct_debitos:.1f}% do total'),
        ],
    ]

    from PIL import Image as PILImage
    for grupo in grupos_metricas:
        buf_grupo = _gerar_imagem_metricas(grupo, LARGURA_PAGINA)
        pil_grupo = PILImage.open(buf_grupo)
        larg_px, alt_px = pil_grupo.size
        buf_grupo.seek(0)
        altura_prop = LARGURA_PAGINA * alt_px / larg_px
        story.append(Image(buf_grupo, width=LARGURA_PAGINA, height=altura_prop))
        # story.append(Spacer(1, 4))


# ─────────────────────────────────────────────────────────────────────────────
# Seção 3: Gráfico — saldo por Dia de Fechamento (uma barra por período)
# ─────────────────────────────────────────────────────────────────────────────

def _gerar_grafico_saldo_por_periodo(
    df_lancamentos: pd.DataFrame,
    largura_pts: float,
) -> Optional[io.BytesIO]:
    """Gera um gráfico de barras horizontais com saldo por Dia de Fechamento.

    Cada barra representa a soma dos lançamentos de um único Dia de Fechamento
    (ex: uma semana). Barras azuis indicam saldo positivo (crédito), barras
    vermelhas indicam saldo negativo (débito). Os rótulos de valor absoluto
    são exibidos fora de cada barra.

    Args:
        df_lancamentos: DataFrame filtrado com colunas 'Dia Fechamento' e 'Valor'.
        largura_pts:    Largura disponível no PDF em pontos ReportLab.

    Returns:
        BytesIO com a imagem PNG pronta para embutir, ou None se o DataFrame
        estiver vazio ou sem coluna 'Dia Fechamento'.
    """
    if df_lancamentos.empty or 'Dia Fechamento' not in df_lancamentos.columns:
        return None

    df_grafico = df_lancamentos.copy()
    df_grafico['Dia Fechamento'] = pd.to_datetime(df_grafico['Dia Fechamento'], errors='coerce')
    df_grafico = df_grafico.dropna(subset=['Dia Fechamento', 'Valor'])

    if df_grafico.empty:
        return None

    # Agrupamento por Dia de Fechamento exato — rótulo "dd/mm/aaaa"
    df_agrupado = (
        df_grafico.groupby('Dia Fechamento')['Valor']
        .sum()
        .reset_index()
        .sort_values('Dia Fechamento')   # ordem cronológica
    )

    rotulos_periodo = df_agrupado['Dia Fechamento'].dt.strftime('%d/%m/%Y').tolist()
    valores_saldo   = df_agrupado['Valor'].tolist()
    cores_barras    = [COR_AZUL_CREDITO_HEX if v >= 0 else COR_VERMELHO_DEB_HEX for v in valores_saldo]

    # Dimensões: altura cresce com o número de períodos (mín. 3 polegadas)
    largura_inches = largura_pts / 72
    altura_inches  = max(3.0, len(rotulos_periodo) * 0.5)

    fig, eixo = plt.subplots(figsize=(largura_inches, altura_inches), facecolor='white')

    barras = eixo.barh(rotulos_periodo, valores_saldo, color=cores_barras, height=0.55)
    eixo.invert_yaxis()   # período mais antigo no topo

    # Rótulos de valor absoluto dentro das barras
    valor_maximo_abs = max(abs(v) for v in valores_saldo) if valores_saldo else 1
    for barra_item, valor_item in zip(barras, valores_saldo):
        deslocamento_x = -valor_maximo_abs * 0.02 if valor_item >= 0 else valor_maximo_abs * 0.02
        alinhamento_h  = 'right'                   if valor_item >= 0 else 'left'
        barra_x_fim    = barra_item.get_width()
        texto_rotulo   = formatar_brl(abs(valor_item))

        kwargs_texto = dict(
            x=barra_x_fim + deslocamento_x,
            y=barra_item.get_y() + barra_item.get_height() / 2,
            s=texto_rotulo,
            va='center', ha=alinhamento_h,
            color='white',
        )
        if FP_LIGHT_9:
            kwargs_texto['fontproperties'] = FP_LIGHT_9
        else:
            kwargs_texto['fontsize'] = 9
        eixo.text(**kwargs_texto)

    # Estética dos eixos
    kwargs_xlabel = dict(xlabel='Saldo (R$)', color=COR_TEXTO_SUAVE_HEX)
    if FP_LIGHT_11:
        kwargs_xlabel['fontproperties'] = FP_LIGHT_11
    eixo.set_xlabel(**kwargs_xlabel)

    eixo.xaxis.set_major_formatter(
        mticker.FuncFormatter(
            lambda x, _: f'{x/1000:.0f} Mil' if abs(x) >= 1000 else f'{x:.0f}'
        )
    )
    eixo.grid(axis='x', color=COR_BORDA_HEX, linewidth=0.4, alpha=0.6, zorder=0)
    eixo.set_axisbelow(True)
    eixo.axvline(0, color=COR_BORDA_HEX, linewidth=0.8, linestyle='--')
    eixo.tick_params(colors=COR_TEXTO_SUAVE_HEX)
    eixo.spines['top'].set_visible(False)
    eixo.spines['right'].set_visible(False)
    eixo.spines['left'].set_color(COR_BORDA_HEX)
    eixo.spines['bottom'].set_color(COR_BORDA_HEX)

    if FP_LIGHT_9:
        plt.setp(eixo.get_xticklabels(), fontproperties=FP_LIGHT_9,  color=COR_TEXTO_SUAVE_HEX)
        plt.setp(eixo.get_yticklabels(), fontproperties=FP_LIGHT_11, color=COR_TEXTO_HEX)

    # Legenda manual: azul = crédito, vermelho = débito (abaixo do gráfico)
    from matplotlib.patches import Patch
    elementos_legenda = [
        Patch(facecolor=COR_AZUL_CREDITO_HEX, label='Crédito (Ressarcimento)'),
        Patch(facecolor=COR_VERMELHO_DEB_HEX, label='Débito (Multa)'),
    ]
    kwargs_legenda = dict(
        handles=elementos_legenda,
        loc='upper center',
        bbox_to_anchor=(0.5, -0.12),
        ncol=2,
        frameon=False,
        fontsize=9,
    )
    if FP_LIGHT_9:
        kwargs_legenda['prop'] = FP_LIGHT_9
    eixo.legend(**kwargs_legenda)

    fig.tight_layout(pad=0.8)

    buffer_png = io.BytesIO()
    fig.savefig(buffer_png, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buffer_png.seek(0)
    return buffer_png


def _secao_grafico_saldo_periodo(
    story: list,
    df_filtrado: pd.DataFrame,
) -> None:
    """Adiciona ao story o gráfico de saldo por Dia de Fechamento.

    Cada barra do gráfico corresponde a um Dia de Fechamento distinto
    (tipicamente uma semana de jogo). O título da seção é "Saldo do Período".

    Args:
        story:        Lista de elementos ReportLab (modificada in-place).
        df_filtrado:  DataFrame filtrado com colunas 'Dia Fechamento' e 'Valor'.
    """
    story.append(PageBreak())
    story.append(Paragraph('Saldo do Período', ESTILO_SECAO))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        'Saldo líquido por semana (Dia de Fechamento). Azul = crédito; vermelho = débito.',
        ESTILO_LEGENDA,
    ))

    buffer_grafico = _gerar_grafico_saldo_por_periodo(df_filtrado, LARGURA_PAGINA)
    if buffer_grafico is None:
        story.append(Paragraph(
            'Dados insuficientes para gerar o gráfico.',
            ESTILO_PARAGRAFO,
        ))
    else:
        from PIL import Image as PILImage
        imagem_pil_grafico = PILImage.open(buffer_grafico)
        largura_px_grafico, altura_px_grafico = imagem_pil_grafico.size
        buffer_grafico.seek(0)

        altura_proporcional_grafico = LARGURA_PAGINA * altura_px_grafico / largura_px_grafico
        imagem_rl_grafico = Image(
            buffer_grafico,
            width=LARGURA_PAGINA,
            height=altura_proporcional_grafico,
        )
        story.append(imagem_rl_grafico)

    story.append(Spacer(1, 12))


# ─────────────────────────────────────────────────────────────────────────────
# Seção 4: Tabela agregada por Clube
# ─────────────────────────────────────────────────────────────────────────────

def _secao_tabela_por_clube(
    story: list,
    df_filtrado: pd.DataFrame,
) -> None:
    """Adiciona ao story uma tabela com o resumo financeiro agrupado por Clube e Liga.

    A tabela exibe quatro colunas:
      - Clube: nome do clube (agrupador).
      - Liga: nome da liga associada ao clube.
      - Nº Lançamentos: quantidade de registros naquele clube.
      - Saldo Total: soma algébrica dos valores do clube.

    Os clubes são ordenados de forma crescente pelo Saldo Total — ou seja,
    os clubes com maior multa líquida (saldo mais negativo) aparecem primeiro,
    facilitando a identificação dos maiores problemas financeiros.

    Uma linha de rodapé "TOTAL" exibe as somas gerais da tabela.

    Args:
        story:        Lista de elementos ReportLab (modificada in-place).
        df_filtrado:  DataFrame filtrado com colunas 'Clube', 'Liga' e 'Valor'.
    """
    story.append(PageBreak())
    story.append(Paragraph('Por Clube', ESTILO_SECAO))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        'Resumo financeiro agrupado por clube e liga, ordenado do maior débito para o maior crédito.',
        ESTILO_LEGENDA,
    ))

    # Validação: verificar se as colunas necessárias existem
    if 'Clube' not in df_filtrado.columns or 'Valor' not in df_filtrado.columns:
        story.append(Paragraph('Dados insuficientes para gerar a tabela por clube.', ESTILO_PARAGRAFO))
        return

    # Verificar se a coluna Liga existe
    tem_coluna_liga = 'Liga' in df_filtrado.columns

    # Agrupar por Clube (e Liga, se disponível), calculando contagem e soma
    if tem_coluna_liga:
        df_por_clube = (
            df_filtrado.groupby(['Clube', 'Liga'], dropna=False)['Valor']
            .agg(quantidade_lancamentos='count', saldo_total='sum')
            .reset_index()
            .sort_values('saldo_total', ascending=True)
        )
        df_por_clube['Clube'] = df_por_clube['Clube'].fillna('Sem Clube')
        df_por_clube['Liga'] = df_por_clube['Liga'].fillna('—')
    else:
        df_por_clube = (
            df_filtrado.groupby('Clube', dropna=False)['Valor']
            .agg(quantidade_lancamentos='count', saldo_total='sum')
            .reset_index()
            .sort_values('saldo_total', ascending=True)
        )
        df_por_clube['Clube'] = df_por_clube['Clube'].fillna('Sem Clube')

    # Calcular totais para a linha de rodapé
    total_geral_lancamentos = int(df_por_clube['quantidade_lancamentos'].sum())
    total_geral_saldo       = df_por_clube['saldo_total'].sum()

    # Cabeçalho da tabela (com ou sem coluna Liga)
    if tem_coluna_liga:
        cabecalho_clube = ['Clube', 'Liga', 'Nº Lançamentos', 'Saldo Total']
        larguras_clube = [
            LARGURA_PAGINA * 0.35,
            LARGURA_PAGINA * 0.30,
            LARGURA_PAGINA * 0.175,
            LARGURA_PAGINA * 0.175,
        ]
    else:
        cabecalho_clube = ['Clube', 'Nº Lançamentos', 'Saldo Total']
        larguras_clube = [
            LARGURA_PAGINA * 0.50,
            LARGURA_PAGINA * 0.25,
            LARGURA_PAGINA * 0.25,
        ]

    # Linhas de dados
    linhas_tabela_clube: list = [
        [Paragraph(cab, ESTILO_CELULA) for cab in cabecalho_clube]
    ]
    for _, linha_clube in df_por_clube.iterrows():
        nome_clube         = texto_ou_traco(linha_clube['Clube'])
        qtd_lancamentos    = str(int(linha_clube['quantidade_lancamentos']))
        saldo_formatado    = formatar_brl(linha_clube['saldo_total'])

        if tem_coluna_liga:
            nome_liga = texto_ou_traco(linha_clube['Liga'])
            linhas_tabela_clube.append([
                Paragraph(nome_clube,       ESTILO_CELULA),
                Paragraph(nome_liga,         ESTILO_CELULA),
                Paragraph(qtd_lancamentos,   ESTILO_CELULA_NOWRAP),
                Paragraph(saldo_formatado,   ESTILO_CELULA_NOWRAP),
            ])
        else:
            linhas_tabela_clube.append([
                Paragraph(nome_clube,       ESTILO_CELULA),
                Paragraph(qtd_lancamentos,  ESTILO_CELULA_NOWRAP),
                Paragraph(saldo_formatado,  ESTILO_CELULA_NOWRAP),
            ])

    # Linha de totais (rodapé em negrito)
    if tem_coluna_liga:
        linhas_tabela_clube.append([
            Paragraph('<b>TOTAL</b>',                        ESTILO_CELULA),
            Paragraph('',                                    ESTILO_CELULA),
            Paragraph(f'<b>{total_geral_lancamentos}</b>',   ESTILO_CELULA_NOWRAP),
            Paragraph(f'<b>{formatar_brl(total_geral_saldo)}</b>', ESTILO_CELULA_NOWRAP),
        ])
    else:
        linhas_tabela_clube.append([
            Paragraph('<b>TOTAL</b>',                        ESTILO_CELULA),
            Paragraph(f'<b>{total_geral_lancamentos}</b>',   ESTILO_CELULA_NOWRAP),
            Paragraph(f'<b>{formatar_brl(total_geral_saldo)}</b>', ESTILO_CELULA_NOWRAP),
        ])

    adicionar_tabela(story, linhas_tabela_clube, larguras_clube, espacamento=8)


# ─────────────────────────────────────────────────────────────────────────────
# Função pública principal
# ─────────────────────────────────────────────────────────────────────────────

def gerar_pdf_relatorio_financeiro(
    df_filtrado: pd.DataFrame,
    data_inicio: date,
    data_fim: date,
    filtro_tipo: str = 'Todos',
    filtro_clubes: Optional[list[str]] = None,
    filtro_categorias: Optional[list[str]] = None,
) -> bytes:
    """Gera o PDF completo do Relatório Financeiro e retorna os bytes.

    Monta sequencialmente as seções:
      1. Filtros aplicados (tabela 2 colunas).
      2. Resumo com cards visuais de métricas.
      3. Gráfico de saldo por Dia de Fechamento.
      4. Tabela agregada por Clube.

    O cabeçalho e rodapé institucionais são adicionados pelo callback do
    pdf_builder em todas as páginas do documento.

    Args:
        df_filtrado:       DataFrame já filtrado e pronto para exibição.
                           Deve ter ao menos as colunas 'Dia Fechamento' e 'Valor'.
        data_inicio:       Data inicial utilizada no filtro de período.
        data_fim:          Data final utilizada no filtro de período.
        filtro_tipo:       Descrição do filtro de tipo aplicado.
                           Ex: 'Todos', 'Créditos (Ressarcimentos)', 'Débitos (Multas)'.
        filtro_clubes:     Lista de clubes/ligas selecionados. None ou lista vazia
                           indica que todos foram incluídos.
        filtro_categorias: Lista de categorias selecionadas. None ou lista vazia
                           indica que todas foram incluídas.

    Returns:
        Bytes do PDF gerado, prontos para uso em st.download_button().
    """
    filtro_clubes     = filtro_clubes     or []
    filtro_categorias = filtro_categorias or []

    titulo_relatorio = (
        f'Relatório Financeiro — '
        f'{formatar_data(data_inicio)} a {formatar_data(data_fim)}'
    )

    buffer_pdf, doc, story = inicializar_pdf(
        protocolo='',
        titulo_completo=titulo_relatorio,
    )

    # ── Seção 1: Filtros aplicados (tabela 2 colunas) ─────────────────────────
    _secao_filtros_aplicados(
        story,
        data_inicio=data_inicio,
        data_fim=data_fim,
        filtro_tipo=filtro_tipo,
        filtro_clubes=filtro_clubes,
        filtro_categorias=filtro_categorias,
    )

    if df_filtrado.empty:
        story.append(Paragraph(
            'Nenhum lançamento encontrado para os filtros selecionados.',
            ESTILO_PARAGRAFO,
        ))
    else:
        # ── Seção 2: Cards visuais de métricas ───────────────────────────────
        _secao_resumo_metricas(story, df_filtrado)

        # ── Seção 3: Gráfico de saldo por Dia de Fechamento ──────────────────
        _secao_grafico_saldo_periodo(story, df_filtrado)

        # ── Seção 4: Tabela agregada por Clube ───────────────────────────────
        _secao_tabela_por_clube(story, df_filtrado)

    buffer_final = finalizar_pdf(buffer_pdf, doc, story)
    return buffer_final.read()
