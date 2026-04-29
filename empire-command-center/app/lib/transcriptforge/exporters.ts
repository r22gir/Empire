/**
 * TranscriptForge v10 — Export format utilities
 * Phase 1: Export + Proofreading UI
 *
 * All formats work on TranscriptSegment[] data.
 * SRT/VTT only enabled when chunkTimestampsValid() is true.
 * Local edited text takes priority over raw/verified transcript.
 */

import type { TranscriptSegment, ExportFormat, ExportOptions, ExportResult } from '../../schemas/transcriptforge-schemas';
import { formatTimestamp, formatTimestampDisplay } from './time';

// ============================================================
// INTERNAL BUILDERS
// ============================================================

function buildHeader(jobId: string, format: ExportFormat): string {
  const date = new Date().toISOString();
  if (format === 'md') {
    return `# Transcript — ${jobId}\n\n*Exported: ${date}*\n\n---\n`;
  }
  if (format === 'json') {
    return ''; // JSON doesn't use a header string
  }
  return '';
}

function formatSegmentTxt(
  seg: TranscriptSegment,
  opts: Pick<ExportOptions, 'includeTimestamps' | 'includeSpeakers' | 'includeConfidence' | 'includeReviewedMarkers'>
): string {
  const parts: string[] = [];
  if (opts.includeTimestamps) {
    parts.push(`[${formatTimestampDisplay(seg.start)}]`);
  }
  if (opts.includeSpeakers && seg.speaker) {
    parts.push(`**${seg.speaker}:**`);
  }
  parts.push(seg.text);
  if (opts.includeReviewedMarkers && seg.reviewed) {
    parts.push(' ✓');
  }
  return parts.join(' ');
}

function formatSegmentMd(
  seg: TranscriptSegment,
  opts: Pick<ExportOptions, 'includeTimestamps' | 'includeSpeakers' | 'includeConfidence' | 'includeReviewedMarkers'>
): string {
  const parts: string[] = [];
  if (opts.includeTimestamps) {
    parts.push(`**[${formatTimestampDisplay(seg.start)}]**`);
  }
  if (opts.includeSpeakers && seg.speaker) {
    parts.push(`*${seg.speaker}:*`);
  }
  let line = seg.text;
  if (opts.includeReviewedMarkers && seg.reviewed) {
    line += ' ~~✓reviewed~~';
  }
  if (seg.edited) {
    line += ' *[edited]*';
  }
  parts.push(line);
  return parts.join(' ');
}

function formatSegmentHtml(
  seg: TranscriptSegment,
  opts: Pick<ExportOptions, 'includeTimestamps' | 'includeSpeakers' | 'includeConfidence' | 'includeReviewedMarkers'>
): string {
  const ts = opts.includeTimestamps
    ? `<span class="ts">${formatTimestampDisplay(seg.start)}</span> `
    : '';
  const sp = opts.includeSpeakers && seg.speaker
    ? `<span class="sp">${seg.speaker}:</span> `
    : '';
  const conf = opts.includeConfidence && seg.confidence !== null
    ? ` <span class="conf">${(seg.confidence * 100).toFixed(0)}%</span>`
    : '';
  const reviewed = opts.includeReviewedMarkers && seg.reviewed ? ' ✓' : '';
  const edited = seg.edited ? ' <em class="edited">[edited]</em>' : '';
  return `<p>${ts}${sp}${seg.text}${conf}${reviewed}${edited}</p>`;
}

// ============================================================
// MAIN EXPORT FUNCTION
// ============================================================

