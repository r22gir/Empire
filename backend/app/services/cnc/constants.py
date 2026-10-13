"""X-Carve machine and shop defaults. Sizes live as integer sixteenths."""
from __future__ import annotations

from app.services.cnc.inches import parse_inches

# Inventables X-Carve usable width. Length is unlimited via tiling.
XCARVE_MAX_WIDTH = parse_inches("29 1/2")
XCARVE_TILE_LENGTH = parse_inches("29 1/2")

# Default 1/8" router / saw kerf.
DEFAULT_KERF = parse_inches("1/8")

# Registration marks on tiled long panels.
REG_MARK_SIZE = parse_inches("1/2")
REG_MARK_INSET = parse_inches("1")

# Default ripped plywood strip the X-Carve can actually cut.
DEFAULT_SHEET_WIDTH = XCARVE_MAX_WIDTH
DEFAULT_SHEET_LENGTH = parse_inches("96")

# Foam sheets (same part size as wood; sheet stock differs).
DEFAULT_FOAM_SHEET_WIDTH = parse_inches("24")
DEFAULT_FOAM_SHEET_LENGTH = parse_inches("72")

# Fabric is a separate labeled cut, nested on a roll.
DEFAULT_FABRIC_USABLE_WIDTH = parse_inches("53")

MACHINE_NAME = "X-Carve"
