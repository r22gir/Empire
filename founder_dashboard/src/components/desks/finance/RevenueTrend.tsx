'use client';
import { MOCK_REVENUE_TREND } from '@/lib/deskData';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';

export default function RevenueTrend() {
  return (
    <div className="rounded-xl p-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      <p className="text-xs font-semibold mb-3" style={{ color: 'var(--gold)' }}>Monthly Revenue Trend</p>
      <div style={{ height: 220 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={MOCK_REVENUE_TREND}>
            <defs>
              <linearGradient id="goldGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#D4AF37" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#D4AF37" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="redGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(212,175,55,0.08)" />
            <XAxis dataKey="month" tick={{ fill: '#8888A8', fontSize: 10 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: '#8888A8', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
            <Tooltip
              contentStyle={{ background: '#0f0f22', border: '1px solid rgba(212,175,55,0.2)', borderRadius: 8, fontSize: 11 }}
              labelStyle={{ color: '#D4AF37' }}
              formatter={(value: number | undefined) => ['$' + (value ?? 0).toLocaleString()]}
            />
            <Area type="monotone" dataKey="revenue" stroke="#D4AF37" fill="url(#goldGrad)" strokeWidth={2} name="Revenue" />
            <Area type="monotone" dataKey="expenses" stroke="#ef4444" fill="url(#redGrad)" strokeWidth={1.5} name="Expenses" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
