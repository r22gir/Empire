'use client';
import { useState } from 'react';
import { ServiceHealth, AIModel } from '@/lib/types';
import { ChevronDown, ChevronRight } from 'lucide-react';

const ITEMS = [
  { key: 'backend', label: 'API', icon: '⚡' },
  { key: 'git',     label: 'Git', icon: '📦', alwaysOn: true },
  { key: 'backup',  label: 'Bak', icon: '💾' },
] as const;

interface Props {
  serviceHealth: ServiceHealth;
  backendOnline: boolean;
  models: AIModel[];
}

export default function EmpireBoxPanel({ serviceHealth, backendOnline, models }: Props) {
  const [open, setOpen] = useState(false);
  const hasGrok = models.some(m => m.id === 'grok' && m.available);
  const hasClaude = models.some(m => m.id === 'claude' && m.available);

  return (
    <div className="cc-panel" style={{ padding: '8px 10px' }}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2"
      >
        <span className="text-[10px]">🛡️</span>
        {/* Service icons with dots */}
        <div className="flex-1 flex items-center gap-2">
          <span className="flex items-center gap-0.5 text-[10px]">⚡<span className={backendOnline ? 'dot-online' : 'dot-offline'} /></span>
          <span className="flex items-center gap-0.5 text-[10px]">📦<span className="dot-online" /></span>
          <span className="flex items-center gap-0.5 text-[10px]">🔑
            <span className={hasGrok || hasClaude ? 'dot-online' : 'dot-offline'} />
          </span>
        </div>
        {open
          ? <ChevronDown className="w-3 h-3 shrink-0" style={{ color: 'var(--text-muted)' }} />
          : <ChevronRight className="w-3 h-3 shrink-0" style={{ color: 'var(--text-muted)' }} />
        }
      </button>

      {open && (
        <div className="mt-2 pt-2 space-y-1.5" style={{ borderTop: '1px solid var(--border)' }}>
          <div className="flex items-center gap-2 text-[10px]">
            <span>⚡</span>
            <span className="flex-1" style={{ color: 'var(--text-secondary)' }}>FastAPI :8000</span>
            <span className={backendOnline ? 'dot-online' : 'dot-offline'} />
          </div>
          <div className="flex items-center gap-2 text-[10px]">
            <span>📦</span>
            <span className="flex-1" style={{ color: 'var(--text-secondary)' }}>Git ~/Empire</span>
            <span className="dot-online" />
          </div>
          <div className="flex items-center gap-2 text-[10px]">
            <span>💾</span>
            <span className="flex-1" style={{ color: 'var(--text-secondary)' }}>Backups</span>
            <span className="dot-unknown" />
          </div>
          <div className="flex gap-1.5 pt-1">
            <span
              className="text-[9px] px-1 py-0.5 rounded font-mono"
              style={{
                background: hasGrok ? 'rgba(34,197,94,0.12)' : 'var(--elevated)',
                color: hasGrok ? '#22c55e' : 'var(--text-muted)',
                border: `1px solid ${hasGrok ? 'rgba(34,197,94,0.2)' : 'var(--border)'}`,
              }}
            >
              Grok {hasGrok ? '✓' : '✗'}
            </span>
            <span
              className="text-[9px] px-1 py-0.5 rounded font-mono"
              style={{
                background: hasClaude ? 'rgba(139,92,246,0.12)' : 'var(--elevated)',
                color: hasClaude ? '#8B5CF6' : 'var(--text-muted)',
                border: `1px solid ${hasClaude ? 'var(--purple-border)' : 'var(--border)'}`,
              }}
            >
              Claude {hasClaude ? '✓' : '✗'}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
