'use client';
import { ServiceHealth } from '@/lib/types';

const FORGES = [
  { key: 'workroomforge' as const, name: 'WorkroomForge', icon: '🪡', port: 3001 },
  { key: 'luxeforge'     as const, name: 'LuxeForge',     icon: '💎', port: 3002 },
];

interface Props {
  serviceHealth: ServiceHealth;
}

export default function ForgePanel({ serviceHealth }: Props) {
  return (
    <div className="cc-panel" style={{ padding: '8px 10px' }}>
      <div className="flex gap-2">
        {FORGES.map(f => {
          const online = serviceHealth[f.key];
          return (
            <a
              key={f.key}
              href={online ? `http://localhost:${f.port}` : undefined}
              target="_blank"
              rel="noreferrer"
              className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-lg text-[11px] font-medium transition"
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
    </div>
  );
}
