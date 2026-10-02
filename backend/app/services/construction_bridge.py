"""ConstructionForge is Maxine's data model.

Projects, phases, lots, buyers, quotes, and payment plans are rows in
the ConstructionForge tables. Businesses, CRM, leads, and content read
and write those rows. They do not keep a second copy.
"""
from __future__ import annotations

import json
import uuid
from typing import Optional

from app.edition import is_maxine


def _db():
    from app.routers.construction import get_db
    return get_db()


def _slug_key(value: str) -> str:
    from app.services.amp_businesses import safe_slug
    return safe_slug(value or "")


def portfolio_summary() -> dict:
    conn = _db()
    try:
        projects = [dict(row) for row in conn.execute(
            "SELECT * FROM cf_projects ORDER BY name"
        ).fetchall()]
        cards = []
        for project in projects:
            pid = project["id"]
            lots = conn.execute(
                "SELECT status, COUNT(*) AS cnt FROM cf_lots WHERE project_id = ? GROUP BY status",
                (pid,),
            ).fetchall()
            by_status = {row["status"]: row["cnt"] for row in lots}
            pipeline = conn.execute(
                """
                SELECT s.status, COUNT(*) AS cnt
                FROM cf_sales s JOIN cf_lots l ON s.lot_id = l.id
                WHERE l.project_id = ? GROUP BY s.status
                """,
                (pid,),
            ).fetchall()
            due = conn.execute(
                """
                SELECT COUNT(*) AS cnt FROM cf_payments p
                JOIN cf_sales s ON p.sale_id = s.id
                JOIN cf_lots l ON s.lot_id = l.id
                WHERE l.project_id = ? AND p.status IN ('pending', 'overdue')
                """,
                (pid,),
            ).fetchone()["cnt"]
            progress = conn.execute(
                """
                SELECT AVG(c.progress_percent) AS avg_p
                FROM cf_construction c JOIN cf_lots l ON c.lot_id = l.id
                WHERE l.project_id = ?
                """,
                (pid,),
            ).fetchone()["avg_p"]
            cards.append({
                "id": pid,
                "name": project.get("name"),
                "slug": project.get("slug"),
                "location": project.get("location"),
                "status": project.get("status"),
                "currency": project.get("currency") or "COP",
                "lots_by_status": by_status,
                "lot_count": sum(by_status.values()),
                "pipeline": {row["status"]: row["cnt"] for row in pipeline},
                "payments_due": due,
                "construction_progress": None if progress is None else round(progress),
            })
        return {"model": "constructionforge", "projects": cards}
    finally:
        conn.close()


def public_portfolio_text() -> str:
    from app.services.edition_facts import public_facts_block

    try:
        summary = portfolio_summary()
    except Exception:
        summary = {"projects": []}
    lines = ["Portafolio ConstructionForge (datos ya guardados):"]
    for project in summary.get("projects") or []:
        counts = ", ".join(f"{status} {count}" for status, count in sorted((project.get("lots_by_status") or {}).items()))
        lines.append(
            f"- {project.get('name')} ({project.get('location') or 'sin lugar'}): "
            f"estado {project.get('status') or 'sin estado'}; lotes: {counts or 'ninguno'}."
        )
    block = public_facts_block()
    if block:
        lines.append(block)
    if len(lines) == 1 and not block:
        return ""
    return "\n".join(lines)


def ensure_project(
    *,
    name: str,
    slug: str,
    location: str = "",
    description: str = "",
    status: str = "planning",
    currency: str = "COP",
    total_lots: Optional[int] = None,
) -> dict:
    conn = _db()
    try:
        row = conn.execute("SELECT * FROM cf_projects WHERE slug = ?", (slug,)).fetchone()
        if row:
            conn.execute(
                """
                UPDATE cf_projects
                SET name = ?, description = ?, location = ?
                WHERE slug = ?
                """,
                (name, description or None, location or None, slug),
            )
            conn.commit()
            return dict(conn.execute("SELECT * FROM cf_projects WHERE slug = ?", (slug,)).fetchone())
        pid = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO cf_projects (
                id, name, slug, description, location, total_lots, status, currency
            ) VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                pid,
                name,
                slug,
                description or None,
                location or None,
                total_lots if total_lots is not None else 0,
                status or "planning",
                currency or "COP",
            ),
        )
        conn.commit()
        return dict(conn.execute("SELECT * FROM cf_projects WHERE id = ?", (pid,)).fetchone())
    finally:
        conn.close()


