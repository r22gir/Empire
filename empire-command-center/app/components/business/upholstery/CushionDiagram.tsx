'use client';

import React, { useState, useMemo } from 'react';

interface CushionDiagramProps {
  cushionType: string;
  width: number;
  depth: number;
  height: number;
  diameter?: number;
  frontHeight?: number;
  backHeight?: number;
  shape: string;
  cornerRadius?: number;
  style: string;
  welt: string;
  tufting: string;
  tuftRows?: number;
  tuftCols?: number;
  fillType: string;
  viewMode?: 'top' | 'side' | 'front' | 'all';
}

const GOLD = '#b8960c';
const OFF_WHITE = '#f5f3ef';
const BORDER = '#ece8e0';
const FILL = '#f9f5e8';
const LABEL_SIZE = 11;
const PADDING = 40;
const MAX_WIDTH = 500;
const MAX_HEIGHT = 500;
const ARROW_SIZE = 5;
const TUFT_RADIUS = 4;

// --- Dimension helpers ---

function DimensionLine({
  x1, y1, x2, y2, label, offset = 20, orientation,
}: {
  x1: number; y1: number; x2: number; y2: number;
  label: string; offset?: number;
  orientation: 'horizontal' | 'vertical';
}) {
  if (orientation === 'horizontal') {
    const ly = y1 + offset;
    const mx = (x1 + x2) / 2;
    return (
      <g className="dimension">
        <line x1={x1} y1={y1} x2={x1} y2={ly + 4} stroke={GOLD} strokeWidth={0.5} />
        <line x1={x2} y1={y1} x2={x2} y2={ly + 4} stroke={GOLD} strokeWidth={0.5} />
        <line x1={x1} y1={ly} x2={mx - 18} y2={ly} stroke={GOLD} strokeWidth={0.7} markerEnd="url(#arrowEnd)" />
        <line x1={x2} y1={ly} x2={mx + 18} y2={ly} stroke={GOLD} strokeWidth={0.7} markerEnd="url(#arrowEnd)" />
        <text x={mx} y={ly + 4} textAnchor="middle" fontSize={LABEL_SIZE} fill={GOLD}>{label}</text>
      </g>
    );
  }
  const lx = x1 + offset;
  const my = (y1 + y2) / 2;
  return (
    <g className="dimension">
      <line x1={x1} y1={y1} x2={lx + 4} y2={y1} stroke={GOLD} strokeWidth={0.5} />
      <line x1={x1} y1={y2} x2={lx + 4} y2={y2} stroke={GOLD} strokeWidth={0.5} />
      <line x1={lx} y1={y1} x2={lx} y2={my - 10} stroke={GOLD} strokeWidth={0.7} markerEnd="url(#arrowEnd)" />
      <line x1={lx} y1={y2} x2={lx} y2={my + 10} stroke={GOLD} strokeWidth={0.7} markerEnd="url(#arrowEnd)" />
      <text x={lx + 2} y={my + 4} textAnchor="start" fontSize={LABEL_SIZE} fill={GOLD} transform={`rotate(-90,${lx + 2},${my + 4})`}>{label}</text>
    </g>
  );
}

// --- Tufting patterns ---

