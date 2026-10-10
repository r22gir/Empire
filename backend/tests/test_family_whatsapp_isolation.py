"""Family WhatsApp + leak gates. Mocks only. Never writes /data/amp or /data/maxine."""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


LIVE_FAMILY_ROOTS = (Path("/data/amp"), Path("/data/maxine"))
WORKROOM_LEAKS = (
    "5124 Frolich",
    "Hyattsville",
    "Nelma's Workroom",
    "Nehal Elrefai",
    "Dahlia = Nehal",
    "The Willard Hotel",
    "McLean Whittington",
    "9408 old courthouse",
)


def _assert_not_live(path: Path) -> None:
    resolved = path.expanduser().resolve()
    for banned in LIVE_FAMILY_ROOTS:
        if resolved == banned or banned in resolved.parents:
            raise AssertionError(f"refusing live family data dir {resolved}")


def _family_env(monkeypatch, tmp_path, edition: str = "amp"):
    _assert_not_live(tmp_path)
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Maxine" if edition == "maxine" else "Max-e")
    monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")
    monkeypatch.delenv("WHATSAPP_OWNER_NUMBERS", raising=False)
    monkeypatch.delenv("WHATSAPP_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("WHATSAPP_FOUNDER_PHONES", raising=False)
    from app.edition import apply_amp_process_paths

    apply_amp_process_paths()


def test_fail_closed_family_data_dir_without_edition_env(monkeypatch, tmp_path):
    from app.edition import is_family_edition, is_founder_edition, edition_name

    amp_root = tmp_path / "amp"
    amp_root.mkdir()
    _assert_not_live(amp_root)
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(amp_root))
    assert is_family_edition() is True
    assert is_founder_edition() is False
    assert edition_name() == "amp"

    maxine_root = tmp_path / "maxine"
    maxine_root.mkdir()
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(maxine_root))
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    assert is_family_edition() is True
    assert edition_name() == "maxine"
    assert is_founder_edition() is False


def test_family_whatsapp_state_stays_under_data_dir(monkeypatch, tmp_path):
    from app.services.whatsapp_cloud import _state_path
    from app.services.whatsapp_store import chat_log_path, jobs_root, media_dir

    for edition in ("amp", "maxine"):
        root = tmp_path / edition
        root.mkdir()
        _family_env(monkeypatch, root, edition)
        state = Path(_state_path()).resolve()
        assert state == (root / "whatsapp.db").resolve()
        assert "empire-data" not in str(state)
        log = chat_log_path().resolve()
        assert log.is_relative_to(root.resolve())
        assert media_dir().resolve().is_relative_to(root.resolve())
        assert jobs_root().resolve() == (root / "jobs").resolve()


def test_family_inbox_and_chats_not_workroom_checkout(monkeypatch, tmp_path):
    from app.api.v1 import chats as chats_mod
    from app.routers import inbox as inbox_mod

    workroom_inbox = Path.home() / "empire-repo" / "backend" / "data" / "inbox"
    workroom_chats = Path(__file__).resolve().parents[1] / "data" / "chats"
    for edition in ("amp", "maxine"):
        root = tmp_path / edition
        root.mkdir()
        _family_env(monkeypatch, root, edition)
        inbox = Path(inbox_mod._inbox_dir()).resolve()
        chats = chats_mod._chats_dir().resolve()
        assert inbox == (root / "inbox").resolve()
        assert chats == (root / "chats").resolve()
        assert inbox != workroom_inbox.resolve()
        assert chats != workroom_chats.resolve()


def test_family_owner_numbers_come_only_from_env(monkeypatch, tmp_path):
    from app.services.whatsapp_cloud import owner_numbers

    _family_env(monkeypatch, tmp_path, "amp")
    monkeypatch.setenv("WHATSAPP_OWNER_NUMBERS", "3001112233")
    assert owner_numbers() == ["3001112233"]
    assert "3122842350" not in owner_numbers()
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    monkeypatch.setenv("WHATSAPP_OWNER_NUMBERS", "3009998888")
    assert owner_numbers() == ["3009998888"]
    assert "3001112233" not in owner_numbers()


