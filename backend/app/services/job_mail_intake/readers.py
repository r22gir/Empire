"""Read-only inbox connectors for job-mail intake.

Business Gmail, personal Gmail (read-only token), Outlook when present.
Tests assign TEST_INBOX to skip live connectors. Nothing is sent.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Optional

# Tests assign a list of message dicts here to skip live connectors.
TEST_INBOX: Optional[list] = None

OUTBOUND_POLICY = "read_only_never_send"


@contextmanager
def _token_env(env_key: str, path: Optional[str]):
    old = os.environ.get(env_key)
    try:
        if path:
            os.environ[env_key] = str(path)
        yield path
    finally:
        if old is None:
            os.environ.pop(env_key, None)
        else:
            os.environ[env_key] = old


def _connected_paths() -> dict:
    """Token files Max already has. Missing files are skipped."""
    from pathlib import Path

    def _exists(raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        p = Path(raw).expanduser()
        return str(p) if p.exists() else None

    business = _exists(os.getenv("GMAIL_TOKEN_PATH"))
    if not business:
        try:
            from app.services.max.gmail_reader import get_oauth_paths
            token = get_oauth_paths().get("token_path")
            business = _exists(str(token)) if token else None
        except Exception:
            business = None

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


def _normalize(em: dict, source: str, account: str) -> dict:
    return {
        "source": source,
        "account": account,
        "message_id": em.get("id") or em.get("message_id"),
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


def _fetch_gmail(account: str, token_path: Optional[str]) -> list[dict]:
    if not token_path:
        return []
    with _token_env("GMAIL_TOKEN_PATH", token_path):
        from app.services.max.gmail_reader import check_inbox
        res = check_inbox(
            limit=25,
            unread_only=False,
            query="in:inbox newer_than:21d",
            disable_default_to_filter=True,
        )
    if not res.get("success"):
        return []
    source = "gmail_personal" if account == "personal" else "gmail_business"
    return [_normalize(em, source, account) for em in (res.get("emails") or []) if em.get("id")]


def _fetch_outlook(token_path: Optional[str]) -> list[dict]:
    if not token_path:
        return []
    with _token_env("OUTLOOK_TOKEN_PATH", token_path):
        from app.services.max.outlook_reader import search_messages
        res = search_messages(folder="inbox", since="21d", limit=25, unread_only=False)
    if not res.get("success"):
        return []
    return [_normalize(em, "outlook", "outlook") for em in (res.get("emails") or []) if em.get("id")]


def fetch_raw_messages() -> list[dict]:
    """Read connected inboxes. Tests set TEST_INBOX and never hit the network."""
    if TEST_INBOX is not None:
        return [dict(m) for m in TEST_INBOX]
    paths = _connected_paths()
    items: list[dict] = []
    items.extend(_fetch_gmail("business", paths.get("gmail_business")))
    items.extend(_fetch_gmail("personal", paths.get("gmail_personal")))
    items.extend(_fetch_outlook(paths.get("outlook")))
    return items


def connected_accounts() -> dict:
    if TEST_INBOX is not None:
        sources = sorted({(m.get("source") or "test") for m in TEST_INBOX})
        return {
            "sources": sources,
            "gmail_business": "gmail_business" in sources,
            "gmail_personal": "gmail_personal" in sources,
            "outlook": "outlook" in sources,
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
        "test_inbox": False,
        "read_only": True,
        "sent": False,
    }
