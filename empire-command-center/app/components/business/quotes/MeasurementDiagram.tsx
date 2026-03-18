'use client';

import React, { useMemo } from 'react';

interface MeasurementDiagramProps {
  item: {
    type: 'window' | 'drapery' | 'roman_shade' | 'sofa' | 'chair' | 'cushion' | 'pillow' | 'upholstery' | 'valance' | 'cornices' | string;
    subtype?: string;
    measurements: {
      width_inches: number;
      height_inches: number;
      depth_inches?: number;
      sill_depth?: number;
      stack_space?: number;
    };
    treatment?: string;
    mount_type?: string;
    lining?: string;
    description?: string;
  };
  width?: number;
  height?: number;
  showLabels?: boolean;
  interactive?: boolean;
  onDimensionClick?: (field: string, value: number) => void;
}

const COLORS = {
  black: '#1a1a1a',
  darkGray: '#4a4a4a',
  lightGray: '#e5e5e5',
  glassBlue: '#d4e8f7',
  gold: '#b8960c',
  white: '#ffffff',
};

export default function MeasurementDiagram({
  item,
  width: svgWidth = 400,
  height: svgHeight = 320,
  showLabels = true,
  interactive = false,
  onDimensionClick,
}: MeasurementDiagramProps) {
  const m = item.measurements;
  const itemType = (item.type || 'window').toLowerCase();

  const isWindow = ['window', 'drapery', 'roman_shade', 'valance', 'cornices'].includes(itemType);
  const isFurniture = ['sofa', 'chair', 'upholstery'].includes(itemType);
  const isCushion = ['cushion', 'cushions', 'pillow', 'pillows'].includes(itemType);

  const svgContent = useMemo(() => {
    if (isWindow) return renderWindow(m, item, svgWidth, svgHeight, showLabels);
    if (isFurniture) return renderFurniture(m, item, svgWidth, svgHeight, showLabels);
    if (isCushion) return renderCushion(m, item, svgWidth, svgHeight, showLabels);
    return renderWindow(m, item, svgWidth, svgHeight, showLabels);
  }, [m.width_inches, m.height_inches, m.depth_inches, m.sill_depth, m.stack_space,
      item.mount_type, item.treatment, item.lining, item.subtype, svgWidth, svgHeight, showLabels]);

  const handleClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!interactive || !onDimensionClick) return;
    const target = e.target as SVGElement;
    const field = target.getAttribute('data-field');
    const value = target.getAttribute('data-value');
    if (field && value) {
      onDimensionClick(field, parseFloat(value));
    }
  };

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox={`0 0 ${svgWidth} ${svgHeight}`}
      width="100%"
      height="100%"
      style={{ fontFamily: 'Arial, Helvetica, sans-serif', maxWidth: svgWidth, cursor: interactive ? 'pointer' : 'default' }}
      onClick={handleClick}
      className="measurement-diagram"
    >
      {svgContent}
    </svg>
  );
}

function DimH({ x1, x2, y, label, field, value, small }: {
  x1: number; x2: number; y: number; label: string; field?: string; value?: number; small?: boolean;
}) {
  const arrow = small ? 3 : 5;
  const fs = small ? 10 : 12;
  const mid = (x1 + x2) / 2;
  return (
    <g>
      <line x1={x1} y1={y} x2={x2} y2={y} stroke={COLORS.black} strokeWidth={1} />
      <polygon points={`${x1},${y} ${x1+arrow},${y-arrow/2} ${x1+arrow},${y+arrow/2}`} fill={COLORS.black} />
      <polygon points={`${x2},${y} ${x2-arrow},${y-arrow/2} ${x2-arrow},${y+arrow/2}`} fill={COLORS.black} />
      <line x1={x1} y1={y-6} x2={x1} y2={y+6} stroke={COLORS.black} strokeWidth={0.5} strokeDasharray="2,2" />
      <line x1={x2} y1={y-6} x2={x2} y2={y+6} stroke={COLORS.black} strokeWidth={0.5} strokeDasharray="2,2" />
      <rect x={mid-30} y={y-fs-2} width={60} height={fs+4} fill={COLORS.white} rx={2} />
      <text
        x={mid} y={y-3} textAnchor="middle" fontSize={fs} fill={COLORS.black} fontWeight={500}
        data-field={field} data-value={value} style={field ? { cursor: 'pointer' } : undefined}
      >
        {label}
      </text>
    </g>
  );
}

