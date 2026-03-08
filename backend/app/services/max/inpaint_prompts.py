"""
Inpainting & mockup prompt library for Empire quote system.

Every treatment type x 3 tiers x style variants.
Used by inpaint_service.py for Stability AI inpainting and Grok clean mockups.
"""

# ── Style modifiers ──────────────────────────────────────────────────

STYLE_MODIFIERS = {
    "farmhouse": "rustic farmhouse aesthetic, warm wood tones, natural textiles, shiplap and reclaimed wood accents, cozy country feel",
    "mid-century-modern": "mid-century modern style, clean geometric lines, tapered legs, organic curves, walnut and teak tones, minimal ornamentation",
    "traditional": "traditional classic style, ornate details, rich wood furniture, symmetrical layout, crown molding, elegant and formal",
    "contemporary": "contemporary modern style, neutral palette, sleek surfaces, minimal decoration, open and airy feel",
    "coastal": "coastal beach style, light blues and whites, natural fiber textures, weathered wood, relaxed airy feel",
    "industrial": "industrial loft style, exposed brick, metal accents, raw materials, Edison bulbs, urban warehouse feel",
    "bohemian": "bohemian eclectic style, layered textiles, rich colors, mixed patterns, plants, globally inspired decor",
    "transitional": "transitional style, blend of traditional and contemporary, neutral tones, clean lines with subtle ornamentation",
    "scandinavian": "Scandinavian minimalist style, white walls, light wood, clean lines, hygge warmth, functional simplicity",
    "art-deco": "art deco glamour, bold geometric patterns, rich jewel tones, brass and gold accents, luxurious materials",
    "": "professional interior, clean and well-lit, Architectural Digest quality",
}


# ── Negative prompts per treatment ───────────────────────────────────

NEGATIVE_PROMPTS = {
    "roman-shade": "NO curtain rod, NO rings, NO drapery hardware, NO grommets, NO pinch pleats, NO blinds, NO traverse rod",
    "ripplefold": "NO roman shade, NO roller shade, NO blinds, NO valance, NO rings, NO grommets",
    "pinch-pleat": "NO ripplefold, NO roman shade, NO grommets, NO casual drape, NO roller shade",
    "grommet": "NO pinch pleat, NO roman shade, NO roller shade, NO ripplefold track",
    "rod-pocket": "NO rings, NO grommets, NO roman shade, NO track, NO ripplefold",
    "roller-shade": "NO curtain rod, NO fabric drape, NO rings, NO roman shade, NO drapery panels",
}


# ── Window treatment inpainting prompts (for customer photo) ─────────
# {color} and {style_modifier} are filled at runtime

