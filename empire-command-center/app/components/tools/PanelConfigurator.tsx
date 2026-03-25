'use client';

import React, { useState, useMemo, useRef } from 'react';
import { Printer } from 'lucide-react';

export type PanelStyle = 'flat' | 'vertical_channels' | 'horizontal_channels' | 'tufted' | 'spaced_panels';

export interface PanelConfig {
  style: PanelStyle;
  panelCount: number;
  panelWidth: number;   // inches (vertical channels / spaced)
  panelHeight: number;  // inches (horizontal channels)
  gap: number;          // inches between panels
  equalDivide: boolean; // auto-divide width/height equally
  // Tufted specific
  rows: number;
  columns: number;
  diamondW: number;
  diamondH: number;
  tuftType: 'button' | 'tuft' | 'biscuit';
  // Multi-section (L/U shaped)
  sections?: SectionConfig[];
}

export interface SectionConfig {
  label: string;
  width: number;
  height: number;
  panelConfig: Omit<PanelConfig, 'sections'>;
}

interface PanelConfiguratorProps {
  backWidth: number;   // inches
  backHeight: number;  // inches
  config: PanelConfig;
  onChange: (config: PanelConfig) => void;
  itemType?: string;   // for L/U detection
  itemLabel?: string;  // for print header
}

const STYLES: { value: PanelStyle; label: string; desc: string }[] = [
  { value: 'flat', label: 'Flat', desc: 'Single piece — no panels' },
  { value: 'vertical_channels', label: 'Vertical Channels', desc: 'Panels side by side' },
  { value: 'horizontal_channels', label: 'Horizontal Channels', desc: 'Panels stacked' },
  { value: 'tufted', label: 'Tufted / Diamond', desc: 'Diamond grid with buttons or tufts' },
  { value: 'spaced_panels', label: 'Spaced Panels', desc: 'Panels with visible gaps' },
];

export const DEFAULT_PANEL_CONFIG: PanelConfig = {
  style: 'flat',
  panelCount: 0,
  panelWidth: 0,
  panelHeight: 0,
  gap: 0,
  equalDivide: true,
  rows: 0,
  columns: 0,
  diamondW: 0,
  diamondH: 0,
  tuftType: 'button',
};

const DEFAULT_SECTION: Omit<PanelConfig, 'sections'> = { ...DEFAULT_PANEL_CONFIG };

const SEAM_ALLOWANCE = 1; // 1 inch per panel side

function isMultiSection(type?: string): false | 'L' | 'U' {
  if (!type) return false;
  const t = type.toLowerCase();
  if (t.includes('u_booth') || t.includes('u_shaped') || t.includes('sectional_u')) return 'U';
  if (t.includes('l_shaped') || t.includes('l_bench') || t.includes('sectional_l')) return 'L';
  return false;
}

function getSectionLabels(shape: 'L' | 'U'): string[] {
  if (shape === 'U') return ['Left Side', 'Center Back', 'Right Side'];
  return ['Long Side', 'Short Side'];
}

// Shared calculation logic
function calcFabric(config: Omit<PanelConfig, 'sections'>, backWidth: number, backHeight: number) {
  const s = config.style;
  if (s === 'flat' || !backWidth || !backHeight) return null;
  const panels: { w: number; h: number; sqft: number; yd: number }[] = [];

  if (s === 'vertical_channels' || s === 'spaced_panels') {
    const count = config.panelCount || 0;
    if (count <= 0) return null;
    const pw = config.equalDivide
      ? Math.max((backWidth - config.gap * (count - 1)) / count, 0)
      : config.panelWidth;
    const ph = backHeight;
    for (let i = 0; i < count; i++) {
      const w = pw + SEAM_ALLOWANCE * 2;
      const h = ph + SEAM_ALLOWANCE * 2;
      const sqft = (w * h) / 144;
      panels.push({ w: pw, h: ph, sqft, yd: sqft / 9 * 1.1 });
    }
  } else if (s === 'horizontal_channels') {
    const count = config.panelCount || 0;
    if (count <= 0) return null;
    const pw = backWidth;
    const ph = config.equalDivide
      ? Math.max((backHeight - config.gap * (count - 1)) / count, 0)
      : config.panelHeight;
    for (let i = 0; i < count; i++) {
      const w = pw + SEAM_ALLOWANCE * 2;
      const h = ph + SEAM_ALLOWANCE * 2;
      const sqft = (w * h) / 144;
      panels.push({ w: pw, h: ph, sqft, yd: sqft / 9 * 1.1 });
    }
  } else if (s === 'tufted') {
    const { rows, columns, diamondW, diamondH } = config;
    if (!rows || !columns) return null;
    const dw = diamondW || (backWidth / columns);
    const dh = diamondH || (backHeight / rows);
    const totalSqft = (backWidth * backHeight) / 144;
    return {
      panels: [{ w: backWidth, h: backHeight, sqft: totalSqft, yd: totalSqft / 9 * 1.3 }],
      totalSqft,
      totalYd: totalSqft / 9 * 1.3,
      dimLabel: `${rows}×${columns} grid, ${dw.toFixed(1)}"×${dh.toFixed(1)}" diamonds`,
    };
  }

  if (panels.length === 0) return null;
  const totalSqft = panels.reduce((s, p) => s + p.sqft, 0);
  const totalYd = panels.reduce((s, p) => s + p.yd, 0);
  return { panels, totalSqft, totalYd };
}

