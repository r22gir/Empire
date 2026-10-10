"""Phase 0 WhatsApp folders: client job, or personal / insurance / store / luxeforge.

Every fileable batch is filed under this edition's jobs root. Reserved
folders never create a LuxeForge job, lead, or estimate. The shared
record is JOB-RECORD.json next to JOB-FACTS.md so Max, the job board,
and the chat log can read the same attachments later.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.services.max.doc_lookup import add_client_alias, jobs_root, probe_job_text, slugify

logger = logging.getLogger("max.whatsapp_folders")

RESERVED_FOLDER_SLUGS = ("personal", "insurance", "store", "luxeforge")
# Exact reserved words only. shop / claim / private / showroom are not
# aliases — a unique client name ("Emma's store order") must win.
RESERVED_FOLDER_ALIASES: dict[str, tuple[str, ...]] = {
    "personal": ("personal",),
    "insurance": ("insurance",),
    "store": ("store",),
    "luxeforge": ("luxeforge", "luxe forge", "luxe-forge"),
}
FOLDER_SUBDIRS = ("photos", "received", "scans")
JOB_RECORD_NAME = "JOB-RECORD.json"
JOB_FACTS_NAME = "JOB-FACTS.md"
SAFE_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,119}$")
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
NEW_JOB_RE = re.compile(
    r"\b(?:new\s+job|nuevo\s+trabajo|new\s+client)\s*[:\-]?\s+"
    r"(.+?)"
    r"(?=\s+(?:new\s+job|nuevo\s+trabajo|new\s+client)\b|[.!?]|$)",
    re.IGNORECASE | re.DOTALL,
)
PURCHASE_RE = re.compile(
    r"\b(?:need to buy|have to buy|want to buy|buy a|buying a|bought a|"
    r"purchase|need a case|buy (?:this|that|it))\b",
    re.IGNORECASE,
)

_record_lock = threading.RLock()
_just_created_slugs: set[str] = set()


class UnsafeJobSlug(ValueError):
    """Slug is not a single safe path segment under the jobs root."""


def edition_owner_label() -> str:
    """Owner written on JOB-RECORD.json. Family editions are not 'founder'."""
    for key in ("WHATSAPP_EDITION_OWNER", "EMPIRE_OWNER_LABEL"):
        val = (os.getenv(key) or "").strip()
        if val:
            return val
    raw = (os.getenv("EMPIRE_DATA_DIR") or "").strip()
    name = Path(raw).name.lower() if raw else ""
    if name in {"amp", "max_e", "max-e", "maxe"}:
        return "Max-e"
    if name == "maxine":
        return "Maxine"
    return "founder"


def safe_folder_slug(slug: str, *, jobs_root_path: Optional[Path | str] = None) -> str:
    """Return one safe path segment that resolves under this edition's jobs root.

    Rejects empty values, '.', '..', absolute paths, separators, and any
    slug whose resolved path is not a direct child of the jobs root.
    """
    raw = (slug or "").strip()
    if not raw:
        raise UnsafeJobSlug("empty job slug")
    if raw.startswith("/") or raw.startswith("\\"):
        raise UnsafeJobSlug("absolute path is not a job slug")
    if len(raw) >= 2 and raw[1] == ":":
        raise UnsafeJobSlug("absolute path is not a job slug")
    if "/" in raw or "\\" in raw or ".." in raw or raw in {".", ".."}:
        raise UnsafeJobSlug("slug must be a single path segment")
    cleaned = raw.lower()
    if not SAFE_SLUG_RE.match(cleaned):
        raise UnsafeJobSlug("slug is not a single safe path segment")
    root = jobs_root(jobs_root_path).resolve()
    try:
        candidate = (root / cleaned).resolve()
    except (OSError, RuntimeError) as exc:
        raise UnsafeJobSlug("slug does not resolve under the jobs root") from exc
    if candidate.parent != root:
        raise UnsafeJobSlug("resolved path is not under the jobs root")
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise UnsafeJobSlug("resolved path is not under the jobs root") from exc
    return cleaned


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
    """Unique client name beats a reserved word. Never guesses.

    'Emma's store order' → Emma's job. 'for the store' → store.
    shop / claim / private / showroom are not reserved aliases.
    """
    ensure_reserved_folders()
    probed = probe_job_text(text)
    if probed.get("status") == "unique" and probed.get("match"):
        match = dict(probed["match"])
        slug = str(match.get("slug") or "")
        kind = folder_kind_for_slug(slug)
        if kind == "client":
            match["kind"] = "client"
            match["created"] = False
            return match
    reserved = match_reserved_folder(text)
    if reserved:
        reserved["created"] = False
        return reserved
    return None


def parse_new_job_name(text: str) -> Optional[str]:
    """'New job home wood suites.' / 'nuevo trabajo X' / 'new client X' → the name."""
    match = NEW_JOB_RE.search(str(text or ""))
    if not match:
        return None
    raw = re.sub(r"[\s.!?]+$", "", match.group(1).strip())
    raw = re.sub(
        r"\b(?:new\s+job|nuevo\s+trabajo|new\s+client)\b",
        " ",
        raw,
        flags=re.IGNORECASE,
    )
    raw = re.sub(r"\s+", " ", raw).strip(" -:;,'\"")
    if not raw:
        return None
    if folder_kind_for_slug(slugify(raw)) != "client":
        return None
    if not slugify(raw):
        return None
    return raw


def title_job_name(name: str) -> str:
    cleaned = re.sub(r"[\s.!?]+$", "", (name or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        return ""
    if cleaned == cleaned.lower() or cleaned == cleaned.upper():
        return cleaned.title()
    return cleaned


def sounds_like_purchase(text: str) -> bool:
    return bool(PURCHASE_RE.search(str(text or "")))


def create_client_job_folder(
    name: str,
    *,
    jobs_root_path: Optional[Path | str] = None,
) -> dict[str, Any]:
    """Create <jobs-root>/<slug> + JOB-FACTS / JOB-RECORD stubs + alias. No LF/quote/lead."""
    title = title_job_name(name)
    slug = safe_folder_slug(slugify(title), jobs_root_path=jobs_root_path)
    if folder_kind_for_slug(slug) != "client":
        raise UnsafeJobSlug("reserved folder is not a new client job")
    root = jobs_root(jobs_root_path)
    folder = root / slug
    existed = folder.is_dir() and (folder / JOB_RECORD_NAME).is_file()
    folder.mkdir(parents=True, exist_ok=True)
    for sub in FOLDER_SUBDIRS:
        (folder / sub).mkdir(parents=True, exist_ok=True)
    facts = folder / JOB_FACTS_NAME
    if not facts.is_file():
        facts.write_text(
            f"# {title}\n\nShared folder record. Attachments live in JOB-RECORD.json.\n",
            encoding="utf-8",
        )
    if not (folder / JOB_RECORD_NAME).is_file():
        record = empty_job_record(slug, jobs_root_path=jobs_root_path)
        record["slug"] = slug
        _atomic_write_text(
            folder / JOB_RECORD_NAME,
            json.dumps(record, indent=2, sort_keys=True) + "\n",
        )
    add_client_alias(title, slug, aliases=[title, name.strip()])
    if not existed:
        _just_created_slugs.add(slug)
    return {
        "slug": slug,
        "client_name": title,
        "folder_path": str(folder),
        "kind": "client",
        "created": not existed or slug in _just_created_slugs,
        "match_reason": "new job" if not existed else "existing folder",
    }


def consume_created_job_flag(slug: str) -> bool:
    """True once after create_client_job_folder, then cleared (for the ack line)."""
    if slug in _just_created_slugs:
        _just_created_slugs.discard(slug)
        return True
    return False


def resolve_or_create_folder(text: str) -> Optional[dict[str, Any]]:
    """Unique existing job, reserved folder, or 'new job <name>' create. Never guesses."""
    named = parse_new_job_name(text)
    if named:
        probed = probe_job_text(named)
        if probed.get("status") == "unique" and probed.get("match"):
            match = dict(probed["match"])
            if folder_kind_for_slug(str(match.get("slug") or "")) == "client":
                match["kind"] = "client"
                match["created"] = False
                return match
        if probed.get("status") == "ambiguous":
            return None
        created = create_client_job_folder(named)
        created["created"] = True
        return created
    match = resolve_folder(text)
    if match and match.get("slug") in _just_created_slugs:
        match["created"] = True
    return match


def is_scan_file(filename: str = "", mime_type: str = "", media_type: str = "") -> bool:
    if (media_type or "").lower() in {"scan", "model", "stl", "polycam"}:
        return True
    name = Path(filename or "").name.lower()
    ext = Path(name).suffix.lower()
    if ext in SCAN_EXTENSIONS:
        return True
    # Polycam room exports arrive as .zip (OBJ/GLTF bundle), not USDZ.
    if ext == ".zip" and "polycam" in name:
        return True
    mime = (mime_type or "").split(";")[0].strip().lower()
    if mime in {"application/zip", "application/x-zip-compressed"} and "polycam" in name:
        return True
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
    clean = safe_folder_slug(slug, jobs_root_path=jobs_root_path)
    return jobs_root(jobs_root_path) / clean / JOB_RECORD_NAME


def _quarantine_corrupt_record(path: Path) -> Optional[Path]:
    """Move a bad JOB-RECORD.json aside. Never overwrite it in place."""
    if not path.is_file():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    dest = path.with_name(f"{path.name}.corrupt-{stamp}")
    n = 0
    while dest.exists():
        n += 1
        dest = path.with_name(f"{path.name}.corrupt-{stamp}-{n}")
    try:
        os.replace(path, dest)
        logger.warning("quarantined corrupt job record %s -> %s", path, dest)
        return dest
    except OSError:
        try:
            dest.write_bytes(path.read_bytes())
            logger.warning("copied corrupt job record %s -> %s", path, dest)
            return dest
        except OSError as exc:
            logger.error("could not quarantine corrupt job record %s: %s", path, exc)
            return None


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".job-record-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _read_job_record_unlocked(
    slug: str, *, jobs_root_path: Optional[Path | str] = None
) -> dict[str, Any]:
    path = job_record_path(slug, jobs_root_path=jobs_root_path)
    if not path.is_file():
        return empty_job_record(slug, jobs_root_path=jobs_root_path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        _quarantine_corrupt_record(path)
        return empty_job_record(slug, jobs_root_path=jobs_root_path)
    if not isinstance(data, dict):
        _quarantine_corrupt_record(path)
        return empty_job_record(slug, jobs_root_path=jobs_root_path)
    return data


def read_job_record(slug: str, *, jobs_root_path: Optional[Path | str] = None) -> dict[str, Any]:
    clean = safe_folder_slug(slug, jobs_root_path=jobs_root_path)
    with _record_lock:
        return _read_job_record_unlocked(clean, jobs_root_path=jobs_root_path)


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
        "owner": edition_owner_label(),
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
    """Append one filed file to JOB-RECORD.json. Never writes intake/quote/lead ids.

    Slug is validated here (not only in callers). The read-modify-write is
    locked and the file is replaced atomically so two photos in one batch
    cannot drop an entry. A corrupt record is quarantined, then a fresh
    record is started.
    """
    slug = safe_folder_slug(slug, jobs_root_path=jobs_root_path)
    with _record_lock:
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
        record = _read_job_record_unlocked(slug, jobs_root_path=jobs_root_path)
        record["slug"] = slug
        record["kind"] = folder_kind_for_slug(slug)
        record["intake_id"] = None
        record["quote_id"] = None
        record["quote_number"] = None
        record["lead_id"] = None
        record["owner"] = edition_owner_label()
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
        seen_path = {
            a.get("filed_path") for a in existing if isinstance(a, dict) and a.get("filed_path")
        }
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
        _atomic_write_text(dest, json.dumps(record, indent=2, sort_keys=True) + "\n")
        return record
