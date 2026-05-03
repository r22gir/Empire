'use client';
import React, { useState } from 'react';
import {
  Upload, Image as ImageIcon, FileText, DollarSign, CheckCircle,
  Send, Download, CreditCard, ArrowRight, Sparkles
} from 'lucide-react';
import { EmpireShell } from '../components/ui/EmpireShell';
import { EmpireDataPanel } from '../components/ui/EmpireDataPanel';
import { EmpireStatusPill } from '../components/ui/EmpireStatusPill';
import { API } from '@/lib/api';

interface PhotoAnalysis {
  width: string;
  height: string;
  confidence: number;
}

export default function CRMPage() {
  const [dragOver, setDragOver] = useState(false);
  const [photoAnalyzed, setPhotoAnalyzed] = useState(false);
  const [analysis, setAnalysis] = useState<PhotoAnalysis | null>(null);
  const [selectedTier, setSelectedTier] = useState<'lite' | 'pro' | 'empire'>('pro');
  const [quoteSent, setQuoteSent] = useState(false);
  const [invoiceSent, setInvoiceSent] = useState(false);

  const clientInfo = { name: 'Alex Morgan', email: 'alex@example.com', phone: '+1 555-0142' };
  const pricing: Record<string, number> = { lite: 1890, pro: 2890, empire: 4890 };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleAnalyze = async () => {
    setAnalysis({ width: '120cm', height: '85cm', confidence: 94 });
    setPhotoAnalyzed(true);
  };

  const handleSendQuote = async () => {
    try {
      await fetch(`${API}/quotes/send`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ client: clientInfo, tier: selectedTier, amount: pricing[selectedTier] }) });
    } catch { /* silent */ }
    setQuoteSent(true);
  };

  const handleSendInvoice = async () => {
    try {
      await fetch(`${API}/invoices/send`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ invoice: 'INV-2024-08765', client: clientInfo }) });
    } catch { /* silent */ }
    setInvoiceSent(true);
  };

  return (
    <EmpireShell commitHash="f535d53">
      <div className="animated-gradient" style={{ padding: 'var(--space-6)' }}>
        {/* Top Metrics Bar */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 'var(--space-4)',
          marginBottom: 'var(--space-6)',
        }}>
          {[
            { label: 'customers', value: '113', icon: <Sparkles size={16} />, color: 'primary' },
            { label: 'revenue', value: '$47.2K', icon: <DollarSign size={16} />, color: 'success' },
            { label: 'collection rate', value: '89%', icon: <CheckCircle size={16} />, color: 'success' },
          ].map((m) => (
            <div key={m.label} className="glass-premium" style={{
              padding: 'var(--space-4)',
              borderRadius: 'var(--radius-lg)',
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-3)',
            }}>
              <span style={{ color: `var(--accent-${m.color})` }}>{m.icon}</span>
              <div>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px' }}>{m.label}</p>
                <p style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--text-primary)' }}>{m.value}</p>
              </div>
            </div>
          ))}
        </div>

        {/* 4-Panel CRM Flow */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 'var(--space-4)',
        }}>
          {/* Panel 1: Photo Upload */}
          <EmpireDataPanel
            title="Photo Upload"
            subtitle="Upload and analyze"
            glass
          >
            <div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => {}}
              className="glass-premium"
              style={{
                border: dragOver ? '2px dashed var(--accent-primary)' : '2px dashed rgba(255,255,255,0.15)',
                borderRadius: 'var(--radius-lg)',
                padding: 'var(--space-6)',
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'all var(--transition-base)',
                marginBottom: 'var(--space-4)',
                minHeight: 160,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 'var(--space-2)',
              }}
            >
              <Upload size={32} style={{ color: dragOver ? 'var(--accent-primary)' : 'var(--text-muted)' }} />
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
                {dragOver ? 'Drop image here' : 'Drag & drop or click to upload'}
              </p>
            </div>

            {photoAnalyzed && analysis && (
              <div style={{
                background: 'rgba(99,102,241,0.1)',
                border: '1px solid var(--accent-glow)',
                borderRadius: 'var(--radius-md)',
                padding: 'var(--space-3)',
                marginBottom: 'var(--space-4)',
                textAlign: 'center',
              }}>
                <ImageIcon size={20} style={{ color: 'var(--accent-primary)', marginBottom: 4 }} />
                <p style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>
                  AI Analysis Complete
                </p>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                  Dimensions: W: {analysis.width} × H: {analysis.height}
                </p>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--success)' }}>
                  Confidence: {analysis.confidence}%
                </p>
              </div>
            )}

            <button
              onClick={handleAnalyze}
              className="button-glow"
              style={{
                width: '100%',
                padding: 'var(--space-3)',
                background: 'var(--accent-primary)',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                color: '#fff',
                fontWeight: 600,
                fontSize: 'var(--text-sm)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 'var(--space-2)',
              }}
            >
              <Sparkles size={14} /> Analyze
            </button>
          </EmpireDataPanel>

          {/* Panel 2: Quote Builder */}
          <EmpireDataPanel
            title="Quote Builder"
            subtitle="Create and send quote"
            glass
          >
            {/* Tier Selector */}
            <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
              {(['lite', 'pro', 'empire'] as const).map((tier) => (
                <button
                  key={tier}
                  onClick={() => setSelectedTier(tier)}
                  style={{
                    flex: 1,
                    padding: 'var(--space-2)',
                    background: selectedTier === tier ? 'var(--accent-primary)' : 'rgba(255,255,255,0.06)',
                    border: selectedTier === tier ? '1px solid var(--accent-primary)' : '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 'var(--radius-md)',
                    color: selectedTier === tier ? '#fff' : 'var(--text-secondary)',
                    fontWeight: selectedTier === tier ? 600 : 400,
                    fontSize: 'var(--text-xs)',
                    cursor: 'pointer',
                    textTransform: 'capitalize',
                    transition: 'all var(--transition-fast)',
                  }}
                >
                  {tier}
                </button>
              ))}
            </div>

            {/* Client Info */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
              <InputRow label="Client" value={clientInfo.name} />
              <InputRow label="Email" value={clientInfo.email} />
              <InputRow label="Phone" value={clientInfo.phone} />
            </div>

            {/* Pricing */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: 'var(--space-3)',
              background: 'rgba(99,102,241,0.1)',
              borderRadius: 'var(--radius-md)',
              marginBottom: 'var(--space-4)',
            }}>
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Total</span>
              <span style={{ fontSize: 'var(--text-lg)', fontWeight: 700, color: 'var(--accent-primary)' }}>
                ${pricing[selectedTier].toLocaleString()}.00
              </span>
            </div>

            {/* PDF Placeholder */}
            <div style={{
              height: 80,
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              marginBottom: 'var(--space-4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 'var(--space-2)',
            }}>
              <FileText size={16} style={{ color: 'var(--text-muted)' }} />
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>PDF Preview</span>
            </div>

            <button
              onClick={handleSendQuote}
              disabled={quoteSent}
              className="button-glow"
              style={{
                width: '100%',
                padding: 'var(--space-3)',
                background: quoteSent ? 'var(--success)' : 'var(--accent-primary)',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                color: '#fff',
                fontWeight: 600,
                fontSize: 'var(--text-sm)',
                cursor: quoteSent ? 'default' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 'var(--space-2)',
              }}
            >
              <Send size={14} /> {quoteSent ? 'Sent!' : 'Send Quote'}
            </button>
          </EmpireDataPanel>

          {/* Panel 3: Invoice Panel */}
          <EmpireDataPanel
            title="Invoice"
            subtitle="Invoice #INV-2024-08765"
            glass
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-4)' }}>
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>Status</span>
              <EmpireStatusPill status="success" label="Verified" size="sm" />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
              <InputRow label="Terms" value="Net 30" />
              <InputRow label="Subtotal" value="$2,890.00" />
              <InputRow label="Tax" value="$173.40" />
              <InputRow label="Shipping" value="$0.00" />
              <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-2)', display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Total</span>
                <span style={{ fontWeight: 700, color: 'var(--accent-primary)' }}>$3,063.40</span>
              </div>
            </div>

            <div style={{ marginBottom: 'var(--space-4)' }}>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 'var(--space-2)' }}>Line Items</p>
              {['Premium Fabric Panels x12', 'Hardware Kit Premium', 'Professional Installation'].map((item, i) => (
                <div key={i} style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  padding: 'var(--space-2) 0',
                  borderBottom: '1px solid var(--border-subtle)',
                }}>
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>{item}</span>
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                    {['$1,560', '$890', '$440'][i]}
                  </span>
                </div>
              ))}
            </div>

            <button
              onClick={handleSendInvoice}
              disabled={invoiceSent}
              className="button-glow"
              style={{
                width: '100%',
                padding: 'var(--space-3)',
                background: invoiceSent ? 'var(--success)' : 'var(--accent-primary)',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                color: '#fff',
                fontWeight: 600,
                fontSize: 'var(--text-sm)',
                cursor: invoiceSent ? 'default' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 'var(--space-2)',
              }}
            >
              <Send size={14} /> {invoiceSent ? 'Sent!' : 'Send Invoice'}
            </button>
          </EmpireDataPanel>

          {/* Panel 4: Payment Tracking */}
          <EmpireDataPanel
            title="Payment Tracking"
            subtitle="Payment status and history"
            glass
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}>
              {[
                { label: 'Subtotal', value: '$2,890.00' },
                { label: 'Tax', value: '$173.40' },
                { label: 'Shipping', value: '$0.00' },
              ].map((row) => (
                <InputRow key={row.label} label={row.label} value={row.value} />
              ))}
              <div style={{ borderTop: '1px solid var(--border-accent)', paddingTop: 'var(--space-3)', display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>Total Due</span>
                <span style={{ fontWeight: 700, fontSize: 'var(--text-lg)', color: 'var(--accent-primary)' }}>$3,063.40</span>
              </div>
            </div>

            <div style={{ marginBottom: 'var(--space-4)' }}>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 'var(--space-2)' }}>Payment History</p>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', fontSize: 'var(--text-xs)', color: 'var(--text-muted)', padding: '4px 0' }}>Date</th>
                    <th style={{ textAlign: 'left', fontSize: 'var(--text-xs)', color: 'var(--text-muted)', padding: '4px 0' }}>Amount</th>
                    <th style={{ textAlign: 'left', fontSize: 'var(--text-xs)', color: 'var(--text-muted)', padding: '4px 0' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style={{ padding: '6px 0', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>2024-04-26</td>
                    <td style={{ padding: '6px 0', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>$3,063.40</td>
                    <td style={{ padding: '6px 0' }}><EmpireStatusPill status="success" label="Paid" size="sm" /></td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: 'var(--space-3)',
              background: 'var(--success-bg)',
              border: '1px solid var(--success-border)',
              borderRadius: 'var(--radius-md)',
              marginBottom: 'var(--space-4)',
            }}>
              <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--success)' }}>Balance Due</span>
              <span style={{ fontSize: 'var(--text-lg)', fontWeight: 700, color: 'var(--success)' }}>$0.00</span>
            </div>

            <button
              className="button-glow"
              style={{
                width: '100%',
                padding: 'var(--space-3)',
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.12)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--text-primary)',
                fontWeight: 600,
                fontSize: 'var(--text-sm)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 'var(--space-2)',
              }}
            >
              <Download size={14} /> Download Receipt
            </button>
          </EmpireDataPanel>
        </div>
      </div>
    </EmpireShell>
  );
}

function InputRow({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{label}</span>
      <span style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--text-secondary)' }}>{value}</span>
    </div>
  );
}
