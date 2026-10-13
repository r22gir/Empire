import assert from 'node:assert/strict';
import test from 'node:test';
import {
  DEFAULT_TRANSCRIPT_OVERLAY,
  TRANSCRIPT_OVERLAY_STORAGE_KEY,
  clampFreePlacement,
  coversAvatarFace,
  loadTranscriptOverlayPlacement,
  overlayMaxWidth,
  parseTranscriptOverlayPlacement,
  transcriptOverlayBoxStyle,
} from './transcriptOverlay.ts';

test('default dock is lower-third bottom so the face is not covered', () => {
  assert.equal(DEFAULT_TRANSCRIPT_OVERLAY.dock, 'bottom');
  assert.equal(coversAvatarFace(DEFAULT_TRANSCRIPT_OVERLAY.dock), false);
  assert.ok(DEFAULT_TRANSCRIPT_OVERLAY.y >= 0.75);
});

test('top dock is the only preset that covers the avatar face', () => {
  assert.equal(coversAvatarFace('top'), true);
  assert.equal(coversAvatarFace('bottom'), false);
  assert.equal(coversAvatarFace('left'), false);
  assert.equal(coversAvatarFace('right'), false);
  assert.equal(coversAvatarFace('free'), false);
});

test('parse falls back to the face-clear default for junk input', () => {
  assert.deepEqual(parseTranscriptOverlayPlacement(null), DEFAULT_TRANSCRIPT_OVERLAY);
  assert.equal(parseTranscriptOverlayPlacement({ dock: 'sideways' }).dock, 'bottom');
  assert.equal(parseTranscriptOverlayPlacement({ dock: 'left', x: 2, y: -1 }).x, 1);
  assert.equal(parseTranscriptOverlayPlacement({ dock: 'left', x: 2, y: -1 }).y, 0);
});

test('load reads persisted dock from storage', () => {
  const store = {
    getItem(key: string) {
      assert.equal(key, TRANSCRIPT_OVERLAY_STORAGE_KEY);
      return JSON.stringify({ dock: 'right', x: 0.2, y: 0.3 });
    },
  };
  const loaded = loadTranscriptOverlayPlacement(store);
  assert.equal(loaded.dock, 'right');
  assert.equal(loaded.x, 0.2);
});

test('free drag stays on a 390px phone viewport', () => {
  const viewport = { width: 390, height: 844 };
  const panel = { width: overlayMaxWidth(390), height: 180 };
  assert.equal(panel.width, 360);
  const offscreen = clampFreePlacement(-40, 900, panel, viewport);
  assert.equal(offscreen.dock, 'free');
  assert.ok(offscreen.x >= 0 && offscreen.x <= 1);
  assert.ok(offscreen.y >= 0 && offscreen.y <= 1);
});

test('bottom dock style sits low (below the face), not at the vertical center', () => {
  const style = transcriptOverlayBoxStyle(DEFAULT_TRANSCRIPT_OVERLAY, { width: 1280, height: 800 });
  assert.equal(style.bottom, 88);
  assert.equal(style.top, undefined);
  assert.ok(Number(style.bottom) < 800 * 0.2);
});

test('390px overlay width leaves 12px gutters and a short max height', () => {
  const style = transcriptOverlayBoxStyle(DEFAULT_TRANSCRIPT_OVERLAY, { width: 390, height: 844 });
  assert.equal(style.width, 360);
  assert.equal(style.maxHeight, '28vh');
});
