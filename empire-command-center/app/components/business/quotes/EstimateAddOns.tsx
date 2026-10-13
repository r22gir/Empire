'use client';

import { Plus, Trash2 } from 'lucide-react';
import { computeEstimateTotals, type EstimateAddon } from '../../../lib/estimate-totals';

interface EstimateAddOnsProps {
  lineItems?: any[];
  addons: EstimateAddon[];
  onChange: (addons: EstimateAddon[]) => void;
  taxRate?: number;
  depositPercent?: number;
}

function money(n: number) {
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function EstimateAddOns({
  lineItems = [],
  addons,
  onChange,
  taxRate = 0,
  depositPercent = 50,
}: EstimateAddOnsProps) {
  const totals = computeEstimateTotals({
    lineItems,
    addons,
    taxRate,
    depositPercent,
  });

  const update = (index: number, patch: Partial<EstimateAddon>) => {
    onChange(addons.map((addon, i) => (i === index ? { ...addon, ...patch } : addon)));
  };

  const addRow = () => {
    onChange([
      ...addons,
      { id: `addon-${Date.now()}`, description: '', quantity: 1, unit: 'ea', rate: 0, optional: true, selected: false },
    ]);
  };

  return (
    <div style={{ borderRadius: 12, border: '1px solid #ece8e0', background: '#fff', overflow: 'hidden' }}>
      <div style={{ padding: '12px 14px', borderBottom: '1px solid #ece8e0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#1a1a1a' }}>Optional add-ons</div>
          <div style={{ fontSize: 11, color: '#888' }}>Selected add-ons update total and deposit live</div>
        </div>
        <button type="button" onClick={addRow} style={{ fontSize: 11, fontWeight: 700, color: '#b8960c', background: '#fdf8eb', border: '1px solid #ead889', borderRadius: 8, padding: '6px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
          <Plus size={12} /> Add line
        </button>
      </div>

      {addons.length === 0 ? (
        <div style={{ padding: 16, fontSize: 12, color: '#999' }}>No optional add-ons on this estimate.</div>
      ) : (
        <div>
          {addons.map((addon, index) => (
            <div key={addon.id || index} style={{ display: 'grid', gridTemplateColumns: '28px 1fr 70px 90px 28px', gap: 8, alignItems: 'center', padding: '8px 12px', borderBottom: '1px solid #f3efe8' }}>
              <input
                type="checkbox"
                checked={!!addon.selected}
                onChange={(e) => update(index, { selected: e.target.checked })}
                aria-label={`Include ${addon.description || 'add-on'}`}
              />
              <input
                value={addon.description}
                onChange={(e) => update(index, { description: e.target.value })}
                placeholder="Hardware, rush, install window…"
                style={{ width: '100%', border: '1px solid #ece8e0', borderRadius: 8, padding: '7px 8px', fontSize: 12 }}
              />
              <input
                value={addon.quantity ?? 1}
                onChange={(e) => update(index, { quantity: e.target.value })}
                placeholder="Qty"
                style={{ width: '100%', border: '1px solid #ece8e0', borderRadius: 8, padding: '7px 8px', fontSize: 12 }}
              />
              <input
                type="number"
                min={0}
                step="0.01"
                value={addon.rate ?? 0}
                onChange={(e) => update(index, { rate: Number(e.target.value) })}
                style={{ width: '100%', border: '1px solid #ece8e0', borderRadius: 8, padding: '7px 8px', fontSize: 12 }}
              />
              <button type="button" onClick={() => onChange(addons.filter((_, i) => i !== index))} style={{ border: 'none', background: 'transparent', color: '#dc2626', cursor: 'pointer' }} aria-label="Remove add-on">
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      )}

      <div style={{ padding: '12px 14px', background: '#fdf8eb' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#555', marginBottom: 4 }}>
          <span>Items</span><span>${money(totals.itemsSubtotal)}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#555', marginBottom: 4 }}>
          <span>Selected add-ons</span><span>${money(totals.addonTotal)}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, fontWeight: 800, color: '#1a1a1a', marginTop: 6 }}>
          <span>Total</span><span>${money(totals.total)}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, fontWeight: 700, color: '#16a34a', marginTop: 4 }}>
          <span>Deposit ({totals.depositPercent}%)</span><span>${money(totals.depositAmount)}</span>
        </div>
      </div>
    </div>
  );
}
