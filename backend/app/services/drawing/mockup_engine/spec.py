"""Structured piece specification for parametric furniture and casework mockups."""
from __future__ import annotations

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field


class SegmentSpec(BaseModel):
    """A segment or leg of a footprint (e.g. 'left', 'main', 'right', or casework bay).

    Can be straight or curved arc (specified by radius_in + sweep_deg, or chord_in + rise_in).
    """
    name: str = "main"
    length_in: float
    depth_in: Optional[float] = None  # if different from piece overall
    label: Optional[str] = None
    # Curved segment properties
    is_curved: bool = False
    radius_in: Optional[float] = None
    sweep_deg: Optional[float] = None
    chord_in: Optional[float] = None
    rise_in: Optional[float] = None


class FootprintSpec(BaseModel):
    """Plan footprint configuration."""
    shape: Literal["straight", "l_shape", "u_shape", "single", "curved", "custom"] = "straight"
    # For U-bench: left, main, right run lengths
    # For L-bench: short, long run lengths
    # For straight / single: main run length (or width_in)
    segments: List[SegmentSpec] = Field(default_factory=list)
    overall_width_in: Optional[float] = None
    overall_depth_in: Optional[float] = None
    # Thickness of back band in plan (drawing aid only, e.g. 2.0")
    back_thickness_in: float = 2.0
    # Corner geometry: square or radiused inside corners
    corner_style: Literal["square", "curved", "miter"] = "square"
    inside_corner_radius_in: float = 0.0

    def get_perimeter_vertices(self, num_arc_samples: int = 16) -> List[Tuple[float, float]]:
        """Return 2D footprint perimeter vertices, including sampled arc points for curved corners."""
        import math
        seg_dict = {s.name.lower(): s.length_in for s in self.segments}
        if self.shape == "u_shape":
            left_len = seg_dict.get("left", 37.75)
            main_len = seg_dict.get("main", 249.75)
            right_len = seg_dict.get("right", 48.5)
            x_min = -main_len / 2.0
            x_max = main_len / 2.0
            r = self.inside_corner_radius_in if self.corner_style == "curved" else 0.0

            verts: List[Tuple[float, float]] = []
            # Start at front of left leg
            verts.append((x_min, left_len))

            if r > 0 and r <= min(left_len, main_len / 2.0):
                verts.append((x_min, r))
                cx_l, cz_l = x_min + r, r
                for i in range(1, num_arc_samples):
                    ang = math.pi + (i / num_arc_samples) * (math.pi / 2.0)
                    verts.append((cx_l + r * math.cos(ang), cz_l - r * math.sin(ang)))
                verts.append((x_min + r, 0.0))
            else:
                verts.append((x_min, 0.0))

            if r > 0 and r <= min(right_len, main_len / 2.0):
                verts.append((x_max - r, 0.0))
                cx_r, cz_r = x_max - r, r
                for i in range(1, num_arc_samples):
                    ang = -math.pi / 2.0 + (i / num_arc_samples) * (math.pi / 2.0)
                    verts.append((cx_r + r * math.cos(ang), cz_r - r * math.sin(ang)))
                verts.append((x_max, r))
            else:
                verts.append((x_max, 0.0))

            # End at front of right leg
            verts.append((x_max, right_len))
            return verts

        elif self.shape == "l_shape":
            short_len = seg_dict.get("short", 95.375)
            long_len = seg_dict.get("long", 107.75)
            r = self.inside_corner_radius_in if self.corner_style == "curved" else 0.0
            verts = [(0.0, long_len)]
            if r > 0 and r <= min(short_len, long_len):
                verts.append((0.0, r))
                for i in range(1, num_arc_samples):
                    ang = math.pi + (i / num_arc_samples) * (math.pi / 2.0)
                    verts.append((r + r * math.cos(ang), r + r * math.sin(ang)))
                verts.append((r, 0.0))
            else:
                verts.append((0.0, 0.0))
            verts.append((short_len, 0.0))
            return verts

        w = self.overall_width_in or (self.segments[0].length_in if self.segments else 72.0)
        return [(-w / 2.0, 0.0), (w / 2.0, 0.0)]


