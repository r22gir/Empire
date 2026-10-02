"""Facts for a family instance, each flagged public or confidential.

Interview items default to confidential. Seed facts that the file marks
as public stay public until the owner changes them. Content paths must
call ``guard_public_text`` and ``public_facts_block``.
"""
from __future__ import annotations

import json
import uuid
from typing import Optional

from app.edition import assert_under_root, require_data_root

PUBLIC = "public"
CONFIDENTIAL = "confidential"


def _path():
    path = require_data_root() / "facts.json"
    return assert_under_root(path)


def _load() -> list[dict]:
    path = _path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = data.get("facts") or []
    return [row for row in data if isinstance(row, dict)]


def _save(facts: list[dict]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"facts": facts}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _visibility(value: Optional[str], default: str = CONFIDENTIAL) -> str:
    raw = (value or "").strip().lower()
    if raw in {PUBLIC, "publicar"}:
        return PUBLIC
    if raw in {CONFIDENTIAL, "confidencial"}:
        return CONFIDENTIAL
    return default


def list_facts() -> list[dict]:
    return _load()


def delete_facts(keys) -> None:
    wanted = {str(key) for key in keys or []}
    if not wanted:
        return
    _save([row for row in _load() if row.get("key") not in wanted])


def delete_facts_by_source(source: str) -> None:
    source = (source or "").strip()
    if not source:
        return
    _save([row for row in _load() if row.get("source") != source])


def public_facts() -> list[dict]:
    return [row for row in _load() if row.get("visibility") == PUBLIC]


def upsert_fact(
    *,
    key: str,
    text: str,
    value: str = "",
    visibility: str = CONFIDENTIAL,
    source: str = "interview",
    label: str = "",
) -> dict:
    key = (key or "").strip()[:80]
    if not key:
        raise ValueError("El dato necesita una clave")
    facts = _load()
    found = None
    for row in facts:
        if row.get("key") == key:
            found = row
            break
    if found is None:
        found = {"id": str(uuid.uuid4()), "key": key}
        facts.append(found)
    found["text"] = (text or "").strip()[:2000]
    found["value"] = (value or "").strip()[:500]
    found["label"] = (label or found.get("label") or key)[:160]
    found["source"] = (source or "interview")[:40]
    found["visibility"] = _visibility(visibility, CONFIDENTIAL)
    _save(facts)
    return found


def set_visibilities(items: list[dict]) -> list[dict]:
    updated = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        if not key:
            continue
        current = next((row for row in _load() if row.get("key") == key), None)
        text = str(item.get("text") or (current or {}).get("text") or "")
        value = str(item.get("value") or (current or {}).get("value") or "")
        label = str(item.get("label") or (current or {}).get("label") or key)
        source = str(item.get("source") or (current or {}).get("source") or "confirm")
        updated.append(
            upsert_fact(
                key=key,
                text=text or f"{label}: {value}",
                value=value,
                label=label,
                source=source,
                visibility=_visibility(item.get("visibility"), CONFIDENTIAL),
            )
        )
    return updated


def confirm_items_for_answers(answers: Optional[dict]) -> list[dict]:
    """Items the owner can mark. Missing flags stay confidential."""
    answers = answers if isinstance(answers, dict) else {}
    flags = answers.get("fact_visibility") if isinstance(answers.get("fact_visibility"), dict) else {}
    rows: list[dict] = []
    seen = set()

    def add(key: str, label: str, value) -> None:
        text_value = "" if value is None else str(value).strip()
        if not text_value or key in seen:
            return
        seen.add(key)
        rows.append({
            "key": key,
            "label": label,
            "value": text_value,
            "text": f"{label}: {text_value}",
            "visibility": _visibility(flags.get(key), CONFIDENTIAL),
            "source": "interview",
        })

    add("legal_name", "Nombre legal", answers.get("legal_name"))
    add("trade_name", "Nombre comercial", answers.get("trade_name"))
    add("city", "Ciudad", answers.get("city"))
    add("email", "Correo", answers.get("email"))
    add("phone", "Teléfono", answers.get("phone"))
    add("website", "Sitio web", answers.get("website"))
    add("tax_id", "NIT", answers.get("tax_id"))
    add("industry_description", "Actividad", answers.get("industry_description"))
    add("customer_who", "Clientes", answers.get("customer_who"))
    customer = answers.get("first_customer") if isinstance(answers.get("first_customer"), dict) else {}
    add("first_customer", "Primer cliente", customer.get("name"))
    for item in answers.get("items") or []:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        price = item.get("price")
        if price is None or price == "":
            continue
        add(f"price:{item['name']}", f"Precio de {item['name']}", price)
    for fact in _load():
        key = str(fact.get("key") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append({
            "key": key,
            "label": fact.get("label") or key,
            "value": fact.get("value") or "",
            "text": fact.get("text") or "",
            "visibility": _visibility(flags.get(key), fact.get("visibility") or CONFIDENTIAL),
            "source": fact.get("source") or "seed",
        })
    return rows


def persist_interview_facts(answers: Optional[dict]) -> list[dict]:
    saved = []
    for item in confirm_items_for_answers(answers):
        if item.get("source") != "interview":
            # Seed rows keep their stored visibility unless the interview set one.
            flags = (answers or {}).get("fact_visibility") if isinstance((answers or {}).get("fact_visibility"), dict) else {}
            if item["key"] not in flags:
                continue
        saved.append(
            upsert_fact(
                key=item["key"],
                text=item["text"],
                value=item["value"],
                label=item["label"],
                source=item.get("source") or "interview",
                visibility=item["visibility"],
            )
        )
    return saved


def public_facts_block() -> str:
    lines = []
    for fact in public_facts():
        text = (fact.get("text") or "").strip()
        if text:
            lines.append(f"- {text}")
    if not lines:
        return ""
    return "Hechos públicos (únicos que pueden salir en contenido):\n" + "\n".join(lines)


def guard_public_text(text: str) -> str:
    """Strip confidential values from anything that might be published."""
    if not text:
        return text or ""
    cleaned = text
    for fact in _load():
        if fact.get("visibility") == PUBLIC:
            continue
        value = (fact.get("value") or "").strip()
        if len(value) < 3:
            continue
        if value in cleaned:
            cleaned = cleaned.replace(value, "[confidencial]")
    return cleaned


def contains_confidential(text: str) -> bool:
    if not text:
        return False
    for fact in _load():
        if fact.get("visibility") == PUBLIC:
            continue
        value = (fact.get("value") or "").strip()
        if len(value) >= 3 and value in text:
            return True
    return False
