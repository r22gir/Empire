"""send_me_link — AMP owner-only link/document delivery.

Delivers a link or document ONLY to Juan's WhatsApp and email, read from
EDITION_OWNER_WHATSAPP / EDITION_OWNER_EMAIL (WHATSAPP_OWNER_NUMBERS is a
phone fallback). Never Studio send_me_this_link. Never business.json,
FOUNDER_EMAIL, or AMP_OWNER_EMAIL.

Tests must mock every send — this module never writes live data; outbound
I/O is isolated in _deliver_* helpers.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("max.send_me_link")

TOOL_NAME = "send_me_link"
STUDIO_TOOL_NAME = "send_me_this_link"
OWNER_FIRST_NAME = "Juan"
OWNER_ALIASES = frozenset({
    "me", "myself", "owner", "juan", "juan diego", "juan diego giraldo",
    "mi correo", "mi email", "my email", "mi whatsapp", "my whatsapp",
})
SIBLING_NAMES = frozenset({
    "camilo", "camilo giraldo",
})
# Client / brand contacts that must never receive. Not owner numbers.
CLIENT_DENY_EMAILS = frozenset({
    "grupoargoscampestre@gmail.com",
})
DENYLIST_EMAILS = frozenset({
    "empirebox2026@gmail.com",
    "rafa22giraldo@gmail.com",
    "workroom@empirebox.store",
    "woodcraft@empirebox.store",
    "max@empirebox.store",
}) | CLIENT_DENY_EMAILS
STUDIO_BUSINESS_PHONES = frozenset({
    "17032136484",
    "7032136484",
    "12032136484",
})
MISSING_WHATSAPP_ES = (
    "Manito, todavía no tengo tu WhatsApp configurado. "
    "Pídele a Rafael que ponga EDITION_OWNER_WHATSAPP en esta instancia."
)
MISSING_EMAIL_ES = (
    "Manito, todavía no tengo tu correo configurado. "
    "Pídele a Rafael que ponga EDITION_OWNER_EMAIL en esta instancia."
)
NOT_OWNER_ES = (
    "Manito, solo te puedo mandar a TU WhatsApp y TU correo de esta instancia. "
    "No mando a clientes, al Studio ni al otro hermano."
)
SEND_VIAS = ("whatsapp", "email")
_EMAIL_IN_BRACKETS = re.compile(r"<([^<>]+@[^<>]+)>")
_BARE_EMAIL = re.compile(r"([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})")
_URL = re.compile(r"^https?://", re.I)


def is_family_send_me_enabled() -> bool:
    try:
        from app.edition import is_family_edition
        return bool(is_family_edition())
    except Exception:
        return False


def normalize_email(addr: str | None) -> str:
    return (addr or "").strip().lower()


def extract_email(addr: str | None) -> str:
    raw = (addr or "").strip()
    m = _EMAIL_IN_BRACKETS.search(raw)
    if m:
        return normalize_email(m.group(1))
    m = _BARE_EMAIL.search(raw)
    if m:
        return normalize_email(m.group(1))
    return normalize_email(raw)


def digits_only(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def _phone_variants(number: str) -> set[str]:
    n = digits_only(number)
    out = {n} if n else set()
    if n.startswith("57") and len(n) >= 12:
        out.add(n[2:])
    elif n.startswith("1") and len(n) == 11:
        out.add(n[1:])
    elif len(n) == 10:
        out.add("1" + n)
        out.add("57" + n)
    return out


def _split_csv(raw: str | None) -> list[str]:
    return [part.strip() for part in (raw or "").split(",") if part.strip()]


def sibling_deny_emails() -> set[str]:
    """Other brother's emails from EDITION_DENY_EMAIL. Never a send target."""
    out: set[str] = set()
    for part in _split_csv(os.getenv("EDITION_DENY_EMAIL") or ""):
        email = extract_email(part)
        if email:
            out.add(email)
    return out


def sibling_deny_phones() -> set[str]:
    """Other brother's WhatsApp from EDITION_DENY_WHATSAPP. Never a send target."""
    out: set[str] = set()
    for part in _split_csv(os.getenv("EDITION_DENY_WHATSAPP") or ""):
        out |= _phone_variants(part)
    return out


def denylist_emails() -> set[str]:
    return set(DENYLIST_EMAILS) | sibling_deny_emails()


def denylist_phones() -> set[str]:
    out: set[str] = set()
    for item in STUDIO_BUSINESS_PHONES:
        out |= _phone_variants(item)
    out |= sibling_deny_phones()
    return out


def is_denied_email(addr: str | None) -> bool:
    return extract_email(addr) in denylist_emails()


