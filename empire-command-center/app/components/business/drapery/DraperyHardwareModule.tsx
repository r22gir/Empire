'use client';
import React, { useState, useMemo } from 'react';
import { Check, Info, ChevronDown, ChevronUp } from 'lucide-react';

/* ── Types ──────────────────────────────────────────────── */
interface HardwareConfig {
  rodType: string;
  rodMaterial: string;
  rodFinish: string;
  rodDiameter: string;
  finialStyle: string;
  bracketStyle: string;
  bracketCount: number;
  ringStyle: string;
  motorization: string;
  mountType: 'wall' | 'ceiling';
  // Measurements (inches)
  windowWidth: number;
  stackBack: number;
  returnDepth: number;
  mountingHeight: number;
  ceilingToFloor: number;
  rodProjection: number;
}

interface DraperyHardwareModuleProps {
  config: Partial<HardwareConfig>;
  onChange: (config: Partial<HardwareConfig>) => void;
  compact?: boolean;
}

/* ── Catalogs ───────────────────────────────────────────── */
const ROD_TYPES = [
  { id: 'traverse', label: 'Traverse Rod', desc: 'Cord-operated, functional open/close', icon: 'traverse' },
  { id: 'decorative_wood', label: 'Decorative Wood', desc: 'Turned or fluted wood pole', icon: 'wood' },
  { id: 'decorative_metal', label: 'Decorative Metal', desc: 'Iron, brass, or steel pole', icon: 'metal' },
  { id: 'decorative_acrylic', label: 'Acrylic Rod', desc: 'Clear or tinted acrylic pole', icon: 'acrylic' },
  { id: 'ripplefold_track', label: 'Ripplefold Track', desc: 'Continuous wave system', icon: 'track' },
  { id: 'motorized_track', label: 'Motorized Track', desc: 'Automated open/close', icon: 'motor' },
  { id: 'ceiling_track', label: 'Ceiling Track', desc: 'Flush ceiling-mounted track', icon: 'ceiling' },
  { id: 'double_rod', label: 'Double Rod', desc: 'Front + back rod for layers', icon: 'double' },
  { id: 'tension', label: 'Tension Rod', desc: 'Spring-loaded, no hardware', icon: 'tension' },
];

const FINIAL_STYLES = [
  { id: 'none', label: 'None / End Cap' },
  { id: 'ball', label: 'Ball' },
  { id: 'spear', label: 'Spear' },
  { id: 'fleur_de_lis', label: 'Fleur-de-Lis' },
  { id: 'crystal', label: 'Crystal' },
  { id: 'urn', label: 'Urn' },
  { id: 'cage', label: 'Cage' },
  { id: 'leaf', label: 'Leaf' },
  { id: 'scroll', label: 'Scroll' },
  { id: 'square', label: 'Square' },
];

const ROD_FINISHES = [
  { id: 'matte_black', label: 'Matte Black' },
  { id: 'satin_nickel', label: 'Satin Nickel' },
  { id: 'brushed_brass', label: 'Brushed Brass' },
  { id: 'antique_bronze', label: 'Antique Bronze' },
  { id: 'polished_chrome', label: 'Polished Chrome' },
  { id: 'oil_rubbed_bronze', label: 'Oil-Rubbed Bronze' },
  { id: 'gold', label: 'Gold' },
  { id: 'pewter', label: 'Pewter' },
  { id: 'natural_wood', label: 'Natural Wood' },
  { id: 'walnut', label: 'Walnut' },
  { id: 'espresso', label: 'Espresso' },
  { id: 'white', label: 'White / Ivory' },
];

const BRACKET_STYLES = [
  { id: 'standard', label: 'Standard' },
  { id: 'decorative', label: 'Decorative' },
  { id: 'minimal', label: 'Minimal / Hidden' },
  { id: 'center_support', label: 'Center Support' },
];

const RING_STYLES = [
  { id: 'none', label: 'None (Rod Pocket / Tab)' },
  { id: 'clip', label: 'Clip Rings' },
  { id: 'eyelet', label: 'Eyelet Rings' },
  { id: 'c_ring', label: 'C-Rings' },
  { id: 'bypass', label: 'Bypass Rings' },
];

