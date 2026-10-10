"""Resolve client names, nicknames, addresses, and quote numbers to job slugs.

Used by WhatsApp filing and the Final Docs hub. If more than one client
matches, return ambiguous — callers must not guess.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Optional


def _config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "client_aliases.json"


def jobs_root(override: Optional[Path | str] = None) -> Path:
    if override:
        return Path(override)
    env = (os.getenv("WHATSAPP_JOBS_ROOT") or "").strip()
    if env:
        return Path(env)
    return Path(os.path.expanduser("~/jobs"))


def load_client_aliases() -> dict[str, Any]:
    path = _config_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def normalize_term(term: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", (term or "").lower()).strip()
    return re.sub(r"\s+", " ", cleaned)


def slugify(name: str) -> str:
    s = re.sub(r"[^\w\s-]", "", (name or "").lower()).strip()
    return re.sub(r"[-\s]+", "-", s)


def _clients() -> list[dict[str, Any]]:
    data = load_client_aliases()
    clients = list(data.get("clients") or [])
    if isinstance(data, dict) and not clients:
        for key, value in data.items():
            if key == "clients":
                continue
            if isinstance(value, dict):
                clients.append(value)
            elif isinstance(value, str):
                clients.append({"slug": value, "name": str(key).title(), "aliases": [key]})
    return [c for c in clients if isinstance(c, dict)]


def _quote_customer(raw_text: str, base_dir: Path) -> Optional[dict[str, Any]]:
    quote_match = re.search(r"\b(est[-_\s]?\d+|q[-_\s]?\d+)\b", raw_text, re.IGNORECASE)
    if not quote_match:
        return None
    q_code = quote_match.group(1).upper().replace(" ", "-").replace("_", "-")
    try:
        from app.db.database import get_db

        with get_db() as conn:
            row = conn.execute(
                "SELECT customer_name, project_name FROM quotes_v2 "
                "WHERE upper(quote_number) = ? OR id = ? LIMIT 1",
                (q_code, q_code),
            ).fetchone()
        if row and row[0]:
            c_name = row[0]
            return {
                "slug": slugify(c_name),
                "client_name": c_name,
                "folder_path": str(base_dir / slugify(c_name)),
                "match_reason": f"quote {q_code}",
            }
    except Exception:
        return None
    return None


def probe_job_text(
    text: str,
    *,
    jobs_root_path: Optional[Path | str] = None,
) -> dict[str, Any]:
    """Classify text as empty, unique, ambiguous, or unknown. Never guesses."""
    if not text or not str(text).strip():
        return {"status": "empty", "matches": []}

    raw_text = str(text).strip()
    norm_text = normalize_term(raw_text)
    base_dir = jobs_root(jobs_root_path)

    quoted = _quote_customer(raw_text, base_dir)
    if quoted:
        return {"status": "unique", "match": quoted, "matches": [quoted]}

    matches: list[dict[str, Any]] = []
    for client in _clients():
        c_slug = client.get("slug") or slugify(client.get("name", ""))
        c_name = client.get("name") or c_slug
        terms = [c_slug, str(c_name).lower()] + [str(a).lower() for a in client.get("aliases") or []]
        for term in terms:
            norm_term = normalize_term(term)
            if norm_term and re.search(r"\b" + re.escape(norm_term) + r"\b", norm_text):
                matches.append({
                    "slug": c_slug,
                    "client_name": c_name,
                    "folder_path": str(base_dir / c_slug),
                    "match_reason": f"matched term '{norm_term}'",
                })
                break

    if len(matches) == 1:
        return {"status": "unique", "match": matches[0], "matches": matches}
    if len(matches) > 1:
        return {"status": "ambiguous", "matches": matches}

    dir_matches: list[dict[str, Any]] = []
    if base_dir.is_dir():
        try:
            for entry in base_dir.iterdir():
                if not entry.is_dir() or entry.name.startswith("."):
                    continue
                words = entry.name.lower().replace("-", " ").replace("_", " ")
                if entry.name.lower() in norm_text or words in norm_text:
                    dir_matches.append({
                        "slug": entry.name,
                        "client_name": entry.name.replace("-", " ").title(),
                        "folder_path": str(entry),
                        "match_reason": f"matched folder {entry.name}",
                    })
        except OSError:
            pass
    if len(dir_matches) == 1:
        return {"status": "unique", "match": dir_matches[0], "matches": dir_matches}
    if len(dir_matches) > 1:
        return {"status": "ambiguous", "matches": dir_matches}
    return {"status": "unknown", "matches": []}


def resolve_job_folder(
    text: str,
    *,
    jobs_root_path: Optional[Path | str] = None,
) -> Optional[dict[str, Any]]:
    """Unique match only. None if empty, unknown, or ambiguous."""
    probed = probe_job_text(text, jobs_root_path=jobs_root_path)
    if probed.get("status") == "unique":
        return probed.get("match")
    return None


def list_job_folders(*, jobs_root_path: Optional[Path | str] = None) -> list[dict[str, str]]:
    """Job slugs from aliases plus directories under the jobs root."""
    base_dir = jobs_root(jobs_root_path)
    found: dict[str, dict[str, str]] = {}
    for client in _clients():
        slug = str(client.get("slug") or slugify(client.get("name", "")))
        if slug:
            found[slug] = {
                "slug": slug,
                "client_name": str(client.get("name") or slug),
                "folder_path": str(base_dir / slug),
            }
    if base_dir.is_dir():
        try:
            for entry in base_dir.iterdir():
                if entry.is_dir() and not entry.name.startswith("."):
                    found.setdefault(entry.name, {
                        "slug": entry.name,
                        "client_name": entry.name.replace("-", " ").title(),
                        "folder_path": str(entry),
                    })
        except OSError:
            pass
    return sorted(found.values(), key=lambda row: row["slug"])