function DimV({ y1, y2, x, label, field, value }: {
  y1: number; y2: number; x: number; label: string; field?: string; value?: number;
}) {
  const arrow = 5;
  const mid = (y1 + y2) / 2;
  return (
    <g>
      <line x1={x} y1={y1} x2={x} y2={y2} stroke={COLORS.black} strokeWidth={1} />
      <polygon points={`${x},${y1} ${x-arrow/2},${y1+arrow} ${x+arrow/2},${y1+arrow}`} fill={COLORS.black} />
      <polygon points={`${x},${y2} ${x-arrow/2},${y2-arrow} ${x+arrow/2},${y2-arrow}`} fill={COLORS.black} />
      <line x1={x-6} y1={y1} x2={x+6} y2={y1} stroke={COLORS.black} strokeWidth={0.5} strokeDasharray="2,2" />
      <line x1={x-6} y1={y2} x2={x+6} y2={y2} stroke={COLORS.black} strokeWidth={0.5} strokeDasharray="2,2" />
      <rect x={x-8} y={mid-22} width={16} height={44} fill={COLORS.white} rx={2} />
      <text
        x={x} y={mid} textAnchor="middle" fontSize={12} fill={COLORS.black} fontWeight={500}
        transform={`rotate(-90,${x},${mid})`}
        data-field={field} data-value={value} style={field ? { cursor: 'pointer' } : undefined}
      >
        {label}
      </text>
    </g>
  );
}

function renderWindow(
  m: MeasurementDiagramProps['item']['measurements'],
  item: MeasurementDiagramProps['item'],
  svgW: number, svgH: number, showLabels: boolean
) {
  const w = m.width_inches || 48;
  const h = m.height_inches || 72;
  const sill = m.sill_depth || 0;
  const stack = m.stack_space || 0;
  const totalWidth = w + (stack * 2);
  const mount = item.mount_type || 'inside';
  const treatment = item.treatment || item.subtype || '';
  const lining = item.lining || '';

  const margin = 50;
  const labelSpace = 60;
  const drawX = margin + labelSpace;
  const drawY = margin;
  const maxW = svgW - drawX - margin - 30;
  const maxH = svgH - drawY - 100;
  const scale = Math.min(maxW / w, maxH / h);
  const winW = w * scale;
  const winH = h * scale;
  const winX = drawX + (maxW - winW) / 2;
  const winY = drawY + (maxH - winH) / 2;
  const stackPx = stack * scale;

  const labels: string[] = [];
  if (mount) labels.push(`Mount: ${mount.charAt(0).toUpperCase() + mount.slice(1)}`);
  if (treatment) labels.push(treatment.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()));
  if (lining) labels.push(`${lining.charAt(0).toUpperCase() + lining.slice(1)} lining`);

  return (
    <>
      <rect width={svgW} height={svgH} fill={COLORS.white} rx={6} />
      <rect x={1} y={1} width={svgW-2} height={svgH-2} fill="none" stroke={COLORS.lightGray} rx={6} />

      {/* Treatment overlay */}
      {stack > 0 && treatment && (
        <rect x={winX - stackPx} y={winY} width={winW + stackPx * 2} height={winH}
          fill={COLORS.gold} fillOpacity={0.12} stroke={COLORS.gold} strokeWidth={1} strokeDasharray="6,3" rx={2} />
      )}

      {/* Window frame */}
      <rect x={winX} y={winY} width={winW} height={winH}
        fill="none" stroke={COLORS.black} strokeWidth={2} rx={1} />

      {/* Glass */}
      <rect x={winX+6} y={winY+6} width={Math.max(winW-12, 4)} height={Math.max(winH-12, 4)}
        fill={COLORS.glassBlue} fillOpacity={0.4} stroke={COLORS.darkGray} strokeWidth={0.5} />

      {/* Cross-bar */}
      <line x1={winX} y1={winY + winH/2} x2={winX + winW} y2={winY + winH/2}
        stroke={COLORS.darkGray} strokeWidth={1.5} />

      {/* Sill */}
      {sill > 0 && (
        <rect x={winX - 8} y={winY + winH} width={winW + 16} height={Math.min(sill * scale, 14)}
          fill={COLORS.lightGray} stroke={COLORS.black} strokeWidth={1} />
      )}

      {/* Width dimension */}
      <DimH x1={winX} x2={winX + winW} y={winY - 22} label={`${w}"`} field="width_inches" value={w} />

      {/* Height dimension */}
      <DimV y1={winY} y2={winY + winH} x={winX + winW + 22} label={`${h}"`} field="height_inches" value={h} />

      {/* Stack dimensions */}
      {stack > 0 && (
        <>
          <DimH x1={winX - stackPx} x2={winX} y={winY + winH + 30} label={`${stack}"`} small />
          <DimH x1={winX} x2={winX + winW} y={winY + winH + 30} label={`${w}"`} small />
          <DimH x1={winX + winW} x2={winX + winW + stackPx} y={winY + winH + 30} label={`${stack}"`} small />
          <DimH x1={winX - stackPx} x2={winX + winW + stackPx} y={winY + winH + 50}
            label={`${totalWidth}" total rod`} />
        </>
      )}

      {/* Sill depth label */}
      {sill > 0 && (
        <text x={winX + winW + 10} y={winY + winH + 10}
          fontFamily="Arial, Helvetica, sans-serif" fontSize={11} fill={COLORS.darkGray}>
          sill: {sill}&quot;
        </text>
      )}

      {/* Labels */}
      {showLabels && labels.length > 0 && (
        <text x={svgW / 2} y={svgH - 28} textAnchor="middle"
          fontSize={13} fill={COLORS.black} fontWeight={600}>
          {labels.join(' · ')}
        </text>
      )}
    </>
  );
}

