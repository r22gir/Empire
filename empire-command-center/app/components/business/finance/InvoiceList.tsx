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
      if (!res.ok) throw new Error(`Failed to create invoice (${res.status})`);
      onSaved();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-[#ece8e1]">
          <h2 className="text-lg font-bold text-gray-800">New Invoice</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded"><X size={18} /></button>
        </div>
        <div className="p-4 space-y-4">
          {error && (
            <div className="p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700 flex items-center gap-2">
              <AlertCircle size={14} /> {error}
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Customer Name</label>
            <input
              value={customerName}
              onChange={e => setCustomerName(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-[#ece8e1] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#b8960c]/30"
              placeholder="Customer name"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-2">Line Items</label>
            <div className="border border-[#ece8e1] rounded-lg overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="bg-[#f5f3ef] text-xs text-gray-500 uppercase">
                    <th className="px-3 py-2 text-left">Description</th>
                    <th className="px-3 py-2 text-right w-20">Qty</th>
                    <th className="px-3 py-2 text-right w-24">Rate</th>
                    <th className="px-3 py-2 text-right w-24">Amount</th>
                    <th className="w-8" />
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, idx) => (
                    <tr key={idx} className="border-t border-[#ece8e1]">
                      <td className="px-2 py-1">
                        <input
                          value={item.description}
                          onChange={e => updateItem(idx, 'description', e.target.value)}
                          className="w-full px-2 py-1 text-sm border border-transparent focus:border-[#ece8e1] rounded focus:outline-none"
                          placeholder="Item description"
                        />
                      </td>
                      <td className="px-2 py-1">
                        <input
                          type="number" min="1" value={item.qty}
                          onChange={e => updateItem(idx, 'qty', Number(e.target.value))}
                          className="w-full px-2 py-1 text-sm text-right border border-transparent focus:border-[#ece8e1] rounded focus:outline-none"
                        />
                      </td>
                      <td className="px-2 py-1">
                        <input
                          type="number" min="0" step="0.01" value={item.rate}
                          onChange={e => updateItem(idx, 'rate', Number(e.target.value))}
                          className="w-full px-2 py-1 text-sm text-right border border-transparent focus:border-[#ece8e1] rounded focus:outline-none"
                        />
                      </td>
                      <td className="px-3 py-1 text-sm text-right text-gray-700">{fmt(item.amount)}</td>
                      <td className="px-1">
                        <button onClick={() => removeItem(idx)} className="p-1 text-gray-400 hover:text-red-500">
                          <X size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <button onClick={addItem} className="mt-2 text-xs text-[#b8960c] hover:underline font-medium">
              + Add Line Item
            </button>
          </div>

          <div className="border-t border-[#ece8e1] pt-3 space-y-1 text-sm text-right">
            <div className="flex justify-end gap-8"><span className="text-gray-500">Subtotal</span><span className="w-28 font-medium">{fmt(subtotal)}</span></div>
            <div className="flex justify-end gap-8"><span className="text-gray-500">Tax (6%)</span><span className="w-28 font-medium">{fmt(tax)}</span></div>
            <div className="flex justify-end gap-8 text-base font-bold"><span>Total</span><span className="w-28">{fmt(total)}</span></div>
          </div>
        </div>
        <div className="flex justify-end gap-2 p-4 border-t border-[#ece8e1]">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 rounded-lg">Cancel</button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 text-sm font-medium text-white bg-[#b8960c] hover:bg-[#a68500] rounded-lg disabled:opacity-50"
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
      if (!res.ok) throw new Error(`Failed to load invoices (${res.status})`);
      const data = await res.json();
      setInvoices(Array.isArray(data) ? data : data.items || []);
    } catch (err: any) {
      setError(err.message);
      setInvoices([]);
    } finally {
      setLoading(false);
    }
  }, [status, search]);

  useEffect(() => { fetchInvoices(); }, [fetchInvoices]);

  const columns: Column[] = [
    { key: 'invoice_number', label: 'Invoice #', sortable: true },
    { key: 'customer_name', label: 'Customer', sortable: true },
    { key: 'amount', label: 'Amount', sortable: true, render: (r) => fmt(r.amount || 0) },
    { key: 'due_date', label: 'Due Date', sortable: true, render: (r) => (
      <span suppressHydrationWarning>{r.due_date ? new Date(r.due_date).toLocaleDateString() : '—'}</span>
    )},
    { key: 'status', label: 'Status', sortable: true, render: (r) => <StatusBadge status={r.status || 'draft'} /> },
    { key: 'balance', label: 'Balance', sortable: true, render: (r) => fmt(r.balance ?? r.amount ?? 0) },
  ];

  return (
    <div className="bg-[#faf9f7] min-h-screen">
      <div className="max-w-6xl mx-auto px-8 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <FileText size={24} className="text-[#b8960c]" />
            <h1 className="text-xl font-bold text-gray-800">Invoices</h1>
          </div>
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-[#b8960c] hover:bg-[#a68500] rounded-lg transition-colors"
          >
            <Plus size={16} /> New Invoice
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-sm text-red-700">
            <AlertCircle size={16} /> {error}
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3 mb-4">
          <select
            value={status}
            onChange={e => setStatus(e.target.value)}
            className="px-3 py-2 text-sm border border-[#ece8e1] rounded-lg bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-[#b8960c]/30"
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
            title="No invoices found"
            description="Create your first invoice to get started."
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
            <div className="mt-2 bg-white border border-[#ece8e1] rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-700">Invoice {inv.invoice_number}</h3>
                <button onClick={() => setExpanded(null)} className="text-gray-400 hover:text-gray-600"><X size={16} /></button>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                <div><span className="text-xs text-gray-500 block">Customer</span>{inv.customer_name}</div>
                <div><span className="text-xs text-gray-500 block">Amount</span>{fmt(inv.amount)}</div>
                <div><span className="text-xs text-gray-500 block">Balance</span>{fmt(inv.balance ?? inv.amount)}</div>
                <div>
                  <span className="text-xs text-gray-500 block">Due Date</span>
                  <span suppressHydrationWarning>{inv.due_date ? new Date(inv.due_date).toLocaleDateString() : '—'}</span>
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
