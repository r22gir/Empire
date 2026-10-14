/**
 * Growth button contrast + mapping.
 * Run: node --experimental-strip-types --test app/components/growth/sharedBtn.test.ts
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '../..');
const read = (rel: string) => readFileSync(join(root, rel), 'utf8');

function relLuminance(hex: string): number {
  const c = hex.replace('#', '');
  const parts = c.length === 3 ? c.split('').map((x) => x + x) : [c.slice(0, 2), c.slice(2, 4), c.slice(4, 6)];
  const [r, g, b] = parts.map((x) => {
    const v = parseInt(x, 16) / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const L1 = relLuminance(a);
  const L2 = relLuminance(b);
  const [hi, lo] = L1 > L2 ? [L1, L2] : [L2, L1];
  return (hi + 0.05) / (lo + 0.05);
}

function brighten(hex: string, amount = 1.08): string {
  const c = hex.replace('#', '');
  const parts = [c.slice(0, 2), c.slice(2, 4), c.slice(4, 6)].map((x) => {
    const v = Math.min(255, Math.round(parseInt(x, 16) * amount));
    return v.toString(16).padStart(2, '0');
  });
  return `#${parts.join('')}`;
}

const AA = 4.5;

const DARK = {
  primary: ['#e6edf3', '#0b0f14'],
  ok: ['#14532d', '#f7fee7'],
  info: ['#1e3a8a', '#eff6ff'],
  danger: ['#7f1d1d', '#fef2f2'],
  accent: ['#4c1d95', '#f5f3ff'],
  disabled: ['#0b0f14', '#8b96a3'],
} as const;

const GOLD = {
  primary: ['#b8912f', '#16191c'],
  ok: ['#2f6b45', '#f7f3ea'],
  info: ['#2c5a85', '#f7f3ea'],
  danger: ['#8a2a2a', '#f7f3ea'],
  accent: ['#5e4590', '#f7f3ea'],
  disabled: ['#f7f3ea', '#5c564a'],
} as const;

test('shared btn helper never defaults to color:#fff', () => {
  const src = read('components/growth/shared.tsx');
  assert.match(src, /export function btn\(/);
  assert.doesNotMatch(src, /color = '#fff'/);
  assert.match(src, /btnClass/);
  assert.match(src, /gf-btn gf-btn--/);
  assert.match(src, /#1a1a1a': 'primary'/);
});

test('dark + gold pairs meet WCAG AA in default, hover, and disabled', () => {
  for (const [name, [bg, fg]] of Object.entries(DARK)) {
    assert.ok(contrast(bg, fg) >= AA, `dark ${name} ${bg}/${fg} = ${contrast(bg, fg).toFixed(2)}`);
    if (name !== 'disabled') {
      assert.ok(contrast(brighten(bg), fg) >= AA, `dark ${name} hover ${contrast(brighten(bg), fg).toFixed(2)}`);
    }
  }
  for (const [name, [bg, fg]] of Object.entries(GOLD)) {
    assert.ok(contrast(bg, fg) >= AA, `gold ${name} ${bg}/${fg} = ${contrast(bg, fg).toFixed(2)}`);
    if (name !== 'disabled') {
      assert.ok(contrast(brighten(bg), fg) >= AA, `gold ${name} hover ${contrast(brighten(bg), fg).toFixed(2)}`);
    }
  }
});

test('Improvements New request uses the shared primary class, not #1a1a1a', () => {
  const page = read('components/growth/ImprovementsPage.tsx');
  assert.match(page, /data-testid="imp-new-request"/);
  assert.match(page, /<Btn[\s\S]*New request/);
  assert.doesNotMatch(page, /btn\('#1a1a1a'\)/);
  assert.doesNotMatch(page, /btn\(['"]#/);
});

test('nearby growth screens use Btn instead of dark-on-dark inline fills', () => {
  for (const rel of ['components/growth/ApprovalsQueue.tsx', 'components/growth/RoiDashboard.tsx']) {
    const src = read(rel);
    assert.match(src, /from '\.\/shared'/);
    assert.match(src, /<Btn /);
    assert.doesNotMatch(src, /btn\('#1a1a1a'\)/);
  }
});

test('tokens.css defines gf-btn states including disabled and loading', () => {
  const css = read('v3/tokens.css');
  assert.match(css, /\.gf-btn\s*\{/);
  assert.match(css, /\.gf-btn:hover:not\(:disabled\):not\(\[aria-busy="true"\]\)/);
  assert.match(css, /\.gf-btn:disabled/);
  assert.match(css, /\.gf-btn\[aria-busy="true"\]/);
  assert.match(css, /-webkit-text-fill-color/);
  assert.match(css, /html\[data-theme="gold"\] \.v3/);
  assert.match(css, /--gf-primary-bg: var\(--gd-gold/);
});
