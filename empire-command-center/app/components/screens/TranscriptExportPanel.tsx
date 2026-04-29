/**
 * TranscriptExportPanel
 * Phase 1: Export + Proofreading UI
 *
 * Export panel for TranscriptForge — format selection, options, preview trigger.
 * Speaker labels are noted as manual-only.
 */

'use client';

import React, { useState } from 'react';
import { Download, Eye, FileText, Copy, AlertTriangle } from 'lucide-react';
import type { TranscriptSegment, ExportFormat, ExportOptions } from '../../schemas/transcriptforge-schemas';
import { buildExport, downloadExport } from '../../lib/transcriptforge/exporters';
import { chunkTimestampsValid } from '../../lib/transcriptforge/time';

interface TranscriptExportPanelProps {
  jobId: string;
  segments: TranscriptSegment[];
  speakerLabelMode?: 'manual' | 'auto'; // UI hint only
}

const FORMAT_BUTTONS: { format: ExportFormat; label: string; icon: string; description: string }[] = [
  { format: 'txt', label: 'TXT', icon: '📄', description: 'Plain text export' },
  { format: 'md', label: 'MD', icon: '📝', description: 'Markdown with formatting' },
  { format: 'json', label: 'JSON', icon: '{}', description: 'Structured JSON data' },
  { format: 'html', label: 'HTML', icon: '🌐', description: 'Printable HTML page' },
  { format: 'srt', label: 'SRT', icon: '⏱', description: 'Subtitles with timestamps' },
  { format: 'vtt', label: 'VTT', icon: '🎬', description: 'WebVTT subtitle format' },
];

