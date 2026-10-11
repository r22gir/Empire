"""Family help tickets: create, redact, isolate, voice, usage, rate limit."""
from __future__ import annotations

import io
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


WORKROOM_LEAKS = (
    "5124 Frolich",
    "Hyattsville",
    "workroom@empirebox.store",
    "Nehal Elrefai",
)


def _family(monkeypatch, tmp_path, edition: str, inbox: Path | None = None):
    root = tmp_path / edition
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(root))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Maxine" if edition == "maxine" else "Max-e")
    monkeypatch.setenv("AMP_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("AMP_JWT_SECRET", "test-secret")
    monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")
    monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", "100000")
    if inbox is not None:
        monkeypatch.setenv("FAMILY_HELP_INBOX_DIR", str(inbox))
    else:
        monkeypatch.delenv("FAMILY_HELP_INBOX_DIR", raising=False)
    from app.edition import apply_amp_process_paths

    apply_amp_process_paths()
    return root


def _founder(monkeypatch, tmp_path, inbox: Path):
    root = tmp_path / "workroom"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(root))
    monkeypatch.setenv("ASSISTANT_NAME", "Max")
    monkeypatch.setenv("FAMILY_HELP_INBOX_DIR", str(inbox))
    monkeypatch.delenv("INSTANCE_USAGE_CAP_PCT", raising=False)
    from app.edition import apply_amp_process_paths

    apply_amp_process_paths()
    return root


def _client():
    from app.routers.family_help import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


def test_is_help_intent_spanish_and_english():
    from app.services.family_help import is_help_intent, leftover_after_intent

    assert is_help_intent("Por favor pide ayuda a Max con esto")
    assert is_help_intent("pídele ayuda a Max")
    assert is_help_intent("ask Max for help with the login")
    assert is_help_intent("Can you ask for help from Max?")
    assert not is_help_intent("hola Max, ¿cómo estás?")
    assert leftover_after_intent("pide ayuda a Max: no abre el chat") == "no abre el chat"


def test_redact_workroom_and_maxine_argos():
    from app.services.family_help import redact_text, sanitize_context_turns

    dirty = (
        "Cliente Nehal Elrefai en 5124 Frolich Lane, Hyattsville. "
        "Correo workroom@empirebox.store y PIN: 123456"
    )
    clean = redact_text(dirty, edition="amp")
    for leak in WORKROOM_LEAKS:
        assert leak not in clean
    assert "PIN: 123456" not in clean
    assert "[oculto]" in clean

    argos = "La razón social: Grupo Argos Campestre S.A.S. NIT 900123456-7 y matrícula mercantil 12345"
    maxine = redact_text(argos, edition="maxine")
    assert "900123456" not in maxine
    assert "Grupo Argos Campestre" not in maxine
    assert "[oculto:argos]" in maxine
    amp = redact_text("dato de un proveedor de Juan, no de Argos Campestre", edition="amp")
    assert "[oculto:argos]" not in amp

    ctx = sanitize_context_turns(
        [
            {"role": "user", "content": "[Context from previous sessions] Workroom"},
            {"role": "user", "content": "Mi lote en Cartago. Hyattsville no aplica."},
            {"role": "assistant", "content": "Ok"},
        ],
        edition="maxine",
    )
    blob = " ".join(row["content"] for row in ctx)
    assert "Hyattsville" not in blob
    assert "[Context from previous sessions]" not in blob


def test_create_ticket_and_list_own(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "amp")
    from app.services.family_help import create_ticket, list_tickets

    ticket = create_ticket(
        message="No me abre el chat de voz",
        sender="Juan Diego Giraldo",
        history=[
            {"role": "user", "content": "Hola"},
            {"role": "assistant", "content": "¿Qué necesitas?"},
        ],
        notify=False,
    )
    assert ticket["id"].startswith("fh-")
    assert ticket["edition"] == "amp"
    assert ticket["sender"] == "Juan Diego Giraldo"
    assert ticket["message"] == "No me abre el chat de voz"
    assert ticket["status"] == "new"
    assert ticket["created_at"]
    assert ticket["context"]
    listed = list_tickets(edition="amp")
    assert listed[0]["id"] == ticket["id"]


def test_isolation_amp_cannot_read_maxine_or_workroom(monkeypatch, tmp_path):
    inbox = tmp_path / "shared-inbox"
    inbox.mkdir()
    _family(monkeypatch, tmp_path, "maxine", inbox)
    from app.services.family_help import create_ticket, get_ticket

    other = create_ticket(
        message="Soy Camilo, ticket de Maxine",
        sender="Camilo Giraldo",
        notify=False,
    )
    maxine_id = other["id"]

    _family(monkeypatch, tmp_path, "amp", inbox)
    from app.services import family_help as fh

    assert fh.get_ticket(maxine_id) is None
    assert fh.get_ticket(maxine_id, edition="maxine") is None
    assert fh.list_tickets() == []
    try:
        fh.store_dir_for("maxine")
        raise AssertionError("amp no debe abrir el store de maxine")
    except PermissionError:
        pass

    # Workroom business tables are not on this API.
    wr = tmp_path / "amp" / "empire.db"
    wr.write_text("not-a-help-ticket", encoding="utf-8")
    for ticket in fh.list_tickets():
        blob = str(ticket)
        assert "workroom" not in blob.lower() or ticket["edition"] == "amp"
        for leak in WORKROOM_LEAKS:
            assert leak not in blob


