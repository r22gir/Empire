'use client';
/** Chat card for Max's open_final_doc tool: opens the doc in the shared viewer. */
import { FileText, ExternalLink } from 'lucide-react';
import { openDocViewer } from './viewerBus';
import './docs.css';

export default function MaxDocCard({ result }: { result: any }) {
  const open = (id?: string, title?: string, url?: string) => {
    if (id) openDocViewer({ id, title: title || 'Document' });
    else if (url) window.location.href = url;
  };
  const when = result.modified ? new Date(result.modified).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) : '';
  return (
    <div className="dh dh-card" style={{ marginTop: 8, maxWidth: 520 }}>
      <div className="dh-card-top">
        <FileText size={20} style={{ color: '#00e5ff', flexShrink: 0, marginTop: 2 }} />
        <div className="dh-card-main">
          <div className="dh-card-title">
            <button type="button" onClick={() => open(result.doc_id, result.title, result.viewer_url)}>{result.title}</button>
            {result.is_final && <span className="dh-badge">FINAL</span>}
            {result.version && <span className="dh-badge is-ver">{result.version}</span>}
          </div>
          <div className="dh-card-sub">{[result.client, result.quote_number, when].filter(Boolean).join(' · ')}</div>
        </div>
      </div>
      <div className="dh-actionbar">
        <button type="button" className="dh-act is-primary" onClick={() => open(result.doc_id, result.title, result.viewer_url)}><FileText size={15} /> Open viewer</button>
        {result.viewer_url && <a className="dh-act" href={result.viewer_url} target="_blank" rel="noopener" style={{ textDecoration: 'none' }}><ExternalLink size={15} /> New tab</a>}
      </div>
      {Array.isArray(result.alternatives) && result.alternatives.length > 0 && (
        <details className="dh-older">
          <summary>Other matches ({result.alternatives.length})</summary>
          <ul>
            {result.alternatives.map((a: any) => (
              <li key={a.doc_id || a.viewer_url}>
                <span className="dh-badge is-ver">{a.version}</span>
                <button type="button" onClick={() => open(a.doc_id, a.title, a.viewer_url)}>{a.title}</button>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
