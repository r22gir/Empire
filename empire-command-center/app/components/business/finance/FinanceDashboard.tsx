'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { PieChart, DollarSign, ArrowDownCircle, TrendingUp, Clock, AlertCircle, Send } from 'lucide-react';
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

interface CollectionsWorkItem {
  customer_id: string | null;
  customer_name: string;
  customer_email?: string | null;
  business_unit: string;
  open_balance: number;
  overdue_balance: number;
  aging: Record<string, number>;
  open_invoice_count: number;
  overdue_invoice_count: number;
  last_collection_action?: string | null;
  last_collection_notes?: string | null;
  last_action_date?: string | null;
  next_action?: string | null;
}

type BusinessFilter = 'workroom' | 'woodcraft' | 'all';

const DATE_RANGES: { value: DateRange; label: string }[] = [
  { value: 'this_month', label: 'This Month' },
  { value: 'last_month', label: 'Last Month' },
  { value: 'this_quarter', label: 'This Quarter' },
  { value: 'ytd', label: 'YTD' },
];

const EMPTY_DASHBOARD: DashboardData = {
  revenue_mtd: 0,
  revenue_trend: 0,
  expenses_mtd: 0,
  expenses_trend: 0,
  net_profit: 0,
  profit_trend: 0,
  outstanding: 0,
  aging: [
    { label: '0-30 days', amount: 0 },
    { label: '31-60 days', amount: 0 },
    { label: '61-90 days', amount: 0 },
    { label: '90+ days', amount: 0 },
  ],
  top_customers: [],
};

function normalizeDashboardData(data: any): DashboardData {
  const aging = data?.aging ?? (data?.accounts_receivable_aging ? [
    { label: '0-30 days', amount: data.accounts_receivable_aging['0_30'] ?? 0 },
    { label: '31-60 days', amount: data.accounts_receivable_aging['31_60'] ?? 0 },
    { label: '61-90 days', amount: data.accounts_receivable_aging['61_90'] ?? 0 },
    { label: '90+ days', amount: data.accounts_receivable_aging['90_plus'] ?? 0 },
  ] : EMPTY_DASHBOARD.aging);

  return {
    revenue_mtd: data?.revenue_mtd ?? data?.revenue?.mtd ?? 0,
    revenue_trend: data?.revenue_trend ?? 0,
    expenses_mtd: data?.expenses_mtd ?? data?.expenses?.mtd ?? 0,
    expenses_trend: data?.expenses_trend ?? 0,
    net_profit: data?.net_profit_mtd ?? (typeof data?.net_profit === 'number' ? data.net_profit : data?.net_profit?.mtd) ?? 0,
    profit_trend: data?.profit_trend ?? 0,
    outstanding: data?.outstanding_total ?? (typeof data?.outstanding === 'number' ? data.outstanding : data?.outstanding?.total) ?? 0,
    aging,
    top_customers: data?.top_customers ?? [],
  };
}

function fmt(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(n);
}

function fmtTrend(n: number): string {
  const sign = n >= 0 ? '+' : '';
  return `${sign}${n.toFixed(1)}%`;
}

function actionLabel(action?: string | null): string {
  return (action || 'none').replace(/_/g, ' ');
}

