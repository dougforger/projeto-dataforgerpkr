# Doug Forger PKR - Sistema de Análise e Segurança

![Versão](https://img.shields.io/badge/version-1.0-blue)

Sistema de integridade e análise de dados para poker online.

## 🛠️ Ferramentas Disponíveis

### 📊 Calculadora de Payjump
Cálculo automatizado de ressarcimentos em torneios:
- Distribuição proporcional de KOs
- Ajuste de blinds por liga
- Geração de strings formatadas

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

## 🚀 Como usar

### Localmente
```bash
cd projeto_payjump/web
pip install -r requirements.txt
streamlit run app.py
```

### Deploy (Streamlit Cloud)
1. Conecte o repositório ao Streamlit Cloud
2. Configure o caminho: `projeto_payjump/web/app.py`
3. Deploy automático

## 📁 Estrutura de Dados

### Arquivos necessários (incluídos no repositório):
- `data/clubes.csv` - Cadastro de clubes
- `data/ligas.csv` - Cadastro de ligas com moedas e handicaps

### Arquivos gerados pelo usuário:
- CSV exportado do Snowflake (upload manual)
- CSV de acumulados (download/upload entre semanas)

## 🔒 Segurança

Sistema desenvolvido para garantir integridade em plataformas de poker online.
Todos os cálculos são auditáveis e os dados permanecem sob controle do usuário.