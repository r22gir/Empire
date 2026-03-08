'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { PieChart, DollarSign, ArrowDownCircle, TrendingUp, Clock, AlertCircle } from 'lucide-react';
import { API } from '../../../lib/api';
import KPICard from '../shared/KPICard';
import DataTable, { Column } from '../shared/DataTable';
import EmptyState from '../shared/EmptyState';
import StatusBadge from '../shared/StatusBadge';

type DateRange = 'this_month' | 'last_month' | 'this_quarter' | 'ytd';

interface DashboardData {
  revenue_mtd: number;
  revenue_trend: number;
  expenses_mtd: number;
  expenses_trend: number;
  net_profit: number;
  profit_trend: number;
  outstanding: number;
  aging: { label: string; amount: number }[];
  top_customers: { name: string; revenue: number }[];
}

interface Transaction {
  id: string;
  date: string;
  description: string;
  type: string;
  amount: number;
  status: string;
}

const DATE_RANGES: { value: DateRange; label: string }[] = [
  { value: 'this_month', label: 'This Month' },
  { value: 'last_month', label: 'Last Month' },
  { value: 'this_quarter', label: 'This Quarter' },
  { value: 'ytd', label: 'YTD' },
];

function fmt(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(n);
}

function fmtTrend(n: number): string {
  const sign = n >= 0 ? '+' : '';
  return `${sign}${n.toFixed(1)}%`;
}