function TuftingPattern({
  x, y, w, h, tufting, rows, cols,
}: {
  x: number; y: number; w: number; h: number;
  tufting: string; rows: number; cols: number;
}) {
  if (tufting === 'none') return null;

  const elements: React.ReactNode[] = [];

  if (tufting === 'button_tufted') {
    for (let r = 1; r <= rows; r++) {
      for (let c = 1; c <= cols; c++) {
        const cx = x + (c / (cols + 1)) * w;
        const cy = y + (r / (rows + 1)) * h;
        elements.push(
          <circle key={`bt-${r}-${c}`} cx={cx} cy={cy} r={TUFT_RADIUS} fill={GOLD} opacity={0.6} />
        );
      }
    }
  } else if (tufting === 'diamond_tufted') {
    const spacingX = w / (cols + 1);
    const spacingY = h / (rows + 1);
    for (let r = 1; r <= rows; r++) {
      for (let c = 1; c <= cols; c++) {
        const cx = x + c * spacingX;
        const cy = y + r * spacingY;
        elements.push(
          <circle key={`dt-${r}-${c}`} cx={cx} cy={cy} r={3} fill={GOLD} opacity={0.5} />
        );
        // diamond lines
        if (c < cols) {
          const nx = x + (c + 1) * spacingX;
          const nry = r < rows ? y + (r + 1) * spacingY : cy;
          elements.push(
            <line key={`dl-r-${r}-${c}`} x1={cx} y1={cy} x2={nx} y2={nry} stroke={GOLD} strokeWidth={0.5} opacity={0.35} />
          );
          if (r > 1) {
            const pry = y + (r - 1) * spacingY;
            elements.push(
              <line key={`dl-u-${r}-${c}`} x1={cx} y1={cy} x2={nx} y2={pry} stroke={GOLD} strokeWidth={0.5} opacity={0.35} />
            );
          }
        }
      }
    }
  } else if (tufting === 'biscuit_tufted') {
    const cellW = w / cols;
    const cellH = h / rows;
    const inset = 3;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        elements.push(
          <rect
            key={`bis-${r}-${c}`}
            x={x + c * cellW + inset}
            y={y + r * cellH + inset}
            width={cellW - inset * 2}
            height={cellH - inset * 2}
            rx={2}
            fill="none"
            stroke={GOLD}
            strokeWidth={0.7}
            opacity={0.4}
          />
        );
      }
    }
  }

  return <g>{elements}</g>;
}

// --- Welt edge helper ---

function weltStrokeProps(welt: string) {
  if (welt === 'single_welt') return { strokeWidth: 2.2, strokeDasharray: undefined };
  if (welt === 'double_welt') return { strokeWidth: 3, strokeDasharray: '4 2' };
  if (welt === 'cord') return { strokeWidth: 2.5, strokeDasharray: '2 2' };
  return { strokeWidth: 1.5, strokeDasharray: undefined };
}

// --- Top View ---

function TopView({
  x, y, w, d, shape, cornerRadius, style, welt, tufting, tuftRows, tuftCols, diameter, cushionType,
}: {
  x: number; y: number; w: number; d: number;
  shape: string; cornerRadius: number; style: string;
  welt: string; tufting: string; tuftRows: number; tuftCols: number;
  diameter?: number; cushionType: string;
}) {
  const ws = weltStrokeProps(welt);

  let shapeEl: React.ReactNode;

  if (cushionType === 'round_cushion' || shape === 'round') {
    const r = (diameter ?? Math.min(w, d)) / 2;
    shapeEl = (
      <circle cx={x + w / 2} cy={y + d / 2} r={r} fill={FILL} stroke={GOLD} {...ws} />
    );
  } else if (shape === 't_cushion') {
    const extW = w * 0.18;
    const extD = d * 0.3;
    const pts = [
      `${x + extW},${y}`,
      `${x + w - extW},${y}`,
      `${x + w - extW},${y + extD}`,
      `${x + w},${y + extD}`,
      `${x + w},${y + d}`,
      `${x},${y + d}`,
      `${x},${y + extD}`,
      `${x + extW},${y + extD}`,
    ].join(' ');
    shapeEl = <polygon points={pts} fill={FILL} stroke={GOLD} {...ws} />;
  } else if (shape === 'bullnose') {
    const r = Math.min(w / 2, d * 0.35);
    const pathD = `M${x},${y} L${x + w},${y} L${x + w},${y + d - r} A${r},${r} 0 0 1 ${x + w - r},${y + d} L${x + r},${y + d} A${r},${r} 0 0 1 ${x},${y + d - r} Z`;
    shapeEl = <path d={pathD} fill={FILL} stroke={GOLD} {...ws} />;
  } else if (shape === 'rounded_corners') {
    const cr = cornerRadius || 8;
    shapeEl = <rect x={x} y={y} width={w} height={d} rx={cr} ry={cr} fill={FILL} stroke={GOLD} {...ws} />;
  } else {
    shapeEl = <rect x={x} y={y} width={w} height={d} fill={FILL} stroke={GOLD} {...ws} />;
  }

  return (
    <g>
      <text x={x + w / 2} y={y - 8} textAnchor="middle" fontSize={12} fontWeight={600} fill={GOLD}>Top View</text>
      {shapeEl}
      <TuftingPattern x={x} y={y} w={w} h={d} tufting={tufting} rows={tuftRows} cols={tuftCols} />
      <DimensionLine x1={x} y1={y + d} x2={x + w} y2={y + d} label={`${(w / 10).toFixed(1)}"`} offset={22} orientation="horizontal" />
      <DimensionLine x1={x + w} y1={y} x2={x + w} y2={y + d} label={`${(d / 10).toFixed(1)}"`} offset={22} orientation="vertical" />
    </g>
  );
}

