'use client';

import React, { useState, useRef, useCallback } from 'react';
import {
  Camera, Upload, X, ChevronRight, Sparkles, Search,
  Tag, DollarSign, Package, RotateCw, Check, AlertCircle,
  ScanBarcode, TrendingUp, ShoppingCart, Copy, Pencil,
  Loader2, Plus, Trash2, ArrowRight, ArrowLeft, Zap, Star,
} from 'lucide-react';

/* ─── Types ─── */
interface PhotoEntry {
  id: string;
  dataUrl: string;
  name: string;
}

type Condition = 'new' | 'like_new' | 'good' | 'fair' | 'poor';

interface AIIdentification {
  productName: string;
  brand: string;
  category: string;
  subcategory: string;
  upc: string;
  model: string;
  color: string;
  material: string;
  size: string;
  condition: Condition;
  conditionScore: number;
  conditionNotes: string;
  defects: string[];
  keywords: string[];
}

interface AIPricing {
  estimatedValue: number;
  suggestedPrice: number;
  priceRange: { low: number; high: number };
  platformPrices: { platform: string; suggested: number; avgSold: number; fees: number; profit: number }[];
  comps: { title: string; price: number; platform: string; soldDate: string; condition: string }[];
  demandLevel: 'high' | 'medium' | 'low';
  avgDaysToSell: number;
}

interface AIDescription {
  title: string;
  description: string;
  tags: string[];
  itemSpecifics: Record<string, string>;
  platformDescriptions: { platform: string; title: string; description: string }[];
}

type Step = 'photos' | 'identify' | 'price' | 'describe' | 'review';

interface SmartListerPanelProps {
  accentColor?: string;
  accentBg?: string;
  marketplaces?: string[];
  marketplaceColors?: Record<string, string>;
  productLabel?: string;
}

const STEPS: { id: Step; label: string; icon: any }[] = [
  { id: 'photos', label: 'Photos', icon: Camera },
  { id: 'identify', label: 'Identify', icon: ScanBarcode },
  { id: 'price', label: 'Price', icon: DollarSign },
  { id: 'describe', label: 'Describe', icon: Tag },
  { id: 'review', label: 'Review & List', icon: ShoppingCart },
];

const CONDITION_LABELS: Record<Condition, string> = {
  new: 'New / Sealed', like_new: 'Like New', good: 'Good', fair: 'Fair', poor: 'Poor / For Parts',
};
const CONDITION_COLORS: Record<Condition, string> = {
  new: '#16a34a', like_new: '#22c55e', good: '#06b6d4', fair: '#d97706', poor: '#dc2626',
};

/* ─── Mock AI ─── */
function mockIdentify(): AIIdentification {
  return {
    productName: 'Nike Air Max 90 Sneakers',
    brand: 'Nike',
    category: 'Footwear',
    subcategory: 'Athletic Sneakers',
    upc: '194501055161',
    model: 'Air Max 90',
    color: 'Black/White',
    material: 'Leather, Mesh, Rubber',
    size: 'US 10',
    condition: 'like_new',
    conditionScore: 9,
    conditionNotes: 'Excellent condition. Worn 2-3 times, minimal sole wear. Original box included.',
    defects: ['Light crease on left toe box'],
    keywords: ['nike', 'air max 90', 'sneakers', 'athletic', 'running', 'black white', 'mens'],
  };
}

