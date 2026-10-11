'use client';
/**
 * Shared in-page viewer for PDFs and images (phone + desktop).
 * PDFs are rendered page-by-page to images on the Dell (poppler), so it works on
 * every phone browser without a PDF plugin; page thumbnails + zoom; download optional.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { X, ZoomIn, ZoomOut, Maximize2, ArrowLeft, Loader2 } from 'lucide-react';
import type { DocEntry, JobContext } from '../../lib/docs-hub/types';
import { DOCS_API } from '../../lib/docs-hub/types';
import DocActionBar from './DocActionBar';
import type { DocRef } from './viewerBus';
import './docs.css';

const fmtDate = (iso?: string) => { if (!iso) return ''; const d = new Date(iso); return isNaN(d.getTime()) ? '' : d.toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' }); };

function renderUrl(ref: DocRef, extra: Record<string, string | number>) {
  const p = new URLSearchParams();
  if (ref.id) p.set('id', ref.id); else if (ref.src) { p.set('src', ref.src); if (ref.v) p.set('v', ref.v); }
  for (const [k, v] of Object.entries(extra)) p.set(k, String(v));
  return `${DOCS_API}/render?${p.toString()}`;
}

export default function DocViewer({ initial, mode = 'modal', onClose, onBack }: { initial: DocRef; mode?: 'modal' | 'page' | 'embed'; onClose?: () => void; onBack?: () => void }) {
  const [ref, setRef] = useState<DocRef>(initial);
  const [meta, setMeta] = useState<{ doc?: DocEntry; versions?: DocEntry[]; context?: JobContext | null } | null>(null);
  const [info, setInfo] = useState<{ kind: 'pdf' | 'image'; pages: number; ratio?: number } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [cur, setCur] = useState(1);
  const [showVersions, setShowVersions] = useState(false);
  const [boxW, setBoxW] = useState(900);
  const pagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => { setRef(initial); }, [initial.id, initial.src, initial.v]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    let dead = false;
    setInfo(null); setErr(null); setCur(1); setShowVersions(false);
    if (ref.id) fetch(`${DOCS_API}?id=${encodeURIComponent(ref.id)}`).then(r => r.ok ? r.json() : null).then(d => { if (!dead) setMeta(d); }).catch(() => {});
    else setMeta(null);
    fetch(renderUrl(ref, { info: 1 })).then(async r => {
      const d = await r.json().catch(() => ({}));
      if (dead) return;
      if (!r.ok) setErr(d.error === 'file missing on disk' ? 'This file is listed but is no longer on disk.' : d.error === 'not found' ? 'This document is not in the index any more.' : `Could not open this document (${d.error || r.status}).`);
      else setInfo({ kind: d.kind, pages: d.pages || 1, ratio: d.ratio });
    }).catch(() => { if (!dead) setErr('Could not reach the document service.'); });
    return () => { dead = true; };
  }, [ref.id, ref.src, ref.v]); // eslint-disable-line react-hooks/exhaustive-deps

  // container width -> fit-to-width page size
  useEffect(() => {
    const el = pagesRef.current; if (!el) return;
    const ro = new ResizeObserver(() => setBoxW(el.clientWidth));
    ro.observe(el); setBoxW(el.clientWidth);
    return () => ro.disconnect();
  }, [info]);

  const pageW = Math.round(Math.max(200, Math.min(boxW - 24, 1100)) * zoom);
  const dpr = typeof window !== 'undefined' ? Math.min(2, window.devicePixelRatio || 1) : 1;
  const bucket = [800, 1200, 1600, 2000].find(b => b >= pageW * dpr) || 2000;

  // current page tracking
  useEffect(() => {
    const root = pagesRef.current; if (!root || !info || info.kind !== 'pdf') return;
    const io = new IntersectionObserver(es => {
      const vis = es.filter(e => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (vis) setCur(Number((vis.target as HTMLElement).dataset.page) || 1);
    }, { root, threshold: [0.25, 0.6] });
    root.querySelectorAll('[data-page]').forEach(n => io.observe(n));
    return () => io.disconnect();
  }, [info, pageW]);

  const goPage = (n: number) => { pagesRef.current?.querySelector(`[data-page="${n}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); };
  const zoomBy = useCallback((f: number) => setZoom(z => Math.max(0.4, Math.min(3, Math.round(z * f * 100) / 100))), []);

  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (mode === 'embed' || ['INPUT', 'TEXTAREA', 'SELECT'].includes(t?.tagName) || t?.isContentEditable) return;
      if (e.key === 'Escape' && mode === 'modal') onClose?.();
      if (e.key === '+' || e.key === '=') zoomBy(1.2);
      if (e.key === '-') zoomBy(1 / 1.2);
    };
    window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k);
  }, [mode, onClose, zoomBy]);

  const doc = meta?.doc;
  const ctx = meta?.context;
  const title = doc?.title || ref.title || 'Document';
  const sub = [doc?.client, doc?.designer && doc.designer !== doc.client ? doc.designer : null, doc?.version, fmtDate(doc?.modified)].filter(Boolean).join(' · ');
  const actionDoc: DocRef = useMemo(() => ({ ...ref, title, kind: info?.kind || doc?.kind || ref.kind, filename: doc?.filename || ref.filename }), [ref, title, info, doc]);
  const versions = meta?.versions || [];

  const body = (
    <div className={`dh dh-viewer${mode === 'page' ? ' is-page' : mode === 'embed' ? ' is-embed' : ''}`} role={mode === 'modal' ? 'dialog' : undefined} aria-modal={mode === 'modal' ? true : undefined} aria-label={title}>
      <div className="dh-viewer-top">
        {mode === 'page'
          ? <button type="button" className="dh-iconbtn" onClick={onBack} aria-label="Back"><ArrowLeft size={17} /></button>
          : null}
        <div className="dh-viewer-title">
          <b>{title}{doc?.isFinal && <span className="dh-badge" style={{ marginLeft: 8, verticalAlign: 'middle' }}>FINAL</span>}</b>
          <small>{sub || (ref.src ? 'Generated from the live record' : '')}</small>
        </div>
        {info?.kind === 'pdf' && <span className="dh-muted dh-num" style={{ fontSize: 12 }}>{cur} / {info.pages}</span>}
        <div className="dh-zoom" aria-label="Zoom">
          <button type="button" className="dh-iconbtn" onClick={() => zoomBy(1 / 1.2)} aria-label="Zoom out"><ZoomOut size={16} /></button>
          <b>{Math.round(zoom * 100)}%</b>
          <button type="button" className="dh-iconbtn" onClick={() => zoomBy(1.2)} aria-label="Zoom in"><ZoomIn size={16} /></button>
          <button type="button" className="dh-iconbtn" onClick={() => setZoom(1)} aria-label="Fit to width"><Maximize2 size={15} /></button>
        </div>
        {mode === 'modal' && <button type="button" className="dh-iconbtn" onClick={onClose} aria-label="Close viewer"><X size={18} /></button>}
      </div>
      {mode !== 'embed' && <DocActionBar doc={err ? null : actionDoc} sticky showPreview={false} versionsCount={versions.length || undefined}
        onVersions={versions.length > 1 ? () => setShowVersions(v => !v) : undefined}
        clientPhone={ctx?.phone} clientEmail={ctx?.email} shareText={`${title}${ctx?.client ? ` for ${ctx.client}` : ''}`} />}
      {showVersions && versions.length > 1 && (
        <div className="dh-versions" role="listbox" aria-label="Versions">
          {versions.map(v => (
            <button key={v.id} type="button" className={v.id === ref.id ? 'is-on' : ''} role="option" aria-selected={v.id === ref.id}
              onClick={() => { setRef({ id: v.id, title: v.title, kind: v.kind, filename: v.filename }); setShowVersions(false); }}>
              {v.isFinal && <span className="dh-badge">FINAL</span>}
              <span className="dh-num">{v.version}</span>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{v.filename}</span>
              <small>{fmtDate(v.modified)}</small>
            </button>
          ))}
        </div>
      )}
      <div className="dh-viewer-body">
        {info?.kind === 'pdf' && info.pages > 1 && (
          <nav className="dh-thumbs" aria-label="Pages">
            {Array.from({ length: info.pages }, (_, i) => i + 1).map(n => (
              <button key={n} type="button" className={n === cur ? 'is-on' : ''} onClick={() => goPage(n)} aria-label={`Page ${n}`}>
                <img src={renderUrl(ref, { page: n, w: 160 })} alt="" loading="lazy" style={{ aspectRatio: `1 / ${info.ratio || 1.294}` }} />
                <span>{n}</span>
              </button>
            ))}
          </nav>
        )}
        <div className="dh-pages" ref={pagesRef}>
          {err && <div className="dh-viewer-msg">{err}</div>}
          {!err && !info && <div className="dh-viewer-msg"><Loader2 size={22} className="animate-spin" style={{ color: '#00e5ff' }} /><br />Opening…</div>}
          {info?.kind === 'pdf' && Array.from({ length: info.pages }, (_, i) => i + 1).map(n => (
            <img key={`${n}-${bucket}`} data-page={n} className="dh-pageimg" src={renderUrl(ref, { page: n, w: bucket })} alt={`${title}, page ${n}`}
              loading={n <= 2 ? 'eager' : 'lazy'} style={{ width: pageW, aspectRatio: `1 / ${info.ratio || 1.294}` }} />
          ))}
          {info?.kind === 'image' && (
            <img className="dh-pageimg" src={ref.src && !ref.id ? ref.src : renderUrl(ref, {})} alt={title} style={{ width: pageW, height: 'auto', background: '#000' }} />
          )}
        </div>
      </div>
    </div>
  );
  if (mode === 'page' || mode === 'embed') return body;
  return <div className="dh-viewer-overlay" onMouseDown={e => { if (e.target === e.currentTarget) onClose?.(); }}>{body}</div>;
}
