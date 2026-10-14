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
    intake_status,
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
            "from": "Random Vendor <sales@vendor-catalog.test>",
            "subject": "Stock check for next season",
            "preview": "Do you still need the extra chairs for the lobby?",
            "date": "2026-10-14",
        }], conn=conn)
        assert result["unmatched"] == 1
        assert result["sent"] is False
        queue = list_review_queue(conn)
        assert queue["count"] == 1
        assert queue["items"][0]["from_addr"] == "sales@vendor-catalog.test"


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
    from app.services.job_mail_intake import filters as filt
    src = (svc.__file__, rdr.__file__, extract_mod.__file__, filt.__file__)
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


def test_tie_or_close_score_goes_to_review():
    from app.services.job_mail_intake.match import match_message
    with get_db() as conn:
        ensure_schema(conn)
        conn.execute(
            """INSERT INTO customers (id, name, email, address)
               VALUES ('cust-a', 'Ada West', 'shared@example.com', '10 Pine St'),
                      ('cust-b', 'Bea East', 'shared@example.com', '20 Oak Ave')"""
        )
        for job_id, title, cust, name in (
            ("job-ada", "Ada living drapery", "cust-a", "Ada West"),
            ("job-bea", "Bea dining drapery", "cust-b", "Bea East"),
        ):
            try:
                conn.execute(
                    """INSERT INTO jobs
                       (id, title, customer_id, status, client_name, client_email)
                       VALUES (?, ?, ?, 'pending', ?, 'shared@example.com')""",
                    (job_id, title, cust, name),
                )
            except Exception:
                conn.execute(
                    """INSERT INTO jobs (id, title, customer_id, status, notes)
                       VALUES (?, ?, ?, 'pending', ?)""",
                    (job_id, title, cust, f"{name} shared@example.com"),
                )
        tied = match_message(conn, {
            "from": "Shared Mailbox <shared@example.com>",
            "subject": "Checking both jobs",
            "preview": "Please confirm the shared mailbox thread.",
        })
        assert tied["matched"] is False
        assert tied["reason"] == "ambiguous"
        assert tied["job_id"] is None


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
        assert first["matched"] == 1
        assert first["duplicates"] == 1
        notes_after_first = list_timeline_notes(conn, job_id="job-nehal")["count"]
        assert notes_after_first == 1
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


def test_same_email_in_two_inboxes_is_recorded_once():
    with get_db() as conn:
        _seed_job(conn)
        result = run_intake(messages=[{
            "source": "gmail_business",
            "account": "business",
            "message_id": "biz-mid",
            "rfc_message_id": "<cross-inbox@mail.test>",
            "from": "Nehal Elrefai <nehal@example.com>",
            "subject": "Re: EST-2026-410",
            "preview": "See you at 100 Main Street McLean VA.",
            "date": "2026-10-14",
        }, {
            "source": "outlook",
            "account": "outlook",
            "message_id": "out-mid",
            "rfc_message_id": "<cross-inbox@mail.test>",
            "from": "Nehal Elrefai <nehal@example.com>",
            "subject": "Re: EST-2026-410",
            "preview": "See you at 100 Main Street McLean VA.",
            "date": "2026-10-14",
        }], conn=conn)
        assert result["matched"] == 1
        assert result["duplicates"] == 1
        assert list_timeline_notes(conn, job_id="job-nehal")["count"] == 1
        processed = conn.execute("SELECT COUNT(*) FROM jmi_processed").fetchone()[0]
        assert processed == 1


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
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers.job_mail_intake import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)
    denied = client.get("/api/v1/job-mail/review-queue")
    assert denied.status_code == 403
    denied_run = client.post("/api/v1/job-mail/run")
    assert denied_run.status_code == 403
    wrong = client.get("/api/v1/job-mail/review-queue", headers={"X-Founder-Pin": "0000"})
    assert wrong.status_code == 403
    ok = client.get("/api/v1/job-mail/review-queue", headers={"X-Founder-Pin": "246810"})
    assert ok.status_code == 200
    denied_status = client.get("/api/v1/job-mail/status")
    assert denied_status.status_code == 403
    ok_status = client.get("/api/v1/job-mail/status", headers={"X-Founder-Pin": "246810"})
    assert ok_status.status_code == 200
    paths = {getattr(r, "path", "") for r in router.routes}
    assert "/job-mail/run" in paths
    assert "/job-mail/status" in paths
    assert "/job-mail/calendar-proposals/{proposal_id}/approve" in paths


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


