/**
 * useLifeReferenceShelf — localStorage persistence + React context for immediate UI updates
 * v10 Phase 1 extension — no backend changes required
 */

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';

const STORAGE_KEY = 'archiveforge_life_references';

// ── Types ──────────────────────────────────────────────────────────────────────

export interface SavedLifeReference {
  id: string;
  source?: string;
  google_books_volume_id?: string;
  date: string;
  volume: number | null;
  issue_number: number | null;
  cover_subject: string;
  issue_title?: string;
  volume_label?: string;
  reference_cover_url: string;
  cover_thumbnail_url?: string;
  cover_preview_url?: string;
  search_query_used?: string;
  match_reason?: string;
  rarity_notes: string;
  tier_guidance: string;
  keywords: string;
  match_score?: number;
  savedAt: string;
  sourceType: 'google_books' | 'local_fixture' | 'internet_archive';
}

type ReferenceLike = Pick<SavedLifeReference,
  | 'id' | 'source' | 'google_books_volume_id' | 'date' | 'volume' | 'issue_number'
  | 'cover_subject' | 'issue_title' | 'volume_label' | 'reference_cover_url'
  | 'cover_thumbnail_url' | 'cover_preview_url' | 'search_query_used'
  | 'match_reason' | 'rarity_notes' | 'tier_guidance' | 'keywords' | 'match_score'
>;

// ── Storage helpers ────────────────────────────────────────────────────────────

export function getSavedReferences(): SavedLifeReference[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function _persist(items: SavedLifeReference[]) {
  if (typeof window !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items.slice(0, 50)));
  }
}

// ── Context ────────────────────────────────────────────────────────────────────

interface ShelfContextValue {
  saved: SavedLifeReference[];
  saveReference: (ref: ReferenceLike) => void;
  removeReference: (key: string) => void;
  getReference: (key: string) => SavedLifeReference | undefined;
  clearAll: () => void;
}

const ShelfContext = createContext<ShelfContextValue | null>(null);

export function LifeReferenceShelfProvider({ children }: { children: ReactNode }) {
  const [saved, setSaved] = useState<SavedLifeReference[]>([]);

  // Init from localStorage on mount
  useEffect(() => {
    setSaved(getSavedReferences());
  }, []);

  const saveReference = useCallback((ref: ReferenceLike) => {
    const key = ref.google_books_volume_id || ref.id;
    setSaved(prev => {
      if (prev.some(s => (s.google_books_volume_id || s.id) === key)) return prev;
      const next: SavedLifeReference = {
        id: ref.id,
        source: ref.source,
        google_books_volume_id: ref.google_books_volume_id,
        date: ref.date,
        volume: ref.volume,
        issue_number: ref.issue_number,
        cover_subject: ref.cover_subject,
        issue_title: ref.issue_title,
        volume_label: ref.volume_label,
        reference_cover_url: ref.reference_cover_url,
        cover_thumbnail_url: ref.cover_thumbnail_url,
        cover_preview_url: ref.cover_preview_url,
        search_query_used: ref.search_query_used,
        match_reason: ref.match_reason,
        rarity_notes: ref.rarity_notes,
        tier_guidance: ref.tier_guidance,
        keywords: ref.keywords,
        match_score: ref.match_score,
        savedAt: new Date().toISOString(),
        sourceType: (ref.source as SavedLifeReference['sourceType']) || 'google_books',
      };
      const updated = [next, ...prev].slice(0, 50);
      _persist(updated);
      return updated;
    });
  }, []);

  const removeReference = useCallback((key: string) => {
    setSaved(prev => {
      const updated = prev.filter(s => (s.google_books_volume_id || s.id) !== key);
      _persist(updated);
      return updated;
    });
  }, []);

  const getReference = useCallback((key: string) =>
    saved.find(s => (s.google_books_volume_id || s.id) === key),
    [saved]
  );

  const clearAll = useCallback(() => {
    setSaved([]);
    _persist([]);
  }, []);

  return (
    <ShelfContext.Provider value={{ saved, saveReference, removeReference, getReference, clearAll }}>
      {children}
    </ShelfContext.Provider>
  );
}

export function useShelfContext(): ShelfContextValue {
  const ctx = useContext(ShelfContext);
  if (!ctx) throw new Error('useShelfContext must be used within LifeReferenceShelfProvider');
  return ctx;
}

// ── Legacy functions (for non-context usage) ──────────────────────────────────

export function saveReference(ref: ReferenceLike) {
  const key = ref.google_books_volume_id || ref.id;
  const existing = getSavedReferences();
  if (existing.some(s => (s.google_books_volume_id || s.id) === key)) return;
  const item: SavedLifeReference = {
    id: ref.id,
    source: ref.source,
    google_books_volume_id: ref.google_books_volume_id,
    date: ref.date,
    volume: ref.volume,
    issue_number: ref.issue_number,
    cover_subject: ref.cover_subject,
    issue_title: ref.issue_title,
    volume_label: ref.volume_label,
    reference_cover_url: ref.reference_cover_url,
    cover_thumbnail_url: ref.cover_thumbnail_url,
    cover_preview_url: ref.cover_preview_url,
    search_query_used: ref.search_query_used,
    match_reason: ref.match_reason,
    rarity_notes: ref.rarity_notes,
    tier_guidance: ref.tier_guidance,
    keywords: ref.keywords,
    match_score: ref.match_score,
    savedAt: new Date().toISOString(),
    sourceType: (ref.source as SavedLifeReference['sourceType']) || 'google_books',
  };
  _persist([item, ...existing].slice(0, 50));
}

export function removeReference(key: string) {
  const updated = getSavedReferences().filter(s => (s.google_books_volume_id || s.id) !== key);
  _persist(updated);
}

export function clearAllReferences() {
  _persist([]);
}