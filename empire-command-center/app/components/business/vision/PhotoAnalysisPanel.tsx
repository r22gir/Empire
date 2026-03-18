'use client';

import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  Camera, Upload, Loader2, Ruler, Armchair, Paintbrush, ClipboardList,
  X, CheckCircle, AlertTriangle, Sparkles, TriangleAlert, Info, Box, Video,
  ArrowRight, Plus, ImageIcon, Trash2, Eye, Printer, Share2, FileDown, FileText, Edit3
} from 'lucide-react';
import { API } from '../../../lib/api';
import MeasurementDiagram from '../quotes/MeasurementDiagram';

/* ═══════════════════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════════════════ */

type AnalysisMode = 'measure' | 'upholstery' | 'mockup' | 'outline';

interface PhotoEntry {
  id: string;
  imageData: string;
  name: string;
  addedAt: Date;
  results: Record<string, any>;  // mode -> result
}

interface PhotoAnalysisPanelProps {
  onAnalysisComplete?: (type: string, data: any) => void;
  onSaveQuote?: (quoteData: any) => void;
  initialImage?: string;
  compact?: boolean;
  customerName?: string;
  customerEmail?: string;
  jobId?: string;
}

interface MeasureResult {
  width_inches: number;
  height_inches: number;
  confidence: number;
  window_type: string;
  reference_objects_used: string[];
  scale_method: string;
  notes: string;
  treatment_suggestions: string[];
}

interface UpholsteryResult {
  furniture_type: string;
  style: string;
  estimated_dimensions: any;
  cushion_count: number;
  fabric_yards_plain: number;
  fabric_yards_patterned: number;
  has_welting: boolean;
  has_tufting: boolean;
  has_channeling: boolean;
  has_skirt: boolean;
  has_nailhead: boolean;
  suggested_labor_type: string;
  estimated_labor_cost_low: number;
  estimated_labor_cost_high: number;
  new_foam_recommended: boolean;
  confidence: number;
  questions: string[];
  all_furniture: any[];
  renovation_proposals: any[];
  generated_image: string;
}

interface MockupProposal {
  tier: string;
  treatment_type: string;
  style: string;
  fabric: string;
  lining: string;
  hardware: string;
  extras: string[];
  price_range_low: number;
  price_range_high: number;
  visual_description: string;
  design_rationale: string;
}

interface MockupResult {
  room_assessment: string | Record<string, any>;
  window_info: any;
  proposals: MockupProposal[];
  generated_images: { tier: string; url: string }[];
  general_recommendations: string | string[];
  confidence: number;
  notes: string;
}

interface OutlineResult {
  window_opening: any;
  wall_dimensions: any;
  clearances: any;
  obstructions: string[];
  existing_treatments: string;
  mounting_recommendations: string[];
  outline_description: string;
  reference_objects_used: string[];
  confidence: number;
  notes: string;
}

/* ═══════════════════════════════════════════════════════════
   Constants
   ═══════════════════════════════════════════════════════════ */

const MODES: { key: AnalysisMode; label: string; icon: React.ReactNode; color: string; desc: string }[] = [
  { key: 'measure', label: 'Measure', icon: <Ruler size={15} />, color: '#2563eb', desc: 'Window measurement analysis' },
  { key: 'upholstery', label: 'Upholstery', icon: <Armchair size={15} />, color: '#7c3aed', desc: 'Furniture reupholstery estimate' },
  { key: 'mockup', label: 'Design Mockup', icon: <Paintbrush size={15} />, color: '#b8960c', desc: '3-tier design proposals with AI images' },
  { key: 'outline', label: 'Install Plan', icon: <ClipboardList size={15} />, color: '#16a34a', desc: 'Installation blueprint — mounting, hardware, clearances, obstructions & installer checklist' },
];

const TIER_COLORS: Record<string, { bg: string; border: string; accent: string }> = {
  'Elegant Essential': { bg: '#f0fdf4', border: '#bbf7d0', accent: '#16a34a' },
  "Designer's Choice": { bg: '#eff6ff', border: '#bfdbfe', accent: '#2563eb' },
  'Ultimate Luxury': { bg: '#fdf4ff', border: '#e9d5ff', accent: '#7c3aed' },
};

const IMAGE_BASE = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
  ? 'https://api.empirebox.store'
  : 'http://localhost:8000';

const DESIGN_STYLES: { key: string; label: string; icon: string; desc: string }[] = [
  { key: 'modern', label: 'Modern', icon: '◻', desc: 'Clean lines, minimal' },
  { key: 'traditional', label: 'Traditional', icon: '⚜', desc: 'Classic, elegant' },
  { key: 'farmhouse', label: 'Farmhouse', icon: '🏡', desc: 'Rustic, cozy' },
  { key: 'contemporary', label: 'Contemporary', icon: '◈', desc: 'Current trends' },
  { key: 'coastal', label: 'Coastal', icon: '🌊', desc: 'Light, breezy' },
  { key: 'industrial', label: 'Industrial', icon: '⚙', desc: 'Raw, urban' },
  { key: 'bohemian', label: 'Bohemian', icon: '✦', desc: 'Eclectic, layered' },
  { key: 'transitional', label: 'Transitional', icon: '◐', desc: 'Traditional + modern' },
  { key: 'minimalist', label: 'Minimalist', icon: '○', desc: 'Less is more' },
  { key: 'luxe', label: 'Luxury', icon: '♛', desc: 'Premium, opulent' },
  { key: 'mid-century', label: 'Mid-Century', icon: '◇', desc: '50s-60s retro' },
  { key: 'scandinavian', label: 'Scandinavian', icon: '△', desc: 'Functional, light' },
];

type MeasureInputMethod = 'photo' | '3dscan' | 'manual';

type ManualItemType = 'window' | 'sofa' | 'chair' | 'cushion' | 'pillow' | 'cornice' | 'valance' | 'roman_shade' | 'other';

const MANUAL_ITEM_TYPES: { key: ManualItemType; label: string; icon: string }[] = [
  { key: 'window', label: 'Window', icon: '🪟' },
  { key: 'sofa', label: 'Sofa', icon: '🛋' },
  { key: 'chair', label: 'Chair', icon: '💺' },
  { key: 'cushion', label: 'Cushion', icon: '🛏' },
  { key: 'pillow', label: 'Pillow', icon: '🛌' },
  { key: 'cornice', label: 'Cornice', icon: '📐' },
  { key: 'valance', label: 'Valance', icon: '🎪' },
  { key: 'roman_shade', label: 'Roman Shade', icon: '🪟' },
  { key: 'other', label: 'Other', icon: '📏' },
];

/* ═══════════════════════════════════════════════════════════
   Helpers
   ═══════════════════════════════════════════════════════════ */

function ConfidenceBar({ value, color = '#b8960c' }: { value: number; color?: string }) {
  const pct = Math.round(value * 100);
  const label = pct >= 90 ? 'Very High' : pct >= 75 ? 'High' : pct >= 60 ? 'Moderate' : pct >= 40 ? 'Low' : 'Very Low';
  const barColor = pct >= 75 ? '#16a34a' : pct >= 50 ? color : pct >= 30 ? '#d97706' : '#dc2626';
  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <div style={{ flex: 1, height: 8, borderRadius: 4, background: '#ece8e0' }}>
          <div style={{ width: `${pct}%`, height: '100%', borderRadius: 4, background: barColor, transition: 'width 0.6s ease' }} />
        </div>
        <span style={{ fontSize: 12, fontWeight: 700, color: barColor, minWidth: 42, textAlign: 'right' }}>{pct}%</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: barColor }}>{label} Confidence</span>
        {pct < 60 && (
          <span style={{ fontSize: 10, color: '#d97706', fontWeight: 500 }}>Consider retaking photo with better lighting or reference objects</span>
        )}
      </div>
    </div>
  );
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return <div className="section-label" style={{ marginBottom: 8, marginTop: 16 }}>{children}</div>;
}

