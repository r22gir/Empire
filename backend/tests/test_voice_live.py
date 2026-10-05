"""MAX live voice (xAI realtime bridge) — auth, tool whitelist, barge-in."""
import asyncio
import json
import time

import pytest
from jose import jwt as jose_jwt
from jose.utils import long_to_base64
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from app.services.max import voice_live as vl


class _WS:
    def __init__(self, headers=None, cookies=None, peer="127.0.0.1"):
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}
        self.cookies = cookies or {}
        self.client = type("C", (), {"host": peer})()
        self.sent = []

    async def send_text(self, text):
        self.sent.append(json.loads(text))

    async def send_bytes(self, data):
        self.sent.append(("audio", len(data)))


def _keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption())
    pub = key.public_key().public_numbers()
    jwk = {"kty": "RSA", "kid": "test", "alg": "RS256", "use": "sig",
           "n": long_to_base64(pub.n).decode(), "e": long_to_base64(pub.e).decode()}
    return pem, jwk


def _token(pem, aud=None, iss=None):
    now = int(time.time())
    return jose_jwt.encode({"aud": [aud or vl.CF_ACCESS_AUD], "iss": iss or f"https://{vl.CF_ACCESS_TEAM_DOMAIN}",
                            "email": "founder@example.com", "iat": now, "exp": now + 300},
                           pem, algorithm="RS256", headers={"kid": "test"})


def test_loopback_allowed_proxied_denied_public_host_denied():
    assert vl.authorize_websocket(_WS())[0] is True
    assert vl.authorize_websocket(_WS({"cf-ray": "x", "x-forwarded-for": "1.2.3.4"}))[0] is False
    assert vl.authorize_websocket(_WS({"host": "luxe.empirebox.store"}))[0] is False
    assert vl.authorize_websocket(_WS(peer="10.0.0.5"))[0] is False


def test_tailscale_serve_allowlist(monkeypatch):
    monkeypatch.setenv("TAILSCALE_ALLOWED_LOGINS", "founder@example.com, second@example.com")
    ok, via, user = vl.authorize_websocket(_WS(
        {"Tailscale-User-Login": "Founder@example.com"}, peer="127.0.0.1",
    ))
    assert (ok, via, user) == (True, "tailscale", "Founder@example.com")
    ok, via, user = vl.authorize_websocket(_WS(
        {"tailscale-user-login": "second@example.com", "x-forwarded-for": "100.1.2.3"},
        peer="::1",
    ))
    assert (ok, via) == (True, "tailscale")

    ok, via, _user = vl.authorize_websocket(_WS(peer="127.0.0.1"))
    assert ok is True and via == "loopback"
    ok, via, _user = vl.authorize_websocket(_WS(
        {"x-forwarded-for": "100.1.2.3"}, peer="127.0.0.1",
    ))
    assert ok is False

    ok, via, _user = vl.authorize_websocket(_WS(
        {"tailscale-user-login": "stranger@example.com"}, peer="127.0.0.1",
    ))
    assert ok is False and via == "tailscale login not allowed"

    ok, via, _user = vl.authorize_websocket(_WS(
        {"tailscale-user-login": "founder@example.com", "x-forwarded-for": "100.1.2.3"},
        peer="100.64.0.8",
    ))
    assert ok is False and via == "tailscale header from non-loopback"

    monkeypatch.setenv("TAILSCALE_ALLOWED_LOGINS", "")
    ok, via, _user = vl.authorize_websocket(_WS(
        {"tailscale-user-login": "founder@example.com"}, peer="127.0.0.1",
    ))
    assert ok is False and via == "tailscale login not allowed"
    monkeypatch.delenv("TAILSCALE_ALLOWED_LOGINS", raising=False)
    ok, _, _ = vl.authorize_websocket(_WS(
        {"tailscale-user-login": "founder@example.com"}, peer="::1",
    ))
    assert ok is False


