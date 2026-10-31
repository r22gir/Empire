"""Job document-set stages, naming, gates, backfill. Mock data only."""
from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.database import get_db
from app.routers import job_stages
from app.services.job_stages.backfill import backfill_job_stages
from app.services.job_stages.catalog import STAGE_WORKROOM, STAGES
from app.services.job_stages.estimates import group_willard_lines
from app.services.job_stages.gate import (
    ClientEstimateGateError,
    SquareSendGateError,
    StageApprovalDenied,
    assert_client_estimate_allowed,
    assert_client_estimate_allowed_for_quote,
    assert_square_send_allowed,
    job_is_gate_enforced,
    register_job_stage_exception_handlers,
    resolve_job_id_for_quote,
)
from app.services.job_stages.max_answer import answer_where_is_this_job, wants_job_location
from app.services.job_stages.naming import build_standard_name, next_revision, parse_standard_name
from app.services.job_stages.schema import get_gate_cutover_at, init_job_stages_schema
from app.services.job_stages.service import (
    approve_stage,
    ensure_job_stages,
    get_stage,
    list_stages,
    register_document,
    set_stage_status,
)
from app.services.job_stages.square_invoice import create_square_invoice_draft, send_square_invoice
from app.services.job_stages.workroom_approval import render_workroom_approval_pdf
from pathlib import Path


def _seed_job(
    *,
    job_id: str = "job-le-midi",
    title: str = "Le Midi",
    client_name: str = "Le Midi",
    room: str = "LivingRoom",
    metadata: dict | None = None,
    current_revision: int = 1,
    notes: str = "",
    gate_enforced: int | None = None,
) -> str:
    with get_db() as conn:
        init_job_stages_schema(conn)
        conn.execute(
            "INSERT INTO customers (id, name, email, business) VALUES (?, ?, ?, 'workroom')",
            (f"cust-{job_id}", client_name, f"{job_id}@example.test"),
        )
        conn.execute(
            """INSERT INTO jobs
               (id, title, customer_id, client_name, room, business_unit, job_number,
                pipeline_stage, metadata, current_revision, notes, gate_enforced)
               VALUES (?, ?, ?, ?, ?, 'workroom', ?, 'designing', ?, ?, ?, ?)""",
            (
                job_id,
                title,
                f"cust-{job_id}",
                client_name,
                room,
                f"JOB-2026-{job_id[-4:]}" if len(job_id) >= 4 else "JOB-2026-0401",
                json.dumps(metadata or {}),
                current_revision,
                notes,
                0 if gate_enforced is None else int(gate_enforced),
            ),
        )
    return job_id


def _link_quote(quote_id: str, job_id: str | None) -> str:
    with get_db() as conn:
        init_job_stages_schema(conn)
        conn.execute(
            """INSERT INTO quotes_v2 (id, quote_number, job_id, customer_name, status, total)
               VALUES (?, ?, ?, ?, 'draft', 100)""",
            (quote_id, f"EST-{quote_id}", job_id, "Mock Client"),
        )
    return quote_id


def _add_doc(job_id: str, document_type: str, filename: str) -> None:
    with get_db() as conn:
        init_job_stages_schema(conn)
        conn.execute(
            """INSERT INTO job_documents
               (id, job_id, document_type, url, filename, visible_to_client)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, 0)""",
            (job_id, document_type, f"/mock/{filename}", filename),
        )


def _client() -> TestClient:
    app = FastAPI()
    register_job_stage_exception_handlers(app)
    app.include_router(job_stages.router, prefix="/api/v1")
    return TestClient(app)


def test_catalog_has_eight_stages_in_order():
    assert [stage["order"] for stage in STAGES] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert STAGES[3]["key"] == STAGE_WORKROOM
    assert STAGES[5]["conditional"] is True
    assert STAGES[6]["conditional"] is True


def test_standard_naming_and_revision_bump():
    name = build_standard_name(
        client="Le Midi",
        area="Living Room",
        doc_type="estimate",
        revision=1,
        stage_key="estimate",
    )
    assert name == "LeMidi_LivingRoom_Estimate_REV1"
    internal = build_standard_name(
        client="Le Midi",
        area="Living Room",
        doc_type="estimate",
        revision=2,
        internal=True,
        extension="pdf",
        stage_key="estimate",
    )
    assert internal == "LeMidi_LivingRoom_Estimate_REV2_INTERNAL.pdf"
    parsed = parse_standard_name(internal)
    assert parsed["revision"] == 2
    assert parsed["internal"] is True
    assert next_revision([name, internal], internal=True) == 3


