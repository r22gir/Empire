"""Tests for AI token tracker free-tier pricing, quota tracking, rollover, and endpoints."""

from datetime import datetime
import pytest

from app.services.max.free_tiers import (
    FREE_TIER_TABLE,
    check_free_tier_quota,
    get_all_free_tier_status,
    get_free_tier_spec,
    is_financial_or_client_desk,
    is_free_tier_model,
    is_free_tier_quota_exhausted,
    record_free_tier_usage,
)
from app.services.max.token_tracker import TokenTracker, calculate_cost


class TestFreeTierCostCalculation:
    """Free tier models must return $0.00 cost."""

    def test_free_tier_models_calculate_zero_cost(self):
        # Groq free OSS models
        assert calculate_cost("openai/gpt-oss-120b", 5000, 2000) == 0.0
        assert calculate_cost("openai/gpt-oss-20b", 5000, 2000) == 0.0
        assert calculate_cost("qwen/qwen3.8-27b", 5000, 2000) == 0.0

        # Gemini free models
        assert calculate_cost("gemini-2.5-flash", 10000, 4000) == 0.0
        assert calculate_cost("gemini-2.5-flash-lite", 10000, 4000) == 0.0
        assert calculate_cost("gemini-3.5-flash", 10000, 4000) == 0.0

        # OpenRouter free models
        assert calculate_cost("nvidia/nemotron-3-super-120b-a12b:free", 10000, 1000) == 0.0
        assert calculate_cost("google/gemma-4-31b-it:free", 10000, 1000) == 0.0
        assert calculate_cost("cohere/north-mini-code:free", 10000, 1000) == 0.0
        assert calculate_cost("openrouter/free", 10000, 1000) == 0.0
        assert calculate_cost("custom-model:free", 5000, 5000) == 0.0

    def test_groq_llama_pricing_retains_paid_cost(self):
        """Groq Llama 3.3 pricing must stay paid since only OSS models are free."""
        # 1M input ($0.59) + 1M output ($0.79) = $1.38
        cost = calculate_cost("llama-3.3-70b-versatile", 1_000_000, 1_000_000)
        assert cost == pytest.approx(1.38, rel=1e-2)
        assert not is_free_tier_model("llama-3.3-70b-versatile")

        cost_named = calculate_cost("groq-llama-3.3-70b", 1_000_000, 1_000_000)
        assert cost_named == pytest.approx(1.38, rel=1e-2)
        assert not is_free_tier_model("groq-llama-3.3-70b")


class TestFreeTierTableStructure:
    """Verify FREE_TIER_TABLE entries and required fields."""

    def test_free_tier_table_fields(self):
        assert len(FREE_TIER_TABLE) >= 10
        for spec in FREE_TIER_TABLE:
            assert spec.provider in ("groq", "gemini", "openrouter")
            assert spec.cost_basis == "free_tier"
            assert spec.rpm > 0
            assert spec.rpd > 0
            assert spec.tpd > 0
            assert spec.reset_tz in ("America/Los_Angeles", "UTC")
            assert spec.source_url.startswith("http")
            assert spec.verified_date == "2026-10-10"
            assert spec.use_cases != ""
            assert spec.not_for != ""

    def test_get_free_tier_spec_matching(self):
        spec_groq = get_free_tier_spec("openai/gpt-oss-120b", "groq")
        assert spec_groq is not None
        assert spec_groq.provider == "groq"
        assert spec_groq.rpd == 1000

        spec_wildcard = get_free_tier_spec("deepseek/deepseek-r1:free", "openrouter")
        assert spec_wildcard is not None
        assert spec_wildcard.cost_basis == "free_tier"


