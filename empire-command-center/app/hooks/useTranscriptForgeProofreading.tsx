/**
 * useTranscriptForgeProofreading — React Context + localStorage hook
 * Phase 1: Export + Proofreading UI
 * Phase 1.5 Hardening: TF-2 (Edit Patch), TF-4 (Confidence Calibration), TF-5 (Speaker Index)
 *
 * Manages:
 * - Speaker labels per job/chunk (localStorage: transcriptforge_speaker_labels)
 * - Local edits per job/chunk (localStorage: transcriptforge_local_edits)
 * - Reviewed segments per job (localStorage: transcriptforge_reviewed_segments)
 * - Undo/redo stack for edits
 * - Speaker index with fingerprint suggestions (localStorage: transcriptforge_speaker_index, limit 100)
 * - Confidence calibration entries (localStorage: transcriptforge_confidence_calibration)
 * - Edit patch export
 */

'use client';

import React, { createContext, useContext, useCallback, useState, useEffect } from 'react';
import type {
  ChunkInfo,
  TranscriptSegment,
  SpeakerLabelStore,
  LocalEditStore,
  ReviewedSegmentStore,
  ProofreadingSession,
  EditPatch,
  SpeakerIndexEntry,
  SpeakerIndexStore,
  ConfidenceCalibrationStore,
  ConfidenceCalibrationEntry,
  CalibrationVerdict,
} from '../schemas/transcriptforge-schemas';
import { chunkToSegment } from '../schemas/transcriptforge-schemas';

// ============================================================
// STORAGE KEYS
// ============================================================

const SPEAKER_KEY = 'transcriptforge_speaker_labels';
const EDITS_KEY = 'transcriptforge_local_edits';
const REVIEWED_KEY = 'transcriptforge_reviewed_segments';
const SPEAKER_INDEX_KEY = 'transcriptforge_speaker_index';
const CONFIDENCE_KEY = 'transcriptforge_confidence_calibration';
const MAX_UNDO = 50;
const SPEAKER_INDEX_MAX = 100;

// ============================================================
// CONTEXT
// ============================================================

interface ProofreadingContextValue {
  // Build segments from current job chunks
  buildSegments: (chunks: ChunkInfo[], jobId: string) => TranscriptSegment[];

  // Speaker labels
  getSpeakerLabel: (jobId: string, chunkId: string) => string;
  setSpeakerLabel: (jobId: string, chunkId: string, label: string) => void;
  renameSpeaker: (jobId: string, oldLabel: string, newLabel: string) => void;
  getUniqueSpeakers: (segments: TranscriptSegment[]) => string[];

  // Local edits
  getLocalEdit: (jobId: string, chunkId: string) => string | null;
  setLocalEdit: (jobId: string, chunkId: string, text: string) => void;
  clearLocalEdit: (jobId: string, chunkId: string) => void;

  // Reviewed state
  isReviewed: (jobId: string, chunkId: string) => boolean;
  setReviewed: (jobId: string, chunkId: string, reviewed: boolean) => void;
  markAllReviewed: (jobId: string, chunkIds: string[]) => void;

  // Undo/redo
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;

  // Active session
  session: ProofreadingSession | null;
  setActiveChunk: (jobId: string, chunkId: string | null) => void;
  setPlayingChunk: (jobId: string, chunkId: string | null) => void;

  // Storage status
  storageWarning: string | null;

  // TF-2: Edit patch export
  exportEditPatch: (jobId: string, segments: TranscriptSegment[]) => EditPatch;

  // TF-5: Speaker index suggestions
  getSpeakerSuggestions: (text: string) => SpeakerIndexEntry[];
  recordSpeakerUsage: (label: string, jobId: string) => void;

  // TF-4: Confidence calibration
  getCalibration: (jobId: string, chunkId: string) => ConfidenceCalibrationEntry | null;
  setCalibration: (jobId: string, chunkId: string, verdict: CalibrationVerdict, note?: string) => void;
  getLowConfidenceSegments: (segments: TranscriptSegment[]) => TranscriptSegment[];
}

const ProofreadingContext = createContext<ProofreadingContextValue | null>(null);

