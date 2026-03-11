'use client';
import React, { useState, useEffect } from 'react';
import { API } from '../../../lib/api';
import {
  Zap, ChevronRight, Check, X, RotateCcw, AlertTriangle,
  ArrowRight, Loader2, ClipboardList, DollarSign, Ruler,
  TrendingUp, FileText, Camera, Shield
} from 'lucide-react';

// ── Types ────────────────────────────────────────────────────

interface QuickQuoteResult {
  type: string;
  item_type: string;
  dimensions: { width: number; height: number; depth: number };
  material_grade: string;
  complexity: string;
  quantity: number;
  size_factor: number;
  tiers: {
    essential: { low: number; high: number; label: string };
    designer: { low: number; high: number; label: string };
    premium: { low: number; high: number; label: string };
  };
  disclaimer: string;
}

interface PhaseData {
  name: string;
  status: string;
  started_at?: string;
  approved_at?: string;
  rejected_at?: string;
  retried_at?: string;
  founder_notes?: string;
  rejection_reason?: string;
  data?: any;
}

interface PhaseStatus {
  has_pipeline: boolean;
  quote_id: string;
  quote_number: string;
  customer_name: string;
  current_phase: number;
  current_phase_name: string;
  phase_status: string;
  total_phases: number;
  progress_pct: number;
  phases: Record<string, PhaseData>;
}

// ── Phase Icons ──────────────────────────────────────────────

const PHASE_ICONS = [ClipboardList, Camera, Ruler, DollarSign, TrendingUp, FileText];
const PHASE_LABELS = ['Intake', 'Vision Analysis', 'Measurements', 'Pricing & Labor', 'Profit & Margin', 'Final PDF'];

// ── Quick Quote Panel ────────────────────────────────────────

const ITEM_TYPES = [
  { value: 'accent_chair', label: 'Accent Chair' },
  { value: 'wingback_chair', label: 'Wingback Chair' },
  { value: 'club_chair', label: 'Club Chair' },
  { value: 'dining_chair_seat', label: 'Dining Chair (Seat)' },
  { value: 'dining_chair_full', label: 'Dining Chair (Full)' },
  { value: 'ottoman', label: 'Ottoman' },
  { value: 'loveseat', label: 'Loveseat' },
  { value: 'sofa_2cushion', label: 'Sofa (2 Cushion)' },
  { value: 'sofa_3cushion', label: 'Sofa (3 Cushion)' },
  { value: 'sectional_per_section', label: 'Sectional (per section)' },
  { value: 'bench', label: 'Bench' },
  { value: 'banquette', label: 'Banquette' },
  { value: 'headboard', label: 'Headboard' },
  { value: 'drapery_panel', label: 'Drapery Panel' },
  { value: 'roman_shade', label: 'Roman Shade' },
  { value: 'roller_shade', label: 'Roller Shade' },
  { value: 'valance', label: 'Valance' },
  { value: 'cornice', label: 'Cornice' },
];