export function buildExport(
  segments: TranscriptSegment[],
  opts: ExportOptions
): ExportResult {
  if (segments.length === 0) {
    return {
      content: '',
      format: opts.format,
      filename: `transcript.${opts.format}`,
      mimeType: getMimeType(opts.format),
      valid: false,
      warning: 'No segments to export.',
    };
  }

  const header = buildHeader(segments[0]?.id.split('_')[0] || 'export', opts.format);
  const segmentOpts = {
    includeTimestamps: opts.includeTimestamps,
    includeSpeakers: opts.includeSpeakers,
    includeConfidence: opts.includeConfidence,
    includeReviewedMarkers: opts.includeReviewedMarkers,
  };

  try {
    switch (opts.format) {
      case 'txt':
        return exportTxt(segments, header, segmentOpts);
      case 'md':
        return exportMd(segments, header, segmentOpts);
      case 'json':
        return exportJson(segments, header, segmentOpts);
      case 'html':
        return exportHtml(segments, header, segmentOpts);
      case 'srt':
        return exportSrt(segments, segmentOpts);
      case 'vtt':
        return exportVtt(segments, segmentOpts);
      default:
        return { content: '', format: opts.format, filename: '', mimeType: '', valid: false, warning: 'Unknown format.' };
    }
  } catch (err) {
    console.warn(`[TranscriptForge] Export failed for format=${opts.format}, segments=${segments.length}:`, err);
    return {
      content: '',
      format: opts.format,
      filename: `transcript.${opts.format}`,
      mimeType: getMimeType(opts.format),
      valid: false,
      warning: `Export failed: ${err instanceof Error ? err.message : String(err)}`,
    };
  }
}

// ============================================================
// FORMAT IMPLEMENTATIONS
// ============================================================

function exportTxt(
  segments: TranscriptSegment[],
  header: string,
  opts: Pick<ExportOptions, 'includeTimestamps' | 'includeSpeakers' | 'includeConfidence' | 'includeReviewedMarkers'>
): ExportResult {
  const lines: string[] = [header];
  for (const seg of segments) {
    lines.push(formatSegmentTxt(seg, opts));
  }
  return {
    content: lines.join('\n'),
    format: 'txt',
    filename: 'transcript.txt',
    mimeType: 'text/plain',
    valid: true,
  };
}

function exportMd(
  segments: TranscriptSegment[],
  header: string,
  opts: Pick<ExportOptions, 'includeTimestamps' | 'includeSpeakers' | 'includeConfidence' | 'includeReviewedMarkers'>
): ExportResult {
  const lines: string[] = [header];
  for (const seg of segments) {
    lines.push(formatSegmentMd(seg, opts));
  }
  return {
    content: lines.join('\n'),
    format: 'md',
    filename: 'transcript.md',
    mimeType: 'text/markdown',
    valid: true,
  };
}

function exportJson(
  segments: TranscriptSegment[],
  _header: string,
  opts: Pick<ExportOptions, 'includeTimestamps' | 'includeSpeakers' | 'includeConfidence' | 'includeReviewedMarkers'>
): ExportResult {
  const exportable = segments.map(seg => {
    const obj: Record<string, unknown> = {
      id: seg.id,
      start: seg.start,
      end: seg.end,
      text: seg.text,
      speaker: opts.includeSpeakers ? seg.speaker : undefined,
      confidence: opts.includeConfidence ? seg.confidence : undefined,
      reviewed: opts.includeReviewedMarkers ? seg.reviewed : undefined,
      edited: seg.edited,
    };
    return obj;
  });
  return {
    content: JSON.stringify({ segments: exportable, exported_at: new Date().toISOString() }, null, 2),
    format: 'json',
    filename: 'transcript.json',
    mimeType: 'application/json',
    valid: true,
  };
}

