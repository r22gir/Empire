"""Gmail read-only inbox reader via OAuth2.

Uses ~/empire-repo/backend/token.json (created by gmail_auth.py).
Filters for emails TO max@empirebox.store by default.
READ ONLY — no delete, no move, no modify.
"""
import os
import logging
import socket
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

logger = logging.getLogger("max.gmail_reader")

TOKEN_FILE = Path(__file__).resolve().parents[3] / "token.json"
CREDS_FILE = Path(__file__).resolve().parents[3] / "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Global timeout for all Gmail HTTP calls (seconds)
_GMAIL_TIMEOUT = 10
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gmail")


def _get_service():
    """Build Gmail API service from saved OAuth2 token."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2

    if not TOKEN_FILE.exists():
        raise RuntimeError(
            f"Gmail token not found at {TOKEN_FILE}. "
            "Run: cd ~/empire-repo/backend && python3 gmail_auth.py"
        )

    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json())

    # Build with a timeout-aware http transport
    http = httplib2.Http(timeout=_GMAIL_TIMEOUT)
    authed_http = AuthorizedHttp(creds, http=http)
    return build("gmail", "v1", http=authed_http, cache_discovery=False)


def _check_inbox_sync(
    limit: int = 10,
    unread_only: bool = True,
    filter_to: Optional[str] = None,
) -> dict:
    """Internal sync implementation — always run in a thread."""
    limit = min(limit, 20)
    max_email = filter_to or os.getenv("MAX_EMAIL", "max@empirebox.store")

    # Set socket-level timeout as safety net
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(_GMAIL_TIMEOUT)
    try:
        service = _get_service()

        # Build Gmail search query
        query_parts = []
        if max_email:
            query_parts.append(f"to:{max_email}")
        if unread_only:
            query_parts.append("is:unread")
        query = " ".join(query_parts) if query_parts else None

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
    finally:
        socket.setdefaulttimeout(old_timeout)


def check_inbox(
    limit: int = 10,
    unread_only: bool = True,
    filter_to: Optional[str] = None,
) -> dict:
    """Fetch recent emails with a hard 15s timeout. Thread-safe, never blocks event loop.

    Tries IMAP first (if GMAIL_IMAP_PASSWORD is set), falls back to OAuth.
    """
    # Try IMAP first if configured
    if os.getenv("GMAIL_IMAP_PASSWORD"):
        try:
            imap_result = _check_inbox_imap(limit, unread_only, filter_to)
            if imap_result.get("success"):
                return imap_result
        except Exception as e:
            logger.warning(f"IMAP check failed, falling back to OAuth: {e}")

    # Fall back to OAuth
    try:
        future = _executor.submit(_check_inbox_sync, limit, unread_only, filter_to)
        return future.result(timeout=15)
    except FuturesTimeout:
        logger.error("Gmail check timed out after 15s")
        return {"success": False, "error": "Gmail request timed out (15s)", "emails": [], "count": 0}
    except Exception as e:
        logger.error(f"Gmail check error: {e}")
        return {"success": False, "error": str(e), "emails": [], "count": 0}


def _check_inbox_imap(limit: int = 10, unread_only: bool = True, filter_to: Optional[str] = None) -> dict:
    """Check Gmail inbox via IMAP (no OAuth needed)."""
    import imaplib
    import email
    from email.header import decode_header

    host = os.getenv("GMAIL_IMAP_HOST", "imap.gmail.com")
    port = int(os.getenv("GMAIL_IMAP_PORT", "993"))
    user = os.getenv("GMAIL_IMAP_USER", os.getenv("MAX_EMAIL", "max@empirebox.store"))
    password = os.getenv("GMAIL_IMAP_PASSWORD")
    max_email = filter_to or os.getenv("MAX_EMAIL", "max@empirebox.store")

    if not password:
        return {"success": False, "error": "IMAP password not configured", "emails": []}

    try:
        mail = imaplib.IMAP4_SSL(host, port)
        mail.login(user, password)
        mail.select("INBOX")

        search_filter = f'UNSEEN' if unread_only else 'ALL'
        status, messages = mail.search(None, search_filter)
        email_ids = messages[0].split()

        # Filter by TO address if needed
        target_ids = []
        for eid in reversed(email_ids):
            if len(target_ids) >= limit:
                break
            _, msg_data = mail.fetch(eid, '(RFC822.HEADER)')
            msg = email.message_from_bytes(msg_data[0][1])
            to_addr = msg.get("To", "")
            if max_email.lower() in to_addr.lower():
                target_ids.append(eid)

        emails = []
        for eid in target_ids:
            _, msg_data = mail.fetch(eid, '(RFC822.HEADER)')
            msg = email.message_from_bytes(msg_data[0][1])
            subject = decode_header(msg.get("Subject", ""))[0]
            subject = subject[0] if isinstance(subject, tuple) else subject
            if isinstance(subject, bytes):
                subject = subject.decode("utf-8", errors="replace")
            from_raw = decode_header(msg.get("From", ""))[0]
            from_addr = from_raw[0] if isinstance(from_raw, tuple) else from_raw
            if isinstance(from_addr, bytes):
                from_addr = from_addr.decode("utf-8", errors="replace")
            emails.append({
                "from": from_addr,
                "to": msg.get("To", ""),
                "subject": subject,
                "date": msg.get("Date", ""),
                "preview": subject,
                "unread": True,
            })

        mail.logout()
        return {"success": True, "count": len(emails), "unread_total": len(emails), "filter": max_email, "emails": emails}
    except Exception as e:
        return {"success": False, "error": str(e), "emails": [], "count": 0}
