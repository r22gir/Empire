'use client';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { API } from '../../lib/api';
import {
  Ruler, Download, RefreshCw, Scissors, Info, FileText, Save,
  Minus, CornerDownRight, Square, Circle, Semicircle as SemicircleIcon,
} from 'lucide-react';

/* ── Types ───────────────────────────────────────────────────── */
interface DimensionField {
  key: string;
  label: string;
  default: number | string;
  unit?: string;
  step?: number;
  min?: number;
  max?: number;
  type?: 'number' | 'select' | 'slider';
  options?: (string | number)[];
}

interface ShapePreset {
  id: string;
  name: string;
  desc: string;
  iconLabel: string;
  fields: DimensionField[];
  edges: string[];
  sections: string[];
}

interface CalculationResult {
  linear_feet: number;
  square_footage: number;
  fabric_yardage_54: number;
  pieces: { name: string; width: number; height: number; quantity: number; notes?: string }[];
  svg?: string;
  construction_notes?: string[];
}

interface CustomShapeBuilderProps {
  onSave?: (shapeType: string, dimensions: Record<string, any>, result: any) => void;
}

/* ── Shape Presets ───────────────────────────────────────────── */
const SHAPES: ShapePreset[] = [
  {
    id: 'straight_bench',
    name: 'Straight Bench',
    desc: 'Standard flat bench seat',
    iconLabel: 'straight',
    fields: [
      { key: 'length', label: 'Length', default: 48, unit: '"', step: 1 },
      { key: 'depth', label: 'Depth', default: 18, unit: '"', step: 0.5 },
      { key: 'height', label: 'Height', default: 18, unit: '"', step: 0.5 },
    ],
    edges: ['back', 'left', 'right'],
    sections: ['main'],
  },
  {
    id: 'l_bench',
    name: 'L-Shaped Bench',
    desc: 'Corner bench with two wings',
    iconLabel: 'l-shape',
    fields: [
      { key: 'length_a', label: 'Length A', default: 60, unit: '"', step: 1 },
      { key: 'length_b', label: 'Length B', default: 48, unit: '"', step: 1 },
      { key: 'depth', label: 'Depth', default: 18, unit: '"', step: 0.5 },
      { key: 'height', label: 'Height', default: 18, unit: '"', step: 0.5 },
      { key: 'corner_type', label: 'Corner Type', default: 'square', type: 'select', options: ['square', 'rounded'] },
    ],
    edges: ['back_a', 'back_b', 'left', 'right'],
    sections: ['section_a', 'section_b'],
  },
  {
    id: 'u_booth',
    name: 'U-Shaped Booth',
    desc: 'Three-sided booth seating',
    iconLabel: 'u-shape',
    fields: [
      { key: 'length_a', label: 'Length A (Back)', default: 72, unit: '"', step: 1 },
      { key: 'length_b', label: 'Length B (Left)', default: 48, unit: '"', step: 1 },
      { key: 'length_c', label: 'Length C (Right)', default: 48, unit: '"', step: 1 },
      { key: 'depth', label: 'Depth', default: 18, unit: '"', step: 0.5 },
      { key: 'height', label: 'Height', default: 18, unit: '"', step: 0.5 },
    ],
    edges: ['back', 'left_outer', 'right_outer'],
    sections: ['section_back', 'section_left', 'section_right'],
  },
  {
    id: 'curved_banquette',
    name: 'Curved Banquette',
    desc: 'Curved arc seating',
    iconLabel: 'arc',
    fields: [
      { key: 'radius', label: 'Radius', default: 36, unit: '"', step: 1 },
      { key: 'arc_degrees', label: 'Arc Degrees', default: 180, type: 'slider', min: 90, max: 360, step: 5 },
      { key: 'depth', label: 'Depth', default: 18, unit: '"', step: 0.5 },
      { key: 'height', label: 'Height', default: 18, unit: '"', step: 0.5 },
    ],
    edges: ['outer', 'left', 'right'],
    sections: ['main'],
  },
  {
    id: 'semicircle',
    name: 'Semicircle',
    desc: 'Half-round bench or ottoman',
    iconLabel: 'semicircle',
    fields: [
      { key: 'diameter', label: 'Diameter', default: 48, unit: '"', step: 1 },
      { key: 'height', label: 'Height', default: 18, unit: '"', step: 0.5 },
    ],
    edges: ['flat', 'curved'],
    sections: ['main'],
  },
  {
    id: 'round_ottoman',
    name: 'Round Ottoman',
    desc: 'Full circle ottoman or pouf',
    iconLabel: 'circle',
    fields: [
      { key: 'diameter', label: 'Diameter', default: 36, unit: '"', step: 1 },
      { key: 'height', label: 'Height', default: 16, unit: '"', step: 0.5 },
    ],
    edges: [],
    sections: ['main'],
  },
];

