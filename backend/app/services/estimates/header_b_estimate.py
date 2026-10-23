"""Portrait estimate. Rafael 2026-10-23 Willard layout (812-C / 838 / 909).

Kept as the Max draft_estimate_and_presentation entry so existing imports
keep working. Body is the Willard renderer (client variant by default).
"""
from __future__ import annotations

from app.services.estimates.rafael_format import VARIANT_CLIENT, VARIANT_INTERNAL
from app.services.estimates.willard_estimate import render_willard_estimate


def render_header_b_estimate(packet: dict, *, variant: str = VARIANT_CLIENT) -> bytes:
    """Render the Max draft estimate. ``variant`` is client or internal."""
    return render_willard_estimate(packet, variant=variant or VARIANT_CLIENT)


def render_header_b_estimate_internal(packet: dict) -> bytes:
    return render_willard_estimate(packet, variant=VARIANT_INTERNAL)
