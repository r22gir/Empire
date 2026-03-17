'use client';
import React, { useState, useEffect, useCallback } from 'react';
import {
  LayoutDashboard, List, ShoppingCart, Copy, BarChart3,
  Search, Filter, Plus, ExternalLink, RefreshCw, TrendingUp,
  Package, DollarSign, Clock, CheckCircle, Truck, AlertTriangle,
  ChevronDown, Eye, Edit2, Trash2, ArrowUpRight, Store, BookOpen, CreditCard, Camera,
  Loader2,
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';
import SmartListerPanel from './SmartListerPanel';

// ============ NAV ============

const NAV_SECTIONS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'smartlister', label: 'Smart Lister', icon: Camera },
  { id: 'listings', label: 'Listings', icon: List },
  { id: 'orders', label: 'Orders', icon: ShoppingCart },
  { id: 'crosslist', label: 'Cross-List', icon: Copy },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'payments', label: 'Payments', icon: CreditCard },
  { id: 'docs', label: 'Docs', icon: BookOpen },
] as const;

type Section = typeof NAV_SECTIONS[number]['id'];

// ============ TYPES ============

interface Listing {
  id: string;
  title: string;
  sku: string;
  price: number;
  qty: number;
  marketplace: string;
  status: 'active' | 'sold' | 'draft';
  image: string;
  category: string;
}

interface Order {
  id: string;
  marketplace: string;
  buyer: string;
  items: string;
  total: number;
  status: 'pending' | 'shipped' | 'delivered';
  date: string;
}

// ============ API ============

const _API_BASE = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
  ? 'https://api.empirebox.store'
  : 'http://localhost:8000';
const API = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
  ? 'https://api.empirebox.store/api/v1'
  : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1');
const LISTINGS_URL = `${_API_BASE}/listings/listings`;
const ORDERS_URL = `${_API_BASE}/preorders/`;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapListingFromAPI(raw: any): Listing {
  return {
    id: String(raw.id ?? ''),
    title: raw.title ?? raw.name ?? '',
    sku: raw.sku ?? '',
    price: Number(raw.price ?? 0),
    qty: Number(raw.qty ?? raw.quantity ?? raw.stock ?? 0),
    marketplace: raw.marketplace ?? raw.platform ?? '',
    status: (['active', 'sold', 'draft'].includes(raw.status) ? raw.status : 'draft') as Listing['status'],
    image: raw.image ?? raw.image_url ?? raw.thumbnail ?? '',
    category: raw.category ?? '',
  };
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapOrderFromAPI(raw: any): Order {
  return {
    id: String(raw.id ?? ''),
    marketplace: raw.marketplace ?? raw.platform ?? '',
    buyer: raw.buyer ?? raw.buyer_name ?? raw.customer_name ?? raw.customer ?? '',
    items: raw.items ?? raw.item ?? raw.product ?? raw.description ?? '',
    total: Number(raw.total ?? raw.amount ?? raw.price ?? 0),
    status: (['pending', 'shipped', 'delivered'].includes(raw.status) ? raw.status : 'pending') as Order['status'],
    date: raw.date ?? raw.created_at ?? raw.order_date ?? '',
  };
}

// ============ DATA HOOKS ============

function useListings() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchListings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(LISTINGS_URL);
      if (!res.ok) throw new Error(`Failed to fetch listings: ${res.status}`);
      const data = await res.json();
      const items = Array.isArray(data) ? data : (data.listings ?? data.items ?? data.results ?? []);
      setListings(items.map(mapListingFromAPI));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch listings');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchListings(); }, [fetchListings]);

  return { listings, loading, error, refetch: fetchListings };
}

function useOrders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(ORDERS_URL);
      if (!res.ok) throw new Error(`Failed to fetch orders: ${res.status}`);
      const data = await res.json();
      const items = Array.isArray(data) ? data : (data.orders ?? data.items ?? data.results ?? []);
      setOrders(items.map(mapOrderFromAPI));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch orders');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchOrders(); }, [fetchOrders]);

  return { orders, loading, error, refetch: fetchOrders };
}

// ============ THEME ============

const BLUE = '#2563eb';
const BLUE_BG = '#dbeafe';
const BLUE_BORDER = '#93c5fd';

const MARKETPLACE_COLORS: Record<string, string> = {
  eBay: '#e53238',
  Poshmark: '#7f0353',
  Mercari: '#4dc4e0',
  Amazon: '#ff9900',
  Etsy: '#f1641e',
};

const MARKETPLACE_LIST = ['eBay', 'Poshmark', 'Mercari', 'Amazon', 'Etsy'];

// ============ SHARED UI ============

