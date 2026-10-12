"""Universal search: edition isolation, screens, records, timeouts, Max tools."""
from __future__ import annotations

import time

import pytest

from app.db.database import get_db
from app.services.search.edition import (
    can_read_workroom_jobs,
    contains_blocked_term,
    is_family_edition,
    process_edition,
)
from app.services.search.universal import (
    SearchHit,
    enqueue_draft_reply,
    run_universal_search,
    search_screens,
)
from app.services.max.ui_map import lookup_feature, feature_markdown_link


REQUIRED = {
    "improvements",
    "tokens",
    "family-help",
    "organizer",
    "minimax-usage",
    "presentation-mode",
}


def _schema(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY,
            client_name TEXT,
            title TEXT,
            description TEXT,
            job_number TEXT,
            business_unit TEXT,
            customer_id TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS quotes_v2 (
            id TEXT PRIMARY KEY,
            quote_number TEXT,
            customer_name TEXT,
            project_name TEXT,
            status TEXT,
            notes TEXT,
            customer_email TEXT,
            business_unit TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY,
            invoice_number TEXT,
            client_name TEXT,
            customer_id TEXT,
            business_unit TEXT,
            status TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            phone TEXT,
            company TEXT,
            business TEXT
        );
        CREATE TABLE IF NOT EXISTS contacts (
            id TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            phone TEXT,
            type TEXT
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            title TEXT
        );
        """
    )


def _seed():
    with get_db() as conn:
        _schema(conn)
        for table in ("jobs", "quotes_v2", "invoices", "tasks", "contacts", "customers"):
            try:
                conn.execute(f"DELETE FROM {table}")
            except Exception:
                pass
        conn.execute(
            "INSERT INTO customers (id, name, email, phone, company, business) "
            "VALUES ('c1','Marley','marley@example.com','3055550100','Marley LLC','workroom')"
        )
        conn.execute(
            "INSERT INTO customers (id, name, email, company, business) "
            "VALUES ('c2','Argos Campestre SA','legal@argos.test','Argos','workroom')"
        )
        try:
            conn.execute(
                "INSERT INTO jobs (id, title, customer_id, client_name, job_number, business_unit) "
                "VALUES ('j1', 'Drapery', 'c1', 'Marley', 'J-100', 'workroom')"
            )
        except Exception:
            conn.execute(
                "INSERT INTO jobs (id, title, customer_id) VALUES ('j1', 'Drapery', 'c1')"
            )
        conn.execute(
            "INSERT INTO quotes_v2 (id, quote_number, customer_name, project_name, status, business_unit) "
            "VALUES ('q1','EST-2026-014','Marley','Living room','draft','workroom')"
        )
        conn.execute(
            "INSERT INTO quotes_v2 (id, quote_number, customer_name, project_name, status, business_unit) "
            "VALUES ('q2','EST-2026-099','Family AMP','Coaching','draft','amp')"
        )
        try:
            conn.execute(
                "INSERT INTO invoices (id, invoice_number, customer_id, client_name, business_unit, status) "
                "VALUES ('i7', 'INV-9', 'c1', 'Marley', 'workroom', 'sent')"
            )
        except Exception:
            conn.execute(
                "INSERT INTO invoices (id, invoice_number, customer_id, status) "
                "VALUES ('i7', 'INV-9', 'c1', 'sent')"
            )
        try:
            conn.execute("INSERT INTO tasks (id, title) VALUES (3, 'Call Marley')")
        except Exception:
            pass


def test_fail_closed_unknown_edition_never_reads_main(monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "staging-xyz")
    assert process_edition() == "unknown"
    assert can_read_workroom_jobs() is False
    out = run_universal_search("Marley")
    assert out["blocked"] is True
    assert out["results"] == []
    assert out["top"] is None
    assert out["error"] == "unknown_edition"


def test_max_is_not_workroom_only(monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "main")
    assert process_edition() == "main"
    assert can_read_workroom_jobs() is True
    assert is_family_edition() is False
    _seed()
    out = run_universal_search("Marley")
    types = {r["type"] for r in out["results"]}
    assert "job" in types
    assert "quote" in types
    titles = " ".join(r["title"] for r in out["results"])
    assert "Marley" in titles


def test_family_never_sees_workroom_jobs_or_screens(monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "max_e")
    assert is_family_edition() is True
    assert can_read_workroom_jobs() is False
    _seed()
    out = run_universal_search("Marley")
    assert all(r["type"] != "job" for r in out["results"])
    assert all("workroom" not in (r.get("subtitle") or "").lower() for r in out["results"] if r["type"] in {"quote", "invoice"})
    screens = search_screens("workroom", family=True)
    assert all(not (h.extra or {}).get("workroom_only") for h in screens)
    assert lookup_feature("Empire Workroom", family=True) is None


def test_maxine_hides_argos(monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    assert contains_blocked_term("Argos Campestre NIT") is True
    _seed()
    out = run_universal_search("Argos")
    blob = " ".join(f"{r['title']} {r.get('subtitle') or ''}" for r in out["results"]).lower()
    assert "argos" not in blob
    assert "campestre" not in blob


def test_screens_include_required_nav_ids():
    hits = search_screens("imp", family=False, cap=20)
    ids = { (h.extra or {}).get("feature_id") for h in hits }
    assert "improvements" in ids
    empty = search_screens("", family=False, cap=20)
    empty_ids = { (h.extra or {}).get("feature_id") for h in empty }
    for req in REQUIRED:
        assert req in empty_ids or any(req in (h.title.lower() + h.id) for h in empty)


def test_presentation_tokens_organizer_family_help_minimax():
    for q, feat in (
        ("presentation", "presentation-mode"),
        ("tokens", "tokens"),
        ("organizer", "organizer"),
        ("family help", "family-help"),
        ("minimax", "minimax-usage"),
        ("improvements", "improvements"),
    ):
        hit = lookup_feature(q, family=False)
        assert hit is not None, q
        assert hit.id == feat or feat in hit.source_ids or feat in hit.id


def test_timeout_isolation_does_not_block():
    def slow(query, edition=None, family=None, cap=6):
        time.sleep(2.0)
        return [SearchHit(id="slow", type="job", title="SLOW", href="/")]

    def fast(query, edition=None, family=None, cap=6):
        return [SearchHit(id="fast", type="quote", title="Marley quote", href="/?screen=quote")]

    out = run_universal_search(
        "Marley",
        edition="main",
        sources=[("job", slow), ("quote", fast)],
        source_timeout=0.15,
        overall_timeout=0.4,
    )
    titles = [r["title"] for r in out["results"]]
    assert "Marley quote" in titles
    assert "SLOW" not in titles
    assert "job" in out["timed_out"]


def test_caps_and_top_includes_jobs():
    def many_jobs(query, edition=None, family=None, cap=6):
        return [SearchHit(id=f"job:{i}", type="job", title=f"Marley {i}", href=f"/?job={i}", score=0.95) for i in range(20)]

    out = run_universal_search(
        "Marley",
        edition="main",
        sources=[("job", many_jobs)],
        per_source_cap=6,
        total_cap=8,
    )
    assert len(out["results"]) <= 8
    assert out["top"]["type"] == "job"
    assert "Marley" in out["top"]["title"]
    assert out["top"]["href"]


def test_draft_reply_never_sends(monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "main")
    with get_db() as conn:
        _schema(conn)
    result = enqueue_draft_reply(
        mail_id="m1",
        source="gmail",
        body="Thanks Marley",
        subject="Re: quote",
        to_address="marley@example.com",
        to_name="Marley",
    )
    assert result.get("sent") is False
    assert result.get("ok") is not False or result.get("requires_confirm") is True
    assert result.get("error") != "sent"


def test_search_returns_deep_links_for_marley_quote(monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "main")
    _seed()
    payload = run_universal_search("Marley's quote")
    assert payload.get("results")
    assert any((r.get("href") or "").startswith("/?") for r in payload["results"])
    assert any(
        "EST-2026-014" in (r.get("title") or "") or r.get("type") == "quote"
        for r in payload["results"]
    )


def test_find_marley_quote_is_a_record_not_a_screen(monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "main")
    _seed()
    feat = lookup_feature("find Marley's quote")
    # UI map must not claim a screen for a customer quote.
    assert feat is None or feat.id not in {"quote", "docs"}
    payload = run_universal_search("find Marley's quote")
    assert any((r.get("href") or "").startswith("/?") for r in payload.get("results") or [])


def test_find_in_app_still_answers_where_is_presentation():
    feat = lookup_feature("where is presentation mode")
    assert feat is not None
    assert "presentation" in feat.href
    link = feature_markdown_link(feat, channel="web", family=False)
    assert link and "/?screen=presentation" in link


def test_unknown_edition_tool_fail_closed(monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "not-a-real-edition")
    payload = run_universal_search("Marley")
    assert payload.get("blocked") is True
    assert payload.get("results") == []


def test_search_tool_is_wired():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    search_src = (root / "app" / "services" / "max" / "tools_search.py").read_text()
    exec_src = (root / "app" / "services" / "max" / "tool_executor.py").read_text()
    ui_src = (root / "app" / "services" / "max" / "tools_ui_map.py").read_text()
    assert '@tool("search")' in search_src
    assert "find_in_app_or_search" in search_src
    assert "tools_search" in exec_src
    assert '"find": "search"' in exec_src
    assert "find_in_app_or_search" in ui_src
    acc = (root / "app" / "services" / "max" / "access_control.py").read_text()
    assert '"search": 1' in acc
    assert '"find_in_app": 1' in acc
