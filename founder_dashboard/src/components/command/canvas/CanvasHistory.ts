/**
 * CanvasHistory — Remember and recall previous canvas states.
 * localStorage-backed persistence of canvas snapshots for recall.
 */

import type { CanvasMode, AnalysisResult } from './ContentAnalyzer';

export interface CanvasSnapshot {
  id: string;
  timestamp: number;
  mode: CanvasMode;
  /** Short label for the snapshot */
  label: string;
  /** The raw content that produced this canvas state */
  content: string;
  /** Analysis result at snapshot time */
  analysis: AnalysisResult;
  /** Associated chat message index (for context) */
  messageIndex?: number;
  /** Tags for categorization */
  tags: string[];
}

const STORAGE_KEY = 'empire_canvas_history';
const MAX_SNAPSHOTS = 50;

/** Load all snapshots from localStorage */
export function loadHistory(): CanvasSnapshot[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

/** Save a new canvas snapshot */
export function saveSnapshot(snapshot: Omit<CanvasSnapshot, 'id' | 'timestamp'>): CanvasSnapshot {
  const history = loadHistory();
  const entry: CanvasSnapshot = {
    ...snapshot,
    id: Math.random().toString(36).slice(2, 10),
    timestamp: Date.now(),
  };

  history.unshift(entry);

  // Trim to max size
  if (history.length > MAX_SNAPSHOTS) {
    history.length = MAX_SNAPSHOTS;
  }

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
  } catch {
    // Storage full — trim more aggressively
    history.length = Math.floor(MAX_SNAPSHOTS / 2);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    } catch { /* give up */ }
  }

  return entry;
}

/** Delete a snapshot by ID */
export function deleteSnapshot(id: string): void {
  const history = loadHistory().filter(s => s.id !== id);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
}

/** Clear all canvas history */
export function clearHistory(): void {
  localStorage.removeItem(STORAGE_KEY);
}

/** Search snapshots by label, tag, or mode */
export function searchHistory(query: string): CanvasSnapshot[] {
  const history = loadHistory();
  const q = query.toLowerCase();
  return history.filter(s =>
    s.label.toLowerCase().includes(q) ||
    s.tags.some(t => t.toLowerCase().includes(q)) ||
    s.mode.includes(q)
  );
}

/** Get snapshots by mode */
export function getByMode(mode: CanvasMode): CanvasSnapshot[] {
  return loadHistory().filter(s => s.mode === mode);
}

/** Get the most recent N snapshots */
export function getRecent(count: number = 10): CanvasSnapshot[] {
  return loadHistory().slice(0, count);
}

/**
 * Auto-label a snapshot based on its analysis.
 * Used when no explicit label is provided.
 */
export function autoLabel(analysis: AnalysisResult): string {
  const parts: string[] = [];

  if (analysis.charts.length > 0) {
    const firstChart = analysis.charts[0];
    parts.push(`Chart: ${firstChart.headers.slice(0, 2).join(' vs ')}`);
  }

  if (analysis.metrics.length > 0) {
    parts.push(`${analysis.metrics.length} metrics`);
  }

  if (analysis.webPreviews.length > 0) {
    const types = analysis.webPreviews.map(w => w.type);
    if (types.includes('youtube')) parts.push('Video');
    else parts.push(`${analysis.webPreviews.length} links`);
  }

  if (analysis.images.length > 0) {
    parts.push(`${analysis.images.length} images`);
  }

  if (parts.length === 0) {
    // Use first line of text content as label
    const firstLine = analysis.textContent.split('\n')[0].replace(/[#*_]/g, '').trim();
    return firstLine.slice(0, 60) || 'Canvas';
  }

  return parts.join(' + ');
}

/**
 * Auto-tag based on analysis results.
 */
export function autoTags(analysis: AnalysisResult): string[] {
  const tags: string[] = [];

  if (analysis.charts.length > 0) tags.push('chart');
  if (analysis.metrics.length > 0) tags.push('metrics');
  if (analysis.webPreviews.length > 0) tags.push('web');
  if (analysis.images.length > 0) tags.push('images');
  if (analysis.hasCode) tags.push('code');
  if (analysis.quotes.length > 0) tags.push('quotes');

  return tags;
}
