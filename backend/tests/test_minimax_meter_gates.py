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
    """Remains unread: warn, but never pause Rafael's personal text on a local guess."""
    _env(monkeypatch, tmp_path, "workroom")
    monkeypatch.setenv("MINIMAX_REMAINS_STUB", "down")
    from app.services.minimax_meter import check, founder_remains_warning, pop_plan_warning, reserve

    assert check(kind="text", edition="workroom", input_tokens=8) is None
    reservation = reserve(kind="text", edition="workroom", input_tokens=8)
    assert reservation.blocked is False
    warning = reservation.warning or pop_plan_warning()
    assert warning
    assert "unread" in warning.lower() or "aviso" in warning.lower() or "sigue" in warning.lower()
    assert "Auto credit usage" in founder_remains_warning()
    assert "paused" not in warning.lower()

    _seed(monkeypatch, tmp_path, "workroom", tokens=800)
    still = check(kind="text", edition="workroom", input_tokens=1)
    assert still is None
    again = reserve(kind="text", edition="workroom", input_tokens=1)
    assert again.blocked is False
    assert again.warning or pop_plan_warning()


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
    from app.services.minimax_video import (
        approve,
        create_draft,
        get_draft,
        llm_create_draft,
        llm_tool_refuses_generate,
    )

    draft = create_draft("a silent clock, no people", edition="workroom")
    approve(draft["id"], confirmed=True)
    refusal = llm_tool_refuses_generate({"prompt": "clock", "approval_id": draft["id"]})
    assert refusal
    assert "cannot generate" in refusal.lower() or "no genera" in refusal.lower()
    with pytest.raises(PermissionError, match="cannot generate|no genera"):
        llm_create_draft({"prompt": "clock", "approval_id": draft["id"]})
    assert get_draft(draft["id"])["status"] == "approved"

    draft_only = llm_create_draft({"prompt": "a silent clock, no people"})
    assert draft_only["status"] == "draft"
    assert draft_only["id"] != draft["id"]

    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "app/services/max/tool_executor.py"
    blob = src.read_text(encoding="utf-8")
    start = blob.find("async def _minimax_video_async")
    end = blob.find("\n@tool(\"minimax_h3_video\")", start)
    fn = blob[start:end]
    assert "generate_approved_clip" not in fn
    assert "llm_tool_refuses_generate" in fn


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


def test_one_snapshot_per_reserve_and_outside_lock(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "workroom")
    from app.services import minimax_meter
    from pathlib import Path

    calls = {"n": 0, "while_locked": 0}
    held = {"on": False}
    real_snap = minimax_meter._plan_snapshot
    real_lock = minimax_meter._with_exclusive_lock

    def counted():
        calls["n"] += 1
        if held["on"]:
            calls["while_locked"] += 1
        return real_snap()

    def locked():
        held["on"] = True
        handle = real_lock()

        class _Handle:
            def close(self_inner):
                held["on"] = False
                handle.close()

        return _Handle()

    monkeypatch.setattr(minimax_meter, "_plan_snapshot", counted)
    monkeypatch.setattr(minimax_meter, "_with_exclusive_lock", locked)
    reservation = minimax_meter.reserve(kind="text", edition="workroom", input_tokens=4)
    assert reservation.blocked is False
    assert calls["n"] == 1
    assert calls["while_locked"] == 0

    router = Path(__file__).resolve().parents[1] / "app/services/max/ai_router.py"
    blob = router.read_text(encoding="utf-8")
    assert "asyncio.to_thread(self._reserve_minimax_text" in blob


def test_remains_down_does_not_slow_chat(monkeypatch, tmp_path):
    """Down remains endpoint: timeout ≤ 3s, negative cache, chat reserve stays fast."""
    import time
    from app.services import minimax_quota
    from app.services.minimax_quota import QuotaUnavailable, clear_quota_cache, fetch_remains, probe_timeout

    _env(monkeypatch, tmp_path, "workroom")
    monkeypatch.delenv("MINIMAX_REMAINS_STUB", raising=False)
    monkeypatch.setenv("MINIMAX_REMAINS_TIMEOUT", "3")
    monkeypatch.setenv("MINIMAX_REMAINS_FAILURE_TTL", "45")
    assert probe_timeout() <= 3.0

    hits = {"n": 0}

    def down(url, timeout=None):
        hits["n"] += 1
        assert timeout is None or float(timeout) <= 3.01
        raise QuotaUnavailable("connect timeout")

    monkeypatch.setattr(minimax_quota, "_get_json", down)
    monkeypatch.setattr(minimax_quota, "remains_probe_enabled", lambda: True)
    clear_quota_cache()

    t0 = time.monotonic()
    first = fetch_remains(force=True)
    first_elapsed = time.monotonic() - t0
    assert first.get("available") is False
    assert first_elapsed < 1.0
    first_hits = hits["n"]
    assert first_hits >= 1

    t1 = time.monotonic()
    second = fetch_remains()
    second_elapsed = time.monotonic() - t1
    assert second.get("available") is False
    assert hits["n"] == first_hits
    assert second_elapsed < 0.2

    from app.services.minimax_meter import reserve

    monkeypatch.setattr("app.services.minimax_meter._plan_snapshot", lambda: {
        "remains": second,
        "credits": {"ok": False, "available": False, "balance": None},
    })
    t2 = time.monotonic()
    for _ in range(8):
        row = reserve(kind="text", edition="workroom", input_tokens=6)
        assert row.blocked is False
    reserve_elapsed = time.monotonic() - t2
    assert reserve_elapsed < 0.5