def test_family_ignores_repo_business_json_and_aliases(monkeypatch, tmp_path):
    from app.config.workroom_billing import resolve_billing
    from app.edition import workroom_business_config, workroom_woodcraft_config
    from app.services.max.doc_lookup import (
        find_docs,
        is_founder_edition,
        load_client_aliases,
        resolve_job_folder,
        _hub_base,
    )

    repo = tmp_path / "rafael-aliases.json"
    repo.write_text(
        json.dumps({
            "clients": [
                {"slug": "nehal-elrefai", "name": "Nehal Elrefai", "aliases": ["dahlia"]},
                {"slug": "emma-vita", "name": "Emma Vita"},
            ]
        }),
        encoding="utf-8",
    )
    monkeypatch.setenv("MAX_CLIENT_ALIASES_REPO_PATH", str(repo))
    for edition in ("amp", "maxine"):
        root = tmp_path / edition
        root.mkdir()
        _family_env(monkeypatch, root, edition)
        assert is_founder_edition() is False
        assert workroom_business_config() == {}
        assert workroom_woodcraft_config() == {}
        billing = resolve_billing()
        blob = json.dumps(billing.__dict__)
        for leak in ("5124 Frolich", "Hyattsville", "Empire Workroom", "Nelma"):
            assert leak not in blob
        aliases = load_client_aliases()
        slugs = {c.get("slug") for c in (aliases.get("clients") or [])}
        assert "nehal-elrefai" not in slugs
        assert "emma-vita" not in slugs
        assert resolve_job_folder("dahlia") is None
        assert resolve_job_folder("new job dahlia") is None
        assert _hub_base() is None
        docs = find_docs("anything")
        assert docs.get("docs") == []
        assert "disabled" in (docs.get("reason") or "")


def test_family_file_roots_and_drawings_disabled(monkeypatch, tmp_path):
    from app.edition import family_file_search_roots, module_enabled
    from app.services.instance_usage import cap_percent

    for edition in ("amp", "maxine"):
        root = tmp_path / edition
        root.mkdir()
        _family_env(monkeypatch, root, edition)
        roots = [p.resolve() for p in family_file_search_roots()]
        assert roots
        for path in roots:
            assert path.is_relative_to(root.resolve())
            assert "empire-repo" not in str(path)
        assert module_enabled("drawings") is False
        assert module_enabled("craftforge") is False
        assert module_enabled("luxeforge") is False
        assert cap_percent() == 20.0


def test_family_prompt_and_tools_have_no_workroom_names(monkeypatch, tmp_path):
    from app.services.max.system_prompt import get_system_prompt
    from app.services.whatsapp_cloud import channel_status
    from app.services.whatsapp_store import jobs_root, whatsapp_data_dir

    for edition in ("amp", "maxine"):
        root = tmp_path / edition
        root.mkdir()
        _family_env(monkeypatch, root, edition)
        from app.services.max.system_prompt import _prompt_cache

        _prompt_cache.update({"prompt": None, "expires": 0, "edition": None})
        prompt = get_system_prompt()
        status = json.dumps(channel_status())
        paths = f"{whatsapp_data_dir()} {jobs_root()}"
        blob = "\n".join([prompt, status, paths])
        for leak in WORKROOM_LEAKS:
            assert leak not in blob
        assert "documents_auto_send" in status
        assert json.loads(status)["documents_auto_send"] is False
        assert json.loads(status)["client_sends"] is False
        assert "/api/v1/whatsapp/webhook" in json.loads(status)["webhook_url"]


