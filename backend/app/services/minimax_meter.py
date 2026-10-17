"""Shared MiniMax usage meter for Max, Max-e, and Maxine.

Per-edition append-only logs (0700 dirs, 0600 files). Every MiniMax call
is reserved under one exclusive lock, then reconciled after the call.

Caps:
* Max-e and Maxine each <= 20% of the text pool (env MINIMAX_EDITION_TEXT_SHARE_PCT).
* No combined family text cap — each edition is independent.
* Matches INSTANCE_USAGE_CAP_PCT=20 per family instance.
* Per family edition per UTC day: 5 images, ~20 short TTS replies.
* Video: 1 clip/week, founder approval only.
* All agents hard-stop near 80% of the plan bar when remains is readable.
* If /token_plan/remains cannot be read: fail CLOSED for images, TTS,
  video, and family text. Founder text may continue only up to the local
  estimate, with a visible warning. Auto credit usage is ON — never rely
  on MiniMax to stop spend.

Gift credits are never treated as room. Messages are Spanish + English.
"""
from __future__ import annotations

import json
import logging
import os
import re
import stat
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("max.minimax_meter")

FAMILY_EDITIONS = frozenset({"amp", "maxine"})
KNOWN_EDITIONS = frozenset({"amp", "maxine", "workroom"})
NONESSENTIAL_KINDS = frozenset({"image", "tts", "video", "web_search"})

DEFAULT_EDITION_TEXT_SHARE_PCT = 20.0
DEFAULT_RESERVED_SHARE_PCT = 80.0
DEFAULT_IMAGE_DAILY_CAP = 5
DEFAULT_TTS_DAILY_CAP = 20
DEFAULT_VIDEO_WEEKLY_CAP = 1
DEFAULT_PLAN_HARD_STOP_PCT = 80.0
DEFAULT_TEXT_POOL_FLOOR = 10_000_000.0
DEFAULT_TTS_MAX_CHARS = 400

_KEY_RE = re.compile(
    r"(?i)(authorization|api[_-]?key|bearer|secret|token|minimax_api_key)\s*[:=]\s*\S+"
)
_BEARER_RE = re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+")

_active_reservation: ContextVar[Optional[str]] = ContextVar("minimax_reservation", default=None)
_plan_warning: ContextVar[Optional[str]] = ContextVar("minimax_plan_warning", default=None)


class MeterBlocked(Exception):
    """Call must not proceed. ``message`` is bilingual user text."""

    def __init__(self, message: str, *, code: str = "blocked"):
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass
class Reservation:
    id: str
    edition: str
    kind: str
    blocked: bool = False
    message: str = ""
    warning: str = ""
    reserved: dict[str, int] = field(default_factory=dict)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime] = None) -> str:
    return (dt or _now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def _float_env(name: str, default: float) -> float:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0.0, float(raw))
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def edition_text_share_pct() -> float:
    return _float_env("MINIMAX_EDITION_TEXT_SHARE_PCT", DEFAULT_EDITION_TEXT_SHARE_PCT)


def reserved_share_pct() -> float:
    return _float_env("MINIMAX_RESERVED_SHARE_PCT", DEFAULT_RESERVED_SHARE_PCT)


def image_daily_cap() -> int:
    return _int_env("MINIMAX_IMAGE_DAILY_CAP", DEFAULT_IMAGE_DAILY_CAP)


def tts_daily_cap() -> int:
    return _int_env("MINIMAX_TTS_DAILY_CAP", DEFAULT_TTS_DAILY_CAP)


def video_weekly_cap() -> int:
    return _int_env("MINIMAX_VIDEO_WEEKLY_CAP", DEFAULT_VIDEO_WEEKLY_CAP)


def plan_hard_stop_pct() -> float:
    return _float_env("MINIMAX_PLAN_HARD_STOP_PCT", DEFAULT_PLAN_HARD_STOP_PCT)


def text_pool_floor() -> float:
    return _float_env("MINIMAX_TEXT_POOL_FLOOR", DEFAULT_TEXT_POOL_FLOOR)


def tts_max_chars() -> int:
    return _int_env("MINIMAX_TTS_MAX_CHARS", DEFAULT_TTS_MAX_CHARS)


def family_tts_enabled() -> bool:
    return (os.getenv("MINIMAX_FAMILY_TTS") or "").strip().lower() in {"1", "true", "yes", "on"}


def h3_enabled() -> bool:
    """H3 is only MINIMAX_H3_ENABLED. MINIMAX_VIDEO_ENABLED must not turn it on."""
    return (os.getenv("MINIMAX_H3_ENABLED") or "").strip().lower() in {"1", "true", "yes", "on"}


