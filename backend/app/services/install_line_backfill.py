"""Propose / apply install-line tags on existing quote and invoice rows."""
from __future__ import annotations

import json
import sqlite3

from app.services.install_line_tagging import (
    LEGACY_DOC_NUMBERS,
    ensure_install_columns,
    looks_like_legacy_doc,
    tag_install_line,
    tag_invoice_lines,
)


def _table_exists(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return bool(row)


def _cols(conn, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _lf_changed(old, new) -> bool:
    if old is None and new is None:
        return False
    if old is None or new is None:
        return True
    try:
        return abs(float(old) - float(new)) > 1e-6
    except (TypeError, ValueError):
        return True


def propose_install_tags(conn: sqlite3.Connection) -> list[dict]:
    """Scan quote_line_items and invoice JSON lines, including legacy docs."""
    rows: list[dict] = []
    legacy_quote_ids: set[str] = set()
    if _table_exists(conn, "quotes_v2"):
        qcols = _cols(conn, "quotes_v2")
        fields = [c for c in ("id", "quote_number", "issued_document", "project_name") if c in qcols]
        for q in conn.execute(f"SELECT {', '.join(fields or ['id'])} FROM quotes_v2"):
            qd = dict(q)
            blob = " ".join(str(qd.get(k) or "") for k in ("quote_number", "issued_document", "project_name"))
            if any(looks_like_legacy_doc(qd.get(k)) for k in ("quote_number", "issued_document", "project_name")):
                legacy_quote_ids.add(str(qd["id"]))
            if any(n.lower() in blob.lower() for n in LEGACY_DOC_NUMBERS):
                legacy_quote_ids.add(str(qd["id"]))

    if _table_exists(conn, "quote_line_items"):
        ensure_install_columns(conn)
        for raw in conn.execute("SELECT * FROM quote_line_items"):
            line = dict(raw)
            tags = tag_install_line(line)
            if not tags["is_install"]:
                continue
            changed = (
                (line.get("item_type") or "") != "installation"
                or line.get("windows") != tags["windows"]
                or _lf_changed(line.get("lf"), tags["lf"])
            )
            rows.append({
                "kind": "quote_line",
                "id": line.get("id"),
                "quote_id": line.get("quote_id"),
                "description": line.get("description") or "",
                "legacy": str(line.get("quote_id") or "") in legacy_quote_ids,
                "before": {
                    "item_type": line.get("item_type"),
                    "windows": line.get("windows"),
                    "lf": line.get("lf"),
                },
                "after": {
                    "item_type": "installation",
                    "windows": tags["windows"],
                    "lf": tags["lf"],
                },
                "changed": changed,
            })

    if _table_exists(conn, "invoices"):
        icols = _cols(conn, "invoices")
        if "line_items" in icols:
            extra = [c for c in ("id", "invoice_number", "quote_id", "notes") if c in icols]
            for raw in conn.execute(f"SELECT {', '.join(extra + ['line_items'])} FROM invoices"):
                inv = dict(raw)
                legacy = looks_like_legacy_doc(inv.get("invoice_number")) or any(
                    n.lower() in str(inv.get("invoice_number") or inv.get("notes") or "").lower()
                    for n in LEGACY_DOC_NUMBERS
                )
                items = tag_invoice_lines(inv.get("line_items"))
                if not items:
                    continue
                install_any = any(
                    isinstance(it, dict) and (it.get("item_type") == "installation")
                    for it in items
                )
                if not install_any:
                    continue
                rows.append({
                    "kind": "invoice_lines",
                    "id": inv.get("id"),
                    "invoice_number": inv.get("invoice_number"),
                    "quote_id": inv.get("quote_id"),
                    "legacy": legacy,
                    "after": items,
                    "changed": True,
                })
    return rows


def apply_install_tags(conn: sqlite3.Connection, rows: list[dict]) -> dict[str, int]:
    counts = {"quote_line": 0, "invoice_lines": 0, "legacy": 0}
    ensure_install_columns(conn)
    for row in rows:
        if not row.get("changed"):
            continue
        if row["kind"] == "quote_line":
            after = row["after"]
            conn.execute(
                "UPDATE quote_line_items SET item_type = ?, windows = ?, lf = ? WHERE id = ?",
                (after["item_type"], after["windows"], after["lf"], row["id"]),
            )
            counts["quote_line"] += 1
            if row.get("legacy"):
                counts["legacy"] += 1
        elif row["kind"] == "invoice_lines":
            conn.execute(
                "UPDATE invoices SET line_items = ? WHERE id = ?",
                (json.dumps(row["after"], default=str), row["id"]),
            )
            counts["invoice_lines"] += 1
            if row.get("legacy"):
                counts["legacy"] += 1
    return counts
