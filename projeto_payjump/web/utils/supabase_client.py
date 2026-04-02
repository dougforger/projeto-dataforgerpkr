"""Utilitário centralizado de conexão com o Supabase.

Todos os módulos que precisam acessar o Supabase devem importar daqui,
evitando duplicação da lógica de detecção de credenciais, criação de
cliente e paginação.

Uso típico:
    from utils.supabase_client import usar_supabase, criar_cliente, paginar

    if usar_supabase():
        cliente = criar_cliente()
        registros = paginar(cliente, 'minha_tabela')
"""

from __future__ import annotations

TAMANHO_LOTE = 500  # registros por requisição (leitura e escrita)


def usar_supabase() -> bool:
    """Retorna True quando SUPABASE_URL e SUPABASE_KEY estão em st.secrets."""
    try:
        import streamlit as st
        url = st.secrets.get('SUPABASE_URL', '')
        key = st.secrets.get('SUPABASE_KEY', '')
        return bool(url and key)
    except Exception:
        return False


def criar_cliente():
    """Cria e retorna o cliente Supabase via REST/HTTPS (porta 443)."""
    import streamlit as st
    from supabase import create_client
    return create_client(st.secrets['SUPABASE_URL'], st.secrets['SUPABASE_KEY'])


def exibir_status_conexao() -> None:
    """Exibe na sidebar o status da conexão com o Supabase via st.success/st.error."""
    import streamlit as st

    if not usar_supabase():
        st.error('🔴 Sem conexão\n\nSUPABASE_URL ou SUPABASE_KEY não configurados em st.secrets.')
        return
    try:
        cliente = criar_cliente()
        # Leitura mínima para validar a conexão
        cliente.table('pipefy_cards').select('id').limit(1).execute()
        st.success('🟢 Supabase conectado')
    except Exception as erro:
        st.error(f'🔴 Sem conexão\n\n{erro}')


def paginar(cliente, nome_tabela: str, colunas: str = '*') -> list[dict]:
    """Lê todos os registros de uma tabela paginando de TAMANHO_LOTE em TAMANHO_LOTE.

    O PostgREST limita cada resposta a 1.000 linhas por padrão. A paginação
    garante que tabelas maiores sejam lidas integralmente.

    Args:
        cliente:      Cliente Supabase já inicializado.
        nome_tabela:  Nome da tabela a ser consultada.
        colunas:      Colunas a selecionar (padrão '*').

    Returns:
        Lista de dicionários com todos os registros.
    """
    todos: list[dict] = []
    inicio = 0

    while True:
        resposta = (
            cliente.table(nome_tabela)
            .select(colunas)
            .range(inicio, inicio + TAMANHO_LOTE - 1)
            .execute()
        )
        lote = resposta.data or []
        todos.extend(lote)

        if len(lote) < TAMANHO_LOTE:
            break
        inicio += TAMANHO_LOTE

    return todos
