import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '../..');
const read = (rel: string) => readFileSync(join(root, rel), 'utf8');

test('simli-face never ships the API key and enforces 600s + idle stop', () => {
  const client = read('public/simli-face.js');
  assert.doesNotMatch(client, /SIMLI_API_KEY/);
  assert.doesNotMatch(client, /x-simli-api-key/);
  assert.match(client, /\/avatar\/simli\/session/);
  assert.match(client, /max_session_length/);
  assert.match(client, /max_idle_time/);
  assert.match(client, /stop\('cap'\)/);
  assert.match(client, /stop\('idle'\)/);
  assert.match(client, /armIdle/);
});

test('avatar.html maps amp to max_e and can skip TalkingHead for the home orb fallback', () => {
  const html = read('public/avatar.html');
  assert.match(html, /function normalizeEdition/);
  assert.match(html, /key === 'amp'/);
  assert.match(html, /return 'max_e'/);
  assert.match(html, /fallback === 'none'/);
  assert.match(html, /startSimliFace/);
  assert.match(html, /status\?\.renderer === 'simli' \? 'simli' : 'talkinghead'/);
});

test('avatar.html posts to its own origin, never *', () => {
  const html = read('public/avatar.html');
  assert.match(html, /const OWN_ORIGIN = window\.location\.origin/);
  assert.match(html, /postMessage\([^)]+,\s*OWN_ORIGIN\)/);
  assert.match(html, /event\.origin !== OWN_ORIGIN/);
  assert.doesNotMatch(html, /postMessage\([^)]+,\s*['"]\*['"]\s*\)/);
});
