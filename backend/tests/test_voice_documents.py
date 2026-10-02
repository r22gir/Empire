"""Voice-to-document borrador. Transcript fixtures only — no live STT."""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

FIXTURE = Path(__file__).parent / "fixtures" / "voice_separar_lote.txt"


def _env(monkeypatch, tmp_path, edition="maxine"):
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("CONSTRUCTION_DB", str(tmp_path / "construction.db"))
    monkeypatch.setenv("VOICE_DRAFTS_DB", str(tmp_path / "voice_drafts.db"))
    monkeypatch.setenv("ASSISTANT_NAME", "Maxine" if edition == "maxine" else "Max-e")


def _lot(number="12", status="available"):
    from app.routers.construction import get_db

    conn = get_db()
    conn.execute(
        "INSERT INTO cf_projects (id, name, slug, currency) VALUES ('p1', 'Portal', 'portal', 'COP')"
    )
    conn.execute(
        """
        INSERT INTO cf_lots (id, project_id, lot_number, status, current_price, base_price)
        VALUES ('l1', 'p1', ?, ?, NULL, NULL)
        """,
        (number, status),
    )
    conn.commit()
    conn.close()


def _lot_status():
    from app.routers.construction import get_db

    conn = get_db()
    try:
        return conn.execute("SELECT status FROM cf_lots WHERE id = 'l1'").fetchone()["status"]
    finally:
        conn.close()


def test_fixture_extracts_reservation_fields():
    from app.services.voice_doc.extract import extract_fields, propose_doc_type

    text = FIXTURE.read_text(encoding="utf-8").strip()
    fields = extract_fields(text)
    assert fields["lot_number"] == "12"
    assert fields["buyer_name"] == "Juan Pérez"
    assert fields["cuota_inicial_pct"] == 30
    assert fields["installments"] == 24
    assert fields["language"] == "es"
    assert fields["locale"] == "es-CO"
    assert propose_doc_type(text, fields, "maxine") == "reservation"