def _seed_emily_completed(conn, *, also_active=False):
    """Synthetic stand-in for live job e0a5b94a / EST-2026-034 / completed."""
    ensure_schema(conn)
    conn.execute(
        """INSERT INTO customers (id, name, email, address)
           VALUES ('cust-emily', 'Emily Richardson',
                   'emily.richardson@clients.test', '44 Willow Lane')"""
    )
    try:
        conn.execute(
            """INSERT INTO jobs
               (id, title, customer_id, status, notes, client_name, client_email,
                client_address, address, job_number)
               VALUES ('e0a5b94a', 'Emily Richardson drapery', 'cust-emily',
                       'completed', 'Quote EST-2026-034 completed install',
                       'Emily Richardson', 'emily.richardson@clients.test',
                       '44 Willow Lane', '44 Willow Lane', 'JOB-2026-034')"""
        )
    except Exception:
        conn.execute(
            """INSERT INTO jobs (id, title, customer_id, status, notes)
               VALUES ('e0a5b94a', 'Emily Richardson drapery', 'cust-emily',
                       'completed',
                       'Emily Richardson emily.richardson@clients.test EST-2026-034')"""
        )
    try:
        conn.execute(
            """INSERT INTO quotes_v2
               (id, quote_number, customer_name, customer_email, customer_address,
                customer_id, job_id, status, created_at, updated_at)
               VALUES ('q-034', 'EST-2026-034', 'Emily Richardson',
                       'emily.richardson@clients.test', '44 Willow Lane',
                       'cust-emily', 'e0a5b94a', 'approved',
                       datetime('now'), datetime('now'))"""
        )
    except Exception:
        pass
    if also_active:
        try:
            conn.execute(
                """INSERT INTO jobs
                   (id, title, customer_id, status, notes, client_name, client_email,
                    client_address, address, job_number)
                   VALUES ('job-emily-active', 'Emily Richardson living drapery',
                           'cust-emily', 'in_progress',
                           'Active follow-up, no estimate token required',
                           'Emily Richardson', 'emily.richardson@clients.test',
                           '44 Willow Lane', '44 Willow Lane', 'JOB-2026-088')"""
            )
        except Exception:
            conn.execute(
                """INSERT INTO jobs (id, title, customer_id, status, notes)
                   VALUES ('job-emily-active', 'Emily Richardson living drapery',
                           'cust-emily', 'in_progress',
                           'Emily Richardson emily.richardson@clients.test 44 Willow Lane')"""
            )


def _ayuda_message(i: int) -> dict:
    edition = "Max-e" if i % 2 == 0 else "Maxine"
    ticket = f"fh-syn-{i:04d}a{i}c"
    who = ("Ana Perez", "Luis Mora", "Sofia Chen", "Diego Ruiz", "Marta Sol")[i % 5]
    return {
        "source": "gmail_business",
        "account": "business",
        "message_id": f"ayuda-{i}",
        "rfc_message_id": f"<ayuda-{i}@empirebox.store>",
        "from": "Max — Empire AI <max@empirebox.store>",
        "to": "empirebox2026@gmail.com",
        "subject": f"Ayuda de {edition}: {who}",
        "preview": (
            f"{edition} · ticket {ticket}\n"
            f"No puedo abrir el portal. Guest note 2026 15:34 EST.\n"
            "Abre el chat de Max → Ayuda de ediciones familiares."
        ),
        "date": "2026-10-14",
    }


def test_ayuda_help_emails_never_attach_completed_emily_job():
    """Live first run: 10 Ayuda de Max-e/Maxine mails attached to e0a5b94a."""
    with get_db() as conn:
        _seed_emily_completed(conn)
        messages = [_ayuda_message(i) for i in range(10)]
        result = run_intake(messages=messages, conn=conn)
        assert result["sent"] is False
        assert result["scanned"] == 10
        assert result["matched"] == 0
        assert result["ignored"] == 10
        assert result["unmatched"] == 0
        notes = list_timeline_notes(conn, job_id="e0a5b94a")
        assert notes["count"] == 0
        queue = list_review_queue(conn)
        assert queue["count"] == 0
        kinds = [r[0] for r in conn.execute("SELECT kind FROM jmi_processed").fetchall()]
        assert kinds == ["ignored"] * 10


