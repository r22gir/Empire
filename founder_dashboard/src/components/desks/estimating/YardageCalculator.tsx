'use client';
import { Scissors } from 'lucide-react';
import { type QuoteCalc } from './useQuoteCalc';

interface YardageCalculatorProps {
  calc: QuoteCalc;
  windowCount: number;
  windowWidth: number;
  windowHeight: number;
  fullness: number;
}

export default function YardageCalculator({ calc, windowCount, windowWidth, windowHeight, fullness }: YardageCalculatorProps) {
  return (
    <div className="rounded-xl p-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      <div className="flex items-center gap-2 mb-3">
        <Scissors className="w-4 h-4" style={{ color: 'var(--purple)' }} />
        <p className="text-xs font-semibold" style={{ color: 'var(--gold)' }}>Yardage Calculator</p>
      </div>
      <div className="space-y-2">
        {[
          { label: 'Window Size', value: `${windowWidth}" × ${windowHeight}"` },
          { label: 'Fullness', value: `${fullness}× (${(windowWidth * fullness).toFixed(0)}" finished)` },
          { label: 'Panels per Window', value: String(calc.panelsNeeded) },
          { label: 'Yardage per Window', value: `${calc.yardagePerWindow} yd` },
          { label: `Base Yardage (×${windowCount})`, value: `${(calc.yardagePerWindow * windowCount).toFixed(1)} yd` },
          { label: 'Waste (+15%)', value: `${calc.wasteYardage} yd` },
        ].map(row => (
          <div key={row.label} className="flex justify-between items-center py-1.5" style={{ borderBottom: '1px solid var(--border)' }}>
            <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>{row.label}</span>
            <span className="text-xs font-mono" style={{ color: 'var(--text-primary)' }}>{row.value}</span>
          </div>
        ))}
        <div className="flex justify-between items-center pt-2">
          <span className="text-xs font-semibold" style={{ color: 'var(--gold)' }}>Total Yardage</span>
          <span className="text-sm font-bold font-mono" style={{ color: 'var(--gold)' }}>{calc.totalYardage} yd</span>
        </div>
      </div>
    </div>
  );
}
