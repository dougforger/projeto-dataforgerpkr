"""Persistência da tabela de ligas no Supabase.

Tabela necessária (executar uma vez no SQL Editor do Supabase):

    CREATE TABLE IF NOT EXISTS ligas (
        liga_id    INTEGER PRIMARY KEY,
        liga_nome  TEXT    NOT NULL,
        idioma     TEXT,
        handicap   NUMERIC,
        moeda      TEXT,
        taxa_liga  NUMERIC
    );

Notas de uso:
- carregar_ligas() tenta o Supabase primeiro. Se a tabela ainda não existir
  ou o Supabase não estiver configurado, faz fallback automático para o
  arquivo web/data/ligas.csv, sem interromper o fluxo.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from utils.supabase_client import TAMANHO_LOTE, criar_cliente, paginar, usar_supabase

_NOME_TABELA  = 'ligas'
_CSV_FALLBACK = Path(__file__).parent.parent / 'data' / 'ligas.csv'


def carregar_ligas() -> pd.DataFrame:
    """Retorna todas as ligas como DataFrame.

    Tenta carregar do Supabase. Se não estiver configurado ou a tabela
    ainda não existir, lê o arquivo web/data/ligas.csv como fallback.

    Returns:
        DataFrame com ao menos as colunas: liga_id, liga_nome.
    """
    if usar_supabase():
        try:
            cliente = criar_cliente()
            registros = paginar(cliente, _NOME_TABELA)
            if registros:
                df = pd.DataFrame(registros)
                df['liga_id'] = pd.to_numeric(df['liga_id'], errors='coerce').astype('Int64')
                return df
        except Exception:
            pass  # tabela inexistente ou erro de rede → fallback para CSV

    return pd.read_csv(_CSV_FALLBACK, dtype={'liga_id': int})


def sincronizar_ligas_csv() -> tuple[int, int]:
    """Lê o ligas.csv e faz upsert de todas as ligas no Supabase.

    Retorna (inseridas, atualizadas).

    Raises:
        RuntimeError: quando Supabase não está configurado.
    """
    if not usar_supabase():
        raise RuntimeError(
            'Supabase não configurado. Verifique SUPABASE_URL e SUPABASE_KEY '
            'em .streamlit/secrets.toml.'
        )

    df = pd.read_csv(_CSV_FALLBACK, dtype={'liga_id': int})

    # Renomeia taxa-liga → taxa_liga para bater com a coluna do banco
    if 'taxa-liga' in df.columns:
        df = df.rename(columns={'taxa-liga': 'taxa_liga'})

    cliente = criar_cliente()
    ids_existentes = {r['liga_id'] for r in paginar(cliente, _NOME_TABELA, 'liga_id')}

    registros = []
    for _, row in df.iterrows():
        registros.append({
            'liga_id':   int(row['liga_id']),
            'liga_nome': str(row['liga_nome']).strip(),
            'idioma':    str(row['idioma']).strip()   if pd.notna(row.get('idioma'))    else None,
            'handicap':  float(row['handicap'])       if pd.notna(row.get('handicap'))  else None,
            'moeda':     str(row['moeda']).strip()    if pd.notna(row.get('moeda'))     else None,
            'taxa_liga': float(row['taxa_liga'])      if pd.notna(row.get('taxa_liga')) else None,
        })

    inseridas   = sum(1 for r in registros if r['liga_id'] not in ids_existentes)
    atualizadas = len(registros) - inseridas

    for i in range(0, len(registros), TAMANHO_LOTE):
        cliente.table(_NOME_TABELA).upsert(registros[i:i + TAMANHO_LOTE]).execute()

    return inseridas, atualizadas


def inserir_liga(
    liga_id: int,
    liga_nome: str,
    idioma: str | None = None,
    handicap: float | None = None,
    moeda: str | None = None,
    taxa_liga: float | None = None,
) -> None:
    """Insere ou atualiza uma liga individualmente no Supabase.

    Args:
        liga_id:   ID único da liga (chave primária).
        liga_nome: Nome da liga.
        idioma:    Idioma principal da liga.
        handicap:  Valor do handicap.
        moeda:     Código da moeda (ex: 'BRL', 'USD').
        taxa_liga: Taxa da liga (0–1).

    Raises:
        RuntimeError: quando Supabase não está configurado.
    """
    if not usar_supabase():
        raise RuntimeError(
            'Supabase não configurado. Verifique SUPABASE_URL e SUPABASE_KEY '
            'em .streamlit/secrets.toml.'
        )

    cliente = criar_cliente()
    cliente.table(_NOME_TABELA).upsert({
        'liga_id':   liga_id,
        'liga_nome': liga_nome.strip(),
        'idioma':    idioma.strip() if idioma else None,
        'handicap':  handicap,
        'moeda':     moeda.strip() if moeda else None,
        'taxa_liga': taxa_liga,
    }).execute()
