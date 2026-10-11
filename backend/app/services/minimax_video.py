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

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

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

# Official H3 Pay-as-you-go video API (not Hailuo /v1 {prompt}).
# https://platform.minimax.io/docs/guides/video-generation
H3_CREATE_PATH = "/v2/video_generation"
H3_QUERY_PATH = "/v2/query/video_generation"
H3_MIN_DURATION = 4
H3_MAX_DURATION = 15
H3_DEFAULT_DURATION = 4
H3_DEFAULT_RESOLUTION = "768P"
H3_DEFAULT_RATIO = "16:9"
H3_PROBE_PROMPT = (
    "A wooden analog clock spinning slowly on a table, no people, no text, silent."
)
SUBSCRIPTION_REJECT_CODES = frozenset({1004, 1008, 2013, 2049})
_SUBSCRIPTION_MARKERS = (
    "pay-as-you-go",
    "pay as you go",
    "subscription key",
    "not support",
    "not available for this",
    "insufficient permission",
    "permission denied",
    "invalid api key",
    "wrong api key",
    "unauthorized",
)
# Pay-as-you-go list price: https://platform.minimax.io/docs/guides/pricing-paygo
H3_PAYGO_USD_PER_SEC = {
    ("MiniMax-H3", "768P"): 0.08,
    ("MiniMax-H3", "2K"): 0.13,
    ("MiniMax-H3-Max", "480P"): 0.05,
    ("MiniMax-H3-Max", "768P"): 0.08,
}
VALID_RESOLUTIONS = frozenset({"768P", "2K", "480P"})
VALID_RATIOS = frozenset({"16:9", "9:16", "1:1", "4:3", "3:4", "21:9"})


class SubscriptionKeyRejected(RuntimeError):
    """MiniMax rejected this subscription/M Plan key for H3. Do not retry."""