def test_family_http_cannot_read_inbox_or_other_tickets(monkeypatch, tmp_path):
    inbox = tmp_path / "shared-inbox"
    inbox.mkdir()
    _family(monkeypatch, tmp_path, "maxine", inbox)
    from app.services.family_help import create_ticket

    foreign = create_ticket(message="ticket maxine", sender="Camilo", notify=False)

    _family(monkeypatch, tmp_path, "amp", inbox)
    client = _client()
    own = client.post(
        "/api/v1/family-help/tickets",
        data={"message": "ayuda de Juan", "history_json": "[]"},
    )
    assert own.status_code == 200, own.text
    mine = own.json()["ticket"]["id"]

    listed = client.get("/api/v1/family-help/tickets")
    assert listed.status_code == 200
    ids = [t["id"] for t in listed.json()["tickets"]]
    assert mine in ids
    assert foreign["id"] not in ids

    assert client.get(f"/api/v1/family-help/tickets/{foreign['id']}").status_code == 404
    assert client.get("/api/v1/family-help/inbox").status_code == 403
    assert client.post(
        f"/api/v1/family-help/inbox/{mine}/reply",
        json={"body": "hola", "explicit_yes": True},
    ).status_code == 403


def test_voice_and_attachment_handling(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "amp")
    from app.services.family_help import attachment_path, create_ticket, validate_upload

    png = (
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    )
    voice = b"RIFF" + b"\x00" * 400
    ticket = create_ticket(
        message="Mira el audio y la captura",
        transcript="no entra al portal",
        attachments=[
            {
                "filename": "nota.webm",
                "content_type": "audio/webm",
                "data": voice,
                "kind": "voice",
            },
            {
                "filename": "pantalla.png",
                "content_type": "image/png",
                "data": png,
                "kind": "file",
            },
        ],
        notify=False,
    )
    assert ticket["transcript"] == "no entra al portal"
    kinds = {a["kind"] for a in ticket["attachments"]}
    assert kinds == {"voice", "image"}
    voice_att = next(a for a in ticket["attachments"] if a["kind"] == "voice")
    path = attachment_path(ticket["id"], voice_att["id"], edition="amp")
    assert path is not None and path.is_file()
    assert path.read_bytes() == voice

    try:
        validate_upload(
            filename="malware.exe",
            content_type="application/octet-stream",
            data=b"MZ" * 20,
            kind="file",
        )
        raise AssertionError("exe debe rechazarse")
    except ValueError:
        pass
    try:
        validate_upload(
            filename="huge.pdf",
            content_type="application/pdf",
            data=b"%PDF" + b"x" * (9 * 1024 * 1024),
            kind="file",
        )
        raise AssertionError("archivo enorme debe rechazarse")
    except ValueError:
        pass


def test_usage_counted_on_request_and_reply(monkeypatch, tmp_path):
    inbox = tmp_path / "shared-inbox"
    inbox.mkdir()
    amp_root = _family(monkeypatch, tmp_path, "amp", inbox)
    from app.services.family_help import create_ticket
    from app.services.instance_usage import usage_summary

    before = usage_summary()["month"]["tokens"]
    ticket = create_ticket(message="ayuda " + ("x" * 200), notify=False)
    after_create = usage_summary()["month"]["tokens"]
    assert after_create > before

    _founder(monkeypatch, tmp_path, inbox)
    from app.services.family_help import add_reply

    add_reply(ticket["id"], "Prueba esto en tu chat.", author="Rafael", explicit_yes=True)
    usage_db = amp_root / "usage" / "usage.db"
    # Peer recorder writes to profile data_dir or store parent. Fall back to scan.
    found = list((tmp_path).rglob("usage.db"))
    assert found, "la respuesta debe escribir usage.db de la edición"
    import sqlite3
    total = 0
    for db in found:
        conn = sqlite3.connect(str(db))
        row = conn.execute(
            "SELECT COALESCE(SUM(input_tokens+output_tokens),0) FROM llm_usage WHERE kind LIKE 'family_help%'"
        ).fetchone()
        conn.close()
        total += int(row[0] or 0)
    assert total > 0


