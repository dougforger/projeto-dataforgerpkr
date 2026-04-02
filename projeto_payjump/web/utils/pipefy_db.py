"""Persistência dos cards Pipefy.

Backends:
  • Supabase  — quando SUPABASE_URL e SUPABASE_KEY estiverem em st.secrets
               (Streamlit Cloud ou .streamlit/secrets.toml local).
               Acesso via REST/HTTPS — sem TCP na porta 5432.
  • SQLite    — fallback automático para desenvolvimento sem secrets.

Tabelas necessárias no Supabase (executar uma vez no SQL Editor):
    CREATE TABLE IF NOT EXISTS pipefy_cards (
        id TEXT PRIMARY KEY, criado_em DATE, categoria TEXT,
        tipo TEXT, resultado TEXT, analista TEXT
    );
    CREATE TABLE IF NOT EXISTS pipefy_sync (
        id INTEGER PRIMARY KEY, sincronizado_em TIMESTAMP WITH TIME ZONE
    );
"""
import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import pandas as pd

# ── SQLite (fallback local) ────────────────────────────────────────────────────
from sqlalchemy import Column, DateTime, Integer, String, Date, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

_DB_PATH = Path(__file__).parent.parent / 'data' / 'pipefy.db'

Base = declarative_base()


class PipefyCard(Base):
    __tablename__ = 'pipefy_cards'
    id        = Column(String, primary_key=True)
    criado_em = Column(Date)
    categoria = Column(String, nullable=True)
    tipo      = Column(String)
    resultado = Column(String)
    analista  = Column(String, nullable=True)


class PipefySync(Base):
    __tablename__ = 'pipefy_sync'
    id              = Column(Integer, primary_key=True)
    sincronizado_em = Column(DateTime)


_engine  = None
_Session = None


def _get_engine():
    global _engine, _Session
    if _engine is None:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _engine  = create_engine(f'sqlite:///{_DB_PATH}', echo=False)
        _Session = sessionmaker(bind=_engine)
        Base.metadata.create_all(_engine)
    return _engine


def _new_session():
    _get_engine()
    return _Session()


# ── Supabase (Streamlit Cloud / local com secrets.toml) ───────────────────────

from utils.supabase_client import TAMANHO_LOTE as _LOTE
from utils.supabase_client import criar_cliente as _supabase_client
from utils.supabase_client import paginar as _supabase_paginar
from utils.supabase_client import usar_supabase as _usar_supabase


# ── API pública ────────────────────────────────────────────────────────────────


def carregar_cards() -> pd.DataFrame:
    """Retorna todos os cards do banco como DataFrame."""
    _colunas = ['id', 'criado_em', 'categoria', 'tipo', 'resultado', 'analista']

    if _usar_supabase():
        client = _supabase_client()
        dados = _supabase_paginar(client, 'pipefy_cards')
        if not dados:
            return pd.DataFrame(columns=_colunas)
        df = pd.DataFrame(dados)[_colunas]
        df['criado_em'] = pd.to_datetime(df['criado_em']).dt.date
        return df

    # SQLite
    session = _new_session()
    try:
        cards = session.query(PipefyCard).all()
        if not cards:
            return pd.DataFrame(columns=_colunas)
        return pd.DataFrame([{
            'id': c.id, 'criado_em': c.criado_em, 'categoria': c.categoria,
            'tipo': c.tipo, 'resultado': c.resultado, 'analista': c.analista,
        } for c in cards])
    finally:
        session.close()


def sincronizar_cards(df: pd.DataFrame) -> tuple[int, int]:
    """Upsert completo dos cards. Retorna (inseridos, atualizados)."""
    if df.empty:
        return 0, 0

    registros = [
        {
            'id':        str(row['id']),
            'criado_em': row['criado_em'].isoformat()
                         if isinstance(row['criado_em'], datetime.date) else None,
            'categoria': row['categoria'] if pd.notna(row.get('categoria')) else None,
            'tipo':      row['tipo'],
            'resultado': row['resultado'],
            'analista':  row['analista']  if pd.notna(row.get('analista'))  else None,
        }
        for _, row in df.iterrows()
    ]

    if _usar_supabase():
        client = _supabase_client()
        # Conta existentes antes do upsert para calcular inseridos vs atualizados
        ids_existentes = {r['id'] for r in _supabase_paginar(client, 'pipefy_cards', 'id')}
        inseridos   = len(set(df['id'].astype(str)) - ids_existentes)
        atualizados = len(df) - inseridos
        # Upsert em lotes
        for i in range(0, len(registros), _LOTE):
            client.table('pipefy_cards').upsert(registros[i:i + _LOTE]).execute()
        return inseridos, atualizados

    # SQLite
    engine = _get_engine()
    session = _new_session()
    try:
        ids_existentes = {row[0] for row in session.query(PipefyCard.id).all()}
    finally:
        session.close()

    inseridos   = len(set(df['id'].astype(str)) - ids_existentes)
    atualizados = len(df) - inseridos

    with engine.begin() as conn:
        conn.execute(
            text(
                'INSERT OR REPLACE INTO pipefy_cards '
                '(id, criado_em, categoria, tipo, resultado, analista) '
                'VALUES (:id, :criado_em, :categoria, :tipo, :resultado, :analista)'
            ),
            registros,
        )
    return inseridos, atualizados


def obter_ultima_sincronizacao() -> datetime.datetime | None:
    """Retorna o datetime da última sincronização, ou None se nunca ocorreu."""
    if _usar_supabase():
        client = _supabase_client()
        resp = client.table('pipefy_sync').select('sincronizado_em').eq('id', 1).execute()
        if resp.data:
            return datetime.datetime.fromisoformat(resp.data[0]['sincronizado_em'])
        return None

    session = _new_session()
    try:
        sync = session.query(PipefySync).filter_by(id=1).first()
        return sync.sincronizado_em if sync else None
    finally:
        session.close()


def registrar_sincronizacao() -> None:
    """Grava/atualiza o registro de sincronização com o datetime atual."""
    sao_paulo_tz = ZoneInfo('America/Sao_Paulo')
    agora = datetime.datetime.now(sao_paulo_tz)

    if _usar_supabase():
        client = _supabase_client()
        client.table('pipefy_sync').upsert({
            'id': 1,
            'sincronizado_em': agora.isoformat(),
        }).execute()
        return

    session = _new_session()
    try:
        sync = session.query(PipefySync).filter_by(id=1).first()
        if sync:
            sync.sincronizado_em = agora
        else:
            session.add(PipefySync(id=1, sincronizado_em=agora))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
