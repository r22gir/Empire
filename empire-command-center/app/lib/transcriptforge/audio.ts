/**
 * audio.ts — TranscriptForge audio readiness validation
 * Phase 1.5 Hardening: TF-6
 *
 * Frontend-only audio validation helper.
 * Does NOT parse binary headers — codec detection requires Phase 2 backend endpoint.
 *
 * Client-side MIME type check is extension-based only.
 * For M4A: assumes AAC codec — mark as low risk with a playback warning.
 * True codec detection requires backend file inspection — Phase 2 endpoint needed.
 */

import type { AudioValidationResult } from '../../schemas/transcriptforge-schemas';

// ============================================================
// EXTENSION -> MIME TYPE MAP
// ============================================================

const MIME_MAP: Record<string, string> = {
  mp3: 'audio/mpeg',
  wav: 'audio/wav',
  m4a: 'audio/mp4',
  aac: 'audio/aac',
  ogg: 'audio/ogg',
  flac: 'audio/flac',
  mp4: 'video/mp4',
};

const M4A_WARNING = 'If playback fails, convert to MP3/WAV.';

// ============================================================
// VALIDATION
// ============================================================

export function validateAudioAvailability(
  chunkCount: number,
  hasFullJobAudio: boolean,
  filename?: string
): AudioValidationResult {
  // Determine source
  if (chunkCount > 0) {
    const ext: string | undefined = filename ? (filename.split('.').pop()?.toLowerCase() ?? undefined) : undefined;
    const mimeType = ext ? MIME_MAP[ext] || 'audio/mpeg' : undefined;

    if (ext === 'm4a') {
      return {
        available: true,
        source: 'chunk',
        mimeType,
        extension: ext,
        likelyPlayable: true,
        risk: 'low',
        message: `Chunk audio available (${ext.toUpperCase()}). ${M4A_WARNING}`,
      };
    }

    return {
      available: true,
      source: 'chunk',
      mimeType,
      extension: ext,
      likelyPlayable: true,
      risk: 'low',
      message: 'Chunk audio available.',
    };
  }

  if (hasFullJobAudio) {
    return {
      available: true,
      source: 'job',
      likelyPlayable: true,
      risk: 'medium',
      message: 'Full-job audio available. Chunk-level sync not verified.',
    };
  }

  return {
    available: false,
    source: 'none',
    likelyPlayable: false,
    risk: 'high',
    message: 'Audio unavailable — transcript view only.',
  };
}

export function validateAudioChunk(chunkId: string, startTime: number, endTime: number): AudioValidationResult {
  const hasValidTimestamps = Number.isFinite(startTime) && startTime >= 0 && Number.isFinite(endTime) && endTime > startTime;

  if (!hasValidTimestamps) {
    return {
      available: false,
      source: 'chunk',
      likelyPlayable: false,
      risk: 'high',
      message: `Chunk ${chunkId}: no valid timestamp — audio seek not possible.`,
    };
  }

  return {
    available: true,
    source: 'chunk',
    likelyPlayable: true,
    risk: 'low',
    message: `Chunk ${chunkId}: audio available (${startTime.toFixed(1)}s – ${endTime.toFixed(1)}s).`,
  };
}