def test_hanging_remains_http_stays_within_probe_budget(monkeypatch, tmp_path):
    """Accept-and-hold HTTP must not inherit the old 12s sync timeout."""
    import socket
    import threading
    import time
    from app.services import minimax_quota
    from app.services.minimax_quota import clear_quota_cache, fetch_remains, probe_timeout

    _env(monkeypatch, tmp_path, "workroom")
    monkeypatch.delenv("MINIMAX_REMAINS_STUB", raising=False)
    monkeypatch.setenv("MINIMAX_REMAINS_TIMEOUT", "0.35")
    monkeypatch.setenv("MINIMAX_REMAINS_FAILURE_TTL", "45")
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-live-not-a-placeholder-key")
    assert probe_timeout() <= 3.0

    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(8)
    port = sock.getsockname()[1]
    stop = threading.Event()

    def hold():
        sock.settimeout(0.15)
        while not stop.is_set():
            try:
                conn, _ = sock.accept()
            except (socket.timeout, OSError):
                continue
            try:
                while not stop.is_set():
                    time.sleep(0.05)
            finally:
                try:
                    conn.close()
                except OSError:
                    pass

    threading.Thread(target=hold, daemon=True).start()
    try:
        monkeypatch.setenv("MINIMAX_REMAINS_BASE", f"http://127.0.0.1:{port}")
        monkeypatch.setenv("MINIMAX_BASE_URL", f"http://127.0.0.1:{port}/v1")
        monkeypatch.setattr(minimax_quota, "remains_probe_enabled", lambda: True)
        clear_quota_cache()

        t0 = time.monotonic()
        first = fetch_remains(force=True)
        first_elapsed = time.monotonic() - t0
        assert first.get("available") is False
        assert first_elapsed < 1.2

        t1 = time.monotonic()
        second = fetch_remains()
        second_elapsed = time.monotonic() - t1
        assert second.get("available") is False
        assert second_elapsed < 0.2

        from app.services.minimax_meter import reserve

        monkeypatch.setattr("app.services.minimax_meter._plan_snapshot", lambda: {
            "remains": second,
            "credits": {"ok": False, "available": False, "balance": None},
        })
        t2 = time.monotonic()
        row = reserve(kind="text", edition="workroom", input_tokens=6)
        assert row.blocked is False
        assert (time.monotonic() - t2) < 0.3
    finally:
        stop.set()
        sock.close()


def test_tts_meter_error_keeps_provider_fallback(monkeypatch, tmp_path):
    """Meter exception (not an explicit block) must not kill Telegram/web voice."""
    _env(monkeypatch, tmp_path, "workroom")
    monkeypatch.setenv("MINIMAX_API_KEY", "test-mm-key")
    monkeypatch.setenv("XAI_API_KEY", "test-xai-key")

    from app.services.max.tts_service import TTSService

    svc = TTSService()
    out = tmp_path / "voice.mp3"
    out.write_bytes(b"ID3")

    async def no_minimax(*_a, **_k):
        return None

    async def yes_xai(*_a, **_k):
        return out

    def meter_boom(**_k):
        raise RuntimeError("meter lock unavailable")

    monkeypatch.setattr(svc, "_synthesize_minimax", no_minimax)
    monkeypatch.setattr(svc, "_synthesize_xai", yes_xai)
    monkeypatch.setattr("app.services.minimax_meter.reserve", meter_boom)

    path = asyncio.run(svc.synthesize("hola Rafael"))
    assert path == out
    assert svc.last_status == "ok"
    assert svc.last_provider == "xai"
    assert svc.last_status != "blocked"
