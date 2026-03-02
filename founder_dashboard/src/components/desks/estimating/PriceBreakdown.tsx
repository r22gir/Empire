'use client';
import { useState } from 'react';
import { DollarSign, FileText, ExternalLink, Loader2 } from 'lucide-react';
import { type QuoteCalc } from './useQuoteCalc';
import { API_URL } from '@/lib/api';

const fmt = (n: number) => '$' + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

interface PriceBreakdownProps {
  calc: QuoteCalc;
  windowCount: number;
  treatment?: string;
  fabricGrade?: string;
  windowWidth?: number;
  windowHeight?: number;
}

export default function PriceBreakdown({ calc, windowCount, treatment, fabricGrade, windowWidth, windowHeight }: PriceBreakdownProps) {
  const [generating, setGenerating] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [error, setError] = useState('');

  const generateQuote = async () => {
    setGenerating(true);
    setError('');
    try {
      const res = await fetch(API_URL + '/quotes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer_name: 'Walk-in Estimate',
          rooms: [{
            name: 'Estimate',
            windows: Array.from({ length: windowCount }, (_, i) => ({
              name: `Window ${i + 1}`,
              width: windowWidth || 72,
              height: windowHeight || 84,
              treatment: treatment || 'drapes',
              fabric_grade: fabricGrade || 'Standard',
              quantity: 1,
            })),
          }],
        }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.pdf_url) {
          setPdfUrl(API_URL.replace('/api/v1', '') + data.pdf_url);
        }
      } else {
        setError('Failed to generate PDF');
      }
    } catch {
      setError('Backend offline — start backend first');
    } finally {
      setGenerating(false);
    }
  };

  const openInWorkroomForge = () => {
    const params = new URLSearchParams({
      treatment: treatment || 'drapes',
      width: String(windowWidth || 72),
      height: String(windowHeight || 84),
      grade: fabricGrade || 'Standard',
      windows: String(windowCount),
    });
    window.open(`http://localhost:3001?${params.toString()}`, '_blank');
  };

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

      {/* Action Buttons */}
      <div className="flex flex-col gap-2">
        <button
          onClick={generateQuote}
          disabled={generating}
          className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition"
          style={{
            background: generating ? 'var(--elevated)' : 'var(--gold)',
            color: generating ? 'var(--text-muted)' : '#0a0a0a',
            border: '1px solid var(--gold-border)',
          }}
        >
          {generating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
          {generating ? 'Generating...' : 'Generate Quote PDF'}
        </button>
        <button
          onClick={openInWorkroomForge}
          className="flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-xs font-medium transition"
          style={{
            background: 'var(--raised)',
            color: 'var(--cyan)',
            border: '1px solid var(--cyan-border)',
          }}
        >
          <ExternalLink className="w-3.5 h-3.5" />
          Open in WorkroomForge
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="px-3 py-2 rounded-lg text-[10px]" style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.2)' }}>
          {error}
        </div>
      )}

      {/* Inline PDF Preview */}
      {pdfUrl && (
        <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
          <div className="flex items-center justify-between px-3 py-2" style={{ background: 'var(--raised)', borderBottom: '1px solid var(--border)' }}>
            <span className="text-[10px] font-semibold" style={{ color: 'var(--gold)' }}>Quote Preview</span>
            <div className="flex gap-2">
              <a href={pdfUrl} target="_blank" rel="noreferrer" className="text-[10px]" style={{ color: 'var(--cyan)' }}>Open</a>
              <button onClick={() => setPdfUrl(null)} className="text-[10px]" style={{ color: 'var(--text-muted)' }}>Close</button>
            </div>
          </div>
          <iframe src={pdfUrl} className="w-full" style={{ height: 300, background: '#fff' }} />
        </div>
      )}
    </div>
  );
}
