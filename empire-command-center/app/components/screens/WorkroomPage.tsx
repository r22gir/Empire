'use client';
import { useState, useEffect } from 'react';
import { API } from '../../lib/api';
import { Scissors, Package, Truck, Users, DollarSign, ClipboardList, Calendar, TrendingUp } from 'lucide-react';

export default function WorkroomPage() {
  const [quotes, setQuotes] = useState<any[]>([]);
  const [stats, setStats] = useState({ pipeline: 0, openQuotes: 0, accepted: 0 });

  useEffect(() => {
    fetch(API + '/quotes?limit=20').then(r => r.json()).then(data => {
      const q = data.quotes || data || [];
      setQuotes(q);
      setStats({
        pipeline: q.reduce((s: number, x: any) => s + (x.total || 0), 0),
        openQuotes: q.filter((x: any) => x.status !== 'accepted').length,
        accepted: q.filter((x: any) => x.status === 'accepted').length,
      });
    }).catch(() => {});
  }, []);

  return (
    <div className="flex-1 overflow-y-auto p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-1">
        <div className="w-10 h-10 rounded-xl bg-[#dcfce7] flex items-center justify-center">
          <Scissors size={20} className="text-[#16a34a]" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[#1a1a1a]">Empire Workroom</h1>
          <p className="text-xs text-[#777]" suppressHydrationWarning>Custom Drapery & Upholstery · {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-3 mt-5 mb-6">
        <KPI icon={<DollarSign size={18} />} iconBg="#fdf8eb" iconColor="#b8960c" label="Pipeline" value={`$${stats.pipeline.toLocaleString()}`} sub={`${quotes.length} quotes`} trend="+12%" />
        <KPI icon={<ClipboardList size={18} />} iconBg="#fef3c7" iconColor="#d97706" label="Open Quotes" value={String(stats.openQuotes)} sub="Awaiting approval" />
        <KPI icon={<TrendingUp size={18} />} iconBg="#dcfce7" iconColor="#16a34a" label="Accepted" value={String(stats.accepted)} sub="Ready to produce" trend="+3" />
        <KPI icon={<Calendar size={18} />} iconBg="#ede9fe" iconColor="#7c3aed" label="In Production" value="--" sub="Active jobs" />
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-[1fr_1fr] gap-4 mb-6">
        {/* Recent Quotes */}
        <div className="bg-white border border-[#e5e0d8] rounded-xl p-5">
          <h3 className="text-sm font-bold text-[#1a1a1a] mb-3 flex items-center gap-2">
            <ClipboardList size={15} className="text-[#b8960c]" /> Recent Quotes
          </h3>
          <div className="space-y-2">
            {quotes.slice(0, 5).map((q, i) => (
              <div key={i} className="flex items-center justify-between p-3 rounded-lg border border-[#ece8e1] hover:border-[#b8960c] hover:bg-[#fdf8eb] transition-all cursor-pointer">
                <div>
                  <div className="text-xs font-semibold text-[#1a1a1a]">{q.quote_number || `Q-${i + 1}`}</div>
                  <div className="text-[10px] text-[#777]">{q.customer_name || 'Customer'}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-[#b8960c]">${(q.total || 0).toLocaleString()}</div>
                  <StatusBadge status={q.status} />
                </div>
              </div>
            ))}
            {quotes.length === 0 && <div className="text-xs text-[#aaa] text-center py-4">No quotes yet</div>}
          </div>
        </div>

        {/* Production Queue */}
        <div className="bg-white border border-[#e5e0d8] rounded-xl p-5">
          <h3 className="text-sm font-bold text-[#1a1a1a] mb-3 flex items-center gap-2">
            <Package size={15} className="text-[#16a34a]" /> Production & Inventory
          </h3>
          <div className="space-y-2">
            <InfoRow icon={<Package size={14} />} label="Fabrics in Stock" value="--" color="#16a34a" />
            <InfoRow icon={<Scissors size={14} />} label="Hardware Inventory" value="--" color="#b8960c" />
            <InfoRow icon={<Truck size={14} />} label="Pending Shipments" value="--" color="#2563eb" />
            <InfoRow icon={<Users size={14} />} label="Active Customers" value={String(new Set(quotes.map(q => q.customer_name)).size)} color="#7c3aed" />
          </div>
          <div className="mt-4 p-3 rounded-lg bg-[#f0fdf4] border border-[#bbf7d0]">
            <div className="text-[10px] font-bold text-[#16a34a] mb-1">PRODUCTION STATUS</div>
            <div className="text-xs text-[#555]">No active production jobs. Approve quotes to begin.</div>
          </div>
        </div>
      </div>

      {/* Revenue chart placeholder */}
      <div className="bg-white border border-[#e5e0d8] rounded-xl p-5 min-h-[180px] flex items-center justify-center">
        <div className="text-center">
          <TrendingUp size={32} className="text-[#d8d3cb] mx-auto mb-2" />
          <div className="text-sm font-semibold text-[#aaa]">Revenue Trend</div>
          <div className="text-[11px] text-[#ccc] mt-1">Monthly revenue chart · Click to expand</div>
        </div>
      </div>
    </div>
  );
}

function KPI({ icon, iconBg, iconColor, label, value, sub, trend }: { icon: React.ReactNode; iconBg: string; iconColor: string; label: string; value: string; sub: string; trend?: string }) {
  return (
    <div className="bg-white border border-[#e5e0d8] rounded-xl p-4 hover:shadow-[0_4px_12px_rgba(0,0,0,0.06)] hover:border-[#b8960c] transition-all cursor-pointer">
      <div className="flex items-center justify-between mb-2">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: iconBg, color: iconColor }}>{icon}</div>
        {trend && <span className="text-[10px] font-bold text-[#16a34a] bg-[#dcfce7] px-1.5 py-0.5 rounded">{trend}</span>}
      </div>
      <div className="text-2xl font-bold text-[#1a1a1a]">{value}</div>
      <div className="text-[10px] text-[#777] font-medium mt-0.5">{label}</div>
      <div className="text-[9px] text-[#aaa] mt-0.5">{sub}</div>
    </div>
  );
}

function InfoRow({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string; color: string }) {
  return (
    <div className="flex items-center justify-between p-3 rounded-lg border border-[#ece8e1] bg-[#faf9f7]">
      <div className="flex items-center gap-2">
        <span style={{ color }}>{icon}</span>
        <span className="text-xs text-[#555]">{label}</span>
      </div>
      <span className="text-sm font-bold" style={{ color }}>{value}</span>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const s = status || 'draft';
  const colors: Record<string, string> = {
    draft: 'bg-[#f5f3ef] text-[#777]',
    sent: 'bg-[#dbeafe] text-[#2563eb]',
    accepted: 'bg-[#dcfce7] text-[#16a34a]',
    rejected: 'bg-[#fee2e2] text-[#dc2626]',
  };
  return <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${colors[s] || colors.draft}`}>{s.toUpperCase()}</span>;
}
