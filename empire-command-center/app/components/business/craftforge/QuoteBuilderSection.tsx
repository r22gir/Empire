'use client';
import React, { useState, useEffect, useCallback } from 'react';
import { API } from '../../../lib/api';
import {
  Plus, X, Trash2, Calculator, Send, Loader2, PenTool, FileDown, Mail
} from 'lucide-react';
import DataTable, { Column } from '../shared/DataTable';
import StatusBadge from '../shared/StatusBadge';
import SearchBar from '../shared/SearchBar';
import EmptyState from '../shared/EmptyState';

// ── Types ──
interface MaterialRow {
  name: string;
  quantity: number;
  unit: string;
  cost_per_unit: number;
}

interface CNCJobRow {
  machine: string;
  operation: string;
  tool: string;
  estimated_time_min: number;
}

const CATEGORIES = ['cornice', 'valance', 'cabinet-door', 'sign', 'furniture', 'custom'] as const;
const STYLES = ['farmhouse', 'modern', 'art-deco', 'traditional', 'geometric', 'ornate'] as const;
const MACHINES = ['x-carve', 'elegoo-saturn', 'manual'] as const;
const OPERATIONS = ['profile', 'pocket', 'vcarve', 'engrave', '3d-relief', '3d-print'] as const;
const UNITS = ['in', 'mm', 'cm', 'ft'] as const;
const MATERIAL_UNITS = ['ea', 'sqft', 'bdft', 'lnft', 'ml', 'kg'] as const;

const CNC_RATE = 1.50; // $/min

const emptyMaterial = (): MaterialRow => ({ name: '', quantity: 1, unit: 'ea', cost_per_unit: 0 });
const emptyCNC = (): CNCJobRow => ({ machine: 'x-carve', operation: 'profile', tool: '', estimated_time_min: 0 });

