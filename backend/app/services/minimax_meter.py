"""Shared MiniMax usage meter for Max, Max-e, and Maxine.

One append-only JSONL log. Every MiniMax call (text tokens, images, TTS
chars, video clips) is recorded with the edition that spent it. Caps:

* Max-e and Maxine each <= MINIMAX_EDITION_TEXT_SHARE_PCT of the text
  pool (default 10). Together they stay under MINIMAX_FAMILY_TEXT_SHARE_PCT
  (default 20). The existing INSTANCE_USAGE_CAP_PCT=20 checker still runs.
* Rafael's personal Max keeps MINIMAX_RESERVED_SHARE_PCT (default 80).
* Per edition per UTC day: MINIMAX_IMAGE_DAILY_CAP images (default 5)
  and MINIMAX_TTS_DAILY_CAP short TTS replies (default 20).
* Video: MINIMAX_VIDEO_WEEKLY_CAP clip/week (default 1) and only with
  Rafael's explicit approval.
* All agents hard-stop near MINIMAX_PLAN_HARD_STOP_PCT of the plan bar
  (default 80) when /v1/token_plan/remains is available. Gift credits
  are never treated as room.

Block. Do not overflow into credits. Messages are Spanish + English.
"""
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("max.minimax_meter")

FAMILY_EDITIONS = frozenset({"amp", "maxine"})
FOUNDER_EDITIONS = frozenset({"workroom", "main", ""})
KINDS = frozenset({"text", "image", "tts", "video", "web_search"})

DEFAULT_EDITION_TEXT_SHARE_PCT = 10.0
DEFAULT_FAMILY_TEXT_SHARE_PCT = 20.0
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


class MeterBlocked(Exception):
    """Call must not proceed. ``message`` is bilingual user text."""

    def __init__(self, message: str, *, code: str = "blocked"):
        super().__init__(message)
        self.message = message
        self.code = code


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


def family_text_share_pct() -> float:
    return _float_env("MINIMAX_FAMILY_TEXT_SHARE_PCT", DEFAULT_FAMILY_TEXT_SHARE_PCT)


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
    return (os.getenv("MINIMAX_FAMILY_TTS") or "").strip() in {"1", "true", "yes", "on"}


def h3_enabled() -> bool:
    raw = (os.getenv("MINIMAX_H3_ENABLED") or os.getenv("MINIMAX_VIDEO_ENABLED") or "").strip()
    return raw in {"1", "true", "yes", "on"}


def h3_model() -> str:
    return (os.getenv("MINIMAX_H3_MODEL") or os.getenv("MINIMAX_VIDEO_MODEL") or "MiniMax-Hailuo-02").strip()


def current_edition() -> str:
    from app.edition import edition_name

    return edition_name()


def is_family(edition: Optional[str] = None) -> bool:
    return (edition or current_edition()) in FAMILY_EDITIONS


def redact(text: str) -> str:
    if not text:
        return ""
    out = _KEY_RE.sub("[KEY_REDACTED]", str(text))
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
        return path
    default = Path("/data/minimax-meter")
    try:
        default.mkdir(parents=True, exist_ok=True)
        if os.access(default, os.W_OK):
            return default
    except OSError:
        pass
    from app.edition import data_root_or_none, is_family_edition

    root = data_root_or_none()
    if root is not None:
        path = Path(root) / "minimax-meter"
        path.mkdir(parents=True, exist_ok=True)
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
    return fallback


def log_path() -> Path:
    return meter_dir() / "calls.jsonl"


def _lock_path() -> Path:
    return meter_dir() / "calls.lock"


def _with_lock(write: bool = False):
    import fcntl

    path = _lock_path()
    flags = fcntl.LOCK_EX if write else fcntl.LOCK_SH
    handle = open(path, "a+", encoding="utf-8")
    fcntl.flock(handle.fileno(), flags)
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
    if rec.get("blocked"):
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