def ensure_phase(project_id: str, name: str, *, total_lots: int = 0, status: str = "planning") -> dict:
    conn = _db()
    try:
        row = conn.execute(
            "SELECT * FROM cf_phases WHERE project_id = ? AND name = ?",
            (project_id, name),
        ).fetchone()
        if row:
            return dict(row)
        phase_id = str(uuid.uuid4())
        number = conn.execute(
            "SELECT COALESCE(MAX(phase_number), 0) + 1 AS n FROM cf_phases WHERE project_id = ?",
            (project_id,),
        ).fetchone()["n"]
        conn.execute(
            """
            INSERT INTO cf_phases (id, project_id, name, phase_number, total_lots, status)
            VALUES (?,?,?,?,?,?)
            """,
            (phase_id, project_id, name, number, total_lots, status),
        )
        conn.commit()
        return dict(conn.execute("SELECT * FROM cf_phases WHERE id = ?", (phase_id,)).fetchone())
    finally:
        conn.close()


def insert_lot(
    *,
    project_id: str,
    phase_id: Optional[str],
    lot_number: str,
    status: str = "available",
    area_m2: Optional[float] = None,
    price: Optional[float] = None,
    block: Optional[str] = None,
) -> dict:
    """Insert one lot. Area and price stay NULL unless the caller passed them."""
    conn = _db()
    try:
        existing = conn.execute(
            "SELECT * FROM cf_lots WHERE project_id = ? AND lot_number = ?",
            (project_id, lot_number),
        ).fetchone()
        if existing:
            return dict(existing)
        lot_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO cf_lots (
                id, project_id, phase_id, lot_number, block, area_m2,
                base_price, current_price, status
            ) VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                lot_id,
                project_id,
                phase_id,
                lot_number,
                block,
                area_m2,
                price,
                price,
                status or "available",
            ),
        )
        conn.commit()
        return dict(conn.execute("SELECT * FROM cf_lots WHERE id = ?", (lot_id,)).fetchone())
    finally:
        conn.close()


def _remember_link(slug: str, project_id: str, brand: str = "") -> None:
    from app.services import amp_businesses

    path_profile = amp_businesses.business_dir(slug) / "business.json"
    if path_profile.is_file():
        data = json.loads(path_profile.read_text(encoding="utf-8"))
        data["cf_project_id"] = project_id
        data["model"] = "constructionforge"
        if brand:
            data["brand"] = brand
        amp_businesses._write_profile(slug, data)
    registry = amp_businesses._load_registry()
    changed = False
    for row in registry["businesses"]:
        if row.get("slug") == slug:
            row["cf_project_id"] = project_id
            row["model"] = "constructionforge"
            if brand and not row.get("brand"):
                row["brand"] = brand
            changed = True
    if changed:
        amp_businesses._save_registry(registry)


def attach_project(profile: dict, answers: Optional[dict] = None) -> dict:
    """Make sure a Maxine business is a ConstructionForge project."""
    if not is_maxine():
        return profile
    answers = answers or {}
    location = " ".join(
        part for part in (answers.get("city"), answers.get("country")) if part
    ).strip()
    project = ensure_project(
        name=profile.get("trade_name") or profile.get("name") or "Proyecto",
        slug=profile["slug"],
        location=location,
        description=profile.get("description") or "",
        currency=profile.get("currency") or "COP",
    )
    _remember_link(profile["slug"], project["id"], brand=str(profile.get("brand") or answers.get("brand") or ""))
    profile["cf_project_id"] = project["id"]
    profile["model"] = "constructionforge"
    return profile


