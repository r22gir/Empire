/**
 * Job card + phase helpers. Mock records only — no live data or real contacts.
 * Run: node --experimental-strip-types --test app/studio/jobStages.test.ts
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import {
  activeJobCards,
  canonicalizeStage,
  jobContacts,
  jobNextDate,
  jobTotal,
  movedToast,
  nextStage,
  phaseHistoryFromEvents,
  stageLabel,
  stagePatchRequest,
  toHomeJobCard,
} from './jobStages.ts';

const hrefFor = (id: string) => `/?product=workroom&section=jobhub&job=${id}`;

const MOCK_JOBS = [
  {
    id: 'job-wr-1',
    title: 'Living room drapery',
    job_number: 'JOB-####',
    client_name: 'Client A',
    business_unit: 'workroom',
    pipeline_stage: 'in_production',
    status: 'in_progress',
    scheduled_date: '2026-10-28',
    quoted_amount: 4200,
    quote_id: 'q-wr-1',
  },
  {
    id: 'job-wc-1',
    title: 'CNC panel set',
    job_number: 'JOB-####',
    client_name: 'Client D',
    business_unit: 'woodcraft',
    pipeline_stage: 'ready',
    status: 'in_progress',
    due_date: '2026-10-30',
    estimated_value: 1800,
  },
  {
    id: 'job-done',
    title: 'Closed drapery',
    client_name: 'Client F',
    business_unit: 'workroom',
    pipeline_stage: 'paid_closed',
    status: 'completed',
    quoted_amount: 900,
  },
  {
    id: 'job-x',
    title: 'Cancelled shade',
    client_name: 'Client X',
    status: 'cancelled',
    pipeline_stage: 'lead',
  },
];

test('canonicalizes intake / quoted / paid aliases onto the 11 kanban stages', () => {
  assert.equal(canonicalizeStage('intake'), 'lead');
  assert.equal(canonicalizeStage('quoted'), 'estimate_sent');
  assert.equal(canonicalizeStage('approved'), 'deposit_paid');
  assert.equal(canonicalizeStage('in_progress'), 'in_production');
  assert.equal(canonicalizeStage('paid'), 'paid_closed');
  assert.equal(stageLabel('fabric_ordered'), 'Fabric ordered');
});

test('next stage is the following kanban column; last stage has none', () => {
  assert.equal(nextStage('lead')?.key, 'estimate_sent');
  assert.equal(nextStage('in_production')?.key, 'ready');
  assert.equal(nextStage('final_invoice')?.key, 'paid_closed');
  assert.equal(nextStage('paid_closed'), null);
});

test('active cards include every business and drop closed or cancelled jobs', () => {
  const cards = activeJobCards(MOCK_JOBS, hrefFor);
  assert.equal(cards.length, 2);
  assert.deepEqual(cards.map((c) => c.business).sort(), ['WoodCraft', 'Workroom']);
  assert.equal(cards.some((c) => c.id === 'job-done' || c.id === 'job-x'), false);
  const wr = cards.find((c) => c.id === 'job-wr-1');
  assert.ok(wr);
  assert.equal(wr.name, 'Living room drapery');
  assert.equal(wr.client, 'Client A');
  assert.equal(wr.phase, 'In production');
  assert.equal(wr.nextDate, '2026-10-28');
  assert.equal(wr.total, 4200);
  assert.equal(wr.totalLabel, '$4,200');
  assert.match(wr.href, /job=job-wr-1/);
  assert.equal(wr.quoteId, 'q-wr-1');
  assert.match(String(wr.estimateHref), /quotes-v2/);
  assert.match(String(wr.estimateHref), /q-wr-1/);
  const blob = JSON.stringify(cards);
  assert.doesNotMatch(blob, /@|Nelma|McLean|\+1\d/);
});

test('card mapping uses next date and total when present, omits empty money', () => {
  const card = toHomeJobCard({
    id: 'job-plain',
    title: 'Banquette',
    client_name: 'Client B',
    pipeline_stage: 'lead',
  }, hrefFor);
  assert.ok(card);
  assert.equal(card.nextDate, null);
  assert.equal(card.total, null);
  assert.equal(card.totalLabel, '');
  assert.equal(jobNextDate({ install_date: '2026-11-02T09:00:00' }), '2026-11-02');
  assert.equal(jobTotal({ payment_strip: { total: 12 } }), 12);
});

test('phase history reads status_change events and keeps from → to', () => {
  const hist = phaseHistoryFromEvents([
    { event_type: 'note', summary: 'Called Client A', created_at: '2026-10-20' },
    { event_type: 'status_change', summary: 'Status: lead -> estimate_sent', created_at: '2026-10-21', actor: 'founder', metadata: { from: 'lead', to: 'estimate_sent' } },
    { event_type: 'status_change', summary: 'Status: estimate_sent -> deposit_paid', created_at: '2026-10-22', metadata: '{"from":"estimate_sent","to":"deposit_paid"}' },
  ]);
  assert.equal(hist.length, 2);
  assert.equal(hist[0].to, 'deposit_paid');
  assert.equal(hist[1].from, 'lead');
  assert.equal(hist[1].actor, 'founder');
});

test('stage PATCH path and move toast stay on mock ids', () => {
  const req = stagePatchRequest('job-wr-1', 'ready', 'cut done');
  assert.equal(req.method, 'PATCH');
  assert.equal(req.path, '/jobs/job-wr-1/stage');
  assert.deepEqual(req.body, { stage: 'ready', notes: 'cut done' });
  assert.equal(movedToast('Living room drapery', 'in_production', 'ready'), 'Moved Living room drapery from In production to Ready');
});

test('contacts reuse the job + customer record and skip empty rows', () => {
  const contacts = jobContacts(
    { client_name: 'Client A', client_phone: '555-0100', contacts: [{ name: 'Site contact', role: 'PM', email: 'pm@example.test' }] },
    { name: 'Client A', email: 'client-a@example.test' },
  );
  assert.equal(contacts[0].name, 'Client A');
  assert.equal(contacts[0].role, 'Client');
  assert.equal(contacts[1].role, 'PM');
  assert.doesNotMatch(JSON.stringify(contacts), /Nelma|McLean/);
});
