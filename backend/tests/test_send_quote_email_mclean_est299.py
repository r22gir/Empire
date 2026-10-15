"""Max estimate emails use the McLean renderer (EST-2026-299 shape).

No real SMTP and no live data writes — send is mocked, PDFs land in tmp_path.
"""
from __future__ import annotations

import io
import os
from pathlib import Path

import pytest

from app.services.max import tool_executor as te
from app.services.quote_service import get_quote, update_quote


def _est299_lines():
    """U banquette / L banquette / Material — same shape as EST-2026-299."""
    return [
        {
            "room": "U banquette",
            "category": "manual_line",
            "description": 'Seat back — main\n249.75" run · back 26.75" · 12" channels',
            "sq_ft": 46.39,
            "price_per_sqft": 65,
        },
        {
            "room": "U banquette",
            "category": "manual_line",
            "description": 'Seat cushion — main\n249 3/4" run · depth 18" · plain cognac',
            "sq_ft": 31.22,
            "price_per_sqft": 45,
        },
        {
            "room": "L banquette",
            "category": "manual_line",
            "description": 'Seat back — long leg\n107 3/4" run · back 26 3/4" · 12" channels',
            "sq_ft": 20.02,
            "price_per_sqft": 65,
        },
        {
            "room": "Material",
            "category": "manual_line",
            "description": "Cognac commercial vinyl\nBacks and seats",
            "quantity": 1,
            "unit": "lot",
            "unit_price": 1785.88,
        },
    ]


def _pdf_text(pdf: bytes) -> str:
    from pypdf import PdfReader
    return "\n".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf)).pages)


def _make_est299(isolated_empire_db):
    from app.services.max.tool_executor import _create_engine_quote

    res = _create_engine_quote({
        "customer_name": "Marley's Bar & Grill",
        "project_name": "Banquettes",
        "line_items": _est299_lines(),
    })
    assert res.success, res.error
    qid = res.result["quote_id"]
    update_quote(qid, {"notes": "Rev B. Banquette estimate fixture."})
    return get_quote(qid)


class _FakeMail:
    is_configured = True
    last_message_id = "msg-est299-test"
    sent: list

    def __init__(self):
        self.sent = []

    def send(self, **kwargs):
        self.sent.append(kwargs)
        return True


@pytest.fixture
def pdf_tmpdir(tmp_path, monkeypatch):
    pdf_dir = tmp_path / "quotes" / "pdf"
    pdf_dir.mkdir(parents=True)
    monkeypatch.setattr(te.dp, "quote_pdf_dir", lambda: pdf_dir)
    monkeypatch.setattr(
        "app.services.quote_pdf_service.quote_pdf_dir", lambda: pdf_dir,
    )
    monkeypatch.setattr(
        "app.services.data_paths.quote_pdf_dir", lambda: pdf_dir,
    )
    return pdf_dir


def test_est299_email_uses_mclean_areas_columns_deposit_and_founder_inbox(
    isolated_empire_db, pdf_tmpdir, monkeypatch, tmp_path,
):
    from app.db.database import get_db

    quote = _make_est299(isolated_empire_db)
    with get_db() as conn:
        conn.execute(
            "UPDATE quotes_v2 SET quote_number = ? WHERE id = ?",
            ("EST-2026-299", quote["id"]),
        )
        conn.commit()
    quote = get_quote(quote["id"])
    mail = _FakeMail()
    monkeypatch.setattr("app.services.max.email_service.EmailService", lambda: mail)

    result = te._send_quote_email({"quote_id": quote["id"], "to": "me"})
    assert result.success, result.error
    assert len(mail.sent) == 1
    sent = mail.sent[0]

    assert sent["to"] == "empirebox2026@gmail.com"
    assert sent.get("cc") in (None, "", [])
    assert "rafa22giraldo" not in str(sent).lower()
    assert result.result["sent_to"] == "empirebox2026@gmail.com"
    assert result.result.get("cc") == []

    subject = sent["subject"]
    body = sent.get("body_text") or ""
    assert "Rev B" in subject or "Rev B" in body
    assert " ET" in subject or " ET" in body
    total = float(quote["total"])
    assert f"${total:,.2f}" in subject or f"${total:,.2f}" in body
    assert "generated" in (subject + body).lower()

    attachments = sent.get("attachments") or []
    assert attachments, "estimate PDF must be attached"
    pdf_path = Path(attachments[0])
    assert pdf_path.exists()
    pdf_bytes = pdf_path.read_bytes()
    assert pdf_bytes[:4] == b"%PDF"
    text = _pdf_text(pdf_bytes)
    flat = " ".join(text.split())
    upper = text.upper()

    for area in ("U BANQUETTE", "L BANQUETTE", "MATERIAL"):
        assert area in upper, f"missing area {area}"
    for col in ("Description", "Qty", "Unit", "Sq ft", "Price/sq ft", "Total"):
        assert col in text, f"missing column {col}"
    # Lot rate is not in Price/sq ft (blank). $1,785.88 remains on line Total and the Material subtotal.
    assert text.count("1,785.88") == 2
    assert "MANUAL_LINE" not in upper
    assert "manual_line" not in text
    assert "Deposit" in text
    assert "Balance" in text
    deposit = float(quote["deposit_required"])
    balance = round(float(quote["total"]) - deposit, 2)
    assert f"${deposit:,.2f}" in flat
    assert f"${balance:,.2f}" in flat
    assert '249 3/4"' in text
    assert '26 3/4"' in text
    assert "249.75" not in text
    assert "26.75" not in text
    assert "EMPIRE" in "".join(text.split()).upper() or "WORKROOM" in upper

    sample = Path("/opt/cursor/artifacts")
    if sample.is_dir():
        out = sample / "est-2026-299-mclean-sample.pdf"
        out.write_bytes(pdf_bytes)
    (tmp_path / "est-2026-299-mclean-sample.pdf").write_bytes(pdf_bytes)


