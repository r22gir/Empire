"""Free-tier model registry, quota tracking, and safety guardrails for MAX AI.

Fields per entry:
  provider, model_pattern, cost_basis, rpm, rpd, tpd, reset_tz,
  source_url, verified_date, use_cases, not_for
"""
from __future__ import annotations

import fnmatch
import logging
import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.services.data_paths import data_root

logger = logging.getLogger("max.free_tiers")


@dataclass
class FreeTierSpec:
    provider: str
    model_pattern: str
    cost_basis: str = "free_tier"
    rpm: int = 15
    rpd: int = 1000
    tpd: int = 1_000_000
    reset_tz: str = "UTC"
    source_url: str = ""
    verified_date: str = "2026-10-10"
    use_cases: str = "general tasks, research, drafting, internal exploration"
    not_for: str = "client-facing, quotes, invoicing, financial desks, private/confidential data"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# Canonical table of supported free-tier models and patterns
FREE_TIER_TABLE: list[FreeTierSpec] = [
    # Groq Open Models
    FreeTierSpec(
        provider="groq",
        model_pattern="openai/gpt-oss-120b",
        cost_basis="free_tier",
        rpm=30,
        rpd=1000,
        tpd=100_000,
        reset_tz="UTC",
        source_url="https://console.groq.com/docs/rate-limits",
        verified_date="2026-10-10",
        use_cases="General reasoning, non-sensitive tasks, open model exploration",
        not_for="Client replies, quotes, invoices, financial calculations, confidential customer data",
    ),
    FreeTierSpec(
        provider="groq",
        model_pattern="openai/gpt-oss-20b",
        cost_basis="free_tier",
        rpm=30,
        rpd=1000,
        tpd=100_000,
        reset_tz="UTC",
        source_url="https://console.groq.com/docs/rate-limits",
        verified_date="2026-10-10",
        use_cases="Lightweight summaries, quick queries, scratchpad coding",
        not_for="Quotes, invoices, client replies, financial tasks, confidential data",
    ),
    FreeTierSpec(
        provider="groq",
        model_pattern="qwen/qwen3.8-27b",
        cost_basis="free_tier",
        rpm=30,
        rpd=1000,
        tpd=100_000,
        reset_tz="UTC",
        source_url="https://console.groq.com/docs/rate-limits",
        verified_date="2026-10-10",
        use_cases="Multilingual text generation, technical drafting",
        not_for="Quotes, invoices, client replies, financial tasks, confidential data",
    ),

    # Google Gemini Free Tier
    FreeTierSpec(
        provider="gemini",
        model_pattern="gemini-2.5-flash",
        cost_basis="free_tier",
        rpm=15,
        rpd=1500,
        tpd=1_000_000,
        reset_tz="America/Los_Angeles",
        source_url="https://ai.google.dev/pricing",
        verified_date="2026-10-10",
        use_cases="Multimodal vision analysis, high context summarization, drafting",
        not_for="Client replies, quotes, invoices, financial desks, confidential business records",
    ),
    FreeTierSpec(
        provider="gemini",
        model_pattern="gemini-2.5-flash-lite",
        cost_basis="free_tier",
        rpm=15,
        rpd=1500,
        tpd=1_000_000,
        reset_tz="America/Los_Angeles",
        source_url="https://ai.google.dev/pricing",
        verified_date="2026-10-10",
        use_cases="Low latency lookups, quick metadata extraction, general chat",
        not_for="Client replies, quotes, invoices, financial desks, confidential data",
    ),
    FreeTierSpec(
        provider="gemini",
        model_pattern="gemini-3.5-flash",
        cost_basis="free_tier",
        rpm=15,
        rpd=1500,
        tpd=1_000_000,
        reset_tz="America/Los_Angeles",
        source_url="https://ai.google.dev/pricing",
        verified_date="2026-10-10",
        use_cases="Complex multimodal exploration, long context draft analysis",
        not_for="Client replies, quotes, invoices, financial desks, confidential data",
    ),

    # OpenRouter Free Models
    FreeTierSpec(
        provider="openrouter",
        model_pattern="nvidia/nemotron-3-super-120b-a12b:free",
        cost_basis="free_tier",
        rpm=20,
        rpd=200,
        tpd=200_000,
        reset_tz="UTC",
        source_url="https://openrouter.ai/models",
        verified_date="2026-10-10",
        use_cases="Experimental reasoning, deep technical Q&A",
        not_for="Client replies, quotes, invoices, financial tasks, confidential customer data",
    ),
    FreeTierSpec(
        provider="openrouter",
        model_pattern="google/gemma-4-31b-it:free",
        cost_basis="free_tier",
        rpm=20,
        rpd=200,
        tpd=200_000,
        reset_tz="UTC",
        source_url="https://openrouter.ai/models",
        verified_date="2026-10-10",
        use_cases="Open source model evaluation, instruction following",
        not_for="Client replies, quotes, invoices, financial tasks, confidential data",
    ),
    FreeTierSpec(
        provider="openrouter",
        model_pattern="cohere/north-mini-code:free",
        cost_basis="free_tier",
        rpm=20,
        rpd=200,
        tpd=200_000,
        reset_tz="UTC",
        source_url="https://openrouter.ai/models",
        verified_date="2026-10-10",
        use_cases="Code completion, refactoring review, syntax inspection",
        not_for="Client replies, quotes, invoices, financial tasks, proprietary source code",
    ),
    FreeTierSpec(
        provider="openrouter",
        model_pattern="openrouter/free",
        cost_basis="free_tier",
        rpm=20,
        rpd=200,
        tpd=200_000,
        reset_tz="UTC",
        source_url="https://openrouter.ai/models",
        verified_date="2026-10-10",
        use_cases="General open router fallback routing",
        not_for="Client replies, quotes, invoices, financial tasks, confidential data",
    ),
    # Wildcard match for any OpenRouter model ending with ':free'
    FreeTierSpec(
        provider="openrouter",
        model_pattern="*:free",
        cost_basis="free_tier",
        rpm=20,
        rpd=200,
        tpd=200_000,
        reset_tz="UTC",
        source_url="https://openrouter.ai/models",
        verified_date="2026-10-10",
        use_cases="Community free tier exploration",
        not_for="Client replies, quotes, invoices, financial desks, confidential data",
    ),
]

