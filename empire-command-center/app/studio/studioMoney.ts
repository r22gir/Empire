/** Studio Money card labels. Currency only — no live contacts. */

export const NOT_CONNECTED = 'Not connected';
export const MONEY_LOADING = 'Loading…';

const usd = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

export function formatStudioAmount(n: number): string {
  return usd.format(n);
}

export type StudioMoneyPayload = {
  to_collect?: number | null;
  deposits_due?: number | null;
  paid_mtd?: number | null;
  connected?: {
    to_collect?: boolean;
    deposits_due?: boolean;
    paid_mtd?: boolean;
  };
};

export type MoneyFigures = {
  toCollect: string;
  depositsDue: string;
  paidMtd: string;
};

export function moneyFigureLabel(opts: {
  example: boolean;
  exampleText: string;
  loading: boolean;
  connected: boolean;
  amount: number | null | undefined;
}): string {
  if (opts.example) return opts.exampleText;
  if (opts.loading) return MONEY_LOADING;
  if (!opts.connected || opts.amount == null || !Number.isFinite(opts.amount)) return NOT_CONNECTED;
  return formatStudioAmount(opts.amount);
}

export function figuresFromPayload(
  payload: StudioMoneyPayload | null,
  opts: { example: boolean; loading: boolean; exampleMoney: MoneyFigures },
): MoneyFigures {
  if (opts.example) return opts.exampleMoney;
  const connected = payload?.connected || {};
  return {
    toCollect: moneyFigureLabel({
      example: false,
      exampleText: opts.exampleMoney.toCollect,
      loading: opts.loading,
      connected: connected.to_collect === true,
      amount: payload?.to_collect,
    }),
    depositsDue: moneyFigureLabel({
      example: false,
      exampleText: opts.exampleMoney.depositsDue,
      loading: opts.loading,
      connected: connected.deposits_due === true,
      amount: payload?.deposits_due,
    }),
    paidMtd: moneyFigureLabel({
      example: false,
      exampleText: opts.exampleMoney.paidMtd,
      loading: opts.loading,
      connected: connected.paid_mtd === true,
      amount: payload?.paid_mtd,
    }),
  };
}
