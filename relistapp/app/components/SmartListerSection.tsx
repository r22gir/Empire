'use client';

import { useState, useRef, useCallback } from 'react';
import {
  Camera, Upload, X, ChevronRight, ChevronDown, Sparkles, Search,
  Tag, DollarSign, Package, RotateCw, Check, AlertCircle, Image,
  ScanBarcode, Star, TrendingUp, ShoppingCart, Copy, Pencil,
  Loader2, Plus, Trash2, Eye, ArrowRight, ArrowLeft, Zap,
} from 'lucide-react';
import { Platform, Condition } from '../lib/types';
import { PLATFORM_COLORS } from '../lib/mock-data';

/* ─── Types ─── */
interface PhotoEntry {
  id: string;
  dataUrl: string;
  name: string;
}

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
  conditionScore: number; // 1-10
  conditionNotes: string;
  defects: string[];
  keywords: string[];
}

interface AIPricing {
  estimatedValue: number;
  suggestedPrice: number;
  priceRange: { low: number; high: number };
  platformPrices: { platform: Platform; suggested: number; avgSold: number; fees: number; profit: number }[];
  comps: { title: string; price: number; platform: string; soldDate: string; condition: string }[];
  demandLevel: 'high' | 'medium' | 'low';
  avgDaysToSell: number;
}

interface AIDescription {
  title: string;
  description: string;
  tags: string[];
  itemSpecifics: Record<string, string>;
  platformDescriptions: { platform: Platform; title: string; description: string }[];
  seoKeywords: string[];
}

type Step = 'photos' | 'identify' | 'price' | 'describe' | 'review';

const STEPS: { id: Step; label: string; icon: any }[] = [
  { id: 'photos', label: 'Photos', icon: Camera },
  { id: 'identify', label: 'Identify', icon: ScanBarcode },
  { id: 'price', label: 'Price', icon: DollarSign },
  { id: 'describe', label: 'Describe', icon: Tag },
  { id: 'review', label: 'Review & List', icon: ShoppingCart },
];

const CONDITION_LABELS: Record<Condition, string> = {
  new: 'New / Sealed',
  like_new: 'Like New',
  good: 'Good',
  fair: 'Fair',
  poor: 'Poor / For Parts',
};

const CONDITION_COLORS: Record<Condition, string> = {
  new: '#16a34a',
  like_new: '#22c55e',
  good: '#06b6d4',
  fair: '#d97706',
  poor: '#dc2626',
};

/* ─── Mock AI Responses ─── */
function mockIdentify(): AIIdentification {
  return {
    productName: 'Sony WH-1000XM5 Wireless Noise Canceling Headphones',
    brand: 'Sony',
    category: 'Electronics',
    subcategory: 'Headphones',
    upc: '027242923416',
    model: 'WH-1000XM5',
    color: 'Black',
    material: 'Synthetic Leather, Plastic',
    size: 'One Size',
    condition: 'like_new',
    conditionScore: 8,
    conditionNotes: 'Excellent condition with minimal wear. Ear cushions intact, no scratches on headband. All buttons functional.',
    defects: ['Minor scuff on left ear cup (barely visible)'],
    keywords: ['sony', 'wh-1000xm5', 'noise canceling', 'wireless', 'bluetooth', 'headphones', 'over-ear'],
  };
}

function mockPricing(): AIPricing {
  return {
    estimatedValue: 230,
    suggestedPrice: 199.99,
    priceRange: { low: 175, high: 250 },
    platformPrices: [
      { platform: 'ebay', suggested: 199.99, avgSold: 205, fees: 26, profit: 174 },
      { platform: 'etsy', suggested: 209.99, avgSold: 215, fees: 14, profit: 196 },
      { platform: 'shopify', suggested: 219.99, avgSold: 220, fees: 6.60, profit: 213 },
      { platform: 'facebook', suggested: 189.99, avgSold: 185, fees: 0, profit: 190 },
      { platform: 'mercari', suggested: 194.99, avgSold: 195, fees: 19.50, profit: 175 },
      { platform: 'amazon', suggested: 214.99, avgSold: 225, fees: 32.25, profit: 183 },
    ],
    comps: [
      { title: 'Sony WH-1000XM5 Black - Excellent', price: 210, platform: 'eBay', soldDate: '2026-03-07', condition: 'Like New' },
      { title: 'Sony WH1000XM5 Wireless NC Headphones', price: 195, platform: 'eBay', soldDate: '2026-03-05', condition: 'Good' },
      { title: 'Sony WH-1000XM5 Over-Ear Headphones', price: 225, platform: 'Mercari', soldDate: '2026-03-04', condition: 'New' },
      { title: 'Sony 1000XM5 Bluetooth Headphones Black', price: 189, platform: 'Facebook', soldDate: '2026-03-03', condition: 'Like New' },
      { title: 'WH-1000XM5 Sony Noise Cancel', price: 205, platform: 'eBay', soldDate: '2026-03-01', condition: 'Good' },
    ],
    demandLevel: 'high',
    avgDaysToSell: 3.2,
  };
}