def test_presentation_http_uses_the_same_tailscale_rule(monkeypatch):
    from pathlib import Path

    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers.simli_avatar import router as simli_router

    avatar_src = (Path(__file__).resolve().parents[1] / "app" / "routers" / "avatar.py").read_text(encoding="utf-8")
    for needle in ("async def avatar_chat", "async def avatar_listen", "async def avatar_speak", "async def avatar_status"):
        assert "_require_avatar_access(request)" in avatar_src.split(needle, 1)[1][:400]

    monkeypatch.setenv("TAILSCALE_ALLOWED_LOGINS", "founder@example.com")
    app = FastAPI()
    app.include_router(simli_router, prefix="/api/v1")
    allowed = TestClient(app, client=("127.0.0.1", 9))
    denied = TestClient(app, client=("100.64.0.8", 9))
    ok = allowed.get("/api/v1/avatar/simli/status", headers={"Tailscale-User-Login": "founder@example.com"})
    assert ok.status_code == 200
    spoofed = denied.get("/api/v1/avatar/simli/status", headers={"Tailscale-User-Login": "founder@example.com"})
    assert spoofed.status_code == 401


def _proxy_wrapped_app():
    """Same middleware uvicorn installs: trusted loopback, X-Forwarded-For rewrites the peer."""
    from fastapi import FastAPI, Request, WebSocket
    from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

    from app.routers.simli_avatar import router as simli_router

    inner = FastAPI()
    inner.include_router(simli_router, prefix="/api/v1")

    @inner.get("/who")
    def who(request: Request):
        return {"peer": request.client.host if request.client else ""}

    @inner.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket):
        ok, via, user = vl.authorize_websocket(websocket)
        if not ok:
            await websocket.close(code=4401)
            return
        await websocket.accept()
        await websocket.send_json({"via": via, "user": user})

    return ProxyHeadersMiddleware(inner, trusted_hosts="127.0.0.1")


def test_proxy_headers_rewrite_peer_before_the_app_sees_it():
    from fastapi.testclient import TestClient

    client = TestClient(_proxy_wrapped_app(), client=("127.0.0.1", 9))
    seen = client.get("/who", headers={"x-forwarded-for": "100.110.233.75"})
    assert seen.status_code == 200
    assert seen.json()["peer"] == "100.110.233.75"
    ignored = TestClient(_proxy_wrapped_app(), client=("10.0.0.8", 9))
    stayed = ignored.get("/who", headers={"x-forwarded-for": "100.110.233.75"})
    assert stayed.json()["peer"] == "10.0.0.8"


def test_rewritten_tailscale_peer_needs_the_next_stamp(monkeypatch):
    from fastapi.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    monkeypatch.setenv("TAILSCALE_ALLOWED_LOGINS", "founder@example.com")
    monkeypatch.setenv("EMPIRE_PROXY_AUTH_SECRET", "hop-secret")
    client = TestClient(_proxy_wrapped_app(), client=("127.0.0.1", 9))
    rewritten = {"x-forwarded-for": "100.110.233.75"}
    trusted = {
        **rewritten,
        "x-empire-proxy-secret": "hop-secret",
        "x-empire-tailscale-verified": "1",
        "tailscale-user-login": "founder@example.com",
    }
    who = client.get("/who", headers=trusted)
    assert who.json()["peer"] == "100.110.233.75"
    assert client.get("/api/v1/avatar/simli/status", headers=trusted).status_code == 200

    spoofed = {
        **rewritten,
        "x-empire-proxy-secret": "hop-secret",
        "tailscale-user-login": "founder@example.com",
    }
    assert client.get("/api/v1/avatar/simli/status", headers=spoofed).status_code == 401

    restored = {**rewritten, "x-empire-proxy-secret": "hop-secret"}
    assert client.get("/api/v1/avatar/simli/status", headers=restored).status_code == 200

    cloudflare = {**restored, "cf-ray": "abc"}
    assert client.get("/api/v1/avatar/simli/status", headers=cloudflare).status_code == 401

    monkeypatch.setenv("TAILSCALE_ALLOWED_LOGINS", "")
    assert client.get("/api/v1/avatar/simli/status", headers=trusted).status_code == 401
    monkeypatch.setenv("TAILSCALE_ALLOWED_LOGINS", "founder@example.com")

    wrong = {**trusted, "x-empire-proxy-secret": "nope"}
    assert client.get("/api/v1/avatar/simli/status", headers=wrong).status_code == 401
    missing = {k: v for k, v in trusted.items() if k != "x-empire-proxy-secret"}
    assert client.get("/api/v1/avatar/simli/status", headers=missing).status_code == 401

    lan = TestClient(_proxy_wrapped_app(), client=("10.0.0.8", 9))
    injected = {
        "x-forwarded-for": "127.0.0.1",
        "x-empire-proxy-secret": "spoofed",
        "x-empire-tailscale-verified": "1",
        "tailscale-user-login": "founder@example.com",
    }
    assert lan.get("/who", headers=injected).json()["peer"] == "10.0.0.8"
    assert lan.get("/api/v1/avatar/simli/status", headers=injected).status_code == 401

    with client.websocket_connect("/ws", headers=trusted) as socket:
        assert socket.receive_json()["via"] == "tailscale"
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws", headers=spoofed):
            pass
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws", headers=restored):
            pass


