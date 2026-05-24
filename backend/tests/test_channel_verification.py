import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.channels import status as channel_status


client = TestClient(app)


def _layer(data: dict, name: str) -> dict:
    for item in data["email_layers"]:
        if item["name"] == name:
            return item
    raise AssertionError(f"layer missing: {name}")


def test_channel_status_endpoint_exists():
    res = client.get("/api/v1/channels/status")

    assert res.status_code == 200
    data = res.json()
    assert data["schema_version"] == 1
    assert {channel["key"] for channel in data["channels"]} >= {"web_chat", "telegram", "email", "hermes"}
    assert data["safety"]["secrets_included"] is False


def test_email_dns_layer_is_separate_from_backend_gmail_status(monkeypatch, tmp_path):
    monkeypatch.setattr(channel_status, "CANONICAL_BACKEND", tmp_path / "main-backend")
    monkeypatch.setattr(channel_status, "LEGACY_BACKEND", tmp_path / "legacy-backend")
    monkeypatch.setattr(
        channel_status,
        "_dig_mx",
        lambda domain=channel_status.DOMAIN: {
            "records": [
                "21 route3.mx.cloudflare.net.",
                "95 route1.mx.cloudflare.net.",
                "29 route2.mx.cloudflare.net.",
            ],
            "cloudflare_records": [
                "21 route3.mx.cloudflare.net.",
                "95 route1.mx.cloudflare.net.",
                "29 route2.mx.cloudflare.net.",
            ],
            "status": channel_status.STATUS_VERIFIED_WORKING,
            "error": None,
        },
    )

    data = channel_status.build_channel_status()

    assert _layer(data, "dns_mx_readiness")["status"] == "verified_working"
    assert _layer(data, "backend_gmail_oauth_read_access")["status"] == "verified_broken"


def test_missing_canonical_gmail_token_returns_verified_broken(monkeypatch, tmp_path):
    legacy_backend = tmp_path / "legacy" / "backend"
    legacy_backend.mkdir(parents=True)
    (legacy_backend / "token.json").write_text("not-read")
    (legacy_backend / "credentials.json").write_text("not-read")
    monkeypatch.setattr(channel_status, "CANONICAL_BACKEND", tmp_path / "main" / "backend")
    monkeypatch.setattr(channel_status, "LEGACY_BACKEND", legacy_backend)

    paths = channel_status._gmail_paths()
    layer = channel_status._gmail_reader_status(paths)

    assert paths["canonical_token_exists"] is False
    assert paths["legacy_token_exists"] is True
    assert paths["legacy_token_auto_used"] is False
    assert paths["token_contents_read"] is False
    assert layer["status"] == "verified_broken"
    assert layer["last_error_category"] == "gmail_token_missing"


def test_missing_sendgrid_smtp_returns_broken_outbound(monkeypatch):
    for name in ("SENDGRID_API_KEY", "SMTP_USER", "SMTP_PASSWORD", "SMTP_HOST", "SMTP_FROM"):
        monkeypatch.delenv(name, raising=False)

    outbound = channel_status._outbound_email_config()

    assert outbound["sendgrid_configured"] is False
    assert outbound["smtp_configured_for_max"] is False
    assert outbound["max_email_configured"] is False


def test_webhook_only_intake_does_not_mark_reply_loop_working(monkeypatch, tmp_path):
    monkeypatch.setattr(channel_status, "CANONICAL_BACKEND", tmp_path / "main" / "backend")
    monkeypatch.setattr(channel_status, "LEGACY_BACKEND", tmp_path / "legacy" / "backend")

    data = channel_status.build_channel_status()
    email = next(channel for channel in data["channels"] if channel["key"] == "email")

    assert _layer(data, "inbound_webhook_or_poller_intake")["status"] in {"partial", "verified_broken"}
    assert _layer(data, "max_response_generation")["status"] == "verified_broken"
    assert email["reply_loop_verified"] is False


