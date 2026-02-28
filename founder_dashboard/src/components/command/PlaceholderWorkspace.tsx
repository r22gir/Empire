'use client';
import { ArrowLeft, Sparkles } from 'lucide-react';
import { EmpireApp } from './WorkspaceOverview';

interface Props {
  app: EmpireApp;
  onBack: () => void;
}

export default function PlaceholderWorkspace({ app, onBack }: Props) {
  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      {/* Header */}
      <div className="shrink-0 flex items-center gap-3 px-4 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition"
          style={{ background: 'var(--raised)', color: 'var(--text-primary)', border: '1px solid var(--border)' }}
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back
        </button>
        <span className="text-xl">{app.icon}</span>
        <h2 className="text-sm font-semibold" style={{ color: app.color }}>{app.name}</h2>
        <span
          className="px-2 py-0.5 rounded text-[9px] font-bold uppercase"
          style={{ background: `${app.color}15`, color: app.color, border: `1px solid ${app.color}30` }}
        >
          Coming Soon
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <span className="text-5xl block mb-4">{app.icon}</span>
          <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>{app.name}</h3>
          <p className="text-sm mb-6" style={{ color: 'var(--text-muted)' }}>{app.description}</p>

          {app.features && app.features.length > 0 && (
            <div className="text-left rounded-xl p-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-4 h-4" style={{ color: app.color }} />
                <h4 className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
                  Planned Features
                </h4>
              </div>
              <div className="space-y-2">
                {app.features.map(f => (
                  <div key={f} className="flex items-center gap-2.5 text-sm" style={{ color: 'var(--text-secondary)' }}>
                    <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: app.color, opacity: 0.6 }} />
                    {f}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
