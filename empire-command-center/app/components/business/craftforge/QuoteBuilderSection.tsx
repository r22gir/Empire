'use client';
import React, { useState, useEffect, useCallback } from 'react';
import { API } from '../../../lib/api';
import {
  Plus, X, Trash2, Calculator, Send, Loader2, PenTool, FileDown, Mail,
  ChevronDown, ChevronRight, Upload, Image as ImageIcon, Save, ArrowLeft,
  CheckCircle, FileText, ClipboardList, DollarSign, Percent
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

interface LineItem {
  description: string;
  quantity: number;
  unit: string;
  unit_price: number;
  material?: string;
  dimensions?: string;
  finish?: string;
}

type JobType = 'general' | 'cnc' | 'mixed';

const CATEGORIES = ['cornice', 'valance', 'cabinet-door', 'sign', 'furniture', 'shelving', 'trim', 'custom'] as const;
const STYLES = ['farmhouse', 'modern', 'art-deco', 'traditional', 'geometric', 'ornate', 'rustic', 'minimalist'] as const;
const MACHINES = ['x-carve', 'elegoo-saturn', 'manual'] as const;
const OPERATIONS = ['profile', 'pocket', 'vcarve', 'engrave', '3d-relief', '3d-print'] as const;
const UNITS = ['in', 'mm', 'cm', 'ft'] as const;
const MATERIAL_UNITS = ['ea', 'sqft', 'bdft', 'lnft', 'ml', 'kg'] as const;

const CNC_RATE = 1.50;

const emptyMaterial = (): MaterialRow => ({ name: '', quantity: 1, unit: 'ea', cost_per_unit: 0 });
const emptyCNC = (): CNCJobRow => ({ machine: 'x-carve', operation: 'profile', tool: '', estimated_time_min: 0 });
const emptyLineItem = (): LineItem => ({ description: '', quantity: 1, unit: 'ea', unit_price: 0 });

export default function QuoteBuilderSection() {
  const [view, setView] = useState<'list' | 'create' | 'edit'>('list');
  const [designs, setDesigns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingNumber, setEditingNumber] = useState<string>('');
  const [editingStatus, setEditingStatus] = useState<string>('draft');

  // Collapsible sections
  const [sectionsOpen, setSectionsOpen] = useState({
    customer: true, lineItems: true, cncMaterials: false, review: true,
  });
  const toggleSection = (key: keyof typeof sectionsOpen) =>
    setSectionsOpen(prev => ({ ...prev, [key]: !prev[key] }));

  // Form state
  const [customerName, setCustomerName] = useState('');
  const [customerEmail, setCustomerEmail] = useState('');
  const [customerPhone, setCustomerPhone] = useState('');
  const [customerAddress, setCustomerAddress] = useState('');
  const [designName, setDesignName] = useState('');
  const [description, setDescription] = useState('');
  const [jobType, setJobType] = useState<JobType>('general');
  const [category, setCategory] = useState<string>('custom');
  const [style, setStyle] = useState<string>('modern');
  const [width, setWidth] = useState<number>(0);
  const [height, setHeight] = useState<number>(0);
  const [depth, setDepth] = useState<number>(0);
  const [dimUnit, setDimUnit] = useState<string>('in');
  const [lineItems, setLineItems] = useState<LineItem[]>([emptyLineItem()]);
  const [materials, setMaterials] = useState<MaterialRow[]>([emptyMaterial()]);
  const [cncJobs, setCncJobs] = useState<CNCJobRow[]>([emptyCNC()]);
  const [laborCost, setLaborCost] = useState<number>(0);
  const [overhead, setOverhead] = useState<number>(0);
  const [margin, setMargin] = useState<number>(0);
  const [depositPct, setDepositPct] = useState<number>(0);
  const [taxRate, setTaxRate] = useState<number>(0);
  const [discountAmount, setDiscountAmount] = useState<number>(0);
  const [discountType, setDiscountType] = useState<'$' | '%'>('$');
  const [notes, setNotes] = useState('');

  // PDF visibility toggles — what the client sees on the quote/invoice
  const [pdfShow, setPdfShow] = useState({
    lineItems: true,
    materials: true,
    cncOps: true,
    dimensions: true,
    photos: false,
    notes: true,
    deposit: true,
    tax: true,
  });
  const togglePdf = (key: keyof typeof pdfShow) => setPdfShow(prev => ({ ...prev, [key]: !prev[key] }));

  // Photo upload state
  const [photos, setPhotos] = useState<{ file?: File; url?: string; name: string }[]>([]);
  const [uploading, setUploading] = useState(false);
  const [aiResults, setAiResults] = useState<any[]>([]);

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

  // Determine visibility flags
  const showCNC = jobType === 'cnc' || jobType === 'mixed';
  const showLineItems = jobType === 'general' || jobType === 'mixed';
  const showMaterials = jobType === 'cnc' || jobType === 'mixed';

  // Auto-calculate costs — fixed to avoid double-counting
  const lineItemTotal = lineItems.reduce((sum, li) => sum + (li.quantity * li.unit_price), 0);
  const materialCost = materials.reduce((sum, m) => sum + (m.quantity * m.cost_per_unit), 0);
  const cncTimeCost = cncJobs.reduce((sum, j) => sum + (j.estimated_time_min * CNC_RATE), 0);

  // Only count what's visible based on job type
  const itemsCost = showLineItems ? lineItemTotal : 0;
  const matsCost = showMaterials ? materialCost : 0;
  const cncCost = showCNC ? cncTimeCost : 0;

  const subtotal = itemsCost + matsCost + cncCost + laborCost + overhead;
  const marginAmount = subtotal * (margin / 100);
  const afterMargin = subtotal + marginAmount;
  const discountValue = discountType === '%' ? afterMargin * (discountAmount / 100) : discountAmount;
  const afterDiscount = afterMargin - discountValue;
  const taxAmount = afterDiscount * (taxRate / 100);
  const total = afterDiscount + taxAmount;
  const deposit = total * (depositPct / 100);

  const resetForm = () => {
    setCustomerName(''); setCustomerEmail(''); setCustomerPhone(''); setCustomerAddress('');
    setDesignName(''); setDescription(''); setJobType('general'); setCategory('custom'); setStyle('modern');
    setWidth(0); setHeight(0); setDepth(0); setDimUnit('in');
    setLineItems([emptyLineItem()]);
    setMaterials([emptyMaterial()]); setCncJobs([emptyCNC()]);
    setLaborCost(0); setOverhead(0); setMargin(0); setDepositPct(0); setNotes('');
    setTaxRate(0); setDiscountAmount(0); setDiscountType('$');
    setEditingId(null); setEditingNumber(''); setEditingStatus('draft');
    setPhotos([]); setAiResults([]);
  };

  // Load existing design into form for editing
  const loadDesign = (design: any) => {
    setEditingId(design.id);
    setEditingNumber(design.design_number || '');
    setEditingStatus(design.status || 'draft');
    setCustomerName(design.customer_name || '');
    setCustomerEmail(design.customer_email || '');
    setCustomerPhone(design.customer_phone || '');
    setCustomerAddress(design.customer_address || '');
    setDesignName(design.name || '');
    setDescription(design.description || '');
    setCategory(design.category || 'custom');
    setStyle(design.style || 'modern');
    setWidth(design.width || 0);
    setHeight(design.height || 0);
    setDepth(design.depth || 0);
    setDimUnit(design.unit || 'in');
    setLaborCost(design.labor_cost || 0);
    setOverhead(design.overhead || 0);
    setMargin(design.margin_percent ?? 0);
    setDepositPct(design.deposit_percent ?? 0);
    setTaxRate((design.tax_rate || 0) <= 1 ? (design.tax_rate || 0) * 100 : (design.tax_rate || 0));
    setDiscountAmount(design.discount_amount || 0);
    setDiscountType(design.discount_type === 'percent' ? '%' : '$');
    setNotes(design.notes || '');
    if (design.pdf_show) setPdfShow({ lineItems: true, materials: true, cncOps: true, dimensions: true, photos: false, notes: true, deposit: true, tax: true, ...design.pdf_show });

    // Determine job type from existing data
    const hasCNC = (design.cnc_jobs || []).some((j: any) => j.estimated_time_min > 0);
    const hasMaterials = (design.materials || []).some((m: any) => m.name);
    if (hasCNC && hasMaterials) setJobType('mixed');
    else if (hasCNC) setJobType('cnc');
    else setJobType('general');

    // Load materials — for general jobs, materials map to line items only (not both)
    const mats = design.materials || [];
    const lineItemsRaw = design.line_items || [];
    if (hasCNC) {
      // CNC/mixed: materials go into materials section, line items separate
      setMaterials(mats.length > 0 ? mats.map((m: any) => ({
        name: m.name || '',
        quantity: m.quantity || 1,
        unit: m.unit || 'ea',
        cost_per_unit: m.cost_per_unit || 0,
      })) : [emptyMaterial()]);
      setLineItems(lineItemsRaw.length > 0 ? lineItemsRaw.map((li: any) => ({
        description: li.description || '',
        quantity: li.quantity || 1,
        unit: li.unit || 'ea',
        unit_price: li.unit_price || 0,
        material: li.material || '',
        dimensions: li.dimensions || '',
        finish: li.finish || '',
      })) : [emptyLineItem()]);
    } else {
      // General woodwork: materials ARE the line items — load into lineItems only
      if (lineItemsRaw.length > 0) {
        // Prefer line_items if they exist
        setLineItems(lineItemsRaw.map((li: any) => ({
          description: li.description || '',
          quantity: li.quantity || 1,
          unit: li.unit || 'ea',
          unit_price: li.unit_price || 0,
          material: li.material || '',
          dimensions: li.dimensions || '',
          finish: li.finish || '',
        })));
      } else if (mats.length > 0) {
        setLineItems(mats.map((m: any) => ({
          description: m.name || '',
          quantity: m.quantity || 1,
          unit: m.unit || 'ea',
          unit_price: m.cost_per_unit || 0,
          material: m.type || '',
          dimensions: '',
          finish: '',
        })));
      } else {
        setLineItems([emptyLineItem()]);
      }
      setMaterials([emptyMaterial()]);  // Empty — no double counting
    }

    const cnc = design.cnc_jobs || [];
    setCncJobs(cnc.length > 0 ? cnc.map((j: any) => ({
      machine: j.machine || 'x-carve',
      operation: j.operation || 'profile',
      tool: j.tool || '',
      estimated_time_min: j.estimated_time_min || 0,
    })) : [emptyCNC()]);

    // Load existing photos
    const existingPhotos = design.photos || [];
    if (existingPhotos.length > 0) {
      setPhotos(existingPhotos.map((p: any) => ({
        url: typeof p === 'string' ? p : p.url || p.path || '',
        name: typeof p === 'string' ? p : p.original_name || p.filename || 'photo',
      })));
    } else {
      setPhotos([]);
    }

    setSectionsOpen({ customer: true, lineItems: true, cncMaterials: hasCNC, review: true });
    setView('edit');
  };

  // Build request body from form state
  const buildBody = () => ({
    customer_name: customerName,
    customer_email: customerEmail || undefined,
    customer_phone: customerPhone || undefined,
    customer_address: customerAddress || undefined,
    name: designName,
    description: description || undefined,
    category,
    style,
    width: width || undefined,
    height: height || undefined,
    depth: depth || undefined,
    unit: dimUnit,
    materials: (jobType === 'general' ? lineItems : materials).filter(m => (m as any).name?.trim() || (m as any).description?.trim()).map(m => {
      if ('description' in m) {
        return { name: m.description, type: 'wood', quantity: m.quantity, unit: m.unit, cost_per_unit: m.unit_price, total: m.quantity * m.unit_price };
      }
      return { ...m, type: 'wood', total: (m as MaterialRow).quantity * (m as MaterialRow).cost_per_unit };
    }),
    line_items: showLineItems ? lineItems.filter(li => li.description.trim()).map(li => ({
      description: li.description,
      quantity: li.quantity,
      unit: li.unit,
      unit_price: li.unit_price,
    })) : [],
    cnc_jobs: (jobType === 'cnc' || jobType === 'mixed') ? cncJobs.filter(j => j.estimated_time_min > 0) : [],
    material_cost: jobType === 'general' ? lineItemTotal : materialCost,
    cnc_time_cost: (jobType === 'cnc' || jobType === 'mixed') ? cncTimeCost : 0,
    labor_cost: laborCost,
    overhead,
    subtotal,
    total,
    margin_percent: margin,
    deposit_percent: depositPct,
    tax_rate: taxRate / 100,
    tax_amount: taxAmount,
    discount_amount: discountAmount,
    discount_type: discountType === '%' ? 'percent' : 'dollar',
    notes: notes || undefined,
    pdf_show: pdfShow,
  });

  const handleSubmit = async () => {
    if (!customerName.trim() || !designName.trim()) return;
    setSubmitting(true);
    try {
      const body = buildBody();
      if (editingId) {
        // Update existing
        await fetch(`${API}/craftforge/designs/${editingId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        resetForm();
        setView('list');
        fetchDesigns();
      } else {
        // Create new
        const resp = await fetch(`${API}/craftforge/designs`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        });
        const created = await resp.json();
        resetForm();
        setView('list');
        fetchDesigns();
        if (created?.id && confirm('Quote saved! Download PDF now?')) {
          handleDownloadPDF(created.id);
        }
      }
    } catch (e) {
      console.error('Failed to save design:', e);
    } finally {
      setSubmitting(false);
    }
  };

  // Line item handlers
  const updateLineItem = (idx: number, field: keyof LineItem, value: any) => {
    setLineItems(prev => prev.map((li, i) => i === idx ? { ...li, [field]: value } : li));
  };
  const addLineItem = () => setLineItems(prev => [...prev, emptyLineItem()]);
  const removeLineItem = (idx: number) => setLineItems(prev => prev.filter((_, i) => i !== idx));

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

  // Accept quote
  const handleAcceptQuote = async (designId: string) => {
    if (!confirm('Mark this quote as accepted?')) return;
    try {
      const resp = await fetch(`${API}/craftforge/designs/${designId}/accept`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || 'Accept failed');
      }
      alert('Quote accepted!');
      if (editingId === designId) setEditingStatus('accepted');
      fetchDesigns();
    } catch (e: any) {
      console.error('Accept failed:', e);
      alert(`Accept failed: ${e.message}`);
    }
  };

  // Create invoice
  const handleCreateInvoice = async (designId: string) => {
    if (!confirm('Create an invoice from this quote?')) return;
    try {
      const resp = await fetch(`${API}/craftforge/designs/${designId}/create-invoice`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || 'Create invoice failed');
      }
      alert('Invoice created!');
      if (editingId === designId) setEditingStatus('invoiced');
      fetchDesigns();
    } catch (e: any) {
      console.error('Create invoice failed:', e);
      alert(`Create invoice failed: ${e.message}`);
    }
  };

  // Create job
  const handleCreateJob = async (designId: string) => {
    if (!confirm('Create a job from this quote?')) return;
    try {
      const resp = await fetch(`${API}/craftforge/designs/${designId}/create-job`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || 'Create job failed');
      }
      alert('Job created!');
      fetchDesigns();
    } catch (e: any) {
      console.error('Create job failed:', e);
      alert(`Create job failed: ${e.message}`);
    }
  };

  // Photo upload
  const handlePhotoUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const newPhotos = Array.from(files).map(f => ({ file: f, name: f.name, url: URL.createObjectURL(f) }));
    setPhotos(prev => [...prev, ...newPhotos]);
  };

  const handlePhotoDrop = (e: React.DragEvent) => {
    e.preventDefault();
    handlePhotoUpload(e.dataTransfer.files);
  };

  const removePhoto = (idx: number) => {
    setPhotos(prev => prev.filter((_, i) => i !== idx));
  };

  const analyzePhoto = async (photoIdx: number) => {
    const photo = photos[photoIdx];
    if (!photo.file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', photo.file);
      const resp = await fetch(`${API}/vision/measure`, { method: 'POST', body: formData });
      if (resp.ok) {
        const result = await resp.json();
        setAiResults(prev => [...prev, { photoIdx, ...result }]);
      }
    } catch (e) {
      console.error('AI analysis failed:', e);
    } finally {
      setUploading(false);
    }
  };

  // ── Section header component ──
  const SectionHeader = ({ label, sectionKey, children }: { label: string; sectionKey: keyof typeof sectionsOpen; children?: React.ReactNode }) => (
    <div
      className="flex items-center justify-between cursor-pointer select-none"
      onClick={() => toggleSection(sectionKey)}
    >
      <div className="flex items-center gap-2">
        {sectionsOpen[sectionKey] ? <ChevronDown size={14} className="text-[#b8960c]" /> : <ChevronRight size={14} className="text-[#999]" />}
        <div className="section-label" style={{ marginBottom: 0 }}>{label}</div>
      </div>
      {children && <div onClick={e => e.stopPropagation()}>{children}</div>}
    </div>
  );

  // ── LIST VIEW ──
  if (view === 'list') {
    const filtered = designs.filter(d => {
      if (!search) return true;
      const q = search.toLowerCase();
      return (d.name || '').toLowerCase().includes(q) ||
             (d.customer_name || '').toLowerCase().includes(q) ||
             (d.design_number || '').toLowerCase().includes(q) ||
             (d.category || '').toLowerCase().includes(q);
    });

    const columns: Column[] = [
      { key: 'design_number', label: '#', sortable: true, render: (row) => <span style={{ fontSize: 12, fontWeight: 700, color: '#b8960c' }}>{row.design_number || '--'}</span> },
      { key: 'name', label: 'Design', sortable: true, render: (row) => <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{row.name || 'Untitled'}</span> },
      { key: 'customer_name', label: 'Customer', sortable: true },
      { key: 'category', label: 'Category', render: (row) => <span className="capitalize">{row.category || '--'}</span> },
      { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status || 'draft'} /> },
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
          <button
            onClick={(e) => { e.stopPropagation(); handleAcceptQuote(row.id); }}
            title="Accept Quote"
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: '#16a34a' }}
            className="hover:text-[#15803d]"
          >
            <CheckCircle size={15} />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); handleCreateInvoice(row.id); }}
            title="Create Invoice"
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: '#2563eb' }}
            className="hover:text-[#1d4ed8]"
          >
            <FileText size={15} />
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); handleCreateJob(row.id); }}
            title="Create Job"
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: '#9333ea' }}
            className="hover:text-[#7e22ce]"
          >
            <ClipboardList size={15} />
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
              onClick={() => { resetForm(); setView('create'); }}
              style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '10px 16px', fontSize: 12, fontWeight: 700, color: '#fff', background: '#b8960c', borderRadius: 10, border: 'none', cursor: 'pointer', minHeight: 44 }}
              className="hover:bg-[#a68500] transition-colors"
            >
              <Plus size={14} /> New Quote
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
            description={search ? 'Try adjusting your search terms.' : 'Create your first quote to get started.'}
            action={!search ? { label: 'Create Quote', onClick: () => { resetForm(); setView('create'); } } : undefined}
          />
        ) : (
          <DataTable columns={columns} data={filtered} onRowClick={(row) => loadDesign(row)} />
        )}
      </div>
    );
  }

  // ── CREATE / EDIT FORM ──
  const isEditing = view === 'edit' && editingId;

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: '24px 36px' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }} className="flex items-center gap-2">
            <Calculator size={20} className="text-[#b8960c]" />
            {isEditing ? `Edit ${editingNumber}` : 'New Quote'}
          </h2>
          {isEditing && <StatusBadge status={editingStatus || 'draft'} />}
        </div>
        <div className="flex items-center gap-2">
          {isEditing && (editingStatus === 'draft' || editingStatus === 'sent') && (
            <button
              onClick={() => handleAcceptQuote(editingId)}
              title="Accept Quote"
              style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '8px 12px', fontSize: 12, fontWeight: 600, color: '#16a34a', background: '#fff', borderRadius: 10, border: '1px solid #ece8e0', cursor: 'pointer', minHeight: 44 }}
            >
              <CheckCircle size={14} /> Accept
            </button>
          )}
          {isEditing && editingStatus === 'accepted' && (
            <button
              onClick={() => handleCreateInvoice(editingId)}
              title="Create Invoice"
              style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '8px 12px', fontSize: 12, fontWeight: 600, color: '#2563eb', background: '#fff', borderRadius: 10, border: '1px solid #ece8e0', cursor: 'pointer', minHeight: 44 }}
            >
              <FileText size={14} /> Invoice
            </button>
          )}
          {isEditing && (editingStatus === 'accepted' || editingStatus === 'invoiced') && (
            <button
              onClick={() => handleCreateJob(editingId)}
              title="Create Job"
              style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '8px 12px', fontSize: 12, fontWeight: 600, color: '#9333ea', background: '#fff', borderRadius: 10, border: '1px solid #ece8e0', cursor: 'pointer', minHeight: 44 }}
            >
              <ClipboardList size={14} /> Job
            </button>
          )}
          {isEditing && (
            <button
              onClick={() => handleDownloadPDF(editingId)}
              style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '8px 12px', fontSize: 12, fontWeight: 600, color: '#b8960c', background: '#fff', borderRadius: 10, border: '1px solid #ece8e0', cursor: 'pointer', minHeight: 44 }}
            >
              <FileDown size={14} /> PDF
            </button>
          )}
          <button
            onClick={() => { resetForm(); setView('list'); }}
            style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '8px 12px', fontSize: 12, fontWeight: 600, color: '#777', background: '#fff', borderRadius: 10, border: '1px solid #ece8e0', cursor: 'pointer', minHeight: 44 }}
          >
            <ArrowLeft size={14} /> Back
          </button>
        </div>
      </div>

      {/* Job Type Selector */}
      <div className="empire-card flat mb-4">
        <div className="section-label mb-3">Job Type</div>
        <div className="flex gap-2">
          {(['general', 'cnc', 'mixed'] as JobType[]).map(jt => (
            <button
              key={jt}
              onClick={() => setJobType(jt)}
              style={{
                flex: 1, padding: '10px 12px', fontSize: 12, fontWeight: 600,
                color: jobType === jt ? '#fff' : '#777',
                background: jobType === jt ? '#b8960c' : '#f8f8f8',
                borderRadius: 8, border: jobType === jt ? 'none' : '1px solid #ece8e0',
                cursor: 'pointer', textTransform: 'capitalize',
              }}
            >
              {jt === 'general' ? 'General Woodwork' : jt === 'cnc' ? 'CNC / Fabrication' : 'Mixed'}
            </button>
          ))}
        </div>
      </div>

      {/* Section 1: Customer & Job Info */}
      <div className="empire-card flat mb-4">
        <SectionHeader label="Customer & Job Info" sectionKey="customer" />
        {sectionsOpen.customer && (
          <div className="mt-3">
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Customer Name *</label>
                <input className="form-input" value={customerName} onChange={e => setCustomerName(e.target.value)} placeholder="Customer name" />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Email</label>
                <input className="form-input" type="email" value={customerEmail} onChange={e => setCustomerEmail(e.target.value)} placeholder="email@example.com" />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Phone</label>
                <input className="form-input" value={customerPhone} onChange={e => setCustomerPhone(e.target.value)} />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Address</label>
                <input className="form-input" value={customerAddress} onChange={e => setCustomerAddress(e.target.value)} />
              </div>
            </div>
            <div className="mb-3">
              <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Project Name *</label>
              <input className="form-input" value={designName} onChange={e => setDesignName(e.target.value)} placeholder="e.g. Custom Shelving Unit — Living Room" />
            </div>
            <div className="grid grid-cols-2 gap-3 mb-3">
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
            <div className="grid grid-cols-4 gap-3 mb-3">
              <div>
                <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Width</label>
                <input className="form-input" type="number" min={0} step={0.25} value={width || ''} onChange={e => setWidth(Number(e.target.value))} />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Height</label>
                <input className="form-input" type="number" min={0} step={0.25} value={height || ''} onChange={e => setHeight(Number(e.target.value))} />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Depth</label>
                <input className="form-input" type="number" min={0} step={0.25} value={depth || ''} onChange={e => setDepth(Number(e.target.value))} />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Unit</label>
                <select className="form-input" value={dimUnit} onChange={e => setDimUnit(e.target.value)}>
                  {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Description</label>
              <textarea className="form-input" rows={2} value={description} onChange={e => setDescription(e.target.value)} placeholder="Project description, special instructions..." />
            </div>
          </div>
        )}
      </div>

      {/* Section 2: Line Items (General Woodwork) */}
      {showLineItems && (
        <div className="empire-card flat mb-4">
          <SectionHeader label="Line Items" sectionKey="lineItems">
            <button onClick={addLineItem} className="flex items-center gap-1 text-[11px] font-bold text-[#b8960c] cursor-pointer hover:underline" style={{ background: 'none', border: 'none' }}>
              <Plus size={12} /> Add Item
            </button>
          </SectionHeader>
          {sectionsOpen.lineItems && (
            <div className="mt-3 space-y-2">
              {lineItems.map((li, i) => (
                <div key={i} className="grid grid-cols-12 gap-2 items-end">
                  <div className="col-span-5">
                    {i === 0 && <label className="block text-[9px] font-semibold text-[#bbb] uppercase mb-1">Description</label>}
                    <input className="form-input" value={li.description} onChange={e => updateLineItem(i, 'description', e.target.value)} placeholder="e.g. Floating shelf — walnut" />
                  </div>
                  <div className="col-span-2">
                    {i === 0 && <label className="block text-[9px] font-semibold text-[#bbb] uppercase mb-1">Qty</label>}
                    <input className="form-input" type="number" min={0} step={1} value={li.quantity || ''} onChange={e => updateLineItem(i, 'quantity', Number(e.target.value))} />
                  </div>
                  <div className="col-span-2">
                    {i === 0 && <label className="block text-[9px] font-semibold text-[#bbb] uppercase mb-1">Unit</label>}
                    <select className="form-input" value={li.unit} onChange={e => updateLineItem(i, 'unit', e.target.value)}>
                      {MATERIAL_UNITS.map(u => <option key={u} value={u}>{u}</option>)}
                    </select>
                  </div>
                  <div className="col-span-2">
                    {i === 0 && <label className="block text-[9px] font-semibold text-[#bbb] uppercase mb-1">Price</label>}
                    <input className="form-input" type="number" min={0} step={0.01} value={li.unit_price || ''} onChange={e => updateLineItem(i, 'unit_price', Number(e.target.value))} />
                  </div>
                  <div className="col-span-1 flex justify-center">
                    {lineItems.length > 1 && (
                      <button onClick={() => removeLineItem(i)} className="text-[#dc2626] hover:text-[#b91c1c] cursor-pointer" style={{ background: 'none', border: 'none', padding: 4 }}>
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </div>
              ))}
              <div className="text-right mt-2">
                <span style={{ fontSize: 12, fontWeight: 700, color: '#b8960c' }}>Line Items Total: ${lineItemTotal.toFixed(2)}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Section 3: Optional CNC/Materials (collapsible) */}
      {(showCNC || showMaterials) && (
        <div className="empire-card flat mb-4">
          <SectionHeader label={showCNC && showMaterials ? 'CNC Operations & Materials' : showCNC ? 'CNC Operations' : 'Materials'} sectionKey="cncMaterials" />
          {sectionsOpen.cncMaterials && (
            <div className="mt-3">
              {/* Materials (for CNC/mixed jobs) */}
              {showMaterials && (
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-semibold text-[#999] uppercase">Materials</span>
                    <button onClick={addMaterial} className="flex items-center gap-1 text-[11px] font-bold text-[#b8960c] cursor-pointer hover:underline" style={{ background: 'none', border: 'none' }}>
                      <Plus size={12} /> Add
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
              )}

              {/* CNC Operations */}
              {showCNC && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-semibold text-[#999] uppercase">CNC Operations</span>
                    <button onClick={addCNC} className="flex items-center gap-1 text-[11px] font-bold text-[#b8960c] cursor-pointer hover:underline" style={{ background: 'none', border: 'none' }}>
                      <Plus size={12} /> Add
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
              )}
            </div>
          )}
        </div>
      )}

      {/* Photo Upload */}
      <div className="empire-card flat mb-4">
        <div className="section-label mb-3">Photos</div>
        <div
          onDragOver={e => e.preventDefault()}
          onDrop={handlePhotoDrop}
          style={{ border: '2px dashed #ece8e0', borderRadius: 8, padding: photos.length > 0 ? 12 : 32, textAlign: 'center', cursor: 'pointer', background: '#fafaf8' }}
          onClick={() => document.getElementById('cf-photo-input')?.click()}
        >
          {photos.length > 0 ? (
            <div className="flex flex-wrap gap-3">
              {photos.map((p, i) => (
                <div key={i} className="relative" style={{ width: 80, height: 80 }}>
                  {p.url && <img src={p.url} alt={p.name} style={{ width: 80, height: 80, objectFit: 'cover', borderRadius: 6 }} />}
                  <button
                    onClick={(e) => { e.stopPropagation(); removePhoto(i); }}
                    style={{ position: 'absolute', top: -6, right: -6, background: '#dc2626', color: '#fff', borderRadius: '50%', width: 18, height: 18, border: 'none', cursor: 'pointer', fontSize: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                  >
                    <X size={10} />
                  </button>
                  {p.file && (
                    <button
                      onClick={(e) => { e.stopPropagation(); analyzePhoto(i); }}
                      title="AI Measure"
                      style={{ position: 'absolute', bottom: 2, right: 2, background: '#b8960c', color: '#fff', borderRadius: 4, padding: '2px 4px', border: 'none', cursor: 'pointer', fontSize: 9 }}
                    >
                      AI
                    </button>
                  )}
                </div>
              ))}
              <div style={{ width: 80, height: 80, border: '2px dashed #ddd', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#bbb' }}>
                <Plus size={20} />
              </div>
            </div>
          ) : (
            <div className="text-[#999]">
              <Upload size={24} className="mx-auto mb-2 text-[#ccc]" />
              <p className="text-[12px] font-semibold">Drop photos here or click to upload</p>
              <p className="text-[10px] mt-1">AI measurement available after upload</p>
            </div>
          )}
        </div>
        <input id="cf-photo-input" type="file" accept="image/*" multiple hidden onChange={e => handlePhotoUpload(e.target.files)} />
        {aiResults.length > 0 && (
          <div className="mt-3 p-3 bg-[#fffcf0] rounded-lg border border-[#f0e6c0]">
            <p className="text-[11px] font-bold text-[#b8960c] mb-2">AI Measurement Results</p>
            {aiResults.map((r, i) => (
              <div key={i} className="text-[11px] text-[#555] mb-1">
                {JSON.stringify(r.measurements || r.items || r, null, 0).slice(0, 200)}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Section 4: Review — Pricing & Notes */}
      <div className="empire-card flat mb-4">
        <SectionHeader label="Review & Pricing" sectionKey="review" />
        {sectionsOpen.review && (
          <div className="mt-3">
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Labor Cost ($)</label>
                <input className="form-input" type="number" min={0} step={0.01} value={laborCost || ''} onChange={e => setLaborCost(Number(e.target.value))} placeholder="0" />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Overhead ($)</label>
                <input className="form-input" type="number" min={0} step={0.01} value={overhead || ''} onChange={e => setOverhead(Number(e.target.value))} placeholder="0" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Margin (%)</label>
                <input className="form-input" type="number" min={0} max={100} step={0.5} value={margin || ''} onChange={e => setMargin(Number(e.target.value))} placeholder="0" />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Tax (%)</label>
                <input className="form-input" type="number" min={0} max={100} step={0.01} value={taxRate || ''} onChange={e => setTaxRate(Number(e.target.value))} placeholder="0" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Deposit (%)</label>
                <input className="form-input" type="number" min={0} max={100} step={1} value={depositPct || ''} onChange={e => setDepositPct(Number(e.target.value))} placeholder="0" />
              </div>
              <div>
                <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Discount</label>
                <div className="flex gap-1">
                  <input className="form-input" style={{ flex: 1 }} type="number" min={0} step={0.01} value={discountAmount || ''} onChange={e => setDiscountAmount(Number(e.target.value))} placeholder="0" />
                  <button
                    onClick={() => setDiscountType(discountType === '$' ? '%' : '$')}
                    style={{
                      padding: '6px 10px', fontSize: 12, fontWeight: 700,
                      color: '#fff', background: '#b8960c',
                      borderRadius: 6, border: 'none', cursor: 'pointer',
                      minWidth: 36, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}
                    title={`Toggle discount type (currently ${discountType})`}
                  >
                    {discountType === '$' ? <DollarSign size={14} /> : <Percent size={14} />}
                  </button>
                </div>
              </div>
            </div>

            <div>
              <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-1">Notes / Special Instructions</label>
              <textarea className="form-input" rows={3} value={notes} onChange={e => setNotes(e.target.value)} placeholder="Additional notes, special instructions, delivery details..." />
            </div>

            {/* PDF visibility toggles */}
            <div className="mt-4 pt-3" style={{ borderTop: '1px solid #ece8e0' }}>
              <label className="block text-[10px] font-semibold text-[#999] uppercase tracking-wide mb-2">Show on Quote / Invoice</label>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
                {([
                  ['lineItems', 'Line Items'],
                  ['materials', 'Materials Table'],
                  ['cncOps', 'CNC Operations'],
                  ['dimensions', 'Dimensions'],
                  ['notes', 'Notes'],
                  ['tax', 'Tax'],
                  ['deposit', 'Deposit Due'],
                  ['photos', 'Photos'],
                ] as [keyof typeof pdfShow, string][]).map(([key, label]) => (
                  <label key={key} className="flex items-center gap-2 cursor-pointer text-[12px] text-[#555]">
                    <input
                      type="checkbox"
                      checked={pdfShow[key]}
                      onChange={() => togglePdf(key)}
                      className="rounded"
                      style={{ accentColor: '#b8960c', width: 16, height: 16 }}
                    />
                    {label}
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Running Total (always visible) — shows full pricing formula */}
      <div className="empire-card flat mb-4" style={{ background: '#fafaf8', border: '2px solid #ece8e0' }}>
        <div className="text-[9px] font-semibold text-[#bbb] uppercase tracking-wide mb-2">Pricing Breakdown</div>
        <div className="space-y-1">
          {itemsCost > 0 && <div className="flex justify-between text-[12px] text-[#777]"><span>Line Items</span><span>${itemsCost.toFixed(2)}</span></div>}
          {matsCost > 0 && <div className="flex justify-between text-[12px] text-[#777]"><span>Materials</span><span>${matsCost.toFixed(2)}</span></div>}
          {cncCost > 0 && <div className="flex justify-between text-[12px] text-[#777]"><span>CNC Time</span><span>${cncCost.toFixed(2)}</span></div>}
          {laborCost > 0 && <div className="flex justify-between text-[12px] text-[#777]"><span>Labor</span><span>${laborCost.toFixed(2)}</span></div>}
          {overhead > 0 && <div className="flex justify-between text-[12px] text-[#777]"><span>Overhead</span><span>${overhead.toFixed(2)}</span></div>}
          <div className="flex justify-between text-[12px] text-[#555]" style={{ borderTop: '1px solid #e8e4dc', paddingTop: 6, marginTop: 4 }}>
            <span>Subtotal</span><span>${subtotal.toFixed(2)}</span>
          </div>
          {margin > 0 && <div className="flex justify-between text-[12px] text-[#777]"><span>Margin {margin}%</span><span>+${marginAmount.toFixed(2)}</span></div>}
          {discountAmount > 0 && <div className="flex justify-between text-[12px] text-[#dc2626]"><span>Discount{discountType === '%' ? ` ${discountAmount}%` : ''}</span><span>-${discountValue.toFixed(2)}</span></div>}
          {taxRate > 0 && <div className="flex justify-between text-[12px] text-[#777]"><span>Tax {taxRate}%</span><span>+${taxAmount.toFixed(2)}</span></div>}
          <div className="flex justify-between text-[14px] font-bold text-[#1a1a1a]" style={{ borderTop: '1px solid #e8e4dc', paddingTop: 8, marginTop: 4 }}>
            <span>TOTAL</span><span style={{ color: '#b8960c' }}>${total.toFixed(2)}</span>
          </div>
          {depositPct > 0 && <div className="flex justify-between text-[12px] font-semibold text-[#2563eb]">
            <span>Deposit Due ({depositPct}%)</span><span>${deposit.toFixed(2)}</span>
          </div>}
          {depositPct > 0 && <div className="flex justify-between text-[11px] text-[#999]">
            <span>Balance Due</span><span>${(total - deposit).toFixed(2)}</span>
          </div>}
        </div>
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
          {submitting ? <Loader2 size={14} className="animate-spin" /> : isEditing ? <Save size={14} /> : <Send size={14} />}
          {submitting ? 'Saving...' : isEditing ? 'Update Quote' : 'Create Quote'}
        </button>
      </div>
    </div>
  );
}
