'use client';

import { useState, useMemo, useCallback } from 'react';
import dynamic from 'next/dynamic';
import {
  Check,
  ChevronDown,
  ChevronUp,
  Sofa,
  Ruler,
  Shapes,
  Layers,
  Scissors,
  Lock,
  Grid3X3,
  Palette,
  Calculator,
  Printer,
  FileText,
  Plus,
  Save,
} from 'lucide-react';

const CushionDiagram = dynamic(() => import('./CushionDiagram'), { ssr: false });

/* ─── Types ─── */

interface MaterialCalculation {
  topPanel: number;
  bottomPanel: number;
  boxingStrip: number;
  weltStrips: number;
  totalFabricSqIn: number;
  totalFabricYards: number;
  weltCordYards: number;
  biasFabricYards: number;
  foamVolumeCuIn: number;
  foamVolumeCuFt: number;
  foamBoardFeet: number;
  zipperLength: number;
  surfaceAreaSqIn: number;
}

interface CostBreakdown {
  fabricCost: number;
  foamCost: number;
  weltCordCost: number;
  zipperCost: number;
  dacronCost: number;
  downCost: number;
  buttonCost: number;
  laborBase: number;
  laborComplexity: number;
  totalLabor: number;
  subtotalPerUnit: number;
  totalAll: number;
}

export interface CushionQuoteData {
  cushionType: string;
  dimensions: Record<string, number>;
  quantity: number;
  shape: string;
  style: string;
  fill: string;
  edge: string;
  closure: string;
  tufting: string;
  fabric: string;
  materials: MaterialCalculation;
  costs: CostBreakdown;
  totalPerUnit: number;
  totalAll: number;
}

export interface CushionTemplate {
  name: string;
  specs: Omit<CushionQuoteData, 'materials' | 'costs' | 'totalPerUnit' | 'totalAll'>;
}

interface CushionBuilderProps {
  onAddToQuote?: (data: CushionQuoteData) => void;
  onSaveTemplate?: (template: CushionTemplate) => void;
  initialTemplate?: CushionTemplate;
  compact?: boolean;
}

/* ─── Constants ─── */

const CUSHION_TYPES = [
  { id: 'seat_cushion', label: 'Seat Cushion' },
  { id: 'back_cushion', label: 'Back Cushion' },
  { id: 'bench_pad', label: 'Bench Pad' },
  { id: 'window_seat', label: 'Window Seat' },
  { id: 'throw_pillow', label: 'Throw Pillow' },
  { id: 'bolster', label: 'Bolster' },
  { id: 'floor_cushion', label: 'Floor Cushion' },
  { id: 'chaise_pad', label: 'Chaise Pad' },
  { id: 'round_cushion', label: 'Round Cushion' },
  { id: 'wedge_cushion', label: 'Wedge Cushion' },
  { id: 'custom', label: 'Custom Shape' },
] as const;

const SHAPE_OPTIONS = [
  { id: 'square_corners', label: 'Square Corners' },
  { id: 'rounded_corners', label: 'Rounded Corners' },
  { id: 'bullnose', label: 'Bullnose' },
  { id: 'waterfall', label: 'Waterfall' },
  { id: 't_cushion', label: 'T-Cushion' },
  { id: 'custom', label: 'Custom' },
] as const;

const STYLE_OPTIONS = [
  { id: 'knife_edge', label: 'Knife Edge' },
  { id: 'box_cushion', label: 'Box Cushion' },
  { id: 'turkish_corners', label: 'Turkish Corners' },
  { id: 'mock_box', label: 'Mock Box' },
  { id: 'waterfall_style', label: 'Waterfall Style' },
  { id: 'channel', label: 'Channel' },
  { id: 'tufted', label: 'Tufted' },
] as const;

const FILL_OPTIONS = [
  { id: 'foam_only', label: 'Foam Only' },
  { id: 'foam_dacron', label: 'Foam + Dacron Wrap' },
  { id: 'foam_down', label: 'Foam + Down Wrap' },
  { id: 'down_only', label: 'Down Only' },
  { id: 'polyfil', label: 'Polyfil' },
  { id: 'down_alternative', label: 'Down Alternative' },
  { id: 'spring_down', label: 'Spring Down' },
  { id: 'latex', label: 'Latex' },
  { id: 'memory_foam', label: 'Memory Foam' },
] as const;

const FOAM_DENSITIES = [
  { value: 1.2, label: '1.2 — Soft' },
  { value: 1.5, label: '1.5 — Medium' },
  { value: 1.8, label: '1.8 — Firm' },
  { value: 2.0, label: '2.0 — Extra Firm' },
] as const;

const FOAM_TYPES = [
  { id: 'HR', label: 'HR (High Resilience)' },
  { id: 'HD', label: 'HD (High Density)' },
  { id: 'Reflex', label: 'Reflex' },
] as const;

const WELT_OPTIONS = [
  { id: 'none', label: 'None' },
  { id: 'single_welt', label: 'Single Welt' },
  { id: 'double_welt', label: 'Double Welt' },
  { id: 'micro_welt', label: 'Micro Welt' },
  { id: 'flanged_welt', label: 'Flanged Welt' },
  { id: 'brush_fringe', label: 'Brush Fringe' },
  { id: 'gimp_braid', label: 'Gimp Braid' },
  { id: 'contrast_welt', label: 'Contrast Welt' },
] as const;

