"""Pedir ayuda → Chief e webhook + secret-gated inbound reply."""
from __future__ import annotations

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.test_family_help import _client, _family


def _support_app():
    from app.middleware.edition_gate import amp_access_middleware
    from app.routers.family_help import router as help_router
    from app.routers.support_tickets import router as support_router

    app = FastAPI()
    app.middleware("http")(amp_access_middleware)
    app.include_router(help_router, prefix="/api/v1")
    app.include_router(support_router, prefix="/api/v1/support")
    return TestClient(app)


class _WebhookSink(BaseHTTPRequestHandler):
    payloads: list[dict] = []
    headers_seen: list[dict] = []
    delay_s: float = 0.0

    def do_POST(self):
        if self.delay_s:
            time.sleep(self.delay_s)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        self.payloads.append(json.loads(raw.decode("utf-8") or "{}"))
        self.headers_seen.append({k.lower(): v for k, v in self.headers.items()})
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, format, *args):
        return


def _start_webhook(delay_s: float = 0.0):
    _WebhookSink.payloads = []
    _WebhookSink.headers_seen = []
    _WebhookSink.delay_s = delay_s
    server = ThreadingHTTPServer(("127.0.0.1", 0), _WebhookSink)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, f"http://{host}:{port}/hook"


def _wait_payloads(timeout: float = 2.0) -> list[dict]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _WebhookSink.payloads:
            return _WebhookSink.payloads
        time.sleep(0.02)
    return _WebhookSink.payloads


def test_family_guard_allows_configured_webhook_loopback(monkeypatch):
    from app.security.family_fs_guard import _webhook_loopback_ports

    monkeypatch.delenv("SUPPORT_WEBHOOK_URL", raising=False)
    assert _webhook_loopback_ports() == set()
    monkeypatch.setenv("SUPPORT_WEBHOOK_URL", "http://127.0.0.1:8099/hook")
    assert _webhook_loopback_ports() == {8099}
    monkeypatch.setenv("SUPPORT_WEBHOOK_URL", "https://example.invalid/support/webhook")
    assert _webhook_loopback_ports() == set()


def test_webhook_loopback_refuses_owner_and_studio_ports(monkeypatch):
    from app.security.family_fs_guard import _owner_loopback_ports, _webhook_loopback_ports

    blocked = _owner_loopback_ports()
    assert {8000, 3000, 3005}.issubset(blocked)
    for port in (8000, 3000, 3005):
        monkeypatch.setenv("SUPPORT_WEBHOOK_URL", f"http://127.0.0.1:{port}/hook")
        assert _webhook_loopback_ports() == set()
        monkeypatch.setenv("SUPPORT_WEBHOOK_URL", f"http://localhost:{port}/support")
        assert _webhook_loopback_ports() == set()
    monkeypatch.setenv("SUPPORT_WEBHOOK_URL", "http://127.0.0.1:8099/hook")
    assert _webhook_loopback_ports() == {8099}


def test_webhook_auth_header_default_and_custom(monkeypatch):
    from app.services.support_bridge import webhook_auth_header

    monkeypatch.delenv("SUPPORT_WEBHOOK_AUTH_HEADER", raising=False)
    assert webhook_auth_header("secret") == ("Authorization", "Bearer secret")
    monkeypatch.setenv("SUPPORT_WEBHOOK_AUTH_HEADER", "X-Support-Key")
    assert webhook_auth_header("secret") == ("X-Support-Key", "secret")
    monkeypatch.setenv("SUPPORT_WEBHOOK_AUTH_HEADER", "X-Hook: <key>")
    assert webhook_auth_header("abc") == ("X-Hook", "abc")


