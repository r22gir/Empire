#!/usr/bin/env node
/**
 * Studio sign-in asset + a11y checks. No live data writes.
 */
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const manifestPath = join(root, 'public/signin-bg/manifest.json');
const cssPath = join(root, 'app/globals.css');
const pagePath = join(root, 'app/signin/page.tsx');
const bgPath = join(root, 'app/components/auth/SignInBackground.tsx');
const authPath = join(root, '..', 'backend/app/routers/auth.py');
const photosDir = join(root, 'public/workroom-showroom/photos');

const PORTFOLIO = [
  'banquette-plant-wall.jpg',
  'banquette-teal-tufted-bench.jpg',
  'bed-cognac-panel-headboard.jpg',
  'bed-mauve-channel.jpg',
  'bed-white-tufted-headboard.jpg',
  'chairs-maze-dining.jpg',
  'drapery-bay-cream-lounge.jpg',
  'drapery-bay-floral.jpg',
  'drapery-music-room.jpg',
  'drapery-window-nook.jpg',
  'romans-bay-nook.jpg',
  'seating-barstools.jpg',
  'seating-grey-sectional-bay.jpg',
  'seating-herringbone-sectional.jpg',
  'sheers-tall-living.jpg',
  'softgoods-trellis-corner.jpg',
  'valance-bath-dragonfly.jpg',
  'woodcraft-champagne-lounge.jpg',
  'woodcraft-chevron-island.jpg',
];

const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
assert.ok(Array.isArray(manifest.slides) && manifest.slides.length === 19, 'need all 19 portfolio slides');
assert.ok(manifest.intervalMs >= 7000, 'interval should be a slow crossfade');

const banned = /stock|portrait|headshot|model|people|person|face/i;
const slideNames = [];
for (const slide of manifest.slides) {
  assert.ok(slide.src && slide.alt, `slide missing src/alt: ${JSON.stringify(slide)}`);
  assert.ok(!banned.test(slide.src + slide.alt), `stock-people asset rejected: ${slide.src}`);
  const name = slide.src.split('/').pop();
  slideNames.push(name);
  assert.ok(PORTFOLIO.includes(name), `${name} is not a curated portfolio photo`);
  const abs = join(root, 'public', slide.src.replace(/^\//, ''));
  assert.ok(existsSync(abs), `missing background ${slide.src}`);
  assert.ok(statSync(abs).size < 280_000, `${slide.src} should stay optimized for fast load`);
  const original = join(photosDir, name);
  assert.ok(existsSync(original), `missing original portfolio photo ${name}`);
}

assert.deepEqual([...slideNames].sort(), [...PORTFOLIO].sort(), 'slides must be the 19 curated photos');
assert.ok(slideNames.includes('drapery-bay-cream-lounge.jpg'));
assert.ok(slideNames.includes('romans-bay-nook.jpg'));

for (const brand of ['public/brand/empire-mark.svg', 'public/brand/empire-icon.png']) {
  assert.ok(existsSync(join(root, brand)), `missing brand asset ${brand}`);
}

const css = readFileSync(cssPath, 'utf8');
assert.match(css, /prefers-reduced-motion/);
assert.match(css, /backdrop-filter/);
assert.match(css, /min-height:\s*44px/);

const page = readFileSync(pagePath, 'utf8');
assert.match(page, /Remember this device/);
assert.match(page, /empire-icon\.png/);
assert.doesNotMatch(page, /7777/);

const bg = readFileSync(bgPath, 'utf8');
assert.match(bg, /prefers-reduced-motion/);
assert.match(bg, /fetchPriority/);
assert.match(bg, /loading=\{i === 0 \? 'eager' : 'lazy'\}/);

const auth = readFileSync(authPath, 'utf8');
assert.match(auth, /getenv\("FOUNDER_PIN", ""\)/);
assert.doesNotMatch(auth, /getenv\("FOUNDER_PIN", "7777"\)/);

const originals = readdirSync(photosDir).filter((f) => f.endsWith('.jpg')).sort();
assert.equal(originals.length, 19, 'expected 19 curated portfolio photos');

console.log(`ok: ${manifest.slides.length} portfolio slides, brand assets, reduced-motion, no default PIN`);
