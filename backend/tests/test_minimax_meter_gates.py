"""Review blockers on PR #102: fail-closed remains, lock, video, auth, H3 flag."""
from __future__ import annotations

import asyncio
import threading

import pytest

from tests.test_minimax_meter import _env, _seed  # helpers shared with cap tests


def test_remains_down_fail_closed_nonessential_and_family(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    monkeypatch.setenv("MINIMAX_REMAINS_STUB", "down")
    from app.services.minimax_meter import check, remains_down_message

    down = remains_down_message()
    for kind, kwargs in (
        ("image", {"images": 1}),
        ("tts", {"tts_chars": 10, "tts_replies": 1}),
        ("text", {"input_tokens": 1}),
    ):
        msg = check(kind=kind, edition="amp", **kwargs)
        assert msg, kind
        assert "token_plan/remains" in msg or "gift" in msg.lower() or "créditos" in msg
    assert down
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    assert check(kind="image", edition="workroom", images=1)
    assert check(kind="tts", edition="workroom", tts_chars=10, tts_replies=1)
    assert check(kind="video", edition="workroom", approval_id="x", video_clips=1)


def test_remains_down_founder_text_local_estimate_with_warning(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "workroom")
    monkeypatch.setenv("MINIMAX_REMAINS_STUB", "down")
    from app.services.minimax_meter import check, founder_remains_warning, pop_plan_warning, reserve

    assert check(kind="text", edition="workroom", input_tokens=8) is None
    reservation = reserve(kind="text", edition="workroom", input_tokens=8)
    assert reservation.blocked is False
    warning = reservation.warning or pop_plan_warning()
    assert warning
    assert "local" in warning.lower() or "estimación" in warning.lower()
    assert "Auto credit usage" in founder_remains_warning()

    _seed(monkeypatch, tmp_path, "workroom", tokens=800)
    blocked = check(kind="text", edition="workroom", input_tokens=1)
    assert blocked
    assert "local" in blocked.lower() or "Estimación" in blocked


def test_founder_text_stopped_at_plan_80_not_only_prep(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "workroom")
    monkeypatch.setenv("MINIMAX_REMAINS_STUB", "hot")
    from app.services.minimax_meter import MeterBlocked, reserve

    reservation = reserve(kind="text", edition="workroom", input_tokens=4, model="MiniMax-M3")
    assert reservation.blocked
    assert "80" in reservation.message or "gift credits" in reservation.message.lower()
    with pytest.raises(MeterBlocked):
        raise MeterBlocked(reservation.message)


def test_reserve_lock_prevents_concurrent_overshoot(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    monkeypatch.setenv("MINIMAX_IMAGE_DAILY_CAP", "1")
    from app.services.minimax_meter import reserve

    results = []

    def go():
        results.append(reserve(kind="image", edition="amp", images=1, model="image-01"))

    threads = [threading.Thread(target=go), threading.Thread(target=go)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    ok = [row for row in results if not row.blocked]
    blocked = [row for row in results if row.blocked]
    assert len(ok) == 1
    assert len(blocked) == 1


def test_reserved_counts_until_reconcile_and_billed_unknown_keeps_cap(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    monkeypatch.setenv("MINIMAX_IMAGE_DAILY_CAP", "1")
    from app.services.minimax_meter import check, reconcile, reserve

    first = reserve(kind="image", edition="amp", images=1)
    assert not first.blocked
    assert check(kind="image", edition="amp", images=1)
    reconcile(first, images=0)
    assert check(kind="image", edition="amp", images=1) is None
    second = reserve(kind="image", edition="amp", images=1)
    assert not second.blocked
    reconcile(second, billed_unknown=True, error="http 500 after billing")
    assert check(kind="image", edition="amp", images=1)


def test_video_generating_reserve_before_http_records_on_error(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "workroom")
    from app.services.minimax_meter import totals
    from app.services.minimax_video import approve, create_draft, generate_approved_clip, get_draft

    draft = create_draft("a silent clock, no people", edition="workroom")
    approve(draft["id"], confirmed=True)

    class FakeResp:
        status_code = 500
        text = "billed-then-error"

        def json(self):
            return {"error": "nope"}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, *args, **kwargs):
            row = get_draft(draft["id"])
            assert row["status"] == "generating"
            assert totals(kind="video")["video_clips"] >= 1
            return FakeResp()

    monkeypatch.setattr("httpx.AsyncClient", FakeClient)
    with pytest.raises(RuntimeError):
        asyncio.run(generate_approved_clip(draft["id"], caller_edition="workroom"))
    assert totals(kind="video")["video_clips"] >= 1
    row = get_draft(draft["id"])
    assert row["status"] == "error"
    assert (row.get("result") or {}).get("billed_unknown") is True


def test_generate_rejects_edition_mismatch(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    from app.services.minimax_video import approve, create_draft, generate_approved_clip

    draft = create_draft("a silent clock, no people", edition="amp")
    approve(draft["id"], confirmed=True)
    with pytest.raises(PermissionError, match="edition"):
        asyncio.run(generate_approved_clip(draft["id"], caller_edition="maxine"))


def test_llm_video_tool_drafts_only_ignores_approval_id(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "workroom")
    from app.services.max.tool_executor import _minimax_video_async
    from app.services.minimax_video import approve, create_draft, get_draft

    draft = create_draft("a silent clock, no people", edition="workroom")
    approve(draft["id"], confirmed=True)
    result = asyncio.run(_minimax_video_async({"prompt": "clock", "approval_id": draft["id"]}))
    assert result.success is False
    assert "cannot generate" in (result.error or "").lower() or "no genera" in (result.error or "").lower()
    assert get_draft(draft["id"])["status"] == "approved"

    draft_only = asyncio.run(_minimax_video_async({"prompt": "a silent clock, no people"}))
    assert draft_only.success is True
    assert draft_only.result["status"] == "draft"


def test_family_image_and_drafts_require_admin(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    from fastapi import HTTPException
    from app.routers import minimax_meter as routes

    class State:
        amp_email = "cousin@example.com"

    class Req:
        state = State()
        headers = {}

    monkeypatch.setattr("app.services.amp_allowlist.entry_role", lambda **kwargs: "member")
    with pytest.raises(HTTPException) as image_exc:
        asyncio.run(routes.generate_image(routes.ImageBody(prompt="a navy chair"), Req()))
    assert image_exc.value.status_code == 403
    with pytest.raises(HTTPException) as draft_exc:
        asyncio.run(routes.create_video_draft(routes.VideoDraftBody(prompt="a silent clock"), Req()))
    assert draft_exc.value.status_code == 403


def test_legacy_video_enabled_does_not_enable_h3(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "workroom")
    monkeypatch.setenv("MINIMAX_H3_ENABLED", "0")
    monkeypatch.setenv("MINIMAX_VIDEO_ENABLED", "1")
    from app.services.minimax_meter import check, h3_enabled

    assert h3_enabled() is False
    msg = check(kind="video", edition="workroom", approval_id="x", video_clips=1)
    assert msg and "MINIMAX_H3_ENABLED" in msg
    assert "MINIMAX_VIDEO_ENABLED" in msg or "does not enable" in msg.lower() or "no lo enciende" in msg.lower()


def test_no_silent_hailuo_default(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "workroom")
    monkeypatch.delenv("MINIMAX_H3_MODEL", raising=False)
    from app.services.minimax_meter import check, h3_model

    assert h3_model() == ""
    msg = check(kind="video", edition="workroom", approval_id="x", video_clips=1)
    assert msg
    assert "MINIMAX_H3_MODEL" in msg
    assert "Hailuo" in msg or "silent" in msg.lower() or "silencio" in msg.lower()


def test_per_edition_files_modes_and_founder_queue(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    from app.services.minimax_meter import (
        edition_dir,
        file_modes,
        founder_video_queue_dir,
        log_path,
        record,
        video_drafts_dir,
    )
    from app.services.minimax_video import create_draft, list_queue

    record(kind="text", edition="amp", model="MiniMax-M3", input_tokens=4)
    path = log_path("amp")
    assert path.name == "calls-amp.jsonl"
    assert path.parent == edition_dir("amp")
    modes = file_modes("amp")
    assert modes["dir"] == 0o700
    assert modes["file"] == 0o600
    assert not log_path("maxine").exists()

    draft = create_draft("a silent clock, no people", edition="amp")
    family_path = video_drafts_dir("amp") / f"{draft['id']}.json"
    assert family_path.is_file()
    import stat as _stat
    assert _stat.S_IMODE(family_path.stat().st_mode) == 0o600
    queue = founder_video_queue_dir()
    assert _stat.S_IMODE(queue.stat().st_mode) == 0o700
    assert not (queue / f"{draft['id']}.json").exists()
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    items = list_queue()
    assert any(row["id"] == draft["id"] for row in items)


def test_key_scrubbing_authorization_and_env(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "amp")
    secret = "sk-live-meter-secret-999"
    monkeypatch.setenv("MINIMAX_API_KEY", secret)
    from app.services.minimax_meter import log_path, record, redact
    from app.services.minimax_quota import redact_secret

    dirty = f"Authorization: Bearer {secret} api_key={secret} MINIMAX_API_KEY={secret}"
    assert secret not in redact(dirty)
    assert secret not in redact_secret(dirty)
    record(kind="text", edition="amp", model="MiniMax-M3", input_tokens=1, reason=dirty)
    blob = log_path("amp").read_text(encoding="utf-8")
    assert secret not in blob
    assert "[KEY_REDACTED]" in blob