def test_create_ticket_posts_webhook_payload(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "amp")
    monkeypatch.setenv("SUPPORT_WEBHOOK_KEY", "sender-key")
    server, url = _start_webhook()
    monkeypatch.setenv("SUPPORT_WEBHOOK_URL", url)
    try:
        from app.services.family_help import create_ticket

        ticket = create_ticket(
            message="No me abre el chat",
            sender="Juan Diego Giraldo",
            current_screen="chat · Max-e",
            last_error="API 500: /max/chat",
            notify=True,
        )
        assert ticket["id"].startswith("fh-")
        assert ticket["current_screen"] == "chat · Max-e"
        assert ticket["last_error"] == "API 500: /max/chat"
        payloads = _wait_payloads()
        assert payloads, "webhook was not called"
        payload = payloads[0]
        assert payload["ticket_id"] == ticket["id"]
        assert payload["edition"] == "max-e"
        assert payload["brother"] == "Juan Diego Giraldo"
        assert payload["question"] == "No me abre el chat"
        assert payload["current_screen"] == "chat · Max-e"
        assert payload["last_error"] == "API 500: /max/chat"
        assert payload["created_at"]
        auth = _WebhookSink.headers_seen[0].get("authorization")
        assert auth == "Bearer sender-key"
    finally:
        server.shutdown()


def test_create_ticket_posts_maxine_webhook_payload(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "maxine")
    monkeypatch.setenv("SUPPORT_WEBHOOK_KEY", "sender-key")
    server, url = _start_webhook()
    monkeypatch.setenv("SUPPORT_WEBHOOK_URL", url)
    try:
        from app.services.family_help import create_ticket

        ticket = create_ticket(
            message="No me abre el chat",
            sender="Camilo Giraldo",
            current_screen="chat · Maxine",
            last_error="API 500: /max/chat",
            notify=True,
        )
        assert ticket["edition"] == "maxine"
        payloads = _wait_payloads()
        assert payloads, "webhook was not called"
        payload = payloads[0]
        assert payload["ticket_id"] == ticket["id"]
        assert payload["edition"] == "maxine"
        assert payload["brother"] == "Camilo Giraldo"
        assert payload["question"] == "No me abre el chat"
        assert payload["current_screen"] == "chat · Maxine"
        assert payload["last_error"] == "API 500: /max/chat"
        assert _WebhookSink.headers_seen[0].get("authorization") == "Bearer sender-key"
    finally:
        server.shutdown()


def test_notify_false_skips_webhook(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "amp")
    monkeypatch.setenv("SUPPORT_WEBHOOK_KEY", "sender-key")
    server, url = _start_webhook()
    monkeypatch.setenv("SUPPORT_WEBHOOK_URL", url)
    try:
        from app.services.family_help import create_ticket

        ticket = create_ticket(
            message="solo local",
            sender="Juan Diego Giraldo",
            notify=False,
        )
        assert ticket["id"].startswith("fh-")
        time.sleep(0.3)
        assert _WebhookSink.payloads == []
    finally:
        server.shutdown()


def test_create_returns_while_webhook_hangs(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "amp")
    monkeypatch.setenv("SUPPORT_WEBHOOK_KEY", "sender-key")
    server, url = _start_webhook(delay_s=2.0)
    monkeypatch.setenv("SUPPORT_WEBHOOK_URL", url)
    try:
        from app.services.family_help import create_ticket

        start = time.monotonic()
        ticket = create_ticket(
            message="el webhook está lento",
            sender="Juan Diego Giraldo",
            notify=True,
        )
        elapsed = time.monotonic() - start
        assert ticket["id"].startswith("fh-")
        assert elapsed < 0.8, f"create_ticket blocked on webhook ({elapsed:.2f}s)"
        payloads = _wait_payloads(timeout=4.0)
        assert payloads and payloads[0]["ticket_id"] == ticket["id"]
    finally:
        server.shutdown()