export default function FinanceDashboard() {
  const [range, setRange] = useState<DateRange>('this_month');
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashRes, paymentsRes, expensesRes] = await Promise.allSettled([
        fetch(`${API}/finance/dashboard?range=${range}`),
        fetch(`${API}/finance/payments?limit=10`),
        fetch(`${API}/finance/expenses?limit=10`),
      ]);

      if (dashRes.status === 'fulfilled' && dashRes.value.ok) {
        const data = await dashRes.value.json();
        setDashboard(data);
      } else {
        setDashboard({
          revenue_mtd: 0, revenue_trend: 0, expenses_mtd: 0, expenses_trend: 0,
          net_profit: 0, profit_trend: 0, outstanding: 0,
          aging: [
            { label: '0-30 days', amount: 0 },
            { label: '31-60 days', amount: 0 },
            { label: '61-90 days', amount: 0 },
            { label: '90+ days', amount: 0 },
          ],
          top_customers: [],
        });
      }

      const txns: Transaction[] = [];
      if (paymentsRes.status === 'fulfilled' && paymentsRes.value.ok) {
        const payments = await paymentsRes.value.json();
        const items = Array.isArray(payments) ? payments : payments.items || [];
        items.forEach((p: any) => txns.push({
          id: p.id, date: p.date || p.payment_date, description: p.description || p.customer_name || 'Payment',
          type: 'payment', amount: p.amount, status: p.status || 'completed',
        }));
      }
      if (expensesRes.status === 'fulfilled' && expensesRes.value.ok) {
        const expenses = await expensesRes.value.json();
        const items = Array.isArray(expenses) ? expenses : expenses.items || [];
        items.forEach((e: any) => txns.push({
          id: e.id, date: e.date || e.expense_date, description: e.description || e.vendor || 'Expense',
          type: 'expense', amount: e.amount, status: e.status || 'recorded',
        }));
      }

      txns.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
      setTransactions(txns.slice(0, 20));
    } catch (err: any) {
      setError(err.message || 'Failed to load finance data');
    } finally {
      setLoading(false);
    }
  }, [range]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const txnColumns: Column[] = [
    { key: 'date', label: 'Date', sortable: true, render: (r) => (
      <span suppressHydrationWarning>{r.date ? new Date(r.date).toLocaleDateString() : '—'}</span>
    )},
    { key: 'description', label: 'Description', sortable: true },
    { key: 'type', label: 'Type', sortable: true, render: (r) => (
      <StatusBadge status={r.type} colorMap={{ payment: { bg: 'bg-green-50', text: 'text-green-700' }, expense: { bg: 'bg-red-50', text: 'text-red-700' } }} />
    )},
    { key: 'amount', label: 'Amount', sortable: true, render: (r) => (
      <span className={r.type === 'expense' ? 'text-red-600' : 'text-green-600'}>
        {r.type === 'expense' ? '-' : '+'}{fmt(r.amount)}
      </span>
    )},
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
  ];

  const d = dashboard;
  const maxAging = d ? Math.max(...d.aging.map(a => a.amount), 1) : 1;

  return (
    <div className="bg-[#faf9f7] min-h-screen">
      <div className="max-w-6xl mx-auto px-8 py-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <PieChart size={24} className="text-[#b8960c]" />
            <h1 className="text-xl font-bold text-gray-800">Finance</h1>
          </div>
          <div className="flex gap-1 bg-white border border-[#ece8e1] rounded-lg p-1">
            {DATE_RANGES.map(dr => (
              <button
                key={dr.value}
                onClick={() => setRange(dr.value)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  range === dr.value
                    ? 'bg-[#b8960c] text-white'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                }`}
              >
                {dr.label}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-sm text-red-700">
            <AlertCircle size={16} /> {error}
          </div>
        )}

        {/* KPI Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <KPICard
            icon={<DollarSign size={20} />}
            label="Revenue (MTD)"
            value={loading ? '...' : fmt(d?.revenue_mtd ?? 0)}
            trend={d ? fmtTrend(d.revenue_trend) : undefined}
            trendUp={d ? d.revenue_trend >= 0 : undefined}
            color="#16a34a"
          />
          <KPICard
            icon={<ArrowDownCircle size={20} />}
            label="Expenses (MTD)"
            value={loading ? '...' : fmt(d?.expenses_mtd ?? 0)}
            trend={d ? fmtTrend(d.expenses_trend) : undefined}
            trendUp={d ? d.expenses_trend <= 0 : undefined}
            color="#dc2626"
          />
          <KPICard
            icon={<TrendingUp size={20} />}
            label="Net Profit"
            value={loading ? '...' : fmt(d?.net_profit ?? 0)}
            trend={d ? fmtTrend(d.profit_trend) : undefined}
            trendUp={d ? d.profit_trend >= 0 : undefined}
            color="#2563eb"
          />
          <KPICard
            icon={<Clock size={20} />}
            label="Outstanding"
            value={loading ? '...' : fmt(d?.outstanding ?? 0)}
            color="#ea580c"
          />
        </div>

        {/* Accounts Receivable Aging */}
        <div className="bg-white border border-[#ece8e1] rounded-lg p-4 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Accounts Receivable Aging</h2>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="h-6 bg-gray-100 rounded animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {(d?.aging ?? []).map((bucket) => (
                <div key={bucket.label} className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 w-20 shrink-0">{bucket.label}</span>
                  <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
                    <div
                      className="h-full bg-[#b8960c] rounded-full transition-all duration-500 flex items-center justify-end pr-2"
                      style={{ width: `${Math.max((bucket.amount / maxAging) * 100, 2)}%` }}
                    >
                      {bucket.amount > 0 && (
                        <span className="text-[10px] font-medium text-white whitespace-nowrap">{fmt(bucket.amount)}</span>
                      )}
                    </div>
                  </div>
                  <span className="text-xs font-medium text-gray-600 w-20 text-right">{fmt(bucket.amount)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Recent Transactions */}
          <div className="lg:col-span-2">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Recent Transactions</h2>
            <DataTable columns={txnColumns} data={transactions} loading={loading} emptyMessage="No recent transactions." />
          </div>

          {/* Revenue by Customer */}
          <div>
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Top Customers by Revenue</h2>
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map(i => (
                  <div key={i} className="h-10 bg-gray-100 rounded animate-pulse" />
                ))}
              </div>
            ) : (d?.top_customers ?? []).length === 0 ? (
              <EmptyState icon={<DollarSign size={32} />} title="No customer data" />
            ) : (
              <div className="bg-white border border-[#ece8e1] rounded-lg divide-y divide-[#ece8e1]">
                {(d?.top_customers ?? []).slice(0, 5).map((c, i) => (
                  <div key={c.name} className="flex items-center justify-between px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-gray-400 w-5">{i + 1}</span>
                      <span className="text-sm text-gray-700">{c.name}</span>
                    </div>
                    <span className="text-sm font-semibold text-gray-800">{fmt(c.revenue)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