/* ── Shape Icon SVGs ─────────────────────────────────────────── */
function ShapeIcon({ type, size = 32 }: { type: string; size?: number }) {
  const s = size;
  const stroke = '#b8960c';
  const sw = 2.5;
  switch (type) {
    case 'straight':
      return (
        <svg width={s} height={s} viewBox="0 0 32 32" fill="none">
          <line x1="4" y1="16" x2="28" y2="16" stroke={stroke} strokeWidth={sw} strokeLinecap="round" />
        </svg>
      );
    case 'l-shape':
      return (
        <svg width={s} height={s} viewBox="0 0 32 32" fill="none">
          <polyline points="4,6 4,26 26,26" stroke={stroke} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" fill="none" />
        </svg>
      );
    case 'u-shape':
      return (
        <svg width={s} height={s} viewBox="0 0 32 32" fill="none">
          <polyline points="4,6 4,26 28,26 28,6" stroke={stroke} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" fill="none" />
        </svg>
      );
    case 'arc':
      return (
        <svg width={s} height={s} viewBox="0 0 32 32" fill="none">
          <path d="M 4 24 Q 16 2 28 24" stroke={stroke} strokeWidth={sw} strokeLinecap="round" fill="none" />
        </svg>
      );
    case 'semicircle':
      return (
        <svg width={s} height={s} viewBox="0 0 32 32" fill="none">
          <path d="M 4 20 A 12 12 0 0 1 28 20" stroke={stroke} strokeWidth={sw} strokeLinecap="round" fill="none" />
          <line x1="4" y1="20" x2="28" y2="20" stroke={stroke} strokeWidth={sw} strokeLinecap="round" />
        </svg>
      );
    case 'circle':
      return (
        <svg width={s} height={s} viewBox="0 0 32 32" fill="none">
          <circle cx="16" cy="16" r="11" stroke={stroke} strokeWidth={sw} fill="none" />
        </svg>
      );
    default:
      return <Square className="w-8 h-8" style={{ color: stroke }} />;
  }
}

/* ── Helpers ──────────────────────────────────────────────────── */
function defaultsForShape(shape: ShapePreset): Record<string, any> {
  const vals: Record<string, any> = {};
  shape.fields.forEach((f) => { vals[f.key] = f.default; });
  return vals;
}

