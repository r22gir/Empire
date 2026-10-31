#!/usr/bin/env python3
"""Hit the real job-stage API and write checklist/gate proof artifacts."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

PROOF_DIR = ROOT / "reports" / "2026-10-31_job_stage_gate"
PROOF_DIR.mkdir(parents=True, exist_ok=True)

os.environ["EMPIRE_TASK_DB"] = str(PROOF_DIR / "proof.db")
os.environ.setdefault("EMPIRE_DB_PATH", os.environ["EMPIRE_TASK_DB"])

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.unified_business_migration import create_all_tables
from app.routers import job_stages
from app.routers.jobs_unified import init_schema
from app.services.job_stages.gate import register_job_stage_exception_handlers
from app.services.job_stages.schema import init_job_stages_schema


def _seed() -> dict[str, str]:
    db_path = os.environ["EMPIRE_TASK_DB"]
    if Path(db_path).exists():
        Path(db_path).unlink()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    create_all_tables(conn)
    conn.close()
    init_schema()
    conn = sqlite3.connect(db_path)
    init_job_stages_schema(conn)
    conn.execute(
        "INSERT INTO customers (id, name, email, business) VALUES ('cust-midi', 'Le Midi', 'midi@example.test', 'workroom')"
    )
    conn.execute(
        """INSERT INTO jobs
           (id, title, customer_id, client_name, room, business_unit, job_number, pipeline_stage, metadata, current_revision, gate_enforced)
           VALUES ('job-le-midi', 'Le Midi', 'cust-midi', 'Le Midi', 'LivingRoom', 'workroom', 'JOB-2026-0401', 'designing', '{}', 1, 0)"""
    )
    for doc_type, name in (
        ("photo", "le-midi-site.jpg"),
        ("drawing", "le-midi-elevation.pdf"),
        ("presentation", "le-midi-board.pdf"),
        ("workroom_approval", "le-midi-approval.pdf"),
    ):
        conn.execute(
            """INSERT INTO job_documents (job_id, document_type, url, filename)
               VALUES ('job-le-midi', ?, ?, ?)""",
            (doc_type, f"/mock/{name}", name),
        )
    conn.execute(
        "INSERT INTO customers (id, name, email, business) VALUES ('cust-new', 'Ada', 'ada@example.test', 'workroom')"
    )
    conn.execute(
        """INSERT INTO jobs
           (id, title, customer_id, client_name, room, business_unit, job_number, pipeline_stage, metadata, current_revision, gate_enforced)
           VALUES ('job-new-gate', 'New Drapery', 'cust-new', 'Ada', 'Dining', 'workroom', 'JOB-2026-0888', 'designing', '{}', 1, 1)"""
    )
    conn.execute(
        """INSERT INTO quotes_v2 (id, quote_number, job_id, customer_name, status, total)
           VALUES ('q-midi', 'EST-MIDI', 'job-le-midi', 'Le Midi', 'draft', 100)"""
    )
    conn.execute(
        """INSERT INTO quotes_v2 (id, quote_number, job_id, customer_name, status, total)
           VALUES ('q-new', 'EST-NEW', 'job-new-gate', 'Ada', 'draft', 100)"""
    )
    conn.execute(
        """INSERT INTO quotes_v2 (id, quote_number, job_id, customer_name, status, total)
           VALUES ('q-orphan', 'EST-ORPHAN', 'job-deleted', 'Orphan', 'draft', 50)"""
    )
    conn.commit()
    conn.close()
    return {
        "le_midi": "job-le-midi",
        "new_job": "job-new-gate",
        "midi_quote": "q-midi",
        "new_quote": "q-new",
        "orphan_quote": "q-orphan",
    }


def _app() -> FastAPI:
    app = FastAPI()
    register_job_stage_exception_handlers(app)
    app.include_router(job_stages.router, prefix="/api/v1")
    return app


def _quote_app() -> FastAPI:
    from app.services.job_stages.gate import assert_client_estimate_allowed_for_quote

    app = FastAPI()
    register_job_stage_exception_handlers(app)

    @app.get("/quotes/{quote_id}/pdf")
    def pdf(quote_id: str):
        state = assert_client_estimate_allowed_for_quote(quote_id)
        return {"allowed": True, "gate": state}

    return app


def _render_panel(checklist: dict, banner: str, gate_html: str, title: str) -> str:
    rows = []
    for stage in checklist.get("stages") or []:
        required = stage.get("required")
        status = stage.get("status")
        rows.append(
            f"<div class='stage {'current' if checklist.get('current_stage_key')==stage.get('stage_key') else ''}'>"
            f"<div class='top'><b>{stage.get('order')}. {stage.get('title')}</b>"
            f"<span class='badge {status}'>{str(status).replace('_',' ')}</span></div>"
            f"<div class='desc'>{stage.get('description')}</div>"
            f"{'' if required else '<div class=\"opt\">not required</div>'}"
            f"</div>"
        )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
body {{ font-family: Georgia, serif; background:#f5f3ef; margin:0; }}
.panel {{ width:440px; margin:24px auto; background:#fff; border-left:1px solid #e5e2dc;
  box-shadow:-4px 0 20px rgba(0,0,0,.08); padding:20px; min-height:90vh; }}
h2 {{ margin:0 0 4px; font-size:18px; }}
.sub {{ color:#888; font-size:12px; margin-bottom:16px; }}
.banner {{ background:#fff7ed; border:1px solid #fed7aa; border-radius:8px; padding:10px; font-size:12px; margin-bottom:12px; }}
.legacy {{ background:#ecfdf5; border:1px solid #a7f3d0; color:#047857; }}
.stage {{ border:1px solid #ece8e0; border-radius:8px; padding:8px; margin-bottom:6px; font-size:12px; }}
.stage.current {{ border-color:#b8960c; background:#fdf8eb; }}
.top {{ display:flex; justify-content:space-between; font-weight:700; }}
.desc {{ color:#666; margin-top:3px; }}
.badge {{ border-radius:99px; padding:1px 8px; font-size:10px; }}
.badge.done {{ background:#eff6ff; color:#1d4ed8; }}
.badge.drafted {{ background:#fffbeb; color:#b45309; }}
.badge.not_started {{ background:#f3f4f6; color:#6b7280; }}
.badge.approved {{ background:#ecfdf5; color:#047857; }}
.gate {{ margin-top:12px; background:#fef2f2; color:#991b1b; border-radius:8px; padding:8px; font-size:12px; }}
.ok {{ margin-top:12px; background:#ecfdf5; color:#065f46; border-radius:8px; padding:8px; font-size:12px; }}
button {{ background:#7f1d1d; color:#fff; border:0; border-radius:6px; padding:6px 10px; font-weight:700; }}
</style></head>
<body>
<div class="panel">
  <h2>{title}</h2>
  <div class="sub">document set · real API path</div>
  <div class="banner {'' if checklist.get('gate_enforced') else 'legacy'}"><b>{banner}</b>
    <div>{checklist.get('next_step')}</div>
    {'' if checklist.get('gate_enforced') else '<div>Legacy job — stage 4 gate is not enforced. Client estimates stay available.</div>'}
  </div>
  {''.join(rows)}
  <p><button>Generate client estimate</button></p>
  {gate_html}
</div>
</body></html>"""


