"""Desk jobs must read real fixture data, name findings, and mark done only on review pass."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from app.db.max_ops_schema import ensure_max_ops_schema
from app.services.max.desks.job_runner import run_scheduled_job
from app.services.max.desks.review_gate import review_desk_output as gate


def _seed(conn, now: datetime):
    ensure_max_ops_schema(conn)
    conn.execute(
        "INSERT INTO customers (id, name, email) VALUES ('cust-nelma', 'Nelma Rivera', 'nelma@example.com')"
    )
    conn.execute(
        """INSERT INTO invoices
           (id, invoice_number, customer_id, status, total, amount_paid, balance_due, due_date, created_at)
           VALUES ('inv-1', 'INV-2044', 'cust-nelma', 'overdue', 2400, 0, 2400, ?, ?)""",
        ((now - timedelta(days=12)).strftime("%Y-%m-%d"), (now - timedelta(days=20)).isoformat()),
    )
    conn.execute(
        """INSERT INTO invoices
           (id, invoice_number, customer_id, status, total, amount_paid, balance_due, due_date, created_at)
           VALUES ('inv-2', 'INV-2045', 'cust-nelma', 'sent', 800, 0, 800, ?, ?)""",
        ((now + timedelta(days=10)).strftime("%Y-%m-%d"), now.isoformat()),
    )
    conn.execute(
        """INSERT INTO payments (id, invoice_id, customer_id, amount, method, notes, payment_date)
           VALUES ('pay-1', 'inv-1', 'cust-nelma', 500, 'card', 'stripe_pi_abc', ?)""",
        ((now - timedelta(hours=6)).strftime("%Y-%m-%d"),),
    )
    conn.execute(
        """INSERT INTO quotes_v2
           (id, quote_number, customer_name, status, total, sent_at, created_at, updated_at)
           VALUES ('q-1', 'EST-2026-088', 'Nelma Rivera', 'sent', 3100, ?, ?, ?)""",
        (
            (now - timedelta(days=8)).isoformat(),
            (now - timedelta(days=8)).isoformat(),
            now.isoformat(),
        ),
    )
    conn.execute(
        """INSERT INTO jobs (id, title, customer_id, status, scheduled_date, created_at)
           VALUES ('job-1', 'Living room drapes', 'cust-nelma', 'in_progress', ?, ?)""",
        (now.strftime("%Y-%m-%d"), now.isoformat()),
    )
    conn.execute(
        """INSERT INTO schedule_events
           (id, type, title, customer_vendor, start_time, status, created_by)
           VALUES ('ev-1', 'install', 'Nelma install', 'Nelma Rivera', ?, 'confirmed', 'max')""",
        ((now + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S"),),
    )
    conn.execute(
        """INSERT INTO pending_mail (id, from_name, from_addr, subject, channel, status, created_at)
           VALUES ('mail-1', 'Carlos Vega', 'carlos@example.com', 'Fabric question', 'email', 'pending', ?)""",
        ((now - timedelta(days=1)).isoformat(),),
    )
    conn.execute(
        """INSERT INTO family_help_tickets (id, requester, subject, status, created_at)
           VALUES ('fam-1', 'Amp', 'School pickup tomorrow', 'open', ?)""",
        (now.isoformat(),),
    )
    conn.execute(
        """INSERT INTO tasks (id, title, description, status, priority, desk, created_by, created_at)
           VALUES ('stuck-1', 'Founder voice request', 'Approve voice clip', 'waiting', 'high', 'forge', 'max', ?)""",
        ((now - timedelta(days=20)).isoformat(),),
    )
    conn.commit()


@pytest.fixture
def seeded_db(isolated_empire_db):
    now = datetime(2026, 10, 12, 9, 0, 0)
    from app.db.database import get_db

    with get_db() as conn:
        _seed(conn, now)
    return now


def test_invoice_audit_names_real_invoices(seeded_db):
    out = run_scheduled_job("finance", "Morning Invoice Audit", now=seeded_db)
    assert out["status"] == "done"
    assert "INV-2044" in out["result"]
    assert "Nelma Rivera" in out["result"]
    assert "INV-2045" in out["result"]
    assert "Recommended: Send payment reminders" not in out["result"]


def test_stale_quote_is_named_and_not_sent(seeded_db):
    out = run_scheduled_job("sales", "Stale Quote Follow-Up Scan", now=seeded_db)
    assert out["status"] == "done"
    assert "EST-2026-088" in out["result"]
    assert "Nelma Rivera" in out["result"]
    assert "not sent" in out["result"].lower()
    assert "Follow-up prepared for customer" not in out["result"]


def test_pipeline_uses_quotes_jobs_schedule(seeded_db):
    out = run_scheduled_job("forge", "Today's Pipeline Summary", now=seeded_db)
    assert out["status"] == "done"
    assert "EST-2026-088" in out["result"]
    assert "Living room drapes" in out["result"]
    assert "Nelma install" in out["result"]
    assert "Quote workflow initiated" not in out["result"]


def test_support_lists_mail_and_isolates_family(seeded_db):
    out = run_scheduled_job("support", "Open Ticket Summary", now=seeded_db)
    assert out["status"] == "done"
    assert "Fabric question" in out["result"]
    assert "Carlos Vega" in out["result"]
    assert "School pickup tomorrow" in out["result"]
    assert "isolated" in out["result"].lower()
    assert "Your order has been shipped" not in out["result"]


def test_metrics_include_named_unpaid(seeded_db):
    out = run_scheduled_job("analytics", "Daily Business Metrics", now=seeded_db)
    assert out["status"] == "done"
    assert "INV-2044" in out["result"]
    assert "Nelma Rivera" in out["result"]


def test_it_health_uses_live_service_list_not_dead_ports(seeded_db):
    def port_ok(port):
        return port in (8000, 3005)

    out = run_scheduled_job(
        "it",
        "Morning Service Health Check",
        now=seeded_db,
        checkers={
            "port_checker": port_ok,
            "container_checker": lambda n: False,
            "process_checker": lambda n: True,
            "disk_checker": lambda p="/": {
                "id": "disk", "name": "disk", "kind": "disk", "up": True,
                "pct": 40, "detail": "40% used",
            },
        },
    )
    assert out["status"] == "done"
    assert "empire-backend" in out["result"]
    assert "empire-portal" in out["result"]
    assert "WorkroomForge" not in out["result"]
    assert "3001" not in out["result"]
    assert "Ollama" not in out["result"]
    names = [f["name"] for f in out["findings"]]
    assert "empire-backend" in names
    assert "disk" in names
    assert "tunnel" in names


def test_done_only_when_review_passes(seeded_db):
    from app.services.max.desks import job_runner as jr

    def canned(_snap):
        return (
            "Overdue check: 2 invoice(s) outstanding. "
            "Recommended: Send payment reminders, escalate 30+ day overdue.",
            [{"name": "INV-2044", "customer": "Nelma Rivera"}],
        )

    original = jr.JOB_REGISTRY["Morning Invoice Audit"]
    jr.JOB_REGISTRY["Morning Invoice Audit"] = canned
    try:
        out = run_scheduled_job("finance", "Morning Invoice Audit", now=seeded_db)
    finally:
        jr.JOB_REGISTRY["Morning Invoice Audit"] = original
    assert out["status"] == "failed"
    assert out["retry_count"] == 1
    assert out["fail_reason"]
    from app.db.database import get_db
    with get_db() as conn:
        row = conn.execute(
            "SELECT status, fail_reason FROM desk_job_results WHERE job_title = ?",
            ("Morning Invoice Audit",),
        ).fetchone()
        assert row[0] == "failed"
        task = conn.execute(
            "SELECT status, result_summary FROM tasks WHERE title = ?",
            ("Morning Invoice Audit",),
        ).fetchone()
        assert task[0] == "cancelled"
        assert "FAILED" in (task[1] or "")


def test_review_gate_rejects_raw_tool_text():
    verdict = gate("Here is the answer\n```tool\n{\"tool\": \"get_invoices\"}\n```")
    assert verdict.passed is False
    assert "tool" in verdict.reason


def test_tool_blocks_are_executed(monkeypatch):
    from app.services.max.desks.base_desk import BaseDesk

    class Dummy(BaseDesk):
        desk_id = "support"
        desk_name = "Support"
        async def _handle_task(self, task):
            return task

    executed = {}

    class R:
        success = True
        result = {"invoices": ["INV-2044"]}
        error = None

    def fake_execute(action, desk=None, **kwargs):
        executed["tool"] = action.get("tool")
        executed["desk"] = desk
        return R()

    monkeypatch.setattr("app.services.max.tool_executor.execute_tool", fake_execute)
    desk = Dummy()
    raw = 'Checking.\n```tool\n{"tool": "get_invoices"}\n```'
    out = desk._execute_tool_blocks(raw)
    assert "```tool" not in out
    assert executed["tool"] == "get_invoices"
    assert "INV-2044" in out


def test_stuck_tasks_surface_as_approvals(seeded_db):
    from app.services.max.desks.job_runner import escalate_stuck_tasks
    from app.db.database import get_db

    stuck = escalate_stuck_tasks(now=seeded_db, older_than_days=7)
    assert any(s.get("name") == "Founder voice request" for s in stuck)
    with get_db() as conn:
        row = conn.execute("SELECT status FROM tasks WHERE id = 'stuck-1'").fetchone()
        assert row[0] == "waiting"
    from app.routers import notifications
    titles = [n["title"] for n in notifications.notifications_db]
    assert any("stuck" in t.lower() for t in titles)


def test_orchestrator_records_idle_desk_runs(seeded_db):
    from app.services.max.orchestrator_runs import list_runs, route_idle_desks

    payload = route_idle_desks(now=seeded_db)
    assert payload["run_id"]
    assert "clients" in payload["desks_assigned"]
    assert "lab" in payload["desks_assigned"]
    runs = list_runs()
    assert runs
    assert runs[0]["id"] == payload["run_id"]
    assert runs[0]["tasks_created"] >= 1
