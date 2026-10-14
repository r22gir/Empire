'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { Box, Copy, Eye, Loader2, Link2, Lock, Trash2, UploadCloud, X } from 'lucide-react';
import {
  copyViewerLink,
  fetchViewerStatus,
  previewViewer,
  publishViewer,
  unpublishViewer,
  type ViewerPreview,
  type ViewerStatus,
} from '../../lib/jobViewer';

type Props = {
  jobId?: string | number | null;
  quoteId?: string | null;
  compact?: boolean;
};

export default function JobViewerButton({ jobId, quoteId, compact }: Props) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<ViewerStatus | null>(null);
  const [preview, setPreview] = useState<ViewerPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [pinOpen, setPinOpen] = useState<'publish' | 'unpublish' | null>(null);
  const [pin, setPin] = useState('');
  const [busy, setBusy] = useState(false);

  const loadStatus = useCallback(async () => {
    try {
      setStatus(await fetchViewerStatus(jobId, quoteId));
    } catch {
      setStatus(null);
    }
  }, [jobId, quoteId]);

  useEffect(() => { loadStatus(); }, [loadStatus]);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2400);
    return () => clearTimeout(t);
  }, [toast]);

  const openPreview = async () => {
    setOpen(true);
    setLoading(true);
    setError(null);
    try {
      const data = await previewViewer(jobId, quoteId);
      setPreview(data);
      setStatus(data.viewer);
    } catch (err: any) {
      setError(err?.message || 'Could not generate the 3D viewer');
    } finally {
      setLoading(false);
    }
  };

  const submitPin = async () => {
    if (!pin.trim() || !pinOpen) return;
    setBusy(true);
    setError(null);
    try {
      const result = pinOpen === 'publish'
        ? await publishViewer(pin.trim(), jobId, quoteId)
        : await unpublishViewer(pin.trim(), jobId, quoteId);
      setStatus(result.viewer);
      if (result.published && result.url) setToast('Published. Copy the link — nothing was sent.');
      if (!result.published) setToast('Unpublished. The public page is gone.');
      setPinOpen(null);
      setPin('');
    } catch (err: any) {
      setError(err?.message || 'Founder tap failed');
    } finally {
      setBusy(false);
    }
  };

  const onCopy = async () => {
    const url = status?.url;
    if (!url) { setToast('Publish first to get a public link.'); return; }
    const ok = await copyViewerLink(url);
    setToast(ok ? 'Link copied. Share it yourself — Max did not send it.' : 'Could not copy');
  };

  const published = !!status?.published && !!status.url;

  return (
    <>
      <button
        type="button"
        onClick={openPreview}
        title="Preview a 3D viewer from this job's measurements. Publish is a founder tap."
        style={{
          minHeight: compact ? 36 : 44,
          padding: compact ? '6px 10px' : '6px 14px',
          borderRadius: 8,
          fontSize: compact ? 11 : 12,
          fontWeight: 700,
          cursor: 'pointer',
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          background: published ? '#1c1910' : '#222',
          color: '#f5e6b8',
          border: '1px solid #b8960c',
          letterSpacing: 0.2,
        }}
      >
        <Box size={14} color="#d4af37" />
        3D viewer
        {published && <span style={{ color: '#22c55e', fontSize: 10, fontWeight: 800 }}>LIVE</span>}
      </button>

      {open && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="3D job viewer"
          onClick={(e) => { if (e.target === e.currentTarget) setOpen(false); }}
          style={{
            position: 'fixed', inset: 0, zIndex: 10050,
            background: 'rgba(18,18,22,0.72)', backdropFilter: 'blur(4px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 12,
          }}
        >
          <div style={{
            width: 'min(1100px, 100%)', height: 'min(88vh, 820px)',
            background: '#faf9f7', borderRadius: 16, overflow: 'hidden',
            border: '1px solid #ece8e0', boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
            display: 'flex', flexDirection: 'column',
          }}>
            <div style={{
              background: '#121214', color: '#fff', padding: '12px 16px',
              borderBottom: '2px solid #b8960c', display: 'flex',
              alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <span style={{
                  background: 'linear-gradient(135deg,#b8960c,#d4af37)', color: '#121214',
                  fontSize: 10, fontWeight: 800, padding: '3px 8px', borderRadius: 6, letterSpacing: 0.5,
                }}>EMPIRE WORKROOM</span>
                <strong style={{ fontSize: 15 }}>3D viewer</strong>
                <span style={{ fontSize: 12, color: published ? '#86efac' : '#fbbf24' }}>
                  {published ? 'Published' : 'Draft — not public'}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                <button type="button" onClick={openPreview} style={actBtn} disabled={loading}>
                  {loading ? <Loader2 size={14} className="animate-spin" /> : <Eye size={14} />} Preview
                </button>
                <button type="button" onClick={() => { setPin(''); setPinOpen('publish'); }} style={actBtn}>
                  <UploadCloud size={14} /> Publish
                </button>
                <button type="button" onClick={onCopy} style={actBtn} disabled={!published}>
                  {published ? <Copy size={14} /> : <Link2 size={14} />} Copy link
                </button>
                <button type="button" onClick={() => { setPin(''); setPinOpen('unpublish'); }} style={{ ...actBtn, opacity: published ? 1 : 0.5 }} disabled={!published}>
                  <Trash2 size={14} /> Unpublish
                </button>
                <button type="button" onClick={() => setOpen(false)} aria-label="Close" style={{ ...actBtn, minWidth: 40 }}>
                  <X size={16} />
                </button>
              </div>
            </div>

            {toast && (
              <div style={{ background: '#ecfdf5', color: '#166534', padding: '8px 14px', fontSize: 12, fontWeight: 600 }}>{toast}</div>
            )}
            {error && (
              <div style={{ background: '#fef2f2', color: '#991b1b', padding: '8px 14px', fontSize: 12 }}>{error}</div>
            )}
            <div style={{ padding: '8px 14px', fontSize: 11, color: '#6b4a24', background: '#fffdf8', borderBottom: '1px solid #ece8e0' }}>
              Preview is a draft. Publish is a founder tap only — nothing is sent to the client. Republish updates the same link.
            </div>

            <div style={{ flex: 1, minHeight: 0, background: '#f1ece1' }}>
              {loading && (
                <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6b4a24', gap: 8 }}>
                  <Loader2 size={18} className="animate-spin" /> Building scene from measurements…
                </div>
              )}
              {!loading && preview?.html && (
                <iframe
                  title="Empire Workroom 3D viewer preview"
                  srcDoc={preview.html}
                  style={{ width: '100%', height: '100%', border: 0, background: '#f1ece1' }}
                />
              )}
            </div>
          </div>
        </div>
      )}

      {pinOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="jv-pin-title"
          onClick={() => { if (!busy) { setPinOpen(null); setPin(''); } }}
          style={{
            position: 'fixed', inset: 0, zIndex: 10060, background: 'rgba(0,0,0,0.4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{ width: '100%', maxWidth: 400, background: '#faf9f7', borderRadius: 14, border: '1px solid #ece8e0', overflow: 'hidden' }}
          >
            <div style={{ padding: '14px 18px', borderBottom: '1px solid #ece8e0', display: 'flex', justifyContent: 'space-between' }}>
              <h3 id="jv-pin-title" style={{ margin: 0, fontSize: 14 }}>
                {pinOpen === 'publish' ? 'Publish 3D viewer (founder PIN)' : 'Unpublish 3D viewer (founder PIN)'}
              </h3>
              <button type="button" onClick={() => { if (!busy) { setPinOpen(null); setPin(''); } }} aria-label="Close" style={{ border: 0, background: 'transparent', cursor: 'pointer' }}>
                <X size={16} />
              </button>
            </div>
            <div style={{ padding: 16 }}>
              <p style={{ fontSize: 12, color: '#555', marginTop: 0 }}>
                Founder tap only. This does not email or text the client. {pinOpen === 'publish' ? 'The public page uses a stable unguessable link.' : 'Removes the public page.'}
              </p>
              <label style={{ fontSize: 10, fontWeight: 700, color: '#6b4a24', textTransform: 'uppercase' }}>Founder PIN</label>
              <input
                type="password"
                autoComplete="off"
                autoFocus
                value={pin}
                disabled={busy}
                onChange={(e) => setPin(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') submitPin(); }}
                placeholder="Enter founder PIN"
                style={{
                  width: '100%', marginTop: 6, padding: '10px 12px', borderRadius: 10,
                  border: '1px solid #ece8e0', fontFamily: 'ui-monospace, monospace', letterSpacing: '0.12em',
                }}
              />
            </div>
            <div style={{ padding: '12px 16px', borderTop: '1px solid #ece8e0', display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button type="button" onClick={() => { if (!busy) { setPinOpen(null); setPin(''); } }} style={{ ...actBtn, color: '#555', border: 0, background: 'transparent' }}>Cancel</button>
              <button type="button" onClick={submitPin} disabled={busy || !pin.trim()} style={{ ...actBtn, background: '#16a34a', color: '#fff', borderColor: '#16a34a' }}>
                {busy ? <Loader2 size={14} className="animate-spin" /> : <Lock size={14} />}
                {pinOpen === 'publish' ? 'Publish' : 'Unpublish'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

const actBtn: React.CSSProperties = {
  minHeight: 36,
  padding: '6px 10px',
  borderRadius: 8,
  fontSize: 12,
  fontWeight: 600,
  cursor: 'pointer',
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  background: '#222',
  color: '#fff',
  border: '1px solid #444',
};
