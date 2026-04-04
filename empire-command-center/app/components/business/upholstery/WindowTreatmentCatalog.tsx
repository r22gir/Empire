'use client';

import React, { useState, useCallback, useMemo } from 'react';
import {
  ChevronLeft, CheckCircle2, Sparkles, Ruler, Search,
} from 'lucide-react';

import {
  WINDOW_TREATMENT_TYPES,
  WT_CATEGORY_LABELS,
  type WindowTreatmentType,
} from './window-treatment-data';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface WindowTreatmentMeasurements {
  treatmentType: string;
  measurements: Record<string, number>;
  notes: string;
}

export interface WindowTreatmentCatalogProps {
  onSelect?: (type: WindowTreatmentType) => void;
  onMeasurementsComplete?: (data: WindowTreatmentMeasurements) => void;
  suggestedType?: string;
  compact?: boolean;
}

// ---------------------------------------------------------------------------
// SVG renderers — generic shapes by category
// ---------------------------------------------------------------------------

const TINTS = [
  'rgba(184,150,12,0.10)', 'rgba(184,150,12,0.18)',
  'rgba(120,100,40,0.10)', 'rgba(200,180,100,0.12)',
];

function SvgDrapery({ full = false }: { full?: boolean }) {
  return (
    <svg viewBox="0 0 200 150" className="w-full h-full">
      {/* Rod */}
      <rect x="10" y="10" width="180" height="6" rx="3" fill="#999" />
      <circle cx="10" cy="13" r="5" fill="#999" />
      <circle cx="190" cy="13" r="5" fill="#999" />
      {/* Left panel with folds */}
      <path d="M15,16 Q20,16 25,16 L25,140 L15,140 Z" fill={full ? TINTS[0] : 'none'} stroke="#999" strokeWidth="1" />
      <path d="M25,16 Q35,16 40,16 L35,140 L25,140 Z" fill={full ? TINTS[1] : 'none'} stroke="#999" strokeWidth="1" />
      <path d="M40,16 Q50,16 55,16 L50,140 L35,140 Z" fill={full ? TINTS[0] : 'none'} stroke="#999" strokeWidth="1" />
      <path d="M55,16 Q65,16 70,16 L65,140 L50,140 Z" fill={full ? TINTS[1] : 'none'} stroke="#999" strokeWidth="1" />
      {/* Right panel with folds */}
      <path d="M130,16 Q140,16 145,16 L140,140 L135,140 Z" fill={full ? TINTS[0] : 'none'} stroke="#999" strokeWidth="1" />
      <path d="M145,16 Q155,16 160,16 L155,140 L140,140 Z" fill={full ? TINTS[1] : 'none'} stroke="#999" strokeWidth="1" />
      <path d="M160,16 Q170,16 175,16 L170,140 L155,140 Z" fill={full ? TINTS[0] : 'none'} stroke="#999" strokeWidth="1" />
      <path d="M175,16 Q180,16 185,16 L185,140 L170,140 Z" fill={full ? TINTS[1] : 'none'} stroke="#999" strokeWidth="1" />
      {/* Window opening */}
      <rect x="70" y="20" width="60" height="100" rx="1" fill="none" stroke="#ccc" strokeWidth="1" strokeDasharray="4,3" />
    </svg>
  );
}

function SvgShade({ full = false }: { full?: boolean }) {
  return (
    <svg viewBox="0 0 200 150" className="w-full h-full">
      {/* Frame */}
      <rect x="30" y="10" width="140" height="130" rx="2" fill="none" stroke="#ccc" strokeWidth="1" />
      {/* Headrail */}
      <rect x="30" y="10" width="140" height="8" rx="2" fill="#999" />
      {/* Shade body */}
      <rect x="32" y="18" width="136" height="80" rx="1" fill={full ? TINTS[0] : 'none'} stroke="#999" strokeWidth="1.5" />
      {/* Fold lines */}
      <line x1="32" y1="38" x2="168" y2="38" stroke="#999" strokeWidth="0.5" />
      <line x1="32" y1="58" x2="168" y2="58" stroke="#999" strokeWidth="0.5" />
      <line x1="32" y1="78" x2="168" y2="78" stroke="#999" strokeWidth="0.5" />
      {/* Bottom bar */}
      <rect x="32" y="94" width="136" height="4" rx="1" fill="#999" />
      {/* Cord */}
      <line x1="160" y1="18" x2="160" y2="130" stroke="#999" strokeWidth="0.5" />
      <circle cx="160" cy="130" r="3" fill="#999" />
    </svg>
  );
}

