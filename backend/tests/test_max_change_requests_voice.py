"""Oct 4 2026 fixes: announced-action guard, voice language / web search / clarify rules."""
import sqlite3

import pytest

from app.services.max.founder_action_continuation import announced_action_nudge, announces_action_without_tool


@pytest.mark.parametrize("text", [
    "Let me pull up the cost/API-expense module to find where to add GropBot tracking, then make the change.",
    "I'll investigate what's tracking costs today, then submit the improvement request for your approval.",
    "Un segundo, consulto el clima y noticias locales.",
    "Voy a revisar los permisos.",
])
def test_announced_action_detected(text):
    assert announces_action_without_tool(text)


@pytest.mark.parametrize("text", [
    "Filed as improvement #12. It'll be built on a test copy for your approval.",
    "You're Rafael Giraldo, founder of Empire.",
    "Want me to file that as an improvement?",
    "EST-2026-297 is $4,200, status sent.",
    "I'll send it once you say yes.",
])
def test_plain_answers_not_flagged(text):
    assert not announces_action_without_tool(text)


def test_nudge_never_authorizes_sends():
    n = announced_action_nudge("Let me check")
    assert "request_improvement" in n and "explicit yes" in n


def test_voice_language_detection():
    from app.services.max import voice_live as vl
    assert vl.detect_language("¿Cuáles son las últimas noticias en Cartago Valle?") == "es"
    assert vl.detect_language("What is on my schedule today?") == "en"
    assert "Spanish" in vl.language_section("es") and "FIRST reply" in vl.language_section("es")
    assert "¿Español o English?" in vl.language_section(None)


def test_voice_last_call_language_from_journal(tmp_path):
    from app.services.max import voice_live as vl
    db = tmp_path / "j.db"
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE max_session_turns (id INTEGER PRIMARY KEY, conversation_id TEXT, channel TEXT, role TEXT, content TEXT, edition TEXT)")
    c.execute("INSERT INTO max_session_turns (conversation_id, channel, role, content, edition) VALUES ('voice-a','voice','user','Show me my quotes please','main')")
    c.execute("INSERT INTO max_session_turns (conversation_id, channel, role, content, edition) VALUES ('voice-b','voice','user','¿Cuáles son las últimas noticias en Cartago?','main')")
    c.commit(); c.close()
    assert vl.last_call_language(str(db)) == "es"
    assert vl.last_call_language(str(tmp_path / "missing.db")) is None


def test_voice_web_search_allowlisted_and_compact():
    from app.services.max import voice_live as vl
    assert "web_search" in vl.VOICE_TOOL_ALLOWLIST
    names = [d["name"] for d in vl.realtime_tool_definitions()]
    assert "web_search" in names
    out = vl._compact_for_voice("web_search", {"success": True, "result": {"query": "q", "source": "DuckDuckGo", "results": [
        {"title": "T", "url": "https://example.com/a", "snippet": "S" * 500}]}})
    assert out["result"]["results"][0]["site"] == "example.com"
    assert len(out["result"]["results"][0]["snippet"]) <= 260


def test_voice_brain_clarify_and_news():
    from app.services.max.voice_brain import VOICE_CAPABILITIES, VOICE_STYLE
    assert "clarifying question" in VOICE_CAPABILITIES and "web_search" in VOICE_CAPABILITIES
    assert "request_improvement" in VOICE_CAPABILITIES
    assert "un segundo" in VOICE_STYLE

