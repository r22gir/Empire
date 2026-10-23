import assert from 'node:assert/strict';
import test from 'node:test';
import { familyHelpLabels } from './familyHelpCopy.ts';
import {
  HELP_MAX_FILE_BYTES,
  inferHelpMime,
  validateHelpFile,
} from './familyHelpUpload.ts';
import { currentHelpScreen, lastClientError, recordClientError } from './lastClientError.ts';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

test('Spanish is the default copy for Pedir ayuda a Max', () => {
  const es = familyHelpLabels('es');
  assert.equal(es.ask, 'Pedir ayuda a Max');
  assert.equal(es.inbox, 'Ayuda de ediciones familiares');
  assert.equal(es.confirm, 'Sí, enviar');
  assert.match(es.attachmentWarning, /no se redacta/);
  assert.equal(es.transcriptPending, 'Transcripción pendiente');
  const en = familyHelpLabels('en');
  assert.equal(en.ask, 'Ask Max for help');
  assert.equal(en.inbox, 'Family help');
  assert.match(en.attachmentWarning, /not redacted/);
});

test('client upload checks size, type, and browser MIME aliases', () => {
  assert.equal(inferHelpMime('shot.jpg', 'image/jpg'), 'image/jpeg');
  assert.equal(inferHelpMime('shot.png', 'application/octet-stream'), 'image/png');
  assert.deepEqual(
    validateHelpFile({ name: 'ok.png', type: 'image/png', size: 1200 }),
    { ok: true },
  );
  assert.equal(
    validateHelpFile({ name: 'phone.jpg', type: 'image/jpg', size: 2048 }).ok,
    true,
  );
  assert.equal(
    validateHelpFile({ name: 'x.html', type: 'image/png', size: 40 }).ok,
    false,
  );
  assert.equal(
    validateHelpFile({ name: 'huge.png', type: 'image/png', size: HELP_MAX_FILE_BYTES + 1 }).ok,
    false,
  );
});

test('Pedir ayuda button stays on AskMaxHelp and records last client error', () => {
  const here = dirname(fileURLToPath(import.meta.url));
  const ui = readFileSync(join(here, '../components/family/AskMaxHelp.tsx'), 'utf8');
  assert.match(ui, /data-testid="pedir-ayuda"/);
  assert.match(ui, /data-testid="pedir-ayuda-thread"/);
  assert.match(ui, /currentHelpScreen\('chat'\)/);
  assert.match(ui, /lastClientError\(\)/);
  recordClientError('API 500: /family-help/tickets');
  assert.equal(lastClientError(), 'API 500: /family-help/tickets');
  assert.equal(currentHelpScreen('chat'), 'chat');
});
