"""Turn a submitted LuxeForge project into the Workroom records Rafael looks at.

The designer portal stores the project in ``intake_projects``. On submit this
module also writes the shared Workroom path: one ForgeCRM customer, one
LeadForge lead, and one Workroom quote draft. The quote is not sent.

The only email is an internal notice to the workroom mailbox. The customer's
address is never the recipient, and this module does not create a customer draft.
"""

from __future__ import annotations

import html
import json
import logging
import os
import threading
from typing import Any, Optional

logger = logging.getLogger(__name__)

OWNER_NOTICE_EMAIL = "workroom@empirebox.store"
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".heic", ".heif"}


def job_type_for_treatment(treatment: Optional[str]) -> str:
    text = (treatment or "").lower()
    parts = [p.strip() for p in text.replace(";", ",").split(",") if p.strip()]
    if len(parts) > 1:
        return "mixed"
    if any(k in text for k in ("drapery", "blind", "shade", "shutter", "roman")):
        return "drapery_romans"
    if "banquette" in text:
        return "banquette"
    if any(k in text for k in ("upholster", "sofa", "chair", "cushion", "seating")):
        return "soft_seating"
    if any(k in text for k in ("headboard", "bedding", "bed")):
        return "headboard"
    return "other"


def _loads(raw: Any, default: Any) -> Any:
    if isinstance(raw, (list, dict)):
        return raw
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return default


def _summary(project: dict, fabrics: list[dict]) -> str:
    rooms = _loads(project.get("rooms"), [])
    lines = [f"LuxeForge {project.get('intake_code') or project.get('id')}: {project.get('name') or 'Project'}"]
    if project.get("address"):
        lines.append(f"Address: {project['address']}")
    if project.get("treatment"):
        lines.append(f"Treatment: {project['treatment']}")
    if project.get("notes"):
        lines.append(str(project["notes"]))
    for room in rooms:
        if isinstance(room, dict):
            bits = [room.get("name") or room.get("room") or "Item", room.get("treatment") or "", room.get("description") or ""]
            lines.append("Item: " + " — ".join(b for b in bits if b))
    for fabric in fabrics:
        pref = fabric.get("fabric_preference") or ""
        name = fabric.get("fabric_name") or fabric.get("item_name") or "Fabric"
        lines.append(f"Fabric ({pref}): {name}")
        if fabric.get("client_notes"):
            lines.append(str(fabric["client_notes"]))
    text = "\n".join(lines).strip() or "LuxeForge designer intake"
    return text[:4000]


def _photo_urls(project: dict, fabrics: list[dict]) -> list[str]:
    urls: list[str] = []
    for bucket in (_loads(project.get("photos"), []), _loads(project.get("scans"), [])):
        for item in bucket:
            if isinstance(item, dict) and item.get("path"):
                urls.append(str(item["path"]))
    for fabric in fabrics:
        if fabric.get("swatch_photo_path"):
            urls.append(str(fabric["swatch_photo_path"]))
        for item in _loads(fabric.get("swatch_files"), []):
            if isinstance(item, dict) and item.get("path"):
                urls.append(str(item["path"]))
    # Lead payload cap is modest. Keep the list short; files stay on disk.
    return urls[:12]


def _quote_items(project: dict, fabrics: list[dict]) -> list[dict]:
    rooms = _loads(project.get("rooms"), [])
    items = []
    for room in rooms:
        if not isinstance(room, dict):
            continue
        label = room.get("name") or room.get("room") or "Item"
        treatment = room.get("treatment") or project.get("treatment") or ""
        description = f"{label} — {treatment}".strip(" —")
        if room.get("description"):
            description = f"{description}: {room['description']}"
        items.append({
            "description": description[:500],
            "quantity": 1,
            "unit": "ea",
            "rate": 0,
            "unit_price": 0,
            "amount": 0,
            # Not a catalog category. A $0 draft must not be priced or sent.
            "category": "intake_pending",
        })
    if not items:
        items.append({
            "description": "Scope pending — LuxeForge intake, not priced",
            "quantity": 1,
            "unit": "ea",
            "rate": 0,
            "unit_price": 0,
            "amount": 0,
            "category": "intake_pending",
        })
    return items