export default function FinanceDashboard({ onSelectCustomer }: { onSelectCustomer?: (id: string) => void }) {
  const [range, setRange] = useState<DateRange>('this_month');
  const [businessFilter, setBusinessFilter] = useState<BusinessFilter>('workroom');
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [collections, setCollections] = useState<CollectionsWorkItem[]>([]);
  const [collectionsTotals, setCollectionsTotals] = useState<any>(null);
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
        setDashboard(normalizeDashboardData(data));
      } else {
        setDashboard(EMPTY_DASHBOARD);
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

  const fetchCollections = useCallback(async () => {
    try {
      const suffix = businessFilter === 'all' ? '' : `?business=${businessFilter}`;
      const res = await fetch(`${API}/finance/collections/worklist${suffix}`);
      if (!res.ok) throw new Error(`Failed to load collections worklist (${res.status})`);
      const data = await res.json();
      setCollections(data.items || []);
      setCollectionsTotals(data.totals || null);
    } catch (err: any) {
      setCollections([]);
      setCollectionsTotals(null);
      setError(err.message || 'Failed to load collections worklist');
    }
  }, [businessFilter]);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => { fetchCollections(); }, [fetchCollections]);

  const txnColumns: Column[] = [
    { key: 'date', label: 'Date', sortable: true, render: (r) => (
      <span suppressHydrationWarning>{r.date ? new Date(r.date).toLocaleDateString() : '\u2014'}</span>
    )},
    { key: 'description', label: 'Description', sortable: true },
    { key: 'type', label: 'Type', sortable: true, render: (r) => (
      <StatusBadge status={r.type} colorMap={{ payment: { bg: '#f0fdf4', text: '#22c55e' }, expense: { bg: '#fef2f2', text: '#dc2626' } }} />
    )},
    { key: 'amount', label: 'Amount', sortable: true, render: (r) => (
      <span className={r.type === 'expense' ? 'text-red-600 font-bold' : 'text-[#22c55e] font-bold'}>
        {r.type === 'expense' ? '-' : '+'}{fmt(r.amount)}
      </span>
    )},
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status} /> },
  ];

  const collectionColumns: Column[] = [
    { key: 'customer_name', label: 'Customer', sortable: true, render: (r: CollectionsWorkItem) => (
      <div>
        <div className="font-bold text-[#1a1a1a]">{r.customer_name || 'Unknown customer'}</div>
        <div className="text-[11px] text-[#999]">{r.customer_email || 'No email'} · {r.business_unit}</div>
      </div>
    )},
    { key: 'open_balance', label: 'Open', sortable: true, render: (r: CollectionsWorkItem) => <span className="font-bold text-[#1a1a1a]">{fmt(r.open_balance || 0)}</span> },
    { key: 'overdue_balance', label: 'Overdue', sortable: true, render: (r: CollectionsWorkItem) => <span className="font-bold text-[#dc2626]">{fmt(r.overdue_balance || 0)}</span> },
    { key: 'open_invoice_count', label: 'Invoices', sortable: true, render: (r: CollectionsWorkItem) => (
      <span className="text-xs text-[#555]">{r.open_invoice_count || 0} open · {r.overdue_invoice_count || 0} overdue</span>
    )},
    { key: 'aging', label: 'Aging', render: (r: CollectionsWorkItem) => (
      <span className="text-xs text-[#555]">
        0-30 {fmt(r.aging?.['0_30'] || 0)} · 31-60 {fmt(r.aging?.['31_60'] || 0)} · 61+ {fmt((r.aging?.['61_90'] || 0) + (r.aging?.['90_plus'] || 0))}
      </span>
    )},
    { key: 'last_collection_action', label: 'Last Action', sortable: true, render: (r: CollectionsWorkItem) => (
      <div>
        <div className="text-xs font-bold text-[#555] capitalize">{actionLabel(r.last_collection_action)}</div>
        <div className="text-[11px] text-[#999]" suppressHydrationWarning>{r.last_action_date ? new Date(r.last_action_date).toLocaleDateString() : 'No action logged'}</div>
        {r.last_collection_notes && <div className="text-[11px] text-[#999] truncate max-w-[180px]">{r.last_collection_notes}</div>}
      </div>
    )},
    { key: 'next_action', label: 'Next', sortable: true, render: (r: CollectionsWorkItem) => <StatusBadge status={actionLabel(r.next_action)} /> },
    { key: 'customer_id', label: '', render: (r: CollectionsWorkItem) => (
      <button
        disabled={!r.customer_id}
        onClick={() => r.customer_id && onSelectCustomer?.(r.customer_id)}
        className="px-3 py-2 text-xs font-bold rounded-lg disabled:opacity-50"
        style={{ color: '#fff', background: '#b8960c', border: 'none', cursor: r.customer_id ? 'pointer' : 'not-allowed' }}
      >
        Statement
      </button>
    )},
  ];

  const d = dashboard;
  const maxAging = d?.aging?.length ? Math.max(...d.aging.map(a => a.amount), 1) : 1;

  return (
    <div className="bg-[#faf9f7] min-h-screen">
      <div className="max-w-6xl mx-auto" style={{ padding: '24px 36px' }}>
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#fdf8eb] flex items-center justify-center">
              <PieChart size={20} className="text-[#b8960c]" />
            </div>
            <h1 className="text-xl font-bold text-[#1a1a1a]">Finance</h1>
          </div>
          <div className="flex gap-1 empire-card flat" style={{ padding: 4 }}>
            {DATE_RANGES.map(dr => (
              <button
                key={dr.value}
                onClick={() => setRange(dr.value)}
                className={`filter-tab ${range === dr.value ? 'active' : ''}`}
              >
                {dr.label}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="mb-4 empire-card flat" style={{ padding: 12, borderColor: '#fca5a5', background: '#fef2f2' }}>
            <div className="flex items-center gap-2 text-sm text-red-700">
              <AlertCircle size={16} /> {error}
            </div>
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
            color="#22c55e"
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
        <div className="empire-card flat" style={{ padding: 20, marginBottom: 24 }}>
          <div className="section-label">Accounts Receivable Aging</div>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="h-6 bg-[#ece8e0] rounded-lg animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {(d?.aging ?? []).map((bucket) => (
                <div key={bucket.label} className="flex items-center gap-3">
                  <span className="text-xs text-[#999] w-20 shrink-0">{bucket.label}</span>
                  <div className="flex-1 bg-[#ece8e0] rounded-full h-5 overflow-hidden">
                    <div
                      className="h-full bg-[#b8960c] rounded-full transition-all duration-500 flex items-center justify-end pr-2"
                      style={{ width: `${Math.max((bucket.amount / maxAging) * 100, 2)}%` }}
                    >
                      {bucket.amount > 0 && (
                        <span className="text-[10px] font-bold text-white whitespace-nowrap">{fmt(bucket.amount)}</span>
                      )}
                    </div>
                  </div>
                  <span className="text-xs font-bold text-[#555] w-20 text-right">{fmt(bucket.amount)}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Collections Worklist */}
        <div className="empire-card flat" style={{ padding: 20, marginBottom: 24 }}>
          <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
            <div>
              <div className="section-label">Collections Worklist</div>
              <div className="text-xs text-[#777]">
                {fmt(collectionsTotals?.open_balance || 0)} open · {fmt(collectionsTotals?.overdue_balance || 0)} overdue · {collectionsTotals?.overdue_invoice_count || 0} overdue invoices
              </div>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {(['workroom', 'woodcraft', 'all'] as BusinessFilter[]).map((biz) => (
                <button
                  key={biz}
                  onClick={() => setBusinessFilter(biz)}
                  className={`filter-tab ${businessFilter === biz ? 'active' : ''}`}
                >
                  {biz === 'all' ? 'All' : biz === 'woodcraft' ? 'WoodCraft' : 'Workroom'}
                </button>
              ))}
            </div>
          </div>
          <DataTable columns={collectionColumns} data={collections} loading={loading} emptyMessage="No open AR to collect." />
          <div className="mt-3 flex items-center gap-2 text-xs text-[#777]">
            <Send size={13} /> Reminder history comes from the customer collections event log. No email delivery is assumed here.
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Recent Transactions */}
          <div className="lg:col-span-2">
            <div className="section-label">Recent Transactions</div>
            <DataTable columns={txnColumns} data={transactions} loading={loading} emptyMessage="No recent transactions." />
          </div>

          {/* Revenue by Customer */}
          <div>
            <div className="section-label">Top Customers by Revenue</div>
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map(i => (
                  <div key={i} className="h-10 bg-[#ece8e0] rounded-xl animate-pulse" />
                ))}
              </div>
            ) : (d?.top_customers ?? []).length === 0 ? (
              <EmptyState icon={<DollarSign size={32} />} title="No customer data" />
            ) : (
              <div className="empire-card flat" style={{ padding: 0, overflow: 'hidden' }}>
                {(d?.top_customers ?? []).slice(0, 5).map((c, i) => (
                  <div key={c.name} className="flex items-center justify-between" style={{ padding: '12px 20px', borderBottom: i < 4 ? '1px solid #ece8e0' : 'none' }}>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-[#bbb] w-5">{i + 1}</span>
                      <span className="text-sm text-[#555]">{c.name}</span>
                    </div>
                    <span className="text-sm font-bold text-[#1a1a1a]">{fmt(c.revenue)}</span>
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
