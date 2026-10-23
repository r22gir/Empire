"""Comparison math, legacy-doc resolve, Max tool, no-send default, saved PDF."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.db.database import get_db
from app.services.install_line_tagging import format_feet
from app.services.install_price_compare import compare_install_prices
from app.services.max.tool_executor import TOOL_REGISTRY, execute_tool
from app.services.quote_service import create_quote


def _link_quote(quote_id: str, *, job_id: str, customer_id: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE quotes_v2 SET job_id = ?, customer_id = ? WHERE id = ?",
            (job_id, customer_id, quote_id),
        )


def _seed_jobs_and_quotes():
    """Mock Willard / Le Midi / legacy paper docs + a new estimate."""
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO customers (id, name, business) VALUES (?, ?, ?)",
            ("cust-willard", "Willard Mock", "workroom"),
        )
        conn.execute(
            "INSERT OR IGNORE INTO customers (id, name, business) VALUES (?, ?, ?)",
            ("cust-midi", "Le Midi Mock", "workroom"),
        )
        jcols = {r[1] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()}
        job_fields = ["id", "title", "customer_id"]
        job_vals_w = ["job-willard", "Willard Est 838", "cust-willard"]
        job_vals_m = ["job-midi", "Le Midi banquettes", "cust-midi"]
        job_vals_n = ["job-new", "New install quote job", "cust-willard"]
        if "client_name" in jcols:
            job_fields.append("client_name")
            job_vals_w.append("Willard Mock")
            job_vals_m.append("Le Midi Mock")
            job_vals_n.append("Willard Mock")
        if "job_number" in jcols:
            job_fields.append("job_number")
            job_vals_w.append("JOB-W")
            job_vals_m.append("JOB-M")
            job_vals_n.append("JOB-N")
        ph = ", ".join("?" * len(job_fields))
        conn.execute(f"INSERT OR IGNORE INTO jobs ({', '.join(job_fields)}) VALUES ({ph})", job_vals_w)
        conn.execute(f"INSERT OR IGNORE INTO jobs ({', '.join(job_fields)}) VALUES ({ph})", job_vals_m)
        conn.execute(f"INSERT OR IGNORE INTO jobs ({', '.join(job_fields)}) VALUES ({ph})", job_vals_n)

    willard = create_quote({
        "customer_name": "Willard Mock",
        "project_name": "Willard Est 838",
        "issued_document": "838",
        "line_items": [{
            "category": "manual_line",
            "description": 'Install 10 windows — 160" wall',
            "unit_price": 1450,
            "quantity": 1,
        }],
    })
    midi = create_quote({
        "customer_name": "Le Midi Mock",
        "project_name": "Le Midi",
        "line_items": [{
            "category": "manual_line",
            "description": "Removal and installation — 8 windows — 20 lf",
            "unit_price": 2000,
            "quantity": 1,
        }],
    })
    _link_quote(willard["id"], job_id="job-willard", customer_id="cust-willard")
    _link_quote(midi["id"], job_id="job-midi", customer_id="cust-midi")
    # Imported historical paper docs (legacy numbers).
    legacy_specs = [
        ("812-C", "job-willard", "cust-willard", 'Hourly install 5 windows — 120" wall', 800),
        ("897", "job-midi", "cust-midi", "Install 6 windows — 12 lf", 900),
        ("909", "job-willard", "cust-willard", "Install drapery — no counts given", 500),
        ("803-A", "job-midi", "cust-midi", "Remove existing track and install — 4 windows — 96\"", 640),
    ]
    legacy = {}
    for number, job_id, cid, desc, price in legacy_specs:
        q = create_quote({
            "customer_name": f"Legacy {number}",
            "project_name": f"Imported estimate {number}",
            "issued_document": number,
            "line_items": [{
                "category": "manual_line",
                "description": desc,
                "unit_price": price,
                "quantity": 1,
            }],
        })
        with get_db() as conn:
            conn.execute(
                "UPDATE quotes_v2 SET quote_number = ?, job_id = ?, customer_id = ? WHERE id = ?",
                (number, job_id, cid, q["id"]),
            )
        legacy[number] = q

    new_q = create_quote({
        "customer_name": "Willard Mock",
        "project_name": "New install compare",
        "line_items": [{
            "category": "manual_line",
            "description": "Install 9 windows — 16 lf",
            "unit_price": 1800,
            "quantity": 1,
        }],
    })
    _link_quote(new_q["id"], job_id="job-new", customer_id="cust-willard")
    return {
        "willard": willard,
        "midi": midi,
        "legacy": legacy,
        "new": new_q,
    }


def test_comparison_math_avg_min_max_and_flags(isolated_empire_db):
    seeded = _seed_jobs_and_quotes()
    result = compare_install_prices(
        quote_numbers=["Willard", "Le Midi"],
        new_quote=seeded["new"]["quote_number"],
        generate_pdf=False,
        save_to_job=False,
    )
    hist = result["historical"]
    assert len(hist) >= 2
    willard = next(ln for ln in hist if ln.get("job_id") == "job-willard" and "160" in ln["description"])
    midi = next(ln for ln in hist if ln.get("job_id") == "job-midi" and "20 lf" in ln["description"])
    assert willard["per_window"] == 145.0  # 1450 / 10
    assert willard["per_lf"] == pytest.approx(round(1450 / (160 / 12), 2))
    assert midi["per_window"] == 250.0  # 2000 / 8
    assert midi["per_lf"] == 100.0  # 2000 / 20
    assert format_feet(willard["lf"]) == "13 1/3 ft"

    pw = result["aggregates"]["historical"]["per_window"]
    assert pw["count"] >= 2
    assert pw["min"] <= pw["avg"] <= pw["max"]

    new_ln = result["new_quote"][0]
    assert new_ln["per_window"] == 200.0  # 1800 / 9
    assert new_ln["per_lf"] == 112.5  # 1800 / 16


def test_legacy_imported_docs_are_included(isolated_empire_db):
    _seed_jobs_and_quotes()
    result = compare_install_prices(
        quote_numbers=["812-C", "838", "897", "909", "803-A"],
        new_quote="EST-9999-001",
        generate_pdf=False,
        save_to_job=False,
    )
    numbers = {ln.get("quote_number") or ln.get("issued_document") for ln in result["historical"]}
    for n in ("812-C", "838", "897", "909", "803-A"):
        assert n in numbers
    flagged = [ln for ln in result["historical"] if ln["quote_number"] == "909"]
    assert flagged and flagged[0]["missing_counts"] is True
    assert flagged[0]["flag"]


def test_tool_registered_and_no_send_default(isolated_empire_db, monkeypatch):
    assert "compare_install_prices" in TOOL_REGISTRY
    from app.services.max import tools_install_compare as tic
    assert "compare_install_prices" in tic.INSTALL_COMPARE_TOOLS_DOC
    assert "Willard" in tic.INSTALL_COMPARE_TOOLS_DOC
    assert "present" in tic.INSTALL_COMPARE_TOOLS_DOC.lower()

    seeded = _seed_jobs_and_quotes()
    sent = {"called": False}

    def _boom(*_a, **_k):
        sent["called"] = True
        raise AssertionError("deliverer must not run when send is off")

    import app.services.install_price_compare as ipc
    monkeypatch.setattr(ipc, "_DELIVER", _boom)

    res = execute_tool({
        "tool": "compare_install_prices",
        "quote_numbers": ["job-willard", "job-midi"],
        "job_ids": ["job-willard", "job-midi"],
        "new_quote": seeded["new"]["quote_number"],
    })
    assert res.success, res.error
    body = res.result
    assert body["sent"] is False
    assert body["telegram_sent"] is False
    assert body["email_sent"] is False
    assert body["whatsapp_sent"] is False
    assert body["used_present_tool"] is False
    assert body["send_default"] == "off"
    assert sent["called"] is False
    assert body.get("pdf_path")
    assert Path(body["pdf_path"]).is_file()
    assert Path(body["pdf_path"]).stat().st_size > 200
    assert body.get("document")
    assert body["document"]["job_id"] == "job-new"
    assert body["document"]["sent"] is False
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM job_documents WHERE job_id = ? AND document_type = ?",
            ("job-new", "install_compare"),
        ).fetchone()
        assert row is not None
        assert dict(row)["filename"].endswith(".pdf")


def test_tool_never_routes_through_present(isolated_empire_db, monkeypatch):
    seeded = _seed_jobs_and_quotes()
    calls = []

    def _fake_present(*_a, **_k):
        calls.append("present")
        raise AssertionError("present tool must not run")

    import app.services.max.tool_executor as te
    monkeypatch.setitem(te.TOOL_REGISTRY, "present", _fake_present)

    res = execute_tool({
        "tool": "compare_install_prices",
        "quote_numbers": [seeded["willard"]["quote_number"]],
        "new_quote": seeded["new"]["quote_number"],
        "send": False,
    })
    assert res.success, res.error
    assert calls == []
    assert res.result["used_present_tool"] is False


def test_explicit_send_does_not_use_present(isolated_empire_db, monkeypatch):
    seeded = _seed_jobs_and_quotes()
    import app.services.install_price_compare as ipc

    def _deliver(payload, params):
        assert params.get("channel") == "telegram"
        return {
            "sent": True,
            "telegram_sent": True,
            "used_present_tool": False,
            "send_reason": "mock_explicit",
        }

    monkeypatch.setattr(ipc, "_DELIVER", _deliver)
    res = execute_tool({
        "tool": "compare_install_prices",
        "quote_numbers": [seeded["willard"]["quote_number"]],
        "new_quote": seeded["new"]["quote_number"],
        "send": True,
        "channel": "telegram",
        "generate_pdf": False,
        "save_to_job": False,
    })
    assert res.success, res.error
    assert res.result["telegram_sent"] is True
    assert res.result["used_present_tool"] is False
