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
    status = Column(String(50)) # 'Imediato' ou 'Acumulado'
    referencia = Column(String(200)) # Ex: 'Semana 10/03'
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    def __repr__(self):
        return f'<Ressarcimento {self.player_id}: R$ {self.valor_ressarcido:.2f} - Protocolo: {self.protocolo}>'
    
class Acumulado(Base):
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

# ===== FUNÇÕES DE ACESSO - FRAUDADORES =====
def get_ids_fraudadores():
    '''
    Retorna lista de IDs de fraudadores conhecidos.

    Returns:
        list: Lista de player_ids que são fraudadores
    '''
    session = Session()
    try:
        fraudadores = session.query(FraudadorIdentificado.player_id).all()
        return [f[0] for f in fraudadores]
    finally:
        session.close()

def get_fraudadores_completo():
    '''
    Retorna todos os dados dos fraudadores identificados.

    Returns:
        list[dict]: Lista de dicionários com dados completos
    '''
    session = Session()
    try:
        fraudadores = session.query(FraudadorIdentificado).all()
        return [{
            'id': f.id,
            'player_id': f.player_id,
            'player_name': f.player_name,
            'club_id': f.club_id,
            'club_name': f.club_name,
            'data_identificacao': f.data_identificacao,
            'protocolo': f.protocolo,
            'valor_total_retido': f.valor_total_retido
        } for f in fraudadores]
    finally:
        session.close()

def adicionar_fraudador(player_id, player_name, club_id, club_name, protocolo, valor_retido):
    '''
    Adiciona ou atualiza um fraudador na lista.

    Args:
        player_id (int): ID do jogador
        player_name (str): Nome do jogador
        club_id (int): ID do clube
        club_name (str): Nome do clube
        protocolo (int): Número do protocolo do Pipefy (ex: 123456789)
        valor_retido (float): Valor total retido

    Returns:
        bool: True se sucesso
    '''
    session = Session()
    try:
        fraudador = FraudadorIdentificado(
            player_id = player_id,
            player_name = player_name,
            club_id = club_id,
            club_name = club_name,
            protocolo = protocolo,
            valor_total_retido = valor_retido
        )
        session.merge(fraudador) # merge = INSERT ou UPDATE se já existir
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f'Erro ao adicionar o fraudador: {e}')
        return False
    finally:
        session.close()

def adicionar_fraudadores_lote(fraudadores):
    '''
    Adiciona múltiplos fraudadores de uma vez.

    Args:
        fraudadores (list[dict]): Lista de dicionários com dados dos fraudadores

    Returns:
        int: Quantidade de fraudadores adicionados
    '''
    session = Session()
    try:
        count = 0
        for f in fraudadores:
            fraudador = FraudadorIdentificado(
                player_id = f['player_id'],
                player_name = f['player_name'],
                club_id = f['club_id'],
                club_name = f['club_name'],
                data_identificacao = datetime.now().date(),
                protocolo = f['protocolo'],
                valor_total_retido = f['valor_total_retido']
            )
            session.merge(fraudador)
            count += 1
        session.commit()
        return count
    except Exception as e:
        session.rollback()
        print(f'Erro ao adicionar fraudadores em lote: {e}')
        return 0
    finally:
        session.close()

def remover_fraudador(player_id):
    '''
    Remove um fraudador da lista.

    Args:
        player_id (int): ID do jogador a remover

    Returns:
        bool: True se removido, False se não encontrado
    '''
    session = Session()
    try:
        fraudador = session.query(FraudadorIdentificado).filter_by(player_id=player_id).first()
        if fraudador:
            session.delete(fraudador)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        print(f'Erro ao remover fraudador: {e}')
        return False
    finally:
        session.close()

# ===== FUNÇÕES DE ACESSO - HISTÓRICO DE RESSARCIMENTOS =====

def salvar_ressarcimento(player_id, player_name, club_id, club_name, valor_ressarcido, status, protocolo, referencia):
    '''
    Salva um ressarcimento no histórico.

    Args:
       player_id (int): ID do jogador
       player_name (str): Nome do jogador
       club_id (int): ID do clube
       club_name (str): Nome do clube
       valor_ressarcido (float): Valor ressarcido em reais
       status (str): 'Imediato' ou 'Acumulado'
       protocolo (int): Número do protocolo no Pipefy
       referencia (str): Referência do período (ex: 'Semana 10/03')

    Returns:
        bool: True se sucesso
    '''
    session = Session()
    try:
        ressarcimento = HistoricoRessarcimento(
            data_ressarcimento = datetime.now().date(),
            player_id = player_id,
            player_name = player_name,
            club_id = club_id,
            club_name = club_name,
            valor_ressarcido = valor_ressarcido,
            status = status,
            protocolo = protocolo,
            referencia = referencia
        )
        session.add(ressarcimento)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f'Erro ao salvar ressarcimento: {e}')
        return False
    finally:
        session.close()

