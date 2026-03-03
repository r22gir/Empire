import { NextRequest, NextResponse } from 'next/server';
import { corsResponse, corsOptions } from '../cors';

export const config = {
  api: { bodyParser: { sizeLimit: '10mb' } },
};
export const maxDuration = 60;

export async function OPTIONS() { return corsOptions(); }

const MOCKUP_PROMPT_BASE = `You are a luxury interior designer specializing in custom window treatments and soft furnishings for high-end residential projects. You have 25+ years of experience creating stunning, functional window solutions.

CRITICAL RULES:
- You are designing WINDOW TREATMENTS ONLY. Do NOT suggest moving, replacing, or rearranging furniture, flooring, or wall decor.
- Keep existing room elements (furniture, art, rugs, paint) exactly as they are — your job is ONLY the windows.
- Each tier MUST be clearly different from the others in treatment type, fabric, hardware, and visual impact.
- Ensure design logic: rods/tracks go BEHIND or ABOVE valances/cornices, never in front. Hardware must be compatible with the treatment style.

Analyze this photo and create a detailed mockup/design proposal for window treatments ONLY.

STEP 1 — ASSESS THE SPACE:
- Room type and function (living room, bedroom, dining, office, etc.)
- Architectural style (modern, traditional, transitional, contemporary, colonial, etc.)
- Light exposure and direction (bright, moderate, low — affects lining and opacity recommendations)
- Existing decor elements (furniture style, color palette, flooring, wall color) — NOTE these but do NOT change them
- Privacy needs based on room type and window position

STEP 2 — WINDOW ANALYSIS:
- Window type (single/double hung, casement, picture, bay, arched, sliding door, French door)
- Approximate dimensions from reference objects
- Current treatment (if any) and its condition
- How the window is used (needs to open? sliding door access?)

STEP 3 — DESIGN PROPOSALS (provide 3 distinctly different options from budget to luxury):`;

const TREATMENT_OPTIONS = `
OPTION 1 — ELEGANT ESSENTIAL (budget-conscious, clean, simple):
- SIMPLE treatment: single-layer panels OR a clean shade/blind — no layering
- Standard-weight fabric: cotton, polyester blend, or basic linen in solid colors
- Standard lining (privacy or light-filtering)
- Simple hardware: basic rod with matching finials OR inside-mount brackets
- NO extras — clean, functional, elegant
- Price range: $200-$600 per window
- Explain why this simple approach works for the space

OPTION 2 — DESIGNER'S CHOICE (mid-range, layered, textured):
- MUST be a different treatment type than Option 1 (e.g., if Option 1 is panels, use Roman shade + sheers)
- Mid-range fabric: textured linen, jacquard, subtle pattern, or woven blend
- Blackout or thermal lining + interlining for body
- Decorative hardware: ornamental rod with detailed finials, rings, or a ripplefold track system
- ONE layer of extras: sheers behind panels, OR decorative trim, OR contrasting banding
- Describe specific fabric texture (e.g., "nubby linen weave" not just "linen")
- Price range: $600-$1,500 per window
- Design rationale explaining the layered approach

OPTION 3 — ULTIMATE LUXURY (premium, statement, multi-layered):
- MUST be the most elaborate — completely different look from Options 1 and 2
- FULL LAYERING: sheers + functional drapery panels + decorative top treatment (cornice, valance, or swag)
- Premium fabric: silk dupioni, Italian velvet, designer embroidered, or hand-printed
- Specify exact fabric texture and sheen (e.g., "crushed silk velvet with a deep luster" not just "velvet")
- Motorization (Lutron or Somfy) for functional layers
- Custom hardware: hand-forged iron, crystal finials, gilded brackets, or hidden motorized track
- Multiple extras: decorative trim, contrast lining reveal, tassel tiebacks, beaded fringe
- Price range: $1,500-$4,000+ per window
- Explain the "wow factor" — what makes someone walk into the room and gasp

DESIGN VALIDATION — Before finalizing, check each proposal:
- Rods/tracks mount ABOVE or BEHIND any valance/cornice — never in front
- Hardware style matches the treatment (no ornate finials with ripplefold tracks)
- Fabric weight is appropriate (heavy velvet needs sturdy hardware, not tension rods)
- Inside-mount only if window frame depth allows it (3.5"+ for blinds)
- Colors complement the existing room palette, don't clash
- Do NOT suggest moving or replacing any furniture or non-window elements

STEP 4 — VISUAL DESCRIPTION (CRITICAL — be extremely specific and vivid):
For each option, paint a picture in words:
- Exact fabric appearance: texture, sheen, drape quality, pattern detail
- How light interacts: does it glow through sheers? Create pooling shadows from heavy velvet?
- Hardware finish: brushed brass with spiral finials? Matte black iron with ball ends?
- The overall emotional impact: cozy? dramatic? serene? grand?
- Include specific color descriptions (not "blue" — say "deep navy with tonal damask pattern")

Return JSON only:
{
  "room_assessment": {
    "room_type": string,
    "style": string,
    "light_level": string,
    "color_palette": string[],
    "privacy_need": "low" | "medium" | "high"
  },
  "window_info": {
    "type": string,
    "estimated_width": number,
    "estimated_height": number,
    "current_treatment": string | null
  },
  "proposals": [
    {
      "tier": string,
      "treatment_type": string,
      "style": string,
      "fabric": string,
      "lining": string,
      "hardware": string,
      "extras": string[],
      "price_range_low": number,
      "price_range_high": number,
      "visual_description": string,
      "design_rationale": string
    }
  ],
  "general_recommendations": string[],
  "confidence": number,
  "notes": string
}`;

