import { NextRequest, NextResponse } from 'next/server';

const VISION_PROMPT = `You are an expert window treatment estimator with 20+ years measuring windows for custom drapery. Analyze this photo and estimate the window dimensions as accurately as possible.

STEP 1 — IDENTIFY ALL REFERENCE OBJECTS in the scene and use them to establish scale:
- Doors/door frames: 80" tall, 32-36" wide
- Standard electrical outlets: 4.5" tall, mounted 12-16" from floor
- Light switches: 5" tall, mounted 48" from floor
- Baseboards: typically 4-6" tall
- Standard ceiling height: 96" (8 ft) unless clearly taller (vaulted, 10ft, etc.)
- Dining/desk chairs: seat height 17-18", total height 30-34"
- Sofas/couches: seat height 17-19", back height 30-36"
- Bookshelves/shelving units: shelves typically spaced 10-12" apart, units are often 72-84" tall
- Floor plants/plant baskets: large decorative baskets are 12-18" diameter, floor planters 14-24" tall
- People standing: average 65-69" (women) or 69-73" (men)
- People seated: torso from seat to top of head ~30-34"
- Standard counter height: 36", bar height: 42"
- Bed frame with mattress: 25" tall (standard), headboard 48-56"
- Floor-to-ceiling windows typically run 84-108" depending on ceiling height

STEP 2 — ESTIMATE WINDOW DIMENSIONS using the reference objects for scale. Cross-reference at least 2 objects if possible. Consider the full window opening from frame edge to frame edge.

STEP 3 — CLASSIFY the window type and suggest treatments for a luxury drapery business.

Return JSON only — no markdown, no explanation outside the JSON:
{"width_inches": number, "height_inches": number, "confidence": number (0-100), "window_type": string, "reference_objects_used": string[], "notes": string, "treatment_suggestions": string[]}`;

export async function POST(req: NextRequest) {
  const apiKey = process.env.XAI_API_KEY;
  if (!apiKey) {
    return NextResponse.json(
      { error: 'XAI_API_KEY not configured' },
      { status: 500 },
    );
  }

  try {
    const { image } = await req.json();
    if (!image) {
      return NextResponse.json({ error: 'No image provided' }, { status: 400 });
    }

    // image is a data URL like "data:image/jpeg;base64,..."
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
              { type: 'text', text: VISION_PROMPT },
            ],
          },
        ],
        max_tokens: 1024,
        temperature: 0.2,
      }),
    });

    if (!res.ok) {
      const errText = await res.text().catch(() => 'Unknown error');
      return NextResponse.json(
        { error: `xAI Vision error: ${res.status} ${errText}` },
        { status: res.status },
      );
    }

    const data = await res.json();
    const content = data.choices?.[0]?.message?.content || '';

    // Extract JSON from response (may be wrapped in markdown code block)
    const jsonMatch = content.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      return NextResponse.json(
        { error: 'Could not parse vision response', raw: content },
        { status: 500 },
      );
    }

    const analysis = JSON.parse(jsonMatch[0]);
    return NextResponse.json(analysis);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Analysis failed';
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
