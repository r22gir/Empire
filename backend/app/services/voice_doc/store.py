"""Borrador sessions and draft records. Nothing here sends email or chat."""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime
from html import escape
from pathlib import Path

from app.services.voice_doc.extract import DOC_LABELS
from app.services.voice_doc.plans import format_cop


def drafts_db_path() -> str:
    explicit = os.getenv("VOICE_DRAFTS_DB", "").strip()
    if explicit:
        return os.path.expanduser(explicit)
    try:
        from app.edition import data_root_or_none

        root = data_root_or_none()
        if root is not None:
            return str(root / "voice_drafts.db")
    except Exception:
        pass
    return os.path.expanduser("~/empire-data/voice_drafts.db")


def connect():
    path = drafts_db_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS voice_sessions (
            id TEXT PRIMARY KEY,
            channel TEXT,
            edition TEXT,
            status TEXT,
            fields_json TEXT,
            doc_type TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS voice_notes (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            transcript TEXT,
            language TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS voice_drafts (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            doc_type TEXT,
            status TEXT,
            sent INTEGER DEFAULT 0,
            payload_json TEXT,
            html TEXT,
            created_at TEXT,
            approved_at TEXT
        );
        """
    )
    return conn


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _session_row(row) -> dict:
    fields = json.loads(row["fields_json"] or "{}")
    return {
        "id": row["id"],
        "channel": row["channel"],
        "edition": row["edition"],
        "status": row["status"],
        "doc_type": row["doc_type"],
        "fields": fields,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_session(session_id: str) -> dict | None:
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM voice_sessions WHERE id = ?", (session_id,)).fetchone()
        return _session_row(row) if row else None
    finally:
        conn.close()


def open_session(channel: str, edition: str) -> dict | None:
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT * FROM voice_sessions
            WHERE channel = ? AND edition = ? AND status = 'open'
            ORDER BY updated_at DESC LIMIT 1
            """,
            (channel, edition),
        ).fetchone()
        return _session_row(row) if row else None
    finally:
        conn.close()


def create_session(channel: str, edition: str, fields: dict, doc_type: str) -> dict:
    session_id = str(uuid.uuid4())
    now = _now()
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO voice_sessions (id, channel, edition, status, fields_json, doc_type, created_at, updated_at)
            VALUES (?, ?, ?, 'open', ?, ?, ?, ?)
            """,
            (session_id, channel, edition, json.dumps(fields, ensure_ascii=False), doc_type, now, now),
        )
        conn.commit()
    finally:
        conn.close()
    return get_session(session_id)


def save_session(session: dict) -> dict:
    conn = connect()
    try:
        conn.execute(
            """
            UPDATE voice_sessions
            SET status = ?, fields_json = ?, doc_type = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                session["status"],
                json.dumps(session.get("fields") or {}, ensure_ascii=False),
                session.get("doc_type"),
                _now(),
                session["id"],
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return get_session(session["id"])


def add_note(session_id: str, transcript: str, language: str) -> None:
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO voice_notes (id, session_id, transcript, language, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), session_id, transcript, language, _now()),
        )
        conn.commit()
    finally:
        conn.close()


def list_notes(session_id: str) -> list[dict]:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT transcript, language, created_at FROM voice_notes WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def save_draft(session_id: str, doc_type: str, payload: dict, html: str) -> dict:
    draft_id = str(uuid.uuid4())
    payload = dict(payload)
    payload["sent"] = False
    payload["auto_send"] = False
    payload["status"] = "draft"
    conn = connect()
    try:
        conn.execute(
            """
            INSERT INTO voice_drafts (id, session_id, doc_type, status, sent, payload_json, html, created_at)
            VALUES (?, ?, ?, 'draft', 0, ?, ?, ?)
            """,
            (draft_id, session_id, doc_type, json.dumps(payload, ensure_ascii=False), html, _now()),
        )
        conn.commit()
    finally:
        conn.close()
    return get_draft(draft_id)


def get_draft(draft_id: str) -> dict | None:
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM voice_drafts WHERE id = ?", (draft_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    payload = json.loads(row["payload_json"] or "{}")
    payload["sent"] = bool(row["sent"])
    payload["auto_send"] = False
    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "doc_type": row["doc_type"],
        "status": row["status"],
        "sent": bool(row["sent"]),
        "auto_send": False,
        "payload": payload,
        "html": row["html"],
        "created_at": row["created_at"],
        "approved_at": row["approved_at"],
    }


def approve_draft(draft_id: str) -> dict:
    draft = get_draft(draft_id)
    if draft is None:
        raise KeyError(draft_id)
    conn = connect()
    try:
        conn.execute(
            "UPDATE voice_drafts SET status = 'approved', approved_at = ?, sent = 0 WHERE id = ?",
            (_now(), draft_id),
        )
        conn.commit()
    finally:
        conn.close()
    return get_draft(draft_id)


