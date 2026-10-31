"""Infer job_stages from existing job_documents. Le Midi lands at stage 4."""
from __future__ import annotations

import json
from typing import Any

from app.db.database import dict_row
from app.services.job_stages.catalog import (
    STAGE_PRELIM,
    STAGE_WORKROOM,
    STAGES,
    STATUS_APPROVED,
    STATUS_DONE,
    STATUS_DRAFTED,
    STATUS_NOT_STARTED,
    infer_stage_key,
)
from app.services.job_stages.schema import init_job_stages_schema
from app.services.job_stages.service import (
    ensure_job_stages,
    get_stage,
    link_document_to_stage,
    set_job_gate_enforced,
    set_stage_status,
)


LE_MIDI_MARKERS = ("le midi", "lemidi")


def _is_le_midi(job: dict[str, Any]) -> bool:
    haystack = " ".join(
        str(job.get(field) or "")
        for field in ("title", "client_name", "room", "description", "notes", "job_number")
    ).lower()
    return any(marker in haystack for marker in LE_MIDI_MARKERS)


def _docs_by_stage(documents: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {stage["key"]: [] for stage in STAGES}
    for doc in documents:
        key = doc.get("stage_key") or infer_stage_key(
            doc.get("document_type"), doc.get("filename") or doc.get("standard_name")
        )
        if key and key in grouped:
            grouped[key].append(doc)
    return grouped


def _highest_inferred_order(grouped: dict[str, list[dict[str, Any]]]) -> int:
    highest = 0
    for stage in STAGES:
        if grouped.get(stage["key"]):
            highest = max(highest, stage["order"])
    return highest


def backfill_job_stages(conn, job_id: str) -> dict[str, Any]:
    """Infer status from job_documents. Le Midi ends at stage 4, awaiting approval."""
    init_job_stages_schema(conn)
    job_row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job_row:
        raise ValueError(f"Job {job_id} not found")
    job = dict_row(job_row)
    ensure_job_stages(conn, job_id)
    documents = [
        dict_row(row)
        for row in conn.execute(
            "SELECT * FROM job_documents WHERE job_id = ? ORDER BY created_at ASC",
            (job_id,),
        ).fetchall()
    ]
    grouped = _docs_by_stage(documents)
    le_midi = _is_le_midi(job)
    highest = _highest_inferred_order(grouped)
    if le_midi:
        # Founder rule: Le Midi is waiting on workroom approval.
        highest = max(highest, 4)

    for stage in STAGES:
        key = stage["key"]
        docs = grouped.get(key) or []
        for doc in docs:
            if doc.get("id"):
                link_document_to_stage(conn, job_id, key, doc["id"], mark_drafted=False)
        current = get_stage(conn, job_id, key)
        if not current:
            continue
        if current["status"] in {STATUS_APPROVED, STATUS_DONE}:
            continue
        if not current["required"] and not docs:
            continue
        if le_midi and key == STAGE_WORKROOM:
            set_stage_status(conn, job_id, key, STATUS_DRAFTED, notes="backfill: Le Midi awaiting approval")
            continue
        if le_midi and stage["order"] < 4:
            set_stage_status(conn, job_id, key, STATUS_DONE, notes="backfill: inferred complete before stage 4")
            continue
        if docs and stage["order"] < highest and key != STAGE_WORKROOM:
            set_stage_status(conn, job_id, key, STATUS_DONE, notes="backfill: later documents exist")
            continue
        if docs:
            set_stage_status(conn, job_id, key, STATUS_DRAFTED, notes="backfill: document present")
            continue
        if highest >= stage["order"] and stage["order"] < 4 and current["required"]:
            # Prior required stages without files still count as done once later
            # work exists — the paper trail started after intake.
            set_stage_status(conn, job_id, key, STATUS_DONE, notes="backfill: implied by later stage")

    if le_midi:
        # Existing Le Midi is grandfathered: checklist still shows stage 4,
        # but the client-estimate gate does not apply.
        set_job_gate_enforced(conn, job_id, False)
        # Never invent an approval. Stage 4 stays drafted / awaiting.
        workroom = get_stage(conn, job_id, STAGE_WORKROOM)
        if workroom and workroom["status"] in {STATUS_APPROVED, STATUS_DONE}:
            set_stage_status(
                conn, job_id, STAGE_WORKROOM, STATUS_DRAFTED,
                notes="backfill: Le Midi reset to awaiting approval",
            )
        # Do not leave later stages ahead of an unapproved gate.
        for stage in STAGES:
            if stage["order"] > 4:
                later = get_stage(conn, job_id, stage["key"])
                if later and later["status"] != STATUS_NOT_STARTED and later["required"]:
                    set_stage_status(
                        conn, job_id, stage["key"], STATUS_NOT_STARTED,
                        notes="backfill: held until workroom approval",
                    )
        if not grouped.get(STAGE_PRELIM) and not grouped.get(STAGE_WORKROOM):
            # Guarantee the checklist shows work in progress at stage 4.
            set_stage_status(
                conn, job_id, STAGE_WORKROOM, STATUS_DRAFTED,
                notes="backfill: Le Midi awaiting approval",
            )

    stages = [
        dict_row(row)
        for row in conn.execute(
            "SELECT * FROM job_stages WHERE job_id = ? ORDER BY stage_order",
            (job_id,),
        ).fetchall()
    ]
    return {
        "job_id": job_id,
        "title": job.get("title"),
        "le_midi": le_midi,
        "document_count": len(documents),
        "gate_enforced": False if le_midi else bool(int(job.get("gate_enforced") or 0)),
        "stages": stages,
    }


def backfill_all_jobs(conn) -> dict[str, Any]:
    init_job_stages_schema(conn)
    jobs = [dict_row(row) for row in conn.execute("SELECT id, title, client_name FROM jobs").fetchall()]
    results = [backfill_job_stages(conn, job["id"]) for job in jobs]
    le_midi = [item for item in results if item.get("le_midi")]
    return {
        "job_count": len(results),
        "le_midi_jobs": le_midi,
        "results": results,
    }
