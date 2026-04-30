/**
 * TranscriptProofreadingPanel
 * Phase 1: Export + Proofreading UI
 *
 * Provides proofreading UI for individual transcript chunks:
 * - Per-chunk editable text
 * - Speaker label assignment
 * - Reviewed state marking
 * - Chunk-level audio playback with active highlight
 * - Undo/redo for edit session
 * - No full audio export offered
 */

'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
  Check, AlertTriangle, Undo2, Redo2, Volume2, VolumeX,
  Edit3, CheckCircle, Loader2, User, Mic, Pause, Play
} from 'lucide-react';
import type { ChunkInfo, TranscriptSegment, TranscriptJobMinimal } from '../../schemas/transcriptforge-schemas';
import { useProofreadingContext } from '../../hooks/useTranscriptForgeProofreading';
import { formatTimestampDisplay } from '../../lib/transcriptforge/time';

interface TranscriptProofreadingPanelProps {
  job: TranscriptJobMinimal;
  onClose?: () => void;
  apiBase?: string;
}

// Audio player for a single chunk with playback highlight
function ChunkAudioPlayer({
  jobId,
  chunk,
  apiBase,
  isPlaying,
  onPlayToggle,
}: {
  jobId: string;
  chunk: ChunkInfo;
  apiBase: string;
  isPlaying: boolean;
  onPlayToggle: () => void;
}) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [loadError, setLoadError] = useState(false);

  const startTime = Number(chunk.start_time);
  const endTime = Number(chunk.end_time);
  const hasValidTimestamps = Number.isFinite(startTime) && startTime >= 0 && Number.isFinite(endTime) && endTime > startTime;

  const audioUrl = hasValidTimestamps
    ? `${apiBase}/transcriptforge/jobs/${jobId}/chunks/${chunk.chunk_id}/audio#t=${startTime},${endTime}`
    : `${apiBase}/transcriptforge/jobs/${jobId}/chunks/${chunk.chunk_id}/audio`;

  useEffect(() => {
    if (!isPlaying && audioRef.current) {
      audioRef.current.pause();
      if (hasValidTimestamps) {
        audioRef.current.currentTime = startTime;
      }
    }
  }, [isPlaying, chunk.start_time]);

  if (loadError) {
    return (
      <span style={{ fontSize: 11, color: '#9ca3af' }}>
        Audio unavailable — transcript view only.
      </span>
    );
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <button
        onClick={onPlayToggle}
        aria-label={isPlaying ? 'Pause chunk audio' : 'Play chunk audio'}
        style={{
          display: 'flex', alignItems: 'center', gap: 4, padding: '4px 8px',
          background: isPlaying ? '#2563eb' : '#f3f4f6',
          color: isPlaying ? '#fff' : '#374151',
          border: 'none', borderRadius: 4, fontSize: 11, cursor: 'pointer',
        }}
      >
        {isPlaying ? <Pause size={11} /> : <Play size={11} />}
        {isPlaying ? 'Pause' : 'Play'}
      </button>
      <audio
        ref={audioRef}
        controls
        preload="none"
        src={audioUrl}
        onError={() => setLoadError(true)}
        style={{ height: 28, fontSize: 10 }}
        aria-label={`Audio for ${chunk.chunk_id}`}
      />
      {!hasValidTimestamps && !loadError && (
        <span style={{ fontSize: 10, color: '#9ca3af' }} title="This chunk has no valid timestamp yet.">
          ⏱ no timestamp
        </span>
      )}
    </div>
  );
}