function LoadingSpinner({ message }: { message?: string }) {
  return (
    <div style={{ padding: 60, textAlign: 'center' }}>
      <Loader2 size={28} style={{ color: BLUE, animation: 'spin 1s linear infinite', margin: '0 auto 12px' }} />
      <div style={{ fontSize: 13, color: '#999' }}>{message || 'Loading...'}</div>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div style={{ padding: '16px 20px', margin: '0 0 16px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 10 }}>
      <div className="flex items-center gap-2">
        <AlertTriangle size={16} style={{ color: '#ef4444' }} />
        <span style={{ fontSize: 13, fontWeight: 600, color: '#ef4444' }}>{message}</span>
        {onRetry && (
          <button onClick={onRetry} style={{ marginLeft: 'auto', padding: '4px 12px', borderRadius: 6, background: '#fff', border: '1px solid #fecaca', fontSize: 12, fontWeight: 600, color: '#ef4444', cursor: 'pointer' }}>
            Retry
          </button>
        )}
      </div>
    </div>
  );
}

function EmptyState({ icon, title, subtitle }: { icon: React.ReactNode; title: string; subtitle: string }) {
  return (
    <div style={{ padding: 60, textAlign: 'center' }}>
      <div style={{ color: '#ccc', marginBottom: 12 }}>{icon}</div>
      <div style={{ fontSize: 15, fontWeight: 600, color: '#666', marginBottom: 4 }}>{title}</div>
      <div style={{ fontSize: 13, color: '#999' }}>{subtitle}</div>
    </div>
  );
}

// ============ HELPERS ============

function MarketplaceBadge({ name }: { name: string }) {
  const color = MARKETPLACE_COLORS[name] || '#666';
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, fontWeight: 600, color, background: color + '15', padding: '2px 8px', borderRadius: 6, border: `1px solid ${color}30` }}>
      <Store size={11} />{name}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { bg: string; color: string; icon: React.ReactNode }> = {
    active: { bg: '#dcfce7', color: '#16a34a', icon: <CheckCircle size={11} /> },
    sold: { bg: '#dbeafe', color: '#2563eb', icon: <DollarSign size={11} /> },
    draft: { bg: '#f3f4f6', color: '#6b7280', icon: <Edit2 size={11} /> },
    pending: { bg: '#fef3c7', color: '#d97706', icon: <Clock size={11} /> },
    shipped: { bg: '#dbeafe', color: '#2563eb', icon: <Truck size={11} /> },
    delivered: { bg: '#dcfce7', color: '#16a34a', icon: <CheckCircle size={11} /> },
  };
  const s = map[status] || map.draft;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, fontWeight: 600, color: s.color, background: s.bg, padding: '2px 8px', borderRadius: 6 }}>
      {s.icon}{status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}

// ============ KPI CARD ============

function KPI({ icon, iconBg, iconColor, label, value, sub }: {
  icon: React.ReactNode; iconBg: string; iconColor: string; label: string; value: string; sub: string;
}) {
  return (
    <div className="empire-card" style={{ padding: '16px 18px' }}>
      <div className="flex items-center gap-3 mb-2">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: iconBg, color: iconColor }}>{icon}</div>
        <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: '#999' }}>{label}</span>
      </div>
      <div style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a' }}>{value}</div>
      <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>{sub}</div>
    </div>
  );
}

// ============ 1. DASHBOARD ============

