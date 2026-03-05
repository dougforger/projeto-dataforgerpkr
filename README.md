# Doug Forger PKR - Sistema de Análise e Segurança

![Versão](https://img.shields.io/badge/version-1.0-blue)

Sistema de integridade e análise de dados para poker online.

## 🛠️ Ferramentas Disponíveis

### 🔍 Análise de Cruzamentos
Sistema de detecção de padrões suspeitos através de cruzamento de dados:

#### 📋 Aba Backend
- Upload múltiplo de planilhas exportadas do sistema
- Análise de frequência de mesas em comum entre jogadores suspeitos
- Cruzamento baseado em Hand ID para garantir simultaneidade
- Percentuais de sobreposição por par de jogadores
- Detalhamento por mesa com resumo de ganhos e rake
- Análise de torneios em comum com detalhamento de premiação e KOs
- Filtro de pares por jogador específico
- Geração de relatório em PDF com marca d'água

#### ❄️ Aba Snowflake
- Upload de CSV exportado do Snowflake
- Análise de frequência de mesas em comum
- Enriquecimento de IPs via ip-api.com
- Geolocalização via reverse geocoding
- Detecção de IP, dispositivo e cidade compartilhados entre contas

### 📊 Calculadora de Payjump
Cálculo automatizado de ressarcimentos em torneios:
- Distribuição proporcional de KOs
- Ajuste de blinds por liga
- Geração de strings formatadas

### 📢 Gerador de Notificações *(em desenvolvimento)*
Sistema automatizado de comunicação com jogadores:
- Geração de notificações personalizadas
- Templates para diferentes tipos de comunicação
- Integração com sistemas de mensageria
- Histórico de notificações enviadas

### 💰 Ressarcimento de Bots
Sistema de cálculo de ressarcimentos para contas suspeitas:
- Upload de dados do Snowflake
- Conversão automática de moedas
- Acumulação de valores pendentes
- Separação entre ressarcimentos imediatos e futuros
- Exportação em múltiplos formatos (String, CSV, Excel)

### 🏢 Gestão de Clubes e Ligas
- Visualização de clubes cadastrados
- Gerenciamento de ligas ativas
- Sincronização com planilhas

**Ferramentas CLI disponíveis:**
- `ip_lookup/`: Consulta batch de IPs com geolocalização
- `reverse_geocode/`: Conversão de coordenadas para endereços

---

## 🚀 Como usar

### Localmente (Web Interface)
```bash
cd projeto_payjump/web
pip install -r requirements.txt
streamlit run app.py
```

### Ferramentas CLI

#### IP Lookup
```bash
cd ip_lookup
pip install -r requirements.txt
# Adicione IPs no arquivo data/ips.txt (um por linha)
python src/ip_lookup.py
# Resultado gerado em output/ip_geoloc.xlsx
```

#### Reverse Geocoding
```bash
cd reverse_geocode
pip install -r requirements.txt
# Adicione coordenadas no arquivo data/coords.csv (colunas: lat,lon)
python src/reverse_geocode.py
# Resultado gerado em output/reverse_geocode.xlsx
```

### Deploy (Streamlit Cloud)
1. Conecte o repositório ao Streamlit Cloud
2. Configure o caminho: `projeto_payjump/web/app.py`
3. Deploy automático

---

## 📁 Estrutura do Projeto
```
projeto_payjump/
├── web/                          # Interface Streamlit
│   ├── app.py                   # Página principal
│   ├── pages/                   # Ferramentas
|   |   ├── 1_📈_Análises.py
│   │   ├── 2_📊_Payjump.py
|   |   ├── 3_🔐_Gerador_de_Notificações.py
│   │   └── 4_💲_Ressarcimento.py
│   └── data/                    # Dados estáticos
│       ├── clubes.csv
│       └── ligas.csv
├── cli/                         # Scripts de linha de comando
│   └── src/
│       ├── payjump.py          # Versão CLI do payjump
│       ├── atualiza_clubes.py  # Atualização de cadastros
│       └── gerar_ligas.py      # Geração de ligas
├── ip_lookup/                   # Geolocalização de IPs
│   ├── src/
│   │   └── ip_lookup.py
│   ├── data/
│   │   └── ips.txt
│   └── output/
└── reverse_geocode/             # Geocodificação reversa
    ├── src/
    │   └── reverse_geocode.py
    ├── data/
    │   └── coords.csv
    └── output/
```

---

## 📊 Estrutura de Dados

### Arquivos necessários (incluídos no repositório):
- `web/data/clubes.csv` - Cadastro de clubes
  - Colunas: `id-clube`, `nome-clube`, `id-liga`, `nome-liga`
- `web/data/ligas.csv` - Cadastro de ligas com moedas e handicaps
  - Colunas: `id-liga`, `nome-liga`, `idioma`, `handicap`, `moeda`

### Arquivos gerados pelo usuário:
- CSV exportado do Snowflake (upload manual)
- CSV de acumulados (download/upload entre semanas)
- Arquivos de análise de IPs e coordenadas

---

## 🔍 Análises de Integridade

### Detecção de Padrões Suspeitos

O sistema oferece múltiplas camadas de análise:

1. **Análise Comportamental**
   - Mãos com ganhos/perdas acima do limite calculado
   - Identificação de bots através de padrões de jogo
   - Cálculo de ressarcimentos proporcionais

2. **Análise Geográfica**
   - Geolocalização por IP
   - Identificação de múltiplas contas no mesmo local
   - Cruzamento de dados geográficos com padrões de jogo

3. **Análise de Rede**
   - Detecção de clusters de jogadores
   - Identificação de contas relacionadas
   - Padrões de transferência suspeitos

---

## 🔒 Segurança e Privacidade

- Sistema desenvolvido para garantir integridade em plataformas de poker online
- Todos os cálculos são auditáveis e transparentes
- Dados permanecem sob controle do usuário
- Logs de análise para auditoria
- Sem armazenamento de dados sensíveis em servidores externos

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.x**
- **Streamlit** - Interface web
- **Pandas** - Processamento de dados
- **OpenPyXL** - Manipulação de Excel
- **Requests** - Consultas de geolocalização
- **Snowflake** - Banco de dados (acesso via export)

---

## 📝 Roadmap

### Em Desenvolvimento
- [ ] Sistema completo de análise de cruzamentos
- [ ] Gerador automático de notificações
- [ ] Dashboard de analytics
- [ ] Histórico de ressarcimentos
- [ ] API para integração com outros sistemas

### Futuras Implementações
- [ ] Integração com Google Sheets
- [ ] Relatórios PDF automatizados
- [ ] Sistema de permissões por usuário

---

## 📄 Licença

Sistema proprietário - Uso interno

---

## 👥 Desenvolvido por

Douglas Armando Ferreira - Suprema Poker

Para suporte ou sugestões, entre em contato através dos canais internos.