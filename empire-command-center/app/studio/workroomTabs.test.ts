/**
 * Workroom daily tabs are four; the old 17 sections remain in the file.
 * Run: node --experimental-strip-types --test app/studio/workroomTabs.test.ts
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const src = readFileSync(join(dirname(fileURLToPath(import.meta.url)), '..', 'components/screens/WorkroomPage.tsx'), 'utf8');

test('Workroom shows four primary tabs plus More', () => {
  assert.match(src, /WORKROOM_PRIMARY/);
  assert.match(src, /label: 'Jobs'/);
  assert.match(src, /label: 'Quotes'/);
  assert.match(src, /label: 'Clients'/);
  assert.match(src, /label: 'Docs'/);
  assert.match(src, />More</);
});

test('old Workroom sections are still defined so deep links work', () => {
  for (const id of ['overview', 'jobhub', 'creations', 'quotes', 'finance', 'invoices', 'expenses', 'customers', 'inventory', 'jobs', 'schedule', 'work-orders', 'templates', 'tasks', 'analysis', 'payments', 'docs']) {
    assert.match(src, new RegExp(`id: '${id}'`));
  }
});
