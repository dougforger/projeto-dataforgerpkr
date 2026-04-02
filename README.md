# Doug Forger PKR — Sistema de Análise e Segurança

![Versão](https://img.shields.io/badge/version-4.0-blue)

Sistema de integridade e análise de dados para a plataforma Suprema Poker. Reúne ferramentas de detecção de conluio, ressarcimento de vítimas, análise geográfica, visualização de hand history, distribuição de premiação em torneios, controle de despesas e gestão de protocolos do Pipefy.

---

## 🚀 Como usar

### Interface Web
```bash
cd projeto_payjump/web
uv sync
uv run streamlit run início.py
```

> Streamlit Cloud ainda usa `requirements.txt` (mantido em paralelo).
> Ao adicionar uma dependência: `uv add <pacote>` e depois
> `uv export --no-hashes -o requirements.txt`.

### Configuração do Supabase

Crie o arquivo `.streamlit/secrets.toml` com as credenciais:

```toml
SUPABASE_URL = "https://<projeto>.supabase.co"
SUPABASE_KEY = "<service_role_key>"
```

Execute `data/supabase_setup.sql` uma vez no SQL Editor do Supabase para criar todas as tabelas. Sem as credenciais, os módulos com fallback (Pipefy, Ressarcimento, Clubes, Ligas) usam SQLite/CSV automaticamente.

### Ferramentas CLI

#### IP Lookup
```bash
cd ip_lookup
pip install -r requirements.txt
# Adicione IPs em data/ips.txt (um por linha)
python src/ip_lookup.py
# Resultado: output/ip_geoloc.xlsx
```

#### Reverse Geocoding
```bash
cd reverse_geocode
pip install -r requirements.txt
# Adicione coordenadas em data/coords.csv (colunas: lat, lon)
python src/reverse_geocode.py
# Resultado: output/reverse_geocode.xlsx
```

---

## 🛠️ Ferramentas Disponíveis

### 📈 Análises — `pages/1_📈_Análises.py`

Detecção de conluio e padrões suspeitos a partir de dados do backend ou do Snowflake.

**Aba Backend** (upload XLSX exportado do sistema):
- Upload múltiplo de planilhas de histórico de mãos
- Análise de cash game: cruzamento de Hand IDs para identificar mesas compartilhadas
- Cálculo de ganhos líquidos e rake por jogador nas mesas em comum
- Percentual de sobreposição par a par
- Detalhamento interativo por mesa selecionada
- Análise de torneios: cruzamento de torneios com inscrição simultânea (MTT + SAT MTT Prize)
- Suporte a torneios satélite (evento `SAT MTT Prize` com `Association` no formato `XXXXX_GAMEID`)
- Detalhamento de torneio selecionado: prêmio, KOs e total por jogador
- Filtro de pares de jogadores por nome
- Relatório inline em Markdown com campo de observações
- Exportação de relatório em PDF com marca d'água, protocolo e legendas explicativas

**Aba Snowflake** (upload CSV exportado do Snowflake):
- Upload único de CSV com dados de mãos
- Merge automático com cadastros de clubes e ligas (Supabase ou CSV fallback)
- Aplicação de multiplicador de moeda por liga
- Filtragem automática de linhas de torneio (ID_MODALIDADE ≥ 100)
- Resumo dos jogadores: ID, nome, clube, total de mesas, ganhos e rake
- Cruzamento de mesas em comum entre todos os pares de jogadores
- Identificação de dispositivos compartilhados entre contas
- Geolocalização de IPs via ip-api.com com cache por sessão
- Geocodificação reversa de coordenadas GPS via OpenStreetMap Nominatim
- Alertas automáticos de compartilhamento (dispositivos, IPs, cidades)
- Exportação de relatório em PDF com protocolo e legendas explicativas

---

### 📊 Payjump — `pages/2_📊_Payjump.py`

Calculadora de ressarcimentos para torneios com reentrada, baseada na distribuição proporcional de KOs.

- Upload de arquivo XLSX "MTT Player List" exportado do backend
- Correção automática de XLSX malformados (fix no `styles.xml`)
- Exibição da lista completa de jogadores, ranks e prêmios
- Merge automático com cadastro de clubes (Supabase ou CSV fallback)
- Distribuição proporcional de KOs entre os jogadores
- Geração de strings formatadas para inserção no sistema

---

### 🔐 Gerador de Notificações — `pages/3_🔐_Gerador_de_Notificações.py`

*(Em desenvolvimento)*

Geração de notificações multilíngues para envio aos jogadores afetados por ações de segurança.

- Suporte previsto a português, inglês e espanhol
- Templates parametrizados por tipo de ocorrência
- Merge automático com dados de clube e liga para personalização
- Dados carregados do Supabase (`clubes`, `ligas`) com fallback para CSV

---

### 💲 Ressarcimento — `pages/4_💲_Ressarcimento.py`

Cálculo e distribuição de ressarcimentos para vítimas de contas fraudulentas.

- Upload de CSV exportado do Snowflake com colunas específicas de mãos
- Validação automática das colunas obrigatórias
- Carregamento de fraudadores conhecidos do banco (Supabase ou SQLite fallback)
- Gerenciamento de fraudadores: visualização, adição e remoção via interface
- Cálculo do saldo líquido afetado por fraudador
- Distribuição proporcional do ressarcimento entre as vítimas
- Separação automática entre pagamentos imediatos, acumulados e futuros
- Registro histórico de ressarcimentos realizados
- Exportação Excel com múltiplas abas

---

### 📝 Relatórios — `pages/5_📝_Relatórios.py`

Relatórios geográficos e de dispositivos com três abas integradas.

**Aba Consulta Manual (IP/GPS):**
- Consulta de endereços IP ou coordenadas GPS sem upload de arquivo

**Aba Importar Planilhas (IP/GPS):**
- Upload de IP Report XLSX e/ou GPS Report XLSX
- Geolocalização de IPs via ip-api.com em lotes de até 100 por requisição
- Geocodificação reversa de coordenadas GPS via OpenStreetMap Nominatim
- Mapa interativo Folium com camadas Ruas e Satélite
- Detecção de alertas: múltiplos países, IPs/dispositivos compartilhados, múltiplas cidades
- Exportação em PDF com tabelas de alertas e resumo geográfico

**Aba Dispositivos:**
- Upload de arquivos "Same Data With Players" exportados do backend (múltiplos)
- Censura automática dos identificadores de dispositivo (UUID parcial)
- Detecção de contas que aparecem em mais de um arquivo
- Exportação em PDF landscape com alertas cruzados

---

### 💵 Despesas Security — `pages/6_💵_Despesas.py`

Controle de despesas operacionais do time de segurança.

- Sincronização via upload do Excel de despesas (DELETE + INSERT, Excel é fonte de verdade)
- Filtros interativos por período, clube, liga e categoria
- Gráficos de evolução mensal e distribuição por categoria
- Exportação em PDF do relatório financeiro
- Status de conexão Supabase na sidebar

---

### 🃏 Hand History Viewer — `pages/7_🃏_Hand_History.py`

Visualizador de histórico de mãos exportado do backend, com filtros interativos e exportação em PDF.

- Upload do arquivo HTML exportado pelo backend (múltiplas mãos por arquivo)
- Seleção de "minhas contas" para revelar cartas e destacar mãos relevantes
- Modos de exibição de cartas: revelar minhas contas / revelar todos / ocultar todos
- Resultado acumulado por conta ao longo de todas as mãos exibidas
- Exportação em PDF com índice navegável clicável e links de volta ao índice

---

### 🔗 Pipefy — `pages/8_🔗_Pipefy.py`

Dashboard de protocolos de segurança sincronizados do Pipefy.

- Sincronização de cards via API Pipefy com barra de progresso
- Persistência no Supabase (`pipefy_cards`, `pipefy_sync`) com fallback SQLite
- Filtros por data, categoria, tipo de ocorrência, resultado e analista
- Métricas: total de protocolos, positivos, internos vs. denúncias, média diária
- Gráficos de resultado, tipo e categoria
- Análise de produtividade por analista (regime 12/36)
- Exportação em PDF do dashboard
- Status de conexão Supabase na sidebar

---

### ⚙️ Banco de Dados — `pages/9_⚙️_Banco_de_Dados.py`

Gerenciamento das tabelas de referência no Supabase.

**Clubes:**
- Upload da planilha de clubes exportada pelo sistema (aba Sheet1)
- Filtragem automática pelas ligas cadastradas
- Upsert no Supabase com contagem de inseridos e atualizados
- Visualização com filtros por nome e liga

**Ligas:**
- Sincronização completa a partir do `ligas.csv` local
- Adição e atualização manual de ligas via formulário (todos os campos)
- Visualização da tabela completa

---

## 📁 Estrutura do Projeto

```
projeto_payjump/
├── web/
│   ├── início.py                          # Homepage
│   ├── pages/
│   │   ├── 1_📈_Análises.py
│   │   ├── 2_📊_Payjump.py
│   │   ├── 3_🔐_Gerador_de_Notificações.py
│   │   ├── 4_💲_Ressarcimento.py
│   │   ├── 5_📝_Relatórios.py
│   │   ├── 6_💵_Despesas.py
│   │   ├── 7_🃏_Hand_History.py
│   │   ├── 8_🔗_Pipefy.py
│   │   └── 9_⚙️_Banco_de_Dados.py
│   ├── utils/
│   │   ├── supabase_client.py             # Conexão centralizada Supabase
│   │   ├── clubes_db.py                   # Persistência clubes (Supabase + CSV fallback)
│   │   ├── ligas_db.py                    # Persistência ligas (Supabase + CSV fallback)
│   │   ├── despesas_db.py                 # Persistência despesas (Supabase)
│   │   ├── pipefy_db.py                   # Persistência Pipefy (Supabase + SQLite fallback)
│   │   ├── ressarcimento_db.py            # Persistência ressarcimentos (Supabase + SQLite fallback)
│   │   ├── database.py                    # SQLAlchemy + SQLite (backend do ressarcimento_db)
│   │   ├── analise_backend.py             # Análise via XLSX do backend
│   │   ├── analise_snowflake.py           # Análise via CSV do Snowflake
│   │   ├── analise_geo.py                 # Análise geográfica e PDFs geo/dispositivos
│   │   ├── geolocation.py                 # Integração ip-api.com e Nominatim
│   │   ├── hand_history_parser.py         # Parser de HTML e geração de PDF do HH
│   │   ├── mapa_utils.py                  # Mapa Folium interativo (Streamlit)
│   │   ├── pdf_builder.py                 # Funções de construção de PDF (ReportLab)
│   │   ├── pdf_config.py                  # Estilos, fontes e configurações de PDF
│   │   ├── calculos.py                    # Lógica de cálculo de ressarcimento
│   │   └── arquivo_utils.py               # Leitura/correção de XLSX malformados
│   ├── data/
│   │   ├── clubes.csv                     # Fallback local de clubes
│   │   ├── ligas.csv                      # Fallback local de ligas
│   │   ├── pipefy.db                      # SQLite fallback do Pipefy
│   │   ├── ressarcimento.db               # SQLite fallback de ressarcimentos
│   │   └── supabase_setup.sql             # DDL completo de todas as tabelas
│   └── requirements.txt
├── cli/
│   └── src/
│       ├── payjump.py
│       ├── atualiza_clubes.py
│       └── gerar_ligas.py
ip_lookup/
│   ├── src/ip_lookup.py
│   └── data/ips.txt
reverse_geocode/
    ├── src/reverse_geocode.py
    └── data/coords.csv
```

---

## 🗄️ Banco de Dados — Supabase

Todas as tabelas são criadas pelo arquivo `data/supabase_setup.sql`.

| Tabela | Módulo responsável | Fallback |
|---|---|---|
| `security_despesas` | `despesas_db.py` | — (obrigatório) |
| `pipefy_cards` / `pipefy_sync` | `pipefy_db.py` | SQLite `pipefy.db` |
| `clubes` | `clubes_db.py` | `clubes.csv` |
| `ligas` | `ligas_db.py` | `ligas.csv` |
| `fraudadores_identificados` | `ressarcimento_db.py` | SQLite `ressarcimento.db` |
| `historico_ressarcimentos` | `ressarcimento_db.py` | SQLite `ressarcimento.db` |
| `acumulados` | `ressarcimento_db.py` | SQLite `ressarcimento.db` |

---

## 📊 Fontes de Dados

| Fonte | Formato | Usado em |
|---|---|---|
| Backend — histórico de mãos | XLSX (múltiplos arquivos) | Análises (aba Backend) |
| Backend — MTT Player List | XLSX | Payjump |
| Backend — IP Report | XLSX | Relatórios (aba Planilhas) |
| Backend — GPS Report | XLSX | Relatórios (aba Planilhas) |
| Backend — Same Data With Players | XLSX | Relatórios (aba Dispositivos) |
| Backend — Hand History | HTML | Hand History Viewer |
| Snowflake — mãos por conta | CSV | Análises (aba Snowflake), Ressarcimento |
| Excel de despesas | XLSX | Despesas Security |
| API Pipefy | REST | Pipefy |
| Supabase | REST (PostgREST) | Todas as páginas |

---

## 🔌 APIs Externas

| API | Uso |
|---|---|
| ip-api.com/batch | Geolocalização de IPs em lote (até 100 por requisição) |
| OpenStreetMap Nominatim | Geocodificação reversa de coordenadas GPS |
| Pipefy GraphQL API | Busca e sincronização de cards de segurança |
| Supabase REST (PostgREST) | Persistência centralizada de dados |

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.x**
- **Streamlit** — interface web
- **Supabase** — banco de dados principal (PostgreSQL via REST)
- **Pandas** — processamento de dados
- **ReportLab** — geração de PDFs
- **Folium / streamlit-folium** — mapas interativos
- **staticmap** — mapas estáticos para PDF
- **BeautifulSoup4** — parsing de HTML do hand history
- **OpenPyXL** — manipulação de Excel
- **SQLAlchemy + SQLite** — fallback local para Pipefy e Ressarcimento
- **Requests** — integração com APIs externas

---

## 🔒 Segurança e Privacidade

- Todos os cálculos são auditáveis e transparentes
- Dados permanecem sob controle do usuário (sem envio para servidores externos, exceto IPs para ip-api.com)
- Identificadores de dispositivo são automaticamente censurados nos relatórios
- Credenciais Supabase armazenadas em `.streamlit/secrets.toml` (não versionado)

---

## 📄 Licença

Sistema proprietário — Uso interno Suprema Poker

---

## 👤 Desenvolvido por

Douglas Armando Ferreira — Suprema Poker

Para suporte ou sugestões, entre em contato através dos canais internos.
