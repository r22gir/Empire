'use client';

import { useState, useEffect } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Order {
  id: number;
  product: string;
  status: string;
  due_date?: string;
  total: number;
  notes?: string;
  images?: string;
  client_id?: number;
  created_at?: string;
}

interface Client {
  id: number;
  name: string;
  email?: string;
  phone?: string;
  address?: string;
  total_orders: number;
  total_spent: number;
  created_at?: string;
}

interface Stats {
  total_orders: number;
  pending_orders: number;
  in_progress_orders: number;
  completed_orders: number;
  total_revenue: number;
  total_clients: number;
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-500',
  in_progress: 'bg-blue-500',
  completed: 'bg-green-500',
  cancelled: 'bg-red-500',
};

export default function WorkroomForgePage() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [activeTab, setActiveTab] = useState<'orders' | 'clients'>('orders');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Order form state
  const [showOrderForm, setShowOrderForm] = useState(false);
  const [orderForm, setOrderForm] = useState({
    product: '',
    status: 'pending',
    due_date: '',
    total: '',
    notes: '',
    client_id: '',
  });
  const [orderFormError, setOrderFormError] = useState<string | null>(null);
  const [orderFormLoading, setOrderFormLoading] = useState(false);

  // Client form state
  const [showClientForm, setShowClientForm] = useState(false);
  const [clientForm, setClientForm] = useState({
    name: '',
    email: '',
    phone: '',
    address: '',
  });
  const [clientFormError, setClientFormError] = useState<string | null>(null);
  const [clientFormLoading, setClientFormLoading] = useState(false);

  useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    setError(null);
    try {
      await Promise.all([fetchOrders(), fetchClients(), fetchStats()]);
    } finally {
      setLoading(false);
    }
  };

  const fetchOrders = async () => {
    try {
      const res = await fetch(`${API_URL}/api/workroom/orders`);
      if (!res.ok) throw new Error('Failed to fetch orders');
      const data = await res.json();
      setOrders(data);
    } catch (e) {
      console.error('Failed to fetch orders:', e);
      setError('Failed to load orders. Is the backend running?');
    }
  };

  const fetchClients = async () => {
    try {
      const res = await fetch(`${API_URL}/api/workroom/clients`);
      if (!res.ok) throw new Error('Failed to fetch clients');
      const data = await res.json();
      setClients(data);
    } catch (e) {
      console.error('Failed to fetch clients:', e);
      setError('Failed to load clients. Is the backend running?');
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_URL}/api/workroom/stats`);
      if (!res.ok) throw new Error('Failed to fetch stats');
      const data = await res.json();
      setStats(data);
    } catch (e) {
      console.error('Failed to fetch stats:', e);
    }
  };

  const submitOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    setOrderFormError(null);
    setOrderFormLoading(true);
    try {
      const payload = {
        product: orderForm.product,
        status: orderForm.status,
        due_date: orderForm.due_date || null,
        total: parseFloat(orderForm.total) || 0,
        notes: orderForm.notes || null,
        client_id: orderForm.client_id ? parseInt(orderForm.client_id) : null,
      };
      const res = await fetch(`${API_URL}/api/workroom/orders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to create order');
      }
      setOrderForm({ product: '', status: 'pending', due_date: '', total: '', notes: '', client_id: '' });
      setShowOrderForm(false);
      await fetchOrders();
      await fetchStats();
    } catch (e: unknown) {
      setOrderFormError(e instanceof Error ? e.message : 'Failed to create order');
    } finally {
      setOrderFormLoading(false);
    }
  };

  const updateOrderStatus = async (id: number, newStatus: string) => {
    try {
      const res = await fetch(`${API_URL}/api/workroom/orders/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (!res.ok) throw new Error('Failed to update order status');
      await fetchOrders();
      await fetchStats();
    } catch (e) {
      console.error('Failed to update order status:', e);
    }
  };

  const deleteOrder = async (id: number) => {
    if (!confirm('Delete this order?')) return;
    try {
      const res = await fetch(`${API_URL}/api/workroom/orders/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete order');
      await fetchOrders();
      await fetchStats();
    } catch (e) {
      console.error('Failed to delete order:', e);
    }
  };

  const submitClient = async (e: React.FormEvent) => {
    e.preventDefault();
    setClientFormError(null);
    setClientFormLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/workroom/clients`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: clientForm.name,
          email: clientForm.email || null,
          phone: clientForm.phone || null,
          address: clientForm.address || null,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to create client');
      }
      setClientForm({ name: '', email: '', phone: '', address: '' });
      setShowClientForm(false);
      await fetchClients();
      await fetchStats();
    } catch (e: unknown) {
      setClientFormError(e instanceof Error ? e.message : 'Failed to create client');
    } finally {
      setClientFormLoading(false);
    }
  };

  const deleteClient = async (id: number) => {
    if (!confirm('Delete this client?')) return;
    try {
      const res = await fetch(`${API_URL}/api/workroom/clients/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete client');
      await fetchClients();
      await fetchStats();
    } catch (e) {
      console.error('Failed to delete client:', e);
    }
  };

  return (
    <div className="min-h-screen bg-[#050508] text-white p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-purple-400">Workroom Forge</h1>
        <p className="text-gray-400 mt-1">Manage custom orders and clients</p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
          {[
            { label: 'Total Orders', value: stats.total_orders },
            { label: 'Pending', value: stats.pending_orders },
            { label: 'In Progress', value: stats.in_progress_orders },
            { label: 'Completed', value: stats.completed_orders },
            { label: 'Revenue', value: `$${stats.total_revenue.toFixed(2)}` },
            { label: 'Clients', value: stats.total_clients },
          ].map((stat) => (
            <div key={stat.label} className="bg-[#0a0a0f] rounded-xl p-4 border border-gray-800">
              <p className="text-xs text-gray-500 mb-1">{stat.label}</p>
              <p className="text-2xl font-bold text-white">{stat.value}</p>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        {(['orders', 'clients'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-5 py-2 rounded-lg font-medium capitalize ${
              activeTab === tab
                ? 'bg-purple-600 text-white'
                : 'bg-[#0a0a0f] text-gray-400 hover:text-white border border-gray-800'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Orders Tab */}
      {activeTab === 'orders' && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Orders</h2>
            <button
              onClick={() => setShowOrderForm(true)}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg text-sm font-medium"
            >
              + New Order
            </button>
          </div>

          {/* New Order Form */}
          {showOrderForm && (
            <div className="mb-6 bg-[#0a0a0f] border border-gray-800 rounded-xl p-5">
              <h3 className="font-semibold mb-4">Create Order</h3>
              <form onSubmit={submitOrder} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Product / Description *</label>
                  <input
                    required
                    value={orderForm.product}
                    onChange={(e) => setOrderForm({ ...orderForm, product: e.target.value })}
                    className="w-full bg-[#050508] border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                    placeholder="e.g. Custom curtains"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Status</label>
                  <select
                    value={orderForm.status}
                    onChange={(e) => setOrderForm({ ...orderForm, status: e.target.value })}
                    className="w-full bg-[#050508] border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                  >
                    <option value="pending">Pending</option>
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Due Date</label>
                  <input
                    type="date"
                    value={orderForm.due_date}
                    onChange={(e) => setOrderForm({ ...orderForm, due_date: e.target.value })}
                    className="w-full bg-[#050508] border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Total ($)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={orderForm.total}
                    onChange={(e) => setOrderForm({ ...orderForm, total: e.target.value })}
                    className="w-full bg-[#050508] border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                    placeholder="0.00"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Client ID</label>
                  <input
                    type="number"
                    value={orderForm.client_id}
                    onChange={(e) => setOrderForm({ ...orderForm, client_id: e.target.value })}
                    className="w-full bg-[#050508] border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                    placeholder="Optional"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Notes</label>
                  <input
                    value={orderForm.notes}
                    onChange={(e) => setOrderForm({ ...orderForm, notes: e.target.value })}
                    className="w-full bg-[#050508] border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                    placeholder="Optional notes"
                  />
                </div>
                {orderFormError && (
                  <div className="md:col-span-2 text-red-400 text-sm">{orderFormError}</div>
                )}
                <div className="md:col-span-2 flex gap-3">
                  <button
                    type="submit"
                    disabled={orderFormLoading}
                    className="px-5 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 rounded-lg text-sm font-medium"
                  >
                    {orderFormLoading ? 'Saving...' : 'Create Order'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowOrderForm(false)}
                    className="px-5 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm font-medium"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}

          {loading ? (
            <p className="text-gray-400">Loading...</p>
          ) : orders.length === 0 ? (
            <p className="text-gray-500 text-sm">No orders yet. Create your first order above.</p>
          ) : (
            <div className="space-y-3">
              {orders.map((order) => (
                <div
                  key={order.id}
                  className="bg-[#0a0a0f] border border-gray-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center gap-3"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`inline-block w-2 h-2 rounded-full ${STATUS_COLORS[order.status] ?? 'bg-gray-500'}`}
                      />
                      <span className="font-medium text-white">{order.product}</span>
                    </div>
                    <div className="flex flex-wrap gap-3 text-xs text-gray-400">
                      <span>#{order.id}</span>
                      {order.due_date && <span>Due: {order.due_date}</span>}
                      {order.client_id && <span>Client: {order.client_id}</span>}
                      <span className="text-green-400 font-medium">${order.total.toFixed(2)}</span>
                    </div>
                    {order.notes && <p className="mt-1 text-xs text-gray-500">{order.notes}</p>}
                  </div>
                  <div className="flex items-center gap-2">
                    <select
                      value={order.status}
                      onChange={(e) => updateOrderStatus(order.id, e.target.value)}
                      className="bg-[#050508] border border-gray-700 rounded-lg px-2 py-1 text-xs text-gray-300"
                    >
                      <option value="pending">Pending</option>
                      <option value="in_progress">In Progress</option>
                      <option value="completed">Completed</option>
                      <option value="cancelled">Cancelled</option>
                    </select>
                    <button
                      onClick={() => deleteOrder(order.id)}
                      className="px-3 py-1 bg-red-900/40 hover:bg-red-800/60 text-red-400 rounded-lg text-xs"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Clients Tab */}
      {activeTab === 'clients' && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Clients</h2>
            <button
              onClick={() => setShowClientForm(true)}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg text-sm font-medium"
            >
              + New Client
            </button>
          </div>

          {/* New Client Form */}
          {showClientForm && (
            <div className="mb-6 bg-[#0a0a0f] border border-gray-800 rounded-xl p-5">
              <h3 className="font-semibold mb-4">Create Client</h3>
              <form onSubmit={submitClient} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Name *</label>
                  <input
                    required
                    value={clientForm.name}
                    onChange={(e) => setClientForm({ ...clientForm, name: e.target.value })}
                    className="w-full bg-[#050508] border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                    placeholder="Client name"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Email</label>
                  <input
                    type="email"
                    value={clientForm.email}
                    onChange={(e) => setClientForm({ ...clientForm, email: e.target.value })}
                    className="w-full bg-[#050508] border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                    placeholder="email@example.com"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Phone</label>
                  <input
                    value={clientForm.phone}
                    onChange={(e) => setClientForm({ ...clientForm, phone: e.target.value })}
                    className="w-full bg-[#050508] border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                    placeholder="+1 (555) 000-0000"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Address</label>
                  <input
                    value={clientForm.address}
                    onChange={(e) => setClientForm({ ...clientForm, address: e.target.value })}
                    className="w-full bg-[#050508] border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                    placeholder="123 Main St"
                  />
                </div>
                {clientFormError && (
                  <div className="md:col-span-2 text-red-400 text-sm">{clientFormError}</div>
                )}
                <div className="md:col-span-2 flex gap-3">
                  <button
                    type="submit"
                    disabled={clientFormLoading}
                    className="px-5 py-2 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 rounded-lg text-sm font-medium"
                  >
                    {clientFormLoading ? 'Saving...' : 'Create Client'}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowClientForm(false)}
                    className="px-5 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm font-medium"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          )}

          {loading ? (
            <p className="text-gray-400">Loading...</p>
          ) : clients.length === 0 ? (
            <p className="text-gray-500 text-sm">No clients yet. Create your first client above.</p>
          ) : (
            <div className="space-y-3">
              {clients.map((client) => (
                <div
                  key={client.id}
                  className="bg-[#0a0a0f] border border-gray-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center gap-3"
                >
                  <div className="flex-1">
                    <p className="font-medium text-white">{client.name}</p>
                    <div className="flex flex-wrap gap-3 text-xs text-gray-400 mt-1">
                      <span>#{client.id}</span>
                      {client.email && <span>{client.email}</span>}
                      {client.phone && <span>{client.phone}</span>}
                      <span>{client.total_orders} orders</span>
                      <span className="text-green-400">${client.total_spent.toFixed(2)} spent</span>
                    </div>
                    {client.address && (
                      <p className="mt-1 text-xs text-gray-500">{client.address}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => deleteClient(client.id)}
                      className="px-3 py-1 bg-red-900/40 hover:bg-red-800/60 text-red-400 rounded-lg text-xs"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
