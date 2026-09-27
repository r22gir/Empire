"""catalog_namespace.py — (family, style) resolution for Max diagram templates.

Quote diagrams are category templates plus parametric dims. Catalog styles
share slugs across families (`box_pleat` is both drapery and a valance;
`arched` is both a valance and a cornice). The B1 registry is a flat
product_type map, so a bare slug keeps its historical winner. Callers that
know the catalog family must pass family and style (or a `family/style`
catalog id) so the collision hits the right template.

Alias bridge (one table, used by quote lines and `render_shop_drawing`):

  catalog roman `flat_fold`  ↔ vision `flat_roman`
  catalog drapery `pinch_pleat` ↔ quote-builder `pinch-pleat`
  catalog `headboard` + style ↔ Max `headboard_channel` (style kept)

How to call
-----------
Pass both pieces. Either form is enough:

    {"family": "valance", "style": "box_pleat", "dims": {"width": 60, "drop": 14}}
    {"product_type": "valances/box_pleat", "dims": {"width": 60, "drop": 14}}
    {"product_type": "cornices/arched", "dims": {"width": 72, "depth": 6, "drop": 12}}
    {"product_type": "flat_roman", "dims": {"width": 38, "height": 64}}
    {"family": "headboard", "style": "wingback", "dims": {"width": 60, "height": 54}}

Bare colliding slugs stay on the historical B1 winner (`box_pleat` →
drapery, `balloon` → roman, `arched` → valance). Do not use the flat
`MEASUREMENT_REQUIREMENTS` dict for those slugs; use
`resolve_catalog_style(...).required_dims`.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.data.product_catalog import DRAPERY_STYLES, FURNITURE_STYLES
from app.services.drawing.templates.base import FamilyTemplate
from app.services.drawing.templates.bench_curved import BenchCurvedTemplate
from app.services.drawing.templates.cornice import CorniceTemplate
from app.services.drawing.templates.drapery import DraperyTemplate
from app.services.drawing.templates.headboard_channel import (
    HeadboardChannelTemplate,
)
from app.services.drawing.templates.roman import RomanTemplate
from app.services.drawing.templates.valance import ValanceTemplate


# Catalog family slug → template class. Bench and banquette share one sheet.
_TEMPLATE_CLASS: dict[str, type[FamilyTemplate]] = {
    "drapery": DraperyTemplate,
    "roman": RomanTemplate,
    "valance": ValanceTemplate,
    "cornice": CorniceTemplate,
    "bench": BenchCurvedTemplate,
    "banquette": BenchCurvedTemplate,
    "headboard": HeadboardChannelTemplate,
}

_TEMPLATE_FAMILY_NAME: dict[str, str] = {
    "drapery": "Drapery",
    "roman": "Roman Shades",
    "valance": "Valance",
    "cornice": "Cornice",
    "bench": "Bench / Banquette",
    "banquette": "Bench / Banquette",
    "headboard": "Channel Headboard",
}

_REQUIRED_DIMS: dict[str, tuple[str, ...]] = {
    "drapery": ("width", "height"),
    "roman": ("width", "height"),
    "valance": ("width", "drop"),
    "cornice": ("width", "depth", "drop"),
    "bench": ("width", "height", "depth"),
    "banquette": ("width", "height", "depth"),
    "headboard": ("width", "height"),
}

_OPTIONAL_DIMS: dict[str, tuple[str, ...]] = {
    "drapery": ("returns", "stacking"),
    "roman": ("mounting_depth",),
    "valance": ("returns",),
    "cornice": ("returns",),
    "bench": ("seat_height", "arm_height", "curve_radius"),
    "banquette": ("seat_height", "arm_height", "curve_radius"),
    "headboard": ("thickness", "channels"),
}

# Catalog subcategory lists. Keys are the canonical family slugs callers pass.
_CATALOG_STYLES: dict[str, frozenset[str]] = {
    "drapery": frozenset(DRAPERY_STYLES["drapery"]),
    "roman": frozenset(DRAPERY_STYLES["roman_shade"]),
    "valance": frozenset(DRAPERY_STYLES["valance"]),
    "cornice": frozenset(DRAPERY_STYLES["cornice"]),
    "bench": frozenset({"bench"}),
    "banquette": frozenset({"banquette"}),
}

# Headboard styles are NOT in the global index. `arched` would otherwise
# collide with valance and cornice. They resolve only when family=headboard
# (or the caller said "headboard" / "headboard_channel").
_HEADBOARD_STYLES: frozenset[str] = frozenset(FURNITURE_STYLES["headboard"]) | {
    "headboard",
    "headboard_channel",
    "channel",
    "channel_tufted",
}

_FAMILY_ALIASES: dict[str, str] = {
    "drapery": "drapery",
    "roman": "roman",
    "roman_shade": "roman",
    "roman_shades": "roman",
    "romanshades": "roman",
    "valance": "valance",
    "valances": "valance",
    "cornice": "cornice",
    "cornices": "cornice",
    "bench": "bench",
    "banquette": "banquette",
    "bench_banquette": "bench",
    "headboard": "headboard",
    "headboard_channel": "headboard",
    "channel_headboard": "headboard",
}

# Quote-builder hyphens. Checked on the raw token so "rod-pocket" stays
# drapery instead of collapsing to the shared slug `rod_pocket`.
_HYPHEN_ALIAS: dict[str, tuple[str, str]] = {
    "rod-pocket": ("drapery", "rod_pocket"),
    "pinch-pleat": ("drapery", "pinch_pleat"),
    "flat-roman": ("roman", "flat_fold"),
    "roman-shade": ("roman", "flat_fold"),
}

# Vision / quote-builder token → (family, canonical catalog style).
# The token itself encodes the family, so a bare call is unambiguous.
_IMPLIED_ALIAS: dict[str, tuple[str, str]] = {
    # Roman: vision parametric slugs ↔ catalog
    "flat_roman": ("roman", "flat_fold"),
    "hobbled_roman": ("roman", "hobbled_teardrop"),
    "relaxed_roman": ("roman", "european_relaxed"),
    "balloon_roman": ("roman", "balloon"),
    "london_roman": ("roman", "london"),
    "tulip_roman": ("roman", "tulip"),
    # Quote builder coarse treatment (style not selected) → flat roman.
    "roman_shade": ("roman", "flat_fold"),
    # Drapery: vision short names and quote-builder hyphens.
    # Hyphens are normalized to underscores before lookup, so
    # "pinch-pleat" arrives here as "pinch_pleat" (already canonical).
    "goblet": ("drapery", "goblet_pleat"),
    "inverted_box": ("drapery", "inverted_box_pleat"),
    "cartridge": ("drapery", "cartridge_pleat"),
    "pencil": ("drapery", "pencil_pleat"),
    # Valance: vision window-catalog names
    "box_pleat_valance": ("valance", "box_pleat"),
    "balloon_valance": ("valance", "balloon"),
    "kingston_valance": ("valance", "kingston"),
    "rod_pocket_valance": ("valance", "rod_pocket"),
    "board_mounted_valance": ("valance", "flat_board_mounted"),
    "swag_jabot": ("valance", "swag_and_jabot"),
    "scarf_swag": ("valance", "swag_and_jabot"),
    # Cornice: vision window-catalog names
    "straight_cornice": ("cornice", "straight"),
    "arched_cornice": ("cornice", "arched"),
    "scalloped_cornice": ("cornice", "scalloped"),
    "serpentine_cornice": ("cornice", "serpentine"),
    "shaped_cornice": ("cornice", "custom_profile"),
    "upholstered_cornice": ("cornice", "straight"),
    # Headboard: catalog item → the one B1 headboard sheet.
    "headboard": ("headboard", "headboard_channel"),
    "headboard_channel": ("headboard", "headboard_channel"),
    "channel_tufted": ("headboard", "channel_tufted"),
}

# (family, token) → canonical catalog style, when the caller already
# named the family. Vision short names then stay inside that family.
_WITHIN_FAMILY_ALIAS: dict[tuple[str, str], str] = {
    ("roman", "flat_roman"): "flat_fold",
    ("roman", "hobbled_roman"): "hobbled_teardrop",
    ("roman", "relaxed_roman"): "european_relaxed",
    ("roman", "balloon_roman"): "balloon",
    ("roman", "london_roman"): "london",
    ("roman", "tulip_roman"): "tulip",
    ("drapery", "goblet"): "goblet_pleat",
    ("drapery", "inverted_box"): "inverted_box_pleat",
    ("drapery", "cartridge"): "cartridge_pleat",
    ("drapery", "pencil"): "pencil_pleat",
    ("valance", "box_pleat_valance"): "box_pleat",
    ("valance", "balloon_valance"): "balloon",
    ("valance", "inverted_box"): "inverted_box_pleat",
    ("valance", "kingston_valance"): "kingston",
    ("valance", "rod_pocket_valance"): "rod_pocket",
    ("valance", "board_mounted_valance"): "flat_board_mounted",
    ("valance", "swag_jabot"): "swag_and_jabot",
    ("valance", "scarf_swag"): "swag_and_jabot",
    ("cornice", "straight_cornice"): "straight",
    ("cornice", "arched_cornice"): "arched",
    ("cornice", "scalloped_cornice"): "scalloped",
    ("cornice", "serpentine_cornice"): "serpentine",
    ("cornice", "shaped_cornice"): "custom_profile",
    ("cornice", "upholstered_cornice"): "straight",
}

# Bare slug → historical B1 registry winner. Passing family overrides this.
_BARE_WINNER: dict[str, str] = {
    "box_pleat": "drapery",
    "inverted_box_pleat": "drapery",
    "rod_pocket": "drapery",
    "balloon": "roman",
    "austrian": "roman",
    "london": "roman",
    "arched": "valance",
    "scalloped": "valance",
    "serpentine": "valance",
}

_STYLE_OWNERS: dict[str, tuple[str, ...]] = {}
for _fam, _styles in _CATALOG_STYLES.items():
    for _style in _styles:
        _STYLE_OWNERS.setdefault(_style, ())
        if _fam not in _STYLE_OWNERS[_style]:
            _STYLE_OWNERS[_style] = _STYLE_OWNERS[_style] + (_fam,)


@dataclass(frozen=True)
class ResolvedStyle:
    """One catalog style bound to the Max template that should draw it."""

    catalog_family: str
    catalog_style: str
    product_type: str
    template_family: str
    required_dims: tuple[str, ...]
    optional_dims: tuple[str, ...]
    ambiguous_bare_slug: bool = False
    alias_from: str | None = None


_INSTANCES: dict[str, FamilyTemplate] = {}


def template_instance(resolved: ResolvedStyle) -> FamilyTemplate:
    """Return the family template instance for a resolved style."""
    key = resolved.catalog_family
    inst = _INSTANCES.get(key)
    if inst is None:
        inst = _TEMPLATE_CLASS[key]()
        _INSTANCES[key] = inst
    return inst


def resolve_catalog_style(
    product_type: str | None = None,
    *,
    family: str | None = None,
    style: str | None = None,
) -> ResolvedStyle:
    """Resolve a catalog or vision name to one Max template family.

    `family` + `style`, a `family/style` catalog id, or a vision alias
    (`flat_roman`, `arched_cornice`, `pinch-pleat`, `headboard`).
    Raises KeyError when the pair is not a connected B1 category.
    """
    raw_style = style if _present(style) else product_type
    if not _present(raw_style) and not _present(family):
        raise KeyError(
            "catalog style resolution needs family+style or a product_type"
        )

    fam_hint = family
    style_raw = str(raw_style).strip() if _present(raw_style) else ""
    alias_from: str | None = None

    if _present(product_type) and "/" in str(product_type) and not _present(style):
        split_fam, split_style = _split_catalog_id(str(product_type))
        if not _present(fam_hint):
            fam_hint = split_fam
        style_raw = split_style
    elif "/" in style_raw and not _present(family):
        fam_hint, style_raw = _split_catalog_id(style_raw)

    if _present(fam_hint) and str(fam_hint).strip().lower() in {
        "upholstery", "furniture_styles",
    }:
        # upholstery/headboard and FURNITURE_STYLES/headboard/<style>
        if _norm(style_raw) in _HEADBOARD_STYLES or _norm(style_raw) == "headboard":
            fam_hint = "headboard"

    norm_style = _norm(style_raw) if style_raw else ""
    if style_raw and norm_style != style_raw.strip().lower():
        alias_from = style_raw.strip()

    canon_family = _canon_family(fam_hint) if _present(fam_hint) else None
    # "Bench / Banquette" normalizes to bench. A banquette style stays
    # on that same sheet but keeps the banquette catalog family.
    if canon_family == "bench" and norm_style == "banquette":
        canon_family = "banquette"

    if canon_family == "headboard":
        return _resolve_headboard(norm_style, alias_from)

    raw_key = style_raw.strip().lower()
    if canon_family is None and raw_key in _HYPHEN_ALIAS:
        hyphen_fam, hyphen_style = _HYPHEN_ALIAS[raw_key]
        return _pack(
            hyphen_fam, hyphen_style, alias_from=style_raw.strip(),
        )

    if canon_family:
        rewritten = _WITHIN_FAMILY_ALIAS.get((canon_family, norm_style))
        if rewritten:
            alias_from = alias_from or norm_style
            norm_style = rewritten
        elif norm_style in _IMPLIED_ALIAS:
            implied_fam, implied_style = _IMPLIED_ALIAS[norm_style]
            if implied_fam != canon_family:
                raise KeyError(
                    f"style {style_raw!r} belongs to family {implied_fam!r}, "
                    f"not {canon_family!r}"
                )
            alias_from = alias_from or norm_style
            norm_style = implied_style
        if norm_style not in _CATALOG_STYLES[canon_family]:
            raise KeyError(
                f"style {style_raw!r} is not in catalog family {canon_family!r}"
            )
        return _pack(canon_family, norm_style, alias_from=alias_from)

    if norm_style in _IMPLIED_ALIAS:
        implied_fam, implied_style = _IMPLIED_ALIAS[norm_style]
        if implied_fam == "headboard":
            return _resolve_headboard(implied_style, alias_from or norm_style)
        return _pack(implied_fam, implied_style, alias_from=alias_from or norm_style)

    owners = _STYLE_OWNERS.get(norm_style, ())
    if len(owners) == 1:
        return _pack(owners[0], norm_style, alias_from=alias_from)
    if len(owners) > 1:
        winner = _BARE_WINNER.get(norm_style)
        if winner is None:
            raise KeyError(
                f"style {style_raw!r} is shared by {owners}; pass family+style"
            )
        return _pack(
            winner, norm_style, alias_from=alias_from, ambiguous=True,
        )
    raise KeyError(
        f"style {style_raw!r} has no Max diagram category. "
        f"Pass family+style for a connected catalog item "
        f"(drapery, roman, valance, cornice, bench, banquette, headboard)."
    )


def prepare_drawing_spec(spec: dict) -> tuple[dict, ResolvedStyle]:
    """Copy `spec` with product_type rewritten to the template slug.

    Sets catalog_family, catalog_style, and family. Does not mutate
    the caller's dict. Dims are left untouched — the template still
    refuses when a required dim is missing.
    """
    resolved = resolve_catalog_style(
        spec.get("product_type"),
        family=spec.get("family") or spec.get("catalog_family"),
        style=spec.get("style") or spec.get("catalog_style"),
    )
    out = dict(spec)
    out["product_type"] = resolved.product_type
    out["catalog_family"] = resolved.catalog_family
    out["catalog_style"] = resolved.catalog_style
    out["family"] = resolved.catalog_family
    if resolved.alias_from:
        out["style_alias_from"] = resolved.alias_from
    return out, resolved


def _resolve_headboard(norm_style: str, alias_from: str | None) -> ResolvedStyle:
    style = norm_style or "headboard_channel"
    if style not in _HEADBOARD_STYLES:
        raise KeyError(
            f"style {norm_style!r} is not a headboard catalog style. "
            f"Known: {sorted(_HEADBOARD_STYLES)}"
        )
    # Furniture labels stay on the spec so the sheet can name the
    # quoted style. The only B1 sheet is headboard_channel.
    if style in {"headboard", "headboard_channel", "channel"}:
        catalog_style = "headboard_channel"
    else:
        catalog_style = style
    return _pack(
        "headboard",
        catalog_style,
        product_type="headboard_channel",
        alias_from=alias_from,
    )


def _pack(
    family: str,
    catalog_style: str,
    *,
    product_type: str | None = None,
    alias_from: str | None = None,
    ambiguous: bool = False,
) -> ResolvedStyle:
    pt = product_type or catalog_style
    if alias_from == pt or alias_from == catalog_style:
        alias_from = None
    return ResolvedStyle(
        catalog_family=family,
        catalog_style=catalog_style,
        product_type=pt,
        template_family=_TEMPLATE_FAMILY_NAME[family],
        required_dims=_REQUIRED_DIMS[family],
        optional_dims=_OPTIONAL_DIMS[family],
        ambiguous_bare_slug=ambiguous,
        alias_from=alias_from,
    )


def _canon_family(raw: str | None) -> str:
    if not _present(raw):
        raise KeyError("catalog family is empty")
    token = _norm(str(raw))
    if token not in _FAMILY_ALIASES:
        raise KeyError(
            f"unknown catalog family {raw!r}. "
            f"Use one of: drapery, roman, valance, cornice, bench, "
            f"banquette, headboard."
        )
    return _FAMILY_ALIASES[token]


def _split_catalog_id(raw: str) -> tuple[str, str]:
    parts = [p.strip() for p in raw.split("/") if p.strip()]
    if len(parts) >= 3 and _norm(parts[0]) in {
        "furniture_styles", "furnitures_styles",
    }:
        return parts[1], parts[2]
    if len(parts) >= 2:
        return parts[0], parts[-1]
    raise KeyError(f"catalog id {raw!r} is not family/style")


def _norm(token: str) -> str:
    text = token.strip().lower().replace("-", "_").replace(" ", "_")
    text = text.replace("/", "_")
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_")


def _present(value: object) -> bool:
    return value is not None and str(value).strip() != ""
