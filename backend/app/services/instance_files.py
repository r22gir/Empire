"""Working copies stay on this machine. Google Drive is each user's own archive.

Tokens are stored per user under the instance data root. This module never
reads a founder Gmail token, a shared token.json, or anyone else's account.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode

DRIVE_SCOPES = (
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/photospicker.mediaitems.readonly",
)
PICKER_SESSION_URL = "https://photospicker.googleapis.com/v1/sessions"
PICKER_ITEMS_URL = "https://photospicker.googleapis.com/v1/mediaItems"


class FileArchiveError(Exception):
    pass


def edition_folder_name(edition: str | None = None) -> str:
    name = (edition or os.getenv("EMPIRE_EDITION") or "").strip().lower()
    if name == "maxine":
        return "Maxine"
    if name == "amp":
        return "Max-e"
    return "Max-e" if name == "" else name


def drive_path(*, business: str, project: str = "", client: str = "", day: str | None = None, edition: str | None = None) -> str:
    parts = [
        edition_folder_name(edition),
        _segment(business or "general"),
        _segment(project or "general"),
        _segment(client or "general"),
        day or date.today().isoformat(),
    ]
    return "/".join(parts)


def _segment(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "-_ " else "-" for ch in (value or "").strip())
    return cleaned.strip().replace(" ", "-") or "general"


def _root() -> Path:
    from app.edition import data_root_or_none

    root = data_root_or_none()
    if root is None:
        root = Path(os.path.expanduser("~/empire-data"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def working_root() -> Path:
    """Local working copy. The Dell keeps this. Drive is the archive."""
    path = _root() / "working"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _user_dir(user_id: str) -> Path:
    key = hashlib.sha256((user_id or "").strip().lower().encode("utf-8")).hexdigest()[:24]
    path = _root() / "drive_users" / key
    path.mkdir(parents=True, exist_ok=True)
    return path


def _reject_foreign_token(path: Path) -> Path:
    text = str(path).lower()
    if "gmail" in text or "token.json" == path.name and "drive_users" not in text:
        raise FileArchiveError("Esta ruta no es el Drive de un usuario de la instancia")
    return path


def token_path(user_id: str) -> Path:
    if not (user_id or "").strip():
        raise FileArchiveError("Falta el usuario. No hay una cuenta compartida.")
    path = _user_dir(user_id) / "google-user.json"
    return _reject_foreign_token(path)


def oauth_configured() -> bool:
    return bool(os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip() and os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip())


def connection_status(user_id: str) -> dict:
    connected = False
    if (user_id or "").strip():
        path = token_path(user_id)
        connected = path.is_file()
    return {
        "configured": oauth_configured(),
        "connected": connected,
        "uses_shared_founder_account": False,
        "working_copy": str(working_root()),
        "archive": "google_drive_per_user" if connected else "not_connected",
    }


def oauth_start(user_id: str, redirect_uri: str) -> dict:
    if not oauth_configured():
        return {
            "ok": False,
            "connected": False,
            "reason": "Esta instancia no tiene GOOGLE_OAUTH_CLIENT_ID. No uso otra cuenta.",
        }
    state = uuid.uuid4().hex
    (_user_dir(user_id) / "oauth-state.txt").write_text(state, encoding="utf-8")
    query = urlencode({
        "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"].strip(),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(DRIVE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "include_granted_scopes": "true",
    })
    return {
        "ok": True,
        "url": f"https://accounts.google.com/o/oauth2/v2/auth?{query}",
        "state": state,
    }


def oauth_finish(user_id: str, code: str, state: str, exchange) -> dict:
    """`exchange(code)` returns the token dict. Tests pass a fake exchange."""
    expected = (_user_dir(user_id) / "oauth-state.txt")
    if not expected.is_file() or expected.read_text(encoding="utf-8").strip() != (state or "").strip():
        raise FileArchiveError("El estado de OAuth no coincide")
    token = exchange(code)
    if not isinstance(token, dict) or not token.get("access_token"):
        raise FileArchiveError("Google no devolvió un token para este usuario")
    path = token_path(user_id)
    path.write_text(json.dumps({"user_id": user_id, **token}), encoding="utf-8")
    return {"ok": True, "connected": True, "uses_shared_founder_account": False}


def save_working_copy(*, relative: str, data: bytes) -> Path:
    dest = working_root() / relative.lstrip("/")
    if working_root() not in dest.resolve().parents and dest.resolve() != working_root():
        raise FileArchiveError("La copia de trabajo tiene que quedar en esta instancia")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest


def archive_draft(*, draft_id: str, filename: str, data: bytes, business: str, client: str = "", project: str = "", edition: str | None = None) -> dict:
    folder = drive_path(business=business, project=project, client=client, edition=edition)
    relative = f"{folder}/{filename}"
    path = save_working_copy(relative=relative, data=data)
    return {
        "working_copy": str(path),
        "drive_path": folder,
        "uploaded": False,
        "reason": "Queda en la copia de trabajo. Se sube al Drive del usuario cuando esa persona conecta su cuenta.",
    }


def connected_users() -> list[str]:
    base = _root() / "drive_users"
    found = []
    if not base.exists():
        return found
    for folder in base.iterdir():
        marker = folder / "user.txt"
        token = folder / "google-user.json"
        if token.is_file() and marker.is_file():
            found.append(marker.read_text(encoding="utf-8").strip())
    return found


def remember_user(user_id: str) -> None:
    (_user_dir(user_id) / "user.txt").write_text(user_id, encoding="utf-8")


def nightly_export() -> dict:
    """Copy instance db and docs to the working folder, then upload only for connected users."""
    day = date.today().isoformat()
    export_dir = working_root() / "exports" / day
    export_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    root = _root()
    for name in ("construction.db", "voice_drafts.db", "photos.db"):
        source = root / name
        if source.is_file():
            target = export_dir / name
            target.write_bytes(source.read_bytes())
            copied.append(name)
    businesses = root / "businesses"
    if businesses.is_dir():
        snap = export_dir / "businesses.json"
        rows = []
        for path in businesses.glob("*/business.json"):
            rows.append(path.read_text(encoding="utf-8"))
        snap.write_text("\n".join(rows), encoding="utf-8")
        copied.append("businesses.json")
    uploads = []
    for user_id in connected_users():
        uploads.append({
            "user_id": user_id,
            "uploaded": False,
            "drive_path": drive_path(business="export", project="nightly", client=user_id, day=day),
            "reason": "Token presente. La subida HTTP queda pendiente de GOOGLE_OAUTH y de red; no se usa otra cuenta.",
        })
    return {
        "day": day,
        "working_copy": str(export_dir),
        "files": copied,
        "uploads": uploads,
        "uses_shared_founder_account": False,
    }


def _photos():
    path = os.getenv("PHOTOS_DB", "").strip() or str(_root() / "photos.db")
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS photos (
            id TEXT PRIMARY KEY,
            project TEXT,
            lot TEXT,
            stage TEXT,
            source TEXT,
            filename TEXT,
            stored_path TEXT,
            picker_session TEXT,
            created_at TEXT
        )
        """
    )
    return conn