function DashboardSection({ onNavigate }: { onNavigate: (s: Section) => void }) {
  const { listings, loading: listingsLoading, error: listingsError, refetch: refetchListings } = useListings();
  const { orders, loading: ordersLoading, error: ordersError, refetch: refetchOrders } = useOrders();

  const loading = listingsLoading || ordersLoading;

  const activeCount = listings.filter(l => l.status === 'active').length;
  const soldCount = listings.filter(l => l.status === 'sold').length;
  const totalRevenue = orders.reduce((sum, o) => sum + o.total, 0);
  const pendingOrders = orders.filter(o => o.status === 'pending').length;

  const marketplaceCounts = MARKETPLACE_LIST.map(mp => ({
    name: mp,
    active: listings.filter(l => l.marketplace === mp && l.status === 'active').length,
    orders: orders.filter(o => o.marketplace === mp).length,
    revenue: orders.filter(o => o.marketplace === mp).reduce((s, o) => s + o.total, 0),
    synced: true,
  }));

  return (
    <div style={{ padding: 24, maxWidth: 1100 }}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a' }}>MarketForge Dashboard</h1>
          <p style={{ fontSize: 13, color: '#999', marginTop: 2 }}>Multi-marketplace listing management</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => onNavigate('crosslist')} className="flex items-center gap-2" style={{ padding: '8px 16px', borderRadius: 10, background: BLUE, color: '#fff', fontSize: 13, fontWeight: 600, border: 'none', cursor: 'pointer' }}>
            <Plus size={15} />Cross-List
          </button>
          <button onClick={() => { refetchListings(); refetchOrders(); }} className="flex items-center gap-2" style={{ padding: '8px 16px', borderRadius: 10, background: '#fff', color: '#666', fontSize: 13, fontWeight: 600, border: '1px solid #e5e7eb', cursor: 'pointer' }}>
            <RefreshCw size={15} />Sync All
          </button>
        </div>
      </div>

      {listingsError && <ErrorBanner message={listingsError} onRetry={refetchListings} />}
      {ordersError && <ErrorBanner message={ordersError} onRetry={refetchOrders} />}

      {loading ? (
        <LoadingSpinner message="Loading dashboard data..." />
      ) : (
        <>
          {/* KPI Row */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <KPI icon={<List size={16} />} iconBg={BLUE_BG} iconColor={BLUE} label="Active Listings" value={String(activeCount)} sub={`${soldCount} sold this month`} />
            <KPI icon={<DollarSign size={16} />} iconBg="#dcfce7" iconColor="#16a34a" label="Total Revenue" value={`$${totalRevenue.toLocaleString('en-US', { minimumFractionDigits: 2 })}`} sub="Last 30 days" />
            <KPI icon={<ShoppingCart size={16} />} iconBg="#fef3c7" iconColor="#d97706" label="Pending Orders" value={String(pendingOrders)} sub="Awaiting shipment" />
            <KPI icon={<Store size={16} />} iconBg="#f3e8ff" iconColor="#9333ea" label="Marketplaces" value={String(MARKETPLACE_LIST.length)} sub="All connected" />
          </div>

          {/* Marketplace Sync Cards */}
          <h2 style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', marginBottom: 12 }}>Marketplace Status</h2>
          <div className="grid grid-cols-5 gap-3 mb-6">
            {marketplaceCounts.map(mp => (
              <div key={mp.name} className="empire-card" style={{ padding: '14px 16px', borderLeft: `3px solid ${MARKETPLACE_COLORS[mp.name]}` }}>
                <div className="flex items-center justify-between mb-2">
                  <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{mp.name}</span>
                  <span style={{ fontSize: 10, fontWeight: 600, color: mp.synced ? '#16a34a' : '#ef4444', background: mp.synced ? '#dcfce7' : '#fee2e2', padding: '1px 6px', borderRadius: 4 }}>
                    {mp.synced ? 'Synced' : 'Error'}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: '#666' }}>{mp.active} active &middot; {mp.orders} orders</div>
                <div style={{ fontSize: 13, fontWeight: 700, color: MARKETPLACE_COLORS[mp.name], marginTop: 4 }}>${mp.revenue.toFixed(2)}</div>
              </div>
            ))}
          </div>

          {/* Quick Actions */}
          <h2 style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', marginBottom: 12 }}>Quick Actions</h2>
          <div className="grid grid-cols-3 gap-3">
            <div onClick={() => onNavigate('listings')} className="empire-card" style={{ cursor: 'pointer', padding: '14px 16px' }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = BLUE)}
              onMouseLeave={e => (e.currentTarget.style.borderColor = '#ece8e0')}>
              <div className="flex items-center gap-2 mb-1" style={{ color: BLUE }}><List size={16} /><span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>Manage Listings</span></div>
              <div style={{ fontSize: 11, color: '#999' }}>View, edit, and manage all product listings</div>
            </div>
            <div onClick={() => onNavigate('orders')} className="empire-card" style={{ cursor: 'pointer', padding: '14px 16px' }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = '#d97706')}
              onMouseLeave={e => (e.currentTarget.style.borderColor = '#ece8e0')}>
              <div className="flex items-center gap-2 mb-1" style={{ color: '#d97706' }}><ShoppingCart size={16} /><span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>Process Orders</span></div>
              <div style={{ fontSize: 11, color: '#999' }}>Fulfill pending orders and track shipments</div>
            </div>
            <div onClick={() => onNavigate('analytics')} className="empire-card" style={{ cursor: 'pointer', padding: '14px 16px' }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = '#16a34a')}
              onMouseLeave={e => (e.currentTarget.style.borderColor = '#ece8e0')}>
              <div className="flex items-center gap-2 mb-1" style={{ color: '#16a34a' }}><BarChart3 size={16} /><span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>View Analytics</span></div>
              <div style={{ fontSize: 11, color: '#999' }}>Sales breakdown by marketplace and product</div>
            </div>
          </div>

          {/* Recent Orders */}
          <h2 style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', marginTop: 24, marginBottom: 12 }}>Recent Orders</h2>
          {orders.length === 0 ? (
            <EmptyState icon={<ShoppingCart size={32} />} title="No orders yet" subtitle="Orders will appear here once customers start buying" />
          ) : (
            <div className="empire-card" style={{ padding: 0, overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: '#f9f8f6', borderBottom: '1px solid #ece8e0' }}>
                    <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: '#666' }}>Order</th>
                    <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: '#666' }}>Marketplace</th>
                    <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: '#666' }}>Buyer</th>
                    <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: '#666' }}>Total</th>
                    <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: '#666' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.slice(0, 5).map(o => (
                    <tr key={o.id} style={{ borderBottom: '1px solid #f3f1ed' }}>
                      <td style={{ padding: '10px 14px', fontWeight: 600, color: BLUE }}>{o.id}</td>
                      <td style={{ padding: '10px 14px' }}><MarketplaceBadge name={o.marketplace} /></td>
                      <td style={{ padding: '10px 14px', color: '#1a1a1a' }}>{o.buyer}</td>
                      <td style={{ padding: '10px 14px', fontWeight: 600 }}>${o.total.toFixed(2)}</td>
                      <td style={{ padding: '10px 14px' }}><StatusBadge status={o.status} /></td>
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

// ============ 2. LISTINGS ============

function ListingsSection() {
  const { listings, loading, error, refetch } = useListings();
  const [search, setSearch] = useState('');
  const [filterMarketplace, setFilterMarketplace] = useState('All');
  const [filterStatus, setFilterStatus] = useState('All');

  const filtered = listings.filter(l => {
    if (search && !l.title.toLowerCase().includes(search.toLowerCase()) && !l.sku.toLowerCase().includes(search.toLowerCase())) return false;
    if (filterMarketplace !== 'All' && l.marketplace !== filterMarketplace) return false;
    if (filterStatus !== 'All' && l.status !== filterStatus) return false;
    return true;
  });

  return (
    <div style={{ padding: 24, maxWidth: 1100 }}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a' }}>Listings</h1>
          <p style={{ fontSize: 13, color: '#999', marginTop: 2 }}>{listings.length} total products across all marketplaces</p>
        </div>
        <button className="flex items-center gap-2" style={{ padding: '8px 16px', borderRadius: 10, background: BLUE, color: '#fff', fontSize: 13, fontWeight: 600, border: 'none', cursor: 'pointer' }}>
          <Plus size={15} />New Listing
        </button>
      </div>

      {error && <ErrorBanner message={error} onRetry={refetch} />}

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex items-center gap-2" style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: '6px 12px', flex: 1, maxWidth: 320 }}>
          <Search size={15} color="#999" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by title or SKU..." style={{ border: 'none', outline: 'none', fontSize: 13, width: '100%', background: 'transparent' }} />
        </div>
        <select value={filterMarketplace} onChange={e => setFilterMarketplace(e.target.value)} style={{ padding: '8px 12px', borderRadius: 10, border: '1px solid #e5e7eb', fontSize: 13, background: '#fff', cursor: 'pointer' }}>
          <option value="All">All Marketplaces</option>
          {MARKETPLACE_LIST.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} style={{ padding: '8px 12px', borderRadius: 10, border: '1px solid #e5e7eb', fontSize: 13, background: '#fff', cursor: 'pointer' }}>
          <option value="All">All Status</option>
          <option value="active">Active</option>
          <option value="sold">Sold</option>
          <option value="draft">Draft</option>
        </select>
      </div>

      {loading ? (
        <LoadingSpinner message="Loading listings..." />
      ) : listings.length === 0 && !error ? (
        <EmptyState icon={<Package size={32} />} title="No listings yet" subtitle="Create your first listing to get started" />
      ) : (
        /* Table */
        <div className="empire-card" style={{ padding: 0, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#f9f8f6', borderBottom: '1px solid #ece8e0' }}>
                <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: '#666' }}>Product</th>
                <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: '#666' }}>SKU</th>
                <th style={{ padding: '10px 14px', textAlign: 'right', fontWeight: 600, color: '#666' }}>Price</th>
                <th style={{ padding: '10px 14px', textAlign: 'center', fontWeight: 600, color: '#666' }}>Qty</th>
                <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: '#666' }}>Marketplace</th>
                <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: '#666' }}>Status</th>
                <th style={{ padding: '10px 14px', textAlign: 'center', fontWeight: 600, color: '#666' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(l => (
                <tr key={l.id} style={{ borderBottom: '1px solid #f3f1ed' }}
                  onMouseEnter={e => (e.currentTarget.style.background = '#fafaf8')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                  <td style={{ padding: '10px 14px' }}>
                    <div className="flex items-center gap-3">
                      <span style={{ fontSize: 20 }}>{l.image || <Package size={20} />}</span>
                      <div>
                        <div style={{ fontWeight: 600, color: '#1a1a1a' }}>{l.title}</div>
                        <div style={{ fontSize: 11, color: '#999' }}>{l.category}</div>
                      </div>
                    </div>
                  </td>
                  <td style={{ padding: '10px 14px', fontFamily: 'monospace', fontSize: 12, color: '#666' }}>{l.sku}</td>
                  <td style={{ padding: '10px 14px', textAlign: 'right', fontWeight: 600 }}>${l.price.toFixed(2)}</td>
                  <td style={{ padding: '10px 14px', textAlign: 'center', fontWeight: 600, color: l.qty === 0 ? '#ef4444' : '#1a1a1a' }}>{l.qty}</td>
                  <td style={{ padding: '10px 14px' }}><MarketplaceBadge name={l.marketplace} /></td>
                  <td style={{ padding: '10px 14px' }}><StatusBadge status={l.status} /></td>
                  <td style={{ padding: '10px 14px', textAlign: 'center' }}>
                    <div className="flex items-center justify-center gap-1">
                      <button style={{ padding: 4, borderRadius: 6, border: 'none', background: 'transparent', cursor: 'pointer', color: '#999' }} title="View"><Eye size={15} /></button>
                      <button style={{ padding: 4, borderRadius: 6, border: 'none', background: 'transparent', cursor: 'pointer', color: '#999' }} title="Edit"><Edit2 size={15} /></button>
                      <button style={{ padding: 4, borderRadius: 6, border: 'none', background: 'transparent', cursor: 'pointer', color: '#999' }} title="Delete"><Trash2 size={15} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <div style={{ padding: 40, textAlign: 'center', color: '#999', fontSize: 13 }}>No listings match your filters</div>
          )}
        </div>
      )}
    </div>
  );
}

