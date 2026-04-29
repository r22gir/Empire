/**
 * ComparableSalesSparkline
 * Phase 1 Prototype — mini line chart for comparable sale prices over time
 */

'use client';

import { useState, useEffect } from 'react';
import type { ComparableSale } from '../../schemas/archiveforge-schemas';

interface ComparableSalesSparklineProps {
  sales: ComparableSale[];
  height?: number;
  showTooltip?: boolean;
}

// Try to use recharts if available, otherwise CSS fallback
function ChartRenderer({
  data,
  height,
  showTooltip,
}: {
  data: ComparableSale[];
  height: number;
  showTooltip: boolean;
}) {
  const [RechartsComp, setRechartsComp] = useState<{
    LineChart: React.ComponentType<any>;
    Line: React.ComponentType<any>;
    XAxis: React.ComponentType<any>;
    YAxis: React.ComponentType<any>;
    Tooltip: React.ComponentType<any>;
    ResponsiveContainer: React.ComponentType<any>;
  } | null>(null);
  const [ rechartsError, setRechartsError ] = useState(false);

  useEffect(() => {
    import('recharts')
      .then((mod) => {
        setRechartsComp({
          LineChart: mod.LineChart,
          Line: mod.Line,
          XAxis: mod.XAxis,
          YAxis: mod.YAxis,
          Tooltip: mod.Tooltip,
          ResponsiveContainer: mod.ResponsiveContainer,
        });
      })
      .catch(() => setRechartsError(true));
  }, []);

  if (rechartsError || !RechartsComp) {
    // CSS fallback
    return (
      <div style={{ height, position: 'relative' }} data-testid="sparkline-css-fallback">
        <CSSSparkline data={data} height={height} showTooltip={showTooltip} />
      </div>
    );
  }

  const { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } = RechartsComp;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data}>
        <XAxis
          dataKey="date"
          tickFormatter={(v: string) => {
            const d = new Date(v);
            return `${d.toLocaleString('en-US', { month: 'short' })}`;
          }}
          tick={{ fontSize: 10, fill: '#9ca3af' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tickFormatter={(v: number) => `$${v}`}
          tick={{ fontSize: 10, fill: '#9ca3af' }}
          axisLine={false}
          tickLine={false}
          width={45}
        />
        {showTooltip && (
          <Tooltip
            formatter={(value: number) => [`$${value}`, 'Price']}
            labelFormatter={(label: string) => new Date(label).toLocaleDateString()}
            contentStyle={{
              backgroundColor: '#1f2937',
              border: '1px solid #374151',
              borderRadius: '6px',
              fontSize: '12px',
              color: '#f3f4f6',
            }}
          />
        )}
        <Line
          type="monotone"
          dataKey="price"
          stroke="#6366f1"
          strokeWidth={2}
          dot={{ r: 3, fill: '#6366f1', strokeWidth: 0 }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

function CSSSparkline({
  data,
  height,
  showTooltip,
}: {
  data: ComparableSale[];
  height: number;
  showTooltip: boolean;
}) {
  if (!data.length) return <div style={{ height }} />;

  const prices = data.map((d) => d.price);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const width = 100;
  const padding = 4;

  const points = data.map((d, i) => {
    const x = (i / (data.length - 1)) * (width - padding * 2) + padding;
    const y = height - padding - ((d.price - min) / range) * (height - padding * 2);
    return { x, y, ...d };
  });

  const pathD = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`)
    .join(' ');

  return (
    <div style={{ position: 'relative', height }}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        style={{ width: '100%', height: '100%', overflow: 'visible' }}
      >
        {/* Grid lines */}
        {[0.25, 0.5, 0.75].map((ratio) => {
          const y = height * ratio;
          return (
            <line
              key={ratio}
              x1={0}
              y1={y}
              x2={width}
              y2={y}
              stroke="#374151"
              strokeWidth={0.5}
              strokeDasharray="2,2"
            />
          );
        })}
        {/* Line */}
        <path d={pathD} fill="none" stroke="#6366f1" strokeWidth={2} strokeLinecap="round" />
        {/* Dots */}
        {points.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r={3} fill="#6366f1" />
        ))}
      </svg>
      {showTooltip && (
        <div style={{
          position: 'absolute',
          top: 2,
          right: 2,
          fontSize: 10,
          color: '#9ca3af',
          background: '#1f2937',
          padding: '2px 6px',
          borderRadius: 4,
        }}>
          ${min}–${max}
        </div>
      )}
    </div>
  );
}

export default function ComparableSalesSparkline({
  sales,
  height = 80,
  showTooltip = true,
}: ComparableSalesSparklineProps) {
  if (!sales || sales.length === 0) {
    return (
      <div
        style={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#6b7280',
          fontSize: 12,
          fontStyle: 'italic',
        }}
      >
        No comparable sales yet
      </div>
    );
  }

  return (
    <div data-max-widget="sparkline">
      <ChartRenderer data={sales} height={height} showTooltip={showTooltip} />
    </div>
  );
}
