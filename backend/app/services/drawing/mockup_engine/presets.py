"""Presets and template generators for straight bench, L bench, U bench, single chair, and WoodCraft wall unit."""
from __future__ import annotations

from typing import Optional, Dict, Any
from app.services.drawing.mockup_engine.spec import (
    PieceSpec, FootprintSpec, SegmentSpec, BackStyleSpec, CushionSpec,
    MaterialFinishSpec, CaseworkSpec, CarcassBoxSpec, ArmSpec,
)


def marleys_u_and_l_preset() -> Dict[str, PieceSpec]:
    """Return exact PieceSpecs reproducing Marley's Hyattsville U and L banquettes."""
    u_spec = PieceSpec(
        piece_id="marleys_u_bench",
        name="Marley's U Bench",
        piece_type="banquette",
        client_name="Marley's",
        client_address="Hyattsville, MD",
        project_name="Marley's channel backs",
        quote_number="EST-2026-299",
        status="NOT SENT",
        business_unit="workroom",
        footprint=FootprintSpec(
            shape="u_shape",
            segments=[
                SegmentSpec(name="left", length_in=37.75),
                SegmentSpec(name="main", length_in=249.75),
                SegmentSpec(name="right", length_in=48.5),
            ],
            back_thickness_in=2.0,
        ),
        back=BackStyleSpec(
            style="channel",
            channel_width_in=12.0,
            net_back_height_in=26.75,
            rake_deg=0.0,
        ),
        cushion=CushionSpec(
            seat_depth_in=16.0,
            seat_height_in=18.0,
            cushion_thickness_in=4.0,
            front_overhang_in=1.25,
        ),
        material=MaterialFinishSpec(
            material_type="vinyl",
            name="Apex (Spradling Softside) vinyl",
            color_name="cognac",
            color_hex="#9A5B2E",
            seat_color_hex="#A8693A",
            seam_color_hex="#5E3518",
        ),
    )

    l_spec = PieceSpec(
        piece_id="marleys_l_bench",
        name="Marley's L Bench",
        piece_type="banquette",
        client_name="Marley's",
        client_address="Hyattsville, MD",
        project_name="Marley's channel backs",
        quote_number="EST-2026-299",
        status="NOT SENT",
        business_unit="workroom",
        footprint=FootprintSpec(
            shape="l_shape",
            segments=[
                SegmentSpec(name="short", length_in=95.375),
                SegmentSpec(name="long", length_in=107.75),
            ],
            back_thickness_in=2.0,
        ),
        back=BackStyleSpec(
            style="channel",
            channel_width_in=12.0,
            net_back_height_in=26.75,
            rake_deg=0.0,
        ),
        cushion=CushionSpec(
            seat_depth_in=16.0,
            seat_height_in=18.0,
            cushion_thickness_in=4.0,
            front_overhang_in=1.25,
        ),
        material=MaterialFinishSpec(
            material_type="vinyl",
            name="Apex (Spradling Softside) vinyl",
            color_name="cognac",
            color_hex="#9A5B2E",
            seat_color_hex="#A8693A",
            seam_color_hex="#5E3518",
        ),
    )
    return {"u_bench": u_spec, "l_bench": l_spec}


def marleys_u_with_curved_corners_preset() -> PieceSpec:
    """Marley's U banquette with 24" inside radius curved corners."""
    base_u = marleys_u_and_l_preset()["u_bench"]
    u_curved = base_u.model_copy(deep=True)
    u_curved.piece_id = "marleys_u_bench_curved_corners"
    u_curved.name = "Marley's U Bench (24\" Curved Corners)"
    u_curved.footprint.corner_style = "curved"
    u_curved.footprint.inside_corner_radius_in = 24.0
    u_curved.notes = [
        "Inside corners radiused to 24\" inside radius.",
        "Vertical channel back fans along corner radial sectors.",
    ]
    return u_curved


