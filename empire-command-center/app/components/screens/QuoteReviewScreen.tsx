'use client';
import { useState, useEffect } from 'react';
import { API } from '../../lib/api';
import { Quote } from '../../lib/types';
import { Check, FileText, Send, Mail, Video, Printer, Image, ExternalLink } from 'lucide-react';
import QuoteVerificationPanel from '../business/quotes/QuoteVerificationPanel';

interface Props {
  quoteId?: string;
  onOpenBuilder?: () => void;
}

export default function QuoteReviewScreen({ quoteId, onOpenBuilder }: Props) {
  const [quote, setQuote] = useState<Quote | null>(null);
  const [selected, setSelected] = useState<number>(1);
  const [loading, setLoading] = useState(false);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (!quoteId) {
      fetch(API + '/quotes?limit=1').then(r => r.json()).then(data => {
        const q = data.quotes?.[0] || data[0];
        if (q) { setQuote(q); loadFull(q.id); }
      }).catch(() => {});
      return;
    }
    loadFull(quoteId);
  }, [quoteId]);

  const loadFull = async (id: string) => {
    setLoading(true);
    try {
      const res = await fetch(API + '/quotes/' + id);
      if (res.ok) setQuote(await res.json());
    } catch { /* silent */ }
    setLoading(false);
  };

  if (loading) return (
    <div className="flex-1 flex items-center justify-center">
      <div className="w-8 h-8 border-3 border-[#e5e0d8] border-t-[#b8960c] rounded-full animate-spin" />
    </div>
  );

  if (!quote) return (
    <div className="flex-1 flex items-center justify-center flex-col gap-3">
      <FileText size={48} className="text-[#d8d3cb]" />
      <p className="text-base font-semibold text-[#888]">No quote selected</p>
      <p className="text-sm text-[#aaa]">Create a quote via chat to review here</p>
    </div>
  );

  const proposals = quote.design_proposals || [];
  const tiers = [
    { label: 'Essential', key: 'A', color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0' },
    { label: 'Designer', key: 'B', color: '#b8960c', bg: '#fdf8eb', border: '#f5ecd0' },
    { label: 'Premium', key: 'C', color: '#7c3aed', bg: '#faf5ff', border: '#e9d5ff' },
  ];

  const showFeedback = (msg: string) => {
    setActionFeedback(msg);
    setTimeout(() => setActionFeedback(null), 3000);
  };

  const handleAction = async (action: string) => {
    if (action === 'pdf') {
      showFeedback('Generating PDF...');
      try {
        const res = await fetch(`${API}/quotes/${quote.id}/pdf?skip_verification=true`, { method: 'POST' });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
          showFeedback(err.error || 'PDF generation failed');
          return;
        }
        const blob = await res.blob();
        const blobUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = `${quote.quote_number || quote.id}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(blobUrl);
        showFeedback('PDF downloaded!');
      } catch {
        showFeedback('PDF generation failed');
      }
    } else if (action === 'telegram') {
      showFeedback('Sending to Telegram...');
      try {
        await fetch(API + '/max/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: `Send quote ${quote.quote_number} for ${quote.customer_name} ($${quote.total}) to Telegram`, model: 'auto', history: [] }),
        });
        showFeedback('Sent to Telegram!');
      } catch { showFeedback('Failed to send'); }
    } else if (action === 'email') {
      const subject = encodeURIComponent(`Quote ${quote.quote_number} - ${quote.customer_name}`);
      const body = encodeURIComponent(`Hi ${quote.customer_name},\n\nPlease find your quote ${quote.quote_number} attached.\n\nTotal: $${(quote.total || 0).toLocaleString()}\n\nThank you,\nEmpire Workroom`);
      window.open(`mailto:?subject=${subject}&body=${body}`, '_blank');
      showFeedback('Opening email client...');
    } else if (action === 'print') {
      window.print();
    } else if (action === 'confirm') {
      showFeedback('Confirming selection...');
      try {
        await fetch(API + `/quotes/${quote.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: 'accepted', selected_tier: selected }),
        });
        setQuote({ ...quote, status: 'accepted' });
        showFeedback('Quote accepted!');
      } catch { showFeedback('Failed to update'); }
    } else if (action === 'video') {
      showFeedback('Video call feature coming soon');
    }
  };

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6 max-w-[850px] mx-auto w-full">
      <div className="flex items-center gap-3 mb-1">
        <div className="w-10 h-10 rounded-xl bg-[#fdf8eb] flex items-center justify-center">
          <FileText size={20} className="text-[#b8960c]" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-[#1a1a1a]">{quote.quote_number} · Quote Review</h1>
          <p className="text-xs text-[#777]">{quote.customer_name} · Created {quote.created_at || 'Today'}</p>
        </div>
      </div>

      {/* Customer photo */}
      {quote.photos && quote.photos.length > 0 ? (
        <div className="empire-card" style={{ padding: 0, marginTop: 16, marginBottom: 20, overflow: 'hidden', borderRadius: 14 }}>
          <div style={{ display: 'flex', gap: 2, overflowX: 'auto' }}>
            {quote.photos.map((photo, pi) => (
              <img
                key={pi}
                src={`${API}/files/images/${photo.filename}`}
                alt={`Customer photo ${pi + 1}`}
                style={{
                  height: 220,
                  objectFit: 'cover',
                  flex: quote.photos!.length === 1 ? '1' : 'none',
                  width: quote.photos!.length === 1 ? '100%' : 'auto',
                  minWidth: 200,
                  borderRadius: quote.photos!.length > 1 ? 4 : 0,
                }}
              />
            ))}
          </div>
        </div>
      ) : (
        <div className="empire-card" style={{ padding: 0, height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: 16, marginBottom: 20, background: '#eae7e2' }}>
          <Image size={36} className="text-[#c0bbb3] mr-3" />
          <span className="text-[#888] font-medium">No photo uploaded</span>
        </div>
      )}

      {/* Quote Quality Verification */}
      <div style={{ marginBottom: 16 }}>
        <QuoteVerificationPanel quoteId={quote.id} />
      </div>

      <div className="text-sm font-bold mb-3 text-[#1a1a1a]">Select a Proposal</div>
      <div className="flex gap-3 mb-5">
        {tiers.map((t, i) => {
          const p = proposals[i];
          const total = p?.total || 0;
          const isSelected = selected === i;
          return (
            <div key={t.key} onClick={() => setSelected(i)}
              className={`empire-card flex-1 cursor-pointer text-center min-h-[140px] transition-all
                ${isSelected
                  ? 'shadow-[0_4px_16px_rgba(0,0,0,0.1)]'
                  : 'hover:shadow-[0_2px_8px_rgba(0,0,0,0.06)]'}`}
              style={{
                padding: 20,
                background: isSelected ? t.bg : '#faf9f7',
                borderColor: isSelected ? t.color : '#ece8e0',
                borderWidth: 2,
                borderLeftWidth: '4px',
                borderLeftColor: t.color,
              }}>
              <div className="text-xs font-bold text-[#777] tracking-wide">{t.key} · {t.label}</div>
              <div className="text-[26px] font-bold my-2" style={{ color: t.color }}>${total.toLocaleString()}</div>
              <div className="text-[11px] text-[#888]">Grade {t.key} fabric · {p?.lining_type || 'Standard'} lining</div>
              {/* Mockup images */}
              {(p?.inpainted_image_url || p?.mockup_image) && (
                <div className="flex gap-1.5 mt-3">
                  {p.inpainted_image_url && (
                    <div className="flex-1 rounded-lg overflow-hidden border border-[#e5e0d8]">
                      <div className="text-[9px] text-center py-1 font-bold" style={{ color: t.color, background: t.bg }}>Your Room</div>
                      <img src={API.replace('/api/v1','') + p.inpainted_image_url} className="w-full h-[70px] object-cover" alt="" />
                    </div>
                  )}
                  {p.clean_mockup_url && (
                    <div className="flex-1 rounded-lg overflow-hidden border border-[#e5e0d8]">
                      <div className="text-[9px] text-center py-1 bg-[#f5f3ef] font-bold text-[#777]">Inspiration</div>
                      <img src={API.replace('/api/v1','') + p.clean_mockup_url} className="w-full h-[70px] object-cover" alt="" />
                    </div>
                  )}
                </div>
              )}
              {!p?.inpainted_image_url && !p?.mockup_image && (
                <div className="w-full h-[80px] bg-[#f5f3ef] rounded-lg mt-3 flex items-center justify-center text-[11px] text-[#bbb] border border-[#ece8e1]">
                  <Image size={16} className="mr-1.5 text-[#d8d3cb]" /> AI Mockup — {t.label}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Feedback toast */}
      {actionFeedback && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 999,
          padding: '10px 20px', borderRadius: 12, background: '#1a1a1a', color: '#fff',
          fontSize: 13, fontWeight: 600, boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
          animation: 'fadeIn 0.2s ease',
        }}>
          {actionFeedback}
        </div>
      )}

      <div className="flex gap-2.5 flex-wrap">
        <button onClick={() => handleAction('confirm')}
          className="flex-1 flex items-center justify-center gap-2 bg-[#b8960c] text-white border-2 border-[#a08509] text-[13px] font-bold cursor-pointer hover:bg-[#a08509] shadow-[0_2px_8px_rgba(184,150,12,0.25)] transition-all active:scale-[0.98]"
          style={{ height: 44, padding: '0 20px', borderRadius: 12 }}>
          <Check size={18} /> Confirm Selection
        </button>
        <ActionBtn icon={<ExternalLink size={16} />} label="QuoteBuilder" onClick={() => {
          if (onOpenBuilder) { onOpenBuilder(); } else { window.open(`http://localhost:3001${quote?.id ? `?quote=${quote.id}` : ''}`, '_blank'); }
        }} />
        <ActionBtn icon={<FileText size={16} />} label="PDF" onClick={() => handleAction('pdf')} />
        <ActionBtn icon={<Send size={16} />} label="Telegram" onClick={() => handleAction('telegram')} />
        <ActionBtn icon={<Mail size={16} />} label="Email" onClick={() => handleAction('email')} />
        <ActionBtn icon={<Video size={16} />} label="Call" onClick={() => handleAction('video')} />
        <ActionBtn icon={<Printer size={16} />} label="Print" onClick={() => handleAction('print')} />
      </div>
    </div>
  );
}

function ActionBtn({ icon, label, onClick }: { icon: React.ReactNode; label: string; onClick?: () => void }) {
  return (
    <button onClick={onClick}
      className="flex items-center gap-1.5 font-bold text-[#555] cursor-pointer hover:bg-[#fdf8eb] hover:border-[#b8960c] hover:text-[#b8960c] transition-all active:scale-[0.97]"
      style={{
        height: 44,
        padding: '0 16px',
        borderRadius: 12,
        border: '1.5px solid #ece8e0',
        background: '#faf9f7',
        fontSize: 12,
      }}>
      {icon} {label}
    </button>
  );
}
