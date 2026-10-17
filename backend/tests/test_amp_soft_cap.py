"""8a — Rafael-aware soft 20% cap. Tmp EMPIRE_DATA_DIR only."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.services.instance_usage import (
    MENSAJE_OVERAGE,
    MENSAJE_PAUSED,
    MENSAJE_PAUSED_REMAINS,
    MENSAJE_PAUSED_RESERVE,
    MENSAJE_PAUSED_SIGNAL,
    MENSAJE_PAUSED_STALE,
    enforce_usage_cap,
    family_overage_allowed,
    public_usage_summary,
    record_usage,
    usage_summary,
)


def _env(monkeypatch, tmp_path, edition="amp"):
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Max-e")
    monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")
    monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", "1000")
    monkeypatch.setenv("FAMILY_ABSOLUTE_MAX_PCT", "40")
    monkeypatch.setenv("FOUNDER_SIGNAL_MAX_AGE_S", "180")
    monkeypatch.setattr("app.services.instance_usage._usage_data_roots", lambda: [tmp_path])
    monkeypatch.delenv("EMPIRE_USAGE_BASELINE_MONTHLY_USD", raising=False)


def _write_signal(tmp_path: Path, *, overage_allowed=True, founder_active=False,
                  reserve_ok=True, reason="inactive_reserve_ok",
                  updated_at=None, extra=None, raw=None):
    folder = tmp_path / "founder-signal"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "status.json"
    if raw is not None:
        path.write_text(raw, encoding="utf-8")
        return path
    now = updated_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "schema": 1,
        "updated_at": now,
        "founder_active": founder_active,
        "founder_last_active_at": now,
        "reserve_ok": reserve_ok,
        "overage_allowed": overage_allowed,
        "reason": reason,
    }
    if extra:
        payload.update(extra)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _set_used(tokens: int):
    record_usage(input_tokens=tokens, output_tokens=0, model="MiniMax-M3")


def test_under_base_chat_allowed_regardless_of_signal(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _set_used(100)  # 10%
    assert usage_summary()["level"] == "ok"
    assert enforce_usage_cap(text="hola") is None
    _write_signal(tmp_path, overage_allowed=False, founder_active=True, reason="founder_active")
    assert enforce_usage_cap(text="hola") is None
    assert family_overage_allowed() is False


def test_overage_allows_chat_refuses_desk_task(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _set_used(250)  # 25%
    _write_signal(tmp_path, overage_allowed=True, founder_active=False)
    summary = usage_summary()
    assert summary["level"] == "overage"
    assert summary["message"] == MENSAJE_OVERAGE
    assert family_overage_allowed() is True
    assert enforce_usage_cap(text="hola manito", source="web") is None
    assert enforce_usage_cap(kind="chat", source="voice") is None
    refused = enforce_usage_cap(kind="desk_task", text="audit", source="scheduler")
    assert refused == MENSAJE_OVERAGE
    public = public_usage_summary()
    assert public["overage_active"] is True
    assert public["meter_label_es"] == "Tiempo extra (Rafael no está)"
    assert "allowance" not in public
    assert "baseline" not in public
    assert "month" not in public
    assert "tokens" not in public


def test_paused_when_founder_active_stale_missing_malformed(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _set_used(250)

    # missing
    summary = usage_summary()
    assert summary["level"] == "paused"
    assert summary["message"] == MENSAJE_PAUSED_SIGNAL
    assert enforce_usage_cap(text="hola", source="web") == MENSAJE_PAUSED_SIGNAL
    assert family_overage_allowed() is False

    stale = (datetime.now(timezone.utc) - timedelta(seconds=400)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _write_signal(tmp_path, overage_allowed=True, updated_at=stale)
    assert usage_summary()["level"] == "paused"
    assert usage_summary()["message"] == MENSAJE_PAUSED_STALE
    assert enforce_usage_cap(text="hola", source="web") == MENSAJE_PAUSED_STALE

    _write_signal(tmp_path, raw="{not json")
    assert usage_summary()["level"] == "paused"
    assert "señal" in usage_summary()["message"]

    _write_signal(tmp_path, overage_allowed=False, founder_active=True, reason="founder_active")
    assert usage_summary()["level"] == "paused"
    public = public_usage_summary()
    assert public["overage_active"] is False
    assert public["meter_label_es"] == "En pausa: Rafael está usando Max"
    assert public["message"] == MENSAJE_PAUSED


def test_absolute_max_refuses_even_if_signal_allows(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _set_used(450)  # 45% > 40
    _write_signal(tmp_path, overage_allowed=True, founder_active=False)
    assert family_overage_allowed() is False
    summary = usage_summary()
    assert summary["level"] == "paused"
    assert "40%" in summary["message"]
    assert "tope extra" in summary["message"]
    assert enforce_usage_cap(text="hola", source="web") == summary["message"]
    assert enforce_usage_cap(kind="desk_task", source="scheduler") == summary["message"]


def test_minimax_family_text_mirrors_soft_cap(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MINIMAX_METER_DIR", str(tmp_path / "meter"))
    monkeypatch.setenv("MINIMAX_TEXT_POOL_FLOOR", "1000")
    monkeypatch.setenv("MINIMAX_EDITION_TEXT_SHARE_PCT", "20")
    monkeypatch.setenv("MINIMAX_REMAINS_STUB", "ok")
    monkeypatch.setenv("MINIMAX_REMAINS_PROBE", "0")
    monkeypatch.setenv("FAMILY_ABSOLUTE_MAX_PCT", "40")
    monkeypatch.setenv("FOUNDER_SIGNAL_MAX_AGE_S", "180")
    (tmp_path / "meter").mkdir(parents=True, exist_ok=True)
    from app.services.minimax_meter import check, record

    record(kind="text", edition="amp", model="MiniMax-M3", input_tokens=250, output_tokens=0)
    blocked = check(kind="text", edition="amp", input_tokens=1, source="web")
    assert blocked
    _write_signal(tmp_path, overage_allowed=True, founder_active=False)
    assert check(kind="text", edition="amp", input_tokens=1, source="web") is None
    assert check(kind="text", edition="amp", input_tokens=1, source="scheduler")
    _write_signal(tmp_path, overage_allowed=False, founder_active=True, reason="founder_active")
    assert check(kind="text", edition="amp", input_tokens=1, source="web")


def test_desk_chat_never_gets_overage_even_with_allowed_signal(monkeypatch, tmp_path):
    """ai_router always passes kind='chat'; desk calls have desk= and empty source."""
    _env(monkeypatch, tmp_path)
    _set_used(250)
    _write_signal(tmp_path, overage_allowed=True, founder_active=False)
    refused = enforce_usage_cap(kind="chat", desk="finance", source="")
    assert refused is not None
    assert enforce_usage_cap(kind="chat", source="") is not None
    assert enforce_usage_cap(kind="chat", source="unknown-job") is not None
    assert enforce_usage_cap(kind="chat", source="web") is None
    assert enforce_usage_cap(kind="chat", source="voice") is None
    assert enforce_usage_cap(kind="chat", source="dashboard") is None
    assert enforce_usage_cap(kind="chat", source="dashboard", desk="finance") is not None


def test_paused_names_reserve_low(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _set_used(250)
    _write_signal(
        tmp_path,
        overage_allowed=False,
        founder_active=False,
        reserve_ok=False,
        reason="reserve_low",
    )
    summary = usage_summary()
    assert summary["level"] == "paused"
    assert summary["message"] == MENSAJE_PAUSED_RESERVE
    public = public_usage_summary()
    assert public["meter_label_es"] == "En pausa: la reserva de Rafael está baja"


def test_brother_ceiling_pct_uses_the_lower_value(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _set_used(350)  # 35%
    _write_signal(
        tmp_path,
        overage_allowed=True,
        founder_active=False,
        extra={"brother_ceiling_pct": 30, "ignored_field": "x"},
    )
    assert family_overage_allowed() is False
    summary = usage_summary()
    assert summary["level"] == "paused"
    assert "30%" in summary["message"]
    _write_signal(
        tmp_path,
        overage_allowed=True,
        founder_active=False,
        extra={"brother_ceiling_pct": 50},
    )
    assert family_overage_allowed() is True
    assert usage_summary()["level"] == "overage"


def test_remains_unavailable_is_not_reserve_low(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _set_used(250)
    _write_signal(
        tmp_path,
        overage_allowed=False,
        founder_active=False,
        reserve_ok=False,
        reason="remains_unavailable",
    )
    summary = usage_summary()
    assert summary["message"] == MENSAJE_PAUSED_REMAINS
    assert "reserva baja" not in summary["message"]
    assert "saldo de Max" in summary["message"]
    public = public_usage_summary()
    assert public["meter_label_es"] == "En pausa: no puedo leer el saldo de Max"

    _write_signal(
        tmp_path,
        overage_allowed=False,
        founder_active=False,
        reserve_ok=False,
        reason="remains_stale",
    )
    assert usage_summary()["message"] == MENSAJE_PAUSED_REMAINS
    assert enforce_usage_cap(text="hola", source="web") == MENSAJE_PAUSED_REMAINS


def test_max_chat_and_stream_overage_with_usage_source(monkeypatch, tmp_path):
    """Juan's chats send usage_source separately; channel stays dashboard."""
    _env(monkeypatch, tmp_path)
    _set_used(250)
    _write_signal(tmp_path, overage_allowed=True, founder_active=False)
    monkeypatch.setenv("MINIMAX_METER_DIR", str(tmp_path / "meter"))
    monkeypatch.setenv("MINIMAX_REMAINS_STUB", "ok")
    monkeypatch.setenv("MINIMAX_REMAINS_PROBE", "0")
    (tmp_path / "meter").mkdir(parents=True, exist_ok=True)

    from app.services.max.ai_router import AIResponse, ai_router

    seen: list[tuple[str, str, object]] = []

    async def fake_chat(
        messages, model=None, image_filename=None, desk=None, system_prompt=None,
        tenant_id="founder", source="", conversation_id="", tools=None,
    ):
        seen.append(("chat", source, desk))
        _model, refusal = ai_router._family_chat_prep(
            messages, desk=desk, tools=bool(tools), source=source,
            image_filename=image_filename, model=model,
        )
        if refusal:
            return AIResponse(content=refusal, model_used="usage-cap", fallback_used=False)
        return AIResponse(content="ok manito", model_used="MiniMax-M3", fallback_used=False)

    async def fake_stream(
        messages, model=None, image_filename=None, desk=None, system_prompt=None,
        tenant_id="founder", source="", conversation_id="",
    ):
        seen.append(("stream", source, desk))
        _model, refusal = ai_router._family_chat_prep(
            messages, desk=desk, tools=False, source=source,
            image_filename=image_filename, model=model,
        )
        if refusal:
            yield refusal, "usage-cap"
            return
        yield "ok manito", "MiniMax-M3"

    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers.max.router import router

    monkeypatch.setattr(ai_router, "chat", fake_chat)
    monkeypatch.setattr(ai_router, "chat_stream", fake_stream)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    chat = client.post(
        "/api/v1/max/chat",
        json={"message": "hola manito", "channel": "dashboard", "usage_source": "web"},
    )
    assert chat.status_code == 200, chat.text
    assert chat.json()["response"] == "ok manito"
    assert chat.json()["model_used"] != "usage-cap"

    stream = client.post(
        "/api/v1/max/chat/stream",
        json={"message": "hola manito", "channel": "dashboard", "usage_source": "web"},
    )
    assert stream.status_code == 200, stream.text
    assert "ok manito" in stream.text
    assert "usage-cap" not in stream.text

    voice = client.post(
        "/api/v1/max/chat/stream",
        json={"message": "hola manito", "channel": "dashboard", "usage_source": "voice"},
    )
    assert voice.status_code == 200, voice.text
    assert "ok manito" in voice.text

    old_client = client.post(
        "/api/v1/max/chat/stream",
        json={"message": "hola manito", "channel": "dashboard"},
    )
    assert old_client.status_code == 200, old_client.text
    assert "ok manito" in old_client.text

    sources = {src for _kind, src, _desk in seen}
    assert "web" in sources
    assert "voice" in sources
    assert "dashboard" in sources
    assert enforce_usage_cap(kind="chat", desk="finance", source="") is not None
    desk_http = client.post(
        "/api/v1/max/chat",
        json={"message": "hola manito", "channel": "dashboard", "usage_source": "web", "desk": "finance"},
    )
    assert desk_http.status_code == 200
    assert desk_http.json()["model_used"] == "usage-cap"
    assert desk_http.json()["response"] != "ok manito"


