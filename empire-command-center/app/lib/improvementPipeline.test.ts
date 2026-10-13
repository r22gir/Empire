import assert from 'node:assert/strict';
import test from 'node:test';
import {
  IMPROVEMENT_PIPELINE,
  isRetryable,
  pipelineIndex,
  usageBarPct,
} from './improvementPipeline.ts';

test('pipeline is proposed > approved > planning > PR open > deployed', () => {
  assert.deepEqual(
    IMPROVEMENT_PIPELINE.map((s) => s.id),
    ['proposed', 'approved', 'planning', 'pr_open', 'deployed'],
  );
  assert.equal(pipelineIndex('proposed'), 0);
  assert.equal(pipelineIndex('approved'), 1);
  assert.equal(pipelineIndex('planning'), 2);
  assert.equal(pipelineIndex('pr_open'), 3);
  assert.equal(pipelineIndex('deployed'), 4);
  assert.equal(pipelineIndex('merge_approved'), 3);
  assert.equal(pipelineIndex('build_failed'), -1);
  assert.equal(isRetryable('build_failed'), true);
  assert.equal(isRetryable('proposed'), false);
  assert.equal(usageBarPct(20, 40), 50);
  assert.equal(usageBarPct(40, 40), 100);
  assert.equal(usageBarPct(0, 0), 0);
});
