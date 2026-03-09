'use client';

import { useState } from 'react';
import {
  Search, Grid3X3, List as ListIcon, Filter, ChevronDown, Plus,
  Share2, Trash2, Archive, Eye, Heart, ExternalLink, X, Image,
  Tag, Package, Pencil, RotateCw, Sparkles, Upload,
} from 'lucide-react';
import { Listing, ListingStatus, Platform } from '../lib/types';
import { mockListings, PLATFORM_COLORS, CATEGORIES, CONDITIONS } from '../lib/mock-data';

export default function ListingsSection() {
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState('newest');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [detailListing, setDetailListing] = useState<Listing | null>(null);
  const [showNewForm, setShowNewForm] = useState(false);

  const statusTabs = ['all', 'active', 'draft', 'sold', 'archived'];

  const filtered = mockListings
    .filter(l => {
      if (statusFilter !== 'all' && l.status !== statusFilter) return false;
      if (searchQuery && !l.title.toLowerCase().includes(searchQuery.toLowerCase())) return false;
      return true;
    })
    .sort((a, b) => {
      if (sortBy === 'newest') return b.created_at.localeCompare(a.created_at);
      if (sortBy === 'price-high') return b.price - a.price;
      if (sortBy === 'price-low') return a.price - b.price;
      if (sortBy === 'views') return (b.views || 0) - (a.views || 0);
      return 0;
    });

  const toggleSelect = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelected(next);
  };

  const toggleSelectAll = () => {
    if (selected.size === filtered.length) setSelected(new Set());
    else setSelected(new Set(filtered.map(l => l.id)));
  };

  const daysSince = (dateStr: string) => {
    const d = new Date(dateStr);
    const now = new Date('2026-03-09');
    return Math.floor((now.getTime() - d.getTime()) / 86400000);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Listings</h1>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{filtered.length} listings</p>
        </div>
        <button onClick={() => setShowNewForm(true)} className="btn-primary">
          <Plus size={15} /> New Listing
        </button>
      </div>

      {/* Filters Bar */}
      <div className="empire-card !py-3">
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--muted)' }} />
            <input
              type="text"
              placeholder="Search listings..."
              className="form-input pl-9 text-sm"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="flex items-center gap-1">
            {statusTabs.map(s => (
              <button
                key={s}
                className={`filter-tab ${statusFilter === s ? 'active' : ''}`}
                onClick={() => setStatusFilter(s)}
              >
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </button>
            ))}
          </div>

          <select
            className="form-input !w-auto text-sm"
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
          >
            <option value="newest">Newest</option>
            <option value="price-high">Price: High-Low</option>
            <option value="price-low">Price: Low-High</option>
            <option value="views">Most Views</option>
          </select>

          <div className="flex items-center border rounded-lg overflow-hidden" style={{ borderColor: 'var(--border)' }}>
            <button
              className="p-1.5 transition-colors"
              style={{ background: viewMode === 'grid' ? 'var(--gold-light)' : 'transparent' }}
              onClick={() => setViewMode('grid')}
            >
              <Grid3X3 size={16} style={{ color: viewMode === 'grid' ? 'var(--gold)' : 'var(--muted)' }} />
            </button>
            <button
              className="p-1.5 transition-colors"
              style={{ background: viewMode === 'list' ? 'var(--gold-light)' : 'transparent' }}
              onClick={() => setViewMode('list')}
            >
              <ListIcon size={16} style={{ color: viewMode === 'list' ? 'var(--gold)' : 'var(--muted)' }} />
            </button>
          </div>
        </div>
      </div>

      {/* Bulk Actions */}
      {selected.size > 0 && (
        <div className="empire-card !py-2 flex items-center gap-3" style={{ background: 'var(--teal-light, #ecfeff)', borderColor: '#06b6d4' }}>
          <span className="text-sm font-medium" style={{ color: '#06b6d4' }}>{selected.size} selected</span>
          <div className="h-4 w-px bg-cyan-300" />
          <button className="btn-primary text-xs py-1"><Share2 size={13} /> Cross-Post</button>
          <button className="btn-secondary text-xs py-1"><RotateCw size={13} /> Relist</button>
          <button className="btn-secondary text-xs py-1"><Tag size={13} /> Update Price</button>
          <button className="btn-secondary text-xs py-1"><Archive size={13} /> Archive</button>
          <button className="btn-danger text-xs py-1"><Trash2 size={13} /> Delete</button>
          <button className="text-xs ml-auto" style={{ color: 'var(--muted)' }} onClick={() => setSelected(new Set())}>Clear</button>
        </div>
      )}

      {/* Listing Grid */}
      {viewMode === 'grid' ? (
        <div className="grid grid-cols-3 gap-4">
          {filtered.map(listing => (
            <div
              key={listing.id}
              className="empire-card !p-0 overflow-hidden cursor-pointer group"
              onClick={() => setDetailListing(listing)}
            >
              {/* Photo */}
              <div className="h-40 bg-gray-100 flex items-center justify-center relative">
                <Image size={32} style={{ color: 'var(--border)' }} />
                <input
                  type="checkbox"
                  className="absolute top-2 left-2 w-4 h-4 rounded accent-cyan-500"
                  checked={selected.has(listing.id)}
                  onClick={e => e.stopPropagation()}
                  onChange={() => toggleSelect(listing.id)}
                />
                <span className={`status-pill ${listing.status} absolute top-2 right-2`}>
                  {listing.status}
                </span>
              </div>

              {/* Info */}
              <div className="p-3">
                <h3 className="text-sm font-semibold truncate mb-1">{listing.title}</h3>
                <div className="text-lg font-bold mb-2" style={{ color: 'var(--gold)' }}>
                  ${listing.price.toFixed(2)}
                </div>

                <div className="flex items-center gap-1 mb-2">
                  {listing.platforms.map(p => (
                    <div
                      key={p.platform}
                      className={`platform-dot ${p.platform}`}
                      title={`${p.platform}: ${p.status}`}
                    />
                  ))}
                  {listing.platforms.length === 0 && (
                    <span className="text-xs" style={{ color: 'var(--muted)' }}>No platforms</span>
                  )}
                </div>

                <div className="flex items-center justify-between text-xs" style={{ color: 'var(--muted)' }}>
                  <div className="flex items-center gap-2">
                    <span className="flex items-center gap-0.5"><Eye size={11} /> {listing.views || 0}</span>
                    <span className="flex items-center gap-0.5"><Heart size={11} /> {listing.favorites || 0}</span>
                  </div>
                  <span>{daysSince(listing.created_at)}d listed</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empire-card !p-0">
          <table className="empire-table">
            <thead>
              <tr>
                <th className="w-8">
                  <input type="checkbox" className="accent-cyan-500" checked={selected.size === filtered.length && filtered.length > 0} onChange={toggleSelectAll} />
                </th>
                <th>Listing</th>
                <th>Price</th>
                <th>Status</th>
                <th>Platforms</th>
                <th>Views</th>
                <th>Days</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(listing => (
                <tr key={listing.id} className="cursor-pointer" onClick={() => setDetailListing(listing)}>
                  <td onClick={e => e.stopPropagation()}>
                    <input type="checkbox" className="accent-cyan-500" checked={selected.has(listing.id)} onChange={() => toggleSelect(listing.id)} />
                  </td>
                  <td>
                    <div className="font-medium text-sm">{listing.title}</div>
                    <div className="text-xs" style={{ color: 'var(--muted)' }}>{listing.sku} | {listing.category}</div>
                  </td>
                  <td className="font-semibold" style={{ color: 'var(--gold)' }}>${listing.price.toFixed(2)}</td>
                  <td><span className={`status-pill ${listing.status}`}>{listing.status}</span></td>
                  <td>
                    <div className="flex gap-1">
                      {listing.platforms.map(p => (
                        <div key={p.platform} className={`platform-dot ${p.platform}`} title={`${p.platform}: ${p.status}`} />
                      ))}
                    </div>
                  </td>
                  <td className="text-sm">{listing.views || 0}</td>
                  <td className="text-sm">{daysSince(listing.created_at)}d</td>
                  <td onClick={e => e.stopPropagation()}>
                    <div className="flex gap-1">
                      <button className="p-1 rounded hover:bg-gray-100"><Pencil size={14} /></button>
                      <button className="p-1 rounded hover:bg-gray-100"><Share2 size={14} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Detail Modal */}
      {detailListing && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setDetailListing(null)}>
          <div className="bg-white rounded-xl max-w-3xl w-full max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="sticky top-0 bg-white border-b p-4 flex items-center justify-between" style={{ borderColor: 'var(--border)' }}>
              <h2 className="font-bold text-lg">{detailListing.title}</h2>
              <button onClick={() => setDetailListing(null)} className="p-1 rounded hover:bg-gray-100"><X size={20} /></button>
            </div>

            <div className="p-5 space-y-5">
              {/* Photo area */}
              <div className="h-48 bg-gray-100 rounded-lg flex items-center justify-center">
                <Image size={48} style={{ color: 'var(--border)' }} />
              </div>

              {/* Price & Profit */}
              <div className="grid grid-cols-4 gap-3">
                <div className="empire-card !p-3 text-center">
                  <div className="text-xs" style={{ color: 'var(--muted)' }}>List Price</div>
                  <div className="text-xl font-bold" style={{ color: 'var(--gold)' }}>${detailListing.price.toFixed(2)}</div>
                </div>
                <div className="empire-card !p-3 text-center">
                  <div className="text-xs" style={{ color: 'var(--muted)' }}>Cost</div>
                  <div className="text-xl font-bold">${(detailListing.purchase_price || 0).toFixed(2)}</div>
                </div>
                <div className="empire-card !p-3 text-center">
                  <div className="text-xs" style={{ color: 'var(--muted)' }}>Profit (est.)</div>
                  <div className="text-xl font-bold" style={{ color: 'var(--green)' }}>
                    ${(detailListing.price - (detailListing.purchase_price || 0)).toFixed(2)}
                  </div>
                </div>
                <div className="empire-card !p-3 text-center">
                  <div className="text-xs" style={{ color: 'var(--muted)' }}>Margin</div>
                  <div className="text-xl font-bold" style={{ color: 'var(--green)' }}>
                    {detailListing.purchase_price
                      ? Math.round(((detailListing.price - detailListing.purchase_price) / detailListing.price) * 100)
                      : 100}%
                  </div>
                </div>
              </div>

              {/* Details */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="section-label">Details</div>
                  <div className="space-y-1.5 text-sm">
                    <div className="flex justify-between"><span style={{ color: 'var(--muted)' }}>Category</span><span>{detailListing.category}</span></div>
                    <div className="flex justify-between"><span style={{ color: 'var(--muted)' }}>Condition</span><span className="capitalize">{detailListing.condition.replace('_', ' ')}</span></div>
                    <div className="flex justify-between"><span style={{ color: 'var(--muted)' }}>SKU</span><span>{detailListing.sku || '—'}</span></div>
                    <div className="flex justify-between"><span style={{ color: 'var(--muted)' }}>Quantity</span><span>{detailListing.quantity}</span></div>
                    <div className="flex justify-between"><span style={{ color: 'var(--muted)' }}>Weight</span><span>{detailListing.weight_oz ? `${detailListing.weight_oz} oz` : '—'}</span></div>
                    <div className="flex justify-between"><span style={{ color: 'var(--muted)' }}>Status</span><span className={`status-pill ${detailListing.status}`}>{detailListing.status}</span></div>
                  </div>
                </div>
                <div>
                  <div className="section-label">Description</div>
                  <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{detailListing.description}</p>
                </div>
              </div>

              {/* Tags */}
              {detailListing.tags.length > 0 && (
                <div>
                  <div className="section-label">Tags</div>
                  <div className="flex flex-wrap gap-1.5">
                    {detailListing.tags.map(t => (
                      <span key={t} className="text-xs px-2 py-0.5 rounded-full" style={{ background: 'var(--gold-light)', color: 'var(--gold)' }}>
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Platform Status */}
              <div>
                <div className="section-label mb-2">Platform Status</div>
                {detailListing.platforms.length > 0 ? (
                  <table className="empire-table text-sm">
                    <thead>
                      <tr><th>Platform</th><th>Status</th><th>Price</th><th>Listed</th><th>Link</th></tr>
                    </thead>
                    <tbody>
                      {detailListing.platforms.map(p => (
                        <tr key={p.platform}>
                          <td className="capitalize font-medium" style={{ color: PLATFORM_COLORS[p.platform] }}>{p.platform}</td>
                          <td><span className={`status-pill ${p.status}`}>{p.status}</span></td>
                          <td>{p.price ? `$${p.price.toFixed(2)}` : '—'}</td>
                          <td>{p.listed_at || '—'}</td>
                          <td>{p.url ? <a href={p.url} className="text-cyan-600 hover:underline flex items-center gap-1"><ExternalLink size={12} />View</a> : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <p className="text-sm" style={{ color: 'var(--muted)' }}>Not listed on any platform yet</p>
                )}
              </div>

              {/* Actions */}
              <div className="flex gap-2 pt-2 border-t" style={{ borderColor: 'var(--border)' }}>
                <button className="btn-secondary"><Pencil size={14} /> Edit</button>
                <button className="btn-primary"><Share2 size={14} /> Cross-Post</button>
                <button className="btn-gold"><RotateCw size={14} /> Relist</button>
                <button className="btn-secondary"><Archive size={14} /> Archive</button>
                <button className="btn-danger ml-auto"><Trash2 size={14} /> Delete</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* New Listing Modal */}
      {showNewForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setShowNewForm(false)}>
          <div className="bg-white rounded-xl max-w-2xl w-full max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="sticky top-0 bg-white border-b p-4 flex items-center justify-between" style={{ borderColor: 'var(--border)' }}>
              <h2 className="font-bold text-lg">New Listing</h2>
              <button onClick={() => setShowNewForm(false)} className="p-1 rounded hover:bg-gray-100"><X size={20} /></button>
            </div>

            <div className="p-5 space-y-4">
              <div>
                <label className="section-label">Title</label>
                <div className="flex gap-2">
                  <input type="text" className="form-input" placeholder="Item title..." />
                  <button className="btn-secondary whitespace-nowrap text-sm"><Sparkles size={14} /> AI Describe</button>
                </div>
              </div>

              <div>
                <label className="section-label">Description</label>
                <textarea className="form-input" rows={4} placeholder="Detailed description..." />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="section-label">Price ($)</label>
                  <input type="number" className="form-input" placeholder="0.00" />
                </div>
                <div>
                  <label className="section-label">Purchase Price ($)</label>
                  <input type="number" className="form-input" placeholder="0.00" />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="section-label">Category</label>
                  <select className="form-input">
                    <option value="">Select category...</option>
                    {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
                <div>
                  <label className="section-label">Condition</label>
                  <select className="form-input">
                    <option value="">Select condition...</option>
                    {CONDITIONS.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                  </select>
                </div>
              </div>

              <div>
                <label className="section-label">Photos</label>
                <div className="border-2 border-dashed rounded-lg p-8 text-center" style={{ borderColor: 'var(--border)' }}>
                  <Upload size={24} className="mx-auto mb-2" style={{ color: 'var(--muted)' }} />
                  <p className="text-sm" style={{ color: 'var(--muted)' }}>Drag and drop photos or click to browse</p>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="section-label">SKU</label>
                  <input type="text" className="form-input" placeholder="Auto-generated" />
                </div>
                <div>
                  <label className="section-label">Quantity</label>
                  <input type="number" className="form-input" defaultValue={1} />
                </div>
                <div>
                  <label className="section-label">Weight (oz)</label>
                  <input type="number" className="form-input" placeholder="0" />
                </div>
              </div>

              <div>
                <label className="section-label">Tags</label>
                <input type="text" className="form-input" placeholder="Comma separated tags..." />
              </div>

              <div>
                <label className="section-label">Target Platforms</label>
                <div className="flex flex-wrap gap-2 mt-1">
                  {['ebay', 'etsy', 'shopify', 'facebook', 'mercari', 'poshmark', 'amazon', 'depop'].map(p => (
                    <label key={p} className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border cursor-pointer hover:bg-gray-50" style={{ borderColor: 'var(--border)' }}>
                      <input type="checkbox" className="accent-cyan-500" />
                      <div className={`platform-dot ${p}`} />
                      <span className="capitalize">{p}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex gap-2 pt-3 border-t" style={{ borderColor: 'var(--border)' }}>
                <button className="btn-secondary flex-1 justify-center"><Package size={14} /> Save as Draft</button>
                <button className="btn-primary flex-1 justify-center"><Share2 size={14} /> List Now</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
