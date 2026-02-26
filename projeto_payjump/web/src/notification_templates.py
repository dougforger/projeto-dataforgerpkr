"""
Templates de Notificação Security PKR
Adicione novos templates seguindo o padrão existente.

Cada template tem:
- "label": nome exibido no selectbox
- "category": categoria para organização
- "fields": campos que o usuário vai preencher (além dos campos base)
- "generate": função que recebe os dados e retorna a mensagem formatada

Campos BASE (sempre disponíveis em todos os templates):
  - protocolo, clube, liga, data
"""

from datetime import date

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def _header(protocolo, clube, liga, data):
    return (
        f"Notificação Security PKR\n\n"
        f"Protocolo: #{protocolo}\n"
        f"Clube: {clube}\n"
        f"Liga: {liga}\n"
        f"Data: {data}\n"
    )

def _footer():
    return "\nSecurity PKR"

# ──────────────────────────────────────────────
# TEMPLATES
# ──────────────────────────────────────────────

TEMPLATES = [

    # ── CHAT ──────────────────────────────────
    {
        "label": "Suspensão de Chat",
        "category": "Chat",
        "fields": [
            {"key": "jogador",   "label": "Jogador (usuário + ID)",  "type": "text",   "placeholder": "sandrovig (304174)"},
            {"key": "motivo",    "label": "Motivo",                  "type": "text",   "placeholder": "abuso de chat"},
            {"key": "dias",      "label": "Duração (dias)",          "type": "number", "default": 30},
        ],
        "generate": lambda d: (
            _header(d["protocolo"], d["clube"], d["liga"], d["data"]) +
            f"\nFoi identificada violação dos termos de conduta envolvendo o jogador {d['jogador']}, "
            f"por {d['motivo']}, desse modo a conta em questão teve o chat suspenso por {d['dias']} dias. "
            f"Ao término do prazo o jogador deverá enviar email para security@suprema.group solicitando o reestabelecimento do chat."
            + _footer()
        ),
    },

    {
        "label": "Advertência de Chat",
        "category": "Chat",
        "fields": [
            {"key": "jogador", "label": "Jogador (usuário + ID)", "type": "text", "placeholder": "sandrovig (304174)"},
            {"key": "motivo",  "label": "Motivo",                 "type": "text", "placeholder": "linguagem ofensiva"},
        ],
        "generate": lambda d: (
            _header(d["protocolo"], d["clube"], d["liga"], d["data"]) +
            f"\nFoi identificada violação dos termos de conduta envolvendo o jogador {d['jogador']}, "
            f"por {d['motivo']}. O jogador recebe formalmente uma advertência. "
            f"Reincidências resultarão em suspensão ou banimento do chat."
            + _footer()
        ),
    },

    # ── CONTA ─────────────────────────────────
    {
        "label": "Banimento de Conta",
        "category": "Conta",
        "fields": [
            {"key": "jogador", "label": "Jogador (usuário + ID)", "type": "text", "placeholder": "sandrovig (304174)"},
            {"key": "motivo",  "label": "Motivo",                 "type": "text", "placeholder": "uso de software proibido"},
        ],
        "generate": lambda d: (
            _header(d["protocolo"], d["clube"], d["liga"], d["data"]) +
            f"\nApós investigação, foi confirmada violação grave dos termos de conduta pelo jogador {d['jogador']}, "
            f"por {d['motivo']}. Desse modo, a conta foi permanentemente banida da plataforma."
            + _footer()
        ),
    },

    {
        "label": "Suspensão Temporária de Conta",
        "category": "Conta",
        "fields": [
            {"key": "jogador", "label": "Jogador (usuário + ID)", "type": "text",   "placeholder": "sandrovig (304174)"},
            {"key": "motivo",  "label": "Motivo",                 "type": "text",   "placeholder": "comportamento suspeito"},
            {"key": "dias",    "label": "Duração (dias)",         "type": "number", "default": 7},
        ],
        "generate": lambda d: (
            _header(d["protocolo"], d["clube"], d["liga"], d["data"]) +
            f"\nFoi identificada violação dos termos de conduta pelo jogador {d['jogador']}, "
            f"por {d['motivo']}. A conta foi suspensa por {d['dias']} dias. "
            f"Ao término do prazo, o acesso será reestabelecido automaticamente."
            + _footer()
        ),
    },

    {
        "label": "Bloqueio de Saque",
        "category": "Conta",
        "fields": [
            {"key": "jogador", "label": "Jogador (usuário + ID)", "type": "text", "placeholder": "sandrovig (304174)"},
            {"key": "motivo",  "label": "Motivo",                 "type": "text", "placeholder": "verificação de identidade pendente"},
        ],
        "generate": lambda d: (
            _header(d["protocolo"], d["clube"], d["liga"], d["data"]) +
            f"\nInformamos que os saques da conta do jogador {d['jogador']} foram temporariamente bloqueados "
            f"devido a: {d['motivo']}. Para regularização, o jogador deve contatar security@suprema.group."
            + _footer()
        ),
    },

    # ── FAIR PLAY ─────────────────────────────
    {
        "label": "Advertência de Fair Play",
        "category": "Fair Play",
        "fields": [
            {"key": "jogador", "label": "Jogador (usuário + ID)", "type": "text", "placeholder": "sandrovig (304174)"},
            {"key": "motivo",  "label": "Motivo",                 "type": "text", "placeholder": "abandono de mesas"},
        ],
        "generate": lambda d: (
            _header(d["protocolo"], d["clube"], d["liga"], d["data"]) +
            f"\nFoi registrada infração de Fair Play pelo jogador {d['jogador']}, "
            f"referente a: {d['motivo']}. O jogador recebe advertência formal. "
            f"Reincidências poderão resultar em restrições à conta."
            + _footer()
        ),
    },

    {
        "label": "Uso de Software Proibido",
        "category": "Fair Play",
        "fields": [
            {"key": "jogador",  "label": "Jogador (usuário + ID)", "type": "text", "placeholder": "sandrovig (304174)"},
            {"key": "software", "label": "Software identificado",  "type": "text", "placeholder": "HUD / solver em tempo real"},
        ],
        "generate": lambda d: (
            _header(d["protocolo"], d["clube"], d["liga"], d["data"]) +
            f"\nFoi confirmado o uso de software não autorizado ({d['software']}) pelo jogador {d['jogador']}. "
            f"Tal prática viola os termos de conduta da plataforma. "
            f"A conta foi penalizada conforme política de Fair Play vigente."
            + _footer()
        ),
    },

    {
        "label": "Conluio / Chip Dumping",
        "category": "Fair Play",
        "fields": [
            {"key": "jogadores", "label": "Jogadores envolvidos", "type": "textarea", "placeholder": "jogador1 (ID), jogador2 (ID)"},
            {"key": "descricao", "label": "Descrição da infração", "type": "textarea", "placeholder": "Transferência suspeita de fichas entre contas"},
        ],
        "generate": lambda d: (
            _header(d["protocolo"], d["clube"], d["liga"], d["data"]) +
            f"\nApós análise, foi identificada prática de conluio/chip dumping envolvendo os seguintes jogadores: "
            f"{d['jogadores']}. Descrição: {d['descricao']}. "
            f"As contas foram penalizadas conforme política de integridade da plataforma."
            + _footer()
        ),
    },

    # ── FINANCEIRO ────────────────────────────
    {
        "label": "Estorno de Fichas",
        "category": "Financeiro",
        "fields": [
            {"key": "jogador", "label": "Jogador (usuário + ID)", "type": "text",   "placeholder": "sandrovig (304174)"},
            {"key": "valor",   "label": "Valor estornado",        "type": "text",   "placeholder": "R$ 500,00"},
            {"key": "motivo",  "label": "Motivo do estorno",      "type": "text",   "placeholder": "erro de sistema"},
        ],
        "generate": lambda d: (
            _header(d["protocolo"], d["clube"], d["liga"], d["data"]) +
            f"\nInformamos que foi realizado o estorno de {d['valor']} para a conta do jogador {d['jogador']}, "
            f"referente a: {d['motivo']}. O valor já está disponível na conta."
            + _footer()
        ),
    },

    # ── VERIFICAÇÃO ───────────────────────────
    {
        "label": "Solicitação de Verificação de Identidade",
        "category": "Verificação",
        "fields": [
            {"key": "jogador", "label": "Jogador (usuário + ID)", "type": "text",     "placeholder": "sandrovig (304174)"},
            {"key": "prazo",   "label": "Prazo para envio",       "type": "text",     "placeholder": "7 dias"},
            {"key": "docs",    "label": "Documentos solicitados", "type": "textarea", "placeholder": "RG ou CNH + comprovante de residência"},
        ],
        "generate": lambda d: (
            _header(d["protocolo"], d["clube"], d["liga"], d["data"]) +
            f"\nSolicitamos ao jogador {d['jogador']} o envio dos seguintes documentos para verificação de identidade: "
            f"{d['docs']}. O prazo para envio é de {d['prazo']}. "
            f"Documentos devem ser encaminhados para security@suprema.group. "
            f"A ausência de retorno poderá resultar em restrições à conta."
            + _footer()
        ),
    },

    # ── INFORMATIVO ───────────────────────────
    {
        "label": "Comunicado Geral",
        "category": "Informativo",
        "fields": [
            {"key": "assunto", "label": "Assunto",    "type": "text",     "placeholder": "Atualização de termos de conduta"},
            {"key": "corpo",   "label": "Mensagem",   "type": "textarea", "placeholder": "Descreva o comunicado..."},
        ],
        "generate": lambda d: (
            _header(d["protocolo"], d["clube"], d["liga"], d["data"]) +
            f"\nAssunto: {d['assunto']}\n\n{d['corpo']}"
            + _footer()
        ),
    },

]

# ──────────────────────────────────────────────
# ÍNDICES PARA O SELECTBOX
# ──────────────────────────────────────────────

def get_template_labels():
    """Retorna lista de labels agrupados por categoria para o selectbox."""
    seen_cats = []
    options = []
    for t in TEMPLATES:
        cat = t["category"]
        if cat not in seen_cats:
            seen_cats.append(cat)
        options.append(f"{cat} › {t['label']}")
    return options

def get_template_by_label(full_label: str):
    """Retorna o template a partir do label completo (Categoria › Nome)."""
    for t in TEMPLATES:
        if f"{t['category']} › {t['label']}" == full_label:
            return t
    return None