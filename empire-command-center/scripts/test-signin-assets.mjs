#!/usr/bin/env node
/**
 * Studio sign-in asset + a11y checks. No live data writes.
 */
import { readFileSync, existsSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const manifestPath = join(root, 'public/signin-bg/manifest.json');
const cssPath = join(root, 'app/globals.css');
const pagePath = join(root, 'app/signin/page.tsx');
const bgPath = join(root, 'app/components/auth/SignInBackground.tsx');

const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
assert.ok(Array.isArray(manifest.slides) && manifest.slides.length >= 2, 'need rotating slides');
assert.ok(manifest.intervalMs >= 4000, 'interval should be gentle');

const banned = /stock|portrait|headshot|model|people|person|face/i;
for (const slide of manifest.slides) {
  assert.ok(slide.src && slide.alt, `slide missing src/alt: ${JSON.stringify(slide)}`);
  assert.ok(!banned.test(slide.src + slide.alt), `stock-people asset rejected: ${slide.src}`);
  const abs = join(root, 'public', slide.src.replace(/^\//, ''));
  assert.ok(existsSync(abs), `missing background ${slide.src}`);
  assert.ok(statSync(abs).size < 80_000, `${slide.src} should stay small for fast load`);
  if (slide.diagram) {
    const d = join(root, 'public', slide.diagram.replace(/^\//, ''));
    assert.ok(existsSync(d), `missing workroom diagram ${slide.diagram}`);
  }
}

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

const bg = readFileSync(bgPath, 'utf8');
assert.match(bg, /prefers-reduced-motion/);
assert.match(bg, /fetchPriority/);

console.log(`ok: ${manifest.slides.length} sign-in slides, brand assets, reduced-motion`);
