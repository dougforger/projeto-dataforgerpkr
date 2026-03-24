"""
Página: Notificações Security PKR
Integre ao payjum adicionando esta página na pasta `pages/`
e o arquivo notification_templates.py na raiz do projeto.
"""

import streamlit as st
from datetime import date
from projeto_payjump.web.src.notification_templates import TEMPLATES, get_template_labels, get_template_by_label

# ──────────────────────────────────────────────
# CONFIG DA PÁGINA
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="Notificações Security PKR",
    page_icon="🔐",
    layout="centered",
)

# ──────────────────────────────────────────────
# CSS — visual alinhado ao payjum (dark-friendly)
# ──────────────────────────────────────────────

st.markdown("""
<style>
    .notif-box {
        background: #1e1e2e;
        border: 1px solid #313149;
        border-radius: 10px;
        padding: 20px 24px;
        font-family: monospace;
        font-size: 14px;
        white-space: pre-wrap;
        color: #cdd6f4;
        line-height: 1.7;
        margin-top: 8px;
    }
    .section-title {
        font-size: 13px;
        font-weight: 600;
        color: #a6adc8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 4px;
        margin-top: 20px;
    }
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }
    .copy-btn > button {
        background-color: #313149;
        color: #cdd6f4;
        border: 1px solid #45475a;
    }
    .copy-btn > button:hover {
        background-color: #45475a;
    }
    hr { border-color: #313149; margin: 24px 0; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────

st.markdown("## 🔐 Notificações Security PKR")
st.caption("Gere notificações padronizadas para envio via WhatsApp.")
st.markdown("---")

# ──────────────────────────────────────────────
# SELEÇÃO DE TEMPLATE
# ──────────────────────────────────────────────

labels = get_template_labels()

st.markdown('<p class="section-title">Tipo de Notificação</p>', unsafe_allow_html=True)
selected_label = st.selectbox(
    "Tipo",
    options=labels,
    label_visibility="collapsed",
)

template = get_template_by_label(selected_label)

st.markdown("---")

# ──────────────────────────────────────────────
# CAMPOS BASE (sempre presentes)
# ──────────────────────────────────────────────

st.markdown('<p class="section-title">Dados Base</p>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    protocolo = st.text_input("Protocolo", placeholder="1300989385")
    clube     = st.text_input("Clube", placeholder="H2 Club 3 (10634)")
with col2:
    liga = st.text_input("Liga", placeholder="Suprema (106)")
    data = st.date_input("Data", value=date.today(), format="DD/MM/YYYY")

data_str = data.strftime("%d/%m/%Y")

# ──────────────────────────────────────────────
# CAMPOS DINÂMICOS DO TEMPLATE
# ──────────────────────────────────────────────

if template and template.get("fields"):
    st.markdown("---")
    st.markdown('<p class="section-title">Detalhes da Ocorrência</p>', unsafe_allow_html=True)

    dynamic_values = {}
    for field in template["fields"]:
        key      = field["key"]
        label    = field["label"]
        ftype    = field.get("type", "text")
        ph       = field.get("placeholder", "")
        default  = field.get("default", "")

        if ftype == "text":
            dynamic_values[key] = st.text_input(label, placeholder=ph)
        elif ftype == "number":
            dynamic_values[key] = st.number_input(label, min_value=1, value=int(default) if default else 1, step=1)
        elif ftype == "textarea":
            dynamic_values[key] = st.text_area(label, placeholder=ph, height=80)

# ──────────────────────────────────────────────
# GERAR NOTIFICAÇÃO
# ──────────────────────────────────────────────

st.markdown("---")

if st.button("⚡ Gerar Notificação", type="primary", width='stretch'):

    # Validação mínima
    missing = []
    if not protocolo: missing.append("Protocolo")
    if not clube:     missing.append("Clube")
    if not liga:      missing.append("Liga")
    if template:
        for field in template.get("fields", []):
            val = dynamic_values.get(field["key"], "")
            if field.get("type") != "number" and not str(val).strip():
                missing.append(field["label"])

    if missing:
        st.warning(f"Preencha os campos obrigatórios: **{', '.join(missing)}**")
    else:
        # Monta dict completo
        data_completa = {
            "protocolo": protocolo,
            "clube":     clube,
            "liga":      liga,
            "data":      data_str,
            **{k: str(v) for k, v in dynamic_values.items()},
        }

        mensagem = template["generate"](data_completa)
        st.session_state["mensagem_gerada"] = mensagem

# ──────────────────────────────────────────────
# EXIBIÇÃO + COPIAR
# ──────────────────────────────────────────────

if "mensagem_gerada" in st.session_state and st.session_state["mensagem_gerada"]:
    msg = st.session_state["mensagem_gerada"]

    st.markdown("---")
    st.markdown('<p class="section-title">📋 Mensagem Gerada</p>', unsafe_allow_html=True)
    st.markdown(f'<div class="notif-box">{msg}</div>', unsafe_allow_html=True)

    st.markdown("")

    # Botão copiar via JS
    escaped = msg.replace("`", "\\`").replace("\\", "\\\\")
    copy_js = f"""
        <script>
        function copyMsg() {{
            navigator.clipboard.writeText(`{escaped}`).then(() => {{
                const btn = document.getElementById('copyBtn');
                btn.innerText = '✅ Copiado!';
                setTimeout(() => btn.innerText = '📋 Copiar Mensagem', 2000);
            }});
        }}
        </script>
        <button id="copyBtn" onclick="copyMsg()"
            style="width:100%;padding:10px;border-radius:8px;border:1px solid #45475a;
                   background:#313149;color:#cdd6f4;font-size:15px;font-weight:600;
                   cursor:pointer;margin-top:8px;">
            📋 Copiar Mensagem
        </button>
    """
    st.components.v1.html(copy_js, height=60)

    # ── WHATSAPP (preparado para API) ─────────
    st.markdown("")
    with st.expander("📲 Enviar via WhatsApp (API — em breve)", expanded=False):
        st.info(
            "Quando você tiver o token da **Cloud API da Meta**, "
            "adicione-o nas variáveis de ambiente (`WA_TOKEN` e `WA_PHONE_ID`) "
            "e descomente o bloco de envio abaixo.",
            icon="ℹ️"
        )
        numero_dest = st.text_input(
            "Número de destino",
            placeholder="5511999999999  (com DDI, sem + ou espaços)"
        )

        if st.button("📲 Enviar via WhatsApp", disabled=True, width='stretch'):
            # ── DESCOMENTE QUANDO TIVER O TOKEN ──────────────────────────
            # import os, requests
            # token    = os.environ["WA_TOKEN"]
            # phone_id = os.environ["WA_PHONE_ID"]
            # url      = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
            # payload  = {
            #     "messaging_product": "whatsapp",
            #     "to": numero_dest,
            #     "type": "text",
            #     "text": {"body": msg},
            # }
            # resp = requests.post(url, json=payload,
            #                      headers={"Authorization": f"Bearer {token}"})
            # if resp.status_code == 200:
            #     st.success("Mensagem enviada com sucesso!")
            # else:
            #     st.error(f"Erro ao enviar: {resp.text}")
            # ─────────────────────────────────────────────────────────────
            pass

    st.markdown("")
    if st.button("🔄 Nova Notificação", width='stretch'):
        del st.session_state["mensagem_gerada"]
        st.rerun()