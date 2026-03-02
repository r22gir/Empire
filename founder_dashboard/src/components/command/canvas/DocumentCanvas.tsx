'use client';
import { FileText, Search, ExternalLink, ZoomIn, ZoomOut } from 'lucide-react';
import { useState } from 'react';

interface DocumentRef {
  filename: string;
  type: string;
  url?: string;
}

interface Props {
  /** Document references found in the response */
  documents?: DocumentRef[];
  /** When a full document URL is provided, try to render it */
  documentUrl?: string;
  inline?: boolean;
}

function getDocIcon(type: string) {
  const ext = type.toLowerCase();
  if (ext === 'pdf') return '📄';
  if (ext.startsWith('doc')) return '📝';
  if (ext.startsWith('xls') || ext === 'csv') return '📊';
  if (ext.startsWith('ppt')) return '📽️';
  return '📎';
}

function getDocColor(type: string) {
  const ext = type.toLowerCase();
  if (ext === 'pdf') return '#ef4444';
  if (ext.startsWith('doc')) return '#3b82f6';
  if (ext.startsWith('xls') || ext === 'csv') return '#22c55e';
  if (ext.startsWith('ppt')) return '#f59e0b';
  return 'var(--text-muted)';
}

export default function DocumentCanvas({ documents, documentUrl, inline }: Props) {
  const [zoom, setZoom] = useState(100);

  if (documentUrl) {
    // Full document embed (PDF viewer)
    const isPdf = documentUrl.toLowerCase().endsWith('.pdf');

    return (
      <div
        className="rounded-xl overflow-hidden flex flex-col"
        style={{
          border: '1px solid var(--border)',
          height: inline ? 400 : '100%',
          minHeight: 300,
        }}
      >
        {/* Toolbar */}
        <div className="flex items-center justify-between px-3 py-1.5 shrink-0" style={{ background: 'var(--raised)', borderBottom: '1px solid var(--border)' }}>
          <div className="flex items-center gap-2">
            <FileText className="w-3.5 h-3.5" style={{ color: 'var(--gold)' }} />
            <span className="text-[10px] font-medium" style={{ color: 'var(--text-primary)' }}>
              Document Viewer
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setZoom(z => Math.max(50, z - 25))}
              className="p-0.5 rounded hover:bg-white/5 transition"
              style={{ color: 'var(--text-muted)' }}
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="text-[9px] min-w-[35px] text-center" style={{ color: 'var(--text-muted)' }}>
              {zoom}%
            </span>
            <button
              onClick={() => setZoom(z => Math.min(200, z + 25))}
              className="p-0.5 rounded hover:bg-white/5 transition"
              style={{ color: 'var(--text-muted)' }}
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <a
              href={documentUrl}
              target="_blank"
              rel="noreferrer"
              className="p-0.5 rounded hover:bg-white/5 transition ml-1"
              style={{ color: 'var(--text-muted)' }}
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>

        {/* Document content */}
        <div className="flex-1 overflow-auto" style={{ background: '#1a1a2e' }}>
          {isPdf ? (
            <iframe
              src={documentUrl}
              className="w-full h-full border-none"
              title="Document"
              style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'top left' }}
            />
          ) : (
            <div className="flex items-center justify-center h-full p-8">
              <div className="text-center">
                <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" style={{ color: 'var(--gold)' }} />
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Preview unavailable</p>
                <a
                  href={documentUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs mt-2 inline-flex items-center gap-1 hover:underline"
                  style={{ color: 'var(--gold)' }}
                >
                  Open document <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Document reference cards (found in text)
  if (!documents || documents.length === 0) return null;

  return (
    <div className={`flex flex-col gap-2 ${inline ? 'my-2' : ''}`}>
      {documents.map((doc, i) => (
        <div
          key={i}
          className="flex items-center gap-3 p-3 rounded-xl transition hover:brightness-110"
          style={{
            background: 'var(--raised)',
            border: '1px solid var(--border)',
          }}
        >
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center text-lg shrink-0"
            style={{ background: 'var(--elevated)' }}
          >
            {getDocIcon(doc.type)}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium truncate" style={{ color: 'var(--text-primary)' }}>
              {doc.filename}
            </p>
            <p className="text-[10px]" style={{ color: getDocColor(doc.type) }}>
              {doc.type.toUpperCase()}
            </p>
          </div>
          {doc.url && (
            <a
              href={doc.url}
              target="_blank"
              rel="noreferrer"
              className="p-1.5 rounded-lg hover:bg-white/5 transition"
              style={{ color: 'var(--text-muted)' }}
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
        </div>
      ))}
    </div>
  );
}
