"""Official-sources web search: providers, tiers, citations, footer, family."""
from __future__ import annotations

import pytest

from app.services.max.official_search.citations import (
    strip_invented_citations,
    verify_citations,
    verify_quoted_text,
)
from app.services.max.official_search.family import family_search_guard, maxine_blocks_query
from app.services.max.official_search.footer import attach_sources_footer, build_sources_footer
from app.services.max.official_search.intent import is_official_intent
from app.services.max.official_search.pipeline import (
    finalize_research_reply,
    official_page_char_cap,
    run_web_search,
)
from app.services.max.official_search.providers import (
    BraveProvider,
    DuckDuckGoProvider,
    ExaProvider,
    ProviderError,
    SearchHit,
    SearchProvider,
    TavilyProvider,
    minimax_research_enabled,
    provider_fallback_order,
    run_providers,
)
from app.services.max.official_search.trust_tiers import classify_domain, filter_by_tiers


class _FakeProvider(SearchProvider):
    def __init__(self, name, hits=None, error=None, enabled=True):
        self.name = name
        self._hits = hits or []
        self._error = error
        self._enabled = enabled
        self.calls = 0

    def enabled(self):
        return self._enabled

    def search(self, query, num_results=5, **kwargs):
        self.calls += 1
        if self._error:
            raise ProviderError(self.name, self._error)
        return list(self._hits)[:num_results]


CDC = SearchHit(
    title="CDC Influenza",
    url="https://www.cdc.gov/flu/prevent/index.htm",
    snippet="Annual influenza vaccination is recommended.",
    published="2024-08-15",
    provider="exa",
)
NIH = SearchHit(
    title="NIH Flu",
    url="https://www.nih.gov/news-events/flu",
    snippet="NIH influenza research.",
    published="2024-07-01",
    provider="exa",
)
BLOG = SearchHit(
    title="Random blog",
    url="https://random-blog.example/flu-cures",
    snippet="Unverified claims.",
    provider="ddg",
)
REUTERS = SearchHit(
    title="Reuters flu",
    url="https://www.reuters.com/health/flu",
    snippet="Wire copy.",
    provider="tavily",
)


def test_official_intent_en_and_es():
    assert is_official_intent("official CDC flu guidance")
    assert is_official_intent("fuente oficial del gobierno sobre vacunas")
    assert is_official_intent("look this up on .gov")
    assert is_official_intent("sitio oficial del IRS")
    assert not is_official_intent("best restaurant booth fabric")


def test_official_mode_returns_only_tier1_domains():
    providers = [_FakeProvider("exa", [CDC, NIH, BLOG, REUTERS])]
    payload = run_web_search(
        {"query": "official CDC influenza schedule", "num_results": 10},
        providers=providers,
    )
    assert payload["success"] is True
    urls = [r["url"] for r in payload["result"]["results"]]
    assert urls
    for url in urls:
        assert classify_domain(url) == 1
        host = url.split("/")[2]
        assert host.endswith(".gov") or host.endswith(".mil") or host.endswith(".edu")
    assert "random-blog.example" not in " ".join(urls)
    assert "reuters.com" not in " ".join(urls)


def test_no_tier1_says_so_and_labels_unverified():
    providers = [_FakeProvider("exa", [BLOG, REUTERS])]
    payload = run_web_search(
        {"query": "official source for this rumor", "num_results": 5},
        providers=providers,
    )
    assert payload["success"] is True
    assert payload["result"]["no_tier1"] is True
    assert "No official (Tier 1)" in payload["result"]["notice"]
    for row in payload["result"]["results"]:
        assert row["tier"] != 1


def test_spanish_sources_footer():
    pages = [{
        "url": "https://www.cdc.gov/flu",
        "title": "Gripe",
        "published": "2024-08-15",
        "text": "Vacuna anual recomendada por el CDC.",
        "tier": 1,
        "read": True,
    }]
    footer = build_sources_footer(pages, language="es")
    assert footer.startswith("Fuentes")
    assert "Oficial" in footer
    assert "leído" in footer
    assert "cdc.gov" in footer
    attached = attach_sources_footer(
        "La vacuna es anual.\n\n## Sources\n1. invented.com",
        pages,
        question="fuente oficial de la vacuna",
    )
    assert "Fuentes" in attached
    assert attached.count("Fuentes") == 1
    assert "invented.com" not in attached.split("Fuentes")[1] or "[Gripe]" in attached


