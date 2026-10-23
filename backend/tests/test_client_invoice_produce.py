"""Max client invoice: Square Share-link + existing PDF + Outlook draft.

Mock data and mocked Square/Outlook HTTP only. No live API calls.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import httpx
import pytest

from app.services.client_invoice.business import InvoiceBusiness, resolve_invoice_business
from app.services.client_invoice.client_copy import client_line_text, sanitize_line_items
from app.services.client_invoice.cover_email import cover_email_text
from app.services.client_invoice.outlook_draft import OutlookDraftClient, OutlookSendForbidden
from app.services.client_invoice.produce import produce_client_invoice
from app.services.client_invoice.square import (
    DELIVERY_SHARE_LINK,
    SquareInvoiceClient,
    SquareSendForbidden,
)
from app.services.invoice_pdf_service import invoice_pay_link

PROOF_DIR = Path(__file__).resolve().parents[2] / "reports" / "2026-10-23_client_invoice"
ARTIFACT_DIR = Path("/opt/cursor/artifacts/screenshots")

ATELIER = InvoiceBusiness(
    id="mock_atelier",
    name="Mock Atelier",
    tagline="Test drapery",
    phone="(555) 010-0001",
    email="hello@mockatelier.test",
    address="100 Test Lane",
    website="atelier.example.test",
    billed_by="mock_atelier",
    square_location_id="LOC_ATELIER",
    square_token_env="SQUARE_ACCESS_TOKEN_MOCK_ATELIER",
    outlook_mailbox="hello@mockatelier.test",
)
MILLWORK = InvoiceBusiness(
    id="mock_millwork",
    name="Mock Millwork",
    tagline="Test wood",
    phone="(555) 010-0002",
    email="shop@mockmillwork.test",
    address="200 Shop Road",
    website="millwork.example.test",
    billed_by="mock_millwork",
    square_location_id="LOC_MILL",
    square_token_env="SQUARE_ACCESS_TOKEN_MOCK_MILLWORK",
    outlook_mailbox="shop@mockmillwork.test",
)

PAY_URL = "https://app.squareup.com/pay-invoice/invtmp:mock-share-link-aaaa"


def _invoice(**kw):
    inv = {
        "id": "inv-mock-1",
        "invoice_number": "INV-MOCK-100",
        "client_name": "Alex Rivera",
        "client_email": "alex@northside.test",
        "client_address": "9 Northside Ave",
        "invoice_date": "2026-10-23",
        "due_date": "2026-10-23",
        "subtotal": 250.0,
        "tax_rate": 0,
        "tax_amount": 0,
        "total": 250.0,
        "amount_paid": 0,
        "balance_due": 250.0,
        "status": "draft",
        "payment_status": "unpaid",
        "invoice_stage": "final",
        "terms": "Due on receipt",
        "line_items": [
            {
                "room": "Window",
                "description": 'Kravet V639 Navy bench — shorten 2.0"',
                "fabric_code": "V008-Navy",
                "quantity": 1,
                "unit": "ea",
                "unit_price": 175.0,
                "total": 175.0,
            },
            {
                "description": "Lumbar pillows",
                "quantity": 3,
                "unit": "ea",
                "unit_price": 25.0,
                "total": 75.0,
            },
        ],
    }
    inv.update(kw)
    return inv


class SquareRecorder:
    def __init__(self):
        self.calls: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        path = request.url.path
        if path.endswith("/send") or path.endswith("/sendMail"):
            return httpx.Response(500, json={"error": "send must never be called"})
        if request.method == "POST" and path.endswith("/customers"):
            return httpx.Response(200, json={"customer": {"id": "CUST_MOCK"}})
        if request.method == "POST" and path.endswith("/orders"):
            return httpx.Response(200, json={"order": {"id": "ORDER_MOCK"}})
        if request.method == "POST" and path.endswith("/invoices"):
            body = json.loads(request.content.decode())
            inv = body.get("invoice") or {}
            return httpx.Response(200, json={
                "invoice": {
                    "id": "SQINV_MOCK",
                    "version": 0,
                    "delivery_method": inv.get("delivery_method"),
                    "public_url": None,
                }
            })
        if request.method == "POST" and path.rstrip("/").endswith("/publish"):
            return httpx.Response(200, json={
                "invoice": {
                    "id": "SQINV_MOCK",
                    "version": 1,
                    "delivery_method": DELIVERY_SHARE_LINK,
                    "public_url": PAY_URL,
                }
            })
        return httpx.Response(404, json={"error": path})


class OutlookRecorder:
    def __init__(self):
        self.calls: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        path = request.url.path
        if path.endswith("/send") or path.endswith("sendMail"):
            return httpx.Response(500, json={"error": "send must never be called"})
        if request.method == "GET" and path.endswith("/messages"):
            return httpx.Response(200, json={
                "value": [{
                    "id": "MSG_THREAD",
                    "subject": "bench repair",
                    "conversationId": "CONV_1",
                    "isDraft": False,
                }]
            })
        if request.method == "POST" and path.endswith("/createReply"):
            return httpx.Response(201, json={
                "id": "DRAFT_REPLY",
                "isDraft": True,
                "conversationId": "CONV_1",
            })
        if request.method == "POST" and path.endswith("/messages"):
            return httpx.Response(201, json={"id": "DRAFT_NEW", "isDraft": True})
        if request.method == "PATCH":
            return httpx.Response(200, json={"id": "DRAFT_REPLY", "isDraft": True})
        if request.method == "POST" and path.endswith("/attachments"):
            return httpx.Response(201, json={"id": "ATT_1"})
        return httpx.Response(404, json={"error": path})


def _clients(log=None):
    slog = log if log is not None else []
    olog = log if log is not None else []
    sq = SquareRecorder()
    ol = OutlookRecorder()
    square = SquareInvoiceClient(
        access_token="tok_mock", location_id="LOC_ATELIER",
        http=httpx.Client(transport=httpx.MockTransport(sq)), log=slog,
    )
    outlook = OutlookDraftClient(
        access_token="tok_mock", mailbox="hello@mockatelier.test",
        http=httpx.Client(transport=httpx.MockTransport(ol)), log=olog,
    )
    return square, outlook, sq, ol


def _pdf_text(pdf_bytes: bytes) -> str:
    import pymupdf
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    return "\n".join(page.get_text() for page in doc)


def test_business_resolver_is_not_workroom_hardcoded():
    a = resolve_invoice_business({"business_id": "x"}, explicit=ATELIER)
    b = resolve_invoice_business({"business_id": "y"}, explicit=MILLWORK)
    assert a.name == "Mock Atelier" and b.name == "Mock Millwork"
    assert "Nelma" not in a.name and "Workroom" not in b.name
    dumped = json.dumps(a.public_dict())
    assert "tok_" not in dumped and "access_token" not in dumped


def test_client_copy_fractions_and_fabric_codes():
    text = client_line_text({
        "description": 'Kravet V639 Navy bench — shorten 2.0"',
        "fabric_code": "V008-Navy",
    })
    assert "Kravet" not in text
    assert "V639" not in text
    assert "V008-Navy" in text
    assert "2.0" not in text
    assert '2"' in text or "2 \"" in text or "2\"" in text
    cleaned = sanitize_line_items([{
        "description": "Schumacher velvet",
        "fabric_code": "V012-Celestine",
        "total": 10,
    }])
    assert "Schumacher" not in cleaned[0]["description"]
    assert "V012-Celestine" in cleaned[0]["description"]


def test_invoice_pay_link_accepts_square_url():
    link = invoice_pay_link({
        "square_pay_url": PAY_URL, "balance_due": 250, "status": "draft",
        "payment_status": "link_ready",
    })
    assert link["url"] == PAY_URL
    assert link["provider"] == "square"
    assert link["amount"] == 250.0


def test_square_share_link_only_and_never_sends():
    rec = SquareRecorder()
    log = []
    client = SquareInvoiceClient(
        access_token="tok_mock", location_id="LOC_ATELIER",
        http=httpx.Client(transport=httpx.MockTransport(rec)), log=log,
    )
    out = client.create_share_link_invoice(
        invoice_number="INV-MOCK-100", client_name="Alex Rivera",
        client_email="alex@northside.test",
        line_items=[{"description": "Bench", "quantity": 1, "total": 175}],
        total=175,
    )
    assert out["delivery_method"] == DELIVERY_SHARE_LINK
    assert out["public_url"] == PAY_URL
    bodies = [json.loads(c.content.decode()) for c in rec.calls if c.content]
    invoices = [b["invoice"] for b in bodies if "invoice" in b and "delivery_method" in b.get("invoice", {})]
    assert invoices and all(i["delivery_method"] == "SHARE_MANUALLY" for i in invoices)
    assert all("/send" not in str(c.url) for c in rec.calls)
    assert any(e.get("event") == "square_share_link" for e in log)
    assert any(e.get("delivery_method") == "SHARE_MANUALLY" for e in log)


def test_square_refuses_email_delivery_and_send_path():
    client = SquareInvoiceClient(
        access_token="tok_mock", location_id="LOC_X",
        http=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={}))),
    )
    with pytest.raises(SquareSendForbidden):
        client.request("POST", "/invoices/x/send", {"version": 0})
    with pytest.raises(SquareSendForbidden):
        from app.services.client_invoice.square import _assert_share_link
        _assert_share_link({"delivery_method": "EMAIL"})


def test_outlook_draft_reply_never_sends():
    rec = OutlookRecorder()
    log = []
    client = OutlookDraftClient(
        access_token="tok_mock", mailbox="hello@mockatelier.test",
        http=httpx.Client(transport=httpx.MockTransport(rec)), log=log,
    )
    thread = client.find_thread_message("alex@northside.test")
    draft = client.create_draft_reply(
        body_html="<p>Hi</p>", subject="Invoice INV-MOCK-100",
        to_email="alex@northside.test", pdf_bytes=b"%PDF-1.4",
        pdf_name="Invoice-INV-MOCK-100.pdf", reply_to_id=thread["id"],
    )
    assert draft["is_draft"] is True and draft["sent"] is False
    assert draft["thread_found"] is True
    assert any("/createReply" in str(c.url) for c in rec.calls)
    assert all("/send" not in str(c.url) and "sendMail" not in str(c.url) for c in rec.calls)
    assert any(e.get("event") == "outlook_draft_ready" and e.get("sent") is False for e in log)
    with pytest.raises(OutlookSendForbidden):
        client.request("POST", "/me/messages/DRAFT_REPLY/send")


def test_cover_email_lists_items_and_pay_link():
    text = cover_email_text(
        client_first="Alex", business_name="Mock Atelier",
        lines=sanitize_line_items(_invoice()["line_items"]),
        pay_url=PAY_URL,
    )
    assert "Hi Alex" in text
    assert "175.00" in text and "75.00" in text
    assert PAY_URL in text
    assert "Kravet" not in text
    assert text.count("\n") >= 4


def test_produce_through_real_pdf_path_square_and_outlook_draft():
    log = []
    square, outlook, sq, ol = _clients(log)
    result = produce_client_invoice(
        _invoice(), business=ATELIER, square_client=square, outlook_client=outlook,
        persist=False, confirm=True, log=log,
    )
    assert result["sent"] is False
    assert result["square"]["delivery_method"] == "SHARE_MANUALLY"
    assert result["square"]["public_url"] == PAY_URL
    assert result["outlook"]["is_draft"] is True
    assert result["outlook"]["sent"] is False
    assert result["outlook"]["thread_found"] is True
    assert result["business"]["name"] == "Mock Atelier"
    pdf = result["pdf_bytes"]
    assert pdf[:4] == b"%PDF"
    text = _pdf_text(pdf)
    assert "PAY HERE" in text and "$250.00" in text
    assert "INVOICE" in text
    assert "2.0\"" not in text
    assert "Kravet" not in text and "V639" not in text
    assert b"/URI" in pdf and b"squareup.com" in pdf
    assert all("/send" not in str(c.url) for c in sq.calls + ol.calls)
    assert any(c.method == "POST" and "/invoices" in str(c.url) for c in sq.calls)
    assert any("/createReply" in str(c.url) for c in ol.calls)


def test_produce_second_business_uses_that_branding():
    log = []
    square, outlook, _, _ = _clients(log)
    result = produce_client_invoice(
        _invoice(invoice_number="INV-MOCK-200"), business=MILLWORK,
        square_client=square, outlook_client=outlook, persist=False, confirm=True, log=log,
    )
    assert result["business"]["name"] == "Mock Millwork"
    assert "Workroom" not in result["business"]["name"]
    assert "Mock Millwork" in result["cover_email"]


def test_preview_does_not_call_square_or_outlook():
    preview = produce_client_invoice(_invoice(), business=ATELIER, confirm=False)
    assert preview["needs_confirmation"] is True
    assert preview["sent"] is False
    assert "Square will not email" in preview["message"]


def test_max_tool_preview_and_confirm(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    from app.db import database, init_db
    import importlib
    importlib.reload(database)
    importlib.reload(init_db)
    init_db.init_database()
    from app.db.database import get_db

    inv = _invoice()
    with get_db() as conn:
        have = {r[1] for r in conn.execute("PRAGMA table_info(invoices)")}
        if "client_email" not in have:
            conn.execute("ALTER TABLE invoices ADD COLUMN client_email TEXT")
        if "client_name" not in have:
            conn.execute("ALTER TABLE invoices ADD COLUMN client_name TEXT")
        if "invoice_date" not in have:
            conn.execute("ALTER TABLE invoices ADD COLUMN invoice_date TEXT")
        if "invoice_stage" not in have:
            conn.execute("ALTER TABLE invoices ADD COLUMN invoice_stage TEXT")
        conn.execute("INSERT OR IGNORE INTO customers (id, name, email) VALUES ('c1','Alex Rivera','alex@northside.test')")
        have = {r[1] for r in conn.execute("PRAGMA table_info(invoices)")}
        row = {
            "id": inv["id"], "invoice_number": inv["invoice_number"], "customer_id": "c1",
            "status": "draft", "subtotal": 250, "tax_rate": 0, "tax_amount": 0, "total": 250,
            "amount_paid": 0, "balance_due": 250, "line_items": json.dumps(inv["line_items"]),
            "client_name": inv["client_name"], "client_email": inv["client_email"],
            "invoice_date": inv["invoice_date"], "invoice_stage": "final",
        }
        row = {k: v for k, v in row.items() if k in have}
        conn.execute(
            f"INSERT INTO invoices ({', '.join(row)}) VALUES ({', '.join('?' * len(row))})",
            list(row.values()),
        )

    from app.services.max.tool_executor import TOOL_REGISTRY
    import app.services.max.tools_client_invoice as tools
    importlib.reload(tools)
    fn = TOOL_REGISTRY["produce_client_invoice"]
    preview = fn({"invoice_number": "INV-MOCK-100"})
    assert preview.success and preview.result["needs_confirmation"] is True

    square, outlook, sq, ol = _clients()
    monkeypatch.setattr(tools, "_square_client", lambda biz, log: square)
    monkeypatch.setattr(tools, "_outlook_client", lambda biz, log: outlook)
    # produce is imported inside the handler — patch the produce module
    import app.services.client_invoice.produce as produce_mod
    real = produce_mod.produce_client_invoice

    def _wrapped(invoice, **kw):
        kw.setdefault("business", ATELIER)
        kw["square_client"] = square
        kw["outlook_client"] = outlook
        kw["persist"] = False
        return real(invoice, **kw)

    monkeypatch.setattr(produce_mod, "produce_client_invoice", _wrapped)
    ran = fn({"invoice_number": "INV-MOCK-100", "confirm": True})
    assert ran.success, ran.error
    assert ran.result["sent"] is False
    assert ran.result["square"]["delivery_label"] == "Share link"
    assert ran.result["outlook"]["is_draft"] is True
    assert "pdf_bytes" not in (ran.result or {})
    assert any("/createReply" in str(c.url) for c in ol.calls)
    assert all("/send" not in str(c.url) for c in sq.calls + ol.calls)


def test_source_has_no_send_code_path():
    root = Path(__file__).resolve().parents[1] / "app" / "services"
    files = list((root / "client_invoice").glob("*.py"))
    files.append(root / "max" / "tools_client_invoice.py")
    # Real send verbs — not comments or deny-lists that mention the forbidden names.
    banned = re.compile(
        r"""(?:requests?\(\s*["']POST["']\s*,\s*["'][^"']*/send"""
        r"""|["']https://graph\.microsoft\.com[^"']*sendMail"""
        r"""|delivery_method\s*=\s*["']EMAIL["'])"""
    )
    for path in files:
        text = path.read_text()
        assert re.search(r"^def send", text, re.M) is None, path.name
        hits = banned.findall(text)
        assert hits == [], f"{path.name} contains send path: {hits}"


def test_proof_png_via_real_invoice_path(tmp_path):
    """Render a mock invoice through produce() and save PNG + call log."""
    log = []
    square, outlook, sq, ol = _clients(log)
    result = produce_client_invoice(
        _invoice(), business=ATELIER, square_client=square, outlook_client=outlook,
        persist=False, confirm=True, log=log,
    )
    pdf = result["pdf_bytes"]
    import pymupdf
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(2, 2))
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    png_path = PROOF_DIR / "mock_invoice.png"
    pix.save(str(png_path))
    art = ARTIFACT_DIR / "mock-client-invoice.png"
    pix.save(str(art))
    (PROOF_DIR / "mock_invoice.pdf").write_bytes(pdf)
    log_path = PROOF_DIR / "square_outlook_calls.log"
    lines = [
        "Max produce_client_invoice proof — mocked Square + Outlook, mock client data",
        f"business={result['business']['name']}",
        f"square.delivery_method={result['square']['delivery_method']}",
        f"square.delivery_label=Share link",
        f"outlook.is_draft={result['outlook']['is_draft']}",
        f"outlook.sent={result['outlook']['sent']}",
        f"sent={result['sent']}",
        "",
        "HTTP calls:",
    ]
    for c in sq.calls:
        extra = ""
        if c.content:
            try:
                body = json.loads(c.content.decode())
                extra = f" delivery_method={body.get('invoice', {}).get('delivery_method')}"
            except Exception:
                extra = ""
        lines.append(f"SQUARE {c.method} {c.url.path}{extra}")
    for c in ol.calls:
        lines.append(f"OUTLOOK {c.method} {c.url.path} draft_only")
    log_path.write_text("\n".join(lines) + "\n")
    assert png_path.exists() and png_path.stat().st_size > 1000
    text = log_path.read_text()
    assert "SHARE_MANUALLY" in text
    assert "createReply" in text
    assert "/send" not in text.replace("never", "")
    assert all("/send" not in str(c.url) for c in sq.calls + ol.calls)
