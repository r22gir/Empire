'use client';
import { ServiceHealth, AIModel } from '@/lib/types';
import { Shield, Server, GitBranch, Key, HardDrive } from 'lucide-react';

interface Props {
  serviceHealth: ServiceHealth;
  backendOnline: boolean;
  models: AIModel[];
}

export default function EmpireBoxPanel({ serviceHealth, backendOnline, models }: Props) {
  const cloudModels = models.filter(m => m.available && m.id !== 'ollama');
  const hasGrok = models.some(m => m.id === 'grok' && m.available);
  const hasClaude = models.some(m => m.id === 'claude' && m.available);
  const hasOllama = serviceHealth.ollama;

  return (
    <div className="cc-panel">
      <div className="flex items-center gap-2 mb-3">
        <Shield className="w-3.5 h-3.5" style={{ color: 'var(--gold)' }} />
        <p className="cc-panel-header mb-0">Empire Box</p>
      </div>

      <div className="space-y-2">
        {/* Server */}
        <div
          className="flex items-center gap-2.5 p-2.5 rounded-lg"
          style={{ background: 'var(--raised)' }}
        >
          <Server className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>Empire Server</p>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>FastAPI :8000</p>
          </div>
          <span className={backendOnline ? 'dot-online' : 'dot-offline'} />
        </div>

        {/* Backups */}
        <div
          className="flex items-center gap-2.5 p-2.5 rounded-lg"
          style={{ background: 'var(--raised)' }}
        >
          <HardDrive className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>Backups</p>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>Last: --</p>
          </div>
          <span className="dot-unknown" />
        </div>

        {/* Git */}
        <div
          className="flex items-center gap-2.5 p-2.5 rounded-lg"
          style={{ background: 'var(--raised)' }}
        >
          <GitBranch className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>Repository</p>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>~/Empire</p>
          </div>
          <span className="dot-online" />
        </div>

        {/* API Keys */}
        <div
          className="flex items-center gap-2.5 p-2.5 rounded-lg"
          style={{ background: 'var(--raised)' }}
        >
          <Key className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>API Keys</p>
            <div className="flex gap-1.5 mt-1">
              <span
                className="text-[10px] px-1.5 py-0.5 rounded"
                style={{
                  background: hasGrok ? 'rgba(34,197,94,0.12)' : 'var(--elevated)',
                  color: hasGrok ? '#22c55e' : 'var(--text-muted)',
                  border: `1px solid ${hasGrok ? 'rgba(34,197,94,0.2)' : 'var(--border)'}`,
                }}
              >
                Grok {hasGrok ? '✓' : '✗'}
              </span>
              <span
                className="text-[10px] px-1.5 py-0.5 rounded"
                style={{
                  background: hasClaude ? 'rgba(139,92,246,0.12)' : 'var(--elevated)',
                  color: hasClaude ? '#8B5CF6' : 'var(--text-muted)',
                  border: `1px solid ${hasClaude ? 'var(--purple-border)' : 'var(--border)'}`,
                }}
              >
                Claude {hasClaude ? '✓' : '✗'}
              </span>
              <span
                className="text-[10px] px-1.5 py-0.5 rounded"
                style={{
                  background: hasOllama ? 'rgba(34,211,238,0.12)' : 'var(--elevated)',
                  color: hasOllama ? '#22D3EE' : 'var(--text-muted)',
                  border: `1px solid ${hasOllama ? 'rgba(34,211,238,0.2)' : 'var(--border)'}`,
                }}
              >
                Ollama {hasOllama ? '✓' : '✗'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
