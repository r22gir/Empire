"""Resolve chat uploads across edition dirs, categories, and encoded names.

Juan's Max-e PDFs 404'd because the chat UI always opened
``/files/view/images/<name>`` while ``/files/upload`` stores PDFs under
``documents/``, and because spaces / parentheses / accents in the
filename were not decoded or Unicode-normalized on lookup.

Family editions stay on EMPIRE_DATA_DIR. Tests must use a temp root —
never live /data.
"""
from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import unquote, unquote_plus

UPLOAD_CATEGORIES = ("images", "documents", "audio", "other", "code")

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".bmp", ".heic", ".heif"}
_DOC_EXTS = {".pdf", ".txt", ".md", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".json"}
_CODE_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".sh", ".yaml", ".yml"}
_AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".ogg", ".flac", ".wma", ".aac"}


def category_for_filename(filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext in _DOC_EXTS:
        return "documents"
    if ext in _CODE_EXTS:
        return "code"
    if ext in _IMAGE_EXTS:
        return "images"
    if ext in _AUDIO_EXTS:
        return "audio"
    return "other"


def decode_stored_name(raw: str) -> str:
    """Strip path bits and undo %20 / + / UTF-8 percent-encoding."""
    name = Path(raw or "").name
    if not name:
        return ""
    for decoder in (unquote, unquote_plus):
        try:
            decoded = decoder(name)
        except Exception:
            continue
        if decoded:
            name = decoded
    return name


def filename_variants(raw: str) -> list[str]:
    """NFC + NFD forms so macOS-composed accents still match Linux storage."""
    seen: set[str] = set()
    out: list[str] = []
    base = decode_stored_name(raw)
    raw_name = Path(raw or "").name
    for candidate in (base, raw_name):
        if not candidate:
            continue
        for form in ("NFC", "NFD"):
            try:
                normalized = unicodedata.normalize(form, candidate)
            except Exception:
                normalized = candidate
            if normalized and normalized not in seen:
                seen.add(normalized)
                out.append(normalized)
    return out


def upload_search_roots() -> list[Path]:
    """Edition uploads first. Optional per-user trees under uploads/users/."""
    roots: list[Path] = []
    try:
        from app.edition import is_family_edition, require_data_root

        if is_family_edition():
            root = require_data_root() / "uploads"
            roots.append(root)
            users = root / "users"
            if users.is_dir():
                roots.extend(sorted(p for p in users.iterdir() if p.is_dir()))
            return roots
    except Exception:
        pass
    try:
        from app.services.data_paths import data_root

        roots.append(data_root() / "uploads")
    except Exception:
        pass
    return roots


def _existing_file(path: Path) -> Optional[Path]:
    try:
        if path.is_file():
            return path
    except OSError:
        return None
    return None


def resolve_uploaded_file(
    filename: str,
    category: Optional[str] = None,
    *,
    roots: Optional[Iterable[Path]] = None,
) -> Optional[Path]:
    """Find an uploaded chat file by display name.

    Tries the hinted category, then every category, then the uploads
    root itself. Filename lookup is encoding- and Unicode-tolerant.
    """
    names = filename_variants(filename)
    if not names:
        return None
    search_roots = list(roots) if roots is not None else upload_search_roots()
    hinted = (category or "").strip().lower()
    if hinted in {"list", "logs", "browse", "upload", "upload-from-path", "delete", "view"}:
        hinted = ""
    cats: list[str] = []
    if hinted and hinted in UPLOAD_CATEGORIES:
        cats.append(hinted)
    inferred = category_for_filename(names[0])
    if inferred not in cats:
        cats.append(inferred)
    for cat in UPLOAD_CATEGORIES:
        if cat not in cats:
            cats.append(cat)

    for root in search_roots:
        if root is None:
            continue
        for name in names:
            for cat in cats:
                found = _existing_file(Path(root) / cat / name)
                if found is not None:
                    return found
            found = _existing_file(Path(root) / name)
            if found is not None:
                return found
    return None
