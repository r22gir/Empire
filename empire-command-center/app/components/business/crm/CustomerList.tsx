'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
  Users, Plus, Upload, AlertCircle, Crown, Search, X,
  ArrowUpDown, Phone, Mail, Building2, Tag, StickyNote,
  ChevronDown, Loader2, MapPin
} from 'lucide-react';
import { API } from '../../../lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface Customer {
  id: string;
  name: string;
  email: string;
  phone: string;
  address: string;
  company: string;
  type: string;
  tags: string[];
  notes: string;
  total_revenue: number;
  lifetime_quotes: number;
  source: string;
  created_at: string;
  updated_at: string;
  business: string;
}

type FilterType = 'all' | 'designer' | 'residential' | 'commercial' | 'contractor';
type SortKey = 'name' | 'revenue' | 'updated' | 'created';

interface CustomerListProps {
  onSelectCustomer?: (id: string) => void;
  business?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function fmt(n: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);
}

/** Strip escaped quotes from QB imports: "\"Name\"" → "Name" */
function cleanName(raw: string): string {
  if (!raw) return '';
  let s = raw.trim();
  // Remove surrounding escaped quotes
  s = s.replace(/^\\?"?|"?\\?$/g, '');
  s = s.replace(/^"|"$/g, '');
  return s.trim();
}

/** Get initials from a name (first letter of first + last word) */
function initials(name: string): string {
  const clean = cleanName(name);
  const parts = clean.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0][0].toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

const TYPE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  designer:    { bg: '#fdf8eb', text: '#b8960c', label: 'Designer' },
  residential: { bg: '#eff6ff', text: '#2563eb', label: 'Residential' },
  commercial:  { bg: '#f0fdf4', text: '#16a34a', label: 'Commercial' },
  contractor:  { bg: '#fffbeb', text: '#d97706', label: 'Contractor' },
};

function typeBadge(type: string) {
  const s = TYPE_STYLES[type?.toLowerCase()] || { bg: '#f3f4f6', text: '#6b7280', label: type || 'Unknown' };
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 10px',
        borderRadius: 999,
        fontSize: 11,
        fontWeight: 700,
        backgroundColor: s.bg,
        color: s.text,
        whiteSpace: 'nowrap',
      }}
    >
      {s.label}
    </span>
  );
}

const AVATAR_COLORS = [
  '#b8960c', '#2563eb', '#16a34a', '#d97706', '#9333ea',
  '#dc2626', '#0891b2', '#6366f1', '#c026d3', '#059669',
];
function avatarColor(id: string): string {
  let hash = 0;
  for (let i = 0; i < id.length; i++) hash = ((hash << 5) - hash + id.charCodeAt(i)) | 0;
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

const FILTERS: { key: FilterType; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'designer', label: 'Designers' },
  { key: 'residential', label: 'Residential' },
  { key: 'commercial', label: 'Commercial' },
  { key: 'contractor', label: 'Contractors' },
];

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: 'name', label: 'Name A-Z' },
  { key: 'revenue', label: 'Revenue High-Low' },
  { key: 'updated', label: 'Last Active' },
  { key: 'created', label: 'Date Added' },
];