class H3GenerationError(RuntimeError):
    """H3 create/poll/download failed without producing a clip."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso() -> str:
    return _now().strftime("%Y-%m-%dT%H:%M:%SZ")


def _chmod(path: Path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def clamp_h3_duration(duration: Any) -> int:
    try:
        value = int(duration)
    except (TypeError, ValueError):
        value = H3_DEFAULT_DURATION
    return max(H3_MIN_DURATION, min(value, H3_MAX_DURATION))


def h3_resolution(raw: Optional[str] = None) -> str:
    value = (raw or H3_DEFAULT_RESOLUTION).strip().upper()
    if value == "768":
        value = "768P"
    if value not in VALID_RESOLUTIONS:
        return H3_DEFAULT_RESOLUTION
    return value


def h3_ratio(raw: Optional[str] = None) -> str:
    value = (raw or H3_DEFAULT_RATIO).strip()
    if value.lower() == "adaptive" or value not in VALID_RATIOS:
        # Text-to-video requires an explicit ratio; adaptive is I2V-only.
        return H3_DEFAULT_RATIO
    return value


def estimate_h3_cost(
    *,
    model: Optional[str] = None,
    duration: Any = H3_DEFAULT_DURATION,
    resolution: Optional[str] = None,
) -> dict[str, Any]:
    model_name = (model or h3_model() or "MiniMax-H3").strip()
    res = h3_resolution(resolution)
    seconds = clamp_h3_duration(duration)
    rate = H3_PAYGO_USD_PER_SEC.get((model_name, res))
    if rate is None:
        rate = H3_PAYGO_USD_PER_SEC[("MiniMax-H3", "768P")]
    usd = round(rate * seconds, 4)
    return {
        "usd": usd,
        "currency": "USD",
        "duration_seconds": seconds,
        "resolution": res,
        "model": model_name,
        "rate_usd_per_second": rate,
        "source": "MiniMax pay-as-you-go list price",
        "source_url": "https://platform.minimax.io/docs/guides/pricing-paygo",
        "note": (
            "H3 is billed on the Pay-as-you-go API. "
            "A subscription / M Plan key may be rejected."
        ),
    }


def clip_was_produced(row: Optional[dict[str, Any]]) -> bool:
    """True only when a real task_id exists and the downloaded file has bytes."""
    if not isinstance(row, dict):
        return False
    result = row.get("result") if isinstance(row.get("result"), dict) else {}
    task_id = str(result.get("task_id") or "").strip()
    path = str(result.get("clip_path") or "").strip()
    if not task_id or not path:
        return False
    try:
        dest = Path(path)
        return dest.is_file() and dest.stat().st_size > 0
    except OSError:
        return False


def h3_poll_interval() -> float:
    raw = (os.getenv("MINIMAX_H3_POLL_INTERVAL") or "").strip()
    try:
        value = float(raw) if raw else 10.0
    except ValueError:
        value = 10.0
    return max(0.0, min(30.0, value))


def h3_poll_timeout() -> float:
    raw = (os.getenv("MINIMAX_H3_POLL_TIMEOUT") or "").strip()
    try:
        value = float(raw) if raw else 480.0
    except ValueError:
        value = 480.0
    return max(0.2, min(900.0, value))


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
    duration: int = H3_DEFAULT_DURATION,
    resolution: Optional[str] = None,
    ratio: Optional[str] = None,
) -> dict[str, Any]:
    from app.edition import edition_name

    ed = normalize_edition(edition or edition_name())
    cleaned = sanitize_prompt(prompt, edition=ed, max_len=1000)
    row = {
        "id": uuid.uuid4().hex[:16],
        "status": "draft",
        "edition": ed,
        "prompt": cleaned,
        "duration": clamp_h3_duration(duration),
        "resolution": h3_resolution(resolution),
        "ratio": h3_ratio(ratio),
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


def _api_origin() -> str:
    raw = (os.getenv("MINIMAX_BASE_URL") or "https://api.minimax.io").strip().rstrip("/")
    parsed = urlparse(raw if "://" in raw else f"https://{raw}")
    origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.netloc else "https://api.minimax.io"
    return origin


def _h3_create_url() -> str:
    return f"{_api_origin()}{H3_CREATE_PATH}"


def _h3_query_url(task_id: str) -> str:
    return f"{_api_origin()}{H3_QUERY_PATH}/{task_id}"


def _api_key() -> str:
    return (os.getenv("MINIMAX_API_KEY") or "").strip()


def _clip_dest(approval_id: str, edition: str) -> Path:
    return _draft_dir(edition) / f"{re_id(approval_id)}.mp4"


def _base_resp(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        return {}
    base = body.get("base_resp")
    return base if isinstance(base, dict) else {}


def _status_code_from_body(body: Any) -> int:
    base = _base_resp(body)
    raw = base.get("status_code", body.get("status_code", 0) if isinstance(body, dict) else 0)
    try:
        return int(raw or 0)
    except (TypeError, ValueError):
        return 0


def _minimax_error_text(status_code: int, body: Any, fallback: str = "") -> str:
    parts = [f"MiniMax HTTP {status_code}"]
    if isinstance(body, dict):
        base = _base_resp(body)
        code = _status_code_from_body(body)
        msg = base.get("status_msg") or body.get("error") or body.get("message") or fallback
        if code not in (0, 200):
            parts.append(f"status_code={code}")
        if msg:
            parts.append(str(msg)[:400])
    elif fallback:
        parts.append(fallback[:400])
    return redact_secret(" ".join(parts))


def is_subscription_rejected(status_code: int, body: Any) -> bool:
    if status_code in {401, 403}:
        return True
    if _status_code_from_body(body) in SUBSCRIPTION_REJECT_CODES:
        return True
    text = ""
    if isinstance(body, dict):
        base = _base_resp(body)
        text = str(base.get("status_msg") or body.get("error") or body.get("message") or "")
    return any(marker in text.lower() for marker in _SUBSCRIPTION_MARKERS)


def _extract_task_id(body: Any) -> Optional[str]:
    if not isinstance(body, dict):
        return None
    for key in ("task_id", "id"):
        val = body.get(key)
        if val:
            return str(val).strip()
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    val = data.get("task_id") or data.get("id")
    if val:
        return str(val).strip()
    task = body.get("task") if isinstance(body.get("task"), dict) else {}
    val = task.get("id") or task.get("task_id")
    return str(val).strip() if val else None


def _extract_video_url(body: Any) -> Optional[str]:
    if not isinstance(body, dict):
        return None
    task = body.get("task") if isinstance(body.get("task"), dict) else body
    content = task.get("content") if isinstance(task.get("content"), dict) else {}
    for candidate in (
        content.get("url"),
        task.get("url"),
        body.get("file_id") if isinstance(body.get("file_id"), str) and str(body.get("file_id")).startswith("http") else None,
    ):
        text = str(candidate or "").strip()
        if text.startswith(("http://", "https://")):
            return text
    return None


def _task_status(body: Any) -> str:
    if not isinstance(body, dict):
        return ""
    task = body.get("task") if isinstance(body.get("task"), dict) else body
    return str(task.get("status") or body.get("status") or "").strip().lower()


def _h3_payload(row: dict[str, Any], model: str) -> dict[str, Any]:
    prompt = f"{row.get('prompt')}\n\n[{AI_LABEL_EN} / {AI_LABEL_ES}]"
    return {
        "model": model,
        "content": [{"type": "text", "text": prompt[:7000]}],
        "duration": clamp_h3_duration(row.get("duration")),
        "resolution": h3_resolution(row.get("resolution")),
        "ratio": h3_ratio(row.get("ratio")),
    }


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


def _fail_row(
    row: dict[str, Any],
    reservation: Any,
    *,
    error: str,
    billed_unknown: bool,
    video_clips: int,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    reconcile(
        reservation,
        billed_unknown=billed_unknown,
        video_clips=video_clips,
        error=error,
    )
    result = {
        "error": error[:400],
        "billed_unknown": billed_unknown,
        "ai_generated": True,
        "posted": False,
    }
    if extra:
        result.update(extra)
    row["status"] = "error"
    row["result"] = result
    _write(row)


async def _poll_h3_task(
    client: httpx.AsyncClient,
    *,
    task_id: str,
    headers: dict[str, str],
) -> tuple[str, dict[str, Any]]:
    """Poll GET /v2/query/video_generation/{task_id} until a URL or hard timeout."""
    deadline = time.monotonic() + h3_poll_timeout()
    interval = h3_poll_interval()
    last_body: dict[str, Any] = {}
    last_status = ""
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise H3GenerationError(
                redact_secret(
                    f"H3 poll timed out after {h3_poll_timeout():.0f}s "
                    f"(task_id={task_id}, last_status={last_status or 'none'})"
                )
            )
        resp = await client.get(_h3_query_url(task_id), headers=headers, timeout=min(30.0, remaining))
        try:
            body = resp.json()
        except Exception:
            body = {"raw": redact_secret(resp.text[:200])}
        last_body = body if isinstance(body, dict) else {"raw": redact_secret(str(body)[:200])}
        if is_subscription_rejected(resp.status_code, body):
            raise SubscriptionKeyRejected(_minimax_error_text(resp.status_code, body))
        if resp.status_code != 200:
            raise H3GenerationError(_minimax_error_text(resp.status_code, body, "query failed"))
        last_status = _task_status(body)
        if last_status in {"succeeded", "success", "completed"}:
            url = _extract_video_url(body)
            if not url:
                raise H3GenerationError(
                    redact_secret(f"H3 task {task_id} succeeded without content.url")
                )
            return url, last_body
        if last_status in {"failed", "cancelled", "canceled", "error"}:
            task = last_body.get("task") if isinstance(last_body.get("task"), dict) else last_body
            detail = task.get("error") or task.get("status_msg") or last_status
            raise H3GenerationError(
                redact_secret(f"H3 task {task_id} {last_status}: {detail}")
            )
        await asyncio.sleep(min(interval, max(0.0, deadline - time.monotonic())))


async def _download_clip(client: httpx.AsyncClient, url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    _chmod(dest.parent, 0o700)
    tmp = dest.with_suffix(".tmp")
    resp = await client.get(url, timeout=120.0, follow_redirects=True)
    if resp.status_code != 200 or not resp.content:
        raise H3GenerationError(
            redact_secret(f"H3 download HTTP {resp.status_code} ({len(resp.content or b'')} bytes)")
        )
    tmp.write_bytes(resp.content)
    _chmod(tmp, 0o600)
    tmp.replace(dest)
    _chmod(dest, 0o600)
    if dest.stat().st_size <= 0:
        raise H3GenerationError("H3 download wrote an empty file")
    return dest


async def generate_approved_clip(
    approval_id: str,
    *,
    caller_edition: Optional[str] = None,
) -> dict[str, Any]:
    """Spend one weekly clip. Reserve + generating MUST happen before HTTP.

    Official H3 flow: one POST /v2/video_generation, poll
    GET /v2/query/video_generation/{task_id}, download task.content.url.
    ``status=generated`` only after a real file exists. Never posts.
    Subscription-key rejects are reported and never retried.
    """
    row = _read(approval_id)
    _assert_caller_edition(row, caller_edition)
    if row.get("status") == "generated" and clip_was_produced(row):
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
    row["duration"] = clamp_h3_duration(row.get("duration"))
    row["resolution"] = h3_resolution(row.get("resolution"))
    row["ratio"] = h3_ratio(row.get("ratio"))
    row["posted"] = False
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

    payload = _h3_payload(row, model)
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    posted_once = False
    task_id: Optional[str] = None
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post(
                    _h3_create_url(),
                    headers=headers,
                    json=payload,
                )
                posted_once = True
            except SubscriptionKeyRejected:
                raise
            except Exception as exc:
                _fail_row(
                    row,
                    reservation,
                    error=redact_secret(f"{type(exc).__name__}"),
                    billed_unknown=True,
                    video_clips=1,
                )
                raise RuntimeError(redact_secret(f"{type(exc).__name__}")) from None

            try:
                body = resp.json()
            except Exception:
                body = {"raw": redact_secret(resp.text[:200])}

            if is_subscription_rejected(resp.status_code, body):
                err = _minimax_error_text(resp.status_code, body)
                _fail_row(
                    row,
                    reservation,
                    error=err,
                    billed_unknown=False,
                    video_clips=0,
                    extra={"subscription_rejected": True},
                )
                raise SubscriptionKeyRejected(err)

            task_id = _extract_task_id(body)
            if resp.status_code != 200 or not task_id:
                err = _minimax_error_text(
                    resp.status_code,
                    body,
                    "create returned no task_id (v1 Hailuo-shaped success is not a clip)",
                )
                _fail_row(
                    row,
                    reservation,
                    error=err,
                    billed_unknown=True,
                    video_clips=1,
                    extra={"task_id": task_id},
                )
                raise H3GenerationError(err)

            row["result"] = {
                "task_id": task_id,
                "ai_generated": True,
                "posted": False,
                "status": "submitted",
            }
            _write(row)

            try:
                video_url, query_body = await _poll_h3_task(
                    client, task_id=task_id, headers=headers
                )
            except SubscriptionKeyRejected as exc:
                _fail_row(
                    row,
                    reservation,
                    error=str(exc),
                    billed_unknown=True,
                    video_clips=1,
                    extra={"task_id": task_id, "subscription_rejected": True},
                )
                raise
            except Exception as exc:
                _fail_row(
                    row,
                    reservation,
                    error=redact_secret(str(exc))[:400],
                    billed_unknown=True,
                    video_clips=1,
                    extra={"task_id": task_id},
                )
                raise H3GenerationError(redact_secret(str(exc))[:400]) from None

            dest = _clip_dest(approval_id, row.get("edition") or "workroom")
            try:
                await _download_clip(client, video_url, dest)
            except Exception as exc:
                _fail_row(
                    row,
                    reservation,
                    error=redact_secret(str(exc))[:400],
                    billed_unknown=True,
                    video_clips=1,
                    extra={"task_id": task_id, "download_url": redact_secret(video_url)[:160]},
                )
                raise H3GenerationError(redact_secret(str(exc))[:400]) from None
    except (SubscriptionKeyRejected, H3GenerationError, RuntimeError, PermissionError):
        raise

    cost = estimate_h3_cost(
        model=model,
        duration=row.get("duration"),
        resolution=row.get("resolution"),
    )
    row["status"] = "generated"
    row["generated_at"] = _iso()
    row["posted"] = False
    row["result"] = {
        "task_id": task_id,
        "clip_path": str(dest),
        "clip_bytes": dest.stat().st_size,
        "download_url": redact_secret(video_url)[:160],
        "query_status": _task_status(query_body),
        "ai_generated": True,
        "posted": False,
        "billed": posted_once,
        "cost_estimate": cost,
        "label_es": AI_LABEL_ES,
        "label_en": AI_LABEL_EN,
    }
    if not clip_was_produced(row):
        _fail_row(
            row,
            reservation,
            error="H3 finished without a downloaded clip",
            billed_unknown=True,
            video_clips=1,
            extra={"task_id": task_id},
        )
        raise H3GenerationError("H3 finished without a downloaded clip")
    _write(row)
    reconcile(reservation, video_clips=1)
    return row


def snapshot_quota() -> dict[str, Any]:
    from app.services.minimax_meter import local_plan_used_pct

    remains = fetch_remains(force=True)
    credits = fetch_credits(force=True)
    credits_readable = bool(credits.get("available") and credits.get("balance") is not None)
    return {
        "at": _iso(),
        "plan_remaining_pct": remains.get("remaining_pct"),
        "plan_used_pct": remains.get("used_pct"),
        "plan_available": remains.get("available"),
        "plan_reason": remains.get("reason"),
        "credit_balance": credits.get("balance"),
        "credits_available": credits.get("available"),
        "credits_readable": credits_readable,
        "credits_reason": (
            None
            if credits_readable
            else (credits.get("reason") or "credit balance endpoint could not be read")
        ),
        "local_plan_used_pct": local_plan_used_pct(),
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
    local_delta = _delta(before.get("local_plan_used_pct"), after.get("local_plan_used_pct"))
    plan_moved = plan_delta is not None and abs(plan_delta) > 0.01
    credit_moved = credit_delta is not None and abs(credit_delta) > 0.01
    credits_readable = bool(after.get("credits_readable") or before.get("credits_readable"))
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
    notes = {
        "plan_quota": "Plan remaining moved; this clip likely used subscription quota.",
        "credit_balance": "Credit balance moved; H3 may not be covered by the M Plan key.",
        "both": "Both plan remaining and credits moved.",
        "no_visible_change": "Neither bar moved enough to tell (docs conflict; do not assume).",
        "unknown_no_remains": "Remains endpoint was not available.",
    }.get(verdict)
    if not credits_readable:
        unread = after.get("credits_reason") or before.get("credits_reason") or (
            "credit balance endpoint could not be read; recorded local estimate"
        )
        notes = f"{notes} {unread}".strip()
    return {
        "verdict": verdict,
        "plan_remaining_delta": plan_delta,
        "credit_balance_delta": credit_delta,
        "local_plan_used_delta": local_delta,
        "credits_readable": credits_readable,
        "h3_on_subscription": verdict == "plan_quota",
        "notes": notes,
    }


def probe_live_allowed() -> bool:
    return (os.getenv("MINIMAX_H3_PROBE_LIVE") or "").strip() in {"1", "true", "yes"}


def llm_tool_refuses_generate(params: Optional[dict] = None) -> Optional[str]:
    """LLM / tool path may only create drafts. approval_id is never a spend key."""
    params = params or {}
    approval_id = (params.get("approval_id") or params.get("approval") or "").strip()
    if approval_id:
        return bilingual(
            "La herramienta no genera clips; Rafael genera desde Max personal "
            "con X-Minimax-Video-Confirm: aprobar.",
            "The LLM tool cannot generate clips. Rafael generates from personal Max "
            "with header X-Minimax-Video-Confirm: aprobar.",
        )
    return None


def llm_create_draft(params: dict) -> dict[str, Any]:
    refusal = llm_tool_refuses_generate(params)
    if refusal:
        raise PermissionError(refusal)
    if not h3_enabled():
        raise PermissionError(
            bilingual(
                "El video H3 está apagado (MINIMAX_H3_ENABLED).",
                "H3 video is disabled (MINIMAX_H3_ENABLED).",
            )
        )
    return create_draft(
        params.get("prompt", ""),
        duration=int(params.get("duration", H3_DEFAULT_DURATION) or H3_DEFAULT_DURATION),
        resolution=params.get("resolution"),
        ratio=params.get("ratio"),
    )
