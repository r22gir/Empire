"""Unified file finder — local disks + Gmail attachments + Google Drive.

Read-only scopes only. This module never sends email, SMS, DMs, or social
posts; the `share` payload it returns is draft/proposal data only and the
founder must tap to send anything (see house rules).

Sources (merged and ranked with the same client-alias matching):
  a. Local disks — filename walk over safe, allow-listed roots (names only,
      never file contents).
  b. Gmail attachments — read-only Gmail OAuth (gmail.readonly). Token
      resolution: GMAIL_TOKEN_PATH env -> ~/.config/empirebox/gmail/token.json
      -> canonical backend token.json.
  c. Google Drive — read-only Drive OAuth (drive.readonly), searched only
      when a credential exists. Token resolution: GOOGLE_DRIVE_TOKEN_PATH env
      -> ~/.config/empirebox/drive/token.json.

Truth guard: every returned hit carries proof (source + id/path) and
`verified: True` only when it came from a real listing. Sources that were
not searched (no credential) or failed (bad token) are reported in
`gmail_status` / `drive_status` and `notices` — MAX must never claim
"nothing exists" when a source failed. A bad/expired/revoked Gmail token
surfaces as "Gmail needs re-auth".

Secret and family exclusions: secret-like filenames (.env, token.json,
credentials.json, *.pem/*.key, *secret*, founder PIN material) and
protected data stores (openclaw, test-studio, willard family data, .ssh,
.gnupg) are never returned.
"""
from __future__ import annotations

import fnmatch
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger("max.file_finder")

# ── Read-only scopes (never add write scopes here) ──────────────────────────
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

GMAIL_NEEDS_REAUTH = "Gmail needs re-auth"
DRIVE_NEEDS_REAUTH = "Drive needs re-auth"

_GMAIL_CONFIG_TOKEN = Path.home() / ".config" / "empirebox" / "gmail" / "token.json"
_DRIVE_CONFIG_TOKEN = Path.home() / ".config" / "empirebox" / "drive" / "token.json"


def _backend_dir() -> Path:
    return Path(__file__).resolve().parents[3]


def gmail_token_candidates() -> list[Path]:
    """Ordered Gmail OAuth token candidates (first existing wins)."""
    ordered: list[Path] = []
    env_path = os.getenv("GMAIL_TOKEN_PATH", "").strip()
    if env_path:
        ordered.append(Path(env_path).expanduser())
    ordered.append(_GMAIL_CONFIG_TOKEN)
    ordered.append(_backend_dir() / "token.json")
    return ordered


def drive_token_candidates() -> list[Path]:
    """Ordered Drive OAuth token candidates (first existing wins)."""
    ordered: list[Path] = []
    env_path = os.getenv("GOOGLE_DRIVE_TOKEN_PATH", "").strip()
    if env_path:
        ordered.append(Path(env_path).expanduser())
    ordered.append(_DRIVE_CONFIG_TOKEN)
    return ordered


def resolve_token(candidates: list[Path]) -> Optional[Path]:
    for candidate in candidates:
        try:
            if candidate.exists():
                return candidate
        except OSError:
            continue
    return None


# ── Secret + family exclusions ──────────────────────────────────────────────
# Never returned by any source. Covers house rules (OpenClaw / test-studio /
# willard family data) plus secret material that must never be surfaced.
EXCLUDED_PATH_PARTS = {
    "openclaw",
    "test-studio",
    "test_studio",
    "willard",
    ".ssh",
    ".gnupg",
    ".git",
    "node_modules",
    "__pycache__",
}

EXCLUDED_NAME_PATTERNS = (
    ".env*",
    "*token*.json",
    "*credential*.json",
    "*.pem",
    "*.key",
    "*secret*",
    "*founder_pin*",
    "*founder-pin*",
    "id_rsa*",
)


def is_excluded(name: str, path_parts: tuple[str, ...] = ()) -> bool:
    """True when a filename/path must never be surfaced (secret/family)."""
    lowered = name.lower()
    for pattern in EXCLUDED_NAME_PATTERNS:
        if fnmatch.fnmatch(lowered, pattern.lower()):
            return True
    for part in path_parts:
        if part.lower() in EXCLUDED_PATH_PARTS:
            return True
    return False


