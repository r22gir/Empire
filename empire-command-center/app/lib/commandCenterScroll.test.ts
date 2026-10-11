/**
 * Home-only scroll contract (PR #104 approach, scoped to Max home).
 *
 * Run: node --experimental-strip-types --test app/lib/commandCenterScroll.test.ts
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const read = (rel: string) => readFileSync(join(root, rel), 'utf8');

function ruleBlock(css: string, selector: string): string {
  const idx = css.indexOf(selector);
  assert.ok(idx >= 0, `missing selector ${selector}`);
  const open = css.indexOf('{', idx);
  const close = css.indexOf('}', open);
  return css.slice(open, close + 1);
}

test('body uses 100dvh and Max home unlocks page scroll', () => {
  const css = read('globals.css');
  const body = ruleBlock(css, '\nbody {');
  assert.match(body, /height:\s*100vh/);
  assert.match(body, /height:\s*100dvh/);
  assert.match(body, /overflow:\s*hidden/);

  const home = ruleBlock(css, 'body:has([data-max-home])');
  assert.match(home, /overflow:\s*auto/);
  assert.match(home, /min-height:\s*100dvh/);
  assert.match(css, /\.cy-shell\.v3:has\(\[data-max-home\]\)/);
  const nested = ruleBlock(css, '.cy-shell.v3:has([data-max-home])');
  assert.match(nested, /overflow:\s*auto/);
});

test('does not force height:auto on every main-pane child (keeps inner scroll)', () => {
  const css = read('globals.css');
  assert.doesNotMatch(
    css,
    /\[data-cc-scroll=["']main["']\]\s*>\s*\*[^\{]*\{\s*height:\s*auto\s*!important/,
    'blanket height:auto !important on pane children would break kanban / split panes',
  );
});

test('Max home is a sibling of the CC shell and marks data-max-home', () => {
  const page = read('page.tsx');
  assert.match(page, /deepLink \? <CommandCenterApp \/> : <MaxHome \/>/);
  const home = read('components/home3/MaxHome.tsx');
  assert.match(home, /data-max-home/);
  assert.doesNotMatch(home, /cy-shell/);
  const homeCss = read('components/home3/home3.css');
  assert.match(homeCss, /min-height:\s*100dvh/);
});

test('screens with their own inner scroll still declare a local scrollport', () => {
  const workroom = read('components/screens/WorkroomPage.tsx');
  assert.match(workroom, /overflow-y-auto|overflowY:\s*['"]auto['"]/);
  const chat = read('components/screens/ChatScreen.tsx');
  assert.match(chat, /overflowY:\s*['"]auto['"]|overflow-y:\s*auto/);
  const presentation = read('components/screens/PresentationScreen.tsx');
  assert.match(presentation, /overflow:\s*hidden/);
  assert.match(presentation, /overflowY:\s*['"]auto['"]/);
  const lead = read('components/screens/LeadForgePageNew.tsx');
  assert.match(lead, /overflowY:\s*['"]auto['"]/);
  const jobs = read('components/business/jobs/JobBoard.tsx');
  assert.match(jobs, /overflowY:\s*['"]auto['"]/);
  assert.match(jobs, /overflowX:\s*['"]auto['"]/);
});
