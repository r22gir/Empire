'use client';

import { useState } from 'react';
import { Share2, Check, AlertCircle, Clock, ChevronRight, ArrowRight } from 'lucide-react';
import { mockListings, PLATFORM_COLORS } from '../lib/mock-data';
import { Platform } from '../lib/types';

const ALL_PLATFORMS: { id: Platform; label: string; maxTitle: number }[] = [
  { id: 'ebay', label: 'eBay', maxTitle: 80 },
  { id: 'etsy', label: 'Etsy', maxTitle: 140 },
  { id: 'shopify', label: 'Shopify', maxTitle: 255 },
  { id: 'poshmark', label: 'Poshmark', maxTitle: 80 },
  { id: 'mercari', label: 'Mercari', maxTitle: 60 },
  { id: 'facebook', label: 'Facebook', maxTitle: 100 },
  { id: 'amazon', label: 'Amazon', maxTitle: 200 },
  { id: 'depop', label: 'Depop', maxTitle: 60 },
];

export default function CrossPostSection() {
  const [step, setStep] = useState(1);
  const [selectedListings, setSelectedListings] = useState<Set<string>>(new Set());
  const [targetPlatforms, setTargetPlatforms] = useState<Set<Platform>>(new Set());
  const [priceAdj, setPriceAdj] = useState<Record<string, number>>({});

  const unpostedListings = mockListings.filter(l => l.status === 'active' || l.status === 'draft');

  const toggleListing = (id: string) => {
    const next = new Set(selectedListings);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelectedListings(next);
  };

  const togglePlatform = (p: Platform) => {
    const next = new Set(targetPlatforms);
    if (next.has(p)) next.delete(p); else next.add(p);
    setTargetPlatforms(next);
  };

  const mockBatchHistory = [
    { id: 'B-001', date: '2026-03-08', listings: 5, platforms: ['ebay', 'etsy'], success: 9, failed: 1 },
    { id: 'B-002', date: '2026-03-06', listings: 3, platforms: ['facebook'], success: 3, failed: 0 },
    { id: 'B-003', date: '2026-03-03', listings: 8, platforms: ['ebay', 'shopify', 'mercari'], success: 22, failed: 2 },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Cross-Post</h1>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Bulk cross-posting workflow</p>
      </div>

      {/* Steps indicator */}
      <div className="flex items-center gap-2 empire-card !py-3">
        {['Select Listings', 'Choose Platforms', 'Review & Adjust', 'Execute'].map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <div
              className="flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium"
              style={{
                background: step === i + 1 ? '#ecfeff' : step > i + 1 ? '#dcfce7' : '#f3f4f6',
                color: step === i + 1 ? '#06b6d4' : step > i + 1 ? '#16a34a' : '#999',
              }}
            >
              {step > i + 1 ? <Check size={14} /> : <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold" style={{ background: step === i + 1 ? '#06b6d4' : '#ddd', color: 'white' }}>{i + 1}</span>}
              {s}
            </div>
            {i < 3 && <ChevronRight size={16} style={{ color: 'var(--muted)' }} />}
          </div>
        ))}
      </div>

      {/* Step 1: Select Listings */}
      {step === 1 && (
        <div className="space-y-3">
          <div className="section-label">Select listings to cross-post ({selectedListings.size} selected)</div>
          <div className="grid grid-cols-2 gap-3">
            {unpostedListings.map(listing => {
              const sel = selectedListings.has(listing.id);
              return (
                <div
                  key={listing.id}
                  className="empire-card !p-3 flex items-center gap-3 cursor-pointer"
                  style={{ borderColor: sel ? '#06b6d4' : undefined, background: sel ? '#ecfeff' : undefined }}
                  onClick={() => toggleListing(listing.id)}
                >
                  <input type="checkbox" className="accent-cyan-500" checked={sel} readOnly />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{listing.title}</div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-sm font-semibold" style={{ color: 'var(--gold)' }}>${listing.price.toFixed(2)}</span>
                      <span className={`status-pill ${listing.status}`} style={{ fontSize: '11px' }}>{listing.status}</span>
                      <div className="flex gap-0.5">
                        {listing.platforms.map(p => <div key={p.platform} className={`platform-dot ${p.platform}`} />)}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex justify-end">
            <button className="btn-primary" onClick={() => setStep(2)} disabled={selectedListings.size === 0}>
              Next: Choose Platforms <ArrowRight size={15} />
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Choose Platforms */}
      {step === 2 && (
        <div className="space-y-4">
          <div className="section-label">Choose target platforms</div>
          <div className="grid grid-cols-4 gap-3">
            {ALL_PLATFORMS.map(p => {
              const sel = targetPlatforms.has(p.id);
              return (
                <div
                  key={p.id}
                  className="empire-card !p-4 text-center cursor-pointer"
                  style={{ borderColor: sel ? PLATFORM_COLORS[p.id] : undefined, background: sel ? `${PLATFORM_COLORS[p.id]}08` : undefined }}
                  onClick={() => togglePlatform(p.id)}
                >
                  <div className="w-10 h-10 rounded-full mx-auto mb-2 flex items-center justify-center text-white font-bold" style={{ background: PLATFORM_COLORS[p.id] }}>
                    {p.label[0]}
                  </div>
                  <div className="text-sm font-semibold">{p.label}</div>
                  <div className="text-xs mt-0.5" style={{ color: 'var(--muted)' }}>Max {p.maxTitle} chars</div>
                  {sel && <Check size={14} className="mx-auto mt-1" style={{ color: PLATFORM_COLORS[p.id] }} />}
                </div>
              );
            })}
          </div>
          <div className="flex justify-between">
            <button className="btn-secondary" onClick={() => setStep(1)}>Back</button>
            <button className="btn-primary" onClick={() => setStep(3)} disabled={targetPlatforms.size === 0}>
              Next: Review <ArrowRight size={15} />
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Review & Adjust */}
      {step === 3 && (
        <div className="space-y-4">
          <div className="section-label">Review cross-post settings</div>
          <div className="empire-card">
            <div className="text-sm font-medium mb-3">Price Adjustments by Platform</div>
            <div className="grid grid-cols-2 gap-3">
              {Array.from(targetPlatforms).map(p => (
                <div key={p} className="flex items-center gap-3 p-2 rounded-lg" style={{ background: '#f9fafb' }}>
                  <div className="w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold" style={{ background: PLATFORM_COLORS[p] }}>
                    {p[0].toUpperCase()}
                  </div>
                  <span className="text-sm font-medium capitalize flex-1">{p}</span>
                  <div className="flex items-center gap-1">
                    <input
                      type="number"
                      className="form-input !w-16 text-sm text-center"
                      value={priceAdj[p] || 0}
                      onChange={e => setPriceAdj({ ...priceAdj, [p]: Number(e.target.value) })}
                    />
                    <span className="text-xs" style={{ color: 'var(--muted)' }}>%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="empire-card">
            <div className="text-sm font-medium mb-3">Preview ({selectedListings.size} listings x {targetPlatforms.size} platforms = {selectedListings.size * targetPlatforms.size} cross-posts)</div>
            <table className="empire-table text-sm">
              <thead><tr><th>Listing</th>{Array.from(targetPlatforms).map(p => <th key={p} className="capitalize">{p}</th>)}</tr></thead>
              <tbody>
                {mockListings.filter(l => selectedListings.has(l.id)).map(l => (
                  <tr key={l.id}>
                    <td className="font-medium">{l.title.slice(0, 40)}...</td>
                    {Array.from(targetPlatforms).map(p => {
                      const adj = priceAdj[p] || 0;
                      const price = l.price * (1 + adj / 100);
                      return <td key={p} style={{ color: 'var(--gold)' }}>${price.toFixed(2)}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex justify-between">
            <button className="btn-secondary" onClick={() => setStep(2)}>Back</button>
            <button className="btn-gold" onClick={() => setStep(4)}>
              <Share2 size={15} /> Execute Cross-Post
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Execute */}
      {step === 4 && (
        <div className="space-y-4">
          <div className="empire-card text-center py-8">
            <div className="w-16 h-16 rounded-full mx-auto mb-4 flex items-center justify-center" style={{ background: '#dcfce7' }}>
              <Check size={32} style={{ color: 'var(--green)' }} />
            </div>
            <h2 className="text-xl font-bold mb-2">Cross-Post Complete!</h2>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              Successfully queued {selectedListings.size * targetPlatforms.size} cross-posts across {targetPlatforms.size} platforms
            </p>
            <div className="flex justify-center gap-3 mt-4">
              <button className="btn-primary" onClick={() => { setStep(1); setSelectedListings(new Set()); setTargetPlatforms(new Set()); }}>
                Start New Batch
              </button>
            </div>
          </div>

          <div className="empire-card">
            <div className="section-label mb-2">Queue Progress</div>
            {mockListings.filter(l => selectedListings.has(l.id)).map(l => (
              <div key={l.id} className="flex items-center gap-3 py-2 border-b last:border-0" style={{ borderColor: 'var(--border)' }}>
                <Check size={14} style={{ color: 'var(--green)' }} />
                <span className="text-sm flex-1">{l.title}</span>
                <div className="flex gap-1">
                  {Array.from(targetPlatforms).map(p => (
                    <span key={p} className="status-pill listed text-xs capitalize">{p}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Batch History */}
      <div className="empire-card">
        <div className="section-label mb-3">Recent Cross-Post Batches</div>
        <table className="empire-table text-sm">
          <thead><tr><th>Batch</th><th>Date</th><th>Listings</th><th>Platforms</th><th>Success</th><th>Failed</th></tr></thead>
          <tbody>
            {mockBatchHistory.map(b => (
              <tr key={b.id}>
                <td className="font-medium">{b.id}</td>
                <td>{b.date}</td>
                <td>{b.listings}</td>
                <td>
                  <div className="flex gap-1">
                    {b.platforms.map(p => <div key={p} className={`platform-dot ${p}`} />)}
                  </div>
                </td>
                <td style={{ color: 'var(--green)' }}>{b.success}</td>
                <td style={{ color: b.failed > 0 ? 'var(--red)' : 'var(--muted)' }}>{b.failed}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