# ── Client-alias matching (same normalization for every source) ─────────────
def normalize_alias(text: str) -> str:
    """Normalize a filename/query for client-alias matching."""
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def match_score(query: str, candidate: str) -> int:
    """Rank score 0-100 using the same alias matching for all sources."""
    q = normalize_alias(query)
    c = normalize_alias(candidate)
    if not q or not c:
        return 0
    if c == q:
        return 100
    if c.startswith(q):
        return 80
    if q in c:
        return 60
    q_tokens = set(q.split())
    c_tokens = set(c.split())
    if q_tokens and q_tokens & c_tokens:
        overlap = len(q_tokens & c_tokens) / len(q_tokens)
        return int(20 + overlap * 30)  # 21-50 by token overlap
    return 0


# ── Share paths (draft-only proposals — never sent by this module) ──────────
def founder_addresses() -> list[str]:
    """Rafael's own addresses: FOUNDER_EMAIL + MAX_EMAIL_ALLOWED_SENDERS."""
    addresses: list[str] = []
    founder = os.getenv("FOUNDER_EMAIL", "empirebox2026@gmail.com").strip()
    if founder:
        addresses.append(founder)
    for item in os.getenv("MAX_EMAIL_ALLOWED_SENDERS", "").split(","):
        item = item.strip()
        if item and "@" in item and item.lower() not in {a.lower() for a in addresses}:
            addresses.append(item)
    return addresses


def share_paths(filename: str, source: str, source_id: str = "") -> dict:
    """Draft-only share options: Studio link, email to Rafael, WhatsApp draft."""
    studio_base = os.getenv("STUDIO_URL", "https://studio.empirebox.store").rstrip("/")
    return {
        "studio_link": f"{studio_base}/files/{source}/{source_id or filename}",
        "email_to": founder_addresses(),
        "email_note": "draft-only — founder tap required before any send",
        "whatsapp_to": "Rafael",
        "whatsapp_note": "draft-only — founder tap required before any send",
    }


# ── Local search ────────────────────────────────────────────────────────────
def default_local_roots() -> list[Path]:
    """Safe, read-only local roots (env-overridable, existing dirs only)."""
    raw = os.getenv("FILE_FINDER_LOCAL_ROOTS", "").strip()
    repo = Path.home() / "empire-repo"
    defaults = [
        repo / "uploads",
        repo / "creations",
        repo / "empire-command-center" / "public",
    ]
    candidates = (
        [Path(p).expanduser() for p in raw.split(os.pathsep) if p.strip()]
        if raw
        else defaults
    )
    roots = []
    for candidate in candidates:
        try:
            if candidate.is_dir():
                roots.append(candidate)
        except OSError:
            continue
    return roots


def search_local(
    query: str,
    limit: int = 10,
    roots: Optional[list[Path]] = None,
) -> list[dict]:
    """Filename-only walk over safe roots (never reads file contents)."""
    hits: list[dict] = []
    for root in roots if roots is not None else default_local_roots():
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                # Prune excluded dirs (secret/family stores) before descending.
                dirnames[:] = [
                    d for d in dirnames if d.lower() not in EXCLUDED_PATH_PARTS
                ]
                rel_parts = tuple(Path(dirpath).relative_to(root).parts)
                if any(p.lower() in EXCLUDED_PATH_PARTS for p in rel_parts):
                    continue
                for filename in filenames:
                    if is_excluded(filename, rel_parts):
                        continue
                    score = match_score(query, filename)
                    if score <= 0:
                        continue
                    full_path = str(Path(dirpath) / filename)
                    try:
                        stat = os.stat(full_path)
                        size, mtime = stat.st_size, stat.st_mtime
                    except OSError:
                        size, mtime = 0, 0.0
                    hits.append(
                        {
                            "name": filename,
                            "source": "local",
                            "path": full_path,
                            "score": score,
                            "size": size,
                            "mtime": mtime,
                            "verified": True,
                            "proof": {"source": "local", "path": full_path},
                            "share": share_paths(filename, "local", full_path),
                        }
                    )
        except OSError as exc:
            logger.warning("file_finder local walk failed for %s: %s", root, exc)
    hits.sort(key=lambda h: (-h["score"], h["name"].lower()))
    return hits[: max(limit, 0)]


# ── Google service builders (lazy imports — stub-friendly) ─────────────────
def _reauth_error_text(exc: Exception) -> Optional[str]:
    text = f"{type(exc).__name__}: {exc}".lower()
    markers = (
        "invalid_grant",
        "expired or revoked",
        "token has been expired or revoked",
        "refresherror",
        "unauthorized",
        "invalid credentials",
        "invalid_client",
    )
    if any(marker in text for marker in markers):
        return text
    status = getattr(exc, "status", getattr(exc, "status_code", None))
    if status in (401, 403) and ("auth" in text or "credential" in text or "token" in text):
        return text
    return None


