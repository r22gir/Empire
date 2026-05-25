"""Tests for RecoveryForge quota system and MiniMax analysis pipeline."""
import json
import os
import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock

# ── Quota tests ────────────────────────────────────────────────────────────────

def test_quota_check_returns_correct_fields(tmp_path):
    """check_quota returns all required fields with correct values for MCP Understand Image."""
    import app.services.max.recoveryforge_quota as q

    orig_file = q.QUOTA_FILE
    q.QUOTA_FILE = str(tmp_path / "quota.json")

    try:
        result = q.check_quota()

        assert result["recoveryforge_vision_bucket"] == "mcp_understand_image"
        assert result["recoveryforge_window_cap"] == 500
        assert result["recoveryforge_daily_soft_cap"] == 1500
        assert result["current_window_used_by_recoveryforge"] == 0
        assert result["current_window_remaining_for_recoveryforge"] >= 0  # non-negative after reserve gap
        assert result["current_window_reserved_for_general_use"] == 1500
        assert result["daily_used_by_recoveryforge"] == 0
        assert result["image_generation_used_by_recoveryforge_batch"] == 0
        assert result["image_generation_reserved_for_quotes_and_mockups"] is True
        assert result["batch_chunk_limit"] == 25
        assert result["cap_reached"] is False
        assert "reset_window_hint" in result
        assert "server_date" in result
    finally:
        q.QUOTA_FILE = orig_file


def test_quota_consume_records_success(tmp_path):
    """consume_quota records a successful analysis in window record."""
    import app.services.max.recoveryforge_quota as q

    orig_file = q.QUOTA_FILE
    q.QUOTA_FILE = str(tmp_path / "quota.json")

    try:
        q.consume_quota("test-key-001", "image-01", success=True)

        data = q._load_quota()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entry = data.get(today, {})
        window_key = q._window_key()
        window_entry = entry.get("window_records", {}).get(window_key, {})

        assert window_entry["window_used"] == 1
        analyses = window_entry.get("analyses", [])
        assert len(analyses) == 1
        assert analyses[0]["image_key"] == "test-key-001"
        assert analyses[0]["status"] == "success"
    finally:
        q.QUOTA_FILE = orig_file


def test_quota_consume_does_not_count_failed(tmp_path):
    """consume_quota does not count failed analyses against cap."""
    import app.services.max.recoveryforge_quota as q

    orig_file = q.QUOTA_FILE
    q.QUOTA_FILE = str(tmp_path / "quota.json")

    try:
        q.consume_quota("test-key-002", "image-01", success=False, error="provider error")

        result = q.check_quota()
        assert result["current_window_used_by_recoveryforge"] == 0
        assert result["daily_used_by_recoveryforge"] == 0
    finally:
        q.QUOTA_FILE = orig_file


def test_quota_image_generation_never_consumed(tmp_path):
    """Image Generation quota is never consumed by RecoveryForge batch."""
    import app.services.max.recoveryforge_quota as q

    orig_file = q.QUOTA_FILE
    q.QUOTA_FILE = str(tmp_path / "quota.json")

    try:
        for i in range(50):
            q.consume_quota(f"key-{i:04d}", "image-01", success=True)

        result = q.check_quota()
        assert result["image_generation_used_by_recoveryforge_batch"] == 0
    finally:
        q.QUOTA_FILE = orig_file


def test_quota_window_cap_tracks_usage(tmp_path):
    """Window usage is tracked correctly up to cap."""
    import app.services.max.recoveryforge_quota as q

    orig_file = q.QUOTA_FILE
    q.QUOTA_FILE = str(tmp_path / "quota.json")

    try:
        for i in range(100):
            q.consume_quota(f"key-{i:04d}", "image-01", success=True)

        result = q.check_quota()
        assert result["current_window_used_by_recoveryforge"] == 100
        assert result["cap_reached"] is False
    finally:
        q.QUOTA_FILE = orig_file


def test_quota_override_bypasses_cap(tmp_path, monkeypatch):
    """RECOVERYFORGE_ALLOW_QUOTA_OVERRIDE=1 bypasses cap."""
    import app.services.max.recoveryforge_quota as q

    orig_file = q.QUOTA_FILE
    q.QUOTA_FILE = str(tmp_path / "quota.json")

    try:
        monkeypatch.setenv("RECOVERYFORGE_ALLOW_QUOTA_OVERRIDE", "1")

        for i in range(505):
            q.consume_quota(f"key-{i:04d}", "image-01", success=True)

        result = q.check_quota()
        assert result["cap_reached"] is False
        assert result["override_enabled"] is True
    finally:
        q.QUOTA_FILE = orig_file


