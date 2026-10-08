"""2026-10-08: send_quote_email bundles every PDF and mockup into ONE email."""
import os
import types

import importlib
max_router = importlib.import_module("app.routers.max.router")
from app.services.max import tool_executor as te


def test_round_bundles_quotes_and_mockups_for_same_recipient():
    calls = [
        {"tool": "send_quote_email", "quote_id": "EST-2026-299", "to": "me"},
        {"tool": "send_quote_email", "quote_id": "EST-2026-300", "to": "me"},
        {"tool": "share_file", "via": "email", "path": "/home/rg/jobs/m/MOCKUP.pdf", "to": "me"},
        {"tool": "get_quote", "quote_id": "EST-2026-299"},
    ]
    out = max_router._bundle_send_tool_calls(calls)
    sends = [c for c in out if c["tool"] == "send_quote_email"]
    assert len(sends) == 1
    assert sends[0]["quote_ids"] == ["EST-2026-299", "EST-2026-300"]
    assert sends[0]["attachments"] == ["/home/rg/jobs/m/MOCKUP.pdf"]
    assert sends[0]["_bundled_calls"] == 3
    assert not any(c["tool"] == "share_file" for c in out)
    assert any(c["tool"] == "get_quote" for c in out)


def test_different_recipients_stay_separate():
    calls = [{"tool": "send_quote_email", "quote_id": "a", "to": "x@example.com"},
             {"tool": "send_quote_email", "quote_id": "b", "to": "y@example.com"}]
    out = max_router._bundle_send_tool_calls(calls)
    assert len(out) == 2 and "_bundled_calls" not in out[0]


def test_one_email_carries_pdfs_and_attachments(tmp_path, monkeypatch):
    mock = tmp_path / "jobs" / "MOCKUP.pdf"
    mock.parent.mkdir(parents=True)
    mock.write_bytes(b"%PDF-1.4 mock")
    pdfs = {}
    for n in ("EST-1", "EST-2"):
        p = tmp_path / f"{n}.pdf"
        p.write_bytes(b"%PDF-1.4 q")
        pdfs[n] = str(p)
    monkeypatch.setenv("MAX_FILE_FINDER_ROOTS", str(tmp_path))
    monkeypatch.setenv("EMPIRE_EDITION", "main")
    import app.services.max.email_recipient_whitelist as wl
    monkeypatch.setattr(wl, "authorize_email_recipient", lambda to: {"recipient_authorized": True, "blocked_reason": None})
    import app.services.quote_service as qs
    monkeypatch.setattr(qs, "resolve_quote", lambda q: {"id": q, "quote_number": q, "customer_name": "Marley's", "total": 1})
    async def fake_pdf(qid):
        return pdfs[qid]
    monkeypatch.setattr(te, "_generate_pdf_for_quote", fake_pdf)
    monkeypatch.setattr(te, "_merge_standing_email_cc", lambda to, cc: [])
    sent = []

    class FakeSvc:
        is_configured = True
        last_message_id = "18abc"

        def send(self, **kw):
            sent.append(kw)
            return True
    import app.services.max.email_service as es
    monkeypatch.setattr(es, "EmailService", FakeSvc)
    r = te._send_quote_email({"quote_ids": ["EST-1", "EST-2"], "attachments": [str(mock)], "to": "me"})
    assert r.success, r.error
    assert len(sent) == 1
    assert [os.path.basename(a) for a in sent[0]["attachments"]] == ["EST-1.pdf", "EST-2.pdf", "MOCKUP.pdf"]
    assert r.result["attachments_sent"] == 3 and r.result["one_email"] is True


def test_secret_attachment_refused_nothing_sent(tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_FILE_FINDER_ROOTS", str(tmp_path))
    env = tmp_path / ".env"
    env.write_text("K=1")
    paths, bad = te._resolve_extra_attachments({"attachments": [str(env)]})
    assert bad == str(env) and paths == []