def test_lone_estimate_token_does_not_attach():
    from app.services.job_mail_intake.match import match_message
    from app.services.job_mail_intake.extract import estimate_numbers

    assert estimate_numbers("Please see EST-2026-034") == ["EST-2026-034"]
    assert estimate_numbers("EST2026034 timezone EST 2026 15:34") == []
    assert estimate_numbers("estimated 2026-034") == []

    with get_db() as conn:
        _seed_emily_completed(conn)
        result = match_message(conn, {
            "from": "Vendor Desk <desk@fabrics.test>",
            "subject": "EST-2026-034",
            "preview": "Confirming EST-2026-034 from last season.",
        })
        assert result["matched"] is False
        assert result["job_id"] is None
        intake = run_intake(messages=[{
            "source": "gmail_business",
            "message_id": "lone-est-034",
            "from": "Vendor Desk <desk@fabrics.test>",
            "subject": "EST-2026-034",
            "preview": "Confirming EST-2026-034 from last season.",
            "date": "2026-10-14",
        }], conn=conn)
        assert intake["matched"] == 0
        assert intake["unmatched"] == 1
        assert list_timeline_notes(conn, job_id="e0a5b94a")["count"] == 0


def test_completed_job_ranks_below_active():
    from app.services.job_mail_intake.match import match_message
    with get_db() as conn:
        _seed_emily_completed(conn, also_active=True)
        result = match_message(conn, {
            "from": "Emily Richardson <emily.richardson@clients.test>",
            "subject": "Follow up on EST-2026-034",
            "preview": "Can we reuse the drapery at 44 Willow Lane?",
        })
        assert result["matched"] is True
        assert result["job_id"] == "job-emily-active"
        assert result["job_id"] != "e0a5b94a"


def test_outlook_off_by_default_even_with_token(monkeypatch, tmp_path):
    monkeypatch.delenv("JOB_MAIL_OUTLOOK_INBOX", raising=False)
    token = tmp_path / "outlook-token.json"
    token.write_text("{}")
    monkeypatch.setenv("OUTLOOK_TOKEN_PATH", str(token))
    monkeypatch.setattr(
        "app.services.max.outlook_reader.token_path",
        lambda override=None: token,
        raising=False,
    )
    from app.services.job_mail_intake.readers import (
        _connected_paths,
        outlook_inbox_enabled,
    )
    assert outlook_inbox_enabled() is False
    paths = _connected_paths()
    assert paths.get("outlook") is None
    assert "outlook" not in paths.get("sources", [])


def test_outlook_opt_in_uses_token(monkeypatch, tmp_path):
    token = tmp_path / "outlook-token.json"
    token.write_text("{}")
    monkeypatch.setenv("JOB_MAIL_OUTLOOK_INBOX", "1")
    monkeypatch.setenv("OUTLOOK_TOKEN_PATH", str(token))
    monkeypatch.setattr(
        "app.services.max.outlook_reader.token_path",
        lambda override=None: token,
        raising=False,
    )
    from app.services.job_mail_intake.readers import (
        _connected_paths,
        outlook_inbox_enabled,
    )
    assert outlook_inbox_enabled() is True
    paths = _connected_paths()
    assert paths.get("outlook") == str(token)
    assert "outlook" in paths.get("sources", [])


