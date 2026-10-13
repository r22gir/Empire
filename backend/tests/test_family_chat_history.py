"""Family chat history: full ids, per-user isolation, no live /data writes."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


def _family_env(monkeypatch, tmp_path, edition="amp"):
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Maxine" if edition == "maxine" else "Max-e")
    monkeypatch.setenv("AMP_OWNER_EMAIL", "owner@example.com")
    monkeypatch.setenv("AMP_JWT_SECRET", "test-family-chat-secret")
    monkeypatch.delenv("FOUNDER_EMAIL", raising=False)


def _workroom_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.delenv("EMPIRE_DATA_DIR", raising=False)
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "en")


def _client(tmp_path):
    from app.api.v1.chats import router as chats_router
    from app.middleware.edition_gate import amp_access_middleware

    app = FastAPI()
    app.middleware("http")(amp_access_middleware)
    app.include_router(chats_router, prefix="/api/v1")
    return TestClient(app)


def _cookie(client, email):
    from app.services.amp_access import SESSION_COOKIE, create_session_token
    from app.services.amp_allowlist import add_entry, is_allowed

    if not is_allowed(email=email):
        add_entry(email=email, role="member")
    client.cookies.set(SESSION_COOKIE, create_session_token(email))


def test_workroom_put_upserts_full_client_id(monkeypatch, tmp_path):
    import asyncio

    _workroom_env(monkeypatch, tmp_path)
    from app.api.v1 import chats

    monkeypatch.setattr(chats, "CHATS_DIR", tmp_path)
    chat_id = "30ea0046-2bc9-461c-8215-5793e12874cd"
    req = chats.UpdateChatRequest(messages=[{"role": "user", "content": "finance readiness"}])
    response = asyncio.run(chats.update_chat(chat_id, req))
    assert response == {"status": "created", "chat_id": chat_id}
    saved = json.loads((tmp_path / "founder" / f"{chat_id}.json").read_text())
    assert saved["id"] == chat_id
    assert saved["timezone"] == "America/New_York"
    assert not (tmp_path / "founder" / f"{chat_id[:8]}.json").exists()


def test_persist_exchange_uses_full_id_and_new_york_zone(monkeypatch, tmp_path):
    _workroom_env(monkeypatch, tmp_path)
    from app.services.chat_history_store import persist_exchange

    chat_id = "30ea0046-2bc9-461c-8215-5793e12874cd"
    persist_exchange(
        chat_id=chat_id,
        user_message="hola",
        assistant_message="listo",
        model="MiniMax-M3",
        workroom_dir=tmp_path,
    )
    short = tmp_path / "founder" / f"{chat_id[:8]}.json"
    full = tmp_path / "founder" / f"{chat_id}.json"
    assert not short.exists()
    saved = json.loads(full.read_text(encoding="utf-8"))
    assert saved["id"] == chat_id
    assert saved["timezone"] == "America/New_York"
    assert saved["updated_at"].endswith("-04:00") or saved["updated_at"].endswith("-05:00")
    assert "T" in saved["created_at"]


def test_family_users_cannot_see_each_others_chats(monkeypatch, tmp_path):
    _family_env(monkeypatch, tmp_path, "maxine")
    from app.services.amp_allowlist import add_entry

    add_entry(email="juan@example.com", role="member")
    add_entry(email="lina@example.com", role="member")
    client = _client(tmp_path)

    _cookie(client, "juan@example.com")
    full_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    saved = client.put(
        f"/api/v1/chats/{full_id}",
        json={"messages": [{"role": "user", "content": "secreto de juan"}]},
    )
    assert saved.status_code == 200
    listed = client.get("/api/v1/chats/list")
    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert listed.json()["chats"][0]["id"] == full_id

    spoof = client.get("/api/v1/chats/list?user_id=lina_at_example.com")
    assert spoof.status_code == 200
    assert spoof.json()["count"] == 1
    assert "secreto de juan" in json.dumps(client.get(f"/api/v1/chats/{full_id}").json())

    _cookie(client, "lina@example.com")
    other = client.get("/api/v1/chats/list?user_id=juan_at_example.com")
    assert other.status_code == 200
    assert other.json()["count"] == 0
    assert client.get(f"/api/v1/chats/{full_id}").status_code == 404

    founder_dir = tmp_path / "chats" / "founder"
    assert not founder_dir.exists() or not any(founder_dir.glob("*.json"))
    juan_dir = tmp_path / "chats" / "juan_at_example.com"
    assert (juan_dir / f"{full_id}.json").is_file()
    assert not (juan_dir / f"{full_id[:8]}.json").exists()


def test_family_save_rejects_claimed_founder_bucket(monkeypatch, tmp_path):
    _family_env(monkeypatch, tmp_path)
    client = _client(tmp_path)
    _cookie(client, "owner@example.com")
    res = client.post(
        "/api/v1/chats/save",
        json={
            "user_id": "founder",
            "id": "11111111-2222-3333-4444-555555555555",
            "messages": [{"role": "user", "content": "mio"}],
        },
    )
    assert res.status_code == 200
    assert res.json()["chat_id"] == "11111111-2222-3333-4444-555555555555"
    assert not (tmp_path / "chats" / "founder").exists() or not any(
        (tmp_path / "chats" / "founder").glob("*.json")
    )
    owner_files = list((tmp_path / "chats" / "owner_at_example.com").glob("*.json"))
    assert len(owner_files) == 1
    assert owner_files[0].stem == "11111111-2222-3333-4444-555555555555"


def test_router_no_longer_writes_eight_char_founder_copies():
    router = (ROOT / "backend" / "app" / "routers" / "max" / "router.py").read_text(encoding="utf-8")
    assert 'conv_id[:8]' not in router
    assert '_chat_id_short' not in router
    assert '_ROUTER_CHATS_DIR / "founder"' not in router
    assert router.count("persist_exchange") >= 2


def test_chat_screen_historial_and_family_skip_inbox_calls():
    screen = (
        ROOT / "empire-command-center" / "app" / "components" / "screens" / "ChatScreen.tsx"
    ).read_text(encoding="utf-8")
    panel = (
        ROOT / "empire-command-center" / "app" / "components" / "ChatHistoryPanel.tsx"
    ).read_text(encoding="utf-8")
    recents = (
        ROOT / "empire-command-center" / "app" / "components" / "RecentChatsList.tsx"
    ).read_text(encoding="utf-8")
    es = (
        ROOT / "empire-command-center" / "app" / "lib" / "i18n" / "locales" / "es" / "common.json"
    ).read_text(encoding="utf-8")

    assert 'data-testid="chat-historial-button"' in screen
    assert "max.historial" in screen
    assert "RecentChatsList" in screen
    assert "isEmptyConversation" in screen
    assert "isFamilyEdition" in panel
    assert "fetchTelegramChats" in panel
    assert "if (family)" in panel
    assert "fetchTelegramChats();" in panel
    # Family branch returns after web chats; those inbox URLs stay for Workroom only.
    family_block = panel.split("if (family)")[1].split("fetchAllChannels")[0]
    assert "/max/telegram/history" not in family_block
    assert "/max/gmail/inbox" not in family_block
    assert "credentials: 'include'" in panel
    assert 'data-testid="chat-recent-list"' in recents
    assert '"historial": "Historial"' in es


def test_cleanup_script_is_dry_run_and_uses_temp_dir(tmp_path):
    user = tmp_path / "juan_at_example.com"
    user.mkdir()
    short_id = "30ea0046"
    full_id = "30ea0046-2bc9-461c-8215-5793e12874cd"
    (user / f"{short_id}.json").write_text(json.dumps({"id": short_id, "messages": []}), encoding="utf-8")
    (user / f"{full_id}.json").write_text(json.dumps({"id": full_id, "messages": []}), encoding="utf-8")
    script = ROOT / "backend" / "scripts" / "chat_history_cleanup.py"
    result = subprocess.run(
        [sys.executable, str(script), "--dir", str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    assert report["dry_run"] is True
    assert report["would_delete"] is False
    assert report["items"][0]["short_id"] == short_id
    assert full_id in report["items"][0]["full_ids"]
    assert (user / f"{short_id}.json").is_file()
    refused = subprocess.run(
        [sys.executable, str(script), "--dir", "/data/amp/chats"],
        capture_output=True,
        text=True,
    )
    assert refused.returncode == 2
    assert "live /data" in refused.stderr


def test_tests_never_point_at_live_data_root():
    here = Path(__file__).read_text(encoding="utf-8")
    store = (ROOT / "backend" / "app" / "services" / "chat_history_store.py").read_text(encoding="utf-8")
    assert "/data/amp" not in here.split("refused")[0] or "tmp_path" in here
    assert "EMPIRE_DATA_DIR" in here
    assert "tmp_path" in here
    assert 'require_data_root() / "chats"' in store
