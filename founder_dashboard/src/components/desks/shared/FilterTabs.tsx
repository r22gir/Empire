'use client';

interface FilterTabsProps {
  options: string[];
  active: string;
  onChange: (val: string) => void;
  formatLabel?: (val: string) => string;
}

export default function FilterTabs({ options, active, onChange, formatLabel }: FilterTabsProps) {
  return (
    <div className="flex gap-1 px-4 pt-3 pb-2 shrink-0">
      {options.map(opt => (
        <button
          key={opt}
          onClick={() => onChange(opt)}
          className="px-3 py-1.5 rounded-lg text-xs font-medium transition capitalize"
          style={{
            background: active === opt ? 'var(--gold-pale)' : 'transparent',
            color: active === opt ? 'var(--gold)' : 'var(--text-muted)',
            border: active === opt ? '1px solid var(--gold-border)' : '1px solid transparent',
          }}
        >
          {formatLabel ? formatLabel(opt) : opt.replace(/_/g, ' ')}
        </button>
      ))}
    </div>
  );
}
