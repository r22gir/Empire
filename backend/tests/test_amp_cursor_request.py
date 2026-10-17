"""7a — Pedir a Cursor queue. tmp EMPIRE_DATA_DIR only. No live senders."""
from __future__ import annotations

import io
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
    b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _env(monkeypatch, tmp_path, edition="amp"):
    root = tmp_path / edition
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(root))
    monkeypatch.setenv("EMPIRE_TASK_DB", str(root / "empire.db"))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Max-e")
    monkeypatch.setenv("AMP_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("AMP_JWT_SECRET", "test-secret")
    monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")
    monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", "10000000")
    monkeypatch.setenv("CURSOR_REQUEST_EST_TOKENS", "150000")
    monkeypatch.setenv("FAMILY_ABSOLUTE_MAX_PCT", "40")
    monkeypatch.delenv("EMPIRE_USAGE_BASELINE_MONTHLY_USD", raising=False)
    monkeypatch.setattr("app.services.instance_usage._usage_data_roots", lambda: [root])
    return root


def _raise_send(*_a, **_k):
    raise RuntimeError("tests must not send email")


def _raise_wa(*_a, **_k):
    raise RuntimeError("tests must not send WhatsApp")


def _patch_senders(monkeypatch):
    monkeypatch.setattr("app.services.max.email_service.EmailService.send", _raise_send, raising=False)
    try:
        monkeypatch.setattr("app.services.whatsapp_cloud.send_text", _raise_wa)
    except Exception:
        pass


def _client():
    from app.middleware.edition_gate import amp_access_middleware
    from app.routers.cursor_requests import router

    app = FastAPI()
    app.middleware("http")(amp_access_middleware)
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def _cookie(client, email="owner@example.com"):
    from app.services.amp_access import SESSION_COOKIE, create_session_token

    client.cookies.set(SESSION_COOKIE, create_session_token(email))


def test_store_create_list_show_edition_from_env(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _patch_senders(monkeypatch)
    from app.services.cursor_requests import create, get, list_requests

    item = create(title="Arreglar el login", body="El botón no abre, manito.", created_by="owner@example.com")
    assert item["edition"] == "amp"
    assert item["status"] == "queued"
    assert item["title"] == "Arreglar el login"
    listed = list_requests()
    assert listed[0]["id"] == item["id"]
    assert get(item["id"])["body"].startswith("El botón")


def test_invalid_transitions_and_decision_only_from_pr_open(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.cursor_requests import (
        CursorRequestError,
        create,
        owner_decision,
        set_status_cli,
    )

    item = create(title="Cambio chico", body="Porque el formulario se traba.")
    try:
        owner_decision(item["id"], "approve")
        assert False, "decision must require pr_open"
    except CursorRequestError:
        pass
    set_status_cli(item["id"], "in_progress")
    set_status_cli(item["id"], "pr_open", pr_url="https://github.com/r22gir/Empire/pull/184")
    try:
        set_status_cli(item["id"], "owner_approved")
        assert False, "CLI cannot set owner_approved"
    except CursorRequestError:
        pass
    decided = owner_decision(item["id"], "approve", "ok")
    assert decided["status"] == "owner_approved"


def test_router_multipart_png_rejects_non_image_and_over_five(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _patch_senders(monkeypatch)
    client = _client()
    _cookie(client)
    ok = client.post(
        "/api/v1/edition/cursor-requests",
        data={"title": "Una captura", "body": "El chat se ve cortado en el celular."},
        files=[("files", ("shot.png", io.BytesIO(TINY_PNG), "image/png"))],
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["screenshots"]

    bad = client.post(
        "/api/v1/edition/cursor-requests",
        data={"title": "Texto", "body": "Esto no es imagen."},
        files=[("files", ("note.txt", io.BytesIO(b"hello"), "text/plain"))],
    )
    assert bad.status_code == 400

    too_many = client.post(
        "/api/v1/edition/cursor-requests",
        data={"title": "Muchas", "body": "Seis archivos no caben."},
        files=[("files", (f"{i}.png", io.BytesIO(TINY_PNG), "image/png")) for i in range(6)],
    )
    assert too_many.status_code == 400


def test_soft_cap_accept_and_reject(monkeypatch, tmp_path):
    root = _env(monkeypatch, tmp_path)
    from app.services.cursor_requests import MENSAJE_PAUSED, create
    from app.services.instance_usage import record_usage

    create(title="Bajo el tope", body="Un arreglo chico del botón.")
    import sqlite3
    conn = sqlite3.connect(root / "usage" / "usage.db")
    row = conn.execute(
        "SELECT kind, provider, model, input_tokens FROM llm_usage WHERE kind = 'cursor_request'"
    ).fetchone()
    conn.close()
    assert row == ("cursor_request", "cursor", "cloud-agent", 150000)

    usage_db = root / "usage" / "usage.db"
    if usage_db.is_file():
        usage_db.unlink()
    monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", "1000")
    record_usage(input_tokens=250, output_tokens=0, model="MiniMax-M3")
    try:
        create(title="En pausa", body="Esto no debe pasar sin señal.")
        assert False, "paused create must fail"
    except Exception as exc:
        assert MENSAJE_PAUSED in str(exc)

    from datetime import datetime, timezone
    folder = root / "founder-signal"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "status.json").write_text(json.dumps({
        "schema": 1,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "founder_active": False,
        "founder_last_active_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "reserve_ok": True,
        "overage_allowed": True,
        "reason": "inactive_reserve_ok",
    }), encoding="utf-8")
    extra = create(title="Tiempo extra", body="Rafael no está, se puede mandar.")
    assert extra["cap_state"] == "overage"
    assert extra["status"] == "queued"


def test_cli_round_trip_and_guards(monkeypatch, tmp_path):
    root = _env(monkeypatch, tmp_path)
    from app.cli.cursor_requests import main
    from app.services.cursor_requests import create

    item = create(title="CLI", body="Probar list/show/set-status.")
    assert main(["list", "--status", "queued", "--json"]) == 0
    assert main(["show", item["id"], "--json"]) == 0
    assert main(["can-launch", item["id"], "--json"]) == 0
    assert main(["set-status", item["id"], "--status", "in_progress", "--json"]) == 0
    assert main([
        "set-status", item["id"], "--status", "pr_open",
        "--pr-url", "https://example.com/not-allowed",
        "--json",
    ]) == 2
    assert main([
        "set-status", item["id"], "--status", "pr_open",
        "--pr-url", "https://github.com/r22gir/Empire/pull/184",
        "--note-es", "PR listo, manito.",
        "--json",
    ]) == 0

    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "other"))
    (tmp_path / "other").mkdir(exist_ok=True)
    assert main(["list", "--json"]) == 2


def test_no_outbound_from_create(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    _patch_senders(monkeypatch)
    from app.services.cursor_requests import create
    from app.services.max.email_service import EmailService

    create(title="Sin envío", body="No manda correo ni WhatsApp.")
    try:
        EmailService.send(None, to="owner@example.com", subject="x", body_html="x")  # type: ignore
        assert False
    except RuntimeError as exc:
        assert "must not send email" in str(exc)
