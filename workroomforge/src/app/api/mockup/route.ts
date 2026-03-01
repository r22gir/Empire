import { NextRequest, NextResponse } from 'next/server';
import { corsResponse, corsOptions } from '../cors';

export const config = {
  api: { bodyParser: { sizeLimit: '10mb' } },
};
export const maxDuration = 60;

export async function OPTIONS() { return corsOptions(); }

const MOCKUP_PROMPT_BASE = `You are a luxury interior designer specializing in custom window treatments and soft furnishings for high-end residential projects in the Washington DC area. You have 25+ years of experience creating stunning, functional window solutions.

Analyze this photo and create a detailed mockup/design proposal for new or replacement window treatments.

STEP 1 — ASSESS THE SPACE:
- Room type and function (living room, bedroom, dining, office, etc.)
- Architectural style (modern, traditional, transitional, contemporary, colonial, etc.)
- Light exposure and direction (bright, moderate, low — affects lining and opacity recommendations)
- Existing decor elements (furniture style, color palette, flooring, wall color)
- Privacy needs based on room type and window position

STEP 2 — WINDOW ANALYSIS:
- Window type (single/double hung, casement, picture, bay, arched, sliding door, French door)
- Approximate dimensions from reference objects
- Current treatment (if any) and its condition
- How the window is used (needs to open? sliding door access?)

STEP 3 — DESIGN PROPOSALS (provide 3 options from budget to luxury):`;

const TREATMENT_OPTIONS = `
OPTION 1 — ELEGANT ESSENTIAL (budget-conscious luxury):
- Treatment type and style
- Fabric weight and type recommendation
- Lining recommendation
- Hardware style
- Estimated price range
- Why this works for the space

OPTION 2 — DESIGNER'S CHOICE (mid-range luxury):
- Treatment type and style (more elaborate)
- Fabric recommendation with pattern/texture suggestions
- Lining and interlining
- Decorative hardware
- Layering suggestions (sheer + drapery, shade + panels)
- Estimated price range
- Design rationale

OPTION 3 — ULTIMATE LUXURY (premium):
- Full custom treatment with all premium details
- Premium fabric recommendations (silks, velvets, designer prints)
- Motorization options
- Full layering (sheers + functional panels + decorative valance/cornice)
- Custom hardware (hand-forged, crystal finials, etc.)
- Estimated price range
- Why this creates maximum impact

STEP 4 — VISUAL DESCRIPTION:
For each option, describe in vivid detail how the treatment would look installed — colors, how the fabric drapes, how light filters through, the overall aesthetic impact. This should help the client visualize the finished result.

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
        model: 'grok-2-vision-1212',
        messages: [
          {
            role: 'user',
            content: [
              { type: 'image_url', image_url: { url: image } },
              { type: 'text', text: fullPrompt },
            ],
          },
        ],
        max_tokens: 3000,
        temperature: 0.4,
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

      const imagePromises = proposals.slice(0, 3).map(async (p: any) => {
        const prompt = `Photorealistic interior design photograph: a ${roomType} with a ${windowType} window. Installed treatment: ${p.treatment_type} in ${p.fabric} fabric, ${p.style} style. The drapery panels are RETRACTED to each side, gathered in elegant stackback folds, revealing the window. Hardware: ${p.hardware}. ${p.lining} lining visible at edges. ${(p.extras || []).join(', ')}. Room color scheme: ${colorPalette}. ${lightLevel} natural light. Professional architectural photography, straight-on view, sharp focus, magazine quality interior design photo.`;

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
