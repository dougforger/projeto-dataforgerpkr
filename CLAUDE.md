# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Comandos essenciais

### Interface Web (principal)
```bash
cd projeto_payjump/web
uv sync               # instala dependências e cria/atualiza .venv
uv run streamlit run início.py
```

> **Streamlit Cloud** ainda usa `requirements.txt` (mantido em paralelo).
> Ao adicionar uma dependência, atualize `pyproject.toml` com `uv add <pacote>`
> e regenere o requirements.txt: `uv export --no-hashes -o requirements.txt`.

### Ferramentas CLI
```bash
# Payjump CLI
cd projeto_payjump/cli
pip install -r requirements.txt
python src/payjump.py

# IP Lookup (adicionar IPs em data/ips.txt, um por linha)
cd ip_lookup
pip install -r requirements.txt
python src/ip_lookup.py
# Saída: output/ip_geoloc.xlsx

# Reverse Geocoding (adicionar coordenadas em data/coords.csv com colunas lat,lon)
cd reverse_geocode
pip install -r requirements.txt
python src/reverse_geocode.py
# Saída: output/reverse_geocode.xlsx
```

### Testes
Os diretórios de testes estão em `projeto_payjump/cli/tests/` e `ip_lookup/tests/`. Não há framework de testes configurado — rodar os arquivos diretamente com `python`.

---

## Arquitetura

O projeto é um sistema de análise de integridade e segurança para a plataforma Suprema Poker, dividido em dois modos: **web** (Streamlit) e **CLI**.

### Interface Web — `projeto_payjump/web/`

Segue o padrão multi-página do Streamlit. O `início.py` é a homepage; as páginas ficam em `pages/` e são auto-descobertas pelo Streamlit:

| Arquivo | Função |
|---|---|
| `início.py` | Homepage com descrição das ferramentas disponíveis |
| `pages/1_📈_Análises.py` | Detecção de conluio — cruzamento de mãos, dispositivos, IPs e geolocalização. Exporta PDF com marca d'água. Suporta fontes Backend (XLSX) e Snowflake (CSV). |
| `pages/2_📊_Payjump.py` | Calculadora de ressarcimentos em torneios com reentrada. Upload XLSX + merge com cadastro de clubes (Supabase). Gera strings formatadas para inserção no sistema. |
| `pages/3_🔐_Gerador_de_Notificações.py` | *(Em desenvolvimento)* Geração de notificações multilíngues (PT/EN/ES) para jogadores afetados por ações de segurança. |
| `pages/4_💲_Ressarcimento.py` | Cálculo de ressarcimentos por bots/fraudadores — upload CSV Snowflake, banco de fraudadores (Supabase ou SQLite fallback), distribuição proporcional, exportação Excel. |
| `pages/5_📝_Relatórios.py` | Relatórios geográficos e de dispositivos — três abas: Consulta Manual (IP/GPS sem upload), Importar Planilhas (IP/GPS com mapa Folium, alertas e PDF), Dispositivos (análise "Same Data With Players" com alertas cruzados e PDF). |
| `pages/6_💵_Despesas.py` | Controle de despesas operacionais do time de segurança. Sincronização via Excel com Supabase (`security_despesas`). Filtros, gráficos e exportação PDF. |
| `pages/7_🃏_Hand_History.py` | Visualizador de hand history — parser do HTML exportado pelo backend, filtros por conta e modo de cartas, resultado acumulado por conta, exportação em PDF com índice navegável. |
| `pages/8_🔗_Pipefy.py` | Dashboard de protocolos de segurança do Pipefy. Sincronização via API, persistência Supabase com fallback SQLite, filtros, gráficos, análise de produtividade e exportação PDF. |
| `pages/9_⚙️_Banco_de_Dados.py` | Gerenciamento das tabelas de referência no Supabase: clubes (upload da planilha do sistema) e ligas (sincronização via CSV + adição manual). Layout em duas colunas. |

---

### Camada Supabase — `utils/supabase_client.py`

Ponto único de configuração e acesso ao Supabase. Todos os módulos de persistência importam daqui:

- `usar_supabase()` → bool — detecta se `SUPABASE_URL` e `SUPABASE_KEY` estão em `st.secrets`
- `criar_cliente()` — factory do cliente Supabase via REST/HTTPS
- `paginar(cliente, tabela, colunas)` — lê todos os registros paginando de `TAMANHO_LOTE` em `TAMANHO_LOTE` (500)
- `exibir_status_conexao()` — renderiza `st.success` / `st.error` com o status da conexão (usado nas sidebars)
- `TAMANHO_LOTE = 500` — constante compartilhada por todos os módulos de persistência

**Credenciais:** `.streamlit/secrets.toml` com `SUPABASE_URL` e `SUPABASE_KEY`.

**DDL completo:** `data/supabase_setup.sql` — executar uma vez no SQL Editor do Supabase.

---

### Módulos de persistência — `utils/`

Todos seguem o padrão: Supabase quando configurado, fallback automático caso contrário.

#### `utils/clubes_db.py`
- `carregar_clubes()` → DataFrame — Supabase ou `data/clubes.csv`
- `sincronizar_clubes(df)` → `(inseridos, atualizados)` — upsert por `clube_id`

#### `utils/ligas_db.py`
- `carregar_ligas()` → DataFrame — Supabase ou `data/ligas.csv` (fallback silencioso em caso de erro)
- `sincronizar_ligas_csv()` → `(inseridas, atualizadas)` — lê `ligas.csv` e faz upsert no Supabase
- `inserir_liga(liga_id, liga_nome, ...)` — upsert de uma liga individual

#### `utils/despesas_db.py`
- `carregar_despesas()` → DataFrame — Supabase obrigatório (sem fallback)
- `sincronizar_excel(df_excel)` → `(removidos, inseridos)` — DELETE completo + INSERT (Excel é fonte de verdade)

#### `utils/pipefy_db.py`
- `carregar_cards()` → DataFrame — Supabase ou SQLite `pipefy.db`
- `sincronizar_cards(df)` → `(inseridos, atualizados)` — upsert por `id`
- `obter_ultima_sincronizacao()` / `registrar_sincronizacao()` — controle de timestamp

#### `utils/ressarcimento_db.py`
- Mesma API pública de `utils/database.py` (drop-in replacement) — Supabase ou SQLite `ressarcimento.db`
- Funções: `get_ids_fraudadores`, `get_fraudadores_completo`, `adicionar_fraudadores_lote`, `salvar_ressarcimentos_lote`, `get_historico_completo`, `get_estatisticas_historico`, `get_acumulados`, `atualizar_acumulados`, `limpar_acumulados`, `get_estatisticas_acumulados`

#### `utils/database.py`
- Backend SQLite puro do ressarcimento. Usado como fallback pelo `ressarcimento_db.py`.
- Banco: `data/ressarcimento.db` — criado automaticamente ao importar o módulo via `inicializar_banco()`
- Tabelas: `fraudadores_identificados`, `historico_ressarcimentos`, `acumulados`
- **Não importar diretamente nas páginas** — usar `ressarcimento_db.py`

---

### Módulos utilitários — `utils/`

#### `utils/pdf_config.py`
Configuração centralizada de estilos PDF (ReportLab):
- Registro de fontes Calibri Light (normal, bold, italic, bold-italic)
- Constantes de largura de página: `LARGURA_PAGINA`, `LARGURA_PAGINA_PAISAGEM`
- Preset de colunas: `COLS_2`, `COLS_3`, `COLS_4`, `COLS_5`, `COLS_6`
- Estilos compartilhados: `ESTILO_TABELA`, `ESTILO_PARAGRAFO`, `ESTILO_LEGENDA`
- `ESTILO_LEGENDA`: Calibri Light Italic, 10pt, cinza (`#555555`), justificado — usado antes de cada tabela nos PDFs como legenda explicativa
- URLs das APIs externas: `URL_IP_API`, `URL_NOMINATIM`
- Constantes de processamento: `MULTIPLICADOR_MOEDA = 5`, `LIMITE_MODALIDADE_CASH = 99`
- `LOGO`: imagem do logo carregada para uso no cabeçalho dos PDFs

