import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.channels import status as channel_status
from app.services.max import gmail_reader
from app.services.max.email_sender_whitelist import authorize_email_sender, sender_whitelist_status
from app.services.max.unified_message_store import UnifiedMessageStore


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


def test_email_sender_whitelist_allows_founder_address(monkeypatch):
    monkeypatch.setenv("MAX_EMAIL_ALLOWED_SENDERS", "empirebox2026@gmail.com,rafa22giraldo@gmail.com")

    authorization = authorize_email_sender("empirebox2026@gmail.com")

    assert authorization["sender_authorized"] is True
    assert authorization["blocked_reason"] is None
    assert authorization["allowed_sender_count"] == 2


def test_email_sender_whitelist_allows_display_name_sender(monkeypatch):
    monkeypatch.setenv("MAX_EMAIL_ALLOWED_SENDERS", "empirebox2026@gmail.com,rafa22giraldo@gmail.com")

    authorization = authorize_email_sender("Rafael Giraldo <rafa22giraldo@gmail.com>")

    assert authorization["sender_authorized"] is True
    assert authorization["sender_address"] == "rafa22giraldo@gmail.com"


def test_email_sender_whitelist_is_case_insensitive(monkeypatch):
    monkeypatch.setenv("MAX_EMAIL_ALLOWED_SENDERS", "empirebox2026@gmail.com,rafa22giraldo@gmail.com")

    authorization = authorize_email_sender("RAFA22GIRALDO@GMAIL.COM")

    assert authorization["sender_authorized"] is True


def test_email_sender_whitelist_blocks_non_founder_sender(monkeypatch):
    monkeypatch.setenv("MAX_EMAIL_ALLOWED_SENDERS", "empirebox2026@gmail.com,rafa22giraldo@gmail.com")

    authorization = authorize_email_sender("Discord <noreply@discord.com>")

    assert authorization["sender_authorized"] is False
    assert authorization["blocked_reason"] == "non_whitelisted_sender"


def test_missing_email_sender_whitelist_blocks_live_reply(monkeypatch):
    monkeypatch.delenv("MAX_EMAIL_ALLOWED_SENDERS", raising=False)

    authorization = authorize_email_sender("empirebox2026@gmail.com")
    status = sender_whitelist_status()

    assert status["email_sender_whitelist_configured"] is False
    assert status["allowed_sender_count"] == 0
    assert authorization["sender_authorized"] is False
    assert authorization["blocked_reason"] == "sender_whitelist_missing"


def test_email_dns_layer_is_separate_from_backend_gmail_status(monkeypatch, tmp_path):
    monkeypatch.delenv("GMAIL_TOKEN_PATH", raising=False)
    monkeypatch.delenv("GMAIL_CREDENTIALS_PATH", raising=False)
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
    monkeypatch.delenv("GMAIL_TOKEN_PATH", raising=False)
    monkeypatch.delenv("GMAIL_CREDENTIALS_PATH", raising=False)
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
    assert paths["token_path_configurable"] is True
    assert paths["token_path_source"] == "canonical backend token.json"
    assert paths["legacy_token_auto_used"] is False
    assert paths["token_contents_read"] is False
    assert layer["status"] == "verified_broken"
    assert layer["last_error_category"] == "gmail_token_missing"


def test_gmail_token_paths_are_runtime_configurable_without_reading_secrets(monkeypatch, tmp_path):
    token_path = tmp_path / "runtime-token.json"
    credentials_path = tmp_path / "runtime-credentials.json"
    token_path.write_text("token-secret-that-must-not-appear")
    credentials_path.write_text("credential-secret-that-must-not-appear")
    monkeypatch.setenv("GMAIL_TOKEN_PATH", str(token_path))
    monkeypatch.setenv("GMAIL_CREDENTIALS_PATH", str(credentials_path))
    monkeypatch.setattr(channel_status, "CANONICAL_BACKEND", tmp_path / "main" / "backend")
    monkeypatch.setattr(channel_status, "LEGACY_BACKEND", tmp_path / "legacy" / "backend")

    paths = channel_status._gmail_paths()
    layer = channel_status._gmail_reader_status(paths)
    rendered = json.dumps({"paths": paths, "layer": layer})

    assert paths["token_path_configurable"] is True
    assert paths["token_env_configured"] is True
    assert paths["credentials_env_configured"] is True
    assert paths["configured_token_exists"] is True
    assert paths["configured_credentials_exists"] is True
    assert paths["legacy_token_auto_used"] is False
    assert paths["token_contents_read"] is False
    assert layer["status"] == "unverified"
    assert "token-secret-that-must-not-appear" not in rendered
    assert "credential-secret-that-must-not-appear" not in rendered