def test_reply_auth_success_and_401(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "amp")
    monkeypatch.setenv("SUPPORT_REPLY_SECRET", "reply-secret")
    monkeypatch.setenv("AMP_OPEN_ACCESS", "1")
    monkeypatch.setenv("AMP_OWNER_EMAIL", "owner@example.com")
    from app.services.family_help import create_ticket

    ticket = create_ticket(message="Ayuda por favor", sender="Juan", notify=False)
    client = _support_app()

    denied = client.post(
        f"/api/v1/support/tickets/{ticket['id']}/reply",
        json={"body": "Hola Juan, ya lo vi."},
        headers={"Authorization": "Bearer wrong"},
    )
    assert denied.status_code == 401

    missing = client.post(
        f"/api/v1/support/tickets/{ticket['id']}/reply",
        json={"body": "Hola Juan, ya lo vi."},
    )
    assert missing.status_code == 401

    ok = client.post(
        f"/api/v1/support/tickets/{ticket['id']}/reply",
        json={"body": "Hola Juan, ya lo vi.", "author": "Chief e"},
        headers={"Authorization": "Bearer reply-secret"},
    )
    assert ok.status_code == 200, ok.text
    body = ok.json()["ticket"]
    assert body["status"] == "answered"
    assert body["replies"][0]["body"] == "Hola Juan, ya lo vi."
    assert body["replies"][0]["author"] == "Chief e"


def test_reply_stays_exempt_from_session_gate(monkeypatch, tmp_path):
    from app.edition import access_exempt, support_reply_exempt

    path = "/api/v1/support/tickets/fh-abc123def456/reply"
    assert support_reply_exempt("POST", path) is True
    assert access_exempt("POST", path) is True
    assert access_exempt("GET", path) is False
    assert access_exempt("POST", "/api/support/tickets/fh-abc123def456/reply") is False
    assert access_exempt("POST", "/api/v1/family-help/inbox/fh-1/reply") is False

    _family(monkeypatch, tmp_path, "amp")
    monkeypatch.setenv("SUPPORT_REPLY_SECRET", "reply-secret")
    monkeypatch.delenv("AMP_OPEN_ACCESS", raising=False)
    from app.services.family_help import create_ticket

    ticket = create_ticket(message="sin sesión", sender="Juan", notify=False)
    client = _support_app()
    gated = client.get("/api/v1/family-help/tickets")
    assert gated.status_code == 403
    replied = client.post(
        f"/api/v1/support/tickets/{ticket['id']}/reply",
        json={"body": "Respuesta sin cookie de sesión."},
        headers={"Authorization": "Bearer reply-secret"},
    )
    assert replied.status_code == 200, replied.text


def test_ticket_isolation_per_edition(monkeypatch, tmp_path):
    inbox = tmp_path / "shared-inbox"
    inbox.mkdir()
    _family(monkeypatch, tmp_path, "maxine", inbox)
    monkeypatch.setenv("SUPPORT_REPLY_SECRET", "reply-secret")
    monkeypatch.setenv("AMP_OPEN_ACCESS", "1")
    from app.services.family_help import create_ticket

    maxine_ticket = create_ticket(message="Soy Camilo", sender="Camilo Giraldo", notify=False)
    assert maxine_ticket["edition"] == "maxine"

    from app.services.support_bridge import build_webhook_payload

    payload = build_webhook_payload(maxine_ticket)
    assert payload["edition"] == "maxine"
    assert payload["brother"] == "Camilo Giraldo"

    _family(monkeypatch, tmp_path, "amp", inbox)
    monkeypatch.setenv("SUPPORT_REPLY_SECRET", "reply-secret")
    monkeypatch.setenv("AMP_OPEN_ACCESS", "1")
    amp_ticket = create_ticket(message="Soy Juan", sender="Juan Diego Giraldo", notify=False)
    client = _support_app()

    foreign = client.post(
        f"/api/v1/support/tickets/{maxine_ticket['id']}/reply",
        json={"body": "esto no debe entrar en Max-e"},
        headers={"Authorization": "Bearer reply-secret"},
    )
    assert foreign.status_code == 404

    listed = _client().get("/api/v1/family-help/tickets")
    ids = [row["id"] for row in listed.json()["tickets"]]
    assert amp_ticket["id"] in ids
    assert maxine_ticket["id"] not in ids
