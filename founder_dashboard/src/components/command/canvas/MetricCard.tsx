'use client';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { MetricData } from './ContentAnalyzer';

interface Props {
  metrics: MetricData[];
}

export default function MetricCard({ metrics }: Props) {
  if (metrics.length === 0) return null;

  // Layout: 2 or 3 columns depending on count
  const cols = metrics.length <= 2 ? 2 : metrics.length <= 3 ? 3 : metrics.length <= 4 ? 2 : 3;

  return (
    <div
      className="grid gap-2 my-2"
      style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}
    >
      {metrics.map((m, i) => (
        <div
          key={i}
          className="rounded-xl p-3 flex flex-col gap-1"
          style={{
            background: 'var(--raised)',
            border: '1px solid var(--border)',
          }}
        >
          <span className="text-[9px] font-medium uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
            {m.label}
          </span>
          <div className="flex items-end gap-2">
            <span className="text-lg font-bold" style={{ color: 'var(--gold)' }}>
              {m.value}
            </span>
            {m.change && (
              <span
                className="text-[10px] font-medium flex items-center gap-0.5 pb-0.5"
                style={{
                  color: m.direction === 'up' ? '#22c55e' :
                         m.direction === 'down' ? '#ef4444' : 'var(--text-muted)',
                }}
              >
                {m.direction === 'up' ? <TrendingUp className="w-3 h-3" /> :
                 m.direction === 'down' ? <TrendingDown className="w-3 h-3" /> :
                 <Minus className="w-3 h-3" />}
                {m.change}
              </span>
            )}
          </div>
          {/* Subtle bar indicator */}
          <div className="w-full h-0.5 rounded-full mt-1" style={{ background: 'var(--border)' }}>
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${Math.min(100, Math.max(10, (i + 1) * 20))}%`,
                background: m.direction === 'up' ? '#22c55e' :
                             m.direction === 'down' ? '#ef4444' : 'var(--gold)',
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