def build_gmail_service(token_path: Path):
    """Build a read-only Gmail API service from a saved OAuth token."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(str(token_path), GMAIL_SCOPES)
    if getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
        creds.refresh(Request())
        try:
            token_path.write_text(creds.to_json())
        except OSError:
            logger.warning("file_finder: could not persist refreshed Gmail token")
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def build_drive_service(token_path: Path):
    """Build a read-only Drive API service from a saved OAuth token."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(str(token_path), DRIVE_SCOPES)
    if getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
        creds.refresh(Request())
        try:
            token_path.write_text(creds.to_json())
        except OSError:
            logger.warning("file_finder: could not persist refreshed Drive token")
    return build("drive", "v3", credentials=creds, cache_discovery=False)


# ── Gmail attachment search ─────────────────────────────────────────────────
def _gmail_attachment_filenames(payload: dict) -> list[str]:
    """Collect attachment filenames from a Gmail message payload (recursive)."""
    names: list[str] = []

    def visit(part: dict) -> None:
        filename = (part.get("filename") or "").strip()
        body = part.get("body") or {}
        if filename and (body.get("attachmentId") or body.get("size", 0)):
            names.append(filename)
        for sub in part.get("parts") or []:
            visit(sub)

    if isinstance(payload, dict):
        visit(payload)
    return names


def search_gmail_attachments(
    query: str,
    limit: int = 10,
    gmail_factory: Optional[Callable[[], Any]] = None,
) -> dict:
    """Search Gmail messages with attachments matching the query.

    Returns {"status": ..., "hits": [...], "notice": ...} where status is one
    of "ok" | "not_configured" | "needs_reauth" | "error".
    """
    token_path = resolve_token(gmail_token_candidates())
    if gmail_factory is None and token_path is None:
        return {
            "status": "needs_reauth",
            "hits": [],
            "notice": f"{GMAIL_NEEDS_REAUTH} (no Gmail OAuth token found).",
        }
    try:
        service = gmail_factory() if gmail_factory else build_gmail_service(token_path)  # type: ignore[arg-type]
        listed = (
            service.users()
            .messages()
            .list(userId="me", q=f"has:attachment {query}", maxResults=min(limit, 20))
            .execute()
        )
        hits: list[dict] = []
        for ref in listed.get("messages", []) or []:
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=ref["id"], format="full")
                .execute()
            )
            headers = {
                h.get("name", ""): h.get("value", "")
                for h in (msg.get("payload", {}).get("headers", []) or [])
            }
            subject = headers.get("Subject", "(no subject)")
            for filename in _gmail_attachment_filenames(msg.get("payload", {})):
                if is_excluded(filename):
                    continue
                score = max(
                    match_score(query, filename), match_score(query, subject)
                )
                if score <= 0:
                    continue
                hits.append(
                    {
                        "name": filename,
                        "source": "gmail",
                        "subject": subject,
                        "message_id": ref["id"],
                        "score": score,
                        "verified": True,
                        "proof": {
                            "source": "gmail",
                            "message_id": ref["id"],
                            "attachment": filename,
                        },
                        "share": share_paths(filename, "gmail", ref["id"]),
                    }
                )
        hits.sort(key=lambda h: (-h["score"], h["name"].lower()))
        return {"status": "ok", "hits": hits[: max(limit, 0)], "notice": ""}
    except Exception as exc:  # noqa: BLE001 — mapped to status, never raised
        if _reauth_error_text(exc) is not None:
            logger.warning("file_finder Gmail re-auth required: %s", exc)
            return {"status": "needs_reauth", "hits": [], "notice": GMAIL_NEEDS_REAUTH}
        logger.error("file_finder Gmail search failed: %s", exc)
        return {"status": "error", "hits": [], "notice": f"Gmail search failed: {exc}"}


# ── Drive search ────────────────────────────────────────────────────────────
def _drive_query(query: str) -> str:
    safe = query.replace("'", "\\'").strip()
    return f"name contains '{safe}' and trashed = false"


