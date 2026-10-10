'use client';
/**
 * Invoice document screen (QuickBooks-style): sticky job header, unified action bar,
 * and the invoice itself as a WYSIWYG page. Draft invoices are edited right on the page
 * (click a line, add / move lines by room, totals update live). Sent / paid invoices are read-only.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, FileText, Printer, Loader2, Pencil, Eye, Save, Undo2, Lock, Receipt, Plus, ExternalLink, Briefcase } from 'lucide-react';
import { API } from '../../lib/api';
import JobHeader from './JobHeader';
import DocActionBar from './DocActionBar';
import DocViewer from './DocViewer';
import DocsTab from './DocsTab';
import DocPaper, { money2, orderByRoom } from './DocPaper';
import { moveToRoom } from './QuoteRooms';
import { openRecord } from './recordBus';
import Breadcrumb from '../shared/Breadcrumb';
import './docs.css';
import './paper.css';

type Line = Record<string, any>;
const FIELDS = { qty: 'quantity', rate: 'unit_price', unit: 'unit', desc: 'description' };
const lineAmount = (l: Line) => {
  const q = Number(l.quantity ?? 0), r = Number(l.unit_price ?? l.rate ?? 0);
  const ext = Math.round(q * r * 100) / 100;
  if (Number.isFinite(ext) && (q || r)) return ext;
  return Number(l.amount ?? l.subtotal ?? 0) || 0;
};
const fmtDate = (s?: string | null) => { if (!s) return ''; const str = String(s); const d = new Date(/^\d{4}-\d{2}-\d{2}$/.test(str) ? `${str}T12:00:00` : str.replace(' ', 'T')); return isNaN(d.getTime()) ? String(s) : d.toLocaleDateString('en-US', { month: 'long', day: '2-digit', year: 'numeric' }); };

export default function InvoiceDocScreen({ invoiceId, onBack }: { invoiceId: string | null; onBack?: () => void }) {
  const [inv, setInv] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [tab, setTab] = useState<'document' | 'pdf' | 'docs'>('document');
  const [items, setItems] = useState<Line[]>([]);
  const [taxRate, setTaxRate] = useState(0);
  const [notes, setNotes] = useState('');
  const [terms, setTerms] = useState('');
  const [dirty, setDirty] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!invoiceId) return;
    setErr(null);
    try {
      const r = await fetch(`${API}/finance/invoices/${encodeURIComponent(invoiceId)}`);
      if (!r.ok) throw new Error(r.status === 404 ? 'Invoice not found' : `Could not load invoice (${r.status})`);
      const j = await r.json();
      setInv(j.invoice || j);
    } catch (e: any) { setErr(e?.message || 'Could not load invoice'); }
  }, [invoiceId]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!inv) return;
    setItems((inv.line_items || []).map((l: Line) => ({ ...l })));
    setTaxRate(Math.round(Number(inv.tax_rate || 0) * 100 * 1000) / 1000); // stored as a fraction
    setNotes(inv.notes || ''); setTerms(inv.terms || '');
    setDirty(false);
  }, [inv]);

  const status = String(inv?.status || '');
  const editable = status === 'draft';
  const canEdit = editable && editMode;
  const subtotal = useMemo(() => Math.round(items.reduce((t, l) => t + lineAmount(l), 0) * 100) / 100, [items]);
  // same math as finance._recalc_invoice: tax on subtotal, discount flat or percent
  const discRaw = Number(inv?.discount_amount || 0);
  const discount = inv?.discount_type === 'percent' ? Math.round(subtotal * discRaw) / 100 : discRaw;
  const tax = Math.round(subtotal * (taxRate / 100) * 100) / 100;
  const total = dirty ? Math.round((subtotal - discount + tax) * 100) / 100 : Number(inv?.total ?? subtotal);
  const paid = Number(inv?.amount_paid || 0);
  const balance = Math.round((total - paid) * 100) / 100;

  const change = (idx: number, field: string, value: any) => {
    setItems(prev => prev.map((l, i) => {
      if (i !== idx) return l;
      const n: Line = { ...l, [field]: field === 'quantity' || field === 'unit_price' ? (parseFloat(value) || 0) : value };
      if (field === 'quantity' || field === 'unit_price') n.amount = Math.round(Number(n.quantity || 0) * Number(n.unit_price || 0) * 100) / 100;
      return n;
    }));
    setDirty(true);
  };
  const remove = (idx: number) => { setItems(prev => prev.filter((_, i) => i !== idx)); setDirty(true); };
  const move = (idx: number, room: string) => { setItems(prev => moveToRoom(prev, idx, room)); setDirty(true); };
  const add = (room: string) => {
    setItems(prev => {
      const blank: Line = { description: '', quantity: 1, unit: 'ea', unit_price: 0, amount: 0, room };
      let at = -1; prev.forEach((l, i) => { if (String(l.room || '') === room) at = i; });
      const next = [...prev]; next.splice(at >= 0 ? at + 1 : next.length, 0, blank); return next;
    });
    setDirty(true); setEditMode(true);
  };

  const save = async () => {
    if (!inv) return;
    setSaving(true);
    try {
      const line_items = orderByRoom(items).map(l => ({ ...l, amount: lineAmount(l) }));
      const r = await fetch(`${API}/finance/invoices/${encodeURIComponent(inv.id)}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ line_items, subtotal, tax_rate: taxRate / 100, notes, terms }),
      });
      if (!r.ok) throw new Error(`Save failed (${r.status})`);
      setToast('Invoice saved'); setEditMode(false);
      await load();
    } catch (e: any) { setToast(e?.message || 'Save failed'); }
    finally { setSaving(false); setTimeout(() => setToast(null), 3000); }
  };

  if (!invoiceId) return <div className="dh dh-empty" style={{ margin: 24 }}>No invoice selected.</div>;
  if (err) return <div style={{ padding: 20 }}>{onBack && <button type="button" className="dh-act" onClick={onBack}><ArrowLeft size={15} /> Back</button>}<div className="dh dh-empty" style={{ marginTop: 12 }}>{err}</div></div>;
  if (!inv) return <div style={{ padding: 40, textAlign: 'center' }}><Loader2 className="animate-spin" /></div>;

  const pdfDoc = { src: `/api/v1/finance/invoices/${inv.id}/pdf`, title: `${inv.invoice_number || 'Invoice'}`, filename: `${inv.invoice_number || inv.id}.pdf`, kind: 'pdf' as const, v: inv.updated_at || null };
  const client = inv.client_name || inv.customer_name || '';
  return (
    <div className="cy-invdoc" style={{ padding: '12px 16px 90px', maxWidth: 1180, margin: '0 auto' }}>
      <div style={{ marginBottom: 12 }}>
        <Breadcrumb
          items={[
            { label: 'Workroom', onClick: onBack },
            { label: 'Invoices', onClick: onBack },
            { label: inv.invoice_number || 'Invoice' },
          ]}
          onBack={onBack}
          backLabel="Back"
        />
      </div>
      <JobHeader invoice={inv.id} refreshKey={inv.updated_at} />
      <DocActionBar doc={pdfDoc} sticky spacer="none" loading={saving} clientPhone={inv.client_phone} clientEmail={inv.client_email}
        shareText={`Invoice ${inv.invoice_number || ''}${client ? ` for ${client}` : ''}`} />
      <div className="dh dh-tabs" role="tablist" style={{ margin: '10px 0 14px', overflowX: 'auto' }}>
        <button type="button" role="tab" data-tab="document" aria-selected={tab === 'document'} className={`dh-tab${tab === 'document' ? ' is-active' : ''}`} onClick={() => setTab('document')}><FileText size={15} /> Document</button>
        <button type="button" role="tab" data-tab="pdf" aria-selected={tab === 'pdf'} className={`dh-tab${tab === 'pdf' ? ' is-active' : ''}`} onClick={() => setTab('pdf')}><Printer size={15} /> Actual PDF</button>
        {inv.quote_id && <button type="button" role="tab" data-tab="docs" aria-selected={tab === 'docs'} className={`dh-tab${tab === 'docs' ? ' is-active' : ''}`} onClick={() => setTab('docs')}><FileText size={15} /> Docs</button>}
      </div>
      {toast && <div className="dh dh-empty" role="status" style={{ padding: 8, marginBottom: 8 }}>{toast}</div>}

      {tab === 'pdf' ? (
        <>{dirty && <div className="dh dh-empty" style={{ padding: 8, textAlign: 'left', marginBottom: 8 }}>Unsaved edits are not in the PDF yet.</div>}<DocViewer mode="embed" initial={pdfDoc} /></>
      ) : tab === 'docs' && inv.quote_id ? (
        <DocsTab quote={inv.quote_id} />
      ) : (
        <div className="qp-wrap">
          <div className="dh qp-toolbar" role="toolbar" aria-label="Invoice editing">
            <span className="qp-state">
              <i className={`qp-dot${!editable ? ' is-locked' : dirty ? ' is-dirty' : ''}`} />
              {!editable ? <><Lock size={13} /> <b>{status.replace(/_/g, ' ') || 'Locked'}</b> · only draft invoices can be edited</> : dirty ? <><b>Unsaved changes</b> · new total {money2(total)}</> : canEdit ? <><b>Editing on the page</b> · click any line</> : <><b>Draft</b> · click a line or Edit to change it</>}
            </span>
            {editable && (editMode
              ? <button type="button" className="dh-act" onClick={() => setEditMode(false)}><Eye size={15} /> Done</button>
              : <button type="button" className="dh-act is-primary" onClick={() => setEditMode(true)}><Pencil size={15} /> Edit</button>)}
            {canEdit && <button type="button" className="dh-act" onClick={() => { const n = window.prompt('New room name (e.g. PRIMARY BEDROOM)'); if (n && n.trim()) add(n.trim()); }}><Plus size={15} /> Add room</button>}
            {dirty && <button type="button" className="dh-act" onClick={() => { setInv((x: any) => ({ ...x })); setEditMode(false); }} disabled={saving}><Undo2 size={15} /> Discard</button>}
            {dirty && <button type="button" className="dh-act is-primary" onClick={save} disabled={saving}>{saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} Save</button>}
            {!editable && <button type="button" className="dh-act" onClick={() => openRecord({ type: 'invoice-edit', id: inv.id })} title="Payments, status and reminders in the invoice manager"><ExternalLink size={15} /> Payments &amp; status</button>}
            {inv.quote_id && <button type="button" className="dh-act" onClick={() => openRecord({ type: 'quote', id: inv.quote_id })}><Receipt size={15} /> Source quote</button>}
            {inv.job_id && <button type="button" className="dh-act" onClick={() => openRecord({ type: 'job', id: inv.job_id })}><Briefcase size={15} /> Job</button>}
          </div>
          <div className="qp-scroll">
            <article className={`qp is-invoice cy-keep-light${canEdit ? ' is-editable' : ''}`} aria-label={`Invoice ${inv.invoice_number || ''}`}>
              <header className="qp-head">
                <div className="qp-brand">EMPIRE WORKROOM</div>
                <div className="qp-headmeta">Custom upholstery &amp; fabrication<br /><b>{inv.business_unit === 'woodcraft' ? 'WoodCraft' : 'Workroom'}</b></div>
                <div className="qp-headright">{inv.invoice_number}<b>Invoice</b></div>
              </header>
              <div className="qp-body">
                <div className="qp-title">
                  <h2>Invoice&nbsp; {inv.invoice_number}</h2>
                  <small>Date: {fmtDate(inv.invoice_date || inv.created_at)} · Due: {fmtDate(inv.due_date) || '—'}</small>
                </div>
                <div className="qp-parties">
                  <div>
                    <div className="qp-label">Bill to</div>
                    {client ? (
                      <button
                        type="button"
                        onClick={() => openRecord({ type: 'customer', id: inv.customer_id || inv.client_id || client })}
                        className="text-left font-bold text-[#b8960c] hover:underline cursor-pointer bg-transparent border-0 p-0 block"
                        title="View customer record"
                      >
                        {client}
                      </button>
                    ) : (
                      <b>—</b>
                    )}
                    {inv.client_address && <span>{inv.client_address}</span>}
                    {inv.client_phone && <span>Tel: {inv.client_phone}</span>}
                    {inv.client_email && <span>{inv.client_email}</span>}
                  </div>
                  <div><div className="qp-label">Terms</div><b>{inv.terms || '—'}</b><span>Status: {status.replace(/_/g, ' ')}</span></div>
                </div>
                <DocPaper items={items} fields={FIELDS} amountOf={lineAmount} editable={canEdit} onRequestEdit={editable ? () => setEditMode(true) : undefined}
                  onChange={change} onRemove={remove} onMove={move} onAdd={add} photoKey={`empire.roomPhotos.inv.${inv.id}`} />
                {items.length === 0 && <div className="qp-empty">No line items.{canEdit ? ' Use "Add room" to start.' : ''}</div>}
                <div className="qp-totals" aria-label="Totals">
                  <div className="row"><span>Subtotal</span><b>{money2(subtotal)}</b></div>
                  {discount > 0 && <div className="row"><span>Discount</span><b>-{money2(discount)}</b></div>}
                  <div className="row"><span className="qp-inl">Tax{canEdit ? <><input type="number" step="0.1" value={taxRate} onChange={e => { setTaxRate(parseFloat(e.target.value) || 0); setDirty(true); }} aria-label="Tax rate percent" />%</> : ` (${taxRate}%)`}</span><b>{money2(dirty ? tax : Number(inv.tax_amount || 0))}</b></div>
                  <div className="row is-total"><span>Total</span><b>{money2(total)}</b></div>
                  {Number(inv.deposit_required || 0) > 0 && <div className="row"><span>Deposit required</span><b>{money2(Number(inv.deposit_required))}</b></div>}
                  <div className="row"><span>Paid</span><b>{paid ? `-${money2(paid)}` : '—'}</b></div>
                  <div className="row is-total"><span>Balance due</span><b>{money2(balance)}</b></div>
                </div>
                {Array.isArray(inv.payments) && inv.payments.length > 0 && (
                  <div className="qp-notes" style={{ gridTemplateColumns: '1fr' }}>
                    <div><div className="qp-label">Payments</div>
                      {inv.payments.map((p: any, i: number) => <p key={p.id || i} style={{ margin: '2px 0' }}>{fmtDate(p.payment_date || p.created_at)} · {money2(Number(p.amount || 0))} · {p.method || p.payment_method || ''}</p>)}
                    </div>
                  </div>
                )}
                <div className="qp-notes">
                  <div><div className="qp-label">Notes</div>{canEdit ? <textarea rows={3} value={notes} onChange={e => { setNotes(e.target.value); setDirty(true); }} aria-label="Notes" /> : <p style={{ whiteSpace: 'pre-wrap' }}>{notes || '—'}</p>}</div>
                  <div><div className="qp-label">Terms</div>{canEdit ? <textarea rows={3} value={terms} onChange={e => { setTerms(e.target.value); setDirty(true); }} aria-label="Terms" /> : <p>{terms || '—'}</p>}</div>
                </div>
              </div>
              <footer className="qp-foot"><span>Empire Workroom · Thank you for your business</span><b>{status === 'draft' ? 'Draft — not sent' : status.replace(/_/g, ' ')}</b></footer>
            </article>
          </div>
        </div>
      )}
      <div className="dh-sticky-spacer" aria-hidden />
    </div>
  );
}