def salvar_ressarcimentos_lote(ressarcimentos, protocolo, referencia):
    '''
    Salva múltiplos ressarcimentos de uma vez.

    Args:
        ressarcimentos (list[dict]): Lista de dicionários com dados dos ressarcimentos
            Cada dict deve ter: player_id, player_name, club_id, club_name, valor_ressarcido, status
        protocolo (int): Número do protocolo do Pipefy
        referência (str): Referência do período

    Returns:
        int: Quantidade de ressarcimentos salvos
    '''
    session = Session()
    try:
        count = 0
        data_hoje = datetime.now().date()

        for r in ressarcimentos:
            ressarcimento = HistoricoRessarcimento(
                data_ressarcimento = datetime.now().date(),
                player_id = r['player_id'],
                player_name = r['player_name'],
                club_id = r['club_id'],
                club_name = r["club_name"],
                valor_ressarcido = r['ressarcimento_total'],
                status = r.get('status', 'Imediato'), # Default: Imediato
                protocolo = protocolo,
                referencia = referencia
            )
            session.add(ressarcimento)
            count += 1
        
        session.commit()
        return count
    except Exception as e:
        session.rollback()
        print(f'Erro ao salvar ressarcimentos em lote: {e}')
        return 0
    finally:
        session.close()

def get_historico_completo():
    '''
    Retorna todo o histórico de ressarcimentos.

    Returns:
        list[dict]: Lista de todos os ressarcimentos
    '''
    session = Session()
    try:
        historico = session.query(HistoricoRessarcimento).order_by(
            HistoricoRessarcimento.data_ressarcimento.desc()
        ).all()

        return [{
            'id': h.id,
            'protocolo': h.protocolo,
            'data_ressarcimento': h.data_ressarcimento,
            'player_id': h.player_id,
            'player_name': h.player_name,
            'club_id': h.club_id,
            'club_name': h.club_name,
            'valor_ressarcido': h.valor_ressarcido,
            'status': h.status,
            'referencia': h.referencia,
            'created_at': h.created_at
        } for h in historico]
    finally:
        session.close()

def get_historico_por_periodo(data_inicio, data_fim):
    '''
    Retorna histórico filtrado por período.

    Args:
        data_inicio (date): Data inicial
        data_fim (date): Data final

    Returns:
        list[dict]: Ressarcimentos no período
    '''
    session = Session()
    try:
        historico = session.query(HistoricoRessarcimento).filter(
            HistoricoRessarcimento.data_ressarcimento.between(data_inicio, data_fim)
        ).order_by(HistoricoRessarcimento.data_ressarcimento.desc()).all()

        return [{
            'id': h.id,
            'protocolo': h.protocolo,
            'data_ressarcimento': h.data_ressarcimento,
            'player_id': h.player_id,
            'player_name': h.player_name,
            'club_id': h.club_id,
            'club_name': h.club_name,
            'valor_ressarcido': h.valor_ressarcido,
            'status': h.status,
            'referencia': h.referencia,
            'created_at': h.created_at
        } for h in historico]
    finally:
        session.close()

def get_historico_por_protocolo(protocolo):
    '''
    Retorna todos os ressarcimentos de um protocolo específico.
    
    Args:
        protocolo (int): Número do protocolo (ex: 123456789)
        
    Returns:
        list[dict]: Ressarcimentos deste protocolo
    '''
    session = Session()
    try:
        historico = session.query(HistoricoRessarcimento).filter_by(
            protocolo = protocolo
        ).order_by(HistoricoRessarcimento.protocolo.desc()).all()

        return [{
            'id': h.id,
            'protocolo': h.protocolo,
            'data_ressarcimento': h.data_ressarcimento,
            'player_id': h.player_id,
            'player_name': h.player_name,
            'club_id': h.club_id,
            'club_name': h.club_name,
            'valor_ressarcido': h.valor_ressarcido,
            'status': h.status,
            'referencia': h.referencia,
            'created_at': h.created_at
        } for h in historico]
    finally:
        session.close()

