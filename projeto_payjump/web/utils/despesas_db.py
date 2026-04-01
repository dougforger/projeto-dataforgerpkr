"""Persistência das despesas Security no Supabase.

Tabelas necessárias (executar uma vez no SQL Editor do Supabase):

    CREATE TABLE IF NOT EXISTS security_despesas (
        id            BIGSERIAL PRIMARY KEY,
        protocolo     TEXT,
        data          DATE,
        dia_fechamento DATE NOT NULL,
        clube         TEXT,
        liga          TEXT,
        valor         NUMERIC(14, 2) NOT NULL,
        categoria     TEXT
    );

Notas de uso:
- O módulo exige que SUPABASE_URL e SUPABASE_KEY estejam disponíveis
  em st.secrets (arquivo .streamlit/secrets.toml para ambiente local
  ou variáveis de ambiente no Streamlit Cloud).
- A sincronização do Excel faz DELETE completo + INSERT — o Excel é
  a fonte de verdade. Sempre que um novo Excel for carregado, todos os
  registros anteriores são substituídos.
- A leitura paginada garante que tabelas com mais de 500 registros
  sejam lidas corretamente, respeitando o limite padrão do PostgREST.
"""

from __future__ import annotations

import datetime
import io
from typing import Optional

import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# Constantes internas
# ─────────────────────────────────────────────────────────────────────────────

_NOME_TABELA_DESPESAS = 'security_despesas'
_TAMANHO_LOTE         = 500   # registros por requisição de leitura / escrita

# Colunas que o DataFrame de despesas deve ter para ser sincronizado.
# As colunas opcionais (Categoria) recebem None quando ausentes no Excel.
_COLUNAS_OBRIGATORIAS = {'Dia Fechamento', 'Valor'}
_COLUNAS_ESPERADAS    = ['Protocolo', 'Data', 'Dia Fechamento', 'Clube', 'Liga', 'Valor', 'Categoria']


# ─────────────────────────────────────────────────────────────────────────────
# Auxiliares de conexão
# ─────────────────────────────────────────────────────────────────────────────

def _usar_supabase() -> bool:
    """Retorna True quando SUPABASE_URL e SUPABASE_KEY estão em st.secrets."""
    try:
        import streamlit as st
        url_configurada = st.secrets.get('SUPABASE_URL', '')
        chave_configurada = st.secrets.get('SUPABASE_KEY', '')
        return bool(url_configurada and chave_configurada)
    except Exception:
        return False


def _criar_cliente_supabase():
    """Cria e retorna o cliente Supabase via REST/HTTPS."""
    import streamlit as st
    from supabase import create_client
    return create_client(st.secrets['SUPABASE_URL'], st.secrets['SUPABASE_KEY'])


def _supabase_paginar(cliente, nome_tabela: str, colunas: str = '*') -> list[dict]:
    """Lê todos os registros de uma tabela paginando de _TAMANHO_LOTE em _TAMANHO_LOTE.

    O PostgREST limita cada resposta a 1.000 linhas por padrão. A paginação
    garante que tabelas maiores sejam lidas integralmente.

    Args:
        cliente:      Cliente Supabase já inicializado.
        nome_tabela:  Nome da tabela a ser consultada.
        colunas:      Colunas a selecionar (padrão '*').

    Returns:
        Lista de dicionários com todos os registros.
    """
    todos_registros: list[dict] = []
    indice_inicio = 0

    while True:
        resposta = (
            cliente.table(nome_tabela)
            .select(colunas)
            .range(indice_inicio, indice_inicio + _TAMANHO_LOTE - 1)
            .execute()
        )
        lote_atual = resposta.data or []
        todos_registros.extend(lote_atual)

        if len(lote_atual) < _TAMANHO_LOTE:
            break   # última página
        indice_inicio += _TAMANHO_LOTE

    return todos_registros


# ─────────────────────────────────────────────────────────────────────────────
# API pública
# ─────────────────────────────────────────────────────────────────────────────

def carregar_despesas() -> pd.DataFrame:
    """Retorna todos os lançamentos de despesas como DataFrame.

    Carrega os dados diretamente do Supabase, paginando automaticamente
    quando o volume de registros ultrapassa o limite por requisição.

    Returns:
        DataFrame com colunas: Protocolo, Data, Dia Fechamento, Clube,
        Liga, Valor, Categoria. Retorna DataFrame vazio se a tabela não
        contiver registros.

    Raises:
        RuntimeError: quando Supabase não está configurado em st.secrets.
    """
    if not _usar_supabase():
        raise RuntimeError(
            'Supabase não configurado. Verifique SUPABASE_URL e SUPABASE_KEY '
            'em .streamlit/secrets.toml.'
        )

    cliente = _criar_cliente_supabase()
    registros_brutos = _supabase_paginar(cliente, _NOME_TABELA_DESPESAS)

    if not registros_brutos:
        return pd.DataFrame(columns=_COLUNAS_ESPERADAS)

    df_carregado = pd.DataFrame(registros_brutos)

    # Mapeamento das colunas snake_case do banco → nomes originais do projeto
    mapa_colunas = {
        'protocolo':     'Protocolo',
        'data':          'Data',
        'dia_fechamento': 'Dia Fechamento',
        'clube':         'Clube',
        'liga':          'Liga',
        'valor':         'Valor',
        'categoria':     'Categoria',
    }
    df_carregado = df_carregado.rename(columns=mapa_colunas)

    # Converter tipos
    if 'Dia Fechamento' in df_carregado.columns:
        df_carregado['Dia Fechamento'] = pd.to_datetime(df_carregado['Dia Fechamento'])
    if 'Data' in df_carregado.columns:
        df_carregado['Data'] = pd.to_datetime(df_carregado['Data']).dt.date
    if 'Valor' in df_carregado.columns:
        df_carregado['Valor'] = pd.to_numeric(df_carregado['Valor'], errors='coerce')

    # Garantir que todas as colunas esperadas existam (mesmo que com NaN)
    for nome_coluna in _COLUNAS_ESPERADAS:
        if nome_coluna not in df_carregado.columns:
            df_carregado[nome_coluna] = None

    return df_carregado[_COLUNAS_ESPERADAS]


