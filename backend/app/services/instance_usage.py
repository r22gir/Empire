"""Per-instance LLM usage for family editions (Rafael-aware soft cap).

How the 20% is computed
-----------------------
Each family instance (EMPIRE_EDITION=amp, maxine, …) records its own
calls: input tokens, output tokens, and an estimated USD cost, rolled
up by UTC day and calendar month in ``EMPIRE_DATA_DIR/usage/usage.db``.

``cap_percent()`` is the **base** share (default 20). Public percentages
are shares of EmpireBox total, not "percent of the 20% slice":

    used_percent      = instance_used / baseline × 100
    remaining_percent = max(0, cap_percent − used_percent)

Past the 20% base a brother may keep going **only while Rafael is
inactive and Rafael's protected reserve is intact** (Studio signal at
``{EMPIRE_DATA_DIR}/founder-signal/status.json``). Missing/stale/malformed
signal fails closed. ``FAMILY_ABSOLUTE_MAX_PCT`` (default 40) is a hard
safety ceiling. Background jobs never use overage.

``level``:

- ``ok``      — under 80% of the base cap
- ``warn``    — at least 80% of the base, still under the base
- ``overage`` — over the base, Studio signal allows extra
- ``paused``  — over the base, extra not allowed (founder active / stale
                signal / absolute max)
- ``blocked`` — ``total_spend_hit`` (this instance used the whole baseline)

``GET /api/v1/edition/usage`` is ``public_usage_summary()``: percentages,
level, overage_active, Spanish message. No absolute token/cost totals.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

HEAVY_KINDS = frozenset({
    "job", "generate", "desk_task", "vision", "social", "heavy", "cursor_request",
})
# Overage is an allowlist: only Camilo's named interactive sources.
# Empty, unknown, desk=, scheduler, generate, etc. never get extra.
INTERACTIVE_OVERAGE_SOURCES = frozenset({
    "web", "web_cc", "chat", "voice", "owner", "cursor_request",
    "dashboard", "whatsapp",
})
DEFAULT_BASELINE_MONTHLY_TOKENS = 10_000_000.0
DEFAULT_ABSOLUTE_MAX_PCT = 40.0

MSG_OVERAGE = (
    "Manito, ya pasaste tu 20% del mes. Sigues con tiempo extra mientras "
    "Rafael no está usando Max."
)
MSG_PAUSED = (
    "Manito, ya usaste tu 20% del mes y Rafael está usando Max ahora, "
    "así que lo extra queda en pausa. Vuelve a intentar en un rato."
)
MSG_PAUSED_SIGNAL = (
    "Manito, ya usaste tu 20% del mes y no pude leer la señal de Rafael "
    "(falta o está vieja), así que lo extra queda en pausa. "
    "Vuelve a intentar en un rato."
)
MSG_PAUSED_RESERVE = (
    "Manito, ya usaste tu 20% del mes y la reserva de Rafael está baja, "
    "así que lo extra queda en pausa. Vuelve a intentar en un rato."
)
MSG_PAUSED_REMAINS = (
    "Manito, ya usaste tu 20% del mes y no puedo leer el saldo de Max ahora, "
    "así que lo extra queda en pausa. Vuelve a intentar en un rato."
)
MSG_BACKGROUND_OVERAGE = (
    "Manito, las tareas automáticas no corren en tiempo extra. "
    "Eso queda para tus chats."
)
MSG_ABSOLUTE = (
    "Manito, ya llegaste al tope extra del mes ({ceiling:g}%). "
    "Hay que esperar un rato."
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def cap_percent() -> float:
    """Base share (default 20 on family). Soft-cap overage is separate."""
    raw = os.getenv("INSTANCE_USAGE_CAP_PCT", "").strip()
    if not raw:
        from app.edition import is_family_edition
        raw = "20" if is_family_edition() else "100"
    try:
        value = float(raw)
    except ValueError:
        value = 20.0
    return max(0.0, value)


def _env_absolute_max_pct() -> float:
    raw = os.getenv("FAMILY_ABSOLUTE_MAX_PCT", "").strip()
    if raw:
        try:
            return max(cap_percent(), float(raw))
        except ValueError:
            pass
    return max(cap_percent(), DEFAULT_ABSOLUTE_MAX_PCT)


def _signal_ceiling_pct(signal: Optional[dict] = None) -> Optional[float]:
    if signal is None:
        try:
            from app.services.founder_signal import load_founder_signal
            signal = load_founder_signal()
        except Exception:
            return None
    raw = signal.get("brother_ceiling_pct") if signal else None
    if raw is None or raw == "":
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value <= 0 or value > 100:
        return None
    return value


def absolute_max_pct(*, signal: Optional[dict] = None) -> float:
    """Hard ceiling: env FAMILY_ABSOLUTE_MAX_PCT, optionally lowered by Studio."""
    env_ceiling = _env_absolute_max_pct()
    extra = _signal_ceiling_pct(signal)
    if extra is None:
        return env_ceiling
    return max(cap_percent(), min(env_ceiling, extra))


def paused_message(*, signal: Optional[dict] = None, used_percent: Optional[float] = None) -> str:
    """Spanish paused copy that names the real reason."""
    if signal is None:
        try:
            from app.services.founder_signal import load_founder_signal
            signal = load_founder_signal()
        except Exception:
            signal = {"ok": False, "reason": "missing"}
    ceiling = absolute_max_pct(signal=signal)
    if used_percent is not None and float(used_percent) >= ceiling:
        return MSG_ABSOLUTE.format(ceiling=ceiling)
    reason = str((signal or {}).get("reason") or "missing")
    if reason in {"remains_unavailable", "remains_stale"}:
        return MSG_PAUSED_REMAINS
    if not (signal or {}).get("ok"):
        return MSG_PAUSED_SIGNAL
    if (signal or {}).get("founder_active") or reason == "founder_active":
        return MSG_PAUSED
    if reason in {"reserve_low", "inputs_unreadable"} or not (signal or {}).get("reserve_ok"):
        return MSG_PAUSED_RESERVE
    return MSG_PAUSED_SIGNAL


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


def family_overage_allowed(*, used_percent: Optional[float] = None) -> bool:
    """True when extra use past the 20% base is allowed right now.

    Name is stable for briefs 2b/7b. Fail closed on a missing signal.
    """
    from app.edition import is_family_edition
    from app.services.founder_signal import load_founder_signal

    if not is_family_edition():
        return False
    signal = load_founder_signal()
    if not signal.get("overage_allowed"):
        return False
    pct = used_percent
    if pct is None:
        pct = _used_percent_now()
    if pct is None:
        return False
    if float(pct) >= absolute_max_pct(signal=signal):
        return False
    return True


def _used_percent_now() -> Optional[float]:
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


def is_background_request(*, kind: str, source: str, desk: Optional[str] = None) -> bool:
    """True unless this is a named interactive source with no desk.

    Desk tasks call ``ai_router.chat(desk=..., source='')`` as kind=chat.
    Any desk= value, empty source, or unknown source is background.
    """
    if desk:
        return True
    src = (source or "").strip().lower()
    kind_l = (kind or "").strip().lower()
    if src in INTERACTIVE_OVERAGE_SOURCES:
        return False
    if kind_l == "cursor_request":
        return False
    return True


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
        "overage_active": False,
        "overage_allowed": False,
        "level": "ok",
        "message": "",
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
    total_spend_hit = bool(baseline is not None and baseline > 0 and used >= float(baseline))
    if baseline and float(baseline) > 0 and family:
        # Public meter: share of EmpireBox total, not share of the 20% slice.
        share = used / float(baseline)
        ratio = round(share, 4)
        used_percent = round(share * 100.0, 1)
        remaining_percent = max(0.0, round(pct - used_percent, 1))
        warn_at = pct * 0.8
        from app.services.founder_signal import load_founder_signal
        signal = load_founder_signal()
        ceiling = absolute_max_pct(signal=signal)
        overage_ok = family_overage_allowed(used_percent=used_percent)
        if total_spend_hit:
            level = "blocked"
            message = (
                "Llegamos al tope total de uso de EmpireBox este mes. "
                "También los mensajes cortos quedan en pausa."
            )
        elif used_percent >= ceiling:
            level = "paused"
            message = paused_message(signal=signal, used_percent=used_percent)
        elif used_percent >= pct:
            if overage_ok:
                level = "overage"
                message = MSG_OVERAGE
            else:
                level = "paused"
                message = paused_message(signal=signal, used_percent=used_percent)
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
        "overage_active": level == "overage",
        "overage_allowed": bool(family and level == "overage"),
        "level": level,
        "message": message,
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
    return {key: summary.get(key) for key in PUBLIC_USAGE_KEYS}


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
    """Return a Spanish refusal, or None to proceed.

    Under the 20% base: allow. Over the base: interactive chat/voice only
    while ``family_overage_allowed()``; background kinds always refused.
    ``total_spend_hit`` is still a hard stop.
    """
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
    background = is_background_request(kind=kind, source=source, desk=desk)
    if background:
        return MSG_BACKGROUND_OVERAGE if summary["level"] == "overage" else summary["message"]
    if summary["level"] == "overage" and family_overage_allowed(used_percent=float(used)):
        return None
    return summary["message"]
