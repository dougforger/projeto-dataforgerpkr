import streamlit as st

st.set_page_config(
    page_title='Doug Forger PKR',
    page_icon='🔒',
    layout='wide',
    initial_sidebar_state='expanded',
)

st.title('🔒 Doug Forger PKR')
st.subheader('Sistema de Análise e Segurança de Poker Online')
st.markdown('---')

st.markdown(
    'Ferramentas desenvolvidas para garantir a integridade do jogo e facilitar '
    'a gestão operacional da plataforma Suprema Poker.'
)

st.markdown('### 🛠️ Ferramentas disponíveis')

col_a, col_b, col_c = st.columns(3)

with col_a:
    st.markdown('''#### 📈 Análises
Detecção de conluio e padrões suspeitos de jogo a partir de arquivos exportados do backend e do Snowflake.

**Recursos:**
- Cruzamento de mãos de cash game e torneios entre múltiplas contas
- Identificação de mesas, dispositivos e IPs em comum
- Análise de geolocalização via GPS integrada ao relatório
- Relatório em PDF com marca d'água e legendas explicativas
- Suporte a torneios satélite (SAT MTT Prize)

**Fontes de dados:** exportação XLSX do backend · exportação CSV do Snowflake
''')

    st.markdown('''#### 💲 Ressarcimento
Cálculo e distribuição de ressarcimentos para vítimas de contas fraudulentas identificadas na plataforma.

**Recursos:**
- Upload de CSV exportado do Snowflake
- Registro de fraudadores em banco de dados interno (SQLite)
- Cálculo do saldo líquido proporcional por vítima
- Separação automática entre pagamentos imediatos, acumulados e futuros
- Exportação Excel com múltiplas abas

**Fonte de dados:** exportação CSV do Snowflake
''')

with col_b:
    st.markdown('''#### 📊 Payjump
Calculadora de ressarcimentos para torneios com reentrada, baseada na distribuição proporcional de KOs entre os jogadores.

**Recursos:**
- Upload de arquivo XLSX da lista de jogadores do torneio
- Correção automática de arquivos XLSX malformados
- Extração de jogadores, ranks e prêmios
- Merge automático com o cadastro de clubes e ligas
- Distribuição proporcional de KOs
- Geração de strings formatadas para inserção no sistema

**Fonte de dados:** MTT Player List XLSX exportado do backend
''')

    st.markdown('''#### 📝 Relatórios
Relatórios geográficos e de dispositivos a partir de exportações do backend, com mapa interativo e exportação em PDF.

**Recursos:**
- Consulta manual de IPs e coordenadas GPS (sem upload de arquivo)
- Upload de IP Report e GPS Report XLSX (detecção automática do tipo)
- Geolocalização de IPs via ip-api.com · geocodificação reversa via Nominatim
- Mapa interativo Folium com marcadores coloridos por conta
- Detecção de alertas: VPN, IPs/dispositivos compartilhados, múltiplas cidades
- Upload de relatório "Same Data With Players" para análise de dispositivos
- Alertas cruzados entre múltiplos arquivos de dispositivos
- Exportação em PDF (geolocalização e dispositivos)

**Fontes de dados:** IP Report XLSX · GPS Report XLSX · Same Data With Players XLSX
''')

with col_c:
    st.markdown('''#### 🔐 Gerador de Notificações
*(Em desenvolvimento)*

Geração de notificações multilíngues para envio aos jogadores afetados por ações de segurança.

**Recursos previstos:**
- Suporte a português, inglês e espanhol
- Templates parametrizados por tipo de ocorrência
- Merge automático com dados de clube e liga para personalização
- Integração com cadastro de ligas e idiomas

**Fonte de dados:** `data/clubes.csv` · `data/ligas.csv`
''')

    st.markdown('''#### 🃏 Hand History Viewer
Visualizador de histórico de mãos exportado do backend com filtros interativos e exportação em PDF.

**Recursos:**
- Parser do arquivo HTML exportado pelo backend (múltiplas mãos por arquivo)
- Seleção de "minhas contas" para revelar cartas e marcar mãos relevantes
- Filtro para exibir apenas mãos com as contas selecionadas
- Modos de exibição de cartas: revelar minhas contas / revelar todos / ocultar todos
- Métricas por mão: pote, rake, jogadores, rodadas
- Resultado acumulado por conta ao longo de todas as mãos exibidas
- Exportação em PDF com índice navegável e links internos

**Fonte de dados:** Hand History HTML exportado do backend
''')

st.markdown('---')
st.caption('👈 Selecione uma ferramenta no menu lateral para começar.')

with st.sidebar:
    st.markdown('### 🔒 Doug Forger PKR')
    st.markdown('**Sistema de Segurança**')
    st.markdown('---')
    st.info(
        'Desenvolvido para análise de dados a fim de garantir '
        'a integridade em plataformas de poker online.'
    )
