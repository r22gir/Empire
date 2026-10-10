'use client';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { API } from '../../../lib/api';
import {
  DollarSign, TrendingUp, Zap, Clock, Download, RefreshCw,
  BarChart3, PieChart as PieChartIcon, Activity, AlertTriangle,
  ExternalLink, Edit3, Info, Shield, ShieldAlert,
} from 'lucide-react';
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine, Legend,
} from 'recharts';

/* ── Types ───────────────────────────────────────────────────── */
export interface FreeTierData {
  provider: string;
  model_pattern: string;
  cost_basis: string;
  rpm: number;
  rpd: number;
  tpd: number;
  reset_tz: string;
  source_url: string;
  verified_date: string;
  use_cases: string;
  not_for: string;
  window_date?: string;
  requests_day?: number;
  tokens_day?: number;
  requests_minute?: number;
  rpm_limit?: number;
  rpd_limit?: number;
  tpd_limit?: number;
  percent_used?: number;
  status?: string;
  warn?: boolean;
  exhausted?: boolean;
}

interface CostOverview {
  period_days: number;
  total: { input_tokens: number; output_tokens: number; total_tokens: number; cost_usd: number; requests: number };
  today: { input_tokens: number; output_tokens: number; cost_usd: number; requests: number };
  by_model: {
    model: string; provider: string; input_tokens: number; output_tokens: number; cost: number; requests: number;
    estimated_cost?: number; provider_reported_cost?: number; provider_reported_rows?: number; estimated_rows?: number;
  }[];
  daily: { day: string; input_tokens: number; output_tokens: number; cost: number; requests: number }[];
  budget: { monthly_limit: number; monthly_spent: number; percent_used: number; alert: boolean; auto_switch_to_local: boolean; auto_switch_threshold: number };
  token_sources?: { provider_reported: number; estimated: number; unknown: number };
}

interface Transaction {
  id: number; timestamp: string; model: string; provider: string;
  input_tokens: number; output_tokens: number; cost_usd: number;
  endpoint: string; feature: string; business: string; source: string;
  token_source?: string;
  estimated_cost?: number;
  provider_reported_cost?: number;
  source_module?: string;
  lane?: string;
  status?: string;
  http_status?: number;
  request_id?: string;
  attempt_id?: string;
  is_legacy?: number;
}

interface BreakdownItem { cost: number; requests: number; input_tokens: number; output_tokens: number; [key: string]: unknown }

interface BleedAlert {
  kind: string;
  source_module: string;
  provider_model: string;
  lane: string;
  count: number;
  last_seen: string;
  recommended_action: string;
}

/* ── Model Tier Map ──────────────────────────────────────────── */
const MODEL_TIERS: Record<string, { tier: string; color: string; bg: string }> = {
  // Free tier models ($0.00)
  'gemini': { tier: 'FREE', color: '#16a34a', bg: '#f0fdf4' },
  'gemini-2.5-flash': { tier: 'FREE', color: '#16a34a', bg: '#f0fdf4' },
  'gemini-2.5-flash-lite': { tier: 'FREE', color: '#16a34a', bg: '#f0fdf4' },
  'gemini-3.5-flash': { tier: 'FREE', color: '#16a34a', bg: '#f0fdf4' },
  'openai/gpt-oss-120b': { tier: 'FREE', color: '#16a34a', bg: '#f0fdf4' },
  'openai/gpt-oss-20b': { tier: 'FREE', color: '#16a34a', bg: '#f0fdf4' },
  'qwen/qwen3.8-27b': { tier: 'FREE', color: '#16a34a', bg: '#f0fdf4' },
  'gpt-oss': { tier: 'FREE', color: '#16a34a', bg: '#f0fdf4' },
  'qwen3.8': { tier: 'FREE', color: '#16a34a', bg: '#f0fdf4' },
  'nvidia/nemotron-3-super-120b-a12b:free': { tier: 'FREE', color: '#16a34a', bg: '#f0fdf4' },
  'google/gemma-4-31b-it:free': { tier: 'FREE', color: '#16a34a', bg: '#f0fdf4' },
  'cohere/north-mini-code:free': { tier: 'FREE', color: '#16a34a', bg: '#f0fdf4' },
  'openrouter/free': { tier: 'FREE', color: '#16a34a', bg: '#f0fdf4' },
  ':free': { tier: 'FREE', color: '#16a34a', bg: '#f0fdf4' },
  'ollama': { tier: 'FREE', color: '#16a34a', bg: '#f0fdf4' },
  'openclaw': { tier: 'FREE', color: '#16a34a', bg: '#f0fdf4' },

  // Cheap models ($0.10 - $0.80 / 1M tokens) - Groq Llama 3.3 fixed as Cheap
  'gpt-4.1-nano': { tier: 'CHEAP', color: '#2563eb', bg: '#eff6ff' },
  'llama-3.3-70b-versatile': { tier: 'CHEAP', color: '#2563eb', bg: '#eff6ff' },
  'groq-llama-3.3-70b': { tier: 'CHEAP', color: '#2563eb', bg: '#eff6ff' },
  'groq': { tier: 'CHEAP (Llama 3.3)', color: '#2563eb', bg: '#eff6ff' },
  'llama-3.1-8b-instant': { tier: 'CHEAP', color: '#2563eb', bg: '#eff6ff' },
  'llama': { tier: 'CHEAP', color: '#2563eb', bg: '#eff6ff' },
  'deepseek-v4-flash': { tier: 'CHEAP', color: '#2563eb', bg: '#eff6ff' },

  // Moderate models ($0.15 - $3.00 / 1M tokens)
  'gpt-4o-mini': { tier: 'MODERATE', color: '#d97706', bg: '#fffbeb' },
  'claude-sonnet-4-6': { tier: 'MODERATE', color: '#d97706', bg: '#fffbeb' },
  'gpt-4.1-mini': { tier: 'MODERATE', color: '#d97706', bg: '#fffbeb' },
  'deepseek-chat': { tier: 'MODERATE', color: '#d97706', bg: '#fffbeb' },
  'deepseek-v4-pro': { tier: 'MODERATE', color: '#d97706', bg: '#fffbeb' },
  'qwen-plus': { tier: 'MODERATE', color: '#d97706', bg: '#fffbeb' },

  // Premium models (>= $5.00 / 1M tokens)
  'grok': { tier: 'PREMIUM', color: '#dc2626', bg: '#fef2f2' },
  'grok-image-gen': { tier: 'PREMIUM', color: '#dc2626', bg: '#fef2f2' },
  'claude-opus-4-6': { tier: 'PREMIUM', color: '#dc2626', bg: '#fef2f2' },
  'gpt-4o': { tier: 'PREMIUM', color: '#dc2626', bg: '#fef2f2' },
  'qwen-max': { tier: 'PREMIUM', color: '#dc2626', bg: '#fef2f2' },
};

