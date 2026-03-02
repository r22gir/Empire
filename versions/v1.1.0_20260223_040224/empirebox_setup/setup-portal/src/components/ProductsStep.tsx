'use client';

import { useState } from 'react';

const PRODUCTS = [
  { id: 'marketforge',     name: 'MarketForge',      size: '850MB', desc: 'Marketplace management' },
  { id: 'supportforge',    name: 'SupportForge',     size: '420MB', desc: 'Customer support' },
  { id: 'contractorforge', name: 'ContractorForge',  size: '680MB', desc: 'Contractor business' },
  { id: 'luxeforge',       name: 'LuxeForge',        size: '520MB', desc: 'Custom workroom' },
  { id: 'leadforge',       name: 'LeadForge',        size: '380MB', desc: 'Lead generation' },
  { id: 'shipforge',       name: 'ShipForge',        size: '290MB', desc: 'Shipping management' },
  { id: 'forgecrm',        name: 'ForgeCRM',         size: '450MB', desc: 'Customer relationships' },
  { id: 'relistapp',       name: 'RelistApp',        size: '180MB', desc: 'Cross-listing tool' },
  { id: 'socialforge',     name: 'SocialForge',      size: '340MB', desc: 'Social media' },
  { id: 'llcfactory',      name: 'LLCFactory',       size: '220MB', desc: 'Business formation' },
  { id: 'apostapp',        name: 'ApostApp',         size: '190MB', desc: 'Document apostille' },
  { id: 'empireassist',    name: 'EmpireAssist',     size: '310MB', desc: 'AI assistant' },
];

interface Props {
  state: { selectedProducts: string[] };
  onUpdate: (patch: { selectedProducts: string[] }) => void;
  onNext: () => void;
  onPrev: () => void;
}

export default function ProductsStep({ state, onUpdate, onNext, onPrev }: Props) {
  const [selected, setSelected] = useState<Set<string>>(new Set(state.selectedProducts));
  const [error, setError] = useState('');

  const toggle = (id: string) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    setSelected(next);
    setError('');
  };

  const handleNext = () => {
    if (selected.size === 0) {
      setError('Please select at least one product.');
      return;
    }
    onUpdate({ selectedProducts: Array.from(selected) });
    onNext();
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-1">Products</h2>
      <p className="text-gray-400 mb-4 text-sm">Select the products to install ({selected.size} selected)</p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mb-4 max-h-80 overflow-y-auto pr-1">
        {PRODUCTS.map((p) => (
          <button
            key={p.id}
            onClick={() => toggle(p.id)}
            className={`flex items-start gap-3 p-3 rounded-lg border text-left transition-colors ${
              selected.has(p.id)
                ? 'border-gold bg-gold/10'
                : 'border-white/10 hover:border-white/30'
            }`}
            style={selected.has(p.id) ? { borderColor: '#C9A84C', backgroundColor: '#C9A84C22' } : {}}
          >
            <div
              className={`mt-0.5 w-4 h-4 rounded flex-shrink-0 flex items-center justify-center text-xs ${
                selected.has(p.id) ? 'bg-gold text-charcoal' : 'border border-white/30'
              }`}
              style={selected.has(p.id) ? { backgroundColor: '#C9A84C', color: '#2C2C2C' } : {}}
            >
              {selected.has(p.id) && '✓'}
            </div>
            <div>
              <div className="font-medium text-sm">{p.name}</div>
              <div className="text-gray-500 text-xs">{p.desc} · {p.size}</div>
            </div>
          </button>
        ))}
      </div>

      {error && <p className="text-red-400 text-sm mb-3">{error}</p>}

      <div className="flex gap-3">
        <button onClick={onPrev} className="flex-1 py-3 rounded-lg bg-white/10 text-white font-medium">
          Back
        </button>
        <button
          onClick={handleNext}
          className="flex-1 py-3 rounded-lg font-semibold transition-opacity hover:opacity-90"
          style={{ backgroundColor: '#C9A84C', color: '#2C2C2C' }}
        >
          Continue
        </button>
      </div>
    </div>
  );
}