function mockDescription(): AIDescription {
  return {
    title: 'Sony WH-1000XM5 Wireless Noise Canceling Headphones - Black - Like New',
    description: `Sony WH-1000XM5 Wireless Noise Canceling Over-Ear Headphones in Black. Industry-leading noise cancellation with Auto NC Optimizer. 30-hour battery life with quick charging (3 min charge = 3 hours playback). Multipoint connection for seamless switching between devices.

Features:
• Integrated Processor V1 with 8 microphones for premium call quality
• Speak-to-Chat auto-pauses music when you talk
• Touch sensor controls on ear cup
• Lightweight design at 250g with soft-fit leather
• Includes carrying case, USB-C cable, and 3.5mm audio cable

Condition: Like New — minimal wear, all functions perfect. One barely visible scuff on left ear cup. Ear cushions in excellent shape.

Ships same or next business day with tracking. 30-day returns accepted.`,
    tags: ['sony', 'wh-1000xm5', 'noise canceling', 'wireless headphones', 'bluetooth', 'over-ear', 'premium audio', 'like new'],
    itemSpecifics: {
      'Brand': 'Sony',
      'Model': 'WH-1000XM5',
      'Type': 'Over-Ear',
      'Connectivity': 'Bluetooth 5.2, 3.5mm',
      'Color': 'Black',
      'Noise Cancellation': 'Active',
      'Battery Life': '30 Hours',
      'Condition': 'Like New',
      'UPC': '027242923416',
    },
    platformDescriptions: [
      {
        platform: 'ebay',
        title: 'Sony WH-1000XM5 Wireless NC Headphones Black - Like New w/ Case',
        description: 'Sony WH-1000XM5 in Like New condition. Industry-leading ANC, 30hr battery, multipoint. Includes case, USB-C cable, 3.5mm cable. One minor scuff on left cup. Ships fast with tracking. 30-day returns.',
      },
      {
        platform: 'etsy',
        title: 'Sony WH-1000XM5 Premium Wireless Noise Canceling Headphones',
        description: 'Premium Sony WH-1000XM5 headphones in excellent Like New condition. Perfect for audiophiles and remote workers. Features industry-best noise cancellation, 30-hour battery, and crystal-clear call quality. Complete with carrying case and all cables.',
      },
      {
        platform: 'shopify',
        title: 'Sony WH-1000XM5 — Wireless Noise Canceling — Like New',
        description: 'Experience industry-leading noise cancellation with the Sony WH-1000XM5. 30-hour battery, multipoint Bluetooth 5.2, and speak-to-chat technology. This Like New unit includes the original carrying case, USB-C cable, and 3.5mm audio cable.',
      },
    ],
    seoKeywords: ['sony wh-1000xm5', 'noise canceling headphones', 'wireless headphones', 'sony headphones', 'bluetooth headphones', 'over ear headphones'],
  };
}

