'use client';
import { useState } from 'react';
import { ServiceHealth, SystemStats } from '@/lib/types';
import { ChevronDown, ChevronRight } from 'lucide-react';

const SERVICES = [
  { key: 'backend',       label: 'API',  port: 8000, icon: '⚡' },
  { key: 'workroomforge', label: 'WF',   port: 3001, icon: '🪡' },
  { key: 'luxeforge',     label: 'LX',   port: 3002, icon: '💎' },
  { key: 'homepage',      label: 'HP',   port: 8080, icon: '🏠' },
] as const;

interface Props {
  systemStats: SystemStats | null;
  serviceHealth: ServiceHealth;
  backendOnline: boolean;
}

export default function SystemStatusPanel({ systemStats, serviceHealth, backendOnline }: Props) {
  const [open, setOpen] = useState(false);
  const s = systemStats;
  const temp = s ? Object.values(s.temperatures).flat()[0]?.current : null;

  const summary = s
    ? `CPU ${s.cpu.percent}% | RAM ${s.memory.used_gb}/${s.memory.total_gb}G | Disk ${s.disk.used_gb}/${s.disk.total_gb}G${temp ? ` | ${temp.toFixed(0)}°C` : ''}`
    : backendOnline ? 'Loading...' : 'Backend offline';

  const summaryColor = !s
    ? 'var(--text-muted)'
    : s.cpu.percent > 80 || s.memory.percent > 80 ? '#f59e0b' : 'var(--text-secondary)';

  return (
    <div className="cc-panel" style={{ padding: '8px 10px' }}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2"
      >
        <span className={backendOnline ? 'dot-online' : 'dot-offline'} />
        <span className="flex-1 text-[11px] font-mono text-left truncate" style={{ color: summaryColor }}>
          {summary}
        </span>
        {open
          ? <ChevronDown className="w-3 h-3 shrink-0" style={{ color: 'var(--text-muted)' }} />
          : <ChevronRight className="w-3 h-3 shrink-0" style={{ color: 'var(--text-muted)' }} />
        }
      </button>

      {open && (
        <div className="mt-2 pt-2 space-y-2" style={{ borderTop: '1px solid var(--border)' }}>
          {s && (
            <>
              {[
                { label: 'CPU', value: s.cpu.percent, extra: `${s.cpu.percent}%` },
                { label: 'RAM', value: s.memory.percent, extra: `${s.memory.used_gb}/${s.memory.total_gb} GB` },
                { label: 'Disk', value: s.disk.percent, extra: `${s.disk.used_gb}/${s.disk.total_gb} GB` },
              ].map(bar => (
                <div key={bar.label}>
                  <div className="flex justify-between text-[10px] mb-0.5">
                    <span style={{ color: 'var(--text-secondary)' }}>{bar.label}</span>
                    <span style={{ color: 'var(--text-primary)' }}>{bar.extra}</span>
                  </div>
                  <div className="h-1 rounded-full overflow-hidden" style={{ background: 'var(--elevated)' }}>
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${bar.value}%`,
                        background: bar.value > 80 ? '#ef4444' : bar.value > 60 ? '#f59e0b' : '#22c55e',
                      }}
                    />
                  </div>
                </div>
              ))}
            </>
          )}
          <div className="flex gap-2 flex-wrap">
            {SERVICES.map(svc => {
              const online = serviceHealth[svc.key as keyof ServiceHealth];
              return (
                <span key={svc.key} className="flex items-center gap-1 text-[10px]" style={{ color: 'var(--text-muted)' }}>
                  {svc.icon}<span className={online ? 'dot-online' : 'dot-offline'} />
                </span>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
