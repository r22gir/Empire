"""Voice notes accumulate in one borrador until the user says listo."""
from __future__ import annotations

from app.services.voice_doc.extract import (
    DOC_LABELS,
    extract_fields,
    follow_up_question,
    merge_fields,
    missing_fields,
    propose_doc_type,
)
from app.services.voice_doc.plans import build_schedule, payment_plan_options, plan_summary
from app.services.voice_doc.store import (
    add_note,
    create_session,
    get_session,
    list_notes,
    open_session,
    render_draft_html,
    save_draft,
    save_session,
)
from app.services.voice_doc.templates import render_package_attachments


def edition_name() -> str:
    try:
        from app.edition import edition_name as current

        return current() or "workroom"
    except Exception:
        return "workroom"


def _choice_patch(choice_id: str) -> dict:
    choice = (choice_id or "").strip()
    if choice in {"T1", "T2", "T3"}:
        return {"house_type": choice, "mentions_house": True}
    if choice in {"con_acabados", "sin_acabados"}:
        return {"finishes": choice, "mentions_house": True}
    if choice in {"plan_a", "plan_b", "plan_c"}:
        return {"selected_plan": choice}
    if choice in {"12", "24", "36"}:
        return {"installments": int(choice)}
    return {}


def build_options(doc_type: str, fields: dict) -> dict | None:
    if fields.get("mentions_house") and not fields.get("house_type"):
        return {
            "kind": "house_type",
            "choices": [
                {"id": "T1", "label": "Casa tipo T1"},
                {"id": "T2", "label": "Casa tipo T2"},
                {"id": "T3", "label": "Casa tipo T3"},
            ],
        }
    if fields.get("mentions_house") and fields.get("house_type") and not fields.get("finishes"):
        return {
            "kind": "finishes",
            "choices": [
                {"id": "con_acabados", "label": "Con acabados"},
                {"id": "sin_acabados", "label": "Sin acabados"},
            ],
        }
    plan_doc = doc_type in {"reservation", "payment_plan"}
    if plan_doc and fields.get("price"):
        plans = payment_plan_options(
            price=int(fields["price"]),
            separacion=int(fields.get("separacion") or 0),
            cuota_inicial_pct=fields.get("cuota_inicial_pct"),
            installments=fields.get("installments"),
            balloon=int(fields.get("balloon") or 0),
        )
        return {
            "kind": "payment_plan",
            "choices": [
                {
                    "id": plan["id"],
                    "label": plan["label"],
                    "summary": plan["summary"],
                    "schedule": plan,
                }
                for plan in plans
            ],
        }
    if plan_doc and not fields.get("installments"):
        return {
            "kind": "installments",
            "choices": [
                {"id": "12", "label": "Saldo en 12 meses"},
                {"id": "24", "label": "Saldo en 24 meses"},
                {"id": "36", "label": "Saldo en 36 meses"},
            ],
        }
    return None


def _selected_schedule(doc_type: str, fields: dict, options: dict | None) -> dict | None:
    if doc_type not in {"reservation", "payment_plan", "quote", "invoice", "contract"}:
        return None
    if not fields.get("price"):
        return None
    if options and options.get("kind") == "payment_plan":
        selected = fields.get("selected_plan") or "plan_a"
        for choice in options["choices"]:
            if choice["id"] == selected:
                return choice["schedule"]
    if doc_type in {"reservation", "payment_plan"} and fields.get("installments"):
        schedule = build_schedule(
            price=int(fields["price"]),
            separacion=int(fields.get("separacion") or 0),
            cuota_inicial_pct=fields.get("cuota_inicial_pct"),
            installments=int(fields["installments"]),
            balloon=int(fields.get("balloon") or 0),
        )
        schedule["summary"] = plan_summary(schedule)
        return schedule
    return None


def _payload(session: dict, options, missing, schedule) -> dict:
    fields = session["fields"]
    attachments = []
    if session["doc_type"] == "reservation":
        from app.services.voice_doc.deals import placeholder_values

        attachments = render_package_attachments(placeholder_values(fields, schedule))
    return {
        "doc_type": session["doc_type"],
        "label": DOC_LABELS.get(session["doc_type"], "Documento"),
        "locale": "es-CO",
        "language": fields.get("language") or "es",
        "fields": {key: value for key, value in fields.items() if key != "raw"},
        "schedule": schedule,
        "options": options,
        "missing": missing,
        "question": follow_up_question(missing),
        "attachments": attachments,
        "sent": False,
        "auto_send": False,
        "watermark": "DRAFT",
    }


