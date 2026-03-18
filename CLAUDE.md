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
| `pages/2_📊_Payjump.py` | Calculadora de ressarcimentos em torneios com reentrada. Upload XLSX + merge com configs de clubes e ligas. Gera strings formatadas para inserção no sistema. |
| `pages/3_🔐_Gerador_de_Notificações.py` | *(Em desenvolvimento)* Geração de notificações multilíngues (PT/EN/ES) para jogadores afetados por ações de segurança. |
| `pages/4_💲_Ressarcimento.py` | Cálculo de ressarcimentos por bots/fraudadores — upload CSV Snowflake, banco SQLite de fraudadores, distribuição proporcional, exportação Excel. |
| `pages/5_🌍_Geolocalização.py` | Análise geográfica standalone de contas investigadas — geolocalização de IPs, geocodificação reversa de GPS, mapa interativo Folium + PDF com mapa estático. |

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
Análise geográfica completa e geração de PDF para a página Geolocalização:
- Paletas de cores (`PALETA_HEX`, `PALETA_RGBA`) — até 10 contas, cor distinta por conta em mapas e tabelas
- Estilos internos para células de tabela ReportLab (`_estilo_cabecalho`, `_estilo_celula`)
- `preparar_dados_ip(df_ip_raw)` — normaliza colunas do IP Report XLSX do backend
- `preparar_dados_gps(df_gps_raw)` — normaliza colunas do GPS Report XLSX do backend
- `detectar_alertas(df_ips_geo, df_gps_geo)` — detecta: múltiplos países, IPs compartilhados, múltiplas cidades, dispositivos compartilhados. Retorna lista de alertas.
- `gerar_mapa_folium(df_ips_geo, df_gps_geo)` — gera mapa interativo HTML com marcadores coloridos por conta (Folium)
- `gerar_mapa_estatico(df_ips_geo, df_gps_geo, largura, altura)` — gera imagem PNG com staticmap para embutir no PDF
- `gerar_pdf_geo(protocolo, df_ips_geo, df_gps_geo, alertas, img_mapa)` → `bytes` — gera PDF landscape com: mapa estático, seção de alertas, tabela IP resumo (com `ESTILO_LEGENDA`), tabela GPS resumo (com `ESTILO_LEGENDA`). As tabelas de alerta já possuem `_paragrafo_alerta()` como explicação e não recebem legenda adicional.

#### `utils/database.py`
Camada de persistência (SQLAlchemy + SQLite):
- Banco: `data/ressarcimento.db` — criado automaticamente ao importar o módulo via `inicializar_banco()`
- Tabelas: `fraudadores_identificados`, `historico_ressarcimentos`, `acumulados`
- Nunca criar tabelas manualmente — o banco é gerenciado pelo módulo

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

Atualização manual:
- `data/clubes.csv` — colunas: `clube_id`, `clube_nome`, `liga_id`, `liga_nome`
- `data/ligas.csv` — colunas: `liga_id`, `nome-liga`, `idioma`, `handicap`, `moeda`, `taxa-liga`
- `data/ressarcimento.db` — SQLite, gerado automaticamente

---

### CLI — `projeto_payjump/cli/src/`

Módulos separados por responsabilidade:
- `arquivo_utils.py` — leitura/correção de XLSX malformados (fix no `styles.xml`)
- `processamento.py` — cálculos de premiação, KOs, payjump
- `io_utils.py` — helpers de entrada/saída
- `payjump.py` — orquestrador principal
- `atualiza_clubes.py` — sincronização do cadastro de clubes
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

### Geolocalização (página 5)
```
IP Report XLSX + GPS Report XLSX (backend)
    → preparar_dados_ip() + preparar_dados_gps()
    → buscar_localizacao_ips() [ip-api.com] + buscar_geocodificacao_reversa() [Nominatim]
    → detectar_alertas() → gerar_mapa_folium() [HTML interativo]
    → gerar_mapa_estatico() + gerar_pdf_geo() [PDF landscape]
```

### Payjump (página 2)
```
XLSX torneio → Correção de arquivo → Extração de jogadores/ranks/prêmios
    → Merge com clubes.csv → Distribuição proporcional de KOs → Cálculo payjump
    → Strings formatadas para sistema
```

### Ressarcimento (página 4)
```
CSV Snowflake → Identificação de fraudadores (SQLite) → Cálculo de saldo líquido por jogador
    → Distribuição proporcional dos fundos retidos → Separação: imediatos / acumulados / futuros
    → Exportação Excel (múltiplas abas)
```

---

## APIs externas

| API | Uso | Configuração |
|---|---|---|
| **ip-api.com** (`/batch`) | Geolocalização de IPs em lotes de até 100 | `URL_IP_API`, `TIMEOUT_IP_API = 15`, `LOTE_IP_API = 100` |
| **OpenStreetMap Nominatim** (`/reverse`) | Geocodificação reversa de coordenadas GPS | `URL_NOMINATIM`, `TIMEOUT_NOMINATIM = 10`, `DELAY_NOMINATIM = 1` (rate limiting) |
| **Snowflake** | Acesso apenas via export CSV (sem conexão direta) | — |

---

## Convenções importantes

- **Homepage**: o arquivo de entrada do Streamlit é `início.py` (não `app.py`)
- **Banco SQLite**: inicializado automaticamente ao importar `utils/database.py`. Não criar tabelas manualmente.
- **XLSX malformados**: arquivos do backend frequentemente estão com `styles.xml` corrompido. Sempre usar `arquivo_utils.py` para leitura.
- **Caminhos hardcoded**: sem `.env`. Ajustes de ambiente devem ser feitos diretamente nos arquivos.
- **Multiplicador de moeda**: ganhos e rake do Snowflake são multiplicados por `MULTIPLICADOR_MOEDA = 5` (conversão de chips para R$).
- **Limite de modalidade**: `LIMITE_MODALIDADE_CASH = 99` — linhas com `ID_MODALIDADE > 99` são torneios e removidas da análise de cash game (Snowflake).
- **Legendas nos PDFs**: todas as tabelas em todos os PDFs gerados pelo sistema possuem `story.append(Paragraph('...', ESTILO_LEGENDA))` imediatamente antes de `adicionar_tabela()`. Manter esse padrão ao adicionar novas tabelas.
- **`montar_tabela_comuns`**: backend usa sem `coluna_nome` (3 colunas, `COLS_3`); Snowflake usa com `coluna_nome='NOME_MESA'` (4 colunas, `COLS_4`).
- **Funções internas em `analise_geo.py`**: prefixo `_` indica uso exclusivamente interno ao módulo. Não chamar de outros arquivos.
- **Cache de geolocalização**: `cache_ips` e `cache_geo` são dicts mantidos no `st.session_state` para evitar requisições duplicadas entre interações do usuário.
- O projeto é de uso interno (licença proprietária). Dados sensíveis não devem sair dos sistemas internos.
