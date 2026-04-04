"use client";

import { useEffect, useState, useCallback } from "react";

const API = "http://localhost:8000";

interface DailyAction {
  type: string;
  icon: string;
  label: string;
  detail: string;
  entity_type: string;
  entity_id: string;
  priority: "urgent" | "high" | "medium";
}

interface DailyActions {
  date: string;
  actions: DailyAction[];
  count: number;
  summary: { urgent: number; high: number; medium: number };
}

interface QuickStats {
  revenue_mtd: number;
  active_jobs: number;
  pending_quotes: number;
  pipeline_value: number;
  in_production: number;
}

interface ProductionBoard {
  total_items: number;
  overdue: number;
  due_soon: number;
}

const PRIORITY_STYLES: Record<string, string> = {
  urgent: "bg-red-100 text-red-700",
  high: "bg-amber-100 text-amber-700",
  medium: "bg-blue-100 text-blue-700",
};

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "GOOD MORNING";
  if (h < 17) return "GOOD AFTERNOON";
  return "GOOD EVENING";
}

function formatDate(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function formatCurrency(n: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);
}

export default function OpsPage() {
  const [dailyActions, setDailyActions] = useState<DailyActions | null>(null);
  const [quickStats, setQuickStats] = useState<QuickStats | null>(null);
  const [productionBoard, setProductionBoard] = useState<ProductionBoard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [actionsRes, statsRes, boardRes] = await Promise.all([
        fetch(`${API}/api/v1/lifecycle/daily-actions`),
        fetch(`${API}/api/v1/lifecycle/quick-stats`),
        fetch(`${API}/api/v1/work-orders/production-board`),
      ]);

      const [actions, stats, board] = await Promise.all([
        actionsRes.ok ? actionsRes.json() : null,
        statsRes.ok ? statsRes.json() : null,
        boardRes.ok ? boardRes.json() : null,
      ]);

      if (actions) setDailyActions(actions);
      if (stats) setQuickStats(stats);
      if (board) setProductionBoard(board);
      setError(null);
    } catch (e) {
      setError("Unable to reach Empire backend");
      console.error("Ops fetch error:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 60_000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  return (
    <div className="min-h-screen" style={{ backgroundColor: "#f5f3ef", fontFamily: "'Outfit', 'Segoe UI', sans-serif" }}>
      {/* Header */}
      <header
        className="px-6 py-10 md:px-12 md:py-14"
        style={{ background: "linear-gradient(135deg, #1a1a2e 0%, #2d2d44 100%)" }}
      >
        <div className="max-w-5xl mx-auto">
          <p className="text-xs font-bold tracking-[0.2em] uppercase mb-2" style={{ color: "#b8960c" }}>
            Empire Workroom — Daily Ops
          </p>
          <h1 className="text-3xl md:text-4xl font-extrabold text-white">
            {getGreeting()}, RG
          </h1>
          <p className="text-white/60 mt-1 text-sm">{formatDate()}</p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 md:px-12 py-8 space-y-8">
        {/* Error banner */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
            {error}
          </div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="text-center py-20 text-sm" style={{ color: "#1a1a2e" }}>
            Loading operations data...
          </div>
        )}

        {/* Quick Stats Bar */}
        {quickStats && (
          <section>
            <h2 className="text-xs font-bold tracking-[0.15em] uppercase mb-3" style={{ color: "#1a1a2e" }}>
              Quick Stats
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {[
                { label: "Revenue MTD", value: formatCurrency(quickStats.revenue_mtd) },
                { label: "Active Jobs", value: String(quickStats.active_jobs) },
                { label: "Pending Quotes", value: String(quickStats.pending_quotes) },
                { label: "Pipeline Value", value: formatCurrency(quickStats.pipeline_value) },
                { label: "In Production", value: String(quickStats.in_production) },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className="bg-white rounded-xl p-4 shadow-sm border border-black/5"
                >
                  <p className="text-[11px] font-semibold tracking-wide uppercase text-gray-400 mb-1">
                    {stat.label}
                  </p>
                  <p className="text-xl font-bold" style={{ color: "#1a1a2e" }}>
                    {stat.value}
                  </p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Today's Priorities */}
        {dailyActions && (
          <section>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-3 gap-2">
              <h2 className="text-xs font-bold tracking-[0.15em] uppercase" style={{ color: "#1a1a2e" }}>
                Today&apos;s Priorities
              </h2>
              <div className="flex gap-2 text-xs font-medium">
                {dailyActions.summary.urgent > 0 && (
                  <span className="bg-red-100 text-red-700 px-2.5 py-0.5 rounded-full">
                    {dailyActions.summary.urgent} urgent
                  </span>
                )}
                {dailyActions.summary.high > 0 && (
                  <span className="bg-amber-100 text-amber-700 px-2.5 py-0.5 rounded-full">
                    {dailyActions.summary.high} high
                  </span>
                )}
                {dailyActions.summary.medium > 0 && (
                  <span className="bg-blue-100 text-blue-700 px-2.5 py-0.5 rounded-full">
                    {dailyActions.summary.medium} medium
                  </span>
                )}
              </div>
            </div>

            {dailyActions.actions.length === 0 ? (
              <div className="bg-white rounded-xl p-8 shadow-sm border border-black/5 text-center text-gray-400 text-sm">
                No action items for today. You&apos;re all clear.
              </div>
            ) : (
              <div className="bg-white rounded-xl shadow-sm border border-black/5 overflow-hidden divide-y divide-gray-100">
                {dailyActions.actions.map((action, i) => (
                  <div
                    key={`${action.entity_type}-${action.entity_id}-${i}`}
                    className={`flex items-center justify-between px-5 py-4 gap-4 ${
                      i % 2 === 1 ? "bg-gray-50/50" : ""
                    }`}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="text-xl flex-shrink-0">{action.icon}</span>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold truncate" style={{ color: "#1a1a2e" }}>
                          {action.label}
                        </p>
                        <p className="text-xs text-gray-500 truncate">{action.detail}</p>
                      </div>
                    </div>
                    <span
                      className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full flex-shrink-0 ${
                        PRIORITY_STYLES[action.priority] || "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {action.priority}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Production Overview */}
        {productionBoard && (
          <section>
            <h2 className="text-xs font-bold tracking-[0.15em] uppercase mb-3" style={{ color: "#1a1a2e" }}>
              Production Overview
            </h2>
            <div className="bg-white rounded-xl shadow-sm border border-black/5 p-5">
              <div className="flex flex-wrap items-center gap-6">
                <div>
                  <p className="text-[11px] font-semibold tracking-wide uppercase text-gray-400 mb-0.5">
                    Total Items
                  </p>
                  <p className="text-2xl font-bold" style={{ color: "#1a1a2e" }}>
                    {productionBoard.total_items}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="bg-red-100 text-red-700 text-xs font-bold px-3 py-1 rounded-full">
                    {productionBoard.overdue} overdue
                  </span>
                  <span className="bg-yellow-100 text-yellow-700 text-xs font-bold px-3 py-1 rounded-full">
                    {productionBoard.due_soon} due soon
                  </span>
                </div>
                <a
                  href="/workroom/production"
                  className="ml-auto text-xs font-semibold hover:underline"
                  style={{ color: "#b8960c" }}
                >
                  View Full Board &rarr;
                </a>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
