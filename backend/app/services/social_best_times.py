"""SocialForge best-time-to-post suggestions from engagement history.

Uses posted-at + engagement when enough samples exist. Falls back to
sane industry defaults for luxury / home-decor accounts when data is thin.
Pure function — no I/O, no live network.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any, Iterable, Optional


WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

# Industry defaults (local time). Tuned for home-decor / luxury service brands.
DEFAULT_WINDOWS: dict[str, list[dict[str, Any]]] = {
    "instagram": [
        {"weekday": "Wednesday", "hour": 11, "score": 0.86},
        {"weekday": "Friday", "hour": 10, "score": 0.82},
        {"weekday": "Thursday", "hour": 14, "score": 0.78},
    ],
    "facebook": [
        {"weekday": "Wednesday", "hour": 13, "score": 0.84},
        {"weekday": "Thursday", "hour": 11, "score": 0.80},
        {"weekday": "Friday", "hour": 9, "score": 0.74},
    ],
    "pinterest": [
        {"weekday": "Saturday", "hour": 20, "score": 0.88},
        {"weekday": "Sunday", "hour": 21, "score": 0.84},
        {"weekday": "Friday", "hour": 15, "score": 0.76},
    ],
    "linkedin": [
        {"weekday": "Tuesday", "hour": 8, "score": 0.86},
        {"weekday": "Wednesday", "hour": 9, "score": 0.82},
        {"weekday": "Thursday", "hour": 10, "score": 0.78},
    ],
    "tiktok": [
        {"weekday": "Tuesday", "hour": 19, "score": 0.84},
        {"weekday": "Thursday", "hour": 19, "score": 0.82},
        {"weekday": "Friday", "hour": 17, "score": 0.76},
    ],
    "x": [
        {"weekday": "Wednesday", "hour": 9, "score": 0.80},
        {"weekday": "Tuesday", "hour": 10, "score": 0.76},
        {"weekday": "Thursday", "hour": 12, "score": 0.72},
    ],
}

_GENERIC_DEFAULTS = [
    {"weekday": "Tuesday", "hour": 10, "score": 0.80},
    {"weekday": "Wednesday", "hour": 11, "score": 0.78},
    {"weekday": "Thursday", "hour": 13, "score": 0.74},
]

# Need this many posted samples with timestamps before history overrides defaults.
MIN_HISTORY_POSTS = 5
# A (weekday, hour) bucket needs this many posts to rank above a default.
MIN_BUCKET_POSTS = 2


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def engagement_score(engagement: Any) -> float:
    """Weighted engagement. Comments and shares count more than likes."""
    if not isinstance(engagement, dict):
        return 0.0
    likes = float(engagement.get("likes") or 0)
    comments = float(engagement.get("comments") or 0)
    shares = float(engagement.get("shares") or 0)
    reach = float(engagement.get("reach") or 0)
    return likes + comments * 2.0 + shares * 3.0 + reach * 0.01


def _label(weekday: str, hour: int) -> str:
    suffix = "AM" if hour < 12 else "PM"
    display = hour if hour == 0 or hour == 12 else hour % 12
    if hour == 0:
        display = 12
    return f"{weekday[:3]} {display}:00 {suffix}"


def _decorate(slot: dict[str, Any], source: str) -> dict[str, Any]:
    weekday = slot["weekday"]
    hour = int(slot["hour"])
    return {
        "weekday": weekday,
        "weekday_index": WEEKDAYS.index(weekday) if weekday in WEEKDAYS else 0,
        "hour": hour,
        "label": _label(weekday, hour),
        "score": round(float(slot.get("score") or 0), 4),
        "source": source,
        "sample_size": int(slot.get("sample_size") or 0),
    }


def default_windows(platform: Optional[str] = None) -> list[dict[str, Any]]:
    key = (platform or "").strip().lower()
    raw = DEFAULT_WINDOWS.get(key) or _GENERIC_DEFAULTS
    return [_decorate(slot, "default") for slot in raw]


def suggest_best_times(
    posts: Iterable[dict[str, Any]],
    platform: Optional[str] = None,
    limit: int = 3,
) -> dict[str, Any]:
    """Return ranked posting windows for a platform.

    History is used only when enough posted samples have timestamps.
    Otherwise (or as fill) the industry defaults are returned.
    """
    platform_key = (platform or "").strip().lower() or None
    posted: list[dict[str, Any]] = []
    for post in posts:
        if not isinstance(post, dict):
            continue
        if platform_key and (post.get("platform") or "").strip().lower() != platform_key:
            continue
        status = (post.get("status") or "").strip().lower()
        if status and status not in {"posted", "published"}:
            continue
        when = _parse_dt(post.get("posted_at") or post.get("scheduled_for") or post.get("created_at"))
        if when is None:
            continue
        posted.append({"when": when, "score": engagement_score(post.get("engagement"))})

    defaults = default_windows(platform_key)
    used_defaults = True
    suggestions: list[dict[str, Any]] = []

    if len(posted) >= MIN_HISTORY_POSTS:
        buckets: dict[tuple[str, int], list[float]] = defaultdict(list)
        for item in posted:
            when: datetime = item["when"]
            buckets[(WEEKDAYS[when.weekday()], when.hour)].append(item["score"])

        ranked = []
        for (weekday, hour), scores in buckets.items():
            if len(scores) < MIN_BUCKET_POSTS:
                continue
            ranked.append({
                "weekday": weekday,
                "hour": hour,
                "score": sum(scores) / len(scores),
                "sample_size": len(scores),
            })
        ranked.sort(key=lambda s: (s["score"], s["sample_size"]), reverse=True)
        if ranked:
            used_defaults = False
            suggestions = [_decorate(slot, "history") for slot in ranked[:limit]]

    if len(suggestions) < limit:
        seen = {(s["weekday"], s["hour"]) for s in suggestions}
        for slot in defaults:
            key = (slot["weekday"], slot["hour"])
            if key in seen:
                continue
            suggestions.append(slot)
            seen.add(key)
            if len(suggestions) >= limit:
                break

    return {
        "platform": platform_key or "all",
        "used_defaults": used_defaults,
        "history_posts": len(posted),
        "min_history_posts": MIN_HISTORY_POSTS,
        "suggestions": suggestions[:limit],
        "note": (
            "Industry defaults for luxury / home-decor accounts — not enough engagement history yet."
            if used_defaults
            else "Ranked from your posted engagement history."
        ),
    }
