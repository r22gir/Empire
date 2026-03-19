'use client';

import React, { useState, useEffect } from 'react';
import {
  CheckCircle, ChevronDown, ChevronRight, Edit3, Plus, Trash2,
  RefreshCw, ArrowLeft, Loader2, Check, X
} from 'lucide-react';
import MeasurementDiagram from '../quotes/MeasurementDiagram';

/* ═══════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════ */

interface DetectedItem {
  id: string;
  type: string;
  description: string;
  checked: boolean;
  width_inches: number;
  height_inches: number;
  depth_inches: number;
  confidence: number;
}

interface MeasuredItem extends DetectedItem {
  sill_depth: number;
  mount_type: string;
  treatment: string;
  lining: string;
  notes: string;
}

interface YardageItem extends MeasuredItem {
  fullness: number;      // 2.0, 2.5, 3.0
  pattern_repeat: number; // inches
  hem_allowance: number;  // inches
  fabric_width: number;   // inches (typically 54)
  cut_length: number;     // calculated
  total_yards: number;    // calculated
}

interface LineItem {
  id: string;
  description: string;
  category: 'fabric' | 'labor' | 'hardware' | 'installation' | 'custom';
  quantity: number;
  unit: string;
  rate: number;
  amount: number;
}

type Phase = 1 | 2 | 3 | 4;

interface AnalysisApprovalFlowProps {
  result: any;                    // Raw AI analysis result
  imageData?: string;
  onRedetect?: () => void;
  onFinalize?: (data: { items: MeasuredItem[]; lineItems: LineItem[]; total: number }) => void;
  onAddToQuote?: (data: any) => void;
}

/* ═══════════════════════════════════════════════════════════
   Item types
   ═══════════════════════════════════════════════════════════ */

const ITEM_TYPES = [
  'window', 'drapery', 'roman_shade', 'valance', 'cornice',
  'sofa', 'chair', 'ottoman', 'cushion', 'pillow',
  'headboard', 'bench', 'other',
];

/* ═══════════════════════════════════════════════════════════
   Component
   ═══════════════════════════════════════════════════════════ */

