-- =============================================================================
-- Script de criação da tabela security_despesas no Supabase
-- Executar uma única vez no SQL Editor do Supabase Dashboard
-- (Menu lateral → SQL Editor → New Query → colar e executar)
-- =============================================================================

-- Tabela principal de lançamentos de despesas/receitas Security
CREATE TABLE IF NOT EXISTS security_despesas (
    id             BIGSERIAL PRIMARY KEY,
    protocolo      TEXT,
    data           DATE,
    dia_fechamento DATE          NOT NULL,
    clube          TEXT,
    liga           TEXT,
    valor          NUMERIC(14, 2) NOT NULL,
    categoria      TEXT
);

-- Índice para acelerar filtros por período (dia_fechamento é o filtro mais comum)
CREATE INDEX IF NOT EXISTS idx_security_despesas_dia_fechamento
    ON security_despesas (dia_fechamento);

-- Índice para filtros por clube e liga (usados nos filtros do relatório)
CREATE INDEX IF NOT EXISTS idx_security_despesas_clube
    ON security_despesas (clube);

CREATE INDEX IF NOT EXISTS idx_security_despesas_liga
    ON security_despesas (liga);

-- Índice para filtros por categoria
CREATE INDEX IF NOT EXISTS idx_security_despesas_categoria
    ON security_despesas (categoria);

-- =============================================================================
-- Como usar após criar a tabela:
--
-- 1. Abra a página "💸 Security" no Streamlit.
-- 2. No painel lateral, em "📤 Sincronizar Excel", faça upload do arquivo
--    Despesas.xlsx.
-- 3. Clique em "⚙️ Sincronizar com Supabase".
--    → Todos os lançamentos do Excel serão importados para esta tabela.
--    → A partir daí, a página carrega os dados diretamente do Supabase.
--
-- Para adicionar a coluna Categoria ao Excel (opcional):
-- Basta adicionar uma coluna chamada "Categoria" na aba "Despesas" do Excel
-- antes de sincronizar. Ela será importada automaticamente.
-- =============================================================================
