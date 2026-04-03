'use client';
import { useState } from 'react';
import { Download, Maximize2, X, RefreshCw, FileText } from 'lucide-react';

const API_BASE = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
  ? 'https://api.empirebox.store'
  : 'http://localhost:8000';

interface InlineDrawingProps {
  result: {
    svg?: string;
    svg_url?: string;
    pdf_url?: string;
    item_type?: string;
    item_name?: string;
    business_unit?: string;
    pages?: number;
    canvas_mode?: string;
  };
}

export default function InlineDrawing({ result }: InlineDrawingProps) {
  const [expanded, setExpanded] = useState(false);

  const svg = result.svg;
  const svgUrl = result.svg_url ? `${API_BASE}${result.svg_url}` : null;
  const pdfUrl = result.pdf_url ? `${API_BASE}${result.pdf_url}` : null;
  const itemName = result.item_name || result.item_type || 'Drawing';
  const bizUnit = result.business_unit;

  if (!svg) return null;

  return (
    <>
      {/* Inline drawing card */}
      <div style={{
        marginTop: 10, borderRadius: 10, overflow: 'hidden',
        border: '1px solid #e5e2dc', background: '#fff',
        maxWidth: 600,
      }}>
        {/* Header */}
        <div style={{
          padding: '8px 12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: '#fdf8eb', borderBottom: '1px solid #f0e6c0',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <FileText size={14} style={{ color: '#b8960c' }} />
            <span style={{ fontSize: 11, fontWeight: 700, color: '#b8960c' }}>
              {itemName.toUpperCase()}
            </span>
            {bizUnit && (
              <span style={{ fontSize: 9, color: '#999', fontWeight: 500 }}>
                {bizUnit === 'woodcraft' ? 'WoodCraft' : 'Workroom'}
              </span>
            )}
          </div>
          <button onClick={() => setExpanded(true)} title="Expand"
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: '#b8960c' }}>
            <Maximize2 size={14} />
          </button>
        </div>

        {/* SVG display */}
        <div style={{ padding: 8, background: '#fff', cursor: 'pointer' }} onClick={() => setExpanded(true)}>
          <div
            dangerouslySetInnerHTML={{ __html: svg }}
            style={{ width: '100%', maxHeight: 350, overflow: 'hidden' }}
          />
        </div>

        {/* Action buttons */}
        <div style={{
          padding: '8px 12px', display: 'flex', gap: 6, borderTop: '1px solid #f0ede6',
          flexWrap: 'wrap',
        }}>
          {pdfUrl && (
            <a href={pdfUrl} target="_blank" rel="noopener noreferrer"
              style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, padding: '4px 10px',
                background: '#b8960c', color: '#fff', borderRadius: 6, textDecoration: 'none',
                fontWeight: 600 }}>
              <Download size={10} /> PDF
            </a>
          )}
          {svgUrl && (
            <a href={svgUrl} target="_blank" rel="noopener noreferrer"
              style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, padding: '4px 10px',
                background: '#f5f3ef', color: '#666', borderRadius: 6, textDecoration: 'none',
                fontWeight: 600 }}>
              <Download size={10} /> SVG
            </a>
          )}
        </div>
      </div>

      {/* Lightbox modal */}
      {expanded && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)', zIndex: 9999,
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          padding: 20,
        }} onClick={() => setExpanded(false)}>
          <div style={{
            position: 'relative', maxWidth: '95vw', maxHeight: '90vh', background: '#fff',
            borderRadius: 12, overflow: 'auto', padding: 16,
          }} onClick={e => e.stopPropagation()}>
            <button onClick={() => setExpanded(false)} style={{
              position: 'absolute', top: 8, right: 8, background: '#f5f3ef', border: 'none',
              borderRadius: 8, padding: 6, cursor: 'pointer', zIndex: 1,
            }}>
              <X size={16} />
            </button>
            <div dangerouslySetInnerHTML={{ __html: svg }} style={{ maxWidth: '100%' }} />
            <div style={{ display: 'flex', gap: 8, marginTop: 12, justifyContent: 'center' }}>
              {pdfUrl && (
                <a href={pdfUrl} target="_blank" rel="noopener noreferrer"
                  style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, padding: '8px 16px',
                    background: '#b8960c', color: '#fff', borderRadius: 8, textDecoration: 'none', fontWeight: 600 }}>
                  <Download size={14} /> Download PDF
                </a>
              )}
              {svgUrl && (
                <a href={svgUrl} target="_blank" rel="noopener noreferrer"
                  style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, padding: '8px 16px',
                    background: '#f5f3ef', color: '#666', borderRadius: 8, textDecoration: 'none', fontWeight: 600 }}>
                  <Download size={14} /> Download SVG
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
