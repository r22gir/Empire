'use client';

import { useState } from 'react';

const AI_MODELS = [
  { id: 'llama3.1:8b',       name: 'Llama 3.1 8B',        size: '4.7GB',  desc: 'General purpose',      recommended: true },
  { id: 'llama3.1:70b',      name: 'Llama 3.1 70B',       size: '40GB',   desc: 'Maximum quality (needs 64GB+ RAM)', recommended: false },
  { id: 'codellama:7b',      name: 'CodeLlama 7B',        size: '3.8GB',  desc: 'Code generation',      recommended: true },
  { id: 'mistral:7b',        name: 'Mistral 7B',          size: '4.1GB',  desc: 'Fast and efficient',   recommended: false },
  { id: 'nomic-embed-text',  name: 'Nomic Embed Text',    size: '274MB',  desc: 'Text embeddings',      recommended: true },
];

interface Props {
  state: { selectedModels: string[] };
  onUpdate: (patch: { selectedModels: string[] }) => void;
  onNext: () => void;
  onPrev: () => void;
}

export default function AIModelsStep({ state, onUpdate, onNext, onPrev }: Props) {
  const [selected, setSelected] = useState<Set<string>>(
    new Set(state.selectedModels.length ? state.selectedModels : AI_MODELS.filter((m) => m.recommended).map((m) => m.id))
  );

  const toggle = (id: string) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
  };

  const handleNext = () => {
    onUpdate({ selectedModels: Array.from(selected) });
    onNext();
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-1">AI Models</h2>
      <p className="text-gray-400 mb-4 text-sm">Choose Ollama models to download ({selected.size} selected)</p>

      <div className="space-y-2 mb-6">
        {AI_MODELS.map((m) => (
          <button
            key={m.id}
            onClick={() => toggle(m.id)}
            className={`w-full flex items-center gap-3 p-3 rounded-lg border text-left transition-colors ${
              selected.has(m.id) ? 'border-gold bg-gold/10' : 'border-white/10 hover:border-white/30'
            }`}
            style={selected.has(m.id) ? { borderColor: '#C9A84C', backgroundColor: '#C9A84C22' } : {}}
          >
            <div
              className={`w-4 h-4 rounded flex-shrink-0 flex items-center justify-center text-xs ${
                selected.has(m.id) ? 'bg-gold text-charcoal' : 'border border-white/30'
              }`}
              style={selected.has(m.id) ? { backgroundColor: '#C9A84C', color: '#2C2C2C' } : {}}
            >
              {selected.has(m.id) && '✓'}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{m.name}</span>
                {m.recommended && (
                  <span className="text-xs px-2 py-0.5 rounded-full" style={{ backgroundColor: '#C9A84C33', color: '#C9A84C' }}>
                    Recommended
                  </span>
                )}
              </div>
              <div className="text-gray-500 text-xs">{m.desc} · {m.size}</div>
            </div>
          </button>
        ))}
      </div>

      <div className="flex gap-3">
        <button onClick={onPrev} className="flex-1 py-3 rounded-lg bg-white/10 text-white font-medium">
          Back
        </button>
        <button
          onClick={handleNext}
          className="flex-1 py-3 rounded-lg font-semibold transition-opacity hover:opacity-90"
          style={{ backgroundColor: '#C9A84C', color: '#2C2C2C' }}
        >
          Start Install
        </button>
      </div>
    </div>
  );
}
