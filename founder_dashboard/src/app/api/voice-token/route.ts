import { NextResponse } from 'next/server';

export async function POST() {
  const apiKey = process.env.XAI_API_KEY;
  if (!apiKey) {
    return NextResponse.json(
      { error: 'XAI_API_KEY not configured' },
      { status: 500 },
    );
  }

  try {
    const res = await fetch('https://api.x.ai/v1/realtime/client_secrets', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({}),
    });

    if (!res.ok) {
      const errText = await res.text().catch(() => 'Unknown error');
      return NextResponse.json(
        { error: `xAI API error: ${res.status} ${errText}` },
        { status: res.status },
      );
    }

    const data = await res.json();
    // xAI returns { value, expires_at } at top level — normalize to { client_secret: { value } }
    const normalized = data.client_secret
      ? data
      : { client_secret: { value: data.value || data.token || data.secret }, expires_at: data.expires_at };
    return NextResponse.json(normalized);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Failed to get token';
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
