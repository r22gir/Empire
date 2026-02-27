import { NextRequest, NextResponse } from 'next/server';

const VISION_PROMPT =
  'You are an expert window measurement estimator. Analyze this window photo. ' +
  'Look for reference objects (doors are 80 inches tall, outlets are 4.5 inches, ' +
  'standard windows are 36x48). Estimate width and height in inches. ' +
  'Return JSON only: {"width_inches": number, "height_inches": number, ' +
  '"confidence": number (0-100), "window_type": string, "notes": string, ' +
  '"treatment_suggestions": string[]}';

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
