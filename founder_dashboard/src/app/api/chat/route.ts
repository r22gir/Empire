import { NextRequest } from 'next/server';

const SYSTEM_PROMPT =
  'You are MAX, the Empire AI Manager for a luxury drapery and window treatment business. ' +
  'Professional, confident, bilingual English/Spanish. You help manage operations, finance, ' +
  'sales, clients, contractors, support, marketing, and more across the Empire platform.';

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