def test_no_urls_in_voice_output():
    pages = [{
        "url": "https://www.cdc.gov/flu/prevent/index.htm",
        "title": "CDC Influenza",
        "text": "Annual influenza vaccination is recommended for everyone 6 months and older.",
        "published": "2024-08-15",
        "tier": 1,
        "read": True,
    }]
    draft = (
        "CDC recommends an annual flu shot.\n\n"
        "See [CDC Influenza](https://www.cdc.gov/flu/prevent/index.htm)\n"
        "https://invented.example/not-real"
    )
    spoken = finalize_research_reply(
        draft, pages=pages, question="official flu guidance", channel="voice", official=True,
    )
    assert "http" not in spoken.lower()
    assert "cdc.gov" not in spoken.lower() or "http" not in spoken.lower()
    assert "https://" not in spoken
    assert "CDC Influenza" in spoken


def test_citation_stripping_invented_and_quotes():
    pages = [{
        "url": "https://www.cdc.gov/flu",
        "title": "CDC",
        "text": "Annual influenza vaccination is recommended for most people.",
    }]
    text = (
        'The CDC says "Annual influenza vaccination is recommended for most people" '
        "([CDC](https://www.cdc.gov/flu)). "
        'They also said "drink bleach daily" '
        "(https://www.cdc.gov/flu). "
        "See also [Blog](https://totally-fake.example/x)."
    )
    checked = verify_citations(text, pages)
    assert "https://totally-fake.example/x" not in checked["text"]
    assert checked["links_removed"] >= 1
    assert "drink bleach daily" not in checked["text"]
    assert checked["quotes_removed"] >= 1
    cleaned, n = strip_invented_citations(
        "Read https://never-fetched.example/a and [CDC](https://www.cdc.gov/flu)",
        pages,
    )
    assert "never-fetched.example" not in cleaned
    assert n >= 1
    quoted, qn = verify_quoted_text('"this quote is not on the page at all now"', pages)
    assert qn == 1
    assert "this quote is not" not in quoted


