"""Easy step-by-step Max-e chat guides. Spanish, one question at a time.

Secrets never belong in chat. WhatsApp tokens go to /amp/whatsapp.
"""
from __future__ import annotations

from typing import Optional

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
        "Ahora abre /amp/whatsapp y pega Phone Number ID, token y App Secret en la pantalla segura. "
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


def secret_refusal() -> str:
    return (
        "Manito, no pongas llaves aquí. Ábreme /amp/whatsapp y pégalas en la pantalla segura. "
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


def whatsapp_guide_next(step: str = "") -> dict:
    keys = [item[0] for item in WHATSAPP_STEPS]
    current = (step or "").strip() or keys[0]
    if current not in keys:
        current = keys[0]
    index = keys.index(current)
    key, question = WHATSAPP_STEPS[index]
    return {
        "flow": "whatsapp",
        "step": key,
        "question": question,
        "next_step": keys[index + 1] if index + 1 < len(keys) else None,
        "setup_path": "/amp/whatsapp",
        "secrets_in_chat": False,
        "juan_number_not_rafael": True,
        "done": index == len(keys) - 1,
    }
