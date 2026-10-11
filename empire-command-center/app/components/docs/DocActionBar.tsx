'use client';
/**
 * Unified action bar for every doc, quote and invoice. Same order and style everywhere:
 *   Preview · Print · Download PDF · Share (copy link / WhatsApp / email draft) · Copy link · Versions
 * Desktop: inline (place it at the top). Phone (<=760px): sticky bar at the bottom when `sticky`.
 * Links point at the in-app viewer on this same host, so they keep the existing sign-in
 * (Cloudflare Access / Tailscale). Nothing here creates a public link or sends anything:
 * email opens a draft in the user's mail app, WhatsApp opens a share sheet.
 */
import { useEffect, useRef, useState } from 'react';
import { Eye, Printer, Download, Share2, Link2, History, MessageCircle, Mail, Copy } from 'lucide-react';
import { DOCS_API, viewerHref } from '../../lib/docs-hub/types';
import { openDocViewer, type DocRef } from './viewerBus';
import './docs.css';

export function docFileUrl(doc: DocRef, download = false): string {
  const p = new URLSearchParams();
  if (doc.id) p.set('id', doc.id); else if (doc.src) p.set('src', doc.src);
  if (doc.src && doc.filename) p.set('name', doc.filename);
  if (doc.src && doc.v) p.set('v', doc.v);
  if (download) p.set('download', '1');
  return `${DOCS_API}/file?${p.toString()}`;
}

export function absoluteViewerUrl(doc: DocRef): string {
  const rel = viewerHref({ id: doc.id, src: doc.id ? undefined : doc.src, title: doc.title });
  return typeof window === 'undefined' ? rel : `${window.location.origin}${rel}`;
}

async function copyText(text: string) {
  try { await navigator.clipboard.writeText(text); return true; } catch {
    const ta = document.createElement('textarea'); ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    let ok = false; try { ok = document.execCommand('copy'); } catch { ok = false; }
    document.body.removeChild(ta); return ok;
  }
}

const waNumber = (phone?: string | null) => {
  const d = (phone || '').replace(/\D/g, '');
  return d.length === 10 ? `1${d}` : d.length === 11 && d.startsWith('1') ? d : '';
};

export interface DocActionBarProps {
  doc: DocRef | null;
  sticky?: boolean;              // phone: fixed bar at the bottom
  showPreview?: boolean;         // hide inside the viewer itself
  onPreview?: () => void;
  versionsCount?: number;
  onVersions?: () => void;
  clientPhone?: string | null;
  clientEmail?: string | null;
  shareText?: string;            // message body used for WhatsApp / email
  className?: string;
  loading?: boolean;             // e.g. while the quote is being saved
  /** 'inline' (default) puts the phone spacer right after the bar; 'none' when the page renders its own <div className="dh-sticky-spacer"/> at the end */
  spacer?: 'inline' | 'none';
}

export default function DocActionBar({ doc, sticky = false, showPreview = true, onPreview, versionsCount, onVersions, clientPhone, clientEmail, shareText, className = '', loading, spacer = 'inline' }: DocActionBarProps) {
  const [menu, setMenu] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!menu) return;
    const close = (e: MouseEvent) => { if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenu(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setMenu(false); };
    document.addEventListener('mousedown', close); document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', esc); };
  }, [menu]);
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 2600); return () => clearTimeout(t); }, [toast]);

  const disabled = !doc || loading;
  const title = doc?.title || 'Document';
  const link = doc ? absoluteViewerUrl(doc) : '';
  const msg = `${shareText || title}\n${link}`;

  const preview = () => { if (!doc) return; if (onPreview) onPreview(); else openDocViewer(doc); };
  const print = () => {
    if (!doc) return;
    const url = docFileUrl(doc);
    const phone = window.matchMedia('(max-width: 760px)').matches || /iPhone|iPad|Android/i.test(navigator.userAgent);
    if (phone) { window.open(url, '_blank', 'noopener'); return; }
    const old = document.getElementById('dh-print-frame'); if (old) old.remove();
    const f = document.createElement('iframe');
    f.id = 'dh-print-frame'; f.style.position = 'fixed'; f.style.right = '0'; f.style.bottom = '0'; f.style.width = '0'; f.style.height = '0'; f.style.border = '0';
    f.src = url;
    f.onload = () => { try { f.contentWindow?.focus(); f.contentWindow?.print(); } catch { window.open(url, '_blank', 'noopener'); } };
    document.body.appendChild(f);
    setToast('Opening print dialog…');
  };
  const download = () => { if (!doc) return; const a = document.createElement('a'); a.href = docFileUrl(doc, true); a.rel = 'noopener'; document.body.appendChild(a); a.click(); a.remove(); };
  const copy = async () => { if (!doc) return; const ok = await copyText(link); setToast(ok ? 'Link copied. It opens for signed-in Empire users.' : 'Could not copy the link'); setMenu(false); };
  const wa = () => { if (!doc) return; const n = waNumber(clientPhone); window.open(`https://wa.me/${n}?text=${encodeURIComponent(msg)}`, '_blank', 'noopener'); setMenu(false); };
  const email = () => {
    if (!doc) return;
    const subject = encodeURIComponent(title);
    const body = encodeURIComponent(`Hi,\n\n${shareText || title}:\n${link}\n\nThank you,\nEmpire Workroom`);
    window.location.href = `mailto:${clientEmail || ''}?subject=${subject}&body=${body}`; // opens a draft only
    setMenu(false);
  };

  return (
    <>
      <div className={`dh dh-actionbar${sticky ? ' is-sticky-mobile' : ''} ${className}`} role="toolbar" aria-label="Document actions">
        {showPreview && <button type="button" className="dh-act is-primary" onClick={preview} disabled={disabled}><Eye size={15} /> Preview</button>}
        <button type="button" className="dh-act" onClick={print} disabled={disabled}><Printer size={15} /> Print</button>
        <button type="button" className="dh-act" onClick={download} disabled={disabled}><Download size={15} /> {doc?.kind === 'image' ? 'Download' : 'Download PDF'}</button>
        <div className="dh-menu-wrap" ref={menuRef}>
          <button type="button" className="dh-act" onClick={() => setMenu(m => !m)} disabled={disabled} aria-haspopup="menu" aria-expanded={menu}><Share2 size={15} /> Share</button>
          {menu && (
            <div className="dh-menu" role="menu">
              <button type="button" role="menuitem" onClick={copy}><Copy size={15} /> Copy link</button>
              <button type="button" role="menuitem" onClick={wa}><MessageCircle size={15} /> WhatsApp{waNumber(clientPhone) ? ' client' : ''}</button>
              <button type="button" role="menuitem" onClick={email}><Mail size={15} /> Email (opens a draft)</button>
              <div className="dh-menu-note">Links open this document in Empire and need the usual sign-in. Nothing is sent automatically.</div>
            </div>
          )}
        </div>
        <button type="button" className="dh-act" onClick={copy} disabled={disabled}><Link2 size={15} /> Copy link</button>
        <button type="button" className="dh-act" onClick={onVersions} disabled={disabled || !onVersions || (versionsCount ?? 0) < 2} title={(versionsCount ?? 0) < 2 ? 'Only one version' : 'Show versions'}>
          <History size={15} /> Versions{versionsCount ? <span className="dh-act-count">{versionsCount}</span> : null}
        </button>
      </div>
      {sticky && spacer === 'inline' && <div className="dh-sticky-spacer" aria-hidden />}
      {toast && <div className="dh dh-toast" role="status">{toast}</div>}
    </>
  );
}
