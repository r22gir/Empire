/**
 * EXAMPLE fixtures never leak into live / loading / empty Studio views.
 * Run: node --experimental-strip-types --test app/studio/liveGate.test.ts
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { EXAMPLE_PIPELINE } from './exampleData.ts';
import {
  gateLive,
  isExampleSearch,
  leaksExample,
  pipelineStatusText,
} from './liveGate.ts';

const root = join(dirname(fileURLToPath(import.meta.url)));
const read = (name: string) => readFileSync(join(root, name), 'utf8');

test('isExampleSearch is only true for example=1', () => {
  assert.equal(isExampleSearch('?example=1'), true);
  assert.equal(isExampleSearch('example=1&tab=work'), true);
  assert.equal(isExampleSearch(''), false);
  assert.equal(isExampleSearch('?tab=work'), false);
  assert.equal(isExampleSearch('?example=0'), false);
  assert.equal(isExampleSearch('?example=true'), false);
});

test('loading and empty live pipeline never include EXAMPLE Client A–F', () => {
  const loading = gateLive(false, null, EXAMPLE_PIPELINE);
  assert.equal(loading.kind, 'loading');
  assert.equal(loading.data, null);
  assert.equal(leaksExample(pipelineStatusText(loading)), false);
  assert.match(pipelineStatusText(loading), /Loading pipeline/);

  const empty = gateLive(false, [], EXAMPLE_PIPELINE);
  assert.equal(empty.kind, 'ready');
  assert.deepEqual(empty.data, []);
  assert.equal(leaksExample(pipelineStatusText(empty)), false);
  assert.match(pipelineStatusText(empty), /No cards in this stage/);

  const live = gateLive(false, [{ id: 'j1', kind: 'job' as const, title: 'Job 1' }], EXAMPLE_PIPELINE);
  assert.equal(live.kind, 'ready');
  assert.equal(leaksExample(pipelineStatusText(live)), false);
  assert.match(pipelineStatusText(live), /Job 1/);
});

test('EXAMPLE fixtures are returned only when the gate is on', () => {
  const gated = gateLive(true, null, EXAMPLE_PIPELINE);
  assert.equal(gated.kind, 'example');
  assert.ok(gated.data && gated.data.length > 0);
  assert.equal(leaksExample(pipelineStatusText(gated)), true);
});

test('Work / Today / Money / Job pane only use EXAMPLE_* behind the example flag', () => {
  const files = ['WorkPipeline.tsx', 'TodayCards.tsx', 'MoneyHome.tsx', 'JobContextPane.tsx', 'VoiceHome.tsx'];
  for (const name of files) {
    const src = read(name);
    const flash = /example\s*\|\|\s*!live\s*\?\s*EXAMPLE_/;
    assert.doesNotMatch(src, flash, `${name} must not flash EXAMPLE while live is null`);
    const usesFixture = /EXAMPLE_[A-Z0-9_]+/.test(src);
    if (usesFixture) {
      assert.match(src, /useExampleMode|example \?/, `${name} uses fixtures without an example gate`);
    }
  }
  const work = read('WorkPipeline.tsx');
  assert.match(work, /gateLive/);
  assert.match(work, /Loading pipeline/);
  assert.match(work, /No jobs/);
});