def test_use_chat_keeps_dashboard_channel_and_sends_usage_source():
    text = Path(__file__).resolve().parents[2].joinpath(
        "empire-command-center/app/hooks/useChat.ts"
    ).read_text(encoding="utf-8")
    assert "channel: 'dashboard'" in text
    assert "usage_source: usageSource || 'web'" in text
    assert "channel || 'web'" not in text


def test_concurrent_desk_during_web_chat_does_not_race(monkeypatch, tmp_path):
    """A desk call mid-web-chat must not steal the web ContextVar (or vice versa)."""
    import asyncio

    _env(monkeypatch, tmp_path)
    monkeypatch.setenv("MINIMAX_METER_DIR", str(tmp_path / "meter"))
    monkeypatch.setenv("MINIMAX_REMAINS_STUB", "ok")
    monkeypatch.setenv("MINIMAX_REMAINS_PROBE", "0")
    monkeypatch.setenv("MINIMAX_TEXT_POOL_FLOOR", "1000")
    monkeypatch.setenv("MINIMAX_EDITION_TEXT_SHARE_PCT", "20")
    (tmp_path / "meter").mkdir(parents=True, exist_ok=True)

    from app.services.max.ai_router import AIMessage, _meter_ctx, ai_router, current_meter_context
    from app.services.minimax_meter import MeterBlocked

    seen: list[tuple[str, object]] = []
    barrier = asyncio.Barrier(2)

    def _try_reserve(text: str) -> tuple[bool, str]:
        try:
            reservation = ai_router._reserve_minimax_text(
                [AIMessage(role="user", content=text)]
            )
            return (not reservation.blocked, reservation.message or "")
        except MeterBlocked as exc:
            return (False, exc.message)

    async def web_chat():
        token = _meter_ctx.set(("web", None))
        try:
            await barrier.wait()
            await asyncio.sleep(0)
            seen.append(("web", current_meter_context()))
            allowed, message = _try_reserve("hola manito")
            seen.append(("web-reserve", (allowed, message)))
        finally:
            _meter_ctx.reset(token)

    async def desk_call():
        token = _meter_ctx.set(("", "finance"))
        try:
            await barrier.wait()
            await asyncio.sleep(0)
            seen.append(("desk", current_meter_context()))
            allowed, message = _try_reserve("audit books")
            seen.append(("desk-reserve", (not allowed, message)))
        finally:
            _meter_ctx.reset(token)

    _set_used(250)
    _write_signal(tmp_path, overage_allowed=True, founder_active=False)
    from app.services.minimax_meter import record
    record(kind="text", edition="amp", model="MiniMax-M3", input_tokens=250, output_tokens=0)

    async def _run():
        await asyncio.gather(web_chat(), desk_call())

    asyncio.run(_run())
    ctxs = {label: value for label, value in seen if label in {"web", "desk"}}
    assert ctxs["web"] == ("web", None)
    assert ctxs["desk"] == ("", "finance")
    assert getattr(ai_router, "_meter_source", None) in (None, "")
    web_ok, _web_msg = next(v for label, v in seen if label == "web-reserve")
    desk_blocked, _desk_msg = next(v for label, v in seen if label == "desk-reserve")
    assert web_ok is True
    assert desk_blocked is True


