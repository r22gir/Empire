"""First-login welcome deck for family editions (Max-e / Maxine).

Seen flags live under that instance's EMPIRE_DATA_DIR / welcome / seen.json.
Workroom and the founder Max process never read or write this store.
Amp and Maxine cannot see each other's users.
"""
from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.edition import (
    EditionPathError,
    assert_under_root,
    assistant_name,
    edition_name,
    is_family_edition,
    require_data_root,
)

DECK_VERSION = 1
DEFAULT_INTERVAL_MS = 8000
MIN_INTERVAL_MS = 3000
MAX_INTERVAL_MS = 30_000
MAX_SLIDES = 20
WELCOME_REPLAY_LABEL = "Ver bienvenida"

# Words / company-legal leftovers that must not appear in the default deck.
_LEAK_RE = re.compile(
    r"\b(nit|rut|sas|llc|s\.a\.s|escritura|cámara de comercio|argos campestre|"
    r"workroom|studio\.empirebox|/data/images|founder pin|empirebox2026)\b",
    re.I,
)

_lock = threading.Lock()

_DEFAULT_SLIDES = (
    {
        "id": "hola",
        "title": "Hola, soy {assistant}",
        "body": (
            "Bienvenido a la familia. Este centro de mando es tuyo: privado, "
            "en español y separado del de tus hermanos."
        ),
    },
    {
        "id": "empirebox",
        "title": "EmpireBox, en breve",
        "body": (
            "Rafael y sus hermanos están construyendo EmpireBox juntos. "
            "Cada uno tiene su propio asistente y su propio espacio. "
            "Aquí no hay papeles de empresa: solo la herramienta para "
            "trabajar y organizarte."
        ),
    },
    {
        "id": "asistente",
        "title": "Lo que hago por ti",
        "body": (
            "Hablo contigo por chat o por voz, recuerdo lo que me pides guardar, "
            "busco en la web cuando hace falta y te ayudo a redactar y organizar. "
            "No publico nada ni toco tus cuentas sin que tú lo apruebes."
        ),
    },
    {
        "id": "uso",
        "title": "Cómo usarlo",
        "body": (
            "Entras con tu correo. Escribes en el chat, usas voz, adjuntas "
            "archivos y pides una búsqueda web. Recuerdo lo que me pides guardar. "
            "Si necesitas a Rafael, usa el botón Pedir ayuda a Max."
        ),
    },
    {
        "id": "reglas",
        "title": "Reglas de esta edición",
        "body": (
            "Tus datos viven solo aquí; no se mezclan con las ediciones de tus "
            "hermanos. Nada se publica sin tu aprobación. El uso de esta "
            "instancia está limitado al 20% del total."
        ),
    },
    {
        "id": "pasos",
        "title": "Primeros pasos",
        "body": (
            "Prueba el chat, dile algo que deba recordar y abre Ayuda si quieres "
            "voz o WhatsApp. Puedes volver a ver esta bienvenida cuando quieras: "
            "Ayuda → Ver bienvenida."
        ),
    },
)


