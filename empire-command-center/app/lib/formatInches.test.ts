import assert from 'node:assert/strict';
import test from 'node:test';
import { formatInches } from './formatInches.ts';

test('formatInches converts numbers to whole inches and fractions', () => {
  assert.equal(formatInches(72), '72"');
  assert.equal(formatInches(72.0), '72"');
  assert.equal(formatInches(14.5), '14½"');
  assert.equal(formatInches(14.25), '14¼"');
  assert.equal(formatInches(14.75), '14¾"');
  assert.equal(formatInches(0.5), '½"');
  assert.equal(formatInches(36.125), '36⅛"');
  assert.equal(formatInches(36.375), '36⅜"');
  assert.equal(formatInches(36.625), '36⅝"');
  assert.equal(formatInches(36.875), '36⅞"');
});

test('formatInches handles null, undefined, and non-numeric values safely', () => {
  assert.equal(formatInches(null), '');
  assert.equal(formatInches(undefined), '');
  assert.equal(formatInches(''), '');
  assert.equal(formatInches('abc'), '');
});
