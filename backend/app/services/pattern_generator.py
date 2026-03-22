"""
Pattern Template Generator — mathematically accurate sewing patterns.
Generates printable PDF templates at 100% scale using ReportLab.
"""
import math
import io
import uuid
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, gray, white, Color

LETTER_W, LETTER_H = LETTER  # 612 x 792 points = 8.5" x 11"
PPI = 72  # points per inch (ReportLab default)


def in_to_frac(val: float) -> str:
    """Convert decimal inches to fraction string. 4.75 -> '4 3/4\"'"""
    whole = int(val)
    frac = val - whole
    # Common sewing fractions: 1/8, 1/4, 3/8, 1/2, 5/8, 3/4, 7/8
    eighths = round(frac * 8)
    if eighths == 0:
        return f'{whole}"'
    if eighths == 8:
        return f'{whole + 1}"'
    # Simplify
    if eighths % 4 == 0:
        return f'{whole} {eighths // 4}/2"' if whole else f'{eighths // 4}/2"'
    if eighths % 2 == 0:
        return f'{whole} {eighths // 2}/4"' if whole else f'{eighths // 2}/4"'
    return f'{whole} {eighths}/8"' if whole else f'{eighths}/8"'


@dataclass
class PatternPiece:
    """A single pattern piece with outline points."""
    name: str
    cut_count: int  # "Cut 2", "Cut 6", etc.
    # Points defining the SEAM LINE (finished size)
    seam_points: List[Tuple[float, float]]  # [(x_inches, y_inches), ...]
    # Points defining the CUTTING LINE (with seam allowance)
    cut_points: List[Tuple[float, float]]
    width_inches: float
    height_inches: float
    is_curved: bool = False
    # For curved pieces, these are control points for bezier curves
    # Format: list of (type, points) where type is 'line' or 'curve'
    seam_path: List[Tuple[str, List[Tuple[float, float]]]] = field(default_factory=list)
    cut_path: List[Tuple[str, List[Tuple[float, float]]]] = field(default_factory=list)
    notch_positions: List[Tuple[float, float]] = field(default_factory=list)
    grainline_vertical: bool = True
    notes: str = ""