/* ── Provider Links ──────────────────────────────────────────── */
const PROVIDER_LINKS: Record<string, string> = {
  'grok': 'https://console.x.ai',
  'grok-image-gen': 'https://console.x.ai',
  'claude-opus-4-6': 'https://console.anthropic.com/settings/billing',
  'claude-sonnet-4-6': 'https://console.anthropic.com/settings/billing',
  'groq': 'https://console.groq.com/settings/billing',
  'llama': 'https://console.groq.com/settings/billing',
  'gemini': 'https://aistudio.google.com/apikey',
  'gemini-2.5-flash': 'https://aistudio.google.com/apikey',
  'gpt-4o': 'https://platform.openai.com/usage',
  'gpt-4o-mini': 'https://platform.openai.com/usage',
  'gpt-4.1-nano': 'https://platform.openai.com/usage',
  'gpt-4.1-mini': 'https://platform.openai.com/usage',
};

const PROVIDER_DASHBOARD_LIST = [
  { name: 'Anthropic (Claude)', url: 'https://console.anthropic.com/settings/billing', color: '#d97706' },
  { name: 'xAI (Grok)', url: 'https://console.x.ai', color: '#dc2626' },
  { name: 'Groq', url: 'https://console.groq.com/settings/billing', color: '#2563eb' },
  { name: 'Google (Gemini)', url: 'https://aistudio.google.com/apikey', color: '#16a34a' },
  { name: 'OpenAI', url: 'https://platform.openai.com/usage', color: '#a855f7' },
];

/* ── Helpers ─────────────────────────────────────────────────── */
function getTierForModel(model: string): { tier: string; color: string; bg: string } {
  const lower = model.toLowerCase();
  if (lower.endsWith(':free')) return { tier: 'FREE', color: '#16a34a', bg: '#f0fdf4' };
  if (lower.includes('gpt-oss') || lower.includes('qwen3.8')) return { tier: 'FREE', color: '#16a34a', bg: '#f0fdf4' };
  if (lower.includes('gemini-2.5-flash') || lower.includes('gemini-3.5-flash')) return { tier: 'FREE', color: '#16a34a', bg: '#f0fdf4' };
  if (MODEL_TIERS[lower]) return MODEL_TIERS[lower];
  for (const [key, val] of Object.entries(MODEL_TIERS)) {
    if (lower.includes(key)) return val;
  }
  return { tier: 'UNKNOWN', color: '#6b7280', bg: '#f9fafb' };
}

function getTierCategory(model: string): 'free' | 'cheap' | 'moderate' | 'premium' {
  const t = getTierForModel(model).tier;
  if (t === 'FREE') return 'free';
  if (t.startsWith('CHEAP')) return 'cheap';
  if (t === 'MODERATE') return 'moderate';
  return 'premium';
}

/* ── Palette ─────────────────────────────────────────────────── */
const COLORS = ['#b8960c', '#7c3aed', '#22c55e', '#ec4899', '#d97706', '#0891b2', '#dc2626', '#a855f7', '#14b8a6', '#f97316'];

const TIER_COLORS: Record<string, string> = { free: '#16a34a', cheap: '#2563eb', moderate: '#d97706', premium: '#dc2626' };

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

/* ── Tier Badge ──────────────────────────────────────────────── */
function TierBadge({ model }: { model: string }) {
  const info = getTierForModel(model);
  return (
    <span
      style={{
        display: 'inline-block',
        fontSize: 9,
        fontWeight: 700,
        padding: '2px 7px',
        borderRadius: 9999,
        color: info.color,
        backgroundColor: info.bg,
        border: `1px solid ${info.color}33`,
        lineHeight: '14px',
        letterSpacing: '0.03em',
      }}
    >
      {info.tier}
    </span>
  );
}

