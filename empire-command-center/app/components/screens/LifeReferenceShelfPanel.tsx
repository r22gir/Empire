/**
 * LifeReferenceShelfPanel
 * v10 Phase 1 extension — displays saved LIFE references, localStorage only
 * No backend changes required.
 */

'use client';

import { useState, useEffect } from 'react';
import { Eye, ExternalLink, BookmarkMinus, BookOpen, Download } from 'lucide-react';
import { useShelfContext, type SavedLifeReference } from '../../hooks/useLifeReferenceShelf';

interface LifeReferenceShelfPanelProps {
  onOpenReference?: (ref: SavedLifeReference) => void;
  collapsed?: boolean;
}

export default function LifeReferenceShelfPanel({ onOpenReference, collapsed = false }: LifeReferenceShelfPanelProps) {
  const { saved, removeReference } = useShelfContext();
  const [isOpen, setIsOpen] = useState(!collapsed);

  const handleRemove = (key: string) => {
    removeReference(key);
  };

  const getOpenUrl = (ref: SavedLifeReference): string => {
    if (ref.cover_preview_url) return ref.cover_preview_url;
    if (ref.google_books_volume_id) {
      return `https://books.google.com/books?id=${ref.google_books_volume_id}`;
    }
    return '#';
  };

  if (saved.length === 0) {
    return null; // Nothing to show
  }

  return (
    <div style={{
      background: '#fff',
      border: '1.5px solid #e5e2dc',
      borderRadius: 12,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <button
        onClick={() => setIsOpen(v => !v)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 14px',
          background: '#f5f3ef',
          border: 'none',
          cursor: 'pointer',
          fontSize: 12,
          fontWeight: 700,
          color: '#374151',
          gap: 8,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <BookmarkMinus size={14} style={{ color: '#06b6d4' }} />
          Saved LIFE References
          <span style={{
            background: '#06b6d4',
            color: '#fff',
            borderRadius: '10px',
            padding: '1px 7px',
            fontSize: 10,
            fontWeight: 700,
          }}>
            {saved.length}
          </span>
        </div>
        <span style={{ color: '#9ca3af', fontSize: 11 }}>
          {isOpen ? '▲ collapse' : '▼ expand'}
        </span>
      </button>

      {/* Saved reference cards */}
      {isOpen && (
        <div style={{ padding: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {saved.map((ref) => {
            const key = ref.google_books_volume_id || ref.id;
            const openUrl = getOpenUrl(ref);
            return (
              <div
                key={key}
                style={{
                  display: 'flex',
                  gap: 10,
                  alignItems: 'center',
                  padding: '8px 10px',
                  background: '#faf9f7',
                  border: '1px solid #e5e2dc',
                  borderRadius: 8,
                }}
              >
                {/* Thumbnail */}
                <div style={{ flexShrink: 0 }}>
                  {ref.cover_thumbnail_url || ref.reference_cover_url ? (
                    <img
                      src={ref.cover_thumbnail_url || ref.reference_cover_url}
                      alt={ref.cover_subject}
                      style={{ width: 48, height: 60, objectFit: 'contain', borderRadius: 4, border: '1px solid #e5e2dc', background: '#f9f8f6' }}
                    />
                  ) : (
                    <div style={{ width: 48, height: 60, background: '#f5f3ef', borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <BookOpen size={16} style={{ color: '#9ca3af' }} />
                    </div>
                  )}
                </div>

                {/* Info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#1a1a1a', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {ref.cover_subject}
                  </div>
                  <div style={{ fontSize: 10, color: '#888', marginTop: 2 }}>
                    {ref.date} · {ref.volume_label || `Vol ${ref.volume}, No. ${ref.issue_number}`}
                  </div>
                  <div style={{ fontSize: 10, color: '#666', marginTop: 1 }}>
                    Saved {new Date(ref.savedAt).toLocaleDateString()}
                  </div>
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                  {/* Open Reference */}
                  <button
                    onClick={() => window.open(openUrl, '_blank', 'noopener')}
                    title="Open Reference (Google Books)"
                    style={{
                      padding: '5px 7px',
                      background: '#1e40af',
                      color: '#fff',
                      border: 'none',
                      borderRadius: 6,
                      cursor: 'pointer',
                      fontSize: 10,
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 3,
                    }}
                  >
                    <ExternalLink size={10} /> Open
                  </button>

                  {/* Preview (same as Open but for consistency) */}
                  <button
                    onClick={() => window.open(openUrl, '_blank', 'noopener')}
                    title="Preview on Google Books"
                    style={{
                      padding: '5px 7px',
                      background: '#f5f3ef',
                      color: '#374151',
                      border: '1px solid #e5e2dc',
                      borderRadius: 6,
                      cursor: 'pointer',
                      fontSize: 10,
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 3,
                    }}
                  >
                    <Eye size={10} /> Preview
                  </button>

                  {/* Download PDF — disabled, Google Books doesn't provide direct PDF for magazines */}
                  <button
                    disabled
                    title="PDF download not available from Google Books for LIFE magazine issues"
                    style={{
                      padding: '5px 7px',
                      background: '#f5f3ef',
                      color: '#ccc',
                      border: '1px solid #e5e2dc',
                      borderRadius: 6,
                      cursor: 'not-allowed',
                      fontSize: 10,
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 3,
                    }}
                  >
                    <Download size={10} /> PDF
                  </button>

                  {/* Remove */}
                  <button
                    onClick={() => handleRemove(key)}
                    title="Remove from saved references"
                    style={{
                      padding: '5px 7px',
                      background: '#fff',
                      color: '#ef4444',
                      border: '1px solid #fecaca',
                      borderRadius: 6,
                      cursor: 'pointer',
                      fontSize: 10,
                      fontWeight: 600,
                    }}
                  >
                    ✕
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}