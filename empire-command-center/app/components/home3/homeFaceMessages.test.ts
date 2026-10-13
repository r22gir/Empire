/**
 * Home-face message sequence. The iframe stays mounted after Simli
 * connects — early onStatus is progress, not a teardown.
 * Run: node --experimental-strip-types --test app/components/home3/homeFaceMessages.test.ts
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  HOME_FACE_LOAD_TIMEOUT_MS,
  HOME_FACE_UNAVAILABLE,
  applyHomeFaceMessage,
  applyHomeFaceTimeout,
  iframeMounted,
  isHomeFaceHardFailure,
  startHomeFace,
  type HomeFaceView,
} from './homeFaceMessages.ts';

const root = join(dirname(fileURLToPath(import.meta.url)), '../..');
const read = (rel: string) => readFileSync(join(root, rel), 'utf8');

const live = (): HomeFaceView => startHomeFace({
  phase: 'ready',
  started: false,
  loaded: false,
  hint: 'Tap to start face',
});

test('iframe stays mounted through the Simli connected status sequence', () => {
  let view = live();
  assert.equal(iframeMounted(view), true);

  // Bug sequence: onStatus fires before startSimliFace returns, so the
  // page renderer was still 'talkinghead' and HomeFace tore the iframe down.
  view = applyHomeFaceMessage(view, {
    type: 'avatar-status',
    success: true,
    renderer: 'talkinghead',
  });
  assert.equal(iframeMounted(view), true, 'early talkinghead status must not unmount');
  assert.equal(view.phase, 'live');

  view = applyHomeFaceMessage(view, {
    type: 'avatar-status',
    success: true,
    renderer: 'simli',
  });
  assert.equal(iframeMounted(view), true, 'connected simli status must not unmount');

  view = applyHomeFaceMessage(view, {
    type: 'avatar-loaded',
    success: true,
    renderer: 'simli',
  });
  assert.equal(iframeMounted(view), true, 'avatar-loaded success keeps the iframe');
  assert.equal(view.loaded, true);
});

test('only avatar-loaded success:false or renderer:none is a hard failure', () => {
  assert.equal(isHomeFaceHardFailure({ type: 'avatar-status', success: true, renderer: 'talkinghead' }), false);
  assert.equal(isHomeFaceHardFailure({ type: 'avatar-status', success: true, renderer: 'simli' }), false);
  assert.equal(isHomeFaceHardFailure({ type: 'avatar-loaded', success: true, renderer: 'simli' }), false);
  assert.equal(isHomeFaceHardFailure({ type: 'avatar-loaded', success: false, renderer: 'none' }), true);
  assert.equal(isHomeFaceHardFailure({ type: 'avatar-status', renderer: 'none' }), true);
  assert.equal(isHomeFaceHardFailure({ type: 'avatar-loaded', success: false }), true);

  let view = live();
  view = applyHomeFaceMessage(view, { type: 'avatar-loaded', success: false, renderer: 'none' });
  assert.equal(iframeMounted(view), false);
  assert.equal(view.phase, 'orb');
  assert.equal(view.hint, HOME_FACE_UNAVAILABLE);
  assert.equal(view.started, false);
});

test('15s hang falls back to the orb with a retry note', () => {
  const view = live();
  const stillWaiting = applyHomeFaceTimeout(view, HOME_FACE_LOAD_TIMEOUT_MS - 1);
  assert.equal(iframeMounted(stillWaiting), true);
  const timedOut = applyHomeFaceTimeout(view, HOME_FACE_LOAD_TIMEOUT_MS);
  assert.equal(iframeMounted(timedOut), false);
  assert.equal(timedOut.hint, HOME_FACE_UNAVAILABLE);
  const afterLoad = applyHomeFaceTimeout(
    { ...view, loaded: true },
    HOME_FACE_LOAD_TIMEOUT_MS + 5_000,
  );
  assert.equal(iframeMounted(afterLoad), true);
});

test('HomeFace uses the hard-failure helper and 15s timeout, not renderer===simli', () => {
  const src = read('components/home3/HomeFace.tsx');
  assert.match(src, /applyHomeFaceMessage/);
  assert.match(src, /applyHomeFaceTimeout/);
  assert.match(src, /HOME_FACE_LOAD_TIMEOUT_MS/);
  assert.match(src, /HOME_FACE_UNAVAILABLE/);
  assert.doesNotMatch(src, /success !== false && renderer === 'simli'/);
  assert.match(src, /mh-face-note/);
  assert.match(src, /HOME_FACE_UNAVAILABLE/);
});

test('avatar.html onStatus posts an explicit renderer so the host is not stuck on talkinghead', () => {
  const html = readFileSync(join(root, '../public/avatar.html'), 'utf8');
  assert.match(html, /status\?\.renderer === 'simli' \? 'simli' : 'talkinghead'/);
  assert.match(html, /renderer: statusRenderer/);
  assert.match(html, /if \(statusRenderer === 'simli'\) renderer = 'simli'/);
});

test('PresentationScreen and MaxAvatarFrame still handle avatar-status / avatar-loaded', () => {
  const screen = read('components/screens/PresentationScreen.tsx');
  const frame = read('max/MaxAvatarFrame.tsx');
  assert.match(screen, /event\.data\?\.type === 'avatar-loaded'/);
  assert.match(screen, /event\.data\?\.type === 'avatar-status'/);
  assert.match(screen, /event\.data\.renderer === 'simli' \? 'Simli face only'/);
  assert.match(screen, /if \(event\.data\.success !== false\) setLoaded\(true\)/);
  assert.doesNotMatch(screen, /success !== false && renderer === 'simli'/);
  assert.match(frame, /event\.data\?\.type !== 'avatar-status'/);
  assert.match(frame, /event\.data\.renderer === 'simli' \? 'Simli face only\.'/);
  assert.doesNotMatch(frame, /success !== false && renderer === 'simli'/);
});