def test_scan_summary_warning_and_status(caplog):
    import logging
    caplog.set_level(logging.WARNING, logger="job_mail_intake")
    with get_db() as conn:
        _seed_emily_completed(conn)
        result = run_intake(messages=[_ayuda_message(0), {
            "source": "gmail_business",
            "message_id": "noise-status",
            "from": "Random Vendor <sales@vendor-catalog.test>",
            "subject": "Stock check for next season",
            "preview": "Do you still need the extra chairs for the lobby?",
            "date": "2026-10-14",
        }], conn=conn)
        assert result["ignored"] == 1
        assert result["unmatched"] == 1
        assert result["matched"] == 0
        assert "job-mail scan:" in caplog.text
        assert "scanned=2" in caplog.text
        assert "matched=0" in caplog.text
        assert "ignored=1" in caplog.text
        status = intake_status(conn)
        assert status["scanned"] == 2
        assert status["matched"] == 0
        assert status["unmatched"] == 1
        assert status["ignored"] == 1
        assert status["sent"] is False
        assert status["outlook_inbox_enabled"] is False


def test_empire_is_never_a_supplier():
    from app.services.job_mail_intake.extract import extract_mail_facts
    facts = extract_mail_facts({
        "from": "Max — Empire AI <max@empirebox.store>",
        "subject": "Order confirmation — tracking 1Z999AA10123456784",
        "preview": "Your order has shipped via UPS. Empire warehouse update.",
    })
    assert facts["is_supplier_order"] is False
    named = extract_mail_facts({
        "from": "Empire <empirebox2026@gmail.com>",
        "subject": "Purchase order PO-9911",
        "preview": "We have received your order.",
    })
    assert named["is_supplier_order"] is False


def test_founder_and_max_self_sends_are_ignored():
    with get_db() as conn:
        _seed_job(conn)
        result = run_intake(messages=[{
            "source": "gmail_business",
            "message_id": "self-founder",
            "from": "Rafael <empirebox2026@gmail.com>",
            "subject": "Re: Living room — EST-2026-410",
            "preview": "Install at 100 Main Street McLean VA",
            "date": "2026-10-14",
        }, {
            "source": "gmail_business",
            "message_id": "self-personal",
            "from": "Rafael <rafa22giraldo@gmail.com>",
            "subject": "Empire morning brief",
            "preview": "Today's jobs and quotes.",
            "date": "2026-10-14",
        }, {
            "source": "gmail_business",
            "message_id": "self-max",
            "from": "Max — Empire AI <max@empirebox.store>",
            "subject": "Tu acceso a AMP",
            "preview": "Link to the family edition.",
            "date": "2026-10-14",
        }], conn=conn)
        assert result["ignored"] == 3
        assert result["matched"] == 0
        assert list_timeline_notes(conn, job_id="job-nehal")["count"] == 0
        assert list_review_queue(conn)["count"] == 0


def _seed_willard_open(conn):
    """Synthetic stand-in for Willard + EST-2026-110 (open job)."""
    ensure_schema(conn)
    conn.execute(
        """INSERT INTO customers (id, name, email, address, company)
           VALUES ('cust-willard', 'Willard Hotel',
                   'purchasing@willard.test', '1401 Pennsylvania Ave',
                   'Willard InterContinental')"""
    )
    contacts = '[{"name":"Maggie Oneil","email":"maggie.oneil@willard.test"}]'
    try:
        conn.execute(
            """INSERT INTO jobs
               (id, title, customer_id, status, notes, client_name, client_email,
                client_address, address, job_number, contacts)
               VALUES ('job-willard', 'Willard InterContinental lobby',
                       'cust-willard', 'in_progress',
                       'Quote EST-2026-110 lobby drapery',
                       'Willard Hotel', 'purchasing@willard.test',
                       '1401 Pennsylvania Ave', '1401 Pennsylvania Ave',
                       'JOB-2026-0110', ?)""",
            (contacts,),
        )
    except Exception:
        conn.execute(
            """INSERT INTO jobs (id, title, customer_id, status, notes)
               VALUES ('job-willard', 'Willard InterContinental lobby',
                       'cust-willard', 'in_progress',
                       'Willard Hotel EST-2026-110 purchasing@willard.test')"""
        )
    try:
        conn.execute(
            """INSERT INTO quotes_v2
               (id, quote_number, customer_name, customer_email, customer_address,
                customer_id, job_id, project_name, status, created_at, updated_at)
               VALUES ('q-110', 'EST-2026-110', 'Willard Hotel',
                       'purchasing@willard.test', '1401 Pennsylvania Ave',
                       'cust-willard', 'job-willard', 'Willard lobby',
                       'sent', datetime('now'), datetime('now'))"""
        )
    except Exception:
        pass