/* ─── Component ─── */
export default function SmartListerSection() {
  const [step, setStep] = useState<Step>('photos');
  const [photos, setPhotos] = useState<PhotoEntry[]>([]);
  const [activePhotoIdx, setActivePhotoIdx] = useState(0);
  const [analyzing, setAnalyzing] = useState(false);
  const [identification, setIdentification] = useState<AIIdentification | null>(null);
  const [pricing, setPricing] = useState<AIPricing | null>(null);
  const [description, setDescription] = useState<AIDescription | null>(null);
  const [selectedPlatforms, setSelectedPlatforms] = useState<Set<Platform>>(new Set<Platform>(['ebay', 'etsy', 'shopify']));
  const [editingField, setEditingField] = useState<string | null>(null);
  const [listingCreated, setListingCreated] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const stepIndex = STEPS.findIndex(s => s.id === step);

  /* ─── Photo handlers ─── */
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    Array.from(files).forEach(file => {
      const reader = new FileReader();
      reader.onload = (ev) => {
        const dataUrl = ev.target?.result as string;
        setPhotos(prev => [...prev, {
          id: `photo-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
          dataUrl,
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

  /* ─── AI Analysis (mock for now, will call backend) ─── */
  const runIdentification = useCallback(async () => {
    setAnalyzing(true);
    // In production: POST /api/v1/vision/identify with photos[0].dataUrl
    await new Promise(r => setTimeout(r, 2000));
    setIdentification(mockIdentify());
    setAnalyzing(false);
    setStep('identify');
  }, []);

  const runPricing = useCallback(async () => {
    setAnalyzing(true);
    // In production: POST /api/v1/relist/price-check with identification data
    await new Promise(r => setTimeout(r, 1800));
    setPricing(mockPricing());
    setAnalyzing(false);
    setStep('price');
  }, []);

  const runDescription = useCallback(async () => {
    setAnalyzing(true);
    // In production: POST /api/v1/relist/generate-description with identification + pricing
    await new Promise(r => setTimeout(r, 2200));
    setDescription(mockDescription());
    setAnalyzing(false);
    setStep('describe');
  }, []);

  const runFullAnalysis = useCallback(async () => {
    setAnalyzing(true);
    await new Promise(r => setTimeout(r, 2000));
    setIdentification(mockIdentify());
    setStep('identify');
    await new Promise(r => setTimeout(r, 1500));
    setPricing(mockPricing());
    await new Promise(r => setTimeout(r, 1500));
    setDescription(mockDescription());
    setAnalyzing(false);
    setStep('describe');
  }, []);

  const createListing = useCallback(() => {
    setListingCreated(true);
    setTimeout(() => setListingCreated(false), 3000);
  }, []);

  const togglePlatform = (p: Platform) => {
    const next = new Set(selectedPlatforms);
    if (next.has(p)) next.delete(p); else next.add(p);
    setSelectedPlatforms(next);
  };

  const canProceed = () => {
    if (step === 'photos') return photos.length > 0;
    if (step === 'identify') return !!identification;
    if (step === 'price') return !!pricing;
    if (step === 'describe') return !!description;
    return true;
  };

  const nextStep = () => {
    const idx = STEPS.findIndex(s => s.id === step);
    if (idx < STEPS.length - 1) {
      const next = STEPS[idx + 1].id;
      if (next === 'identify' && !identification) { runIdentification(); return; }
      if (next === 'price' && !pricing) { runPricing(); return; }
      if (next === 'describe' && !description) { runDescription(); return; }
      setStep(next);
    }
  };

  const prevStep = () => {
    const idx = STEPS.findIndex(s => s.id === step);
    if (idx > 0) setStep(STEPS[idx - 1].id);
  };

  const resetAll = () => {
    setPhotos([]);
    setActivePhotoIdx(0);
    setIdentification(null);
    setPricing(null);
    setDescription(null);
    setStep('photos');
    setListingCreated(false);
    setSelectedPlatforms(new Set<Platform>(['ebay', 'etsy', 'shopify']));
  };

  /* ─── Render helpers ─── */
  const renderProgressBar = () => (
    <div className="flex items-center gap-1 mb-6">
      {STEPS.map((s, i) => {
        const Icon = s.icon;
        const isActive = s.id === step;
        const isDone = i < stepIndex;
        const isLocked = i > stepIndex + 1;
        return (
          <div key={s.id} className="flex items-center flex-1">
            <button
              onClick={() => !isLocked && setStep(s.id)}
              disabled={isLocked}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold transition-all w-full"
              style={{
                background: isActive ? '#ecfeff' : isDone ? '#f0fdf4' : '#f9fafb',
                color: isActive ? '#06b6d4' : isDone ? '#16a34a' : isLocked ? '#ccc' : '#777',
                border: isActive ? '1.5px solid #06b6d4' : '1.5px solid transparent',
                cursor: isLocked ? 'not-allowed' : 'pointer',
              }}
            >
              {isDone ? <Check size={14} /> : <Icon size={14} />}
              <span className="hidden sm:inline">{s.label}</span>
              <span className="sm:hidden">{i + 1}</span>
            </button>
            {i < STEPS.length - 1 && (
              <ChevronRight size={14} className="mx-0.5 shrink-0" style={{ color: '#ccc' }} />
            )}
          </div>
        );
      })}
    </div>
  );

  /* ── Step 1: Photos ── */
  const renderPhotosStep = () => (
    <div>
      <h3 className="text-lg font-bold mb-1">Snap Your Item</h3>
      <p className="text-sm mb-4" style={{ color: 'var(--muted)' }}>
        Take or upload photos. More angles = better AI identification. Include any labels, tags, barcodes.
      </p>

      {photos.length === 0 ? (
        <div className="empire-card flex flex-col items-center justify-center py-16 border-2 border-dashed"
          style={{ borderColor: 'var(--border)' }}
          onDragOver={e => { e.preventDefault(); e.currentTarget.style.borderColor = '#06b6d4'; }}
          onDragLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; }}
          onDrop={e => {
            e.preventDefault();
            e.currentTarget.style.borderColor = 'var(--border)';
            const files = e.dataTransfer.files;
            if (files.length) {
              const fakeEvent = { target: { files, value: '' } } as any;
              handleFileUpload(fakeEvent);
            }
          }}
        >
          <div className="w-16 h-16 rounded-2xl bg-[#ecfeff] flex items-center justify-center mb-4">
            <Camera size={28} style={{ color: '#06b6d4' }} />
          </div>
          <p className="font-semibold text-sm mb-1">Drop photos here or click to upload</p>
          <p className="text-xs mb-4" style={{ color: 'var(--muted)' }}>JPG, PNG up to 20MB each. Up to 12 photos.</p>
          <div className="flex gap-3">
            <button className="btn-primary" onClick={() => fileInputRef.current?.click()}>
              <Upload size={15} /> Upload Photos
            </button>
            <button className="btn-secondary" onClick={() => cameraInputRef.current?.click()}>
              <Camera size={15} /> Take Photo
            </button>
          </div>
        </div>
      ) : (
        <div>
          {/* Main photo preview */}
          <div className="empire-card p-0 overflow-hidden mb-3" style={{ height: 360, position: 'relative' }}>
            <img
              src={photos[activePhotoIdx]?.dataUrl}
              alt="Item"
              style={{ width: '100%', height: '100%', objectFit: 'contain', background: '#f9fafb' }}
            />
            <div className="absolute top-3 right-3 flex gap-2">
              <button className="w-8 h-8 rounded-lg bg-white/90 flex items-center justify-center shadow-sm hover:bg-white"
                onClick={() => removePhoto(photos[activePhotoIdx]?.id)}>
                <Trash2 size={14} style={{ color: '#dc2626' }} />
              </button>
            </div>
            <div className="absolute bottom-3 left-3 px-2 py-1 rounded-md text-xs font-semibold"
              style={{ background: 'rgba(0,0,0,0.6)', color: 'white' }}>
              {activePhotoIdx + 1} / {photos.length}
            </div>
          </div>

          {/* Thumbnails */}
          <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
            {photos.map((p, i) => (
              <button key={p.id} onClick={() => setActivePhotoIdx(i)}
                className="shrink-0 rounded-lg overflow-hidden transition-all"
                style={{
                  width: 72, height: 56,
                  border: i === activePhotoIdx ? '2px solid #06b6d4' : '2px solid var(--border)',
                  boxShadow: i === activePhotoIdx ? '0 0 0 2px rgba(6,182,212,0.2)' : 'none',
                }}>
                <img src={p.dataUrl} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              </button>
            ))}
            {photos.length < 12 && (
              <button onClick={() => fileInputRef.current?.click()}
                className="shrink-0 rounded-lg flex items-center justify-center transition-all hover:border-[#06b6d4]"
                style={{ width: 72, height: 56, border: '2px dashed var(--border)' }}>
                <Plus size={18} style={{ color: 'var(--muted)' }} />
              </button>
            )}
          </div>

          {/* Quick-analyze button */}
          <div className="flex gap-3">
            <button className="btn-primary flex-1 justify-center py-3" onClick={runFullAnalysis} disabled={analyzing}>
              {analyzing ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
              {analyzing ? 'Analyzing...' : 'AI Full Analysis — Identify, Price & Describe'}
            </button>
          </div>
          <p className="text-xs mt-2 text-center" style={{ color: 'var(--muted)' }}>
            Or step through each stage using the Next button below
          </p>
        </div>
      )}

      <input ref={fileInputRef} type="file" accept="image/*" multiple onChange={handleFileUpload} className="hidden" />
      <input ref={cameraInputRef} type="file" accept="image/*" capture="environment" onChange={handleFileUpload} className="hidden" />
    </div>
  );

  /* ── Step 2: Identify ── */
  const renderIdentifyStep = () => {
    if (analyzing) return renderAnalyzingState('Identifying your item...', 'Scanning for brand, model, UPC, condition...');
    if (!identification) return renderAnalyzingState('Ready to identify', 'Click "Analyze" to identify this item');

    const id = identification;
    return (
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-bold">AI Identification</h3>
            <p className="text-xs" style={{ color: 'var(--muted)' }}>Review and edit detected information</p>
          </div>
          <button className="btn-secondary text-xs" onClick={runIdentification}>
            <RotateCw size={13} /> Re-Analyze
          </button>
        </div>

        {/* Product card */}
        <div className="empire-card mb-4">
          <div className="flex gap-4">
            {photos[0] && (
              <div className="shrink-0 w-24 h-24 rounded-lg overflow-hidden" style={{ border: '1px solid var(--border)' }}>
                <img src={photos[0].dataUrl} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              </div>
            )}
            <div className="flex-1">
              <div className="text-xs font-bold uppercase mb-1" style={{ color: 'var(--muted)' }}>Identified Product</div>
              <h4 className="font-bold text-base mb-1">{id.productName}</h4>
              <div className="flex gap-2 flex-wrap">
                <span className="status-pill active">{id.brand}</span>
                <span className="status-pill draft">{id.category}</span>
                {id.upc && (
                  <span className="status-pill pending" style={{ fontFamily: 'monospace' }}>
                    <ScanBarcode size={11} /> UPC: {id.upc}
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Details grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
          {[
            { label: 'Brand', value: id.brand },
            { label: 'Model', value: id.model },
            { label: 'Category', value: `${id.category} › ${id.subcategory}` },
            { label: 'Color', value: id.color },
            { label: 'Material', value: id.material },
            { label: 'Size', value: id.size },
          ].map(item => (
            <div key={item.label} className="empire-card" style={{ padding: 12 }}>
              <div className="text-[10px] font-bold uppercase mb-0.5" style={{ color: 'var(--muted)' }}>{item.label}</div>
              <div className="text-sm font-semibold">{item.value}</div>
            </div>
          ))}
        </div>

        {/* Condition assessment */}
        <div className="empire-card mb-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs font-bold uppercase" style={{ color: 'var(--muted)' }}>Condition Assessment</div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold" style={{ color: CONDITION_COLORS[id.condition] }}>
                {id.conditionScore}/10
              </span>
              <span className="status-pill" style={{
                background: CONDITION_COLORS[id.condition] + '18',
                color: CONDITION_COLORS[id.condition],
              }}>
                {CONDITION_LABELS[id.condition]}
              </span>
            </div>
          </div>
          {/* Score bar */}
          <div className="w-full h-2 rounded-full mb-3" style={{ background: '#f3f4f6' }}>
            <div className="h-full rounded-full transition-all" style={{
              width: `${id.conditionScore * 10}%`,
              background: CONDITION_COLORS[id.condition],
            }} />
          </div>
          <p className="text-sm mb-2">{id.conditionNotes}</p>
          {id.defects.length > 0 && (
            <div>
              <div className="text-xs font-bold mb-1" style={{ color: '#d97706' }}>Noted Defects:</div>
              {id.defects.map((d, i) => (
                <div key={i} className="flex items-start gap-1.5 text-xs" style={{ color: '#d97706' }}>
                  <AlertCircle size={12} className="shrink-0 mt-0.5" /> {d}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Keywords */}
        <div className="empire-card">
          <div className="text-xs font-bold uppercase mb-2" style={{ color: 'var(--muted)' }}>Detected Keywords</div>
          <div className="flex flex-wrap gap-1.5">
            {id.keywords.map(kw => (
              <span key={kw} className="px-2 py-0.5 rounded-full text-xs font-medium"
                style={{ background: '#ecfeff', color: '#06b6d4' }}>
                {kw}
              </span>
            ))}
          </div>
        </div>
      </div>
    );
  };

  /* ── Step 3: Price ── */
  const renderPriceStep = () => {
    if (analyzing) return renderAnalyzingState('Checking market prices...', 'Searching eBay sold, Mercari, and more...');
    if (!pricing) return renderAnalyzingState('Ready to price', 'Click Next to run pricing analysis');

    const p = pricing;
    return (
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-bold">AI Pricing Intelligence</h3>
            <p className="text-xs" style={{ color: 'var(--muted)' }}>Market data from recent sales across platforms</p>
          </div>
          <button className="btn-secondary text-xs" onClick={runPricing}>
            <RotateCw size={13} /> Refresh
          </button>
        </div>

        {/* Price summary */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          <div className="empire-card text-center" style={{ padding: 16 }}>
            <div className="text-[10px] font-bold uppercase mb-1" style={{ color: 'var(--muted)' }}>Suggested Price</div>
            <div className="text-2xl font-bold" style={{ color: '#06b6d4' }}>${p.suggestedPrice}</div>
          </div>
          <div className="empire-card text-center" style={{ padding: 16 }}>
            <div className="text-[10px] font-bold uppercase mb-1" style={{ color: 'var(--muted)' }}>Market Range</div>
            <div className="text-lg font-bold">${p.priceRange.low} – ${p.priceRange.high}</div>
          </div>
          <div className="empire-card text-center" style={{ padding: 16 }}>
            <div className="text-[10px] font-bold uppercase mb-1" style={{ color: 'var(--muted)' }}>Avg Days to Sell</div>
            <div className="text-lg font-bold">{p.avgDaysToSell} days</div>
            <span className="status-pill text-[10px]" style={{
              background: p.demandLevel === 'high' ? '#dcfce7' : p.demandLevel === 'medium' ? '#fff7ed' : '#fef2f2',
              color: p.demandLevel === 'high' ? '#16a34a' : p.demandLevel === 'medium' ? '#d97706' : '#dc2626',
            }}>
              <TrendingUp size={10} /> {p.demandLevel} demand
            </span>
          </div>
        </div>

        {/* Per-platform pricing */}
        <div className="empire-card mb-4">
          <div className="text-xs font-bold uppercase mb-3" style={{ color: 'var(--muted)' }}>Per-Platform Breakdown</div>
          <div className="space-y-2">
            {p.platformPrices.map(pp => {
              const color = PLATFORM_COLORS[pp.platform] || '#777';
              return (
                <div key={pp.platform} className="flex items-center gap-3 py-2 px-3 rounded-lg"
                  style={{ background: '#f9fafb' }}>
                  <div className="platform-dot" style={{ background: color }} />
                  <div className="text-sm font-semibold capitalize flex-1" style={{ minWidth: 70 }}>{pp.platform}</div>
                  <div className="text-center" style={{ minWidth: 80 }}>
                    <div className="text-xs" style={{ color: 'var(--muted)' }}>Suggest</div>
                    <div className="text-sm font-bold">${pp.suggested}</div>
                  </div>
                  <div className="text-center" style={{ minWidth: 70 }}>
                    <div className="text-xs" style={{ color: 'var(--muted)' }}>Avg Sold</div>
                    <div className="text-sm font-medium">${pp.avgSold}</div>
                  </div>
                  <div className="text-center" style={{ minWidth: 60 }}>
                    <div className="text-xs" style={{ color: 'var(--muted)' }}>Fees</div>
                    <div className="text-sm font-medium" style={{ color: '#dc2626' }}>-${pp.fees}</div>
                  </div>
                  <div className="text-center" style={{ minWidth: 60 }}>
                    <div className="text-xs" style={{ color: 'var(--muted)' }}>Profit</div>
                    <div className="text-sm font-bold" style={{ color: '#16a34a' }}>${pp.profit}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Comparable sales */}
        <div className="empire-card">
          <div className="text-xs font-bold uppercase mb-3" style={{ color: 'var(--muted)' }}>Recent Comparable Sales</div>
          <table className="empire-table">
            <thead>
              <tr>
                <th>Item</th>
                <th>Platform</th>
                <th>Condition</th>
                <th>Sold Price</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {p.comps.map((c, i) => (
                <tr key={i}>
                  <td className="text-sm">{c.title}</td>
                  <td className="text-sm font-medium">{c.platform}</td>
                  <td className="text-xs"><span className="status-pill active">{c.condition}</span></td>
                  <td className="text-sm font-bold">${c.price}</td>
                  <td className="text-xs" style={{ color: 'var(--muted)' }}>{c.soldDate}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  /* ── Step 4: Describe ── */
  const renderDescribeStep = () => {
    if (analyzing) return renderAnalyzingState('Generating descriptions...', 'Writing platform-optimized titles and descriptions...');
    if (!description) return renderAnalyzingState('Ready to describe', 'Click Next to auto-generate listing content');

    const d = description;
    return (
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-bold">AI-Generated Listing Content</h3>
            <p className="text-xs" style={{ color: 'var(--muted)' }}>SEO-optimized, platform-tailored descriptions</p>
          </div>
          <button className="btn-secondary text-xs" onClick={runDescription}>
            <RotateCw size={13} /> Regenerate
          </button>
        </div>

        {/* Master title + description */}
        <div className="empire-card mb-4">
          <div className="text-xs font-bold uppercase mb-2" style={{ color: 'var(--muted)' }}>Master Listing</div>
          <div className="mb-3">
            <label className="field-label">Title</label>
            <input className="form-input font-semibold" defaultValue={d.title} />
          </div>
          <div className="mb-3">
            <label className="field-label">Description</label>
            <textarea className="form-input" rows={8} defaultValue={d.description}
              style={{ fontFamily: 'inherit', lineHeight: 1.6 }} />
          </div>
          <div>
            <label className="field-label">Tags</label>
            <div className="flex flex-wrap gap-1.5">
              {d.tags.map(tag => (
                <span key={tag} className="px-2 py-0.5 rounded-full text-xs font-medium flex items-center gap-1"
                  style={{ background: '#ecfeff', color: '#06b6d4' }}>
                  {tag} <X size={10} className="cursor-pointer" />
                </span>
              ))}
              <button className="px-2 py-0.5 rounded-full text-xs"
                style={{ border: '1px dashed var(--border)', color: 'var(--muted)' }}>
                + Add
              </button>
            </div>
          </div>
        </div>

        {/* Item specifics */}
        <div className="empire-card mb-4">
          <div className="text-xs font-bold uppercase mb-2" style={{ color: 'var(--muted)' }}>Item Specifics</div>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(d.itemSpecifics).map(([k, v]) => (
              <div key={k} className="flex items-center gap-2 py-1.5 px-2 rounded-md" style={{ background: '#f9fafb' }}>
                <span className="text-xs font-semibold shrink-0" style={{ color: 'var(--muted)', minWidth: 90 }}>{k}</span>
                <span className="text-sm font-medium">{v}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Platform-specific descriptions */}
        <div className="empire-card">
          <div className="text-xs font-bold uppercase mb-3" style={{ color: 'var(--muted)' }}>Platform-Optimized Versions</div>
          <div className="space-y-3">
            {d.platformDescriptions.map(pd => {
              const color = PLATFORM_COLORS[pd.platform] || '#777';
              return (
                <div key={pd.platform} className="rounded-lg p-3" style={{ border: '1px solid var(--border)' }}>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="platform-dot" style={{ background: color }} />
                    <span className="text-xs font-bold uppercase" style={{ color }}>{pd.platform}</span>
                    <button className="ml-auto text-xs flex items-center gap-1" style={{ color: 'var(--muted)' }}>
                      <Copy size={11} /> Copy
                    </button>
                  </div>
                  <input className="form-input text-sm font-semibold mb-1.5" defaultValue={pd.title}
                    style={{ fontSize: 13, padding: '6px 10px' }} />
                  <textarea className="form-input text-sm" rows={3} defaultValue={pd.description}
                    style={{ fontSize: 12, padding: '6px 10px', lineHeight: 1.5 }} />
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  /* ── Step 5: Review & List ── */
  const renderReviewStep = () => {
    if (!identification || !pricing || !description) {
      return (
        <div className="empire-card text-center py-12">
          <AlertCircle size={32} style={{ color: '#d97706', margin: '0 auto 12px' }} />
          <p className="font-semibold mb-1">Analysis Incomplete</p>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>Complete all steps before creating a listing.</p>
        </div>
      );
    }

    return (
      <div>
        <h3 className="text-lg font-bold mb-1">Review & Publish</h3>
        <p className="text-sm mb-4" style={{ color: 'var(--muted)' }}>
          Final review before listing on selected platforms
        </p>

        {listingCreated && (
          <div className="rounded-xl p-4 mb-4 flex items-center gap-3"
            style={{ background: '#dcfce7', border: '1px solid #86efac' }}>
            <Check size={20} style={{ color: '#16a34a' }} />
            <div>
              <div className="text-sm font-bold" style={{ color: '#16a34a' }}>Listing Created!</div>
              <div className="text-xs" style={{ color: '#15803d' }}>
                Published to {selectedPlatforms.size} platform{selectedPlatforms.size !== 1 ? 's' : ''}. View in Listings tab.
              </div>
            </div>
          </div>
        )}

        {/* Summary card */}
        <div className="empire-card mb-4">
          <div className="flex gap-4">
            {photos[0] && (
              <div className="shrink-0 w-28 h-28 rounded-lg overflow-hidden" style={{ border: '1px solid var(--border)' }}>
                <img src={photos[0].dataUrl} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              </div>
            )}
            <div className="flex-1">
              <h4 className="font-bold mb-1">{description.title}</h4>
              <div className="flex gap-2 flex-wrap mb-2">
                <span className="status-pill active">{identification.brand}</span>
                <span className="status-pill" style={{
                  background: CONDITION_COLORS[identification.condition] + '18',
                  color: CONDITION_COLORS[identification.condition],
                }}>{CONDITION_LABELS[identification.condition]}</span>
                {identification.upc && (
                  <span className="status-pill pending" style={{ fontFamily: 'monospace', fontSize: 10 }}>
                    UPC: {identification.upc}
                  </span>
                )}
              </div>
              <div className="flex gap-4 text-sm">
                <div>
                  <span style={{ color: 'var(--muted)' }}>Price: </span>
                  <span className="font-bold" style={{ color: '#06b6d4' }}>${pricing.suggestedPrice}</span>
                </div>
                <div>
                  <span style={{ color: 'var(--muted)' }}>Photos: </span>
                  <span className="font-semibold">{photos.length}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Platform selection */}
        <div className="empire-card mb-4">
          <div className="text-xs font-bold uppercase mb-3" style={{ color: 'var(--muted)' }}>Publish To</div>
          <div className="grid grid-cols-3 gap-2">
            {(['ebay', 'etsy', 'shopify', 'facebook', 'mercari', 'amazon'] as Platform[]).map(p => {
              const active = selectedPlatforms.has(p);
              const color = PLATFORM_COLORS[p] || '#777';
              const pp = pricing.platformPrices.find(x => x.platform === p);
              return (
                <button key={p} onClick={() => togglePlatform(p)}
                  className="rounded-lg p-3 text-left transition-all"
                  style={{
                    border: active ? `2px solid ${color}` : '2px solid var(--border)',
                    background: active ? color + '08' : 'white',
                  }}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold capitalize" style={{ color: active ? color : '#777' }}>{p}</span>
                    {active && <Check size={14} style={{ color }} />}
                  </div>
                  {pp && (
                    <div className="text-xs" style={{ color: 'var(--muted)' }}>
                      ${pp.suggested} → <span style={{ color: '#16a34a' }}>${pp.profit} profit</span>
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Projected earnings */}
        <div className="empire-card mb-4">
          <div className="text-xs font-bold uppercase mb-2" style={{ color: 'var(--muted)' }}>Projected Earnings</div>
          <div className="grid grid-cols-3 gap-3">
            <div className="text-center">
              <div className="text-xs" style={{ color: 'var(--muted)' }}>Best Platform</div>
              <div className="text-sm font-bold capitalize" style={{ color: '#16a34a' }}>
                {pricing.platformPrices
                  .filter(pp => selectedPlatforms.has(pp.platform))
                  .sort((a, b) => b.profit - a.profit)[0]?.platform || '—'}
              </div>
            </div>
            <div className="text-center">
              <div className="text-xs" style={{ color: 'var(--muted)' }}>Max Profit</div>
              <div className="text-lg font-bold" style={{ color: '#16a34a' }}>
                ${Math.max(...pricing.platformPrices.filter(pp => selectedPlatforms.has(pp.platform)).map(pp => pp.profit), 0)}
              </div>
            </div>
            <div className="text-center">
              <div className="text-xs" style={{ color: 'var(--muted)' }}>Est. Sell Time</div>
              <div className="text-sm font-bold">{pricing.avgDaysToSell} days</div>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button className="btn-primary flex-1 justify-center py-3 text-sm" onClick={createListing}>
            <ShoppingCart size={16} />
            Publish to {selectedPlatforms.size} Platform{selectedPlatforms.size !== 1 ? 's' : ''}
          </button>
          <button className="btn-secondary" onClick={() => {
            // Save as draft
            createListing();
          }}>
            Save Draft
          </button>
        </div>
      </div>
    );
  };

  /* ── Loading state ── */
  const renderAnalyzingState = (title: string, subtitle: string) => (
    <div className="empire-card flex flex-col items-center justify-center py-16">
      {analyzing ? (
        <div className="w-12 h-12 rounded-full border-3 border-t-[#06b6d4] animate-spin mb-4"
          style={{ borderWidth: 3, borderColor: '#e5e7eb', borderTopColor: '#06b6d4' }} />
      ) : (
        <Sparkles size={32} style={{ color: '#06b6d4', marginBottom: 16 }} />
      )}
      <p className="font-semibold text-sm mb-1">{title}</p>
      <p className="text-xs" style={{ color: 'var(--muted)' }}>{subtitle}</p>
    </div>
  );

  /* ─── Main render ─── */
  return (
    <div style={{ maxWidth: 900 }}>
      <div className="flex items-center justify-between mb-2">
        <div>
          <h2 className="text-xl font-bold">Smart Lister</h2>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>
            Snap → Identify → Price → Describe → List. AI does the work.
          </p>
        </div>
        {(photos.length > 0 || identification) && (
          <button className="btn-secondary text-xs" onClick={resetAll}>
            <RotateCw size={13} /> Start Over
          </button>
        )}
      </div>

      {renderProgressBar()}

      <div className="mb-6">
        {step === 'photos' && renderPhotosStep()}
        {step === 'identify' && renderIdentifyStep()}
        {step === 'price' && renderPriceStep()}
        {step === 'describe' && renderDescribeStep()}
        {step === 'review' && renderReviewStep()}
      </div>

      {/* Navigation buttons */}
      <div className="flex items-center justify-between">
        <button className="btn-secondary" onClick={prevStep} disabled={stepIndex === 0}
          style={{ opacity: stepIndex === 0 ? 0.4 : 1 }}>
          <ArrowLeft size={15} /> Back
        </button>
        <div className="text-xs font-medium" style={{ color: 'var(--muted)' }}>
          Step {stepIndex + 1} of {STEPS.length}
        </div>
        {stepIndex < STEPS.length - 1 ? (
          <button className="btn-primary" onClick={nextStep} disabled={!canProceed() || analyzing}
            style={{ opacity: !canProceed() || analyzing ? 0.5 : 1 }}>
            {analyzing ? <Loader2 size={15} className="animate-spin" /> : null}
            Next <ArrowRight size={15} />
          </button>
        ) : (
          <div />
        )}
      </div>
    </div>
  );
}