// --- Side View ---

function SideView({
  x, y, d, h, style, frontHeight, backHeight, welt,
}: {
  x: number; y: number; d: number; h: number;
  style: string; frontHeight?: number; backHeight?: number; welt: string;
}) {
  const ws = weltStrokeProps(welt);
  let shapeEl: React.ReactNode;

  if (style === 'knife_edge') {
    const mid = h * 0.15;
    const pathD = `M${x},${y + h / 2} L${x + d},${y + mid} L${x + d},${y + h - mid} Z`;
    shapeEl = <path d={pathD} fill={FILL} stroke={GOLD} {...ws} />;
  } else if (style === 'waterfall') {
    const curveR = h * 0.6;
    const pathD = `M${x},${y} L${x + d - curveR},${y} Q${x + d},${y} ${x + d},${y + curveR} L${x + d},${y + h} L${x},${y + h} Z`;
    shapeEl = <path d={pathD} fill={FILL} stroke={GOLD} {...ws} />;
  } else if (frontHeight != null && backHeight != null && frontHeight !== backHeight) {
    // wedge
    const fh = frontHeight * 10;
    const bh = backHeight * 10;
    const scale = h / Math.max(fh, bh);
    const sfh = fh * scale;
    const sbh = bh * scale;
    const baseY = y + h;
    shapeEl = (
      <polygon
        points={`${x},${baseY - sbh} ${x + d},${baseY - sfh} ${x + d},${baseY} ${x},${baseY}`}
        fill={FILL} stroke={GOLD} {...ws}
      />
    );
  } else if (style === 'box_cushion' || style === 'turkish_corners') {
    // boxing band rectangle
    shapeEl = (
      <g>
        <rect x={x} y={y} width={d} height={h} fill={FILL} stroke={GOLD} {...ws} />
        <line x1={x} y1={y + 2} x2={x + d} y2={y + 2} stroke={GOLD} strokeWidth={0.5} strokeDasharray="3 2" opacity={0.5} />
        <line x1={x} y1={y + h - 2} x2={x + d} y2={y + h - 2} stroke={GOLD} strokeWidth={0.5} strokeDasharray="3 2" opacity={0.5} />
      </g>
    );
  } else {
    shapeEl = <rect x={x} y={y} width={d} height={h} fill={FILL} stroke={GOLD} {...ws} />;
  }

  return (
    <g>
      <text x={x + d / 2} y={y - 8} textAnchor="middle" fontSize={12} fontWeight={600} fill={GOLD}>Side View</text>
      {shapeEl}
      <DimensionLine x1={x} y1={y + h} x2={x + d} y2={y + h} label={`${(d / 10).toFixed(1)}"`} offset={22} orientation="horizontal" />
      <DimensionLine x1={x + d} y1={y} x2={x + d} y2={y + h} label={`${(h / 10).toFixed(1)}"`} offset={22} orientation="vertical" />
    </g>
  );
}

