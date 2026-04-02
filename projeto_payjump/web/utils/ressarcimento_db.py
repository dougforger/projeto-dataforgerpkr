"""Persistência do módulo de ressarcimentos.

Backends:
  • Supabase  — quando SUPABASE_URL e SUPABASE_KEY estiverem em st.secrets.
  • SQLite    — fallback automático via utils/database.py.

Tabelas necessárias no Supabase (executar uma vez no SQL Editor):

    CREATE TABLE IF NOT EXISTS fraudadores_identificados (
        id                  BIGSERIAL PRIMARY KEY,
        protocolo           INTEGER   NOT NULL,
        jogador_id          INTEGER   UNIQUE NOT NULL,
        jogador_nome        TEXT,
        clube_id            INTEGER,
        clube_nome          TEXT,
        data_identificacao  DATE      NOT NULL,
        valor_total_retido  NUMERIC   DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS historico_ressarcimentos (
        id                  BIGSERIAL PRIMARY KEY,
        protocolo           INTEGER   NOT NULL,
        data_ressarcimento  DATE      NOT NULL,
        jogador_id          INTEGER   NOT NULL,
        jogador_nome        TEXT,
        clube_id            INTEGER,
        clube_nome          TEXT,
        valor_ressarcido    NUMERIC   NOT NULL,
        status              TEXT,
        referencia          TEXT,
        created_at          TIMESTAMPTZ DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS acumulados (
        id                       BIGSERIAL PRIMARY KEY,
        jogador_id               INTEGER NOT NULL,
        clube_id                 INTEGER NOT NULL,
        jogador_nome             TEXT,
        clube_nome               TEXT,
        ressarcimento_acumulado  NUMERIC NOT NULL,
        data_ultima_atualizacao  DATE    NOT NULL,
        UNIQUE (jogador_id, clube_id)
    );

Notas de uso:
- Todas as funções públicas têm a mesma assinatura do utils/database.py,
  permitindo substituição direta nos imports.
- O Supabase é escolhido automaticamente quando as credenciais estão
  disponíveis; caso contrário, o SQLite local é usado sem interrupção.
"""

from __future__ import annotations

import datetime

from utils.supabase_client import TAMANHO_LOTE, criar_cliente, paginar, usar_supabase

# Importa o backend SQLite para uso como fallback
import utils.database as _sqlite


# ─────────────────────────────────────────────────────────────────────────────
# Helpers internos
# ─────────────────────────────────────────────────────────────────────────────

def _hoje_iso() -> str:
    return datetime.date.today().isoformat()


def _data_iso(valor) -> str | None:
    if valor is None:
        return None
    if isinstance(valor, (datetime.date, datetime.datetime)):
        return valor.isoformat()
    return str(valor)


# ─────────────────────────────────────────────────────────────────────────────
# Fraudadores
# ─────────────────────────────────────────────────────────────────────────────

def get_ids_fraudadores() -> list[int]:
    """Retorna lista de IDs dos fraudadores conhecidos."""
    if usar_supabase():
        cliente = criar_cliente()
        registros = paginar(cliente, 'fraudadores_identificados', 'jogador_id')
        return [r['jogador_id'] for r in registros]
    return _sqlite.get_ids_fraudadores()


def get_fraudadores_completo() -> list[dict]:
    """Retorna todos os dados dos fraudadores identificados."""
    if usar_supabase():
        cliente = criar_cliente()
        return paginar(cliente, 'fraudadores_identificados')
    return _sqlite.get_fraudadores_completo()


def adicionar_fraudadores_lote(fraudadores: list[dict]) -> int:
    """Upsert de múltiplos fraudadores. Retorna quantidade processada."""
    if usar_supabase():
        cliente = criar_cliente()
        registros = [
            {
                'protocolo':           int(f['protocolo']),
                'jogador_id':          int(f['jogador_id']),
                'jogador_nome':        f.get('jogador_nome'),
                'clube_id':            int(f['clube_id']) if f.get('clube_id') is not None else None,
                'clube_nome':          f.get('clube_nome'),
                'data_identificacao':  _hoje_iso(),
                'valor_total_retido':  float(f.get('valor_total_retido', 0)),
            }
            for f in fraudadores
        ]
        for i in range(0, len(registros), TAMANHO_LOTE):
            cliente.table('fraudadores_identificados').upsert(
                registros[i:i + TAMANHO_LOTE],
                on_conflict='jogador_id',
            ).execute()
        return len(registros)
    return _sqlite.adicionar_fraudadores_lote(fraudadores)