/* ── Budget Gauge (enhanced) ─────────────────────────────────── */
function BudgetGauge({
  spent, limit, percent, alert, trendData, onEditBudget,
}: {
  spent: number; limit: number; percent: number; alert: boolean;
  trendData: { label: string; cost: number; requests: number }[];
  onEditBudget: () => void;
}) {
  const pct = Math.min(percent, 100);
  const color = pct > 95 ? '#dc2626' : pct > 80 ? '#d97706' : '#22c55e';

  // Calculate pre/post tiering averages (cutoff: 03-22)
  const cutoffLabel = '03-22';
  const preDays = trendData.filter(d => d.label < cutoffLabel);
  const postDays = trendData.filter(d => d.label >= cutoffLabel);
  const preAvg = preDays.length > 0 ? preDays.reduce((s, d) => s + d.cost, 0) / preDays.length : 0;
  const postAvg = postDays.length > 0 ? postDays.reduce((s, d) => s + d.cost, 0) / postDays.length : 0;

  // Use last 3 days for projection
  const last3 = trendData.slice(-3);
  const avgDaily = last3.length > 0 ? last3.reduce((s, d) => s + d.cost, 0) / last3.length : 0;
  const projected = avgDaily * 30;

  return (
    <div className="empire-card flat" style={{ padding: 20, borderColor: alert ? '#fca5a5' : undefined }}>
      <div className="flex items-center justify-between mb-2">
        <span className="section-label" style={{ marginBottom: 0, display: 'flex', alignItems: 'center', gap: 6 }}>
          Monthly Budget
          <button
            onClick={onEditBudget}
            className="text-[#999] hover:text-[#b8960c] transition-colors cursor-pointer"
            title="Edit budget"
          >
            <Edit3 size={13} />
          </button>
        </span>
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

      {/* Projection line */}
      {trendData.length > 0 && (
        <div className="mt-3 pt-3 border-t border-[#ece8e0] text-[11px] text-[#777] flex flex-wrap gap-x-4 gap-y-1">
          {preDays.length > 0 && <span>Pre-tiering avg: <b>${preAvg.toFixed(4)}</b>/day</span>}
          {postDays.length > 0 && <span>Post-tiering avg: <b>${postAvg.toFixed(4)}</b>/day</span>}
          <span>Projected monthly: <b>${projected.toFixed(2)}</b></span>
        </div>
      )}
    </div>
  );
}

/* ── Budget Edit Modal ───────────────────────────────────────── */
function BudgetEditModal({ current, onSave, onClose }: { current: number; onSave: (v: number) => void; onClose: () => void }) {
  const [val, setVal] = useState(String(current));
  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'rgba(0,0,0,0.35)',
      }}
      onClick={onClose}
    >
      <div
        className="empire-card flat"
        style={{ padding: 24, width: 340, background: '#fff', borderRadius: 16, boxShadow: '0 8px 32px rgba(0,0,0,0.15)' }}
        onClick={e => e.stopPropagation()}
      >
        <div className="text-sm font-bold text-[#1a1a1a] mb-3">Set Monthly Budget</div>
        <div className="flex items-center gap-2 mb-4">
          <span className="text-lg font-bold text-[#b8960c]">$</span>
          <input
            type="number"
            min={0}
            step={1}
            value={val}
            onChange={e => setVal(e.target.value)}
            className="flex-1 border border-[#ece8e0] rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-[#b8960c]"
            autoFocus
          />
        </div>
        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-4 py-1.5 text-xs rounded-xl border border-[#ece8e0] bg-white hover:bg-[#faf9f7] cursor-pointer">Cancel</button>
          <button
            onClick={() => { const n = parseFloat(val); if (!isNaN(n) && n > 0) onSave(n); }}
            className="px-4 py-1.5 text-xs rounded-xl bg-[#b8960c] text-white hover:bg-[#96750a] font-bold cursor-pointer"
          >Save</button>
        </div>
      </div>
    </div>
  );
}

