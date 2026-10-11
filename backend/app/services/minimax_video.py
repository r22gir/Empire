"""H3 video drafts, Rafael's approval gate, and one-clip generation.

Family drafts live under that edition's 0700 dir. The founder video_queue
is founder-only (0700). Nothing is posted. Social keys are never read.
Every clip is labeled AI-generated.

Generation runs only from the founder router endpoint after
X-Minimax-Video-Confirm: aprobar. The LLM tool may only create drafts.

Reserve the weekly cap and set status=generating BEFORE the HTTP call.
If the API errors after it may have billed, keep the reserved cost.
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
    FAMILY_EDITIONS,
    KNOWN_EDITIONS,
    bilingual,
    current_edition,
    founder_video_queue_dir,
    h3_enabled,
    h3_model,
    normalize_edition,
    redact,
    reserve,
    reconcile,
    video_drafts_dir,
)
from app.services.minimax_prompts import sanitize_prompt
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


def _chmod(path: Path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def queue_dir() -> Path:
    """Founder-only approval queue (0700)."""
    return founder_video_queue_dir()


def re_id(approval_id: str) -> str:
    raw = (approval_id or "").strip()
    if not raw or any(ch in raw for ch in "/\\") or ".." in raw:
        raise ValueError("invalid approval id")
    return "".join(ch for ch in raw if ch.isalnum() or ch in "-_")[:40]


def _draft_dir(edition: str) -> Path:
    ed = normalize_edition(edition)
    if ed in FAMILY_EDITIONS:
        return video_drafts_dir(ed)
    return founder_video_queue_dir()


def _candidate_paths(approval_id: str) -> list[Path]:
    safe = re_id(approval_id)
    paths = [founder_video_queue_dir() / f"{safe}.json"]
    for ed in KNOWN_EDITIONS:
        paths.append(video_drafts_dir(ed) / f"{safe}.json")
    # de-dupe while keeping order
    seen: set[str] = set()
    out: list[Path] = []
    for path in paths:
        key = str(path)
        if key not in seen:
            seen.add(key)
            out.append(path)
    return out


def _path_for_new(approval_id: str, edition: str) -> Path:
    return _draft_dir(edition) / f"{re_id(approval_id)}.json"


def _locate(approval_id: str) -> Path:
    for path in _candidate_paths(approval_id):
        if path.is_file():
            return path
    raise FileNotFoundError(approval_id)


def _read(approval_id: str) -> dict[str, Any]:
    path = _locate(approval_id)
    return json.loads(path.read_text(encoding="utf-8"))


def get_draft(approval_id: str) -> dict[str, Any]:
    return _read(approval_id)


def _write_at(path: Path, row: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    _chmod(path.parent, 0o700)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    _chmod(tmp, 0o600)
    tmp.replace(path)
    _chmod(path, 0o600)
    return row


def _write(row: dict[str, Any]) -> dict[str, Any]:
    try:
        path = _locate(row["id"])
    except FileNotFoundError:
        path = _path_for_new(row["id"], row.get("edition") or current_edition())
    return _write_at(path, row)


def list_queue(*, status: Optional[str] = None) -> list[dict[str, Any]]:
    """Founder aggregator: founder queue + every edition's drafts."""
    rows = []
    seen: set[str] = set()
    paths: list[Path] = []
    paths.extend(founder_video_queue_dir().glob("*.json"))
    for ed in KNOWN_EDITIONS:
        paths.extend(video_drafts_dir(ed).glob("*.json"))
    for path in paths:
        if path.suffix != ".json" or path.name.endswith(".tmp"):
            continue
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rid = str(row.get("id") or path.stem)
        if rid in seen:
            continue
        seen.add(rid)
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

    ed = normalize_edition(edition or edition_name())
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
        "generating_at": None,
        "generated_at": None,
        "result": None,
    }
    path = _path_for_new(row["id"], ed)
    return _write_at(path, row)


