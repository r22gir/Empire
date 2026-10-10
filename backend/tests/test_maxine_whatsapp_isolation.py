"""Maxine-only WhatsApp isolation. Mocks only. No GAC legal details."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from app.edition import MAXINE_OWNER_NAME


GAC_LEGAL_BANNED = (
    "NIT",
    "shareholder",
    "accionista",
    "escritura",
    "capital social",
    "abogado",
    "registro mercantil",
)


def _maxine(monkeypatch, tmp_path):
    root = tmp_path / "maxine"
    root.mkdir()
    assert "/data/maxine" not in str(root.resolve())
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(root))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Maxine")
    monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")
    monkeypatch.setenv("WHATSAPP_OWNER_NUMBERS", "3009998888")
    from app.edition import apply_amp_process_paths

    apply_amp_process_paths()
    return root


def test_maxine_edition_paths_and_cap(monkeypatch, tmp_path):
    from app.edition import (
        edition_name,
        edition_profile,
        is_founder_edition,
        is_maxine,
        module_enabled,
    )
    from app.services.instance_usage import cap_percent
    from app.services.whatsapp_cloud import channel_status, owner_numbers
    from app.services.whatsapp_store import jobs_root, whatsapp_data_dir

    root = _maxine(monkeypatch, tmp_path)
    assert is_maxine() is True
    assert is_founder_edition() is False
    assert edition_name() == "maxine"
    profile = edition_profile()
    assert profile["backend_port"] == 8012
    assert profile["host"] == "maxine.empirebox.store"
    assert cap_percent() == 20.0
    assert module_enabled("drawings") is False
    assert owner_numbers() == ["3009998888"]
    status = channel_status()
    assert status["edition"] == "maxine"
    assert status["webhook_url"].endswith("/api/v1/whatsapp/webhook")
    assert "maxine.empirebox.store" in status["webhook_url"]
    assert "amp.empirebox.store" not in status["webhook_url"]
    assert status["documents_auto_send"] is False
    assert status["secret_file"] == "/home/rg/empire-maxine.env"
    assert whatsapp_data_dir().resolve().is_relative_to(root.resolve())
    assert jobs_root().resolve() == (root / "jobs").resolve()


def test_maxine_fail_closed_on_data_dir_basename(monkeypatch, tmp_path):
    from app.edition import edition_name, is_family_edition, is_founder_edition, is_maxine

    root = tmp_path / "maxine"
    root.mkdir()
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(root))
    assert is_maxine() is True
    assert is_family_edition() is True
    assert is_founder_edition() is False
    assert edition_name() == "maxine"


def test_maxine_cannot_see_workroom_inbox_chats_quotes_or_jobs(monkeypatch, tmp_path):
    from app.api.v1 import chats as chats_mod
    from app.edition import family_file_search_roots, module_enabled
    from app.routers import inbox as inbox_mod
    from app.services.data_paths import quotes_data_dir
    from app.services.max.doc_lookup import find_docs, _hub_base
    from app.services.max.system_prompt import get_system_prompt, _prompt_cache
    from app.services.whatsapp_store import jobs_root

    root = _maxine(monkeypatch, tmp_path)
    workroom_inbox = Path.home() / "empire-repo" / "backend" / "data" / "inbox"
    workroom_chats = Path(__file__).resolve().parents[1] / "data" / "chats"
    inbox = Path(inbox_mod._inbox_dir()).resolve()
    chats = chats_mod._chats_dir().resolve()
    quotes = quotes_data_dir().resolve()
    jobs = jobs_root().resolve()
    assert inbox == (root / "inbox").resolve()
    assert chats == (root / "chats").resolve()
    assert quotes == (root / "quotes").resolve()
    assert jobs == (root / "jobs").resolve()
    assert inbox != workroom_inbox.resolve()
    assert chats != workroom_chats.resolve()
    assert list(inbox.glob("*.json")) == []
    assert list(chats.glob("**/*.json")) == []
    assert _hub_base() is None
    assert find_docs("dahlia")["docs"] == []
    for path in family_file_search_roots():
        assert path.resolve().is_relative_to(root.resolve())
        assert "empire-repo" not in str(path)
    assert module_enabled("drawings") is False
    _prompt_cache.update({"prompt": None, "expires": 0, "edition": None})
    prompt = get_system_prompt()
    for leak in (
        "5124 Frolich",
        "Nelma's Workroom",
        "Nehal Elrefai",
        "The Willard Hotel",
        "Empire Workroom",
    ):
        assert leak not in prompt


def test_maxine_env_example_has_no_owner_number_or_token():
    text = Path(__file__).resolve().parents[2].joinpath(
        "deploy", "empire-maxine.env.example"
    ).read_text(encoding="utf-8")
    assert "WHATSAPP_OWNER_NUMBERS=" in text
    assert "3122842350" not in text
    assert "3174437313" not in text
    assert "EAA" not in text
    assert "INSTANCE_USAGE_CAP_PCT=20" in text


def test_maxine_does_not_see_workroom_or_amp_aliases(monkeypatch, tmp_path):
    from app.services.max.doc_lookup import load_client_aliases, resolve_job_folder
    from app.edition import workroom_business_config

    root = _maxine(monkeypatch, tmp_path)
    repo = tmp_path / "rafael.json"
    repo.write_text(
        json.dumps({"clients": [{"slug": "nehal-elrefai", "name": "Nehal Elrefai", "aliases": ["dahlia"]}]}),
        encoding="utf-8",
    )
    monkeypatch.setenv("MAX_CLIENT_ALIASES_REPO_PATH", str(repo))
    (root / "client_aliases.json").write_text(json.dumps({"clients": []}), encoding="utf-8")
    aliases = load_client_aliases()
    slugs = {c.get("slug") for c in (aliases.get("clients") or [])}
    assert "nehal-elrefai" not in slugs
    assert resolve_job_folder("dahlia") is None
    assert workroom_business_config() == {}


def test_maxine_spanish_guide_is_camilo_construction_not_gac_legal():
    root = Path(__file__).resolve().parents[2]
    script = """
import { renderWhatsAppSetupPage } from './empire-command-center/app/lib/whatsappSetup.mjs';
process.stdout.write(renderWhatsAppSetupPage('maxine'));
"""
    html = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "Maxine" in html
    assert MAXINE_OWNER_NAME.split()[0] in html
    assert "construcción" in html
    assert "inmuebles" in html
    assert "maxine.empirebox.store/api/v1/whatsapp/webhook" in html
    assert "/home/rg/empire-maxine.env" in html
    assert "no la de Rafael" in html
    assert "solicitud segura" in html
    assert "Max-e" not in html
    assert "amp.empirebox.store" not in html
    assert "Juan Diego" not in html
    assert "3174437313" not in html
    assert "3122842350" not in html
    for banned in GAC_LEGAL_BANNED:
        assert banned not in html
    assert "Grupo Argos Campestre" not in html
