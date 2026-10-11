"""H3 video drafts, Rafael's approval gate, and one-clip generation.

Drafts go to an approval queue. Nothing is posted. Social keys are never
read. Every clip is labeled AI-generated. Generation runs only after an
explicit founder confirmation header and only through the shared meter.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

from app.services.minimax_meter import (
    bilingual,
    h3_enabled,
    h3_model,
    meter_dir,
    record,
    redact,
)
from app.services.minimax_prompts import PromptRejected, sanitize_prompt
from app.services.minimax_quota import fetch_credits, fetch_remains, redact_secret

logger = logging.getLogger("max.minimax_video")

CONFIRM_HEADER = "x-minimax-video-confirm"
CONFIRM_VALUE = "aprobar"
AI_LABEL_ES = "Generado por IA — MiniMax H3. Borrador. No publicado."
AI_LABEL_EN = "AI-generated — MiniMax H3. Draft. Not posted."


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso() -> str:
    return _now().strftime("%Y-%m-%dT%H:%M:%SZ")


def queue_dir() -> Path:
    path = meter_dir() / "video_queue"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _path(approval_id: str) -> Path:
    safe = re_id(approval_id)
    return queue_dir() / f"{safe}.json"


def re_id(approval_id: str) -> str:
    raw = (approval_id or "").strip()
    if not raw or any(ch in raw for ch in "/\\.."):
        raise ValueError("invalid approval id")
    return "".join(ch for ch in raw if ch.isalnum() or ch in "-_")[:40]


def _read(approval_id: str) -> dict[str, Any]:
    path = _path(approval_id)
    if not path.is_file():
        raise FileNotFoundError(approval_id)
    return json.loads(path.read_text(encoding="utf-8"))


def _write(row: dict[str, Any]) -> dict[str, Any]:
    path = _path(row["id"])
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    return row


def list_queue(*, status: Optional[str] = None) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(queue_dir().glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if status and row.get("status") != status:
            continue
        rows.append(row)
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return rows


def create_draft(
    prompt: str,
    *,
    edition: Optional[str] = None,
    duration: int = 5,
) -> dict[str, Any]:
    from app.edition import edition_name

    ed = edition or edition_name()
    cleaned = sanitize_prompt(prompt, edition=ed, max_len=1000)
    row = {
        "id": uuid.uuid4().hex[:16],
        "status": "draft",
        "edition": ed,
        "prompt": cleaned,
        "duration": max(1, min(int(duration or 5), 10)),
        "model": h3_model(),
        "label_es": AI_LABEL_ES,
        "label_en": AI_LABEL_EN,
        "ai_generated": True,
        "posted": False,
        "social_keys_used": False,
        "created_at": _iso(),
        "approved_at": None,
        "generated_at": None,
        "result": None,
    }
    return _write(row)


def approval_is_live(approval_id: str) -> bool:
    try:
        row = _read(approval_id)
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return False
    return row.get("status") == "approved" and not row.get("generated_at")


def explicit_yes(request, body_flag: bool = False) -> bool:
    """Only the founder UI confirm header counts. LLM / tool flags do not."""
    header = ""
    if request is not None:
        header = (request.headers.get(CONFIRM_HEADER) or "").strip().lower()
    if header == CONFIRM_VALUE:
        return True
    return False


def approve(approval_id: str, *, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise PermissionError(
            bilingual(
                "Rafael debe pulsar Aprobar (cabecera X-Minimax-Video-Confirm: aprobar).",
                "Rafael must click Approve (header X-Minimax-Video-Confirm: aprobar).",
            )
        )
    row = _read(approval_id)
    if row.get("status") not in {"draft", "approved"}:
        raise ValueError(f"cannot approve status={row.get('status')}")
    row["status"] = "approved"
    row["approved_at"] = _iso()
    return _write(row)


def reject(approval_id: str, *, confirmed: bool) -> dict[str, Any]:
    if not confirmed:
        raise PermissionError("explicit reject required")
    row = _read(approval_id)
    row["status"] = "rejected"
    row["rejected_at"] = _iso()
    return _write(row)


def _api_base() -> str:
    return (os.getenv("MINIMAX_BASE_URL") or "https://api.minimax.io/v1").rstrip("/")


def _api_key() -> str:
    return (os.getenv("MINIMAX_API_KEY") or "").strip()


async def generate_approved_clip(approval_id: str) -> dict[str, Any]:
    """Spend one weekly clip. Caller must have already passed meter.enforce."""
    from app.services.minimax_meter import enforce

    row = _read(approval_id)
    if row.get("status") != "approved":
        raise PermissionError("clip is not approved")
    if row.get("generated_at"):
        return row
    if not h3_enabled():
        raise PermissionError("H3 disabled")
    refusal = enforce(kind="video", edition=row.get("edition"), approval_id=approval_id, video_clips=1)
    if refusal:
        record(
            kind="video",
            edition=row.get("edition"),
            model=row.get("model") or h3_model(),
            video_clips=0,
            blocked=True,
            reason=refusal,
            approval_id=approval_id,
        )
        raise PermissionError(refusal)
    key = _api_key()
    if not key:
        raise RuntimeError("MINIMAX_API_KEY not set")
    model = row.get("model") or h3_model()
    prompt = f"{row.get('prompt')}\n\n[{AI_LABEL_EN} / {AI_LABEL_ES}]"
    payload = {
        "model": model,
        "prompt": prompt[:1200],
        "duration": row.get("duration") or 5,
    }
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{_api_base()}/video_generation",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
            body = {}
            try:
                body = resp.json()
            except Exception:
                body = {"raw": redact_secret(resp.text[:200])}
    except Exception as exc:
        raise RuntimeError(redact_secret(f"{type(exc).__name__}")) from None
    if resp.status_code != 200:
        raise RuntimeError(redact_secret(f"MiniMax HTTP {resp.status_code}"))
    row["status"] = "generated"
    row["generated_at"] = _iso()
    row["result"] = {
        "task_id": body.get("task_id") or body.get("id") or (body.get("data") or {}).get("task_id"),
        "ai_generated": True,
        "posted": False,
        "label_es": AI_LABEL_ES,
        "label_en": AI_LABEL_EN,
    }
    _write(row)
    record(
        kind="video",
        edition=row.get("edition"),
        model=model,
        video_clips=1,
        approval_id=approval_id,
    )
    return row


def snapshot_quota() -> dict[str, Any]:
    remains = fetch_remains(force=True)
    credits = fetch_credits(force=True)
    return {
        "at": _iso(),
        "plan_remaining_pct": remains.get("remaining_pct"),
        "plan_used_pct": remains.get("used_pct"),
        "plan_available": remains.get("available"),
        "credit_balance": credits.get("balance"),
        "credits_available": credits.get("available"),
    }


def compare_snapshots(before: dict, after: dict) -> dict[str, Any]:
    def _delta(a, b):
        if a is None or b is None:
            return None
        try:
            return round(float(b) - float(a), 4)
        except (TypeError, ValueError):
            return None

    plan_delta = _delta(before.get("plan_remaining_pct"), after.get("plan_remaining_pct"))
    credit_delta = _delta(before.get("credit_balance"), after.get("credit_balance"))
    plan_moved = plan_delta is not None and abs(plan_delta) > 0.01
    credit_moved = credit_delta is not None and abs(credit_delta) > 0.01
    if plan_moved and not credit_moved:
        verdict = "plan_quota"
    elif credit_moved and not plan_moved:
        verdict = "credit_balance"
    elif plan_moved and credit_moved:
        verdict = "both"
    elif before.get("plan_available") is False and after.get("plan_available") is False:
        verdict = "unknown_no_remains"
    else:
        verdict = "no_visible_change"
    return {
        "verdict": verdict,
        "plan_remaining_delta": plan_delta,
        "credit_balance_delta": credit_delta,
        "h3_on_subscription": verdict == "plan_quota",
        "notes": {
            "plan_quota": "Plan remaining moved; this clip likely used subscription quota.",
            "credit_balance": "Credit balance moved; H3 may not be covered by the M Plan key.",
            "both": "Both plan remaining and credits moved.",
            "no_visible_change": "Neither bar moved enough to tell (docs conflict; do not assume).",
            "unknown_no_remains": "Remains endpoint was not available.",
        }.get(verdict),
    }


def probe_live_allowed() -> bool:
    return (os.getenv("MINIMAX_H3_PROBE_LIVE") or "").strip() in {"1", "true", "yes"}