# Client-facing and financial desk keywords that MUST NEVER route to free-tier models
FORBIDDEN_DESKS = {
    "forge",
    "finance",
    "workroom",
    "quotes",
    "quote",
    "clients",
    "sales",
    "invoicing",
    "accounting",
}

FORBIDDEN_FEATURES = {
    "quote",
    "quotes",
    "finance",
    "invoice",
    "invoicing",
    "client_reply",
    "client_communication",
    "accounting",
    "forge_quote",
}


def is_financial_or_client_desk(
    desk: Optional[str] = None,
    feature: Optional[str] = None,
    business: Optional[str] = None,
) -> bool:
    """Guardrail check: returns True if desk, feature, or business involves client or financial operations."""
    desk_norm = (desk or "").strip().lower()
    feat_norm = (feature or "").strip().lower()
    biz_norm = (business or "").strip().lower()

    if desk_norm in FORBIDDEN_DESKS or any(d in desk_norm for d in ("quote", "finance", "client", "invoice")):
        return True
    if feat_norm in FORBIDDEN_FEATURES or any(f in feat_norm for f in ("quote", "finance", "invoice", "client")):
        return True
    if biz_norm in FORBIDDEN_DESKS or any(b in biz_norm for b in ("quote", "finance", "client", "invoice")):
        return True
    return False


def get_free_tier_spec(model: str, provider: Optional[str] = None) -> Optional[FreeTierSpec]:
    """Find the best matching FreeTierSpec for a given model name and optional provider."""
    model_norm = (model or "").strip()
    if not model_norm:
        return None

    # 1. Exact match pattern
    for spec in FREE_TIER_TABLE:
        if spec.model_pattern == model_norm:
            if provider and spec.provider != provider:
                continue
            return spec

    # 2. Case-insensitive exact match
    for spec in FREE_TIER_TABLE:
        if spec.model_pattern.lower() == model_norm.lower():
            if provider and spec.provider != provider:
                continue
            return spec

    # 3. Wildcard / fnmatch pattern (e.g. *:free)
    for spec in FREE_TIER_TABLE:
        if "*" in spec.model_pattern:
            if fnmatch.fnmatch(model_norm.lower(), spec.model_pattern.lower()):
                if provider and spec.provider != provider:
                    continue
                return spec

    # 4. Fallback heuristics for groq/gemini/openrouter free patterns
    lower = model_norm.lower()
    if lower.endswith(":free"):
        return FREE_TIER_TABLE[-1]  # *:free spec
    if "gpt-oss-" in lower or "qwen3.8-" in lower:
        for spec in FREE_TIER_TABLE:
            if spec.provider == "groq" and (spec.model_pattern in lower or lower in spec.model_pattern):
                return spec
    if "gemini-2.5-flash" in lower or "gemini-3.5-flash" in lower:
        for spec in FREE_TIER_TABLE:
            if spec.provider == "gemini" and spec.model_pattern in lower:
                return spec

    return None


