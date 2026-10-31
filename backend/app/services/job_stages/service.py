"""Per-job stage checklist: ensure, status, approve, document link, location."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db.database import dict_row, get_db
from app.services.job_stages.catalog import (
    STAGE_REFERRAL,
    STAGE_REVISION,
    STAGES,
    STATUS_APPROVED,
    STATUS_DONE,
    STATUS_DRAFTED,
    STATUS_NOT_STARTED,
    VALID_STATUSES,
    infer_stage_key,
    stage_definition,
)
from app.services.job_stages.naming import (
    build_standard_name,
    family_key,
    next_revision,
    parse_standard_name,
)
from app.services.job_stages.schema import init_job_stages_schema


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


def _parse_linked(raw: Any) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(item) for item in raw]
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return [raw] if raw else []
        if isinstance(data, list):
            return [str(item) for item in data]
    return []


def _stage_row(row) -> dict[str, Any]:
    data = dict_row(row) if row is not None and not isinstance(row, dict) else dict(row or {})
    if not data:
        return data
    data["linked_documents"] = _parse_linked(data.get("linked_documents"))
    data["required"] = bool(data.get("required", 1))
    definition = stage_definition(data["stage_key"])
    data["title"] = definition["title"]
    data["description"] = definition["description"]
    data["conditional"] = bool(definition.get("conditional"))
    data["doc_type"] = definition["doc_type"]
    data["order"] = definition["order"]
    data["gate"] = bool(definition.get("gate"))
    return data


def job_has_referral(conn, job: dict[str, Any]) -> bool:
    metadata = job.get("metadata")
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except (json.JSONDecodeError, TypeError):
            metadata = {}
    metadata = metadata or {}
    if metadata.get("referral") or metadata.get("referral_name") or metadata.get("referred_by"):
        return True
    title = f"{job.get('title') or ''} {job.get('client_name') or ''} {job.get('notes') or ''}".lower()
    if "referral" in title:
        return True
    try:
        count = conn.execute(
            """SELECT COUNT(*) FROM job_documents
               WHERE job_id = ? AND (
                   lower(COALESCE(document_type, '')) LIKE '%referral%'
                   OR lower(COALESCE(filename, '')) LIKE '%referral%'
                   OR lower(COALESCE(stage_key, '')) = 'referral_totals'
               )""",
            (job["id"],),
        ).fetchone()[0]
    except Exception:
        count = 0
    return count > 0


def job_is_revised(conn, job: dict[str, Any]) -> bool:
    revision = job.get("current_revision") or 1
    try:
        revision = int(revision)
    except (TypeError, ValueError):
        revision = 1
    if revision > 1:
        return True
    try:
        rev_count = conn.execute(
            "SELECT COUNT(*) FROM job_revisions WHERE job_id = ?",
            (job["id"],),
        ).fetchone()[0]
    except Exception:
        rev_count = 0
    if rev_count:
        return True
    try:
        doc_count = conn.execute(
            """SELECT COUNT(*) FROM job_documents
               WHERE job_id = ? AND (
                   lower(COALESCE(document_type, '')) LIKE '%revision%'
                   OR lower(COALESCE(filename, '')) LIKE '%revision%'
                   OR lower(COALESCE(stage_key, '')) = 'revision_comparison'
               )""",
            (job["id"],),
        ).fetchone()[0]
    except Exception:
        doc_count = 0
    return doc_count > 0


def _load_job(conn, job_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return dict_row(row) if row else None


def stage_is_required(conn, job: dict[str, Any], stage_key: str) -> bool:
    definition = stage_definition(stage_key)
    if not definition.get("conditional"):
        return True
    if definition.get("required_when") == "referral":
        return job_has_referral(conn, job)
    if definition.get("required_when") == "revision":
        return job_is_revised(conn, job)
    return False


def ensure_job_stages(conn, job_id: str) -> list[dict[str, Any]]:
    """Create the 8 stage rows for a job. Conditional stages flip required."""
    init_job_stages_schema(conn)
    job = _load_job(conn, job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")
    existing = {
        row["stage_key"]: row
        for row in conn.execute(
            "SELECT * FROM job_stages WHERE job_id = ?", (job_id,)
        ).fetchall()
    }
    for definition in STAGES:
        required = 1 if stage_is_required(conn, job, definition["key"]) else 0
        current = existing.get(definition["key"])
        if current is None:
            conn.execute(
                """INSERT INTO job_stages
                   (id, job_id, stage_key, stage_order, status, linked_documents, required)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    _new_id(),
                    job_id,
                    definition["key"],
                    definition["order"],
                    STATUS_NOT_STARTED,
                    "[]",
                    required,
                ),
            )
        elif int(current["required"] or 0) != required:
            conn.execute(
                "UPDATE job_stages SET required = ?, updated_at = datetime('now') "
                "WHERE job_id = ? AND stage_key = ?",
                (required, job_id, definition["key"]),
            )
    return list_stages(conn, job_id)


