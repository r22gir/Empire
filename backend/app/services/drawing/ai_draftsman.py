"""
AI Parametric Draftsman — sends structured prompts to Claude Sonnet,
receives JSON drafting instructions. NEVER receives SVG.

Stage 1 of the two-stage pipeline:
  AI decides WHAT to draw (geometry, dimensions, annotations)
  Code decides HOW to draw it (projection, line weights, fonts, arrows)
"""
import os
import json
import httpx
import re
import logging

log = logging.getLogger("ai_draftsman")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ============================================================
# MASTER SYSTEM PROMPT
# ============================================================
DRAFTSMAN_SYSTEM_PROMPT = """You are a senior architectural draftsman and millwork detailer.

You DO NOT output drawings or SVG.
You output structured JSON drafting instructions for a parametric rendering engine.

Your job is to:
1. Interpret the object (bench, banquette, booth, millwork, cabinetry, wall paneling)
2. Define precise 3D geometry using named points
3. Define dimension callouts with exact placement
4. Define annotations and channel details

OUTPUT FORMAT: Return ONLY valid JSON. No explanation. No markdown fences. Just JSON.

COORDINATE SYSTEM:
- Origin at (0, 0, 0) = front-left corner at floor level
- X axis: width (left to right)
- Y axis: depth (front to back)
- Z axis: height (bottom to top)
- All units in INCHES
- Every coordinate must be exact, derived from the input dimensions

JSON SCHEMA:

{
  "object_type": "bench_straight | bench_l_shape | bench_u_shape",
  "label": "DESCRIPTIVE NAME",
  "geometry": {
    "points": {
      "seat_fl": [0, 0, 0],
      "seat_fr": [width, 0, 0],
      "...": "etc — define ALL corners of ALL volumes"
    },
    "edges": [
      {"from": "seat_fl", "to": "seat_fr", "weight": "outline"},
      {"from": "...", "to": "...", "weight": "outline | detail | channel"}
    ],
    "faces": [
      {"points": ["A", "B", "C", "D"], "type": "seat_top | back_front | seat_front | side_right | back_top | back_rear"}
    ]
  },
  "dimensions": [
    {
      "type": "linear",
      "from": "seat_fl",
      "to": "seat_fr",
      "value": 250,
      "label": "250\\"",
      "placement": "bottom",
      "offset": 25
    }
  ],
  "channels": {
    "face": "back_front",
    "count": 8,
    "style": "vertical"
  }
}

GEOMETRY RULES FOR BENCHES:

A bench is composed of two volumes:
1. SEAT BOX: from floor to seat_height. Width × Depth × seat_height.
   - The back portion of the seat depth is occupied by the back panel thickness (back_t = 4").
   - So the usable seat surface depth = depth - back_t.

2. BACK PANEL: from seat_height to (seat_height + back_height). Width × back_t × back_height.
   - Sits at the rear of the seat box.
   - The back panel's front face is where channel lines go.

Point naming convention (use these exact names):
- Seat box: seat_fl, seat_fr, seat_bl, seat_br (floor corners), seat_tfl, seat_tfr, seat_tbl, seat_tbr (top corners)
- Back panel: back_bfl, back_bfr, back_bbl, back_bbr (bottom corners), back_tfl, back_tfr, back_tbl, back_tbr (top corners)
- For L-shape: prefix wing points with "wing_"
- For U-shape: prefix left wing with "lw_", right wing with "rw_", center with "ctr_"

Edge weights:
- "outline" = structural edges (1.5px) — all visible outer edges
- "detail" = construction details (0.5px) — seat/back junction line
- "channel" = upholstery channels on back face (0.3px)

STRAIGHT BENCH example with width=100, depth=21, seat_h=18, back_h=32, back_t=4:
- seat_fl=[0,0,0], seat_fr=[100,0,0], seat_bl=[0,17,0], seat_br=[100,17,0]
- seat_tfl=[0,0,18], seat_tfr=[100,0,18], seat_tbl=[0,17,18], seat_tbr=[100,17,18]
- back_bfl=[0,17,18], back_bfr=[100,17,18], back_bbl=[0,21,18], back_bbr=[100,21,18]
- back_tfl=[0,17,50], back_tfr=[100,17,50], back_tbl=[0,21,50], back_tbr=[100,21,50]

L-SHAPE: Two sections meeting at a corner. The long leg runs along X, the short leg (wing) runs along Y from the right end. Define both sections fully with shared corner points.

U-SHAPE: Center back section + left wing + right wing. Center runs along X at the far Y edge. Wings run along Y on left and right sides.

DIMENSION PLACEMENT:
- "bottom" = below the front edge (for widths)
- "top" = above the back edge (for widths)
- "right" = to the right of the right face (for heights and depths)
- "left" = to the left of the left face (for heights)
- offset: pixels away from object (typically 20-30)

REQUIRED DIMENSIONS for every bench:
- Total width
- Seat depth
- Seat height
- Back height
- For L-shape: both leg lengths, depth
- For U-shape: back width, side depths, seat depth, both heights

VALIDATION (check before outputting):
- ALL point names in edges and dimensions must exist in points
- Dimension label values must match actual coordinate differences
- Every visible face must be defined
- Channel count should be width/12 to width/8 (reasonable spacing)"""


# ============================================================
# USER PROMPT BUILDERS
# ============================================================

