"""Ranked clickable Fuentes for Max-e web search."""
from app.services.max.search_sources import (
    attach_ranked_sources,
    edition_official_hosts,
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


def test_own_business_website_is_official():
    rows = rank_search_results(
        [
            {"title": "TikTok AMP", "url": "https://www.tiktok.com/@amp"},
            {"title": "Nota", "url": "https://www.eltiempo.com/amp-nota"},
            {"title": "Cursos AMP", "url": "https://actitudmentalpositiva.com/cursos"},
            {"title": "WWW AMP", "url": "https://www.actitudmentalpositiva.com/"},
        ],
        official_hosts=["actitudmentalpositiva.com"],
    )
    assert [row["source_bucket"] for row in rows[:2]] == ["official", "official"]
    assert rows[-1]["source_bucket"] == "social"
    assert source_bucket(
        "https://cursos.actitudmentalpositiva.com",
        official_hosts=["actitudmentalpositiva.com"],
    ) == "official"
    assert source_bucket(
        "https://notactitudmentalpositiva.com",
        official_hosts=["actitudmentalpositiva.com"],
    ) == "other"


def test_amp_edition_product_site_is_official(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    hosts = edition_official_hosts()
    assert "actitudmentalpositiva.com" in hosts
    assert source_bucket("https://actitudmentalpositiva.com/cursos") == "official"


def test_registry_matches_host_not_title_or_path():
    assert source_bucket("https://www.rues.org.co/empresa", "Empresa") == "registry"
    assert source_bucket("https://www.camaracali.org.co/", "Cámara") == "registry"
    assert source_bucket("https://directorio.example.co/fichas", "") == "registry"
    assert source_bucket("https://www.bogotachamber.com/listing", "") == "registry"
    assert source_bucket(
        "https://www.eltiempo.com/directorio-empresas",
        "Directorio y Cámara de Comercio / RUES",
    ) == "news"
    assert source_bucket(
        "https://www.elespectador.com/economia/camara-de-comercio",
        "La cámara y el RUES",
    ) == "news"


def test_fuentes_are_short_clickable_links_without_raw_url():
    block = format_fuentes_markdown([
        {"title": "Sitio oficial AMP", "url": "https://amp.gov.co/hola"},
        {"title": "TikTok AMP", "url": "https://www.tiktok.com/@amp"},
    ])
    assert block.startswith("**Fuentes**")
    assert "[Sitio oficial AMP](https://amp.gov.co/hola)" in block
    assert " — https://amp.gov.co/hola" not in block
    assert block.count("https://amp.gov.co/hola") == 1
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
    assert " — https://www.banrep.gov.co/trm" not in out
    assert out.index("banrep.gov.co") < out.index("instagram.com")
    assert "tiktok.com" not in out


def test_family_grounding_asks_for_clickable_fuentes(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    from app.services.max.factual_guard import grounding_directive

    text = grounding_directive("Qué pasó en Panamá")
    assert "Fuentes" in text
    assert "[título](url)" in text
    assert "sin repetir" in text
    assert "TikTok" in text
    assert "2 a 5 oraciones" in text
