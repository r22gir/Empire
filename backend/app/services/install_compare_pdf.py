"""Empire Workroom install-price comparison PDF.

Landscape letter, McLean chrome bands, fraction measurements (never
decimal inches/feet). Dollars may be decimals. Saved to the job's
documents. This module does not send Telegram, email, or WhatsApp
and never calls the Max `present` tool.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas

from app.services.drawing.max_sheet_chrome import (
    BAND,
    FTR_H,
    GOLD,
    HDR_H,
    INK,
    LETTERHEAD,
    MUTE,
    PAPER,
    PH,
    POWERED_BY,
    PW,
    render_chrome_bands,
)
from app.services.install_line_tagging import format_feet

PANEL = HexColor("#efe9dc")
ROW_SHADE = HexColor("#efe8dc")
FLAG = HexColor("#8b2e2e")
MARGIN_L = 28.0
MARGIN_R = 28.0
CONTENT_TOP = PH - HDR_H - 14.0
CONTENT_BOTTOM = FTR_H + 14.0


def _money(n) -> str:
    if n is None:
        return "—"
    return f"${float(n):,.2f}"


def _intish(n) -> str:
    if n is None:
        return "—"
    return str(int(n))


def render_install_compare_pdf(payload: dict, dest: Optional[Path] = None) -> tuple[bytes, Path]:
    """Render the comparison table. Returns (bytes, path)."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(PW, PH))
    c.setTitle("Install Price Comparison — Empire Workroom")
    c.setAuthor("Empire Workroom")
    hist = payload.get("historical") or []
    new_lines = payload.get("new_quote") or []
    job_id = (payload.get("resolved") or {}).get("job_id") or payload.get("job_id") or ""
    refs = (payload.get("resolved") or {}).get("historical_refs") or []
    new_refs = (payload.get("resolved") or {}).get("new_quote_refs") or []
    date_s = datetime.now().strftime("%d %b %Y").upper()

    render_chrome_bands(
        c,
        sheet_no=1,
        total=1,
        right_title="INSTALL COMPARE",
        letterhead=LETTERHEAD,
        powered_by=POWERED_BY,
        client="EMPIRE WORKROOM",
        project="INSTALL PRICE COMPARISON",
        rev="A",
        date=date_s,
    )
    c.setFillColor(PAPER)
    c.rect(0, FTR_H, PW, PH - HDR_H - FTR_H, fill=1, stroke=0)

    y = CONTENT_TOP
    c.setFillColor(INK)
    c.setFont("Times-Bold", 13)
    c.drawString(MARGIN_L, y, "Installation price comparison")
    y -= 14
    c.setFillColor(MUTE)
    c.setFont("Helvetica", 8)
    c.drawString(
        MARGIN_L,
        y,
        f"Past jobs: {', '.join(str(r) for r in refs) or '—'}    ·    New quote: {', '.join(str(r) for r in new_refs) or '—'}",
    )
    y -= 11
    c.drawString(
        MARGIN_L,
        y,
        "Measurements in fractions. Dollars may use decimals. Sending is off — this PDF is saved to the job only.",
    )
    y -= 16

    headers = ["Source", "Quote / job", "Description", "Windows", "LF", "Amount", "$/window", "$/LF", "Flags"]
    widths = [52, 78, 196, 50, 58, 64, 64, 58, 76]
    rows = [_pdf_row(ln) for ln in hist] + [_pdf_row(ln) for ln in new_lines]
    if not rows:
        rows = [["—", "—", "No installation lines found", "—", "—", "—", "—", "—", "—"]]

    y = _draw_table(c, MARGIN_L, y, headers, rows, widths)

    y -= 18
    agg = payload.get("aggregates") or {}
    hist_a = agg.get("historical") or {}
    new_a = agg.get("new_quote") or {}
    cmp_ = payload.get("comparison") or {}
    y = _draw_aggregates(c, MARGIN_L, y, hist_a, new_a, cmp_)

    flagged = payload.get("flagged_lines") or []
    if flagged:
        y -= 16
        c.setFillColor(FLAG)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(MARGIN_L, y, f"Lines lacking counts: {len(flagged)}")
        y -= 11
        c.setFont("Helvetica", 7)
        for ln in flagged[:8]:
            c.drawString(
                MARGIN_L,
                y,
                f"• {ln.get('quote_number') or ln.get('job_id') or '—'}  {ln.get('description') or ''}  —  {ln.get('flag')}",
            )
            y -= 10
            if y < CONTENT_BOTTOM + 20:
                break

    c.save()
    pdf_bytes = buf.getvalue()
    if dest is None:
        from app.services.data_paths import data_root
        stamp = datetime.now(timezone.utc).strftime("%y%m%d_%H%M%S")
        dest = data_root() / "generated" / "install_compare" / f"install-price-compare-{stamp}.pdf"
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(pdf_bytes)
    return pdf_bytes, dest