const MOTORIZATION_OPTIONS = [
  { id: 'none', label: 'Manual' },
  { id: 'somfy', label: 'Somfy' },
  { id: 'lutron', label: 'Lutron Serena' },
  { id: 'hunter_douglas', label: 'Hunter Douglas PowerView' },
  { id: 'silent_gliss', label: 'Silent Gliss' },
];

/* ── Installation Diagram SVG ───────────────────────────── */
function InstallationDiagram({ config }: { config: Partial<HardwareConfig> }) {
  const ww = config.windowWidth || 48;
  const sb = config.stackBack || 6;
  const rd = config.returnDepth || 3.5;
  const mh = config.mountingHeight || 4;
  const ctf = config.ceilingToFloor || 96;
  const isCeiling = config.mountType === 'ceiling';

  // SVG dimensions and scale
  const svgW = 460;
  const svgH = 340;
  const margin = { top: 50, right: 40, bottom: 40, left: 50 };
  const drawW = svgW - margin.left - margin.right;
  const drawH = svgH - margin.top - margin.bottom;

  // Scale: fit window + stackback into drawing area
  const totalRodW = ww + sb * 2;
  const scaleX = drawW / (totalRodW + 12);
  const scaleY = drawH / (ctf + 8);
  const scale = Math.min(scaleX, scaleY, 3.5);

  const cx = margin.left + drawW / 2;
  const windowW = ww * scale;
  const stackW = sb * scale;
  const returnD = rd * scale;
  const mountH = mh * scale;
  const floorY = margin.top + ctf * scale;
  const windowTopY = margin.top + 10; // casing top
  const windowH = (ctf - 10) * scale * 0.7; // approximate window height
  const rodY = isCeiling ? margin.top : (windowTopY - mountH);
  const rodW = windowW + stackW * 2;

  // Positions
  const windowLeft = cx - windowW / 2;
  const windowRight = cx + windowW / 2;
  const rodLeft = cx - rodW / 2;
  const rodRight = cx + rodW / 2;

  const bracketCount = config.bracketCount || (totalRodW > 84 ? 3 : 2);

  // Dimension helpers
  const DimH = (x1: number, x2: number, y: number, label: string, above = false) => {
    const dir = above ? -1 : 1;
    const offset = 14 * dir;
    const tickLen = 6 * dir;
    return (
      <g>
        <line x1={x1} y1={y} x2={x1} y2={y + tickLen} stroke="#999" strokeWidth={0.8} />
        <line x1={x2} y1={y} x2={x2} y2={y + tickLen} stroke="#999" strokeWidth={0.8} />
        <line x1={x1} y1={y + offset / 2} x2={x2} y2={y + offset / 2} stroke="#b8960c" strokeWidth={1.2} markerStart="url(#arrowL)" markerEnd="url(#arrowR)" />
        <rect x={(x1 + x2) / 2 - 18} y={y + offset / 2 - 7} width={36} height={14} rx={3} fill="#fff" stroke="none" />
        <text x={(x1 + x2) / 2} y={y + offset / 2 + 4} textAnchor="middle" fontSize={10} fontWeight={600} fill="#b8960c">{label}</text>
      </g>
    );
  };

  const DimV = (x: number, y1: number, y2: number, label: string, right = true) => {
    const dir = right ? 1 : -1;
    const offset = 18 * dir;
    const tickLen = 6 * dir;
    return (
      <g>
        <line x1={x} y1={y1} x2={x + tickLen} y2={y1} stroke="#999" strokeWidth={0.8} />
        <line x1={x} y1={y2} x2={x + tickLen} y2={y2} stroke="#999" strokeWidth={0.8} />
        <line x1={x + offset / 2} y1={y1} x2={x + offset / 2} y2={y2} stroke="#b8960c" strokeWidth={1.2} markerStart="url(#arrowU)" markerEnd="url(#arrowD)" />
        <rect x={x + offset / 2 - 18} y={(y1 + y2) / 2 - 7} width={36} height={14} rx={3} fill="#fff" stroke="none" />
        <text x={x + offset / 2} y={(y1 + y2) / 2 + 4} textAnchor="middle" fontSize={10} fontWeight={600} fill="#b8960c">{label}</text>
      </g>
    );
  };

  const fmtIn = (v: number) => {
    if (v >= 12) {
      const ft = Math.floor(v / 12);
      const inches = v % 12;
      return inches > 0 ? `${ft}'-${inches}"` : `${ft}'-0"`;
    }
    return `${v}"`;
  };

  return (
    <svg viewBox={`0 0 ${svgW} ${svgH}`} width="100%" style={{ maxWidth: 460 }}>
      <defs>
        <marker id="arrowR" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
          <path d="M0,0 L6,3 L0,6" fill="none" stroke="#b8960c" strokeWidth={1.2} />
        </marker>
        <marker id="arrowL" markerWidth="6" markerHeight="6" refX="1" refY="3" orient="auto">
          <path d="M6,0 L0,3 L6,6" fill="none" stroke="#b8960c" strokeWidth={1.2} />
        </marker>
        <marker id="arrowD" markerWidth="6" markerHeight="6" refX="3" refY="5" orient="auto">
          <path d="M0,0 L3,6 L6,0" fill="none" stroke="#b8960c" strokeWidth={1.2} />
        </marker>
        <marker id="arrowU" markerWidth="6" markerHeight="6" refX="3" refY="1" orient="auto">
          <path d="M0,6 L3,0 L6,6" fill="none" stroke="#b8960c" strokeWidth={1.2} />
        </marker>
      </defs>

      {/* Title */}
      <text x={svgW / 2} y={16} textAnchor="middle" fontSize={13} fontWeight={700} fill="#1a1a1a">
        Installation Diagram — {isCeiling ? 'Ceiling Mount' : 'Wall Mount'}
      </text>

      {/* Wall background */}
      <rect x={margin.left - 10} y={margin.top - 5} width={drawW + 20} height={floorY - margin.top + 15}
        rx={4} fill="#faf9f7" stroke="#e8e4dc" strokeWidth={1} />

      {/* Window opening */}
      <rect x={windowLeft} y={windowTopY} width={windowW} height={windowH}
        rx={2} fill="#d4e8f7" stroke="#888" strokeWidth={1.5} />
      {/* Window casing */}
      <rect x={windowLeft - 3} y={windowTopY - 3} width={windowW + 6} height={windowH + 6}
        rx={3} fill="none" stroke="#666" strokeWidth={2} />
      <text x={cx} y={windowTopY + windowH / 2 + 4} textAnchor="middle" fontSize={10} fill="#6b93b8" fontWeight={500}>
        WINDOW
      </text>

      {/* Floor line */}
      <line x1={margin.left - 5} y1={floorY} x2={svgW - margin.right + 5} y2={floorY}
        stroke="#333" strokeWidth={2} />
      <text x={margin.left - 5} y={floorY + 14} fontSize={9} fill="#999">FLOOR</text>

      {/* Rod */}
      <line x1={rodLeft} y1={rodY} x2={rodRight} y2={rodY}
        stroke="#444" strokeWidth={3} strokeLinecap="round" />

      {/* Finials */}
      {config.finialStyle && config.finialStyle !== 'none' && (
        <>
          <circle cx={rodLeft - 4} cy={rodY} r={5} fill="#666" stroke="#444" strokeWidth={1} />
          <circle cx={rodRight + 4} cy={rodY} r={5} fill="#666" stroke="#444" strokeWidth={1} />
        </>
      )}

      {/* Brackets */}
      {Array.from({ length: bracketCount }).map((_, i) => {
        const bx = bracketCount === 2
          ? (i === 0 ? rodLeft + 8 : rodRight - 8)
          : rodLeft + (rodW / (bracketCount - 1)) * i;
        return (
          <g key={i}>
            <rect x={bx - 3} y={rodY} width={6} height={12} rx={1} fill="#888" stroke="#666" strokeWidth={0.8} />
            <circle cx={bx} cy={rodY + 14} r={2} fill="#aaa" />
          </g>
        );
      })}

      {/* Returns (side view indicators) */}
      <line x1={rodLeft} y1={rodY - 2} x2={rodLeft} y2={rodY + 18} stroke="#b8960c" strokeWidth={1} strokeDasharray="3,2" />
      <line x1={rodRight} y1={rodY - 2} x2={rodRight} y2={rodY + 18} stroke="#b8960c" strokeWidth={1} strokeDasharray="3,2" />

      {/* Drapery fabric suggestion */}
      <path
        d={`M${rodLeft + 2},${rodY + 4} Q${rodLeft + stackW * 0.3},${rodY + windowH * 0.4} ${rodLeft + stackW},${rodY + windowH * 0.95}
            L${rodRight - stackW},${rodY + windowH * 0.95}
            Q${rodRight - stackW * 0.3},${rodY + windowH * 0.4} ${rodRight - 2},${rodY + 4}`}
        fill="none" stroke="#c4b07a" strokeWidth={1.5} strokeDasharray="6,3" opacity={0.5}
      />

      {/* ── Dimensions ── */}

      {/* Window width */}
      {DimH(windowLeft, windowRight, windowTopY + windowH + 8, fmtIn(ww))}

      {/* Total rod width */}
      {DimH(rodLeft, rodRight, rodY - 22, fmtIn(Math.round(totalRodW)), true)}

      {/* Left stack-back */}
      {stackW > 15 && DimH(rodLeft, windowLeft - 3, rodY + 24, fmtIn(sb))}

      {/* Right stack-back */}
      {stackW > 15 && DimH(windowRight + 3, rodRight, rodY + 24, fmtIn(sb))}

      {/* Mounting height above window */}
      {!isCeiling && mountH > 8 && DimV(rodRight + 12, rodY, windowTopY - 3, fmtIn(mh))}

      {/* Return depth label */}
      <text x={rodLeft - 4} y={rodY + 32} textAnchor="end" fontSize={9} fill="#666">
        Return: {fmtIn(rd)}
      </text>

      {/* Legend */}
      <text x={margin.left} y={svgH - 8} fontSize={9} fill="#aaa">
        Rod: {ROD_TYPES.find(r => r.id === config.rodType)?.label || 'Not selected'}
        {config.rodFinish ? ` · ${ROD_FINISHES.find(f => f.id === config.rodFinish)?.label || config.rodFinish}` : ''}
        {config.motorization && config.motorization !== 'none' ? ` · ${MOTORIZATION_OPTIONS.find(m => m.id === config.motorization)?.label}` : ''}
      </text>
    </svg>
  );
}

