"""
TranscriptForge Hermes Support Layer.
Bounded beneath MAX — NOT a replacement for MAX's authority.

Hermes SHOULD help with (PENDING skills):
  - transcriptforge-intake
  - transcriptforge-qc-review
  - transcriptforge-critical-field-check

Hermes SHOULD NOT:
  - invent transcript content
  - approve transcripts
  - override MAX runtime truth
  - act as if a tool result exists when it does not

MAX remains the authority on job state, approval boundaries, and runtime truth.
"""

from pathlib import Path
import json, logging, uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("hermes.transcriptforge")


# ── TranscriptForge Workflow Skill Specs ─────────────────────────────

TRANSCRIPTFORGE_WORKFLOWS: dict[str, dict[str, Any]] = {
    "transcriptforge-intake": {
        "label": "TranscriptForge intake preparation",
        "aliases": ("transcript intake", "new transcription job", "transcribe audio", "transcription job"),
        "required_fields": ("source_mode", "uploader"),
        "target_route": "/api/v1/transcriptforge/jobs",
        "field_order": ("source_mode", "uploader", "notes"),
        "outcome": "job_created",
        "max_authority": True,
        "notes": "Hermes prepares draft metadata. MAX creates actual job via API.",
    },
    "transcriptforge-qc-review": {
        "label": "TranscriptForge QA review prep",
        "aliases": ("review transcript", "transcript QA", "check transcript quality", "transcript flags"),
        "required_fields": ("job_id", "chunk_id"),
        "target_route": "/api/v1/transcriptforge/jobs/{job_id}/chunks/{chunk_id}/review",
        "field_order": ("job_id", "chunk_id", "review_status", "reviewer"),
        "outcome": "chunk_reviewed",
        "max_authority": True,
        "notes": "Hermes prepares review checklist from correction patterns. MAX routes review action.",
    },
    "transcriptforge-critical-field-check": {
        "label": "TranscriptForge critical field extraction prep",
        "aliases": ("extract legal fields", "transcript fields", "critical fields", "names and dates"),
        "required_fields": ("job_id",),
        "target_route": "/api/v1/transcriptforge/jobs/{job_id}/approve",
        "field_order": ("job_id",),
        "outcome": "fields_extracted",
        "max_authority": True,
        "notes": "Hermes identifies potential critical fields for human review. Cannot approve — only MAX approves.",
    },
}


# ── Pending Skills Registry ──────────────────────────────────────────

