"""Company setup interview: merge-only, founder-only, edition-isolated."""
from __future__ import annotations

import json
import logging
import os
import stat
import threading
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
    monkeypatch.delenv("COMPANY_SETUP_BUSINESS_PATH", raising=False)
    monkeypatch.delenv("COMPANY_SETUP_SEED_PATH", raising=False)
    for key in (
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_APP_SECRET",
        "WHATSAPP_VERIFY_TOKEN",
    ):
        monkeypatch.delenv(key, raising=False)

    def fake_verify(token):
        if str(token).startswith("good:"):
            return True, "cloudflare_access", token.split(":", 1)[1]
        return False, "invalid", ""

    monkeypatch.setattr("app.services.max.voice_live.verify_access_jwt", fake_verify)
    from app.services.pricing.rate_cards import invalidate_rate_overlay_cache

    invalidate_rate_overlay_cache()
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


def _seed_file(root: Path, monkeypatch, **extra) -> Path:
    path = root / "seed.json"
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
    monkeypatch.setenv("COMPANY_SETUP_SEED_PATH", str(path))
    return path


def _overlay(root: Path) -> dict:
    path = root / "company" / "business.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def test_status_requires_founder_session(isolated):
    client = _client()
    assert client.get("/api/v1/onboarding/status").status_code == 403
    assert client.get("/api/v1/onboarding/status", headers={"Cf-Access-Jwt-Assertion": "good:guest@x.com"}).status_code == 403
    ok = client.get("/api/v1/onboarding/status", headers=_auth())
    assert ok.status_code == 200
    body = ok.json()
    assert body["configured"] is False
    assert "config" not in body


def test_public_configured_does_not_403(isolated):
    client = _client()
    res = client.get("/api/v1/onboarding/configured")
    assert res.status_code == 200
    assert res.json() == {"configured": False}


def test_overlay_stores_only_changed_keys(isolated, monkeypatch):
    seed = _seed_file(isolated, monkeypatch)
    from app.services.company_setup.store import load_merged, save_section

    save_section("identity", {"legal_name": "Empire Workroom LLC", "dba": "Empire Workroom", "owner_name": "rg"})
    overlay = _overlay(isolated)
    assert overlay["legal_name"] == "Empire Workroom LLC"
    assert "business_phone" not in overlay
    assert "founder_phones" not in overlay
    assert load_merged()["business_phone"] == "(703) 555-0100"
    seed.write_text(json.dumps({
        "business_phone": "(202) 555-9999",
        "founder_phones": ["+12025559999"],
        "business_email": "keep@example.com",
        "business_address": "1 Overlay Lane",
    }), encoding="utf-8")
    save_section("tax", {"ein": "12-3456789"})
    assert load_merged()["business_phone"] == "(202) 555-9999"
    assert "business_phone" not in _overlay(isolated)
    assert json.loads(seed.read_text())["business_phone"] == "(202) 555-9999"


def test_merge_preserves_phones(isolated, monkeypatch):
    _seed_file(isolated, monkeypatch)
    from app.services.company_setup.store import load_merged, save_section

    save_section("identity", {"legal_name": "Empire Workroom LLC", "dba": "Empire Workroom", "owner_name": "rg"})
    merged = load_merged()
    assert merged["business_phone"] == "(703) 555-0100"
    assert merged["founder_phones"] == ["+17035550100"]
    assert merged["legal_name"] == "Empire Workroom LLC"


def test_legacy_setup_merges_not_replaces(isolated, monkeypatch):
    _seed_file(isolated, monkeypatch)
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
    assert client.get("/api/v1/onboarding/configured").json()["configured"] is True


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


def test_services_cannot_overwrite_founder_phones(isolated, monkeypatch):
    _seed_file(isolated, monkeypatch)
    client = _client()
    res = client.put(
        "/api/v1/onboarding/interview/services",
        headers=_auth(),
        json={"data": {"labor_rate": 70, "founder_phones": ["+19999999999"], "catalog": []}},
    )
    assert res.status_code == 400
    assert "founder_phones" in res.text
    from app.services.company_setup.store import load_merged

    assert load_merged()["founder_phones"] == ["+17035550100"]


