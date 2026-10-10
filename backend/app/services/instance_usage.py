"""Per-instance LLM usage cap for family editions.

How the 20% is computed
-----------------------
Each family instance (EMPIRE_EDITION=amp, maxine, …) records its own
calls: input tokens, output tokens, and an estimated USD cost, rolled
up by UTC day and calendar month in ``EMPIRE_DATA_DIR/usage/usage.db``.

The allowance is a share of EmpireBox's measured AI use for the month:

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

At 80% of the allowance the API reports ``level=warn`` and remaining
percent. At 100%, heavy work is refused in Spanish; a short chat
reply still runs unless this instance has used the whole baseline
(the total spend limit).

``GET /api/v1/edition/usage`` is ``public_usage_summary()``: used
percent of this instance's allowance, remaining percent, level, and
the Spanish message. It does not include baseline, allowance, or
absolute token/cost totals (those would reveal EmpireBox-wide usage).
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

HEAVY_KINDS = frozenset({"job", "generate", "desk_task", "vision", "social", "heavy"})
DEFAULT_BASELINE_MONTHLY_TOKENS = 10_000_000.0


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
        "remaining_percent": 100.0 if family else None,
        "total_spend_hit": False,
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
    remaining_percent = 100.0 if family else None
    used_percent = 0.0 if family else None
    level = "ok"
    message = ""
    total_spend_hit = bool(baseline is not None and baseline > 0 and used >= float(baseline))
    if allowance and allowance > 0:
        ratio = round(used / allowance, 4)
        remaining_percent = max(0.0, round((1.0 - ratio) * 100.0, 1))
        used_percent = min(100.0, round(ratio * 100.0, 1))
        used_pct = round(ratio * 100)
        if total_spend_hit:
            level = "blocked"
            message = (
                "Llegamos al tope total de uso de EmpireBox este mes. "
                "También los mensajes cortos quedan en pausa."
            )
        elif ratio >= 1:
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
                f"Esta instancia ya usó el {used_pct:g}% de su tope "
                f"({pct:g}% del uso de EmpireBox este mes). "
                f"Queda el {remaining_percent:g}%."
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
)


def public_usage_summary() -> dict:
    """Owner-facing meter. Percentages only — no EmpireBox-wide totals."""
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
    """Return a Spanish refusal for heavy work at 100%, or None to proceed."""
    from app.edition import is_family_edition

    if not is_family_edition():
        return None
    summary = usage_summary()
    if summary["level"] != "blocked":
        return None
    if summary.get("total_spend_hit"):
        return summary["message"]
    if not is_heavy_request(kind=kind, text=text, desk=desk, tools=tools, source=source, image=image):
        return None
    return summary["message"]
