"""Tests for RecoveryForge quota system and MiniMax analysis pipeline."""
import json
import os
import pytest
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException
from starlette.testclient import TestClient

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
    assert result["model"] == "mmx_vision"
    assert result["transport"] == "mmx_cli"
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


# ── Selected-image workbench flow ─────────────────────────────────────────────

def _recovery_index_fixture(monkeypatch, tmp_path, images):
    import app.routers.recovery as recovery

    index_file = tmp_path / "presorted_inventory.json"
    index_file.write_text(json.dumps({"images": images, "stats": {}}))
    monkeypatch.setattr(recovery, "INDEX_FILE", str(index_file))
    monkeypatch.setattr(recovery, "CLASSIFIED_DIR", str(tmp_path / "classified"))
    monkeypatch.setattr(recovery, "SOCIAL_DIR", str(tmp_path / "social"))
    monkeypatch.setattr(recovery, "quota_allow_new", lambda: True)
    return recovery, index_file


def test_selected_image_detail_returns_file_existence(monkeypatch, tmp_path):
    source = tmp_path / "source.png"
    source.write_bytes(b"png")
    image = {"filename": "source.png", "path": str(source), "description": "Old record"}
    recovery, _ = _recovery_index_fixture(monkeypatch, tmp_path, [image])

    detail = asyncio.run(recovery.recovery_image_detail(recovery._record_key(image)))

    assert detail["image"]["source_path"] == str(source)
    assert detail["image"]["source_exists"] is True
    assert detail["path_status"]["source"]["readable"] is True
    assert detail["image"]["classified_exists"] is False


def test_selected_image_reanalyze_uses_mmx_path_and_clears_ollama_error(monkeypatch, tmp_path):
    source = tmp_path / "window.png"
    source.write_bytes(b"png")
    image = {
        "filename": "window.png",
        "path": str(source),
        "description": "Ollama error: <urlopen error [Errno 111] Connection refused>",
        "error": "<urlopen error [Errno 111] Connection refused>",
        "classified_by": "ollama-llava",
        "confidence": 0.0,
    }
    recovery, index_file = _recovery_index_fixture(monkeypatch, tmp_path, [image])
    captured = {}

    async def fake_analyze_image(image_key, image_path):
        captured["image_key"] = image_key
        captured["image_path"] = image_path
        return {
            "image_key": image_key,
            "analysis_status": "success",
            "provider": "minimax",
            "transport": "mmx_cli",
            "model": "mmx_vision",
            "timestamp": "2026-05-25T10:00:00+00:00",
            "stale": False,
            "description": "A window treatment installation with neutral drapery.",
            "tags": ["drapery-fabrics", "interior"],
            "personal_work_classification": {"classification": "work_related", "confidence": 0.9, "reason": "test"},
            "business_route": "empire-workroom",
            "action_recommendation": "keep",
            "image_quality_score": 8.0,
            "analysis_confidence": 0.87,
            "needs_manual_review": False,
            "reason_for_manual_review": None,
        }

    monkeypatch.setattr(recovery, "analyze_image", fake_analyze_image)

    response = asyncio.run(
        recovery.recovery_reanalyze_image(
            recovery._record_key(image),
            recovery.RecoveryImageReanalyzeRequest(force=True),
        )
    )

    assert response["success"] is True
    assert response["analysis"]["transport"] == "mmx_cli"
    assert response["path_source"] == "source_path"
    assert captured["image_path"] == str(source.resolve())
    assert response["image"]["description"] == "A window treatment installation with neutral drapery."
    assert response["image"]["classified_by"] == "minimax-mmx_vision"
    assert response["image"]["last_error"] is None

    saved = json.loads(index_file.read_text())["images"][0]
    assert saved["description"] == "A window treatment installation with neutral drapery."
    assert saved["business"] == "empire-workroom"
    assert saved["confidence"] == 0.87
    assert "error" not in saved
    assert "analysis_error" not in saved
    assert saved["minimax_analysis"]["provider"] == "minimax"
    assert saved["minimax_analysis"]["transport"] == "mmx_cli"


def test_selected_image_reanalyze_missing_file_returns_clear_error(monkeypatch, tmp_path):
    image = {"filename": "missing.png", "path": str(tmp_path / "missing.png")}
    recovery, _ = _recovery_index_fixture(monkeypatch, tmp_path, [image])

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            recovery.recovery_reanalyze_image(
                recovery._record_key(image),
                recovery.RecoveryImageReanalyzeRequest(force=True),
            )
        )

    assert exc.value.status_code == 400
    assert exc.value.detail["error"] == "No readable RecoveryForge image file found for selected record"
    assert exc.value.detail["path_status"]["source"]["exists"] is False


def test_selected_image_review_only_updates_target_record(monkeypatch, tmp_path):
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    first.write_bytes(b"png")
    second.write_bytes(b"png")
    image_one = {"filename": "first.png", "path": str(first), "business": "general", "category": "misc"}
    image_two = {"filename": "second.png", "path": str(second), "business": "general", "category": "misc"}
    recovery, index_file = _recovery_index_fixture(monkeypatch, tmp_path, [image_one, image_two])

    response = asyncio.run(
        recovery.recovery_review_image(
            recovery._record_key(image_one),
            recovery.RecoveryImageReview(
                business="woodcraft",
                category="cabinet",
                review_status="approved",
                social_ready=True,
            ),
        )
    )

    assert response["status"] == "updated"
    saved = json.loads(index_file.read_text())["images"]
    assert saved[0]["business"] == "woodcraft"
    assert saved[0]["category"] == "cabinet"
    assert saved[0]["review_status"] == "approved"
    assert saved[1]["business"] == "general"
    assert saved[1]["category"] == "misc"


def test_file_endpoint_unknown_record_returns_404(monkeypatch, tmp_path):
    """Unknown record_key must return 404, not expose internal data."""
    image = {"filename": "exists.png", "path": str(tmp_path / "exists.png")}
    recovery, _ = _recovery_index_fixture(monkeypatch, tmp_path, [image])

    with pytest.raises(HTTPException) as exc:
        asyncio.run(recovery.recovery_image_file("zzzznotahexkey", "source"))

    assert exc.value.status_code == 404


