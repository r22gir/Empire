'use client';
import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { TokenStats } from '@/lib/types';

interface Props {
  tokenStats: TokenStats | null;
  backendOnline: boolean;
}

function formatTokens(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K';
  return n.toString();
}

const MODEL_COLORS: Record<string, string> = {
  grok: '#22c55e',
  'claude-4.6-sonnet': '#8B5CF6',
  'claude-sonnet-4-6': '#8B5CF6',
  'ollama-llama3.1': '#fb923c',
  'ollama-llama': '#fb923c',
  openclaw: '#06b6d4',
};

export default function TokenCostPanel({ tokenStats, backendOnline }: Props) {
  const [open, setOpen] = useState(false);

  if (!backendOnline || !tokenStats) {
    return (
      <div className="cc-panel" style={{ padding: '8px 10px' }}>
        <div className="flex items-center gap-2">
          <span className="dot-unknown" />
          <span className="text-[11px] font-mono" style={{ color: 'var(--text-muted)' }}>
            {backendOnline ? 'Loading tokens...' : 'Backend offline'}
          </span>
        </div>
      </div>
    );
  }

  const { total, today, budget, by_model } = tokenStats;
  const budgetColor = budget.percent_used > 90 ? '#ef4444'
    : budget.percent_used > 70 ? '#f59e0b'
    : '#22c55e';

  const summary = `$${budget.monthly_spent.toFixed(2)}/$${budget.monthly_limit} | ${formatTokens(total.total_tokens)} tok`;

  return (
    <div className="cc-panel" style={{ padding: '8px 10px' }}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2"
      >
        <span
          className="shrink-0"
          style={{
            width: '7px', height: '7px', borderRadius: '50%',
            background: budgetColor,
          }}
        />
        <span className="flex-1 text-[11px] font-mono text-left truncate" style={{ color: 'var(--text-secondary)' }}>
          {summary}
        </span>
        {budget.alert && (
          <span className="text-[9px] px-1 py-0.5 rounded font-mono shrink-0"
            style={{ background: 'rgba(239,68,68,0.15)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.2)' }}
          >
            ALERT
          </span>
        )}
        {open
          ? <ChevronDown className="w-3 h-3 shrink-0" style={{ color: 'var(--text-muted)' }} />
          : <ChevronRight className="w-3 h-3 shrink-0" style={{ color: 'var(--text-muted)' }} />
        }
      </button>

      {open && (
        <div className="mt-2 pt-2 space-y-2.5" style={{ borderTop: '1px solid var(--border)' }}>
          {/* Budget progress bar */}
          <div>
            <div className="flex justify-between text-[10px] mb-0.5">
              <span style={{ color: 'var(--text-secondary)' }}>Monthly Budget</span>
              <span style={{ color: budgetColor, fontFamily: "'JetBrains Mono', monospace" }}>
                {budget.percent_used.toFixed(0)}%
              </span>
            </div>
            <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--elevated)' }}>
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${Math.min(budget.percent_used, 100)}%`,
                  background: budgetColor,
                }}
              />
            </div>
            <div className="flex justify-between text-[9px] mt-0.5 font-mono" style={{ color: 'var(--text-muted)' }}>
              <span>${budget.monthly_spent.toFixed(2)}</span>
              <span>${budget.monthly_limit.toFixed(2)}</span>
            </div>
          </div>

          {/* Today's usage */}
          <div>
            <div className="text-[10px] mb-1" style={{ color: 'var(--text-muted)' }}>Today</div>
            <div className="grid grid-cols-3 gap-1">
              <div className="text-center rounded-lg py-1" style={{ background: 'var(--elevated)' }}>
                <div className="text-[10px] font-mono" style={{ color: 'var(--gold)' }}>
                  {today.requests}
                </div>
                <div className="text-[8px]" style={{ color: 'var(--text-muted)' }}>reqs</div>
              </div>
              <div className="text-center rounded-lg py-1" style={{ background: 'var(--elevated)' }}>
                <div className="text-[10px] font-mono" style={{ color: 'var(--cyan)' }}>
                  {formatTokens(today.input_tokens + today.output_tokens)}
                </div>
                <div className="text-[8px]" style={{ color: 'var(--text-muted)' }}>tokens</div>
              </div>
              <div className="text-center rounded-lg py-1" style={{ background: 'var(--elevated)' }}>
                <div className="text-[10px] font-mono" style={{ color: budgetColor }}>
                  ${today.cost_usd.toFixed(3)}
                </div>
                <div className="text-[8px]" style={{ color: 'var(--text-muted)' }}>cost</div>
              </div>
            </div>
          </div>

          {/* Per-model breakdown */}
          {by_model.length > 0 && (
            <div>
              <div className="text-[10px] mb-1" style={{ color: 'var(--text-muted)' }}>By Model (30d)</div>
              <div className="space-y-1">
                {by_model.map(m => {
                  const color = MODEL_COLORS[m.model] || 'var(--text-secondary)';
                  const totalTok = m.input_tokens + m.output_tokens;
                  return (
                    <div key={m.model} className="flex items-center gap-1.5 text-[10px]">
                      <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: color, flexShrink: 0 }} />
                      <span className="flex-1 truncate" style={{ color: 'var(--text-secondary)' }}>
                        {m.model}
                      </span>
                      <span className="font-mono shrink-0" style={{ color }}>
                        {formatTokens(totalTok)}
                      </span>
                      {m.cost > 0 && (
                        <span className="font-mono shrink-0" style={{ color: 'var(--text-muted)' }}>
                          ${m.cost.toFixed(3)}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Auto-switch indicator */}
          {budget.auto_switch_to_local && (
            <div
              className="flex items-center gap-1.5 px-2 py-1 rounded-lg text-[9px]"
              style={{ background: 'rgba(251,146,60,0.1)', border: '1px solid rgba(251,146,60,0.2)' }}
            >
              <span>🦙</span>
              <span style={{ color: '#fb923c' }}>
                Auto-switch at {(budget.auto_switch_threshold * 100).toFixed(0)}%
              </span>
            </div>
          )}

          {/* 30-day total */}
          <div className="flex justify-between text-[9px] pt-1 font-mono" style={{ borderTop: '1px solid var(--border)', color: 'var(--text-muted)' }}>
            <span>30d: {total.requests} reqs</span>
            <span>{formatTokens(total.total_tokens)} tokens</span>
            <span>${total.cost_usd.toFixed(2)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
