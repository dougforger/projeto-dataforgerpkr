"""Persistência da tabela de clubes no Supabase.

Tabela necessária (executar uma vez no SQL Editor do Supabase):

    CREATE TABLE IF NOT EXISTS clubes (
        clube_id   INTEGER PRIMARY KEY,
        clube_nome TEXT    NOT NULL,
        liga_id    INTEGER NOT NULL,
        liga_nome  TEXT    NOT NULL
    );

Notas de uso:
- A sincronização faz UPSERT — clubes existentes são atualizados e novos
  são inseridos. Clubes removidos do Excel NÃO são apagados do banco.
- A leitura paginada garante que tabelas com mais de 500 registros sejam
  lidas corretamente, respeitando o limite padrão do PostgREST.
- Quando o Supabase não está configurado, carregar_clubes() faz fallback
  para o arquivo web/data/clubes.csv.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from utils.supabase_client import TAMANHO_LOTE, criar_cliente, paginar, usar_supabase

_NOME_TABELA  = 'clubes'
_CSV_FALLBACK = Path(__file__).parent.parent / 'data' / 'clubes.csv'

_COLUNAS = ['clube_id', 'clube_nome', 'liga_id', 'liga_nome']


def carregar_clubes() -> pd.DataFrame:
    """Retorna todos os clubes como DataFrame.

    Tenta carregar do Supabase. Se não estiver configurado, lê o CSV local.

    Returns:
        DataFrame com colunas: clube_id, clube_nome, liga_id, liga_nome.
    """
    if usar_supabase():
        cliente = criar_cliente()
        registros = paginar(cliente, _NOME_TABELA)
        if not registros:
            return pd.DataFrame(columns=_COLUNAS)
        df = pd.DataFrame(registros)[_COLUNAS]
        df['clube_id'] = pd.to_numeric(df['clube_id'], errors='coerce').astype('Int64')
        df['liga_id']  = pd.to_numeric(df['liga_id'],  errors='coerce').astype('Int64')
        return df

    # Fallback: CSV local
    return pd.read_csv(_CSV_FALLBACK, dtype={'clube_id': int, 'liga_id': int})


def sincronizar_clubes(df: pd.DataFrame) -> tuple[int, int]:
    """Faz upsert dos clubes no Supabase. Retorna (inseridos, atualizados).

    Args:
        df: DataFrame com colunas clube_id, clube_nome, liga_id, liga_nome.

    Returns:
        Tupla (inseridos, atualizados).

    Raises:
        RuntimeError: quando Supabase não está configurado.
    """
    if not usar_supabase():
        raise RuntimeError(
            'Supabase não configurado. Verifique SUPABASE_URL e SUPABASE_KEY '
            'em .streamlit/secrets.toml.'
        )

    cliente = criar_cliente()

    ids_existentes = {
        r['clube_id'] for r in paginar(cliente, _NOME_TABELA, 'clube_id')
    }

    registros = [
        {
            'clube_id':   int(row['clube_id']),
            'clube_nome': str(row['clube_nome']).strip(),
            'liga_id':    int(row['liga_id']),
            'liga_nome':  str(row['liga_nome']).strip(),
        }
        for _, row in df.iterrows()
    ]

    inseridos   = sum(1 for r in registros if r['clube_id'] not in ids_existentes)
    atualizados = len(registros) - inseridos

    for i in range(0, len(registros), TAMANHO_LOTE):
        cliente.table(_NOME_TABELA).upsert(registros[i:i + TAMANHO_LOTE]).execute()

    return inseridos, atualizados
