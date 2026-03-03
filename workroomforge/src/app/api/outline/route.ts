import { NextRequest, NextResponse } from 'next/server';
import { corsResponse, corsOptions } from '../cors';

export const config = {
  api: { bodyParser: { sizeLimit: '10mb' } },
};
export const maxDuration = 60;

export async function OPTIONS() { return corsOptions(); }

const OUTLINE_PROMPT = `You are an expert window treatment installer and architectural draftsman. Analyze this photo and create a detailed dimensional outline/plan of the window area.

STEP 1 — IDENTIFY AND MAP ALL ELEMENTS:
- Window frame boundaries (left edge, right edge, top, bottom)
- Wall space above window (to ceiling or crown molding)
- Wall space on each side of window (to nearest obstruction: corner, another window, door frame)
- Distance from window bottom to floor
- Any obstructions: radiators, A/C units, furniture blocking the window wall, electrical outlets, light switches
- Existing window treatments if any (curtain rod, brackets, blinds, shutters)

STEP 2 — ESTABLISH MEASUREMENTS using reference objects:
- Doors: 80" tall, 32-36" wide
- Electrical outlets: 4.5" tall, mounted 12-16" from floor
- Light switches: 5" tall, mounted 48" from floor
- Baseboards: 4-6" tall
- Standard ceiling: 96" (8 ft)
- Chair rail: typically at 32-36" from floor
- Crown molding: typically 3-6" from ceiling

STEP 3 — CREATE A DIMENSIONAL PLAN with all measurements labeled. Include:
- Window opening width and height
- Total wall width available for treatment
- Ceiling to window top measurement
- Window bottom to floor measurement
- Stackback space available on each side (for drapery panels when open)
- Mounting height options (inside mount vs outside mount vs ceiling mount)
- Any clearance issues (furniture, radiators, outlets that would be covered)

STEP 4 — PROVIDE MOUNTING RECOMMENDATIONS:
- Recommended rod/track width (typically window width + 6-12" per side for stackback)
- Recommended mounting height (typically 4-6" above window or at ceiling)
- Inside mount feasibility (frame depth needed: 3.5"+ for blinds, 2"+ for shades)
- Identify any obstacles that affect treatment installation

Return JSON only — no markdown:
{
  "window_opening": {"width": number, "height": number},
  "wall_dimensions": {"total_width": number, "ceiling_height": number},
  "clearances": {
    "above_window": number,
    "below_window": number,
    "left_wall": number,
    "right_wall": number
  },
  "obstructions": [{"type": string, "location": string, "distance_from_window": number}],
  "existing_treatments": string | null,
  "mounting_recommendations": {
    "rod_width": number,
    "mounting_height": number,
    "mount_type": string,
    "inside_mount_feasible": boolean,
    "notes": string
  },
  "outline_description": string,
  "reference_objects_used": string[],
  "confidence": number,
  "notes": string
}`;

export async function POST(req: NextRequest) {
  const apiKey = process.env.XAI_API_KEY;
  if (!apiKey) {
    return corsResponse({ error: 'XAI_API_KEY not configured' }, 500);
  }

  try {
    const { image } = await req.json();
    if (!image) {
      return corsResponse({ error: 'No image provided' }, 400);
    }

    const res = await fetch('https://api.x.ai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: 'grok-3',
        messages: [
          {
            role: 'user',
            content: [
              { type: 'image_url', image_url: { url: image } },
              { type: 'text', text: OUTLINE_PROMPT },
            ],
          },
        ],
        max_tokens: 1500,
        temperature: 0.2,
      }),
    });

    if (!res.ok) {
      const errText = await res.text().catch(() => 'Unknown error');
      return corsResponse({ error: `Vision error: ${res.status} ${errText}` }, res.status);
    }

    const data = await res.json();
    const content = data.choices?.[0]?.message?.content || '';
    const jsonMatch = content.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      return corsResponse({ error: 'Could not parse response', raw: content }, 500);
    }

    const analysis = JSON.parse(jsonMatch[0]);
    return corsResponse(analysis);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Outline analysis failed';
    return corsResponse({ error: msg }, 500);
  }
}
