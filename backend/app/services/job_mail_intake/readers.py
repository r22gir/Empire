"""Read-only inbox connectors for job-mail intake.

Business Gmail, personal Gmail (read-only token), Outlook when present.
Tests assign TEST_INBOX to skip live connectors. Nothing is sent.
Token paths are passed into the readers — process env is never mutated.
"""

from __future__ import annotations

import os
from typing import Optional

# Tests assign a list of message dicts here to skip live connectors.
TEST_INBOX: Optional[list] = None

OUTBOUND_POLICY = "read_only_never_send"

_TRUTHY = {"1", "true", "yes", "on"}


class JobMailFetchError(Exception):
    """Inbox fetch failed. ``error_type`` is the exception class name only."""

    def __init__(self, error_type: str, status_code: Optional[int] = None):
        self.error_type = error_type or "Exception"
        self.status_code = status_code
        super().__init__(self.error_type)


def personal_inbox_enabled() -> bool:
    """Personal Gmail is OFF unless JOB_MAIL_PERSONAL_INBOX is truthy."""
    return os.getenv("JOB_MAIL_PERSONAL_INBOX", "").strip().lower() in _TRUTHY


def intake_enabled() -> bool:
    """Scheduler kill switch. Default on; set JOB_MAIL_INTAKE_ENABLED=0 to stop."""
    raw = os.getenv("JOB_MAIL_INTAKE_ENABLED", "1").strip().lower()
    return raw in _TRUTHY


def _error_status(exc: BaseException) -> Optional[int]:
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        return status
    resp = getattr(exc, "resp", None)
    if resp is not None:
        try:
            return int(getattr(resp, "status", 0) or 0) or None
        except (TypeError, ValueError):
            return None
    return None


def _raise_fetch(exc: BaseException) -> None:
    raise JobMailFetchError(type(exc).__name__, _error_status(exc)) from None


def _exists(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    from pathlib import Path
    p = Path(raw).expanduser()
    return str(p) if p.exists() else None


def _connected_paths() -> dict:
    """Token files Max already has. Missing files are skipped. Env is not written."""
    from pathlib import Path

    business = _exists(os.getenv("GMAIL_TOKEN_PATH"))
    if not business:
        try:
            from app.services.max.gmail_reader import get_oauth_paths
            token = get_oauth_paths().get("token_path")
            business = _exists(str(token)) if token else None
        except Exception:
            business = None

    personal = None
    if personal_inbox_enabled():
        personal = _exists(
            os.getenv("GMAIL_PERSONAL_TOKEN_PATH")
            or str(Path.home() / ".config" / "empirebox" / "gmail-personal" / "token.json")
        )
    outlook = None
    try:
        from app.services.max.outlook_reader import token_path
        outlook = _exists(str(token_path()) if token_path() else None)
    except Exception:
        outlook = _exists(os.getenv("OUTLOOK_TOKEN_PATH"))

    sources = []
    if business:
        sources.append("gmail_business")
    if personal:
        sources.append("gmail_personal")
    if outlook:
        sources.append("outlook")
    return {
        "gmail_business": business,
        "gmail_personal": personal,
        "outlook": outlook,
        "sources": sources,
        "read_only": True,
        "sent": False,
    }


def _gmail_query(since: Optional[str]) -> str:
    if since:
        day = str(since).strip()[:10]
        if len(day) >= 10 and day[4] == "-":
            y, m, d = day.split("-")[:3]
            return f"in:inbox after:{y}/{m}/{d}"
    return "in:inbox newer_than:21d"


def _outlook_since(since: Optional[str]) -> str:
    if since:
        return str(since).strip()
    return "21d"


def _normalize(em: dict, source: str, account: str) -> dict:
    rfc = em.get("rfc_message_id") or em.get("internetMessageId") or ""
    return {
        "source": source,
        "account": account,
        "message_id": em.get("id") or em.get("message_id"),
        "rfc_message_id": rfc,
        "thread_id": em.get("thread_id") or em.get("threadId") or em.get("conversationId") or "",
        "from": em.get("from"),
        "to": em.get("to") or "",
        "subject": em.get("subject") or "(no subject)",
        "date": em.get("date"),
        "preview": em.get("preview") or em.get("bodyPreview") or "",
        "body": em.get("body") or em.get("preview") or "",
        "unread": bool(em.get("unread")),
        "read_only": True,
        "sent": False,
    }


def _fetch_gmail(account: str, token_path: Optional[str], since: Optional[str] = None) -> list[dict]:
    if not token_path:
        return []
    from app.services.max.gmail_reader import check_inbox
    try:
        res = check_inbox(
            limit=25,
            unread_only=False,
            query=_gmail_query(since),
            disable_default_to_filter=True,
            token_path=token_path,
        )
    except Exception as exc:
        _raise_fetch(exc)
    if not res.get("success"):
        err = res.get("error") or "GmailError"
        # Never surface raw exception text — type name only.
        raise JobMailFetchError(type(err).__name__ if not isinstance(err, str) else "GmailError")
    source = "gmail_personal" if account == "personal" else "gmail_business"
    return [_normalize(em, source, account) for em in (res.get("emails") or []) if em.get("id")]


def _fetch_outlook(token_path: Optional[str], since: Optional[str] = None) -> list[dict]:
    if not token_path:
        return []
    from app.services.max.outlook_reader import search_messages
    try:
        res = search_messages(
            folder="inbox",
            since=_outlook_since(since),
            limit=25,
            unread_only=False,
            token_path=token_path,
        )
    except Exception as exc:
        _raise_fetch(exc)
    if not res.get("success"):
        raise JobMailFetchError("OutlookError")
    return [_normalize(em, "outlook", "outlook") for em in (res.get("emails") or []) if em.get("id")]


def fetch_raw_messages(since: Optional[str] = None) -> list[dict]:
    """Read connected inboxes. Tests set TEST_INBOX and never hit the network."""
    if TEST_INBOX is not None:
        return [dict(m) for m in TEST_INBOX]
    paths = _connected_paths()
    items: list[dict] = []
    items.extend(_fetch_gmail("business", paths.get("gmail_business"), since=since))
    if personal_inbox_enabled():
        items.extend(_fetch_gmail("personal", paths.get("gmail_personal"), since=since))
    items.extend(_fetch_outlook(paths.get("outlook"), since=since))
    return items


def connected_accounts() -> dict:
    if TEST_INBOX is not None:
        sources = sorted({(m.get("source") or "test") for m in TEST_INBOX})
        return {
            "sources": sources,
            "gmail_business": "gmail_business" in sources,
            "gmail_personal": "gmail_personal" in sources,
            "outlook": "outlook" in sources,
            "personal_inbox_enabled": personal_inbox_enabled(),
            "test_inbox": True,
            "read_only": True,
            "sent": False,
        }
    paths = _connected_paths()
    return {
        "sources": paths["sources"],
        "gmail_business": bool(paths.get("gmail_business")),
        "gmail_personal": bool(paths.get("gmail_personal")),
        "outlook": bool(paths.get("outlook")),
        "personal_inbox_enabled": personal_inbox_enabled(),
        "test_inbox": False,
        "read_only": True,
        "sent": False,
    }