// --- Front View ---

function FrontView({
  x, y, w, h, shape, style, welt,
}: {
  x: number; y: number; w: number; h: number;
  shape: string; style: string; welt: string;
}) {
  const ws = weltStrokeProps(welt);
  let shapeEl: React.ReactNode;

  if (shape === 'bullnose') {
    const curveH = h * 0.35;
    const pathD = `M${x},${y + curveH} Q${x + w / 2},${y - curveH * 0.3} ${x + w},${y + curveH} L${x + w},${y + h} L${x},${y + h} Z`;
    shapeEl = <path d={pathD} fill={FILL} stroke={GOLD} {...ws} />;
  } else {
    shapeEl = <rect x={x} y={y} width={w} height={h} fill={FILL} stroke={GOLD} {...ws} />;
  }

  // channel lines
  const channelLines: React.ReactNode[] = [];
  if (style === 'channel') {
    const count = 5;
    for (let i = 1; i < count; i++) {
      const lx = x + (i / count) * w;
      channelLines.push(
        <line key={`ch-${i}`} x1={lx} y1={y} x2={lx} y2={y + h} stroke={GOLD} strokeWidth={0.7} opacity={0.45} />
      );
    }
  }

  return (
    <g>
      <text x={x + w / 2} y={y - 8} textAnchor="middle" fontSize={12} fontWeight={600} fill={GOLD}>Front View</text>
      {shapeEl}
      {channelLines}
      <DimensionLine x1={x} y1={y + h} x2={x + w} y2={y + h} label={`${(w / 10).toFixed(1)}"`} offset={22} orientation="horizontal" />
      <DimensionLine x1={x + w} y1={y} x2={x + w} y2={y + h} label={`${(h / 10).toFixed(1)}"`} offset={22} orientation="vertical" />
    </g>
  );
}

// --- Main Component ---

