"""AMP edition: switching, gating, Spanish, data root, allowlist, Max-e, businesses.

These tests never open the Workroom max/memory.md for writing.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


REPO_MEMORY = Path(__file__).resolve().parents[2] / "max" / "memory.md"


def _amp_env(monkeypatch, tmp_path, *, name="Max-e"):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ASSISTANT_NAME", name)
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("AMP_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("AMP_OWNER_USERNAME", "owner")


def _workroom_env(monkeypatch):
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.delenv("ASSISTANT_NAME", raising=False)
    monkeypatch.delenv("EMPIRE_DEFAULT_LOCALE", raising=False)
    monkeypatch.delenv("EMPIRE_DATA_DIR", raising=False)


def _client(monkeypatch, tmp_path) -> TestClient:
    _amp_env(monkeypatch, tmp_path)
    from app.middleware.edition_gate import amp_access_middleware
    from app.routers.amp import router as amp_router
    from app.routers.edition import router as edition_router

    app = FastAPI()
    app.middleware("http")(amp_access_middleware)

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    @app.post("/api/v1/drawings/generate")
    def drawings():
        return {"ok": True}

    @app.get("/api/v1/craftforge/designs")
    def craft():
        return {"ok": True}

    app.include_router(edition_router, prefix="/api/v1")
    app.include_router(amp_router, prefix="/api/v1/amp")
    # SocialForge router, so approval gating is the real one.
    from app.routers.socialforge import router as social_router
    app.include_router(social_router, prefix="/api/v1/socialforge")
    return TestClient(app)


def _owner():
    return {"X-User-Email": "owner@example.com"}


def _assert_no_prices(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"price", "price_cents", "amount", "rate"}:
                assert item is None, f"{key} must stay unset, got {item!r}"
            else:
                _assert_no_prices(item)
    elif isinstance(value, list):
        for item in value:
            _assert_no_prices(item)


def test_workroom_defaults_when_unset(monkeypatch):
    _workroom_env(monkeypatch)
    from app.edition import (
        assistant_name,
        default_locale,
        edition_name,
        edition_prompt_suffix,
        is_amp,
        module_enabled,
        prompt_identity_name,
        resolve_socialforge_root,
    )

    assert edition_name() == "workroom"
    assert is_amp() is False
    assert module_enabled("workroom") is True
    assert module_enabled("drawings") is True
    assert module_enabled("luxe") is True
    assert assistant_name() == "Max"
    assert prompt_identity_name() == "MAX"
    assert default_locale() == "en"
    assert edition_prompt_suffix() == ""
    assert str(resolve_socialforge_root()).endswith("empire-repo/backend/data/socialforge")


def test_edition_switches_to_amp(monkeypatch, tmp_path):
    _amp_env(monkeypatch, tmp_path)
    from app.edition import (
        assistant_name,
        default_locale,
        edition_manifest,
        edition_name,
        is_amp,
        module_enabled,
        prompt_identity_name,
    )

    assert edition_name() == "amp"
    assert is_amp() is True
    assert default_locale() == "es"
    assert assistant_name() == "Max-e"
    assert prompt_identity_name() == "Max-e"
    assert module_enabled("amp") is True
    assert module_enabled("crm") is True
    assert module_enabled("leadforge") is True
    assert module_enabled("socialforge") is True
    assert module_enabled("finance") is True
    assert module_enabled("workroom") is False
    assert module_enabled("craft") is False
    assert module_enabled("luxe") is False
    assert module_enabled("drawings") is False
    manifest = edition_manifest()
    assert manifest["default_locale"] == "es"
    assert manifest["assistant"]["name"] == "Max-e"
    assert "Juan Diego Giraldo" in manifest["assistant"]["persona"]
    assert manifest["product"]["also_known_as"] == "El Portal de la Alegría"


def test_module_gating_blocks_hidden_routes(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    denied = client.post("/api/v1/drawings/generate", headers=_owner())
    assert denied.status_code == 403
    assert "no disponible" in denied.json()["detail"]
    craft = client.get("/api/v1/craftforge/designs", headers=_owner())
    assert craft.status_code == 403
    # Shared edition manifest stays open.
    edition = client.get("/api/v1/edition")
    assert edition.status_code == 200
    assert edition.json()["edition"] == "amp"


def test_spanish_default_and_english_greeting(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    body = client.get("/api/v1/edition").json()
    assert body["default_locale"] == "es"
    assert body["greeting"].startswith("Hola, soy Max-e")
    assert "Juan Diego Giraldo" in body["greeting"]
    from app.edition import greeting
    assert greeting("en").startswith("Hi, I'm Max-e")


def test_max_e_is_separate_from_workroom_max(monkeypatch, tmp_path):
    before = REPO_MEMORY.read_bytes() if REPO_MEMORY.exists() else None
    _amp_env(monkeypatch, tmp_path)
    from app.edition import apply_edition_prompt, ensure_assistant_files, prompt_identity_name

    info = ensure_assistant_files()
    assert info["name"] == "Max-e"
    memory = Path(info["memory_path"])
    history = Path(info["history_path"])
    settings = Path(info["settings_path"])
    assert memory.is_file() and history.is_file() and settings.is_file()
    assert str(tmp_path) in str(memory)
    assert str(tmp_path) in str(history)
    assert str(tmp_path) in str(settings)
    assert "Max-e" in memory.read_text(encoding="utf-8")
    stored = json.loads(settings.read_text(encoding="utf-8"))
    assert stored["name"] == "Max-e"
    assert "Juan Diego Giraldo" in stored["persona"]
    assert stored["separate_from_workroom"] is True
    assert prompt_identity_name() == "Max-e"
    prompt = apply_edition_prompt("You are MAX — workroom base.")
    assert "Max-e" in prompt
    assert "INSTANCE ASSISTANT: Max-e" in prompt
    assert "max/memory.md" not in str(memory)
    if before is not None:
        assert REPO_MEMORY.read_bytes() == before
    # Workroom name does not follow this instance once the env is cleared.
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.delenv("ASSISTANT_NAME", raising=False)
    assert edition_name_after_clear() == "Max"


def edition_name_after_clear() -> str:
    from app.edition import assistant_name, edition_prompt_suffix, prompt_identity_name
    assert prompt_identity_name() == "MAX"
    assert edition_prompt_suffix() == ""
    return assistant_name()


def test_data_root_isolation(monkeypatch, tmp_path):
    _amp_env(monkeypatch, tmp_path)
    from app.edition import EditionPathError, assert_under_root, ensure_assistant_files
    from app.services import amp_allowlist, amp_businesses

    ensure_assistant_files()
    amp_allowlist.load_allowlist()
    amp_businesses.ensure_default_business()
    created = amp_businesses.create_business(name="Taller Norte", industry="datos", description="En blanco")
    note = amp_businesses.write_generated_note(created["slug"], "Prep", "Sesión sin precio.")
    assert "Max-e" in note.read_text(encoding="utf-8")

    for path in tmp_path.rglob("*"):
        if path.is_file():
            assert_under_root(path, tmp_path)

    with pytest.raises(EditionPathError):
        assert_under_root(Path("/tmp/outside-amp-instance.txt"), tmp_path)


def test_allowlist_allow_and_deny(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    denied = client.get("/api/v1/businesses")
    assert denied.status_code == 403
    body = denied.json()
    assert body["code"] == "sin_acceso"
    assert "Sin acceso" in body["detail"]

    health = client.get("/health")
    assert health.status_code == 200

    stranger = client.get("/api/v1/businesses", headers={"X-User-Email": "nobody@example.com"})
    assert stranger.status_code == 403
    assert "Sin acceso" in stranger.json()["detail"]

    allowed = client.get("/api/v1/businesses", headers=_owner())
    assert allowed.status_code == 200
    slugs = [row["slug"] for row in allowed.json()["businesses"]]
    assert "amp" in slugs

    added = client.post(
        "/api/v1/amp/allowlist",
        headers=_owner(),
        json={"email": "juan@example.com", "role": "member"},
    )
    assert added.status_code == 200
    as_juan = client.get("/api/v1/businesses", headers={"X-User-Email": "juan@example.com"})
    assert as_juan.status_code == 200
    # A member cannot administer the list.
    forbidden = client.get("/api/v1/amp/allowlist", headers={"X-User-Email": "juan@example.com"})
    assert forbidden.status_code == 403


def test_allowlist_cli(monkeypatch, tmp_path):
    _amp_env(monkeypatch, tmp_path)
    import os
    import subprocess
    import sys
    from app.services import amp_allowlist

    script = Path(__file__).resolve().parents[1] / "scripts" / "amp_allowlist.py"
    env = os.environ.copy()
    added = subprocess.run(
        [sys.executable, str(script), "add", "--username", "lina"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert added.returncode == 0, added.stderr
    listed = subprocess.run(
        [sys.executable, str(script), "list"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert listed.returncode == 0, listed.stderr
    assert "lina" in listed.stdout
    assert amp_allowlist.is_allowed(username="lina")
    assert amp_allowlist.is_allowed(email="owner@example.com")
    assert not amp_allowlist.is_allowed(email="nope@example.com")


def test_blank_business_and_isolation(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    blank = client.post(
        "/api/v1/businesses",
        headers=_owner(),
        json={"name": "Norte Datos", "industry": "Datos", "description": "Espacio en blanco"},
    )
    assert blank.status_code == 200, blank.text
    created = blank.json()
    assert created["template"] is None
    assert created["industry_modules"] == []
    for module in ("crm", "leadforge", "socialforge", "quotes", "scheduling", "finance"):
        assert module in created["modules"]
    for hidden in ("workroom", "craftforge", "luxeforge", "drawings"):
        assert hidden not in created["modules"]
    _assert_no_prices(created)
    assert created["service_categories"] == []

    other = client.post(
        "/api/v1/businesses",
        headers=_owner(),
        json={"name": "Mapas del Valle", "industry": "GIS", "description": "Otra empresa"},
    )
    assert other.status_code == 200
    slug_a = created["slug"]
    slug_b = other.json()["slug"]
    assert slug_a != slug_b

    added = client.post(
        f"/api/v1/businesses/{slug_a}/contacts",
        headers={**_owner(), "X-Empire-Business": slug_a},
        json={"name": "Ana Ruiz", "email": "ana@example.com"},
    )
    assert added.status_code == 200
    only_a = client.get(f"/api/v1/businesses/{slug_a}/contacts", headers=_owner())
    only_b = client.get(f"/api/v1/businesses/{slug_b}/contacts", headers=_owner())
    assert any(row["name"] == "Ana Ruiz" for row in only_a.json()["contacts"])
    assert only_b.json()["contacts"] == []

    dir_a = tmp_path / "businesses" / slug_a
    dir_b = tmp_path / "businesses" / slug_b
    assert (dir_a / "workspace.db").is_file()
    assert (dir_b / "workspace.db").is_file()
    assert dir_a.resolve() != dir_b.resolve()
    assert str(tmp_path) in str(dir_a.resolve())


def test_templates_have_no_prices(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    templates = client.get("/api/v1/businesses/templates", headers=_owner())
    assert templates.status_code == 200
    ids = {row["id"] for row in templates.json()["templates"]}
    assert {"ciberseguridad", "datos_bi", "gis", "redes_voip", "erp_crm"} <= ids
    _assert_no_prices(templates.json())

    created = client.post(
        "/api/v1/businesses",
        headers=_owner(),
        json={"name": "Seguridad Andina", "industry": "", "description": "", "template": "ciberseguridad"},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["service_categories"]
    assert any(row["key"] == "activos_criticos" for row in body["crm_fields"])
    _assert_no_prices(body)
    assert all(row["price"] is None for row in body["service_categories"])


def test_coaching_catalog_has_no_prices(monkeypatch, tmp_path):
    _amp_env(monkeypatch, tmp_path)
    from app.services.amp_businesses import COACHING_PACKAGES, ensure_default_business
    ensure_default_business()
    assert all(package["price"] is None for package in COACHING_PACKAGES)
    profile = json.loads((tmp_path / "businesses" / "amp" / "business.json").read_text(encoding="utf-8"))
    assert profile["coach"] == "Juan Diego Giraldo"
    _assert_no_prices(profile)
    fields = {row["key"] for row in profile["coachee_fields"]}
    assert {"metas", "historial_sesiones", "notas_progreso"} <= fields


def test_content_course_audio_and_mood(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    item = client.post(
        "/api/v1/amp/content",
        headers=_owner(),
        json={
            "type": "meditation",
            "title": "Calma de la mañana",
            "theme": "calma",
            "duration_seconds": 300,
            "premium": False,
        },
    )
    assert item.status_code == 200, item.text
    assert item.json()["type"] == "meditation"
    assert item.json()["theme"] == "calma"
    assert "price" not in item.json()

    course = client.post(
        "/api/v1/amp/courses",
        headers=_owner(),
        json={
            "title": "Portal de la Alegría",
            "description": "Programa de dos semanas",
            "theme": "bienestar",
            "weeks": [
                {"week_number": 1, "title": "Semana 1", "theme": "calma", "lessons": [
                    {"title": "Respirar", "duration_seconds": 600}
                ]},
                {"week_number": 2, "title": "Semana 2", "theme": "gratitud", "lessons": [
                    {"title": "Agradecer", "duration_seconds": 600}
                ]},
            ],
        },
    )
    assert course.status_code == 200, course.text
    assert len(course.json()["weeks"]) == 2
    assert len(course.json()["lessons"]) == 2

    audio = client.post(
        "/api/v1/amp/audio",
        headers=_owner(),
        files={"file": ("meditacion.mp3", b"not-a-real-mp3", "audio/mpeg")},
    )
    assert audio.status_code == 200, audio.text
    stored = Path(audio.json()["path"])
    assert stored.is_file()
    assert str(tmp_path) in str(stored.resolve())
    streamed = client.get(audio.json()["stream_url"], headers=_owner())
    assert streamed.status_code == 200
    assert streamed.content == b"not-a-real-mp3"

    signup = client.post(
        "/api/v1/amp/signup",
        headers=_owner(),
        json={"name": "Ana", "email": "ana@example.com", "password": "clave-segura"},
    )
    assert signup.status_code == 200, signup.text
    token = signup.json()["token"]
    mood = client.post(
        "/api/v1/amp/moods",
        headers={**_owner(), "Authorization": f"Bearer {token}"},
        json={"mood": "ansioso", "emoji": "😟", "date": "2026-10-01"},
    )
    assert mood.status_code == 200, mood.text
    assert mood.json()["kind"] == "daily_checkin"
    again = client.post(
        "/api/v1/amp/moods",
        headers={**_owner(), "Authorization": f"Bearer {token}"},
        json={"mood": "en_paz", "date": "2026-10-01"},
    )
    assert again.status_code == 200
    listing = client.get(
        "/api/v1/amp/moods",
        headers={**_owner(), "Authorization": f"Bearer {token}"},
    )
    days = [row["date"] for row in listing.json()]
    assert days.count("2026-10-01") == 1


def test_social_requires_approval_on_amp(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    created = client.post(
        "/api/v1/socialforge/posts",
        headers=_owner(),
        json={"platform": "instagram", "content": "Borrador", "status": "posted"},
    )
    assert created.status_code == 200, created.text
    assert created.json()["status"] == "pending_approval"
    from app.edition import resolve_socialforge_root
    root = resolve_socialforge_root()
    assert str(tmp_path) in str(root.resolve())
    assert (root / "posts").is_dir()
    live = client.post(
        "/api/v1/socialforge/post/instagram",
        headers=_owner(),
        json={"caption": "no debe salir"},
    )
    assert live.status_code == 403
    assert "Sin aprobación" in live.json()["detail"]