def test_ensure_creates_conditional_stages(isolated_empire_db):
    job_id = _seed_job(metadata={"referral": "Designer A"}, current_revision=2)
    with get_db() as conn:
        stages = ensure_job_stages(conn, job_id)
    by_key = {stage["stage_key"]: stage for stage in stages}
    assert len(stages) == 8
    assert by_key["referral_totals"]["required"] is True
    assert by_key["revision_comparison"]["required"] is True
    assert by_key["workroom_approval"]["status"] == "not_started"


def test_conditional_stages_off_without_referral_or_revision(isolated_empire_db):
    job_id = _seed_job(job_id="job-plain", title="Plain Job", client_name="Ada")
    with get_db() as conn:
        stages = ensure_job_stages(conn, job_id)
    by_key = {stage["stage_key"]: stage for stage in stages}
    assert by_key["referral_totals"]["required"] is False
    assert by_key["revision_comparison"]["required"] is False


def test_gate_blocks_client_estimate_until_stage_4_approved(isolated_empire_db):
    job_id = _seed_job(gate_enforced=1)
    with get_db() as conn:
        ensure_job_stages(conn, job_id)
    with pytest.raises(ClientEstimateGateError) as exc:
        assert_client_estimate_allowed(job_id)
    assert exc.value.payload["blocked"] is True
    assert exc.value.payload["required_stage"] == "workroom_approval"

    client = _client()
    blocked = client.post(f"/api/v1/jobs/{job_id}/estimates/client", json={"lines": []})
    assert blocked.status_code == 409
    assert blocked.json()["error"] == "WORKROOM_APPROVAL_REQUIRED"

    share = client.post(f"/api/v1/jobs/{job_id}/estimates/share")
    assert share.status_code == 409

    with get_db() as conn:
        approve_stage(conn, job_id, STAGE_WORKROOM, "workroom")
    allowed = assert_client_estimate_allowed(job_id)
    assert allowed["allowed"] is True
    opened = client.post(
        f"/api/v1/jobs/{job_id}/estimates/client",
        json={
            "lines": [
                {"area": "Living Room", "category": "Labor", "description": "Sew", "qty": 1, "unit_price": 100},
                {"area": "Living Room", "category": "Materials", "description": "Lining", "qty": 2, "unit_price": 20},
                {"area": "Living Room", "category": "Install", "description": "Hang", "qty": 1, "unit_price": 95},
            ]
        },
    )
    assert opened.status_code == 200
    body = opened.json()
    assert body["sent"] is False
    assert "INTERNAL" in body["internal_document"]["filename"]
    assert body["client_document"]["filename"].endswith("_REV1.pdf")


def test_new_revision_supersedes_older_docs(isolated_empire_db):
    job_id = _seed_job(job_id="job-rev", title="Rev Job", client_name="Ada")
    with get_db() as conn:
        first = register_document(
            conn, job_id=job_id, document_type="drawing", url="/mock/a.pdf",
            area="Dining", extension="pdf",
        )
        second = register_document(
            conn, job_id=job_id, document_type="drawing", url="/mock/b.pdf",
            area="Dining", extension="pdf",
        )
        older = conn.execute(
            "SELECT * FROM job_documents WHERE id = ?", (first["id"],)
        ).fetchone()
    assert first["filename"] == "Ada_Dining_Drawing_REV1_INTERNAL.pdf"
    assert second["filename"] == "Ada_Dining_Drawing_REV2_INTERNAL.pdf"
    assert older["superseded"] == 1
    assert older["superseded_by"] == second["id"]
    assert second["superseded"] == 0


