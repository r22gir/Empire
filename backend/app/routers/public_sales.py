"""Public sales site API (Maxine edition only).

Read-only project and lot data for the public /ventas pages, plus one
rate-limited lead form that creates a ConstructionForge buyer.

Only public fields leave this module: no buyer data, no internal notes,
no prices unless the lot or the project is flagged public.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import unicodedata
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.routers.construction import get_db

router = APIRouter(prefix="/public/ventas", tags=["public-sales"])

PUBLIC_STATUSES = ("available", "reserved", "sold", "consultar")
_STATUS_MAP = {
    "available": "available",
    "disponible": "available",
    "reserved": "reserved",
    "separado": "reserved",
    "sold": "sold",
    "vendido": "sold",
}
STATUS_LABELS = {
    "available": "Disponible",
    "reserved": "Separado",
    "sold": "Vendido",
    "consultar": "Consultar",
}
PROJECT_STATUS_LABELS = {
    "planning": "Próximamente",
    "pre_sale": "Preventa",
    "presale": "Preventa",
    "active": "En venta",
    "under_construction": "En construcción",
    "completed": "Entregado",
    "sold_out": "Vendido",
}
HIDDEN_PROJECT_STATUSES = {"archived", "cancelled", "draft", "private"}

RATE_PER_IP = 5           # leads per IP per window
RATE_WINDOW_S = 15 * 60
RATE_GLOBAL_PER_DAY = 200


def _enabled() -> bool:
    try:
        from app.edition import is_maxine

        return bool(is_maxine())
    except Exception:
        return False


def _require_enabled() -> None:
    if not _enabled():
        raise HTTPException(404, "No encontrado")


def _ensure_public_schema(conn) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS cf_public_profile (
            project_id TEXT PRIMARY KEY,
            published INTEGER NOT NULL DEFAULT 1,
            tagline TEXT,
            public_description TEXT,
            highlights TEXT,
            show_prices INTEGER NOT NULL DEFAULT 0,
            price_note TEXT,
            whatsapp TEXT,
            sort_order INTEGER DEFAULT 100,
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS cf_public_lot_flags (
            lot_id TEXT PRIMARY KEY,
            show_price INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS cf_public_lead_hits (
            ip_hash TEXT NOT NULL,
            ts REAL NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_cf_public_lead_hits ON cf_public_lead_hits(ip_hash, ts);
        """
    )
    cols = {r[1] for r in conn.execute("PRAGMA table_info(cf_public_profile)")}
    if "unit_label" not in cols:
        conn.execute("ALTER TABLE cf_public_profile ADD COLUMN unit_label TEXT")
        conn.commit()


def _conn():
    conn = get_db()
    _ensure_public_schema(conn)
    return conn


def slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "proyecto"


def _public_status(raw: Optional[str]) -> str:
    return _STATUS_MAP.get((raw or "").strip().lower(), "consultar")


def _whatsapp_number(profile: Optional[dict]) -> Optional[str]:
    raw = ((profile or {}).get("whatsapp") or os.getenv("MAXINE_SALES_WHATSAPP", "")).strip()
    digits = re.sub(r"\D", "", raw)
    return digits if len(digits) >= 8 else None


def _num(value):
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _profile(conn, project_id: str) -> dict:
    row = conn.execute("SELECT * FROM cf_public_profile WHERE project_id = ?", (project_id,)).fetchone()
    return dict(row) if row else {}


def _visible_projects(conn) -> list[dict]:
    out = []
    for row in conn.execute("SELECT * FROM cf_projects ORDER BY created_at"):
        proj = dict(row)
        if (proj.get("status") or "").lower() in HIDDEN_PROJECT_STATUSES:
            continue
        prof = _profile(conn, proj["id"])
        if prof and not prof.get("published", 1):
            continue
        proj["_profile"] = prof
        proj["_slug"] = slugify(proj.get("slug") or proj.get("name") or "")
        out.append(proj)
    out.sort(key=lambda p: (p["_profile"].get("sort_order") or 100, p.get("created_at") or ""))
    return out