WINDOW_INPAINT_PROMPTS = {
    "roman-shade": {
        "A": (
            "Simple flat roman shade with clean horizontal folds, {color} solid cotton fabric, "
            "basic white cassette headrail, inside mount, clean minimal look, "
            "natural lighting, photorealistic, {style_modifier}"
        ),
        "B": (
            "Textured linen roman shade with elegant horizontal folds, {color} woven fabric "
            "with subtle pattern, decorative cassette headrail, inside mount, "
            "professional quality, photorealistic, {style_modifier}"
        ),
        "C": (
            "Luxury damask roman shade, {color} heavy silk fabric with rich texture, "
            "ornate gilded cassette headrail, blackout lined, inside mount, "
            "opulent and refined, photorealistic, {style_modifier}"
        ),
    },
    "ripplefold": {
        "A": (
            "Basic ripplefold drapery panels, {color} polyester blend fabric, "
            "simple ceiling-mounted track, evenly spaced S-curve folds, clean look, "
            "natural lighting, photorealistic, {style_modifier}"
        ),
        "B": (
            "Designer ripplefold panels, {color} textured linen fabric, "
            "brushed nickel ceiling track, elegant continuous wave pattern, "
            "layered and sophisticated, photorealistic, {style_modifier}"
        ),
        "C": (
            "Premium floor-to-ceiling ripplefold panels, {color} Italian velvet fabric, "
            "motorized track with silent operation, luxurious deep S-curve folds, "
            "opulent drape pooling slightly on floor, photorealistic, {style_modifier}"
        ),
    },
    "pinch-pleat": {
        "A": (
            "Simple pinch pleat drapery panels, {color} cotton fabric, "
            "basic decorative rod with simple finials, classic gathered pleats, "
            "clean traditional look, photorealistic, {style_modifier}"
        ),
        "B": (
            "Designer pinch pleat panels, {color} textured jacquard fabric, "
            "ornamental rod with decorative rings, deep triple pinch pleats, "
            "full and elegant drape, photorealistic, {style_modifier}"
        ),
        "C": (
            "Luxury pinch pleat drapery, {color} silk dupioni fabric with sheen, "
            "hand-forged iron rod with crystal finials, goblet pleats, "
            "contrast lining reveal, floor-length with break, photorealistic, {style_modifier}"
        ),
    },
    "grommet": {
        "A": (
            "Simple grommet top curtain panels, {color} cotton blend fabric, "
            "basic metal rod, evenly spaced brushed nickel grommets, "
            "clean modern folds, photorealistic, {style_modifier}"
        ),
        "B": (
            "Designer grommet panels, {color} textured linen fabric, "
            "decorative rod with ball finials, matte black grommets, "
            "uniform wave-like folds, photorealistic, {style_modifier}"
        ),
        "C": (
            "Premium grommet drapery, {color} heavy velvet fabric, "
            "oversized decorative rod with ornate finials, antique brass grommets, "
            "deep luxurious folds with thermal lining, photorealistic, {style_modifier}"
        ),
    },
    "rod-pocket": {
        "A": (
            "Simple rod pocket curtains, {color} lightweight cotton fabric, "
            "basic decorative rod, soft gathered header, "
            "casual airy look, photorealistic, {style_modifier}"
        ),
        "B": (
            "Designer rod pocket panels, {color} linen blend fabric, "
            "turned wood rod with carved finials, ruffled header detail, "
            "full romantic drape, photorealistic, {style_modifier}"
        ),
        "C": (
            "Luxury rod pocket curtains, {color} silk taffeta fabric, "
            "gilded rod with crystal finials, generous ruffle header, "
            "floor-length with puddle, sheer under-layer, photorealistic, {style_modifier}"
        ),
    },
    "roller-shade": {
        "A": (
            "Clean roller shade, {color} light-filtering fabric, "
            "slim white cassette housing, smooth flat material, "
            "minimal modern look, photorealistic, {style_modifier}"
        ),
        "B": (
            "Designer roller shade, {color} textured solar screen fabric, "
            "decorative cassette with fascia, chain-pull mechanism, "
            "sleek contemporary look, photorealistic, {style_modifier}"
        ),
        "C": (
            "Premium motorized roller shade, {color} blackout fabric with woven texture, "
            "concealed cassette in matching ceiling pocket, "
            "ultra-clean lines with hidden mechanism, photorealistic, {style_modifier}"
        ),
    },
}


# ── Clean mockup prompts (aspirational, NOT customer photo) ──────────