PENDING_SKILLS = {
    "transcriptforge-intake": {
        "status": "PENDING",
        "promotion_conditions": (
            "100+ successful job creations without regression",
            "founder approval after 30-day observation period",
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "description": "Prepare TranscriptForge job metadata before MAX creates job via API",
    },
    "transcriptforge-qc-review": {
        "status": "PENDING",
        "promotion_conditions": (
            "100+ successful chunk reviews without quality issues",
            "correction pattern accuracy > 95%",
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "description": "Generate QA review checklists from prior correction patterns",
    },
    "transcriptforge-critical-field-check": {
        "status": "PENDING",
        "promotion_conditions": (
            "50+ successful field extractions without missing critical legal content",
            "founder approval",
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "description": "Identify potential critical fields (names, dates, amounts) from transcript text for human review",
    },
}


# ── Transcript Correction Pattern Memory ─────────────────────────────

def correction_patterns_root() -> Path:
    from app.services.max.hermes_memory import memory_root
    return memory_root() / "TRANSCRIPTFORGE" / "correction_patterns"


def ensure_transcriptforge_scaffold() -> dict[str, Any]:
    root = Path(__file__).parent.parent / "max" / "brain" / "TRANSCRIPTFORGE"
    root.mkdir(parents=True, exist_ok=True)
    (root / "correction_patterns").mkdir(exist_ok=True)
    (root / "reviews").mkdir(exist_ok=True)
    return {
        "root": str(root),
        "correction_patterns": str(root / "correction_patterns"),
        "reviews": str(root / "reviews"),
    }


def record_correction_pattern(
    job_id: str,
    chunk_id: str,
    original_text: str,
    corrected_text: str,
    correction_type: str,  # e.g., "name", "date", "legal_phrase", "spelling"
    reviewer: str,
) -> None:
    """Record a correction pattern for Hermes learning."""
    root = Path(__file__).parent.parent / "max" / "brain" / "TRANSCRIPTFORGE" / "correction_patterns"
    root.mkdir(parents=True, exist_ok=True)

    record = {
        "id": f"cp_{uuid.uuid4().hex[:12]}",
        "job_id": job_id,
        "chunk_id": chunk_id,
        "original": original_text,
        "corrected": corrected_text,
        "type": correction_type,
        "reviewer": reviewer,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    fname = root / f"{record['id']}.json"
    fname.write_text(json.dumps(record, indent=2, default=str))
    logger.info(f"Recorded correction pattern: {record['id']} ({correction_type})")


def get_correction_patterns_by_type(correction_type: str) -> list[dict[str, Any]]:
    """Retrieve correction patterns of a given type for Hermes review."""
    root = Path(__file__).parent.parent / "max" / "brain" / "TRANSCRIPTFORGE" / "correction_patterns"
    if not root.exists():
        return []

    patterns = []
    for f in root.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            if data.get("type") == correction_type:
                patterns.append(data)
        except Exception:
            continue

    return patterns


# ── MAX Integration Hooks ───────────────────────────────────────────

def transcriptforge_max_context_addition() -> str:
    """
    Called by MAX when building its system prompt / brain context.
    Returns the TranscriptForge awareness text for MAX.
    """
    return """
## TranscriptForge
- Route: /api/v1/transcriptforge
- States: uploaded → chunking → first_chunk_processing → first_chunk_ready →
  processing_remaining_chunks → verification_running → needs_review →
  approved / corrected_and_approved / rejected
- NEVER auto-approve. NEVER claim a transcript is approved without real approval action.
- NEVER fabricate transcript content — use actual API results.
- Approval requires: no unresolved critical-field flags, no unreviewed low-confidence chunks.
- corrected_and_approved is visibly distinct from approved.
- Web Chat mode is future-ready (labeled accordingly).
- Hermes role is bounded: prepares drafts, generates checklists, identifies patterns.
  MAX retains authority over state, approval, and runtime truth.
""".strip()


def transcriptforge_job_summary_for_max(job_id: str) -> str:
    """Build a MAX-readable summary of a TranscriptForge job."""
    try:
        from app.routers.transcriptforge import _load_job
        job = _load_job(job_id)
    except Exception:
        return f"TranscriptForge job {job_id}: not found or not accessible."

    state = job.get("state", "unknown")
    chunks_total = job.get("chunks_total", 0)
    chunks_complete = job.get("chunks_complete", 0)
    chunks_failed = job.get("chunks_failed", 0)
    flags = job.get("critical_field_flags", [])
    qc = job.get("qc_summary", {})

    summary_parts = [
        f"Job {job_id} — state: {state}",
        f"Progress: {chunks_complete}/{chunks_total} chunks, {chunks_failed} failed",
        f"Mode: {job.get('source_mode', 'unknown')}",
        f"Overall confidence: {job.get('overall_confidence', 'N/A')}",
    ]

    if flags:
        summary_parts.append(f"CRITICAL FLAGS ({len(flags)}): {', '.join(flags[:3])}")

    if qc:
        low_conf = qc.get("low_confidence_segments", 0)
        if low_conf > 0:
            summary_parts.append(f"Low-confidence segments: {low_conf}")

    if state in ["approved", "corrected_and_approved"]:
        summary_parts.append("STATUS: APPROVED — Human reviewed")
    elif state == "rejected":
        summary_parts.append("STATUS: REJECTED")
    elif state == "needs_review":
        summary_parts.append("STATUS: NEEDS REVIEW — Approval gate not passed")
    elif state in ["first_chunk_ready", "verification_running"]:
        summary_parts.append("STATUS: IN REVIEW — Do not claim approved")

    return "\n".join(summary_parts)