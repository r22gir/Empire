"""Gmail attachments + Google Drive for Rafael's file finder (read-only).

2026-10-06 (improvement #5, "Yes. Delegate"). find_files also looks in:
- Gmail attachments of empirebox2026@gmail.com, via the existing read-only
  Gmail OAuth (gmail.readonly; gmail_reader._get_service, token at
  ~/.config/empirebox/gmail/token.json);
- Rafael's Google Drive, via a separate drive.readonly token at
  ~/.config/empirebox/gdrive/token.json (backend/drive_auth.py). The rclone
  "gdrive" remote on the Dell has full read-write scope, so it is NOT used.

Results are scored with the same ranking and client aliases as local files
(file_finder._score) and use the same secret/family name exclusions.
A bad or missing token is reported as a status ("needs_reauth" /
"not_connected"), never as "nothing exists". Downloads only happen for an
explicit share, into a private temp cache.
"""
from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import logging
import os
import re
import secrets
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from app.services.max import file_finder as ff

logger = logging.getLogger("max.cloud_files")

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
DRIVE_DIR = Path(os.path.expanduser("~")) / ".config" / "empirebox" / "gdrive"
CLOUD_TIMEOUT = float(os.getenv("MAX_CLOUD_SEARCH_TIMEOUT", "12"))
MAX_GMAIL_MESSAGES = 25
MAX_DRIVE_FILES = 40
REAUTH_GMAIL = ("Gmail needs re-auth: the Gmail read token on the Dell is expired or revoked, so email "
                "attachments were NOT searched. Rafael: run `cd ~/empire-repo-main/backend && venv/bin/python "
                "gmail_auth.py --browser` on the Dell.")
CONNECT_DRIVE = ("Google Drive is not connected (no read-only Drive token on the Dell), so Drive was NOT searched. "
                 "Rafael: run `cd ~/empire-repo-main/backend && venv/bin/python drive_auth.py --browser` on the Dell.")
REAUTH_DRIVE = ("Google Drive needs re-auth: the Drive read token is expired or revoked, so Drive was NOT searched. "
                "Rafael: run `cd ~/empire-repo-main/backend && venv/bin/python drive_auth.py --browser` on the Dell.")

GOOGLE_EXPORT = {  # native Google files -> PDF on share
    "application/vnd.google-apps.document": ("application/pdf", ".pdf"),
    "application/vnd.google-apps.spreadsheet": ("application/pdf", ".pdf"),
    "application/vnd.google-apps.presentation": ("application/pdf", ".pdf"),
    "application/vnd.google-apps.drawing": ("application/pdf", ".pdf"),
}

# Remote refs live only in this process (same lifetime as share links).
_REMOTE: dict[str, dict] = {}
_LOCK = threading.Lock()
_CACHE_DIR: Optional[Path] = None


def _is_auth_error(exc: BaseException) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    return any(s in text for s in ("invalid_grant", "refresherror", "token not found", "unauthorized",
                                   "invalid_client", "401", "insufficient", "token has been expired"))


# ── services (patched in tests) ─────────────────────────────────────
def _gmail_service():
    from app.services.max.gmail_reader import _get_service
    return _get_service()


def drive_token_path() -> Path:
    return Path(os.getenv("GDRIVE_TOKEN_PATH") or (DRIVE_DIR / "token.json"))