def _vision_configured() -> bool:
    for key in ("XAI_API_KEY", "GOOGLE_GEMINI_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY"):
        if (os.getenv(key) or "").strip():
            return True
    return False


def _is_image(filename: str, content_type: Optional[str]) -> bool:
    ext = ""
    if filename and "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
    if ext in _IMAGE_EXTS:
        return True
    return (content_type or "").lower().startswith("image/")


def analyze_intake_image(content: bytes, filename: str, content_type: Optional[str]) -> dict:
    """Owner-only photo read. Returns a small record, never raises to the caller."""
    if not _is_image(filename, content_type):
        return {"filename": filename, "status": "skipped", "detail": "Not an image"}
    if not _vision_configured():
        return {"filename": filename, "status": "unavailable", "detail": "Vision is not configured"}
    try:
        import base64
        from app.services.quote_engine.item_analyzer import analyze_photo_items_sync

        mime = content_type or "image/jpeg"
        data_uri = f"data:{mime};base64,{base64.b64encode(content).decode('ascii')}"
        result = analyze_photo_items_sync(data_uri, "")
        if not isinstance(result, dict):
            result = {"raw": str(result)[:2000]}
        result["filename"] = filename
        result["status"] = result.get("status") or "ready"
        return result
    except Exception as exc:
        logger.warning("LuxeForge photo analysis failed for %s: %s", filename, exc)
        return {"filename": filename, "status": "unavailable", "detail": "Analysis did not complete"}


def store_owner_photo_analysis(project_id: str, record: dict) -> None:
    from app.routers import intake_auth

    conn = intake_auth.get_db()
    try:
        row = conn.execute(
            "SELECT photo_analysis FROM intake_projects WHERE id = ?",
            (project_id,),
        ).fetchone()
        if not row:
            return
        current = _loads(row["photo_analysis"], [])
        if not isinstance(current, list):
            current = []
        current.append(record)
        conn.execute(
            "UPDATE intake_projects SET photo_analysis = ?, updated_at = datetime('now') WHERE id = ?",
            (json.dumps(current), project_id),
        )
        conn.commit()
    finally:
        conn.close()


def run_owner_photo_analysis(project_id: str, content: bytes, filename: str, content_type: Optional[str]) -> dict:
    record = analyze_intake_image(content, filename, content_type)
    store_owner_photo_analysis(project_id, record)
    return record


def schedule_owner_photo_analysis(project_id: str, content: bytes, filename: str, content_type: Optional[str]) -> None:
    """Run after the upload response. The designer never sees this result."""
    if not _is_image(filename, content_type):
        return

    def _run() -> None:
        try:
            run_owner_photo_analysis(project_id, content, filename, content_type)
        except Exception:
            logger.exception("Owner photo analysis failed for %s", project_id)

    threading.Thread(target=_run, name="luxeforge-photo-analysis", daemon=True).start()


async def send_owner_intake_notice(*, project: dict, user: dict, lead_id: Any, quote_id: Any, quote_number: Any) -> dict:
    """Email the workroom mailbox only. Never the customer. Not a draft."""
    from app.services.email.sender import send_email

    to = OWNER_NOTICE_EMAIL
    customer = (user.get("email") or "").strip()
    if customer.lower() == to.lower():
        # The mailbox itself submitted something. Still an internal notice.
        customer_note = "the workroom mailbox"
    else:
        customer_note = customer or "unknown"
    code = project.get("intake_code") or project.get("id")
    subject = f"LuxeForge intake {code}"
    body = (
        "<p>Internal notice for the Workroom owner. This message was not sent to the customer "
        "and it is not a draft waiting to be sent.</p>"
        f"<p><strong>{html.escape(str(project.get('name') or 'Project'))}</strong> "
        f"({html.escape(str(code))})</p>"
        f"<p>Contact: {html.escape(str(user.get('name') or ''))} "
        f"&lt;{html.escape(customer_note)}&gt;</p>"
        f"<p>LeadForge #{html.escape(str(lead_id or '—'))} · "
        f"Quote {html.escape(str(quote_number or quote_id or '—'))}</p>"
        "<p>Open Command Center → Workroom → LuxeForge Intakes.</p>"
    )
    sent = await send_email(to, subject, body)
    return {"to": to, "sent": bool(sent), "customer_emailed": False}


