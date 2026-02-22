import streamlit as st

# Configurações da página
st.set_page_config(
    page_title = 'Doug Forger PKR',
    page_icon = '🔒',
    layout = 'wide',
    initial_sidebar_state = 'expanded'
)

# Homepage
st.title('🔒 Doug Forger PKR')
st.subheader('Sistema de Análise e Segurança de Poker Online')
st.markdown('---')

st.markdown("""
### Bem-vindo ao sistema de integridade e análise de dados

Ferramentas desenvolvidas para garantir o jogo limpo e facilitar a gestão operacional de partidas de poker online.

#### 🛠️ Ferramentas Disponíveis:

**📊 Calculadora de Payjump**
- Cálculo automatizado de ressarcimentos em torneios
- Distribuição proporcional de KOs
- Geração de strings formatadas para sistema

**🏢 Gestão de Clubes e Ligas**
- Visualização e atualização de clubes cadastrados
- Gerenciamento de ligas ativas
- Sincronização com planilhas do sistema

**🔍 Análise de Dados** *(em desenvolvimento)*
- Detecção de padrões suspeitos
- Relatórios de integridade
- Monitoramento de anomalias

---

👈 **Selecione uma ferramenta no menu lateral para começar**
""")

# Sidebar
with st.sidebar:
    st.markdown("### 🔒 Doug Forger PKR")
    st.markdown("**Sistema de Segurança**")
    st.markdown("---")
    st.info("""
    Desenvolvido para análise de dados
    a fim de garantir a integridade em
    plataformas de poker online.
    """)