def send_draft(draft_id: str, *, confirm: bool, channel: str = "") -> dict:
    """Explicit confirm still does not email. External delivery is not connected here."""
    draft = get_draft(draft_id)
    if draft is None:
        raise KeyError(draft_id)
    if not confirm or draft["status"] != "approved":
        return {
            "id": draft_id,
            "sent": False,
            "emailed": False,
            "status": draft["status"],
            "reason": "Confirmación explícita requerida. No se envió nada.",
        }
    return {
        "id": draft_id,
        "sent": False,
        "emailed": False,
        "status": draft["status"],
        "channel": channel or "",
        "reason": "El envío externo no está conectado. Descarga el borrador. No se envió correo ni mensaje.",
    }


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def render_draft_pdf(payload: dict, notes: list[str]) -> bytes:
    """Small DRAFT preview. No mailer is attached to these bytes."""
    lines = ["DRAFT", "BORRADOR - no enviado", str(payload.get("label") or "Documento"), "Locale es-CO"]
    fields = payload.get("fields") or {}
    for key in ("buyer_name", "lot_number", "house_type", "finishes", "product_name", "price"):
        if fields.get(key) not in (None, ""):
            lines.append(f"{key}: {fields[key]}")
    schedule = payload.get("schedule") or {}
    if schedule.get("balance") is not None:
        lines.append(f"Saldo {schedule.get('balance')} {schedule.get('currency') or 'COP'}")
    for row in (schedule.get("installments") or [])[:18]:
        lines.append(f"Cuota {row['installment_number']}: {row['amount']}")
    lines.append("BORRADOR - requiere revision de abogado")
    for note in notes[:6]:
        lines.append(str(note)[:90])
    commands = ["BT", "/F1 11 Tf", "48 760 Td"]
    for index, line in enumerate(lines[:42]):
        if index:
            commands.append("0 -16 Td")
        commands.append(f"({_pdf_escape(line[:100])}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("cp1252", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode("ascii")
    )
    return bytes(output)


def render_draft_html(payload: dict, notes: list[str]) -> str:
    doc_type = payload.get("doc_type") or "general"
    title = DOC_LABELS.get(doc_type, "Documento")
    fields = payload.get("fields") or {}
    schedule = payload.get("schedule") or {}
    lines = []
    for label, key in (
        ("Cliente", "buyer_name"),
        ("Lote", "lot_number"),
        ("Casa", "house_type"),
        ("Acabados", "finishes"),
        ("Programa", "product_name"),
        ("Tipo", "product_kind"),
    ):
        if fields.get(key):
            lines.append(f"<tr><th>{escape(label)}</th><td>{escape(str(fields[key]))}</td></tr>")
    if fields.get("price"):
        currency = fields.get("currency") or "COP"
        if currency == "USD":
            amount = f"{fields['price']} USD"
        else:
            amount = f"{format_cop(int(float(fields['price'])))} COP"
        lines.append(f"<tr><th>Precio</th><td>{escape(amount)}</td></tr>")
    schedule_html = ""
    if schedule.get("installments"):
        rows = "".join(
            f"<tr><td>{row['installment_number']}</td><td>{escape(format_cop(row['amount']))}</td></tr>"
            for row in schedule["installments"]
        )
        schedule_html = (
            "<h2>Plan de pagos</h2>"
            f"<p>{escape(schedule.get('summary') or schedule.get('label') or '')}</p>"
            "<table><tr><th>Cuota</th><th>Valor</th></tr>"
            f"{rows}</table>"
            f"<p>Saldo {escape(format_cop(schedule['balance']))}. "
            f"Suma de cuotas {escape(format_cop(sum(row['amount'] for row in schedule['installments'])))}.</p>"
        )
    if payload.get("recibo"):
        schedule_html += f"<h2>Recibo</h2><pre>{escape(payload['recibo'])}</pre>"
    legal = ""
    for attachment in payload.get("attachments") or []:
        legal += f"<h2>{escape(attachment.get('title') or '')}</h2><pre>{escape(attachment.get('body') or '')}</pre>"
    transcript = "\n\n".join(notes)
    missing = ", ".join(payload.get("missing") or []) or "Ninguno"
    return f"""<!DOCTYPE html>
<html lang="es-CO">
<head><meta charset="utf-8"><title>DRAFT {escape(title)}</title>
<style>
body {{ font-family: sans-serif; margin: 32px; color: #1a1a1a; }}
.banner {{ background: #fff4d6; border: 1px solid #b8960c; padding: 12px 16px; font-weight: 700; }}
.watermark {{ position: fixed; inset: 0; display: flex; align-items: center; justify-content: center;
  font-size: 72px; color: rgba(180,0,0,0.12); transform: rotate(-24deg); pointer-events: none; }}
table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
th, td {{ border: 1px solid #ddd; padding: 6px 8px; text-align: left; font-size: 14px; }}
pre {{ white-space: pre-wrap; background: #faf9f7; padding: 12px; }}
</style></head>
<body>
<div class="watermark">BORRADOR</div>
<div class="banner">DRAFT · BORRADOR · No enviado. Hace falta tu confirmación.</div>
<p>Locale es-CO</p>
<h1>{escape(title)}</h1>
<table>{''.join(lines)}</table>
{schedule_html}
<p><strong>Faltantes:</strong> {escape(missing)}</p>
<h2>Transcripción</h2>
<pre>{escape(transcript)}</pre>
{legal}
</body></html>"""