export async function POST(req: NextRequest) {
  const apiKey = process.env.XAI_API_KEY;
  if (!apiKey) {
    return corsResponse({ error: 'XAI_API_KEY not configured' }, 500);
  }

  try {
    const { image, preferences } = await req.json();
    if (!image) {
      return corsResponse({ error: 'No image provided' }, 400);
    }

    // Allow user to pass style preferences
    const prefText = preferences
      ? `\n\nCLIENT PREFERENCES: ${preferences}\nIncorporate these preferences into your proposals.`
      : '';

    const fullPrompt = MOCKUP_PROMPT_BASE + prefText + TREATMENT_OPTIONS;

    const res = await fetch('https://api.x.ai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({
        model: 'grok-4-fast-non-reasoning',
        messages: [
          {
            role: 'user',
            content: [
              { type: 'image_url', image_url: { url: image } },
              { type: 'text', text: fullPrompt },
            ],
          },
        ],
        max_tokens: 4500,
        temperature: 0.3,
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

    // Generate AI mockup images for each proposal (non-blocking)
    try {
      const proposals = analysis.proposals || [];
      const roomType = analysis.room_assessment?.room_type || 'room';
      const windowType = analysis.window_info?.type || 'window';
      const colorPalette = (analysis.room_assessment?.color_palette || []).join(', ') || 'neutral tones';
      const lightLevel = analysis.room_assessment?.light_level || 'natural';

      const tierImageStyles: Record<string, string> = {
        'Elegant Essential': 'Simple, clean, minimal design. Single-layer treatment. Standard fabric with solid color. Basic rod or brackets. Bright, airy, budget-friendly elegance. The simplicity IS the style.',
        "Designer's Choice": 'Layered, textured, curated design. Multiple elements working together. Visible fabric texture and weave. Decorative hardware with detailed finials. Rich mid-range materials. The room feels "designed" and intentional.',
        'Ultimate Luxury': 'Opulent, grand, multi-layered statement. Floor-to-ceiling panels with sheers behind. Visible fabric sheen and luster (silk, velvet). Ornate custom hardware with crystal or gilded finials. Decorative top treatment (cornice or valance). Tiebacks or trim details. The room feels like a luxury magazine cover.',
      };

      const imagePromises = proposals.slice(0, 3).map(async (p: any, idx: number) => {
        const tierStyle = tierImageStyles[p.tier] || tierImageStyles['Elegant Essential'];
        const isValance = p.treatment_type?.toLowerCase().includes('valance') || p.treatment_type?.toLowerCase().includes('cornice');
        const hardwareNote = isValance
          ? `The ${p.hardware || 'mounting board'} is HIDDEN BEHIND the valance/cornice — NOT visible in front.`
          : `Hardware: ${p.hardware || 'decorative rod'} mounted 4-6 inches ABOVE the window frame.`;

        const prompt = [
          `PROFESSIONAL interior design photograph of a ${roomType} with a ${windowType} window.`,
          `WINDOW TREATMENT ONLY (do NOT change furniture or decor):`,
          `Installed: ${p.treatment_type} in ${p.fabric} fabric, ${p.style} style.`,
          tierStyle,
          `The fabric has visible texture: ${p.fabric?.includes('velvet') ? 'deep plush velvet pile with light-catching sheen' : p.fabric?.includes('silk') ? 'smooth lustrous silk with subtle shimmer' : p.fabric?.includes('linen') ? 'natural linen weave with organic texture' : 'rich woven textile with visible drape and body'}.`,
          hardwareNote,
          p.lining ? `${p.lining} lining providing ${p.lining === 'blackout' ? 'complete light blocking' : 'privacy and light filtering'}.` : '',
          (p.extras || []).length > 0 ? `Details: ${p.extras.join(', ')}.` : '',
          `Room: ${colorPalette} color scheme. ${lightLevel} light. All existing furniture and decor UNCHANGED.`,
          `Photorealistic, straight-on view, 4K sharp focus, Architectural Digest magazine quality.`,
          idx === 2 ? 'This is the MOST LUXURIOUS option — make it visually stunning and dramatically different from a basic treatment.' : '',
        ].filter(Boolean).join(' ');


        try {
          const imgRes = await fetch('https://api.x.ai/v1/images/generations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
            body: JSON.stringify({ model: 'grok-imagine-image', prompt, n: 1, response_format: 'url' }),
          });
          if (imgRes.ok) {
            const imgData = await imgRes.json();
            const url = imgData.data?.[0]?.url;
            if (url) return { tier: p.tier, url };
          }
        } catch { /* skip failed image */ }
        return null;
      });

      const images = (await Promise.all(imagePromises)).filter(Boolean);
      analysis.generated_images = images;
    } catch {
      analysis.generated_images = [];
    }

    return corsResponse(analysis);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Mockup analysis failed';
    return corsResponse({ error: msg }, 500);
  }
}
