'use client';

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import type { ChartSpec } from '../lib/chatContent';

const COLORS = ['#b8960c', '#2563eb', '#16a34a', '#dc2626', '#7c3aed', '#0891b2'];

export default function ChatChartBlock({ chart }: { chart: ChartSpec }) {
  const rows = chart.labels.map((name, i) => ({
    name,
    value: chart.data[i] ?? 0,
  }));

  return (
    <div style={{ marginTop: 10, marginBottom: 4, width: '100%', maxWidth: 480 }}>
      {chart.title && (
        <div style={{ fontSize: 12, fontWeight: 700, color: '#555', marginBottom: 6 }}>{chart.title}</div>
      )}
      <div style={{ width: '100%', height: 220 }}>
        <ResponsiveContainer width="100%" height="100%">
          {chart.type === 'pie' ? (
            <PieChart>
              <Pie data={rows} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={72} label>
                {rows.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          ) : chart.type === 'line' ? (
            <LineChart data={rows}>
              <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 10 }} width={40} />
              <Tooltip />
              <Line type="monotone" dataKey="value" stroke="#b8960c" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          ) : (
            <BarChart data={rows}>
              <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} angle={-20} textAnchor="end" height={50} />
              <YAxis tick={{ fontSize: 10 }} width={40} />
              <Tooltip />
              <Bar dataKey="value" fill="#b8960c" radius={[4, 4, 0, 0]} />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
