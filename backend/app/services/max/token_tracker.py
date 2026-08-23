"""
Token usage tracking and cost estimation for all LLM providers.
Stores usage in SQLite on the brain drive (or local fallback).

Tracks: provider, model, tokens, cost, feature, business, source.
"""
import sqlite3
import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from app.services.data_paths import data_root
from app.services.max.routing_state import load_routing_state, provider_disabled

logger = logging.getLogger("max.tokens")

# Cost per 1M tokens (USD) — updated Mar 2026
COST_RATES = {
    # xAI Grok
    "grok": {"input": 5.00, "output": 15.00},
    "grok-3-fast": {"input": 5.00, "output": 15.00},
    "grok-vision": {"input": 5.00, "output": 15.00},
    # Anthropic Claude
    "claude-4.6-sonnet": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
    # Groq (free tier / very cheap)
    "groq-llama-3.3-70b": {"input": 0.59, "output": 0.79},
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    "groq-whisper": {"input": 0.0, "output": 0.0},  # free STT
    # OpenAI / compatible
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 5.00, "output": 15.00},
    # DeepSeek / Qwen / OpenRouter defaults (estimated)
    "deepseek-chat": {"input": 0.27, "output": 1.10},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19},
    # DeepSeek V4 (official pricing page; still treated as estimated in UI)
    "deepseek-v4-flash": {"input": 0.14, "output": 0.28},
    "deepseek-v4-pro": {"input": 0.435, "output": 0.87},
    "qwen-plus": {"input": 0.40, "output": 1.20},
    "qwen-max": {"input": 1.20, "output": 3.60},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
    # Local models (free)
    "ollama-llama3.1": {"input": 0.0, "output": 0.0},
    "llama3.1:8b": {"input": 0.0, "output": 0.0},
    "ollama-llama": {"input": 0.0, "output": 0.0},
    "openclaw": {"input": 0.0, "output": 0.0},
    "mistral:7b": {"input": 0.0, "output": 0.0},
    "nomic-embed-text": {"input": 0.0, "output": 0.0},
}

# Fixed per-call costs (not token-based)
FIXED_COSTS = {
    "grok-tts": 0.015,        # ~$0.015 per TTS call (estimated)
    "grok-image-gen": 0.04,   # ~$0.04 per image generation
    "stability-inpaint": 0.04,  # ~$0.04 per inpainting
    "pixazo": 0.0,            # free
}

# Feature labels for categorization
FEATURES = [
    "chat", "chat/stream", "vision", "tts", "stt",
    "image_gen", "inpaint", "mockup", "quote",
    "desk_task", "measurement", "web_search", "email",
    "brain_learn", "embedding", "other",
]

# Business labels
BUSINESSES = [
    "workroom", "craftforge", "personal", "platform", "luxeforge",
    "socialforge", "marketforge", "recoveryforge", "general",
]

# Default monthly budget (USD)
DEFAULT_MONTHLY_BUDGET = 50.00


PROVIDER_ALIASES = {
    "grok": "xai",
    "x-ai": "xai",
    "anthropic": "claude",
    "google": "gemini",
    "chatgpt": "openai",
    "open-ai": "openai",
    "local": "ollama",
}

MODEL_PROVIDER_HINTS = {
    "grok": "xai",
    "claude": "claude",
    "gemini": "gemini",
    "gpt-": "openai",
    "minimax": "minimax",
    "deepseek": "deepseek",
    "qwen": "qwen",
    "openai/": "openrouter",
    "llama3.1": "ollama",
    # NOTE: no "openclaw" entry — wrapper providers never round-trip through
    # the model field. The wrapper's inner delegate (e.g. "deepseek-v4-flash")
    # classifies via the "deepseek" hint above. If a model string ever
    # contains "openclaw" again, that is stale legacy data and will fall
    # through to no-hint.
}

MODEL_ALIASES = {
    "minimax-minimax-m2.7": "MiniMax-M2.7",
    "minimax-m2.7": "MiniMax-M2.7",
    "grok-3-fast": "grok-4-fast-non-reasoning",
    "grok": "grok-4-fast-non-reasoning",
    "ollama-llama3.1": "llama3.1:8b",
    "ollama-llama": "llama3.1:8b",
    "groq-llama-3.3-70b": "llama-3.3-70b-versatile",
}


def _get_db_path() -> str:
    try:
        from app.services.max.brain.brain_config import get_brain_path
        return str(get_brain_path() / "token_usage.db")
    except Exception:
        fallback = data_root() / "token_usage.db"
        fallback.parent.mkdir(parents=True, exist_ok=True)
        return str(fallback)


