/**
 * Studio module map: every existing module stays reachable; planned/system leave the daily path.
 * Run: node --experimental-strip-types --test app/studio/moduleHome.test.ts
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  STUDIO_MODULES,
  STUDIO_TABS,
  PLANNED_MODULE_IDS,
  SYSTEM_MODULE_IDS,
  WORKROOM_PRIMARY_TABS,
  dailySheetItemIds,
  isPlannedModule,
  isSystemModule,
  moduleById,
  navHref,
  tabForRoute,
  workroomPrimaryTab,
} from './moduleHome.ts';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const leftNav = readFileSync(join(root, 'components/layout/LeftNav.tsx'), 'utf8');

function navIdsFromLeftNav(): string[] {
  const ids = [...leftNav.matchAll(/id:\s*'([^']+)'/g)].map((m) => m[1]);
  return [...new Set(ids)];
}

test('four studio tabs only', () => {
  assert.deepEqual([...STUDIO_TABS], ['max', 'today', 'work', 'money']);
});

test('every LeftNav id has a studio home (or is covered by a merge)', () => {
  const aliases: Record<string, string> = {
    customers: 'crm',
    calendar: 'schedule',
    organizer: 'schedule',
  };
  for (const id of navIdsFromLeftNav()) {
    const mapped = moduleById(id) || moduleById(aliases[id] || '');
    assert.ok(mapped, `LeftNav id ${id} is missing from STUDIO_MODULES`);
    assert.ok(mapped!.path.startsWith('/') || mapped!.path.startsWith('?'), `${id} path`);
  }
});

test('planned modules are hidden from the daily sheet', () => {
  for (const id of PLANNED_MODULE_IDS) {
    assert.equal(isPlannedModule(id), true);
    assert.equal(moduleById(id)?.hiddenFromDaily, true);
    assert.equal(moduleById(id)?.home, 'settings-planned');
  }
  assert.deepEqual(
    dailySheetItemIds(['owner', 'vetforge', 'pay', 'assist']),
    ['owner', 'pay'],
  );
});

test('system/dev tools live under Settings/System', () => {
  for (const id of SYSTEM_MODULE_IDS) {
    assert.equal(isSystemModule(id), true);
    assert.equal(moduleById(id)?.home, 'settings-system');
    assert.equal(moduleById(id)?.hiddenFromDaily, true);
  }
});

test('duplicate schedule / money / clients collapse to one home each', () => {
  assert.equal(moduleById('schedule')?.home, 'today');
  assert.equal(moduleById('tasks')?.home, 'today');
  assert.equal(moduleById('pay')?.home, 'money');
  assert.equal(moduleById('invoices')?.home, 'money');
  assert.equal(moduleById('crm')?.home, 'work-clients');
});

test('tabForRoute maps products and screens onto the four tabs', () => {
  assert.equal(tabForRoute(null, null, 'work'), 'work');
  assert.equal(tabForRoute('workroom', null, null), 'work');
  assert.equal(tabForRoute('pay', null, null), 'money');
  assert.equal(tabForRoute(null, 'invoices', null), 'money');
  assert.equal(tabForRoute(null, 'calendar', null), 'today');
  assert.equal(tabForRoute('owner', 'chat', null), 'max');
  assert.equal(tabForRoute('system', null, null), 'max');
});

test('Workroom primary tabs are four and cover the old 17 section ids', () => {
  assert.equal(WORKROOM_PRIMARY_TABS.length, 4);
  assert.deepEqual(WORKROOM_PRIMARY_TABS.map((t) => t.id), ['jobs', 'quotes', 'clients', 'docs']);
  const covered = WORKROOM_PRIMARY_TABS.flatMap((t) => [...t.sections]);
  for (const id of ['overview', 'jobhub', 'quotes', 'customers', 'docs', 'jobs', 'work-orders']) {
    assert.ok(covered.includes(id), `section ${id} should map under a primary tab`);
  }
  assert.equal(workroomPrimaryTab('quotes'), 'quotes');
  assert.equal(workroomPrimaryTab('customers'), 'clients');
  assert.equal(workroomPrimaryTab('docs'), 'docs');
  assert.equal(workroomPrimaryTab('jobhub'), 'jobs');
});

test('navHref prefers the studio map', () => {
  assert.equal(navHref({ id: 'owner' }), '/?tab=max&screen=chat');
  assert.equal(navHref({ id: 'pay' }), '/?tab=money&product=pay');
  assert.equal(navHref({ id: 'vetforge' }), '/?product=vetforge');
});

test('fixtures and map contain no live contact strings', () => {
  const blob = JSON.stringify(STUDIO_MODULES);
  assert.doesNotMatch(blob, /@gmail\.com|@empire|Nelma|McLean|\+1\s?\d/i);
});
