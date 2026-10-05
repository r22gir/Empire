"""max-sessions: journal + daily export (2026-10-04). Uses tmp dirs only."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest


@pytest.fixture()
def env(tmp_path, monkeypatch):
    data = tmp_path / "empire-data"
    (data / "brain").mkdir(parents=True)
    (data / "uploads" / "images").mkdir(parents=True)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(data))
    monkeypatch.setenv("EMPIRE_BRAIN_DIR", str(data / "brain"))
    monkeypatch.setenv("EMPIRE_MAX_JOURNAL_DB", str(data / "brain" / "max_session_journal.db"))
    monkeypatch.setenv("EMPIRE_MAX_JOURNAL_ARCHIVE", str(data / "max-sessions-archive" / "attachments"))
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    return data


def test_disabled_under_pytest_without_explicit_db(monkeypatch):
    from app.services.max import session_journal as sj
    monkeypatch.delenv("EMPIRE_MAX_JOURNAL_DB", raising=False)
    assert sj.is_enabled() is False


def test_exchange_archives_image_and_tool_summary(env):
    from app.services.max import session_journal as sj
    img = env / "uploads" / "images" / "IMG_1.jpg"
    img.write_bytes(b"\xff\xd8\xff fake jpeg")
    uid = sj.record_exchange(
        conversation_id="c1", channel="dashboard", user_text="what do you see?",
        assistant_text="A window.", image_filename="IMG_1.jpg",
        tool_results=[{"tool": "search_contacts", "success": False, "error": "boom", "args": {"pin": "1234", "q": "x"}}],
        model="m",
    )
    assert uid
    img.unlink()  # original deleted — archive must survive
    turns = sj.get_session("c1")
    assert [t["role"] for t in turns] == ["user", "assistant"]
    assert turns[0]["channel"] == "studio"
    att = turns[0]["attachments"][0]
    assert att["archived"] and Path(att["archive_path"]).is_file()
    assert sj.attachment_path(att["sha256"][:24]) is not None
    call = turns[1]["tool_calls"][0]
    assert call["tool"] == "search_contacts" and call["success"] is False and call["error"] == "boom"
    assert call["args"]["pin"] == "[redacted]"


def test_stream_capture_reads_sse():
    from app.services.max.session_journal import StreamCapture
    cap = StreamCapture()
    cap.feed('data: {"type": "text", "content": "Hel"}\n\ndata: {"type": "text", "con')
    cap.feed('tent": "lo"}\n\ndata: {"type": "tool_result", "tool": "t", "success": true, "result": {"a": 1}}\n\n')
    cap.feed(b'data: {"type": "done", "model_used": "x", "conversation_id": "abc"}\n\n')
    assert cap.text == "Hello" and cap.model == "x" and cap.conversation_id == "abc" and cap.done
    assert cap.tool_results[0]["tool"] == "t"


@pytest.mark.asyncio
async def test_journal_stream_passthrough(env):
    from types import SimpleNamespace
    from app.services.max import session_journal as sj

    async def body():
        yield 'data: {"type": "text", "content": "I can\'t open that."}\n\n'
        yield 'data: {"type": "done", "model_used": "m", "conversation_id": "s1"}\n\n'

    req = SimpleNamespace(message="open it", channel="dashboard", image_filename=None, conversation_id=None, desk=None)
    chunks = [c async for c in sj.journal_stream(body(), request=req)]
    assert len(chunks) == 2
    turns = sj.get_session("s1")
    assert turns[1]["content"] == "I can't open that." and turns[1]["status"] == "ok"


def _legacy_db(data: Path):
    db = data / "brain" / "unified_messages.db"
    c = sqlite3.connect(db)
    c.execute("""CREATE TABLE unified_messages (id INTEGER PRIMARY KEY, conversation_id TEXT, channel TEXT, role TEXT,
                 content TEXT, model TEXT, tool_results TEXT, metadata TEXT, attachment_refs TEXT, created_at TEXT)""")
    rows = [
        ("L1", "web_chat", "user", "make a roman shade quote", None, None, None, None, "2026-10-04 14:00:00"),
        ("L1", "web_chat", "assistant", "I cannot find that customer.", "m", json.dumps([{"tool": "search_contacts", "success": False}]), None, None, "2026-10-04 14:00:05"),
        ("L1", "web_chat", "user", "make a roman shade quote", None, None, None, None, "2026-10-04 14:01:00"),
        ("L1", "web_chat", "user", "No, I said Sebastian Santos", None, None, None, None, "2026-10-04 14:02:00"),
        ("L2", "web_chat", "user", "photo", None, None, json.dumps({"image_filename": "gone.jpg"}), json.dumps([{"type": "upload", "ref": "gone.jpg"}]), "2026-10-04 15:00:00"),
        ("X", "email", "assistant", "brief", None, None, None, None, "2026-10-04 15:00:00"),
        ("Y", "web_chat", "user", "previous day", None, None, None, None, "2026-10-04 03:00:00"),  # 23:00 ET Oct 3
    ]
    c.executemany("INSERT INTO unified_messages (conversation_id, channel, role, content, model, tool_results, metadata, attachment_refs, created_at) VALUES (?,?,?,?,?,?,?,?,?)", rows)
    c.commit()
    c.close()


def test_export_day(env, tmp_path):
    from app.services.max import session_export as se, session_journal as sj
    _legacy_db(env)
    img = env / "uploads" / "images" / "IMG_2.png"
    img.write_bytes(b"\x89PNG fake")
    sj.record_exchange(conversation_id="J1", channel="telegram", user_text="look", assistant_text="Nice.",
                       image_filename="IMG_2.png", started_at=datetime(2026, 10, 4, 16, 0, tzinfo=timezone.utc),
                       finished_at=datetime(2026, 10, 4, 16, 0, 3, tzinfo=timezone.utc))
    out = tmp_path / "out"
    s = se.export_day("2026-10-04", out_root=out, data_dir=env)
    day = out / "2026-10-04"
    assert (day / "summary.json").is_file()
    assert s["sessions"] == 3, s["excluded_sessions"]  # L1, L2, J1 (email and previous-day row excluded)
    assert s["by_channel"]["telegram"]["sessions"] == 1
    assert s["images"] == {"exported": 1, "missing": 1}
    assert len(list((day / "images").iterdir())) == 1
    assert s["counts"]["tool_errors"] == 1 and s["counts"]["cant_replies"] == 1
    assert s["counts"]["repeats"] == 1 and s["counts"]["corrections"] == 1
    files = sorted(p.name for p in day.glob("*.jsonl"))
    assert len(files) == 3
    first = json.loads((day / files[0]).read_text().splitlines()[0])
    assert first["type"] == "session"


def test_family_edition_refused(env, monkeypatch, tmp_path):
    from app.services.max import session_export as se
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    with pytest.raises(se.FamilyEditionError):
        se.export_day("2026-10-04", out_root=tmp_path / "o", data_dir=env)
    monkeypatch.delenv("EMPIRE_EDITION")
    with pytest.raises(se.FamilyEditionError):
        se.export_day("2026-10-04", out_root=tmp_path / "o", data_dir=Path("/data/maxine"))


# ── traffic tagging (automated / test chats are kept but not counted as Rafael's) ──

def test_classify_traffic_rules():
    from app.services.max import session_journal as sj
    assert sj.classify_traffic("price the Willard drapes", {"ip": "50.202.56.37", "user_agent": "Mozilla/5.0 (iPhone)"})["traffic"] == "real"
    a = sj.classify_traffic("What continuity packet is loaded?", {"ip": "50.202.56.37"})
    assert a["traffic"] == "automated" and "continuity_audit_prompt" in a["reasons"]
    assert sj.classify_traffic("hello", {"ip": "127.0.0.1"})["reasons"] == ["local_host_client"]
    assert "automated_user_agent" in sj.classify_traffic("hello", {"ip": "100.102.84.127", "user_agent": "Mozilla/5.0 HeadlessChrome/147"})["reasons"]
    assert sj.classify_traffic("hello", {"ip": "testclient", "user_agent": "testclient"})["traffic"] == "test"
    assert sj.classify_traffic("hello", None)["traffic"] == "real"


def test_exchange_tagged_with_client_and_listing_hides_automated(env):
    from app.services.max import session_journal as sj
    sj.record_exchange(conversation_id="real-1", channel="web", user_text="price the Willard drapes",
                       assistant_text="ok", client={"ip": "100.102.84.127", "user_agent": "Mozilla/5.0 (iPhone)"})
    sj.record_exchange(conversation_id="audit-1", channel="web", user_text="what continuity packet is loaded",
                       assistant_text="Continuity audit completed.", client={"ip": "50.202.56.37"})
    sj.record_exchange(conversation_id="local-1", channel="web", user_text="is openclaw online",
                       assistant_text="yes", client={"ip": "127.0.0.1", "user_agent": "node-fetch"})
    u = sj.get_session("audit-1")[0]
    assert u["metadata"]["traffic"] == "automated" and u["metadata"]["client"]["ip"] == "50.202.56.37"
    assert sj.get_session("real-1")[0]["metadata"]["traffic"] == "real"
    assert [s["conversation_id"] for s in sj.list_sessions()] == ["real-1"]
    every = {s["conversation_id"]: s["traffic"] for s in sj.list_sessions(include_automated=True)}
    assert every == {"real-1": "real", "audit-1": "automated", "local-1": "automated"}


def test_export_excludes_automated_sessions_but_keeps_rows(env, tmp_path):
    from app.services.max import session_journal as sj
    from app.services.max import session_export as se
    sj.record_exchange(conversation_id="real-2", channel="web", user_text="draft the Osteria quote",
                       assistant_text="Drafted.", client={"ip": "50.202.56.37", "user_agent": "Mozilla/5.0"})
    # an older, untagged row (recorded before tagging existed) is caught by the prompt rule
    sj.record_turn("audit-old", "web", "user", "what continuity packet is loaded")
    sj.record_turn("audit-old", "web", "assistant", "Continuity audit completed.")
    today = sj.to_local(datetime.now(timezone.utc)).date()
    out = tmp_path / "out"
    summary = se.export_day(today, out_root=out, data_dir=env)
    ids = [s["session_id"] for s in summary["session_index"]]
    assert ids == ["real-2"]
    reasons = {e["session"]: e["reason"] for e in summary["excluded_sessions"]}
    assert reasons["audit-old"].startswith("automated:") and "continuity_audit_prompt" in reasons["audit-old"]
    assert summary["counts"]["excluded_by_reason"]
    assert len(sj.get_session("audit-old")) == 2  # nothing deleted
    full = se.export_day(today, out_root=tmp_path / "out2", data_dir=env, include_tests=True)
    assert {"real-2", "audit-old"} <= {s["session_id"] for s in full["session_index"]}


def test_max_router_captures_client_for_journal(env):
    from fastapi import FastAPI, APIRouter, Depends, Request
    from fastapi.testclient import TestClient
    from app.services.max import session_journal as sj
    r = APIRouter(dependencies=[Depends(sj.capture_client)])

    @r.post("/x")
    async def x():
        sj.record_exchange(conversation_id="via-http", channel="web", user_text="hi", assistant_text="hey")
        return {"ok": True}

    app = FastAPI()
    app.include_router(r)
    assert TestClient(app).post("/x").json() == {"ok": True}
    md = sj.get_session("via-http")[0]["metadata"]
    assert md["client"]["ip"] == "testclient" and md["traffic"] == "test"