def get_estatisticas_historico():
    '''
    Retorna estatísticas gerais do histórico.
    
    Returns:
        dict: Estatísticas agregadas
    '''
    session = Session()
    try:
        from sqlalchemy import func

        stats = session.query(
            func.count(HistoricoRessarcimento.id).label('total_ressarcimentos'),
            func.sum(HistoricoRessarcimento.valor_ressarcido).label('valor_total'),
            func.count(func.distinct(HistoricoRessarcimento.player_id)).label('jogadores_unicos'),
            func.count(func.distinct(HistoricoRessarcimento.club_id)).label('clubes_unicos'),
            func.count(func.distinct(HistoricoRessarcimento.protocolo)).label('protocolos_unicos')
        ).first()

        return {
            'total_ressarcimentos': stats.total_ressarcimentos or 0,
            'valor_total': stats.valor_total or 0.0,
            'jogadores_unicos': stats.jogadores_unicos or 0,
            'clubes_unicos': stats.clubes_unicos or 0,
            'protocolos_unicos': stats.protocolos_unicos or 0
        }
    finally:
        session.close()

# ===== FUNÇOES DE ACESSO - ACUMULADOS =====

def get_acumulados():
    '''
    Retorna todos os acumulados pendentes.
    
    Returns:
        list[dict]: Lista de acumulados
    '''
    session = Session()
    try:
        acumulados = session.query(Acumulado).order_by(
            Acumulado.ressarcimento_acumulado.desc()
        ).all()

        return [{
            'player_id': a.player_id,
            'player_name': a.player_name,
            'club_id': a.club_id,
            'club_name': a.club_name,
            'ressarcimento_acumulado': a.ressarcimento_acumulado,
            'data_ultima_atualizacao': a.data_ultima_atualizacao
        } for a in acumulados]
    finally:
        session.close()

def atualizar_acumulados(acumulados_novos):
    '''
    Substitui TODOS os acumulados pelos novos.
    
    Remove todos os acumulados antigos e insere os novos.
    Usado após cada cálculo de ressarcimento.
    
    Args:
        acumulados_novos (list[dict]): Lista de novos acumulados
            Cada dict deve ter: player_id, club_id, player_name, club_name, ressarcimento_total
            
    Returns:
        int: Quantidade de acumulados salvos
    '''
    session = Session()
    try:
        # Limpar todos os acumulados antigos
        session.query(Acumulado).delete()

        # Inserir novos acumulados
        count = 0
        data_hoje = datetime.now().date()

        for a in acumulados_novos:
            acumulado = Acumulado(
                player_id = a['player_id'],
                player_name = a['player_name'],
                club_id = a['club_id'],
                club_name = a['club_name'],
                ressarcimento_acumulado = a['ressarcimento_total'],
                data_ultima_atualizacao = data_hoje
            )
            session.add(acumulado)
            count += 1

        session.commit()
        return count
    except Exception as e:
        session.rollback()
        print(f'Erro ao atualizar o acumulado: {e}')
        return 0
    finally:
        session.close()

def limpar_acumulados():
    '''
    Remove TODOS os acumulados do banco.
    
    Útil para reset ou limpeza.
    
    Returns:
        int: Quantidade de acumulados removidos
    '''
    session = Session()
    try:
        count = session.query(Acumulado).count()
        session.query(Acumulado).delete()
        session.commit()
        return count
    except Exception as e:
        session.rollback()
        print(f'Erro ao limpar acumulados: {e}')
        return 0
    finally:
        session.close()

def get_estatisticas_acumulados():
    '''
    Retorna estatísticas dos acumulados pendentes.
    
    Returns:
        dict: Estatísticas agregadas
    '''
    session = Session()
    try:
        from sqlalchemy import func

        stats = session.query(
            func.count(Acumulado.id).label('total_acumulados'),
            func.sum(Acumulado.ressarcimento_acumulado).label('valor_total_acumulado'),
            func.avg(Acumulado.ressarcimento_acumulado).label('valor_medio'),
            func.min(Acumulado.ressarcimento_acumulado).label('valor_minimo'),
            func.max(Acumulado.ressarcimento_acumulado).label('valor_maximo')
        ).first()

        return {
            'total_acumulados': stats.total_acumulados or 0,
            'valor_total_acumulado': stats.valor_total_acumulado or 0,
            'valor_medio': stats.valor_medio or 0,
            'valor_minimo': stats.valor_minimo or 0,
            'valor_maximo': stats.valor_maximo or 0
        }
    finally:
        session.close()