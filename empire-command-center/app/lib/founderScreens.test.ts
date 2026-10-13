import assert from 'node:assert/strict';
import test from 'node:test';
import {
  EMPIRE_ASSIST_NAV,
  FOUNDER_COMMAND_NAV_SPECS,
  FOUNDER_SCREEN_IDS,
  hookFounderDeepLinks,
  injectFounderCommandItems,
  isEmpireAssistPath,
  isFounderScreen,
  renameAssistNavItem,
} from './founderScreens.ts';

test('founder family-help spec is the wired Ayuda screen', () => {
  assert.deepEqual([...FOUNDER_SCREEN_IDS], ['family-help']);
  assert.equal(FOUNDER_COMMAND_NAV_SPECS[0].name, 'Ayuda de ediciones familiares');
  assert.equal(isFounderScreen('family-help'), true);
  assert.equal(isFounderScreen('chat'), false);
});

test('empireassist and family-help are the same view', () => {
  assert.equal(isEmpireAssistPath('/empireassist'), true);
  assert.equal(isEmpireAssistPath('/empireassist/'), true);
  assert.equal(isEmpireAssistPath('/'), false);
  assert.equal(EMPIRE_ASSIST_NAV.name, 'Empire Assist: Family Requests');
  assert.equal(EMPIRE_ASSIST_NAV.status, 'active');
  assert.equal(EMPIRE_ASSIST_NAV.screen, 'family-help');
});

test('hookFounderDeepLinks is additive', () => {
  const deep: Record<string, string> = { jobs: 'jobs' };
  const ids = new Set<string>(['chat', 'jobs']);
  hookFounderDeepLinks(deep, ids);
  assert.equal(deep.jobs, 'jobs');
  assert.equal(deep['family-help'], 'family-help');
  assert.equal(ids.has('family-help'), true);
  assert.equal(ids.has('empireassist'), true);
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
    ['owner', 'family-help', 'workroom'],
  );
  injectFounderCommandItems(groups, extras);
  assert.deepEqual(
    groups[0].items.map((item) => item.id),
    ['owner', 'family-help', 'workroom'],
  );
});

test('renameAssistNavItem promotes the dead EmpireAssist item', () => {
  const items = renameAssistNavItem([
    { id: 'assist', name: 'EmpireAssist', status: 'dev' },
    { id: 'llc', name: 'LLCFactory', status: 'active' },
  ]);
  assert.equal(items[0].name, 'Empire Assist: Family Requests');
  assert.equal(items[0].status, 'active');
  assert.equal(items[0].screen, 'family-help');
  assert.equal(items[1].name, 'LLCFactory');
});