def materialize_from_interview(created: dict, answers: dict) -> dict:
    """Interview finish: project, one phase, and only the lots the owner listed."""
    if not is_maxine():
        return created
    created = attach_project(created, answers)
    project_id = created["cf_project_id"]
    lots = answers.get("lots") if isinstance(answers.get("lots"), list) else []
    phase_name = (answers.get("phase_name") or "").strip() or "Etapa inicial"
    phase = ensure_phase(project_id, phase_name, total_lots=len(lots), status="planning")
    stored = []
    for lot in lots:
        if not isinstance(lot, dict) or not lot.get("lot_number"):
            continue
        stored.append(insert_lot(
            project_id=project_id,
            phase_id=phase["id"],
            lot_number=str(lot["lot_number"]),
            status=str(lot.get("status") or "available"),
            area_m2=lot.get("area_m2"),
            price=lot.get("price"),
        ))
    customer = answers.get("first_customer") if isinstance(answers.get("first_customer"), dict) else {}
    if customer.get("name"):
        upsert_buyer(
            name=customer["name"],
            email=customer.get("email") or "",
            phone=customer.get("phone") or "",
            city=answers.get("city") or "",
            notes="Primer cliente de la entrevista",
            project_id=project_id,
        )
    created["cf_phase_id"] = phase["id"]
    created["cf_lots"] = stored
    created["model"] = "constructionforge"
    return created


def project_id_for_slug(slug: str) -> Optional[str]:
    conn = _db()
    try:
        row = conn.execute("SELECT id FROM cf_projects WHERE slug = ?", (slug,)).fetchone()
        if row:
            return row["id"]
        row = conn.execute("SELECT id FROM cf_projects ORDER BY created_at LIMIT 1").fetchone()
        return row["id"] if row else None
    finally:
        conn.close()


