'use client';
import React, { useState, useEffect, useCallback } from 'react';
import { API } from '../../../lib/api';
import {
  Ruler, Plus, Search, Circle, Square, Minimize2, Download,
  Copy, Pencil, Trash2, X, Save, Loader2, ChevronLeft,
} from 'lucide-react';
import PatternTemplateGenerator from '../../tools/PatternTemplateGenerator';
import CustomShapeBuilder from '../../tools/CustomShapeBuilder';

/* ── Types ───────────────────────────────────────────────────── */
interface PatternPiece {
  name: string;
  width: number;
  height: number;
  quantity: number;
  notes?: string;
  svg?: string;
}

interface PatternResult {
  pieces: PatternPiece[];
  construction_notes: string[];
  fabric_yardage_54: number;
  summary?: string;
}

interface SavedTemplate {
  id: string;
  name: string;
  shape_type: string;
  dimensions: Record<string, any>;
  result: PatternResult;
  customer_id?: string;
  job_id?: string;
  quote_id?: string;
  notes?: string;
  created_at: string;
  updated_at?: string;
}

/* ── Shape Icons ────────────────────────────────────────────── */
// Cylinder icon as inline SVG component since lucide doesn't export one
const CylinderIcon = ({ className, style }: { className?: string; style?: React.CSSProperties }) => (
  <svg className={className} style={style} width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <ellipse cx="12" cy="5" rx="9" ry="3" />
    <path d="M3 5v14a9 3 0 0 0 18 0V5" />
    <ellipse cx="12" cy="19" rx="9" ry="3" />
  </svg>
);

const SHAPE_ICONS: Record<string, { icon: any; label: string; color: string }> = {
  sphere: { icon: Circle, label: 'Sphere', color: '#2563eb' },
  cylinder: { icon: CylinderIcon, label: 'Cylinder', color: '#d97706' },
  box_cushion: { icon: Square, label: 'Box Cushion', color: '#16a34a' },
  knife_edge: { icon: Minimize2, label: 'Knife Edge', color: '#7c3aed' },
};

/* ── Helpers ─────────────────────────────────────────────────── */
function timeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = now - then;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  return `${months}mo ago`;
}

function dimensionSummary(t: SavedTemplate): string {
  const p = t.dimensions || {};
  switch (t.shape_type) {
    case 'sphere':
      return `${p.diameter || '?'}" dia, ${p.num_gores || '?'} gores`;
    case 'cylinder':
      return `${p.diameter || '?'}" dia x ${p.length || '?'}" long`;
    case 'box_cushion':
      return `${p.width || '?'}" x ${p.depth || '?'}" x ${p.thickness || '?'}"`;
    case 'knife_edge':
      return `${p.width || '?'}" x ${p.height || '?'}"`;
    default:
      return '';
  }
}