def _seed_watson_job(conn):
    ensure_schema(conn)
    conn.execute(
        """INSERT INTO customers (id, name, email, address, company)
           VALUES ('cust-watson', 'Watson Client',
                   'office@watsonclient.test', '10 Harbor St',
                   'Watson Client LLC')"""
    )
    contacts = (
        '[{"name":"Watson & Watson","email":"watsonins@verizon.net",'
        '"company":"Watson & Watson"}]'
    )
    try:
        conn.execute(
            """INSERT INTO jobs
               (id, title, customer_id, status, notes, client_name, client_email,
                job_number, contacts)
               VALUES ('job-watson', 'Watson insurance drapery',
                       'cust-watson', 'scheduled',
                       'Designer contact Watson & Watson',
                       'Watson Client', 'office@watsonclient.test',
                       'JOB-2026-0010', ?)""",
            (contacts,),
        )
    except Exception:
        conn.execute(
            """INSERT INTO jobs (id, title, customer_id, status, notes)
               VALUES ('job-watson', 'Watson insurance drapery',
                       'cust-watson', 'scheduled',
                       'watsonins@verizon.net Watson & Watson JOB-2026-0010')"""
        )


def _seed_mariella_job(conn):
    ensure_schema(conn)
    conn.execute(
        """INSERT INTO customers (id, name, email)
           VALUES ('cust-mariella', 'Atelier Client', 'atelier@clients.test')"""
    )
    contacts = '[{"name":"Mariella","email":"mariella@atelier.test"}]'
    try:
        conn.execute(
            """INSERT INTO jobs
               (id, title, customer_id, status, notes, client_name, job_number, contacts)
               VALUES ('job-mariella', 'Atelier dining drapery',
                       'cust-mariella', 'pending', 'Designer Mariella',
                       'Atelier Client', 'JOB-2026-0003', ?)""",
            (contacts,),
        )
    except Exception:
        conn.execute(
            """INSERT INTO jobs (id, title, customer_id, status, notes)
               VALUES ('job-mariella', 'Atelier dining drapery',
                       'cust-mariella', 'pending',
                       'Mariella mariella@atelier.test JOB-2026-0003')"""
        )


def test_willard_plus_est_2026_110_attaches():
    from app.services.job_mail_intake.match import match_message
    with get_db() as conn:
        _seed_willard_open(conn)
        result = match_message(conn, {
            "from": "Rowley <orders@rowleycompany.com>",
            "subject": "Willard fabric — EST-2026-110",
            "preview": "Confirming the Willard lobby order for EST-2026-110.",
        })
        assert result["matched"] is True
        assert result["job_id"] == "job-willard"
        assert "estimate_open" in (result.get("reason") or "")
        intake = run_intake(messages=[{
            "source": "gmail_business",
            "message_id": "willard-est-110",
            "from": "Rowley <orders@rowleycompany.com>",
            "subject": "Willard fabric — EST-2026-110",
            "preview": "Confirming the Willard lobby order for EST-2026-110.",
            "date": "2026-10-14",
        }], conn=conn)
        assert intake["matched"] == 1
        assert list_timeline_notes(conn, job_id="job-willard")["count"] == 1


def test_help_email_still_ignored_when_est_110_exists():
    with get_db() as conn:
        _seed_willard_open(conn)
        msg = _ayuda_message(1)
        msg["preview"] = msg["preview"] + " Mention of EST-2026-110 in a ticket."
        result = run_intake(messages=[msg], conn=conn)
        assert result["ignored"] == 1
        assert result["matched"] == 0
        assert list_timeline_notes(conn, job_id="job-willard")["count"] == 0
        assert list_review_queue(conn)["count"] == 0


def test_watson_attaches_through_job_contact():
    from app.services.job_mail_intake.match import match_message
    with get_db() as conn:
        _seed_watson_job(conn)
        result = match_message(conn, {
            "from": "Watson & Watson <watsonins@verizon.net>",
            "subject": "Fabric approval for the living room",
            "preview": "Please hold the reserve until we confirm.",
        })
        assert result["matched"] is True
        assert result["job_id"] == "job-watson"
        assert "contact" in (result.get("reason") or "")
        by_domain = match_message(conn, {
            "from": "Watson assistant <front@verizon.net>",
            "subject": "Measure window",
            "preview": "Sending widths this afternoon.",
        })
        assert by_domain["matched"] is True
        assert by_domain["job_id"] == "job-watson"
        assert "contact_domain" in (by_domain.get("reason") or "")