def test_gmail_reader_uses_runtime_oauth_path_env_names(monkeypatch, tmp_path):
    token_path = tmp_path / "token.json"
    credentials_path = tmp_path / "credentials.json"
    token_path.write_text("token-content-not-read")
    credentials_path.write_text("credential-content-not-read")
    monkeypatch.setenv("GMAIL_TOKEN_PATH", str(token_path))
    monkeypatch.setenv("GMAIL_CREDENTIALS_PATH", str(credentials_path))

    paths = gmail_reader.get_oauth_paths()
    rendered = json.dumps(paths, default=str)

    assert paths["token_path"] == token_path
    assert paths["credentials_path"] == credentials_path
    assert paths["token_path_source"] == "GMAIL_TOKEN_PATH"
    assert paths["credentials_path_source"] == "GMAIL_CREDENTIALS_PATH"
    assert paths["token_exists"] is True
    assert paths["credentials_exists"] is True
    assert "token-content-not-read" not in rendered
    assert "credential-content-not-read" not in rendered


def test_missing_sendgrid_smtp_returns_broken_outbound(monkeypatch):
    for name in ("SENDGRID_API_KEY", "SENDGRID_FROM_EMAIL", "SMTP_USER", "SMTP_PASSWORD", "SMTP_HOST", "SMTP_FROM"):
        monkeypatch.delenv(name, raising=False)

    outbound = channel_status._outbound_email_config()

    assert outbound["sendgrid_configured"] is False
    assert outbound["sendgrid_from_configured"] is False
    assert outbound["smtp_configured_for_max"] is False
    assert outbound["max_from_identity_configured"] is False
    assert outbound["max_email_configured"] is False


def test_sendgrid_configured_does_not_mark_live_outbound_verified(monkeypatch):
    monkeypatch.setenv("SENDGRID_API_KEY", "SG.secret-value-that-must-not-leak")
    monkeypatch.setenv("SENDGRID_FROM_EMAIL", "max@empirebox.store")
    for name in ("SMTP_USER", "SMTP_PASSWORD", "SMTP_HOST", "SMTP_FROM"):
        monkeypatch.delenv(name, raising=False)

    outbound = channel_status._outbound_email_config()
    email_channel, layers = channel_status._email_status()
    outbound_layer = next(layer for layer in layers if layer["name"] == "sendgrid_smtp_outbound")

    assert outbound["sendgrid_configured"] is True
    assert outbound["sendgrid_from_configured"] is True
    assert outbound["max_from_identity_configured"] is True
    assert outbound["max_email_configured"] is True
    assert outbound_layer["status"] == "partial"
    assert email_channel["outbound_configured"] is True
    assert email_channel["outbound_verified"] is False


def test_webhook_only_intake_does_not_mark_reply_loop_working(monkeypatch, tmp_path):
    monkeypatch.delenv("GMAIL_TOKEN_PATH", raising=False)
    monkeypatch.delenv("GMAIL_CREDENTIALS_PATH", raising=False)
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
    monkeypatch.setenv("MAX_EMAIL_ALLOWED_SENDERS", "empirebox2026@gmail.com,rafa22giraldo@gmail.com")

    data = channel_status.build_channel_status()
    rendered = json.dumps(data)

    assert "SG.secret-value-that-must-not-leak" not in rendered
    assert "smtp-password-that-must-not-leak" not in rendered
    assert "telegram-token-that-must-not-leak" not in rendered
    assert "empirebox2026@gmail.com" not in rendered
    assert "rafa22giraldo@gmail.com" not in rendered
    assert data["safety"]["secrets_included"] is False


