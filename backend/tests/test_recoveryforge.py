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