def list_stages(conn, job_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM job_stages WHERE job_id = ? ORDER BY stage_order",
        (job_id,),
    ).fetchall()
    return [_stage_row(row) for row in rows]


def get_stage(conn, job_id: str, stage_key: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM job_stages WHERE job_id = ? AND stage_key = ?",
        (job_id, stage_key),
    ).fetchone()
    return _stage_row(row) if row else None


def set_stage_status(
    conn,
    job_id: str,
    stage_key: str,
    status: str,
    *,
    actor: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid stage status: {status}")
    stage_definition(stage_key)
    ensure_job_stages(conn, job_id)
    fields = ["status = ?", "updated_at = datetime('now')"]
    values: list[Any] = [status]
    if notes is not None:
        fields.append("notes = ?")
        values.append(notes)
    if status == STATUS_APPROVED:
        fields.append("approved_by = ?")
        fields.append("approved_at = ?")
        values.append(actor or "workroom")
        values.append(_now())
    elif status in {STATUS_NOT_STARTED, STATUS_DRAFTED}:
        fields.append("approved_by = NULL")
        fields.append("approved_at = NULL")
    values.extend([job_id, stage_key])
    conn.execute(
        f"UPDATE job_stages SET {', '.join(fields)} WHERE job_id = ? AND stage_key = ?",
        values,
    )
    return get_stage(conn, job_id, stage_key)


def approve_stage(conn, job_id: str, stage_key: str, approved_by: str) -> dict[str, Any]:
    if not (approved_by or "").strip():
        raise ValueError("approved_by is required")
    return set_stage_status(
        conn, job_id, stage_key, STATUS_APPROVED, actor=approved_by.strip()
    )


def link_document_to_stage(
    conn,
    job_id: str,
    stage_key: str,
    document_id: str,
    *,
    mark_drafted: bool = True,
) -> dict[str, Any]:
    ensure_job_stages(conn, job_id)
    stage = get_stage(conn, job_id, stage_key)
    if not stage:
        raise ValueError(f"Stage {stage_key} not found for job {job_id}")
    linked = list(stage["linked_documents"])
    if document_id not in linked:
        linked.append(document_id)
    new_status = stage["status"]
    if mark_drafted and new_status == STATUS_NOT_STARTED:
        new_status = STATUS_DRAFTED
    conn.execute(
        """UPDATE job_stages
           SET linked_documents = ?, status = ?, updated_at = datetime('now')
           WHERE job_id = ? AND stage_key = ?""",
        (json.dumps(linked), new_status, job_id, stage_key),
    )
    conn.execute(
        "UPDATE job_documents SET stage_key = ? WHERE id = ?",
        (stage_key, document_id),
    )
    return get_stage(conn, job_id, stage_key)


def _document_family_rows(conn, job_id: str, key: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM job_documents WHERE job_id = ? ORDER BY created_at DESC",
        (job_id,),
    ).fetchall()
    matches = []
    for row in rows:
        doc = dict_row(row)
        parsed = parse_standard_name(doc.get("standard_name") or doc.get("filename"))
        internal = (doc.get("audience") or "").lower() == "internal"
        if parsed:
            doc_key = family_key(
                client=parsed["client"],
                area=parsed["area"],
                doc_type=parsed["doc_type"],
                internal=parsed["internal"],
            )
        else:
            doc_key = family_key(
                client=None,
                area=None,
                doc_type=doc.get("document_type"),
                stage_key=doc.get("stage_key"),
                internal=internal,
            )
        if doc_key == key:
            matches.append(doc)
    return matches


def register_document(
    conn,
    *,
    job_id: str,
    document_type: str,
    url: str,
    filename: str | None = None,
    item_key: str | None = None,
    route_to: str | None = None,
    visible_to_client: bool = False,
    audience: str | None = None,
    stage_key: str | None = None,
    area: str | None = None,
    client: str | None = None,
    extension: str | None = None,
    revision: int | None = None,
) -> dict[str, Any]:
    """Insert a named document, bump REV#, and mark older copies superseded."""
    init_job_stages_schema(conn)
    job = _load_job(conn, job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")
    resolved_stage = stage_key or infer_stage_key(document_type, filename)
    internal = (audience or "").lower() == "internal" or (
        not visible_to_client and (audience or "").lower() != "client"
    )
    if visible_to_client:
        internal = False
        audience = "client"
    elif not audience:
        audience = "internal" if internal else "client"
    client_name = client or job.get("client_name") or job.get("title")
    area_name = area or job.get("room") or item_key or "Job"
    ext = extension
    if not ext and filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1]
    family = family_key(
        client=client_name,
        area=area_name,
        doc_type=document_type,
        stage_key=resolved_stage,
        internal=internal,
    )
    existing = _document_family_rows(conn, job_id, family)
    names = [doc.get("standard_name") or doc.get("filename") or "" for doc in existing]
    computed = next_revision(names, internal=internal)
    rev = max(computed, int(revision or 1))
    standard_name = build_standard_name(
        client=client_name,
        area=area_name,
        doc_type=document_type,
        revision=rev,
        internal=internal,
        extension=ext,
        stage_key=resolved_stage,
    )
    doc_id = _new_id()
    conn.execute(
        """INSERT INTO job_documents
           (id, job_id, document_type, item_key, route_to, url, filename, revision,
            visible_to_client, superseded, standard_name, audience, stage_key)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)""",
        (
            doc_id,
            job_id,
            document_type,
            item_key,
            route_to,
            url,
            standard_name,
            rev,
            1 if visible_to_client else 0,
            standard_name,
            audience,
            resolved_stage,
        ),
    )
    for older in existing:
        if older.get("id") == doc_id:
            continue
        if older.get("superseded"):
            continue
        conn.execute(
            "UPDATE job_documents SET superseded = 1, superseded_by = ? WHERE id = ?",
            (doc_id, older["id"]),
        )
    if resolved_stage:
        link_document_to_stage(conn, job_id, resolved_stage, doc_id)
    row = conn.execute("SELECT * FROM job_documents WHERE id = ?", (doc_id,)).fetchone()
    return dict_row(row)


def _documents_for_stage(conn, job_id: str, stage_key: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """SELECT * FROM job_documents
           WHERE job_id = ? AND (
               stage_key = ?
               OR lower(COALESCE(document_type, '')) LIKE ?
           )
           ORDER BY created_at DESC""",
        (job_id, stage_key, f"%{stage_key.split('_')[0]}%"),
    ).fetchall()
    return [dict_row(row) for row in rows]


def _stage_complete(stage: dict[str, Any]) -> bool:
    if not stage.get("required"):
        return True
    if stage["stage_key"] == "workroom_approval":
        return stage["status"] in {STATUS_APPROVED, STATUS_DONE}
    return stage["status"] in {STATUS_APPROVED, STATUS_DONE}


def _missing_for_stage(stage: dict[str, Any], documents: list[dict[str, Any]]) -> list[str]:
    missing: list[str] = []
    if not stage.get("required"):
        return missing
    live_docs = [doc for doc in documents if not doc.get("superseded")]
    if stage["status"] == STATUS_NOT_STARTED:
        missing.append(f"{stage['title']} has not been started.")
    if not live_docs:
        missing.append(f"No current {stage['doc_type']} document is linked.")
    if stage["stage_key"] == "workroom_approval" and stage["status"] not in {
        STATUS_APPROVED, STATUS_DONE,
    }:
        missing.append("Workroom approval is required before a client estimate.")
    if stage["stage_key"] == "square_invoice" and stage["status"] != STATUS_DONE:
        missing.append("Square invoice stays a draft until Rafael expressly says send.")
    return missing


def _next_step(stage: dict[str, Any] | None) -> str:
    if stage is None:
        return "All required document-set stages are complete."
    key = stage["stage_key"]
    if key == "prelim_info":
        return "Collect site measurements, photos, and first notes into the Prelim Info Sheet."
    if key == "drawing":
        return "Produce the elevation/plan with full dimensions on the gold template."
    if key == "presentation_board":
        return "Build the presentation board: concept, layers, and fabric."
    if key == "workroom_approval":
        return (
            "Workroom must approve the 3-page approval document before any "
            "estimate goes to the client."
        )
    if key == "estimate":
        return (
            "Generate the Willard-layout estimate (client + INTERNAL copies) "
            "grouped by area, then Labor / Materials / Install."
        )
    if key == "referral_totals":
        return "Issue referral totals for this referred job."
    if key == "revision_comparison":
        return "Produce the revision comparison for the current change."
    if key == "square_invoice":
        return "Keep the Square invoice as a draft until Rafael expressly says send."
    return f"Complete {stage['title']}."


def job_location(conn, job_id: str) -> dict[str, Any]:
    ensure_job_stages(conn, job_id)
    job = _load_job(conn, job_id)
    stages = list_stages(conn, job_id)
    current = None
    for stage in stages:
        if not _stage_complete(stage):
            current = stage
            break
    documents = _documents_for_stage(conn, job_id, current["stage_key"]) if current else []
    missing = _missing_for_stage(current, documents) if current else []
    return {
        "job_id": job_id,
        "job_number": job.get("job_number") if job else None,
        "title": job.get("title") if job else None,
        "client_name": job.get("client_name") if job else None,
        "current_stage": current,
        "current_stage_key": current["stage_key"] if current else None,
        "current_stage_title": current["title"] if current else "Complete",
        "current_status": current["status"] if current else STATUS_DONE,
        "missing": missing,
        "next_step": _next_step(current),
        "stages": stages,
        "gate_open": any(
            stage["stage_key"] == "workroom_approval"
            and stage["status"] in {STATUS_APPROVED, STATUS_DONE}
            for stage in stages
        ),
    }


def find_job(conn, query: str | None) -> dict[str, Any] | None:
    text = (query or "").strip()
    if not text:
        return None
    row = conn.execute(
        "SELECT * FROM jobs WHERE id = ? OR job_number = ? COLLATE NOCASE",
        (text, text),
    ).fetchone()
    if row:
        return dict_row(row)
    like = f"%{text}%"
    row = conn.execute(
        """SELECT * FROM jobs
           WHERE title LIKE ? OR client_name LIKE ? OR room LIKE ?
           ORDER BY updated_at DESC LIMIT 1""",
        (like, like, like),
    ).fetchone()
    return dict_row(row) if row else None


def get_checklist(job_id: str) -> dict[str, Any]:
    with get_db() as conn:
        location = job_location(conn, job_id)
        documents = [
            dict_row(row)
            for row in conn.execute(
                "SELECT * FROM job_documents WHERE job_id = ? ORDER BY created_at DESC",
                (job_id,),
            ).fetchall()
        ]
    location["documents"] = documents
    return location


def format_location_answer(location: dict[str, Any]) -> str:
    title = location.get("title") or location.get("job_number") or location.get("job_id")
    current = location.get("current_stage_title") or "Complete"
    status = location.get("current_status") or "done"
    missing = location.get("missing") or []
    next_step = location.get("next_step") or ""
    lines = [
        f"{title} is at {current} ({status.replace('_', ' ')}).",
    ]
    if missing:
        lines.append("Missing: " + " ".join(missing))
    else:
        lines.append("Nothing required is missing on the current stage.")
    lines.append(f"Next step: {next_step}")
    if not location.get("gate_open"):
        lines.append(
            "Client estimate generation and share/export stay blocked "
            "until workroom approval is signed off."
        )
    return " ".join(lines)
