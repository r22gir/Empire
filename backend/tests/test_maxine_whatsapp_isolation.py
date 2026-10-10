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