def upsert_buyer(
    *,
    name: str,
    email: str = "",
    phone: str = "",
    city: str = "",
    notes: str = "",
    project_id: Optional[str] = None,
    source: str = "",
) -> dict:
    parts = (name or "").strip().split()
    first = parts[0] if parts else "Contacto"
    last = " ".join(parts[1:]) if len(parts) > 1 else ""
    conn = _db()
    try:
        row = None
        if email:
            row = conn.execute(
                "SELECT * FROM cf_buyers WHERE lower(email) = ?",
                (email.strip().lower(),),
            ).fetchone()
        if row is None and phone:
            row = conn.execute("SELECT * FROM cf_buyers WHERE phone = ?", (phone,)).fetchone()
        if row:
            return dict(row)
        buyer_id = str(uuid.uuid4())
        note = notes or ""
        if project_id:
            note = (note + f"\nproyecto:{project_id}").strip()
        if source:
            note = (note + f"\norigen:{source}").strip()
        conn.execute(
            """
            INSERT INTO cf_buyers (
                id, first_name, last_name, email, phone, city, country, notes, locale, referral_source
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                buyer_id,
                first,
                last or "—",
                email or None,
                phone or None,
                city or None,
                "Colombia",
                note or None,
                "es",
                source or None,
            ),
        )
        conn.commit()
        return dict(conn.execute("SELECT * FROM cf_buyers WHERE id = ?", (buyer_id,)).fetchone())
    finally:
        conn.close()


def buyers_as_contacts(slug: str = "") -> list[dict]:
    project_id = project_id_for_slug(slug) if slug else None
    conn = _db()
    try:
        rows = conn.execute("SELECT * FROM cf_buyers ORDER BY created_at").fetchall()
        contacts = []
        for row in rows:
            notes = row["notes"] or ""
            if project_id and f"proyecto:{project_id}" not in notes and slug:
                # Buyers are instance-wide. Keep them; the note links a project when we have one.
                pass
            name = " ".join(part for part in (row["first_name"], row["last_name"]) if part and part != "—")
            contacts.append({
                "id": row["id"],
                "name": name,
                "email": row["email"] or "",
                "phone": row["phone"] or "",
                "fields_json": json.dumps({"model": "constructionforge", "city": row["city"] or ""}, ensure_ascii=False),
                "cf_buyer_id": row["id"],
            })
        return contacts
    finally:
        conn.close()


def lead_to_buyer(lead: dict) -> dict:
    name = " ".join(part for part in (lead.get("first_name"), lead.get("last_name")) if part).strip()
    if not name:
        name = lead.get("company") or "Prospecto"
    buyer = upsert_buyer(
        name=name,
        email=lead.get("email") or "",
        phone=lead.get("phone") or "",
        city=lead.get("city") or "",
        notes=lead.get("notes") or "",
        source=lead.get("source") or "lead",
    )
    return {
        "lead": {
            "id": buyer["id"],
            "first_name": buyer["first_name"],
            "last_name": buyer["last_name"],
            "email": buyer.get("email"),
            "phone": buyer.get("phone"),
            "status": "new",
            "model": "constructionforge",
        },
        "model": "constructionforge",
    }


def list_leads_from_buyers() -> dict:
    contacts = buyers_as_contacts()
    leads = []
    for contact in contacts:
        parts = (contact["name"] or "").split()
        leads.append({
            "id": contact["id"],
            "first_name": parts[0] if parts else "",
            "last_name": " ".join(parts[1:]),
            "email": contact["email"],
            "phone": contact["phone"],
            "status": "new",
            "model": "constructionforge",
        })
    return {"leads": leads, "total": len(leads)}


def list_contacts_from_buyers() -> dict:
    contacts = []
    for contact in buyers_as_contacts():
        contacts.append({
            "id": contact["id"],
            "name": contact["name"],
            "type": "client",
            "email": contact["email"],
            "phone": contact["phone"],
            "notes": "",
            "model": "constructionforge",
        })
    return {"contacts": contacts, "total": len(contacts)}


def contact_as_buyer(contact: dict) -> dict:
    buyer = upsert_buyer(
        name=contact.get("name") or "Contacto",
        email=contact.get("email") or "",
        phone=contact.get("phone") or "",
        notes=contact.get("notes") or "",
        source="crm",
    )
    return {
        "id": buyer["id"],
        "name": contact.get("name"),
        "type": contact.get("type") or "client",
        "email": buyer.get("email"),
        "phone": buyer.get("phone"),
        "model": "constructionforge",
    }


def _find_lot(conn, lot_id: Optional[str] = None, lot_number: Optional[str] = None, project_id: Optional[str] = None):
    if lot_id:
        return conn.execute("SELECT * FROM cf_lots WHERE id = ?", (lot_id,)).fetchone()
    if lot_number and project_id:
        return conn.execute(
            "SELECT * FROM cf_lots WHERE project_id = ? AND lot_number = ?",
            (project_id, str(lot_number)),
        ).fetchone()
    if lot_number:
        return conn.execute("SELECT * FROM cf_lots WHERE lot_number = ?", (str(lot_number),)).fetchone()
    return None


def create_payment_plan(
    *,
    amount: float,
    currency: str = "COP",
    buyer_name: str,
    buyer_email: str = "",
    buyer_phone: str = "",
    lot_id: Optional[str] = None,
    lot_number: Optional[str] = None,
    project_slug: str = "",
    installments: int = 1,
    notes: str = "",
) -> dict:
    """A quote or payment plan is a cf_sales row plus cf_payments. COP by default.

    The lot must already exist. Amount must be the one the owner typed.
    """
    if amount is None or float(amount) <= 0:
        raise ValueError("Indica el valor en COP. No invento precios.")
    project_id = project_id_for_slug(project_slug) if project_slug else None
    conn = _db()
    try:
        lot = _find_lot(conn, lot_id=lot_id, lot_number=lot_number, project_id=project_id)
        if not lot:
            raise ValueError("Indica un lote que ya exista. No creo lotes ni áreas.")
        buyer = upsert_buyer(name=buyer_name, email=buyer_email, phone=buyer_phone, project_id=lot["project_id"])
        sale_id = str(uuid.uuid4())
        count = max(1, int(installments or 1))
        each = round(float(amount) / count, 2)
        plan = {"currency": currency or "COP", "installments": count, "amount_each": each}
        conn.execute(
            """
            INSERT INTO cf_sales (
                id, lot_id, buyer_id, sale_price, currency, payment_plan, status, notes
            ) VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                sale_id,
                lot["id"],
                buyer["id"],
                float(amount),
                currency or "COP",
                json.dumps(plan),
                "pending",
                notes or None,
            ),
        )
        payments = []
        for number in range(1, count + 1):
            payment_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO cf_payments (
                    id, sale_id, buyer_id, amount, currency, installment_number, status, notes
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    payment_id,
                    sale_id,
                    buyer["id"],
                    each,
                    currency or "COP",
                    number,
                    "pending",
                    notes or None,
                ),
            )
            payments.append({"id": payment_id, "installment_number": number, "amount": each, "status": "pending"})
        conn.execute(
            "UPDATE cf_lots SET status = CASE WHEN status = 'available' THEN 'reserved' ELSE status END WHERE id = ?",
            (lot["id"],),
        )
        conn.commit()
        return {
            "model": "constructionforge",
            "id": sale_id,
            "cf_sale_id": sale_id,
            "lot_id": lot["id"],
            "buyer_id": buyer["id"],
            "sale_price": float(amount),
            "currency": currency or "COP",
            "payments": payments,
            "quote_number": sale_id[:8],
            "status": "draft",
            "total": float(amount),
            "customer_name": buyer_name,
            "project_name": lot_number or lot["lot_number"],
        }
    finally:
        conn.close()


