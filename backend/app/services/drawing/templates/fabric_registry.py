"""templates/fabric_registry.py — Fabric → color/motif registry.

HOTFIX B2d (2026-07-25) — DATA module, not DB. The B2d directive
("FABRIC ZONES RENDERED — color + stylized motif from fabric
registry; 'TBC — CONFIRM BEFORE CUT' when absent") requires the
renderer to look up a fabric's visual identity at render time.

Per founder directive:
  - Registry is a Python data module, ADDITIVE — new fabrics land
    in `_REGISTRY` below. Renderer logic contains no fabric-
    specific hardcoding.
  - Each Fabric record carries: name, mill, base_color_hex
    (the dominant tone that fills the fabric zone), pattern_class,
    width_in, repeat_in (vertical repeat for pattern alignment).
  - pattern_class ∈ {floral, geometric, solid, texture, stripe}.
    The renderer maps each pattern_class → stylized motif marks:
      floral    → leaf + blossom shapes (GP&J Baker Nympheus
                  treatment — the Willard reference shows the
                  velvet in solid fill; this is the B2d upgrade
                  to render the floral motif)
      geometric → diamond grid
      stripe    → vertical bands
      texture   → stipple (small dots; e.g. Charlotte Fabrics R357
                  Natural oatmeal)
      solid     → flat fill (no motif)
  - Unknown SKU at render time → neutral fill + the text
    "FABRIC: TBC — CONFIRM BEFORE CUT" inside the fabric zone
    AND a row in NOTES / ASSUMPTIONS.

Seed (B2d): fabrics we know.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from reportlab.lib import colors as _rl_colors


# ── Pattern classes ────────────────────────────────────────────────

PATTERN_FLORAL = "floral"
PATTERN_GEOMETRIC = "geometric"
PATTERN_SOLID = "solid"
PATTERN_TEXTURE = "texture"
PATTERN_STRIPE = "stripe"

VALID_PATTERN_CLASSES: frozenset[str] = frozenset({
    PATTERN_FLORAL,
    PATTERN_GEOMETRIC,
    PATTERN_SOLID,
    PATTERN_TEXTURE,
    PATTERN_STRIPE,
})


# ── Fabric record ─────────────────────────────────────────────────


@dataclass(frozen=True)
class Fabric:
    sku: str
    name: str
    mill: str
    base_color_hex: str     # "#rrggbb" — fills the fabric zone
    pattern_class: str      # one of VALID_PATTERN_CLASSES
    width_in: float
    repeat_in: Optional[float] = None   # None = no vertical repeat


# ── Seed data (additive — new fabrics land here) ─────────────────


_REGISTRY: Dict[str, Fabric] = {
    "BP10814-2": Fabric(
        sku="BP10814-2",
        name="Nympheus Velvet Emerald",
        mill="GP&J Baker",
        base_color_hex="#123a2a",       # deep emerald green
        pattern_class=PATTERN_FLORAL,
        width_in=54.0,
        repeat_in=35.46,                # vertical repeat (in)
    ),
    "SVI001": Fabric(
        sku="SVI001",
        name="Vintage Ale",
        mill="Keyston Bros",
        base_color_hex="#8b5a2b",       # saddle brown
        pattern_class=PATTERN_SOLID,
        width_in=54.0,
        repeat_in=None,
    ),
    "R357": Fabric(
        sku="R357",
        name="Natural",
        mill="Charlotte Fabrics",
        base_color_hex="#d4c9a8",       # oatmeal
        pattern_class=PATTERN_TEXTURE,
        width_in=54.0,
        repeat_in=None,
    ),
    "D3967": Fabric(
        sku="D3967",
        name="Pigeon",
        mill="—",
        base_color_hex="#9aa0a3",       # warm grey
        pattern_class=PATTERN_SOLID,
        width_in=54.0,
        repeat_in=None,
    ),
    "5937": Fabric(
        sku="5937",
        name="Oxford",
        mill="—",
        base_color_hex="#3a4a5c",       # oxford navy
        pattern_class=PATTERN_SOLID,
        width_in=54.0,
        repeat_in=None,
    ),
}


# ── Public API ────────────────────────────────────────────────────


def get_fabric(sku: Optional[str]) -> Optional[Fabric]:
    """Look up a fabric by SKU. Returns None if unset or unknown."""
    if not sku:
        return None
    return _REGISTRY.get(str(sku).strip())


def is_known(sku: Optional[str]) -> bool:
    """True iff the SKU is in the registry."""
    return get_fabric(sku) is not None


def known_skus() -> List[str]:
    """Sorted list of known SKUs (for diagnostics / dropdowns)."""
    return sorted(_REGISTRY.keys())


def fallback_label() -> str:
    """The literal text to print when fabric is missing or unknown —
    both inside the fabric zone and as a NOTES / ASSUMPTIONS row."""
    return "FABRIC: TBC — CONFIRM BEFORE CUT"


# ── Color helpers (used by renderer for motif marks) ──────────────


def hex_to_color(hex_color: str):
    """Parse "#rrggbb" (or "#rgb") into a ReportLab Color.

    Centralised so the renderer never re-implements hex parsing.
    """
    s = hex_color.strip()
    if s.startswith("#"):
        s = s[1:]
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        # Fall back to neutral if the registry has a bad entry
        return _rl_colors.HexColor("#cccccc")
    return _rl_colors.HexColor("#" + s)


def darken(hex_color: str, factor: float):
    """Return a ReportLab Color that's `factor` (0..1) darker than
    the input. Used for motif marks so they read against the
    fabric base color without competing with it.

    factor=0.15 is the typical Empire letterhead motif weight
    (subtle but legible on cream paper).
    """
    s = hex_color.strip()
    if s.startswith("#"):
        s = s[1:]
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if len(s) != 6:
        return _rl_colors.HexColor("#888888")
    r = int(s[0:2], 16)
    g = int(s[2:4], 16)
    b = int(s[4:6], 16)
    f = max(0.0, min(1.0, factor))
    r = max(0, int(round(r * (1 - f))))
    g = max(0, int(round(g * (1 - f))))
    b = max(0, int(round(b * (1 - f))))
    return _rl_colors.HexColor(f"#{r:02x}{g:02x}{b:02x}")