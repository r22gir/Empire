'use client';

import { useState, type CSSProperties } from 'react';
import { Maximize2, Minimize2, X } from 'lucide-react';
import ChatChartBlock from '../ChatChartBlock';
import InlineDrawing from '../InlineDrawing';
import QuoteCard from '../business/quotes/QuoteCard';
import type { ChartSpec } from '../../lib/chatContent';

export type StageArtifact = {
  id: string;
  kind: string;
  title: string;
  narration?: string;
  brand?: string;
  payload?: Record<string, unknown>;
};

function asChart(payload: Record<string, unknown> | undefined): ChartSpec | null {
  if (!payload || payload.empty) return null;
  const type = String(payload.type || '');
  if (type !== 'bar' && type !== 'line' && type !== 'pie') return null;
  const labels = Array.isArray(payload.labels) ? payload.labels.map(String) : [];
  const data = Array.isArray(payload.data) ? payload.data.map((v) => Number(v) || 0) : [];
  if (!labels.length || labels.length !== data.length) return null;
  return { type, labels, data, title: payload.title ? String(payload.title) : undefined };
}

function publicUrl(value: unknown): string {
  const text = String(value || '').trim();
  if (!text || text.includes('/home/') || text.startsWith('file:')) return '';
  if (text.startsWith('https://') || text.startsWith('http://') || text.startsWith('/')) return text;
  return '';
}

function Diagram({ source }: { source: string }) {
  const lines = source.split('\n').map((line) => line.trim()).filter(Boolean);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {lines.map((line, i) => {
        const parts = line.split(/-->|---|==>/).map((part) => part.replace(/[\[\]\(\)]/g, '').trim()).filter(Boolean);
        if (parts.length < 2) {
          return (
            <div key={i} style={{
              alignSelf: 'flex-start', padding: '8px 12px', borderRadius: 8,
              border: '1px solid #e5e2dc', background: '#fff', fontSize: 13,
            }}>
              {line}
            </div>
          );
        }
        return (
          <div key={i} style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
            {parts.map((part, j) => (
              <span key={j} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {j > 0 && <span style={{ color: '#b8960c', fontWeight: 700 }}>→</span>}
                <span style={{
                  padding: '8px 12px', borderRadius: 8,
                  border: '1px solid #e5e2dc', background: '#fff', fontSize: 13,
                }}>
                  {part}
                </span>
              </span>
            ))}
          </div>
        );
      })}
    </div>
  );
}

function DraftCard({ payload }: { payload: Record<string, unknown> }) {
  const items = Array.isArray(payload.line_items) ? payload.line_items : [];
  const missing = Array.isArray(payload.missing) ? payload.missing : [];
  return (
    <div style={{ padding: 12, borderRadius: 12, background: '#fff', border: '1px solid #e5e2dc' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 6 }}>
        <strong style={{ fontSize: 13 }}>
          {payload.quote_number ? `Draft ${String(payload.quote_number)}` : 'Voice draft'} · not sent
        </strong>
        <span style={{ fontSize: 11, color: '#888' }}>{String(payload.client_brand || 'Empire Workroom')}</span>
      </div>
      {items.map((item: any, idx: number) => (
        <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '2px 0' }}>
          <span>{item.description}</span>
          <span>{item.amount != null ? `$${Number(item.amount).toFixed(2)}` : ''}</span>
        </div>
      ))}
      {payload.total != null && (
        <div style={{ fontSize: 13, fontWeight: 700, marginTop: 4 }}>Total ${Number(payload.total).toFixed(2)}</div>
      )}
      {missing.length > 0 && (
        <ul style={{ margin: '8px 0 0', paddingLeft: 18, fontSize: 12 }}>
          {missing.map((row: any, idx: number) => <li key={row.id || idx}>{row.label || String(row)}</li>)}
        </ul>
      )}
      <p style={{ margin: '8px 0 0', fontSize: 11, color: '#888' }}>Draft stays here until you confirm a send.</p>
    </div>
  );
}

