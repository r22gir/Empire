import assert from 'node:assert/strict';
import test from 'node:test';
import { productTitle } from '../fine-fabrics/api.ts';
import {
  MOCKUP_ITEMS,
  SHOP_THIS_LOOK,
  TEMPLATES,
  parseInches,
  parseRepeat,
  pointInPolygon,
  polygonToPath,
  quoteHref,
  sampleHref,
  tileSizePx,
  uploadIsClientOnly,
} from '../fine-fabrics/seeOnItem.ts';

test('six mockup templates are defined', () => {
  assert.deepEqual(
    MOCKUP_ITEMS.map((item) => item.id),
    ['pillow', 'drapery_panel', 'roman_shade', 'sofa', 'accent_chair', 'bench'],
  );
  assert.equal(TEMPLATES.length, 6);
  for (const template of TEMPLATES) {
    assert.ok(template.fill.startsWith('M'));
    assert.ok(template.shade.length >= 1);
  }
});

test('tile size scales from repeat and width', () => {
  const unknown = tileSizePx('', '');
  const known = tileSizePx('54 in', '27x25');
  assert.equal(unknown, 64);
  assert.ok(known >= 28 && known <= 140);
  assert.notEqual(known, unknown);
  assert.equal(parseInches('54 in'), 54);
  assert.deepEqual(parseRepeat('27 x 25'), { h: 27, v: 25 });
});

test('sample and quote CTAs stay on the store', () => {
  assert.equal(sampleHref(12), '/fine-fabrics/samples?id=12');
  assert.equal(
    quoteHref(12, 'roman_shade', 'L001-Navy'),
    '/fine-fabrics/quote?product_id=12&item=roman_shade&code=L001-Navy',
  );
});

test('upload polygon is client-side geometry only', () => {
  const poly = [
    { x: 0, y: 0 },
    { x: 10, y: 0 },
    { x: 10, y: 10 },
    { x: 0, y: 10 },
  ];
  assert.equal(polygonToPath(poly), 'M0,0 L10,0 L10,10 L0,10 Z');
  assert.equal(pointInPolygon({ x: 5, y: 5 }, poly), true);
  assert.equal(pointInPolygon({ x: 20, y: 20 }, poly), false);
  assert.equal(uploadIsClientOnly(), true);
  assert.equal(SHOP_THIS_LOOK.length, 3);
});

test('product title prefers mill + vendor SKU + pattern + color', () => {
  assert.equal(
    productTitle({
      display_title: 'Kravet PEF100019.34 Indienne Fennel',
      brand: 'Kravet',
      sku: 'PEF100019.34',
      pattern: 'Indienne',
      color: 'Fennel',
      empire_code: 'F-INDIENNE-FENNEL',
    }),
    'Kravet PEF100019.34 Indienne Fennel',
  );
  assert.equal(
    productTitle({
      brand: 'Kravet',
      sku: 'PEF100019.34',
      pattern: 'Indienne',
      color: 'Fennel',
      empire_code: 'F-INDIENNE-FENNEL',
    }),
    'Kravet PEF100019.34 Indienne Fennel',
  );
});
