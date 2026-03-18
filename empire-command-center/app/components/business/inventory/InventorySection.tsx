'use client';
import { useState, useEffect, useCallback } from 'react';
import { API } from '../../../lib/api';
import {
  Package, Search, Plus, AlertTriangle, Trash2, TrendingDown, TrendingUp, X, Loader2,
  DollarSign, Pencil, Check
} from 'lucide-react';

interface InventoryItem {
  id: string;
  name: string;
  sku: string;
  category: string;
  quantity: number;
  unit: string;
  min_stock: number;
  cost_per_unit: number;
  sell_price: number;
  vendor: string;
  location: string;
  business: string;
  notes: string;
}

interface DashboardStats {
  total_items: number;
  total_value: number;
  low_stock_count: number;
  by_category: Record<string, { count: number; value: number; low_stock: number }>;
}

export default function InventorySection() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [lowStockOnly, setLowStockOnly] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingItem, setEditingItem] = useState<string | null>(null);
  const [editPrices, setEditPrices] = useState<{ cost: string; sell: string }>({ cost: '', sell: '' });
  const [showPricing, setShowPricing] = useState(false);

  const fetchItems = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      if (categoryFilter) params.set('category', categoryFilter);
      if (lowStockOnly) params.set('low_stock', 'true');
      params.set('limit', '200');

      const [itemsRes, statsRes] = await Promise.all([
        fetch(`${API}/inventory/items?${params}`),
        fetch(`${API}/inventory/dashboard`),
      ]);

      if (itemsRes.ok) {
        const data = await itemsRes.json();
        setItems(data.items || (Array.isArray(data) ? data : []));
      }
      if (statsRes.ok) {
        const data = await statsRes.json();
        setStats(data);
      }
    } catch {
      // API offline
    } finally {
      setLoading(false);
    }
  }, [search, categoryFilter, lowStockOnly]);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const categories = [...new Set(items.map(i => i.category).filter(Boolean))];

  const handleDelete = async (id: string) => {
    try {
      const res = await fetch(`${API}/inventory/items/${id}`, { method: 'DELETE' });
      if (res.ok) fetchItems();
    } catch { /* */ }
  };

  const handleAddItem = async (item: Partial<InventoryItem>) => {
    try {
      const res = await fetch(`${API}/inventory/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item),
      });
      if (res.ok) {
        setShowAddForm(false);
        fetchItems();
      }
    } catch { /* */ }
  };

  const handleUpdateItem = async (id: string, updates: Partial<InventoryItem>) => {
    try {
      const res = await fetch(`${API}/inventory/items/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      if (res.ok) {
        const updated = await res.json();
        setItems(prev => prev.map(i => i.id === id ? { ...i, ...updated } : i));
      }
    } catch { /* */ }
  };

  const handleStockAdjust = (id: string, delta: number) => {
    const item = items.find(i => i.id === id);
    if (!item) return;
    const newQty = Math.max(0, item.quantity + delta);
    handleUpdateItem(id, { quantity: newQty } as any);
    setItems(prev => prev.map(i => i.id === id ? { ...i, quantity: newQty } : i));
  };

  const startPriceEdit = (item: InventoryItem) => {
    setEditingItem(item.id);
    setEditPrices({ cost: String(item.cost_per_unit || 0), sell: String(item.sell_price || 0) });
  };

  const savePriceEdit = (id: string) => {
    handleUpdateItem(id, {
      cost_per_unit: parseFloat(editPrices.cost) || 0,
      sell_price: parseFloat(editPrices.sell) || 0,
    } as any);
    setEditingItem(null);
  };

  const totalItems = stats?.total_items ?? items.length;
  const totalValue = stats?.total_value ?? 0;
  const lowStockCount = stats?.low_stock_count ?? items.filter(i => i.quantity < i.min_stock).length;
  const outOfStock = items.filter(i => i.quantity === 0).length;

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '24px 36px' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#dcfce7] flex items-center justify-center">
            <Package size={20} className="text-[#16a34a]" />
          </div>
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>Inventory</h2>
            <p style={{ fontSize: 13, color: '#aaa', margin: 0 }}>{totalItems} items &middot; Value: ${totalValue.toLocaleString()}</p>
          </div>
        </div>
        <button
          onClick={() => setShowAddForm(true)}
          className="flex items-center gap-1.5 cursor-pointer hover:brightness-110 transition-all active:scale-[0.97]"
          style={{ padding: '10px 18px', fontSize: 13, fontWeight: 700, color: '#fff', background: '#16a34a', borderRadius: 12, border: 'none', boxShadow: '0 2px 8px rgba(22,163,106,0.3)' }}
        >
          <Plus size={16} /> Add Item
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-3 gap-3 mb-5">
        <div className="empire-card">
          <div style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>Total Items</div>
          <div className="kpi-value">{totalItems}</div>
        </div>
        <div className="empire-card" style={{ borderColor: lowStockCount > 0 ? '#fde68a' : undefined }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: lowStockCount > 0 ? '#d97706' : '#777', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>
            {lowStockCount > 0 && <AlertTriangle size={11} className="inline mr-1" style={{ verticalAlign: '-1px' }} />}
            Low Stock
          </div>
          <div className="kpi-value" style={{ color: lowStockCount > 0 ? '#d97706' : '#1a1a1a' }}>{lowStockCount}</div>
        </div>
        <div className="empire-card" style={{ borderColor: outOfStock > 0 ? '#fecaca' : undefined }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: outOfStock > 0 ? '#dc2626' : '#777', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>Out of Stock</div>
          <div className="kpi-value" style={{ color: outOfStock > 0 ? '#dc2626' : '#1a1a1a' }}>{outOfStock}</div>
        </div>
      </div>

      {/* Search & Filters */}
      <div className="flex items-center gap-3 mb-5">
        <div className="flex items-center gap-2 flex-1" style={{ padding: '0 14px', borderRadius: 12, border: '1px solid #ece8e0', background: '#faf9f7' }}>
          <Search size={16} className="text-[#bbb]" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search by name or SKU..."
            className="flex-1 py-2.5 text-[13px] bg-transparent outline-none placeholder:text-[#bbb] text-[#1a1a1a]"
          />
          {search && (
            <button onClick={() => setSearch('')} className="cursor-pointer text-[#bbb] hover:text-[#777]"><X size={14} /></button>
          )}
        </div>

        <select
          value={categoryFilter}
          onChange={e => setCategoryFilter(e.target.value)}
          className="cursor-pointer outline-none"
          style={{ padding: '9px 14px', fontSize: 13, borderRadius: 12, border: '1px solid #ece8e0', background: '#faf9f7', color: '#555' }}
        >
          <option value="">All Categories</option>
          {categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>

        <button
          onClick={() => setLowStockOnly(!lowStockOnly)}
          className={`flex items-center gap-1.5 cursor-pointer transition-all ${lowStockOnly ? '' : 'hover:bg-[#fef3c7]'}`}
          style={{
            padding: '9px 14px', fontSize: 12, fontWeight: 600, borderRadius: 12,
            border: `1.5px solid ${lowStockOnly ? '#d97706' : '#ece8e0'}`,
            background: lowStockOnly ? '#fef3c7' : '#faf9f7',
            color: lowStockOnly ? '#d97706' : '#777',
            whiteSpace: 'nowrap',
          }}
        >
          <AlertTriangle size={13} /> Low stock only
        </button>

        <button
          onClick={() => setShowPricing(!showPricing)}
          className={`flex items-center gap-1.5 cursor-pointer transition-all`}
          style={{
            padding: '9px 14px', fontSize: 12, fontWeight: 600, borderRadius: 12,
            border: `1.5px solid ${showPricing ? '#b8960c' : '#ece8e0'}`,
            background: showPricing ? '#fdf8eb' : '#faf9f7',
            color: showPricing ? '#b8960c' : '#777',
            whiteSpace: 'nowrap',
          }}
        >
          <DollarSign size={13} /> Pricing
        </button>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={24} className="animate-spin text-[#b8960c]" />
        </div>
      )}

      {/* Pricing Table View */}
      {!loading && showPricing && items.length > 0 && (
        <div className="empire-card mb-5" style={{ padding: 0, overflow: 'hidden' }}>
          <div className="flex items-center gap-2 px-4 py-3 border-b border-[#ece8e0]" style={{ background: '#fdf8eb' }}>
            <DollarSign size={14} className="text-[#b8960c]" />
            <span style={{ fontSize: 13, fontWeight: 700, color: '#b8960c' }}>Price Management</span>
            <span style={{ fontSize: 11, color: '#999', marginLeft: 'auto' }}>
              Avg margin: {items.filter(i => i.sell_price > 0 && i.cost_per_unit > 0).length > 0
                ? ((items.filter(i => i.sell_price > 0).reduce((sum, i) => sum + (1 - i.cost_per_unit / i.sell_price), 0) / items.filter(i => i.sell_price > 0).length) * 100).toFixed(0) + '%'
                : '—'}
            </span>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#faf9f7' }}>
                <th style={{ padding: '8px 12px', fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', textAlign: 'left', letterSpacing: '0.05em' }}>Item</th>
                <th style={{ padding: '8px 12px', fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', textAlign: 'right', letterSpacing: '0.05em' }}>Cost</th>
                <th style={{ padding: '8px 12px', fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', textAlign: 'right', letterSpacing: '0.05em' }}>Sell</th>
                <th style={{ padding: '8px 12px', fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', textAlign: 'right', letterSpacing: '0.05em' }}>Margin</th>
                <th style={{ padding: '8px 12px', fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', textAlign: 'right', letterSpacing: '0.05em' }}>Profit/Unit</th>
                <th style={{ padding: '8px 6px', width: 40 }}></th>
              </tr>
            </thead>
            <tbody>
              {items.map(item => {
                const margin = item.sell_price > 0 ? ((1 - item.cost_per_unit / item.sell_price) * 100) : 0;
                const profit = item.sell_price - item.cost_per_unit;
                return (
                  <tr key={item.id} className="hover:bg-[#faf9f7] transition-colors" style={{ borderTop: '1px solid #f0ede8' }}>
                    <td style={{ padding: '10px 12px' }}>
                      <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{item.name}</div>
                      <div style={{ fontSize: 10, color: '#bbb', fontFamily: 'monospace' }}>{item.sku}</div>
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: 12, color: '#999' }}>${item.cost_per_unit?.toFixed(2)}</td>
                    <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>${item.sell_price?.toFixed(2)}</td>
                    <td style={{ padding: '10px 12px', textAlign: 'right' }}>
                      <span style={{ fontSize: 11, fontWeight: 700, color: margin >= 40 ? '#16a34a' : margin >= 20 ? '#d97706' : '#dc2626' }}>
                        {margin > 0 ? `${margin.toFixed(0)}%` : '—'}
                      </span>
                    </td>
                    <td style={{ padding: '10px 12px', textAlign: 'right', fontSize: 12, fontWeight: 600, color: profit > 0 ? '#16a34a' : '#dc2626' }}>
                      {profit !== 0 ? `$${profit.toFixed(2)}` : '—'}
                    </td>
                    <td style={{ padding: '10px 6px', textAlign: 'center' }}>
                      <button
                        onClick={() => startPriceEdit(item)}
                        className="cursor-pointer text-[#ccc] hover:text-[#b8960c] transition-colors"
                      >
                        <Pencil size={12} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Items Grid */}
      {!loading && items.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {items.map(item => {
            const isLow = item.min_stock > 0 && item.quantity < item.min_stock;
            const isOut = item.quantity === 0;
            return (
              <div
                key={item.id}
                className="empire-card"
                style={{
                  borderColor: isOut ? '#fecaca' : isLow ? '#fde68a' : undefined,
                  position: 'relative',
                }}
              >
                {/* SKU */}
                <div style={{ fontSize: 10, fontWeight: 600, color: '#bbb', fontFamily: 'monospace', marginBottom: 4 }}>{item.sku || '—'}</div>

                {/* Name */}
                <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 8, lineHeight: 1.3, paddingRight: 24 }}>{item.name}</div>

                {/* Tags */}
                <div className="flex items-center gap-1.5 flex-wrap mb-3">
                  {item.category && (
                    <span className="status-pill" style={{ background: '#dcfce7', color: '#16a34a', fontSize: 10 }}>{item.category}</span>
                  )}
                  {item.vendor && (
                    <span style={{ fontSize: 10, color: '#999' }}>{item.vendor}</span>
                  )}
                  {item.location && (
                    <span style={{ fontSize: 10, color: '#bbb' }}>{item.location}</span>
                  )}
                </div>

                {/* Quantity */}
                <div className="flex items-center gap-2 mb-2">
                  <span style={{ fontSize: 22, fontWeight: 700, color: isOut ? '#dc2626' : isLow ? '#d97706' : '#1a1a1a' }}>
                    {item.quantity}
                  </span>
                  <span style={{ fontSize: 11, color: '#999' }}>
                    {item.unit} (min: {item.min_stock})
                  </span>
                </div>

                {/* Stock adjustment buttons */}
                <div className="flex items-center gap-2 mb-3">
                  <button
                    onClick={(e) => { e.stopPropagation(); handleStockAdjust(item.id, -1); }}
                    className="flex items-center justify-center cursor-pointer transition-colors hover:brightness-90 active:scale-95"
                    title="Decrease stock"
                    style={{ width: 32, height: 32, borderRadius: 8, background: isOut ? '#fecaca' : '#fef3c7', border: 'none', color: isOut ? '#dc2626' : '#d97706' }}
                  >
                    <TrendingDown size={16} />
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleStockAdjust(item.id, 1); }}
                    className="flex items-center justify-center cursor-pointer transition-colors hover:brightness-90 active:scale-95"
                    title="Increase stock"
                    style={{ width: 32, height: 32, borderRadius: 8, background: '#dcfce7', border: 'none', color: '#16a34a' }}
                  >
                    <TrendingUp size={16} />
                  </button>
                </div>

                {/* Prices — clickable for editing */}
                {editingItem === item.id ? (
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1 flex-1">
                      <span style={{ fontSize: 9, color: '#999', fontWeight: 600 }}>$</span>
                      <input
                        type="number"
                        step="0.01"
                        value={editPrices.cost}
                        onChange={e => setEditPrices(p => ({ ...p, cost: e.target.value }))}
                        onClick={e => e.stopPropagation()}
                        className="w-full outline-none text-[12px] text-[#1a1a1a]"
                        style={{ padding: '4px 6px', borderRadius: 6, border: '1px solid #ece8e0', background: '#faf9f7' }}
                        placeholder="Cost"
                        autoFocus
                      />
                    </div>
                    <div className="flex items-center gap-1 flex-1">
                      <span style={{ fontSize: 9, color: '#999', fontWeight: 600 }}>$</span>
                      <input
                        type="number"
                        step="0.01"
                        value={editPrices.sell}
                        onChange={e => setEditPrices(p => ({ ...p, sell: e.target.value }))}
                        onClick={e => e.stopPropagation()}
                        className="w-full outline-none text-[12px] text-[#1a1a1a]"
                        style={{ padding: '4px 6px', borderRadius: 6, border: '1px solid #ece8e0', background: '#faf9f7' }}
                        placeholder="Sale"
                      />
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); savePriceEdit(item.id); }}
                      className="cursor-pointer hover:scale-110 transition-transform"
                      style={{ color: '#16a34a' }}
                    >
                      <Check size={14} />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); setEditingItem(null); }}
                      className="cursor-pointer hover:scale-110 transition-transform"
                      style={{ color: '#ccc' }}
                    >
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <div
                    onClick={(e) => { e.stopPropagation(); startPriceEdit(item); }}
                    className="flex items-center justify-between cursor-pointer group hover:bg-[#fdf8eb] transition-colors"
                    style={{ padding: '4px 8px', margin: '0 -8px', borderRadius: 8 }}
                    title="Click to edit prices"
                  >
                    <span style={{ fontSize: 11, color: '#999' }}>Cost: ${item.cost_per_unit?.toFixed(2) || '0.00'}</span>
                    <span style={{ fontSize: 11, color: '#777', fontWeight: 600 }}>Sale: ${item.sell_price?.toFixed(2) || '0.00'}</span>
                    <Pencil size={10} className="text-[#ddd] group-hover:text-[#b8960c] transition-colors" />
                  </div>
                )}

                {/* Margin indicator (visible in pricing mode) */}
                {showPricing && item.cost_per_unit > 0 && item.sell_price > 0 && (
                  <div style={{ marginTop: 6, padding: '4px 8px', borderRadius: 6, background: '#f0fdf4', fontSize: 10, fontWeight: 600, color: '#16a34a', textAlign: 'center' }}>
                    Margin: {((1 - item.cost_per_unit / item.sell_price) * 100).toFixed(0)}% &middot; Profit: ${(item.sell_price - item.cost_per_unit).toFixed(2)}/unit
                  </div>
                )}

                {/* Delete */}
                <button
                  onClick={() => handleDelete(item.id)}
                  className="flex items-center justify-center cursor-pointer hover:bg-[#fef2f2] transition-colors"
                  title="Delete item"
                  style={{ position: 'absolute', top: 12, right: 12, width: 24, height: 24, borderRadius: 6, border: 'none', background: 'transparent', color: '#ccc' }}
                >
                  <Trash2 size={13} />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Empty state */}
      {!loading && items.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16">
          <Package size={48} className="text-[#d8d3cb] mb-3" />
          <div style={{ fontSize: 16, fontWeight: 600, color: '#999', marginBottom: 4 }}>
            {search || categoryFilter || lowStockOnly ? 'No items match your filters' : 'No inventory items yet'}
          </div>
          <div style={{ fontSize: 13, color: '#bbb', marginBottom: 16 }}>
            Add fabrics, hardware, and materials to track stock levels
          </div>
          {!search && !categoryFilter && (
            <button
              onClick={() => setShowAddForm(true)}
              className="flex items-center gap-1.5 cursor-pointer hover:brightness-110 transition-all"
              style={{ padding: '10px 20px', fontSize: 13, fontWeight: 700, color: '#fff', background: '#16a34a', borderRadius: 12, border: 'none' }}
            >
              <Plus size={16} /> Add First Item
            </button>
          )}
        </div>
      )}

      {/* Add Item Modal */}
      {showAddForm && (
        <AddItemModal onClose={() => setShowAddForm(false)} onSave={handleAddItem} />
      )}
    </div>
  );
}

/* ── Add Item Modal ── */

function AddItemModal({ onClose, onSave }: { onClose: () => void; onSave: (item: any) => void }) {
  const [form, setForm] = useState({
    name: '', sku: '', category: 'Fabrics', quantity: 0, unit: 'yards',
    min_stock: 10, cost_per_unit: 0, sell_price: 0, vendor: '', location: '', notes: '',
  });
  const [saving, setSaving] = useState(false);

  const set = (key: string, value: any) => setForm(f => ({ ...f, [key]: value }));

  const handleSubmit = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    await onSave(form);
    setSaving(false);
  };

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center" onClick={onClose}>
      <div className="absolute inset-0 bg-black/30 backdrop-blur-[2px]" />
      <div onClick={e => e.stopPropagation()} className="relative w-[520px] bg-white rounded-2xl shadow-[0_20px_60px_rgba(0,0,0,0.2)] border border-[#e5e0d8] overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#ece8e1]">
          <h3 style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Add Inventory Item</h3>
          <button onClick={onClose} className="cursor-pointer text-[#999] hover:text-[#555]"><X size={18} /></button>
        </div>
        <div className="px-6 py-5 max-h-[70vh] overflow-y-auto">
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Name *" span={2}>
              <input value={form.name} onChange={e => set('name', e.target.value)} placeholder="Seda Dupioni - Ivory" className="form-input" />
            </FormField>
            <FormField label="SKU">
              <input value={form.sku} onChange={e => set('sku', e.target.value)} placeholder="FAB-SILK-001" className="form-input" />
            </FormField>
            <FormField label="Category">
              <select value={form.category} onChange={e => set('category', e.target.value)} className="form-input">
                <option>Fabrics</option>
                <option>Hardware</option>
                <option>Motors</option>
                <option>Lining</option>
                <option>Trim</option>
                <option>Supplies</option>
                <option>Wood</option>
                <option>Other</option>
              </select>
            </FormField>
            <FormField label="Quantity">
              <input type="number" value={form.quantity} onChange={e => set('quantity', +e.target.value)} className="form-input" />
            </FormField>
            <FormField label="Unit">
              <select value={form.unit} onChange={e => set('unit', e.target.value)} className="form-input">
                <option value="yards">Yards</option>
                <option value="meters">Meters</option>
                <option value="pieces">Pieces</option>
                <option value="rolls">Rolls</option>
                <option value="feet">Feet</option>
                <option value="each">Each</option>
              </select>
            </FormField>
            <FormField label="Min Stock">
              <input type="number" value={form.min_stock} onChange={e => set('min_stock', +e.target.value)} className="form-input" />
            </FormField>
            <FormField label="Cost / Unit ($)">
              <input type="number" step="0.01" value={form.cost_per_unit} onChange={e => set('cost_per_unit', +e.target.value)} className="form-input" />
            </FormField>
            <FormField label="Sell Price ($)">
              <input type="number" step="0.01" value={form.sell_price} onChange={e => set('sell_price', +e.target.value)} className="form-input" />
            </FormField>
            <FormField label="Vendor">
              <input value={form.vendor} onChange={e => set('vendor', e.target.value)} placeholder="Rowley" className="form-input" />
            </FormField>
            <FormField label="Location">
              <input value={form.location} onChange={e => set('location', e.target.value)} placeholder="A1" className="form-input" />
            </FormField>
            <FormField label="Notes" span={2}>
              <textarea value={form.notes} onChange={e => set('notes', e.target.value)} rows={2} placeholder="Optional notes..." className="form-input" style={{ resize: 'none' }} />
            </FormField>
          </div>
        </div>
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#ece8e1]">
          <button onClick={onClose} className="cursor-pointer hover:bg-[#f0ede8] transition-colors" style={{ padding: '8px 16px', fontSize: 13, fontWeight: 600, borderRadius: 10, border: '1px solid #ece8e0', background: '#faf9f7', color: '#777' }}>
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!form.name.trim() || saving}
            className="cursor-pointer hover:brightness-110 transition-all disabled:opacity-50"
            style={{ padding: '8px 20px', fontSize: 13, fontWeight: 700, borderRadius: 10, border: 'none', background: '#16a34a', color: '#fff' }}
          >
            {saving ? <Loader2 size={14} className="animate-spin" /> : 'Add Item'}
          </button>
        </div>
      </div>
    </div>
  );
}

function FormField({ label, children, span }: { label: string; children: React.ReactNode; span?: number }) {
  return (
    <div style={{ gridColumn: span === 2 ? 'span 2' : undefined }}>
      <label style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 5 }}>
        {label}
      </label>
      {children}
    </div>
  );
}
