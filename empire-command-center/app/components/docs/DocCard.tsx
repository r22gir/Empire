'use client';
import { ChevronRight } from 'lucide-react';
import type { DocEntry, DocGroup } from '../../lib/docs-hub/types';
import { DOCS_API } from '../../lib/docs-hub/types';
import DocActionBar from './DocActionBar';
import { openDocViewer, type DocRef } from './viewerBus';
import './docs.css';

export const fmtShort = (iso?: string) => { if (!iso) return ''; const d = new Date(iso); return isNaN(d.getTime()) ? '' : d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }); };
export const toRef = (d: DocEntry): DocRef => ({ id: d.id, title: d.title, kind: d.kind, filename: d.filename });
export const thumbUrl = (d: DocEntry) => d.kind === 'image' ? (d.src || `${DOCS_API}/render?id=${encodeURIComponent(d.id)}`) : `${DOCS_API}/render?id=${encodeURIComponent(d.id)}&page=1&w=160`;

export default function DocCard({ group, showClient = false, phone, email }: { group: DocGroup; showClient?: boolean; phone?: string | null; email?: string | null }) {
  const d = group.final;
  const sub = [showClient ? (d.client || d.designer) : null, d.quoteNumber, d.invoiceNumber, fmtShort(d.modified), d.source].filter(Boolean).join(' · ');
  return (
    <article className="dh dh-card">
      <div className="dh-card-top">
        <button type="button" className={`dh-thumb${d.kind === 'image' ? ' is-img' : ''}`} style={{ backgroundImage: `url("${thumbUrl(d)}")` }} onClick={() => openDocViewer(toRef(d))} aria-label={`Preview ${d.title}`} />
        <div className="dh-card-main">
          <div className="dh-card-title">
            <button type="button" onClick={() => openDocViewer(toRef(d))}>{d.title}</button>
            {d.isFinal && <span className="dh-badge" title={d.finalReason === 'explicit' ? 'Marked final' : 'Latest version'}>FINAL</span>}
            <span className="dh-badge is-ver">{d.version}</span>
            {d.generated && <span className="dh-badge is-gen">Live</span>}
          </div>
          <div className="dh-card-sub">{sub}</div>
          <div className="dh-card-sub dh-muted" title={d.location} style={{ fontSize: 11.5 }}>{d.filename}</div>
        </div>
      </div>
      <DocActionBar doc={toRef(d)} versionsCount={group.older.length + 1}
        onVersions={group.older.length ? () => openDocViewer(toRef(d)) : undefined}
        clientPhone={phone} clientEmail={email} shareText={`${d.title}${d.client ? ` for ${d.client}` : ''}`} />
      {group.older.length > 0 && (
        <details className="dh-older">
          <summary><ChevronRight size={13} /> Older versions ({group.older.length})</summary>
          <ul>
            {group.older.map(o => (
              <li key={o.id}>
                <span className="dh-badge is-ver">{o.version}</span>
                <button type="button" onClick={() => openDocViewer(toRef(o))} title={o.location}>{o.filename}</button>
                <span className="dh-num" style={{ fontSize: 11 }}>{fmtShort(o.modified)}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </article>
  );
}