// ============ 3. ORDERS ============

function OrdersSection() {
  const { orders, loading, error, refetch } = useOrders();
  const [search, setSearch] = useState('');
  const [filterMarketplace, setFilterMarketplace] = useState('All');
  const [filterStatus, setFilterStatus] = useState('All');

  const filtered = orders.filter(o => {
    if (search && !o.id.toLowerCase().includes(search.toLowerCase()) && !o.buyer.toLowerCase().includes(search.toLowerCase()) && !o.items.toLowerCase().includes(search.toLowerCase())) return false;
    if (filterMarketplace !== 'All' && o.marketplace !== filterMarketplace) return false;
    if (filterStatus !== 'All' && o.status !== filterStatus) return false;
    return true;
  });

  return (
    <div style={{ padding: 24, maxWidth: 1100 }}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a' }}>Orders</h1>
          <p style={{ fontSize: 13, color: '#999', marginTop: 2 }}>{orders.length} total orders across all marketplaces</p>
        </div>
      </div>

      {error && <ErrorBanner message={error} onRetry={refetch} />}

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex items-center gap-2" style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10, padding: '6px 12px', flex: 1, maxWidth: 320 }}>
          <Search size={15} color="#999" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search orders, buyers, items..." style={{ border: 'none', outline: 'none', fontSize: 13, width: '100%', background: 'transparent' }} />
        </div>
        <select value={filterMarketplace} onChange={e => setFilterMarketplace(e.target.value)} style={{ padding: '8px 12px', borderRadius: 10, border: '1px solid #e5e7eb', fontSize: 13, background: '#fff', cursor: 'pointer' }}>
          <option value="All">All Marketplaces</option>
          {MARKETPLACE_LIST.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)} style={{ padding: '8px 12px', borderRadius: 10, border: '1px solid #e5e7eb', fontSize: 13, background: '#fff', cursor: 'pointer' }}>
          <option value="All">All Status</option>
          <option value="pending">Pending</option>
          <option value="shipped">Shipped</option>
          <option value="delivered">Delivered</option>
        </select>
      </div>

      {loading ? (
        <LoadingSpinner message="Loading orders..." />
      ) : orders.length === 0 && !error ? (
        <EmptyState icon={<ShoppingCart size={32} />} title="No orders yet" subtitle="Orders will appear here as they come in" />
      ) : (
        /* Table */
        <div className="empire-card" style={{ padding: 0, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#f9f8f6', borderBottom: '1px solid #ece8e0' }}>
                <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: '#666' }}>Order ID</th>
                <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: '#666' }}>Marketplace</th>
                <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: '#666' }}>Buyer</th>
                <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: '#666' }}>Items</th>
                <th style={{ padding: '10px 14px', textAlign: 'right', fontWeight: 600, color: '#666' }}>Total</th>
                <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: '#666' }}>Status</th>
                <th style={{ padding: '10px 14px', textAlign: 'left', fontWeight: 600, color: '#666' }}>Date</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(o => (
                <tr key={o.id} style={{ borderBottom: '1px solid #f3f1ed' }}
                  onMouseEnter={e => (e.currentTarget.style.background = '#fafaf8')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                  <td style={{ padding: '10px 14px', fontWeight: 600, color: BLUE }}>{o.id}</td>
                  <td style={{ padding: '10px 14px' }}><MarketplaceBadge name={o.marketplace} /></td>
                  <td style={{ padding: '10px 14px', color: '#1a1a1a' }}>{o.buyer}</td>
                  <td style={{ padding: '10px 14px', color: '#666', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{o.items}</td>
                  <td style={{ padding: '10px 14px', textAlign: 'right', fontWeight: 600 }}>${o.total.toFixed(2)}</td>
                  <td style={{ padding: '10px 14px' }}><StatusBadge status={o.status} /></td>
                  <td style={{ padding: '10px 14px', color: '#666' }}>{o.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <div style={{ padding: 40, textAlign: 'center', color: '#999', fontSize: 13 }}>No orders match your filters</div>
          )}
        </div>
      )}
    </div>
  );
}