def _pdf_row(ln: dict) -> list[str]:
    return [
        "NEW" if ln.get("role") == "new" else ("LEGACY" if ln.get("legacy") else "PAST"),
        str(ln.get("quote_number") or ln.get("job_id") or "—"),
        (ln.get("description") or "")[:56],
        _intish(ln.get("windows")),
        ln.get("lf_display") or (format_feet(ln["lf"]) if ln.get("lf") is not None else "—"),
        _money(ln.get("amount")),
        _money(ln.get("per_window")),
        _money(ln.get("per_lf")),
        ln.get("flag") or "",
    ]


def _draw_table(c: canvas.Canvas, x: float, y: float, headers: list[str], rows: list[list[str]], widths: list[float]) -> float:
    row_h = 14.0
    head_h = 16.0
    total_w = sum(widths)
    c.setFillColor(BAND)
    c.rect(x, y - head_h, total_w, head_h, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 6.5)
    cx = x
    for h, w in zip(headers, widths):
        c.drawString(cx + 3, y - 11, h.upper())
        cx += w
    y -= head_h
    for i, row in enumerate(rows):
        bg = ROW_SHADE if i % 2 == 0 else PANEL
        c.setFillColor(bg)
        c.rect(x, y - row_h, total_w, row_h, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("Helvetica", 6.5)
        cx = x
        for cell, w in zip(row, widths):
            c.drawString(cx + 3, y - 10, str(cell)[:36])
            cx += w
        y -= row_h
        if y < CONTENT_BOTTOM + 80:
            break
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.6)
    c.rect(x, y, total_w, head_h + row_h * min(len(rows), 20), fill=0, stroke=1)
    return y


def _draw_aggregates(c, x, y, hist_a, new_a, cmp_) -> float:
    c.setFillColor(INK)
    c.setFont("Times-Bold", 10)
    c.drawString(x, y, "Aggregates")
    y -= 13
    c.setFont("Helvetica", 8)
    def line(label, block):
        pw = block.get("per_window") or {}
        pl = block.get("per_lf") or {}
        return (
            f"{label}:  $/window avg {_money(pw.get('avg'))}  min {_money(pw.get('min'))}  max {_money(pw.get('max'))}"
            f"    ·    $/LF avg {_money(pl.get('avg'))}  min {_money(pl.get('min'))}  max {_money(pl.get('max'))}"
        )
    c.drawString(x, y, line("Past jobs", hist_a))
    y -= 11
    c.drawString(x, y, line("New quote", new_a))
    y -= 11
    c.drawString(
        x,
        y,
        f"New vs past avg:  $/window {_money(cmp_.get('per_window_delta_vs_avg'))}    ·    $/LF {_money(cmp_.get('per_lf_delta_vs_avg'))}",
    )
    return y


def save_pdf_to_job(conn, job_id: str, pdf_path: Path, pdf_bytes: bytes) -> dict:
    """Write the PDF onto the job and insert a job_documents row. No send."""
    from app.services.data_paths import jobs_dir

    job_id = str(job_id)
    dest_dir = jobs_dir() / job_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(pdf_path).name
    dest = dest_dir / filename
    if Path(pdf_path).resolve() != dest.resolve():
        dest.write_bytes(pdf_bytes)
    url = f"/api/v1/jobs/{job_id}/files/{filename}"
    doc_id = uuid.uuid4().hex[:16]
    now = datetime.now(timezone.utc).isoformat()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(job_documents)").fetchall()} if _table_ok(conn, "job_documents") else set()
    if not cols:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS job_documents (
                id TEXT PRIMARY KEY,
                job_id TEXT,
                quote_id TEXT,
                document_type TEXT,
                item_key TEXT,
                url TEXT,
                filename TEXT,
                revision INTEGER DEFAULT 1,
                visible_to_client INTEGER DEFAULT 0,
                source_channel TEXT,
                created_at TEXT
            )"""
        )
        cols = {r[1] for r in conn.execute("PRAGMA table_info(job_documents)").fetchall()}
    fields = ["id", "job_id", "document_type", "url", "filename"]
    values: list[Any] = [doc_id, job_id, "install_compare", url, filename]
    if "visible_to_client" in cols:
        fields.append("visible_to_client")
        values.append(0)
    if "source_channel" in cols:
        fields.append("source_channel")
        values.append("max_chat")
    if "created_at" in cols:
        fields.append("created_at")
        values.append(now)
    placeholders = ", ".join("?" * len(fields))
    conn.execute(
        f"INSERT INTO job_documents ({', '.join(fields)}) VALUES ({placeholders})",
        values,
    )
    try:
        conn.commit()
    except Exception:
        pass
    return {
        "id": doc_id,
        "job_id": job_id,
        "document_type": "install_compare",
        "filename": filename,
        "url": url,
        "path": str(dest),
        "sent": False,
    }


def _table_ok(conn, name: str) -> bool:
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone()
        return bool(row)
    except Exception:
        return False
