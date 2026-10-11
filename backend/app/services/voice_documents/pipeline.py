"""Orchestrate transcript → extraction → draft document. Never sends."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from app.services.voice_documents.edition import EditionConfig, get_edition
from app.services.voice_documents.email_format import render_draft_email
from app.services.voice_documents.extract import (
    extract_transcript,
    is_done_utterance,
    merge_extractions,
)
from app.services.voice_documents.kinds import ensure_handlers_loaded, get_handler
from app.services.voice_documents.send_gate import DraftSendBlocked, assert_may_send
from app.services.voice_documents.session import (
    VoiceSession,
    get_session,
    open_session,
    save_session,
)

logger = logging.getLogger("voice_documents.pipeline")


def _apply_overrides(extraction, overrides: dict):
    if not extraction.items or not overrides:
        return extraction
    item = extraction.items[0]
    fabric = overrides.get("fabric")
    if fabric in ("com", "workroom"):
        item.fabric_mode = fabric
        if fabric == "com" and not item.fabric_name:
            item.fabric_name = "supplied"
    welt = overrides.get("welt")
    if welt in ("none", "self", "contrast"):
        item.welt = welt
    if overrides.get("seat_sections"):
        item.seat_sections = int(overrides["seat_sections"])
    if overrides.get("back_sections"):
        item.back_sections = int(overrides["back_sections"])
    return extraction


def _remember(session_id: str, transcript: str, reply: str) -> None:
    """Best-effort copy into the existing voice transcript store."""
    try:
        from app.services.max.voice_transcript import VoiceTranscript

        note = VoiceTranscript(f"doc-{session_id}", user="founder")
        note.add_user(transcript)
        note.add_assistant(reply)
    except Exception:
        logger.debug("voice transcript record skipped", exc_info=True)


def _reply(result: dict) -> str:
    lines = [f"Transcript: {result.get('latest_transcript') or ''}"]
    brand = result.get("client_brand") or ""
    if brand:
        lines.append(f"Brand: {brand}")
    quote_no = result.get("quote_number") or ""
    status = result.get("quote_status") or result.get("status") or "draft"
    if quote_no:
        lines.append(f"Draft {quote_no} ({status}). Not sent.")
    for item in result.get("line_items") or []:
        amount = item.get("amount")
        try:
            amount_s = f"${float(amount):,.2f}"
        except (TypeError, ValueError):
            amount_s = ""
        lines.append(f"{item.get('description')}: {amount_s}".rstrip())
    if result.get("total") is not None:
        lines.append(f"Total: ${float(result['total']):,.2f}")
    drawing = result.get("drawing") or {}
    fab = drawing.get("fabrication") or {}
    if fab.get("usable_seat_in") is not None and fab.get("overall_depth_in"):
        lines.append(
            "Drawing: usable seat "
            f"{fab['usable_seat_in']:g} in "
            f"(depth {fab['overall_depth_in']:g} minus back {fab['back_thickness_in']:g}). "
            f"Cushion {fab['seat_cushion_thickness_in']:g} in. "
            f"Overhang {fab['overhang_in']:g} in. "
            + ("Back vertical." if fab.get("vertical_back") else f"Back raked {fab['back_angle_deg']:g} deg.")
        )
    missing = result.get("missing") or []
    if missing:
        lines.append("Missing:")
        for row in missing:
            lines.append(f"- {row.get('label')}")
    options = result.get("options") or []
    if options:
        lines.append("Choices:")
        for opt in options:
            labels = ", ".join(c.get("label") or "" for c in opt.get("choices") or [])
            lines.append(f"- {opt.get('prompt')}: {labels}")
    if result.get("send_requested"):
        lines.append("Send was asked and blocked. Nothing is emailed until you confirm send after done.")
    elif result.get("status") == "finalized":
        lines.append("Draft finished. It is still not emailed.")
    else:
        lines.append("Say done when this draft is finished. Nothing is emailed until you confirm send.")
    if result.get("stub"):
        lines.append(result.get("summary") or "This document type is stubbed for this edition.")
    return "\n".join(lines)


def _assemble(session: VoiceSession) -> dict[str, Any]:
    ensure_handlers_loaded()
    edition: EditionConfig = get_edition(session.edition_id)
    parts = [extract_transcript(text) for text in session.transcripts]
    extraction = merge_extractions(parts) if parts else extract_transcript("")
    extraction = _apply_overrides(extraction, session.overrides)
    kind = extraction.document_kind if edition.allows(extraction.document_kind) else edition.default_document_kind
    handler = get_handler(kind) or get_handler(edition.default_document_kind)
    doc, quote_id = handler(extraction, edition, session.quote_id)
    if quote_id:
        session.quote_id = quote_id
    payload = doc.payload or {}
    if edition.rate_adapter == "workroom":
        from app.services.voice_documents.adapters.workroom import missing_and_options

        missing, options = missing_and_options(extraction)
        missing = list(missing) + list(payload.get("price_missing") or [])
    else:
        missing = []
        if not extraction.client_name:
            missing.append({"id": "client", "label": "Client name"})
        options = []
    line_items = payload.get("line_items") or []
    total = payload.get("total") if payload.get("total") is not None else 0
    email = {"plain_text": "", "html": "", "sent": False}
    if line_items:
        email = render_draft_email(
            line_items=line_items,
            total=float(total or 0),
            recipient_name=payload.get("customer_name") or extraction.client_name or None,
            billed_by=payload.get("billed_by"),
        )
    if session.status != "finalized" and extraction.done:
        session.status = "finalized"
    result = {
        "handled": True,
        "session_id": session.id,
        "edition": edition.edition_id,
        "document_kind": doc.kind,
        "status": "finalized" if session.status == "finalized" else "accumulating",
        "sent": False,
        "send_requested": bool(session.send_requested),
        "stub": bool(doc.stub),
        "summary": doc.summary,
        "transcript": extraction.transcript,
        "latest_transcript": session.transcripts[-1] if session.transcripts else "",
        "extraction": extraction.to_dict(),
        "missing": missing,
        "options": options,
        "quote_id": payload.get("quote_id") or session.quote_id,
        "quote_number": payload.get("quote_number"),
        "quote_status": payload.get("quote_status") or "draft",
        "total": payload.get("total"),
        "line_items": line_items,
        "drawing": payload.get("drawing") or {},
        "client_brand": payload.get("client_brand") or edition.client_brand_default,
        "billed_by": payload.get("billed_by"),
        "customer_name": payload.get("customer_name") or extraction.client_name,
        "email_preview": email,
        "persisted": doc.persisted,
    }
    result["reply_text"] = _reply(result)
    save_session(session)
    return result


def ingest_transcript(
    transcript: str,
    *,
    channel: str = "cc",
    session_key: str = "",
    edition_id: str = "workroom",
    session_id: str = "",
) -> dict[str, Any]:
    """Add one voice note to the open draft. Does not email or send."""
    text = (transcript or "").strip()
    edition = get_edition(edition_id)
    key = session_key or f"{channel}:default"
    if session_id:
        session = get_session(session_id)
        if session is None:
            session = open_session(key=key, edition_id=edition.edition_id)
    else:
        session = open_session(key=key, edition_id=edition.edition_id)
    if session.status == "finalized":
        probe = extract_transcript(text)
        if probe.done and not probe.items:
            return {
                "handled": False,
                "sent": False,
                "transcript": text,
                "reply_text": "That draft is already finished. Start the next one with the job.",
            }
        session = VoiceSession(id=_new_id(), key=key, edition_id=edition.edition_id)
        save_session(session)

    probe = extract_transcript(text)
    if not session.transcripts and not probe.document_intent and not probe.done:
        return {
            "handled": False,
            "sent": False,
            "transcript": text,
            "session_id": session.id,
            "reply_text": "",
        }
    if not text:
        return {"handled": False, "sent": False, "transcript": "", "reply_text": "No transcript."}

    session.transcripts.append(text)
    if probe.send_requested:
        session.send_requested = True
    if probe.done or is_done_utterance(text):
        session.status = "finalized"
    save_session(session)
    result = _assemble(session)
    result["sent"] = False
    _remember(session.id, text, result.get("reply_text") or "")
    return result


def _new_id() -> str:
    import uuid
    return uuid.uuid4().hex[:12]


def choose_option(session_id: str, option_id: str, choice_id: str) -> dict[str, Any]:
    session = get_session(session_id)
    if session is None:
        return {"handled": False, "sent": False, "reply_text": "No draft."}
    session.overrides[option_id] = choice_id
    save_session(session)
    result = _assemble(session)
    result["sent"] = False
    return result


def ingest_telegram_voice_transcript(transcript: str, chat_id: str) -> dict[str, Any]:
    """Telegram voice notes enter the same pipeline as Command Center hold-to-talk."""
    return ingest_transcript(
        transcript,
        channel="telegram",
        session_key=f"telegram:{chat_id or 'unknown'}",
        edition_id="workroom",
    )


async def ingest_audio(
    audio_path: str | Path,
    *,
    channel: str = "cc",
    session_key: str = "",
    edition_id: str = "workroom",
    session_id: str = "",
    language: str = "en",
) -> dict[str, Any]:
    """Transcribe with the existing STT service, then run the document pipeline."""
    from app.services.max.stt_service import stt_service

    transcript = await stt_service.transcribe(audio_path, language=language)
    result = ingest_transcript(
        transcript,
        channel=channel,
        session_key=session_key,
        edition_id=edition_id,
        session_id=session_id,
    )
    result["transcript_raw"] = transcript
    result["sent"] = False
    return result


def prepare_send(
    session_id: str,
    *,
    confirmed: bool,
    to_email: str = "",
) -> dict[str, Any]:
    """Authorize a send. Does not call the mailer."""
    assert_may_send(confirmed=confirmed, auto_send=False)
    session = get_session(session_id)
    if session is None:
        raise DraftSendBlocked("no draft")
    if session.status != "finalized":
        raise DraftSendBlocked("say done before sending")
    assembled = _assemble(session)
    email = assembled.get("email_preview") or {}
    recipient = (to_email or "").strip()
    if not recipient and session.quote_id:
        try:
            from app.services.quote_service import get_quote

            recipient = (get_quote(session.quote_id) or {}).get("customer_email") or ""
        except Exception:
            recipient = ""
    brand = assembled.get("client_brand") or "Empire Workroom"
    number = assembled.get("quote_number") or "draft"
    return {
        "authorized": True,
        "sent": False,
        "to": recipient,
        "subject": f"Your quote {number} from {brand}",
        "html": email.get("html") or "",
        "plain_text": email.get("plain_text") or "",
        "session_id": session.id,
    }


async def dispatch_confirmed_send(
    session_id: str,
    *,
    confirmed: bool,
    to_email: str = "",
    sender: Optional[Any] = None,
) -> dict[str, Any]:
    """Send only after prepare_send allows it."""
    prepared = prepare_send(session_id, confirmed=confirmed, to_email=to_email)
    if not prepared.get("to"):
        prepared["reason"] = "no recipient"
        return prepared
    if sender is None:
        from app.services.email.sender import send_email

        sender = send_email
    outcome = sender(prepared["to"], prepared["subject"], prepared["html"])
    if hasattr(outcome, "__await__"):
        outcome = await outcome
    prepared["sent"] = bool(outcome)
    if prepared["sent"]:
        session = get_session(session_id)
        if session:
            session.sent = True
            save_session(session)
    return prepared