def _read_records() -> list[dict[str, Any]]:
    path = log_path()
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    handle = _with_lock(False)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                text = line.strip()
                if not text:
                    continue
                try:
                    rec = json.loads(text)
                except json.JSONDecodeError:
                    continue
                if isinstance(rec, dict):
                    rows.append(rec)
    finally:
        handle.close()
    return rows


def append_record(rec: dict[str, Any]) -> dict[str, Any]:
    """Append one JSON object. Never writes the API key."""
    payload = dict(rec)
    payload.setdefault("id", uuid.uuid4().hex[:12])
    payload.setdefault("ts", _iso())
    payload["edition"] = str(payload.get("edition") or current_edition())
    payload["kind"] = str(payload.get("kind") or "text")
    for key in ("model", "reason", "approval_id"):
        if key in payload and payload[key] is not None:
            payload[key] = redact(str(payload[key]))[:300]
    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    key = os.getenv("MINIMAX_API_KEY") or ""
    if key and key in line:
        line = line.replace(key, "[KEY_REDACTED]")
    line = redact(line)
    handle = _with_lock(True)
    try:
        with open(log_path(), "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    finally:
        handle.close()
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
) -> dict[str, Any]:
    out = _empty_totals()
    for rec in _read_records():
        if edition and rec.get("edition") != edition:
            continue
        if kind and rec.get("kind") != kind:
            continue
        if not _match_window(rec, day=day, week=week, month=month):
            continue
        _add(out, rec)
    return out


def _family_combined_tokens(month: str) -> int:
    tokens = 0
    for ed in FAMILY_EDITIONS:
        tokens += int(totals(edition=ed, month=month)["text_tokens"])
    return tokens


def _pool_tokens(month: str) -> float:
    return max(float(totals(month=month)["text_tokens"]), text_pool_floor())


def _plan_snapshot() -> dict[str, Any]:
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
        "para no gastar los créditos de regalo.",
        f"MiniMax plan cap: every agent stops at {stop:g}% of the usage bar "
        "so gift credits are not spent.",
    )


def plan_hard_stopped(snapshot: Optional[dict] = None) -> Optional[str]:
    snap = snapshot or _plan_snapshot()
    remains = snap.get("remains") or {}
    if not remains.get("available"):
        return None
    used = remains.get("used_pct")
    remaining = remains.get("remaining_pct")
    stop = plan_hard_stop_pct()
    if used is not None and float(used) >= stop:
        return _plan_block_message()
    if remaining is not None and float(remaining) <= max(0.0, 100.0 - stop):
        return _plan_block_message()
    return None


def _family_text_block(edition: str, add_tokens: int, month: str) -> Optional[str]:
    if edition not in FAMILY_EDITIONS:
        return None
    pool = _pool_tokens(month)
    mine = int(totals(edition=edition, month=month)["text_tokens"]) + max(0, add_tokens)
    family = _family_combined_tokens(month) + max(0, add_tokens)
    per = edition_text_share_pct()
    combined = family_text_share_pct()
    mine_pct = (mine / pool) * 100.0 if pool else 0.0
    family_pct = (family / pool) * 100.0 if pool else 0.0
    if mine_pct > per + 1e-9:
        return bilingual(
            f"Tope de esta edición: Max-e y Maxine pueden usar cada una el {per:g}% "
            f"del cupo de texto MiniMax. Esta edición ya iría al {mine_pct:.1f}%.",
            f"Edition cap: Max-e and Maxine may each use {per:g}% of the MiniMax "
            f"text pool. This edition would be at {mine_pct:.1f}%.",
        )
    if family_pct > combined + 1e-9:
        return bilingual(
            f"Tope familiar: Max-e y Maxine juntas se quedan bajo el {combined:g}% "
            f"del cupo de texto (el 20% existente). Juntas irían al {family_pct:.1f}%.",
            f"Family cap: Max-e and Maxine together stay under {combined:g}% of the "
            f"text pool (the existing 20%). Together they would be at {family_pct:.1f}%.",
        )
    reserved = reserved_share_pct()
    if family_pct > max(0.0, 100.0 - reserved) + 1e-9:
        return bilingual(
            f"La parte reservada de Rafael ({reserved:g}%) no se puede usar.",
            f"Rafael's reserved share ({reserved:g}%) cannot be used.",
        )
    return None


