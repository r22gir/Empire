"""MiniMax-M2 planner for approved improvements (included plan path only).

Hard daily call/token cap. Gift credits are never treated as room.
Family editions (Max-e / Maxine) are refused here; their 20% text share
is also enforced through the shared MiniMax meter if this is ever called
under a family process.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.services.leadforge import growth
from app.services.max import improvements as imp

PLANNER_MODEL_DEFAULT = "MiniMax-M2"
DEFAULT_DAILY_CALLS = 40
DEFAULT_DAILY_TOKENS = 200_000
DEFAULT_RESERVE_IN = 4_000
DEFAULT_RESERVE_OUT = 4_000


class BudgetExceeded(RuntimeError):
    """Daily planner cap or family/plan meter blocked the call."""

    def __init__(self, message: str, *, code: str = "budget"):
        super().__init__(message)
        self.message = message
        self.code = code


class PlannerUnavailable(RuntimeError):
    """MiniMax key missing or the included-plan call failed."""


def _int_env(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def planner_model() -> str:
    return (os.getenv("MAX_IMPROVE_MINIMAX_MODEL") or PLANNER_MODEL_DEFAULT).strip() or PLANNER_MODEL_DEFAULT


def daily_call_cap() -> int:
    return _int_env("MAX_IMPROVE_MINIMAX_DAILY_CALLS", DEFAULT_DAILY_CALLS)


def daily_token_cap() -> int:
    return _int_env("MAX_IMPROVE_MINIMAX_DAILY_TOKENS", DEFAULT_DAILY_TOKENS)


def minimax_configured() -> bool:
    key = (os.getenv("MINIMAX_API_KEY") or "").strip()
    if not key:
        return False
    if key.startswith("test") or key in {"mm", "fake", "dummy", "test-mm-key", "test-minimax-key"}:
        return os.getenv("MAX_IMPROVE_ALLOW_TEST_KEY") == "1"
    return True


def _utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def ensure_usage(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS max_improvement_minimax_usage (
            day TEXT PRIMARY KEY,
            calls INTEGER NOT NULL DEFAULT 0,
            tokens INTEGER NOT NULL DEFAULT 0,
            blocked_calls INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            updated_at TEXT
        )"""
    )


def usage_snapshot(day: Optional[str] = None) -> dict:
    day = day or _utc_day()
    with growth._db() as conn:
        ensure_usage(conn)
        row = conn.execute(
            "SELECT * FROM max_improvement_minimax_usage WHERE day=?", (day,)
        ).fetchone()
    calls = int(row["calls"]) if row else 0
    tokens = int(row["tokens"]) if row else 0
    call_cap = daily_call_cap()
    token_cap = daily_token_cap()
    stopped = calls >= call_cap or tokens >= token_cap
    return {
        "day": day,
        "calls": calls,
        "tokens": tokens,
        "call_cap": call_cap,
        "token_cap": token_cap,
        "calls_left": max(0, call_cap - calls),
        "tokens_left": max(0, token_cap - tokens),
        "stopped": stopped,
        "auto_credits": False,
        "model": planner_model(),
        "family_text_share_pct": 20.0,
        "note": (
            "Hard daily cap. Stops at the cap. Gift credits are never spent. "
            "Max-e / Maxine stay on their 20% text share (INSTANCE_USAGE_CAP_PCT)."
        ),
        "last_error": (row["last_error"] if row else None),
    }


def _record_usage(*, calls: int = 0, tokens: int = 0, blocked: bool = False, error: str = "") -> dict:
    day = _utc_day()
    with growth._db() as conn:
        ensure_usage(conn)
        conn.execute(
            """INSERT INTO max_improvement_minimax_usage (day, calls, tokens, blocked_calls, last_error, updated_at)
               VALUES (?, 0, 0, 0, NULL, ?)
               ON CONFLICT(day) DO NOTHING""",
            (day, datetime.now().isoformat(timespec="seconds")),
        )
        conn.execute(
            """UPDATE max_improvement_minimax_usage
               SET calls = calls + ?,
                   tokens = tokens + ?,
                   blocked_calls = blocked_calls + ?,
                   last_error = COALESCE(?, last_error),
                   updated_at = ?
               WHERE day=?""",
            (
                max(0, calls),
                max(0, tokens),
                1 if blocked else 0,
                (error or None),
                datetime.now().isoformat(timespec="seconds"),
                day,
            ),
        )
    return usage_snapshot(day)


def assert_budget() -> dict:
    snap = usage_snapshot()
    if snap["stopped"]:
        raise BudgetExceeded(
            f"MiniMax planner cap reached ({snap['calls']}/{snap['call_cap']} calls, "
            f"{snap['tokens']}/{snap['token_cap']} tokens UTC {snap['day']}). "
            "No auto-credits. Retry tomorrow or raise MAX_IMPROVE_MINIMAX_DAILY_CALLS / "
            "MAX_IMPROVE_MINIMAX_DAILY_TOKENS.",
            code="daily_cap",
        )
    return snap


def _family_blocked() -> Optional[str]:
    try:
        from app.edition import is_family_edition

        if is_family_edition():
            return (
                "Improvement planner is founder-Max only. Family editions (Max-e / Maxine) "
                "keep their 20% MiniMax text share and do not run this loop."
            )
    except Exception:
        pass
    return None


def _reserve_meter(model: str):
    from app.services.minimax_meter import MeterBlocked, reserve

    try:
        reservation = reserve(
            kind="text",
            model=model,
            input_tokens=DEFAULT_RESERVE_IN,
            output_tokens=DEFAULT_RESERVE_OUT,
        )
    except MeterBlocked as exc:
        raise BudgetExceeded(exc.message, code="meter") from exc
    if reservation.blocked:
        raise BudgetExceeded(reservation.message or "MiniMax meter blocked this call", code="meter")
    return reservation