#### `utils/pdf_builder.py`
Funções de baixo nível para construção de PDFs com ReportLab:
- `inicializar_pdf(protocolo)` — cria buffer, SimpleDocTemplate e story iniciais com cabeçalho (logo + data + protocolo)
- `finalizar_pdf(buffer, doc, story)` — constrói e retorna bytes do PDF
- `adicionar_tabela(story, dados, larguras, espacamento)` — insere Table com `ESTILO_TABELA` no story
- `montar_tabela_comuns(df, mesas_comuns, coluna_nome=None)` — monta lista de linhas para tabela de mesas/torneios em comum, com link clicável para o Hand History. Quando `coluna_nome` é fornecido (ex: `'NOME_MESA'`), adiciona coluna com nome da mesa como segunda coluna (header: `['ID Mesa', 'Nome da Mesa', 'Jogadores', 'Link']`). Sem `coluna_nome`, usa 3 colunas (header: `['ID Mesa', 'Jogadores', 'Link']`).
- `adicionar_alerta_compartilhamento(story, df, coluna_grupo, coluna_jogador, msg_alerta, msg_ok)` — detecta compartilhamentos e exibe alerta ou confirmação

#### `utils/analise_backend.py`
Análise de conluio a partir de exportações XLSX do backend:
- `analisar_cash(df)` → `(resumo_cash, df_pares_cash, mesas_comuns_cash)` — calcula resumo por jogador, pares com % de mesas compartilhadas e conjunto de mesas em comum via Hand IDs
- `analisar_torneios(df)` → `(resumo_mtt, df_pares_mtt, torneios_comuns)` — análise equivalente para torneios (MTT + SAT MTT Prize)
- `detalhar_torneio(df, game_id)` → `(resumo_torneio, df_torneio)` — detalha prêmios (MttPrize, SAT MTT Prize) e KOs (MttKOPrize) de um torneio específico
- `gerar_pdf(...)` → `bytes` — gera PDF com seções: Cash Game, Torneios, Detalhamento do torneio selecionado. Todas as tabelas possuem `ESTILO_LEGENDA` antes.

**Suporte a torneios satélite:** eventos `SAT MTT Prize` têm `Game ID` nulo e `Association` no formato `'XXXXX_GAMEID'`. O código extrai o `GAMEID` via regex para inclusão nos cruzamentos de torneios.

#### `utils/analise_snowflake.py`
Análise de conluio a partir de exportações CSV do Snowflake:
- `preprocessar_dados(df_bruto, df_clubes, df_ligas)` → `(df, qtd_removidas)` — merge com clubes/ligas, aplica `MULTIPLICADOR_MOEDA` em ganhos e rake, filtra linhas de torneio (`ID_MODALIDADE > LIMITE_MODALIDADE_CASH`)
- `resumo_por_jogador(df)` → DataFrame com colunas `['Jogador ID', 'Jogador Nome', 'Clube Nome', 'Total de Mesas', 'Ganhos (R$)', 'Rake (R$)']` — clube determinado pela moda entre os registros do jogador
- `detectar_mesas_comuns(df, resumo)` → `(df_pares, mesas_comuns_total)` — compara todos os pares de jogadores via sets de mesas
- `detectar_dispositivos_compartilhados(df)` → `(df_disp, codigos_compartilhados)`
- `detectar_ips_compartilhados(df)` → `(df_ips, ips_compartilhados)`
- `gerar_pdf_snowflake(...)` → `bytes` — gera PDF com seções: Cash Games, Dispositivos, Endereços IP, Geolocalização GPS. A tabela de mesas comuns inclui coluna `Nome da Mesa`. Todas as tabelas possuem `ESTILO_LEGENDA` antes.

#### `utils/geolocation.py`
Integração com APIs externas de geolocalização:
- `buscar_localizacao_ips(df_ips, cache_ips)` — geocodifica IPs via ip-api.com em lotes de até 100. Atualiza `cache_ips` in-place (evita requisições duplicadas). Adiciona colunas `CIDADE`, `ESTADO`, `PAIS`, `LATITUDE`, `LONGITUDE`.
- `buscar_geocodificacao_reversa(df_coordenadas, cache_geo)` — converte coordenadas GPS em endereço textual via OpenStreetMap Nominatim. Respeita rate limiting com `DELAY_NOMINATIM`.

