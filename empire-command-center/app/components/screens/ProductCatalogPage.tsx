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

const WINDOW_GROUPS: Record<string, { label: string; styles: string[] }> = {
  drapery: { label: '🪟 Drapery (12 pleat styles)', styles: ['pinch_pleat','french_pleat','euro_pleat','goblet','ripplefold','grommet','rod_pocket','tab_top','inverted_box','cartridge','pencil','smocked'] },
  roman: { label: '🏠 Roman Shades (7 styles)', styles: ['flat_roman','hobbled_roman','balloon_roman','austrian','relaxed_roman','london_roman','tulip_roman'] },
  cornice: { label: '🎭 Cornices & Valances (12 styles)', styles: ['straight_cornice','arched_cornice','scalloped_cornice','shaped_cornice','upholstered_cornice','swag_jabot','balloon_valance','box_pleat_valance','kingston_valance','rod_pocket_valance','board_mounted_valance','scarf_swag'] },
};

const MODE_INFO: Record<string, { label: string; desc: string; color: string; bg: string }> = {
  presentation: { label: 'Presentation', desc: 'Client-friendly view — clean visuals, fabric emphasis, minimal technical detail', color: '#2563eb', bg: '#dbeafe' },
  shop: { label: 'Shop Drawing', desc: 'For your fabrication team — exact dimensions, construction notes, material schedule', color: '#d97706', bg: '#fef3c7' },
  construction: { label: 'Construction', desc: 'Builder view — exploded frame, numbered parts, cut list, assembly diagram', color: '#dc2626', bg: '#fef2f2' },
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
  const [drawMode, setDrawMode] = useState('presentation');
  const [subFilter, setSubFilter] = useState<string>('all');

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

  // Navigate to Drawing Studio with pre-selected style
  const handleDrawThis = (style: any) => {
    // Switch parent view back to studio with the item type pre-selected
    // For now, send a MAX chat message to generate the drawing
    const msg = `Draw a ${style.style_name} (${selectedCategory?.name}) in ${drawMode} mode`;
    window.open(`/?screen=chat&autoMessage=${encodeURIComponent(msg)}`, '_self');
  };

  // Style detail view
  if (selectedCategory) {
    const isWindow = selectedCategory.key === 'window';
    const groups = isWindow ? WINDOW_GROUPS : null;

    const getFilteredStyles = () => {
      if (!isWindow || subFilter === 'all') return selectedCategory.styles;
      const groupStyles = groups?.[subFilter]?.styles || [];
      return selectedCategory.styles.filter(s => groupStyles.includes(s.style_key));
    };

    return (
      <div style={{ padding: '20px 24px' }}>
        <button onClick={() => setSelectedCategory(null)} style={{ display: 'flex', alignItems: 'center', gap: 4, background: 'none', border: 'none', cursor: 'pointer', color: '#666', fontSize: 12, marginBottom: 12 }}>
          <ArrowLeft size={14} /> Back to Catalog
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <span style={{ fontSize: 24 }}>{CAT_ICONS[selectedCategory.key] || '📋'}</span>
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>{selectedCategory.name}</h2>
            <p style={{ fontSize: 12, color: '#888', margin: 0 }}>{selectedCategory.style_count} styles · {selectedCategory.business_unit}</p>
          </div>
          <span style={{ padding: '2px 8px', borderRadius: 8, fontSize: 10, fontWeight: 600, ...BIZ_COLORS[selectedCategory.business_unit] }}>{BIZ_COLORS[selectedCategory.business_unit]?.label}</span>
        </div>

        {/* Mode selector with explanations */}
        <div style={{ background: '#faf9f7', borderRadius: 10, padding: 12, marginBottom: 14, border: '1px solid #e5e2dc' }}>
          <div style={{ fontSize: 10, fontWeight: 600, color: '#888', marginBottom: 6, textTransform: 'uppercase' }}>Drawing Mode</div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {selectedCategory.modes.map(m => {
              const info = MODE_INFO[m] || { label: m, desc: '', color: '#888', bg: '#f5f3ef' };
              return (
                <button key={m} onClick={() => setDrawMode(m)} title={info.desc} style={{
                  padding: '6px 12px', borderRadius: 8, fontSize: 11, fontWeight: 600, cursor: 'pointer',
                  background: drawMode === m ? info.bg : '#fff',
                  color: drawMode === m ? info.color : '#999',
                  border: drawMode === m ? `2px solid ${info.color}` : '1px solid #e5e2dc',
                }}>
                  {info.label}
                </button>
              );
            })}
          </div>
          <p style={{ fontSize: 10, color: '#888', margin: '6px 0 0', fontStyle: 'italic' }}>
            {MODE_INFO[drawMode]?.desc || ''}
          </p>
          <div style={{ fontSize: 9, color: '#aaa', marginTop: 8, lineHeight: 1.5 }}>
            ✅ Presentation mode produces professional drawings for all 204 styles.<br />
            ⚙️ Shop mode adds technical dimensions — live for windows & banquettes, expanding to all categories.<br />
            🔧 Construction mode (exploded diagrams, parts lists) is live for banquettes and in development for other WoodCraft items.
          </div>
        </div>

        {/* Sub-category filter for window treatments */}
        {isWindow && groups && (
          <div style={{ display: 'flex', gap: 6, marginBottom: 14, flexWrap: 'wrap' }}>
            <button onClick={() => setSubFilter('all')} style={{
              fontSize: 11, padding: '5px 12px', borderRadius: 8, cursor: 'pointer',
              border: subFilter === 'all' ? '2px solid #b8960c' : '1px solid #e5e2dc',
              background: subFilter === 'all' ? '#fdf8eb' : '#fff',
              color: subFilter === 'all' ? '#b8960c' : '#666', fontWeight: subFilter === 'all' ? 600 : 400,
            }}>All (31)</button>
            {Object.entries(groups).map(([key, group]) => (
              <button key={key} onClick={() => setSubFilter(key)} style={{
                fontSize: 11, padding: '5px 12px', borderRadius: 8, cursor: 'pointer',
                border: subFilter === key ? '2px solid #b8960c' : '1px solid #e5e2dc',
                background: subFilter === key ? '#fdf8eb' : '#fff',
                color: subFilter === key ? '#b8960c' : '#666', fontWeight: subFilter === key ? 600 : 400,
              }}>{group.label}</button>
            ))}
          </div>
        )}

        {/* Style cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 10 }}>
          {getFilteredStyles().map(style => {
            const r = READINESS[style.readiness] || READINESS.fallback;
            return (
              <div key={style.style_key} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 14 }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{style.style_name}</div>
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
                  <span style={{ fontSize: 8, padding: '1px 6px', borderRadius: 4, fontWeight: 600, background: r.bg, color: r.color }}>{r.label}</span>
                  {style.modes.map(m => {
                    const mi = MODE_INFO[m];
                    const modeStatus = (style as any).mode_status?.[m] || 'planned';
                    const isActive = modeStatus === 'active';
                    const tooltip = isActive ? mi?.desc : `In development — currently produces same output as Presentation mode`;
                    return (
                      <span key={m} title={tooltip} style={{
                        fontSize: 8, padding: '1px 5px', borderRadius: 4, cursor: 'help',
                        background: isActive ? (mi?.bg || '#f5f3ef') : 'transparent',
                        color: isActive ? (mi?.color || '#888') : '#bbb',
                        border: isActive ? 'none' : '1px dashed #ddd',
                        fontStyle: isActive ? 'normal' : 'italic',
                      }}>
                        {isActive ? '' : '🔧 '}{mi?.label || m}{!isActive ? ' (planned)' : ''}
                      </span>
                    );
                  })}
                </div>
                {/* Planned mode warning */}
                {(style as any).mode_status?.[drawMode] === 'planned' && (
                  <div style={{ fontSize: 9, color: '#999', fontStyle: 'italic', marginBottom: 6, padding: '4px 6px', background: '#faf9f7', borderRadius: 4 }}>
                    Note: {MODE_INFO[drawMode]?.label} mode for this style uses the shared renderer. Output will look similar to Presentation.
                  </div>
                )}
                <button onClick={() => handleDrawThis(style)} style={{ fontSize: 10, padding: '6px 10px', background: '#b8960c', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600, width: '100%' }}>
                  Draw This ({MODE_INFO[drawMode]?.label || drawMode})
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
