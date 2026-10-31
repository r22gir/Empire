"""Shared Max answer for 'where is this job?' — used by chat and stream."""
from __future__ import annotations

import re
from typing import Any

from app.db.database import get_db
from app.services.job_stages.backfill import backfill_job_stages
from app.services.job_stages.gate import extract_job_query
from app.services.job_stages.schema import init_job_stages_schema
from app.services.job_stages.service import (
    find_job,
    format_location_answer,
    job_location,
)

# Tight: only explicit job-location questions. Do not match "what's the
# current stage", bare "job status", or action requests that mention a job.
_WHERE_JOB = re.compile(
    r"^\s*(?:hey\s+max[,:]?\s+)?"
    r"(?:"
    r"where\s+is\s+(?:this\s+|the\s+)?job(?:\s+(?:called\s+|named\s+|—\s*|-\s*)?.{1,60})?"
    r"|where\s+is\s+(?:the\s+)?(?P<named>[A-Za-z][\w '.&-]{1,40})\s+job"
    r"|where\s+is\s+job\s+(?P<id>JOB-\d{4}-\d+|[A-Za-z0-9-]{4,})"
    r"|where\s+are\s+we\s+(?:on|with)\s+(?:this\s+|the\s+)?job(?:\s+.{0,40})?"
    r"|what(?:'s| is)\s+missing\s+(?:on|for|with)\s+(?:this\s+|the\s+)?job(?:\s+.{0,40})?"
    r")"
    r"[\s?!.]*$",
    re.I,
)

_OTHER_WORK = re.compile(
    r"\b(draw|drawing|email|send|invoice|create|generate|yardage|"
    r"approve quote|render|sketch|fabric|install)\b",
    re.I,
)


def wants_job_location(message: str | None) -> bool:
    text = (message or "").strip()
    if not text or len(text) > 160:
        return False
    if _OTHER_WORK.search(text):
        return False
    return bool(_WHERE_JOB.match(text))


def locate_job(query: str | None = None, job_id: str | None = None) -> dict[str, Any]:
    with get_db() as conn:
        init_job_stages_schema(conn)
        job = None
        if job_id:
            job = find_job(conn, job_id)
        if job is None and query:
            job = find_job(conn, query)
        if job is None:
            return {
                "found": False,
                "answer": (
                    "I need a job name, job number, or job id to answer "
                    "'where is this job?' Nothing was sent."
                ),
            }
        backfill_job_stages(conn, job["id"])
        location = job_location(conn, job["id"])
    location["found"] = True
    location["answer"] = format_location_answer(location)
    return location


def answer_where_is_this_job(message: str | None, job_id: str | None = None) -> dict[str, Any]:
    query = job_id or extract_job_query(message)
    return locate_job(query=query, job_id=job_id)
