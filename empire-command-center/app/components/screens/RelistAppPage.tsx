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
  { id: 'deals', label: 'AI Deal Finder', icon: Target },
  { id: 'listings', label: 'My Listings', icon: Package },
  { id: 'crosslist', label: 'Cross-List', icon: Link },
  { id: 'orders', label: 'Orders', icon: ShoppingCart },
  { id: 'pricemon', label: 'Price Monitor', icon: TrendingUp },
  { id: 'services', label: 'Services', icon: Activity },
  { id: 'calculator', label: 'Profit Calculator', icon: Calculator },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
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
      case 'dashboard': return <DashboardSection onNav={(s) => setSection(s as Section)} />;
      case 'scout': return <ScoutSection />;
      case 'deals': return <DealsSection />;
      case 'listings': return <ListingsSection />;
      case 'crosslist': return <CrossListSection />;
      case 'orders': return <OrdersSection />;
      case 'pricemon': return <PriceMonitorSection />;
      case 'services': return <ServicesSection />;
      case 'calculator': return <CalculatorSection />;
      case 'analytics': return <AnalyticsSection />;
      case 'plans': return <PlansSection />;
      case 'docs': return <ProductDocs product="relist" />;
      default: return <DashboardSection onNav={(s) => setSection(s as Section)} />;
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

