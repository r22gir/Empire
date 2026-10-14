"""Company setup interview: merge-only, founder-only, edition-isolated."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

FOUNDER = "founder@example.com"
SECRET_TOKEN = "EAABvery-secret-whatsapp-token-xyz"
WORKROOM_LEAKS = ("5124 Frolich", "Hyattsville", "workroom@empirebox.store")


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    root = tmp_path / "studio"
    root.mkdir()
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(root))
    monkeypatch.setenv("EMPIRE_EDITION", "main")
    monkeypatch.setenv("FOUNDER_ACCESS_EMAILS", FOUNDER)
    monkeypatch.delenv("FOUNDER_EMAIL", raising=False)
    monkeypatch.setenv("EMPIRE_WHATSAPP_SECRETS_PATH", str(root / "secrets" / "whatsapp.json"))

    def fake_verify(token):
        if str(token).startswith("good:"):
            return True, "cloudflare_access", token.split(":", 1)[1]
        return False, "invalid", ""

    monkeypatch.setattr("app.services.max.voice_live.verify_access_jwt", fake_verify)
    return root


def _req(headers=None, cookies=None):
    return SimpleNamespace(headers={k.lower(): v for k, v in (headers or {}).items()}, cookies=cookies or {})


def _client():
    from app.routers.onboarding import router
    from app.routers import whatsapp as wa

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.include_router(wa.router, prefix="/api/v1")
    return TestClient(app)


def _auth():
    return {"Cf-Access-Jwt-Assertion": f"good:{FOUNDER}"}


def _seed(root: Path, **extra):
    path = root / "company" / "business.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "business_name": "Empire Workroom",
        "business_phone": "(703) 555-0100",
        "founder_phones": ["+17035550100"],
        "owner_phones": ["+17035550100"],
        "business_email": "keep@example.com",
        "business_address": "1 Overlay Lane",
        **extra,
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def test_status_requires_founder_session(isolated):
    client = _client()
    assert client.get("/api/v1/onboarding/status").status_code == 403
    assert client.get("/api/v1/onboarding/status", headers={"Cf-Access-Jwt-Assertion": "good:guest@x.com"}).status_code == 403
    ok = client.get("/api/v1/onboarding/status", headers=_auth())
    assert ok.status_code == 200
    body = ok.json()
    assert body["configured"] is False
    assert "config" not in body


def test_merge_preserves_phones(isolated):
    _seed(isolated)
    from app.services.company_setup.store import load_merged, save_section

    save_section("identity", {"legal_name": "Empire Workroom LLC", "dba": "Empire Workroom", "owner_name": "rg"})
    merged = load_merged()
    assert merged["business_phone"] == "(703) 555-0100"
    assert merged["founder_phones"] == ["+17035550100"]
    assert merged["legal_name"] == "Empire Workroom LLC"
    raw = json.loads((isolated / "company" / "business.json").read_text())
    assert raw["business_phone"] == "(703) 555-0100"


def test_legacy_setup_merges_not_replaces(isolated):
    _seed(isolated)
    client = _client()
    res = client.post(
        "/api/v1/onboarding/setup",
        headers=_auth(),
        json={"business_name": "Nelma's Workroom", "owner_name": "rg"},
    )
    assert res.status_code == 200
    from app.services.company_setup.store import load_merged

    merged = load_merged()
    assert merged["business_phone"] == "(703) 555-0100"
    assert merged["founder_phones"] == ["+17035550100"]
    assert "Empire" in (merged.get("dba") or merged.get("business_name") or "") or merged.get("business_name")


def test_configured_needs_name_and_contact(isolated):
    from app.services.company_setup.schema import is_configured
    from app.services.company_setup.store import load_merged, save_section

    assert is_configured(load_merged()) is False
    save_section("identity", {
        "legal_name": "Empire Workroom LLC",
        "dba": "Empire Workroom",
        "brands": [{"id": "empire-workroom", "name": "Empire Workroom", "is_default": True}],
    })
    assert is_configured(load_merged()) is False
    save_section("contact", {
        "address": "5120 Test Rd, Hyattsville, MD",
        "phone": "(703) 555-0199",
        "email": "docs@example.com",
    })
    assert is_configured(load_merged()) is True
    client = _client()
    body = client.get("/api/v1/onboarding/status", headers=_auth()).json()
    assert body["configured"] is True
    assert body["missing"] == []


def test_save_resume_and_review(isolated):
    client = _client()
    first = client.put(
        "/api/v1/onboarding/interview/identity",
        headers=_auth(),
        json={"data": {"legal_name": "Empire Workroom LLC", "dba": "Empire Workroom"}},
    )
    assert first.status_code == 200
    assert first.json()["progress"]["current_section"] == "contact"
    resumed = client.get("/api/v1/onboarding/interview", headers=_auth())
    assert resumed.json()["progress"]["completed_sections"] == ["identity"]
    review = client.get("/api/v1/onboarding/interview/review", headers=_auth())
    assert review.status_code == 200
    assert review.json()["data"]["legal_name"] == "Empire Workroom LLC"
    done = client.post("/api/v1/onboarding/interview/complete", headers=_auth())
    assert done.json()["progress"]["completed"] is True


def test_family_edition_never_writes_workroom(monkeypatch, tmp_path, isolated):
    workroom = tmp_path / "workroom-biz.json"
    workroom.write_text(json.dumps({"business_phone": "KEEP", "founder_phones": ["1"]}), encoding="utf-8")
    amp = tmp_path / "amp"
    amp.mkdir()
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(amp))
    from app.edition import apply_amp_process_paths

    apply_amp_process_paths()
    from app.services.company_setup.store import business_json_path, save_section

    path = business_json_path()
    assert "amp" in str(path)
    save_section("identity", {"legal_name": "AMP", "dba": "AMP"})
    assert json.loads(workroom.read_text())["business_phone"] == "KEEP"
    written = json.loads(path.read_text())
    assert written["legal_name"] == "AMP"
    for leak in WORKROOM_LEAKS:
        assert leak not in path.read_text()


def test_studio_edition_founder_session_works(isolated, monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "studio")
    from app.services.company_setup.auth import require_verified_founder

    session = require_verified_founder(_req({"Cf-Access-Jwt-Assertion": f"good:{FOUNDER}"}))
    assert session["verified"] is True
    client = _client()
    assert client.get("/api/v1/onboarding/status", headers=_auth()).status_code == 200


def test_invites_never_send_email(isolated):
    sendmail = MagicMock()
    with patch("smtplib.SMTP") as smtp:
        smtp.return_value.sendmail = sendmail
        from app.services.company_setup.invites import create_invite

        row = create_invite("seam@example.com", "seamstress", "Sam")
        assert row["sent"] is False
        assert row["send_channel"] == "none"
        sendmail.assert_not_called()
    client = _client()
    res = client.post(
        "/api/v1/onboarding/team/invites",
        headers=_auth(),
        json={"email": "est@example.com", "role": "estimator"},
    )
    assert res.status_code == 200
    assert res.json()["sent"] is False


def test_whatsapp_keys_masked_never_returned(isolated, caplog):
    caplog.set_level(logging.INFO)
    client = _client()
    res = client.post(
        "/api/v1/onboarding/whatsapp",
        headers=_auth(),
        json={
            "WHATSAPP_ACCESS_TOKEN": SECRET_TOKEN,
            "WHATSAPP_PHONE_NUMBER_ID": "123456",
            "WHATSAPP_APP_SECRET": "app-secret-value",
            "WHATSAPP_VERIFY_TOKEN": "verify-me",
            "owner_numbers": ["+17035550111"],
        },
    )
    assert res.status_code == 200
    dumped = json.dumps(res.json())
    assert SECRET_TOKEN not in dumped
    assert "app-secret-value" not in dumped
    assert "verify-me" not in dumped
    assert res.json()["fields"][0]["set"] is True
    assert res.json()["fields"][0]["masked"].startswith("••••")
    assert SECRET_TOKEN not in caplog.text
    stored = (isolated / "secrets" / "whatsapp.json").read_text()
    assert SECRET_TOKEN in stored
    again = client.get("/api/v1/onboarding/whatsapp", headers=_auth()).json()
    assert SECRET_TOKEN not in json.dumps(again)
    assert again["owner_numbers_count"] == 1


def test_whatsapp_keys_require_founder(isolated):
    client = _client()
    assert client.get("/api/v1/whatsapp/keys").status_code == 403
    assert client.post("/api/v1/whatsapp/keys", json={"WHATSAPP_ACCESS_TOKEN": SECRET_TOKEN}).status_code == 403


def test_webhook_verification_state(isolated):
    from app.services.company_setup.whatsapp_secrets import save_secrets, status_panel

    save_secrets({
        "WHATSAPP_ACCESS_TOKEN": "tok",
        "WHATSAPP_PHONE_NUMBER_ID": "1",
        "WHATSAPP_APP_SECRET": "sec",
        "WHATSAPP_VERIFY_TOKEN": "hub-token",
    })
    client = _client()
    bad = client.get("/api/v1/whatsapp/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "99"})
    assert bad.status_code == 403
    assert status_panel()["webhook"]["verified"] is False
    good = client.get("/api/v1/whatsapp/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "hub-token", "hub.challenge": "99"})
    assert good.status_code == 200
    assert good.text == "99"
    assert status_panel()["webhook"]["verified"] is True


def test_rate_cards_feed_pricing_studio(isolated):
    from app.services.company_setup.store import save_section
    from app.services.pricing.rate_cards import component_rates

    save_section("services", {
        "catalog": [{"name": "Roman shade", "rate": 70, "unit": "window"}],
        "labor_rate": 88,
        "rate_cards": {"workroom": {"labor_rate": 88}},
    })
    assert component_rates("workroom")["labor_rate"] == 88


def test_does_not_touch_live_empire_data(isolated):
    home = Path.home() / "empire-data"
    before = home.exists()
    from app.services.company_setup.store import business_json_path, save_section

    path = business_json_path()
    assert "empire-data" not in str(path)
    save_section("identity", {"legal_name": "Tmp LLC"})
    assert str(path).startswith(str(isolated))
    if not before:
        assert not home.exists()