def is_denied_phone(number: str | None) -> bool:
    variants = _phone_variants(number or "")
    denied = denylist_phones()
    return bool(variants & denied)


def is_sibling_recipient(to: str | None) -> bool:
    raw = (to or "").strip().lower()
    if not raw:
        return False
    if raw in SIBLING_NAMES:
        return True
    if re.search(r"\bcamilo\b", raw):
        return True
    email = extract_email(raw)
    if email and email in sibling_deny_emails():
        return True
    if is_denied_phone(raw):
        return True
    return False


def owner_emails() -> list[str]:
    """Juan's emails for THIS AMP instance. Comma-separated EDITION_OWNER_EMAIL.

    Never FOUNDER_EMAIL or AMP_OWNER_EMAIL. Denylisted values are skipped.
    """
    out: list[str] = []
    for part in _split_csv(os.getenv("EDITION_OWNER_EMAIL") or ""):
        email = extract_email(part)
        if not email or is_denied_email(email) or email in out:
            continue
        out.append(email)
    return out


def owner_email() -> str:
    """Primary owner email (first in EDITION_OWNER_EMAIL)."""
    emails = owner_emails()
    return emails[0] if emails else ""


def owner_whatsapp() -> str:
    """Juan's WhatsApp. EDITION_OWNER_WHATSAPP, else first non-denied WHATSAPP_OWNER_NUMBERS."""
    candidates = []
    primary = (os.getenv("EDITION_OWNER_WHATSAPP") or "").strip()
    if primary:
        candidates.append(primary)
    candidates.extend(_split_csv(os.getenv("WHATSAPP_OWNER_NUMBERS") or ""))
    for raw in candidates:
        number = digits_only(raw)
        if number and not is_denied_phone(number):
            return number
    return ""


def _is_owner_alias(raw: str) -> bool:
    return (raw or "").strip().lower() in OWNER_ALIASES or not (raw or "").strip()


def authorize_recipient(via: str, to: str | None) -> dict[str, Any]:
    """Allowlist: only this edition owner's WhatsApp / email."""
    via = (via or "").strip().lower()
    raw = (to or "").strip()
    email = extract_email(raw)
    if via in ("mail", "gmail"):
        via = "email"
    if via in ("wa", "whats app", "chat"):
        via = "whatsapp"

    if is_sibling_recipient(raw) or is_denied_email(raw) or (digits_only(raw) and is_denied_phone(raw)):
        return {"authorized": False, "via": via, "to": raw, "error": NOT_OWNER_ES}

    if via == "email":
        allowed = owner_emails()
        if not allowed:
            return {"authorized": False, "via": "email", "to": email or raw, "error": MISSING_EMAIL_ES}
        if _is_owner_alias(raw):
            return {"authorized": True, "via": "email", "to": allowed[0], "error": None}
        asked = extract_email(raw)
        if asked and asked in allowed:
            return {"authorized": True, "via": "email", "to": asked, "error": None}
        return {"authorized": False, "via": "email", "to": email or raw, "error": NOT_OWNER_ES}

    if via == "whatsapp":
        configured = owner_whatsapp()
        if not configured:
            return {"authorized": False, "via": "whatsapp", "to": digits_only(raw) or raw, "error": MISSING_WHATSAPP_ES}
        if _is_owner_alias(raw):
            return {"authorized": True, "via": "whatsapp", "to": configured, "error": None}
        asked = digits_only(raw)
        if asked and (_phone_variants(asked) & _phone_variants(configured)):
            return {"authorized": True, "via": "whatsapp", "to": configured, "error": None}
        return {"authorized": False, "via": "whatsapp", "to": asked or raw, "error": NOT_OWNER_ES}

    return {
        "authorized": False,
        "via": via,
        "to": raw,
        "error": f"via must be one of {', '.join(SEND_VIAS)}",
    }


def asked_to_send(message: Optional[str]) -> bool:
    t = message or ""
    return bool(re.search(
        r"\b(?:send|sent|resend|e-?mail|forward|whats\s?app|"
        r"m[aá]nd[ae]|m[aá]ndame|env[ií]a|env[ií]ame|correo)\b",
        t,
        re.I,
    ))


def _refuse_live_send(channel: str) -> None:
    """Tests must mock _deliver_*. Never hit WhatsApp or SMTP from pytest."""
    if os.environ.get("PYTEST_CURRENT_TEST"):
        raise RuntimeError(
            f"{TOOL_NAME} {channel} send blocked under pytest — mock _deliver_{channel}"
        )


def _under_data_dir(path: str) -> Optional[str]:
    raw = (os.getenv("EMPIRE_DATA_DIR") or "").strip()
    if not raw or not path:
        return None
    try:
        root = Path(raw).expanduser().resolve()
        resolved = Path(path).expanduser().resolve()
        resolved.relative_to(root)
    except Exception:
        return None
    if not resolved.is_file():
        return None
    return str(resolved)


