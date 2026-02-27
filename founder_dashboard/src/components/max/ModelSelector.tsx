'use client';
import { Cpu } from 'lucide-react';
import { AIModel } from '@/lib/types';

interface ModelSelectorProps {
  models: AIModel[];
  selectedModel: string;
  onSelect: (model: string) => void;
}

export default function ModelSelector({ models, selectedModel, onSelect }: ModelSelectorProps) {
  return (
    <div className="flex items-center gap-2">
      <Cpu className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--purple)' }} />
      <select
        value={selectedModel}
        onChange={e => onSelect(e.target.value)}
        className="flex-1 text-xs rounded-lg px-2 py-1.5 appearance-none cursor-pointer outline-none transition"
        style={{
          background: 'var(--raised)',
          color: 'var(--gold)',
          border: '1px solid var(--border)',
          fontFamily: "'JetBrains Mono', monospace",
        }}
      >
        {models.map(m => (
          <option key={m.id} value={m.id}>
            {m.available ? '◆' : '◇'} {m.name}{m.primary ? ' ✦' : ''}
          </option>
        ))}
        {models.length === 0 && <option value="claude">◇ Claude 4.6 Sonnet</option>}
      </select>
    </div>
  );
}