def test_channel_status_reports_whitelist_without_exposing_addresses(monkeypatch):
    monkeypatch.setenv("MAX_EMAIL_ALLOWED_SENDERS", "empirebox2026@gmail.com,rafa22giraldo@gmail.com")

    data = channel_status.build_channel_status()
    email = next(channel for channel in data["channels"] if channel["key"] == "email")
    rendered = json.dumps(data)

    assert email["email_sender_whitelist_configured"] is True
    assert email["allowed_sender_count"] == 2
    assert _layer(data, "sender_whitelist_gate")["status"] == "partial"
    assert "empirebox2026@gmail.com" not in rendered
    assert "rafa22giraldo@gmail.com" not in rendered


def test_channel_dry_run_does_not_send_live_messages(monkeypatch):
    monkeypatch.setenv("MAX_EMAIL_ALLOWED_SENDERS", "empirebox2026@gmail.com,rafa22giraldo@gmail.com")
    res = client.post(
        "/api/v1/channels/test/dry-run",
        json={
            "channel": "email",
            "payload": {
                "from": "Empire Founder <empirebox2026@gmail.com>",
                "subject": "Question",
                "body": "Can MAX see this?",
            },
        },
    )

    assert res.status_code == 200
    data = res.json()
    assert data["dry_run"] is True
    assert data["live_send_performed"] is False
    assert data["sender_authorized"] is True
    assert data["blocked_reason"] is None
    assert data["reply_payload_preview"]["would_send"] is False
    assert data["max_request_payload"]["channel"] == "email"


def test_channel_dry_run_reports_blocked_sender(monkeypatch):
    monkeypatch.setenv("MAX_EMAIL_ALLOWED_SENDERS", "empirebox2026@gmail.com,rafa22giraldo@gmail.com")

    res = client.post(
        "/api/v1/channels/test/dry-run",
        json={
            "channel": "email",
            "payload": {
                "from": "Discord <noreply@discord.com>",
                "subject": "Discord notification",
                "body": "This should not go to MAX.",
            },
        },
    )

    assert res.status_code == 200
    data = res.json()
    assert data["dry_run"] is True
    assert data["live_send_performed"] is False
    assert data["sender_authorized"] is False
    assert data["blocked_reason"] == "non_whitelisted_sender"
    assert data["max_request_payload"] is None
    assert data["reply_payload_preview"]["would_send"] is False
    assert data["reply_payload_preview"]["blocked"] is True


def test_email_webhook_blocks_non_whitelisted_sender(monkeypatch, tmp_path):
    monkeypatch.setenv("MAX_EMAIL_ALLOWED_SENDERS", "empirebox2026@gmail.com,rafa22giraldo@gmail.com")
    store = UnifiedMessageStore(tmp_path / "unified_messages.db")
    monkeypatch.setattr("app.services.max.unified_message_store.unified_store", store)

    res = client.post(
        "/webhooks/email/inbound",
        json={
            "from": "Discord <noreply@discord.com>",
            "to": "max@empirebox.store",
            "subject": "Discord notification",
            "text": "This should be ignored by MAX.",
            "message_id": "discord-msg-1",
        },
    )

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "blocked"
    assert data["sender_authorized"] is False
    assert data["blocked_reason"] == "non_whitelisted_sender"

    rows = store.list_memory_bank(channel="email", limit=10)
    assert len(rows) == 1
    assert rows[0]["direction"] == "ignored"
    assert rows[0]["role"] == "system"
    assert rows[0]["founder_verified"] is False
    assert rows[0]["metadata"]["blocked_reason"] == "non_whitelisted_sender"
    assert "This should be ignored by MAX." not in rows[0]["body"]


def test_legacy_token_path_detected_but_not_auto_used(monkeypatch, tmp_path):
    monkeypatch.delenv("GMAIL_TOKEN_PATH", raising=False)
    monkeypatch.delenv("GMAIL_CREDENTIALS_PATH", raising=False)
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
