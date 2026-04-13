from app.routers.relistapp import _extract_product_from_html, _score_deal


def test_extract_product_from_html_gets_actionable_fields():
    html = """
    <html>
      <head>
        <meta property="og:title" content="Acme Adjustable Laptop Stand" />
        <meta name="description" content="Aluminum folding stand." />
        <meta property="product:price:amount" content="24.99" />
        <meta property="product:brand" content="Acme" />
        <meta property="og:image" content="https://example.test/stand.jpg" />
      </head>
      <body><div itemprop="availability" content="https://schema.org/InStock">In stock</div></body>
    </html>
    """

    product = _extract_product_from_html("https://example.test/item/acme-stand", "example", html)

    assert product.title == "Acme Adjustable Laptop Stand"
    assert product.description == "Aluminum folding stand."
    assert product.price == 24.99
    assert product.brand == "Acme"
    assert product.images == ["https://example.test/stand.jpg"]
    assert product.extraction_status == "live"
    assert product.needs_manual_review is False


def test_extract_product_from_html_marks_missing_price_for_review():
    html = "<html><head><title>Mystery Product</title></head><body>No price</body></html>"

    product = _extract_product_from_html("https://example.test/item/mystery", "example", html)

    assert product.title == "Mystery Product"
    assert product.price == 0
    assert product.extraction_status == "partial"
    assert product.needs_manual_review is True
    assert "No source price found" in product.extraction_error


def test_score_deal_returns_actionable_profit_signal():
    deal = _score_deal(market_price=80, source_price=25, shipping=8, fees=10)

    assert deal["score"] > 0
    assert deal["label"] in {"medium", "strong"}
    assert deal["profit"] == 37
    assert "ROI" in deal["reason"]