function mockPricing(): AIPricing {
  return {
    estimatedValue: 130,
    suggestedPrice: 109.99,
    priceRange: { low: 85, high: 140 },
    platformPrices: [
      { platform: 'eBay', suggested: 109.99, avgSold: 115, fees: 14.30, profit: 95.70 },
      { platform: 'Poshmark', suggested: 115.00, avgSold: 110, fees: 23.00, profit: 92.00 },
      { platform: 'Mercari', suggested: 104.99, avgSold: 105, fees: 10.50, profit: 94.50 },
      { platform: 'Amazon', suggested: 119.99, avgSold: 125, fees: 18.00, profit: 102.00 },
      { platform: 'Etsy', suggested: 114.99, avgSold: 112, fees: 7.80, profit: 107.20 },
    ],
    comps: [
      { title: 'Nike Air Max 90 Black/White Sz 10', price: 115, platform: 'eBay', soldDate: '2026-03-07', condition: 'Like New' },
      { title: 'Air Max 90 Mens 10 Black VNDS', price: 105, platform: 'Poshmark', soldDate: '2026-03-06', condition: 'Good' },
      { title: 'Nike AM90 Size 10 w/ Box', price: 125, platform: 'Mercari', soldDate: '2026-03-05', condition: 'New' },
      { title: 'Nike Air Max 90 Essential Black', price: 98, platform: 'eBay', soldDate: '2026-03-03', condition: 'Good' },
    ],
    demandLevel: 'high',
    avgDaysToSell: 4.5,
  };
}

function mockDescription(): AIDescription {
  return {
    title: 'Nike Air Max 90 Sneakers Black/White - Size 10 - Like New w/ Box',
    description: `Nike Air Max 90 Athletic Sneakers in Black/White colorway. Men's Size US 10. Like New condition — worn only 2-3 times with minimal sole wear.

Features:
• Classic Air Max 90 silhouette with visible Air cushioning
• Premium leather and mesh upper
• Rubber waffle outsole for traction
• Original box and extra laces included

Condition: 9/10 — One light crease on left toe box, otherwise pristine. No discoloration, no odor. Insoles clean.

Ships same or next business day with tracking. Returns accepted within 30 days.`,
    tags: ['nike', 'air max 90', 'sneakers', 'mens shoes', 'size 10', 'black white', 'athletic', 'like new'],
    itemSpecifics: {
      'Brand': 'Nike', 'Model': 'Air Max 90', 'Size': 'US 10', 'Color': 'Black/White',
      'Condition': 'Like New', 'UPC': '194501055161', 'Style': 'Athletic',
    },
    platformDescriptions: [
      { platform: 'eBay', title: 'Nike Air Max 90 Black White Mens Size 10 Like New w/ Box', description: 'Nike Air Max 90 in Black/White. Sz 10. Like New, worn 2-3 times. Includes OG box. Light crease on left toe, otherwise pristine. Fast shipping with tracking.' },
      { platform: 'Poshmark', title: 'Nike Air Max 90 • Black/White • Size 10 • Like New', description: 'Selling my Nike Air Max 90s in the classic Black/White colorway. Size 10. Only worn a couple times — basically new! Comes with original box. Minor toe crease. Ships next day!' },
      { platform: 'Mercari', title: 'Nike Air Max 90 Black/White Size 10 Near Mint', description: 'Nike Air Max 90 sneakers. Size 10 mens. Black/White. Worn 2-3x, 9/10 condition. Original box included. One light crease on toe. Ships fast!' },
    ],
  };
}