def test_timestamped_backup_and_0600(isolated):
    from app.services.company_setup.store import business_json_path, save_section

    path = business_json_path()
    save_section("identity", {"legal_name": "First LLC"})
    save_section("tax", {"ein": "11-1111111"})
    backups = list(path.parent.glob("business.json.*.bak"))
    assert backups
    mode = stat.S_IMODE(path.stat().st_mode)
    assert mode == 0o600
    progress = isolated / "company" / "setup_progress.json"
    assert progress.exists()
    assert list(progress.parent.glob("setup_progress.json.*.bak")) == []


def test_backup_rotation_keeps_10_and_drops_old(isolated, tmp_path):
    import time

    from app.services.company_setup.io import BACKUP_KEEP, rotate_backups

    dest = tmp_path / "baks"
    dest.mkdir()
    now = time.time()
    for i in range(12):
        p = dest / f"business.json.202601{i:02d}T000000Z.bak"
        p.write_text(str(i), encoding="utf-8")
        os.utime(p, (now - i * 60, now - i * 60))
    old = dest / "business.json.old.bak"
    old.write_text("old", encoding="utf-8")
    os.utime(old, (now - 8 * 86400, now - 8 * 86400))
    rotate_backups(dest, "business.json")
    left = sorted(dest.glob("business.json.*.bak"))
    assert old not in left
    assert not old.exists()
    assert len(left) == BACKUP_KEEP


def test_workroom_backups_go_outside_repo(isolated, monkeypatch):
    from app.services.company_setup.io import backup_file, workroom_backup_dir

    src = isolated / "config" / "business.json"
    src.parent.mkdir()
    src.write_text('{"business_name":"Empire"}', encoding="utf-8")
    dest = backup_file(src, backup_dir=workroom_backup_dir())
    assert dest is not None
    assert dest.parent == workroom_backup_dir()
    assert "backups/company-setup" in dest.as_posix()
    assert list(src.parent.glob("*.bak")) == []


def test_mirror_preserves_file_mode(isolated, monkeypatch):
    from app.services.company_setup import store as store_mod

    target = isolated / "workroom-config.json"
    target.write_text('{"business_name":"Empire"}', encoding="utf-8")
    os.chmod(target, 0o644)
    bak = isolated / "off-repo-baks"
    bak.mkdir()
    monkeypatch.setattr(store_mod, "_WORKROOM_CONFIG", target)
    monkeypatch.setattr(store_mod, "in_test", lambda: False)
    monkeypatch.setattr(store_mod, "is_family_edition", lambda: False)
    monkeypatch.setattr(store_mod, "is_founder_edition", lambda: True)
    monkeypatch.setattr(store_mod, "workroom_backup_dir", lambda: bak)
    store_mod._maybe_mirror_patch({"legal_name": "Empire Workroom LLC"})
    assert stat.S_IMODE(target.stat().st_mode) == 0o644
    assert json.loads(target.read_text())["legal_name"] == "Empire Workroom LLC"
    assert list(target.parent.glob("workroom-config.json.*.bak")) == []
    assert list(bak.glob("workroom-config.json.*.bak"))


def test_interview_set_key_wins_over_later_hand_edit(isolated, monkeypatch):
    seed = _seed_file(isolated, monkeypatch, legal_name="Hand LLC")
    from app.services.company_setup.store import load_merged, save_section

    save_section("identity", {"legal_name": "Interview LLC", "dba": "Empire Workroom"})
    data = json.loads(seed.read_text())
    data["legal_name"] = "Hand Edited LLC"
    seed.write_text(json.dumps(data), encoding="utf-8")
    assert load_merged()["legal_name"] == "Interview LLC"


def test_concurrent_saves(isolated):
    from app.services.company_setup.store import load_merged, save_section

    errors = []

    def ident():
        try:
            save_section("identity", {"legal_name": "Concurrent LLC", "dba": "Concurrent"})
        except Exception as exc:
            errors.append(exc)

    def contact():
        try:
            save_section("contact", {
                "address": "9 Race Lane",
                "phone": "(301) 555-0100",
                "email": "race@example.com",
            })
        except Exception as exc:
            errors.append(exc)

    t1 = threading.Thread(target=ident)
    t2 = threading.Thread(target=contact)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert errors == []
    merged = load_merged()
    assert merged["legal_name"] == "Concurrent LLC"
    assert merged["contact"]["email"] == "race@example.com"