/* ── Side-View Return Diagram ───────────────────────────── */
function ReturnDiagram({ returnDepth, projection }: { returnDepth: number; projection: number }) {
  const svgW = 200;
  const svgH = 120;
  const scale = Math.min(2.5, 80 / Math.max(returnDepth, projection, 4));
  const wallX = 30;
  const rodY = 30;

  return (
    <svg viewBox={`0 0 ${svgW} ${svgH}`} width="100%" style={{ maxWidth: 200 }}>
      {/* Wall */}
      <rect x={wallX - 4} y={10} width={8} height={svgH - 20} fill="#e8e4dc" stroke="#ccc" strokeWidth={1} />
      <text x={wallX} y={svgH - 4} textAnchor="middle" fontSize={8} fill="#aaa">WALL</text>

      {/* Bracket */}
      <rect x={wallX + 2} y={rodY - 2} width={returnDepth * scale} height={4} rx={1} fill="#888" stroke="#666" strokeWidth={0.8} />

      {/* Rod (circle = cross-section) */}
      <circle cx={wallX + 4 + returnDepth * scale} cy={rodY} r={4} fill="#444" stroke="#333" strokeWidth={1} />

      {/* Return line */}
      <line x1={wallX + 4 + returnDepth * scale} y1={rodY + 5}
        x2={wallX + 4 + returnDepth * scale} y2={rodY + 50}
        stroke="#c4b07a" strokeWidth={1} strokeDasharray="4,2" />
      <line x1={wallX + 4 + returnDepth * scale} y1={rodY + 50}
        x2={wallX + 2} y2={rodY + 50}
        stroke="#c4b07a" strokeWidth={1} strokeDasharray="4,2" />

      {/* Return depth dimension */}
      <line x1={wallX + 4} y1={rodY + 60} x2={wallX + 4 + returnDepth * scale} y2={rodY + 60}
        stroke="#b8960c" strokeWidth={1} markerStart="url(#arrowL)" markerEnd="url(#arrowR)" />
      <text x={wallX + 4 + (returnDepth * scale) / 2} y={rodY + 74} textAnchor="middle" fontSize={9} fontWeight={600} fill="#b8960c">
        {returnDepth}"
      </text>

      <text x={wallX + 4 + returnDepth * scale + 10} y={rodY + 4} fontSize={8} fill="#666">Rod</text>
      <text x={wallX + 4 + (returnDepth * scale) / 2} y={rodY + 56} textAnchor="middle" fontSize={7} fill="#999">Return</text>
    </svg>
  );
}

