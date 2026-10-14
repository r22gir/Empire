"""Family chats login gate + WhatsApp 20% usage cap. Mocks only."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


LIVE_FAMILY_ROOTS = (Path("/data/amp"), Path("/data/maxine"))
CHATS_PATHS = (
    "/api/v1/whatsapp/chats",
    "/api/v1/whatsapp/chats/search",
    "/api/v1/whatsapp/chats/573001112233/messages",
)


def _assert_not_live(path: Path) -> None:
    resolved = path.expanduser().resolve()
    for banned in LIVE_FAMILY_ROOTS:
        if resolved == banned or banned in resolved.parents:
            raise AssertionError(f"refusing live family data dir {resolved}")


def _family_env(monkeypatch, tmp_path, edition: str):
    _assert_not_live(tmp_path)
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Maxine" if edition == "maxine" else "Max-e")
    monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")
    monkeypatch.setenv("AMP_JWT_SECRET", "test-secret")
    monkeypatch.setenv("AMP_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "5551234")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "test-secret")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify-me")
    monkeypatch.setenv("WHATSAPP_OWNER_NUMBERS", "573001112233")
    monkeypatch.setenv("WHATSAPP_REPLY_MODE", "text")
    monkeypatch.setenv("VOICE_DRAFTS_DB", str(tmp_path / "voice.db"))
    monkeypatch.setenv("WHATSAPP_STATE_DB", str(tmp_path / "wa.db"))
    monkeypatch.delenv("EMPIRE_USAGE_BASELINE_MONTHLY_USD", raising=False)
    monkeypatch.delenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", raising=False)
    monkeypatch.delenv("EMPIRE_USAGE_PEER_DATA_DIRS", raising=False)
    monkeypatch.setattr("app.services.instance_usage._usage_data_roots", lambda: [tmp_path])
    from app.edition import apply_amp_process_paths

    apply_amp_process_paths()


def _chats_client(monkeypatch, tmp_path, edition: str):
    _family_env(monkeypatch, tmp_path, edition)
    from app.middleware.edition_gate import amp_access_middleware
    from app.routers.whatsapp import router

    app = FastAPI()
    app.middleware("http")(amp_access_middleware)
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def _sign(body: bytes, secret: str = "test-secret") -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return "sha256=" + digest


def _payload(text: str, message_id: str, sender: str = "573001112233") -> bytes:
    return json.dumps({
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {"phone_number_id": "5551234"},
                    "messages": [{
                        "from": sender,
                        "id": message_id,
                        "timestamp": str(int(time.time())),
                        "type": "text",
                        "text": {"body": text},
                    }],
                }
            }]
        }],
    }).encode("utf-8")


def test_anonymous_whatsapp_chats_are_401_on_amp_and_maxine(monkeypatch, tmp_path):
    from app.edition import _ALLOWLIST_EXEMPT

    exempt = {(method, path) for method, path in _ALLOWLIST_EXEMPT}
    assert ("GET", "/api/v1/whatsapp/chats") not in exempt
    assert ("GET", "/api/v1/whatsapp/chats/search") not in exempt
    assert ("GET", "/api/v1/whatsapp/webhook") in exempt

    for edition in ("amp", "maxine"):
        root = tmp_path / edition
        root.mkdir()
        client = _chats_client(monkeypatch, root, edition)
        for path in CHATS_PATHS:
            denied = client.get(path, params={"q": "hola"} if path.endswith("/search") else None)
            assert denied.status_code in {401, 302, 303}, (edition, path, denied.status_code)
            if denied.status_code == 401:
                body = denied.json()
                assert body.get("code") == "sin_acceso" or "Sin acceso" in str(body.get("detail") or "")


def test_logged_in_owner_can_read_chats_on_amp_and_maxine(monkeypatch, tmp_path):
    from app.services.amp_access import SESSION_COOKIE, create_session_token
    from app.services.whatsapp_store import record_message

    for edition in ("amp", "maxine"):
        root = tmp_path / f"{edition}-ok"
        root.mkdir()
        client = _chats_client(monkeypatch, root, edition)
        record_message("573001112233", direction="in", kind="text", body="hola dueño")
        client.cookies.set(SESSION_COOKIE, create_session_token("owner@example.com"))
        listed = client.get("/api/v1/whatsapp/chats")
        assert listed.status_code == 200, (edition, listed.status_code, listed.text)
        assert listed.json()["readonly"] is True
        thread = client.get("/api/v1/whatsapp/chats/573001112233/messages")
        assert thread.status_code == 200
        assert thread.json()["messages"][0]["body"] == "hola dueño"


def test_whatsapp_inbound_usage_cap_under_at_over_both_editions(monkeypatch, tmp_path):
    """Cap check runs before ingest. Spanish reply to the owner only."""
    from app.services import whatsapp_cloud as wa
    from app.services.instance_usage import record_usage, usage_summary, whatsapp_cap_reply_es

    ingest_calls = []
    graph_calls = []

    def fake_ingest(transcript, **kwargs):
        ingest_calls.append({"transcript": transcript, "kwargs": kwargs})
        return {"draft": {"id": "draft-test"}, "session_id": "sess-test"}

    def fake_format(_view):
        return "respuesta de prueba del modelo"

    def fake_graph(method, url, token="", body=None, headers=None):
        graph_calls.append({"method": method, "url": url, "token": token, "body": body or b""})
        assert token == "test-token"
        if url.endswith("/messages"):
            return 200, b'{"messages":[{"id":"wamid.out"}]}'
        raise AssertionError(url)

    monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", "1000")
    monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")
    monkeypatch.setattr("app.services.voice_doc.ingest_transcript", fake_ingest)
    monkeypatch.setattr("app.services.voice_doc.format_session_reply", fake_format)
    monkeypatch.setattr(wa, "graph_request", fake_graph)

    for edition in ("amp", "maxine"):
        root = tmp_path / f"{edition}-cap"
        root.mkdir()
        _family_env(monkeypatch, root, edition)
        monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", "1000")
        monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")

        ingest_calls.clear()
        graph_calls.clear()
        record_usage(input_tokens=100, output_tokens=0, model="MiniMax-M3")
        under = usage_summary()
        assert under["allowance"] == 200
        assert under["level"] == "ok"
        body = _payload("Cotiza el curso para Ana", f"wamid.{edition}.under")
        result = wa.handle_webhook(body, _sign(body))
        assert result["processed"] == 1
        assert ingest_calls, f"{edition} under cap must call the model"
        assert not result.get("usage_capped")
        sent_to = [json.loads(call["body"]).get("to") for call in graph_calls if call["url"].endswith("/messages")]
        assert sent_to == ["573001112233"]
        assert all("3009998888" not in str(call["body"]) for call in graph_calls)

        ingest_calls.clear()
        graph_calls.clear()
        record_usage(input_tokens=100, output_tokens=0, model="MiniMax-M3")
        at = usage_summary()
        assert at["month"]["tokens"] == 200
        assert at["level"] == "blocked"
        body = _payload("Otra cotización", f"wamid.{edition}.at")
        result = wa.handle_webhook(body, _sign(body))
        assert result["processed"] == 1
        assert result.get("usage_capped") is True
        assert ingest_calls == []
        refusal = whatsapp_cap_reply_es()
        assert "tope" in refusal
        assert "20%" in refusal
        assert result["reply"] == refusal
        outbound = [json.loads(call["body"]) for call in graph_calls if call["url"].endswith("/messages")]
        assert len(outbound) == 1
        assert outbound[0]["to"] == "573001112233"
        assert outbound[0]["text"]["body"] == refusal
        assert "respuesta de prueba del modelo" not in json.dumps(outbound)

        ingest_calls.clear()
        graph_calls.clear()
        record_usage(input_tokens=50, output_tokens=0, model="MiniMax-M3")
        over = usage_summary()
        assert over["month"]["tokens"] == 250
        assert over["level"] == "blocked"
        assert over["used"] > over["allowance"]
        body = _payload("Sigue dictando", f"wamid.{edition}.over")
        result = wa.handle_webhook(body, _sign(body))
        assert result.get("usage_capped") is True
        assert ingest_calls == []
        outbound = [json.loads(call["body"]) for call in graph_calls if call["url"].endswith("/messages")]
        assert outbound and outbound[0]["to"] == "573001112233"
        assert outbound[0]["text"]["body"] == refusal
        stranger = _payload("Hola desde otro número", f"wamid.{edition}.stranger", sender="573009998888")
        before = len(graph_calls)
        ignored = wa.handle_webhook(stranger, _sign(stranger))
        assert ignored["processed"] == 0
        assert len(graph_calls) == before


def test_family_default_baseline_enforces_without_env_both_editions(monkeypatch, tmp_path):
    """No EMPIRE_USAGE_BASELINE_* — built-in 5M tokens, 20% = 1M, enforced."""
    from app.services import whatsapp_cloud as wa
    from app.services.instance_usage import (
        DEFAULT_FAMILY_BASELINE_MONTHLY_TOKENS,
        enforce_whatsapp_model_cap,
        record_usage,
        usage_summary,
        whatsapp_cap_reply_es,
    )

    ingest_calls = []
    graph_calls = []

    def fake_ingest(transcript, **kwargs):
        ingest_calls.append(transcript)
        return {"draft": {"id": "draft-default"}, "session_id": "sess-default"}

    def fake_format(_view):
        return "respuesta de prueba del modelo"

    def fake_graph(method, url, token="", body=None, headers=None):
        graph_calls.append({"url": url, "body": body or b""})
        if url.endswith("/messages"):
            return 200, b'{"messages":[{"id":"wamid.out"}]}'
        raise AssertionError(url)

    monkeypatch.setattr("app.services.voice_doc.ingest_transcript", fake_ingest)
    monkeypatch.setattr("app.services.voice_doc.format_session_reply", fake_format)
    monkeypatch.setattr(wa, "graph_request", fake_graph)

    assert DEFAULT_FAMILY_BASELINE_MONTHLY_TOKENS == 5_000_000
    default_allowance = DEFAULT_FAMILY_BASELINE_MONTHLY_TOKENS * 0.20

    for edition in ("amp", "maxine"):
        root = tmp_path / f"{edition}-default"
        root.mkdir()
        _family_env(monkeypatch, root, edition)
        monkeypatch.delenv("EMPIRE_USAGE_BASELINE_MONTHLY_USD", raising=False)
        monkeypatch.delenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", raising=False)

        summary = usage_summary()
        assert summary["enforced"] is True
        assert summary["baseline_source"] == "default"
        assert summary["baseline_basis"] == "recorded_tokens"
        assert summary["baseline"] == DEFAULT_FAMILY_BASELINE_MONTHLY_TOKENS
        assert summary["allowance"] == default_allowance
        assert summary["used_percent"] == 0.0
        assert summary["remaining_percent"] == 20.0
        assert summary["level"] == "ok"
        assert summary["cap_percent"] == 20
        assert enforce_whatsapp_model_cap() is None

        ingest_calls.clear()
        graph_calls.clear()
        body = _payload("Cotiza con el tope por defecto", f"wamid.{edition}.default.under")
        result = wa.handle_webhook(body, _sign(body))
        assert result["processed"] == 1
        assert ingest_calls
        assert not result.get("usage_capped")

        record_usage(input_tokens=int(default_allowance), output_tokens=0, model="MiniMax-M3")
        blocked = usage_summary()
        assert blocked["level"] == "blocked"
        assert blocked["used_percent"] == 20.0
        assert blocked["remaining_percent"] == 0.0
        assert blocked["used"] >= blocked["allowance"]
        assert enforce_whatsapp_model_cap() == whatsapp_cap_reply_es()

        ingest_calls.clear()
        graph_calls.clear()
        body = _payload("Otra cotización al tope", f"wamid.{edition}.default.at")
        result = wa.handle_webhook(body, _sign(body))
        assert result.get("usage_capped") is True
        assert ingest_calls == []
        outbound = [json.loads(call["body"]) for call in graph_calls if call["url"].endswith("/messages")]
        assert outbound and outbound[0]["to"] == "573001112233"
        assert outbound[0]["text"]["body"] == whatsapp_cap_reply_es()


def test_family_baseline_env_overrides_default_both_editions(monkeypatch, tmp_path):
    from app.services.instance_usage import (
        DEFAULT_FAMILY_BASELINE_MONTHLY_TOKENS,
        record_usage,
        usage_summary,
    )

    for edition in ("amp", "maxine"):
        root = tmp_path / f"{edition}-override"
        root.mkdir()
        _family_env(monkeypatch, root, edition)
        monkeypatch.delenv("EMPIRE_USAGE_BASELINE_MONTHLY_USD", raising=False)
        monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", "1000")
        summary = usage_summary()
        assert summary["enforced"] is True
        assert summary["baseline_source"] == "env"
        assert summary["baseline"] == 1000
        assert summary["allowance"] == 200
        assert summary["baseline"] != DEFAULT_FAMILY_BASELINE_MONTHLY_TOKENS
        record_usage(input_tokens=200, output_tokens=0, model="MiniMax-M3")
        assert usage_summary()["level"] == "blocked"

        monkeypatch.delenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", raising=False)
        monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_USD", "10")
        monkeypatch.setenv("MINIMAX_USD_PER_MILLION_TOKENS", "1")
        usd = usage_summary()
        assert usd["baseline_source"] == "env"
        assert usd["baseline_basis"] == "usd"
        assert usd["baseline"] == 10
        assert usd["allowance"] == 2


def test_whatsapp_fail_closed_when_usage_unreadable(monkeypatch, tmp_path):
    from app.services import whatsapp_cloud as wa
    from app.services.instance_usage import enforce_whatsapp_model_cap, whatsapp_cap_reply_es

    ingest_calls = []
    graph_calls = []

    def fake_ingest(transcript, **kwargs):
        ingest_calls.append(transcript)
        return {"draft": {"id": "nope"}, "session_id": "nope"}

    def fake_graph(method, url, token="", body=None, headers=None):
        graph_calls.append({"url": url, "body": body or b""})
        if url.endswith("/messages"):
            return 200, b'{"messages":[{"id":"wamid.out"}]}'
        raise AssertionError(url)

    monkeypatch.setattr("app.services.voice_doc.ingest_transcript", fake_ingest)
    monkeypatch.setattr("app.services.voice_doc.format_session_reply", lambda _view: "no")
    monkeypatch.setattr(wa, "graph_request", fake_graph)
    monkeypatch.setattr(
        "app.services.instance_usage._connect",
        lambda: (_ for _ in ()).throw(RuntimeError("usage db unreadable")),
    )

    for edition in ("amp", "maxine"):
        root = tmp_path / f"{edition}-fail"
        root.mkdir()
        _family_env(monkeypatch, root, edition)
        monkeypatch.delenv("EMPIRE_USAGE_BASELINE_MONTHLY_USD", raising=False)
        monkeypatch.delenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", raising=False)
        refusal = whatsapp_cap_reply_es()
        assert enforce_whatsapp_model_cap() == refusal
        ingest_calls.clear()
        graph_calls.clear()
        body = _payload("Dicta aunque no se lea el uso", f"wamid.{edition}.failclosed")
        result = wa.handle_webhook(body, _sign(body))
        assert result.get("usage_capped") is True
        assert ingest_calls == []
        outbound = [json.loads(call["body"]) for call in graph_calls if call["url"].endswith("/messages")]
        assert outbound and outbound[0]["to"] == "573001112233"
        assert outbound[0]["text"]["body"] == refusal


def test_tutorial_routes_linked_from_dashboard_and_help():
    root = Path(__file__).resolve().parents[2]
    help_menu = (root / "empire-command-center" / "app" / "components" / "voice" / "HelpMenu.tsx").read_text(encoding="utf-8")
    dashboard = (root / "empire-command-center" / "app" / "amp" / "dashboard" / "page.tsx").read_text(encoding="utf-8")
    amp_nav = (root / "empire-command-center" / "app" / "components" / "amp" / "AmpNav.tsx").read_text(encoding="utf-8")
    dashboard_screen = (root / "empire-command-center" / "app" / "components" / "screens" / "DashboardScreen.tsx").read_text(encoding="utf-8")
    assert 'href="/ayuda/whatsapp"' in help_menu
    assert "/amp/whatsapp" not in help_menu
    assert 'href: \'/amp/whatsapp\'' in dashboard or 'href: "/amp/whatsapp"' in dashboard
    assert "/ayuda/whatsapp" in dashboard
    assert "/amp/whatsapp" in amp_nav
    assert "HelpMenu" in dashboard_screen
    setup = (root / "empire-command-center" / "app" / "amp" / "whatsapp" / "page.tsx").read_text(encoding="utf-8")
    ayuda = (root / "empire-command-center" / "app" / "ayuda" / "whatsapp" / "page.tsx").read_text(encoding="utf-8")
    assert "renderWhatsAppSetupPage" in setup
    assert "renderWhatsAppSetupPage" in ayuda
