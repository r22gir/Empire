'use client';
import { Zap } from 'lucide-react';

const DAILY_BUDGET = 100_000; // tokens

const PROVIDERS = [
  { name: 'Grok',   tokens: 0, cost: 0, color: '#22c55e', bg: 'rgba(34,197,94,0.12)', border: 'rgba(34,197,94,0.2)' },
  { name: 'Claude', tokens: 0, cost: 0, color: '#8B5CF6', bg: 'rgba(139,92,246,0.12)', border: 'var(--purple-border)' },
];

interface Props {
  backendOnline: boolean;
}

export default function AiUsagePanel({ backendOnline }: Props) {
  // Placeholder — will be wired to backend token_usage API later
  const totalTokens = PROVIDERS.reduce((s, p) => s + p.tokens, 0);
  const totalCost = PROVIDERS.reduce((s, p) => s + p.cost, 0);
  const usagePercent = Math.min((totalTokens / DAILY_BUDGET) * 100, 100);
  const budgetColor = usagePercent > 80 ? '#ef4444' : usagePercent > 60 ? '#f59e0b' : '#22c55e';

  return (
    <div className="cc-panel">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Zap className="w-3.5 h-3.5" style={{ color: 'var(--gold)' }} />
          <p className="cc-panel-header mb-0">AI Usage</p>
        </div>
        <span
          className="text-[10px] px-1.5 py-0.5 rounded font-mono"
          style={{ background: 'var(--elevated)', color: 'var(--text-muted)' }}
        >
          today
        </span>
      </div>

      {/* Total tokens + cost */}
      <div
        className="flex items-center justify-between p-2.5 rounded-lg mb-3"
        style={{ background: 'var(--raised)' }}
      >
        <div>
          <p className="text-sm font-bold font-mono" style={{ color: 'var(--text-primary)' }}>
            {totalTokens.toLocaleString()}
          </p>
          <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>tokens</p>
        </div>
        <div className="text-right">
          <p className="text-sm font-bold font-mono" style={{ color: 'var(--gold)' }}>
            ${totalCost.toFixed(2)}
          </p>
          <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>est. cost</p>
        </div>
      </div>

      {/* Budget bar */}
      <div className="mb-3">
        <div className="flex justify-between text-xs mb-1">
          <span style={{ color: 'var(--text-secondary)' }}>Daily Budget</span>
          <span style={{ color: 'var(--text-primary)' }}>
            {totalTokens.toLocaleString()} / {(DAILY_BUDGET / 1000).toFixed(0)}k
          </span>
        </div>
        <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--elevated)' }}>
          <div
            className="h-full rounded-full transition-all"
            style={{ width: `${Math.max(usagePercent, 1)}%`, background: budgetColor }}
          />
        </div>
      </div>

      {/* Per-provider breakdown */}
      <div className="space-y-1.5">
        {PROVIDERS.map(p => (
          <div key={p.name} className="flex items-center gap-2">
            <span
              className="text-[10px] px-1.5 py-0.5 rounded font-mono"
              style={{ background: p.bg, color: p.color, border: `1px solid ${p.border}` }}
            >
              {p.name}
            </span>
            <span className="flex-1 text-xs font-mono" style={{ color: 'var(--text-primary)' }}>
              {p.tokens.toLocaleString()}
            </span>
            <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>
              ${p.cost.toFixed(2)}
            </span>
          </div>
        ))}
      </div>

      {/* Hint */}
      {!backendOnline && (
        <p className="text-[10px] text-center mt-3" style={{ color: 'var(--text-muted)' }}>
          Connect backend for live tracking
        </p>
      )}
    </div>
  );
}
