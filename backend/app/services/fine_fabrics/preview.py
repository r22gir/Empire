"""Hand a selected fabric to the drawing engine / mockup.

When the renderer accepts a fabric SKU the call goes through
``/drawings/generate``. Otherwise this returns a stub with a TODO so the
store button still has a contract.
"""

from __future__ import annotations

from app.services.fine_fabrics.catalog import get_product

TODO = (
    "TODO: wire selected fabric into the drawing engine/mockup when the "
    "renderer accepts a live fabric handoff (sku + color + empire_code). "
    "The store page uses client-side tiled templates in the meantime."
)

MOCKUP_ITEMS = (
    "pillow",
    "drapery_panel",
    "roman_shade",
    "sofa",
    "accent_chair",
    "bench",
)


def preview_fabric(product_id: int, *, item_type: str = "roman_shade") -> dict:
    product = get_product(product_id, owner=False, allow_hidden=False)
    if not product:
        raise LookupError(f"Product {product_id} is not for online sale")

    handoff = {
        "product_id": product["id"],
        "empire_code": product["empire_code"],
        "pattern": product["pattern"],
        "color": product["color"],
        "category": product["category"],
        "width": product["width"],
        "repeat": product["repeat"],
        "item_type": item_type,
        "mockup_items": list(MOCKUP_ITEMS),
    }

    try:
        from app.routers.drawings import UniversalDrawingRequest, _render_universal_drawing

        result = _render_universal_drawing(
            UniversalDrawingRequest(
                user_text=(
                    f"{item_type.replace('_', ' ')} mockup in "
                    f"{product['pattern']} {product['color']} {product['empire_code']}"
                ),
                params={
                    "item_type": item_type,
                    "name": f"{product['pattern']} {product['color']}",
                    "fabric_sku": product["empire_code"],
                    "fabric_name": product["pattern"],
                    "fabric_color": product["color"],
                    "description": f"Empire Fine Fabrics preview {product['empire_code']}",
                },
            )
        )
        return {
            "ok": True,
            "engine": "drawing",
            "stub": False,
            "todo": None,
            "fabric": handoff,
            "drawing": {
                "item_type": (result or {}).get("item_type") or (result or {}).get("classification", {}).get("type"),
                "classification": (result or {}).get("classification"),
                "has_svg": bool((result or {}).get("svg") or (result or {}).get("svg_text")),
            },
        }
    except Exception as exc:
        return {
            "ok": False,
            "engine": "stub",
            "stub": True,
            "todo": TODO,
            "fabric": handoff,
            "error": str(exc),
        }