// Shared SVG preview
function SvgPreview({ config, backWidth, backHeight }: { config: Omit<PanelConfig, 'sections'>; backWidth: number; backHeight: number }) {
  const preview = useMemo(() => {
    if (config.style === 'flat' || !backWidth || !backHeight) return null;
    const svgW = 280;
    const svgH = 100;
    const scale = Math.min(svgW / backWidth, svgH / backHeight) * 0.9;
    const oX = (svgW - backWidth * scale) / 2;
    const oY = (svgH - backHeight * scale) / 2;
    const rects: React.ReactNode[] = [];

    rects.push(<rect key="bg" x={oX} y={oY} width={backWidth * scale} height={backHeight * scale} fill="#f0ede8" stroke="#b8960c" strokeWidth={1.5} rx={3} />);

    if (config.style === 'vertical_channels' || config.style === 'spaced_panels') {
      const count = config.panelCount || 0;
      const gap = config.gap * scale;
      const pw = config.equalDivide
        ? (backWidth * scale - gap * (count - 1)) / count
        : config.panelWidth * scale;
      for (let i = 0; i < count; i++) {
        const x = oX + i * (pw + gap);
        rects.push(
          <rect key={`p${i}`} x={x} y={oY + 2} width={Math.max(pw - 1, 1)} height={backHeight * scale - 4}
            fill="#d4af3730" stroke="#b8960c" strokeWidth={0.8} rx={2} />
        );
        if (i < 3 || i === count - 1) {
          rects.push(<text key={`t${i}`} x={x + pw / 2} y={oY + backHeight * scale / 2} textAnchor="middle" fontSize={8} fill="#b8960c">
            {i + 1}
          </text>);
        }
      }
    } else if (config.style === 'horizontal_channels') {
      const count = config.panelCount || 0;
      const gap = config.gap * scale;
      const ph = config.equalDivide
        ? (backHeight * scale - gap * (count - 1)) / count
        : config.panelHeight * scale;
      for (let i = 0; i < count; i++) {
        const y = oY + i * (ph + gap);
        rects.push(
          <rect key={`p${i}`} x={oX + 2} y={y} width={backWidth * scale - 4} height={Math.max(ph - 1, 1)}
            fill="#d4af3730" stroke="#b8960c" strokeWidth={0.8} rx={2} />
        );
      }
    } else if (config.style === 'tufted') {
      const { rows, columns } = config;
      if (rows > 0 && columns > 0) {
        const cw = (backWidth * scale) / columns;
        const ch = (backHeight * scale) / rows;
        for (let r = 0; r < rows; r++) {
          for (let c = 0; c < columns; c++) {
            const cx = oX + c * cw + cw / 2;
            const cy = oY + r * ch + ch / 2;
            const hw = cw * 0.35, hh = ch * 0.35;
            rects.push(
              <polygon key={`d${r}_${c}`}
                points={`${cx},${cy - hh} ${cx + hw},${cy} ${cx},${cy + hh} ${cx - hw},${cy}`}
                fill="#d4af3720" stroke="#b8960c" strokeWidth={0.5} />
            );
            rects.push(<circle key={`b${r}_${c}`} cx={cx} cy={cy} r={2} fill="#b8960c" />);
          }
        }
      }
    }

    return (
      <svg width={svgW} height={svgH} viewBox={`0 0 ${svgW} ${svgH}`} style={{ display: 'block', margin: '8px auto 0' }}>
        {rects}
      </svg>
    );
  }, [config, backWidth, backHeight]);

  return preview;
}