export default function AnalysisApprovalFlow({ result, imageData, onRedetect, onFinalize, onAddToQuote }: AnalysisApprovalFlowProps) {
  const [phase, setPhase] = useState<Phase>(1);
  const [approved, setApproved] = useState<Record<Phase, boolean>>({ 1: false, 2: false, 3: false, 4: false });

  // Phase 1: Items
  const [items, setItems] = useState<DetectedItem[]>([]);

  // Phase 2: Measurements (extended items)
  const [measuredItems, setMeasuredItems] = useState<MeasuredItem[]>([]);

  // Phase 3: Yardage
  const [yardageItems, setYardageItems] = useState<YardageItem[]>([]);

  // Phase 4: Line items
  const [lineItems, setLineItems] = useState<LineItem[]>([]);
  const [taxRate, setTaxRate] = useState(0.06);

  // ── Initialize from AI result ──
  useEffect(() => {
    if (!result) return;
    const detected: DetectedItem[] = [];

    // Parse various result formats
    if (result.width_inches || result.height_inches) {
      // Single measure result
      detected.push({
        id: '1',
        type: result.window_type || 'window',
        description: result.notes || 'Detected window',
        checked: true,
        width_inches: result.width_inches || 0,
        height_inches: result.height_inches || 0,
        depth_inches: 0,
        confidence: result.confidence || 0.8,
      });
    }
    if (result.items) {
      result.items.forEach((item: any, i: number) => {
        detected.push({
          id: String(i + 1),
          type: item.type || item.window_type || 'window',
          description: item.description || item.name || `Item ${i + 1}`,
          checked: true,
          width_inches: item.width_inches || item.measurements?.width_inches || 0,
          height_inches: item.height_inches || item.measurements?.height_inches || 0,
          depth_inches: item.depth_inches || 0,
          confidence: item.confidence || 0.7,
        });
      });
    }
    if (result.windows) {
      result.windows.forEach((w: any, i: number) => {
        detected.push({
          id: `w${i + 1}`,
          type: w.window_type || 'window',
          description: w.name || w.description || `Window ${i + 1}`,
          checked: true,
          width_inches: w.width_inches || 0,
          height_inches: w.height_inches || 0,
          depth_inches: 0,
          confidence: w.confidence || 0.7,
        });
      });
    }
    if (result.treatment_suggestions) {
      // Already have items, just attach suggestions
    }
    if (detected.length === 0 && (result.furniture_type || result.style)) {
      // Upholstery result
      detected.push({
        id: '1',
        type: result.furniture_type || 'sofa',
        description: `${result.furniture_type || 'Furniture'} - ${result.style || 'Unknown style'}`,
        checked: true,
        width_inches: result.estimated_dimensions?.width || 0,
        height_inches: result.estimated_dimensions?.height || 0,
        depth_inches: result.estimated_dimensions?.depth || 0,
        confidence: 0.7,
      });
    }

    if (detected.length > 0) setItems(detected);
  }, [result]);

  // ── Phase navigation ──
  const goBack = (targetPhase: Phase) => {
    setPhase(targetPhase);
    // Reset all approvals after the target
    const newApproved = { ...approved };
    for (let p = targetPhase; p <= 4; p++) {
      newApproved[p as Phase] = false;
    }
    setApproved(newApproved);
  };

  // ── Approve Phase 1 → Phase 2 ──
  const approveItems = () => {
    const selected = items.filter(i => i.checked);
    if (selected.length === 0) return;
    setMeasuredItems(selected.map(i => ({
      ...i,
      sill_depth: 0,
      mount_type: 'inside',
      treatment: '',
      lining: '',
      notes: '',
    })));
    setApproved(prev => ({ ...prev, 1: true }));
    setPhase(2);
  };

  // ── Approve Phase 2 → Phase 3 ──
  const approveMeasurements = () => {
    setYardageItems(measuredItems.map(m => ({
      ...m,
      fullness: 2.5,
      pattern_repeat: 0,
      hem_allowance: 8,
      fabric_width: 54,
      cut_length: 0,
      total_yards: 0,
    })));
    setApproved(prev => ({ ...prev, 2: true }));
    setPhase(3);
  };

  // ── Calculate yardage ──
  const calcYardage = (item: YardageItem): { cutLength: number; totalYards: number } => {
    const w = item.width_inches || 0;
    const h = item.height_inches || 0;
    const fabricW = item.fabric_width || 54;
    const fullness = item.fullness || 2.5;
    const hem = item.hem_allowance || 8;
    const patternRepeat = item.pattern_repeat || 0;

    const cutLength = h + hem + (patternRepeat > 0 ? patternRepeat : 0);
    const totalWidth = w * fullness;
    const widths = Math.ceil(totalWidth / fabricW);
    const totalInches = widths * cutLength;
    const totalYards = Math.ceil(totalInches / 36 * 10) / 10;

    return { cutLength, totalYards };
  };

  // ── Approve Phase 3 → Phase 4 ──
  const approveYardage = () => {
    const newLineItems: LineItem[] = [];
    yardageItems.forEach((item, i) => {
      const { totalYards } = calcYardage(item);
      // Fabric line item
      newLineItems.push({
        id: `fab-${i}`,
        description: `${item.description} — Fabric (${totalYards} yds)`,
        category: 'fabric',
        quantity: totalYards,
        unit: 'yd',
        rate: 45, // default $/yd
        amount: Math.round(totalYards * 45 * 100) / 100,
      });
      // Labor
      newLineItems.push({
        id: `lab-${i}`,
        description: `${item.description} — Labor`,
        category: 'labor',
        quantity: 1,
        unit: 'ea',
        rate: 150,
        amount: 150,
      });
      // Lining
      if (item.lining && item.lining !== 'none') {
        newLineItems.push({
          id: `lin-${i}`,
          description: `${item.description} — ${item.lining} lining`,
          category: 'fabric',
          quantity: totalYards * 0.8,
          unit: 'yd',
          rate: 18,
          amount: Math.round(totalYards * 0.8 * 18 * 100) / 100,
        });
      }
    });
    setLineItems(newLineItems);
    setApproved(prev => ({ ...prev, 3: true }));
    setPhase(4);
  };

  // ── Update line item ──
  const updateLineItem = (id: string, field: keyof LineItem, value: any) => {
    setLineItems(prev => prev.map(li => {
      if (li.id !== id) return li;
      const updated = { ...li, [field]: value };
      if (field === 'quantity' || field === 'rate') {
        updated.amount = Math.round((updated.quantity || 0) * (updated.rate || 0) * 100) / 100;
      }
      return updated;
    }));
  };

  const subtotal = lineItems.reduce((s, li) => s + li.amount, 0);
  const tax = Math.round(subtotal * taxRate * 100) / 100;
  const total = Math.round((subtotal + tax) * 100) / 100;

  // ── Phase label ──
  const phases: { id: Phase; label: string; desc: string }[] = [
    { id: 1, label: 'Items', desc: 'Review detected items' },
    { id: 2, label: 'Measurements', desc: 'Verify & adjust dimensions' },
    { id: 3, label: 'Yardage', desc: 'Calculate fabric needs' },
    { id: 4, label: 'Pricing', desc: 'Set rates & finalize' },
  ];

  return (
    <div>
      {/* ── Progress bar ── */}
      <div style={{ marginBottom: 16, padding: '12px 14px', borderRadius: 10, background: '#faf9f7', border: '1px solid #ece8e0' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 6 }}>
          {phases.map((p, i) => {
            const done = approved[p.id];
            const active = phase === p.id;
            return (
              <React.Fragment key={p.id}>
                <button
                  onClick={() => { if (done || active) goBack(p.id); }}
                  className="flex items-center gap-1.5 cursor-pointer transition-all"
                  style={{
                    padding: '5px 12px', borderRadius: 8, fontSize: 11, fontWeight: 600, border: 'none',
                    background: active ? '#b8960c' : done ? '#dcfce7' : 'transparent',
                    color: active ? '#fff' : done ? '#16a34a' : '#999',
                  }}>
                  {done && !active ? <CheckCircle size={12} /> : <span>{p.id}.</span>}
                  {' '}{p.label}
                </button>
                {i < phases.length - 1 && (
                  <div style={{ width: 20, height: 2, background: done ? '#16a34a' : '#ddd', borderRadius: 1 }} />
                )}
              </React.Fragment>
            );
          })}
        </div>
        <div style={{ fontSize: 10, color: '#999', paddingLeft: 2 }}>
          Phase {phase}/4: {phases.find(p => p.id === phase)?.desc}
        </div>
      </div>

      {/* ═══════ PHASE 1: ITEMS ═══════ */}
      {phase === 1 && (
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 10 }}>
            Detected Items ({items.length})
          </div>
          {items.length === 0 && (
            <div style={{ padding: '20px', textAlign: 'center', color: '#999', fontSize: 12 }}>
              No items detected. Add items manually below.
            </div>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {items.map((item, i) => (
              <div key={item.id} style={{
                display: 'flex', alignItems: 'center', gap: 10, padding: '10px 14px', borderRadius: 10,
                border: `1.5px solid ${item.checked ? '#b8960c' : '#ece8e0'}`,
                background: item.checked ? '#fdf8eb' : '#faf9f7',
              }}>
                <button onClick={() => setItems(prev => prev.map((it, idx) => idx === i ? { ...it, checked: !it.checked } : it))}
                  style={{ width: 22, height: 22, borderRadius: 6, border: `2px solid ${item.checked ? '#b8960c' : '#ddd'}`, background: item.checked ? '#b8960c' : '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', flexShrink: 0 }}>
                  {item.checked && <Check size={12} style={{ color: '#fff' }} />}
                </button>
                <select value={item.type}
                  onChange={e => setItems(prev => prev.map((it, idx) => idx === i ? { ...it, type: e.target.value } : it))}
                  style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 12, background: '#fff', minWidth: 100 }}>
                  {ITEM_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</option>)}
                </select>
                <input value={item.description}
                  onChange={e => setItems(prev => prev.map((it, idx) => idx === i ? { ...it, description: e.target.value } : it))}
                  style={{ flex: 1, padding: '6px 10px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 12 }} />
                {item.confidence > 0 && (
                  <span style={{ fontSize: 10, color: item.confidence >= 0.7 ? '#16a34a' : '#f59e0b', fontWeight: 600 }}>
                    {Math.round(item.confidence * 100)}%
                  </span>
                )}
                <button onClick={() => setItems(prev => prev.filter((_, idx) => idx !== i))}
                  className="cursor-pointer hover:text-[#dc2626] transition-colors"
                  style={{ background: 'none', border: 'none', color: '#ccc', padding: 2 }}>
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          </div>

          <button onClick={() => setItems(prev => [...prev, { id: Date.now().toString(), type: 'window', description: 'New item', checked: true, width_inches: 0, height_inches: 0, depth_inches: 0, confidence: 0 }])}
            className="flex items-center gap-1.5 cursor-pointer transition-all hover:bg-[#fdf8eb] mt-3"
            style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7', fontSize: 11, fontWeight: 600, color: '#777' }}>
            <Plus size={12} /> Add Item
          </button>

          <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
            <button onClick={approveItems}
              disabled={items.filter(i => i.checked).length === 0}
              className="flex-1 flex items-center justify-center gap-2 cursor-pointer transition-all hover:brightness-110 disabled:opacity-50"
              style={{ padding: '12px 20px', borderRadius: 10, background: '#b8960c', color: '#fff', fontSize: 13, fontWeight: 700, border: 'none', minHeight: 48 }}>
              <CheckCircle size={16} /> Approve Items & Continue
            </button>
            {onRedetect && (
              <button onClick={onRedetect}
                className="flex items-center gap-1.5 cursor-pointer transition-all hover:bg-[#f0ede8]"
                style={{ padding: '12px 16px', borderRadius: 10, border: '1px solid #ece8e0', background: '#faf9f7', fontSize: 12, fontWeight: 600, color: '#777', minHeight: 48 }}>
                <RefreshCw size={14} /> Re-detect
              </button>
            )}
          </div>
        </div>
      )}

      {/* ═══════ PHASE 2: MEASUREMENTS ═══════ */}
      {phase === 2 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>
              Measurements ({measuredItems.length} items)
            </div>
            <button onClick={() => goBack(1)}
              className="flex items-center gap-1 cursor-pointer transition-all hover:text-[#b8960c]"
              style={{ background: 'none', border: 'none', fontSize: 11, fontWeight: 600, color: '#999' }}>
              <ArrowLeft size={12} /> Back to Items
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {measuredItems.map((item, i) => {
              const isWindow = ['window', 'drapery', 'roman_shade', 'valance', 'cornice'].includes(item.type);
              const currentItem = {
                type: item.type, subtype: item.treatment || undefined,
                measurements: { width_inches: item.width_inches, height_inches: item.height_inches },
                treatment: item.treatment || item.type, mount_type: item.mount_type,
              };
              return (
                <div key={item.id} style={{ padding: '14px 16px', borderRadius: 12, border: '1.5px solid #ece8e0', background: '#faf9f7' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#1a1a1a', marginBottom: 10 }}>
                    {item.description}
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                    {/* Left: form */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                        <label style={{ fontSize: 11 }}>
                          <span style={{ color: '#888', fontWeight: 600 }}>Width (in)</span>
                          <input type="number" value={item.width_inches || ''} onChange={e => setMeasuredItems(prev => prev.map((it, idx) => idx === i ? { ...it, width_inches: parseFloat(e.target.value) || 0 } : it))}
                            style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, marginTop: 3, background: '#fff' }} />
                        </label>
                        <label style={{ fontSize: 11 }}>
                          <span style={{ color: '#888', fontWeight: 600 }}>Height (in)</span>
                          <input type="number" value={item.height_inches || ''} onChange={e => setMeasuredItems(prev => prev.map((it, idx) => idx === i ? { ...it, height_inches: parseFloat(e.target.value) || 0 } : it))}
                            style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 13, marginTop: 3, background: '#fff' }} />
                        </label>
                      </div>
                      {isWindow && (
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                          <label style={{ fontSize: 11 }}>
                            <span style={{ color: '#888', fontWeight: 600 }}>Mount</span>
                            <select value={item.mount_type} onChange={e => setMeasuredItems(prev => prev.map((it, idx) => idx === i ? { ...it, mount_type: e.target.value } : it))}
                              style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 12, marginTop: 3, background: '#fff' }}>
                              <option value="inside">Inside Mount</option>
                              <option value="outside">Outside Mount</option>
                            </select>
                          </label>
                          <label style={{ fontSize: 11 }}>
                            <span style={{ color: '#888', fontWeight: 600 }}>Treatment</span>
                            <select value={item.treatment} onChange={e => setMeasuredItems(prev => prev.map((it, idx) => idx === i ? { ...it, treatment: e.target.value } : it))}
                              style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 12, marginTop: 3, background: '#fff' }}>
                              <option value="">--</option>
                              <option value="pinch_pleat">Pinch Pleat</option>
                              <option value="rod_pocket">Rod Pocket</option>
                              <option value="grommet">Grommet</option>
                              <option value="ripplefold">Ripplefold</option>
                              <option value="goblet">Goblet</option>
                            </select>
                          </label>
                        </div>
                      )}
                      {isWindow && (
                        <label style={{ fontSize: 11 }}>
                          <span style={{ color: '#888', fontWeight: 600 }}>Lining</span>
                          <select value={item.lining} onChange={e => setMeasuredItems(prev => prev.map((it, idx) => idx === i ? { ...it, lining: e.target.value } : it))}
                            style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 12, marginTop: 3, background: '#fff' }}>
                            <option value="">None</option>
                            <option value="standard">Standard</option>
                            <option value="blackout">Blackout</option>
                            <option value="thermal">Thermal</option>
                          </select>
                        </label>
                      )}
                      <input value={item.notes} onChange={e => setMeasuredItems(prev => prev.map((it, idx) => idx === i ? { ...it, notes: e.target.value } : it))}
                        placeholder="Notes..." style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 12, background: '#fff' }} />
                    </div>
                    {/* Right: SVG diagram */}
                    <div>
                      {(item.width_inches > 0 || item.height_inches > 0) ? (
                        <div style={{ border: '1px solid #ece8e0', borderRadius: 10, overflow: 'hidden', background: '#fff', padding: 6 }}>
                          <MeasurementDiagram item={currentItem as any} width={320} height={240} />
                        </div>
                      ) : (
                        <div style={{ height: 240, borderRadius: 10, border: '2px dashed #ece8e0', background: '#faf9f7', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, color: '#aaa' }}>
                          Enter dimensions to see diagram
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
            <button onClick={approveMeasurements}
              className="flex-1 flex items-center justify-center gap-2 cursor-pointer transition-all hover:brightness-110"
              style={{ padding: '12px 20px', borderRadius: 10, background: '#b8960c', color: '#fff', fontSize: 13, fontWeight: 700, border: 'none', minHeight: 48 }}>
              <CheckCircle size={16} /> Approve Measurements & Continue
            </button>
          </div>
        </div>
      )}

      {/* ═══════ PHASE 3: YARDAGE ═══════ */}
      {phase === 3 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>Yardage Calculation</div>
            <button onClick={() => goBack(2)} className="flex items-center gap-1 cursor-pointer" style={{ background: 'none', border: 'none', fontSize: 11, fontWeight: 600, color: '#999' }}>
              <ArrowLeft size={12} /> Back to Measurements
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {yardageItems.map((item, i) => {
              const { cutLength, totalYards } = calcYardage(item);
              return (
                <div key={item.id} style={{ padding: '14px 16px', borderRadius: 12, border: '1.5px solid #ece8e0', background: '#faf9f7' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: '#1a1a1a', marginBottom: 8 }}>
                    {item.description} — {item.width_inches}" × {item.height_inches}"
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6, marginBottom: 10 }}>
                    <label style={{ fontSize: 10 }}>
                      <span style={{ color: '#888', fontWeight: 600 }}>Fullness</span>
                      <select value={item.fullness} onChange={e => setYardageItems(prev => prev.map((it, idx) => idx === i ? { ...it, fullness: parseFloat(e.target.value) } : it))}
                        style={{ width: '100%', padding: '6px', borderRadius: 6, border: '1px solid #ece8e0', fontSize: 12, marginTop: 2 }}>
                        <option value={2}>2×</option>
                        <option value={2.5}>2.5×</option>
                        <option value={3}>3×</option>
                      </select>
                    </label>
                    <label style={{ fontSize: 10 }}>
                      <span style={{ color: '#888', fontWeight: 600 }}>Pattern Repeat (in)</span>
                      <input type="number" value={item.pattern_repeat || ''} onChange={e => setYardageItems(prev => prev.map((it, idx) => idx === i ? { ...it, pattern_repeat: parseFloat(e.target.value) || 0 } : it))}
                        style={{ width: '100%', padding: '6px', borderRadius: 6, border: '1px solid #ece8e0', fontSize: 12, marginTop: 2 }} />
                    </label>
                    <label style={{ fontSize: 10 }}>
                      <span style={{ color: '#888', fontWeight: 600 }}>Hem Allowance (in)</span>
                      <input type="number" value={item.hem_allowance || ''} onChange={e => setYardageItems(prev => prev.map((it, idx) => idx === i ? { ...it, hem_allowance: parseFloat(e.target.value) || 0 } : it))}
                        style={{ width: '100%', padding: '6px', borderRadius: 6, border: '1px solid #ece8e0', fontSize: 12, marginTop: 2 }} />
                    </label>
                    <label style={{ fontSize: 10 }}>
                      <span style={{ color: '#888', fontWeight: 600 }}>Fabric Width (in)</span>
                      <input type="number" value={item.fabric_width || ''} onChange={e => setYardageItems(prev => prev.map((it, idx) => idx === i ? { ...it, fabric_width: parseFloat(e.target.value) || 0 } : it))}
                        style={{ width: '100%', padding: '6px', borderRadius: 6, border: '1px solid #ece8e0', fontSize: 12, marginTop: 2 }} />
                    </label>
                  </div>
                  {/* Calculation breakdown */}
                  <div style={{ padding: '10px 12px', borderRadius: 8, background: '#fff', border: '1px solid #ece8e0', fontSize: 11, color: '#555', lineHeight: 1.8 }}>
                    <div>Cut length: {item.height_inches}" + {item.hem_allowance}" hem{item.pattern_repeat > 0 ? ` + ${item.pattern_repeat}" repeat` : ''} = <strong>{Math.round(cutLength)}"</strong></div>
                    <div>Total width: {item.width_inches}" × {item.fullness}× fullness = <strong>{Math.round(item.width_inches * item.fullness)}"</strong></div>
                    <div>Widths needed: {Math.round(item.width_inches * item.fullness)}" ÷ {item.fabric_width}" = <strong>{Math.ceil(item.width_inches * item.fullness / item.fabric_width)}</strong></div>
                    <div style={{ marginTop: 4, fontSize: 14, fontWeight: 700, color: '#b8960c' }}>
                      Total: {totalYards} yards
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
            <button onClick={approveYardage}
              className="flex-1 flex items-center justify-center gap-2 cursor-pointer transition-all hover:brightness-110"
              style={{ padding: '12px 20px', borderRadius: 10, background: '#b8960c', color: '#fff', fontSize: 13, fontWeight: 700, border: 'none', minHeight: 48 }}>
              <CheckCircle size={16} /> Approve Yardage & Continue
            </button>
          </div>
        </div>
      )}

      {/* ═══════ PHASE 4: LINE ITEMS & PRICING ═══════ */}
      {phase === 4 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>Line Items & Pricing</div>
            <button onClick={() => goBack(3)} className="flex items-center gap-1 cursor-pointer" style={{ background: 'none', border: 'none', fontSize: 11, fontWeight: 600, color: '#999' }}>
              <ArrowLeft size={12} /> Back to Yardage
            </button>
          </div>

          <div style={{ border: '1.5px solid #ece8e0', borderRadius: 12, overflow: 'hidden' }}>
            {/* Header */}
            <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr 1fr 1fr 36px', gap: 0, padding: '8px 14px', background: '#f5f3ef', borderBottom: '1px solid #ece8e0', fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase' }}>
              <div>Description</div>
              <div style={{ textAlign: 'right' }}>Qty</div>
              <div style={{ textAlign: 'right' }}>Rate</div>
              <div style={{ textAlign: 'right' }}>Amount</div>
              <div />
            </div>
            {lineItems.map(li => (
              <div key={li.id} style={{ display: 'grid', gridTemplateColumns: '3fr 1fr 1fr 1fr 36px', gap: 0, padding: '8px 14px', borderBottom: '1px solid #f0ede8', fontSize: 12, alignItems: 'center' }}>
                <input value={li.description} onChange={e => updateLineItem(li.id, 'description', e.target.value)}
                  style={{ border: 'none', background: 'transparent', fontSize: 12, padding: '2px 0', width: '100%' }} />
                <input type="number" value={li.quantity} onChange={e => updateLineItem(li.id, 'quantity', parseFloat(e.target.value) || 0)}
                  style={{ border: 'none', background: 'transparent', fontSize: 12, textAlign: 'right', width: '100%', padding: '2px 0' }} />
                <div style={{ textAlign: 'right' }}>
                  $<input type="number" value={li.rate} onChange={e => updateLineItem(li.id, 'rate', parseFloat(e.target.value) || 0)}
                    style={{ border: 'none', background: 'transparent', fontSize: 12, textAlign: 'right', width: 60, padding: '2px 0' }} />
                </div>
                <div style={{ textAlign: 'right', fontWeight: 600 }}>${li.amount.toFixed(2)}</div>
                <button onClick={() => setLineItems(prev => prev.filter(l => l.id !== li.id))}
                  className="cursor-pointer hover:text-[#dc2626] transition-colors"
                  style={{ background: 'none', border: 'none', color: '#ccc', padding: 2, display: 'flex', justifyContent: 'center' }}>
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
          </div>

          <button onClick={() => setLineItems(prev => [...prev, { id: Date.now().toString(), description: 'Custom item', category: 'custom', quantity: 1, unit: 'ea', rate: 0, amount: 0 }])}
            className="flex items-center gap-1.5 cursor-pointer transition-all hover:bg-[#fdf8eb] mt-2"
            style={{ padding: '8px 14px', borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7', fontSize: 11, fontWeight: 600, color: '#777' }}>
            <Plus size={12} /> Add Line Item
          </button>

          {/* Totals */}
          <div style={{ marginTop: 12, padding: '12px 14px', borderRadius: 10, background: '#faf9f7', border: '1px solid #ece8e0' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
              <span>Subtotal</span>
              <span style={{ fontWeight: 600 }}>${subtotal.toFixed(2)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12, marginBottom: 4 }}>
              <span>Tax ({(taxRate * 100).toFixed(0)}%)</span>
              <span style={{ fontWeight: 600 }}>${tax.toFixed(2)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 16, fontWeight: 700, color: '#b8960c', borderTop: '1px solid #ece8e0', paddingTop: 8, marginTop: 4 }}>
              <span>Total</span>
              <span>${total.toFixed(2)}</span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
            <button
              onClick={() => {
                if (onFinalize) onFinalize({ items: measuredItems, lineItems, total });
                if (onAddToQuote) onAddToQuote({ items: measuredItems, lineItems, total, subtotal, tax, taxRate });
              }}
              className="flex-1 flex items-center justify-center gap-2 cursor-pointer transition-all hover:brightness-110"
              style={{ padding: '12px 20px', borderRadius: 10, background: '#16a34a', color: '#fff', fontSize: 13, fontWeight: 700, border: 'none', minHeight: 48 }}>
              <CheckCircle size={16} /> Finalize Quote
            </button>
            {onAddToQuote && (
              <button
                onClick={() => onAddToQuote({ items: measuredItems, lineItems, total, subtotal, tax, taxRate, addToExisting: true })}
                className="flex items-center gap-1.5 cursor-pointer transition-all hover:bg-[#fdf8eb]"
                style={{ padding: '12px 16px', borderRadius: 10, border: '1.5px solid #b8960c', background: '#faf9f7', fontSize: 12, fontWeight: 600, color: '#b8960c', minHeight: 48 }}>
                Add to Existing Quote
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