def test_access_jwt_valid_accepted_wrong_aud_rejected(monkeypatch):
    pem, jwk = _keypair()
    monkeypatch.setitem(vl._jwks_cache, "keys", {"keys": [jwk]})
    monkeypatch.setitem(vl._jwks_cache, "at", time.time())
    ok, via, user = vl.authorize_websocket(_WS({"cf-ray": "x", "cf-access-jwt-assertion": _token(pem)}))
    assert (ok, via, user) == (True, "cloudflare_access", "founder@example.com")
    ok, _, _ = vl.authorize_websocket(_WS({"cf-ray": "x"}, cookies={"CF_Authorization": _token(pem)}))
    assert ok is True
    assert vl.authorize_websocket(_WS({"cf-ray": "x", "cf-access-jwt-assertion": _token(pem, aud="other")}))[0] is False
    assert vl.authorize_websocket(_WS({"cf-ray": "x", "cf-access-jwt-assertion": _token(pem, iss="https://evil")}))[0] is False


def test_session_exposes_only_read_only_tools_and_voice_flag(monkeypatch):
    ev = vl.session_update_event()
    names = [t["name"] for t in ev["session"]["tools"]]
    # request_improvement only writes a change request; builds need Rafael's tap (Oct 4, 2026)
    assert names == list(vl.VOICE_READ_ONLY_TOOLS) + ["queue_for_founder_approval", "request_improvement",
                                                      "send_email"]
    for must in ("get_tasks", "get_desk_status", "get_services_health", "get_system_stats", "check_email",
                 "list_job_images", "search_conversations", "get_weather", "list_quotes_awaiting_review",
                 "show_quote_for_review"):
        assert must in names
    for banned in ("shell_execute", "file_write", "approve_quote", "deposit_pay_link", "create_task"):
        assert banned not in names
    assert ev["session"]["turn_detection"]["type"] == "server_vad"
    assert ev["session"]["audio"]["input"]["format"] == {"type": "audio/pcm", "rate": 24000}
    monkeypatch.setenv("XAI_API_KEY", "k")
    monkeypatch.setenv("MAX_DISABLE_XAI", "true")
    monkeypatch.delenv("MAX_VOICE_XAI_ENABLED", raising=False)
    assert vl.voice_status()["enabled"] is True  # voice flag independent of text kill switch
    monkeypatch.setenv("MAX_VOICE_XAI_ENABLED", "false")
    assert vl.voice_status()["enabled"] is False


def test_non_whitelisted_tool_refused():
    out = vl.run_readonly_tool("shell_execute", {"command": "id"})
    assert out["success"] is False and "not available in voice mode" in out["error"]


