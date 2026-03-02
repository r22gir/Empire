'use client';
import { ServiceHealth } from '@/lib/types';

const FORGES = [
  { key: 'workroomforge' as const, name: 'WorkroomForge', icon: '🪡', port: 3001 },
  { key: 'luxeforge'     as const, name: 'LuxeForge',     icon: '💎', port: 3002 },
  { key: 'amp'           as const, name: 'AMP',            icon: '📢', port: 3003 },
  { key: 'socialforge'   as const, name: 'SocialForge',    icon: '🌐', port: 3004 },
];

const DEVICES = [
  { name: 'Beelink',      icon: '🖥️', status: 'active' as const },
  { name: 'Solana Phone',  icon: '📱', status: 'planned' as const },
];

interface Props {
  serviceHealth: ServiceHealth;
}

export default function ForgePanel({ serviceHealth }: Props) {
  return (
    <div className="cc-panel" style={{ padding: '8px 10px' }}>
      {/* Empire Apps */}
      <div className="grid grid-cols-2 gap-1.5">
        {FORGES.map(f => {
          const online = serviceHealth[f.key];
          return (
            <a
              key={f.key}
              href={online ? `http://localhost:${f.port}` : undefined}
              target="_blank"
              rel="noreferrer"
              className="flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-[10px] font-medium transition"
              style={{
                background: 'var(--raised)',
                color: online ? 'var(--text-primary)' : 'var(--text-muted)',
                border: '1px solid var(--border)',
                cursor: online ? 'pointer' : 'default',
                opacity: online ? 1 : 0.6,
                textDecoration: 'none',
              }}
              onMouseEnter={e => { if (online) e.currentTarget.style.borderColor = 'var(--gold-border)'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; }}
            >
              {f.icon} {f.name.replace('Forge', '')}
              <span className={online ? 'dot-online' : 'dot-offline'} />
            </a>
          );
        })}
      </div>

      {/* Devices */}
      <div className="mt-2 pt-2" style={{ borderTop: '1px solid var(--border)' }}>
        <p className="text-[9px] font-semibold mb-1.5" style={{ color: 'var(--text-muted)', letterSpacing: '0.05em' }}>DEVICES</p>
        <div className="flex gap-1.5">
          {DEVICES.map(d => (
            <div
              key={d.name}
              className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-[10px] font-medium"
              style={{
                background: 'var(--raised)',
                color: d.status === 'active' ? 'var(--text-primary)' : 'var(--text-muted)',
                border: '1px solid var(--border)',
                opacity: d.status === 'active' ? 1 : 0.5,
              }}
            >
              {d.icon} {d.name}
              <span className={d.status === 'active' ? 'dot-online' : 'dot-unknown'} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
