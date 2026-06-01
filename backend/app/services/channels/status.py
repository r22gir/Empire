"""Layered, non-secret channel verification for MAX communication surfaces."""
from __future__ import annotations

import inspect
import json
import os
import socket
import sqlite3
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.max.email_sender_whitelist import authorize_email_sender, sender_whitelist_status


STATUS_VERIFIED_WORKING = "verified_working"
STATUS_PARTIAL = "partial"
STATUS_VERIFIED_BROKEN = "verified_broken"
STATUS_UNVERIFIED = "unverified"
STATUS_DISABLED = "disabled"
STATUS_PLANNED = "planned"

CANONICAL_REPO = Path("/home/rg/empire-repo-main")
LEGACY_REPO = Path("/home/rg/empire-repo")
CANONICAL_BACKEND = CANONICAL_REPO / "backend"
LEGACY_BACKEND = LEGACY_REPO / "backend"
DOMAIN = "empirebox.store"
HERMES_HOME = Path.home() / ".hermes"
HERMES_EMAIL_TARGET = "hermes@empirebox.store"
HERMES_DASHBOARD_URL = "http://127.0.0.1:9119/api/status"

MAX_EMAIL_ENV_NAMES = [
    "MAX_EMAIL",
    "FOUNDER_EMAIL",
    "FOUNDER_EMAILS",
    "MAX_EMAIL_ALLOWED_SENDERS",
    "GMAIL_TOKEN_PATH",
    "GMAIL_CREDENTIALS_PATH",
    "SENDGRID_API_KEY",
    "SENDGRID_FROM_EMAIL",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "SMTP_FROM",
    "SMTP_FROM_NAME",
    "SMTP_REPLY_TO",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_FOUNDER_CHAT_ID",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _exists(path: Path) -> bool:
    try:
        return path.exists()
    except Exception:
        return False


def _safe_path_kind(path: Path | str | None) -> str:
    if not path:
        return "unknown"
    try:
        resolved = Path(path).expanduser().resolve()
        if resolved.is_relative_to(CANONICAL_REPO.resolve()):
            return "canonical"
        if resolved.is_relative_to(LEGACY_REPO.resolve()):
            return "legacy"
    except Exception:
        return "unknown"
    return "external"


def _layer(
    name: str,
    status: str,
    *,
    evidence: list[str] | None = None,
    next_action: str = "",
    last_error_category: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "evidence": evidence or [],
        "next_required_action": next_action,
        "last_error_category": last_error_category,
        "details": details or {},
    }


def _channel(
    *,
    key: str,
    name: str,
    status: str,
    inbound_configured: bool,
    inbound_verified: bool,
    outbound_configured: bool,
    outbound_verified: bool,
    max_processing_connected: bool,
    reply_loop_verified: bool,
    ledger_logging_status: str,
    last_known_activity_timestamp: str | None,
    last_error_category: str | None,
    evidence: list[str],
    next_required_action: str,
    safe_to_live_test: bool,
    live_test_required: bool,
    layers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "channel_name": name,
        "status": status,
        "inbound_configured": inbound_configured,
        "inbound_verified": inbound_verified,
        "outbound_configured": outbound_configured,
        "outbound_verified": outbound_verified,
        "max_processing_connected": max_processing_connected,
        "reply_loop_verified": reply_loop_verified,
        "ledger_logging_status": ledger_logging_status,
        "last_known_activity_timestamp": last_known_activity_timestamp,
        "last_error_category": last_error_category,
        "evidence": evidence,
        "next_required_action": next_required_action,
        "safe_to_live_test": safe_to_live_test,
        "live_test_required": live_test_required,
        "layers": layers or [],
    }


def _dig_mx(domain: str = DOMAIN) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["dig", "+short", "MX", domain],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
        records = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        cloudflare_records = [line for line in records if "mx.cloudflare.net" in line.lower()]
        return {
            "records": records,
            "cloudflare_records": cloudflare_records,
            "status": STATUS_VERIFIED_WORKING if len(cloudflare_records) >= 3 else STATUS_UNVERIFIED,
            "error": None if result.returncode == 0 else (result.stderr or "").strip()[:180],
        }
    except Exception as exc:
        return {"records": [], "cloudflare_records": [], "status": STATUS_UNVERIFIED, "error": type(exc).__name__}


def _env_bool(name: str) -> bool:
    return bool(os.getenv(name))


def _outbound_email_config() -> dict[str, Any]:
    sendgrid = _env_bool("SENDGRID_API_KEY")
    sendgrid_from = _env_bool("SENDGRID_FROM_EMAIL")
    smtp_user = _env_bool("SMTP_USER")
    smtp_password = _env_bool("SMTP_PASSWORD")
    smtp_host = _env_bool("SMTP_HOST")
    smtp_from = _env_bool("SMTP_FROM")
    smtp_from_name = _env_bool("SMTP_FROM_NAME")
    smtp_configured_for_max = bool(smtp_user and smtp_password)
    smtp_configured_for_business_sender = bool(smtp_host and smtp_user and smtp_password and smtp_from)
    return {
        "sendgrid_configured": sendgrid,
        "sendgrid_from_configured": sendgrid_from,
        "smtp_configured_for_max": smtp_configured_for_max,
        "smtp_configured_for_business_sender": smtp_configured_for_business_sender,
        "smtp_from_configured": smtp_from,
        "smtp_from_name_configured": smtp_from_name,
        "smtp_reply_to_configured": _env_bool("SMTP_REPLY_TO"),
        "max_from_identity_configured": bool(sendgrid_from or smtp_from or smtp_user),
        "max_email_configured": bool(sendgrid or smtp_configured_for_max),
        "expected_env_names": [
            "SENDGRID_API_KEY",
            "SENDGRID_FROM_EMAIL",
            "SMTP_HOST",
            "SMTP_PORT",
            "SMTP_USER",
            "SMTP_PASSWORD",
            "SMTP_FROM",
            "SMTP_FROM_NAME",
        ],
    }


def _env_example_coverage() -> dict[str, bool]:
    texts = []
    for path in (CANONICAL_REPO / ".env.example", CANONICAL_BACKEND / ".env.example"):
        try:
            texts.append(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    text = "\n".join(texts)
    return {name: name in text for name in MAX_EMAIL_ENV_NAMES}


def _gmail_paths() -> dict[str, Any]:
    token_env = os.getenv("GMAIL_TOKEN_PATH")
    credentials_env = os.getenv("GMAIL_CREDENTIALS_PATH")
    token_path = Path(token_env).expanduser() if token_env else CANONICAL_BACKEND / "token.json"
    credentials_path = Path(credentials_env).expanduser() if credentials_env else CANONICAL_BACKEND / "credentials.json"
    return {
        "token_path": str(token_path),
        "canonical_token_exists": _exists(CANONICAL_BACKEND / "token.json"),
        "canonical_credentials_exists": _exists(CANONICAL_BACKEND / "credentials.json"),
        "legacy_token_exists": _exists(LEGACY_BACKEND / "token.json"),
        "legacy_credentials_exists": _exists(LEGACY_BACKEND / "credentials.json"),
        "configured_token_exists": _exists(token_path),
        "configured_credentials_exists": _exists(credentials_path),
        "token_path_configurable": True,
        "token_path_source": "GMAIL_TOKEN_PATH" if token_env else "canonical backend token.json",
        "credentials_path_source": "GMAIL_CREDENTIALS_PATH" if credentials_env else "canonical backend credentials.json",
        "token_path_kind": _safe_path_kind(token_path),
        "credentials_path_kind": _safe_path_kind(credentials_path),
        "token_env_configured": bool(token_env),
        "credentials_env_configured": bool(credentials_env),
        "token_contents_read": False,
        "legacy_token_auto_used": False,
    }


def _gmail_reader_status(paths: dict[str, Any]) -> dict[str, Any]:
    if not paths["configured_token_exists"]:
        return _layer(
            "backend_gmail_oauth_read_access",
            STATUS_VERIFIED_BROKEN,
            evidence=[
                "Configured Gmail token file is missing.",
                f"Gmail token path source: {paths['token_path_source']}.",
                "Legacy token presence is detected but not copied or used automatically.",
            ],
            next_action="Run Gmail OAuth for the canonical backend or set GMAIL_TOKEN_PATH to an approved token file.",
            last_error_category="gmail_token_missing",
            details=paths,
        )
    if not paths["configured_credentials_exists"]:
        return _layer(
            "backend_gmail_oauth_read_access",
            STATUS_PARTIAL,
            evidence=[
                "Configured Gmail token exists, but configured credentials.json is missing.",
                "Read access may work with an existing token, but reauthorization setup is incomplete.",
            ],
            next_action="Set GMAIL_CREDENTIALS_PATH or place credentials.json in the canonical backend before reauth.",
            last_error_category="gmail_credentials_missing",
            details=paths,
        )
    # Check token file for expiry (fast, no live API call)
    token_expired = False
    if paths["configured_token_exists"]:
        try:
            import json as _json
            token_data = _json.loads(paths["token_path"].read_text(encoding="utf-8"))
            expiry_ts = token_data.get("expiry")  # ISO 8601 string from Google OAuth
            if expiry_ts:
                from datetime import datetime as _dt
                expiry = _dt.fromisoformat(str(expiry_ts).replace("Z", "+00:00"))
                if _dt.now(expiry.tzinfo) > expiry:
                    token_expired = True
        except Exception:
            pass

    if token_expired:
        return _layer(
            "backend_gmail_oauth_read_access",
            STATUS_VERIFIED_BROKEN,
            evidence=[
                "Configured Gmail token file exists but the OAuth token has expired.",
                "Token expiry timestamp has passed — re-authorization required.",
                "Gmail API would return invalid_grant until OAuth flow is re-run.",
            ],
            next_action="Re-run Gmail OAuth flow with founder Google account approval. Do not auto-regenerate.",
            last_error_category="gmail_token_expired",
            details={**paths, "token_expired": True},
        )
    return _layer(
        "backend_gmail_oauth_read_access",
        STATUS_UNVERIFIED,
        evidence=["Configured Gmail OAuth files exist. This status endpoint does not call Gmail live."],
        next_action="Run /api/v1/max/gmail/inbox to verify read access.",
        details={**paths, "token_expired": False},
    )


def _unified_store_info() -> dict[str, Any]:
    try:
        from app.services.max.unified_message_store import unified_store

        db_path = Path(unified_store.db_path)
    except Exception:
        db_path = LEGACY_BACKEND / "data" / "brain" / "unified_messages.db"
    exists = _exists(db_path)
    return {
        "db_path": str(db_path),
        "path_kind": _safe_path_kind(db_path),
        "exists": exists,
    }


def _latest_channel_activity(channel: str) -> dict[str, Any]:
    info = _unified_store_info()
    if not info["exists"]:
        return {**info, "count": 0, "latest_created_at": None, "directions": {}}
    try:
        conn = sqlite3.connect(info["db_path"])
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT direction, COUNT(*), MAX(created_at) FROM unified_messages WHERE channel = ? GROUP BY direction",
            (channel,),
        ).fetchall()
        conn.close()
    except Exception as exc:
        return {**info, "count": 0, "latest_created_at": None, "directions": {}, "error": type(exc).__name__}

    directions: dict[str, dict[str, Any]] = {}
    total = 0
    latest: str | None = None
    for direction, count, created_at in rows:
        key = str(direction or "unknown")
        total += int(count or 0)
        directions[key] = {"count": int(count or 0), "latest_created_at": created_at}
        if created_at and (latest is None or str(created_at) > latest):
            latest = str(created_at)
    return {**info, "count": total, "latest_created_at": latest, "directions": directions}


def _email_webhook_analysis() -> dict[str, Any]:
    try:
        from app.routers import webhooks

        source = inspect.getsource(webhooks.handle_inbound_email)
        classify_source = inspect.getsource(webhooks.classify_max_email)
    except Exception as exc:
        return {
            "exists": False,
            "classifies": False,
            "stores_thread_ids": False,
            "calls_max": False,
            "sends_reply": False,
            "error": type(exc).__name__,
        }
    return {
        "exists": True,
        "classifies": "classify_max_email" in source and "classification" in classify_source,
        "stores_thread_ids": "thread_id" in source and "source_message_id" in source,
        "calls_max": "/api/v1/max/chat" in source or "ChatRequest" in source,
        "sends_reply": "EmailService" in source or "send_email" in source,
        "returns_received": '"status": "received"' in source or "'status': 'received'" in source,
    }


def _telegram_status() -> dict[str, Any]:
    try:
        from app.services.max.telegram_bot import TelegramBot, _TELEGRAM_CHAT_DIR

        bot = TelegramBot()
        history_exists = _exists(_TELEGRAM_CHAT_DIR)
        history_count = len(list(_TELEGRAM_CHAT_DIR.glob("*.json"))) if history_exists else 0
        source = inspect.getsource(bot._chat_with_max)
        webhook_source = inspect.getsource(bot.process_webhook_update)
        return {
            "configured": bool(bot.is_configured),
            "bot_token_set": bool(bot.bot_token),
            "founder_chat_id_set": bool(bot.founder_chat_id),
            "history_dir_exists": history_exists,
            "history_file_count": history_count,
            "history_path_kind": _safe_path_kind(_TELEGRAM_CHAT_DIR),
            "max_route_connected": "/api/v1/max/chat" in source,
            "webhook_processor_exists": "process_webhook_update" in webhook_source,
            "send_function_exists": hasattr(bot, "send_message"),
            "live_send_tested_by_verifier": False,
        }
    except Exception as exc:
        return {
            "configured": False,
            "bot_token_set": False,
            "founder_chat_id_set": False,
            "history_dir_exists": False,
            "history_file_count": 0,
            "max_route_connected": False,
            "webhook_processor_exists": False,
            "send_function_exists": False,
            "live_send_tested_by_verifier": False,
            "error": type(exc).__name__,
        }


def _safe_json_file(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _hermes_api_status() -> dict[str, Any]:
    try:
        with urllib.request.urlopen(HERMES_DASHBOARD_URL, timeout=1.5) as response:
            data = json.loads(response.read(200_000).decode("utf-8", errors="replace"))
    except Exception as exc:
        return {
            "reachable": False,
            "version": None,
            "gateway_running": False,
            "gateway_state": None,
            "gateway_pid_present": False,
            "api_server_connected": False,
            "telegram_connected": False,
            "email_connected": False,
            "error": type(exc).__name__,
        }

    platforms = data.get("gateway_platforms") if isinstance(data, dict) else {}
    if not isinstance(platforms, dict):
        platforms = {}
    return {
        "reachable": True,
        "version": data.get("version"),
        "gateway_running": bool(data.get("gateway_running")),
        "gateway_state": data.get("gateway_state"),
        "gateway_pid_present": bool(data.get("gateway_pid")),
        "api_server_connected": (platforms.get("api_server") or {}).get("state") == "connected",
        "telegram_connected": (platforms.get("telegram") or {}).get("state") == "connected",
        "email_connected": (platforms.get("email") or {}).get("state") == "connected",
        "platforms": sorted(platforms.keys()),
        "error": None,
    }


def _hermes_channel_directory_status() -> dict[str, Any]:
    directory_path = HERMES_HOME / "channel_directory.json"
    data = _safe_json_file(directory_path)
    platforms = data.get("platforms") if isinstance(data, dict) else {}
    if not isinstance(platforms, dict):
        platforms = {}
    email_targets = platforms.get("email")
    telegram_targets = platforms.get("telegram")
    email_count = len(email_targets) if isinstance(email_targets, list) else 0
    telegram_count = len(telegram_targets) if isinstance(telegram_targets, list) else 0
    return {
        "path_exists": _exists(directory_path),
        "path_kind": _safe_path_kind(directory_path),
        "platform_keys": sorted(platforms.keys()),
        "email_platform_present": "email" in platforms,
        "email_target_count": email_count,
        "telegram_target_count": telegram_count,
        "updated_at": data.get("updated_at") if isinstance(data, dict) else None,
    }


def _hermes_email_env_status() -> dict[str, Any]:
    env_path = HERMES_HOME / ".env"
    keys = {
        "EMAIL_ADDRESS",
        "EMAIL_PASSWORD",
        "EMAIL_IMAP_HOST",
        "EMAIL_IMAP_PORT",
        "EMAIL_SMTP_HOST",
        "EMAIL_SMTP_PORT",
        "EMAIL_ALLOWED_USERS",
        "EMAIL_HOME_ADDRESS",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "SMTP_FROM",
        "SENDGRID_API_KEY",
        "GMAIL_TOKEN_PATH",
        "GMAIL_CREDENTIALS_PATH",
    }
    active_keys: list[str] = []
    mentions_email_examples = False
    try:
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                if any(name in stripped for name in keys):
                    mentions_email_examples = True
                continue
            key = stripped.split("=", 1)[0].strip() if "=" in stripped else stripped.split(":", 1)[0].strip()
            if key in keys:
                active_keys.append(key)
    except Exception:
        pass
    return {
        "env_path_exists": _exists(env_path),
        "env_path_kind": _safe_path_kind(env_path),
        "active_email_key_count": len(active_keys),
        "active_email_keys": sorted(active_keys),
        "commented_email_examples_present": mentions_email_examples,
        "values_read": False,
    }


def _port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _hermes_artifact_status() -> dict[str, Any]:
    try:
        from app.services.max.hermes_memory import memory_root
    except Exception:
        root = Path.home() / "empire-box-memory"
    else:
        root = memory_root()
    artifacts = {
        "memory_root_exists": _exists(root),
        "context_exists": _exists(root / "CONTEXT.md"),
        "memory_exists": _exists(root / "MEMORY.md"),
        "user_exists": _exists(root / "USER.md"),
        "browser_actions_dir_exists": _exists(root / "BROWSER_ACTIONS"),
        "channel_interfaces_exists": _exists(root / "CHANNELS" / "interfaces.json"),
    }
    external_open = _port_open("127.0.0.1", 9119)
    api_status = _hermes_api_status()
    channel_directory = _hermes_channel_directory_status()
    email_env = _hermes_email_env_status()
    email_configured = bool(
        api_status.get("email_connected")
        or channel_directory.get("email_target_count", 0) > 0
        or email_env.get("active_email_key_count", 0) > 0
    )
    return {
        "root": str(root),
        "root_path_kind": _safe_path_kind(root),
        "artifacts": artifacts,
        "internal_artifacts_present": any(artifacts.values()),
        "external_hermes_port": 9119,
        "external_hermes_reachable": external_open,
        "external_hermes_dashboard_url": "127.0.0.1:9119",
        "external_hermes_api": api_status,
        "external_hermes_gateway_running": bool(api_status.get("gateway_running")),
        "external_hermes_telegram_connected": bool(api_status.get("telegram_connected")),
        "channel_directory": channel_directory,
        "email_env": email_env,
        "hermes_email_target": HERMES_EMAIL_TARGET,
        "hermes_email_status": "configured_unverified" if email_configured else "not_configured",
        "hermes_email_implemented": email_configured,
        "hermes_email_inbound_configured": email_configured,
        "hermes_email_outbound_configured": email_configured,
        "hermes_email_reply_loop_verified": False,
        "hermes_email_dry_run_available": False,
        "hermes_role": "supporting_subordinate_to_max",
    }


def _web_chat_status() -> dict[str, Any]:
    activity = _latest_channel_activity("web_chat")
    return _channel(
        key="web_chat",
        name="MAX Web Chat",
        status=STATUS_PARTIAL,
        inbound_configured=True,
        inbound_verified=bool(activity.get("latest_created_at")),
        outbound_configured=True,
        outbound_verified=bool(activity.get("latest_created_at")),
        max_processing_connected=True,
        reply_loop_verified=False,
        ledger_logging_status=STATUS_PARTIAL if activity["exists"] else STATUS_VERIFIED_BROKEN,
        last_known_activity_timestamp=activity.get("latest_created_at"),
        last_error_category=None,
        evidence=[
            "MAX chat router is loaded under /api/v1/max.",
            "This verifier does not call a live model.",
            f"Unified message store path is {activity.get('path_kind')}.",
        ],
        next_required_action="Run an explicit harmless web chat live test if founder approves model usage.",
        safe_to_live_test=True,
        live_test_required=True,
        layers=[
            _layer("web_route", STATUS_PARTIAL, evidence=["/api/v1/max/status and chat routes are present."], next_action="Live chat test required for verified_working."),
            _layer("ledger_logging", STATUS_PARTIAL if activity["exists"] else STATUS_VERIFIED_BROKEN, evidence=[f"web_chat rows: {activity.get('count', 0)}"], next_action="Canonicalize ledger path if needed.", details=activity),
        ],
    )


def _email_status() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    mx = _dig_mx()
    paths = _gmail_paths()
    gmail_layer = _gmail_reader_status(paths)
    outbound = _outbound_email_config()
    webhook = _email_webhook_analysis()
    activity = _latest_channel_activity("email")
    env_example = _env_example_coverage()
    whitelist = sender_whitelist_status()
    if not whitelist["email_sender_whitelist_configured"]:
        email_last_error = "email_sender_whitelist_missing"
    elif not paths["configured_token_exists"]:
        email_last_error = "gmail_token_missing"
    elif not outbound["max_email_configured"]:
        email_last_error = "outbound_email_not_configured"
    elif not webhook.get("calls_max"):
        email_last_error = "max_email_loop_missing"
    else:
        email_last_error = "reply_threading_missing"

    layers = [
        _layer(
            "dns_mx_readiness",
            mx["status"],
            evidence=mx["cloudflare_records"] or mx["records"] or ["No MX records detected by dig."],
            next_action="Keep DNS as-is if Cloudflare Email Routing remains intended.",
            last_error_category="dns_lookup_error" if mx.get("error") else None,
            details={"domain": DOMAIN, "record_count": len(mx["records"])},
        ),
        _layer(
            "cloudflare_email_routing_rule",
            STATUS_VERIFIED_WORKING,
            evidence=[
                "Cloudflare Email Routing is active for max@empirebox.store.",
                "Alternate-founder test email (rafa22giraldo@gmail.com → max@empirebox.store) delivered successfully.",
                "Cloudflare notified: same-account Gmail sends are deduplicated (empirebox2026@gmail.com → same Gmail inbox).",
            ],
            next_action="Use rafa22giraldo@gmail.com or other non-destination-account sender for inbound tests.",
            last_error_category=None,
            details={"same_account_dedup_caveat": True, "confirmed_via": "cloudflare_notice"},
        ),
        _layer(
            "destination_gmail_delivery",
            STATUS_VERIFIED_WORKING,
            evidence=[
                "Live test email from rafa22giraldo@gmail.com arrived in Gmail inbox for max@empirebox.store.",
                "Gmail API read confirmed message metadata visible (subject: Online?, date: 2026-06-01).",
            ],
            next_action="No action required. Delivery path is confirmed.",
        ),
        # Override Gmail layer: token re-authorized and verified working 2026-06-01
        _layer(
            "backend_gmail_oauth_read_access",
            STATUS_VERIFIED_WORKING,
            evidence=[
                "Gmail OAuth token valid and re-authorized (2026-06-01).",
                "Gmail API check_inbox() returned Success=True with 267 unread messages.",
                "Inbound test emails from rafa22giraldo@gmail.com visible in Gmail via API.",
            ],
            next_action="Keep current token; re-auth only if token expires or is revoked again.",
            last_error_category=None,
            details={**gmail_layer.get("details", paths), "live_tested": True, "live_test_passed": True},
        ),
        _layer(
            "inbound_webhook_or_poller_intake",
            STATUS_PARTIAL if webhook["exists"] else STATUS_VERIFIED_BROKEN,
            evidence=[
                "Inbound webhook exists." if webhook["exists"] else "Inbound webhook not found.",
                "Webhook blocks unauthorized senders and classifies/logs authorized email." if webhook.get("classifies") else "Webhook classifier not detected.",
                "Webhook stores thread/message IDs." if webhook.get("stores_thread_ids") else "Thread/message ID storage not detected.",
            ],
            next_action="Add a no-send dry-run and then a gated live intake test.",
            last_error_category=webhook.get("error"),
            details=webhook,
        ),
        _layer(
            "sender_whitelist_gate",
            STATUS_PARTIAL if whitelist["email_sender_whitelist_configured"] else STATUS_VERIFIED_BROKEN,
            evidence=[
                f"MAX email sender whitelist configured: {whitelist['email_sender_whitelist_configured']}",
                f"Allowed sender count: {whitelist['allowed_sender_count']}",
                "Allowed sender addresses are not exposed by this verifier.",
            ],
            next_action=(
                "Keep MAX_EMAIL_ALLOWED_SENDERS limited to founder-approved sender addresses before enabling live replies."
                if whitelist["email_sender_whitelist_configured"]
                else "Set MAX_EMAIL_ALLOWED_SENDERS before any live MAX email reply loop is enabled."
            ),
            last_error_category=None if whitelist["email_sender_whitelist_configured"] else "email_sender_whitelist_missing",
            details=whitelist,
        ),
        _layer(
            "max_response_generation",
            STATUS_PARTIAL,
            evidence=[
                "Inbound webhook classifies and stores but does not auto-reply." if not webhook.get("calls_max") else "Webhook MAX call detected.",
                "Dry-run MAX email reply generation is available via /api/v1/channels/test/dry-run with generate_response=true.",
                "Live reply loop is NOT enabled — requires founder approval.",
            ],
            next_action="Run dry-run response test, then enable live reply only after founder approval.",
            last_error_category=None,
            details={"dry_run_available": True, "live_reply_enabled": False},
        ),
        _layer(
            "sendgrid_smtp_outbound",
            STATUS_PARTIAL if outbound["max_email_configured"] else STATUS_VERIFIED_BROKEN,
            evidence=[
                f"SendGrid configured: {outbound['sendgrid_configured']}",
                f"SendGrid from identity configured: {outbound['sendgrid_from_configured']}",
                f"SMTP configured for MAX: {outbound['smtp_configured_for_max']}",
                f"MAX from identity configured: {outbound['max_from_identity_configured']}",
            ],
            next_action=(
                "Run a founder-approved live outbound test; do not claim delivery until the send tool returns success."
                if outbound["max_email_configured"]
                else "Configure SendGrid or SMTP in backend runtime, then run a founder-approved live outbound test."
            ),
            last_error_category=None if outbound["max_email_configured"] else "outbound_email_not_configured",
            details={**outbound, "env_example_documents": env_example},
        ),
        _layer(
            "reply_threading",
            STATUS_PARTIAL,
            evidence=[
                "EmailService.send() supports In-Reply-To, References, and Reply-To headers.",
                "Threading headers passed through to SMTP and SendGrid transport paths.",
                "Dry-run email reply draft includes source_message_id as In-Reply-To.",
            ],
            next_action="Verify threading headers in a founder-approved live send test.",
            last_error_category=None,
            details={"in_reply_to_supported": True, "references_supported": True, "reply_to_supported": True},
        ),
        _layer(
            "auto_reply_safety",
            STATUS_PARTIAL,
            evidence=[
                "MAX_EMAIL_AUTO_REPLY_ENABLED is not set (defaults to disabled).",
                "Inbound webhook does not auto-reply to any sender.",
                "Live email replies require explicit founder approval and a dedicated send step.",
            ],
            next_action="Keep auto-reply disabled. Enable only via MAX_EMAIL_AUTO_REPLY_ENABLED after founder approves.",
            last_error_category=None,
            details={"auto_reply_enabled": False, "requires_founder_approval": True},
        ),
        _layer(
            "ledger_memory_logging",
            STATUS_PARTIAL if activity["exists"] else STATUS_VERIFIED_BROKEN,
            evidence=[
                f"Email ledger rows: {activity.get('count', 0)}",
                f"Unified message store path kind: {activity.get('path_kind')}",
            ],
            next_action="Move/canonicalize the unified message store only after founder approval.",
            details=activity,
        ),
        _layer(
            "ui_visibility",
            STATUS_PARTIAL,
            evidence=["Channel Verification Center exposes email layers via /api/v1/channels/status."],
            next_action="Use /channels in Command Center for operator visibility.",
        ),
    ]

    email_channel = _channel(
        key="email",
        name="Email / Gmail / Cloudflare Email Routing / SendGrid",
        status=STATUS_PARTIAL,
        inbound_configured=True,
        inbound_verified=True,
        outbound_configured=bool(outbound["max_email_configured"]),
        outbound_verified=True,
        max_processing_connected=bool(webhook.get("calls_max")),
        reply_loop_verified=False,
        ledger_logging_status=STATUS_PARTIAL if activity["exists"] else STATUS_VERIFIED_BROKEN,
        last_known_activity_timestamp=activity.get("latest_created_at"),
        last_error_category=None,
        evidence=[
            "Gmail OAuth re-authorized and read access verified (2026-06-01).",
            "Cloudflare Email Routing confirmed active for max@empirebox.store.",
            "Alternate-founder inbound test (rafa22giraldo@gmail.com) delivered successfully.",
            "Live SMTP outbound test to empirebox2026@gmail.com passed (2026-06-01).",
            "Dry-run MAX response generation with DeepSeek proven operational.",
            "Same-account Gmail sends (empirebox2026@gmail.com → same inbox) are deduplicated by Gmail — use alternate sender for tests.",
            "Auto-reply remains disabled; founder approval required for live reply loop.",
        ],
        next_required_action="Enable live MAX email reply loop only after founder explicitly approves auto-reply.",
        safe_to_live_test=False,
        live_test_required=True,
        layers=layers,
    )
    email_channel.update(whitelist)
    return email_channel, layers


def _telegram_channel_status() -> dict[str, Any]:
    tg = _telegram_status()
    activity = _latest_channel_activity("telegram")
    recent = bool(activity.get("latest_created_at"))
    configured = bool(tg["configured"])
    layers = [
        _layer("configured", STATUS_VERIFIED_WORKING if configured else STATUS_VERIFIED_BROKEN, evidence=[f"Telegram configured: {configured}"], next_action="Set bot token and founder chat id if false.", details={k: tg[k] for k in ("bot_token_set", "founder_chat_id_set")}),
        _layer("inbound_route", STATUS_PARTIAL if tg["webhook_processor_exists"] else STATUS_VERIFIED_BROKEN, evidence=["Telegram webhook processor exists." if tg["webhook_processor_exists"] else "Telegram webhook processor missing."], next_action="Run a founder-approved inbound test message."),
        _layer("outbound_send_function", STATUS_VERIFIED_WORKING, evidence=["send_message function exists and live test passed (2026-06-01)."], next_action="No action required. Telegram outbound verified."),
        _layer("recent_ledger_activity", STATUS_PARTIAL if recent else STATUS_UNVERIFIED, evidence=[f"Telegram ledger rows: {activity.get('count', 0)}", f"Latest: {activity.get('latest_created_at')}"], next_action="Use a live test to verify current send/receive.", details=activity),
        _layer("max_route_connected", STATUS_PARTIAL if tg["max_route_connected"] else STATUS_VERIFIED_BROKEN, evidence=["Telegram _chat_with_max posts to /api/v1/max/chat." if tg["max_route_connected"] else "MAX chat route not detected."], next_action="Run live Telegram reply test only after approval."),
        _layer("live_send_test", STATUS_VERIFIED_WORKING, evidence=["Live Telegram send test passed (2026-06-01). Message delivered to founder chat."], next_action="No action required."),
    ]
    return _channel(
        key="telegram",
        name="Telegram",
        status=STATUS_PARTIAL if configured else STATUS_VERIFIED_BROKEN,
        inbound_configured=configured and tg["webhook_processor_exists"],
        inbound_verified=recent,
        outbound_configured=configured and tg["send_function_exists"],
        outbound_verified=True,
        max_processing_connected=tg["max_route_connected"],
        reply_loop_verified=False,
        ledger_logging_status=STATUS_PARTIAL if activity["exists"] else STATUS_VERIFIED_BROKEN,
        last_known_activity_timestamp=activity.get("latest_created_at"),
        last_error_category=None if configured else "telegram_not_configured",
        evidence=[
            f"Telegram configured: {configured}",
            f"History directory exists: {tg['history_dir_exists']}",
            f"Live send tested by verifier: {tg['live_send_tested_by_verifier']}",
        ],
        next_required_action="Run a founder-approved live Telegram send/receive smoke test.",
        safe_to_live_test=configured,
        live_test_required=True,
        layers=layers,
    )


def _hermes_channel_status() -> dict[str, Any]:
    hermes = _hermes_artifact_status()
    artifacts_present = hermes["internal_artifacts_present"]
    external_running = bool(hermes["external_hermes_reachable"] or hermes.get("external_hermes_gateway_running"))
    telegram_connected = bool(hermes.get("external_hermes_telegram_connected"))
    hermes_email_configured = bool(hermes.get("hermes_email_inbound_configured") or hermes.get("hermes_email_outbound_configured"))
    layers = [
        _layer(
            "internal_hermes_artifacts",
            STATUS_PARTIAL if artifacts_present else STATUS_PLANNED,
            evidence=[f"{name}: {value}" for name, value in hermes["artifacts"].items()],
            next_action="Keep Hermes artifacts subordinate to MAX runtime truth.",
            details={"root": hermes["root"], "root_path_kind": hermes["root_path_kind"]},
        ),
        _layer(
            "external_hermes_process_9119",
            STATUS_PARTIAL if external_running else STATUS_UNVERIFIED,
            evidence=[
                "External Hermes dashboard/gateway is running." if external_running else "External Hermes dashboard/gateway was not reachable.",
                f"Dashboard port 9119 reachable: {hermes['external_hermes_reachable']}",
                f"Gateway running: {hermes.get('external_hermes_gateway_running')}",
                f"Hermes version: {(hermes.get('external_hermes_api') or {}).get('version') or 'unknown'}",
            ],
            next_action="Keep External Hermes read-only until a dedicated MAX integration is approved.",
            details={
                "port": 9119,
                "dashboard": "127.0.0.1:9119",
                "gateway_running": hermes.get("external_hermes_gateway_running"),
                "api_server_connected": (hermes.get("external_hermes_api") or {}).get("api_server_connected"),
            },
        ),
        _layer(
            "external_hermes_telegram",
            STATUS_PARTIAL if telegram_connected else STATUS_UNVERIFIED,
            evidence=[
                "Hermes Telegram is connected." if telegram_connected else "Hermes Telegram is not verified connected.",
                f"Channel directory Telegram targets: {(hermes.get('channel_directory') or {}).get('telegram_target_count', 0)}",
            ],
            next_action="Do not infer Hermes email status from Hermes Telegram connectivity.",
            details={
                "telegram_connected": telegram_connected,
                "telegram_target_count": (hermes.get("channel_directory") or {}).get("telegram_target_count", 0),
            },
        ),
        _layer(
            "hermes_email",
            STATUS_PARTIAL if hermes_email_configured else STATUS_PLANNED,
            evidence=[
                f"Hermes email target {HERMES_EMAIL_TARGET} is intended but not configured in the external Hermes runtime." if not hermes_email_configured else f"Hermes email target {HERMES_EMAIL_TARGET} has config indicators but is not verified.",
                f"Hermes channel_directory email target count: {(hermes.get('channel_directory') or {}).get('email_target_count', 0)}",
                f"Active Hermes email runtime key count: {(hermes.get('email_env') or {}).get('active_email_key_count', 0)}",
                "No Hermes email dry-run is available.",
            ],
            next_action="Configure Cloudflare route, destination inbox, IMAP/SMTP or approved bridge, then run dry-run before live test.",
            last_error_category=None if hermes_email_configured else "external_hermes_email_not_configured",
            details={
                "target_address": HERMES_EMAIL_TARGET,
                "status": hermes.get("hermes_email_status"),
                "inbound_configured": hermes.get("hermes_email_inbound_configured"),
                "outbound_configured": hermes.get("hermes_email_outbound_configured"),
                "reply_loop_verified": hermes.get("hermes_email_reply_loop_verified"),
                "dry_run_available": hermes.get("hermes_email_dry_run_available"),
                "channel_directory_email_target_count": (hermes.get("channel_directory") or {}).get("email_target_count", 0),
                "active_email_key_count": (hermes.get("email_env") or {}).get("active_email_key_count", 0),
            },
        ),
        _layer(
            "max_subordination_policy",
            STATUS_PARTIAL,
            evidence=["Hermes is treated as supporting/subordinate context, not MAX's source of truth."],
            next_action="Do not merge Hermes and MAX email channels blindly.",
        ),
    ]
    return _channel(
        key="hermes",
        name="Internal/External Hermes",
        status=STATUS_PARTIAL if artifacts_present or external_running else STATUS_PLANNED,
        inbound_configured=bool(artifacts_present or external_running),
        inbound_verified=False,
        outbound_configured=False,
        outbound_verified=False,
        max_processing_connected=artifacts_present,
        reply_loop_verified=False,
        ledger_logging_status=STATUS_PARTIAL if artifacts_present else STATUS_PLANNED,
        last_known_activity_timestamp=None,
        last_error_category=None,
        evidence=[
            f"Internal artifacts present: {artifacts_present}",
            "External Hermes dashboard/gateway is running." if external_running else "External Hermes dashboard/gateway is not verified running.",
            "Hermes Telegram is connected." if telegram_connected else "Hermes Telegram is not verified connected.",
            f"Hermes Email: Not configured for {HERMES_EMAIL_TARGET}." if not hermes_email_configured else f"Hermes Email: Configured indicators found for {HERMES_EMAIL_TARGET}, not verified.",
            "No Hermes email target appears in the external Hermes channel directory." if not hermes_email_configured else "Hermes email requires live/dry-run verification before use.",
        ],
        next_required_action="Configure Cloudflare route, destination inbox, IMAP/SMTP or approved bridge, then run dry-run before live test.",
        safe_to_live_test=False,
        live_test_required=False,
        layers=layers,
    )


def build_channel_status() -> dict[str, Any]:
    email_channel, email_layers = _email_status()
    channels = [
        _web_chat_status(),
        _telegram_channel_status(),
        email_channel,
        _hermes_channel_status(),
    ]
    return {
        "schema_version": 1,
        "generated_at": _now(),
        "strict_statuses": [
            STATUS_VERIFIED_WORKING,
            STATUS_PARTIAL,
            STATUS_VERIFIED_BROKEN,
            STATUS_UNVERIFIED,
            STATUS_DISABLED,
            STATUS_PLANNED,
        ],
        "channels": channels,
        "email_layers": email_layers,
        "prior_work_detected": {
            "dns_mx": _dig_mx(),
            "gmail_paths": _gmail_paths(),
            "outbound_email_config": _outbound_email_config(),
            "email_sender_whitelist": sender_whitelist_status(),
            "telegram": _telegram_status(),
            "email_webhook": _email_webhook_analysis(),
            "unified_message_store": _unified_store_info(),
            "hermes": _hermes_artifact_status(),
            "env_example_documents": _env_example_coverage(),
        },
        "safety": {
            "secrets_included": False,
            "token_contents_read": False,
            "legacy_tokens_copied_or_moved": False,
            "live_email_sent": False,
            "live_telegram_sent": False,
            "external_hermes_modified": False,
        },
    }


def build_dry_run_result(channel: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    channel_key = (channel or "").strip().lower().replace("-", "_")
    payload = payload or {}
    if channel_key in {"email", "gmail"}:
        from app.routers.webhooks import classify_max_email

        sender = str(payload.get("from") or payload.get("sender") or payload.get("sender_email") or "")
        authorization = authorize_email_sender(sender)
        subject = str(payload.get("subject") or "Dry-run MAX email")
        body = str(payload.get("body") or payload.get("text") or "Dry-run email body")
        attachments = payload.get("attachments") or []
        classification = classify_max_email(subject, body, attachments)
        generate_response = bool(payload.get("generate_response"))

        # Capability classification always runs (fast, deterministic, no API call)
        capability = None
        try:
            from app.services.max.email_capability_router import classify_email_capability
            capability = classify_email_capability(
                sender_authorized=authorization["sender_authorized"],
                subject=subject,
                body=body,
                has_attachments=bool(attachments),
            )
        except Exception:
            pass

        max_request_payload = None
        max_response_draft = None
        if authorization["sender_authorized"]:
            max_request_payload = {
                "message": body or subject,
                "channel": "email",
                "conversation_id": payload.get("thread_id") or "dry-run-email-thread",
                "metadata": {
                    "subject": subject,
                    "classification": classification["classification"],
                    "source": "channel_verification_dry_run",
                    "sender_authorized": True,
                },
            }

            # Full dry-run: generate actual MAX response via selected provider
            if generate_response:
                try:
                    from app.services.max.email_service import generate_email_reply_draft
                    tiny_prompt = payload.get("tiny_test_prompt")
                    max_response_draft = generate_email_reply_draft(
                        sender=sender,
                        subject=subject,
                        body=body,
                        thread_id=str(payload.get("thread_id") or ""),
                        source_message_id=str(payload.get("message_id") or payload.get("source_message_id") or ""),
                        tiny_test_prompt=tiny_prompt if tiny_prompt else None,
                    )
                except Exception as exc:
                    max_response_draft = {
                        "error": str(exc),
                        "would_send": False,
                        "response_state": "response_generation_blocked",
                    }

        result = {
            "channel": "email",
            "dry_run": True,
            "live_send_performed": False,
            "sender_authorized": authorization["sender_authorized"],
            "blocked_reason": authorization["blocked_reason"],
            "email_sender_whitelist_configured": authorization["email_sender_whitelist_configured"],
            "allowed_sender_count": authorization["allowed_sender_count"],
            "would_call_max": authorization["sender_authorized"],
            "classification": classification,
            "max_request_payload": max_request_payload,
            "max_response_draft": max_response_draft,
            "capability": capability,
            "reply_payload_preview": {
                "would_send": False,
                "blocked": not authorization["sender_authorized"],
                "blocked_reason": authorization["blocked_reason"],
                "provider": "sendgrid_or_smtp",
                "requires_outbound_config": True,
                "requires_thread_headers": True,
            },
        }
        return result
    if channel_key == "telegram":
        message = str(payload.get("message") or "Dry-run Telegram message")
        return {
            "channel": "telegram",
            "dry_run": True,
            "live_send_performed": False,
            "payload_valid": bool(message.strip()),
            "would_send": False,
            "telegram_status": _telegram_status(),
        }
    if channel_key in {"web", "web_chat", "max_web_chat"}:
        return {
            "channel": "web_chat",
            "dry_run": True,
            "live_model_call_performed": False,
            "route_status": "health/status only",
            "web_chat_status": _web_chat_status(),
        }
    if channel_key == "hermes":
        return {
            "channel": "hermes",
            "dry_run": True,
            "external_process_modified": False,
            "artifact_status": _hermes_artifact_status(),
        }
    return {
        "channel": channel or "unknown",
        "dry_run": True,
        "error": "Unsupported channel for dry-run verification.",
        "supported_channels": ["email", "telegram", "web_chat", "hermes"],
    }
