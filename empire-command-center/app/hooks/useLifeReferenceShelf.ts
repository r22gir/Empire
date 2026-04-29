/**
 * useLifeReferenceShelf — localStorage persistence for saved LIFE references
 * v10 Phase 1 extension — no backend changes required
 */

const STORAGE_KEY = 'archiveforge_life_references';

export interface SavedLifeReference {
  // Inherit all LifeReferenceIssue fields via spread
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
  // Saved-specific fields
  savedAt: string;
  sourceType: 'google_books' | 'local_fixture' | 'internet_archive';
}

export function getSavedReferences(): SavedLifeReference[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

/** Minimal shape that saveReference needs from caller */
type ReferenceLike = {
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
};

export function saveReference(issue: ReferenceLike): void {
  const saved = getSavedReferences();
  const key = issue.google_books_volume_id || issue.id;
  // Don't duplicate
  if (saved.some(s => (s.google_books_volume_id || s.id) === key)) return;
  const savedRef: SavedLifeReference = {
    id: issue.id,
    source: issue.source,
    google_books_volume_id: issue.google_books_volume_id,
    date: issue.date,
    volume: issue.volume,
    issue_number: issue.issue_number,
    cover_subject: issue.cover_subject,
    issue_title: issue.issue_title,
    volume_label: issue.volume_label,
    reference_cover_url: issue.reference_cover_url,
    cover_thumbnail_url: issue.cover_thumbnail_url,
    cover_preview_url: issue.cover_preview_url,
    search_query_used: issue.search_query_used,
    match_reason: issue.match_reason,
    rarity_notes: issue.rarity_notes,
    tier_guidance: issue.tier_guidance,
    keywords: issue.keywords,
    match_score: issue.match_score,
    savedAt: new Date().toISOString(),
    sourceType: issue.source === 'google_books' ? 'google_books'
      : issue.source === 'local_reference_fixture' ? 'local_fixture'
      : 'google_books',
  };
  saved.unshift(savedRef);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(saved.slice(0, 50))); // max 50
}

export function removeReference(key: string): void {
  const saved = getSavedReferences().filter(
    s => (s.google_books_volume_id || s.id) !== key
  );
  localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
}

export function getReference(key: string): SavedLifeReference | undefined {
  return getSavedReferences().find(
    s => (s.google_books_volume_id || s.id) === key
  );
}

export function clearAllReferences(): void {
  localStorage.removeItem(STORAGE_KEY);
}