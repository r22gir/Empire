'use client';
/** Sticky job header for quote / invoice / job / doc pages: who, where, money, next step, Call / Map / WhatsApp. */
import { useEffect, useState } from 'react';
import { Phone, MapPin, MessageCircle, ArrowRight, Briefcase } from 'lucide-react';
import { jobHubHref } from '../jobhub/href';
import type { JobContext } from '../../lib/docs-hub/types';
import { DOCS_API } from '../../lib/docs-hub/types';
import { openRecord } from './recordBus';
import './docs.css';

const money = (n?: number | null) => n == null ? '—' : `$${Number(n).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
const statusLabel = (s?: string | null) => (s || '').replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase()) || '—';
const waDigits = (p?: string | null) => { const d = (p || '').replace(/\D/g, ''); return d.length === 10 ? `1${d}` : d; };

export function useJobContext(opts: { quote?: string | null; job?: string | null; invoice?: string | null }, refreshKey?: unknown) {
  const [ctx, setCtx] = useState<JobContext | null>(null);
  const key = `${opts.quote || ''}|${opts.job || ''}|${opts.invoice || ''}`;
  useEffect(() => {
    if (!opts.quote && !opts.job && !opts.invoice) { setCtx(null); return; }
    let dead = false;
    const p = new URLSearchParams();
    if (opts.quote) p.set('quote', opts.quote); if (opts.job) p.set('job', opts.job); if (opts.invoice) p.set('invoice', opts.invoice);
    if (refreshKey) p.set('refresh', '1');
    fetch(`${DOCS_API}/context?${p}`).then(r => r.ok ? r.json() : null).then(d => { if (!dead) setCtx(d?.found ? d : null); }).catch(() => {});
    return () => { dead = true; };
  }, [key, refreshKey]); // eslint-disable-line react-hooks/exhaustive-deps
  return ctx;
}

export default function JobHeader({ quote, job, invoice, context, refreshKey, className = '', hubLink = true }: { quote?: string | null; job?: string | null; invoice?: string | null; context?: JobContext | null; refreshKey?: unknown; className?: string; hubLink?: boolean }) {
  const fetched = useJobContext(context ? {} : { quote, job, invoice }, refreshKey);
  const c = context || fetched;
  if (!c) return null;
  const tel = (c.phone || '').replace(/[^\d+]/g, '');
  const owed = c.depositOwed || 0;
  const ids = [c.jobNumber && `Job ${c.jobNumber}`, c.quoteNumber].filter(Boolean) as string[];
  return (
    <header className={`dh dh-jobhead ${className}`} aria-label="Job summary">
      <div className="dh-jobhead-main">
        <div className="dh-jobhead-title">
          <button
            type="button"
            onClick={() => openRecord({ type: 'customer', id: (c as any).clientId || c.client || c.designer || 'client' })}
            className="hover:underline font-bold text-left bg-transparent border-0 p-0 text-[inherit] cursor-pointer"
            title="View customer record"
          >
            {c.client || c.designer || 'Client'}
          </button>
          {c.designer && c.designer !== c.client && <small>via {c.designer}</small>}
          {c.jobNumber && (
            <button
              type="button"
              onClick={() => openRecord({ type: 'job', id: String(c.jobId || c.jobNumber), title: c.jobNumber || undefined })}
              className="dh-num hover:underline cursor-pointer bg-transparent border-0 p-0"
              title="Open job folder"
            >
              Job {c.jobNumber}
            </button>
          )}
          {c.quoteNumber && (
            <button
              type="button"
              onClick={() => openRecord({ type: 'quote', id: String(c.quoteId || c.quoteNumber), title: c.quoteNumber || undefined })}
              className="dh-num hover:underline cursor-pointer bg-transparent border-0 p-0"
              title="Open quote"
            >
              {c.quoteNumber}
            </button>
          )}
        </div>
        <div className="dh-jobhead-meta">
          {c.address && <a href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(c.address)}`} target="_blank" rel="noopener noreferrer">{c.address}</a>}
          {c.phone && <a href={`tel:${tel}`} className="dh-num dh-hide-sm">{c.phone}</a>}
          <span>Status: <b style={{ color: '#f2fbff', fontWeight: 600 }}>{statusLabel(c.status)}</b></span>
        </div>
      </div>
      <div className="dh-jobhead-stats">
        <div className="dh-stat"><span>Total</span><b>{money(c.total)}</b></div>
        <div className={`dh-stat ${c.depositRequired ? (owed > 0 ? 'is-warn' : 'is-ok') : ''}`}>
          <span>Deposit {c.depositRequired ? (owed > 0 ? 'owed' : 'paid') : ''}</span>
          <b>{c.depositRequired ? (owed > 0 ? `${money(owed)} of ${money(c.depositRequired)}` : money(c.depositPaid)) : (c.depositPaid ? money(c.depositPaid) : 'None set')}</b>
        </div>
        <div className="dh-stat"><span>Install</span><b>{c.installDate ? new Date(c.installDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Not scheduled'}</b></div>
      </div>
      <div className="dh-contact">
        <a href={tel ? `tel:${tel}` : undefined} aria-disabled={!tel} aria-label="Call client"><Phone size={14} /> Call</a>
        <a href={c.address ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(c.address)}` : undefined} target="_blank" rel="noopener noreferrer" aria-disabled={!c.address} aria-label="Open address in Maps"><MapPin size={14} /> Map</a>
        <a href={tel ? `https://wa.me/${waDigits(c.phone)}` : undefined} target="_blank" rel="noopener noreferrer" aria-disabled={!tel} aria-label="WhatsApp client"><MessageCircle size={14} /> WhatsApp</a>
        {hubLink && (c.jobId || c.quoteId) && <a href={jobHubHref({ job: c.jobId, quote: c.quoteId })} aria-label="Open the job hub"><Briefcase size={14} /> Job hub</a>}
      </div>
      {c.nextStep && <div className="dh-next"><ArrowRight size={14} style={{ color: '#00e5ff' }} /> <span>Next step: <b>{c.nextStep}</b></span></div>}
    </header>
  );
}