/* ── Component ───────────────────────────────────────────────── */
export default function TemplateModule() {
  const [templates, setTemplates] = useState<SavedTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [shapeFilter, setShapeFilter] = useState('');
  const [showGenerator, setShowGenerator] = useState(false);
  const [showShapeBuilder, setShowShapeBuilder] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<SavedTemplate | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Edit form state for detail panel
  const [editName, setEditName] = useState('');
  const [editCustomer, setEditCustomer] = useState('');
  const [editJob, setEditJob] = useState('');
  const [editQuote, setEditQuote] = useState('');
  const [editNotes, setEditNotes] = useState('');

  /* ── Fetch templates ───────────────────────────────────────── */
  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      if (shapeFilter) params.set('shape_type', shapeFilter);
      const qs = params.toString();
      const res = await fetch(`${API}/patterns/saved${qs ? `?${qs}` : ''}`);
      if (!res.ok) throw new Error(`API ${res.status}`);
      const data = await res.json();
      setTemplates(Array.isArray(data) ? data : data.templates || data.items || []);
    } catch (e: any) {
      setError(e.message || 'Failed to load templates');
      setTemplates([]);
    } finally {
      setLoading(false);
    }
  }, [search, shapeFilter]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  /* ── Actions ────────────────────────────────────────────────── */
  const handleDelete = useCallback(async (id: string) => {
    if (!confirm('Delete this template?')) return;
    try {
      const res = await fetch(`${API}/patterns/saved/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`Delete failed (${res.status})`);
      setTemplates((prev) => prev.filter((t) => t.id !== id));
      if (selectedTemplate?.id === id) setSelectedTemplate(null);
    } catch (e: any) {
      alert(e.message || 'Delete failed');
    }
  }, [selectedTemplate]);

  const handleDuplicate = useCallback(async (id: string) => {
    try {
      const res = await fetch(`${API}/patterns/saved/${id}/duplicate`, { method: 'POST' });
      if (!res.ok) throw new Error(`Duplicate failed (${res.status})`);
      fetchTemplates();
    } catch (e: any) {
      alert(e.message || 'Duplicate failed');
    }
  }, [fetchTemplates]);

  const handleDownloadPdf = useCallback((id: string) => {
    window.open(`${API}/patterns/saved/${id}/pdf`, '_blank');
  }, []);

  const handleSaveEdit = useCallback(async () => {
    if (!selectedTemplate) return;
    setSaving(true);
    try {
      const res = await fetch(`${API}/patterns/saved/${selectedTemplate.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: editName,
          customer_id: editCustomer,
          job_id: editJob,
          quote_id: editQuote,
          notes: editNotes,
        }),
      });
      if (!res.ok) throw new Error(`Save failed (${res.status})`);
      const updated = await res.json();
      setTemplates((prev) => prev.map((t) => (t.id === selectedTemplate.id ? { ...t, ...updated } : t)));
      setSelectedTemplate((prev) => prev ? { ...prev, ...updated } : null);
    } catch (e: any) {
      alert(e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  }, [selectedTemplate, editName, editCustomer, editJob, editQuote, editNotes]);

  // Called when PatternTemplateGenerator result should be saved
  const handleSaveFromGenerator = useCallback(async (shape: string, params: Record<string, any>, _result: PatternResult, projectName: string) => {
    setSaving(true);
    try {
      const res = await fetch(`${API}/patterns/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: projectName || `${SHAPE_ICONS[shape]?.label || shape} - ${new Date().toLocaleDateString()}`,
          shape_type: shape,
          dimensions: params,
        }),
      });
      if (!res.ok) throw new Error(`Save failed (${res.status})`);
      setShowGenerator(false);
      fetchTemplates();
    } catch (e: any) {
      alert(e.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  }, [fetchTemplates]);

  /* ── Open detail panel ──────────────────────────────────────── */
  const openDetail = useCallback((t: SavedTemplate) => {
    setSelectedTemplate(t);
    setEditName(t.name || '');
    setEditCustomer(t.customer_id || '');
    setEditJob(t.job_id || '');
    setEditQuote(t.quote_id || '');
    setEditNotes(t.notes || '');
  }, []);

  /* ── Filter templates ───────────────────────────────────────── */
  const filtered = templates;

  /* ── Render: Generator Panel ────────────────────────────────── */
  if (showGenerator) {
    return (
      <div className="flex-1 overflow-y-auto" style={{ background: '#faf9f7' }}>
        <div className="p-4 sm:p-6">
          <div className="flex items-center gap-3 mb-4">
            <button
              onClick={() => setShowGenerator(false)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-[#e8e4dc] bg-white
                         hover:bg-gray-50 text-sm font-medium text-[#2D2A26] transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              Back to Templates
            </button>
            {saving && (
              <span className="flex items-center gap-1 text-sm text-[#666]">
                <Loader2 className="w-4 h-4 animate-spin" /> Saving...
              </span>
            )}
          </div>
          <PatternTemplateGenerator
            onSave={handleSaveFromGenerator}
          />
        </div>
      </div>
    );
  }

  /* ── Render: Custom Shape Builder ──────────────────────────── */
  if (showShapeBuilder) {
    return (
      <div className="flex-1 overflow-y-auto" style={{ background: '#faf9f7' }}>
        <div className="p-4 sm:p-6">
          <div className="flex items-center gap-3 mb-4">
            <button
              onClick={() => setShowShapeBuilder(false)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-[#e8e4dc] bg-white
                         hover:bg-gray-50 text-sm font-medium text-[#2D2A26] transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              Back to Templates
            </button>
          </div>
          <CustomShapeBuilder
            onSave={(shapeType, dims, result) => {
              handleSaveFromGenerator(shapeType, dims, result, `Custom ${shapeType.replace(/_/g, ' ')}`);
              setShowShapeBuilder(false);
            }}
          />
        </div>
      </div>
    );
  }

  /* ── Render: Detail / Edit Panel ────────────────────────────── */
  if (selectedTemplate) {
    const shapeInfo = SHAPE_ICONS[selectedTemplate.shape_type] || { icon: Circle, label: selectedTemplate.shape_type, color: '#666' };
    const ShapeIcon = shapeInfo.icon;
    const result = selectedTemplate.result;

    return (
      <div className="flex-1 overflow-y-auto" style={{ background: '#faf9f7' }}>
        <div className="p-4 sm:p-6 max-w-4xl mx-auto">
          {/* Header — responsive */}
          <div className="mb-6">
            <div className="flex items-center gap-3 mb-3">
              <button
                onClick={() => setSelectedTemplate(null)}
                className="flex items-center gap-2 px-3 py-2 min-h-[44px] rounded-xl border border-[#e8e4dc] bg-white
                           hover:bg-gray-50 text-sm font-medium text-[#2D2A26] transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                Back
              </button>
              <div className="flex-1 min-w-0">
                <h2 className="text-lg sm:text-xl font-bold text-[#2D2A26] truncate">{selectedTemplate.name}</h2>
                <div className="flex items-center gap-2 mt-1">
                  <ShapeIcon className="w-4 h-4 shrink-0" style={{ color: shapeInfo.color }} />
                  <span className="text-sm text-[#666] truncate">{shapeInfo.label} — {dimensionSummary(selectedTemplate)}</span>
                </div>
              </div>
            </div>
            <div className="flex flex-col sm:flex-row gap-2">
              <button
                onClick={() => handleDownloadPdf(selectedTemplate.id)}
                className="flex items-center justify-center gap-2 px-4 py-3 sm:py-2 rounded-xl bg-[#16a34a] text-white
                           font-medium text-sm hover:bg-[#15803d] transition-colors min-h-[44px]"
              >
                <Download className="w-4 h-4" />
                Download PDF
              </button>
              <button
                onClick={() => { handleDuplicate(selectedTemplate.id); setSelectedTemplate(null); }}
                className="flex items-center justify-center gap-2 px-4 py-3 sm:py-2 rounded-xl border border-[#e8e4dc] bg-white
                           hover:bg-gray-50 text-sm font-medium text-[#2D2A26] transition-colors min-h-[44px]"
              >
                <Copy className="w-4 h-4" />
                Duplicate & Modify
              </button>
            </div>
          </div>

          {/* Edit Fields */}
          <div className="bg-white rounded-xl border border-[#e8e4dc] p-5 mb-6">
            <h3 className="text-sm font-semibold text-[#2D2A26] mb-4">Template Details</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-[#666] mb-1">Template Name</label>
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-[#e8e4dc] focus:border-[#16a34a]
                             focus:ring-1 focus:ring-[#16a34a] outline-none text-sm transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#666] mb-1">Customer</label>
                <input
                  type="text"
                  value={editCustomer}
                  onChange={(e) => setEditCustomer(e.target.value)}
                  placeholder="Customer name..."
                  className="w-full px-3 py-2 rounded-xl border border-[#e8e4dc] focus:border-[#16a34a]
                             focus:ring-1 focus:ring-[#16a34a] outline-none text-sm transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#666] mb-1">Job #</label>
                <input
                  type="text"
                  value={editJob}
                  onChange={(e) => setEditJob(e.target.value)}
                  placeholder="Job number..."
                  className="w-full px-3 py-2 rounded-xl border border-[#e8e4dc] focus:border-[#16a34a]
                             focus:ring-1 focus:ring-[#16a34a] outline-none text-sm transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#666] mb-1">Quote #</label>
                <input
                  type="text"
                  value={editQuote}
                  onChange={(e) => setEditQuote(e.target.value)}
                  placeholder="Quote reference..."
                  className="w-full px-3 py-2 rounded-xl border border-[#e8e4dc] focus:border-[#16a34a]
                             focus:ring-1 focus:ring-[#16a34a] outline-none text-sm transition-colors"
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-[#666] mb-1">Notes</label>
                <textarea
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  rows={3}
                  placeholder="Additional notes..."
                  className="w-full px-3 py-2 rounded-xl border border-[#e8e4dc] focus:border-[#16a34a]
                             focus:ring-1 focus:ring-[#16a34a] outline-none text-sm transition-colors resize-none"
                />
              </div>
            </div>
            <div className="flex justify-end mt-4">
              <button
                onClick={handleSaveEdit}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#16a34a] text-white
                           font-medium text-sm hover:bg-[#15803d] transition-colors disabled:opacity-50"
              >
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>

          {/* Pattern Pieces */}
          {result && (
            <>
              <div className="bg-white rounded-xl border border-[#e8e4dc] p-5 mb-6">
                <h3 className="text-sm font-semibold text-[#2D2A26] mb-4">Pattern Pieces</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                  {result.pieces.map((piece, i) => (
                    <div key={i} className="border border-[#e8e4dc] rounded-xl p-3 text-center">
                      <div className="text-sm font-semibold text-[#2D2A26] mb-1">{piece.name}</div>
                      <div className="text-xs text-[#666] mb-2">
                        {piece.width}" x {piece.height}" &middot; Cut {piece.quantity}
                      </div>
                      {piece.svg ? (
                        <div
                          className="flex items-center justify-center min-h-[100px]"
                          dangerouslySetInnerHTML={{ __html: piece.svg }}
                        />
                      ) : (
                        <div className="flex items-center justify-center min-h-[100px] text-[#999] text-xs">
                          No preview
                        </div>
                      )}
                      {piece.notes && (
                        <div className="text-xs text-[#999] mt-2 italic">{piece.notes}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Construction Notes */}
              {result.construction_notes?.length > 0 && (
                <div className="bg-white rounded-xl border border-[#e8e4dc] p-5 mb-6">
                  <h3 className="text-sm font-semibold text-[#2D2A26] mb-3">Construction Notes</h3>
                  <ul className="space-y-1.5">
                    {result.construction_notes.map((note, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-[#2D2A26]">
                        <span className="text-[#16a34a] mt-0.5">&#8226;</span>
                        <span>{note}</span>
                      </li>
                    ))}
                  </ul>
                  <div className="pt-3 mt-3 border-t border-[#e8e4dc]">
                    <span className="text-sm font-semibold text-[#2D2A26]">Fabric: </span>
                    <span className="text-lg font-bold text-[#16a34a]">
                      {result.fabric_yardage_54.toFixed(2)} yards
                    </span>
                    <span className="text-sm text-[#666] ml-1">(54" wide)</span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    );
  }

  /* ── Render: Main List View ─────────────────────────────────── */
  return (
    <div className="flex-1 overflow-y-auto" style={{ background: '#faf9f7' }}>
      <div className="p-4 sm:p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-3">
            <Ruler className="w-6 h-6 text-[#16a34a]" />
            <h1 className="text-xl sm:text-2xl font-bold text-[#2D2A26]">Pattern Templates</h1>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowShapeBuilder(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl border border-[#b8960c] text-[#b8960c]
                         font-medium text-sm hover:bg-[#fdf8eb] transition-colors"
            >
              <Square className="w-4 h-4" />
              Custom Shape
            </button>
            <button
              onClick={() => setShowGenerator(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#16a34a] text-white
                         font-medium text-sm hover:bg-[#15803d] transition-colors"
            >
              <Plus className="w-4 h-4" />
              New Template
            </button>
          </div>
        </div>

        {/* Search + Filter Bar */}
        <div className="flex flex-col sm:flex-row gap-3 mb-5">
          <div className="flex-1 relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#999]" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search templates..."
              className="w-full pl-9 pr-3 py-2 rounded-xl border border-[#e8e4dc] bg-white
                         focus:border-[#16a34a] focus:ring-1 focus:ring-[#16a34a] outline-none
                         text-sm transition-colors"
            />
          </div>
          <select
            value={shapeFilter}
            onChange={(e) => setShapeFilter(e.target.value)}
            className="px-3 py-2 rounded-xl border border-[#e8e4dc] bg-white text-sm
                       focus:border-[#16a34a] focus:ring-1 focus:ring-[#16a34a] outline-none
                       transition-colors"
          >
            <option value="">All Shapes</option>
            <option value="sphere">Sphere</option>
            <option value="cylinder">Cylinder</option>
            <option value="box_cushion">Box Cushion</option>
            <option value="knife_edge">Knife Edge</option>
          </select>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-5 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-6 h-6 text-[#16a34a] animate-spin" />
          </div>
        )}

        {/* Empty State */}
        {!loading && filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Ruler className="w-16 h-16 text-[#ccc] mb-4" />
            <p className="text-lg font-medium text-[#2D2A26] mb-2">No pattern templates yet</p>
            <p className="text-sm text-[#666] mb-6">
              Click &quot;+ New Template&quot; to create your first one.
            </p>
            <button
              onClick={() => setShowGenerator(true)}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#16a34a] text-white
                         font-medium text-sm hover:bg-[#15803d] transition-colors"
            >
              <Plus className="w-4 h-4" />
              New Template
            </button>
          </div>
        )}

        {/* Template Cards Grid */}
        {!loading && filtered.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filtered.map((template) => {
              const shapeInfo = SHAPE_ICONS[template.shape_type] || { icon: Circle, label: template.shape_type, color: '#666' };
              const ShapeIcon = shapeInfo.icon;
              const firstPiece = template.result?.pieces?.[0];

              return (
                <div
                  key={template.id}
                  className="bg-white rounded-xl border border-[#e8e4dc] shadow-sm hover:shadow-md
                             transition-all cursor-pointer group"
                  onClick={() => openDetail(template)}
                >
                  {/* SVG Thumbnail */}
                  <div className="border-b border-[#e8e4dc] rounded-t-xl bg-[#faf9f7] flex items-center justify-center min-h-[120px] p-3 overflow-hidden">
                    {firstPiece?.svg ? (
                      <div
                        className="max-w-full max-h-[100px] flex items-center justify-center [&_svg]:max-w-full [&_svg]:max-h-[100px]"
                        dangerouslySetInnerHTML={{ __html: firstPiece.svg }}
                      />
                    ) : (
                      <Ruler className="w-10 h-10 text-[#ddd]" />
                    )}
                  </div>

                  {/* Card Body */}
                  <div className="p-4">
                    <div className="flex items-start gap-2 mb-2">
                      <ShapeIcon className="w-4 h-4 mt-0.5 flex-shrink-0" style={{ color: shapeInfo.color }} />
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold text-sm text-[#2D2A26] truncate">{template.name}</div>
                        <div className="text-xs text-[#666] mt-0.5">{shapeInfo.label}</div>
                      </div>
                    </div>

                    <div className="text-xs text-[#999] mb-2">{dimensionSummary(template)}</div>

                    {template.customer_id && (
                      <div className="text-xs text-[#666] truncate mb-0.5">{template.customer_id}</div>
                    )}
                    {template.job_id && (
                      <div className="text-xs text-[#999] truncate mb-0.5">Job #{template.job_id}</div>
                    )}

                    <div className="text-xs text-[#bbb] mt-2">{timeAgo(template.created_at)}</div>

                    {/* Action Buttons — 44px min tap targets for mobile */}
                    <div className="flex items-center gap-1 mt-3 pt-3 border-t border-[#e8e4dc]">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDownloadPdf(template.id); }}
                        title="Download PDF"
                        className="min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg hover:bg-[#f5f3ef] text-[#666] hover:text-[#2D2A26] transition-colors"
                      >
                        <Download className="w-4 h-4" />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDuplicate(template.id); }}
                        title="Duplicate"
                        className="min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg hover:bg-[#f5f3ef] text-[#666] hover:text-[#2D2A26] transition-colors"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); openDetail(template); }}
                        title="Edit"
                        className="min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg hover:bg-[#f5f3ef] text-[#666] hover:text-[#2D2A26] transition-colors"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <div className="flex-1" />
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(template.id); }}
                        title="Delete"
                        className="min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg hover:bg-red-50 text-[#ccc] hover:text-red-500 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
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
