"""Public SEO artifacts for Empire Fine Fabrics.

Customer pages get per-product meta + schema.org Product. The sitemap and
Google Merchant Center feed list only goods that are for online sale —
hidden mills and the Unsorted queue are excluded.
"""

from __future__ import annotations

import os
from xml.sax.saxutils import escape

from app.services.fine_fabrics.catalog import get_product, list_catalog

PUBLIC_ORIGIN = os.getenv("FINE_FABRICS_PUBLIC_ORIGIN", "https://fabrics.empirebox.store")
STORE_BRAND = "Empire Fine Fabrics"


def public_origin() -> str:
    return (os.getenv("FINE_FABRICS_PUBLIC_ORIGIN") or PUBLIC_ORIGIN).rstrip("/")


def product_url(product_id: int) -> str:
    return f"{public_origin()}/fine-fabrics/{int(product_id)}"


def product_seo(product: dict) -> dict:
    pattern = (product.get("pattern") or "").strip()
    color = (product.get("color") or "").strip()
    code = (product.get("empire_code") or "").strip()
    title_bits = [b for b in (pattern, color) if b]
    title = " ".join(title_bits) or STORE_BRAND
    if code:
        title = f"{title} · {code} | {STORE_BRAND}"
    else:
        title = f"{title} | {STORE_BRAND}"
    unit = product.get("unit_label") or "yard"
    price = product.get("price_per_unit") or product.get("price_per_yard") or 0
    parts = [
        f"{pattern} {color}".strip(),
        product.get("category") or "",
        product.get("content") or "",
        f"{product.get('width')} wide" if product.get("width") else "",
        f"{price:.2f} per {unit}" if price else "",
    ]
    description = ". ".join(p for p in parts if p) or f"Cloth from {STORE_BRAND}."
    brand = product.get("brand") or STORE_BRAND
    image = product.get("image_url")
    if image and image.startswith("/"):
        image = f"{public_origin()}{image}"
    if not image:
        image = f"{public_origin()}/ff-placeholder-swatch.svg"
    url = product_url(product["id"])
    json_ld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": f"{pattern} {color}".strip() or code,
        "sku": code,
        "description": description,
        "brand": {"@type": "Brand", "name": brand},
        "image": image,
        "url": url,
        "offers": {
            "@type": "Offer",
            "url": url,
            "priceCurrency": "USD",
            "price": f"{float(price):.2f}",
            "availability": "https://schema.org/InStock",
            "itemCondition": "https://schema.org/NewCondition",
        },
    }
    return {
        "title": title,
        "description": description,
        "canonical": url,
        "json_ld": json_ld,
    }


def attach_seo(product: dict | None) -> dict | None:
    if not product:
        return None
    product = dict(product)
    product["seo"] = product_seo(product)
    return product


def sitemap_xml() -> str:
    urls = [
        f"{public_origin()}/fine-fabrics",
        f"{public_origin()}/fine-fabrics/samples",
    ]
    for product in list_catalog(owner=False):
        urls.append(product_url(product["id"]))
    body = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc in urls:
        body.append("  <url>")
        body.append(f"    <loc>{escape(loc)}</loc>")
        body.append("  </url>")
    body.append("</urlset>")
    return "\n".join(body) + "\n"


def merchant_xml() -> str:
    """Google Merchant Center RSS 2.0. Hidden vendors and Unsorted stay out."""
    origin = public_origin()
    items = []
    for product in list_catalog(owner=False):
        seo = product_seo(product)
        image = seo["json_ld"]["image"]
        brand = product.get("brand") or STORE_BRAND
        price = product.get("price_per_unit") or product.get("price_per_yard") or 0
        items.append(
            "\n".join(
                [
                    "    <item>",
                    f"      <g:id>{escape(str(product.get('empire_code') or product['id']))}</g:id>",
                    f"      <title>{escape(seo['json_ld']['name'])}</title>",
                    f"      <description>{escape(seo['description'])}</description>",
                    f"      <link>{escape(seo['canonical'])}</link>",
                    f"      <g:image_link>{escape(str(image))}</g:image_link>",
                    f"      <g:price>{float(price):.2f} USD</g:price>",
                    "      <g:availability>in_stock</g:availability>",
                    "      <g:condition>new</g:condition>",
                    f"      <g:brand>{escape(str(brand))}</g:brand>",
                    "    </item>",
                ]
            )
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">\n'
        "  <channel>\n"
        f"    <title>{escape(STORE_BRAND)}</title>\n"
        f"    <link>{escape(origin)}</link>\n"
        "    <description>Cloth for drapery, upholstery, and outdoor work. Shipping is never free.</description>\n"
        + ("\n".join(items) + "\n" if items else "")
        + "  </channel>\n"
        "</rss>\n"
    )


def get_public_product(product_id: int) -> dict | None:
    return attach_seo(get_product(product_id, owner=False, allow_hidden=False))
