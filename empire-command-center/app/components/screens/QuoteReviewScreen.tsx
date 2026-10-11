'use client';
import { useState, useEffect, useRef, useCallback } from 'react';
import { API, API_BASE } from '../../lib/api';
import { formatInches } from '../../lib/formatInches';
import { Quote } from '../../lib/types';
import { compressImageDataUrl, visionAbortSignal, visionTimeoutMessage } from '../../lib/visionImage';
import { linesFromAnalyzedItems, quoteLineDescriptions } from '../../lib/photoQuote';
import { Check, FileText, Send, Mail, Video, Printer, Image, ExternalLink, Upload, Search, Camera, Receipt, Loader2, Save, Plus, Trash2, ShieldCheck, X, ArrowLeft } from 'lucide-react';
import QuoteVerificationPanel from '../business/quotes/QuoteVerificationPanel';
import DepositPayLinkButton from '../business/finance/DepositPayLink';
import JobHeader from '../docs/JobHeader';
import DocActionBar from '../docs/DocActionBar';
import DocsTab, { useQuoteDocs } from '../docs/DocsTab';
import { moveToRoom } from '../docs/QuoteRooms';
import QuoteDocument from '../docs/QuoteDocument';
import DocViewer from '../docs/DocViewer';
import { orderByRoom } from '../docs/DocPaper';
import { openRecord } from '../docs/recordBus';
import { openDocViewer } from '../docs/viewerBus';
import { HudHeader, GaugeRow, RadialGauge, MaxStrip, fmtMoney, daysSince, type HudChip, type MaxSuggestion } from '../cyber/hud';

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
  name?: string;
  description: string;
  width?: number;
  height?: number;
  quantity?: number;
  dimensions?: { width?: number; height?: number; depth?: number };
  confidence?: number;
  selected?: boolean;
  line_items?: any[];
}

interface AnalysisResult {
  items: AnalyzedItem[];
  quote?: any;
  error?: string;
}

interface Props {
  quoteId?: string;
  onOpenBuilder?: () => void;
  onBack?: () => void;
}

/** Amount shown on Quote Review. Server rate is the unit price; amount is qty × rate. */
function lineItemAmount(item: { quantity?: number; rate?: number; amount?: number }) {
  const qty = Number(item?.quantity ?? 0);
  const rate = Number(item?.rate ?? 0);
  const extended = Math.round(qty * rate * 100) / 100;
  const stored = Number(item?.amount ?? 0);
  if (!Number.isFinite(extended)) return stored;
  if (Math.abs(extended - stored) > 0.02) return extended;
  return Number.isFinite(stored) ? stored : extended;
}