export function QuickQuotePanel({ onPromote }: { onPromote?: (data: QuickQuoteResult) => void }) {
  const [itemType, setItemType] = useState('accent_chair');
  const [width, setWidth] = useState('');
  const [height, setHeight] = useState('');
  const [depth, setDepth] = useState('');
  const [grade, setGrade] = useState('B');
  const [complexity, setComplexity] = useState('moderate');
  const [quantity, setQuantity] = useState('1');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QuickQuoteResult | null>(null);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const res = await fetch(API + '/quotes/quick', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          item_type: itemType,
          width: parseFloat(width) || 0,
          height: parseFloat(height) || 0,
          depth: parseFloat(depth) || 0,
          material_grade: grade,
          complexity,
          quantity: parseInt(quantity) || 1,
          notes,
        }),
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      console.error('Quick quote error:', e);
    }
    setLoading(false);
  };

  const inputStyle: React.CSSProperties = {
    padding: '8px 12px', border: '1px solid #ece8e0', borderRadius: 10,
    fontSize: 12, background: '#fff', outline: 'none', width: '100%',
  };
  const labelStyle: React.CSSProperties = { fontSize: 11, fontWeight: 600, color: '#555', marginBottom: 4, display: 'block' };

  return (
    <div className="empire-card" style={{ padding: 20 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }} className="flex items-center gap-2">
        <Zap size={16} className="text-[#b8960c]" /> Quick Quote Calculator
      </h3>

      {!result ? (
        <>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <div>
              <label style={labelStyle}>Item Type</label>
              <select value={itemType} onChange={e => setItemType(e.target.value)}
                style={{ ...inputStyle, cursor: 'pointer' }}>
                {ITEM_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Complexity</label>
              <select value={complexity} onChange={e => setComplexity(e.target.value)}
                style={{ ...inputStyle, cursor: 'pointer' }}>
                <option value="simple">Simple</option>
                <option value="moderate">Moderate</option>
                <option value="complex">Complex</option>
                <option value="luxury">Luxury</option>
              </select>
            </div>
            <div>
              <label style={labelStyle}>Fabric Grade</label>
              <select value={grade} onChange={e => setGrade(e.target.value)}
                style={{ ...inputStyle, cursor: 'pointer' }}>
                <option value="A">A — Quality Basics ($15/yd)</option>
                <option value="B">B — Designer ($35/yd)</option>
                <option value="C">C — Luxury Premium ($65/yd)</option>
                <option value="D">D — Ultra Luxury ($120/yd)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-4 gap-3 mb-3">
            <div>
              <label style={labelStyle}>Width (in)</label>
              <input type="number" value={width} onChange={e => setWidth(e.target.value)}
                placeholder="36" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Height (in)</label>
              <input type="number" value={height} onChange={e => setHeight(e.target.value)}
                placeholder="34" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Depth (in)</label>
              <input type="number" value={depth} onChange={e => setDepth(e.target.value)}
                placeholder="30" style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>Quantity</label>
              <input type="number" value={quantity} onChange={e => setQuantity(e.target.value)}
                min="1" placeholder="1" style={inputStyle} />
            </div>
          </div>

          <div className="mb-3">
            <label style={labelStyle}>Notes (optional)</label>
            <input value={notes} onChange={e => setNotes(e.target.value)}
              placeholder="e.g., tufted back, nailhead trim..." style={inputStyle} />
          </div>

          <button onClick={handleSubmit} disabled={loading}
            className="flex items-center gap-2 cursor-pointer font-bold transition-all hover:bg-[#a08509]"
            style={{ height: 40, padding: '0 20px', fontSize: 13, borderRadius: 10, background: '#b8960c', color: '#fff', border: 'none', opacity: loading ? 0.7 : 1 }}>
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
            Get Ballpark
          </button>
        </>
      ) : (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <div style={{ fontSize: 12, color: '#777' }}>{result.item_type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())} &middot; {result.complexity} &middot; Grade {result.material_grade}</div>
              <div style={{ fontSize: 11, color: '#aaa' }}>{result.dimensions.width}&quot;W x {result.dimensions.height}&quot;H{result.dimensions.depth ? ` x ${result.dimensions.depth}"D` : ''} &middot; Qty {result.quantity}</div>
            </div>
            <button onClick={() => setResult(null)}
              className="cursor-pointer transition-all hover:bg-[#f5f3ef]"
              style={{ padding: '6px 12px', fontSize: 11, borderRadius: 8, border: '1px solid #ece8e0', background: '#fff', color: '#555', fontWeight: 600 }}>
              New Quote
            </button>
          </div>

          <div className="grid grid-cols-3 gap-3 mb-4">
            {(['essential', 'designer', 'premium'] as const).map((tier, i) => {
              const t = result.tiers[tier];
              const colors = [
                { bg: '#f0fdf4', border: '#bbf7d0', text: '#16a34a' },
                { bg: '#fdf8eb', border: '#f5ecd0', text: '#b8960c' },
                { bg: '#faf5ff', border: '#e9d5ff', text: '#7c3aed' },
              ][i];
              return (
                <div key={tier} style={{ padding: 14, borderRadius: 12, background: colors.bg, border: `1.5px solid ${colors.border}` }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: colors.text, textTransform: 'uppercase', marginBottom: 6 }}>{t.label.split(' (')[0]}</div>
                  <div style={{ fontSize: 20, fontWeight: 800, color: '#1a1a1a' }}>
                    ${t.low.toLocaleString()}–${t.high.toLocaleString()}
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ padding: 10, borderRadius: 8, background: '#fef3c7', border: '1px solid #fcd34d', fontSize: 11, color: '#92400e', marginBottom: 12 }}>
            <AlertTriangle size={12} style={{ display: 'inline', marginRight: 4 }} />
            {result.disclaimer}
          </div>

          {onPromote && (
            <button onClick={() => onPromote(result)}
              className="flex items-center gap-2 cursor-pointer font-bold transition-all hover:bg-[#15803d]"
              style={{ height: 36, padding: '0 16px', fontSize: 12, borderRadius: 10, background: '#16a34a', color: '#fff', border: 'none' }}>
              <ArrowRight size={14} /> Promote to Full Analysis
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ── Phase Pipeline Dashboard ─────────────────────────────────

export function QuotePhasePipeline({ quoteId, onRefresh }: { quoteId: string; onRefresh?: () => void }) {
  const [status, setStatus] = useState<PhaseStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [expandedPhase, setExpandedPhase] = useState<number | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [approveNotes, setApproveNotes] = useState('');

  const fetchStatus = async () => {
    try {
      const res = await fetch(API + `/quotes/phase/status/${quoteId}`);
      const data = await res.json();
      setStatus(data);
    } catch (e) {
      console.error('Phase status error:', e);
    }
    setLoading(false);
  };

  useEffect(() => { fetchStatus(); }, [quoteId]);

  const initPipeline = async () => {
    setActing(true);
    try {
      await fetch(API + `/quotes/phase/init/${quoteId}`, { method: 'POST' });
      await fetchStatus();
    } catch (e) { console.error(e); }
    setActing(false);
  };

  const advancePhase = async () => {
    setActing(true);
    try {
      await fetch(API + `/quotes/phase/advance/${quoteId}`, { method: 'POST' });
      await fetchStatus();
    } catch (e) { console.error(e); }
    setActing(false);
  };

  const approvePhase = async () => {
    setActing(true);
    try {
      await fetch(API + `/quotes/phase/approve/${quoteId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes: approveNotes }),
      });
      setApproveNotes('');
      await fetchStatus();
    } catch (e) { console.error(e); }
    setActing(false);
  };

  const rejectPhase = async () => {
    setActing(true);
    try {
      await fetch(API + `/quotes/phase/reject/${quoteId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: rejectReason }),
      });
      setRejectReason('');
      await fetchStatus();
    } catch (e) { console.error(e); }
    setActing(false);
  };

  const retryPhase = async () => {
    setActing(true);
    try {
      await fetch(API + `/quotes/phase/retry/${quoteId}`, { method: 'POST' });
      await fetchStatus();
    } catch (e) { console.error(e); }
    setActing(false);
  };

  if (loading) return <div className="flex items-center justify-center py-8"><Loader2 size={20} className="text-[#b8960c] animate-spin" /></div>;

  // No pipeline yet — offer to initialize
  if (!status?.has_pipeline) {
    return (
      <div className="empire-card" style={{ padding: 20, textAlign: 'center' }}>
        <Shield size={32} className="text-[#b8960c] mx-auto mb-3" />
        <h4 style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 6 }}>Multi-Phase Review Pipeline</h4>
        <p style={{ fontSize: 12, color: '#777', marginBottom: 16, maxWidth: 400, margin: '0 auto 16px' }}>
          Enable 6-phase review workflow with founder approval gates at each stage.
        </p>
        <button onClick={initPipeline} disabled={acting}
          className="inline-flex items-center gap-2 cursor-pointer font-bold transition-all hover:bg-[#a08509]"
          style={{ height: 40, padding: '0 20px', fontSize: 13, borderRadius: 10, background: '#b8960c', color: '#fff', border: 'none' }}>
          {acting ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />}
          Start Phase Pipeline
        </button>
      </div>
    );
  }

  const current = status.current_phase;
  const phaseStatus = status.phase_status;

  return (
    <div className="empire-card" style={{ padding: 20 }}>
      <div className="flex items-center justify-between mb-4">
        <h4 style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }} className="flex items-center gap-2">
          <Shield size={16} className="text-[#b8960c]" /> Quote Pipeline
          <span style={{ fontSize: 11, fontWeight: 500, color: '#999' }}>{status.quote_number}</span>
        </h4>
        <div style={{ fontSize: 11, color: '#777' }}>
          Phase {current}/5 &middot; {status.progress_pct}%
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ height: 6, background: '#ece8e0', borderRadius: 3, marginBottom: 16, overflow: 'hidden' }}>
        <div style={{
          height: '100%',
          width: `${status.progress_pct}%`,
          background: phaseStatus === 'revision' ? '#f59e0b' : '#16a34a',
          borderRadius: 3,
          transition: 'width 0.3s ease',
        }} />
      </div>

      {/* Phase steps */}
      <div className="flex items-center gap-1 mb-5" style={{ overflowX: 'auto' }}>
        {[0, 1, 2, 3, 4, 5].map((phase) => {
          const Icon = PHASE_ICONS[phase];
          const phaseData = status.phases[String(phase)];
          const isComplete = phaseData?.status === 'approved';
          const isCurrent = phase === current;
          const isReview = isCurrent && phaseStatus === 'review';
          const isRevision = isCurrent && phaseStatus === 'revision';
          const isFuture = phase > current;

          let bg = '#f5f3ef';
          let border = '#ece8e0';
          let color = '#aaa';
          if (isComplete && !isCurrent) { bg = '#f0fdf4'; border = '#bbf7d0'; color = '#16a34a'; }
          if (isReview) { bg = '#fdf8eb'; border = '#f5ecd0'; color = '#b8960c'; }
          if (isRevision) { bg = '#fef3c7'; border = '#fcd34d'; color = '#d97706'; }
          if (isCurrent && phaseStatus === 'approved') { bg = '#eff6ff'; border = '#bfdbfe'; color = '#2563eb'; }

          return (
            <React.Fragment key={phase}>
              <button
                onClick={() => setExpandedPhase(expandedPhase === phase ? null : phase)}
                className="flex flex-col items-center gap-1 cursor-pointer transition-all"
                style={{
                  padding: '8px 10px', borderRadius: 10, border: `1.5px solid ${border}`,
                  background: bg, minWidth: 72, flex: '1 0 auto',
                }}
              >
                <div className="flex items-center gap-1">
                  {isComplete && !isCurrent ? <Check size={12} style={{ color }} /> : <Icon size={14} style={{ color }} />}
                </div>
                <div style={{ fontSize: 9, fontWeight: 600, color, textAlign: 'center', lineHeight: 1.2 }}>
                  {PHASE_LABELS[phase]}
                </div>
                {isReview && <div style={{ fontSize: 8, fontWeight: 700, color: '#b8960c', background: '#fef3c7', padding: '1px 6px', borderRadius: 4 }}>REVIEW</div>}
                {isRevision && <div style={{ fontSize: 8, fontWeight: 700, color: '#d97706', background: '#fef3c7', padding: '1px 6px', borderRadius: 4 }}>REVISION</div>}
              </button>
              {phase < 5 && <ChevronRight size={12} style={{ color: '#ddd', flexShrink: 0 }} />}
            </React.Fragment>
          );
        })}
      </div>

      {/* Expanded phase detail */}
      {expandedPhase !== null && status.phases[String(expandedPhase)] && (
        <div style={{ padding: 14, borderRadius: 10, background: '#faf9f7', border: '1px solid #ece8e0', marginBottom: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#1a1a1a', marginBottom: 8 }}>
            Phase {expandedPhase}: {PHASE_LABELS[expandedPhase]}
          </div>
          {status.phases[String(expandedPhase)]?.data?.review_checklist && (
            <div className="space-y-1">
              {(status.phases[String(expandedPhase)].data.review_checklist as string[]).map((item: string, i: number) => (
                <div key={i} style={{ fontSize: 11, color: '#555', padding: '3px 0' }} className="flex items-start gap-2">
                  <ClipboardList size={10} style={{ marginTop: 2, flexShrink: 0 }} className="text-[#b8960c]" />
                  {item}
                </div>
              ))}
            </div>
          )}
          {status.phases[String(expandedPhase)]?.founder_notes && (
            <div style={{ marginTop: 8, padding: 8, borderRadius: 6, background: '#f0fdf4', fontSize: 11, color: '#166534' }}>
              <strong>Founder notes:</strong> {status.phases[String(expandedPhase)].founder_notes}
            </div>
          )}
          {status.phases[String(expandedPhase)]?.rejection_reason && (
            <div style={{ marginTop: 8, padding: 8, borderRadius: 6, background: '#fef2f2', fontSize: 11, color: '#991b1b' }}>
              <strong>Rejection:</strong> {status.phases[String(expandedPhase)].rejection_reason}
            </div>
          )}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* Advance button — only when current phase is approved and not at final */}
        {phaseStatus === 'approved' && current < 5 && (
          <button onClick={advancePhase} disabled={acting}
            className="flex items-center gap-1.5 cursor-pointer font-bold transition-all hover:bg-[#15803d]"
            style={{ height: 36, padding: '0 14px', fontSize: 12, borderRadius: 10, background: '#16a34a', color: '#fff', border: 'none' }}>
            {acting ? <Loader2 size={12} className="animate-spin" /> : <ArrowRight size={14} />}
            Advance to Phase {current + 1}
          </button>
        )}

        {/* Approve/Reject — only when in review */}
        {phaseStatus === 'review' && (
          <>
            <div className="flex items-center gap-1">
              <input value={approveNotes} onChange={e => setApproveNotes(e.target.value)}
                placeholder="Notes (optional)"
                style={{ padding: '7px 10px', border: '1px solid #ece8e0', borderRadius: 8, fontSize: 11, width: 160 }} />
              <button onClick={approvePhase} disabled={acting}
                className="flex items-center gap-1 cursor-pointer font-bold transition-all hover:bg-[#15803d]"
                style={{ height: 34, padding: '0 12px', fontSize: 11, borderRadius: 8, background: '#16a34a', color: '#fff', border: 'none' }}>
                {acting ? <Loader2 size={12} className="animate-spin" /> : <Check size={14} />}
                Approve
              </button>
            </div>
            <div className="flex items-center gap-1">
              <input value={rejectReason} onChange={e => setRejectReason(e.target.value)}
                placeholder="Reason..."
                style={{ padding: '7px 10px', border: '1px solid #ece8e0', borderRadius: 8, fontSize: 11, width: 140 }} />
              <button onClick={rejectPhase} disabled={acting}
                className="flex items-center gap-1 cursor-pointer font-bold transition-all hover:bg-[#dc2626]"
                style={{ height: 34, padding: '0 12px', fontSize: 11, borderRadius: 8, background: '#ef4444', color: '#fff', border: 'none' }}>
                <X size={14} /> Reject
              </button>
            </div>
          </>
        )}

        {/* Retry — only when in revision */}
        {phaseStatus === 'revision' && (
          <button onClick={retryPhase} disabled={acting}
            className="flex items-center gap-1.5 cursor-pointer font-bold transition-all hover:bg-[#d97706]"
            style={{ height: 36, padding: '0 14px', fontSize: 12, borderRadius: 10, background: '#f59e0b', color: '#fff', border: 'none' }}>
            {acting ? <Loader2 size={12} className="animate-spin" /> : <RotateCcw size={14} />}
            Retry Phase
          </button>
        )}

        {/* Final phase approved — ready to generate PDF */}
        {current === 5 && phaseStatus === 'approved' && (
          <div style={{ padding: '8px 14px', borderRadius: 8, background: '#f0fdf4', border: '1px solid #bbf7d0', fontSize: 12, color: '#16a34a', fontWeight: 700 }}
            className="flex items-center gap-2">
            <Check size={14} /> Pipeline Complete — Ready to Generate PDF
          </div>
        )}
      </div>
    </div>
  );
}

export default QuotePhasePipeline;