def save_photo(*, data: bytes, filename: str, project: str, lot: str = "", stage: str = "", source: str = "upload", picker_session: str = "") -> dict:
    if source not in {"upload", "chat", "google_photos_picker"}:
        raise FileArchiveError("Origen de foto desconocido")
    if source == "google_photos_picker" and not picker_session:
        raise FileArchiveError("Photos solo entra si el usuario lo eligió en el selector")
    photo_id = str(uuid.uuid4())
    relative = f"photos/{_segment(project)}/{date.today().isoformat()}/{photo_id}-{_segment(filename)}"
    path = save_working_copy(relative=relative, data=data)
    conn = _photos()
    try:
        conn.execute(
            """
            INSERT INTO photos (id, project, lot, stage, source, filename, stored_path, picker_session, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (photo_id, project, lot, stage, source, filename, str(path), picker_session or None, datetime.utcnow().isoformat(timespec="seconds")),
        )
        conn.commit()
    finally:
        conn.close()
    return {"id": photo_id, "project": project, "lot": lot, "stage": stage, "source": source, "path": str(path)}


def photo_timeline(project: str) -> list[dict]:
    conn = _photos()
    try:
        rows = conn.execute(
            "SELECT id, project, lot, stage, source, filename, created_at FROM photos WHERE project = ? ORDER BY created_at",
            (project,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def picker_session(user_id: str, opener) -> dict:
    """`opener(url, token)` performs the Photos Picker call. Tests pass a fake."""
    status = connection_status(user_id)
    if not status["connected"]:
        return {"ok": False, "reason": "Conecta la cuenta de Google de este usuario. No hay una cuenta compartida."}
    token = json.loads(token_path(user_id).read_text(encoding="utf-8"))
    created = opener(PICKER_SESSION_URL, token.get("access_token") or "")
    if not created.get("id"):
        raise FileArchiveError("El selector de Photos no abrió sesión")
    return {"ok": True, "session_id": created["id"], "picker_uri": created.get("pickerUri"), "picked_only": True}


def import_picked(*, user_id: str, session_id: str, project: str, lot: str = "", stage: str = "", fetch_items) -> list[dict]:
    """Import only the items the user picked in this session."""
    if not session_id:
        raise FileArchiveError("Sin sesión del selector no se lee la fototeca")
    token = json.loads(token_path(user_id).read_text(encoding="utf-8"))
    items = fetch_items(session_id, token.get("access_token") or "")
    saved = []
    for item in items:
        claimed = item.get("session_id") or item.get("sessionId")
        if claimed and claimed != session_id:
            continue
        media_id = item.get("id") or ""
        if not media_id:
            continue
        blob = item.get("bytes") or b""
        saved.append(save_photo(
            data=blob,
            filename=item.get("filename") or f"{media_id}.jpg",
            project=project,
            lot=lot,
            stage=stage,
            source="google_photos_picker",
            picker_session=session_id,
        ))
    return saved