def test_minimax_chat_bypass_inside_chat_context_is_refused(monkeypatch, tmp_path):
    """_minimax_chat without a set ContextVar is background, even if leftover attrs say web."""
    _env(monkeypatch, tmp_path)
    _set_used(250)
    _write_signal(tmp_path, overage_allowed=True, founder_active=False)
    monkeypatch.setenv("MINIMAX_METER_DIR", str(tmp_path / "meter"))
    monkeypatch.setenv("MINIMAX_REMAINS_STUB", "ok")
    monkeypatch.setenv("MINIMAX_REMAINS_PROBE", "0")
    monkeypatch.setenv("MINIMAX_TEXT_POOL_FLOOR", "1000")
    monkeypatch.setenv("MINIMAX_EDITION_TEXT_SHARE_PCT", "20")
    (tmp_path / "meter").mkdir(parents=True, exist_ok=True)
    from app.services.minimax_meter import record
    record(kind="text", edition="amp", model="MiniMax-M3", input_tokens=250, output_tokens=0)

    from app.services.max.ai_router import AIMessage, _meter_ctx, ai_router, current_meter_context
    from app.services.minimax_meter import MeterBlocked

    # Leftover instance attrs from the old shared-object design must not grant overage.
    ai_router._meter_source = "web"
    ai_router._meter_desk = None
    assert current_meter_context() == ("", None)

    with pytest.raises(MeterBlocked):
        ai_router._reserve_minimax_text(
            [AIMessage(role="user", content="bypass spend")]
        )

    # Inside a real chat() context the same leftover attrs are ignored; ContextVar wins.
    token = _meter_ctx.set(("web", None))
    try:
        assert current_meter_context() == ("web", None)
        ok = ai_router._reserve_minimax_text(
            [AIMessage(role="user", content="typed chat")]
        )
        assert ok.blocked is False
        # A nested bypass that clears the ContextVar is refused again.
        _meter_ctx.reset(token)
        token = None
        with pytest.raises(MeterBlocked):
            ai_router._reserve_minimax_text(
                [AIMessage(role="user", content="bypass after reset")]
            )
    finally:
        if token is not None:
            _meter_ctx.reset(token)

    async def _call_minimax():
        try:
            await ai_router._minimax_chat([AIMessage(role="user", content="direct bypass")])
        except MeterBlocked:
            return "refused"
        except Exception as exc:
            return f"other:{type(exc).__name__}"
        return "allowed"

    import asyncio
    assert asyncio.run(_call_minimax()) == "refused"