class TestQuotaTrackingAndRollover:
    """Test quota increment, warning at 80%, exhausted at 100%, and rollover."""

    def test_quota_rollover_minute_and_daily(self, tmp_path):
        db_path = str(tmp_path / "test_rollover.db")

        # Minute 1: Record 10 requests
        t1 = datetime(2026, 10, 10, 10, 0, 0)
        res1 = record_free_tier_usage("openai/gpt-oss-120b", "groq", requests=10, tokens=5000, db_path=db_path, now=t1)
        assert res1["requests_minute"] == 10
        assert res1["requests_day"] == 10
        assert res1["tokens_day"] == 5000

        # Minute 2: Same day, next minute -> minute rolls over to fresh count
        t2 = datetime(2026, 10, 10, 10, 1, 0)
        res2 = record_free_tier_usage("openai/gpt-oss-120b", "groq", requests=5, tokens=2000, db_path=db_path, now=t2)
        assert res2["requests_minute"] == 5  # minute reset
        assert res2["requests_day"] == 15    # daily accumulated
        assert res2["tokens_day"] == 7000

        # Next Day: Date rolls over -> daily counters reset
        t3 = datetime(2026, 10, 11, 10, 0, 0)
        res3 = record_free_tier_usage("openai/gpt-oss-120b", "groq", requests=7, tokens=1500, db_path=db_path, now=t3)
        assert res3["requests_minute"] == 7
        assert res3["requests_day"] == 7     # reset on new day
        assert res3["tokens_day"] == 1500

    def test_quota_thresholds_warn_and_exhausted(self, tmp_path):
        db_path = str(tmp_path / "test_thresholds.db")
        now = datetime(2026, 10, 10, 14, 0, 0)

        # Groq gpt-oss-120b limit: 30 rpm, 1000 rpd
        # 1. 20 requests in 1 min -> 20/30 RPM (66.7%), normal
        res_normal = record_free_tier_usage("openai/gpt-oss-120b", "groq", requests=20, tokens=1000, db_path=db_path, now=now)
        assert res_normal["status"] == "normal"
        assert res_normal["warn"] is False
        assert res_normal["exhausted"] is False
        assert not is_free_tier_quota_exhausted("openai/gpt-oss-120b", "groq", db_path=db_path, now=now)

        # 2. Add 4 requests in same min -> 24/30 RPM = 80% (warn threshold)
        res_warn = record_free_tier_usage("openai/gpt-oss-120b", "groq", requests=4, tokens=500, db_path=db_path, now=now)
        assert res_warn["status"] == "warn"
        assert res_warn["warn"] is True
        assert res_warn["exhausted"] is False
        assert not is_free_tier_quota_exhausted("openai/gpt-oss-120b", "groq", db_path=db_path, now=now)

        # 3. Add 6 requests in same min -> 30/30 RPM = 100% (exhausted / failover threshold)
        res_exhaust = record_free_tier_usage("openai/gpt-oss-120b", "groq", requests=6, tokens=500, db_path=db_path, now=now)
        assert res_exhaust["status"] == "exhausted"
        assert res_exhaust["warn"] is True
        assert res_exhaust["exhausted"] is True
        assert is_free_tier_quota_exhausted("openai/gpt-oss-120b", "groq", db_path=db_path, now=now) is True

    def test_token_tracker_log_usage_updates_free_tier_usage(self, tmp_path):
        db_path = str(tmp_path / "test_token_tracker_log.db")
        tracker = TokenTracker(db_path=db_path)

        # Log usage of free-tier model
        record = tracker.log_usage(
            model="openai/gpt-oss-20b",
            provider="groq",
            input_tokens=100,
            output_tokens=50,
            feature="analysis",
            business="empire",
        )
        assert record["cost_usd"] == 0.0

        # Check free tier status
        status_list = tracker.get_free_tier_status()
        assert len(status_list) > 0
        oss_20b = next((item for item in status_list if item["model_pattern"] == "openai/gpt-oss-20b"), None)
        assert oss_20b is not None
        assert oss_20b["requests_day"] >= 1
        assert oss_20b["tokens_day"] >= 150


class TestFinancialAndClientDeskGuardrails:
    """Guardrails: client-facing/financial desks must never be routed to free-tier models."""

    def test_desk_guardrail_rules(self):
        # Client-facing / financial desks
        assert is_financial_or_client_desk(desk="forge") is True
        assert is_financial_or_client_desk(desk="finance") is True
        assert is_financial_or_client_desk(desk="workroom") is True
        assert is_financial_or_client_desk(desk="quotes") is True
        assert is_financial_or_client_desk(desk="sales") is True
        assert is_financial_or_client_desk(desk="clients") is True

        # Client-facing / financial features
        assert is_financial_or_client_desk(feature="quote") is True
        assert is_financial_or_client_desk(feature="invoice") is True
        assert is_financial_or_client_desk(feature="client_reply") is True
        assert is_financial_or_client_desk(feature="forge_quote") is True

        # Non-financial desks
        assert is_financial_or_client_desk(desk="dev", feature="code") is False
        assert is_financial_or_client_desk(desk="system", feature="health") is False
        assert is_financial_or_client_desk(desk="research", feature="notes") is False
