'use client';
import { ServiceHealth, SystemStats } from '@/lib/types';

const SERVICES = [
  { key: 'backend',       label: 'FastAPI Backend', port: 8000, icon: '⚡' },
  { key: 'workroomforge', label: 'WorkroomForge',   port: 3001, icon: '🪡' },
  { key: 'luxeforge',     label: 'LuxeForge',       port: 3002, icon: '💎' },
  { key: 'homepage',      label: 'Homepage',        port: 8080, icon: '🏠' },
  { key: 'openclaw',      label: 'OpenClaw AI',     port: 7878, icon: '🧠' },
  { key: 'ollama',        label: 'Ollama',          port: 11434,icon: '🦙' },
] as const;

function StatBar({ label, value, extra }: { label: string; value: number; extra?: string }) {
  const color = value > 80 ? '#ef4444' : value > 60 ? '#f59e0b' : '#22c55e';
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ color: 'var(--text-primary)' }}>{extra || `${value}%`}</span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--elevated)' }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${value}%`, background: color }} />
      </div>
    </div>
  );
}

interface Props {
  systemStats: SystemStats | null;
  serviceHealth: ServiceHealth;
  backendOnline: boolean;
}

export default function SystemStatusPanel({ systemStats, serviceHealth, backendOnline }: Props) {
  const onlineCount = Object.values(serviceHealth).filter(Boolean).length;

  return (
    <div className="cc-panel">
      <div className="flex items-center justify-between mb-3">
        <p className="cc-panel-header mb-0">System Status</p>
        <div className="flex items-center gap-1.5">
          <span className={backendOnline ? 'dot-online' : 'dot-offline'} />
          <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
            {onlineCount}/{SERVICES.length}
          </span>
        </div>
      </div>

      {/* Resource bars */}
      {systemStats && (
        <div className="space-y-2.5 mb-4">
          <StatBar label="CPU" value={systemStats.cpu.percent} />
          <StatBar
            label="RAM"
            value={systemStats.memory.percent}
            extra={`${systemStats.memory.used_gb}/${systemStats.memory.total_gb} GB`}
          />
          <StatBar
            label="Disk"
            value={systemStats.disk.percent}
            extra={`${systemStats.disk.used_gb}/${systemStats.disk.total_gb} GB`}
          />
          {Object.entries(systemStats.temperatures).slice(0, 2).map(([name, sensors]) =>
            sensors.slice(0, 1).map((s, i) => (
              <div key={name + i} className="flex justify-between text-xs">
                <span style={{ color: 'var(--text-secondary)' }}>{s.label || name}</span>
                <span style={{ color: s.current > 80 ? '#ef4444' : s.current > 65 ? '#f59e0b' : '#22c55e' }}>
                  {s.current.toFixed(0)}°C
                </span>
              </div>
            ))
          )}
        </div>
      )}

      {!systemStats && (
        <p className="text-xs text-center py-3 mb-3" style={{ color: 'var(--text-muted)' }}>
          {backendOnline ? 'Loading stats...' : 'Backend offline'}
        </p>
      )}

      {/* Services */}
      <div className="space-y-1.5">
        {SERVICES.map(svc => {
          const online = serviceHealth[svc.key as keyof ServiceHealth];
          return (
            <div key={svc.key} className="flex items-center gap-2">
              <span className="text-sm">{svc.icon}</span>
              <span
                className="flex-1 text-xs truncate"
                style={{ color: online ? 'var(--text-primary)' : 'var(--text-muted)' }}
              >
                {svc.label}
              </span>
              <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>
                :{svc.port}
              </span>
              <span className={online ? 'dot-online' : 'dot-offline'} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