// Single segment editor
function SegmentEditor({
  segment,
  jobId,
  isActive,
  isPlaying,
  onPlayToggle,
  apiBase,
  hasFullAudio,
  onSegmentClick,
}: {
  segment: TranscriptSegment;
  jobId: string;
  isActive: boolean;
  isPlaying: boolean;
  onPlayToggle: () => void;
  apiBase: string;
  hasFullAudio: boolean;
  onSegmentClick: () => void;
}) {
  const { setLocalEdit, setSpeakerLabel, setReviewed, getLocalEdit } = useProofreadingContext();
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(segment.text);
  const [speakerValue, setSpeakerValue] = useState(segment.speaker);

  const chunk = segment;

  const handleSaveEdit = () => {
    if (editText !== segment.text) {
      setLocalEdit(jobId, segment.id, editText);
    }
    setEditing(false);
  };

  const handleCancelEdit = () => {
    setEditText(segment.text);
    setEditing(false);
  };

  const handleSpeakerChange = (val: string) => {
    setSpeakerValue(val);
    setSpeakerLabel(jobId, segment.id, val);
  };

  const handleReviewed = () => {
    setReviewed(jobId, segment.id, !segment.reviewed);
  };

  const confidenceColor = segment.confidence !== null
    ? segment.confidence >= 0.8 ? '#166534' : segment.confidence >= 0.5 ? '#92400e' : '#991b1b'
    : '#6b7280';

  return (
    <div
      onClick={onSegmentClick}
      aria-current={isActive ? 'true' : undefined}
      style={{
        padding: '10px 14px',
        background: isActive ? '#eff6ff' : isPlaying ? '#f5f3ef' : '#fafaf9',
        border: `1px solid ${isActive ? '#2563eb' : '#e5e7eb'}`,
        borderRadius: 8,
        marginBottom: 8,
        cursor: hasFullAudio ? 'pointer' : 'default',
      }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 11, fontFamily: 'monospace', fontWeight: 600, color: '#6b7280', minWidth: 80 }}>
          {segment.id}
        </span>
        <span style={{ fontSize: 11, color: '#9ca3af' }}>
          {formatTimestampDisplay(segment.start)} — {formatTimestampDisplay(segment.end)}
        </span>
        {segment.confidence !== null && (
          <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 999, background: '#f3f4f6', color: confidenceColor }}>
            {(segment.confidence * 100).toFixed(0)}%
          </span>
        )}
        {segment.edited && (
          <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 999, background: '#f3e8ff', color: '#6b21a8' }}>
            edited
          </span>
        )}
        {segment.reviewed && (
          <span style={{ fontSize: 10, padding: '1px 6px', borderRadius: 999, background: '#dcfce7', color: '#166534' }}>
            ✓ reviewed
          </span>
        )}
      </div>

      {/* Speaker label */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
        <User size={11} style={{ color: '#6b7280' }} />
        <input
          type="text"
          value={speakerValue}
          onChange={e => handleSpeakerChange(e.target.value)}
          placeholder="Speaker label"
          aria-label="Speaker label"
          onClick={e => e.stopPropagation()}
          style={{ flex: 1, padding: '3px 8px', borderRadius: 4, border: '1px solid #d1d5db', fontSize: 12, background: '#fff' }}
        />
      </div>

      {/* Transcript text */}
      <div style={{ marginBottom: 8 }}>
        {editing ? (
          <textarea
            value={editText}
            onChange={e => setEditText(e.target.value)}
            onClick={e => e.stopPropagation()}
            style={{ width: '100%', minHeight: 60, padding: '8px 10px', borderRadius: 6, border: '1px solid #2563eb', fontSize: 13, resize: 'vertical', fontFamily: 'inherit', lineHeight: 1.5 }}
            autoFocus
          />
        ) : (
          <div
            onClick={() => setEditing(true)}
            style={{
              fontSize: 13, lineHeight: 1.6, whiteSpace: 'pre-wrap',
              background: '#f9fafb', padding: '8px 10px', borderRadius: 6,
              border: '1px solid transparent', cursor: 'text', minHeight: 40,
              color: '#1a1a1a',
            }}
            role="button"
            tabIndex={0}
            onKeyDown={e => e.key === 'Enter' && setEditing(true)}
            aria-label="Click to edit transcript"
          >
            {segment.text || <em style={{ color: '#9ca3af' }}>No transcript for this chunk yet.</em>}
          </div>
        )}
      </div>

      {/* Actions row */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
        {editing ? (
          <>
            <button
              onClick={e => { e.stopPropagation(); handleSaveEdit(); }}
              style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 4, fontSize: 11, cursor: 'pointer' }}
            >
              <Check size={11} /> Save
            </button>
            <button
              onClick={e => { e.stopPropagation(); handleCancelEdit(); }}
              style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px', background: '#f3f4f6', color: '#374151', border: 'none', borderRadius: 4, fontSize: 11, cursor: 'pointer' }}
            >
              Cancel
            </button>
          </>
        ) : (
          <button
            onClick={e => { e.stopPropagation(); setEditing(true); }}
            style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px', background: '#eff6ff', color: '#1e40af', border: 'none', borderRadius: 4, fontSize: 11, cursor: 'pointer' }}
          >
            <Edit3 size={11} /> Edit
          </button>
        )}
        <button
          onClick={e => { e.stopPropagation(); handleReviewed(); }}
          aria-pressed={segment.reviewed}
          style={{
            display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px',
            background: segment.reviewed ? '#dcfce7' : '#f3f4f6',
            color: segment.reviewed ? '#166534' : '#374151',
            border: 'none', borderRadius: 4, fontSize: 11, cursor: 'pointer',
          }}
        >
          <CheckCircle size={11} />
          {segment.reviewed ? 'Reviewed' : 'Mark Reviewed'}
        </button>

        {/* Chunk audio */}
        <div onClick={e => e.stopPropagation()}>
          <ChunkAudioPlayer
            jobId={jobId}
            chunk={segment as any}
            apiBase={apiBase}
            isPlaying={isPlaying}
            onPlayToggle={onPlayToggle}
          />
        </div>
      </div>

      {/* Edit notice */}
      {segment.edited && (
        <div style={{ fontSize: 10, color: '#7c3aed', marginTop: 4 }}>
          Proofreading edits are local-only until backend save is added.
        </div>
      )}
    </div>
  );
}

