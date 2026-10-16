/**
 * Pipeline stage + next-action mapping. EXAMPLE records only.
 * Run: node --experimental-strip-types --test app/studio/pipeline.test.ts
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { classifyStage, groupPipeline, nextAction, toPipelineCard } from './pipeline.ts';
import { EXAMPLE_PIPELINE } from './exampleData.ts';

test('classifies lead / quote / job / cut / install / paid', () => {
  assert.equal(classifyStage({ id: '1', kind: 'lead', title: 'Client A', status: 'new' }), 'lead');
  assert.equal(classifyStage({ id: '2', kind: 'quote', title: 'EST-####', status: 'sent' }), 'quote');
  assert.equal(classifyStage({ id: '3', kind: 'job', title: 'JOB-####', status: 'in_progress' }), 'job');
  assert.equal(classifyStage({ id: '4', kind: 'job', title: 'JOB-####', status: 'cut_ready', cutReady: true }), 'cut');
  assert.equal(classifyStage({ id: '5', kind: 'job', title: 'JOB-####', status: 'scheduled', scheduled: true }), 'install');
  assert.equal(classifyStage({ id: '6', kind: 'job', title: 'JOB-####', status: 'paid', paid: true }), 'paid');
  assert.equal(classifyStage({ id: '7', kind: 'quote', title: 'x', status: 'cancelled' }), null);
});

test('primary button is the next step', () => {
  assert.equal(nextAction({ stage: 'lead' }).label, 'Quote it');
  assert.equal(nextAction({ stage: 'quote', status: 'sent', silentDays: 8 }).label, 'Follow up → Job');
  assert.equal(nextAction({ stage: 'quote', status: 'draft' }).label, 'Send me a link');
  assert.equal(nextAction({ stage: 'quote', approved: true }).label, 'Take deposit → Job');
  assert.equal(nextAction({ stage: 'job' }).label, 'Work order');
  assert.equal(nextAction({ stage: 'cut' }).label, 'Mark cut');
  assert.equal(nextAction({ stage: 'install' }).label, 'Schedule');
  assert.equal(nextAction({ stage: 'paid' }).label, 'Pay link');
});

test('EXAMPLE pipeline groups into six stages with no live names', () => {
  const grouped = groupPipeline(EXAMPLE_PIPELINE);
  assert.ok(grouped.lead.length >= 1);
  assert.ok(grouped.quote.length >= 1);
  assert.ok(grouped.job.length >= 1);
  assert.ok(grouped.cut.length >= 1);
  assert.ok(grouped.install.length >= 1);
  assert.ok(grouped.paid.length >= 1);
  const blob = JSON.stringify(grouped);
  assert.match(blob, /Client A|EST-####|JOB-####/);
  assert.doesNotMatch(blob, /@|Nelma|McLean|\+1\d/);
  const card = toPipelineCard(EXAMPLE_PIPELINE[3]);
  assert.equal(card?.primaryLabel, 'Follow up → Job');
});
