"""Family-edition chrome, login redirect, WhatsApp gate, Maxine unit, presentation layout."""
from __future__ import annotations

import subprocess
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


def test_family_chrome_runs_on_node_without_strip_types():
    script = """
import { familyHomeRedirect, navGroupLabel, presentationChrome, searchPlaceholder } from './empire-command-center/app/lib/familyChrome.mjs';
if (familyHomeRedirect('amp', '/', false) !== '/login') throw new Error('amp home');
if (familyHomeRedirect('maxine', '/', false) !== '/login') throw new Error('maxine home');
if (familyHomeRedirect('amp', '/', true) !== null) throw new Error('session');
if (familyHomeRedirect('workroom', '/', false) !== null) throw new Error('workroom');
if (familyHomeRedirect('amp', '/login', false) !== null) throw new Error('other path');
const maxine = presentationChrome('maxine', 'Maxine');
if (maxine.header !== 'Maxine') throw new Error(maxine.header);
if (maxine.presentation !== 'Presentación') throw new Error(maxine.presentation);
if (maxine.presentationMode !== 'Modo presentación') throw new Error(maxine.presentationMode);
if (!maxine.placeholder.includes('Maxine')) throw new Error(maxine.placeholder);
if (maxine.simliFace !== 'Solo el rostro de Simli') throw new Error(maxine.simliFace);
const maxe = presentationChrome('amp', '');
if (maxe.header !== 'Max-e') throw new Error(maxe.header);
const workroom = presentationChrome('workroom', 'MAX');
if (workroom.header !== 'MAX — Empire AI') throw new Error(workroom.header);
if (workroom.simliFace !== 'Simli face only') throw new Error(workroom.simliFace);
if (navGroupLabel('amp', 'command', 'COMMAND') !== 'Comando') throw new Error('command');
if (navGroupLabel('maxine', 'business', 'BUSINESS') !== 'Negocio') throw new Error('business');
if (navGroupLabel('workroom', 'command', 'COMMAND') !== 'COMMAND') throw new Error('workroom nav');
if (searchPlaceholder('amp') !== 'Buscar cualquier cosa...') throw new Error('search es');
if (searchPlaceholder('workroom') !== 'Search anything...') throw new Error('search en');
process.stdout.write('ok');
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == "ok"
    device_test = (ROOT / "backend" / "tests" / "test_device_access_help.py").read_text(encoding="utf-8")
    assert "--experimental-strip-types" not in device_test
    assert "deviceAccess.mjs" in device_test


def test_presentation_layout_keeps_a_square_uncropped_face():
    screen = (ROOT / "empire-command-center" / "app" / "components" / "screens" / "PresentationScreen.tsx").read_text(encoding="utf-8")
    html = (ROOT / "empire-command-center" / "public" / "avatar.html").read_text(encoding="utf-8")
    assert "presentationChrome" in screen
    assert "chrome.header" in screen
    assert "MAX — Empire AI" not in screen
    assert "aspect-ratio: 1 / 1" in screen
    assert "orientation: landscape" in screen
    assert "orientation: portrait" in screen
    assert "safe-area-inset" in screen
    assert 'className="presentation-caption"' in screen
    assert "object-fit: contain" in html
    assert "object-fit: cover" not in html
    assert "position: static" in html
    assert "showBadge('')" in html
    assert "enableSFU" in (ROOT / "empire-command-center" / "public" / "simli-face.js").read_text(encoding="utf-8")
    layout = (ROOT / "empire-command-center" / "app" / "layout.tsx").read_text(encoding="utf-8")
    assert "viewportFit: 'cover'" in layout


def test_maxine_unit_uses_its_tree_lock_and_secondary_worker():
    text = (ROOT / "deploy" / "empire-maxine.service").read_text(encoding="utf-8")
    assert "WorkingDirectory=/home/rg/empire-maxine/backend" in text
    assert "ExecStart=/home/rg/empire-maxine/backend/venv/bin/python3" in text
    assert "/home/rg/empire-repo" not in text
    assert "Environment=EMPIRE_WORKER_LOCK=/data/maxine/run/empire_primary_worker.lock" in text
    assert "/tmp/empire_primary_worker.lock" in text
    assert "ExecStartPre=" in text
    assert "--workers 2" in text
    assert "Environment=EMPIRE_WORKER_LOCK=/tmp/empire_primary_worker.lock" not in text


def _client():
    from app.middleware.edition_gate import amp_access_middleware
    from app.routers.whatsapp import router as whatsapp_router

    app = FastAPI()
    app.middleware("http")(amp_access_middleware)
    app.include_router(whatsapp_router, prefix="/api/v1")
    return TestClient(app)


def test_whatsapp_webhook_skips_the_access_gate(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AMP_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("AMP_JWT_SECRET", "test-secret")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "1234567890")
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "app-secret")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "verify-me")
    monkeypatch.setenv("WHATSAPP_OWNER_NUMBERS", "573001112233")
    monkeypatch.delenv("FOUNDER_EMAIL", raising=False)

    from app.edition import access_exempt

    assert access_exempt("GET", "/api/v1/whatsapp/webhook") is True
    assert access_exempt("POST", "/api/v1/whatsapp/webhook") is True
    assert access_exempt("GET", "/api/v1/whatsapp/status") is False

    client = _client()
    status = client.get("/api/v1/whatsapp/status")
    assert status.status_code == 403
    assert status.json()["code"] == "sin_acceso"

    bad = client.get(
        "/api/v1/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "abc"},
    )
    assert bad.status_code == 403
    assert bad.json().get("code") != "sin_acceso"

    ok = client.get(
        "/api/v1/whatsapp/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "challenge-123"},
    )
    assert ok.status_code == 200
    assert ok.text == "challenge-123"

    posted = client.post(
        "/api/v1/whatsapp/webhook",
        content=b"{}",
        headers={"X-Hub-Signature-256": "sha256=dead"},
    )
    assert posted.status_code == 403
    body = posted.json()
    assert body["reason"] == "Firma inválida"
    assert body.get("code") != "sin_acceso"
    assert "sha256=dead" not in posted.text