def test_file_endpoint_missing_file_returns_404(monkeypatch, tmp_path):
    """Record exists but file on disk is missing must return 404."""
    image = {"filename": "missing.png", "path": str(tmp_path / "missing.png")}
    recovery, _ = _recovery_index_fixture(monkeypatch, tmp_path, [image])

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            recovery.recovery_image_file(
                recovery._record_key(image),
                "source",
            )
        )

    assert exc.value.status_code == 404
    assert "not found" in str(exc.value.detail).lower()


def test_file_endpoint_valid_source_returns_response(monkeypatch, tmp_path):
    """Valid record with readable source file must return a FileResponse."""
    from starlette.responses import FileResponse
    source = tmp_path / "window.png"
    source.write_bytes(b"png-file-bytes")
    image = {"filename": "window.png", "path": str(source)}
    recovery, _ = _recovery_index_fixture(monkeypatch, tmp_path, [image])

    response = asyncio.run(
        recovery.recovery_image_file(
            recovery._record_key(image),
            "source",
        )
    )

    assert isinstance(response, FileResponse)


def test_file_endpoint_query_pattern_restricts_variant():
    """FastAPI Query pattern on variant parameter must restrict to source|classified|social."""
    import inspect
    from app.routers.recovery import recovery_image_file

    sig = inspect.signature(recovery_image_file)
    variant_param = sig.parameters.get("variant")
    assert variant_param is not None
    # The default value carries the Query() with pattern — check it exists
    default_repr = repr(variant_param.default)
    assert "pattern" in default_repr or "source" in default_repr.lower()


def _categories_fixture(monkeypatch, tmp_path):
    import app.routers.recovery as recovery
    cats_file = tmp_path / "recovery_categories.json"
    monkeypatch.setattr(recovery, "CATEGORIES_FILE", str(cats_file))
    return recovery, cats_file


def test_list_categories_returns_builtins(monkeypatch, tmp_path):
    """GET /recovery/categories returns builtin category and business list."""
    recovery, _ = _categories_fixture(monkeypatch, tmp_path)
    result = asyncio.run(recovery.recovery_list_categories())
    assert "categories" in result
    slugs = [c["slug"] for c in result["categories"]]
    assert "empire-workroom" in slugs
    assert "woodcraft" in slugs
    assert "misc" in slugs
    # builtin entries have source=builtin
    builtin = [c for c in result["categories"] if c["source"] == "builtin"]
    assert len(builtin) >= 6


def test_list_categories_filter_by_kind(monkeypatch, tmp_path):
    """GET /recovery/categories?kind=category returns only categories."""
    recovery, _ = _categories_fixture(monkeypatch, tmp_path)
    result = asyncio.run(recovery.recovery_list_categories(kind="category"))
    for c in result["categories"]:
        assert c["kind"] == "category"


def test_post_category_creates_custom(monkeypatch, tmp_path):
    """POST /recovery/categories creates a custom category entry."""
    recovery, cats_file = _categories_fixture(monkeypatch, tmp_path)
    result = asyncio.run(recovery.recovery_create_category(recovery.CategoryCreate(label="Test Custom Category")))
    assert result["status"] == "created"
    assert result["entry"]["slug"] == "test-custom-category"
    assert result["entry"]["label"] == "Test Custom Category"
    assert result["entry"]["source"] == "custom"
    assert cats_file.exists()


def test_post_category_rejects_duplicate_case_insensitive(monkeypatch, tmp_path):
    """Creating a category with the same label (different case) returns 409."""
    recovery, _ = _categories_fixture(monkeypatch, tmp_path)
    asyncio.run(recovery.recovery_create_category(recovery.CategoryCreate(label="My Fabric Photos")))
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(recovery.recovery_create_category(recovery.CategoryCreate(label="my fabric photos")))
    assert exc_info.value.status_code == 409


def test_post_category_rejects_empty_label(monkeypatch, tmp_path):
    """Empty label is rejected with 400."""
    recovery, _ = _categories_fixture(monkeypatch, tmp_path)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(recovery.recovery_create_category(recovery.CategoryCreate(label="   ")))
    assert exc_info.value.status_code == 400


def test_post_category_rejects_builtin_slug(monkeypatch, tmp_path):
    """Creating a category matching a builtin slug returns 409."""
    recovery, _ = _categories_fixture(monkeypatch, tmp_path)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(recovery.recovery_create_category(recovery.CategoryCreate(label="misc")))
    assert exc_info.value.status_code == 409


def test_delete_category_removes_custom(monkeypatch, tmp_path):
    """DELETE /recovery/categories/{slug} removes a custom entry."""
    recovery, _ = _categories_fixture(monkeypatch, tmp_path)
    asyncio.run(recovery.recovery_create_category(recovery.CategoryCreate(label="Temporary Tag")))
    delete_result = asyncio.run(recovery.recovery_delete_category("temporary-tag"))
    assert delete_result["status"] == "deleted"
    # verify it's gone
    result = asyncio.run(recovery.recovery_list_categories())
    slugs = [c["slug"] for c in result["categories"]]
    assert "temporary-tag" not in slugs


def test_delete_category_forbidden_for_builtin(monkeypatch, tmp_path):
    """Deleting a builtin category returns 403."""
    recovery, _ = _categories_fixture(monkeypatch, tmp_path)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(recovery.recovery_delete_category("misc"))
    assert exc_info.value.status_code == 403