// ============ 4. CROSS-LIST ============

function CrossListSection() {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [sku, setSku] = useState('');
  const [category, setCategory] = useState('Clothing');
  const [condition, setCondition] = useState('New');
  const [quantity, setQuantity] = useState('1');
  const [selectedPlatforms, setSelectedPlatforms] = useState<Record<string, boolean>>({ eBay: true, Poshmark: false, Mercari: false, Amazon: false, Etsy: false });
  const [prices, setPrices] = useState<Record<string, string>>({ eBay: '', Poshmark: '', Mercari: '', Amazon: '', Etsy: '' });

  const togglePlatform = (p: string) => {
    setSelectedPlatforms(prev => ({ ...prev, [p]: !prev[p] }));
  };

  const selectedCount = Object.values(selectedPlatforms).filter(Boolean).length;

  return (
    <div style={{ padding: 24, maxWidth: 900 }}>
      <div className="mb-6">
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a' }}>Cross-List Product</h1>
        <p style={{ fontSize: 13, color: '#999', marginTop: 2 }}>List a product across multiple marketplaces simultaneously</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Left: Product Details */}
        <div>
          <div className="empire-card" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }}>Product Details</h3>

            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Title</label>
              <input value={title} onChange={e => setTitle(e.target.value)} placeholder="Product title..." style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13, outline: 'none' }} />
            </div>

            <div style={{ marginBottom: 14 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Description</label>
              <textarea value={description} onChange={e => setDescription(e.target.value)} placeholder="Product description..." rows={4} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13, outline: 'none', resize: 'vertical' }} />
            </div>

            <div className="grid grid-cols-2 gap-3" style={{ marginBottom: 14 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>SKU</label>
                <input value={sku} onChange={e => setSku(e.target.value)} placeholder="SKU-001" style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13, outline: 'none' }} />
              </div>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Quantity</label>
                <input type="number" value={quantity} onChange={e => setQuantity(e.target.value)} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13, outline: 'none' }} />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Category</label>
                <select value={category} onChange={e => setCategory(e.target.value)} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13, background: '#fff', cursor: 'pointer' }}>
                  <option>Clothing</option>
                  <option>Electronics</option>
                  <option>Home Goods</option>
                  <option>Accessories</option>
                  <option>Collectibles</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Condition</label>
                <select value={condition} onChange={e => setCondition(e.target.value)} style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #e5e7eb', fontSize: 13, background: '#fff', cursor: 'pointer' }}>
                  <option>New</option>
                  <option>Like New</option>
                  <option>Good</option>
                  <option>Fair</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Platform Selection & Pricing */}
        <div>
          <div className="empire-card" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }}>Platforms & Pricing</h3>
            <p style={{ fontSize: 12, color: '#999', marginBottom: 14 }}>Select marketplaces and set per-platform pricing</p>

            <div className="flex flex-col gap-3">
              {MARKETPLACE_LIST.map(mp => {
                const isSelected = selectedPlatforms[mp];
                const color = MARKETPLACE_COLORS[mp];
                return (
                  <div key={mp} style={{
                    padding: '12px 14px', borderRadius: 10,
                    border: `1.5px solid ${isSelected ? color : '#e5e7eb'}`,
                    background: isSelected ? color + '08' : '#fff',
                    transition: 'all 0.15s ease',
                  }}>
                    <div className="flex items-center justify-between">
                      <label className="flex items-center gap-3 cursor-pointer" style={{ flex: 1 }}>
                        <input type="checkbox" checked={isSelected} onChange={() => togglePlatform(mp)}
                          style={{ accentColor: color, width: 16, height: 16 }} />
                        <span style={{ fontSize: 13, fontWeight: 600, color: isSelected ? color : '#666' }}>{mp}</span>
                      </label>
                      {isSelected && (
                        <div className="flex items-center gap-1">
                          <span style={{ fontSize: 13, color: '#666' }}>$</span>
                          <input
                            value={prices[mp]}
                            onChange={e => setPrices(prev => ({ ...prev, [mp]: e.target.value }))}
                            placeholder="0.00"
                            style={{ width: 80, padding: '4px 8px', borderRadius: 6, border: '1px solid #e5e7eb', fontSize: 13, outline: 'none', textAlign: 'right' }}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <button style={{
            marginTop: 16, width: '100%', padding: '12px 20px', borderRadius: 10,
            background: selectedCount > 0 ? BLUE : '#e5e7eb',
            color: selectedCount > 0 ? '#fff' : '#999',
            fontSize: 14, fontWeight: 700, border: 'none', cursor: selectedCount > 0 ? 'pointer' : 'not-allowed',
          }}>
            <div className="flex items-center justify-center gap-2">
              <Copy size={16} />
              List on {selectedCount} Platform{selectedCount !== 1 ? 's' : ''}
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}

// ============ 5. ANALYTICS ============

function AnalyticsSection() {
  const { listings, loading: listingsLoading, error: listingsError, refetch: refetchListings } = useListings();
  const { orders, loading: ordersLoading, error: ordersError, refetch: refetchOrders } = useOrders();

  const loading = listingsLoading || ordersLoading;

  const revenueByMarketplace = MARKETPLACE_LIST.map(mp => ({
    name: mp,
    revenue: orders.filter(o => o.marketplace === mp).reduce((s, o) => s + o.total, 0),
    orders: orders.filter(o => o.marketplace === mp).length,
    color: MARKETPLACE_COLORS[mp],
  }));

  const totalRevenue = revenueByMarketplace.reduce((s, m) => s + m.revenue, 0);
  const avgOrderValue = orders.length > 0 ? totalRevenue / orders.length : 0;

  // Top products by revenue (from orders)
  const productRevenue: Record<string, number> = {};
  orders.forEach(o => {
    const key = o.items.split(' x')[0]; // handle "item x2" format
    productRevenue[key] = (productRevenue[key] || 0) + o.total;
  });
  const topProducts = Object.entries(productRevenue)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  const highestSale = orders.length > 0 ? Math.max(...orders.map(o => o.total)) : 0;

  return (
    <div style={{ padding: 24, maxWidth: 1100 }}>
      <div className="mb-6">
        <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a' }}>Analytics</h1>
        <p style={{ fontSize: 13, color: '#999', marginTop: 2 }}>Sales performance across all marketplaces</p>
      </div>

      {listingsError && <ErrorBanner message={listingsError} onRetry={refetchListings} />}
      {ordersError && <ErrorBanner message={ordersError} onRetry={refetchOrders} />}

      {loading ? (
        <LoadingSpinner message="Loading analytics..." />
      ) : (
        <>
          {/* Metric Cards */}
          <div className="grid grid-cols-4 gap-4 mb-6">
            <KPI icon={<DollarSign size={16} />} iconBg="#dcfce7" iconColor="#16a34a" label="Total Revenue" value={`$${totalRevenue.toFixed(2)}`} sub="All marketplaces" />
            <KPI icon={<ShoppingCart size={16} />} iconBg={BLUE_BG} iconColor={BLUE} label="Total Orders" value={String(orders.length)} sub="Last 30 days" />
            <KPI icon={<TrendingUp size={16} />} iconBg="#fef3c7" iconColor="#d97706" label="Avg Order Value" value={`$${avgOrderValue.toFixed(2)}`} sub="Per transaction" />
            <KPI icon={<Package size={16} />} iconBg="#f3e8ff" iconColor="#9333ea" label="Products Listed" value={String(listings.length)} sub={`${listings.filter(l => l.status === 'active').length} active`} />
          </div>

          <div className="grid grid-cols-2 gap-6">
            {/* Revenue by Marketplace (visual chart) */}
            <div className="empire-card" style={{ padding: 20 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }}>Revenue by Marketplace</h3>

              {totalRevenue === 0 ? (
                <EmptyState icon={<BarChart3 size={32} />} title="No revenue data" subtitle="Revenue chart will appear once orders come in" />
              ) : (
                <>
                  {/* Pie-style circle */}
                  <div className="flex items-center justify-center mb-6" style={{ position: 'relative' }}>
                    <svg width={180} height={180} viewBox="0 0 180 180">
                      {(() => {
                        let cumAngle = 0;
                        return revenueByMarketplace.filter(m => m.revenue > 0).map((m) => {
                          const pct = m.revenue / totalRevenue;
                          const angle = pct * 360;
                          const startAngle = cumAngle;
                          cumAngle += angle;
                          const startRad = (startAngle - 90) * (Math.PI / 180);
                          const endRad = (startAngle + angle - 90) * (Math.PI / 180);
                          const largeArc = angle > 180 ? 1 : 0;
                          const r = 80;
                          const cx = 90, cy = 90;
                          const x1 = cx + r * Math.cos(startRad);
                          const y1 = cy + r * Math.sin(startRad);
                          const x2 = cx + r * Math.cos(endRad);
                          const y2 = cy + r * Math.sin(endRad);
                          const d = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`;
                          return <path key={m.name} d={d} fill={m.color} opacity={0.85} />;
                        });
                      })()}
                      <circle cx={90} cy={90} r={40} fill="#fff" />
                      <text x={90} y={85} textAnchor="middle" style={{ fontSize: 14, fontWeight: 700, fill: '#1a1a1a' }}>${totalRevenue.toFixed(0)}</text>
                      <text x={90} y={100} textAnchor="middle" style={{ fontSize: 10, fill: '#999' }}>Total</text>
                    </svg>
                  </div>

                  {/* Legend */}
                  <div className="flex flex-col gap-2">
                    {revenueByMarketplace.map(m => (
                      <div key={m.name} className="flex items-center justify-between" style={{ fontSize: 13 }}>
                        <div className="flex items-center gap-2">
                          <div style={{ width: 10, height: 10, borderRadius: 3, background: m.color }} />
                          <span style={{ fontWeight: 500, color: '#1a1a1a' }}>{m.name}</span>
                        </div>
                        <div className="flex items-center gap-4">
                          <span style={{ color: '#666' }}>{m.orders} orders</span>
                          <span style={{ fontWeight: 700, color: m.color }}>${m.revenue.toFixed(2)}</span>
                          <span style={{ fontSize: 11, color: '#999' }}>{totalRevenue > 0 ? ((m.revenue / totalRevenue) * 100).toFixed(0) : 0}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* Top Products */}
            <div className="empire-card" style={{ padding: 20 }}>
              <h3 style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }}>Top Products by Revenue</h3>

              {topProducts.length === 0 ? (
                <EmptyState icon={<TrendingUp size={32} />} title="No product data" subtitle="Product rankings will appear with order data" />
              ) : (
                <div className="flex flex-col gap-3">
                  {topProducts.map(([name, rev], i) => {
                    const pct = topProducts[0][1] > 0 ? (rev / topProducts[0][1]) * 100 : 0;
                    return (
                      <div key={name}>
                        <div className="flex items-center justify-between mb-1">
                          <span style={{ fontSize: 13, fontWeight: 500, color: '#1a1a1a' }}>{i + 1}. {name}</span>
                          <span style={{ fontSize: 13, fontWeight: 700, color: BLUE }}>${rev.toFixed(2)}</span>
                        </div>
                        <div style={{ height: 6, borderRadius: 3, background: '#f3f4f6', overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${pct}%`, borderRadius: 3, background: BLUE, transition: 'width 0.3s ease' }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Revenue Metrics */}
              <div style={{ marginTop: 24, paddingTop: 16, borderTop: '1px solid #ece8e0' }}>
                <h4 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 12 }}>Revenue Metrics</h4>
                <div className="grid grid-cols-2 gap-3">
                  <div style={{ padding: '10px 12px', background: '#f9fafb', borderRadius: 8 }}>
                    <div style={{ fontSize: 10, fontWeight: 600, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5 }}>Highest Sale</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a', marginTop: 2 }}>${highestSale.toFixed(2)}</div>
                  </div>
                  <div style={{ padding: '10px 12px', background: '#f9fafb', borderRadius: 8 }}>
                    <div style={{ fontSize: 10, fontWeight: 600, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5 }}>Avg Per Day</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a', marginTop: 2 }}>${(totalRevenue / 30).toFixed(2)}</div>
                  </div>
                  <div style={{ padding: '10px 12px', background: '#f9fafb', borderRadius: 8 }}>
                    <div style={{ fontSize: 10, fontWeight: 600, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5 }}>Fill Rate</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#16a34a', marginTop: 2 }}>--</div>
                  </div>
                  <div style={{ padding: '10px 12px', background: '#f9fafb', borderRadius: 8 }}>
                    <div style={{ fontSize: 10, fontWeight: 600, color: '#999', textTransform: 'uppercase', letterSpacing: 0.5 }}>Return Rate</div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a', marginTop: 2 }}>--</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

// ============ MAIN COMPONENT ============

export default function MarketForgePage() {
  const [section, setSection] = useState<Section>('dashboard');

  const renderContent = () => {
    switch (section) {
      case 'dashboard': return <DashboardSection onNavigate={setSection} />;
      case 'smartlister': return <SmartListerPanel accentColor="#2563eb" accentBg="#dbeafe" marketplaces={MARKETPLACE_LIST} marketplaceColors={MARKETPLACE_COLORS} productLabel="MarketForge" />;
      case 'listings': return <ListingsSection />;
      case 'orders': return <OrdersSection />;
      case 'crosslist': return <CrossListSection />;
      case 'analytics': return <AnalyticsSection />;
      case 'payments': return <PaymentModule product="market" />;
      case 'docs': return <div style={{ padding: 24 }}><ProductDocs product="market" /></div>;
      default: return <DashboardSection onNavigate={setSection} />;
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      <nav style={{ width: 200, background: '#fff', borderRight: '1px solid #ece8e0', flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '18px 16px', borderBottom: '1px solid #ece8e0' }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: BLUE_BG }}>
              <Store size={18} style={{ color: BLUE }} />
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>MarketForge</div>
              <div style={{ fontSize: 10, color: '#999' }}>Multi-Marketplace</div>
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto" style={{ padding: '10px 10px' }}>
          <div className="flex flex-col gap-1.5">
            {NAV_SECTIONS.map(nav => {
              const Icon = nav.icon;
              const isActive = section === nav.id;
              return (
                <button key={nav.id}
                  onClick={() => setSection(nav.id)}
                  className="w-full flex items-center gap-3 text-left cursor-pointer transition-all"
                  style={{
                    padding: '10px 14px', borderRadius: 12, fontSize: 13,
                    fontWeight: isActive ? 700 : 500,
                    background: isActive ? BLUE_BG : 'transparent',
                    color: isActive ? BLUE : '#666',
                    border: isActive ? `1.5px solid ${BLUE_BORDER}` : '1.5px solid transparent',
                  }}
                  onMouseEnter={e => { if (!isActive) { e.currentTarget.style.background = '#f5f3ef'; e.currentTarget.style.borderColor = '#ece8e0'; } }}
                  onMouseLeave={e => { if (!isActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'transparent'; } }}
                >
                  <Icon size={17} />
                  {nav.label}
                </button>
              );
            })}
          </div>
        </div>
      </nav>
      <div className="flex-1 overflow-y-auto" style={{ background: '#f5f2ed' }}>
        {renderContent()}
      </div>
    </div>
  );
}