def test_est299_refuses_rafa22_cc_and_clients(isolated_empire_db, pdf_tmpdir, monkeypatch):
    quote = _make_est299(isolated_empire_db)
    mail = _FakeMail()
    monkeypatch.setattr("app.services.max.email_service.EmailService", lambda: mail)

    rafa = te._send_quote_email({
        "quote_id": quote["id"],
        "to": "rafa22giraldo@gmail.com",
    })
    assert not rafa.success
    assert "estimate_emails_founder_inbox_only" in (rafa.error or "")
    assert mail.sent == []

    client = te._send_quote_email({
        "quote_id": quote["id"],
        "to": "davonne@marleys.example",
        "cc": "rafa22giraldo@gmail.com",
    })
    assert not client.success
    assert "estimate_emails_founder_inbox_only" in (client.error or "")
    assert mail.sent == []

    # Even if a CC is requested, a valid founder send has no CC.
    ok = te._send_quote_email({
        "quote_id": quote["id"],
        "to": "empirebox2026@gmail.com",
        "cc": "rafa22giraldo@gmail.com",
    })
    assert ok.success, ok.error
    assert mail.sent[-1].get("cc") in (None, "", [])
    assert "rafa22giraldo" not in str(mail.sent[-1].get("cc") or "").lower()


def test_stale_pdf_newer_than_updated_at_is_replaced(isolated_empire_db, pdf_tmpdir, monkeypatch):
    """mtime newer than updated_at is still stale — always re-render on send."""
    import time

    quote = _make_est299(isolated_empire_db)
    pdf_path = pdf_tmpdir / f"{quote['quote_number']}.pdf"
    stale = b"%PDF-1.4 stale weasyprint MANUAL_LINE\n" + b"X" * 200
    pdf_path.write_bytes(stale)
    future = time.time() + 365 * 24 * 3600
    os.utime(pdf_path, (future, future))

    mail = _FakeMail()
    monkeypatch.setattr("app.services.max.email_service.EmailService", lambda: mail)
    result = te._send_quote_email({"quote_id": quote["id"], "to": "me"})
    assert result.success, result.error
    fresh = Path(mail.sent[0]["attachments"][0]).read_bytes()
    assert fresh[:4] == b"%PDF"
    assert fresh != stale
    assert b"MANUAL_LINE" not in fresh
    text = _pdf_text(fresh)
    assert "U BANQUETTE" in text.upper()
    assert "Deposit" in text
    assert "Price/sq ft" in text


def test_generate_pdf_for_quote_skips_weasyprint(isolated_empire_db, pdf_tmpdir, monkeypatch):
    quote = _make_est299(isolated_empire_db)

    async def boom(*_a, **_k):
        raise AssertionError("WeasyPrint generate_pdf must not run for v2 quotes")

    monkeypatch.setattr("app.routers.quotes.generate_pdf", boom)
    import asyncio
    path = asyncio.run(te._generate_pdf_for_quote(quote["id"]))
    data = Path(path).read_bytes()
    assert data[:4] == b"%PDF"
    assert "MANUAL_LINE" not in _pdf_text(data).upper()


def test_send_quote_email_accepts_quote_number(isolated_empire_db, pdf_tmpdir, monkeypatch):
    quote = _make_est299(isolated_empire_db)
    mail = _FakeMail()
    monkeypatch.setattr("app.services.max.email_service.EmailService", lambda: mail)
    result = te._send_quote_email({"quote_id": quote["quote_number"], "to": "me"})
    assert result.success, result.error
    assert result.result["quote_id"] == quote["id"]
    assert mail.sent[0]["to"] == "empirebox2026@gmail.com"


