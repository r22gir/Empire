"""Atlas / CodeForge worker: plan an approved improvement, file a GitHub issue.

Never merges. Never deploys. Never sends email / WhatsApp / SMS.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

from app.services.leadforge import growth
from app.services.max import improvement_queue as queue
from app.services.max import improvements as imp
from app.services.max.improvement_github import (
    GitHubUnavailable,
    github_configured,
    open_improvement_issue,
)
from app.services.max.improvement_planner import (
    BudgetExceeded,
    PlannerUnavailable,
    minimax_configured,
    plan_improvement,
    template_plan,
)
from app.services.max.studio_frozen_gate import evaluate_studio_frozen_gate

logger = logging.getLogger("max.improvements.worker")

DESK_ID = "codeforge"
AGENT = "Atlas"


def _family_blocked() -> Optional[str]:
    try:
        from app.edition import is_family_edition

        if is_family_edition():
            return "Improvement worker does not run on family editions (amp / maxine)."
    except Exception:
        return None
    return None


def _set_status(req_id: int, **upd) -> None:
    if not upd:
        return
    with growth._db() as conn:
        imp._ensure(conn)
        conn.execute(
            f"UPDATE max_improvements SET {', '.join(k + '=?' for k in upd)} WHERE id=?",
            (*upd.values(), req_id),
        )


def _maybe_launch_cursor(req: dict, spec: str) -> dict:
    """Optional grok-4.6 draft-PR agent. Never merges. Skipped without CURSOR_API_KEY."""
    if not imp.cursor_configured():
        return {}
    try:
        launched = imp._launch_cursor_agent({**req, "_prompt_override": spec})
        return {
            "agent_id": launched.get("agent_id"),
            "run_id": launched.get("run_id"),
            "agent_url": launched.get("agent_url"),
            "model": launched.get("model") or "grok-4.6",
        }
    except Exception as exc:
        return {"cursor_error": str(exc)[:400]}


def worker_enabled() -> bool:
    return (os.getenv("MAX_IMPROVE_WORKER_ENABLED") or "").strip().lower() in {"1", "true", "yes", "on"}


def run_atlas_plan(job: dict) -> dict:
    """Synchronous Atlas job. Safe to call from tests and the worker loop."""
    if not worker_enabled():
        raise PermissionError("Atlas improvement worker is off (MAX_IMPROVE_WORKER_ENABLED not set).")
    from app.services.max.improve_base_ref import assert_safe_improve_base_ref, resolve_base_ref
    # Refuses main/master/amp/maxine before any GitHub issue or Cursor agent.
    assert_safe_improve_base_ref(resolve_base_ref())
    blocked = _family_blocked()
    if blocked:
        raise PermissionError(blocked)
    req_id = int(job["improvement_id"])
    req = imp.get(req_id)
    if not req:
        raise LookupError(f"improvement {req_id} not found")

    gate = evaluate_studio_frozen_gate()
    logger.info(gate["log_line"])
    if not gate["keep"]:
        _set_status(
            req_id,
            status="build_failed",
            build_note=gate["log_line"][:500],
        )
        raise RuntimeError(gate["log_line"])

    _set_status(
        req_id,
        status="planning",
        build_note=f"{AGENT} ({DESK_ID}) is writing the MiniMax plan.",
    )

    used_llm = False
    try:
        if minimax_configured():
            planned = plan_improvement(req)
            used_llm = True
        else:
            planned = template_plan(req)
    except BudgetExceeded as exc:
        _set_status(req_id, status="build_failed", build_note=exc.message[:500])
        raise
    except PlannerUnavailable as exc:
        _set_status(req_id, status="build_failed", build_note=str(exc)[:500])
        raise

    try:
        spec_path = imp.write_spec({**req, "spec_override": planned["spec"]})
    except Exception as exc:
        _set_status(req_id, status="build_failed", build_note=f"Could not write spec: {exc}"[:500])
        raise

    upd = {
        "spec_path": spec_path,
        "model": planned.get("model") or req.get("model"),
        "build_note": (
            f"{AGENT} wrote a {'MiniMax' if used_llm else 'template'} plan. "
            "Opening a GitHub issue labeled max-improvement. Nothing merges or deploys."
        ),
    }
    _set_status(req_id, **upd)

    issue: dict = {}
    if github_configured():
        try:
            issue = open_improvement_issue(req, planned["plan"])
            upd.update(
                {
                    "issue_url": issue.get("issue_url"),
                    "build_note": (
                        f"{AGENT} opened GitHub issue #{issue.get('issue_number')} "
                        f"({issue.get('issue_url')}) labeled max-improvement. "
                        "A Cursor cloud agent (grok-4.6) may open a draft PR. "
                        "Never merge. Never deploy."
                    ),
                    "status": "pr_open",
                }
            )
        except GitHubUnavailable as exc:
            upd.update(
                {
                    "status": "awaiting_build",
                    "build_note": (
                        f"Plan ready at {spec_path}. GitHub issue not opened: {exc}. "
                        "Set MAX_IMPROVE_GITHUB_TOKEN and tap Retry."
                    )[:500],
                }
            )
    else:
        upd.update(
            {
                "status": "awaiting_build",
                "build_note": (
                    f"Plan ready at {spec_path}. No GitHub token. "
                    "Set MAX_IMPROVE_GITHUB_TOKEN (or GITHUB_TOKEN) and tap Retry, "
                    "or paste the spec into a Cursor cloud agent."
                ),
            }
        )

    cursor = _maybe_launch_cursor(req, planned["spec"])
    if cursor.get("agent_id"):
        upd.update(
            {
                "agent_id": cursor["agent_id"],
                "run_id": cursor.get("run_id"),
                "agent_url": cursor.get("agent_url"),
                "model": cursor.get("model") or upd.get("model"),
            }
        )
        if upd.get("status") != "pr_open":
            upd["status"] = "planning"
            upd["build_note"] = (
                (upd.get("build_note") or "")
                + " Cursor cloud agent started (grok-4.6); it opens a draft PR on its own branch."
            )[:500]
    elif cursor.get("cursor_error"):
        upd["build_note"] = ((upd.get("build_note") or "") + f" Cursor: {cursor['cursor_error']}")[:500]

    _set_status(req_id, **{k: v for k, v in upd.items() if v is not None})
    result = {
        "improvement_id": req_id,
        "job_id": job.get("id"),
        "desk": DESK_ID,
        "agent": AGENT,
        "status": upd.get("status"),
        "spec_path": spec_path,
        "issue_url": issue.get("issue_url"),
        "issue_number": issue.get("issue_number"),
        "used_llm": used_llm,
        "merged": False,
        "deployed": False,
        "kept": True,
        "frozen_gate": gate["verdict"],
    }
    return result


def process_one(job: Optional[dict] = None) -> Optional[dict]:
    claimed = job or queue.claim_next()
    if not claimed:
        return None
    job_id = claimed["id"]
    try:
        result = run_atlas_plan(claimed)
        queue.mark_done(job_id, result)
        return result
    except Exception as exc:
        logger.warning("improvement job %s failed: %s", job_id, exc)
        queue.mark_failed(job_id, str(exc))
        req_id = claimed.get("improvement_id")
        if req_id:
            current = imp.get(int(req_id)) or {}
            if current.get("status") not in ("build_failed", "rejected"):
                _set_status(int(req_id), status="build_failed", build_note=str(exc)[:500])
        return {"job_id": job_id, "error": str(exc)[:400], "status": "failed"}


async def worker_loop(poll_seconds: Optional[float] = None) -> None:
    """Primary-worker loop. Family editions exit immediately."""
    blocked = _family_blocked()
    if blocked:
        logger.info(blocked)
        return
    # Explicit opt-in: MiniMax/Cursor keys already exist in the Studio env for
    # other features, so key presence alone must not start the loop.
    if not worker_enabled():
        logger.info("Atlas improvement worker off (set MAX_IMPROVE_WORKER_ENABLED=1 to enable)")
        return
    interval = poll_seconds
    if interval is None:
        raw = (os.getenv("MAX_IMPROVE_WORKER_POLL") or "12").strip()
        try:
            interval = max(3.0, float(raw))
        except ValueError:
            interval = 12.0
    logger.info("Atlas improvement worker polling every %ss", interval)
    while True:
        try:
            processed = await asyncio.to_thread(process_one)
            if not processed:
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("improvement worker tick: %s", exc)
            await asyncio.sleep(interval)


def process_all(limit: int = 20) -> list[dict]:
    """Drain up to ``limit`` queued jobs (tests / manual)."""
    out = []
    for _ in range(max(1, limit)):
        row = process_one()
        if not row:
            break
        out.append(row)
    return out
