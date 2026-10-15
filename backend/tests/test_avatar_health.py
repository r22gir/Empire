"""Avatar health uses /avatar/status checks and can report down."""
from app.services.max.desks.live_services import (
    LIVE_SERVICES,
    avatar_readiness,
    avatar_service_status,
    check_live_services,
)


def test_live_services_includes_avatar():
    row = next(s for s in LIVE_SERVICES if s["id"] == "avatar")
    assert row["kind"] == "avatar"
    assert row["module"] == "app.routers.avatar"


def test_avatar_reports_down_when_a_check_fails(monkeypatch):
    monkeypatch.setattr(
        "app.services.max.desks.live_services.avatar_readiness",
        lambda: {"online": False, "checks": {"simli": False, "tts": True, "stt": True, "voice": True},
                 "details": {"simli": "disabled"}},
    )
    row = avatar_service_status()
    assert row["status"] == "offline"
    rows = check_live_services(
        port_checker=lambda p: True,
        container_checker=lambda n: False,
        systemd_checker=lambda n: True,
        process_checker=lambda n: True,
        disk_checker=lambda p="/": {"id": "disk", "name": "disk", "up": True, "pct": 10, "detail": "ok"},
        module_checker=lambda n: True,
    )
    by_id = {r["id"]: r for r in rows}
    assert by_id["avatar"]["up"] is False


def test_avatar_reports_up_when_all_status_checks_pass(monkeypatch):
    monkeypatch.setattr(
        "app.services.max.desks.live_services.avatar_readiness",
        lambda: {"online": True, "checks": {"simli": True, "tts": True, "stt": True, "voice": True},
                 "details": {}},
    )
    row = avatar_service_status()
    assert row["status"] == "online"
    rows = check_live_services(
        port_checker=lambda p: True,
        container_checker=lambda n: False,
        systemd_checker=lambda n: True,
        process_checker=lambda n: True,
        disk_checker=lambda p="/": {"id": "disk", "name": "disk", "up": True, "pct": 10, "detail": "ok"},
        module_checker=lambda n: True,
    )
    by_id = {r["id"]: r for r in rows}
    assert by_id["avatar"]["up"] is True


def test_avatar_readiness_uses_simli_tts_stt_voice(monkeypatch):
    monkeypatch.setattr("app.services.max.simli_avatar.simli_status", lambda ed: {"enabled": True, "status": "enabled"})

    class _On:
        is_configured = True

    monkeypatch.setattr("app.services.max.tts_service.tts_service", _On())
    monkeypatch.setattr("app.services.max.stt_service.stt_service", _On())
    monkeypatch.setattr("app.services.max.voice_live.voice_status", lambda: {"enabled": True})
    ready = avatar_readiness()
    assert ready["online"] is True
    assert set(ready["checks"]) == {"simli", "tts", "stt", "voice"}

    monkeypatch.setattr("app.services.max.voice_live.voice_status", lambda: {"enabled": False, "reason": "no key"})
    down = avatar_readiness()
    assert down["online"] is False
    assert down["checks"]["voice"] is False


def test_system_health_payload_has_avatar_key(monkeypatch):
    import asyncio
    monkeypatch.setattr(
        "app.services.max.desks.live_services.avatar_service_status",
        lambda: {"status": "offline", "checks": {"voice": False}},
    )
    from app.routers.system_monitor import system_health

    payload = asyncio.run(system_health())
    assert "Avatar" in payload["services"]
    assert payload["services"]["Avatar"] is False
