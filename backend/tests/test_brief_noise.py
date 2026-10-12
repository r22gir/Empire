"""Brief noise filters: money, quotes, mail, decisions, family, calendar, NEW, bullets."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.services.max.brief_filters import (
    filter_followup_quotes,
    filter_real_money,
    is_noise_client,
    is_promotional_mail,
    keep_founder_decision,
    mail_account_label,
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


def test_mail_filters_promo_and_labels_account(seeded_db):
    import app.services.organizer.mail as mailmod

    mailmod.TEST_INBOX = [
        {
            "source": "gmail",
            "message_id": "human-1",
            "from": "Marley <marley@example.com>",
            "subject": "Install date?",
            "date": "2026-10-11T12:00:00",
            "preview": "Can we move the drapery install?",
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
        assert "Weekend sale" not in subjects
        assert "Your weekly lookbook" not in subjects
        labels = {m["name"]: m.get("account_label") for m in snap["pending_mail"]}
        assert labels["Install date?"] == "Business Gmail"
        assert labels["Fabric confirmation"] == "Outlook/Nelma"
        text = render_brief_plain(build_brief_sections(snap, now=seeded_db, service_rows=[]), seeded_db)
        assert "Business Gmail" in text
        assert "Outlook/Nelma" in text
    finally:
        mailmod.TEST_INBOX = None


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


def test_family_follows_symlinks_and_drops_test_tickets(isolated_empire_db, tmp_path, seeded_db):
    from app.services.max.desks.family_help_store import list_open_tickets, write_ticket_for_tests

    real_amp = tmp_path / "amp-data" / "family-help" / "amp"
    real_amp.mkdir(parents=True)
    real_max = tmp_path / "maxine-data" / "family-help" / "maxine"
    real_max.mkdir(parents=True)
    base = tmp_path / "family-help"
    base.mkdir()
    (base / "amp").symlink_to(tmp_path / "amp-data")
    (base / "maxine").symlink_to(tmp_path / "maxine-data")

    # Write through the symlink-resolved nested help.db path used on the Dell.
    write_ticket_for_tests(
        edition="amp", ticket_id="fh-78b2ef984df6", sender="Amp",
        message="Need a ride to practice", created_at=seeded_db.isoformat(),
        base=tmp_path / "amp-data" / "family-help",
    )
    write_ticket_for_tests(
        edition="maxine", ticket_id="fh-297d9c540399", sender="Maxine",
        message="Help with homework", created_at=seeded_db.isoformat(),
        base=tmp_path / "maxine-data" / "family-help",
    )
    write_ticket_for_tests(
        edition="amp", ticket_id="fh-d2f629e91a6d", sender="Amp",
        message="School form", created_at=seeded_db.isoformat(),
        base=tmp_path / "amp-data" / "family-help",
    )
    write_ticket_for_tests(
        edition="amp", ticket_id="fh-test-emp", sender="empirebox2026@gmail.com",
        message="TEST family ticket", created_at=seeded_db.isoformat(),
        base=tmp_path / "amp-data" / "family-help",
    )
    items = list_open_tickets(base=base)
    ids = [i["id"] for i in items]
    assert "fh-78b2ef984df6" in ids
    assert "fh-297d9c540399" in ids
    assert "fh-d2f629e91a6d" in ids
    assert "fh-test-emp" not in ids


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


def test_filter_helpers_unit():
    assert is_noise_client("TEST RESIDUE")
    assert is_noise_client("Woodcraft Test")
    assert is_noise_client("Empresa Prueba")
    assert not is_noise_client("Nelma Rivera")
    assert is_promotional_mail({"from": "Etsy <updates@etsy.com>", "subject": "Sale"})
    assert is_promotional_mail({"labels": ["CATEGORY_SOCIAL"], "from": "fb"})
    assert not is_promotional_mail({"from": "Marley <marley@example.com>", "subject": "Install"})
    assert mail_account_label("gmail") == "Business Gmail"
    assert mail_account_label("outlook") == "Outlook/Nelma"
    assert keep_founder_decision({"name": "Founder voice request", "status": "waiting"})
    assert not keep_founder_decision({"name": "JWT auth rewrite", "status": "todo", "kind": "stuck_task"})
    money = filter_real_money([
        {"name": "A", "customer": "Nelma Rivera", "amount": 100, "age_days": 1},
        {"name": "B", "customer": "Test Client", "amount": 50, "age_days": 2},
        {"name": "C", "customer": "Nelma Rivera", "amount": 0, "age_days": 3},
    ])
    assert [m["name"] for m in money] == ["A"]
    quotes = filter_followup_quotes([
        {"name": "Q1", "customer": "Customer", "amount": 10, "status": "sent", "age_days": 4},
        {"name": "Q2", "customer": "Nelma Rivera", "amount": 10, "status": "draft", "age_days": 4},
        {"name": "Q3", "customer": "Nelma Rivera", "amount": 10, "status": "sent", "age_days": 4},
    ])
    assert [q["name"] for q in quotes] == ["Q3"]
