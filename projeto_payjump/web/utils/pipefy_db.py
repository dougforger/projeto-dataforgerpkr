"""Persistência dos cards Pipefy em SQLite.

Segue o padrão de utils/database.py: SQLAlchemy declarativo, Session/try/finally,
banco em data/pipefy.db, inicialização automática no import.
"""
import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import Column, DateTime, Integer, String, Date, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ===== CONFIGURAÇÃO DO BANCO =====
DB_PATH = Path(__file__).parent.parent / 'data' / 'pipefy.db'
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Base = declarative_base()
Session = sessionmaker(bind=engine)


# ===== MODELOS (TABELAS) =====

class PipefyCard(Base):
    """Um card do pipe Security PKR."""
    __tablename__ = 'pipefy_cards'

    id        = Column(String, primary_key=True)
    criado_em = Column(Date)
    categoria = Column(String, nullable=True)
    tipo      = Column(String)
    resultado = Column(String)
    analista  = Column(String, nullable=True)

    def __repr__(self):
        return f'<PipefyCard {self.id} — {self.categoria} / {self.resultado}>'


class PipefySync(Base):
    """Registro de data/hora da última sincronização (sempre id=1)."""
    __tablename__ = 'pipefy_sync'

    id              = Column(Integer, primary_key=True)
    sincronizado_em = Column(DateTime)


# ===== INICIALIZAÇÃO =====

def inicializar_banco() -> None:
    """Cria as tabelas se não existirem. Chamada automaticamente no import."""
    Base.metadata.create_all(engine)


inicializar_banco()


# ===== FUNÇÕES DE ACESSO =====

def carregar_cards() -> pd.DataFrame:
    """Lê todos os cards do banco e retorna DataFrame com as colunas padrão.

    Retorna DataFrame vazio (mesmas colunas) se o banco ainda não tiver dados.
    """
    session = Session()
    try:
        cards = session.query(PipefyCard).all()
        if not cards:
            return pd.DataFrame(
                columns=['id', 'criado_em', 'categoria', 'tipo', 'resultado', 'analista']
            )
        return pd.DataFrame([{
            'id':        c.id,
            'criado_em': c.criado_em,
            'categoria': c.categoria,
            'tipo':      c.tipo,
            'resultado': c.resultado,
            'analista':  c.analista,
        } for c in cards])
    finally:
        session.close()


def sincronizar_cards(df: pd.DataFrame) -> tuple[int, int]:
    """Upsert de todos os cards do DataFrame no banco.

    Cards novos são inseridos; cards existentes têm todos os campos atualizados
    (garante que alterações de resultado, analista, etc. sejam capturadas).

    Returns:
        (inseridos, atualizados): contagem de cards novos e de cards já existentes.
    """
    if df.empty:
        return 0, 0

    # Identifica quais IDs já existem para separar inserções de atualizações
    session = Session()
    try:
        ids_existentes = {row[0] for row in session.query(PipefyCard.id).all()}
    finally:
        session.close()

    ids_novos = set(df['id']) - ids_existentes
    inseridos  = len(ids_novos)
    atualizados = len(df) - inseridos

    # Prepara registros — criado_em (datetime.date) convertido para ISO string
    registros = [
        {
            'id':        row['id'],
            'criado_em': row['criado_em'].isoformat() if row['criado_em'] is not None else None,
            'categoria': row['categoria'] if pd.notna(row.get('categoria')) else None,
            'tipo':      row['tipo'],
            'resultado': row['resultado'],
            'analista':  row['analista']  if pd.notna(row.get('analista'))  else None,
        }
        for _, row in df.iterrows()
    ]

    # INSERT OR REPLACE: insere novos e substitui existentes pelo primary key
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
    session = Session()
    try:
        sync = session.query(PipefySync).filter_by(id=1).first()
        return sync.sincronizado_em if sync else None
    finally:
        session.close()


def registrar_sincronizacao() -> None:
    """Grava/atualiza o registro de sincronização (id=1) com o datetime atual."""
    session = Session()
    try:
        sync = session.query(PipefySync).filter_by(id=1).first()
        agora = datetime.datetime.now()
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
