/**
 * Money figures from mocked finance payloads. No live contacts or amounts.
 * Run: node --experimental-strip-types --test app/studio/studioMoney.test.ts
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { EXAMPLE_MONEY } from './exampleData.ts';
import {
  NOT_CONNECTED,
  MONEY_LOADING,
  figuresFromPayload,
  formatStudioAmount,
  moneyFigureLabel,
} from './studioMoney.ts';

const EXAMPLE_FIG = {
  toCollect: EXAMPLE_MONEY.toCollect,
  depositsDue: EXAMPLE_MONEY.depositsDue,
  paidMtd: EXAMPLE_MONEY.paidMtd,
};

test('currency formatting uses dollars and cents', () => {
  assert.equal(formatStudioAmount(0), '$0.00');
  assert.equal(formatStudioAmount(250.25), '$250.25');
  assert.equal(formatStudioAmount(1200), '$1,200.00');
});

test('live mocked payload maps deposits due and paid MTD', () => {
  const figures = figuresFromPayload(
    {
      to_collect: 120.5,
      deposits_due: 650,
      paid_mtd: 250.25,
      connected: { to_collect: true, deposits_due: true, paid_mtd: true },
    },
    { example: false, loading: false, exampleMoney: EXAMPLE_FIG },
  );
  assert.equal(figures.toCollect, '$120.50');
  assert.equal(figures.depositsDue, '$650.00');
  assert.equal(figures.paidMtd, '$250.25');
  assert.doesNotMatch(JSON.stringify(figures), /EXAMPLE|Client [A-F]|—/);
});

test('loading and disconnected never show EXAMPLE dashes', () => {
  const loading = figuresFromPayload(null, { example: false, loading: true, exampleMoney: EXAMPLE_FIG });
  assert.equal(loading.depositsDue, MONEY_LOADING);
  assert.equal(loading.paidMtd, MONEY_LOADING);
  assert.doesNotMatch(JSON.stringify(loading), /EXAMPLE|Client [A-F]/);

  const down = figuresFromPayload(null, { example: false, loading: false, exampleMoney: EXAMPLE_FIG });
  assert.equal(down.depositsDue, NOT_CONNECTED);
  assert.equal(down.paidMtd, NOT_CONNECTED);
  assert.equal(down.toCollect, NOT_CONNECTED);

  assert.equal(moneyFigureLabel({
    example: false, exampleText: '$—', loading: false, connected: false, amount: 99,
  }), NOT_CONNECTED);
});

test('example=1 keeps placeholder copy and does not use live amounts', () => {
  const figures = figuresFromPayload(
    { to_collect: 999, deposits_due: 999, paid_mtd: 999, connected: { to_collect: true, deposits_due: true, paid_mtd: true } },
    { example: true, loading: false, exampleMoney: EXAMPLE_FIG },
  );
  assert.equal(figures.toCollect, EXAMPLE_MONEY.toCollect);
  assert.equal(figures.depositsDue, EXAMPLE_MONEY.depositsDue);
  assert.equal(figures.paidMtd, EXAMPLE_MONEY.paidMtd);
});
