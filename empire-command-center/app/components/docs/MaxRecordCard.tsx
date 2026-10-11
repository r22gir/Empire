'use client';
/** Chat card for Max's open_record / edit_quote_lines / convert_quote_to_invoice tools:
 *  one click opens the quote or invoice document page. Shows a confirmation note when Max
 *  is only previewing (nothing created or sent yet). */
import { FileText, Receipt, AlertTriangle } from 'lucide-react';
import { openRecord } from './recordBus';
import { money2 } from './DocPaper';
import './docs.css';

export default function MaxRecordCard({ tool, result }: { tool: string; result: any }) {
  const isInv = result.type === 'invoice';
  const id = result.id as string | undefined;
  const title = isInv ? (result.invoice_number || result.number || 'Invoice') : (result.number || result.quote_number || 'Quote');
  const sub = [result.client, result.project, result.status, result.total != null ? money2(Number(result.total)) : ''].filter(Boolean).join(' · ');
  return (
    <div className="dh dh-card" style={{ marginTop: 8, maxWidth: 560 }}>
      <div className="dh-card-top">
        {isInv ? <Receipt size={20} style={{ color: '#00e5ff', flexShrink: 0, marginTop: 2 }} /> : <FileText size={20} style={{ color: '#00e5ff', flexShrink: 0, marginTop: 2 }} />}
        <div className="dh-card-main">
          <div className="dh-card-title">
            {id ? <button type="button" onClick={() => openRecord({ type: isInv ? 'invoice' : 'quote', id })}>{title}</button> : <span>{title}</span>}
            {result.needs_confirmation && <span className="dh-badge is-ver">Needs your OK</span>}
            {result.status === 'draft' && <span className="dh-badge is-ver">Draft</span>}
          </div>
          {sub && <div className="dh-card-sub">{sub}</div>}
          {result.message && <div className="dh-card-sub" style={{ marginTop: 4 }}>{result.message}</div>}
          {Array.isArray(result.changes) && result.changes.length > 0 && <ul style={{ margin: '6px 0 0 16px', fontSize: 12.5 }}>{result.changes.map((c: string, i: number) => <li key={i}>{c}</li>)}</ul>}
          {Array.isArray(result.would_remove) && <ul style={{ margin: '6px 0 0 16px', fontSize: 12.5 }}>{result.would_remove.map((c: string, i: number) => <li key={i}><AlertTriangle size={11} /> {c}</li>)}</ul>}
          {Array.isArray(result.rooms) && result.rooms.length > 0 && <div className="dh-card-sub" style={{ marginTop: 4 }}>Rooms: {result.rooms.join(', ')}</div>}
        </div>
      </div>
      {id && (
        <div className="dh-actionbar">
          <button type="button" className="dh-act is-primary" onClick={() => openRecord({ type: isInv ? 'invoice' : 'quote', id })}>
            {isInv ? <Receipt size={15} /> : <FileText size={15} />} Open {isInv ? 'invoice' : 'quote'} page
          </button>
        </div>
      )}
      <span hidden data-tool={tool} />
    </div>
  );
}
