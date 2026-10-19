'use client';
import type { ReactNode } from 'react';
import { CalendarDays, DollarSign, Layers } from 'lucide-react';
import { Orb } from '../v3/ui';
import type { StudioTab } from './moduleHome';

const TABS: { k: StudioTab; label: string; icon: ReactNode }[] = [
  { k: 'max', label: 'Max', icon: <Orb size={22} /> },
  { k: 'today', label: 'Today', icon: <CalendarDays size={18} strokeWidth={1.6} /> },
  { k: 'work', label: 'Work', icon: <Layers size={18} strokeWidth={1.6} /> },
  { k: 'money', label: 'Money', icon: <DollarSign size={18} strokeWidth={1.6} /> },
];

export function StudioTabButtons({
  active,
  onPick,
  className,
}: {
  active: StudioTab;
  onPick: (tab: StudioTab) => void;
  className?: string;
}) {
  return (
    <nav className={className} aria-label="Studio">
      {TABS.map((t) => (
        <button
          key={t.k}
          type="button"
          className={`studio-tab${active === t.k ? ' on' : ''}`}
          onClick={() => onPick(t.k)}
          aria-current={active === t.k ? 'page' : undefined}
          data-testid={`studio-tab-${t.k}`}
        >
          <span className="dot">{t.icon}</span>
          {t.label}
        </button>
      ))}
    </nav>
  );
}
