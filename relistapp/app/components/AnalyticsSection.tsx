'use client';

import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { TrendingUp, Eye, DollarSign } from 'lucide-react';
import {
  mockRevenueByPlatform, mockSalesTrend, mockStatusBreakdown,
  mockCategoryRevenue, mockDaysToSellByPlatform, PLATFORM_COLORS, mockListings,
} from '../lib/mock-data';

const CHART_COLORS = ['#06b6d4', '#b8960c', '#16a34a', '#7c3aed', '#dc2626', '#d97706'];

export default function AnalyticsSection() {
  const topListings = [...mockListings]
    .filter(l => l.views && l.views > 0)
    .sort((a, b) => (b.views || 0) - (a.views || 0))
    .slice(0, 10);

  const soldListings = mockListings.filter(l => l.status === 'sold');
  const sellThroughRate = mockListings.length > 0 ? (soldListings.length / mockListings.length) * 100 : 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Analytics</h1>
        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Performance insights and trends</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="empire-card text-center">
          <div className="section-label">Sell-Through Rate</div>
          <div className="text-3xl font-bold mt-2" style={{ color: 'var(--teal)' }}>{sellThroughRate.toFixed(1)}%</div>
          <div className="text-xs mt-1" style={{ color: 'var(--muted)' }}>{soldListings.length} of {mockListings.length} listed</div>
        </div>
        <div className="empire-card text-center">
          <div className="section-label">Total Revenue (90d)</div>
          <div className="text-3xl font-bold mt-2" style={{ color: 'var(--green)' }}>$4,375</div>
          <div className="text-xs mt-1 flex items-center justify-center gap-1" style={{ color: 'var(--green)' }}>
            <TrendingUp size={12} /> +18% vs prior period
          </div>
        </div>
        <div className="empire-card text-center">
          <div className="section-label">Avg Profit per Sale</div>
          <div className="text-3xl font-bold mt-2" style={{ color: 'var(--gold)' }}>$62.40</div>
          <div className="text-xs mt-1" style={{ color: 'var(--muted)' }}>After fees & shipping</div>
        </div>
      </div>

      {/* Revenue by Platform + Status Breakdown */}
      <div className="grid grid-cols-2 gap-4">
        <div className="empire-card">
          <div className="section-label mb-3">Revenue by Platform (30 Days)</div>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={mockRevenueByPlatform}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ece8e0" />
              <XAxis dataKey="platform" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} tickFormatter={v => `$${v}`} />
              <Tooltip formatter={(v) => [`$${v}`, 'Revenue']} />
              <Bar dataKey="revenue" radius={[6, 6, 0, 0]}>
                {mockRevenueByPlatform.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="empire-card">
          <div className="section-label mb-3">Listings by Status</div>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={mockStatusBreakdown}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={90}
                paddingAngle={3}
                dataKey="value"
              >
                {mockStatusBreakdown.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Sales Trend */}
      <div className="empire-card">
        <div className="section-label mb-3">Sales Trend (90 Days)</div>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={mockSalesTrend}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ece8e0" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis yAxisId="left" tick={{ fontSize: 12 }} tickFormatter={v => `$${v}`} />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Line yAxisId="left" type="monotone" dataKey="revenue" stroke="#06b6d4" strokeWidth={2} name="Revenue ($)" dot={{ r: 3 }} />
            <Line yAxisId="right" type="monotone" dataKey="sales" stroke="#b8960c" strokeWidth={2} name="Sales (#)" dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Category Revenue + Days to Sell */}
      <div className="grid grid-cols-2 gap-4">
        <div className="empire-card">
          <div className="section-label mb-3">Top Categories by Revenue</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart layout="vertical" data={mockCategoryRevenue}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ece8e0" />
              <XAxis type="number" tick={{ fontSize: 12 }} tickFormatter={v => `$${v}`} />
              <YAxis type="category" dataKey="category" tick={{ fontSize: 12 }} width={80} />
              <Tooltip formatter={(v) => [`$${v}`, 'Revenue']} />
              <Bar dataKey="revenue" radius={[0, 6, 6, 0]} fill="#b8960c" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="empire-card">
          <div className="section-label mb-3">Avg Days to Sell by Platform</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={mockDaysToSellByPlatform}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ece8e0" />
              <XAxis dataKey="platform" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v) => [`${v} days`, 'Avg Days']} />
              <Bar dataKey="days" radius={[6, 6, 0, 0]}>
                {mockDaysToSellByPlatform.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Best Performing Listings */}
      <div className="empire-card">
        <div className="section-label mb-3">Best Performing Listings</div>
        <table className="empire-table text-sm">
          <thead>
            <tr><th>#</th><th>Listing</th><th>Price</th><th>Views</th><th>Favorites</th><th>Platforms</th><th>Status</th></tr>
          </thead>
          <tbody>
            {topListings.map((listing, i) => (
              <tr key={listing.id}>
                <td className="font-bold" style={{ color: 'var(--muted)' }}>{i + 1}</td>
                <td className="font-medium">{listing.title}</td>
                <td style={{ color: 'var(--gold)' }}>${listing.price.toFixed(2)}</td>
                <td>
                  <span className="flex items-center gap-1"><Eye size={12} /> {listing.views}</span>
                </td>
                <td>{listing.favorites}</td>
                <td>
                  <div className="flex gap-0.5">
                    {listing.platforms.map(p => <div key={p.platform} className={`platform-dot ${p.platform}`} />)}
                  </div>
                </td>
                <td><span className={`status-pill ${listing.status}`}>{listing.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
