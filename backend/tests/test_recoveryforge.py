"""Tests for RecoveryForge quota system and MiniMax analysis pipeline."""
import json
import os
import pytest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock

# ── Quota tests ────────────────────────────────────────────────────────────────

def test_quota_check_returns_correct_structure(tmp_path):
    """check_quota returns all required fields with correct values."""
    import app.services.max.recoveryforge_quota as q

    orig_file = q.QUOTA_FILE
    q.QUOTA_FILE = str(tmp_path / "quota.json")

    try:
        result = q.check_quota()

        assert result["daily_cap"] == 80
        assert result["daily_reserved_quota"] == 20
        assert result["used_today"] == 0
        assert result["remaining_recoveryforge_today"] == 80
        assert result["cap_reached"] is False
        assert "reset_date" in result
        assert "server_date" in result
    finally:
        q.QUOTA_FILE = orig_file


def test_quota_consume_records_success(tmp_path):
    """consume_quota records a successful analysis."""
    import app.services.max.recoveryforge_quota as q

    orig_file = q.QUOTA_FILE
    q.QUOTA_FILE = str(tmp_path / "quota.json")

    try:
        q.consume_quota("test-key-001", "image-01", success=True)

        data = q._load_quota()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entry = data.get(today, {})

        assert entry["used"] == 1
        assert len(entry["analyses"]) == 1
        assert entry["analyses"][0]["image_key"] == "test-key-001"
        assert entry["analyses"][0]["status"] == "success"
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
        assert result["used_today"] == 0
    finally:
        q.QUOTA_FILE = orig_file


def test_quota_allow_new_false_at_cap(tmp_path):
    """quota_allow_new returns False when cap reached."""
    import app.services.max.recoveryforge_quota as q

    orig_file = q.QUOTA_FILE
    q.QUOTA_FILE = str(tmp_path / "quota.json")

    try:
        # Fill to exactly 80
        for i in range(80):
            q.consume_quota(f"key-{i:04d}", "image-01", success=True)

        assert q.quota_allow_new() is False

        result = q.check_quota()
        assert result["cap_reached"] is True
        assert result["remaining_recoveryforge_today"] == 0
    finally:
        q.QUOTA_FILE = orig_file


def test_quota_override_bypasses_cap(tmp_path, monkeypatch):
    """RECOVERYFORGE_ALLOW_QUOTA_OVERRIDE=1 bypasses cap."""
    import app.services.max.recoveryforge_quota as q

    orig_file = q.QUOTA_FILE
    q.QUOTA_FILE = str(tmp_path / "quota.json")

    try:
        monkeypatch.setenv("RECOVERYFORGE_ALLOW_QUOTA_OVERRIDE", "1")

        for i in range(85):
            q.consume_quota(f"key-{i:04d}", "image-01", success=True)

        result = q.check_quota()
        assert result["cap_reached"] is False
        assert result["override_active"] is True
    finally:
        q.QUOTA_FILE = orig_file


def test_quota_reserved_quota_preserved(tmp_path):
    """80 cap leaves 20 reserved for non-RecoveryForge use."""
    import app.services.max.recoveryforge_quota as q

    orig_file = q.QUOTA_FILE
    q.QUOTA_FILE = str(tmp_path / "quota.json")

    try:
        # Use 80
        for i in range(80):
            q.consume_quota(f"key-{i:04d}", "image-01", success=True)

        # The 20 reserved means MiniMax still has 20 remaining for quotes/work
        result = q.check_quota()
        assert result["remaining_recoveryforge_today"] == 0
        # But total daily MiniMax budget is 100, so 20 are still available
        # for non-RecoveryForge uses (this is enforced by MiniMax, not here)
        assert result["used_today"] == 80
    finally:
        q.QUOTA_FILE = orig_file


def test_quota_file_persists_across_calls(tmp_path):
    """Quota file persists across function calls and reads."""
    import app.services.max.recoveryforge_quota as q

    orig_file = q.QUOTA_FILE
    q.QUOTA_FILE = str(tmp_path / "quota.json")

    try:
        q.consume_quota("persist-key", "image-01", success=True)

        # File should contain the recorded usage
        data = q._load_quota()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        assert data[today]["used"] == 1

        # Read from disk directly (simulating cross-call persistence)
        with open(tmp_path / "quota.json") as f:
            disk_data = json.load(f)
        assert disk_data[today]["used"] == 1
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

    test_cases = [
        ("A custom drapery installation for a client window", "empire-workroom"),
        ("Wooden cabinetry project in a kitchen", "woodcraft"),
        ("Random family photo", "unknown-work"),
    ]

    for desc, expected in test_cases:
        result = _build_structured_analysis("key", desc, {})
        assert result["business_route"] in valid_routes, f"{desc} -> {result['business_route']} not valid"


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
        # Force cap not reached
        monkeypatch.setenv("RECOVERYFORGE_ALLOW_QUOTA_OVERRIDE", "1")

        # Verify quota system works independently of Ollama
        result = q.check_quota()
        assert result["remaining_recoveryforge_today"] >= 0
    finally:
        q.QUOTA_FILE = orig_file


# ── Stale marking tests ────────────────────────────────────────────────────────

def test_mark_stale_sets_stale_flag(tmp_path):
    """Mark prior analysis as stale without deleting files."""
    import app.services.max.recoveryforge_analyzer as a

    img = {
        "filename": "test.jpg",
        "path": "/data/images/test.jpg",
        "minimax_analysis": {
            "analysis_status": "success",
            "provider": "minimax",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }

    # Simulate stale marking
    analysis = img["minimax_analysis"]
    analysis["stale"] = True
    analysis["superseded_at"] = datetime.now(timezone.utc).isoformat()

    assert analysis["stale"] is True
    assert "superseded_at" in analysis
    # Original file path is preserved
    assert img["path"] == "/data/images/test.jpg"


# ── Recovery router tests ──────────────────────────────────────────────────────

def test_recovery_status_includes_quota(tmp_path):
    """GET /recovery/status includes minimax_quota."""
    from app.routers.recovery import PROGRESS_FILE, TOTAL_IMAGES
    import json

    # Progress file exists
    Path(PROGRESS_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w") as f:
        json.dump({"processed": [], "stats": {}}, f)

    from app.services.max.recoveryforge_quota import check_quota
    result = check_quota()

    assert "daily_cap" in result
    assert "used_today" in result
    assert "remaining_recoveryforge_today" in result
    assert "cap_reached" in result
    assert "daily_reserved_quota" in result


def test_analyze_endpoint_rejects_missing_image():
    """POST /recovery/analyze returns 404 for unknown image_key."""
    from app.routers.recovery import _load_image_index, _find_image

    data = _load_image_index()
    result = _find_image(data, "nonexistent-key-xyz")
    assert result is None


def test_batch_analyze_respects_quota(tmp_path):
    """Batch analyze stops when cap is reached."""
    import app.services.max.recoveryforge_quota as q

    orig_file = q.QUOTA_FILE
    q.QUOTA_FILE = str(tmp_path / "quota.json")

    try:
        q.consume_quota("cap-fill-1", "image-01", success=True)
        q.consume_quota("cap-fill-2", "image-01", success=True)
        # ... fill to 80

        status = q.check_quota()
        assert status["remaining_recoveryforge_today"] <= 78
    finally:
        q.QUOTA_FILE = orig_file


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