export default function TranscriptExportPanel({ jobId, segments, speakerLabelMode = 'manual' }: TranscriptExportPanelProps) {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('txt');
  const [includeTimestamps, setIncludeTimestamps] = useState(true);
  const [includeSpeakers, setIncludeSpeakers] = useState(true);
  const [includeConfidence, setIncludeConfidence] = useState(false);
  const [includeReviewedMarkers, setIncludeReviewedMarkers] = useState(true);
  const [showPreview, setShowPreview] = useState(false);
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const [previewWarning, setPreviewWarning] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  // Check if SRT/VTT are available (require valid chunk timestamps)
  const timestampsValid = segments.length > 0 && chunkTimestampsValid(
    segments.map(s => ({ start_time: s.start, end_time: s.end, chunk_id: s.id } as any))
  );

  const srtVttDisabled = !timestampsValid;

  const handlePreview = () => {
    const opts: ExportOptions = {
      format: selectedFormat,
      includeTimestamps,
      includeSpeakers,
      includeConfidence,
      includeReviewedMarkers,
      maxPreviewSegments: 10,
    };
    const result = buildExport(segments.slice(0, 10), { ...opts, maxPreviewSegments: 10 });
    setPreviewContent(result.content);
    setPreviewWarning(result.warning || null);
    setShowPreview(true);
  };

  const handleDownload = () => {
    const opts: ExportOptions = {
      format: selectedFormat,
      includeTimestamps,
      includeSpeakers,
      includeConfidence,
      includeReviewedMarkers,
    };
    const result = buildExport(segments, opts);
    if (result.valid) {
      downloadExport(result);
    }
  };

  const handleCopy = () => {
    if (!previewContent) return;
    navigator.clipboard.writeText(previewContent).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }).catch(() => {
      setCopied(false);
    });
  };

  const activeFormat = FORMAT_BUTTONS.find(f => f.format === selectedFormat);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Speaker label notice */}
      {speakerLabelMode === 'manual' && (
        <div style={{ padding: '8px 12px', background: '#f5f3ef', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 11, color: '#6b7280' }}>
          ⚠️ Manual speaker labels — automatic diarization is not enabled yet.
        </div>
      )}

      {/* Format selection */}
      <div>
        <label style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 8 }}>
          Export Format
        </label>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {FORMAT_BUTTONS.map(btn => {
            const disabled = (btn.format === 'srt' || btn.format === 'vtt') && srtVttDisabled;
            return (
              <button
                key={btn.format}
                onClick={() => !disabled && setSelectedFormat(btn.format)}
                disabled={disabled}
                aria-label={disabled ? `${btn.label} requires valid chunk timestamps` : btn.description}
                title={disabled ? 'Subtitle export requires valid timestamped chunks' : btn.description}
                style={{
                  padding: '6px 12px',
                  background: selectedFormat === btn.format ? '#2563eb' : disabled ? '#f3f4f6' : '#fff',
                  color: selectedFormat === btn.format ? '#fff' : disabled ? '#ccc' : '#374151',
                  border: selectedFormat === btn.format ? 'none' : '1px solid #d1d5db',
                  borderRadius: 6,
                  fontSize: 12,
                  fontWeight: 600,
                  cursor: disabled ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                }}
              >
                <span aria-hidden="true">{btn.icon}</span>
                {btn.label}
              </button>
            );
          })}
        </div>
        {srtVttDisabled && (
          <p style={{ fontSize: 11, color: '#9ca3af', marginTop: 6 }}>
            Subtitle export (SRT/VTT) requires valid timestamped chunks — currently disabled.
          </p>
        )}
      </div>

      {/* Options */}
      <div>
        <label style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 8 }}>
          Options
        </label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {[
            { key: 'includeTimestamps', label: 'Include timestamps', checked: includeTimestamps, setter: setIncludeTimestamps },
            { key: 'includeSpeakers', label: 'Include speaker labels', checked: includeSpeakers, setter: setIncludeSpeakers },
            { key: 'includeConfidence', label: 'Include confidence scores', checked: includeConfidence, setter: setIncludeConfidence },
            { key: 'includeReviewedMarkers', label: 'Mark reviewed segments', checked: includeReviewedMarkers, setter: setIncludeReviewedMarkers },
          ].map(({ key, label, checked, setter }) => (
            <label key={key} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: '#374151', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={checked}
                onChange={e => setter(e.target.checked)}
                style={{ width: 14, height: 14 }}
              />
              {label}
            </label>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 8 }}>
        <button
          onClick={handlePreview}
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', background: '#fff', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 13, cursor: 'pointer', color: '#374151' }}
        >
          <Eye size={14} /> Preview
        </button>
        <button
          onClick={handleDownload}
          disabled={segments.length === 0}
          aria-label="Download export"
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', background: segments.length === 0 ? '#e5e7eb' : '#2563eb', color: segments.length === 0 ? '#9ca3af' : '#fff', border: 'none', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: segments.length === 0 ? 'not-allowed' : 'pointer' }}
        >
          <Download size={14} /> Download
        </button>
      </div>

      {/* Preview modal (inline, not a portal since no portal available) */}
      {showPreview && previewContent !== null && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div style={{ background: 'white', borderRadius: 12, padding: 24, width: 640, maxWidth: '90vw', maxHeight: '80vh', overflow: 'auto' }}>
            <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>
              Preview: {activeFormat?.label} ({Math.min(10, segments.length)} segments)
            </h3>
            {previewWarning && (
              <div style={{ padding: '8px 12px', background: '#fef9c3', border: '1px solid #fde047', borderRadius: 6, fontSize: 12, color: '#92400e', marginBottom: 12 }}>
                <AlertTriangle size={12} style={{ display: 'inline', marginRight: 4 }} />
                {previewWarning}
              </div>
            )}
            <pre style={{
              fontSize: 12, lineHeight: 1.5, whiteSpace: 'pre-wrap',
              background: '#f9fafb', padding: 12, borderRadius: 6,
              border: '1px solid #e5e7eb', maxHeight: 300, overflowY: 'auto',
              fontFamily: 'monospace', marginBottom: 16
            }}>
              {previewContent}
            </pre>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button
                onClick={handleCopy}
                style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', background: copied ? '#dcfce7' : '#f3f4f6', color: copied ? '#166534' : '#374151', border: 'none', borderRadius: 6, fontSize: 13, cursor: 'pointer' }}
              >
                <Copy size={13} /> {copied ? 'Copied!' : 'Copy'}
              </button>
              <button
                onClick={() => { setShowPreview(false); setPreviewContent(null); }}
                style={{ padding: '8px 14px', background: '#f3f4f6', border: 'none', borderRadius: 6, fontSize: 13, cursor: 'pointer' }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