/* ── Default Free Tier Fallback ──────────────────────────────── */
const DEFAULT_FREE_TIERS: FreeTierData[] = [
  {
    provider: 'groq',
    model_pattern: 'openai/gpt-oss-120b',
    cost_basis: 'free_tier',
    rpm: 30,
    rpd: 1000,
    tpd: 1000000,
    reset_tz: 'America/Los_Angeles',
    source_url: 'https://console.groq.com/docs/rate-limits',
    verified_date: '2026-10-10',
    use_cases: 'General reasoning, draft coding, analysis',
    not_for: 'Client quotes, invoices, customer messages',
    percent_used: 0,
    status: 'normal',
  },
  {
    provider: 'groq',
    model_pattern: 'openai/gpt-oss-20b',
    cost_basis: 'free_tier',
    rpm: 30,
    rpd: 1000,
    tpd: 1000000,
    reset_tz: 'America/Los_Angeles',
    source_url: 'https://console.groq.com/docs/rate-limits',
    verified_date: '2026-10-10',
    use_cases: 'Fast extraction, summaries, parsing',
    not_for: 'Client quotes, invoices, customer messages',
    percent_used: 0,
    status: 'normal',
  },
  {
    provider: 'groq',
    model_pattern: 'qwen/qwen3.8-27b',
    cost_basis: 'free_tier',
    rpm: 30,
    rpd: 1000,
    tpd: 1000000,
    reset_tz: 'America/Los_Angeles',
    source_url: 'https://console.groq.com/docs/rate-limits',
    verified_date: '2026-10-10',
    use_cases: 'Multilingual tasks, formatting, code reviews',
    not_for: 'Client quotes, invoices, customer messages',
    percent_used: 0,
    status: 'normal',
  },
  {
    provider: 'gemini',
    model_pattern: 'gemini-2.5-flash',
    cost_basis: 'free_tier',
    rpm: 15,
    rpd: 1500,
    tpd: 1000000,
    reset_tz: 'America/Los_Angeles',
    source_url: 'https://ai.google.dev/pricing',
    verified_date: '2026-10-10',
    use_cases: 'Multimodal image analysis, large context docs',
    not_for: 'Client quotes, invoices, customer messages',
    percent_used: 0,
    status: 'normal',
  },
  {
    provider: 'gemini',
    model_pattern: 'gemini-2.5-flash-lite',
    cost_basis: 'free_tier',
    rpm: 30,
    rpd: 1500,
    tpd: 1000000,
    reset_tz: 'America/Los_Angeles',
    source_url: 'https://ai.google.dev/pricing',
    verified_date: '2026-10-10',
    use_cases: 'Lightweight fast tasks, quick drafts',
    not_for: 'Client quotes, invoices, customer messages',
    percent_used: 0,
    status: 'normal',
  },
  {
    provider: 'gemini',
    model_pattern: 'gemini-3.5-flash',
    cost_basis: 'free_tier',
    rpm: 15,
    rpd: 1500,
    tpd: 1000000,
    reset_tz: 'America/Los_Angeles',
    source_url: 'https://ai.google.dev/pricing',
    verified_date: '2026-10-10',
    use_cases: 'Advanced multimodal drafts, system tasks',
    not_for: 'Client quotes, invoices, customer messages',
    percent_used: 0,
    status: 'normal',
  },
  {
    provider: 'openrouter',
    model_pattern: 'nvidia/nemotron-3-super-120b-a12b:free',
    cost_basis: 'free_tier',
    rpm: 20,
    rpd: 200,
    tpd: 500000,
    reset_tz: 'UTC',
    source_url: 'https://openrouter.ai/models',
    verified_date: '2026-10-10',
    use_cases: 'Deep reasoning, fallback synthesis',
    not_for: 'Client quotes, invoices, customer messages',
    percent_used: 0,
    status: 'normal',
  },
  {
    provider: 'openrouter',
    model_pattern: 'google/gemma-4-31b-it:free',
    cost_basis: 'free_tier',
    rpm: 20,
    rpd: 200,
    tpd: 500000,
    reset_tz: 'UTC',
    source_url: 'https://openrouter.ai/models',
    verified_date: '2026-10-10',
    use_cases: 'Text transformation, instructions',
    not_for: 'Client quotes, invoices, customer messages',
    percent_used: 0,
    status: 'normal',
  },
  {
    provider: 'openrouter',
    model_pattern: 'cohere/north-mini-code:free',
    cost_basis: 'free_tier',
    rpm: 20,
    rpd: 200,
    tpd: 500000,
    reset_tz: 'UTC',
    source_url: 'https://openrouter.ai/models',
    verified_date: '2026-10-10',
    use_cases: 'Code syntax checking, helper routines',
    not_for: 'Client quotes, invoices, customer messages',
    percent_used: 0,
    status: 'normal',
  },
  {
    provider: 'openrouter',
    model_pattern: 'openrouter/free',
    cost_basis: 'free_tier',
    rpm: 20,
    rpd: 200,
    tpd: 500000,
    reset_tz: 'UTC',
    source_url: 'https://openrouter.ai/models',
    verified_date: '2026-10-10',
    use_cases: 'Generic router free fallback',
    not_for: 'Client quotes, invoices, customer messages',
    percent_used: 0,
    status: 'normal',
  },
];

