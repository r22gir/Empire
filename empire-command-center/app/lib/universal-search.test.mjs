import test from 'node:test';
import assert from 'node:assert/strict';
import {
  DEBOUNCE_MS,
  REQUIRED_SCREENS,
  WORKROOM_ONLY_SCREENS,
  actionHref,
  filterHitsForEdition,
  flattenGroups,
  groupHits,
  isDraftReply,
  isFamilyEditionId,
  parseSearchHref,
  resultForEnter,
  shouldFetch,
  topResult,
} from './universal-search.ts';

const hit = (over) => ({
  id: 'x',
  type: 'screen',
  title: 'X',
  href: '/?screen=x',
  action: { kind: 'open', label: 'Open', href: '/?screen=x' },
  ...over,
});

test('required screens include Improvements, Tokens, Family help, Organizer, MiniMax, Presentation', () => {
  for (const id of ['improvements', 'tokens', 'family-help', 'organizer', 'minimax-usage', 'presentation-mode']) {
    assert.ok(REQUIRED_SCREENS.includes(id), id);
  }
});

test('debounce is 200ms and fetch starts at 1 char', () => {
  assert.equal(DEBOUNCE_MS, 200);
  assert.equal(shouldFetch(''), false);
  assert.equal(shouldFetch('  '), false);
  assert.equal(shouldFetch('m'), true);
  assert.equal(shouldFetch('Marley'), true);
});

test('flatten + enter opens the top result including jobs', () => {
  const groups = [
    { type: 'screen', label: 'Screens', items: [hit({ id: 'screen:tokens', title: 'Tokens' })] },
    { type: 'job', label: 'Jobs', items: [hit({ id: 'job:1', type: 'job', title: 'Marley', href: '/?product=workroom&section=jobhub&job=1', score: 0.99 })] },
  ];
  const flat = flattenGroups(groups);
  assert.equal(flat[0].type, 'screen');
  const payload = {
    groups,
    results: [
      hit({ id: 'job:1', type: 'job', title: 'Marley', href: '/?product=workroom&section=jobhub&job=1' }),
      hit({ id: 'screen:tokens', title: 'Tokens' }),
    ],
    top: hit({ id: 'job:1', type: 'job', title: 'Marley', href: '/?product=workroom&section=jobhub&job=1' }),
  };
  const top = topResult(payload);
  assert.equal(top.type, 'job');
  assert.equal(top.title, 'Marley');
  const opened = resultForEnter(payload.results, 0);
  assert.equal(opened.type, 'job');
  assert.match(opened.href, /job=1/);
});

test('enter with no highlight still opens index 0 (job)', () => {
  const jobs = [hit({ id: 'job:9', type: 'job', title: 'Marley job', href: '/?product=workroom&section=jobhub&job=9' })];
  assert.equal(resultForEnter(jobs, -1).id, 'job:9');
  assert.equal(resultForEnter([], 0), null);
});

test('family edition drops Workroom-only screens and jobs', () => {
  assert.equal(isFamilyEditionId('maxine'), true);
  assert.equal(isFamilyEditionId('max_e'), true);
  assert.equal(isFamilyEditionId('main'), false);
  const hits = [
    hit({ id: 'screen:improvements', extra: { feature_id: 'improvements' }, title: 'Improvements' }),
    hit({ id: 'screen:workroom', extra: { feature_id: 'workroom', workroom_only: true }, title: 'Workroom' }),
    hit({ id: 'job:1', type: 'job', title: 'Marley' }),
    hit({ id: 'quote:1', type: 'quote', title: 'Family quote' }),
  ];
  const family = filterHitsForEdition(hits, 'max_e');
  assert.equal(family.some(h => h.type === 'job'), false);
  assert.equal(family.some(h => h.title === 'Workroom'), false);
  assert.equal(family.some(h => h.title === 'Improvements'), true);
  assert.ok(WORKROOM_ONLY_SCREENS.has('workroom'));
});

test('Maxine never surfaces Argos Campestre', () => {
  const hits = [
    hit({ id: 'person:c2', type: 'person', title: 'Argos Campestre SA' }),
    hit({ id: 'person:c1', type: 'person', title: 'Camilo' }),
  ];
  const kept = filterHitsForEdition(hits, 'maxine');
  assert.deepEqual(kept.map(h => h.title), ['Camilo']);
});

test('groupHits keeps type order', () => {
  const groups = groupHits([
    hit({ id: 'q', type: 'quote', title: 'Q' }),
    hit({ id: 's', type: 'screen', title: 'S' }),
    hit({ id: 'j', type: 'job', title: 'J' }),
  ]);
  assert.deepEqual(groups.map(g => g.type), ['screen', 'job', 'quote']);
});

test('parseSearchHref and actions', () => {
  const p = parseSearchHref('/?product=workroom&section=jobhub&job=42');
  assert.equal(p.product, 'workroom');
  assert.equal(p.section, 'jobhub');
  assert.equal(p.job, '42');
  const call = hit({
    action: { kind: 'call', label: 'Call', phone: '3055550100', href: '/?product=crm' },
  });
  assert.equal(actionHref(call), 'tel:3055550100');
  const mail = hit({
    action: { kind: 'draft_reply', label: 'Draft reply', mail_id: 'm1', source: 'gmail' },
  });
  assert.equal(isDraftReply(mail), true);
});