// Single-section panel editor (reused for each section in multi-section mode)
function PanelEditor({ config, onChange, backWidth, backHeight, radioName }: {
  config: Omit<PanelConfig, 'sections'>;
  onChange: (c: Omit<PanelConfig, 'sections'>) => void;
  backWidth: number;
  backHeight: number;
  radioName: string;
}) {
  const set = (partial: Partial<PanelConfig>) => onChange({ ...config, ...partial });
  const fabricCalc = useMemo(() => calcFabric(config, backWidth, backHeight), [config, backWidth, backHeight]);

  const inputStyle: React.CSSProperties = {
    width: 60, fontSize: 11, padding: '4px 6px', borderRadius: 6,
    border: '1px solid #ece8e0', background: '#fff', textAlign: 'center' as const,
  };
  const labelStyle: React.CSSProperties = { fontSize: 9, fontWeight: 600, color: '#999' };

  return (
    <div>
      {/* Panel Style */}
      <div style={{ marginBottom: 10 }}>
        <label style={labelStyle}>PANEL STYLE</label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginTop: 4 }}>
          {STYLES.map(s => (
            <label key={s.value} className="flex items-center gap-2 cursor-pointer" style={{ fontSize: 11 }}>
              <input
                type="radio" name={radioName} value={s.value}
                checked={config.style === s.value}
                onChange={() => set({ style: s.value })}
                style={{ accentColor: '#b8960c' }}
              />
              <span style={{ fontWeight: config.style === s.value ? 700 : 500, color: config.style === s.value ? '#b8960c' : '#555' }}>
                {s.label}
              </span>
              <span style={{ fontSize: 9, color: '#999' }}>{s.desc}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Vertical / Spaced */}
      {(config.style === 'vertical_channels' || config.style === 'spaced_panels') && (
        <div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 6, alignItems: 'end' }}>
            <div>
              <label style={labelStyle}>PANEL WIDTH (in)</label>
              <input type="number" min={0} step={0.5} value={config.panelWidth || ''} onChange={e => {
                const pw = +e.target.value;
                const gap = config.gap || 0;
                const autoCount = pw > 0 && backWidth > 0 ? Math.floor((backWidth + gap) / (pw + gap)) : config.panelCount;
                set({ panelWidth: pw, panelCount: autoCount, equalDivide: false });
              }} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>GAP (in)</label>
              <input type="number" min={0} step={0.25} value={config.gap || ''} onChange={e => {
                const gap = +e.target.value;
                const pw = config.panelWidth || 0;
                const autoCount = pw > 0 && backWidth > 0 ? Math.floor((backWidth + gap) / (pw + gap)) : config.panelCount;
                set({ gap, panelCount: autoCount });
              }} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}># PANELS</label>
              <input type="number" min={0} value={config.panelCount || ''} onChange={e => set({ panelCount: +e.target.value })} style={inputStyle} />
            </div>
            <label className="flex items-center gap-1 cursor-pointer" style={{ fontSize: 10, color: '#777' }}>
              <input type="checkbox" checked={config.equalDivide} onChange={e => {
                const eq = e.target.checked;
                if (eq && config.panelCount > 0 && backWidth > 0) {
                  const pw = (backWidth - config.gap * (config.panelCount - 1)) / config.panelCount;
                  set({ equalDivide: eq, panelWidth: Math.round(pw * 10) / 10 });
                } else {
                  set({ equalDivide: eq });
                }
              }} style={{ accentColor: '#b8960c' }} />
              Equal width
            </label>
          </div>
          {backWidth > 0 && config.panelCount > 0 && (
            <div style={{ fontSize: 10, color: '#888', marginBottom: 10 }}>
              {backWidth}&quot; total &divide; {config.panelCount} panels
              {config.gap > 0 ? ` (${config.gap}" gap)` : ''}
              {' = '}
              <span style={{ fontWeight: 700, color: '#b8960c' }}>
                {config.equalDivide
                  ? `${((backWidth - config.gap * (config.panelCount - 1)) / config.panelCount).toFixed(1)}"`
                  : `${config.panelWidth || 0}"`
                } each
              </span>
              {!config.equalDivide && config.panelWidth > 0 && (() => {
                const used = config.panelCount * config.panelWidth + (config.panelCount - 1) * (config.gap || 0);
                const leftover = backWidth - used;
                return leftover > 0.1
                  ? <span style={{ color: '#d97706' }}> ({leftover.toFixed(1)}&quot; remaining)</span>
                  : leftover < -0.1
                  ? <span style={{ color: '#dc2626' }}> ({Math.abs(leftover).toFixed(1)}&quot; over!)</span>
                  : null;
              })()}
            </div>
          )}
        </div>
      )}

      {/* Horizontal */}
      {config.style === 'horizontal_channels' && (
        <div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 6, alignItems: 'end' }}>
            <div>
              <label style={labelStyle}>PANEL HEIGHT (in)</label>
              <input type="number" min={0} step={0.5} value={config.panelHeight || ''} onChange={e => {
                const ph = +e.target.value;
                const gap = config.gap || 0;
                const autoCount = ph > 0 && backHeight > 0 ? Math.floor((backHeight + gap) / (ph + gap)) : config.panelCount;
                set({ panelHeight: ph, panelCount: autoCount, equalDivide: false });
              }} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>GAP (in)</label>
              <input type="number" min={0} step={0.25} value={config.gap || ''} onChange={e => {
                const gap = +e.target.value;
                const ph = config.panelHeight || 0;
                const autoCount = ph > 0 && backHeight > 0 ? Math.floor((backHeight + gap) / (ph + gap)) : config.panelCount;
                set({ gap, panelCount: autoCount });
              }} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}># PANELS</label>
              <input type="number" min={0} value={config.panelCount || ''} onChange={e => set({ panelCount: +e.target.value })} style={inputStyle} />
            </div>
            <label className="flex items-center gap-1 cursor-pointer" style={{ fontSize: 10, color: '#777' }}>
              <input type="checkbox" checked={config.equalDivide} onChange={e => {
                const eq = e.target.checked;
                if (eq && config.panelCount > 0 && backHeight > 0) {
                  const ph = (backHeight - config.gap * (config.panelCount - 1)) / config.panelCount;
                  set({ equalDivide: eq, panelHeight: Math.round(ph * 10) / 10 });
                } else {
                  set({ equalDivide: eq });
                }
              }} style={{ accentColor: '#b8960c' }} />
              Equal height
            </label>
          </div>
          {backHeight > 0 && config.panelCount > 0 && (
            <div style={{ fontSize: 10, color: '#888', marginBottom: 10 }}>
              {backHeight}&quot; total &divide; {config.panelCount} panels
              {config.gap > 0 ? ` (${config.gap}" gap)` : ''}
              {' = '}
              <span style={{ fontWeight: 700, color: '#b8960c' }}>
                {config.equalDivide
                  ? `${((backHeight - config.gap * (config.panelCount - 1)) / config.panelCount).toFixed(1)}"`
                  : `${config.panelHeight || 0}"`
                } each
              </span>
            </div>
          )}
        </div>
      )}

      {/* Tufted */}
      {config.style === 'tufted' && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 10, alignItems: 'end' }}>
          <div>
            <label style={labelStyle}>ROWS</label>
            <input type="number" min={0} value={config.rows || ''} onChange={e => set({ rows: +e.target.value })} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>COLUMNS</label>
            <input type="number" min={0} value={config.columns || ''} onChange={e => set({ columns: +e.target.value })} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>DIAMOND W (in)</label>
            <input type="number" min={0} step={0.5} value={config.diamondW || ''} onChange={e => set({ diamondW: +e.target.value })} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>DIAMOND H (in)</label>
            <input type="number" min={0} step={0.5} value={config.diamondH || ''} onChange={e => set({ diamondH: +e.target.value })} style={inputStyle} />
          </div>
          <div>
            <label style={labelStyle}>TUFT TYPE</label>
            <select value={config.tuftType} onChange={e => set({ tuftType: e.target.value as PanelConfig['tuftType'] })}
              style={{ ...inputStyle, width: 80 }}>
              <option value="button">Button</option>
              <option value="tuft">Tuft</option>
              <option value="biscuit">Biscuit</option>
            </select>
          </div>
        </div>
      )}

      {/* SVG Preview */}
      <SvgPreview config={config} backWidth={backWidth} backHeight={backHeight} />

      {/* Fabric Estimate */}
      {fabricCalc && (
        <div style={{ marginTop: 10, padding: '8px 10px', background: '#fff', borderRadius: 8, border: '1px solid #ece8e0' }}>
          <div style={{ fontSize: 9, fontWeight: 700, color: '#b8960c', textTransform: 'uppercase', marginBottom: 4 }}>
            Fabric Estimate (display only)
          </div>
          {fabricCalc.panels && fabricCalc.panels.length > 1 && fabricCalc.panels.slice(0, 5).map((p, i) => (
            <div key={i} style={{ fontSize: 10, color: '#666', lineHeight: 1.6 }}>
              Panel {i + 1}: {p.w.toFixed(1)}&quot; &times; {p.h.toFixed(1)}&quot; = {p.sqft.toFixed(2)} sq ft &rarr; {p.yd.toFixed(2)} yd
            </div>
          ))}
          {fabricCalc.panels && fabricCalc.panels.length > 5 && (
            <div style={{ fontSize: 10, color: '#999' }}>... +{fabricCalc.panels.length - 5} more panels</div>
          )}
          {'dimLabel' in fabricCalc && (
            <div style={{ fontSize: 10, color: '#666' }}>{(fabricCalc as any).dimLabel}</div>
          )}
          <div style={{ fontSize: 11, fontWeight: 700, color: '#1a1a1a', marginTop: 4, borderTop: '1px solid #ece8e0', paddingTop: 4 }}>
            Total back panels: {fabricCalc.totalSqft.toFixed(2)} sq ft &rarr; {fabricCalc.totalYd.toFixed(2)} yd
          </div>
        </div>
      )}
    </div>
  );
}

