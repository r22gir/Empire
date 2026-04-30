/**
 * useTranscriptForgeAPI — Phase 2 backend integration swap point
 * Phase 1.5 Hardening
 *
 * TF-3: Placeholder for future backend integration.
 * No calls are made in Phase 1. All functions are TODO stubs.
 *
 * When backend is ready, replace mock returns with real fetch calls.
 * Import this file as the single integration point for TranscriptForge backend.
 */

'use client';

// ============================================================
// TODO STUBS — Phase 2 implementation markers
// ============================================================

/**
 * GET /api/v1/transcriptforge/jobs/{job_id}
 * Fetch full job details including chunks
 */
export async function fetchJob(jobId: string): Promise<unknown> {
  console.warn('[TranscriptForge] [API] fetchJob not implemented — Phase 2 endpoint');
  // TODO(Phase 2): Replace with:
  // const res = await fetch(`/api/v1/transcriptforge/jobs/${jobId}`);
  // if (!res.ok) throw new Error(`Job fetch failed: ${res.status}`);
  // return res.json();
  return null;
}

/**
 * PATCH /api/v1/transcriptforge/jobs/{job_id}/segments/{chunk_id}
 * Save proofreading edits to backend
 * Body: { transcript_text: string, speaker_label?: string, reviewed?: boolean }
 */
export async function saveSegmentEdit(
  jobId: string,
  chunkId: string,
  payload: { transcript_text: string; speaker_label?: string; reviewed?: boolean }
): Promise<unknown> {
  console.warn('[TranscriptForge] [API] saveSegmentEdit not implemented — Phase 2 endpoint');
  // TODO(Phase 2): Replace with:
  // const res = await fetch(`/api/v1/transcriptforge/jobs/${jobId}/segments/${chunkId}`, {
  //   method: 'PATCH',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify(payload),
  // });
  // if (!res.ok) throw new Error(`Segment save failed: ${res.status}`);
  // return res.json();
  return null;
}

/**
 * POST /api/v1/transcriptforge/jobs/{job_id}/speaker-labels
 * Sync speaker label assignments to backend
 * Body: { labels: Array<{ chunk_id: string; label: string }> }
 */
export async function syncSpeakerLabels(
  jobId: string,
  labels: Array<{ chunk_id: string; label: string }>
): Promise<unknown> {
  console.warn('[TranscriptForge] [API] syncSpeakerLabels not implemented — Phase 2 endpoint');
  // TODO(Phase 2): Replace with:
  // const res = await fetch(`/api/v1/transcriptforge/jobs/${jobId}/speaker-labels`, {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify({ labels }),
  // });
  // if (!res.ok) throw new Error(`Speaker sync failed: ${res.status}`);
  // return res.json();
  return null;
}

/**
 * POST /api/v1/transcriptforge/jobs/{job_id}/reviewed
 * Mark segments as reviewed on backend
 * Body: { chunk_ids: string[] }
 */
export async function markSegmentsReviewed(
  jobId: string,
  chunkIds: string[]
): Promise<unknown> {
  console.warn('[TranscriptForge] [API] markSegmentsReviewed not implemented — Phase 2 endpoint');
  // TODO(Phase 2): Replace with:
  // const res = await fetch(`/api/v1/transcriptforge/jobs/${jobId}/reviewed`, {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify({ chunk_ids: chunkIds }),
  // });
  // if (!res.ok) throw new Error(`Reviewed sync failed: ${res.status}`);
  // return res.json();
  return null;
}

/**
 * GET /api/v1/transcriptforge/jobs/{job_id}/audio
 * Get full-job audio stream or URL for playback
 * Returns: { url: string, mime_type: string, duration_sec: number }
 */
export async function fetchJobAudio(jobId: string): Promise<unknown> {
  console.warn('[TranscriptForge] [API] fetchJobAudio not implemented — Phase 2 endpoint');
  // TODO(Phase 2): Replace with:
  // const res = await fetch(`/api/v1/transcriptforge/jobs/${jobId}/audio`);
  // if (!res.ok) throw new Error(`Audio fetch failed: ${res.status}`);
  // return res.json();
  return null;
}

/**
 * GET /api/v1/transcriptforge/jobs/{job_id}/export/audio-bundle
 * Export full-job audio as a downloadable bundle (ZIP of chunks or single file)
 * Returns: { url: string, filename: string, size_bytes: number }
 */
export async function fetchAudioBundle(jobId: string): Promise<unknown> {
  console.warn('[TranscriptForge] [API] fetchAudioBundle not implemented — Phase 2 endpoint');
  // TODO(Phase 2): Replace with:
  // const res = await fetch(`/api/v1/transcriptforge/jobs/${jobId}/export/audio-bundle`);
  // if (!res.ok) throw new Error(`Audio bundle fetch failed: ${res.status}`);
  // return res.json();
  return null;
}

/**
 * GET /api/v1/transcriptforge/jobs/{job_id}/export/{format}
 * Export transcript in specified format (txt, md, json, html, srt, vtt)
 * Params: format, include_timestamps, include_speakers, include_confidence, include_reviewed_markers
 * Returns: { content: string, filename: string }
 */
export async function fetchTranscriptExport(
  jobId: string,
  params: {
    format: string;
    include_timestamps?: boolean;
    include_speakers?: boolean;
    include_confidence?: boolean;
    include_reviewed_markers?: boolean;
  }
): Promise<unknown> {
  console.warn('[TranscriptForge] [API] fetchTranscriptExport not implemented — Phase 2 endpoint');
  // TODO(Phase 2): Replace with:
  // const qs = new URLSearchParams({ format: params.format, ... }).toString();
  // const res = await fetch(`/api/v1/transcriptforge/jobs/${jobId}/export/${params.format}?${qs}`);
  // if (!res.ok) throw new Error(`Export fetch failed: ${res.status}`);
  // return res.json();
  return null;
}

/**
 * POST /api/v1/transcriptforge/jobs/{job_id}/confidence-feedback
 * Send confidence calibration feedback to backend for model improvement
 * Body: { chunk_id: string, verdict: 'looks_good' | 'needs_correction' | 'unclear', note?: string }
 */
export async function sendConfidenceFeedback(
  jobId: string,
  chunkId: string,
  verdict: string,
  note?: string
): Promise<unknown> {
  console.warn('[TranscriptForge] [API] sendConfidenceFeedback not implemented — Phase 2 endpoint');
  // TODO(Phase 2): Replace with:
  // const res = await fetch(`/api/v1/transcriptforge/jobs/${jobId}/confidence-feedback`, {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify({ chunk_id: chunkId, verdict, note }),
  // });
  // if (!res.ok) throw new Error(`Confidence feedback failed: ${res.status}`);
  // return res.json();
  return null;
}