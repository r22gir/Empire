"""Compare installation prices across jobs: $/window and $/LF.

Read-only against quotes_v2 / quote_line_items / invoices. The PDF write
is the only side effect, and sending stays off unless the caller sets
send=true AND a channel. This module never calls the Max `present` tool.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.services.install_line_tagging import (
    apply_tags_to_line,
    format_feet,
    is_install_line,
    looks_like_legacy_doc,
    normalize_doc_ref,
    parse_mixed_number,
    persist_quote_line_tags,
    tag_install_line,
    tag_invoice_lines,
)

_SEND_CHANNELS = {"telegram", "email", "whatsapp"}

# Tests monkeypatch this. Default implementation is a no-op so a bug
# cannot silently ship a document through present / Telegram / mail.
_DELIVER = None


def _as_amount(line: dict) -> Optional[float]:
    for key in ("final_price", "amount", "subtotal", "total", "line_total"):
        n = parse_mixed_number(line.get(key))
        if n is not None:
            return round(n, 2)
    qty = parse_mixed_number(line.get("quantity") or line.get("qty")) or 1.0
    rate = parse_mixed_number(line.get("unit_price") or line.get("rate") or line.get("price"))
    if rate is None:
        return None
    return round(qty * rate, 2)


def _money(n: Optional[float]) -> Optional[float]:
    if n is None:
        return None
    return round(float(n), 2)


def _per(amount: Optional[float], count: Optional[float]) -> Optional[float]:
    if amount is None or count is None or count <= 0:
        return None
    return round(amount / count, 2)


def _stats(values: list[float]) -> dict:
    clean = [v for v in values if v is not None]
    if not clean:
        return {"avg": None, "min": None, "max": None, "count": 0}
    return {
        "avg": _money(statistics.fmean(clean)),
        "min": _money(min(clean)),
        "max": _money(max(clean)),
        "count": len(clean),
    }


def _table_exists(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return bool(row)


def _cols(conn, table: str) -> set[str]:
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return set()


def _row(r) -> dict:
    if r is None:
        return {}
    try:
        return dict(r)
    except Exception:
        return {}


def _explicit_send_requested(params: dict) -> bool:
    send = params.get("send")
    if send is True:
        pass
    elif str(send or "").strip().lower() in {"1", "true", "yes", "on"}:
        pass
    else:
        return False
    channel = str(params.get("channel") or params.get("via") or "").strip().lower()
    return channel in _SEND_CHANNELS


def _match_ref(value: Any, wanted: set[str]) -> bool:
    if not wanted:
        return False
    text = normalize_doc_ref(value)
    if text in wanted:
        return True
    raw = str(value or "").strip().upper()
    if raw in wanted:
        return True
    # "Willard Est 838" / issued_document 812-C
    tokens = {normalize_doc_ref(p) for p in re.split(r"[\s,/|]+", str(value or "")) if p}
    return bool(tokens & wanted)


def resolve_quotes_and_jobs(conn, refs: list[str]) -> dict:
    """Resolve EST numbers, job ids, and imported legacy numbers (812-C, 838, …)."""
    wanted = {normalize_doc_ref(r) for r in refs if str(r or "").strip()}
    wanted |= {str(r).strip().upper() for r in refs if str(r or "").strip()}
    quotes: list[dict] = []
    jobs: list[dict] = []
    invoices: list[dict] = []
    seen_q: set[str] = set()
    seen_j: set[str] = set()
    seen_i: set[str] = set()

    if _table_exists(conn, "quotes_v2") and wanted:
        qcols = _cols(conn, "quotes_v2")
        fields = [c for c in (
            "id", "quote_number", "job_id", "customer_id", "customer_name",
            "project_name", "issued_document", "status", "total", "source_json_path",
        ) if c in qcols]
        for row in conn.execute(f"SELECT {', '.join(fields or ['id'])} FROM quotes_v2"):
            q = _row(row)
            hay = [
                q.get("id"), q.get("quote_number"), q.get("issued_document"),
                q.get("project_name"), q.get("job_id"),
            ]
            if any(_match_ref(h, wanted) for h in hay) or looks_like_legacy_doc(q.get("quote_number") or q.get("issued_document")) and normalize_doc_ref(q.get("quote_number") or q.get("issued_document")) in wanted:
                qid = str(q.get("id") or "")
                if qid and qid not in seen_q:
                    seen_q.add(qid)
                    quotes.append(q)

    if _table_exists(conn, "jobs") and wanted:
        jcols = _cols(conn, "jobs")
        fields = [c for c in (
            "id", "job_number", "title", "quote_id", "customer_id", "client_name",
        ) if c in jcols]
        for row in conn.execute(f"SELECT {', '.join(fields or ['id'])} FROM jobs"):
            j = _row(row)
            hay = [j.get("id"), j.get("job_number"), j.get("title"), j.get("quote_id")]
            if any(_match_ref(h, wanted) for h in hay):
                jid = str(j.get("id") or "")
                if jid and jid not in seen_j:
                    seen_j.add(jid)
                    jobs.append(j)

        # Quotes linked to matched jobs
        if quotes is not None and _table_exists(conn, "quotes_v2"):
            job_ids = {str(j["id"]) for j in jobs}
            quote_ids = {str(j.get("quote_id")) for j in jobs if j.get("quote_id")}
            if job_ids or quote_ids:
                qcols = _cols(conn, "quotes_v2")
                fields = [c for c in (
                    "id", "quote_number", "job_id", "customer_id", "customer_name",
                    "project_name", "issued_document", "status", "total",
                ) if c in qcols]
                for row in conn.execute(f"SELECT {', '.join(fields or ['id'])} FROM quotes_v2"):
                    q = _row(row)
                    qid = str(q.get("id") or "")
                    if qid in seen_q:
                        continue
                    if str(q.get("job_id") or "") in job_ids or qid in quote_ids:
                        seen_q.add(qid)
                        quotes.append(q)

    if _table_exists(conn, "invoices") and wanted:
        icols = _cols(conn, "invoices")
        fields = [c for c in (
            "id", "invoice_number", "quote_id", "job_id", "client_name",
            "line_items", "notes", "total",
        ) if c in icols]
        quote_ids = {str(q["id"]) for q in quotes}
        job_ids = {str(j["id"]) for j in jobs}
        for row in conn.execute(f"SELECT {', '.join(fields or ['id'])} FROM invoices"):
            inv = _row(row)
            iid = str(inv.get("id") or "")
            hay = [
                inv.get("id"), inv.get("invoice_number"), inv.get("quote_id"),
                inv.get("job_id"), inv.get("notes"),
            ]
            linked = str(inv.get("quote_id") or "") in quote_ids or str(inv.get("job_id") or "") in job_ids
            if linked or any(_match_ref(h, wanted) for h in hay):
                if iid and iid not in seen_i:
                    seen_i.add(iid)
                    invoices.append(inv)

    return {"quotes": quotes, "jobs": jobs, "invoices": invoices, "wanted": sorted(wanted)}


def _quote_meta(quote: dict) -> dict:
    return {
        "source_kind": "quote",
        "source_id": quote.get("id"),
        "quote_id": quote.get("id"),
        "quote_number": (
            quote.get("issued_document")
            if looks_like_legacy_doc(quote.get("issued_document"))
            else quote.get("quote_number") or quote.get("issued_document") or quote.get("id")
        ),
        "job_id": quote.get("job_id"),
        "customer_name": quote.get("customer_name"),
        "project_name": quote.get("project_name"),
        "issued_document": quote.get("issued_document"),
        "legacy": looks_like_legacy_doc(quote.get("quote_number") or quote.get("issued_document")),
    }


def collect_install_lines(conn, refs: list[str], *, role: str) -> list[dict]:
    resolved = resolve_quotes_and_jobs(conn, refs)
    lines: list[dict] = []
    seen: set[tuple] = set()

    if _table_exists(conn, "quote_line_items"):
        from app.services.install_line_tagging import ensure_install_columns
        ensure_install_columns(conn)
        for q in resolved["quotes"]:
            meta = _quote_meta(q)
            rows = conn.execute(
                "SELECT * FROM quote_line_items WHERE quote_id = ? ORDER BY line_number, id",
                (q["id"],),
            ).fetchall()
            for row in rows:
                raw = _row(row)
                tagged = apply_tags_to_line(raw)
                if not is_install_line(
                    tagged.get("description"),
                    item_type=tagged.get("item_type"),
                    category=tagged.get("category"),
                    labor_description=tagged.get("labor_description"),
                ):
                    continue
                key = ("qli", str(raw.get("id") or ""), str(q.get("id") or ""))
                if key in seen:
                    continue
                seen.add(key)
                lines.append(_line_record(tagged, meta, role))

    for inv in resolved["invoices"]:
        raw_items = inv.get("line_items")
        items = tag_invoice_lines(raw_items)
        meta = {
            "source_kind": "invoice",
            "source_id": inv.get("id"),
            "quote_id": inv.get("quote_id"),
            "quote_number": inv.get("invoice_number"),
            "job_id": inv.get("job_id"),
            "customer_name": inv.get("client_name"),
            "project_name": None,
            "issued_document": inv.get("invoice_number"),
            "legacy": looks_like_legacy_doc(inv.get("invoice_number")),
        }
        for idx, tagged in enumerate(items):
            if not isinstance(tagged, dict):
                continue
            if not is_install_line(
                tagged.get("description") or tagged.get("name"),
                item_type=tagged.get("item_type"),
                category=tagged.get("category"),
            ):
                continue
            key = ("inv", str(inv.get("id") or ""), idx, str(tagged.get("description") or ""))
            if key in seen:
                continue
            # Skip invoice lines that already appear on a resolved quote
            if str(inv.get("quote_id") or "") in {str(q.get("id")) for q in resolved["quotes"]}:
                continue
            seen.add(key)
            lines.append(_line_record(tagged, meta, role))

    return lines


def _line_record(tagged: dict, meta: dict, role: str) -> dict:
    tags = tag_install_line(tagged)
    windows = tags["windows"]
    lf = tags["lf"]
    amount = _as_amount(tagged)
    missing_windows = windows is None
    missing_lf = lf is None
    return {
        **meta,
        "role": role,
        "description": tagged.get("description") or tagged.get("name") or "",
        "item_type": "installation",
        "windows": windows,
        "lf": lf,
        "lf_display": format_feet(lf) if lf is not None else "—",
        "amount": amount,
        "per_window": _per(amount, windows),
        "per_lf": _per(amount, lf),
        "missing_windows": missing_windows,
        "missing_lf": missing_lf,
        "missing_counts": missing_windows or missing_lf,
        "flag": (
            "lacking window count and LF"
            if missing_windows and missing_lf
            else "lacking window count"
            if missing_windows
            else "lacking LF"
            if missing_lf
            else None
        ),
    }


def compare_install_prices(
    *,
    quote_numbers: Optional[list[str]] = None,
    job_ids: Optional[list[str]] = None,
    new_quote: Optional[str | list[str]] = None,
    conn=None,
    generate_pdf: bool = True,
    save_to_job: bool = True,
    send: bool = False,
    channel: Optional[str] = None,
    params: Optional[dict] = None,
) -> dict:
    """Per-line and aggregated $/window and $/LF vs a new quote.

    Sending is OFF unless send=true and channel is telegram|email|whatsapp.
    Never routes through the `present` tool.
    """
    params = dict(params or {})
    if quote_numbers:
        params.setdefault("quote_numbers", quote_numbers)
    if job_ids:
        params.setdefault("job_ids", job_ids)
    if new_quote:
        params.setdefault("new_quote", new_quote)
    params.setdefault("generate_pdf", generate_pdf)
    params.setdefault("save_to_job", save_to_job)
    if send:
        params["send"] = True
    if channel:
        params["channel"] = channel

    refs = _as_ref_list(params.get("quote_numbers") or params.get("quotes") or params.get("quote_number"))
    refs += _as_ref_list(params.get("job_ids") or params.get("jobs") or params.get("job_id"))
    new_refs = _as_ref_list(params.get("new_quote") or params.get("new_quote_number"))

    close_conn = False
    if conn is None:
        from app.db.database import get_connection
        conn = get_connection()
        close_conn = True
    try:
        historical = collect_install_lines(conn, refs, role="historical")
        new_lines = collect_install_lines(conn, new_refs, role="new") if new_refs else []

        hist_pw = [ln["per_window"] for ln in historical if ln["per_window"] is not None]
        hist_pl = [ln["per_lf"] for ln in historical if ln["per_lf"] is not None]
        new_pw = [ln["per_window"] for ln in new_lines if ln["per_window"] is not None]
        new_pl = [ln["per_lf"] for ln in new_lines if ln["per_lf"] is not None]
        hist_agg = {
            "per_window": _stats(hist_pw),
            "per_lf": _stats(hist_pl),
            "line_count": len(historical),
            "flagged": sum(1 for ln in historical if ln["missing_counts"]),
        }
        new_agg = {
            "per_window": _stats(new_pw),
            "per_lf": _stats(new_pl),
            "line_count": len(new_lines),
            "flagged": sum(1 for ln in new_lines if ln["missing_counts"]),
        }

        def _delta(new_s, hist_s):
            if new_s.get("avg") is None or hist_s.get("avg") is None:
                return None
            return _money(new_s["avg"] - hist_s["avg"])

        comparison = {
            "per_window_delta_vs_avg": _delta(new_agg["per_window"], hist_agg["per_window"]),
            "per_lf_delta_vs_avg": _delta(new_agg["per_lf"], hist_agg["per_lf"]),
        }

        job_id = _pick_job_id(params, historical, new_lines, conn)
        payload = {
            "ok": True,
            "read_only": True,
            "used_present_tool": False,
            "sent": False,
            "telegram_sent": False,
            "email_sent": False,
            "whatsapp_sent": False,
            "send_default": "off",
            "historical": historical,
            "new_quote": new_lines,
            "aggregates": {"historical": hist_agg, "new_quote": new_agg},
            "comparison": comparison,
            "flagged_lines": [ln for ln in (historical + new_lines) if ln["missing_counts"]],
            "resolved": {
                "historical_refs": refs,
                "new_quote_refs": new_refs,
                "job_id": job_id,
            },
            "pdf_path": None,
            "document": None,
        }

        want_pdf = _truthy(params.get("generate_pdf"), default=True)
        if want_pdf:
            from app.services.install_compare_pdf import render_install_compare_pdf, save_pdf_to_job
            pdf_bytes, pdf_path = render_install_compare_pdf(payload)
            payload["pdf_path"] = str(pdf_path)
            payload["pdf_size_bytes"] = len(pdf_bytes)
            if _truthy(params.get("save_to_job"), default=True) and job_id:
                doc = save_pdf_to_job(conn, job_id, pdf_path, pdf_bytes)
                payload["document"] = doc
                payload["job_id"] = job_id

        send_requested = _explicit_send_requested(params)
        payload["send_requested"] = send_requested
        if send_requested:
            payload.update(_deliver(payload, params))
        else:
            payload["send_reason"] = "sending_off_by_default"
        return payload
    finally:
        if close_conn:
            conn.close()


def _as_ref_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    if "," in text:
        return [p.strip() for p in text.split(",") if p.strip()]
    return [text]


def _truthy(value: Any, *, default: bool) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _pick_job_id(params: dict, historical: list[dict], new_lines: list[dict], conn) -> Optional[str]:
    for key in ("save_job_id", "target_job_id", "job_id"):
        if params.get(key):
            return str(params[key])
    for ln in new_lines + historical:
        if ln.get("job_id"):
            return str(ln["job_id"])
    return None


def _deliver(payload: dict, params: dict) -> dict:
    """Explicit send only. Never calls `present`."""
    channel = str(params.get("channel") or params.get("via") or "").strip().lower()
    result = {
        "sent": False,
        "telegram_sent": False,
        "email_sent": False,
        "whatsapp_sent": False,
        "used_present_tool": False,
        "send_channel": channel,
    }
    deliver = _DELIVER
    if deliver is None:
        result["send_reason"] = "explicit_send_requested_but_no_deliverer_bound"
        return result
    delivered = deliver(payload, params) or {}
    if delivered.get("used_present_tool"):
        raise RuntimeError("install compare must not use the present tool path")
    result.update(delivered)
    return result


def apply_tags_on_quote_save(conn, data: dict, **kwargs) -> dict:
    """Quoted so quote_service can persist tags without importing compare."""
    return persist_quote_line_tags(conn, data, **kwargs)
