"""send_me_this_link — founder-only link/document delivery (Fix B).

Delivers a link or document ONLY to Rafael's own WhatsApp and
empirebox2026@gmail.com. The allowlist is hardcoded. Any other recipient
(clients, the brothers, rafa22giraldo@gmail.com) is refused.

"the 3D drawing" / "that drawing" resolve to the most recent matching
drawing or doc. Tests must mock every send — this module never writes
live data; outbound I/O is isolated in _deliver_* helpers.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Optional

logger = logging.getLogger("max.send_me_link")

# Hardcoded. Not env. Not FOUNDER_SELF_EMAILS.
SEND_ME_EMAIL = "empirebox2026@gmail.com"
SEND_ME_EMAILS = frozenset({SEND_ME_EMAIL})
BLOCKED_EMAILS = frozenset({
    "rafa22giraldo@gmail.com",
})
# The brothers — never a send_me recipient, by name or number.
BROTHER_NAMES = frozenset({
    "juan", "camilo", "juan diego", "juan diego giraldo", "camilo giraldo",
    "the brothers", "hermanos",
})
FAMILY_REFUSED = (
    "send_me_this_link is not available in family editions (amp / maxine). "
    "It only delivers to Rafael on Studio."
)
SEND_VIAS = ("whatsapp", "email")
STUDIO_VIAS = frozenset({"studio", "link", "enlace", "view", "open"})
_STUDIO_WORD = re.compile(r"\b(?:studio|link|enlace)\b", re.I)


def wants_studio_share(text: str | None = None, via: str | None = None) -> bool:
    """True when Rafael asked for a Studio share link, not WhatsApp/email."""
    raw_via = (via or "").strip().lower()
    if raw_via in STUDIO_VIAS:
        return True
    return bool(_STUDIO_WORD.search(text or ""))


def resolve_voice_share_via(user_text: str | None = None, via: str | None = None) -> str:
    """Voice: 'studio' / 'link' → studio. Never default those to email/WhatsApp."""
    raw = (via or "").strip().lower()
    if wants_studio_share(user_text, raw):
        return "studio"
    if raw in ("email", "mail", "gmail"):
        return "email"
    if raw in ("whatsapp", "wa", "whats app"):
        return "whatsapp"
    return "studio"
_EMAIL_IN_BRACKETS = re.compile(r"<([^<>]+@[^<>]+)>")
_BARE_EMAIL = re.compile(r"([A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})")

_DRAWING_REF = re.compile(
    r"(?i)\b(?:the|that|this|el|la|ese|esa|este|esta)\s+"
    r"(?:3\s*-?\s*d\s+)?(?:drawing|drawings|dibujo|dibujos|plano|planos)\b"
    r"|\b(?:3\s*-?\s*d\s+)(?:drawing|drawings|dibujo|plano)\b"
)
_THAT_DOC = re.compile(
    r"(?i)\b(?:the|that|this|el|la|ese|esa|este|esta)\s+"
    r"(?:doc|docs|document|pdf|file|archivo|documento)\b"
)


def family_edition_blocked() -> bool:
    """True for amp / maxine, including EMPIRE_DATA_DIR=/data/amp with no EMPIRE_EDITION."""
    try:
        from app.edition import is_family_edition
        return bool(is_family_edition())
    except Exception:
        return False


def normalize_email(addr: str | None) -> str:
    return (addr or "").strip().lower()


def extract_email(addr: str | None) -> str:
    """Accept 'Rafael <empirebox2026@gmail.com>' as well as a bare address."""
    raw = (addr or "").strip()
    m = _EMAIL_IN_BRACKETS.search(raw)
    if m:
        return normalize_email(m.group(1))
    m = _BARE_EMAIL.search(raw)
    if m:
        return normalize_email(m.group(1))
    return normalize_email(raw)


def is_send_me_email(addr: str | None) -> bool:
    return extract_email(addr) in SEND_ME_EMAILS


def is_brother_recipient(to: str | None) -> bool:
    raw = (to or "").strip().lower()
    if not raw:
        return False
    if raw in BROTHER_NAMES:
        return True
    if re.search(r"\b(?:juan(?:\s+diego)?|camilo)\b", raw):
        return True
    return False


def founder_phones_ordered() -> list[str]:
    """business_phone, then founder_phones / owner_phones, then env. Not sorted. No phonebook."""
    try:
        from app.services.max.whatsapp_channel import normalize_msisdn
    except Exception:
        return []
    raw: list[str] = []
    try:
        from pathlib import Path
        import json
        path = Path(__file__).resolve().parents[2] / "config" / "business.json"
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    phone = str((data or {}).get("business_phone") or "").strip()
    if phone:
        raw.append(phone)
    for key in ("founder_phones", "owner_phones"):
        extra = (data or {}).get(key) or []
        if isinstance(extra, str):
            extra = [extra]
        if isinstance(extra, dict):
            extra = list(extra.values())
        if isinstance(extra, list):
            for item in extra:
                if isinstance(item, dict):
                    raw.append(str(item.get("phone") or item.get("number") or item.get("wa_id") or ""))
                else:
                    raw.append(str(item))
    env_phones = os.getenv("WHATSAPP_FOUNDER_PHONES") or ""
    if env_phones.strip():
        raw.extend(part.strip() for part in env_phones.split(",") if part.strip())
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        n = normalize_msisdn(item)
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def founder_whatsapp_numbers() -> frozenset[str]:
    """Rafael's WhatsApp only. Never clients or the brothers."""
    return frozenset(founder_phones_ordered())


