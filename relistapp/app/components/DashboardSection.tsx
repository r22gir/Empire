'use client';

import { Package, DollarSign, ShoppingCart, TrendingUp, Clock, Globe, Plus, Upload, Share2, Sparkles } from 'lucide-react';
import { mockStats, mockActivities, mockConnections, PLATFORM_COLORS } from '../lib/mock-data';

interface DashboardProps {
  onNavigate: (section: string) => void;
}

export default function DashboardSection({ onNavigate }: DashboardProps) {
  const kpis = [
    { label: 'Active Listings', value: mockStats.active_listings, color: 'var(--green)', icon: Package },
    { label: 'Total Value', value: `$${mockStats.total_value.toLocaleString()}`, color: 'var(--gold)', icon: DollarSign },
    { label: 'Sold This Month', value: mockStats.sold_this_month, color: 'var(--blue)', icon: ShoppingCart },
    { label: 'Revenue', value: `$${mockStats.revenue_this_month.toLocaleString()}`, color: 'var(--green)', icon: TrendingUp },
    { label: 'Avg Days to Sell', value: mockStats.avg_days_to_sell, color: 'var(--purple)', icon: Clock },
    { label: 'Connected Platforms', value: mockStats.total_platforms, color: 'var(--blue)', icon: Globe },
  ];

  const actionBadge: Record<string, { bg: string; color: string; label: string }> = {
    listed: { bg: '#dcfce7', color: '#16a34a', label: 'Listed' },
    sold: { bg: '#dbeafe', color: '#2563eb', label: 'Sold' },
    crossposted: { bg: '#ecfeff', color: '#06b6d4', label: 'Cross-posted' },
    relisted: { bg: '#fdf8eb', color: '#b8960c', label: 'Relisted' },
  };

  const activeConns = mockConnections.filter(c => c.status === 'active');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold mb-1">Dashboard</h1>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Overview of your reselling business</p>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-3 gap-4">
        {kpis.map(kpi => {
          const Icon = kpi.icon;
          return (
            <div key={kpi.label} className="empire-card flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${kpi.color}15` }}>
                <Icon size={20} style={{ color: kpi.color }} />
              </div>
              <div>
                <div className="kpi-value" style={{ color: kpi.color }}>{kpi.value}</div>
                <div className="kpi-label">{kpi.label}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Platform Distribution + Quick Actions */}
      <div className="grid grid-cols-2 gap-4">
        <div className="empire-card">
          <div className="section-label">Platform Distribution</div>
          <div className="space-y-2 mt-3">
            {activeConns.map(c => (
              <div key={c.platform} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ background: PLATFORM_COLORS[c.platform] }} />
                  <span className="text-sm font-medium capitalize">{c.platform}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className="h-2 rounded-full"
                    style={{
                      width: `${Math.max(20, (c.listings_count / 70) * 120)}px`,
                      background: PLATFORM_COLORS[c.platform],
                      opacity: 0.7,
                    }}
                  />
                  <span className="text-sm font-medium w-8 text-right">{c.listings_count}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="empire-card">
          <div className="section-label">Quick Actions</div>
          <div className="grid grid-cols-2 gap-2 mt-3">
            <button onClick={() => onNavigate('listings')} className="btn-primary text-sm justify-center">
              <Plus size={15} /> New Listing
            </button>
            <button className="btn-secondary text-sm justify-center">
              <Upload size={15} /> Bulk Import
            </button>
            <button onClick={() => onNavigate('crosspost')} className="btn-gold text-sm justify-center">
              <Share2 size={15} /> Cross-Post All
            </button>
            <button onClick={() => onNavigate('pricing')} className="btn-secondary text-sm justify-center">
              <Sparkles size={15} /> AI Price Check
            </button>
          </div>
          <div className="mt-3 text-xs p-2 rounded-lg" style={{ background: 'var(--gold-light)', color: 'var(--gold)' }}>
            {mockStats.pending_crossposts} listings pending cross-post
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="empire-card">
        <div className="section-label mb-3">Recent Activity</div>
        <div className="space-y-2">
          {mockActivities.map(act => {
            const badge = actionBadge[act.action] || actionBadge.listed;
            return (
              <div key={act.id} className="flex items-center justify-between py-1.5 border-b last:border-b-0" style={{ borderColor: 'var(--border)' }}>
                <div className="flex items-center gap-3">
                  <span
                    className="text-xs font-medium px-2 py-0.5 rounded-full"
                    style={{ background: badge.bg, color: badge.color }}
                  >
                    {badge.label}
                  </span>
                  <span className="text-sm">{act.listing}</span>
                  {act.platform && (
                    <span className="text-xs capitalize" style={{ color: PLATFORM_COLORS[act.platform] || 'var(--muted)' }}>
                      on {act.platform}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  {'amount' in act && act.amount && (
                    <span className="text-sm font-semibold" style={{ color: 'var(--green)' }}>
                      +${act.amount}
                    </span>
                  )}
                  <span className="text-xs" style={{ color: 'var(--muted)' }}>{act.time}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