def _image_block(edition: str, add_images: int, day: str) -> Optional[str]:
    cap = image_daily_cap()
    used = int(totals(edition=edition, day=day, kind="image")["images"]) + max(0, add_images)
    if used > cap:
        return bilingual(
            f"Tope de imágenes: esta edición puede generar {cap} al día. Ya se usaría {used}.",
            f"Image cap: this edition may generate {cap} images per day. It would be {used}.",
        )
    return None


def _tts_block(edition: str, add_replies: int, day: str) -> Optional[str]:
    cap = tts_daily_cap()
    used = int(totals(edition=edition, day=day, kind="tts")["tts_replies"]) + max(0, add_replies)
    if used > cap:
        return bilingual(
            f"Tope de voz: esta edición puede hacer {cap} respuestas cortas de TTS al día.",
            f"Voice cap: this edition may make {cap} short TTS replies per day.",
        )
    return None


def _video_block(edition: str, add_clips: int, week: str) -> Optional[str]:
    cap = video_weekly_cap()
    used = int(totals(week=week, kind="video")["video_clips"]) + max(0, add_clips)
    if used > cap:
        return bilingual(
            f"Tope de video: {cap} clip por semana en todo el plan, y solo con la aprobación de Rafael.",
            f"Video cap: {cap} clip per week across the plan, and only with Rafael's approval.",
        )
    return None


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
) -> Optional[str]:
    """Return a bilingual refusal, or None if the call may proceed."""
    ed = edition or current_edition()
    kind = (kind or "text").strip().lower()
    now = _now()
    day = now.strftime("%Y-%m-%d")
    month = now.strftime("%Y-%m")
    week = _iso_week(now)

    plan_msg = plan_hard_stopped()
    if plan_msg:
        return plan_msg

    if kind == "text":
        add = max(0, int(input_tokens)) + max(0, int(output_tokens))
        return _family_text_block(ed, add or 1, month)
    if kind == "image":
        if ed in FAMILY_EDITIONS:
            text_msg = _family_text_block(ed, 0, month)
            if text_msg:
                return text_msg
            return _image_block(ed, max(1, int(images) or 1), day)
        return _image_block(ed, max(1, int(images) or 1), day)
    if kind == "tts":
        if ed in FAMILY_EDITIONS and not family_tts_enabled():
            return bilingual(
                "La voz MiniMax (speech-2.8) está apagada en esta edición (MINIMAX_FAMILY_TTS).",
                "MiniMax speech-2.8 voice is off for this edition (MINIMAX_FAMILY_TTS).",
            )
        chars = max(0, int(tts_chars))
        if ed in FAMILY_EDITIONS and chars > tts_max_chars():
            return bilingual(
                f"Esta respuesta de voz es demasiado larga (máx. {tts_max_chars()} caracteres).",
                f"This voice reply is too long (max {tts_max_chars()} characters).",
            )
        if ed not in FAMILY_EDITIONS:
            return None
        return _tts_block(ed, max(1, int(tts_replies) or 1), day)
    if kind == "video":
        if not h3_enabled():
            return bilingual(
                "El video H3 está apagado (MINIMAX_H3_ENABLED).",
                "H3 video is disabled (MINIMAX_H3_ENABLED).",
            )
        if not approval_id:
            return bilingual(
                "Cada clip H3 necesita la aprobación explícita de Rafael. Se guardó un borrador.",
                "Each H3 clip needs Rafael's explicit approval. A draft was saved.",
            )
        from app.services.minimax_video import approval_is_live

        if not approval_is_live(approval_id):
            return bilingual(
                "No hay una aprobación vigente de Rafael para este clip.",
                "There is no live approval from Rafael for this clip.",
            )
        return _video_block(ed, max(1, int(video_clips) or 1), week)
    return None


