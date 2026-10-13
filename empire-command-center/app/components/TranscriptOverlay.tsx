'use client';

import { useCallback, useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import {
  DEFAULT_TRANSCRIPT_OVERLAY,
  clampFreePlacement,
  loadTranscriptOverlayPlacement,
  serializeTranscriptOverlayPlacement,
  TRANSCRIPT_OVERLAY_STORAGE_KEY,
  transcriptOverlayBoxStyle,
  type TranscriptDock,
  type TranscriptOverlayPlacement,
} from '../lib/transcriptOverlay';

export type OverlayLine = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  text: string;
  final?: boolean;
};

const DOCK_BUTTONS: { id: TranscriptDock; label: string }[] = [
  { id: 'bottom', label: 'Bottom' },
  { id: 'left', label: 'Left' },
  { id: 'right', label: 'Right' },
  { id: 'top', label: 'Top' },
];

function persist(placement: TranscriptOverlayPlacement) {
  try {
    window.localStorage.setItem(
      TRANSCRIPT_OVERLAY_STORAGE_KEY,
      serializeTranscriptOverlayPlacement(placement),
    );
  } catch {
    /* private mode */
  }
}

export default function TranscriptOverlay({
  open,
  title = 'Max · Live voice',
  status,
  lines,
  onClose,
  headerExtra,
}: {
  open: boolean;
  title?: string;
  status?: string;
  lines: OverlayLine[];
  onClose?: () => void;
  headerExtra?: ReactNode;
}) {
  const [placement, setPlacement] = useState<TranscriptOverlayPlacement>(DEFAULT_TRANSCRIPT_OVERLAY);
  const [viewport, setViewport] = useState({ width: 390, height: 844 });
  const panelRef = useRef<HTMLDivElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<{ startX: number; startY: number; origLeft: number; origTop: number } | null>(null);

  useEffect(() => {
    setPlacement(loadTranscriptOverlayPlacement(typeof window === 'undefined' ? null : window.localStorage));
    const measure = () => setViewport({ width: window.innerWidth, height: window.innerHeight });
    measure();
    window.addEventListener('resize', measure);
    return () => window.removeEventListener('resize', measure);
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 1e9 });
  }, [lines]);

  const setDock = (dock: TranscriptDock) => {
    const next = { ...placement, dock };
    setPlacement(next);
    persist(next);
  };

  const onDragStart = useCallback((e: React.PointerEvent) => {
    if ((e.target as HTMLElement).closest('button')) return;
    const el = panelRef.current;
    if (!el) return;
    e.preventDefault();
    const rect = el.getBoundingClientRect();
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      origLeft: rect.left,
      origTop: rect.top,
    };
    el.setPointerCapture(e.pointerId);

    const onMove = (ev: PointerEvent) => {
      if (!dragRef.current) return;
      const dx = ev.clientX - dragRef.current.startX;
      const dy = ev.clientY - dragRef.current.startY;
      const next = clampFreePlacement(
        dragRef.current.origLeft + dx,
        dragRef.current.origTop + dy,
        { width: rect.width, height: rect.height },
        { width: window.innerWidth, height: window.innerHeight },
      );
      setPlacement(next);
    };
    const onUp = (ev: PointerEvent) => {
      document.removeEventListener('pointermove', onMove);
      document.removeEventListener('pointerup', onUp);
      if (!dragRef.current) return;
      const dx = ev.clientX - dragRef.current.startX;
      const dy = ev.clientY - dragRef.current.startY;
      const next = clampFreePlacement(
        dragRef.current.origLeft + dx,
        dragRef.current.origTop + dy,
        { width: rect.width, height: rect.height },
        { width: window.innerWidth, height: window.innerHeight },
      );
      dragRef.current = null;
      setPlacement(next);
      persist(next);
    };
    document.addEventListener('pointermove', onMove);
    document.addEventListener('pointerup', onUp);
  }, []);

  if (!open) return null;

  const box = transcriptOverlayBoxStyle(placement, viewport);
  const shell: CSSProperties = {
    ...box,
    background: 'color-mix(in srgb, var(--panel) 94%, transparent)',
    color: 'var(--text)',
    border: '1px solid var(--gold-border)',
    borderRadius: 14,
    padding: 10,
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    boxShadow: '0 10px 30px rgba(0,0,0,0.28)',
    fontSize: 14,
    backdropFilter: 'blur(10px)',
  };

  return (
    <div
      ref={panelRef}
      style={shell}
      data-testid="max-live-transcript-overlay"
      data-dock={placement.dock}
      className="max-live-transcript"
    >
      <div
        onPointerDown={onDragStart}
        data-testid="max-live-transcript-drag"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 8,
          cursor: 'grab',
          touchAction: 'none',
          userSelect: 'none',
        }}
        title="Drag to move. Dock with the buttons."
      >
        <strong style={{ color: 'var(--gold)', fontSize: 13 }}>{title}</strong>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {headerExtra}
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close transcript"
              style={{ background: 'none', border: 'none', color: 'var(--muted)', fontSize: 18, cursor: 'pointer' }}
            >
              ×
            </button>
          )}
        </div>
      </div>

      <div
        role="toolbar"
        aria-label="Dock transcript"
        data-testid="max-live-transcript-docks"
        style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}
      >
        {DOCK_BUTTONS.map((d) => {
          const on = placement.dock === d.id;
          return (
            <button
              key={d.id}
              type="button"
              onClick={() => setDock(d.id)}
              data-testid={`max-live-transcript-dock-${d.id}`}
              aria-pressed={on}
              style={{
                fontSize: 10,
                fontWeight: on ? 700 : 500,
                padding: '4px 8px',
                minHeight: 28,
                borderRadius: 8,
                cursor: 'pointer',
                border: on ? '1px solid var(--gold)' : '1px solid var(--border)',
                background: on ? 'var(--gold-light)' : 'var(--hover)',
                color: on ? 'var(--gold)' : 'var(--text-secondary)',
              }}
            >
              {d.label}
            </button>
          );
        })}
      </div>

      {status && (
        <div style={{ fontSize: 12, color: 'var(--dim)' }} data-testid="max-live-transcript-status">
          {status}
        </div>
      )}

      <div
        ref={scrollRef}
        data-testid="max-live-transcript-lines"
        style={{ overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6, minHeight: 48 }}
      >
        {lines.length === 0 && (
          <div style={{ color: 'var(--muted)', fontSize: 12 }}>
            Transcript appears here. Drag the header or dock Bottom so it stays off the face.
          </div>
        )}
        {lines.map((l) => (
          <div
            key={l.id}
            data-role={l.role}
            style={{
              alignSelf: l.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '88%',
              background:
                l.role === 'user'
                  ? 'var(--card-bg)'
                  : l.role === 'assistant'
                    ? 'var(--gold-light)'
                    : 'transparent',
              color: l.role === 'system' ? 'var(--muted)' : 'var(--text)',
              border: l.role === 'system' ? 'none' : '1px solid var(--border)',
              borderRadius: 10,
              padding: l.role === 'system' ? 0 : '6px 9px',
              fontStyle: l.role === 'system' ? 'italic' : 'normal',
              opacity: l.final === false ? 0.8 : 1,
              fontSize: l.role === 'system' ? 12 : 14,
            }}
          >
            {l.text || '…'}
          </div>
        ))}
      </div>
    </div>
  );
}