#### `utils/analise_geo.py`
Análise geográfica completa e geração de PDFs para a página Relatórios:
- Paleta de cores `PALETA_HEX` — até 10 contas, cor distinta por conta em mapas e tabelas
- `mapa_cores_hex_por_id(ids)` — mapeia IDs ordenados para cores da paleta
- `preparar_df_ip(df_bruto)` — normaliza colunas do IP Report XLSX do backend
- `preparar_df_gps(df_bruto)` — normaliza colunas do GPS Report XLSX do backend
- `resumo_ip(df)` / `resumo_gps(df)` — deduplica registros para visão resumida
- `detectar_alertas_ip(df)` → `{'multiplos_paises', 'ips_compartilhados'}` — detecta anomalias em registros de IP
- `detectar_alertas_gps(df)` → `{'multiplas_cidades', 'dispositivos_compartilhados'}` — detecta anomalias em GPS
- `detectar_alertas_dispositivos(lista_nome_df)` → `{'contas_cruzadas'}` — detecta contas em múltiplos arquivos
- `gerar_elementos_mapa_pdf(df, largura_util)` → lista de elementos ReportLab (imagem + legenda) reutilizável
- `preparar_df_dispositivos(df_bruto)` — normaliza e censura colunas do arquivo "Same Data With Players"
- `gerar_pdf_geo(titulo, df_ip, df_gps, alertas_ip, alertas_gps)` → `bytes` — PDF de geolocalização com seções IP/GPS, alertas e mapas estáticos
- `gerar_pdf_dispositivos(titulo, lista_nome_df, alertas)` → `bytes` — PDF landscape de dispositivos com alertas cruzados
- `_inferir_titulo_investigacao(df)` / `_inferir_id_investigacao(df)` — identifica conta investigada (usadas pela página)
- `_encontrar_ids_compartilhados(df, coluna_grupo, coluna_jogador)` — função interna, também importada por `analise_snowflake.py`

#### `utils/mapa_utils.py`
Utilitário de mapa interativo Folium para uso nas páginas Streamlit:
- `exibir_mapa_folium(df, key)` — renderiza mapa interativo com marcadores coloridos por `JOGADOR_ID`, camadas de Ruas e Satélite, popup com localização e legenda de cores abaixo do mapa
- Centraliza a lógica de mapa para reutilização entre Análises (Snowflake) e Relatórios

#### `utils/hand_history_parser.py`
Parser de HTML de hand history e geração de PDF — sem código Streamlit (testável isoladamente):
- `parse_arquivo_html(conteudo_html)` → `(lista_maos, n_erros)` — divide o arquivo em blocos e parseia cada mão
- `parse_mao(html_bloco)` → dict com `metadados`, `rodadas` e `resultado`
- `coletar_jogadores(lista_maos)` → `{id: nome}` — mapa de todos os jogadores presentes
- `ids_contas_na_mao(mao)` → `set` — IDs dos jogadores presentes nas ações de uma mão
- `renderizar_cartas(lista_cartas, revelar)` → str para exibição Streamlit (com emoji de naipe)
- `_fmt_br(valor, decimais, sinal)` — formata número no padrão brasileiro
- `gerar_pdf_hand_history(maos, contas_selecionadas, modo_cartas, game_id)` → `bytes` — PDF com índice navegável clicável, seções por mão (ações + resultado), links internos

#### `utils/calculos.py`
Lógica de negócio para cálculo de ressarcimentos:
- Cálculo de saldo líquido por jogador vitimado
- Distribuição proporcional dos fundos retidos
- Separação entre pagamentos imediatos, acumulados e futuros

#### `utils/arquivo_utils.py`
Correção e leitura de arquivos XLSX malformados do backend:
- Corrige erros no `styles.xml` antes de processar com openpyxl
- Sempre usar essas funções ao ler Excel do backend — os arquivos frequentemente estão malformados

