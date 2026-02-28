'use client';
import { ServiceHealth } from '@/lib/types';
import { ExternalLink } from 'lucide-react';

interface Props {
  serviceHealth: ServiceHealth;
}

const FORGES = [
  {
    key: 'workroomforge' as const,
    name: 'WorkroomForge',
    desc: 'Quote builder & AI photo analysis',
    icon: '🪡',
    port: 3001,
  },
  {
    key: 'luxeforge' as const,
    name: 'LuxeForge',
    desc: 'Designer portal & marketplace',
    icon: '💎',
    port: 3002,
  },
];

export default function ForgePanel({ serviceHealth }: Props) {
  return (
    <div className="cc-panel">
      <p className="cc-panel-header">Workroom & Luxe Forge</p>
      <div className="space-y-2">
        {FORGES.map(forge => {
          const online = serviceHealth[forge.key];
          return (
            <a
              key={forge.key}
              href={online ? `http://localhost:${forge.port}` : undefined}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-3 p-3 rounded-xl transition-all group"
              style={{
                background: 'var(--raised)',
                border: '1px solid var(--border)',
                cursor: online ? 'pointer' : 'default',
                opacity: online ? 1 : 0.5,
                textDecoration: 'none',
              }}
              onMouseEnter={e => { if (online) { e.currentTarget.style.borderColor = 'var(--gold-border)'; e.currentTarget.style.background = 'var(--elevated)'; } }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.background = 'var(--raised)'; }}
            >
              <span className="text-2xl">{forge.icon}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{forge.name}</p>
                <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{forge.desc}</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>:{forge.port}</span>
                <span className={online ? 'dot-online' : 'dot-offline'} />
                {online && <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition" style={{ color: 'var(--gold)' }} />}
              </div>
            </a>
          );
        })}
      </div>
    </div>
  );
}
