/**
 * Rafael's rule: every feature is reachable from Command Center home / left nav.
 * Run: node --experimental-strip-types --test app/lib/homeReachability.test.ts
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (rel: string) => readFileSync(join(root, rel), 'utf8');

function hrefs(src: string): string[] {
  return [...src.matchAll(/href=["'`]([^"'`]+)["'`]/g)].map(m => m[1]);
}

test('hero exposes Talk (LiveVoiceCall) and Presentation mode', () => {
  const home = read('components/home3/MaxHome.tsx');
  assert.match(home, /<HomeFace/);
  assert.match(home, /variant="hero"/);
  assert.match(home, /label="Talk"/);
  assert.match(home, /data-testid="mh-presentation"/);
  assert.match(home, /\/\?screen=presentation&mode=presentation/);
  assert.match(home, /data-testid="mh-quick-actions"/);
});

test('home quick actions and left nav cover URL/hotkey-only features', () => {
  const home = read('components/home3/MaxHome.tsx');
  const nav = read('components/layout/LeftNav.tsx');
  const combined = home + '\n' + nav;
  const need = [
    '/?screen=presentation',
    '/?screen=video',
    '/?screen=telegram',
    '/?screen=memory-bank',
    '/?screen=tasks',
    '/?screen=research',
  ];
  for (const href of need) {
    assert.ok(combined.includes(href), `missing visible entry ${href}`);
  }
  assert.match(nav, /name: 'MAX Avatar'/);
  assert.match(nav, /screen: 'presentation'/);
  assert.match(nav, /name: 'Video Call'/);
  assert.match(nav, /name: 'Telegram'/);
  assert.match(nav, /name: 'Memory Bank'/);
  const listed = hrefs(home);
  assert.ok(listed.some(h => h.includes('screen=presentation')), 'home links to presentation');
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
