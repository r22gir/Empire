import assert from 'node:assert/strict';
import test from 'node:test';
import {
  LIP_SYNC_OFFSET_MS,
  PREFERRED_CHUNK_BYTES,
  chunkPcm16,
  pcm16WireBytes,
  playbackDelayMs,
} from './simliLipsync.ts';

test('playback delay defaults to the Simli compose offset', () => {
  assert.equal(LIP_SYNC_OFFSET_MS, 220);
  assert.equal(playbackDelayMs(), 220);
  assert.equal(playbackDelayMs({ playback_delay_ms: 220 }), 220);
  assert.equal(playbackDelayMs({ lip_sync_offset_ms: 0, playback_delay_ms: 0 }), 0);
});

test('pcm16 wire bytes send the view, not the leftover backing buffer', () => {
  const backing = new ArrayBuffer(64);
  const view = new Int16Array(backing, 16, 8);
  view.fill(1234);
  const wire = pcm16WireBytes(view);
  assert.equal(wire.byteLength, 16);
  assert.notEqual(wire.byteLength, backing.byteLength);
});

test('pcm chunks match Simli 6000-byte frames', () => {
  const bytes = new ArrayBuffer(12800);
  const chunks = chunkPcm16(bytes, PREFERRED_CHUNK_BYTES);
  assert.deepEqual(chunks.map((c) => c.byteLength), [6000, 6000, 800]);
});