@dataclass
class PatternResult:
    """Complete pattern result with all pieces."""
    shape: str
    pieces: List[PatternPiece]
    total_fabric_sq_in: float
    fabric_yardage_54: float  # yards needed on 54" wide fabric
    construction_notes: List[str]
    dimensions_summary: str


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SPHERE GORE PATTERN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def generate_sphere(
    diameter: float = 9.39,
    num_gores: int = 8,
    seam_allowance: float = 0.5,
    pillow_cover: bool = False,
    pillow_reduction: float = 0.5,
) -> PatternResult:
    """
    Generate sphere gore pattern.

    Gore shape formula:
    - Gore height (pole to pole along surface) = pi x diameter / 2
    - Gore width at angle theta: w(theta) = (circumference / num_gores) x sin(theta)
    - theta goes from 0 (north pole) to pi (south pole)
    """
    d = diameter
    if pillow_cover:
        d -= pillow_reduction

    circumference = math.pi * d
    gore_height = math.pi * d / 2  # Half circumference = pole-to-pole arc
    max_gore_width = circumference / num_gores  # Width at equator

    # Generate gore outline points (seam line)
    # Sample 100 points along the gore from pole to pole
    n_points = 100
    seam_right = []
    seam_left = []

    for i in range(n_points + 1):
        theta = (i / n_points) * math.pi  # 0 to pi
        y = (i / n_points) * gore_height  # 0 to gore_height
        half_width = (max_gore_width / 2) * math.sin(theta)
        seam_right.append((half_width, y))
        seam_left.append((-half_width, y))

    # Seam line: left side (bottom to top) + right side (top to bottom)
    seam_points = list(reversed(seam_left)) + seam_right

    # Cutting line: offset outward by seam_allowance
    cut_right = []
    cut_left = []
    for i in range(n_points + 1):
        theta = (i / n_points) * math.pi
        y = (i / n_points) * gore_height
        half_width = (max_gore_width / 2) * math.sin(theta)

        # Calculate outward normal direction for offset
        if i == 0 or i == n_points:
            # At poles, offset vertically
            y_offset = -seam_allowance if i == 0 else seam_allowance
            cut_right.append((half_width + seam_allowance * 0.3, y + y_offset))
            cut_left.append((-half_width - seam_allowance * 0.3, y + y_offset))
        else:
            # Normal offset along the width
            cut_right.append((half_width + seam_allowance, y))
            cut_left.append((-half_width - seam_allowance, y))

    cut_points = list(reversed(cut_left)) + cut_right

    # Build path for smooth curves
    seam_path = _points_to_path(seam_right, seam_left)
    cut_path = _points_to_path(cut_right, cut_left)

    # Notch marks at equator (widest point) on both sides
    notches = [
        (max_gore_width / 2, gore_height / 2),
        (-max_gore_width / 2, gore_height / 2),
    ]

    piece = PatternPiece(
        name=f"Sphere Gore ({num_gores}-panel)",
        cut_count=num_gores,
        seam_points=seam_points,
        cut_points=cut_points,
        width_inches=max_gore_width + seam_allowance * 2,
        height_inches=gore_height + seam_allowance * 2,
        is_curved=True,
        seam_path=seam_path,
        cut_path=cut_path,
        notch_positions=notches,
        grainline_vertical=True,
        notes=f"Width at equator: {in_to_frac(max_gore_width)} (seam to seam)",
    )

    fabric_area = num_gores * piece.width_inches * piece.height_inches
    yardage = _estimate_yardage([(piece.width_inches, piece.height_inches, num_gores)], 54)

    notes = [
        f"Sphere diameter: {in_to_frac(d)} ({d:.2f}\")",
        f"Circumference: {in_to_frac(circumference)} ({circumference:.2f}\")",
        f"Gore height (pole to pole): {in_to_frac(gore_height)} ({gore_height:.2f}\")",
        f"Gore width at equator: {in_to_frac(max_gore_width)} ({max_gore_width:.2f}\")",
        f"Number of gores: {num_gores}",
        f"Seam allowance: {in_to_frac(seam_allowance)}",
        f"Sew gores together along long curved edges, matching notch marks at equator.",
        f"Leave a 3-4\" opening in the last seam for turning/stuffing.",
    ]
    if pillow_cover:
        notes.insert(0, f"PILLOW COVER: Template reduced by {pillow_reduction}\" for snug fit over insert.")

    return PatternResult(
        shape="sphere",
        pieces=[piece],
        total_fabric_sq_in=fabric_area,
        fabric_yardage_54=yardage,
        construction_notes=notes,
        dimensions_summary=f"{in_to_frac(d)} diameter, {num_gores} gores",
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CYLINDER / BOLSTER PATTERN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def generate_cylinder(
    diameter: float = 6.0,
    length: float = 18.0,
    seam_allowance: float = 0.5,
    end_cap_style: str = "flat",  # flat, gathered, piped
    zipper: bool = True,
    piping: bool = False,
) -> PatternResult:
    """
    Generate cylinder (bolster) pattern pieces.

    Body panel: rectangle, width = pi x diameter, height = length
    End caps: circles, diameter + seam allowance on each side
    """
    circumference = math.pi * diameter
    radius = diameter / 2

    pieces = []

    # Body panel (rectangle)
    body_w = circumference + seam_allowance * 2  # SA on both sides
    body_h = length + seam_allowance * 2
    if zipper:
        # Add overlap for zipper
        body_w += 1.0  # 0.5" overlap each side

    body_seam = [
        (0, 0), (circumference, 0),
        (circumference, length), (0, length), (0, 0)
    ]
    body_cut = [
        (-seam_allowance, -seam_allowance),
        (circumference + seam_allowance + (1.0 if zipper else 0), -seam_allowance),
        (circumference + seam_allowance + (1.0 if zipper else 0), length + seam_allowance),
        (-seam_allowance, length + seam_allowance),
        (-seam_allowance, -seam_allowance),
    ]

    body_notes = f"Body: {in_to_frac(circumference)} wide x {in_to_frac(length)} long"
    if zipper:
        body_notes += " (includes 1\" zipper overlap)"

    pieces.append(PatternPiece(
        name="Bolster Body",
        cut_count=1,
        seam_points=body_seam,
        cut_points=body_cut,
        width_inches=body_w,
        height_inches=body_h,
        notes=body_notes,
    ))

    # End caps
    if end_cap_style == "flat":
        # Circle end cap
        n_pts = 72
        cap_seam = []
        cap_cut = []
        for i in range(n_pts + 1):
            angle = (i / n_pts) * 2 * math.pi
            cap_seam.append((radius * math.cos(angle), radius * math.sin(angle)))
            cap_cut.append(((radius + seam_allowance) * math.cos(angle),
                           (radius + seam_allowance) * math.sin(angle)))

        cap_notches = [
            (radius, 0), (-radius, 0), (0, radius), (0, -radius)
        ]

        pieces.append(PatternPiece(
            name="End Cap (circle)",
            cut_count=2,
            seam_points=cap_seam,
            cut_points=cap_cut,
            width_inches=diameter + seam_allowance * 2,
            height_inches=diameter + seam_allowance * 2,
            is_curved=True,
            notch_positions=cap_notches,
            notes=f"Diameter: {in_to_frac(diameter)} (seam to seam)",
        ))
    elif end_cap_style == "gathered":
        # Gathered end: circle with extra radius for gather
        gather_extra = 2.0
        n_pts = 72
        cap_seam = []
        cap_cut = []
        r_gather = radius + gather_extra
        for i in range(n_pts + 1):
            angle = (i / n_pts) * 2 * math.pi
            cap_seam.append((r_gather * math.cos(angle), r_gather * math.sin(angle)))
            cap_cut.append(((r_gather + seam_allowance) * math.cos(angle),
                           (r_gather + seam_allowance) * math.sin(angle)))

        pieces.append(PatternPiece(
            name="End Cap (gathered)",
            cut_count=2,
            seam_points=cap_seam,
            cut_points=cap_cut,
            width_inches=(r_gather + seam_allowance) * 2,
            height_inches=(r_gather + seam_allowance) * 2,
            is_curved=True,
            notes=f"Gather {in_to_frac(gather_extra)} toward center with drawstring",
        ))

    # Piping piece
    if piping:
        pipe_w = 1.5  # Piping strip width (covers 1/4" cord)
        pipe_l = circumference + 2.0  # Extra for overlap
        pieces.append(PatternPiece(
            name="Piping Strip (bias cut)",
            cut_count=2,
            seam_points=[(0, 0), (pipe_l, 0), (pipe_l, pipe_w), (0, pipe_w), (0, 0)],
            cut_points=[(0, 0), (pipe_l, 0), (pipe_l, pipe_w), (0, pipe_w), (0, 0)],
            width_inches=pipe_l,
            height_inches=pipe_w,
            grainline_vertical=False,
            notes=f"Cut on bias (45 degrees). Wrap around 1/4\" cording.",
        ))

    # Calculations
    all_pieces_dims = [(p.width_inches, p.height_inches, p.cut_count) for p in pieces]
    fabric_area = sum(w * h * c for w, h, c in all_pieces_dims)
    yardage = _estimate_yardage(all_pieces_dims, 54)

    notes = [
        f"Bolster: {in_to_frac(diameter)} diameter x {in_to_frac(length)} long",
        f"Body circumference: {in_to_frac(circumference)} ({circumference:.2f}\")",
        f"Seam allowance: {in_to_frac(seam_allowance)}",
        f"End cap style: {end_cap_style}",
    ]
    if zipper:
        notes.append(f"Install zipper along the long edge of the body panel.")
    notes.extend([
        f"Pin end caps to body tube, matching notches to seam and fold lines.",
        f"Sew end caps with the cap facing up (easing fullness evenly).",
    ])

    return PatternResult(
        shape="cylinder",
        pieces=pieces,
        total_fabric_sq_in=fabric_area,
        fabric_yardage_54=yardage,
        construction_notes=notes,
        dimensions_summary=f"{in_to_frac(diameter)} dia x {in_to_frac(length)} long",
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BOX CUSHION PATTERN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def generate_box_cushion(
    width: float = 20.0,
    depth: float = 20.0,
    thickness: float = 4.0,
    seam_allowance: float = 0.5,
    corner_radius: float = 0.0,
    zipper_in_back: bool = True,
    welt: bool = False,
    t_cushion: bool = False,
    t_arm_width: float = 6.0,
    t_arm_depth: float = 4.0,
) -> PatternResult:
    """
    Generate box cushion pattern.

    Top/bottom panels: width x depth (with optional corner radius or T-shape)
    Boxing strip: perimeter x thickness
    """
    pieces = []
    sa = seam_allowance

    if t_cushion:
        # T-cushion: main rect + T-arm extensions
        # Shape: wider at front, narrower at back (arms extend forward)
        #   +------------------+
        #   |   T-arm          |  <- t_arm_depth tall
        #   |  +----------+    |
        #   |  |          |    |
        #   |  |   main   |    |
        #   |  |          |    |
        #   |  +----------+    |
        #   +------------------+
        # Actually T-cushion: back is full width, front has notches for chair arms
        main_w = width - 2 * t_arm_width

        # Build T-cushion outline
        seam_pts = [
            (0, 0),  # back-left
            (width, 0),  # back-right
            (width, depth - t_arm_depth),  # right before notch
            (width - t_arm_width, depth - t_arm_depth),  # notch inner-right
            (width - t_arm_width, depth),  # front-right
            (t_arm_width, depth),  # front-left
            (t_arm_width, depth - t_arm_depth),  # notch inner-left
            (0, depth - t_arm_depth),  # left before notch
            (0, 0),  # close
        ]
        cut_pts = [
            (-sa, -sa),
            (width + sa, -sa),
            (width + sa, depth - t_arm_depth),
            (width - t_arm_width + sa, depth - t_arm_depth - sa),
            (width - t_arm_width + sa, depth + sa),
            (t_arm_width - sa, depth + sa),
            (t_arm_width - sa, depth - t_arm_depth - sa),
            (-sa, depth - t_arm_depth),
            (-sa, -sa),
        ]
        perimeter = 2 * width + 2 * depth + 4 * t_arm_depth  # Approximate
        panel_notes = f"T-cushion: {in_to_frac(width)} x {in_to_frac(depth)}, arm notch {in_to_frac(t_arm_width)} x {in_to_frac(t_arm_depth)}"

    elif corner_radius > 0:
        # Rounded corners
        n_arc = 16
        seam_pts = []
        cut_pts = []
        r = corner_radius

        # Generate rounded rectangle
        corners = [
            (r, r, math.pi, 1.5 * math.pi),           # bottom-left
            (width - r, r, 1.5 * math.pi, 2 * math.pi), # bottom-right
            (width - r, depth - r, 0, 0.5 * math.pi),  # top-right
            (r, depth - r, 0.5 * math.pi, math.pi),    # top-left
        ]
        for cx, cy, a_start, a_end in corners:
            for j in range(n_arc + 1):
                angle = a_start + (a_end - a_start) * (j / n_arc)
                seam_pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
                cut_pts.append((cx + (r + sa) * math.cos(angle), cy + (r + sa) * math.sin(angle)))
        seam_pts.append(seam_pts[0])
        cut_pts.append(cut_pts[0])

        perimeter = 2 * (width + depth) - 8 * r + 2 * math.pi * r
        panel_notes = f"Rounded corners: {in_to_frac(corner_radius)} radius"
    else:
        # Simple rectangle
        seam_pts = [
            (0, 0), (width, 0), (width, depth), (0, depth), (0, 0)
        ]
        cut_pts = [
            (-sa, -sa), (width + sa, -sa),
            (width + sa, depth + sa), (-sa, depth + sa), (-sa, -sa)
        ]
        perimeter = 2 * (width + depth)
        panel_notes = f"Square corners"

    # Top panel
    pieces.append(PatternPiece(
        name="Top Panel",
        cut_count=1,
        seam_points=seam_pts,
        cut_points=cut_pts,
        width_inches=width + sa * 2,
        height_inches=depth + sa * 2,
        is_curved=corner_radius > 0,
        notch_positions=[(width / 2, 0), (width / 2, depth), (0, depth / 2), (width, depth / 2)],
        notes=panel_notes,
    ))

    # Bottom panel (same as top, but may have zipper)
    pieces.append(PatternPiece(
        name="Bottom Panel",
        cut_count=1,
        seam_points=seam_pts,
        cut_points=cut_pts,
        width_inches=width + sa * 2,
        height_inches=depth + sa * 2,
        is_curved=corner_radius > 0,
        notch_positions=[(width / 2, 0), (width / 2, depth)],
        notes=panel_notes + (". Zipper in back edge." if zipper_in_back else ""),
    ))

    # Boxing strip (sides)
    if zipper_in_back:
        # Front boxing: 3 sides (left + front + right)
        front_boxing_len = depth + width + depth  # left side + front + right side
        back_boxing_len = width + 2.0  # back + zipper overlap

        # Front boxing
        pieces.append(PatternPiece(
            name="Front Boxing Strip",
            cut_count=1,
            seam_points=[(0, 0), (front_boxing_len, 0), (front_boxing_len, thickness), (0, thickness), (0, 0)],
            cut_points=[(-sa, -sa), (front_boxing_len + sa, -sa),
                       (front_boxing_len + sa, thickness + sa), (-sa, thickness + sa), (-sa, -sa)],
            width_inches=front_boxing_len + sa * 2,
            height_inches=thickness + sa * 2,
            notch_positions=[(depth, thickness / 2), (depth + width, thickness / 2)],
            notes=f"Front + sides: {in_to_frac(front_boxing_len)} long x {in_to_frac(thickness)} wide. Notch at corners.",
        ))

        # Back boxing (2 pieces for zipper)
        half_box = thickness / 2 + 1.0  # Half height + zipper seam
        pieces.append(PatternPiece(
            name="Back Boxing (zipper half)",
            cut_count=2,
            seam_points=[(0, 0), (back_boxing_len, 0), (back_boxing_len, half_box), (0, half_box), (0, 0)],
            cut_points=[(-sa, -sa), (back_boxing_len + sa, -sa),
                       (back_boxing_len + sa, half_box + sa), (-sa, half_box + sa), (-sa, -sa)],
            width_inches=back_boxing_len + sa * 2,
            height_inches=half_box + sa * 2,
            notes=f"Back boxing zipper halves: {in_to_frac(back_boxing_len)} x {in_to_frac(half_box)}. Install zipper between these two pieces.",
        ))
    else:
        # Single continuous boxing strip
        total_boxing_len = perimeter + 2.0  # Add overlap
        pieces.append(PatternPiece(
            name="Boxing Strip",
            cut_count=1,
            seam_points=[(0, 0), (total_boxing_len, 0), (total_boxing_len, thickness), (0, thickness), (0, 0)],
            cut_points=[(-sa, -sa), (total_boxing_len + sa, -sa),
                       (total_boxing_len + sa, thickness + sa), (-sa, thickness + sa), (-sa, -sa)],
            width_inches=total_boxing_len + sa * 2,
            height_inches=thickness + sa * 2,
            notes=f"Full perimeter: {in_to_frac(total_boxing_len)} x {in_to_frac(thickness)}",
        ))

    # Welt/piping
    if welt:
        welt_len = perimeter * 2 + 4  # Top and bottom perimeter + extra
        pieces.append(PatternPiece(
            name="Welt Cord Cover (bias cut)",
            cut_count=2,
            seam_points=[(0, 0), (welt_len, 0), (welt_len, 1.5), (0, 1.5), (0, 0)],
            cut_points=[(0, 0), (welt_len, 0), (welt_len, 1.5), (0, 1.5), (0, 0)],
            width_inches=welt_len,
            height_inches=1.5,
            grainline_vertical=False,
            notes=f"Cut on bias (45 degrees). Wrap around welt cord. May need to piece strips.",
        ))

    all_pieces_dims = [(p.width_inches, p.height_inches, p.cut_count) for p in pieces]
    fabric_area = sum(w * h * c for w, h, c in all_pieces_dims)
    yardage = _estimate_yardage(all_pieces_dims, 54)

    notes = [
        f"Box cushion: {in_to_frac(width)} W x {in_to_frac(depth)} D x {in_to_frac(thickness)} thick",
        f"Boxing perimeter: {in_to_frac(perimeter)} ({perimeter:.2f}\")",
        f"Seam allowance: {in_to_frac(seam_allowance)}",
    ]
    if t_cushion:
        notes.append(f"T-cushion: arm notches {in_to_frac(t_arm_width)} x {in_to_frac(t_arm_depth)}")
    if corner_radius > 0:
        notes.append(f"Corner radius: {in_to_frac(corner_radius)}")
    if zipper_in_back:
        notes.append("Install zipper in back boxing strip before assembling.")
    notes.extend([
        "Sew welt to top and bottom panels first (if using).",
        "Pin boxing to top panel, matching notches. Sew.",
        "Pin and sew bottom panel, leaving opening if no zipper.",
    ])

    return PatternResult(
        shape="box_cushion",
        pieces=pieces,
        total_fabric_sq_in=fabric_area,
        fabric_yardage_54=yardage,
        construction_notes=notes,
        dimensions_summary=f"{in_to_frac(width)} x {in_to_frac(depth)} x {in_to_frac(thickness)}",
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KNIFE EDGE CUSHION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def generate_knife_edge(
    width: float = 18.0,
    height: float = 18.0,
    shape: str = "square",  # square, rectangle, round, oval
    seam_allowance: float = 0.5,
    zipper: bool = True,
) -> PatternResult:
    sa = seam_allowance
    pieces = []

    if shape in ("round", "oval"):
        n_pts = 72
        seam_pts = []
        cut_pts = []
        rx, ry = width / 2, height / 2
        for i in range(n_pts + 1):
            angle = (i / n_pts) * 2 * math.pi
            seam_pts.append((rx * math.cos(angle), ry * math.sin(angle)))
            cut_pts.append(((rx + sa) * math.cos(angle), (ry + sa) * math.sin(angle)))

        pieces.append(PatternPiece(
            name=f"{'Round' if shape == 'round' else 'Oval'} Panel",
            cut_count=2,
            seam_points=seam_pts,
            cut_points=cut_pts,
            width_inches=width + sa * 2,
            height_inches=height + sa * 2,
            is_curved=True,
            notch_positions=[(rx, 0), (-rx, 0), (0, ry), (0, -ry)],
            notes=f"{'Circle' if shape == 'round' else 'Oval'}: {in_to_frac(width)} x {in_to_frac(height)}",
        ))
    else:
        seam_pts = [(0, 0), (width, 0), (width, height), (0, height), (0, 0)]
        cut_pts = [(-sa, -sa), (width + sa, -sa), (width + sa, height + sa), (-sa, height + sa), (-sa, -sa)]

        pieces.append(PatternPiece(
            name=f"{'Square' if width == height else 'Rectangle'} Panel",
            cut_count=2,
            seam_points=seam_pts,
            cut_points=cut_pts,
            width_inches=width + sa * 2,
            height_inches=height + sa * 2,
            notch_positions=[(width / 2, 0), (width / 2, height)],
            notes=f"{in_to_frac(width)} x {in_to_frac(height)}. One panel has zipper in bottom edge." if zipper else f"{in_to_frac(width)} x {in_to_frac(height)}",
        ))

    all_dims = [(p.width_inches, p.height_inches, p.cut_count) for p in pieces]
    fabric_area = sum(w * h * c for w, h, c in all_dims)
    yardage = _estimate_yardage(all_dims, 54)

    notes = [
        f"Knife edge cushion: {in_to_frac(width)} x {in_to_frac(height)}, {shape}",
        f"Cut 2 panels. Sew right sides together, leave 6-8\" opening for turning.",
    ]
    if zipper:
        notes.append("Install zipper in bottom edge of one panel before sewing panels together.")

    return PatternResult(
        shape="knife_edge",
        pieces=pieces,
        total_fabric_sq_in=fabric_area,
        fabric_yardage_54=yardage,
        construction_notes=notes,
        dimensions_summary=f"{in_to_frac(width)} x {in_to_frac(height)} {shape}",
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PDF GENERATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def generate_pdf(result: PatternResult, project_name: str = "") -> bytes:
    """Generate a printable PDF at 100% scale with tiled pages."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)

    margin = 0.5 * inch
    usable_w = LETTER_W - 2 * margin
    usable_h = LETTER_H - 2 * margin

    # Title page
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, LETTER_H - margin - 20, "Pattern Template")
    c.setFont("Helvetica", 12)
    c.drawString(margin, LETTER_H - margin - 40, f"Shape: {result.shape.replace('_', ' ').title()}")
    c.drawString(margin, LETTER_H - margin - 56, f"Dimensions: {result.dimensions_summary}")
    if project_name:
        c.drawString(margin, LETTER_H - margin - 72, f"Project: {project_name}")

    y = LETTER_H - margin - 100
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Construction Notes:")
    y -= 16
    c.setFont("Helvetica", 9)
    for note in result.construction_notes:
        if y < margin + 20:
            c.showPage()
            y = LETTER_H - margin - 20
        c.drawString(margin + 10, y, f"• {note}")
        y -= 14

    y -= 10
    c.setFont("Helvetica", 9)
    c.drawString(margin, y, f"Estimated fabric (54\" wide): {result.fabric_yardage_54:.2f} yards")
    y -= 14
    c.drawString(margin, y, f"Total fabric area: {result.total_fabric_sq_in:.1f} sq in")

    # 1" verification square on title page
    y -= 30
    c.setStrokeColor(black)
    c.setLineWidth(1)
    c.rect(margin, y - inch, inch, inch)
    c.setFont("Helvetica", 7)
    c.drawCentredString(margin + inch / 2, y - inch - 10, '1" verification square')
    c.drawCentredString(margin + inch / 2, y - inch - 20, 'Measure to verify print scale')

    # Piece summary
    y -= 50
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, "Pattern Pieces:")
    y -= 16
    c.setFont("Helvetica", 9)
    for piece in result.pieces:
        c.drawString(margin + 10, y, f"• {piece.name} — Cut {piece.cut_count} — {piece.width_inches:.2f}\" x {piece.height_inches:.2f}\"")
        y -= 14

    c.showPage()

    # Generate each piece on tiled pages
    for piece in result.pieces:
        _draw_piece_tiled(c, piece, margin, usable_w, usable_h, project_name)

    c.save()
    return buf.getvalue()


def _draw_piece_tiled(c: canvas.Canvas, piece: PatternPiece,
                      margin: float, usable_w: float, usable_h: float,
                      project_name: str):
    """Draw a pattern piece across tiled pages if it's larger than one page."""
    # Convert piece dimensions to points
    piece_w_pts = piece.width_inches * PPI
    piece_h_pts = piece.height_inches * PPI

    # Calculate grid of pages needed
    cols = max(1, math.ceil(piece_w_pts / usable_w))
    rows = max(1, math.ceil(piece_h_pts / usable_h))

    # Center offset for the piece within the total tiled area
    total_w = cols * usable_w
    total_h = rows * usable_h
    offset_x = (total_w - piece_w_pts) / 2
    offset_y = (total_h - piece_h_pts) / 2

    for row in range(rows):
        for col in range(cols):
            # Viewport for this page
            vp_x = col * usable_w - offset_x
            vp_y = row * usable_h - offset_y

            c.saveState()
            # Clip to usable area
            p = c.beginPath()
            p.rect(margin, margin, usable_w, usable_h)
            c.clipPath(p, stroke=0)

            # Transform: piece coordinates to page coordinates
            # piece (0,0) is at center of piece
            center_x = piece_w_pts / 2
            center_y = piece_h_pts / 2

            def to_page(px_in, py_in):
                """Convert piece coords (inches) to page coords (points)."""
                px = (px_in * PPI) + center_x - vp_x + margin
                py = (py_in * PPI) + center_y - vp_y + margin
                return px, py

            # Draw cutting line (solid)
            c.setStrokeColor(black)
            c.setLineWidth(1.5)
            _draw_polygon(c, piece.cut_points, to_page)

            # Draw seam line (dashed)
            c.setDash(4, 3)
            c.setStrokeColor(gray)
            c.setLineWidth(0.75)
            _draw_polygon(c, piece.seam_points, to_page)
            c.setDash()

            # Notch marks
            c.setStrokeColor(black)
            c.setLineWidth(1)
            for nx, ny in piece.notch_positions:
                px, py = to_page(nx, ny)
                c.line(px - 4, py - 4, px + 4, py + 4)
                c.line(px - 4, py + 4, px + 4, py - 4)

            # Grainline arrow (center of piece)
            if piece.grainline_vertical:
                gx, gy_top = to_page(0, piece.height_inches / 2 * 0.3 - center_y / PPI)
                _, gy_bot = to_page(0, -piece.height_inches / 2 * 0.3 + center_y / PPI)
                # Simplified: just draw a vertical arrow in the center area
                cx_page = margin + usable_w / 2
                arrow_len = min(60, usable_h * 0.3)
                cy_page = margin + usable_h / 2
                c.setStrokeColor(Color(0.6, 0.6, 0.6))
                c.setLineWidth(0.5)
                c.line(cx_page, cy_page - arrow_len / 2, cx_page, cy_page + arrow_len / 2)
                # Arrowhead
                c.line(cx_page, cy_page + arrow_len / 2, cx_page - 4, cy_page + arrow_len / 2 - 8)
                c.line(cx_page, cy_page + arrow_len / 2, cx_page + 4, cy_page + arrow_len / 2 - 8)

            c.restoreState()

            # Page info outside clip area
            c.setFont("Helvetica", 7)
            c.setFillColor(gray)
            c.drawString(margin, margin - 10, f"{piece.name} — Cut {piece.cut_count} — Page {row * cols + col + 1}/{rows * cols}")
            if project_name:
                c.drawRightString(LETTER_W - margin, margin - 10, project_name)

            # Registration marks for tiling
            if cols > 1 or rows > 1:
                c.setStrokeColor(black)
                c.setLineWidth(0.5)
                # Corner crosses
                for cx, cy in [(margin, margin), (margin + usable_w, margin),
                               (margin, margin + usable_h), (margin + usable_w, margin + usable_h)]:
                    c.line(cx - 6, cy, cx + 6, cy)
                    c.line(cx, cy - 6, cx, cy + 6)

            c.setFillColor(black)
            c.showPage()


def _draw_polygon(c: canvas.Canvas, points, to_page_fn):
    """Draw a closed polygon on the canvas."""
    if not points:
        return
    p = c.beginPath()
    px, py = to_page_fn(points[0][0], points[0][1])
    p.moveTo(px, py)
    for pt in points[1:]:
        px, py = to_page_fn(pt[0], pt[1])
        p.lineTo(px, py)
    p.close()
    c.drawPath(p, stroke=1, fill=0)


def _points_to_path(right_points, left_points):
    """Convert point lists to a path description for SVG rendering."""
    # Not used for PDF, but useful for frontend SVG
    return [("polyline", right_points), ("polyline", list(reversed(left_points)))]


def _estimate_yardage(pieces_dims: List[Tuple[float, float, int]], fabric_width: float) -> float:
    """
    Estimate fabric yardage needed.
    Simple bin-packing: lay pieces side by side across fabric width,
    stack rows as needed.
    """
    total_length = 0
    remaining_width = fabric_width
    current_row_height = 0

    # Flatten pieces by cut count
    all_pieces = []
    for w, h, count in pieces_dims:
        for _ in range(count):
            all_pieces.append((w, h))

    # Sort by height descending for better packing
    all_pieces.sort(key=lambda p: p[1], reverse=True)

    for w, h in all_pieces:
        if w > fabric_width:
            # Piece wider than fabric — needs to be placed lengthwise
            total_length += w
            # This is simplified; real layout would need more logic
            continue
        if w <= remaining_width:
            remaining_width -= w
            current_row_height = max(current_row_height, h)
        else:
            total_length += current_row_height
            remaining_width = fabric_width - w
            current_row_height = h

    total_length += current_row_height

    return total_length / 36  # inches to yards


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SVG GENERATION (for frontend preview)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def generate_svg_preview(piece: PatternPiece, view_width: int = 400, view_height: int = 500) -> str:
    """Generate SVG string for a pattern piece preview."""
    # Scale to fit view
    scale = min(
        (view_width - 40) / piece.width_inches,
        (view_height - 60) / piece.height_inches,
    )

    cx = view_width / 2
    cy = view_height / 2

    def to_svg(x, y):
        return (cx + x * scale, cy - y * scale + piece.height_inches * scale / 2)

    lines = [f'<svg viewBox="0 0 {view_width} {view_height}" xmlns="http://www.w3.org/2000/svg">']
    lines.append(f'<rect width="{view_width}" height="{view_height}" fill="#faf9f7"/>')

    # Cutting line
    if piece.cut_points:
        pts = " ".join(f"{to_svg(x, y)[0]:.1f},{to_svg(x, y)[1]:.1f}" for x, y in piece.cut_points)
        lines.append(f'<polygon points="{pts}" fill="none" stroke="#1a1a1a" stroke-width="2"/>')

    # Seam line
    if piece.seam_points:
        pts = " ".join(f"{to_svg(x, y)[0]:.1f},{to_svg(x, y)[1]:.1f}" for x, y in piece.seam_points)
        lines.append(f'<polygon points="{pts}" fill="none" stroke="#b8960c" stroke-width="1" stroke-dasharray="6,4"/>')

    # Notch marks
    for nx, ny in piece.notch_positions:
        sx, sy = to_svg(nx, ny)
        lines.append(f'<line x1="{sx-5}" y1="{sy-5}" x2="{sx+5}" y2="{sy+5}" stroke="#dc2626" stroke-width="1.5"/>')
        lines.append(f'<line x1="{sx-5}" y1="{sy+5}" x2="{sx+5}" y2="{sy-5}" stroke="#dc2626" stroke-width="1.5"/>')

    # Dimensions
    # Width dimension (top)
    w_left = to_svg(-piece.width_inches / 2 + (piece.cut_points[0][0] if piece.cut_points else 0), 0)
    w_right = to_svg(piece.width_inches / 2, 0)
    dim_y = 18
    lines.append(f'<text x="{cx}" y="{dim_y}" text-anchor="middle" font-size="11" font-family="monospace" fill="#555">{piece.width_inches:.2f}" ({in_to_frac(piece.width_inches)})</text>')

    # Height dimension (right)
    dim_x = view_width - 10
    lines.append(f'<text x="{dim_x}" y="{cy}" text-anchor="middle" font-size="11" font-family="monospace" fill="#555" transform="rotate(-90,{dim_x},{cy})">{piece.height_inches:.2f}" ({in_to_frac(piece.height_inches)})</text>')

    # Label
    lines.append(f'<text x="{cx}" y="{view_height - 12}" text-anchor="middle" font-size="10" font-family="sans-serif" fill="#999">{piece.name} — Cut {piece.cut_count}</text>')

    # Grainline arrow
    if piece.grainline_vertical:
        lines.append(f'<line x1="{cx}" y1="{cy - 30}" x2="{cx}" y2="{cy + 30}" stroke="#ccc" stroke-width="1"/>')
        lines.append(f'<polygon points="{cx},{cy-30} {cx-4},{cy-22} {cx+4},{cy-22}" fill="#ccc"/>')

    lines.append('</svg>')
    return "\n".join(lines)


def result_to_dict(result: PatternResult) -> dict:
    """Convert PatternResult to JSON-serializable dict."""
    return {
        "shape": result.shape,
        "dimensions_summary": result.dimensions_summary,
        "total_fabric_sq_in": round(result.total_fabric_sq_in, 1),
        "fabric_yardage_54": round(result.fabric_yardage_54, 2),
        "construction_notes": result.construction_notes,
        "pieces": [
            {
                "name": p.name,
                "cut_count": p.cut_count,
                "width_inches": round(p.width_inches, 2),
                "height_inches": round(p.height_inches, 2),
                "is_curved": p.is_curved,
                "notes": p.notes,
                "svg": generate_svg_preview(p),
            }
            for p in result.pieces
        ],
    }