def approval_is_live(approval_id: str) -> bool:
    try:
        row = _read(approval_id)
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        return False
    status = row.get("status")
    return status in {"approved", "generating"} and not row.get("generated_at")


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


def _assert_caller_edition(row: dict[str, Any], caller_edition: Optional[str]) -> str:
    caller = normalize_edition(caller_edition or current_edition())
    row_ed = normalize_edition(row.get("edition"))
    if caller in FAMILY_EDITIONS and row_ed != caller:
        raise PermissionError(
            bilingual(
                "Este borrador no pertenece a esta edición.",
                "This draft does not belong to this edition.",
            )
        )
    return caller


async def generate_approved_clip(
    approval_id: str,
    *,
    caller_edition: Optional[str] = None,
) -> dict[str, Any]:
    """Spend one weekly clip. Reserve + generating MUST happen before HTTP."""
    row = _read(approval_id)
    _assert_caller_edition(row, caller_edition)
    if row.get("generated_at") and row.get("status") == "generated":
        return row
    if row.get("status") not in {"approved", "generating"}:
        raise PermissionError("clip is not approved")
    if not h3_enabled():
        raise PermissionError("H3 disabled")
    model = (row.get("model") or h3_model() or "").strip()
    if not model:
        raise PermissionError(
            bilingual(
                "No hay MINIMAX_H3_MODEL. No usamos Hailuo-02 en silencio.",
                "MINIMAX_H3_MODEL is unset. Hailuo-02 is not a silent default.",
            )
        )

    # Mark generating first so a concurrent caller cannot start a second HTTP.
    row["status"] = "generating"
    row["generating_at"] = _iso()
    row["model"] = model
    _write(row)

    reservation = reserve(
        kind="video",
        edition=row.get("edition"),
        model=model,
        approval_id=approval_id,
        video_clips=1,
    )
    if reservation.blocked:
        row["status"] = "approved"
        row["block_reason"] = reservation.message
        _write(row)
        raise PermissionError(reservation.message)

    key = _api_key()
    if not key:
        reconcile(reservation, video_clips=0, error="MINIMAX_API_KEY not set")
        row["status"] = "approved"
        row["block_reason"] = "MINIMAX_API_KEY not set"
        _write(row)
        raise RuntimeError("MINIMAX_API_KEY not set")

    prompt = f"{row.get('prompt')}\n\n[{AI_LABEL_EN} / {AI_LABEL_ES}]"
    payload = {
        "model": model,
        "prompt": prompt[:1200],
        "duration": row.get("duration") or 5,
    }
    billed = False
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{_api_base()}/video_generation",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=payload,
            )
            billed = True
            body: dict[str, Any] = {}
            try:
                body = resp.json()
            except Exception:
                body = {"raw": redact_secret(resp.text[:200])}
    except Exception as exc:
        reconcile(
            reservation,
            billed_unknown=True,
            video_clips=1,
            error=redact_secret(f"{type(exc).__name__}"),
        )
        row["status"] = "error"
        row["result"] = {"error": redact_secret(str(exc))[:200], "billed_unknown": True}
        _write(row)
        raise RuntimeError(redact_secret(f"{type(exc).__name__}")) from None

    if resp.status_code != 200:
        reconcile(
            reservation,
            billed_unknown=True,
            video_clips=1,
            error=redact_secret(f"MiniMax HTTP {resp.status_code}"),
        )
        row["status"] = "error"
        row["result"] = {
            "error": redact_secret(f"MiniMax HTTP {resp.status_code}"),
            "billed_unknown": True,
        }
        _write(row)
        raise RuntimeError(redact_secret(f"MiniMax HTTP {resp.status_code}"))

    row["status"] = "generated"
    row["generated_at"] = _iso()
    row["result"] = {
        "task_id": body.get("task_id") or body.get("id") or (body.get("data") or {}).get("task_id"),
        "ai_generated": True,
        "posted": False,
        "billed": billed,
        "label_es": AI_LABEL_ES,
        "label_en": AI_LABEL_EN,
    }
    _write(row)
    reconcile(reservation, video_clips=1)
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
