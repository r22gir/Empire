'use client';
import { useState, useEffect } from 'react';
import { Server, Cpu, HardDrive, Activity, RefreshCw } from 'lucide-react';
import { StatsBar, TaskList } from './shared';

interface ServiceStatus { name: string; port: number; status: 'online' | 'offline' | 'checking'; latency?: number }

const SERVICES: Omit<ServiceStatus, 'status'>[] = [
  { name: 'Command Center', port: 3009 },
  { name: 'WorkroomForge', port: 3001 },
  { name: 'LuxeForge', port: 3002 },
  { name: 'FastAPI Backend', port: 8000 },
  { name: 'Homepage', port: 8080 },
  { name: 'Ollama', port: 11434 },
];

export default function ITDesk() {
  const [services, setServices] = useState<ServiceStatus[]>(
    SERVICES.map(s => ({ ...s, status: 'checking' }))
  );
  const [refreshing, setRefreshing] = useState(false);

  const checkServices = async () => {
    setRefreshing(true);
    const results = await Promise.all(
      SERVICES.map(async (svc) => {
        const start = Date.now();
        try {
          await fetch(`http://localhost:${svc.port}`, { mode: 'no-cors', signal: AbortSignal.timeout(3000) });
          return { ...svc, status: 'online' as const, latency: Date.now() - start };
        } catch {
          return { ...svc, status: 'offline' as const };
        }
      })
    );
    setServices(results);
    setRefreshing(false);
  };

  useEffect(() => { checkServices(); }, []);

  const online = services.filter(s => s.status === 'online').length;
  const offline = services.filter(s => s.status === 'offline').length;

  return (
    <div className="flex flex-col h-full">
      <StatsBar
        items={[
          { label: 'Services Online', value: `${online}/${services.length}`, icon: Activity, color: '#22c55e' },
          { label: 'Offline', value: String(offline), icon: Server, color: offline > 0 ? '#ef4444' : 'var(--text-muted)' },
          { label: 'Switchboard Limit', value: '3 servers', icon: Cpu, color: '#6366F1' },
        ]}
        rightSlot={
          <button
            onClick={checkServices}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition shrink-0"
            style={{ background: 'var(--raised)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
          >
            <RefreshCw className={`w-3 h-3 ${refreshing ? 'animate-spin' : ''}`} /> Refresh
          </button>
        }
      />

      <div className="flex-1 overflow-auto p-4 flex gap-4">
        <div className="flex-1 flex flex-col gap-4">
          <div className="space-y-2">
            {services.map(svc => (
              <div
                key={svc.port}
                className="rounded-xl p-4 flex items-center gap-4"
                style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
              >
                <span
                  className="w-3 h-3 rounded-full shrink-0"
                  style={{
                    background: svc.status === 'online' ? '#22c55e' : svc.status === 'offline' ? '#ef4444' : '#f59e0b',
                    boxShadow: svc.status === 'online' ? '0 0 8px rgba(34,197,94,0.4)' : 'none',
                  }}
                />
                <div className="flex-1">
                  <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{svc.name}</p>
                  <p className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>localhost:{svc.port}</p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  {svc.latency !== undefined && (
                    <span className="text-xs font-mono" style={{ color: svc.latency < 100 ? '#22c55e' : '#f59e0b' }}>
                      {svc.latency}ms
                    </span>
                  )}
                  <span
                    className="px-2 py-0.5 rounded-full text-[10px] font-semibold capitalize"
                    style={{
                      background: svc.status === 'online' ? 'rgba(34,197,94,0.12)' : svc.status === 'offline' ? 'rgba(239,68,68,0.12)' : 'rgba(245,158,11,0.12)',
                      color: svc.status === 'online' ? '#22c55e' : svc.status === 'offline' ? '#ef4444' : '#f59e0b',
                    }}
                  >
                    {svc.status}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* System info */}
          <div className="rounded-xl p-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <h3 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: 'var(--gold)' }}>System Info</h3>
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'Platform', value: 'EmpireBox Mini PC', icon: Server },
                { label: 'Storage', value: '457 GB NVMe + 1TB External', icon: HardDrive },
                { label: 'CPU', value: 'AMD Ryzen 7 5825U', icon: Cpu },
              ].map(item => (
                <div key={item.label} className="rounded-lg p-3" style={{ background: 'var(--raised)' }}>
                  <item.icon className="w-4 h-4 mb-2" style={{ color: '#6366F1' }} />
                  <p className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>{item.value}</p>
                  <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{item.label}</p>
                </div>
              ))}
            </div>
          </div>

          <TaskList desk="it" compact />
        </div>
      </div>
    </div>
  );
}
