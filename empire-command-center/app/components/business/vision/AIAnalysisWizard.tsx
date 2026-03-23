'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  CheckCircle, Check, Plus, Trash2, ArrowLeft, Edit3,
  Sofa, Armchair, Package, Scissors, Ruler, DollarSign,
  ChevronRight, X, AlertCircle, Eye
} from 'lucide-react';

/* ═══════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════ */

export interface QuoteLineItem {
  description: string;
  category: 'fabric' | 'labor' | 'foam' | 'hardware' | 'other';
  quantity: number;
  unit: string;
  rate: number;
  amount: number;
  notes?: string;
}

interface DetectedItem {
  id: string;
  type: string;
  description: string;
  checked: boolean;
  confidence: number;
  condition?: string;
  width: number;
  depth: number;
  height: number;
  cushions: {
    seat: number;
    back: number;
    throw: number;
  };
}

type WorkType =
  | 'full_reupholster'
  | 'cushion_replacement'
  | 'slipcover'
  | 'recover'
  | 'repair'
  | 'refinish';

interface ScopeSelection {
  itemId: string;
  workType: WorkType;
  additionalWork: string[];
  customWork: string[];
}

interface PricingLine {
  id: string;
  itemId: string;
  description: string;
  category: QuoteLineItem['category'];
  quantity: number;
  unit: string;
  rate: number;
  amount: number;
  formula: string;
  notes?: string;
}

type Step = 1 | 2 | 3 | 4;

interface AIAnalysisWizardProps {
  photoUrl: string;
  analysisResult: any;
  onComplete: (items: QuoteLineItem[]) => void;
  onCancel: () => void;
}

/* ═══════════════════════════════════════════════════════════
   Constants
   ═══════════════════════════════════════════════════════════ */

const FURNITURE_TYPES = [
  'sofa', 'loveseat', 'chair', 'armchair', 'recliner', 'ottoman',
  'sectional', 'chaise', 'bench', 'headboard', 'dining_chair',
  'barstool', 'wingback', 'club_chair', 'settee', 'other',
];

const WORK_TYPES: { value: WorkType; label: string; description: string }[] = [
  { value: 'full_reupholster', label: 'Full Reupholster', description: 'Strip old fabric, repair frame, new fabric & foam' },
  { value: 'cushion_replacement', label: 'Cushion Replacement', description: 'Replace cushion foam and recover cushion covers' },
  { value: 'slipcover', label: 'Slipcover', description: 'Custom-fitted removable slipcover over existing upholstery' },
  { value: 'recover', label: 'Recover', description: 'New fabric over existing padding without full strip-down' },
  { value: 'repair', label: 'Repair', description: 'Fix specific damage: seams, tears, sagging, broken springs' },
  { value: 'refinish', label: 'Refinish', description: 'Wood frame refinishing: strip, sand, stain or paint' },
];

const ADDITIONAL_WORK_OPTIONS = [
  { value: 'new_foam', label: 'New Foam', category: 'foam' as const },
  { value: 'welting_piping', label: 'Welting / Piping', category: 'labor' as const },
  { value: 'tufting', label: 'Tufting', category: 'labor' as const },
  { value: 'nailhead_trim', label: 'Nailhead Trim', category: 'hardware' as const },
  { value: 'skirt', label: 'Skirt', category: 'labor' as const },
  { value: 'spring_repair', label: 'Spring Repair', category: 'labor' as const },
  { value: 'webbing', label: 'Webbing', category: 'labor' as const },
];

const BASE_LABOR_RATES: Record<WorkType, number> = {
  full_reupholster: 850,
  cushion_replacement: 350,
  slipcover: 600,
  recover: 550,
  repair: 250,
  refinish: 400,
};

const ADDITIONAL_WORK_RATES: Record<string, { rate: number; unit: string }> = {
  new_foam: { rate: 85, unit: 'cushion' },
  welting_piping: { rate: 12, unit: 'ft' },
  tufting: { rate: 175, unit: 'ea' },
  nailhead_trim: { rate: 8, unit: 'ft' },
  skirt: { rate: 185, unit: 'ea' },
  spring_repair: { rate: 125, unit: 'ea' },
  webbing: { rate: 95, unit: 'ea' },
};

const STEP_META: { id: Step; label: string; icon: React.ReactNode }[] = [
  { id: 1, label: 'Identify', icon: <Eye size={14} /> },
  { id: 2, label: 'Measurements', icon: <Ruler size={14} /> },
  { id: 3, label: 'Scope', icon: <Scissors size={14} /> },
  { id: 4, label: 'Pricing', icon: <DollarSign size={14} /> },
];

/* ═══════════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════════ */