export default function QuoteBuilderSection() {
  const [view, setView] = useState<'list' | 'create'>('list');
  const [designs, setDesigns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Form state
  const [customerName, setCustomerName] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [designName, setDesignName] = useState('');
  const [category, setCategory] = useState<string>('cornice');
  const [style, setStyle] = useState<string>('modern');
  const [width, setWidth] = useState<number>(0);
  const [height, setHeight] = useState<number>(0);
  const [depth, setDepth] = useState<number>(0);
  const [dimUnit, setDimUnit] = useState<string>('in');
  const [materials, setMaterials] = useState<MaterialRow[]>([emptyMaterial()]);
  const [cncJobs, setCncJobs] = useState<CNCJobRow[]>([emptyCNC()]);
  const [laborCost, setLaborCost] = useState<number>(0);
  const [overhead, setOverhead] = useState<number>(0);
  const [margin, setMargin] = useState<number>(40);
  const [depositPct, setDepositPct] = useState<number>(50);
  const [notes, setNotes] = useState('');

  const fetchDesigns = useCallback(() => {
    setLoading(true);
    fetch(`${API}/craftforge/designs`)
      .then(r => r.json())
      .then(data => {
        setDesigns(Array.isArray(data) ? data : data.designs || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => { fetchDesigns(); }, [fetchDesigns]);

  // Auto-calculate costs
  const materialCost = materials.reduce((sum, m) => sum + (m.quantity * m.cost_per_unit), 0);
  const cncTimeCost = cncJobs.reduce((sum, j) => sum + (j.estimated_time_min * CNC_RATE), 0);
  const subtotal = materialCost + cncTimeCost + laborCost + overhead;
  const marginAmount = subtotal * (margin / 100);
  const total = subtotal + marginAmount;
  const deposit = total * (depositPct / 100);

  const resetForm = () => {
    setCustomerName(''); setCustomerEmail(''); setCustomerPhone('');
    setDesignName(''); setCategory('cornice'); setStyle('modern');
    setWidth(0); setHeight(0); setDepth(0); setDimUnit('in');
    setMaterials([emptyMaterial()]); setCncJobs([emptyCNC()]);
    setLaborCost(0); setOverhead(0); setMargin(40); setDepositPct(50); setNotes('');
  };

  const handleSubmit = async () => {
    if (!customerName.trim() || !designName.trim()) return;
    setSubmitting(true);
    try {
      const body = {
        customer_name: customerName,
        customer_email: customerEmail || undefined,
        customer_phone: customerPhone || undefined,
        name: designName,
        category,
        style,
        width: width || undefined,
        height: height || undefined,
        depth: depth || undefined,
        unit: dimUnit,
        materials: materials.filter(m => m.name.trim()).map(m => ({
          ...m,
          type: 'wood',
          total: m.quantity * m.cost_per_unit,
        })),
        cnc_jobs: cncJobs.filter(j => j.estimated_time_min > 0),
        material_cost: materialCost,
        cnc_time_cost: cncTimeCost,
        labor_cost: laborCost,
        overhead,
        subtotal,
        total,
        margin_percent: margin,
        deposit_percent: depositPct,
        notes: notes || undefined,
      };
      const resp = await fetch(`${API}/craftforge/designs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const created = await resp.json();
      resetForm();
      setView('list');
      fetchDesigns();
      // Offer immediate PDF download
      if (created?.id && confirm('Quote saved! Download PDF now?')) {
        handleDownloadPDF(created.id);
      }
    } catch (e) {
      console.error('Failed to create design:', e);
    } finally {
      setSubmitting(false);
    }
  };

  // Material row handlers
  const updateMaterial = (idx: number, field: keyof MaterialRow, value: any) => {
    setMaterials(prev => prev.map((m, i) => i === idx ? { ...m, [field]: value } : m));
  };
  const addMaterial = () => setMaterials(prev => [...prev, emptyMaterial()]);
  const removeMaterial = (idx: number) => setMaterials(prev => prev.filter((_, i) => i !== idx));

  // CNC row handlers
  const updateCNC = (idx: number, field: keyof CNCJobRow, value: any) => {
    setCncJobs(prev => prev.map((j, i) => i === idx ? { ...j, [field]: value } : j));
  };
  const addCNC = () => setCncJobs(prev => [...prev, emptyCNC()]);
  const removeCNC = (idx: number) => setCncJobs(prev => prev.filter((_, i) => i !== idx));

  // PDF download
  const handleDownloadPDF = async (designId: string) => {
    try {
      const resp = await fetch(`${API}/craftforge/designs/${designId}/pdf`, { method: 'POST' });
      if (!resp.ok) throw new Error('PDF generation failed');
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `quote-${designId.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('PDF download failed:', e);
      alert('PDF generation failed — check backend logs');
    }
  };

  // Email quote
  const handleEmailQuote = async (designId: string, email?: string) => {
    const toEmail = email || prompt('Enter customer email:');
    if (!toEmail) return;
    try {
      const resp = await fetch(`${API}/craftforge/designs/${designId}/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ to_email: toEmail }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || 'Send failed');
      }
      alert('Quote sent!');
      fetchDesigns();
    } catch (e: any) {
      console.error('Email failed:', e);
      alert(`Email failed: ${e.message}`);
    }
  };

  // List view
  if (view === 'list') {
    const filtered = designs.filter(d => {
      if (!search) return true;
      const q = search.toLowerCase();
      return (d.name || '').toLowerCase().includes(q) ||
             (d.customer_name || '').toLowerCase().includes(q) ||
             (d.category || '').toLowerCase().includes(q);
    });

    const columns: Column[] = [
      { key: 'design_number', label: '#', sortable: true, render: (row) => <span style={{ fontSize: 12, fontWeight: 700, color: '#b8960c' }}>{row.design_number || '--'}</span> },
      { key: 'name', label: 'Design', sortable: true, render: (row) => <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{row.name || 'Untitled'}</span> },
      { key: 'customer_name', label: 'Customer', sortable: true },
      { key: 'category', label: 'Category', render: (row) => <span className="capitalize">{row.category || '--'}</span> },
      { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status || 'concept'} /> },
      { key: 'total', label: 'Total', sortable: true, render: (row) => <span style={{ fontSize: 12, fontWeight: 700, color: '#b8960c' }}>{row.total != null ? `$${Number(row.total).toFixed(2)}` : '--'}</span> },
      { key: 'created_at', label: 'Created', render: (row) => <span style={{ fontSize: 11, color: '#999' }} suppressHydrationWarning>{row.created_at ? new Date(row.created_at).toLocaleDateString() : '--'}</span> },
      { key: 'actions', label: '', render: (row) => (
        <div className="flex items-center gap-1">
          <button
            onClick={(e) => { e.stopPropagation(); handleDownloadPDF(row.id); }}
            title="Download PDF"
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: '#b8960c' }}
            className="hover:text-[#a68500]"
          >
            <FileDown size={15} />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); handleEmailQuote(row.id, row.customer_email); }}
            title="Email Quote"
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: '#2563eb' }}
            className="hover:text-[#1d4ed8]"
          >
            <Mail size={15} />
          </button>
        </div>
      )},
    ];

    return (
      <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
        <div className="flex items-center justify-between mb-5">
          <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }} className="flex items-center gap-2">
            <PenTool size={20} className="text-[#b8960c]" /> Quote Builder
          </h2>
          <div className="flex items-center gap-3">
            <div className="w-64">
              <SearchBar value={search} onChange={setSearch} placeholder="Search designs..." />
            </div>
            <button
              onClick={() => setView('create')}
              style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '10px 16px', fontSize: 12, fontWeight: 700, color: '#fff', background: '#b8960c', borderRadius: 10, border: 'none', cursor: 'pointer', minHeight: 44 }}
              className="hover:bg-[#a68500] transition-colors"
            >
              <Plus size={14} /> New Design Quote
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={24} className="text-[#b8960c] animate-spin" />
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={<PenTool size={32} />}
            title="No designs found"
            description={search ? 'Try adjusting your search terms.' : 'Create your first design quote to get started.'}
            action={!search ? { label: 'Create Design Quote', onClick: () => setView('create') } : undefined}
          />
        ) : (
          <DataTable columns={columns} data={filtered} />
        )}
      </div>
    );
  }

  // Create form view
  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: '24px 36px' }}>
      <div className="flex items-center justify-between mb-5">
        <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }} className="flex items-center gap-2">
          <Calculator size={20} className="text-[#b8960c]" /> New Design Quote
        </h2>
        <button
          onClick={() => { resetForm(); setView('list'); }}
          style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '8px 12px', fontSize: 12, fontWeight: 600, color: '#777', background: '#fff', borderRadius: 10, border: '1px solid #ece8e0', cursor: 'pointer', minHeight: 44 }}
        >
          <X size={14} /> Cancel
        </button>
      </div>

      {/* Customer Info */}
      <div className="empire-card flat mb-4">
        <div className="section-label mb-3">Customer Information</div>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Name *</label>
            <input className="form-input" value={customerName} onChange={e => setCustomerName(e.target.value)} placeholder="Customer name" />
          </div>
          <div>
            <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Email</label>
            <input className="form-input" type="email" value={customerEmail} onChange={e => setCustomerEmail(e.target.value)} placeholder="email@example.com" />
          </div>
          <div>
            <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Phone</label>
            <input className="form-input" value={customerPhone} onChange={e => setCustomerPhone(e.target.value)} placeholder="(555) 000-0000" />
          </div>
        </div>
      </div>

      {/* Design Info */}
      <div className="empire-card flat mb-4">
        <div className="section-label mb-3">Design Details</div>
        <div className="grid grid-cols-3 gap-3 mb-3">
          <div className="col-span-3">
            <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Design Name *</label>
            <input className="form-input" value={designName} onChange={e => setDesignName(e.target.value)} placeholder="e.g. Custom Cornice - Living Room" />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Category</label>
            <select className="form-input" value={category} onChange={e => setCategory(e.target.value)}>
              {CATEGORIES.map(c => <option key={c} value={c}>{c.replace('-', ' ')}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Style</label>
            <select className="form-input" value={style} onChange={e => setStyle(e.target.value)}>
              {STYLES.map(s => <option key={s} value={s}>{s.replace('-', ' ')}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Dimensions */}
      <div className="empire-card flat mb-4">
        <div className="section-label mb-3">Dimensions</div>
        <div className="grid grid-cols-4 gap-3">
          <div>
            <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Width</label>
            <input className="form-input" type="number" min={0} step={0.25} value={width || ''} onChange={e => setWidth(Number(e.target.value))} placeholder="0" />
          </div>
          <div>
            <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Height</label>
            <input className="form-input" type="number" min={0} step={0.25} value={height || ''} onChange={e => setHeight(Number(e.target.value))} placeholder="0" />
          </div>
          <div>
            <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Depth</label>
            <input className="form-input" type="number" min={0} step={0.25} value={depth || ''} onChange={e => setDepth(Number(e.target.value))} placeholder="0" />
          </div>
          <div>
            <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Unit</label>
            <select className="form-input" value={dimUnit} onChange={e => setDimUnit(e.target.value)}>
              {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Materials */}
      <div className="empire-card flat mb-4">
        <div className="flex items-center justify-between mb-3">
          <div className="section-label">Materials</div>
          <button onClick={addMaterial} className="flex items-center gap-1 text-[11px] font-bold text-[#b8960c] cursor-pointer hover:underline" style={{ background: 'none', border: 'none' }}>
            <Plus size={12} /> Add Row
          </button>
        </div>
        <div className="space-y-2">
          {materials.map((m, i) => (
            <div key={i} className="grid grid-cols-12 gap-2 items-end">
              <div className="col-span-4">
                {i === 0 && <label className="block text-[9px] font-semibold text-[#bbb] uppercase mb-1">Material</label>}
                <input className="form-input" value={m.name} onChange={e => updateMaterial(i, 'name', e.target.value)} placeholder="e.g. 3/4 MDF" />
              </div>
              <div className="col-span-2">
                {i === 0 && <label className="block text-[9px] font-semibold text-[#bbb] uppercase mb-1">Qty</label>}
                <input className="form-input" type="number" min={0} step={0.5} value={m.quantity || ''} onChange={e => updateMaterial(i, 'quantity', Number(e.target.value))} />
              </div>
              <div className="col-span-2">
                {i === 0 && <label className="block text-[9px] font-semibold text-[#bbb] uppercase mb-1">Unit</label>}
                <select className="form-input" value={m.unit} onChange={e => updateMaterial(i, 'unit', e.target.value)}>
                  {MATERIAL_UNITS.map(u => <option key={u} value={u}>{u}</option>)}
                </select>
              </div>
              <div className="col-span-3">
                {i === 0 && <label className="block text-[9px] font-semibold text-[#bbb] uppercase mb-1">$/Unit</label>}
                <input className="form-input" type="number" min={0} step={0.01} value={m.cost_per_unit || ''} onChange={e => updateMaterial(i, 'cost_per_unit', Number(e.target.value))} />
              </div>
              <div className="col-span-1 flex justify-center">
                {materials.length > 1 && (
                  <button onClick={() => removeMaterial(i)} className="text-[#dc2626] hover:text-[#b91c1c] cursor-pointer" style={{ background: 'none', border: 'none', padding: 4 }}>
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
        <div className="text-right mt-2">
          <span style={{ fontSize: 12, fontWeight: 700, color: '#b8960c' }}>Material Total: ${materialCost.toFixed(2)}</span>
        </div>
      </div>

      {/* CNC Jobs */}
      <div className="empire-card flat mb-4">
        <div className="flex items-center justify-between mb-3">
          <div className="section-label">CNC Operations</div>
          <button onClick={addCNC} className="flex items-center gap-1 text-[11px] font-bold text-[#b8960c] cursor-pointer hover:underline" style={{ background: 'none', border: 'none' }}>
            <Plus size={12} /> Add Operation
          </button>
        </div>
        <div className="space-y-2">
          {cncJobs.map((j, i) => (
            <div key={i} className="grid grid-cols-12 gap-2 items-end">
              <div className="col-span-3">
                {i === 0 && <label className="block text-[9px] font-semibold text-[#bbb] uppercase mb-1">Machine</label>}
                <select className="form-input" value={j.machine} onChange={e => updateCNC(i, 'machine', e.target.value)}>
                  {MACHINES.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </div>
              <div className="col-span-3">
                {i === 0 && <label className="block text-[9px] font-semibold text-[#bbb] uppercase mb-1">Operation</label>}
                <select className="form-input" value={j.operation} onChange={e => updateCNC(i, 'operation', e.target.value)}>
                  {OPERATIONS.map(o => <option key={o} value={o}>{o.replace('-', ' ')}</option>)}
                </select>
              </div>
              <div className="col-span-3">
                {i === 0 && <label className="block text-[9px] font-semibold text-[#bbb] uppercase mb-1">Tool</label>}
                <input className="form-input" value={j.tool} onChange={e => updateCNC(i, 'tool', e.target.value)} placeholder='e.g. 1/4" endmill' />
              </div>
              <div className="col-span-2">
                {i === 0 && <label className="block text-[9px] font-semibold text-[#bbb] uppercase mb-1">Time (min)</label>}
                <input className="form-input" type="number" min={0} step={5} value={j.estimated_time_min || ''} onChange={e => updateCNC(i, 'estimated_time_min', Number(e.target.value))} />
              </div>
              <div className="col-span-1 flex justify-center">
                {cncJobs.length > 1 && (
                  <button onClick={() => removeCNC(i)} className="text-[#dc2626] hover:text-[#b91c1c] cursor-pointer" style={{ background: 'none', border: 'none', padding: 4 }}>
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
        <div className="text-right mt-2">
          <span style={{ fontSize: 12, color: '#777' }}>@ ${CNC_RATE.toFixed(2)}/min</span>
          <span style={{ fontSize: 12, fontWeight: 700, color: '#b8960c', marginLeft: 8 }}>CNC Total: ${cncTimeCost.toFixed(2)}</span>
        </div>
      </div>

      {/* Cost Summary */}
      <div className="empire-card flat mb-4">
        <div className="section-label mb-3">Pricing</div>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Labor Cost ($)</label>
            <input className="form-input" type="number" min={0} step={5} value={laborCost || ''} onChange={e => setLaborCost(Number(e.target.value))} placeholder="0.00" />
          </div>
          <div>
            <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Overhead ($)</label>
            <input className="form-input" type="number" min={0} step={5} value={overhead || ''} onChange={e => setOverhead(Number(e.target.value))} placeholder="0.00" />
          </div>
        </div>

        <div className="mb-3">
          <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Margin: {margin}%</label>
          <input type="range" min={0} max={80} step={5} value={margin} onChange={e => setMargin(Number(e.target.value))}
            className="w-full h-2 rounded-lg appearance-none cursor-pointer"
            style={{ accentColor: '#b8960c' }} />
        </div>

        <div className="mb-3">
          <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Deposit: {depositPct}%</label>
          <input type="range" min={0} max={100} step={10} value={depositPct} onChange={e => setDepositPct(Number(e.target.value))}
            className="w-full h-2 rounded-lg appearance-none cursor-pointer"
            style={{ accentColor: '#b8960c' }} />
        </div>

        <div style={{ borderTop: '1px solid #ece8e0', paddingTop: 12 }} className="space-y-1">
          <div className="flex justify-between text-[12px] text-[#777]"><span>Materials</span><span>${materialCost.toFixed(2)}</span></div>
          <div className="flex justify-between text-[12px] text-[#777]"><span>CNC Time</span><span>${cncTimeCost.toFixed(2)}</span></div>
          <div className="flex justify-between text-[12px] text-[#777]"><span>Labor</span><span>${laborCost.toFixed(2)}</span></div>
          <div className="flex justify-between text-[12px] text-[#777]"><span>Overhead</span><span>${overhead.toFixed(2)}</span></div>
          <div className="flex justify-between text-[12px] text-[#777]"><span>Subtotal</span><span>${subtotal.toFixed(2)}</span></div>
          <div className="flex justify-between text-[12px] text-[#777]"><span>Margin ({margin}%)</span><span>${marginAmount.toFixed(2)}</span></div>
          <div className="flex justify-between text-[14px] font-bold text-[#1a1a1a]" style={{ borderTop: '1px solid #ece8e0', paddingTop: 8, marginTop: 4 }}>
            <span>Total</span><span style={{ color: '#b8960c' }}>${total.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-[12px] font-semibold text-[#2563eb]">
            <span>Deposit Due ({depositPct}%)</span><span>${deposit.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* Notes */}
      <div className="empire-card flat mb-4">
        <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Notes</label>
        <textarea className="form-input" rows={3} value={notes} onChange={e => setNotes(e.target.value)} placeholder="Additional notes..." />
      </div>

      {/* Submit */}
      <div className="flex justify-end gap-3">
        <button
          onClick={() => { resetForm(); setView('list'); }}
          style={{ padding: '10px 20px', fontSize: 13, fontWeight: 600, color: '#777', background: '#fff', borderRadius: 10, border: '1px solid #ece8e0', cursor: 'pointer', minHeight: 44 }}
        >
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={submitting || !customerName.trim() || !designName.trim()}
          style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '10px 20px', fontSize: 13, fontWeight: 700,
            color: '#fff', background: (!customerName.trim() || !designName.trim()) ? '#d5d0c8' : '#b8960c',
            borderRadius: 10, border: 'none', cursor: (!customerName.trim() || !designName.trim()) ? 'not-allowed' : 'pointer', minHeight: 44,
          }}
          className="hover:bg-[#a68500] transition-colors"
        >
          {submitting ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
          {submitting ? 'Saving...' : 'Create Design Quote'}
        </button>
      </div>
    </div>
  );
}
