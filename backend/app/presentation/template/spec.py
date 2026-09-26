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

    McLean golden chrome: `letterhead` (NELMA'S WORKROOM) +
    `header_tagline` (POWERED BY EMPIRE WORKROOM) + brand footer
    (`letterhead · tagline · locale`). Street address stays on
    `address` for gates/estimates; drawing sheets print brand_footer().

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
    header_tagline:    str  # POWERED BY EMPIRE WORKROOM
    footer_letterhead: str  # street override / gate source; drawings use brand footer
    locale:            str  # HYATTSVILLE MD

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

    # ── Cover / schedule open-item lists (job-specific; never inherit
    # another job's McLean closure notes). Empty → body derives from
    # this JobSpec's room check lists.
    open_at_glance:      List[str] = field(default_factory=list)
    schedule_open_notes: List[str] = field(default_factory=list)

    # ── Body data (rooms, panels, schedule, etc.) ──
    rooms:     List[dict] = field(default_factory=list)
    schedule:  List[tuple] = field(default_factory=list)

    # McLean golden brand (default Max drawing chrome)
    letterhead: str = "NELMA'S WORKROOM"

    def project_line(self) -> str:
        """Header project line: CLIENT · PROJECT (McLean)."""
        return f"{self.client}  ·  {self.project}".upper()

    def brand_footer(self) -> str:
        """Footer left zone — McLean brand language (not street address)."""
        return f"{self.letterhead}  ·  {self.header_tagline}  ·  {self.locale}"

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




def normalize_check_lines(check) -> List[str]:
    """Normalize room['check'] to a list of bullet strings.

    A plain str is ONE bullet (or newline-split bullets) — never iterated
    character-by-character (that produced Field Check letter-stacks).
    Dict items with text/line keys are supported (settled-marker form).
    """
    if check is None:
        return []
    if isinstance(check, str):
        parts = [p.strip() for p in check.replace("\r\n", "\n").split("\n") if p.strip()]
        return parts if parts else ([check.strip()] if check.strip() else [])
    out: List[str] = []
    for item in check:
        if isinstance(item, dict):
            text = item.get("text") or item.get("line") or ""
            if text:
                out.append(str(text))
        elif item is not None and str(item).strip():
            out.append(str(item))
    return out


# ══════════════════════ IN-SCOPE FILTER ══════════════════════════════════════
# Founder rule (2026-09-26): EXCLUDED / omitted / not-in-scope openings must
# NOT appear as sheets, schedule rows, cover bullets, or drawn panels labeled
# "(EXCLUDED)". Skip them entirely — never draw with an exclusion stamp.

_OUT_OF_SCOPE_STATUS = frozenset({
    "excluded", "exclude", "omitted", "omit", "out_of_scope", "oos",
    "not_in_scope", "not-in-scope", "out-of-scope", "noscope",
})

_IN_SCOPE_STATUS = frozenset({
    "included", "include", "in_scope", "in-scope", "active", "scope",
})


def _status_token(value) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _blob_flags_out_of_scope(*parts) -> bool:
    """True when free text marks an opening as excluded / omitted / OOS."""
    blob = " ".join(str(p) for p in parts if p is not None and str(p).strip())
    if not blob:
        return False
    low = blob.lower()
    # Parenthetical or bare status markers commonly used in JobSpecs.
    markers = (
        "(excluded)", "excluded", "(omit)", "(omitted)", " omitted",
        "omit —", "omit -", "omit:", "out of scope", "out-of-scope",
        "not in scope", "not-in-scope", "oos)",
    )
    return any(m in low for m in markers)


def is_panel_in_scope(panel: dict) -> bool:
    """False when a panel is explicitly or textually out of job scope."""
    if not isinstance(panel, dict):
        return False
    status = _status_token(panel.get("status") or panel.get("scope"))
    if status in _OUT_OF_SCOPE_STATUS:
        return False
    if status in _IN_SCOPE_STATUS:
        return True
    if _blob_flags_out_of_scope(
        panel.get("label"), panel.get("title"), panel.get("note"),
        panel.get("name"),
    ):
        return False
    return True


def is_schedule_row_in_scope(row) -> bool:
    """False when a schedule tuple marks an excluded / omitted opening."""
    if not row:
        return False
    # Optional trailing status on long rows; canonical is 6-tuple.
    note = row[5] if len(row) > 5 else ""
    mark = row[1] if len(row) > 1 else ""
    status = _status_token(row[6]) if len(row) > 6 else ""
    if status in _OUT_OF_SCOPE_STATUS:
        return False
    if status in _IN_SCOPE_STATUS:
        return True
    if _blob_flags_out_of_scope(mark, note):
        return False
    return True


def is_room_in_scope(room: dict) -> bool:
    """False when the room itself is out of scope (before panel filter)."""
    if not isinstance(room, dict):
        return False
    status = _status_token(room.get("status") or room.get("scope"))
    if status in _OUT_OF_SCOPE_STATUS:
        return False
    if _blob_flags_out_of_scope(room.get("name"), room.get("sub"), room.get("key")):
        # Room titled "... (EXCLUDED)" — skip whole room.
        return False
    return True


def _filter_data_rows(rows) -> list:
    out = []
    for row in rows or []:
        if isinstance(row, (list, tuple)) and len(row) >= 2:
            if _blob_flags_out_of_scope(row[0], row[1]):
                continue
            out.append(row)
        elif isinstance(row, dict):
            if _blob_flags_out_of_scope(
                row.get("label"), row.get("key"), row.get("value"),
                row.get("text"),
            ):
                continue
            out.append(row)
        else:
            out.append(row)
    return out


def _filter_text_lines(lines) -> list:
    return [
        ln for ln in (lines or [])
        if not _blob_flags_out_of_scope(ln)
    ]


def filter_in_scope_rooms(rooms: List[dict]) -> List[dict]:
    """Drop out-of-scope rooms and strip excluded panels / data / checks.

    Rooms that retain zero in-scope panels are omitted entirely (no empty
    elevation sheet).
    """
    filtered: List[dict] = []
    for room in rooms or []:
        if not is_room_in_scope(room):
            continue
        panels = [p for p in room.get("panels", []) if is_panel_in_scope(p)]
        if not panels:
            continue
        new_room = dict(room)
        new_room["panels"] = panels
        if "data" in new_room:
            new_room["data"] = _filter_data_rows(new_room.get("data"))
        if "check" in new_room:
            checks = normalize_check_lines(new_room.get("check"))
            scrubbed = _filter_text_lines(checks)
            new_room["check"] = scrubbed
        # Scrub math that only exists to note an exclusion.
        if _blob_flags_out_of_scope(new_room.get("math")):
            # Keep useful package math; strip trailing exclusion clauses
            # when the whole string is an exclusion bullet. Prefer empty
            # over emitting "blinds excluded" as layout math.
            math = str(new_room.get("math") or "")
            # Drop segments separated by · that flag out of scope.
            parts = [p.strip() for p in math.replace("·", "|").split("|")]
            keep = [p for p in parts if p and not _blob_flags_out_of_scope(p)]
            new_room["math"] = " · ".join(keep)
        filtered.append(new_room)
    return filtered


def filter_in_scope_schedule(schedule: List[tuple]) -> List[tuple]:
    return [row for row in (schedule or []) if is_schedule_row_in_scope(row)]


def in_scope_spec(spec: "JobSpec") -> "JobSpec":
    """Return a JobSpec copy with out-of-scope openings removed.

    Applied once at assemble() so cover index, room elevations, schedule,
    count_openings, and open-at-glance all agree — no EXCLUDED sheets.
    """
    from dataclasses import replace
    rooms = filter_in_scope_rooms(list(spec.rooms))
    schedule = filter_in_scope_schedule(list(spec.schedule))
    glance = _filter_text_lines(list(spec.open_at_glance))
    notes = _filter_text_lines(list(spec.schedule_open_notes))
    # Drop photos keyed to rooms that were removed.
    keep_keys = {r.get("key") for r in rooms if r.get("key")}
    photos = {
        k: v for k, v in (spec.photos or {}).items()
        if k in keep_keys or not keep_keys
    }
    # If some rooms remain, restrict photos to surviving keys only.
    if rooms:
        photos = {k: v for k, v in (spec.photos or {}).items() if k in keep_keys}
    return replace(
        spec,
        rooms=rooms,
        schedule=schedule,
        open_at_glance=glance,
        schedule_open_notes=notes,
        photos=photos,
    )


def derive_open_items(spec: "JobSpec", limit: int = 6) -> List[str]:
    """Honest per-job open items from room check lists.

    Used when open_at_glance / schedule_open_notes are empty. Never
    falls back to another job's (McLean Whittington) closure notes.
    """
    items: List[str] = []
    for r in spec.rooms:
        name = r.get("name") or r.get("key") or "ROOM"
        for line in normalize_check_lines(r.get("check")):
            if line.upper().startswith("DRAFT"):
                continue
            items.append(f"{name}: {line}")
            if len(items) >= limit:
                return items
    return items or ["No open items recorded on this JobSpec."]

# ══════════════════════ DERIVED — single source for repeated quantities ══════

def count_openings(spec: JobSpec) -> int:
    """Single derivation for total openings (Amendment 4).

    Read by BOTH cover index AND schedule. Two derivation paths in the
    reference (cover counts drawn windows, schedule sums SCHEDULE
    qtys) disagree in McLean RevA (21 vs 22). This function is the
    ONE source — both sheets consume it.

    Counts in-scope window-kind items only (excluded/omitted openings
    are skipped — founder rule 2026-09-26).
    """
    schedule = filter_in_scope_schedule(list(spec.schedule)) if spec.schedule else []
    if schedule:
        # SCHEDULE rows are (room, mark, qty, width, height, note).
        # Total = sum of qty (col index 2).
        return sum(row[2] for row in schedule)
    # Fallback: count window-kind items in in-scope rooms/panels.
    n = 0
    for r in filter_in_scope_rooms(list(spec.rooms)):
        for p in r.get("panels", []):
            for i in p.get("items", []):
                if i.get("kind") == "window":
                    n += 1
    return n