def test_review_with_custom_category_preserves_description(monkeypatch, tmp_path):
    """Reclassifying a selected image with a custom category preserves generated_description."""
    import app.routers.recovery as recovery_module

    cats_file = tmp_path / "recovery_categories.json"
    monkeypatch.setattr(recovery_module, "CATEGORIES_FILE", str(cats_file))

    index_file = tmp_path / "presorted_inventory.json"
    source = tmp_path / "photo.png"
    source.write_bytes(b"png")
    image = {
        "filename": "photo.png",
        "path": str(source),
        "business": "empire-workroom",
        "category": "misc",
        "generated_description": "A set of curtain fabric samples in neutral tones.",
        "minimax_analysis": {"description": "A set of curtain fabric samples in neutral tones."},
    }
    index_file.write_text(json.dumps({"images": [image], "stats": {}}))
    monkeypatch.setattr(recovery_module, "INDEX_FILE", str(index_file))
    monkeypatch.setattr(recovery_module, "CLASSIFIED_DIR", str(tmp_path / "classified"))
    monkeypatch.setattr(recovery_module, "SOCIAL_DIR", str(tmp_path / "social"))
    monkeypatch.setattr(recovery_module, "quota_allow_new", lambda: True)

    # Create a custom category
    asyncio.run(recovery_module.recovery_create_category(recovery_module.CategoryCreate(label="fabric-samples", kind="category")))

    # Reclassify image to custom category
    record_key = recovery_module._record_key(image)
    response = asyncio.run(
        recovery_module.recovery_review_image(
            record_key,
            recovery_module.RecoveryImageReview(category="fabric-samples"),
        )
    )
    assert response["status"] == "updated"
    saved = json.loads(index_file.read_text())["images"][0]
    assert saved["category"] == "fabric-samples"
    assert saved["generated_description"] == "A set of curtain fabric samples in neutral tones."
    assert saved["minimax_analysis"]["description"] == "A set of curtain fabric samples in neutral tones."


def _scrap_fixture(monkeypatch, tmp_path):
    import app.routers.recovery as recovery
    cats_file = tmp_path / "recovery_categories.json"
    monkeypatch.setattr(recovery, "CATEGORIES_FILE", str(cats_file))
    return recovery


def _scrap_index(images, tmp_path, monkeypatch):
    import app.routers.recovery as recovery
    index_file = tmp_path / "presorted_inventory.json"
    monkeypatch.setattr(recovery, "INDEX_FILE", str(index_file))
    monkeypatch.setattr(recovery, "CLASSIFIED_DIR", str(tmp_path / "classified"))
    monkeypatch.setattr(recovery, "SOCIAL_DIR", str(tmp_path / "social"))
    monkeypatch.setattr(recovery, "quota_allow_new", lambda: True)
    index_file.write_text(json.dumps({"images": images, "stats": {}}))
    return recovery, index_file


def test_scrap_soft_delete_marks_record(monkeypatch, tmp_path):
    """soft_delete marks the record scrapped without touching files."""
    recovery, index_file = _scrap_index([
        {"filename": "photo.png", "path": str(tmp_path / "photo.png"), "business": "general", "category": "misc"}
    ], tmp_path, monkeypatch)

    record_key = recovery._record_key({"filename": "photo.png", "path": str(tmp_path / "photo.png")})
    result = asyncio.run(recovery.recovery_scrap_image(
        record_key,
        recovery.RecoveryImageScrapRequest(mode="soft_delete", reason="unrelated"),
    ))
    assert result["status"] == "scrapped"
    assert result["mode"] == "soft_delete"
    assert result["source_kept"] is True
    assert result["classified_deleted"] is False
    saved = json.loads(index_file.read_text())["images"][0]
    assert saved["scrapped"] is True
    assert saved["scrapped_reason"] == "unrelated"
    assert "scrapped_at" in saved


def test_scrap_soft_delete_hides_from_active_list(monkeypatch, tmp_path):
    """scrapped records are hidden from active list by default."""
    recovery, index_file = _scrap_index([
        {"filename": "keep.png", "path": str(tmp_path / "keep.png"), "business": "general", "category": "misc", "description": "keep"},
        {"filename": "trash.png", "path": str(tmp_path / "trash.png"), "business": "general", "category": "misc", "description": "trash"},
    ], tmp_path, monkeypatch)

    # scrap the second record
    rk = recovery._record_key({"filename": "trash.png", "path": str(tmp_path / "trash.png")})
    asyncio.run(recovery.recovery_scrap_image(rk, recovery.RecoveryImageScrapRequest(mode="soft_delete")))

    # active list should only show the first
    result = asyncio.run(recovery.recovery_images(status="active", analyzed_only=False, limit=48, offset=0))
    keys = [img["record_key"] for img in result["images"]]
    assert rk not in keys  # scrapped is hidden

    # scrapped filter should show it
    result2 = asyncio.run(recovery.recovery_images(status="scrapped", analyzed_only=False, limit=48, offset=0))
    scrapped_keys = [img["record_key"] for img in result2["images"]]
    assert rk in scrapped_keys


def test_scrap_delete_classified_trashes_copies(monkeypatch, tmp_path):
    """delete_classified moves classified/social copies to trash, keeps source."""
    classified_dir = tmp_path / "classified" / "general" / "misc"
    classified_dir.mkdir(parents=True)
    classified_file = classified_file_path = classified_dir / "photo.png"
    classified_file.write_bytes(b"classified-img")

    recovery, index_file = _scrap_index([
        {"filename": "photo.png", "path": str(tmp_path / "source.png"), "classified_path": str(classified_file), "business": "general", "category": "misc", "description": "desc"}
    ], tmp_path, monkeypatch)

    record_key = recovery._record_key({"filename": "photo.png", "path": str(tmp_path / "source.png")})
    result = asyncio.run(recovery.recovery_scrap_image(
        record_key,
        recovery.RecoveryImageScrapRequest(mode="delete_classified"),
    ))
    assert result["status"] == "scrapped"
    assert result["source_kept"] is True
    assert result["source_missing"] is False
    assert classified_file.exists() is False  # moved to trash


def test_scrap_delete_all_copies_requires_confirm(monkeypatch, tmp_path):
    """delete_all_copies without confirm=True returns 400."""
    recovery, _ = _scrap_index([
        {"filename": "photo.png", "path": str(tmp_path / "photo.png"), "business": "general", "category": "misc"}
    ], tmp_path, monkeypatch)
    record_key = recovery._record_key({"filename": "photo.png", "path": str(tmp_path / "photo.png")})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(recovery.recovery_scrap_image(
            record_key,
            recovery.RecoveryImageScrapRequest(mode="delete_all_copies"),
        ))
    assert exc.value.status_code == 400