def straight_bench_preset(
    length_in: float = 72.0,
    seat_depth_in: float = 20.0,
    back_height_in: float = 24.0,
    back_style: str = "channel",
    channel_width_in: float = 12.0,
    name: str = "Straight Dining Bench",
    color_hex: str = "#8B5A2B",
) -> PieceSpec:
    """Preset for a straight bench or banquette."""
    return PieceSpec(
        name=name,
        piece_type="bench",
        footprint=FootprintSpec(
            shape="straight",
            segments=[SegmentSpec(name="main", length_in=length_in)],
            overall_width_in=length_in,
            overall_depth_in=seat_depth_in + 3.0,
        ),
        back=BackStyleSpec(
            style=back_style,
            channel_width_in=channel_width_in,
            net_back_height_in=back_height_in,
        ),
        cushion=CushionSpec(
            seat_depth_in=seat_depth_in,
            seat_height_in=18.0,
            cushion_thickness_in=4.0,
        ),
        material=MaterialFinishSpec(
            material_type="fabric",
            name="Custom Upholstery Fabric",
            color_name="warm brown",
            color_hex=color_hex,
            seat_color_hex=color_hex,
        ),
    )


def l_bench_preset(
    short_leg_in: float = 60.0,
    long_leg_in: float = 84.0,
    seat_depth_in: float = 18.0,
    back_height_in: float = 24.0,
    back_style: str = "channel",
    name: str = "L-Shaped Corner Banquette",
) -> PieceSpec:
    """Preset for an L-shaped corner banquette."""
    return PieceSpec(
        name=name,
        piece_type="banquette",
        footprint=FootprintSpec(
            shape="l_shape",
            segments=[
                SegmentSpec(name="short", length_in=short_leg_in),
                SegmentSpec(name="long", length_in=long_leg_in),
            ],
            back_thickness_in=3.0,
        ),
        back=BackStyleSpec(
            style=back_style,
            channel_width_in=12.0,
            net_back_height_in=back_height_in,
        ),
        cushion=CushionSpec(
            seat_depth_in=seat_depth_in,
            seat_height_in=18.0,
        ),
    )


def u_bench_preset(
    left_leg_in: float = 48.0,
    main_leg_in: float = 120.0,
    right_leg_in: float = 48.0,
    seat_depth_in: float = 18.0,
    back_height_in: float = 24.0,
    name: str = "U-Shaped Booth Banquette",
) -> PieceSpec:
    """Preset for a U-shaped booth banquette."""
    return PieceSpec(
        name=name,
        piece_type="banquette",
        footprint=FootprintSpec(
            shape="u_shape",
            segments=[
                SegmentSpec(name="left", length_in=left_leg_in),
                SegmentSpec(name="main", length_in=main_leg_in),
                SegmentSpec(name="right", length_in=right_leg_in),
            ],
            back_thickness_in=3.0,
        ),
        back=BackStyleSpec(
            style="channel",
            channel_width_in=12.0,
            net_back_height_in=back_height_in,
        ),
        cushion=CushionSpec(
            seat_depth_in=seat_depth_in,
            seat_height_in=18.0,
        ),
    )


def single_chair_preset(
    width_in: float = 34.0,
    depth_in: float = 30.0,
    seat_depth_in: Optional[float] = None,
    seat_height_in: float = 18.0,
    back_height_in: float = 22.0,
    rake_deg: float = 8.0,
    back_style: str = "tufted",
    name: str = "Upholstered Club Chair",
    has_arms: bool = True,
    arm_width_in: float = 4.0,
    arm_height_in: float = 24.0,
    client_name: str = "Private Client",
    client_address: str = "McLean, VA",
) -> PieceSpec:
    """Preset for an upholstered club chair or armchair with arms.
    
    Seat depth defaults to 26" (depth 30" - 4" back thickness), agreeing across plan and section.
    Back profile includes proper rake angle (default 8 deg).
    """
    actual_seat_depth = seat_depth_in if seat_depth_in is not None else (depth_in - 4.0)
    actual_overall_depth = depth_in if seat_depth_in is None else (actual_seat_depth + 4.0)
    return PieceSpec(
        name=name,
        piece_type="chair",
        client_name=client_name,
        client_address=client_address,
        quote_number="EST-2026-312",
        status="NOT SENT",
        footprint=FootprintSpec(
            shape="single",
            segments=[SegmentSpec(name="main", length_in=width_in)],
            overall_width_in=width_in,
            overall_depth_in=actual_overall_depth,
            back_thickness_in=4.0,
        ),
        back=BackStyleSpec(
            style=back_style,
            net_back_height_in=back_height_in,
            tuft_spacing_x_in=6.0,
            tuft_spacing_y_in=6.0,
            rake_deg=rake_deg,
        ),
        cushion=CushionSpec(
            seat_depth_in=actual_seat_depth,
            seat_height_in=seat_height_in,
            cushion_thickness_in=5.0,
        ),
        arm=ArmSpec(
            has_arms=has_arms,
            arm_width_in=arm_width_in,
            arm_height_in=arm_height_in,
            arm_style="track",
        ),
        material=MaterialFinishSpec(
            material_type="fabric",
            name="Textured Velvet",
            color_name="emerald green",
            color_hex="#1B4D3E",
            seat_color_hex="#225F4D",
            seam_color_hex="#0D2E24",
        ),
    )


