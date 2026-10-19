/**
 * Rafael's rule: every feature is reachable from the Studio shell.
 * Run: node --experimental-strip-types --test app/lib/homeReachability.test.ts
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { STUDIO_MODULES } from '../studio/moduleHome.ts';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (rel: string) => readFileSync(join(root, rel), 'utf8');

test('Studio voice home is the single talk entry; composer keeps a mic', () => {
  const voice = read('studio/VoiceHome.tsx');
  const chat = read('components/screens/ChatScreen.tsx');
  const app = read('CommandCenterApp.tsx');
  assert.match(voice, /studio-talk/);
  assert.match(voice, /useLiveVoice/);
  assert.match(voice, /studio-keyboard/);
  assert.match(chat, /aria-label=\{recording \? 'Stop recording' : 'Start recording'\}/);
  assert.match(app, /variant === 'studio'/);
  assert.match(app, /<VoiceHome/);
  assert.match(app, /<JobContextPane/);
  const studioBlock = app.slice(app.indexOf("if (variant === 'studio')"), app.indexOf("if (variant === 'studio')") + 900);
  assert.doesNotMatch(studioBlock, /<LiveVoiceCall/);
});

test('four tabs and three intents are in the daily path', () => {
  const tabs = read('studio/StudioTabs.tsx');
  const voice = read('studio/VoiceHome.tsx');
  assert.match(tabs, /k: 'max'/);
  assert.match(tabs, /k: 'today'/);
  assert.match(tabs, /k: 'work'/);
  assert.match(tabs, /k: 'money'/);
  assert.match(tabs, /studio-tab-\$\{t\.k\}/);
  assert.match(voice, /studio-intent-\$\{it\.id\}/);
  const intents = read('studio/studioIntents.ts');
  assert.match(intents, /What's on today/);
  assert.match(intents, /Quote from photo/);
  assert.match(intents, /Send me a link/);
});

test('presentation, video, telegram, memory, tasks, research stay reachable', () => {
  const need = [
    '/?screen=presentation',
    '/?screen=video',
    '/?screen=telegram',
    '/?screen=memory-bank',
    '/?tab=today',
    '/?screen=research',
  ];
  const map = STUDIO_MODULES.map((m) => m.path).join('\n');
  for (const href of need) {
    assert.ok(map.includes(href) || map.includes(href.replace('/?tab=today', '/?tab=today')), `missing ${href}`);
  }
  assert.ok(STUDIO_MODULES.some((m) => m.id === 'max-avatar'));
  assert.ok(STUDIO_MODULES.some((m) => m.id === 'tasks'));
});

test('PresentationScreen and MaxAvatarFrame pass current edition, not a hard-coded workroom', () => {
  const screen = read('components/screens/PresentationScreen.tsx');
  const frame = read('max/MaxAvatarFrame.tsx');
  assert.doesNotMatch(screen, /src=["']\/avatar\.html\?edition=workroom["']/);
  assert.doesNotMatch(frame, /src=["']\/avatar\.html\?edition=workroom["']/);
  assert.match(screen, /avatarFrameSrc\(edition\)/);
  assert.match(frame, /avatarFrameSrc\(edition\)/);
  assert.match(screen, /resolveAvatarEdition/);
  assert.match(frame, /resolveAvatarEdition/);
  assert.match(screen, /usage\?edition=\$\{encodeURIComponent\(edition\)\}/);
});

test('deep links for presentation and video are registered', () => {
  const app = read('CommandCenterApp.tsx');
  assert.match(app, /'presentation'/);
  assert.match(app, /'video'/);
});

test('preview cockpit and ring use StudioAuthGate', () => {
  const cockpit = read('preview/cockpit/layout.tsx');
  const ring = read('preview/ring/layout.tsx');
  assert.match(cockpit, /StudioAuthGate/);
  assert.match(ring, /StudioAuthGate/);
});

test('one shell: page.tsx always renders CommandCenterApp studio variant', () => {
  const page = read('page.tsx');
  assert.match(page, /<CommandCenterApp variant="studio" \/>/);
  assert.doesNotMatch(page, /deepLink \? <CommandCenterApp/);
});
