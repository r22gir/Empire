"""Legal attachment slots.

Skeletons are empty placeholders. They are not Colombian legal clauses.
Company fields stay blank unless a fact was marked public.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

WATERMARK = "BORRADOR – requiere revisión de abogado"

LEGAL_SLOTS = (
    {"key": "acuerdo_separacion", "title": "Acuerdo de separación"},
    {"key": "promesa_compraventa", "title": "Promesa de compraventa"},
    {"key": "autorizacion_datos", "title": "Autorización de tratamiento de datos (Ley 1581)"},
    {"key": "pagare", "title": "Pagaré / carta de instrucciones"},
    {"key": "anexo_plan_pagos", "title": "Anexo plan de pagos"},
)

IT_LEGAL_SLOTS = (
    {"key": "nda", "title": "Acuerdo de confidencialidad"},
    {"key": "tratamiento_datos", "title": "Acuerdo de tratamiento de datos (Ley 1581 habeas data)"},
    {"key": "sla", "title": "Contrato de servicios / SLA"},
    {"key": "sow", "title": "Orden de trabajo"},
)

COMPANY_PLACEHOLDERS = {"empresa", "razon_social", "nit", "representante", "notaria"}

_FACT_TO_PLACEHOLDER = {
    "legal_name": "empresa",
    "trade_name": "empresa",
    "razon_social": "razon_social",
    "nit": "nit",
    "tax_id": "nit",
    "representante": "representante",
    "representante_legal": "representante",
    "notaria": "notaria",
    "notary": "notaria",
}

_PLACEHOLDER = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


def skeleton_body(title: str) -> str:
    return (
        f"{WATERMARK}\n\n"
        f"{title}\n\n"
        "Plantilla vacía. Aquí no hay cláusulas. "
        "Quien suba el documento y lo marque aprobado por abogado escribe el texto.\n\n"
        "Comprador: {{comprador}}\n"
        "Lote: {{lote}}\n"
        "Proyecto: {{proyecto}}\n"
        "Precio: {{precio}}\n"
        "Fecha: {{fecha}}\n"
        "Empresa: {{empresa}}\n"
        "NIT: {{nit}}\n"
        "Representante: {{representante}}\n"
        "Notaría: {{notaria}}\n\n"
        "{{contenido_abogado}}\n"
    )


def it_skeleton_body(title: str) -> str:
    return (
        f"{WATERMARK}\n\n"
        f"{title}\n\n"
        "Plantilla vacía. Aquí no hay cláusulas. "
        "Quien suba el documento y lo marque aprobado por abogado escribe el texto.\n\n"
        "Cliente: {{cliente}}\n"
        "Servicio: {{servicio}}\n"
        "Cobro: {{cobro}}\n"
        "Moneda: {{moneda}}\n"
        "Precio: {{precio}}\n"
        "Fecha: {{fecha}}\n"
        "Empresa: {{empresa}}\n"
        "NIT: {{nit}}\n"
        "Representante: {{representante}}\n\n"
        "{{contenido_abogado}}\n"
    )


def _all_slots() -> tuple:
    return LEGAL_SLOTS + IT_LEGAL_SLOTS


def public_company_values() -> dict:
    """Only facts Camilo marked Publicar. Anything else stays a placeholder."""
    try:
        from app.services.edition_facts import public_facts

        facts = public_facts()
    except Exception:
        return {}
    values: dict = {}
    ranked = {"trade_name": 1, "legal_name": 2}
    best = {}
    for fact in facts:
        if fact.get("visibility") != "public":
            continue
        key = fact.get("key") or ""
        target = _FACT_TO_PLACEHOLDER.get(key)
        if not target:
            continue
        text = (fact.get("value") or fact.get("text") or "").strip()
        if not text:
            continue
        rank = ranked.get(key, 1)
        if target not in best or rank >= best[target][0]:
            best[target] = (rank, text)
    for target, (_rank, text) in best.items():
        values[target] = text
    return values


def fill_placeholders(
    template: str,
    values: dict | None = None,
    public_company: dict | None = None,
    *,
    force_watermark: bool = True,
) -> str:
    company = public_company if public_company is not None else public_company_values()
    supplied = dict(values or {})

    def replace(match: re.Match) -> str:
        key = match.group(1).strip()
        if key in COMPANY_PLACEHOLDERS:
            if key in company and company[key]:
                return str(company[key])
            return "{{" + key + "}}"
        if key in supplied and supplied[key] not in (None, ""):
            return str(supplied[key])
        return "{{" + key + "}}"

    filled = _PLACEHOLDER.sub(replace, template or "")
    if force_watermark and WATERMARK not in filled:
        filled = f"{WATERMARK}\n\n{filled}"
    return filled


def _template_db():
    from app.routers.construction import get_db

    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cf_legal_templates (
            slot TEXT PRIMARY KEY,
            title TEXT,
            filename TEXT,
            body TEXT,
            stored_path TEXT,
            approved_by_lawyer INTEGER DEFAULT 0,
            updated_at TEXT
        )
        """
    )
    conn.commit()
    return conn


