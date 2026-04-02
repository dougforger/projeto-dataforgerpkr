-- =============================================================================
-- Script de criação de todas as tabelas do projeto no Supabase
-- Executar uma única vez no SQL Editor do Supabase Dashboard
-- (Menu lateral → SQL Editor → New Query → colar e executar)
-- =============================================================================


-- ─────────────────────────────────────────────────────────────────────────────
-- Despesas Security
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS security_despesas (
    id             BIGSERIAL PRIMARY KEY,
    protocolo      TEXT,
    data           DATE,
    dia_fechamento DATE           NOT NULL,
    clube          TEXT,
    liga           TEXT,
    valor          NUMERIC(14, 2) NOT NULL,
    categoria      TEXT
);

CREATE INDEX IF NOT EXISTS idx_security_despesas_dia_fechamento
    ON security_despesas (dia_fechamento);
CREATE INDEX IF NOT EXISTS idx_security_despesas_clube
    ON security_despesas (clube);
CREATE INDEX IF NOT EXISTS idx_security_despesas_liga
    ON security_despesas (liga);
CREATE INDEX IF NOT EXISTS idx_security_despesas_categoria
    ON security_despesas (categoria);


-- ─────────────────────────────────────────────────────────────────────────────
-- Pipefy
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS pipefy_cards (
    id         TEXT PRIMARY KEY,
    criado_em  DATE,
    categoria  TEXT,
    tipo       TEXT,
    resultado  TEXT,
    analista   TEXT
);

CREATE TABLE IF NOT EXISTS pipefy_sync (
    id              INTEGER PRIMARY KEY,
    sincronizado_em TIMESTAMPTZ
);


-- ─────────────────────────────────────────────────────────────────────────────
-- Clubes e Ligas
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS clubes (
    clube_id   INTEGER PRIMARY KEY,
    clube_nome TEXT    NOT NULL,
    liga_id    INTEGER NOT NULL,
    liga_nome  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS ligas (
    liga_id    INTEGER PRIMARY KEY,
    liga_nome  TEXT    NOT NULL,
    idioma     TEXT,
    handicap   NUMERIC,
    moeda      TEXT,
    taxa_liga  NUMERIC
);


-- ─────────────────────────────────────────────────────────────────────────────
-- Ressarcimentos
-- ─────────────────────────────────────────────────────────────────────────────

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

CREATE INDEX IF NOT EXISTS idx_fraudadores_jogador_id
    ON fraudadores_identificados (jogador_id);

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

CREATE INDEX IF NOT EXISTS idx_historico_data
    ON historico_ressarcimentos (data_ressarcimento);
CREATE INDEX IF NOT EXISTS idx_historico_protocolo
    ON historico_ressarcimentos (protocolo);
CREATE INDEX IF NOT EXISTS idx_historico_jogador
    ON historico_ressarcimentos (jogador_id);

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
