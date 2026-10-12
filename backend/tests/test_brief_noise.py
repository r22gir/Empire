"""Brief noise filters: money, quotes, mail, decisions, family, calendar, NEW, bullets."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.services.max.brief_filters import (
    DEFAULT_TEST_CLIENT_PATTERNS,
    dedupe_mail,
    filter_followup_quotes,
    filter_real_money,
    format_et,
    is_bank_notice,
    is_flagged_test,
    is_noise_client,
    is_promotional_mail,
    is_test_family_ticket,
    keep_founder_decision,
    mail_account_label,
    stale_task_count,
    test_client_patterns as brief_test_client_patterns,
)
from app.services.max.daily_brief import build_and_persist_brief, build_brief_sections, render_brief_plain
from app.services.max.desks.live_data import snapshot
from tests.test_desk_live_jobs import _seed


@pytest.fixture
def seeded_db(isolated_empire_db):
    now = datetime(2026, 10, 12, 8, 0, 0)
    from app.db.database import get_db

    with get_db() as conn:
        _seed(conn, now)
    return now


def test_watch_list_uses_systemd_not_docker():
    from app.services.max.desks.live_services import LIVE_SERVICES, check_live_services

    kinds = {s["id"]: s["kind"] for s in LIVE_SERVICES}
    assert kinds["empire-amp"] == "systemd"
    assert kinds["empire-maxine"] == "systemd"
    rows = check_live_services(
        port_checker=lambda p: True,
        container_checker=lambda n: False,
        systemd_checker=lambda n: True,
        process_checker=lambda n: True,
        disk_checker=lambda p="/": {"id": "disk", "name": "disk", "up": True, "pct": 10, "detail": "ok"},
    )
    by_id = {r["id"]: r for r in rows}
    assert by_id["empire-amp"]["up"] is True
    assert "not running" not in by_id["empire-amp"]["detail"]
    assert "systemd" in by_id["empire-amp"]["detail"]


def test_money_excludes_test_purge_and_zero_sorted(seeded_db):
    from app.db.database import get_db

    now = seeded_db
    with get_db() as conn:
        conn.execute(
            "INSERT INTO customers (id, name, email) VALUES ('c-test', 'TEST RESIDUE', 't@example.com')"
        )
        conn.execute(
            "INSERT INTO customers (id, name, email) VALUES ('c-purge', 'purge candidate', 'p@example.com')"
        )
        conn.execute(
            """INSERT INTO invoices
               (id, invoice_number, customer_id, status, total, amount_paid, balance_due, due_date, created_at)
               VALUES ('inv-t', 'INV-TEST', 'c-test', 'sent', 0, 0, 0, ?, ?)""",
            ((now - timedelta(days=5)).strftime("%Y-%m-%d"), now.isoformat()),
        )
        conn.execute(
            """INSERT INTO invoices
               (id, invoice_number, customer_id, status, total, amount_paid, balance_due, due_date, created_at)
               VALUES ('inv-p', 'INV-PURGE', 'c-purge', 'sent', 50, 0, 50, ?, ?)""",
            ((now - timedelta(days=2)).strftime("%Y-%m-%d"), now.isoformat()),
        )
        conn.execute(
            """INSERT INTO invoices
               (id, invoice_number, customer_id, status, total, amount_paid, balance_due, due_date, created_at)
               VALUES ('inv-z', 'INV-ZERO', 'cust-nelma', 'sent', 0, 0, 0, ?, ?)""",
            ((now - timedelta(days=1)).strftime("%Y-%m-%d"), now.isoformat()),
        )
    unpaid = snapshot(now)["unpaid_invoices"]
    names = [i["name"] for i in unpaid]
    assert "INV-2044" in names
    assert "INV-2045" in names
    assert "INV-TEST" not in names
    assert "INV-PURGE" not in names
    assert "INV-ZERO" not in names
    amounts = [i["amount"] for i in unpaid]
    assert amounts == sorted(amounts, reverse=True)


def test_quotes_exclude_zero_draft_test_and_old(seeded_db):
    from app.db.database import get_db

    now = seeded_db
    with get_db() as conn:
        conn.execute(
            """INSERT INTO quotes_v2
               (id, quote_number, customer_name, status, total, sent_at, created_at, updated_at)
               VALUES ('q-zero', 'EST-0', 'Customer', 'draft', 0, ?, ?, ?)""",
            (now.isoformat(), now.isoformat(), now.isoformat()),
        )
        conn.execute(
            """INSERT INTO quotes_v2
               (id, quote_number, customer_name, status, total, sent_at, created_at, updated_at)
               VALUES ('q-old', 'EST-OLD', 'Nelma Rivera', 'sent', 900, ?, ?, ?)""",
            (
                (now - timedelta(days=90)).isoformat(),
                (now - timedelta(days=90)).isoformat(),
                (now - timedelta(days=90)).isoformat(),
            ),
        )
        conn.execute(
            """INSERT INTO quotes_v2
               (id, quote_number, customer_name, status, total, sent_at, created_at, updated_at)
               VALUES ('q-test', 'EST-T', 'E2E Test', 'sent', 400, ?, ?, ?)""",
            (now.isoformat(), now.isoformat(), now.isoformat()),
        )
    quotes = snapshot(now)["stale_quotes"]
    names = [q["name"] for q in quotes]
    assert "EST-2026-088" in names
    assert "EST-0" not in names
    assert "EST-OLD" not in names
    assert "EST-T" not in names


def test_quotes_cap_plus_n_more(seeded_db):
    from app.db.database import get_db

    now = seeded_db
    with get_db() as conn:
        for i in range(12):
            conn.execute(
                """INSERT INTO quotes_v2
                   (id, quote_number, customer_name, status, total, sent_at, created_at, updated_at)
                   VALUES (?, ?, 'Nelma Rivera', 'sent', 100, ?, ?, ?)""",
                (
                    f"q-cap-{i}",
                    f"EST-CAP-{i:02d}",
                    (now - timedelta(days=i + 1)).isoformat(),
                    (now - timedelta(days=i + 1)).isoformat(),
                    now.isoformat(),
                ),
            )
    sections = build_brief_sections(snapshot(now), previous={"quote_items": []}, now=now, service_rows=[])
    text = sections["quotes"]["text"]
    assert text.count("• ") <= 10
    assert "+3 more" in text or "+ more" in text or "+" in text and "more" in text


def test_first_brief_seeds_baseline_without_new_tags(seeded_db):
    first = build_and_persist_brief(now=seeded_db, service_rows=[])
    assert " NEW" not in first["text_plain"]
    assert " new" not in first["html"].lower() or "· 0 new" not in first["html"]
    sections = first["sections"]
    for key in ("today_and_week", "money", "quotes", "leads_and_mail"):
        assert sections[key].get("new_count", 0) == 0


def test_test_client_patterns_are_one_configurable_list():
    assert "*test*" in DEFAULT_TEST_CLIENT_PATTERNS
    assert "MOCK-SWEEP*" in DEFAULT_TEST_CLIENT_PATTERNS
    assert "Jane Smith" in DEFAULT_TEST_CLIENT_PATTERNS
    assert "Customer" in DEFAULT_TEST_CLIENT_PATTERNS
    assert brief_test_client_patterns() == DEFAULT_TEST_CLIENT_PATTERNS
    assert is_noise_client("TrustTest")
    assert is_noise_client("MOCK-SWEEP-014")
    assert is_noise_client("Jane Smith")
    assert is_noise_client("Customer")
    assert not is_noise_client("Nelma Rivera")
    assert is_flagged_test({"customer": "Woodcraft", "is_test": 1})
    assert not is_flagged_test({"customer": "Nelma Rivera", "is_test": 0})


def test_quotes_exclude_trusttest_mock_jane_and_is_test_flag(seeded_db):
    from app.db.database import get_db

    now = seeded_db
    with get_db() as conn:
        for qid, number, customer, flag in (
            ("q-tt", "EST-TT", "TrustTest", 0),
            ("q-ms", "EST-MS", "MOCK-SWEEP-014", 0),
            ("q-js", "EST-JS", "Jane Smith", 0),
            ("q-flag", "EST-FLAG", "Nelma Rivera", 1),
        ):
            conn.execute(
                """INSERT INTO quotes_v2
                   (id, quote_number, customer_name, status, total, sent_at, created_at, updated_at, is_test)
                   VALUES (?, ?, ?, 'sent', 400, ?, ?, ?, ?)""",
                (qid, number, customer, now.isoformat(), now.isoformat(), now.isoformat(), flag),
            )
    names = [q["name"] for q in snapshot(now)["stale_quotes"]]
    assert "EST-2026-088" in names
    assert "EST-TT" not in names
    assert "EST-MS" not in names
    assert "EST-JS" not in names
    assert "EST-FLAG" not in names


def test_mail_filters_promo_bank_dedupe_and_labels_account(seeded_db):
    import app.services.organizer.mail as mailmod

    mailmod.TEST_INBOX = [
        {
            "source": "gmail",
            "message_id": "human-1",
            "thread_id": "th-human",
            "from": "Marley <marley@example.com>",
            "subject": "Install date?",
            "date": "2026-10-11T12:00:00",
            "preview": "Can we move the drapery install?",
            "unread": True,
            "account": "gmail",
        },
        {
            "source": "gmail",
            "message_id": "human-1-dup",
            "thread_id": "th-human",
            "from": "Marley <marley@example.com>",
            "subject": "Re: Install date?",
            "date": "2026-10-11T13:00:00",
            "preview": "Same thread",
            "unread": True,
            "account": "gmail",
        },
        {
            "source": "gmail",
            "message_id": "promo-1",
            "from": "Macy's <deals@macys.com>",
            "subject": "Weekend sale",
            "date": "2026-10-11T10:00:00",
            "preview": "40% off",
            "unread": True,
            "labels": ["CATEGORY_PROMOTIONS"],
        },
        {
            "source": "outlook",
            "message_id": "news-1",
            "from": "Wayfair <hello@wayfair.com>",
            "subject": "Your weekly lookbook",
            "date": "2026-10-10T09:00:00",
            "preview": "Unsubscribe anytime",
            "list_unsubscribe": "<mailto:unsub@wayfair.com>",
        },
        {
            "source": "gmail",
            "message_id": "crate-1",
            "from": "Crate & Barrel <noreply@crateandbarrel.com>",
            "subject": "Market invite — webinar this week",
            "date": "2026-10-11T07:00:00",
            "preview": "Join our design webinar",
        },
        {
            "source": "gmail",
            "message_id": "hd-1",
            "from": "Home Depot Pro Xtra <noreply@homedepot.com>",
            "subject": "Pro Xtra rewards",
            "date": "2026-10-11T06:00:00",
            "preview": "Don't miss this exclusive offer",
        },
        {
            "source": "outlook",
            "message_id": "zelle-1",
            "from": "Bank of America <alerts@bofa.com>",
            "subject": "You received a Zelle payment",
            "date": "2026-10-11T05:00:00",
            "preview": "Zelle from a customer",
        },
        {
            "source": "gmail",
            "message_id": "dep-1",
            "from": "Chase <no-reply@chase.com>",
            "subject": "Mobile deposit received",
            "date": "2026-10-11T04:00:00",
            "preview": "Your mobile deposit is available",
        },
        {
            "source": "outlook",
            "message_id": "nelma-1",
            "from": "Nelma <nelma@example.com>",
            "subject": "Fabric confirmation",
            "date": "2026-10-11T08:00:00",
            "preview": "Please confirm the lining",
            "unread": True,
            "account": "outlook",
        },
    ]
    try:
        snap = snapshot(seeded_db)
        subjects = [m["name"] for m in snap["pending_mail"]]
        assert "Install date?" in subjects
        assert "Fabric confirmation" in subjects
        assert "Re: Install date?" not in subjects
        assert "Weekend sale" not in subjects
        assert "Your weekly lookbook" not in subjects
        assert "Market invite — webinar this week" not in subjects
        assert "Pro Xtra rewards" not in subjects
        assert "You received a Zelle payment" not in subjects
        assert "Mobile deposit received" not in subjects
        labels = {m["name"]: m.get("account_label") for m in snap["pending_mail"]}
        assert labels["Install date?"] == "Business Gmail"
        assert labels["Fabric confirmation"] == "Outlook/Nelma"
        bank_names = [m["name"] for m in snap["bank_notices"]]
        assert "You received a Zelle payment" in bank_names
        assert "Mobile deposit received" in bank_names
        text = render_brief_plain(build_brief_sections(snap, now=seeded_db, service_rows=[]), seeded_db)
        assert "Business Gmail" in text
        assert "Outlook/Nelma" in text
        assert "Bank / transaction FYI" in text
        assert "You received a Zelle payment" in text
        mail_block = text.split("New leads and unanswered mail")[1].split("\n\n")[0]
        assert "Zelle" not in mail_block
        assert "Mobile deposit" not in mail_block
    finally:
        mailmod.TEST_INBOX = None


def test_gmail_brief_query_skips_chat_max_unread_filter():
    from app.services.max.gmail_reader import build_gmail_query

    q, filt = build_gmail_query(
        unread_only=False,
        query="in:inbox newer_than:21d",
        disable_default_to_filter=True,
    )
    assert q == "in:inbox newer_than:21d"
    assert filt is None
    assert "to:" not in (q or "")
    assert "is:unread" not in (q or "")

    chat_q, chat_filt = build_gmail_query()
    assert chat_filt
    assert "to:" in (chat_q or "")
    assert "is:unread" in (chat_q or "")


def test_fetch_gmail_passes_brief_filters(monkeypatch):
    captured = {}

    def fake_check_inbox(**kwargs):
        captured.update(kwargs)
        return {"success": True, "emails": []}

    monkeypatch.setattr("app.services.max.gmail_reader.check_inbox", fake_check_inbox)
    monkeypatch.setattr(
        "app.services.organizer.mail.mailbox_token_paths",
        lambda: {"edition": "main", "gmail": None, "outlook": None, "sources": []},
    )
    monkeypatch.setattr("app.services.organizer.mail.process_edition", lambda: "main")
    from app.services.organizer.mail import _fetch_gmail

    _fetch_gmail()
    assert captured.get("unread_only") is False
    assert captured.get("disable_default_to_filter") is True
    assert "to:max" not in str(captured.get("query") or "")


def test_decisions_dedupe_and_drop_backlog(seeded_db):
    from app.db.database import get_db

    now = seeded_db
    with get_db() as conn:
        conn.execute(
            """INSERT INTO tasks (id, title, description, status, priority, desk, created_by, created_at)
               VALUES ('jwt-1', 'JWT auth rewrite', '', 'todo', 'low', 'codeforge', 'max', ?)""",
            ((now - timedelta(days=40)).isoformat(),),
        )
        conn.execute(
            """INSERT INTO tasks (id, title, description, status, priority, desk, created_by, created_at)
               VALUES ('sql-1', 'SQLite encryption', '', 'todo', 'low', 'it', 'max', ?)""",
            ((now - timedelta(days=40)).isoformat(),),
        )
        conn.execute(
            """INSERT INTO tasks (id, title, description, status, priority, desk, created_by, created_at)
               VALUES ('voice-2', 'Founder voice request', 'dup', 'waiting', 'high', 'forge', 'max', ?)""",
            ((now - timedelta(days=20)).isoformat(),),
        )
        conn.execute(
            """INSERT INTO tasks (id, title, description, status, priority, desk, created_by, created_at)
               VALUES ('jwt-ok', 'Approve JWT rollout', '', 'waiting', 'high', 'it', 'max', ?)""",
            ((now - timedelta(days=2)).isoformat(),),
        )
    sections = build_brief_sections(snapshot(now), now=now, service_rows=[])
    text = sections["decisions"]["text"]
    assert "Founder voice request" in text
    assert text.count("Founder voice request") == 1
    assert "JWT auth rewrite" not in text
    assert "SQLite encryption" not in text
    assert "Approve JWT rollout" in text
    assert "2 stale tasks >30d" in text


def test_family_follows_exact_dell_symlinks_and_keeps_founder_inbox(
    isolated_empire_db, tmp_path, seeded_db,
):
    from app.services.max.desks.family_help_store import list_open_tickets, write_ticket_for_tests

    # Exact live layout: /data/family-help/amp → /data/amp/family-help/amp
    real_amp = tmp_path / "amp" / "family-help" / "amp"
    real_max = tmp_path / "maxine" / "family-help" / "maxine"
    real_amp.mkdir(parents=True)
    real_max.mkdir(parents=True)
    base = tmp_path / "family-help"
    base.mkdir()
    (base / "amp").symlink_to(real_amp)
    (base / "maxine").symlink_to(real_max)

    write_ticket_for_tests(
        edition="amp", ticket_id="fh-78b2ef984df6", sender="Amp",
        message="Need a ride to practice", created_at=seeded_db.isoformat(),
        base=base,
    )
    write_ticket_for_tests(
        edition="maxine", ticket_id="fh-297d9c540399", sender="Maxine",
        message="Help with homework", created_at=seeded_db.isoformat(),
        base=base,
    )
    write_ticket_for_tests(
        edition="amp", ticket_id="fh-d2f629e91a6d",
        sender="empirebox2026@gmail.com",
        message="School form", created_at=seeded_db.isoformat(),
        base=base, filename="fh-d2f629e91a6d.json",
    )
    write_ticket_for_tests(
        edition="amp", ticket_id="fh-test-emp", sender="empirebox2026@gmail.com",
        message="TEST family ticket", created_at=seeded_db.isoformat(),
        base=base,
    )
    items = list_open_tickets(base=base)
    ids = [i["id"] for i in items]
    assert "fh-78b2ef984df6" in ids
    assert "fh-297d9c540399" in ids
    assert "fh-d2f629e91a6d" in ids
    assert "fh-test-emp" not in ids
    assert not is_test_family_ticket({
        "id": "fh-d2f629e91a6d",
        "customer": "empirebox2026@gmail.com",
        "name": "School form",
        "message": "School form",
    })


def test_calendar_next_14_days_and_even_bullets(seeded_db):
    from app.db.database import get_db

    now = seeded_db
    with get_db() as conn:
        conn.execute(
            """INSERT INTO schedule_events
               (id, type, title, customer_vendor, start_time, status, created_by)
               VALUES ('ev-dahlia', 'install', 'Dahlia install', 'Dahlia', ?, 'confirmed', 'max')""",
            ((now + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),),
        )
        conn.execute(
            """INSERT INTO schedule_events
               (id, type, title, customer_vendor, start_time, status, created_by)
               VALUES ('ev-becky', 'delivery', 'Becky benches', 'Becky', ?, 'confirmed', 'max')""",
            ((now + timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S"),),
        )
    snap = snapshot(now)
    names = [i["name"] for i in snap["schedule_next14"]]
    assert "Dahlia install" in names
    assert "Becky benches" in names
    text = render_brief_plain(build_brief_sections(snap, now=now, service_rows=[]), now)
    assert "Next 14 days" in text
    assert "Dahlia install" in text
    assert "Becky benches" in text
    # First and later bullets share the same marker after HTML strip.
    quote_block = text.split("Quotes needing follow-up")[1].split("\n\n")[0]
    bullets = [ln for ln in quote_block.splitlines() if ln.startswith("• ")]
    assert bullets
    assert all(ln.startswith("• ") for ln in bullets)


def test_week_omits_today_and_uses_friendly_et_dates(seeded_db):
    from app.db.database import get_db

    now = seeded_db
    later = (now + timedelta(days=2)).replace(hour=9, minute=0, second=0)
    with get_db() as conn:
        conn.execute(
            """INSERT INTO schedule_events
               (id, type, title, customer_vendor, start_time, status, created_by)
               VALUES ('ev-week', 'measure', 'Tuesday measure', 'Carlos', ?, 'confirmed', 'max')""",
            (later.strftime("%Y-%m-%d %H:%M:%S"),),
        )
    snap = snapshot(now)
    today_names = [i["name"] for i in snap["schedule_today"]]
    assert "Nelma install" in today_names
    text = render_brief_plain(build_brief_sections(snap, now=now, service_rows=[]), now)
    today_block = text.split("This week")[0]
    week_block = text.split("This week")[1].split("Next 14 days")[0]
    assert "Nelma install" in today_block
    assert "Nelma install" not in week_block
    assert "Tuesday measure" in week_block
    assert "Mon Oct 12, 11 AM" in text
    assert "Wed Oct 14, 9 AM" in text
    assert "2026-10-12 11:00:00" not in text


def test_empty_other_areas_is_single_nothing_new_line():
    sections = build_brief_sections(
        {
            "schedule_today": [],
            "schedule_week": [],
            "schedule_next14": [],
            "schedule_overdue": [],
            "payments_since_yesterday": [],
            "unpaid_invoices": [],
            "stale_quotes": [],
            "pending_mail": [],
            "unreviewed_inbox": [],
            "stuck_tasks": [],
            "open_tasks": [],
            "approval_queue": [],
            "desk_results": [],
            "other_areas": {"empire": [], "family": [], "personal": [], "ventures": []},
        },
        now=datetime(2026, 10, 12, 8, 0, 0),
        service_rows=[],
    )
    assert sections["other_areas"]["text"] == "(nothing new)"
    assert "Empire:" not in sections["other_areas"]["text"]
    assert "(none)" not in sections["other_areas"]["text"]


def test_filter_helpers_unit():
    assert is_noise_client("TEST RESIDUE")
    assert is_noise_client("Woodcraft Test")
    assert is_noise_client("Empresa Prueba")
    assert is_noise_client("TrustTest")
    assert is_noise_client("MOCK-SWEEP-014")
    assert is_noise_client("Jane Smith")
    assert is_noise_client("Customer")
    assert not is_noise_client("Nelma Rivera")
    assert is_promotional_mail({"from": "Etsy <updates@etsy.com>", "subject": "Sale"})
    assert is_promotional_mail({"labels": ["CATEGORY_SOCIAL"], "from": "fb"})
    assert is_promotional_mail({
        "from": "Crate & Barrel <noreply@crateandbarrel.com>",
        "subject": "Webinar invite",
    })
    assert is_promotional_mail({
        "from": "Home Depot Pro Xtra <noreply@homedepot.com>",
        "subject": "Market invite",
    })
    assert not is_promotional_mail({"from": "Marley <marley@example.com>", "subject": "Install"})
    assert is_bank_notice({"from": "alerts@bofa.com", "subject": "Zelle payment"})
    assert is_bank_notice({"subject": "Your receipt from Square"})
    assert not is_bank_notice({"from": "Marley", "subject": "Install date?"})
    assert mail_account_label("gmail") == "Business Gmail"
    assert mail_account_label("outlook") == "Outlook/Nelma"
    assert keep_founder_decision({"name": "Founder voice request", "status": "waiting"})
    assert keep_founder_decision({"name": "Send quote", "source": "approval_queue", "needs_approval": True})
    assert not keep_founder_decision({"name": "JWT auth rewrite", "status": "todo", "kind": "stuck_task"})
    assert stale_task_count([
        {"id": "a", "name": "JWT auth rewrite", "age_days": 40},
        {"id": "b", "name": "Founder voice request", "age_days": 40},
        {"id": "a", "name": "JWT auth rewrite", "age_days": 40},
    ]) == 1
    assert format_et("2026-10-13 09:00:00") == "Tue Oct 13, 9 AM"
    assert format_et(datetime(2026, 10, 13, 9, 30, 0)) == "Tue Oct 13, 9:30 AM"
    money = filter_real_money([
        {"name": "A", "customer": "Nelma Rivera", "amount": 100, "age_days": 1},
        {"name": "B", "customer": "Test Client", "amount": 50, "age_days": 2},
        {"name": "C", "customer": "Nelma Rivera", "amount": 0, "age_days": 3},
        {"name": "D", "customer": "Jane Smith", "amount": 80, "age_days": 1},
        {"name": "E", "customer": "Woodcraft", "amount": 90, "age_days": 1, "is_test": 1},
    ])
    assert [m["name"] for m in money] == ["A"]
    quotes = filter_followup_quotes([
        {"name": "Q1", "customer": "Customer", "amount": 10, "status": "sent", "age_days": 4},
        {"name": "Q2", "customer": "Nelma Rivera", "amount": 10, "status": "draft", "age_days": 4},
        {"name": "Q3", "customer": "Nelma Rivera", "amount": 10, "status": "sent", "age_days": 4},
        {"name": "Q4", "customer": "Nelma Rivera", "amount": 10, "status": "sent", "age_days": 4, "is_test": True},
    ])
    assert [q["name"] for q in quotes] == ["Q3"]
    assert [m["name"] for m in dedupe_mail([
        {"name": "A", "thread_id": "t1", "id": "1"},
        {"name": "B", "thread_id": "t1", "id": "2"},
        {"name": "C", "id": "3"},
    ])] == ["A", "C"]
