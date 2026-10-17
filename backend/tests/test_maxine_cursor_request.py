"""Pedir a Cursor queue: store, router, CLI, soft cap. Mocked only."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def _env(monkeypatch, tmp_path: Path, edition="maxine"):
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", "1000000")
    monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")
    monkeypatch.setenv("FAMILY_ABSOLUTE_MAX_PCT", "40")
    monkeypatch.setenv("AMP_OWNER_EMAIL", "camilo.owner@example.com")
    monkeypatch.setenv("AMP_JWT_SECRET", "test-secret")
    monkeypatch.setenv("CURSOR_REQUEST_EST_TOKENS", "60000")
    monkeypatch.setattr("app.services.instance_usage._usage_data_roots", lambda: [tmp_path])
    monkeypatch.delenv("FOUNDER_EMAIL", raising=False)


@pytest.fixture(autouse=True)
def _no_outbound(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("no outbound email/WhatsApp/SMS from Pedir a Cursor")

    monkeypatch.setattr("app.services.max.email_service.EmailService.send", _boom)
    for target in (
        "app.services.max.telegram_bot.telegram_bot.send_message",
        "app.services.whatsapp_cloud.send_text",
    ):
        try:
            monkeypatch.setattr(target, _boom)
        except Exception:
            pass


def _client():
    from app.middleware.edition_gate import amp_access_middleware
    from app.routers.cursor_requests import router

    app = FastAPI()
    app.middleware("http")(amp_access_middleware)
    app.include_router(router, prefix="/api/v1/edition/cursor-requests")
    return TestClient(app)


def _cookie(client, email="camilo.owner@example.com"):
    from app.services.amp_access import SESSION_COOKIE, create_session_token

    client.cookies.set(SESSION_COOKIE, create_session_token(email))


def test_store_create_list_show_forces_edition(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.cursor_requests import create_request, get_request, list_requests

    row = create_request(
        title="Arreglar el resumen",
        body="El resumen de la mañana no muestra las tareas vencidas.",
        created_by="camilo.owner@example.com",
    )
    assert row["edition"] == "maxine"
    assert row["status"] == "queued"
    assert row["cap_state"] == "base"
    assert row["est_tokens"] == 60000
    listed = list_requests()
    assert listed[0]["id"] == row["id"]
    assert get_request(row["id"])["title"] == "Arreglar el resumen"

    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "amp"))
    (tmp_path / "amp").mkdir()
    with pytest.raises(Exception):
        get_request(row["id"])


def test_invalid_transition_and_decision_only_from_pr_open(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.cursor_requests import (
        CursorRequestError,
        create_request,
        owner_decision,
        set_status,
    )

    row = create_request(title="Cambio chiquito", body="Porque el botón no se ve.")
    with pytest.raises(CursorRequestError):
        owner_decision(row["id"], decision="approve")
    with pytest.raises(CursorRequestError):
        set_status(row["id"], status="done")
    moved = set_status(row["id"], status="in_progress")
    assert moved["status"] == "in_progress"
    with pytest.raises(CursorRequestError):
        set_status(
            row["id"],
            status="pr_open",
            pr_url="https://evil.example.com/pull/1",
        )
    opened = set_status(
        row["id"],
        status="pr_open",
        pr_url="https://github.com/r22gir/Empire/pull/99",
        note_es="Listo para que lo mires, manito.",
    )
    assert opened["status"] == "pr_open"
    approved = owner_decision(row["id"], decision="approve", note="sí")
    assert approved["status"] == "owner_approved"


def test_router_multipart_png_rejects_non_image_and_too_many(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    client = _client()
    _cookie(client)
    ok = client.post(
        "/api/v1/edition/cursor-requests",
        data={"title": "Captura", "body": "El mapa de lotes se corta en el celular."},
        files=[("files", ("shot.png", PNG_1X1, "image/png"))],
    )
    assert ok.status_code == 200, ok.text
    row = ok.json()
    shot = Path(tmp_path) / row["screenshots"][0]
    assert shot.is_file()
    assert shot.read_bytes().startswith(b"\x89PNG")

    bad = client.post(
        "/api/v1/edition/cursor-requests",
        data={"title": "Mal archivo", "body": "Esto no es imagen."},
        files=[("files", ("note.txt", b"hello", "text/plain"))],
    )
    assert bad.status_code == 409

    many = [("files", (f"{i}.png", PNG_1X1, "image/png")) for i in range(6)]
    too = client.post(
        "/api/v1/edition/cursor-requests",
        data={"title": "Demasiadas", "body": "Seis capturas."},
        files=many,
    )
    assert too.status_code == 409


def test_soft_cap_accept_and_reject(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.cursor_requests import MSG_CURSOR_PAUSED, cap_gate, create_request
    from app.services.instance_usage import record_usage

    assert cap_gate(title="hola") is None
    create_request(title="Bajo el tope", body="Un arreglo chiquito.")

    record_usage(input_tokens=150000, output_tokens=0, provider="minimax")
    refused = cap_gate(title="hola")
    assert refused == MSG_CURSOR_PAUSED

    folder = tmp_path / "founder-signal"
    folder.mkdir()
    from datetime import datetime, timezone

    (folder / "status.json").write_text(
        json.dumps(
            {
                "schema": 1,
                "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "founder_active": False,
                "founder_last_active_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "reserve_ok": True,
                "overage_allowed": True,
                "reason": "inactive_reserve_ok",
            }
        ),
        encoding="utf-8",
    )
    assert cap_gate(title="hola") is None
    extra = create_request(title="Tiempo extra", body="Rafael no está.")
    assert extra["cap_state"] == "overage"

    from app.services.instance_usage import _connect

    conn = _connect()
    rows = conn.execute("SELECT kind, provider, input_tokens FROM llm_usage").fetchall()
    conn.close()
    cursor_rows = [r for r in rows if r["kind"] == "cursor_request"]
    assert cursor_rows
    assert all(r["provider"] == "cursor" for r in cursor_rows)
    from app.services.instance_usage import usage_summary as _summary
    split = _summary()
    assert split["cursor"]["tokens"] >= 60000
    assert split["minimax"]["tokens"] == split["month"]["tokens"] - split["cursor"]["tokens"]
    assert split["month"]["tokens"] == split["minimax"]["tokens"] + split["cursor"]["tokens"]
    assert "MiniMax" in (split.get("limit_note_es") or "")
    assert "Pedir a Cursor" in (split.get("limit_note_es") or "")


def test_cli_round_trip_and_guards(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.cli.cursor_requests import main
    from app.services.cursor_requests import create_request

    row = create_request(title="CLI pedido", body="Para que Chief e lo vea.")
    assert main(["list", "--status", "queued", "--json"]) == 0
    assert main(["show", row["id"], "--json"]) == 0
    assert main(["can-launch", row["id"], "--json"]) == 0
    assert main(["set-status", row["id"], "--status", "in_progress", "--json"]) == 0
    bad_url = main(
        [
            "set-status",
            row["id"],
            "--status",
            "pr_open",
            "--pr-url",
            "https://example.com/p/1",
            "--json",
        ]
    )
    assert bad_url == 2
    assert (
        main(
            [
                "set-status",
                row["id"],
                "--status",
                "pr_open",
                "--pr-url",
                "https://github.com/r22gir/Empire/pull/12",
                "--note-es",
                "Míralo cuando puedas, manito.",
                "--json",
            ]
        )
        == 0
    )

    monkeypatch.setenv("EMPIRE_DATA_DIR", "/data/amp")
    from app.services.cursor_requests import CursorRequestError, assert_edition_data_dir

    with pytest.raises(CursorRequestError):
        assert_edition_data_dir(allow_tmp=False)


def test_assert_data_dir_rejects_folder_named_maxine(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.cursor_requests import CursorRequestError, assert_edition_data_dir

    decoy = tmp_path / "maxine"
    decoy.mkdir()
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(decoy))
    with pytest.raises(CursorRequestError, match="/data/maxine"):
        assert_edition_data_dir(allow_tmp=False)
    monkeypatch.setenv("EMPIRE_DATA_DIR", "/data/maxine")
    assert assert_edition_data_dir(allow_tmp=False) == Path("/data/maxine").resolve()


def test_default_estimate_is_60000(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    monkeypatch.delenv("CURSOR_REQUEST_EST_TOKENS", raising=False)
    from app.services.cursor_requests import estimated_tokens

    assert estimated_tokens() == 60000


def test_decline_refunds_cursor_estimate(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    from app.services.cursor_requests import create_request, set_status
    from app.services.instance_usage import usage_summary

    row = create_request(title="No se hará", body="Chief e lo va a rechazar.")
    before = usage_summary()
    assert before["cursor"]["tokens"] == 60000
    assert before["month"]["tokens"] == 60000
    assert before["minimax"]["tokens"] == 0
    declined = set_status(row["id"], status="declined")
    assert declined["status"] == "declined"
    after = usage_summary()
    assert after["cursor"]["tokens"] == 0
    assert after["month"]["tokens"] == 0
    assert after["minimax"]["tokens"] == 0


def test_frontend_spanish_strings_present():
    from pathlib import Path

    page = Path(__file__).resolve().parents[2] / "empire-command-center" / "app" / "pedir-cursor" / "page.tsx"
    text = page.read_text(encoding="utf-8")
    assert "Pedir a Cursor" in text
    assert "¿Qué necesitas y por qué?" in text
    assert "Aprobar" in text
    assert "Pedir cambios" in text
    assert "paused" in text
    copy = Path(__file__).resolve().parents[2] / "empire-command-center" / "app" / "lib" / "pedirCursorCopy.ts"
    blob = copy.read_text(encoding="utf-8")
    assert "En cola" in blob
    assert "Rafael da el sí final" in blob
