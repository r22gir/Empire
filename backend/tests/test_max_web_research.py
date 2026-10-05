"""Full-page research reads, empty-section validation, and a mocked research answer."""
import asyncio
from pathlib import Path

from app.services.max.answer_quality import (
    enforce_reply_structure,
    validate_reply_structure,
)
from app.services.max.web_research import (
    extract_dates,
    read_search_results,
    run_research_answer,
)

QUESTION = "Compare Sunbrella vs Crypton fabric for restaurant booths and cite sources."

SUNBRELLA_HTML = """
<html><head>
<meta content="2025-01-15" property="article:modified_time">
<meta property="article:published_time" content="2024-05-02T12:00:00Z">
<title>Sunbrella Contract</title>
</head><body><article>
<h1>Sunbrella for hospitality</h1>
<p>Sunbrella solution-dyed acrylic is rated at 30,000 double rubs (Wyzenbeek).
It cleans with mild soap and water and is bleach-cleanable.
Contract price is about $45 to $70 per yard for restaurant booth programs.</p>
</article></body></html>
"""

CRYPTON_HTML = """
<html><head><title>Crypton hospitality</title>
<script type="application/ld+json">
{"headline": "Crypton", "datePublished": "2023-11-08"}
</script>
</head><body>
<p>Crypton is a performance fabric with a moisture barrier, typically 50,000 double rubs.
Cleaning uses water-based cleaners and many patterns are bleach-cleanable.
Hospitality pricing is about $40 to $90 per yard.</p>
</body></html>
"""

COMPARE_HTML = """
<html><head>
<meta name="date" content="March 3, 2024">
<title>Booth fabric comparison</title>
</head><body>
<p>For restaurant booths, Crypton's moisture barrier handles spills better than standard Sunbrella.
Sunbrella is more breathable and widely available for large booth runs.</p>
</body></html>
"""

CLEANING_HTML = """
<html><body>
<p>Restaurant booth upholstery should be cleaned promptly after spills.
Sunbrella is bleach cleanable. Crypton uses a built-in stain barrier that still needs routine wiping.</p>
</body></html>
"""

PAYWALL_HTML = """
<html><body><p>Subscribe to continue reading this article. Members only.</p></body></html>
"""

GOOD_ANSWER = """
For restaurant booths, Crypton is the better working fabric. Sunbrella remains the better-known acrylic.

## Verified
Sunbrella solution-dyed acrylic is rated at 30,000 double rubs (Wyzenbeek). It cleans with mild soap and water and is bleach-cleanable. Contract price is about $45 to $70 per yard. [1](https://fabric.example/sunbrella)

Crypton is a performance fabric with a moisture barrier, typically 50,000 double rubs. Cleaning uses water-based cleaners and many patterns are bleach-cleanable. Hospitality pricing is about $40 to $90 per yard. [2](https://fabric.example/crypton)

Crypton's moisture barrier handles spills better than standard Sunbrella, while Sunbrella is more breathable. [3](https://fabric.example/compare)

## Max's inference
I recommend Crypton for restaurant booths. The moisture barrier and higher double-rub rating matter more at a booth edge than Sunbrella's breathability, and the yard-price ranges overlap.

## Sources
1. Sunbrella Contract — 2024-05-02 — https://fabric.example/sunbrella
2. Crypton hospitality — 2023-11-08 — https://fabric.example/crypton
3. Booth fabric comparison — 2024-03-03 — https://fabric.example/compare
4. Booth cleaning notes — date not shown — https://fabric.example/cleaning
"""

BAD_DRAFT = (
    "## Verified\n\n"
    "I am not able to confirm from these snippets alone:\n\n"
    "Want me to open the articles?"
)


def _pages():
    return {
        "https://dead.example/missing": {
            "status": 404, "text": "Not found", "content_type": "text/html", "error": None,
        },
        "https://pay.example/wall": {
            "status": 200, "text": PAYWALL_HTML, "content_type": "text/html", "error": None,
        },
        "https://fabric.example/sunbrella": {
            "status": 200, "text": SUNBRELLA_HTML, "content_type": "text/html", "error": None,
        },
        "https://fabric.example/crypton": {
            "status": 200, "text": CRYPTON_HTML, "content_type": "text/html", "error": None,
        },
        "https://timeout.example/slow": {
            "status": 0, "text": "", "content_type": "", "error": "TimeoutException",
        },
        "https://fabric.example/compare": {
            "status": 200, "text": COMPARE_HTML, "content_type": "text/html", "error": None,
        },
        "https://fabric.example/cleaning": {
            "status": 200, "text": CLEANING_HTML, "content_type": "text/html", "error": None,
        },
        "https://fabric.example/extra": {
            "status": 404, "text": "Gone", "content_type": "text/html", "error": None,
        },
    }