def test_notes_accumulate_until_listo_and_never_send(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.voice_doc.pipeline import ingest_transcript
    from app.services.voice_doc.store import approve_draft, get_draft, send_draft

    first = FIXTURE.read_text(encoding="utf-8").strip()
    opened = ingest_transcript(first, channel="web", edition="maxine")
    assert opened["draft"] is None
    assert opened["sent"] is False
    assert opened["doc_type"] == "reservation"
    second = ingest_transcript(
        "El precio es 100000000 y la separación es 5000000.",
        session_id=opened["session_id"],
        channel="web",
        edition="maxine",
    )
    closed = ingest_transcript("listo", session_id=second["session_id"], channel="web", edition="maxine")
    assert closed["fields"]["buyer_name"] == "Juan Pérez"
    assert closed["fields"]["price"] == 100000000
    assert closed["fields"]["separacion"] == 5000000
    assert closed["draft"]["sent"] is False
    assert closed["draft"]["auto_send"] is False
    draft = get_draft(closed["draft"]["id"])
    assert draft["sent"] is False
    assert draft["status"] == "draft"
    assert "DRAFT" in draft["html"]
    assert "BORRADOR" in draft["html"]
    from app.services.voice_doc.store import render_draft_pdf

    pdf = render_draft_pdf(draft["payload"], ["Separar el lote 12"])
    assert pdf.startswith(b"%PDF")
    assert b"DRAFT" in pdf
    assert "Juan Pérez" in draft["html"]
    schedule = draft["payload"]["schedule"]
    assert sum(row["amount"] for row in schedule["installments"]) == schedule["balance"]
    approved = approve_draft(draft["id"])
    assert approved["status"] == "approved"
    assert approved["sent"] is False
    refused = send_draft(draft["id"], confirm=False, channel="email")
    assert refused["sent"] is False
    assert refused["emailed"] is False
    confirmed = send_draft(draft["id"], confirm=True, channel="email")
    assert confirmed["sent"] is False
    assert confirmed["emailed"] is False
    assert get_draft(draft["id"])["sent"] is False


def test_payment_plan_cop_rounding_and_sum():
    from app.services.voice_doc.plans import build_schedule, payment_plan_options, split_installments

    assert split_installments(70, 3) == [24, 23, 23]
    odd = build_schedule(price=101, cuota_inicial_pct=10, installments=3)
    assert odd["cuota_inicial"] == 10
    assert sum(row["amount"] for row in odd["installments"]) == odd["balance"] == 91
    plans = payment_plan_options(price=100_000_000, separacion=5_000_000, cuota_inicial_pct=30, installments=24)
    assert len(plans) == 3
    for plan in plans:
        assert sum(row["amount"] for row in plan["installments"]) == plan["balance"]
        assert plan["cuota_inicial"] + plan["balloon"] + plan["balance"] == plan["price"]
        assert all(isinstance(row["amount"], int) for row in plan["installments"])
    assert plans[2]["balloon"] > 0


def test_lot_status_only_on_confirmation(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _lot()
    from app.services.voice_doc.deals import DealError, confirm_reservation, transition_lot_status
    from app.services.voice_doc.plans import build_schedule

    with pytest.raises(DealError):
        transition_lot_status("available", "reservado", confirmed=False)
    with pytest.raises(DealError):
        transition_lot_status("available", "vendido", confirmed=True)

    schedule = build_schedule(price=100_000_000, separacion=5_000_000, cuota_inicial_pct=30, installments=24)
    fields = {"lot_number": "12", "buyer_name": "Juan Pérez", "price": 100_000_000, "separacion": 5_000_000}
    refused = confirm_reservation(fields=fields, schedule=schedule, draft_id="d1", confirm=False, lot_status="reservado")
    assert refused["sale_id"] is None
    assert refused["sent"] is False
    assert _lot_status() == "available"
    with pytest.raises(DealError):
        confirm_reservation(fields=fields, schedule=schedule, draft_id="d1", confirm=True, lot_status="vendido")
    assert _lot_status() == "available"
    booked = confirm_reservation(fields=fields, schedule=schedule, draft_id="d1", confirm=True, lot_status="reservado")
    assert booked["sent"] is False
    assert booked["lot_status"] == "reservado"
    assert booked["contract_type"] == "separacion"
    assert _lot_status() == "reservado"
    confirm_reservation(fields=fields, schedule=schedule, draft_id="d1", confirm=True, lot_status="separado")
    assert _lot_status() == "separado"
    sold = confirm_reservation(fields=fields, schedule=schedule, draft_id="d1", confirm=True, lot_status="vendido")
    assert sold["contract_type"] == "compraventa"
    assert _lot_status() == "vendido"

    from app.routers.construction import get_db

    conn = get_db()
    try:
        sale = conn.execute(
            "SELECT contract_type, contract_date, contract_document, currency FROM cf_sales WHERE id = ?",
            (booked["sale_id"],),
        ).fetchone()
        assert sale["contract_type"] == "separacion"
        assert sale["contract_date"]
        assert "acuerdo_separacion" in sale["contract_document"]
        assert sale["currency"] == "COP"
        paid = conn.execute("SELECT amount FROM cf_payments WHERE sale_id = ?", (booked["sale_id"],)).fetchall()
        assert sum(row["amount"] for row in paid) == 100_000_000
    finally:
        conn.close()


def test_recibo_only_when_payment_recorded(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _lot()
    from app.services.voice_doc.deals import confirm_reservation
    from app.services.voice_doc.plans import build_schedule

    schedule = build_schedule(price=10_000_000, separacion=1_000_000, cuota_inicial_pct=30, installments=2)
    fields = {"lot_number": "12", "buyer_name": "Ana Gómez", "price": 10_000_000}
    without = confirm_reservation(fields=fields, schedule=schedule, draft_id="d", confirm=True, lot_status="reservado")
    assert without["recibo"] is None
    with_pay = confirm_reservation(
        fields=fields,
        schedule=schedule,
        draft_id="d",
        confirm=True,
        lot_status="separado",
        payment={"kind": "separacion", "amount": 1_000_000, "date": "2026-10-02"},
    )
    assert with_pay["recibo"]
    assert "RECIBO BORRADOR" in with_pay["recibo"]
    assert with_pay["sent"] is False


def test_placeholder_fill_uses_only_public_company_fields(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.edition_facts import upsert_fact
    from app.services.voice_doc.templates import WATERMARK, fill_placeholders, skeleton_body

    upsert_fact(key="legal_name", text="Taller Público", value="Taller Público", visibility="public")
    upsert_fact(key="nit", text="900111222", value="900111222", visibility="confidential")
    body = skeleton_body("Acuerdo de separación")
    filled = fill_placeholders(body, {"comprador": "Juan Pérez", "lote": "12"})
    assert "Juan Pérez" in filled
    assert "Taller Público" in filled
    assert "{{nit}}" in filled
    assert "900111222" not in filled
    assert WATERMARK in filled
    assert "GAC" not in body
    assert "se obliga" not in body.lower()
    for slot_title in ("Acuerdo de separación", "Promesa de compraventa", "Pagaré / carta de instrucciones"):
        assert "GAC" not in skeleton_body(slot_title)


def test_overdue_payments_feed_the_brief(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _lot()
    from app.routers.construction import get_db
    from app.services.voice_doc.deals import confirm_reservation, overdue_brief_text, overdue_payments
    from app.services.voice_doc.plans import build_schedule
    scheduler = Path(__file__).resolve().parents[1] / "app" / "services" / "max" / "scheduler.py"

    schedule = build_schedule(price=10_000_000, separacion=1_000_000, cuota_inicial_pct=30, installments=2)
    confirm_reservation(
        fields={"lot_number": "12", "buyer_name": "Ana Gómez", "price": 10_000_000},
        schedule=schedule,
        draft_id="d",
        confirm=True,
        lot_status="reservado",
    )
    yesterday = (date.today() - timedelta(days=3)).isoformat()
    conn = get_db()
    conn.execute("UPDATE cf_payments SET due_date = ?, status = 'pending' WHERE notes = 'cuota'", (yesterday,))
    conn.commit()
    conn.close()
    rows = overdue_payments(date.today().isoformat())
    assert rows
    assert all(row["due_date"] < date.today().isoformat() for row in rows)
    text = overdue_brief_text(date.today().isoformat())
    assert "Pagos vencidos" in text
    assert "Ana Gómez" in text
    assert "overdue_brief_text" in scheduler.read_text(encoding="utf-8")
    assert "is_maxine" in scheduler.read_text(encoding="utf-8")


def test_max_e_coaching_quote_stays_draft(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    from app.services.voice_doc.pipeline import channel_report, ingest_transcript

    view = ingest_transcript(
        "Cotiza el curso de liderazgo para Ana Gómez, precio 1500000. listo",
        channel="web",
        edition="amp",
    )
    assert view["doc_type"] == "quote"
    assert view["fields"]["product_kind"] == "course"
    assert view["fields"]["product_name"] == "liderazgo"
    assert view["fields"]["buyer_name"] == "Ana Gómez"
    assert view["fields"]["price"] == 1500000
    assert view["locale"] == "es-CO"
    assert view["draft"]["sent"] is False
    report = channel_report()
    assert report["telegram"]["connected"] is True
    assert report["web"]["connected"] is True
    assert report["whatsapp"]["connected"] is False


def test_house_and_finish_options_are_two_or_three(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.voice_doc.pipeline import ingest_transcript

    view = ingest_transcript(
        "Cotizar la casa para Juan Pérez, precio 200000000.",
        channel="web",
        edition="maxine",
    )
    choices = view["options"]["choices"]
    assert view["options"]["kind"] == "house_type"
    assert [choice["id"] for choice in choices] == ["T1", "T2", "T3"]
    picked = ingest_transcript("", session_id=view["session_id"], choice_id="T2", channel="web", edition="maxine")
    assert picked["fields"]["house_type"] == "T2"
    assert picked["options"]["kind"] == "finishes"
    assert len(picked["options"]["choices"]) == 2


def test_send_route_never_flips_sent(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    from app.routers.voice_documents import router
    from app.services.voice_doc.pipeline import ingest_transcript

    view = ingest_transcript("Notas de la reunión con Ana Gómez. listo", channel="web", edition="amp")
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)
    draft_id = view["draft"]["id"]
    preview = client.get(f"/api/v1/voice/documents/drafts/{draft_id}/preview")
    assert preview.status_code == 200
    assert "DRAFT" in preview.text
    send = client.post(f"/api/v1/voice/documents/drafts/{draft_id}/send", json={"confirm": False, "channel": "email"})
    assert send.status_code == 200
    assert send.json()["sent"] is False
    assert send.json()["emailed"] is False