def test_dashboard_stream_still_shows_pin_card(monkeypatch, tmp_path):
    """Dashboard stream is not founder (same as base); PIN card is emitted."""
    from app.services.max.guardrails import is_founder_message

    assert is_founder_message({"channel": "dashboard"}) is False
    assert is_founder_message({"channel": "web"}) is True
    assert is_founder_message({"channel": "web_cc"}) is True

    monkeypatch.setenv("FOUNDER_PIN", "918273")
    monkeypatch.setattr("app.services.max.tool_executor.FOUNDER_PIN", "918273")
    _env(monkeypatch, tmp_path)

    from app.services.max.ai_router import ai_router

    async def fake_stream(
        messages, model=None, image_filename=None, desk=None, system_prompt=None,
        tenant_id="founder", source="", conversation_id="",
    ):
        yield (
            "```tool\n"
            '{"tool": "shell_execute", "command": "pwd"}\n'
            "```",
            "MiniMax-M3",
        )

    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers.max.router import router

    monkeypatch.setattr(ai_router, "chat_stream", fake_stream)

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    stream = client.post(
        "/api/v1/max/chat/stream",
        json={
            "message": "run pwd on the server",
            "channel": "dashboard",
            "usage_source": "web",
        },
    )
    assert stream.status_code == 200, stream.text
    assert "pin_required" in stream.text
    assert "resume_id" in stream.text
    # usage_source must not flip privileges: web stream would be founder on /chat,
    # but this path is /stream with channel=dashboard.
    web_as_channel = client.post(
        "/api/v1/max/chat/stream",
        json={"message": "run pwd on the server", "channel": "web"},
    )
    assert web_as_channel.status_code == 200
    # Base: dashboard asks for the card. Do not require web-as-channel to skip it
    # (PIN gate runs for founder too); just prove dashboard still emits it.
