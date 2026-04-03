'use client';
import React, { useState, useEffect } from 'react';
import { API } from '../../lib/api';
import { useTranslation } from '../../lib/i18n';
import {
  BarChart3, Search, Package, RefreshCw, ShoppingCart, DollarSign,
  TrendingUp, AlertTriangle, ExternalLink, Plus, Eye, Heart,
  ArrowRight, Clock, CheckCircle, Loader2, Link, Target, Tag,
  Calculator, Activity, Filter, ChevronRight, Globe, Star
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';

const RA_API = `${API}/relist`;

const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
  { id: 'scout', label: 'Product Scout', icon: Search },
  { id: 'listings', label: 'My Listings', icon: Package },
  { id: 'crosslist', label: 'Cross-List', icon: Link },
  { id: 'orders', label: 'Orders', icon: ShoppingCart },
  { id: 'pricemon', label: 'Price Monitor', icon: TrendingUp },
  { id: 'calculator', label: 'Profit Calculator', icon: Calculator },
  { id: 'analytics', label: 'Analytics', icon: Activity },
  { id: 'docs', label: 'Docs', icon: BarChart3 },
] as const;

type Section = typeof NAV[number]['id'];

const PLATFORM_COLORS: Record<string, string> = {
  ebay: '#e53238', poshmark: '#7b2d8e', mercari: '#4dc0ff', facebook_marketplace: '#1877f2',
  offerup: '#00ab80', etsy: '#f56400', amazon: '#ff9900', walmart: '#0071dc',
};

interface RelistAppPageProps { initialSection?: string; }

