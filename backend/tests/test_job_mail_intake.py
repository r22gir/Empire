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
            "source": "gmail_business",
            "account": "business",
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


def test_name_alone_does_not_attach_lauren_smith_to_lauren_jones():
    from app.services.job_mail_intake.match import match_message
    with get_db() as conn:
        ensure_schema(conn)
        conn.execute(
            """INSERT INTO customers (id, name, email, address)
               VALUES ('cust-lj', 'Lauren Jones', 'lauren.jones@example.com', '9 Oak Ave')"""
        )
        try:
            conn.execute(
                """INSERT INTO jobs
                   (id, title, customer_id, status, client_name, client_email, client_address)
                   VALUES ('job-lj', 'Lauren Jones drapery', 'cust-lj', 'pending',
                           'Lauren Jones', 'lauren.jones@example.com', '9 Oak Ave')"""
            )
        except Exception:
            conn.execute(
                """INSERT INTO jobs (id, title, customer_id, status, notes)
                   VALUES ('job-lj', 'Lauren Jones drapery', 'cust-lj', 'pending',
                           'Lauren Jones lauren.jones@example.com')"""
            )
        result = match_message(conn, {
            "from": "Lauren Smith <lauren.smith@other.test>",
            "subject": "Checking in",
            "preview": "Hi, this is Lauren Smith about a sofa.",
        })
        assert result["matched"] is False
        assert result["job_id"] is None


def test_channel_in_supplier_email_does_not_match_client_channel():
    from app.services.job_mail_intake.match import match_message
    with get_db() as conn:
        ensure_schema(conn)
        conn.execute(
            """INSERT INTO customers (id, name, email, address)
               VALUES ('cust-ch', 'Channel', 'client@channel-home.test', '1 Harbor Way')"""
        )
        try:
            conn.execute(
                """INSERT INTO jobs
                   (id, title, customer_id, status, client_name, client_email)
                   VALUES ('job-ch', 'Channel', 'cust-ch', 'pending', 'Channel',
                           'client@channel-home.test')"""
            )
        except Exception:
            conn.execute(
                """INSERT INTO jobs (id, title, customer_id, status, notes)
                   VALUES ('job-ch', 'Channel', 'cust-ch', 'pending', 'Channel client')"""
            )
        result = match_message(conn, {
            "from": "Sales <orders@rowleycompany.com>",
            "subject": "New Channel collection swatches",
            "preview": "Browse the Channel book for this season.",
        })
        assert result["matched"] is False
        assert result["job_id"] is None


def test_second_intake_on_same_messages_adds_nothing():
    with get_db() as conn:
        _seed_job(conn)
        messages = [{
            "source": "gmail_business",
            "account": "business",
            "message_id": "gmail-1",
            "rfc_message_id": "<same-rfc@mail.test>",
            "from": "Nehal Elrefai <nehal@example.com>",
            "subject": "Re: Living room — EST-2026-410",
            "preview": "Confirming the install at 100 Main Street McLean VA.",
            "date": "2026-10-14",
        }, {
            "source": "outlook",
            "account": "outlook",
            "message_id": "outlook-other-id",
            "rfc_message_id": "<same-rfc@mail.test>",
            "from": "Nehal Elrefai <nehal@example.com>",
            "subject": "Re: Living room — EST-2026-410",
            "preview": "Confirming the install at 100 Main Street McLean VA.",
            "date": "2026-10-14",
        }]
        first = run_intake(messages=messages, conn=conn)
        notes_after_first = list_timeline_notes(conn, job_id="job-nehal")["count"]
        cals_after_first = list_calendar_proposals(conn)["count"]
        suppliers_after_first = list_supplier_events(conn, job_id="job-nehal")["count"]
        second = run_intake(messages=messages, conn=conn)
        assert first["matched"] >= 1
        assert second["duplicates"] == len(messages)
        assert second["matched"] == 0
        assert second["unmatched"] == 0
        assert list_timeline_notes(conn, job_id="job-nehal")["count"] == notes_after_first
        assert list_calendar_proposals(conn)["count"] == cals_after_first
        assert list_supplier_events(conn, job_id="job-nehal")["count"] == suppliers_after_first