def search_drive(
    query: str,
    limit: int = 10,
    drive_factory: Optional[Callable[[], Any]] = None,
) -> dict:
    """Search Rafael's Google Drive filenames matching the query.

    Returns {"status": ..., "hits": [...], "notice": ...} where status is one
    of "ok" | "not_configured" | "needs_reauth" | "error". A missing
    credential is "not_configured" (Drive skipped); a bad token is
    "needs_reauth".
    """
    token_path = resolve_token(drive_token_candidates())
    if drive_factory is None and token_path is None:
        return {"status": "not_configured", "hits": [], "notice": ""}
    try:
        service = drive_factory() if drive_factory else build_drive_service(token_path)  # type: ignore[arg-type]
        listed = (
            service.files()
            .list(
                q=_drive_query(query),
                fields="files(id,name,mimeType,size,modifiedTime)",
                pageSize=min(limit, 20),
            )
            .execute()
        )
        hits: list[dict] = []
        for item in listed.get("files", []) or []:
            filename = (item.get("name") or "").strip()
            if not filename or is_excluded(filename):
                continue
            score = match_score(query, filename)
            if score <= 0:
                continue
            hits.append(
                {
                    "name": filename,
                    "source": "drive",
                    "file_id": item.get("id", ""),
                    "mime_type": item.get("mimeType", ""),
                    "score": score,
                    "verified": True,
                    "proof": {
                        "source": "drive",
                        "file_id": item.get("id", ""),
                        "name": filename,
                    },
                    "share": share_paths(filename, "drive", item.get("id", "")),
                }
            )
        hits.sort(key=lambda h: (-h["score"], h["name"].lower()))
        return {"status": "ok", "hits": hits[: max(limit, 0)], "notice": ""}
    except Exception as exc:  # noqa: BLE001 — mapped to status, never raised
        if _reauth_error_text(exc) is not None:
            logger.warning("file_finder Drive re-auth required: %s", exc)
            return {"status": "needs_reauth", "hits": [], "notice": DRIVE_NEEDS_REAUTH}
        logger.error("file_finder Drive search failed: %s", exc)
        return {"status": "error", "hits": [], "notice": f"Drive search failed: {exc}"}


# ── Merge + rank ────────────────────────────────────────────────────────────
_SOURCE_ORDER = {"local": 0, "gmail": 1, "drive": 2}


@dataclass
class FindFilesResult:
    query: str
    results: list[dict] = field(default_factory=list)
    searched_sources: list[str] = field(default_factory=list)
    failed_sources: list[str] = field(default_factory=list)
    gmail_status: str = "not_configured"
    drive_status: str = "not_configured"
    notices: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "count": len(self.results),
            "results": self.results,
            "searched_sources": self.searched_sources,
            "failed_sources": self.failed_sources,
            "gmail_status": self.gmail_status,
            "drive_status": self.drive_status,
            "notices": self.notices,
        }


def find_files(
    query: str,
    limit: int = 10,
    include_gmail: bool = True,
    include_drive: bool = True,
    gmail_factory: Optional[Callable[[], Any]] = None,
    drive_factory: Optional[Callable[[], Any]] = None,
    local_roots: Optional[list[Path]] = None,
) -> dict:
    """Search local disks, Gmail attachments, and Drive; merge and rank.

    Never raises for source failures — they land in `failed_sources` /
    `notices` so MAX never claims "nothing exists" when a source failed.
    """
    query = (query or "").strip()
    limit = max(min(int(limit or 10), 20), 1)
    merged: list[dict] = []
    searched = ["local"]
    failed: list[str] = []
    notices: list[str] = []

    merged.extend(search_local(query, limit=limit, roots=local_roots))

    gmail_status = "skipped"
    if include_gmail:
        gmail = search_gmail_attachments(
            query, limit=limit, gmail_factory=gmail_factory
        )
        gmail_status = gmail["status"]
        if gmail_status == "ok":
            searched.append("gmail")
            merged.extend(gmail["hits"])
        elif gmail_status in ("needs_reauth", "error"):
            failed.append("gmail")
            notices.append(gmail["notice"])
        # "not_configured" is unreachable (missing token -> needs_reauth).

    drive_status = "skipped"
    if include_drive:
        drive = search_drive(query, limit=limit, drive_factory=drive_factory)
        drive_status = drive["status"]
        if drive_status == "ok":
            searched.append("drive")
            merged.extend(drive["hits"])
        elif drive_status in ("needs_reauth", "error"):
            failed.append("drive")
            notices.append(drive["notice"])
        # "not_configured" -> Drive silently skipped (no credential exists).

    merged.sort(
        key=lambda h: (
            -h["score"],
            _SOURCE_ORDER.get(h.get("source", ""), 9),
            h["name"].lower(),
        )
    )
    return FindFilesResult(
        query=query,
        results=merged[:limit],
        searched_sources=searched,
        failed_sources=failed,
        gmail_status=gmail_status,
        drive_status=drive_status,
        notices=[n for n in notices if n],
    ).to_dict()
