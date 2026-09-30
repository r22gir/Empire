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
    assert names == ["search_quotes", "get_quote", "search_contacts"]
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
