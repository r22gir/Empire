import { NextRequest, NextResponse } from 'next/server';
import { corsResponse, corsOptions } from '../cors';

// Allow large base64 image payloads (up to 10MB)
export const config = {
  api: { bodyParser: { sizeLimit: '10mb' } },
};

// Allow up to 60 seconds for xAI vision API
export const maxDuration = 60;

export async function OPTIONS() { return corsOptions(); }

const UPHOLSTERY_VISION_PROMPT = `You are an expert upholstery estimator with 20+ years experience in the Washington DC area custom upholstery market. Analyze this photo of furniture and provide a detailed reupholstery estimate.

STEP 1 — IDENTIFY THE FURNITURE:
- Type: sofa, loveseat, chair, ottoman, bench, headboard, chaise, daybed, sectional, recliner, dining chair, stool
- Style: club, wing, barrel/tub, Chesterfield, tufted, channel-back, slipcovered, mid-century, traditional, parsons, camelback, Lawson, English roll-arm, track-arm
- Approximate dimensions (width, depth, height in inches)
- Count all visible cushions: seat cushions, back cushions, throw pillows
- Construction: tufting, channeling, skirted, exposed legs, nailhead trim, welting/piping

STEP 2 — IDENTIFY REFERENCE OBJECTS to estimate furniture size:
- Doors: 80" tall, 32-36" wide
- Electrical outlets: 4.5" tall, mounted 12-16" from floor
- Standard ceiling height: 96"
- Floor plants/baskets: large decorative baskets 12-18" diameter
- Shelving units: shelves typically 10-12" apart, units 72-84" tall
- People seated: torso ~30-34" from seat to head
- Coffee tables: 16-18" tall, end tables 24-26" tall
- Throw pillows: standard 18x18" or 20x20"
- Seat cushion depth: typically 21-24"

STEP 3 — ESTIMATE FABRIC YARDAGE using this industry chart (54" wide plain fabric):
- Dining chair seat only: 0.75 yd
- Dining chair with arms: 2-3 yd
- Parsons chair: 3 yd
- Accent/side chair: 3-4 yd
- Club chair: 6-7 yd
- Wing chair: 7-9 yd
- Barrel/tub chair: 5-6 yd
- Recliner: 8-10 yd
- Lounge chair: 7-8 yd
- Ottoman small (under 29"): 2-3 yd
- Ottoman large (30-45"): 3-5 yd
- Loveseat 2-cushion: 10-12 yd
- Sofa 2-cushion: 12-14 yd
- Sofa 3-cushion: 14-16 yd
- Sofa 4+ cushion: 16-20 yd
- Sectional per section: 12-16 yd
- Chaise lounge: 8-10 yd
- Daybed: 10-12 yd
- Bench small: 2-3 yd
- Bench large/tufted: 4-6 yd
- Headboard twin: 3-4 yd
- Headboard queen: 5-6 yd
- Headboard king: 6-8 yd
- Stool/bar stool seat: 1-1.5 yd

Adjustments:
- Patterned or striped fabric: add 15-25% (pattern matching waste)
- Welting/piping: add 10%
- Tufting: add 10-15%
- Channeling: add 5-10%
- Skirt/ruffle: add 1-2 yards
- Railroading can reduce yardage 10-20% on wide pieces

STEP 4 — DC AREA PRICING CONTEXT:
Labor rates (per yard of fabric):
- Standard reupholstery: $50-75/yd
- Tufting work: $65-90/yd
- Channeling: $60-85/yd
- Leather work: $80-120/yd

Fabric cost ranges (per yard, 54" wide):
- Basic/utility: $15-30/yd
- Mid-range decorator: $35-65/yd
- Premium/name brand: $70-150/yd
- Designer/luxury: $150-400/yd

Additional services:
- New cushion foam (per seat): $45-85
- Nailhead trim application: $100-200 per piece
- Arm caps or headrest covers: $35-60
- Pickup & delivery (DC metro): $75-150

STEP 5 — GENERATE QUESTIONS the estimator should ask the customer before finalizing the quote.

Return JSON only — no markdown, no explanation outside the JSON:
{
  "furniture_type": string,
  "style": string,
  "estimated_dimensions": {"width": number, "depth": number, "height": number},
  "cushion_count": {"seat": number, "back": number, "throw_pillows": number},
  "reference_objects_used": string[],
  "fabric_yards_plain": number,
  "fabric_yards_patterned": number,
  "has_welting": boolean,
  "has_tufting": boolean,
  "has_channeling": boolean,
  "has_skirt": boolean,
  "has_nailhead": boolean,
  "suggested_labor_type": string,
  "estimated_labor_cost_low": number,
  "estimated_labor_cost_high": number,
  "new_foam_recommended": boolean,
  "confidence": number,
  "notes": string,
  "questions": string[]
}`;

export async function POST(req: NextRequest) {
  const apiKey = process.env.XAI_API_KEY;
  if (!apiKey) {
    return corsResponse(
      { error: 'XAI_API_KEY not configured' },
      500,
    );
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
        model: 'grok-2-vision-1212',
        messages: [
          {
            role: 'user',
            content: [
              { type: 'image_url', image_url: { url: image } },
              { type: 'text', text: UPHOLSTERY_VISION_PROMPT },
            ],
          },
        ],
        max_tokens: 1500,
        temperature: 0.2,
      }),
    });

    if (!res.ok) {
      const errText = await res.text().catch(() => 'Unknown error');
      return corsResponse(
        { error: `xAI Vision error: ${res.status} ${errText}` },
        res.status,
      );
    }

    const data = await res.json();
    const content = data.choices?.[0]?.message?.content || '';

    const jsonMatch = content.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      return corsResponse(
        { error: 'Could not parse vision response', raw: content },
        500,
      );
    }

    const analysis = JSON.parse(jsonMatch[0]);

    // Generate AI before/after illustration (non-blocking)
    try {
      const details: string[] = [];
      if (analysis.has_tufting) details.push('diamond tufting');
      if (analysis.has_welting) details.push('contrast welting/piping');
      if (analysis.has_nailhead) details.push('brass nailhead trim');
      if (analysis.has_skirt) details.push('tailored skirt');
      if (analysis.has_channeling) details.push('vertical channeling');
      const detailText = details.length > 0 ? details.join(', ') : 'clean upholstery';
      const cushions = analysis.cushion_count || {};

      const prompt = `Professional design studio illustration of furniture reupholstery transformation: A ${analysis.furniture_type || 'sofa'} in ${analysis.style || 'traditional'} style, split-view showing before and after. Left side shows the original piece needing reupholstery work, slightly worn. Right side shows the beautifully reupholstered result with fresh fabric featuring ${detailText}. ${cushions.seat ? `${cushions.seat} seat cushions` : ''}${cushions.back ? `, ${cushions.back} back cushions` : ''}. Clean white studio background, detailed craftsmanship visible, professional furniture design rendering, high quality.`;

      const imgRes = await fetch('https://api.x.ai/v1/images/generations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
        body: JSON.stringify({ model: 'grok-imagine-image', prompt, n: 1, response_format: 'url' }),
      });
      if (imgRes.ok) {
        const imgData = await imgRes.json();
        analysis.generated_image = imgData.data?.[0]?.url || null;
      }
    } catch {
      analysis.generated_image = null;
    }

    return corsResponse(analysis);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Analysis failed';
    return corsResponse({ error: msg }, 500);
  }
}
