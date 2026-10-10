"""
Willard CST-23 3D Assembly Model, Layer Engine & CNC Production Service.

Business Unit: WoodCraft by Empire
Client: Maggie O'Neill / The Willard InterContinental (Scotch Bar CST-23)
Reviewed Custom Piece: Custom rules take precedence over general defaults.

Key Specifications:
  - Geometry: Front R37.07", Rear R63.82", Sweep 77.47 deg, Chord 79.87", Depth 26.75", Crown 53"
  - Channels: 8 vertical wedge back channels (4 per half, ~9 5/32" wide along back arc)
  - Rules:
      1. Wood/board cut = true size, no add-ons.
      2. Foam cut = same as wood cut.
      3. Fabric cut = foam/channel width plus 2 to 3 inches for stapling.
      4. Always list wood cut and fabric cut as separate labeled sizes.
      5. Fractions only for all dimensions and cut lists.
  - Armrests: Laminated END arm vs Slide-in, plus upholstered/fringe options.
  - Cut Sheets: Revised pack nests on 8 sheets (artifact previously stated 9),
                files in /workspace/willard_cst23_rev/ on Chief e's box.
  - Open Items: Channel height range, empty R24 dado pocket, foam/board thickness.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def format_fraction(val: float | int | None, max_denom: int = 32) -> str:
    """Format decimal inches into exact fractions (fractions only).

    Examples:
        9.15625 -> 9 5/32"
        2.5     -> 2 1/2"
        36.0    -> 36"
        0.75    -> 3/4"
    """
    if val is None:
        return ""
    val_f = float(val)
    if abs(val_f) < 1e-6:
        return '0"'

    sign = "-" if val_f < 0 else ""
    val_f = abs(val_f)

    units = round(val_f * max_denom)
    whole = units // max_denom
    rem = units - whole * max_denom

    if rem == 0:
        return f'{sign}{whole}"' if whole else f'{sign}0"'

    g = math.gcd(rem, max_denom)
    n = rem // g
    d = max_denom // g

    if whole:
        return f'{sign}{whole} {n}/{d}"'
    return f'{sign}{n}/{d}"'


class LayerConfig(BaseModel):
    back_foam_enabled: bool = True
    back_foam_thickness: float = Field(default=2.0, ge=0.5, le=4.0)
    back_fabric_enabled: bool = True
    back_fabric_material: str = "GP&J Baker Nympheus Velvet Emerald BP10814-2"
    seat_foam_enabled: bool = True
    seat_foam_thickness: float = Field(default=5.0, ge=1.0, le=7.0)
    seat_fabric_enabled: bool = True
    seat_fabric_material: str = "Keyston Bros Vintage Ale SVI001 Vinyl"
    show_frame: bool = False
    spring_seat_deck: bool = True


class ArmrestConfig(BaseModel):
    arm_type: str = Field(default="laminated_end", description="laminated_end or slide_in")
    upholstered: bool = Field(default=True, description="Upholstered face vs exposed wood")
    fringe: bool = Field(default=True, description="Fabricut Rupi 158 6in bullion fringe returns")
    stock_thickness: float = Field(default=1.5, description="Thickness in inches")


class ChannelControlInput(BaseModel):
    channel_count: int = Field(default=8, ge=4, le=16)
    channel_width: float = Field(default=9.15625, description="Nominal width 9 5/32 in")
    channel_height: float = Field(default=36.0, description="Nominal height 36 in (range 24-38 in)")
    stapling_allowance: float = Field(default=2.5, ge=2.0, le=3.0, description="2 to 3 inches for stapling")
    channel_depth: float = Field(default=2.0, description="Foam thickness (nominal 2 in)")


class CutScheduleItem(BaseModel):
    part_id: str
    part_name: str
    quantity: int
    category: str  # wood, foam, fabric, hardware
    wood_cut_size: str
    foam_cut_size: str
    fabric_cut_size: str
    raw_wood_dims: Dict[str, float]
    raw_fabric_dims: Dict[str, float]
    material: str
    notes: str


class WillardCST23Spec(BaseModel):
    project_id: str = "WC-PRJ-CST23"
    project_name: str = "Willard CST-23 Scotch Bar Curved Banquette"
    business_unit: str = "WoodCraft by Empire"
    client: str = "Maggie O'Neill / The Willard InterContinental"
    location: str = "5124 Frolich Ln, Hyattsville, MD 20781"
    status: str = "Reviewed Custom Piece"
    reviewed_rule_notice: str = (
        "Willard CST-23 is a reviewed custom piece; general rules do not override it. "
        "Wood/board cut = true size, no add-ons. Foam cut = same as wood cut. "
        "Fabric cut = foam/channel width plus 2 to 3 inches for stapling. "
        "Always list wood cut and fabric cut as separate labeled sizes. Fractions only."
    )
    dimensions: Dict[str, str]
    layers: LayerConfig
    armrests: ArmrestConfig
    channels: ChannelControlInput
    cut_schedule: List[CutScheduleItem]
    sheet_nesting: Dict[str, Any]
    open_items: List[Dict[str, str]]


# Standard 25 parts schedule across 8 CNC nested sheets
NESTED_SHEETS_DATA = {
    "total_sheets": 8,
    "sheet_material": "3/4\" Baltic Birch (48\" × 96\")",
    "artifact_vs_revised_note": "Revised pack nests on 8 sheets (Claude artifact previously stated 9).",
    "box_file_paths": {
        "base_directory": "/workspace/willard_cst23_rev/",
        "cut_list_pdf": "/workspace/willard_cst23_rev/Willard_CST23_RevPack_CutList.pdf",
        "nested_svgs_dir": "/workspace/willard_cst23_rev/sheets/",
        "nested_svg_files": [f"/workspace/willard_cst23_rev/sheets/sheet_{i:02d}.svg" for i in range(1, 9)],
        "zip_pack": "/workspace/willard_cst23_rev/Willard_CST23_Revised_Pack.zip",
    },
    "sheets": [
        {
            "sheet_num": 1,
            "sheet_title": "Sheet 1 of 8: Base Plates & Bottom Rail Ribs",
            "material": "3/4\" Baltic Birch 48\" × 96\"",
            "parts_count": 3,
            "parts": [
                {"part_id": "BP-01", "name": "Curved Base Bottom Plate (Left)", "size": "44 1/2\" × 26 3/4\"", "process": "CNC Route"},
                {"BP-02": "BP-02", "name": "Curved Base Bottom Plate (Right)", "size": "44 1/2\" × 26 3/4\"", "process": "CNC Route"},
                {"part_id": "BR-01", "name": "Front Rail Support Rib A", "size": "38\" × 11 1/4\"", "process": "CNC Route"},
            ]
        },
        {
            "sheet_num": 2,
            "sheet_title": "Sheet 2 of 8: Deck Substrate & Sinuous Spring Rails",
            "material": "3/4\" Baltic Birch 48\" × 96\"",
            "parts_count": 4,
            "parts": [
                {"part_id": "DK-01", "name": "Radial Seat Deck Substrate (Left)", "size": "42 3/8\" × 24 3/4\"", "process": "CNC Route"},
                {"part_id": "DK-02", "name": "Radial Seat Deck Substrate (Right)", "size": "42 3/8\" × 24 3/4\"", "process": "CNC Route"},
                {"part_id": "SR-01", "name": "Sinuous Spring Front Anchor Rail", "size": "41 1/2\" × 3 1/2\"", "process": "CNC Route"},
                {"part_id": "SR-02", "name": "Sinuous Spring Rear Anchor Rail", "size": "41 1/2\" × 3 1/2\"", "process": "CNC Route"},
            ]
        },
        {
            "sheet_num": 3,
            "sheet_title": "Sheet 3 of 8: Radial Frame Joists J1–J5",
            "material": "3/4\" Baltic Birch 48\" × 96\"",
            "parts_count": 5,
            "parts": [
                {"part_id": "J-01", "name": "Radial Joist J1 (Left End)", "size": "26\" × 11 1/4\"", "process": "CNC Route"},
                {"part_id": "J-02", "name": "Radial Joist J2", "size": "24 3/4\" × 11 1/4\"", "process": "CNC Route"},
                {"part_id": "J-03", "name": "Radial Joist J3", "size": "24 3/4\" × 11 1/4\"", "process": "CNC Route"},
                {"part_id": "J-04", "name": "Radial Joist J4", "size": "24 3/4\" × 11 1/4\"", "process": "CNC Route"},
                {"part_id": "J-05", "name": "Radial Joist J5 (Center Splice Left)", "size": "24 3/4\" × 11 1/4\"", "process": "CNC Route"},
            ]
        },
        {
            "sheet_num": 4,
            "sheet_title": "Sheet 4 of 8: Radial Frame Joists J6–J9 & Blocking",
            "material": "3/4\" Baltic Birch 48\" × 96\"",
            "parts_count": 4,
            "parts": [
                {"part_id": "J-06", "name": "Radial Joist J6 (Center Splice Right)", "size": "24 3/4\" × 11 1/4\"", "process": "CNC Route"},
                {"part_id": "J-07", "name": "Radial Joist J7", "size": "24 3/4\" × 11 1/4\"", "process": "CNC Route"},
                {"part_id": "J-08", "name": "Radial Joist J8", "size": "24 3/4\" × 11 1/4\"", "process": "CNC Route"},
                {"part_id": "J-09", "name": "Radial Joist J9 (Right End)", "size": "26\" × 11 1/4\"", "process": "CNC Route"},
            ]
        },
        {
            "sheet_num": 5,
            "sheet_title": "Sheet 5 of 8: Channel Back Boards CH-1 to CH-4 (Left Unit)",
            "material": "3/4\" Baltic Birch 48\" × 96\"",
            "parts_count": 4,
            "parts": [
                {"part_id": "CHB-01", "name": "Channel Back Board #1", "size": "9 5/32\" × 36\"", "process": "CNC Route / Bevel"},
                {"part_id": "CHB-02", "name": "Channel Back Board #2", "size": "9 5/32\" × 36\"", "process": "CNC Route / Bevel"},
                {"part_id": "CHB-03", "name": "Channel Back Board #3", "size": "9 5/32\" × 36\"", "process": "CNC Route / Bevel"},
                {"part_id": "CHB-04", "name": "Channel Back Board #4", "size": "9 5/32\" × 36\"", "process": "CNC Route / Bevel"},
            ]
        },
        {
            "sheet_num": 6,
            "sheet_title": "Sheet 6 of 8: Channel Back Boards CH-5 to CH-8 (Right Unit)",
            "material": "3/4\" Baltic Birch 48\" × 96\"",
            "parts_count": 4,
            "parts": [
                {"part_id": "CHB-05", "name": "Channel Back Board #5", "size": "9 5/32\" × 36\"", "process": "CNC Route / Bevel"},
                {"part_id": "CHB-06", "name": "Channel Back Board #6", "size": "9 5/32\" × 36\"", "process": "CNC Route / Bevel"},
                {"part_id": "CHB-07", "name": "Channel Back Board #7", "size": "9 5/32\" × 36\"", "process": "CNC Route / Bevel"},
                {"part_id": "CHB-08", "name": "Channel Back Board #8", "size": "9 5/32\" × 36\"", "process": "CNC Route / Bevel"},
            ]
        },
        {
            "sheet_num": 7,
            "sheet_title": "Sheet 7 of 8: Vertical Stood Ribs R1–R9 (Back Rake Skeleton)",
            "material": "3/4\" Baltic Birch 48\" × 96\"",
            "parts_count": 3,
            "parts": [
                {"part_id": "VR-01", "name": "Vertical Rib Stack Left (R1-R3)", "size": "44\" × 8\"", "process": "CNC Route 10° Rake"},
                {"part_id": "VR-02", "name": "Vertical Rib Stack Center (R4-R6)", "size": "44\" × 8\"", "process": "CNC Route 10° Rake"},
                {"part_id": "VR-03", "name": "Vertical Rib Stack Right (R7-R9)", "size": "44\" × 8\"", "process": "CNC Route 10° Rake"},
            ]
        },
        {
            "sheet_num": 8,
            "sheet_title": "Sheet 8 of 8: Armrest End Components (Laminated / Slide-In)",
            "material": "3/4\" Baltic Birch 48\" × 96\"",
            "parts_count": 2,
            "parts": [
                {"part_id": "ARM-L", "name": "Armrest Assembly Blank (Left)", "size": "27 5/8\" × 44\"", "process": "CNC Route Profile"},
                {"part_id": "ARM-R", "name": "Armrest Assembly Blank (Right)", "size": "27 5/8\" × 44\"", "process": "CNC Route Profile"},
            ]
        },
    ]
}

OPEN_ITEMS_DATA = [
    {
        "id": "ITEM-1",
        "title": "Channel height range",
        "status": "OPEN",
        "current_spec": 'Nominal 36" back channel height (above 17" seat = 53" overall crown height)',
        "range": '24" to 38"',
        "impact": "Field wall conditions at The Willard Scotch Bar and the 82\" overall cap require verifying clear height under sconces/moldings.",
        "rule_note": "Wood cut and foam cut are 1:1 true size; fabric cut adds 2\" to 3\" for top/bottom stapling."
    },
    {
        "id": "ITEM-2",
        "title": "Empty R24 dado pocket",
        "status": "OPEN",
        "current_spec": 'R24 circular dado pocket located in the base curved rib assembly',
        "range": '24" radius pocket',
        "impact": "Resolve whether pocket is designated for wiring / LED under-bench light conduit chase, weight reduction, or alignment spline.",
        "rule_note": "Do not remove from CNC cut files until confirmed by lead fabricator."
    },
    {
        "id": "ITEM-3",
        "title": "Foam/board thickness",
        "status": "OPEN",
        "current_spec": 'Back channels: 1/2" or 3/4" Baltic birch board + 2" HR foam. Seat: 5" multi-density foam stack.',
        "range": 'Back foam: 1" to 4" (nominal 2"). Seat foam: 2" to 6" (nominal 5"). Board: 1/2" vs 3/4".',
        "impact": "Affects inside seat depth clearance (26\" radial) and back rake feel. Changing foam thickness changes fabric wrap dimensions.",
        "rule_note": "Foam cut = exact wood board cut size. Fabric cut = channel width + 2\" to 3\" for stapling wrap."
    }
]


def calculate_cut_schedule(
    channel_count: int = 8,
    channel_width: float = 9.15625,
    channel_height: float = 36.0,
    stapling_allowance: float = 2.5,
    channel_foam_thickness: float = 2.0,
    seat_foam_thickness: float = 5.0,
    arm_type: str = "laminated_end",
    upholstered_arm: bool = True,
    fringe: bool = True,
) -> List[CutScheduleItem]:
    """Calculate cut schedule strictly enforcing the CST-23 rules:

    1. Wood/board cut = true size, no add-ons.
    2. Foam cut = same as wood cut.
    3. Fabric cut = foam/channel width plus 2 to 3 inches for stapling.
    4. Always list wood cut and fabric cut as separate labeled sizes.
    5. Fractions only.
    """
    stapling_allowance = max(2.0, min(3.0, stapling_allowance))

    items: List[CutScheduleItem] = []

    # 1. Back channels (CH-1 to CH-N)
    wood_w = channel_width
    wood_h = channel_height
    fabric_w = wood_w + stapling_allowance
    fabric_h = wood_h + stapling_allowance

    wood_str = f"{format_fraction(wood_w)} × {format_fraction(wood_h)}"
    foam_str = f"{format_fraction(wood_w)} × {format_fraction(wood_h)} × {format_fraction(channel_foam_thickness)}"
    fabric_str = f"{format_fraction(fabric_w)} × {format_fraction(fabric_h)}"

    for i in range(1, channel_count + 1):
        items.append(CutScheduleItem(
            part_id=f"CH-{i:02d}",
            part_name=f"Channel Back #{i}",
            quantity=1,
            category="channel",
            wood_cut_size=wood_str,
            foam_cut_size=foam_str,
            fabric_cut_size=fabric_str,
            raw_wood_dims={"width": wood_w, "height": wood_h, "thickness": 0.75},
            raw_fabric_dims={"width": fabric_w, "height": fabric_h, "stapling_allowance": stapling_allowance},
            material="GP&J Baker Nympheus Velvet / High Resilience Foam",
            notes=f"Wood = true size ({format_fraction(wood_w)}). Foam = exact same ({format_fraction(wood_w)}). Fabric = +{format_fraction(stapling_allowance)} for stapling."
        ))

    # 2. Seat Cushions (Left & Right halves)
    seat_wood_w = 41.5
    seat_wood_d = 24.75
    seat_fabric_w = seat_wood_w + stapling_allowance
    seat_fabric_d = seat_wood_d + stapling_allowance

    seat_wood_str = f"{format_fraction(seat_wood_w)} × {format_fraction(seat_wood_d)}"
    seat_foam_str = f"{format_fraction(seat_wood_w)} × {format_fraction(seat_wood_d)} × {format_fraction(seat_foam_thickness)}"
    seat_fabric_str = f"{format_fraction(seat_fabric_w)} × {format_fraction(seat_fabric_d)}"

    items.append(CutScheduleItem(
        part_id="CUSH-L",
        part_name="Seat Cushion Deck (Left Half)",
        quantity=1,
        category="seat",
        wood_cut_size=seat_wood_str,
        foam_cut_size=seat_foam_str,
        fabric_cut_size=seat_fabric_str,
        raw_wood_dims={"width": seat_wood_w, "height": seat_wood_d, "thickness": 0.75},
        raw_fabric_dims={"width": seat_fabric_w, "height": seat_fabric_d, "stapling_allowance": stapling_allowance},
        material="Keyston Bros Vintage Ale SVI001 Vinyl",
        notes=f"Seat foam thickness {format_fraction(seat_foam_thickness)}. Wood cut {seat_wood_str}, fabric cut {seat_fabric_str} with {format_fraction(stapling_allowance)} stapling allowance."
    ))

    items.append(CutScheduleItem(
        part_id="CUSH-R",
        part_name="Seat Cushion Deck (Right Half)",
        quantity=1,
        category="seat",
        wood_cut_size=seat_wood_str,
        foam_cut_size=seat_foam_str,
        fabric_cut_size=seat_fabric_str,
        raw_wood_dims={"width": seat_wood_w, "height": seat_wood_d, "thickness": 0.75},
        raw_fabric_dims={"width": seat_fabric_w, "height": seat_fabric_d, "stapling_allowance": stapling_allowance},
        material="Keyston Bros Vintage Ale SVI001 Vinyl",
        notes=f"Seat foam thickness {format_fraction(seat_foam_thickness)}. Wood cut {seat_wood_str}, fabric cut {seat_fabric_str} with {format_fraction(stapling_allowance)} stapling allowance."
    ))

    # 3. Armrests (Left & Right)
    arm_w = 27.625
    arm_h = 44.0
    arm_fabric_w = arm_w + (stapling_allowance if upholstered_arm else 0.0)
    arm_fabric_h = arm_h + (stapling_allowance if upholstered_arm else 0.0)

    arm_wood_str = f"{format_fraction(arm_w)} × {format_fraction(arm_h)}"
    arm_foam_str = f"{format_fraction(arm_w)} × {format_fraction(arm_h)} × 1/2\"" if upholstered_arm else "N/A (Exposed Laminated Wood)"
    arm_fabric_str = f"{format_fraction(arm_fabric_w)} × {format_fraction(arm_fabric_h)}" if upholstered_arm else "N/A (Exposed Wood Finish)"

    items.append(CutScheduleItem(
        part_id="ARM-01",
        part_name=f"End Armrest Left ({arm_type.replace('_', ' ').title()})",
        quantity=1,
        category="armrest",
        wood_cut_size=arm_wood_str,
        foam_cut_size=arm_foam_str,
        fabric_cut_size=arm_fabric_str,
        raw_wood_dims={"width": arm_w, "height": arm_h, "thickness": 1.5},
        raw_fabric_dims={"width": arm_fabric_w, "height": arm_fabric_h, "stapling_allowance": stapling_allowance if upholstered_arm else 0.0},
        material="3/4\" Baltic Birch Laminate" + (" with Vinyl Wrap" if upholstered_arm else " Finished Edge"),
        notes=f"Mode: {arm_type}. Upholstered: {upholstered_arm}. Fringe Return: {fringe}."
    ))

    items.append(CutScheduleItem(
        part_id="ARM-02",
        part_name=f"End Armrest Right ({arm_type.replace('_', ' ').title()})",
        quantity=1,
        category="armrest",
        wood_cut_size=arm_wood_str,
        foam_cut_size=arm_foam_str,
        fabric_cut_size=arm_fabric_str,
        raw_wood_dims={"width": arm_w, "height": arm_h, "thickness": 1.5},
        raw_fabric_dims={"width": arm_fabric_w, "height": arm_fabric_h, "stapling_allowance": stapling_allowance if upholstered_arm else 0.0},
        material="3/4\" Baltic Birch Laminate" + (" with Vinyl Wrap" if upholstered_arm else " Finished Edge"),
        notes=f"Mode: {arm_type}. Upholstered: {upholstered_arm}. Fringe Return: {fringe}."
    ))

    # 4. Fringe trim schedule
    if fringe:
        items.append(CutScheduleItem(
            part_id="TRIM-01",
            part_name="Front Face Fringe Band (Rupi 158)",
            quantity=1,
            category="trim",
            wood_cut_size="N/A (Fabric Trim)",
            foam_cut_size="N/A",
            fabric_cut_size="84\" Linear × 6\" Drop",
            raw_wood_dims={"width": 0, "height": 0, "thickness": 0},
            raw_fabric_dims={"width": 84.0, "height": 6.0, "stapling_allowance": 0},
            material="Fabricut Rupi 158 6\" Bullion Fringe",
            notes="Header at 7\" AFF, 6\" drop with 1\" floor clearance across curved front arc."
        ))
        items.append(CutScheduleItem(
            part_id="TRIM-02",
            part_name="End Arm Fringe Returns (Left + Right)",
            quantity=2,
            category="trim",
            wood_cut_size="N/A (Fabric Trim)",
            foam_cut_size="N/A",
            fabric_cut_size="27\" Linear × 6\" Drop",
            raw_wood_dims={"width": 0, "height": 0, "thickness": 0},
            raw_fabric_dims={"width": 27.0, "height": 6.0, "stapling_allowance": 0},
            material="Fabricut Rupi 158 6\" Bullion Fringe",
            notes="Returns along both end arm bases matching front header 7\" AFF."
        ))

    return items


def get_full_willard_spec(
    channel_count: int = 8,
    channel_width: float = 9.15625,
    channel_height: float = 36.0,
    stapling_allowance: float = 2.5,
    channel_foam_thickness: float = 2.0,
    seat_foam_thickness: float = 5.0,
    arm_type: str = "laminated_end",
    upholstered_arm: bool = True,
    fringe: bool = True,
    show_frame: bool = False,
) -> WillardCST23Spec:
    """Return the complete Willard CST-23 project specification."""
    cut_schedule = calculate_cut_schedule(
        channel_count=channel_count,
        channel_width=channel_width,
        channel_height=channel_height,
        stapling_allowance=stapling_allowance,
        channel_foam_thickness=channel_foam_thickness,
        seat_foam_thickness=seat_foam_thickness,
        arm_type=arm_type,
        upholstered_arm=upholstered_arm,
        fringe=fringe,
    )

    dimensions_formatted = {
        "chord": format_fraction(79.875),
        "total_back_arc": format_fraction(83.5),
        "front_radius": format_fraction(37.0625),
        "rear_radius": format_fraction(63.8125),
        "seat_depth": format_fraction(26.75),
        "seat_height": format_fraction(17.0),
        "back_height": format_fraction(channel_height),
        "overall_height": format_fraction(17.0 + channel_height),
        "crown_height": format_fraction(53.0),
        "separation_gap": format_fraction(1.5),
        "floor_clearance": format_fraction(1.0),
        "fringe_header_aff": format_fraction(7.0),
        "fringe_drop": format_fraction(6.0),
        "channel_width": format_fraction(channel_width),
        "channel_height": format_fraction(channel_height),
        "stapling_allowance": format_fraction(stapling_allowance),
        "channel_foam_thickness": format_fraction(channel_foam_thickness),
        "seat_foam_thickness": format_fraction(seat_foam_thickness),
    }

    return WillardCST23Spec(
        dimensions=dimensions_formatted,
        layers=LayerConfig(
            back_foam_enabled=True,
            back_foam_thickness=channel_foam_thickness,
            back_fabric_enabled=True,
            seat_foam_enabled=True,
            seat_foam_thickness=seat_foam_thickness,
            seat_fabric_enabled=True,
            show_frame=show_frame,
            spring_seat_deck=True,
        ),
        armrests=ArmrestConfig(
            arm_type=arm_type,
            upholstered=upholstered_arm,
            fringe=fringe,
        ),
        channels=ChannelControlInput(
            channel_count=channel_count,
            channel_width=channel_width,
            channel_height=channel_height,
            stapling_allowance=stapling_allowance,
            channel_depth=channel_foam_thickness,
        ),
        cut_schedule=cut_schedule,
        sheet_nesting=NESTED_SHEETS_DATA,
        open_items=OPEN_ITEMS_DATA,
    )
