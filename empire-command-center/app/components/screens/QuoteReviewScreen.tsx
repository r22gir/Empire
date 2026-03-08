'use client';
import { useState, useEffect } from 'react';
import { API } from '../../lib/api';
import { Quote } from '../../lib/types';
import { Check, FileText, Send, Mail, Video, Printer, Image } from 'lucide-react';

interface Props {
  quoteId?: string;
}

export default function QuoteReviewScreen({ quoteId }: Props) {
  const [quote, setQuote] = useState<Quote | null>(null);
  const [selected, setSelected] = useState<number>(1);
  const [loading, setLoading] = useState(false);

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

  const handleAction = async (action: string) => {
    if (action === 'pdf') {
      window.open(API.replace('/api/v1', '') + `/api/v1/quotes/${quote.id}/pdf`, '_blank');
    } else if (action === 'telegram') {
      await fetch(API + '/max/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: `Send quote ${quote.id} to Telegram`, model: 'auto', history: [] }),
      });
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

      {/* Customer photo placeholder */}
      <div className="bg-[#eae7e2] border border-[#d8d3cb] rounded-xl h-[200px] flex items-center justify-center mt-4 mb-5">
        <Image size={36} className="text-[#c0bbb3] mr-3" />
        <span className="text-[#888] font-medium">Customer photo</span>
      </div>

      <div className="text-sm font-bold mb-3 text-[#1a1a1a]">Select a Proposal</div>
      <div className="flex gap-3 mb-5">
        {tiers.map((t, i) => {
          const p = proposals[i];
          const total = p?.total || 0;
          const isSelected = selected === i;
          return (
            <div key={t.key} onClick={() => setSelected(i)}
              className={`flex-1 p-5 rounded-xl cursor-pointer text-center min-h-[140px] transition-all border-2
                ${isSelected
                  ? 'shadow-[0_4px_16px_rgba(0,0,0,0.1)]'
                  : 'hover:shadow-[0_2px_8px_rgba(0,0,0,0.06)]'}`}
              style={{
                background: isSelected ? t.bg : 'white',
                borderColor: isSelected ? t.color : '#e5e0d8',
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

      <div className="flex gap-2.5 flex-wrap">
        <button onClick={() => handleAction('confirm')}
          className="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-[#b8960c] text-white border-2 border-[#a08509] rounded-xl text-[14px] font-bold cursor-pointer min-h-[48px] hover:bg-[#a08509] shadow-[0_2px_8px_rgba(184,150,12,0.25)] transition-all active:scale-[0.98]">
          <Check size={18} /> Confirm Selection
        </button>
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
      className="flex items-center gap-1.5 px-4 py-3 rounded-xl border-1.5 border-[#d8d3cb] bg-white text-[13px] font-semibold text-[#555] cursor-pointer min-h-[48px] hover:bg-[#fdf8eb] hover:border-[#b8960c] hover:text-[#b8960c] transition-all active:scale-[0.97] shadow-[0_1px_3px_rgba(0,0,0,0.05)]">
      {icon} {label}
    </button>
  );
}
