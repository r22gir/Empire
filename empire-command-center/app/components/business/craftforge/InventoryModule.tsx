'use client';
import React, { useState, useEffect, useCallback } from 'react';
import { API } from '../../../lib/api';
import {
  Package, Plus, X, Loader2, Trash2, Edit3
} from 'lucide-react';
import DataTable, { Column } from '../shared/DataTable';
import SearchBar from '../shared/SearchBar';
import EmptyState from '../shared/EmptyState';

const TYPES = ['all', 'wood', 'hardware', 'finishing', 'consumable', 'filament', 'tool'] as const;

export default function InventoryModule() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);

  // Form
  const [name, setName] = useState('');
  const [type, setType] = useState('wood');
  const [sku, setSku] = useState('');
  const [quantity, setQuantity] = useState<number>(0);
  const [unit, setUnit] = useState('ea');
  const [costPerUnit, setCostPerUnit] = useState<number>(0);
  const [reorderPoint, setReorderPoint] = useState<number>(0);
  const [supplier, setSupplier] = useState('');
  const [location, setLocation] = useState('');
  const [itemNotes, setItemNotes] = useState('');

  const fetchItems = useCallback(() => {
    setLoading(true);
    const url = typeFilter !== 'all'
      ? `${API}/craftforge/inventory?type=${typeFilter}`
      : `${API}/craftforge/inventory`;
    fetch(url)
      .then(r => r.json())
      .then(data => {
        setItems(Array.isArray(data) ? data : data.items || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [typeFilter]);

  useEffect(() => { fetchItems(); }, [fetchItems]);

  const resetForm = () => {
    setName(''); setType('wood'); setSku(''); setQuantity(0); setUnit('ea');
    setCostPerUnit(0); setReorderPoint(0); setSupplier(''); setLocation(''); setItemNotes('');
    setEditItem(null);
  };

  const openEdit = (item: any) => {
    setEditItem(item);
    setName(item.name || '');
    setType(item.type || 'wood');
    setSku(item.sku || '');
    setQuantity(item.quantity || 0);
    setUnit(item.unit || 'ea');
    setCostPerUnit(item.cost_per_unit || 0);
    setReorderPoint(item.reorder_point || 0);
    setSupplier(item.supplier || '');
    setLocation(item.location || '');
    setItemNotes(item.notes || '');
    setShowForm(true);
  };

  const handleSubmit = async () => {
    if (!name.trim()) return;
    setSubmitting(true);
    try {
      const body = {
        name, type, sku: sku || undefined, quantity, unit, cost_per_unit: costPerUnit,
        reorder_point: reorderPoint, supplier: supplier || undefined,
        location: location || undefined, notes: itemNotes || undefined,
      };
      if (editItem) {
        await fetch(`${API}/craftforge/inventory/${editItem.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
      } else {
        await fetch(`${API}/craftforge/inventory`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
      }
      resetForm();
      setShowForm(false);
      fetchItems();
    } catch (e) {
      console.error('Inventory save failed:', e);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this inventory item?')) return;
    try {
      await fetch(`${API}/craftforge/inventory/${id}`, { method: 'DELETE' });
      fetchItems();
    } catch (e) {
      console.error('Delete failed:', e);
    }
  };

  const filtered = items.filter(item => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (item.name || '').toLowerCase().includes(q) ||
           (item.sku || '').toLowerCase().includes(q) ||
           (item.supplier || '').toLowerCase().includes(q);
  });

  const lowStockCount = items.filter(i => i.quantity != null && i.reorder_point != null && i.quantity <= i.reorder_point).length;

  const columns: Column[] = [
    { key: 'name', label: 'Name', sortable: true, render: (row) => <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{row.name}</span> },
    { key: 'type', label: 'Type', sortable: true, render: (row) => <span className="capitalize" style={{ fontSize: 12 }}>{row.type || '--'}</span> },
    { key: 'sku', label: 'SKU', render: (row) => <span style={{ fontSize: 11, color: '#777', fontFamily: 'monospace' }}>{row.sku || '--'}</span> },
    {
      key: 'quantity', label: 'Qty', sortable: true,
      render: (row) => {
        const isLow = row.quantity != null && row.reorder_point != null && row.quantity <= row.reorder_point;
        return (
          <span style={{ fontSize: 13, fontWeight: 700, color: isLow ? '#dc2626' : '#1a1a1a', background: isLow ? '#fef2f2' : 'transparent', padding: isLow ? '2px 8px' : 0, borderRadius: 6 }}>
            {row.quantity ?? '--'}
          </span>
        );
      },
    },
    { key: 'unit', label: 'Unit', render: (row) => <span style={{ fontSize: 12, color: '#777' }}>{row.unit || '--'}</span> },
    { key: 'cost_per_unit', label: '$/Unit', sortable: true, render: (row) => <span style={{ fontSize: 12, fontWeight: 600, color: '#b8960c' }}>{row.cost_per_unit != null ? `$${Number(row.cost_per_unit).toFixed(2)}` : '--'}</span> },
    { key: 'reorder_point', label: 'Reorder Pt', render: (row) => <span style={{ fontSize: 12, color: '#999' }}>{row.reorder_point ?? '--'}</span> },
    { key: 'supplier', label: 'Supplier', render: (row) => <span style={{ fontSize: 12, color: '#555' }}>{row.supplier || '--'}</span> },
    { key: 'location', label: 'Location', render: (row) => <span style={{ fontSize: 12, color: '#555' }}>{row.location || '--'}</span> },
    {
      key: 'actions', label: '',
      render: (row) => (
        <div className="flex items-center gap-1">
          <button onClick={(e) => { e.stopPropagation(); openEdit(row); }} className="p-1.5 rounded-lg hover:bg-[#f5f3ef] cursor-pointer" style={{ background: 'none', border: 'none' }}>
            <Edit3 size={13} className="text-[#777]" />
          </button>
          <button onClick={(e) => { e.stopPropagation(); handleDelete(row.id); }} className="p-1.5 rounded-lg hover:bg-[#fef2f2] cursor-pointer" style={{ background: 'none', border: 'none' }}>
            <Trash2 size={13} className="text-[#dc2626]" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 1060, margin: '0 auto', padding: '24px 36px' }}>
      <div className="flex items-center justify-between mb-4">
        <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }} className="flex items-center gap-2">
          <Package size={20} className="text-[#b8960c]" /> Inventory
          {lowStockCount > 0 && (
            <span style={{ fontSize: 11, fontWeight: 700, color: '#dc2626', background: '#fef2f2', padding: '2px 8px', borderRadius: 8 }}>
              {lowStockCount} low stock
            </span>
          )}
        </h2>
        <div className="flex items-center gap-3">
          <div className="w-56">
            <SearchBar value={search} onChange={setSearch} placeholder="Search inventory..." />
          </div>
          <button
            onClick={() => { resetForm(); setShowForm(true); }}
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '10px 16px', fontSize: 12, fontWeight: 700, color: '#fff', background: '#b8960c', borderRadius: 10, border: 'none', cursor: 'pointer', minHeight: 44 }}
            className="hover:bg-[#a68500] transition-colors"
          >
            <Plus size={14} /> Add Item
          </button>
        </div>
      </div>

      {/* Type filter tabs */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {TYPES.map(t => (
          <button
            key={t}
            onClick={() => setTypeFilter(t)}
            className={`filter-tab capitalize ${typeFilter === t ? 'active' : ''}`}
          >
            {t === 'all' ? 'All Types' : t}
          </button>
        ))}
      </div>

      {/* Add/Edit Modal */}
      {showForm && (
        <div className="empire-card flat mb-4" style={{ border: '1.5px solid #b8960c' }}>
          <div className="flex items-center justify-between mb-3">
            <div className="section-label">{editItem ? 'Edit Item' : 'Add Inventory Item'}</div>
            <button onClick={() => { resetForm(); setShowForm(false); }} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
              <X size={16} className="text-[#999]" />
            </button>
          </div>
          <div className="grid grid-cols-4 gap-3 mb-3">
            <div className="col-span-2">
              <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Name *</label>
              <input className="form-input" value={name} onChange={e => setName(e.target.value)} placeholder="Item name" />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Type</label>
              <select className="form-input" value={type} onChange={e => setType(e.target.value)}>
                {TYPES.filter(t => t !== 'all').map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">SKU</label>
              <input className="form-input" value={sku} onChange={e => setSku(e.target.value)} placeholder="Optional" />
            </div>
          </div>
          <div className="grid grid-cols-5 gap-3 mb-3">
            <div>
              <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Quantity</label>
              <input className="form-input" type="number" min={0} step={1} value={quantity || ''} onChange={e => setQuantity(Number(e.target.value))} />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Unit</label>
              <input className="form-input" value={unit} onChange={e => setUnit(e.target.value)} placeholder="ea" />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">$/Unit</label>
              <input className="form-input" type="number" min={0} step={0.01} value={costPerUnit || ''} onChange={e => setCostPerUnit(Number(e.target.value))} />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Reorder Pt</label>
              <input className="form-input" type="number" min={0} step={1} value={reorderPoint || ''} onChange={e => setReorderPoint(Number(e.target.value))} />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Location</label>
              <input className="form-input" value={location} onChange={e => setLocation(e.target.value)} placeholder="Shelf A" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Supplier</label>
              <input className="form-input" value={supplier} onChange={e => setSupplier(e.target.value)} placeholder="Supplier name" />
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Notes</label>
              <input className="form-input" value={itemNotes} onChange={e => setItemNotes(e.target.value)} placeholder="Optional notes" />
            </div>
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={() => { resetForm(); setShowForm(false); }} style={{ padding: '8px 16px', fontSize: 12, fontWeight: 600, color: '#777', background: '#fff', borderRadius: 10, border: '1px solid #ece8e0', cursor: 'pointer', minHeight: 44 }}>Cancel</button>
            <button onClick={handleSubmit} disabled={submitting || !name.trim()}
              style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', fontSize: 12, fontWeight: 700, color: '#fff', background: !name.trim() ? '#d5d0c8' : '#b8960c', borderRadius: 10, border: 'none', cursor: !name.trim() ? 'not-allowed' : 'pointer', minHeight: 44 }}>
              {submitting ? <Loader2 size={14} className="animate-spin" /> : null}
              {editItem ? 'Update' : 'Add Item'}
            </button>
          </div>
        </div>
      )}

      <DataTable columns={columns} data={filtered} loading={loading} emptyMessage="No inventory items found. Add materials and supplies to track stock." />
    </div>
  );
}
