'use client';

import { useEffect, useState } from 'react';
import { sellerAPI } from '@/lib/api';
import { formatPrice, formatDate } from '@/lib/utils';
import Link from 'next/link';

export default function SellerDashboard() {
  const [orders, setOrders] = useState([]);
  const [stats, setStats] = useState({ revenue: 0, activeListings: 0, rating: 4.9 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const ordersData = await sellerAPI.orders({ status: 'paid' });
        setOrders(ordersData.orders || []);
        // In real app, fetch stats from API
        setStats({ revenue: 1247.50, activeListings: 23, rating: 4.9 });
      } catch (error) {
        console.error('Failed to load dashboard:', error);
      } finally {
        setLoading(false);
      }
    }
    loadDashboard();
  }, []);

  return (
    <div className="container py-8">
      <h1 className="text-3xl font-bold mb-8">Seller Dashboard</h1>

      {/* Stats */}
      <div className="grid md:grid-cols-3 gap-6 mb-8">
        <div className="card">
          <p className="text-sm text-gray-600 mb-2">This Month</p>
          <p className="text-3xl font-bold text-primary">
            {formatPrice(stats.revenue)}
          </p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-600 mb-2">Active Listings</p>
          <p className="text-3xl font-bold">{stats.activeListings}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-600 mb-2">Rating</p>
          <p className="text-3xl font-bold">⭐ {stats.rating}</p>
        </div>
      </div>

      {/* Needs Action */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4">🚨 Needs Action</h2>
        {loading ? (
          <div className="card animate-pulse">
            <div className="bg-gray-200 h-20 rounded"></div>
          </div>
        ) : orders.length === 0 ? (
          <div className="card">
            <p className="text-gray-500">No orders pending shipment</p>
          </div>
        ) : (
          <div className="space-y-4">
            {orders.map((order: any) => (
              <div key={order.id} className="card">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-bold mb-1">{order.product_title}</h3>
                    <p className="text-sm text-gray-600">
                      Order #{order.order_number} • {formatDate(order.created_at)}
                    </p>
                    <p className="text-sm text-gray-600">
                      Ship to: {order.shipping_address?.city}, {order.shipping_address?.state}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Link href={`/shipforge?order=${order.id}`} className="btn btn-primary">
                      Ship with ShipForge
                    </Link>
                    <button className="btn btn-outline">Mark Shipped</button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid md:grid-cols-3 gap-4">
        <Link href="/seller/listings/new" className="btn btn-primary text-center">
          + New Listing
        </Link>
        <Link href="/marketforge" className="btn btn-outline text-center">
          Import from MarketForge
        </Link>
        <Link href="/seller/orders" className="btn btn-outline text-center">
          View All Orders
        </Link>
      </div>
    </div>
  );
}