def build_bench_prompt(bench_type: str, dimensions: dict, label: str,
                       options: dict = None) -> str:
    """Build the user prompt for a bench drawing."""
    options = options or {}
    prompt = f"Create a parametric drawing definition for:\n\nType: {bench_type}\nLabel: {label}\n\nDimensions:\n"

    if bench_type == "bench_straight":
        prompt += f"- width: {dimensions.get('width', 120)}\" (total width)\n"
        prompt += f"- depth: {dimensions.get('depth', 21)}\" (seat depth including back thickness)\n"
        prompt += f"- seat_height: {dimensions.get('seat_height', 18)}\"\n"
        prompt += f"- back_height: {dimensions.get('back_height', 18)}\" (above seat)\n"

    elif bench_type == "bench_l_shape":
        prompt += f"- leg1_length: {dimensions.get('leg1', dimensions.get('width', 0))}\" (long leg, along X)\n"
        prompt += f"- leg2_length: {dimensions.get('leg2', dimensions.get('short', 0))}\" (short leg/wing, along Y)\n"
        prompt += f"- seat_depth: {dimensions.get('depth', 21)}\" (bench depth including back)\n"
        prompt += f"- seat_height: {dimensions.get('seat_height', 18)}\"\n"
        prompt += f"- back_height: {dimensions.get('back_height', 18)}\" (above seat)\n"

    elif bench_type == "bench_u_shape":
        prompt += f"- back_width: {dimensions.get('back_width', dimensions.get('width', 0))}\" (center back section)\n"
        prompt += f"- left_wing_depth: {dimensions.get('left_depth', dimensions.get('side_depth', 0))}\" (left side wing length)\n"
        prompt += f"- right_wing_depth: {dimensions.get('right_depth', dimensions.get('side_depth', 0))}\" (right side wing length)\n"
        prompt += f"- seat_depth: {dimensions.get('depth', 21)}\" (bench seat depth)\n"
        prompt += f"- side_depth: {dimensions.get('side_seat_depth', dimensions.get('depth', 21))}\" (wing seat depth)\n"
        prompt += f"- seat_height: {dimensions.get('seat_height', 18)}\"\n"
        prompt += f"- back_height: {dimensions.get('back_height', 18)}\" (above seat)\n"

    prompt += f"\nOptions:\n"
    prompt += f"- back_thickness: 4\" (fixed)\n"
    prompt += f"- channel_count: {options.get('channels', 'auto (width/10)')}\n"
    prompt += f"\nReturn ONLY the JSON definition. No explanation."
    return prompt


def build_project_sheet_prompt(benches: list) -> str:
    """Build prompt for multiple benches to be laid out on a project sheet."""
    prompt = "Create parametric drawing definitions for EACH of these benches.\n\n"
    prompt += "Return a JSON object: {\"benches\": [<full definition for each>]}\n"
    prompt += "Each bench gets its own complete geometry/dimensions/channels definition.\n\n"

    for i, b in enumerate(benches):
        prompt += f"--- Bench {i+1} ---\n"
        prompt += f"Type: {b['type']}\n"
        prompt += f"Label: {b['label']}\n"
        prompt += f"Dimensions:\n"
        for k, v in b.get("dimensions", {}).items():
            prompt += f"  - {k}: {v}\"\n"
        if b.get("qty", 1) > 1:
            prompt += f"  Quantity: {b['qty']}x\n"
        prompt += "\n"

    prompt += "Return ONLY valid JSON."
    return prompt


# ============================================================
# API CALLS — Sonnet primary, GPT-4o fallback
# ============================================================

async def call_draftsman(prompt: str) -> dict:
    """Send prompt to AI draftsman. Returns parsed JSON."""
    if ANTHROPIC_API_KEY:
        result = await _call_sonnet(prompt)
        if result:
            return result
        log.warning("Sonnet failed, trying GPT-4o fallback")

    if OPENAI_API_KEY:
        result = await _call_gpt4o(prompt)
        if result:
            return result

    log.error("All draftsman providers failed")
    return {}


async def _call_sonnet(prompt: str) -> dict:
    """Call Claude Sonnet 4.6 — primary draftsman."""
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-6-20250514",
                    "max_tokens": 8000,
                    "system": DRAFTSMAN_SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
        if resp.status_code != 200:
            log.error(f"Sonnet API error {resp.status_code}: {resp.text[:200]}")
            return {}
        data = resp.json()
        text = data.get("content", [{}])[0].get("text", "")
        return _parse_json(text)
    except Exception as e:
        log.error(f"Sonnet draftsman error: {e}")
        return {}


async def _call_gpt4o(prompt: str) -> dict:
    """Fallback: GPT-4o."""
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o",
                    "messages": [
                        {"role": "system", "content": DRAFTSMAN_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 8000,
                    "response_format": {"type": "json_object"},
                },
            )
        if resp.status_code != 200:
            log.error(f"GPT-4o API error {resp.status_code}: {resp.text[:200]}")
            return {}
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return _parse_json(text)
    except Exception as e:
        log.error(f"GPT-4o draftsman error: {e}")
        return {}


def _parse_json(text: str) -> dict:
    """Clean and parse JSON from AI response."""
    text = text.strip()
    # Strip markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # Try to find JSON object in the response
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        log.error(f"JSON parse failed: {e}")
        return {}
