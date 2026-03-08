'use client';
import { useState, useEffect, useCallback } from 'react';
import { apiFetch } from '@/lib/api';
import {
  DollarSign, TrendingUp, Zap, Clock, Download, RefreshCw,
  BarChart3, PieChart as PieChartIcon, Activity, AlertTriangle,
} from 'lucide-react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
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
const COLORS = ['#D4AF37', '#8B5CF6', '#22C55E', '#EC4899', '#F59E0B', '#06B6D4', '#EF4444', '#A855F7', '#14B8A6', '#F97316'];

/* ── KPI Card ────────────────────────────────────────────────── */
function KPI({ icon: Icon, label, value, sub, alert }: { icon: React.ElementType; label: string; value: string; sub?: string; alert?: boolean }) {
  return (
    <div className={`rounded-lg border p-4 ${alert ? 'border-red-500/50 bg-red-500/5' : 'border-white/10 bg-white/[0.03]'}`}>
      <div className="flex items-center gap-2 text-xs text-white/50 mb-1">
        <Icon size={14} className={alert ? 'text-red-400' : 'text-amber-400'} />
        {label}
      </div>
      <div className={`text-2xl font-bold ${alert ? 'text-red-400' : 'text-white'}`}>{value}</div>
      {sub && <div className="text-xs text-white/40 mt-1">{sub}</div>}
    </div>
  );
}

/* ── Budget Gauge ────────────────────────────────────────────── */
function BudgetGauge({ spent, limit, percent, alert }: { spent: number; limit: number; percent: number; alert: boolean }) {
  const pct = Math.min(percent, 100);
  const color = pct > 95 ? '#EF4444' : pct > 80 ? '#F59E0B' : '#22C55E';
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-white/50">Monthly Budget</span>
        {alert && <span className="text-xs text-red-400 flex items-center gap-1"><AlertTriangle size={12} /> Alert</span>}
      </div>
      <div className="flex items-end gap-2 mb-3">
        <span className="text-2xl font-bold text-white">${spent.toFixed(2)}</span>
        <span className="text-sm text-white/40 mb-0.5">/ ${limit.toFixed(2)}</span>
      </div>
      <div className="w-full h-3 bg-white/10 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <div className="text-xs text-white/40 mt-1 text-right">{percent.toFixed(1)}% used</div>
    </div>
  );
}

