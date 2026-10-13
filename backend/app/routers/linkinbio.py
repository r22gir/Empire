"""Public Link-in-Bio catalog.

Each business slug is a public marketing page. The primary CTA routes to
LeadForge quote intake. This catalog is hardcoded and public-safe — it does
not read or write business.json / client_aliases.json.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

router = APIRouter(prefix="/linkinbio", tags=["linkinbio"])

# Public-safe marketing catalog only. No phones, addresses, or private config.
PUBLIC_BUSINESSES = {
    "empire-workroom": {
        "slug": "empire-workroom",
        "name": "Empire Workroom",
        "tagline": "Custom drapery, shades, blinds, and upholstery",
        "blurb": "Made-to-measure window treatments and soft furnishings for homes and designers in the DC metro.",
        "business_unit": "workroom",
        "accent": "#b8960c",
        "services": ["Custom drapery", "Shades & blinds", "Upholstery", "Bedding"],
        "links": [
            {"id": "quote", "label": "Request a quote", "kind": "quote_intake", "primary": True},
            {"id": "apostille", "label": "Document apostille", "href": "/apostille", "primary": False},
        ],
    },
    "woodcraft": {
        "slug": "woodcraft",
        "name": "WoodCraft",
        "tagline": "Custom wood furniture and built-ins",
        "blurb": "Tables, cabinets, and built-ins made to the room — not pulled from a showroom floor.",
        "business_unit": "woodcraft",
        "accent": "#8b5a2b",
        "services": ["Custom tables", "Cabinets", "Built-ins", "Repairs"],
        "links": [
            {"id": "quote", "label": "Request a quote", "kind": "quote_intake", "primary": True},
        ],
    },
    "apostapp": {
        "slug": "apostapp",
        "name": "ApostApp",
        "tagline": "Apostille & document legalization support",
        "blurb": "Prepare, submit, and track apostille requests for DC, MD, VA, and federal documents.",
        "business_unit": "empire_saas",
        "accent": "#0ea5e9",
        "services": ["State apostille", "Federal apostille", "Notarization support", "Status tracking"],
        "links": [
            {"id": "quote", "label": "Ask about a document", "kind": "quote_intake", "primary": True},
            {"id": "order", "label": "Start an apostille order", "href": "/apostille", "primary": False},
            {"id": "status", "label": "Track an order", "href": "/apostille/status", "primary": False},
        ],
    },
    "empirebox": {
        "slug": "empirebox",
        "name": "EmpireBox",
        "tagline": "The operating system for the shop",
        "blurb": "Quotes, production, apostille, and follow-up in one place. Start with a project brief.",
        "business_unit": "empire_saas",
        "accent": "#1a1a1a",
        "services": ["Quotes", "Production", "Apostille", "Lead follow-up"],
        "links": [
            {"id": "quote", "label": "Request a quote", "kind": "quote_intake", "primary": True},
            {"id": "landing", "label": "Learn more", "href": "/landing", "primary": False},
        ],
    },
}


def resolve_business(slug: str) -> Optional[dict]:
    return PUBLIC_BUSINESSES.get((slug or "").strip().lower())


def _public_view(biz: dict) -> dict:
    quote_path = f"/quote/intake?business={biz['slug']}"
    links = []
    for link in biz["links"]:
        item = dict(link)
        if item.get("kind") == "quote_intake":
            item["href"] = quote_path
        links.append(item)
    return {
        "slug": biz["slug"],
        "name": biz["name"],
        "tagline": biz["tagline"],
        "blurb": biz["blurb"],
        "business_unit": biz["business_unit"],
        "accent": biz["accent"],
        "services": biz["services"],
        "quote_intake_path": quote_path,
        "links": links,
    }


@router.get("")
@router.get("/")
async def list_bios():
    """Public catalog. No PII, no private business.json."""
    return {
        "businesses": [_public_view(b) for b in PUBLIC_BUSINESSES.values()],
        "source": "public_catalog",
        "reads_business_json": False,
    }


@router.get("/{slug}")
async def get_bio(slug: str):
    biz = resolve_business(slug)
    if biz is None:
        raise HTTPException(status_code=404, detail="Business page not found")
    return _public_view(biz)