def _results():
    titles = {
        "https://dead.example/missing": "Missing",
        "https://pay.example/wall": "Paywalled",
        "https://fabric.example/sunbrella": "Sunbrella Contract",
        "https://fabric.example/crypton": "Crypton hospitality",
        "https://timeout.example/slow": "Timed out",
        "https://fabric.example/compare": "Booth fabric comparison",
        "https://fabric.example/cleaning": "Booth cleaning notes",
        "https://fabric.example/extra": "Extra dead page",
    }
    return [
        {"title": titles[url], "url": url, "snippet": "snippet only"}
        for url in titles
    ]


def test_extract_dates_from_meta_either_attribute_order_and_jsonld():
    published, updated = extract_dates(SUNBRELLA_HTML)
    assert published == "2024-05-02"
    assert updated == "2025-01-15"
    assert extract_dates(CRYPTON_HTML)[0] == "2023-11-08"
    assert extract_dates('<html><body><p>Updated March 1, 2022. Crypton barrier notes for booths.</p></body></html>')[1] == "2022-03-01"


def test_read_search_results_skips_dead_and_paywalled_and_reads_next_pages():
    pages = _pages()
    seen = []

    def fetch(url, timeout):
        seen.append((url, timeout))
        return pages[url]

    report = read_search_results(_results(), fetch=fetch, question=QUESTION)
    urls = [page["url"] for page in report["pages"]]
    assert urls == [
        "https://fabric.example/sunbrella",
        "https://fabric.example/crypton",
        "https://fabric.example/compare",
        "https://fabric.example/cleaning",
    ]
    assert "https://dead.example/missing" not in urls
    assert "https://pay.example/wall" not in urls
    assert "https://timeout.example/slow" not in urls
    reasons = {item["url"]: item["reason"] for item in report["skipped"]}
    assert reasons["https://dead.example/missing"] == "dead"
    assert reasons["https://pay.example/wall"] == "paywalled"
    assert reasons["https://timeout.example/slow"] == "dead"
    # First wave was short, so the reader tried the next ranked URLs.
    assert "https://fabric.example/extra" in {url for url, _timeout in seen}
    assert {timeout for _url, timeout in seen} == {8.0}

    by_url = {page["url"]: page for page in report["pages"]}
    sunbrella = by_url["https://fabric.example/sunbrella"]
    assert sunbrella["published"] == "2024-05-02"
    assert sunbrella["updated"] == "2025-01-15"
    assert sunbrella["date_label"] == "2024-05-02"
    assert "30,000 double rubs" in sunbrella["text"]
    assert "bleach-cleanable" in sunbrella["text"]
    assert by_url["https://fabric.example/crypton"]["date_label"] == "2023-11-08"
    assert by_url["https://fabric.example/compare"]["published"] == "2024-03-03"
    assert by_url["https://fabric.example/cleaning"]["date_label"] == "date not shown"
    assert "snippet only" not in sunbrella["text"]


def test_page_text_is_truncated():
    long_html = "<html><body><p>" + ("Sunbrella double rubs and bleach cleaning. " * 200) + "</p></body></html>"

    def fetch(url, timeout):
        return {"status": 200, "text": long_html, "content_type": "text/html", "error": None}

    report = read_search_results(
        [{"title": "Long", "url": "https://fabric.example/long", "snippet": ""}],
        fetch=fetch,
        question=QUESTION,
        max_chars=400,
        target_min=1,
        target_max=1,
    )
    text = report["pages"][0]["text"]
    assert text.endswith("[truncated]")
    assert len(text) < 450


def test_spanish_question_labels_undated_page_fecha_no_indicada():
    html = "<html><body><p>" + ("La tela Crypton resiste manchas en booths de restaurante. " * 4) + "</p></body></html>"

    def fetch(url, timeout):
        return {"status": 200, "text": html, "content_type": "text/html", "error": None}

    report = read_search_results(
        [{"title": "Tela", "url": "https://tela.example/crypton", "snippet": ""}],
        fetch=fetch,
        question="Compara la tela Sunbrella y Crypton para booths",
    )
    assert report["pages"][0]["date_label"] == "fecha no indicada"


