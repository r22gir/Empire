'use client';
import { DollarSign, FileText } from 'lucide-react';
import { type QuoteCalc } from './useQuoteCalc';

const fmt = (n: number) => '$' + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

interface PriceBreakdownProps {
  calc: QuoteCalc;
  windowCount: number;
}

export default function PriceBreakdown({ calc, windowCount }: PriceBreakdownProps) {
  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-xl p-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
        <div className="flex items-center gap-2 mb-3">
          <DollarSign className="w-4 h-4" style={{ color: '#22c55e' }} />
          <p className="text-xs font-semibold" style={{ color: 'var(--gold)' }}>Price Breakdown</p>
        </div>
        <div className="space-y-2">
          {[
            { label: `Materials (${windowCount} windows)`, value: calc.materialsTotal },
            { label: `Labor (${windowCount} windows)`, value: calc.laborTotal },
            { label: `Hardware (${windowCount} windows)`, value: calc.hardwareTotal },
          ].map(row => (
            <div key={row.label} className="flex justify-between items-center py-1.5" style={{ borderBottom: '1px solid var(--border)' }}>
              <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>{row.label}</span>
              <span className="text-xs font-mono" style={{ color: 'var(--text-primary)' }}>{fmt(row.value)}</span>
            </div>
          ))}
          <div className="flex justify-between items-center py-1.5" style={{ borderBottom: '1px solid var(--border)' }}>
            <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>Subtotal</span>
            <span className="text-xs font-mono" style={{ color: 'var(--text-primary)' }}>{fmt(calc.subtotal)}</span>
          </div>
          <div className="flex justify-between items-center py-1.5" style={{ borderBottom: '1px solid var(--border)' }}>
            <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>Tax (8.25%)</span>
            <span className="text-xs font-mono" style={{ color: 'var(--text-primary)' }}>{fmt(calc.tax)}</span>
          </div>
          <div className="flex justify-between items-center pt-2">
            <span className="text-xs font-bold" style={{ color: 'var(--gold)' }}>TOTAL</span>
            <span className="text-lg font-bold font-mono" style={{ color: '#22c55e' }}>{fmt(calc.total)}</span>
          </div>
        </div>
      </div>

      <div className="rounded-xl p-4 flex flex-col items-center justify-center text-center flex-1"
        style={{ background: 'var(--surface)', border: '2px dashed var(--border)', minHeight: 120 }}>
        <FileText className="w-8 h-8 mb-2" style={{ color: 'var(--text-muted)' }} />
        <p className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Quote PDF Preview</p>
        <p className="text-[10px] mt-1" style={{ color: 'var(--text-muted)' }}>PDF generation coming soon</p>
        <button className="mt-3 px-4 py-1.5 rounded-lg text-[10px] font-semibold transition"
          style={{ background: 'var(--gold)', color: '#0a0a0a' }}>
          Generate Quote
        </button>
      </div>
    </div>
  );
}
