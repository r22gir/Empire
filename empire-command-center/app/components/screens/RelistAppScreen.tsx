'use client';
import { useState, useEffect, useCallback } from 'react';
import {
  ShoppingBag, Plus, RefreshCw, Loader2, Search, Tag,
  ExternalLink, Trash2, Edit3, DollarSign, Package, TrendingUp,
} from 'lucide-react';
import { API } from '../../lib/api';

interface Listing {
  id: number;
  title: string;
  description: string;
  price: number;
  category: string;
  condition: string;
  platforms: string[];
  status: string;
  quantity: number;
  created_at: string;
}

const PLATFORMS = ['eBay', 'Facebook Marketplace', 'Craigslist', 'OfferUp', 'Mercari', 'Poshmark'];
const CONDITIONS = ['new', 'like_new', 'good', 'fair', 'poor'];
const CATEGORIES = ['Furniture', 'Electronics', 'Clothing', 'Home & Garden', 'Collectibles', 'Auto Parts', 'Other'];

export default function RelistAppScreen() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [newListing, setNewListing] = useState({ title: '', description: '', price: 0, category: 'Other', condition: 'good', platforms: [] as string[], quantity: 1 });
  const [saving, setSaving] = useState(false);

  const fetchListings = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/relist`);
      if (res.ok) {
        const data = await res.json();
        setListings(Array.isArray(data) ? data : []);
      } else {
        setListings([]);
      }
    } catch {
      setListings([]);
      setError('Could not connect to listings API');
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchListings(); }, [fetchListings]);

  const handleCreate = async () => {
    if (!newListing.title.trim()) return;
    setSaving(true);
    try {
      const res = await fetch(`${API}/relist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newListing),
      });
      if (res.ok) {
        setShowCreate(false);
        setNewListing({ title: '', description: '', price: 0, category: 'Other', condition: 'good', platforms: [], quantity: 1 });
        fetchListings();
      }
    } catch { /* */ }
    setSaving(false);
  };

  const handleDelete = async (id: number) => {
    try {
      await fetch(`${API}/relist/${id}`, { method: 'DELETE' });
      fetchListings();
    } catch { /* */ }
  };

  const togglePlatform = (p: string) => {
    setNewListing(prev => ({
      ...prev,
      platforms: prev.platforms.includes(p) ? prev.platforms.filter(x => x !== p) : [...prev.platforms, p],
    }));
  };

  const filtered = listings.filter(l =>
    !search || l.title?.toLowerCase().includes(search.toLowerCase()) || l.category?.toLowerCase().includes(search.toLowerCase())
  );

  const stats = {
    total: listings.length,
    active: listings.filter(l => l.status === 'active' || l.status === 'published').length,
    draft: listings.filter(l => l.status === 'draft').length,
    totalValue: listings.reduce((s, l) => s + (l.price || 0) * (l.quantity || 1), 0),
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#f5f2ed' }}>
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3 px-4 sm:px-5 py-3" style={{
        background: '#fff', borderBottom: '1px solid #ece8e0', flexShrink: 0,
      }}>
        <ShoppingBag size={20} style={{ color: '#06b6d4' }} />
        <h2 style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>RelistApp</h2>
        <span style={{ fontSize: 11, color: '#999' }}>Smart Cross-Platform Lister</span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <button onClick={() => setShowCreate(true)} style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '7px 14px',
            background: '#06b6d4', color: '#fff', border: 'none', borderRadius: 10,
            fontSize: 13, fontWeight: 600, cursor: 'pointer',
          }}>
            <Plus size={14} /> New Listing
          </button>
          <button onClick={fetchListings} style={{
            background: 'none', border: '1px solid #ece8e0', borderRadius: 8,
            padding: '6px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center',
          }}>
            <RefreshCw size={14} style={{ color: '#999' }} />
          </button>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="flex flex-wrap gap-3 px-4 py-3" style={{ background: '#fff', borderBottom: '1px solid #ece8e0' }}>
        {[
          { icon: <Package size={15} />, label: 'Total', value: stats.total, color: '#06b6d4' },
          { icon: <TrendingUp size={15} />, label: 'Active', value: stats.active, color: '#16a34a' },
          { icon: <Edit3 size={15} />, label: 'Draft', value: stats.draft, color: '#f59e0b' },
          { icon: <DollarSign size={15} />, label: 'Value', value: `$${stats.totalValue.toLocaleString()}`, color: '#b8960c' },
        ].map((s, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 12px', background: '#f9f8f6', borderRadius: 8 }}>
            <span style={{ color: s.color }}>{s.icon}</span>
            <span style={{ fontSize: 11, color: '#999' }}>{s.label}</span>
            <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>{s.value}</span>
          </div>
        ))}
      </div>

      {/* Search */}
      <div style={{ padding: '12px 16px', background: '#fff', borderBottom: '1px solid #ece8e0' }}>
        <div style={{ position: 'relative', maxWidth: 400 }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: 10, color: '#999' }} />
          <input
            value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search listings..."
            style={{
              width: '100%', padding: '8px 8px 8px 32px', border: '1px solid #ece8e0',
              borderRadius: 8, fontSize: 13, outline: 'none',
            }}
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto" style={{ padding: 16 }}>
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 size={20} className="animate-spin" style={{ color: '#06b6d4' }} />
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 20px', color: '#999' }}>
            <ShoppingBag size={48} style={{ color: '#ddd', margin: '0 auto 16px' }} />
            <div style={{ fontSize: 16, fontWeight: 600, color: '#666', marginBottom: 8 }}>
              {listings.length === 0 ? 'No listings yet' : 'No matching listings'}
            </div>
            <div style={{ fontSize: 13 }}>
              {listings.length === 0 ? 'Create your first listing to start cross-platform selling.' : 'Try a different search term.'}
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
            {filtered.map(listing => (
              <div key={listing.id} style={{
                background: '#fff', borderRadius: 12, border: '1px solid #ece8e0',
                padding: 16, display: 'flex', flexDirection: 'column', gap: 8,
              }}>
                <div className="flex items-start justify-between">
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 14, fontWeight: 600, color: '#1a1a1a' }}>{listing.title}</div>
                    <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>{listing.category} · {listing.condition}</div>
                  </div>
                  <span style={{
                    padding: '2px 8px', borderRadius: 6, fontSize: 10, fontWeight: 600,
                    background: listing.status === 'active' || listing.status === 'published' ? '#dcfce7' : '#fef3cd',
                    color: listing.status === 'active' || listing.status === 'published' ? '#16a34a' : '#b8960c',
                  }}>
                    {listing.status}
                  </span>
                </div>
                {listing.description && (
                  <div style={{ fontSize: 12, color: '#666', lineHeight: 1.4 }}>
                    {listing.description.slice(0, 100)}{listing.description.length > 100 ? '...' : ''}
                  </div>
                )}
                <div className="flex items-center justify-between" style={{ marginTop: 'auto' }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a' }}>
                    ${listing.price?.toFixed(2)}
                    {listing.quantity > 1 && <span style={{ fontSize: 11, color: '#999', fontWeight: 400 }}> × {listing.quantity}</span>}
                  </div>
                  <div className="flex gap-1">
                    {(listing.platforms || []).map((p, i) => (
                      <span key={i} style={{ fontSize: 9, padding: '2px 6px', background: '#f0f0f0', borderRadius: 4, color: '#666' }}>{p}</span>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2" style={{ marginTop: 4 }}>
                  <button onClick={() => handleDelete(listing.id)} style={{
                    display: 'flex', alignItems: 'center', gap: 4, padding: '5px 10px',
                    background: 'none', border: '1px solid #fecaca', borderRadius: 6,
                    fontSize: 11, color: '#dc2626', cursor: 'pointer',
                  }}>
                    <Trash2 size={12} /> Remove
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
          <div style={{ background: '#fff', borderRadius: 16, width: '100%', maxWidth: 500, maxHeight: '90vh', overflow: 'auto', padding: 24 }}>
            <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 16 }}>New Listing</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <input placeholder="Title *" value={newListing.title} onChange={e => setNewListing(p => ({ ...p, title: e.target.value }))}
                style={{ padding: '10px 12px', border: '1px solid #ddd', borderRadius: 8, fontSize: 14 }} />
              <textarea placeholder="Description" value={newListing.description} onChange={e => setNewListing(p => ({ ...p, description: e.target.value }))}
                rows={3} style={{ padding: '10px 12px', border: '1px solid #ddd', borderRadius: 8, fontSize: 14, resize: 'vertical' }} />
              <div className="flex gap-3">
                <input type="number" placeholder="Price" value={newListing.price || ''} onChange={e => setNewListing(p => ({ ...p, price: parseFloat(e.target.value) || 0 }))}
                  style={{ flex: 1, padding: '10px 12px', border: '1px solid #ddd', borderRadius: 8, fontSize: 14 }} />
                <input type="number" placeholder="Qty" value={newListing.quantity} onChange={e => setNewListing(p => ({ ...p, quantity: parseInt(e.target.value) || 1 }))}
                  style={{ width: 80, padding: '10px 12px', border: '1px solid #ddd', borderRadius: 8, fontSize: 14 }} />
              </div>
              <select value={newListing.category} onChange={e => setNewListing(p => ({ ...p, category: e.target.value }))}
                style={{ padding: '10px 12px', border: '1px solid #ddd', borderRadius: 8, fontSize: 14 }}>
                {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
              <select value={newListing.condition} onChange={e => setNewListing(p => ({ ...p, condition: e.target.value }))}
                style={{ padding: '10px 12px', border: '1px solid #ddd', borderRadius: 8, fontSize: 14 }}>
                {CONDITIONS.map(c => <option key={c} value={c}>{c.replace('_', ' ')}</option>)}
              </select>
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6, color: '#666' }}>Platforms</div>
                <div className="flex flex-wrap gap-2">
                  {PLATFORMS.map(p => (
                    <button key={p} onClick={() => togglePlatform(p)} style={{
                      padding: '6px 12px', borderRadius: 8, fontSize: 12, fontWeight: 500, cursor: 'pointer',
                      background: newListing.platforms.includes(p) ? '#06b6d4' : '#f5f5f5',
                      color: newListing.platforms.includes(p) ? '#fff' : '#666',
                      border: newListing.platforms.includes(p) ? '1px solid #06b6d4' : '1px solid #ddd',
                    }}>
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-3" style={{ marginTop: 20 }}>
              <button onClick={() => setShowCreate(false)} style={{
                padding: '8px 16px', border: '1px solid #ddd', borderRadius: 8,
                background: '#fff', fontSize: 13, cursor: 'pointer',
              }}>Cancel</button>
              <button onClick={handleCreate} disabled={saving || !newListing.title.trim()} style={{
                padding: '8px 16px', border: 'none', borderRadius: 8,
                background: '#06b6d4', color: '#fff', fontSize: 13, fontWeight: 600,
                cursor: 'pointer', opacity: saving ? 0.6 : 1,
              }}>
                {saving ? 'Creating...' : 'Create Listing'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