def woodcraft_wall_unit_preset(
    from_craftforge_design: Optional[Dict[str, Any]] = None,
    name: str = "WoodCraft Custom Built-In Wall Unit",
    wood_species: str = "Black Walnut",
    total_width_in: float = 108.0,
    total_height_in: float = 84.0,
    depth_in: float = 20.0,
) -> PieceSpec:
    """Preset for a WoodCraft millwork wall unit / bookcase / credenza cabinet.

    Integrates with WoodCraft / CraftForge design data (materials, cuts, boxes) when provided.
    """
    materials_list = []
    finish = "Natural Hand-Rubbed Oil Satin"
    client_name = "Private Residence"
    client_address = "Potomac, MD"
    quote_number = "WC-2026-108"

    if from_craftforge_design:
        cf = from_craftforge_design
        name = cf.get("name") or name
        total_width_in = float(cf.get("width") or total_width_in)
        total_height_in = float(cf.get("height") or total_height_in)
        depth_in = float(cf.get("depth") or depth_in)
        primary_mat = cf.get("primary_material") or wood_species
        wood_species = primary_mat
        materials_list = cf.get("materials") or []
        client_name = cf.get("customer_name") or client_name
        client_address = cf.get("customer_address") or ""
        quote_number = cf.get("design_number") or quote_number

        # Check line_items / description / notes for finish details
        if cf.get("style"):
            finish = f"{cf.get('style').capitalize()} finish"

    # Build 3 carcass bays (left bookcases, center TV/bar bay, right bookcases)
    bay_w = total_width_in / 3.0
    boxes = [
        CarcassBoxSpec(
            name="Left Bay - Shelving",
            width_in=bay_w,
            height_in=total_height_in - 4.0,  # above toe kick
            depth_in=depth_in,
            shelves=4,
            doors=0,
            drawers=0,
            door_style="open",
        ),
        CarcassBoxSpec(
            name="Center Lower Bay - Drawers",
            width_in=bay_w,
            height_in=total_height_in - 4.0,
            depth_in=depth_in,
            shelves=0,
            doors=0,
            drawers=3,
            door_style="open",
        ),
        CarcassBoxSpec(
            name="Right Bay - Shaker Cabinet",
            width_in=bay_w,
            height_in=total_height_in - 4.0,
            depth_in=depth_in,
            shelves=3,
            doors=2,
            drawers=0,
            door_style="shaker",
        ),
    ]

    casework = CaseworkSpec(
        overall_width_in=total_width_in,
        overall_height_in=total_height_in,
        overall_depth_in=depth_in,
        boxes=boxes,
        toe_kick_height_in=4.0,
        toe_kick_depth_in=3.0,
        wood_species=wood_species,
        finish=finish,
        materials=materials_list,
    )

    return PieceSpec(
        name=name,
        piece_type="wall_unit",
        business_unit="woodcraft",
        client_name=client_name,
        client_address=client_address,
        quote_number=quote_number,
        footprint=FootprintSpec(
            shape="straight",
            overall_width_in=total_width_in,
            overall_depth_in=depth_in,
        ),
        casework=casework,
        material=MaterialFinishSpec(
            material_type="wood",
            name=wood_species,
            color_name="natural wood",
            color_hex="#8B5A2B",
            wood_species=wood_species,
            wood_finish=finish,
        ),
    )