export default function TranscriptProofreadingPanel({ job, onClose, apiBase = '' }: TranscriptProofreadingPanelProps) {
  const {
    buildSegments,
    undo,
    redo,
    canUndo,
    canRedo,
    storageWarning,
    setReviewed,
    markAllReviewed,
    setPlayingChunk,
    setActiveChunk,
  } = useProofreadingContext();

  const [activeChunkId, setActiveChunkId] = useState<string | null>(null);
  const [playingChunkId, setPlayingChunkId] = useState<string | null>(null);

  const segments = buildSegments(job.chunks, job.job_id);

  const handleSegmentClick = (chunkId: string) => {
    setActiveChunkId(prev => prev === chunkId ? null : chunkId);
    if (job.chunks[0]) {
      setActiveChunk(job.job_id, chunkId);
    }
  };

  const handlePlayToggle = (chunkId: string) => {
    setPlayingChunkId(prev => prev === chunkId ? null : chunkId);
    setPlayingChunk(job.job_id, chunkId);
  };

  const handleMarkAllReviewed = () => {
    markAllReviewed(job.job_id, job.chunks.map(c => c.chunk_id));
  };

  const allReviewed = job.chunks.every(c =>
    segments.find(s => s.id === c.chunk_id)?.reviewed
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: '#7c3aed', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Edit3 size={16} style={{ color: 'white' }} />
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700 }}>Proofreading Mode</div>
            <div style={{ fontSize: 11, color: '#9ca3af' }}>Local edits — not saved to backend</div>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button
            onClick={undo}
            disabled={!canUndo}
            aria-label="Undo"
            title="Undo"
            style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '6px 10px', background: canUndo ? '#f3f4f6' : '#f3f4f6', color: canUndo ? '#374151' : '#ccc', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 12, cursor: canUndo ? 'pointer' : 'not-allowed' }}
          >
            <Undo2 size={13} /> Undo
          </button>
          <button
            onClick={redo}
            disabled={!canRedo}
            aria-label="Redo"
            title="Redo"
            style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '6px 10px', background: canRedo ? '#f3f4f6' : '#f3f4f6', color: canRedo ? '#374151' : '#ccc', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 12, cursor: canRedo ? 'pointer' : 'not-allowed' }}
          >
            <Redo2 size={13} /> Redo
          </button>
          {onClose && (
            <button
              onClick={onClose}
              aria-label="Close proofreading panel"
              style={{ padding: '6px 10px', background: '#f3f4f6', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 12, cursor: 'pointer' }}
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Storage warning */}
      {storageWarning && (
        <div style={{ padding: '8px 12px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 6, fontSize: 12, color: '#dc2626', display: 'flex', alignItems: 'center', gap: 6 }}>
          <AlertTriangle size={13} /> {storageWarning}
        </div>
      )}

      {/* Audio sync notice */}
      <div style={{ padding: '8px 12px', background: '#f5f3ef', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 11, color: '#6b7280' }}>
        Full-transcript audio sync requires a full-job audio endpoint. Current mode supports chunk-level proofing.
      </div>

      {/* Segment count + bulk actions */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: 12, color: '#6b7280' }}>
          {segments.length} segments · {segments.filter(s => s.reviewed).length} reviewed
        </span>
        <button
          onClick={handleMarkAllReviewed}
          disabled={allReviewed}
          aria-label="Mark all segments as reviewed"
          style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '5px 10px', background: allReviewed ? '#f3f4f6' : '#dcfce7', color: allReviewed ? '#9ca3af' : '#166534', border: 'none', borderRadius: 6, fontSize: 11, cursor: allReviewed ? 'not-allowed' : 'pointer' }}
        >
          <CheckCircle size={11} /> Mark All Reviewed
        </button>
      </div>

      {/* Segment list */}
      <div role="list" aria-label="Transcript segments for proofreading">
        {segments.map(segment => (
          <div key={segment.id} role="listitem">
            <SegmentEditor
              segment={segment}
              jobId={job.job_id}
              isActive={activeChunkId === segment.id}
              isPlaying={playingChunkId === segment.id}
              onPlayToggle={() => handlePlayToggle(segment.id)}
              apiBase={apiBase}
              hasFullAudio={false}
              onSegmentClick={() => handleSegmentClick(segment.id)}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
