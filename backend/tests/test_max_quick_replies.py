"""Greeting / docs-location / existing-quote lookups and internal-source scrub (2026-10-04)."""
from app.services.max import quick_replies as q


def test_greetings_only_when_bare():
    for t in ("Hi", "hi!", "Hey Max", "good evening", "hola", "what's up"):
        assert q.is_greeting(t), t
    for t in ("Hi, send me the last quote", "Hello can you check the Dahlia job", "good job on that quote", "hi 2"):
        assert not q.is_greeting(t), t
    assert q.direct_reply("Hi")["skill"] == "greeting"
    assert q.direct_reply("Hi", has_image=True) is None  # images always go to the model


def test_docs_location_typo_tolerant():
    assert q.is_docs_location_request("Where are the dics you have comoleted?")
    assert q.is_docs_location_request("where are my docs")
    assert not q.is_docs_location_request("where are we on the Dahlia job")


def test_docs_location_reply_links(monkeypatch):
    monkeypatch.setattr(q, "latest_final_docs", lambda limit=5: [
        {"id": "abc", "title": "Dahlia final estimate", "client": "Dahlia Design", "modified": "2026-10-02T20:00"}])
    web = q.docs_location_reply("web")
    assert "/?screen=final-docs" in web and "/docs/view?id=abc" in web and "docs/" not in web.replace("/docs/view", "")
    wa = q.docs_location_reply("whatsapp")
    assert "https://" in wa and "/?screen=final-docs" in wa


def test_quote_lookup_vs_new_quote_dictation():
    assert q.parse_quote_lookup("Send me last quote") == {"quote_number": "", "names": [], "want_pdf": True}
    hit = q.parse_quote_lookup("Can you send me like a voice message, like a status on the last Marley's quote?")
    assert hit and hit["names"][0] == "marley"
    assert q.parse_quote_lookup("what's the status of EST-2026-295")["quote_number"] == "EST-2026-295"
    assert q.parse_quote_lookup("Make a new quote for Marley 2 cushions 20 by 20") is None
    assert q.parse_quote_lookup("quote for Dahlia, bench 60 inches") is None


def test_quote_lookup_reply_uses_latest_match(monkeypatch):
    rows = [
        {"id": "a1", "quote_number": "EST-2026-294", "customer_name": "Marley's Hyattsville", "status": "draft", "total": 5605.94, "created_at": "2026-10-01T12:00"},
        {"id": "a2", "quote_number": "EST-2026-295", "customer_name": "Marley's Hyattsville", "status": "draft", "total": 3546.69, "created_at": "2026-10-01T12:30"},
    ]
    import app.services.quote_service as qs
    monkeypatch.setattr(qs, "list_quotes", lambda **kw: {"quotes": list(rows) if kw.get("search") in (None, "marley") else []})
    out = q.quote_lookup_reply("status on the last Marley's quote", channel="whatsapp")
    assert out["quote"]["quote_number"] == "EST-2026-295"
    assert "EST-2026-295" in out["text"] and "$3,546.69" in out["text"] and "draft" in out["text"] and "Next step" in out["text"]


def test_internal_sources_scrubbed():
    text = ("Your docs are in Final Docs.\n\n### Sources\n1. `docs/MAX_DOCUMENT_WORKSPACE.md` — open_final_doc.\n"
            "2. MAX Operating Truth Registry, Surface Truth — drawings render inline.")
    assert q.scrub_internal_sources(text) == "Your docs are in Final Docs."
    keep = "Answer [1](https://a.com)\n\nSources\n1. A — a.com (2026)\n2. docs/X.md — y"
    out = q.scrub_internal_sources(keep)
    assert "a.com (2026)" in out and "docs/X.md" not in out
