"""8a — Rafael-aware soft 20% cap. Tmp EMPIRE_DATA_DIR only."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.instance_usage import (
    MENSAJE_OVERAGE,
    MENSAJE_PAUSED,
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
    assert enforce_usage_cap(text="hola manito") is None
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
    assert summary["message"] == MENSAJE_PAUSED
    assert enforce_usage_cap(text="hola") == MENSAJE_PAUSED
    assert family_overage_allowed() is False

    stale = (datetime.now(timezone.utc) - timedelta(seconds=400)).strftime("%Y-%m-%dT%H:%M:%SZ")
    _write_signal(tmp_path, overage_allowed=True, updated_at=stale)
    assert usage_summary()["level"] == "paused"
    assert enforce_usage_cap(text="hola") == MENSAJE_PAUSED

    _write_signal(tmp_path, raw="{not json")
    assert usage_summary()["level"] == "paused"

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
    assert enforce_usage_cap(text="hola") == MENSAJE_PAUSED
    assert enforce_usage_cap(kind="desk_task", source="scheduler") == MENSAJE_PAUSED


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
    blocked = check(kind="text", edition="amp", input_tokens=1)
    assert blocked
    _write_signal(tmp_path, overage_allowed=True, founder_active=False)
    assert check(kind="text", edition="amp", input_tokens=1) is None
    _write_signal(tmp_path, overage_allowed=False, founder_active=True, reason="founder_active")
    assert check(kind="text", edition="amp", input_tokens=1)