def test_mariella_contact_and_job_number_are_strong():
    from app.services.job_mail_intake.match import match_message
    with get_db() as conn:
        _seed_mariella_job(conn)
        by_contact = match_message(conn, {
            "from": "Mariella <mariella@atelier.test>",
            "subject": "Measure photos",
            "preview": "Sending the dining room widths.",
        })
        assert by_contact["matched"] is True
        assert by_contact["job_id"] == "job-mariella"
        by_code = match_message(conn, {
            "from": "Shop <cut@workroom.test>",
            "subject": "Status on JOB-2026-0003",
            "preview": "Panels are on the table.",
        })
        assert by_code["matched"] is True
        assert by_code["job_id"] == "job-mariella"
        assert "job_number" in (by_code.get("reason") or "")


def test_cf_code_is_a_strong_key():
    from app.services.job_mail_intake.match import match_message
    with get_db() as conn:
        ensure_schema(conn)
        conn.execute(
            """INSERT INTO customers (id, name, email)
               VALUES ('cust-cf', 'Bench Client', 'bench@clients.test')"""
        )
        try:
            conn.execute(
                """INSERT INTO jobs
                   (id, title, customer_id, status, notes, client_name, job_number)
                   VALUES ('job-cf', 'Freestanding bench', 'cust-cf', 'pending',
                           'WoodCraft CF-2026-001', 'Bench Client', 'JOB-2026-0099')"""
            )
        except Exception:
            conn.execute(
                """INSERT INTO jobs (id, title, customer_id, status, notes)
                   VALUES ('job-cf', 'Freestanding bench', 'cust-cf', 'pending',
                           'CF-2026-001 Bench Client')"""
            )
        try:
            conn.execute(
                """INSERT INTO quotes_v2
                   (id, quote_number, customer_name, customer_id, job_id,
                    status, created_at, updated_at)
                   VALUES ('q-cf', 'CF-2026-001', 'Bench Client', 'cust-cf',
                           'job-cf', 'sent', datetime('now'), datetime('now'))"""
            )
        except Exception:
            pass
        result = match_message(conn, {
            "from": "Mill <shop@wood.test>",
            "subject": "CF-2026-001 shop drawing",
            "preview": "Ready for review.",
        })
        assert result["matched"] is True
        assert result["job_id"] == "job-cf"
        assert "cf_number" in (result.get("reason") or "")


def test_supplier_sidemark_links_to_customer_when_no_job_token():
    from app.services.job_mail_intake.extract import extract_mail_facts, order_numbers, sidemarks
    from app.services.job_mail_intake.match import match_message

    blob = (
        "Sidemark: Nehal Elrefai\n"
        "Thank you. See our order policies and confirmation details."
    )
    assert sidemarks(blob) == ["Nehal Elrefai"]
    assert "licies" not in [x.lower() for x in order_numbers(blob)]
    assert order_numbers("order policies confirmation number") == []
    facts = extract_mail_facts({
        "from": "Rowley <orders@rowleycompany.com>",
        "subject": "Your order has shipped",
        "preview": blob + " Tracking 1Z999AA10123456784",
    })
    assert facts["is_supplier_order"] is True
    assert facts["sidemarks"] == ["Nehal Elrefai"]

    with get_db() as conn:
        _seed_job(conn)
        result = match_message(conn, {
            "from": "Rowley <orders@rowleycompany.com>",
            "subject": "Your order has shipped",
            "preview": blob + " Tracking 1Z999AA10123456784",
        })
        assert result["matched"] is True
        assert result["job_id"] == "job-nehal"
        assert "sidemark" in (result.get("reason") or "")


