'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Receipt, Plus, AlertCircle } from 'lucide-react';
import { API } from '../../../lib/api';
import DataTable, { Column } from '../shared/DataTable';
import EmptyState from '../shared/EmptyState';

interface Expense {
  id: string;
  date: string;
  vendor: string;
  category: string;
  amount: number;
  description: string;
}

const CATEGORIES = [
  'fabric', 'hardware', 'labor', 'shipping', 'rent',
  'utilities', 'marketing', 'tools', 'vehicle', 'insurance', 'other',
];

function fmt(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);
}

function todayISO(): string {
  return new Date().toISOString().split('T')[0];
}

export default function ExpenseTracker() {
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Quick-add form
  const [formDate, setFormDate] = useState(todayISO());
  const [formVendor, setFormVendor] = useState('');
  const [formCategory, setFormCategory] = useState('other');
  const [formAmount, setFormAmount] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const fetchExpenses = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/finance/expenses`);
      if (!res.ok) throw new Error(`Failed to load expenses (${res.status})`);
      const data = await res.json();
      setExpenses(Array.isArray(data) ? data : data.items || []);
    } catch (err: any) {
      setError(err.message);
      setExpenses([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchExpenses(); }, [fetchExpenses]);

  const handleAdd = async () => {
    if (!formVendor.trim()) { setFormError('Vendor is required'); return; }
    if (!formAmount || Number(formAmount) <= 0) { setFormError('Enter a valid amount'); return; }
    setSaving(true);
    setFormError(null);
    try {
      const res = await fetch(`${API}/finance/expenses`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date: formDate,
          vendor: formVendor.trim(),
          category: formCategory,
          amount: Number(formAmount),
          description: formDesc.trim(),
        }),
      });
      if (!res.ok) throw new Error(`Failed to add expense (${res.status})`);
      setFormVendor('');
      setFormAmount('');
      setFormDesc('');
      setFormDate(todayISO());
      setFormCategory('other');
      fetchExpenses();
    } catch (err: any) {
      setFormError(err.message);
    } finally {
      setSaving(false);
    }
  };

  // Monthly summary by category
  const categorySummary = expenses.reduce<Record<string, number>>((acc, e) => {
    const cat = e.category || 'other';
    acc[cat] = (acc[cat] || 0) + (e.amount || 0);
    return acc;
  }, {});

  const columns: Column[] = [
    { key: 'date', label: 'Date', sortable: true, render: (r) => (
      <span suppressHydrationWarning>{r.date ? new Date(r.date).toLocaleDateString() : '—'}</span>
    )},
    { key: 'vendor', label: 'Vendor', sortable: true },
    { key: 'category', label: 'Category', sortable: true, render: (r) => (
      <span className="capitalize text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{(r.category || 'other').replace(/_/g, ' ')}</span>
    )},
    { key: 'amount', label: 'Amount', sortable: true, render: (r) => <span className="text-red-600 font-medium">{fmt(r.amount || 0)}</span> },
    { key: 'description', label: 'Description' },
  ];

  const CATEGORY_COLORS: Record<string, string> = {
    fabric: '#8b5cf6', hardware: '#6366f1', labor: '#3b82f6', shipping: '#0ea5e9',
    rent: '#14b8a6', utilities: '#22c55e', marketing: '#eab308', tools: '#f97316',
    vehicle: '#ef4444', insurance: '#ec4899', other: '#6b7280',
  };

  return (
    <div className="bg-[#faf9f7] min-h-screen">
      <div className="max-w-6xl mx-auto px-8 py-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <Receipt size={24} className="text-[#b8960c]" />
          <h1 className="text-xl font-bold text-gray-800">Expenses</h1>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-sm text-red-700">
            <AlertCircle size={16} /> {error}
          </div>
        )}

        {/* Quick-Add Form */}
        <div className="bg-white border border-[#ece8e1] rounded-lg p-4 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <Plus size={16} className="text-[#b8960c]" /> Quick Add Expense
          </h2>
          {formError && (
            <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">{formError}</div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Date</label>
              <input
                type="date" value={formDate}
                onChange={e => setFormDate(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-[#ece8e1] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#b8960c]/30"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Vendor</label>
              <input
                value={formVendor}
                onChange={e => setFormVendor(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-[#ece8e1] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#b8960c]/30"
                placeholder="Vendor name"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Category</label>
              <select
                value={formCategory}
                onChange={e => setFormCategory(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-[#ece8e1] rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-[#b8960c]/30"
              >
                {CATEGORIES.map(c => (
                  <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Amount</label>
              <input
                type="number" min="0" step="0.01" value={formAmount}
                onChange={e => setFormAmount(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-[#ece8e1] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#b8960c]/30"
                placeholder="0.00"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Description</label>
              <div className="flex gap-2">
                <input
                  value={formDesc}
                  onChange={e => setFormDesc(e.target.value)}
                  className="flex-1 px-3 py-2 text-sm border border-[#ece8e1] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#b8960c]/30"
                  placeholder="Notes"
                  onKeyDown={e => { if (e.key === 'Enter') handleAdd(); }}
                />
                <button
                  onClick={handleAdd}
                  disabled={saving}
                  className="px-4 py-2 text-sm font-medium text-white bg-[#b8960c] hover:bg-[#a68500] rounded-lg disabled:opacity-50 shrink-0"
                >
                  {saving ? '...' : 'Add'}
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Monthly Summary by Category */}
        {Object.keys(categorySummary).length > 0 && (
          <div className="mb-6">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Summary by Category</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {Object.entries(categorySummary)
                .sort((a, b) => b[1] - a[1])
                .map(([cat, total]) => (
                  <div key={cat} className="bg-white border border-[#ece8e1] rounded-lg p-3 flex items-center gap-3">
                    <div
                      className="w-3 h-3 rounded-full shrink-0"
                      style={{ backgroundColor: CATEGORY_COLORS[cat] || '#6b7280' }}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-gray-500 capitalize">{cat.replace(/_/g, ' ')}</p>
                      <p className="text-sm font-bold text-gray-800">{fmt(total)}</p>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Expenses Table */}
        {!loading && expenses.length === 0 && !error ? (
          <EmptyState
            icon={<Receipt size={40} />}
            title="No expenses recorded"
            description="Use the form above to add your first expense."
          />
        ) : (
          <DataTable columns={columns} data={expenses} loading={loading} emptyMessage="No expenses found." />
        )}
      </div>
    </div>
  );
}
