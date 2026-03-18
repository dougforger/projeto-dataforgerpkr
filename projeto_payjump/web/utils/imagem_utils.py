import os
import tempfile

import dataframe_image as dfi
import pandas as pd

# Paleta de cores institucional (mesma do PDF)
_ESTILOS_TABELA = [
    {
        'selector': 'table',
        'props': [
            ('border-collapse', 'collapse'),
            ('font-family', 'Calibri, Arial, sans-serif'),
            ('font-size', '13px'),
            ('border', '1px solid #DDDDDD'),
        ],
    },
    {
        'selector': 'th',
        'props': [
            ('background-color', '#F0A64D'),
            ('color', '#1C1C1C'),
            ('font-weight', 'bold'),
            ('padding', '7px 10px'),
            ('border-bottom', '2px solid #C47E20'),
            ('text-align', 'left'),
        ],
    },
    {
        'selector': 'td',
        'props': [
            ('color', '#1C1C1C'),
            ('padding', '6px 10px'),
            ('border-bottom', '1px solid #DDDDDD'),
            ('text-align', 'left'),
        ],
    },
    {
        'selector': 'tr:nth-child(even) td',
        'props': [('background-color', '#FEF6E8')],
    },
    {
        'selector': 'tr:nth-child(odd) td',
        'props': [('background-color', '#FFFFFF')],
    },
]


def gerar_imagem_df(df: pd.DataFrame, formatar_colunas: list[str] | None = None) -> bytes:
    """Exporta um DataFrame como PNG estilizado com a identidade visual da Suprema.

    Args:
        df: DataFrame já preparado para exibição (colunas e valores finais).
        formatar_colunas: lista de colunas numéricas para formatar com 2 casas decimais.

    Returns:
        Bytes da imagem PNG.
    """
    styled = df.style.set_table_styles(_ESTILOS_TABELA).hide(axis='index')

    if formatar_colunas:
        styled = styled.format({col: '{:,.2f}' for col in formatar_colunas if col in df.columns})

    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        caminho = tmp.name

    try:
        dfi.export(styled, caminho, table_conversion='chrome', dpi=200)
    except Exception:
        # Fallback para matplotlib se Playwright/Chrome não estiver disponível
        dfi.export(styled, caminho, table_conversion='matplotlib', dpi=200)

    with open(caminho, 'rb') as f:
        img_bytes = f.read()

    os.unlink(caminho)
    return img_bytes