class TokenTracker:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or _get_db_path()
        self._init_db()

    def _init_db(self):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                    model TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    cost_usd REAL NOT NULL DEFAULT 0.0,
                    endpoint TEXT DEFAULT 'chat',
                    conversation_id TEXT,
                    feature TEXT DEFAULT 'chat',
                    business TEXT DEFAULT 'general',
                    source TEXT DEFAULT ''
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_token_timestamp ON token_usage(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_token_model ON token_usage(model)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_token_feature ON token_usage(feature)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_token_business ON token_usage(business)")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS budget_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    monthly_budget REAL NOT NULL DEFAULT 50.0,
                    alert_threshold REAL NOT NULL DEFAULT 0.8,
                    auto_switch_to_local BOOLEAN NOT NULL DEFAULT 0,
                    auto_switch_threshold REAL NOT NULL DEFAULT 0.95
                )
            """)
            conn.execute("""
                INSERT OR IGNORE INTO budget_config (id, monthly_budget, alert_threshold, auto_switch_to_local, auto_switch_threshold)
                VALUES (1, ?, 0.8, 0, 0.95)
            """, (DEFAULT_MONTHLY_BUDGET,))
            # Safe migration: add columns if missing
            for col, default in [
                ("feature", "'chat'"),
                ("business", "'general'"),
                ("source", "''"),
                ("tenant_id", "'founder'"),
                ("desk", "''"),
                ("request_id", "''"),
                ("attempt_id", "''"),
                ("provider_canonical", "''"),
                ("model_canonical", "''"),
                ("raw_provider", "''"),
                ("raw_model", "''"),
                ("source_module", "''"),
                ("route_name", "''"),
                ("lane", "'stable/main'"),
                ("status", "'success'"),
                ("http_status", "0"),
                ("fallback_of", "''"),
                ("token_source", "'estimated'"),
                ("total_tokens", "0"),
                ("estimated_cost", "0.0"),
                ("provider_reported_cost", "0.0"),
                ("is_legacy", "0"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE token_usage ADD COLUMN {col} TEXT DEFAULT {default}")
                except sqlite3.OperationalError:
                    pass  # Column already exists
            # Fix types for numeric columns if ALTER added them as TEXT in some SQLite builds
            for col, default in [("http_status", "0"), ("total_tokens", "0"), ("estimated_cost", "0.0"), ("provider_reported_cost", "0.0"), ("is_legacy", "0")]:
                try:
                    conn.execute(f"UPDATE token_usage SET {col} = {default} WHERE {col} IS NULL")
                except Exception:
                    pass
            conn.execute("CREATE INDEX IF NOT EXISTS idx_token_tenant ON token_usage(tenant_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_token_desk ON token_usage(desk)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_token_request_id ON token_usage(request_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_token_attempt_id ON token_usage(attempt_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_token_provider_canonical ON token_usage(provider_canonical)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_token_model_canonical ON token_usage(model_canonical)")
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Token tracker DB init failed: {e}")

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count from text (roughly 4 chars per token)."""
        return max(1, len(text) // 4)

    @staticmethod
    def canonical_provider(provider: str | None, model: str | None = None) -> str:
        raw = (provider or "").strip().lower()
        if raw in PROVIDER_ALIASES:
            raw = PROVIDER_ALIASES[raw]
        if raw:
            return raw
        model_l = (model or "").strip().lower()
        for prefix, canonical in MODEL_PROVIDER_HINTS.items():
            if prefix in model_l:
                return canonical
        return "unknown"

    @staticmethod
    def canonical_model(model: str | None) -> str:
        raw = (model or "").strip()
        if not raw:
            return "unknown-model"
        key = raw.lower()
        if key in MODEL_ALIASES:
            return MODEL_ALIASES[key]
        if key.startswith("minimax-") and "m2.7" in key:
            return "MiniMax-M2.7"
        return raw

    @staticmethod
    def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        rates = COST_RATES.get(model)
        if not rates:
            return 0.0
        input_cost = (input_tokens / 1_000_000) * rates["input"]
        output_cost = (output_tokens / 1_000_000) * rates["output"]
        return round(input_cost + output_cost, 6)

    def log_usage(
        self,
        model: str,
        provider: str,
        input_tokens: int,
        output_tokens: int,
        endpoint: str = "chat",
        conversation_id: str = None,
        feature: str = "chat",
        business: str = "general",
        source: str = "",
        tenant_id: str = "founder",
        request_id: str | None = None,
        attempt_id: str | None = None,
        source_module: str = "",
        route_name: str = "",
        lane: str | None = None,
        status: str = "success",
        http_status: int | None = None,
        fallback_of: str | None = None,
        token_source: str = "estimated",
        provider_reported_cost: float | None = None,
        raw_provider: str | None = None,
        raw_model: str | None = None,
        is_legacy: bool = False,
    ):
        model_canonical = self.canonical_model(model)
        provider_canonical = self.canonical_provider(provider, model=model_canonical)
        cost = self.calculate_cost(model_canonical, input_tokens, output_tokens)
        total_tokens = max(0, int(input_tokens or 0) + int(output_tokens or 0))
        req_id = request_id or str(uuid.uuid4())
        att_id = attempt_id or str(uuid.uuid4())
        lane_name = lane or os.getenv("EMPIRE_LANE", "stable/main")
        token_source_norm = token_source if token_source in {"provider_reported", "estimated", "unknown"} else "estimated"
        provider_cost = float(provider_reported_cost) if provider_reported_cost is not None else None
        final_cost = provider_cost if provider_cost is not None else cost
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """INSERT INTO token_usage (
                       model, provider, input_tokens, output_tokens, cost_usd, endpoint, conversation_id, feature, business, source, tenant_id,
                       request_id, attempt_id, provider_canonical, model_canonical, raw_provider, raw_model, source_module, route_name, lane,
                       status, http_status, fallback_of, token_source, total_tokens, estimated_cost, provider_reported_cost, is_legacy
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    model_canonical,
                    provider_canonical,
                    int(input_tokens or 0),
                    int(output_tokens or 0),
                    float(final_cost or 0.0),
                    endpoint,
                    conversation_id,
                    feature,
                    business,
                    source,
                    tenant_id,
                    req_id,
                    att_id,
                    provider_canonical,
                    model_canonical,
                    raw_provider or provider,
                    raw_model or model,
                    source_module or source or "unknown",
                    route_name or endpoint,
                    lane_name,
                    status or "success",
                    int(http_status or 0),
                    fallback_of or "",
                    token_source_norm,
                    total_tokens,
                    float(cost),
                    float(provider_cost) if provider_cost is not None else 0.0,
                    1 if is_legacy else 0,
                ),
            )
            conn.commit()
            conn.close()
            logger.debug(
                "Cost logged: provider=%s model=%s source=%s token_source=%s est=$%.4f final=$%.4f",
                provider_canonical,
                model_canonical,
                source_module or source or "unknown",
                token_source_norm,
                cost,
                final_cost,
            )
        except Exception as e:
            logger.warning(f"Failed to log token usage: {e}")

    def log_fixed_cost(
        self,
        cost_type: str,
        feature: str = "other",
        business: str = "general",
        source: str = "",
    ):
        """Log a fixed-cost API call (TTS, image gen, inpainting)."""
        cost = FIXED_COSTS.get(cost_type, 0.0)
        model = cost_type
        provider = "free" if cost == 0 else "cloud"
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """INSERT INTO token_usage (model, provider, input_tokens, output_tokens, cost_usd, endpoint, feature, business, source)
                   VALUES (?, ?, 0, 0, ?, ?, ?, ?, ?)""",
                (model, provider, cost, cost_type, feature, business, source),
            )
            conn.commit()
            conn.close()
            logger.debug(f"Fixed cost logged: {cost_type} ${cost:.4f} [{feature}/{business}]")
        except Exception as e:
            logger.warning(f"Failed to log fixed cost: {e}")

    def log_chat(
        self,
        model: str,
        input_text: str,
        output_text: str,
        endpoint: str = "chat",
        conversation_id: str = None,
        feature: str = "chat",
        business: str = "general",
        source: str = "",
        tenant_id: str = "founder",
    ):
        """Convenience: estimate tokens from text and log."""
        provider = self.canonical_provider("", model=model)
        input_tokens = self.estimate_tokens(input_text)
        output_tokens = self.estimate_tokens(output_text)
        self.log_usage(
            model,
            provider,
            input_tokens,
            output_tokens,
            endpoint,
            conversation_id,
            feature,
            business,
            source,
            tenant_id,
            source_module=source or "ai_router",
            route_name=endpoint,
            token_source="estimated",
            raw_provider=provider,
            raw_model=model,
        )

    def get_stats(self, days: int = 30) -> dict:
        """Get aggregated token usage stats."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            since = (datetime.utcnow() - timedelta(days=days)).isoformat()

            # Total usage in period
            row = conn.execute(
                """SELECT
                     COALESCE(SUM(input_tokens), 0) as total_input,
                     COALESCE(SUM(output_tokens), 0) as total_output,
                     COALESCE(SUM(cost_usd), 0) as total_cost,
                     COUNT(*) as total_requests
                   FROM token_usage WHERE timestamp >= ?""",
                (since,),
            ).fetchone()

            total_input = row["total_input"]
            total_output = row["total_output"]
            total_cost = round(row["total_cost"], 4)
            total_requests = row["total_requests"]

            # Per-model breakdown (canonicalized)
            model_rows = conn.execute(
                """SELECT
                     COALESCE(model_canonical, model) as model_canonical,
                     COALESCE(provider_canonical, provider) as provider_canonical,
                     SUM(input_tokens) as input_tokens,
                     SUM(output_tokens) as output_tokens,
                     SUM(cost_usd) as cost,
                     SUM(estimated_cost) as estimated_cost,
                     SUM(provider_reported_cost) as provider_reported_cost,
                     SUM(CASE WHEN token_source = 'provider_reported' THEN 1 ELSE 0 END) as provider_reported_rows,
                     SUM(CASE WHEN token_source = 'estimated' THEN 1 ELSE 0 END) as estimated_rows,
                     COUNT(*) as requests
                   FROM token_usage WHERE timestamp >= ?
                   GROUP BY COALESCE(model_canonical, model), COALESCE(provider_canonical, provider)
                   ORDER BY cost DESC""",
                (since,),
            ).fetchall()

            by_model = [
                {
                    "model": r["model_canonical"],
                    "provider": r["provider_canonical"],
                    "input_tokens": r["input_tokens"],
                    "output_tokens": r["output_tokens"],
                    "cost": round(r["cost"], 4),
                    "estimated_cost": round((r["estimated_cost"] or 0), 4),
                    "provider_reported_cost": round((r["provider_reported_cost"] or 0), 4),
                    "provider_reported_rows": int(r["provider_reported_rows"] or 0),
                    "estimated_rows": int(r["estimated_rows"] or 0),
                    "requests": r["requests"],
                }
                for r in model_rows
            ]

            # Daily usage (last 7 days)
            week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
            daily_rows = conn.execute(
                """SELECT DATE(timestamp) as day,
                     SUM(input_tokens) as input_tokens,
                     SUM(output_tokens) as output_tokens,
                     SUM(cost_usd) as cost,
                     COUNT(*) as requests
                   FROM token_usage WHERE timestamp >= ?
                   GROUP BY DATE(timestamp) ORDER BY day""",
                (week_ago,),
            ).fetchall()

            daily = [
                {
                    "day": r["day"],
                    "input_tokens": r["input_tokens"],
                    "output_tokens": r["output_tokens"],
                    "cost": round(r["cost"], 4),
                    "requests": r["requests"],
                }
                for r in daily_rows
            ]

            # Today's usage
            today = datetime.utcnow().strftime("%Y-%m-%d")
            today_row = conn.execute(
                """SELECT
                     COALESCE(SUM(input_tokens), 0) as input_tokens,
                     COALESCE(SUM(output_tokens), 0) as output_tokens,
                     COALESCE(SUM(cost_usd), 0) as cost,
                     COUNT(*) as requests
                   FROM token_usage WHERE DATE(timestamp) = ?""",
                (today,),
            ).fetchone()

            # Monthly cost (current month)
            month_start = datetime.utcnow().replace(day=1).strftime("%Y-%m-%d")
            month_row = conn.execute(
                """SELECT COALESCE(SUM(cost_usd), 0) as cost
                   FROM token_usage WHERE timestamp >= ?""",
                (month_start,),
            ).fetchone()
            monthly_cost = round(month_row["cost"], 4)

            # Budget config
            budget_row = conn.execute("SELECT * FROM budget_config WHERE id = 1").fetchone()
            monthly_budget = budget_row["monthly_budget"] if budget_row else DEFAULT_MONTHLY_BUDGET
            alert_threshold = budget_row["alert_threshold"] if budget_row else 0.8
            auto_switch = bool(budget_row["auto_switch_to_local"]) if budget_row else False
            auto_switch_at = budget_row["auto_switch_threshold"] if budget_row else 0.95

            budget_used = monthly_cost / monthly_budget if monthly_budget > 0 else 0
            budget_alert = budget_used >= alert_threshold

            token_source_row = conn.execute(
                """SELECT
                     SUM(CASE WHEN token_source = 'provider_reported' THEN 1 ELSE 0 END) as provider_reported,
                     SUM(CASE WHEN token_source = 'estimated' THEN 1 ELSE 0 END) as estimated,
                     SUM(CASE WHEN token_source = 'unknown' THEN 1 ELSE 0 END) as unknown
                   FROM token_usage WHERE timestamp >= ?""",
                (since,),
            ).fetchone()

            conn.close()

            return {
                "period_days": days,
                "total": {
                    "input_tokens": total_input,
                    "output_tokens": total_output,
                    "total_tokens": total_input + total_output,
                    "cost_usd": total_cost,
                    "requests": total_requests,
                },
                "today": {
                    "input_tokens": today_row["input_tokens"],
                    "output_tokens": today_row["output_tokens"],
                    "cost_usd": round(today_row["cost"], 4),
                    "requests": today_row["requests"],
                },
                "by_model": by_model,
                "daily": daily,
                "token_sources": {
                    "provider_reported": int(token_source_row["provider_reported"] or 0),
                    "estimated": int(token_source_row["estimated"] or 0),
                    "unknown": int(token_source_row["unknown"] or 0),
                },
                "budget": {
                    "monthly_limit": monthly_budget,
                    "monthly_spent": monthly_cost,
                    "percent_used": round(budget_used * 100, 1),
                    "alert": budget_alert,
                    "auto_switch_to_local": auto_switch,
                    "auto_switch_threshold": auto_switch_at,
                },
            }
        except Exception as e:
            logger.error(f"Token stats query failed: {e}")
            return {
                "period_days": days,
                "total": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0, "requests": 0},
                "today": {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0, "requests": 0},
                "by_model": [],
                "daily": [],
                "token_sources": {"provider_reported": 0, "estimated": 0, "unknown": 0},
                "budget": {
                    "monthly_limit": DEFAULT_MONTHLY_BUDGET,
                    "monthly_spent": 0,
                    "percent_used": 0,
                    "alert": False,
                    "auto_switch_to_local": False,
                    "auto_switch_threshold": 0.95,
                },
            }

    def get_daily(self, days: int = 30) -> list:
        """Daily cost breakdown for the last N days."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            since = (datetime.utcnow() - timedelta(days=days)).isoformat()
            rows = conn.execute(
                """SELECT DATE(timestamp) as day,
                     SUM(input_tokens) as input_tokens,
                     SUM(output_tokens) as output_tokens,
                     SUM(cost_usd) as cost,
                     COUNT(*) as requests
                   FROM token_usage WHERE timestamp >= ?
                   GROUP BY DATE(timestamp) ORDER BY day""",
                (since,),
            ).fetchall()
            conn.close()
            return [{"day": r["day"], "input_tokens": r["input_tokens"],
                     "output_tokens": r["output_tokens"],
                     "cost": round(r["cost"], 4), "requests": r["requests"]} for r in rows]
        except Exception as e:
            logger.error(f"get_daily failed: {e}")
            return []

    def get_weekly(self, weeks: int = 12) -> list:
        """Weekly cost breakdown for the last N weeks."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            since = (datetime.utcnow() - timedelta(weeks=weeks)).isoformat()
            rows = conn.execute(
                """SELECT strftime('%Y-W%W', timestamp) as week,
                     SUM(input_tokens) as input_tokens,
                     SUM(output_tokens) as output_tokens,
                     SUM(cost_usd) as cost,
                     COUNT(*) as requests
                   FROM token_usage WHERE timestamp >= ?
                   GROUP BY strftime('%Y-W%W', timestamp) ORDER BY week""",
                (since,),
            ).fetchall()
            conn.close()
            return [{"week": r["week"], "input_tokens": r["input_tokens"],
                     "output_tokens": r["output_tokens"],
                     "cost": round(r["cost"], 4), "requests": r["requests"]} for r in rows]
        except Exception as e:
            logger.error(f"get_weekly failed: {e}")
            return []

    def get_monthly(self, months: int = 12) -> list:
        """Monthly cost breakdown for the last N months."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            since = (datetime.utcnow() - timedelta(days=months * 30)).isoformat()
            rows = conn.execute(
                """SELECT strftime('%Y-%m', timestamp) as month,
                     SUM(input_tokens) as input_tokens,
                     SUM(output_tokens) as output_tokens,
                     SUM(cost_usd) as cost,
                     COUNT(*) as requests
                   FROM token_usage WHERE timestamp >= ?
                   GROUP BY strftime('%Y-%m', timestamp) ORDER BY month""",
                (since,),
            ).fetchall()
            conn.close()
            return [{"month": r["month"], "input_tokens": r["input_tokens"],
                     "output_tokens": r["output_tokens"],
                     "cost": round(r["cost"], 4), "requests": r["requests"]} for r in rows]
        except Exception as e:
            logger.error(f"get_monthly failed: {e}")
            return []

    def get_by_provider(self, days: int = 30) -> list:
        """Cost breakdown by provider."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            since = (datetime.utcnow() - timedelta(days=days)).isoformat()
            rows = conn.execute(
                """SELECT COALESCE(provider_canonical, provider) as provider,
                     SUM(input_tokens) as input_tokens,
                     SUM(output_tokens) as output_tokens,
                     SUM(cost_usd) as cost,
                     COUNT(*) as requests
                   FROM token_usage WHERE timestamp >= ?
                   GROUP BY COALESCE(provider_canonical, provider) ORDER BY cost DESC""",
                (since,),
            ).fetchall()
            conn.close()
            return [{"provider": r["provider"], "input_tokens": r["input_tokens"],
                     "output_tokens": r["output_tokens"],
                     "cost": round(r["cost"], 4), "requests": r["requests"]} for r in rows]
        except Exception as e:
            logger.error(f"get_by_provider failed: {e}")
            return []

    def get_by_feature(self, days: int = 30) -> list:
        """Cost breakdown by feature."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            since = (datetime.utcnow() - timedelta(days=days)).isoformat()
            rows = conn.execute(
                """SELECT feature,
                     SUM(input_tokens) as input_tokens,
                     SUM(output_tokens) as output_tokens,
                     SUM(cost_usd) as cost,
                     COUNT(*) as requests
                   FROM token_usage WHERE timestamp >= ?
                   GROUP BY feature ORDER BY cost DESC""",
                (since,),
            ).fetchall()
            conn.close()
            return [{"feature": r["feature"], "input_tokens": r["input_tokens"],
                     "output_tokens": r["output_tokens"],
                     "cost": round(r["cost"], 4), "requests": r["requests"]} for r in rows]
        except Exception as e:
            logger.error(f"get_by_feature failed: {e}")
            return []

    def get_by_business(self, days: int = 30) -> list:
        """Cost breakdown by business unit."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            since = (datetime.utcnow() - timedelta(days=days)).isoformat()
            rows = conn.execute(
                """SELECT business,
                     SUM(input_tokens) as input_tokens,
                     SUM(output_tokens) as output_tokens,
                     SUM(cost_usd) as cost,
                     COUNT(*) as requests
                   FROM token_usage WHERE timestamp >= ?
                   GROUP BY business ORDER BY cost DESC""",
                (since,),
            ).fetchall()
            conn.close()
            return [{"business": r["business"], "input_tokens": r["input_tokens"],
                     "output_tokens": r["output_tokens"],
                     "cost": round(r["cost"], 4), "requests": r["requests"]} for r in rows]
        except Exception as e:
            logger.error(f"get_by_business failed: {e}")
            return []

    def get_recent_transactions(self, limit: int = 50) -> list:
        """Get recent individual transactions for the log view."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT id, timestamp,
                     COALESCE(model_canonical, model) as model,
                     COALESCE(provider_canonical, provider) as provider,
                     input_tokens, output_tokens,
                     cost_usd, endpoint, feature, business, source,
                     request_id, attempt_id, raw_provider, raw_model, source_module, route_name, lane,
                     status, http_status, fallback_of, token_source, total_tokens, estimated_cost, provider_reported_cost, is_legacy
                   FROM token_usage ORDER BY timestamp DESC LIMIT ?""",
                (limit,),
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"get_recent_transactions failed: {e}")
            return []

    def get_bleed_watch_alerts(self, hours: int = 24) -> list[dict]:
        """Detect likely token bleed or accounting integrity anomalies."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            since = (datetime.utcnow() - timedelta(hours=max(1, hours))).isoformat()
            state = load_routing_state()
            selected_provider = self.canonical_provider(state.selected_provider)
            alerts: list[dict] = []

            def add_alert(kind: str, provider: str, model: str, lane: str, count: int, last_seen: str, recommendation: str, source_module: str = "unknown"):
                alerts.append(
                    {
                        "kind": kind,
                        "source_module": source_module,
                        "provider_model": f"{provider}/{model}",
                        "lane": lane or "unknown",
                        "count": int(count or 0),
                        "last_seen": last_seen,
                        "recommended_action": recommendation,
                    }
                )

            # 401/403/429 bursts
            for row in conn.execute(
                """SELECT COALESCE(provider_canonical, provider) as provider, COALESCE(model_canonical, model) as model,
                          lane, source_module, COUNT(*) as cnt, MAX(timestamp) as last_seen
                   FROM token_usage
                   WHERE timestamp >= ? AND http_status IN (401,403,429)
                   GROUP BY COALESCE(provider_canonical, provider), COALESCE(model_canonical, model), lane, source_module
                   HAVING COUNT(*) >= 3""",
                (since,),
            ).fetchall():
                add_alert(
                    "auth_or_quota_burst",
                    row["provider"],
                    row["model"],
                    row["lane"],
                    row["cnt"],
                    row["last_seen"],
                    "Disable provider or fix key/quota immediately. Prevent retries until healthy.",
                    row["source_module"] or "unknown",
                )

            # Same request under multiple models
            for row in conn.execute(
                """SELECT request_id, COUNT(DISTINCT COALESCE(model_canonical, model)) as model_count,
                          MAX(timestamp) as last_seen
                   FROM token_usage
                   WHERE timestamp >= ? AND request_id != ''
                   GROUP BY request_id
                   HAVING COUNT(DISTINCT COALESCE(model_canonical, model)) > 1""",
                (since,),
            ).fetchall():
                add_alert(
                    "request_multi_model",
                    "multiple",
                    row["request_id"],
                    state.lane,
                    row["model_count"],
                    row["last_seen"],
                    "Verify one-request/one-final-result logging and fallback normalization.",
                    "token_tracker",
                )

            # External Hermes / v10 usage crossing into main lane
            for marker, kind, recommendation in [
                ("hermes", "external_hermes_usage", "Separate Hermes lane totals from founder stable/main totals."),
                ("v10", "v10_usage_in_main", "Stop/disable v10 workers or route v10 traffic to isolated lane."),
            ]:
                for row in conn.execute(
                    """SELECT COALESCE(provider_canonical, provider) as provider, COALESCE(model_canonical, model) as model,
                              lane, source_module, COUNT(*) as cnt, MAX(timestamp) as last_seen
                       FROM token_usage
                       WHERE timestamp >= ? AND lower(source_module) LIKE ?
                       GROUP BY COALESCE(provider_canonical, provider), COALESCE(model_canonical, model), lane, source_module""",
                    (since, f"%{marker}%"),
                ).fetchall():
                    add_alert(kind, row["provider"], row["model"], row["lane"], row["cnt"], row["last_seen"], recommendation, row["source_module"] or "unknown")

            # Autonomous non-user modules consuming tokens
            for row in conn.execute(
                """SELECT source_module, COALESCE(provider_canonical, provider) as provider,
                          COALESCE(model_canonical, model) as model, lane, COUNT(*) as cnt, MAX(timestamp) as last_seen
                   FROM token_usage
                   WHERE timestamp >= ?
                     AND lower(COALESCE(source_module, '')) NOT IN ('ai_router', 'max_chat_response')
                   GROUP BY source_module, COALESCE(provider_canonical, provider), COALESCE(model_canonical, model), lane
                   HAVING COUNT(*) >= 2""",
                (since,),
            ).fetchall():
                add_alert(
                    "autonomous_usage_without_visible_request",
                    row["provider"],
                    row["model"],
                    row["lane"],
                    row["cnt"],
                    row["last_seen"],
                    "Review scheduler/worker source and require explicit founder enable before running.",
                    row["source_module"] or "unknown",
                )

            # MiniMax called while non-MiniMax selected
            if selected_provider != "minimax":
                row = conn.execute(
                    """SELECT COUNT(*) as cnt, MAX(timestamp) as last_seen
                       FROM token_usage
                       WHERE timestamp >= ? AND COALESCE(provider_canonical, provider) = 'minimax'""",
                    (since,),
                ).fetchone()
                if row and int(row["cnt"] or 0) > 0:
                    add_alert(
                        "minimax_called_while_not_selected",
                        "minimax",
                        "MiniMax-M2.7",
                        state.lane,
                        row["cnt"],
                        row["last_seen"],
                        "Audit routing bypass: selected provider is not MiniMax.",
                        "routing",
                    )

            # Provider called while kill-switched currently
            for provider in ("minimax", "deepseek", "claude", "groq", "gemini", "openai", "xai", "ollama", "openrouter", "qwen"):
                if not provider_disabled(provider):
                    continue
                row = conn.execute(
                    """SELECT COUNT(*) as cnt, MAX(timestamp) as last_seen
                       FROM token_usage
                       WHERE timestamp >= ? AND COALESCE(provider_canonical, provider) = ?""",
                    (since, provider),
                ).fetchone()
                if row and int(row["cnt"] or 0) > 0:
                    add_alert(
                        "provider_called_while_disabled",
                        provider,
                        "any",
                        state.lane,
                        row["cnt"],
                        row["last_seen"],
                        "Blocked provider still received traffic; inspect bypass path immediately.",
                        "routing",
                    )

            conn.close()
            return alerts
        except Exception as e:
            logger.error(f"get_bleed_watch_alerts failed: {e}")
            return []

    def update_budget(self, monthly_budget: float = None, alert_threshold: float = None,
                      auto_switch: bool = None, auto_switch_threshold: float = None):
        try:
            conn = sqlite3.connect(self.db_path)
            updates = []
            params = []
            if monthly_budget is not None:
                updates.append("monthly_budget = ?")
                params.append(monthly_budget)
            if alert_threshold is not None:
                updates.append("alert_threshold = ?")
                params.append(alert_threshold)
            if auto_switch is not None:
                updates.append("auto_switch_to_local = ?")
                params.append(int(auto_switch))
            if auto_switch_threshold is not None:
                updates.append("auto_switch_threshold = ?")
                params.append(auto_switch_threshold)
            if updates:
                conn.execute(f"UPDATE budget_config SET {', '.join(updates)} WHERE id = 1", params)
                conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Budget update failed: {e}")

    def should_switch_to_local(self) -> bool:
        """Check if budget threshold is reached and auto-switch is enabled."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            budget = conn.execute("SELECT * FROM budget_config WHERE id = 1").fetchone()
            if not budget or not budget["auto_switch_to_local"]:
                conn.close()
                return False
            month_start = datetime.utcnow().replace(day=1).strftime("%Y-%m-%d")
            row = conn.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) as cost FROM token_usage WHERE timestamp >= ?",
                (month_start,),
            ).fetchone()
            conn.close()
            spent = row["cost"]
            return (spent / budget["monthly_budget"]) >= budget["auto_switch_threshold"]
        except Exception:
            return False


    def get_tenant_usage(self, tenant_id: str, days: int = 30) -> dict:
        """Get aggregated token usage stats for a specific tenant."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            since = (datetime.utcnow() - timedelta(days=days)).isoformat()

            row = conn.execute(
                """SELECT
                     COALESCE(SUM(input_tokens), 0) as total_input,
                     COALESCE(SUM(output_tokens), 0) as total_output,
                     COALESCE(SUM(cost_usd), 0) as total_cost,
                     COUNT(*) as total_requests
                   FROM token_usage WHERE tenant_id = ? AND timestamp >= ?""",
                (tenant_id, since),
            ).fetchone()

            # Current month usage
            month_start = datetime.utcnow().replace(day=1).strftime("%Y-%m-%d")
            month_row = conn.execute(
                """SELECT
                     COALESCE(SUM(input_tokens), 0) as input_tokens,
                     COALESCE(SUM(output_tokens), 0) as output_tokens,
                     COALESCE(SUM(cost_usd), 0) as cost
                   FROM token_usage WHERE tenant_id = ? AND timestamp >= ?""",
                (tenant_id, month_start),
            ).fetchone()

            # Per-model breakdown
            model_rows = conn.execute(
                """SELECT model,
                     SUM(input_tokens) as input_tokens,
                     SUM(output_tokens) as output_tokens,
                     SUM(cost_usd) as cost,
                     COUNT(*) as requests
                   FROM token_usage WHERE tenant_id = ? AND timestamp >= ?
                   GROUP BY model ORDER BY cost DESC""",
                (tenant_id, since),
            ).fetchall()

            conn.close()

            total_input = row["total_input"]
            total_output = row["total_output"]

            return {
                "tenant_id": tenant_id,
                "period_days": days,
                "total": {
                    "input_tokens": total_input,
                    "output_tokens": total_output,
                    "total_tokens": total_input + total_output,
                    "cost_usd": round(row["total_cost"], 4),
                    "requests": row["total_requests"],
                },
                "current_month": {
                    "input_tokens": month_row["input_tokens"],
                    "output_tokens": month_row["output_tokens"],
                    "total_tokens": month_row["input_tokens"] + month_row["output_tokens"],
                    "cost_usd": round(month_row["cost"], 4),
                },
                "by_model": [
                    {
                        "model": r["model"],
                        "input_tokens": r["input_tokens"],
                        "output_tokens": r["output_tokens"],
                        "cost": round(r["cost"], 4),
                        "requests": r["requests"],
                    }
                    for r in model_rows
                ],
            }
        except Exception as e:
            logger.error(f"get_tenant_usage failed: {e}")
            return {
                "tenant_id": tenant_id,
                "period_days": days,
                "total": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0, "requests": 0},
                "current_month": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0},
                "by_model": [],
            }

    def get_tenant_budget_status(self, tenant_id: str, tier_id: str) -> dict:
        """Get budget status for a tenant compared to their tier limits."""
        from app.config.pricing_tiers import get_tier, get_token_budget

        tier = get_tier(tier_id)
        token_budget = get_token_budget(tier_id)

        # Get current month token usage
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            month_start = datetime.utcnow().replace(day=1).strftime("%Y-%m-%d")
            row = conn.execute(
                """SELECT
                     COALESCE(SUM(input_tokens), 0) as input_tokens,
                     COALESCE(SUM(output_tokens), 0) as output_tokens,
                     COALESCE(SUM(cost_usd), 0) as cost
                   FROM token_usage WHERE tenant_id = ? AND timestamp >= ?""",
                (tenant_id, month_start),
            ).fetchone()
            conn.close()

            total_tokens = row["input_tokens"] + row["output_tokens"]
            cost_usd = round(row["cost"], 4)
        except Exception as e:
            logger.error(f"get_tenant_budget_status failed: {e}")
            total_tokens = 0
            cost_usd = 0.0

        # Calculate budget percentage (unlimited = -1)
        if token_budget == -1:
            percent_used = 0.0
            over_budget = False
        else:
            percent_used = round((total_tokens / token_budget) * 100, 1) if token_budget > 0 else 0.0
            over_budget = total_tokens >= token_budget

        return {
            "tenant_id": tenant_id,
            "tier": tier_id,
            "tier_name": tier["name"],
            "token_budget": token_budget,
            "tokens_used": total_tokens,
            "tokens_remaining": max(0, token_budget - total_tokens) if token_budget != -1 else -1,
            "percent_used": percent_used,
            "over_budget": over_budget,
            "cost_usd": cost_usd,
            "price_monthly": tier["price_monthly"],
        }

    def check_tenant_within_budget(self, tenant_id: str, tier_id: str) -> bool:
        """Quick check: is this tenant still within their tier's token budget?"""
        status = self.get_tenant_budget_status(tenant_id, tier_id)
        return not status["over_budget"]


# Singleton
token_tracker = TokenTracker()
