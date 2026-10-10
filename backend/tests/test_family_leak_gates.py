"""Chief-e leak gates: family prompt, tool list, and WhatsApp paths.

Mocks only. Never writes /data/amp or /data/maxine. Covers amp and maxine.
"""
from __future__ import annotations

import json
from pathlib import Path

WORKROOM_LEAKS = (
    "5124 Frolich",
    "Hyattsville",
    "Nelma's Workroom",
    "Nelma's",
    "Dahlia = Nehal Elrefai",
    "Nehal Elrefai",
    "The Willard Hotel",
    "bill the Willard",
    "McLean Whittington",
    "9408 old courthouse",
    "Empire Workroom",
)


def _family(monkeypatch, tmp_path, edition: str):
    root = tmp_path / edition
    root.mkdir()
    assert "/data/amp" not in str(root.resolve())
    assert "/data/maxine" not in str(root.resolve())
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(root))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Maxine" if edition == "maxine" else "Max-e")
    monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")
    from app.edition import apply_amp_process_paths
    from app.services.max.system_prompt import _prompt_cache

    apply_amp_process_paths()
    _prompt_cache.update({"prompt": None, "expires": 0, "edition": None})
    return root


def _blob_has_leak(blob: str) -> list[str]:
    return [leak for leak in WORKROOM_LEAKS if leak in blob]


def test_family_prompt_tools_and_whatsapp_paths_have_no_workroom_leaks(monkeypatch, tmp_path):
    from app.edition import (
        family_default_drawing_fixtures,
        family_file_search_roots,
        is_founder_edition,
        module_enabled,
        workroom_business_config,
        workroom_woodcraft_config,
    )
    from app.services.max.desk_prompt import get_desk_system_prompt
    from app.services.max.system_prompt import get_system_prompt
    from app.services.max.tool_executor import tools_doc_for_process
    from app.services.max.doc_lookup import default_hub_get, final_docs_all, find_docs, _hub_base
    from app.services.whatsapp_cloud import channel_status, _state_path
    from app.services.whatsapp_store import jobs_root, labels_path, whatsapp_data_dir
    from app.services.voice_documents.edition import forbidden_client_names

    for edition in ("amp", "maxine"):
        root = _family(monkeypatch, tmp_path, edition)
        assert is_founder_edition() is False
        assert workroom_business_config() == {}
        assert workroom_woodcraft_config() == {}
        assert family_default_drawing_fixtures() == ()
        assert module_enabled("drawings") is False

        prompt = get_system_prompt()
        tools = tools_doc_for_process()
        desk = get_desk_system_prompt("forge")
        status = json.dumps(channel_status(), ensure_ascii=False)
        paths = "\n".join(
            str(p)
            for p in (
                _state_path(),
                whatsapp_data_dir(),
                jobs_root(),
                labels_path(),
                *family_file_search_roots(),
            )
        )
        blob = "\n".join([prompt, tools, desk, status, paths])
        found = _blob_has_leak(blob)
        assert found == [], f"{edition} leaked {found}"
        assert "bill the Willard" not in tools
        assert "Dahlia" not in tools
        assert Path(_state_path()).resolve().is_relative_to(root.resolve())
        for path in family_file_search_roots():
            assert path.resolve().is_relative_to(root.resolve())
            assert "empire-repo" not in str(path)
        assert _hub_base() is None
        assert find_docs()["docs"] == []
        assert default_hub_get("/")["docs"] == []
        assert final_docs_all() == []
        names = forbidden_client_names()
        assert "rafael giraldo" not in " ".join(names).lower()
        assert channel_status()["documents_auto_send"] is False
        assert str(channel_status()["usage_cap_pct"]) == "20"


def test_family_whatsapp_modules_do_not_read_repo_business_json():
    root = Path(__file__).resolve().parents[1]
    for rel in (
        "app/services/whatsapp_cloud.py",
        "app/services/whatsapp_store.py",
        "app/services/max/doc_lookup.py",
        "app/routers/whatsapp.py",
    ):
        text = (root / rel).read_text(encoding="utf-8")
        assert "config/business.json" not in text
        assert "woodcraft_business.json" not in text
        for leak in WORKROOM_LEAKS:
            if leak == "Empire Workroom":
                continue
            assert leak not in text
    assert not (root / "app/services/max/whatsapp_channel.py").exists()
    assert not (root / "app/services/max/whatsapp_log.py").exists()
    assert not (root / "app/services/max/tools_files.py").exists()


def test_family_skips_social_frolich_seed(monkeypatch, tmp_path):
    _family(monkeypatch, tmp_path, "amp")
    from app.routers import social_setup

    # Re-run init under family env: Workroom rows must not be inserted.
    social_setup._init_tables()
    from app.db.database import get_db

    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT address, business_name FROM business_profiles"
            ).fetchall()
    except Exception:
        rows = []
    blob = " ".join(str(r) for r in rows)
    assert "5124 Frolich" not in blob
    assert "Empire Workroom" not in blob


def test_fail_closed_unknown_edition_in_family_data_dir(monkeypatch, tmp_path):
    from app.edition import is_family_edition, is_founder_edition, edition_name

    amp = tmp_path / "amp"
    amp.mkdir()
    monkeypatch.setenv("EMPIRE_EDITION", "staging")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(amp))
    assert is_family_edition() is True
    assert is_founder_edition() is False
    assert edition_name() == "amp"
