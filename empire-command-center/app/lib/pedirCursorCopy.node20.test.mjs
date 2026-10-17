import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const here = dirname(fileURLToPath(import.meta.url));
const source = readFileSync(join(here, 'pedirCursorCopy.ts'), 'utf8');

test('Pedir a Cursor copy is Spanish manito (Node 20, no TS loader)', () => {
  assert.match(source, /button: 'Pedir a Cursor'/);
  assert.match(source, /no lanza nada solo/);
  assert.match(source, /Rafael da el sí final/);
  assert.match(source, /fieldBody: '¿Qué necesitas y por qué\?'/);
  assert.match(source, /queued: 'En cola'/);
  assert.match(source, /pr_open: 'PR listo para revisar'/);
  assert.match(source, /owner_approved: 'Aprobado por ti'/);
  assert.match(source, /changes_requested: 'Pediste cambios'/);
  assert.match(source, /declined: 'No se hará'/);
  assert.match(source, /Guárdalo y lo mandas en un rato/);
});
