"""Model-first pre-lookups + MiniMax bullet-list fix (2026-10-07). No model, no data."""
from app.services.max import answer_policy as ap


def _tools(msg, history=None):
    return [c["tool"] for c in ap.prelookup_calls(msg, history)]


def test_named_client_runs_quote_lookup():
    assert _tools("What's the latest quote for Dahlia?") == ["search_quotes"]
    assert _tools("Show me Nehal's phase 1 quote") == ["search_quotes"]
    assert _tools("Mándame la cotización EST-2026-297 aquí")[0] == "get_quote"


def test_job_docs_run_file_search():
    assert "find_files" in _tools("Wall Unit for Philip and Naomi.")
    assert _tools("Find the Willard addendum PDF") == ["find_files"]


def test_job_visual_typos_run_file_search():
    hist = [{"role": "user", "content": "Best possible solution is a 4 panel basket weave v 8 panel"},
            {"role": "assistant", "content": "Got it: Marley's seat backs, 4-panel vs 8-panel."}]
    calls = ap.prelookup_calls("Show me mick up drwings or something for bisual reference", hist)
    assert calls and calls[0]["tool"] == "find_files" and "marleys" in calls[0]["query"]
    assert _tools("Show me a mockup of the Marley's basketweave seat back") == ["find_files"]


def test_weather_and_brief():
    calls = ap.prelookup_calls("What's the weather in Hyattsville tomorrow?")
    assert calls == [{"tool": "get_weather", "city": "Hyattsville"}]
    assert "get_tasks" in _tools("Morning Max, brief me on today's jobs")


def test_no_prelookup_for_small_talk_or_research():
    assert _tools("hi") == []
    assert _tools("Research the latest on solar for the Travelers claim") == []


def test_minimax_sanitizer_keeps_bullet_lists():
    from app.services.max.ai_router import AIRouter
    r = AIRouter.__new__(AIRouter)
    text = "Here's what we have for Nehal:\n\n- EST-2026-297 Phase 1, $3,411.84, draft\n- EST-2026-298 Phase 2, $9,350.76, draft\n\nWant me to open one?"
    out = r._sanitize_minimax_content(text)
    assert "EST-2026-297" in out and "EST-2026-298" in out
    talk = "Let me think about this.\n- let me check quotes\n\nEST-2026-298 is the latest."
    assert r._sanitize_minimax_content(talk).startswith("EST-2026-298")
