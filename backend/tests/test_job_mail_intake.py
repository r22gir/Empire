"""Read-only job-mail intake. Tests inject mail and never send."""

from __future__ import annotations

import os

import pytest

from app.db.database import get_db
from app.services.job_mail_intake import extract as extract_mod
from app.services.job_mail_intake import readers
from app.services.job_mail_intake.extract import extract_mail_facts
from app.services.job_mail_intake.schema import ensure_schema
from app.services.job_mail_intake.service import (
    OUTBOUND_POLICY,
    approve_calendar_proposal,
    list_calendar_proposals,
    list_review_queue,
    list_supplier_events,
    list_timeline_notes,
    run_intake,
)


FORBIDDEN_SEND_NAMES = (
    "send_email",
    "send_message",
    "send_whatsapp",
    "whatsapp_send",
    "smtp",
)


def _seed_job(conn, *, name="Nehal Elrefai", email="nehal@example.com",
              address="100 Main Street McLean VA", sidemark="Nehal Elrefai",
              quote_number="EST-2026-410"):
    ensure_schema(conn)
    conn.execute(
        """INSERT INTO customers (id, name, email, address, notes)
           VALUES ('cust-nehal', ?, ?, ?, ?)""",
        (name, email, address, f"Sidemark: {sidemark}"),
    )
    try:
        conn.execute(
            """INSERT INTO jobs
               (id, title, customer_id, status, notes, client_name, client_email,
                client_address, address, job_number)
               VALUES ('job-nehal', 'Living room drapery', 'cust-nehal', 'pending',
                       ?, ?, ?, ?, ?, 'JOB-2026-010')""",
            (f"Sidemark: {sidemark}. Quote {quote_number}", name, email, address, address),
        )
    except Exception:
        conn.execute(
            """INSERT INTO jobs (id, title, customer_id, status, notes)
               VALUES ('job-nehal', 'Living room drapery', 'cust-nehal', 'pending', ?)""",
            (f"Sidemark: {sidemark}. Quote {quote_number} {address}",),
        )
    try:
        conn.execute(
            """INSERT INTO quotes_v2
               (id, quote_number, customer_name, customer_email, customer_address,
                customer_id, job_id, status, created_at, updated_at)
               VALUES ('q-410', ?, ?, ?, ?, 'cust-nehal', 'job-nehal', 'sent',
                       datetime('now'), datetime('now'))""",
            (quote_number, name, email, address),
        )
    except Exception:
        pass


def test_extract_dates_tracking_and_estimates():
    facts = extract_mail_facts({
        "subject": "Order confirmation for EST-2026-410 — tracking 1Z999AA10123456784",
        "preview": "Install by October 22, 2026. Sidemark: Nehal Elrefai. PO #PO-77821",
        "from": "Rowley <orders@rowleycompany.com>",
    })
    assert "EST-2026-410" in facts["estimate_numbers"]
    assert "1Z999AA10123456784" in facts["tracking_numbers"]
    assert facts["is_supplier_order"] is True
    assert any(p["date"] == "2026-10-22" for p in facts["proposed_dates"])
    assert facts["sent"] is False


def test_intake_matches_job_adds_note_and_never_sends():
    with get_db() as conn:
        _seed_job(conn)
        result = run_intake(messages=[{
            "source": "gmail_business",
            "message_id": "m-job-1",
            "from": "Nehal Elrefai <nehal@example.com>",
            "subject": "Re: Living room — EST-2026-410",
            "preview": "Can we install by November 3, 2026 at 100 Main Street McLean VA?",
            "date": "2026-10-14",
        }], conn=conn)
        assert result["sent"] is False
        assert result["outbound_policy"] == OUTBOUND_POLICY
        assert result["matched"] == 1
        notes = list_timeline_notes(conn, job_id="job-nehal")
        assert notes["count"] >= 1
        assert "EST-2026-410" in notes["items"][0]["summary"] or "Nehal" in notes["items"][0]["summary"]
        cals = list_calendar_proposals(conn)
        assert cals["count"] >= 1
        assert cals["items"][0]["status"] == "pending"
        approved = approve_calendar_proposal(cals["items"][0]["id"], conn=conn)
        assert approved["ok"] is True
        assert approved["sent"] is False


def test_unmatched_mail_goes_to_review_queue():
    with get_db() as conn:
        _seed_job(conn)
        result = run_intake(messages=[{
            "source": "outlook",
            "message_id": "m-unknown-1",
            "from": "Random Vendor <noreply@spam.test>",
            "subject": "Wholesale catalog 2026",
            "preview": "Browse our new catalog of office chairs.",
            "date": "2026-10-14",
        }], conn=conn)
        assert result["unmatched"] == 1
        assert result["sent"] is False
        queue = list_review_queue(conn)
        assert queue["count"] == 1
        assert queue["items"][0]["from_addr"] == "noreply@spam.test"


def test_tracking_becomes_supplier_order_event():
    with get_db() as conn:
        _seed_job(conn)
        run_intake(messages=[{
            "source": "gmail_personal",
            "message_id": "m-track-1",
            "from": "UPS <mcinfo@ups.com>",
            "subject": "Your order for EST-2026-410 has shipped",
            "preview": "Tracking number 1Z999AA10123456784. Sidemark: Nehal Elrefai.",
            "date": "2026-10-14",
        }], conn=conn)
        events = list_supplier_events(conn, job_id="job-nehal")
        assert events["count"] >= 1
        assert events["items"][0]["tracking_number"] == "1Z999AA10123456784"
        assert events["items"][0]["sent"] == 0
        ev = conn.execute(
            "SELECT event_type FROM job_events WHERE job_id = ? AND event_type = 'supplier_order'",
            ("job-nehal",),
        ).fetchone()
        assert ev is not None


def test_intake_uses_injected_inbox_not_live_readers(monkeypatch):
    def _boom(*_a, **_k):
        raise AssertionError("live inbox reader must not run in tests")

    monkeypatch.setattr(readers, "_fetch_gmail", _boom)
    monkeypatch.setattr(readers, "_fetch_outlook", _boom)
    monkeypatch.setattr(readers, "TEST_INBOX", [{
        "source": "gmail_business",
        "message_id": "injected-only",
        "from": "Nobody <nobody@example.com>",
        "subject": "noise",
        "preview": "unrelated",
    }])
    result = run_intake()
    assert result["sent"] is False
    assert result["scanned"] == 1
    assert result["accounts"]["test_inbox"] is True


def test_module_never_imports_senders():
    import app.services.job_mail_intake.service as svc
    import app.services.job_mail_intake.readers as rdr
    src = (svc.__file__, rdr.__file__, extract_mod.__file__)
    for path in src:
        text = open(path).read().lower()
        for banned in FORBIDDEN_SEND_NAMES:
            assert banned not in text
    assert os.getenv("EMPIRE_TASK_DB", "").startswith(("/tmp", "/var/tmp")) or "empire_test" in os.getenv("EMPIRE_TASK_DB", "")
