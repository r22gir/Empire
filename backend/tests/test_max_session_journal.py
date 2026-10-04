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