def _view(session: dict, draft: dict | None = None) -> dict:
    notes = list_notes(session["id"])
    transcript = "\n".join(note["transcript"] for note in notes)
    options = build_options(session["doc_type"], session["fields"])
    missing = missing_fields(session["doc_type"], session["fields"])
    schedule = None
    if draft and draft.get("payload"):
        schedule = draft["payload"].get("schedule")
        options = draft["payload"].get("options") or options
        missing = draft["payload"].get("missing") or missing
    else:
        schedule = _selected_schedule(session["doc_type"], session["fields"], options)
    return {
        "session_id": session["id"],
        "status": session["status"],
        "channel": session["channel"],
        "edition": session["edition"],
        "doc_type": session["doc_type"],
        "label": DOC_LABELS.get(session["doc_type"], "Documento"),
        "locale": "es-CO",
        "language": session["fields"].get("language") or "es",
        "transcript": transcript,
        "notes": notes,
        "fields": {key: value for key, value in session["fields"].items() if key != "raw"},
        "options": options,
        "missing": missing,
        "question": follow_up_question(missing),
        "schedule": schedule,
        "draft": None if draft is None else {
            "id": draft["id"],
            "status": draft["status"],
            "sent": False if not draft["sent"] else True,
            "auto_send": False,
            "preview_path": f"/api/v1/voice/documents/drafts/{draft['id']}/preview",
        },
        "sent": False,
        "auto_send": False,
        "handled": session["doc_type"] != "general",
    }


def _apply_transcript(session: dict, transcript: str, language: str | None) -> dict:
    extracted = extract_fields(transcript)
    if language:
        extracted["language"] = language
    session["fields"] = merge_fields(session["fields"], extracted)
    inferred = propose_doc_type(transcript, session["fields"], session["edition"])
    if session["doc_type"] in {None, "", "general"} or inferred != "general":
        session["doc_type"] = inferred
    add_note(session["id"], transcript, extracted.get("language") or "es")
    if session["fields"].get("ready"):
        return _close(session)
    session["status"] = "open"
    save_session(session)
    return _view(get_session(session["id"]))


def _close(session: dict) -> dict:
    options = build_options(session["doc_type"], session["fields"])
    missing = missing_fields(session["doc_type"], session["fields"])
    schedule = _selected_schedule(session["doc_type"], session["fields"], options)
    if schedule:
        schedule = dict(schedule)
        schedule["summary"] = schedule.get("summary") or ""
    payload = _payload(session, options, missing, schedule)
    notes = [note["transcript"] for note in list_notes(session["id"])]
    payload["transcript"] = "\n".join(notes)
    html = render_draft_html(payload, notes)
    draft = save_draft(session["id"], session["doc_type"], payload, html)
    session["status"] = "ready"
    save_session(session)
    view = _view(get_session(session["id"]), draft)
    view["draft"]["sent"] = False
    view["sent"] = False
    return view


def ingest_transcript(
    transcript: str,
    *,
    session_id: str | None = None,
    channel: str = "web",
    edition: str | None = None,
    language: str | None = None,
    choice_id: str | None = None,
) -> dict:
    text = (transcript or "").strip()
    if text.startswith("[STT") or text.startswith("[Transcription") or text.startswith("[Audio"):
        return {"ok": False, "handled": False, "error": text, "sent": False, "auto_send": False}
    edition = edition or edition_name()
    session = get_session(session_id) if session_id else None
    if session is None or session["status"] != "open":
        session = open_session(channel, edition) if not session_id else None
    if session is None:
        session = create_session(channel, edition, {}, "general")
    if choice_id:
        session["fields"] = merge_fields(session["fields"], _choice_patch(choice_id))
        save_session(session)
        session = get_session(session["id"])
    if not text and choice_id:
        return _view(session)
    if not text:
        return _view(session)
    return _apply_transcript(session, text, language)


