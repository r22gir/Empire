"""House catalog for the designer selection board.

Read-only seed data. Prices are studio list rates used to compose a
preview estimate — they are never written into live quotes from this module.
"""

from __future__ import annotations

FABRICS = [
    {
        "id": "fab-belgian-flax",
        "kind": "fabric",
        "name": "Belgian Flax",
        "house": "Liberty Atelier",
        "color": "Warm flax",
        "material": "Linen",
        "width_in": 54,
        "repeat_in": 0,
        "price_per_yard": 86,
        "swatch": "linear-gradient(135deg,#d8c4a4 0%,#c4aa82 42%,#b89a6e 100%)",
        "texture": "slub",
        "notes": "Dry hand, beautiful drape for unlined panels.",
    },
    {
        "id": "fab-silk-taffeta",
        "kind": "fabric",
        "name": "Champagne Taffeta",
        "house": "Maison Vérone",
        "color": "Pale champagne",
        "material": "Silk",
        "width_in": 54,
        "repeat_in": 0,
        "price_per_yard": 164,
        "swatch": "linear-gradient(120deg,#f4e6c8 0%,#e8d2a0 50%,#d4b56a 100%)",
        "texture": "crisp",
        "notes": "Light-catching face. Pair with blackout interlining.",
    },
    {
        "id": "fab-mohair-velvet",
        "kind": "fabric",
        "name": "Midnight Mohair",
        "house": "Atelier Noir",
        "color": "Deep ink",
        "material": "Mohair velvet",
        "width_in": 55,
        "repeat_in": 0,
        "price_per_yard": 248,
        "swatch": "linear-gradient(160deg,#1a1d27 0%,#2a2438 55%,#3d3354 100%)",
        "texture": "plush",
        "notes": "Upholstery grade. Directional pile — add 15% waste.",
    },
    {
        "id": "fab-wool-boucle",
        "kind": "fabric",
        "name": "Cloud Bouclé",
        "house": "Nordic Weave",
        "color": "Ivory mist",
        "material": "Wool bouclé",
        "width_in": 54,
        "repeat_in": 0,
        "price_per_yard": 132,
        "swatch": "linear-gradient(145deg,#f4efe8 0%,#e6ddd0 48%,#d2c6b4 100%)",
        "texture": "nubby",
        "notes": "Soft lounge seating. Specify performance backing.",
    },
    {
        "id": "fab-printed-botanical",
        "kind": "fabric",
        "name": "Orangerie Botanical",
        "house": "Côte & Grove",
        "color": "Sage on cream",
        "material": "Cotton-linen print",
        "width_in": 54,
        "repeat_in": 27,
        "price_per_yard": 118,
        "swatch": "linear-gradient(180deg,#e8ead8 0%,#c5c9a4 40%,#8a9a6a 100%)",
        "texture": "print",
        "notes": "Railroad for wide roman shades. Match half-drop.",
    },
    {
        "id": "fab-performance-oyster",
        "kind": "fabric",
        "name": "Oyster Performance",
        "house": "Studio Endure",
        "color": "Oyster",
        "material": "Solution-dyed acrylic",
        "width_in": 54,
        "repeat_in": 0,
        "price_per_yard": 74,
        "swatch": "linear-gradient(135deg,#efe8dc 0%,#ddd4c4 55%,#c9bfae 100%)",
        "texture": "tight",
        "notes": "Indoor-outdoor. Ideal for banquettes and high-traffic seats.",
    },
]

FINISHES = [
    {
        "id": "fin-brass-antique",
        "kind": "finish",
        "name": "Antique Brass Nailhead",
        "family": "Hardware",
        "color": "Warm brass",
        "price": 86,
        "unit": "run",
        "swatch": "linear-gradient(90deg,#8a6a2f,#d4a017,#6b4e16)",
        "notes": "Close-set #9 heads along the apron.",
    },
    {
        "id": "fin-nickel-polished",
        "kind": "finish",
        "name": "Polished Nickel",
        "family": "Hardware",
        "color": "Cool silver",
        "price": 74,
        "unit": "run",
        "swatch": "linear-gradient(90deg,#9aa3ad,#e8eef4,#6d7680)",
        "notes": "Rods, rings, and holdbacks as a set.",
    },
    {
        "id": "fin-walnut-handrub",
        "kind": "finish",
        "name": "Hand-Rubbed Walnut",
        "family": "Wood",
        "color": "Deep walnut",
        "price": 220,
        "unit": "item",
        "swatch": "linear-gradient(160deg,#3b2414,#6b3e22,#2a160c)",
        "notes": "Frame stain plus satin conversion varnish.",
    },
    {
        "id": "fin-welting-self",
        "kind": "finish",
        "name": "Self-Welting",
        "family": "Upholstery",
        "color": "Match fabric",
        "price": 48,
        "unit": "item",
        "swatch": "linear-gradient(90deg,#cfc6b8,#eee8de,#b8ae9e)",
        "notes": "Double-welt on seat and back seams.",
    },
    {
        "id": "fin-interline-blackout",
        "kind": "finish",
        "name": "Blackout Interlining",
        "family": "Drapery",
        "color": "Ivory bump",
        "price": 36,
        "unit": "yard",
        "swatch": "linear-gradient(180deg,#f7f4ee,#e8e2d6)",
        "notes": "Bump + blackout. Quoted per finished width.",
    },
    {
        "id": "fin-contrast-band",
        "kind": "finish",
        "name": "Contrast Leading Edge",
        "family": "Drapery",
        "color": "Custom",
        "price": 62,
        "unit": "pair",
        "swatch": "linear-gradient(90deg,#1f2933 0 28%,#f3efe6 28% 100%)",
        "notes": "3-inch band, mitered corners.",
    },
]

PHOTOS = [
    {
        "id": "pho-drawing-room",
        "kind": "photo",
        "name": "Drawing room, late light",
        "room": "Living",
        "mood": "Quiet evening",
        "swatch": "linear-gradient(160deg,#2c241c 0%,#6a5340 38%,#c9b089 100%)",
        "notes": "Full-length panels, puddle break, antique brass rod.",
    },
    {
        "id": "pho-banquette",
        "kind": "photo",
        "name": "Banquette corner",
        "room": "Dining",
        "mood": "Gathered",
        "swatch": "linear-gradient(145deg,#1c1916 0%,#4a3b32 45%,#d7c4a3 100%)",
        "notes": "Tight seat, buttonless back, walnut plinth.",
    },
    {
        "id": "pho-bedroom-shade",
        "kind": "photo",
        "name": "Primary bedroom roman",
        "room": "Bedroom",
        "mood": "Soft morning",
        "swatch": "linear-gradient(180deg,#efe7d6 0%,#c9b8a0 55%,#8f7a62 100%)",
        "notes": "Flat roman, hidden headrail, blackout.",
    },
    {
        "id": "pho-library",
        "kind": "photo",
        "name": "Library club chairs",
        "room": "Library",
        "mood": "Study",
        "swatch": "linear-gradient(150deg,#14161c 0%,#2e3340 50%,#8a7a5c 100%)",
        "notes": "Mohair pair, nailhead, tight seat.",
    },
]


def catalog_bundle() -> dict:
    return {
        "fabrics": list(FABRICS),
        "finishes": list(FINISHES),
        "photos": list(PHOTOS),
        "read_only": True,
        "wrote_live": False,
    }


def item_by_id(item_id: str) -> dict | None:
    for row in (*FABRICS, *FINISHES, *PHOTOS):
        if row["id"] == item_id:
            return dict(row)
    return None
