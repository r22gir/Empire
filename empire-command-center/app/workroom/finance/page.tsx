"use client";

import { useEffect, useState } from "react";

const API = "http://localhost:8000";

/* ── types ─────────────────────────────────────────────── */

interface DashboardData {
  revenue: { mtd: number; ytd: number };
  expenses: { mtd: number; ytd: number; breakdown_mtd: Record<string, number> };
  net_profit: { mtd: number; ytd: number };
  outstanding: { total: number; count: number };
  accounts_receivable_aging: {
    "0_30": number;
    "31_60": number;
    "61_90": number;
    "90_plus": number;
  };
  recent_invoices: Invoice[];
}

interface Invoice {
  id: string;
  number: string;
  client_name: string;
  amount: number;
  status: string;
  date: string;
}

interface CategoryRow {
  category: string;
  quote_count: number;
  total_value: number;
  item_count: number;
}

interface MonthRow {
  month: string;
  revenue: number;
  expenses: number;
  profit: number;
  revenue_change_pct: number | null;
}

interface ClientRow {
  id: string;
  name: string;
  total_revenue: number;
  quote_count: number;
  actual_revenue: number;
}

interface QuickStats {
  revenue_mtd: number;
  active_jobs: number;
  pending_quotes: number;
  pipeline_value: number;
  in_production: number;
}

/* ── helpers ───────────────────────────────────────────── */

