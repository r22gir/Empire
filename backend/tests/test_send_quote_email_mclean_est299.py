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
    quote = _make_est299(isolated_empire_db)
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
    for col in ("Description", "Qty", "Unit", "Sq ft", "Price", "Total"):
        assert col in text, f"missing column {col}"
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


def test_stale_pdf_is_regenerated_before_resend(isolated_empire_db, pdf_tmpdir, monkeypatch):
    quote = _make_est299(isolated_empire_db)
    pdf_path = pdf_tmpdir / f"{quote['quote_number']}.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 stale weasyprint MANUAL_LINE")
    old_mtime = 1_000_000_000  # 2001
    os.utime(pdf_path, (old_mtime, old_mtime))
    assert te._pdf_is_stale(str(pdf_path), quote)

    mail = _FakeMail()
    monkeypatch.setattr("app.services.max.email_service.EmailService", lambda: mail)
    result = te._send_quote_email({"quote_id": quote["id"], "to": "me"})
    assert result.success, result.error
    fresh = Path(mail.sent[0]["attachments"][0]).read_bytes()
    assert fresh[:4] == b"%PDF"
    assert b"MANUAL_LINE" not in fresh
    text = _pdf_text(fresh)
    assert "U BANQUETTE" in text.upper()
    assert "Deposit" in text


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
