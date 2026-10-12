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

test('in-app deep links are clickable; job file paths stay plain text', () => {
  assert.equal(safeUrl('/?screen=presentation'), '/?screen=presentation');
  assert.equal(safeUrl('/?screen=presentation&mode=presentation'), '/?screen=presentation&mode=presentation');
  assert.equal(safeUrl('/?product=improvements'), '/?product=improvements');
  assert.equal(safeUrl('/'), '/');
  assert.equal(safeUrl('/ayuda'), '/ayuda');
  assert.equal(safeUrl('//evil.example'), '');
  assert.equal(safeUrl('/jobs/wall-unit/led.pdf'), '');

  const reply = 'Presentation mode is on MAX Home. [Open Presentation](/?screen=presentation)';
  assert.equal(markdownLinkCount(reply) >= 1, true);
});

test('safeUrl rejects javascript: and data: hrefs', () => {
  assert.equal(safeUrl('javascript:alert(1)'), '');
  assert.equal(safeUrl('JAVASCRIPT:alert(1)'), '');
  assert.equal(safeUrl('data:text/html,<script>alert(1)</script>'), '');
  assert.equal(safeUrl('vbscript:msgbox(1)'), '');
  assert.equal(safeUrl('file:///etc/passwd'), '');
});