def _find_project(conn, slug: str) -> dict:
    key = slugify(slug)
    for proj in _visible_projects(conn):
        if proj["_slug"] == key:
            return proj
    raise HTTPException(404, "Proyecto no encontrado")


def _lot_counts(conn, project_id: str) -> dict:
    counts = {s: 0 for s in PUBLIC_STATUSES}
    for row in conn.execute("SELECT status FROM cf_lots WHERE project_id = ?", (project_id,)):
        counts[_public_status(row["status"])] += 1
    return counts


def _public_project(conn, proj: dict, detail: bool = False) -> dict:
    prof = proj.get("_profile") or {}
    counts = _lot_counts(conn, proj["id"])
    total = sum(counts.values())
    highlights = []
    try:
        highlights = [str(h) for h in json.loads(prof.get("highlights") or "[]") if str(h).strip()]
    except Exception:
        highlights = []
    out = {
        "slug": proj["_slug"],
        "name": proj.get("name"),
        "location": proj.get("location"),
        "status": PROJECT_STATUS_LABELS.get((proj.get("status") or "").lower(), "En venta"),
        "tagline": prof.get("tagline") or None,
        "description": prof.get("public_description") or None,
        "highlights": highlights,
        "unit_label": (prof.get("unit_label") or "Lote").strip()[:20] or "Lote",
        "total_units": total or proj.get("total_lots") or 0,
        "counts": counts,
        "price_note": (prof.get("price_note") or None) if prof.get("show_prices") else None,
        "whatsapp": _whatsapp_number(prof),
    }
    if detail:
        lat, lng = _num(proj.get("latitude")), _num(proj.get("longitude"))
        out["map"] = {"lat": lat, "lng": lng} if lat is not None and lng is not None else None
    return out


def _public_lots(conn, proj: dict) -> list[dict]:
    show_project_prices = bool((proj.get("_profile") or {}).get("show_prices"))
    flags = {
        r["lot_id"]: bool(r["show_price"])
        for r in conn.execute("SELECT lot_id, show_price FROM cf_public_lot_flags")
    }
    phases = {
        r["id"]: r["name"]
        for r in conn.execute("SELECT id, name FROM cf_phases WHERE project_id = ?", (proj["id"],))
    }
    lots = []
    for row in conn.execute(
        "SELECT id, phase_id, lot_number, block, area_m2, frontage_m, depth_m, orientation, "
        "current_price, base_price, status FROM cf_lots WHERE project_id = ?",
        (proj["id"],),
    ):
        status = _public_status(row["status"])
        price = None
        if status in ("available", "consultar") and (show_project_prices or flags.get(row["id"])):
            price = _num(row["current_price"]) or _num(row["base_price"])
        lots.append({
            "number": str(row["lot_number"] or ""),
            "block": row["block"] or None,
            "phase": phases.get(row["phase_id"]) or None,
            "area_m2": _num(row["area_m2"]),
            "frontage_m": _num(row["frontage_m"]),
            "depth_m": _num(row["depth_m"]),
            "orientation": row["orientation"] or None,
            "status": status,
            "status_label": STATUS_LABELS[status],
            "price": price,
        })

    def _key(lot):
        num = lot["number"]
        return (lot["block"] or "", int(num) if num.isdigit() else 10**9, num)

    lots.sort(key=_key)
    return lots


@router.get("/projects")
def public_projects():
    _require_enabled()
    conn = _conn()
    try:
        return {"projects": [_public_project(conn, p) for p in _visible_projects(conn)],
                "instagram": "https://www.instagram.com/gacconstruye/",
                "whatsapp": _whatsapp_number(None)}
    finally:
        conn.close()


@router.get("/projects/{slug}")
def public_project(slug: str):
    _require_enabled()
    conn = _conn()
    try:
        proj = _find_project(conn, slug)
        return {"project": _public_project(conn, proj, detail=True),
                "instagram": "https://www.instagram.com/gacconstruye/"}
    finally:
        conn.close()


