import assert from 'node:assert/strict';
import test from 'node:test';
import {
  HOLD_LONGER_HINT,
  clipTooShort,
  filenameForMime,
  pointerDownAction,
  recorderFormat,
  shouldStopOnPointerUp,
  sttLanguage,
  transcriptIsFailure,
} from './voiceCapture.ts';

const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1';

test('touch taps start and stop; a short lift does not cut the take', () => {
  assert.equal(pointerDownAction({ touchDevice: true, alreadyRecording: false }), 'start');
  assert.equal(shouldStopOnPointerUp({ touchDevice: true, holdArmed: false }), false);
  assert.equal(pointerDownAction({ touchDevice: true, alreadyRecording: true }), 'stop');
  assert.equal(shouldStopOnPointerUp({ touchDevice: true, holdArmed: true }), true);
  assert.equal(pointerDownAction({ touchDevice: false, alreadyRecording: false }), 'start');
  assert.equal(shouldStopOnPointerUp({ touchDevice: false, holdArmed: true }), true);
});

test('clips under half a second are dropped with the hold-longer hint', () => {
  assert.equal(clipTooShort(499), true);
  assert.equal(clipTooShort(500), false);
  assert.equal(HOLD_LONGER_HINT, 'Hold longer');
});

test('Safari records audio/mp4 and the filename matches the MIME', () => {
  const safari = recorderFormat(IPHONE, () => false);
  assert.equal(safari.mimeType, 'audio/mp4');
  assert.equal(safari.filename, 'recording.mp4');
  assert.equal(filenameForMime('audio/mp4'), 'recording.mp4');
  const chrome = recorderFormat(
    'Mozilla/5.0 Chrome/120.0.0.0',
    (mime) => mime.startsWith('audio/webm'),
  );
  assert.equal(chrome.filename, 'recording.webm');
});

test('Spanish follows the UI language and English is not forced', () => {
  assert.equal(sttLanguage('es'), 'es');
  assert.equal(sttLanguage('es-MX'), 'es');
  assert.equal(sttLanguage('en'), null);
  assert.equal(sttLanguage(null), null);
});

test('a Groq failure string is not a transcript to send', () => {
  assert.equal(transcriptIsFailure('[Transcription failed: could not process file]'), true);
  assert.equal(transcriptIsFailure('hola, necesito una cotización'), false);
});
