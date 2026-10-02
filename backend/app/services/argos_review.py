"""Argos Campestre import for Maxine.

Camilo chooses in the interview. "Sí, cargar todo" creates one task for the
owner, Rafael, and a review queue. Items stay out of facts until Camilo
marks Publicar or Confidencial. "Solo lo público" keeps the public seed
and does not open the import. No legal entity or NIT is preloaded.
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Optional

from app.edition import assert_under_root, is_maxine, require_data_root

TASK_TITLE = "Importación Argos pendiente"
TASK_DESCRIPTION = (
    "Rafael carga los correos y archivos 2021–2024 y los planos de Argos Campestre "
    "para revisarlos con Camilo. No incluye datos legales de la sociedad ni un NIT. "
    "Cada pieza entra a la cola de revisión como Confidencial y no se usa ni se muestra "
    "hasta que Camilo la apruebe."
)


def _path():
    return assert_under_root(require_data_root() / "argos_review.json")


def _owner_email() -> str:
    return os.getenv("AMP_OWNER_EMAIL", "").strip().lower()


def _empty() -> dict:
    return {"active": False, "task": None, "items": []}


def _load() -> dict:
    path = _path()
    if not path.is_file():
        return _empty()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _empty()
    if not isinstance(data, dict):
        return _empty()
    items = data.get("items") if isinstance(data.get("items"), list) else []
    task = data.get("task") if isinstance(data.get("task"), dict) else None
    return {"active": bool(data.get("active")), "task": task, "items": items}


def _save(data: dict) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _drop_argos_facts() -> None:
    from app.services.edition_facts import delete_facts, delete_facts_by_source

    delete_facts({"argos:lugar", "argos:planos", "argos:marca"})
    delete_facts_by_source("argos")


def review_state() -> dict:
    """Queue Camilo can see. Pending items are not facts."""
    if not is_maxine():
        return _empty()
    return _load()


def sync_argos_consent(answers: Optional[dict]) -> dict:
    """Store the interview answer as a task plus a queue, or clear that import."""
    if not is_maxine():
        return _empty()
    answers = answers if isinstance(answers, dict) else {}
    choice = (answers.get("argos_consent") or "").strip().lower()
    if choice != "all":
        _drop_argos_facts()
        _save(_empty())
        return _empty()
    current = _load()
    task = current.get("task") if isinstance(current.get("task"), dict) else None
    if not task or task.get("title") != TASK_TITLE:
        task = {
            "id": uuid.uuid4().hex[:12],
            "title": TASK_TITLE,
            "description": TASK_DESCRIPTION,
            "status": "todo",
            "assigned_to": _owner_email(),
            "owner_name": "Rafael",
        }
    else:
        task["description"] = TASK_DESCRIPTION
        task["status"] = "todo"
        task["assigned_to"] = _owner_email()
        task["owner_name"] = "Rafael"
    data = {"active": True, "task": task, "items": current.get("items") or []}
    _save(data)
    return data


def enqueue_item(*, title: str, text: str) -> dict:
    """Stage one imported piece. It is not a fact until Camilo decides."""
    if not is_maxine():
        raise RuntimeError("La cola de Argos solo existe en Maxine")
    data = _load()
    if not data.get("active") or not data.get("task"):
        raise RuntimeError("No hay una importación de Argos pendiente")
    title = (title or "").strip()
    text = (text or "").strip()
    if not title or not text:
        raise ValueError("La pieza necesita título y texto")
    item = {
        "id": uuid.uuid4().hex[:12],
        "title": title[:200],
        "text": text[:2000],
        "visibility": "confidential",
        "status": "pending",
        "source": "argos",
    }
    data["items"] = list(data.get("items") or []) + [item]
    _save(data)
    return item


def decide_item(item_id: str, visibility: str) -> dict:
    """Publicar or Confidencial. Only this writes a fact."""
    if not is_maxine():
        raise RuntimeError("La cola de Argos solo existe en Maxine")
    choice = (visibility or "").strip().lower()
    if choice not in {"public", "confidential", "publicar", "confidencial"}:
        raise ValueError("Elige Publicar o Confidencial")
    stored = "public" if choice in {"public", "publicar"} else "confidential"
    data = _load()
    found = None
    for item in data.get("items") or []:
        if isinstance(item, dict) and item.get("id") == item_id:
            found = item
            break
    if found is None:
        raise ValueError("Esa pieza no está en la cola")
    from app.services.edition_facts import upsert_fact

    fact = upsert_fact(
        key=f"argos:{item_id}"[:80],
        text=found.get("text") or "",
        value=(found.get("text") or "")[:500],
        label=(found.get("title") or "Argos Campestre")[:160],
        visibility=stored,
        source="argos",
    )
    found["status"] = "approved"
    found["visibility"] = stored
    _save(data)
    return {"item": found, "fact": {"key": fact["key"], "visibility": fact["visibility"]}}
