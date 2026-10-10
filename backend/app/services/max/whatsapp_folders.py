"""Phase 0 WhatsApp folders: client job, or personal / insurance / store / luxeforge.

Every fileable batch is filed under this edition's jobs root. Reserved
folders never create a LuxeForge job, lead, or estimate. The shared
record is JOB-RECORD.json next to JOB-FACTS.md so Max, the job board,
and the chat log can read the same attachments later.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.services.max.doc_lookup import jobs_root, probe_job_text

RESERVED_FOLDER_SLUGS = ("personal", "insurance", "store", "luxeforge")
RESERVED_FOLDER_ALIASES: dict[str, tuple[str, ...]] = {
    "personal": ("personal", "private"),
    "insurance": ("insurance", "claim"),
    "store": ("store", "shop", "showroom"),
    "luxeforge": ("luxeforge", "luxe forge", "luxe-forge"),
}
FOLDER_SUBDIRS = ("photos", "received", "scans")
JOB_RECORD_NAME = "JOB-RECORD.json"
JOB_FACTS_NAME = "JOB-FACTS.md"
SCAN_EXTENSIONS = {
    ".stl", ".glb", ".gltf", ".obj", ".usdz", ".ply", ".fbx",
}
SCAN_MIME_HINTS = (
    "model/stl",
    "model/gltf",
    "model/vnd.usdz",
    "application/sla",
    "application/vnd.ms-pki.stl",
)
FILEABLE_MEDIA = {"image", "photo", "document", "scan", "model"}


def folder_kind_for_slug(slug: str) -> str:
    raw = (slug or "").strip().lower()
    if raw in RESERVED_FOLDER_SLUGS:
        return raw
    return "client"


def folder_allows_quote(slug: Optional[str]) -> bool:
    """Estimates only for a resolved client folder. Reserved + unknown: never."""
    if not slug:
        return False
    return folder_kind_for_slug(slug) == "client"


def ensure_reserved_folders(*, jobs_root_path: Optional[Path | str] = None) -> list[Path]:
    """Create personal / insurance / store / luxeforge under this edition only."""
    root = jobs_root(jobs_root_path)
    created: list[Path] = []
    for slug in RESERVED_FOLDER_SLUGS:
        folder = root / slug
        folder.mkdir(parents=True, exist_ok=True)
        for sub in FOLDER_SUBDIRS:
            (folder / sub).mkdir(parents=True, exist_ok=True)
        created.append(folder)
    return created


def match_reserved_folder(text: str) -> Optional[dict[str, str]]:
    blob = " ".join(str(text or "").lower().split())
    if not blob:
        return None
    hits: list[tuple[int, str, str]] = []
    for slug, aliases in RESERVED_FOLDER_ALIASES.items():
        for alias in aliases:
            for match in re.finditer(
                r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", blob
            ):
                hits.append((match.start(), slug, alias))
    if not hits:
        return None
    hits.sort()
    _pos, slug, alias = hits[0]
    root = jobs_root()
    return {
        "slug": slug,
        "client_name": slug.replace("-", " ").title(),
        "folder_path": str(root / slug),
        "kind": slug,
        "match_reason": f"reserved folder '{alias}'",
    }


def resolve_folder(text: str) -> Optional[dict[str, str]]:
    """Reserved folder word wins; else a unique client match. Never guesses."""
    ensure_reserved_folders()
    reserved = match_reserved_folder(text)
    if reserved:
        return reserved
    probed = probe_job_text(text)
    if probed.get("status") == "unique" and probed.get("match"):
        match = dict(probed["match"])
        match["kind"] = folder_kind_for_slug(str(match.get("slug") or ""))
        return match
    return None


def is_scan_file(filename: str = "", mime_type: str = "", media_type: str = "") -> bool:
    if (media_type or "").lower() in {"scan", "model", "stl", "polycam"}:
        return True
    ext = Path(filename or "").suffix.lower()
    if ext in SCAN_EXTENSIONS:
        return True
    mime = (mime_type or "").split(";")[0].strip().lower()
    return any(hint in mime for hint in SCAN_MIME_HINTS)


def classify_media_type(
    message_type: str = "",
    filename: str = "",
    mime_type: str = "",
) -> str:
    kind = (message_type or "").strip().lower()
    if kind in {"image", "photo"}:
        return "image"
    if is_scan_file(filename, mime_type, kind):
        return "scan"
    if kind in {"document", "scan", "model"}:
        return "document" if kind == "document" else "scan"
    return kind or "document"


def filing_subdir(media_type: str, filename: str = "", mime_type: str = "") -> str:
    if (media_type or "").lower() in {"image", "photo"}:
        return "photos"
    if is_scan_file(filename, mime_type, media_type):
        return "scans"
    return "received"


def job_record_path(slug: str, *, jobs_root_path: Optional[Path | str] = None) -> Path:
    return jobs_root(jobs_root_path) / slug / JOB_RECORD_NAME


def read_job_record(slug: str, *, jobs_root_path: Optional[Path | str] = None) -> dict[str, Any]:
    path = job_record_path(slug, jobs_root_path=jobs_root_path)
    if not path.is_file():
        return empty_job_record(slug, jobs_root_path=jobs_root_path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return empty_job_record(slug, jobs_root_path=jobs_root_path)
    return data if isinstance(data, dict) else empty_job_record(slug, jobs_root_path=jobs_root_path)


def empty_job_record(slug: str, *, jobs_root_path: Optional[Path | str] = None) -> dict[str, Any]:
    kind = folder_kind_for_slug(slug)
    return {
        "version": 1,
        "slug": slug,
        "kind": kind,
        "intake_id": None,
        "quote_id": None,
        "quote_number": None,
        "lead_id": None,
        "owner": "founder",
        "attachments": [],
        "updated_at": "",
    }


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content or b"").hexdigest()


def append_job_record(
    slug: str,
    attachment: dict[str, Any],
    *,
    content: bytes = b"",
    jobs_root_path: Optional[Path | str] = None,
) -> dict[str, Any]:
    """Append one filed file to JOB-RECORD.json. Never writes intake/quote/lead ids."""
    if not slug:
        return empty_job_record(slug or "", jobs_root_path=jobs_root_path)
    folder = jobs_root(jobs_root_path) / slug
    folder.mkdir(parents=True, exist_ok=True)
    for sub in FOLDER_SUBDIRS:
        (folder / sub).mkdir(parents=True, exist_ok=True)
    facts = folder / JOB_FACTS_NAME
    if not facts.is_file():
        facts.write_text(
            f"# {slug}\n\nShared folder record. Attachments live in JOB-RECORD.json.\n",
            encoding="utf-8",
        )
    record = read_job_record(slug, jobs_root_path=jobs_root_path)
    record["slug"] = slug
    record["kind"] = folder_kind_for_slug(slug)
    record["intake_id"] = None
    record["quote_id"] = None
    record["quote_number"] = None
    record["lead_id"] = None
    record["owner"] = "founder"
    digest = str(attachment.get("sha256") or "") or (_sha256(content) if content else "")
    entry = {
        "filename": attachment.get("filename") or "",
        "filed_path": attachment.get("filed_path") or "",
        "media_type": attachment.get("media_type") or "",
        "wa_message_id": attachment.get("wa_message_id") or "",
        "whatsapp_attachment_id": attachment.get("whatsapp_attachment_id")
        or attachment.get("id")
        or "",
        "sha256": digest,
        "folder_kind": record["kind"],
    }
    existing = list(record.get("attachments") or [])
    seen_path = {a.get("filed_path") for a in existing if isinstance(a, dict) and a.get("filed_path")}
    seen_id = {
        str(a.get("whatsapp_attachment_id"))
        for a in existing
        if isinstance(a, dict) and a.get("whatsapp_attachment_id")
    }
    duplicate = (entry["filed_path"] and entry["filed_path"] in seen_path) or (
        entry["whatsapp_attachment_id"] and str(entry["whatsapp_attachment_id"]) in seen_id
    )
    if not duplicate:
        existing.append(entry)
    record["attachments"] = existing
    record["updated_at"] = datetime.now(timezone.utc).isoformat()
    dest = job_record_path(slug, jobs_root_path=jobs_root_path)
    dest.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record
