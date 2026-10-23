"""Easy step-by-step family chat guides. Spanish, one question at a time.

Secrets never belong in chat. WhatsApp tokens go to the instance secure screen.
The WhatsApp setup guide fires only on explicit setup intent — never on
greetings, first-turn questions, or empty history.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

DEFAULT_PENDING_WHATSAPP_KEY = "pendiente_whatsapp_famp"
_PENDING_WHATSAPP_KEY_RE = re.compile(r"(?i)^pendiente_.*whatsapp")
_WHATSAPP_RE = r"whats?\s*app"
_SETUP_VERB_RE = (
    r"(?:activ(?:ar|o|a|e|ando)|configur(?:ar|o|a|e|ando)|conect(?:ar|o|a|e|ando)"
    r"|habilit(?:ar|o|a|e|ando)|instal(?:ar|o|a|e|ando)|vincul(?:ar|o|a|e|ando)"
    r"|setup|set\s*up|enable|enabling|install|create|creating)"
)
_SEND_RE = re.compile(
    r"\b(?:envia(?:r|me|nos)?|manda(?:r|me|nos)?|send|message|mensaje|escribe|escribir)\b"
)
_GUIDE_RE = r"(?:guia|guide|tutorial|pasos|instrucciones)"
_NUMBER_RE = r"(?:numero|number|linea)"
_ACCOUNT_RE = r"(?:cuenta|account|app\b)"
_META_RE = r"(?:meta|facebook)"

COMPANY_STEPS = (
    ("name", "¿Cómo se llama la empresa?"),
    ("industry", "¿A qué se dedica, en una frase?"),
    ("city", "¿En qué ciudad está? Si no aplica, di “online”."),
    ("contact_email", "¿Cuál es el correo de contacto? Si no tienes, di “después”."),
    ("description", "Cuéntame en una o dos frases qué vende o qué servicio ofrece."),
)

WHATSAPP_STEPS = (
    (
        "own_account",
        "Vamos a crear TU cuenta de Meta y TU número de WhatsApp Business, "
        "separados de los de Rafael. ¿Ya tienes Facebook con tu correo, manito?",
    ),
    (
        "meta_business",
        "Entra a business.facebook.com con TU Facebook y crea o abre TU Business. "
        "No uses la cuenta del Workroom. ¿Ya estás dentro?",
    ),
    (
        "developers",
        "En developers.facebook.com crea una app tipo Business. "
        "En el use-case elige “Conectar con clientes por WhatsApp”. ¿Lista la app?",
    ),
    (
        "system_user",
        "En Business Settings → System users crea un usuario del sistema y un token permanente "
        "con whatsapp_business_messaging y whatsapp_business_management. "
        "El App Secret está en App settings → Basic. ¿Ya los copiaste en un lugar seguro?",
    ),
    (
        "webhook",
        "En WhatsApp → Configuration pega el webhook de ESTA instancia y pulsa Verify and save. "
        "Yo te digo la URL. El verify token lo verás en la pantalla segura, no aquí. ¿Listo?",
    ),
    (
        "secure_screen",
        "Ahora abre la pantalla segura y pega Phone Number ID, token y App Secret. "
        "Nunca los escribas en este chat. Cuando los hayas pegado, dime “ya los pegué”.",
    ),
)

SECRET_HINTS = (
    "token",
    "app secret",
    "app_secret",
    "eaa",
    "verify_token",
    "llave",
    "secret",
    "bearer",
)


def _clip(value, limit: int = 200) -> str:
    return str(value or "").replace("\x00", "").strip()[:limit]


def looks_like_secret(text: str) -> bool:
    folded = (text or "").strip().lower()
    if not folded:
        return False
    if folded.startswith("eaa") and len(folded) > 20:
        return True
    if "begin private" in folded:
        return True
    compact = folded.replace(" ", "")
    if any(word in folded for word in SECRET_HINTS) and len(compact) > 24:
        return True
    return False


def _fold(text: str) -> str:
    raw = unicodedata.normalize("NFD", text or "")
    return "".join(ch for ch in raw if unicodedata.category(ch) != "Mn").lower()


def whatsapp_setup_path() -> str:
    try:
        from app.edition import is_maxine

        if is_maxine():
            return "/ayuda/whatsapp"
    except Exception:
        pass
    return "/amp/whatsapp"


def default_pending_whatsapp_key() -> str:
    try:
        from app.edition import is_maxine

        if is_maxine():
            return "pendiente_whatsapp_maxine"
    except Exception:
        pass
    return DEFAULT_PENDING_WHATSAPP_KEY


def is_whatsapp_setup_intent(message: str) -> bool:
    """True only when the owner asks to activate / configure / connect WhatsApp."""
    text = _fold(message)
    if not text:
        return False
    if _SEND_RE.search(text) and not re.search(_SETUP_VERB_RE, text):
        return False
    if re.search(rf"{_SETUP_VERB_RE}.{{0,48}}{_WHATSAPP_RE}", text):
        return True
    if re.search(rf"{_WHATSAPP_RE}.{{0,48}}{_SETUP_VERB_RE}", text):
        return True
    if re.search(rf"{_GUIDE_RE}.{{0,24}}{_WHATSAPP_RE}", text):
        return True
    if re.search(rf"{_WHATSAPP_RE}.{{0,24}}{_GUIDE_RE}", text):
        return True
    if re.search(rf"(?:conectar|configurar|activar|vincular).{{0,32}}{_NUMBER_RE}.{{0,24}}{_WHATSAPP_RE}", text):
        return True
    if re.search(rf"(?:crear|create).{{0,24}}{_ACCOUNT_RE}.{{0,24}}(?:{_META_RE}|{_WHATSAPP_RE})", text):
        return True
    return False


def secret_refusal() -> str:
    path = whatsapp_setup_path()
    return (
        f"Manito, no pongas llaves aquí. Ábreme {path} y pégalas en la pantalla segura. "
        "Yo no las leo ni las repito."
    )


def company_guide_next(answers: Optional[dict] = None) -> dict:
    answers = answers if isinstance(answers, dict) else {}
    filled = {key: _clip(answers.get(key)) for key, _ in COMPANY_STEPS}
    for key, question in COMPANY_STEPS:
        if not filled.get(key) or filled[key].lower() in {"después", "despues", "luego", "skip"}:
            if key in {"contact_email"} and filled.get(key) in {"después", "despues", "luego", "skip", "online"}:
                continue
            if not filled.get(key):
                return {
                    "flow": "company",
                    "step": key,
                    "question": question,
                    "answers": filled,
                    "done": False,
                    "confirm": False,
                }
    preview = {
        "name": filled["name"],
        "industry": filled["industry"],
        "city": "" if filled["city"].lower() == "online" else filled["city"],
        "contact_email": "" if filled["contact_email"].lower() in {"después", "despues", "luego", "skip"} else filled["contact_email"],
        "description": filled["description"],
    }
    return {
        "flow": "company",
        "step": "confirm",
        "question": (
            f"Así lo dejaría: {preview['name']}"
            + (f" · {preview['industry']}" if preview["industry"] else "")
            + (f" · {preview['city']}" if preview["city"] else "")
            + ". ¿Lo guardo?"
        ),
        "answers": preview,
        "done": True,
        "confirm": True,
        "preview": preview,
    }


def whatsapp_step_keys() -> list[str]:
    return [item[0] for item in WHATSAPP_STEPS]


def whatsapp_guide_next(step: str = "") -> dict:
    keys = whatsapp_step_keys()
    current = (step or "").strip() or keys[0]
    if current not in keys:
        current = keys[0]
    index = keys.index(current)
    key, question = WHATSAPP_STEPS[index]
    path = whatsapp_setup_path()
    if key == "secure_screen":
        question = (
            f"Ahora abre {path} y pega Phone Number ID, token y App Secret en la pantalla segura. "
            "Nunca los escribas en este chat. Cuando los hayas pegado, dime “ya los pegué”."
        )
    return {
        "flow": "whatsapp",
        "step": key,
        "question": question,
        "next_step": keys[index + 1] if index + 1 < len(keys) else None,
        "setup_path": path,
        "secrets_in_chat": False,
        "juan_number_not_rafael": True,
        "done": index == len(keys) - 1,
    }


def format_whatsapp_guide_message(guide: dict, webhook_url: str = "") -> str:
    """One Spanish question. Keys stay on the secure screen, never in chat."""
    question = str((guide or {}).get("question") or "").strip()
    webhook = (webhook_url or str((guide or {}).get("webhook_url") or "")).strip()
    path = str((guide or {}).get("setup_path") or "").strip() or whatsapp_setup_path()
    parts = [question] if question else []
    if webhook and str((guide or {}).get("step") or "") == "webhook":
        parts.append(f"Webhook: {webhook}.")
    parts.append(f"Pantalla segura: {path}. Nunca pegues el token aquí.")
    return " ".join(parts)


def is_pending_whatsapp_key(key: str) -> bool:
    return bool(_PENDING_WHATSAPP_KEY_RE.search((key or "").strip()))


def pending_whatsapp_facts() -> list[dict]:
    """Pending WhatsApp items from this instance facts.json only."""
    try:
        from app.edition import is_family_edition

        if not is_family_edition():
            return []
        from app.services.edition_facts import list_facts

        return [row for row in list_facts() if is_pending_whatsapp_key(str(row.get("key") or ""))]
    except Exception:
        return []


def step_from_pending_fact(fact: Optional[dict]) -> str:
    keys = whatsapp_step_keys()
    blob = " ".join(
        str((fact or {}).get(field) or "")
        for field in ("value", "text", "label", "step")
    ).strip().lower()
    for key in keys:
        if re.search(rf"\b{re.escape(key)}\b", blob):
            return key
    return keys[0]


def saved_whatsapp_guide_step() -> str:
    rows = pending_whatsapp_facts()
    if not rows:
        return whatsapp_step_keys()[0]
    return step_from_pending_fact(rows[0])


def persist_whatsapp_guide_step(step: str, key: Optional[str] = None) -> dict:
    """Write the current guide step so a new Max-e session resumes here."""
    from app.services.edition_facts import upsert_fact

    keys = whatsapp_step_keys()
    current = (step or "").strip() or keys[0]
    if current not in keys:
        current = keys[0]
    existing = pending_whatsapp_facts()
    fact_key = (key or "").strip() or (
        str(existing[0].get("key") or "").strip() if existing else default_pending_whatsapp_key()
    )
    if not is_pending_whatsapp_key(fact_key):
        fact_key = default_pending_whatsapp_key()
    label = ""
    if existing:
        label = str(existing[0].get("label") or "")
    return upsert_fact(
        key=fact_key,
        text=f"WhatsApp guía pendiente en {current}",
        value=current,
        label=label or "WhatsApp pendiente",
        source="whatsapp_guide",
        visibility="confidential",
    )


def whatsapp_channel_is_disabled() -> bool:
    try:
        from app.services.whatsapp_cloud import channel_status

        status = channel_status() or {}
        if status.get("enabled"):
            return False
        return str(status.get("status") or "disabled") != "ready"
    except Exception:
        return True


def run_whatsapp_setup_guide(step: str = "", *, persist: bool = True) -> dict:
    """Same result the whatsapp_setup_guide tool returns, from a saved step."""
    from app.services.whatsapp_cloud import channel_status, webhook_public_url

    resolved = (step or "").strip() or saved_whatsapp_guide_step()
    guide = whatsapp_guide_next(resolved)
    status = channel_status()
    guide["webhook_url"] = webhook_public_url()
    guide["channel_status"] = status.get("status")
    guide["configured"] = bool(status.get("enabled"))
    guide["message"] = format_whatsapp_guide_message(guide)
    if persist:
        try:
            persist_whatsapp_guide_step(guide["step"])
        except Exception:
            pass
    return guide


def pending_whatsapp_guide(*, persist: bool = False) -> Optional[dict]:
    """If facts have pendiente_* WhatsApp and the channel is off, the saved step.

    This does not answer chat. Chat uses maybe_resume_whatsapp_guide, which
    requires explicit WhatsApp setup intent.
    """
    try:
        from app.edition import is_family_edition

        if not is_family_edition():
            return None
    except Exception:
        return None
    if not pending_whatsapp_facts():
        return None
    if not whatsapp_channel_is_disabled():
        return None
    return run_whatsapp_setup_guide(saved_whatsapp_guide_step(), persist=persist)


def is_new_chat_first_turn(message: str, history: Optional[list] = None) -> bool:
    """Family greeting or the first user turn of a new Max-e session."""
    try:
        from app.services.max.quick_replies import is_greeting

        if is_greeting(message):
            return True
    except Exception:
        folded = (message or "").strip().lower()
        if folded in {"hola", "hi", "hey", "buenas", "quiubo", "quiúbo"}:
            return True
    users: list[str] = []
    for item in history or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("role") or "") != "user":
            continue
        content = str(item.get("content") or "")
        if content.startswith("[Context from previous sessions]"):
            continue
        users.append(content.strip())
    if not users:
        return True
    return len(users) == 1 and users[0] == (message or "").strip()


def maybe_resume_whatsapp_guide(
    message: str = "",
    history: Optional[list] = None,
    *,
    persist: bool = True,
) -> Optional[dict]:
    """Return the Spanish WhatsApp guide only on explicit setup intent."""
    if not is_whatsapp_setup_intent(message):
        return None
    try:
        from app.edition import is_family_edition

        if not is_family_edition():
            return None
    except Exception:
        return None
    if not whatsapp_channel_is_disabled():
        return None
    return run_whatsapp_setup_guide(saved_whatsapp_guide_step(), persist=persist)