WINDOW_CLEAN_PROMPTS = {
    "roman-shade": {
        "A": (
            "Professional interior design photo of a beautiful room with {color} flat roman shade "
            "on window, basic cassette headrail, clean minimal design, "
            "bright natural light, magazine quality, {style_modifier}"
        ),
        "B": (
            "High-end interior design photo, elegant {color} textured linen roman shade "
            "with decorative cassette, soft horizontal folds, "
            "warm natural light, Architectural Digest quality, {style_modifier}"
        ),
        "C": (
            "Luxury showroom photo, premium {color} silk roman shade with ornate details, "
            "gilded cassette headrail, blackout lined, rich layered window treatment, "
            "editorial photography quality, {style_modifier}"
        ),
    },
    "ripplefold": {
        "A": (
            "Professional interior photo, {color} ripplefold drapery on ceiling track, "
            "simple S-curve folds, clean modern room, "
            "bright natural light, magazine quality, {style_modifier}"
        ),
        "B": (
            "High-end interior photo, {color} linen ripplefold panels on brushed nickel track, "
            "elegant wave pattern, layered with sheers, "
            "Architectural Digest quality, {style_modifier}"
        ),
        "C": (
            "Luxury editorial photo, floor-to-ceiling {color} velvet ripplefold panels, "
            "motorized track, deep dramatic folds, "
            "opulent living space, editorial photography, {style_modifier}"
        ),
    },
    "pinch-pleat": {
        "A": (
            "Professional interior photo, {color} pinch pleat curtains on simple rod, "
            "classic gathered pleats, traditional room, "
            "bright natural light, magazine quality, {style_modifier}"
        ),
        "B": (
            "High-end interior photo, {color} jacquard pinch pleat panels, "
            "decorative rod with rings, deep triple pleats, "
            "elegant traditional room, Architectural Digest quality, {style_modifier}"
        ),
        "C": (
            "Luxury editorial photo, {color} silk pinch pleat drapery with goblet pleats, "
            "hand-forged iron rod with crystal finials, contrast lining, "
            "grand formal room, editorial photography, {style_modifier}"
        ),
    },
    "grommet": {
        "A": (
            "Professional interior photo, {color} grommet curtain panels, "
            "basic metal rod, clean modern folds, bright contemporary room, "
            "magazine quality, {style_modifier}"
        ),
        "B": (
            "High-end interior photo, {color} linen grommet panels, "
            "decorative rod with finials, uniform wave folds, "
            "stylish modern room, Architectural Digest quality, {style_modifier}"
        ),
        "C": (
            "Luxury editorial photo, {color} heavy velvet grommet drapery, "
            "oversized decorative rod, deep luxurious folds, "
            "dramatic modern interior, editorial photography, {style_modifier}"
        ),
    },
    "rod-pocket": {
        "A": (
            "Professional interior photo, {color} rod pocket curtains, "
            "simple decorative rod, soft gathered header, airy casual room, "
            "magazine quality, {style_modifier}"
        ),
        "B": (
            "High-end interior photo, {color} linen rod pocket panels, "
            "turned wood rod, romantic ruffled header, "
            "charming traditional room, Architectural Digest quality, {style_modifier}"
        ),
        "C": (
            "Luxury editorial photo, {color} silk taffeta rod pocket curtains, "
            "gilded rod with crystal finials, generous ruffle, floor puddle, "
            "grand feminine interior, editorial photography, {style_modifier}"
        ),
    },
    "roller-shade": {
        "A": (
            "Professional interior photo, {color} roller shade in modern room, "
            "slim cassette, clean minimal lines, bright contemporary space, "
            "magazine quality, {style_modifier}"
        ),
        "B": (
            "High-end interior photo, {color} solar screen roller shade, "
            "decorative cassette fascia, sleek contemporary room, "
            "Architectural Digest quality, {style_modifier}"
        ),
        "C": (
            "Luxury editorial photo, {color} motorized blackout roller shade, "
            "concealed cassette in ceiling pocket, ultra-clean minimalist room, "
            "editorial photography, {style_modifier}"
        ),
    },
}


# ── Upholstery inpainting prompts (for customer photo) ───────────────
# {furniture_type}, {color}, {details}, {style_modifier} filled at runtime

UPHOLSTERY_INPAINT_PROMPTS = {
    "A": (
        "Reupholstered {furniture_type} in {color} solid cotton fabric, "
        "clean simple lines, {details}, fresh new fabric, photorealistic, {style_modifier}"
    ),
    "B": (
        "Reupholstered {furniture_type} in {color} textured linen fabric, "
        "{details}, professional quality craftsmanship, photorealistic, {style_modifier}"
    ),
    "C": (
        "Reupholstered {furniture_type} in {color} premium velvet fabric, "
        "{details}, luxury showroom quality, rich texture and sheen, photorealistic, {style_modifier}"
    ),
}


# ── Upholstery clean mockup prompts (aspirational) ──────────────────