def test_telegram_configured_but_live_send_untested_is_partial(monkeypatch):
    monkeypatch.setattr(
        channel_status,
        "_telegram_status",
        lambda: {
            "configured": True,
            "bot_token_set": True,
            "founder_chat_id_set": True,
            "history_dir_exists": True,
            "history_file_count": 1,
            "history_path_kind": "legacy",
            "max_route_connected": True,
            "webhook_processor_exists": True,
            "send_function_exists": True,
            "live_send_tested_by_verifier": False,
        },
    )
    monkeypatch.setattr(
        channel_status,
        "_latest_channel_activity",
        lambda channel: {
            "exists": True,
            "path_kind": "legacy",
            "count": 4,
            "latest_created_at": "2026-05-23 23:59:17",
            "directions": {},
        },
    )

    telegram = channel_status._telegram_channel_status()

    assert telegram["status"] == "partial"
    assert telegram["outbound_configured"] is True
    assert telegram["outbound_verified"] is False
    assert telegram["reply_loop_verified"] is False
    assert telegram["live_test_required"] is True


def test_hermes_email_returns_planned_not_working(monkeypatch):
    monkeypatch.setattr(
        channel_status,
        "_hermes_artifact_status",
        lambda: {
            "root": "/tmp/empire-box-memory",
            "root_path_kind": "external",
            "artifacts": {
                "memory_root_exists": True,
                "context_exists": True,
                "memory_exists": True,
                "user_exists": False,
                "browser_actions_dir_exists": True,
                "channel_interfaces_exists": True,
            },
            "internal_artifacts_present": True,
            "external_hermes_port": 9119,
            "external_hermes_reachable": False,
            "hermes_email_implemented": False,
            "hermes_role": "supporting_subordinate_to_max",
        },
    )

    hermes = channel_status._hermes_channel_status()
    email_layer = next(layer for layer in hermes["layers"] if layer["name"] == "hermes_email")

    assert email_layer["status"] == "planned"
    assert hermes["reply_loop_verified"] is False
    assert hermes["outbound_verified"] is False


def test_no_secrets_appear_in_channel_status_response(monkeypatch):
    monkeypatch.setenv("SENDGRID_API_KEY", "SG.secret-value-that-must-not-leak")
    monkeypatch.setenv("SMTP_PASSWORD", "smtp-password-that-must-not-leak")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-token-that-must-not-leak")

    data = channel_status.build_channel_status()
    rendered = json.dumps(data)

    assert "SG.secret-value-that-must-not-leak" not in rendered
    assert "smtp-password-that-must-not-leak" not in rendered
    assert "telegram-token-that-must-not-leak" not in rendered
    assert data["safety"]["secrets_included"] is False


def test_channel_dry_run_does_not_send_live_messages():
    res = client.post(
        "/api/v1/channels/test/dry-run",
        json={"channel": "email", "payload": {"subject": "Question", "body": "Can MAX see this?"}},
    )

    assert res.status_code == 200
    data = res.json()
    assert data["dry_run"] is True
    assert data["live_send_performed"] is False
    assert data["reply_payload_preview"]["would_send"] is False
    assert data["max_request_payload"]["channel"] == "email"


def test_legacy_token_path_detected_but_not_auto_used(monkeypatch, tmp_path):
    canonical_backend = tmp_path / "canonical" / "backend"
    legacy_backend = tmp_path / "legacy" / "backend"
    legacy_backend.mkdir(parents=True)
    (legacy_backend / "token.json").write_text("token-would-not-be-read")
    monkeypatch.setattr(channel_status, "CANONICAL_BACKEND", canonical_backend)
    monkeypatch.setattr(channel_status, "LEGACY_BACKEND", legacy_backend)

    paths = channel_status._gmail_paths()

    assert paths["legacy_token_exists"] is True
    assert paths["canonical_token_exists"] is False
    assert paths["legacy_token_auto_used"] is False
    assert paths["token_contents_read"] is False