def test_fallback_order_exa_tavily_brave_off_ddg(monkeypatch):
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    monkeypatch.delenv("EXA_API_KEY_MAXINE", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY_MAXINE", raising=False)
    monkeypatch.setenv("EMPIRE_EDITION", "main")
    assert provider_fallback_order() == ["duckduckgo"]
    assert BraveProvider().enabled() is False

    monkeypatch.setenv("EXA_API_KEY", "exa-free")
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-free")
    assert provider_fallback_order() == ["exa", "tavily", "duckduckgo"]
    assert "brave" not in provider_fallback_order()

    monkeypatch.setenv("BRAVE_API_KEY", "bs-key")
    assert provider_fallback_order() == ["exa", "tavily", "brave", "duckduckgo"]


def test_fail_closed_on_provider_errors():
    providers = [
        _FakeProvider("exa", error="timeout", enabled=True),
        _FakeProvider("tavily", error="http 500", enabled=True),
        _FakeProvider("duckduckgo", error="blocked", enabled=True),
    ]
    raw = run_providers("official IRS standard mileage", providers=providers)
    assert raw["ok"] is False
    assert raw["results"] == []
    assert raw["error"]

    payload = run_web_search({"query": "official IRS mileage"}, providers=providers)
    assert payload["success"] is False
    assert payload["error"]
    assert payload["result"]["results"] == []


def test_empty_from_primary_falls_through_to_next():
    ddg = _FakeProvider("duckduckgo", [CDC])
    providers = [
        _FakeProvider("exa", hits=[], enabled=True),
        _FakeProvider("brave", enabled=False),
        ddg,
    ]
    raw = run_providers("cdc flu", providers=providers)
    assert raw["ok"] is True
    assert raw["source"] == "duckduckgo"
    assert ddg.calls == 1


def test_minimax_research_stays_off(monkeypatch):
    monkeypatch.delenv("MINIMAX_WEB_SEARCH_FOR_RESEARCH", raising=False)
    assert minimax_research_enabled() is False


def test_family_usage_cap_and_maxine_argos(monkeypatch):
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    assert maxine_blocks_query("Argos Campestre NIT and bylaws") is True
    blocked = run_web_search({"query": "Argos Campestre legal documents"})
    assert blocked["success"] is False
    assert blocked["error"] == "maxine_argos_blocked"
    assert blocked["result"]["results"] == []

    monkeypatch.setenv("OFFICIAL_SEARCH_USED_PCT", "20")
    monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")
    guard = family_search_guard("web_search")
    assert guard["ok"] is False
    assert guard["error"] == "family_usage_cap"


def test_family_keys_do_not_inherit_workroom(monkeypatch):
    from app.services.max.official_search.config import edition_key

    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    monkeypatch.setenv("EXA_API_KEY", "workroom-key")
    monkeypatch.delenv("EXA_API_KEY_MAXINE", raising=False)
    assert edition_key("EXA_API_KEY") == ""
    monkeypatch.setenv("EXA_API_KEY_MAXINE", "maxine-key")
    assert edition_key("EXA_API_KEY") == "maxine-key"


def test_official_page_cap_is_6_to_8k():
    cap = official_page_char_cap("https://www.cdc.gov/flu", official_mode=True)
    assert 6000 <= cap <= 8000
    normal = official_page_char_cap("https://random-blog.example/x", official_mode=False)
    assert normal == 2500


def test_one_per_domain_and_independent():
    dup = [
        {"url": "https://www.cdc.gov/a", "title": "A"},
        {"url": "https://www.cdc.gov/b", "title": "B"},
        {"url": "https://www.nih.gov/c", "title": "C"},
    ]
    out = filter_by_tiers(dup, official=True, query="official flu")
    domains = {r["domain"] for r in out["results"]}
    assert "cdc.gov" in domains
    assert len([r for r in out["results"] if r["domain"] == "cdc.gov"]) == 1
    assert out["independent"] is True


def test_tavily_include_domains_hard_filter():
    seen = {}

    class _Tavily(TavilyProvider):
        def enabled(self):
            return True

        def search(self, query, num_results=5, **kwargs):
            seen["include_domains"] = kwargs.get("include_domains")
            return [CDC]

    # Patch edition key so Tavily counts as enabled in order, then call via fake.
    raw = run_providers(
        "official flu",
        include_domains=["cdc.gov", "nih.gov"],
        providers=[_Tavily()],
    )
    assert raw["ok"] is True
    assert "cdc.gov" in (seen.get("include_domains") or [])


def test_authoritative_tools_optional(monkeypatch):
    from app.services.max.official_search.authoritative import (
        congress_search,
        fact_check_search,
        pubmed_search,
        wikipedia_search,
    )

    monkeypatch.delenv("DATA_GOV_API_KEY", raising=False)
    monkeypatch.delenv("CONGRESS_GOV_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_FACTCHECK_API_KEY", raising=False)

    class _Resp:
        status_code = 403
        def json(self):
            return {}

    assert congress_search({"query": "chips act"}, http_get=lambda *a, **k: _Resp())["ok"] is False
    assert fact_check_search({"query": "vaccines"})["disabled"] is True

    class _Wiki:
        status_code = 200
        def json(self):
            return {"query": {"search": [{"title": "Influenza", "snippet": "A virus"}]}, "search": []}

    wiki = wikipedia_search({"query": "influenza"}, http_get=lambda *a, **k: _Wiki())
    assert wiki["ok"] is True
    assert wiki["results"][0]["url"].startswith("https://en.wikipedia.org/")


def test_tool_executor_fail_closed_and_shape():
    providers = [_FakeProvider("exa", error="boom"), _FakeProvider("duckduckgo", error="boom")]
    payload = run_web_search({"query": "official IRS mileage rate"}, providers=providers)
    assert payload["success"] is False
    assert payload["tool"] == "web_search"
    assert "results" in payload["result"]