---

### Dados estáticos — `data/`

- `data/clubes.csv` — fallback local de clubes (colunas: `clube_id`, `clube_nome`, `liga_id`, `liga_nome`)
- `data/ligas.csv` — fallback local de ligas (colunas: `liga_id`, `liga_nome`, `idioma`, `handicap`, `moeda`, `taxa-liga`)
- `data/pipefy.db` — SQLite fallback do Pipefy (gerado automaticamente)
- `data/ressarcimento.db` — SQLite fallback de ressarcimentos (gerado automaticamente)
- `data/supabase_setup.sql` — DDL completo de todas as tabelas do Supabase

---

### CLI — `projeto_payjump/cli/src/`

Módulos separados por responsabilidade:
- `arquivo_utils.py` — leitura/correção de XLSX malformados (fix no `styles.xml`)
- `processamento.py` — cálculos de premiação, KOs, payjump
- `io_utils.py` — helpers de entrada/saída
- `payjump.py` — orquestrador principal
- `atualiza_clubes.py` — sincronização do cadastro de clubes (atualiza CSV local; a versão web usa `clubes_db.py`)
- `gerar_ligas.py` — gerador de ligas

---

## Fluxos de dados

### Análises (página 1)
```
XLSX Backend (mãos/torneios) → analisar_cash() + analisar_torneios()
    → Cruzamento par a par → PDF com seções Cash + Torneios

CSV Snowflake → preprocessar_dados() → resumo_por_jogador()
    → detectar_mesas_comuns() + detectar_dispositivos_compartilhados() + detectar_ips_compartilhados()
    → Geolocalização de IPs (ip-api.com) + Geocodificação reversa GPS (Nominatim)
    → PDF com seções Cash + Dispositivos + IPs + GPS
```

### Relatórios (página 5)
```
IP Report XLSX + GPS Report XLSX (backend)
    → preparar_df_ip() + preparar_df_gps()
    → buscar_localizacao_ips() [ip-api.com] + buscar_geocodificacao_reversa() [Nominatim]
    → detectar_alertas_ip() + detectar_alertas_gps()
    → exibir_mapa_folium() [HTML interativo, via mapa_utils.py]
    → gerar_pdf_geo() [PDF portrait/landscape com mapas estáticos]

Same Data With Players XLSX (backend, múltiplos arquivos)
    → preparar_df_dispositivos() [censura UUID]
    → detectar_alertas_dispositivos() [cruzamento entre arquivos]
    → gerar_pdf_dispositivos() [PDF landscape]
```

### Hand History (página 7)
```
Hand History HTML (backend)
    → parse_arquivo_html() → lista de mãos parseadas
    → coletar_jogadores() [mapa id→nome para o multiselect]
    → Filtros de conta + modo de cartas na UI
    → gerar_pdf_hand_history() [PDF com índice navegável + tabelas de ações/resultado]
```

### Payjump (página 2)
```
XLSX torneio → Correção de arquivo → Extração de jogadores/ranks/prêmios
    → carregar_clubes() [Supabase ou CSV] → Distribuição proporcional de KOs → Cálculo payjump
    → Strings formatadas para sistema
```

### Ressarcimento (página 4)
```
CSV Snowflake → Identificação de fraudadores (ressarcimento_db → Supabase ou SQLite)
    → Cálculo de saldo líquido por jogador
    → Distribuição proporcional dos fundos retidos
    → Separação: imediatos / acumulados / futuros
    → Exportação Excel (múltiplas abas)
```

### Despesas (página 6)
```
Excel de despesas → sincronizar_excel() → DELETE + INSERT no Supabase (security_despesas)
    → carregar_despesas() → Filtros + gráficos na UI → gerar_pdf_relatorio_financeiro()
```

### Pipefy (página 8)
```
API Pipefy → buscar_todos_os_cards() → sincronizar_cards() [Supabase ou SQLite]
    → registrar_sincronizacao() → Filtros + métricas + gráficos → gerar_pdf_dashboard()
```