@router.get("/projects/{slug}/sitemap")
def public_sitemap(slug: str):
    """Live lot map: public lot fields and status only."""
    _require_enabled()
    conn = _conn()
    try:
        proj = _find_project(conn, slug)
        lots = _public_lots(conn, proj)
        return {"slug": proj["_slug"], "lots": lots, "counts": _lot_counts(conn, proj["id"]),
                "legend": STATUS_LABELS}
    finally:
        conn.close()


class PublicLead(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    phone: str = Field(..., min_length=7, max_length=30)
    email: Optional[str] = Field(None, max_length=160)
    city: Optional[str] = Field(None, max_length=80)
    lot: Optional[str] = Field(None, max_length=40)
    message: Optional[str] = Field(None, max_length=1000)
    consent: bool = False
    website: Optional[str] = Field(None, max_length=200)  # honeypot: humans never see it


def _client_ip(request: Request) -> str:
    for header in ("cf-connecting-ip", "x-real-ip"):
        value = (request.headers.get(header) or "").strip()
        if value:
            return value
    fwd = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if fwd:
        return fwd
    return request.client.host if request.client else "unknown"


def _rate_limited(conn, ip: str) -> bool:
    salt = os.getenv("MAXINE_SALES_RATE_SALT", "maxine-ventas")
    ip_hash = hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()[:32]
    now = time.time()
    conn.execute("DELETE FROM cf_public_lead_hits WHERE ts < ?", (now - 86400,))
    recent = conn.execute(
        "SELECT COUNT(*) FROM cf_public_lead_hits WHERE ip_hash = ? AND ts > ?",
        (ip_hash, now - RATE_WINDOW_S),
    ).fetchone()[0]
    total = conn.execute("SELECT COUNT(*) FROM cf_public_lead_hits").fetchone()[0]
    if recent >= RATE_PER_IP or total >= RATE_GLOBAL_PER_DAY:
        conn.commit()
        return True
    conn.execute("INSERT INTO cf_public_lead_hits (ip_hash, ts) VALUES (?, ?)", (ip_hash, now))
    conn.commit()
    return False


_OK = {"ok": True, "message": "¡Gracias! Un asesor te contactará pronto."}


@router.post("/projects/{slug}/lead", status_code=201)
def public_lead(slug: str, body: PublicLead, request: Request):
    _require_enabled()
    if (body.website or "").strip():
        return _OK  # honeypot filled: pretend success, store nothing
    if not body.consent:
        raise HTTPException(422, "Debes aceptar que te contactemos.")
    phone = re.sub(r"[^\d+]", "", body.phone)
    if len(re.sub(r"\D", "", phone)) < 7:
        raise HTTPException(422, "Revisa el número de teléfono.")
    email = (body.email or "").strip() or None
    if email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(422, "Revisa el correo.")
    conn = _conn()
    try:
        proj = _find_project(conn, slug)
        if _rate_limited(conn, _client_ip(request)):
            raise HTTPException(429, "Recibimos varios mensajes seguidos. Intenta de nuevo más tarde.")
        parts = " ".join(body.name.split()).split(" ", 1)
        first, last = parts[0][:60], (parts[1] if len(parts) > 1 else "")[:60]
        lot = (body.lot or "").strip()
        notes = f"Lead web /ventas/{proj['_slug']} — {proj.get('name')}"
        if lot:
            notes += f" — lote/unidad de interés: {lot}"
        if (body.message or "").strip():
            notes += f"\nMensaje: {body.message.strip()}"
        buyer_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO cf_buyers (id, first_name, last_name, email, phone, whatsapp, city, "
            "buyer_type, referral_source, notes, locale) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'es')",
            (buyer_id, first, last, email, phone, phone, (body.city or "").strip() or None,
             "lead", f"web ventas/{proj['_slug']}", notes),
        )
        conn.commit()
        return _OK
    finally:
        conn.close()
