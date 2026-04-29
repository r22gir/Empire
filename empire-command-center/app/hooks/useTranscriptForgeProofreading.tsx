/**
 * useTranscriptForgeProofreading — React Context + localStorage hook
 * Phase 1: Export + Proofreading UI
 *
 * Manages:
 * - Speaker labels per job/chunk (localStorage: transcriptforge_speaker_labels)
 * - Local edits per job/chunk (localStorage: transcriptforge_local_edits)
 * - Reviewed segments per job (localStorage: transcriptforge_reviewed_segments)
 * - Undo/redo stack for edits
 */

'use client';

import React, { createContext, useContext, useCallback, useState, useEffect } from 'react';
import type { ChunkInfo } from '../schemas/transcriptforge-schemas';
import type {
  TranscriptSegment,
  SpeakerLabelStore,
  LocalEditStore,
  ReviewedSegmentStore,
  ProofreadingSession,
} from '../schemas/transcriptforge-schemas';
import { chunkToSegment } from '../schemas/transcriptforge-schemas';

// ============================================================
// STORAGE KEYS
// ============================================================

const SPEAKER_KEY = 'transcriptforge_speaker_labels';
const EDITS_KEY = 'transcriptforge_local_edits';
const REVIEWED_KEY = 'transcriptforge_reviewed_segments';
const MAX_UNDO = 50;

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
  const [undoStack, setUndoStack] = useState<UndoAction[]>([]);
  const [redoStack, setUndoStackRedo] = useState<UndoAction[]>([]);
  const [session, setSession] = useState<ProofreadingSession | null>(null);
  const [storageWarning, setStorageWarning] = useState<string | null>(null);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const sp = localStorage.getItem(SPEAKER_KEY);
      if (sp) setSpeakerStore(JSON.parse(sp));
      const ed = localStorage.getItem(EDITS_KEY);
      if (ed) setEditStore(JSON.parse(ed));
      const rev = localStorage.getItem(REVIEWED_KEY);
      if (rev) setReviewedStore(JSON.parse(rev));
    } catch {
      setStorageWarning('localStorage unavailable — edits will not persist.');
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