def h3_model() -> str:
    """No silent Hailuo-02 default. Set MINIMAX_H3_MODEL only after the probe."""
    return (os.getenv("MINIMAX_H3_MODEL") or "").strip()


def current_edition() -> str:
    from app.edition import edition_name

    return normalize_edition(edition_name())


def normalize_edition(raw: Optional[str]) -> str:
    name = (raw or "").strip().lower()
    if name in {"", "main"}:
        return "workroom"
    if name in KNOWN_EDITIONS:
        return name
    return name or "workroom"


def is_family(edition: Optional[str] = None) -> bool:
    return normalize_edition(edition or current_edition()) in FAMILY_EDITIONS


def redact(text: str) -> str:
    if not text:
        return ""
    out = _BEARER_RE.sub("Bearer [KEY_REDACTED]", str(text))
    out = _KEY_RE.sub("[KEY_REDACTED]", out)
    key = os.getenv("MINIMAX_API_KEY", "")
    if key and len(key) >= 8:
        out = out.replace(key, "[KEY_REDACTED]")
    return out


def bilingual(es: str, en: str) -> str:
    return f"{es} / {en}"


def meter_dir() -> Path:
    raw = (os.getenv("MINIMAX_METER_DIR") or "").strip()
    if raw:
        path = Path(raw).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        _chmod(path, 0o700)
        return path
    default = Path("/data/minimax-meter")
    try:
        default.mkdir(parents=True, exist_ok=True)
        if os.access(default, os.W_OK):
            _chmod(default, 0o700)
            return default
    except OSError:
        pass
    from app.edition import data_root_or_none, is_family_edition

    root = data_root_or_none()
    if root is not None:
        path = Path(root) / "minimax-meter"
        path.mkdir(parents=True, exist_ok=True)
        _chmod(path, 0o700)
        return path
    if is_family_edition():
        raise MeterBlocked(
            bilingual(
                "No hay un directorio compartido para el medidor MiniMax (MINIMAX_METER_DIR).",
                "Shared MiniMax meter directory is not configured (MINIMAX_METER_DIR).",
            ),
            code="meter_unavailable",
        )
    fallback = Path(os.getenv("TMPDIR") or "/tmp") / "empire-minimax-meter"
    fallback.mkdir(parents=True, exist_ok=True)
    _chmod(fallback, 0o700)
    return fallback


