"""Maxine soft cap: Rafael-aware overage, fail-closed signal, no absolute totals."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


def _env(monkeypatch, tmp_path, edition="maxine"):
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", "1000")
    monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")
    monkeypatch.setenv("FAMILY_ABSOLUTE_MAX_PCT", "40")
    monkeypatch.setenv("FOUNDER_SIGNAL_MAX_AGE_S", "180")
    monkeypatch.setattr("app.services.instance_usage._usage_data_roots", lambda: [tmp_path])
    monkeypatch.delenv("EMPIRE_USAGE_BASELINE_MONTHLY_USD", raising=False)


def _write_signal(
    tmp_path: Path,
    *,
    allowed=True,
    founder_active=False,
    stale=False,
    malformed=False,
    reserve_ok=None,
    reason=None,
    brother_ceiling_pct=None,
):
    folder = tmp_path / "founder-signal"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "status.json"
    if malformed:
        path.write_text("{not-json", encoding="utf-8")
        return
    now = datetime.now(timezone.utc)
    updated = now - timedelta(hours=1) if stale else now
    payload = {
        "schema": 1,
        "updated_at": updated.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "founder_active": founder_active,
        "founder_last_active_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reserve_ok": (allowed and not founder_active) if reserve_ok is None else reserve_ok,
        "overage_allowed": allowed and not founder_active,
        "reason": reason or (
            "inactive_reserve_ok" if allowed and not founder_active else "founder_active"
        ),
    }
    if brother_ceiling_pct is not None:
        payload["brother_ceiling_pct"] = brother_ceiling_pct
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_ten_percent_chat_allowed_regardless_of_signal(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.instance_usage import enforce_usage_cap, record_usage, usage_summary

    record_usage(input_tokens=100, output_tokens=0)
    assert usage_summary()["used_percent"] == 10.0
    assert usage_summary()["level"] == "ok"
    assert enforce_usage_cap(text="hola manito", kind="chat", source="web") is None
    _write_signal(tmp_path, founder_active=True, allowed=False)
    assert enforce_usage_cap(text="hola manito", kind="chat", source="web") is None


def test_twenty_five_overage_allows_chat_refuses_desk(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _write_signal(tmp_path, allowed=True, founder_active=False)
    from app.services.instance_usage import enforce_usage_cap, record_usage, usage_summary

    record_usage(input_tokens=250, output_tokens=0)
    summary = usage_summary()
    assert summary["used_percent"] == 25.0
    assert summary["level"] == "overage"
    assert summary["overage_active"] is True
    assert "tiempo extra" in summary["message"]
    assert enforce_usage_cap(text="hola", kind="chat", source="web") is None
    desk = enforce_usage_cap(text="hola", kind="desk_task", source="scheduler")
    assert desk and "automáticas" in desk


@pytest.mark.parametrize("signal", ["founder_active", "stale", "missing", "malformed"])
def test_twenty_five_paused_without_good_signal(monkeypatch, tmp_path, signal):
    _env(monkeypatch, tmp_path)
    if signal == "founder_active":
        _write_signal(tmp_path, allowed=False, founder_active=True)
    elif signal == "stale":
        _write_signal(tmp_path, allowed=True, stale=True)
    elif signal == "malformed":
        _write_signal(tmp_path, malformed=True)
    from app.services.instance_usage import enforce_usage_cap, record_usage, usage_summary

    record_usage(input_tokens=250, output_tokens=0)
    summary = usage_summary()
    assert summary["level"] == "paused"
    assert summary["overage_active"] is False
    refused = enforce_usage_cap(text="hola", kind="chat", source="web")
    assert refused and "pausa" in refused
    assert "Manito" in refused
    if signal == "founder_active":
        assert "Rafael está usando Max" in refused
    elif signal in {"stale", "missing", "malformed"}:
        assert "señal de Rafael" in refused


def test_forty_five_refused_even_if_signal_allows(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _write_signal(tmp_path, allowed=True, founder_active=False)
    from app.services.instance_usage import enforce_usage_cap, record_usage, usage_summary

    record_usage(input_tokens=450, output_tokens=0)
    summary = usage_summary()
    assert summary["used_percent"] == 45.0
    assert summary["level"] == "paused"
    refused = enforce_usage_cap(text="hola", kind="chat", source="web")
    assert refused and "tope extra" in refused
    assert "40%" in refused


def test_minimax_family_text_mirrors_soft_cap(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "maxine"))
    monkeypatch.setenv("MINIMAX_METER_DIR", str(tmp_path / "meter"))
    monkeypatch.setenv("MINIMAX_TEXT_POOL_FLOOR", "1000")
    monkeypatch.setenv("MINIMAX_EDITION_TEXT_SHARE_PCT", "20")
    monkeypatch.setenv("MINIMAX_REMAINS_PROBE", "0")
    monkeypatch.setenv("MINIMAX_REMAINS_STUB", "ok")
    monkeypatch.setenv("FAMILY_ABSOLUTE_MAX_PCT", "40")
    (tmp_path / "maxine").mkdir(parents=True)
    (tmp_path / "meter").mkdir(parents=True)
    from app.services.minimax_meter import check, record

    record(kind="text", edition="maxine", model="MiniMax-M3", input_tokens=250, output_tokens=0)
    blocked = check(kind="text", edition="maxine", input_tokens=1, source="web")
    assert blocked and "pausa" in blocked

    _write_signal(tmp_path / "maxine", allowed=True, founder_active=False)
    assert check(kind="text", edition="maxine", input_tokens=1, source="web") is None
    desk = check(kind="text", edition="maxine", input_tokens=1, source="desk_task")
    assert desk and "automáticas" in desk


def test_public_usage_hides_absolute_totals(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _write_signal(tmp_path, allowed=True)
    from app.services.instance_usage import public_usage_summary, record_usage

    record_usage(input_tokens=250, output_tokens=0)
    public = public_usage_summary()
    assert public["overage_active"] is True
    assert public["level"] == "overage"
    assert "Manito" in public["message"]
    hidden = {"baseline", "baseline_basis", "allowance", "used", "day", "month", "ratio", "tokens", "cost_usd"}
    assert hidden.isdisjoint(public)
    blob = json.dumps(public)
    assert "250" not in blob
    assert "1000" not in blob


def test_desk_chat_with_empty_source_never_gets_overage(monkeypatch, tmp_path):
    """Desk tasks call ai_router.chat(desk=..., source='') as kind=chat."""
    import asyncio

    _env(monkeypatch, tmp_path)
    _write_signal(tmp_path, allowed=True, founder_active=False)
    from app.services.instance_usage import enforce_usage_cap, record_usage
    from app.services.max.ai_router import AIMessage, AIResponse, AIRouter

    record_usage(input_tokens=250, output_tokens=0)
    assert enforce_usage_cap(kind="chat", source="web") is None
    refused = enforce_usage_cap(kind="chat", source="", desk="finance")
    assert refused and "automáticas" in refused
    empty_source = enforce_usage_cap(kind="chat", source="")
    assert empty_source and "automáticas" in empty_source

    async def fake_selected(self, **_kwargs):
        return AIResponse(content="SHOULD NOT RUN", model_used="minimax-test")

    monkeypatch.setattr(AIRouter, "_chat_via_selected_routing", fake_selected)
    router = AIRouter()
    resp = asyncio.run(
        router.chat(
            [AIMessage(role="user", content="Morning Invoice Audit")],
            desk="finance",
        )
    )
    assert resp.model_used == "usage-cap"
    assert "automáticas" in resp.content

    from app.services.minimax_meter import check, record

    monkeypatch.setenv("MINIMAX_METER_DIR", str(tmp_path / "meter"))
    monkeypatch.setenv("MINIMAX_TEXT_POOL_FLOOR", "1000")
    monkeypatch.setenv("MINIMAX_EDITION_TEXT_SHARE_PCT", "20")
    monkeypatch.setenv("MINIMAX_REMAINS_PROBE", "0")
    monkeypatch.setenv("MINIMAX_REMAINS_STUB", "ok")
    (tmp_path / "meter").mkdir(parents=True, exist_ok=True)
    record(kind="text", edition="maxine", model="MiniMax-M3", input_tokens=250, output_tokens=0)
    meter = check(kind="text", edition="maxine", input_tokens=1, source="", desk="finance")
    assert meter and "automáticas" in meter
    assert check(kind="text", edition="maxine", input_tokens=1, source="web") is None


def test_brother_ceiling_pct_lowers_env_ceiling(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _write_signal(tmp_path, allowed=True, founder_active=False, brother_ceiling_pct=30)
    from app.services.instance_usage import absolute_max_pct, enforce_usage_cap, record_usage, usage_summary

    assert absolute_max_pct() == 30.0
    record_usage(input_tokens=320, output_tokens=0)
    summary = usage_summary()
    assert summary["level"] == "paused"
    refused = enforce_usage_cap(text="hola", kind="chat", source="web")
    assert refused and "30%" in refused
    assert "tope extra" in refused


@pytest.mark.parametrize("reason", ["remains_unavailable", "remains_stale"])
def test_paused_message_names_remains_unread(monkeypatch, tmp_path, reason):
    _env(monkeypatch, tmp_path)
    _write_signal(
        tmp_path,
        allowed=False,
        founder_active=False,
        reserve_ok=False,
        reason=reason,
    )
    from app.services.instance_usage import enforce_usage_cap, record_usage, usage_summary

    record_usage(input_tokens=250, output_tokens=0)
    summary = usage_summary()
    assert summary["level"] == "paused"
    assert "saldo de Max" in summary["message"]
    assert "reserva de Rafael" not in summary["message"]
    refused = enforce_usage_cap(text="hola", kind="chat", source="web")
    assert refused and "saldo de Max" in refused
    assert "reserva de Rafael" not in refused


def test_paused_message_names_reserve_low(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _write_signal(
        tmp_path,
        allowed=False,
        founder_active=False,
        reserve_ok=False,
        reason="reserve_low",
    )
    from app.services.instance_usage import enforce_usage_cap, record_usage, usage_summary

    record_usage(input_tokens=250, output_tokens=0)
    summary = usage_summary()
    assert summary["level"] == "paused"
    assert "reserva de Rafael" in summary["message"]
    refused = enforce_usage_cap(text="hola", kind="chat", source="web")
    assert refused and "reserva de Rafael" in refused


def test_dashboard_chat_and_stream_overage_reach_reserve(monkeypatch, tmp_path):
    """Interactive dashboard chat/stream get overage; desk calls do not."""
    import asyncio

    _env(monkeypatch, tmp_path)
    _write_signal(tmp_path, allowed=True, founder_active=False)
    monkeypatch.setenv("MINIMAX_API_KEY", "sk-test-not-used")
    monkeypatch.setenv("MINIMAX_METER_DIR", str(tmp_path / "meter"))
    monkeypatch.setenv("MINIMAX_TEXT_POOL_FLOOR", "1000")
    monkeypatch.setenv("MINIMAX_EDITION_TEXT_SHARE_PCT", "20")
    monkeypatch.setenv("MINIMAX_REMAINS_PROBE", "0")
    monkeypatch.setenv("MINIMAX_REMAINS_STUB", "ok")
    monkeypatch.setenv("MAX_ALLOW_FALLBACK", "false")
    (tmp_path / "meter").mkdir(parents=True, exist_ok=True)

    from app.services.instance_usage import record_usage
    from app.services.max.ai_router import AIMessage, AIRouter
    from app.services.minimax_meter import record
    from app.services.minimax_meter import reserve as real_reserve

    record_usage(input_tokens=250, output_tokens=0)
    record(kind="text", edition="maxine", model="MiniMax-M3", input_tokens=250, output_tokens=0)

    captured = []

    def wrap_reserve(**kwargs):
        captured.append(dict(kwargs))
        return real_reserve(**kwargs)

    monkeypatch.setattr("app.services.minimax_meter.reserve", wrap_reserve)

    class _Resp:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "Claro, manito."}}]}

    async def fake_retry(fn, *a, **k):
        return _Resp()

    monkeypatch.setattr("app.services.max.minimax_retry.request_with_retry", fake_retry)

    router = AIRouter()
    msg = [AIMessage(role="user", content="Hola manito")]

    chat = asyncio.run(router.chat(msg, source="dashboard"))
    assert chat.model_used != "usage-cap"
    assert "automáticas" not in (chat.content or "")
    assert any(
        (c.get("source") or "") == "dashboard" and not c.get("desk")
        for c in captured
    )

    captured.clear()

    async def _stream():
        out = []
        async for chunk, model in router.chat_stream(msg, source="dashboard"):
            out.append((chunk, model))
        return out

    stream = asyncio.run(_stream())
    assert stream and stream[0][1] != "usage-cap"
    assert "automáticas" not in "".join(c[0] or "" for c in stream)
    assert any(
        (c.get("source") or "") == "dashboard" and not c.get("desk")
        for c in captured
    )

    captured.clear()
    desk = asyncio.run(router.chat(msg, desk="finance"))
    assert desk.model_used == "usage-cap"
    assert "automáticas" in desk.content
    assert captured == []