def is_free_tier_model(model: str, provider: Optional[str] = None) -> bool:
    """Return True if model matches free-tier criteria (or is local)."""
    raw = (model or "").strip().lower()
    if not raw:
        return False
    # Explicit suffix
    if raw.endswith(":free"):
        return True
    # Groq OSS free models
    if "openai/gpt-oss-" in raw or "gpt-oss-120b" in raw or "gpt-oss-20b" in raw:
        return True
    if "qwen/qwen3.8-27b" in raw or "qwen3.8-27b" in raw:
        return True
    # Gemini free models
    if raw in ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3.5-flash"):
        return True
    if any(m in raw for m in ("gemini-2.5-flash-lite", "gemini-3.5-flash", "gemini-2.5-flash")):
        return True
    # OpenRouter free models
    if raw in (
        "nvidia/nemotron-3-super-120b-a12b:free",
        "google/gemma-4-31b-it:free",
        "cohere/north-mini-code:free",
        "openrouter/free",
    ):
        return True
    # Matching spec
    spec = get_free_tier_spec(model, provider)
    return spec is not None


def _get_db_path(custom_path: Optional[str] = None) -> str:
    if custom_path:
        return custom_path
    try:
        from app.services.max.brain.brain_config import get_brain_path
        return str(get_brain_path() / "token_usage.db")
    except Exception:
        fallback = data_root() / "token_usage.db"
        fallback.parent.mkdir(parents=True, exist_ok=True)
        return str(fallback)


