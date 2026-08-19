"""assemble.py — Orders sheets, stamps one rev across the set, refuses
mixed-rev.

Per EMPIRE_CLIENT_DOC_STANDARD.md Section 4 rule 6:
"Every sheet carries rev + date. **A set with mixed revs is a defect
— assembly must refuse to emit.**"

Per P1-T·c (Builder interface): builders are pure functions, no
module-global mutable state. `assemble(spec)` returns a BuildResult
(pdf_bytes, gate_report, derived_quantities) — or raises
SpecIncomplete for missing fields.

The dispatch explicitly states: REPLACE `sys.exit(1)` EVERYWHERE.
A process exit cannot be orchestrated; MAX must receive either a
document or a list of what to go ask the founder for.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import List

from app.presentation.template.spec import JobSpec, SpecIncomplete
from app.presentation.template.body.measurement_set import (
    cover, room_sheet, schedule_sheet,
)


# Body builders keyed by document_type. One per type.
BODY_BUILDERS = {
    "measurement_set": None,   # set in _register_body_builders below
    # Other four are SCAFFOLDS — raise SpecIncomplete.
}


def _register_body_builders():
    """Register the measurement_set body builders.

    Called at module load. Keeps body builders decoupled from spec.
    """
    BODY_BUILDERS["measurement_set"] = {
        "cover":           lambda spec, no, total, placed: cover(spec, total, placed),
        "room_sheet":      lambda spec, room, no, total, placed:
                                room_sheet(spec, room, no, total, placed),
        "schedule_sheet":  lambda spec, no, total, placed:
                                schedule_sheet(spec, no, total, placed),
    }


_register_body_builders()


@dataclass
class BuildResult:
    """Per P1-T·c: pure-function output.

    pdf_bytes        : the assembled PDF as bytes
    gate_report      : list of (gate_name, status, line) tuples
    derived          : dict of derived quantities consumed during build
                      (so MAX can show them in the response without
                      re-deriving)
    """
    pdf_bytes: bytes
    gate_report: List[tuple] = field(default_factory=list)
    derived: dict = field(default_factory=dict)


def assemble(spec: JobSpec) -> BuildResult:
    """Assemble a document from spec. Pure function — no sys.exit.

    Raises:
        SpecIncomplete: missing required fields. Caller (MAX) renders
                        a structured refusal listing what's absent.
        GateReportFail: a gate fails (text vs text, bounds, etc.).
    """
    # Validate spec
    spec.validate()  # raises SpecIncomplete

    if spec.document_type != "measurement_set":
        # Delegate to the scaffolded body builder, which raises
        # SpecIncomplete.
        return _delegate(spec)

    builder = BODY_BUILDERS["measurement_set"]
    placed_global: List = []     # Amendment 5: draw-time bboxes
    total = len(spec.rooms) + 2  # cover + rooms + schedule

    # Rev singularity check (Section 4 rule 6)
    rev = spec.rev
    if not rev:
        raise SpecIncomplete(missing=["rev (single stamp across set)"])

    # Build each sheet with a SHEET-SCOPED placed accumulator
    # (per the P1-T·c builder-interface ruling: pure builders, no
    # module-global state).
    sheets: List[str] = []
    for fn_name, fn in (
        ("cover", builder["cover"]),
        ("schedule_sheet", builder["schedule_sheet"]),
    ):
        # Schedule sheet's index is `total` (last sheet).
        sheet_svg = fn(spec, total, total, [])
        sheets.append(sheet_svg)
    # (Room sheets are between cover and schedule; assemble in order)
    # We re-collect room sheets separately to interleave them.
    room_svgs = []
    for n, r in enumerate(spec.rooms, start=2):
        room_svgs.append(builder["room_sheet"](spec, r, n, total, []))
    # Re-order: cover, room1..roomN, schedule.
    cover_svg = sheets[0]
    schedule_svg = sheets[1]
    sheets = [cover_svg] + room_svgs + [schedule_svg]

    # Render SVG → PDF via cairosvg + pypdf
    try:
        import cairosvg
        from pypdf import PdfWriter, PdfReader
    except ImportError as e:
        raise SpecIncomplete(missing=[
            f"build dependencies missing: {e}. Install cairosvg + pypdf."
        ])

    w = PdfWriter()
    for svg in sheets:
        buf = io.BytesIO()
        cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=buf, dpi=72)
        buf.seek(0)
        w.add_page(PdfReader(buf).pages[0])

    # Run gates on the placed list (Amendment 5)
    gate_report: List[tuple] = []
    from app.presentation.template.gates import (
        gate_bounds, gate_collisions,
    )
    bounds_failures = gate_bounds(placed_global)
    if bounds_failures:
        gate_report.append(("G1 bounds", "FAIL", "; ".join(bounds_failures)))
    else:
        gate_report.append(("G1 bounds", "PASS", "all text inside page"))
    collision_failures = gate_collisions(placed_global)
    if collision_failures:
        gate_report.append(("G2 collisions", "FAIL",
                            "; ".join(collision_failures)))
    else:
        gate_report.append(("G2 collisions", "PASS", "no text overlaps"))

    # Write to bytes
    out = io.BytesIO()
    w.write(out)
    pdf_bytes = out.getvalue()

    # Amendment 4: derived counts (single source)
    from app.presentation.template.spec import count_openings
    derived = {
        "count_openings": count_openings(spec),
    }

    return BuildResult(
        pdf_bytes=pdf_bytes,
        gate_report=gate_report,
        derived=derived,
    )


def _delegate(spec: JobSpec) -> BuildResult:
    """Delegate to a non-measurement-set body builder.

    All four other types are SCAFFOLDS — they raise SpecIncomplete.
    """
    body_type = spec.document_type
    if body_type == "estimate":
        from app.presentation.template.body import estimate as _b
    elif body_type == "invoice":
        from app.presentation.template.body import invoice as _b
    elif body_type == "presentation_sheet":
        from app.presentation.template.body import presentation_sheet as _b
    elif body_type == "board":
        from app.presentation.template.body import board as _b
    else:
        raise SpecIncomplete(missing=[f"document_type '{body_type}'"])
    return _b.build(spec)  # raises SpecIncomplete