### Banco de Dados (página 9)
```
Planilha de clubes (XLSX) → corrigir_xlsx_memoria() → filtrar por carregar_ligas()
    → sincronizar_clubes() [upsert Supabase]

ligas.csv → sincronizar_ligas_csv() [upsert Supabase]
Formulário manual → inserir_liga() [upsert Supabase]
```

---

## APIs externas

| API | Uso | Configuração |
|---|---|---|
| **ip-api.com** (`/batch`) | Geolocalização de IPs em lotes de até 100 | `URL_IP_API`, `TIMEOUT_IP_API = 15`, `LOTE_IP_API = 100` |
| **OpenStreetMap Nominatim** (`/reverse`) | Geocodificação reversa de coordenadas GPS | `URL_NOMINATIM`, `TIMEOUT_NOMINATIM = 10`, `DELAY_NOMINATIM = 1` (rate limiting) |
| **Snowflake** | Acesso apenas via export CSV (sem conexão direta) | — |
| **Pipefy GraphQL** | Busca de cards de segurança | Token em `st.secrets['PIPEFY_TOKEN']` |
| **Supabase REST** | Persistência centralizada | `SUPABASE_URL`, `SUPABASE_KEY` em `st.secrets` |

---

## Convenções importantes

- **Homepage**: o arquivo de entrada do Streamlit é `início.py` (não `app.py`)
- **Supabase**: toda conexão passa por `utils/supabase_client.py`. Nunca criar clientes Supabase diretamente nas páginas ou em outros utilitários.
- **Clubes e Ligas**: usar sempre `carregar_clubes()` / `carregar_ligas()` — nunca `pd.read_csv` direto nas páginas. Ambas têm fallback automático para CSV.
- **Ressarcimento**: importar de `utils/ressarcimento_db.py`, não de `utils/database.py`. O `database.py` é o backend SQLite e não deve ser importado diretamente pelas páginas.
- **XLSX malformados**: arquivos do backend frequentemente estão com `styles.xml` corrompido. Sempre usar `arquivo_utils.py` para leitura.
- **Caminhos hardcoded**: sem `.env`. Ajustes de ambiente devem ser feitos diretamente nos arquivos.
- **Multiplicador de moeda**: ganhos e rake do Snowflake são multiplicados por `MULTIPLICADOR_MOEDA = 5` (conversão de chips para R$).
- **Limite de modalidade**: `LIMITE_MODALIDADE_CASH = 99` — linhas com `ID_MODALIDADE > 99` são torneios e removidas da análise de cash game (Snowflake).
- **Legendas nos PDFs**: todas as tabelas em todos os PDFs gerados pelo sistema possuem `story.append(Paragraph('...', ESTILO_LEGENDA))` imediatamente antes de `adicionar_tabela()`. Manter esse padrão ao adicionar novas tabelas.
- **`montar_tabela_comuns`**: backend usa sem `coluna_nome` (3 colunas, `COLS_3`); Snowflake usa com `coluna_nome='NOME_MESA'` (4 colunas, `COLS_4`).
- **Funções internas em `analise_geo.py`**: prefixo `_` indica uso exclusivamente interno ao módulo. Exceção documentada: `_encontrar_ids_compartilhados` é importada por `analise_snowflake.py` e `_inferir_titulo_investigacao` / `_inferir_id_investigacao` são importadas pela página de Relatórios.
- **Cache de geolocalização**: `cache_ips` e `cache_geo` são dicts mantidos no `st.session_state` para evitar requisições duplicadas entre interações do usuário.
- **`utils/hand_history_parser.py`**: módulo sem Streamlit — contém todo o parsing do HTML e a geração de PDF do Hand History. A página `7_🃏_Hand_History.py` importa deste módulo e contém apenas a camada de UI.
- **`utils/mapa_utils.py`**: centraliza a lógica do mapa Folium interativo. Importar e usar `exibir_mapa_folium(df, key)` em vez de duplicar código de mapa entre páginas.
- **`TAMANHO_LOTE`**: constante definida em `supabase_client.py`. Todos os módulos de persistência importam daqui — nunca redefinir localmente.
- O projeto é de uso interno (licença proprietária). Dados sensíveis não devem sair dos sistemas internos.
