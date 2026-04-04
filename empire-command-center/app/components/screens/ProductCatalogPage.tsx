'use client';
import React, { useState, useEffect, useMemo } from 'react';
import { API } from '../../lib/api';
import {
  Search, Package, Layers, ArrowLeft, ExternalLink, Filter,
  Armchair, Frame, Grid3x3, Sofa, Lamp
} from 'lucide-react';

const CAT_ICONS: Record<string, string> = {
  sofa: '🛋️', chair: '💺', ottoman: '🪑', headboard: '🛏️', cushion: '🔲',
  pillow: '🟤', window: '🪟', bedding: '🛌', slipcover: '👘', wall_panel: '🖼️',
  banquette: '🍽️', shelving: '📚', murphy_bed: '🛏️', desk: '🖥️',
  storage_bench: '📦', table: '🪵', millwork: '🔨', commercial: '🏢',
};

const BIZ_COLORS: Record<string, { bg: string; color: string; label: string }> = {
  workroom: { bg: '#fdf8eb', color: '#b8960c', label: 'Workroom' },
  woodcraft: { bg: '#f0fdf4', color: '#16a34a', label: 'WoodCraft' },
};

const READINESS: Record<string, { bg: string; color: string; label: string }> = {
  dedicated: { bg: '#dcfce7', color: '#16a34a', label: '✓ Dedicated' },
  shared_renderer: { bg: '#dbeafe', color: '#2563eb', label: '⚙ Shared' },
  fallback: { bg: '#f3f4f6', color: '#6b7280', label: '↩ Fallback' },
};

interface CatalogCategory {
  key: string; name: string; business_unit: string; style_count: number;
  modes: string[]; styles: { style_key: string; style_name: string; renderer: string; readiness: string; business_unit: string; modes: string[] }[];
}

export default function ProductCatalogPage() {
  const [catalog, setCatalog] = useState<{ categories: CatalogCategory[]; total_styles: number; total_categories: number } | null>(null);
  const [search, setSearch] = useState('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [bizFilter, setBizFilter] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<CatalogCategory | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/drawings/catalog`).then(r => r.json()).then(d => { setCatalog(d); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (search.length >= 2) {
      fetch(`${API}/drawings/catalog/search?q=${encodeURIComponent(search)}`).then(r => r.json()).then(d => setSearchResults(d.results || [])).catch(() => {});
    } else {
      setSearchResults([]);
    }
  }, [search]);

  const filteredCategories = useMemo(() => {
    if (!catalog) return [];
    return catalog.categories.filter(c => bizFilter === 'all' || c.business_unit === bizFilter);
  }, [catalog, bizFilter]);

  if (loading) return <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>Loading product catalog...</div>;
  if (!catalog) return <div style={{ textAlign: 'center', padding: 40, color: '#dc2626' }}>Could not load catalog</div>;

  // Style detail view
  if (selectedCategory) {
    return (
      <div style={{ padding: '20px 24px' }}>
        <button onClick={() => setSelectedCategory(null)} style={{ display: 'flex', alignItems: 'center', gap: 4, background: 'none', border: 'none', cursor: 'pointer', color: '#666', fontSize: 12, marginBottom: 12 }}>
          <ArrowLeft size={14} /> Back to Catalog
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <span style={{ fontSize: 24 }}>{CAT_ICONS[selectedCategory.key] || '📋'}</span>
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>{selectedCategory.name}</h2>
            <p style={{ fontSize: 12, color: '#888', margin: 0 }}>{selectedCategory.style_count} styles · {selectedCategory.business_unit}</p>
          </div>
          <span style={{ padding: '2px 8px', borderRadius: 8, fontSize: 10, fontWeight: 600, ...BIZ_COLORS[selectedCategory.business_unit] }}>{BIZ_COLORS[selectedCategory.business_unit]?.label}</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10 }}>
          {selectedCategory.styles.map(style => {
            const r = READINESS[style.readiness] || READINESS.fallback;
            return (
              <div key={style.style_key} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 14 }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{style.style_name}</div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
                  <span style={{ fontSize: 8, padding: '1px 6px', borderRadius: 4, fontWeight: 600, background: r.bg, color: r.color }}>{r.label}</span>
                  {style.modes.map(m => <span key={m} style={{ fontSize: 8, padding: '1px 5px', borderRadius: 4, background: '#f5f3ef', color: '#888' }}>{m}</span>)}
                </div>
                <button style={{ fontSize: 10, padding: '4px 10px', background: '#b8960c', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600, width: '100%' }}>
                  Draw This
                </button>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // Category grid view
  return (
    <div style={{ padding: '20px 24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Product Catalog</h2>
          <p style={{ fontSize: 12, color: '#888', margin: '2px 0 0' }}>{catalog.total_styles} styles across {catalog.total_categories} categories</p>
        </div>
      </div>

      {/* Search + Filters */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: 9, color: '#999' }} />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search styles... (wingback, roman, murphy, chesterfield)"
            style={{ width: '100%', padding: '7px 8px 7px 30px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12 }} />
        </div>
        {['all', 'workroom', 'woodcraft'].map(f => (
          <button key={f} onClick={() => setBizFilter(f)} style={{
            fontSize: 11, padding: '5px 12px', borderRadius: 8, cursor: 'pointer',
            border: bizFilter === f ? '2px solid #b8960c' : '1px solid #e5e2dc',
            background: bizFilter === f ? '#fdf8eb' : '#fff',
            color: bizFilter === f ? '#b8960c' : '#666', fontWeight: bizFilter === f ? 600 : 400,
          }}>
            {f === 'all' ? 'All' : f === 'workroom' ? 'Empire Workroom' : 'WoodCraft'}
          </button>
        ))}
      </div>

      {/* Search results */}
      {searchResults.length > 0 && (
        <div style={{ marginBottom: 16, background: '#fdf8eb', border: '1px solid #f0e6c0', borderRadius: 10, padding: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#b8960c', marginBottom: 8 }}>{searchResults.length} styles matching "{search}"</div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {searchResults.slice(0, 12).map(r => (
              <span key={`${r.category}-${r.style_key}`} style={{ fontSize: 10, padding: '3px 8px', borderRadius: 6, background: '#fff', border: '1px solid #e5e2dc' }}>
                {r.style_name} <span style={{ color: '#999' }}>({r.category})</span>
              </span>
            ))}
            {searchResults.length > 12 && <span style={{ fontSize: 10, color: '#888' }}>+{searchResults.length - 12} more</span>}
          </div>
        </div>
      )}

      {/* Category Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: 12 }}>
        {filteredCategories.map(cat => {
          const biz = BIZ_COLORS[cat.business_unit] || BIZ_COLORS.workroom;
          return (
            <div key={cat.key} onClick={() => setSelectedCategory(cat)}
              style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 16, cursor: 'pointer', transition: 'border-color 0.15s' }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = '#b8960c')}
              onMouseLeave={e => (e.currentTarget.style.borderColor = '#e5e2dc')}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <span style={{ fontSize: 24 }}>{CAT_ICONS[cat.key] || '📋'}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>{cat.name}</div>
                  <div style={{ fontSize: 11, color: '#888' }}>{cat.style_count} styles</div>
                </div>
                <span style={{ fontSize: 9, fontWeight: 600, padding: '2px 6px', borderRadius: 6, background: biz.bg, color: biz.color }}>{biz.label}</span>
              </div>
              <div style={{ display: 'flex', gap: 4 }}>
                {cat.modes.map(m => <span key={m} style={{ fontSize: 9, padding: '1px 6px', borderRadius: 4, background: '#f5f3ef', color: '#888' }}>{m}</span>)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