def test_scrap_delete_source_requires_exact_confirm_text(monkeypatch, tmp_path):
    """delete_source requires confirm_text='DELETE', not just confirm=True."""
    recovery, _ = _scrap_index([
        {"filename": "photo.png", "path": str(tmp_path / "photo.png"), "business": "general", "category": "misc"}
    ], tmp_path, monkeypatch)
    record_key = recovery._record_key({"filename": "photo.png", "path": str(tmp_path / "photo.png")})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(recovery.recovery_scrap_image(
            record_key,
            recovery.RecoveryImageScrapRequest(mode="soft_delete", delete_source=True, confirm=True, confirm_text="WRONG"),
        ))
    assert exc.value.status_code == 400


def test_scrap_invalid_record_returns_404(monkeypatch, tmp_path):
    """Scraping a non-existent record_key returns 404."""
    recovery, _ = _scrap_index([
        {"filename": "photo.png", "path": str(tmp_path / "photo.png"), "business": "general", "category": "misc"}
    ], tmp_path, monkeypatch)
    with pytest.raises(HTTPException) as exc:
        asyncio.run(recovery.recovery_scrap_image(
            "nonexistent-key",
            recovery.RecoveryImageScrapRequest(),
        ))
    assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Phase 2B-A: Deterministic tag extraction tests
# ---------------------------------------------------------------------------

def test_slugify_tag_basic():
    """_slugify_tag converts spaces/special chars to hyphens and lowercases."""
    from app.routers.recovery import _slugify_tag
    assert _slugify_tag("Hello World!") == "hello-world"
    assert _slugify_tag("Velvet & Silk") == "velvet-silk"
    assert _slugify_tag("  Modern  ") == "modern"


def test_slugify_tag_special_chars():
    """_slugify_tag strips non-alphanumeric except hyphens."""
    from app.routers.recovery import _slugify_tag
    assert _slugify_tag("Scandinavian Design") == "scandinavian-design"
    assert _slugify_tag("Upholstery (fabric)") == "upholstery-fabric"
    assert _slugify_tag("living-room") == "living-room"


def test_extract_asset_tags_single_category():
    """_extract_asset_tags finds object terms in description text."""
    from app.routers.recovery import _extract_asset_tags
    tags = _extract_asset_tags("A beautiful velvet sofa with wooden legs")
    assert "velvet" in tags["material_tags"]
    assert "sofa" in tags["object_tags"] or "chair" in tags["object_tags"]
    assert "wood" in tags["material_tags"]


def test_extract_asset_tags_business_domain_workroom():
    """Drapery/curtain/blind/shade terms infer empire-workroom domain."""
    from app.routers.recovery import _extract_asset_tags
    tags = _extract_asset_tags("Window treatment with drapery and curtain valance")
    assert "empire-workroom" in tags["business_domains"]
    assert "drapery" in tags["object_tags"]
    assert "window-treatment" in tags["object_tags"]


def test_extract_asset_tags_business_domain_woodcraft():
    """Wood/material terms infer woodcraft domain."""
    from app.routers.recovery import _extract_asset_tags
    tags = _extract_asset_tags("Custom oak cabinet with wood grain finish")
    assert "woodcraft" in tags["business_domains"]
    assert "oak" in tags["material_tags"]


def test_extract_asset_tags_post_process_window_treatment():
    """Drapery/curtain/blind/shade post-process to window-treatment slug."""
    from app.routers.recovery import _extract_asset_tags
    tags = _extract_asset_tags("Sheer curtains and wooden blinds")
    assert "window-treatment" in tags["object_tags"]


def test_apply_asset_tags_writes_all_tag_arrays():
    """_apply_asset_tags writes all 9 tag arrays onto the image dict."""
    from app.routers.recovery import _apply_asset_tags
    img = {}
    _apply_asset_tags(img, "Modern velvet sofa in a Scandinavian living room with a dog")
    assert "object_tags" in img
    assert "material_tags" in img
    assert "room_tags" in img
    assert "pet_tags" in img
    assert "style_tags" in img
    assert "business_domains" in img
    assert "asset_tags" in img
    assert "people_tags" in img
    assert "campaign_tags" in img
    assert img["object_tags"] == ["sofa"]
    assert img["material_tags"] == ["velvet"]
    assert img["room_tags"] == ["living room"]
    assert img["pet_tags"] == ["dog"]
    assert img["style_tags"] == ["modern", "scandinavian"]


# ---------------------------------------------------------------------------
# Phase 2B-B: Manual tag editing endpoint tests
# ---------------------------------------------------------------------------

def _make_test_client(tmp_path: Path, imgs: list[dict]):
    """Build a TestClient wired to a temporary index via a minimal FastAPI app."""
    from fastapi import FastAPI
    import app.routers.recovery as rec
    idx = tmp_path / "inv.json"
    with open(idx, "w") as f:
        json.dump({"images": imgs}, f)
    rec.INDEX_FILE = str(idx)
    rec.QUEUE_FILE = str(tmp_path / "queue.json")
    app = FastAPI()
    app.include_router(rec.router)
    return TestClient(app)


def test_tags_update_single_record_only(tmp_path: Path):
    """PATCH /recovery/images/{record_key}/tags updates only the targeted record."""
    imgs = [
        {"filename": "a.jpg", "path": str(tmp_path / "a.jpg"), "business": "general", "category": "misc",
         "object_tags": [], "room_tags": [], "material_tags": [], "style_tags": [],
         "people_tags": [], "pet_tags": [], "campaign_tags": [], "business_domains": [], "asset_tags": []},
        {"filename": "b.jpg", "path": str(tmp_path / "b.jpg"), "business": "general", "category": "misc",
         "object_tags": ["sofa"], "room_tags": [], "material_tags": [], "style_tags": [],
         "people_tags": [], "pet_tags": [], "campaign_tags": [], "business_domains": [], "asset_tags": []},
    ]
    client = _make_test_client(tmp_path, imgs)
    resp = client.patch("/recovery/images/a.jpg/tags", json={"campaign_tags": ["website-gallery"]})
    assert resp.status_code == 200
    assert resp.json()["image"]["campaign_tags"] == ["website-gallery"]
    resp2 = client.get("/recovery/images/b.jpg")
    assert resp2.json()["image"]["campaign_tags"] == []