function SvgValance({ full = false }: { full?: boolean }) {
  return (
    <svg viewBox="0 0 200 150" className="w-full h-full">
      {/* Board */}
      <rect x="20" y="20" width="160" height="8" rx="2" fill="#999" />
      {/* Valance body */}
      <path d="M20,28 L20,80 Q60,100 100,80 Q140,60 180,80 L180,28 Z"
        fill={full ? TINTS[0] : 'none'} stroke="#999" strokeWidth="1.5" />
      {/* Window below */}
      <rect x="40" y="85" width="120" height="55" rx="1" fill="none" stroke="#ccc" strokeWidth="1" strokeDasharray="4,3" />
    </svg>
  );
}

function SvgBlind({ full = false }: { full?: boolean }) {
  return (
    <svg viewBox="0 0 200 150" className="w-full h-full">
      {/* Frame */}
      <rect x="30" y="10" width="140" height="130" rx="2" fill="none" stroke="#ccc" strokeWidth="1" />
      {/* Headrail */}
      <rect x="30" y="10" width="140" height="8" rx="2" fill="#999" />
      {/* Slats */}
      {[28, 42, 56, 70, 84, 98, 112, 126].map((y) => (
        <rect key={y} x="32" y={y} width="136" height="8" rx="1" fill={full ? TINTS[0] : 'none'} stroke="#999" strokeWidth="0.5" />
      ))}
    </svg>
  );
}

function SvgShutter({ full = false }: { full?: boolean }) {
  return (
    <svg viewBox="0 0 200 150" className="w-full h-full">
      {/* Frame */}
      <rect x="20" y="10" width="160" height="130" rx="3" fill="none" stroke="#999" strokeWidth="2" />
      {/* Left panel */}
      <rect x="22" y="12" width="78" height="126" rx="1" fill="none" stroke="#999" strokeWidth="1" />
      {/* Right panel */}
      <rect x="100" y="12" width="78" height="126" rx="1" fill="none" stroke="#999" strokeWidth="1" />
      {/* Louvers left */}
      {[25, 40, 55, 70, 85, 100, 115].map((y) => (
        <line key={`l${y}`} x1="28" y1={y} x2="94" y2={y} stroke="#999" strokeWidth="0.7" />
      ))}
      {/* Louvers right */}
      {[25, 40, 55, 70, 85, 100, 115].map((y) => (
        <line key={`r${y}`} x1="106" y1={y} x2="172" y2={y} stroke="#999" strokeWidth="0.7" />
      ))}
      {/* Tilt bars */}
      <line x1="61" y1="15" x2="61" y2="135" stroke="#999" strokeWidth="1" />
      <line x1="139" y1="15" x2="139" y2="135" stroke="#999" strokeWidth="1" />
    </svg>
  );
}

function SvgGenericWT({ full = false }: { full?: boolean }) {
  return (
    <svg viewBox="0 0 200 150" className="w-full h-full">
      <rect x="40" y="20" width="120" height="110" rx="6" fill={full ? TINTS[0] : 'none'} stroke="#999" strokeWidth="1.5" strokeDasharray="4,4" />
      <text x="100" y="80" textAnchor="middle" fontSize="11" fill="#999">Custom</text>
    </svg>
  );
}

const WT_SVG_MAP: Record<string, React.FC<{ full?: boolean }>> = {
  drapery: SvgDrapery,
  shade: SvgShade,
  valance: SvgValance,
  blind: SvgBlind,
  shutter: SvgShutter,
  specialty: SvgDrapery,
  hardware: SvgGenericWT,
  accessory: SvgGenericWT,
  generic: SvgGenericWT,
};