def quote_payload_to_sale(payload: dict) -> dict:
    total = payload.get("total")
    if not total:
        items = payload.get("line_items") or payload.get("items") or []
        summed = 0.0
        for item in items:
            if isinstance(item, dict) and item.get("total"):
                summed += float(item["total"])
            elif isinstance(item, dict) and item.get("unit_price") and item.get("quantity"):
                summed += float(item["unit_price"]) * float(item["quantity"])
        total = summed or None
    notes = payload.get("notes") or ""
    lot_number = payload.get("lot_number")
    if not lot_number and notes.lower().startswith("lote "):
        lot_number = notes.split()[1]
    return create_payment_plan(
        amount=float(total) if total else 0,
        currency="COP",
        buyer_name=payload.get("customer_name") or "Comprador",
        buyer_email=payload.get("customer_email") or "",
        buyer_phone=payload.get("customer_phone") or "",
        lot_number=str(lot_number) if lot_number else None,
        project_slug=payload.get("project_slug") or payload.get("business_unit") or "",
        notes=notes,
    )


def list_quotes_from_sales() -> dict:
    conn = _db()
    try:
        rows = conn.execute(
            """
            SELECT s.*, b.first_name, b.last_name, l.lot_number, p.name AS project_name
            FROM cf_sales s
            JOIN cf_buyers b ON s.buyer_id = b.id
            JOIN cf_lots l ON s.lot_id = l.id
            JOIN cf_projects p ON l.project_id = p.id
            ORDER BY s.created_at DESC
            """
        ).fetchall()
        quotes = []
        for row in rows:
            quotes.append({
                "id": row["id"],
                "quote_number": row["id"][:8],
                "customer_name": " ".join(part for part in (row["first_name"], row["last_name"]) if part and part != "—"),
                "project_name": row["project_name"],
                "status": row["status"],
                "total": row["sale_price"],
                "currency": row["currency"] or "COP",
                "pricing_mode": "flat",
                "model": "constructionforge",
                "lot_number": row["lot_number"],
            })
        return {"quotes": quotes, "count": len(quotes), "total": len(quotes)}
    finally:
        conn.close()