def test_amp_cannot_see_workroom_quotes_jobs_chats(monkeypatch, tmp_path):
    """EMPIRE_EDITION=amp must not list Rafael's checkout inbox/chats/quotes."""
    from app.api.v1 import chats as chats_mod
    from app.routers import inbox as inbox_mod
    from app.services.data_paths import quotes_data_dir

    root = tmp_path / "amp"
    root.mkdir()
    _family_env(monkeypatch, root, "amp")
    rafael_inbox = tmp_path / "rafael-inbox"
    rafael_inbox.mkdir()
    (rafael_inbox / "secret.json").write_text(
        json.dumps({"id": "r1", "text": "Dahlia quote EST-2026-300", "created_at": "2026-01-01"}),
        encoding="utf-8",
    )
    family_inbox = Path(inbox_mod._inbox_dir())
    assert family_inbox == root / "inbox"
    assert not (family_inbox / "secret.json").exists()
    listed = list(family_inbox.glob("*.json")) if family_inbox.exists() else []
    assert listed == []

    family_chats = chats_mod._chats_dir()
    assert family_chats == root / "chats"
    assert list(family_chats.glob("**/*.json")) == []

    quotes = quotes_data_dir()
    assert quotes == root / "quotes"
    assert list(quotes.glob("*")) == []


def test_whatsapp_chats_api_is_readonly(monkeypatch, tmp_path):
    from app.routers.whatsapp import router
    from app.services.whatsapp_store import record_message

    _family_env(monkeypatch, tmp_path, "amp")
    record_message("573001112233", direction="in", kind="text", body="hola desde la casa")
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)
    listed = client.get("/api/v1/whatsapp/chats")
    assert listed.status_code == 200
    body = listed.json()
    assert body["readonly"] is True
    assert body["draft_only"] is True
    assert body["conversations"][0]["last4"] == "2233"
    thread = client.get("/api/v1/whatsapp/chats/573001112233/messages")
    assert thread.status_code == 200
    assert thread.json()["messages"][0]["body"] == "hola desde la casa"
    search = client.get("/api/v1/whatsapp/chats/search", params={"q": "casa"})
    assert search.json()["matches"]
    setup = client.get("/api/v1/whatsapp/setup")
    assert setup.json()["secrets_in_page"] is False
    assert setup.json()["documents_auto_send"] is False
    dumped = json.dumps(setup.json())
    assert "test-token" not in dumped
    assert "EAA" not in dumped


def test_no_client_send_flag(monkeypatch, tmp_path):
    from app.services.whatsapp_cloud import channel_status

    _family_env(monkeypatch, tmp_path, "amp")
    status = channel_status()
    assert status["documents_auto_send"] is False
    assert status["draft_only"] is True
    assert status["client_sends"] is False
    assert str(status["usage_cap_pct"]) == "20"


def test_ayuda_whatsapp_has_no_secrets_or_hardcoded_numbers():
    script = """
import { renderWhatsAppSetupPage } from './empire-command-center/app/lib/whatsappSetup.mjs';
process.stdout.write(renderWhatsAppSetupPage(process.env.EDITION || 'amp'));
"""
    import subprocess

    root = Path(__file__).resolve().parents[2]
    for edition, host, other in (
        ("amp", "amp.empirebox.store", "maxine.empirebox.store"),
        ("maxine", "maxine.empirebox.store", "amp.empirebox.store"),
    ):
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "EDITION": edition},
        )
        html = result.stdout
        assert "no la de Rafael" in html
        assert "solicitud segura" in html
        assert host in html
        assert other not in html
        assert "WHATSAPP_ACCESS_TOKEN=" not in html
        assert "3174437313" not in html
        assert "3122842350" not in html
        assert "EAA" not in html
        assert "Grupo Argos Campestre" not in html
        assert "20%" in html
        assert "número de prueba" in html.lower() or "prueba de Meta" in html
        if edition == "maxine":
            assert "construcción" in html
            assert "Max-e" not in html
            assert "Camilo" in html
        else:
            assert "Maxine" not in html
            assert "Juan Diego" in html
