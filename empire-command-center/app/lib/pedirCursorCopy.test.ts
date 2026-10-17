import assert from 'node:assert/strict';
import test from 'node:test';
import { PEDIR_CURSOR_COPY, pedirCursorStatusLabel } from './pedirCursorCopy.ts';

test('Pedir a Cursor copy is Spanish manito', () => {
  assert.equal(PEDIR_CURSOR_COPY.button, 'Pedir a Cursor');
  assert.match(PEDIR_CURSOR_COPY.note, /no lanza nada solo/);
  assert.match(PEDIR_CURSOR_COPY.note, /Rafael da el sí final/);
  assert.equal(PEDIR_CURSOR_COPY.fieldBody, '¿Qué necesitas y por qué?');
  assert.equal(pedirCursorStatusLabel('queued'), 'En cola');
  assert.equal(pedirCursorStatusLabel('pr_open'), 'PR listo para revisar');
  assert.equal(pedirCursorStatusLabel('owner_approved'), 'Aprobado por ti');
  assert.equal(pedirCursorStatusLabel('changes_requested'), 'Pediste cambios');
  assert.equal(pedirCursorStatusLabel('declined'), 'No se hará');
  assert.match(PEDIR_CURSOR_COPY.paused, /Guárdalo y lo mandas en un rato/);
});
