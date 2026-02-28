'use client';
import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

const DAILY_BUDGET = 100_000;
const PROVIDERS = [
  { name: 'Grok',   tokens: 0, cost: 0, color: '#22c55e', bg: 'rgba(34,197,94,0.12)', border: 'rgba(34,197,94,0.2)' },
  { name: 'Claude', tokens: 0, cost: 0, color: '#8B5CF6', bg: 'rgba(139,92,246,0.12)', border: 'var(--purple-border)' },
];

interface Props {
  backendOnline: boolean;
}

export default function AiUsagePanel({ backendOnline }: Props) {
  const [open, setOpen] = useState(false);
  const totalTokens = PROVIDERS.reduce((s, p) => s + p.tokens, 0);
  const totalCost = PROVIDERS.reduce((s, p) => s + p.cost, 0);
  const usagePercent = Math.min((totalTokens / DAILY_BUDGET) * 100, 100);
  const budgetColor = usagePercent > 80 ? '#ef4444' : usagePercent > 60 ? '#f59e0b' : '#22c55e';

  return (
    <div className="cc-panel" style={{ padding: '8px 10px' }}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2"
      >
        <span className="text-[10px]">⚡</span>
        <span className="flex-1 text-[11px] font-mono text-left truncate" style={{ color: 'var(--text-secondary)' }}>
          {totalTokens.toLocaleString()} tokens | ${totalCost.toFixed(2)} today
        </span>
        {open
          ? <ChevronDown className="w-3 h-3 shrink-0" style={{ color: 'var(--text-muted)' }} />
          : <ChevronRight className="w-3 h-3 shrink-0" style={{ color: 'var(--text-muted)' }} />
        }
      </button>

      {open && (
        <div className="mt-2 pt-2 space-y-2" style={{ borderTop: '1px solid var(--border)' }}>
          {/* Budget bar */}
          <div>
            <div className="flex justify-between text-[10px] mb-0.5">
              <span style={{ color: 'var(--text-secondary)' }}>Budget</span>
              <span style={{ color: 'var(--text-primary)' }}>
                {totalTokens.toLocaleString()} / {(DAILY_BUDGET / 1000).toFixed(0)}k
              </span>
            </div>
            <div className="h-1 rounded-full overflow-hidden" style={{ background: 'var(--elevated)' }}>
              <div className="h-full rounded-full" style={{ width: `${Math.max(usagePercent, 1)}%`, background: budgetColor }} />
            </div>
          </div>

          {/* Providers */}
          <div className="space-y-1">
            {PROVIDERS.map(p => (
              <div key={p.name} className="flex items-center gap-1.5">
                <span
                  className="text-[9px] px-1 py-0.5 rounded font-mono"
                  style={{ background: p.bg, color: p.color, border: `1px solid ${p.border}` }}
                >
                  {p.name}
                </span>
                <span className="flex-1 text-[10px] font-mono" style={{ color: 'var(--text-primary)' }}>
                  {p.tokens.toLocaleString()}
                </span>
                <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>
                  ${p.cost.toFixed(2)}
                </span>
              </div>
            ))}
          </div>

          {!backendOnline && (
            <p className="text-[9px] text-center" style={{ color: 'var(--text-muted)' }}>
              Connect backend for live tracking
            </p>
          )}
        </div>
      )}
    </div>
  );
}
