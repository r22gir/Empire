'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { API, API_BASE } from '../../lib/api';
import { Quote } from '../../lib/types';
import { Check, FileText, Send, Mail, Video, Printer, Image, ExternalLink, Upload, Search, Camera, Receipt, Loader2, Save, Plus, Trash2, ShieldCheck, X } from 'lucide-react';
import QuoteVerificationPanel from '../business/quotes/QuoteVerificationPanel';

interface UploadedPhoto {
  filename: string;
  path: string;
  size: number;
  source: string;
  analyzing?: boolean;
  analysis?: AnalysisResult | null;
}

interface AnalyzedItem {
  type: string;
  description: string;
  width?: number;
  height?: number;
  confidence?: number;
  selected?: boolean;
}

interface AnalysisResult {
  items: AnalyzedItem[];
  error?: string;
}

interface Props {
  quoteId?: string;
  onOpenBuilder?: () => void;
}

export default function QuoteReviewScreen({ quoteId, onOpenBuilder }: Props) {
  const [quote, setQuote] = useState<Quote | null>(null);
  const [selected, setSelected] = useState<number>(1);
  const [loading, setLoading] = useState(false);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);
  const [uploadedPhotos, setUploadedPhotos] = useState<UploadedPhoto[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [previewPhoto, setPreviewPhoto] = useState<string | null>(null);
  const [creatingInvoice, setCreatingInvoice] = useState(false);
  const [invoiceNumber, setInvoiceNumber] = useState<string | null>(null);
  const [editItems, setEditItems] = useState<any[]>([]);
  const [editNotes, setEditNotes] = useState('');
  const [editTerms, setEditTerms] = useState('');
  const [editTaxRate, setEditTaxRate] = useState(0);
  const [editDepositPct, setEditDepositPct] = useState(50);
  const [editDiscountAmt, setEditDiscountAmt] = useState(0);
  const [editDiscountType, setEditDiscountType] = useState<'dollar' | 'percent'>('dollar');
  const [dirty, setDirty] = useState(false);
  // HOTFIX 4.1 — Approve PIN gate. The "Confirm Selection" button now
  // opens a PIN modal that calls POST /quotes-v2/{id}/approve with
  // founder_pin instead of bypassing straight to status='accepted'.
  const [approveModalOpen, setApproveModalOpen] = useState(false);
  const [approvePin, setApprovePin] = useState('');
  const [approveError, setApproveError] = useState<string | null>(null);
  const [approving, setApproving] = useState(false);
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // HOTFIX 4b: removed silent "first row of list" fallback. Pre-fix,
    // when no quoteId was passed (e.g. clicking a chat link that only
    // carried "EST-2026-110"), this effect fetched the most recent
    // quote and surfaced IT as if it were the requested one. The bug
    // was: an active list with EST-2026-124 (draft) made every
    // EST-2026-110 click land on EST-2026-124's review page.
    //
    // Post-fix: if no quoteId is passed, show a not-found state. The
    // chat-link click handler in ChatScreen.tsx now resolves the
    // quote_number to a real id via /quotes-v2/by-number/{qn} before
    // navigating, so this branch should rarely fire — but if it does,
    // the user sees a clear "no quote selected" hint instead of
    // silently opening the wrong quote.
    if (!quoteId) {
      setQuote(null);
      setLoading(false);
      return;
    }
    loadFull(quoteId);
  }, [quoteId]);

  const loadFull = async (id: string) => {
    setLoading(true);
    try {
      const res = await fetch(API + '/quotes-v2/' + id);
      if (res.ok) setQuote(await res.json());
    } catch { /* silent */ }
    setLoading(false);
  };

  // Initialize editable fields from quote
  useEffect(() => {
    if (!quote) return;
    const q = quote as any;
    setEditItems(JSON.parse(JSON.stringify(q.line_items || [])));
    setEditNotes(q.notes || '');
    setEditTerms(q.terms || '');
    setEditTaxRate((q.tax_rate || 0) * 100);
    setEditDepositPct(q.deposit?.deposit_percent || 50);
    setEditDiscountAmt(q.discount_amount || 0);
    setEditDiscountType(q.discount_type || 'dollar');
    setDirty(false);
  }, [quote]);

  // Recalculate totals from editable items
  const computedSubtotal = editItems.reduce((sum, item) => sum + (item.amount || 0), 0);
  const computedDiscount = editDiscountType === 'percent'
    ? Math.round(computedSubtotal * (editDiscountAmt / 100) * 100) / 100
    : editDiscountAmt;
  const computedTax = Math.round(computedSubtotal * (editTaxRate / 100) * 100) / 100;
  const computedTotal = Math.round((computedSubtotal + computedTax - computedDiscount) * 100) / 100;
  const computedDeposit = Math.round(computedTotal * (editDepositPct / 100) * 100) / 100;

  const updateItem = (idx: number, field: string, value: any) => {
    setEditItems(prev => {
      const items = [...prev];
      items[idx] = { ...items[idx], [field]: value };
      if (field === 'quantity' || field === 'rate') {
        items[idx].amount = Math.round((items[idx].quantity || 0) * (items[idx].rate || 0) * 100) / 100;
      }
      return items;
    });
    setDirty(true);
  };

  const addItem = () => {
    setEditItems(prev => [...prev, { description: '', quantity: 1, unit: 'sqft', rate: 0, amount: 0, category: 'labor' }]);
    setDirty(true);
  };

  const removeItem = (idx: number) => {
    setEditItems(prev => prev.filter((_, i) => i !== idx));
    setDirty(true);
  };

  const saveQuote = async () => {
    if (!quote) return;
    setSaving(true);
    try {
      const res = await fetch(`${API}/quotes-v2/${quote.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          line_items: editItems,
          subtotal: computedSubtotal,
          tax_rate: editTaxRate / 100,
          tax_amount: computedTax,
          discount_amount: editDiscountAmt,
          discount_type: editDiscountType,
          total: computedTotal,
          deposit: { deposit_percent: editDepositPct, deposit_amount: computedDeposit },
          notes: editNotes,
          terms: editTerms,
          customer_name: (quote as any).customer_name,
          customer_email: (quote as any).customer_email,
          customer_phone: (quote as any).customer_phone,
          customer_address: (quote as any).customer_address,
          business_unit: (quote as any).business_unit,
        }),
      });
      if (res.ok) {
        const updated = await res.json();
        setQuote(updated.quote || updated);
        setDirty(false);
        showFeedback('Quote saved!');
      } else {
        showFeedback('Save failed');
      }
    } catch {
      showFeedback('Save failed');
    }
    setSaving(false);
  };

  // Load existing photos for this quote (from intake transfer or photo store)
  useEffect(() => {
    if (!quote?.id) return;
    const intakePhotos: UploadedPhoto[] = (quote.photos || []).map((p: any) => {
      const isString = typeof p === 'string';
      return {
        filename: isString ? (p.split('/').pop() || 'photo') : (p.filename || p.original_name || 'photo'),
        path: isString ? p : (p.url || p.path || ''),
        size: 0,
        source: 'intake',
        analyzing: false,
        analysis: null,
      };
    });
    if (intakePhotos.length) {
      setUploadedPhotos(prev => {
        const existing = new Set(prev.map(p => p.filename));
        return [...prev, ...intakePhotos.filter(p => !existing.has(p.filename))];
      });
    }
    // Also try photo store
    fetch(`${API}/photos/quote/${quote.id}`)
      .then(r => r.json())
      .then(data => {
        if (data.photos?.length) {
          setUploadedPhotos(prev => {
            const existing = new Set(prev.map(p => p.filename));
            const newPhotos = data.photos
              .filter((p: UploadedPhoto) => !existing.has(p.filename))
              .map((p: UploadedPhoto) => ({ ...p, analyzing: false, analysis: null }));
            return [...prev, ...newPhotos];
          });
        }
      })
      .catch(() => {});
  }, [quote?.id, quote?.photos]);

  const handlePhotoUpload = useCallback(async (fileList: FileList | File[]) => {
    if (!quote?.id) return;
    const files = Array.from(fileList).filter(f => f.type.startsWith('image/'));
    if (!files.length) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('entity_type', 'quote');
      formData.append('entity_id', quote.id);
      formData.append('source', 'cc');
      files.forEach(f => formData.append('files', f));
      const res = await fetch(`${API}/photos/upload`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
      const data = await res.json();
      setUploadedPhotos(prev => [...prev, ...data.photos.map((p: UploadedPhoto) => ({ ...p, analyzing: false, analysis: null }))]);
      showFeedback(`${data.total} photo(s) uploaded`);
    } catch (err) {
      showFeedback('Upload failed');
    }
    setUploading(false);
  }, [quote?.id]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length) handlePhotoUpload(e.dataTransfer.files);
  }, [handlePhotoUpload]);

  const handleAnalyze = async (photo: UploadedPhoto, index: number) => {
    setUploadedPhotos(prev => prev.map((p, i) => i === index ? { ...p, analyzing: true } : p));
    try {
      const imgRes = await fetch(`${API_BASE}${photo.path}`);
      const blob = await imgRes.blob();
      const reader = new FileReader();
      const b64 = await new Promise<string>((resolve) => {
        reader.onload = () => resolve(reader.result as string);
        reader.readAsDataURL(blob);
      });
      const res = await fetch(`${API}/quotes/analyze-photo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: b64, customer_notes: quote?.customer_name || '' }),
      });
      if (!res.ok) throw new Error(`Analysis failed: ${res.status}`);
      const data = await res.json();
      const items = (data.items || data.analysis?.items || data.analyzed_items || []).map((it: AnalyzedItem) => ({ ...it, selected: true }));
      setUploadedPhotos(prev => prev.map((p, i) => i === index ? { ...p, analyzing: false, analysis: { items } } : p));
      showFeedback(`Found ${items.length} item(s)`);
    } catch {
      setUploadedPhotos(prev => prev.map((p, i) => i === index ? { ...p, analyzing: false, analysis: { items: [], error: 'Analysis failed' } } : p));
      showFeedback('Analysis failed');
    }
  };

  const proposals = quote?.design_proposals || [];
  const tiers = [
    { label: 'Essential', key: 'A', color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0' },
    { label: 'Designer', key: 'B', color: '#b8960c', bg: '#fdf8eb', border: '#f5ecd0' },
    { label: 'Premium', key: 'C', color: '#7c3aed', bg: '#faf5ff', border: '#e9d5ff' },
  ];
  const derivedTierProposals = proposals.length > 0 ? proposals : tiers
    .map((tierMeta, index) => {
      const tierMap = (quote as any)?.tiers || {};
      const tier = Array.isArray(tierMap)
        ? tierMap.find((entry: any) => entry?.fabric_grade === tierMeta.key || entry?.key === tierMeta.key)
        : tierMap[tierMeta.key];
      if (!tier) return null;
      return {
        label: tierMeta.label,
        tier: tierMeta.label,
        fabric_grade: tierMeta.key,
        lining_type: (quote as any)?.options?.lining_type || (quote as any)?.lining_preference || 'Standard',
        subtotal: tier.subtotal || 0,
        tax_amount: tier.tax || 0,
        tax_rate: tier.tax_rate || 0,
        total: tier.total || 0,
        line_items: (tier.items || []).flatMap((item: any) => item.line_items || []),
        source: 'tiers',
        index,
      };
    })
    .filter(Boolean);
  const showProposalSelector = derivedTierProposals.length > 0
    && editItems.length === 0
    && ((quote as any)?.selected_proposal === null || (quote as any)?.selected_proposal === undefined);
  const activeProposal = derivedTierProposals[selected] || derivedTierProposals[(quote as any)?.selected_proposal ?? 0] || null;
  const activeQuoteTotal = quote?.total ?? activeProposal?.total ?? 0;

  useEffect(() => {
    if (!quote) return;
    if ((quote as any).selected_proposal !== null && (quote as any).selected_proposal !== undefined) {
      setSelected((quote as any).selected_proposal);
    } else if (derivedTierProposals.length > 1) {
      setSelected(1);
    } else {
      setSelected(0);
    }
  }, [quote?.id, (quote as any)?.selected_proposal, derivedTierProposals.length]);

  if (loading) return (
    <div className="flex-1 flex items-center justify-center">
      <div className="w-8 h-8 border-3 border-[#e5e0d8] border-t-[#b8960c] rounded-full animate-spin" />
    </div>
  );

  if (!quote) return (
    <div className="flex-1 flex items-center justify-center flex-col gap-3">
      <FileText size={48} className="text-[#d8d3cb]" />
      <p className="text-base font-semibold text-[#888]">No quote selected</p>
      <p className="text-sm text-[#aaa]">Create a quote via chat to review here</p>
    </div>
  );

  const showFeedback = (msg: string) => {
    setActionFeedback(msg);
    setTimeout(() => setActionFeedback(null), 3000);
  };

  const handleAction = async (action: string) => {
    if (action === 'pdf') {
      showFeedback('Generating PDF...');
      try {
        const res = await fetch(`${API}/quotes/${quote.id}/pdf?skip_verification=true`, { method: 'POST' });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
          showFeedback(err.error || 'PDF generation failed');
          return;
        }
        const blob = await res.blob();
        const blobUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = `${quote.quote_number || quote.id}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(blobUrl);
        showFeedback('PDF downloaded!');
      } catch {
        showFeedback('PDF generation failed');
      }
    } else if (action === 'telegram') {
      showFeedback('Sending to Telegram...');
      try {
        await fetch(API + '/max/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: `Send quote ${quote.quote_number} for ${quote.customer_name} ($${activeQuoteTotal}) to Telegram`, model: 'auto', history: [] }),
        });
        showFeedback('Sent to Telegram!');
      } catch { showFeedback('Failed to send'); }
    } else if (action === 'email') {
      const subject = encodeURIComponent(`Quote ${quote.quote_number} - ${quote.customer_name}`);
      const body = encodeURIComponent(`Hi ${quote.customer_name},\n\nPlease find your quote ${quote.quote_number} attached.\n\nTotal: $${Number(activeQuoteTotal || 0).toLocaleString()}\n\nThank you,\nEmpire Workroom`);
      window.open(`mailto:?subject=${subject}&body=${body}`, '_blank');
      showFeedback('Opening email client...');
    } else if (action === 'print') {
      window.print();
    } else if (action === 'confirm') {
      // HOTFIX 4.1 — "Confirm Selection" only saves the tier selection
      // (selected_proposal + selected_tier). It MUST NOT set the quote
      // status to 'accepted' — that's a customer-side transition and
      // reaching it from this screen with no PIN was the bypass bug.
      showFeedback('Saving tier selection...');
      try {
        const res = await fetch(API + `/quotes-v2/${quote.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            selected_proposal: selected,
            selected_tier: tiers[selected]?.key,
          }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
          showFeedback(err.detail || err.error || 'Failed to update');
          return;
        }
        const data = await res.json();
        setQuote(data.quote || data);
        showFeedback('Tier selection saved.');
      } catch { showFeedback('Failed to update'); }
    } else if (action === 'approve_send') {
      // HOTFIX 4.1 — Founder approve-and-send flow. PIN-gated; calls
      // POST /api/v1/quotes-v2/{id}/approve with founder_pin in the
      // body. The server-side _require_founder_pin gates the actual
      // founder_review -> sent transition; no client-side bypass is
      // possible from this screen.
      if (quote.status !== 'founder_review' && quote.status !== 'draft') {
        showFeedback(`Cannot approve from '${quote.status}'.`);
        return;
      }
      setApproveError(null);
      setApprovePin('');
      setApproveModalOpen(true);
    } else if (action === 'approve_submit') {
      // HOTFIX 4.1 — submit PIN and let the server validate.
      if (approving) return;
      setApproving(true);
      setApproveError(null);
      try {
        const res = await fetch(API + `/quotes-v2/${quote.id}/approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            founder_pin: approvePin,
            changed_by: 'founder',
            reason: 'Approved from QuoteReviewScreen (HOTFIX 4.1)',
          }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
          setApproveError(err.detail || err.error || `HTTP ${res.status}`);
          return;
        }
        const data = await res.json();
        setQuote(data.quote || data);
        setApproveModalOpen(false);
        setApprovePin('');
        showFeedback('Quote approved and marked sent.');
      } catch (e) {
        setApproveError(`Network error: ${(e as Error).message}`);
      } finally {
        setApproving(false);
      }
    } else if (action === 'video') {
      showFeedback('Video call feature coming soon');
    }
  };

  const handleCreateInvoice = async () => {
    if (!quote?.id) return;
    setCreatingInvoice(true);
    try {
      const res = await fetch(`${API}/finance/invoices/from-quote/${quote.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        showFeedback(err.detail || err.error || 'Failed to create invoice');
        setCreatingInvoice(false);
        return;
      }
      const data = await res.json();
      const inv = data.invoice || data;
      const invNum = inv.invoice_number || inv.id || 'Created';
      setInvoiceNumber(invNum);
      showFeedback(`Invoice ${invNum} created — $${(inv.total || 0).toFixed(2)}`);
    } catch {
      showFeedback('Failed to create invoice');
    }
    setCreatingInvoice(false);
  };

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6 max-w-[850px] mx-auto w-full">
      <div className="flex items-center gap-3 mb-1">
        <div className="w-10 h-10 rounded-xl bg-[#fdf8eb] flex items-center justify-center">
          <FileText size={20} className="text-[#b8960c]" />
        </div>
        <div>
          <h1 className="text-lg font-bold text-[#1a1a1a]">{quote.quote_number} · Quote Review</h1>
          <p className="text-xs text-[#777]">{quote.customer_name} · Created {quote.created_at || 'Today'}</p>
        </div>
      </div>

      {/* Hidden file inputs */}
      <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,image/heic,image/webp" multiple
        style={{ display: 'none' }} onChange={e => e.target.files && handlePhotoUpload(e.target.files)} />
      <input ref={cameraInputRef} type="file" accept="image/*"
        style={{ display: 'none' }} onChange={e => e.target.files && handlePhotoUpload(e.target.files)} />

      {/* Photo area */}
      {uploadedPhotos.length > 0 ? (
        <div className="empire-card" style={{ padding: 12, marginTop: 16, marginBottom: 20, borderRadius: 14 }}>
          <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 8 }}>
            {/* All photos (intake + uploaded) with analyze buttons */}
            {uploadedPhotos.map((photo, pi) => {
              const photoUrl = photo.path?.startsWith('/api/') ? `${API_BASE}${photo.path}` : `${API_BASE}${photo.path}`;
              return (
              <div key={`u-${pi}`} style={{ position: 'relative', flexShrink: 0 }}>
                <img
                  src={photoUrl}
                  alt={`Photo ${pi + 1}`}
                  onClick={() => setPreviewPhoto(photoUrl)}
                  style={{ height: 160, width: 200, objectFit: 'cover', borderRadius: 8, cursor: 'pointer', border: '1px solid #e5e0d8' }}
                />
                <button
                  onClick={() => handleAnalyze(photo, pi)}
                  disabled={photo.analyzing}
                  style={{
                    position: 'absolute', bottom: 6, right: 6, padding: '5px 10px', borderRadius: 6,
                    background: photo.analyzing ? '#888' : '#b8960c', color: '#fff', border: 'none',
                    fontSize: 11, fontWeight: 600, cursor: photo.analyzing ? 'default' : 'pointer',
                    display: 'flex', alignItems: 'center', gap: 4, minHeight: 30,
                  }}
                >
                  <Search size={12} /> {photo.analyzing ? 'Analyzing...' : 'Analyze'}
                </button>
                {/* Analysis results */}
                {photo.analysis && photo.analysis.items.length > 0 && (
                  <div style={{ marginTop: 6, background: '#f0fdf4', borderRadius: 6, padding: 6, fontSize: 11, maxWidth: 200 }}>
                    {photo.analysis.items.map((it, ii) => (
                      <label key={ii} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '2px 0', cursor: 'pointer' }}>
                        <input type="checkbox" checked={it.selected !== false} onChange={() => {
                          setUploadedPhotos(prev => prev.map((p, i) => {
                            if (i !== pi || !p.analysis) return p;
                            const items = [...p.analysis.items];
                            items[ii] = { ...items[ii], selected: !items[ii].selected };
                            return { ...p, analysis: { ...p.analysis, items } };
                          }));
                        }} />
                        <span>{it.description || it.type} {it.width && it.height ? `${it.width}×${it.height}"` : ''}</span>
                      </label>
                    ))}
                  </div>
                )}
                {photo.analysis?.error && (
                  <div style={{ marginTop: 4, fontSize: 11, color: '#dc2626', padding: '2px 4px' }}>{photo.analysis.error}</div>
                )}
              </div>
            );})}
            {/* Add more button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              style={{
                flexShrink: 0, width: 80, height: 160, borderRadius: 8, border: '2px dashed #ccc',
                background: '#faf9f7', cursor: 'pointer', display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center', gap: 4, color: '#999', fontSize: 12,
              }}
            >
              <Upload size={20} />
              Add
            </button>
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
            <button onClick={() => fileInputRef.current?.click()} disabled={uploading}
              style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #ddd', background: '#fff', cursor: 'pointer', fontSize: 13, minHeight: 44, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Upload size={14} /> Upload Files
            </button>
            <button onClick={() => cameraInputRef.current?.click()} disabled={uploading}
              style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid #ddd', background: '#fff', cursor: 'pointer', fontSize: 13, minHeight: 44, display: 'flex', alignItems: 'center', gap: 6 }}>
              <Camera size={14} /> Take Photo
            </button>
          </div>
        </div>
      ) : (
        <div
          className="empire-card"
          onDrop={handleDrop}
          onDragOver={e => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          style={{
            padding: 0, height: 200, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 12,
            marginTop: 16, marginBottom: 20,
            background: dragOver ? '#fdf8eb' : '#eae7e2',
            border: dragOver ? '2px dashed #b8960c' : '2px dashed transparent',
            transition: 'all 0.2s',
            cursor: 'pointer',
          }}
          onClick={() => fileInputRef.current?.click()}
        >
          {uploading ? (
            <>
              <div className="w-6 h-6 border-2 border-[#ccc] border-t-[#b8960c] rounded-full animate-spin" />
              <span className="text-[#888] text-sm">Uploading...</span>
            </>
          ) : (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Image size={32} className="text-[#c0bbb3]" />
              </div>
              <span className="text-[#888] font-medium text-sm">No photos yet — drop images here or click to upload</span>
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}
                  style={{
                    padding: '10px 20px', borderRadius: 8, border: 'none',
                    background: '#b8960c', color: '#fff', fontSize: 14, fontWeight: 600,
                    cursor: 'pointer', minHeight: 44, display: 'flex', alignItems: 'center', gap: 6,
                  }}>
                  <Camera size={16} /> Add Photos
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Full-size preview modal */}
      {previewPhoto && (
        <div
          onClick={() => setPreviewPhoto(null)}
          style={{
            position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.85)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
          }}
        >
          <img src={previewPhoto} alt="Preview" style={{ maxWidth: '90vw', maxHeight: '90vh', borderRadius: 8 }} />
        </div>
      )}

      {/* Quote Quality Verification */}
      <div style={{ marginBottom: 16 }}>
        <QuoteVerificationPanel quoteId={quote.id} />
      </div>

      {/* Editable line items */}
      {!showProposalSelector ? (
        <div className="mb-5">
          <div className="flex items-center justify-between mb-3">
            <div className="text-sm font-bold text-[#1a1a1a]">Line Items</div>
            <div className="flex items-center gap-2">
              {dirty && (
                <button onClick={saveQuote} disabled={saving}
                  className="flex items-center gap-1.5 cursor-pointer"
                  style={{ padding: '6px 14px', borderRadius: 8, background: '#b8960c', color: '#fff', border: 'none', fontSize: 12, fontWeight: 700 }}>
                  {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              )}
              <button onClick={addItem} className="flex items-center gap-1 cursor-pointer"
                style={{ padding: '6px 12px', borderRadius: 8, background: '#f0fdf4', color: '#16a34a', border: '1px solid #bbf7d0', fontSize: 11, fontWeight: 600 }}>
                <Plus size={12} /> Add Line
              </button>
            </div>
          </div>
          <div className="empire-card" style={{ padding: 16 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e5e0d8' }}>
                  <th style={{ textAlign: 'left', padding: '6px 8px', color: '#777', fontSize: 11, textTransform: 'uppercase' }}>Description</th>
                  <th style={{ textAlign: 'right', padding: '6px 8px', color: '#777', fontSize: 11, width: 80 }}>Qty</th>
                  <th style={{ textAlign: 'center', padding: '6px 8px', color: '#777', fontSize: 11, width: 60 }}>Unit</th>
                  <th style={{ textAlign: 'right', padding: '6px 8px', color: '#777', fontSize: 11, width: 90 }}>Rate</th>
                  <th style={{ textAlign: 'right', padding: '6px 8px', color: '#777', fontSize: 11, width: 100 }}>Amount</th>
                  <th style={{ width: 36 }}></th>
                </tr>
              </thead>
              <tbody>
                {editItems.map((item: any, i: number) => (
                  <tr key={i} style={{ borderBottom: '1px solid #f0ece4' }}>
                    <td style={{ padding: '4px 8px' }}>
                      <input type="text" value={item.description || ''}
                        onChange={e => updateItem(i, 'description', e.target.value)}
                        style={{ width: '100%', fontSize: 12, padding: '6px 8px', border: '1px solid #ece8e0', borderRadius: 6, background: '#faf9f7', color: '#333' }} />
                      {/* HOTFIX 5: per-row "Founder override" badge when
                          price_overridden=1. The server's _item_to_dict
                          now aliases rate/amount to final_price when
                          overridden, so the editable inputs already
                          show $1,933.33 — this badge makes the override
                          state explicit so the founder doesn't accidentally
                          edit and lose the override on a Save that goes
                          through a path we haven't audited. */}
                      {item.price_overridden ? (
                        <span
                          title={`Found set final price: $${(item.final_price ?? item.rate ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })} (original unit_price was $${item.unit_price ?? 0}).`}
                          style={{
                            display: 'inline-block', marginTop: 4,
                            fontSize: 10, fontWeight: 600, color: '#7c5a00',
                            background: '#fcf3cf', border: '1px solid #e0b700',
                            borderRadius: 4, padding: '1px 6px',
                            textTransform: 'uppercase', letterSpacing: '0.5px',
                          }}
                        >
                          Founder override
                        </span>
                      ) : null}
                    </td>
                    <td style={{ padding: '4px 4px' }}>
                      <input type="number" step="0.1" value={item.quantity ?? ''}
                        onChange={e => updateItem(i, 'quantity', parseFloat(e.target.value) || 0)}
                        style={{ width: '100%', textAlign: 'right', fontSize: 12, padding: '6px 6px', border: '1px solid #ece8e0', borderRadius: 6, background: '#faf9f7' }} />
                    </td>
                    <td style={{ padding: '4px 4px' }}>
                      <select value={item.unit || 'ea'}
                        onChange={e => { updateItem(i, 'unit', e.target.value); }}
                        style={{ width: '100%', fontSize: 11, padding: '6px 2px', border: '1px solid #ece8e0', borderRadius: 6, background: '#faf9f7', color: '#555' }}>
                        <option value="sqft">sqft</option>
                        <option value="ea">ea</option>
                        <option value="yd">yd</option>
                        <option value="hr">hr</option>
                        <option value="lf">lf</option>
                      </select>
                    </td>
                    <td style={{ padding: '4px 4px' }}>
                      <div style={{ display: 'flex', alignItems: 'center' }}>
                        <span style={{ fontSize: 11, color: '#888', marginRight: 2 }}>$</span>
                        <input type="number" step="0.01" value={item.rate ?? ''}
                          onChange={e => updateItem(i, 'rate', parseFloat(e.target.value) || 0)}
                          style={{ width: '100%', textAlign: 'right', fontSize: 12, padding: '6px 6px', border: '1px solid #ece8e0', borderRadius: 6, background: '#faf9f7' }} />
                      </div>
                    </td>
                    <td style={{ padding: '4px 8px', textAlign: 'right', fontWeight: 600, color: '#1a1a1a', fontSize: 12 }}>
                      ${(item.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td style={{ padding: '4px 4px', textAlign: 'center' }}>
                      <button onClick={() => removeItem(i)} className="cursor-pointer"
                        style={{ border: 'none', background: 'none', color: '#ccc', padding: 4 }}
                        onMouseEnter={e => (e.currentTarget.style.color = '#dc2626')}
                        onMouseLeave={e => (e.currentTarget.style.color = '#ccc')}>
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={4} style={{ padding: '10px 8px', textAlign: 'right', color: '#666', fontSize: 12 }}>Subtotal</td>
                  <td style={{ padding: '10px 8px', textAlign: 'right', fontWeight: 600, fontSize: 13, color: '#1a1a1a' }}>
                    ${computedSubtotal.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                  <td></td>
                </tr>
                <tr>
                  <td colSpan={3} style={{ padding: '4px 8px', textAlign: 'right', color: '#16a34a', fontSize: 12 }}>Discount</td>
                  <td style={{ padding: '4px 4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 2 }}>
                      <input type="number" step="0.01" min="0" value={editDiscountAmt || ''}
                        onChange={e => { setEditDiscountAmt(parseFloat(e.target.value) || 0); setDirty(true); }}
                        style={{ width: 50, textAlign: 'right', fontSize: 11, padding: '4px 4px', border: '1px solid #ece8e0', borderRadius: 4, background: '#faf9f7' }}
                        placeholder="0" />
                      <button onClick={() => { setEditDiscountType(editDiscountType === 'dollar' ? 'percent' : 'dollar'); setDirty(true); }}
                        style={{ fontSize: 11, color: '#16a34a', background: 'none', border: '1px solid #ece8e0', borderRadius: 4, padding: '2px 6px', cursor: 'pointer', fontWeight: 600 }}
                        title={`Toggle discount type (currently ${editDiscountType})`}>
                        {editDiscountType === 'dollar' ? '$' : '%'}
                      </button>
                    </div>
                  </td>
                  <td style={{ padding: '4px 8px', textAlign: 'right', fontSize: 12, color: '#16a34a' }}>
                    {computedDiscount > 0 ? `-$${computedDiscount.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : '—'}
                  </td>
                  <td></td>
                </tr>
                <tr>
                  <td colSpan={3} style={{ padding: '4px 8px', textAlign: 'right', color: '#666', fontSize: 12 }}>Tax</td>
                  <td style={{ padding: '4px 4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 2 }}>
                      <input type="number" step="0.1" value={editTaxRate}
                        onChange={e => { setEditTaxRate(parseFloat(e.target.value) || 0); setDirty(true); }}
                        style={{ width: 50, textAlign: 'right', fontSize: 11, padding: '4px 4px', border: '1px solid #ece8e0', borderRadius: 4, background: '#faf9f7' }} />
                      <span style={{ fontSize: 11, color: '#888' }}>%</span>
                    </div>
                  </td>
                  <td style={{ padding: '4px 8px', textAlign: 'right', fontSize: 12, color: '#666' }}>
                    ${computedTax.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                  <td></td>
                </tr>
                <tr style={{ borderTop: '2px solid #b8960c' }}>
                  <td colSpan={4} style={{ padding: '10px 8px', textAlign: 'right', fontWeight: 700, fontSize: 15 }}>
                    Total
                    <span
                      title="HOTFIX 5: total is read from quotes_v2.total (canonical server value), not client-side recompute. The client-computed value would silently double-count when a line item's price_overridden=1."
                      style={{
                        marginLeft: 8, fontSize: 10, fontWeight: 500, color: '#888',
                        background: '#fef9e7', border: '1px solid #f1c40f', borderRadius: 4, padding: '1px 6px',
                      }}
                    >
                      canonical
                    </span>
                  </td>
                  <td style={{ padding: '10px 8px', textAlign: 'right', fontWeight: 700, fontSize: 18, color: '#b8960c' }}>
                    {/* HOTFIX 5: previously this read computedTotal (a
                        client-side recompute that ignored price_overridden
                        and rendered $3,600 instead of the canonical $2,900
                        for the Maggie O'Neil EST-2026-110 quote). The
                        server's _recalculate_totals honors final_price
                        when price_overridden=1, so quotes_v2.total is the
                        authoritative total. We display the canonical
                        total and only flip to computedTotal while the
                        user has unsaved edits (so they see what their
                        in-progress change will look like). */}
                    ${(
                      dirty
                        ? computedTotal
                        : (quote as any).total ?? computedTotal
                    ).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                  <td></td>
                </tr>
                <tr>
                  <td colSpan={3} style={{ padding: '6px 8px', textAlign: 'right', color: '#666', fontSize: 12 }}>Deposit</td>
                  <td style={{ padding: '4px 4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 2 }}>
                      <input type="number" step="1" value={editDepositPct}
                        onChange={e => { setEditDepositPct(parseFloat(e.target.value) || 0); setDirty(true); }}
                        style={{ width: 45, textAlign: 'right', fontSize: 11, padding: '4px 4px', border: '1px solid #ece8e0', borderRadius: 4, background: '#faf9f7' }} />
                      <span style={{ fontSize: 11, color: '#888' }}>%</span>
                    </div>
                  </td>
                  <td style={{ padding: '6px 8px', textAlign: 'right', fontWeight: 600, color: '#16a34a', fontSize: 13 }}>
                    ${computedDeposit.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </td>
                  <td></td>
                </tr>
              </tfoot>
            </table>

            {/* Editable notes */}
            <div style={{ marginTop: 14 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#777', marginBottom: 4 }}>Notes</div>
              <textarea value={editNotes}
                onChange={e => { setEditNotes(e.target.value); setDirty(true); }}
                rows={3}
                style={{ width: '100%', fontSize: 12, padding: '8px 10px', border: '1px solid #ece8e0', borderRadius: 8, background: '#faf9f7', color: '#444', lineHeight: 1.5, resize: 'vertical' }} />
            </div>

            {/* Editable terms */}
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#777', marginBottom: 4 }}>Terms & Conditions</div>
              <textarea value={editTerms}
                onChange={e => { setEditTerms(e.target.value); setDirty(true); }}
                rows={2}
                style={{ width: '100%', fontSize: 12, padding: '8px 10px', border: '1px solid #ece8e0', borderRadius: 8, background: '#faf9f7', color: '#444', lineHeight: 1.5, resize: 'vertical' }} />
            </div>

            {/* Save bar at bottom when dirty */}
            {dirty && (
              <div style={{ marginTop: 14, display: 'flex', justifyContent: 'flex-end' }}>
                <button onClick={saveQuote} disabled={saving}
                  className="flex items-center gap-2 cursor-pointer"
                  style={{ padding: '10px 24px', borderRadius: 10, background: '#b8960c', color: '#fff', border: 'none', fontSize: 13, fontWeight: 700, boxShadow: '0 2px 8px rgba(184,150,12,0.3)' }}>
                  {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                  {saving ? 'Saving...' : 'Save Quote'}
                </button>
              </div>
            )}
          </div>
        </div>
      ) : (
      <>
      <div className="text-sm font-bold mb-3 text-[#1a1a1a]">Select a Proposal</div>
      <div className="flex gap-3 mb-5">
        {tiers.map((t, i) => {
          const p = derivedTierProposals[i];
          const total = p?.total || 0;
          const isSelected = selected === i;
          return (
            <div key={t.key} onClick={() => setSelected(i)}
              className={`empire-card flex-1 cursor-pointer text-center min-h-[140px] transition-all
                ${isSelected
                  ? 'shadow-[0_4px_16px_rgba(0,0,0,0.1)]'
                  : 'hover:shadow-[0_2px_8px_rgba(0,0,0,0.06)]'}`}
              style={{
                padding: 20,
                background: isSelected ? t.bg : '#faf9f7',
                borderColor: isSelected ? t.color : '#ece8e0',
                borderWidth: 2,
                borderLeftWidth: '4px',
                borderLeftColor: t.color,
              }}>
              <div className="text-xs font-bold text-[#777] tracking-wide">{t.key} · {t.label}</div>
              <div className="text-[26px] font-bold my-2" style={{ color: t.color }}>${total.toLocaleString()}</div>
              <div className="text-[11px] text-[#888]">Grade {t.key} fabric · {p?.lining_type || 'Standard'} lining</div>
              {/* Mockup images */}
              {(p?.inpainted_image_url || p?.mockup_image) && (
                <div className="flex gap-1.5 mt-3">
                  {p.inpainted_image_url && (
                    <div className="flex-1 rounded-lg overflow-hidden border border-[#e5e0d8]">
                      <div className="text-[9px] text-center py-1 font-bold" style={{ color: t.color, background: t.bg }}>Your Room</div>
                      <img src={API.replace('/api/v1','') + p.inpainted_image_url} className="w-full h-[70px] object-cover" alt="" />
                    </div>
                  )}
                  {p.clean_mockup_url && (
                    <div className="flex-1 rounded-lg overflow-hidden border border-[#e5e0d8]">
                      <div className="text-[9px] text-center py-1 bg-[#f5f3ef] font-bold text-[#777]">Inspiration</div>
                      <img src={API.replace('/api/v1','') + p.clean_mockup_url} className="w-full h-[70px] object-cover" alt="" />
                    </div>
                  )}
                </div>
              )}
              {!p?.inpainted_image_url && !p?.mockup_image && (
                <div className="w-full h-[80px] bg-[#f5f3ef] rounded-lg mt-3 flex items-center justify-center text-[11px] text-[#bbb] border border-[#ece8e1]">
                  <Image size={16} className="mr-1.5 text-[#d8d3cb]" /> AI Mockup — {t.label}
                </div>
              )}
            </div>
          );
        })}
      </div>
      </>
      )}

      {/* Feedback toast */}
      {actionFeedback && (
        <div style={{
          position: 'fixed', bottom: 24, right: 24, zIndex: 999,
          padding: '10px 20px', borderRadius: 12, background: '#1a1a1a', color: '#fff',
          fontSize: 13, fontWeight: 600, boxShadow: '0 4px 20px rgba(0,0,0,0.2)',
          animation: 'fadeIn 0.2s ease',
        }}>
          {actionFeedback}
        </div>
      )}

      {/* Create Invoice button — shown when quote is accepted */}
      {quote.status === 'accepted' && (
        <div style={{ marginBottom: 12 }}>
          {invoiceNumber ? (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 10, padding: '12px 18px',
              borderRadius: 12, background: '#f0fdf4', border: '1.5px solid #bbf7d0',
            }}>
              <Receipt size={18} className="text-[#16a34a]" />
              <div>
                <div style={{ fontSize: 13, fontWeight: 700, color: '#16a34a' }}>Invoice Created</div>
                <div style={{ fontSize: 12, color: '#555' }}>{invoiceNumber}</div>
              </div>
            </div>
          ) : (
            <button
              onClick={handleCreateInvoice}
              disabled={creatingInvoice}
              className="w-full flex items-center justify-center gap-2 text-white text-[13px] font-bold cursor-pointer hover:bg-[#a08509] shadow-[0_2px_8px_rgba(184,150,12,0.25)] transition-all active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed"
              style={{ height: 44, padding: '0 20px', borderRadius: 12, background: '#b8960c', border: '2px solid #a08509' }}
            >
              {creatingInvoice ? <Loader2 size={18} className="animate-spin" /> : <Receipt size={18} />}
              {creatingInvoice ? 'Creating Invoice...' : 'Create Invoice'}
            </button>
          )}
        </div>
      )}

      <div className="flex gap-2.5 flex-wrap">
        <button onClick={() => handleAction('confirm')}
          className="flex-1 flex items-center justify-center gap-2 bg-[#b8960c] text-white border-2 border-[#a08509] text-[13px] font-bold cursor-pointer hover:bg-[#a08509] shadow-[0_2px_8px_rgba(184,150,12,0.25)] transition-all active:scale-[0.98]"
          style={{ height: 44, padding: '0 20px', borderRadius: 12 }}
          title="Save the selected tier/proposal. Does NOT change the quote status.">
          <Check size={18} /> Save Tier
        </button>
        {quote &&
          ['draft', 'founder_review'].includes(quote.status) && (
          <button onClick={() => handleAction('approve_send')}
            className="flex items-center justify-center gap-2 bg-[#16a34a] text-white border-2 border-[#15803d] text-[13px] font-bold cursor-pointer hover:bg-[#15803d] shadow-[0_2px_8px_rgba(22,163,74,0.25)] transition-all active:scale-[0.98]"
            style={{ height: 44, padding: '0 20px', borderRadius: 12 }}
            title="Move draft/founder_review -> sent. Requires PIN via modal.">
            <ShieldCheck size={18} /> Approve &amp; Send
          </button>
        )}
        <ActionBtn icon={<ExternalLink size={16} />} label="QuoteBuilder" onClick={() => {
          if (onOpenBuilder) { onOpenBuilder(); }
        }} />
        <ActionBtn icon={<FileText size={16} />} label="PDF" onClick={() => handleAction('pdf')} />
        <ActionBtn icon={<Send size={16} />} label="Telegram" onClick={() => handleAction('telegram')} />
        <ActionBtn icon={<Mail size={16} />} label="Email" onClick={() => handleAction('email')} />
        <ActionBtn icon={<Video size={16} />} label="Call" onClick={() => handleAction('video')} />
        <ActionBtn icon={<Printer size={16} />} label="Print" onClick={() => handleAction('print')} />
      </div>

      {/* HOTFIX 4.1 — PIN modal for founder approve-and-send.
          Replaces the bypass 'Confirm Selection' button. Modal is
          closed by default; opens via handleAction('approve_send').
          The PIN is sent server-side as founder_pin in the approve
          body; the server uses _require_founder_pin to validate. */}
      {approveModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="approve-pin-title"
          style={{
            position: 'fixed', inset: 0, background: 'rgba(20,20,20,0.55)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000,
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget && !approving) {
              setApproveModalOpen(false);
              setApprovePin('');
              setApproveError(null);
            }
          }}>
          <div style={{
            background: '#fff', borderRadius: 14, padding: 24,
            width: '90%', maxWidth: 420, boxShadow: '0 24px 48px rgba(0,0,0,0.22)',
          }}>
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              marginBottom: 12,
            }}>
              <h3 id="approve-pin-title" style={{
                fontSize: 17, fontWeight: 700, color: '#1a1a1a',
                display: 'flex', alignItems: 'center', gap: 8, margin: 0,
              }}>
                <ShieldCheck size={20} color="#16a34a" />
                Approve &amp; Send
              </h3>
              <button
                onClick={() => {
                  if (!approving) {
                    setApproveModalOpen(false);
                    setApprovePin('');
                    setApproveError(null);
                  }
                }}
                aria-label="Close"
                style={{
                  background: 'none', border: 'none', cursor: approving ? 'wait' : 'pointer',
                  color: '#888', padding: 4,
                }}>
                <X size={20} />
              </button>
            </div>
            <p style={{ fontSize: 13, color: '#555', margin: '0 0 16px', lineHeight: 1.5 }}>
              Move <strong>{quote?.quote_number || quote?.id}</strong> from
              <strong> {quote?.status} </strong> to <strong>sent</strong>.
              PIN entry happens only via this portal modal — never
              typed in chat. Enter your founder PIN to confirm.
            </p>
            <input
              type="password"
              autoComplete="off"
              autoFocus
              value={approvePin}
              onChange={(e) => setApprovePin(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleAction('approve_submit');
              }}
              placeholder="Founder PIN"
              disabled={approving}
              style={{
                width: '100%', padding: '10px 12px', fontSize: 14,
                border: '1.5px solid #ece8e0', borderRadius: 8,
                fontFamily: 'ui-monospace, monospace', letterSpacing: '0.15em',
                background: approving ? '#f8f8f6' : '#fff',
                marginBottom: 10,
              }}
            />
            {approveError && (
              <div style={{
                background: '#fef2f2', border: '1px solid #fecaca',
                color: '#991b1b', borderRadius: 6, padding: '8px 10px',
                fontSize: 12, marginBottom: 10,
              }}>
                {approveError}
              </div>
            )}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button
                onClick={() => {
                  if (approving) return;
                  setApproveModalOpen(false);
                  setApprovePin('');
                  setApproveError(null);
                }}
                disabled={approving}
                style={{
                  padding: '8px 14px', borderRadius: 6,
                  border: '1.5px solid #ece8e0', background: '#fff',
                  color: '#555', fontSize: 13, fontWeight: 600,
                  cursor: approving ? 'wait' : 'pointer',
                }}>
                Cancel
              </button>
              <button
                onClick={() => handleAction('approve_submit')}
                disabled={approving || approvePin.length < 4}
                style={{
                  padding: '8px 14px', borderRadius: 6, border: 'none',
                  background: approving || approvePin.length < 4 ? '#9ca3af' : '#16a34a',
                  color: '#fff', fontSize: 13, fontWeight: 700,
                  cursor: approving || approvePin.length < 4 ? 'wait' : 'pointer',
                  display: 'flex', alignItems: 'center', gap: 6,
                }}>
                <ShieldCheck size={16} />
                {approving ? 'Approving...' : 'Approve & Send'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ActionBtn({ icon, label, onClick }: { icon: React.ReactNode; label: string; onClick?: () => void }) {
  return (
    <button onClick={onClick}
      className="flex items-center gap-1.5 font-bold text-[#555] cursor-pointer hover:bg-[#fdf8eb] hover:border-[#b8960c] hover:text-[#b8960c] transition-all active:scale-[0.97]"
      style={{
        height: 44,
        padding: '0 16px',
        borderRadius: 12,
        border: '1.5px solid #ece8e0',
        background: '#faf9f7',
        fontSize: 12,
      }}>
      {icon} {label}
    </button>
  );
}