const CORD_SIZES = ['3/16"', '5/32"', '1/4"', '3/8"'] as const;

const FLANGE_OPTIONS = [
  { id: 'none', label: 'None' },
  { id: 'knife_edge_flange', label: 'Knife Edge Flange' },
  { id: 'brush_fringe_flange', label: 'Brush Fringe Flange' },
  { id: 'ruffle_flange', label: 'Ruffle Flange' },
  { id: 'contrast_flange', label: 'Contrast Flange' },
] as const;

const CLOSURE_OPTIONS = [
  { id: 'sewn_shut', label: 'Sewn Shut' },
  { id: 'zipper_hidden', label: 'Zipper (Hidden)' },
  { id: 'zipper_exposed', label: 'Zipper (Exposed)' },
  { id: 'velcro', label: 'Velcro' },
  { id: 'envelope_back', label: 'Envelope Back' },
] as const;

const ZIPPER_LOCATIONS = [
  { id: 'bottom', label: 'Bottom' },
  { id: 'back', label: 'Back' },
  { id: 'side', label: 'Side' },
  { id: 'l_shaped', label: 'L-Shaped' },
] as const;

const TUFTING_OPTIONS = [
  { id: 'none', label: 'None' },
  { id: 'button_tufted', label: 'Button Tufted' },
  { id: 'diamond_tufted', label: 'Diamond Tufted' },
  { id: 'biscuit_tufted', label: 'Biscuit Tufted' },
] as const;

const BUTTON_TYPES = [
  { id: 'self_covered', label: 'Self-Covered' },
  { id: 'metal', label: 'Metal' },
  { id: 'crystal', label: 'Crystal' },
  { id: 'wood', label: 'Wood' },
] as const;

const STEPS = [
  { key: 'type', label: 'Cushion Type', icon: Sofa },
  { key: 'dimensions', label: 'Dimensions', icon: Ruler },
  { key: 'shape', label: 'Shape & Style', icon: Shapes },
  { key: 'fill', label: 'Fill / Insert', icon: Layers },
  { key: 'edge', label: 'Edge Treatment', icon: Scissors },
  { key: 'closure', label: 'Closure', icon: Lock },
  { key: 'tufting', label: 'Tufting', icon: Grid3X3 },
  { key: 'fabric', label: 'Fabric', icon: Palette },
  { key: 'preview', label: 'Preview & Calculate', icon: Calculator },
] as const;

const DENSITY_PRICE: Record<number, number> = { 1.2: 3, 1.5: 4, 1.8: 5, 2.0: 6 };

/* ─── Shared Styles ─── */

const gold = '#b8960c';
const offWhite = '#f5f3ef';
const border = '#ece8e0';

const inputStyle: React.CSSProperties = {
  padding: '10px 12px',
  borderRadius: 8,
  border: `1px solid ${border}`,
  background: '#fff',
  fontSize: 14,
  outline: 'none',
  width: '100%',
};

const selectStyle: React.CSSProperties = { ...inputStyle, cursor: 'pointer' };

const labelStyle: React.CSSProperties = {
  fontSize: 12,
  fontWeight: 600,
  color: '#555',
  marginBottom: 4,
  display: 'block',
};

const gridCardStyle = (selected: boolean): React.CSSProperties => ({
  padding: '14px 12px',
  borderRadius: 10,
  border: `2px solid ${selected ? gold : border}`,
  background: selected ? '#fdf8eb' : '#fff',
  cursor: 'pointer',
  textAlign: 'center',
  fontSize: 13,
  fontWeight: selected ? 700 : 500,
  color: selected ? gold : '#333',
  transition: 'all 0.15s',
});

const goldBtnStyle: React.CSSProperties = {
  minHeight: 44,
  padding: '0 24px',
  borderRadius: 10,
  border: 'none',
  background: `linear-gradient(135deg, ${gold}, #d4a90e)`,
  color: '#fff',
  fontWeight: 700,
  fontSize: 14,
  cursor: 'pointer',
};

const outlineBtnStyle: React.CSSProperties = {
  minHeight: 44,
  padding: '0 20px',
  borderRadius: 10,
  border: `2px solid ${border}`,
  background: '#fff',
  color: '#555',
  fontWeight: 600,
  fontSize: 14,
  cursor: 'pointer',
};

/* ─── Component ─── */