// ============================================================
// UNDO STACK
// ============================================================

type UndoAction =
  | { type: 'set_edit'; jobId: string; chunkId: string; oldText: string | null; newText: string }
  | { type: 'set_speaker'; jobId: string; chunkId: string; oldLabel: string; newLabel: string };

// ============================================================
// PROVIDER
// ============================================================

export function ProofreadingProvider({ children }: { children: React.ReactNode }) {
  const [speakerStore, setSpeakerStore] = useState<SpeakerLabelStore>({});
  const [editStore, setEditStore] = useState<LocalEditStore>({});
  const [reviewedStore, setReviewedStore] = useState<ReviewedSegmentStore>({});
  const [speakerIndex, setSpeakerIndex] = useState<SpeakerIndexStore>({});
  const [calibrationStore, setCalibrationStore] = useState<ConfidenceCalibrationStore>({});
  const [undoStack, setUndoStack] = useState<UndoAction[]>([]);
  const [redoStack, setUndoStackRedo] = useState<UndoAction[]>([]);
  const [session, setSession] = useState<ProofreadingSession | null>(null);
  const [storageWarning, setStorageWarning] = useState<string | null>(null);

  // Load all from localStorage on mount
  useEffect(() => {
    try {
      const sp = localStorage.getItem(SPEAKER_KEY);
      if (sp) setSpeakerStore(JSON.parse(sp));
      const ed = localStorage.getItem(EDITS_KEY);
      if (ed) setEditStore(JSON.parse(ed));
      const rev = localStorage.getItem(REVIEWED_KEY);
      if (rev) setReviewedStore(JSON.parse(rev));
      const idx = localStorage.getItem(SPEAKER_INDEX_KEY);
      if (idx) setSpeakerIndex(JSON.parse(idx));
      const cal = localStorage.getItem(CONFIDENCE_KEY);
      if (cal) setCalibrationStore(JSON.parse(cal));
    } catch {
      console.warn('[TranscriptForge] [ProofreadingProvider] localStorage parse failed — using defaults');
    }
  }, []);

  const saveSpeakerStore = useCallback((store: SpeakerLabelStore) => {
    try {
      localStorage.setItem(SPEAKER_KEY, JSON.stringify(store));
      setSpeakerStore(store);
    } catch {
      setStorageWarning('localStorage quota exceeded — speaker labels will not persist.');
    }
  }, []);

  const saveEditStore = useCallback((store: LocalEditStore) => {
    try {
      localStorage.setItem(EDITS_KEY, JSON.stringify(store));
      setEditStore(store);
    } catch {
      setStorageWarning('localStorage quota exceeded — edits will not persist.');
    }
  }, []);

  const saveReviewedStore = useCallback((store: ReviewedSegmentStore) => {
    try {
      localStorage.setItem(REVIEWED_KEY, JSON.stringify(store));
      setReviewedStore(store);
    } catch {
      setStorageWarning('localStorage quota exceeded — reviewed state will not persist.');
    }
  }, []);

  const saveSpeakerIndex = useCallback((store: SpeakerIndexStore) => {
    try {
      localStorage.setItem(SPEAKER_INDEX_KEY, JSON.stringify(store));
      setSpeakerIndex(store);
    } catch {
      console.warn('[TranscriptForge] [SpeakerIndex] localStorage quota exceeded — index will not persist');
    }
  }, []);

  const saveCalibrationStore = useCallback((store: ConfidenceCalibrationStore) => {
    try {
      localStorage.setItem(CONFIDENCE_KEY, JSON.stringify(store));
      setCalibrationStore(store);
    } catch {
      console.warn('[TranscriptForge] [ConfidenceCalibration] localStorage quota exceeded — calibration will not persist');
    }
  }, []);

  // ── Build segments ──────────────────────────────────────────

  const buildSegments = useCallback((chunks: ChunkInfo[], jobId: string): TranscriptSegment[] => {
    return chunks.map(chunk => {
      const speakerLabel = (speakerStore[jobId] || {})[chunk.chunk_id] || 'Unknown Speaker';
      const localEdit = (editStore[jobId] || {})[chunk.chunk_id] || null;
      const isReviewed = ((reviewedStore[jobId] || []).includes(chunk.chunk_id));
      return chunkToSegment(chunk, speakerLabel, localEdit, isReviewed);
    });
  }, [speakerStore, editStore, reviewedStore]);

  // ── Speaker labels ───────────────────────────────────────────

  const getSpeakerLabel = useCallback((jobId: string, chunkId: string): string => {
    return (speakerStore[jobId] || {})[chunkId] || 'Unknown Speaker';
  }, [speakerStore]);

  const setSpeakerLabel = useCallback((jobId: string, chunkId: string, label: string) => {
    const oldLabel = getSpeakerLabel(jobId, chunkId);
    const newStore = { ...speakerStore, [jobId]: { ...(speakerStore[jobId] || {}), [chunkId]: label } };
    saveSpeakerStore(newStore);
    pushUndo({ type: 'set_speaker', jobId, chunkId, oldLabel, newLabel: label });
  }, [speakerStore, saveSpeakerStore, getSpeakerLabel]);

  const renameSpeaker = useCallback((jobId: string, oldLabel: string, newLabel: string) => {
    if (!oldLabel || !newLabel || oldLabel === newLabel) return;
    const jobLabels = speakerStore[jobId] || {};
    const newJobLabels: Record<string, string> = {};
    Object.entries(jobLabels).forEach(([chunkId, label]) => {
      newJobLabels[chunkId] = label === oldLabel ? newLabel : label;
    });
    saveSpeakerStore({ ...speakerStore, [jobId]: newJobLabels });
  }, [speakerStore, saveSpeakerStore]);

  const getUniqueSpeakers = useCallback((segments: TranscriptSegment[]): string[] => {
    const labels = segments.map(s => s.speaker).filter(Boolean);
    return [...new Set(labels)];
  }, []);

  // ── Local edits ────────────────────────────────────────────

  const getLocalEdit = useCallback((jobId: string, chunkId: string): string | null => {
    return (editStore[jobId] || {})[chunkId] || null;
  }, [editStore]);

  const setLocalEdit = useCallback((jobId: string, chunkId: string, text: string) => {
    const oldText = getLocalEdit(jobId, chunkId);
    const newStore = { ...editStore, [jobId]: { ...(editStore[jobId] || {}), [chunkId]: text } };
    saveEditStore(newStore);
    pushUndo({ type: 'set_edit', jobId, chunkId, oldText, newText: text });
  }, [editStore, saveEditStore, getLocalEdit]);

  const clearLocalEdit = useCallback((jobId: string, chunkId: string) => {
    const oldText = getLocalEdit(jobId, chunkId);
    const jobEdits = { ...editStore[jobId] };
    delete jobEdits[chunkId];
    const newStore = { ...editStore, [jobId]: jobEdits };
    saveEditStore(newStore);
    if (oldText !== null) {
      pushUndo({ type: 'set_edit', jobId, chunkId, oldText, newText: '' });
    }
  }, [editStore, saveEditStore, getLocalEdit]);

  // ── Reviewed state ─────────────────────────────────────────

  const isReviewed = useCallback((jobId: string, chunkId: string): boolean => {
    return (reviewedStore[jobId] || []).includes(chunkId);
  }, [reviewedStore]);

  const setReviewed = useCallback((jobId: string, chunkId: string, reviewed: boolean) => {
    const current = reviewedStore[jobId] || [];
    let next: string[];
    if (reviewed) {
      next = current.includes(chunkId) ? current : [...current, chunkId];
    } else {
      next = current.filter(id => id !== chunkId);
    }
    saveReviewedStore({ ...reviewedStore, [jobId]: next });
  }, [reviewedStore, saveReviewedStore]);

  const markAllReviewed = useCallback((jobId: string, chunkIds: string[]) => {
    const current = reviewedStore[jobId] || [];
    const next = [...new Set([...current, ...chunkIds])];
    saveReviewedStore({ ...reviewedStore, [jobId]: next });
  }, [reviewedStore, saveReviewedStore]);

  // ── Undo/redo ────────────────────────────────────────────────

  const pushUndo = (action: UndoAction) => {
    setUndoStack(prev => [...prev.slice(-MAX_UNDO + 1), action]);
    setUndoStackRedo([]);
  };

  const undo = useCallback(() => {
    const action = undoStack[undoStack.length - 1];
    if (!action) return;
    if (action.type === 'set_edit') {
      const jobEdits = { ...editStore[action.jobId] };
      if (action.oldText) {
        jobEdits[action.chunkId] = action.oldText;
      } else {
        delete jobEdits[action.chunkId];
      }
      saveEditStore({ ...editStore, [action.jobId]: jobEdits });
    } else if (action.type === 'set_speaker') {
      const jobLabels = { ...speakerStore[action.jobId] || {} };
      jobLabels[action.chunkId] = action.oldLabel;
      saveSpeakerStore({ ...speakerStore, [action.jobId]: jobLabels });
    }
    setUndoStack(prev => prev.slice(0, -1));
    setUndoStackRedo(prev => [...prev, action]);
  }, [undoStack, editStore, speakerStore, saveEditStore, saveSpeakerStore]);

  const redo = useCallback(() => {
    const action = redoStack[redoStack.length - 1];
    if (!action) return;
    if (action.type === 'set_edit') {
      const newStore = { ...editStore, [action.jobId]: { ...(editStore[action.jobId] || {}), [action.chunkId]: action.newText } };
      saveEditStore(newStore);
    } else if (action.type === 'set_speaker') {
      const newStore = { ...speakerStore, [action.jobId]: { ...(speakerStore[action.jobId] || {}), [action.chunkId]: action.newLabel } };
      saveSpeakerStore(newStore);
    }
    setUndoStackRedo(prev => prev.slice(0, -1));
    setUndoStack(prev => [...prev, action]);
  }, [redoStack, editStore, speakerStore, saveEditStore, saveSpeakerStore]);

  // ── Session helpers ─────────────────────────────────────────

  const setActiveChunk = useCallback((jobId: string, chunkId: string | null) => {
    setSession(prev => prev?.jobId === jobId
      ? { ...prev, activeSegmentId: chunkId }
      : { jobId, segments: [], activeSegmentId: chunkId, playingChunkId: null }
    );
  }, []);

  const setPlayingChunk = useCallback((jobId: string, chunkId: string | null) => {
    setSession(prev => prev?.jobId === jobId
      ? { ...prev, playingChunkId: chunkId }
      : null
    );
  }, []);

  // ── TF-2: Edit Patch Export ──────────────────────────────────

  const exportEditPatch = useCallback((jobId: string, segments: TranscriptSegment[]): EditPatch => {
    const jobEdits = editStore[jobId] || {};
    const edits = Object.entries(jobEdits).map(([chunkId, editedText]) => {
      const segment = segments.find(s => s.id === chunkId);
      return {
        chunkId,
        originalText: segment?.text || undefined,
        editedText,
        speakerLabel: segment?.speaker || undefined,
        reviewed: segment?.reviewed || false,
        editedAt: new Date().toISOString(),
      };
    });
    return {
      jobId,
      exportedAt: new Date().toISOString(),
      source: 'localStorage',
      edits,
    };
  }, [editStore]);

  // ── TF-5: Speaker Index ───────────────────────────────────────

  /**
   * Simple non-sensitive fingerprint from speaker label text.
   * Uses first 3 chars + length to avoid storing raw audio or biometric data.
   * Does NOT use audio fingerprints, biometric identifiers, or raw speaker data.
   */
  function fingerprintFromLabel(label: string): string {
    const normalized = label.trim().toLowerCase();
    const prefix = normalized.slice(0, 3);
    const len = normalized.length;
    // Simple non-cryptographic hash for index lookup
    let hash = 0;
    for (let i = 0; i < normalized.length; i++) {
      hash = ((hash << 5) - hash) + normalized.charCodeAt(i);
      hash |= 0;
    }
    return `${prefix}_${len}_${Math.abs(hash).toString(36).slice(-6)}`;
  }

  const getSpeakerSuggestions = useCallback((text: string): SpeakerIndexEntry[] => {
    if (!text) return [];
    const fp = fingerprintFromLabel(text);
    const match = Object.values(speakerIndex).find(e => e.fingerprintHash === fp);
    return match ? [match] : [];
  }, [speakerIndex]);

  const recordSpeakerUsage = useCallback((label: string, jobId: string) => {
    const fp = fingerprintFromLabel(label);
    const existing = speakerIndex[fp];
    const now = new Date().toISOString();

    let next: SpeakerIndexStore;
    if (existing) {
      // Update existing entry
      next = {
        ...speakerIndex,
        [fp]: {
          ...existing,
          lastSeenAt: now,
          jobIds: existing.jobIds.includes(jobId) ? existing.jobIds : [...existing.jobIds, jobId],
          usageCount: existing.usageCount + 1,
        },
      };
    } else {
      // Add new entry, evict oldest if at limit
      const entries = Object.values(speakerIndex);
      if (entries.length >= SPEAKER_INDEX_MAX) {
        // Evict oldest by lastSeenAt
        const oldest = entries.reduce((min, e) => e.lastSeenAt < min.lastSeenAt ? e : min, entries[0]);
        console.warn(`[TranscriptForge] [SpeakerIndex] index full — evicted oldest entry for ${oldest.fingerprintHash}`);
        const { [oldest.fingerprintHash]: _, ...rest } = speakerIndex;
        next = {
          ...rest,
          [fp]: {
            fingerprintHash: fp,
            speakerLabel: label,
            lastSeenAt: now,
            jobIds: [jobId],
            usageCount: 1,
          },
        };
      } else {
        next = {
          ...speakerIndex,
          [fp]: {
            fingerprintHash: fp,
            speakerLabel: label,
            lastSeenAt: now,
            jobIds: [jobId],
            usageCount: 1,
          },
        };
      }
    }
    saveSpeakerIndex(next);
  }, [speakerIndex, saveSpeakerIndex]);

  // ── TF-4: Confidence Calibration ─────────────────────────────

  const getCalibration = useCallback((jobId: string, chunkId: string): ConfidenceCalibrationEntry | null => {
    const key = `${jobId}_${chunkId}`;
    return calibrationStore[key] || null;
  }, [calibrationStore]);

  const setCalibration = useCallback((jobId: string, chunkId: string, verdict: CalibrationVerdict, note?: string) => {
    const key = `${jobId}_${chunkId}`;
    const next: ConfidenceCalibrationStore = {
      ...calibrationStore,
      [key]: {
        jobId,
        chunkId,
        confidence: null,
        verdict,
        note,
        reviewedAt: new Date().toISOString(),
      },
    };
    saveCalibrationStore(next);
  }, [calibrationStore, saveCalibrationStore]);

  const getLowConfidenceSegments = useCallback((segments: TranscriptSegment[]): TranscriptSegment[] => {
    return segments.filter(s => s.confidence !== null && s.confidence < 0.7);
  }, []);

  const value: ProofreadingContextValue = {
    buildSegments,
    getSpeakerLabel,
    setSpeakerLabel,
    renameSpeaker,
    getUniqueSpeakers,
    getLocalEdit,
    setLocalEdit,
    clearLocalEdit,
    isReviewed,
    setReviewed,
    markAllReviewed,
    undo,
    redo,
    canUndo: undoStack.length > 0,
    canRedo: redoStack.length > 0,
    session,
    setActiveChunk,
    setPlayingChunk,
    storageWarning,
    exportEditPatch,
    getSpeakerSuggestions,
    recordSpeakerUsage,
    getCalibration,
    setCalibration,
    getLowConfidenceSegments,
  };

  return (
    <ProofreadingContext.Provider value={value}>
      {children}
    </ProofreadingContext.Provider>
  );
}

// ============================================================
// HOOK
// ============================================================

export function useProofreadingContext(): ProofreadingContextValue {
  const ctx = useContext(ProofreadingContext);
  if (!ctx) throw new Error('useProofreadingContext must be used within ProofreadingProvider');
  return ctx;
}