// ---------------------------------------------------------------------------
// Add Customer Slide-Out
// ---------------------------------------------------------------------------
function AddCustomerPanel({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [form, setForm] = useState({
    name: '',
    company: '',
    email: '',
    phone: '',
    address: '',
    type: '',
    notes: '',
    tags: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const panelRef = useRef<HTMLDivElement>(null);

  // Auto-detect type from company name
  useEffect(() => {
    if (form.type) return; // don't override manual selection
    const c = form.company.toLowerCase();
    if (c.includes('design') || c.includes('interior')) {
      setForm((f) => ({ ...f, type: 'designer' }));
    }
  }, [form.company, form.type]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        onClose();
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open, onClose]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open, onClose]);

  const reset = () => {
    setForm({ name: '', company: '', email: '', phone: '', address: '', type: '', notes: '', tags: '' });
    setError('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) {
      setError('Name is required');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const body: any = {
        name: form.name.trim(),
        company: form.company.trim(),
        email: form.email.trim(),
        phone: form.phone.trim(),
        address: form.address.trim(),
        type: form.type || 'residential',
        notes: form.notes.trim(),
        tags: form.tags
          .split(',')
          .map((t) => t.trim())
          .filter(Boolean),
      };
      const res = await fetch(`${API}/crm/customers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`Failed to create customer (${res.status})`);
      reset();
      onCreated();
      onClose();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      {/* Backdrop */}
      <div
        style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0,0,0,0.3)',
          zIndex: 998,
          opacity: open ? 1 : 0,
          pointerEvents: open ? 'auto' : 'none',
          transition: 'opacity 0.2s',
        }}
      />
      {/* Panel */}
      <div
        ref={panelRef}
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          bottom: 0,
          width: 420,
          maxWidth: '100vw',
          backgroundColor: '#fff',
          zIndex: 999,
          transform: open ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.25s ease',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '-4px 0 24px rgba(0,0,0,0.08)',
        }}
      >
        {/* Panel header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '20px 24px',
            borderBottom: '1px solid #ece8e0',
          }}
        >
          <h2 style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>
            Add Customer
          </h2>
          <button
            onClick={() => { reset(); onClose(); }}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: 4,
              color: '#888',
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
          }}
        >
          {error && (
            <div
              style={{
                padding: '10px 14px',
                borderRadius: 8,
                backgroundColor: '#fef2f2',
                border: '1px solid #fca5a5',
                color: '#b91c1c',
                fontSize: 13,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <AlertCircle size={14} /> {error}
            </div>
          )}

          <FormField label="Name *" value={form.name} onChange={(v) => setForm({ ...form, name: v })} placeholder="Customer name" />
          <FormField label="Company" value={form.company} onChange={(v) => setForm({ ...form, company: v })} placeholder="Company name" />
          <FormField label="Email" value={form.email} onChange={(v) => setForm({ ...form, email: v })} placeholder="email@example.com" type="email" />
          <FormField label="Phone" value={form.phone} onChange={(v) => setForm({ ...form, phone: v })} placeholder="(555) 123-4567" />
          <FormField label="Address" value={form.address} onChange={(v) => setForm({ ...form, address: v })} placeholder="Full address" />

          {/* Type dropdown */}
          <div>
            <label style={labelStyle}>Type</label>
            <div style={{ position: 'relative' }}>
              <select
                value={form.type}
                onChange={(e) => setForm({ ...form, type: e.target.value })}
                style={{ ...inputStyle, appearance: 'none', paddingRight: 36 }}
              >
                <option value="">Select type...</option>
                <option value="designer">Designer</option>
                <option value="residential">Residential</option>
                <option value="commercial">Commercial</option>
                <option value="contractor">Contractor</option>
              </select>
              <ChevronDown
                size={16}
                style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', color: '#999', pointerEvents: 'none' }}
              />
            </div>
          </div>

          <div>
            <label style={labelStyle}>Notes</label>
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              placeholder="Any notes..."
              rows={3}
              style={{ ...inputStyle, resize: 'vertical', minHeight: 72 }}
            />
          </div>

          <FormField label="Tags" value={form.tags} onChange={(v) => setForm({ ...form, tags: v })} placeholder="designer, vip (comma separated)" />

          <div style={{ flex: 1 }} />

          <button
            type="submit"
            disabled={saving}
            style={{
              height: 48,
              borderRadius: 12,
              border: 'none',
              backgroundColor: '#b8960c',
              color: '#fff',
              fontSize: 14,
              fontWeight: 700,
              cursor: saving ? 'not-allowed' : 'pointer',
              opacity: saving ? 0.6 : 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
              transition: 'opacity 0.15s',
            }}
          >
            {saving ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
            {saving ? 'Saving...' : 'Create Customer'}
          </button>
        </form>
      </div>
    </>
  );
}

// Shared form styles
const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: 12,
  fontWeight: 600,
  color: '#555',
  marginBottom: 6,
};
const inputStyle: React.CSSProperties = {
  width: '100%',
  height: 44,
  borderRadius: 10,
  border: '1px solid #ece8e0',
  padding: '0 14px',
  fontSize: 14,
  color: '#1a1a1a',
  backgroundColor: '#faf9f7',
  outline: 'none',
  boxSizing: 'border-box',
};

function FormField({
  label,
  value,
  onChange,
  placeholder,
  type = 'text',
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <div>
      <label style={labelStyle}>{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={inputStyle}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------
export default function CustomerList({ onSelectCustomer, business }: CustomerListProps) {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [importing, setImporting] = useState(false);
  const [filter, setFilter] = useState<FilterType>('all');
  const [sort, setSort] = useState<SortKey>('name');
  const [showSortMenu, setShowSortMenu] = useState(false);
  const [showAddPanel, setShowAddPanel] = useState(false);

  // -----------------------------------------------------------------------
  // Data fetching
  // -----------------------------------------------------------------------
  const fetchCustomers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = business ? `?business=${business}` : '';
      const res = await fetch(`${API}/crm/customers${params}`);
      if (!res.ok) throw new Error(`Failed to load customers (${res.status})`);
      const data = await res.json();
      setCustomers(Array.isArray(data) ? data : data.customers || data.items || []);
    } catch (err: any) {
      setError(err.message);
      setCustomers([]);
    } finally {
      setLoading(false);
    }
  }, [business]);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  const handleImport = async () => {
    setImporting(true);
    try {
      const res = await fetch(`${API}/crm/customers/import-from-quotes`, { method: 'POST' });
      if (!res.ok) throw new Error(`Import failed (${res.status})`);
      fetchCustomers();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setImporting(false);
    }
  };

  // -----------------------------------------------------------------------
  // Filtering, searching, sorting
  // -----------------------------------------------------------------------
  const processed = useMemo(() => {
    let list = [...customers];

    // Filter by type
    if (filter !== 'all') {
      list = list.filter((c) => c.type?.toLowerCase() === filter);
    }

    // Search
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (c) =>
          cleanName(c.name).toLowerCase().includes(q) ||
          cleanName(c.company || '').toLowerCase().includes(q) ||
          (c.email || '').toLowerCase().includes(q) ||
          (c.phone || '').includes(q)
      );
    }

    // Sort
    list.sort((a, b) => {
      switch (sort) {
        case 'name':
          return cleanName(a.name).localeCompare(cleanName(b.name));
        case 'revenue':
          return (b.total_revenue || 0) - (a.total_revenue || 0);
        case 'updated':
          return new Date(b.updated_at || 0).getTime() - new Date(a.updated_at || 0).getTime();
        case 'created':
          return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime();
        default:
          return 0;
      }
    });

    return list;
  }, [customers, filter, search, sort]);

  // Count by type
  const counts = useMemo(() => {
    const c: Record<string, number> = { all: customers.length };
    for (const cust of customers) {
      const t = cust.type?.toLowerCase() || 'unknown';
      c[t] = (c[t] || 0) + 1;
    }
    return c;
  }, [customers]);

  // Close sort menu on outside click
  const sortRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!showSortMenu) return;
    function handleClick(e: MouseEvent) {
      if (sortRef.current && !sortRef.current.contains(e.target as Node)) {
        setShowSortMenu(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [showSortMenu]);

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------
  return (
    <div style={{ backgroundColor: '#f5f3ef', minHeight: '100vh' }}>
      <div style={{ maxWidth: 960, margin: '0 auto', padding: '28px 36px' }}>
        {/* ---- Header ---- */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 24,
            flexWrap: 'wrap',
            gap: 12,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: 12,
                backgroundColor: '#fdf8eb',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Users size={22} className="text-[#b8960c]" />
            </div>
            <div>
              <h1 style={{ fontSize: 22, fontWeight: 800, color: '#1a1a1a', margin: 0 }}>
                Customers
              </h1>
            </div>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                minWidth: 28,
                height: 24,
                borderRadius: 999,
                backgroundColor: '#b8960c',
                color: '#fff',
                fontSize: 12,
                fontWeight: 700,
                padding: '0 8px',
              }}
            >
              {customers.length}
            </span>
          </div>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button
              onClick={handleImport}
              disabled={importing}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                height: 44,
                padding: '0 18px',
                fontSize: 13,
                fontWeight: 700,
                color: '#555',
                backgroundColor: '#fff',
                border: '1px solid #ece8e0',
                borderRadius: 12,
                cursor: importing ? 'not-allowed' : 'pointer',
                opacity: importing ? 0.6 : 1,
                transition: 'background-color 0.15s',
              }}
              onMouseEnter={(e) => !importing && ((e.currentTarget.style.backgroundColor = '#faf9f7'))}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#fff')}
            >
              {importing ? (
                <Loader2 size={16} className="animate-spin" />
              ) : (
                <Upload size={16} />
              )}
              {importing ? 'Importing...' : 'Import from Quotes'}
            </button>
            <button
              onClick={() => setShowAddPanel(true)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                height: 44,
                padding: '0 20px',
                fontSize: 13,
                fontWeight: 700,
                color: '#fff',
                backgroundColor: '#b8960c',
                border: 'none',
                borderRadius: 12,
                cursor: 'pointer',
                transition: 'background-color 0.15s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#a68500')}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#b8960c')}
            >
              <Plus size={16} /> Add Customer
            </button>
          </div>
        </div>

        {/* ---- Error ---- */}
        {error && (
          <div
            style={{
              marginBottom: 16,
              padding: '12px 16px',
              borderRadius: 10,
              backgroundColor: '#fef2f2',
              border: '1px solid #fca5a5',
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              fontSize: 13,
              color: '#b91c1c',
            }}
          >
            <AlertCircle size={16} /> {error}
          </div>
        )}

        {/* ---- Filter pills ---- */}
        <div
          style={{
            display: 'flex',
            gap: 8,
            marginBottom: 16,
            flexWrap: 'wrap',
          }}
        >
          {FILTERS.map((f) => {
            const active = filter === f.key;
            return (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                style={{
                  height: 36,
                  padding: '0 18px',
                  borderRadius: 999,
                  border: active ? 'none' : '1px solid #ece8e0',
                  backgroundColor: active ? '#b8960c' : '#fff',
                  color: active ? '#fff' : '#555',
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                }}
              >
                {f.label}
                {counts[f.key] != null && (
                  <span
                    style={{
                      fontSize: 11,
                      opacity: active ? 0.85 : 0.6,
                    }}
                  >
                    {counts[f.key] || 0}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* ---- Search + Sort row ---- */}
        <div
          style={{
            display: 'flex',
            gap: 10,
            marginBottom: 20,
            alignItems: 'center',
          }}
        >
          {/* Search */}
          <div
            style={{
              flex: 1,
              maxWidth: 420,
              position: 'relative',
            }}
          >
            <Search
              size={16}
              style={{
                position: 'absolute',
                left: 14,
                top: '50%',
                transform: 'translateY(-50%)',
                color: '#aaa',
                pointerEvents: 'none',
              }}
            />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name, company, email, phone..."
              style={{
                width: '100%',
                height: 44,
                borderRadius: 12,
                border: '1px solid #ece8e0',
                padding: '0 14px 0 40px',
                fontSize: 14,
                color: '#1a1a1a',
                backgroundColor: '#fff',
                outline: 'none',
                boxSizing: 'border-box',
              }}
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                style={{
                  position: 'absolute',
                  right: 10,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: '#aaa',
                  padding: 4,
                  display: 'flex',
                }}
              >
                <X size={14} />
              </button>
            )}
          </div>

          {/* Sort dropdown */}
          <div ref={sortRef} style={{ position: 'relative' }}>
            <button
              onClick={() => setShowSortMenu(!showSortMenu)}
              style={{
                height: 44,
                padding: '0 16px',
                borderRadius: 12,
                border: '1px solid #ece8e0',
                backgroundColor: '#fff',
                color: '#555',
                fontSize: 13,
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                whiteSpace: 'nowrap',
              }}
            >
              <ArrowUpDown size={14} />
              {SORT_OPTIONS.find((s) => s.key === sort)?.label}
              <ChevronDown size={14} />
            </button>
            {showSortMenu && (
              <div
                style={{
                  position: 'absolute',
                  right: 0,
                  top: 50,
                  backgroundColor: '#fff',
                  border: '1px solid #ece8e0',
                  borderRadius: 12,
                  boxShadow: '0 8px 24px rgba(0,0,0,0.08)',
                  zIndex: 50,
                  overflow: 'hidden',
                  minWidth: 180,
                }}
              >
                {SORT_OPTIONS.map((s) => (
                  <button
                    key={s.key}
                    onClick={() => {
                      setSort(s.key);
                      setShowSortMenu(false);
                    }}
                    style={{
                      display: 'block',
                      width: '100%',
                      padding: '10px 16px',
                      border: 'none',
                      backgroundColor: sort === s.key ? '#fdf8eb' : '#fff',
                      color: sort === s.key ? '#b8960c' : '#333',
                      fontSize: 13,
                      fontWeight: sort === s.key ? 700 : 500,
                      textAlign: 'left',
                      cursor: 'pointer',
                    }}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* ---- Results count ---- */}
        <div
          style={{
            fontSize: 13,
            color: '#888',
            marginBottom: 12,
            fontWeight: 500,
          }}
        >
          {loading
            ? 'Loading customers...'
            : `${processed.length} customer${processed.length !== 1 ? 's' : ''}${
                filter !== 'all' || search ? ' found' : ''
              }`}
        </div>

        {/* ---- Customer cards ---- */}
        {loading ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
            }}
          >
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                style={{
                  height: 88,
                  borderRadius: 12,
                  backgroundColor: '#fff',
                  border: '1px solid #ece8e0',
                  animation: 'pulse 1.5s ease-in-out infinite',
                }}
              />
            ))}
            <style>{`@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }`}</style>
          </div>
        ) : processed.length === 0 ? (
          <div
            style={{
              padding: '60px 24px',
              textAlign: 'center',
              backgroundColor: '#fff',
              borderRadius: 12,
              border: '1px solid #ece8e0',
            }}
          >
            <Users size={40} style={{ color: '#ccc', margin: '0 auto 16px' }} />
            <h3 style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a', margin: '0 0 8px' }}>
              {search || filter !== 'all' ? 'No customers match your filters' : 'No customers yet'}
            </h3>
            <p style={{ fontSize: 14, color: '#888', margin: '0 0 20px' }}>
              {search || filter !== 'all'
                ? 'Try a different search term or filter.'
                : 'Add a customer or import from your quotes.'}
            </p>
            {!search && filter === 'all' && (
              <button
                onClick={handleImport}
                disabled={importing}
                style={{
                  height: 44,
                  padding: '0 24px',
                  borderRadius: 12,
                  border: 'none',
                  backgroundColor: '#b8960c',
                  color: '#fff',
                  fontSize: 13,
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <Upload size={16} /> Import from Quotes
              </button>
            )}
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {processed.map((cust) => {
              const name = cleanName(cust.name);
              const company = cleanName(cust.company || '');
              const showCompany = company && company.toLowerCase() !== name.toLowerCase();
              const color = avatarColor(cust.id);

              return (
                <button
                  key={cust.id}
                  onClick={() => onSelectCustomer?.(cust.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 16,
                    padding: 16,
                    backgroundColor: '#fff',
                    border: '1px solid #ece8e0',
                    borderRadius: 12,
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'box-shadow 0.15s, border-color 0.15s',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
                    width: '100%',
                    minHeight: 88,
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.08)';
                    e.currentTarget.style.borderColor = '#d4d0c8';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.04)';
                    e.currentTarget.style.borderColor = '#ece8e0';
                  }}
                >
                  {/* Avatar */}
                  <div
                    style={{
                      width: 48,
                      height: 48,
                      borderRadius: '50%',
                      backgroundColor: color + '18',
                      color: color,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 16,
                      fontWeight: 800,
                      flexShrink: 0,
                      letterSpacing: 0.5,
                    }}
                  >
                    {initials(cust.name)}
                  </div>

                  {/* Info */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        marginBottom: 4,
                        flexWrap: 'wrap',
                      }}
                    >
                      <span
                        style={{
                          fontSize: 15,
                          fontWeight: 700,
                          color: '#1a1a1a',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {name}
                      </span>
                      {(cust.total_revenue || 0) > 10000 && (
                        <Crown size={14} style={{ color: '#b8960c', flexShrink: 0 }} />
                      )}
                      {typeBadge(cust.type)}
                    </div>

                    {showCompany && (
                      <div
                        style={{
                          fontSize: 13,
                          color: '#777',
                          marginBottom: 4,
                          display: 'flex',
                          alignItems: 'center',
                          gap: 4,
                        }}
                      >
                        <Building2 size={12} style={{ flexShrink: 0 }} />
                        <span
                          style={{
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {company}
                        </span>
                      </div>
                    )}

                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 16,
                        fontSize: 13,
                        color: '#888',
                        flexWrap: 'wrap',
                      }}
                    >
                      {cust.phone && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <Phone size={12} /> {cust.phone}
                        </span>
                      )}
                      {cust.email && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <Mail size={12} /> {cust.email}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Revenue */}
                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <div
                      style={{
                        fontSize: 16,
                        fontWeight: 800,
                        color: (cust.total_revenue || 0) > 0 ? '#16a34a' : '#ccc',
                      }}
                    >
                      {fmt(cust.total_revenue || 0)}
                    </div>
                    {(cust.lifetime_quotes || 0) > 0 && (
                      <div style={{ fontSize: 12, color: '#aaa', marginTop: 2 }}>
                        {cust.lifetime_quotes} quote{cust.lifetime_quotes !== 1 ? 's' : ''}
                      </div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* ---- Add Customer Panel ---- */}
      <AddCustomerPanel
        open={showAddPanel}
        onClose={() => setShowAddPanel(false)}
        onCreated={fetchCustomers}
      />
    </div>
  );
}
