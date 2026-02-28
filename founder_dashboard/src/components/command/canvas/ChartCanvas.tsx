'use client';
import { useState } from 'react';
import { BarChart3, Table2, X } from 'lucide-react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  AreaChart, Area,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts';
import type { ChartData } from './ContentAnalyzer';

const CHART_COLORS = ['#D4AF37', '#8B5CF6', '#22D3EE', '#D946EF', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4'];

const TOOLTIP_STYLE = {
  contentStyle: {
    background: '#0a0a1a',
    border: '1px solid rgba(212,175,55,0.2)',
    borderRadius: 8,
    fontSize: 12,
    color: '#e4e4e8',
  },
  labelStyle: { color: '#D4AF37' },
};

type ChartType = 'bar' | 'line' | 'pie' | 'area';

interface Props {
  charts: ChartData[];
  /** Render inline (within markdown) vs full canvas mode */
  inline?: boolean;
}

function SingleChart({ data, inline }: { data: ChartData; inline?: boolean }) {
  const [chartType, setChartType] = useState<ChartType>('bar');
  const [showTable, setShowTable] = useState(false);
  const labelKey = data.headers[0];
  const valueKeys = data.headers.slice(1).filter(h =>
    data.rows.some(d => typeof d[h] === 'number')
  );

  if (valueKeys.length === 0) return null;

  const height = inline ? 200 : 280;

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}
    >
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-1.5" style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="flex gap-1">
          {(['bar', 'line', 'area', 'pie'] as const).map(t => (
            <button
              key={t}
              onClick={() => { setChartType(t); setShowTable(false); }}
              className="px-2 py-0.5 rounded text-[9px] font-medium transition-all"
              style={{
                background: chartType === t && !showTable ? 'var(--gold)' : 'var(--elevated)',
                color: chartType === t && !showTable ? '#0a0a0a' : 'var(--text-muted)',
              }}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
          <div style={{ width: 1, background: 'var(--border)', margin: '0 4px' }} />
          <button
            onClick={() => setShowTable(!showTable)}
            className="px-2 py-0.5 rounded text-[9px] font-medium transition-all flex items-center gap-1"
            style={{
              background: showTable ? 'var(--purple)' : 'var(--elevated)',
              color: showTable ? 'white' : 'var(--text-muted)',
            }}
          >
            <Table2 className="w-3 h-3" /> Data
          </button>
        </div>
      </div>

      {/* Chart or Table */}
      {showTable ? (
        <div className="overflow-x-auto max-h-64">
          <table className="w-full text-[11px]" style={{ color: 'var(--text-secondary)' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {data.headers.map(h => (
                  <th key={h} className="px-3 py-1.5 text-left font-medium" style={{ color: 'var(--gold)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row, i) => (
                <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                  {data.headers.map(h => (
                    <td key={h} className="px-3 py-1">{String(row[h] ?? '')}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="px-3 py-2" style={{ width: '100%', height }}>
          <ResponsiveContainer>
            {chartType === 'pie' ? (
              <PieChart>
                <Pie
                  data={data.rows}
                  dataKey={valueKeys[0]}
                  nameKey={labelKey}
                  cx="50%" cy="50%"
                  outerRadius={inline ? 65 : 90}
                  label={(props) => `${props.name || ''} ${((props.percent ?? 0) * 100).toFixed(0)}%`}
                  fontSize={10}
                >
                  {data.rows.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip {...TOOLTIP_STYLE} />
              </PieChart>
            ) : chartType === 'area' ? (
              <AreaChart data={data.rows}>
                <defs>
                  {valueKeys.map((_, i) => (
                    <linearGradient key={i} id={`area-grad-${i}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={CHART_COLORS[i % CHART_COLORS.length]} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={CHART_COLORS[i % CHART_COLORS.length]} stopOpacity={0} />
                    </linearGradient>
                  ))}
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(212,175,55,0.08)" />
                <XAxis dataKey={labelKey} tick={{ fill: '#8888A8', fontSize: 10 }} />
                <YAxis tick={{ fill: '#8888A8', fontSize: 10 }} />
                <Tooltip {...TOOLTIP_STYLE} />
                {valueKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 10 }} />}
                {valueKeys.map((k, i) => (
                  <Area key={k} type="monotone" dataKey={k} stroke={CHART_COLORS[i % CHART_COLORS.length]} fill={`url(#area-grad-${i})`} strokeWidth={2} />
                ))}
              </AreaChart>
            ) : chartType === 'line' ? (
              <LineChart data={data.rows}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(212,175,55,0.08)" />
                <XAxis dataKey={labelKey} tick={{ fill: '#8888A8', fontSize: 10 }} />
                <YAxis tick={{ fill: '#8888A8', fontSize: 10 }} />
                <Tooltip {...TOOLTIP_STYLE} />
                {valueKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 10 }} />}
                {valueKeys.map((k, i) => (
                  <Line key={k} type="monotone" dataKey={k} stroke={CHART_COLORS[i % CHART_COLORS.length]} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                ))}
              </LineChart>
            ) : (
              <BarChart data={data.rows}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(212,175,55,0.08)" />
                <XAxis dataKey={labelKey} tick={{ fill: '#8888A8', fontSize: 10 }} />
                <YAxis tick={{ fill: '#8888A8', fontSize: 10 }} />
                <Tooltip {...TOOLTIP_STYLE} />
                {valueKeys.length > 1 && <Legend wrapperStyle={{ fontSize: 10 }} />}
                {valueKeys.map((k, i) => (
                  <Bar key={k} dataKey={k} fill={CHART_COLORS[i % CHART_COLORS.length]} radius={[4, 4, 0, 0]} />
                ))}
              </BarChart>
            )}
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export default function ChartCanvas({ charts, inline }: Props) {
  if (charts.length === 0) return null;

  return (
    <div className={`flex flex-col gap-3 ${inline ? 'my-2' : ''}`}>
      {charts.map((chart, i) => (
        <SingleChart key={i} data={chart} inline={inline} />
      ))}
    </div>
  );
}
