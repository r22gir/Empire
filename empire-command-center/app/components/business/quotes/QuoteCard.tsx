'use client';

import { useState } from 'react';
import { Check, FileDown, Star, Crown, Gem, Loader2, ExternalLink } from 'lucide-react';
import { API } from '../../../lib/api';

const TIERS = [
  { key: 'A', label: 'Essential', color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0', icon: Star },
  { key: 'B', label: 'Designer', color: '#b8960c', bg: '#fdf8eb', border: '#f5ecd0', icon: Crown },
  { key: 'C', label: 'Premium', color: '#7c3aed', bg: '#faf5ff', border: '#e9d5ff', icon: Gem },
];

interface QuoteCardProps {
  result: any;
  onScreenChange?: (screen: string) => void;
  onSend?: (msg: string) => void;
}

export default function QuoteCard({ result, onScreenChange, onSend }: QuoteCardProps) {
  const [selectedTier, setSelectedTier] = useState<string | null>(null);
  const [selecting, setSelecting] = useState(false);

  const { quote_id, quote_number, customer_name, proposal_totals, items_count, pdf_url } = result;

  const handleSelectProposal = async (option: string) => {
    setSelecting(true);
    setSelectedTier(option);
    // Ask MAX to select the proposal
    onSend?.(`Select proposal ${option} on quote ${quote_id}`);
    setSelecting(false);
  };

  const handleDownloadPDF = async () => {
    if (!pdf_url) return;
    try {
      const res = await fetch(`${API}${pdf_url}`);
      if (!res.ok) throw new Error('Failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${quote_number}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // Fallback: open in new tab
      window.open(`${API}${pdf_url}`, '_blank');
    }
  };

  return (
    <div style={{
      marginTop: 12,
      borderRadius: 16,
      border: '1.5px solid #f0e6c0',
      background: '#fffdf7',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '14px 18px',
        background: 'linear-gradient(135deg, #fdf8eb 0%, #fff9ee 100%)',
        borderBottom: '1px solid #f0e6c0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>
            {quote_number}
          </div>
          <div style={{ fontSize: 12, color: '#888', marginTop: 2 }}>
            {customer_name} · {items_count || 0} item{items_count !== 1 ? 's' : ''}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {pdf_url && (
            <button
              onClick={handleDownloadPDF}
              title="Download PDF"
              style={{
                width: 34, height: 34, borderRadius: 10,
                background: '#fff', border: '1px solid #ece8e0',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', color: '#b8960c',
              }}
            >
              <FileDown size={15} />
            </button>
          )}
          <button
            onClick={() => onScreenChange?.('quote')}
            title="Full Review"
            style={{
              width: 34, height: 34, borderRadius: 10,
              background: '#fff', border: '1px solid #ece8e0',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', color: '#555',
            }}
          >
            <ExternalLink size={15} />
          </button>
        </div>
      </div>

      {/* 3 Tier Options */}
      <div style={{ padding: '14px 16px', display: 'flex', gap: 10 }}>
        {TIERS.map(tier => {
          const total = proposal_totals?.[tier.key] || 0;
          const isSelected = selectedTier === tier.key;
          const Icon = tier.icon;
          return (
            <div
              key={tier.key}
              onClick={() => !selecting && setSelectedTier(tier.key)}
              style={{
                flex: 1,
                padding: '14px 12px',
                borderRadius: 14,
                border: `2px solid ${isSelected ? tier.color : '#ece8e0'}`,
                background: isSelected ? tier.bg : '#fff',
                cursor: 'pointer',
                textAlign: 'center',
                transition: 'all 0.2s',
                position: 'relative',
              }}
            >
              {isSelected && (
                <div style={{
                  position: 'absolute', top: -8, right: -8,
                  width: 20, height: 20, borderRadius: '50%',
                  background: tier.color, display: 'flex',
                  alignItems: 'center', justifyContent: 'center',
                }}>
                  <Check size={12} color="#fff" />
                </div>
              )}
              <Icon size={18} style={{ color: tier.color, marginBottom: 4 }} />
              <div style={{ fontSize: 10, fontWeight: 700, color: tier.color, letterSpacing: 0.5, textTransform: 'uppercase' }}>
                {tier.key} · {tier.label}
              </div>
              <div style={{ fontSize: 22, fontWeight: 800, color: tier.color, margin: '6px 0 2px' }}>
                ${total.toLocaleString()}
              </div>
              <div style={{ fontSize: 9, color: '#999' }}>
                {tier.key === 'A' ? 'Economy fabrics' : tier.key === 'B' ? 'Mid-grade fabrics' : 'Premium fabrics'}
              </div>
            </div>
          );
        })}
      </div>

      {/* Action Row */}
      {selectedTier && (
        <div style={{
          padding: '0 16px 14px',
          display: 'flex',
          gap: 8,
        }}>
          <button
            onClick={() => handleSelectProposal(selectedTier)}
            disabled={selecting}
            style={{
              flex: 1,
              height: 40,
              borderRadius: 12,
              background: TIERS.find(t => t.key === selectedTier)?.color || '#b8960c',
              color: '#fff',
              border: 'none',
              fontSize: 13,
              fontWeight: 700,
              cursor: selecting ? 'wait' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
              transition: 'opacity 0.2s',
              opacity: selecting ? 0.7 : 1,
            }}
          >
            {selecting ? <Loader2 size={15} className="animate-spin" /> : <Check size={15} />}
            Confirm {TIERS.find(t => t.key === selectedTier)?.label} — ${(proposal_totals?.[selectedTier] || 0).toLocaleString()}
          </button>
        </div>
      )}
    </div>
  );
}
