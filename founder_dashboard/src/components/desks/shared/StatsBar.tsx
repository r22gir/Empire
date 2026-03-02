'use client';
import { type LucideIcon } from 'lucide-react';
import { type ReactNode } from 'react';

export interface StatItem {
  label: string;
  value: string | number;
  icon: LucideIcon;
  color: string;
}

interface StatsBarProps {
  items: StatItem[];
  rightSlot?: ReactNode;
}

export default function StatsBar({ items, rightSlot }: StatsBarProps) {
  return (
    <div className="flex gap-3 p-4 shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
      {items.map(s => (
        <div
          key={s.label}
          className="flex-1 rounded-xl p-3 flex items-center gap-3"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
        >
          <s.icon className="w-5 h-5 shrink-0" style={{ color: s.color }} />
          <div>
            <p className="text-xl font-bold" style={{ color: s.color }}>{s.value}</p>
            <p className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>{s.label}</p>
          </div>
        </div>
      ))}
      {rightSlot && <div className="flex items-center gap-1 ml-auto shrink-0">{rightSlot}</div>}
    </div>
  );
}
