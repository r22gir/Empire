"""Family editions: usage cap, one login, fact visibility, Maxine on ConstructionForge."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


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
    from app.routers.amp import router as amp_router
    from app.routers.edition import router as edition_router

    app = FastAPI()
    app.middleware("http")(amp_access_middleware)
    app.include_router(edition_router, prefix="/api/v1")
    app.include_router(amp_router, prefix="/api/v1/amp")
    return TestClient(app)


def _cookie(client, email="owner@example.com"):
    from app.services.amp_access import SESSION_COOKIE, create_session_token
    client.cookies.set(SESSION_COOKIE, create_session_token(email))


def test_usage_cap_warns_then_soft_blocks_heavy_only(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", "1000")
    monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")
    from app.services.instance_usage import enforce_usage_cap, record_usage, usage_summary

    record_usage(input_tokens=160, output_tokens=0, model="MiniMax-M3")
    summary = usage_summary()
    assert summary["allowance"] == 200
    assert summary["level"] == "warn"
    assert summary["cap_percent"] == 20
    assert summary["used_percent"] == 80.0
    assert summary["remaining_percent"] == 20.0
    assert "20" in summary["message"]
    assert "Queda el 20%" in summary["message"]
    assert "20%" in summary["limit_note_es"]
    assert "MiniMax" in summary["limit_note_es"]
    assert enforce_usage_cap(text="hola") is None

    record_usage(input_tokens=50, output_tokens=0, model="MiniMax-M3")
    blocked = usage_summary()
    assert blocked["level"] == "blocked"
    assert blocked["month"]["tokens"] == 210
    assert enforce_usage_cap(text="un mensaje corto") is None
    heavy = enforce_usage_cap(text="x" * 500)
    assert heavy and "tope" in heavy
    generated = enforce_usage_cap(text="hola", source="generate")
    assert generated and "mensajes cortos" in generated


def test_family_forces_minimax_m3(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "maxine")
    monkeypatch.setenv("MAX_SELECTED_PROVIDER", "openai")
    monkeypatch.setenv("MAX_SELECTED_MODEL", "gpt-4o")
    from app.edition import app_display_name, is_amp, is_maxine, primary_shell
    from app.services.max.routing_state import load_routing_state

    assert is_maxine() is True
    assert is_amp() is False
    assert primary_shell() == "construction"
    assert app_display_name() == "Maxine · Centro de mando"
    state = load_routing_state()
    assert state.selected_provider == "minimax"
    assert state.selected_model == "MiniMax-M3"
    assert state.fallback_enabled is False


def test_session_cookie_opens_amp_me_without_second_login(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    client = _client()
    denied = client.get("/api/v1/amp/me")
    assert denied.status_code == 403
    _cookie(client)
    me = client.get("/api/v1/amp/me")
    assert me.status_code == 200
    assert me.json()["email"] == "owner@example.com"


def test_usage_page_is_owner_only_and_states_the_twenty_percent_cap(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", "1000")
    from app.services.amp_allowlist import add_entry
    from app.services.instance_usage import record_usage

    record_usage(input_tokens=10, output_tokens=5, cost_usd=0.01)
    client = _client()
    assert client.get("/api/v1/edition/usage").status_code == 403
    add_entry(email="member@example.com", role="member")
    _cookie(client, "member@example.com")
    assert client.get("/api/v1/edition/usage").status_code == 403
    _cookie(client, "owner@example.com")
    body = client.get("/api/v1/edition/usage")
    assert body.status_code == 200
    payload = body.json()
    assert payload["cap_percent"] == 20
    assert payload["used_percent"] == 7.5
    assert payload["remaining_percent"] == 92.5
    assert payload["limit_note_es"] == "Tu uso está limitado al 20% del uso total de MiniMax."
    hidden = {"baseline", "baseline_basis", "allowance", "used", "day", "month", "ratio"}
    assert hidden.isdisjoint(payload)
    card = (Path(__file__).resolve().parents[2] / "empire-command-center" / "app" / "components" / "UsageCard.tsx").read_text(encoding="utf-8")
    page = (Path(__file__).resolve().parents[2] / "empire-command-center" / "app" / "uso" / "page.tsx").read_text(encoding="utf-8")
    assert "limitado al" in card
    assert "queda" in card
    assert "usado" in card
    assert " tok" not in card
    assert "cupo" not in card
    assert "baseline" not in card
    assert "20%" in page
    assert "queda" in page
    assert "usado" in page
    assert "cupo" not in page
    assert "solo para el dueño" in page


def test_confidential_facts_stay_out_of_generated_notes(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.amp_businesses import create_business, write_generated_note
    from app.services.edition_facts import guard_public_text, upsert_fact

    upsert_fact(key="phone", text="Teléfono: 3001112233", value="3001112233", visibility="confidential", label="Teléfono")
    upsert_fact(key="city", text="Ciudad: Medellín", value="Medellín", visibility="public", label="Ciudad")
    created = create_business(name="Taller Norte", industry="oficios")
    note = write_generated_note(created["slug"], "Post", "Llama al 3001112233 en Medellín")
    text = note.read_text(encoding="utf-8")
    assert "3001112233" not in text
    assert "[confidencial]" in text
    assert "Medellín" in text
    assert guard_public_text("el nit 900123 y Medellín") == "el nit 900123 y Medellín"


def test_maxine_seed_is_constructionforge_and_public_only(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "maxine")
    from app.routers.construction import get_db
    from app.services.edition_facts import list_facts
    from app.services.edition_seed import load_edition_seed

    result = load_edition_seed()
    assert len(result["projects"]) == 2
    assert result["brand"] == "GAC"
    conn = get_db()
    try:
        projects = {row["slug"]: dict(row) for row in conn.execute("SELECT * FROM cf_projects").fetchall()}
        assert set(projects) == {"rincon-de-san-jeronimo", "portal-campestre-2"}
        leaks = (
            "Things to ask",
            "Prices for the Rincón",
            "Current status of Argos",
            "Which tools to turn on",
            "Earlier project:",
            "parque infantil",
        )
        for row in projects.values():
            description = row["description"] or ""
            for leak in leaks:
                assert leak not in description, leak
        assert "Calle 12" in (projects["portal-campestre-2"]["description"] or "")
        assert "OCMA" in (projects["rincon-de-san-jeronimo"]["description"] or "")
        assert "Portal Campestre" not in (projects["rincon-de-san-jeronimo"]["description"] or "")
        portal_lots = conn.execute(
            "SELECT lot_number, status, area_m2, current_price, base_price FROM cf_lots WHERE project_id = ? ORDER BY CAST(lot_number AS INTEGER)",
            (projects["portal-campestre-2"]["id"],),
        ).fetchall()
        assert len(portal_lots) == 27
        counts = {}
        for lot in portal_lots:
            counts[lot["status"]] = counts.get(lot["status"], 0) + 1
            assert lot["area_m2"] is None
            assert lot["current_price"] is None
            assert lot["base_price"] is None
        assert counts == {"available": 14, "sold": 7, "consultar": 6}
        rincon = conn.execute(
            "SELECT lot_number, status, area_m2, current_price FROM cf_lots WHERE project_id = ?",
            (projects["rincon-de-san-jeronimo"]["id"],),
        ).fetchall()
        assert len(rincon) == 4
        areas = sorted(row["area_m2"] for row in rincon)
        assert areas == [35.9, 35.9, 37.63, 37.63]
        assert all(row["current_price"] is None for row in rincon)
        assert all(row["status"] == "under_construction" for row in rincon)
        builder = conn.execute("SELECT name, cedula_nit FROM cf_contractors").fetchall()
        assert [row["name"] for row in builder] == ["OCMA"]
        assert builder[0]["cedula_nit"] is None
        phases = conn.execute("SELECT COUNT(*) AS n FROM cf_phases").fetchone()["n"]
        assert phases == 2
    finally:
        conn.close()

    facts = list_facts()
    public = [fact["text"] for fact in facts if fact["visibility"] == "public"]
    confidential = [fact["text"] for fact in facts if fact["visibility"] == "confidential"]
    assert any("321 495 0275" in text for text in public)
    assert any("550.000.000" in text for text in public)
    assert any("Prices for the Rincón" in text for text in confidential)
    for path in Path(tmp_path, "businesses").rglob("*.json"):
        raw = path.read_text(encoding="utf-8")
        assert "tax_id" not in raw
        assert "NIT" not in raw
    assert "GAC" in Path(tmp_path, "businesses", "index.json").read_text(encoding="utf-8")
    for path in Path(tmp_path, "businesses").rglob("business.json"):
        description = path.read_text(encoding="utf-8")
        assert "Things to ask" not in description
        assert "Prices for the Rincón" not in description
        assert "Which tools to turn on" not in description


def test_maxine_seed_refresh_rewrites_a_polluted_description(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "maxine")
    from app.routers.construction import get_db
    from app.services.edition_seed import load_edition_seed, maybe_load_seed

    load_edition_seed()
    polluted = (
        "Vivienda campestre.\n"
        "## Earlier project: Argos Campestre\n"
        "- Plans from 2022.\n"
        "## Things to ask Camilo on day one\n"
        "1. Prices for the Rincón units and Portal Campestre types 2 and 3.\n"
        "2. Current status of Argos Campestre and what he wants Maxine to track.\n"
        "3. Which tools to turn on (CRM, quotes, lead capture, social posts).\n"
    )
    conn = get_db()
    try:
        conn.execute(
            "UPDATE cf_projects SET description = ? WHERE slug = ?",
            (polluted, "portal-campestre-2"),
        )
        conn.commit()
        before = conn.execute("SELECT COUNT(*) AS n FROM cf_lots").fetchone()["n"]
    finally:
        conn.close()
    assert (tmp_path / "seed_loaded.json").is_file()
    refreshed = maybe_load_seed()
    assert refreshed["refreshed"] is True
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT description FROM cf_projects WHERE slug = ?",
            ("portal-campestre-2",),
        ).fetchone()
        description = row["description"]
        assert "Things to ask" not in description
        assert "Argos Campestre" not in description
        assert "Prices for the Rincón" not in description
        assert "Which tools to turn on" not in description
        assert "disponibles" in description
        after = conn.execute("SELECT COUNT(*) AS n FROM cf_lots").fetchone()["n"]
        assert after == before == 31
    finally:
        conn.close()
    profile = next(Path(tmp_path, "businesses").rglob("portal-campestre-2/business.json"))
    stored = profile.read_text(encoding="utf-8")
    assert "Things to ask" not in stored
    assert "Argos Campestre" not in stored


def test_maxine_interview_defaults_to_confidential_and_skips_private_files(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "maxine")
    secret = tmp_path / "privado.txt"
    secret.write_text("SECRETO-ARCHIVO-PRIVADO nit 900111222", encoding="utf-8")
    from app.services.amp_businesses import finish_interview
    from app.services.edition_facts import list_facts
    from app.services.edition_seed import load_edition_seed

    loaded = load_edition_seed()
    assert loaded["projects"]
    blob = "\n".join(fact["text"] for fact in list_facts())
    assert "SECRETO-ARCHIVO-PRIVADO" not in blob
    assert "Grupo Argos Campestre" not in blob
    for path in Path(tmp_path, "businesses").rglob("*.json"):
        raw = path.read_text(encoding="utf-8")
        assert "Grupo Argos Campestre" not in raw
        assert "SECRETO-ARCHIVO-PRIVADO" not in raw
        assert "tax_id" not in raw

    finish_interview(
        "owner@example.com",
        step=9,
        answers={
            "legal_name": "Grupo Argos Campestre S.A.S.",
            "tax_id": "900111222",
            "trade_name": "Lote demo",
            "city": "Cartago",
            "country": "Colombia",
            "phase_name": "Etapa entrevista",
            "lots": [{"lot_number": "B1", "status": "available"}],
        },
    )
    stored = {fact["key"]: fact for fact in list_facts()}
    assert "legal_name" not in stored
    assert "tax_id" not in stored
    assert stored["city"]["visibility"] == "confidential"
    assert stored["trade_name"]["visibility"] == "confidential"
    assert all(fact["visibility"] == "confidential" or fact["source"] != "interview" for fact in stored.values())


def test_maxine_interview_and_payment_plan_share_construction_rows(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path, "maxine")
    from app.routers.construction import get_db
    from app.services.amp_businesses import finish_interview
    from app.services.construction_bridge import create_payment_plan, lead_to_buyer, list_quotes_from_sales
    from app.services.edition_facts import list_facts

    created = finish_interview(
        "owner@example.com",
        step=9,
        answers={
            "legal_name": "Lote demo",
            "trade_name": "Lote demo",
            "city": "Cartago",
            "country": "Colombia",
            "phase_name": "Etapa entrevista",
            "lots": [{"lot_number": "A1", "status": "available"}],
            "fact_visibility": {"city": "public"},
            "first_customer": {"name": "Ana Ruiz", "email": "ana@example.com", "phone": ""},
        },
    )
    assert created["model"] == "constructionforge"
    assert created["cf_project_id"]
    conn = get_db()
    try:
        lot = conn.execute("SELECT area_m2, current_price, status FROM cf_lots WHERE lot_number = 'A1'").fetchone()
        assert lot["area_m2"] is None
        assert lot["current_price"] is None
        assert lot["status"] == "available"
        phase = conn.execute("SELECT name FROM cf_phases").fetchone()
        assert phase["name"] == "Etapa entrevista"
    finally:
        conn.close()
    city = next(fact for fact in list_facts() if fact["key"] == "city")
    assert city["visibility"] == "public"

    lead_to_buyer({"first_name": "Ana", "last_name": "Ruiz", "email": "ana@example.com", "source": "lead"})
    plan = create_payment_plan(
        amount=1000000,
        buyer_name="Ana Ruiz",
        buyer_email="ana@example.com",
        lot_number="A1",
        project_slug=created["slug"],
        installments=2,
    )
    assert plan["currency"] == "COP"
    assert plan["sale_price"] == 1000000
    assert len(plan["payments"]) == 2
    quotes = list_quotes_from_sales()
    assert quotes["total"] == 1
    assert quotes["quotes"][0]["id"] == plan["cf_sale_id"]
    conn = get_db()
    try:
        buyers = conn.execute("SELECT COUNT(*) AS n FROM cf_buyers WHERE email = 'ana@example.com'").fetchone()["n"]
        assert buyers == 1
    finally:
        conn.close()


def test_usage_endpoint_reports_percentages_only(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_USD", "1")
    monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")
    monkeypatch.setenv("MINIMAX_USD_PER_MILLION_TOKENS", "1")
    from app.services.instance_usage import record_usage
    record_usage(input_tokens=1_000_000, output_tokens=0, model="MiniMax-M3")
    client = _client()
    _cookie(client)
    body = client.get("/api/v1/edition/usage")
    assert body.status_code == 200
    data = body.json()
    assert data["enforced"] is True
    assert data["used_percent"] == 100.0
    assert data["remaining_percent"] == 0.0
    assert data["level"] == "blocked"
    assert "allowance" not in data
    assert "baseline" not in data
    assert "month" not in data