class BackStyleSpec(BaseModel):
    """Backrest style configuration."""
    style: Literal[
        "plain",
        "channel",
        "tufted",
        "button_tufted",
        "horizontal_channel",
        "basketweave",
        "padded_modules",
        "none"
    ] = "plain"
    # Channel width in inches (default 12" per standard)
    channel_width_in: float = 12.0
    channel_orientation: Literal["vertical", "horizontal"] = "vertical"
    # Module dimensions for padded / basketweave modules
    module_width_in: Optional[float] = None
    module_height_in: Optional[float] = None
    # Tuft spacing
    tuft_spacing_x_in: Optional[float] = None
    tuft_spacing_y_in: Optional[float] = None
    # Net back height above seat cushion
    net_back_height_in: float = 26.75
    # Back lean / rake angle (degrees from vertical, default 0.0 vertical)
    rake_deg: float = 0.0
    back_lean_in: float = 0.0


class CushionSpec(BaseModel):
    """Seat cushion configuration."""
    style: Literal["plain", "channel", "tufted", "box", "waterfall"] = "plain"
    seat_depth_in: float = 18.0
    seat_height_in: float = 18.0  # AFF plane
    cushion_thickness_in: float = 4.0  # Nominal cushion thickness
    cushion_width_in: Optional[float] = None  # Split/run cushion width
    front_overhang_in: float = 1.0  # Cushion overhang past base/platform


class MaterialFinishSpec(BaseModel):
    """Fabric, vinyl, leather, or wood finish details."""
    material_type: Literal["fabric", "vinyl", "leather", "wood", "mdf", "metal", "com"] = "vinyl"
    name: str = "Apex (Spradling Softside) vinyl"
    color_name: str = "cognac"
    color_hex: str = "#9A5B2E"        # Primary back / upholstery color
    seat_color_hex: str = "#A8693A"   # Seat cushion color
    seam_color_hex: str = "#5E3518"   # Seam/accent color
    wood_species: Optional[str] = None  # e.g. "Walnut", "White Oak", "Maple"
    wood_finish: Optional[str] = None   # e.g. "Natural matte", "Satin lacquer"


class CarcassBoxSpec(BaseModel):
    """Casework / millwork carcass cabinet box."""
    name: str
    width_in: float
    height_in: float
    depth_in: float
    x_offset_in: float = 0.0
    y_offset_in: float = 0.0
    shelves: int = 0
    drawers: int = 0
    doors: int = 0
    door_style: Literal["slab", "shaker", "glass", "open"] = "slab"
    has_face_frame: bool = True
    cut_list: List[Dict[str, Any]] = Field(default_factory=list)


class CaseworkSpec(BaseModel):
    """WoodCraft casework / wall unit details."""
    overall_width_in: float
    overall_height_in: float
    overall_depth_in: float
    boxes: List[CarcassBoxSpec] = Field(default_factory=list)
    countertop_thickness_in: float = 1.5
    countertop_height_in: Optional[float] = None  # e.g. 36.0 for base cabinets
    toe_kick_height_in: float = 4.0
    toe_kick_depth_in: float = 3.0
    wood_species: str = "Walnut"
    finish: str = "Natural satin"
    materials: List[Dict[str, Any]] = Field(default_factory=list)


class ArmSpec(BaseModel):
    """Armrest configuration (for chairs, sofas, club chairs)."""
    has_arms: bool = False
    arm_width_in: float = 3.5
    arm_height_in: float = 24.0  # Height AFF plane
    arm_style: Literal["straight", "track", "rolled", "flared"] = "track"


class PieceSpec(BaseModel):
    """Complete structured parametric specification for any furniture or casework piece."""
    piece_id: Optional[str] = None
    name: str = "Custom Piece"
    piece_type: Literal[
        "banquette",
        "bench",
        "chair",
        "stool",
        "headboard",
        "sofa",
        "wall_unit",
        "cabinet",
        "credenza",
        "millwork",
        "custom"
    ] = "banquette"
    
    # Metadata
    client_name: str = "Client"
    client_address: Optional[str] = None
    project_name: str = "Project"
    quote_number: str = "EST-2026-000"
    status: str = "NOT SENT"
    business_unit: Literal["workroom", "woodcraft"] = "workroom"
    billed_by: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
    
    # Footprint & overall
    footprint: FootprintSpec = Field(default_factory=FootprintSpec)
    
    # Upholstery components (for seating, headboard, etc.)
    back: BackStyleSpec = Field(default_factory=BackStyleSpec)
    cushion: CushionSpec = Field(default_factory=CushionSpec)
    arm: ArmSpec = Field(default_factory=ArmSpec)
    material: MaterialFinishSpec = Field(default_factory=MaterialFinishSpec)
    
    # Casework components (for wall units, credenzas, cabinets)
    casework: Optional[CaseworkSpec] = None

    # Side section option
    include_section: bool = True
