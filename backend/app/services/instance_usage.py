"""Per-instance LLM usage cap for family editions.

How the 20% is computed
-----------------------
Each family instance (EMPIRE_EDITION=amp, maxine, …) records its own
MiniMax calls: input tokens, output tokens, and an estimated USD cost,
rolled up by UTC day and calendar month in ``EMPIRE_DATA_DIR/usage/usage.db``.

The allowance is a share of a measured EmpireBox baseline for the same
month, not an invented account total:

    allowance = INSTANCE_USAGE_CAP_PCT / 100 * baseline

``INSTANCE_USAGE_CAP_PCT`` defaults to 20 on family editions.

Baseline, first match wins:

1. ``EMPIRE_USAGE_BASELINE_MONTHLY_USD`` — measured EmpireBox AI spend
   for the month (all instances, or the provider invoice). The ratio
   uses this instance's estimated USD.
2. ``EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS`` — measured EmpireBox token
   total for the month. The ratio uses this instance's tokens.

USD for display and for case 1 is:

    tokens / 1_000_000 * MINIMAX_USD_PER_MILLION_TOKENS

``MINIMAX_USD_PER_MILLION_TOKENS`` is an operator estimate (default
0.30). It is not a price invented per lot or per customer. If neither
baseline is set, usage is still tracked and the cap is not enforced.

At 80% of the allowance the API reports ``level=warn``. At 100%, new
heavy work is refused with a Spanish message. A short chat reply
(no tools, no image, no desk job, user text at most
``INSTANCE_SHORT_REPLY_CHARS``, default 400) still runs and is counted.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

HEAVY_KINDS = frozenset({"job", "generate", "desk_task", "vision", "social", "heavy"})


def _now() -> datetime:
    return datetime.now(timezone.utc)


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


def _baseline() -> tuple[str, Optional[float]]:
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


def usage_summary() -> dict:
    from app.edition import edition_name, is_family_edition

    now = _now()
    basis, baseline = _baseline()
    pct = cap_percent()
    allowance = None if baseline is None else round(baseline * pct / 100.0, 6)
    empty = {
        "enforced": bool(is_family_edition() and allowance is not None),
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
        "ratio": None,
        "level": "ok",
        "message": "",
        "limit_note_es": (
            f"Tu uso está limitado al {pct:g}% del uso total de MiniMax."
            if is_family_edition() else ""
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
    level = "ok"
    message = ""
    if allowance and allowance > 0 and basis != "none":
        ratio = round(used / allowance, 4)
        if ratio >= 1:
            level = "blocked"
            message = (
                f"Llegamos al tope de uso de esta instancia "
                f"({pct:g}% del uso de EmpireBox este mes). "
                "Los trabajos largos quedan en pausa. "
                "Puedo seguir contestando mensajes cortos."
            )
        elif ratio >= 0.8:
            level = "warn"
            message = (
                f"Esta instancia ya usó el {round(ratio * 100):g}% de su tope "
                f"({pct:g}% del uso de EmpireBox este mes)."
            )
    elif is_family_edition():
        level = "unconfigured"
        message = (
            "El uso se está registrando. Falta la base del mes "
            "(EMPIRE_USAGE_BASELINE_MONTHLY_USD o EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS) "
            "para aplicar el tope."
        )
    empty.update({
        "day": day,
        "month": month,
        "used": used,
        "ratio": ratio,
        "level": level,
        "message": message,
    })
    return empty


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
    """Return a Spanish refusal for heavy work at 100%, or None to proceed."""
    from app.edition import is_family_edition

    if not is_family_edition():
        return None
    summary = usage_summary()
    if summary["level"] != "blocked":
        return None
    if not is_heavy_request(kind=kind, text=text, desk=desk, tools=tools, source=source, image=image):
        return None
    return summary["message"]
