# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Comandos essenciais

### Interface Web (principal)
```bash
cd projeto_payjump/web
pip install -r requirements.txt
streamlit run app.py
```

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

## Arquitetura

O projeto é um sistema de análise de integridade e segurança para a plataforma Suprema Poker, dividido em dois modos: **web** (Streamlit) e **CLI**.

### Interface Web — `projeto_payjump/web/`

Segue o padrão multi-página do Streamlit. O `app.py` é a homepage; as páginas ficam em `pages/` e são auto-descobertas:

| Arquivo | Função |
|---|---|
| `pages/1_📈_Análises.py` | Detecção de conluio — cruzamento de mãos, IPs, geolocalização. Exporta PDF com marca d'água. |
| `pages/2_📊_Payjump.py` | Calculadora de ressarcimentos em torneios (upload XLSX + merge com configs). |
| `pages/3_🔐_Gerador_de_Notificações.py` | Geração de notificações multilíngues para jogadores. |
| `pages/4_💲_Ressarcimento.py` | Cálculo de ressarcimentos por bots — upload CSV Snowflake, distribuição proporcional, exportação Excel. |

**Camada de banco de dados** (`utils/database.py`): SQLAlchemy + SQLite (`data/ressarcimento.db`, criado automaticamente). Três tabelas: `fraudadores_identificados`, `historico_ressarcimentos`, `acumulados`.

**Templates de notificação** (`src/modelos_notificacao.py`): sistema de templates com suporte a português, inglês e espanhol.

**Dados estáticos** (atualização manual):
- `data/clubes.csv` — colunas: `id-clube`, `nome-clube`, `id-liga`, `nome-liga`
- `data/ligas.csv` — colunas: `id-liga`, `nome-liga`, `idioma`, `handicap`, `moeda`, `taxa-liga`

### CLI — `projeto_payjump/cli/src/`

Módulos separados por responsabilidade:
- `arquivo_utils.py` — leitura/correção de XLSX malformados (fix no `styles.xml`)
- `processamento.py` — cálculos de premiação, KOs, payjump
- `io_utils.py` — helpers de entrada/saída
- `payjump.py` — orquestrador principal
- `atualiza_clubes.py` — sincronização do cadastro de clubes
- `gerar_ligas.py` — gerador de ligas

### Fluxo de dados — Ressarcimento (página principal)

```
CSV Snowflake → Identificação de fraudadores (SQLite) → Cálculo de saldo líquido por jogador
→ Distribuição proporcional dos fundos retidos → Separação: imediatos / acumulados / futuros
→ Exportação Excel (múltiplas abas)
```

### Fluxo de dados — Payjump (CLI e Web)

```
XLSX torneio → Correção de arquivo → Extração de jogadores/ranks/prêmios
→ Merge com clubes.csv → Distribuição proporcional de KOs → Cálculo payjump
→ Strings formatadas para sistema
```

### APIs externas

- **ip-api.com** — geolocalização batch de IPs (100 por requisição)
- **OpenStreetMap Nominatim** — geocodificação reversa (respeitar rate limiting)
- **Snowflake** — acesso apenas via export CSV (sem conexão direta)

## Convenções importantes

- O banco SQLite é inicializado automaticamente ao importar `utils/database.py` via `inicializar_banco()`. Não criar tabelas manualmente.
- Os arquivos XLSX de entrada frequentemente estão malformados — o código em `arquivo_utils.py` corrige o `styles.xml` antes de processar. Sempre usar essas funções ao ler Excel.
- Caminhos são hardcoded (sem `.env`). Ajustes de ambiente devem ser feitos diretamente nos arquivos.
- O projeto é de uso interno (licença proprietária). Dados sensíveis não devem sair dos sistemas internos.
