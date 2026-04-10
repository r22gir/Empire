'use client';
import React, { useState, useEffect } from 'react';
import { API, relistFetch, getRelistToken, setRelistToken, obtainFounderToken } from '../../lib/api';
import { useTranslation } from '../../lib/i18n';
import {
  BarChart3, Search, Package, RefreshCw, ShoppingCart, DollarSign,
  TrendingUp, AlertTriangle, ExternalLink, Plus, Eye, Heart,
  ArrowRight, Clock, CheckCircle, Loader2, Link, Target, Tag,
  Calculator, Activity, Filter, ChevronRight, Globe, Star, Crown, Zap, Lock
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
  { id: 'plans', label: 'Plans', icon: Crown },
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
      case 'plans': return <PlansSection />;
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

function UsageBar({ used, limit, label }: { used: number; limit: number | string; label: string }) {
  const isUnlimited = limit === -1 || limit === 'unlimited';
  const pct = isUnlimited ? 0 : Math.min(100, (used / (limit as number)) * 100);
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
        <span style={{ color: '#666' }}>{label}</span>
        <span style={{ color: '#888' }}>{isUnlimited ? `${used} (unlimited)` : `${used} / ${limit}`}</span>
      </div>
      {!isUnlimited && (
        <div style={{ height: 6, background: '#f0ede6', borderRadius: 3, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${pct}%`, background: pct > 90 ? '#dc2626' : pct > 75 ? '#b8960c' : '#06b6d4', borderRadius: 3 }} />
        </div>
      )}
    </div>
  );
}

function PlansSection() {
  const [usage, setUsage] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState(false);
  const [tier, setTier] = useState('lite');
  const [userId, setUserId] = useState<string | null>(null);

  useEffect(() => {
    const token = getRelistToken();
    if (token) {
      relistFetch(`${RA_API}/whoami`)
        .then((data: any) => {
          if (data.user_id) setUserId(data.user_id);
        })
        .catch(() => {});
      return;
    }
    obtainFounderToken('7777')
      .then(data => {
        setRelistToken(data.access_token);
        setUserId(data.user.id);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!userId) return;
    relistFetch(`${RA_API}/subscription/me`)
      .then((sub: any) => {
        if (sub.tier) setTier(sub.tier);
      })
      .catch(() => {});
  }, [userId]);

  useEffect(() => {
    if (!tier) return;
    setLoading(true);
    relistFetch(`${RA_API}/usage`)
      .then((d: any) => { setUsage(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [tier]);

  const handleUpgrade = async () => {
    if (!usage?.upgrade_to) return;
    const uid = userId || getRelistToken();
    setUpgrading(true);
    try {
      const res = await fetch(`${API}/payments/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tier: usage.upgrade_to, user_id: uid }),
      });
      const data = await res.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch (e) {
      console.error('Upgrade failed', e);
    }
    setUpgrading(false);
  };

  const TIERS = [
    { id: 'lite', name: 'Lite', price: 29, color: '#6b7280', features: ['25 source products', '50 listings', '10 AI analyses/mo', 'Basic support'] },
    { id: 'pro', name: 'Pro', price: 79, color: '#3b82f6', features: ['200 source products', '500 listings', '100 AI analyses/mo', 'AI Deal Finder', 'Auto-relist', 'Priority support'], popular: true },
    { id: 'empire', name: 'Empire', price: 199, color: '#8b5cf6', features: ['Unlimited products', 'Unlimited listings', 'Unlimited AI analyses', 'AI Deal Finder', 'Auto-relist', 'Price alerts', 'VIP support'] },
  ];

  return (
    <div>
      <SH title="Plans & Usage" subtitle="Manage your RelistApp subscription" />
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}><Loader2 size={24} className="animate-spin" style={{ color: '#06b6d4' }} /></div>
      ) : (
        <>
          <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 20, marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <Crown size={18} style={{ color: '#b8960c' }} />
              <span style={{ fontSize: 14, fontWeight: 700 }}>Current Plan: {usage?.tier_name || tier}</span>
              <span style={{ fontSize: 11, color: '#888', marginLeft: 'auto' }}>${usage?.price_monthly || 0}/month</span>
            </div>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 16 }}>Your usage this billing cycle:</div>
            {usage && (
              <>
                <UsageBar used={usage.usage?.source_products?.used || 0} limit={usage.usage?.source_products?.limit || 0} label="Source Products" />
                <UsageBar used={usage.usage?.listings?.used || 0} limit={usage.usage?.listings?.limit || 0} label="Listings" />
                <UsageBar used={usage.usage?.orders?.used || 0} limit={usage.usage?.orders?.limit || 0} label="Orders" />
              </>
            )}
          </div>

          {usage?.upgrade_available && (
            <button
              onClick={handleUpgrade}
              disabled={upgrading}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '10px 20px',
                background: '#06b6d4', color: '#fff', border: 'none', borderRadius: 10,
                fontSize: 13, fontWeight: 600, cursor: upgrading ? 'wait' : 'pointer', marginBottom: 20,
              }}
            >
              {upgrading ? <Loader2 size={14} className="animate-spin" /> : <Zap size={14} />}
              Upgrade to {usage.upgrade_to === 'pro' ? 'Pro ($79/mo)' : 'Empire ($199/mo)'}
            </button>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
            {TIERS.map(t => (
              <div key={t.id} style={{
                background: '#fff', border: `2px solid ${t.id === tier ? t.color : '#e5e2dc'}`,
                borderRadius: 12, padding: 20, position: 'relative',
              }}>
                {t.popular && (
                  <div style={{ position: 'absolute', top: -10, left: '50%', transform: 'translateX(-50%)', background: t.color, color: '#fff', fontSize: 10, fontWeight: 700, padding: '2px 10px', borderRadius: 10 }}>
                    MOST POPULAR
                  </div>
                )}
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                  <Crown size={16} style={{ color: t.color }} />
                  <span style={{ fontSize: 16, fontWeight: 700 }}>{t.name}</span>
                </div>
                <div style={{ fontSize: 28, fontWeight: 700, color: t.color, marginBottom: 12 }}>${t.price}<span style={{ fontSize: 12, color: '#888', fontWeight: 400 }}>/mo</span></div>
                <div style={{ marginBottom: 12 }}>
                  {t.features.map((f, i) => (
                    <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: '#666', marginBottom: 4 }}>
                      <CheckCircle size={12} style={{ color: '#16a34a' }} /> {f}
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => setTier(t.id)}
                  style={{
                    width: '100%', padding: '8px', borderRadius: 8, fontSize: 12, fontWeight: 600,
                    cursor: 'pointer', border: t.id === tier ? 'none' : `1px solid ${t.color}`,
                    background: t.id === tier ? t.color : 'transparent', color: t.id === tier ? '#fff' : t.color,
                  }}
                >
                  {t.id === tier ? 'Current Plan' : 'Select Plan'}
                </button>
              </div>
            ))}
          </div>

          <div style={{ marginTop: 20, padding: 16, background: '#fef3cd', borderRadius: 10, fontSize: 12, color: '#856404' }}>
            <Lock size={14} style={{ display: 'inline', marginRight: 6 }} />
            Plans are billed monthly through Stripe. Cancel anytime from your account settings.
          </div>
        </>
      )}
    </div>
  );
}