function MetricBox({ label, value, color = '#1a1a1a', sub }: { label: string; value: string; color?: string; sub?: string }) {
  return (
    <div style={{ padding: '12px 14px', borderRadius: 12, background: '#faf9f7', border: '1px solid #ece8e0', flex: 1, minWidth: 0 }}>
      <div style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, color }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function DetailCheck({ label, checked }: { label: string; checked: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: checked ? '#1a1a1a' : '#bbb' }}>
      <CheckCircle size={14} style={{ color: checked ? '#16a34a' : '#ddd' }} />
      <span style={{ fontWeight: checked ? 600 : 400 }}>{label}</span>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Dimension Drawing Overlay
   ═══════════════════════════════════════════════════════════ */

function DimensionDrawing({ imageData, width, height, windowType }: {
  imageData: string; width: number; height: number; windowType: string;
}) {
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = overlayCanvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const img = new Image();
    img.onload = () => {
      const maxW = container.clientWidth || 600;
      const scale = Math.min(maxW / img.width, 400 / img.height, 1);
      const dw = img.width * scale;
      const dh = img.height * scale;
      canvas.width = dw;
      canvas.height = dh;

      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      // Draw image
      ctx.drawImage(img, 0, 0, dw, dh);

      // Semi-transparent overlay
      ctx.fillStyle = 'rgba(0,0,0,0.15)';
      ctx.fillRect(0, 0, dw, dh);

      // Calculate window region (centered, ~60% of image)
      const margin = 0.18;
      const wx = dw * margin;
      const wy = dh * margin;
      const ww = dw * (1 - 2 * margin);
      const wh = dh * (1 - 2 * margin);

      // Clear window region (brighten it)
      ctx.clearRect(wx, wy, ww, wh);
      ctx.drawImage(img, wx / scale, wy / scale, ww / scale, wh / scale, wx, wy, ww, wh);

      // Window frame highlight
      ctx.strokeStyle = '#2563eb';
      ctx.lineWidth = 2.5;
      ctx.setLineDash([]);
      ctx.strokeRect(wx, wy, ww, wh);

      // Corner brackets
      const bLen = 14;
      ctx.lineWidth = 3;
      ctx.strokeStyle = '#2563eb';
      // Top-left
      ctx.beginPath(); ctx.moveTo(wx, wy + bLen); ctx.lineTo(wx, wy); ctx.lineTo(wx + bLen, wy); ctx.stroke();
      // Top-right
      ctx.beginPath(); ctx.moveTo(wx + ww - bLen, wy); ctx.lineTo(wx + ww, wy); ctx.lineTo(wx + ww, wy + bLen); ctx.stroke();
      // Bottom-left
      ctx.beginPath(); ctx.moveTo(wx, wy + wh - bLen); ctx.lineTo(wx, wy + wh); ctx.lineTo(wx + bLen, wy + wh); ctx.stroke();
      // Bottom-right
      ctx.beginPath(); ctx.moveTo(wx + ww - bLen, wy + wh); ctx.lineTo(wx + ww, wy + wh); ctx.lineTo(wx + ww, wy + wh - bLen); ctx.stroke();

      // Width dimension line (below window)
      const dimY = wy + wh + 20;
      ctx.strokeStyle = '#2563eb';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([]);
      // Horizontal line
      ctx.beginPath(); ctx.moveTo(wx, dimY); ctx.lineTo(wx + ww, dimY); ctx.stroke();
      // End ticks
      ctx.beginPath(); ctx.moveTo(wx, dimY - 6); ctx.lineTo(wx, dimY + 6); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(wx + ww, dimY - 6); ctx.lineTo(wx + ww, dimY + 6); ctx.stroke();
      // Extension lines (dashed)
      ctx.setLineDash([3, 3]);
      ctx.strokeStyle = 'rgba(37,99,235,0.4)';
      ctx.beginPath(); ctx.moveTo(wx, wy + wh); ctx.lineTo(wx, dimY + 6); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(wx + ww, wy + wh); ctx.lineTo(wx + ww, dimY + 6); ctx.stroke();
      ctx.setLineDash([]);

      // Width label
      const widthLabel = `${width}"`;
      ctx.font = 'bold 14px system-ui, sans-serif';
      ctx.textAlign = 'center';
      const tw = ctx.measureText(widthLabel).width;
      ctx.fillStyle = '#2563eb';
      ctx.beginPath();
      const rx = wx + ww / 2 - tw / 2 - 8;
      const ry = dimY - 10;
      const rw = tw + 16;
      const rh = 20;
      ctx.roundRect(rx, ry, rw, rh, 4);
      ctx.fill();
      ctx.fillStyle = '#fff';
      ctx.fillText(widthLabel, wx + ww / 2, dimY + 4);

      // Height dimension line (right of window)
      const dimX = wx + ww + 20;
      ctx.strokeStyle = '#2563eb';
      ctx.lineWidth = 1.5;
      // Vertical line
      ctx.beginPath(); ctx.moveTo(dimX, wy); ctx.lineTo(dimX, wy + wh); ctx.stroke();
      // End ticks
      ctx.beginPath(); ctx.moveTo(dimX - 6, wy); ctx.lineTo(dimX + 6, wy); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(dimX - 6, wy + wh); ctx.lineTo(dimX + 6, wy + wh); ctx.stroke();
      // Extension lines (dashed)
      ctx.setLineDash([3, 3]);
      ctx.strokeStyle = 'rgba(37,99,235,0.4)';
      ctx.beginPath(); ctx.moveTo(wx + ww, wy); ctx.lineTo(dimX + 6, wy); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(wx + ww, wy + wh); ctx.lineTo(dimX + 6, wy + wh); ctx.stroke();
      ctx.setLineDash([]);

      // Height label (rotated)
      const heightLabel = `${height}"`;
      ctx.save();
      ctx.translate(dimX + 4, wy + wh / 2);
      ctx.rotate(-Math.PI / 2);
      const th = ctx.measureText(heightLabel).width;
      ctx.fillStyle = '#2563eb';
      ctx.beginPath();
      ctx.roundRect(-th / 2 - 8, -10, th + 16, 20, 4);
      ctx.fill();
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 14px system-ui, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(heightLabel, 0, 4);
      ctx.restore();

      // Window type label (top-left)
      ctx.font = 'bold 11px system-ui, sans-serif';
      ctx.textAlign = 'left';
      const typeLabel = windowType || 'Window';
      const typeTw = ctx.measureText(typeLabel).width;
      ctx.fillStyle = 'rgba(37,99,235,0.9)';
      ctx.beginPath();
      ctx.roundRect(wx + 6, wy + 6, typeTw + 14, 22, 4);
      ctx.fill();
      ctx.fillStyle = '#fff';
      ctx.fillText(typeLabel, wx + 13, wy + 21);
    };
    img.src = imageData;
  }, [imageData, width, height, windowType]);

  return (
    <div ref={containerRef} style={{ borderRadius: 12, overflow: 'hidden', border: '2px solid #2563eb', marginBottom: 14 }}>
      <canvas ref={overlayCanvasRef} style={{ width: '100%', display: 'block' }} />
      <div style={{ padding: '8px 12px', background: '#eff6ff', borderTop: '1px solid #bfdbfe', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: '#2563eb' }}>AI Dimension Drawing</span>
        <span style={{ fontSize: 10, color: '#1e40af' }}>{width}" W x {height}" H</span>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Manual Measure Entry
   ═══════════════════════════════════════════════════════════ */

function ManualMeasureEntry({ onAddToQuote }: { onAddToQuote?: (item: any) => void }) {
  const [itemType, setItemType] = useState<ManualItemType>('window');
  const [m, setM] = useState({ width_inches: 0, height_inches: 0, depth_inches: 0, sill_depth: 0, stack_space: 0 });
  const [opts, setOpts] = useState({ mount_type: 'inside', treatment: '', lining: '', notes: '', fabric: '' });
  const [items, setItems] = useState<any[]>([]);

  const isWindow = ['window', 'cornice', 'valance', 'roman_shade'].includes(itemType);
  const isFurniture = ['sofa', 'chair'].includes(itemType);
  const isCushion = ['cushion', 'pillow'].includes(itemType);

  const updateM = (key: string, val: string) => {
    setM(prev => ({ ...prev, [key]: parseFloat(val) || 0 }));
  };

  const currentItem = {
    type: itemType,
    subtype: opts.treatment || undefined,
    measurements: { width_inches: m.width_inches, height_inches: m.height_inches, depth_inches: m.depth_inches || undefined, sill_depth: m.sill_depth || undefined, stack_space: m.stack_space || undefined },
    treatment: opts.treatment || itemType,
    mount_type: opts.mount_type || undefined,
    lining: opts.lining || undefined,
    description: opts.notes || undefined,
  };

  const addItem = () => {
    if (!m.width_inches && !m.height_inches) return;
    const newItem = { ...currentItem, id: Date.now() };
    setItems(prev => [...prev, newItem]);
    if (onAddToQuote) onAddToQuote(newItem);
    setM({ width_inches: 0, height_inches: 0, depth_inches: 0, sill_depth: 0, stack_space: 0 });
    setOpts({ mount_type: 'inside', treatment: '', lining: '', notes: '', fabric: '' });
  };

  return (
    <div style={{ marginBottom: 16 }}>
      {/* Item type selector */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 8 }}>
          What are you measuring?
        </label>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {MANUAL_ITEM_TYPES.map(t => (
            <button key={t.key} onClick={() => setItemType(t.key)}
              className="cursor-pointer transition-all"
              style={{
                padding: '8px 14px', borderRadius: 10, fontSize: 12, fontWeight: 600,
                border: `1.5px solid ${itemType === t.key ? '#b8960c' : '#ece8e0'}`,
                background: itemType === t.key ? '#fdf8e8' : '#faf9f7',
                color: itemType === t.key ? '#b8960c' : '#777',
                minHeight: 44,
              }}>
              {t.icon} {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Measurement form + live diagram — side by side on desktop */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 16 }}>
        {/* Left: form fields */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <label style={{ fontSize: 12 }}>
              <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Width (in)</span>
              <input type="number" value={m.width_inches || ''} onChange={e => updateM('width_inches', e.target.value)}
                placeholder="e.g. 72" style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 14, marginTop: 4, background: '#faf9f7', minHeight: 44 }} />
            </label>
            <label style={{ fontSize: 12 }}>
              <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Height (in)</span>
              <input type="number" value={m.height_inches || ''} onChange={e => updateM('height_inches', e.target.value)}
                placeholder="e.g. 96" style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 14, marginTop: 4, background: '#faf9f7', minHeight: 44 }} />
            </label>
          </div>

          {(isFurniture || isCushion) && (
            <label style={{ fontSize: 12 }}>
              <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Depth (in)</span>
              <input type="number" value={m.depth_inches || ''} onChange={e => updateM('depth_inches', e.target.value)}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 14, marginTop: 4, background: '#faf9f7', minHeight: 44 }} />
            </label>
          )}

          {isWindow && (
            <>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <label style={{ fontSize: 12 }}>
                  <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Sill Depth (in)</span>
                  <input type="number" value={m.sill_depth || ''} onChange={e => updateM('sill_depth', e.target.value)}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 14, marginTop: 4, background: '#faf9f7', minHeight: 44 }} />
                </label>
                <label style={{ fontSize: 12 }}>
                  <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Stack Space (in/side)</span>
                  <input type="number" value={m.stack_space || ''} onChange={e => updateM('stack_space', e.target.value)}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 14, marginTop: 4, background: '#faf9f7', minHeight: 44 }} />
                </label>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <label style={{ fontSize: 12 }}>
                  <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Mount Type</span>
                  <select value={opts.mount_type} onChange={e => setOpts(p => ({...p, mount_type: e.target.value}))}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 13, marginTop: 4, background: '#faf9f7', minHeight: 44 }}>
                    <option value="inside">Inside Mount</option>
                    <option value="outside">Outside Mount</option>
                  </select>
                </label>
                <label style={{ fontSize: 12 }}>
                  <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Treatment</span>
                  <select value={opts.treatment} onChange={e => setOpts(p => ({...p, treatment: e.target.value}))}
                    style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 13, marginTop: 4, background: '#faf9f7', minHeight: 44 }}>
                    <option value="">--</option>
                    <option value="pinch_pleat">Pinch Pleat</option>
                    <option value="rod_pocket">Rod Pocket</option>
                    <option value="grommet">Grommet</option>
                    <option value="tab_top">Tab Top</option>
                    <option value="ripplefold">Ripplefold</option>
                    <option value="eyelet">Eyelet</option>
                    <option value="goblet">Goblet</option>
                  </select>
                </label>
              </div>
              <label style={{ fontSize: 12 }}>
                <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Lining</span>
                <select value={opts.lining} onChange={e => setOpts(p => ({...p, lining: e.target.value}))}
                  style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 13, marginTop: 4, background: '#faf9f7', minHeight: 44 }}>
                  <option value="">None</option>
                  <option value="standard">Standard</option>
                  <option value="blackout">Blackout</option>
                  <option value="thermal">Thermal</option>
                </select>
              </label>
            </>
          )}

          <label style={{ fontSize: 12 }}>
            <span style={{ color: '#888', fontSize: 11, fontWeight: 600 }}>Notes</span>
            <textarea value={opts.notes} onChange={e => setOpts(p => ({...p, notes: e.target.value}))}
              placeholder="Additional notes..." rows={2}
              style={{ width: '100%', padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', fontSize: 13, marginTop: 4, background: '#faf9f7', resize: 'none' }} />
          </label>

          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
            <button onClick={addItem}
              disabled={!m.width_inches && !m.height_inches}
              className="flex items-center gap-2 cursor-pointer transition-all hover:brightness-110 disabled:opacity-50"
              style={{ flex: 1, padding: '12px 20px', borderRadius: 10, background: '#b8960c', color: '#fff', fontSize: 13, fontWeight: 700, border: 'none', minHeight: 48 }}>
              <CheckCircle size={16} /> Add Item
            </button>
            <button onClick={() => { setM({width_inches:0,height_inches:0,depth_inches:0,sill_depth:0,stack_space:0}); setOpts({mount_type:'inside',treatment:'',lining:'',notes:'',fabric:''}); }}
              className="cursor-pointer transition-all hover:bg-[#f0ede8]"
              style={{ padding: '12px 16px', borderRadius: 10, border: '1px solid #ece8e0', background: '#faf9f7', fontSize: 13, fontWeight: 600, color: '#777', minHeight: 48 }}>
              Clear
            </button>
          </div>
        </div>

        {/* Right: live SVG diagram */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
          {(m.width_inches > 0 || m.height_inches > 0) ? (
            <>
              <div style={{ border: '1px solid #ece8e0', borderRadius: 12, overflow: 'hidden', background: '#fff', padding: 8, width: '100%' }}>
                <MeasurementDiagram
                  item={currentItem as any}
                  width={400}
                  height={320}
                />
              </div>
              <span style={{ fontSize: 11, color: '#888' }}>Live preview -- updates as you type</span>
            </>
          ) : (
            <div style={{ width: '100%', height: 320, borderRadius: 12, border: '2px dashed #ece8e0', background: '#faf9f7', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
              <Ruler size={32} style={{ color: '#ddd' }} />
              <span style={{ fontSize: 13, color: '#aaa', fontWeight: 500 }}>Enter measurements to see diagram</span>
            </div>
          )}
        </div>
      </div>

      {/* Added items list */}
      {items.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <div className="section-label" style={{ marginBottom: 8 }}>ITEMS ADDED ({items.length})</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {items.map((item, i) => (
              <div key={item.id} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 14px', borderRadius: 10, background: '#f0fdf4', border: '1px solid #bbf7d0' }}>
                <CheckCircle size={16} style={{ color: '#16a34a', flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>
                    {MANUAL_ITEM_TYPES.find(t => t.key === item.type)?.label || item.type}
                  </span>
                  <span style={{ fontSize: 12, color: '#666', marginLeft: 8 }}>
                    {item.measurements.width_inches}" x {item.measurements.height_inches}"
                    {item.treatment ? ` · ${item.treatment.replace(/_/g, ' ')}` : ''}
                  </span>
                </div>
                <button onClick={() => setItems(prev => prev.filter((_, idx) => idx !== i))}
                  className="cursor-pointer hover:bg-white transition-colors"
                  style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid #bbf7d0', background: 'transparent', color: '#999' }}>
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════
   Main Component
   ═══════════════════════════════════════════════════════════ */

const MODE_ORDER: AnalysisMode[] = ['measure', 'upholstery', 'mockup', 'outline'];

export default function PhotoAnalysisPanel({ onAnalysisComplete, onSaveQuote, initialImage, compact = false, customerName, customerEmail, jobId }: PhotoAnalysisPanelProps) {
  const [mode, setMode] = useState<AnalysisMode>('measure');
  const [imageData, setImageData] = useState<string>(initialImage || '');
  const [preferences, setPreferences] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<any>(null);
  // Store results per mode so they persist when switching tabs
  const [allResults, setAllResults] = useState<Record<string, any>>({});
  const [dragActive, setDragActive] = useState(false);
  const [showCamera, setShowCamera] = useState(false);
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [model3D, setModel3D] = useState<string | null>(null);
  // Multi-photo organizer
  const [photos, setPhotos] = useState<PhotoEntry[]>([]);
  const [activePhotoId, setActivePhotoId] = useState<string | null>(null);
  const [showGallery, setShowGallery] = useState(true);
  // Design Mockup style preferences
  const [selectedStyles, setSelectedStyles] = useState<string[]>([]);
  const [measureInputMethod, setMeasureInputMethod] = useState<MeasureInputMethod>('photo');
  const fileRef = useRef<HTMLInputElement>(null);
  const file3DRef = useRef<HTMLInputElement>(null);
  const multiFileRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (initialImage) setImageData(initialImage);
  }, [initialImage]);

  // Sync active photo's results with allResults
  const activePhoto = photos.find(p => p.id === activePhotoId);

  // When switching modes, restore previous result for that mode (keep photo)
  const switchMode = (newMode: AnalysisMode) => {
    setMode(newMode);
    const results = activePhoto ? activePhoto.results : allResults;
    setResult(results[newMode] || null);
    setError('');
  };

  const nextMode = () => {
    const idx = MODE_ORDER.indexOf(mode);
    if (idx < MODE_ORDER.length - 1) switchMode(MODE_ORDER[idx + 1]);
  };

  const currentResults = activePhoto ? activePhoto.results : allResults;
  const completedSteps = MODE_ORDER.filter(m => currentResults[m]);

  /* ── Multi-photo helpers ── */

  const addPhotoEntry = (imgData: string, name?: string) => {
    const id = `photo-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    const entry: PhotoEntry = {
      id,
      imageData: imgData,
      name: name || `Photo ${photos.length + 1}`,
      addedAt: new Date(),
      results: {},
    };
    setPhotos(prev => [...prev, entry]);
    selectPhoto(entry);
  };

  const selectPhoto = (entry: PhotoEntry) => {
    setActivePhotoId(entry.id);
    setImageData(entry.imageData);
    setAllResults(entry.results);
    setResult(entry.results[mode] || null);
    setError('');
  };

  const removePhoto = (id: string) => {
    setPhotos(prev => prev.filter(p => p.id !== id));
    if (activePhotoId === id) {
      setActivePhotoId(null);
      setImageData('');
      setAllResults({});
      setResult(null);
    }
  };

  const handleMultiFiles = async (files: FileList) => {
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (!file.type.startsWith('image/') || file.size > 20 * 1024 * 1024) continue;
      try {
        const b64 = await fileToBase64(file);
        const id = `photo-${Date.now()}-${i}-${Math.random().toString(36).slice(2, 6)}`;
        const entry: PhotoEntry = {
          id,
          imageData: b64,
          name: file.name.replace(/\.[^.]+$/, '') || `Photo ${photos.length + i + 1}`,
          addedAt: new Date(),
          results: {},
        };
        setPhotos(prev => [...prev, entry]);
        // Auto-select first added
        if (i === 0) selectPhoto(entry);
      } catch { /* skip bad files */ }
    }
  };

  const getPhotoAnalysisCount = (p: PhotoEntry) => MODE_ORDER.filter(m => p.results[m]).length;
  const totalAnalyzed = photos.filter(p => getPhotoAnalysisCount(p) > 0).length;

  /* ── File handling ── */

  const fileToBase64 = (file: File): Promise<string> =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

  const handleFile = useCallback(async (file: File) => {
    if (!file.type.startsWith('image/')) {
      setError('Please upload an image file (JPG, PNG, etc.)');
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      setError('Image must be under 20 MB.');
      return;
    }
    setError('');
    try {
      const b64 = await fileToBase64(file);
      setImageData(b64);
      setResult(null);
      // Add to gallery
      addPhotoEntry(b64, file.name.replace(/\.[^.]+$/, ''));
    } catch {
      setError('Failed to read image file.');
    }
  }, [photos.length]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  /* ── Camera ── */

  const startCamera = async () => {
    setError('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
      });
      setCameraStream(stream);
      setShowCamera(true);
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play();
        }
      }, 100);
    } catch {
      setError('Camera access denied. Please allow camera permission and try again.');
    }
  };

  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
    setImageData(dataUrl);
    setResult(null);
    addPhotoEntry(dataUrl, `Camera ${new Date().toLocaleTimeString()}`);
    stopCamera();
  };

  const stopCamera = () => {
    if (cameraStream) {
      cameraStream.getTracks().forEach(t => t.stop());
      setCameraStream(null);
    }
    setShowCamera(false);
  };

  useEffect(() => {
    return () => {
      if (cameraStream) cameraStream.getTracks().forEach(t => t.stop());
    };
  }, [cameraStream]);

  /* ── 3D File ── */

  const handle3DUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['glb', 'gltf', 'obj', 'ply', 'usdz'].includes(ext || '')) {
      setError('Supported 3D formats: GLB, GLTF, OBJ, PLY, USDZ');
      return;
    }
    setError('');
    const url = URL.createObjectURL(file);
    setModel3D(url);
    setResult(null);
  };

  /* ── Analysis ── */

  const analyze = async () => {
    if (!imageData) { setError('Please upload a photo first.'); return; }
    setLoading(true);
    setError('');
    setResult(null);

    const endpointMap: Record<AnalysisMode, string> = {
      measure: '/vision/measure',
      upholstery: '/vision/upholstery',
      mockup: '/vision/mockup',
      outline: '/vision/outline',
    };

    const body: any = { image: imageData };
    if ((mode === 'measure' || mode === 'mockup') && preferences.trim()) {
      body.preferences = preferences.trim();
    }
    if (mode === 'mockup' && selectedStyles.length > 0) {
      body.styles = selectedStyles;
      // Append styles to preferences for AI context
      const styleNames = selectedStyles.map(s => DESIGN_STYLES.find(ds => ds.key === s)?.label || s).join(', ');
      body.preferences = `${body.preferences || ''} Requested styles: ${styleNames}`.trim();
    }

    try {
      const res = await fetch(`${API}${endpointMap[mode]}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`Analysis failed (${res.status})`);
      const data = await res.json();
      setResult(data);
      setAllResults(prev => ({ ...prev, [mode]: data }));
      // Save result to active photo entry
      if (activePhotoId) {
        setPhotos(prev => prev.map(p =>
          p.id === activePhotoId ? { ...p, results: { ...p.results, [mode]: data } } : p
        ));
      }
      onAnalysisComplete?.(mode, data);
    } catch (err: any) {
      setError(err.message || 'Analysis failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  /* ── Create Quote in Backend ── */

  const createQuoteFromAnalysis = async () => {
    const measureData = currentResults['measure'] as MeasureResult | undefined;
    const upholsteryData = currentResults['upholstery'] as UpholsteryResult | undefined;
    const mockupData = currentResults['mockup'] as MockupResult | undefined;
    const outlineData = currentResults['outline'] as OutlineResult | undefined;

    // 1. Create or find customer in ForgeCRM
    let crmCustomerId: string | null = null;
    if (customerName) {
      try {
        // Check if customer already exists
        const searchRes = await fetch(`${API}/crm/customers?search=${encodeURIComponent(customerName)}&limit=1`);
        const searchData = await searchRes.json();
        const existing = (searchData.customers || []).find((c: any) =>
          c.name?.toLowerCase() === customerName.toLowerCase() ||
          (customerEmail && c.email?.toLowerCase() === customerEmail.toLowerCase())
        );

        if (existing) {
          crmCustomerId = existing.id;
        } else {
          // Create new customer in CRM
          const createRes = await fetch(`${API}/crm/customers`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              name: customerName,
              email: customerEmail || null,
              phone: null,
              address: null,
              type: 'residential',
              source: 'direct',
              tags: ['ai-analysis'],
              notes: `Created from AI Photo Analysis on ${new Date().toLocaleDateString()}. ${photos.length} photo(s) analyzed.`,
            }),
          });
          if (createRes.ok) {
            const crmData = await createRes.json();
            crmCustomerId = crmData.customer?.id || null;
          }
        }
      } catch { /* CRM creation is non-blocking */ }
    }

    // 2. Build line items from analysis results
    const lineItems: any[] = [];

    if (measureData) {
      lineItems.push({
        description: `Window Measurement — ${measureData.window_type || 'Standard'} (${measureData.width_inches}" W x ${measureData.height_inches}" H)`,
        quantity: 1, unit: 'ea', rate: 0, amount: 0, category: 'labor',
      });
    }

    if (upholsteryData) {
      lineItems.push({
        description: `${upholsteryData.furniture_type || 'Furniture'} Reupholstery — ${upholsteryData.style || 'Standard'}`,
        quantity: 1, unit: 'ea',
        rate: upholsteryData.estimated_labor_cost_low || 0,
        amount: upholsteryData.estimated_labor_cost_low || 0,
        category: 'labor',
      });
      if (upholsteryData.fabric_yards_plain > 0) {
        lineItems.push({
          description: `Fabric (plain) — ${upholsteryData.fabric_yards_plain} yards`,
          quantity: upholsteryData.fabric_yards_plain, unit: 'ea', rate: 25, amount: upholsteryData.fabric_yards_plain * 25,
          category: 'materials',
        });
      }
    }

    if (mockupData?.proposals?.length) {
      mockupData.proposals.forEach((p: any) => {
        lineItems.push({
          description: `Design Proposal: ${p.tier} — ${p.treatment_type || ''} ${p.style || ''}`.trim(),
          quantity: 1, unit: 'ea',
          rate: p.price_range_low || 0,
          amount: p.price_range_low || 0,
          category: 'labor',
        });
      });
    }

    const subtotal = lineItems.reduce((s, i) => s + (i.amount || 0), 0);
    const taxRate = 0.06;

    const payload = {
      customer_name: customerName || 'Walk-in Customer',
      customer_email: customerEmail || null,
      customer_phone: null,
      customer_address: null,
      project_name: `AI Analysis${jobId ? ` — ${jobId}` : ''}`,
      project_description: `AI Photo Analysis: ${completedSteps.length}/4 steps completed. ${photos.length} photo(s) analyzed.${selectedStyles.length ? ` Styles: ${selectedStyles.join(', ')}` : ''}`,
      line_items: lineItems,
      measurements: measureData ? {
        width: measureData.width_inches,
        height: measureData.height_inches,
        unit: 'in',
        window_type: measureData.window_type || null,
        notes: measureData.notes || null,
      } : null,
      subtotal,
      tax_rate: taxRate,
      tax_amount: Math.round(subtotal * taxRate * 100) / 100,
      discount_amount: 0,
      total: Math.round(subtotal * (1 + taxRate) * 100) / 100,
      deposit: { deposit_percent: 50, deposit_amount: Math.round(subtotal * (1 + taxRate) * 50) / 100 },
      notes: `Generated from AI Photo Analysis.\nPhotos: ${photos.length}\nSteps: ${completedSteps.map(s => MODES.find(m => m.key === s)?.label).join(', ')}`,
      rooms: [],
      ai_outlines: outlineData ? [outlineData] : [],
      ai_mockups: mockupData?.proposals || [],
    };

    try {
      const res = await fetch(`${API}/quotes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`Failed (${res.status})`);
      const data = await res.json();
      const qNum = data.quote?.quote_number || data.quote_number || 'New';
      onSaveQuote?.({ ...payload, quoteId: data.quote?.id, quoteNumber: qNum, crmCustomerId });
      alert(`Quote ${qNum} created!${crmCustomerId ? ` Customer saved to ForgeCRM.` : ''}\nView in Empire Workroom → Quotes.`);
      return data;
    } catch (err: any) {
      alert(`Failed to create quote: ${err.message}`);
      return null;
    }
  };

  /* ── Result renderers ── */

  const renderMeasureResults = (data: MeasureResult) => (
    <div>
      {/* Dimension Drawing on Photo */}
      {imageData && data.width_inches > 0 && data.height_inches > 0 && (
        <>
          <SectionHeader>DIMENSION DRAWING</SectionHeader>
          <DimensionDrawing
            imageData={imageData}
            width={data.width_inches}
            height={data.height_inches}
            windowType={data.window_type || 'Window'}
          />
        </>
      )}

      <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
        <MetricBox label="Width" value={`${data.width_inches}"`} color="#2563eb" />
        <MetricBox label="Height" value={`${data.height_inches}"`} color="#2563eb" />
      </div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
        <MetricBox label="Window Type" value={data.window_type || 'Standard'} />
        <MetricBox label="Scale Method" value={data.scale_method || 'Auto'} />
      </div>

      <SectionHeader>CONFIDENCE</SectionHeader>
      <ConfidenceBar value={data.confidence} color="#2563eb" />

      {data.reference_objects_used?.length > 0 && (
        <>
          <SectionHeader>REFERENCE OBJECTS</SectionHeader>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {data.reference_objects_used.map((obj, i) => (
              <span key={i} className="status-pill" style={{ background: '#eff6ff', color: '#2563eb' }}>{typeof obj === 'string' ? obj : JSON.stringify(obj)}</span>
            ))}
          </div>
        </>
      )}

      {data.treatment_suggestions?.length > 0 && (
        <>
          <SectionHeader>TREATMENT SUGGESTIONS</SectionHeader>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {data.treatment_suggestions.map((s, i) => (
              <span key={i} className="status-pill" style={{ background: '#fdf4ff', color: '#7c3aed' }}>{typeof s === 'string' ? s : JSON.stringify(s)}</span>
            ))}
          </div>
        </>
      )}

      {data.notes && (
        <>
          <SectionHeader>NOTES</SectionHeader>
          <p style={{ fontSize: 12, color: '#555', lineHeight: 1.5 }}>{data.notes}</p>
        </>
      )}
    </div>
  );

  const renderUpholsteryResults = (data: UpholsteryResult) => (
    <div>
      <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
        <MetricBox label="Furniture Type" value={data.furniture_type || 'Unknown'} color="#7c3aed" />
        <MetricBox label="Style" value={data.style || 'Standard'} color="#7c3aed" />
      </div>

      <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
        <MetricBox label="Cushions" value={String(data.cushion_count ?? '—')} />
        <MetricBox label="Plain Fabric" value={`${data.fabric_yards_plain ?? '—'} yd`} sub="yardage" />
        <MetricBox label="Patterned Fabric" value={`${data.fabric_yards_patterned ?? '—'} yd`} sub="yardage" />
      </div>

      <SectionHeader>LABOR ESTIMATE</SectionHeader>
      <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
        <MetricBox label="Labor Type" value={data.suggested_labor_type || '—'} />
        <MetricBox
          label="Cost Range"
          value={`$${data.estimated_labor_cost_low?.toLocaleString() ?? '—'} – $${data.estimated_labor_cost_high?.toLocaleString() ?? '—'}`}
          color="#b8960c"
        />
      </div>

      <SectionHeader>DETAILS</SectionHeader>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 14 }}>
        <DetailCheck label="Welting" checked={data.has_welting} />
        <DetailCheck label="Tufting" checked={data.has_tufting} />
        <DetailCheck label="Channeling" checked={data.has_channeling} />
        <DetailCheck label="Skirt" checked={data.has_skirt} />
        <DetailCheck label="Nailhead Trim" checked={data.has_nailhead} />
        <DetailCheck label="New Foam Recommended" checked={data.new_foam_recommended} />
      </div>

      <SectionHeader>CONFIDENCE</SectionHeader>
      <ConfidenceBar value={data.confidence} color="#7c3aed" />

      {data.questions?.length > 0 && (
        <>
          <SectionHeader>FOLLOW-UP QUESTIONS</SectionHeader>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {data.questions.map((q, i) => (
              <li key={i} style={{ fontSize: 12, color: '#555', lineHeight: 1.6 }}>{typeof q === 'string' ? q : JSON.stringify(q)}</li>
            ))}
          </ul>
        </>
      )}

      {data.renovation_proposals?.length > 0 && (
        <>
          <SectionHeader>RENOVATION PROPOSALS</SectionHeader>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {data.renovation_proposals.map((p: any, i: number) => (
              <div key={i} style={{ padding: 14, borderRadius: 12, border: '1px solid #e9d5ff', background: '#fdf4ff' }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: '#7c3aed', marginBottom: 4 }}>{p.title || `Proposal ${i + 1}`}</div>
                <p style={{ fontSize: 12, color: '#555', lineHeight: 1.5, margin: 0 }}>{p.description || JSON.stringify(p)}</p>
                {p.estimated_cost && (
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#b8960c', marginTop: 6 }}>{p.estimated_cost}</div>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {data.generated_image && (
        <>
          <SectionHeader>AI VISUALIZATION</SectionHeader>
          <div style={{ borderRadius: 12, overflow: 'hidden', border: '1px solid #ece8e0' }}>
            <img
              src={data.generated_image.startsWith('http') ? data.generated_image : `${IMAGE_BASE}${data.generated_image}`}
              alt="AI-generated upholstery visualization"
              style={{ width: '100%', display: 'block' }}
            />
          </div>
        </>
      )}
    </div>
  );

  const renderMockupResults = (data: MockupResult) => (
    <div>
      {data.room_assessment && (
        <>
          <SectionHeader>ROOM ASSESSMENT</SectionHeader>
          {typeof data.room_assessment === 'string' ? (
            <p style={{ fontSize: 12, color: '#555', lineHeight: 1.6, margin: 0, marginBottom: 10 }}>{data.room_assessment}</p>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
              {Object.entries(data.room_assessment).map(([k, v]) => (
                <div key={k} style={{ padding: '8px 12px', borderRadius: 8, background: '#faf9f7', border: '1px solid #ece8e0' }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{k.replace(/_/g, ' ')}</div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a', marginTop: 2 }}>{Array.isArray(v) ? (v as string[]).join(', ') : String(v)}</div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {data.window_info && (
        <>
          <SectionHeader>WINDOW INFO</SectionHeader>
          {typeof data.window_info === 'string' ? (
            <p style={{ fontSize: 12, color: '#555', lineHeight: 1.6, margin: 0, marginBottom: 10 }}>{data.window_info}</p>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 10 }}>
              {Object.entries(data.window_info).map(([k, v]) => (
                <div key={k} style={{ padding: '8px 12px', borderRadius: 8, background: '#faf9f7', border: '1px solid #ece8e0' }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{k.replace(/_/g, ' ')}</div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a', marginTop: 2 }}>{v == null ? '—' : String(v)}</div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      <SectionHeader>DESIGN PROPOSALS</SectionHeader>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {(data.proposals || []).map((p, i) => {
          const tierStyle = TIER_COLORS[p.tier] || { bg: '#faf9f7', border: '#ece8e0', accent: '#b8960c' };
          const genImage = data.generated_images?.find(g => g.tier === p.tier);

          return (
            <div key={i} style={{ borderRadius: 14, border: `1.5px solid ${tierStyle.border}`, background: tierStyle.bg, overflow: 'hidden' }}>
              <div style={{ padding: '14px 18px', borderBottom: `1px solid ${tierStyle.border}` }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontSize: 14, fontWeight: 700, color: tierStyle.accent }}>{p.tier}</span>
                  <span style={{ fontSize: 14, fontWeight: 700, color: '#b8960c' }}>
                    ${p.price_range_low?.toLocaleString()} – ${p.price_range_high?.toLocaleString()}
                  </span>
                </div>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a', marginBottom: 2 }}>{p.treatment_type} &middot; {p.style}</div>
              </div>

              <div style={{ padding: '14px 18px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 12 }}>
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em' }}>FABRIC</div>
                    <div style={{ fontSize: 12, color: '#333', marginTop: 2 }}>{p.fabric}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em' }}>LINING</div>
                    <div style={{ fontSize: 12, color: '#333', marginTop: 2 }}>{p.lining}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em' }}>HARDWARE</div>
                    <div style={{ fontSize: 12, color: '#333', marginTop: 2 }}>{p.hardware}</div>
                  </div>
                  {p.extras?.length > 0 && (
                    <div>
                      <div style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em' }}>EXTRAS</div>
                      <div style={{ fontSize: 12, color: '#333', marginTop: 2 }}>{p.extras.join(', ')}</div>
                    </div>
                  )}
                </div>

                {p.visual_description && (
                  <div style={{ padding: '10px 12px', borderRadius: 10, background: 'rgba(255,255,255,0.6)', border: `1px solid ${tierStyle.border}`, marginBottom: 10 }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>VISUAL DESCRIPTION</div>
                    <p style={{ fontSize: 12, color: '#555', lineHeight: 1.5, margin: 0 }}>{p.visual_description}</p>
                  </div>
                )}

                {p.design_rationale && (
                  <div style={{ padding: '10px 12px', borderRadius: 10, background: 'rgba(255,255,255,0.6)', border: `1px solid ${tierStyle.border}` }}>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>DESIGN RATIONALE</div>
                    <p style={{ fontSize: 12, color: '#555', lineHeight: 1.5, margin: 0 }}>{p.design_rationale}</p>
                  </div>
                )}
              </div>

              {genImage?.url && (
                <div style={{ borderTop: `1px solid ${tierStyle.border}` }}>
                  <img
                    src={genImage.url.startsWith('http') ? genImage.url : `${IMAGE_BASE}${genImage.url}`}
                    alt={`${p.tier} design mockup`}
                    style={{ width: '100%', display: 'block' }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {data.general_recommendations && (
        <>
          <SectionHeader>GENERAL RECOMMENDATIONS</SectionHeader>
          {Array.isArray(data.general_recommendations) ? (
            <ul style={{ margin: 0, paddingLeft: 18, marginBottom: 10 }}>
              {data.general_recommendations.map((r: string, i: number) => (
                <li key={i} style={{ fontSize: 12, color: '#555', lineHeight: 1.6 }}>{typeof r === 'string' ? r : JSON.stringify(r)}</li>
              ))}
            </ul>
          ) : (
            <p style={{ fontSize: 12, color: '#555', lineHeight: 1.6, margin: 0 }}>{String(data.general_recommendations)}</p>
          )}
        </>
      )}

      <SectionHeader>CONFIDENCE</SectionHeader>
      <ConfidenceBar value={data.confidence} color="#b8960c" />

      {data.notes && (
        <>
          <SectionHeader>NOTES</SectionHeader>
          <p style={{ fontSize: 12, color: '#555', lineHeight: 1.5, margin: 0 }}>{data.notes}</p>
        </>
      )}
    </div>
  );

  const renderOutlineResults = (data: OutlineResult) => {
    const dims = (obj: any, label: string) => {
      if (!obj) return null;
      if (typeof obj === 'string') return <MetricBox label={label} value={obj} />;
      const parts: string[] = [];
      if (obj.width) parts.push(`W: ${obj.width}"`);
      if (obj.height) parts.push(`H: ${obj.height}"`);
      if (obj.depth) parts.push(`D: ${obj.depth}"`);
      return <MetricBox label={label} value={parts.join(' x ') || JSON.stringify(obj)} color="#16a34a" />;
    };

    // Installer checklist items
    const checklist = [
      { label: 'Verify window dimensions on-site', category: 'pre' },
      { label: 'Check for level/plumb with spirit level', category: 'pre' },
      { label: 'Confirm mounting surface (drywall, wood, plaster, concrete)', category: 'pre' },
      { label: 'Mark bracket positions with pencil', category: 'install' },
      { label: 'Pre-drill pilot holes', category: 'install' },
      { label: 'Install brackets/hardware', category: 'install' },
      { label: 'Hang treatment and adjust', category: 'install' },
      { label: 'Test operation (open/close, tilt, raise/lower)', category: 'post' },
      { label: 'Check clearance from furniture/walls', category: 'post' },
      { label: 'Clean up and photograph finished install', category: 'post' },
    ];

    return (
      <div>
        {/* Summary banner */}
        <div style={{ padding: '14px 16px', borderRadius: 12, background: 'linear-gradient(135deg, #f0fdf4, #dcfce7)', border: '1px solid #bbf7d0', marginBottom: 14 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#16a34a', marginBottom: 4 }}>Installation Blueprint</div>
          <div style={{ fontSize: 11, color: '#15803d', lineHeight: 1.5 }}>
            This plan provides all dimensions, clearances, obstructions, and mounting details your installer needs. Print or share with the install team.
          </div>
        </div>

        {/* Dimensions */}
        <SectionHeader>DIMENSIONS</SectionHeader>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 14 }}>
          {dims(data.window_opening, 'Window Opening')}
          {dims(data.wall_dimensions, 'Wall Dimensions')}
        </div>

        {data.clearances && (
          <>
            <SectionHeader>CLEARANCES & SPACE</SectionHeader>
            <div style={{ padding: 14, borderRadius: 12, border: '1px solid #ece8e0', background: '#faf9f7', marginBottom: 10 }}>
              {typeof data.clearances === 'string' ? (
                <p style={{ fontSize: 12, color: '#555', margin: 0 }}>{data.clearances}</p>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  {Object.entries(data.clearances).map(([k, v]) => (
                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                      <span style={{ color: '#777', textTransform: 'capitalize' }}>{k.replace(/_/g, ' ')}</span>
                      <span style={{ fontWeight: 600, color: '#1a1a1a' }}>{String(v)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        {data.obstructions?.length > 0 && (
          <>
            <SectionHeader>OBSTRUCTIONS & HAZARDS</SectionHeader>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 10 }}>
              {data.obstructions.map((o, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', borderRadius: 8, background: '#fffbeb', border: '1px solid #fde68a', fontSize: 12, color: '#d97706' }}>
                  <TriangleAlert size={14} />
                  <span style={{ color: '#92400e', fontWeight: 500 }}>{typeof o === 'string' ? o : JSON.stringify(o)}</span>
                </div>
              ))}
            </div>
          </>
        )}

        {data.existing_treatments && (
          <>
            <SectionHeader>EXISTING TREATMENTS</SectionHeader>
            <div style={{ padding: 12, borderRadius: 10, background: '#faf9f7', border: '1px solid #ece8e0', marginBottom: 10 }}>
              <p style={{ fontSize: 12, color: '#555', lineHeight: 1.5, margin: 0 }}>{data.existing_treatments}</p>
            </div>
          </>
        )}

        {data.mounting_recommendations?.length > 0 && (
          <>
            <SectionHeader>MOUNTING RECOMMENDATIONS</SectionHeader>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 10 }}>
              {data.mounting_recommendations.map((r, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '8px 12px', borderRadius: 8, background: '#f0fdf4', border: '1px solid #bbf7d0' }}>
                  <CheckCircle size={14} style={{ color: '#16a34a', marginTop: 1, flexShrink: 0 }} />
                  <span style={{ fontSize: 12, color: '#1a1a1a', lineHeight: 1.5 }}>{typeof r === 'string' ? r : JSON.stringify(r)}</span>
                </div>
              ))}
            </div>
          </>
        )}

        {data.outline_description && (
          <>
            <SectionHeader>INSTALLATION NOTES</SectionHeader>
            <div style={{ padding: 12, borderRadius: 10, background: '#eff6ff', border: '1px solid #bfdbfe', marginBottom: 10 }}>
              <p style={{ fontSize: 12, color: '#1e40af', lineHeight: 1.5, margin: 0 }}>{data.outline_description}</p>
            </div>
          </>
        )}

        {data.reference_objects_used?.length > 0 && (
          <>
            <SectionHeader>REFERENCE OBJECTS DETECTED</SectionHeader>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
              {data.reference_objects_used.map((obj, i) => (
                <span key={i} className="status-pill" style={{ background: '#f0fdf4', color: '#16a34a' }}>{typeof obj === 'string' ? obj : JSON.stringify(obj)}</span>
              ))}
            </div>
          </>
        )}

        <SectionHeader>CONFIDENCE</SectionHeader>
        <ConfidenceBar value={data.confidence} color="#16a34a" />

        {data.notes && (
          <>
            <SectionHeader>ADDITIONAL NOTES</SectionHeader>
            <p style={{ fontSize: 12, color: '#555', lineHeight: 1.5, margin: 0, marginBottom: 14 }}>{data.notes}</p>
          </>
        )}

        {/* Installer Checklist */}
        <SectionHeader>INSTALLER CHECKLIST</SectionHeader>
        <div style={{ borderRadius: 12, border: '1px solid #ece8e0', overflow: 'hidden' }}>
          {['pre', 'install', 'post'].map(cat => (
            <div key={cat}>
              <div style={{ padding: '8px 14px', background: cat === 'pre' ? '#eff6ff' : cat === 'install' ? '#fdf8e8' : '#f0fdf4', fontSize: 10, fontWeight: 700, color: cat === 'pre' ? '#2563eb' : cat === 'install' ? '#b8960c' : '#16a34a', textTransform: 'uppercase', letterSpacing: '0.05em', borderBottom: '1px solid #ece8e0' }}>
                {cat === 'pre' ? 'Pre-Install Checks' : cat === 'install' ? 'Installation Steps' : 'Post-Install Verification'}
              </div>
              {checklist.filter(c => c.category === cat).map((c, i) => (
                <label key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 14px', borderBottom: '1px solid #f5f3ef', cursor: 'pointer', fontSize: 12, color: '#555' }}>
                  <input type="checkbox" style={{ accentColor: '#16a34a', width: 16, height: 16 }} />
                  <span>{c.label}</span>
                </label>
              ))}
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderResults = () => {
    if (!result) return null;
    switch (mode) {
      case 'measure': return renderMeasureResults(result);
      case 'upholstery': return renderUpholsteryResults(result);
      case 'mockup': return renderMockupResults(result);
      case 'outline': return renderOutlineResults(result);
    }
  };

  /* ── Render ── */

  const currentMode = MODES.find(m => m.key === mode)!;

  return (
    <div className="empire-card flat" style={{ padding: 0 }}>
      {/* Header */}
      <div
        className="flex items-center justify-between"
        style={{ padding: compact ? '12px 16px' : '14px 20px', borderBottom: '1px solid #ece8e0' }}
      >
        <div>
          <h3 className="flex items-center gap-2" style={{ fontSize: compact ? 13 : 15, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>
            <Camera size={compact ? 16 : 18} className="text-[#b8960c]" />
            AI Photo Analysis
          </h3>
          {customerName && (
            <div style={{ fontSize: 11, color: '#b8960c', fontWeight: 600, marginTop: 2 }}>
              Customer: {customerName} {jobId ? `· Job ${jobId}` : ''}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {photos.length > 0 && completedSteps.length > 0 && (
            <button
              onClick={createQuoteFromAnalysis}
              className="flex items-center gap-1 cursor-pointer hover:brightness-110 transition-all"
              style={{ padding: '4px 12px', borderRadius: 8, border: 'none', background: '#16a34a', fontSize: 11, fontWeight: 700, color: '#fff' }}
            >
              <CheckCircle size={12} /> Save to Quote
            </button>
          )}
          {result && (
            <button
              onClick={() => { setResult(null); setError(''); }}
              className="flex items-center gap-1 cursor-pointer hover:bg-[#f0ede8] transition-colors"
              style={{ padding: '4px 10px', borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7', fontSize: 11, fontWeight: 600, color: '#777' }}
            >
              <X size={12} /> Clear
            </button>
          )}
        </div>
      </div>

      <div style={{ padding: compact ? '14px 16px' : '20px' }}>

        {/* Workflow Progress */}
        {imageData && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 14, padding: '10px 14px', borderRadius: 10, background: '#faf9f7', border: '1px solid #ece8e0' }}>
            {MODE_ORDER.map((m, i) => {
              const modeInfo = MODES.find(x => x.key === m)!;
              const done = !!allResults[m];
              const active = m === mode;
              return (
                <React.Fragment key={m}>
                  <button
                    onClick={() => switchMode(m)}
                    className="flex items-center gap-1.5 cursor-pointer transition-all"
                    style={{
                      padding: '4px 10px', borderRadius: 8, fontSize: 11, fontWeight: 600, border: 'none',
                      background: active ? modeInfo.color : done ? '#dcfce7' : 'transparent',
                      color: active ? '#fff' : done ? '#16a34a' : '#999',
                    }}
                  >
                    {done && !active ? <CheckCircle size={12} /> : null}
                    {modeInfo.label}
                  </button>
                  {i < MODE_ORDER.length - 1 && (
                    <div style={{ width: 20, height: 2, background: done ? '#16a34a' : '#ddd', borderRadius: 1 }} />
                  )}
                </React.Fragment>
              );
            })}
            <span style={{ marginLeft: 'auto', fontSize: 10, fontWeight: 600, color: '#999' }}>
              {completedSteps.length}/{MODE_ORDER.length} complete
            </span>
          </div>
        )}

        {/* Mode tabs */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 16, flexWrap: 'wrap' }}>
          {MODES.map(m => {
            const active = m.key === mode;
            const done = !!allResults[m.key];
            return (
              <button
                key={m.key}
                onClick={() => switchMode(m.key)}
                className="flex items-center gap-1.5 cursor-pointer transition-all"
                style={{
                  padding: compact ? '6px 10px' : '8px 14px',
                  borderRadius: 10,
                  border: `1.5px solid ${active ? m.color : done ? '#16a34a' : '#ece8e0'}`,
                  background: active ? `${m.color}10` : done ? '#f0fdf4' : '#faf9f7',
                  color: active ? m.color : done ? '#16a34a' : '#777',
                  fontSize: compact ? 11 : 12,
                  fontWeight: 600,
                  whiteSpace: 'nowrap',
                }}
              >
                {m.icon}
                {m.label}
              </button>
            );
          })}
        </div>

        {/* Mode description */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 14 }}>
          <Info size={13} style={{ color: currentMode.color, flexShrink: 0 }} />
          <span style={{ fontSize: 12, color: '#777' }}>{currentMode.desc}</span>
        </div>

        {/* Input method selector — Measure tab only */}
        {mode === 'measure' && (
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            {[
              { key: 'photo' as MeasureInputMethod, label: 'Photo', icon: <Camera size={15} />, color: '#2563eb' },
              { key: '3dscan' as MeasureInputMethod, label: '3D Scan', icon: <Box size={15} />, color: '#16a34a' },
              { key: 'manual' as MeasureInputMethod, label: 'Manual Entry', icon: <Edit3 size={15} />, color: '#b8960c' },
            ].map(mi => {
              const active = measureInputMethod === mi.key;
              return (
                <button key={mi.key} onClick={() => setMeasureInputMethod(mi.key)}
                  className="flex items-center gap-2 cursor-pointer transition-all"
                  style={{
                    flex: 1, padding: '12px 16px', borderRadius: 12, fontSize: 13, fontWeight: 700,
                    border: `2px solid ${active ? mi.color : '#ece8e0'}`,
                    background: active ? `${mi.color}10` : '#faf9f7',
                    color: active ? mi.color : '#777', minHeight: 48,
                    justifyContent: 'center',
                  }}>
                  {mi.icon} {mi.label}
                </button>
              );
            })}
          </div>
        )}

        {/* Hidden inputs */}
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
        />
        <input
          ref={file3DRef}
          type="file"
          accept=".glb,.gltf,.obj,.ply,.usdz"
          className="hidden"
          onChange={handle3DUpload}
        />
        <input
          ref={multiFileRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={e => { if (e.target.files?.length) handleMultiFiles(e.target.files); }}
        />
        <canvas ref={canvasRef} className="hidden" />

        {/* ═══ Photo Gallery / Organizer ═══ */}
        {photos.length > 0 && !(mode === 'measure' && measureInputMethod === 'manual') && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <ImageIcon size={14} style={{ color: '#b8960c' }} />
                <span style={{ fontSize: 11, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Photo Queue ({photos.length})
                </span>
                <span style={{ fontSize: 10, color: '#999' }}>
                  {totalAnalyzed}/{photos.length} analyzed
                </span>
              </div>
              <button
                onClick={() => multiFileRef.current?.click()}
                className="flex items-center gap-1 cursor-pointer transition-colors hover:bg-[#f0ede8]"
                style={{ padding: '4px 10px', borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7', fontSize: 11, fontWeight: 600, color: '#b8960c' }}
              >
                <Plus size={12} /> Add Photos
              </button>
            </div>
            <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 6 }}>
              {photos.map(p => {
                const isActive = p.id === activePhotoId;
                const analysisCount = getPhotoAnalysisCount(p);
                const fullyDone = analysisCount === MODE_ORDER.length;
                return (
                  <div
                    key={p.id}
                    onClick={() => selectPhoto(p)}
                    className="cursor-pointer transition-all"
                    style={{
                      position: 'relative', flexShrink: 0, width: 80, borderRadius: 10, overflow: 'hidden',
                      border: `2px solid ${isActive ? '#b8960c' : fullyDone ? '#16a34a' : '#ece8e0'}`,
                      boxShadow: isActive ? '0 2px 10px rgba(184,150,12,0.3)' : 'none',
                    }}
                  >
                    <img src={p.imageData} alt={p.name} style={{ width: 80, height: 60, objectFit: 'cover', display: 'block' }} />
                    {/* Status overlay */}
                    <div style={{
                      position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                      background: fullyDone ? 'rgba(22,163,106,0.15)' : analysisCount > 0 ? 'rgba(184,150,12,0.1)' : 'transparent',
                    }} />
                    {/* Analysis badge */}
                    <div style={{
                      position: 'absolute', top: 3, right: 3,
                      width: 18, height: 18, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 9, fontWeight: 700,
                      background: fullyDone ? '#16a34a' : analysisCount > 0 ? '#b8960c' : '#ddd',
                      color: '#fff',
                    }}>
                      {fullyDone ? '✓' : `${analysisCount}`}
                    </div>
                    {/* Remove button */}
                    <button
                      onClick={(e) => { e.stopPropagation(); removePhoto(p.id); }}
                      className="cursor-pointer transition-opacity hover:opacity-100"
                      style={{
                        position: 'absolute', top: 3, left: 3, opacity: 0.6,
                        width: 16, height: 16, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                        background: 'rgba(0,0,0,0.5)', border: 'none', color: '#fff', padding: 0,
                      }}
                    >
                      <X size={10} />
                    </button>
                    {/* Name label */}
                    <div style={{
                      padding: '3px 6px', fontSize: 8, fontWeight: 600, color: '#777',
                      background: '#faf9f7', borderTop: '1px solid #ece8e0',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {p.name}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Three input method buttons */}
        {!imageData && !showCamera && !model3D && !(mode === 'measure' && measureInputMethod === 'manual') && (
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 8 }}>
              Choose Input Method
            </label>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10 }}>
              {/* Take Photo */}
              <button
                onClick={startCamera}
                className="flex flex-col items-center justify-center gap-2 cursor-pointer transition-all hover:scale-[1.02] active:scale-[0.98]"
                style={{
                  padding: compact ? '20px 12px' : '28px 16px',
                  borderRadius: 14,
                  border: '2px solid #7c3aed',
                  background: 'linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%)',
                }}
              >
                <div
                  className="flex items-center justify-center"
                  style={{ width: 48, height: 48, borderRadius: 14, background: '#7c3aed', color: '#fff' }}
                >
                  <Camera size={22} />
                </div>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#7c3aed' }}>Take Photo</span>
                <span style={{ fontSize: 10, color: '#999', textAlign: 'center' }}>Use device camera</span>
              </button>

              {/* Upload Photo */}
              <button
                onClick={() => fileRef.current?.click()}
                onDragOver={e => { e.preventDefault(); setDragActive(true); }}
                onDragLeave={() => setDragActive(false)}
                onDrop={handleDrop}
                className="flex flex-col items-center justify-center gap-2 cursor-pointer transition-all hover:scale-[1.02] active:scale-[0.98]"
                style={{
                  padding: compact ? '20px 12px' : '28px 16px',
                  borderRadius: 14,
                  border: `2px solid ${dragActive ? currentMode.color : '#2563eb'}`,
                  background: dragActive ? '#eff6ff' : 'linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)',
                }}
              >
                <div
                  className="flex items-center justify-center"
                  style={{ width: 48, height: 48, borderRadius: 14, background: '#2563eb', color: '#fff' }}
                >
                  <Upload size={22} />
                </div>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#2563eb' }}>Upload Photo</span>
                <span style={{ fontSize: 10, color: '#999', textAlign: 'center' }}>JPG, PNG up to 20 MB</span>
              </button>

              {/* Polycam 3D */}
              <button
                onClick={() => file3DRef.current?.click()}
                className="flex flex-col items-center justify-center gap-2 cursor-pointer transition-all hover:scale-[1.02] active:scale-[0.98]"
                style={{
                  padding: compact ? '20px 12px' : '28px 16px',
                  borderRadius: 14,
                  border: '2px solid #16a34a',
                  background: 'linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)',
                }}
              >
                <div
                  className="flex items-center justify-center"
                  style={{ width: 48, height: 48, borderRadius: 14, background: '#16a34a', color: '#fff' }}
                >
                  <Box size={22} />
                </div>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#16a34a' }}>Polycam 3D</span>
                <span style={{ fontSize: 10, color: '#999', textAlign: 'center' }}>GLB, GLTF, OBJ, PLY</span>
              </button>
            </div>
          </div>
        )}

        {/* Camera view */}
        {showCamera && !(mode === 'measure' && measureInputMethod === 'manual') && (
          <div style={{ marginBottom: 16, position: 'relative', borderRadius: 14, overflow: 'hidden', border: '2px solid #7c3aed', background: '#000' }}>
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              style={{ width: '100%', maxHeight: compact ? 220 : 360, display: 'block', objectFit: 'cover' }}
            />
            <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, display: 'flex', justifyContent: 'center', gap: 12, padding: '16px', background: 'linear-gradient(transparent, rgba(0,0,0,0.7))' }}>
              <button
                onClick={capturePhoto}
                className="flex items-center gap-2 cursor-pointer transition-all hover:scale-105 active:scale-95"
                style={{ padding: '10px 24px', borderRadius: 12, background: '#7c3aed', color: '#fff', fontSize: 13, fontWeight: 700, border: 'none', boxShadow: '0 4px 15px rgba(124,58,237,0.4)' }}
              >
                <Camera size={16} /> Capture
              </button>
              <button
                onClick={stopCamera}
                className="flex items-center gap-2 cursor-pointer transition-all hover:scale-105"
                style={{ padding: '10px 24px', borderRadius: 12, background: 'rgba(255,255,255,0.15)', color: '#fff', fontSize: 13, fontWeight: 600, border: '1px solid rgba(255,255,255,0.3)', backdropFilter: 'blur(8px)' }}
              >
                <X size={16} /> Cancel
              </button>
            </div>
          </div>
        )}

        {/* Photo preview */}
        {imageData && !showCamera && !(mode === 'measure' && measureInputMethod === 'manual') && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ position: 'relative', borderRadius: 14, overflow: 'hidden', border: '1px solid #ece8e0' }}>
              <img
                src={imageData}
                alt="Uploaded photo"
                style={{ width: '100%', maxHeight: compact ? 200 : 320, objectFit: 'contain', display: 'block', background: '#f5f3ef' }}
              />
              <button
                onClick={() => { setImageData(''); setModel3D(null); setResult(null); }}
                className="flex items-center justify-center cursor-pointer hover:bg-[#f0ede8] transition-colors"
                style={{
                  position: 'absolute', top: 8, right: 8,
                  width: 28, height: 28, borderRadius: 8,
                  background: 'rgba(255,255,255,0.9)', border: '1px solid #ece8e0',
                }}
              >
                <X size={14} className="text-[#999]" />
              </button>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <button
                onClick={() => multiFileRef.current?.click()}
                className="flex items-center gap-1.5 cursor-pointer transition-colors hover:bg-[#f0ede8]"
                style={{ padding: '6px 12px', borderRadius: 8, border: '1px solid #b8960c', background: '#fdf8e8', fontSize: 11, fontWeight: 600, color: '#b8960c' }}
              >
                <Plus size={12} /> Add More Photos
              </button>
              <button
                onClick={() => fileRef.current?.click()}
                className="flex items-center gap-1.5 cursor-pointer transition-colors hover:bg-[#f0ede8]"
                style={{ padding: '6px 12px', borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7', fontSize: 11, fontWeight: 600, color: '#777' }}
              >
                <Upload size={12} /> Replace
              </button>
              <button
                onClick={startCamera}
                className="flex items-center gap-1.5 cursor-pointer transition-colors hover:bg-[#f0ede8]"
                style={{ padding: '6px 12px', borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7', fontSize: 11, fontWeight: 600, color: '#777' }}
              >
                <Camera size={12} /> Camera
              </button>
            </div>
          </div>
        )}

        {/* 3D Model preview */}
        {model3D && !imageData && !showCamera && !(mode === 'measure' && measureInputMethod === 'manual') && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ position: 'relative', borderRadius: 14, overflow: 'hidden', border: '2px solid #16a34a', background: '#f0fdf4', padding: '32px 20px', textAlign: 'center' }}>
              <Box size={48} style={{ color: '#16a34a', margin: '0 auto 12px' }} />
              <div style={{ fontSize: 14, fontWeight: 700, color: '#16a34a', marginBottom: 4 }}>3D Model Loaded</div>
              <div style={{ fontSize: 12, color: '#777' }}>Polycam scan ready for analysis</div>
              <button
                onClick={() => { setModel3D(null); setResult(null); }}
                className="flex items-center justify-center cursor-pointer hover:bg-white transition-colors"
                style={{
                  position: 'absolute', top: 8, right: 8,
                  width: 28, height: 28, borderRadius: 8,
                  background: 'rgba(255,255,255,0.9)', border: '1px solid #bbf7d0',
                }}
              >
                <X size={14} className="text-[#999]" />
              </button>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <button
                onClick={() => { setModel3D(null); setResult(null); }}
                className="flex items-center gap-1.5 cursor-pointer transition-colors hover:bg-[#f0ede8]"
                style={{ padding: '6px 12px', borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7', fontSize: 11, fontWeight: 600, color: '#777' }}
              >
                <X size={12} /> Remove
              </button>
              <button
                onClick={() => fileRef.current?.click()}
                className="flex items-center gap-1.5 cursor-pointer transition-colors hover:bg-[#f0ede8]"
                style={{ padding: '6px 12px', borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7', fontSize: 11, fontWeight: 600, color: '#777' }}
              >
                <Upload size={12} /> Add Photo Instead
              </button>
            </div>
          </div>
        )}

        {/* Manual Entry — Measure tab only */}
        {mode === 'measure' && measureInputMethod === 'manual' && (
          <ManualMeasureEntry onAddToQuote={onSaveQuote} />
        )}

        {/* ═══ Mode-specific info panels & options ═══ */}

        {/* Measure info panel */}
        {mode === 'measure' && (
          <div style={{ marginBottom: 16, padding: '12px 14px', borderRadius: 12, background: '#eff6ff', border: '1px solid #bfdbfe' }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#2563eb', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
              What Measure Generates:
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
              {[
                'Window width & height (inches)',
                'Window type identification',
                'Reference object detection',
                'Scale method used',
                'Confidence score',
                'Treatment suggestions',
                'Measurement notes',
                'Photo reference points',
              ].map(item => (
                <div key={item} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#1e40af' }}>
                  <CheckCircle size={11} style={{ color: '#2563eb', flexShrink: 0 }} />
                  {item}
                </div>
              ))}
            </div>
            <div style={{ marginTop: 8, padding: '8px 10px', borderRadius: 8, background: 'rgba(37,99,235,0.08)', fontSize: 10, color: '#1e40af', lineHeight: 1.5 }}>
              Tip: Include a reference object (credit card, tape measure, dollar bill) in the photo for best accuracy.
            </div>
          </div>
        )}

        {/* Upholstery info panel */}
        {mode === 'upholstery' && (
          <div style={{ marginBottom: 16, padding: '12px 14px', borderRadius: 12, background: '#faf5ff', border: '1px solid #e9d5ff' }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#7c3aed', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
              What Upholstery Analysis Generates:
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
              {[
                'Furniture type & style ID',
                'Estimated dimensions',
                'Cushion count',
                'Fabric yardage (plain & patterned)',
                'Detail detection (welting, tufting, etc.)',
                'Labor type & cost estimate',
                'Foam replacement recommendation',
                'Renovation proposals with pricing',
                'AI visualization mockup',
                'Follow-up questions',
              ].map(item => (
                <div key={item} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#6b21a8' }}>
                  <CheckCircle size={11} style={{ color: '#7c3aed', flexShrink: 0 }} />
                  {item}
                </div>
              ))}
            </div>
            <div style={{ marginTop: 8, padding: '8px 10px', borderRadius: 8, background: 'rgba(124,58,237,0.08)', fontSize: 10, color: '#6b21a8', lineHeight: 1.5 }}>
              Tip: Take photos from multiple angles — front, side, cushion close-up — for the most accurate estimate. Add all to the photo queue.
            </div>
          </div>
        )}

        {/* Design Mockup Style Selector */}
        {mode === 'mockup' && (
          <>
            <div style={{ marginBottom: 12, padding: '12px 14px', borderRadius: 12, background: '#fdf8e8', border: '1px solid #fde68a' }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#b8960c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
                What Design Mockup Generates:
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                {[
                  'Room & window assessment',
                  '3-tier design proposals',
                  'Fabric & hardware recommendations',
                  'Price range per tier',
                  'Visual descriptions',
                  'AI-generated design images',
                  'Design rationale',
                  'General recommendations',
                ].map(item => (
                  <div key={item} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#92400e' }}>
                    <CheckCircle size={11} style={{ color: '#b8960c', flexShrink: 0 }} />
                    {item}
                  </div>
                ))}
              </div>
            </div>
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <label style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Select Design Styles — pick one or more
                </label>
                {selectedStyles.length > 0 && (
                  <span style={{ fontSize: 10, fontWeight: 600, color: '#b8960c' }}>
                    {selectedStyles.length} selected — mockup for each
                  </span>
                )}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6 }}>
                {DESIGN_STYLES.map(s => {
                  const selected = selectedStyles.includes(s.key);
                  return (
                    <button
                      key={s.key}
                      onClick={() => setSelectedStyles(prev =>
                        prev.includes(s.key) ? prev.filter(x => x !== s.key) : [...prev, s.key]
                      )}
                      className="cursor-pointer transition-all hover:scale-[1.02] active:scale-[0.98]"
                      style={{
                        padding: '8px 6px', borderRadius: 10, textAlign: 'center',
                        border: `1.5px solid ${selected ? '#b8960c' : '#ece8e0'}`,
                        background: selected ? '#fdf8e8' : '#faf9f7',
                      }}
                    >
                      <div style={{ fontSize: 18, marginBottom: 2 }}>{s.icon}</div>
                      <div style={{ fontSize: 11, fontWeight: 700, color: selected ? '#b8960c' : '#555' }}>{s.label}</div>
                      <div style={{ fontSize: 9, color: '#999', marginTop: 1 }}>{s.desc}</div>
                      {selected && (
                        <div style={{ marginTop: 4 }}>
                          <CheckCircle size={12} style={{ color: '#b8960c' }} />
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          </>
        )}

        {/* Install Plan info panel */}
        {mode === 'outline' && (
          <div style={{ marginBottom: 16, padding: '12px 14px', borderRadius: 12, background: '#f0fdf4', border: '1px solid #bbf7d0' }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: '#16a34a', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
              What Install Plan Generates:
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
              {[
                'Window opening dimensions',
                'Wall measurements',
                'Clearance from ceiling/floor',
                'Obstruction detection',
                'Mounting recommendations',
                'Existing treatment analysis',
                'Hardware requirements',
                'Installer checklist',
              ].map(item => (
                <div key={item} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#15803d' }}>
                  <CheckCircle size={11} style={{ color: '#16a34a', flexShrink: 0 }} />
                  {item}
                </div>
              ))}
            </div>
            <div style={{ marginTop: 8, padding: '8px 10px', borderRadius: 8, background: 'rgba(22,163,106,0.08)', fontSize: 10, color: '#15803d', lineHeight: 1.5 }}>
              Tip: Show full window frame, surrounding walls, and any nearby furniture or fixtures for complete install planning.
            </div>
          </div>
        )}

        {/* Preferences textarea (for measure and mockup) */}
        {(mode === 'measure' || mode === 'mockup') && (
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 6 }}>
              {mode === 'mockup' ? 'Additional Notes (Optional)' : 'Client Preferences (Optional)'}
            </label>
            <textarea
              value={preferences}
              onChange={e => setPreferences(e.target.value)}
              placeholder={mode === 'measure'
                ? 'e.g. Blackout needed, standard rod pocket, 96-inch wide window...'
                : 'e.g. Neutral palette, sheer + blackout layering, specific fabric preferences...'}
              rows={2}
              className="w-full outline-none focus:border-[#b8960c] transition-colors resize-none"
              style={{ padding: '10px 14px', fontSize: 13, border: '1px solid #ece8e0', borderRadius: 12, background: '#faf9f7' }}
            />
          </div>
        )}

        {/* Error */}
        {error && (
          <div style={{ padding: '10px 14px', borderRadius: 10, background: '#fef2f2', border: '1px solid #fecaca', fontSize: 12, color: '#dc2626', fontWeight: 600, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
            <AlertTriangle size={14} />
            {error}
          </div>
        )}

        {/* Analyze button */}
        {!result && !(mode === 'measure' && measureInputMethod === 'manual') && (
          <button
            onClick={analyze}
            disabled={loading || (!imageData && !model3D)}
            className="w-full flex items-center justify-center gap-2 cursor-pointer font-bold transition-all hover:brightness-110 disabled:opacity-50 active:scale-[0.98]"
            style={{
              height: compact ? 40 : 46,
              fontSize: 13,
              borderRadius: 12,
              background: currentMode.color,
              color: '#fff',
              border: 'none',
              boxShadow: `0 2px 10px ${currentMode.color}40`,
            }}
          >
            {loading ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Analyzing{mode === 'mockup' && selectedStyles.length > 0 ? ` ${selectedStyles.length} styles...` : '...'}
              </>
            ) : (
              <>
                <Sparkles size={16} />
                {mode === 'mockup' && selectedStyles.length > 0
                  ? `Generate ${selectedStyles.length} Design Mockup${selectedStyles.length > 1 ? 's' : ''}`
                  : 'Analyze Photo'}
              </>
            )}
          </button>
        )}

        {/* Results */}
        {result && (
          <div style={{ marginTop: 4 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
              <CheckCircle size={16} className="text-[#16a34a]" />
              <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>Analysis Complete</span>
              <span className="status-pill" style={{ background: `${currentMode.color}15`, color: currentMode.color }}>
                {currentMode.label}
              </span>
              <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
                {/* Print */}
                <button
                  onClick={() => window.print()}
                  className="flex items-center gap-1 cursor-pointer hover:bg-[#f0ede8] transition-colors"
                  title="Print"
                  style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid #ece8e0', background: '#faf9f7', fontSize: 10, fontWeight: 600, color: '#777' }}
                >
                  <Printer size={12} />
                </button>
                {/* PDF Download */}
                <button
                  onClick={async () => {
                    try {
                      const pdfBody: any = {
                        fileName: `${currentMode.label} - ${customerName || 'Analysis'}`,
                        screenshot: imageData || '',
                        unit: 'in',
                        measurements: [],
                      };
                      if (mode === 'measure' && result) {
                        pdfBody.measurements = [
                          { id: 1, distance_in: result.width_inches, distance_ft: (result.width_inches / 12).toFixed(2), distance_m: (result.width_inches * 0.0254).toFixed(3) },
                          { id: 2, distance_in: result.height_inches, distance_ft: (result.height_inches / 12).toFixed(2), distance_m: (result.height_inches * 0.0254).toFixed(3) },
                        ];
                      }
                      const res = await fetch(`${API}/vision/measurements-pdf`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(pdfBody),
                      });
                      if (res.ok) {
                        const blob = await res.blob();
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `${currentMode.label}_${customerName || 'analysis'}_${new Date().toISOString().slice(0, 10)}.pdf`;
                        a.click();
                        URL.revokeObjectURL(url);
                      } else {
                        alert('PDF generation failed — check backend');
                      }
                    } catch { alert('Could not generate PDF'); }
                  }}
                  className="flex items-center gap-1 cursor-pointer hover:bg-[#f0ede8] transition-colors"
                  title="Download PDF"
                  style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid #ece8e0', background: '#faf9f7', fontSize: 10, fontWeight: 600, color: '#777' }}
                >
                  <FileDown size={12} /> PDF
                </button>
                {/* Share */}
                <button
                  onClick={() => {
                    if (navigator.share) {
                      navigator.share({
                        title: `${currentMode.label} Analysis${customerName ? ` - ${customerName}` : ''}`,
                        text: `AI ${currentMode.label} analysis results${mode === 'measure' && result ? `: ${result.width_inches}" W x ${result.height_inches}" H` : ''}`,
                      }).catch(() => {});
                    } else {
                      const text = `AI ${currentMode.label} Analysis${customerName ? ` for ${customerName}` : ''}${mode === 'measure' && result ? `\nDimensions: ${result.width_inches}" W x ${result.height_inches}" H` : ''}`;
                      navigator.clipboard.writeText(text);
                      alert('Copied to clipboard!');
                    }
                  }}
                  className="flex items-center gap-1 cursor-pointer hover:bg-[#f0ede8] transition-colors"
                  title="Share"
                  style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid #ece8e0', background: '#faf9f7', fontSize: 10, fontWeight: 600, color: '#777' }}
                >
                  <Share2 size={12} />
                </button>
              </div>
            </div>
            {renderResults()}

            {/* Next Step Button */}
            {MODE_ORDER.indexOf(mode) < MODE_ORDER.length - 1 && (
              <div style={{ marginTop: 20, paddingTop: 16, borderTop: '1px solid #ece8e0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ fontSize: 11, color: '#999' }}>
                  Photo carries over to next step automatically
                </div>
                <button
                  onClick={nextMode}
                  className="flex items-center gap-2 cursor-pointer transition-all hover:brightness-110 active:scale-[0.98]"
                  style={{
                    padding: '10px 20px', borderRadius: 10, fontSize: 13, fontWeight: 700, border: 'none',
                    background: MODES[MODE_ORDER.indexOf(mode) + 1]?.color || '#16a34a',
                    color: '#fff',
                    boxShadow: `0 2px 10px ${MODES[MODE_ORDER.indexOf(mode) + 1]?.color || '#16a34a'}40`,
                  }}
                >
                  Next: {MODES[MODE_ORDER.indexOf(mode) + 1]?.label}
                  <ArrowRight size={14} />
                </button>
              </div>
            )}

            {/* All Steps Complete */}
            {MODE_ORDER.indexOf(mode) === MODE_ORDER.length - 1 && completedSteps.length === MODE_ORDER.length && (
              <div style={{ marginTop: 20, padding: '16px 18px', borderRadius: 12, background: '#dcfce7', border: '1px solid #bbf7d0', textAlign: 'center' }}>
                <CheckCircle size={24} style={{ color: '#16a34a', margin: '0 auto 8px' }} />
                <div style={{ fontSize: 14, fontWeight: 700, color: '#16a34a' }}>Full Analysis Complete</div>
                <div style={{ fontSize: 12, color: '#15803d', marginTop: 4 }}>
                  All 4 steps finished{customerName ? ` for ${customerName}` : ''} — {photos.length} photo{photos.length !== 1 ? 's' : ''} analyzed
                </div>
                {photos.length > 1 && (
                  <div style={{ fontSize: 11, color: '#16a34a', marginTop: 6 }}>
                    {totalAnalyzed}/{photos.length} photos have analysis data
                  </div>
                )}
                <button
                  onClick={createQuoteFromAnalysis}
                  className="flex items-center gap-2 cursor-pointer transition-all hover:brightness-110 active:scale-[0.98]"
                  style={{
                    margin: '12px auto 0', padding: '10px 24px', borderRadius: 10, fontSize: 13, fontWeight: 700,
                    border: 'none', background: '#16a34a', color: '#fff', boxShadow: '0 2px 10px rgba(22,163,106,0.3)',
                  }}
                >
                  <CheckCircle size={14} /> Save Analysis to Quote
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