function edgeLabelFriendly(edge: string): string {
  return edge.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/* ── SVG Preview Generator (client-side) ─────────────────────── */
function generatePreviewSvg(
  shape: ShapePreset,
  dims: Record<string, any>,
  seatbacks: Record<string, boolean>,
  cushionCounts: Record<string, number>,
): string {
  const W = 400;
  const H = 300;
  const pad = 40;
  const seatColor = '#fdf9ef';
  const strokeColor = '#b8960c';
  const backColor = '#e8dcc8';
  const dividerColor = '#d4cfc5';
  const textColor = '#666';
  const seatbackH = 12;

  let svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" style="font-family:sans-serif">`;
  svg += `<rect width="${W}" height="${H}" fill="white" rx="8"/>`;

  switch (shape.id) {
    case 'straight_bench': {
      const len = dims.length || 48;
      const dep = dims.depth || 18;
      const scale = Math.min((W - pad * 2) / len, (H - pad * 2) / dep);
      const rw = len * scale;
      const rh = dep * scale;
      const x = (W - rw) / 2;
      const y = (H - rh) / 2;
      svg += `<rect x="${x}" y="${y}" width="${rw}" height="${rh}" fill="${seatColor}" stroke="${strokeColor}" stroke-width="2" rx="3"/>`;
      // Seatbacks
      if (seatbacks['back']) svg += `<rect x="${x}" y="${y - seatbackH}" width="${rw}" height="${seatbackH}" fill="${backColor}" stroke="${strokeColor}" stroke-width="1.5" rx="2"/>`;
      if (seatbacks['left']) svg += `<rect x="${x - seatbackH}" y="${y}" width="${seatbackH}" height="${rh}" fill="${backColor}" stroke="${strokeColor}" stroke-width="1.5" rx="2"/>`;
      if (seatbacks['right']) svg += `<rect x="${x + rw}" y="${y}" width="${seatbackH}" height="${rh}" fill="${backColor}" stroke="${strokeColor}" stroke-width="1.5" rx="2"/>`;
      // Cushion dividers
      const cc = cushionCounts['main'] || 1;
      if (cc > 1) {
        for (let i = 1; i < cc; i++) {
          const dx = x + (rw / cc) * i;
          svg += `<line x1="${dx}" y1="${y + 4}" x2="${dx}" y2="${y + rh - 4}" stroke="${dividerColor}" stroke-width="1.5" stroke-dasharray="4,3"/>`;
        }
      }
      // Dimension annotations
      svg += `<text x="${x + rw / 2}" y="${y + rh + 20}" text-anchor="middle" font-size="11" fill="${textColor}">${len}"</text>`;
      svg += `<text x="${x - 16}" y="${y + rh / 2 + 4}" text-anchor="middle" font-size="11" fill="${textColor}" transform="rotate(-90 ${x - 16} ${y + rh / 2})">${dep}"</text>`;
      break;
    }
    case 'l_bench': {
      const la = dims.length_a || 60;
      const lb = dims.length_b || 48;
      const dep = dims.depth || 18;
      const totalW = la;
      const totalH = lb;
      const scale = Math.min((W - pad * 2) / totalW, (H - pad * 2) / totalH);
      const sw = la * scale;
      const sh = lb * scale;
      const dw = dep * scale;
      const ox = (W - sw) / 2;
      const oy = (H - sh) / 2;
      // Horizontal arm
      svg += `<rect x="${ox}" y="${oy + sh - dw}" width="${sw}" height="${dw}" fill="${seatColor}" stroke="${strokeColor}" stroke-width="2" rx="3"/>`;
      // Vertical arm
      svg += `<rect x="${ox}" y="${oy}" width="${dw}" height="${sh - dw}" fill="${seatColor}" stroke="${strokeColor}" stroke-width="2" rx="3"/>`;
      // Corner fill
      if (dims.corner_type === 'rounded') {
        svg += `<circle cx="${ox + dw}" cy="${oy + sh - dw}" r="${dw * 0.3}" fill="${seatColor}" stroke="${strokeColor}" stroke-width="1"/>`;
      }
      // Seatbacks
      if (seatbacks['back_a']) svg += `<rect x="${ox}" y="${oy + sh}" width="${sw}" height="${seatbackH}" fill="${backColor}" stroke="${strokeColor}" stroke-width="1.5" rx="2"/>`;
      if (seatbacks['back_b']) svg += `<rect x="${ox - seatbackH}" y="${oy}" width="${seatbackH}" height="${sh}" fill="${backColor}" stroke="${strokeColor}" stroke-width="1.5" rx="2"/>`;
      // Cushion dividers section A (horizontal)
      const ccA = cushionCounts['section_a'] || 1;
      if (ccA > 1) {
        for (let i = 1; i < ccA; i++) {
          const dx = ox + (sw / ccA) * i;
          svg += `<line x1="${dx}" y1="${oy + sh - dw + 4}" x2="${dx}" y2="${oy + sh - 4}" stroke="${dividerColor}" stroke-width="1.5" stroke-dasharray="4,3"/>`;
        }
      }
      // Cushion dividers section B (vertical)
      const ccB = cushionCounts['section_b'] || 1;
      if (ccB > 1) {
        for (let i = 1; i < ccB; i++) {
          const dy = oy + ((sh - dw) / ccB) * i;
          svg += `<line x1="${ox + 4}" y1="${dy}" x2="${ox + dw - 4}" y2="${dy}" stroke="${dividerColor}" stroke-width="1.5" stroke-dasharray="4,3"/>`;
        }
      }
      // Annotations
      svg += `<text x="${ox + sw / 2}" y="${oy + sh + 28}" text-anchor="middle" font-size="11" fill="${textColor}">${la}" (A)</text>`;
      svg += `<text x="${ox + sw + 14}" y="${oy + sh / 2}" text-anchor="middle" font-size="11" fill="${textColor}" transform="rotate(-90 ${ox + sw + 14} ${oy + sh / 2})">${lb}" (B)</text>`;
      break;
    }
    case 'u_booth': {
      const la = dims.length_a || 72;
      const lb = dims.length_b || 48;
      const lc = dims.length_c || 48;
      const dep = dims.depth || 18;
      const maxSide = Math.max(lb, lc);
      const totalW = la;
      const totalH = maxSide;
      const scale = Math.min((W - pad * 2) / totalW, (H - pad * 2) / totalH);
      const sw = la * scale;
      const sh = maxSide * scale;
      const dw = dep * scale;
      const lbH = lb * scale;
      const lcH = lc * scale;
      const ox = (W - sw) / 2;
      const oy = (H - sh) / 2;
      // Bottom (back)
      svg += `<rect x="${ox}" y="${oy + sh - dw}" width="${sw}" height="${dw}" fill="${seatColor}" stroke="${strokeColor}" stroke-width="2" rx="3"/>`;
      // Left
      svg += `<rect x="${ox}" y="${oy + sh - lbH}" width="${dw}" height="${lbH - dw}" fill="${seatColor}" stroke="${strokeColor}" stroke-width="2" rx="3"/>`;
      // Right
      svg += `<rect x="${ox + sw - dw}" y="${oy + sh - lcH}" width="${dw}" height="${lcH - dw}" fill="${seatColor}" stroke="${strokeColor}" stroke-width="2" rx="3"/>`;
      // Seatbacks
      if (seatbacks['back']) svg += `<rect x="${ox}" y="${oy + sh}" width="${sw}" height="${seatbackH}" fill="${backColor}" stroke="${strokeColor}" stroke-width="1.5" rx="2"/>`;
      if (seatbacks['left_outer']) svg += `<rect x="${ox - seatbackH}" y="${oy + sh - lbH}" width="${seatbackH}" height="${lbH}" fill="${backColor}" stroke="${strokeColor}" stroke-width="1.5" rx="2"/>`;
      if (seatbacks['right_outer']) svg += `<rect x="${ox + sw}" y="${oy + sh - lcH}" width="${seatbackH}" height="${lcH}" fill="${backColor}" stroke="${strokeColor}" stroke-width="1.5" rx="2"/>`;
      // Annotations
      svg += `<text x="${ox + sw / 2}" y="${oy + sh + 28}" text-anchor="middle" font-size="11" fill="${textColor}">${la}" (A)</text>`;
      svg += `<text x="${ox - 20}" y="${oy + sh - lbH / 2}" text-anchor="middle" font-size="11" fill="${textColor}" transform="rotate(-90 ${ox - 20} ${oy + sh - lbH / 2})">${lb}" (B)</text>`;
      svg += `<text x="${ox + sw + 20}" y="${oy + sh - lcH / 2}" text-anchor="middle" font-size="11" fill="${textColor}" transform="rotate(-90 ${ox + sw + 20} ${oy + sh - lcH / 2})">${lc}" (C)</text>`;
      break;
    }
    case 'curved_banquette': {
      const r = dims.radius || 36;
      const deg = dims.arc_degrees || 180;
      const dep = dims.depth || 18;
      const scale = Math.min((W - pad * 2) / (r * 2 + dep * 2), (H - pad * 2) / (r + dep));
      const outerR = (r + dep) * scale;
      const innerR = r * scale;
      const cx = W / 2;
      const cy = H * 0.6;
      const startAngle = Math.PI + (Math.PI - (deg * Math.PI / 180)) / 2;
      const endAngle = startAngle + (deg * Math.PI / 180);
      const outerX1 = cx + outerR * Math.cos(startAngle);
      const outerY1 = cy + outerR * Math.sin(startAngle);
      const outerX2 = cx + outerR * Math.cos(endAngle);
      const outerY2 = cy + outerR * Math.sin(endAngle);
      const innerX1 = cx + innerR * Math.cos(startAngle);
      const innerY1 = cy + innerR * Math.sin(startAngle);
      const innerX2 = cx + innerR * Math.cos(endAngle);
      const innerY2 = cy + innerR * Math.sin(endAngle);
      const largeArc = deg > 180 ? 1 : 0;
      svg += `<path d="M${outerX1},${outerY1} A${outerR},${outerR} 0 ${largeArc} 1 ${outerX2},${outerY2} L${innerX2},${innerY2} A${innerR},${innerR} 0 ${largeArc} 0 ${innerX1},${innerY1} Z" fill="${seatColor}" stroke="${strokeColor}" stroke-width="2"/>`;
      // Seatback on outer edge
      if (seatbacks['outer']) {
        const sbR = outerR + seatbackH;
        const sbX1 = cx + sbR * Math.cos(startAngle);
        const sbY1 = cy + sbR * Math.sin(startAngle);
        const sbX2 = cx + sbR * Math.cos(endAngle);
        const sbY2 = cy + sbR * Math.sin(endAngle);
        svg += `<path d="M${outerX1},${outerY1} A${outerR},${outerR} 0 ${largeArc} 1 ${outerX2},${outerY2} L${sbX2},${sbY2} A${sbR},${sbR} 0 ${largeArc} 0 ${sbX1},${sbY1} Z" fill="${backColor}" stroke="${strokeColor}" stroke-width="1.5"/>`;
      }
      svg += `<text x="${cx}" y="${H - 8}" text-anchor="middle" font-size="11" fill="${textColor}">R${r}" / ${deg}°</text>`;
      break;
    }
    case 'semicircle': {
      const dia = dims.diameter || 48;
      const r = dia / 2;
      const scale = Math.min((W - pad * 2) / dia, (H - pad * 2) / r);
      const sr = r * scale;
      const cx = W / 2;
      const cy = H * 0.55;
      svg += `<path d="M${cx - sr},${cy} A${sr},${sr} 0 0 1 ${cx + sr},${cy} Z" fill="${seatColor}" stroke="${strokeColor}" stroke-width="2"/>`;
      // Seatback on flat edge
      if (seatbacks['flat']) {
        svg += `<rect x="${cx - sr}" y="${cy}" width="${sr * 2}" height="${seatbackH}" fill="${backColor}" stroke="${strokeColor}" stroke-width="1.5" rx="2"/>`;
      }
      // Seatback on curved edge
      if (seatbacks['curved']) {
        const sbR = sr + seatbackH;
        svg += `<path d="M${cx - sr},${cy} A${sr},${sr} 0 0 1 ${cx + sr},${cy} L${cx + sbR},${cy} A${sbR},${sbR} 0 0 0 ${cx - sbR},${cy} Z" fill="${backColor}" stroke="${strokeColor}" stroke-width="1.5"/>`;
      }
      svg += `<text x="${cx}" y="${cy + 28}" text-anchor="middle" font-size="11" fill="${textColor}">${dia}"</text>`;
      break;
    }
    case 'round_ottoman': {
      const dia = dims.diameter || 36;
      const scale = Math.min((W - pad * 2) / dia, (H - pad * 2) / dia);
      const sr = (dia / 2) * scale;
      const cx = W / 2;
      const cy = H / 2;
      svg += `<circle cx="${cx}" cy="${cy}" r="${sr}" fill="${seatColor}" stroke="${strokeColor}" stroke-width="2"/>`;
      svg += `<text x="${cx}" y="${cy + sr + 18}" text-anchor="middle" font-size="11" fill="${textColor}">${dia}" dia</text>`;
      break;
    }
  }

  svg += '</svg>';
  return svg;
}

/* ── Component ───────────────────────────────────────────────── */
export default function CustomShapeBuilder({ onSave }: CustomShapeBuilderProps) {
  const [selectedShape, setSelectedShape] = useState<string>('straight_bench');
  const [formValues, setFormValues] = useState<Record<string, any>>(() =>
    defaultsForShape(SHAPES[0])
  );
  const [seatbacks, setSeatbacks] = useState<Record<string, boolean>>({});
  const [seatbackHeight, setSeatbackHeight] = useState<number>(18);
  const [cushionCounts, setCushionCounts] = useState<Record<string, number>>({});
  const [result, setResult] = useState<CalculationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeShape = SHAPES.find((s) => s.id === selectedShape)!;

  /* Reset form when shape changes */
  useEffect(() => {
    const shape = SHAPES.find((s) => s.id === selectedShape);
    if (shape) {
      setFormValues(defaultsForShape(shape));
      setSeatbacks({});
      const cc: Record<string, number> = {};
      shape.sections.forEach((s) => { cc[s] = 1; });
      setCushionCounts(cc);
      setResult(null);
      setError(null);
    }
  }, [selectedShape]);

  /* Field change handler */
  const handleField = useCallback((key: string, value: any) => {
    setFormValues((prev) => ({ ...prev, [key]: value }));
  }, []);

  /* Toggle seatback */
  const toggleSeatback = useCallback((edge: string) => {
    setSeatbacks((prev) => ({ ...prev, [edge]: !prev[edge] }));
  }, []);

  /* Update cushion count */
  const setCushionCount = useCallback((section: string, count: number) => {
    setCushionCounts((prev) => ({ ...prev, [section]: Math.max(1, Math.min(8, count)) }));
  }, []);

  /* Live SVG preview */
  const previewSvg = useMemo(() => {
    return generatePreviewSvg(activeShape, formValues, seatbacks, cushionCounts);
  }, [activeShape, formValues, seatbacks, cushionCounts]);

  /* Calculate */
  const calculate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = `${API}/custom-shapes/calculate`;
      const body = {
        shape_type: selectedShape,
        dimensions: { ...formValues },
        seatbacks,
        seatback_height: seatbackHeight,
        cushion_counts: cushionCounts,
      };

      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(`API ${res.status}: ${msg}`);
      }
      const data: CalculationResult = await res.json();
      setResult(data);
    } catch (e: any) {
      setError(e.message || 'Calculation failed');
    } finally {
      setLoading(false);
    }
  }, [selectedShape, formValues, seatbacks, seatbackHeight, cushionCounts]);

  /* Reset */
  const reset = useCallback(() => {
    setResult(null);
    setError(null);
    setFormValues(defaultsForShape(activeShape));
    setSeatbacks({});
    const cc: Record<string, number> = {};
    activeShape.sections.forEach((s) => { cc[s] = 1; });
    setCushionCounts(cc);
  }, [activeShape]);

  return (
    <div className="min-h-screen p-6" style={{ background: '#faf9f7' }}>
      {/* ── Header ────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Ruler className="w-6 h-6" style={{ color: '#b8960c' }} />
          <h1 className="text-2xl font-bold text-gray-900">Custom Shape Builder</h1>
        </div>
        <button
          onClick={reset}
          className="flex items-center gap-2 px-4 py-2 rounded-xl border border-[#ece8e0] bg-white
                     hover:bg-gray-50 text-sm font-medium text-gray-700 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Reset
        </button>
      </div>

      {/* ── Shape Selector ────────────────────────────────── */}
      <div className="mb-6">
        <div className="section-label text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
          Select Shape
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {SHAPES.map((s) => (
            <button
              key={s.id}
              onClick={() => setSelectedShape(s.id)}
              className={`empire-card p-4 rounded-xl border-2 text-left transition-all ${
                selectedShape === s.id
                  ? 'border-[#b8960c] bg-[#fdf9ef] shadow-md'
                  : 'border-[#ece8e0] bg-white hover:border-[#d4cfc5] hover:shadow-sm'
              }`}
            >
              <div className="mb-1">
                <ShapeIcon type={s.iconLabel} />
              </div>
              <div className="font-semibold text-gray-900 text-sm">{s.name}</div>
              <div className="text-xs text-gray-500 mt-0.5">{s.desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* ── Main Grid: Form + Preview ─────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Left: Input Form */}
        <div className="empire-card bg-white rounded-xl border border-[#ece8e0] p-5">
          <div className="section-label text-xs font-semibold uppercase tracking-wider text-gray-500 mb-4 flex items-center gap-2">
            <Ruler className="w-4 h-4" style={{ color: '#b8960c' }} />
            Dimensions &amp; Options
          </div>

          {/* Dynamic Fields */}
          <div className="space-y-3">
            {activeShape.fields.map((field) => (
              <div key={field.key}>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {field.label}
                  {field.unit && <span className="text-gray-400 ml-1">{field.unit}</span>}
                </label>

                {field.type === 'select' ? (
                  <select
                    value={formValues[field.key]}
                    onChange={(e) => handleField(field.key, e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-[#ece8e0] focus:border-[#b8960c]
                               focus:ring-1 focus:ring-[#b8960c] outline-none text-sm bg-white transition-colors"
                  >
                    {field.options!.map((opt) => (
                      <option key={String(opt)} value={opt}>{String(opt)}</option>
                    ))}
                  </select>
                ) : field.type === 'slider' ? (
                  <div className="flex items-center gap-3">
                    <input
                      type="range"
                      value={formValues[field.key]}
                      onChange={(e) => handleField(field.key, Number(e.target.value))}
                      min={field.min || 0}
                      max={field.max || 360}
                      step={field.step || 5}
                      className="flex-1 accent-[#b8960c]"
                    />
                    <span className="text-sm font-medium text-gray-700 w-12 text-right">
                      {formValues[field.key]}°
                    </span>
                  </div>
                ) : (
                  <input
                    type="number"
                    value={formValues[field.key]}
                    onChange={(e) => handleField(field.key, Number(e.target.value))}
                    step={field.step || 0.25}
                    min={field.min || 0}
                    className="w-full px-3 py-2 rounded-xl border border-[#ece8e0] focus:border-[#b8960c]
                               focus:ring-1 focus:ring-[#b8960c] outline-none text-sm transition-colors"
                  />
                )}
              </div>
            ))}
          </div>

          {/* ── Seatback Toggles ──────────────────────────────── */}
          {activeShape.edges.length > 0 && (
            <div className="mt-5 pt-4 border-t border-[#ece8e0]">
              <div className="section-label text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
                Seatback Edges
              </div>
              <div className="flex flex-wrap gap-2 mb-3">
                {activeShape.edges.map((edge) => (
                  <button
                    key={edge}
                    onClick={() => toggleSeatback(edge)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      seatbacks[edge]
                        ? 'bg-[#b8960c] text-white shadow-sm'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {edgeLabelFriendly(edge)}
                  </button>
                ))}
              </div>
              {Object.values(seatbacks).some(Boolean) && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Seatback Height <span className="text-gray-400">"</span>
                  </label>
                  <input
                    type="number"
                    value={seatbackHeight}
                    onChange={(e) => setSeatbackHeight(Number(e.target.value))}
                    step={0.5}
                    min={6}
                    max={36}
                    className="w-full px-3 py-2 rounded-xl border border-[#ece8e0] focus:border-[#b8960c]
                               focus:ring-1 focus:ring-[#b8960c] outline-none text-sm transition-colors"
                  />
                </div>
              )}
            </div>
          )}

          {/* ── Cushion Counts ────────────────────────────────── */}
          {activeShape.sections.length > 1 && (
            <div className="mt-5 pt-4 border-t border-[#ece8e0]">
              <div className="section-label text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
                Cushion Count per Section
              </div>
              <div className="space-y-2">
                {activeShape.sections.map((section) => (
                  <div key={section} className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700">
                      {edgeLabelFriendly(section)}
                    </span>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setCushionCount(section, (cushionCounts[section] || 1) - 1)}
                        className="w-7 h-7 rounded-lg border border-[#ece8e0] flex items-center justify-center
                                   hover:bg-gray-50 text-gray-600 transition-colors"
                      >
                        <Minus className="w-3 h-3" />
                      </button>
                      <span className="text-sm font-semibold text-gray-900 w-6 text-center">
                        {cushionCounts[section] || 1}
                      </span>
                      <button
                        onClick={() => setCushionCount(section, (cushionCounts[section] || 1) + 1)}
                        className="w-7 h-7 rounded-lg border border-[#ece8e0] flex items-center justify-center
                                   hover:bg-gray-50 text-gray-600 transition-colors text-lg"
                      >
                        +
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Single-section cushion count ──────────────────── */}
          {activeShape.sections.length === 1 && activeShape.id !== 'round_ottoman' && (
            <div className="mt-5 pt-4 border-t border-[#ece8e0]">
              <div className="section-label text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">
                Cushion Count
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCushionCount('main', (cushionCounts['main'] || 1) - 1)}
                  className="w-7 h-7 rounded-lg border border-[#ece8e0] flex items-center justify-center
                             hover:bg-gray-50 text-gray-600 transition-colors"
                >
                  <Minus className="w-3 h-3" />
                </button>
                <span className="text-sm font-semibold text-gray-900 w-6 text-center">
                  {cushionCounts['main'] || 1}
                </span>
                <button
                  onClick={() => setCushionCount('main', (cushionCounts['main'] || 1) + 1)}
                  className="w-7 h-7 rounded-lg border border-[#ece8e0] flex items-center justify-center
                             hover:bg-gray-50 text-gray-600 transition-colors text-lg"
                >
                  +
                </button>
              </div>
            </div>
          )}

          {/* ── Action Buttons ────────────────────────────────── */}
          <div className="flex gap-3 mt-6">
            <button
              onClick={calculate}
              disabled={loading}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
                         text-white font-medium text-sm transition-all disabled:opacity-50"
              style={{ background: '#b8960c' }}
            >
              {loading ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Scissors className="w-4 h-4" />
              )}
              {loading ? 'Calculating...' : 'Calculate'}
            </button>
            {result && (
              <button
                onClick={() => alert('PDF download coming soon')}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-[#b8960c]
                           text-[#b8960c] font-medium text-sm hover:bg-[#fdf9ef] transition-colors"
              >
                <Download className="w-4 h-4" />
                PDF
              </button>
            )}
          </div>

          {/* Save as Template */}
          {result && onSave && (
            <button
              className="w-full mt-3 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl
                         bg-[#16a34a] text-white font-medium text-sm
                         hover:bg-[#15803d] transition-colors"
              onClick={() => onSave(selectedShape, { ...formValues, seatbacks, seatback_height: seatbackHeight, cushion_counts: cushionCounts }, result)}
            >
              <Save className="w-4 h-4" />
              Save as Template
            </button>
          )}

          {/* Error */}
          {error && (
            <div className="mt-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm flex items-start gap-2">
              <Info className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Right: SVG Preview */}
        <div className="empire-card bg-white rounded-xl border border-[#ece8e0] p-5">
          <div className="section-label text-xs font-semibold uppercase tracking-wider text-gray-500 mb-4 flex items-center gap-2">
            <FileText className="w-4 h-4" style={{ color: '#b8960c' }} />
            Preview
          </div>

          <div
            className="flex items-center justify-center min-h-[300px]"
            dangerouslySetInnerHTML={{ __html: result?.svg || previewSvg }}
          />

          {!result && (
            <p className="text-xs text-gray-400 text-center mt-2">
              Live preview — click Calculate to get measurements
            </p>
          )}
        </div>
      </div>

      {/* ── Output Section (after calculation) ────────────── */}
      {result && (
        <div className="empire-card bg-white rounded-xl border border-[#ece8e0] p-5 mb-6">
          <div className="section-label text-xs font-semibold uppercase tracking-wider text-gray-500 mb-4 flex items-center gap-2">
            <Ruler className="w-4 h-4" style={{ color: '#b8960c' }} />
            Calculation Results
          </div>

          <div className="grid grid-cols-3 gap-6 mb-5">
            <div className="text-center">
              <div className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">Linear Feet</div>
              <div className="text-3xl font-bold" style={{ color: '#b8960c' }}>
                {result.linear_feet.toFixed(1)}
              </div>
              <div className="text-xs text-gray-500">ft</div>
            </div>
            <div className="text-center">
              <div className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">Square Footage</div>
              <div className="text-3xl font-bold" style={{ color: '#b8960c' }}>
                {result.square_footage.toFixed(1)}
              </div>
              <div className="text-xs text-gray-500">sq ft</div>
            </div>
            <div className="text-center">
              <div className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">Fabric Yardage</div>
              <div className="text-3xl font-bold" style={{ color: '#b8960c' }}>
                {result.fabric_yardage_54.toFixed(2)}
              </div>
              <div className="text-xs text-gray-500">yards (54" wide)</div>
            </div>
          </div>

          {/* Construction Notes */}
          {result.construction_notes && result.construction_notes.length > 0 && (
            <div className="pt-4 border-t border-[#ece8e0]">
              <div className="section-label text-xs font-semibold uppercase tracking-wider text-gray-500 mb-2 flex items-center gap-2">
                <Info className="w-3.5 h-3.5" style={{ color: '#b8960c' }} />
                Construction Notes
              </div>
              <ul className="space-y-1.5">
                {result.construction_notes.map((note, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="text-[#b8960c] mt-0.5">&#8226;</span>
                    <span>{note}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* ── Pieces List ───────────────────────────────────── */}
      {result && result.pieces && result.pieces.length > 0 && (
        <div className="empire-card bg-white rounded-xl border border-[#ece8e0] p-5">
          <div className="section-label text-xs font-semibold uppercase tracking-wider text-gray-500 mb-4 flex items-center gap-2">
            <Scissors className="w-4 h-4" style={{ color: '#b8960c' }} />
            Pieces
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {result.pieces.map((piece, i) => (
              <div
                key={i}
                className="border border-[#ece8e0] rounded-xl p-3 text-center hover:shadow-sm transition-shadow"
              >
                <div className="font-semibold text-sm text-gray-900">{piece.name}</div>
                <div className="text-xs text-gray-500 mt-1">
                  {piece.width}&quot; x {piece.height}&quot;
                </div>
                <div className="text-xs font-medium mt-1" style={{ color: '#b8960c' }}>
                  Cut {piece.quantity}
                </div>
                {piece.notes && (
                  <div className="text-xs text-gray-400 mt-1 italic">{piece.notes}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
