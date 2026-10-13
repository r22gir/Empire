"""Designer selection board → preview proposal/estimate.

Boards persist in the isolated empire DB for draft work. Conversion
composes an estimate payload and never writes quotes, invoices,
customers, or any live Workroom record.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Optional

from app.services.luxeforge.catalog import FABRICS, FINISHES, PHOTOS, item_by_id

DEFAULT_YARDS = {
    "drapery": 18,
    "upholstery": 12,
    "roman": 8,
    "bedding": 10,
}
DEFAULT_LABOR = {
    "drapery": 980,
    "upholstery": 1640,
    "roman": 540,
    "bedding": 420,
}


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def new_id() -> str:
    return uuid.uuid4().hex


def ensure_board_schema(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS luxe_selection_boards (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            client_name TEXT,
            project_name TEXT,
            treatment TEXT,
            notes TEXT,
            selections_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT,
            updated_at TEXT
        )
        """
    )


def _row_to_board(row) -> dict:
    data = dict(row)
    try:
        selections = json.loads(data.get("selections_json") or "[]")
    except Exception:
        selections = []
    data["selections"] = selections
    data.pop("selections_json", None)
    return data


def list_boards(conn) -> list[dict]:
    ensure_board_schema(conn)
    rows = conn.execute(
        "SELECT * FROM luxe_selection_boards ORDER BY updated_at DESC"
    ).fetchall()
    return [_row_to_board(r) for r in rows]


def load_board(conn, board_id: str) -> Optional[dict]:
    ensure_board_schema(conn)
    row = conn.execute(
        "SELECT * FROM luxe_selection_boards WHERE id = ?", (board_id,)
    ).fetchone()
    return _row_to_board(row) if row else None