function exportHtml(
  segments: TranscriptSegment[],
  header: string,
  opts: Pick<ExportOptions, 'includeTimestamps' | 'includeSpeakers' | 'includeConfidence' | 'includeReviewedMarkers'>
): ExportResult {
  const body = segments.map(seg => formatSegmentHtml(seg, opts)).join('\n');
  const content = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Transcript Export</title>
<style>
  body { font-family: Georgia, serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #1a1a1a; }
  .ts { color: #888; font-size: 0.85em; margin-right: 6px; }
  .sp { font-weight: 700; color: #374151; margin-right: 6px; }
  .conf { color: #6b7280; font-size: 0.8em; }
  .edited { color: #7c3aed; font-size: 0.85em; }
  p { margin: 0 0 12px 0; line-height: 1.7; }
  @media print { body { margin: 20px; } p { break-inside: avoid; } }
</style>
</head>
<body>
${header ? `<h1 style="font-size:1.1em;color:#374151;margin-bottom:20px;">Transcript Export</h1>\n` : ''}
${body}
</body>
</html>`;
  return {
    content,
    format: 'html',
    filename: 'transcript.html',
    mimeType: 'text/html',
    valid: true,
  };
}

function exportSrt(
  segments: TranscriptSegment[],
  opts: Pick<ExportOptions, 'includeTimestamps' | 'includeSpeakers' | 'includeConfidence' | 'includeReviewedMarkers'>
): ExportResult {
  let index = 1;
  const lines: string[] = [];
  for (const seg of segments) {
    if (seg.start < 0 || seg.end <= seg.start) {
      console.warn(`[TranscriptForge] Skipping SRT segment ${seg.id} due to invalid timestamps.`);
      continue;
    }
    lines.push(formatSrtCue(index, seg.start, seg.end, seg.text, opts.includeSpeakers ? seg.speaker : '', opts.includeReviewedMarkers && seg.reviewed ? ' ✓' : ''));
    index++;
  }
  return {
    content: lines.join('\n'),
    format: 'srt',
    filename: 'transcript.srt',
    mimeType: 'application/x-subrip',
    valid: lines.length > 0,
    warning: lines.length === 0 ? 'No valid timestamped segments for SRT export.' : undefined,
  };
}

function formatSrtCue(index: number, start: number, end: number, text: string, speaker: string, reviewedMark: string): string {
  const startStr = formatTimestamp(start, 'srt');
  const endStr = formatTimestamp(end, 'srt');
  const speakerLine = speaker ? `${speaker}\n` : '';
  return `${index}\n${startStr} --> ${endStr}\n${speakerLine}${text}${reviewedMark}\n`;
}

function exportVtt(
  segments: TranscriptSegment[],
  opts: Pick<ExportOptions, 'includeTimestamps' | 'includeSpeakers' | 'includeConfidence' | 'includeReviewedMarkers'>
): ExportResult {
  const lines: string[] = ['WEBVTT', ''];
  let index = 1;
  for (const seg of segments) {
    if (seg.start < 0 || seg.end <= seg.start) {
      console.warn(`[TranscriptForge] Skipping VTT segment ${seg.id} due to invalid timestamps.`);
      continue;
    }
    lines.push(formatVttCue(index, seg.start, seg.end, seg.text, opts.includeSpeakers ? seg.speaker : '', opts.includeReviewedMarkers && seg.reviewed ? ' ✓' : ''));
    index++;
  }
  return {
    content: lines.join('\n'),
    format: 'vtt',
    filename: 'transcript.vtt',
    mimeType: 'text/vtt',
    valid: lines.length > 2,
    warning: lines.length <= 2 ? 'No valid timestamped segments for VTT export.' : undefined,
  };
}

function formatVttCue(index: number, start: number, end: number, text: string, speaker: string, reviewedMark: string): string {
  const startStr = formatTimestamp(start, 'vtt');
  const endStr = formatTimestamp(end, 'vtt');
  const speakerLine = speaker ? `<c.speaker>${speaker}</c>\n` : '';
  return `${index}\n${startStr} --> ${endStr}\n${speakerLine}${text}${reviewedMark}\n`;
}

// ============================================================
// HELPERS
// ============================================================

function getMimeType(format: ExportFormat): string {
  const map: Record<ExportFormat, string> = {
    txt: 'text/plain',
    md: 'text/markdown',
    json: 'application/json',
    html: 'text/html',
    srt: 'application/x-subrip',
    vtt: 'text/vtt',
  };
  return map[format] || 'text/plain';
}

export function downloadExport(result: ExportResult): void {
  if (!result.valid || !result.content) return;
  const blob = new Blob([result.content], { type: result.mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = result.filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard) {
    return navigator.clipboard.writeText(text).catch(() => {});
  }
  return Promise.reject(new Error('Clipboard API not available'));
}
