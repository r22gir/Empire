import assert from 'node:assert/strict';
import test from 'node:test';
import { familyHelpLabels } from './familyHelpCopy.ts';

test('Spanish is the default copy for Pedir ayuda a Max', () => {
  const es = familyHelpLabels('es');
  assert.equal(es.ask, 'Pedir ayuda a Max');
  assert.equal(es.inbox, 'Ayuda de ediciones familiares');
  const en = familyHelpLabels('en');
  assert.equal(en.ask, 'Ask Max for help');
  assert.equal(en.inbox, 'Family help');
});
