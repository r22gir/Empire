"""Mocked Simli compose API. No live network and no secrets in responses."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import simli_avatar as simli_router
from app.services.max import simli_avatar as simli

FAKE_KEY = "test-simli-key"
FAKE_FACE = "test-face-workroom"
FAKE_TOKEN = "test-session-token"


class _Resp:
    def __init__(self, payload, status_code=200):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def _no_secret(payload) -> None:
    blob = json.dumps(payload)
    assert FAKE_KEY not in blob
    assert FAKE_FACE not in blob
    assert "test-face-maxine" not in blob
    assert "test-face-maxe" not in blob


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    for name in (
        "SIMLI_API_KEY",
        "SIMLI_FACE_ID",
        "SIMLI_FACE_ID_WORKROOM",
        "SIMLI_FACE_ID_MAX_E",
        "SIMLI_FACE_ID_MAXINE",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(simli, "_usage_path", lambda: tmp_path / "simli_usage.json")


def _enable(monkeypatch, face_name="SIMLI_FACE_ID", face=FAKE_FACE):
    monkeypatch.setenv("SIMLI_API_KEY", FAKE_KEY)
    monkeypatch.setenv(face_name, face)


def test_unset_falls_back_without_http():
    called = {"n": 0}

    def boom(*_a, **_k):
        called["n"] += 1
        raise AssertionError("Simli HTTP must not run when unset")

    status = simli.simli_status("workroom")
    assert status["enabled"] is False
    assert status["status"] == "disabled"
    assert status["renderer"] == "talkinghead"
    assert status["fallback"] == "talkinghead"
    assert "SIMLI_API_KEY" in status["missing"]
    assert "SIMLI_FACE_ID" in status["missing"]
    assert "TalkingHead" in status["reason"]
    assert status["max_session_length"] == 600
    assert status["max_idle_time"] == 60
    assert status["face_id_set"] is False
    assert status["talkinghead_placeholder"]["license"] == "CC BY-NC 4.0"
    assert status["talkinghead_placeholder"]["body"] == "M"
    assert status["talkinghead_placeholder"]["commercial_use"] is False
    assert status["edition_avatar"]["placeholder"] is True
    assert status["edition_avatar"]["installed"] is False
    _no_secret(status)

    result = asyncio.run(simli.create_session("workroom", http_post=boom, http_get=boom))
    assert called["n"] == 0
    assert result["session_token"] == ""
    assert result["ice_servers"] == []
    assert result["renderer"] == "talkinghead"
    _no_secret(result)


def test_session_mints_token_with_spend_caps(monkeypatch):
    _enable(monkeypatch)
    seen = {}

    def post(url, body, headers):
        seen["url"] = url
        seen["body"] = body
        seen["key"] = headers.get("x-simli-api-key")
        return _Resp({"session_token": FAKE_TOKEN, "api_key": "should-not-pass-through"})

    def get(url, headers):
        seen["ice_url"] = url
        assert headers.get("x-simli-api-key") == FAKE_KEY
        return _Resp({"iceServers": [{"urls": "stun:example.invalid:19302"}]})

    result = asyncio.run(simli.create_session("workroom", http_post=post, http_get=get))
    assert seen["url"] == simli.TOKEN_URL
    assert seen["ice_url"] == simli.ICE_URL
    assert seen["key"] == FAKE_KEY
    body = seen["body"]
    assert body["faceId"] == FAKE_FACE
    assert body["apiVersion"] == "v2"
    assert body["maxSessionLength"] == 600
    assert body["maxIdleTime"] == 60
    assert body["audioInputFormat"] == "pcm16"
    assert result["enabled"] is True
    assert result["renderer"] == "simli"
    assert result["session_token"] == FAKE_TOKEN
    assert result["webrtc_url"] == simli.WEBRTC_URL
    assert result["ice_servers"][0]["urls"] == "stun:example.invalid:19302"
    assert result["audio_source"] == "max_tts_and_live_voice"
    assert "api_key" not in result
    _no_secret(result)


def test_http_failure_falls_back(monkeypatch):
    _enable(monkeypatch)

    def post(_url, _body, _headers):
        return _Resp({"error": "no"}, 401)

    result = asyncio.run(simli.create_session("workroom", http_post=post, http_get=post))
    assert result["enabled"] is False
    assert result["renderer"] == "talkinghead"
    assert result["session_token"] == ""
    assert "TalkingHead" in result["reason"]
    _no_secret(result)


def test_missing_token_falls_back(monkeypatch):
    _enable(monkeypatch)

    def post(_url, _body, _headers):
        return _Resp({})

    def get(_url, _headers):
        return _Resp({"iceServers": [{"urls": "stun:example.invalid:19302"}]})

    result = asyncio.run(simli.create_session("workroom", http_post=post, http_get=get))
    assert result["session_token"] == ""
    assert result["renderer"] == "talkinghead"
    assert "session token" in result["reason"]
    _no_secret(result)


def test_per_edition_face_env(monkeypatch):
    monkeypatch.setenv("SIMLI_FACE_ID_MAXINE", "test-face-maxine")
    monkeypatch.setenv("SIMLI_FACE_ID_MAX_E", "test-face-maxe")
    monkeypatch.setenv("SIMLI_FACE_ID", FAKE_FACE)

    assert simli.face_env_name("maxine") == "SIMLI_FACE_ID_MAXINE"
    assert simli.face_env_name("max-e") == "SIMLI_FACE_ID_MAX_E"
    assert simli.normalize_edition("maxe") == "max_e"
    maxine = simli.simli_status("maxine")
    assert maxine["face_env"] == "SIMLI_FACE_ID_MAXINE"
    assert maxine["face_id_set"] is True
    assert "SIMLI_API_KEY" in maxine["missing"]
    assert maxine["edition_avatar"]["glb"] == "/avatars/maxine.glb"
    assert maxine["edition_avatar"]["body"] == "F"
    assert maxine["edition_avatar"]["installed"] is False
    workroom = simli.simli_status("workroom")
    assert workroom["face_env"] == "SIMLI_FACE_ID"
    assert workroom["edition_avatar"]["body"] == "M"
    _no_secret(maxine)
    _no_secret(workroom)

    seen = {}

    def post(_url, body, headers):
        seen["face"] = body["faceId"]
        seen["key"] = headers.get("x-simli-api-key")
        return _Resp({"session_token": FAKE_TOKEN})

    def get(_url, _headers):
        return _Resp({})

    monkeypatch.setenv("SIMLI_API_KEY", FAKE_KEY)
    monkeypatch.setenv("SIMLI_FACE_ID_WORKROOM", "test-face-alias")
    result = asyncio.run(simli.create_session("workroom", http_post=post, http_get=get))
    assert seen["face"] == "test-face-alias"
    assert seen["key"] == FAKE_KEY
    assert "test-face-alias" not in json.dumps(result)


def test_usage_card_caps_minutes(monkeypatch):
    import app.services.max.token_tracker as tracker

    monkeypatch.setattr(tracker.token_tracker, "log_usage", lambda **_k: None)
    first = simli.record_usage("workroom", 900, "test")
    assert first["seconds"] == 600
    assert first["capped"] is True
    assert first["minutes"] == 10.0
    simli.record_usage("maxine", 30, "test")
    card = simli.usage_card("workroom")
    assert card["seconds"] == 600
    assert card["minutes"] == 10.0
    assert card["sessions"] == 1
    everything = simli.usage_card(None)
    assert everything["edition"] == "all"
    assert everything["sessions"] == 2
    assert everything["seconds"] == 630


def test_router_status_session_and_usage(monkeypatch):
    import app.services.max.token_tracker as tracker

    monkeypatch.setattr(tracker.token_tracker, "log_usage", lambda **_k: None)
    app = FastAPI()
    app.include_router(simli_router.router, prefix="/api/v1")
    client = TestClient(app)

    status = client.get("/api/v1/avatar/simli/status", params={"edition": "workroom"})
    assert status.status_code == 200
    body = status.json()
    assert body["renderer"] == "talkinghead"
    assert body["enabled"] is False
    _no_secret(body)

    session = client.post("/api/v1/avatar/simli/session", json={"edition": "workroom"})
    assert session.status_code == 200
    assert session.json()["session_token"] == ""
    assert session.json()["renderer"] == "talkinghead"

    logged = client.post(
        "/api/v1/avatar/simli/usage",
        json={"edition": "workroom", "seconds": 90, "source": "test"},
    )
    assert logged.status_code == 200
    assert logged.json()["seconds"] == 90
    card = client.get("/api/v1/avatar/simli/usage", params={"edition": "workroom"})
    assert card.json()["minutes"] == 1.5
    assert card.json()["sessions"] == 1
    _no_secret(card.json())


def test_router_is_loaded_in_main():
    text = (Path(__file__).resolve().parents[1] / "app" / "main.py").read_text(encoding="utf-8")
    assert 'load_router("app.routers.simli_avatar", "/api/v1", ["simli"])' in text


def test_avatar_html_edition_and_placeholder_contract():
    root = Path(__file__).resolve().parents[2] / "empire-command-center" / "public"
    html = (root / "avatar.html").read_text(encoding="utf-8")
    assert "CC BY-NC 4.0" in html
    assert "brunette" in html
    assert "edition" in html
    assert "body: 'M'" in html
    assert "/avatars/workroom.glb" in html
    assert "/avatars/maxine.glb" in html
    assert "body: 'F'" in html
    assert "startSimliFace" in html
    assert "live-pcm" in html
    client = (root / "simli-face.js").read_text(encoding="utf-8")
    assert "x-simli-api-key" not in client
    assert "SIMLI_API_KEY" not in client
    assert "/avatar/simli/session" in client
    screen = (
        Path(__file__).resolve().parents[2]
        / "empire-command-center"
        / "app"
        / "components"
        / "screens"
        / "PresentationScreen.tsx"
    ).read_text(encoding="utf-8")
    assert "/avatar.html?edition=workroom" in screen
    assert "max-live-pcm" in screen
    assert "Simli off — TalkingHead" in screen
    page = (
        Path(__file__).resolve().parents[2]
        / "empire-command-center"
        / "app"
        / "max"
        / "page.tsx"
    ).read_text(encoding="utf-8")
    assert "MaxAvatarFrame" in page
    assert 'src="/avatar.html"' not in page