def test_le_midi_backfill_lands_at_stage_4_awaiting_approval(isolated_empire_db):
    job_id = _seed_job()
    _add_doc(job_id, "photo", "le-midi-site.jpg")
    _add_doc(job_id, "drawing", "le-midi-elevation.pdf")
    _add_doc(job_id, "presentation", "le-midi-board.pdf")
    _add_doc(job_id, "workroom_approval", "le-midi-approval.pdf")
    with get_db() as conn:
        result = backfill_job_stages(conn, job_id)
        stages = {row["stage_key"]: row for row in list_stages(conn, job_id)}
    assert result["le_midi"] is True
    assert stages["prelim_info"]["status"] == "done"
    assert stages["drawing"]["status"] == "done"
    assert stages["presentation_board"]["status"] == "done"
    assert stages["workroom_approval"]["status"] == "drafted"
    assert stages["workroom_approval"]["approved_by"] is None
    assert stages["estimate"]["status"] == "not_started"
    state = assert_client_estimate_allowed(job_id)
    assert state["allowed"] is True
    assert state["grandfathered"] is True
    assert state["gate_enforced"] is False


def test_where_is_this_job_tool_and_max_answer(isolated_empire_db):
    job_id = _seed_job()
    _add_doc(job_id, "drawing", "le-midi-elevation.pdf")
    _add_doc(job_id, "workroom_approval", "le-midi-approval.pdf")
    assert wants_job_location("Where is this job — Le Midi?")
    location = answer_where_is_this_job("Where is this job Le Midi?")
    assert location["found"] is True
    assert location["current_stage_key"] == "workroom_approval"
    assert "approve" in location["next_step"].lower()
    source = Path(__file__).resolve().parents[1] / "app" / "services" / "max" / "tool_executor.py"
    text = source.read_text()
    assert '@tool("where_is_this_job")' in text
    assert '"job_status": "where_is_this_job"' in text


def test_square_invoice_stays_draft_until_rafael_says_send(isolated_empire_db):
    job_id = _seed_job(job_id="job-sq", title="Square Job", client_name="Ada")
    draft = create_square_invoice_draft(job_id, amount=500)
    assert draft["status"] == "draft"
    assert draft["sent"] is False
    assert draft["auto_send"] is False
    with pytest.raises(SquareSendGateError):
        send_square_invoice(job_id, authorized_by="max", express_send=True)
    with pytest.raises(SquareSendGateError):
        assert_square_send_allowed(authorized_by="rafael", express_send=False)
    authorized = send_square_invoice(
        job_id,
        authorized_by="rafael",
        express_send=True,
        send_phrase="rafael says send",
    )
    assert authorized["sent"] is False
    assert authorized["auto_send"] is False
    client = _client()
    refused = client.post(f"/api/v1/jobs/{job_id}/square-invoice/send", json={})
    assert refused.status_code == 409
    assert refused.json()["sent"] is False


def test_workroom_approval_pdf_is_three_pages_and_internal(isolated_empire_db):
    pdf = render_workroom_approval_pdf({
        "client_name": "Le Midi",
        "area": "Living Room",
        "job_number": "JOB-2026-0401",
        "measurements": {"width": '84"', "height": '96"'},
        "lines": [
            {"unit": "Ripplefold pair", "unit_price": 800, "qty": 1},
        ],
    })
    assert pdf.startswith(b"%PDF")
    assert pdf.count(b"/Type /Page") >= 3 or pdf.count(b"/Type/Page") >= 3
    assert b"DO NOT SEND TO CLIENT" in pdf
    assert b"WORKROOM APPROVED BY" in pdf


def test_willard_grouping_is_area_then_labor_materials_install():
    grouped = group_willard_lines([
        {"area": "Dining", "category": "install", "description": "Hang", "qty": 1, "unit_price": 95},
        {"area": "Dining", "category": "labor", "description": "Sew", "qty": 1, "unit_price": 200},
        {"area": "Dining", "category": "materials", "description": "Lining", "qty": 2, "unit_price": 40},
        {"area": "Kitchen", "category": "labor", "description": "Shade", "qty": 1, "unit_price": 150},
    ])
    assert [area["area"] for area in grouped] == ["Dining", "Kitchen"]
    dining = grouped[0]
    assert [bucket["name"] for bucket in dining["categories"]] == ["Labor", "Materials", "Install"]
    assert dining["base"] == 375.0
    assert dining["client_total"] == 450.0