def enforce(**kwargs) -> Optional[str]:
    """Public cap check used by chat, tools, and TTS."""
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
    rec = {
        "edition": edition or current_edition(),
        "kind": kind,
        "model": model,
        "input_tokens": max(0, int(input_tokens)),
        "output_tokens": max(0, int(output_tokens)),
        "images": max(0, int(images)),
        "tts_chars": max(0, int(tts_chars)),
        "video_clips": max(0, int(video_clips)),
        "blocked": bool(blocked),
        "reason": reason,
        "approval_id": approval_id,
    }
    return append_record(rec)


def _edition_view(edition: str, *, day: str, week: str, month: str, pool: float) -> dict[str, Any]:
    month_tot = totals(edition=edition, month=month)
    day_tot = totals(edition=edition, day=day)
    week_tot = totals(edition=edition, week=week)
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
    """Full per-edition breakdown for Rafael's personal Max."""
    now = _now()
    day = now.strftime("%Y-%m-%d")
    month = now.strftime("%Y-%m")
    week = _iso_week(now)
    pool = _pool_tokens(month)
    family_tokens = _family_combined_tokens(month)
    family_pct = (family_tokens / pool) * 100.0 if pool else 0.0
    editions = ["workroom", "amp", "maxine"]
    plan = _plan_snapshot()
    plan_block = plan_hard_stopped(plan)
    return {
        "enforced": True,
        "month": month,
        "day": day,
        "week": week,
        "edition_text_share_pct": edition_text_share_pct(),
        "family_text_share_pct": family_text_share_pct(),
        "reserved_share_pct": reserved_share_pct(),
        "family_text_share_used_pct": round(family_pct, 2),
        "image_daily_cap": image_daily_cap(),
        "tts_daily_cap": tts_daily_cap(),
        "video_weekly_cap": video_weekly_cap(),
        "plan_hard_stop_pct": plan_hard_stop_pct(),
        "family_tts_enabled": family_tts_enabled(),
        "h3_enabled": h3_enabled(),
        "h3_model": h3_model(),
        "plan": {
            "available": bool((plan.get("remains") or {}).get("available")),
            "remaining_pct": (plan.get("remains") or {}).get("remaining_pct"),
            "used_pct": (plan.get("remains") or {}).get("used_pct"),
            "hard_stopped": bool(plan_block),
            "message": plan_block or "",
            "credits_known": bool((plan.get("credits") or {}).get("available")),
            "credits_not_spendable": True,
        },
        "editions": [_edition_view(ed, day=day, week=week, month=month, pool=pool) for ed in editions],
        "message": plan_block
        or bilingual(
            "Medidor MiniMax compartido. Max-e y Maxine 10% cada una; juntas bajo el 20%. "
            "No se gastan créditos de regalo.",
            "Shared MiniMax meter. Max-e and Maxine 10% each; together under 20%. "
            "Gift credits are not spent.",
        ),
    }


def edition_public_summary(edition: Optional[str] = None) -> dict[str, Any]:
    """This edition only — no EmpireBox-wide token totals."""
    ed = edition or current_edition()
    now = _now()
    day = now.strftime("%Y-%m-%d")
    month = now.strftime("%Y-%m")
    week = _iso_week(now)
    pool = _pool_tokens(month)
    view = _edition_view(ed, day=day, week=week, month=month, pool=pool)
    public = {
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
        "plan_hard_stopped": bool(plan_hard_stopped()),
        "message": bilingual(
            f"Esta edición puede usar el {view['text_cap_pct']:g}% del cupo de texto MiniMax. "
            f"Imágenes: {view['images_today']}/{view['image_daily_cap']} hoy. "
            f"Voz: {view['tts_today']}/{view['tts_daily_cap']} hoy.",
            f"This edition may use {view['text_cap_pct']:g}% of the MiniMax text pool. "
            f"Images: {view['images_today']}/{view['image_daily_cap']} today. "
            f"Voice: {view['tts_today']}/{view['tts_daily_cap']} today.",
        ),
    }
    return public
