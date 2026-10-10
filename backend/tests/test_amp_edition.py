"""AMP edition: switching, gating, Spanish, data root, allowlist, Max-e, businesses.

These tests never open the Workroom max/memory.md for writing.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient


REPO_MEMORY = Path(__file__).resolve().parents[2] / "max" / "memory.md"


def _amp_env(monkeypatch, tmp_path, *, name="Max-e"):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ASSISTANT_NAME", name)
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("AMP_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("AMP_OWNER_USERNAME", "owner")
    monkeypatch.setenv("AMP_JWT_SECRET", "test-amp-jwt-secret")
    monkeypatch.setenv("AMP_PUBLIC_BASE_URL", "http://127.0.0.1:8011")


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

    @app.get("/api/v1/whoami")
    def whoami(request: Request):
        return {
            "x_user_email": request.headers.get("x-user-email"),
            "x_user_name": request.headers.get("x-user-name"),
            "cf_user_email": request.headers.get("cf-access-authenticated-user-email"),
            "email": getattr(request.state, "amp_email", None),
            "via": getattr(request.state, "amp_auth_via", None),
        }

    app.include_router(edition_router, prefix="/api/v1")
    app.include_router(amp_router, prefix="/api/v1/amp")
    # SocialForge router, so approval gating is the real one.
    from app.routers.socialforge import router as social_router
    app.include_router(social_router, prefix="/api/v1/socialforge")
    return TestClient(app)


def _session(email="owner@example.com"):
    from app.services.amp_access import create_session_token
    return {"Authorization": f"Bearer {create_session_token(email)}"}


def _owner():
    return _session("owner@example.com")


def _cookie(client, email="owner@example.com"):
    from app.services.amp_access import SESSION_COOKIE, create_session_token
    client.cookies.set(SESSION_COOKIE, create_session_token(email))


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


def test_spanish_news_question_triggers_search(monkeypatch, tmp_path):
    _amp_env(monkeypatch, tmp_path)
    from app.services.max.factual_guard import is_factual_question
    from app.services.max.search_context import build_search_query

    assert is_factual_question("Que paso en Panama")
    assert is_factual_question("Max-e, qué pasó en Panamá")
    assert is_factual_question("noticias de hoy")
    assert is_factual_question("cuanto esta el dolar hoy")
    query = build_search_query("Que paso en Panama")["query"].lower()
    assert "panama" in query or "panamá" in query
    assert "hoy" in query


def test_casual_spanish_does_not_trigger_search(monkeypatch, tmp_path):
    _amp_env(monkeypatch, tmp_path)
    from app.services.max.factual_guard import is_factual_question

    for message in (
        "hoy no puedo",
        "voy a casa hoy",
        "como puedo ayudarte",
        "que es eso",
        "por que no funciona",
        "buenos dias, que tal hoy",
    ):
        assert not is_factual_question(message), message


def test_gate_rejects_anonymous_requests_when_amp(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    for path in ("/api/v1/whoami", "/api/v1/businesses", "/api/v1/amp/content"):
        denied = client.get(path)
        assert denied.status_code == 403, path
        body = denied.json()
        assert body["code"] == "sin_acceso"
        assert "Sin acceso" in body["detail"]
    open_health = client.get("/health")
    assert open_health.status_code == 200


def test_family_prompt_asks_for_short_spanish_and_search_first(monkeypatch, tmp_path):
    _amp_env(monkeypatch, tmp_path)
    from app.edition import edition_prompt_suffix

    suffix = edition_prompt_suffix()
    assert "Responde en español" in suffix
    assert "2 a 5 oraciones" in suffix
    assert "una sola pregunta" in suffix
    assert "busca primero" in suffix


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
    as_juan = client.get("/api/v1/businesses", headers=_session("juan@example.com"))
    assert as_juan.status_code == 200
    # A member cannot administer the list. The email header does not grant admin.
    forbidden = client.get("/api/v1/amp/allowlist", headers=_session("juan@example.com"))
    assert forbidden.status_code == 403
    spoofed_admin = client.get(
        "/api/v1/amp/allowlist",
        headers={**_session("juan@example.com"), "X-User-Email": "owner@example.com"},
    )
    assert spoofed_admin.status_code == 403


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
    # The content-account bearer is not an edition session. The cookie is.
    _cookie(client)
    mood = client.post(
        "/api/v1/amp/moods",
        headers={"Authorization": f"Bearer {token}"},
        json={"mood": "ansioso", "emoji": "😟", "date": "2026-10-01"},
    )
    assert mood.status_code == 200, mood.text
    assert mood.json()["kind"] == "daily_checkin"
    again = client.post(
        "/api/v1/amp/moods",
        headers={"Authorization": f"Bearer {token}"},
        json={"mood": "en_paz", "date": "2026-10-01"},
    )
    assert again.status_code == 200
    listing = client.get(
        "/api/v1/amp/moods",
        headers={"Authorization": f"Bearer {token}"},
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


def test_spoofed_identity_header_is_denied(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    spoofed = client.get(
        "/api/v1/businesses",
        headers={
            "X-User-Email": "owner@example.com",
            "X-User-Name": "owner",
            "Cf-Access-Authenticated-User-Email": "owner@example.com",
        },
    )
    assert spoofed.status_code == 403
    assert spoofed.json()["code"] == "sin_acceso"


def test_valid_session_cookie_is_allowed_and_strips_headers(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    _cookie(client, "owner@example.com")
    allowed = client.get(
        "/api/v1/businesses",
        headers={"X-User-Email": "nobody@example.com", "X-User-Name": "nobody"},
    )
    assert allowed.status_code == 200
    who = client.get(
        "/api/v1/whoami",
        headers={
            "X-User-Email": "nobody@example.com",
            "Cf-Access-Authenticated-User-Email": "nobody@example.com",
        },
    )
    assert who.status_code == 200
    body = who.json()
    assert body["email"] == "owner@example.com"
    assert body["via"] == "session"
    assert body["x_user_email"] is None
    assert body["cf_user_email"] is None


def test_invalid_and_expired_session_are_denied(monkeypatch, tmp_path):
    import time
    from jose import jwt as jose_jwt

    client = _client(monkeypatch, tmp_path)
    from app.services.amp_access import SESSION_COOKIE

    client.cookies.set(SESSION_COOKIE, "not-a-token")
    invalid = client.get("/api/v1/businesses")
    assert invalid.status_code == 403
    assert invalid.json()["code"] == "sin_acceso"

    expired = jose_jwt.encode(
        {
            "email": "owner@example.com",
            "purpose": "amp_access",
            "aud": "amp-access",
            "exp": int(time.time()) - 60,
        },
        "test-amp-jwt-secret",
        algorithm="HS256",
    )
    client.cookies.set(SESSION_COOKIE, expired)
    denied = client.get("/api/v1/businesses")
    assert denied.status_code == 403

    # A content-account token signed with the same secret is not an edition session.
    other = jose_jwt.encode(
        {"sub": "user-1", "email": "owner@example.com", "exp": int(time.time()) + 3600},
        "test-amp-jwt-secret",
        algorithm="HS256",
    )
    client.cookies.clear()
    bearer = client.get("/api/v1/businesses", headers={"Authorization": f"Bearer {other}"})
    assert bearer.status_code == 403


def test_login_code_sets_secure_cookie_and_does_not_email(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    sent = {}

    def _no_send(*args, **kwargs):
        sent["called"] = True
        raise AssertionError("mail must not be sent when SMTP is unset")

    monkeypatch.setattr("app.services.amp_access.try_send_login_email", _no_send)
    asked = client.post("/api/v1/amp/auth/request", json={"email": "owner@example.com"})
    assert asked.status_code == 200
    assert "code" not in asked.json()
    assert "token" not in asked.json()
    assert "called" not in sent

    from app.services.amp_access import issue_login_challenge
    issued = issue_login_challenge("owner@example.com", with_code=True)
    verified = client.post(
        "/api/v1/amp/auth/verify",
        json={"email": "owner@example.com", "code": issued["code"]},
    )
    assert verified.status_code == 200, verified.text
    cookie = verified.headers.get("set-cookie", "")
    assert "amp_session=" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    replay = client.post(
        "/api/v1/amp/auth/verify",
        json={"email": "owner@example.com", "code": issued["code"]},
    )
    assert replay.status_code == 403


def _rsa_keypair():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from jose.utils import long_to_base64

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    pub = key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "kid": "test",
        "alg": "RS256",
        "use": "sig",
        "n": long_to_base64(pub.n).decode(),
        "e": long_to_base64(pub.e).decode(),
    }
    return pem, jwk


def test_cloudflare_jwt_allowed_only_when_email_is_allowlisted(monkeypatch, tmp_path):
    import time
    from jose import jwt as jose_jwt

    client = _client(monkeypatch, tmp_path)
    monkeypatch.setenv("CF_ACCESS_TEAM_DOMAIN", "amp-team.cloudflareaccess.com")
    monkeypatch.setenv("CF_ACCESS_AUD", "test-aud")
    pem, jwk = _rsa_keypair()
    monkeypatch.setattr(
        "app.services.amp_access.fetch_access_certs",
        lambda host: {"keys": [jwk]},
    )

    def token(email, *, aud="test-aud", exp_delta=300):
        now = int(time.time())
        return jose_jwt.encode(
            {
                "aud": [aud],
                "iss": "https://amp-team.cloudflareaccess.com",
                "email": email,
                "iat": now,
                "exp": now + exp_delta,
            },
            pem,
            algorithm="RS256",
            headers={"kid": "test"},
        )

    allowed = client.get(
        "/api/v1/businesses",
        headers={
            "Cf-Access-Jwt-Assertion": token("owner@example.com"),
            "X-User-Email": "nobody@example.com",
        },
    )
    assert allowed.status_code == 200, allowed.text
    who = client.get(
        "/api/v1/whoami",
        headers={"Cf-Access-Jwt-Assertion": token("owner@example.com")},
    )
    assert who.json()["email"] == "owner@example.com"
    assert who.json()["via"] == "cloudflare"
    assert who.json()["x_user_email"] is None

    stranger = client.get(
        "/api/v1/businesses",
        headers={"Cf-Access-Jwt-Assertion": token("nobody@example.com")},
    )
    assert stranger.status_code == 403
    assert stranger.json()["code"] == "sin_acceso"

    bad_aud = client.get(
        "/api/v1/businesses",
        headers={"Cf-Access-Jwt-Assertion": token("owner@example.com", aud="other-aud")},
    )
    assert bad_aud.status_code == 403
    expired = client.get(
        "/api/v1/businesses",
        headers={"Cf-Access-Jwt-Assertion": token("owner@example.com", exp_delta=-60)},
    )
    assert expired.status_code == 403


def test_login_link_cli_prints_one_time_url(monkeypatch, tmp_path):
    import os
    import subprocess
    import sys

    _amp_env(monkeypatch, tmp_path)
    script = Path(__file__).resolve().parents[1] / "scripts" / "amp_allowlist.py"
    env = os.environ.copy()
    added = subprocess.run(
        [sys.executable, str(script), "login-link", "--email", "owner@example.com"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert added.returncode == 0, added.stderr
    assert added.stdout.strip().startswith("http://127.0.0.1:8011/api/v1/amp/auth/magic?token=")
    missing = subprocess.run(
        [sys.executable, str(script), "login-link", "--email", "nope@example.com"],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing.returncode == 2
    assert "Sin acceso" in missing.stderr

    from urllib.parse import parse_qs, urlparse
    token = parse_qs(urlparse(added.stdout.strip()).query)["token"][0]
    client = _client(monkeypatch, tmp_path)
    opened = client.get("/api/v1/amp/auth/magic", params={"token": token}, follow_redirects=False)
    assert opened.status_code == 303, opened.text
    assert "HttpOnly" in opened.headers.get("set-cookie", "")
    again = client.get("/api/v1/amp/auth/magic", params={"token": token}, follow_redirects=False)
    assert again.status_code == 403


def test_workroom_api_base_and_lock_stay_default(monkeypatch, tmp_path):
    monkeypatch.delenv("EMPIRE_API_BASE", raising=False)
    monkeypatch.delenv("EMPIRE_DATA_DIR", raising=False)
    monkeypatch.delenv("EMPIRE_WORKER_LOCK", raising=False)
    from app.instance_url import empire_api_base, empire_api_url, primary_worker_lock_path

    assert empire_api_base() == "http://localhost:8000"
    assert empire_api_url("/api/v1/health") == "http://localhost:8000/api/v1/health"
    assert str(primary_worker_lock_path()) == "/tmp/empire_primary_worker.lock"

    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_API_BASE", "http://127.0.0.1:8011")
    assert empire_api_base() == "http://127.0.0.1:8011"
    assert empire_api_url("/health") == "http://127.0.0.1:8011/health"
    assert primary_worker_lock_path() == tmp_path / "run" / "empire_primary_worker.lock"

    monkeypatch.setenv("EMPIRE_WORKER_LOCK", str(tmp_path / "custom.lock"))
    assert primary_worker_lock_path() == tmp_path / "custom.lock"


def test_interview_draft_save_and_resume(monkeypatch, tmp_path):
    """A half-done interview is stored per verified user and resumes."""
    client = _client(monkeypatch, tmp_path)
    denied = client.get("/api/v1/businesses/interview")
    assert denied.status_code == 403
    assert denied.json()["code"] == "sin_acceso"
    denied_put = client.put(
        "/api/v1/businesses/interview",
        json={"step": 1, "answers": {"legal_name": "No"}},
    )
    assert denied_put.status_code == 403

    first = client.put(
        "/api/v1/businesses/interview",
        headers=_owner(),
        json={
            "step": 2,
            "answers": {
                "legal_name": "Andes Datos SAS",
                "city": "Medellín",
                "modules": {"crm": True},
            },
        },
    )
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "draft"
    assert first.json()["step"] == 2
    assert first.json()["answers"]["legal_name"] == "Andes Datos SAS"
    assert first.json()["answers"]["country"] == "Colombia"
    assert first.json()["answers"]["currency"] == "COP"
    assert first.json()["answers"]["modules"]["crm"] is True
    assert first.json()["answers"]["modules"]["socialforge"] is False
    assert first.json()["assistant"] == "Max-e"

    # A later screen merges. It does not wipe the earlier answers.
    second = client.put(
        "/api/v1/businesses/interview",
        headers=_owner(),
        json={"step": 5, "answers": {"currency": "USD", "modules": {"leadforge": True}}},
    )
    assert second.status_code == 200, second.text
    assert second.json()["step"] == 5
    assert second.json()["answers"]["legal_name"] == "Andes Datos SAS"
    assert second.json()["answers"]["city"] == "Medellín"
    assert second.json()["answers"]["currency"] == "USD"
    assert second.json()["answers"]["modules"]["crm"] is True
    assert second.json()["answers"]["modules"]["leadforge"] is True

    resumed = client.get("/api/v1/businesses/interview", headers=_owner())
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "draft"
    assert resumed.json()["step"] == 5
    assert resumed.json()["answers"]["legal_name"] == "Andes Datos SAS"

    # Identity headers do not switch the draft. The session does.
    spoofed = client.get(
        "/api/v1/businesses/interview",
        headers={**_owner(), "X-User-Email": "otra@example.com"},
    )
    assert spoofed.status_code == 200
    assert spoofed.json()["answers"]["legal_name"] == "Andes Datos SAS"

    from app.services import amp_allowlist
    amp_allowlist.add_entry(email="otra@example.com", role="member")
    other = client.get("/api/v1/businesses/interview", headers=_session("otra@example.com"))
    assert other.status_code == 200
    assert other.json()["status"] == "empty"
    assert other.json()["step"] == 0
    assert other.json()["answers"]["legal_name"] == ""

    drafts = list((tmp_path / "businesses" / "interview-drafts").glob("*.json"))
    assert len(drafts) == 1
    assert "owner-example-com" in drafts[0].name
    assert str(tmp_path) in str(drafts[0].resolve())


def test_interview_finish_creates_company_and_clears_draft(monkeypatch, tmp_path):
    client = _client(monkeypatch, tmp_path)
    denied = client.post(
        "/api/v1/businesses/interview/finish",
        json={"answers": {"legal_name": "Fuera"}},
    )
    assert denied.status_code == 403

    saved = client.put(
        "/api/v1/businesses/interview",
        headers=_owner(),
        json={
            "step": 3,
            "answers": {
                "legal_name": "Andes Datos SAS",
                "trade_name": "Andes Datos",
                "city": "Medellín",
                "country": "Colombia",
                "email": "hola@andesdatos.co",
                "phone": "3000000000",
                "website": "https://andesdatos.co",
                "template": "datos_bi",
                "industry_description": "Tableros para pymes",
            },
        },
    )
    assert saved.status_code == 200, saved.text

    missing = client.post(
        "/api/v1/businesses/interview/finish",
        headers=_owner(),
        json={"step": 8, "answers": {"legal_name": "  "}},
    )
    assert missing.status_code == 400

    unknown = client.post(
        "/api/v1/businesses/interview/finish",
        headers=_owner(),
        json={"answers": {"legal_name": "Andes Datos SAS", "template": "no-existe"}},
    )
    assert unknown.status_code == 400

    finished = client.post(
        "/api/v1/businesses/interview/finish",
        headers=_owner(),
        json={
            "step": 8,
            "answers": {
                "sells": "servicios",
                "items": [
                    {"name": "Acompañamiento mensual", "kind": "servicio", "price": 1500000},
                ],
                "customer_who": "Pymes de retail",
                "customer_type": "b2b",
                "first_customer": {"name": "Ana Ruiz", "email": "ana@cliente.co", "phone": "3010000000"},
                "currency": "COP",
                "fiscal_year_start": "01-01",
                "tax_id": "900123456",
                "charges_iva": True,
                "payment_methods": ["transferencia", "pse"],
                "team_mode": "solo",
                "modules": {"crm": True, "leadforge": True, "workroom": True},
            },
        },
    )
    assert finished.status_code == 200, finished.text
    body = finished.json()
    assert body["legal_name"] == "Andes Datos SAS"
    assert body["trade_name"] == "Andes Datos"
    assert body["city"] == "Medellín"
    assert body["country"] == "Colombia"
    assert body["currency"] == "COP"
    assert body["fiscal_year_start"] == "01-01"
    assert body["tax_id"] == "900123456"
    assert body["charges_iva"] is True
    assert body["payment_methods"] == ["transferencia", "pse"]
    assert body["customer_type"] == "b2b"
    assert body["setup"] == "entrevista"
    assert body["assistant"] == "Max-e"
    assert body["template"] == "datos_bi"
    assert body["industry_modules"] == []
    # Only the tools they turned on. workroom is not an AMP module.
    assert body["modules"] == ["crm", "leadforge"]
    for hidden in ("socialforge", "quotes", "invoices", "courses", "workroom", "max"):
        assert hidden not in body["modules"]
    prices = {row["name"]: row["price"] for row in body["service_categories"]}
    assert prices["Diagnóstico de datos"] is None
    assert prices["Acompañamiento mensual"] == 1500000
    assert any(row["name"] == "Ana Ruiz" and row["email"] == "ana@cliente.co" for row in body["contacts"])

    cleared = client.get("/api/v1/businesses/interview", headers=_owner())
    assert cleared.json()["status"] == "empty"
    assert cleared.json()["answers"]["legal_name"] == ""
    assert list((tmp_path / "businesses" / "interview-drafts").glob("*.json")) == []

    fetched = client.get(f"/api/v1/businesses/{body['slug']}", headers=_owner())
    assert fetched.status_code == 200
    stored = fetched.json()
    assert stored["currency"] == "COP"
    assert stored["city"] == "Medellín"
    assert stored["charges_iva"] is True
    assert stored["interview"]["industry_description"] == "Tableros para pymes"
    fetched_prices = {row["name"]: row["price"] for row in stored["service_categories"]}
    assert fetched_prices["Acompañamiento mensual"] == 1500000
    assert fetched_prices["Diagnóstico de datos"] is None

    # Tools stay off when the interview does not choose them.
    plain = client.post(
        "/api/v1/businesses/interview/finish",
        headers=_owner(),
        json={"answers": {"legal_name": "Sin Herramientas SAS", "currency": "EUR"}},
    )
    assert plain.status_code == 200, plain.text
    assert plain.json()["modules"] == []
    assert plain.json()["currency"] == "COP"
    assert plain.json()["country"] == "Colombia"
    assert plain.json()["slug"] != body["slug"]