/* ─── Component ─── */
export default function SmartListerPanel({
  accentColor = '#2563eb',
  accentBg = '#dbeafe',
  marketplaces = ['eBay', 'Poshmark', 'Mercari', 'Amazon', 'Etsy'],
  marketplaceColors = { eBay: '#e53238', Poshmark: '#7f0353', Mercari: '#4dc4e0', Amazon: '#ff9900', Etsy: '#f1641e' },
  productLabel = 'MarketForge',
}: SmartListerPanelProps) {
  const [step, setStep] = useState<Step>('photos');
  const [photos, setPhotos] = useState<PhotoEntry[]>([]);
  const [activePhotoIdx, setActivePhotoIdx] = useState(0);
  const [analyzing, setAnalyzing] = useState(false);
  const [identification, setIdentification] = useState<AIIdentification | null>(null);
  const [pricing, setPricing] = useState<AIPricing | null>(null);
  const [description, setDescription] = useState<AIDescription | null>(null);
  const [selectedPlatforms, setSelectedPlatforms] = useState<Set<string>>(new Set(marketplaces.slice(0, 3)));
  const [listingCreated, setListingCreated] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const stepIndex = STEPS.findIndex(s => s.id === step);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    Array.from(files).forEach(file => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        setPhotos(prev => [...prev, {
          id: `photo-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
          dataUrl: ev.target?.result as string,
          name: file.name,
        }]);
      };
      reader.readAsDataURL(file);
    });
    e.target.value = '';
  };

  const removePhoto = (id: string) => {
    setPhotos(prev => prev.filter(p => p.id !== id));
    if (activePhotoIdx >= photos.length - 1) setActivePhotoIdx(Math.max(0, photos.length - 2));
  };

  const runFullAnalysis = useCallback(async () => {
    setAnalyzing(true);
    await new Promise(r => setTimeout(r, 1800));
    setIdentification(mockIdentify());
    setStep('identify');
    await new Promise(r => setTimeout(r, 1200));
    setPricing(mockPricing());
    await new Promise(r => setTimeout(r, 1200));
    setDescription(mockDescription());
    setAnalyzing(false);
    setStep('describe');
  }, []);

  const runStep = useCallback(async (which: 'identify' | 'price' | 'describe') => {
    setAnalyzing(true);
    await new Promise(r => setTimeout(r, 1500));
    if (which === 'identify') { setIdentification(mockIdentify()); setStep('identify'); }
    if (which === 'price') { setPricing(mockPricing()); setStep('price'); }
    if (which === 'describe') { setDescription(mockDescription()); setStep('describe'); }
    setAnalyzing(false);
  }, []);

  const togglePlatform = (p: string) => {
    const next = new Set(selectedPlatforms);
    if (next.has(p)) next.delete(p); else next.add(p);
    setSelectedPlatforms(next);
  };

  const nextStep = () => {
    const idx = STEPS.findIndex(s => s.id === step);
    if (idx < STEPS.length - 1) {
      const next = STEPS[idx + 1].id;
      if (next === 'identify' && !identification) { runStep('identify'); return; }
      if (next === 'price' && !pricing) { runStep('price'); return; }
      if (next === 'describe' && !description) { runStep('describe'); return; }
      setStep(next);
    }
  };

  const prevStep = () => {
    const idx = STEPS.findIndex(s => s.id === step);
    if (idx > 0) setStep(STEPS[idx - 1].id);
  };

  const resetAll = () => {
    setPhotos([]); setActivePhotoIdx(0); setIdentification(null);
    setPricing(null); setDescription(null); setStep('photos');
    setListingCreated(false); setSelectedPlatforms(new Set(marketplaces.slice(0, 3)));
  };

  /* ─── Sub-renders ─── */
  const loadingBox = (title: string, sub: string) => (
    <div className="empire-card flat" style={{ textAlign: 'center', padding: '60px 24px' }}>
      {analyzing ? (
        <div style={{ width: 40, height: 40, border: `3px solid #e5e7eb`, borderTopColor: accentColor, borderRadius: '50%', margin: '0 auto 16px' }} className="animate-spin" />
      ) : (
        <Sparkles size={28} style={{ color: accentColor, margin: '0 auto 16px' }} />
      )}
      <div style={{ fontWeight: 600, fontSize: 14 }}>{title}</div>
      <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>{sub}</div>
    </div>
  );

  /* ── Progress bar ── */
  const renderProgress = () => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 20 }}>
      {STEPS.map((s, i) => {
        const Icon = s.icon;
        const isActive = s.id === step;
        const isDone = i < stepIndex;
        const isLocked = i > stepIndex + 1;
        return (
          <React.Fragment key={s.id}>
            <button onClick={() => !isLocked && setStep(s.id)} disabled={isLocked}
              style={{
                flex: 1, display: 'flex', alignItems: 'center', gap: 6, padding: '8px 10px',
                borderRadius: 10, fontSize: 12, fontWeight: 600, border: 'none', cursor: isLocked ? 'not-allowed' : 'pointer',
                background: isActive ? accentBg : isDone ? '#f0fdf4' : '#f9fafb',
                color: isActive ? accentColor : isDone ? '#16a34a' : isLocked ? '#ccc' : '#777',
                outline: isActive ? `2px solid ${accentColor}` : 'none', outlineOffset: -2,
              }}>
              {isDone ? <Check size={13} /> : <Icon size={13} />}
              {s.label}
            </button>
            {i < STEPS.length - 1 && <ChevronRight size={13} style={{ color: '#ccc', flexShrink: 0 }} />}
          </React.Fragment>
        );
      })}
    </div>
  );

  /* ── Step 1: Photos ── */
  const renderPhotos = () => (
    <div>
      <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 4 }}>Snap Your Item</h3>
      <p style={{ fontSize: 13, color: '#999', marginBottom: 16 }}>Upload or take photos. Include labels, barcodes, multiple angles.</p>
      {photos.length === 0 ? (
        <div className="empire-card flat" style={{ textAlign: 'center', padding: '60px 24px', border: '2px dashed #ddd' }}
          onDragOver={e => { e.preventDefault(); e.currentTarget.style.borderColor = accentColor; }}
          onDragLeave={e => { e.currentTarget.style.borderColor = '#ddd'; }}
          onDrop={e => { e.preventDefault(); e.currentTarget.style.borderColor = '#ddd'; if (e.dataTransfer.files.length) handleFileUpload({ target: { files: e.dataTransfer.files, value: '' } } as any); }}>
          <div style={{ width: 56, height: 56, borderRadius: 16, background: accentBg, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 14px' }}>
            <Camera size={26} style={{ color: accentColor }} />
          </div>
          <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>Drop photos here</div>
          <div style={{ fontSize: 12, color: '#999', marginBottom: 16 }}>JPG, PNG up to 20MB. Up to 12 photos.</div>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
            <button onClick={() => fileInputRef.current?.click()} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '9px 18px', background: accentColor, color: '#fff', border: 'none', borderRadius: 10, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
              <Upload size={14} /> Upload
            </button>
            <button onClick={() => cameraInputRef.current?.click()} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '9px 18px', background: '#fff', color: '#555', border: '1px solid #ddd', borderRadius: 10, fontSize: 13, fontWeight: 500, cursor: 'pointer' }}>
              <Camera size={14} /> Camera
            </button>
          </div>
        </div>
      ) : (
        <div>
          <div className="empire-card flat" style={{ padding: 0, overflow: 'hidden', height: 300, position: 'relative', marginBottom: 10 }}>
            <img src={photos[activePhotoIdx]?.dataUrl} alt="" style={{ width: '100%', height: '100%', objectFit: 'contain', background: '#fafafa' }} />
            <button onClick={() => removePhoto(photos[activePhotoIdx]?.id)} style={{ position: 'absolute', top: 10, right: 10, width: 30, height: 30, borderRadius: 8, background: 'rgba(255,255,255,0.9)', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Trash2 size={13} style={{ color: '#dc2626' }} />
            </button>
            <div style={{ position: 'absolute', bottom: 10, left: 10, background: 'rgba(0,0,0,0.6)', color: '#fff', padding: '3px 8px', borderRadius: 6, fontSize: 11, fontWeight: 600 }}>
              {activePhotoIdx + 1}/{photos.length}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 6, marginBottom: 14, overflowX: 'auto', paddingBottom: 4 }}>
            {photos.map((p, i) => (
              <button key={p.id} onClick={() => setActivePhotoIdx(i)} style={{ width: 64, height: 48, borderRadius: 8, overflow: 'hidden', border: i === activePhotoIdx ? `2px solid ${accentColor}` : '2px solid #ddd', flexShrink: 0, cursor: 'pointer', padding: 0 }}>
                <img src={p.dataUrl} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              </button>
            ))}
            {photos.length < 12 && (
              <button onClick={() => fileInputRef.current?.click()} style={{ width: 64, height: 48, borderRadius: 8, border: '2px dashed #ddd', flexShrink: 0, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'transparent' }}>
                <Plus size={16} style={{ color: '#999' }} />
              </button>
            )}
          </div>
          <button onClick={runFullAnalysis} disabled={analyzing} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, padding: '12px 20px', background: accentColor, color: '#fff', border: 'none', borderRadius: 10, fontSize: 14, fontWeight: 700, cursor: analyzing ? 'wait' : 'pointer', opacity: analyzing ? 0.7 : 1 }}>
            {analyzing ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
            {analyzing ? 'Analyzing...' : 'AI Full Analysis — Identify, Price & Describe'}
          </button>
        </div>
      )}
      <input ref={fileInputRef} type="file" accept="image/*" multiple onChange={handleFileUpload} style={{ display: 'none' }} />
      <input ref={cameraInputRef} type="file" accept="image/*" onChange={handleFileUpload} style={{ display: 'none' }} />
    </div>
  );

  /* ── Step 2: Identify ── */
  const renderIdentify = () => {
    if (analyzing) return loadingBox('Identifying item...', 'Scanning brand, model, UPC, condition...');
    if (!identification) return loadingBox('Ready to identify', 'Click Next to analyze');
    const id = identification;
    return (
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <h3 style={{ fontSize: 17, fontWeight: 700 }}>AI Identification</h3>
          <button onClick={() => runStep('identify')} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '6px 12px', background: '#fff', border: '1px solid #ddd', borderRadius: 8, fontSize: 12, fontWeight: 500, cursor: 'pointer' }}><RotateCw size={12} /> Re-Analyze</button>
        </div>
        <div className="empire-card flat" style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', gap: 14 }}>
            {photos[0] && <div style={{ width: 80, height: 80, borderRadius: 10, overflow: 'hidden', border: '1px solid #eee', flexShrink: 0 }}><img src={photos[0].dataUrl} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /></div>}
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', marginBottom: 4 }}>Identified Product</div>
              <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 6 }}>{id.productName}</div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                <span style={{ padding: '2px 10px', borderRadius: 9999, fontSize: 11, fontWeight: 600, background: '#dcfce7', color: '#16a34a' }}>{id.brand}</span>
                <span style={{ padding: '2px 10px', borderRadius: 9999, fontSize: 11, fontWeight: 600, background: '#f3f4f6', color: '#6b7280' }}>{id.category}</span>
                {id.upc && <span style={{ padding: '2px 10px', borderRadius: 9999, fontSize: 11, fontWeight: 600, background: '#fff7ed', color: '#d97706', fontFamily: 'monospace' }}>UPC: {id.upc}</span>}
              </div>
            </div>
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 12 }}>
          {[{ l: 'Brand', v: id.brand }, { l: 'Model', v: id.model }, { l: 'Category', v: `${id.category} › ${id.subcategory}` }, { l: 'Color', v: id.color }, { l: 'Material', v: id.material }, { l: 'Size', v: id.size }].map(x => (
            <div key={x.l} className="empire-card flat" style={{ padding: 10 }}>
              <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999' }}>{x.l}</div>
              <div style={{ fontSize: 13, fontWeight: 600, marginTop: 2 }}>{x.v}</div>
            </div>
          ))}
        </div>
        <div className="empire-card flat" style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999' }}>Condition</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 14, fontWeight: 700, color: CONDITION_COLORS[id.condition] }}>{id.conditionScore}/10</span>
              <span style={{ padding: '2px 10px', borderRadius: 9999, fontSize: 11, fontWeight: 600, background: CONDITION_COLORS[id.condition] + '18', color: CONDITION_COLORS[id.condition] }}>{CONDITION_LABELS[id.condition]}</span>
            </div>
          </div>
          <div style={{ width: '100%', height: 6, borderRadius: 3, background: '#f3f4f6', marginBottom: 10 }}>
            <div style={{ height: '100%', borderRadius: 3, width: `${id.conditionScore * 10}%`, background: CONDITION_COLORS[id.condition] }} />
          </div>
          <p style={{ fontSize: 13, marginBottom: 6 }}>{id.conditionNotes}</p>
          {id.defects.length > 0 && id.defects.map((d, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'start', gap: 5, fontSize: 12, color: '#d97706' }}>
              <AlertCircle size={12} style={{ marginTop: 2, flexShrink: 0 }} /> {d}
            </div>
          ))}
        </div>
        <div className="empire-card flat">
          <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', marginBottom: 8 }}>Keywords</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
            {id.keywords.map(k => <span key={k} style={{ padding: '2px 8px', borderRadius: 9999, fontSize: 11, fontWeight: 500, background: accentBg, color: accentColor }}>{k}</span>)}
          </div>
        </div>
      </div>
    );
  };

  /* ── Step 3: Price ── */
  const renderPrice = () => {
    if (analyzing) return loadingBox('Checking prices...', 'Searching recent sold listings...');
    if (!pricing) return loadingBox('Ready to price', 'Click Next to check market prices');
    const p = pricing;
    return (
      <div>
        <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 14 }}>AI Pricing Intelligence</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 14 }}>
          <div className="empire-card flat" style={{ textAlign: 'center', padding: 14 }}>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999' }}>Suggested</div>
            <div style={{ fontSize: 22, fontWeight: 700, color: accentColor }}>${p.suggestedPrice}</div>
          </div>
          <div className="empire-card flat" style={{ textAlign: 'center', padding: 14 }}>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999' }}>Range</div>
            <div style={{ fontSize: 16, fontWeight: 700 }}>${p.priceRange.low} – ${p.priceRange.high}</div>
          </div>
          <div className="empire-card flat" style={{ textAlign: 'center', padding: 14 }}>
            <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999' }}>Sell Time</div>
            <div style={{ fontSize: 16, fontWeight: 700 }}>{p.avgDaysToSell} days</div>
            <span style={{ padding: '2px 8px', borderRadius: 9999, fontSize: 10, fontWeight: 600, background: p.demandLevel === 'high' ? '#dcfce7' : '#fff7ed', color: p.demandLevel === 'high' ? '#16a34a' : '#d97706' }}>{p.demandLevel} demand</span>
          </div>
        </div>
        <div className="empire-card flat" style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', marginBottom: 10 }}>Per-Platform Breakdown</div>
          {p.platformPrices.map(pp => (
            <div key={pp.platform} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', borderRadius: 8, background: '#fafafa', marginBottom: 4 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: marketplaceColors[pp.platform] || '#777' }} />
              <div style={{ fontSize: 13, fontWeight: 600, flex: 1 }}>{pp.platform}</div>
              <div style={{ textAlign: 'center', minWidth: 65 }}><div style={{ fontSize: 10, color: '#999' }}>Price</div><div style={{ fontSize: 13, fontWeight: 700 }}>${pp.suggested}</div></div>
              <div style={{ textAlign: 'center', minWidth: 50 }}><div style={{ fontSize: 10, color: '#999' }}>Fees</div><div style={{ fontSize: 12, color: '#dc2626' }}>-${pp.fees}</div></div>
              <div style={{ textAlign: 'center', minWidth: 55 }}><div style={{ fontSize: 10, color: '#999' }}>Profit</div><div style={{ fontSize: 13, fontWeight: 700, color: '#16a34a' }}>${pp.profit}</div></div>
            </div>
          ))}
        </div>
        <div className="empire-card flat">
          <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', marginBottom: 8 }}>Recent Comps</div>
          {p.comps.map((c, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 0', borderBottom: i < p.comps.length - 1 ? '1px solid #f0f0f0' : 'none', fontSize: 12 }}>
              <div style={{ flex: 1 }}>{c.title}</div>
              <div style={{ fontWeight: 600 }}>{c.platform}</div>
              <div style={{ fontWeight: 700, color: '#16a34a' }}>${c.price}</div>
              <div style={{ color: '#999', fontSize: 11 }}>{c.soldDate}</div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  /* ── Step 4: Describe ── */
  const renderDescribe = () => {
    if (analyzing) return loadingBox('Writing descriptions...', 'Generating SEO-optimized listing content...');
    if (!description) return loadingBox('Ready to describe', 'Click Next to generate');
    const d = description;
    return (
      <div>
        <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 14 }}>AI-Generated Content</h3>
        <div className="empire-card flat" style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', marginBottom: 8 }}>Master Listing</div>
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#555', marginBottom: 4 }}>Title</div>
            <input defaultValue={d.title} style={{ width: '100%', padding: '8px 10px', border: '1px solid #ddd', borderRadius: 8, fontSize: 13, fontWeight: 600 }} />
          </div>
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#555', marginBottom: 4 }}>Description</div>
            <textarea defaultValue={d.description} rows={7} style={{ width: '100%', padding: '8px 10px', border: '1px solid #ddd', borderRadius: 8, fontSize: 12, lineHeight: 1.6, fontFamily: 'inherit', resize: 'vertical' }} />
          </div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#555', marginBottom: 4 }}>Tags</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
              {d.tags.map(t => <span key={t} style={{ padding: '2px 8px', borderRadius: 9999, fontSize: 11, fontWeight: 500, background: accentBg, color: accentColor, display: 'flex', alignItems: 'center', gap: 3 }}>{t} <X size={9} style={{ cursor: 'pointer' }} /></span>)}
            </div>
          </div>
        </div>
        <div className="empire-card flat" style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', marginBottom: 8 }}>Item Specifics</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
            {Object.entries(d.itemSpecifics).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', gap: 6, padding: '5px 8px', borderRadius: 6, background: '#fafafa' }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: '#999', minWidth: 70 }}>{k}</span>
                <span style={{ fontSize: 12, fontWeight: 500 }}>{v}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="empire-card flat">
          <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', marginBottom: 10 }}>Platform Versions</div>
          {d.platformDescriptions.map(pd => (
            <div key={pd.platform} style={{ padding: 10, borderRadius: 10, border: '1px solid #eee', marginBottom: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: marketplaceColors[pd.platform] || '#777' }} />
                <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: marketplaceColors[pd.platform] || '#777' }}>{pd.platform}</span>
                <button style={{ marginLeft: 'auto', fontSize: 11, display: 'flex', alignItems: 'center', gap: 3, color: '#999', background: 'none', border: 'none', cursor: 'pointer' }}><Copy size={10} /> Copy</button>
              </div>
              <input defaultValue={pd.title} style={{ width: '100%', padding: '5px 8px', border: '1px solid #eee', borderRadius: 6, fontSize: 12, fontWeight: 600, marginBottom: 4 }} />
              <textarea defaultValue={pd.description} rows={2} style={{ width: '100%', padding: '5px 8px', border: '1px solid #eee', borderRadius: 6, fontSize: 11, lineHeight: 1.5, fontFamily: 'inherit', resize: 'vertical' }} />
            </div>
          ))}
        </div>
      </div>
    );
  };

  /* ── Step 5: Review ── */
  const renderReview = () => {
    if (!identification || !pricing || !description) return (
      <div className="empire-card flat" style={{ textAlign: 'center', padding: '50px 24px' }}>
        <AlertCircle size={28} style={{ color: '#d97706', margin: '0 auto 10px' }} />
        <div style={{ fontWeight: 600, fontSize: 14 }}>Analysis Incomplete</div>
        <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>Complete all steps first.</div>
      </div>
    );

    return (
      <div>
        <h3 style={{ fontSize: 17, fontWeight: 700, marginBottom: 14 }}>Review & Publish</h3>
        {listingCreated && (
          <div style={{ padding: '12px 16px', borderRadius: 12, background: '#dcfce7', border: '1px solid #86efac', display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <Check size={18} style={{ color: '#16a34a' }} />
            <div><div style={{ fontSize: 13, fontWeight: 700, color: '#16a34a' }}>Listing Created!</div><div style={{ fontSize: 11, color: '#15803d' }}>Published to {selectedPlatforms.size} platform{selectedPlatforms.size !== 1 ? 's' : ''}.</div></div>
          </div>
        )}
        <div className="empire-card flat" style={{ marginBottom: 14 }}>
          <div style={{ display: 'flex', gap: 14 }}>
            {photos[0] && <div style={{ width: 90, height: 90, borderRadius: 10, overflow: 'hidden', border: '1px solid #eee', flexShrink: 0 }}><img src={photos[0].dataUrl} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /></div>}
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>{description.title}</div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 6 }}>
                <span style={{ padding: '2px 8px', borderRadius: 9999, fontSize: 10, fontWeight: 600, background: '#dcfce7', color: '#16a34a' }}>{identification.brand}</span>
                <span style={{ padding: '2px 8px', borderRadius: 9999, fontSize: 10, fontWeight: 600, background: CONDITION_COLORS[identification.condition] + '18', color: CONDITION_COLORS[identification.condition] }}>{CONDITION_LABELS[identification.condition]}</span>
              </div>
              <div style={{ fontSize: 13 }}><span style={{ color: '#999' }}>Price: </span><span style={{ fontWeight: 700, color: accentColor }}>${pricing.suggestedPrice}</span> <span style={{ color: '#999', marginLeft: 10 }}>Photos: </span><span style={{ fontWeight: 600 }}>{photos.length}</span></div>
            </div>
          </div>
        </div>
        <div className="empire-card flat" style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', marginBottom: 10 }}>Publish To</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
            {marketplaces.map(mp => {
              const active = selectedPlatforms.has(mp);
              const color = marketplaceColors[mp] || '#777';
              const pp = pricing.platformPrices.find(x => x.platform === mp);
              return (
                <button key={mp} onClick={() => togglePlatform(mp)} style={{ padding: 10, borderRadius: 10, textAlign: 'left', border: active ? `2px solid ${color}` : '2px solid #eee', background: active ? color + '08' : '#fff', cursor: 'pointer' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: active ? color : '#999' }}>{mp}</span>
                    {active && <Check size={13} style={{ color }} />}
                  </div>
                  {pp && <div style={{ fontSize: 10, color: '#999' }}>${pp.suggested} → <span style={{ color: '#16a34a' }}>${pp.profit} profit</span></div>}
                </button>
              );
            })}
          </div>
        </div>
        <button onClick={() => setListingCreated(true)} style={{ width: '100%', padding: '12px 20px', background: accentColor, color: '#fff', border: 'none', borderRadius: 10, fontSize: 14, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
          <ShoppingCart size={16} /> Publish to {selectedPlatforms.size} Platform{selectedPlatforms.size !== 1 ? 's' : ''}
        </button>
      </div>
    );
  };

  /* ─── Main ─── */
  return (
    <div style={{ padding: '24px 28px', maxWidth: 860, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700 }}>Smart Lister</h2>
          <p style={{ fontSize: 13, color: '#999' }}>Snap → Identify → Price → Describe → List</p>
        </div>
        {(photos.length > 0 || identification) && (
          <button onClick={resetAll} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '6px 12px', background: '#fff', border: '1px solid #ddd', borderRadius: 8, fontSize: 12, fontWeight: 500, cursor: 'pointer' }}><RotateCw size={12} /> Start Over</button>
        )}
      </div>
      {renderProgress()}
      <div style={{ marginBottom: 24 }}>
        {step === 'photos' && renderPhotos()}
        {step === 'identify' && renderIdentify()}
        {step === 'price' && renderPrice()}
        {step === 'describe' && renderDescribe()}
        {step === 'review' && renderReview()}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button onClick={prevStep} disabled={stepIndex === 0} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '8px 14px', background: '#fff', border: '1px solid #ddd', borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: stepIndex === 0 ? 'not-allowed' : 'pointer', opacity: stepIndex === 0 ? 0.4 : 1 }}>
          <ArrowLeft size={14} /> Back
        </button>
        <span style={{ fontSize: 12, color: '#999' }}>Step {stepIndex + 1} of {STEPS.length}</span>
        {stepIndex < STEPS.length - 1 ? (
          <button onClick={nextStep} disabled={photos.length === 0 || analyzing} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '8px 14px', background: accentColor, color: '#fff', border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: (photos.length === 0 || analyzing) ? 'not-allowed' : 'pointer', opacity: (photos.length === 0 || analyzing) ? 0.5 : 1 }}>
            Next <ArrowRight size={14} />
          </button>
        ) : <div />}
      </div>
    </div>
  );
}