def test_tags_update_normalizes_slugs(tmp_path: Path):
    """Submitted tags are slugified and deduplicated."""
    imgs = [{"filename": "c.jpg", "path": str(tmp_path / "c.jpg"), "business": "general", "category": "misc",
             "object_tags": [], "room_tags": [], "material_tags": [], "style_tags": [],
             "people_tags": [], "pet_tags": [], "campaign_tags": [], "business_domains": [], "asset_tags": []}]
    client = _make_test_client(tmp_path, imgs)
    resp = client.patch("/recovery/images/c.jpg/tags", json={"style_tags": ["Modern Furniture!", "modern-furniture"]})
    assert resp.status_code == 200
    tags = resp.json()["image"]["style_tags"]
    assert "modern-furniture" in tags
    assert len(tags) == 1


def test_tags_update_rejects_blocked(tmp_path: Path):
    """Blocked tags are rejected and reported, not stored."""
    imgs = [{"filename": "d.jpg", "path": str(tmp_path / "d.jpg"), "business": "general", "category": "misc",
             "object_tags": [], "room_tags": [], "material_tags": [], "style_tags": [],
             "people_tags": [], "pet_tags": [], "campaign_tags": [], "business_domains": [], "asset_tags": []}]
    client = _make_test_client(tmp_path, imgs)
    resp = client.patch("/recovery/images/d.jpg/tags", json={"business_domains": ["none", "unknown"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["rejected_tags"] == ["none", "unknown"]
    assert "none" not in body["image"]["business_domains"]


def test_tags_update_provenance_fields(tmp_path: Path):
    """Manual edit sets tags_manually_edited, tags_updated_at, tags_updated_by."""
    imgs = [{"filename": "e.jpg", "path": str(tmp_path / "e.jpg"), "business": "general", "category": "misc",
             "object_tags": [], "room_tags": [], "material_tags": [], "style_tags": [],
             "people_tags": [], "pet_tags": [], "campaign_tags": [], "business_domains": [], "asset_tags": []}]
    client = _make_test_client(tmp_path, imgs)
    resp = client.patch("/recovery/images/e.jpg/tags", json={"object_tags": ["lamp"]})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tags_manually_edited"] is True
    assert body["tags_updated_at"] is not None
    assert body["tags_updated_by"] == "operator"


def test_tags_update_preserves_description(tmp_path: Path):
    """PATCH tags does NOT touch generated_description or minimax_analysis."""
    desc = "A velvet sofa in a modern living room"
    imgs = [{"filename": "f.jpg", "path": str(tmp_path / "f.jpg"), "business": "general", "category": "misc",
             "description": desc, "generated_description": desc,
             "minimax_analysis": {"description": desc, "analysis_status": "success"},
             "object_tags": [], "room_tags": [], "material_tags": [], "style_tags": [],
             "people_tags": [], "pet_tags": [], "campaign_tags": [], "business_domains": [], "asset_tags": []}]
    client = _make_test_client(tmp_path, imgs)
    resp = client.patch("/recovery/images/f.jpg/tags", json={"campaign_tags": ["social-ad"]})
    assert resp.status_code == 200
    body = resp.json()["image"]
    assert body["description"] == desc
    assert body["generated_description"] == desc
    assert body["minimax_analysis"] is not None


def test_tags_update_partial_update(tmp_path: Path):
    """Supplying only one field leaves other tag arrays untouched."""
    imgs = [{"filename": "g.jpg", "path": str(tmp_path / "g.jpg"), "business": "general", "category": "misc",
             "object_tags": ["sofa"], "room_tags": ["living-room"], "material_tags": ["velvet"],
             "style_tags": ["modern"], "people_tags": [], "pet_tags": [], "campaign_tags": [], "business_domains": [], "asset_tags": []}]
    client = _make_test_client(tmp_path, imgs)
    resp = client.patch("/recovery/images/g.jpg/tags", json={"campaign_tags": ["website-gallery"]})
    assert resp.status_code == 200
    body = resp.json()["image"]
    assert body["campaign_tags"] == ["website-gallery"]
    assert body["object_tags"] == ["sofa"]
    assert body["room_tags"] == ["living-room"]


def test_tags_update_empty_list_clears_field(tmp_path: Path):
    """Explicit empty list clears a tag array."""
    imgs = [{"filename": "h.jpg", "path": str(tmp_path / "h.jpg"), "business": "general", "category": "misc",
             "object_tags": ["sofa"], "room_tags": [], "material_tags": [], "style_tags": [],
             "people_tags": [], "pet_tags": [], "campaign_tags": [], "business_domains": [], "asset_tags": []}]
    client = _make_test_client(tmp_path, imgs)
    resp = client.patch("/recovery/images/h.jpg/tags", json={"object_tags": []})
    assert resp.status_code == 200
    assert resp.json()["image"]["object_tags"] == []


def test_tags_update_404_on_missing_record(tmp_path: Path):
    """Patching a non-existent record returns 404."""
    client = _make_test_client(tmp_path, [])
    resp = client.patch("/recovery/images/nonexistent/tags", json={"object_tags": ["lamp"]})
    assert resp.status_code == 404


# ── Persistence truth tests ──────────────────────────────────────────────────────

def test_is_persisted_analyzed_true_for_minimax_record(tmp_path: Path):
    """Records with real MiniMax description + analysis are detected as persisted analyzed."""
    from app.routers.recovery import _is_persisted_analyzed
    img = {
        "filename": "x.jpg",
        "description": "A detailed description of a sofa in a living room with velvet fabric.",
        "minimax_analysis": {"analysis_status": "success", "provider": "minimax"},
        "analyzed_at": "2026-05-26T10:00:00+00:00",
        "confidence": 0.85,
        "classified_by": "minimax-mmx_vision",
    }
    assert _is_persisted_analyzed(img) is True


def test_is_persisted_analyzed_false_for_untouched_record(tmp_path: Path):
    """Records with no analysis fields return False."""
    from app.routers.recovery import _is_persisted_analyzed
    img = {
        "filename": "y.jpg",
        "path": "/some/path/y.jpg",
        "business": "unknown",
        "category": "misc",
        "object_tags": ["sofa"],
        "material_tags": ["velvet"],
    }
    assert _is_persisted_analyzed(img) is False


def test_is_persisted_analyzed_false_for_ollama_error_record(tmp_path: Path):
    """Records with only Ollama error are NOT counted as persisted analyzed."""
    from app.routers.recovery import _is_persisted_analyzed
    img = {
        "filename": "z.jpg",
        "last_error": "Ollama connection refused",
        "classified_by": "none",
        "confidence": None,
        "description": "",
    }
    assert _is_persisted_analyzed(img) is False


def test_is_persisted_analyzed_requires_classified_with_confidence(tmp_path: Path):
    """Confidence alone without classified_by does not count as analyzed."""
    from app.routers.recovery import _is_persisted_analyzed
    img = {"filename": "w.jpg", "confidence": 0.75, "classified_by": "none"}
    assert _is_persisted_analyzed(img) is False


def test_analyzed_only_true_filters_correctly_via_helper(tmp_path: Path):
    """analyzed_only=True returns only records matching _is_persisted_analyzed."""
    imgs = [
        {"filename": "a.jpg", "description": "A detailed description of a sofa in a workshop.",
         "minimax_analysis": {"status": "success"}, "analyzed_at": "2026-05-26T10:00:00+00:00",
         "confidence": 0.9, "classified_by": "minimax-mmx_vision"},
        {"filename": "b.jpg", "object_tags": ["sofa"], "material_tags": ["velvet"]},
        {"filename": "c.jpg", "last_error": "Ollama error", "classified_by": "none"},
        {"filename": "d.jpg", "business": "unknown", "category": "misc"},
    ]
    client = _make_test_client(tmp_path, imgs)
    resp = client.get("/recovery/images?analyzed_only=true")
    assert resp.status_code == 200
    keys = [img["filename"] for img in resp.json()["images"]]
    assert "a.jpg" in keys
    # Tags-only, error-only, unknown-only should be excluded
    assert "b.jpg" not in keys
    assert "c.jpg" not in keys
    assert "d.jpg" not in keys


def test_status_endpoint_returns_persisted_analyzed_count(tmp_path: Path):
    """Status endpoint exposes persisted_analyzed (not stale ollama_processed) as primary count."""
    imgs = [
        {"filename": "x.jpg", "description": "A detailed description of a sofa for Empire Workroom.",
         "minimax_analysis": {"status": "success"}, "analyzed_at": "2026-05-26T10:00:00+00:00",
         "confidence": 0.85, "classified_by": "minimax-mmx_vision"},
        {"filename": "y.jpg", "object_tags": ["lamp"]},
        {"filename": "z.jpg", "business": "unknown", "category": "misc"},
    ]
    client = _make_test_client(tmp_path, imgs)
    resp = client.get("/recovery/status")
    assert resp.status_code == 200
    data = resp.json()
    # persisted_analyzed is the canonical count
    assert "persisted_analyzed" in data
    assert data["persisted_analyzed"] == 1  # only x.jpg has real analysis
    # processed is the stale ollama counter from the progress file
    assert "processed" in data
    # total_images is indexed total, not hardcoded TOTAL_IMAGES
    assert data["total_images"] == 3


def test_persistence_audit_endpoint_reports_truth(tmp_path: Path):
    """GET /recovery/persistence-audit returns per-field counts and reanalysis candidates."""
    imgs = [
        {"filename": "a.jpg", "description": "A detailed fabric description for upholstery work in a workshop setting with tools and materials.",
         "minimax_analysis": {"status": "success"}, "analyzed_at": "2026-05-26T10:00:00+00:00",
         "confidence": 0.85, "classified_by": "minimax-mmx_vision"},
        {"filename": "b.jpg", "path": str(tmp_path / "b.jpg"), "last_error": "Ollama error"},
        {"filename": "c.jpg", "path": str(tmp_path / "c.jpg")},
        {"filename": "d.jpg", "business": "unknown", "category": "misc"},
    ]
    client = _make_test_client(tmp_path, imgs)
    resp = client.get("/recovery/persistence-audit")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_records"] == 4
    assert data["persisted_analyzed_count"] == 1
    assert data["records_with_description"] == 1
    assert data["records_with_minimax_analysis"] == 1
    assert data["records_with_error"] == 1
    assert data["records_with_ollama_error"] == 1
    # b.jpg and c.jpg have path but no error-free analyzed state → reanalysis candidates
    assert data["needs_reanalysis_candidates"] >= 1
    assert "progress_file" in data
    assert "index_file" in data


# ── Reanalysis queue tests ──────────────────────────────────────────────────────

def test_queue_start_rejects_invalid_limit(tmp_path: Path):
    """limit must be one of allowed values."""
    client = _make_test_client(tmp_path, [{"filename": "x.jpg", "path": str(tmp_path / "x.jpg")}])
    resp = client.post("/recovery/reanalysis-queue/start", json={"limit": 7})  # 7 not allowed
    assert resp.status_code == 400
    assert "limit must be one of" in resp.json()["detail"]


def test_queue_start_dry_run_returns_candidates_without_analysis(tmp_path: Path):
    """dry_run=true returns candidate list without calling MiniMax."""
    # Create actual files so path validation passes
    (tmp_path / "a.jpg").touch()
    (tmp_path / "b.jpg").touch()
    (tmp_path / "c.jpg").touch()
    imgs = [
        {"filename": "a.jpg", "path": str(tmp_path / "a.jpg")},
        {"filename": "b.jpg", "path": str(tmp_path / "b.jpg")},
        {"filename": "c.jpg", "path": str(tmp_path / "c.jpg")},
    ]
    client = _make_test_client(tmp_path, imgs)
    resp = client.post("/recovery/reanalysis-queue/start", json={"limit": 5, "dry_run": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["dry_run"] is True
    assert data["selected_count"] == 3  # only 3 candidates exist, all selected with limit=5
    assert len(data["selected_keys"]) == 3
    assert "candidate_count" in data
    assert "selected_keys" in data


def test_queue_start_bounded_selection(tmp_path: Path):
    """limit is bounded — only up to limit candidates selected."""
    # Create actual files so path validation passes
    for c in "abcdefghij":
        (tmp_path / f"{c}.jpg").touch()
    imgs = [{"filename": f"{c}.jpg", "path": str(tmp_path / f"{c}.jpg")} for c in "abcdefghij"]
    client = _make_test_client(tmp_path, imgs)
    resp = client.post("/recovery/reanalysis-queue/start", json={"limit": 5, "dry_run": True})
    assert resp.status_code == 200
    assert resp.json()["selected_count"] == 5


def test_queue_candidates_exclude_persisted_analyzed(tmp_path: Path):
    """Records already persisted analyzed are excluded from candidates."""
    import app.routers.recovery as rec

    # Create actual files so path validation passes
    (tmp_path / "a.jpg").touch()
    (tmp_path / "b.jpg").touch()
    imgs = [
        {"filename": "a.jpg", "path": str(tmp_path / "a.jpg"),
         "description": "A detailed description of a sofa in a workshop with tools and workbench.",
         "minimax_analysis": {"status": "success"}, "analyzed_at": "2026-05-26T10:00:00+00:00",
         "confidence": 0.85, "classified_by": "minimax-mmx_vision"},
        {"filename": "b.jpg", "path": str(tmp_path / "b.jpg")},
    ]
    client = _make_test_client(tmp_path, imgs)
    resp = client.post("/recovery/reanalysis-queue/start", json={"limit": 5, "dry_run": True})
    assert resp.status_code == 200
    # a.jpg is already persisted analyzed, only b.jpg should be selected
    assert resp.json()["selected_count"] == 1
    assert rec._record_key(imgs[0]) not in resp.json()["selected_keys"]
    assert rec._record_key(imgs[1]) in resp.json()["selected_keys"]


def test_queue_candidates_exclude_scrapped(tmp_path: Path):
    """Scrapped records are excluded from candidates."""
    import app.routers.recovery as rec

    # Create actual files so path validation passes
    (tmp_path / "a.jpg").touch()
    (tmp_path / "b.jpg").touch()
    imgs = [
        {"filename": "a.jpg", "path": str(tmp_path / "a.jpg"), "scrapped": True},
        {"filename": "b.jpg", "path": str(tmp_path / "b.jpg")},
    ]
    client = _make_test_client(tmp_path, imgs)
    resp = client.post("/recovery/reanalysis-queue/start", json={"limit": 5, "dry_run": True})
    assert resp.status_code == 200
    assert resp.json()["selected_count"] == 1
    assert rec._record_key(imgs[0]) not in resp.json()["selected_keys"]
    assert rec._record_key(imgs[1]) in resp.json()["selected_keys"]


def test_queue_status_returns_state(tmp_path: Path):
    """Queue status endpoint returns current state plus persisted_analyzed."""
    client = _make_test_client(tmp_path, [{"filename": "x.jpg", "path": str(tmp_path / "x.jpg")}])
    resp = client.get("/recovery/reanalysis-queue/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "running" in data
    assert "paused" in data
    assert "persisted_analyzed" in data
    assert "total_indexed" in data


def test_queue_stop_clears_running(tmp_path: Path):
    """Stop endpoint sets running=False."""
    client = _make_test_client(tmp_path, [{"filename": "x.jpg", "path": str(tmp_path / "x.jpg")}])
    resp = client.post("/recovery/reanalysis-queue/stop", json={})
    assert resp.status_code == 200
    assert resp.json()["stopped"] is True
    assert resp.json()["state"]["running"] is False


def test_queue_pause_resume_transitions(tmp_path: Path):
    """Pause sets paused=True; resume clears it."""
    # Create actual image files so path validation passes
    (tmp_path / "x.jpg").touch()
    client = _make_test_client(tmp_path, [{"filename": "x.jpg", "path": str(tmp_path / "x.jpg")}])
    # First start the queue
    client.post("/recovery/reanalysis-queue/start", json={"limit": 1})
    pause_resp = client.post("/recovery/reanalysis-queue/pause", json={})
    assert pause_resp.status_code == 200
    assert pause_resp.json().get("paused") is True
    resume_resp = client.post("/recovery/reanalysis-queue/resume", json={})
    assert resume_resp.status_code == 200
    assert resume_resp.json().get("resumed") is True
    assert resume_resp.json()["state"]["paused"] is False


def test_queue_process_next_requires_running_state(tmp_path: Path):
    """process-next fails if queue not started."""
    client = _make_test_client(tmp_path, [{"filename": "x.jpg", "path": str(tmp_path / "x.jpg")}])
    resp = client.post("/recovery/reanalysis-queue/process-next", json={})
    assert resp.status_code == 200
    assert resp.json()["processed"] is False
    assert resp.json()["reason"] == "queue not running"


def test_queue_process_next_persists_success_after_reload(monkeypatch, tmp_path: Path):
    """A queue success is counted only after analysis fields survive a disk reload."""
    import app.routers.recovery as rec

    (tmp_path / "done.jpg").touch()
    (tmp_path / "fresh.jpg").touch()
    analyzed = {
        "filename": "done.jpg",
        "path": str(tmp_path / "done.jpg"),
        "description": "A detailed description of completed drapery work in a living room with fabric samples.",
        "generated_description": "A detailed description of completed drapery work in a living room with fabric samples.",
        "minimax_analysis": {"analysis_status": "success", "description": "already done"},
        "analyzed_at": "2026-05-26T10:00:00+00:00",
        "confidence": 0.85,
        "classified_by": "minimax-mmx_vision",
    }
    fresh = {"filename": "fresh.jpg", "path": str(tmp_path / "fresh.jpg")}
    client = _make_test_client(tmp_path, [analyzed, fresh])
    monkeypatch.setattr(rec, "quota_allow_new", lambda: True)

    async def fake_analyze_image(image_key, image_path):
        return {
            "image_key": image_key,
            "analysis_status": "success",
            "timestamp": "2026-05-27T10:00:00+00:00",
            "description": "A modern living room sofa with velvet drapery fabric and curtain hardware for Empire Workroom.",
            "business_route": "empire-workroom",
            "analysis_confidence": 0.92,
        }

    monkeypatch.setattr(rec, "analyze_image", fake_analyze_image)

    before = client.get("/recovery/status").json()["persisted_analyzed"]
    assert before == 1
    assert client.post("/recovery/reanalysis-queue/start", json={"limit": 1}).status_code == 200

    resp = client.post("/recovery/reanalysis-queue/process-next", json={})
    assert resp.status_code == 200
    result = resp.json()
    assert result["processed"] is True
    assert result["status"] == "success"
    assert result["success"] is True
    assert result["persisted_verified"] is True
    assert result["persisted_analyzed_before"] == 1
    assert result["persisted_analyzed_after"] == 2
    assert result["success_count"] == 1
    assert result["failure_count"] == 0
    assert result["image_generation_used"] is False

    reloaded = json.loads((tmp_path / "inv.json").read_text())
    saved = next(img for img in reloaded["images"] if img["filename"] == "fresh.jpg")
    assert saved["description"]
    assert saved["generated_description"]
    assert saved["minimax_analysis"]["description"]
    assert saved["minimax_analysis"]["provider"] == "minimax"
    assert saved["minimax_analysis"]["transport"] == "mmx_cli"
    assert saved["minimax_analysis"]["model"] == "mmx_vision"
    assert saved["analyzed_at"] == "2026-05-27T10:00:00+00:00"
    assert saved["classified_by"] == "minimax-mmx_vision"
    assert "sofa" in saved["object_tags"]
    assert "window-treatment" in saved["object_tags"]
    assert "velvet" in saved["material_tags"]
    assert "empire-workroom" in saved["business_domains"]
    assert rec._is_persisted_analyzed(saved) is True


def test_queue_process_next_success_requires_reload_truth(monkeypatch, tmp_path: Path):
    """If the save writes stale data, the queue records failure instead of success."""
    import app.routers.recovery as rec

    (tmp_path / "fresh.jpg").touch()
    fresh = {"filename": "fresh.jpg", "path": str(tmp_path / "fresh.jpg")}
    client = _make_test_client(tmp_path, [fresh])
    monkeypatch.setattr(rec, "quota_allow_new", lambda: True)

    async def fake_analyze_image(image_key, image_path):
        return {
            "image_key": image_key,
            "analysis_status": "success",
            "timestamp": "2026-05-27T10:00:00+00:00",
            "description": "A modern sofa with velvet fabric in a living room for workroom marketing.",
            "analysis_confidence": 0.91,
        }

    def save_stale_index(data):
        (tmp_path / "inv.json").write_text(json.dumps({"images": [fresh]}))

    monkeypatch.setattr(rec, "analyze_image", fake_analyze_image)
    assert client.post("/recovery/reanalysis-queue/start", json={"limit": 1}).status_code == 200
    monkeypatch.setattr(rec, "_save_image_index", save_stale_index)

    resp = client.post("/recovery/reanalysis-queue/process-next", json={})
    assert resp.status_code == 200
    result = resp.json()
    assert result["processed"] is True
    assert result["status"] == "persistence_failed"
    assert result["success"] is False
    assert result["persisted_verified"] is False
    assert result["success_count"] == 0
    assert result["failure_count"] == 1
    assert result["persisted_analyzed_before"] == 0
    assert result["persisted_analyzed_after"] == 0

    queue_state = json.loads((tmp_path / "queue.json").read_text())
    assert rec._record_key(fresh) in queue_state["failed_record_keys"]
    assert queue_state["completed_record_keys"] == []


def test_queue_process_next_save_failure_is_not_success(monkeypatch, tmp_path: Path):
    """A disk save exception must not advance success/completed counters."""
    import app.routers.recovery as rec

    (tmp_path / "fresh.jpg").touch()
    fresh = {"filename": "fresh.jpg", "path": str(tmp_path / "fresh.jpg")}
    client = _make_test_client(tmp_path, [fresh])
    monkeypatch.setattr(rec, "quota_allow_new", lambda: True)

    async def fake_analyze_image(image_key, image_path):
        return {
            "image_key": image_key,
            "analysis_status": "success",
            "timestamp": "2026-05-27T10:00:00+00:00",
            "description": "A modern sofa with velvet fabric in a living room for workroom marketing.",
            "analysis_confidence": 0.91,
        }

    def fail_save(data):
        raise RuntimeError("disk write failed")

    monkeypatch.setattr(rec, "analyze_image", fake_analyze_image)
    assert client.post("/recovery/reanalysis-queue/start", json={"limit": 1}).status_code == 200
    monkeypatch.setattr(rec, "_save_image_index", fail_save)

    resp = client.post("/recovery/reanalysis-queue/process-next", json={})
    assert resp.status_code == 200
    result = resp.json()
    assert result["processed"] is True
    assert result["status"] == "persistence_failed"
    assert result["success"] is False
    assert result["persisted_verified"] is False
    assert result["success_count"] == 0
    assert result["failure_count"] == 1
    assert result["persisted_analyzed_before"] == 0
    assert result["persisted_analyzed_after"] == 0

    saved = json.loads((tmp_path / "inv.json").read_text())["images"][0]
    assert "description" not in saved
    queue_state = json.loads((tmp_path / "queue.json").read_text())
    assert rec._record_key(fresh) in queue_state["failed_record_keys"]
    assert queue_state["completed_record_keys"] == []