def _chmod(path: Path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def edition_dir(edition: Optional[str] = None) -> Path:
    ed = normalize_edition(edition or current_edition())
    path = meter_dir() / ed
    path.mkdir(parents=True, exist_ok=True)
    _chmod(path, 0o700)
    return path


def log_path(edition: Optional[str] = None) -> Path:
    ed = normalize_edition(edition or current_edition())
    return edition_dir(ed) / f"calls-{ed}.jsonl"


def video_drafts_dir(edition: Optional[str] = None) -> Path:
    path = edition_dir(edition) / "video_drafts"
    path.mkdir(parents=True, exist_ok=True)
    _chmod(path, 0o700)
    return path


def founder_video_queue_dir() -> Path:
    """Founder-only queue (0700). Family editions write drafts under their own dir."""
    path = meter_dir() / "video_queue"
    path.mkdir(parents=True, exist_ok=True)
    _chmod(path, 0o700)
    return path


def _lock_path() -> Path:
    return meter_dir() / "meter.lock"


def _with_exclusive_lock():
    import fcntl

    path = _lock_path()
    handle = open(path, "a+", encoding="utf-8")
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    _chmod(path, 0o600)
    return handle


def _iso_week(dt: Optional[datetime] = None) -> str:
    stamp = dt or _now()
    iso = stamp.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def _empty_totals() -> dict[str, Any]:
    return {
        "text_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "images": 0,
        "tts_replies": 0,
        "tts_chars": 0,
        "video_clips": 0,
        "web_search": 0,
        "calls": 0,
    }


def _add(totals: dict[str, Any], rec: dict[str, Any]) -> None:
    if rec.get("blocked") or rec.get("status") == "blocked":
        return
    kind = rec.get("kind") or "text"
    totals["calls"] += 1
    totals["input_tokens"] += int(rec.get("input_tokens") or 0)
    totals["output_tokens"] += int(rec.get("output_tokens") or 0)
    totals["text_tokens"] += int(rec.get("input_tokens") or 0) + int(rec.get("output_tokens") or 0)
    totals["images"] += int(rec.get("images") or 0)
    totals["tts_replies"] += 1 if kind == "tts" else 0
    totals["tts_chars"] += int(rec.get("tts_chars") or 0)
    totals["video_clips"] += int(rec.get("video_clips") or 0)
    totals["web_search"] += 1 if kind == "web_search" else 0


def _parse_line(text: str) -> Optional[dict[str, Any]]:
    try:
        rec = json.loads(text)
    except json.JSONDecodeError:
        return None
    return rec if isinstance(rec, dict) else None


def _read_file(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            rec = _parse_line(line.strip())
            if rec:
                rows.append(rec)
    return rows


def _effective(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Latest row per id wins (reserve then settle)."""
    by_id: dict[str, dict[str, Any]] = {}
    loose: list[dict[str, Any]] = []
    for rec in rows:
        rid = rec.get("id")
        if rid:
            by_id[str(rid)] = rec
        else:
            loose.append(rec)
    return loose + list(by_id.values())


def _read_records_unlocked(*, edition: Optional[str] = None, aggregator: bool = False) -> list[dict[str, Any]]:
    if edition and not aggregator:
        return _effective(_read_file(log_path(edition)))
    rows: list[dict[str, Any]] = []
    for ed in KNOWN_EDITIONS:
        path = log_path(ed)
        try:
            rows.extend(_read_file(path))
        except OSError:
            continue
    return _effective(rows)


def _append_unlocked(rec: dict[str, Any]) -> dict[str, Any]:
    payload = dict(rec)
    payload.setdefault("id", uuid.uuid4().hex[:12])
    payload.setdefault("ts", _iso())
    payload["edition"] = normalize_edition(payload.get("edition") or current_edition())
    payload["kind"] = str(payload.get("kind") or "text")
    for key in ("model", "reason", "approval_id"):
        if key in payload and payload[key] is not None:
            payload[key] = redact(str(payload[key]))[:300]
    line = redact(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    key = os.getenv("MINIMAX_API_KEY") or ""
    if key:
        line = line.replace(key, "[KEY_REDACTED]")
    path = log_path(payload["edition"])
    if not path.exists():
        path.touch()
    _chmod(path, 0o600)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    _chmod(path, 0o600)
    return payload


def _match_window(rec: dict[str, Any], *, day: Optional[str], week: Optional[str], month: Optional[str]) -> bool:
    ts = rec.get("ts") or ""
    if day and not str(ts).startswith(day):
        return False
    if month and not str(ts).startswith(month):
        return False
    if week:
        try:
            stamp = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except ValueError:
            return False
        if _iso_week(stamp) != week:
            return False
    return True


def totals(
    *,
    edition: Optional[str] = None,
    day: Optional[str] = None,
    week: Optional[str] = None,
    month: Optional[str] = None,
    kind: Optional[str] = None,
    rows: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    out = _empty_totals()
    records = rows if rows is not None else _read_records_unlocked(edition=edition, aggregator=edition is None)
    for rec in records:
        if edition and rec.get("edition") != edition:
            continue
        if kind and rec.get("kind") != kind:
            continue
        if not _match_window(rec, day=day, week=week, month=month):
            continue
        _add(out, rec)
    return out


def _family_combined_tokens(month: str, rows: list[dict[str, Any]]) -> int:
    tokens = 0
    for ed in FAMILY_EDITIONS:
        tokens += int(totals(edition=ed, month=month, rows=rows)["text_tokens"])
    return tokens


def _pool_tokens(month: str, rows: list[dict[str, Any]]) -> float:
    return max(float(totals(month=month, rows=rows)["text_tokens"]), text_pool_floor())


def _stub_snapshot() -> Optional[dict[str, Any]]:
    stub = (os.getenv("MINIMAX_REMAINS_STUB") or "").strip().lower()
    if stub == "ok":
        return {
            "remains": {"ok": True, "available": True, "remaining_pct": 90.0, "used_pct": 10.0},
            "credits": {"ok": False, "available": False, "balance": None},
        }
    if stub in {"down", "unavailable"}:
        return {
            "remains": {"ok": False, "available": False, "remaining_pct": None, "used_pct": None},
            "credits": {"ok": False, "available": False, "balance": None},
        }
    if stub in {"hot", "80", "stopped"}:
        return {
            "remains": {"ok": True, "available": True, "remaining_pct": 15.0, "used_pct": 85.0},
            "credits": {"ok": True, "available": True, "balance": 2000},
        }
    return None


def _plan_snapshot() -> dict[str, Any]:
    stub = _stub_snapshot()
    if stub is not None:
        return stub
    try:
        from app.services.minimax_quota import fetch_credits, fetch_remains

        remains = fetch_remains()
        credits = fetch_credits()
    except Exception as exc:
        logger.info("minimax remains probe failed: %s", redact(str(exc)))
        remains = {"ok": False, "available": False, "remaining_pct": None, "used_pct": None}
        credits = {"ok": False, "available": False, "balance": None}
    return {"remains": remains, "credits": credits}


def _plan_block_message() -> str:
    stop = plan_hard_stop_pct()
    return bilingual(
        f"Tope del plan MiniMax: todos los agentes se detienen al {stop:g}% de la barra "
        "para no gastar los créditos de regalo (Auto credit usage está ON).",
        f"MiniMax plan cap: every agent stops at {stop:g}% of the usage bar "
        "so gift credits are not spent (Auto credit usage is ON).",
    )


def remains_down_message() -> str:
    return bilingual(
        "No pude leer /token_plan/remains. Auto credit usage está ON: bloqueo imágenes, voz, "
        "video y el texto familiar para no gastar créditos de regalo.",
        "Could not read /token_plan/remains. Auto credit usage is ON: blocking images, voice, "
        "video, and family text so gift credits are not spent.",
    )


def founder_remains_warning() -> str:
    return bilingual(
        "Aviso: no hay lectura del cupo MiniMax. El texto personal sigue solo con la estimación "
        "local. Recomendación: apaga Auto credit usage en MiniMax.",
        "Warning: MiniMax remaining-quota is unread. Personal text continues only on the local "
        "estimate. Recommendation: turn off Auto credit usage on MiniMax.",
    )


def local_plan_used_pct(rows: Optional[list[dict[str, Any]]] = None) -> float:
    """Local stand-in for the unpublished plan bar: recorded tokens / floor."""
    month = _now().strftime("%Y-%m")
    recorded = float(totals(month=month, rows=rows)["text_tokens"])
    images = float(totals(month=month, kind="image", rows=rows)["images"])
    tts = float(totals(month=month, kind="tts", rows=rows)["tts_replies"])
    clips = float(totals(month=month, kind="video", rows=rows)["video_clips"])
    # Cheap proxy so generation also moves the local bar.
    proxy = recorded + images * 50_000 + tts * 5_000 + clips * 200_000
    floor = max(text_pool_floor(), 1.0)
    return min(100.0, round(proxy / floor * 100.0, 2))


def plan_hard_stopped(
    snapshot: Optional[dict] = None,
    *,
    kind: str = "text",
    edition: Optional[str] = None,
    rows: Optional[list[dict[str, Any]]] = None,
) -> Optional[str]:
    """Fail CLOSED when remains is unread. Founder text may continue on local estimate."""
    snap = snapshot or _plan_snapshot()
    remains = snap.get("remains") or {}
    ed = normalize_edition(edition or current_edition())
    kind = (kind or "text").strip().lower()
    stop = plan_hard_stop_pct()

    if remains.get("available"):
        used = remains.get("used_pct")
        remaining = remains.get("remaining_pct")
        if used is not None and float(used) >= stop:
            return _plan_block_message()
        if remaining is not None and float(remaining) <= max(0.0, 100.0 - stop):
            return _plan_block_message()
        return None

    # Remains unread: never fail-open into Auto credits.
    if kind in NONESSENTIAL_KINDS or ed in FAMILY_EDITIONS:
        return remains_down_message()
    local = local_plan_used_pct(rows)
    if local >= stop:
        return bilingual(
            f"Estimación local del plan ≥ {stop:g}% y no hay lectura de remains. Texto personal en pausa.",
            f"Local plan estimate ≥ {stop:g}% and remains is unread. Personal text is paused.",
        )
    return None


def pop_plan_warning() -> str:
    text = _plan_warning.get() or ""
    _plan_warning.set(None)
    return text


def active_reservation_id() -> Optional[str]:
    return _active_reservation.get()


def _family_text_block(
    edition: str,
    add_tokens: int,
    month: str,
    rows: list[dict[str, Any]],
    *,
    kind: str = "",
    source: str = "",
    desk: Optional[str] = None,
) -> Optional[str]:
    if edition not in FAMILY_EDITIONS:
        return None
    pool = _pool_tokens(month, rows)
    mine = int(totals(edition=edition, month=month, rows=rows)["text_tokens"]) + max(0, add_tokens)
    per = edition_text_share_pct()
    mine_pct = (mine / pool) * 100.0 if pool else 0.0
    if mine_pct > per + 1e-9:
        try:
            from app.services.instance_usage import family_overage_allowed, is_background_request
            if family_overage_allowed(mine_pct) and not is_background_request(
                kind=kind, source=source, desk=desk,
            ):
                return None
        except Exception:
            pass
        return bilingual(
            f"Tope de esta edición: Max-e y Maxine pueden usar cada una el {per:g}% "
            f"del cupo de texto MiniMax (el mismo 20% que INSTANCE_USAGE_CAP_PCT). "
            f"Esta edición ya iría al {mine_pct:.1f}%. No hay tope combinado.",
            f"Edition cap: Max-e and Maxine may each use {per:g}% of the MiniMax "
            f"text pool (the same 20% as INSTANCE_USAGE_CAP_PCT). "
            f"This edition would be at {mine_pct:.1f}%. There is no combined family cap.",
        )
    return None


def _image_block(edition: str, add_images: int, day: str, rows: list[dict[str, Any]]) -> Optional[str]:
    cap = image_daily_cap()
    used = int(totals(edition=edition, day=day, kind="image", rows=rows)["images"]) + max(0, add_images)
    if used > cap:
        return bilingual(
            f"Tope de imágenes: esta edición puede generar {cap} al día. Ya se usaría {used}.",
            f"Image cap: this edition may generate {cap} images per day. It would be {used}.",
        )
    return None


def _tts_block(edition: str, add_replies: int, day: str, rows: list[dict[str, Any]]) -> Optional[str]:
    cap = tts_daily_cap()
    used = int(totals(edition=edition, day=day, kind="tts", rows=rows)["tts_replies"]) + max(0, add_replies)
    if used > cap:
        return bilingual(
            f"Tope de voz: esta edición puede hacer {cap} respuestas cortas de TTS al día.",
            f"Voice cap: this edition may make {cap} short TTS replies per day.",
        )
    return None


def _video_block(add_clips: int, week: str, rows: list[dict[str, Any]]) -> Optional[str]:
    cap = video_weekly_cap()
    used = int(totals(week=week, kind="video", rows=rows)["video_clips"]) + max(0, add_clips)
    if used > cap:
        return bilingual(
            f"Tope de video: {cap} clip por semana en todo el plan, y solo con la aprobación de Rafael.",
            f"Video cap: {cap} clip per week across the plan, and only with Rafael's approval.",
        )
    return None


def _eval_caps(
    *,
    kind: str,
    edition: str,
    input_tokens: int,
    output_tokens: int,
    images: int,
    tts_chars: int,
    tts_replies: int,
    video_clips: int,
    approval_id: Optional[str],
    rows: list[dict[str, Any]],
    source: str = "",
    desk: Optional[str] = None,
    request_kind: str = "",
) -> tuple[Optional[str], str]:
    now = _now()
    day = now.strftime("%Y-%m-%d")
    month = now.strftime("%Y-%m")
    week = _iso_week(now)
    warning = ""

    plan_msg = plan_hard_stopped(kind=kind, edition=edition, rows=rows)
    if plan_msg:
        return plan_msg, warning
    snap = _plan_snapshot()
    if not (snap.get("remains") or {}).get("available") and edition not in FAMILY_EDITIONS and kind == "text":
        warning = founder_remains_warning()

    if kind == "text":
        add = max(0, int(input_tokens)) + max(0, int(output_tokens))
        return _family_text_block(
            edition, add or 1, month, rows,
            kind=request_kind or kind, source=source, desk=desk,
        ), warning
    if kind == "image":
        if edition in FAMILY_EDITIONS:
            text_msg = _family_text_block(
                edition, 0, month, rows,
                kind=request_kind or kind, source=source, desk=desk,
            )
            if text_msg:
                return text_msg, warning
        return _image_block(edition, max(1, int(images) or 1), day, rows), warning
    if kind == "tts":
        if edition in FAMILY_EDITIONS and not family_tts_enabled():
            return bilingual(
                "La voz MiniMax (speech-2.8) está apagada en esta edición (MINIMAX_FAMILY_TTS).",
                "MiniMax speech-2.8 voice is off for this edition (MINIMAX_FAMILY_TTS).",
            ), warning
        chars = max(0, int(tts_chars))
        if edition in FAMILY_EDITIONS and chars > tts_max_chars():
            return bilingual(
                f"Esta respuesta de voz es demasiado larga (máx. {tts_max_chars()} caracteres).",
                f"This voice reply is too long (max {tts_max_chars()} characters).",
            ), warning
        if edition not in FAMILY_EDITIONS:
            return None, warning
        return _tts_block(edition, max(1, int(tts_replies) or 1), day, rows), warning
    if kind == "video":
        if not h3_enabled():
            return bilingual(
                "El video H3 está apagado (MINIMAX_H3_ENABLED). MINIMAX_VIDEO_ENABLED no lo enciende.",
                "H3 video is disabled (MINIMAX_H3_ENABLED). MINIMAX_VIDEO_ENABLED does not enable it.",
            ), warning
        if not h3_model():
            return bilingual(
                "No hay MINIMAX_H3_MODEL. No usamos Hailuo-02 en silencio; primero el probe de un clip.",
                "MINIMAX_H3_MODEL is unset. Hailuo-02 is not a silent default; run the one-clip probe first.",
            ), warning
        if not approval_id:
            return bilingual(
                "Cada clip H3 necesita la aprobación explícita de Rafael. Se guardó un borrador.",
                "Each H3 clip needs Rafael's explicit approval. A draft was saved.",
            ), warning
        from app.services.minimax_video import approval_is_live

        if not approval_is_live(approval_id):
            return bilingual(
                "No hay una aprobación vigente de Rafael para este clip.",
                "There is no live approval from Rafael for this clip.",
            ), warning
        return _video_block(max(1, int(video_clips) or 1), week, rows), warning
    return None, warning


def check(
    *,
    kind: str,
    edition: Optional[str] = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    images: int = 0,
    tts_chars: int = 0,
    tts_replies: int = 0,
    video_clips: int = 0,
    approval_id: Optional[str] = None,
    source: str = "",
    desk: Optional[str] = None,
    request_kind: str = "",
) -> Optional[str]:
    """Read-only cap peek (tests). Production callers use reserve()."""
    ed = normalize_edition(edition or current_edition())
    handle = _with_exclusive_lock()
    try:
        rows = _read_records_unlocked(aggregator=True)
        msg, warning = _eval_caps(
            kind=(kind or "text").strip().lower(),
            edition=ed,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            images=images,
            tts_chars=tts_chars,
            tts_replies=tts_replies,
            video_clips=video_clips,
            approval_id=approval_id,
            rows=rows,
            source=source,
            desk=desk,
            request_kind=request_kind,
        )
        if warning:
            _plan_warning.set(warning)
        return msg
    finally:
        handle.close()


def enforce(**kwargs) -> Optional[str]:
    try:
        return check(**kwargs)
    except MeterBlocked as exc:
        return exc.message
    except Exception:
        logger.warning("minimax meter check failed closed", exc_info=True)
        return bilingual(
            "No pude confirmar el cupo MiniMax. No gasto créditos de regalo.",
            "Could not confirm MiniMax quota. Gift credits will not be spent.",
        )


def reserve(
    *,
    kind: str,
    edition: Optional[str] = None,
    model: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    images: int = 0,
    tts_chars: int = 0,
    tts_replies: int = 0,
    video_clips: int = 0,
    approval_id: Optional[str] = None,
    source: str = "",
    desk: Optional[str] = None,
    request_kind: str = "",
) -> Reservation:
    """Atomically check caps and append a reserved row under one exclusive lock."""
    ed = normalize_edition(edition or current_edition())
    kind = (kind or "text").strip().lower()
    handle = _with_exclusive_lock()
    try:
        rows = _read_records_unlocked(aggregator=True)
        msg, warning = _eval_caps(
            kind=kind,
            edition=ed,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            images=images,
            tts_chars=tts_chars,
            tts_replies=tts_replies,
            video_clips=video_clips,
            approval_id=approval_id,
            rows=rows,
            source=source,
            desk=desk,
            request_kind=request_kind,
        )
        if warning:
            _plan_warning.set(warning)
        if msg:
            rec = _append_unlocked({
                "edition": ed,
                "kind": kind,
                "model": model,
                "status": "blocked",
                "blocked": True,
                "reason": msg,
                "approval_id": approval_id,
            })
            return Reservation(id=rec["id"], edition=ed, kind=kind, blocked=True, message=msg, warning=warning)
        reserved = {
            "input_tokens": max(0, int(input_tokens)),
            "output_tokens": max(0, int(output_tokens)),
            "images": max(0, int(images)),
            "tts_chars": max(0, int(tts_chars)),
            "video_clips": max(0, int(video_clips)),
        }
        rec = _append_unlocked({
            "edition": ed,
            "kind": kind,
            "model": model,
            "status": "reserved",
            "blocked": False,
            "approval_id": approval_id,
            **reserved,
        })
        _active_reservation.set(rec["id"])
        return Reservation(
            id=rec["id"],
            edition=ed,
            kind=kind,
            reserved=reserved,
            warning=warning,
        )
    finally:
        handle.close()


def reconcile(
    reservation: Reservation | str,
    *,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    images: Optional[int] = None,
    tts_chars: Optional[int] = None,
    video_clips: Optional[int] = None,
    billed_unknown: bool = False,
    error: str = "",
) -> dict[str, Any]:
    """Settle a reservation. If billing is unknown, keep the reserved amounts."""
    rid = reservation.id if isinstance(reservation, Reservation) else str(reservation)
    reserved = reservation.reserved if isinstance(reservation, Reservation) else {}
    handle = _with_exclusive_lock()
    try:
        rows = _read_records_unlocked(aggregator=True)
        prior = next((r for r in rows if r.get("id") == rid), None)
        if prior is None:
            prior = {"id": rid, "edition": current_edition(), "kind": "text", **reserved}
        amounts = {
            "input_tokens": reserved.get("input_tokens", prior.get("input_tokens") or 0),
            "output_tokens": reserved.get("output_tokens", prior.get("output_tokens") or 0),
            "images": reserved.get("images", prior.get("images") or 0),
            "tts_chars": reserved.get("tts_chars", prior.get("tts_chars") or 0),
            "video_clips": reserved.get("video_clips", prior.get("video_clips") or 0),
        }
        if not billed_unknown:
            if input_tokens is not None:
                amounts["input_tokens"] = max(0, int(input_tokens))
            if output_tokens is not None:
                amounts["output_tokens"] = max(0, int(output_tokens))
            if images is not None:
                amounts["images"] = max(0, int(images))
            if tts_chars is not None:
                amounts["tts_chars"] = max(0, int(tts_chars))
            if video_clips is not None:
                amounts["video_clips"] = max(0, int(video_clips))
        payload = {
            **prior,
            **amounts,
            "id": rid,
            "ts": _iso(),
            "status": "settled",
            "blocked": False,
            "billed_unknown": bool(billed_unknown),
            "reason": redact(error)[:300] if error else prior.get("reason") or "",
        }
        return _append_unlocked(payload)
    finally:
        handle.close()
        if _active_reservation.get() == rid:
            _active_reservation.set(None)


def record(
    *,
    kind: str,
    edition: Optional[str] = None,
    model: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    images: int = 0,
    tts_chars: int = 0,
    video_clips: int = 0,
    blocked: bool = False,
    reason: str = "",
    approval_id: Optional[str] = None,
) -> dict[str, Any]:
    """Direct settled write (seeds / tests). Production spend uses reserve+reconcile."""
    handle = _with_exclusive_lock()
    try:
        return _append_unlocked({
            "edition": normalize_edition(edition or current_edition()),
            "kind": kind,
            "model": model,
            "status": "blocked" if blocked else "settled",
            "input_tokens": max(0, int(input_tokens)),
            "output_tokens": max(0, int(output_tokens)),
            "images": max(0, int(images)),
            "tts_chars": max(0, int(tts_chars)),
            "video_clips": max(0, int(video_clips)),
            "blocked": bool(blocked),
            "reason": reason,
            "approval_id": approval_id,
        })
    finally:
        handle.close()


def _edition_view(edition: str, *, day: str, week: str, month: str, pool: float, rows: list[dict[str, Any]]) -> dict[str, Any]:
    month_tot = totals(edition=edition, month=month, rows=rows)
    day_tot = totals(edition=edition, day=day, rows=rows)
    week_tot = totals(edition=edition, week=week, rows=rows)
    text_tokens = int(month_tot["text_tokens"])
    share = (text_tokens / pool) * 100.0 if pool else 0.0
    cap = edition_text_share_pct() if edition in FAMILY_EDITIONS else reserved_share_pct()
    return {
        "edition": edition,
        "label": {"amp": "Max-e · Juan", "maxine": "Maxine · Camilo", "workroom": "Max · Rafael"}.get(
            edition, edition
        ),
        "text_tokens": text_tokens,
        "text_share_pct": round(share, 2),
        "text_cap_pct": cap,
        "images_today": int(day_tot["images"]),
        "image_daily_cap": image_daily_cap(),
        "tts_today": int(day_tot["tts_replies"]),
        "tts_daily_cap": tts_daily_cap(),
        "video_this_week": int(week_tot["video_clips"]),
        "video_weekly_cap": video_weekly_cap(),
    }


def founder_summary() -> dict[str, Any]:
    """Full per-edition breakdown for Rafael's personal Max (aggregator)."""
    now = _now()
    day = now.strftime("%Y-%m-%d")
    month = now.strftime("%Y-%m")
    week = _iso_week(now)
    handle = _with_exclusive_lock()
    try:
        rows = _read_records_unlocked(aggregator=True)
    finally:
        handle.close()
    pool = _pool_tokens(month, rows)
    family_tokens = _family_combined_tokens(month, rows)
    family_pct = (family_tokens / pool) * 100.0 if pool else 0.0
    plan = _plan_snapshot()
    plan_block = plan_hard_stopped(plan, kind="text", edition="workroom", rows=rows)
    remains_ok = bool((plan.get("remains") or {}).get("available"))
    warning = "" if remains_ok else founder_remains_warning()
    return {
        "enforced": True,
        "month": month,
        "day": day,
        "week": week,
        "edition_text_share_pct": edition_text_share_pct(),
        "combined_family_cap": False,
        "reserved_share_pct": reserved_share_pct(),
        "family_text_share_used_pct": round(family_pct, 2),
        "image_daily_cap": image_daily_cap(),
        "tts_daily_cap": tts_daily_cap(),
        "video_weekly_cap": video_weekly_cap(),
        "plan_hard_stop_pct": plan_hard_stop_pct(),
        "family_tts_enabled": family_tts_enabled(),
        "h3_enabled": h3_enabled(),
        "h3_model": h3_model() or "",
        "plan": {
            "available": remains_ok,
            "remaining_pct": (plan.get("remains") or {}).get("remaining_pct"),
            "used_pct": (plan.get("remains") or {}).get("used_pct"),
            "hard_stopped": bool(plan_block),
            "fail_closed_when_unread": True,
            "local_used_pct": local_plan_used_pct(rows),
            "message": plan_block or warning,
            "warning": warning,
            "credits_known": bool((plan.get("credits") or {}).get("available")),
            "credits_not_spendable": True,
            "recommend_disable_auto_credits": True,
        },
        "editions": [_edition_view(ed, day=day, week=week, month=month, pool=pool, rows=rows) for ed in ("workroom", "amp", "maxine")],
        "message": plan_block
        or warning
        or bilingual(
            "Medidor MiniMax por edición (0700/0600). Max-e y Maxine: 20% cada una del cupo de texto "
            "(igual que INSTANCE_USAGE_CAP_PCT). Sin tope combinado. Si remains no responde, se bloquea. "
            "Apaga Auto credit usage.",
            "Per-edition MiniMax meter (0700/0600). Max-e and Maxine: 20% each of the text pool "
            "(same as INSTANCE_USAGE_CAP_PCT). No combined family cap. If remains is down, we block. "
            "Turn off Auto credit usage.",
        ),
    }


def edition_public_summary(edition: Optional[str] = None) -> dict[str, Any]:
    """This edition only — reads only that edition's file."""
    ed = normalize_edition(edition or current_edition())
    now = _now()
    day = now.strftime("%Y-%m-%d")
    month = now.strftime("%Y-%m")
    week = _iso_week(now)
    handle = _with_exclusive_lock()
    try:
        mine = _read_records_unlocked(edition=ed)
        all_rows = _read_records_unlocked(aggregator=True) if not is_family(ed) else mine
    finally:
        handle.close()
    pool = _pool_tokens(month, all_rows if not is_family(ed) else mine)
    view = _edition_view(ed, day=day, week=week, month=month, pool=pool, rows=mine)
    return {
        "enforced": True,
        "edition": ed,
        "text_share_pct": view["text_share_pct"],
        "text_cap_pct": view["text_cap_pct"],
        "images_today": view["images_today"],
        "image_daily_cap": view["image_daily_cap"],
        "tts_today": view["tts_today"],
        "tts_daily_cap": view["tts_daily_cap"],
        "video_this_week": view["video_this_week"],
        "video_weekly_cap": view["video_weekly_cap"],
        "family_tts_enabled": family_tts_enabled(),
        "h3_enabled": h3_enabled(),
        "plan_hard_stopped": bool(plan_hard_stopped(kind="text", edition=ed, rows=mine)),
        "message": bilingual(
            f"Esta edición puede usar el {view['text_cap_pct']:g}% del cupo de texto MiniMax. "
            f"Imágenes: {view['images_today']}/{view['image_daily_cap']} hoy. "
            f"Voz: {view['tts_today']}/{view['tts_daily_cap']} hoy.",
            f"This edition may use {view['text_cap_pct']:g}% of the MiniMax text pool. "
            f"Images: {view['images_today']}/{view['image_daily_cap']} today. "
            f"Voice: {view['tts_today']}/{view['tts_daily_cap']} today.",
        ),
    }


def file_modes(edition: Optional[str] = None) -> dict[str, int]:
    """Test helper: directory and log permission bits."""
    ed = normalize_edition(edition or current_edition())
    d = edition_dir(ed)
    p = log_path(ed)
    if not p.exists():
        p.touch()
        _chmod(p, 0o600)
    return {
        "dir": stat.S_IMODE(d.stat().st_mode),
        "file": stat.S_IMODE(p.stat().st_mode),
    }