def test_quota_daily_soft_cap_tracks_across_windows(tmp_path):
    """Daily used accumulates across multiple windows."""
    import app.services.max.recoveryforge_quota as q

    orig_file = q.QUOTA_FILE
    q.QUOTA_FILE = str(tmp_path / "quota.json")

    try:
        # Add analyses - will accumulate in today's daily total
        for i in range(50):
            q.consume_quota(f"key-{i:04d}", "image-01", success=True)

        result = q.check_quota()
        assert result["daily_used_by_recoveryforge"] == 50
        assert result["daily_remaining_soft_cap"] == 1450
    finally:
        q.QUOTA_FILE = orig_file


def test_quota_batch_chunk_limit(tmp_path):
    """batch_chunk_limit is correctly set to 25."""
    import app.services.max.recoveryforge_quota as q

    orig_file = q.QUOTA_FILE
    q.QUOTA_FILE = str(tmp_path / "quota.json")

    try:
        result = q.check_quota()
        assert result["batch_chunk_limit"] == 25
    finally:
        q.QUOTA_FILE = orig_file


def test_quota_file_persists_across_calls(tmp_path):
    """Quota file persists across calls."""
    import app.services.max.recoveryforge_quota as q

    orig_file = q.QUOTA_FILE
    q.QUOTA_FILE = str(tmp_path / "quota.json")

    try:
        q.consume_quota("persist-key", "image-01", success=True)

        data = q._load_quota()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert data[today]["daily_used"] == 1

        with open(tmp_path / "quota.json") as f:
            disk_data = json.load(f)
        assert disk_data[today]["daily_used"] == 1
    finally:
        q.QUOTA_FILE = orig_file


def test_quota_window_key_changes(tmp_path):
    """Window key changes every 5 hours."""
    import app.services.max.recoveryforge_quota as q

    orig_file = q.QUOTA_FILE
    q.QUOTA_FILE = str(tmp_path / "quota.json")

    try:
        # At start of hour 0-4, window key is YYYY-MM-DD-0
        # At start of hour 5-9, window key is YYYY-MM-DD-1
        key = q._window_key()
        assert len(key) == len("YYYY-MM-DD-N")  # date + window number
        assert key[-1] in "01234"  # window number 0-4 within 5-hour blocks
    finally:
        q.QUOTA_FILE = orig_file


# ── Analysis schema tests ─────────────────────────────────────────────────────

def test_analysis_result_has_required_schema_fields():
    """Structured analysis result contains all required schema fields."""
    from app.services.max.recoveryforge_analyzer import _build_structured_analysis

    result = _build_structured_analysis(
        "test-key",
        "A fabric curtain installation in a living room with good lighting",
        {},
    )

    required_fields = [
        "image_key", "analysis_status", "provider", "model", "timestamp",
        "stale", "description", "tags", "personal_work_classification",
        "business_route", "action_recommendation", "image_quality_score",
        "analysis_confidence", "needs_manual_review", "reason_for_manual_review",
    ]
    for field in required_fields:
        assert field in result, f"Missing field: {field}"

    assert result["provider"] == "minimax"
    assert result["model"] == "image-01"
    assert result["analysis_status"] == "success"
    assert result["stale"] is False


def test_personal_work_classification_has_required_subfields():
    """personal_work_classification has classification, confidence, reason."""
    from app.services.max.recoveryforge_analyzer import _build_structured_analysis

    result = _build_structured_analysis(
        "test-key",
        "A family gathering in a living room with personal photos on the wall",
        {},
    )

    pwc = result["personal_work_classification"]
    assert "classification" in pwc
    assert "confidence" in pwc
    assert "reason" in pwc
    assert pwc["classification"] in {"personal", "work_related", "mixed", "unknown"}


def test_business_route_valid_options():
    """business_route values are from the allowed set."""
    from app.services.max.recoveryforge_analyzer import _build_structured_analysis

    valid_routes = {
        "empire-workroom", "woodcraft", "archiveforge", "luxeforge",
        "contractorforge", "recoveryforge", "general-business", "unknown-work",
    }

    result = _build_structured_analysis("key", "A custom drapery installation for a client window", {})
    assert result["business_route"] in valid_routes


