"""Rafael's file finder: all matches ranked, aliases, exclusions, read-only share. Uses temp copies only."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from app.services.max import file_finder as ff


def _touch(p: Path, data: bytes = b"%PDF-1.4 test", age_days: float = 0.0) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    if age_days:
        t = time.time() - age_days * 86400
        os.utime(p, (t, t))
    return p


@pytest.fixture()
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    jobs = h / "jobs" / "nehal-elrefai"
    _touch(jobs / "EST-2026-297-phase1-v26-FINAL-nobump.pdf", age_days=1)
    _touch(jobs / "EST-2026-298-phase2-v8-FINAL-nobump.pdf", age_days=1)
    _touch(jobs / "EST-2026-297-phase1-v12.pdf", age_days=9)
    _touch(jobs / "SCOPE-AND-COST-COMPARISON-Nehal.pdf", age_days=2)
    # ~/Downloads is a symlink elsewhere on the real Dell
    dl_real = tmp_path / "data" / "empire" / "Downloads"
    _touch(dl_real / "Kitchen-Remodel-Invoice-Thompson-0912.pdf")
    (h / "Downloads").symlink_to(dl_real)
    # must never be found
    _touch(h / "empire-repo-main" / "backend" / ".env", b"SECRET=1")
    _touch(h / "empire-data" / "nehal-api-token.txt", b"x")
    _touch(h / "empire-data" / "empire.db", b"x")
    _touch(h / ".ssh" / "id_rsa", b"x")
    _touch(h / "credentials" / "nehal-estimate.pdf", b"x")
    fam = tmp_path / "data" / "amp"
    _touch(fam / "Nehal-final-estimate-family.pdf")
    (h / "famlink").symlink_to(fam)
    _touch(h / "empire-maxine" / "nehal-estimate.pdf")
    _touch(h / "backups" / "pdf-fix-empire-amp-1" / "Nehal-estimate-amp.pdf")
    aliases = tmp_path / "aliases.json"
    aliases.write_text(json.dumps({"clients": [
        {"name": "Nehal Elrefai", "aliases": ["Dahlia", "Dhalia", "Dalia", "Nehal"], "address": "9408 Old Courthouse Rd"}]}))
    monkeypatch.setenv("MAX_CLIENT_ALIASES_PATH", str(aliases))
    monkeypatch.setenv("MAX_FILE_FINDER_ROOTS", str(h))
    monkeypatch.setattr(ff, "_excluded_realpaths",
                        lambda: (str(fam), str(h / "empire-maxine"), str(h / ".ssh")))
    ff.INDEX.clear()
    yield h
    ff.INDEX.clear()


def _names(res):
    return [m["name"] for m in res["matches"]]


def test_nehal_final_estimate_returns_both_finals_first(home):
    res = ff.find_files("Nehal final estimate")
    names = _names(res)
    assert res["found"] and res["parsed"]["client"] == "Nehal Elrefai"
    assert set(names[:2]) == {"EST-2026-297-phase1-v26-FINAL-nobump.pdf", "EST-2026-298-phase2-v8-FINAL-nobump.pdf"}
    assert "EST-2026-297-phase1-v12.pdf" in names  # older versions still listed, lower


def test_dahlia_resolves_to_nehal(home):
    res = ff.find_files("Dahlia docs")
    assert res["parsed"]["client"] == "Nehal Elrefai" and res["parsed"]["client_via"].startswith("alias:")
    assert len(res["matches"]) >= 4


def test_random_download_found_through_symlink(home):
    res = ff.find_files("thompson kitchen invoice")
    assert _names(res)[0] == "Kitchen-Remodel-Invoice-Thompson-0912.pdf"
    assert res["matches"][0]["path"].endswith("Downloads/Kitchen-Remodel-Invoice-Thompson-0912.pdf")


@pytest.mark.parametrize("query", [".env", "env", "secret", "token", "id_rsa", "empire db", "Nehal family",
                                   "credentials", "amp", "maxine"])
def test_protected_and_family_never_found(home, query):
    res = ff.find_files(query)
    for m in res["matches"] + res.get("closest", []):
        p = m["path"].lower()
        assert ".env" not in p and "token" not in p and ".db" not in p and ".ssh" not in p
        name = p.rsplit("/", 1)[-1]
        assert "family" not in name and "amp" not in name and "maxine" not in p
        assert "credentials" not in p


def test_family_and_protected_paths_not_shareable(home, tmp_path):
    for p in (tmp_path / "data/amp/Nehal-final-estimate-family.pdf", home / "famlink/Nehal-final-estimate-family.pdf",
              home / "empire-repo-main/backend/.env", home / ".ssh/id_rsa", home / "empire-data/empire.db",
              home / "empire-maxine/nehal-estimate.pdf"):
        assert ff.resolve_file(str(p)) is None
    assert ff.resolve_file(str(home / "jobs/nehal-elrefai/SCOPE-AND-COST-COMPARISON-Nehal.pdf"))


def test_real_exclusion_rules():
    for p in ("/data/amp/x.pdf", "/data/maxine/x.pdf", os.path.expanduser("~/empire-amp/a.pdf"),
              os.path.expanduser("~/empire-maxine/a.pdf"), os.path.expanduser("~/.config/empirebox/gmail/token.json"),
              os.path.expanduser("~/.hermes/x.pdf"), os.path.expanduser("~/empire-repo-main/backend/.env"),
              "/x/client_secret_123.json", "/x/empire.db", "/x/amp.db"):
        assert ff.is_excluded(p), p
    assert not ff.is_excluded(os.path.expanduser("~/jobs/nehal-elrefai/EST-2026-298.pdf"))


def test_nothing_matches_gives_closest(home):
    res = ff.find_files("nehall scopee comparisn zzq")
    assert not res["found"]
    assert any("SCOPE" in c["name"] for c in res["closest"])


def test_quote_number_lookup(home):
    res = ff.find_files("EST-2026-298")
    assert _names(res) == ["EST-2026-298-phase2-v8-FINAL-nobump.pdf"]


# ── tools ─────────────────────────────────────────────────────────
def test_find_files_tool_and_studio_share_link(home):
    from app.services.max.tool_executor import TOOL_REGISTRY, execute_tool
    assert "find_files" in TOOL_REGISTRY and "share_file" in TOOL_REGISTRY
    r = execute_tool({"tool": "find_files", "query": "Nehal final estimate"}).to_dict()
    assert r["success"] and r["result"]["total"] >= 2
    fid = r["result"]["matches"][0]["file_id"]
    s = execute_tool({"tool": "share_file", "file_id": fid, "via": "studio"}).to_dict()
    assert s["success"] and s["result"]["viewer_url"].startswith("/api/v1/files/found?t=")
    token = s["result"]["viewer_url"].split("t=", 1)[1]
    real = ff.verify_share_token(token)
    assert real and real.endswith(".pdf")
    assert ff.verify_share_token(token[:-2] + "00") is None  # tampered


def test_found_route_serves_file_and_blocks_bad_tokens(home):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.api.v1.files as files_mod
    app = FastAPI(); app.include_router(files_mod.router, prefix="/api/v1")
    files_mod.log_access = lambda *a, **k: None
    c = TestClient(app)
    path = str(home / "jobs/nehal-elrefai/EST-2026-298-phase2-v8-FINAL-nobump.pdf")
    ok = c.get("/api/v1/files/found", params={"t": ff.share_token(path)})
    assert ok.status_code == 200 and ok.content.startswith(b"%PDF")
    assert c.get("/api/v1/files/found", params={"t": "garbage.sig"}).status_code == 404
    env = str(home / "empire-repo-main/backend/.env")
    assert c.get("/api/v1/files/found", params={"t": ff.share_token(env)}).status_code == 404


def test_share_email_self_only_and_uses_temp_copy(home, monkeypatch):
    import app.services.max.tool_executor as te
    sent = []

    class R:
        def __init__(self, d): self.d = d
        def to_dict(self): return self.d

    def fake(call, **kw):
        sent.append(call)
        assert os.path.exists(call["attachments"][0]) and "max-share-" in call["attachments"][0]
        return R({"success": True, "result": {"sent_to": call["to"], "message_id": "<t>", "attachments_sent": 1}})

    monkeypatch.setattr(te, "execute_tool", fake)
    from app.services.max import tools_files as tf
    path = str(home / "jobs/nehal-elrefai/SCOPE-AND-COST-COMPARISON-Nehal.pdf")
    ok = tf._share_file({"path": path, "via": "email"})
    assert ok.success and sent[0]["to"] == "empirebox2026@gmail.com"
    assert not os.path.exists(sent[0]["attachments"][0])  # temp copy cleaned up
    assert os.path.exists(path)  # original untouched
    bad = tf._share_file({"path": path, "via": "email", "to": "client@example.com"})
    assert not bad.success and "explicit yes" in bad.error and len(sent) == 1


def test_share_whatsapp_to_founder_only(home, monkeypatch):
    from app.services.max import tools_files as tf
    import app.services.max.whatsapp_channel as wa
    calls = {}
    monkeypatch.setattr(tf, "_founder_whatsapp", lambda: "15555550100")
    monkeypatch.setattr(wa, "_require_enabled", lambda: None)
    monkeypatch.setattr(wa, "is_allowlisted", lambda n: n == "15555550100")
    monkeypatch.setattr(wa, "customer_window_open", lambda n: True)

    async def up(data, mime, name, **kw):
        calls["upload"] = (len(data), mime, name); return "MEDIA1"

    async def post(body, **kw):
        calls["post"] = body; return {"messages": [{"id": "m"}]}

    monkeypatch.setattr(wa, "upload_media", up)
    monkeypatch.setattr(wa, "_post_graph", post)
    path = str(home / "Downloads/Kitchen-Remodel-Invoice-Thompson-0912.pdf")
    r = tf._share_file({"path": path, "via": "whatsapp"})
    assert r.success and calls["upload"][1] == "application/pdf"
    assert calls["post"]["to"] == "15555550100" and calls["post"]["type"] == "document"


def test_expand_finals_lists_both_nehal_phases():
    from app.services.max.final_docs_all import expand_finals
    docs = [
        {"id": "a", "type": "estimate", "title": "Estimate EST-2026-297", "filename": "EST-2026-297-phase1-v26-FINAL-nobump.pdf", "modified": "2026-10-05T17:00", "isFinal": True, "quoteNumber": "EST-2026-297"},
        {"id": "b", "type": "estimate", "title": "Estimate EST-2026-298", "filename": "EST-2026-298-phase2-v8-FINAL-nobump.pdf", "modified": "2026-10-05T16:00", "isFinal": True, "quoteNumber": "EST-2026-298"},
        {"id": "c", "type": "estimate", "title": "Estimate EST-2026-296", "filename": "EST-2026-296-preliminary-v3.pdf", "modified": "2026-10-01T16:00", "isFinal": True, "quoteNumber": "EST-2026-296"},
    ]
    found = {"found": True, "client": "Nehal Elrefai", "docs": [{"doc_id": "a"}], "count": 1}
    out = expand_finals("Nehal final estimate", found, hub_get=lambda path, params: {"docs": docs})
    qns = [d["quote_number"] for d in out["docs"]]
    assert qns[:2] == ["EST-2026-297", "EST-2026-298"] and out["count"] == 3


def test_voice_has_file_search_and_share():
    from app.services.max import voice_live as vl
    names = [t["name"] for t in vl.realtime_tool_definitions()]
    assert "find_files" in names and "share_file" in names and "open_final_doc" in names
    from app.services.max.voice_brain import VOICE_CAPABILITIES
    assert "find_files" in VOICE_CAPABILITIES


def test_truth_guard_accepts_find_files_proof():
    from app.services.max.runtime_truth_enforcer import PROOF_TOOL_EXACT
    assert {"find_files", "share_file"} <= PROOF_TOOL_EXACT
