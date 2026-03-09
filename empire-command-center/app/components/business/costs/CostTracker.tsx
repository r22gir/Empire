'use client';
import { useState, useEffect, useCallback } from 'react';
import { API } from '../../../lib/api';
import {
  DollarSign, TrendingUp, Zap, Clock, Download, RefreshCw,
  BarChart3, PieChart as PieChartIcon, Activity, AlertTriangle,
} from 'lucide-react';
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

/* ── Types ───────────────────────────────────────────────────── */
interface CostOverview {
  period_days: number;
  total: { input_tokens: number; output_tokens: number; total_tokens: number; cost_usd: number; requests: number };
  today: { input_tokens: number; output_tokens: number; cost_usd: number; requests: number };
  by_model: { model: string; provider: string; input_tokens: number; output_tokens: number; cost: number; requests: number }[];
  daily: { day: string; input_tokens: number; output_tokens: number; cost: number; requests: number }[];
  budget: { monthly_limit: number; monthly_spent: number; percent_used: number; alert: boolean; auto_switch_to_local: boolean; auto_switch_threshold: number };
}

interface Transaction {
  id: number; timestamp: string; model: string; provider: string;
  input_tokens: number; output_tokens: number; cost_usd: number;
  endpoint: string; feature: string; business: string; source: string;
}

interface BreakdownItem { cost: number; requests: number; input_tokens: number; output_tokens: number; [key: string]: unknown }

/* ── Palette ─────────────────────────────────────────────────── */
const COLORS = ['#b8960c', '#7c3aed', '#22c55e', '#ec4899', '#d97706', '#0891b2', '#dc2626', '#a855f7', '#14b8a6', '#f97316'];

/* ── KPI Card ────────────────────────────────────────────────── */
function KPI({ icon: Icon, label, value, sub, alert }: { icon: React.ElementType; label: string; value: string; sub?: string; alert?: boolean }) {
  return (
    <div className={`empire-card flat`} style={{ padding: 20, borderColor: alert ? '#fca5a5' : undefined, background: alert ? '#fef2f2' : undefined }}>
      <div className="kpi-label" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <Icon size={14} className={alert ? 'text-red-500' : 'text-[#b8960c]'} />
        {label}
      </div>
      <div className={`kpi-value ${alert ? 'red' : ''}`}>{value}</div>
      {sub && <div className="text-[11px] text-[#999] mt-1">{sub}</div>}
    </div>
  );
}

