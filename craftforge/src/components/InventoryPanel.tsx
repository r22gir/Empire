'use client';
import { useState } from 'react';
import { Package, AlertTriangle, Plus } from 'lucide-react';
import { API } from '../lib/api';

const typeColors: Record<string, string> = {
  wood: 'bg-[#fdf8eb] text-[#c9a84c]',
  hardware: 'bg-[#f5f3ef] text-[#777]',
  finishing: 'bg-[#ede9fe] text-[#7c3aed]',
  consumable: 'bg-[#dbeafe] text-[#2563eb]',
  filament: 'bg-[#fce7f3] text-[#db2777]',
  tool: 'bg-[#dcfce7] text-[#16a34a]',
};

export default function InventoryPanel({
  inventory,
  onRefresh,
  full,
}: {
  inventory: any[];
  onRefresh: () => void;
  full?: boolean;
}) {
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ name: '', type: 'wood', quantity: '', cost_per_unit: '', reorder_point: '', unit: 'ea', supplier: '' });

  const handleAdd = async () => {
    if (!form.name) return;
    await fetch(`${API}/inventory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...form,
        quantity: parseFloat(form.quantity) || 0,
        cost_per_unit: parseFloat(form.cost_per_unit) || 0,
        reorder_point: parseFloat(form.reorder_point) || 0,
      }),
    });
    setForm({ name: '', type: 'wood', quantity: '', cost_per_unit: '', reorder_point: '', unit: 'ea', supplier: '' });
    setAdding(false);
    onRefresh();
  };

  const shown = full ? inventory : inventory.slice(0, 8);
  const totalValue = inventory.reduce((s, i) => s + (i.total_value || 0), 0);
  const lowStock = inventory.filter(i => i.low_stock);

  return (
    <div className="bg-white border border-[#e5e0d8] rounded-xl p-5">
      <h3 className="text-sm font-bold text-[#1a1a1a] mb-3 flex items-center gap-2">
        <Package size={15} className="text-[#7c3aed]" />
        {full ? 'Full Inventory' : 'Inventory'}
        <span className="text-[10px] text-[#aaa] font-normal ml-auto">
          {inventory.length} items · ${totalValue.toLocaleString()}
        </span>
        <button onClick={() => setAdding(!adding)} className="ml-2 w-5 h-5 rounded bg-[#ede9fe] text-[#7c3aed] flex items-center justify-center hover:bg-[#7c3aed] hover:text-white transition-colors">
          <Plus size={12} />
        </button>
      </h3>

      {adding && (
        <div className="mb-3 p-3 rounded-lg bg-[#faf9f7] border border-[#e5e0d8] space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <input placeholder="Item name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="text-xs px-2 py-1.5 border border-[#e5e0d8] rounded" />
            <select value={form.type} onChange={e => setForm({ ...form, type: e.target.value })} className="text-xs px-2 py-1.5 border border-[#e5e0d8] rounded">
              {Object.keys(typeColors).map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <input placeholder="Qty" type="number" value={form.quantity} onChange={e => setForm({ ...form, quantity: e.target.value })} className="text-xs px-2 py-1.5 border border-[#e5e0d8] rounded" />
            <input placeholder="Cost/unit" type="number" step="0.01" value={form.cost_per_unit} onChange={e => setForm({ ...form, cost_per_unit: e.target.value })} className="text-xs px-2 py-1.5 border border-[#e5e0d8] rounded" />
            <input placeholder="Reorder at" type="number" value={form.reorder_point} onChange={e => setForm({ ...form, reorder_point: e.target.value })} className="text-xs px-2 py-1.5 border border-[#e5e0d8] rounded" />
            <input placeholder="Supplier" value={form.supplier} onChange={e => setForm({ ...form, supplier: e.target.value })} className="text-xs px-2 py-1.5 border border-[#e5e0d8] rounded" />
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setAdding(false)} className="text-[10px] px-3 py-1 text-[#777] hover:text-[#1a1a1a]">Cancel</button>
            <button onClick={handleAdd} className="text-[10px] px-3 py-1 bg-[#7c3aed] text-white rounded font-semibold hover:bg-[#6d28d9]">Add Item</button>
          </div>
        </div>
      )}

      {lowStock.length > 0 && (
        <div className="mb-3 p-2 rounded-lg bg-[#fef3c7] border border-[#fbbf24]/30">
          <div className="flex items-center gap-1 text-[10px] font-bold text-[#d97706]">
            <AlertTriangle size={12} /> LOW STOCK: {lowStock.map(i => i.name).join(', ')}
          </div>
        </div>
      )}

      <div className="space-y-1.5">
        {shown.map(item => (
          <div key={item.id} className="flex items-center justify-between p-2.5 rounded-lg border border-[#ece8e1] hover:border-[#c9a84c] transition-all">
            <div className="flex items-center gap-2">
              <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded ${typeColors[item.type] || typeColors.wood}`}>
                {item.type.toUpperCase()}
              </span>
              <div>
                <div className="text-[11px] font-medium text-[#1a1a1a]">{item.name}</div>
                {item.supplier && <div className="text-[9px] text-[#aaa]">{item.supplier}</div>}
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs font-bold text-[#1a1a1a]">{item.quantity} {item.unit}</div>
              <div className="text-[9px] text-[#aaa]">${(item.total_value || 0).toFixed(2)}</div>
            </div>
          </div>
        ))}
        {inventory.length === 0 && (
          <div className="text-xs text-[#aaa] text-center py-6">No inventory items. Add materials and tools to track stock.</div>
        )}
      </div>
    </div>
  );
}
