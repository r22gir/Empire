'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { FileText, Plus, X, AlertCircle } from 'lucide-react';
import { API } from '../../../lib/api';
import DataTable, { Column } from '../shared/DataTable';
import SearchBar from '../shared/SearchBar';
import StatusBadge from '../shared/StatusBadge';
import EmptyState from '../shared/EmptyState';

interface Invoice {
  id: string;
  invoice_number: string;
  customer_name: string;
  amount: number;
  balance: number;
  due_date: string;
  status: string;
}

interface LineItem {
  description: string;
  qty: number;
  rate: number;
  amount: number;
}

const STATUS_OPTIONS = ['all', 'draft', 'sent', 'paid', 'overdue'];

function fmt(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);
}

function InvoiceForm({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [customerName, setCustomerName] = useState('');
  const [items, setItems] = useState<LineItem[]>([{ description: '', qty: 1, rate: 0, amount: 0 }]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateItem = (idx: number, field: keyof LineItem, value: string | number) => {
    setItems(prev => {
      const next = [...prev];
      const item = { ...next[idx], [field]: value };
      if (field === 'qty' || field === 'rate') {
        item.amount = Number(item.qty) * Number(item.rate);
      }
      next[idx] = item;
      return next;
    });
  };

  const addItem = () => setItems(prev => [...prev, { description: '', qty: 1, rate: 0, amount: 0 }]);
  const removeItem = (idx: number) => setItems(prev => prev.length > 1 ? prev.filter((_, i) => i !== idx) : prev);

  const subtotal = items.reduce((s, i) => s + i.amount, 0);
  const tax = subtotal * 0.06;
  const total = subtotal + tax;

  const handleSave = async () => {
    if (!customerName.trim()) { setError('Customer name is required'); return; }
    if (items.every(i => !i.description.trim())) { setError('Add at least one line item'); return; }
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`${API}/finance/invoices`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_name: customerName,
          line_items: items.filter(i => i.description.trim()),
          subtotal, tax_rate: 0.06, tax_amount: tax, total,
        }),
      });
      if (!res.ok) {
        if (res.status === 404) throw new Error('Invoice endpoint not available. Connect backend to enable.');
        throw new Error(`Failed to create invoice (${res.status})`);
      }
      onSaved();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const inputClass = "w-full px-3.5 py-2.5 text-sm border border-[#ece8e0] rounded-[14px] bg-[#faf9f7] outline-none focus:border-[#b8960c] transition-colors";

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="empire-card" style={{ padding: 0, width: '100%', maxWidth: 672, maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 20px 60px rgba(0,0,0,0.12)' }}>
        <div className="flex items-center justify-between" style={{ padding: '16px 24px', borderBottom: '1px solid #ece8e0' }}>
          <h2 className="text-lg font-bold text-[#1a1a1a]">New Invoice</h2>
          <button onClick={onClose} className="p-1.5 hover:bg-[#f0ede8] rounded-xl cursor-pointer transition-colors"><X size={18} className="text-[#999]" /></button>
        </div>
        <div style={{ padding: '16px 24px' }} className="space-y-4">
          {error && (
            <div className="flex items-center gap-2 text-sm text-red-700" style={{ padding: '10px 14px', background: '#fef2f2', borderRadius: 14 }}>
              <AlertCircle size={14} /> {error}
            </div>
          )}
          <div>
            <label className="section-label" style={{ fontSize: 10 }}>Customer Name</label>
            <input value={customerName} onChange={e => setCustomerName(e.target.value)} className={inputClass} placeholder="Customer name" />
          </div>

          <div>
            <label className="section-label" style={{ fontSize: 10 }}>Line Items</label>
            <div className="empire-card flat" style={{ padding: 0, overflow: 'hidden' }}>
              <table className="empire-table">
                <thead>
                  <tr>
                    <th className="text-left">Description</th>
                    <th className="text-right" style={{ width: 80 }}>Qty</th>
                    <th className="text-right" style={{ width: 96 }}>Rate</th>
                    <th className="text-right" style={{ width: 96 }}>Amount</th>
                    <th style={{ width: 32 }} />
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, idx) => (
                    <tr key={idx}>
                      <td>
                        <input
                          value={item.description}
                          onChange={e => updateItem(idx, 'description', e.target.value)}
                          className="w-full px-2 py-1 text-sm border border-transparent focus:border-[#ece8e0] rounded-lg focus:outline-none bg-transparent"
                          placeholder="Item description"
                        />
                      </td>
                      <td>
                        <input
                          type="number" min="1" value={item.qty}
                          onChange={e => updateItem(idx, 'qty', Number(e.target.value))}
                          className="w-full px-2 py-1 text-sm text-right border border-transparent focus:border-[#ece8e0] rounded-lg focus:outline-none bg-transparent"
                        />
                      </td>
                      <td>
                        <input
                          type="number" min="0" step="0.01" value={item.rate}
                          onChange={e => updateItem(idx, 'rate', Number(e.target.value))}
                          className="w-full px-2 py-1 text-sm text-right border border-transparent focus:border-[#ece8e0] rounded-lg focus:outline-none bg-transparent"
                        />
                      </td>
                      <td className="text-sm text-right text-[#555] font-medium">{fmt(item.amount)}</td>
                      <td>
                        <button onClick={() => removeItem(idx)} className="p-1 text-[#bbb] hover:text-red-500 cursor-pointer">
                          <X size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <button onClick={addItem} className="mt-2 text-xs text-[#b8960c] hover:underline font-bold cursor-pointer">
              + Add Line Item
            </button>
          </div>

          <div style={{ borderTop: '1px solid #ece8e0', paddingTop: 12 }} className="space-y-1 text-sm text-right">
            <div className="flex justify-end gap-8"><span className="text-[#999]">Subtotal</span><span className="w-28 font-medium">{fmt(subtotal)}</span></div>
            <div className="flex justify-end gap-8"><span className="text-[#999]">Tax (6%)</span><span className="w-28 font-medium">{fmt(tax)}</span></div>
            <div className="flex justify-end gap-8 text-base font-bold"><span>Total</span><span className="w-28">{fmt(total)}</span></div>
          </div>
        </div>
        <div className="flex justify-end gap-2" style={{ padding: '12px 24px', borderTop: '1px solid #ece8e0' }}>
          <button onClick={onClose} className="px-4 py-2.5 text-xs font-medium text-[#999] hover:text-[#555] transition-colors cursor-pointer">Cancel</button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2.5 text-xs font-bold text-white bg-[#b8960c] hover:bg-[#a68500] rounded-xl disabled:opacity-50 transition-colors cursor-pointer"
          >
            {saving ? 'Saving...' : 'Save Invoice'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function InvoiceList() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState('all');
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  const fetchInvoices = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (status !== 'all') params.set('status', status);
      if (search.trim()) params.set('search', search.trim());
      const res = await fetch(`${API}/finance/invoices?${params}`);
      if (!res.ok) {
        if (res.status === 404 || res.status === 500) {
          setError(null);
          setInvoices([]);
          return;
        }
        throw new Error(`Failed to load invoices (${res.status})`);
      }
      const data = await res.json();
      setInvoices(Array.isArray(data) ? data : data.items || []);
    } catch (err: any) {
      setError(null);
      setInvoices([]);
    } finally {
      setLoading(false);
    }
  }, [status, search]);

  useEffect(() => { fetchInvoices(); }, [fetchInvoices]);

  const columns: Column[] = [
    { key: 'invoice_number', label: 'Invoice #', sortable: true },
    { key: 'customer_name', label: 'Customer', sortable: true },
    { key: 'amount', label: 'Amount', sortable: true, render: (r) => <span className="font-bold text-[#1a1a1a]">{fmt(r.amount || 0)}</span> },
    { key: 'due_date', label: 'Due Date', sortable: true, render: (r) => (
      <span className="text-xs text-[#999]" suppressHydrationWarning>{r.due_date ? new Date(r.due_date).toLocaleDateString() : '\u2014'}</span>
    )},
    { key: 'status', label: 'Status', sortable: true, render: (r) => <StatusBadge status={r.status || 'draft'} /> },
    { key: 'balance', label: 'Balance', sortable: true, render: (r) => <span className="font-bold text-[#b8960c]">{fmt(r.balance ?? r.amount ?? 0)}</span> },
  ];

  return (
    <div className="bg-[#faf9f7] min-h-screen">
      <div className="max-w-6xl mx-auto" style={{ padding: '24px 36px' }}>
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#fdf8eb] flex items-center justify-center">
              <FileText size={20} className="text-[#b8960c]" />
            </div>
            <h1 className="text-xl font-bold text-[#1a1a1a]">Invoices</h1>
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 px-4 py-2.5 text-xs font-bold text-white bg-[#b8960c] hover:bg-[#a68500] rounded-xl transition-colors cursor-pointer"
          >
            <Plus size={16} /> New Invoice
          </button>
        </div>

        {error && (
          <div className="mb-4 empire-card flat" style={{ padding: 12, borderColor: '#fca5a5', background: '#fef2f2' }}>
            <div className="flex items-center gap-2 text-sm text-red-700">
              <AlertCircle size={16} /> {error}
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3 mb-5">
          <select
            value={status}
            onChange={e => setStatus(e.target.value)}
            className="px-3 py-2.5 text-xs border border-[#ece8e0] rounded-[14px] bg-[#faf9f7] text-[#555] focus:outline-none focus:border-[#b8960c] transition-colors"
          >
            {STATUS_OPTIONS.map(s => (
              <option key={s} value={s}>{s === 'all' ? 'All Statuses' : s.charAt(0).toUpperCase() + s.slice(1)}</option>
            ))}
          </select>
          <div className="flex-1 max-w-sm">
            <SearchBar value={search} onChange={setSearch} placeholder="Search invoices..." />
          </div>
        </div>

        {/* Table */}
        {!loading && invoices.length === 0 && !error ? (
          <EmptyState
            icon={<FileText size={40} />}
            title="No invoices yet"
            description="Connect backend endpoint to enable, or create your first invoice to get started."
            action={{ label: 'New Invoice', onClick: () => setShowForm(true) }}
          />
        ) : (
          <DataTable
            columns={columns}
            data={invoices}
            loading={loading}
            onRowClick={(row) => setExpanded(expanded === row.id ? null : row.id)}
            emptyMessage="No invoices match your filters."
          />
        )}

        {/* Expanded detail */}
        {expanded && (() => {
          const inv = invoices.find(i => i.id === expanded);
          if (!inv) return null;
          return (
            <div className="mt-3 empire-card flat" style={{ padding: 20 }}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-bold text-[#1a1a1a]">Invoice {inv.invoice_number}</h3>
                <button onClick={() => setExpanded(null)} className="text-[#bbb] hover:text-[#555] cursor-pointer"><X size={16} /></button>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                <div><span className="section-label" style={{ fontSize: 10 }}>Customer</span><span className="text-[#555] block">{inv.customer_name}</span></div>
                <div><span className="section-label" style={{ fontSize: 10 }}>Amount</span><span className="text-[#555] block">{fmt(inv.amount)}</span></div>
                <div><span className="section-label" style={{ fontSize: 10 }}>Balance</span><span className="text-[#555] block">{fmt(inv.balance ?? inv.amount)}</span></div>
                <div>
                  <span className="section-label" style={{ fontSize: 10 }}>Due Date</span>
                  <span className="text-[#555] block" suppressHydrationWarning>{inv.due_date ? new Date(inv.due_date).toLocaleDateString() : '\u2014'}</span>
                </div>
              </div>
            </div>
          );
        })()}

        {showForm && (
          <InvoiceForm
            onClose={() => setShowForm(false)}
            onSaved={() => { setShowForm(false); fetchInvoices(); }}
          />
        )}
      </div>
    </div>
  );
}
