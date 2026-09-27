import assert from 'node:assert/strict';
import test from 'node:test';
import { fitWithinMaxEdge, VISION_IMAGE_MAX_EDGE } from './visionImage.ts';

test('phone photo longest edge fits inside the vision max', () => {
  const fitted = fitWithinMaxEdge(4032, 3024);
  assert.equal(Math.max(fitted.width, fitted.height), VISION_IMAGE_MAX_EDGE);
  assert.equal(fitted.width, 1600);
  assert.equal(fitted.height, 1200);
});

test('portrait phone photo scales the height', () => {
  const fitted = fitWithinMaxEdge(3024, 4032);
  assert.equal(fitted.height, 1600);
  assert.equal(fitted.width, 1200);
});

test('already-small smoke size is unchanged', () => {
  assert.deepEqual(fitWithinMaxEdge(1280, 960), { width: 1280, height: 960 });
});

test('custom max edge', () => {
  assert.deepEqual(fitWithinMaxEdge(2000, 1000, 1000), { width: 1000, height: 500 });
});
