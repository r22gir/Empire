#!/usr/bin/env python3
"""Hit the real job-stage API and write checklist/gate proof artifacts."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
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
from app.services.job_stages.schema import init_job_stages_schema


def _seed() -> str:
    conn = sqlite3.connect(os.environ["EMPIRE_TASK_DB"])
    conn.row_factory = sqlite3.Row
    create_all_tables(conn)
    conn.close()
    init_schema()
    conn = sqlite3.connect(os.environ["EMPIRE_TASK_DB"])
    init_job_stages_schema(conn)
    conn.execute(
        "INSERT INTO customers (id, name, email, business) VALUES ('cust-midi', 'Le Midi', 'midi@example.test', 'workroom')"
    )
    conn.execute(
        """INSERT INTO jobs
           (id, title, customer_id, client_name, room, business_unit, job_number, pipeline_stage, metadata, current_revision)
           VALUES ('job-le-midi', 'Le Midi', 'cust-midi', 'Le Midi', 'LivingRoom', 'workroom', 'JOB-2026-0401', 'designing', '{}', 1)"""
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
    conn.commit()
    conn.close()
    return "job-le-midi"


def _app() -> FastAPI:
    app = FastAPI()
    app.include_router(job_stages.router, prefix="/api/v1")
    return app


def main() -> None:
    job_id = _seed()
    client = TestClient(_app())
    backfill = client.post(f"/api/v1/jobs/{job_id}/stages/backfill")
    stages = client.get(f"/api/v1/jobs/{job_id}/stages")
    where = client.get(f"/api/v1/jobs/{job_id}/where")
    gate = client.get(f"/api/v1/jobs/{job_id}/estimates/gate")
    blocked = client.post(f"/api/v1/jobs/{job_id}/estimates/client", json={"lines": []})
    share = client.post(f"/api/v1/jobs/{job_id}/estimates/share")
    proof = {
        "job_id": job_id,
        "backfill": backfill.json(),
        "stages": stages.json(),
        "where": where.json(),
        "gate": gate.json(),
        "estimate_blocked_status": blocked.status_code,
        "estimate_blocked": blocked.json(),
        "share_blocked_status": share.status_code,
        "share_blocked": share.json(),
    }
    (PROOF_DIR / "api_proof.json").write_text(json.dumps(proof, indent=2))
    checklist = stages.json()
    rows = []
    for stage in checklist.get("stages") or []:
        required = stage.get("required")
        status = stage.get("status")
        rows.append(
            f"<div class='stage {'current' if checklist.get('current_stage_key')==stage.get('stage_key') else ''}'>"
            f"<div class='top'><b>{stage.get('order')}. {stage.get('title')}</b>"
            f"<span class='badge {status}'>{status.replace('_',' ')}</span></div>"
            f"<div class='desc'>{stage.get('description')}</div>"
            f"{'' if required else '<div class=\"opt\">not required</div>'}"
            f"</div>"
        )
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Le Midi · Document set</title>
<style>
body {{ font-family: Georgia, serif; background:#f5f3ef; margin:0; }}
.panel {{ width:440px; margin:24px auto; background:#fff; border-left:1px solid #e5e2dc;
  box-shadow:-4px 0 20px rgba(0,0,0,.08); padding:20px; min-height:90vh; }}
h2 {{ margin:0 0 4px; font-size:18px; }}
.sub {{ color:#888; font-size:12px; margin-bottom:16px; }}
.banner {{ background:#fff7ed; border:1px solid #fed7aa; border-radius:8px; padding:10px; font-size:12px; margin-bottom:12px; }}
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
button {{ background:#7f1d1d; color:#fff; border:0; border-radius:6px; padding:6px 10px; font-weight:700; }}
</style></head>
<body>
<div class="panel">
  <h2>JOB-2026-0401 · Le Midi</h2>
  <div class="sub">LivingRoom · document set</div>
  <div class="banner"><b>{checklist.get('current_stage_title')} · {checklist.get('current_status')}</b><div>{checklist.get('next_step')}</div></div>
  {''.join(rows)}
  <p><button>Generate client estimate</button></p>
  <div class="gate" data-testid="estimate-gate-message">
    {proof['estimate_blocked'].get('detail') or proof['estimate_blocked']}
  </div>
</div>
</body></html>"""
    html_path = PROOF_DIR / "checklist.html"
    html_path.write_text(html)
    print(json.dumps({
        "proof_dir": str(PROOF_DIR),
        "estimate_blocked_status": blocked.status_code,
        "current_stage": checklist.get("current_stage_key"),
        "gate_open": checklist.get("gate_open"),
        "html": str(html_path),
    }, indent=2))


if __name__ == "__main__":
    main()