def primary_founder_whatsapp() -> Optional[str]:
    """First listed founder number (business_phone), not sorted()[0]."""
    nums = founder_phones_ordered()
    return nums[0] if nums else None


def authorize_recipient(via: str, to: str | None) -> dict[str, Any]:
    """Hard allowlist. Reject anything that is not Rafael's WA or empirebox2026."""
    via = (via or "").strip().lower()
    raw = (to or "").strip()
    email = extract_email(raw)
    refused = (
        "recipient_not_allowlisted: send_me_this_link only reaches Rafael's "
        "WhatsApp and empirebox2026@gmail.com. Never clients, the brothers, "
        "or rafa22giraldo@gmail.com."
    )
    if is_brother_recipient(raw):
        return {"authorized": False, "via": via, "to": raw, "error": refused}
    if email in BLOCKED_EMAILS:
        return {"authorized": False, "via": via, "to": email, "error": refused}
    if via == "email":
        if raw.lower() in ("", "me", "myself", "rafael", "founder", "owner", "my email"):
            return {"authorized": True, "via": "email", "to": SEND_ME_EMAIL, "error": None}
        if is_send_me_email(raw):
            return {"authorized": True, "via": "email", "to": SEND_ME_EMAIL, "error": None}
        return {"authorized": False, "via": "email", "to": email or raw, "error": refused}
    if via == "whatsapp":
        allowed = founder_whatsapp_numbers()
        if not raw or raw.lower() in ("me", "myself", "rafael", "founder", "my whatsapp"):
            primary = primary_founder_whatsapp()
            if not primary:
                return {
                    "authorized": False,
                    "via": "whatsapp",
                    "to": "",
                    "error": "Rafael's WhatsApp number is not on file.",
                }
            return {"authorized": True, "via": "whatsapp", "to": primary, "error": None}
        try:
            from app.services.max.whatsapp_channel import normalize_msisdn
            number = normalize_msisdn(raw)
            if number and number in allowed:
                return {"authorized": True, "via": "whatsapp", "to": number, "error": None}
        except Exception:
            pass
        return {"authorized": False, "via": "whatsapp", "to": raw, "error": refused}
    return {
        "authorized": False,
        "via": via,
        "to": raw,
        "error": f"via must be one of {', '.join(SEND_VIAS)}",
    }


def resolve_search_query(query: str, history: Any = None) -> str:
    """Map 'the 3D drawing' / 'that drawing' to a find_files query."""
    raw = (query or "").strip()
    ctx = _recent_user_text(history)
    blob = f"{raw}\n{ctx}"
    if _DRAWING_REF.search(raw) or re.search(r"(?i)\b3\s*-?\s*d\b", raw):
        kind = "3d drawing" if re.search(r"(?i)3\s*-?\s*d", blob) else "drawing"
        client = _client_hint(blob)
        return f"{client} {kind}".strip()
    if _THAT_DOC.search(raw) or raw.lower() in ("that", "this", "it", "ese", "esa", "esto"):
        client = _client_hint(blob)
        return f"{client} drawing".strip() or "drawing"
    return raw or "drawing"


