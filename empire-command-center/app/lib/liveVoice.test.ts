import assert from 'node:assert/strict';
import test from 'node:test';
import {
  liveVoiceConnectError,
  liveVoiceTitle,
  liveVoiceUrl,
} from './liveVoice.ts';

test('AMP public origin uses its own wss path, never studio', () => {
  const url = liveVoiceUrl(
    { protocol: 'https:', host: 'amp.empirebox.store' },
    'https://studio.empirebox.store/api/v1',
  );
  assert.equal(url, 'wss://amp.empirebox.store/api/v1/avatar/live');
  assert.equal(url.includes('studio.empirebox.store'), false);
});

test('localhost still uses the backend API base for the socket', () => {
  assert.equal(
    liveVoiceUrl({ protocol: 'http:', host: 'localhost:3011' }, 'http://127.0.0.1:8011/api/v1'),
    'ws://127.0.0.1:8011/api/v1/avatar/live',
  );
});

test('AMP connect error is Spanish and does not mention studio', () => {
  const msg = liveVoiceConnectError('amp');
  assert.match(msg, /Error de conexión/);
  assert.equal(msg.toLowerCase().includes('studio'), false);
  assert.equal(liveVoiceTitle('amp', 'Max-e'), 'Max-e · Voz en vivo');
});
