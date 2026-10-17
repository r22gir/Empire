"""Per-instance LLM usage cap for family editions.

How the 20% is computed
-----------------------
Each family instance (EMPIRE_EDITION=amp, maxine, …) records its own
calls: input tokens, output tokens, and an estimated USD cost, rolled
up by UTC day and calendar month in ``EMPIRE_DATA_DIR/usage/usage.db``.

The cap means this instance may use **at most**
``INSTANCE_USAGE_CAP_PCT`` of EmpireBox's measured AI use for the
month (default 20). Public percentages are shares of that total pie,
not "percent of the 20% slice":

    used_percent      = instance_used / baseline × 100
    remaining_percent = max(0, cap_percent − used_percent)

So ``used_percent=13.1``, ``cap_percent=20``, ``remaining_percent=6.9``
means Max-e has used 13.1% of EmpireBox total and may use 6.9% more
before hitting the 20% cap. A reading of ``used_percent=65.7`` next
to ``cap_percent=20`` was the old (wrong) "percent of allowance"
meter and must not come back.

Internal enforcement still uses an allowance:

    allowance = INSTANCE_USAGE_CAP_PCT / 100 * baseline

``INSTANCE_USAGE_CAP_PCT`` defaults to 20 on family editions. The cap
is enforced with no baseline env. Baseline, first match wins:

1. ``EMPIRE_USAGE_BASELINE_MONTHLY_USD`` — optional invoice override.
   ``used`` is this instance's estimated USD.
2. ``EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS`` — optional token override.
   ``used`` is this instance's tokens.
3. Auto: sum of recorded tokens this UTC month across every readable
   edition ``usage/usage.db`` (this instance, ``/data/amp``,
   ``/data/maxine``, Workroom ``backend/data``, and
   ``EMPIRE_USAGE_PEER_DATA_DIRS``). All providers in those files
   count. The baseline is ``max(recorded_total, default_floor)``.
   The floor (``EMPIRE_USAGE_DEFAULT_BASELINE_TOKENS``, default
   10_000_000) covers a cold month so 20% is a real allowance.
   Workroom often writes no ``usage.db``: ``data_root_or_none()`` is
   ``None`` when ``EMPIRE_DATA_DIR`` is unset, so Workroom is absent
   from the pie and the floor applies until other edition files have
   more than 10M tokens this month.

USD for display and for case 1 is:

    tokens / 1_000_000 * MINIMAX_USD_PER_MILLION_TOKENS

``level`` is compared to the **base** cap (20) as a share of total.
The old hard wall is replaced by a Rafael-aware soft cap:

- ``ok``      — ``used_percent`` < 80% of ``cap_percent`` (under 16 when cap is 20)
- ``warn``    — at least 80% of the cap, still under the cap
- ``overage`` — over the base cap, Studio signal allows extra, under the absolute max
- ``paused``  — over the base cap and extra is not allowed (Rafael active,
  reserve low, stale/missing signal, or past ``FAMILY_ABSOLUTE_MAX_PCT``)
- ``blocked`` — only ``total_spend_hit`` (this instance used the whole baseline)

Overage is allowlisted: only Juan's web chat, voice, and a
user-initiated Pedir a Cursor request may use extra. Any ``desk=``
call, empty source, or unknown source is background and never gets
overage. Missing / stale / malformed founder signal fail closed.

``GET /api/v1/edition/usage`` is ``public_usage_summary()``: used
percent of EmpireBox total, remaining percent until the cap, level,
and the Spanish message. It does not include baseline, allowance, or
absolute token/cost totals (those would reveal EmpireBox-wide usage).
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

HEAVY_KINDS = frozenset({"job", "generate", "desk_task", "vision", "social", "heavy", "cursor_request"})
BACKGROUND_KINDS = frozenset({"desk_task", "job", "generate", "social"})
# Overage allowlist: named interactive sources only. Empty / unknown / desk = background.
# dashboard is the old Command Center default; interactive only when desk is unset.
INTERACTIVE_SOURCES = frozenset({"web", "web_cc", "voice", "voice_live", "dashboard"})
INTERACTIVE_CURSOR_SOURCES = frozenset({"", "web", "web_cc", "user", "owner", "cursor_request"})
DEFAULT_BASELINE_MONTHLY_TOKENS = 10_000_000.0
MENSAJE_OVERAGE = (
    "Manito, ya pasaste tu 20% del mes. Sigues con tiempo extra "
    "mientras Rafael no está usando Max."
)
MENSAJE_PAUSED = (
    "Manito, ya usaste tu 20% del mes y Rafael está usando Max ahora, "
    "así que lo extra queda en pausa. Vuelve a intentar en un rato."
)
MENSAJE_PAUSED_SIGNAL = (
    "Manito, ya usaste tu 20% del mes y no hay señal de Rafael, "
    "así que lo extra queda en pausa. Vuelve a intentar en un rato."
)
MENSAJE_PAUSED_STALE = (
    "Manito, ya usaste tu 20% del mes y la señal de Rafael está vieja, "
    "así que lo extra queda en pausa. Vuelve a intentar en un rato."
)
MENSAJE_PAUSED_RESERVE = (
    "Manito, ya usaste tu 20% del mes y la reserva de Rafael está baja, "
    "así que lo extra queda en pausa."
)
MENSAJE_PAUSED_REMAINS = (
    "Manito, ya usaste tu 20% del mes y no puedo leer el saldo de Max ahora, "
    "así que lo extra queda en pausa. Vuelve a intentar en un rato."
)
METER_OVERAGE_ES = "Tiempo extra (Rafael no está)"
METER_PAUSED_ES = "En pausa: Rafael está usando Max"
METER_PAUSED_SIGNAL_ES = "En pausa: no hay señal de Rafael"
METER_PAUSED_RESERVE_ES = "En pausa: la reserva de Rafael está baja"
METER_PAUSED_REMAINS_ES = "En pausa: no puedo leer el saldo de Max"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _env_absolute_max_percent() -> float:
    raw = os.getenv("FAMILY_ABSOLUTE_MAX_PCT", "").strip() or "40"
    try:
        value = float(raw)
    except ValueError:
        value = 40.0
    return max(cap_percent(), value)


def absolute_max_percent() -> float:
    """Safety ceiling above the base 20%. Env default 40; signal may lower it."""
    env_ceiling = _env_absolute_max_percent()
    from app.services.founder_signal import read_founder_signal

    signal = read_founder_signal()
    extra = signal.get("brother_ceiling_pct")
    if isinstance(extra, (int, float)) and not isinstance(extra, bool) and extra > 0:
        return max(cap_percent(), min(env_ceiling, float(extra)))
    return env_ceiling


def family_overage_allowed(used_percent: Optional[float] = None) -> bool:
    """True when Studio's signal allows extra AND the edition is under the ceiling.

    Name is stable for briefs 2a / 7a. Fail closed on a missing signal.
    """
    from app.edition import is_family_edition
    from app.services.founder_signal import read_founder_signal

    if not is_family_edition():
        return False
    signal = read_founder_signal()
    if not signal.get("overage_allowed"):
        return False
    if used_percent is None:
        used_percent = _used_percent()
    if used_percent is None:
        return False
    return float(used_percent) < absolute_max_percent()


def is_interactive_request(*, kind: str = "", source: str = "", desk: Optional[str] = None) -> bool:
    """True only for named interactive sources. Desk / empty / unknown are not."""
    if desk:
        return False
    src = (source or "").strip().lower()
    k = (kind or "").strip().lower()
    if k == "cursor_request" and src in INTERACTIVE_CURSOR_SOURCES:
        return True
    return src in INTERACTIVE_SOURCES


def is_background_request(*, kind: str = "", source: str = "", desk: Optional[str] = None) -> bool:
    if desk:
        return True
    labels = {(kind or "").strip().lower(), (source or "").strip().lower()}
    if labels & BACKGROUND_KINDS:
        return True
    src = (source or "").strip().lower()
    if "scheduler" in src or src.startswith("event:"):
        return True
    return not is_interactive_request(kind=kind, source=source, desk=desk)


def paused_reason_and_message(used_percent: Optional[float] = None) -> tuple[str, str]:
    """Spanish manito copy that names why extra time is paused."""
    from app.services.founder_signal import read_founder_signal

    signal = read_founder_signal()
    ceiling = absolute_max_percent()
    used = used_percent if used_percent is not None else _used_percent()
    if used is not None and float(used) >= ceiling:
        label = f"{ceiling:g}"
        return (
            "ceiling",
            f"Manito, ya llegaste al tope extra del {label}% de este mes. "
            "Ahí se acaba el tiempo extra.",
        )
    reason = str(signal.get("reason") or "")
    if reason == "stale":
        return "signal_stale", MENSAJE_PAUSED_STALE
    if reason in {"missing", "malformed"} or not signal.get("valid"):
        return "signal_missing", MENSAJE_PAUSED_SIGNAL
    if reason == "founder_active" or signal.get("founder_active"):
        return "founder_active", MENSAJE_PAUSED
    if reason in {"remains_unavailable", "remains_stale"}:
        return "remains_unavailable", MENSAJE_PAUSED_REMAINS
    if reason == "reserve_low" or signal.get("reserve_ok") is False:
        return "reserve_low", MENSAJE_PAUSED_RESERVE
    return "signal_missing", MENSAJE_PAUSED_SIGNAL


def meter_label_for_reason(reason: str) -> str:
    if reason == "ceiling":
        return f"En pausa: llegaste al tope extra ({absolute_max_percent():g}%)"
    if reason in {"signal_missing", "signal_stale"}:
        return METER_PAUSED_SIGNAL_ES
    if reason == "reserve_low":
        return METER_PAUSED_RESERVE_ES
    if reason == "remains_unavailable":
        return METER_PAUSED_REMAINS_ES
    return METER_PAUSED_ES


def cap_percent() -> float:
    raw = os.getenv("INSTANCE_USAGE_CAP_PCT", "").strip()
    if not raw:
        from app.edition import is_family_edition
        raw = "20" if is_family_edition() else "100"
    try:
        value = float(raw)
    except ValueError:
        value = 20.0
    return max(0.0, value)


def usd_per_million() -> float:
    raw = os.getenv("MINIMAX_USD_PER_MILLION_TOKENS", "0.30").strip() or "0.30"
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 0.30


def short_reply_chars() -> int:
    raw = os.getenv("INSTANCE_SHORT_REPLY_CHARS", "400").strip() or "400"
    try:
        return max(1, int(raw))
    except ValueError:
        return 400


def default_baseline_tokens() -> float:
    raw = os.getenv("EMPIRE_USAGE_DEFAULT_BASELINE_TOKENS", "").strip()
    if raw:
        try:
            return max(0.0, float(raw))
        except ValueError:
            pass
    return DEFAULT_BASELINE_MONTHLY_TOKENS


def _env_baseline() -> tuple[str, Optional[float]]:
    usd = os.getenv("EMPIRE_USAGE_BASELINE_MONTHLY_USD", "").strip()
    if usd:
        try:
            return "usd", float(usd)
        except ValueError:
            pass
    tokens = os.getenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", "").strip()
    if tokens:
        try:
            return "tokens", float(tokens)
        except ValueError:
            pass
    return "none", None


def _usage_data_roots():
    """Edition data roots that may hold a usage.db for the EmpireBox total."""
    from pathlib import Path

    from app.edition import EDITION_PROFILES, data_root_or_none

    seen: set[str] = set()
    roots = []

    def add(raw) -> None:
        if not raw:
            return
        path = Path(str(raw)).expanduser()
        try:
            resolved = str(path.resolve())
        except OSError:
            resolved = str(path)
        if resolved in seen:
            return
        seen.add(resolved)
        roots.append(path)

    add(data_root_or_none())
    for profile in EDITION_PROFILES.values():
        add(profile.get("data_dir"))
    add(os.getenv("EMPIRE_WORKROOM_DATA_DIR", "").strip())
    try:
        from app.services.data_paths import backend_root, data_root
        add(data_root())
        add(backend_root() / "data")
    except Exception:
        pass
    add(Path.home() / "empire-repo" / "backend" / "data")
    for part in os.getenv("EMPIRE_USAGE_PEER_DATA_DIRS", "").split(","):
        add(part.strip())
    return roots


def _month_totals_from_db(path, month: str) -> dict:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return _period_totals(conn, "month", month)
    finally:
        conn.close()


def recorded_usage_across_editions(month: Optional[str] = None) -> dict:
    """Sum recorded (unblocked) usage this month across edition usage DBs."""
    from pathlib import Path

    month = month or _now().strftime("%Y-%m")
    tokens = 0
    cost = 0.0
    files = []
    for root in _usage_data_roots():
        db = Path(root) / "usage" / "usage.db"
        if not db.is_file():
            continue
        try:
            totals = _month_totals_from_db(db, month)
        except Exception:
            continue
        tokens += int(totals["tokens"])
        cost += float(totals["cost_usd"])
        files.append(str(db))
    return {
        "month": month,
        "tokens": tokens,
        "cost_usd": round(cost, 6),
        "files": files,
    }


def _baseline() -> tuple[str, float]:
    """Return (basis, baseline). Family editions always get a number."""
    kind, value = _env_baseline()
    if value is not None:
        return kind, float(value)
    recorded = recorded_usage_across_editions()
    floor = default_baseline_tokens()
    return "recorded_tokens", max(float(recorded["tokens"]), floor)


def usage_db_path():
    from app.edition import data_root_or_none, is_family_edition, require_data_root

    if is_family_edition():
        root = require_data_root()
    else:
        root = data_root_or_none()
        if root is None:
            return None
    folder = root / "usage"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "usage.db"


def _connect():
    path = usage_db_path()
    if path is None:
        return None
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            day TEXT NOT NULL,
            month TEXT NOT NULL,
            model TEXT,
            provider TEXT,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cost_usd REAL NOT NULL DEFAULT 0,
            kind TEXT,
            blocked INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_usage_month ON llm_usage(month)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_usage_day ON llm_usage(day)")
    return conn


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    tokens = max(0, int(input_tokens)) + max(0, int(output_tokens))
    return round(tokens / 1_000_000 * usd_per_million(), 8)


def record_usage(
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    model: str = "MiniMax-M3",
    provider: str = "minimax",
    kind: str = "chat",
    blocked: bool = False,
    cost_usd: Optional[float] = None,
) -> None:
    conn = _connect()
    if conn is None:
        return
    now = _now()
    cost = estimate_cost(input_tokens, output_tokens) if cost_usd is None else float(cost_usd)
    try:
        conn.execute(
            """
            INSERT INTO llm_usage (
                created_at, day, month, model, provider,
                input_tokens, output_tokens, cost_usd, kind, blocked
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                now.isoformat(),
                now.strftime("%Y-%m-%d"),
                now.strftime("%Y-%m"),
                model,
                provider,
                int(input_tokens),
                int(output_tokens),
                cost,
                kind,
                1 if blocked else 0,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _period_totals(conn, column: str, value: str) -> dict:
    row = conn.execute(
        f"""
        SELECT
            COALESCE(SUM(input_tokens), 0) AS input_tokens,
            COALESCE(SUM(output_tokens), 0) AS output_tokens,
            COALESCE(SUM(cost_usd), 0) AS cost_usd
        FROM llm_usage
        WHERE {column} = ? AND blocked = 0
        """,
        (value,),
    ).fetchone()
    tokens = int(row["input_tokens"]) + int(row["output_tokens"])
    return {
        "input_tokens": int(row["input_tokens"]),
        "output_tokens": int(row["output_tokens"]),
        "tokens": tokens,
        "cost_usd": round(float(row["cost_usd"]), 6),
    }


def _used_percent() -> Optional[float]:
    """This instance's share of the baseline pie. No level / signal logic."""
    from app.edition import is_family_edition

    if not is_family_edition():
        return None
    basis, baseline = _baseline()
    if not baseline or float(baseline) <= 0:
        return 0.0
    conn = _connect()
    if conn is None:
        return 0.0
    try:
        month = _period_totals(conn, "month", _now().strftime("%Y-%m"))
    finally:
        conn.close()
    used = month["cost_usd"] if basis == "usd" else float(month["tokens"])
    return round(used / float(baseline) * 100.0, 1)


def usage_summary() -> dict:
    from app.edition import edition_name, is_family_edition

    now = _now()
    family = is_family_edition()
    pct = cap_percent()
    basis, baseline = _baseline() if family else ("none", None)
    allowance = None if baseline is None else round(float(baseline) * pct / 100.0, 6)
    empty = {
        "enforced": bool(family and allowance is not None),
        "edition": edition_name(),
        "model": "MiniMax-M3",
        "provider": "minimax",
        "cap_percent": pct,
        "baseline_basis": basis,
        "baseline": baseline,
        "allowance": allowance,
        "day": {"tokens": 0, "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0},
        "month": {"tokens": 0, "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0},
        "used": 0.0,
        "used_percent": 0.0 if family else None,
        "ratio": None,
        "remaining_percent": pct if family else None,
        "total_spend_hit": False,
        "level": "ok",
        "message": "",
        "paused_reason": "",
        "limit_note_es": (
            f"Tu uso está limitado al {pct:g}% del uso total de MiniMax."
            if family else ""
        ),
    }
    conn = _connect()
    if conn is None:
        return empty
    try:
        day = _period_totals(conn, "day", now.strftime("%Y-%m-%d"))
        month = _period_totals(conn, "month", now.strftime("%Y-%m"))
    finally:
        conn.close()
    used = month["cost_usd"] if basis == "usd" else float(month["tokens"])
    ratio = None
    remaining_percent = pct if family else None
    used_percent = 0.0 if family else None
    level = "ok"
    message = ""
    pause_reason = ""
    total_spend_hit = bool(baseline is not None and baseline > 0 and used >= float(baseline))
    if baseline and float(baseline) > 0 and family:
        # Public meter: share of EmpireBox total, not share of the 20% slice.
        share = used / float(baseline)
        ratio = round(share, 4)
        used_percent = round(share * 100.0, 1)
        remaining_percent = max(0.0, round(pct - used_percent, 1))
        warn_at = pct * 0.8
        if total_spend_hit:
            level = "blocked"
            message = (
                "Llegamos al tope total de uso de EmpireBox este mes. "
                "También los mensajes cortos quedan en pausa."
            )
        elif used_percent >= pct:
            extra_ok = family_overage_allowed(used_percent)
            if extra_ok:
                level = "overage"
                message = MENSAJE_OVERAGE
            else:
                level = "paused"
                pause_reason, message = paused_reason_and_message(used_percent)
        elif used_percent >= warn_at:
            level = "warn"
            message = (
                f"Esta instancia ya usó el {used_percent:g}% del uso total "
                f"de EmpireBox este mes. El tope es el {pct:g}%. "
                f"Queda el {remaining_percent:g}% del total antes del tope."
            )
        else:
            message = (
                f"Esta instancia ha usado el {used_percent:g}% del uso total "
                f"de EmpireBox este mes. El tope es el {pct:g}%. "
                f"Queda el {remaining_percent:g}% del total."
            )
    empty.update({
        "day": day,
        "month": month,
        "used": used,
        "used_percent": used_percent,
        "ratio": ratio,
        "remaining_percent": remaining_percent,
        "total_spend_hit": total_spend_hit,
        "level": level,
        "message": message,
        "paused_reason": pause_reason if level == "paused" else "",
    })
    return empty


PUBLIC_USAGE_KEYS = (
    "enforced",
    "edition",
    "cap_percent",
    "used_percent",
    "remaining_percent",
    "level",
    "message",
    "limit_note_es",
    "overage_active",
)


def public_usage_summary() -> dict:
    """Owner-facing meter. Percentages only — no EmpireBox-wide totals.

    used_percent is this instance's share of EmpireBox total (the pie).
    remaining_percent is how much of that pie is left before the cap.
    cap_percent is the maximum share this instance may use (default 20).
    """
    summary = usage_summary()
    public = {key: summary.get(key) for key in PUBLIC_USAGE_KEYS}
    public["overage_active"] = summary.get("level") == "overage"
    if summary.get("level") == "overage":
        public["meter_label_es"] = METER_OVERAGE_ES
    elif summary.get("level") == "paused":
        public["meter_label_es"] = meter_label_for_reason(summary.get("paused_reason") or "")
    else:
        public["meter_label_es"] = ""
    return public


def is_heavy_request(*, kind: str, text: str, desk: Optional[str], tools: bool, source: str, image: bool) -> bool:
    if image or tools or desk:
        return True
    labels = {(kind or "").strip().lower(), (source or "").strip().lower()}
    if labels & HEAVY_KINDS:
        return True
    return len(text or "") > short_reply_chars()


def enforce_usage_cap(
    *,
    kind: str = "chat",
    text: str = "",
    desk: Optional[str] = None,
    tools: bool = False,
    source: str = "",
    image: bool = False,
) -> Optional[str]:
    """Refuse over-base background always; interactive only when overage is allowed."""
    from app.edition import is_family_edition

    if not is_family_edition():
        return None
    summary = usage_summary()
    if summary.get("total_spend_hit"):
        return summary["message"]
    used = summary.get("used_percent")
    pct = summary.get("cap_percent") or cap_percent()
    if used is None or float(used) < float(pct):
        return None
    # Over the base 20%. Only named interactive sources may use overage.
    if is_background_request(kind=kind, source=source, desk=desk):
        return summary["message"]
    if family_overage_allowed(used):
        return None
    return summary["message"]