async def handoff_submitted_intake(project: dict, user: dict, fabrics: Optional[list[dict]] = None) -> dict:
    """Create the CRM lead and Workroom quote, then notify the owner mailbox."""
    fabrics = list(fabrics or [])
    if project.get("lead_id") and project.get("quote_id"):
        return {
            "lead_id": project.get("lead_id"),
            "customer_id": project.get("customer_id"),
            "quote_id": project.get("quote_id"),
            "quote_number": project.get("quote_number"),
            "notice": {"to": OWNER_NOTICE_EMAIL, "sent": False, "customer_emailed": False, "skipped": True},
        }

    from app.services.workroom_lead_intake import LuxeForgeHandoff, WorkroomIntake, submit_intake

    email = (user.get("email") or "").strip()
    summary = _summary(project, fabrics)
    rooms = _loads(project.get("rooms"), [])
    address = (project.get("address") or "").strip()[:200] or None
    intake = WorkroomIntake(
        full_name=((user.get("name") or project.get("name") or "Designer").strip() or "Designer")[:200],
        email=email or "unknown@invalid.example",
        phone=((user.get("phone") or "").strip()[:40] or None),
        firm_name=((user.get("company") or "").strip()[:200] or None),
        city_region=address,
        job_type=job_type_for_treatment(project.get("treatment")),
        message=summary,
        photo_urls=_photo_urls(project, fabrics),
        source="web",
        consent_contact=True,
        business="workroom",
        capture_surface="luxeforge",
        luxeforge=LuxeForgeHandoff(
            brief=summary[:2000],
            room_count=len(rooms) if isinstance(rooms, list) else None,
            photo_notes=project.get("notes"),
        ),
    )
    # Invalid designer email must not block the project row. The owner list
    # still shows the intake; the lead write is reported as an error.
    lead_id = customer_id = None
    lead_error = None
    if "@" not in email or email.lower() == OWNER_NOTICE_EMAIL:
        # A missing email cannot become a CRM row. The owner notice still goes out.
        if not email:
            lead_error = "no customer email"
    try:
        if email and "@" in email:
            created = await submit_intake(intake)
            lead_id = created.get("lead_id")
            customer_id = created.get("customer_id")
    except Exception as exc:
        lead_error = str(exc)
        logger.exception("LuxeForge lead handoff failed for %s", project.get("id"))

    quote_id = quote_number = None
    quote_error = None
    try:
        from app.services.quote_service import create_quote

        quote = create_quote({
            "customer_name": user.get("name") or project.get("name") or "Intake client",
            "customer_email": email,
            "customer_phone": user.get("phone") or "",
            "customer_address": project.get("address") or "",
            "customer_id": customer_id,
            "business_unit": "workroom",
            "project_name": project.get("name") or "LuxeForge intake",
            "project_description": summary[:2000],
            "notes": (
                f"Draft from LuxeForge {project.get('intake_code') or ''}. "
                "Not priced and not sent to the customer.\n\n"
                + summary
            )[:8000],
            "pricing_mode": "flat",
            "terms": "Draft from designer intake. Not sent.",
            "valid_days": 30,
            "line_items": _quote_items(project, fabrics),
            "rooms": rooms if isinstance(rooms, list) else [],
        })
        quote_id = (quote or {}).get("id")
        quote_number = (quote or {}).get("quote_number")
    except Exception as exc:
        quote_error = str(exc)
        logger.exception("LuxeForge quote handoff failed for %s", project.get("id"))

    notice = await send_owner_intake_notice(
        project=project,
        user=user,
        lead_id=lead_id,
        quote_id=quote_id,
        quote_number=quote_number,
    )
    return {
        "lead_id": lead_id,
        "customer_id": customer_id,
        "quote_id": quote_id,
        "quote_number": quote_number,
        "lead_error": lead_error,
        "quote_error": quote_error,
        "notice": notice,
    }