def test_barge_in_cancels_active_response_and_drops_its_audio():
    ws = _WS()
    call = vl.LiveCall(ws)
    upstream = []

    async def fake_send_upstream(payload):
        upstream.append(payload)

    call.send_upstream = fake_send_upstream

    async def run():
        await call.handle_upstream_event({"type": "response.created", "response": {"id": "r1"}})
        await call.handle_upstream_event({"type": "response.output_audio.delta", "response_id": "r1", "delta": "AAAA"})
        await call.handle_upstream_event({"type": "input_audio_buffer.speech_started"})
        await call.handle_upstream_event({"type": "response.output_audio.delta", "response_id": "r1", "delta": "AAAA"})

    asyncio.run(run())
    assert {"type": "response.cancel"} in upstream
    assert any(isinstance(m, dict) and m.get("type") == "interrupt" and m.get("response_id") == "r1" for m in ws.sent)
    assert sum(1 for m in ws.sent if isinstance(m, tuple)) == 1  # post-cancel audio dropped
    assert call.interrupts == 1


@pytest.mark.parametrize("name", ["shell_execute", "file_write", "file_delete", "approve_quote",
                                  "reject_quote", "deposit_pay_link", "create_task", "bash", "send_mail"])
def test_voice_allowlist_refuses_writes_server_side(monkeypatch, name):
    import app.services.max.tool_executor as te
    called = []
    monkeypatch.setattr(te, "execute_tool", lambda *a, **k: called.append(a))
    out = vl.run_voice_tool(name, {"to": "x@example.com", "command": "id"})
    assert out["success"] is False and "not available in voice mode" in out["error"]
    assert called == []  # refused before tool_executor is touched


def test_static_instructions_do_not_read_stale_memory_md(monkeypatch, tmp_path):
    stale = tmp_path / "memory.md"
    stale.write_text("# MAX AI — COMPLETE BRAIN v5.1\n## Last Updated: 2026-03-18\n")
    monkeypatch.setenv("MAX_MEMORY_PATH", str(stale))
    text = vl.build_instructions()
    assert "v5.1" not in text and "2026-03-18" not in text and "March 18" not in text
    assert "saved" in text and "queue_for_founder_approval" in text


def test_voice_brain_strips_stale_lines_and_caps_size():
    from app.services.max import voice_brain as vb
    assert vb.strip_stale("ok line\nI'm on brain v5.1 from March 18th\nkeep") == "ok line\nkeep"
    text = vb.assemble(model="m", read_tools=["get_tasks"], core="C" * 50000, snapshot="S",
                       brain="B" * 50000, memory="M" * 50000)
    assert len(text) <= vb.MAX_INSTRUCTION_CHARS
    assert "Transcripts" in text and "Live snapshot" in text


def test_voice_brain_cache(monkeypatch):
    from app.services.max import voice_brain as vb
    vb.clear_cache()
    calls = []

    async def fake_build(**kw):
        calls.append(1)
        return "INSTR", {"chars": 5}

    monkeypatch.setattr(vb, "build_voice_instructions", fake_build)
    t1, m1 = asyncio.run(vb.get_voice_instructions(model="m", read_tools=[]))
    t2, m2 = asyncio.run(vb.get_voice_instructions(model="m", read_tools=[]))
    assert t1 == t2 == "INSTR" and len(calls) == 1 and m2["cached"] is True
    vb.clear_cache()