def save_board(conn, payload: dict, board_id: Optional[str] = None) -> dict:
    ensure_board_schema(conn)
    stamp = now_iso()
    selections = payload.get("selections") or []
    blob = json.dumps(selections)
    if board_id:
        existing = load_board(conn, board_id)
        if not existing:
            raise KeyError(board_id)
        conn.execute(
            """
            UPDATE luxe_selection_boards
               SET title = ?, client_name = ?, project_name = ?, treatment = ?,
                   notes = ?, selections_json = ?, updated_at = ?
             WHERE id = ?
            """,
            (
                payload.get("title") or existing.get("title") or "Untitled board",
                payload.get("client_name", existing.get("client_name")),
                payload.get("project_name", existing.get("project_name")),
                payload.get("treatment", existing.get("treatment") or "drapery"),
                payload.get("notes", existing.get("notes")),
                blob,
                stamp,
                board_id,
            ),
        )
        return load_board(conn, board_id) or {}
    board_id = new_id()
    conn.execute(
        """
        INSERT INTO luxe_selection_boards
            (id, title, client_name, project_name, treatment, notes, selections_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            board_id,
            payload.get("title") or "Untitled board",
            payload.get("client_name") or "",
            payload.get("project_name") or "",
            payload.get("treatment") or "drapery",
            payload.get("notes") or "",
            blob,
            stamp,
            stamp,
        ),
    )
    return load_board(conn, board_id) or {}


def hydrate_selections(selections: list[dict]) -> list[dict]:
    out = []
    for sel in selections or []:
        catalog = item_by_id(str(sel.get("id") or sel.get("catalog_id") or ""))
        if not catalog:
            continue
        row = {**catalog, **{k: v for k, v in sel.items() if v is not None}}
        row["qty"] = float(sel.get("qty") or _default_qty(catalog, sel))
        out.append(row)
    return out


def _default_qty(catalog: dict, sel: dict) -> float:
    kind = catalog.get("kind")
    if kind == "fabric":
        return float(sel.get("qty") or DEFAULT_YARDS.get(sel.get("treatment") or "drapery", 12))
    if kind == "finish":
        return float(sel.get("qty") or 1)
    return 1


def line_amount(item: dict) -> float:
    kind = item.get("kind")
    qty = float(item.get("qty") or 1)
    if kind == "fabric":
        return round(qty * float(item.get("price_per_yard") or 0), 2)
    if kind == "finish":
        return round(qty * float(item.get("price") or 0), 2)
    return 0.0


def board_to_estimate(board: dict) -> dict:
    """Compose a preview proposal. Never writes a quote."""
    treatment = (board.get("treatment") or "drapery").lower()
    selections = hydrate_selections(board.get("selections") or [])
    lines = []
    materials = 0.0
    for item in selections:
        if item.get("kind") == "photo":
            continue
        amount = line_amount(item)
        materials += amount
        unit = "yard" if item.get("kind") == "fabric" else item.get("unit") or "ea"
        unit_price = item.get("price_per_yard") if item.get("kind") == "fabric" else item.get("price")
        lines.append({
            "id": item.get("id"),
            "kind": item.get("kind"),
            "name": item.get("name"),
            "house": item.get("house") or item.get("family"),
            "qty": item.get("qty"),
            "unit": unit,
            "unit_price": unit_price,
            "amount": amount,
            "notes": item.get("notes"),
        })
    labor = float(DEFAULT_LABOR.get(treatment, 800))
    if any(i.get("kind") == "fabric" for i in selections):
        lines.append({
            "id": "labor-studio",
            "kind": "labor",
            "name": f"{treatment.title()} studio labor",
            "house": "LuxeForge workroom",
            "qty": 1,
            "unit": "lot",
            "unit_price": labor,
            "amount": labor,
            "notes": "Cut, sew, finish. Preview rate — not a live quote.",
        })
    subtotal = round(materials + labor if any(i.get("kind") == "fabric" for i in selections) else materials, 2)
    if not any(i.get("kind") == "fabric" for i in selections):
        labor = 0.0
        subtotal = round(materials, 2)
    deposit = round(subtotal * 0.5, 2)
    photos = [i for i in selections if i.get("kind") == "photo"]
    return {
        "title": board.get("title") or "Design proposal",
        "client_name": board.get("client_name") or "",
        "project_name": board.get("project_name") or "",
        "treatment": treatment,
        "notes": board.get("notes") or "",
        "lines": lines,
        "photos": [{"id": p["id"], "name": p["name"], "room": p.get("room"), "mood": p.get("mood")} for p in photos],
        "materials": round(materials, 2),
        "labor": labor,
        "subtotal": subtotal,
        "deposit_suggested": deposit,
        "currency": "USD",
        "status": "preview",
        "wrote_quote": False,
        "wrote_live": False,
        "wrote_invoices": False,
        "sent": False,
        "catalog_counts": {
            "fabrics": sum(1 for i in selections if i.get("kind") == "fabric"),
            "finishes": sum(1 for i in selections if i.get("kind") == "finish"),
            "photos": len(photos),
        },
        "disclaimer": "Preview estimate only. Nothing was written to live quotes, invoices, or clients.",
    }


def demo_board() -> dict:
    """In-memory starter board so the UI is never empty."""
    return {
        "id": "demo",
        "title": "Drawing-room study",
        "client_name": "Sample residence",
        "project_name": "North windows + pair of chairs",
        "treatment": "drapery",
        "notes": "Keep the evening light. Chair pair in mohair.",
        "selections": [
            {"id": "fab-silk-taffeta", "qty": 18, "treatment": "drapery"},
            {"id": "fab-mohair-velvet", "qty": 14, "treatment": "upholstery"},
            {"id": "fin-brass-antique", "qty": 1},
            {"id": "fin-interline-blackout", "qty": 18},
            {"id": "pho-drawing-room"},
            {"id": "pho-library"},
        ],
    }


# Keep catalogs importable for tests without a DB.
CATALOG_SIZES = {"fabrics": len(FABRICS), "finishes": len(FINISHES), "photos": len(PHOTOS)}