function DashboardSection({ onNav }: { onNav?: (s: string) => void }) {
  const [stats, setStats] = useState<any>({});
  useEffect(() => {
    fetch(`${RA_API}/analytics/dashboard`).then(r => r.json()).then(setStats).catch(() => {});
  }, []);
  const nav = (id: string) => { if (onNav) onNav(id); };
  return (
    <div>
      <SH title="RelistApp Dashboard" subtitle="Drop-ship arbitrage overview" />
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
        <Kpi label="Total Profit" value={`$${(stats.financials?.total_profit || 0).toFixed(2)}`} color="#16a34a" />
        <Kpi label="Active Listings" value={stats.listings?.active ?? '—'} color="#06b6d4" />
        <Kpi label="Pending Orders" value={stats.orders?.pending ?? '—'} color="#b8960c" />
        <Kpi label="Source Products" value={stats.source_products ?? '—'} color="#8b5f6" />
      </div>
      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16 }}>
        <h3 style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>Quick Actions</h3>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {[
            { label: 'Import Product URL', icon: Link, color: '#06b6d4', section: 'scout' },
            { label: 'AI Deal Finder', icon: Target, color: '#b8960c', section: 'deals' },
            { label: 'Check All Prices', icon: RefreshCw, color: '#16a34a', section: 'pricemon' },
            { label: 'View Orders', icon: ShoppingCart, color: '#8b5f6', section: 'orders' },
          ].map((a, i) => (
            <button key={i} onClick={() => nav(a.section)}
              style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', border: '1px solid #e5e2dc', borderRadius: 8, background: '#fff', cursor: 'pointer', fontSize: 12, fontWeight: 500 }}>
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
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState('');
  const [lastResult, setLastResult] = useState<any>(null);
  const [scoutRunning, setScoutRunning] = useState(false);
  const [scoutResult, setScoutResult] = useState<any>(null);
  const [selectedSources, setSelectedSources] = useState<string[]>(['amazon_bestsellers']);

  useEffect(() => { fetch(`${RA_API}/sources`).then(r => r.json()).then(d => setSources(d.items || [])).catch(() => {}); }, []);

  const doImport = async () => {
    if (!url.trim()) return;
    setImporting(true);
    setError('');
    try {
      const res = await fetch(`${RA_API}/sources/import-full`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Import failed');
      setLastResult(data);
      setSources(prev => [data, ...prev.filter(s => s.id !== data.id)]);
      setUrl('');
    } catch (e: any) {
      setError(e.message || 'Import failed');
    } finally {
      setImporting(false);
    }
  };

  const runScout = async () => {
    setScoutRunning(true);
    setScoutResult(null);
    try {
      const res = await fetch(`${RA_API}/scout/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sources: selectedSources, limit_per_source: 20 }),
      });
      const data = await res.json();
      setScoutResult(data);
      if (data.imported > 0) {
        fetch(`${RA_API}/sources`).then(r => r.json()).then(d => setSources(d.items || [])).catch(() => {});
      }
    } catch (e: any) {
      setScoutResult({ error: e.message });
    } finally {
      setScoutRunning(false);
    }
  };

  const toggleSource = (src: string) => {
    setSelectedSources(prev =>
      prev.includes(src) ? prev.filter(s => s !== src) : [...prev, src]
    );
  };

  return (
    <div>
      <SH title="Product Scout" subtitle="Import products to analyze and resell at a profit" />

      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16, marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Automated Scout</div>
        <div style={{ fontSize: 11, color: '#888', marginBottom: 10 }}>
          Run automated product discovery from free public sources.
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
          {[
            { key: 'amazon_bestsellers', label: 'Amazon Best Sellers', badge: 'Free/Public' },
            { key: 'walmart_trending', label: 'Walmart Trending', badge: 'Free/Public' },
          ].map(src => (
            <button key={src.key} onClick={() => toggleSource(src.key)} style={{
              padding: '6px 12px', borderRadius: 8, border: `1.5px solid ${selectedSources.includes(src.key) ? '#06b6d4' : '#e5e2dc'}`,
              background: selectedSources.includes(src.key) ? '#ecfeff' : '#fff',
              cursor: 'pointer', fontSize: 11, fontWeight: selectedSources.includes(src.key) ? 600 : 400,
            }}>
              {src.label}
              <span style={{ marginLeft: 6, fontSize: 9, padding: '1px 5px', borderRadius: 8, background: selectedSources.includes(src.key) ? '#dcfce7' : '#f5f3ef', color: selectedSources.includes(src.key) ? '#16a34a' : '#888' }}>
                {src.badge}
              </span>
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button onClick={runScout} disabled={scoutRunning || selectedSources.length === 0}
            style={{ padding: '8px 16px', background: scoutRunning ? '#9ca3af' : '#06b6d4', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 600, fontSize: 12, cursor: scoutRunning ? 'wait' : 'pointer' }}>
            {scoutRunning ? <><Loader2 size={12} className="animate-spin" /> Scanning...</> : 'Run Scout'}
          </button>
          {scoutResult && !scoutResult.error && (
            <span style={{ fontSize: 11, color: scoutResult.imported > 0 ? '#16a34a' : '#888' }}>
              Found {scoutResult.scouted} products, imported {scoutResult.imported} new, skipped {scoutResult.skipped_duplicates} duplicates
            </span>
          )}
          {scoutResult?.error && (
            <span style={{ fontSize: 11, color: '#dc2626' }}>{scoutResult.error}</span>
          )}
        </div>
      </div>

      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16, marginBottom: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8 }}>Import Product from URL</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input value={url} onChange={e => setUrl(e.target.value)} onKeyDown={e => e.key === 'Enter' && doImport()}
            placeholder="Paste Amazon, Walmart, AliExpress, or any product URL..."
            style={{ flex: 1, padding: '8px 12px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12 }} />
          <button onClick={doImport} disabled={importing}
            style={{ padding: '8px 16px', background: importing ? '#9ca3af' : '#06b6d4', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 600, fontSize: 12, cursor: importing ? 'wait' : 'pointer' }}>
            {importing ? 'Importing...' : 'Import'}
          </button>
        </div>
        {error && <div style={{ marginTop: 8, fontSize: 11, color: '#dc2626' }}>{error}</div>}
        {lastResult && (
          <div style={{ marginTop: 12, padding: 12, borderRadius: 8, background: '#f0fdf4', border: '1px solid #86efac' }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#16a34a', marginBottom: 4 }}>
              ✓ Imported: {lastResult.title?.slice(0, 60)}...
            </div>
            <div style={{ display: 'flex', gap: 16, fontSize: 11, color: '#666' }}>
              <span>Source: <b>${lastResult.price?.toFixed(2) || '?'}</b></span>
              <span>Market: <b>${(lastResult.deal?.market_price || 0).toFixed(2)}</b></span>
              <span>Est. Profit: <b style={{ color: '#16a34a' }}>${(lastResult.market_estimate?.estimated_profit || 0).toFixed(2)}</b></span>
              <span>Score: <b>{lastResult.deal?.score || 0}/100</b> <span style={{ color: lastResult.deal?.label === 'strong' ? '#16a34a' : lastResult.deal?.label === 'medium' ? '#ca8a04' : '#dc2626' }}>({lastResult.deal?.label})</span></span>
            </div>
            {lastResult.deal?.reason && <div style={{ fontSize: 11, color: '#888', marginTop: 4 }}>{lastResult.deal.reason}</div>}
          </div>
        )}
      </div>
      <div style={{ fontSize: 11, color: '#888', marginBottom: 12 }}>{sources.length} products imported</div>
      {sources.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999', background: '#fff', borderRadius: 10, border: '1px solid #e5e2dc' }}>
          No source products yet. Run automated scout or paste a URL above to import your first product.
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
          {sources.map((s: any) => {
            let deal = { score: 0, label: 'weak', reason: '' };
            try { if (s.notes) { const n = typeof s.notes === 'string' ? JSON.parse(s.notes) : s.notes; deal = n.deal_score || deal; } } catch {}
            return (
              <div key={s.id} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 14 }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{s.title?.slice(0, 60)}</div>
                <div style={{ fontSize: 11, color: '#888' }}>{s.source_platform} — ${(s.source_price || 0).toFixed(2)}</div>
                {s.market_estimate && (
                  <div style={{ fontSize: 11, marginTop: 4 }}>
                    <span style={{ color: '#16a34a' }}>Profit ${(s.market_estimate.estimated_profit || 0).toFixed(2)}</span>
                    <span style={{ marginLeft: 8, color: '#888' }}>ROI {(s.market_estimate.roi_percent || 0).toFixed(0)}%</span>
                  </div>
                )}
                <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                  <button style={{ fontSize: 10, padding: '4px 10px', background: '#06b6d4', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}
                    onClick={async () => {
                      await fetch(`${RA_API}/listings/from-source`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source_id: s.id, platform: 'ebay', your_price: s.market_estimate?.market_price || s.source_price * 2 || 29.99, platform_fee_percent: 13 }) });
                    }}>
                    Create Draft
                  </button>
                  <button style={{ fontSize: 10, padding: '4px 10px', background: '#f5f3ef', color: '#666', border: 'none', borderRadius: 6, cursor: 'pointer' }}
                    onClick={async () => { await fetch(`${RA_API}/sources/${s.id}/analyze`, { method: 'POST' }); }}>
                    Refresh
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function DealsSection() {
  const [deals, setDeals] = useState<any[]>([]);
  const [totals, setTotals] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [sortBy, setSortBy] = useState('score');
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [creating, setCreating] = useState(false);

  const loadDeals = () => {
    setLoading(true);
    fetch(`${RA_API}/deals?sort_by=${sortBy}&limit=100`)
      .then(r => r.json())
      .then(d => { setDeals(d.deals || []); setTotals({ strong: d.strong, medium: d.medium, weak: d.weak, total: d.total }); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffect(() => { loadDeals(); }, [sortBy]);

  const filtered = filter === 'all' ? deals : deals.filter((d: any) => d.deal_label === filter);

  const toggleSelect = (id: number) => {
    setSelected(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
  };

  const bulkCreateDrafts = async (platform = 'ebay') => {
    if (selected.size === 0) return;
    setCreating(true);
    for (const id of selected) {
      const d = deals.find((x: any) => x.id === id);
      if (!d) continue;
      const yourPrice = d.market_estimate?.market_price || d.source_price * 2;
      await fetch(`${RA_API}/listings/from-source`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_id: id, platform, your_price: yourPrice, platform_fee_percent: 13 }),
      });
    }
    setSelected(new Set());
    setCreating(false);
  };

  const labelColor = (label: string) => label === 'strong' ? '#16a34a' : label === 'medium' ? '#ca8a04' : '#dc2626';

  return (
    <div>
      <SH title="AI Deal Finder" subtitle="Scored arbitrage opportunities ranked by profit potential" />
      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <Kpi label="Strong Deals" value={totals.strong ?? '—'} color="#16a34a" />
        <Kpi label="Medium Deals" value={totals.medium ?? '—'} color="#ca8a04" />
        <Kpi label="Weak Deals" value={totals.weak ?? '—'} color="#dc2626" />
        <Kpi label="Total" value={totals.total ?? '—'} />
      </div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: 6 }}>
          {['all', 'strong', 'medium', 'weak'].map(f => (
            <button key={f} onClick={() => setFilter(f)} style={{
              fontSize: 10, padding: '4px 12px', borderRadius: 12, cursor: 'pointer',
              border: filter === f ? '2px solid #06b6d4' : '1px solid #e5e2dc',
              background: filter === f ? '#ecfeff' : '#fff', color: filter === f ? '#06b6d4' : '#666', fontWeight: filter === f ? 600 : 400,
            }}>
              {f.charAt(0).toUpperCase() + f.slice(1)} ({f === 'all' ? deals.length : deals.filter((d: any) => d.deal_label === f).length})
            </button>
          ))}
        </div>
        <select value={sortBy} onChange={e => setSortBy(e.target.value)} style={{ fontSize: 11, padding: '4px 8px', border: '1px solid #e5e2dc', borderRadius: 6 }}>
          <option value="score">Sort: Score</option>
          <option value="profit">Sort: Profit</option>
          <option value="roi">Sort: ROI</option>
          <option value="price">Sort: Price</option>
        </select>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          {selected.size > 0 && (
            <>
              <span style={{ fontSize: 11, color: '#666', alignSelf: 'center' }}>{selected.size} selected</span>
              <button onClick={() => bulkCreateDrafts('ebay')} disabled={creating} style={{ fontSize: 10, padding: '6px 12px', background: '#06b6d4', color: '#fff', border: 'none', borderRadius: 6, fontWeight: 600, cursor: creating ? 'wait' : 'pointer' }}>
                {creating ? 'Creating...' : `Create ${selected.size} Drafts`}
              </button>
              <button onClick={() => setSelected(new Set())} style={{ fontSize: 10, padding: '6px 10px', background: '#f5f3ef', color: '#666', border: 'none', borderRadius: 6, cursor: 'pointer' }}>Clear</button>
            </>
          )}
        </div>
      </div>
      {loading ? <div style={{ textAlign: 'center', padding: 40, color: '#999' }}><Loader2 size={20} className="animate-spin" style={{ color: '#06b6d4' }} /></div> :
       filtered.length === 0 ? <div style={{ textAlign: 'center', padding: 40, color: '#999', background: '#fff', borderRadius: 10, border: '1px solid #e5e2dc' }}>No deals found. Import source products first.</div> : (
        <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, overflow: 'hidden' }}>
          <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
            <thead><tr style={{ background: '#f5f3ef', borderBottom: '2px solid #e5e2dc' }}>
              <th style={{ padding: '8px 6px', width: 32 }}><input type="checkbox" checked={selected.size === filtered.length && filtered.length > 0} onChange={() => selected.size === filtered.length ? setSelected(new Set()) : setSelected(new Set(filtered.map((d: any) => d.id)))} /></th>
              <th style={{ padding: 8, textAlign: 'left' }}>Product</th>
              <th style={{ padding: 8 }}>Source</th>
              <th style={{ padding: 8 }}>Cost</th>
              <th style={{ padding: 8 }}>Market</th>
              <th style={{ padding: 8 }}>Profit</th>
              <th style={{ padding: 8 }}>ROI</th>
              <th style={{ padding: 8 }}>Score</th>
              <th style={{ padding: 8 }}>Actions</th>
            </tr></thead>
            <tbody>{filtered.map((d: any) => (
              <tr key={d.id} style={{ borderBottom: '1px solid #f0ede6', background: selected.has(d.id) ? '#f0fdf4' : 'transparent' }}>
                <td style={{ padding: '6px' }}><input type="checkbox" checked={selected.has(d.id)} onChange={() => toggleSelect(d.id)} /></td>
                <td style={{ padding: '6px 8px', maxWidth: 200 }}>
                  <div style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.title}</div>
                  {d.deal_reason && <div style={{ fontSize: 10, color: '#888', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.deal_reason}</div>}
                </td>
                <td style={{ padding: 8, color: '#666' }}>{d.source_platform}</td>
                <td style={{ padding: 8, fontWeight: 600 }}>${(d.source_price || 0).toFixed(2)}</td>
                <td style={{ padding: 8, color: '#16a34a' }}>${(d.market_estimate?.market_price || 0).toFixed(2)}</td>
                <td style={{ padding: 8, fontWeight: 600, color: '#16a34a' }}>${(d.estimated_profit || 0).toFixed(2)}</td>
                <td style={{ padding: 8, color: '#666' }}>{(d.roi_percent || 0).toFixed(0)}%</td>
                <td style={{ padding: 8 }}>
                  <span style={{ fontSize: 11, fontWeight: 700, color: labelColor(d.deal_label) }}>{d.deal_score}/100</span>
                  <span style={{ fontSize: 10, marginLeft: 4, color: labelColor(d.deal_label) }}>{d.deal_label}</span>
                </td>
                <td style={{ padding: 8 }}>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button style={{ fontSize: 10, padding: '3px 8px', background: '#06b6d4', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontWeight: 600 }}
                      onClick={async () => {
                        const yourPrice = d.market_estimate?.market_price || d.source_price * 2;
                        await fetch(`${RA_API}/listings/from-source`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source_id: d.id, platform: 'ebay', your_price: yourPrice, platform_fee_percent: 13 }) });
                      }}>Draft</button>
                    <button style={{ fontSize: 10, padding: '3px 8px', background: '#f5f3ef', color: '#666', border: 'none', borderRadius: 4, cursor: 'pointer' }}
                      onClick={async () => { await fetch(`${RA_API}/sources/${d.id}/analyze`, { method: 'POST' }); loadDeals(); }}>Refresh</button>
                  </div>
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ListingsSection() {
  const [listings, setListings] = useState<any[]>([]);
  const [filter, setFilter] = useState('all');
  useEffect(() => { fetch(`${RA_API}/listings`).then(r => r.json()).then(d => setListings(d.items || d.listings || [])).catch(() => {}); }, []);
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
  const [listings, setListings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<any>(null);
  const [targetPlatform, setTargetPlatform] = useState('ebay');
  const [yourPrice, setYourPrice] = useState<number>(0);
  const [platformFee, setPlatformFee] = useState(13);
  const [crossListing, setCrossListing] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const platforms = [
    { key: 'ebay', label: 'eBay', color: '#e53238' },
    { key: 'poshmark', label: 'Poshmark', color: '#7b2d8e' },
    { key: 'mercari', label: 'Mercari', color: '#4dc0ff' },
    { key: 'facebook_marketplace', label: 'Facebook Marketplace', color: '#1877f2' },
    { key: 'offerup', label: 'OfferUp', color: '#00ab80' },
    { key: 'etsy', label: 'Etsy', color: '#f56400' },
  ];

  useEffect(() => {
    fetch(`${RA_API}/listings?status=active&limit=100`)
      .then(r => r.json())
      .then(d => { setListings(d.items || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const handleSelect = (listing: any) => {
    setSelected(listing);
    setYourPrice(listing.your_price || 0);
    setResult(null);
    setError(null);
    const otherPlatforms = platforms.filter(p => p.key !== listing.platform);
    if (otherPlatforms.length > 0) setTargetPlatform(otherPlatforms[0].key);
  };

  const handleCrossList = async () => {
    if (!selected) return;
    setCrossListing(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${RA_API}/listings/${selected.id}/cross-list`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_platform: targetPlatform, your_price: yourPrice, platform_fee_percent: platformFee }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Cross-list failed');
      setResult(data);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setCrossListing(false);
    }
  };

  const availableTargets = platforms.filter(p => p.key !== selected?.platform);

  return (
    <div>
      <SH title="Cross-List" subtitle="Clone an existing listing to another platform" />
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}><Loader2 size={24} className="animate-spin" style={{ color: '#06b6d4' }} /></div>
      ) : listings.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999', background: '#fff', borderRadius: 10, border: '1px solid #e5e2dc' }}>
          No active listings to cross-list. Import and list products first.
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: '#666' }}>Select a listing to cross-list</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {listings.map((l: any) => (
                <div key={l.id} onClick={() => handleSelect(l)} style={{
                  padding: 12, borderRadius: 10, border: `2px solid ${selected?.id === l.id ? '#06b6d4' : '#e5e2dc'}`,
                  background: selected?.id === l.id ? '#ecfeff' : '#fff', cursor: 'pointer', transition: 'all 0.15s',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 6, background: (PLATFORM_COLORS[l.platform] || '#888') + '20', color: PLATFORM_COLORS[l.platform] || '#888' }}>
                      {l.platform}
                    </span>
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#111' }}>{l.title?.slice(0, 40)}{l.title?.length > 40 ? '...' : ''}</span>
                  </div>
                  <div style={{ fontSize: 11, color: '#888' }}>${(l.your_price || 0).toFixed(2)} — Est. profit ${(l.estimated_profit || 0).toFixed(2)}</div>
                </div>
              ))}
            </div>
          </div>

          <div>
            {selected ? (
              <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 20 }}>
                <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12 }}>Cross-list to another platform</div>
                <div style={{ fontSize: 11, color: '#666', marginBottom: 12 }}>
                  Listing: <b>{selected.title?.slice(0, 50)}</b> on <b>{selected.platform}</b> at <b>${(selected.your_price || 0).toFixed(2)}</b>
                </div>

                <div style={{ marginBottom: 12 }}>
                  <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Target Platform</label>
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {availableTargets.map(p => (
                      <button key={p.key} onClick={() => setTargetPlatform(p.key)} style={{
                        padding: '6px 12px', borderRadius: 8, border: `1.5px solid ${targetPlatform === p.key ? p.color : '#e5e2dc'}`,
                        background: targetPlatform === p.key ? p.color + '15' : '#fff', color: targetPlatform === p.key ? p.color : '#666',
                        fontSize: 11, fontWeight: targetPlatform === p.key ? 600 : 400, cursor: 'pointer',
                      }}>
                        {p.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
                  <div style={{ flex: 1 }}>
                    <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Your Price ($)</label>
                    <input type="number" value={yourPrice} onChange={e => setYourPrice(parseFloat(e.target.value) || 0)}
                      style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 13 }} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Platform Fee (%)</label>
                    <input type="number" value={platformFee} onChange={e => setPlatformFee(parseFloat(e.target.value) || 0)}
                      style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 13 }} />
                  </div>
                </div>

                <button onClick={handleCrossList} disabled={crossListing || availableTargets.length === 0}
                  style={{ width: '100%', padding: '10px 16px', background: crossListing ? '#9ca3af' : '#06b6d4', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 600, fontSize: 13, cursor: crossListing ? 'wait' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                  {crossListing ? <><Loader2 size={14} className="animate-spin" /> Cross-Listing...</> : <><ArrowRight size={14} /> Cross-List to {platforms.find(p => p.key === targetPlatform)?.label}</>}
                </button>

                {error && <div style={{ marginTop: 10, padding: '8px 12px', background: '#fee2e2', borderRadius: 8, fontSize: 12, color: '#dc2626' }}>{error}</div>}

                {result && (
                  <div style={{ marginTop: 12, padding: 14, background: '#f0fdf4', borderRadius: 10, border: '1px solid #86efac' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                      <CheckCircle size={16} style={{ color: '#16a34a' }} />
                      <span style={{ fontWeight: 700, color: '#16a34a' }}>Cross-list successful!</span>
                    </div>
                    <div style={{ fontSize: 12, color: '#666' }}>
                      <div>New listing on <b>{result.platform}</b></div>
                      <div>Price: <b>${(result.your_price || 0).toFixed(2)}</b> — Est. profit: <b style={{ color: '#16a34a' }}>${(result.estimated_profit || 0).toFixed(2)}</b></div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#999', background: '#fff', borderRadius: 10, border: '1px solid #e5e2dc' }}>
                Select a listing from the left to cross-list it to another platform.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function OrdersSection() {
  const [orders, setOrders] = useState<any[]>([]);
  useEffect(() => { fetch(`${RA_API}/orders`).then(r => r.json()).then(d => setOrders(d.items || d.orders || [])).catch(() => {}); }, []);
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
  const [sources, setSources] = useState<any[]>([]);
  const [checking, setChecking] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { fetch(`${RA_API}/sources`).then(r => r.json()).then(d => setSources(d.items || [])).catch(() => {}).finally(() => setLoading(false)); }, []);

  const checkAll = async () => {
    setChecking(true);
    setResults(null);
    try {
      const res = await fetch(`${RA_API}/sources/bulk-refresh`, { method: 'POST' });
      const data = await res.json();
      setResults(data);
      setSources(prev => prev.map((s: any) => { const r = data.results?.find((x: any) => x.id === s.id); return r ? { ...s, last_checked: new Date().toISOString() } : s; }));
    } catch {}
    setChecking(false);
  };

  const recColor = (r: string) => r === 'keep' ? '#16a34a' : r === 'reprice' ? '#ca8a04' : r === 'review' ? '#dc2626' : '#888';

  return (
    <div>
      <SH title="Price Monitor" subtitle="Watch source prices for changes" action={
        <button onClick={checkAll} disabled={checking || sources.length === 0} style={{ padding: '8px 16px', background: checking ? '#9ca3af' : '#16a34a', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 600, fontSize: 12, cursor: checking ? 'wait' : 'pointer' }}>
          {checking ? 'Checking...' : 'Check All Prices'}
        </button>
      } />
      {results && (
        <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
          {[['keep', 'Keep'], ['reprice', 'Reprice'], ['review', 'Review'], ['delist', 'Delist']].map(([r, label]) => (
            <div key={r} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 8, padding: '10px 14px', flex: 1, textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: recColor(r as string) }}>{results.summary?.[r] ?? 0}</div>
              <div style={{ fontSize: 10, color: '#888' }}>{label}</div>
            </div>
          ))}
        </div>
      )}
      {loading ? <div style={{ textAlign: 'center', padding: 40, color: '#999' }}><Loader2 size={20} className="animate-spin" style={{ color: '#06b6d4' }} /></div> :
       sources.length === 0 ? <div style={{ textAlign: 'center', padding: 40, color: '#999', background: '#fff', borderRadius: 10, border: '1px solid #e5e2dc' }}>No source products yet. Import products from the Product Scout first.</div> : (
        <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, overflow: 'hidden' }}>
          <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
            <thead><tr style={{ background: '#f5f3ef', borderBottom: '2px solid #e5e2dc' }}>
              <th style={{ padding: 8, textAlign: 'left' }}>Product</th>
              <th style={{ padding: 8 }}>Prev Price</th>
              <th style={{ padding: 8 }}>Current</th>
              <th style={{ padding: 8 }}>Change</th>
              <th style={{ padding: 8 }}>Est. Profit</th>
              <th style={{ padding: 8 }}>Recommendation</th>
            </tr></thead>
            <tbody>{sources.map((s: any) => {
              const r = results?.results?.find((x: any) => x.id === s.id);
              return (
                <tr key={s.id} style={{ borderBottom: '1px solid #f0ede6' }}>
                  <td style={{ padding: 8, fontWeight: 500, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.title}</td>
                  <td style={{ padding: 8, color: '#888' }}>{r ? `$${(r.prev_price || 0).toFixed(2)}` : '—'}</td>
                  <td style={{ padding: 8, fontWeight: 600 }}>${(s.source_price || 0).toFixed(2)}</td>
                  <td style={{ padding: 8, fontWeight: 600, color: r?.price_change > 0 ? '#16a34a' : r?.price_change < 0 ? '#dc2626' : '#888' }}>
                    {r ? (r.price_change > 0 ? '+' : '') + `$${r.price_change.toFixed(2)}` : '—'}
                  </td>
                  <td style={{ padding: 8, color: '#16a34a', fontWeight: 600 }}>${(r?.estimated_profit || s.market_estimate?.estimated_profit || 0).toFixed(2)}</td>
                  <td style={{ padding: 8 }}>
                    {r ? <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 8, background: recColor(r.recommendation) + '20', color: recColor(r.recommendation) }}>{r.recommendation.toUpperCase()}</span> : '—'}
                  </td>
                </tr>
              );
            })}</tbody>
          </table>
        </div>
      )}
    </div>
  );
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
  const [dash, setDash] = useState<any>(null);
  const [platforms, setPlatforms] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${RA_API}/analytics/dashboard`).then(r => r.json()),
      fetch(`${RA_API}/analytics/by-platform`).then(r => r.json()),
    ]).then(([d, p]) => {
      setDash(d);
      setPlatforms(p.platforms || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div><SH title="Analytics" subtitle="Profit trends, platform comparison, best sellers" /><div style={{ textAlign: 'center', padding: 40 }}><Loader2 size={24} className="animate-spin" style={{ color: '#06b6d4' }} /></div></div>;

  const hasData = dash && (dash.orders.total > 0 || dash.listings.total > 0);

  return (
    <div>
      <SH title="Analytics" subtitle="Profit trends, platform comparison, best sellers" />
      {!hasData ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999', background: '#fff', borderRadius: 10, border: '1px solid #e5e2dc' }}>
          Analytics will populate as you make sales. Import products and create listings to see your metrics here.
        </div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 16 }}>
            {[
              { label: 'Total Revenue', value: `$${(dash.financials.total_revenue || 0).toFixed(2)}`, color: '#06b6d4' },
              { label: 'Total Profit', value: `$${(dash.financials.total_profit || 0).toFixed(2)}`, color: '#16a34a' },
              { label: 'Items Sold', value: dash.listings.sold || 0, color: '#8b5cf6' },
              { label: 'Active Listings', value: dash.listings.active || 0, color: '#e53238' },
            ].map((k, i) => (
              <div key={i} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16, textAlign: 'center' }}>
                <div style={{ fontSize: 22, fontWeight: 700, color: k.color }}>{k.value}</div>
                <div style={{ fontSize: 11, color: '#888', marginTop: 4 }}>{k.label}</div>
              </div>
            ))}
          </div>

          {platforms.length > 0 && (
            <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12 }}>Performance by Platform</div>
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                <thead><tr style={{ borderBottom: '2px solid #e5e2dc' }}>
                  <th style={{ padding: 8, textAlign: 'left' }}>Platform</th>
                  <th style={{ padding: 8 }}>Listings</th>
                  <th style={{ padding: 8 }}>Sold</th>
                  <th style={{ padding: 8 }}>Revenue</th>
                  <th style={{ padding: 8 }}>Profit</th>
                  <th style={{ padding: 8 }}>Avg Markup</th>
                </tr></thead>
                <tbody>
                  {platforms.map((p: any) => (
                    <tr key={p.platform} style={{ borderBottom: '1px solid #f0ede6' }}>
                      <td style={{ padding: 8 }}>
                        <span style={{ fontWeight: 600, color: PLATFORM_COLORS[p.platform] || '#666' }}>{p.platform}</span>
                      </td>
                      <td style={{ padding: 8 }}>{p.total_listings || 0}</td>
                      <td style={{ padding: 8 }}>{p.sold || 0}</td>
                      <td style={{ padding: 8, fontWeight: 600 }}>${(p.revenue || 0).toFixed(2)}</td>
                      <td style={{ padding: 8, fontWeight: 600, color: '#16a34a' }}>${(p.profit || 0).toFixed(2)}</td>
                      <td style={{ padding: 8 }}>{((p.avg_markup || 0) * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}

const HEALTH_COLORS: Record<string, string> = {
  healthy: '#16a34a',
  stub: '#ca8a04',
  not_implemented: '#9ca3af',
  no_auth: '#dc2626',
  not_configured: '#dc2626',
  error: '#dc2626',
  unknown: '#9ca3af',
};

const TYPE_LABELS: Record<string, string> = {
  free_public: 'Free/Public',
  official_api: 'Official API',
  premium_optional: 'Premium Optional',
};

const MODE_LABELS: Record<string, string> = {
  off: 'Off',
  manual: 'Manual',
  assist: 'Assist',
  auto: 'Auto',
};

function ServicesSection() {
  const [services, setServices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState<string | null>(null);
  const [filter, setFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');

  const loadServices = () => {
    setLoading(true);
    fetch(`${RA_API}/services`)
      .then(r => r.json())
      .then(d => { setServices(d.services || []); setLoading(false); })
      .catch(() => setLoading(false));
  };

  useEffect(() => { loadServices(); }, []);

  const updateService = async (key: string, updates: any) => {
    setUpdating(key);
    try {
      await fetch(`${RA_API}/services/${key}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      });
      loadServices();
    } finally {
      setUpdating(null);
    }
  };

  const pauseService = async (key: string) => {
    setUpdating(key);
    try {
      const reason = prompt('Pause reason (optional):') || '';
      await fetch(`${RA_API}/services/${key}/pause?reason=${encodeURIComponent(reason)}`, { method: 'POST' });
      loadServices();
    } finally {
      setUpdating(null);
    }
  };

  const resumeService = async (key: string) => {
    setUpdating(key);
    try {
      await fetch(`${RA_API}/services/${key}/resume`, { method: 'POST' });
      loadServices();
    } finally {
      setUpdating(null);
    }
  };

  const filtered = services.filter((s: any) => {
    const matchesEnabled = filter === 'all' || (filter === 'enabled' && s.enabled) || (filter === 'disabled' && !s.enabled);
    const matchesType = typeFilter === 'all' || s.service_type === typeFilter;
    return matchesEnabled && matchesType;
  });

  const grouped = filtered.reduce((acc: Record<string, any[]>, s: any) => {
    if (!acc[s.service_type]) acc[s.service_type] = [];
    acc[s.service_type].push(s);
    return acc;
  }, {});

  return (
    <div>
      <SH title="Service Control Panel" subtitle="Enable, pause, and configure RelistApp services" />
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: 6 }}>
          {['all', 'enabled', 'disabled'].map(f => (
            <button key={f} onClick={() => setFilter(f)} style={{
              fontSize: 11, padding: '4px 12px', borderRadius: 12, cursor: 'pointer',
              border: filter === f ? '2px solid #06b6d4' : '1px solid #e5e2dc',
              background: filter === f ? '#ecfeff' : '#fff', color: filter === f ? '#06b6d4' : '#666',
              fontWeight: filter === f ? 600 : 400,
            }}>
              {f === 'all' ? 'All' : f === 'enabled' ? 'Enabled' : 'Paused'}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          {['all', 'free_public', 'official_api', 'premium_optional'].map(f => (
            <button key={f} onClick={() => setTypeFilter(f)} style={{
              fontSize: 10, padding: '3px 10px', borderRadius: 10, cursor: 'pointer',
              border: typeFilter === f ? '2px solid #06b6d4' : '1px solid #e5e2dc',
              background: typeFilter === f ? '#ecfeff' : '#fff', color: typeFilter === f ? '#06b6d4' : '#888',
              fontWeight: typeFilter === f ? 600 : 400,
            }}>
              {f === 'all' ? 'All Types' : TYPE_LABELS[f] || f}
            </button>
          ))}
        </div>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: '#888' }}>
          {services.filter((s: any) => s.enabled).length} enabled / {services.length} total
        </span>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}><Loader2 size={20} className="animate-spin" style={{ color: '#06b6d4' }} /></div>
      ) : (
        Object.entries(grouped).map(([type, svcs]) => (
          <div key={type} style={{ marginBottom: 24 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#888', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{
                padding: '1px 6px', borderRadius: 4, fontSize: 9, fontWeight: 700,
                background: type === 'free_public' ? '#dcfce7' : type === 'official_api' ? '#dbeafe' : '#f3e8ff',
                color: type === 'free_public' ? '#16a34a' : type === 'official_api' ? '#2563eb' : '#7c3aed',
              }}>
                {TYPE_LABELS[type] || type}
              </span>
              <span style={{ color: '#aaa' }}>{type === 'free_public' ? 'On by default — free to use' : type === 'official_api' ? 'Off until credentials provided' : 'Off — premium subscription required'}</span>
            </div>
            <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))' }}>
              {(svcs as any[]).map((svc: any) => {
                const healthColor = HEALTH_COLORS[svc.health] || HEALTH_COLORS.unknown;
                const isUpdating = updating === svc.service_key;
                return (
                  <div key={svc.service_key} style={{
                    background: '#fff', border: `1px solid ${svc.enabled ? '#e5e2dc' : '#fee2e2'}`,
                    borderRadius: 10, padding: 14,
                    opacity: svc.enabled ? 1 : 0.7,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, fontSize: 13 }}>{svc.display_name}</div>
                        <div style={{ fontSize: 11, color: '#888', marginTop: 2 }}>{svc.description}</div>
                      </div>
                      <div style={{ display: 'flex', gap: 4, flexShrink: 0, marginLeft: 8 }}>
                        {!svc.enabled ? (
                          <button onClick={() => resumeService(svc.service_key)} disabled={isUpdating}
                            style={{ fontSize: 10, padding: '4px 8px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 6, cursor: isUpdating ? 'wait' : 'pointer', fontWeight: 600 }}>
                            Resume
                          </button>
                        ) : (
                          <button onClick={() => pauseService(svc.service_key)} disabled={isUpdating}
                            style={{ fontSize: 10, padding: '4px 8px', background: '#f5f3ef', color: '#666', border: 'none', borderRadius: 6, cursor: isUpdating ? 'wait' : 'pointer' }}>
                            Pause
                          </button>
                        )}
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
                      <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: svc.enabled ? '#dcfce7' : '#fee2e2', color: svc.enabled ? '#16a34a' : '#dc2626', fontWeight: 600 }}>
                        {svc.enabled ? 'Enabled' : 'Paused'}
                      </span>
                      <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: '#f5f3ef', color: '#666' }}>
                        {MODE_LABELS[svc.mode] || svc.mode}
                      </span>
                      <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: svc.auth_required && !svc.auth_present ? '#fee2e2' : '#f5f3ef', color: svc.auth_required && !svc.auth_present ? '#dc2626' : '#888' }}>
                        {svc.auth_required ? (svc.auth_present ? 'Auth OK' : 'Auth Missing') : 'No Auth'}
                      </span>
                      <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 10, background: healthColor + '20', color: healthColor, fontWeight: 600 }}>
                        {svc.health.replace('_', ' ')}
                      </span>
                    </div>

                    {svc.last_error && (
                      <div style={{ fontSize: 10, color: '#dc2626', marginBottom: 6, padding: '4px 8px', background: '#fee2e2', borderRadius: 6 }}>
                        Error: {svc.last_error.slice(0, 80)}
                      </div>
                    )}

                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                      <select value={svc.mode} onChange={e => updateService(svc.service_key, { mode: e.target.value })}
                        style={{ fontSize: 11, padding: '3px 6px', border: '1px solid #e5e2dc', borderRadius: 6, background: '#fff', cursor: 'pointer' }}>
                        <option value="off">Off</option>
                        <option value="manual">Manual</option>
                        <option value="assist">Assist</option>
                        <option value="auto">Auto</option>
                      </select>
                      <span style={{ fontSize: 10, color: '#888' }}>Weight</span>
                      <input type="range" min="0" max="200" value={svc.weight}
                        onChange={e => updateService(svc.service_key, { weight: parseInt(e.target.value) })}
                        style={{ flex: 1, cursor: 'pointer' }} />
                      <span style={{ fontSize: 10, fontWeight: 600, color: '#666', minWidth: 28 }}>{svc.weight}%</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))
      )}
    </div>
  );
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