function renderFurniture(
  m: MeasurementDiagramProps['item']['measurements'],
  item: MeasurementDiagramProps['item'],
  svgW: number, svgH: number, showLabels: boolean
) {
  const w = m.width_inches || 72;
  const h = m.height_inches || 36;
  const depth = m.depth_inches || 30;
  const cushions = 3;

  const margin = 50;
  const maxW = svgW - margin * 2 - 60;
  const maxH = svgH - margin * 2 - 60;
  const scale = Math.min(maxW / w, maxH / h);
  const fw = w * scale;
  const fh = h * scale;
  const fx = (svgW - fw) / 2;
  const fy = margin + 20;
  const armW = fw * 0.1;

  const cushionArea = fw - armW * 2 - 8;
  const cushionW = (cushionArea - (cushions - 1) * 4) / cushions;
  const cushionH = fh * 0.55;
  const cushionY = fy + fh - cushionH - 6;

  return (
    <>
      <rect width={svgW} height={svgH} fill={COLORS.white} rx={6} />
      <rect x={1} y={1} width={svgW-2} height={svgH-2} fill="none" stroke={COLORS.lightGray} rx={6} />

      {/* Body */}
      <rect x={fx} y={fy} width={fw} height={fh} fill="#f0ede8" stroke={COLORS.black} strokeWidth={2} rx={6} />

      {/* Arms */}
      <rect x={fx} y={fy} width={armW} height={fh} fill="#e8e4de" stroke={COLORS.black} strokeWidth={1.5} rx={4} />
      <rect x={fx + fw - armW} y={fy} width={armW} height={fh} fill="#e8e4de" stroke={COLORS.black} strokeWidth={1.5} rx={4} />

      {/* Cushions */}
      {Array.from({ length: cushions }).map((_, i) => (
        <rect key={i} x={fx + armW + 4 + i * (cushionW + 4)} y={cushionY} width={cushionW} height={cushionH}
          fill={COLORS.gold} fillOpacity={0.15} stroke={COLORS.gold} strokeWidth={1} rx={3} />
      ))}

      <DimH x1={fx} x2={fx + fw} y={fy - 18} label={`${w}"`} field="width_inches" value={w} />
      <DimV y1={fy} y2={fy + fh} x={fx + fw + 22} label={`${h}"`} field="height_inches" value={h} />

      {showLabels && (
        <>
          <text x={svgW / 2} y={svgH - 45} textAnchor="middle" fontSize={13} fill={COLORS.black} fontWeight={600}>
            Depth: {depth}&quot; · {cushions} cushions
          </text>
          <text x={svgW / 2} y={svgH - 25} textAnchor="middle" fontSize={11} fill={COLORS.darkGray}>
            {item.description || item.type || 'Furniture'}
          </text>
        </>
      )}
    </>
  );
}

function renderCushion(
  m: MeasurementDiagramProps['item']['measurements'],
  item: MeasurementDiagramProps['item'],
  svgW: number, svgH: number, showLabels: boolean
) {
  const w = m.width_inches || 20;
  const h = m.height_inches || 20;
  const depth = m.depth_inches || 4;

  const margin = 50;
  const maxS = Math.min(svgW, svgH) - margin * 2 - 50;
  const scale = Math.min(maxS / w, maxS / h);
  const cw = w * scale;
  const ch = h * scale;
  const cx = (svgW - cw) / 2;
  const cy = margin + 10;

  return (
    <>
      <rect width={svgW} height={svgH} fill={COLORS.white} rx={6} />
      <rect x={1} y={1} width={svgW-2} height={svgH-2} fill="none" stroke={COLORS.lightGray} rx={6} />

      <rect x={cx} y={cy} width={cw} height={ch}
        fill={COLORS.gold} fillOpacity={0.12} stroke={COLORS.black} strokeWidth={2} rx={8} />

      {depth > 0 && (
        <>
          <rect x={cx + cw + 20} y={cy + ch * 0.3} width={depth * scale * 0.5} height={ch * 0.4}
            fill="#f0ede8" stroke={COLORS.black} strokeWidth={1} rx={2} />
          <text x={cx + cw + 20 + depth * scale * 0.25} y={cy + ch * 0.7 + 14}
            textAnchor="middle" fontSize={10} fill={COLORS.darkGray}>{depth}&quot;</text>
        </>
      )}

      <DimH x1={cx} x2={cx + cw} y={cy - 16} label={`${w}"`} field="width_inches" value={w} />
      <DimV y1={cy} y2={cy + ch} x={cx - 22} label={`${h}"`} field="height_inches" value={h} />

      {showLabels && (
        <text x={svgW / 2} y={svgH - 25} textAnchor="middle" fontSize={12} fill={COLORS.black} fontWeight={600}>
          {item.description || 'Cushion'}
        </text>
      )}
    </>
  );
}
