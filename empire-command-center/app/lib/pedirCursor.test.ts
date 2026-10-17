import assert from 'node:assert/strict';
import test from 'node:test';
import {
  PEDIR_CURSOR_APPROVED,
  PEDIR_CURSOR_NOTE,
  PEDIR_CURSOR_PAUSED,
  statusChip,
} from './pedirCursorCopy.ts';

test('Pedir a Cursor copy is Spanish manito tone', () => {
  assert.match(PEDIR_CURSOR_NOTE, /no lanza nada/);
  assert.match(PEDIR_CURSOR_NOTE, /Rafael da el sí final/);
  assert.match(PEDIR_CURSOR_PAUSED, /Manito/);
  assert.match(PEDIR_CURSOR_PAUSED, /Guárdalo/);
  assert.match(PEDIR_CURSOR_APPROVED, /aprobado de tu lado/);
  assert.equal(statusChip('queued'), 'En cola');
  assert.equal(statusChip('in_progress'), 'En progreso');
  assert.equal(statusChip('pr_open'), 'PR listo para revisar');
  assert.equal(statusChip('owner_approved'), 'Aprobado por ti');
  assert.equal(statusChip('changes_requested'), 'Pediste cambios');
  assert.equal(statusChip('done'), 'Listo');
  assert.equal(statusChip('declined'), 'No se hará');
});
