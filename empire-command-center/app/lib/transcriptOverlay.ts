/**
 * Placement for the Max Live voice transcript overlay.
 *
 * Default is a lower-third (`bottom`) so the box sits under a typical
 * Simli / TalkingHead face crop instead of covering the mouth / eyes.
 * Users can dock it or drag it (`free`); the last choice is persisted.
 */

export type TranscriptDock = 'bottom' | 'left' | 'right' | 'top' | 'free';

export type TranscriptOverlayPlacement = {
  dock: TranscriptDock;
  /** 0–1 viewport X used when dock === 'free' (panel top-left). */
  x: number;
  /** 0–1 viewport Y used when dock === 'free'. */
  y: number;
};

export const TRANSCRIPT_OVERLAY_STORAGE_KEY = 'empire.maxLive.transcriptOverlay.v1';

/** Lower-third: below the face, above the live-call mic. */
export const DEFAULT_TRANSCRIPT_OVERLAY: TranscriptOverlayPlacement = {
  dock: 'bottom',
  x: 0.5,
  y: 0.86,
};

const DOCKS = new Set<TranscriptDock>(['bottom', 'left', 'right', 'top', 'free']);

export function isTranscriptDock(value: unknown): value is TranscriptDock {
  return typeof value === 'string' && DOCKS.has(value as TranscriptDock);
}

export function clamp01(n: number): number {
  if (!Number.isFinite(n)) return 0;
  return Math.min(1, Math.max(0, n));
}

export function coversAvatarFace(dock: TranscriptDock): boolean {
  return dock === 'top';
}

export function parseTranscriptOverlayPlacement(raw: unknown): TranscriptOverlayPlacement {
  if (!raw || typeof raw !== 'object') return { ...DEFAULT_TRANSCRIPT_OVERLAY };
  const rec = raw as Record<string, unknown>;
  const dock = isTranscriptDock(rec.dock) ? rec.dock : DEFAULT_TRANSCRIPT_OVERLAY.dock;
  return {
    dock,
    x: typeof rec.x === 'number' ? clamp01(rec.x) : DEFAULT_TRANSCRIPT_OVERLAY.x,
    y: typeof rec.y === 'number' ? clamp01(rec.y) : DEFAULT_TRANSCRIPT_OVERLAY.y,
  };
}

export function loadTranscriptOverlayPlacement(
  storage?: Pick<Storage, 'getItem'> | null,
): TranscriptOverlayPlacement {
  try {
    const raw = storage?.getItem(TRANSCRIPT_OVERLAY_STORAGE_KEY);
    if (!raw) return { ...DEFAULT_TRANSCRIPT_OVERLAY };
    return parseTranscriptOverlayPlacement(JSON.parse(raw));
  } catch {
    return { ...DEFAULT_TRANSCRIPT_OVERLAY };
  }
}

export function serializeTranscriptOverlayPlacement(p: TranscriptOverlayPlacement): string {
  return JSON.stringify(parseTranscriptOverlayPlacement(p));
}

export type ViewportBox = { width: number; height: number };

/** Keep a free-drag panel fully on screen (12px gutter). */
export function clampFreePlacement(
  xPx: number,
  yPx: number,
  panel: ViewportBox,
  viewport: ViewportBox,
  gutter = 12,
): TranscriptOverlayPlacement {
  const maxX = Math.max(gutter, viewport.width - panel.width - gutter);
  const maxY = Math.max(gutter, viewport.height - panel.height - gutter);
  const x = Math.min(maxX, Math.max(gutter, xPx));
  const y = Math.min(maxY, Math.max(gutter, yPx));
  const denomX = Math.max(1, viewport.width - gutter * 2);
  const denomY = Math.max(1, viewport.height - gutter * 2);
  return {
    dock: 'free',
    x: clamp01((x - gutter) / denomX),
    y: clamp01((y - gutter) / denomY),
  };
}

export function freePlacementToPixels(
  placement: TranscriptOverlayPlacement,
  panel: ViewportBox,
  viewport: ViewportBox,
  gutter = 12,
): { left: number; top: number } {
  const maxX = Math.max(gutter, viewport.width - panel.width - gutter);
  const maxY = Math.max(gutter, viewport.height - panel.height - gutter);
  const left = gutter + placement.x * Math.max(0, viewport.width - panel.width - gutter * 2);
  const top = gutter + placement.y * Math.max(0, viewport.height - panel.height - gutter * 2);
  return {
    left: Math.min(maxX, Math.max(gutter, left)),
    top: Math.min(maxY, Math.max(gutter, top)),
  };
}

/** Width that stays usable at the 390px mobile house-rule viewport. */
export function overlayMaxWidth(viewportWidth: number): number {
  const w = viewportWidth || 390;
  return Math.min(360, Math.max(240, w - 24));
}

export type OverlayBoxStyle = {
  position: 'fixed';
  zIndex: number;
  width: number;
  maxHeight: string;
  left?: number | string;
  right?: number | string;
  top?: number | string;
  bottom?: number | string;
  transform?: string;
};

export function transcriptOverlayBoxStyle(
  placement: TranscriptOverlayPlacement,
  viewport: ViewportBox,
  panel: ViewportBox = { width: overlayMaxWidth(viewport.width), height: 160 },
): OverlayBoxStyle {
  const width = overlayMaxWidth(viewport.width);
  const mobile = viewport.width <= 430;
  const maxHeight = mobile ? '28vh' : '32vh';
  const base: OverlayBoxStyle = {
    position: 'fixed',
    zIndex: 9991,
    width,
    maxHeight,
  };

  switch (placement.dock) {
    case 'left':
      return { ...base, left: 12, bottom: 12 };
    case 'right':
      return { ...base, right: 12, bottom: 12 };
    case 'top':
      return { ...base, left: '50%', top: 12, transform: 'translateX(-50%)' };
    case 'free': {
      const px = freePlacementToPixels(placement, { ...panel, width }, viewport);
      return { ...base, left: px.left, top: px.top };
    }
    case 'bottom':
    default:
      return { ...base, left: '50%', bottom: 88, transform: 'translateX(-50%)' };
  }
}
