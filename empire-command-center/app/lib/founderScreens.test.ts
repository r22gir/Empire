import assert from 'node:assert/strict';
import test from 'node:test';
import {
  FOUNDER_COMMAND_NAV_SPECS,
  FOUNDER_SCREEN_IDS,
  hookFounderDeepLinks,
  injectFounderCommandItems,
  isFounderScreen,
} from './founderScreens.ts';

test('founder screens are family-help and minimax-usage', () => {
  assert.deepEqual([...FOUNDER_SCREEN_IDS], ['family-help', 'minimax-usage']);
  assert.equal(isFounderScreen('family-help'), true);
  assert.equal(isFounderScreen('minimax-usage'), true);
  assert.equal(isFounderScreen('chat'), false);
});

test('hookFounderDeepLinks is additive', () => {
  const deep: Record<string, string> = { jobs: 'jobs' };
  const ids = new Set<string>(['chat', 'jobs']);
  hookFounderDeepLinks(deep, ids);
  assert.equal(deep.jobs, 'jobs');
  assert.equal(deep['family-help'], 'family-help');
  assert.equal(deep['minimax-usage'], 'minimax-usage');
  assert.equal(ids.has('chat'), true);
  assert.equal(ids.has('family-help'), true);
  assert.equal(ids.has('minimax-usage'), true);
});

test('injectFounderCommandItems inserts after owner and is idempotent', () => {
  const groups = [
    {
      key: 'command',
      items: [
        { id: 'owner', name: "Owner's Desk" },
        { id: 'workroom', name: 'Empire Workroom' },
      ],
    },
  ];
  const extras = FOUNDER_COMMAND_NAV_SPECS.map((spec) => ({ ...spec }));
  injectFounderCommandItems(groups, extras);
  assert.deepEqual(
    groups[0].items.map((item) => item.id),
    ['owner', 'family-help', 'minimax-usage', 'workroom'],
  );
  injectFounderCommandItems(groups, extras);
  assert.deepEqual(
    groups[0].items.map((item) => item.id),
    ['owner', 'family-help', 'minimax-usage', 'workroom'],
  );
});