def test_several_open_jobs_for_one_customer_are_ambiguous():
    from app.services.job_mail_intake.match import match_message
    with get_db() as conn:
        _seed_emily_completed(conn, also_active=True)
        try:
            conn.execute(
                """INSERT INTO jobs
                   (id, title, customer_id, status, notes, client_name, client_email,
                    job_number)
                   VALUES ('job-emily-two', 'Emily Richardson bedroom',
                           'cust-emily', 'pending',
                           'Second open job',
                           'Emily Richardson', 'emily.richardson@clients.test',
                           'JOB-2026-089')"""
            )
        except Exception:
            conn.execute(
                """INSERT INTO jobs (id, title, customer_id, status, notes)
                   VALUES ('job-emily-two', 'Emily Richardson bedroom',
                           'cust-emily', 'pending',
                           'Emily Richardson emily.richardson@clients.test')"""
            )
        result = match_message(conn, {
            "from": "Emily Richardson <emily.richardson@clients.test>",
            "subject": "Quick question",
            "preview": "Can you call me tomorrow?",
        })
        assert result["matched"] is False
        assert result["reason"] == "ambiguous"
        intake = run_intake(messages=[{
            "source": "gmail_business",
            "message_id": "emily-multi-open",
            "from": "Emily Richardson <emily.richardson@clients.test>",
            "subject": "Quick question",
            "preview": "Can you call me tomorrow?",
            "date": "2026-10-14",
        }], conn=conn)
        assert intake["matched"] == 0
        assert intake["unmatched"] == 1
        assert list_review_queue(conn)["count"] == 1


def test_noreply_login_and_marketing_skipped_before_queue():
    with get_db() as conn:
        _seed_willard_open(conn)
        result = run_intake(messages=[{
            "source": "gmail_business",
            "message_id": "login-1",
            "from": "Google <no-reply@accounts.google.com>",
            "subject": "Your login code is 482193",
            "preview": "Use this login code to sign in. EST-2026-110 is in the footer.",
            "date": "2026-10-14",
        }, {
            "source": "gmail_business",
            "message_id": "mkt-1",
            "from": "Wayfair <deals@wayfair.com>",
            "subject": "Flash sale — 40% off lookbook",
            "preview": "Shop now. Limited time. Unsubscribe at the bottom.",
            "date": "2026-10-14",
        }, {
            "source": "gmail_business",
            "message_id": "nr-1",
            "from": "Alerts <noreply@bank-alerts.test>",
            "subject": "Account notice",
            "preview": "This is an automated no-reply message.",
            "date": "2026-10-14",
        }], conn=conn)
        assert result["ignored"] == 3
        assert result["matched"] == 0
        assert result["unmatched"] == 0
        assert list_review_queue(conn)["count"] == 0
        assert list_timeline_notes(conn, job_id="job-willard")["count"] == 0


def _seed_mccool_customer_only(conn):
    """Sidemark McCool — customer exists, no open job (replay SO1391374)."""
    ensure_schema(conn)
    conn.execute(
        """INSERT INTO customers (id, name, email, notes)
           VALUES ('cust-mccool', 'McCool', 'mccool@clients.test',
                   'Sidemark McCool')"""
    )


def test_sidemark_mccool_keeps_customer_on_queue_and_supplier_event():
    from app.services.job_mail_intake.match import match_message
    with get_db() as conn:
        _seed_mccool_customer_only(conn)
        msg = {
            "source": "gmail_business",
            "message_id": "rowley-so1391374",
            "from": "Rowley Company <noreply@rowleycompany.com>",
            "subject": "SO1391374",
            "preview": "Sidemark: McCool\nSales order SO1391374 is in production.",
            "date": "2026-10-14",
        }
        matched = match_message(conn, msg)
        assert matched["matched"] is False
        assert matched["job_id"] is None
        assert matched["customer_id"] == "cust-mccool"
        assert matched["customer_name"] == "McCool"
        result = run_intake(messages=[msg], conn=conn)
        assert result["matched"] == 0
        assert result["ignored"] == 0
        assert result["unmatched"] == 1
        queue = list_review_queue(conn)
        assert queue["count"] == 1
        assert queue["items"][0]["customer_id"] == "cust-mccool"
        assert queue["items"][0]["customer_name"] == "McCool"
        events = list_supplier_events(conn)
        assert events["count"] >= 1
        assert events["items"][0]["customer_id"] == "cust-mccool"
        assert events["items"][0]["customer_name"] == "McCool"
        assert events["items"][0].get("job_id") in (None, "")


