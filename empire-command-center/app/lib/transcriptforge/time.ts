/**
 * TranscriptForge v10 — Timestamp formatting utilities
 * Phase 1: Export + Proofreading UI
 */

import type { ChunkInfo } from '../../schemas/transcriptforge-schemas';

export function formatTimestamp(seconds: number, format: 'srt' | 'vtt' | 'display'): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 1000);

  if (format === 'srt') {
    return `${pad2(h)}:${pad2(m)}:${pad2(s)},${pad3(ms)}`;
  }
  if (format === 'vtt') {
    return `${pad2(h)}:${pad2(m)}:${pad2(s)}.${pad3(ms)}`;
  }
  return `${pad2(h)}:${pad2(m)}:${pad2(s)}`;
}

function pad2(n: number): string {
  return String(n).padStart(2, '0');
}

function pad3(n: number): string {
  return String(n).padStart(3, '0');
}

export function formatTimestampDisplay(seconds: number): string {
  return formatTimestamp(seconds, 'display');
}

export function fmtDuration(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${String(s).padStart(2, '0')}`;
}

/**
 * Returns true only if ALL chunks have valid positive timestamps
 * where end_time > start_time. Used to gate SRT/VTT export.
 */
export function chunkTimestampsValid(chunks: ChunkInfo[]): boolean {
  return chunks.every(c =>
    typeof c.start_time === 'number' &&
    typeof c.end_time === 'number' &&
    c.start_time >= 0 &&
    c.end_time > c.start_time
  );
}

/**
 * Format a single SRT/VTT timestamped cue from a segment.
 */
export function formatSrtcCue(
  index: number,
  start: number,
  end: number,
  text: string,
  speaker: string,
  includeSpeaker: boolean
): string {
  const startStr = formatTimestamp(start, 'srt');
  const endStr = formatTimestamp(end, 'srt');
  const speakerLine = includeSpeaker && speaker ? `${speaker}\n` : '';
  return `${index}\n${startStr} --> ${endStr}\n${speakerLine}${text}\n`;
}

export function formatVttCue(
  start: number,
  end: number,
  text: string,
  speaker: string,
  includeSpeaker: boolean
): string {
  const startStr = formatTimestamp(start, 'vtt');
  const endStr = formatTimestamp(end, 'vtt');
  const speakerLine = includeSpeaker && speaker ? `<c.speaker>${speaker}</c>\n` : '';
  return `${startStr} --> ${endStr}\n${speakerLine}${text}\n`;
}