export default function CushionBuilder({
  onAddToQuote,
  onSaveTemplate,
  initialTemplate,
  compact = false,
}: CushionBuilderProps) {
  const [currentStep, setCurrentStep] = useState(0);

  // Step 1 — Cushion Type
  const [cushionType, setCushionType] = useState(initialTemplate?.specs.cushionType ?? '');

  // Step 2 — Dimensions
  const [dims, setDims] = useState<Record<string, number>>(
    initialTemplate?.specs.dimensions ?? { width: 0, depth: 0, height: 0 }
  );
  const [quantity, setQuantity] = useState(initialTemplate?.specs.quantity ?? 1);

  // Step 3 — Shape & Style
  const [shape, setShape] = useState(initialTemplate?.specs.shape ?? 'square_corners');
  const [cornerRadius, setCornerRadius] = useState(2);
  const [style, setStyle] = useState(initialTemplate?.specs.style ?? 'box_cushion');

  // Step 4 — Fill
  const [fill, setFill] = useState(initialTemplate?.specs.fill ?? 'foam_dacron');
  const [foamDensity, setFoamDensity] = useState(1.8);
  const [foamType, setFoamType] = useState('HR');
  const [downPercent, setDownPercent] = useState(75);
  const [featherPercent, setFeatherPercent] = useState(25);

  // Step 5 — Edge
  const [welt, setWelt] = useState(initialTemplate?.specs.edge ?? 'single_welt');
  const [cordSize, setCordSize] = useState('3/16"');
  const [flange, setFlange] = useState('none');
  const [flangeWidth, setFlangeWidth] = useState(1);

  // Step 6 — Closure
  const [closure, setClosure] = useState(initialTemplate?.specs.closure ?? 'zipper_hidden');
  const [zipperLocation, setZipperLocation] = useState('bottom');

  // Step 7 — Tufting
  const [tufting, setTufting] = useState(initialTemplate?.specs.tufting ?? 'none');
  const [buttonRows, setButtonRows] = useState(3);
  const [buttonCols, setButtonCols] = useState(3);
  const [buttonType, setButtonType] = useState('self_covered');

  // Step 8 — Fabric
  const [fabricName, setFabricName] = useState(initialTemplate?.specs.fabric ?? '');
  const [fabricPrice, setFabricPrice] = useState(30);
  const [repeatH, setRepeatH] = useState(0);
  const [repeatV, setRepeatV] = useState(0);
  const [railroaded, setRailroaded] = useState(false);
  const [directionalNap, setDirectionalNap] = useState(false);
  const [fabricWidth, setFabricWidth] = useState(54);

  // Template save name
  const [templateName, setTemplateName] = useState(initialTemplate?.name ?? '');

  /* ─── Derived values ─── */

  const isRound = cushionType === 'round_cushion';
  const isBolster = cushionType === 'bolster';
  const isWedge = cushionType === 'wedge_cushion';
  const isTCushion = shape === 't_cushion';
  const isBoxStyle = ['box_cushion', 'turkish_corners', 'mock_box'].includes(style);
  const isKnifeEdge = style === 'knife_edge';
  const hasFoam = ['foam_only', 'foam_dacron', 'foam_down', 'latex', 'memory_foam'].includes(fill);
  const hasDacron = fill === 'foam_dacron';
  const hasDown = ['foam_down', 'down_only', 'spring_down'].includes(fill);
  const hasWelt = welt !== 'none';
  const hasZipper = closure === 'zipper_hidden' || closure === 'zipper_exposed';
  const hasTufting = tufting !== 'none';
  const buttonCount = hasTufting ? buttonRows * buttonCols : 0;
  const isTufted = style === 'tufted' || hasTufting;

  const w = dims.width || 0;
  const d = dims.depth || 0;
  const h = dims.height || dims.loft || 0;
  const diameter = dims.diameter || 0;
  const length = dims.length || 0;
  const frontH = dims.front_height || 0;
  const backH = dims.back_height || 0;

  /* ─── Material Calculation ─── */

  const materials = useMemo<MaterialCalculation>(() => {
    let topPanel = 0;
    let bottomPanel = 0;
    let boxingStrip = 0;
    let perimeter = 0;
    let surfaceArea = 0;
    let foamVolCuIn = 0;
    let longestEdge = 0;

    if (isRound) {
      const r = diameter / 2;
      const area = Math.PI * r * r;
      topPanel = area * 1.1; // seam allowance ~10%
      bottomPanel = topPanel;
      perimeter = Math.PI * diameter;
      surfaceArea = area * 2;
      foamVolCuIn = area * (h || 3);
      longestEdge = diameter;
    } else if (isBolster) {
      const r = diameter / 2;
      const circumference = Math.PI * diameter;
      topPanel = Math.PI * r * r * 1.1; // end cap
      bottomPanel = topPanel; // other end cap
      boxingStrip = (length + 1) * (circumference + 1);
      perimeter = circumference;
      surfaceArea = circumference * length + 2 * Math.PI * r * r;
      foamVolCuIn = Math.PI * r * r * length;
      longestEdge = length;
    } else if (isWedge) {
      topPanel = (w + 1) * (d + 1);
      bottomPanel = topPanel;
      const avgH = (frontH + backH) / 2;
      perimeter = 2 * (w + d);
      boxingStrip = perimeter * (avgH + 1);
      surfaceArea = w * d * 2;
      foamVolCuIn = w * d * avgH;
      longestEdge = Math.max(w, d);
    } else {
      topPanel = (w + 1) * (d + 1);
      bottomPanel = topPanel;
      perimeter = 2 * (w + d);
      boxingStrip = isBoxStyle ? perimeter * (h + 1) : 0;
      surfaceArea = w * d * 2;
      foamVolCuIn = w * d * (h || 3);
      longestEdge = Math.max(w, d);
    }

    // Welt strips
    const weltRuns = isBoxStyle ? 2 : 1;
    let totalWeltIn = hasWelt ? perimeter * weltRuns : 0;
    if (welt === 'double_welt') totalWeltIn *= 2;
    totalWeltIn *= 1.1; // 10% waste
    const weltYards = totalWeltIn / 36;
    const biasFabYards = (totalWeltIn * 1.5) / (fabricWidth * 36);
    const weltStripArea = biasFabYards * fabricWidth * 36; // back to sq inches for total

    let totalFabricSqIn = topPanel + bottomPanel + boxingStrip + weltStripArea;

    // T-cushion: +30%
    if (isTCushion) totalFabricSqIn *= 1.3;

    // Convert to linear yards
    let totalYards = totalFabricSqIn / (fabricWidth * 36);

    // Pattern repeat adjustment
    if (repeatV > 0) {
      const cutsNeeded = Math.ceil(totalYards * 36 / repeatV);
      totalYards = (cutsNeeded * repeatV) / 36;
    }

    // Foam oversized for compression fit
    const cutW = (isRound ? diameter : w) + 1;
    const cutD = (isRound ? diameter : isBolster ? length : d) + 1;
    const cutH = isWedge ? (frontH + backH) / 2 : h || 3;
    let foamVol: number;
    if (isRound) {
      foamVol = Math.PI * (cutW / 2) * (cutW / 2) * cutH;
    } else if (isBolster) {
      foamVol = Math.PI * ((diameter + 1) / 2) * ((diameter + 1) / 2) * (length + 1);
    } else {
      foamVol = cutW * cutD * cutH;
    }

    const zipperLength = longestEdge + 2;

    return {
      topPanel,
      bottomPanel,
      boxingStrip,
      weltStrips: weltStripArea,
      totalFabricSqIn,
      totalFabricYards: Math.ceil(totalYards * 100) / 100,
      weltCordYards: Math.ceil(weltYards * 100) / 100,
      biasFabricYards: Math.ceil(biasFabYards * 100) / 100,
      foamVolumeCuIn: foamVol,
      foamVolumeCuFt: foamVol / 1728,
      foamBoardFeet: foamVol / 144,
      zipperLength,
      surfaceAreaSqIn: surfaceArea,
    };
  }, [
    w, d, h, diameter, length, frontH, backH,
    isRound, isBolster, isWedge, isBoxStyle, isKnifeEdge, isTCushion,
    hasWelt, welt, fabricWidth, repeatV,
  ]);

  /* ─── Cost Calculation ─── */

  const costs = useMemo<CostBreakdown>(() => {
    const fabricCost = materials.totalFabricYards * fabricPrice;
    const foamCost = hasFoam ? materials.foamBoardFeet * (DENSITY_PRICE[foamDensity] ?? 4) : 0;
    const weltCordCost = hasWelt ? materials.weltCordYards * 2.5 : 0;
    const zipperCost = hasZipper ? 3.5 : 0;
    const dacronCost = hasDacron ? (materials.surfaceAreaSqIn / 1296) * 8 : 0;
    const downCost = hasDown ? materials.foamVolumeCuFt * 45 : 0;
    const bCost = buttonCount * 1.5;

    const laborBase = isKnifeEdge ? 35 : isBoxStyle ? 55 : isTufted ? 85 : 45;
    const laborComplexity = (hasWelt ? 10 : 0) + (hasTufting ? 25 : 0) + (isTCushion ? 15 : 0);
    const totalLabor = laborBase + laborComplexity;

    const subtotal = fabricCost + foamCost + weltCordCost + zipperCost + dacronCost + downCost + bCost + totalLabor;
    const totalAll = subtotal * quantity;

    return {
      fabricCost: r2(fabricCost),
      foamCost: r2(foamCost),
      weltCordCost: r2(weltCordCost),
      zipperCost: r2(zipperCost),
      dacronCost: r2(dacronCost),
      downCost: r2(downCost),
      buttonCost: r2(bCost),
      laborBase,
      laborComplexity,
      totalLabor,
      subtotalPerUnit: r2(subtotal),
      totalAll: r2(totalAll),
    };
  }, [
    materials, fabricPrice, hasFoam, foamDensity, hasWelt, hasZipper,
    hasDacron, hasDown, buttonCount, isKnifeEdge, isBoxStyle, isTufted,
    hasTufting, isTCushion, quantity,
  ]);

  /* ─── Step completion ─── */

  const stepComplete = useCallback(
    (idx: number): boolean => {
      switch (idx) {
        case 0: return !!cushionType;
        case 1: {
          if (isRound) return diameter > 0;
          if (isBolster) return diameter > 0 && length > 0;
          if (isWedge) return w > 0 && d > 0 && frontH > 0 && backH > 0;
          return w > 0 && d > 0;
        }
        case 2: return !!shape && !!style;
        case 3: return !!fill;
        case 4: return true; // always valid (none is fine)
        case 5: return !!closure;
        case 6: return true;
        case 7: return fabricPrice > 0 && fabricWidth > 0;
        case 8: return true;
        default: return false;
      }
    },
    [cushionType, isRound, isBolster, isWedge, diameter, length, w, d, frontH, backH, h, shape, style, fill, closure, fabricPrice, fabricWidth]
  );

  const canGoTo = (idx: number) => {
    if (idx <= currentStep) return true;
    for (let i = 0; i < idx; i++) {
      if (!stepComplete(i)) return false;
    }
    return true;
  };

  /* ─── Build quote data ─── */

  const buildQuoteData = (): CushionQuoteData => ({
    cushionType,
    dimensions: { ...dims },
    quantity,
    shape,
    style,
    fill,
    edge: welt,
    closure,
    tufting,
    fabric: fabricName,
    materials,
    costs,
    totalPerUnit: costs.subtotalPerUnit,
    totalAll: costs.totalAll,
  });

  /* ─── Render helpers ─── */

  const renderStepContent = (stepIdx: number) => {
    switch (stepIdx) {
      case 0:
        return (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10 }}>
            {CUSHION_TYPES.map((ct) => (
              <div
                key={ct.id}
                style={gridCardStyle(cushionType === ct.id)}
                onClick={() => {
                  setCushionType(ct.id);
                  // Reset dimensions when type changes
                  if (ct.id === 'round_cushion') setDims({ diameter: 0, height: 0 });
                  else if (ct.id === 'bolster') setDims({ length: 0, diameter: 0 });
                  else if (ct.id === 'wedge_cushion') setDims({ width: 0, depth: 0, front_height: 0, back_height: 0 });
                  else setDims({ width: 0, depth: 0, height: 0 });
                }}
              >
                {ct.label}
              </div>
            ))}
          </div>
        );

      case 1:
        return (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 16 }}>
            {isRound ? (
              <>
                <Field label="Diameter (in)" value={dims.diameter} onChange={(v) => setDims((p) => ({ ...p, diameter: v }))} />
                <Field label="Height / Loft (in)" value={dims.height} onChange={(v) => setDims((p) => ({ ...p, height: v }))} />
              </>
            ) : isBolster ? (
              <>
                <Field label="Length (in)" value={dims.length} onChange={(v) => setDims((p) => ({ ...p, length: v }))} />
                <Field label="Diameter (in)" value={dims.diameter} onChange={(v) => setDims((p) => ({ ...p, diameter: v }))} />
              </>
            ) : isWedge ? (
              <>
                <Field label="Width (in)" value={dims.width} onChange={(v) => setDims((p) => ({ ...p, width: v }))} />
                <Field label="Depth (in)" value={dims.depth} onChange={(v) => setDims((p) => ({ ...p, depth: v }))} />
                <Field label="Front Height (in)" value={dims.front_height} onChange={(v) => setDims((p) => ({ ...p, front_height: v }))} />
                <Field label="Back Height (in)" value={dims.back_height} onChange={(v) => setDims((p) => ({ ...p, back_height: v }))} />
              </>
            ) : (
              <>
                <Field label="Width (in)" value={dims.width} onChange={(v) => setDims((p) => ({ ...p, width: v }))} />
                <Field label="Depth (in)" value={dims.depth} onChange={(v) => setDims((p) => ({ ...p, depth: v }))} />
                <Field label="Height / Loft (in)" value={dims.height} onChange={(v) => setDims((p) => ({ ...p, height: v }))} />
              </>
            )}
            <Field label="Quantity" value={quantity} onChange={setQuantity} min={1} step={1} />
          </div>
        );

      case 2:
        return (
          <div className="flex flex-col gap-5">
            <div>
              <div style={{ ...labelStyle, marginBottom: 10 }}>Shape</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10 }}>
                {SHAPE_OPTIONS.map((s) => (
                  <div key={s.id} style={gridCardStyle(shape === s.id)} onClick={() => setShape(s.id)}>
                    {s.label}
                  </div>
                ))}
              </div>
              {shape === 'rounded_corners' && (
                <div style={{ marginTop: 12, maxWidth: 200 }}>
                  <Field label="Corner Radius (in)" value={cornerRadius} onChange={setCornerRadius} min={0.5} step={0.25} />
                </div>
              )}
            </div>
            <div>
              <div style={{ ...labelStyle, marginBottom: 10 }}>Style</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10 }}>
                {STYLE_OPTIONS.map((s) => (
                  <div key={s.id} style={gridCardStyle(style === s.id)} onClick={() => setStyle(s.id)}>
                    {s.label}
                  </div>
                ))}
              </div>
            </div>
          </div>
        );

      case 3:
        return (
          <div className="flex flex-col gap-5">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 10 }}>
              {FILL_OPTIONS.map((f) => (
                <div key={f.id} style={gridCardStyle(fill === f.id)} onClick={() => setFill(f.id)}>
                  {f.label}
                </div>
              ))}
            </div>
            {hasFoam && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16, padding: 16, background: offWhite, borderRadius: 10, border: `1px solid ${border}` }}>
                <div>
                  <label style={labelStyle}>Foam Density</label>
                  <select style={selectStyle} value={foamDensity} onChange={(e) => setFoamDensity(parseFloat(e.target.value))}>
                    {FOAM_DENSITIES.map((fd) => (
                      <option key={fd.value} value={fd.value}>{fd.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label style={labelStyle}>Foam Type</label>
                  <select style={selectStyle} value={foamType} onChange={(e) => setFoamType(e.target.value)}>
                    {FOAM_TYPES.map((ft) => (
                      <option key={ft.id} value={ft.id}>{ft.label}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}
            {hasDown && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, padding: 16, background: offWhite, borderRadius: 10, border: `1px solid ${border}`, maxWidth: 400 }}>
                <Field label="Down %" value={downPercent} onChange={(v) => { setDownPercent(v); setFeatherPercent(100 - v); }} min={0} max={100} step={5} />
                <Field label="Feather %" value={featherPercent} onChange={(v) => { setFeatherPercent(v); setDownPercent(100 - v); }} min={0} max={100} step={5} />
              </div>
            )}
          </div>
        );

      case 4:
        return (
          <div className="flex flex-col gap-5">
            <div>
              <div style={{ ...labelStyle, marginBottom: 10 }}>Welt / Edge</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10 }}>
                {WELT_OPTIONS.map((wo) => (
                  <div key={wo.id} style={gridCardStyle(welt === wo.id)} onClick={() => setWelt(wo.id)}>
                    {wo.label}
                  </div>
                ))}
              </div>
            </div>
            {hasWelt && (
              <div style={{ maxWidth: 240, padding: 16, background: offWhite, borderRadius: 10, border: `1px solid ${border}` }}>
                <label style={labelStyle}>Cord Size</label>
                <select style={selectStyle} value={cordSize} onChange={(e) => setCordSize(e.target.value)}>
                  {CORD_SIZES.map((cs) => (
                    <option key={cs} value={cs}>{cs}</option>
                  ))}
                </select>
              </div>
            )}
            <div>
              <div style={{ ...labelStyle, marginBottom: 10 }}>Flange (Pillows / Edge)</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10 }}>
                {FLANGE_OPTIONS.map((fo) => (
                  <div key={fo.id} style={gridCardStyle(flange === fo.id)} onClick={() => setFlange(fo.id)}>
                    {fo.label}
                  </div>
                ))}
              </div>
              {(flange === 'knife_edge_flange' || flange === 'ruffle_flange') && (
                <div style={{ marginTop: 12, maxWidth: 200 }}>
                  <Field label="Flange Width (in)" value={flangeWidth} onChange={setFlangeWidth} min={0.5} step={0.25} />
                </div>
              )}
            </div>
          </div>
        );

      case 5:
        return (
          <div className="flex flex-col gap-5">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10 }}>
              {CLOSURE_OPTIONS.map((co) => (
                <div key={co.id} style={gridCardStyle(closure === co.id)} onClick={() => setClosure(co.id)}>
                  {co.label}
                </div>
              ))}
            </div>
            {hasZipper && (
              <div style={{ maxWidth: 240, padding: 16, background: offWhite, borderRadius: 10, border: `1px solid ${border}` }}>
                <label style={labelStyle}>Zipper Location</label>
                <select style={selectStyle} value={zipperLocation} onChange={(e) => setZipperLocation(e.target.value)}>
                  {ZIPPER_LOCATIONS.map((zl) => (
                    <option key={zl.id} value={zl.id}>{zl.label}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
        );

      case 6:
        return (
          <div className="flex flex-col gap-5">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10 }}>
              {TUFTING_OPTIONS.map((to) => (
                <div key={to.id} style={gridCardStyle(tufting === to.id)} onClick={() => setTufting(to.id)}>
                  {to.label}
                </div>
              ))}
            </div>
            {hasTufting && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 16, padding: 16, background: offWhite, borderRadius: 10, border: `1px solid ${border}`, maxWidth: 520 }}>
                <Field label="Button Rows" value={buttonRows} onChange={setButtonRows} min={1} step={1} />
                <Field label="Button Columns" value={buttonCols} onChange={setButtonCols} min={1} step={1} />
                <div>
                  <label style={labelStyle}>Button Type</label>
                  <select style={selectStyle} value={buttonType} onChange={(e) => setButtonType(e.target.value)}>
                    {BUTTON_TYPES.map((bt) => (
                      <option key={bt.id} value={bt.id}>{bt.label}</option>
                    ))}
                  </select>
                </div>
              </div>
            )}
          </div>
        );

      case 7:
        return (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
            <div>
              <label style={labelStyle}>Fabric Name</label>
              <input style={inputStyle} value={fabricName} onChange={(e) => setFabricName(e.target.value)} placeholder="e.g. Sunbrella Canvas" />
            </div>
            <Field label="Price per Yard ($)" value={fabricPrice} onChange={setFabricPrice} min={0} step={0.5} />
            <Field label="Pattern Repeat H (in)" value={repeatH} onChange={setRepeatH} min={0} step={0.25} />
            <Field label="Pattern Repeat V (in)" value={repeatV} onChange={setRepeatV} min={0} step={0.25} />
            <Field label="Fabric Width (in)" value={fabricWidth} onChange={setFabricWidth} min={36} step={1} />
            <div className="flex items-center gap-4" style={{ gridColumn: 'span 2' }}>
              <label className="flex items-center gap-2" style={{ fontSize: 14, cursor: 'pointer' }}>
                <input type="checkbox" checked={railroaded} onChange={(e) => setRailroaded(e.target.checked)} style={{ width: 18, height: 18, accentColor: gold }} />
                Railroaded
              </label>
              <label className="flex items-center gap-2" style={{ fontSize: 14, cursor: 'pointer' }}>
                <input type="checkbox" checked={directionalNap} onChange={(e) => setDirectionalNap(e.target.checked)} style={{ width: 18, height: 18, accentColor: gold }} />
                Directional / Nap
              </label>
            </div>
          </div>
        );

      case 8:
        return (
          <div style={{ display: 'grid', gridTemplateColumns: compact ? '1fr' : '1fr 1fr', gap: 24 }}>
            {/* Left — Diagram */}
            <div style={{ background: offWhite, borderRadius: 12, border: `1px solid ${border}`, minHeight: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
              <CushionDiagram
                cushionType={cushionType}
                width={dims.width || dims.diameter || 18}
                depth={dims.depth || dims.diameter || 18}
                height={dims.height || dims.front_height || 4}
                diameter={dims.diameter}
                frontHeight={dims.front_height}
                backHeight={dims.back_height}
                shape={shape}
                cornerRadius={cornerRadius}
                style={style}
                welt={welt}
                tufting={tufting}
                tuftRows={buttonRows}
                tuftCols={buttonCols}
                fillType={fill}
              />
            </div>

            {/* Right — Calculation results */}
            <div className="flex flex-col gap-3">
              <SectionCard title="Material Estimates">
                <Row label="Total Fabric" value={`${materials.totalFabricYards.toFixed(2)} yards`} />
                {hasWelt && <Row label="Welt Cord" value={`${materials.weltCordYards.toFixed(2)} yards`} />}
                {hasWelt && <Row label="Bias Fabric (welt)" value={`${materials.biasFabricYards.toFixed(2)} yards`} />}
                {hasFoam && <Row label="Foam Volume" value={`${materials.foamVolumeCuFt.toFixed(2)} cu ft (${materials.foamBoardFeet.toFixed(1)} bd ft)`} />}
                {hasZipper && <Row label="Zipper Length" value={`${materials.zipperLength.toFixed(0)}"`} />}
                {hasTufting && <Row label="Buttons" value={`${buttonCount} (${buttonRows} x ${buttonCols})`} />}
              </SectionCard>

              <SectionCard title="Cost Breakdown">
                <Row label="Fabric" value={fmt(costs.fabricCost)} />
                {hasFoam && <Row label="Foam" value={fmt(costs.foamCost)} />}
                {hasWelt && <Row label="Welt Cord" value={fmt(costs.weltCordCost)} />}
                {hasZipper && <Row label="Zipper" value={fmt(costs.zipperCost)} />}
                {hasDacron && <Row label="Dacron Wrap" value={fmt(costs.dacronCost)} />}
                {hasDown && <Row label="Down Fill" value={fmt(costs.downCost)} />}
                {buttonCount > 0 && <Row label="Buttons" value={fmt(costs.buttonCost)} />}
                <Row label="Labor" value={fmt(costs.totalLabor)} sub={`base $${costs.laborBase} + complexity $${costs.laborComplexity}`} />
                <div style={{ borderTop: `2px solid ${gold}`, marginTop: 8, paddingTop: 8 }}>
                  <Row label="Per Unit" value={fmt(costs.subtotalPerUnit)} bold />
                  {quantity > 1 && <Row label={`x ${quantity} units`} value={fmt(costs.totalAll)} bold />}
                </div>
              </SectionCard>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  /* ─── Main render ─── */

  const progressPct = ((currentStep + 1) / STEPS.length) * 100;

  return (
    <div style={{ background: '#fff', borderRadius: 14, border: `1px solid ${border}`, overflow: 'hidden' }}>
      {/* Progress bar */}
      <div style={{ height: 4, background: border }}>
        <div style={{ height: '100%', width: `${progressPct}%`, background: `linear-gradient(90deg, ${gold}, #d4a90e)`, transition: 'width 0.3s' }} />
      </div>

      {/* Header */}
      <div style={{ padding: '20px 24px 0', borderBottom: `1px solid ${border}` }}>
        <h2 className="flex items-center gap-2" style={{ fontSize: 20, fontWeight: 700, color: '#222', margin: 0, paddingBottom: 16 }}>
          <Sofa size={22} color={gold} />
          Cushion Builder
        </h2>
      </div>

      {/* Stepper */}
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {STEPS.map((step, idx) => {
          const Icon = step.icon;
          const isActive = idx === currentStep;
          const done = stepComplete(idx) && idx < currentStep;
          const clickable = canGoTo(idx);

          return (
            <div key={step.key}>
              {/* Step header */}
              <button
                type="button"
                onClick={() => clickable && setCurrentStep(idx)}
                disabled={!clickable}
                className="flex items-center gap-3"
                style={{
                  width: '100%',
                  padding: '14px 24px',
                  background: isActive ? offWhite : '#fff',
                  border: 'none',
                  borderBottom: `1px solid ${border}`,
                  cursor: clickable ? 'pointer' : 'default',
                  opacity: clickable ? 1 : 0.45,
                  textAlign: 'left',
                  transition: 'background 0.15s',
                }}
              >
                <div
                  style={{
                    width: 30,
                    height: 30,
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background: done ? gold : isActive ? '#fdf8eb' : '#f5f3ef',
                    border: `2px solid ${done ? gold : isActive ? gold : border}`,
                    flexShrink: 0,
                  }}
                >
                  {done ? (
                    <Check size={14} color="#fff" strokeWidth={3} />
                  ) : (
                    <span style={{ fontSize: 12, fontWeight: 700, color: isActive ? gold : '#999' }}>{idx + 1}</span>
                  )}
                </div>
                <Icon size={16} color={isActive ? gold : '#999'} />
                <span style={{ fontSize: 14, fontWeight: isActive ? 700 : 500, color: isActive ? '#222' : '#666', flex: 1 }}>
                  {step.label}
                </span>
                {isActive ? <ChevronUp size={16} color="#999" /> : <ChevronDown size={16} color="#ccc" />}
              </button>

              {/* Step body (expanded only when active) */}
              {isActive && (
                <div style={{ padding: '20px 24px 24px', borderBottom: `1px solid ${border}`, background: offWhite }}>
                  {renderStepContent(idx)}

                  {/* Nav buttons */}
                  <div className="flex items-center gap-3" style={{ marginTop: 20 }}>
                    {idx > 0 && (
                      <button type="button" style={outlineBtnStyle} onClick={() => setCurrentStep(idx - 1)}>
                        Back
                      </button>
                    )}
                    {idx < STEPS.length - 1 && (
                      <button
                        type="button"
                        style={{ ...goldBtnStyle, opacity: stepComplete(idx) ? 1 : 0.5 }}
                        disabled={!stepComplete(idx)}
                        onClick={() => setCurrentStep(idx + 1)}
                      >
                        Next
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Bottom action bar */}
      <div className="flex items-center gap-3" style={{ padding: '16px 24px', borderTop: `1px solid ${border}`, background: '#fff', flexWrap: 'wrap' }}>
        <button
          type="button"
          style={goldBtnStyle}
          className="flex items-center gap-2"
          onClick={() => onAddToQuote?.(buildQuoteData())}
        >
          <Plus size={16} /> Add to Quote
        </button>

        <div className="flex items-center gap-2" style={{ flex: 1, minWidth: 200 }}>
          <input
            style={{ ...inputStyle, maxWidth: 200 }}
            placeholder="Template name..."
            value={templateName}
            onChange={(e) => setTemplateName(e.target.value)}
          />
          <button
            type="button"
            style={outlineBtnStyle}
            className="flex items-center gap-2"
            onClick={() => {
              if (!templateName.trim()) return;
              onSaveTemplate?.({
                name: templateName.trim(),
                specs: {
                  cushionType,
                  dimensions: { ...dims },
                  quantity,
                  shape,
                  style,
                  fill,
                  edge: welt,
                  closure,
                  tufting,
                  fabric: fabricName,
                },
              });
            }}
          >
            <Save size={14} /> Save as Template
          </button>
        </div>

        <button
          type="button"
          style={outlineBtnStyle}
          className="flex items-center gap-2"
          onClick={() => window.print()}
        >
          <Printer size={14} /> Print
        </button>

        <button
          type="button"
          style={outlineBtnStyle}
          className="flex items-center gap-2"
          onClick={() => alert('PDF export coming soon.')}
        >
          <FileText size={14} /> PDF
        </button>
      </div>
    </div>
  );
}

/* ─── Sub-components ─── */

function Field({
  label,
  value,
  onChange,
  min,
  max,
  step = 0.25,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
}) {
  return (
    <div>
      <label style={labelStyle}>{label}</label>
      <input
        type="number"
        style={inputStyle}
        value={value || ''}
        min={min}
        max={max}
        step={step}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
      />
    </div>
  );
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: '#fff', borderRadius: 10, border: `1px solid ${border}`, padding: 16 }}>
      <h4 style={{ margin: '0 0 10px', fontSize: 13, fontWeight: 700, color: gold, textTransform: 'uppercase', letterSpacing: 0.5 }}>
        {title}
      </h4>
      <div className="flex flex-col gap-1">{children}</div>
    </div>
  );
}

function Row({ label, value, bold, sub }: { label: string; value: string; bold?: boolean; sub?: string }) {
  return (
    <div>
      <div className="flex items-center" style={{ justifyContent: 'space-between', fontSize: bold ? 15 : 13, fontWeight: bold ? 700 : 400, color: bold ? '#222' : '#555' }}>
        <span>{label}</span>
        <span style={{ fontWeight: 600, color: bold ? gold : '#333' }}>{value}</span>
      </div>
      {sub && <div style={{ fontSize: 11, color: '#999', textAlign: 'right' }}>{sub}</div>}
    </div>
  );
}

/* ─── Utilities ─── */

function r2(n: number) {
  return Math.round(n * 100) / 100;
}

function fmt(n: number) {
  return `$${n.toFixed(2)}`;
}
