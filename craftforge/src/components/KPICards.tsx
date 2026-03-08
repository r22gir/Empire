'use client';
import { DollarSign, Ruler, ListTodo, Package, TrendingUp, AlertTriangle } from 'lucide-react';

export default function KPICards({ dashboard }: { dashboard: any }) {
  if (!dashboard) return <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 animate-pulse">{Array(4).fill(0).map((_, i) => <div key={i} className="h-28 bg-white rounded-xl border border-[#e5e0d8]" />)}</div>;

  const cards = [
    {
      icon: DollarSign, iconBg: '#fdf8eb', iconColor: '#c9a84c',
      label: 'Pipeline', value: `$${dashboard.pipeline?.toLocaleString() || '0'}`,
      sub: `${dashboard.total_designs || 0} designs`, trend: dashboard.revenue > 0 ? `$${dashboard.revenue.toLocaleString()} earned` : undefined,
    },
    {
      icon: Ruler, iconBg: '#dbeafe', iconColor: '#2563eb',
      label: 'Active Designs', value: String(dashboard.total_designs || 0),
      sub: Object.entries(dashboard.designs_by_status || {}).map(([k, v]) => `${v} ${k}`).join(', ') || 'None yet',
    },
    {
      icon: ListTodo, iconBg: '#dcfce7', iconColor: '#16a34a',
      label: 'Production', value: String(dashboard.jobs?.active || 0),
      sub: `${dashboard.jobs?.queued || 0} queued · ${dashboard.jobs?.completed || 0} done`,
      trend: dashboard.jobs?.in_progress > 0 ? `${dashboard.jobs.in_progress} cutting` : undefined,
    },
    {
      icon: Package, iconBg: '#ede9fe', iconColor: '#7c3aed',
      label: 'Inventory', value: `$${(dashboard.inventory?.total_value || 0).toLocaleString()}`,
      sub: `${dashboard.inventory?.total_items || 0} items`,
      alert: dashboard.inventory?.low_stock > 0 ? `${dashboard.inventory.low_stock} low stock` : undefined,
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {cards.map((c, i) => (
        <div key={i} className="bg-white border border-[#e5e0d8] rounded-xl p-4 hover:shadow-[0_4px_12px_rgba(0,0,0,0.06)] hover:border-[#c9a84c] transition-all cursor-pointer">
          <div className="flex items-center justify-between mb-2">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: c.iconBg, color: c.iconColor }}>
              <c.icon size={18} />
            </div>
            {c.trend && <span className="text-[10px] font-bold text-[#16a34a] bg-[#dcfce7] px-1.5 py-0.5 rounded">{c.trend}</span>}
            {c.alert && <span className="text-[10px] font-bold text-[#d97706] bg-[#fef3c7] px-1.5 py-0.5 rounded flex items-center gap-0.5"><AlertTriangle size={10} />{c.alert}</span>}
          </div>
          <div className="text-2xl font-bold text-[#1a1a1a]">{c.value}</div>
          <div className="text-[10px] text-[#777] font-medium mt-0.5">{c.label}</div>
          <div className="text-[9px] text-[#aaa] mt-0.5">{c.sub}</div>
        </div>
      ))}
    </div>
  );
}
