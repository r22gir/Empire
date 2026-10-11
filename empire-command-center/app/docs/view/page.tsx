'use client';
/**
 * Standalone viewer page: /docs/view?id=<docId> | ?src=<backend pdf>&title= | ?q=<natural language>
 * Used by shared links and by Max ("show me Nehal's final estimate"). Same auth as the app.
 */
import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import DocViewer from '../../components/docs/DocViewer';
import type { DocRef } from '../../components/docs/viewerBus';
import { DOCS_API } from '../../lib/docs-hub/types';
import '../../components/docs/docs.css';

function goBack() {
  const sameOrigin = typeof document !== 'undefined' && document.referrer.startsWith(window.location.origin);
  if (sameOrigin && window.history.length > 1) window.history.back();
  else window.location.href = '/?screen=final-docs';
}

function ViewerInner() {
  const sp = useSearchParams();
  const id = sp.get('id'); const src = sp.get('src'); const q = sp.get('q'); const title = sp.get('title') || '';
  const [ref, setRef] = useState<DocRef | null>(id ? { id, title } : src ? { src, title } : null);
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => {
    if (id) { setRef({ id, title }); return; }
    if (src) { setRef({ src, title }); return; }
    if (!q) { setMsg('No document selected.'); return; }
    fetch(`${DOCS_API}/resolve?q=${encodeURIComponent(q)}`).then(r => r.json()).then(d => {
      if (d.found && d.doc) setRef({ id: d.doc.id, title: d.doc.title, kind: d.doc.kind });
      else setMsg(d.message || `No document matched “${q}”.`);
    }).catch(() => setMsg('Could not reach the document service.'));
  }, [id, src, q, title]);
  if (msg) return (
    <div className="dh dh-viewer is-page"><div className="dh-viewer-msg">{msg}<br /><br />
      <a href={`/?screen=final-docs${q ? `&q=${encodeURIComponent(q)}` : ''}`} className="dh-act" style={{ textDecoration: 'none' }}>Open Final Docs</a></div></div>
  );
  if (!ref) return <div className="dh dh-viewer is-page"><div className="dh-viewer-msg">Finding the document…</div></div>;
  return <DocViewer initial={ref} mode="page" onBack={goBack} />;
}

export default function DocViewPage() {
  return <Suspense fallback={<div className="dh dh-viewer is-page"><div className="dh-viewer-msg">Loading…</div></div>}><ViewerInner /></Suspense>;
}