export default function PanelConfigurator({ backWidth, backHeight, config, onChange, itemType, itemLabel }: PanelConfiguratorProps) {
  const printRef = useRef<HTMLDivElement>(null);
  const multiShape = isMultiSection(itemType);
  const [activeSection, setActiveSection] = useState(0);

  const set = (partial: Partial<PanelConfig>) => onChange({ ...config, ...partial });

  // Initialize sections for L/U shapes
  const ensureSections = (): SectionConfig[] => {
    if (config.sections && config.sections.length > 0) return config.sections;
    const labels = getSectionLabels(multiShape || 'L');
    return labels.map(label => ({
      label,
      width: multiShape === 'U' ? Math.round(backWidth / 3) : Math.round(backWidth / 2),
      height: backHeight,
      panelConfig: { ...DEFAULT_SECTION },
    }));
  };

  const updateSection = (idx: number, partial: Partial<SectionConfig>) => {
    const sections = ensureSections();
    sections[idx] = { ...sections[idx], ...partial };
    onChange({ ...config, sections });
  };

  const handlePrint = () => {
    if (!printRef.current) return;
    const printWindow = window.open('', '_blank', 'width=800,height=600');
    if (!printWindow) return;
    const html = printRef.current.innerHTML;
    printWindow.document.write(`<!DOCTYPE html><html><head>
      <title>Back Panel Configuration${itemLabel ? ` — ${itemLabel}` : ''}</title>
      <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', -apple-system, sans-serif; padding: 24px; color: #1a1a1a; }
        h2 { font-size: 16px; margin-bottom: 12px; color: #b8960c; }
        .print-header { border-bottom: 2px solid #b8960c; padding-bottom: 8px; margin-bottom: 16px; }
        .print-header h1 { font-size: 20px; }
        .print-header .sub { font-size: 12px; color: #888; margin-top: 4px; }
        svg { max-width: 100%; }
        input, select, button { display: none; }
        label { pointer-events: none; }
        @media print { body { padding: 12px; } }
      </style>
    </head><body>
      <div class="print-header">
        <h1>Back Panel Configuration</h1>
        <div class="sub">${itemLabel || ''} — ${backWidth}" W × ${backHeight}" H — ${new Date().toLocaleDateString()}</div>
      </div>
      ${html}
    </body></html>`);
    printWindow.document.close();
    setTimeout(() => printWindow.print(), 300);
  };

  return (
    <div ref={printRef} style={{ marginTop: 10, border: '1px solid #f0e6c0', borderRadius: 10, background: '#fdf8eb', overflow: 'hidden' }}>
      {/* Header — always open, with print button */}
      <div
        className="w-full flex items-center justify-between"
        style={{ padding: '8px 12px', background: 'transparent', fontSize: 11, fontWeight: 700, color: '#b8960c' }}
      >
        Back Panel Configuration
        <button
          onClick={handlePrint}
          className="flex items-center gap-1 cursor-pointer hover:opacity-70 transition-opacity"
          style={{ background: 'none', border: 'none', fontSize: 10, fontWeight: 600, color: '#b8960c', padding: '4px 8px' }}
          title="Print / Share"
        >
          <Printer size={13} /> Print
        </button>
      </div>

      <div style={{ padding: '0 12px 12px' }}>
        {/* Multi-section tabs for L/U shaped items */}
        {multiShape ? (
          <div>
            {/* Section tabs */}
            <div style={{ display: 'flex', gap: 0, marginBottom: 12, borderBottom: '2px solid #ece8e0' }}>
              {ensureSections().map((sec, i) => (
                <button
                  key={i}
                  onClick={() => setActiveSection(i)}
                  className="cursor-pointer transition-colors"
                  style={{
                    flex: 1, padding: '8px 12px', fontSize: 11, fontWeight: activeSection === i ? 700 : 500,
                    color: activeSection === i ? '#b8960c' : '#888',
                    background: activeSection === i ? '#fff' : 'transparent',
                    border: 'none',
                    borderBottom: activeSection === i ? '2px solid #b8960c' : '2px solid transparent',
                    marginBottom: -2,
                  }}
                >
                  {sec.label}
                  {sec.panelConfig.style !== 'flat' && (
                    <span style={{ fontSize: 8, marginLeft: 4, opacity: 0.6 }}>
                      ({STYLES.find(s => s.value === sec.panelConfig.style)?.label})
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Active section dimensions */}
            {(() => {
              const sections = ensureSections();
              const sec = sections[activeSection];
              if (!sec) return null;
              return (
                <div>
                  <div style={{ display: 'flex', gap: 10, marginBottom: 10, alignItems: 'end' }}>
                    <div>
                      <label style={{ fontSize: 9, fontWeight: 600, color: '#999' }}>SECTION WIDTH (in)</label>
                      <input type="number" min={0} step={0.5} value={sec.width || ''}
                        onChange={e => updateSection(activeSection, { width: +e.target.value })}
                        style={{ width: 70, fontSize: 11, padding: '4px 6px', borderRadius: 6, border: '1px solid #ece8e0', background: '#fff', textAlign: 'center' as const }}
                      />
                    </div>
                    <div>
                      <label style={{ fontSize: 9, fontWeight: 600, color: '#999' }}>SECTION HEIGHT (in)</label>
                      <input type="number" min={0} step={0.5} value={sec.height || ''}
                        onChange={e => updateSection(activeSection, { height: +e.target.value })}
                        style={{ width: 70, fontSize: 11, padding: '4px 6px', borderRadius: 6, border: '1px solid #ece8e0', background: '#fff', textAlign: 'center' as const }}
                      />
                    </div>
                  </div>

                  <PanelEditor
                    config={sec.panelConfig}
                    onChange={(pc) => updateSection(activeSection, { panelConfig: pc })}
                    backWidth={sec.width}
                    backHeight={sec.height}
                    radioName={`panelStyle-section-${activeSection}`}
                  />
                </div>
              );
            })()}
          </div>
        ) : (
          /* Single-section mode — standard items */
          <PanelEditor
            config={config}
            onChange={(pc) => set(pc)}
            backWidth={backWidth}
            backHeight={backHeight}
            radioName="panelStyle"
          />
        )}
      </div>
    </div>
  );
}