function formatType(t: string): string {
  return t.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function confidenceBadge(conf: number) {
  const pct = Math.round(conf * 100);
  let bg = '#dcfce7';
  let color = '#16a34a';
  let label = 'High';
  if (conf < 0.5) { bg = '#fef2f2'; color = '#dc2626'; label = 'Low'; }
  else if (conf < 0.75) { bg = '#fefce8'; color = '#ca8a04'; label = 'Medium'; }
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '2px 8px', borderRadius: 20, fontSize: 10, fontWeight: 700,
      background: bg, color,
    }}>
      {pct}% {label}
    </span>
  );
}

function uid(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

/* ═══════════════════════════════════════════════════════════
   Component
   ═══════════════════════════════════════════════════════════ */

export default function AIAnalysisWizard({
  photoUrl,
  analysisResult,
  onComplete,
  onCancel,
}: AIAnalysisWizardProps) {
  const [step, setStep] = useState<Step>(1);
  const [completedSteps, setCompletedSteps] = useState<Set<Step>>(new Set());

  // Step 1: Detected items
  const [items, setItems] = useState<DetectedItem[]>([]);

  // Step 2: Measurements (uses same items array, just edited in step 2)
  // Step 3: Scope
  const [scopes, setScopes] = useState<ScopeSelection[]>([]);

  // Step 4: Pricing
  const [pricingLines, setPricingLines] = useState<PricingLine[]>([]);

  /* ── Initialize from AI result ── */
  useEffect(() => {
    if (!analysisResult) return;
    const detected: DetectedItem[] = [];

    const dims = analysisResult.estimated_dimensions || {};
    const cushions = analysisResult.cushion_counts || analysisResult.cushions || {};

    if (analysisResult.all_furniture && Array.isArray(analysisResult.all_furniture)) {
      analysisResult.all_furniture.forEach((item: any, i: number) => {
        const itemDims = item.estimated_dimensions || item.dimensions || dims;
        const itemCushions = item.cushion_counts || item.cushions || cushions;
        detected.push({
          id: uid(),
          type: item.furniture_type || item.type || 'other',
          description: item.description || item.name || `${formatType(item.furniture_type || item.type || 'Item')} ${i + 1}`,
          checked: true,
          confidence: item.confidence || 0.7,
          condition: item.condition || analysisResult.condition || '',
          width: itemDims.width || itemDims.width_inches || 0,
          depth: itemDims.depth || itemDims.depth_inches || 0,
          height: itemDims.height || itemDims.height_inches || 0,
          cushions: {
            seat: itemCushions.seat || itemCushions.seat_cushions || 0,
            back: itemCushions.back || itemCushions.back_cushions || 0,
            throw: itemCushions.throw || itemCushions.throw_pillows || 0,
          },
        });
      });
    }

    // Fallback: single main furniture item
    if (detected.length === 0 && (analysisResult.furniture_type || analysisResult.type || analysisResult.style)) {
      detected.push({
        id: uid(),
        type: analysisResult.furniture_type || analysisResult.type || 'sofa',
        description: [
          formatType(analysisResult.furniture_type || analysisResult.type || 'Furniture'),
          analysisResult.style ? `- ${analysisResult.style}` : '',
        ].filter(Boolean).join(' '),
        checked: true,
        confidence: analysisResult.confidence || 0.7,
        condition: analysisResult.condition || '',
        width: dims.width || dims.width_inches || 0,
        depth: dims.depth || dims.depth_inches || 0,
        height: dims.height || dims.height_inches || 0,
        cushions: {
          seat: cushions.seat || cushions.seat_cushions || 0,
          back: cushions.back || cushions.back_cushions || 0,
          throw: cushions.throw || cushions.throw_pillows || 0,
        },
      });
    }

    // Fallback: items array
    if (detected.length === 0 && analysisResult.items && Array.isArray(analysisResult.items)) {
      analysisResult.items.forEach((item: any, i: number) => {
        const itemDims = item.estimated_dimensions || item.dimensions || {};
        detected.push({
          id: uid(),
          type: item.furniture_type || item.type || 'other',
          description: item.description || item.name || `Item ${i + 1}`,
          checked: true,
          confidence: item.confidence || 0.7,
          condition: item.condition || '',
          width: itemDims.width || item.width_inches || 0,
          depth: itemDims.depth || item.depth_inches || 0,
          height: itemDims.height || item.height_inches || 0,
          cushions: { seat: 0, back: 0, throw: 0 },
        });
      });
    }

    if (detected.length > 0) setItems(detected);
  }, [analysisResult]);

  /* ── Item mutations ── */
  const updateItem = useCallback((id: string, patch: Partial<DetectedItem>) => {
    setItems(prev => prev.map(it => it.id === id ? { ...it, ...patch } : it));
  }, []);

  const removeItem = useCallback((id: string) => {
    setItems(prev => prev.filter(it => it.id !== id));
  }, []);

  const addItem = useCallback(() => {
    setItems(prev => [...prev, {
      id: uid(),
      type: 'other',
      description: '',
      checked: true,
      confidence: 0,
      condition: '',
      width: 0,
      depth: 0,
      height: 0,
      cushions: { seat: 0, back: 0, throw: 0 },
    }]);
  }, []);

  /* ── Selected items (checked) ── */
  const selectedItems = useMemo(() => items.filter(i => i.checked), [items]);

  /* ── Step transitions ── */
  const approveStep1 = () => {
    if (selectedItems.length === 0) return;
    setCompletedSteps(prev => new Set([...prev, 1]));
    setStep(2);
  };

  const approveStep2 = () => {
    // Initialize scopes for each selected item
    setScopes(selectedItems.map(item => ({
      itemId: item.id,
      workType: 'full_reupholster',
      additionalWork: [],
      customWork: [],
    })));
    setCompletedSteps(prev => new Set([...prev, 2]));
    setStep(3);
  };

  const approveStep3 = () => {
    // Generate pricing lines from scope selections
    const lines: PricingLine[] = [];

    selectedItems.forEach(item => {
      const scope = scopes.find(s => s.itemId === item.id);
      if (!scope) return;

      const workLabel = WORK_TYPES.find(w => w.value === scope.workType)?.label || scope.workType;
      const fabricYards = analysisResult?.fabric_yards_plain || analysisResult?.fabric_estimate?.yards_plain || 8;

      // Fabric line
      const fabricRate = 45;
      lines.push({
        id: uid(),
        itemId: item.id,
        description: `${item.description} - Fabric`,
        category: 'fabric',
        quantity: Math.round(fabricYards * 10) / 10,
        unit: 'yd',
        rate: fabricRate,
        amount: Math.round(fabricYards * fabricRate * 100) / 100,
        formula: `${fabricYards} yards x $${fabricRate}/yd`,
      });

      // Labor line
      const laborRate = BASE_LABOR_RATES[scope.workType];
      lines.push({
        id: uid(),
        itemId: item.id,
        description: `${item.description} - ${workLabel} Labor`,
        category: 'labor',
        quantity: 1,
        unit: 'ea',
        rate: laborRate,
        amount: laborRate,
        formula: `${workLabel} base rate`,
      });

      // Additional work items
      scope.additionalWork.forEach(workKey => {
        const opt = ADDITIONAL_WORK_OPTIONS.find(o => o.value === workKey);
        const rateInfo = ADDITIONAL_WORK_RATES[workKey];
        if (!opt || !rateInfo) return;

        let qty = 1;
        if (workKey === 'new_foam') {
          qty = item.cushions.seat + item.cushions.back || 1;
        } else if (workKey === 'welting_piping' || workKey === 'nailhead_trim') {
          // Estimate perimeter in feet: (w + d) * 2 / 12
          qty = Math.round(((item.width + item.depth) * 2) / 12) || 6;
        }

        lines.push({
          id: uid(),
          itemId: item.id,
          description: `${item.description} - ${opt.label}`,
          category: opt.category,
          quantity: qty,
          unit: rateInfo.unit,
          rate: rateInfo.rate,
          amount: Math.round(qty * rateInfo.rate * 100) / 100,
          formula: `${qty} ${rateInfo.unit} x $${rateInfo.rate}/${rateInfo.unit}`,
        });
      });

      // Custom work items
      scope.customWork.forEach(label => {
        lines.push({
          id: uid(),
          itemId: item.id,
          description: `${item.description} - ${label}`,
          category: 'other',
          quantity: 1,
          unit: 'ea',
          rate: 0,
          amount: 0,
          formula: 'Custom - set rate',
        });
      });
    });

    setPricingLines(lines);
    setCompletedSteps(prev => new Set([...prev, 3]));
    setStep(4);
  };

  const finalizeQuote = () => {
    const lineItems: QuoteLineItem[] = pricingLines.map(pl => ({
      description: pl.description,
      category: pl.category,
      quantity: pl.quantity,
      unit: pl.unit,
      rate: pl.rate,
      amount: pl.amount,
      notes: pl.notes,
    }));
    onComplete(lineItems);
  };

  /* ── Pricing line mutations ── */
  const updatePricingLine = useCallback((id: string, patch: Partial<PricingLine>) => {
    setPricingLines(prev => prev.map(pl => {
      if (pl.id !== id) return pl;
      const updated = { ...pl, ...patch };
      if ('quantity' in patch || 'rate' in patch) {
        updated.amount = Math.round((updated.quantity || 0) * (updated.rate || 0) * 100) / 100;
        updated.formula = `${updated.quantity} ${updated.unit} x $${updated.rate}/${updated.unit}`;
      }
      return updated;
    }));
  }, []);

  const removePricingLine = useCallback((id: string) => {
    setPricingLines(prev => prev.filter(pl => pl.id !== id));
  }, []);

  const addPricingLine = useCallback(() => {
    setPricingLines(prev => [...prev, {
      id: uid(),
      itemId: '',
      description: 'Custom item',
      category: 'other' as const,
      quantity: 1,
      unit: 'ea',
      rate: 0,
      amount: 0,
      formula: 'Custom',
    }]);
  }, []);

  const subtotal = useMemo(() => pricingLines.reduce((sum, pl) => sum + pl.amount, 0), [pricingLines]);

  /* ── Scope mutations ── */
  const updateScope = useCallback((itemId: string, patch: Partial<ScopeSelection>) => {
    setScopes(prev => prev.map(s => s.itemId === itemId ? { ...s, ...patch } : s));
  }, []);

  const toggleAdditionalWork = useCallback((itemId: string, workKey: string) => {
    setScopes(prev => prev.map(s => {
      if (s.itemId !== itemId) return s;
      const has = s.additionalWork.includes(workKey);
      return {
        ...s,
        additionalWork: has
          ? s.additionalWork.filter(w => w !== workKey)
          : [...s.additionalWork, workKey],
      };
    }));
  }, []);

  const addCustomWork = useCallback((itemId: string, label: string) => {
    if (!label.trim()) return;
    setScopes(prev => prev.map(s => {
      if (s.itemId !== itemId) return s;
      return { ...s, customWork: [...s.customWork, label.trim()] };
    }));
  }, []);

  const removeCustomWork = useCallback((itemId: string, idx: number) => {
    setScopes(prev => prev.map(s => {
      if (s.itemId !== itemId) return s;
      return { ...s, customWork: s.customWork.filter((_, i) => i !== idx) };
    }));
  }, []);

  /* ── Go back ── */
  const goBack = (target: Step) => {
    setCompletedSteps(prev => {
      const next = new Set(prev);
      for (let s = target; s <= 4; s++) next.delete(s as Step);
      return next;
    });
    setStep(target);
  };

  /* ── Custom work input state per scope ── */
  const [customWorkInputs, setCustomWorkInputs] = useState<Record<string, string>>({});

  /* ═══════════════════════════════════════════════════════════
     Render
     ═══════════════════════════════════════════════════════════ */

  return (
    <div style={{ background: '#faf9f7', borderRadius: 16, padding: 24, minHeight: 400 }}>

      {/* ── Progress Indicator ── */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        gap: 0, marginBottom: 28, padding: '16px 20px',
        background: '#fff', borderRadius: 12, border: '1px solid #e8e4dc',
      }}>
        {STEP_META.map((s, i) => {
          const done = completedSteps.has(s.id);
          const active = step === s.id;
          return (
            <React.Fragment key={s.id}>
              <button
                onClick={() => { if (done) goBack(s.id); }}
                disabled={!done && !active}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '8px 16px', borderRadius: 10, border: 'none',
                  cursor: done ? 'pointer' : 'default',
                  background: active ? '#16a34a' : done ? '#dcfce7' : 'transparent',
                  color: active ? '#fff' : done ? '#16a34a' : '#aaa',
                  fontWeight: 700, fontSize: 13, transition: 'all 0.2s',
                }}
              >
                <span style={{
                  width: 26, height: 26, borderRadius: '50%', display: 'flex',
                  alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 800,
                  background: active ? 'rgba(255,255,255,0.2)' : done ? '#16a34a' : '#e8e4dc',
                  color: active ? '#fff' : done ? '#fff' : '#999',
                }}>
                  {done && !active ? <Check size={13} strokeWidth={3} /> : s.id}
                </span>
                <span className="hidden sm:inline">{s.label}</span>
              </button>
              {i < STEP_META.length - 1 && (
                <div style={{
                  width: 32, height: 2, borderRadius: 1,
                  background: done ? '#16a34a' : '#e8e4dc',
                  margin: '0 4px',
                }} />
              )}
            </React.Fragment>
          );
        })}
      </div>

      <div style={{ fontSize: 11, color: '#999', textAlign: 'center', marginTop: -20, marginBottom: 20 }}>
        Step {step} of 4
      </div>

      {/* ═══════ STEP 1: IDENTIFY ═══════ */}
      {step === 1 && (
        <div>
          <div style={{ fontSize: 18, fontWeight: 800, color: '#1a1a1a', marginBottom: 4 }}>
            Identify Furniture
          </div>
          <p style={{ fontSize: 13, color: '#777', marginBottom: 20 }}>
            Review the AI-detected items. Check or uncheck, edit descriptions, and add any missed pieces.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            {/* Left: Photo */}
            <div style={{
              background: '#fff', borderRadius: 12, border: '1px solid #e8e4dc',
              overflow: 'hidden',
            }}>
              <img
                src={photoUrl}
                alt="Uploaded furniture photo"
                style={{ width: '100%', height: 'auto', display: 'block', objectFit: 'cover', maxHeight: 400 }}
              />
            </div>

            {/* Right: Detected items */}
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 10 }}>
                Detected Items ({items.length})
              </div>

              {items.length === 0 && (
                <div style={{
                  padding: 24, textAlign: 'center', color: '#999', fontSize: 13,
                  background: '#fff', borderRadius: 12, border: '1px dashed #e8e4dc',
                }}>
                  <AlertCircle size={20} style={{ margin: '0 auto 8px', opacity: 0.5 }} />
                  No items detected. Add items manually below.
                </div>
              )}

              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {items.map(item => (
                  <div key={item.id} style={{
                    padding: '12px 14px', borderRadius: 12,
                    border: `1.5px solid ${item.checked ? '#16a34a' : '#e8e4dc'}`,
                    background: item.checked ? '#f0fdf4' : '#fff',
                    transition: 'all 0.15s',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                      {/* Checkbox */}
                      <button
                        onClick={() => updateItem(item.id, { checked: !item.checked })}
                        style={{
                          width: 22, height: 22, borderRadius: 6, flexShrink: 0,
                          border: `2px solid ${item.checked ? '#16a34a' : '#d4d0c8'}`,
                          background: item.checked ? '#16a34a' : '#fff',
                          display: 'flex', alignItems: 'center', justifyContent: 'center',
                          cursor: 'pointer', transition: 'all 0.15s',
                        }}
                      >
                        {item.checked && <Check size={13} style={{ color: '#fff' }} strokeWidth={3} />}
                      </button>

                      {/* Type selector */}
                      <select
                        value={item.type}
                        onChange={e => updateItem(item.id, { type: e.target.value })}
                        style={{
                          padding: '6px 10px', borderRadius: 8,
                          border: '1px solid #e8e4dc', fontSize: 12,
                          background: '#fff', fontWeight: 600, minWidth: 110,
                        }}
                      >
                        {FURNITURE_TYPES.map(t => (
                          <option key={t} value={t}>{formatType(t)}</option>
                        ))}
                      </select>

                      {/* Confidence badge */}
                      {item.confidence > 0 && confidenceBadge(item.confidence)}

                      {/* Delete */}
                      <button
                        onClick={() => removeItem(item.id)}
                        style={{
                          background: 'none', border: 'none', color: '#ccc',
                          cursor: 'pointer', padding: 2, marginLeft: 'auto',
                          transition: 'color 0.15s',
                        }}
                        onMouseEnter={e => (e.currentTarget.style.color = '#dc2626')}
                        onMouseLeave={e => (e.currentTarget.style.color = '#ccc')}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>

                    {/* Description */}
                    <input
                      value={item.description}
                      onChange={e => updateItem(item.id, { description: e.target.value })}
                      placeholder="Description..."
                      style={{
                        width: '100%', padding: '7px 10px', borderRadius: 8,
                        border: '1px solid #e8e4dc', fontSize: 12, background: '#fff',
                        boxSizing: 'border-box',
                      }}
                    />

                    {/* Condition */}
                    {item.condition && (
                      <div style={{ marginTop: 6, fontSize: 11, color: '#888' }}>
                        Condition: <span style={{ fontWeight: 600, color: '#555' }}>{item.condition}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Add Item */}
              <button
                onClick={addItem}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '10px 14px', borderRadius: 10, marginTop: 10,
                  border: '1.5px dashed #d4d0c8', background: '#fff',
                  fontSize: 12, fontWeight: 600, color: '#888',
                  cursor: 'pointer', transition: 'all 0.15s', width: '100%',
                  justifyContent: 'center',
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = '#16a34a'; e.currentTarget.style.color = '#16a34a'; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = '#d4d0c8'; e.currentTarget.style.color = '#888'; }}
              >
                <Plus size={14} /> Add Item
              </button>
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 10, marginTop: 24, justifyContent: 'flex-end' }}>
            <button
              onClick={onCancel}
              style={{
                padding: '12px 24px', borderRadius: 10, fontSize: 13, fontWeight: 600,
                border: '1px solid #e8e4dc', background: '#fff', color: '#777',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              onClick={approveStep1}
              disabled={selectedItems.length === 0}
              style={{
                padding: '12px 28px', borderRadius: 10, fontSize: 14, fontWeight: 700,
                border: 'none', color: '#fff', cursor: 'pointer',
                background: selectedItems.length === 0 ? '#ccc' : '#16a34a',
                opacity: selectedItems.length === 0 ? 0.6 : 1,
                display: 'flex', alignItems: 'center', gap: 8,
                transition: 'all 0.15s',
              }}
            >
              <CheckCircle size={16} />
              Approve Items & Continue
            </button>
          </div>
        </div>
      )}

      {/* ═══════ STEP 2: MEASUREMENTS ═══════ */}
      {step === 2 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#1a1a1a' }}>
              Verify Measurements
            </div>
            <button
              onClick={() => goBack(1)}
              style={{
                display: 'flex', alignItems: 'center', gap: 4,
                background: 'none', border: 'none', fontSize: 12, fontWeight: 600,
                color: '#999', cursor: 'pointer',
              }}
            >
              <ArrowLeft size={14} /> Back to Identify
            </button>
          </div>
          <p style={{ fontSize: 13, color: '#777', marginBottom: 20 }}>
            Confirm or adjust AI-estimated dimensions and cushion counts for each piece.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {selectedItems.map(item => (
              <div key={item.id} style={{
                padding: '18px 20px', borderRadius: 12,
                background: '#fff', border: '1px solid #e8e4dc',
              }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 14 }}>
                  {item.description || formatType(item.type)}
                </div>

                {/* Dimensions */}
                <div style={{ fontSize: 11, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 8, letterSpacing: 0.5 }}>
                  Dimensions (inches)
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 16 }}>
                  {(['width', 'depth', 'height'] as const).map(dim => (
                    <label key={dim} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      <span style={{ fontSize: 11, fontWeight: 600, color: '#888', textTransform: 'capitalize' }}>{dim}</span>
                      <input
                        type="number"
                        value={item[dim] || ''}
                        onChange={e => updateItem(item.id, { [dim]: parseFloat(e.target.value) || 0 })}
                        placeholder="0"
                        style={{
                          padding: '10px 12px', borderRadius: 8,
                          border: '1px solid #e8e4dc', fontSize: 14, fontWeight: 600,
                          background: '#faf9f7', width: '100%', boxSizing: 'border-box',
                        }}
                      />
                    </label>
                  ))}
                </div>

                {/* Cushion counts */}
                <div style={{ fontSize: 11, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 8, letterSpacing: 0.5 }}>
                  Cushion Counts
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
                  {(['seat', 'back', 'throw'] as const).map(cType => (
                    <label key={cType} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                      <span style={{ fontSize: 11, fontWeight: 600, color: '#888', textTransform: 'capitalize' }}>{cType} Cushions</span>
                      <input
                        type="number"
                        min={0}
                        value={item.cushions[cType] || ''}
                        onChange={e => updateItem(item.id, {
                          cushions: { ...item.cushions, [cType]: parseInt(e.target.value) || 0 },
                        })}
                        placeholder="0"
                        style={{
                          padding: '10px 12px', borderRadius: 8,
                          border: '1px solid #e8e4dc', fontSize: 14, fontWeight: 600,
                          background: '#faf9f7', width: '100%', boxSizing: 'border-box',
                        }}
                      />
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 10, marginTop: 24, justifyContent: 'flex-end' }}>
            <button
              onClick={onCancel}
              style={{
                padding: '12px 24px', borderRadius: 10, fontSize: 13, fontWeight: 600,
                border: '1px solid #e8e4dc', background: '#fff', color: '#777',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              onClick={approveStep2}
              style={{
                padding: '12px 28px', borderRadius: 10, fontSize: 14, fontWeight: 700,
                border: 'none', background: '#16a34a', color: '#fff', cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 8,
              }}
            >
              <CheckCircle size={16} />
              Approve Measurements & Continue
            </button>
          </div>
        </div>
      )}

      {/* ═══════ STEP 3: SCOPE ═══════ */}
      {step === 3 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#1a1a1a' }}>
              Define Scope of Work
            </div>
            <button
              onClick={() => goBack(2)}
              style={{
                display: 'flex', alignItems: 'center', gap: 4,
                background: 'none', border: 'none', fontSize: 12, fontWeight: 600,
                color: '#999', cursor: 'pointer',
              }}
            >
              <ArrowLeft size={14} /> Back to Measurements
            </button>
          </div>
          <p style={{ fontSize: 13, color: '#777', marginBottom: 20 }}>
            Choose the type of work and any additional services for each piece.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {selectedItems.map(item => {
              const scope = scopes.find(s => s.itemId === item.id);
              if (!scope) return null;
              const customInput = customWorkInputs[item.id] || '';

              return (
                <div key={item.id} style={{
                  padding: '20px', borderRadius: 12,
                  background: '#fff', border: '1px solid #e8e4dc',
                }}>
                  <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }}>
                    {item.description || formatType(item.type)}
                  </div>

                  {/* Work Type Cards */}
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 8, letterSpacing: 0.5 }}>
                    Work Type
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 20 }}>
                    {WORK_TYPES.map(wt => {
                      const selected = scope.workType === wt.value;
                      return (
                        <button
                          key={wt.value}
                          onClick={() => updateScope(item.id, { workType: wt.value })}
                          style={{
                            padding: '12px 14px', borderRadius: 10, textAlign: 'left',
                            border: `2px solid ${selected ? '#16a34a' : '#e8e4dc'}`,
                            background: selected ? '#f0fdf4' : '#faf9f7',
                            cursor: 'pointer', transition: 'all 0.15s',
                          }}
                        >
                          <div style={{ fontSize: 12, fontWeight: 700, color: selected ? '#16a34a' : '#1a1a1a', marginBottom: 4 }}>
                            {wt.label}
                          </div>
                          <div style={{ fontSize: 10, color: '#888', lineHeight: 1.4 }}>
                            {wt.description}
                          </div>
                        </button>
                      );
                    })}
                  </div>

                  {/* Additional Work Checkboxes */}
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 8, letterSpacing: 0.5 }}>
                    Additional Work
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6, marginBottom: 12 }}>
                    {ADDITIONAL_WORK_OPTIONS.map(opt => {
                      const checked = scope.additionalWork.includes(opt.value);
                      return (
                        <button
                          key={opt.value}
                          onClick={() => toggleAdditionalWork(item.id, opt.value)}
                          style={{
                            padding: '8px 12px', borderRadius: 8, textAlign: 'center',
                            border: `1.5px solid ${checked ? '#16a34a' : '#e8e4dc'}`,
                            background: checked ? '#f0fdf4' : '#fff',
                            cursor: 'pointer', transition: 'all 0.15s',
                            fontSize: 11, fontWeight: checked ? 700 : 500,
                            color: checked ? '#16a34a' : '#666',
                          }}
                        >
                          {checked && <Check size={10} style={{ marginRight: 4, verticalAlign: -1 }} />}
                          {opt.label}
                        </button>
                      );
                    })}
                  </div>

                  {/* Custom Work Items */}
                  {scope.customWork.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
                      {scope.customWork.map((cw, idx) => (
                        <span key={idx} style={{
                          display: 'inline-flex', alignItems: 'center', gap: 4,
                          padding: '4px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600,
                          background: '#eff6ff', color: '#2563eb', border: '1px solid #bfdbfe',
                        }}>
                          {cw}
                          <button
                            onClick={() => removeCustomWork(item.id, idx)}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#93c5fd', padding: 0, display: 'flex' }}
                          >
                            <X size={11} />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Add Custom */}
                  <div style={{ display: 'flex', gap: 6 }}>
                    <input
                      value={customInput}
                      onChange={e => setCustomWorkInputs(prev => ({ ...prev, [item.id]: e.target.value }))}
                      onKeyDown={e => {
                        if (e.key === 'Enter' && customInput.trim()) {
                          addCustomWork(item.id, customInput);
                          setCustomWorkInputs(prev => ({ ...prev, [item.id]: '' }));
                        }
                      }}
                      placeholder="Add custom work item..."
                      style={{
                        flex: 1, padding: '8px 12px', borderRadius: 8,
                        border: '1px solid #e8e4dc', fontSize: 12, background: '#faf9f7',
                      }}
                    />
                    <button
                      onClick={() => {
                        if (customInput.trim()) {
                          addCustomWork(item.id, customInput);
                          setCustomWorkInputs(prev => ({ ...prev, [item.id]: '' }));
                        }
                      }}
                      style={{
                        padding: '8px 14px', borderRadius: 8, fontSize: 11, fontWeight: 600,
                        border: '1px solid #e8e4dc', background: '#fff', color: '#777',
                        cursor: 'pointer',
                      }}
                    >
                      <Plus size={13} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 10, marginTop: 24, justifyContent: 'flex-end' }}>
            <button
              onClick={onCancel}
              style={{
                padding: '12px 24px', borderRadius: 10, fontSize: 13, fontWeight: 600,
                border: '1px solid #e8e4dc', background: '#fff', color: '#777',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              onClick={approveStep3}
              style={{
                padding: '12px 28px', borderRadius: 10, fontSize: 14, fontWeight: 700,
                border: 'none', background: '#16a34a', color: '#fff', cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: 8,
              }}
            >
              <CheckCircle size={16} />
              Approve Scope & Continue
            </button>
          </div>
        </div>
      )}

      {/* ═══════ STEP 4: PRICING ═══════ */}
      {step === 4 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#1a1a1a' }}>
              Review Pricing
            </div>
            <button
              onClick={() => goBack(3)}
              style={{
                display: 'flex', alignItems: 'center', gap: 4,
                background: 'none', border: 'none', fontSize: 12, fontWeight: 600,
                color: '#999', cursor: 'pointer',
              }}
            >
              <ArrowLeft size={14} /> Back to Scope
            </button>
          </div>
          <p style={{ fontSize: 13, color: '#777', marginBottom: 20 }}>
            Review auto-generated line items. Every number is editable. Adjust quantities and rates as needed.
          </p>

          {/* Line items table */}
          <div style={{
            background: '#fff', borderRadius: 12, border: '1px solid #e8e4dc',
            overflow: 'hidden',
          }}>
            {/* Header */}
            <div style={{
              display: 'grid', gridTemplateColumns: '3fr 1fr 1fr 1.2fr 32px',
              gap: 0, padding: '10px 16px',
              background: '#f5f3ef', borderBottom: '1px solid #e8e4dc',
              fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase',
              letterSpacing: 0.5,
            }}>
              <div>Description</div>
              <div style={{ textAlign: 'right' }}>Qty</div>
              <div style={{ textAlign: 'right' }}>Rate</div>
              <div style={{ textAlign: 'right' }}>Amount</div>
              <div />
            </div>

            {pricingLines.map(pl => (
              <div key={pl.id}>
                <div style={{
                  display: 'grid', gridTemplateColumns: '3fr 1fr 1fr 1.2fr 32px',
                  gap: 0, padding: '10px 16px', alignItems: 'center',
                  borderBottom: '1px solid #f0ede8', fontSize: 12,
                }}>
                  <div>
                    <input
                      value={pl.description}
                      onChange={e => updatePricingLine(pl.id, { description: e.target.value })}
                      style={{
                        border: 'none', background: 'transparent', fontSize: 12,
                        fontWeight: 600, width: '100%', padding: '2px 0', color: '#1a1a1a',
                      }}
                    />
                    <div style={{ fontSize: 10, color: '#b8960c', fontWeight: 500, marginTop: 2 }}>
                      {pl.formula}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <input
                      type="number"
                      value={pl.quantity}
                      onChange={e => updatePricingLine(pl.id, { quantity: parseFloat(e.target.value) || 0 })}
                      style={{
                        border: 'none', background: 'transparent', fontSize: 12,
                        textAlign: 'right', width: '100%', padding: '2px 0', fontWeight: 600,
                      }}
                    />
                    <div style={{ fontSize: 10, color: '#999' }}>{pl.unit}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
                      <span style={{ fontSize: 12, color: '#999' }}>$</span>
                      <input
                        type="number"
                        value={pl.rate}
                        onChange={e => updatePricingLine(pl.id, { rate: parseFloat(e.target.value) || 0 })}
                        style={{
                          border: 'none', background: 'transparent', fontSize: 12,
                          textAlign: 'right', width: 70, padding: '2px 0', fontWeight: 600,
                        }}
                      />
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', fontWeight: 700, fontSize: 13, color: '#1a1a1a' }}>
                    ${pl.amount.toFixed(2)}
                  </div>
                  <button
                    onClick={() => removePricingLine(pl.id)}
                    style={{
                      background: 'none', border: 'none', color: '#ccc',
                      cursor: 'pointer', padding: 2, display: 'flex', justifyContent: 'center',
                      transition: 'color 0.15s',
                    }}
                    onMouseEnter={e => (e.currentTarget.style.color = '#dc2626')}
                    onMouseLeave={e => (e.currentTarget.style.color = '#ccc')}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Add line item */}
          <button
            onClick={addPricingLine}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'center',
              padding: '10px 14px', borderRadius: 10, marginTop: 8, width: '100%',
              border: '1.5px dashed #d4d0c8', background: '#fff',
              fontSize: 12, fontWeight: 600, color: '#888', cursor: 'pointer',
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = '#16a34a'; e.currentTarget.style.color = '#16a34a'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = '#d4d0c8'; e.currentTarget.style.color = '#888'; }}
          >
            <Plus size={14} /> Add Line Item
          </button>

          {/* Subtotal */}
          <div style={{
            marginTop: 16, padding: '16px 20px', borderRadius: 12,
            background: '#fff', border: '1px solid #e8e4dc',
          }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              fontSize: 20, fontWeight: 800, color: '#1a1a1a',
            }}>
              <span>Subtotal</span>
              <span style={{ color: '#16a34a' }}>${subtotal.toFixed(2)}</span>
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 10, marginTop: 24, justifyContent: 'flex-end' }}>
            <button
              onClick={onCancel}
              style={{
                padding: '12px 24px', borderRadius: 10, fontSize: 13, fontWeight: 600,
                border: '1px solid #e8e4dc', background: '#fff', color: '#777',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              onClick={finalizeQuote}
              disabled={pricingLines.length === 0}
              style={{
                padding: '14px 32px', borderRadius: 10, fontSize: 15, fontWeight: 800,
                border: 'none', color: '#fff', cursor: 'pointer',
                background: pricingLines.length === 0 ? '#ccc' : '#16a34a',
                opacity: pricingLines.length === 0 ? 0.6 : 1,
                display: 'flex', alignItems: 'center', gap: 8,
                transition: 'all 0.15s',
              }}
            >
              <CheckCircle size={18} />
              Add to Quote
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
