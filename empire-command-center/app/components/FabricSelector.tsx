'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { API } from '../lib/api';
import { Search, X, Plus, ChevronDown, Loader2 } from 'lucide-react';

export interface Fabric {
  id: number;
  code: string;
  name: string;
  color_pattern: string | null;
  material_type: string | null;
  supplier: string | null;
  cost_per_yard: number;
  margin_percent: number;
  width_inches: number;
  pattern_repeat_v: number;
  pattern_repeat_h: number;
  backing_fabric_id: number | null;
  backing?: Fabric | null;
  swatch_photo_path: string | null;
  notes: string | null;
}

interface FabricSelectorProps {
  mode: 'owner' | 'client';
  onSelect: (fabric: Fabric) => void;
  onClose: () => void;
  filterType?: string;
  suggestedBackingId?: number | null;
}

export default function FabricSelector({ mode, onSelect, onClose, filterType, suggestedBackingId }: FabricSelectorProps) {
  const [fabrics, setFabrics] = useState<Fabric[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const API_BASE = API.replace(/\/api\/v1$/, '');

  const fetchFabrics = useCallback(async (q?: string) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (q) params.set('search', q);
      if (filterType) params.set('type', filterType);
      const url = mode === 'client'
        ? `${API}/fabrics/catalog?${params}`
        : `${API}/fabrics?${params}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setFabrics(data);
      }
    } catch {}
    setLoading(false);
  }, [filterType, mode]);

  useEffect(() => {
    fetchFabrics();
    setTimeout(() => searchRef.current?.focus(), 100);
  }, [fetchFabrics]);

  const handleSearch = (val: string) => {
    setSearch(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchFabrics(val), 300);
  };

  const suggested = suggestedBackingId
    ? fabrics.find(f => f.id === suggestedBackingId)
    : null;

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 100,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      {/* Backdrop */}
      <div onClick={onClose} style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.4)' }} />

      {/* Panel */}
      <div style={{
        position: 'relative', width: '100%', maxWidth: 520,
        maxHeight: '85vh', display: 'flex', flexDirection: 'column',
        background: '#fff', borderRadius: 16, boxShadow: '0 12px 40px rgba(0,0,0,0.2)',
        overflow: 'hidden',
      }}
        className="fabric-selector-panel"
      >
        {/* Header */}
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid #ece8e0',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>
              {filterType === 'Backing' ? 'Select Backing Fabric' : 'Select Fabric'}
            </div>
            <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>
              {filterType ? `Showing: ${filterType}` : 'All fabric types'}
            </div>
          </div>
          <button onClick={onClose}
            className="cursor-pointer transition-all hover:bg-[#f5f3ef]"
            style={{ width: 32, height: 32, borderRadius: 8, border: '1px solid #ece8e0', background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <X size={16} className="text-[#999]" />
          </button>
        </div>

        {/* Search */}
        <div style={{ padding: '12px 20px', borderBottom: '1px solid #f0ede8' }}>
          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#bbb' }} />
            <input
              ref={searchRef}
              value={search}
              onChange={e => handleSearch(e.target.value)}
              placeholder="Search by code, name, color, supplier..."
              style={{
                width: '100%', padding: '10px 12px 10px 32px',
                borderRadius: 10, border: '1.5px solid #ece8e0',
                fontSize: 13, outline: 'none',
              }}
            />
          </div>
        </div>

        {/* Suggested backing hint */}
        {suggested && (
          <div style={{
            padding: '8px 20px', background: '#f0fdf4', borderBottom: '1px solid #bbf7d0',
            display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#16a34a',
          }}>
            <span style={{ fontWeight: 600 }}>Suggested:</span>
            <button onClick={() => onSelect(suggested)}
              className="cursor-pointer transition-all hover:bg-[#dcfce7]"
              style={{
                padding: '4px 10px', borderRadius: 6, border: '1px solid #bbf7d0',
                background: '#fff', fontSize: 12, fontWeight: 600, color: '#16a34a',
              }}>
              {suggested.code} {suggested.name} — {suggested.color_pattern}
            </button>
          </div>
        )}

        {/* Fabric list */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '8px 12px' }}>
          {loading && (
            <div style={{ padding: 32, textAlign: 'center', color: '#bbb' }}>
              <Loader2 size={20} className="animate-spin mx-auto" />
              <div style={{ marginTop: 8, fontSize: 12 }}>Loading fabrics...</div>
            </div>
          )}

          {!loading && fabrics.length === 0 && (
            <div style={{ padding: 32, textAlign: 'center', color: '#bbb', fontSize: 13 }}>
              No fabrics found{search ? ` for "${search}"` : ''}
            </div>
          )}

          {!loading && fabrics.map(f => (
            <button key={f.id} onClick={() => onSelect(f)}
              className="cursor-pointer transition-all hover:bg-[#fdf8eb] w-full text-left"
              style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px',
                borderRadius: 10, border: '1px solid transparent', marginBottom: 2,
              }}>
              {/* Swatch / color dot */}
              <div style={{
                width: 48, height: 48, borderRadius: 8, flexShrink: 0,
                border: '1px solid #ece8e0', overflow: 'hidden',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: f.swatch_photo_path ? undefined : '#f5f3ef',
              }}>
                {f.swatch_photo_path ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={`${API_BASE}${f.swatch_photo_path}`} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : (
                  <div style={{
                    width: 28, height: 28, borderRadius: '50%',
                    background: f.color_pattern
                      ? getColorFromName(f.color_pattern)
                      : '#ddd',
                    border: '2px solid #fff', boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
                  }} />
                )}
              </div>

              {/* Info */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                  <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>
                    {f.code}
                  </span>
                  <span style={{ fontSize: 12, color: '#666' }}>
                    {f.name}
                  </span>
                  {f.color_pattern && (
                    <span style={{ fontSize: 11, color: '#999' }}>
                      — {f.color_pattern}
                    </span>
                  )}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 3 }}>
                  {f.material_type && (
                    <span style={{
                      fontSize: 9, fontWeight: 700, textTransform: 'uppercase',
                      padding: '2px 6px', borderRadius: 4,
                      background: f.material_type === 'Backing' ? '#eff6ff' : f.material_type === 'Marine Vinyl' ? '#fef3c7' : '#f0fdf4',
                      color: f.material_type === 'Backing' ? '#2563eb' : f.material_type === 'Marine Vinyl' ? '#d97706' : '#16a34a',
                    }}>
                      {f.material_type}
                    </span>
                  )}
                  {mode === 'owner' && (
                    <span style={{ fontSize: 11, color: f.cost_per_yard > 0 ? '#1a1a1a' : '#bbb' }}>
                      {f.cost_per_yard > 0
                        ? `$${f.cost_per_yard.toFixed(2)}/yd${f.margin_percent > 0 ? ` + ${f.margin_percent}%` : ''}`
                        : '$0.00/yd'}
                    </span>
                  )}
                  {mode === 'owner' && f.supplier && (
                    <span style={{ fontSize: 10, color: '#999' }}>{f.supplier}</span>
                  )}
                </div>
                {f.backing && (
                  <div style={{ fontSize: 10, color: '#7c3aed', marginTop: 2 }}>
                    Linked backing: {f.backing.code} {f.backing.name}
                  </div>
                )}
              </div>
            </button>
          ))}
        </div>

        {/* Add new fabric (owner only) */}
        {mode === 'owner' && (
          <div style={{ borderTop: '1px solid #ece8e0' }}>
            {!showAddForm ? (
              <button onClick={() => setShowAddForm(true)}
                className="cursor-pointer transition-all hover:bg-[#fdf8eb] w-full"
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                  padding: '12px', fontSize: 12, fontWeight: 600, color: '#b8960c',
                  background: '#faf9f7', border: 'none',
                }}>
                <Plus size={14} /> Add New Fabric
              </button>
            ) : (
              <QuickAddForm onSave={(f) => { setShowAddForm(false); fetchFabrics(search); }} onCancel={() => setShowAddForm(false)} />
            )}
          </div>
        )}
      </div>

      <style>{`
        @media (max-width: 500px) {
          .fabric-selector-panel {
            max-width: 100% !important;
            max-height: 100vh !important;
            border-radius: 0 !important;
            height: 100vh;
          }
        }
      `}</style>
    </div>
  );
}

function QuickAddForm({ onSave, onCancel }: { onSave: (f: Fabric) => void; onCancel: () => void }) {
  const [code, setCode] = useState('');
  const [name, setName] = useState('');
  const [color, setColor] = useState('');
  const [type, setType] = useState('Upholstery');
  const [cost, setCost] = useState('');
  const [margin, setMargin] = useState('');
  const [saving, setSaving] = useState(false);

  const save = async () => {
    if (!code || !name) return;
    setSaving(true);
    try {
      const res = await fetch(`${API}/fabrics`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code, name,
          color_pattern: color || null,
          material_type: type,
          cost_per_yard: parseFloat(cost) || 0,
          margin_percent: parseFloat(margin) || 0,
        }),
      });
      if (res.ok) {
        const f = await res.json();
        onSave(f);
      }
    } catch {}
    setSaving(false);
  };

  const inputStyle = {
    width: '100%', padding: '8px 10px', borderRadius: 8,
    border: '1.5px solid #ece8e0', fontSize: 12, outline: 'none',
  };

  return (
    <div style={{ padding: '12px 16px', background: '#faf9f7' }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: '#b8960c', marginBottom: 8 }}>QUICK ADD FABRIC</div>
      <div className="grid grid-cols-2 gap-2">
        <input value={code} onChange={e => setCode(e.target.value)} placeholder="Code (e.g. V639)" style={inputStyle} />
        <input value={name} onChange={e => setName(e.target.value)} placeholder="Name" style={inputStyle} />
        <input value={color} onChange={e => setColor(e.target.value)} placeholder="Color / Pattern" style={inputStyle} />
        <select value={type} onChange={e => setType(e.target.value)} style={inputStyle}>
          <option value="Upholstery">Upholstery</option>
          <option value="Marine Vinyl">Marine Vinyl</option>
          <option value="Backing">Backing</option>
          <option value="Drapery">Drapery</option>
          <option value="Sheer">Sheer</option>
        </select>
        <input value={cost} onChange={e => setCost(e.target.value)} placeholder="Cost/yd ($)" type="number" step="0.01" style={inputStyle} />
        <input value={margin} onChange={e => setMargin(e.target.value)} placeholder="Margin (%)" type="number" style={inputStyle} />
      </div>
      <div className="flex gap-2 mt-3">
        <button onClick={save} disabled={!code || !name || saving}
          className="cursor-pointer transition-all hover:bg-[#b8960c] disabled:opacity-50"
          style={{ flex: 1, padding: '8px', borderRadius: 8, border: 'none', background: '#b8960c', color: '#fff', fontSize: 12, fontWeight: 600 }}>
          {saving ? 'Saving...' : 'Add Fabric'}
        </button>
        <button onClick={onCancel}
          className="cursor-pointer transition-all hover:bg-[#f0ede8]"
          style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #ece8e0', background: '#fff', fontSize: 12, color: '#999' }}>
          Cancel
        </button>
      </div>
    </div>
  );
}

/** Map common color names to approximate hex */
function getColorFromName(name: string): string {
  const n = name.toLowerCase();
  const map: Record<string, string> = {
    spruce: '#4a7c5c', teak: '#b5785a', hazelnut: '#a67b5b',
    neutral: '#c4b99a', fawn: '#c4a76c', umber: '#6b4423',
    black: '#333', white: '#f5f5f5', navy: '#1e3a5f',
    red: '#b33', blue: '#336699', green: '#448844',
    beige: '#d4c5a9', cream: '#fffdd0', ivory: '#fffff0',
    charcoal: '#444', gray: '#888', grey: '#888',
    brown: '#795548', tan: '#d2b48c', gold: '#b8960c',
    burgundy: '#722f37', sage: '#8fa67a', olive: '#708238',
    rust: '#b7410e', taupe: '#8b7d6b', slate: '#708090',
    chocolate: '#5c3d2e', espresso: '#3c2415', mocha: '#5f4536',
  };
  for (const [key, val] of Object.entries(map)) {
    if (n.includes(key)) return val;
  }
  return '#c4b99a';
}
