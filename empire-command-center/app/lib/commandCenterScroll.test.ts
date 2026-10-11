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
 * MANUAL CHECK (https://studio.empirebox.store, Dark/Gold, desktop):
 *  1. / — Max home scrolls.
 *  2. /?product=owner — chat auto-scrolls to bottom; composer stays sticky.
 *  3. Dashboard, Family Help, MiniMax usage, WhatsApp each scroll in the
 *     data-cc-scroll pane. A modal (Quick Switch / job folder) still centers.
 *  4. iPhone Safari — composer sits above the browser chrome.
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (rel: string) => readFileSync(join(root, rel), 'utf8');

test('body lock uses dvh and Max home can scroll', () => {
  const css = read('globals.css');
  assert.match(css, /height:\s*100dvh/);
  assert.match(css, /body:has\(\[data-max-home\]\)/);
  assert.match(css, /body:has\(\[data-max-home\]\)[\s\S]{0,120}overflow:\s*auto/);
  assert.match(css, /\.cy-shell\.v3:has\(\[data-max-home\]\)[\s\S]{0,80}overflow:\s*auto/);
  assert.match(css, /\.cy-shell\.v3\s*\{[\s\S]{0,160}overflow:\s*hidden/);
  assert.match(css, /\.cy-shell\.v3\s*>\s*\.v3-body\s*\{[\s\S]{0,80}min-height:\s*0/);
  assert.match(css, /\[data-cc-scroll="main"\]/);
  assert.match(css, /\[data-testid="chat-message-list"\]/);
  assert.match(css, /:not\(\[data-cc-chat\]\):not\(\.presentation-root\)/);
});

test('Max home is a sibling of the CC shell on this tree', () => {
  const page = read('page.tsx');
  assert.match(page, /deepLink \? <CommandCenterApp \/> : <MaxHome \/>/);
  const home = read('components/home3/MaxHome.tsx');
  assert.match(home, /data-max-home/);
  assert.doesNotMatch(home, /cy-shell/);
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
  assert.match(chat, /flex:\s*1/);
  assert.doesNotMatch(chat, /flex:\s*1,\s*height:\s*'100%'/);
  assert.match(chat, /msgsEndRef\.current\?\.scrollIntoView/);
  const composer = chat.slice(chat.indexOf('{/* Input area */}'));
  assert.match(composer, /flexShrink:\s*0/);
});

test('Family Help / MiniMax / WhatsApp do not clip if present', () => {
  const files = [
    'components/screens/FamilyHelpInbox.tsx',
    'components/screens/MinimaxUsageScreen.tsx',
    'components/screens/WhatsAppChatsScreen.tsx',
  ];
  for (const rel of files) {
    const abs = join(root, rel);
    if (!existsSync(abs)) continue;
    const src = readFileSync(abs, 'utf8');
    const rootOpen = src.match(/return \(\s*<div([^>]*)>/);
    assert.ok(rootOpen, `${rel} has a root div`);
    const attrs = rootOpen[1];
    const locksHeight = /h-full|height:\s*['"]100%['"]/.test(attrs);
    const hidesOverflow = /overflow-hidden|overflow:\s*['"]hidden['"]/.test(attrs);
    const innerScroll = /overflowY:\s*['"]auto['"]|overflow:\s*['"]auto['"]|overflow-y-auto/.test(src);
    assert.ok(!(locksHeight && hidesOverflow && !innerScroll), `${rel} root must not be h-full/overflow-hidden without an inner scroll`);
  }
});