def test_checklist_api_and_where_endpoint(isolated_empire_db):
    job_id = _seed_job()
    client = _client()
    client.post(f"/api/v1/jobs/{job_id}/stages/backfill")
    checklist = client.get(f"/api/v1/jobs/{job_id}/stages")
    assert checklist.status_code == 200
    body = checklist.json()
    assert body["current_stage_key"] == "workroom_approval"
    assert body["gate_enforced"] is False
    assert body["gate_open"] is True
    where = client.get(f"/api/v1/jobs/{job_id}/where")
    assert "stage 4" in where.json()["next_step"].lower() or "approve" in where.json()["next_step"].lower()
    gate = client.get(f"/api/v1/jobs/{job_id}/estimates/gate")
    assert gate.status_code == 200
    assert gate.json()["allowed"] is True


def test_cutover_grandfathered_jobs_keep_quote_pdf_paths_open(isolated_empire_db):
    """Existing jobs (Le Midi) are not gated; post-cutover jobs are."""
    midi = _seed_job()
    _link_quote("q-midi", midi)
    midi_state = assert_client_estimate_allowed_for_quote("q-midi")
    assert midi_state["allowed"] is True
    assert midi_state["grandfathered"] is True
    assert midi_state["gate_enforced"] is False

    new_id = _seed_job(
        job_id="job-new-gate", title="New Drapery", client_name="Ada", gate_enforced=1,
    )
    _link_quote("q-new", new_id)
    with pytest.raises(ClientEstimateGateError) as exc:
        assert_client_estimate_allowed_for_quote("q-new")
    assert exc.value.status_code == 409
    assert exc.value.payload["blocked"] is True

    with get_db() as conn:
        init_job_stages_schema(conn)
        cutover = get_gate_cutover_at(conn)
        assert cutover
        assert job_is_gate_enforced({"created_at": "1999-01-01T00:00:00"}, conn) is False
        assert job_is_gate_enforced({"created_at": "9999-12-31T00:00:00"}, conn) is True
        assert job_is_gate_enforced({"gate_enforced": 0, "created_at": "9999-12-31T00:00:00"}, conn) is False
    assert job_is_gate_enforced(None) is False


def test_quote_pdf_service_gate_is_http_409_not_500(isolated_empire_db):
    """Callers of quote_pdf_service must see 409, never a 500 from a bare raise.

    generate_quote_pdf itself is not imported here — its Max import graph
    is out of scope. The service calls assert_client_estimate_allowed_for_quote
    with no local try/except; that is the path under test.
    """
    job_id = _seed_job(
        job_id="job-pdf-gate", title="Gated Job", client_name="Ada", gate_enforced=1,
    )
    _link_quote("q-pdf-gate", job_id)

    source = Path(__file__).resolve().parents[1] / "app" / "services" / "quote_pdf_service.py"
    text = source.read_text()
    assert "assert_client_estimate_allowed_for_quote" in text
    assert "except ClientEstimateGateError" not in text

    quotes_src = Path(__file__).resolve().parents[1] / "app" / "routers" / "quotes.py"
    quotes_text = quotes_src.read_text()
    assert "assert_client_estimate_allowed_for_quote" in quotes_text
    tools = Path(__file__).resolve().parents[1] / "app" / "services" / "max" / "tool_executor.py"
    tool_src = tools.read_text()
    assert "def _quote_share_blocked" in tool_src
    assert "assert_client_estimate_allowed_for_quote" in tool_src

    with pytest.raises(ClientEstimateGateError) as raised:
        assert_client_estimate_allowed_for_quote("q-pdf-gate")
    assert raised.value.status_code == 409

    app = FastAPI()
    register_job_stage_exception_handlers(app)

    @app.get("/quotes/{quote_id}/pdf")
    def _pdf(quote_id: str):
        # Same call generate_quote_pdf / generate_pdf / Max share tools make.
        return assert_client_estimate_allowed_for_quote(quote_id)

    res = TestClient(app).get("/quotes/q-pdf-gate/pdf")
    assert res.status_code == 409
    assert res.json()["error"] == "WORKROOM_APPROVAL_REQUIRED"
    assert res.json()["blocked"] is True