def test_long_article_that_mentions_paywall_is_still_read():
    filler = "Sunbrella booth fabric stays bleach cleanable for restaurants. " * 40
    html = f"<html><body><p>{filler}</p><p>Some news sites use a paywall.</p></body></html>"

    def fetch(url, timeout):
        return {"status": 200, "text": html, "content_type": "text/html", "error": None}

    report = read_search_results(
        [{"title": "Guide", "url": "https://fabric.example/guide", "snippet": ""}],
        fetch=fetch,
        question=QUESTION,
        target_min=1,
        target_max=1,
    )
    assert report["pages"]
    assert report["skipped"] == []


def test_empty_section_validator_regenerates_then_fills():
    calls = []

    def regenerate(issues):
        calls.append(issues)
        return "Still empty:\n\nWant me to open the articles?"

    filled = enforce_reply_structure(
        "I am not able to confirm from these snippets alone:",
        regenerate=regenerate,
    )
    assert calls and "dangling_colon" in calls[0]
    assert "snippets alone" not in filled
    assert "open the articles" not in filled.lower()
    assert validate_reply_structure(filled) == []

    replaced = enforce_reply_structure(BAD_DRAFT, regenerate=lambda issues: GOOD_ANSWER)
    assert "30,000 double rubs" in replaced
    assert "Want me to open" not in replaced
    assert validate_reply_structure(replaced) == []


def test_research_answer_end_to_end_includes_data_citations_dates_and_recommendation():
    pages = _pages()
    attempts = []

    def fetch(url, timeout):
        return pages[url]

    def generate(prompt, attempt):
        attempts.append(attempt)
        if attempt == 1:
            assert "30,000 double rubs" in prompt
            assert "bleach-cleanable" in prompt
            assert "2024-05-02" in prompt
            assert "2023-11-08" in prompt
            assert "date not shown" in prompt
            assert "clear recommendation" in prompt
            assert "answer directly from the verified search-result snippets" not in prompt
            assert "snippet only" not in prompt.split("Fetched pages:")[1]
            return BAD_DRAFT
        return GOOD_ANSWER

    result = run_research_answer(QUESTION, _results(), fetch=fetch, generate=generate)
    answer = result["answer"]
    assert attempts == [1, 2]
    assert "30,000 double rubs" in answer
    assert "50,000" in answer
    assert "$45 to $70 per yard" in answer
    assert "$40 to $90 per yard" in answer
    assert "bleach-cleanable" in answer
    assert "[1](https://fabric.example/sunbrella)" in answer
    assert "[2](https://fabric.example/crypton)" in answer
    assert "2024-05-02" in answer
    assert "2023-11-08" in answer
    assert "2024-03-03" in answer
    assert "date not shown" in answer
    assert "I recommend Crypton" in answer
    assert "## Verified" in answer
    assert "Max's inference" in answer
    assert "## Sources" in answer
    assert "Want me to open" not in answer
    assert "snippets alone" not in answer
    assert validate_reply_structure(answer) == []
    assert len(result["pages"]) >= 3


def test_router_research_path_reads_pages_instead_of_snippets(monkeypatch):
    from app.routers.max.router import _attach_research_page_reads

    def fake_ground(question, payload, fetch=None, skip_urls=None):
        return {
            "pages": [{
                "url": "https://fabric.example/sunbrella",
                "title": "Sunbrella Contract",
                "text": "30,000 double rubs",
                "published": "2024-05-02",
                "updated": None,
                "date_label": "2024-05-02",
            }],
            "skipped": [],
            "tool_entries": [{
                "tool": "web_read",
                "success": True,
                "result": {
                    "url": "https://fabric.example/sunbrella",
                    "content": "30,000 double rubs",
                    "date_label": "2024-05-02",
                },
            }],
            "message": "grounded from pages",
        }

    monkeypatch.setattr("app.services.max.web_research.ground_web_search", fake_ground)
    round_results = [{
        "tool": "web_search",
        "success": True,
        "result": {"results": [{"url": "https://fabric.example/sunbrella", "title": "S", "snippet": "x"}]},
    }]
    tool_results = list(round_results)
    read_urls: set[str] = set()
    added = asyncio.run(_attach_research_page_reads(
        QUESTION, round_results, tool_results, read_urls,
    ))
    assert added[0]["tool"] == "web_read"
    assert "30,000 double rubs" in added[0]["result"]["content"]
    assert "https://fabric.example/sunbrella" in read_urls
    router_text = Path(__file__).resolve().parents[1].joinpath("app/routers/max/router.py").read_text()
    assert "answer directly from the verified search-result snippets" not in router_text
    assert "_ground_search_payload" in router_text
