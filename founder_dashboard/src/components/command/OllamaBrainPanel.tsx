'use client';
import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { BrainStatus } from '@/lib/types';

interface Props {
  brainStatus: BrainStatus | null;
  backendOnline: boolean;
}

export default function OllamaBrainPanel({ brainStatus, backendOnline }: Props) {
  const [open, setOpen] = useState(false);

  const ollamaOnline = brainStatus?.ollama?.online ?? false;
  const brainOnline = brainStatus?.brain_online ?? false;
  const memoryCount = brainStatus?.memories?.total ?? 0;
  const isExternal = brainStatus?.storage?.external_drive ?? false;
  const modelCount = brainStatus?.ollama?.models?.length ?? 0;
  const activeConvos = brainStatus?.conversations?.active ?? 0;

  const summaryColor = !backendOnline
    ? 'var(--text-muted)'
    : brainOnline ? 'var(--text-secondary)' : '#f59e0b';

  const summary = !backendOnline
    ? 'Backend offline'
    : brainOnline
      ? `Ollama ${modelCount} models | ${memoryCount} memories${isExternal ? ' | BACKUP11' : ''}`
      : ollamaOnline
        ? `Ollama up | Brain offline`
        : 'Ollama offline';

  return (
    <div className="cc-panel" style={{ padding: '8px 10px' }}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2"
      >
        <span className={brainOnline ? 'dot-online' : ollamaOnline ? 'dot-warning' : 'dot-offline'} />
        <span className="flex-1 text-[11px] font-mono text-left truncate" style={{ color: summaryColor }}>
          {summary}
        </span>
        {open
          ? <ChevronDown className="w-3 h-3 shrink-0" style={{ color: 'var(--text-muted)' }} />
          : <ChevronRight className="w-3 h-3 shrink-0" style={{ color: 'var(--text-muted)' }} />
        }
      </button>

      {open && brainStatus && (
        <div className="mt-2 pt-2 space-y-2" style={{ borderTop: '1px solid var(--border)' }}>
          {/* Ollama Status */}
          <div className="flex items-center gap-2 text-[10px]">
            <span>🦙</span>
            <span className="flex-1" style={{ color: 'var(--text-secondary)' }}>Ollama :11434</span>
            <span className={ollamaOnline ? 'dot-online' : 'dot-offline'} />
          </div>

          {/* Brain Storage */}
          <div className="flex items-center gap-2 text-[10px]">
            <span>🧠</span>
            <span className="flex-1" style={{ color: 'var(--text-secondary)' }}>
              Brain {isExternal ? '(BACKUP11)' : '(local)'}
            </span>
            <span className={brainOnline ? 'dot-online' : 'dot-offline'} />
          </div>

          {/* Memory count */}
          <div className="flex items-center gap-2 text-[10px]">
            <span>💾</span>
            <span className="flex-1" style={{ color: 'var(--text-secondary)' }}>Memories</span>
            <span style={{ color: 'var(--gold)', fontFamily: "'JetBrains Mono', monospace" }}>{memoryCount}</span>
          </div>

          {/* Active conversations */}
          {activeConvos > 0 && (
            <div className="flex items-center gap-2 text-[10px]">
              <span>💬</span>
              <span className="flex-1" style={{ color: 'var(--text-secondary)' }}>Active convos</span>
              <span style={{ color: 'var(--cyan)', fontFamily: "'JetBrains Mono', monospace" }}>{activeConvos}</span>
            </div>
          )}

          {/* Ollama Models */}
          {brainStatus.ollama.models.length > 0 && (
            <div className="flex gap-1.5 pt-1 flex-wrap">
              {brainStatus.ollama.models.map(model => (
                <span
                  key={model}
                  className="text-[9px] px-1.5 py-0.5 rounded font-mono"
                  style={{
                    background: 'rgba(34,197,94,0.12)',
                    color: '#22c55e',
                    border: '1px solid rgba(34,197,94,0.2)',
                  }}
                >
                  {model}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