def _reconcile_meter(reservation, *, input_tokens: int, output_tokens: int, error: str = "") -> None:
    if reservation is None:
        return
    try:
        from app.services.minimax_meter import reconcile

        reconcile(
            reservation,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            error=error,
        )
    except Exception:
        pass


def _parse_usage(payload: dict) -> tuple[int, int]:
    usage = payload.get("usage") if isinstance(payload, dict) else None
    if not isinstance(usage, dict):
        return 0, 0
    inp = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
    out = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
    return max(0, inp), max(0, out)


def _extract_content(payload: dict) -> str:
    try:
        return str(payload["choices"][0]["message"]["content"] or "")
    except Exception:
        return ""


def call_minimax(system: str, user: str) -> dict:
    """One included-plan MiniMax-M2 call. Raises BudgetExceeded / PlannerUnavailable."""
    family = _family_blocked()
    if family:
        _record_usage(blocked=True, error=family)
        raise BudgetExceeded(family, code="family")
    assert_budget()
    key = (os.getenv("MINIMAX_API_KEY") or "").strip()
    if not key:
        raise PlannerUnavailable("MINIMAX_API_KEY is not set")
    model = planner_model()
    base = (os.getenv("MINIMAX_BASE_URL") or "https://api.minimax.io/v1").rstrip("/")
    reservation = _reserve_meter(model)
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": min(8192, DEFAULT_RESERVE_OUT),
        "temperature": 0.2,
    }
    try:
        with httpx.Client(timeout=90) as client:
            resp = client.post(
                f"{base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
    except Exception as exc:
        _reconcile_meter(reservation, input_tokens=0, output_tokens=0, error=str(exc))
        _record_usage(blocked=True, error=str(exc)[:200])
        raise PlannerUnavailable(f"MiniMax request failed: {type(exc).__name__}") from None

    payload: dict[str, Any] = {}
    try:
        parsed = resp.json()
        if isinstance(parsed, dict):
            payload = parsed
    except Exception:
        payload = {}
    inp, out = _parse_usage(payload)
    tokens = inp + out
    if resp.status_code >= 400:
        err = f"MiniMax HTTP {resp.status_code}: {(resp.text or '')[:240]}"
        _reconcile_meter(reservation, input_tokens=inp, output_tokens=out, error=err)
        _record_usage(calls=1, tokens=tokens or 1, blocked=True, error=err)
        raise PlannerUnavailable(err)
    text = _extract_content(payload)
    _reconcile_meter(reservation, input_tokens=inp or DEFAULT_RESERVE_IN, output_tokens=out)
    _record_usage(calls=1, tokens=tokens or 1)
    return {
        "text": text,
        "model": model,
        "input_tokens": inp,
        "output_tokens": out,
        "tokens": tokens,
        "auto_credits": False,
    }


_SYSTEM = """You are Atlas on the CodeForge desk for EmpireBox (github.com/r22gir/Empire).
Write a concrete implementation plan and a proposed patch/spec. Do not merge. Do not deploy.
Never mention or invent secrets, .env values, client_aliases.json, or business.json.
Never send email, SMS, WhatsApp, or social posts.
Output Markdown with these headings exactly:
## Plan
## Proposed patch / spec
## Files to touch
## Tests
## Rollback
Keep it implementable by a Cursor cloud agent (grok-4.6) as a draft PR on a new branch.
"""


def plan_prompt(req: dict) -> str:
    return (
        f"{imp.build_prompt(req)}\n\n"
        "Write the plan and proposed patch/spec against this repo. "
        "Be specific about FastAPI (backend/app) and Next.js (empire-command-center). "
        "Do not merge. Do not deploy. Do not edit max/memory.md."
    )


def _strip_fences(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"^```(?:markdown|md)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    return t.strip()


def plan_improvement(req: dict) -> dict:
    """Call MiniMax-M2 and return plan + spec body. No GitHub, no merge."""
    raw = call_minimax(_SYSTEM, plan_prompt(req))
    body = _strip_fences(raw["text"])
    if not body:
        raise PlannerUnavailable("MiniMax returned an empty plan")
    spec = (
        f"{imp.build_prompt(req)}\n\n---\n"
        f"# Atlas / MiniMax plan ({raw['model']})\n\n{body}\n"
    )
    return {
        "plan": body,
        "spec": spec,
        "model": raw["model"],
        "input_tokens": raw["input_tokens"],
        "output_tokens": raw["output_tokens"],
        "tokens": raw["tokens"],
        "used_llm": True,
    }


def template_plan(req: dict) -> dict:
    """Honest fallback when MiniMax is not configured. Not billed as an LLM call."""
    spec = imp.build_prompt(req)
    plan = (
        "## Plan\n"
        "MiniMax is not configured on this box. This is the house-rules spec only.\n\n"
        "## Proposed patch / spec\n"
        f"{req.get('proposed_change') or ''}\n\n"
        "## Files to touch\n"
        f"{', '.join(req.get('affected_modules') or []) or '(see proposed change)'}\n\n"
        "## Tests\nAdd or update tests for the new behaviour. Existing suites must pass.\n\n"
        "## Rollback\nRevert the draft PR. Do not merge. Do not deploy.\n"
    )
    return {
        "plan": plan,
        "spec": spec + "\n\n---\n# Template spec (MiniMax not configured)\n\n" + plan,
        "model": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "tokens": 0,
        "used_llm": False,
    }
