"""Max-e companies: live list, confirm-before-write, PUT route. Temp dirs only."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _env(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Max-e")
    monkeypatch.setenv("AMP_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("AMP_JWT_SECRET", "test-secret")
    monkeypatch.delenv("FOUNDER_EMAIL", raising=False)


def _client():
    from app.middleware.edition_gate import amp_access_middleware
    from app.routers.edition import router as edition_router

    app = FastAPI()
    app.middleware("http")(amp_access_middleware)
    app.include_router(edition_router, prefix="/api/v1")
    return TestClient(app)


def _cookie(client, email="owner@example.com"):
    from app.services.amp_access import SESSION_COOKIE, create_session_token

    client.cookies.set(SESSION_COOKIE, create_session_token(email))


def test_list_businesses_and_prompt_include_juan_companies(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.edition import edition_prompt_suffix, greeting
    from app.services.amp_businesses import companies_prompt_block, company_choices, create_business

    rows = company_choices()
    slugs = [row["slug"] for row in rows]
    assert slugs == ["amp", "cibernettic"]
    create_business(name="Datos Andinos", industry="datos", description="Tableros")
    slugs = [row["slug"] for row in company_choices()]
    assert "datos-andinos" in slugs
    block = companies_prompt_block()
    assert "Datos Andinos" in block
    assert "slug:" in block
    assert "Cibernettic" in greeting("es")
    assert "Datos Andinos" in greeting("es")
    suffix = edition_prompt_suffix()
    assert "Datos Andinos" in suffix
    assert "save_company" in suffix


def test_update_requires_confirm_then_writes(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.amp_businesses import get_business, update_business

    preview = update_business(
        "datos-andinos",
        fields={"name": "Datos Andinos", "industry": "BI", "city": "Cali"},
        confirm=False,
    )
    assert preview["needs_confirmation"] is True
    assert get_business("datos-andinos") is None
    saved = update_business(
        "datos-andinos",
        fields={"name": "Datos Andinos", "industry": "BI", "city": "Cali"},
        confirm=True,
    )
    assert saved["ok"] is True
    assert saved["created"] is True
    row = get_business("datos-andinos")
    assert row["industry"] == "BI"
    assert row["city"] == "Cali"
    again = update_business("datos-andinos", fields={"city": "Medellín"}, confirm=True)
    assert again["ok"] is True
    assert get_business("datos-andinos")["city"] == "Medellín"


def test_put_business_requires_owner_and_confirm(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.amp_allowlist import add_entry

    add_entry(email="member@example.com", role="member")
    client = _client()
    _cookie(client, "member@example.com")
    denied = client.put("/api/v1/businesses/nueva-co", json={"name": "Nueva Co", "confirm": True})
    assert denied.status_code == 403

    _cookie(client, "owner@example.com")
    preview = client.put("/api/v1/businesses/nueva-co", json={"name": "Nueva Co", "industry": "redes"})
    assert preview.status_code == 200
    body = preview.json()
    assert body["needs_confirmation"] is True
    listed = client.get("/api/v1/businesses")
    slugs = [row["slug"] for row in listed.json()["businesses"]]
    assert "nueva-co" not in slugs

    saved = client.put(
        "/api/v1/businesses/nueva-co",
        json={"name": "Nueva Co", "industry": "redes", "confirm": True},
    )
    assert saved.status_code == 200
    assert saved.json()["ok"] is True
    listed = client.get("/api/v1/businesses")
    slugs = [row["slug"] for row in listed.json()["businesses"]]
    assert "nueva-co" in slugs


def test_voice_and_leadforge_use_dynamic_companies(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.amp_businesses import create_business
    from app.services.leadforge.trade_profile import trade_profile
    from app.services.voice_doc.extract import choice_from_text
    from app.services.voice_doc.pipeline import build_options

    create_business(name="Datos Andinos", industry="datos")
    ids = [choice["id"] for choice in build_options("quote", {"edition": "amp"})["choices"]]
    assert "business_amp" in ids
    assert "business_cibernettic" in ids
    assert "business_datos-andinos" in ids
    assert choice_from_text("es de Datos Andinos") == "business_datos-andinos"
    units = [unit["value"] for unit in trade_profile("amp")["business_units"]]
    assert "datos-andinos" in units
    assert "amp" in units
