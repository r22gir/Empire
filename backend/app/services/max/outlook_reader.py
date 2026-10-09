"""Outlook / Microsoft 365 mail reader for Max: READ-ONLY, Microsoft Graph.

Sign-in: device-code flow (public client, no secret). Rafael runs
``backend/outlook_auth.py`` once on the Dell; it prints a URL and a code,
he signs in with Microsoft and the refresh token is saved to
``~/.config/empirebox/outlook/token.json`` (dir 700, file 600, outside git).
Override with OUTLOOK_TOKEN_PATH.

Scopes requested: Mail.Read + offline_access ONLY. No Mail.Send,
Mail.ReadWrite or any other write scope is ever requested.

Read-only is enforced in code, not just by scope: every Graph call goes
through ``_graph_get``, which only issues HTTP GET to an allowlist of
read paths (/me/messages, /me/mailFolders). GET never marks a message as
read. There is no send, delete, move, flag or mark-read function here.

Token contents are never logged or returned.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import httpx

logger = logging.getLogger("max.outlook_reader")

# Microsoft Graph Command Line Tools: Microsoft's own public client, works with
# device code for work/school and personal accounts. Override with
# OUTLOOK_CLIENT_ID if Rafael registers his own Azure app.
DEFAULT_CLIENT_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"
DEFAULT_TENANT = "common"
SCOPES = ("https://graph.microsoft.com/Mail.Read", "offline_access")
GRAPH = "https://graph.microsoft.com/v1.0"
TIMEOUT = 15

SIGN_IN_COMMAND = "cd ~/empire-repo-main/backend && venv/bin/python outlook_auth.py"
NOT_SIGNED_IN = (
    "Outlook not signed in yet. Rafael signs in once on the Dell by running: "
    f"{SIGN_IN_COMMAND}  (it prints a Microsoft link and a code; read-only access)."
)

WELL_KNOWN_FOLDERS = {
    "inbox": "inbox", "sent": "sentitems", "sentitems": "sentitems", "sent items": "sentitems",
    "drafts": "drafts", "archive": "archive", "junk": "junkemail", "junkemail": "junkemail",
    "spam": "junkemail", "deleted": "deleteditems", "deleteditems": "deleteditems",
    "trash": "deleteditems",
}

# Read-only allowlist for Graph paths (relative to /v1.0).
_ALLOWED_PATHS = (
    re.compile(r"^/me/messages$"),
    re.compile(r"^/me/messages/[A-Za-z0-9_\-=%]+$"),
    re.compile(r"^/me/mailFolders$"),
    re.compile(r"^/me/mailFolders/[A-Za-z0-9_\-=%]+/messages$"),
)

_LIST_FIELDS = "id,subject,from,receivedDateTime,bodyPreview,isRead,hasAttachments"
_READ_FIELDS = "id,subject,from,toRecipients,ccRecipients,receivedDateTime,body,hasAttachments,webLink"
MAX_BODY_CHARS = 8000


class OutlookNotSignedIn(RuntimeError):
    pass


def client_id() -> str:
    return (os.getenv("OUTLOOK_CLIENT_ID") or DEFAULT_CLIENT_ID).strip()


def tenant() -> str:
    return (os.getenv("OUTLOOK_TENANT") or DEFAULT_TENANT).strip()


def token_path() -> Path:
    env = os.getenv("OUTLOOK_TOKEN_PATH")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".config" / "empirebox" / "outlook" / "token.json"


def _authority() -> str:
    return f"https://login.microsoftonline.com/{tenant()}/oauth2/v2.0"


# ── token storage ───────────────────────────────────────────────────────────

def load_token() -> Optional[dict]:
    p = token_path()
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
    except Exception:
        logger.warning("Outlook token file unreadable")
        return None
    return data if isinstance(data, dict) and data.get("refresh_token") else None


def save_token(data: dict) -> Path:
    """Write the token file with 600 perms (dir 700), atomically."""
    p = token_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(p.parent, 0o700)
    except OSError:
        pass
    tmp = p.with_suffix(".tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(data, fh)
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)
    return p


def _store_token_response(resp: dict) -> dict:
    granted = str(resp.get("scope") or "")
    data = {
        "access_token": resp.get("access_token"),
        "refresh_token": resp.get("refresh_token"),
        "expires_at": int(time.time()) + int(resp.get("expires_in") or 3600) - 60,
        "scope": granted,
        "client_id": client_id(),
        "tenant": tenant(),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    save_token(data)
    return data


def status() -> dict:
    """Non-secret sign-in status."""
    tok = load_token()
    return {
        "signed_in": bool(tok),
        "token_path": str(token_path()),
        "scope": (tok or {}).get("scope", ""),
        "saved_at": (tok or {}).get("saved_at"),
        "sign_in_command": SIGN_IN_COMMAND,
    }


# ── device-code sign-in (used by outlook_auth.py) ──────────────────────────

def start_device_code(http: Optional[httpx.Client] = None) -> dict:
    c = http or httpx.Client(timeout=TIMEOUT)
    r = c.post(f"{_authority()}/devicecode",
               data={"client_id": client_id(), "scope": " ".join(SCOPES)})
    data = r.json()
    if "device_code" not in data:
        raise RuntimeError(f"Device code request failed: {data.get('error')}: "
                           f"{str(data.get('error_description', ''))[:300]}")
    return data


def poll_device_code(flow: dict, http: Optional[httpx.Client] = None,
                     sleep=time.sleep, now=time.monotonic) -> dict:
    """Poll the token endpoint until the user finishes sign-in; saves the token."""
    c = http or httpx.Client(timeout=TIMEOUT)
    interval = int(flow.get("interval") or 5)
    deadline = now() + int(flow.get("expires_in") or 900)
    while now() < deadline:
        sleep(interval)
        r = c.post(f"{_authority()}/token", data={
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": client_id(),
            "device_code": flow["device_code"],
        })
        data = r.json()
        if "access_token" in data:
            if not data.get("refresh_token"):
                raise RuntimeError("Sign-in finished but no refresh token was returned (offline_access missing).")
            return _store_token_response(data)
        err = data.get("error")
        if err == "authorization_pending":
            continue
        if err == "slow_down":
            interval += 5
            continue
        raise RuntimeError(f"Sign-in failed: {err}: {str(data.get('error_description', ''))[:300]}")
    raise RuntimeError("Sign-in code expired before it was used. Run the command again.")


# ── access token ────────────────────────────────────────────────────────────

def _access_token(http: httpx.Client) -> str:
    tok = load_token()
    if not tok:
        raise OutlookNotSignedIn(NOT_SIGNED_IN)
    if tok.get("access_token") and int(tok.get("expires_at") or 0) > time.time():
        return tok["access_token"]
    r = http.post(f"{_authority()}/token", data={
        "grant_type": "refresh_token",
        "client_id": tok.get("client_id") or client_id(),
        "refresh_token": tok["refresh_token"],
        "scope": " ".join(SCOPES),
    })
    data = r.json()
    if "access_token" not in data:
        err = data.get("error", "unknown")
        if err in ("invalid_grant", "interaction_required"):
            raise OutlookNotSignedIn(
                "Outlook sign-in expired or was revoked. Rafael signs in again on the Dell: " + SIGN_IN_COMMAND)
        raise RuntimeError(f"Outlook token refresh failed: {err}")
    if not data.get("refresh_token"):
        data["refresh_token"] = tok["refresh_token"]
    return _store_token_response(data)["access_token"]


def _graph_get(http: httpx.Client, path: str, params: Optional[dict] = None,
               headers: Optional[dict] = None) -> dict:
    """The ONLY way this module talks to Graph: GET on an allowlisted read path."""
    if not any(rx.match(path) for rx in _ALLOWED_PATHS):
        raise PermissionError(f"Outlook reader: path not allowed (read-only): {path}")
    h = {"Authorization": f"Bearer {_access_token(http)}"}
    if headers:
        h.update(headers)
    r = http.request("GET", GRAPH + path, params=params, headers=h)
    if r.status_code == 401:
        raise OutlookNotSignedIn("Outlook rejected the sign-in. Rafael signs in again on the Dell: " + SIGN_IN_COMMAND)
    if r.status_code >= 400:
        try:
            msg = r.json().get("error", {}).get("message", "")
        except Exception:
            msg = r.text[:200]
        raise RuntimeError(f"Outlook Graph error {r.status_code}: {msg[:300]}")
    return r.json()


# ── public read API ─────────────────────────────────────────────────────────

def _addr(x: Optional[dict]) -> str:
    ea = (x or {}).get("emailAddress") or {}
    name, addr = ea.get("name") or "", ea.get("address") or ""
    return f"{name} <{addr}>" if name and addr and name != addr else (addr or name)


def _parse_since(since: Optional[str]) -> Optional[str]:
    """'2026-10-01', '7d', '24h', 'today', 'yesterday' -> ISO date (UTC)."""
    if not since:
        return None
    s = str(since).strip().lower()
    now = datetime.now(timezone.utc)
    m = re.fullmatch(r"(\d+)\s*(d|day|days|h|hour|hours|w|week|weeks)", s)
    if m:
        n, u = int(m.group(1)), m.group(2)[0]
        delta = {"d": timedelta(days=n), "h": timedelta(hours=n), "w": timedelta(weeks=n)}[u]
        return (now - delta).strftime("%Y-%m-%dT%H:%M:%SZ")
    if s == "today":
        return now.strftime("%Y-%m-%dT00:00:00Z")
    if s == "yesterday":
        return (now - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s + "T00:00:00Z"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}t[\d:]+z?", s):
        return s.upper() if s.endswith("z") else s.upper() + "Z"
    raise ValueError(f"since not understood: {since!r} (use YYYY-MM-DD, 7d, 24h, today)")


def _folder_path(http: httpx.Client, folder: Optional[str]) -> str:
    if not folder:
        return "/me/messages"
    key = str(folder).strip().lower()
    if key in ("all", "any", "*"):
        return "/me/messages"
    if key in WELL_KNOWN_FOLDERS:
        return f"/me/mailFolders/{WELL_KNOWN_FOLDERS[key]}/messages"
    name = str(folder).strip().replace("'", "''")
    data = _graph_get(http, "/me/mailFolders",
                      params={"$filter": f"displayName eq '{name}'", "$select": "id,displayName"})
    vals = data.get("value") or []
    if not vals:
        raise ValueError(f"No Outlook folder named {folder!r}")
    return f"/me/mailFolders/{quote(vals[0]['id'], safe='')}/messages"


def search_messages(query: Optional[str] = None, folder: Optional[str] = None,
                    since: Optional[str] = None, limit: int = 10,
                    from_sender: Optional[str] = None, unread_only: bool = False,
                    http: Optional[httpx.Client] = None) -> dict:
    limit = max(1, min(int(limit or 10), 50))
    c = http or httpx.Client(timeout=TIMEOUT)
    path = _folder_path(c, folder)
    since_iso = _parse_since(since)
    params: dict = {"$top": str(limit), "$select": _LIST_FIELDS}
    headers: dict = {}
    terms = []
    if query and str(query).strip():
        terms.append(str(query).strip().replace('"', ""))
    if from_sender and str(from_sender).strip():
        terms.append(f"from:{str(from_sender).strip().replace(chr(34), '')}")
    if terms:
        # $search (KQL) cannot be combined with $orderby; results come by relevance/date.
        kql = " ".join(terms)
        if since_iso:
            kql += f" received>={since_iso[:10]}"
        if unread_only:
            kql += " isread:false"
        params["$search"] = f'"{kql}"'
        headers["ConsistencyLevel"] = "eventual"
    else:
        filters = []
        if since_iso:
            filters.append(f"receivedDateTime ge {since_iso}")
        if unread_only:
            filters.append("isRead eq false")
        if filters:
            params["$filter"] = " and ".join(filters)
        params["$orderby"] = "receivedDateTime desc"
    data = _graph_get(c, path, params=params, headers=headers or None)
    msgs = []
    for m in (data.get("value") or [])[:limit]:
        msgs.append({
            "id": m.get("id"),
            "from": _addr(m.get("from")),
            "subject": m.get("subject") or "(no subject)",
            "date": m.get("receivedDateTime"),
            "preview": (m.get("bodyPreview") or "")[:300],
            "unread": not m.get("isRead", True),
            "has_attachments": bool(m.get("hasAttachments")),
        })
    return {"success": True, "source": "outlook", "count": len(msgs), "emails": msgs,
            "query": query, "from_sender": from_sender, "folder": folder or "all", "since": since}


def read_message(message_id: str, http: Optional[httpx.Client] = None) -> dict:
    if not message_id or not re.fullmatch(r"[A-Za-z0-9_\-=%+/]+", str(message_id)):
        raise ValueError("message_id missing or invalid (use an id from the list result)")
    c = http or httpx.Client(timeout=TIMEOUT)
    mid = quote(str(message_id), safe="")
    m = _graph_get(c, f"/me/messages/{mid}", params={"$select": _READ_FIELDS},
                   headers={"Prefer": 'outlook.body-content-type="text"'})
    body = ((m.get("body") or {}).get("content") or "").strip()
    truncated = len(body) > MAX_BODY_CHARS
    return {
        "success": True, "source": "outlook", "id": m.get("id"),
        "from": _addr(m.get("from")),
        "to": [_addr(x) for x in (m.get("toRecipients") or [])],
        "cc": [_addr(x) for x in (m.get("ccRecipients") or [])],
        "subject": m.get("subject") or "(no subject)",
        "date": m.get("receivedDateTime"),
        "has_attachments": bool(m.get("hasAttachments")),
        "body": body[:MAX_BODY_CHARS] + ("\n[... truncated]" if truncated else ""),
    }
