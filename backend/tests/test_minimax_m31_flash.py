"""MiniMax-M3.1-Flash-Preview: founder registry, family gate, probe, meter."""
from __future__ import annotations

import pytest


MODEL = "MiniMax-M3.1-Flash-Preview"


def test_registry_keeps_m3_default_and_excludes_h3():
    from app.services.max.routing_state import (
        KNOWN_MODELS,
        PROVIDER_DEFAULT_MODELS,
        is_minimax_video_model,
        provider_default_model,
        provider_model_choices,
    )

    assert PROVIDER_DEFAULT_MODELS["minimax"] == "MiniMax-M3"
    assert provider_default_model("minimax") == "MiniMax-M3"
    assert MODEL in KNOWN_MODELS["minimax"]
    assert "MiniMax-H3" not in KNOWN_MODELS["minimax"]
    assert is_minimax_video_model("MiniMax-H3") is True
    assert is_minimax_video_model(MODEL) is False


def test_founder_unset_and_studio_see_flash(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "empire-data"))
    (tmp_path / "empire-data").mkdir()
    monkeypatch.delenv("MINIMAX_MODEL", raising=False)
    monkeypatch.delenv("MAX_MODELS_MINIMAX", raising=False)
    from app.services.max.routing_state import provider_model_choices

    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.delenv("MINIMAX_M31_FLASH_FAMILY", raising=False)
    choices = provider_model_choices("minimax")
    assert MODEL in choices
    assert "MiniMax-M3" in choices
    assert choices.index("MiniMax-M3") < choices.index(MODEL)

    monkeypatch.setenv("EMPIRE_EDITION", "studio")
    assert MODEL in provider_model_choices("minimax")


def test_family_editions_hide_flash_unless_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "amp"))
    (tmp_path / "amp").mkdir()
    monkeypatch.delenv("MINIMAX_M31_FLASH_FAMILY", raising=False)
    from app.services.max.routing_state import provider_model_choices

    assert MODEL not in provider_model_choices("minimax")
    assert "MiniMax-M3" in provider_model_choices("minimax")

    monkeypatch.setenv("MINIMAX_M31_FLASH_FAMILY", "1")
    assert MODEL in provider_model_choices("minimax")


def test_selector_rejects_flash_on_family_without_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "maxine"))
    (tmp_path / "maxine").mkdir()
    monkeypatch.delenv("MINIMAX_M31_FLASH_FAMILY", raising=False)
    monkeypatch.setenv("MINIMAX_API_KEY", "test-mm-key")
    from app.services.max.routing_state import provider_model_choices

    assert MODEL not in provider_model_choices("minimax")


def test_fallback_flag_still_defaults_false(monkeypatch):
    monkeypatch.delenv("MAX_ALLOW_FALLBACK", raising=False)
    from app.services.max.routing_state import env_flag

    assert env_flag("MAX_ALLOW_FALLBACK", False) is False


def test_plan_unsupported_error_is_clear():
    from app.services.minimax_m31_flash import (
        is_plan_unsupported_payload,
        plan_unsupported_message,
    )

    msg = plan_unsupported_message(MODEL, "model_not_found")
    assert "M Plan" in msg
    assert "MiniMax Code" in msg
    assert "MiniMax-M3" in msg
    assert is_plan_unsupported_payload(MODEL, body="unknown model", status_code=404) is True
    assert is_plan_unsupported_payload("MiniMax-M3", body="unknown model", status_code=404) is False


def test_probe_dry_run_does_not_http(monkeypatch):
    hits = {"n": 0}

    def boom(*_a, **_k):
        hits["n"] += 1
        raise AssertionError("probe dry-run must not HTTP")

    monkeypatch.setenv("MINIMAX_API_KEY", "sk-live-not-placeholder")
    monkeypatch.setattr("httpx.post", boom)
    from app.services.minimax_m31_flash import maybe_startup_probe, probe_m31_flash

    monkeypatch.delenv("MINIMAX_M31_FLASH_PROBE", raising=False)
    report = probe_m31_flash(live=False)
    assert report["ok"] is True
    assert report["live"] is False
    assert hits["n"] == 0
    startup = maybe_startup_probe()
    assert startup["live"] is False
    assert hits["n"] == 0


def test_probe_live_reports_plan_unsupported(monkeypatch):
    class Resp:
        status_code = 403
        text = "model_not_found: MiniMax-M3.1-Flash-Preview not in your plan"

        def json(self):
            return {"base_resp": {"status_code": 1008, "status_msg": "model not available"}}

    monkeypatch.setenv("MINIMAX_API_KEY", "sk-live-not-placeholder")
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.setattr("httpx.post", lambda *a, **k: Resp())
    from app.services.minimax_m31_flash import probe_m31_flash

    report = probe_m31_flash(live=True)
    assert report["ok"] is False
    assert "M Plan" in report["reason"]


def test_meter_records_flash_as_text(monkeypatch, tmp_path):
    from tests.test_minimax_meter import _env

    _env(monkeypatch, tmp_path, "workroom")
    from app.services.minimax_meter import record, totals

    record(kind="text", edition="workroom", model=MODEL, input_tokens=8, output_tokens=2)
    tot = totals(edition="workroom", kind="text")
    assert tot["text_tokens"] >= 10


def test_token_tracker_canonical_flash():
    from app.services.max.token_tracker import TokenTracker

    assert TokenTracker.canonical_model("minimax-MiniMax-M3.1-Flash-Preview") == MODEL
    assert TokenTracker.canonical_model(MODEL) == MODEL


def test_active_model_honors_selector(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "workroom"))
    monkeypatch.setenv("MINIMAX_API_KEY", "test-mm-key")
    monkeypatch.setenv("MINIMAX_MODEL", "MiniMax-M3")
    (tmp_path / "workroom").mkdir()
    from app.services.max.ai_router import AIRouter
    from app.services.max.routing_state import RoutingState

    router = AIRouter()
    router.routing_state = RoutingState(
        selected_provider="minimax",
        selected_model=MODEL,
        fallback_enabled=False,
        ai_calls_disabled=False,
        lane="test",
        updated_at="",
        updated_by="test",
        last_switch_reason="test",
    )
    assert router._minimax_active_model() == MODEL
    assert router._minimax_active_model("MiniMax-M3") == "MiniMax-M3"
