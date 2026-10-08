/**
 * Queueing check for useChat (2026-10-08). Run: scripts/check-chat-queue.sh
 * Drives the real hook with a React shim and a fake streaming fetch:
 * messages sent while Max answers are shown as queued, run in order, see the
 * earlier replies in their history, can be removed while queued, and Stop
 * ends only the current reply.
 */
import * as assert from 'assert';
// eslint-disable-next-line @typescript-eslint/no-var-requires
const React: any = require('react');
import { useChat } from '../useChat';
import { insertAfter, historyFor, splitForView } from '../chatQueue';

type Pending = { body: any; push: (s: string) => void; end: () => void; fail: (e: any) => void };
const pending: Pending[] = [];
(globalThis as any).fetch = (url: string, init: any) => {
  if (!String(url).includes('/max/chat/stream')) return Promise.resolve({ ok: false, json: async () => null });
  return new Promise((resolve) => {
    const chunks: string[] = [];
    let waiter: ((v: any) => void) | null = null;
    let ended = false;
    let failed: any = null;
    const wake = () => { if (waiter) { const w = waiter; waiter = null; w(null); } };
    const signal: AbortSignal | undefined = init?.signal;
    signal?.addEventListener('abort', () => { failed = Object.assign(new Error('aborted'), { name: 'AbortError' }); wake(); });
    const reader = {
      async read(): Promise<{ done: boolean; value?: Uint8Array }> {
        for (;;) {
          if (failed) throw failed;
          if (chunks.length) return { done: false, value: new TextEncoder().encode(chunks.shift()!) };
          if (ended) return { done: true };
          await new Promise(r => { waiter = r; });
        }
      },
    };
    pending.push({
      body: JSON.parse(init.body),
      push: (s) => { chunks.push(s); wake(); },
      end: () => { ended = true; wake(); },
      fail: (e) => { failed = e; wake(); },
    });
    resolve({ ok: true, status: 200, body: { getReader: () => reader } });
  });
};

const tick = () => new Promise(r => setTimeout(r, 5));
const reply = (p: Pending, text: string) => {
  p.push(`data: ${JSON.stringify({ type: 'text', content: text })}\n`);
  p.push(`data: ${JSON.stringify({ type: 'done', model_used: 'minimax-test' })}\n`);
  p.end();
};

async function main() {
  // pure helpers
  const m = (id: string, role: 'user' | 'assistant', queued = false): any => ({ id, role, content: id, timestamp: '', queued });
  const list = [m('a', 'user'), m('b', 'user', true)];
  assert.deepStrictEqual(insertAfter(list, 'a', m('ra', 'assistant')).map(x => x.id), ['a', 'ra', 'b']);
  assert.deepStrictEqual(historyFor([m('a', 'user'), m('ra', 'assistant'), m('b', 'user'), m('c', 'user', true)], 'b').map(x => x.id), ['a', 'ra', 'b']);
  assert.deepStrictEqual(splitForView(list).queued.map(x => x.id), ['b']);

  React.__reset();
  const chat: any = useChat();
  const state = () => React.__state[0].v as any[];          // messages cell (first useState)
  const ids = () => state().filter((x: any) => x.id !== 'welcome').map((x: any) => `${x.role[0]}:${x.content}${x.queued ? '(q)' : ''}`);

  const firstDone = chat.sendMessage('A');
  await tick();
  assert.strictEqual(pending.length, 1, 'A is being answered');
  chat.sendMessage('B');
  chat.sendMessage('C');
  await tick();
  assert.strictEqual(pending.length, 1, 'B and C wait; no second request while A runs');
  assert.deepStrictEqual(ids(), ['u:A', 'u:B(q)', 'u:C(q)'], 'queued messages show at once, marked queued');
  chat.cancelQueued(state().find((x: any) => x.content === 'C').id);
  chat.sendMessage('D');
  assert.deepStrictEqual(ids(), ['u:A', 'u:B(q)', 'u:D(q)'], 'C removed while still queued');

  reply(pending[0], 'reply A');
  await firstDone;
  await tick(); await tick();
  assert.strictEqual(pending.length, 2, 'B starts right after A');
  assert.strictEqual(pending[1].body.message, 'B');
  const h1 = pending[1].body.history.map((x: any) => x.content);
  assert.ok(h1.includes('A') && h1.includes('reply A') && h1[h1.length - 1] === 'B' && !h1.includes('D'), `B history: ${h1}`);
  assert.deepStrictEqual(ids(), ['u:A', 'a:reply A', 'u:B', 'u:D(q)']);

  // Stop ends only B's reply; D still runs after it
  pending[1].push(`data: ${JSON.stringify({ type: 'text', content: 'partial B' })}\n`);
  await tick();
  chat.stopStreaming();
  await tick(); await tick();
  assert.strictEqual(pending.length, 3, 'D runs after B was stopped');
  assert.strictEqual(pending[2].body.message, 'D');
  reply(pending[2], 'reply D');
  await tick(); await tick();
  assert.deepStrictEqual(ids(), ['u:A', 'a:reply A', 'u:B', 'a:partial B\n\n*[Stopped]*', 'u:D', 'a:reply D']);
  assert.strictEqual(chat.queuedCount !== undefined, true);
  assert.strictEqual(React.__state.find((c: any) => c && c.v === true), undefined, 'not streaming at the end');
  console.log('chat queue check: OK');
}

main().catch((e) => { console.error(e); process.exit(1); });