/* ── Main Component ──────────────────────────────────────────── */
export default function CostTrackerDesk() {
  const [overview, setOverview] = useState<CostOverview | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [byProvider, setByProvider] = useState<BreakdownItem[]>([]);
  const [byFeature, setByFeature] = useState<BreakdownItem[]>([]);
  const [byBusiness, setByBusiness] = useState<BreakdownItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [trendData, setTrendData] = useState<{ label: string; cost: number; requests: number }[]>([]);
  const [tab, setTab] = useState<'overview' | 'breakdown' | 'log'>('overview');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ov, tx, prov, feat, biz] = await Promise.all([
        apiFetch<CostOverview>('/costs/overview?days=30'),
        apiFetch<{ transactions: Transaction[] }>('/costs/transactions?limit=100'),
        apiFetch<{ by_provider: BreakdownItem[] }>('/costs/by-provider?days=30'),
        apiFetch<{ by_feature: BreakdownItem[] }>('/costs/by-feature?days=30'),
        apiFetch<{ by_business: BreakdownItem[] }>('/costs/by-business?days=30'),
      ]);
      setOverview(ov);
      setTransactions(tx.transactions);
      setByProvider(prov.by_provider);
      setByFeature(feat.by_feature);
      setByBusiness(biz.by_business);
    } catch (e) {
      console.error('Cost data load failed:', e);
    }
    setLoading(false);
  }, []);

  const loadTrend = useCallback(async () => {
    try {
      if (view === 'daily') {
        const r = await apiFetch<{ daily: { day: string; cost: number; requests: number }[] }>('/costs/daily?days=30');
        setTrendData(r.daily.map(d => ({ label: d.day.slice(5), cost: d.cost, requests: d.requests })));
      } else if (view === 'weekly') {
        const r = await apiFetch<{ weekly: { week: string; cost: number; requests: number }[] }>('/costs/weekly?weeks=12');
        setTrendData(r.weekly.map(d => ({ label: d.week, cost: d.cost, requests: d.requests })));
      } else {
        const r = await apiFetch<{ monthly: { month: string; cost: number; requests: number }[] }>('/costs/monthly?months=12');
        setTrendData(r.monthly.map(d => ({ label: d.month, cost: d.cost, requests: d.requests })));
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
    return <div className="flex items-center justify-center h-full text-white/40"><RefreshCw className="animate-spin mr-2" size={18} /> Loading cost data...</div>;
  }

  const ov = overview!;
  const fmt = (n: number) => n >= 1 ? `$${n.toFixed(2)}` : `$${n.toFixed(4)}`;
  const fmtK = (n: number) => n >= 1_000_000 ? `${(n/1_000_000).toFixed(1)}M` : n >= 1000 ? `${(n/1000).toFixed(0)}K` : String(n);

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4 gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <DollarSign size={20} className="text-amber-400" /> AI Cost Tracker
        </h2>
        <div className="flex items-center gap-2">
          <button onClick={load} className="p-2 rounded hover:bg-white/10 text-white/60" title="Refresh">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
          <button onClick={exportCSV} className="p-2 rounded hover:bg-white/10 text-white/60" title="Export CSV">
            <Download size={16} />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-white/5 rounded-lg p-1">
        {(['overview', 'breakdown', 'log'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`flex-1 py-1.5 px-3 rounded text-sm capitalize transition ${tab === t ? 'bg-amber-500/20 text-amber-400' : 'text-white/50 hover:text-white/70'}`}>
            {t}
          </button>
        ))}
      </div>

      {/* ── Overview Tab ──────────────────────────────────────── */}
      {tab === 'overview' && (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <KPI icon={DollarSign} label="Today" value={fmt(ov.today.cost_usd)} sub={`${ov.today.requests} calls`} />
            <KPI icon={TrendingUp} label="This Month" value={fmt(ov.budget.monthly_spent)} sub={`${ov.budget.percent_used.toFixed(1)}% of budget`} alert={ov.budget.alert} />
            <KPI icon={Zap} label="30-Day Total" value={fmt(ov.total.cost_usd)} sub={`${fmtK(ov.total.total_tokens)} tokens`} />
            <KPI icon={Clock} label="30-Day Calls" value={String(ov.total.requests)} sub={`Avg ${ov.total.requests > 0 ? fmt(ov.total.cost_usd / ov.total.requests) : '$0'}/call`} />
          </div>

          {/* Budget Gauge */}
          <BudgetGauge spent={ov.budget.monthly_spent} limit={ov.budget.monthly_limit} percent={ov.budget.percent_used} alert={ov.budget.alert} />

          {/* Trend Chart */}
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-white/60 flex items-center gap-1"><Activity size={14} /> Cost Trend</span>
              <div className="flex gap-1">
                {(['daily', 'weekly', 'monthly'] as const).map(v => (
                  <button key={v} onClick={() => setView(v)}
                    className={`px-2 py-0.5 rounded text-xs capitalize ${view === v ? 'bg-amber-500/20 text-amber-400' : 'text-white/40 hover:text-white/60'}`}>
                    {v}
                  </button>
                ))}
              </div>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="label" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }} />
                <YAxis tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 11 }} tickFormatter={v => `$${v}`} />
                <Tooltip contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
                  labelStyle={{ color: '#fff' }} formatter={(v: number) => [`$${v.toFixed(4)}`, 'Cost']} />
                <Bar dataKey="cost" fill="#D4AF37" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Model Breakdown Table */}
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
            <span className="text-sm text-white/60 flex items-center gap-1 mb-3"><BarChart3 size={14} /> By Model</span>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead><tr className="text-white/40 border-b border-white/10">
                  <th className="text-left py-2 pr-3">Model</th>
                  <th className="text-left py-2 pr-3">Provider</th>
                  <th className="text-right py-2 pr-3">Calls</th>
                  <th className="text-right py-2 pr-3">Tokens</th>
                  <th className="text-right py-2">Cost</th>
                </tr></thead>
                <tbody>
                  {ov.by_model.map((m, i) => (
                    <tr key={i} className="border-b border-white/5 text-white/70">
                      <td className="py-2 pr-3 font-mono">{m.model}</td>
                      <td className="py-2 pr-3">{m.provider}</td>
                      <td className="py-2 pr-3 text-right">{m.requests}</td>
                      <td className="py-2 pr-3 text-right">{fmtK(m.input_tokens + m.output_tokens)}</td>
                      <td className="py-2 text-right text-amber-400">{fmt(m.cost)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* ── Breakdown Tab ─────────────────────────────────────── */}
      {tab === 'breakdown' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* By Provider */}
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
            <span className="text-sm text-white/60 flex items-center gap-1 mb-3"><PieChartIcon size={14} /> By Provider</span>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={byProvider} dataKey="cost" nameKey="provider" cx="50%" cy="50%" outerRadius={70} label={({ name, percent }) => `${name} ${(percent*100).toFixed(0)}%`}>
                  {byProvider.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v: number) => fmt(v)} />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-1 mt-2">
              {byProvider.map((p, i) => (
                <div key={i} className="flex justify-between text-xs text-white/60">
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />{(p as Record<string, unknown>).provider as string}</span>
                  <span className="text-amber-400">{fmt(p.cost)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* By Feature */}
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
            <span className="text-sm text-white/60 flex items-center gap-1 mb-3"><Zap size={14} /> By Feature</span>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={byFeature} dataKey="cost" nameKey="feature" cx="50%" cy="50%" outerRadius={70} label={({ name, percent }) => `${name} ${(percent*100).toFixed(0)}%`}>
                  {byFeature.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v: number) => fmt(v)} />
              </PieChart>
            </ResponsiveContainer>
            <div className="space-y-1 mt-2">
              {byFeature.map((f, i) => (
                <div key={i} className="flex justify-between text-xs text-white/60">
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />{(f as Record<string, unknown>).feature as string}</span>
                  <span className="text-amber-400">{fmt(f.cost)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* By Business */}
          <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
            <span className="text-sm text-white/60 flex items-center gap-1 mb-3"><BarChart3 size={14} /> By Business</span>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={byBusiness} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis type="number" tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }} tickFormatter={v => `$${v}`} />
                <YAxis type="category" dataKey="business" tick={{ fill: 'rgba(255,255,255,0.5)', fontSize: 10 }} width={80} />
                <Tooltip formatter={(v: number) => fmt(v)} contentStyle={{ background: '#1a1a2e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }} />
                <Bar dataKey="cost" fill="#8B5CF6" radius={[0,4,4,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* ── Transaction Log Tab ───────────────────────────────── */}
      {tab === 'log' && (
        <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm text-white/60">Recent Transactions ({transactions.length})</span>
            <button onClick={exportCSV} className="text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1">
              <Download size={12} /> CSV
            </button>
          </div>
          <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-[#0a0a1a]"><tr className="text-white/40 border-b border-white/10">
                <th className="text-left py-2 pr-2">Time</th>
                <th className="text-left py-2 pr-2">Model</th>
                <th className="text-left py-2 pr-2">Feature</th>
                <th className="text-left py-2 pr-2">Business</th>
                <th className="text-right py-2 pr-2">In</th>
                <th className="text-right py-2 pr-2">Out</th>
                <th className="text-right py-2">Cost</th>
              </tr></thead>
              <tbody>
                {transactions.map(t => (
                  <tr key={t.id} className="border-b border-white/5 text-white/60 hover:bg-white/5">
                    <td className="py-1.5 pr-2 whitespace-nowrap">{t.timestamp?.slice(5, 16)}</td>
                    <td className="py-1.5 pr-2 font-mono text-white/70">{t.model}</td>
                    <td className="py-1.5 pr-2">{t.feature}</td>
                    <td className="py-1.5 pr-2">{t.business}</td>
                    <td className="py-1.5 pr-2 text-right">{fmtK(t.input_tokens)}</td>
                    <td className="py-1.5 pr-2 text-right">{fmtK(t.output_tokens)}</td>
                    <td className="py-1.5 text-right text-amber-400">{t.cost_usd > 0 ? fmt(t.cost_usd) : '-'}</td>
                  </tr>
                ))}
                {transactions.length === 0 && (
                  <tr><td colSpan={7} className="text-center py-8 text-white/30">No transactions yet</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