function getWTSvg(wt: WindowTreatmentType): React.FC<{ full?: boolean }> {
  return WT_SVG_MAP[wt.svgHint || ''] || WT_SVG_MAP[wt.category] || WT_SVG_MAP.generic;
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function WindowTreatmentCatalog({
  onSelect,
  onMeasurementsComplete,
  suggestedType,
  compact = false,
}: WindowTreatmentCatalogProps) {
  const [selected, setSelected] = useState<WindowTreatmentType | null>(null);
  const [measurements, setMeasurements] = useState<Record<string, string>>({});
  const [notes, setNotes] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState<string>('all');

  const filteredTypes = useMemo(() => {
    let items = WINDOW_TREATMENT_TYPES;
    if (activeCategory !== 'all') {
      items = items.filter((wt) => wt.category === activeCategory);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      items = items.filter(
        (wt) =>
          wt.name.toLowerCase().includes(q) ||
          wt.category.toLowerCase().includes(q) ||
          (wt.subcategory || '').toLowerCase().includes(q) ||
          (wt.description || '').toLowerCase().includes(q),
      );
    }
    return items;
  }, [activeCategory, searchQuery]);

  const categories = useMemo(() => {
    const cats = new Set(WINDOW_TREATMENT_TYPES.map((wt) => wt.category));
    return ['all', ...Array.from(cats)];
  }, []);

  const allFilled = useMemo(() => {
    if (!selected) return false;
    return selected.measurementPoints.every((mp) => {
      // Text fields are optional
      if (['Mount Type', 'Style', 'Shape', 'Pattern', 'Finish', 'Color', 'Hinge Side', 'Stack Side',
           'Motor Side', 'Power Source', 'Smart Hub', 'Smart Hub Compatible', 'Template/Pattern',
           'Weave Style', 'Louver Size', 'Panel Style', 'Mount Type (inside/outside)',
           'Roll Direction (standard/reverse)'].some(t => mp.includes(t))) return true;
      const v = measurements[mp];
      return v !== undefined && v !== '';
    });
  }, [selected, measurements]);

  const handleSelect = useCallback((wt: WindowTreatmentType) => {
    setSelected(wt);
    setMeasurements({});
    setNotes('');
    onSelect?.(wt);
  }, [onSelect]);

  const handleBack = useCallback(() => {
    setSelected(null);
    setMeasurements({});
    setNotes('');
  }, []);

  const handleComplete = useCallback(() => {
    if (!selected) return;
    const parsed: Record<string, number> = {};
    for (const [k, v] of Object.entries(measurements)) {
      const n = Number(v);
      if (!isNaN(n)) parsed[k] = n;
    }
    onMeasurementsComplete?.({ treatmentType: selected.key, measurements: parsed, notes });
  }, [selected, measurements, notes, onMeasurementsComplete]);

  // ── Detail view ──
  if (selected) {
    const SvgComponent = getWTSvg(selected);
    return (
      <div style={{ background: '#f5f3ef', borderRadius: 12, border: '1px solid #ece8e0', padding: compact ? 16 : 24, fontFamily: 'inherit' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
          <button onClick={handleBack} style={{ display: 'flex', alignItems: 'center', gap: 4, background: 'none', border: 'none', cursor: 'pointer', color: '#b8960c', fontWeight: 600, fontSize: 14, padding: 0, minHeight: 44 }}>
            <ChevronLeft size={18} /> Back
          </button>
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: '#333' }}>{selected.name}</h2>
          <span style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', background: '#b8960c', color: '#fff', padding: '2px 8px', borderRadius: 4 }}>
            {WT_CATEGORY_LABELS[selected.category]}
          </span>
        </div>

        {selected.description && (
          <p style={{ fontSize: 13, color: '#666', margin: '0 0 16px', lineHeight: 1.4 }}>{selected.description}</p>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: compact ? '1fr' : '1fr 1fr', gap: 24 }}>
          {/* Diagram */}
          <div style={{ background: '#fff', borderRadius: 10, border: '1px solid #ece8e0', padding: 16, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div style={{ width: '100%', maxWidth: 340 }}><SvgComponent full /></div>
            <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {selected.fabricSections.map((section) => (
                <span key={section} style={{ fontSize: 10, background: 'rgba(184,150,12,0.12)', border: '1px solid #ece8e0', borderRadius: 4, padding: '2px 6px', color: '#666' }}>
                  {section}
                </span>
              ))}
            </div>
          </div>

          {/* Measurements */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              <Ruler size={16} color="#b8960c" />
              <span style={{ fontWeight: 600, fontSize: 14, color: '#333' }}>Measurements</span>
            </div>
            {selected.measurementPoints.map((mp) => {
              const isText = ['Mount Type', 'Style', 'Shape', 'Pattern', 'Finish', 'Color'].some(t => mp.includes(t));
              return (
                <div key={mp} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <label style={{ flex: 1, fontSize: 13, color: '#555', minWidth: 120 }}>{mp}</label>
                  <input
                    type={isText ? 'text' : 'number'}
                    placeholder={isText ? 'enter...' : '"'}
                    value={measurements[mp] ?? ''}
                    onChange={(e) => setMeasurements((prev) => ({ ...prev, [mp]: e.target.value }))}
                    style={{ width: 100, minHeight: 44, borderRadius: 6, border: '1px solid #ece8e0', padding: '0 10px', fontSize: 14, textAlign: isText ? 'left' : 'center', outline: 'none' }}
                  />
                </div>
              );
            })}
            <div style={{ marginTop: 4 }}>
              <label style={{ fontSize: 13, color: '#555' }}>Notes</label>
              <textarea rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Lining type, trim details, motorization..."
                style={{ width: '100%', marginTop: 4, borderRadius: 6, border: '1px solid #ece8e0', padding: 10, fontSize: 13, resize: 'vertical', outline: 'none', fontFamily: 'inherit' }} />
            </div>
            <button onClick={handleComplete} disabled={!allFilled}
              style={{ marginTop: 8, minHeight: 48, borderRadius: 8, border: 'none', background: allFilled ? '#b8960c' : '#ddd', color: allFilled ? '#fff' : '#999', fontWeight: 700, fontSize: 15, cursor: allFilled ? 'pointer' : 'not-allowed', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, transition: 'background 0.2s' }}>
              <CheckCircle2 size={18} /> Complete Measurements
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Grid view ──
  return (
    <div style={{ background: '#f5f3ef', borderRadius: 12, border: '1px solid #ece8e0', padding: compact ? 16 : 24, fontFamily: 'inherit' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#b8960c" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="3" y1="15" x2="21" y2="15" /></svg>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#333' }}>Window Treatment Catalog</h2>
        <span style={{ fontSize: 12, color: '#999', marginLeft: 'auto' }}>
          {filteredTypes.length} of {WINDOW_TREATMENT_TYPES.length} items
        </span>
      </div>

      <div style={{ position: 'relative', marginBottom: 12 }}>
        <Search size={16} style={{ position: 'absolute', left: 12, top: 14, color: '#999' }} />
        <input type="text" placeholder="Search window treatments..." value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{ width: '100%', minHeight: 44, borderRadius: 8, border: '1px solid #ece8e0', padding: '0 12px 0 36px', fontSize: 14, outline: 'none', fontFamily: 'inherit', background: '#fff' }} />
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 14 }}>
        {categories.map((cat) => (
          <button key={cat} onClick={() => setActiveCategory(cat)}
            style={{ padding: '4px 12px', borderRadius: 16, border: activeCategory === cat ? '1px solid #b8960c' : '1px solid #ece8e0', background: activeCategory === cat ? '#b8960c' : '#fff', color: activeCategory === cat ? '#fff' : '#666', fontSize: 12, fontWeight: 600, cursor: 'pointer', textTransform: 'capitalize', transition: 'all 0.15s' }}>
            {cat === 'all' ? `All (${WINDOW_TREATMENT_TYPES.length})` : `${WT_CATEGORY_LABELS[cat] || cat}`}
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: compact ? 'repeat(auto-fill, minmax(140px, 1fr))' : 'repeat(auto-fill, minmax(180px, 1fr))', gap: compact ? 10 : 14, maxHeight: 600, overflowY: 'auto' }}>
        {filteredTypes.map((wt) => {
          const isSuggested = suggestedType === wt.key;
          const SvgComponent = getWTSvg(wt);
          return (
            <button key={wt.key} onClick={() => handleSelect(wt)}
              style={{ position: 'relative', background: '#fff', borderRadius: 10, border: isSuggested ? '2px solid #b8960c' : '1px solid #ece8e0', padding: compact ? 10 : 14, cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, minHeight: compact ? 120 : 160, transition: 'box-shadow 0.15s, border-color 0.15s', boxShadow: isSuggested ? '0 0 0 3px rgba(184,150,12,0.18)' : '0 1px 3px rgba(0,0,0,0.04)' }}
              onMouseEnter={(e) => { (e.currentTarget).style.borderColor = '#b8960c'; (e.currentTarget).style.boxShadow = '0 2px 8px rgba(184,150,12,0.15)'; }}
              onMouseLeave={(e) => { (e.currentTarget).style.borderColor = isSuggested ? '#b8960c' : '#ece8e0'; (e.currentTarget).style.boxShadow = isSuggested ? '0 0 0 3px rgba(184,150,12,0.18)' : '0 1px 3px rgba(0,0,0,0.04)'; }}>
              {isSuggested && (
                <span style={{ position: 'absolute', top: 6, right: 6, fontSize: 9, fontWeight: 700, textTransform: 'uppercase', background: '#b8960c', color: '#fff', padding: '2px 6px', borderRadius: 4, display: 'flex', alignItems: 'center', gap: 3 }}>
                  <Sparkles size={10} /> AI Suggested
                </span>
              )}
              <div style={{ width: compact ? 100 : 130, height: compact ? 75 : 95, flexShrink: 0 }}>
                <SvgComponent />
              </div>
              <span style={{ fontSize: compact ? 12 : 13, fontWeight: 600, color: '#333', textAlign: 'center', lineHeight: 1.2 }}>{wt.name}</span>
              <span style={{ fontSize: 10, fontWeight: 600, textTransform: 'uppercase', color: '#b8960c', background: 'rgba(184,150,12,0.08)', padding: '2px 8px', borderRadius: 4 }}>
                {WT_CATEGORY_LABELS[wt.category]}
              </span>
              {wt.subcategory && (
                <span style={{ fontSize: 9, color: '#999' }}>{wt.subcategory}</span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
