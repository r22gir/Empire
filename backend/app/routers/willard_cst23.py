"""
Willard CST-23 API Router — 3D Assembly Review, Layer Engine & WoodCraft Project Data.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.services.woodcraft.willard_cst23 import (
    get_full_willard_spec,
    calculate_cut_schedule,
    format_fraction,
    WillardCST23Spec,
    ChannelControlInput,
    LayerConfig,
    ArmrestConfig,
    NESTED_SHEETS_DATA,
    OPEN_ITEMS_DATA,
)

router = APIRouter(tags=["willard-cst23", "woodcraft"])


@router.get("/spec", response_model=WillardCST23Spec)
async def get_willard_spec(
    channel_count: int = Query(default=8, ge=4, le=16),
    channel_width: float = Query(default=9.15625),
    channel_height: float = Query(default=36.0),
    stapling_allowance: float = Query(default=2.5, ge=2.0, le=3.0),
    back_foam_thickness: float = Query(default=2.0, ge=0.5, le=4.0),
    seat_foam_thickness: float = Query(default=5.0, ge=1.0, le=7.0),
    arm_type: str = Query(default="laminated_end"),
    upholstered_arm: bool = Query(default=True),
    fringe: bool = Query(default=True),
    show_frame: bool = Query(default=False),
):
    """Retrieve full Willard CST-23 3D assembly specification and project data."""
    return get_full_willard_spec(
        channel_count=channel_count,
        channel_width=channel_width,
        channel_height=channel_height,
        stapling_allowance=stapling_allowance,
        channel_foam_thickness=back_foam_thickness,
        seat_foam_thickness=seat_foam_thickness,
        arm_type=arm_type,
        upholstered_arm=upholstered_arm,
        fringe=fringe,
        show_frame=show_frame,
    )


@router.post("/sizing")
async def calculate_channel_sizing(input_data: ChannelControlInput):
    """Calculate channel cuts enforcing Willard CST-23 rules:
    - Wood/board cut = true size, no add-ons.
    - Foam cut = same as wood cut.
    - Fabric cut = foam/channel width plus 2 to 3 inches for stapling.
    - Always list wood cut and fabric cut as separate labeled sizes.
    - Fractions only.
    """
    schedule = calculate_cut_schedule(
        channel_count=input_data.channel_count,
        channel_width=input_data.channel_width,
        channel_height=input_data.channel_height,
        stapling_allowance=input_data.stapling_allowance,
        channel_foam_thickness=input_data.channel_depth,
    )
    channel_items = [item for item in schedule if item.category == "channel"]

    wood_cut = f"{format_fraction(input_data.channel_width)} × {format_fraction(input_data.channel_height)}"
    foam_cut = f"{format_fraction(input_data.channel_width)} × {format_fraction(input_data.channel_height)} × {format_fraction(input_data.channel_depth)}"
    fabric_cut = f"{format_fraction(input_data.channel_width + input_data.stapling_allowance)} × {format_fraction(input_data.channel_height + input_data.stapling_allowance)}"

    return {
        "channel_count": input_data.channel_count,
        "wood_cut_labeled": {
            "label": "Wood / Board Cut (True Size, No Add-ons)",
            "size": wood_cut,
            "width": format_fraction(input_data.channel_width),
            "height": format_fraction(input_data.channel_height),
        },
        "foam_cut_labeled": {
            "label": "Foam Cut (Same as Wood Cut)",
            "size": foam_cut,
            "thickness": format_fraction(input_data.channel_depth),
        },
        "fabric_cut_labeled": {
            "label": f"Fabric Cut (Width + {format_fraction(input_data.stapling_allowance)} for Stapling)",
            "size": fabric_cut,
            "width": format_fraction(input_data.channel_width + input_data.stapling_allowance),
            "height": format_fraction(input_data.channel_height + input_data.stapling_allowance),
            "stapling_allowance": format_fraction(input_data.stapling_allowance),
        },
        "items": channel_items,
        "custom_rule_applied": "Willard CST-23 is a reviewed custom piece; general rules do not override it.",
    }


@router.get("/cut-sheets")
async def get_cut_sheets():
    """Retrieve 8-sheet nesting schedule and links to files in /workspace/willard_cst23_rev/."""
    return NESTED_SHEETS_DATA


@router.get("/open-items")
async def get_open_items():
    """Retrieve tracked open items: channel height range, empty R24 dado pocket, foam/board thickness."""
    return {"open_items": OPEN_ITEMS_DATA}
