'''
Módulo de gerenciamento de bando de dados SQLite para ressarcimentos.

Estrutura:
- ids_fraudadores: Lista com ID conhecidos como fraudadores.
- historico_ressarcimentos: Todos os ressarcimentos já processados.
- acumulados: Ressarcimentos pendentes abaixo do mínimo.
'''

from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from pathlib import Path

# ===== CONFIGURAÇÃO DO BANCO ======
# Caminho: web/data/ressarcimentos.db
DB_PATH = Path(__file__).parent.parent / 'data' / 'ressarcimento.db'

# Criar diretório se não existir
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Engine do SQLAlchemy
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)

# Base para os modelos
Base = declarative_base()

# Session make
Session = sessionmaker(bind=engine)

# ===== MODELOS (TABELAS) =====

class FraudadorIdentificado(Base):
    '''
    Tabela de ids identificados como fraudadores (blaklist).

    Inclui: bots, collusion, chip dumping, etc.
    Cada conta só pode aparecer uma vez (player_id único).
    '''
    __tablename__ = 'fraudadores_identificados'

    id = Column(Integer, primary_key=True, autoincrement=True)
    protocolo = Column(Integer, nullable=False, index=True)
    player_id = Column(Integer, unique=True, nullable=False, index=True)
    player_name = Column(String(200))
    club_id = Column(Integer)
    club_name = Column(String(200))
    data_identificacao = Column(Date, nullable=False)
    valor_total_retido = Column(Float, default=0.0)

    def __repr__(self):
        return f'<{self.player_name} ({self.player_id}) - Protocolo: {self.protocolo}>'
    
class HistoricoRessarcimento(Base):
    '''
    Histórico completo de todos os ressarcimentos já processados.

    Cada ressarcimento gera uma linha nova (não tem UNIQUE).
    '''
    __tablename__ = 'historico_ressarcimentos'

    id = Column(Integer, primary_key=True, autoincrement=True)
    protocolo = Column(Integer, nullable=False, index=True)
    data_ressarcimento = Column(Date, nullable=False, index=True)
    player_id = Column(Integer, nullable=False, index=True)
    player_name = Column(String(200))
    club_id = Column(Integer, index=True)
    club_name = Column(String(200))
    valor_ressarcido = Column(Float, nullable=False)
    tipo = Column(String(50)) # 'Imediato' ou 'Acumulado'
    referencia = Column(String(200)) # Ex: 'Semana 10/03'
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    def __repr__(self):
        return f'<Ressarcimento {self.player_id}: R$ {self.valor_ressarcido:.2f} - Protocolo: {self.protocolo}>'
    
class Acumulados(Base):
    '''
    Ressarcimentos pendentes (abaixo do valor mínimo definido)

    Cada jogador+clube só pode ter um registro (UNIQUE constraint).
    '''
    __tablename__ = 'acumulados'
    __table_args__ = [
        UniqueConstraint('player_id', 'club_id', name='uq_player_club')
    ]

    id = Column(Integer, primary_key=True, autoincrement=True)
    player_id = Column(Integer, nullable=False, index=True)
    club_id = Column(Integer, nullable=False, index=True)
    player_name = Column(String(200))
    club_name = Column(String(200))
    ressarcimento_acumulado = Column(Float, nullable=False)
    data_ultima_atualizacao = Column(Date, nullable=False)

    def __repr__(self):
        return f'<Acumulado {self.player_id}: R$ {self.ressarcimento_acumulado:.2f}>'
    
# =====  CRIAR TABELAS NO BANCO =====
def incializar_banco():
    '''
    Cria todas as tabelas no banco de dados.
    
    Se as tabelas já existirem, não faz nada.
    '''
    Base.metadata.create_all(engine)
    print(f'✅ Banco incializado em: {DB_PATH}')

# Inicialização automática ao importat o módulo
incializar_banco()