def _norm_email(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def seed_path(edition: Optional[str] = None) -> Path:
    name = (edition or edition_name()).strip().lower() or "amp"
    return _repo_root() / "deploy" / "seeds" / f"{name}-welcome.json"


def welcome_dir() -> Path:
    root = require_data_root()
    path = assert_under_root(root / "welcome", root)
    path.mkdir(parents=True, exist_ok=True)
    return path


def seen_path() -> Path:
    return assert_under_root(welcome_dir() / "seen.json")


def override_deck_path() -> Path:
    return assert_under_root(welcome_dir() / "slides.json")


def sanitize_image(raw: Any) -> Optional[str]:
    """Same-origin relative path only. Blocks //host and parent traversal."""
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    if not value.startswith("/") or value.startswith("//") or ".." in value:
        return None
    if "\\" in value or "\n" in value or "\r" in value:
        return None
    return value


def _clamp_interval(raw: Any) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_INTERVAL_MS
    return max(MIN_INTERVAL_MS, min(MAX_INTERVAL_MS, value))


def _clean_slide(raw: Any, index: int) -> Optional[dict]:
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title") or "").strip()
    body = str(raw.get("body") or "").strip()
    if not title or not body:
        return None
    slide_id = str(raw.get("id") or f"slide-{index + 1}").strip() or f"slide-{index + 1}"
    return {
        "id": slide_id[:64],
        "title": title[:200],
        "body": body[:2000],
        "image": sanitize_image(raw.get("image")),
    }


def _normalize_deck(raw: Any, *, edition: str, assistant: str) -> dict:
    data = raw if isinstance(raw, dict) else {}
    slides = []
    for index, item in enumerate(list(data.get("slides") or [])[:MAX_SLIDES]):
        slide = _clean_slide(item, index)
        if slide:
            slides.append(slide)
    if not slides:
        slides = default_slides(assistant)
    version = data.get("deck_version", DECK_VERSION)
    try:
        version = int(version)
    except (TypeError, ValueError):
        version = DECK_VERSION
    return {
        "edition": edition,
        "assistant": assistant,
        "deck_version": version,
        "interval_ms": _clamp_interval(data.get("interval_ms", DEFAULT_INTERVAL_MS)),
        "slides": slides,
    }


def default_slides(assistant: str) -> list[dict]:
    name = (assistant or "Max-e").strip() or "Max-e"
    slides = []
    for item in _DEFAULT_SLIDES:
        slides.append({
            "id": item["id"],
            "title": item["title"].format(assistant=name),
            "body": item["body"].format(assistant=name),
            "image": None,
        })
    return slides


def default_deck(edition: Optional[str] = None) -> dict:
    name = (edition or edition_name()).strip().lower() or "amp"
    if is_family_edition() and (edition is None or edition == edition_name()):
        assistant = assistant_name()
    else:
        assistant = "Maxine" if name == "maxine" else "Max-e"
    return {
        "edition": name,
        "assistant": assistant,
        "deck_version": DECK_VERSION,
        "interval_ms": DEFAULT_INTERVAL_MS,
        "slides": default_slides(assistant),
    }


def _read_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def load_deck() -> dict:
    """Per-edition deck. Override file, then deploy/seeds, then built-in copy."""
    if not is_family_edition():
        raise EditionPathError("La bienvenida solo aplica a las ediciones familiares")
    edition = edition_name()
    assistant = assistant_name()
    for path in (override_deck_path(), seed_path(edition)):
        loaded = _read_json(path)
        if loaded:
            return _normalize_deck(loaded, edition=edition, assistant=assistant)
    return default_deck(edition)


def _empty_seen(edition: str) -> dict:
    return {"edition": edition, "users": {}}


def _read_seen() -> dict:
    edition = edition_name()
    data = _read_json(seen_path()) or _empty_seen(edition)
    stored = str(data.get("edition") or "").strip().lower()
    if stored and stored != edition:
        return _empty_seen(edition)
    users = data.get("users")
    if not isinstance(users, dict):
        users = {}
    return {"edition": edition, "users": users}


def _write_seen(data: dict) -> None:
    path = seen_path()
    tmp = path.with_suffix(".json.tmp")
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)


def has_seen(email: str) -> bool:
    if not is_family_edition():
        return False
    key = _norm_email(email)
    if not key:
        return False
    with _lock:
        entry = _read_seen()["users"].get(key) or {}
    return bool(isinstance(entry, dict) and entry.get("seen"))


def mark_seen(email: str) -> dict:
    if not is_family_edition():
        raise EditionPathError("La bienvenida solo aplica a las ediciones familiares")
    key = _norm_email(email)
    if not key or "@" not in key:
        raise ValueError("Se requiere un correo autorizado")
    now = datetime.now(timezone.utc).isoformat()
    with _lock:
        data = _read_seen()
        entry = {
            "seen": True,
            "seen_at": now,
            "deck_version": DECK_VERSION,
        }
        data["users"][key] = entry
        data["edition"] = edition_name()
        _write_seen(data)
    return dict(entry)


def public_state(email: str) -> dict:
    """Current user's welcome payload. Never includes other users."""
    deck = load_deck()
    seen = has_seen(email)
    return {
        "edition": deck["edition"],
        "assistant": deck["assistant"],
        "show": not seen,
        "seen": seen,
        "interval_ms": deck["interval_ms"],
        "deck_version": deck["deck_version"],
        "slides": deck["slides"],
        "replay_label": WELCOME_REPLAY_LABEL,
    }


def deck_has_leak(deck: dict) -> list[str]:
    hits = []
    for slide in deck.get("slides") or []:
        blob = f"{slide.get('title') or ''} {slide.get('body') or ''}"
        found = _LEAK_RE.findall(blob)
        hits.extend(found)
    return hits
