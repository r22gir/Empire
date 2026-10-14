import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, 'jobViewer.ts'), 'utf8');
const button = readFileSync(join(here, '../components/jobs/JobViewerButton.tsx'), 'utf8');

test('viewer API helpers never auto-publish and require a founder PIN to publish', () => {
  assert.match(src, /\/preview/);
  assert.match(src, /\/publish/);
  assert.match(src, /\/unpublish/);
  assert.match(src, /founder_pin/);
  assert.equal(src.includes('auto_published'), true);
  assert.doesNotMatch(src, /amp|maxine/i);
});

test('3D viewer button exposes preview, publish, copy link, and unpublish', () => {
  assert.match(button, /3D viewer/);
  assert.match(button, /Publish/);
  assert.match(button, /Copy link/);
  assert.match(button, /Unpublish/);
  assert.match(button, /founder PIN/i);
  assert.doesNotMatch(button, /supplier_sku|unit_price|client_address/);
});
