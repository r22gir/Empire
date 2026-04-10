'use client';

import { useState, useEffect } from 'react';
import { ShoppingCart, Loader2, Package, Truck, CheckCircle, Clock, AlertCircle, ExternalLink } from 'lucide-react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface Order {
  id: number;
  listing_id: number | null;
  source_product_id: number | null;
  platform: string;
  buyer_name: string;
  sale_price: number;
  platform_fee: number;
  source_order_id: string;
  source_order_cost: number;
  source_order_status: string;
  tracking_number: string;
  tracking_carrier: string;
  profit: number;
  status: string;
  notes: string;
  created_at: string;
  listing_title?: string;
  listing_platform?: string;
}

interface OrdersResponse {
  items: Order[];
  total: number;
}

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; icon: any }> = {
  new: { label: 'New', color: '#06b6d4', bg: '#ecfeff', icon: Clock },
  source_ordered: { label: 'Source Ordered', color: '#8b5cf6', bg: '#f5f3ff', icon: Package },
  shipped: { label: 'Shipped', color: '#f59e0b', bg: '#fff7ed', icon: Truck },
  completed: { label: 'Completed', color: '#16a34a', bg: '#f0fdf4', icon: CheckCircle },
  refunded: { label: 'Refunded', color: '#dc2626', bg: '#fef2f2', icon: AlertCircle },
  cancelled: { label: 'Cancelled', color: '#6b7280', bg: '#f9fafb', icon: AlertCircle },
};

export default function OrdersSection() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [platformFilter, setPlatformFilter] = useState<string>('');

  useEffect(() => {
    fetchOrders();
  }, [statusFilter, platformFilter]);

  const fetchOrders = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ limit: '100' });
      if (statusFilter) params.set('status', statusFilter);
      if (platformFilter) params.set('platform', platformFilter);

      const res = await fetch(`${API}/relist/orders?${params}`);
      const data: OrdersResponse = await res.json();
      setOrders(data.items || []);
    } catch (e) {
      console.error('Failed to fetch orders', e);
    } finally {
      setLoading(false);
    }
  };

  const getStatusConfig = (status: string) => {
    return STATUS_CONFIG[status] || { label: status, color: '#6b7280', bg: '#f9fafb', icon: Clock };
  };

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={32} className="animate-spin" style={{ color: '#06b6d4' }} />
      </div>
    );
  }

  return (
    <div className="max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold mb-1">Orders</h2>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>
            Track your sales, orders, and realized profit
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-6">
        <select
          className="form-input !w-40 text-sm"
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="new">New</option>
          <option value="source_ordered">Source Ordered</option>
          <option value="shipped">Shipped</option>
          <option value="completed">Completed</option>
          <option value="refunded">Refunded</option>
        </select>
        <select
          className="form-input !w-40 text-sm"
          value={platformFilter}
          onChange={e => setPlatformFilter(e.target.value)}
        >
          <option value="">All Platforms</option>
          <option value="ebay">eBay</option>
          <option value="etsy">Etsy</option>
          <option value="amazon">Amazon</option>
          <option value="shopify">Shopify</option>
          <option value="mercari">Mercari</option>
          <option value="poshmark">Poshmark</option>
        </select>
      </div>

      {/* Orders List */}
      {orders.length === 0 ? (
        <div className="empire-card text-center py-16">
          <ShoppingCart size={40} style={{ color: 'var(--muted)', margin: '0 auto 12px' }} />
          <p className="font-semibold mb-1">No orders yet</p>
          <p className="text-sm" style={{ color: 'var(--muted)' }}>
            Orders will appear here when you make sales on your listings
          </p>
          <div className="mt-4 p-4 rounded-lg text-left" style={{ background: '#f9fafb', border: '1px solid var(--border)' }}>
            <p className="text-sm font-semibold mb-2">Getting started:</p>
            <ol className="text-xs text-gray-600 space-y-1 list-decimal list-inside">
              <li>Import products from a URL using the Import URL section</li>
              <li>Review deals in AI Deal Finder</li>
              <li>Create listing drafts from strong deals</li>
              <li>Publish listings to your sales platforms</li>
              <li>Track orders here when items sell</li>
            </ol>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {orders.map(order => {
            const statusConfig = getStatusConfig(order.status);
            const StatusIcon = statusConfig.icon;

            return (
              <div key={order.id} className="empire-card">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <StatusIcon size={16} style={{ color: statusConfig.color }} />
                    <span
                      className="text-xs font-bold px-2 py-0.5 rounded"
                      style={{ background: statusConfig.bg, color: statusConfig.color }}
                    >
                      {statusConfig.label}
                    </span>
                    <span className="text-xs" style={{ color: 'var(--muted)' }}>
                      Order #{order.id}
                    </span>
                  </div>
                  <span className="text-xs" style={{ color: 'var(--muted)' }}>
                    {formatDate(order.created_at)}
                  </span>
                </div>

                <div className="grid grid-cols-4 gap-4 mb-3">
                  <div>
                    <span className="text-xs text-gray-500 block">Platform</span>
                    <span className="font-semibold text-sm capitalize">{order.platform}</span>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500 block">Sale Price</span>
                    <span className="font-semibold text-sm">${(order.sale_price || 0).toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500 block">Cost</span>
                    <span className="font-semibold text-sm">${(order.source_order_cost || 0).toFixed(2)}</span>
                  </div>
                  <div>
                    <span className="text-xs text-gray-500 block">Est. Profit</span>
                    <span
                      className="font-semibold text-sm"
                      style={{ color: (order.profit || 0) >= 0 ? '#16a34a' : '#dc2626' }}
                    >
                      ${(order.profit || 0).toFixed(2)}
                    </span>
                  </div>
                </div>

                {order.tracking_number && (
                  <div className="pt-3 border-t" style={{ borderColor: 'var(--border)' }}>
                    <div className="flex items-center gap-2 text-xs">
                      <Truck size={12} />
                      <span className="font-medium">{order.tracking_carrier || 'Tracking'}:</span>
                      <span style={{ color: '#06b6d4' }}>{order.tracking_number}</span>
                    </div>
                  </div>
                )}

                {order.notes && (
                  <div className="pt-3 border-t text-xs" style={{ borderColor: 'var(--border)', color: 'var(--muted)' }}>
                    {order.notes}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
