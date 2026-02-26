'use client';
import { useState, useEffect } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface ProductStatus {
  id: string;
  name: string;
  container: string;
  port: number;
  emoji: string;
  status: string;
}

const PRODUCT_META: Record<string, { description: string; color: string }> = {
  'workroom-forge': { description: 'Order management & workshop tracking', color: 'from-orange-500 to-red-600' },
  'luxeforge': { description: 'Product configurator & custom quotes', color: 'from-purple-500 to-pink-600' },
  'install-forge': { description: 'Installation scheduling & dispatch', color: 'from-blue-500 to-cyan-600' },
  'quote-forge': { description: 'Quotes & proposals generator', color: 'from-green-500 to-emerald-600' },
  'max-ai': { description: 'AI assistant & task coordinator', color: 'from-amber-500 to-orange-600' },
  'openclaw': { description: 'Skills-augmented local AI engine', color: 'from-red-500 to-orange-600' },
  'supportforge': { description: 'Customer support & ticketing', color: 'from-cyan-500 to-blue-600' },
  'cryptopay': { description: 'Cryptocurrency payment processing', color: 'from-yellow-500 to-orange-600' },
  'listingbot': { description: 'Multi-marketplace listing automation', color: 'from-pink-500 to-rose-600' },
  'shippingbot': { description: 'Shipping label & tracking automation', color: 'from-teal-500 to-green-600' },
  'analytics': { description: 'Business analytics & reporting', color: 'from-indigo-500 to-blue-600' },
  'founder-dashboard': { description: 'Founder command center', color: 'from-amber-600 to-yellow-700' },
  'marketplace-hub': { description: 'eBay, Poshmark, Mercari, Etsy hub', color: 'from-emerald-500 to-teal-600' },
};

export default function ProductsPage() {
  const [products, setProducts] = useState<ProductStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const res = await fetch(API_URL + '/docker/status');
      const data = await res.json();
      setProducts(data.products || []);
    } catch (e) {
      console.error('Failed to fetch docker status:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const toggleProduct = async (id: string, currentStatus: string) => {
    const action = currentStatus === 'running' ? 'stop' : 'start';
    setActionLoading(id);
    try {
      await fetch(`${API_URL}/docker/${id}/${action}`, { method: 'POST' });
      await fetchStatus();
    } catch (e) {
      console.error(`Failed to ${action} ${id}:`, e);
    } finally {
      setActionLoading(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'running': return <span className="px-2 py-0.5 rounded-full text-xs bg-green-500/20 text-green-400 border border-green-500/30">Running</span>;
      case 'exited': return <span className="px-2 py-0.5 rounded-full text-xs bg-red-500/20 text-red-400 border border-red-500/30">Stopped</span>;
      case 'not_found': return <span className="px-2 py-0.5 rounded-full text-xs bg-gray-500/20 text-gray-400 border border-gray-500/30">No Container</span>;
      default: return <span className="px-2 py-0.5 rounded-full text-xs bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">{status}</span>;
    }
  };

  return (
    <div className="min-h-screen bg-[#030308] text-white p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <a href="/" className="text-gray-400 hover:text-white mb-2 block text-sm">&larr; Back to Console</a>
            <h1 className="text-3xl font-bold">Empire Box® Business Center</h1>
            <p className="text-gray-500 mt-1">All {products.length} products &mdash; live Docker status</p>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span className="text-green-400">{products.filter(p => p.status === 'running').length} running</span>
            <span className="text-red-400">{products.filter(p => p.status === 'exited').length} stopped</span>
            <span className="text-gray-400">{products.filter(p => p.status === 'not_found').length} no container</span>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-20 text-gray-500">Loading product status...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {products.map((p) => {
              const meta = PRODUCT_META[p.id] || { description: '', color: 'from-gray-500 to-gray-600' };
              return (
                <div key={p.id} className="rounded-xl border border-gray-800 bg-[#0a0a0f] hover:border-amber-500/50 transition-all overflow-hidden">
                  <div className={`h-1 bg-gradient-to-r ${meta.color}`} />
                  <div className="p-5">
                    <div className="flex items-start justify-between mb-3">
                      <span className="text-3xl">{p.emoji}</span>
                      {getStatusBadge(p.status)}
                    </div>
                    <h3 className="font-bold text-lg mb-1">{p.name}</h3>
                    <p className="text-gray-500 text-sm mb-3">{meta.description}</p>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-gray-600">:{p.port}</span>
                      <div className="flex gap-2">
                        {p.status === 'running' && (
                          <a
                            href={`http://localhost:${p.port}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-3 py-1 rounded-lg text-xs bg-amber-600/20 text-amber-400 border border-amber-500/30 hover:bg-amber-600/40 transition"
                          >
                            Open
                          </a>
                        )}
                        {p.status !== 'not_found' && (
                          <button
                            onClick={() => toggleProduct(p.id, p.status)}
                            disabled={actionLoading === p.id}
                            className={`px-3 py-1 rounded-lg text-xs transition disabled:opacity-50 ${
                              p.status === 'running'
                                ? 'bg-red-600/20 text-red-400 border border-red-500/30 hover:bg-red-600/40'
                                : 'bg-green-600/20 text-green-400 border border-green-500/30 hover:bg-green-600/40'
                            }`}
                          >
                            {actionLoading === p.id ? '...' : p.status === 'running' ? 'Stop' : 'Start'}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
