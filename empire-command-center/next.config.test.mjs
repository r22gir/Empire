import assert from 'node:assert/strict';
import test from 'node:test';
// next.config.js is the file Next.js loads (CONFIG_FILES: js, then mjs, then ts).
import config from './next.config.js';

function sizeBytes(value) {
  if (typeof value === 'number') return value;
  const match = String(value).trim().toLowerCase().match(/^(\d+(?:\.\d+)?)(b|kb|mb|gb)?$/);
  assert.ok(match, `unparsed size ${value}`);
  const amount = Number(match[1]);
  const unit = match[2] || 'b';
  const scale = { b: 1, kb: 1024, mb: 1024 ** 2, gb: 1024 ** 3 }[unit];
  return amount * scale;
}

test('rewrite proxy waits well past the 30s socket-hang-up default', () => {
  assert.ok(config.experimental.proxyTimeout >= 120_000);
});

test('docs tracing skips local virtualenvs under docs/', () => {
  const excludes = config.outputFileTracingExcludes || {};
  const patterns = [
    ...(excludes['*'] || []),
    ...(excludes['/api/docs/read'] || []),
  ];
  const joined = patterns.join('\n');
  assert.match(joined, /pdf_venv/);
  assert.match(joined, /venv/);
});

test('cloned request body accepts a multi-MB phone JPEG base64', () => {
  // 20MB file cap in PhotoAnalysisPanel becomes ~27MB of base64.
  assert.ok(sizeBytes(config.experimental.proxyClientMaxBodySize) >= 32 * 1024 * 1024);
});

test('family-help multipart (5×8 MiB files + 12 MiB voice) fits the rewrite proxy', () => {
  const familyHelpMax = (5 * 8 + 12) * 1024 * 1024;
  assert.ok(sizeBytes(config.experimental.proxyClientMaxBodySize) > familyHelpMax);
});
