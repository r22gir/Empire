"""Document handlers. Quote and drawing call the workroom adapter.

Invoice, contract, payment plan, and notes stay on the same session and
extraction. Their persistence is stubbed so a family edition can replace
the handler without a second pipeline.
"""
from __future__ import annotations

from app.services.voice_documents.edition import EditionConfig
from app.services.voice_documents.extract import Extraction
from app.services.voice_documents.kinds import DraftDocument, register_handler


def _unported(kind: str, edition: EditionConfig, extraction: Extraction) -> DraftDocument:
    return DraftDocument(
        kind=kind,
        status="stub",
        persisted=False,
        sent=False,
        stub=True,
        summary=f"{edition.label} {kind} output is not ported yet.",
        payload={"extraction": extraction.to_dict(), "edition": edition.edition_id},
    )


def handle_quote(extraction: Extraction, edition: EditionConfig, session_quote_id: str) -> tuple[DraftDocument, str]:
    if edition.rate_adapter != "workroom":
        return _unported("quote", edition, extraction), ""
    from app.services.voice_documents.adapters.workroom import build_quote_draft

    return build_quote_draft(extraction, edition, session_quote_id)


def handle_drawing(extraction: Extraction, edition: EditionConfig, session_quote_id: str) -> tuple[DraftDocument, str]:
    if edition.drawing_adapter != "workroom_bench":
        return _unported("drawing", edition, extraction), ""
    doc, quote_id = handle_quote(extraction, edition, session_quote_id)
    doc.kind = "drawing"
    return doc, quote_id


def handle_invoice(extraction: Extraction, edition: EditionConfig, session_quote_id: str) -> tuple[DraftDocument, str]:
    """Same extraction and rates as a quote. Invoice rows are not created."""
    if edition.rate_adapter != "workroom":
        return _unported("invoice", edition, extraction), ""
    doc, quote_id = handle_quote(extraction, edition, session_quote_id)
    doc.kind = "invoice"
    doc.stub = True
    doc.summary = "Invoice draft uses the quote lines. Invoice PDF persistence is not issued from voice."
    doc.payload["invoice_persistence"] = "stub"
    doc.payload["client_line_rule"] = "invoice_pdf_service.client_visible_line_description"
    return doc, quote_id


def handle_contract(extraction: Extraction, edition: EditionConfig, session_quote_id: str) -> tuple[DraftDocument, str]:
    return _unported("contract", edition, extraction), session_quote_id


def handle_payment_plan(extraction: Extraction, edition: EditionConfig, session_quote_id: str) -> tuple[DraftDocument, str]:
    doc = _unported("payment_plan", edition, extraction)
    doc.payload["deposit_percent"] = 50
    doc.summary = "Payment plan stub. Workroom job invoices use the existing 50% deposit schedule when issued."
    return doc, session_quote_id


def handle_notes(extraction: Extraction, edition: EditionConfig, session_quote_id: str) -> tuple[DraftDocument, str]:
    doc = _unported("notes", edition, extraction)
    doc.summary = "Notes captured on the voice draft. Nothing is sent."
    return doc, session_quote_id


def _register() -> None:
    register_handler("quote", handle_quote)
    register_handler("invoice", handle_invoice)
    register_handler("drawing", handle_drawing)
    register_handler("contract", handle_contract)
    register_handler("payment_plan", handle_payment_plan)
    register_handler("notes", handle_notes)


_register()
