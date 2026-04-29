/**
 * TranscriptForge v10 — TypeScript interfaces (frontend-only, no Zod)
 * Phase 1: Export + Proofreading UI
 */

// ChunkInfo must match the interface in TranscriptForgePage.tsx
export interface ChunkInfo {
  chunk_id: string;
  job_id: string;
  sequence: number;
  start_time: number;
  end_time: number;
  raw_transcript: string | null;
  verified_transcript: string | null;
  confidence: number | null;
  mismatch_flags: string[];
  review_status: string;
  reviewer: string | null;
  reviewer_timestamp: string | null;
  processing_status?: string;
  raw_transcript_path?: string | null;
  verified_transcript_path?: string | null;
}

// ============================================================
// TRANSCRIPT SEGMENT (built from ChunkInfo)
// ============================================================

export interface TranscriptSegment {
  id: string;           // chunk_id
  start: number;        // start_time (seconds)
  end: number;          // end_time (seconds)
  speaker: string;      // locally assigned or "Unknown Speaker"
  text: string;         // edited text优先 || verified_transcript || raw_transcript || ""
  confidence: number | null;
  reviewed: boolean;    // local proofreading state
  edited: boolean;      // local edit exists
}

// ============================================================
// SPEAKER LABELS (localStorage)
// ============================================================

export type SpeakerLabelMap = Record<string, string>; // chunkId -> speaker label
export type JobSpeakerLabels = Record<string, SpeakerLabelMap>; // jobId -> { chunkId -> label }

export interface SpeakerLabelStore {
  [jobId: string]: SpeakerLabelMap;
}

// ============================================================
// LOCAL EDITS (localStorage)
// ============================================================

export type LocalEditMap = Record<string, string>; // chunkId -> edited text
export type JobLocalEdits = Record<string, LocalEditMap>; // jobId -> { chunkId -> text }

export interface LocalEditStore {
  [jobId: string]: LocalEditMap;
}

// ============================================================
// REVIEWED SEGMENTS (localStorage)
// ============================================================

export type ReviewedSegmentSet = string[]; // array of chunkIds marked reviewed
export type JobReviewedSegments = Record<string, ReviewedSegmentSet>;

export interface ReviewedSegmentStore {
  [jobId: string]: ReviewedSegmentSet;
}

// ============================================================
// EXPORT OPTIONS
// ============================================================

export type ExportFormat = 'txt' | 'md' | 'json' | 'html' | 'srt' | 'vtt';

export interface ExportOptions {
  format: ExportFormat;
  includeTimestamps: boolean;
  includeSpeakers: boolean;
  includeConfidence: boolean;
  includeReviewedMarkers: boolean;
  // SRT/VTT only:
  maxPreviewSegments?: number; // for preview modal, default 10
}

// ============================================================
// EXPORT RESULT
// ============================================================

export interface ExportResult {
  content: string;
  format: ExportFormat;
  filename: string;
  mimeType: string;
  valid: boolean;
  warning?: string; // e.g. SRT/VTT disabled reason
}

// ============================================================
// PROOFREADING SESSION
// ============================================================

export interface ProofreadingSession {
  jobId: string;
  segments: TranscriptSegment[];
  activeSegmentId: string | null;
  playingChunkId: string | null; // chunk currently highlighted during playback
}

// ============================================================
// CHUNK INFO MAPPING HELPER
// ============================================================

export function chunkToSegment(
  chunk: ChunkInfo,
  speakerLabel: string,
  localEdit: string | null,
  isReviewed: boolean
): TranscriptSegment {
  return {
    id: chunk.chunk_id,
    start: chunk.start_time,
    end: chunk.end_time,
    speaker: speakerLabel,
    text: localEdit || chunk.verified_transcript || chunk.raw_transcript || "",
    confidence: chunk.confidence,
    reviewed: isReviewed,
    edited: localEdit !== null,
  };
}

// ============================================================
// TIMESTAMP FORMATTING
// ============================================================

export function formatTimestamp(seconds: number, format: 'srt' | 'vtt' | 'display'): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 1000);

  if (format === 'srt') {
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(ms).padStart(3, '0')}`;
  }
  if (format === 'vtt') {
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(ms).padStart(3, '0')}`;
  }
  // display
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).toString().padStart(2, '0')}`;
}

export function formatTimestampDisplay(seconds: number): string {
  return formatTimestamp(seconds, 'display');
}

export function chunkTimestampsValid(chunks: ChunkInfo[]): boolean {
  return chunks.every(c =>
    typeof c.start_time === 'number' &&
    typeof c.end_time === 'number' &&
    c.start_time >= 0 &&
    c.end_time > c.start_time
  );
}

// Minimal TranscriptJob interface for frontend components
export interface TranscriptJobMinimal {
  job_id: string;
  state: string;
  source_mode: string;
  uploader: string;
  created_at: string;
  updated_at: string;
  file_name: string;
  file_size: number;
  duration_sec: number | null;
  chunks_total: number;
  chunks_complete: number;
  chunks_failed: number;
  overall_confidence: number | null;
  raw_transcript_path: string | null;
  verified_transcript_path: string | null;
  approved_transcript_path: string | null;
  critical_field_flags: string[];
  boundary_coherence_flags?: Array<Record<string, unknown>>;
  qc_summary: QCSummary | null;
  chunks: ChunkInfo[];
  audit_trail: AuditEntry[];
  display_state?: string;
  truth_summary?: string;
}

export interface QCSummary {
  chunks_total: number;
  chunks_complete: number;
  chunks_failed: number;
  low_confidence_segments: number;
  unreviewed_low_confidence: number;
  mismatch_count: number;
  reviewer_corrections_count: number;
  overall_confidence: number | null;
}

export interface AuditEntry {
  event: string;
  timestamp: string;
  actor?: string;
  chunk_id?: string;
  status?: string;
  notes?: string;
  corrections_applied?: number;
  flags?: string[];
}
