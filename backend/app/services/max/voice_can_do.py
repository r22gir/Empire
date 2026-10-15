"""Voice 'can you do X' answers from a fixed capability list.

Voice Max-e answers capability questions from this list — it does not guess
and it does not invent tools. 'Can you send me X' is an action: call
send_me_link, never a canned yes.
"""
from __future__ import annotations

import re
from typing import Any, Optional

_CAN_YOU_RE = re.compile(
    r"(?i)^\s*(?:"
    r"(?:hey\s+|ok\s+|okay\s+)?(?:max(?:-e)?[, ]+)?"
    r"(?:can|could|will|would)\s+you\s+(?:please\s+)?"
    r"|(?:are|is)\s+you\s+able\s+to\s+"
    r"|(?:do\s+you\s+(?:know\s+how\s+to|support|handle|have))\s+"
    r"|(?:puedes|podr[ií]as|podes|sos\s+capaz\s+de)\s+(?:hacer\s+)?"
    r")"
    r"(.+?)\s*\??\s*$"
)

_PURE_CAPABILITY = re.compile(
    r"(?i)^\s*(?:"
    r"(?:are|is)\s+you\s+able\s+to\s+"
    r"|(?:do\s+you\s+(?:know\s+how\s+to|support|handle|have))\s+"
    r"|(?:sos\s+capaz\s+de|sabes\s+c[oó]mo)\s+"
    r")"
)

_ACTION_TOOLS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)\b(?:send|email|whatsapp|m[aá]nda|env[ií]a)\b.+\b(?:drawing|dibujo|link|enlace|doc|file|3\s*-?\s*d)\b"
                r"|\b(?:3\s*-?\s*d|drawing|dibujo).+\b(?:whatsapp|email|send)\b"
                r"|\b(?:send|m[aá]nda|env[ií]a)\s+me\b"),
     "send_me_link"),
    (re.compile(r"(?i)\b(?:check|see|show|list|look\s*up)\b.+\b(?:calendar|schedule|agenda|horario|calendario)\b"
                r"|\b(?:calendar|schedule|agenda)\b"),
     "get_today_agenda"),
    (re.compile(r"(?i)\b(?:check|get|what(?:'s| is))?\s*(?:the\s+)?weather\b|\bclima\b"),
     "get_weather"),
)

VOICE_CAPABILITY_LIST: tuple[dict[str, object], ...] = (
    {
        "id": "today_agenda",
        "keys": (
            "calendar", "schedule", "agenda", "what's on today", "whats on today",
            "today", "horario", "calendario", "qué hay hoy", "que hay hoy",
        ),
        "can": True,
        "en": "Yes. I check the calendar, Organizer, and today's tasks with my tools and list what's on.",
        "es": "Sí. Reviso el calendario, el Organizer y las tareas de hoy con mis herramientas y te listo lo que hay.",
    },
    {
        "id": "send_me_link",
        "keys": (
            "send me this link", "send me the link", "send this link", "send me a link",
            "email me", "whatsapp me", "send me the drawing", "send me the 3d",
            "mándame el enlace", "mandame el enlace", "envíame el link", "enviame el link",
        ),
        "can": True,
        "en": "Yes. I can send a link or document only to your WhatsApp and email on this instance.",
        "es": "Sí. Puedo mandar un enlace o documento solo a tu WhatsApp y a tu correo de esta instancia.",
    },
    {
        "id": "find_files",
        "keys": (
            "find files", "find a file", "find the drawing", "look up a file",
            "search files", "encontrar archivos", "buscar el dibujo",
        ),
        "can": True,
        "en": "Yes. I search this instance's files and can send a matching doc to you.",
        "es": "Sí. Busco los archivos de esta instancia y te puedo mandar el documento que coincida.",
    },
    {
        "id": "quotes",
        "keys": (
            "quotes", "quote", "estimate", "cotización", "cotizacion", "look up a quote",
        ),
        "can": True,
        "en": "Yes. I look up quotes and estimates with the quote tools.",
        "es": "Sí. Busco cotizaciones y estimates con las herramientas de quotes.",
    },
    {
        "id": "tasks",
        "keys": ("tasks", "task", "to-do", "todo", "tareas", "organizer"),
        "can": True,
        "en": "Yes. I read tasks and Organizer items with the task tools.",
        "es": "Sí. Leo tareas e items del Organizer con las herramientas de tasks.",
    },
    {
        "id": "email_read",
        "keys": ("check email", "read email", "inbox", "correo", "revisar el correo"),
        "can": True,
        "en": "Yes. I can read the inbox. Sending from voice only goes to your own WhatsApp or email.",
        "es": "Sí. Puedo leer el correo. Desde voz solo mando a tu WhatsApp o a tu correo.",
    },
    {
        "id": "weather",
        "keys": ("weather", "forecast", "clima", "el tiempo"),
        "can": True,
        "en": "Yes. I check the weather with get_weather.",
        "es": "Sí. Reviso el clima con get_weather.",
    },
    {
        "id": "services",
        "keys": ("services", "health", "avatar", "are you working", "servicios"),
        "can": True,
        "en": "Yes. I check Empire services, including the avatar, with the health tool.",
        "es": "Sí. Reviso los servicios, incluyendo el avatar, con la herramienta de health.",
    },
    {
        "id": "improvements",
        "keys": ("file an improvement", "change request", "fix empire", "mejora"),
        "can": True,
        "en": "Yes. I can file an improvement for your approval. I do not deploy.",
        "es": "Sí. Puedo archivar una mejora para tu aprobación. No hago deploy.",
    },
    {
        "id": "client_email",
        "keys": (
            "email a client", "email the client", "send to a client", "email the brothers",
            "email rafa22", "send to rafa22giraldo",
        ),
        "can": False,
        "en": "No. I do not email clients, the other brother, or Studio addresses. I only send to your WhatsApp and email.",
        "es": "No. No mando correo a clientes, al otro hermano ni a direcciones del Studio. Solo a tu WhatsApp y a tu correo.",
    },
    {
        "id": "approve_deploy",
        "keys": ("approve a quote", "deploy", "run shell", "delete files"),
        "can": False,
        "en": "No. From voice I cannot approve quotes, deploy, run shell, or delete files. I can queue that for your approval.",
        "es": "No. En voz no puedo aprobar quotes, hacer deploy, usar shell ni borrar archivos. Puedo encolarlo para tu aprobación.",
    },
)