def init_free_tier_db(db_path: Optional[str] = None) -> None:
    path = _get_db_path(db_path)
    try:
        conn = sqlite3.connect(path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS free_tier_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                provider TEXT NOT NULL,
                window_date TEXT NOT NULL,
                window_minute TEXT NOT NULL,
                requests_day INTEGER NOT NULL DEFAULT 0,
                tokens_day INTEGER NOT NULL DEFAULT 0,
                requests_minute INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'normal',
                updated_at TEXT NOT NULL,
                UNIQUE(model, window_date)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_free_tier_model ON free_tier_usage(model)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_free_tier_date ON free_tier_usage(window_date)")
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to init free_tier_usage table: {e}")


def _get_window_keys(now: Optional[datetime] = None) -> tuple[str, str]:
    dt = now or datetime.now(timezone.utc)
    date_key = dt.strftime("%Y-%m-%d")
    minute_key = dt.strftime("%Y-%m-%d %H:%M")
    return date_key, minute_key


def record_free_tier_usage(
    model: str,
    provider: str,
    tokens: int,
    requests: int = 1,
    db_path: Optional[str] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Increment free_tier_usage for day and minute, calculate ratio vs limits, warn at 80%, failover at 100%."""
    spec = get_free_tier_spec(model, provider)
    rpm_limit = spec.rpm if spec else 30
    rpd_limit = spec.rpd if spec else 1000
    tpd_limit = spec.tpd if spec else 1_000_000

    path = _get_db_path(db_path)
    init_free_tier_db(path)
    date_key, minute_key = _get_window_keys(now)
    now_iso = (now or datetime.now(timezone.utc)).isoformat()

    req_delta = max(1, int(requests or 1))
    requests_day = req_delta
    tokens_day = max(0, int(tokens or 0))
    requests_minute = req_delta

    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute(
            "SELECT id, window_minute, requests_day, tokens_day, requests_minute FROM free_tier_usage WHERE model = ? AND window_date = ?",
            (model, date_key),
        )
        row = cur.fetchone()
        if row:
            row_id, last_min, r_day, t_day, r_min = row
            requests_day = r_day + req_delta
            tokens_day = t_day + max(0, int(tokens or 0))
            requests_minute = (r_min + req_delta) if last_min == minute_key else req_delta

            rpm_pct = requests_minute / max(1, rpm_limit)
            rpd_pct = requests_day / max(1, rpd_limit)
            tpd_pct = tokens_day / max(1, tpd_limit)
            max_pct = max(rpm_pct, rpd_pct, tpd_pct)

            status = "normal"
            if max_pct >= 1.0:
                status = "exhausted"
            elif max_pct >= 0.8:
                status = "warn"

            cur.execute(
                """UPDATE free_tier_usage
                   SET window_minute = ?, requests_day = ?, tokens_day = ?, requests_minute = ?, status = ?, updated_at = ?
                   WHERE id = ?""",
                (minute_key, requests_day, tokens_day, requests_minute, status, now_iso, row_id),
            )
        else:
            rpm_pct = requests_minute / max(1, rpm_limit)
            rpd_pct = requests_day / max(1, rpd_limit)
            tpd_pct = tokens_day / max(1, tpd_limit)
            max_pct = max(rpm_pct, rpd_pct, tpd_pct)

            status = "normal"
            if max_pct >= 1.0:
                status = "exhausted"
            elif max_pct >= 0.8:
                status = "warn"

            cur.execute(
                """INSERT INTO free_tier_usage (model, provider, window_date, window_minute, requests_day, tokens_day, requests_minute, status, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (model, provider, date_key, minute_key, requests_day, tokens_day, requests_minute, status, now_iso),
            )

        conn.commit()
        conn.close()

        if status == "warn":
            logger.warning(f"[MAX FREE TIER] Quota warning: {model} at {max_pct*100:.1f}% of limit (RPM {requests_minute}/{rpm_limit}, RPD {requests_day}/{rpd_limit}, TPD {tokens_day}/{tpd_limit})")
        elif status == "exhausted":
            logger.error(f"[MAX FREE TIER] Quota exhausted: {model} reached 100% of limit (RPM {requests_minute}/{rpm_limit}, RPD {requests_day}/{rpd_limit}, TPD {tokens_day}/{tpd_limit})")

        return {
            "model": model,
            "provider": provider,
            "window_date": date_key,
            "requests_day": requests_day,
            "tokens_day": tokens_day,
            "requests_minute": requests_minute,
            "rpm_limit": rpm_limit,
            "rpd_limit": rpd_limit,
            "tpd_limit": tpd_limit,
            "percent_used": round(max_pct * 100, 2),
            "status": status,
            "warn": status in ("warn", "exhausted"),
            "exhausted": status == "exhausted",
        }
    except Exception as e:
        logger.warning(f"Failed to record free tier usage for {model}: {e}")
        return {
            "model": model,
            "provider": provider,
            "percent_used": 0.0,
            "status": "error",
            "warn": False,
            "exhausted": False,
        }


def check_free_tier_quota(
    model: str,
    provider: Optional[str] = None,
    db_path: Optional[str] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """Check current quota usage for model without incrementing."""
    spec = get_free_tier_spec(model, provider)
    rpm_limit = spec.rpm if spec else 30
    rpd_limit = spec.rpd if spec else 1000
    tpd_limit = spec.tpd if spec else 1_000_000

    path = _get_db_path(db_path)
    init_free_tier_db(path)
    date_key, minute_key = _get_window_keys(now)

    requests_day = 0
    tokens_day = 0
    requests_minute = 0
    status = "normal"

    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute(
            "SELECT window_minute, requests_day, tokens_day, requests_minute, status FROM free_tier_usage WHERE model = ? AND window_date = ?",
            (model, date_key),
        )
        row = cur.fetchone()
        conn.close()

        if row:
            last_min, r_day, t_day, r_min, st = row
            requests_day = r_day
            tokens_day = t_day
            requests_minute = r_min if last_min == minute_key else 0
            status = st

        rpm_pct = requests_minute / max(1, rpm_limit)
        rpd_pct = requests_day / max(1, rpd_limit)
        tpd_pct = tokens_day / max(1, tpd_limit)
        max_pct = max(rpm_pct, rpd_pct, tpd_pct)

        if max_pct >= 1.0:
            status = "exhausted"
        elif max_pct >= 0.8:
            status = "warn"

        return {
            "model": model,
            "provider": provider or (spec.provider if spec else "unknown"),
            "window_date": date_key,
            "requests_day": requests_day,
            "tokens_day": tokens_day,
            "requests_minute": requests_minute,
            "rpm_limit": rpm_limit,
            "rpd_limit": rpd_limit,
            "tpd_limit": tpd_limit,
            "percent_used": round(max_pct * 100, 2),
            "status": status,
            "warn": status in ("warn", "exhausted"),
            "exhausted": status == "exhausted",
        }
    except Exception as e:
        logger.warning(f"Failed to check free tier quota for {model}: {e}")
        return {
            "model": model,
            "provider": provider or "unknown",
            "percent_used": 0.0,
            "status": "normal",
            "warn": False,
            "exhausted": False,
        }


def is_free_tier_quota_exhausted(
    model: str,
    provider: Optional[str] = None,
    db_path: Optional[str] = None,
    now: Optional[datetime] = None,
) -> bool:
    """Return True if model is a free tier model and its quota is 100% exhausted."""
    if not is_free_tier_model(model, provider):
        return False
    quota = check_free_tier_quota(model, provider, db_path, now)
    return bool(quota.get("exhausted"))


def get_all_free_tier_status(db_path: Optional[str] = None) -> list[dict[str, Any]]:
    """Return specs and current usage for all registered free-tier models."""
    res = []
    for spec in FREE_TIER_TABLE:
        # Skip generic wildcard from primary list display if concrete models exist
        if spec.model_pattern == "*:free":
            continue
        status_info = check_free_tier_quota(spec.model_pattern, spec.provider, db_path)
        item = spec.to_dict()
        item.update(status_info)
        res.append(item)
    return res
