"""Family first-login welcome: per-user /data store, no edition leaks."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


REPO = Path(__file__).resolve().parents[2]
AMP_SEED = REPO / "deploy" / "seeds" / "amp-welcome.json"
MAXINE_SEED = REPO / "deploy" / "seeds" / "maxine-welcome.json"
LIB_AMP = REPO / "empire-command-center" / "app" / "lib" / "welcome" / "amp.json"
LIB_MAXINE = REPO / "empire-command-center" / "app" / "lib" / "welcome" / "maxine.json"
HELP_MENU = REPO / "empire-command-center" / "app" / "components" / "voice" / "HelpMenu.tsx"
AYUDA = REPO / "empire-command-center" / "app" / "ayuda" / "page.tsx"
LAYOUT = REPO / "empire-command-center" / "app" / "layout.tsx"


def _env(monkeypatch, tmp_path, edition="amp"):
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Maxine" if edition == "maxine" else "Max-e")
    monkeypatch.setenv("AMP_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("AMP_JWT_SECRET", "test-secret")
    monkeypatch.delenv("FOUNDER_EMAIL", raising=False)


def _client():
    from app.middleware.edition_gate import amp_access_middleware
    from app.routers.family_welcome import router as welcome_router

    app = FastAPI()
    app.middleware("http")(amp_access_middleware)
    app.include_router(welcome_router, prefix="/api/v1")
    return TestClient(app)


def _cookie(client, email="owner@example.com"):
    from app.services.amp_access import SESSION_COOKIE, create_session_token
    client.cookies.set(SESSION_COOKIE, create_session_token(email))


def test_seeds_and_lib_match_and_have_six_spanish_slides():
    amp = json.loads(AMP_SEED.read_text(encoding="utf-8"))
    maxine = json.loads(MAXINE_SEED.read_text(encoding="utf-8"))
    assert amp == json.loads(LIB_AMP.read_text(encoding="utf-8"))
    assert maxine == json.loads(LIB_MAXINE.read_text(encoding="utf-8"))
    assert amp["assistant"] == "Max-e"
    assert maxine["assistant"] == "Maxine"
    assert len(amp["slides"]) == 6
    assert len(maxine["slides"]) == 6
    assert amp["interval_ms"] == 8000
    assert "Hola, soy Max-e" in amp["slides"][0]["title"]
    assert "Hola, soy Maxine" in maxine["slides"][0]["title"]
    assert "hermanos" in amp["slides"][1]["body"]
    assert "Pedir ayuda a Max" in amp["slides"][3]["body"]
    assert "20%" in amp["slides"][4]["body"]
    assert "Ver bienvenida" in amp["slides"][5]["body"]
    from app.services.family_welcome import deck_has_leak
    assert deck_has_leak(amp) == []
    assert deck_has_leak(maxine) == []


def test_first_login_shows_then_marks_seen_per_user(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.amp_allowlist import add_entry
    add_entry(email="juan@example.com", role="owner")
    add_entry(email="otro@example.com", role="member")
    client = _client()
    assert client.get("/api/v1/welcome").status_code == 403
    _cookie(client, "juan@example.com")
    first = client.get("/api/v1/welcome")
    assert first.status_code == 200
    body = first.json()
    assert body["show"] is True
    assert body["seen"] is False
    assert body["edition"] == "amp"
    assert body["assistant"] == "Max-e"
    assert len(body["slides"]) == 6
    assert "users" not in body
    assert "email" not in body
    marked = client.post("/api/v1/welcome/seen")
    assert marked.status_code == 200
    assert marked.json()["seen"] is True
    second = client.get("/api/v1/welcome")
    assert second.json()["show"] is False
    assert second.json()["seen"] is True
    assert len(second.json()["slides"]) == 6
    store = json.loads((tmp_path / "welcome" / "seen.json").read_text(encoding="utf-8"))
    assert store["edition"] == "amp"
    assert store["users"]["juan@example.com"]["seen"] is True
    assert "camilo@example.com" not in store["users"]

    _cookie(client, "otro@example.com")
    other = client.get("/api/v1/welcome")
    assert other.json()["show"] is True
    assert other.json()["seen"] is False


def test_seen_does_not_leak_across_editions(monkeypatch, tmp_path):
    amp_dir = tmp_path / "amp"
    maxine_dir = tmp_path / "maxine"
    _env(monkeypatch, amp_dir, "amp")
    from app.services import family_welcome

    family_welcome.mark_seen("juan@example.com")
    assert family_welcome.has_seen("juan@example.com") is True
    amp_store = json.loads((amp_dir / "welcome" / "seen.json").read_text(encoding="utf-8"))
    assert amp_store["edition"] == "amp"
    assert "juan@example.com" in amp_store["users"]

    _env(monkeypatch, maxine_dir, "maxine")
    assert family_welcome.has_seen("juan@example.com") is False
    family_welcome.mark_seen("camilo@example.com")
    maxine_store = json.loads((maxine_dir / "welcome" / "seen.json").read_text(encoding="utf-8"))
    assert maxine_store["edition"] == "maxine"
    assert "camilo@example.com" in maxine_store["users"]
    assert "juan@example.com" not in maxine_store["users"]
    amp_again = json.loads((amp_dir / "welcome" / "seen.json").read_text(encoding="utf-8"))
    assert "camilo@example.com" not in amp_again["users"]
    assert (tmp_path / "workroom").exists() is False


def test_workroom_and_founder_never_get_welcome(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "workroom"))
    monkeypatch.delenv("ASSISTANT_NAME", raising=False)
    client = _client()
    _cookie(client)
    missing = client.get("/api/v1/welcome")
    assert missing.status_code == 404
    assert client.post("/api/v1/welcome/seen").status_code == 404
    assert not (tmp_path / "workroom" / "welcome").exists()
    from app.edition import EditionPathError
    from app.services import family_welcome
    try:
        family_welcome.load_deck()
        raise AssertionError("workroom must not load a family welcome deck")
    except EditionPathError:
        pass


def test_data_dir_override_swaps_rafael_deck(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "maxine")
    override = tmp_path / "welcome" / "slides.json"
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text(json.dumps({
        "deck_version": 2,
        "interval_ms": 9000,
        "slides": [
            {"id": "custom", "title": "Nueva lámina", "body": "Texto de Rafael.", "image": "/welcome/maxine/01.jpg"},
            {"id": "bad", "title": "Leak", "body": "x", "image": "https://evil.example/x.png"},
        ],
    }, ensure_ascii=False), encoding="utf-8")
    from app.services import family_welcome
    deck = family_welcome.load_deck()
    assert deck["assistant"] == "Maxine"
    assert deck["interval_ms"] == 9000
    assert deck["slides"][0]["image"] == "/welcome/maxine/01.jpg"
    assert deck["slides"][1]["image"] is None


def test_help_menu_and_layout_wire_replay():
    help_menu = HELP_MENU.read_text(encoding="utf-8")
    ayuda = AYUDA.read_text(encoding="utf-8")
    layout = LAYOUT.read_text(encoding="utf-8")
    assert "Ver bienvenida" in help_menu or "FamilyWelcomeReplayButton" in help_menu
    assert "FamilyWelcomeReplayButton" in ayuda
    assert "FamilyWelcomeHost" in layout
    overlay = (REPO / "empire-command-center" / "app" / "components" / "family" / "FamilyWelcomeOverlay.tsx").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in (REPO / "empire-command-center" / "app" / "components" / "family" / "familyWelcome.css").read_text(encoding="utf-8")
    assert "Saltar" in overlay
    assert "Saltar / Skip" in overlay
    assert "max-width: 720px" in (REPO / "empire-command-center" / "app" / "components" / "family" / "familyWelcome.css").read_text(encoding="utf-8")
