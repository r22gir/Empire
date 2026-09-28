import assert from 'node:assert/strict';
import test from 'node:test';
import {
  asWorkroomQuoteLine,
  linesFromAnalyzedItems,
  linesFromMeasureResult,
  linesFromPhotoGallery,
  newWorkroomPhotoQuoteBody,
} from './photoQuote.ts';

test('measure save lines are manual_line amounts, not catalog labor', () => {
  const lines = linesFromMeasureResult({
    width_inches: 36,
    height_inches: 60,
    window_type: 'double-hung',
  });
  assert.equal(lines.length, 2);
  assert.ok(lines.every((line) => line.category === 'manual_line'));
  assert.ok(lines.every((line) => line.category !== 'labor'));
  assert.equal(lines[0].quantity, 3.8);
  assert.equal(lines[0].unit_price, 45);
  assert.equal(lines[0].amount, 171);
  assert.equal(lines[1].unit_price, 150);
  assert.equal(lines[1].amount, 150);
  assert.match(lines[0].description, /36/);
  assert.match(lines[0].description, /60/);
  assert.equal(lines[0].inputs?.unit_price, 45);
});

test('a QIS labor display line is rewritten before it hits quotes-v2', () => {
  const line = asWorkroomQuoteLine({
    category: 'labor',
    description: 'Left Wall Window reupholstery',
    quantity: 1,
    unit: 'ea',
    rate: 380,
    amount: 380,
  });
  assert.ok(line);
  assert.equal(line?.category, 'manual_line');
  assert.equal(line?.unit_price, 380);
  assert.equal(line?.amount, 380);
});

test('analyzed items with tier prices land as quote lines; unchecked items do not', () => {
  const lines = linesFromAnalyzedItems(
    [
      { name: 'Left Wall Window', type: 'drapery_panel', description: 'Left Wall Window', selected: true },
      { name: 'Skip me', type: 'valance', description: 'Skip me', selected: false, width: 40, height: 12 },
    ],
    {
      tiers: {
        A: {
          items: [
            {
              name: 'Left Wall Window',
              line_items: [
                { category: 'fabric', description: 'Grade A fabric — linen (4 yd)', quantity: 4, unit: 'yd', rate: 28, amount: 112 },
                { category: 'labor', description: 'Left Wall Window reupholstery', quantity: 1, unit: 'ea', rate: 380, amount: 380 },
              ],
            },
          ],
        },
      },
    },
  );
  assert.equal(lines.length, 2);
  assert.deepEqual(lines.map((line) => line.description), [
    'Grade A fabric — linen (4 yd)',
    'Left Wall Window reupholstery',
  ]);
  assert.equal(lines[0].amount, 112);
  assert.equal(lines[1].amount, 380);
  assert.ok(lines.every((line) => line.category === 'manual_line'));
});

test('an analyzed window with only dimensions still becomes priced lines', () => {
  const lines = linesFromAnalyzedItems([
    { type: 'roman_shade', description: 'Bedroom roman', width: 36, height: 60, selected: true },
  ]);
  assert.ok(lines.some((line) => line.amount === 171));
  assert.ok(lines.some((line) => line.amount === 150));
});

test('an analyzed item with no price is a note, not dropped', () => {
  const lines = linesFromAnalyzedItems([
    { type: 'dining_chair_seat', description: 'Dining Chair Set', quantity: 6, selected: true },
  ]);
  assert.equal(lines.length, 1);
  assert.equal(lines[0].category, 'note');
  assert.equal(lines[0].description, 'Dining Chair Set');
  assert.equal(lines[0].amount, 0);
});

test('gallery save collects every photo, and the payload is a Workroom flat quote', () => {
  const lines = linesFromPhotoGallery([
    { results: { measure: { width_inches: 36, height_inches: 60, window_type: 'double-hung' } } },
    { results: { upholstery: { furniture_type: 'Sofa', style: 'Track', estimated_labor_cost_low: 400, fabric_yards_plain: 8 } } },
  ]);
  assert.ok(lines.length >= 3);
  const body = newWorkroomPhotoQuoteBody({
    customerName: 'Photo Customer',
    lines,
    taxRate: 0,
  });
  assert.equal(body.business_unit, 'workroom');
  assert.equal(body.pricing_mode, 'flat');
  assert.equal(body.customer_name, 'Photo Customer');
  assert.equal((body.line_items as unknown[]).length, lines.length);
  assert.ok(Number(body.total) > 0);
});
