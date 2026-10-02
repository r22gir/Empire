"""Turn a submitted LuxeForge project into the Workroom records Rafael looks at.

The designer portal stores the project in ``intake_projects``. On submit this
module also writes the shared Workroom path: one ForgeCRM customer, one
LeadForge lead, and one Workroom quote draft in ``quotes_v2``. Fabric details
and photos are attached to that draft. The quote is not sent, and it is not
flagged as a test quote, so it stays in the normal Quotes list.

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
_ANALYSIS_START = "--- owner photo notes ---"
_ANALYSIS_END = "--- end owner photo notes ---"


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
    for fabric in fabrics:
        pref = fabric.get("fabric_preference") or "unspecified"
        name = fabric.get("fabric_name") or fabric.get("item_name") or "Fabric"
        room = fabric.get("room_name") or ""
        description = f"Fabric ({pref}): {name}"
        if room:
            description = f"{room} — {description}"
        if fabric.get("client_notes"):
            description = f"{description} — {fabric['client_notes']}"
        names = []
        for swatch in _loads(fabric.get("swatch_files"), []):
            if isinstance(swatch, dict) and swatch.get("original_name"):
                names.append(str(swatch["original_name"]))
        if names:
            description = f"{description} · files: {', '.join(names)}"
        items.append({
            "description": description[:500],
            "quantity": 1,
            "unit": "ea",
            "rate": 0,
            "unit_price": 0,
            "amount": 0,
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


def _disk_name(entry: dict) -> str:
    filename = str(entry.get("filename") or "").strip()
    if filename:
        return os.path.basename(filename.replace("\\", "/"))
    path = str(entry.get("path") or "").split("?", 1)[0].strip()
    if path:
        return os.path.basename(path.replace("\\", "/"))
    return ""


def _collect_files(project: dict, fabrics: list[dict]) -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()

    def add(entry: Any, kind: str) -> None:
        if not isinstance(entry, dict):
            return
        name = _disk_name(entry)
        path = str(entry.get("path") or "").strip()
        key = name or path
        if not key or key in seen:
            return
        seen.add(key)
        rows.append({
            "filename": name,
            "path": path,
            "original_name": entry.get("original_name") or name or kind,
            "content_type": entry.get("content_type"),
            "uploaded_at": entry.get("uploaded_at") or "",
            "kind": kind,
        })

    for item in _loads(project.get("photos"), []):
        add(item, "photo")
    for item in _loads(project.get("scans"), []):
        add(item, "scan")
    for fabric in fabrics:
        if fabric.get("swatch_photo_path"):
            add({
                "path": fabric.get("swatch_photo_path"),
                "original_name": fabric.get("fabric_name") or "swatch",
            }, "swatch")
        for item in _loads(fabric.get("swatch_files"), []):
            add(item, "swatch")
    return rows


def _file_note_lines(project: dict, fabrics: list[dict]) -> list[str]:
    project_id = str(project.get("id") or "")
    lines = []
    for entry in _collect_files(project, fabrics):
        loc = entry["path"]
        if not loc and entry["filename"] and project_id:
            loc = f"/intake_uploads/{project_id}/{entry['filename']}"
        label = str(entry["original_name"] or entry["filename"] or entry["kind"])
        lines.append(f"{entry['kind']}: {label}" + (f" {loc}" if loc else ""))
    return lines


def _useful_analysis(records: Any) -> list[dict]:
    loaded = _loads(records, [])
    if not isinstance(loaded, list):
        return []
    useful = []
    for rec in loaded:
        if isinstance(rec, dict) and (rec.get("overall_notes") or rec.get("items")):
            useful.append(rec)
    return useful


def _merge_analysis_notes(existing: str, records: Any) -> str:
    """Replace the owner-only analysis section. The designer portal never reads this."""
    text = existing or ""
    if _ANALYSIS_START in text and _ANALYSIS_END in text:
        pre, rest = text.split(_ANALYSIS_START, 1)
        _section, post = rest.split(_ANALYSIS_END, 1)
        text = (pre.rstrip() + "\n\n" + post.lstrip()).strip()
    lines = []
    for rec in _useful_analysis(records):
        name = rec.get("filename") or "photo"
        notes = str(rec.get("overall_notes") or "").strip()
        line = f"- {name}"
        if notes:
            line += f": {notes}"
        lines.append(line)
        if rec.get("items"):
            lines.append("  " + json.dumps(rec["items"], default=str)[:800])
    if not lines:
        return text
    section = (
        f"{_ANALYSIS_START}\n"
        "Owner only. Not shown to the designer.\n"
        + "\n".join(lines)
        + f"\n{_ANALYSIS_END}"
    )
    return (text + "\n\n" + section).strip() if text else section


def _fresh_photo_analysis(project: dict) -> Any:
    project_id = project.get("id")
    if not project_id:
        return project.get("photo_analysis")
    try:
        from app.routers import intake_auth

        conn = intake_auth.get_db()
        try:
            row = conn.execute(
                "SELECT photo_analysis FROM intake_projects WHERE id = ?",
                (project_id,),
            ).fetchone()
        finally:
            conn.close()
        if row and row["photo_analysis"]:
            return row["photo_analysis"]
    except Exception:
        logger.exception("Could not read photo analysis for %s", project_id)
    return project.get("photo_analysis")


def _quote_notes(project: dict, fabrics: list[dict], analysis: Any) -> str:
    summary = _summary(project, fabrics)
    notes = (
        f"Draft from LuxeForge {project.get('intake_code') or ''}. "
        "Not priced and not sent to the customer.\n\n"
        + summary
    )
    file_lines = _file_note_lines(project, fabrics)
    if file_lines:
        notes += "\n\nFiles:\n" + "\n".join(f"- {line}" for line in file_lines)
    return _merge_analysis_notes(notes, analysis)[:8000]


def attach_intake_files_to_quote(quote_id: str, project: dict, fabrics: list[dict]) -> list[dict]:
    """Copy intake images onto the quote so Quote Review can show them.

    Image bytes land in the quote photo folder and in ``photos_json``.
    Other files stay on their intake paths and are named in the quote notes.
    """
    import shutil
    from pathlib import Path

    from app.routers import intake_auth

    project_id = str(project.get("id") or "")
    uploads = Path(intake_auth.UPLOADS_DIR) / project_id
    dest_dir = Path(intake_auth.PHOTOS_DIR) / "quote" / str(quote_id)
    photos: list[dict] = []
    for entry in _collect_files(project, fabrics):
        src_name = entry["filename"]
        if not src_name or not _is_image(src_name, entry.get("content_type")):
            continue
        src = uploads / src_name
        if not src.is_file():
            logger.warning("Intake file missing for quote %s: %s", quote_id, src)
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_name = f"intake_{src_name}"
        dest_path = dest_dir / dest_name
        shutil.copy2(src, dest_path)
        meta = {
            "original_name": entry["original_name"],
            "source": "intake",
            "size": dest_path.stat().st_size,
            "content_type": entry.get("content_type") or "",
            "uploaded_at": entry.get("uploaded_at") or "",
            "entity_type": "quote",
            "entity_id": quote_id,
            "intake_project_id": project_id,
            "kind": entry["kind"],
        }
        (dest_dir / f"{dest_name}.meta.json").write_text(json.dumps(meta), encoding="utf-8")
        url = f"/api/v1/photos/serve/quote/{quote_id}/{dest_name}"
        photos.append({
            "filename": dest_name,
            "path": url,
            "url": url,
            "original_name": entry["original_name"],
            "source": "intake",
            "uploaded_at": entry.get("uploaded_at") or "",
        })
    if photos:
        from app.services.quote_service import update_quote

        update_quote(quote_id, {"photos": photos})
    return photos


def _push_analysis_to_linked_quote(project_id: str) -> None:
    from app.routers import intake_auth
    from app.services.quote_service import get_quote, update_quote

    conn = intake_auth.get_db()
    try:
        row = conn.execute(
            "SELECT quote_id, photo_analysis FROM intake_projects WHERE id = ?",
            (project_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row or not row["quote_id"]:
        return
    quote = get_quote(row["quote_id"])
    if not quote:
        return
    notes = _merge_analysis_notes(quote.get("notes") or "", row["photo_analysis"])
    if notes != (quote.get("notes") or ""):
        update_quote(row["quote_id"], {"notes": notes[:8000]})


def _remember_handoff(project_id: str, lead_id: Any, customer_id: Any, quote_id: Any, quote_number: Any) -> None:
    if not project_id:
        return
    from app.routers import intake_auth

    conn = intake_auth.get_db()
    try:
        conn.execute(
            """UPDATE intake_projects
               SET lead_id = COALESCE(?, lead_id),
                   customer_id = COALESCE(?, customer_id),
                   quote_id = COALESCE(?, quote_id),
                   quote_number = COALESCE(?, quote_number),
                   updated_at = datetime('now')
               WHERE id = ?""",
            (lead_id, customer_id, quote_id, quote_number, project_id),
        )
        conn.commit()
    finally:
        conn.close()


def _keep_quote_visible(quote_id: str) -> None:
    """A designer intake is a real draft. The Quotes list hides is_test=1."""
    from app.services.quote_service import set_quote_test_flag

    set_quote_test_flag(quote_id, False, changed_by="luxeforge_intake")


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
    try:
        _push_analysis_to_linked_quote(project_id)
    except Exception:
        logger.exception("Could not copy photo analysis onto the quote for %s", project_id)


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
        "<p>Open Command Center → Workroom → Quotes. "
        "The draft is in that list, with the fabric details and photos. "
        "It has not been sent.</p>"
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
    # Invalid designer email must not block the project row. The Workroom
    # quote draft is still created; the lead write is reported as an error.
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

        analysis = _fresh_photo_analysis(project)
        quote = create_quote({
            "customer_name": user.get("name") or project.get("name") or "Intake client",
            "customer_email": email,
            "customer_phone": user.get("phone") or "",
            "customer_address": project.get("address") or "",
            "business_unit": "workroom",
            "project_name": project.get("name") or "LuxeForge intake",
            "project_description": summary[:2000],
            "notes": _quote_notes(project, fabrics, analysis),
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

    if quote_id:
        try:
            _keep_quote_visible(quote_id)
            attach_intake_files_to_quote(quote_id, project, fabrics)
            if customer_id:
                from app.services.quote_service import update_quote
                update_quote(quote_id, {"customer_id": customer_id})
            _remember_handoff(project.get("id"), lead_id, customer_id, quote_id, quote_number)
            _push_analysis_to_linked_quote(str(project.get("id") or ""))
        except Exception:
            logger.exception("LuxeForge quote attachments failed for %s", project.get("id"))

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