/* ── Budget Gauge ────────────────────────────────────────────── */
function BudgetGauge({ spent, limit, percent, alert }: { spent: number; limit: number; percent: number; alert: boolean }) {
  const pct = Math.min(percent, 100);
  const color = pct > 95 ? '#dc2626' : pct > 80 ? '#d97706' : '#22c55e';
  return (
    <div className="empire-card flat" style={{ padding: 20, borderColor: alert ? '#fca5a5' : undefined }}>
      <div className="flex items-center justify-between mb-2">
        <span className="section-label" style={{ marginBottom: 0 }}>Monthly Budget</span>
        {alert && <span className="text-[11px] text-red-500 font-bold flex items-center gap-1"><AlertTriangle size={12} /> Alert</span>}
      </div>
      <div className="flex items-end gap-2 mb-3">
        <span className="kpi-value">${spent.toFixed(2)}</span>
        <span className="text-sm text-[#999] mb-0.5">/ ${limit.toFixed(2)}</span>
      </div>
      <div className="w-full h-3 bg-[#ece8e0] rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <div className="text-[11px] text-[#999] mt-1.5 text-right">{percent.toFixed(1)}% used</div>
    </div>
  );
}

/* ── Main Component ──────────────────────────────────────────── */
export default function CostTracker() {
  const [overview, setOverview] = useState<CostOverview | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [byProvider, setByProvider] = useState<BreakdownItem[]>([]);
  const [byFeature, setByFeature] = useState<BreakdownItem[]>([]);
  const [byBusiness, setByBusiness] = useState<BreakdownItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [trendData, setTrendData] = useState<{ label: string; cost: number; requests: number }[]>([]);
  const [tab, setTab] = useState<'overview' | 'breakdown' | 'log'>('overview');

  const safeFetch = async (url: string) => {
    try {
      const res = await fetch(url);
      if (!res.ok) return null;
      return await res.json();
    } catch { return null; }
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ov, tx, prov, feat, biz] = await Promise.all([
        safeFetch(`${API}/costs/overview?days=30`),
        safeFetch(`${API}/costs/transactions?limit=100`),
        safeFetch(`${API}/costs/by-provider?days=30`),
        safeFetch(`${API}/costs/by-feature?days=30`),
        safeFetch(`${API}/costs/by-business?days=30`),
      ]);
      setOverview(ov);
      setTransactions(ov?.transactions || tx?.transactions || tx || []);
      setByProvider(prov?.by_provider || []);
      setByFeature(feat?.by_feature || []);
      setByBusiness(biz?.by_business || []);
    } catch (e) {
      console.error('Cost data load failed:', e);
    }
    setLoading(false);
  }, []);

  const loadTrend = useCallback(async () => {
    try {
      if (view === 'daily') {
        const r = await safeFetch(`${API}/costs/daily?days=30`);
        setTrendData((r?.daily || []).map((d: any) => ({ label: d.day?.slice(5) || '', cost: d.cost, requests: d.requests })));
      } else if (view === 'weekly') {
        const r = await safeFetch(`${API}/costs/weekly?weeks=12`);
        setTrendData((r?.weekly || []).map((d: any) => ({ label: d.week || '', cost: d.cost, requests: d.requests })));
      } else {
        const r = await safeFetch(`${API}/costs/monthly?months=12`);
        setTrendData((r?.monthly || []).map((d: any) => ({ label: d.month || '', cost: d.cost, requests: d.requests })));
      }
    } catch { /* ignore */ }
  }, [view]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { loadTrend(); }, [loadTrend]);

  const exportCSV = () => {
    if (!transactions.length) return;
    const header = 'timestamp,model,provider,input_tokens,output_tokens,cost_usd,feature,business,source\n';
    const rows = transactions.map(t =>
      `${t.timestamp},${t.model},${t.provider},${t.input_tokens},${t.output_tokens},${t.cost_usd},${t.feature},${t.business},${t.source}`
    ).join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'ai-costs.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  if (loading && !overview) {
    return (
      <div className="flex-1 flex items-center justify-center py-20">
        <RefreshCw className="animate-spin text-[#b8960c] mr-2" size={20} />
        <span className="text-sm text-[#999]">Loading cost data...</span>
      </div>
    );
  }

  if (!overview) {
    return (
      <div className="flex-1 flex items-center justify-center py-20">
        <div className="text-center">
          <DollarSign size={40} className="text-[#d8d3cb] mx-auto mb-3" />
          <div className="text-sm text-[#999]">No cost data available yet</div>
          <div className="text-[11px] text-[#bbb] mt-1">API calls will be tracked automatically</div>
        </div>
      </div>
    );
  }

  const ov = overview;
  const fmt = (n: number) => n >= 1 ? `$${n.toFixed(2)}` : `$${n.toFixed(4)}`;
  const fmtK = (n: number) => n >= 1_000_000 ? `${(n/1_000_000).toFixed(1)}M` : n >= 1000 ? `${(n/1000).toFixed(0)}K` : String(n);

  return (
    <div className="flex-1 overflow-y-auto bg-[#faf9f7]">
      <div className="max-w-5xl mx-auto" style={{ padding: '24px 36px' }}>
        <div className="space-y-5">
          {/* Header */}
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-bold text-[#1a1a1a] flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-[#fdf8eb] flex items-center justify-center">
                <DollarSign size={18} className="text-[#b8960c]" />
              </div>
              AI Cost Tracker
            </h2>
            <div className="flex items-center gap-2">
              <button onClick={load} className="p-2.5 rounded-xl border border-[#ece8e0] bg-[#faf9f7] hover:bg-white text-[#999] hover:text-[#555] transition-colors cursor-pointer" title="Refresh">
                <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
              </button>
              <button onClick={exportCSV} className="p-2.5 rounded-xl border border-[#ece8e0] bg-[#faf9f7] hover:bg-white text-[#999] hover:text-[#555] transition-colors cursor-pointer" title="Export CSV">
                <Download size={15} />
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-1 empire-card flat" style={{ padding: 4 }}>
            {(['overview', 'breakdown', 'log'] as const).map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={`filter-tab ${tab === t ? 'active' : ''}`}
                style={{ flex: 1, textAlign: 'center', textTransform: 'capitalize' }}>
                {t}
              </button>
            ))}
          </div>

          {/* ── Overview Tab ──────────────────────────────────────── */}
          {tab === 'overview' && (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <KPI icon={DollarSign} label="Today" value={fmt(ov.today.cost_usd)} sub={`${ov.today.requests} calls`} />
                <KPI icon={TrendingUp} label="This Month" value={fmt(ov.budget.monthly_spent)} sub={`${ov.budget.percent_used.toFixed(1)}% of budget`} alert={ov.budget.alert} />
                <KPI icon={Zap} label="30-Day Total" value={fmt(ov.total.cost_usd)} sub={`${fmtK(ov.total.total_tokens)} tokens`} />
                <KPI icon={Clock} label="30-Day Calls" value={String(ov.total.requests)} sub={`Avg ${ov.total.requests > 0 ? fmt(ov.total.cost_usd / ov.total.requests) : '$0'}/call`} />
              </div>

              <BudgetGauge spent={ov.budget.monthly_spent} limit={ov.budget.monthly_limit} percent={ov.budget.percent_used} alert={ov.budget.alert} />

              {/* Trend Chart */}
              <div className="empire-card flat" style={{ padding: 20 }}>
                <div className="flex items-center justify-between mb-4">
                  <span className="section-label" style={{ marginBottom: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Activity size={15} className="text-[#b8960c]" /> Cost Trend
                  </span>
                  <div className="flex gap-1 bg-[#faf9f7] rounded-xl p-1">
                    {(['daily', 'weekly', 'monthly'] as const).map(v => (
                      <button key={v} onClick={() => setView(v)}
                        className={`filter-tab ${view === v ? 'active' : ''}`}
                        style={{ textTransform: 'capitalize', fontSize: 10, padding: '4px 10px' }}>
                        {v}
                      </button>
                    ))}
                  </div>
                </div>
                {trendData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={trendData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#ece8e0" />
                      <XAxis dataKey="label" tick={{ fill: '#999', fontSize: 10 }} />
                      <YAxis tick={{ fill: '#999', fontSize: 10 }} tickFormatter={v => `$${v}`} />
                      <Tooltip contentStyle={{ background: '#faf9f7', border: '1px solid #ece8e0', borderRadius: 14, boxShadow: '0 4px 12px rgba(0,0,0,0.06)' }}
                        formatter={(v: unknown) => [`$${Number(v).toFixed(4)}`, 'Cost']} />
                      <Bar dataKey="cost" fill="#b8960c" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="text-center py-12 text-sm text-[#bbb]">No trend data yet</div>
                )}
              </div>

              {/* Model Breakdown */}
              <div className="empire-card flat" style={{ padding: 0, overflow: 'hidden' }}>
                <div style={{ padding: '16px 20px 0 20px' }}>
                  <span className="section-label" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <BarChart3 size={15} className="text-[#7c3aed]" /> By Model
                  </span>
                </div>
                <div className="overflow-x-auto">
                  <table className="empire-table">
                    <thead><tr>
                      <th className="text-left">Model</th>
                      <th className="text-left">Provider</th>
                      <th className="text-right">Calls</th>
                      <th className="text-right">Tokens</th>
                      <th className="text-right">Cost</th>
                    </tr></thead>
                    <tbody>
                      {ov.by_model.map((m, i) => (
                        <tr key={i}>
                          <td className="font-mono font-medium text-[#1a1a1a]">{m.model}</td>
                          <td>{m.provider}</td>
                          <td className="text-right">{m.requests}</td>
                          <td className="text-right">{fmtK(m.input_tokens + m.output_tokens)}</td>
                          <td className="text-right font-bold text-[#b8960c]">{fmt(m.cost)}</td>
                        </tr>
                      ))}
                      {ov.by_model.length === 0 && (
                        <tr><td colSpan={5} className="text-center py-8 text-[#bbb]">No model data yet</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {/* ── Breakdown Tab ─────────────────────────────────────── */}
          {tab === 'breakdown' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <BreakdownCard title="By Provider" icon={PieChartIcon} data={byProvider} nameKey="provider" fmt={fmt} />
              <BreakdownCard title="By Feature" icon={Zap} data={byFeature} nameKey="feature" fmt={fmt} />
              <BreakdownCard title="By Business" icon={BarChart3} data={byBusiness} nameKey="business" fmt={fmt} />
            </div>
          )}

          {/* ── Transaction Log Tab ───────────────────────────────── */}
          {tab === 'log' && (
            <div className="empire-card flat" style={{ padding: 0, overflow: 'hidden' }}>
              <div className="flex items-center justify-between" style={{ padding: '16px 20px' }}>
                <span className="section-label" style={{ marginBottom: 0 }}>Recent Transactions ({transactions.length})</span>
                <button onClick={exportCSV} className="text-xs text-[#b8960c] hover:text-[#96750a] flex items-center gap-1 font-bold cursor-pointer">
                  <Download size={12} /> CSV
                </button>
              </div>
              <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                <table className="empire-table">
                  <thead className="sticky top-0 bg-[#faf9f7]"><tr>
                    <th className="text-left">Time</th>
                    <th className="text-left">Model</th>
                    <th className="text-left">Feature</th>
                    <th className="text-left">Business</th>
                    <th className="text-right">In</th>
                    <th className="text-right">Out</th>
                    <th className="text-right">Cost</th>
                  </tr></thead>
                  <tbody>
                    {transactions.map(t => (
                      <tr key={t.id}>
                        <td className="whitespace-nowrap font-mono text-[#999]" suppressHydrationWarning>{t.timestamp?.slice(5, 16)}</td>
                        <td className="font-mono font-medium text-[#1a1a1a]">{t.model}</td>
                        <td>{t.feature}</td>
                        <td>{t.business}</td>
                        <td className="text-right">{fmtK(t.input_tokens)}</td>
                        <td className="text-right">{fmtK(t.output_tokens)}</td>
                        <td className="text-right font-bold text-[#b8960c]">{t.cost_usd > 0 ? fmt(t.cost_usd) : '-'}</td>
                      </tr>
                    ))}
                    {transactions.length === 0 && (
                      <tr><td colSpan={7} className="text-center py-12 text-[#bbb]">No transactions yet</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Breakdown Card ──────────────────────────────────────────── */
function BreakdownCard({ title, icon: Icon, data, nameKey, fmt }: {
  title: string; icon: React.ElementType; data: BreakdownItem[]; nameKey: string; fmt: (n: number) => string;
}) {
  return (
    <div className="empire-card flat" style={{ padding: 20 }}>
      <span className="section-label" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Icon size={15} className="text-[#b8960c]" /> {title}
      </span>
      {data.length > 0 ? (
        <>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={data} dataKey="cost" nameKey={nameKey} cx="50%" cy="50%" outerRadius={65} strokeWidth={2} stroke="#faf9f7">
                {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip formatter={(v: unknown) => fmt(Number(v))} contentStyle={{ background: '#faf9f7', border: '1px solid #ece8e0', borderRadius: 14 }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-2 mt-3">
            {data.map((p, i) => (
              <div key={i} className="flex justify-between text-xs text-[#555]">
                <span className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                  {(p as Record<string, unknown>)[nameKey] as string}
                </span>
                <span className="font-bold text-[#b8960c]">{fmt(p.cost)}</span>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="text-center py-12 text-sm text-[#bbb]">No data yet</div>
      )}
    </div>
  );
}