export default function RelistAppPage({ initialSection }: RelistAppPageProps) {
  const [section, setSection] = useState<Section>((initialSection as Section) || 'dashboard');
  const { t } = useTranslation('relist');

  useEffect(() => { if (initialSection) setSection(initialSection as Section); }, [initialSection]);

  const renderContent = () => {
    switch (section) {
      case 'dashboard': return <DashboardSection />;
      case 'scout': return <ScoutSection />;
      case 'listings': return <ListingsSection />;
      case 'crosslist': return <CrossListSection />;
      case 'orders': return <OrdersSection />;
      case 'pricemon': return <PriceMonitorSection />;
      case 'calculator': return <CalculatorSection />;
      case 'analytics': return <AnalyticsSection />;
      case 'docs': return <ProductDocs product="relist" />;
      default: return <DashboardSection />;
    }
  };

  return (
    <div style={{ display: 'flex', height: '100%', background: '#faf9f7' }}>
      <div style={{ width: 200, borderRight: '1px solid #e5e2dc', padding: '16px 0', flexShrink: 0, overflowY: 'auto' }}>
        <div style={{ padding: '0 16px 12px', borderBottom: '1px solid #e5e2dc', marginBottom: 8 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#06b6d4', display: 'flex', alignItems: 'center', gap: 6 }}>
            <RefreshCw size={16} /> RelistApp
          </div>
          <div style={{ fontSize: 10, color: '#999', marginTop: 2 }}>Drop-Ship Arbitrage Engine</div>
        </div>
        {NAV.map(n => (
          <button key={n.id} onClick={() => setSection(n.id)} style={{
            display: 'flex', alignItems: 'center', gap: 8, width: '100%', padding: '8px 16px',
            border: 'none', cursor: 'pointer', background: section === n.id ? '#ecfeff' : 'transparent',
            color: section === n.id ? '#06b6d4' : '#666', fontWeight: section === n.id ? 600 : 400,
            fontSize: 12, textAlign: 'left',
          }}>
            <n.icon size={14} /> {n.label}
          </button>
        ))}
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>{renderContent()}</div>
    </div>
  );
}

function SH({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
      <div>
        <h2 style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>{title}</h2>
        {subtitle && <p style={{ fontSize: 12, color: '#888', marginTop: 2 }}>{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

function Kpi({ label, value, color, sub }: { label: string; value: string | number; color?: string; sub?: string }) {
  return (
    <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: '16px 18px', flex: 1, minWidth: 130 }}>
      <div style={{ fontSize: 10, fontWeight: 600, color: '#888', textTransform: 'uppercase' }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: color || '#1a1a1a', marginTop: 4 }}>{value}</div>
      {sub && <div style={{ fontSize: 10, color: '#aaa', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function DashboardSection() {
  const [stats, setStats] = useState<any>({});
  useEffect(() => {
    fetch(`${RA_API}/analytics/dashboard`).then(r => r.json()).then(setStats).catch(() => {});
  }, []);
  return (
    <div>
      <SH title="RelistApp Dashboard" subtitle="Drop-ship arbitrage overview" />
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
        <Kpi label="Total Profit (Month)" value={`$${(stats.monthly_profit || 0).toFixed(2)}`} color="#16a34a" />
        <Kpi label="Active Listings" value={stats.active_listings ?? '—'} color="#06b6d4" />
        <Kpi label="Pending Orders" value={stats.pending_orders ?? '—'} color="#b8960c" />
        <Kpi label="Average ROI" value={`${(stats.avg_roi || 0).toFixed(0)}%`} color="#8b5cf6" />
      </div>
      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16 }}>
        <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Quick Actions</h3>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {[
            { label: 'Import Product URL', icon: Link, color: '#06b6d4' },
            { label: 'AI Deal Finder', icon: Target, color: '#b8960c' },
            { label: 'Check All Prices', icon: RefreshCw, color: '#16a34a' },
            { label: 'View Orders', icon: ShoppingCart, color: '#8b5cf6' },
          ].map((a, i) => (
            <button key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', border: '1px solid #e5e2dc', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 500 }}>
              <a.icon size={14} style={{ color: a.color }} /> {a.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function ScoutSection() {
  const [url, setUrl] = useState('');
  const [sources, setSources] = useState<any[]>([]);
  useEffect(() => { fetch(`${RA_API}/sources`).then(r => r.json()).then(d => setSources(d.sources || d || [])).catch(() => {}); }, []);

  return (
    <div>
      <SH title="Product Scout" subtitle="Find products to resell at a profit" />
      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16, marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Import Product from URL</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input value={url} onChange={e => setUrl(e.target.value)} placeholder="Paste Amazon, Walmart, or wholesale URL..."
            style={{ flex: 1, padding: '8px 12px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12 }} />
          <button style={{ padding: '8px 16px', background: '#06b6d4', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 600, fontSize: 12, cursor: 'pointer' }}>
            Import
          </button>
        </div>
      </div>
      {sources.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>No source products yet. Import a URL or use AI Deal Finder.</div>
      ) : (
        <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
          {sources.map((s: any) => (
            <div key={s.id} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 14 }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{s.title}</div>
              <div style={{ fontSize: 11, color: '#888' }}>{s.source_platform} — ${(s.source_price || 0).toFixed(2)}</div>
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <button style={{ fontSize: 10, padding: '4px 10px', background: '#06b6d4', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}>Relist</button>
                <button style={{ fontSize: 10, padding: '4px 10px', background: '#f5f3ef', color: '#666', border: 'none', borderRadius: 6, cursor: 'pointer' }}>Check Price</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ListingsSection() {
  const [listings, setListings] = useState<any[]>([]);
  const [filter, setFilter] = useState('all');
  useEffect(() => { fetch(`${RA_API}/listings`).then(r => r.json()).then(d => setListings(d.listings || d || [])).catch(() => {}); }, []);
  const filtered = filter === 'all' ? listings : listings.filter((l: any) => l.status === filter);
  return (
    <div>
      <SH title="My Listings" subtitle={`${listings.length} listings across all platforms`} />
      <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
        {['all', 'active', 'draft', 'sold', 'expired', 'out_of_stock'].map(s => (
          <button key={s} onClick={() => setFilter(s)} style={{
            fontSize: 10, padding: '4px 12px', borderRadius: 12, cursor: 'pointer',
            border: filter === s ? '2px solid #06b6d4' : '1px solid #e5e2dc',
            background: filter === s ? '#ecfeff' : '#fff', color: filter === s ? '#06b6d4' : '#666',
            fontWeight: filter === s ? 600 : 400,
          }}>
            {s === 'all' ? 'All' : s.replace('_', ' ')} ({s === 'all' ? listings.length : listings.filter((l: any) => l.status === s).length})
          </button>
        ))}
      </div>
      {filtered.length === 0 ? <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>No listings.</div> : (
        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
          <thead><tr style={{ borderBottom: '2px solid #e5e2dc', textAlign: 'left' }}>
            <th style={{ padding: 8 }}>Title</th><th style={{ padding: 8 }}>Platform</th><th style={{ padding: 8 }}>Your Price</th>
            <th style={{ padding: 8 }}>Source</th><th style={{ padding: 8 }}>Profit</th><th style={{ padding: 8 }}>Status</th>
          </tr></thead>
          <tbody>{filtered.map((l: any) => (
            <tr key={l.id} style={{ borderBottom: '1px solid #f0ede6' }}>
              <td style={{ padding: 8, fontWeight: 500, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{l.title}</td>
              <td style={{ padding: 8 }}><span style={{ color: PLATFORM_COLORS[l.platform] || '#666', fontWeight: 600 }}>{l.platform}</span></td>
              <td style={{ padding: 8, fontWeight: 600 }}>${(l.your_price || 0).toFixed(2)}</td>
              <td style={{ padding: 8, color: '#888' }}>${(l.source_price || 0).toFixed(2)}</td>
              <td style={{ padding: 8, fontWeight: 600, color: '#16a34a' }}>${(l.estimated_profit || 0).toFixed(2)}</td>
              <td style={{ padding: 8 }}><span style={{ fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 8, background: l.status === 'active' ? '#f0fdf4' : l.status === 'sold' ? '#dbeafe' : '#f5f3ef', color: l.status === 'active' ? '#16a34a' : l.status === 'sold' ? '#2563eb' : '#888' }}>{l.status}</span></td>
            </tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
}

function CrossListSection() {
  return <div><SH title="Cross-List" subtitle="Post to multiple platforms at once" /><div style={{ textAlign: 'center', padding: 40, color: '#999' }}>Select a source product, then choose platforms to list on.</div></div>;
}

function OrdersSection() {
  const [orders, setOrders] = useState<any[]>([]);
  useEffect(() => { fetch(`${RA_API}/orders`).then(r => r.json()).then(d => setOrders(d.orders || d || [])).catch(() => {}); }, []);
  const STAGES = ['Buyer Paid', 'Source Ordered', 'Shipped', 'Delivered', 'Completed'];
  const stageKeys = ['new', 'source_ordered', 'shipped', 'delivered', 'completed'];
  return (
    <div>
      <SH title="Order Tracker" subtitle="Manage the drop-ship fulfillment pipeline" />
      <div style={{ display: 'flex', gap: 10, overflowX: 'auto' }}>
        {STAGES.map((stage, i) => {
          const cards = orders.filter((o: any) => o.status === stageKeys[i]);
          return (
            <div key={i} style={{ minWidth: 180, background: '#f5f3ef', borderRadius: 10, padding: 10, flex: 1 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: '#06b6d4', marginBottom: 8 }}>{stage} ({cards.length})</div>
              {cards.length === 0 ? <div style={{ fontSize: 10, color: '#ccc', textAlign: 'center', padding: 12 }}>—</div> : cards.map((o: any) => (
                <div key={o.id} style={{ background: '#fff', borderRadius: 8, padding: 10, marginBottom: 6, border: '1px solid #e5e2dc', fontSize: 11 }}>
                  <div style={{ fontWeight: 600 }}>{o.buyer_name || 'Buyer'}</div>
                  <div style={{ color: '#888', fontSize: 10 }}>${(o.sale_price || 0).toFixed(2)} — profit ${(o.profit || 0).toFixed(2)}</div>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PriceMonitorSection() {
  return <div><SH title="Price Monitor" subtitle="Watch source prices for changes" /><div style={{ textAlign: 'center', padding: 40, color: '#999' }}>No products being monitored. Add source products first.</div></div>;
}

function CalculatorSection() {
  const [sourcePrice, setSourcePrice] = useState(20);
  const [sellPrice, setSellPrice] = useState(35);
  const [platformFee, setPlatformFee] = useState(13);
  const [shipping, setShipping] = useState(0);
  const feeAmt = sellPrice * (platformFee / 100);
  const profit = sellPrice - sourcePrice - feeAmt - shipping;
  const roi = sourcePrice > 0 ? (profit / sourcePrice) * 100 : 0;
  const margin = sellPrice > 0 ? (profit / sellPrice) * 100 : 0;

  return (
    <div>
      <SH title="Profit Calculator" subtitle="Calculate your markup, fees, and profit before listing" />
      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 20, maxWidth: 500 }}>
        {[
          { label: 'Source Price ($)', value: sourcePrice, set: setSourcePrice },
          { label: 'Your Selling Price ($)', value: sellPrice, set: setSellPrice },
          { label: 'Platform Fee (%)', value: platformFee, set: setPlatformFee },
          { label: 'Shipping Cost ($)', value: shipping, set: setShipping },
        ].map((f, i) => (
          <div key={i} style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>{f.label}</label>
            <input type="number" value={f.value} onChange={e => f.set(Number(e.target.value))}
              style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 13 }} />
          </div>
        ))}
        <div style={{ borderTop: '2px solid #e5e2dc', paddingTop: 12, marginTop: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}><span>Platform Fee</span><span>-${feeAmt.toFixed(2)}</span></div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 18, fontWeight: 700, color: profit >= 0 ? '#16a34a' : '#dc2626' }}><span>Profit</span><span>${profit.toFixed(2)}</span></div>
          <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 11, color: '#888' }}>
            <span>ROI: {roi.toFixed(0)}%</span>
            <span>Margin: {margin.toFixed(0)}%</span>
            <span>Markup: ${(sellPrice - sourcePrice).toFixed(2)}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function AnalyticsSection() {
  return <div><SH title="Analytics" subtitle="Profit trends, platform comparison, best sellers" /><div style={{ textAlign: 'center', padding: 40, color: '#999' }}>Analytics will populate as you make sales.</div></div>;
}