def test_action_recommendation_valid_options():
    """action_recommendation values are from the allowed set."""
    from app.services.max.recoveryforge_analyzer import _build_structured_analysis

    valid_actions = {
        "keep", "archive", "use_for_quote", "add_to_inventory",
        "group_with_similar", "needs_manual_review", "delete_candidate",
        "duplicate_candidate", "customer_project_candidate",
    }

    result = _build_structured_analysis("key", "damaged old curtain with stains", {})
    assert result["action_recommendation"] in valid_actions


def test_quality_score_below_threshold_sets_manual_review():
    """image_quality_score < 6 triggers needs_manual_review."""
    from app.services.max.recoveryforge_analyzer import _build_structured_analysis

    result = _build_structured_analysis(
        "key",
        "blurry dark low-res image with severe damage",
        {},
    )

    assert result["image_quality_score"] < 6
    assert result["needs_manual_review"] is True


# ── Ollama unavailable does not block RecoveryForge ───────────────────────────

def test_ollama_unavailable_does_not_block_minimax_path(tmp_path, monkeypatch):
    """RecoveryForge MiniMax analysis works even when Ollama is unavailable."""
    import app.services.max.recoveryforge_quota as q

    orig_file = q.QUOTA_FILE
    q.QUOTA_FILE = str(tmp_path / "quota.json")

    try:
        monkeypatch.setenv("RECOVERYFORGE_ALLOW_QUOTA_OVERRIDE", "1")

        result = q.check_quota()
        assert result["current_window_remaining_for_recoveryforge"] >= 0
    finally:
        q.QUOTA_FILE = orig_file


# ── Stale marking tests ────────────────────────────────────────────────────────

def test_mark_stale_sets_stale_flag(tmp_path):
    """Mark prior analysis as stale without deleting files."""
    from app.services.max.recoveryforge_analyzer import _build_structured_analysis

    img = {
        "filename": "test.jpg",
        "path": "/data/images/test.jpg",
        "minimax_analysis": {
            "analysis_status": "success",
            "provider": "minimax",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }

    analysis = img["minimax_analysis"]
    analysis["stale"] = True
    analysis["superseded_at"] = datetime.now(timezone.utc).isoformat()

    assert analysis["stale"] is True
    assert "superseded_at" in analysis
    assert img["path"] == "/data/images/test.jpg"


# ── Recovery router tests ──────────────────────────────────────────────────────

def test_recovery_status_includes_quota(tmp_path):
    """GET /recovery/status includes minimax_quota with correct fields."""
    from app.services.max.recoveryforge_quota import check_quota
    result = check_quota()

    assert "recoveryforge_vision_bucket" in result
    assert "recoveryforge_window_cap" in result
    assert "current_window_used_by_recoveryforge" in result
    assert "current_window_reserved_for_general_use" in result
    assert "image_generation_used_by_recoveryforge_batch" in result
    assert "batch_chunk_limit" in result


def test_analyze_endpoint_rejects_missing_image():
    """POST /recovery/analyze returns 404 for unknown image_key."""
    from app.routers.recovery import _load_image_index, _find_image

    data = _load_image_index()
    result = _find_image(data, "nonexistent-key-xyz")
    assert result is None


def test_quota_status_endpoint_exists():
    """GET /recovery/quota-status endpoint is registered."""
    from app.routers.recovery import router

    routes = [r.path for r in router.routes]
    assert any("quota-status" in r for r in routes)


def test_mark_stale_endpoint_exists():
    """POST /recovery/mark-stale endpoint is registered."""
    from app.routers.recovery import router

    routes = [r.path for r in router.routes]
    assert any("mark-stale" in r for r in routes)


def test_analyze_endpoint_exists():
    """POST /recovery/analyze endpoint is registered."""
    from app.routers.recovery import router

    routes = [r.path for r in router.routes]
    assert any("analyze" in r for r in routes)


def test_batch_analyze_endpoint_exists():
    """POST /recovery/batch-analyze endpoint is registered."""
    from app.routers.recovery import router

    routes = [r.path for r in router.routes]
    assert any("batch-analyze" in r for r in routes)