/* ── Free-Tier Quota Cards Component ─────────────────────────── */
function FreeTierQuotaCards({ freeTiers }: { freeTiers: FreeTierData[] }) {
  const displayTiers = freeTiers.length > 0 ? freeTiers : DEFAULT_FREE_TIERS;

  const fmtKTokens = (n: number) => {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
    return String(n);
  };

  return (
    <div className="space-y-4">
      {/* Black & Gold Theme Privacy Note */}
      <div
        className="rounded-2xl p-4 md:p-5 border transition-all"
        style={{
          background: 'linear-gradient(135deg, #0e1013 0%, #171a1f 100%)',
          borderColor: '#b8960c',
          boxShadow: '0 4px 20px rgba(184, 150, 12, 0.08)',
        }}
      >
        <div className="flex items-start gap-3">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
            style={{ background: 'rgba(184, 150, 12, 0.15)', border: '1px solid #b8960c' }}
          >
            <ShieldAlert size={18} className="text-[#d4b84a]" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-wider text-[#d4b84a]">
                Free-Tier Policy & Guardrail Protection
              </span>
              <span
                className="text-[9px] font-bold px-2 py-0.5 rounded tracking-wide"
                style={{ background: '#b8960c', color: '#000' }}
              >
                FREE IS NOT PRIVATE
              </span>
            </div>
            <p className="text-[12px] text-[#ccc] mt-1.5 leading-relaxed">
              <strong className="text-white">Free is not private:</strong> Free-tier endpoints may store prompt transcripts and evaluate them for provider model fine-tuning.
              Empire guardrails <strong>strictly block all client-facing and financial operations</strong> (forge quotes, customer invoices, workroom calculations, and client replies) from free models.
            </p>
            <div className="text-[10px] text-[#999] mt-2 flex flex-wrap gap-x-4 gap-y-1 font-mono">
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#f59e0b]" />
                Quota alert: warns at 4/5 (80%) of daily or minute rate
              </span>
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#ef4444]" />
                Failover: 100% exhaustion auto-skips to next candidate
              </span>
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-[#22c55e]" />
                Cost basis: $0.00 / call
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Grid of Quota Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
        {displayTiers.map((ft, idx) => {
          const reqMin = ft.requests_minute || 0;
          const limMin = ft.rpm_limit || ft.rpm || 30;
          const reqDay = ft.requests_day || 0;
          const limDay = ft.rpd_limit || ft.rpd || 1000;
          const tokDay = ft.tokens_day || 0;
          const limTok = ft.tpd_limit || ft.tpd || 1_000_000;

          const pct = Math.min(ft.percent_used || 0, 100);
          const isExhausted = ft.exhausted || pct >= 100;
          const isWarn = ft.warn || pct >= 80;

          // Status colors
          const statusBg = isExhausted
            ? 'rgba(220, 38, 38, 0.18)'
            : isWarn
            ? 'rgba(217, 119, 6, 0.18)'
            : 'rgba(22, 163, 74, 0.18)';
          const statusColor = isExhausted ? '#ef4444' : isWarn ? '#f59e0b' : '#22c55e';
          const statusText = isExhausted
            ? '100% EXHAUSTED (FAILOVER)'
            : isWarn
            ? `${pct.toFixed(0)}% WARN (≥80%)`
            : 'NORMAL ($0)';

          const useCasesText = typeof ft.use_cases === 'string'
            ? ft.use_cases
            : Array.isArray(ft.use_cases) ? (ft.use_cases as string[]).join(', ') : 'Internal tasks, draft analysis';

          const notForText = typeof ft.not_for === 'string'
            ? ft.not_for
            : Array.isArray(ft.not_for) ? (ft.not_for as string[]).join(', ') : 'Quotes, invoices, client replies';

          return (
            <div
              key={idx}
              className="rounded-2xl p-4 flex flex-col justify-between transition-all"
              style={{
                background: '#121417',
                border: `1px solid ${isExhausted ? '#dc2626' : isWarn ? '#d97706' : '#242830'}`,
                boxShadow: isWarn ? '0 4px 14px rgba(217, 119, 6, 0.12)' : '0 2px 8px rgba(0,0,0,0.25)',
              }}
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="min-w-0">
                    <span className="text-[10px] uppercase font-bold tracking-wider text-[#b8960c]">
                      {ft.provider}
                    </span>
                    <h4 className="text-[12px] font-bold text-white font-mono break-all leading-tight mt-0.5">
                      {ft.model_pattern}
                    </h4>
                  </div>
                  <span
                    className="text-[9px] font-bold px-2 py-0.5 rounded-full shrink-0 border whitespace-nowrap"
                    style={{
                      background: statusBg,
                      color: statusColor,
                      borderColor: `${statusColor}40`,
                    }}
                  >
                    {statusText}
                  </span>
                </div>

                {/* Quota Progress Bar */}
                <div className="mt-3">
                  <div className="flex justify-between items-center text-[10px] text-[#888] mb-1 font-mono">
                    <span>Quota Utilized</span>
                    <span style={{ color: statusColor }}>{pct.toFixed(1)}%</span>
                  </div>
                  <div className="w-full h-2 rounded-full overflow-hidden bg-[#22262d]">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.max(pct, 2)}%`,
                        backgroundColor: statusColor,
                      }}
                    />
                  </div>
                </div>

                {/* Quota Fractions (RPM, RPD, TPD) */}
                <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-[#22262d] text-center font-mono">
                  <div className="p-1.5 rounded-xl bg-[#181b20]">
                    <div className="text-[9px] text-[#777] uppercase">RPM Limit</div>
                    <div className="text-[11px] font-bold text-white mt-0.5">
                      {reqMin}/{limMin}
                    </div>
                  </div>
                  <div className="p-1.5 rounded-xl bg-[#181b20]">
                    <div className="text-[9px] text-[#777] uppercase">RPD Limit</div>
                    <div className="text-[11px] font-bold text-white mt-0.5">
                      {reqDay}/{limDay}
                    </div>
                  </div>
                  <div className="p-1.5 rounded-xl bg-[#181b20]">
                    <div className="text-[9px] text-[#777] uppercase">TPD Limit</div>
                    <div className="text-[11px] font-bold text-white mt-0.5">
                      {fmtKTokens(tokDay)}/{fmtKTokens(limTok)}
                    </div>
                  </div>
                </div>

                {/* Use cases and Not for */}
                <div className="mt-3 space-y-1 text-[10px]">
                  <div className="text-[#a1a1aa] flex items-start gap-1">
                    <span className="text-[#22c55e] font-bold shrink-0">✓ Best:</span>
                    <span className="truncate">{useCasesText}</span>
                  </div>
                  <div className="text-[#fca5a5] flex items-start gap-1">
                    <span className="text-[#ef4444] font-bold shrink-0">✕ Block:</span>
                    <span className="truncate">{notForText}</span>
                  </div>
                </div>
              </div>

              <div className="mt-3 pt-2.5 border-t border-[#22262d] flex items-center justify-between text-[9px] text-[#777] font-mono">
                <span className="text-[#b8960c] font-bold">$0 · Free Tier</span>
                <span>Reset: {ft.reset_tz || 'UTC'}</span>
              </div>
            </div>
          );
        })}
      </div>
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
  const [freeTiers, setFreeTiers] = useState<FreeTierData[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [trendData, setTrendData] = useState<{ label: string; cost: number; requests: number }[]>([]);
  const [tab, setTab] = useState<'overview' | 'free-tiers' | 'breakdown' | 'log'>('overview');
  const [budgetOverride, setBudgetOverride] = useState<number | null>(null);
  const [showBudgetEdit, setShowBudgetEdit] = useState(false);
  const [bleedAlerts, setBleedAlerts] = useState<BleedAlert[]>([]);

  // Load budget from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem('empire_monthly_budget');
      if (stored) {
        const n = parseFloat(stored);
        if (!isNaN(n) && n > 0) setBudgetOverride(n);
      }
    } catch { /* ignore */ }
  }, []);

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
      const [ov, tx, prov, feat, biz, bleed, ft] = await Promise.all([
        safeFetch(`${API}/costs/overview?days=30`),
        safeFetch(`${API}/costs/transactions?limit=100`),
        safeFetch(`${API}/costs/by-provider?days=30`),
        safeFetch(`${API}/costs/by-feature?days=30`),
        safeFetch(`${API}/costs/by-business?days=30`),
        safeFetch(`${API}/costs/bleed-watch?hours=24`),
        safeFetch(`${API}/costs/free-tiers`),
      ]);
      setOverview(ov);
      setTransactions(ov?.transactions || tx?.transactions || tx || []);
      setByProvider(prov?.by_provider || []);
      setByFeature(feat?.by_feature || []);
      setByBusiness(biz?.by_business || []);
      setBleedAlerts(bleed?.alerts || []);
      setFreeTiers(ft?.free_tiers || []);
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

  /* ── Stacked bar data from transactions ──────────────────── */
  const stackedTrendData = useMemo(() => {
    if (!transactions.length || view !== 'daily') return null;
    const byDay: Record<string, { label: string; free: number; cheap: number; moderate: number; premium: number }> = {};
    for (const t of transactions) {
      if (!t.timestamp) continue;
      const dayLabel = t.timestamp.slice(5, 10); // MM-DD
      if (!byDay[dayLabel]) byDay[dayLabel] = { label: dayLabel, free: 0, cheap: 0, moderate: 0, premium: 0 };
      const tier = getTierCategory(t.model);
      byDay[dayLabel][tier] += t.cost_usd;
    }
    const sorted = Object.values(byDay).sort((a, b) => a.label.localeCompare(b.label));
    return sorted.length > 0 ? sorted : null;
  }, [transactions, view]);

  /* ── Cost savings calculation ───────────────────────────── */
  const savings = useMemo(() => {
    if (!overview) return 0;
    let total = 0;
    for (const m of overview.by_model) {
      const tier = getTierForModel(m.model).tier;
      if (tier !== 'PREMIUM') {
        const grokEquiv = (m.input_tokens * 5) / 1_000_000 + (m.output_tokens * 15) / 1_000_000;
        const diff = grokEquiv - m.cost;
        if (diff > 0) total += diff;
      }
    }
    return total;
  }, [overview]);

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

  const handleBudgetSave = (val: number) => {
    setBudgetOverride(val);
    try { localStorage.setItem('empire_monthly_budget', String(val)); } catch { /* ignore */ }
    setShowBudgetEdit(false);
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
  const effectiveLimit = budgetOverride ?? ov.budget.monthly_limit;
  const effectivePercent = effectiveLimit > 0 ? (ov.budget.monthly_spent / effectiveLimit) * 100 : 0;
  const effectiveAlert = effectivePercent >= (ov.budget.auto_switch_threshold || 90);
  const fmt = (n: number) => n >= 1 ? `$${n.toFixed(2)}` : `$${n.toFixed(4)}`;
  const fmtK = (n: number) => n >= 1_000_000 ? `${(n/1_000_000).toFixed(1)}M` : n >= 1000 ? `${(n/1000).toFixed(0)}K` : String(n);
  const tokenSources = ov.token_sources || { provider_reported: 0, estimated: 0, unknown: 0 };
  const tokenSourceRows = tokenSources.provider_reported + tokenSources.estimated + tokenSources.unknown;
  const providerReportedPct = tokenSourceRows > 0 ? ((tokenSources.provider_reported / tokenSourceRows) * 100) : 0;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const chartData: any[] = stackedTrendData && view === 'daily' ? stackedTrendData : trendData;
  const useStacked = !!stackedTrendData && view === 'daily';

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
            {(['overview', 'free-tiers', 'breakdown', 'log'] as const).map(t => (
              <button key={t} onClick={() => setTab(t)}
                className={`filter-tab ${tab === t ? 'active' : ''}`}
                style={{ flex: 1, textAlign: 'center', textTransform: 'capitalize' }}>
                {t === 'free-tiers' ? 'Free-Tier Quotas' : t}
              </button>
            ))}
          </div>

          {/* ── Overview Tab ──────────────────────────────────────── */}
          {tab === 'overview' && (
            <>
              {/* KPI Row */}
              <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
                <KPI icon={DollarSign} label="Today" value={fmt(ov.today.cost_usd)} sub={`${ov.today.requests} calls`} />
                <KPI icon={TrendingUp} label="This Month" value={fmt(ov.budget.monthly_spent)} sub={`${effectivePercent.toFixed(1)}% of budget`} alert={effectiveAlert} />
                <KPI icon={Zap} label="30-Day Total" value={fmt(ov.total.cost_usd)} sub={`${fmtK(ov.total.total_tokens)} tokens`} />
                <KPI icon={Clock} label="30-Day Calls" value={String(ov.total.requests)} sub={`Avg ${ov.total.requests > 0 ? fmt(ov.total.cost_usd / ov.total.requests) : '$0'}/call`} />
                <KPI icon={Shield} label="Est. Savings" value={fmt(savings)} sub="vs all-Grok routing" />
                <KPI icon={Info} label="Provider Reported" value={`${providerReportedPct.toFixed(0)}%`} sub={`${tokenSources.provider_reported} rows provider-reported`} />
              </div>

              {/* Budget Gauge */}
              <BudgetGauge
                spent={ov.budget.monthly_spent}
                limit={effectiveLimit}
                percent={effectivePercent}
                alert={effectiveAlert}
                trendData={trendData}
                onEditBudget={() => setShowBudgetEdit(true)}
              />

              <div className="empire-card flat" style={{ padding: 16 }}>
                <div className="flex items-center justify-between mb-2">
                  <div className="section-label" style={{ marginBottom: 0, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <AlertTriangle size={13} className="text-[#b8960c]" />
                    Bleed Watch
                  </div>
                  <span className={`status-pill ${bleedAlerts.length === 0 ? 'ok' : 'overdue'}`}>{bleedAlerts.length === 0 ? 'CLEAN' : `${bleedAlerts.length} ALERTS`}</span>
                </div>
                {bleedAlerts.length === 0 ? (
                  <div className="text-[11px] text-[#777]">No routing/cost anomalies detected in the last 24 hours.</div>
                ) : (
                  <div className="space-y-2">
                    {bleedAlerts.slice(0, 8).map((a, idx) => (
                      <div key={idx} className="rounded-xl border border-[#f3d3d3] bg-[#fff7f7] px-3 py-2">
                        <div className="text-[11px] font-semibold text-[#9f1239]">{a.kind}</div>
                        <div className="text-[10px] text-[#666]">
                          {a.provider_model} · lane {a.lane} · {a.count} · {a.source_module}
                        </div>
                        <div className="text-[10px] text-[#7f1d1d] mt-1">{a.recommended_action}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Billing Cutoff Info */}
              <div className="empire-card flat" style={{ padding: 16 }}>
                <div className="flex items-center gap-2 mb-2">
                  <Info size={13} className="text-[#b8960c]" />
                  <span className="text-[11px] font-bold text-[#555]">Provider Billing Cycles</span>
                </div>
                <div className="text-[11px] text-[#777] space-y-0.5 pl-5">
                  <div>&#8226; Anthropic: Monthly from account creation date</div>
                  <div>&#8226; xAI (Grok): Pay-as-you-go, billed monthly</div>
                  <div>&#8226; Groq: Free tier resets daily (30 RPM, 1000 req/day)</div>
                  <div>&#8226; Google Gemini: Free tier resets daily (10 RPM, 250 req/day)</div>
                  <div>&#8226; OpenAI: Pay-as-you-go, billed monthly</div>
                </div>
              </div>

              {/* Trend Chart */}
              <div className="empire-card flat" style={{ padding: 20 }}>
                <div className="flex items-center justify-between mb-4">
                  <span className="section-label" style={{ marginBottom: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Activity size={15} className="text-[#b8960c]" /> Cost Trend
                    {useStacked && <span className="text-[10px] font-normal text-[#999]">(by tier)</span>}
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
                {chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#ece8e0" />
                      <XAxis dataKey="label" tick={{ fill: '#999', fontSize: 10 }} />
                      <YAxis tick={{ fill: '#999', fontSize: 10 }} tickFormatter={v => `$${v}`} />
                      <Tooltip
                        contentStyle={{ background: '#faf9f7', border: '1px solid #ece8e0', borderRadius: 14, boxShadow: '0 4px 12px rgba(0,0,0,0.06)' }}
                        // eslint-disable-next-line @typescript-eslint/no-explicit-any
                        formatter={(v: any, name: any) => [`$${Number(v).toFixed(4)}`, useStacked && name ? String(name).charAt(0).toUpperCase() + String(name).slice(1) : 'Cost']}
                      />
                      {view === 'daily' && (
                        <ReferenceLine
                          x="03-22"
                          stroke="#dc2626"
                          strokeDasharray="6 4"
                          strokeWidth={2}
                          label={{ value: 'Tiered Routing', position: 'top', fill: '#dc2626', fontSize: 10, fontWeight: 700 }}
                        />
                      )}
                      {useStacked ? (
                        <>
                          <Bar dataKey="free" stackId="a" fill={TIER_COLORS.free} name="Free" />
                          <Bar dataKey="cheap" stackId="a" fill={TIER_COLORS.cheap} name="Cheap" />
                          <Bar dataKey="moderate" stackId="a" fill={TIER_COLORS.moderate} name="Moderate" />
                          <Bar dataKey="premium" stackId="a" fill={TIER_COLORS.premium} name="Premium" radius={[6, 6, 0, 0]} />
                          <Legend
                            wrapperStyle={{ fontSize: 10 }}
                            formatter={(value: string) => <span style={{ color: '#555' }}>{value}</span>}
                          />
                        </>
                      ) : (
                        <Bar dataKey="cost" fill="#b8960c" radius={[6, 6, 0, 0]} />
                      )}
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
                      <th className="text-center">Tier</th>
                      <th className="text-right">Calls</th>
                      <th className="text-right">Tokens</th>
                      <th className="text-right">Est / Reported</th>
                      <th className="text-right">Cost</th>
                    </tr></thead>
                    <tbody>
                      {ov.by_model.map((m, i) => {
                        const link = PROVIDER_LINKS[m.model.toLowerCase()] ||
                          Object.entries(PROVIDER_LINKS).find(([k]) => m.model.toLowerCase().includes(k))?.[1];
                        return (
                          <tr key={i}>
                            <td className="font-mono font-medium text-[#1a1a1a]">
                              {link ? (
                                <a href={link} target="_blank" rel="noopener noreferrer" className="hover:text-[#b8960c] transition-colors flex items-center gap-1.5">
                                  {m.model}
                                  <ExternalLink size={11} className="text-[#bbb] shrink-0" />
                                </a>
                              ) : m.model}
                            </td>
                            <td>{m.provider}</td>
                            <td className="text-center"><TierBadge model={m.model} /></td>
                            <td className="text-right">{m.requests}</td>
                            <td className="text-right">{fmtK(m.input_tokens + m.output_tokens)}</td>
                            <td className="text-right text-[11px] text-[#666]">
                              {fmt(m.estimated_cost || 0)} / {fmt(m.provider_reported_cost || 0)}
                            </td>
                            <td className="text-right font-bold text-[#b8960c]">{fmt(m.cost)}</td>
                          </tr>
                        );
                      })}
                      {ov.by_model.length === 0 && (
                        <tr><td colSpan={7} className="text-center py-8 text-[#bbb]">No model data yet</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Free-Tier Quota & Policy Section */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="section-label" style={{ marginBottom: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Shield size={15} className="text-[#b8960c]" /> Free-Tier Models & Active Quotas
                  </span>
                  <button
                    onClick={() => setTab('free-tiers')}
                    className="text-xs text-[#b8960c] hover:underline font-semibold cursor-pointer"
                  >
                    View details →
                  </button>
                </div>
                <FreeTierQuotaCards freeTiers={freeTiers} />
              </div>

              {/* Manage Providers */}
              <div className="empire-card flat" style={{ padding: 20 }}>
                <span className="section-label" style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                  <ExternalLink size={15} className="text-[#b8960c]" /> Manage Providers
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                  {PROVIDER_DASHBOARD_LIST.map(p => (
                    <a
                      key={p.name}
                      href={p.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 px-3 py-2.5 rounded-xl border border-[#ece8e0] hover:border-[#b8960c] bg-white hover:bg-[#fdf8eb] transition-colors text-xs font-medium text-[#555] hover:text-[#1a1a1a]"
                    >
                      <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: p.color }} />
                      {p.name}
                      <ExternalLink size={10} className="ml-auto text-[#bbb]" />
                    </a>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* ── Free Tiers Tab ────────────────────────────────────── */}
          {tab === 'free-tiers' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold text-[#1a1a1a]">Free-Tier Models & Active Quotas</h3>
                  <p className="text-xs text-[#777] mt-0.5">
                    Real-time monitoring of free model quotas, rate limits, and privacy guardrails.
                  </p>
                </div>
                <button
                  onClick={load}
                  className="px-3 py-1.5 text-xs font-semibold rounded-xl border border-[#ece8e0] bg-white hover:bg-[#fdf8eb] text-[#b8960c] flex items-center gap-1.5 cursor-pointer"
                >
                  <RefreshCw size={12} className={loading ? 'animate-spin' : ''} /> Refresh Quotas
                </button>
              </div>
              <FreeTierQuotaCards freeTiers={freeTiers} />
            </div>
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
                    <th className="text-left">Source</th>
                    <th className="text-left">Feature</th>
                    <th className="text-left">Business</th>
                    <th className="text-right">In</th>
                    <th className="text-right">Out</th>
                    <th className="text-left">Token Src</th>
                    <th className="text-right">Cost</th>
                  </tr></thead>
                  <tbody>
                    {transactions.map(t => (
                      <tr key={t.id}>
                        <td className="whitespace-nowrap font-mono text-[#999]" suppressHydrationWarning>{t.timestamp?.slice(5, 16)}</td>
                        <td className="font-mono font-medium text-[#1a1a1a]">{t.model}</td>
                        <td className="text-[11px]">{t.source_module || t.source || '-'}</td>
                        <td>{t.feature}</td>
                        <td>{t.business}</td>
                        <td className="text-right">{fmtK(t.input_tokens)}</td>
                        <td className="text-right">{fmtK(t.output_tokens)}</td>
                        <td className="text-[11px]">{t.token_source || 'estimated'}</td>
                        <td className="text-right font-bold text-[#b8960c]">{t.cost_usd > 0 ? fmt(t.cost_usd) : '-'}</td>
                      </tr>
                    ))}
                    {transactions.length === 0 && (
                      <tr><td colSpan={9} className="text-center py-12 text-[#bbb]">No transactions yet</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Budget Edit Modal */}
      {showBudgetEdit && (
        <BudgetEditModal
          current={effectiveLimit}
          onSave={handleBudgetSave}
          onClose={() => setShowBudgetEdit(false)}
        />
      )}
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