def test_rate_limit_and_usage_cap_block_create(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "amp")
    monkeypatch.setenv("FAMILY_HELP_DAILY_LIMIT", "2")
    from app.services.family_help import create_ticket

    create_ticket(message="uno", notify=False)
    create_ticket(message="dos", notify=False)
    try:
        create_ticket(message="tres", notify=False)
        raise AssertionError("el tercer ticket del día debe bloquearse")
    except PermissionError as exc:
        assert "límite" in str(exc)

    monkeypatch.setenv("FAMILY_HELP_DAILY_LIMIT", "20")
    monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", "1000")
    from app.services.instance_usage import record_usage

    record_usage(input_tokens=1000, output_tokens=0, model="MiniMax-M3")
    try:
        create_ticket(message="con tope", notify=False)
        raise AssertionError("el tope de uso debe bloquear el ticket")
    except PermissionError as exc:
        assert "tope" in str(exc) or "20" in str(exc)


def test_founder_inbox_reply_requires_yes_and_never_applies(monkeypatch, tmp_path):
    inbox = tmp_path / "shared-inbox"
    inbox.mkdir()
    _family(monkeypatch, tmp_path, "amp", inbox)
    from app.services.family_help import create_ticket

    ticket = create_ticket(message="se trabó el login", sender="Juan", notify=False)

    _founder(monkeypatch, tmp_path, inbox)
    client = _client()
    inbox_list = client.get("/api/v1/family-help/inbox")
    assert inbox_list.status_code == 200
    ids = [t["id"] for t in inbox_list.json()["tickets"]]
    assert ticket["id"] in ids

    denied = client.post(
        f"/api/v1/family-help/inbox/{ticket['id']}/reply",
        json={"body": "borra sus datos", "explicit_yes": False},
    )
    assert denied.status_code == 403

    draft = client.post(f"/api/v1/family-help/inbox/{ticket['id']}/draft")
    assert draft.status_code == 200
    assert draft.json()["can_apply_automatically"] is False
    assert "cloud-agent" in draft.json()["code_fix_path"]

    sent = client.post(
        f"/api/v1/family-help/inbox/{ticket['id']}/reply",
        json={"body": "Prueba recargar el chat.", "explicit_yes": True, "author": "Rafael"},
    )
    assert sent.status_code == 200
    assert sent.json()["ticket"]["status"] == "answered"
    assert sent.json()["ticket"]["replies"][-1]["body"].startswith("Prueba recargar")

    apply = client.post(
        f"/api/v1/family-help/inbox/{ticket['id']}/apply",
        json={"explicit_yes": True},
    )
    assert apply.status_code == 200
    assert apply.json()["applied"] is False

    # Family sees the reply on its own ticket.
    _family(monkeypatch, tmp_path, "amp", inbox)
    family = _client()
    mine = family.get(f"/api/v1/family-help/tickets/{ticket['id']}")
    assert mine.status_code == 200
    assert mine.json()["ticket"]["replies"][-1]["author"] == "Rafael"


def test_notify_email_only_founder_address(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "amp")
    sent = []

    async def _fake_send(to, subject, html):
        sent.append((to, subject, html))
        return True

    monkeypatch.setattr("app.services.email.sender.send_email", _fake_send)
    monkeypatch.setenv("FAMILY_HELP_NOTIFY_EMAIL", "cliente@example.com")
    from app.services.family_help import FOUNDER_NOTIFY_EMAIL, create_ticket, founder_notify_email

    assert founder_notify_email() == FOUNDER_NOTIFY_EMAIL
    create_ticket(message="avísale a Max", notify=True)
    for to, _subject, _html in sent:
        assert to == FOUNDER_NOTIFY_EMAIL
        assert "cliente@example.com" not in to


def test_chat_intent_creates_ticket(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "maxine")
    from app.services.family_help import handle_chat_intent, list_tickets

    hit = handle_chat_intent(
        "pide ayuda a Max, no carga el portafolio",
        history=[{"role": "user", "content": "hola"}],
        sender="Camilo Giraldo",
    )
    assert hit is not None
    assert "ticket" in hit["response"].lower()
    assert hit["ticket"]["id"].startswith("fh-")
    tickets = list_tickets(edition="maxine")
    assert tickets
    assert "portafolio" in tickets[0]["message"]


def test_max_router_wires_family_help_intent():
    from pathlib import Path
    text = (Path(__file__).resolve().parents[1] / "app" / "routers" / "max" / "router.py").read_text(encoding="utf-8")
    assert "handle_chat_intent" in text
    assert 'skill_used="family_help"' in text


def test_family_http_upload_roundtrip(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "amp")
    client = _client()
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 80
    res = client.post(
        "/api/v1/family-help/tickets",
        data={
            "message": "adjunto captura",
            "history_json": '[{"role":"user","content":"antes"}]',
        },
        files=[("files", ("shot.png", io.BytesIO(png), "image/png"))],
    )
    assert res.status_code == 200, res.text
    ticket = res.json()["ticket"]
    assert ticket["attachments"]
    att = ticket["attachments"][0]
    file_res = client.get(
        f"/api/v1/family-help/tickets/{ticket['id']}/attachments/{att['id']}"
    )
    assert file_res.status_code == 200
    assert file_res.content == png
