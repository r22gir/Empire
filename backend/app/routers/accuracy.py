"""
MAX Accuracy Monitor — API endpoints for viewing grounding audit stats and logs.
"""
from fastapi import APIRouter, Query
from typing import Optional

from app.services.max.accuracy_monitor import accuracy_monitor

router = APIRouter(prefix="/max/accuracy", tags=["MAX Accuracy"])


@router.get("/stats")
async def get_accuracy_stats(days: int = Query(default=30, ge=1, le=365)):
    """Get accuracy statistics for the last N days."""
    return accuracy_monitor.get_stats(days=days)


@router.get("/log")
async def get_accuracy_log(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    model: Optional[str] = Query(default=None),
    passed: Optional[bool] = Query(default=None),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
):
    """Get paginated audit log with optional filters."""
    return accuracy_monitor.get_log(
        page=page,
        per_page=per_page,
        model=model,
        passed=passed,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/flagged")
async def get_flagged_responses(limit: int = Query(default=50, ge=1, le=500)):
    """Get responses that failed grounding or have low confidence."""
    return accuracy_monitor.get_flagged(limit=limit)