UPHOLSTERY_CLEAN_PROMPTS = {
    "A": (
        "Professional furniture photo, {furniture_type} reupholstered in {color} cotton fabric, "
        "{details}, clean studio setting, bright even lighting, catalog quality, {style_modifier}"
    ),
    "B": (
        "High-end furniture photo, {furniture_type} in {color} textured linen, "
        "{details}, styled interior setting, Architectural Digest quality, {style_modifier}"
    ),
    "C": (
        "Luxury editorial furniture photo, {furniture_type} in {color} premium velvet, "
        "{details}, grand interior setting, editorial photography, rich and opulent, {style_modifier}"
    ),
}


# ── Helper: build prompt from templates ──────────────────────────────

def build_window_inpaint_prompt(
    treatment: str, tier: str, color: str, style: str = ""
) -> str:
    """Build inpainting prompt for a window treatment."""
    templates = WINDOW_INPAINT_PROMPTS.get(treatment, WINDOW_INPAINT_PROMPTS["ripplefold"])
    template = templates.get(tier, templates["B"])
    style_mod = STYLE_MODIFIERS.get(style, STYLE_MODIFIERS[""])
    color = color or "neutral"
    return template.format(color=color, style_modifier=style_mod)


def build_window_clean_prompt(
    treatment: str, tier: str, color: str, style: str = ""
) -> str:
    """Build clean mockup prompt for a window treatment."""
    templates = WINDOW_CLEAN_PROMPTS.get(treatment, WINDOW_CLEAN_PROMPTS["ripplefold"])
    template = templates.get(tier, templates["B"])
    style_mod = STYLE_MODIFIERS.get(style, STYLE_MODIFIERS[""])
    color = color or "neutral"
    return template.format(color=color, style_modifier=style_mod)


def build_upholstery_inpaint_prompt(
    furniture_type: str, tier: str, color: str, details: str = "", style: str = ""
) -> str:
    """Build inpainting prompt for furniture upholstery."""
    template = UPHOLSTERY_INPAINT_PROMPTS.get(tier, UPHOLSTERY_INPAINT_PROMPTS["B"])
    style_mod = STYLE_MODIFIERS.get(style, STYLE_MODIFIERS[""])
    color = color or "neutral"
    furniture_type = furniture_type or "sofa"
    details = details or "standard cushions"
    return template.format(
        furniture_type=furniture_type, color=color,
        details=details, style_modifier=style_mod,
    )


def build_upholstery_clean_prompt(
    furniture_type: str, tier: str, color: str, details: str = "", style: str = ""
) -> str:
    """Build clean mockup prompt for furniture."""
    template = UPHOLSTERY_CLEAN_PROMPTS.get(tier, UPHOLSTERY_CLEAN_PROMPTS["B"])
    style_mod = STYLE_MODIFIERS.get(style, STYLE_MODIFIERS[""])
    color = color or "neutral"
    furniture_type = furniture_type or "sofa"
    details = details or "standard cushions"
    return template.format(
        furniture_type=furniture_type, color=color,
        details=details, style_modifier=style_mod,
    )


def get_negative_prompt(treatment: str) -> str:
    """Get negative prompt for a treatment type."""
    return NEGATIVE_PROMPTS.get(treatment, "")


def build_upholstery_details(ai_analysis: dict) -> str:
    """Build details string from AI upholstery analysis."""
    parts = []
    if ai_analysis.get("has_tufting"):
        parts.append("diamond tufting")
    if ai_analysis.get("has_welting"):
        parts.append("contrast welting")
    if ai_analysis.get("has_channeling"):
        parts.append("channel back")
    if ai_analysis.get("has_nailhead"):
        parts.append("decorative nailhead trim")
    if ai_analysis.get("has_skirt"):
        parts.append("tailored skirt")
    cushions = ai_analysis.get("cushion_count", {})
    seat = cushions.get("seat", 0)
    if seat:
        parts.append(f"{seat} seat cushions")
    return ", ".join(parts) if parts else "standard cushions"
