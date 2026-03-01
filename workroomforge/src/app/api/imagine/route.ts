import { NextRequest } from 'next/server';
import { corsResponse, corsOptions } from '../cors';

export const maxDuration = 60;

export async function OPTIONS() { return corsOptions(); }

const MODELS = ['grok-imagine-image', 'grok-2-image-1212'];

export async function POST(req: NextRequest) {
  const apiKey = process.env.XAI_API_KEY;
  if (!apiKey) {
    return corsResponse({ error: 'XAI_API_KEY not configured' }, 500);
  }

  try {
    const { prompt } = await req.json();
    if (!prompt) {
      return corsResponse({ error: 'No prompt provided' }, 400);
    }

    let lastError = '';
    for (const model of MODELS) {
      try {
        const res = await fetch('https://api.x.ai/v1/images/generations', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${apiKey}`,
          },
          body: JSON.stringify({ model, prompt, n: 1, response_format: 'url' }),
        });

        if (res.ok) {
          const data = await res.json();
          const image = data.data?.[0];
          if (image?.url) {
            return corsResponse({
              url: image.url,
              revised_prompt: image.revised_prompt || prompt,
              model,
            });
          }
        }

        const errText = await res.text().catch(() => '');
        lastError = `${model}: ${res.status} ${errText}`;
      } catch (err: unknown) {
        lastError = `${model}: ${err instanceof Error ? err.message : 'failed'}`;
      }
    }

    return corsResponse({ error: `Image generation failed: ${lastError}` }, 500);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Image generation failed';
    return corsResponse({ error: msg }, 500);
  }
}
