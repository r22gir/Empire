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


def get_oauth_paths(
    token_path: Optional[str] = None,
    credentials_path: Optional[str] = None,
) -> dict:
    """Return non-secret Gmail OAuth path metadata for status endpoints.

    Explicit ``token_path`` / ``credentials_path`` win over env and never
    mutate process environment.
    """
    if token_path:
        resolved_token = Path(token_path).expanduser()
        token_env = False
        token_source = "explicit token_path"
    else:
        token_env = bool(os.getenv("GMAIL_TOKEN_PATH"))
        resolved_token = _configured_path("GMAIL_TOKEN_PATH", DEFAULT_TOKEN_FILE)
        token_source = "GMAIL_TOKEN_PATH" if token_env else "canonical backend token.json"
    if credentials_path:
        resolved_creds = Path(credentials_path).expanduser()
        credentials_env = False
        creds_source = "explicit credentials_path"
    else:
        credentials_env = bool(os.getenv("GMAIL_CREDENTIALS_PATH"))
        resolved_creds = _configured_path("GMAIL_CREDENTIALS_PATH", DEFAULT_CREDS_FILE)
        creds_source = "GMAIL_CREDENTIALS_PATH" if credentials_env else "canonical backend credentials.json"
    return {
        "token_path": resolved_token,
        "credentials_path": resolved_creds,
        "token_path_source": token_source,
        "credentials_path_source": creds_source,
        "token_env_configured": token_env,
        "credentials_env_configured": credentials_env,
        "token_exists": resolved_token.exists(),
        "credentials_exists": resolved_creds.exists(),
    }


def _get_service(
    token_path: Optional[str] = None,
    credentials_path: Optional[str] = None,
):
    """Build Gmail API service from saved OAuth2 token."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google_auth_httplib2 import AuthorizedHttp
    import httplib2

    paths = get_oauth_paths(token_path=token_path, credentials_path=credentials_path)
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


def build_gmail_query(
    *,
    unread_only: bool = True,
    filter_to: Optional[str] = None,
    from_sender: Optional[str] = None,
    query: Optional[str] = None,
    disable_default_to_filter: bool = False,
) -> tuple[Optional[str], Optional[str]]:
    """Return (gmail_q, to_filter). Chat default is unread mail to MAX_EMAIL.

    The daily brief / Organizer pending list must pass
    ``disable_default_to_filter=True`` so Business Gmail (empirebox2026,
    which receives workroom@, info@, and max@) is not narrowed to max@.
    """
    searching = bool((from_sender or "").strip() or (query or "").strip())
    if disable_default_to_filter:
        max_email = (filter_to or "").strip() or None
    else:
        max_email = filter_to or (None if searching else os.getenv("MAX_EMAIL", "max@empirebox.store"))
    parts: list[str] = []
    if max_email:
        parts.append(f"to:{max_email}")
    if from_sender and from_sender.strip():
        sender = from_sender.strip().replace('"', "")
        parts.append(f'from:"{sender}"' if " " in sender else f"from:{sender}")
    if query and query.strip():
        parts.append(query.strip())
    if unread_only:
        parts.append("is:unread")
    return (" ".join(parts) if parts else None, max_email)


def _check_inbox_sync(
    limit: int = 10,
    unread_only: bool = True,
    filter_to: Optional[str] = None,
    from_sender: Optional[str] = None,
    query: Optional[str] = None,
    disable_default_to_filter: bool = False,
    token_path: Optional[str] = None,
    credentials_path: Optional[str] = None,
) -> dict:
    """Internal sync implementation — always run in a thread.

    2026-10-05: ``from_sender`` / ``query`` search the whole mailbox
    ("check email from Nelma"), read and unread, instead of only unread
    mail addressed to MAX_EMAIL.
    """
    limit = min(limit, 20)
    query, max_email = build_gmail_query(
        unread_only=unread_only,
        filter_to=filter_to,
        from_sender=from_sender,
        query=query,
        disable_default_to_filter=disable_default_to_filter,
    )

    # Set socket-level timeout as safety net
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(_GMAIL_TIMEOUT)
    try:
        service = _get_service(token_path=token_path, credentials_path=credentials_path)

        results = service.users().messages().list(
            userId="me", q=query, maxResults=limit
        ).execute()
        message_ids = results.get("messages", [])

        emails = []
        for msg_ref in message_ids:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date", "List-Unsubscribe", "List-Id", "Message-ID"],
            ).execute()

            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            snippet = msg.get("snippet", "")
            rfc_id = headers.get("Message-ID") or headers.get("Message-Id") or ""

            emails.append({
                "id": msg_ref["id"],
                "thread_id": msg.get("threadId") or msg_ref.get("threadId") or "",
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", "(no subject)"),
                "date": headers.get("Date", ""),
                "preview": snippet[:200],
                "unread": "UNREAD" in msg.get("labelIds", []),
                "labels": msg.get("labelIds", []),
                "list_unsubscribe": headers.get("List-Unsubscribe", ""),
                "rfc_message_id": rfc_id,
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
            "query": query,
            "source": "gmail",
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
    from_sender: Optional[str] = None,
    query: Optional[str] = None,
    disable_default_to_filter: bool = False,
    token_path: Optional[str] = None,
    credentials_path: Optional[str] = None,
) -> dict:
    """Fetch recent emails with a hard 15s timeout. Thread-safe, never blocks event loop."""
    try:
        future = _executor.submit(
            _check_inbox_sync, limit, unread_only, filter_to, from_sender, query,
            disable_default_to_filter, token_path, credentials_path,
        )
        return future.result(timeout=15)
    except FuturesTimeout:
        logger.error("Gmail check timed out after 15s")
        return {"success": False, "error": "Gmail request timed out (15s)", "emails": [], "count": 0}
    except Exception as e:
        logger.error(f"Gmail check error: {e}")
        return {"success": False, "error": str(e), "emails": [], "count": 0}
