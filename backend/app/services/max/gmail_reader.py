"""Gmail read-only inbox reader via OAuth2.

Defaults to the canonical backend token/credentials files, but allows runtime
path overrides through GMAIL_TOKEN_PATH and GMAIL_CREDENTIALS_PATH. This module
never copies legacy token files and never logs token contents.
"""
import os
import logging
import socket
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

logger = logging.getLogger("max.gmail_reader")

DEFAULT_TOKEN_FILE = Path(__file__).resolve().parents[3] / "token.json"
DEFAULT_CREDS_FILE = Path(__file__).resolve().parents[3] / "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Global timeout for all Gmail HTTP calls (seconds)
_GMAIL_TIMEOUT = 10
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gmail")


def _configured_path(env_name: str, default_path: Path) -> Path:
    value = os.getenv(env_name)
    if value:
        return Path(value).expanduser()
    return default_path


def get_oauth_paths() -> dict:
    """Return non-secret Gmail OAuth path metadata for status endpoints."""
    token_env = bool(os.getenv("GMAIL_TOKEN_PATH"))
    credentials_env = bool(os.getenv("GMAIL_CREDENTIALS_PATH"))
    token_path = _configured_path("GMAIL_TOKEN_PATH", DEFAULT_TOKEN_FILE)
    credentials_path = _configured_path("GMAIL_CREDENTIALS_PATH", DEFAULT_CREDS_FILE)
    return {
        "token_path": token_path,
        "credentials_path": credentials_path,
        "token_path_source": "GMAIL_TOKEN_PATH" if token_env else "canonical backend token.json",
        "credentials_path_source": "GMAIL_CREDENTIALS_PATH" if credentials_env else "canonical backend credentials.json",
        "token_env_configured": token_env,
        "credentials_env_configured": credentials_env,
        "token_exists": token_path.exists(),
        "credentials_exists": credentials_path.exists(),
    }


def _get_service():
    """Build Gmail API service from saved OAuth2 token."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2

    paths = get_oauth_paths()
    token_file = paths["token_path"]
    if not paths["token_exists"]:
        raise RuntimeError(
            f"Gmail token not found ({paths['token_path_source']}). "
            "Run Gmail OAuth for the canonical backend or set GMAIL_TOKEN_PATH."
        )

    creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.write_text(creds.to_json())

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
    """Fetch recent emails with a hard 15s timeout. Thread-safe, never blocks event loop."""
    try:
        future = _executor.submit(_check_inbox_sync, limit, unread_only, filter_to)
        return future.result(timeout=15)
    except FuturesTimeout:
        logger.error("Gmail check timed out after 15s")
        return {"success": False, "error": "Gmail request timed out (15s)", "emails": [], "count": 0}
    except Exception as e:
        logger.error(f"Gmail check error: {e}")
        return {"success": False, "error": str(e), "emails": [], "count": 0}
