"""Fix C: avatar is part of the health check. No live writes."""
from app.services.max.desks.live_services import (
    LIVE_SERVICES,
    avatar_service_status,
    check_live_services,
)


def test_live_services_includes_avatar_module():
    row = next(s for s in LIVE_SERVICES if s["id"] == "avatar")
    assert row["kind"] == "module"
    assert row["module"] == "app.routers.avatar"


def test_check_live_services_reports_avatar():
    rows = check_live_services(
        port_checker=lambda p: True,
        container_checker=lambda n: False,
        systemd_checker=lambda n: True,
        process_checker=lambda n: True,
        disk_checker=lambda p="/": {"id": "disk", "name": "disk", "up": True, "pct": 10, "detail": "ok"},
        module_checker=lambda n: n == "app.routers.avatar",
    )
    by_id = {r["id"]: r for r in rows}
    assert by_id["avatar"]["up"] is True
    assert "module" in by_id["avatar"]["detail"]


def test_avatar_service_status_is_online():
    row = avatar_service_status()
    assert row["status"] == "online"
    assert row["description"].lower().startswith("avatar")


def test_system_health_payload_has_avatar_key():
    import asyncio
    from app.routers.system_monitor import system_health

    payload = asyncio.run(system_health())
    assert "Avatar" in payload["services"]