def test_only_rafael_or_workroom_can_approve_stage_4(isolated_empire_db):
    job_id = _seed_job(
        job_id="job-acl", title="ACL Job", client_name="Ada", gate_enforced=1,
    )
    with get_db() as conn:
        ensure_job_stages(conn, job_id)
        with pytest.raises(StageApprovalDenied) as denied:
            approve_stage(conn, job_id, STAGE_WORKROOM, "max")
        assert denied.value.status_code == 403
        with pytest.raises(StageApprovalDenied):
            set_stage_status(conn, job_id, STAGE_WORKROOM, "approved", actor="max-agent")
        with pytest.raises(StageApprovalDenied):
            set_stage_status(conn, job_id, STAGE_WORKROOM, "approved", actor=None)

    client = _client()
    max_patch = client.patch(
        f"/api/v1/jobs/{job_id}/stages/workroom_approval",
        json={"status": "approved", "actor": "max"},
    )
    assert max_patch.status_code == 403
    assert max_patch.json()["error"] == "STAGE_APPROVAL_DENIED"

    max_approve = client.post(
        f"/api/v1/jobs/{job_id}/stages/workroom_approval/approve",
        json={"approved_by": "max"},
    )
    assert max_approve.status_code == 403

    workroom = client.post(
        f"/api/v1/jobs/{job_id}/stages/workroom_approval/approve",
        json={"approved_by": "workroom"},
    )
    assert workroom.status_code == 200
    assert workroom.json()["stage"]["status"] == "approved"

    tools = Path(__file__).resolve().parents[1] / "app" / "services" / "max" / "tool_executor.py"
    tool_src = tools.read_text()
    assert '@tool("approve_job_stage")' not in tool_src
    assert '@tool("approve_workroom")' not in tool_src
    assert "approve_stage(" not in tool_src


def test_create_job_from_quote_survives_backfill_error(isolated_empire_db, tmp_path, monkeypatch):
    from app.routers import jobs_unified

    quotes_dir = tmp_path / "quotes"
    quotes_dir.mkdir()
    (quotes_dir / "q-bf.json").write_text(json.dumps({
        "id": "q-bf",
        "quote_number": "EST-2026-0999",
        "customer_name": "Backfill Client",
        "total": 10,
        "rooms": [],
    }))
    monkeypatch.setattr(jobs_unified, "QUOTES_DIR", quotes_dir)
    monkeypatch.setattr(
        "app.services.job_stages.backfill.backfill_job_stages",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("backfill exploded")),
    )
    result = jobs_unified.create_job_from_quote("q-bf")
    job = result["job"]
    assert job["id"]
    assert result.get("quote_id") == "q-bf"
    assert job["stage_backfill"]["skipped"] is True
    assert "backfill exploded" in job["stage_backfill"]["error"]
    with get_db() as conn:
        row = conn.execute("SELECT id FROM jobs WHERE id = ?", (job["id"],)).fetchone()
    assert row is not None

    wrapper = Path(__file__).resolve().parents[1] / "app" / "routers" / "jobs_unified.py"
    src = wrapper.read_text()
    assert "def _safe_stage_backfill_after_create" in src
    assert "except Exception" in src.split("def _safe_stage_backfill_after_create", 1)[1][:800]


def test_quote_whose_job_was_deleted_is_allowed(isolated_empire_db):
    job_id = _seed_job(
        job_id="job-gone", title="Deleted Job", client_name="Ada", gate_enforced=1,
    )
    _link_quote("q-orphan", job_id)
    assert resolve_job_id_for_quote("q-orphan") == job_id
    with get_db() as conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    assert resolve_job_id_for_quote("q-orphan") is None
    assert assert_client_estimate_allowed_for_quote("q-orphan") is None
    assert assert_client_estimate_allowed("job-gone")["allowed"] is True
    assert assert_client_estimate_allowed("job-gone")["job_missing"] is True


def test_wants_job_location_does_not_hijack_other_max_messages():
    assert wants_job_location("Where is this job — Le Midi?") is True
    assert wants_job_location("Where is this job?") is True
    assert wants_job_location("Where are we on this job?") is True
    assert wants_job_location("What's missing on this job?") is True
    assert wants_job_location("what's the current stage") is False
    assert wants_job_location("what's the current stage of this job") is False
    assert wants_job_location("generate an estimate for this job") is False
    assert wants_job_location("update job status") is False
    assert wants_job_location("send the invoice for this job") is False
    assert wants_job_location("approve quote for the Le Midi job") is False
    assert wants_job_location("draw the elevation for this job") is False
    assert wants_job_location("Where is this job and also generate an estimate") is False
    assert wants_job_location("x" * 200) is False