def test_family_edition_never_writes_workroom(monkeypatch, tmp_path, isolated):
    workroom = tmp_path / "workroom-biz.json"
    workroom.write_text(json.dumps({"business_phone": "KEEP", "founder_phones": ["1"]}), encoding="utf-8")
    amp = tmp_path / "amp"
    amp.mkdir()
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(amp))
    monkeypatch.delenv("EMPIRE_WHATSAPP_SECRETS_PATH", raising=False)
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


def test_maxine_and_amp_cannot_write_studio(monkeypatch, tmp_path, isolated):
    from app.services.company_setup.store import business_json_path, save_section

    save_section("identity", {"legal_name": "Studio LLC"})
    studio_file = isolated / "company" / "business.json"
    studio_before = studio_file.read_text()

    for edition in ("amp", "maxine"):
        root = tmp_path / edition
        root.mkdir(exist_ok=True)
        monkeypatch.setenv("EMPIRE_EDITION", edition)
        monkeypatch.setenv("EMPIRE_DATA_DIR", str(root))
        monkeypatch.delenv("EMPIRE_WHATSAPP_SECRETS_PATH", raising=False)
        from app.edition import apply_amp_process_paths

        apply_amp_process_paths()
        path = business_json_path()
        assert edition in str(path)
        assert isolated.as_posix() not in path.as_posix()
        save_section("identity", {"legal_name": f"{edition}-only", "dba": edition})
        assert f"{edition}-only" in path.read_text()
        assert studio_file.read_text() == studio_before
        assert f"{edition}-only" not in studio_file.read_text()


def test_path_override_refused_outside_edition_dir(isolated, monkeypatch, tmp_path):
    monkeypatch.setenv("COMPANY_SETUP_BUSINESS_PATH", str(tmp_path / "outside.json"))
    from app.edition import EditionPathError
    from app.services.company_setup.store import business_json_path

    with pytest.raises(EditionPathError):
        business_json_path()
    monkeypatch.setenv("EMPIRE_WHATSAPP_SECRETS_PATH", str(tmp_path / "wa.json"))
    from app.services.company_setup.whatsapp_secrets import secrets_path

    with pytest.raises(EditionPathError):
        secrets_path()


def test_path_overrides_ignored_outside_tests(isolated, monkeypatch, tmp_path):
    monkeypatch.setenv("COMPANY_SETUP_BUSINESS_PATH", str(tmp_path / "outside.json"))
    from app.services.company_setup import store as store_mod

    monkeypatch.setattr(store_mod, "in_test", lambda: False)
    path = store_mod.business_json_path()
    assert path == store_mod.edition_company_dir() / "business.json"


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
    mode = stat.S_IMODE((isolated / "secrets" / "whatsapp.json").stat().st_mode)
    assert mode == 0o600
    dir_mode = stat.S_IMODE((isolated / "secrets").stat().st_mode)
    assert dir_mode == 0o700
    again = client.get("/api/v1/onboarding/whatsapp", headers=_auth()).json()
    assert SECRET_TOKEN not in json.dumps(again)
    assert again["owner_numbers_count"] == 1
    audit = (isolated / "company" / "audit.jsonl").read_text()
    assert "owner_numbers_changed" in audit
    assert "+17035550111" not in audit


def test_whatsapp_newline_rejected(isolated):
    client = _client()
    bad = "good\nbad-token-must-not-leak"
    for path in ("/api/v1/onboarding/whatsapp", "/api/v1/whatsapp/keys"):
        res = client.post(path, headers=_auth(), json={"WHATSAPP_ACCESS_TOKEN": bad})
        assert res.status_code == 400
        assert bad not in res.text
        assert "good" not in res.text
        assert "bad-token-must-not-leak" not in res.text
        assert res.json()["detail"] == "Access token is invalid"


def test_whatsapp_e164_rejected(isolated):
    client = _client()
    res = client.post(
        "/api/v1/onboarding/whatsapp",
        headers=_auth(),
        json={"owner_numbers": ["7035550111"]},
    )
    assert res.status_code == 400
    assert "7035550111" not in res.text
    assert "E.164" in res.json()["detail"]