def test_approve_calendar_proposal_stays_pending_when_insert_fails(monkeypatch):
    with get_db() as conn:
        _seed_job(conn)
        run_intake(messages=[{
            "source": "gmail_business",
            "message_id": "m-cal-fail",
            "from": "Nehal Elrefai <nehal@example.com>",
            "subject": "Re: EST-2026-410",
            "preview": "Install by November 3, 2026 at 100 Main Street McLean VA.",
            "date": "2026-10-14",
        }], conn=conn)
        cals = list_calendar_proposals(conn)
        assert cals["count"] >= 1
        pid = cals["items"][0]["id"]

        def _boom(*_a, **_k):
            raise RuntimeError("organizer down")

        monkeypatch.setattr("app.services.organizer.store.insert_item", _boom)
        result = approve_calendar_proposal(pid, conn=conn, approved_by="founder")
        assert result["ok"] is False
        assert result["status"] == "pending"
        row = dict(conn.execute(
            "SELECT status, approved_by FROM jmi_calendar_proposals WHERE id = ?", (pid,)
        ).fetchone())
        assert row["status"] == "pending"
        assert not row.get("approved_by")


def test_job_mail_routes_are_founder_only(monkeypatch):
    monkeypatch.setenv("FOUNDER_PIN", "246810")
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    denied = client.get("/api/v1/job-mail/review-queue")
    assert denied.status_code in (403, 503)
    denied_run = client.post("/api/v1/job-mail/run")
    assert denied_run.status_code in (403, 503)
    ok = client.get("/api/v1/job-mail/review-queue", headers={"X-Founder-Pin": "246810"})
    assert ok.status_code == 200


def test_approve_records_who_approved():
    with get_db() as conn:
        _seed_job(conn)
        run_intake(messages=[{
            "source": "gmail_business",
            "message_id": "m-cal-ok",
            "from": "Nehal Elrefai <nehal@example.com>",
            "subject": "Re: EST-2026-410",
            "preview": "Install by December 1, 2026 at 100 Main Street McLean VA.",
            "date": "2026-10-14",
        }], conn=conn)
        pid = list_calendar_proposals(conn)["items"][0]["id"]
        result = approve_calendar_proposal(pid, conn=conn, approved_by="founder")
        if result.get("ok"):
            row = dict(conn.execute(
                "SELECT approved_by, status FROM jmi_calendar_proposals WHERE id = ?", (pid,)
            ).fetchone())
            assert row["status"] == "approved"
            assert row["approved_by"] == "founder"


def test_personal_inbox_off_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("JOB_MAIL_PERSONAL_INBOX", raising=False)
    from app.services.job_mail_intake.readers import personal_inbox_enabled, _connected_paths
    assert personal_inbox_enabled() is False
    token = tmp_path / "personal-token.json"
    token.write_text("{}")
    monkeypatch.setenv("GMAIL_PERSONAL_TOKEN_PATH", str(token))
    paths = _connected_paths()
    assert paths.get("gmail_personal") is None


def test_readers_never_mutate_token_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GMAIL_TOKEN_PATH", "/original/business.json")
    from app.services.job_mail_intake import readers as rdr

    def _fake_check(**kwargs):
        assert kwargs.get("token_path") == str(tmp_path / "other.json")
        assert os.environ.get("GMAIL_TOKEN_PATH") == "/original/business.json"
        return {"success": True, "emails": []}

    monkeypatch.setattr("app.services.max.gmail_reader.check_inbox", _fake_check)
    rdr._fetch_gmail("business", str(tmp_path / "other.json"))
    assert os.environ.get("GMAIL_TOKEN_PATH") == "/original/business.json"


def test_account_stored_and_personal_preview_stays_out_of_job_events():
    with get_db() as conn:
        _seed_job(conn)
        run_intake(messages=[{
            "source": "gmail_personal",
            "account": "personal",
            "message_id": "m-personal-1",
            "from": "Nehal Elrefai <nehal@example.com>",
            "subject": "Re: EST-2026-410 private note",
            "preview": "PERSONAL-PREVIEW-SECRET about 100 Main Street McLean VA",
            "date": "2026-10-14",
        }], conn=conn)
        notes = list_timeline_notes(conn, job_id="job-nehal")
        assert notes["count"] >= 1
        assert notes["items"][0]["account"] == "personal"
        events = conn.execute(
            "SELECT summary, metadata FROM job_events WHERE job_id = ?",
            ("job-nehal",),
        ).fetchall()
        blob = " ".join(
            f"{row[0] or ''} {row[1] or ''}" for row in events
        )
        assert "PERSONAL-PREVIEW-SECRET" not in blob