# ─────────────────────────────────────────────────────────────────────────────
# Histórico de ressarcimentos
# ─────────────────────────────────────────────────────────────────────────────

def salvar_ressarcimentos_lote(ressarcimentos: list[dict], protocolo: int, referencia: str) -> int:
    """Insere múltiplos ressarcimentos no histórico. Retorna quantidade salva."""
    if usar_supabase():
        cliente = criar_cliente()
        hoje = _hoje_iso()
        registros = [
            {
                'protocolo':           protocolo,
                'data_ressarcimento':  hoje,
                'jogador_id':          r['jogador_id'],
                'jogador_nome':        r.get('jogador_nome'),
                'clube_id':            r.get('clube_id'),
                'clube_nome':          r.get('clube_nome'),
                'valor_ressarcido':    float(r['ressarcimento_total']),
                'status':              r.get('status', 'Imediato'),
                'referencia':          referencia,
            }
            for r in ressarcimentos
        ]
        for i in range(0, len(registros), TAMANHO_LOTE):
            cliente.table('historico_ressarcimentos').insert(
                registros[i:i + TAMANHO_LOTE]
            ).execute()
        return len(registros)
    return _sqlite.salvar_ressarcimentos_lote(ressarcimentos, protocolo, referencia)


def get_historico_completo() -> list[dict]:
    """Retorna todo o histórico de ressarcimentos."""
    if usar_supabase():
        cliente = criar_cliente()
        return paginar(cliente, 'historico_ressarcimentos')
    return _sqlite.get_historico_completo()


def get_estatisticas_historico() -> dict:
    """Retorna estatísticas agregadas do histórico."""
    if usar_supabase():
        registros = get_historico_completo()
        jogadores = {r['jogador_id'] for r in registros}
        clubes    = {r['clube_id']   for r in registros if r.get('clube_id')}
        protocolos = {r['protocolo'] for r in registros}
        return {
            'total_ressarcimentos': len(registros),
            'valor_total':          sum(float(r['valor_ressarcido']) for r in registros),
            'jogadores_unicos':     len(jogadores),
            'clubes_unicos':        len(clubes),
            'protocolos_unicos':    len(protocolos),
        }
    return _sqlite.get_estatisticas_historico()


# ─────────────────────────────────────────────────────────────────────────────
# Acumulados
# ─────────────────────────────────────────────────────────────────────────────

def get_acumulados() -> list[dict]:
    """Retorna todos os acumulados pendentes."""
    if usar_supabase():
        cliente = criar_cliente()
        return paginar(cliente, 'acumulados')
    return _sqlite.get_acumulados()


def atualizar_acumulados(acumulados_novos: list[dict]) -> int:
    """Substitui TODOS os acumulados pelos novos. Retorna quantidade salva."""
    if usar_supabase():
        cliente = criar_cliente()
        hoje = _hoje_iso()
        # Apaga todos os existentes
        cliente.table('acumulados').delete().gte('id', 0).execute()
        if not acumulados_novos:
            return 0
        registros = [
            {
                'jogador_id':              a['jogador_id'],
                'clube_id':                a['clube_id'],
                'jogador_nome':            a.get('jogador_nome'),
                'clube_nome':              a.get('clube_nome'),
                'ressarcimento_acumulado': float(a['ressarcimento_total']),
                'data_ultima_atualizacao': hoje,
            }
            for a in acumulados_novos
        ]
        for i in range(0, len(registros), TAMANHO_LOTE):
            cliente.table('acumulados').insert(
                registros[i:i + TAMANHO_LOTE]
            ).execute()
        return len(registros)
    return _sqlite.atualizar_acumulados(acumulados_novos)


def limpar_acumulados() -> int:
    """Remove TODOS os acumulados. Retorna quantidade removida."""
    if usar_supabase():
        cliente = criar_cliente()
        existentes = paginar(cliente, 'acumulados', 'id')
        if existentes:
            cliente.table('acumulados').delete().gte('id', 0).execute()
        return len(existentes)
    return _sqlite.limpar_acumulados()


def get_estatisticas_acumulados() -> dict:
    """Retorna estatísticas dos acumulados pendentes."""
    if usar_supabase():
        registros = get_acumulados()
        valores = [float(r['ressarcimento_acumulado']) for r in registros]
        return {
            'total_acumulados':      len(valores),
            'valor_total_acumulado': sum(valores),
            'valor_medio':           sum(valores) / len(valores) if valores else 0,
            'valor_minimo':          min(valores) if valores else 0,
            'valor_maximo':          max(valores) if valores else 0,
        }
    return _sqlite.get_estatisticas_acumulados()
