import assert from 'node:assert/strict';
import test from 'node:test';
import { measureQuoteLineItems, normalizeMeasureResult } from './visionMeasure.ts';

test('nested window_info dims fill the flats Save-to-Quote reads', () => {
  const normalized = normalizeMeasureResult({
    window_info: { type: 'double-hung', estimated_width: 36, estimated_height: 60 },
    notes: 'door scale',
  });
  assert.equal(normalized.width_inches, 36);
  assert.equal(normalized.height_inches, 60);
  assert.equal(normalized.window_type, 'double-hung');
});

test('positive flat inches win over nested estimates', () => {
  const normalized = normalizeMeasureResult({
    width_inches: 30,
    height_inches: 48,
    window_type: 'picture',
    window_info: { type: 'casement', estimated_width: 99, estimated_height: 99 },
  });
  assert.equal(normalized.width_inches, 30);
  assert.equal(normalized.height_inches, 48);
  assert.equal(normalized.window_type, 'picture');
});

test('zero flats fall through to nested estimates', () => {
  const normalized = normalizeMeasureResult({
    width_inches: 0,
    height_inches: 0,
    window_info: { estimated_width: '42', estimated_height: '64 in' },
  });
  assert.equal(normalized.width_inches, 42);
  assert.equal(normalized.height_inches, 64);
});

test('Save-to-Quote lines are not $0 once dims exist', () => {
  const lines = measureQuoteLineItems({
    width_inches: 36,
    height_inches: 60,
    window_type: 'double-hung',
  });
  assert.ok(lines.every((line) => line.amount > 0));
  assert.ok(lines.some((line) => line.description.includes('36') && line.description.includes('60')));
  assert.equal(lines.some((line) => /None|undefined/.test(line.description)), false);
});

test('missing dims stay an unpriced placeholder', () => {
  const lines = measureQuoteLineItems({ width_inches: null, height_inches: null, window_type: null });
  assert.equal(lines.length, 1);
  assert.equal(lines[0].amount, 0);
});
