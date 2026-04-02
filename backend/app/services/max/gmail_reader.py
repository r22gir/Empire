"""Gmail read-only inbox reader via OAuth2.

Uses ~/empire-repo/backend/token.json (created by gmail_auth.py).
Filters for emails TO max@empirebox.store by default.
READ ONLY — no delete, no move, no modify.
"""
import os
import base64
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger("max.gmail_reader")

TOKEN_FILE = Path(__file__).resolve().parents[3] / "token.json"
CREDS_FILE = Path(__file__).resolve().parents[3] / "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _get_service():
    """Build Gmail API service from saved OAuth2 token."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if not TOKEN_FILE.exists():
        raise RuntimeError(
            f"Gmail token not found at {TOKEN_FILE}. "
            "Run: cd ~/empire-repo/backend && python3 gmail_auth.py"
        )

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def check_inbox(
    limit: int = 10,
    unread_only: bool = True,
    filter_to: Optional[str] = None,
) -> dict:
    """Fetch recent emails. Returns dict with count and email list.

    Parameters
    ----------
    limit : int
        Max emails to return (default 10, max 20).
    unread_only : bool
        If True, only return unread emails.
    filter_to : str or None
        Filter for emails sent TO this address. Defaults to MAX_EMAIL env var.
    """
    limit = min(limit, 20)
    max_email = filter_to or os.getenv("MAX_EMAIL", "max@empirebox.store")

    try:
        service = _get_service()
    except Exception as e:
        return {"success": False, "error": str(e), "emails": [], "count": 0}

    # Build Gmail search query
    query_parts = []
    if max_email:
        query_parts.append(f"to:{max_email}")
    if unread_only:
        query_parts.append("is:unread")
    query = " ".join(query_parts) if query_parts else None

    try:
        results = service.users().messages().list(
            userId="me", q=query, maxResults=limit
        ).execute()
        message_ids = results.get("messages", [])

        emails = []
        for msg_ref in message_ids:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"],
            ).execute()

            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            snippet = msg.get("snippet", "")

            emails.append({
                "id": msg_ref["id"],
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", "(no subject)"),
                "date": headers.get("Date", ""),
                "preview": snippet[:200],
                "unread": "UNREAD" in msg.get("labelIds", []),
            })

        unread_total = 0
        try:
            label = service.users().labels().get(userId="me", id="INBOX").execute()
            unread_total = label.get("messagesUnread", 0)
        except Exception:
            pass

        return {
            "success": True,
            "count": len(emails),
            "unread_total": unread_total,
            "filter": max_email,
            "emails": emails,
        }
    except Exception as e:
        logger.error(f"Gmail check failed: {e}")
        return {"success": False, "error": str(e), "emails": [], "count": 0}
