'use client';
import { useState } from 'react';
import { X, Hammer } from 'lucide-react';
import { API } from '../lib/api';

const categories = [
  { value: 'cornice', label: 'Cornice Board' },
  { value: 'valance', label: 'Valance' },
  { value: 'headboard', label: 'Headboard' },
  { value: 'cabinet-door', label: 'Cabinet Door' },
  { value: 'sign', label: 'Sign / Lettering' },
  { value: 'furniture', label: 'Furniture' },
  { value: 'custom', label: 'Custom Project' },
];

const styles = [
  'traditional', 'farmhouse', 'modern', 'art-deco', 'geometric', 'ornate', 'shaker', 'mid-century',
];

const materials = ['MDF', 'Plywood', 'Pine', 'Oak', 'Maple', 'Walnut', 'Cherry', 'Acrylic', 'Foam'];

export default function NewDesignModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void;
}) {
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    customer_name: '',
    customer_email: '',
    customer_phone: '',
    name: '',
    description: '',
    category: 'cornice',
    style: 'traditional',
    width: '',
    height: '',
    depth: '',
    primary_material: 'MDF',
    labor_cost: '',
    notes: '',
  });

  const set = (key: string, val: string) => setForm(f => ({ ...f, [key]: val }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.customer_name || !form.name) return;
    setLoading(true);
    try {
      await fetch(`${API}/designs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...form,
          width: parseFloat(form.width) || undefined,
          height: parseFloat(form.height) || undefined,
          depth: parseFloat(form.depth) || undefined,
          labor_cost: parseFloat(form.labor_cost) || 0,
        }),
      });
      onCreated();
    } catch (_err) {
      alert('Error creating design');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-5 border-b border-[#e5e0d8]">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[#c9a84c] flex items-center justify-center">
              <Hammer size={16} className="text-white" />
            </div>
            <h2 className="text-base font-bold">New CraftForge Design</h2>
          </div>
          <button onClick={onClose} className="text-[#aaa] hover:text-[#1a1a1a]"><X size={18} /></button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {/* Customer */}
          <div>
            <label className="text-[10px] font-bold text-[#777] uppercase tracking-wider">Customer</label>
            <div className="grid grid-cols-2 gap-2 mt-1">
              <input placeholder="Name *" required value={form.customer_name} onChange={e => set('customer_name', e.target.value)} className="col-span-2 text-sm px-3 py-2 border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] focus:ring-1 focus:ring-[#c9a84c]/30 outline-none" />
              <input placeholder="Email" value={form.customer_email} onChange={e => set('customer_email', e.target.value)} className="text-sm px-3 py-2 border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none" />
              <input placeholder="Phone" value={form.customer_phone} onChange={e => set('customer_phone', e.target.value)} className="text-sm px-3 py-2 border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none" />
            </div>
          </div>

          {/* Design */}
          <div>
            <label className="text-[10px] font-bold text-[#777] uppercase tracking-wider">Design</label>
            <div className="space-y-2 mt-1">
              <input placeholder="Design name *" required value={form.name} onChange={e => set('name', e.target.value)} className="w-full text-sm px-3 py-2 border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none" />
              <textarea placeholder="Description / notes" value={form.description} onChange={e => set('description', e.target.value)} rows={2} className="w-full text-sm px-3 py-2 border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none resize-none" />
            </div>
          </div>

          {/* Category, Style, Material */}
          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="text-[10px] font-bold text-[#777] uppercase tracking-wider">Category</label>
              <select value={form.category} onChange={e => set('category', e.target.value)} className="w-full mt-1 text-sm px-3 py-2 border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none">
                {categories.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[10px] font-bold text-[#777] uppercase tracking-wider">Style</label>
              <select value={form.style} onChange={e => set('style', e.target.value)} className="w-full mt-1 text-sm px-3 py-2 border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none">
                {styles.map(s => <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>)}
              </select>
            </div>
            <div>
              <label className="text-[10px] font-bold text-[#777] uppercase tracking-wider">Material</label>
              <select value={form.primary_material} onChange={e => set('primary_material', e.target.value)} className="w-full mt-1 text-sm px-3 py-2 border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none">
                {materials.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
          </div>

          {/* Dimensions */}
          <div>
            <label className="text-[10px] font-bold text-[#777] uppercase tracking-wider">Dimensions (inches)</label>
            <div className="grid grid-cols-3 gap-2 mt-1">
              <input placeholder="Width" type="number" step="0.25" value={form.width} onChange={e => set('width', e.target.value)} className="text-sm px-3 py-2 border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none" />
              <input placeholder="Height" type="number" step="0.25" value={form.height} onChange={e => set('height', e.target.value)} className="text-sm px-3 py-2 border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none" />
              <input placeholder="Depth" type="number" step="0.25" value={form.depth} onChange={e => set('depth', e.target.value)} className="text-sm px-3 py-2 border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none" />
            </div>
          </div>

          {/* Labor cost */}
          <div>
            <label className="text-[10px] font-bold text-[#777] uppercase tracking-wider">Labor Cost ($)</label>
            <input placeholder="0.00" type="number" step="0.01" value={form.labor_cost} onChange={e => set('labor_cost', e.target.value)} className="w-full mt-1 text-sm px-3 py-2 border border-[#e5e0d8] rounded-lg focus:border-[#c9a84c] outline-none" />
          </div>

          {/* Submit */}
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="flex-1 px-4 py-2.5 text-sm text-[#777] border border-[#e5e0d8] rounded-lg hover:bg-[#f5f3ef] transition-colors">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="flex-1 px-4 py-2.5 text-sm font-semibold text-white bg-[#c9a84c] rounded-lg hover:bg-[#b8960c] transition-colors disabled:opacity-50">
              {loading ? 'Creating...' : 'Create Design'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