export default function QuoteReviewScreen({ quoteId, onOpenBuilder, onBack }: Props) {
  const [quote, setQuote] = useState<Quote | null>(null);
  const [selected, setSelected] = useState<number>(1);
  const [loading, setLoading] = useState(false);
  const [actionFeedback, setActionFeedback] = useState<string | null>(null);
  const [uploadedPhotos, setUploadedPhotos] = useState<UploadedPhoto[]>([]);
  const [uploading, setUploading] = useState(false);
  const [addingLines, setAddingLines] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [previewPhoto, setPreviewPhoto] = useState<string | null>(null);
  const [creatingInvoice, setCreatingInvoice] = useState(false);
  const [invoiceNumber, setInvoiceNumber] = useState<string | null>(null);
  const [createdInvoiceId, setCreatedInvoiceId] = useState<string | null>(null);
  const [editItems, setEditItems] = useState<any[]>([]);
  const [editNotes, setEditNotes] = useState('');
  const [editTerms, setEditTerms] = useState('');
  const [editTaxRate, setEditTaxRate] = useState(0);
  const [editDepositPct, setEditDepositPct] = useState(50);
  const [editDiscountAmt, setEditDiscountAmt] = useState(0);
  const [editDiscountType, setEditDiscountType] = useState<'dollar' | 'percent'>('dollar');
  const [dirty, setDirty] = useState(false);
  const [tab, setTab] = useState<'document' | 'pdf' | 'details' | 'docs'>('document');
  const [editMode, setEditMode] = useState(false);
  const [pdfSource, setPdfSource] = useState<'live' | 'final'>('live');
  const quoteDocs = useQuoteDocs(quoteId);
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
    const loaded = JSON.parse(JSON.stringify(q.line_items || [])).map((item: any) => ({
      ...item,
      amount: lineItemAmount(item),
    }));
    setEditItems(loaded);
    setEditNotes(q.notes || '');
    setEditTerms(q.terms || '');
    setEditTaxRate((q.tax_rate || 0) * 100);
    setEditDepositPct(q.deposit?.deposit_percent || 50);
    setEditDiscountAmt(q.discount_amount || 0);
    setEditDiscountType(q.discount_type || 'dollar');
    setDirty(false);
  }, [quote]);

  // Recalculate totals from editable items
  const computedSubtotal = editItems.reduce((sum, item) => sum + lineItemAmount(item), 0);
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

  // Rooms (4B): move a line into another room ('' = Job-wide) / add a line to a room.
  const moveItemToRoom = (idx: number, room: string) => {
    setEditItems(prev => moveToRoom(prev, idx, room));
    setDirty(true);
  };
  const addItemToRoom = (room: string) => {
    setEditItems(prev => {
      const blank = { description: '', quantity: 1, unit: 'ea', rate: 0, amount: 0, category: 'labor', room };
      return moveToRoom([...prev, blank], prev.length, room);
    });
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
          line_items: orderByRoom(editItems), // room order = the sections the client PDF prints
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
    setUploadedPhotos(prev => prev.map((p, i) => i === index ? { ...p, analyzing: true, analysis: null } : p));
    try {
      const imgRes = await fetch(`${API_BASE}${photo.path}`, { signal: visionAbortSignal() });
      if (!imgRes.ok) throw new Error(`Could not load photo (${imgRes.status})`);
      const blob = await imgRes.blob();
      const reader = new FileReader();
      const b64 = await new Promise<string>((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error('Could not read photo')), 20_000);
        reader.onload = () => {
          clearTimeout(timer);
          resolve(reader.result as string);
        };
        reader.onerror = () => {
          clearTimeout(timer);
          reject(new Error('Could not read photo'));
        };
        reader.readAsDataURL(blob);
      });
      const image = await compressImageDataUrl(b64);
      const res = await fetch(`${API}/quotes/analyze-photo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image,
          notes: quote?.customer_name || '',
          customer_notes: quote?.customer_name || '',
          customer_name: quote?.customer_name || 'Customer',
          // Attach the analysis to THIS quote instead of creating a new
          // JSON-store quote (the endpoint no longer persists a new one
          // regardless, but passing quote_id lets it record ai_outlines
          // on the quote already open here).
          quote_id: quote?.id,
        }),
        signal: visionAbortSignal(),
      });
      if (!res.ok) throw new Error(`Analysis failed: ${res.status}`);
      const data = await res.json();
      const items = (data.items || data.analysis?.items || data.analyzed_items || []).map((it: AnalyzedItem) => ({ ...it, selected: true }));
      setUploadedPhotos(prev => prev.map((p, i) => i === index ? {
        ...p,
        analyzing: false,
        analysis: { items, quote: data.quote },
      } : p));
      showFeedback(items.length
        ? `Found ${items.length} item(s). Check the ones you want, then add them to the quote.`
        : 'Found 0 item(s)');
    } catch (err) {
      const timedOut = visionTimeoutMessage(err);
      setUploadedPhotos(prev => prev.map((p, i) => i === index ? {
        ...p,
        analyzing: false,
        analysis: { items: [], error: timedOut || 'Analysis failed' },
      } : p));
      showFeedback(timedOut || 'Analysis failed');
    }
  };

  const addSelectedToQuoteLines = async () => {
    if (!quote?.id || addingLines) return;
    const incoming = uploadedPhotos.flatMap((photo) => linesFromAnalyzedItems(photo.analysis?.items || [], photo.analysis?.quote));
    if (!incoming.length) {
      showFeedback('Select at least one analyzed item');
      return;
    }
    const have = quoteLineDescriptions(editItems);
    const fresh = incoming.filter((line) => !have.has(line.description));
    if (!fresh.length) {
      showFeedback('Selected items are already on this quote');
      return;
    }
    setAddingLines(true);
    try {
      let last: any = null;
      for (const line of fresh) {
        const res = await fetch(`${API}/quotes-v2/${quote.id}/items`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ...line, business_unit: 'workroom' }),
          signal: visionAbortSignal(),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
          const detail = err.detail || err.error || `HTTP ${res.status}`;
          throw new Error(typeof detail === 'string' ? detail : 'Could not add line');
        }
        last = await res.json();
      }
      const updated = last?.quote || last;
      if (updated?.id) setQuote(updated);
      else await loadFull(quote.id);
      const notes = fresh.filter((line) => line.category === 'note').length;
      showFeedback(`Added ${fresh.length} line(s) to ${quote.quote_number || 'this quote'}${notes ? ` (${notes} unpriced)` : ''}`);
    } catch (err: any) {
      showFeedback(visionTimeoutMessage(err) || err.message || 'Could not add line items');
    } finally {
      setAddingLines(false);
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
  const quoteLocked = ['sent', 'accepted', 'in_production', 'completed'].includes(String(quote?.status || ''));
  const quoteFinalDoc = (() => {
    const g = quoteDocs.data?.groups.find(x => x.type === 'estimate' && x.final.jobFolder && !x.final.generated);
    return g ? g.final : null;
  })();
  const showProposalSelector = derivedTierProposals.length > 0
    && editItems.length === 0
    && ((quote as any)?.selected_proposal === null || (quote as any)?.selected_proposal === undefined);
  useEffect(() => { if (showProposalSelector) setTab(t => (t === 'document' ? 'details' : t)); }, [showProposalSelector]);
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
      <p className="text-base font-semibold text-[#888]">{quoteId ? `Quote ${quoteId} not found` : 'No quote selected'}</p>
      <p className="text-sm text-[#aaa]">{quoteId ? 'Go back to Quotes and pick it from the list' : 'Create a quote via chat to review here'}</p>
    </div>
  );

  const showFeedback = (msg: string) => {
    setActionFeedback(msg);
    setTimeout(() => setActionFeedback(null), 3000);
  };

  const handleAction = async (action: string) => {
    if (action === 'pdf') {
      // Opens the shared in-page viewer (preview, print, download, share) instead of forcing a download.
      openDocViewer({ src: `/api/v1/quotes-v2/${quote.id}/pdf`, title: `${quote.quote_number || 'Quote'} estimate`, filename: `${quote.quote_number || quote.id}.pdf`, kind: 'pdf' });
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
    if (!window.confirm(`Create a DRAFT invoice from ${quote.quote_number || 'this quote'}?\n\nIt carries over the line items (with rooms), client and deposit. Nothing is sent to the client.`)) return;
    setCreatingInvoice(true);
    try {
      // canonical quote -> invoice conversion (lifecycle_service.create_invoice_from_quote)
      const res = await fetch(`${API}/quotes-v2/${quote.id}/to-invoice`, {
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
      setInvoiceNumber(invNum); if (inv.id) setCreatedInvoiceId(inv.id);
      showFeedback(`Draft invoice ${invNum} created — $${(inv.total || 0).toFixed(2)}`);
      if (inv.id) setTimeout(() => openRecord({ type: 'invoice', id: inv.id }), 600);
    } catch {
      showFeedback('Failed to create invoice');
    }
    setCreatingInvoice(false);
  };

  // HUD header data — all read from the loaded quote / current edit state.
  const hudTotal = dirty ? computedTotal : ((quote as any).total ?? computedTotal);
  const hudStatus = String(quote.status || 'draft');
  const hudAge = daysSince((quote as any).sent_at || (quote as any).updated_at || quote.created_at);
  const hudChips: HudChip[] = [
    { label: hudStatus.replace(/_/g, ' '), tone: hudStatus === 'accepted' ? 'teal' : hudStatus === 'sent' ? 'blue' : hudStatus === 'draft' ? 'muted' : 'amber', live: hudStatus === 'sent' },
    ...((quote as any).intake_code ? [{ label: `Intake ${(quote as any).intake_code}`, tone: 'violet' as const }] : []),
    ...((quote as any).business_unit ? [{ label: String((quote as any).business_unit), tone: 'cyan' as const }] : []),
    ...(dirty ? [{ label: 'Unsaved changes', tone: 'mag' as const, live: true }] : []),
  ];
  const hudSugg: MaxSuggestion[] = [];
  if (dirty) hudSugg.push({ id: 'save', tone: 'mag', title: 'Save your edits', text: `Line items changed — new total ${fmtMoney(computedTotal, true)} is not saved yet.`, actionLabel: saving ? 'Saving…' : 'Save quote', onAction: () => { if (!saving) saveQuote(); }, source: 'local edits' });
  if (['draft', 'founder_review'].includes(hudStatus)) hudSugg.push({ id: 'approve', tone: 'cyan', title: 'Ready to send?', text: `${quote.quote_number} for ${quote.customer_name || 'this customer'} is still ${hudStatus.replace(/_/g, ' ')} at ${fmtMoney(hudTotal || 0, true)}. Approve with your PIN to mark it sent.`, actionLabel: 'Approve & Send', onAction: () => handleAction('approve_send'), source: `status ${hudStatus}` });
  if (hudStatus === 'sent' && hudAge != null && hudAge >= 7) hudSugg.push({ id: 'chase', tone: 'amber', title: 'Follow up', text: `Sent ${hudAge} days ago with no decision. Email ${quote.customer_name || 'the customer'} a reminder.`, actionLabel: 'Email customer', onAction: () => handleAction('email'), source: 'sent_at' });
  if (hudStatus === 'accepted' && !invoiceNumber) hudSugg.push({ id: 'inv', tone: 'teal', title: 'Accepted — bill it', text: `Create the invoice for ${fmtMoney(hudTotal || 0, true)}.`, actionLabel: creatingInvoice ? 'Creating…' : 'Create invoice', onAction: () => { if (!creatingInvoice) handleCreateInvoice(); }, source: 'status accepted' });
  if (uploadedPhotos.length === 0) hudSugg.push({ id: 'photos', tone: 'violet', title: 'No photos yet', text: 'Add room photos so Max can measure windows and suggest line items.', actionLabel: 'Add photos', onAction: () => fileInputRef.current?.click(), source: 'photos' });

  return (
    <div className="cy-qr flex-1 w-full">
      {onBack && <button type="button" className="dh-act" style={{ marginBottom: 8 }} onClick={onBack}><ArrowLeft size={15} /> Back</button>}
      <JobHeader quote={quote.id} refreshKey={(quote as any).updated_at} />
      <HudHeader
        icon={<FileText size={20} />}
        title={<><span className="cy-mono">{quote.quote_number}</span> · Quote Review</>}
        subtitle={<span suppressHydrationWarning>{quote.customer_name} · Created {quote.created_at ? new Date(quote.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Today'}</span>}
        chips={hudChips}
      />
      <DocActionBar
        doc={{ src: `/api/v1/quotes-v2/${quote.id}/pdf`, title: `${quote.quote_number || 'Quote'} estimate`, filename: `${quote.quote_number || quote.id}.pdf`, kind: 'pdf', v: (quote as any).updated_at || null }}
        sticky loading={saving}
        versionsCount={quoteDocs.data ? quoteDocs.data.groups.filter(g => g.type === 'estimate').reduce((t, g) => t + 1 + g.older.length, 0) + 1 : undefined}
        onVersions={() => setTab('docs')}
        clientPhone={(quote as any).customer_phone} clientEmail={(quote as any).customer_email}
        shareText={`Estimate ${quote.quote_number || ''}${quote.customer_name ? ` for ${quote.customer_name}` : ''}`}
        className="cy-qr-docbar" spacer="none"
      />
      <div className="dh dh-tabs" role="tablist" style={{ margin: '10px 0 14px', overflowX: 'auto' }}>
        <button type="button" role="tab" data-tab="document" aria-selected={tab === 'document'} className={`dh-tab${tab === 'document' ? ' is-active' : ''}`} onClick={() => setTab('document')}><FileText size={15} /> Document</button>
        <button type="button" role="tab" data-tab="pdf" aria-selected={tab === 'pdf'} className={`dh-tab${tab === 'pdf' ? ' is-active' : ''}`} onClick={() => setTab('pdf')}><Printer size={15} /> Actual PDF</button>
        <button type="button" role="tab" data-tab="details" aria-selected={tab === 'details'} className={`dh-tab${tab === 'details' ? ' is-active' : ''}`} onClick={() => setTab('details')}><Receipt size={15} /> Details</button>
        <button type="button" role="tab" data-tab="docs" aria-selected={tab === 'docs'} className={`dh-tab${tab === 'docs' ? ' is-active' : ''}`} onClick={() => setTab('docs')}>
          <FileText size={15} /> Docs{quoteDocs.data ? <span className="dh-act-count">{quoteDocs.data.groups.reduce((t, g) => t + (g.type === 'photo' ? 1 + g.older.length : 1), 0)}</span> : null}
        </button>
      </div>
      {tab === 'docs' ? (
        <div style={{ marginBottom: 20 }}><DocsTab quote={quote.id} /></div>
      ) : tab === 'document' ? (
        <div style={{ marginBottom: 24 }}>
          <QuoteDocument
            quote={quote} items={editItems} amountOf={lineItemAmount}
            editable={!quoteLocked} locked={quoteLocked} lockReason={quoteLocked ? 'Sent and accepted quotes cannot be edited (Sprint 1c). Revise it in QuoteBuilder as a new version.' : undefined}
            editMode={editMode} setEditMode={setEditMode}
            dirty={dirty} saving={saving} onSave={saveQuote} onDiscard={() => { setQuote(q => (q ? { ...q } : q)); setEditMode(false); }}
            onChange={updateItem} onRemove={removeItem} onMove={moveItemToRoom} onAdd={addItemToRoom}
            totals={{ subtotal: computedSubtotal, discount: computedDiscount, tax: computedTax, total: computedTotal, deposit: computedDeposit }}
            discountAmt={editDiscountAmt} setDiscountAmt={n => { setEditDiscountAmt(n); setDirty(true); }}
            discountType={editDiscountType} toggleDiscountType={() => { setEditDiscountType(editDiscountType === 'dollar' ? 'percent' : 'dollar'); setDirty(true); }}
            taxRate={editTaxRate} setTaxRate={n => { setEditTaxRate(n); setDirty(true); }}
            depositPct={editDepositPct} setDepositPct={n => { setEditDepositPct(n); setDirty(true); }}
            notes={editNotes} setNotes={v => { setEditNotes(v); setDirty(true); }} terms={editTerms} setTerms={v => { setEditTerms(v); setDirty(true); }}
            photos={uploadedPhotos.filter(ph => ph.path).map((ph, pi) => ({ url: `${API_BASE}${ph.path}`, label: `Photo ${pi + 1}` }))}
            onShowPdf={() => setTab('pdf')}
            onConvert={invoiceNumber && createdInvoiceId ? () => openRecord({ type: 'invoice', id: createdInvoiceId }) : handleCreateInvoice}
            convertLabel={invoiceNumber ? `Open ${invoiceNumber}` : 'Convert to invoice'}
            convertDisabledReason={invoiceNumber ? null : ['draft', 'founder_review'].includes(quote.status) ? 'Approve & send the quote first (founder PIN), then convert' : null}
            converting={creatingInvoice}
            extraTools={onOpenBuilder ? <button type="button" className="dh-act" onClick={onOpenBuilder}><ExternalLink size={15} /> QuoteBuilder</button> : null}
          />
        </div>
      ) : tab === 'pdf' ? (
        <div style={{ marginBottom: 24, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {quoteFinalDoc && (
            <div className="dh dh-actionbar" role="group" aria-label="Which PDF">
              <button type="button" className={`dh-chip${pdfSource === 'live' ? ' is-on' : ''}`} onClick={() => setPdfSource('live')}>Live quote PDF (current lines)</button>
              <button type="button" className={`dh-chip${pdfSource === 'final' ? ' is-on' : ''}`} onClick={() => setPdfSource('final')}>Saved FINAL · {quoteFinalDoc.version}</button>
            </div>
          )}
          {dirty && <div className="dh dh-empty" style={{ padding: 8, textAlign: 'left' }}>You have unsaved edits on the Document tab. The PDF shows the last saved version.</div>}
          <DocViewer mode="embed" initial={pdfSource === 'final' && quoteFinalDoc
            ? { id: quoteFinalDoc.id, title: quoteFinalDoc.title, kind: 'pdf' }
            : { src: `/api/v1/quotes-v2/${quote.id}/pdf`, title: `${quote.quote_number || 'Quote'} estimate`, kind: 'pdf', v: (quote as any).updated_at || null }} />
        </div>
      ) : (<>
      <GaugeRow>
        <RadialGauge i={0} label={dirty ? 'Total (editing)' : 'Quote total'} value={Number(hudTotal) || 0} format={n => fmtMoney(n, true)} tone="cyan" fraction={null} icon={<Receipt size={20} />}
          sub={`subtotal ${fmtMoney(computedSubtotal, true)}`} />
        <RadialGauge i={1} label="Deposit" value={computedDeposit} format={n => fmtMoney(n, true)} tone="teal" fraction={editDepositPct / 100}
          sub={`${editDepositPct}% of edited total`} />
        <RadialGauge i={2} label="Line items" value={editItems.length} tone="violet" fraction={null} icon={<FileText size={20} />}
          sub={dirty ? 'edited · unsaved' : 'saved'} />
        <RadialGauge i={3} label="Photos" value={uploadedPhotos.length} tone={uploadedPhotos.length ? 'amber' : 'muted'} fraction={null} icon={<Camera size={20} />}
          sub={uploadedPhotos.length ? `${uploadedPhotos.filter(ph => ph.analysis).length} analyzed` : 'none yet'} onClick={() => fileInputRef.current?.click()} />
      </GaugeRow>
      <MaxStrip items={hudSugg.slice(0, 3)} empty="This quote has nothing pending." />

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
                        <span>{it.description || it.type} {it.width && it.height ? `${formatInches(it.width)} × ${formatInches(it.height)}` : ''}</span>
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
            <button
              onClick={() => { void addSelectedToQuoteLines(); }}
              disabled={addingLines || !uploadedPhotos.some(p => (p.analysis?.items || []).some(it => it.selected !== false))}
              style={{
                padding: '8px 16px', borderRadius: 8, border: 'none', background: '#16a34a', color: '#fff',
                cursor: 'pointer', fontSize: 13, fontWeight: 700, minHeight: 44,
                display: 'flex', alignItems: 'center', gap: 6,
                opacity: addingLines || !uploadedPhotos.some(p => (p.analysis?.items || []).some(it => it.selected !== false)) ? 0.55 : 1,
              }}
            >
              <Plus size={14} /> {addingLines ? 'Adding...' : 'Add selected to line items'}
            </button>
          </div>
          <p style={{ margin: '8px 0 0', fontSize: 11, color: '#777' }}>
            Checkmarks only select items. They are written onto this Workroom quote when you add them.
          </p>
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

      {/* Line items are edited on the Document tab (WYSIWYG page) */}
      {!showProposalSelector ? (
        <div className="mb-5">
          <div className="empire-card" style={{ padding: 14, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: 220 }}>
              <div className="cy-qr-title">Line items</div>
              <div style={{ fontSize: 12.5, color: 'var(--cy-text-2, #a9c7d3)' }}>{editItems.length} lines · {fmtMoney(computedTotal, true)}. Edit them directly on the document page, grouped by room.</div>
            </div>
            <button type="button" className="cy-btn is-primary" onClick={() => { setTab('document'); setEditMode(!quoteLocked); }}><FileText size={14} /> Open document editor</button>
          </div>
            {(() => {
              const collect = (item: any) => {
                const idea = item?.idea_diagram;
                if (idea?.status === 'not_applicable') return null;
                const svg = idea?.svg || item?.drawing_svg;
                if (!svg && !idea?.note) return null;
                return {
                  label: item.description || item.name || item.type || idea?.category || 'Item',
                  svg: typeof svg === 'string' && svg.includes('<svg') ? svg : '',
                  note: idea?.note || '',
                  status: idea?.status || (svg ? 'attached' : 'degraded'),
                };
              };
              const fromLines = editItems.map(collect).filter(Boolean) as { label: string; svg: string; note: string; status: string }[];
              const fromRooms = (quote.rooms || []).flatMap((room: any) => (room.items || []).map(collect)).filter(Boolean) as { label: string; svg: string; note: string; status: string }[];
              const diagrams = fromLines.length ? fromLines : fromRooms;
              if (!diagrams.length) return null;
              return (
                <div style={{ marginTop: 16 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>Idea diagrams</div>
                  <p style={{ margin: '4px 0 10px', fontSize: 12, color: '#667085' }}>
                    Category and dimensions only. These sheets transmit the idea — final design is a later process.
                  </p>
                  {diagrams.map((diagram, index) => (
                    <div key={`${diagram.label}-${index}`} style={{ marginBottom: 12, padding: 10, border: '1px solid #ece8e0', borderRadius: 8, background: '#fff' }}>
                      <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 6 }}>{diagram.label}</div>
                      {diagram.svg ? (
                        <div className="cy-keep-light cy-paper" style={{ maxWidth: 720 }} dangerouslySetInnerHTML={{ __html: diagram.svg }} />
                      ) : (
                        <p style={{ margin: 0, fontSize: 12, color: '#8a5a00' }}>{diagram.note || 'Idea diagram unavailable. The quote totals are unchanged.'}</p>
                      )}
                      {diagram.svg && diagram.note ? (
                        <p style={{ margin: '6px 0 0', fontSize: 11, color: '#98a2b3' }}>{diagram.note}</p>
                      ) : null}
                    </div>
                  ))}
                </div>
              );
            })()}
        </div>
      ) : (
      <>
      <div className="cy-qr-title mb-3">Select a Proposal</div>
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
          padding: '10px 20px', background: 'rgba(3,14,22,0.95)', color: '#d9f8ff', border: '1px solid rgba(0,229,255,0.5)',
          fontSize: 13, fontWeight: 600, boxShadow: '0 0 22px rgba(0,229,255,0.35)', fontFamily: 'var(--cy-mono, monospace)',
          animation: 'fadeIn 0.2s ease',
        }}>
          {actionFeedback}
        </div>
      )}

      <div style={{ marginBottom: 12 }}>
        <DepositPayLinkButton
          quoteId={quote.id}
          customer={{
            name: quote.customer_name,
            email: (quote as any).customer_email,
            phone: (quote as any).customer_phone,
            address: (quote as any).customer_address,
          }}
        />
        <p className="text-[11px] text-[#888] mt-2">Sends a deposit Checkout link using this quote’s client. A second click reuses the same link.</p>
      </div>

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
              className="cy-btn is-teal is-pulse"
              style={{ width: '100%', minHeight: 44 }}
            >
              {creatingInvoice ? <Loader2 size={18} className="animate-spin" /> : <Receipt size={18} />}
              {creatingInvoice ? 'Creating Invoice...' : 'Create Invoice'}
            </button>
          )}
        </div>
      )}

      <div className="cy-qr-actions flex gap-2.5 flex-wrap">
        <button onClick={() => handleAction('confirm')}
          className="cy-btn is-primary"
          style={{ flex: '1 1 160px', minHeight: 44 }}
          title="Save the selected tier/proposal. Does NOT change the quote status.">
          <Check size={18} /> Save Tier
        </button>
        {quote &&
          ['draft', 'founder_review'].includes(quote.status) && (
          <button onClick={() => handleAction('approve_send')}
            className="cy-btn is-teal is-pulse"
            style={{ minHeight: 44 }}
            title="Move draft/founder_review -> sent. Requires PIN via modal.">
            <ShieldCheck size={18} /> Approve &amp; Send
          </button>
        )}
        <ActionBtn icon={<ExternalLink size={16} />} label="QuoteBuilder" onClick={() => {
          if (onOpenBuilder) { onOpenBuilder(); }
        }} />
        <ActionBtn icon={<Send size={16} />} label="Telegram" onClick={() => handleAction('telegram')} />
        <ActionBtn icon={<Video size={16} />} label="Call" onClick={() => handleAction('video')} />
      </div>

      </>)}

      <div className="dh-sticky-spacer" aria-hidden />
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
    <button type="button" onClick={onClick} className="cy-btn" style={{ minHeight: 44 }}>
      {icon} {label}
    </button>
  );
}
