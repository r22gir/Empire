'use client';

import { useState, type CSSProperties } from 'react';
import TranscriptOverlay, { type OverlayLine } from '../components/TranscriptOverlay';

const DEMO: OverlayLine[] = [
  { id: 'u1', role: 'user', text: 'Max, what is on the board this week?', final: true },
  { id: 'a1', role: 'assistant', text: 'Three installs and one Willard follow-up. I can walk the list out loud.', final: true },
];

export default function MaxLiveOverlayPreview() {
  const [open, setOpen] = useState(true);
  const [dark, setDark] = useState(false);

  return (
    <div
      data-theme={dark ? 'dark' : 'gold'}
      style={{
        minHeight: '100vh',
        background: dark ? '#0d0b08' : 'var(--bg)',
        color: dark ? '#eee' : 'var(--text)',
        position: 'relative',
        ['--panel' as string]: dark ? '#1a1812' : undefined,
        ['--text' as string]: dark ? '#eee' : undefined,
        ['--hover' as string]: dark ? '#241f16' : undefined,
        ['--card-bg' as string]: dark ? '#241f16' : undefined,
        ['--gold-light' as string]: dark ? '#2a2410' : undefined,
        ['--muted' as string]: dark ? '#aaa' : undefined,
        ['--dim' as string]: dark ? '#bbb' : undefined,
        ['--text-secondary' as string]: dark ? '#ccc' : undefined,
        ['--border' as string]: dark ? '#3a3426' : undefined,
      } as CSSProperties}
    >
      <div
        style={{
          height: '58vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(180deg, #1a1812 0%, #0d0b08 100%)',
          borderBottom: '2px solid var(--gold)',
        }}
      >
        <div
          data-testid="max-live-face-standin"
          style={{
            width: 160,
            height: 160,
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #b8960c, #d4af37)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontWeight: 800,
            letterSpacing: 2,
          }}
        >
          MAX
        </div>
      </div>
      <div style={{ padding: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button type="button" onClick={() => setOpen((o) => !o)} data-testid="preview-toggle">
          {open ? 'Hide transcript' : 'Show transcript'}
        </button>
        <button type="button" onClick={() => setDark((d) => !d)} data-testid="preview-theme">
          {dark ? 'Gold theme' : 'Dark theme'}
        </button>
      </div>
      <TranscriptOverlay
        open={open}
        title="Max · Live voice"
        status="Preview — dock Bottom so the face stays clear"
        lines={DEMO}
        onClose={() => setOpen(false)}
      />
    </div>
  );
}
