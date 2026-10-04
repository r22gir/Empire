'use client';
/**
 * Quote document workspace: the quote builder lives inside a page that looks like the
 * Empire Workroom estimate PDF. Click a line to edit, add / move lines by room, totals update
 * live. Saving writes the same line items (in room order) that the client PDF prints.
 */
import type { ReactNode } from 'react';
import { Pencil, Eye, Save, Undo2, Loader2, Plus, Receipt, FileText, Lock } from 'lucide-react';
import DocPaper, { money2 } from './DocPaper';
import './paper.css';

export interface QuoteDocProps {
  quote: any;
  items: any[];
  amountOf: (i: any) => number;
  editable: boolean; locked: boolean; lockReason?: string;
  editMode: boolean; setEditMode: (v: boolean) => void;
  dirty: boolean; saving: boolean; onSave: () => void; onDiscard: () => void;
  onChange: (idx: number, field: string, value: any) => void; onRemove: (idx: number) => void;
  onMove: (idx: number, room: string) => void; onAdd: (room: string) => void;
  totals: { subtotal: number; discount: number; tax: number; total: number; deposit: number };
  discountAmt: number; setDiscountAmt: (n: number) => void; discountType: 'dollar' | 'percent'; toggleDiscountType: () => void;
  taxRate: number; setTaxRate: (n: number) => void; depositPct: number; setDepositPct: (n: number) => void;
  notes: string; setNotes: (s: string) => void; terms: string; setTerms: (s: string) => void;
  photos?: { url: string; label: string }[];
  onConvert?: () => void; convertLabel?: string; convertDisabledReason?: string | null; converting?: boolean;
  onShowPdf?: () => void;
  extraTools?: ReactNode;
}

const fmtDate = (s?: string) => { const d = s ? new Date(/^\d{4}-\d{2}-\d{2}$/.test(s) ? `${s}T12:00:00` : s.replace(' ', 'T')) : new Date(); return isNaN(d.getTime()) ? '' : d.toLocaleDateString('en-US', { month: 'long', day: '2-digit', year: 'numeric' }); };