def _recent_user_text(history: Any) -> str:
    parts = []
    for h in list(history or [])[-6:]:
        c = h.get("content") if isinstance(h, dict) else getattr(h, "content", "")
        parts.append(str(c or ""))
    return "\n".join(parts)


def _client_hint(text: str) -> str:
    try:
        from app.services.max.answer_policy import _clients_in
        hits = _clients_in(text)
        if hits:
            return hits[0][1]
    except Exception:
        pass
    return ""


def _modified_key(match: dict[str, Any]) -> str:
    return str(match.get("modified") or match.get("mtime") or "")


def pick_latest_match(matches: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not matches:
        return None
    ranked = sorted(matches, key=_modified_key, reverse=True)
    return ranked[0]


def find_latest_document(query: str, history: Any = None) -> dict[str, Any]:
    from app.services.max import file_finder as ff

    q = resolve_search_query(query, history)
    res = ff.find_files(q, limit=15)
    matches = list(res.get("matches") or [])
    latest = pick_latest_match(matches)
    return {
        "query": q,
        "found": bool(latest),
        "match": latest,
        "matches": matches[:8],
        "total": res.get("total") or len(matches),
        "closest": res.get("closest") or [],
    }


def _refuse_live_send(channel: str) -> None:
    """Tests must mock _deliver_*. Never hit WhatsApp or SMTP from pytest."""
    if os.environ.get("PYTEST_CURRENT_TEST"):
        raise RuntimeError(
            f"send_me_this_link {channel} send blocked under pytest — mock _deliver_{channel}"
        )


def _deliver_email(path: str, *, to: str, subject: str, body: str) -> dict[str, Any]:
    """Outbound email. Tests monkeypatch this. Never called with a live send in tests."""
    _refuse_live_send("email")
    from app.services.max.tools_files import _temp_copy
    import shutil
    from app.services.max.tool_executor import execute_tool

    copy = _temp_copy(path)
    try:
        res = execute_tool(
            {
                "tool": "send_email",
                "to": to,
                "subject": subject,
                "body": body,
                "attachments": [copy],
            },
            founder=False,
            channel="send_me_this_link",
        )
    finally:
        shutil.rmtree(os.path.dirname(copy), ignore_errors=True)
    data = res.to_dict()
    if not data.get("success"):
        raise RuntimeError(data.get("error") or "email not sent")
    return data.get("result") or {}


def _deliver_whatsapp(path: str, *, to: str, caption: str) -> dict[str, Any]:
    """Outbound WhatsApp. Tests monkeypatch this."""
    _refuse_live_send("whatsapp")
    from app.services.max.tools_files import _run_async, _send_whatsapp_file

    return _run_async(_send_whatsapp_file(to, path, caption))


def _studio_share_only(path: str, *, query: str = "") -> dict[str, Any]:
    """Return a studio share URL. Never emails or WhatsApps."""
    from app.services.max import file_finder as ff
    from app.services.max.doc_links import studio_found_url

    name = os.path.basename(path)
    shown = ff._display_path(path)
    url = studio_found_url(path)
    return {
        "success": True,
        "result": {
            "via": "studio",
            "name": name,
            "path": shown,
            "query": query,
            "viewer_url": url,
            "download_url": (url + "&download=1") if url else "",
            "markdown_link": f"[{name}]({url})" if url else name,
            "message": f"[{name}]({url})" if url else f"{name} — studio link.",
            "sent": False,
        },
    }


def send_me_this_link(params: dict) -> dict[str, Any]:
    """Core send. Returns {success, result?, error?}. Tests mock _deliver_*."""
    if family_edition_blocked():
        return {"success": False, "error": FAMILY_REFUSED}
    via = str(params.get("via") or params.get("channel") or "").strip().lower()
    user_text = str(params.get("user_text") or params.get("query") or params.get("what") or "")
    if wants_studio_share(user_text, via):
        via = "studio"
    elif via in ("mail", "gmail"):
        via = "email"
    elif via in ("wa", "whats app", "chat"):
        via = "whatsapp"
    elif not via:
        via = "whatsapp"
    if via == "studio":
        ref = str(params.get("file_id") or params.get("path") or params.get("file") or "").strip()
        query = str(params.get("query") or params.get("what") or params.get("ref") or "").strip()
        history = params.get("history")
        path = None
        if ref:
            from app.services.max import file_finder as ff
            path = ff.resolve_file(ref)
        if not path:
            looked = find_latest_document(query or ref or "drawing", history)
            match = looked.get("match")
            if match:
                from app.services.max import file_finder as ff
                path = ff.resolve_file(match.get("file_id") or match.get("path") or "")
            if not path:
                near = "; ".join(c.get("name") or c.get("path") or "" for c in looked.get("closest") or [])
                return {
                    "success": False,
                    "result": looked,
                    "error": (
                        f'No matching drawing or doc for "{looked.get("query") or query}". '
                        + (f"Closest: {near}." if near else "Nothing close either.")
                    ),
                }
        return _studio_share_only(path, query=query)
    gate = authorize_recipient(via, params.get("to"))
    if not gate["authorized"]:
        return {"success": False, "error": gate["error"]}

    ref = str(params.get("file_id") or params.get("path") or params.get("file") or "").strip()
    query = str(params.get("query") or params.get("what") or params.get("ref") or "").strip()
    history = params.get("history")
    path = None
    resolved_query = query
    if ref:
        from app.services.max import file_finder as ff
        path = ff.resolve_file(ref)
    if not path:
        looked = find_latest_document(query or ref or "drawing", history)
        resolved_query = looked["query"]
        match = looked.get("match")
        if match:
            from app.services.max import file_finder as ff
            path = ff.resolve_file(match.get("file_id") or match.get("path") or "")
        if not path:
            near = "; ".join(c.get("name") or c.get("path") or "" for c in looked.get("closest") or [])
            return {
                "success": False,
                "result": looked,
                "error": (
                    f'No matching drawing or doc for "{resolved_query}". '
                    + (f"Closest: {near}." if near else "Nothing close either.")
                ),
            }

    from app.services.max import file_finder as ff

    name = os.path.basename(path)
    shown = ff._display_path(path)
    if via == "email":
        try:
            sent = _deliver_email(
                path,
                to=gate["to"],
                subject=str(params.get("subject") or f"File: {name}"),
                body=str(params.get("body") or f"Attached: {name}\nFrom: {shown}"),
            )
        except Exception as exc:
            return {"success": False, "error": f"Email not sent: {exc}"}
        return {"success": True, "result": {
            "via": "email",
            "sent_to": SEND_ME_EMAIL,
            "name": name,
            "path": shown,
            "query": resolved_query,
            "message_id": sent.get("message_id"),
            "message": f"Emailed {name} to {SEND_ME_EMAIL}.",
        }}

    try:
        sent = _deliver_whatsapp(
            path,
            to=gate["to"],
            caption=str(params.get("caption") or f"{name} — for you"),
        )
    except Exception as exc:
        return {"success": False, "error": f"WhatsApp not sent: {exc}"}
    return {"success": True, "result": {
        "via": "whatsapp",
        "sent_to": "rafael_whatsapp",
        "name": name,
        "path": shown,
        "query": resolved_query,
        "media_id": (sent or {}).get("media_id"),
        "message": f"Sent {name} to Rafael on WhatsApp.",
    }}


def register_tools(tool, ToolResult) -> None:
    if family_edition_blocked():
        return

    @tool("send_me_this_link")
    def _send_me_this_link(params: dict, desk: Optional[str] = None):
        data = send_me_this_link(params)
        return ToolResult(
            tool="send_me_this_link",
            success=bool(data.get("success")),
            result=data.get("result"),
            error=data.get("error"),
        )


def send_me_link_doc() -> str:
    if family_edition_blocked():
        return ""
    return f"""
### Send this link (Rafael only)
- **send_me_this_link** — Send a link or document ONLY to Rafael's WhatsApp or
  {SEND_ME_EMAIL}. Hardcoded allowlist. Never clients, never the brothers, never
  rafa22giraldo@gmail.com. "the 3D drawing" / "that drawing" resolve to the most
  recent matching drawing or doc.
  `{{"tool": "send_me_this_link", "query": "the 3D drawing", "via": "whatsapp"}}`
  `{{"tool": "send_me_this_link", "query": "that drawing", "via": "email"}}`
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