def sincronizar_excel(df_excel: pd.DataFrame) -> tuple[int, int]:
    """Sincroniza o DataFrame do Excel com o Supabase (DELETE completo + INSERT).

    O Excel é a fonte de verdade. Ao chamar esta função, todos os registros
    existentes na tabela são apagados e substituídos pelos dados do Excel
    fornecido.

    Args:
        df_excel: DataFrame lido diretamente do Excel de despesas.
                  Deve conter ao menos as colunas 'Dia Fechamento' e 'Valor'.

    Returns:
        Tupla (total_removidos, total_inseridos).

    Raises:
        ValueError:   quando o DataFrame não contém as colunas obrigatórias.
        RuntimeError: quando Supabase não está configurado.
    """
    if not _usar_supabase():
        raise RuntimeError(
            'Supabase não configurado. Verifique SUPABASE_URL e SUPABASE_KEY.'
        )

    # Validação das colunas obrigatórias
    colunas_faltando = _COLUNAS_OBRIGATORIAS - set(df_excel.columns)
    if colunas_faltando:
        raise ValueError(
            f'O Excel não contém as colunas obrigatórias: {colunas_faltando}. '
            f'Verifique se o arquivo correto foi enviado.'
        )

    cliente = _criar_cliente_supabase()

    # Contar registros atuais antes de apagar
    registros_anteriores = _supabase_paginar(cliente, _NOME_TABELA_DESPESAS, 'id')
    total_removidos = len(registros_anteriores)

    # Apagar todos os registros existentes
    if total_removidos > 0:
        cliente.table(_NOME_TABELA_DESPESAS).delete().gt('id', 0).execute()

    # Montar lista de registros para inserção
    lista_registros: list[dict] = []
    for _, linha in df_excel.iterrows():
        registro = _converter_linha_para_dict(linha)
        lista_registros.append(registro)

    # Inserir em lotes para respeitar limite do PostgREST
    total_inseridos = 0
    for indice_inicio in range(0, len(lista_registros), _TAMANHO_LOTE):
        lote = lista_registros[indice_inicio: indice_inicio + _TAMANHO_LOTE]
        cliente.table(_NOME_TABELA_DESPESAS).insert(lote).execute()
        total_inseridos += len(lote)

    return total_removidos, total_inseridos


def _converter_linha_para_dict(linha: pd.Series) -> dict:
    """Converte uma linha do DataFrame de despesas para dicionário do Supabase.

    Realiza as conversões de tipo necessárias (datas para ISO 8601, floats,
    None para campos ausentes) para compatibilidade com o PostgREST.

    Args:
        linha: Série pandas representando uma linha do DataFrame de despesas.

    Returns:
        Dicionário com chaves no formato snake_case, pronto para upsert.
    """

    def _data_para_iso(valor) -> Optional[str]:
        """Converte uma data (datetime, date, string ou NaT) para string ISO."""
        if valor is None or (isinstance(valor, float) and pd.isna(valor)):
            return None
        if isinstance(valor, (datetime.datetime, datetime.date)):
            return valor.isoformat()
        if isinstance(valor, pd.Timestamp):
            return valor.date().isoformat() if not pd.isna(valor) else None
        try:
            return pd.to_datetime(valor).date().isoformat()
        except Exception:
            return None

    def _texto_ou_none(valor) -> Optional[str]:
        """Retorna o valor como string ou None se estiver ausente."""
        if valor is None:
            return None
        if isinstance(valor, float) and pd.isna(valor):
            return None
        return str(valor).strip() or None

    def _float_ou_none(valor) -> Optional[float]:
        """Retorna o valor como float ou None se não for numérico."""
        if valor is None:
            return None
        try:
            resultado = float(valor)
            return None if pd.isna(resultado) else resultado
        except (TypeError, ValueError):
            return None

    return {
        'protocolo':      _texto_ou_none(linha.get('Protocolo')),
        'data':           _data_para_iso(linha.get('Data')),
        'dia_fechamento': _data_para_iso(linha.get('Dia Fechamento')),
        'clube':          _texto_ou_none(linha.get('Clube')),
        'liga':           _texto_ou_none(linha.get('Liga')),
        'valor':          _float_ou_none(linha.get('Valor')),
        'categoria':      _texto_ou_none(linha.get('Categoria')),
    }


def verificar_conexao() -> tuple[bool, str]:
    """Testa a conexão com o Supabase e retorna o status.

    Returns:
        Tupla (sucesso, mensagem) onde sucesso é True se a conexão
        funcionou e mensagem descreve o resultado ou o erro.
    """
    if not _usar_supabase():
        return False, 'SUPABASE_URL ou SUPABASE_KEY não configurados em st.secrets.'
    try:
        cliente = _criar_cliente_supabase()
        # Tentativa de leitura de 1 registro para validar conexão
        cliente.table(_NOME_TABELA_DESPESAS).select('id').limit(1).execute()
        return True, 'Conexão com Supabase estabelecida com sucesso.'
    except Exception as erro_conexao:
        return False, f'Falha na conexão: {erro_conexao}'