export default function QuoteDocument(p: QuoteDocProps) {
  const q = p.quote || {};
  const canEdit = p.editable && p.editMode;
  const project = q.project_name || '';
  const site = q.project_address || q.customer_address || '';
  const status = String(q.status || 'draft');
  return (
    <div className="qp-wrap">
      <div className="dh qp-toolbar" role="toolbar" aria-label="Document editing">
        <span className="qp-state">
          <i className={`qp-dot${p.locked ? ' is-locked' : p.dirty ? ' is-dirty' : ''}`} />
          {p.locked ? <><Lock size={13} /> <b>Locked</b> {p.lockReason}</> : p.dirty ? <><b>Unsaved changes</b> · new total {money2(p.totals.total)}</> : canEdit ? <><b>Editing on the page</b> · click any line</> : <><b>Saved</b> · click a line or Edit to change it</>}
        </span>
        {!p.locked && (p.editMode
          ? <button type="button" className="dh-act" onClick={() => p.setEditMode(false)}><Eye size={15} /> Done</button>
          : <button type="button" className="dh-act is-primary" onClick={() => p.setEditMode(true)}><Pencil size={15} /> Edit</button>)}
        {canEdit && <button type="button" className="dh-act" onClick={() => { const n = window.prompt('New room name (e.g. PRIMARY BEDROOM)'); if (n && n.trim()) p.onAdd(n.trim().replace(/\s+—\s+/g, ' - ')); }}><Plus size={15} /> Add room</button>}
        {p.dirty && <button type="button" className="dh-act" onClick={p.onDiscard} disabled={p.saving}><Undo2 size={15} /> Discard</button>}
        {p.dirty && <button type="button" className="dh-act is-primary" onClick={p.onSave} disabled={p.saving}>{p.saving ? <Loader2 size={15} className="animate-spin" /> : <Save size={15} />} Save</button>}
        {p.onShowPdf && <button type="button" className="dh-act" onClick={p.onShowPdf}><FileText size={15} /> Actual PDF</button>}
        {p.onConvert && <button type="button" className="dh-act" onClick={p.onConvert} disabled={!!p.convertDisabledReason || p.converting || p.dirty} title={p.dirty ? 'Save first' : p.convertDisabledReason || 'Create a draft invoice from this quote'}>
          {p.converting ? <Loader2 size={15} className="animate-spin" /> : <Receipt size={15} />} {p.convertLabel || 'Convert to invoice'}</button>}
        {p.extraTools}
      </div>

      <div className="qp-scroll">
        <article className={`qp cy-keep-light${canEdit ? ' is-editable' : ''}`} aria-label={`Estimate ${q.quote_number || ''}`}>
          <header className="qp-head">
            <div className="qp-brand">EMPIRE WORKROOM</div>
            <div className="qp-headmeta">{[q.customer_name, project].filter(Boolean).join(' · ')}<br /><b>Custom upholstery &amp; fabrication</b></div>
            <div className="qp-headright">{fmtDate(q.created_at)}<b>Estimate</b></div>
          </header>
          <div className="qp-body">
            {p.locked && <div className="qp-lock">This quote is {status.replace(/_/g, ' ')}, so its lines are locked. {p.lockReason}</div>}
            <div className="qp-title">
              <h2>Estimate&nbsp; {q.quote_number}</h2>
              <small>Date: {fmtDate(q.created_at)} · Valid: {q.valid_days || 30} days</small>
            </div>
            <div className="qp-parties">
              <div><div className="qp-label">Prepared for</div><b>{q.customer_name || '—'}</b>{q.customer_phone && <span>Tel: {q.customer_phone}</span>}{q.customer_email && <span>{q.customer_email}</span>}</div>
              <div><div className="qp-label">Project site</div><b>{site || '—'}</b>{project && <span>{project}</span>}</div>
            </div>

            <DocPaper items={p.items} amountOf={p.amountOf} editable={canEdit} onRequestEdit={p.editable ? () => p.setEditMode(true) : undefined}
              onChange={p.onChange} onRemove={p.onRemove} onMove={p.onMove} onAdd={p.onAdd} photos={p.photos} photoKey={`empire.roomPhotos.${q.id}`} />
            {p.items.length === 0 && <div className="qp-empty">No line items yet.{canEdit ? ' Use "Add room" or "Add a line" to start.' : ''}</div>}

            <div className="qp-totals" aria-label="Totals">
              <div className="row"><span>Subtotal</span><b>{money2(p.totals.subtotal)}</b></div>
              <div className="row"><span className="qp-inl">Discount{canEdit && <><input type="number" step="0.01" min="0" value={p.discountAmt || ''} placeholder="0" onChange={e => p.setDiscountAmt(parseFloat(e.target.value) || 0)} aria-label="Discount" />
                <button type="button" className="qp-addline" style={{ margin: 0 }} onClick={p.toggleDiscountType} aria-label="Toggle discount type">{p.discountType === 'dollar' ? '$' : '%'}</button></>}</span>
                <b>{p.totals.discount > 0 ? `-${money2(p.totals.discount)}` : '—'}</b></div>
              <div className="row"><span className="qp-inl">Tax{canEdit ? <><input type="number" step="0.1" value={p.taxRate} onChange={e => p.setTaxRate(parseFloat(e.target.value) || 0)} aria-label="Tax rate percent" />%</> : ` (${p.taxRate}%)`}</span><b>{money2(p.totals.tax)}</b></div>
              <div className="row is-total"><span>Total</span><b>{money2(p.totals.total)}</b></div>
              <div className="row"><span className="qp-inl">Deposit{canEdit ? <><input type="number" step="1" value={p.depositPct} onChange={e => p.setDepositPct(parseFloat(e.target.value) || 0)} aria-label="Deposit percent" />%</> : ` (${p.depositPct}%)`}</span><b>{money2(p.totals.deposit)}</b></div>
              <div className="row"><span>Balance on completion</span><b>{money2(p.totals.total - p.totals.deposit)}</b></div>
            </div>

            <div className="qp-notes">
              <div><div className="qp-label">Notes</div>{canEdit ? <textarea rows={3} value={p.notes} onChange={e => p.setNotes(e.target.value)} aria-label="Notes" /> : <p>{p.notes || '—'}</p>}</div>
              <div><div className="qp-label">Terms</div>{canEdit ? <textarea rows={3} value={p.terms} onChange={e => p.setTerms(e.target.value)} aria-label="Terms" /> : <p>{p.terms || '—'}</p>}</div>
            </div>
          </div>
          <footer className="qp-foot"><span>Empire Workroom · Custom upholstery &amp; fabrication · Hyattsville MD</span>{['draft', 'founder_review'].includes(status) ? <b>Draft — not for client issue</b> : <b>{status.replace(/_/g, ' ')}</b>}</footer>
        </article>
      </div>
    </div>
  );
}