function fmt(n: number): string {
  return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtShort(n: number): string {
  if (n >= 1_000_000) return "$" + (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return "$" + (n / 1_000).toFixed(1) + "K";
  return fmt(n);
}

function pct(part: number, total: number): string {
  if (total === 0) return "0%";
  return ((part / total) * 100).toFixed(1) + "%";
}

const statusColor: Record<string, { bg: string; text: string }> = {
  paid: { bg: "#dcfce7", text: "#166534" },
  partial: { bg: "#fef9c3", text: "#854d0e" },
  overdue: { bg: "#fee2e2", text: "#991b1b" },
  sent: { bg: "#dbeafe", text: "#1e40af" },
  draft: { bg: "#f3f4f6", text: "#374151" },
};

/* ── skeleton ──────────────────────────────────────────── */

function Skeleton({ h = 20, w = "100%" }: { h?: number; w?: string | number }) {
  return (
    <div
      className="animate-pulse rounded"
      style={{ height: h, width: w, backgroundColor: "#e5e5e5" }}
    />
  );
}

function CardSkeleton() {
  return (
    <div className="rounded-lg shadow-sm p-6" style={{ backgroundColor: "#fff" }}>
      <Skeleton h={14} w="50%" />
      <div className="mt-3"><Skeleton h={32} w="60%" /></div>
      <div className="mt-2"><Skeleton h={12} w="40%" /></div>
    </div>
  );
}

/* ── main component ────────────────────────────────────── */

export default function FinanceDashboard() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [categories, setCategories] = useState<{ categories: CategoryRow[]; grand_total: number } | null>(null);
  const [monthly, setMonthly] = useState<{ months: MonthRow[] } | null>(null);
  const [clients, setClients] = useState<{ top_clients: ClientRow[] } | null>(null);
  const [quickStats, setQuickStats] = useState<QuickStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [dashRes, catRes, monthRes, clientRes, statsRes] = await Promise.all([
          fetch(`${API}/api/v1/finance/dashboard`),
          fetch(`${API}/api/v1/finance/revenue-by-category`),
          fetch(`${API}/api/v1/finance/monthly-comparison?months=6`),
          fetch(`${API}/api/v1/finance/revenue-by-client`),
          fetch(`${API}/api/v1/lifecycle/quick-stats`),
        ]);

        if (!dashRes.ok) throw new Error("Failed to load dashboard data");

        const [dashData, catData, monthData, clientData, statsData] = await Promise.all([
          dashRes.json(),
          catRes.ok ? catRes.json() : { categories: [], grand_total: 0 },
          monthRes.ok ? monthRes.json() : { months: [] },
          clientRes.ok ? clientRes.json() : { top_clients: [] },
          statsRes.ok ? statsRes.json() : null,
        ]);

        setDashboard(dashData);
        setCategories(catData);
        setMonthly(monthData);
        setClients(clientData);
        setQuickStats(statsData);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Failed to load data");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  /* ── loading state ────────────────────────────────────── */

  if (loading) {
    return (
      <div className="min-h-screen p-6 md:p-10" style={{ backgroundColor: "#f5f3ef" }}>
        <h1 className="text-2xl font-bold mb-6" style={{ color: "#1a1a2e" }}>
          Financial Dashboard
        </h1>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[1, 2, 3, 4].map((i) => <CardSkeleton key={i} />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="rounded-lg shadow-sm p-6 bg-white">
            <Skeleton h={16} w="40%" />
            <div className="mt-4 space-y-3">
              {[1, 2, 3, 4].map((i) => <Skeleton key={i} h={28} />)}
            </div>
          </div>
          <div className="rounded-lg shadow-sm p-6 bg-white">
            <Skeleton h={16} w="40%" />
            <div className="mt-4 space-y-3">
              {[1, 2, 3, 4, 5, 6].map((i) => <Skeleton key={i} h={28} />)}
            </div>
          </div>
        </div>
      </div>
    );
  }

  /* ── error state ──────────────────────────────────────── */

  if (error || !dashboard) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: "#f5f3ef" }}>
        <div className="rounded-lg shadow-sm p-8 bg-white text-center max-w-md">
          <div className="text-4xl mb-4">!</div>
          <h2 className="text-xl font-bold mb-2" style={{ color: "#1a1a2e" }}>
            Unable to Load Financial Data
          </h2>
          <p className="text-gray-500 mb-4">{error || "No data returned from the server."}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 rounded-lg text-white font-medium"
            style={{ backgroundColor: "#b8960c" }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  /* ── derived values ──────────────────────────────────── */

  const aging = dashboard.accounts_receivable_aging;
  const catMax = categories
    ? Math.max(...categories.categories.map((c) => c.total_value), 1)
    : 1;
  const monthMax = monthly
    ? Math.max(...monthly.months.flatMap((m) => [m.revenue, m.expenses]), 1)
    : 1;

  /* ── render ──────────────────────────────────────────── */

  return (
    <div className="min-h-screen p-6 md:p-10" style={{ backgroundColor: "#f5f3ef", fontFamily: "'Outfit', 'Segoe UI', sans-serif" }}>
      {/* header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold" style={{ color: "#1a1a2e" }}>
            Financial Dashboard
          </h1>
          <p className="text-sm text-gray-500 mt-1">Empire Workroom</p>
        </div>
        {quickStats && (
          <div className="flex gap-4 mt-3 sm:mt-0 text-sm text-gray-600">
            <span>Active Jobs: <strong>{quickStats.active_jobs}</strong></span>
            <span>Pending Quotes: <strong>{quickStats.pending_quotes}</strong></span>
            <span>Pipeline: <strong>{fmtShort(quickStats.pipeline_value)}</strong></span>
          </div>
        )}
      </div>

      {/* ── 1. KPI cards ──────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {/* Revenue */}
        <div className="rounded-lg shadow-sm p-5 bg-white">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Revenue MTD</p>
          <p className="text-2xl font-bold mt-1" style={{ color: dashboard.revenue.mtd >= 0 ? "#166534" : "#991b1b" }}>
            {fmt(dashboard.revenue.mtd)}
          </p>
          <p className="text-xs text-gray-400 mt-1">YTD {fmt(dashboard.revenue.ytd)}</p>
        </div>

        {/* Expenses */}
        <div className="rounded-lg shadow-sm p-5 bg-white">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Expenses MTD</p>
          <p className="text-2xl font-bold mt-1" style={{ color: "#1a1a2e" }}>
            {fmt(dashboard.expenses.mtd)}
          </p>
          <p className="text-xs text-gray-400 mt-1">YTD {fmt(dashboard.expenses.ytd)}</p>
        </div>

        {/* Net Profit */}
        <div className="rounded-lg shadow-sm p-5 bg-white">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Net Profit MTD</p>
          <p className="text-2xl font-bold mt-1" style={{ color: dashboard.net_profit.mtd >= 0 ? "#166534" : "#991b1b" }}>
            {fmt(dashboard.net_profit.mtd)}
          </p>
          <p className="text-xs text-gray-400 mt-1">YTD {fmt(dashboard.net_profit.ytd)}</p>
        </div>

        {/* Outstanding AR */}
        <div className="rounded-lg shadow-sm p-5 bg-white">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Outstanding AR</p>
          <p className="text-2xl font-bold mt-1" style={{ color: dashboard.outstanding.total > 0 ? "#b45309" : "#166534" }}>
            {fmt(dashboard.outstanding.total)}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            {dashboard.outstanding.count} invoice{dashboard.outstanding.count !== 1 ? "s" : ""}
          </p>
        </div>
      </div>

      {/* ── 2. Revenue by Category ────────────────────────── */}
      {categories && categories.categories.length > 0 && (
        <div className="rounded-lg shadow-sm p-6 bg-white mb-6">
          <h2 className="text-lg font-bold mb-4" style={{ color: "#1a1a2e" }}>Revenue by Category</h2>
          <div className="space-y-3">
            {categories.categories.map((cat) => (
              <div key={cat.category}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="font-medium" style={{ color: "#1a1a2e" }}>{cat.category}</span>
                  <span className="text-gray-500">
                    {fmt(cat.total_value)} &middot; {pct(cat.total_value, categories.grand_total)}
                  </span>
                </div>
                <div className="w-full rounded-full h-5" style={{ backgroundColor: "#f0ede6" }}>
                  <div
                    className="h-5 rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.max((cat.total_value / catMax) * 100, 1)}%`,
                      background: "linear-gradient(90deg, #b8960c, #d4af37)",
                    }}
                  />
                </div>
                <p className="text-xs text-gray-400 mt-0.5">
                  {cat.quote_count} quote{cat.quote_count !== 1 ? "s" : ""} &middot; {cat.item_count} item{cat.item_count !== 1 ? "s" : ""}
                </p>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-3 border-t text-sm font-bold" style={{ color: "#1a1a2e" }}>
            Total: {fmt(categories.grand_total)}
          </div>
        </div>
      )}

      {/* ── 3 + 4. Monthly Trend + Top Clients side by side ─ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Monthly Trend */}
        {monthly && monthly.months.length > 0 && (
          <div className="rounded-lg shadow-sm p-6 bg-white">
            <h2 className="text-lg font-bold mb-4" style={{ color: "#1a1a2e" }}>Monthly Trend</h2>
            <div className="space-y-4">
              {monthly.months.map((m) => (
                <div key={m.month}>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="font-medium" style={{ color: "#1a1a2e" }}>{m.month}</span>
                    {m.revenue_change_pct !== null && (
                      <span
                        className="text-xs font-semibold px-2 py-0.5 rounded-full"
                        style={{
                          backgroundColor: m.revenue_change_pct >= 0 ? "#dcfce7" : "#fee2e2",
                          color: m.revenue_change_pct >= 0 ? "#166534" : "#991b1b",
                        }}
                      >
                        {m.revenue_change_pct >= 0 ? "+" : ""}
                        {m.revenue_change_pct.toFixed(1)}%
                      </span>
                    )}
                  </div>
                  {/* revenue bar */}
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs text-gray-400 w-10">Rev</span>
                    <div className="flex-1 rounded-full h-4" style={{ backgroundColor: "#f0ede6" }}>
                      <div
                        className="h-4 rounded-full"
                        style={{
                          width: `${Math.max((m.revenue / monthMax) * 100, 1)}%`,
                          background: "linear-gradient(90deg, #b8960c, #d4af37)",
                        }}
                      />
                    </div>
                    <span className="text-xs font-medium w-20 text-right">{fmtShort(m.revenue)}</span>
                  </div>
                  {/* expense bar */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400 w-10">Exp</span>
                    <div className="flex-1 rounded-full h-4" style={{ backgroundColor: "#f0ede6" }}>
                      <div
                        className="h-4 rounded-full"
                        style={{
                          width: `${Math.max((m.expenses / monthMax) * 100, 1)}%`,
                          backgroundColor: "#9ca3af",
                        }}
                      />
                    </div>
                    <span className="text-xs font-medium w-20 text-right">{fmtShort(m.expenses)}</span>
                  </div>
                  <p className="text-xs mt-1" style={{ color: m.profit >= 0 ? "#166534" : "#991b1b" }}>
                    Profit: {fmt(m.profit)}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Top Clients */}
        {clients && clients.top_clients.length > 0 && (
          <div className="rounded-lg shadow-sm p-6 bg-white">
            <h2 className="text-lg font-bold mb-4" style={{ color: "#1a1a2e" }}>Top Clients</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b" style={{ borderColor: "#e5e5e5" }}>
                    <th className="text-left py-2 font-semibold text-gray-500">#</th>
                    <th className="text-left py-2 font-semibold text-gray-500">Client</th>
                    <th className="text-right py-2 font-semibold text-gray-500">Revenue</th>
                    <th className="text-right py-2 font-semibold text-gray-500">Quotes</th>
                  </tr>
                </thead>
                <tbody>
                  {clients.top_clients.slice(0, 10).map((c, i) => (
                    <tr key={c.id} className="border-b last:border-0" style={{ borderColor: "#f0ede6" }}>
                      <td className="py-2 text-gray-400">{i + 1}</td>
                      <td className="py-2 font-medium" style={{ color: "#1a1a2e" }}>{c.name}</td>
                      <td className="py-2 text-right">{fmt(c.total_revenue)}</td>
                      <td className="py-2 text-right text-gray-500">{c.quote_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* ── 5. AR Aging ───────────────────────────────────── */}
      <div className="rounded-lg shadow-sm p-6 bg-white mb-6">
        <h2 className="text-lg font-bold mb-4" style={{ color: "#1a1a2e" }}>Accounts Receivable Aging</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="rounded-lg p-4 text-center" style={{ backgroundColor: "#dcfce7" }}>
            <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "#166534" }}>0 - 30 days</p>
            <p className="text-xl font-bold mt-1" style={{ color: "#166534" }}>{fmt(aging["0_30"])}</p>
          </div>
          <div className="rounded-lg p-4 text-center" style={{ backgroundColor: "#fef9c3" }}>
            <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "#854d0e" }}>31 - 60 days</p>
            <p className="text-xl font-bold mt-1" style={{ color: "#854d0e" }}>{fmt(aging["31_60"])}</p>
          </div>
          <div className="rounded-lg p-4 text-center" style={{ backgroundColor: "#ffedd5" }}>
            <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "#9a3412" }}>61 - 90 days</p>
            <p className="text-xl font-bold mt-1" style={{ color: "#9a3412" }}>{fmt(aging["61_90"])}</p>
          </div>
          <div className="rounded-lg p-4 text-center" style={{ backgroundColor: "#fee2e2" }}>
            <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "#991b1b" }}>90+ days</p>
            <p className="text-xl font-bold mt-1" style={{ color: "#991b1b" }}>{fmt(aging["90_plus"])}</p>
          </div>
        </div>
      </div>

      {/* ── 6. Recent Invoices ────────────────────────────── */}
      {dashboard.recent_invoices.length > 0 && (
        <div className="rounded-lg shadow-sm p-6 bg-white">
          <h2 className="text-lg font-bold mb-4" style={{ color: "#1a1a2e" }}>Recent Invoices</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b" style={{ borderColor: "#e5e5e5" }}>
                  <th className="text-left py-2 font-semibold text-gray-500">Invoice #</th>
                  <th className="text-left py-2 font-semibold text-gray-500">Client</th>
                  <th className="text-right py-2 font-semibold text-gray-500">Amount</th>
                  <th className="text-center py-2 font-semibold text-gray-500">Status</th>
                  <th className="text-right py-2 font-semibold text-gray-500">Date</th>
                </tr>
              </thead>
              <tbody>
                {dashboard.recent_invoices.map((inv) => {
                  const sc = statusColor[inv.status.toLowerCase()] || statusColor.draft;
                  return (
                    <tr key={inv.id} className="border-b last:border-0" style={{ borderColor: "#f0ede6" }}>
                      <td className="py-2 font-mono text-xs" style={{ color: "#1a1a2e" }}>{inv.number}</td>
                      <td className="py-2 font-medium" style={{ color: "#1a1a2e" }}>{inv.client_name}</td>
                      <td className="py-2 text-right">{fmt(inv.amount)}</td>
                      <td className="py-2 text-center">
                        <span
                          className="text-xs font-semibold px-2 py-0.5 rounded-full inline-block"
                          style={{ backgroundColor: sc.bg, color: sc.text }}
                        >
                          {inv.status}
                        </span>
                      </td>
                      <td className="py-2 text-right text-gray-500">{inv.date}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