def test_whatsapp_unexpected_error_is_500_without_values(isolated, monkeypatch):
    def boom(_body):
        raise RuntimeError("boom leak-this-token-xyz")

    monkeypatch.setattr("app.routers.onboarding.save_secrets", boom)
    monkeypatch.setattr("app.services.company_setup.whatsapp_secrets.save_secrets", boom)
    client = _client()
    for path in ("/api/v1/onboarding/whatsapp", "/api/v1/whatsapp/keys"):
        res = client.post(path, headers=_auth(), json={"WHATSAPP_ACCESS_TOKEN": "ValidToken_123"})
        assert res.status_code == 500
        assert "ValidToken_123" not in res.text
        assert "leak-this-token-xyz" not in res.text
        assert res.json()["detail"] == "Could not save WhatsApp keys"


def test_webhook_status_has_no_backup(isolated):
    from app.services.company_setup.whatsapp_secrets import (
        record_webhook_challenge,
        webhook_status_path,
    )

    record_webhook_challenge(ok=True)
    path = webhook_status_path()
    assert path.exists()
    assert list(path.parent.glob("whatsapp_webhook_status.json.*.bak")) == []


def test_whatsapp_env_not_overridden(isolated, monkeypatch):
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "from-env-file")
    from app.services.company_setup.whatsapp_secrets import apply_to_environ, get_secret, save_secrets

    save_secrets({
        "WHATSAPP_ACCESS_TOKEN": "from-edition-file",
        "WHATSAPP_PHONE_NUMBER_ID": "1",
        "WHATSAPP_APP_SECRET": "sec",
        "WHATSAPP_VERIFY_TOKEN": "ver",
    })
    assert os.environ["WHATSAPP_ACCESS_TOKEN"] == "from-env-file"
    assert get_secret("WHATSAPP_ACCESS_TOKEN") == "from-env-file"
    apply_to_environ()
    assert os.environ["WHATSAPP_ACCESS_TOKEN"] == "from-env-file"


def test_whatsapp_keys_require_founder(isolated):
    client = _client()
    assert client.get("/api/v1/whatsapp/keys").status_code == 403
    assert client.post("/api/v1/whatsapp/keys", json={"WHATSAPP_ACCESS_TOKEN": SECRET_TOKEN}).status_code == 403


def test_webhook_records_only_success(isolated):
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
    assert status_panel()["webhook"]["reason"] == "never_challenged"
    good = client.get("/api/v1/whatsapp/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "hub-token", "hub.challenge": "99"})
    assert good.status_code == 200
    assert good.text == "99"
    assert status_panel()["webhook"]["verified"] is True


def test_rate_cards_agree_and_reject_bool(isolated):
    from app.services.company_setup.store import save_section
    from app.services.pricing.rate_cards import component_rates, invalidate_rate_overlay_cache, lookup_rate

    save_section("services", {
        "catalog": [{"name": "Roman shade", "rate": 70, "unit": "window"}],
        "labor_rate": 88,
        "rate_cards": {"workroom": {"labor_rate": 88, "missing_key": 12, "flag": True, "zero": 0}},
    })
    invalidate_rate_overlay_cache()
    assert component_rates("workroom")["labor_rate"] == 88
    assert lookup_rate("workroom", "labor_rate") == 88
    assert "missing_key" not in component_rates("workroom")
    save_section("services", {
        "catalog": [],
        "rate_cards": {"workroom": {"labor_rate": True}},
    })
    invalidate_rate_overlay_cache()
    # bool is skipped; the card falls back to the canonical 65.
    assert component_rates("workroom")["labor_rate"] == 65
    assert lookup_rate("workroom", "labor_rate") == component_rates("workroom")["labor_rate"]


def test_fabric_overlay_does_not_override_rafael(isolated):
    from app.config.fabric_cut_allowance import CONFIRM_WITH_RAFAEL, lookup_fabric_allowance
    from app.services.company_setup.store import save_section

    rafael = lookup_fabric_allowance(2.0)
    save_section("fabric", {
        "code_format": "V###-Color",
        "next_number": 3,
        "allowance_by_foam_thickness": [
            {"foam_thickness_in": 2.0, "allowance_in": 99.0, "status": "confirmed"},
            {"foam_thickness_in": 2.25, "allowance_in": 5.5},
            {"allowance_in": 4.0},
        ],
    })
    still = lookup_fabric_allowance(2.0)
    assert still["allowance_in"] == rafael["allowance_in"]
    added = lookup_fabric_allowance(2.25)
    assert added["allowance_in"] == 5.5
    assert added["status"] == CONFIRM_WITH_RAFAEL
    assert added.get("apply") == "per_side"
    missing = lookup_fabric_allowance(9.0)
    assert missing["allowance_in"] is None


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
