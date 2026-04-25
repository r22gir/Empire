"""Timeline-aware TranscriptForge incident diagnosis.

Hermes is consulted before runtime diagnosis. MAX remains the authority on the
classification and OpenClaw is only used as a bounded repair executor after its
gate is healthy.
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.db.database import get_db
from app.services.max.brain.memory_store import MemoryStore
from app.services.max.openclaw_gate import check_openclaw_gate
from app.services.max.startup_health import read_startup_health_record


BASE_DIR = Path.home() / "empire-repo" / "backend" / "data" / "transcriptforge"
JOBS_DIR = BASE_DIR / "jobs"
CHUNKS_DIR = BASE_DIR / "chunks"
TRANSCRIPTS_DIR = BASE_DIR / "transcripts"
PENDING_SKILLS_DIR = (
    Path.home()
    / "empire-repo"
    / "backend"
    / "app"
    / "services"
    / "max"
    / "brain"
    / "TRANSCRIPTFORGE"
    / "pending_skills"
)

KNOWN_FIX_COMMITS = {
    "transcriptforge_added": "55eeeea",
    "route_prefix_fix": "d4869bb",
    "upload_background_tasks_fix": "560288d",
    "first_chunk_gate_fix": "7bf95c2",
    "final_chunk_loop_fix": "87071f4",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _safe_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _run_git(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=Path.home() / "empire-repo",
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return None


def _commit_info(short_hash: str) -> dict[str, Any]:
    raw = _run_git("show", "-s", "--format=%h%x00%H%x00%cI%x00%s", short_hash)
    if not raw:
        return {"key": short_hash, "hash": short_hash, "available": False}
    short, full, committed_at, subject = raw.split("\x00", 3)
    return {
        "short": short,
        "hash": full,
        "committed_at": committed_at,
        "subject": subject,
        "available": True,
    }


def _current_commit() -> str | None:
    return _run_git("rev-parse", "--short", "HEAD")


def _infer_memory_status(memory: dict[str, Any]) -> str:
    tags = [str(tag).upper() for tag in (memory.get("tags") or [])]
    if "PENDING" in tags:
        return "PENDING"
    if "ACTIVE" in tags:
        return "ACTIVE"

    haystack = " ".join(
        [
            str(memory.get("subject") or ""),
            str(memory.get("content") or ""),
            " ".join(tags),
        ]
    ).upper()
    if re.search(r'"STATUS"\s*:\s*"PENDING"|STATUS\s*:\s*PENDING|\bPENDING\b', haystack):
        return "PENDING"
    if re.search(r'"STATUS"\s*:\s*"ACTIVE"|STATUS\s*:\s*ACTIVE|\bACTIVE\b', haystack):
        return "ACTIVE"
    return "memory-only"


def _extract_last_fix(content: str) -> dict[str, str | None]:
    commit = re.search(r"\b[0-9a-f]{7,40}\b", content or "")
    date = re.search(r"\b20\d{2}-\d{2}-\d{2}(?:T[\d:.+\-Z]+)?\b", content or "")
    return {
        "commit": commit.group(0) if commit else None,
        "date": date.group(0) if date else None,
    }


def hermes_first_consult(query: str, limit: int = 10) -> dict[str, Any]:
    """First required step for TranscriptForge incident analysis."""
    store = MemoryStore()
    queries = [
        query,
        "TranscriptForge stuck job",
        "TranscriptForge first-chunk pause",
        "transcriptforge timeline review",
        "transcriptforge incident",
    ]
    memories_by_id: dict[str, dict[str, Any]] = {}
    for item in queries:
        for memory in store.search_memories(query=item, limit=limit):
            if memory.get("id"):
                memories_by_id[memory["id"]] = memory
    memories = list(memories_by_id.values())[:limit]
    matches = []
    for memory in memories:
        content = str(memory.get("content") or "")
        matches.append(
            {
                "id": memory.get("id"),
                "subject": memory.get("subject"),
                "category": memory.get("category"),
                "subcategory": memory.get("subcategory"),
                "status": _infer_memory_status(memory),
                "importance": memory.get("importance"),
                "created_at": memory.get("created_at"),
                "last_verified_fix": _extract_last_fix(content),
            }
        )
    return {
        "queried_at": _now(),
        "query": query,
        "query_aliases": queries[1:],
        "matches": matches,
        "count": len(matches),
        "first_consult_rule": "satisfied",
    }


def _list_jobs() -> list[dict[str, Any]]:
    jobs = []
    if not JOBS_DIR.exists():
        return jobs
    for path in JOBS_DIR.glob("*.json"):
        job = _safe_json(path)
        if not job:
            continue
        job["_artifact"] = {
            "path": str(path),
            "mtime": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        }
        jobs.append(job)
    jobs.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return jobs


def _chunk_artifacts(job_id: str) -> list[dict[str, Any]]:
    artifacts = []
    for path in sorted(CHUNKS_DIR.glob(f"{job_id}_chunk_*.json")):
        chunk = _safe_json(path) or {}
        artifacts.append(
            {
                "chunk_id": chunk.get("chunk_id") or path.stem.replace(f"{job_id}_", ""),
                "path": str(path),
                "mtime": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                "size": path.stat().st_size,
                "has_raw_transcript": bool(chunk.get("raw_transcript")),
                "processing_status": chunk.get("processing_status"),
                "review_status": chunk.get("review_status"),
                "confidence": chunk.get("confidence"),
                "raw_transcript_path": chunk.get("raw_transcript_path"),
                "verified_transcript_path": chunk.get("verified_transcript_path"),
            }
        )
    return artifacts


def _transcript_artifacts(job_id: str) -> list[dict[str, Any]]:
    artifacts = []
    paths = list(TRANSCRIPTS_DIR.glob(f"{job_id}*.txt"))
    paths.extend((TRANSCRIPTS_DIR / job_id).glob("*.txt") if (TRANSCRIPTS_DIR / job_id).exists() else [])
    for path in sorted(paths):
        artifacts.append(
            {
                "path": str(path),
                "mtime": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                "size": path.stat().st_size,
            }
        )
    return artifacts


def _backend_log_evidence(job_ids: list[str], since: datetime | None) -> dict[str, Any]:
    if not job_ids:
        return {"lines": [], "source": "journalctl", "available": True}
    since_arg = (since or (datetime.now(timezone.utc) - timedelta(hours=12))).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    try:
        result = subprocess.run(
            ["journalctl", "--user", "-u", "empire-backend.service", "--since", since_arg, "--no-pager"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except Exception as exc:
        return {"lines": [], "source": "journalctl", "available": False, "error": str(exc)}

    patterns = ["transcriptforge", "chunk", "transcrib", "GStreamer", "ValidationError", "NameError", *job_ids]
    lines = []
    for line in result.stdout.splitlines():
        lower = line.lower()
        if any(pattern.lower() in lower for pattern in patterns):
            lines.append(line)
    return {"lines": lines[-120:], "source": "journalctl", "available": True}


def _classify_job(job: dict[str, Any], commits: dict[str, dict[str, Any]], current_commit: str | None) -> dict[str, Any]:
    created = _parse_dt(job.get("created_at"))
    updated = _parse_dt(job.get("updated_at"))
    chunks = job.get("chunks") or []
    transcribed = [c for c in chunks if c.get("raw_transcript")]
    pending = [c for c in chunks if not c.get("raw_transcript")]
    state = job.get("state")
    age_since_update = (datetime.now(timezone.utc) - updated).total_seconds() if updated else None

    upload_fix = _parse_dt(commits["upload_background_tasks_fix"].get("committed_at"))
    first_gate_fix = _parse_dt(commits["first_chunk_gate_fix"].get("committed_at"))
    final_loop_fix = _parse_dt(commits["final_chunk_loop_fix"].get("committed_at"))

    labels: list[str] = []
    evidence: list[str] = []

    if created and upload_fix and created < upload_fix and not transcribed:
        labels.append("old_dead_job")
        labels.append("kickoff_failure")
        evidence.append("job predates upload background task fix and has no raw transcript")
    elif created and first_gate_fix and created < first_gate_fix and state == "chunking" and not chunks:
        labels.append("old_dead_job")
        labels.append("queueing_failure")
        evidence.append("job predates first-chunk gate fix and never persisted chunks")
    elif created and final_loop_fix and created < final_loop_fix and state == "chunking" and not chunks:
        labels.append("old_dead_job")
        labels.append("chunking_failure")
        evidence.append("job predates final chunk loop fix and remains in chunking with zero chunks")

    if created and final_loop_fix and created >= final_loop_fix and state == "first_chunk_ready":
        if transcribed and transcribed[0].get("sequence") == 0:
            labels.append("newly_fixed_path")
            labels.append("intended_pause_behavior")
            evidence.append("post-fix job has chunk_000 raw transcript and is paused before remaining chunks by design")

    if state == "first_chunk_processing" and not transcribed and age_since_update and age_since_update > 600:
        labels.append("still_live_bug")
        labels.append("stalled")
        labels.append("kickoff_failure")
        evidence.append(f"job has been first_chunk_processing without transcript for {int(age_since_update)}s")

    if state == "first_chunk_ready" and transcribed and pending:
        labels.append("paused_by_design")
        evidence.append("remaining chunks are pending because only chunk_000 is queued before review")

    if any(c.get("raw_provider_result") for c in transcribed):
        labels.append("provider_success_evidence")
        evidence.append("at least one chunk has provider result metadata")

    classification = "unknown"
    if "old_dead_job" in labels:
        classification = "old_dead_job"
    elif "paused_by_design" in labels or "intended_pause_behavior" in labels:
        classification = "intended_pause_behavior"
    elif "still_live_bug" in labels:
        classification = "still_live_bug"
    elif state in {"approved", "corrected_and_approved"}:
        classification = "completed"

    return {
        "job_id": job.get("job_id"),
        "classification": classification,
        "labels": sorted(set(labels)),
        "evidence": evidence,
        "state": state,
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "created_after_latest_fix": bool(created and final_loop_fix and created >= final_loop_fix),
        "running_commit": current_commit,
        "chunks_total": job.get("chunks_total", 0),
        "chunks_complete": job.get("chunks_complete", 0),
        "chunks_failed": job.get("chunks_failed", 0),
        "transcribed_chunks": [c.get("chunk_id") for c in transcribed],
        "pending_chunks": [c.get("chunk_id") for c in pending],
        "chunk_1_started": any((c.get("sequence") == 0 and c.get("processing_status") in {"transcribing", "transcribed"}) or (c.get("sequence") == 0 and c.get("raw_transcript")) for c in chunks),
        "has_transcript_text": any(bool(c.get("raw_transcript")) for c in chunks),
    }


def build_transcriptforge_incident_diagnosis(job_id: str | None = None, include_logs: bool = True) -> dict[str, Any]:
    consult = hermes_first_consult(
        "TranscriptForge stuck job first_chunk_ready background_tasks final chunk loop OpenClaw gate"
    )
    commits = {name: _commit_info(commit) for name, commit in KNOWN_FIX_COMMITS.items()}
    current_commit = _current_commit()
    startup = read_startup_health_record() or {}
    gate = check_openclaw_gate(force=True).to_dict()
    jobs = _list_jobs()
    selected = next((job for job in jobs if job.get("job_id") == job_id), None) if job_id else (jobs[0] if jobs else None)

    classifications = [_classify_job(job, commits, current_commit) for job in jobs]
    selected_classification = (
        next((item for item in classifications if selected and item["job_id"] == selected.get("job_id")), None)
        if selected
        else None
    )

    earliest = min((_parse_dt(job.get("created_at")) for job in jobs if _parse_dt(job.get("created_at"))), default=None)
    log_job_ids = [j.get("job_id") for j in jobs if j.get("job_id")]
    logs = _backend_log_evidence(log_job_ids, earliest) if include_logs else {"lines": [], "source": "journalctl", "available": False}

    chunk0_success = any("provider_success_evidence" in item["labels"] for item in classifications)
    restart_mismatch = bool(startup.get("running_commit_hash") and current_commit and startup.get("running_commit_hash") != current_commit)

    selected_detail = None
    if selected:
        selected_detail = {
            "job": {k: v for k, v in selected.items() if not k.startswith("_")},
            "job_artifact": selected.get("_artifact"),
            "chunk_artifacts": _chunk_artifacts(selected["job_id"]),
            "transcript_artifacts": _transcript_artifacts(selected["job_id"]),
        }

    return {
        "generated_at": _now(),
        "hermes_first_consult": consult,
        "current_running_commit": current_commit,
        "startup_health": startup,
        "restart_version_mismatch": restart_mismatch,
        "known_fix_commits": commits,
        "openclaw_gate": gate,
        "jobs_total": len(jobs),
        "selected_job_id": selected.get("job_id") if selected else None,
        "selected_classification": selected_classification,
        "job_classifications": classifications,
        "selected_detail": selected_detail,
        "backend_log_evidence": logs,
        "provider_truth": {
            "chunk_0_success_seen": chunk0_success,
            "conclusion": "provider path has current success evidence" if chunk0_success else "no successful provider call found in current artifacts",
        },
        "max_decision": _max_decision(selected_classification, gate),
    }


def _max_decision(classification: dict[str, Any] | None, gate: dict[str, Any]) -> dict[str, Any]:
    if not classification:
        return {"action": "inspect_only", "reason": "no TranscriptForge job selected"}
    if classification["classification"] == "intended_pause_behavior":
        return {
            "action": "do_not_repair",
            "reason": "job is paused by design after first chunk; use review/continue controls",
            "founder_recommendation": "Review chunk 1, then continue remaining chunks only when ready.",
        }
    if classification["classification"] == "old_dead_job":
        return {
            "action": "do_not_resume_dead_job",
            "reason": "job was created before the validated fixes and should not contaminate post-fix diagnosis",
            "founder_recommendation": "Use a fresh post-fix job for proof; do not resume the dead job.",
        }
    if not gate.get("allowed"):
        return {
            "action": "repair_blocked",
            "reason": f"OpenClaw gate {gate.get('state')}: {gate.get('reason')}",
            "founder_recommendation": "Do not queue repair until OpenClaw health, queue, and worker heartbeat are healthy.",
        }
    return {
        "action": "repair_task_safe_to_queue",
        "reason": "classification is not intentional pause and OpenClaw gate is healthy",
        "founder_recommendation": "Queue one bounded repair task if current runtime checks confirm the bug.",
    }


def queue_bounded_transcriptforge_repair(job_id: str, description: str | None = None) -> dict[str, Any]:
    diagnosis = build_transcriptforge_incident_diagnosis(job_id=job_id, include_logs=True)
    gate = diagnosis["openclaw_gate"]
    classification = (diagnosis.get("selected_classification") or {}).get("classification")
    if classification in {"intended_pause_behavior", "old_dead_job", "completed"}:
        return {
            "queued": False,
            "reason": f"repair_not_applicable_for_{classification}",
            "openclaw_gate": gate,
            "diagnosis": diagnosis,
        }
    if not gate.get("allowed"):
        record_incident_learning(
            subject=f"TranscriptForge repair not queued for {job_id}",
            status="PENDING",
            learning_type="repair_blocked",
            evidence={"openclaw_gate": gate, "job_id": job_id},
            fix_summary="No repair queued because OpenClaw gate was not healthy.",
        )
        return {"queued": False, "reason": "openclaw_gate_not_healthy", "openclaw_gate": gate}

    with get_db() as db:
        cursor = db.execute(
            """INSERT INTO openclaw_tasks
               (title, description, desk, priority, source, assigned_to, max_retries)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                f"TranscriptForge bounded repair: {job_id}",
                description or "Inspect one TranscriptForge job, repair only the classified blocker, and verify with a fresh first-chunk smoke.",
                "reliability",
                3,
                "transcriptforge_incident_response",
                "openclaw",
                1,
            ),
        )
        task_id = cursor.lastrowid
    return {"queued": True, "task_id": task_id, "openclaw_gate": gate, "diagnosis": diagnosis}