def test_queue_for_founder_approval_creates_waiting_task_and_executes_nothing(monkeypatch, tmp_path):
    import sqlite3
    from contextlib import contextmanager
    db = tmp_path / "t.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        "CREATE TABLE tasks (id TEXT PRIMARY KEY, title TEXT, description TEXT, status TEXT, priority TEXT,"
        " desk TEXT, created_by TEXT, tags TEXT, metadata TEXT, created_at TEXT, updated_at TEXT);"
        "CREATE TABLE task_activity (task_id TEXT, actor TEXT, action TEXT, detail TEXT, created_at TEXT);")
    conn.commit(); conn.close()

    @contextmanager
    def fake_get_db():
        c = sqlite3.connect(db); c.row_factory = sqlite3.Row
        try:
            yield c; c.commit()
        finally:
            c.close()

    import app.db.database as dbm
    import app.services.max.tool_executor as te
    monkeypatch.setattr(dbm, "get_db", fake_get_db)
    executed = []
    monkeypatch.setattr(te, "execute_tool", lambda *a, **k: executed.append(a))
    out = vl.run_voice_tool("queue_for_founder_approval",
                            {"action": "Send Max this transcript", "details": "the voice call", "_founder": True},
                            call_id="abc", conversation_id="voice-abc")
    assert out["success"] is True and out["result"]["executed"] is False
    assert executed == []  # never goes through tool_executor / create_task
    c = sqlite3.connect(db); c.row_factory = sqlite3.Row
    row = dict(c.execute("SELECT * FROM tasks").fetchone())
    assert row["status"] == "waiting" and row["created_by"] == "voice"
    assert json.loads(row["tags"]) == ["voice-request", "needs-founder-approval"]
    assert "auto_execute" not in row["metadata"]  # TaskWorker trigger key must be absent
    assert "voice-abc" in row["description"]


def test_transcript_records_lines_tools_and_summary(monkeypatch, tmp_path):
    from app.services.max import voice_transcript as vt
    from app.services.max.unified_message_store import UnifiedMessageStore
    import app.services.max.unified_message_store as ums
    store = UnifiedMessageStore(tmp_path / "u.db")
    monkeypatch.setattr(ums, "unified_store", store)
    monkeypatch.setattr(vt, "CHATS_DIR", tmp_path / "chats")
    mem = []
    monkeypatch.setattr(vt.VoiceTranscript, "_write_memory", lambda self: mem.append(self.summary))
    t = vt.VoiceTranscript("abcdef1234", auth_via="loopback", model="grok-voice")
    t.start()
    t.add_user("Any tasks open?")
    t.add_tool("get_tasks", {"_founder": True}, True, "2 result(s)")
    t.add_assistant("Two open tasks.")
    res = t.finish(12.0, "hangup")
    assert res["saved"] is True
    rows = store.get_conversation("voice-abcdef1234")
    assert [r["role"] for r in rows] == ["system", "user", "tool", "assistant", "system", "system"]
    assert all(r["channel"] == "voice" for r in rows)
    assert "_founder" not in rows[2]["content"]
    assert "Any tasks open?" in t.summary and "get_tasks" in t.summary and mem
    chat = json.loads((tmp_path / "chats" / "founder" / "vabcdef1.json").read_text())
    assert chat["channel"] == "voice" and chat["messages"][0]["content"] == "Any tasks open?"
    last = vt.last_voice_call()
    assert last["conversation_id"] == "voice-abcdef1234" and last["summary"] and not last["in_progress"]
    assert vt.is_generic_voice_query("what did we discuss on the last voice call")
    assert "Two open tasks" in vt.render_last_voice_call_for_prompt()


def test_live_call_feeds_transcript_from_events():
    ws = _WS()
    call = vl.LiveCall(ws)
    got = []

    class T:
        conversation_id = "voice-x"
        def add_user(self, *a): got.append(("user",) + a)
        def add_assistant(self, *a): got.append(("assistant",) + a)

    call.transcript = T()

    async def fake_send_upstream(payload):
        pass

    call.send_upstream = fake_send_upstream

    async def run():
        await call.handle_upstream_event({"type": "conversation.item.input_audio_transcription.completed",
                                          "transcript": "hi", "item_id": "i1"})
        await call.handle_upstream_event({"type": "response.created", "response": {"id": "r1"}})
        await call.handle_upstream_event({"type": "response.output_audio_transcript.delta", "response_id": "r1", "delta": "Hel"})
        await call.handle_upstream_event({"type": "response.output_audio_transcript.done", "response_id": "r1", "transcript": "Hello"})
        await call.handle_upstream_event({"type": "response.done", "response": {"id": "r1", "status": "completed"}})
        # barged-in response: only deltas, then done -> recorded as interrupted partial
        await call.handle_upstream_event({"type": "response.created", "response": {"id": "r2"}})
        await call.handle_upstream_event({"type": "response.output_audio_transcript.delta", "response_id": "r2", "delta": "Long ans"})
        await call.handle_upstream_event({"type": "input_audio_buffer.speech_started"})
        await call.handle_upstream_event({"type": "response.done", "response": {"id": "r2", "status": "cancelled"}})

    asyncio.run(run())
    assert got[0] == ("user", "hi", "i1")
    assert got[1] == ("assistant", "Hello", "r1", False)
    assert got[2] == ("assistant", "Long ans", "r2", True)