def resolve_payload(params: dict) -> dict[str, Any]:
    url = str(params.get("url") or params.get("link") or "").strip()
    query = str(params.get("query") or params.get("what") or params.get("ref") or "").strip()
    path = str(params.get("path") or params.get("file") or params.get("file_id") or "").strip()
    if not url and _URL.match(query):
        url = query
    safe_path = _under_data_dir(path) if path else None
    return {"url": url, "path": safe_path, "query": query}


def _deliver_email(payload: str, *, to: str, subject: str, body: str) -> dict[str, Any]:
    """Outbound email. Tests monkeypatch this. Never called live in tests."""
    _refuse_live_send("email")
    raise RuntimeError("email send is not wired without a mock")


def _deliver_whatsapp(payload: str, *, to: str, caption: str) -> dict[str, Any]:
    """Outbound WhatsApp. Tests monkeypatch this."""
    _refuse_live_send("whatsapp")
    raise RuntimeError("whatsapp send is not wired without a mock")


def send_me_link(params: dict) -> dict[str, Any]:
    """Core send. Returns {success, result?, error?}. Tests mock _deliver_*."""
    if not is_family_send_me_enabled():
        return {
            "success": False,
            "error": "send_me_link only runs on this family instance.",
        }
    via = str(params.get("via") or params.get("channel") or "whatsapp").strip().lower()
    if via in ("mail", "gmail"):
        via = "email"
    if via in ("wa", "whats app", "chat"):
        via = "whatsapp"
    gate = authorize_recipient(via, params.get("to"))
    if not gate["authorized"]:
        return {"success": False, "error": gate["error"]}

    looked = resolve_payload(params)
    payload = looked["url"] or looked["path"] or looked["query"]
    if not payload:
        return {
            "success": False,
            "error": "No encontré un enlace o archivo para mandarte.",
        }

    name = Path(looked["path"]).name if looked["path"] else (looked["url"] or payload)
    if via == "email":
        try:
            sent = _deliver_email(
                payload,
                to=gate["to"],
                subject=str(params.get("subject") or f"Para ti: {name}"),
                body=str(params.get("body") or payload),
            )
        except Exception as exc:
            return {"success": False, "error": f"Email not sent: {exc}"}
        return {"success": True, "result": {
            "via": "email",
            "sent_to": gate["to"],
            "name": name,
            "payload": payload,
            "message_id": (sent or {}).get("message_id"),
            "message": f"Te mandé {name} a tu correo.",
        }}

    try:
        sent = _deliver_whatsapp(
            payload,
            to=gate["to"],
            caption=str(params.get("caption") or f"{name} — para ti, manito"),
        )
    except Exception as exc:
        return {"success": False, "error": f"WhatsApp not sent: {exc}"}
    return {"success": True, "result": {
        "via": "whatsapp",
        "sent_to": "owner_whatsapp",
        "name": name,
        "payload": payload,
        "media_id": (sent or {}).get("media_id"),
        "message": f"Te mandé {name} a tu WhatsApp.",
    }}


def register_tools(tool, ToolResult) -> None:
    @tool(TOOL_NAME)
    def _send_me_link(params: dict, desk: Optional[str] = None):
        data = send_me_link(params)
        return ToolResult(
            tool=TOOL_NAME,
            success=bool(data.get("success")),
            result=data.get("result"),
            error=data.get("error"),
        )


def send_me_link_doc() -> str:
    if not is_family_send_me_enabled():
        return ""
    return f"""
### Mandarme este enlace (solo {OWNER_FIRST_NAME})
- **{TOOL_NAME}** — Manda un enlace o documento SOLO al WhatsApp y correo del dueño
  de ESTA instancia (EDITION_OWNER_WHATSAPP / EDITION_OWNER_EMAIL). Nunca clientes,
  nunca el Studio, nunca el otro hermano. Nunca uses send_me_this_link.
  `{{"tool": "{TOOL_NAME}", "query": "https://ejemplo.com/agenda", "via": "whatsapp"}}`
  `{{"tool": "{TOOL_NAME}", "url": "https://ejemplo.com/doc", "via": "email"}}`
"""


class _SendMeDoc(str):
    def __new__(cls):
        return str.__new__(cls, send_me_link_doc())

    def __str__(self) -> str:
        return send_me_link_doc()

    def __add__(self, other):
        return send_me_link_doc() + other

    def __radd__(self, other):
        return other + send_me_link_doc()


SEND_ME_LINK_DOC = _SendMeDoc()