def ingest_structured(fields: dict, *, channel: str = "form", edition: str | None = None, session_id: str | None = None) -> dict:
    """Form entry uses the same borrador as a voice note."""
    parts = []
    if fields.get("lot_number"):
        parts.append(f"Separar el lote {fields['lot_number']}")
    if fields.get("buyer_name"):
        parts.append(f"para {fields['buyer_name']}")
    if fields.get("price"):
        parts.append(f"precio {int(fields['price'])}")
    if fields.get("separacion"):
        parts.append(f"separación {int(fields['separacion'])}")
    if fields.get("cuota_inicial_pct") is not None:
        parts.append(f"cuota inicial {int(fields['cuota_inicial_pct'])}%")
    if fields.get("installments"):
        parts.append(f"saldo en {int(fields['installments'])} meses")
    if fields.get("balloon"):
        parts.append(f"cuota final {int(fields['balloon'])}")
    if fields.get("house_type"):
        parts.append(f"casa tipo {fields['house_type'][-1]}")
    if fields.get("finishes") == "con_acabados":
        parts.append("con acabados")
    elif fields.get("finishes") == "sin_acabados":
        parts.append("sin acabados")
    if fields.get("product_name"):
        kind = fields.get("product_kind") or "programa"
        parts.append(f"{kind} {fields['product_name']}")
    transcript = ", ".join(parts) or (fields.get("transcript") or "")
    view = ingest_transcript(transcript, session_id=session_id, channel=channel, edition=edition or edition_name())
    extra = {}
    for key in ("lot_number", "buyer_name", "buyer_email", "buyer_phone", "house_type", "finishes", "product_name", "product_kind"):
        if fields.get(key) not in (None, ""):
            extra[key] = fields[key]
    for key in ("price", "separacion", "balloon", "installments", "cuota_inicial_pct"):
        if fields.get(key) not in (None, ""):
            extra[key] = int(fields[key]) if key != "cuota_inicial_pct" else fields[key]
    if not extra or not view.get("session_id"):
        return view
    session = get_session(view["session_id"])
    if session is None or session["status"] != "open":
        return view
    session["fields"] = merge_fields(session["fields"], extra)
    if fields.get("lot_number") and (edition or edition_name()) != "amp":
        session["doc_type"] = "reservation"
    elif fields.get("product_kind") and session["doc_type"] == "general":
        session["doc_type"] = "quote"
    save_session(session)
    return _view(get_session(session["id"]))


def close_session(session_id: str) -> dict:
    session = get_session(session_id)
    if session is None:
        raise KeyError(session_id)
    session["fields"] = merge_fields(session["fields"], {"ready": True})
    return _close(session)


def format_session_reply(view: dict) -> str:
    if view.get("error"):
        return f"No pude transcribir: {view['error']}"
    lines = [
        f"Transcripción: {view.get('transcript') or ''}",
        f"Documento: {view.get('label') or 'Documento'} (borrador, es-CO).",
    ]
    options = view.get("options") or {}
    choices = options.get("choices") or []
    if choices:
        lines.append("Opciones:")
        for choice in choices[:3]:
            lines.append(f"- {choice.get('label')}: {choice.get('summary') or choice.get('id')}")
    missing = view.get("missing") or []
    if missing:
        lines.append("Falta: " + ", ".join(missing))
    if view.get("question"):
        lines.append(view["question"])
    draft = view.get("draft")
    if draft:
        lines.append("Borrador listo. DRAFT. No lo envié.")
        lines.append("Aprueba el borrador en el chat antes de descargar o enviar.")
    else:
        lines.append("Sigue hablando o escribe listo para cerrar el borrador. No envío nada solo.")
    lines.append(f"No enviado. sent={view.get('sent') is True}")
    return "\n".join(lines)


def channel_report() -> dict:
    return {
        "web": {"connected": True, "how": "Micrófono en el chat: transcribe y entra al mismo borrador."},
        "telegram": {"connected": True, "how": "Las notas de voz que ya llegan al bot usan este borrador. No se envía el PDF solo."},
        "whatsapp": {
            "connected": False,
            "how": "No hay un canal de voz entrante de WhatsApp en el código. No se creó una cuenta nueva.",
        },
        "locale": "es-CO",
        "auto_send": False,
    }
