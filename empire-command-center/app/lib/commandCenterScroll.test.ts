/**
 * Command Center / Max-home scroll contract.
 *
 * The live studio app freezes the page because body is overflow:hidden and
 * the chat column is a flex child with min-height:auto (content-sized), so
 * overflow-y:auto never becomes a scrollport. This file pins the source
 * contract so a merge with the Dell's local checkout cannot silently drop it.
 *
 * Run: node --experimental-strip-types --test app/lib/commandCenterScroll.test.ts
 *
 * MANUAL CHECK (https://studio.empirebox.store, Dark/Gold):
 *  1. / — Max home scrolls through Research / Growth / Today.
 *  2. /?product=owner — chat list scrolls; composer + Voice/Code stay put;
 *     new replies still auto-scroll to the bottom (msgsEndRef).
 *  3. /?product=owner&screen=dashboard — center pane scrolls.
 *  4. /?product=workroom — module pane scrolls; left rail stays put.
 *  5. iPhone Safari — composer is not under the browser chrome (100dvh).
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (rel: string) => readFileSync(join(root, rel), 'utf8');

test('body lock uses dvh and Max home can scroll', () => {
  const css = read('globals.css');
  assert.match(css, /height:\s*100dvh/);
  assert.match(css, /body:has\(\[data-max-home\]\)/);
  assert.match(css, /body:has\(\[data-max-home\]\)[\s\S]{0,120}overflow:\s*auto/);
  assert.match(css, /\.cy-shell\.v3\s*\{[\s\S]{0,160}overflow:\s*hidden/);
  assert.match(css, /\.cy-shell\.v3\s*>\s*\.v3-body\s*\{[\s\S]{0,80}min-height:\s*0/);
  assert.match(css, /\[data-cc-scroll="main"\]/);
  assert.match(css, /\[data-testid="chat-message-list"\]/);
});

test('Command Center shell flex chain can shrink', () => {
  const app = read('CommandCenterApp.tsx');
  assert.match(app, /h-dvh/);
  assert.match(app, /min-h-0 overflow-hidden v3-body/);
  assert.match(app, /data-cc-scroll="main"/);
  assert.doesNotMatch(app, /className="cy-shell v3 h-screen/);
});

test('chat list is a min-height-0 scrollport; composer stays flex-shrink 0', () => {
  const chat = read('components/screens/ChatScreen.tsx');
  assert.match(chat, /data-testid="chat-message-list"/);
  assert.match(chat, /minHeight:\s*0/);
  assert.match(chat, /msgsEndRef\.current\?\.scrollIntoView/);
  const composer = chat.slice(chat.indexOf('{/* Input area */}'));
  assert.match(composer, /flexShrink:\s*0/);
});