# ── 2026-10-05: voice gets the same self-email rule as text chat ──────
class _FakeResult:
    def __init__(self, data):
        self._d = data

    def to_dict(self):
        return self._d


@pytest.mark.parametrize("to", ["", "me", "empirebox2026@gmail.com", "rafa22giraldo@gmail.com",
                                "max@empirebox.store", "Rafael <RAFA22GIRALDO@gmail.com>"])
def test_voice_self_email_sends_immediately_no_pin(monkeypatch, to):
    import app.services.max.tool_executor as te
    calls = []

    def fake_execute(call, **kw):
        calls.append((call, kw))
        return _FakeResult({"tool": "send_email", "success": True, "result": {"sent_to": call["to"]}})

    monkeypatch.setattr(te, "execute_tool", fake_execute)
    out = vl.run_voice_tool("send_email", {"to": to, "subject": "Voice test", "body": "dry run"})
    assert out["success"] is True
    assert len(calls) == 1
    call, kw = calls[0]
    assert call["tool"] == "send_email" and call["subject"] == "Voice test"
    assert kw.get("founder") is False and kw.get("access_context") is None  # no PIN / confirm session
    assert "attachments" not in call


@pytest.mark.parametrize("args", [
    {"to": "client@example.com", "subject": "s", "body": "b"},
    {"to": "empirebox2026@gmail.com", "cc": "client@example.com", "subject": "s", "body": "b"},
    {"to": "empirebox2026@gmail.com", "cc": ["max@empirebox.store", "vendor@x.com"], "subject": "s", "body": "b"},
])
def test_voice_email_to_others_refused_before_executor(monkeypatch, args):
    import app.services.max.tool_executor as te
    called = []
    monkeypatch.setattr(te, "execute_tool", lambda *a, **k: called.append(a))
    out = vl.run_voice_tool("send_email", args)
    assert out["success"] is False
    assert "explicit yes" in out["error"] and "queue_for_founder_approval" in out["error"]
    assert called == []


def test_voice_send_email_schema_is_self_only():
    defs = {d["name"]: d for d in vl.realtime_tool_definitions()}
    assert "send_email" in defs
    desc = defs["send_email"]["description"]
    assert "empirebox2026@gmail.com" in desc and "refused" in desc
    assert "attachments" not in defs["send_email"]["parameters"]["properties"]


def test_voice_instructions_self_email_rule_and_no_settings_excuse():
    from app.services.max.voice_brain import VOICE_CAPABILITIES
    text = VOICE_CAPABILITIES
    assert "call send_email right away" in text and "No PIN" in text
    assert "never say you can't send email" in text
    assert "explicit yes" in text
    assert "You CANNOT send email" not in text
    static = vl.build_instructions()
    assert "send_email" in static


def test_voice_self_email_dry_run_through_real_executor(monkeypatch):
    """Real tool_executor + whitelist path; only the SMTP provider is stubbed."""
    import app.services.max.email_service as es
    sent = []

    class FakeSvc:
        is_configured = True
        last_message_id = "<dry-run@test>"

        def send(self, **kw):
            sent.append(kw)
            return True

    monkeypatch.setattr(es, "EmailService", FakeSvc)
    out = vl.run_voice_tool("send_email", {"subject": "Voice dry run", "body": "no real send"})
    assert out["success"] is True, out
    assert sent and sent[0]["to"] == "empirebox2026@gmail.com"
    assert out["result"]["message_id"] == "<dry-run@test>"
