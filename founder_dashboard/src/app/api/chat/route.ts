import { NextRequest } from 'next/server';

const SYSTEM_PROMPT =
  'You are MAX, the AI Director for the entire Empire ecosystem. ' +
  'You are professional, confident, and fully bilingual English/Spanish. ' +
  'You oversee ALL Empire businesses and help the founder with anything:\n\n' +
  '• WorkroomForge — DC-area luxury window treatments (drapery, blinds, shades, motorization). Quoting, workroom ops, installs.\n' +
  '• LuxeForge — Designer portal for trade professionals to browse collections, request quotes, manage projects.\n' +
  '• AMP (Cali, Colombia) — 9-service business: upholstery, curtains, blinds, motorization, furniture, flooring, wallpaper, painting, cleaning.\n' +
  '• SocialForge — Social media management platform (in development).\n' +
  '• CRM Personal — Personal relationship and contact management.\n' +
  '• Empire Box — Central file storage and document management.\n\n' +
  'You assist with operations, finance, sales, design, estimating, clients, contractors, support, ' +
  'marketing, IT, legal, and R&D across every business. You are the founder\'s right hand — ' +
  'handle whatever is asked with precision and initiative.';

export async function POST(req: NextRequest) {
  const apiKey = process.env.XAI_API_KEY;
  if (!apiKey) {
    return new Response(
      `data: ${JSON.stringify({ type: 'error', content: 'XAI_API_KEY not configured' })}\n\n`,
      { status: 200, headers: sseHeaders() },
    );
  }

  const { message, history, desk } = await req.json();

  const messages = [
    { role: 'system' as const, content: desk ? `${SYSTEM_PROMPT} Current desk: ${desk}.` : SYSTEM_PROMPT },
    ...((history || []) as { role: string; content: string }[]).slice(-20),
    { role: 'user' as const, content: message },
  ];

  const xaiRes = await fetch('https://api.x.ai/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: 'grok-3-fast',
      messages,
      stream: true,
    }),
  });

  if (!xaiRes.ok || !xaiRes.body) {
    const errText = await xaiRes.text().catch(() => 'Unknown error');
    return new Response(
      `data: ${JSON.stringify({ type: 'error', content: `Grok API error: ${xaiRes.status} ${errText}` })}\n\n`,
      { status: 200, headers: sseHeaders() },
    );
  }

  const encoder = new TextEncoder();
  const reader = xaiRes.body.getReader();
  const decoder = new TextDecoder();

  const stream = new ReadableStream({
    async start(controller) {
      let buf = '';
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          const lines = buf.split('\n');
          buf = lines.pop() || '';

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const payload = line.slice(6).trim();
            if (payload === '[DONE]') continue;
            try {
              const chunk = JSON.parse(payload);
              const delta = chunk.choices?.[0]?.delta?.content;
              if (delta) {
                controller.enqueue(
                  encoder.encode(`data: ${JSON.stringify({ type: 'text', content: delta })}\n\n`),
                );
              }
            } catch { /* skip malformed chunks */ }
          }
        }
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ type: 'done', model_used: 'grok-3-fast (direct)' })}\n\n`),
        );
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Stream error';
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ type: 'error', content: msg })}\n\n`),
        );
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, { status: 200, headers: sseHeaders() });
}

function sseHeaders(): HeadersInit {
  return {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
  };
}
