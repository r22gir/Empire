"""Ranked clickable Fuentes for Max-e web search."""
from app.services.max.search_sources import (
    attach_ranked_sources,
    format_fuentes_markdown,
    rank_search_results,
    source_bucket,
)


def test_official_and_news_beat_social():
    rows = rank_search_results([
        {"title": "AMP on TikTok", "url": "https://www.tiktok.com/@amp"},
        {"title": "AMP Instagram", "url": "https://instagram.com/amp"},
        {"title": "AMP Facebook", "url": "https://www.facebook.com/amp"},
        {"title": "El Tiempo", "url": "https://www.eltiempo.com/amp-nota"},
        {"title": "Registro RUES", "url": "https://www.rues.org.co/empresa"},
        {"title": "Sitio oficial", "url": "https://amp.gov.co/"},
    ])
    buckets = [row["source_bucket"] for row in rows]
    assert buckets[0] == "official"
    assert "registry" in buckets[:3]
    assert buckets[-3:] == ["social", "social", "social"]
    assert source_bucket("https://www.facebook.com/x") == "social"


def test_fuentes_are_clickable_title_and_url():
    block = format_fuentes_markdown([
        {"title": "Sitio oficial AMP", "url": "https://amp.gov.co/hola"},
        {"title": "TikTok AMP", "url": "https://www.tiktok.com/@amp"},
    ])
    assert block.startswith("**Fuentes**")
    assert "[Sitio oficial AMP](https://amp.gov.co/hola) — https://amp.gov.co/hola" in block
    assert block.index("amp.gov.co") < block.index("tiktok.com")


def test_attach_replaces_bare_sources_list():
    answer = "El dólar subió.\n\n**Sources**\n- tiktok.com"
    out = attach_ranked_sources(answer, [{
        "tool": "web_search",
        "success": True,
        "result": {"results": [
            {"title": "BanRep", "url": "https://www.banrep.gov.co/trm"},
            {"title": "Reel", "url": "https://www.instagram.com/p/abc"},
        ]},
    }])
    assert "**Fuentes**" in out
    assert "[BanRep](https://www.banrep.gov.co/trm)" in out
    assert out.index("banrep.gov.co") < out.index("instagram.com")
    assert "tiktok.com" not in out


def test_family_grounding_asks_for_clickable_fuentes(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    from app.services.max.factual_guard import grounding_directive

    text = grounding_directive("Qué pasó en Panamá")
    assert "Fuentes" in text
    assert "[título](url)" in text
    assert "TikTok" in text
    assert "2 a 5 oraciones" in text