function TableBlock({ payload }: { payload: Record<string, unknown> }) {
  const columns = Array.isArray(payload.columns) ? payload.columns.map(String) : [];
  const rows = Array.isArray(payload.rows) ? payload.rows : [];
  if (!rows.length) return null;
  const keys = columns.length ? columns : Object.keys(rows[0] || {});
  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, background: '#fff' }}>
        <thead>
          <tr>
            {keys.map((key) => (
              <th key={key} style={{ textAlign: 'left', padding: '6px 8px', borderBottom: '1px solid #e5e2dc' }}>{key}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row: any, i: number) => (
            <tr key={i}>
              {keys.map((key) => (
                <td key={key} style={{ padding: '6px 8px', borderBottom: '1px solid #f0eee8' }}>{String(row?.[key] ?? '')}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ArtifactBody({ artifact }: { artifact: StageArtifact }) {
  const payload = artifact.payload || {};
  if (artifact.kind === 'chart') {
    const chart = asChart(payload);
    if (!chart) {
      return <p style={{ margin: 0, fontSize: 14 }}>{artifact.narration || 'No chart for that window.'}</p>;
    }
    return <ChatChartBlock chart={chart} />;
  }
  if (artifact.kind === 'diagram') {
    return <Diagram source={String(payload.source || '')} />;
  }
  if (artifact.kind === 'document') {
    const url = publicUrl(payload.url);
    if (!url) return <p style={{ margin: 0, fontSize: 13 }}>Document path is not public.</p>;
    return <iframe title={artifact.title} src={url} style={{ width: '100%', height: 360, border: '1px solid #e5e2dc', borderRadius: 8, background: '#fff' }} />;
  }
  if (artifact.kind === 'drawing') {
    return <InlineDrawing result={payload as any} />;
  }
  if (artifact.kind === 'image') {
    const urls = (Array.isArray(payload.urls) ? payload.urls : []).map(publicUrl).filter(Boolean);
    return (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {urls.map((url) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img key={url} src={url} alt="" style={{ maxWidth: '100%', maxHeight: 320, objectFit: 'contain', background: '#fff' }} />
        ))}
      </div>
    );
  }
  if (artifact.kind === 'table') return <TableBlock payload={payload} />;
  if (artifact.kind === 'quote') return <QuoteCard result={{ ...payload, sent: payload.sent }} />;
  if (artifact.kind === 'quote_draft') return <DraftCard payload={{ ...payload, sent: false }} />;
  return <p style={{ margin: 0, fontSize: 13 }}>{artifact.narration || artifact.title}</p>;
}

export default function PresentationStage({
  artifact,
  history,
  slideLabel,
  onSelect,
  onClose,
}: {
  artifact: StageArtifact | null;
  history: StageArtifact[];
  slideLabel?: string;
  onSelect: (artifact: StageArtifact) => void;
  onClose: () => void;
}) {
  const [full, setFull] = useState(false);
  if (!artifact && history.length === 0) return null;

  const panel = (
    <div className={full ? 'presentation-stage presentation-stage-full' : 'presentation-stage'}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <strong style={{ fontSize: 13, flex: 1 }}>{artifact?.title || 'Stage'}</strong>
        {slideLabel && <span style={{ fontSize: 11, color: '#888' }}>{slideLabel}</span>}
        {artifact?.brand && <span style={{ fontSize: 11, color: '#888' }}>{artifact.brand}</span>}
        <button type="button" onClick={() => setFull((v) => !v)} title={full ? 'Exit full screen' : 'Full screen'} style={iconBtn}>
          {full ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
        </button>
        <button type="button" onClick={onClose} title="Close" style={iconBtn}><X size={14} /></button>
      </div>
      <div style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
        {artifact ? <ArtifactBody artifact={artifact} /> : <p style={{ margin: 0, fontSize: 13, color: '#888' }}>Stage closed. Pick an item below.</p>}
      </div>
      {history.length > 0 && (
        <div style={{ display: 'flex', gap: 6, overflowX: 'auto', paddingTop: 8 }}>
          {history.map((item) => (
            <button
              key={item.id + item.title}
              type="button"
              onClick={() => onSelect(item)}
              style={{
                flex: '0 0 auto', fontSize: 11, padding: '4px 8px', borderRadius: 8, cursor: 'pointer',
                border: item.id === artifact?.id ? '1px solid #b8960c' : '1px solid #e5e2dc',
                background: item.id === artifact?.id ? '#fdf8eb' : '#fff',
              }}
            >
              {item.title || item.kind}
            </button>
          ))}
        </div>
      )}
    </div>
  );

  return panel;
}

const iconBtn: CSSProperties = {
  width: 28, height: 28, borderRadius: 8, border: '1px solid #e5e2dc',
  background: '#fff', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
};