def ensure_pending_transcriptforge_skill() -> dict[str, Any]:
    PENDING_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    path = PENDING_SKILLS_DIR / "transcriptforge-stuck-job-triage.json"
    payload = {
        "skill": "transcriptforge-stuck-job-triage",
        "status": "PENDING",
        "created_or_updated_at": _now(),
        "purpose": "Timeline-aware triage for TranscriptForge jobs that appear stuck, stale, paused, or dead.",
        "promotion_rule": "Promote to ACTIVE only after one verified fresh incident application, explicit MAX/founder approval, and a promotion log with commit hash and date.",
        "required_order": [
            "Hermes first-consult",
            "timeline reconstruction",
            "current runtime and OpenClaw gate check",
            "bounded repair decision",
            "fresh verification run",
            "Hermes memory write",
        ],
        "secret_policy": "Never store API keys, tokens, passwords, or provider secrets.",
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return {"path": str(path), **payload}


def record_incident_learning(
    *,
    subject: str,
    status: str,
    learning_type: str,
    evidence: dict[str, Any],
    fix_summary: str,
    commit_hash: str | None = None,
) -> dict[str, Any]:
    skill = ensure_pending_transcriptforge_skill()
    content = json.dumps(
        {
            "status": status,
            "learning_type": learning_type,
            "recorded_at": _now(),
            "commit_hash": commit_hash or _current_commit(),
            "evidence": evidence,
            "fix_summary": fix_summary,
            "skill_status": "PENDING",
        },
        indent=2,
        sort_keys=True,
        default=str,
    )
    memory_id = MemoryStore().add_memory(
        category="incident_response",
        subcategory="transcriptforge",
        subject=subject,
        content=content,
        importance=8,
        source="transcriptforge_incident_response",
        tags=["transcriptforge", "incident", status, learning_type, "PENDING"],
    )
    return {"memory_id": memory_id, "pending_skill": skill}