def _slot(key: str) -> dict:
    for slot in _all_slots():
        if slot["key"] == key:
            return slot
    raise KeyError(key)


def _default_body(slot: dict) -> str:
    if any(slot["key"] == item["key"] for item in IT_LEGAL_SLOTS):
        return it_skeleton_body(slot["title"])
    return skeleton_body(slot["title"])


def list_slots() -> list[dict]:
    conn = _template_db()
    try:
        rows = {
            row["slot"]: row
            for row in conn.execute("SELECT * FROM cf_legal_templates").fetchall()
        }
    finally:
        conn.close()
    listed = []
    for slot in LEGAL_SLOTS:
        row = rows.get(slot["key"])
        listed.append({
            "key": slot["key"],
            "title": slot["title"],
            "filename": row["filename"] if row else None,
            "approved_by_lawyer": bool(row["approved_by_lawyer"]) if row else False,
            "has_upload": bool(row),
            "watermark": None if row and row["approved_by_lawyer"] else WATERMARK,
        })
    return listed


def template_dir() -> Path:
    from app.edition import data_root_or_none

    root = data_root_or_none()
    base = root if root is not None else Path(os.path.expanduser("~/empire-data"))
    path = base / "legal_templates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _docx_text(data: bytes) -> str:
    import io
    import zipfile
    from xml.etree import ElementTree

    with zipfile.ZipFile(io.BytesIO(data)) as package:
        xml = package.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    parts = [node.text or "" for node in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")]
    return "\n".join(part for part in parts if part).strip()


def save_uploaded_template(slot: str, filename: str, data: bytes) -> dict:
    meta = _slot(slot)
    suffix = Path(filename or "plantilla.txt").suffix.lower()
    dest = template_dir() / f"{slot}{suffix or '.bin'}"
    dest.write_bytes(data)
    if suffix == ".docx":
        body = _docx_text(data)
    elif suffix in {".txt", ".md", ".html"}:
        body = data.decode("utf-8", errors="replace")
    else:
        body = (
            f"Archivo cargado: {filename}\n\n"
            "El texto de este archivo lo aporta quien lo sube. "
            "Esta ficha no redacta cláusulas.\n\n"
            + skeleton_body(meta["title"])
        )
    conn = _template_db()
    try:
        conn.execute(
            """
            INSERT INTO cf_legal_templates (slot, title, filename, body, stored_path, approved_by_lawyer, updated_at)
            VALUES (?, ?, ?, ?, ?, 0, ?)
            ON CONFLICT(slot) DO UPDATE SET
                filename=excluded.filename,
                body=excluded.body,
                stored_path=excluded.stored_path,
                approved_by_lawyer=0,
                updated_at=excluded.updated_at
            """,
            (slot, meta["title"], filename, body, str(dest), datetime.utcnow().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
    return {"key": slot, "title": meta["title"], "filename": filename, "approved_by_lawyer": False}


def mark_lawyer_approved(slot: str, approved: bool) -> dict:
    _slot(slot)
    conn = _template_db()
    try:
        row = conn.execute("SELECT slot FROM cf_legal_templates WHERE slot = ?", (slot,)).fetchone()
        if row is None:
            meta = _slot(slot)
            conn.execute(
                """
                INSERT INTO cf_legal_templates (slot, title, filename, body, approved_by_lawyer, updated_at)
                VALUES (?, ?, '', '', ?, ?)
                """,
                (slot, meta["title"], 1 if approved else 0, datetime.utcnow().isoformat()),
            )
        else:
            conn.execute(
                "UPDATE cf_legal_templates SET approved_by_lawyer = ?, updated_at = ? WHERE slot = ?",
                (1 if approved else 0, datetime.utcnow().isoformat(), slot),
            )
        conn.commit()
    finally:
        conn.close()
    return {"key": slot, "approved_by_lawyer": bool(approved)}


def render_slot(slot: str, values: dict | None = None) -> dict:
    meta = _slot(slot)
    conn = _template_db()
    try:
        row = conn.execute("SELECT * FROM cf_legal_templates WHERE slot = ?", (slot,)).fetchone()
    finally:
        conn.close()
    approved = bool(row["approved_by_lawyer"]) if row else False
    source = row["body"] if row and row["body"] else _default_body(meta)
    if not approved and WATERMARK not in source:
        source = f"{WATERMARK}\n\n{source}"
    filled = fill_placeholders(source, values, force_watermark=not approved)
    return {
        "key": slot,
        "title": meta["title"],
        "approved_by_lawyer": approved,
        "watermark": None if approved else WATERMARK,
        "body": filled,
    }


def render_package_attachments(values: dict | None = None) -> list[dict]:
    return [render_slot(slot["key"], values) for slot in LEGAL_SLOTS]


def render_it_attachments(values: dict | None = None) -> list[dict]:
    return [render_slot(slot["key"], values) for slot in IT_LEGAL_SLOTS]


def attachment_manifest(attachments: list[dict]) -> str:
    return json.dumps(
        [{"key": item["key"], "title": item["title"], "approved_by_lawyer": item["approved_by_lawyer"]} for item in attachments],
        ensure_ascii=False,
    )