export default function CushionDiagram({
  cushionType,
  width,
  depth,
  height,
  diameter,
  frontHeight,
  backHeight,
  shape,
  cornerRadius,
  style,
  welt,
  tufting,
  tuftRows,
  tuftCols,
  fillType,
  viewMode: viewModeProp,
}: CushionDiagramProps) {
  const [activeView, setActiveView] = useState<'top' | 'side' | 'front' | 'all'>(viewModeProp ?? 'all');

  // Scale inches to drawing units (10px per inch base)
  const baseScale = 10;
  const rawW = width * baseScale;
  const rawD = depth * baseScale;
  const rawH = height * baseScale;

  const dims = useMemo(() => {
    const dimPad = PADDING * 2;

    if (activeView === 'top') {
      const totalW = rawW + dimPad;
      const totalH = rawD + dimPad;
      const s = Math.min(MAX_WIDTH / totalW, MAX_HEIGHT / totalH, 1.5);
      return { svgW: totalW * s, svgH: totalH * s, scale: s };
    }
    if (activeView === 'side') {
      const totalW = rawD + dimPad;
      const totalH = rawH + dimPad;
      const s = Math.min(MAX_WIDTH / totalW, MAX_HEIGHT / totalH, 1.5);
      return { svgW: totalW * s, svgH: totalH * s, scale: s };
    }
    if (activeView === 'front') {
      const totalW = rawW + dimPad;
      const totalH = rawH + dimPad;
      const s = Math.min(MAX_WIDTH / totalW, MAX_HEIGHT / totalH, 1.5);
      return { svgW: totalW * s, svgH: totalH * s, scale: s };
    }
    // all views: top on left, side+front stacked on right
    const leftW = rawW + dimPad;
    const leftH = rawD + dimPad;
    const rightW = Math.max(rawD, rawW) + dimPad;
    const rightH = rawH * 2 + dimPad * 2 + 20;
    const totalW = leftW + rightW + 20;
    const totalH = Math.max(leftH, rightH);
    const s = Math.min(MAX_WIDTH / totalW, MAX_HEIGHT / totalH, 1.2);
    return { svgW: totalW * s, svgH: totalH * s, scale: s };
  }, [activeView, rawW, rawD, rawH]);

  const { svgW, svgH, scale } = dims;
  const sw = rawW * scale;
  const sd = rawD * scale;
  const sh = rawH * scale;
  const cr = (cornerRadius ?? 8) * scale;

  const rows = tuftRows ?? 3;
  const cols = tuftCols ?? 4;

  const showTabs = viewModeProp === 'all' || viewModeProp == null;

  const tabs: { key: 'top' | 'side' | 'front' | 'all'; label: string }[] = [
    { key: 'top', label: 'Top' },
    { key: 'side', label: 'Side' },
    { key: 'front', label: 'Front' },
    { key: 'all', label: 'All Views' },
  ];

  return (
    <div style={{ background: OFF_WHITE, border: `1px solid ${BORDER}`, borderRadius: 8, padding: 12, display: 'inline-block' }}>
      {showTabs && (
        <div style={{ display: 'flex', gap: 4, marginBottom: 8 }}>
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveView(tab.key)}
              style={{
                padding: '4px 12px',
                fontSize: 12,
                fontWeight: activeView === tab.key ? 700 : 400,
                background: activeView === tab.key ? GOLD : 'transparent',
                color: activeView === tab.key ? '#fff' : GOLD,
                border: `1px solid ${GOLD}`,
                borderRadius: 4,
                cursor: 'pointer',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      )}
      <svg
        width={svgW}
        height={svgH}
        viewBox={`0 0 ${svgW} ${svgH}`}
        xmlns="http://www.w3.org/2000/svg"
        style={{ display: 'block' }}
      >
        <defs>
          <marker id="arrowEnd" markerWidth={ARROW_SIZE} markerHeight={ARROW_SIZE} refX={ARROW_SIZE} refY={ARROW_SIZE / 2} orient="auto">
            <path d={`M0,0 L${ARROW_SIZE},${ARROW_SIZE / 2} L0,${ARROW_SIZE}`} fill={GOLD} />
          </marker>
        </defs>

        {(activeView === 'top' || activeView === 'all') && (
          <TopView
            x={PADDING * scale}
            y={PADDING * scale}
            w={sw}
            d={sd}
            shape={shape}
            cornerRadius={cr}
            style={style}
            welt={welt}
            tufting={tufting}
            tuftRows={rows}
            tuftCols={cols}
            diameter={diameter ? diameter * scale * baseScale : undefined}
            cushionType={cushionType}
          />
        )}

        {(activeView === 'side' || activeView === 'all') && (() => {
          const ox = activeView === 'all' ? PADDING * scale + sw + 40 * scale : PADDING * scale;
          const oy = PADDING * scale;
          return (
            <SideView
              x={ox}
              y={oy}
              d={activeView === 'all' ? Math.min(sd, sw) : sd}
              h={sh}
              style={style}
              frontHeight={frontHeight}
              backHeight={backHeight}
              welt={welt}
            />
          );
        })()}

        {(activeView === 'front' || activeView === 'all') && (() => {
          const ox = activeView === 'all' ? PADDING * scale + sw + 40 * scale : PADDING * scale;
          const oy = activeView === 'all' ? PADDING * scale + sh + 40 * scale : PADDING * scale;
          return (
            <FrontView
              x={ox}
              y={oy}
              w={activeView === 'all' ? Math.min(sw, sd) : sw}
              h={sh}
              shape={shape}
              style={style}
              welt={welt}
            />
          );
        })()}
      </svg>

      <div style={{ marginTop: 6, fontSize: 11, color: '#888', textAlign: 'center' }}>
        {cushionType.replace(/_/g, ' ')} &middot; {style.replace(/_/g, ' ')} &middot; {fillType.replace(/_/g, ' ')}
      </div>
    </div>
  );
}