_SUMMARY_EN = (
    "In voice I can check today's calendar and Organizer, look up quotes and files, "
    "and send a link only to your WhatsApp and email on this instance. "
    "I cannot email clients or Studio addresses."
)
_SUMMARY_ES = (
    "En voz puedo revisar el calendario y el Organizer de hoy, buscar quotes y archivos, "
    "y mandar un enlace solo a tu WhatsApp y a tu correo de esta instancia. "
    "No puedo escribir a clientes ni a direcciones del Studio."
)


def is_capability_question(text: str | None) -> bool:
    raw = (text or "").strip()
    if not raw or len(raw) > 240:
        return False
    return bool(_CAN_YOU_RE.match(raw))


def matching_action_tool(text: str | None) -> Optional[str]:
    """If this 'can you' is actually a request to run a tool, return that tool name."""
    raw = (text or "").strip()
    if not raw:
        return None
    for pat, tool in _ACTION_TOOLS:
        if pat.search(raw):
            return tool
    return None


def is_pure_capability_question(text: str | None) -> bool:
    raw = (text or "").strip()
    if not raw or matching_action_tool(raw):
        return False
    return bool(_PURE_CAPABILITY.search(raw)) or (
        is_capability_question(raw) and matching_action_tool(raw) is None
    )


def _lang(text: str) -> str:
    if re.search(r"[áéíóúñ¿¡]|\b(?:puedes|podrías|podes|hacer|agenda|correo|clima)\b", text, re.I):
        return "es"
    return "en"


def _needle(text: str) -> str:
    m = _CAN_YOU_RE.match((text or "").strip())
    return (m.group(1) if m else text or "").strip().lower()


def match_capability(text: str | None) -> Optional[dict[str, object]]:
    needle = _needle(text or "")
    if not needle:
        return None
    best = None
    best_len = 0
    for row in VOICE_CAPABILITY_LIST:
        for key in row["keys"]:
            k = str(key).lower()
            if k and k in needle and len(k) > best_len:
                best = row
                best_len = len(k)
    return best


def answer_can_you_do(text: str | None) -> Optional[str]:
    """Spoken answer from the capability list, or None when an action tool should run."""
    if matching_action_tool(text):
        return None
    if not is_capability_question(text):
        return None
    lang = _lang(text or "")
    row = match_capability(text)
    if row:
        return str(row["es"] if lang == "es" else row["en"])
    return _SUMMARY_ES if lang == "es" else _SUMMARY_EN


def capability_list_for_prompt() -> str:
    lines = ["# Voice capability list (answer 'can you do X' from this, do not guess)"]
    for row in VOICE_CAPABILITY_LIST:
        flag = "YES" if row["can"] else "NO"
        lines.append(f"- {flag}: {row['en']}")
    return "\n".join(lines)


def can_you_do(params: dict) -> dict[str, Any]:
    """Answer a 'can you do X' question from the voice capability list."""
    q = str(params.get("question") or params.get("query") or params.get("x") or "").strip()
    asked = q if is_capability_question(q) else f"can you {q}"
    action = matching_action_tool(asked)
    if action:
        return {
            "success": True,
            "result": {
                "question": q,
                "answer": None,
                "action_tool": action,
                "capability": None,
                "can": True,
                "instruction": f"This is an action request. Call {action} now. Do not answer with a capability yes.",
            },
        }
    text = answer_can_you_do(asked)
    row = match_capability(asked)
    return {
        "success": True,
        "result": {
            "question": q,
            "answer": text or _SUMMARY_EN,
            "capability": (row or {}).get("id"),
            "can": bool((row or {}).get("can")) if row else None,
            "instruction": "Speak the answer. Do not guess beyond this list.",
        },
    }


def register_tools(tool, ToolResult) -> None:
    @tool("can_you_do")
    def _can_you_do(params: dict, desk: Optional[str] = None):
        data = can_you_do(params)
        return ToolResult(tool="can_you_do", success=True, result=data["result"])