def test_supplier_invoice_receipt_order_not_dropped_as_noise():
    from app.services.job_mail_intake.extract import extract_mail_facts, is_supplier_mail
    replay = [
        {
            "source": "gmail_business",
            "message_id": "keystone-inv",
            "from": "Keystone Bros <noreply@keystonebros.com>",
            "subject": "Invoice for order 6471485-00",
            "preview": "Invoice for order 6471485-00 is attached. Unsubscribe below.",
            "list_unsubscribe": "<mailto:unsub@keystonebros.com>",
            "date": "2026-10-14",
        },
        {
            "source": "gmail_business",
            "message_id": "angels-receipt",
            "from": "Angel's Distributing <noreply@angelsdistributing.com>",
            "subject": "Receipt for payment of $753.27",
            "preview": "Receipt for payment of $753.27. Thank you for your order.",
            "date": "2026-10-14",
        },
        {
            "source": "gmail_business",
            "message_id": "angels-pkg",
            "from": "Angel's Distributing <noreply@angelsdistributing.com>",
            "subject": "Your order PKG-26036 has been prepared",
            "preview": "Your order PKG-26036 has been prepared and will ship shortly.",
            "date": "2026-10-14",
        },
    ]
    for msg in replay:
        facts = extract_mail_facts(msg)
        assert facts["is_supplier_order"] is True, msg["subject"]
        assert is_supplier_mail(msg) is True, msg["subject"]
    with get_db() as conn:
        ensure_schema(conn)
        result = run_intake(messages=replay, conn=conn)
        assert result["ignored"] == 0
        assert result["matched"] == 0
        assert result["unmatched"] == 3
        queue = list_review_queue(conn)
        assert queue["count"] == 3
        subjects = {item["subject"] for item in queue["items"]}
        assert "Invoice for order 6471485-00" in subjects
        assert "Receipt for payment of $753.27" in subjects
        assert "Your order PKG-26036 has been prepared" in subjects
        events = list_supplier_events(conn)
        assert events["count"] == 3


def test_one_word_contact_name_emma_does_not_attach():
    from app.services.job_mail_intake.match import match_message
    with get_db() as conn:
        ensure_schema(conn)
        conn.execute(
            """INSERT INTO customers (id, name, email)
               VALUES ('cust-emma-job', 'Atelier East', 'atelier.east@clients.test')"""
        )
        contacts = '[{"name":"Emma"}]'
        try:
            conn.execute(
                """INSERT INTO jobs
                   (id, title, customer_id, status, notes, client_name, client_email,
                    job_number, contacts)
                   VALUES ('job-emma-listed', 'East dining drapery',
                           'cust-emma-job', 'pending', 'Designer listed as Emma',
                           'Atelier East', 'atelier.east@clients.test',
                           'JOB-2026-0077', ?)""",
                (contacts,),
            )
        except Exception:
            conn.execute(
                """INSERT INTO jobs (id, title, customer_id, status, notes)
                   VALUES ('job-emma-listed', 'East dining drapery',
                           'cust-emma-job', 'pending', 'Designer listed as Emma')"""
            )
        lone = match_message(conn, {
            "from": "Emma Stone <emma.stone@other.test>",
            "subject": "Checking in",
            "preview": "Hi, this is Emma about a sofa.",
        })
        assert lone["matched"] is False
        assert lone["job_id"] is None
        # Email or domain on the listed contact still attaches.
        try:
            conn.execute(
                "UPDATE jobs SET contacts = ? WHERE id = 'job-emma-listed'",
                ('[{"name":"Emma","email":"emma.stone@other.test"}]',),
            )
        except Exception:
            pass
        with_email = match_message(conn, {
            "from": "Emma Stone <emma.stone@other.test>",
            "subject": "Checking in",
            "preview": "Hi, this is Emma about a sofa.",
        })
        if conn.execute(
            "SELECT contacts FROM jobs WHERE id = 'job-emma-listed'"
        ).fetchone():
            assert with_email["matched"] is True
            assert with_email["job_id"] == "job-emma-listed"
