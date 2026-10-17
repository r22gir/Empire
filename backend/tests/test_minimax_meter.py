"""Shared MiniMax meter: caps, isolation, approval, no gift-credit overflow."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _env(monkeypatch, tmp_path, edition="amp"):
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / edition))
    monkeypatch.setenv("MINIMAX_METER_DIR", str(tmp_path / "meter"))
    monkeypatch.setenv("MINIMAX_TEXT_POOL_FLOOR", "1000")
    monkeypatch.setenv("MINIMAX_EDITION_TEXT_SHARE_PCT", "20")
    monkeypatch.setenv("MINIMAX_RESERVED_SHARE_PCT", "80")
    monkeypatch.setenv("MINIMAX_IMAGE_DAILY_CAP", "5")
    monkeypatch.setenv("MINIMAX_TTS_DAILY_CAP", "20")
    monkeypatch.setenv("MINIMAX_VIDEO_WEEKLY_CAP", "1")
    monkeypatch.setenv("MINIMAX_PLAN_HARD_STOP_PCT", "80")
    monkeypatch.setenv("MINIMAX_FAMILY_TTS", "1")
    monkeypatch.setenv("MINIMAX_H3_ENABLED", "1")
    monkeypatch.setenv("MINIMAX_H3_MODEL", "MiniMax-H3-test")
    monkeypatch.setenv("MINIMAX_REMAINS_PROBE", "0")
    monkeypatch.setenv("MINIMAX_REMAINS_STUB", "ok")
    monkeypatch.setenv("MINIMAX_API_KEY", "test-mm-key")
    monkeypatch.delenv("INSTANCE_USAGE_CAP_PCT", raising=False)
    (tmp_path / edition).mkdir(parents=True, exist_ok=True)
    (tmp_path / "meter").mkdir(parents=True, exist_ok=True)


def _seed(monkeypatch, tmp_path, edition: str, *, kind="text", tokens=0, images=0, tts=0, clips=0):
    from app.services.minimax_meter import record

    monkeypatch.setenv("EMPIRE_EDITION", edition)
    if kind == "text":
        record(kind="text", edition=edition, model="MiniMax-M3", input_tokens=tokens, output_tokens=0)
    elif kind == "image":
        record(kind="image", edition=edition, model="image-01", images=images)
    elif kind == "tts":
        for _ in range(tts):
            record(kind="tts", edition=edition, model="speech-2.8-turbo", tts_chars=20)
    elif kind == "video":
        record(kind="video", edition=edition, model="H3", video_clips=clips, approval_id="seed")


def test_existing_20_percent_instance_cap_still_works(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")
    monkeypatch.delenv("EMPIRE_USAGE_BASELINE_MONTHLY_USD", raising=False)
    monkeypatch.delenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", raising=False)
    monkeypatch.setattr("app.services.instance_usage._usage_data_roots", lambda: [tmp_path])
    from app.services.instance_usage import cap_percent, enforce_usage_cap, record_usage, usage_summary

    assert cap_percent() == 20.0
    record_usage(input_tokens=2_000_001, output_tokens=0)
    summary = usage_summary()
    assert summary["cap_percent"] == 20.0
    assert summary["level"] == "paused"
    assert enforce_usage_cap(text="x" * 500)


def test_each_family_edition_capped_at_20_percent(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    _seed(monkeypatch, tmp_path, "amp", tokens=200)
    from app.services.minimax_meter import check

    blocked = check(kind="text", edition="amp", input_tokens=1, source="web")
    assert blocked
    assert "20%" in blocked
    assert "Edition cap" in blocked
    assert "no combined" in blocked.lower() or "no hay tope combinado" in blocked.lower()


def test_no_combined_family_text_cap(monkeypatch, tmp_path):
    """Amp at 15% and Maxine at 18% must not block Amp — no combined 20% limit."""
    _env(monkeypatch, tmp_path, "amp")
    _seed(monkeypatch, tmp_path, "amp", tokens=150)
    _seed(monkeypatch, tmp_path, "maxine", tokens=180)
    from app.services.minimax_meter import check

    assert check(kind="text", edition="amp", input_tokens=10) is None
    assert check(kind="text", edition="maxine", input_tokens=10) is None
    _seed(monkeypatch, tmp_path, "amp", tokens=50)
    blocked = check(kind="text", edition="amp", input_tokens=1, source="web")
    assert blocked
    assert "Edition cap" in blocked
    assert "Family cap" not in blocked


def test_rafael_not_limited_by_family_20(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "workroom")
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    _seed(monkeypatch, tmp_path, "workroom", tokens=500)
    from app.services.minimax_meter import check

    assert check(kind="text", edition="workroom", input_tokens=10) is None


def test_image_daily_cap_and_isolation(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    for _ in range(5):
        _seed(monkeypatch, tmp_path, "amp", kind="image", images=1)
    from app.services.minimax_meter import check

    assert check(kind="image", edition="amp", images=1)
    assert check(kind="image", edition="maxine", images=1) is None


def test_tts_daily_cap_and_flag(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "maxine")
    for _ in range(20):
        _seed(monkeypatch, tmp_path, "maxine", kind="tts", tts=1)
    from app.services.minimax_meter import check, family_tts_enabled

    assert family_tts_enabled() is True
    assert check(kind="tts", edition="maxine", tts_chars=20, tts_replies=1)
    monkeypatch.setenv("MINIMAX_FAMILY_TTS", "0")
    assert check(kind="tts", edition="maxine", tts_chars=10, tts_replies=1)
    assert "MINIMAX_FAMILY_TTS" in check(kind="tts", edition="maxine", tts_chars=10, tts_replies=1)


def test_video_requires_approval_and_weekly_cap(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "workroom")
    from app.services.minimax_meter import check
    from app.services.minimax_video import approve, create_draft, explicit_yes

    assert check(kind="video", edition="workroom")
    draft = create_draft("a silent clock, no people", edition="workroom")
    class Req:
        headers = {}
    assert explicit_yes(Req(), True) is False
    with pytest.raises(PermissionError):
        approve(draft["id"], confirmed=False)
    class Yes:
        headers = {"x-minimax-video-confirm": "aprobar"}
    assert explicit_yes(Yes(), False) is True
    approve(draft["id"], confirmed=True)
    assert check(kind="video", edition="workroom", approval_id=draft["id"], video_clips=1) is None
    _seed(monkeypatch, tmp_path, "workroom", kind="video", clips=1)
    assert check(kind="video", edition="workroom", approval_id=draft["id"], video_clips=1)


def test_h3_flag_blocks(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "workroom")
    monkeypatch.setenv("MINIMAX_H3_ENABLED", "0")
    from app.services.minimax_meter import check

    msg = check(kind="video", edition="workroom", approval_id="x")
    assert msg and "MINIMAX_H3_ENABLED" in msg


def test_plan_bar_hard_stop_all_editions(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "workroom")
    from app.services import minimax_meter

    monkeypatch.setattr(
        minimax_meter,
        "_plan_snapshot",
        lambda: {
            "remains": {"available": True, "remaining_pct": 15.0, "used_pct": 85.0},
            "credits": {"available": True, "balance": 2000},
        },
    )
    assert minimax_meter.check(kind="text", edition="workroom", input_tokens=1)
    assert minimax_meter.check(kind="text", edition="amp", input_tokens=1)
    assert "gift credits" in minimax_meter.check(kind="image", edition="maxine", images=1).lower()


def test_credits_are_not_room(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    from app.services.minimax_quota import parse_remains

    parsed = parse_remains({
        "base_resp": {"status_code": 0},
        "model_remains": [{"model_type": "general", "remaining": 12.0, "weekly_remaining": 40.0}],
        "credit": 2000,
    })
    assert parsed["remaining_pct"] == 12.0
    assert parsed["used_pct"] == 88.0
    assert parsed["credit_hint"] == 2000
    from app.services.minimax_meter import plan_hard_stopped

    msg = plan_hard_stopped({
        "remains": parsed,
        "credits": {"available": True, "balance": 2000},
    })
    assert msg
    assert "créditos de regalo" in msg or "gift credits" in msg.lower()


def test_append_only_log_never_writes_key(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-super-secret-meter-key")
    from app.services.minimax_meter import log_path, record

    record(kind="text", model="MiniMax-M3", input_tokens=4, reason="used sk-super-secret-meter-key")
    blob = log_path().read_text(encoding="utf-8")
    assert "sk-super-secret-meter-key" not in blob
    assert "[KEY_REDACTED]" in blob
    rec = json.loads(blob.strip())
    assert rec["kind"] == "text"
    assert rec["edition"] == "amp"


def test_founder_summary_lists_editions_family_me_does_not(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    _seed(monkeypatch, tmp_path, "amp", tokens=20)
    _seed(monkeypatch, tmp_path, "maxine", tokens=10)
    from app.services.minimax_meter import edition_public_summary, founder_summary

    mine = edition_public_summary("amp")
    assert mine["edition"] == "amp"
    assert "editions" not in mine
    assert mine["text_cap_pct"] == 20
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    full = founder_summary()
    names = {row["edition"] for row in full["editions"]}
    assert names == {"workroom", "amp", "maxine"}
    assert full["edition_text_share_pct"] == 20
    assert full["combined_family_cap"] is False
    amp = next(row for row in full["editions"] if row["edition"] == "amp")
    maxine = next(row for row in full["editions"] if row["edition"] == "maxine")
    assert amp["text_tokens"] != maxine["text_tokens"]
    assert amp["text_cap_pct"] == 20
    assert maxine["text_cap_pct"] == 20


def test_prompt_sanitizer_strips_workroom_and_client_data(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    from app.services.minimax_prompts import PromptRejected, sanitize_prompt

    cleaned = sanitize_prompt("a blue chair for the living room, no people")
    assert "blue chair" in cleaned
    with pytest.raises(PromptRejected):
        sanitize_prompt("quote for Nelma at 5124 Frolich Hyattsville")
    out = sanitize_prompt("send to jane@client.com at +1 202 555 0100")
    assert "jane@client.com" not in out
    assert "+1 202 555 0100" not in out


def test_workroom_photo_path_blocked_for_family_image_prompts(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    from app.services.minimax_prompts import PromptRejected, sanitize_prompt

    with pytest.raises(PromptRejected, match="photo path"):
        sanitize_prompt("use /home/rg/empire-repo/backend/data/photos/quote/52/cc.jpeg")
    with pytest.raises(PromptRejected, match="photo path"):
        sanitize_prompt("see /api/v1/photos/serve/quote/3/room.jpg")
    with pytest.raises(PromptRejected, match="photo path"):
        sanitize_prompt("workroom-showroom/photos/bed-cognac-panel-headboard.jpg")
    ok = sanitize_prompt("a navy drapery panel, no people")
    assert "navy" in ok


def test_family_image_to_image_blocked(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "maxine")
    from app.services.minimax_media import reject_family_image_to_image

    assert reject_family_image_to_image()


def test_router_family_forbidden_from_founder_usage(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    from fastapi import HTTPException
    from app.routers import minimax_meter as routes

    with pytest.raises(HTTPException) as exc:
        import asyncio
        asyncio.run(routes.founder_usage())
    assert exc.value.status_code == 403


def test_compare_snapshots_plan_vs_credits():
    from app.services.minimax_video import compare_snapshots

    before = {"plan_remaining_pct": 50.0, "credit_balance": 2000, "plan_available": True}
    after = {"plan_remaining_pct": 48.0, "credit_balance": 2000, "plan_available": True}
    cmp = compare_snapshots(before, after)
    assert cmp["verdict"] == "plan_quota"
    after_credit = {"plan_remaining_pct": 50.0, "credit_balance": 1800, "plan_available": True}
    assert compare_snapshots(before, after_credit)["verdict"] == "credit_balance"


def _load_probe():
    import importlib.util
    path = Path(__file__).resolve().parents[2] / "scripts" / "minimax_h3_probe.py"
    spec = importlib.util.spec_from_file_location("minimax_h3_probe", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_probe_script_dry_run_no_key_exit(monkeypatch, tmp_path):
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    assert _load_probe().main([]) == 2


def test_probe_script_refuses_live_without_flag(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "workroom")
    monkeypatch.setenv("MINIMAX_H3_PROBE_LIVE", "0")
    assert _load_probe().main(["--live"]) == 2


def test_quota_parser_auth_failure():
    from app.services.minimax_quota import QuotaUnavailable, parse_remains

    with pytest.raises(QuotaUnavailable):
        parse_remains({"base_resp": {"status_code": 2049}})
