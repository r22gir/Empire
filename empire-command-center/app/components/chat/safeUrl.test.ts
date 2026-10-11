import assert from 'node:assert/strict';
import test from 'node:test';
import { markdownLinkCount, safeUrl } from './safeUrl.ts';

test('studio file links render as clickable hrefs; relative job paths do not', () => {
  const abs = 'https://studio.empirebox.store/api/v1/files/found?t=abc.sig';
  const found = '/api/v1/files/found?t=abc.sig';
  assert.equal(safeUrl(abs), abs);
  assert.equal(safeUrl(found), found);
  assert.equal(safeUrl('/jobs/wall-unit/led.pdf'), '');
  assert.equal(safeUrl('~/jobs/wall-unit/led.pdf'), '');

  const firstReply = `Here are the wall unit LED docs.\n\nSources\n1. [Wall-Unit-LED-Spec.pdf](${abs})\n2. [Layout](${found})`;
  assert.equal(markdownLinkCount(firstReply) >= 2, true);
});
