import { parseFractionInches } from './measurements';

export interface EstimateAddon {
  id?: string;
  description: string;
  quantity?: number | string;
  unit?: string;
  rate?: number;
  amount?: number;
  optional?: boolean;
  selected?: boolean;
}

export interface EstimateTotals {
  itemsSubtotal: number;
  addonTotal: number;
  subtotal: number;
  taxAmount: number;
  total: number;
  depositPercent: number;
  depositAmount: number;
}

function money(n: number): number {
  return Math.round((n + Number.EPSILON) * 100) / 100;
}

export function computeEstimateTotals(input: {
  lineItems?: Array<{ quantity?: number | string; qty?: number; rate?: number; unit_price?: number; amount?: number }>;
  addons?: EstimateAddon[];
  taxRate?: number;
  discountAmount?: number;
  discountType?: string;
  depositPercent?: number;
}): EstimateTotals {
  const itemsSubtotal = money(
    (input.lineItems || []).reduce((sum, item) => {
      if (item.amount != null) return sum + Number(item.amount || 0);
      const qty = parseFractionInches(item.quantity ?? item.qty ?? 1) || 1;
      const rate = Number(item.rate ?? item.unit_price ?? 0);
      return sum + qty * rate;
    }, 0)
  );

  const addonTotal = money(
    (input.addons || []).reduce((sum, addon) => {
      if (!addon.selected) return sum;
      const qty = parseFractionInches(addon.quantity ?? 1) || 1;
      const rate = Number(addon.rate ?? addon.amount ?? 0);
      return sum + qty * rate;
    }, 0)
  );

  const subtotal = money(itemsSubtotal + addonTotal);
  let discount = Number(input.discountAmount || 0);
  if ((input.discountType || 'dollar') === 'percent' && discount > 0) {
    discount = money(subtotal * (discount / 100));
  }
  let taxRate = Number(input.taxRate || 0);
  if (taxRate > 1) taxRate = taxRate / 100;
  const taxAmount = money(subtotal * taxRate);
  const total = money(Math.max(0, subtotal + taxAmount - discount));
  const depositPercent = Number(input.depositPercent ?? 50);
  const depositAmount = money(total * (depositPercent / 100));

  return { itemsSubtotal, addonTotal, subtotal, taxAmount, total, depositPercent, depositAmount };
}