def _drive_service():
    p = drive_token_path()
    if not p.exists():
        raise FileNotFoundError("drive token not found")
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    import json as _json
    info = _json.loads(p.read_text())
    raw = info.get("scopes") or info.get("scope") or []
    granted = set(raw.split() if isinstance(raw, str) else raw)
    if not granted or not granted <= set(DRIVE_SCOPES):
        raise PermissionError("drive token is not drive.readonly-only; refusing to use it")
    creds = Credentials.from_authorized_user_info(info, DRIVE_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        p.write_text(creds.to_json())
    return build("drive", "v3", credentials=creds, cache_discovery=False)


# ── query building ──────────────────────────────────────────────────
def _q_words(q: dict) -> tuple[list[str], list[str]]:
    """(any-of client words, all-of terms)."""
    client_any: list[str] = []
    if q.get("client"):
        client_any = sorted(set(q.get("client_words") or []) | set(q["client"].get("alias_words") or []))
        client_any = [w for w in client_any if len(w) >= 3]
    terms = [t for t in (q.get("terms") or []) if len(t) >= 3]
    return client_any, terms


def gmail_query(q: dict) -> str:
    parts = ["has:attachment"]
    client_any, terms = _q_words(q)
    if q.get("quote_number"):
        parts.append(f'"{q["quote_number"]}"')
    if client_any:
        parts.append("{" + " ".join(client_any) + "}")
    parts.extend(terms)
    types = set(q.get("types") or [])
    if types & {"photo", "photos"}:
        parts.append("{filename:jpg filename:jpeg filename:png filename:heic}")
    elif types & {"pdf", "pdfs"}:
        parts.append("filename:pdf")
    elif types & {"spreadsheet"}:
        parts.append("{filename:xlsx filename:xls filename:csv}")
    return " ".join(parts)


def _drive_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("'", "\\'")


def drive_query(q: dict) -> str:
    client_any, terms = _q_words(q)
    clauses = ["trashed = false", "mimeType != 'application/vnd.google-apps.folder'"]
    if q.get("quote_number"):
        clauses.append(f"(name contains '{_drive_escape(q['quote_number'])}' or fullText contains "
                       f"'{_drive_escape(q['quote_number'])}')")
    if client_any:
        clauses.append("(" + " or ".join(f"name contains '{_drive_escape(w)}'" for w in client_any) + ")")
    for t in terms:
        clauses.append(f"name contains '{_drive_escape(t)}'")
    return " and ".join(clauses)


# ── search ──────────────────────────────────────────────────────────
def _remember(ref: dict) -> str:
    raw = f"{ref['source']}:{ref.get('message_id','')}:{ref.get('attachment_id','')}:{ref.get('file_id','')}:{ref['name']}"
    fid = ref["source"][:2] + "-" + hashlib.sha256(ff._SECRET + raw.encode()).hexdigest()[:18]
    with _LOCK:
        _REMOTE[fid] = ref
        if len(_REMOTE) > 5000:
            for k in list(_REMOTE)[:1000]:
                _REMOTE.pop(k, None)
    return fid


def _entry_for(name: str, context: str, mtime: float, size: int, source: str) -> ff.Entry:
    return ff.Entry(path=f"/{source}/{name}", name=name, size=int(size or 0), mtime=float(mtime or 0), root=source,
                    tokens=tuple(ff._tokens(os.path.splitext(name)[0])) + tuple(ff._tokens(os.path.splitext(name)[1])),
                    dir_tokens=tuple(ff._tokens(context))[:40])


def _walk_parts(payload: dict) -> list[dict]:
    out, stack = [], [payload or {}]
    while stack:
        p = stack.pop()
        if p.get("filename") and (p.get("body") or {}).get("attachmentId"):
            out.append(p)
        stack.extend(p.get("parts") or [])
    return out


def search_gmail(q: dict, *, service_factory: Optional[Callable] = None) -> dict:
    try:
        svc = (service_factory or _gmail_service)()
        query = gmail_query(q)
        listing = svc.users().messages().list(userId="me", q=query, maxResults=MAX_GMAIL_MESSAGES).execute() or {}
        hits = []
        for m in (listing.get("messages") or [])[:MAX_GMAIL_MESSAGES]:
            msg = svc.users().messages().get(userId="me", id=m["id"], format="full").execute() or {}
            headers = {h.get("name", "").lower(): h.get("value", "") for h in (msg.get("payload") or {}).get("headers") or []}
            subject, sender = headers.get("subject", ""), headers.get("from", "")
            mtime = int(msg.get("internalDate") or 0) / 1000.0
            for part in _walk_parts(msg.get("payload") or {}):
                name = part["filename"]
                if ff._name_excluded(name):
                    continue
                hits.append({"source": "gmail", "name": name, "mime": part.get("mimeType") or "",
                             "size": int((part.get("body") or {}).get("size") or 0), "mtime": mtime,
                             "message_id": msg.get("id") or m["id"], "thread_id": msg.get("threadId") or "",
                             "attachment_id": part["body"]["attachmentId"], "subject": subject, "from": sender,
                             "context": f"{subject} {sender}"})
        return {"status": "ok", "query": query, "hits": hits}
    except Exception as exc:
        if _is_auth_error(exc):
            return {"status": "needs_reauth", "message": REAUTH_GMAIL, "hits": []}
        logger.warning("cloud_files: gmail search failed: %s", type(exc).__name__)
        return {"status": "error", "message": f"Gmail search failed ({type(exc).__name__}); attachments not searched.",
                "hits": []}


def search_drive(q: dict, *, service_factory: Optional[Callable] = None) -> dict:
    if service_factory is None and not drive_token_path().exists():
        return {"status": "not_connected", "message": CONNECT_DRIVE, "hits": []}
    try:
        svc = (service_factory or _drive_service)()
        query = drive_query(q)
        res = svc.files().list(q=query, pageSize=MAX_DRIVE_FILES, orderBy="modifiedTime desc",
                               fields="files(id,name,mimeType,modifiedTime,size,webViewLink)",
                               supportsAllDrives=True, includeItemsFromAllDrives=True).execute() or {}
        hits = []
        for f in res.get("files") or []:
            name = f.get("name") or ""
            if not name or ff._name_excluded(name):
                continue
            try:
                from datetime import datetime
                mtime = datetime.fromisoformat(str(f.get("modifiedTime", "")).replace("Z", "+00:00")).timestamp()
            except Exception:
                mtime = 0.0
            hits.append({"source": "drive", "name": name, "mime": f.get("mimeType") or "",
                         "size": int(f.get("size") or 0), "mtime": mtime, "file_id": f.get("id"),
                         "web_link": f.get("webViewLink") or "", "context": "google drive"})
        return {"status": "ok", "query": query, "hits": hits}
    except FileNotFoundError:
        return {"status": "not_connected", "message": CONNECT_DRIVE, "hits": []}
    except PermissionError as exc:
        return {"status": "error", "message": f"Drive not used: {exc}", "hits": []}
    except Exception as exc:
        if _is_auth_error(exc):
            return {"status": "needs_reauth", "message": REAUTH_DRIVE, "hits": []}
        logger.warning("cloud_files: drive search failed: %s", type(exc).__name__)
        return {"status": "error", "message": f"Drive search failed ({type(exc).__name__}); Drive not searched.",
                "hits": []}


def search_cloud(query: str, *, gmail_factory=None, drive_factory=None, timeout: float = CLOUD_TIMEOUT) -> dict:
    """Search Gmail attachments + Drive in parallel; score with the local ranking."""
    if not ff._edition_allowed() or os.getenv("MAX_CLOUD_FILES_DISABLED") == "1":
        return {"matches": [], "status": {}}
    q = ff.parse_query(query)
    if not (q["terms"] or q["client"] or q["quote_number"]):
        return {"matches": [], "status": {}}
    status: dict[str, dict] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futs = {"gmail": pool.submit(search_gmail, q, service_factory=gmail_factory),
                "drive": pool.submit(search_drive, q, service_factory=drive_factory)}
        for src, fut in futs.items():
            try:
                status[src] = fut.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                status[src] = {"status": "timeout", "message": f"{src} search timed out; not searched.", "hits": []}
    matches = []
    client_any, terms = _q_words(q)
    # Gmail matched these words server-side (subject/body); count them as context for ranking.
    server_ctx = " ".join(client_any + terms + ([q["quote_number"]] if q.get("quote_number") else []))
    for src, res in status.items():
        for h in res.get("hits") or []:
            ctx = h.get("context", "") + (" " + server_ctx if src == "gmail" else "")
            e = _entry_for(h["name"], ctx, h.get("mtime", 0), h.get("size", 0), src)
            sc, why = ff._score(e, q)
            if sc <= 0:
                continue
            fid = _remember(h)
            where = (f"Gmail: \"{h.get('subject','')[:80]}\" from {h.get('from','')[:60]}" if src == "gmail"
                     else "Google Drive")
            matches.append({"file_id": fid, "name": h["name"], "source": src, "path": where, "folder": where,
                            "size": ff._human_size(h.get("size") or 0),
                            "modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(h.get("mtime") or 0)),
                            "score": round(sc, 1), "why": why, "other_copies": 0, "copy_paths": [],
                            "is_final": "final" in e.tokens,
                            "web_link": h.get("web_link") or (f"https://mail.google.com/mail/u/0/#all/{h.get('thread_id')}"
                                                              if src == "gmail" and h.get("thread_id") else "")})
    return {"matches": matches,
            "status": {k: {"status": v.get("status"), "message": v.get("message", "")} for k, v in status.items()}}


# ── share support ───────────────────────────────────────────────────
def get_remote(fid: str) -> Optional[dict]:
    with _LOCK:
        return _REMOTE.get((fid or "").strip())


def cache_dir() -> Path:
    global _CACHE_DIR
    if _CACHE_DIR is None or not _CACHE_DIR.exists():
        _CACHE_DIR = Path(tempfile.mkdtemp(prefix="max-cloud-share-"))
        os.chmod(_CACHE_DIR, 0o700)
    return _CACHE_DIR


def download_remote(ref: dict, *, gmail_factory=None, drive_factory=None, max_bytes: int = 25 * 1024 * 1024) -> str:
    """Fetch one Gmail attachment / Drive file into the private cache. Returns the local temp path."""
    name = os.path.basename(ref["name"]) or "file"
    if ref["source"] == "gmail":
        svc = (gmail_factory or _gmail_service)()
        att = svc.users().messages().attachments().get(userId="me", messageId=ref["message_id"],
                                                        id=ref["attachment_id"]).execute() or {}
        data = base64.urlsafe_b64decode((att.get("data") or "") + "=" * (-len(att.get("data") or "") % 4))
    elif ref["source"] == "drive":
        svc = (drive_factory or _drive_service)()
        mime = ref.get("mime") or ""
        if mime in GOOGLE_EXPORT:
            out_mime, ext = GOOGLE_EXPORT[mime]
            data = svc.files().export(fileId=ref["file_id"], mimeType=out_mime).execute()
            if not name.lower().endswith(ext):
                name += ext
        else:
            data = svc.files().get_media(fileId=ref["file_id"], supportsAllDrives=True).execute()
    else:
        raise ValueError("unknown source")
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise RuntimeError("download returned no data")
    if len(data) > max_bytes:
        raise ValueError(f"file is larger than {max_bytes // (1024 * 1024)} MB")
    d = cache_dir() / secrets.token_hex(8)
    d.mkdir(mode=0o700)
    p = d / name
    p.write_bytes(bytes(data))
    return str(p)


def is_cached_share(path: str) -> bool:
    if _CACHE_DIR is None:
        return False
    real = os.path.realpath(path)
    base = os.path.realpath(str(_CACHE_DIR))
    return real.startswith(base + "/") and os.path.isfile(real) and not ff._name_excluded(os.path.basename(real))
