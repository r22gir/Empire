'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Receipt, Plus, AlertCircle, X, Filter } from 'lucide-react';
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
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedExpense, setSelectedExpense] = useState<Expense | null>(null);

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
      if (!res.ok) {
        if (res.status === 404 || res.status === 500) {
          setError(null);
          setExpenses([]);
          return;
        }
        throw new Error(`Failed to load expenses (${res.status})`);
      }
      const data = await res.json();
      setExpenses(Array.isArray(data) ? data : data.items || []);
    } catch (err: any) {
      setError(null);
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
          expense_date: formDate,
          vendor: formVendor.trim(),
          category: formCategory,
          amount: Number(formAmount),
          description: formDesc.trim(),
        }),
      });
      if (!res.ok) {
        if (res.status === 404) throw new Error('Expense endpoint not available. Connect backend to enable.');
        throw new Error(`Failed to add expense (${res.status})`);
      }
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
      <span className="text-xs text-[#999]" suppressHydrationWarning>{r.date ? new Date(r.date).toLocaleDateString() : '\u2014'}</span>
    )},
    { key: 'vendor', label: 'Vendor', sortable: true },
    { key: 'category', label: 'Category', sortable: true, render: (r) => (
      <span className="status-pill capitalize" style={{ backgroundColor: '#f0ede8', color: '#777' }}>{(r.category || 'other').replace(/_/g, ' ')}</span>
    )},
    { key: 'amount', label: 'Amount', sortable: true, render: (r) => <span className="text-red-600 font-bold">{fmt(r.amount || 0)}</span> },
    { key: 'description', label: 'Description' },
  ];

  const CATEGORY_COLORS: Record<string, string> = {
    fabric: '#8b5cf6', hardware: '#6366f1', labor: '#3b82f6', shipping: '#0ea5e9',
    rent: '#14b8a6', utilities: '#22c55e', marketing: '#eab308', tools: '#f97316',
    vehicle: '#ef4444', insurance: '#ec4899', other: '#6b7280',
  };

  const inputClass = "w-full px-3.5 py-2.5 text-sm border border-[#ece8e0] rounded-[14px] bg-[#faf9f7] outline-none focus:border-[#b8960c] transition-colors";

  return (
    <div className="bg-[#faf9f7] min-h-screen">
      <div className="max-w-6xl mx-auto" style={{ padding: '24px 36px' }}>
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-[#fdf8eb] flex items-center justify-center">
            <Receipt size={20} className="text-[#b8960c]" />
          </div>
          <h1 className="text-xl font-bold text-[#1a1a1a]">Expenses</h1>
        </div>

        {error && (
          <div className="mb-4 empire-card flat" style={{ padding: 12, borderColor: '#fca5a5', background: '#fef2f2' }}>
            <div className="flex items-center gap-2 text-sm text-red-700">
              <AlertCircle size={16} /> {error}
            </div>
          </div>
        )}

        {/* Quick-Add Form */}
        <div className="empire-card flat" style={{ padding: 20, marginBottom: 24 }}>
          <div className="section-label" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Plus size={16} className="text-[#b8960c]" /> Quick Add Expense
          </div>
          {formError && (
            <div className="mb-3 text-xs text-red-700" style={{ padding: '8px 14px', background: '#fef2f2', borderRadius: 14 }}>{formError}</div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            <div>
              <label className="kpi-label block mb-1">Date</label>
              <input type="date" value={formDate} onChange={e => setFormDate(e.target.value)} className={inputClass} />
            </div>
            <div>
              <label className="kpi-label block mb-1">Vendor</label>
              <input value={formVendor} onChange={e => setFormVendor(e.target.value)} className={inputClass} placeholder="Vendor name" />
            </div>
            <div>
              <label className="kpi-label block mb-1">Category</label>
              <select value={formCategory} onChange={e => setFormCategory(e.target.value)} className={inputClass}>
                {CATEGORIES.map(c => (
                  <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="kpi-label block mb-1">Amount</label>
              <input type="number" min="0" step="0.01" value={formAmount} onChange={e => setFormAmount(e.target.value)} className={inputClass} placeholder="0.00" />
            </div>
            <div>
              <label className="kpi-label block mb-1">Description</label>
              <div className="flex gap-2">
                <input
                  value={formDesc}
                  onChange={e => setFormDesc(e.target.value)}
                  className={`flex-1 ${inputClass}`}
                  placeholder="Notes"
                  onKeyDown={e => { if (e.key === 'Enter') handleAdd(); }}
                />
                <button
                  onClick={handleAdd}
                  disabled={saving}
                  className="px-4 py-2.5 text-xs font-bold text-white bg-[#b8960c] hover:bg-[#a68500] rounded-xl disabled:opacity-50 shrink-0 transition-colors cursor-pointer"
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
            <div className="section-label">Summary by Category (Click to filter)</div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {Object.entries(categorySummary)
                .sort((a, b) => b[1] - a[1])
                .map(([cat, total]) => {
                  const isSelected = selectedCategory === cat;
                  return (
                    <div
                      key={cat}
                      onClick={() => setSelectedCategory(prev => prev === cat ? null : cat)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setSelectedCategory(prev => prev === cat ? null : cat); }}
                      className="empire-card flat cursor-pointer transition-all hover:border-[#b8960c]"
                      style={{
                        padding: 14,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12,
                        borderColor: isSelected ? '#b8960c' : undefined,
                        backgroundColor: isSelected ? '#fdf8eb' : undefined,
                        boxShadow: isSelected ? '0 0 0 1px #b8960c' : undefined,
                      }}
                    >
                      <div
                        className="w-3.5 h-3.5 rounded-full shrink-0"
                        style={{ backgroundColor: CATEGORY_COLORS[cat] || '#6b7280' }}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="kpi-label capitalize" style={{ marginBottom: 0 }}>{cat.replace(/_/g, ' ')}</p>
                        <p className="text-sm font-bold text-[#1a1a1a]">{fmt(total)}</p>
                      </div>
                    </div>
                  );
                })}
            </div>
          </div>
        )}

        {/* Filter Indicator */}
        {selectedCategory && (
          <div className="flex items-center justify-between mb-3 px-3.5 py-2 bg-[#fdf8eb] border border-[#b8960c]/30 rounded-xl text-xs">
            <span className="font-semibold text-[#b8960c] flex items-center gap-1.5 capitalize">
              <Filter size={13} />
              Filtered by Category: {selectedCategory.replace(/_/g, ' ')} ({(expenses.filter(e => e.category === selectedCategory)).length} matching)
            </span>
            <button
              onClick={() => setSelectedCategory(null)}
              className="text-[#999] hover:text-[#1a1a1a] flex items-center gap-1 font-semibold cursor-pointer"
            >
              <X size={13} /> Clear Filter
            </button>
          </div>
        )}

        {/* Expenses Table */}
        {!loading && (selectedCategory ? expenses.filter(e => e.category === selectedCategory) : expenses).length === 0 && !error ? (
          <EmptyState
            icon={<Receipt size={40} />}
            title="No expenses found"
            description={selectedCategory ? `No expenses recorded under ${selectedCategory}.` : "Connect backend endpoint to enable, or use the form above to add your first expense."}
          />
        ) : (
          <DataTable
            columns={columns}
            data={selectedCategory ? expenses.filter(e => e.category === selectedCategory) : expenses}
            loading={loading}
            onRowClick={(row) => setSelectedExpense(row)}
            emptyMessage="No expenses found."
          />
        )}

        {/* Expense Detail Modal */}
        {selectedExpense && (
          <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
            <div className="empire-card" style={{ padding: 24, width: '100%', maxWidth: 440, boxShadow: '0 20px 60px rgba(0,0,0,0.12)' }}>
              <div className="flex items-center justify-between mb-4 pb-3 border-b border-[#ece8e0]">
                <div className="flex items-center gap-2">
                  <Receipt size={18} className="text-[#b8960c]" />
                  <h3 className="font-bold text-base text-[#1a1a1a]">Expense Details</h3>
                </div>
                <button onClick={() => setSelectedExpense(null)} className="p-1 hover:bg-[#f0ede8] rounded-lg cursor-pointer">
                  <X size={16} className="text-[#999]" />
                </button>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between py-1.5 border-b border-[#f5f3ef]">
                  <span className="text-[#999] font-medium">Vendor</span>
                  <span className="font-bold text-[#1a1a1a]">{selectedExpense.vendor}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[#f5f3ef]">
                  <span className="text-[#999] font-medium">Amount</span>
                  <span className="font-bold text-red-600">{fmt(selectedExpense.amount)}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[#f5f3ef]">
                  <span className="text-[#999] font-medium">Category</span>
                  <span className="status-pill capitalize" style={{ backgroundColor: '#f0ede8', color: '#777' }}>
                    {selectedExpense.category.replace(/_/g, ' ')}
                  </span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[#f5f3ef]">
                  <span className="text-[#999] font-medium">Date</span>
                  <span className="text-[#555]">{selectedExpense.date ? new Date(selectedExpense.date).toLocaleDateString() : '—'}</span>
                </div>
                {selectedExpense.description && (
                  <div className="pt-2">
                    <span className="text-[#999] text-xs font-semibold block mb-1">Description</span>
                    <p className="text-[#555] bg-[#faf9f7] p-2.5 rounded-xl border border-[#ece8e0] text-xs leading-relaxed">
                      {selectedExpense.description}
                    </p>
                  </div>
                )}
              </div>
              <div className="mt-5 flex justify-end">
                <button
                  onClick={() => setSelectedExpense(null)}
                  className="px-4 py-2 text-xs font-bold bg-[#faf9f7] hover:bg-[#f0ede8] border border-[#ece8e0] rounded-xl text-[#555] cursor-pointer"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