def test_send_quote_email_refuses_duplicate_quote_number(isolated_empire_db, pdf_tmpdir, monkeypatch):
    import json
    from app.db.database import get_db
    from app.services.data_paths import quotes_data_dir

    live = _make_est299(isolated_empire_db)
    with get_db() as conn:
        conn.execute(
            "UPDATE quotes_v2 SET quote_number = ?, total = 11328.65, "
            "created_at = ? WHERE id = ?",
            ("EST-2026-299", "2026-10-10 12:00:00", live["id"]),
        )
        conn.commit()

    quotes_dir = quotes_data_dir()
    quotes_dir.mkdir(parents=True, exist_ok=True)
    leftover_id = "est299-potthast-leftover"
    leftover_path = quotes_dir / f"{leftover_id}.json"
    leftover_path.write_text(json.dumps({
        "id": leftover_id,
        "quote_number": "EST-2026-299",
        "customer_name": "Potthast",
        "total": 637,
        "created_at": "2026-10-03T12:00:00Z",
        "status": "draft",
    }))
    try:
        mail = _FakeMail()
        monkeypatch.setattr("app.services.max.email_service.EmailService", lambda: mail)
        result = te._send_quote_email({"quote_id": "EST-2026-299", "to": "me"})
        assert not result.success
        err = result.error or ""
        assert "duplicated" in err.lower()
        assert "Potthast" in err
        assert "637" in err
        assert "which one" in err.lower()
        assert mail.sent == []

        by_id = te._send_quote_email({"quote_id": live["id"], "to": "me"})
        assert by_id.success, by_id.error
        assert mail.sent[-1]["to"] == "empirebox2026@gmail.com"
    finally:
        if leftover_path.exists():
            leftover_path.unlink()


def test_send_email_quote_pdf_reroutes_to_send_quote_email(
    isolated_empire_db, pdf_tmpdir, monkeypatch,
):
    import time

    quote = _make_est299(isolated_empire_db)
    stale_path = pdf_tmpdir / f"{quote['quote_number']}.pdf"
    stale_path.write_bytes(b"%PDF-1.4 STALE MANUAL_LINE\n")
    os.utime(stale_path, (time.time() + 365 * 24 * 3600,) * 2)

    mail = _FakeMail()
    monkeypatch.setattr("app.services.max.email_service.EmailService", lambda: mail)
    result = te._send_email({
        "to": "rafa22giraldo@gmail.com",
        "subject": "Estimate PDF",
        "body": "Please find attached",
        "attachments": [str(stale_path)],
        "cc": "rafa22giraldo@gmail.com",
    })
    assert result.success, result.error
    assert result.tool == "send_quote_email"
    sent = mail.sent[0]
    assert sent["to"] == "empirebox2026@gmail.com"
    assert sent.get("cc") in (None, "", [])
    assert "rafa22giraldo" not in str(sent).lower()
    fresh = Path(sent["attachments"][0]).read_bytes()
    assert fresh[:4] == b"%PDF"
    assert b"MANUAL_LINE" not in fresh
    assert "Price/sq ft" in _pdf_text(fresh)


def test_send_email_blocks_rafa22_to_and_cc(isolated_empire_db, monkeypatch):
    mail = _FakeMail()
    monkeypatch.setattr("app.services.max.email_service.EmailService", lambda: mail)
    to_rafa = te._send_email({
        "to": "rafa22giraldo@gmail.com",
        "subject": "hello",
        "body": "no attachment",
    })
    assert not to_rafa.success
    assert "recipient_not_in_whitelist" in (to_rafa.error or "")
    cc_rafa = te._send_email({
        "to": "empirebox2026@gmail.com",
        "cc": "rafa22giraldo@gmail.com",
        "subject": "hello",
        "body": "no attachment",
    })
    assert not cc_rafa.success
    assert mail.sent == []


def test_send_email_doc_attachment_founder_inbox_no_cc(isolated_empire_db, tmp_path, monkeypatch):
    mail = _FakeMail()
    monkeypatch.setattr("app.services.max.email_service.EmailService", lambda: mail)
    invoice = tmp_path / "INV-2026-100.pdf"
    invoice.write_bytes(b"%PDF-1.4 invoice")
    result = te._send_email({
        "to": "max@empirebox.store",
        "cc": "workroom@empirebox.store",
        "subject": "Invoice",
        "body": "invoice attached",
        "attachments": [str(invoice)],
    })
    assert result.success, result.error
    sent = mail.sent[0]
    assert sent["to"] == "empirebox2026@gmail.com"
    assert sent.get("cc") in (None, "", [])
    assert "rafa22giraldo" not in str(sent).lower()