/* ── Main Component ─────────────────────────────────────── */
export default function DraperyHardwareModule({ config, onChange, compact }: DraperyHardwareModuleProps) {
  const [expandedSection, setExpandedSection] = useState<string>('rod');

  const update = (key: keyof HardwareConfig, value: any) => {
    onChange({ ...config, [key]: value });
  };

  const currentRod = ROD_TYPES.find(r => r.id === config.rodType);

  const Section = ({ id, title, children }: { id: string; title: string; children: React.ReactNode }) => {
    const isOpen = expandedSection === id;
    return (
      <div style={{ borderBottom: '1px solid #e8e4dc' }}>
        <button
          onClick={() => setExpandedSection(isOpen ? '' : id)}
          className="flex items-center justify-between w-full cursor-pointer"
          style={{ padding: '12px 0', background: 'none', border: 'none', fontSize: 12, fontWeight: 700, color: '#1a1a1a' }}
        >
          {title}
          {isOpen ? <ChevronUp size={14} className="text-[#999]" /> : <ChevronDown size={14} className="text-[#999]" />}
        </button>
        {isOpen && <div style={{ paddingBottom: 16 }}>{children}</div>}
      </div>
    );
  };

  const SelectGrid = ({ items, value, onSelect, columns = 3 }: {
    items: { id: string; label: string; desc?: string }[];
    value: string | undefined;
    onSelect: (id: string) => void;
    columns?: number;
  }) => (
    <div className={`grid gap-2`} style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
      {items.map(item => {
        const isActive = value === item.id;
        return (
          <button key={item.id} onClick={() => onSelect(item.id)}
            className="text-left cursor-pointer transition-all"
            style={{
              padding: '8px 10px', borderRadius: 8, fontSize: 11,
              border: `1.5px solid ${isActive ? '#2563eb' : '#e8e4dc'}`,
              background: isActive ? '#eff6ff' : '#fff',
              color: isActive ? '#2563eb' : '#555',
              fontWeight: isActive ? 600 : 400,
            }}>
            <div style={{ fontWeight: 600 }}>{item.label}</div>
            {item.desc && <div style={{ fontSize: 9, color: '#999', marginTop: 2 }}>{item.desc}</div>}
            {isActive && <Check size={12} style={{ color: '#2563eb', marginTop: 4 }} />}
          </button>
        );
      })}
    </div>
  );

  return (
    <div style={{ background: '#fff', borderRadius: 12, border: '1.5px solid #d6e4f0', padding: 16 }}>
      <div className="flex items-center gap-2 mb-2">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2" strokeLinecap="round">
          <line x1="2" y1="8" x2="22" y2="8" />
          <circle cx="4" cy="8" r="2" fill="#2563eb" />
          <circle cx="20" cy="8" r="2" fill="#2563eb" />
          <line x1="4" y1="10" x2="4" y2="14" />
          <line x1="20" y1="10" x2="20" y2="14" />
          <line x1="12" y1="10" x2="12" y2="14" />
        </svg>
        <span style={{ fontSize: 12, fontWeight: 700, color: '#2563eb', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          Drapery Hardware Configuration
        </span>
      </div>

      {/* ── Installation Diagram ── */}
      <div style={{ background: '#fafcff', borderRadius: 10, border: '1px solid #e8eef5', padding: 12, marginBottom: 16 }}>
        <InstallationDiagram config={config} />
      </div>

      {/* ── Measurement Inputs ── */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#333', marginBottom: 8 }}>Installation Measurements</div>
        <div className="grid grid-cols-3 gap-3">
          {[
            { key: 'windowWidth', label: 'Window Width', ph: '48', unit: '"' },
            { key: 'stackBack', label: 'Stack-Back', ph: '6', unit: '"' },
            { key: 'returnDepth', label: 'Return Depth', ph: '3.5', unit: '"' },
            { key: 'mountingHeight', label: 'Above Window', ph: '4', unit: '"' },
            { key: 'ceilingToFloor', label: 'Ceiling to Floor', ph: '96', unit: '"' },
            { key: 'rodProjection', label: 'Rod Projection', ph: '4', unit: '"' },
          ].map(f => (
            <div key={f.key}>
              <label style={{ fontSize: 9, fontWeight: 600, color: '#888', display: 'block', marginBottom: 2 }}>{f.label}</label>
              <div style={{ position: 'relative' }}>
                <input
                  type="number"
                  value={(config as any)[f.key] || ''}
                  onChange={e => update(f.key as keyof HardwareConfig, parseFloat(e.target.value) || 0)}
                  placeholder={f.ph}
                  className="form-input"
                  style={{ width: '100%', fontSize: 12, padding: '7px 22px 7px 8px' }}
                />
                <span style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', fontSize: 10, color: '#bbb' }}>{f.unit}</span>
              </div>
            </div>
          ))}
        </div>
        <div className="flex gap-2 mt-3">
          {(['wall', 'ceiling'] as const).map(mt => (
            <button key={mt} onClick={() => update('mountType', mt)}
              className="flex-1 cursor-pointer transition-all"
              style={{
                padding: '8px', borderRadius: 8, fontSize: 11, fontWeight: 600, textAlign: 'center',
                border: `1.5px solid ${config.mountType === mt ? '#2563eb' : '#e8e4dc'}`,
                background: config.mountType === mt ? '#eff6ff' : '#fff',
                color: config.mountType === mt ? '#2563eb' : '#777',
              }}>
              {mt === 'wall' ? 'Wall Mount' : 'Ceiling Mount'}
            </button>
          ))}
        </div>
      </div>

      {/* ── Return Depth Side View ── */}
      {(config.returnDepth || 0) > 0 && (
        <div style={{ background: '#fafcff', borderRadius: 10, border: '1px solid #e8eef5', padding: 12, marginBottom: 16 }}>
          <div style={{ fontSize: 10, fontWeight: 600, color: '#888', marginBottom: 6 }}>Side View — Return Depth</div>
          <ReturnDiagram returnDepth={config.returnDepth || 3.5} projection={config.rodProjection || 4} />
        </div>
      )}

      {/* ── Accordion Sections ── */}
      <Section id="rod" title="Rod Type & Material">
        <SelectGrid items={ROD_TYPES} value={config.rodType} onSelect={(id) => update('rodType', id)} columns={3} />
      </Section>

      <Section id="finish" title="Finish & Diameter">
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 10, fontWeight: 600, color: '#888', marginBottom: 6 }}>Finish</div>
          <SelectGrid items={ROD_FINISHES} value={config.rodFinish} onSelect={(id) => update('rodFinish', id)} columns={4} />
        </div>
        <div>
          <div style={{ fontSize: 10, fontWeight: 600, color: '#888', marginBottom: 6 }}>Rod Diameter</div>
          <div className="flex gap-2">
            {['3/4"', '1"', '1-3/8"', '1-1/2"', '2"', '3"'].map(d => (
              <button key={d} onClick={() => update('rodDiameter', d)}
                className="flex-1 cursor-pointer transition-all"
                style={{
                  padding: '7px 4px', borderRadius: 8, fontSize: 11, fontWeight: 600, textAlign: 'center',
                  border: `1.5px solid ${config.rodDiameter === d ? '#2563eb' : '#e8e4dc'}`,
                  background: config.rodDiameter === d ? '#eff6ff' : '#fff',
                  color: config.rodDiameter === d ? '#2563eb' : '#777',
                }}>
                {d}
              </button>
            ))}
          </div>
        </div>
      </Section>

      <Section id="finial" title="Finials">
        <SelectGrid items={FINIAL_STYLES} value={config.finialStyle} onSelect={(id) => update('finialStyle', id)} columns={5} />
      </Section>

      <Section id="bracket" title="Brackets & Rings">
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 10, fontWeight: 600, color: '#888', marginBottom: 6 }}>Bracket Style</div>
          <SelectGrid items={BRACKET_STYLES} value={config.bracketStyle} onSelect={(id) => update('bracketStyle', id)} columns={4} />
        </div>
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 10, fontWeight: 600, color: '#888', marginBottom: 6 }}>Bracket Count</div>
          <div className="flex gap-2">
            {[2, 3, 4, 5].map(n => (
              <button key={n} onClick={() => update('bracketCount', n)}
                className="cursor-pointer transition-all"
                style={{
                  width: 44, height: 36, borderRadius: 8, fontSize: 13, fontWeight: 700, textAlign: 'center',
                  border: `1.5px solid ${config.bracketCount === n ? '#2563eb' : '#e8e4dc'}`,
                  background: config.bracketCount === n ? '#eff6ff' : '#fff',
                  color: config.bracketCount === n ? '#2563eb' : '#777',
                }}>
                {n}
              </button>
            ))}
          </div>
        </div>
        <div>
          <div style={{ fontSize: 10, fontWeight: 600, color: '#888', marginBottom: 6 }}>Ring Style</div>
          <SelectGrid items={RING_STYLES} value={config.ringStyle} onSelect={(id) => update('ringStyle', id)} columns={3} />
        </div>
      </Section>

      <Section id="motor" title="Motorization">
        <SelectGrid items={MOTORIZATION_OPTIONS} value={config.motorization} onSelect={(id) => update('motorization', id)} columns={3} />
        {config.motorization && config.motorization !== 'none' && (
          <div style={{ marginTop: 10, padding: '8px 12px', borderRadius: 8, background: '#eff6ff', border: '1px solid #dbeafe', fontSize: 11, color: '#2563eb' }}>
            <Info size={12} style={{ display: 'inline', verticalAlign: 'text-bottom', marginRight: 4 }} />
            {config.motorization === 'somfy' && 'Somfy motors require dedicated power supply. Plan for outlet placement within 6\' of the header.'}
            {config.motorization === 'lutron' && 'Lutron Serena integrates with Caseta/RadioRA. Battery-powered option available.'}
            {config.motorization === 'hunter_douglas' && 'PowerView requires hub and gateway. Supports scheduling and voice control.'}
            {config.motorization === 'silent_gliss' && 'Silent Gliss requires hardwired power. Ultra-quiet operation, ideal for bedrooms.'}
          </div>
        )}
      </Section>

      {/* ── Summary ── */}
      {config.rodType && (
        <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 10, background: '#f0f9ff', border: '1px solid #dbeafe' }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#2563eb', marginBottom: 4 }}>HARDWARE SUMMARY</div>
          <div style={{ fontSize: 11, color: '#333', lineHeight: 1.6 }}>
            {currentRod?.label || config.rodType}
            {config.rodDiameter ? ` (${config.rodDiameter})` : ''}
            {config.rodFinish ? ` — ${ROD_FINISHES.find(f => f.id === config.rodFinish)?.label}` : ''}
            <br />
            {config.finialStyle && config.finialStyle !== 'none' ? `Finials: ${FINIAL_STYLES.find(f => f.id === config.finialStyle)?.label}` : 'No finials'}
            {' · '}{config.bracketCount || 2} brackets
            {config.ringStyle && config.ringStyle !== 'none' ? ` · ${RING_STYLES.find(r => r.id === config.ringStyle)?.label}` : ''}
            {config.motorization && config.motorization !== 'none' ? (
              <><br />Motor: {MOTORIZATION_OPTIONS.find(m => m.id === config.motorization)?.label}</>
            ) : ''}
            <br />
            Rod width: {Math.round((config.windowWidth || 48) + (config.stackBack || 6) * 2)}"
            {' · '}Return: {config.returnDepth || 3.5}"
            {' · '}{config.mountType === 'ceiling' ? 'Ceiling' : 'Wall'} mount
          </div>
        </div>
      )}
    </div>
  );
}
