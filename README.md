# Doug Forger PKR — Sistema de Análise e Segurança

![Versão](https://img.shields.io/badge/version-2.0-blue)

Sistema de integridade e análise de dados para a plataforma Suprema Poker. Reúne ferramentas de detecção de conluio, ressarcimento de vítimas, análise geográfica e distribuição de premiação em torneios.

---

## 🚀 Como usar

### Interface Web
```bash
cd projeto_payjump/web
pip install -r requirements.txt
streamlit run início.py
```

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
- Merge automático com cadastros de clubes e ligas
- Aplicação de multiplicador de moeda por liga
- Filtragem automática de linhas de torneio (ID_MODALIDADE ≥ 100)
- Resumo dos jogadores: ID, nome, clube, total de mesas, ganhos e rake
- Cruzamento de mesas em comum entre todos os pares de jogadores
- Identificação de dispositivos compartilhados entre contas
- Geolocalização de IPs via ip-api.com com cache por sessão
- Geocodificação reversa de coordenadas GPS via OpenStreetMap Nominatim
- Alertas automáticos de compartilhamento (dispositivos, IPs, cidades)
- Detalhamento por mesa: ganhos, rake e histórico de mãos por jogador
- Exportação de relatório em PDF com protocolo e legendas explicativas

---

### 📊 Payjump — `pages/2_📊_Payjump.py`

Calculadora de ressarcimentos para torneios com reentrada, baseada na distribuição proporcional de KOs.

- Upload de arquivo XLSX "MTT Player List" exportado do backend
- Validação do nome do arquivo
- Correção automática de XLSX malformados (fix no `styles.xml`)
- Exibição da lista completa de jogadores, ranks e prêmios
- Merge automático com `data/clubes.csv` para identificação de clube
- Distribuição proporcional de KOs entre os jogadores
- Geração de strings formatadas para inserção no sistema

---

### 🔐 Gerador de Notificações — `pages/3_🔐_Gerador_de_Notificações.py`

*(Em desenvolvimento)*

Geração de notificações multilíngues para envio aos jogadores afetados por ações de segurança.

- Suporte previsto a português, inglês e espanhol
- Templates parametrizados por tipo de ocorrência
- Merge automático com dados de clube e liga para personalização
- Integração com cadastros de ligas e idiomas (`data/clubes.csv`, `data/ligas.csv`)

---

### 💲 Ressarcimento — `pages/4_💲_Ressarcimento.py`

Cálculo e distribuição de ressarcimentos para vítimas de contas fraudulentas.

- Upload de CSV exportado do Snowflake com colunas específicas de mãos
- Validação automática das colunas obrigatórias
- Carregamento automático de fraudadores conhecidos do banco SQLite interno
- Gerenciamento de fraudadores: visualização, adição e remoção via interface
- Cálculo do saldo líquido afetado por fraudador
- Distribuição proporcional do ressarcimento entre as vítimas
- Separação automática entre pagamentos imediatos, acumulados e futuros
- Registro histórico de ressarcimentos realizados
- Exportação Excel com múltiplas abas

---

### 🌍 Geolocalização — `pages/5_🌍_Geolocalização.py`

Análise geográfica independente de contas investigadas a partir de relatórios de IP e GPS exportados do backend.

- Upload de IP Report XLSX e/ou GPS Report XLSX (detecção automática do tipo)
- Geolocalização de IPs via ip-api.com em lotes de até 100 por requisição
- Geocodificação reversa de coordenadas GPS via OpenStreetMap Nominatim
- Cache por sessão para evitar requisições duplicadas
- Marcadores coloridos por conta (paleta de até 10 cores)
- Mapa interativo (Folium) com camadas: Ruas (OpenStreetMap) e Satélite (Esri)
- Popups com nome do jogador, cidade, estado e país
- Detecção de alertas: múltiplos países, IPs compartilhados, múltiplas cidades, dispositivos compartilhados
- Exportação de relatório em PDF landscape com mapa estático, tabela de alertas e tabelas resumo de IP e GPS

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
│   │   └── 5_🌍_Geolocalização.py
│   ├── utils/
│   │   ├── analise_backend.py             # Análise via XLSX do backend
│   │   ├── analise_snowflake.py           # Análise via CSV do Snowflake
│   │   ├── analise_geo.py                 # Análise geográfica e geração de PDF geo
│   │   ├── geolocation.py                 # Integração ip-api.com e Nominatim
│   │   ├── pdf_builder.py                 # Funções de construção de PDF (ReportLab)
│   │   ├── pdf_config.py                  # Estilos e configurações de PDF
│   │   ├── calculos.py                    # Lógica de cálculo de ressarcimento
│   │   ├── database.py                    # SQLAlchemy + SQLite
│   │   └── arquivo_utils.py               # Leitura/correção de XLSX malformados
│   ├── data/
│   │   ├── clubes.csv
│   │   ├── ligas.csv
│   │   └── ressarcimento.db               # Gerado automaticamente
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

## 📊 Fontes de Dados

| Fonte | Formato | Usado em |
|---|---|---|
| Backend — histórico de mãos | XLSX (múltiplos arquivos) | Análises (aba Backend) |
| Backend — MTT Player List | XLSX | Payjump |
| Backend — IP Report | XLSX | Geolocalização |
| Backend — GPS Report | XLSX | Geolocalização |
| Snowflake — mãos por conta | CSV | Análises (aba Snowflake), Ressarcimento |
| `data/clubes.csv` | CSV estático | Análises, Payjump |
| `data/ligas.csv` | CSV estático | Análises (Snowflake) |

---

## 🔌 APIs Externas

| API | Uso |
|---|---|
| ip-api.com/batch | Geolocalização de IPs em lote (até 100 por requisição) |
| OpenStreetMap Nominatim | Geocodificação reversa de coordenadas GPS |

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.x**
- **Streamlit** — interface web
- **Pandas** — processamento de dados
- **ReportLab** — geração de PDFs
- **Folium** — mapas interativos
- **staticmap** — mapas estáticos para PDF
- **OpenPyXL** — manipulação de Excel
- **SQLAlchemy + SQLite** — banco de dados de ressarcimentos
- **Requests** — integração com APIs externas

---

## 🔒 Segurança e Privacidade

- Todos os cálculos são auditáveis e transparentes
- Dados permanecem sob controle do usuário (sem envio para servidores externos, exceto IPs para ip-api.com)
- Banco SQLite local para persistência de fraudadores e histórico de ressarcimentos

---

## 📄 Licença

Sistema proprietário — Uso interno Suprema Poker

---

## 👤 Desenvolvido por

Douglas Armando Ferreira — Suprema Poker

Para suporte ou sugestões, entre em contato através dos canais internos.
