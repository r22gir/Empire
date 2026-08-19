"""spec.py — JobSpec + derived layer for the Document Template Engine.

Per EMPIRE_CLIENT_DOC_STANDARD.md Amendment 4 (COUNTS DERIVE ONCE):
every quantity appearing in more than one place is computed once and
read everywhere. Cover index, schedule totals, per-sheet counts all
read from `count_openings(spec)`.

Per P1-T·b founder ruling (2026-08-19):
- chrome() takes TWO distinct fields — `header_tagline` and
  `footer_letterhead` — with the address in `footer_letterhead` only.
  (POWERED BY EMPIRE WORKROOM appearing in both was the ambiguity;
  the split resolves it.)
- Address components (`address_street`, `address_city`,
  `address_state`, `address_zip`) live in the spec — never typed
  twice. The footer formats them once.

Per Amendment 7 (PHOTOS per-job upload): photos are NOT in the spec.
The intake path (photos.py) loads from job-supplied paths; spec
carries the (path, caption) list per sheet key.

Per Amendment 8 (FABRIC SWATCH): source_url and the cached asset
path live in spec when present. The build pipeline fetches once
at intake; build(spec) stays pure.

This module raises SpecIncomplete — a STRUCTURED refusal listing
exactly what is absent — never `sys.exit(1)`, never silent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


class SpecIncomplete(Exception):
    """Structured refusal listing exactly what's absent.

    Per P1-T·c (Builder interface): MAX must receive either a
    document or a list of what to go ask the founder for. Process
    exits cannot be orchestrated.
    """
    def __init__(self, missing: List[str]):
        self.missing = list(missing)
        super().__init__(
            f"Spec incomplete. Missing required fields: {self.missing}"
        )


@dataclass(frozen=True)
class Address:
    """Single source for the footer address (Amendment 1).

    Street / city / state / zip are typed ONCE here. Footer renders
    `street · city state zip` from this record. Nothing typed twice.
    """
    street: str  # e.g. "5124 Frolich Ln"
    city:   str  # e.g. "Hyattsville"
    state:  str  # e.g. "MD"
    zip:    str  # e.g. "20781"

    def footer_letterhead(self) -> str:
        """Full address, single source — chrome() reads this."""
        return f"{self.street}  ·  {self.city} {self.state} {self.zip}"


@dataclass(frozen=True)
class JobSpec:
    """The single source for every sheet. Nothing typed twice.

    Per EMPIRE_CLIENT_DOC_STANDARD.md Rule 1 (THE ONE RULE).

    `header_tagline` and `footer_letterhead` are TWO DISTINCT fields
    (per P1-T·b ruling). `POWERED BY EMPIRE WORKROOM` belongs in
    `header_tagline`; the address belongs in `footer_letterhead`.

    `document_type` is one of five: measurement_set, estimate,
    invoice, presentation_sheet, board.

    `content_family` is what is being drawn/priced (e.g.
    window_openings for measurement sets, drapery for drapery
    presentation sheets). Kept independent of document_type
    per the dispatch's two-axis rule.
    """
    # ── Job-level ──
    project:       str
    client:        str
    client_loc:    str
    scope:         str

    # ── Address (Amendment 1) — single source for footer ──
    address:       Address

    # ── Chrome fields (TWO distinct — P1-T·b ruling) ──
    header_tagline:    str  # e.g. "POWERED BY EMPIRE WORKROOM"
    footer_letterhead: str  # computed from address (override-able)
    locale:            str  # e.g. "HYATTSVILLE MD" (legacy)

    # ── Rev / status (Amendment 6: single stamp across set) ──
    rev:     str
    date:    str
    source:  str
    status:  str

    # ── Type axes (kept independent per dispatch) ──
    document_type:   str   # measurement_set | estimate | invoice | presentation_sheet | board
    content_family:  str   # window_openings (P1-T·b proven); others added in later dispatches

    # ── Per-sheet photos (Amendment 7: per-job upload) ──
    # Keyed by sheet key (e.g. "FD", "LRB"). Each value is a list of
    # (asset_path, caption). Missing paths degrade to
    # "NO SITE PHOTO ON FILE" (handled by chrome/band layer).
    photos: dict[str, List[Tuple[str, str]]] = field(default_factory=dict)

    # ── Body data (rooms, panels, schedule, etc.) ──
    rooms:     List[dict] = field(default_factory=list)
    schedule:  List[tuple] = field(default_factory=list)

    def missing_required_fields(self) -> List[str]:
        """What the spec is missing — drives SpecIncomplete."""
        missing: List[str] = []
        if not self.project:             missing.append("project")
        if not self.client:              missing.append("client")
        if not self.address.street:       missing.append("address.street")
        if not self.address.city:         missing.append("address.city")
        if not self.address.state:        missing.append("address.state")
        if not self.address.zip:          missing.append("address.zip")
        if not self.header_tagline:      missing.append("header_tagline")
        if not self.rev:                 missing.append("rev")
        if not self.date:                missing.append("date")
        if not self.document_type:       missing.append("document_type")
        if not self.content_family:      missing.append("content_family")
        return missing

    def validate(self) -> None:
        """Raise SpecIncomplete if anything required is absent.

        Per P1-T·c: structured refusal with the missing-field list,
        never `sys.exit(1)`. Per Rule 3 of the standard: never invent
        dimensions. The list is exact.
        """
        missing = self.missing_required_fields()
        if missing:
            raise SpecIncomplete(missing=missing)


# ══════════════════════ DERIVED — single source for repeated quantities ══════

def count_openings(spec: JobSpec) -> int:
    """Single derivation for total openings (Amendment 4).

    Read by BOTH cover index AND schedule. Two derivation paths in the
    reference (cover counts drawn windows, schedule sums SCHEDULE
    qtys) disagree in McLean RevA (21 vs 22). This function is the
    ONE source — both sheets consume it.

    Counts window-kind items across all panels/rooms.
    """
    if spec.schedule:
        # SCHEDULE rows are (room, mark, qty, width, height, note).
        # Total = sum of qty (col index 2).
        return sum(row[2] for row in spec.schedule)
    # Fallback: count window-kind items in rooms/panels.
    n = 0
    for r in spec.rooms:
        for p in r.get("panels", []):
            for i in p.get("items", []):
                if i.get("kind") == "window":
                    n += 1
    return n
