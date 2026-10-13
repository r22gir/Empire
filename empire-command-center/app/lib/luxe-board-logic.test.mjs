import test from 'node:test';
import assert from 'node:assert/strict';
import {
  HOUSE_CATALOG, DEMO_BOARD, catalogIndex, composeEstimate, toggleSelection, setSelectionQty, money,
} from './luxe-board-logic.ts';

test('compose estimate from the house catalog is preview-only', () => {
  const index = catalogIndex(HOUSE_CATALOG);
  const est = composeEstimate(DEMO_BOARD, index);
  assert.equal(est.wrote_quote, false);
  assert.equal(est.wrote_live, false);
  assert.equal(est.sent, false);
  assert.ok(est.materials > 0);
  assert.ok(est.labor > 0);
  assert.ok(est.subtotal >= est.materials);
  assert.equal(est.photos.length, 2);
  assert.equal(money(1640), '$1640');
});

test('toggle and qty stay on the board without implying a live write', () => {
  const silk = HOUSE_CATALOG.fabrics.find((f) => f.id === 'fab-silk-taffeta');
  let board = { ...DEMO_BOARD, selections: [] };
  board = toggleSelection(board, silk);
  assert.equal(board.selections.length, 1);
  board = setSelectionQty(board, silk.id, 9);
  assert.equal(board.selections[0].qty, 9);
  board = toggleSelection(board, silk);
  assert.equal(board.selections.length, 0);
});