def main() -> None:
    ids = _seed()
    client = TestClient(_app())
    quotes = TestClient(_quote_app())

    backfill = client.post(f"/api/v1/jobs/{ids['le_midi']}/stages/backfill")
    stages = client.get(f"/api/v1/jobs/{ids['le_midi']}/stages")
    where = client.get(f"/api/v1/jobs/{ids['le_midi']}/where")
    midi_gate = client.get(f"/api/v1/jobs/{ids['le_midi']}/estimates/gate")
    midi_estimate = client.post(f"/api/v1/jobs/{ids['le_midi']}/estimates/client", json={"lines": []})
    midi_share = client.post(f"/api/v1/jobs/{ids['le_midi']}/estimates/share")
    midi_quote = quotes.get(f"/quotes/{ids['midi_quote']}/pdf")

    client.post(f"/api/v1/jobs/{ids['new_job']}/stages/ensure")
    new_stages = client.get(f"/api/v1/jobs/{ids['new_job']}/stages")
    new_gate = client.get(f"/api/v1/jobs/{ids['new_job']}/estimates/gate")
    new_estimate = client.post(f"/api/v1/jobs/{ids['new_job']}/estimates/client", json={"lines": []})
    new_quote = quotes.get(f"/quotes/{ids['new_quote']}/pdf")
    orphan_quote = quotes.get(f"/quotes/{ids['orphan_quote']}/pdf")

    max_approve = client.post(
        f"/api/v1/jobs/{ids['new_job']}/stages/workroom_approval/approve",
        json={"approved_by": "max"},
    )
    max_patch = client.patch(
        f"/api/v1/jobs/{ids['new_job']}/stages/workroom_approval",
        json={"status": "approved", "actor": "max"},
    )

    proof = {
        "le_midi": {
            "job_id": ids["le_midi"],
            "backfill": backfill.json(),
            "stages": stages.json(),
            "where": where.json(),
            "gate_status": midi_gate.status_code,
            "gate": midi_gate.json(),
            "estimate_status": midi_estimate.status_code,
            "share_status": midi_share.status_code,
            "quote_pdf_status": midi_quote.status_code,
            "quote_pdf": midi_quote.json(),
        },
        "new_job": {
            "job_id": ids["new_job"],
            "stages": new_stages.json(),
            "gate_status": new_gate.status_code,
            "gate": new_gate.json(),
            "estimate_status": new_estimate.status_code,
            "estimate": new_estimate.json(),
            "quote_pdf_status": new_quote.status_code,
            "quote_pdf": new_quote.json(),
        },
        "deleted_job_quote": {
            "quote_id": ids["orphan_quote"],
            "status": orphan_quote.status_code,
            "body": orphan_quote.json(),
        },
        "approval_acl": {
            "max_approve_status": max_approve.status_code,
            "max_approve": max_approve.json(),
            "max_patch_status": max_patch.status_code,
            "max_patch": max_patch.json(),
        },
    }
    (PROOF_DIR / "api_proof.json").write_text(json.dumps(proof, indent=2))

    midi_ok = (
        f"<div class='ok' data-testid='estimate-gate-message'>"
        f"Legacy Le Midi allowed ({midi_estimate.status_code}). "
        f"Job-linked quote PDF {midi_quote.status_code}."
        f"</div>"
    )
    html_path = PROOF_DIR / "checklist.html"
    html_path.write_text(_render_panel(
        stages.json(),
        f"{stages.json().get('current_stage_title')} · {stages.json().get('current_status')}",
        midi_ok,
        "JOB-2026-0401 · Le Midi",
    ))

    blocked_detail = new_estimate.json().get("detail") or new_estimate.json()
    blocked_html = (
        f"<div class='gate' data-testid='estimate-gate-message'>{blocked_detail}</div>"
    )
    blocked_path = PROOF_DIR / "gate_blocked.html"
    blocked_path.write_text(_render_panel(
        new_stages.json(),
        f"{new_stages.json().get('current_stage_title')} · {new_stages.json().get('current_status')}",
        blocked_html,
        "JOB-2026-0888 · New Drapery (post-cutover)",
    ))

    print(json.dumps({
        "proof_dir": str(PROOF_DIR),
        "le_midi_estimate_status": midi_estimate.status_code,
        "le_midi_quote_pdf_status": midi_quote.status_code,
        "le_midi_gate_open": stages.json().get("gate_open"),
        "new_job_estimate_status": new_estimate.status_code,
        "new_job_quote_pdf_status": new_quote.status_code,
        "orphan_quote_status": orphan_quote.status_code,
        "max_approve_status": max_approve.status_code,
        "html": str(html_path),
        "blocked_html": str(blocked_path),
    }, indent=2))


if __name__ == "__main__":
    main()
