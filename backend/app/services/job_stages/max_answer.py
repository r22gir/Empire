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

_WHERE_JOB = re.compile(
    r"\bwhere\s+is\s+(this\s+)?(the\s+)?job\b"
    r"|\bwhat'?s\s+(the\s+)?(current\s+)?stage\b"
    r"|\bjob\s+(status|stage|checklist|progress)\b"
    r"|\bwhere\s+are\s+we\s+(on|with)\s+(this\s+)?(the\s+)?job\b"
    r"|\bwhat'?s\s+missing\s+(on|for|with)?\s*(this\s+)?(the\s+)?job\b",
    re.I,
)


def wants_job_location(message: str | None) -> bool:
    return bool(_WHERE_JOB.search(message or ""))


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
