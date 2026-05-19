'use client';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Search, Package, Camera, Archive, CheckCircle, List,
  Table2, ChevronRight, ChevronDown, Upload, X, Loader2,
  AlertTriangle, Check, Tag, FolderOpen, Box, ArrowRight,
  RefreshCw, Filter, Download, Eye, Plus, Trash2, Star, Award, Layers,
} from 'lucide-react';

const API = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
  ? 'https://api.empirebox.store/api/v1'
  : (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1');

const AG_API = `${API}/archiveforge`;
const SUPPORTED_UPLOAD_MIME_TYPES = new Set(['image/jpeg', 'image/png', 'image/gif', 'image/webp']);

// ── Types ──────────────────────────────────────────────────────────────────────

interface LifeReferenceIssue {
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
}

interface ArchiveItem {
  id: number;
  reference_issue_id: string;
  reference_source: string;
  google_books_volume_id: string;
  issue_title: string;
  volume_label: string;
  cover_thumbnail_url: string;
  cover_preview_url: string;
  search_query_used: string;
  match_reason: string;
  issue_date: string;
  volume: number;
  issue_number: number;
  cover_subject: string;
  reference_cover_url: string;
  actual_listing_images: string[];
  source_box_code: string;
  source_slot_position: string;
  processed_box_code: string;
  processed_status: string;
  archive_location: string;
  reboxed_at: string | null;
  reboxed_by: string | null;
  condition_score: number;
  has_address_label: boolean;
  is_complete: boolean;
  defects: string;
  notes: string;
  tier: string;
  rough_comp_min: number;
  rough_comp_max: number;
  final_price: number | null;
  sale_plan: string;
  listing_title: string;
  listing_description: string;
  item_specifics: Record<string, string>;
  batch_tag: string;
  marketforge_category_id: string;
  marketforge_ships_from_zip: string;
  listing_status: string;
  marketforge_listing_id: string;
  marketforge_push_status: string;
  marketforge_pushed_at: string;
  marketforge_error_message: string;
  created_at: string;
  updated_at: string;
  archive_id?: number;
  display_title?: string;
  short_description?: string;
  is_life_magazine?: boolean;
  issue_info_status?: string;
  ad_opportunity_status?: string;
  ad_opportunity_ready?: boolean;
  pricing_status?: string;
  is_test_record?: boolean;
  needs_review?: boolean;
  front_photo_present?: boolean;
  ad_page_photo_count?: number;
  verified_ad_count?: number;
  front_photo_url?: string;
  thumbnail_url?: string;
  status_badges?: string[];
}

interface DraftOutput {
  draft_id: number;
  listing_title: string;
  description: string;
  item_specifics: Record<string, string>;
  marketforge_payload: any;
  batch_tag: string;
  status: string;
}

interface ListingPacketDraft {
  draft_id: number;
  draft_status: string;
  platform_target: string;
  title: string;
  description: string;
  recommended_price?: number | null;
  missing_fields?: string[];
  draft?: {
    draft_id?: number;
    draft_status?: string;
    platform_target?: string;
    title?: string;
    recommended_price?: number | null;
    missing_fields?: string[];
  };
}

interface PhotoRecord {
  id: number;
  photo_id?: number;
  archive_id: number;
  role: string;
  filename: string;
  original_name: string;
  file_path: string;
  image_path?: string;
  photo_url?: string;
  thumbnail_url?: string;
  mime_type?: string;
  file_size?: number;
  file_size_bytes?: number;
  analysis_status?: string;
  candidate_id?: number | null;
  page_number?: string;
  created_at: string;
}

interface IdentifyAiResult {
  is_life_magazine?: boolean;
  confidence?: number;
  issue_date?: string | null;
  cover_title?: string | null;
  visible_text?: string[];
  subject_description?: string | null;
  condition_notes?: string | null;
  tier?: string;
  pricing_basis?: string | null;
  recommended_price_range?: { low?: number | null; high?: number | null };
  evidence_source?: string;
  reasoning_summary?: string;
  google_books_candidates?: GoogleBooksCandidate[];
  selected_google_books_candidate?: GoogleBooksCandidate | null;
  needs_user_confirmation?: boolean;
}

interface GoogleBooksCandidate {
  volume_id?: string;
  title?: string;
  publishedDate?: string;
  publisher?: string;
  pageCount?: number | null;
  cover_image_url?: string;
  preview_link?: string;
  info_link?: string;
  web_reader_link?: string;
  match_confidence?: number;
  query?: string;
  lookup_status?: string;
  cache_hit?: boolean;
}

interface IdentifyResponse {
  archive_id: number;
  photo_id?: number;
  image_path?: string;
  file_size_bytes?: number;
  mime_type?: string;
  identify_run_id?: string;
  identified_at?: string;
  stale_result_used?: boolean;
  identified: boolean;
  provider: string;
  capability: string;
  image?: {
    exists?: boolean;
    readable?: boolean;
    mime_type?: string;
    image_path?: string;
    file_size_bytes?: number;
    supported_mime_type?: boolean;
  };
  ai_result: IdentifyAiResult;
  google_books_candidates?: GoogleBooksCandidate[];
  selected_google_books_candidate?: GoogleBooksCandidate | null;
  needs_user_confirmation?: boolean;
  archive_updated: boolean;
}

interface IssueInfoRun {
  id?: number;
  run_id?: number;
  archive_id: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'stale' | 'not_run';
  front_photo_id?: number | null;
  image_path?: string;
  file_size_bytes?: number;
  mime_type?: string;
  is_life_magazine?: boolean;
  confidence?: number;
  issue_date?: string | null;
  cover_title?: string | null;
  detected_subject?: string | null;
  detected_quote?: string | null;
  detected_price?: string | null;
  visible_text?: string[];
  condition_notes?: string | null;
  evidence_source?: string;
  evidence_grade?: string;
  google_books_candidates?: GoogleBooksCandidate[];
  selected_google_books_volume_id?: string;
  selected_google_books_candidate?: GoogleBooksCandidate | null;
  reference_sources?: Array<Record<string, any>>;
  conflicts?: Array<Record<string, any>>;
  dealer_reference?: Record<string, any> | null;
  needs_user_confirmation?: boolean;
  ad_opportunity_ready?: boolean;
  stale_result_used?: boolean;
  stale_warning?: string;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
}

interface MatchConfirmation {
  status: 'pending' | 'confirmed' | 'wrong' | 'manual';
  source: string;
  reference_id?: string;
  reference_url?: string;
  issue_date?: string | null;
  cover_title?: string | null;
  confidence?: number;
}

interface PricingResult {
  stage: string;
  pricing_type: string;
  true_comps_available: boolean;
  message: string;
  rough_comp_min: number;
  rough_comp_max: number;
  recommended_price?: number | null;
  sale_plan?: string;
  pricing_basis?: string;
  confidence?: string;
  warnings?: string[];
  pricing_summary?: any;
  comps?: any[];
  accepted?: boolean;
}

interface IssueMetadata {
  id?: number;
  source_volume_id?: string;
  issue_title?: string;
  issue_date?: string;
  publisher?: string;
  page_count?: number;
  description?: string;
  preview_link?: string;
  info_link?: string;
  web_reader_link?: string;
  cover_image_url?: string;
  lookup_status?: string;
  contents_available?: boolean;
  contents_limitation?: string;
}

interface GoogleBooksStatus {
  api_key_configured?: boolean;
  cooldown_active?: boolean;
  last_429_at?: string | null;
  calls_last_hour?: number;
  calls_today?: number;
  cache_entries?: number;
  known_seed_references_available?: boolean;
}

interface AdOpportunity {
  id: number;
  brand?: string;
  product?: string;
  category?: string;
  search_query?: string;
  evidence_grade?: string;
  evidence_source?: string;
  evidence_text?: string;
  verification_status?: string;
  estimated_low?: number | null;
  estimated_high?: number | null;
  comp_count?: number;
  sold_comp_count?: number;
  active_listing_count?: number;
  value_score?: number;
  comp_confidence?: string;
  policy_flags?: string[];
  recommendation?: string;
  suggested_action?: string;
  user_notes?: string;
  priority?: number;
  uploaded_photo_count?: number;
  analyzed_photo_count?: number;
}

interface AdComp {
  id: number;
  candidate_id: number;
  provider?: string;
  result_type?: string;
  title?: string;
  url?: string;
  price?: number | null;
  total_price?: number | null;
  notes?: string;
}

interface AdCompGroup {
  candidate: AdOpportunity;
  comps: AdComp[];
  summary?: {
    comp_count?: number;
    search_link_count?: number;
    sold_comp_count?: number;
    active_listing_count?: number;
    estimated_low?: number | null;
    estimated_high?: number | null;
    comp_confidence?: string;
  };
}

interface AdRanking {
  candidate_id: number;
  brand?: string;
  product?: string;
  category?: string;
  value_score?: number;
  comp_confidence?: string;
  comp_count?: number;
  sold_comp_count?: number;
  active_listing_count?: number;
  search_link_count?: number;
  estimated_low?: number | null;
  estimated_high?: number | null;
  verification_status?: string;
  suggested_action?: string;
  reasoning_summary?: string;
  policy_flags?: string[];
}

interface AdRecommendation {
  recommendation?: string;
  whole_magazine_estimate?: { low?: number | null; high?: number | null };
  verified_ad_estimate?: { low?: number | null; high?: number | null };
  candidate_ad_estimate?: { low?: number | null; high?: number | null };
  evidence_grade?: string;
  reasoning_summary?: string;
  next_action?: string;
}

const STATUSES = ["RAW","IDENTIFIED","PHOTOGRAPHED","VALUED","READY_TO_LIST","LISTED","SOLD","HOLD","REBOXED"];
const STATUS_COLORS: Record<string, string> = {
  RAW: '#9ca3af', IDENTIFIED: '#3b82f6', PHOTOGRAPHED: '#8b5cf6',
  VALUED: '#f59e0b', READY_TO_LIST: '#10b981', LISTED: '#06b6d4',
  SOLD: '#16a34a', HOLD: '#ef4444', REBOXED: '#6b7280',
};
const TIER_COLORS: Record<string, string> = { A: '#ef4444', B: '#f59e0b', C: '#6b7280' };
const TIER_LABELS: Record<string, string> = {
  A: 'Tier A — 1936–1945, iconic / historical',
  B: 'Tier B — 1950s–1960s themed / runs',
  C: 'Tier C — common issues / duplicates / bulk',
};
const BOX_SUGGESTIONS = ["A-RARE-01","B-1960s-01","B-WWII-01","C-BULK-01","HOLD-01","SOLD-STAGING-01"];
const PUSH_STATUS_COLORS: Record<string, string> = {
  not_pushed: '#9ca3af',
  draft_saved: '#f59e0b',
  pushing: '#8b5cf6',
  pushed: '#16a34a',
  failed: '#ef4444',
};
const LISTING_STATUS_LABELS: Record<string, string> = {
  none: 'No Listing',
  draft: 'Draft Saved',
  ready: 'Ready to Publish',
  pushed: 'Published',
  failed: 'Publish Failed',
};

// ── Utility ─────────────────────────────────────────────────────────────────────

function fmt(date: string) {
  if (!date) return '—';
  try { return new Date(date).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }); }
  catch { return date; }
}

function StartSection({
  onStartPhoto,
  onSearchKnown,
  creating,
  error,
}: {
  onStartPhoto: () => void;
  onSearchKnown: () => void;
  creating: boolean;
  error: string;
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>ArchiveForge LIFE Intake</h2>
        <p style={{ fontSize: 12, color: '#666', marginTop: 6, maxWidth: 760 }}>
          Best workflow: take/upload the actual magazine cover first. ArchiveForge will identify the issue, then match it to reference covers.
        </p>
      </div>

      {error && (
        <div style={{ padding: 12, background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 10, fontSize: 12, color: '#991b1b' }}>
          <AlertTriangle size={13} style={{ display: 'inline', marginRight: 4 }} />
          {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 14 }}>
        <button
          onClick={onStartPhoto}
          disabled={creating}
          style={{
            textAlign: 'left', background: '#fff', border: '2px solid #06b6d4', borderRadius: 10,
            padding: 18, cursor: creating ? 'wait' : 'pointer', display: 'flex', gap: 12, alignItems: 'flex-start',
          }}
        >
          <Camera size={22} color="#06b6d4" />
          <span>
            <span style={{ display: 'block', fontSize: 16, fontWeight: 800, color: '#1a1a1a' }}>
              {creating ? 'Creating intake…' : 'Start with Photo'}
            </span>
            <span style={{ display: 'block', marginTop: 5, fontSize: 12, color: '#666', lineHeight: 1.4 }}>
              Capture the front cover first, then run AI identification and confirm the reference match.
            </span>
          </span>
        </button>

        <button
          onClick={onSearchKnown}
          style={{
            textAlign: 'left', background: '#fff', border: '1.5px solid #e5e2dc', borderRadius: 10,
            padding: 18, cursor: 'pointer', display: 'flex', gap: 12, alignItems: 'flex-start',
          }}
        >
          <Search size={22} color="#6b7280" />
          <span>
            <span style={{ display: 'block', fontSize: 16, fontWeight: 800, color: '#1a1a1a' }}>
              Search Known Issue
            </span>
            <span style={{ display: 'block', marginTop: 5, fontSize: 12, color: '#666', lineHeight: 1.4 }}>
              Use date, person, event, or cover subject when the issue is already known.
            </span>
          </span>
        </button>
      </div>
    </div>
  );
}

// ── Section 1: Intake / Search ────────────────────────────────────────────────

function IntakeSection({ onIdentified }: { onIdentified: (ref: LifeReferenceIssue) => void }) {
  const [q, setQ] = useState('');
  const [issueDate, setIssueDate] = useState('');
  const [keyword, setKeyword] = useState('');
  const [results, setResults] = useState<LifeReferenceIssue[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [sourceStatus, setSourceStatus] = useState('');
  const [activeSearchTerm, setActiveSearchTerm] = useState('');
  const searchSeq = useRef(0);

  const doSearch = useCallback(async () => {
    const legacyQuery = q.trim();
    const dateQuery = issueDate.trim();
    const keywordQuery = keyword.trim();
    if (!legacyQuery && !dateQuery && !keywordQuery) return;
    const requestId = searchSeq.current + 1;
    searchSeq.current = requestId;
    const submittedTerm = [dateQuery, keywordQuery || legacyQuery].filter(Boolean).join(' · ');
    setResults([]);
    setSourceStatus('');
    setActiveSearchTerm(submittedTerm);
    setSearched(true);
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (dateQuery) params.set('date', dateQuery);
      if (keywordQuery || legacyQuery) params.set('keyword', keywordQuery || legacyQuery);
      const r = await fetch(`${AG_API}/reference/search?${params.toString()}`);
      const d = await r.json();
      if (requestId !== searchSeq.current) return;
      setResults(d.results || []);
      setSourceStatus(d.source_status || '');
      setActiveSearchTerm(d.query?.query_used || submittedTerm);
    } catch {
      if (requestId === searchSeq.current) setResults([]);
    } finally {
      if (requestId === searchSeq.current) setLoading(false);
    }
  }, [q, issueDate, keyword]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Step 1 — Identify the Issue</h2>
        <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
          Search by date, volume/issue number, or cover subject keyword. LIFE magazine ran 1936–1972.
        </p>
      </div>

      <div style={{ background: '#fff', border: '1.5px solid #e5e2dc', borderRadius: 12, padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>Find matching LIFE cover</div>
          <div style={{ fontSize: 11, color: '#888', marginTop: 2 }}>
            Uses Google Books LIFE issue metadata when available. Cover images are reference-only and never replace uploaded item photos.
          </div>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '180px 1fr auto', gap: 8, alignItems: 'end' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 11, color: '#666', fontWeight: 600 }}>
            Date
            <input
              value={issueDate} onChange={e => setIssueDate(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && doSearch()}
              placeholder="1936-11-23"
              type="date"
              style={{ padding: '10px 12px', border: '1.5px solid #e5e2dc', borderRadius: 8, fontSize: 13, outline: 'none' }}
            />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 11, color: '#666', fontWeight: 600 }}>
            Event / Person / Keyword
            <input
              value={keyword} onChange={e => { setKeyword(e.target.value); setQ(e.target.value); }}
              onKeyDown={e => e.key === 'Enter' && doSearch()}
              placeholder="Apollo 11, moon, Kennedy, Pearl Harbor..."
              style={{ padding: '10px 12px', border: '1.5px solid #e5e2dc', borderRadius: 8, fontSize: 13, outline: 'none' }}
            />
          </label>
          <button onClick={doSearch} disabled={loading}
            style={{ padding: '10px 18px', background: loading ? '#9ca3af' : '#06b6d4', color: '#fff', border: 'none', borderRadius: 8, fontWeight: 600, fontSize: 13, cursor: loading ? 'wait' : 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />} Search Covers
          </button>
        </div>
        <input
          value={q} onChange={e => { setQ(e.target.value); setKeyword(e.target.value); }}
          onKeyDown={e => e.key === 'Enter' && doSearch()}
          placeholder="Optional quick search: 1969 moon landing, Nov 1963, vol 11 issue 25..."
          style={{ padding: '9px 12px', border: '1px solid #eee8df', borderRadius: 8, fontSize: 12, outline: 'none' }}
        />
      </div>

      {searched && results.length === 0 && (
        <div style={{ padding: 24, textAlign: 'center', color: '#999', background: '#fff', borderRadius: 10, border: '1px solid #e5e2dc' }}>
          No reference issues matched {activeSearchTerm ? `"${activeSearchTerm}"` : 'this search'}. Try a different date, event, person, or keyword.
        </div>
      )}

      {results.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {activeSearchTerm && (
            <div style={{ padding: '8px 10px', background: '#eef8fb', border: '1px solid #bae6fd', borderRadius: 8, color: '#155e75', fontSize: 11 }}>
              Showing results for: <strong>{activeSearchTerm}</strong>
            </div>
          )}
          {sourceStatus && sourceStatus !== 'google_books_api' && (
            <div style={{ padding: '8px 10px', background: '#fef9ec', border: '1px solid #fde68a', borderRadius: 8, color: '#92400e', fontSize: 11 }}>
              Google Books API status: {sourceStatus}. Showing known Google Books issue pages and local references where available.
            </div>
          )}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
          {results.map(ref => (
            <div key={ref.id} style={{
              background: '#fff', border: `1.5px solid ${ref.match_score && ref.match_score > 0.5 ? '#06b6d4' : '#e5e2dc'}`,
              borderRadius: 12, padding: 12, cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 10,
              transition: 'all 0.15s',
            }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = '#06b6d4')}
              onMouseLeave={e => (e.currentTarget.style.borderColor = ref.match_score && ref.match_score > 0.5 ? '#06b6d4' : '#e5e2dc')}
              onClick={() => onIdentified(ref)}
            >
              {ref.cover_thumbnail_url || ref.reference_cover_url ? (
                <img
                  src={ref.cover_thumbnail_url || ref.reference_cover_url}
                  alt={`LIFE cover ${ref.date}`}
                  style={{ width: '100%', height: 190, objectFit: 'contain', background: '#f9f8f6', border: '1px solid #eee8df', borderRadius: 8 }}
                />
              ) : (
                <div style={{ width: '100%', height: 190, background: '#f5f3ef', border: '1px dashed #d6d3cc', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af', fontSize: 12 }}>
                  no cover image available
                </div>
              )}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <div style={{ fontWeight: 700, fontSize: 13, color: '#1a1a1a' }}>{ref.cover_subject}</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  <span style={{ fontSize: 11, padding: '2px 7px', background: '#f5f3ef', borderRadius: 6, color: '#666' }}>{ref.date || 'date unknown'}</span>
                  <span style={{ fontSize: 11, padding: '2px 7px', background: '#f5f3ef', borderRadius: 6, color: '#666' }}>
                    {ref.volume_label || `Vol ${ref.volume || '—'}, No. ${ref.issue_number || '—'}`}
                  </span>
                  <span style={{ fontSize: 11, padding: '2px 7px', borderRadius: 6, fontWeight: 700,
                    background: (TIER_COLORS[ref.tier_guidance] || '#6b7280') + '20',
                    color: TIER_COLORS[ref.tier_guidance] || '#6b7280' }}>
                    {ref.tier_guidance || 'C'}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: '#666', minHeight: 30 }}>
                  {ref.match_reason || ref.rarity_notes}
                </div>
                <div style={{ fontSize: 10, color: '#888' }}>
                  Source: {ref.source === 'google_books' ? 'Google Books' : 'local reference'} {ref.google_books_volume_id ? `· ${ref.google_books_volume_id}` : ''}
                </div>
                {ref.match_score !== undefined && (
                  <div style={{ fontSize: 11, color: ref.match_score > 0.5 ? '#16a34a' : '#888' }}>
                    Match confidence: {Math.round(ref.match_score * 100)}%
                  </div>
                )}
                <button style={{ marginTop: 2, padding: '8px 12px', background: '#06b6d4', color: '#fff', border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>
                  Select this issue
                </button>
              </div>
            </div>
          ))}
          </div>
        </div>
      )}

      <div style={{ padding: 12, background: '#fef9ec', borderRadius: 10, border: '1px solid #fde68a', fontSize: 12, color: '#92400e' }}>
        <strong>Reference-only covers</strong> — Google Books or local reference covers help identify the issue.
        They are not listing photos. Upload your actual item photos in Step 3 before listing.
      </div>

      <TextIssueSearch onUseMatch={(match) => onIdentified({
        id: `dtm-${match.issue_date}`,
        source: match.source_type,
        google_books_volume_id: '',
        date: match.issue_date,
        volume: null,
        issue_number: null,
        cover_subject: match.description,
        issue_title: 'LIFE',
        volume_label: '',
        reference_cover_url: '',
        rarity_notes: `DTM guide ${match.low || ''}-${match.high || ''}. Reference price guide, not sold comps.`,
        tier_guidance: 'C',
        keywords: match.description,
        match_score: match.match_score,
      })} />
    </div>
  );
}

function TextIssueSearch({ onUseMatch }: { onUseMatch: (match: any) => void }) {
  const [query, setQuery] = useState('');
  const [year, setYear] = useState('');
  const [matches, setMatches] = useState<any[]>([]);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setMessage('');
    try {
      const params = new URLSearchParams({ q: query.trim() });
      if (year.trim()) params.set('year', year.trim());
      const res = await fetch(`${AG_API}/life-issues/search?${params.toString()}`);
      const out = await res.json();
      if (!res.ok) throw new Error(out.detail || `Search failed with ${res.status}`);
      setMatches(out.matches || []);
      setMessage(out.message || '');
    } catch (exc: any) {
      setMessage(exc?.message || 'Text issue search failed.');
      setMatches([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14, display: 'grid', gap: 10 }}>
      <div>
        <div style={{ fontSize: 13, fontWeight: 800, color: '#1a1a1a' }}>Text Search Issue Lookup</div>
        <div style={{ fontSize: 11, color: '#777', marginTop: 2 }}>Search the local LIFE Issue Master by last name, date, keyword, or topic. DTM values are reference-guide values, not sold comps.</div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 110px auto', gap: 8 }}>
        <input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && search()} placeholder="Armstrong, Grace Kelly, Grissom, Batman..."
          style={{ padding: '9px 11px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12 }} />
        <input value={year} onChange={e => setYear(e.target.value)} onKeyDown={e => e.key === 'Enter' && search()} placeholder="Year"
          style={{ padding: '9px 11px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12 }} />
        <button onClick={search} disabled={loading} style={{ padding: '9px 12px', background: '#111827', color: '#fff', border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 800, cursor: loading ? 'wait' : 'pointer' }}>
          {loading ? 'Searching...' : 'Search LIFE Issues'}
        </button>
      </div>
      {message && <div style={{ fontSize: 11, color: '#92400e', background: '#fef9ec', border: '1px solid #fde68a', borderRadius: 8, padding: 8 }}>{message}</div>}
      {matches.length > 0 && (
        <div style={{ display: 'grid', gap: 6 }}>
          {matches.slice(0, 8).map(match => (
            <div key={`${match.issue_date}-${match.description}`} style={{ display: 'grid', gridTemplateColumns: '110px 1fr auto', gap: 8, alignItems: 'center', padding: 9, border: '1px solid #eee8df', borderRadius: 8, fontSize: 12 }}>
              <strong>{match.issue_date}</strong>
              <span>{match.description} <span style={{ color: '#888' }}>guide ${match.low || '—'}-${match.high || '—'}</span></span>
              <button onClick={() => onUseMatch(match)} style={{ padding: '6px 9px', background: '#eef2ff', color: '#3730a3', border: '1px solid #c7d2fe', borderRadius: 7, fontSize: 11, fontWeight: 800, cursor: 'pointer' }}>
                Use Selected Match
              </button>
            </div>
          ))}
        </div>
      )}

    </div>
  );
}

// ── Section 2: Reference Match ────────────────────────────────────────────────

function ReferenceSection({ ref_issue }: { ref_issue: LifeReferenceIssue }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Step 2 — Reference Issue</h2>
        <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
          Canonical reference for this issue. Use this to compare against your actual item.
        </p>
      </div>

      <div style={{ background: '#fff', border: '1.5px solid #e5e2dc', borderRadius: 12, padding: 20, display: 'flex', gap: 20, alignItems: 'flex-start' }}>
        {ref_issue.reference_cover_url ? (
          <img
            src={ref_issue.reference_cover_url}
            alt={`LIFE ${ref_issue.date}`}
            style={{ width: 160, height: 200, objectFit: 'contain', borderRadius: 8, border: '1px solid #e5e2dc', flexShrink: 0, background: '#f9f9f9' }}
            onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
        ) : (
          <div style={{ width: 160, height: 200, background: '#f5f3ef', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#aaa', fontSize: 11, flexShrink: 0 }}>
            No ref. image
          </div>
        )}
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 8 }}>{ref_issue.cover_subject}</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 24px', fontSize: 12 }}>
            {[
	              ["Date", ref_issue.date],
	              ["Volume", ref_issue.volume ? String(ref_issue.volume) : '—'],
	              ["Issue #", ref_issue.issue_number ? String(ref_issue.issue_number) : '—'],
	              ["Source", ref_issue.source === 'google_books' ? 'Google Books' : 'Local reference'],
	              ["Google Books ID", ref_issue.google_books_volume_id || '—'],
	              ["Tier", ref_issue.tier_guidance],
	              ["Match confidence", ref_issue.match_score ? `${Math.round(ref_issue.match_score * 100)}%` : 'N/A'],
	            ].map(([label, value]) => (
              <div key={label}><span style={{ color: '#888' }}>{label}: </span><span style={{ fontWeight: 600 }}>{value}</span></div>
            ))}
          </div>
	          <div style={{ marginTop: 10, fontSize: 12, color: '#666', fontStyle: 'italic' }}>
	            "{ref_issue.rarity_notes}"
	          </div>
	          {ref_issue.match_reason && (
	            <div style={{ marginTop: 8, fontSize: 12, color: '#155e75' }}>
	              Match reason: {ref_issue.match_reason}
	            </div>
	          )}
        </div>
      </div>

      <div style={{ padding: 12, background: '#ecfeff', borderRadius: 10, fontSize: 12, color: '#155e75' }}>
        <strong>Important:</strong> Compare your physical item against this reference. Note any differences in condition, missing pages, or defects. This comparison drives the condition score in Step 5.
      </div>
    </div>
  );
}

// ── Section 3: Photo Capture ───────────────────────────────────────────────────

const PHOTO_ROLES = [
  { key: 'front', label: 'Front Cover', required: true, desc: 'Clear flat scan of front cover' },
  { key: 'spine', label: 'Spine', required: false, desc: 'Spine condition — critical for grading' },
  { key: 'back', label: 'Back Cover', required: false, desc: 'Back cover scan' },
  { key: 'defects', label: 'Defect Photos', required: false, desc: 'Any tears, foxing, missing pages, writing' },
  { key: 'label', label: 'Mailing Label', required: false, desc: 'Address label close-up (if present)' },
];

function IdentifyResultPanel({
  result,
  latestFrontPhotoId,
  onConfirmIssue,
}: {
  result: IdentifyResponse;
  latestFrontPhotoId?: number | null;
  onConfirmIssue?: () => void;
}) {
  const ai = result.ai_result || {};
  const range = ai.recommended_price_range || {};
  const visibleText = Array.isArray(ai.visible_text) ? ai.visible_text : [];
  const needsRealPhoto = result.image && (!result.image.exists || !result.image.readable || (result.image.file_size_bytes || 0) <= 0);
  const staleForLatestPhoto = !!latestFrontPhotoId && !!result.photo_id && result.photo_id !== latestFrontPhotoId;
  const candidates = result.google_books_candidates || ai.google_books_candidates || [];
  const selectedCandidate = result.selected_google_books_candidate || ai.selected_google_books_candidate || null;

  return (
    <div style={{ background: '#fff', border: '1px solid #dbeafe', borderRadius: 10, padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <CheckCircle size={15} color="#2563eb" />
        <div style={{ fontSize: 13, fontWeight: 800, color: '#1e3a8a' }}>AI Identify Result</div>
      </div>
      {needsRealPhoto && (
        <div style={{ padding: 10, background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, fontSize: 12, color: '#991b1b' }}>
          This archive needs a real front-cover photo before AI identification can run.
        </div>
      )}
      {staleForLatestPhoto && (
        <div style={{ padding: 10, background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 8, fontSize: 12, color: '#9a3412' }}>
          This result was generated before the latest front-cover upload. Run AI Identify again.
        </div>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 8, fontSize: 12 }}>
        {[
          ['archive_id', result.archive_id],
          ['analyzed_photo_id', result.photo_id || '—'],
          ['image_path', result.image_path || result.image?.image_path || '—'],
          ['identify_run_id', result.identify_run_id || '—'],
          ['identified_at', result.identified_at || '—'],
          ['image_saved', result.image?.exists ? 'true' : 'false'],
          ['provider', result.provider],
          ['capability', result.capability],
          ['evidence_source', ai.evidence_source],
          ['is_life_magazine', ai.is_life_magazine === undefined ? '—' : String(ai.is_life_magazine)],
          ['confidence', ai.confidence === undefined ? '—' : `${Math.round((ai.confidence || 0) * 100)}%`],
          ['issue_date', ai.issue_date || '—'],
          ['cover_title', ai.cover_title || '—'],
          ['subject_description', ai.subject_description || '—'],
          ['condition_notes', ai.condition_notes || '—'],
          ['tier', ai.tier || '—'],
          ['recommended_price_range', range.low || range.high ? `$${range.low || 0}–$${range.high || 0}` : '—'],
        ].map(([label, value]) => (
          <div key={label}>
            <div style={{ fontSize: 10, color: '#888' }}>{label}</div>
            <div style={{ fontWeight: 600, color: '#1f2937' }}>{value}</div>
          </div>
        ))}
      </div>
      {visibleText.length > 0 && (
        <div style={{ fontSize: 12, color: '#374151' }}>
          <span style={{ color: '#888' }}>visible_text: </span>{visibleText.join(', ')}
        </div>
      )}
      {selectedCandidate && (
        <div style={{ padding: 10, background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: 8, fontSize: 12, color: '#075985' }}>
          <strong>Google Books candidate:</strong> {selectedCandidate.title || 'LIFE'} {selectedCandidate.publishedDate ? `· ${selectedCandidate.publishedDate}` : ''} {selectedCandidate.volume_id ? `· ${selectedCandidate.volume_id}` : ''} {selectedCandidate.match_confidence !== undefined ? `· ${Math.round((selectedCandidate.match_confidence || 0) * 100)}%` : ''}
        </div>
      )}
      {!selectedCandidate && candidates.length > 0 && (
        <div style={{ padding: 10, background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 12, color: '#475569' }}>
          Google Books returned candidate(s), but none were strong enough to auto-select. Confirm manually.
        </div>
      )}
      <div style={{ fontSize: 12, color: '#374151' }}>
        <span style={{ color: '#888' }}>reasoning_summary: </span>{ai.reasoning_summary || '—'}
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {onConfirmIssue && (
          <button onClick={onConfirmIssue}
            style={{ padding: '8px 12px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 800, cursor: 'pointer' }}>
            Confirm This Issue
          </button>
        )}
      </div>
    </div>
  );
}

function IssueInfoPanel({
  issueInfo,
  latestFrontPhotoId,
  resolving,
  manualVolumeId,
  onManualVolumeId,
  onResolve,
  onRerun,
  onConfirmIssue,
  onManualCorrection,
  onLookupManualVolume,
}: {
  issueInfo: IssueInfoRun | null;
  latestFrontPhotoId?: number | null;
  resolving: boolean;
  manualVolumeId: string;
  onManualVolumeId: (value: string) => void;
  onResolve: () => void;
  onRerun: () => void;
  onConfirmIssue: () => void;
  onManualCorrection: () => void;
  onLookupManualVolume: () => void;
}) {
  const staleForLatestPhoto = !!issueInfo?.front_photo_id && !!latestFrontPhotoId && issueInfo.front_photo_id !== latestFrontPhotoId;
  const visibleText = Array.isArray(issueInfo?.visible_text) ? issueInfo.visible_text : [];
  const candidates = issueInfo?.google_books_candidates || [];
  const selected = issueInfo?.selected_google_books_candidate || candidates.find(c => c.volume_id === issueInfo?.selected_google_books_volume_id) || null;
  const status = issueInfo?.status || 'not_run';
  const statusLabel = resolving || status === 'pending' || status === 'running' ? 'Resolving issue information...' : status;

  return (
    <div style={{ background: '#fff', border: '1px solid #bae6fd', borderRadius: 10, padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {resolving || status === 'pending' || status === 'running' ? <Loader2 size={15} className="animate-spin" color="#0369a1" /> : <Layers size={15} color="#0369a1" />}
        <div style={{ fontSize: 13, fontWeight: 800, color: '#075985' }}>Issue Info Resolver</div>
      </div>
      <div style={{ fontSize: 12, color: '#155e75' }}>
        {statusLabel}
      </div>
      {(staleForLatestPhoto || issueInfo?.stale_warning) && (
        <div style={{ padding: 10, background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 8, fontSize: 12, color: '#9a3412' }}>
          This issue info was generated before the latest front-cover upload. Re-run resolver.
        </div>
      )}
      {issueInfo?.status === 'failed' && (
        <div style={{ padding: 10, background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, fontSize: 12, color: '#991b1b' }}>
          {issueInfo.error_message || 'Issue resolver failed.'}
        </div>
      )}
      {issueInfo && issueInfo.status !== 'not_run' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 8, fontSize: 12 }}>
          {[
            ['status', issueInfo.status],
            ['analyzed_photo_id', issueInfo.front_photo_id || '—'],
            ['image_path', issueInfo.image_path || '—'],
            ['file_size_bytes', issueInfo.file_size_bytes || 0],
            ['mime_type', issueInfo.mime_type || '—'],
            ['is_life_magazine', issueInfo.is_life_magazine === undefined ? '—' : String(issueInfo.is_life_magazine)],
            ['confidence', issueInfo.confidence === undefined ? '—' : `${Math.round((issueInfo.confidence || 0) * 100)}%`],
            ['issue_date', issueInfo.issue_date || '—'],
            ['cover_title', issueInfo.cover_title || '—'],
            ['detected_subject', issueInfo.detected_subject || '—'],
            ['detected_quote', issueInfo.detected_quote || '—'],
            ['detected_price', issueInfo.detected_price || '—'],
            ['evidence_source', issueInfo.evidence_source || '—'],
            ['evidence_grade', issueInfo.evidence_grade || '—'],
            ['needs_user_confirmation', issueInfo.needs_user_confirmation === undefined ? '—' : String(issueInfo.needs_user_confirmation)],
            ['ad_opportunity_ready', issueInfo.ad_opportunity_ready === undefined ? '—' : String(issueInfo.ad_opportunity_ready)],
          ].map(([label, value]) => (
            <div key={label}>
              <div style={{ fontSize: 10, color: '#888' }}>{label}</div>
              <div style={{ fontWeight: 600, color: '#1f2937', overflowWrap: 'anywhere' }}>{value}</div>
            </div>
          ))}
        </div>
      )}
      {visibleText.length > 0 && (
        <div style={{ fontSize: 12, color: '#374151' }}>
          <span style={{ color: '#888' }}>visible text: </span>{visibleText.join(', ')}
        </div>
      )}
      {selected && (
        <div style={{ padding: 10, background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: 8, fontSize: 12, color: '#075985' }}>
          <strong>Google Books candidate:</strong> {selected.title || 'LIFE'} {selected.publishedDate ? `· ${selected.publishedDate}` : ''} {selected.volume_id ? `· ${selected.volume_id}` : ''} {selected.match_confidence !== undefined ? `· ${Math.round((selected.match_confidence || 0) * 100)}%` : ''}
        </div>
      )}
      {(issueInfo?.reference_sources || []).length > 0 && (
        <div style={{ fontSize: 12, color: '#374151' }}>
          <span style={{ color: '#888' }}>sources: </span>{(issueInfo?.reference_sources || []).map(src => src.source || src.capability || 'source').join(', ')}
        </div>
      )}
      {(issueInfo?.conflicts || []).length > 0 && (
        <div style={{ padding: 10, background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 8, fontSize: 12, color: '#92400e' }}>
          Conflicts: {(issueInfo?.conflicts || []).map(c => `${c.volume_id || 'candidate'} ${c.reason || ''}`).join('; ')}
        </div>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(180px, 1fr) auto', gap: 8, alignItems: 'end' }}>
        <label style={{ display: 'flex', flexDirection: 'column', gap: 5, fontSize: 11, color: '#666', fontWeight: 700 }}>
          Manual Google Books Volume ID
          <input value={manualVolumeId} onChange={e => onManualVolumeId(e.target.value)} placeholder="eFYEAAAAMBAJ"
            style={{ padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12 }} />
        </label>
        <button onClick={onLookupManualVolume} disabled={resolving || !manualVolumeId.trim()}
          style={{ padding: '9px 12px', borderRadius: 8, border: '1px solid #0284c7', background: '#f0f9ff', color: '#075985', fontSize: 12, fontWeight: 800, cursor: resolving || !manualVolumeId.trim() ? 'not-allowed' : 'pointer' }}>
          Manual Google Books Volume ID
        </button>
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button onClick={onResolve} disabled={resolving}
          style={{ padding: '8px 12px', background: '#0369a1', color: '#fff', border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 800, cursor: resolving ? 'not-allowed' : 'pointer' }}>
          Resolve Issue Info
        </button>
        <button onClick={onRerun} disabled={resolving}
          style={{ padding: '8px 12px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 800, cursor: resolving ? 'not-allowed' : 'pointer' }}>
          Re-run Resolver on Latest Front Cover
        </button>
        <button onClick={onConfirmIssue}
          style={{ padding: '8px 12px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 800, cursor: 'pointer' }}>
          Confirm This Issue
        </button>
        <button onClick={onManualCorrection}
          style={{ padding: '8px 12px', background: '#fff', color: '#374151', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 12, fontWeight: 800, cursor: 'pointer' }}>
          Manual Correction
        </button>
      </div>
    </div>
  );
}

function PhotoSection({
  archiveId,
  refIssue,
  identifyResult,
  onIdentifyResult,
  onConfirmIssue,
}: {
  archiveId: number | null;
  refIssue: LifeReferenceIssue | null;
  identifyResult: IdentifyResponse | null;
  onIdentifyResult: (result: IdentifyResponse | null) => void;
  onConfirmIssue: () => void;
}) {
  const [photos, setPhotos] = useState<PhotoRecord[]>([]);
  const [uploadingRole, setUploadingRole] = useState<string | null>(null);
  const [photoError, setPhotoError] = useState<string | null>(null);
  const [identifying, setIdentifying] = useState(false);
  const [identifyError, setIdentifyError] = useState('');
  const [issueInfo, setIssueInfo] = useState<IssueInfoRun | null>(null);
  const [issueInfoError, setIssueInfoError] = useState('');
  const [resolvingIssueInfo, setResolvingIssueInfo] = useState(false);
  const [manualIssueVolumeId, setManualIssueVolumeId] = useState('');

  const loadPhotos = useCallback(async () => {
    if (!archiveId) return;
    try {
      const r = await fetch(`${AG_API}/uploads/${archiveId}`);
      const d = await r.json();
      setPhotos(d.photos || []);
    } catch { /* silent */ }
  }, [archiveId]);

  const loadIssueInfo = useCallback(async (): Promise<IssueInfoRun | null> => {
    if (!archiveId) return null;
    try {
      const r = await fetch(`${AG_API}/${archiveId}/issue-info`);
      const d = await r.json().catch(() => ({}));
      if (!r.ok) {
        setIssueInfo(null);
        return null;
      }
      setIssueInfo(d);
      return d;
    } catch {
      return null;
    }
  }, [archiveId]);

  const pollIssueInfo = useCallback(async () => {
    for (let attempt = 0; attempt < 8; attempt++) {
      const current = await loadIssueInfo();
      if (current && !['pending', 'running'].includes(current.status)) break;
      await new Promise(resolve => setTimeout(resolve, 1500));
    }
  }, [loadIssueInfo]);

  useEffect(() => { loadPhotos(); loadIssueInfo(); }, [loadPhotos, loadIssueInfo]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>, role: string) => {
    const files = e.target.files;
    if (!files || files.length === 0) {
      setPhotoError('No file selected.');
      return;
    }
    if (!archiveId) {
      setPhotoError('Archive record is not ready yet.');
      return;
    }
    setUploadingRole(role);
    setPhotoError(null);
	    for (let i = 0; i < files.length; i++) {
      const selectedFile = files[i];
      if (selectedFile.size <= 0) {
        setPhotoError('Selected image is empty. Choose a non-empty JPEG, PNG, GIF, or WebP file.');
        continue;
      }
      if (selectedFile.type && !SUPPORTED_UPLOAD_MIME_TYPES.has(selectedFile.type)) {
        setPhotoError('Unsupported image type. Upload a JPEG, PNG, GIF, or WebP file.');
        continue;
      }
	      const formData = new FormData();
	      formData.append('file', selectedFile);
	      formData.append('role', role);
	      try {
	        const response = await fetch(`${AG_API}/uploads/${archiveId}`, { method: 'POST', body: formData });
          const data = await response.json().catch(() => ({}));
	        if (!response.ok) {
	          let message = `Upload failed with ${response.status}`;
	          if (data?.detail) message = data.detail;
	          throw new Error(message);
	        }
          if (data?.issue_info && role === 'front') {
            setIssueInfo({
              archive_id: archiveId,
              status: data.issue_info.status || 'pending',
              front_photo_id: data.issue_info.front_photo_id,
              run_id: data.issue_info.run_id,
            });
          }
	      } catch (exc: any) {
	        setPhotoError(exc?.message || 'Photo upload failed.');
	      }
		    }
		    await loadPhotos();
		    if (role === 'front') {
          onIdentifyResult(null);
          await pollIssueInfo();
        }
		    setUploadingRole(null);
		    if (e.target) e.target.value = '';
		  };

  const runIdentify = async () => {
    if (!archiveId) return;
    setIdentifying(true);
    setIdentifyError('');
    try {
      const res = await fetch(`${AG_API}/identify?archive_id=${archiveId}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Identify failed with ${res.status}`);
      onIdentifyResult(data);
      await loadIssueInfo();
    } catch (exc: any) {
      setIdentifyError(exc?.message || 'AI identification failed.');
    } finally {
      setIdentifying(false);
    }
  };

  const resolveIssueInfo = async (forceRefresh = false) => {
    if (!archiveId) return;
    setResolvingIssueInfo(true);
    setIssueInfoError('');
    try {
      const suffix = forceRefresh ? '?force_refresh=true' : '';
      const res = await fetch(`${AG_API}/${archiveId}/resolve-issue-info${suffix}`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Issue resolver failed with ${res.status}`);
      setIssueInfo(data);
    } catch (exc: any) {
      setIssueInfoError(exc?.message || 'Issue resolver failed.');
    } finally {
      setResolvingIssueInfo(false);
    }
  };

  const lookupManualIssueVolume = async () => {
    if (!archiveId || !manualIssueVolumeId.trim()) return;
    setResolvingIssueInfo(true);
    setIssueInfoError('');
    try {
      const params = new URLSearchParams({ volume_id: manualIssueVolumeId.trim() });
      const res = await fetch(`${AG_API}/${archiveId}/google-books/lookup?${params.toString()}`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Google Books lookup failed with ${res.status}`);
      await resolveIssueInfo(true);
    } catch (exc: any) {
      setIssueInfoError(exc?.message || 'Manual Google Books lookup failed.');
    } finally {
      setResolvingIssueInfo(false);
    }
  };

  const handleDelete = async (photoId: number) => {
    try {
      await fetch(`${AG_API}/photo/${photoId}`, { method: 'DELETE' });
      setPhotos(prev => prev.filter(p => p.id !== photoId));
    } catch { /* silent */ }
  };

	  const byRole = (role: string) => photos.filter(p => p.role === role);
	  const photoUrl = (photo: PhotoRecord) => `${AG_API}/photo/${photo.id}`;
	  const totalCount = photos.length;
	  const hasFrontPhoto = byRole('front').length > 0;
	  const latestFrontPhoto = [...byRole('front')].sort((a, b) => {
	    const at = new Date(a.created_at || '').getTime() || 0;
	    const bt = new Date(b.created_at || '').getTime() || 0;
	    if (bt !== at) return bt - at;
	    return (b.id || 0) - (a.id || 0);
	  })[0];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Step 3 — Actual Listing Photos</h2>
        <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
          Upload photos of <strong>your actual item</strong>. Photos are saved to the server — they persist across page refreshes.
        </p>
      </div>

      {!archiveId && (
        <div style={{ padding: 12, background: '#fef9ec', border: '1px solid #fde68a', borderRadius: 10, fontSize: 12, color: '#92400e' }}>
          <AlertTriangle size={13} style={{ display: 'inline', marginRight: 4 }} />
          Archive record not yet created. Complete Steps 1–2 and proceed from the Reference step to enable photo uploads.
        </div>
      )}
      {photoError && (
        <div style={{ padding: 12, background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 10, fontSize: 12, color: '#991b1b' }}>
          <AlertTriangle size={13} style={{ display: 'inline', marginRight: 4 }} />
          {photoError}
        </div>
      )}
      {identifyError && (
        <div style={{ padding: 12, background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 10, fontSize: 12, color: '#991b1b' }}>
          <AlertTriangle size={13} style={{ display: 'inline', marginRight: 4 }} />
          {identifyError}
        </div>
      )}
      {issueInfoError && (
        <div style={{ padding: 12, background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 10, fontSize: 12, color: '#991b1b' }}>
          <AlertTriangle size={13} style={{ display: 'inline', marginRight: 4 }} />
          {issueInfoError}
        </div>
      )}

      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 14, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 260px' }}>
          <div style={{ fontSize: 13, fontWeight: 800, color: '#1a1a1a' }}>AI cover identification</div>
          <div style={{ fontSize: 12, color: '#666', marginTop: 3 }}>
            Upload a real front-cover photo first. ArchiveForge sends the actual image to MiniMax Token Plan image understanding.
          </div>
        </div>
        <button
          onClick={runIdentify}
          disabled={!archiveId || !hasFrontPhoto || identifying}
          style={{
            padding: '9px 14px', borderRadius: 8, border: 'none', fontSize: 12, fontWeight: 800,
            background: !archiveId || !hasFrontPhoto ? '#e5e7eb' : '#2563eb',
            color: '#fff', cursor: !archiveId || !hasFrontPhoto || identifying ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', gap: 6,
          }}
        >
          {identifying ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
          {identifyResult ? 'Re-run AI Identify on latest front cover' : 'Run AI Identify'}
        </button>
        {!hasFrontPhoto && (
          <div style={{ width: '100%', fontSize: 11, color: '#92400e' }}>
            This archive needs a real front-cover photo before AI identification can run.
          </div>
        )}
      </div>

      {(hasFrontPhoto || issueInfo) && (
        <IssueInfoPanel
          issueInfo={issueInfo}
          latestFrontPhotoId={latestFrontPhoto?.id || null}
          resolving={resolvingIssueInfo}
          manualVolumeId={manualIssueVolumeId}
          onManualVolumeId={setManualIssueVolumeId}
          onResolve={() => resolveIssueInfo(false)}
          onRerun={() => resolveIssueInfo(true)}
          onConfirmIssue={onConfirmIssue}
          onManualCorrection={onConfirmIssue}
          onLookupManualVolume={lookupManualIssueVolume}
        />
      )}

      {identifyResult && (
        <IdentifyResultPanel
          result={identifyResult}
          latestFrontPhotoId={latestFrontPhoto?.id || null}
          onConfirmIssue={onConfirmIssue}
        />
      )}

      {/* Side-by-side: Reference cover | Upload slots */}
      <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', gap: 20, alignItems: 'start' }}>
        {/* Left: reference cover */}
        <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#888', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 }}>Reference Cover</div>
          {refIssue?.reference_cover_url ? (
            <img src={refIssue.reference_cover_url} alt="Reference cover"
              style={{ width: '100%', aspectRatio: '4/5', objectFit: 'contain', borderRadius: 8, border: '1px solid #e5e2dc', background: '#f9f9f9', display: 'block' }}
              onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          ) : (
            <div style={{ width: '100%', aspectRatio: '4/5', background: '#f5f3ef', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#aaa', fontSize: 11 }}>
              No reference image
            </div>
          )}
          {refIssue && (
            <div style={{ marginTop: 8, fontSize: 10, color: '#888', lineHeight: 1.4 }}>
              <div style={{ fontWeight: 600 }}>{refIssue.date}</div>
              <div>{refIssue.cover_subject}</div>
            </div>
          )}
          <div style={{ marginTop: 8, padding: '6px 8px', background: '#ecfeff', borderRadius: 6, fontSize: 10, color: '#155e75' }}>
            Compare your item against this reference when photographing.
          </div>
        </div>

        {/* Right: upload slots grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
          {PHOTO_ROLES.map(role => {
            const rolePhotos = byRole(role.key);
            const isUploading = uploadingRole === role.key;
            return (
              <div key={role.key} style={{ background: '#fff', border: `1.5px solid ${rolePhotos.length > 0 ? '#10b981' : '#e5e2dc'}`, borderRadius: 10, padding: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <span style={{ fontSize: 12, fontWeight: 600 }}>{role.label}</span>
                    {role.required && <span style={{ fontSize: 9, background: '#fee2e2', color: '#dc2626', padding: '1px 5px', borderRadius: 3 }}>REQ</span>}
                    {rolePhotos.length > 0 && <CheckCircle size={12} color="#10b981" />}
                  </div>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <label style={{
                      padding: '3px 8px', background: archiveId ? '#06b6d4' : '#d1d5db', color: '#fff',
                      borderRadius: 5, fontSize: 10, fontWeight: 600,
                      cursor: archiveId ? 'pointer' : 'not-allowed', display: 'flex', alignItems: 'center', gap: 4,
                    }}>
                      {isUploading ? <Loader2 size={10} className="animate-spin" /> : <Upload size={10} />} Upload from file
                      <input type="file" accept="image/*" multiple style={{ display: 'none' }} disabled={!archiveId}
                        onChange={e => handleUpload(e, role.key)} />
                    </label>
                    <label style={{
                      padding: '3px 8px', background: archiveId ? '#0f766e' : '#d1d5db', color: '#fff',
                      borderRadius: 5, fontSize: 10, fontWeight: 600,
                      cursor: archiveId ? 'pointer' : 'not-allowed', display: 'flex', alignItems: 'center', gap: 4,
                    }}>
                      <Camera size={10} /> Take photo
                      <input type="file" accept="image/*" capture="environment" style={{ display: 'none' }} disabled={!archiveId}
                        onChange={e => handleUpload(e, role.key)} />
                    </label>
                  </div>
                </div>
                <div style={{ fontSize: 10, color: '#888', marginBottom: 6 }}>{role.desc}</div>
                {rolePhotos.length === 0 ? (
                  <div style={{ height: 52, background: '#f9f8f6', borderRadius: 7, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ccc', fontSize: 10, border: '1.5px dashed #e5e2dc' }}>
                    {isUploading ? 'Uploading…' : 'No photo yet'}
                  </div>
                ) : (
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {rolePhotos.map(photo => (
                      <div key={photo.id} style={{ position: 'relative' }}>
                        <img src={photoUrl(photo)} alt={role.label}
                          style={{ width: 52, height: 52, objectFit: 'cover', borderRadius: 6, border: '1px solid #e5e2dc' }} />
                        <button onClick={() => handleDelete(photo.id)}
                          style={{ position: 'absolute', top: -5, right: -5, width: 16, height: 16, background: '#ef4444', color: '#fff', border: 'none', borderRadius: '50%', cursor: 'pointer', fontSize: 9, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          ×
                        </button>
                        <div style={{ position: 'absolute', bottom: 2, left: 2, background: 'rgba(16,185,129,0.85)', borderRadius: 3, padding: '1px 3px', fontSize: 7, color: '#fff', fontWeight: 700 }}>
                          SAVED
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {totalCount > 0 && (
        <div style={{ padding: 10, background: '#f0fdf4', borderRadius: 8, fontSize: 12, color: '#166534', display: 'flex', alignItems: 'center', gap: 6 }}>
          <CheckCircle size={13} />
          {totalCount} photo(s) saved to server — will persist across page refreshes.
          <button onClick={loadPhotos} style={{ marginLeft: 'auto', padding: '2px 8px', background: 'transparent', border: '1px solid #16a34a', borderRadius: 5, fontSize: 11, cursor: 'pointer', color: '#16a34a' }}>
            Refresh
          </button>
        </div>
      )}

    </div>
  );
}

function ConfirmMatchSection({
  archiveId,
  refIssue,
  identifyResult,
  confirmation,
  onConfirmed,
  onSearchAgain,
  onManual,
}: {
  archiveId: number | null;
  refIssue: LifeReferenceIssue | null;
  identifyResult: IdentifyResponse | null;
  confirmation: MatchConfirmation | null;
  onConfirmed: (confirmation: MatchConfirmation) => void;
  onSearchAgain: () => void;
  onManual: () => void;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [uploadedFrontPhoto, setUploadedFrontPhoto] = useState<PhotoRecord | null>(null);
  const ai = identifyResult?.ai_result;

  // Fetch latest front-cover photo for this archive
  useEffect(() => {
    if (!archiveId) { setUploadedFrontPhoto(null); return; }
    let cancelled = false;
    fetch(`${AG_API}/${archiveId}/photos`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (cancelled || !data?.photos) return;
        const fronts: PhotoRecord[] = (data.photos.front || []).map((p: PhotoRecord) => ({
          ...p,
          id: p.id || p.photo_id,
        }));
        if (fronts.length === 0) return;
        // Latest front photo by created_at, then by id descending
        const latest = [...fronts].sort((a, b) => {
          const at = new Date(a.created_at || '').getTime() || 0;
          const bt = new Date(b.created_at || '').getTime() || 0;
          if (bt !== at) return bt - at;
          return (b.id || 0) - (a.id || 0);
        })[0];
        if (!cancelled) setUploadedFrontPhoto(latest);
      })
      .catch(() => { /* non-critical */ });
    return () => { cancelled = true; };
  }, [archiveId]);

  // Fetch dealer reference from issue-info API
  const [dealerReference, setDealerReference] = useState<Record<string, any> | null>(null);
  useEffect(() => {
    if (!archiveId) { setDealerReference(null); return; }
    let cancelled = false;
    fetch(`${AG_API}/${archiveId}/issue-info`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (cancelled) return;
        setDealerReference(data?.dealer_reference && typeof data.dealer_reference === 'object' && Object.keys(data.dealer_reference).length > 0 ? data.dealer_reference : null);
      })
      .catch(() => { /* non-critical */ });
    return () => { cancelled = true; };
  }, [archiveId]);

  // Build reference cover: refIssue → Google Books candidate → dealer reference (fallback)
  const gbCandidate = identifyResult?.selected_google_books_candidate || ai?.selected_google_books_candidate || null;
  const referenceCover = refIssue?.reference_cover_url
    ? { label: 'Reference image — not item photo', source: 'reference_search', volume_id: refIssue.google_books_volume_id || refIssue.id, issue_date: refIssue.date, cover_title: refIssue.cover_subject, cover_image_url: refIssue.reference_cover_url, match_confidence: refIssue.match_score || 0 }
    : gbCandidate?.cover_image_url
      ? { label: 'Reference image — not item photo', source: 'google_books', volume_id: gbCandidate.volume_id || '', issue_date: gbCandidate.publishedDate || '', cover_title: gbCandidate.title || '', cover_image_url: gbCandidate.cover_image_url, match_confidence: gbCandidate.match_confidence || 0 }
      : dealerReference?.source_url
        ? {
            label: dealerReference.asking_price
              ? `Dealer catalog — $${dealerReference.asking_price} asking price (not sold comp evidence)`
              : 'Dealer catalog reference image — not your item photo',
            source: 'dealer_reference',
            volume_id: '',
            issue_date: dealerReference.issue_date || '',
            cover_title: dealerReference.title || '',
            cover_image_url: '',
            source_url: dealerReference.source_url || '',
            asking_price: dealerReference.asking_price || null,
            match_confidence: dealerReference.match_confidence || 0,
          }
        : null;

  // Build uploaded cover from latest front photo
  const uploadedCover = uploadedFrontPhoto ? {
    label: 'Your uploaded magazine',
    source: 'uploaded_front_cover',
    photo_id: uploadedFrontPhoto.id || uploadedFrontPhoto.photo_id,
    photo_url: uploadedFrontPhoto.photo_url || `${AG_API}/photo/${uploadedFrontPhoto.id || uploadedFrontPhoto.photo_id}`,
    thumbnail_url: uploadedFrontPhoto.thumbnail_url || `${AG_API}/${archiveId}/photos/${uploadedFrontPhoto.id || uploadedFrontPhoto.photo_id}/thumbnail`,
    file_size_bytes: uploadedFrontPhoto.file_size_bytes || uploadedFrontPhoto.file_size || 0,
    mime_type: uploadedFrontPhoto.mime_type || '',
  } : null;

  const candidate = refIssue ? {
    source: refIssue.source || 'reference_search',
    reference_id: refIssue.id,
    reference_url: refIssue.reference_cover_url,
    issue_date: refIssue.date,
    cover_title: refIssue.cover_subject,
    confidence: refIssue.match_score || 0,
  } : ai ? {
    source: ai.evidence_source || 'ai_identify',
    reference_id: archiveId ? `ai-${archiveId}` : '',
    reference_url: '',
    issue_date: ai.issue_date || null,
    cover_title: ai.cover_title || ai.subject_description || '',
    confidence: ai.confidence || 0,
  } : null;

  const confirm = async (mode: 'confirmed' | 'manual') => {
    if (!archiveId) return;
    const payload = mode === 'manual' ? {
      reference_source: 'manual',
      reference_id: '',
      reference_url: '',
      confirmed_issue_date: '',
      cover_title: 'Manual entry',
      confidence: 0,
      source: 'manual',
      confirmed_by_user: true,
    } : {
      reference_source: candidate?.source || '',
      reference_id: candidate?.reference_id || '',
      reference_url: candidate?.reference_url || '',
      confirmed_issue_date: candidate?.issue_date || '',
      cover_title: candidate?.cover_title || '',
      confidence: candidate?.confidence || 0,
      source: candidate?.source || '',
      confirmed_by_user: true,
    };
    setSaving(true);
    setError('');
    try {
      const res = await fetch(`${AG_API}/${archiveId}/confirm-reference`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Confirm failed with ${res.status}`);
      onConfirmed({
        status: mode,
        source: payload.reference_source,
        reference_id: payload.reference_id,
        reference_url: payload.reference_url,
        issue_date: payload.confirmed_issue_date,
        cover_title: payload.cover_title,
        confidence: payload.confidence,
      });
    } catch (exc: any) {
      setError(exc?.message || 'Could not confirm reference match.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Confirm Match</h2>
        <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
          Confirm the AI/reference match before entering final details.
        </p>
      </div>

      {error && (
        <div style={{ padding: 12, background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 10, fontSize: 12, color: '#991b1b' }}>
          <AlertTriangle size={13} style={{ display: 'inline', marginRight: 4 }} />
          {error}
        </div>
      )}

      {candidate ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Side-by-side reference vs uploaded cover */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {/* Reference Cover */}
            <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5 }}>Reference Cover</span>
                {referenceCover?.source === 'google_books' && (
                  <span style={{ fontSize: 10, padding: '1px 6px', background: '#ecfeff', color: '#155e75', borderRadius: 4, fontWeight: 600 }}>Google Books</span>
                )}
                {referenceCover?.source === 'reference_search' && (
                  <span style={{ fontSize: 10, padding: '1px 6px', background: '#f0fdf4', color: '#166534', borderRadius: 4, fontWeight: 600 }}>Reference</span>
                )}
                {referenceCover?.source === 'dealer_reference' && (
                  <span style={{ fontSize: 10, padding: '1px 6px', background: '#fef3c7', color: '#92400e', borderRadius: 4, fontWeight: 600 }}>Dealer Catalog</span>
                )}
              </div>
              <div style={{ background: '#f9f8f6', borderRadius: 8, border: '1px solid #e5e2dc', minHeight: 180, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
                {referenceCover?.cover_image_url ? (
                  <img
                    src={referenceCover.cover_image_url}
                    alt="Reference cover from Google Books or reference database"
                    style={{ maxWidth: '100%', maxHeight: 180, objectFit: 'contain', borderRadius: 8 }}
                    onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                ) : (
                  <span style={{ fontSize: 11, color: '#999', textAlign: 'center', padding: 12 }}>No reference image</span>
                )}
              </div>
              {referenceCover && (
                <div style={{ fontSize: 10, color: '#888', lineHeight: 1.5 }}>
                  {referenceCover.source === 'dealer_reference' && referenceCover.asking_price && (
                    <div><span style={{ color: '#92400e' }}>Asking price: </span><span style={{ fontWeight: 700, color: '#92400e' }}>${referenceCover.asking_price}</span></div>
                  )}
                  {referenceCover.issue_date && <div><span style={{ color: '#6b7280' }}>Issue date: </span>{referenceCover.issue_date}</div>}
                  {referenceCover.cover_title && <div><span style={{ color: '#6b7280' }}>Title: </span>{referenceCover.cover_title}</div>}
                  {referenceCover.source_url && (
                    <div><span style={{ color: '#6b7280' }}>Source: </span><a href={referenceCover.source_url} target="_blank" rel="noopener noreferrer" style={{ color: '#06b6d4' }}>OriginalLifeMagazines.com</a></div>
                  )}
                  {referenceCover.source !== 'dealer_reference' && referenceCover.volume_id && <div><span style={{ color: '#6b7280' }}>Volume ID: </span><span style={{ fontFamily: 'monospace' }}>{referenceCover.volume_id}</span></div>}
                  {referenceCover.source !== 'dealer_reference' && referenceCover.match_confidence !== undefined && referenceCover.match_confidence > 0 && (
                    <div><span style={{ color: '#6b7280' }}>Confidence: </span>{Math.round(referenceCover.match_confidence * 100)}%</div>
                  )}
                </div>
              )}
              {referenceCover?.source === 'dealer_reference' ? (
                <div style={{ padding: '5px 8px', background: '#fef3c7', border: '1px solid #fcd34d', borderRadius: 6, fontSize: 10, color: '#92400e', lineHeight: 1.4 }}>
                  Dealer asking price — not sold comp evidence
                </div>
              ) : (
                <div style={{ padding: '5px 8px', background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 6, fontSize: 10, color: '#9a3412', lineHeight: 1.4 }}>
                  Reference image — not your item photo
                </div>
              )}
            </div>

            {/* Uploaded Cover */}
            <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5 }}>Your Uploaded Cover</span>
                {uploadedCover && (
                  <span style={{ fontSize: 10, padding: '1px 6px', background: '#f0fdf4', color: '#166534', borderRadius: 4, fontWeight: 600 }}>Item photo</span>
                )}
              </div>
              <div style={{ background: '#f9f8f6', borderRadius: 8, border: '1px solid #e5e2dc', minHeight: 180, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
                {uploadedCover?.thumbnail_url ? (
                  <img
                    src={uploadedCover.thumbnail_url}
                    alt="Your uploaded magazine front cover"
                    style={{ maxWidth: '100%', maxHeight: 180, objectFit: 'contain', borderRadius: 8 }}
                    onError={e => { (e.target as HTMLImageElement).src = uploadedCover.photo_url || ''; }}
                  />
                ) : uploadedCover?.photo_url ? (
                  <img
                    src={uploadedCover.photo_url}
                    alt="Your uploaded magazine front cover"
                    style={{ maxWidth: '100%', maxHeight: 180, objectFit: 'contain', borderRadius: 8 }}
                    onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                ) : (
                  <span style={{ fontSize: 11, color: '#999', textAlign: 'center', padding: 12 }}>No uploaded cover photo</span>
                )}
              </div>
              {uploadedCover && (
                <div style={{ fontSize: 10, color: '#888', lineHeight: 1.5 }}>
                  <div><span style={{ color: '#6b7280' }}>photo_id: </span>{uploadedCover.photo_id}</div>
                  <div><span style={{ color: '#6b7280' }}>file size: </span>{(uploadedCover.file_size_bytes / 1024).toFixed(1)} KB</div>
                  {uploadedCover.mime_type && <div><span style={{ color: '#6b7280' }}>type: </span>{uploadedCover.mime_type}</div>}
                  <div style={{ color: '#16a34a', fontWeight: 600 }}>Saved to server</div>
                </div>
              )}
              {!uploadedCover && (
                <div style={{ padding: '5px 8px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 6, fontSize: 10, color: '#991b1b' }}>
                  No uploaded cover photo found
                </div>
              )}
            </div>
          </div>

          {/* Candidate metadata row */}
          <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ fontSize: 15, fontWeight: 800, color: '#1a1a1a' }}>{candidate.cover_title || 'Unconfirmed LIFE issue'}</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
              <div><span style={{ color: '#888' }}>Issue date: </span>{candidate.issue_date || '—'}</div>
              <div><span style={{ color: '#888' }}>Source: </span>{candidate.source || '—'}</div>
              <div><span style={{ color: '#888' }}>Confidence: </span>{Math.round((candidate.confidence || 0) * 100)}%</div>
              <div><span style={{ color: '#888' }}>Reference ID: </span>{candidate.reference_id || '—'}</div>
            </div>
            {identifyResult && <IdentifyResultPanel result={identifyResult} />}
          </div>
        </div>
      ) : (
        <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 16, fontSize: 12, color: '#666' }}>
          No AI/reference candidate is selected yet. Search a known issue or enter details manually.
        </div>
      )}

      {confirmation && (
        <div style={{ padding: 10, background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 8, fontSize: 12, color: '#166534' }}>
          Match state: {confirmation.status} via {confirmation.source || 'manual'}
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button onClick={() => confirm('confirmed')} disabled={!archiveId || !candidate || saving}
          style={{ padding: '9px 14px', background: !candidate ? '#e5e7eb' : '#16a34a', color: '#fff', border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 800, cursor: !candidate || saving ? 'not-allowed' : 'pointer' }}>
          {saving ? 'Saving…' : 'Confirm this match'}
        </button>
        <button onClick={onSearchAgain}
          style={{ padding: '9px 14px', background: '#fff', color: '#155e75', border: '1px solid #06b6d4', borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>
          Wrong match, search again
        </button>
        <button onClick={() => { onManual(); confirm('manual'); }}
          style={{ padding: '9px 14px', background: '#fff', color: '#6b7280', border: '1px solid #d1d5db', borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>
          No match found, enter manually
        </button>
      </div>
    </div>
  );
}

function AdOpportunitySection({ archiveId }: { archiveId: number | null }) {
  const [issueInfo, setIssueInfo] = useState<IssueInfoRun | null>(null);
  const [metadata, setMetadata] = useState<IssueMetadata | null>(null);
  const [googleBooksStatus, setGoogleBooksStatus] = useState<GoogleBooksStatus | null>(null);
  const [candidates, setCandidates] = useState<AdOpportunity[]>([]);
  const [adPhotos, setAdPhotos] = useState<PhotoRecord[]>([]);
  const [compGroups, setCompGroups] = useState<AdCompGroup[]>([]);
  const [ranking, setRanking] = useState<AdRanking[]>([]);
  const [showCompLinks, setShowCompLinks] = useState(false);
  const [recommendation, setRecommendation] = useState<AdRecommendation | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedCandidateId, setSelectedCandidateId] = useState<number | null>(null);
  const [adPhotoUploadOpen, setAdPhotoUploadOpen] = useState(false);
  const [manualVolumeId, setManualVolumeId] = useState('');
  const [pageNumber, setPageNumber] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!archiveId) return;
    try {
      const [statusRes, issueInfoRes, metadataRes, candidatesRes, recommendationRes, adPhotosRes] = await Promise.all([
        fetch(`${AG_API}/google-books/status`),
        fetch(`${AG_API}/${archiveId}/issue-info`),
        fetch(`${AG_API}/${archiveId}/google-books/metadata`),
        fetch(`${AG_API}/${archiveId}/ad-opportunities`),
        fetch(`${AG_API}/${archiveId}/ad-breakout-recommendation`),
        fetch(`${AG_API}/${archiveId}/ad-page-photos`),
      ]);
      if (statusRes.ok) setGoogleBooksStatus(await statusRes.json());
      if (issueInfoRes.ok) setIssueInfo(await issueInfoRes.json());
      if (metadataRes.ok) setMetadata((await metadataRes.json()).metadata || null);
      if (candidatesRes.ok) setCandidates((await candidatesRes.json()).candidates || []);
      if (recommendationRes.ok) setRecommendation(await recommendationRes.json());
      if (adPhotosRes.ok) setAdPhotos((await adPhotosRes.json()).photos || []);
      const [compsRes, rankingRes] = await Promise.all([
        fetch(`${AG_API}/${archiveId}/ad-comps`),
        fetch(`${AG_API}/${archiveId}/ad-priority-ranking`),
      ]);
      if (compsRes.ok) setCompGroups((await compsRes.json()).groups || []);
      if (rankingRes.ok) setRanking((await rankingRes.json()).ranked_candidates || []);
    } catch {
      /* no-op; explicit actions surface errors */
    }
  }, [archiveId]);

  useEffect(() => { load(); }, [load]);

  const lookupGoogleBooks = async () => {
    if (!archiveId) return;
    setLoading(true); setError(''); setMessage('');
    try {
      const params = new URLSearchParams();
      if (manualVolumeId.trim()) params.set('volume_id', manualVolumeId.trim());
      const suffix = params.toString() ? `?${params.toString()}` : '';
      const res = await fetch(`${AG_API}/${archiveId}/google-books/lookup${suffix}`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Google Books lookup failed (${res.status})`);
      setMetadata(data.metadata || null);
      setMessage(data.cache_hit ? 'Using cached Google Books issue metadata.' : 'Google Books issue metadata stored.');
      await load();
    } catch (e: any) {
      setError(e?.message || 'Google Books lookup failed.');
    } finally {
      setLoading(false);
    }
  };

  const useCachedMetadata = async () => {
    if (!archiveId) return;
    setLoading(true); setError(''); setMessage('');
    try {
      const res = await fetch(`${AG_API}/${archiveId}/google-books/metadata`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `No cached metadata (${res.status})`);
      setMetadata(data.metadata || null);
      setMessage('Cached Google Books metadata loaded.');
      await load();
    } catch (e: any) {
      setError(e?.message || 'No cached Google Books metadata found.');
    } finally {
      setLoading(false);
    }
  };

  const runAdCheck = async () => {
    if (!archiveId) return;
    setLoading(true); setError(''); setMessage('');
    try {
      const res = await fetch(`${AG_API}/${archiveId}/ad-opportunity-check`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Ad opportunity check failed (${res.status})`);
      setCandidates(data.candidates || []);
      setRecommendation(data.recommendation || null);
      setMessage(data.unverified_warning || 'Ad opportunity candidates generated.');
    } catch (e: any) {
      setError(e?.message || 'Ad opportunity check failed.');
    } finally {
      setLoading(false);
    }
  };

  const researchAdComps = async () => {
    if (!archiveId) return;
    setLoading(true); setError(''); setMessage('');
    try {
      const res = await fetch(`${AG_API}/${archiveId}/ad-comps/research`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: 'auto', max_candidates: 5, max_results_per_candidate: 5 }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Ad comp research failed (${res.status})`);
      setCompGroups((await (await fetch(`${AG_API}/${archiveId}/ad-comps`)).json()).groups || []);
      setRanking(data.ranked_candidates || []);
      setMessage(data.note || 'Ad comp research saved.');
    } catch (e: any) {
      setError(e?.message || 'Ad comp research failed.');
    } finally {
      setLoading(false);
    }
  };

  const refreshRanking = async () => {
    if (!archiveId) return;
    setLoading(true); setError(''); setMessage('');
    try {
      const res = await fetch(`${AG_API}/${archiveId}/ad-priority-ranking`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Ranking failed (${res.status})`);
      setRanking(data.ranked_candidates || []);
      setMessage('Ad photograph priority ranking refreshed.');
    } catch (e: any) {
      setError(e?.message || 'Could not refresh ad ranking.');
    } finally {
      setLoading(false);
    }
  };

  const addManualComp = async () => {
    if (!archiveId) return;
    const candidateId = selectedCandidateId || candidates[0]?.id;
    if (!candidateId) {
      setError('Select an ad candidate before adding a manual comp.');
      return;
    }
    const title = window.prompt('Manual comp title') || '';
    const url = window.prompt('Manual comp URL') || '';
    const priceText = window.prompt('Manual comp price, optional') || '';
    if (!title.trim() && !url.trim()) {
      setError('Manual comp requires a title or URL.');
      return;
    }
    setLoading(true); setError(''); setMessage('');
    try {
      const res = await fetch(`${AG_API}/${archiveId}/ad-comps/manual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          candidate_id: candidateId,
          title,
          url,
          price: priceText ? Number(priceText) : null,
          result_type: 'manual_reference',
          currency: 'USD',
          notes: 'Manual founder-entered comp',
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Manual comp failed (${res.status})`);
      setMessage('Manual comp saved.');
      await load();
    } catch (e: any) {
      setError(e?.message || 'Could not save manual comp.');
    } finally {
      setLoading(false);
    }
  };

  const uploadAdPage = async (file: File | null) => {
    if (!archiveId || !file) {
      setError('No ad-page image selected.');
      return;
    }
    if (file.size <= 0) {
      setError('Selected ad-page image is empty.');
      return;
    }
    if (file.type && !SUPPORTED_UPLOAD_MIME_TYPES.has(file.type)) {
      setError('Unsupported ad-page image type. Upload JPEG, PNG, GIF, or WebP.');
      return;
    }
    setUploading(true); setError(''); setMessage('');
    const form = new FormData();
    form.append('file', file);
    if (selectedCandidateId) form.append('candidate_id', String(selectedCandidateId));
    if (pageNumber.trim()) form.append('page_number', pageNumber.trim());
    try {
      const res = await fetch(`${AG_API}/${archiveId}/ad-pages/upload`, { method: 'POST', body: form });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Ad-page upload failed (${res.status})`);
      setMessage(`Ad-page photo saved${selectedCandidateId ? ` for candidate #${selectedCandidateId}` : ''}. Analyze uploaded ad pages to verify.`);
      await load();
    } catch (e: any) {
      setError(e?.message || 'Ad-page upload failed.');
    } finally {
      setUploading(false);
    }
  };

  const analyzeAds = async () => {
    if (!archiveId) return;
    setAnalyzing(true); setError(''); setMessage('');
    try {
      const res = await fetch(`${AG_API}/${archiveId}/ads/analyze`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Ad analysis failed (${res.status})`);
      setMessage(`Analyzed ${data.analyzed?.length || 0} ad-page photo(s). Verified ads are now separated from issue-level candidates.`);
      await load();
    } catch (e: any) {
      setError(e?.message || 'Ad analysis failed.');
    } finally {
      setAnalyzing(false);
    }
  };

  const updateStatus = async (candidateId: number, status: string, suggestedAction = '', userNotes = '') => {
    if (!archiveId) return;
    setError(''); setMessage('');
    try {
      const res = await fetch(`${AG_API}/${archiveId}/ad-opportunities/${candidateId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ verification_status: status, suggested_action: suggestedAction || undefined, user_notes: userNotes || undefined }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Status update failed (${res.status})`);
      setCandidates(prev => prev.map(c => c.id === candidateId ? { ...c, ...(data.candidate || {}), verification_status: status } : c));
      setMessage(`Candidate #${candidateId} marked ${status.replace(/_/g, ' ')}.`);
      await load();
    } catch (e: any) {
      setError(e?.message || 'Could not update candidate status.');
    }
  };

  const addToPacket = async () => {
    if (!archiveId) return;
    setLoading(true); setError(''); setMessage('');
    try {
      const res = await fetch(`${AG_API}/${archiveId}/create-listing-draft`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Could not refresh listing draft (${res.status})`);
      setMessage(`Ad opportunity section will appear in listing packet exports. Draft #${data.draft_id} refreshed.`);
    } catch (e: any) {
      setError(e?.message || 'Could not refresh listing draft.');
    } finally {
      setLoading(false);
    }
  };

  const gradeColor: Record<string, string> = { A: '#16a34a', B: '#2563eb', C: '#f59e0b', D: '#6b7280', F: '#dc2626' };
  const verifiedCount = candidates.filter(c => c.verification_status === 'verified_in_copy').length;
  const selectedCandidate = selectedCandidateId ? candidates.find(c => c.id === selectedCandidateId) || null : null;
  const photosByCandidate = (candidateId: number) => adPhotos.filter(photo => Number((photo as any).candidate_id || 0) === candidateId);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Ad Opportunity Check</h2>
        <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
          ArchiveForge can suggest likely ad opportunities from the identified issue, but an ad is only verified when you photograph that ad page.
        </p>
      </div>

      {!archiveId && (
        <div style={{ padding: 12, background: '#fef9ec', border: '1px solid #fde68a', borderRadius: 10, fontSize: 12, color: '#92400e' }}>
          Save an archive record before running ad checks.
        </div>
      )}
      {googleBooksStatus && !googleBooksStatus.api_key_configured && (
        <div style={{ padding: 12, background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 10, fontSize: 12, color: '#92400e' }}>
          Google Books API key is not configured. Live lookup may be quota-limited. Add GOOGLE_BOOKS_API_KEY server-side for reliable lookups.
        </div>
      )}
      {googleBooksStatus?.cooldown_active && (
        <div style={{ padding: 12, background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 10, fontSize: 12, color: '#991b1b' }}>
          Google Books quota is temporarily limited. Using cached or known issue metadata where available.
        </div>
      )}
      {error && (
        <div style={{ padding: 12, background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 10, fontSize: 12, color: '#991b1b' }}>
          <AlertTriangle size={13} style={{ display: 'inline', marginRight: 4 }} />{error}
        </div>
      )}
      {message && (
        <div style={{ padding: 12, background: '#ecfeff', border: '1px solid #bae6fd', borderRadius: 10, fontSize: 12, color: '#155e75' }}>
          {message}
        </div>
      )}
      {issueInfo?.ad_opportunity_ready && candidates.length > 0 && (
        <div style={{ padding: 12, background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 10, fontSize: 12, color: '#166534' }}>
          <strong>Ad opportunities ready.</strong> Top candidates to look for: {(ranking.length ? ranking : candidates).slice(0, 4).map((item: any) => item.brand || item.category || item.product || 'candidate').join(', ')}.
          <div style={{ marginTop: 4, color: '#92400e' }}>
            These are issue-level leads only. An ad is not verified until you photograph and analyze that ad page.
          </div>
        </div>
      )}
      {issueInfo?.status === 'completed' && !issueInfo.ad_opportunity_ready && (
        <div style={{ padding: 12, background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 10, fontSize: 12, color: '#92400e' }}>
          Issue info is complete, but ad opportunities are not ready for this archive.
        </div>
      )}

      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(220px, 1fr) auto', gap: 8, alignItems: 'end' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 5, fontSize: 11, color: '#666', fontWeight: 700 }}>
            Manual Google Books Volume ID
            <input value={manualVolumeId} onChange={e => setManualVolumeId(e.target.value)} placeholder="9kwEAAAAMBAJ"
              style={{ padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12 }} />
          </label>
          <button onClick={useCachedMetadata} disabled={!archiveId || loading}
            style={{ padding: '9px 12px', borderRadius: 8, border: '1px solid #d1d5db', background: '#fff', color: '#374151', fontSize: 12, fontWeight: 800, cursor: !archiveId || loading ? 'not-allowed' : 'pointer' }}>
            Use Cached Metadata
          </button>
        </div>
        {googleBooksStatus && (
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', fontSize: 11, color: '#666' }}>
            <span>Key: {googleBooksStatus.api_key_configured ? 'configured' : 'missing'}</span>
            <span>Cooldown: {googleBooksStatus.cooldown_active ? 'active' : 'off'}</span>
            <span>Calls last hour: {googleBooksStatus.calls_last_hour ?? 0}</span>
            <span>Cache entries: {googleBooksStatus.cache_entries ?? 0}</span>
          </div>
        )}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button onClick={lookupGoogleBooks} disabled={!archiveId || loading}
            style={{ padding: '9px 12px', borderRadius: 8, border: 'none', background: '#2563eb', color: '#fff', fontSize: 12, fontWeight: 800, cursor: !archiveId || loading ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
            {loading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />} Lookup Google Books Issue
          </button>
          <button onClick={runAdCheck} disabled={!archiveId || loading}
            style={{ padding: '9px 12px', borderRadius: 8, border: '1px solid #f59e0b', background: '#fffbeb', color: '#92400e', fontSize: 12, fontWeight: 800, cursor: !archiveId || loading ? 'not-allowed' : 'pointer' }}>
            Run Ad Opportunity Check
          </button>
          <button onClick={researchAdComps} disabled={!archiveId || loading}
            style={{ padding: '9px 12px', borderRadius: 8, border: '1px solid #7c3aed', background: '#f5f3ff', color: '#5b21b6', fontSize: 12, fontWeight: 800, cursor: !archiveId || loading ? 'not-allowed' : 'pointer' }}>
            Research Ad Comps
          </button>
          <button onClick={() => setShowCompLinks(v => !v)} disabled={!archiveId}
            style={{ padding: '9px 12px', borderRadius: 8, border: '1px solid #d1d5db', background: '#fff', color: '#374151', fontSize: 12, fontWeight: 800, cursor: !archiveId ? 'not-allowed' : 'pointer' }}>
            View Comp Links
          </button>
          <button onClick={addManualComp} disabled={!archiveId || loading}
            style={{ padding: '9px 12px', borderRadius: 8, border: '1px solid #d1d5db', background: '#fff', color: '#374151', fontSize: 12, fontWeight: 800, cursor: !archiveId || loading ? 'not-allowed' : 'pointer' }}>
            Add Manual Comp
          </button>
          <button onClick={refreshRanking} disabled={!archiveId || loading}
            style={{ padding: '9px 12px', borderRadius: 8, border: '1px solid #0f766e', background: '#f0fdfa', color: '#115e59', fontSize: 12, fontWeight: 800, cursor: !archiveId || loading ? 'not-allowed' : 'pointer' }}>
            Rank Ads to Photograph
          </button>
          <button onClick={refreshRanking} disabled={!archiveId || loading}
            style={{ padding: '9px 12px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#f9fafb', color: '#374151', fontSize: 12, fontWeight: 800, cursor: !archiveId || loading ? 'not-allowed' : 'pointer' }}>
            Refresh Ranking
          </button>
          <button onClick={analyzeAds} disabled={!archiveId || analyzing}
            style={{ padding: '9px 12px', borderRadius: 8, border: '1px solid #10b981', background: '#ecfdf5', color: '#065f46', fontSize: 12, fontWeight: 800, cursor: !archiveId || analyzing ? 'not-allowed' : 'pointer' }}>
            {analyzing ? 'Analyzing...' : 'Analyze Uploaded Ad Pages'}
          </button>
          <button onClick={addToPacket} disabled={!archiveId || loading}
            style={{ padding: '9px 12px', borderRadius: 8, border: '1px solid #d1d5db', background: '#fff', color: '#374151', fontSize: 12, fontWeight: 800, cursor: !archiveId || loading ? 'not-allowed' : 'pointer' }}>
            Add Ad Opportunities to Listing Packet
          </button>
          <button disabled style={{ padding: '9px 12px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#f9fafb', color: '#9ca3af', fontSize: 12, fontWeight: 800, cursor: 'not-allowed' }}>
            Create Ad Listing Draft - coming next
          </button>
        </div>

        <div style={{ padding: 10, border: '1px solid #e5e7eb', background: '#f9fafb', borderRadius: 8, fontSize: 11, color: '#666' }}>
          No marketplace API credentials configured. ArchiveForge generated research links and manual comp fields instead of live comps.
        </div>

        {adPhotoUploadOpen && (
          <div style={{ border: '1px solid #06b6d4', background: '#f0fdff', borderRadius: 10, padding: 12, display: 'grid', gap: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontSize: 12, fontWeight: 900, color: '#155e75' }}>Upload/photo page for candidate: {selectedCandidate?.brand || selectedCandidate?.category || selectedCandidate?.product || 'Unassigned'}</div>
                <div style={{ fontSize: 11, color: '#64748b', marginTop: 3 }}>Upload does not verify the ad. Run analysis after upload.</div>
              </div>
              <button onClick={() => setAdPhotoUploadOpen(false)} style={{ border: '1px solid #bae6fd', background: '#fff', color: '#155e75', borderRadius: 8, padding: '5px 8px', fontSize: 11, cursor: 'pointer' }}>Cancel</button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 5, fontSize: 11, color: '#666', fontWeight: 700 }}>
            Candidate for uploaded page
            <select value={selectedCandidateId || ''} onChange={e => setSelectedCandidateId(e.target.value ? Number(e.target.value) : null)}
              style={{ padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12 }}>
              <option value="">Unassigned ad page</option>
              {candidates.map(c => <option key={c.id} value={c.id}>{c.brand || c.category || 'candidate'} {c.product || ''}</option>)}
            </select>
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 5, fontSize: 11, color: '#666', fontWeight: 700 }}>
            Page number
            <input value={pageNumber} onChange={e => setPageNumber(e.target.value)} placeholder="optional"
              style={{ padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12 }} />
          </label>
          <label style={{ padding: '9px 12px', borderRadius: 8, border: '1px solid #06b6d4', background: '#ecfeff', color: '#155e75', fontSize: 12, fontWeight: 800, cursor: archiveId && !uploading ? 'pointer' : 'not-allowed', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
            <Upload size={14} /> Add Ad Page Photo
            <input type="file" accept="image/jpeg,image/png,image/gif,image/webp" style={{ display: 'none' }} disabled={!archiveId || uploading}
              onChange={e => uploadAdPage(e.target.files?.[0] || null).finally(() => { e.currentTarget.value = ''; })} />
          </label>
          <label style={{ padding: '9px 12px', borderRadius: 8, border: '1px solid #06b6d4', background: '#ecfeff', color: '#155e75', fontSize: 12, fontWeight: 800, cursor: archiveId && !uploading ? 'pointer' : 'not-allowed', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
            <Camera size={14} /> Take Ad Page Photo
            <input type="file" accept="image/jpeg,image/png,image/gif,image/webp" capture="environment" style={{ display: 'none' }} disabled={!archiveId || uploading}
              onChange={e => uploadAdPage(e.target.files?.[0] || null).finally(() => { e.currentTarget.value = ''; })} />
          </label>
            </div>
            {selectedCandidateId && photosByCandidate(selectedCandidateId).length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {photosByCandidate(selectedCandidateId).map(photo => (
                  <div key={photo.id || photo.photo_id} style={{ display: 'flex', gap: 6, alignItems: 'center', padding: 6, borderRadius: 8, background: '#fff', border: '1px solid #bae6fd' }}>
                    {photo.thumbnail_url && <img src={`${API}${photo.thumbnail_url.replace('/api/v1', '')}`} alt="uploaded ad page" style={{ width: 42, height: 54, objectFit: 'cover', borderRadius: 5 }} />}
                    <div style={{ fontSize: 10, color: '#475569' }}>Photo #{photo.id || photo.photo_id}<br />{photo.analysis_status || 'pending'}</div>
                  </div>
                ))}
              </div>
            )}
        </div>
        )}
      </div>

      {metadata && (
        <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
          <div style={{ fontSize: 12, fontWeight: 800, color: '#666', marginBottom: 8 }}>GOOGLE BOOKS ISSUE METADATA</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 8, fontSize: 12 }}>
            <div><span style={{ color: '#888' }}>Volume ID: </span>{metadata.source_volume_id || '—'}</div>
            <div><span style={{ color: '#888' }}>Issue date: </span>{metadata.issue_date || '—'}</div>
            <div><span style={{ color: '#888' }}>Publisher: </span>{metadata.publisher || '—'}</div>
            <div><span style={{ color: '#888' }}>Pages: </span>{metadata.page_count || '—'}</div>
            <div><span style={{ color: '#888' }}>Lookup: </span>{metadata.lookup_status || '—'}</div>
            <div><span style={{ color: '#888' }}>Contents terms: </span>{metadata.contents_available ? 'available' : 'not available through official API'}</div>
          </div>
          {metadata.contents_limitation && <div style={{ marginTop: 8, fontSize: 11, color: '#92400e' }}>{metadata.contents_limitation}</div>}
        </div>
      )}

      {recommendation && (
        <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
          <div style={{ fontSize: 12, fontWeight: 800, color: '#666', marginBottom: 8 }}>RECOMMENDATION PANEL</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 8, fontSize: 12 }}>
            <div><span style={{ color: '#888' }}>Recommendation: </span><strong>{recommendation.recommendation || 'insufficient_data'}</strong></div>
            <div><span style={{ color: '#888' }}>Evidence grade: </span>{recommendation.evidence_grade || 'F'}</div>
            <div><span style={{ color: '#888' }}>Whole magazine: </span>{recommendation.whole_magazine_estimate?.low || recommendation.whole_magazine_estimate?.high ? `$${recommendation.whole_magazine_estimate?.low || 0}-$${recommendation.whole_magazine_estimate?.high || 0}` : '—'}</div>
            <div><span style={{ color: '#888' }}>Verified ads: </span>{verifiedCount}</div>
          </div>
          <div style={{ marginTop: 8, fontSize: 12, color: '#374151' }}>{recommendation.reasoning_summary || 'Insufficient data.'}</div>
          <div style={{ marginTop: 4, fontSize: 12, color: '#155e75' }}>Next action: {recommendation.next_action || 'manual review'}</div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 10 }}>
        {candidates.map(candidate => {
          const rank = ranking.find(r => r.candidate_id === candidate.id);
          const group = compGroups.find(g => g.candidate?.id === candidate.id);
          const links = (group?.comps || []).filter(comp => comp.result_type === 'search_link');
          const actionLabel = (rank?.suggested_action || candidate.recommendation || 'needs_comps').replace(/_/g, ' ');
          const candidatePhotos = photosByCandidate(candidate.id);
          const inactive = ['ignored', 'not_found', 'rejected'].includes(candidate.verification_status || '');
          const verified = candidate.verification_status === 'verified_in_copy';
          return (
          <div key={candidate.id} style={{ background: inactive ? '#f9fafb' : '#fff', opacity: inactive ? 0.68 : 1, border: verified ? '1px solid #86efac' : '1px solid #e5e2dc', borderRadius: 12, padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 800, color: '#1a1a1a' }}>{candidate.brand || candidate.category || 'Ad candidate'}</div>
                <div style={{ fontSize: 12, color: '#666' }}>{candidate.product || candidate.category || 'possible opportunity'}</div>
              </div>
              <span style={{ height: 24, minWidth: 32, borderRadius: 6, background: (gradeColor[candidate.evidence_grade || 'D'] || '#6b7280') + '20', color: gradeColor[candidate.evidence_grade || 'D'] || '#6b7280', fontSize: 11, fontWeight: 900, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                {candidate.evidence_grade || 'D'}
              </span>
            </div>
            <div style={{ fontSize: 11, color: candidate.verification_status === 'verified_in_copy' ? '#166534' : '#92400e', background: candidate.verification_status === 'verified_in_copy' ? '#f0fdf4' : '#fffbeb', borderRadius: 6, padding: '5px 7px' }}>
              {candidate.verification_status || 'unverified'} · uploaded photos: {candidatePhotos.length || candidate.uploaded_photo_count || 0} · analyzed: {candidate.analyzed_photo_count || candidatePhotos.filter(p => p.analysis_status && p.analysis_status !== 'pending').length || 0}
            </div>
            <div style={{ fontSize: 11, color: '#666' }}>Search: {candidate.search_query || '—'}</div>
            <div style={{ fontSize: 11, color: '#374151' }}>{candidate.evidence_text || 'Issue-level candidate only.'}</div>
            {(candidate.policy_flags || []).length > 0 && (
              <div style={{ fontSize: 11, color: '#991b1b', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 6, padding: '5px 7px' }}>
                Policy warning: {(candidate.policy_flags || []).join(', ')}
              </div>
            )}
            <div style={{ fontSize: 11, color: '#888' }}>
              Estimate: {candidate.estimated_low || candidate.estimated_high ? `$${candidate.estimated_low || 0}-$${candidate.estimated_high || 0}` : 'Price unavailable until ad is verified or comps are added.'}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: 11, color: '#374151' }}>
              <div>Value score: <strong>{rank?.value_score ?? candidate.value_score ?? 0}</strong></div>
              <div>Confidence: <strong>{rank?.comp_confidence || candidate.comp_confidence || 'none'}</strong></div>
              <div>Comps: {rank?.comp_count ?? candidate.comp_count ?? 0}</div>
              <div>Active: {rank?.active_listing_count ?? candidate.active_listing_count ?? 0}</div>
              <div>Sold: {rank?.sold_comp_count ?? candidate.sold_comp_count ?? 0}</div>
              <div>Action: <strong>{actionLabel}</strong></div>
            </div>
            {showCompLinks && links.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 11 }}>
                {links.slice(0, 3).map(link => (
                  <a key={link.id} href={link.url || '#'} target="_blank" rel="noreferrer"
                    style={{ color: '#2563eb', textDecoration: 'none', overflowWrap: 'anywhere' }}>
                    {link.title || link.provider || 'research link'}
                  </a>
                ))}
              </div>
            )}
            {rank?.reasoning_summary && <div style={{ fontSize: 11, color: '#666' }}>{rank.reasoning_summary}</div>}
            {candidatePhotos.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {candidatePhotos.slice(0, 4).map(photo => (
                  <div key={photo.id || photo.photo_id} title={photo.analysis_status || 'pending'} style={{ display: 'flex', alignItems: 'center', gap: 5, padding: 4, border: '1px solid #e5e7eb', borderRadius: 7, background: '#fff' }}>
                    {photo.thumbnail_url && <img src={`${API}${photo.thumbnail_url.replace('/api/v1', '')}`} alt="ad page" style={{ width: 34, height: 44, objectFit: 'cover', borderRadius: 4 }} />}
                    <span style={{ fontSize: 9, color: '#64748b' }}>{photo.analysis_status || 'pending'}</span>
                  </div>
                ))}
              </div>
            )}
            <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginTop: 'auto' }}>
              <button disabled={inactive || verified} onClick={() => { setSelectedCandidateId(candidate.id); setAdPhotoUploadOpen(true); setMessage(`Ready to upload ad-page photo for ${candidate.brand || candidate.category || 'candidate #' + candidate.id}.`); }} style={{ padding: '5px 7px', border: '1px solid #06b6d4', background: inactive || verified ? '#f3f4f6' : '#ecfeff', color: inactive || verified ? '#9ca3af' : '#155e75', borderRadius: 6, fontSize: 10, fontWeight: 800, cursor: inactive || verified ? 'not-allowed' : 'pointer' }}>
                Photograph this ad if present
              </button>
              <button disabled={verified} onClick={() => updateStatus(candidate.id, 'not_found', 'not_found', 'User reviewed issue and did not find this ad.')} style={{ padding: '5px 7px', border: '1px solid #e5e7eb', background: '#fff', color: verified ? '#9ca3af' : '#6b7280', borderRadius: 6, fontSize: 10, fontWeight: 700, cursor: verified ? 'not-allowed' : 'pointer' }}>
                Mark not found
              </button>
              <button disabled={verified} onClick={() => updateStatus(candidate.id, 'ignored', 'ignore', 'User ignored this issue-level candidate.')} style={{ padding: '5px 7px', border: '1px solid #e5e7eb', background: '#fff', color: verified ? '#9ca3af' : '#6b7280', borderRadius: 6, fontSize: 10, fontWeight: 700, cursor: verified ? 'not-allowed' : 'pointer' }}>
                Ignore
              </button>
              <button disabled title={verified ? 'Verified by uploaded ad-page analysis.' : 'Upload and analyze an ad-page photo before verifying.'} style={{ padding: '5px 7px', border: '1px solid #e5e7eb', background: verified ? '#f0fdf4' : '#f9fafb', color: verified ? '#166534' : '#9ca3af', borderRadius: 6, fontSize: 10, fontWeight: 700, cursor: 'not-allowed' }}>
                {verified ? 'Verified in this copy' : 'Verify after analysis'}
              </button>
            </div>
          </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Section 4: Physical Archive ────────────────────────────────────────────────

const STATUS_TRANSITIONS: Record<string, string[]> = {
  RAW: ["IDENTIFIED","HOLD"], IDENTIFIED: ["PHOTOGRAPHED","HOLD","REBOXED"],
  PHOTOGRAPHED: ["VALUED","HOLD"], VALUED: ["READY_TO_LIST","HOLD","REBOXED"],
  READY_TO_LIST: ["LISTED","HOLD","REBOXED"], LISTED: ["SOLD","HOLD","REBOXED"],
  SOLD: [], HOLD: ["RAW","IDENTIFIED","PHOTOGRAPHED","VALUED","READY_TO_LIST"],
  REBOXED: ["RAW","IDENTIFIED","PHOTOGRAPHED","VALUED","READY_TO_LIST"],
};

function ArchiveSection({ data, archiveId, onChange }: {
  data: Partial<ArchiveItem>;
  archiveId: number | null;
  onChange: (d: Partial<ArchiveItem>) => void;
}) {
  const [transitioning, setTransitioning] = useState(false);
  const [transitionError, setTransitionError] = useState('');

  const update = (field: keyof ArchiveItem, value: any) => onChange({ ...data, [field]: value });

  const handleStatusTransition = async (newStatus: string) => {
    if (!archiveId) return;
    setTransitionError('');
    setTransitioning(true);
    try {
      const res = await fetch(`${AG_API}/archives/${archiveId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        const d = await res.json();
        update('processed_status', d.processed_status);
      } else {
        const err = await res.json().catch(() => ({ detail: 'Transition failed' }));
        setTransitionError(err.detail || `Cannot transition to ${newStatus}`);
      }
    } catch {
      setTransitionError('Network error — try again');
    }
    setTransitioning(false);
  };

  const allowed = STATUS_TRANSITIONS[data.processed_status as string] || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Step 4 — Physical Archive Tracking</h2>
        <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
          Track exactly where this item lives at each stage. Source box = where you found it. Processed box = where it goes next.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Source Box */}
        <div style={{ background: '#fff', border: '2px solid #e5e2dc', borderRadius: 12, padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6, color: '#6b7280' }}>
            <Box size={14} />
            Source Box — where you found it
          </div>
          <div style={{ marginBottom: 8 }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Box Code (exact label as-is)</label>
            <input value={data.source_box_code || ''} onChange={e => update('source_box_code', e.target.value)}
              placeholder="e.g. A-RARE-01"
              style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 13 }} />
          </div>
          <div>
            <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Slot Position (optional)</label>
            <input value={data.source_slot_position || ''} onChange={e => update('source_slot_position', e.target.value)}
              placeholder="e.g. top shelf, left corner"
              style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 13 }} />
          </div>
          <div style={{ marginTop: 6, fontSize: 10, color: '#aaa' }}>
            Examples: A-RARE-01, B-WWII-01, C-BULK-01
          </div>
        </div>

        {/* Processed Box */}
        <div style={{ background: '#fff', border: '2px solid #06b6d4', borderRadius: 12, padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 6, color: '#06b6d4' }}>
            <Package size={14} />
            Processed Box — destination after this step
          </div>
          <div style={{ marginBottom: 8 }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Processed Box Code</label>
            <input value={data.processed_box_code || ''} onChange={e => update('processed_box_code', e.target.value)}
              placeholder="e.g. B-1960s-01"
              style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 13 }} />
          </div>
          <div style={{ marginBottom: 8 }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Archive Location</label>
            <input value={data.archive_location || ''} onChange={e => update('archive_location', e.target.value)}
              placeholder="e.g. shelf B2, cabinet 3"
              style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 13 }} />
          </div>
          <div>
            <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>
              Current Status
              {transitioning && <span style={{ marginLeft: 6, color: '#06b6d4' }}><Loader2 size={10} className="animate-spin" /></span>}
            </label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {STATUSES.map(s => {
                const isActive = data.processed_status === s;
                const canTransition = allowed.includes(s);
                return (
                  <button key={s}
                    onClick={() => canTransition && !transitioning && handleStatusTransition(s)}
                    disabled={!canTransition || transitioning}
                    style={{
                      padding: '3px 8px', borderRadius: 6, fontSize: 10, fontWeight: 600,
                      cursor: canTransition && !transitioning ? 'pointer' : 'not-allowed',
                      background: isActive ? STATUS_COLORS[s] : canTransition ? '#f5f3ef' : '#f9f9f9',
                      color: isActive ? '#fff' : canTransition ? '#666' : '#ccc',
                      border: 'none', opacity: (canTransition || isActive) ? 1 : 0.5,
                    }}>
                    {s}
                  </button>
                );
              })}
            </div>
            {transitionError && (
              <div style={{ marginTop: 6, fontSize: 11, color: '#dc2626', background: '#fef2f2', padding: '6px 8px', borderRadius: 6 }}>
                <AlertTriangle size={11} style={{ display: 'inline', marginRight: 4 }} />
                {transitionError}
              </div>
            )}
          </div>
          {/* Reboxed metadata */}
          {data.processed_status === 'REBOXED' && (
            <div style={{ marginTop: 10, padding: '8px 10px', background: '#f9f9f9', borderRadius: 8, fontSize: 11, color: '#666' }}>
              <div><span style={{ color: '#888' }}>Reboxed at:</span> {data.reboxed_at ? fmt(data.reboxed_at) : 'just now'}</div>
              {data.reboxed_by && <div><span style={{ color: '#888' }}>By:</span> {data.reboxed_by}</div>}
            </div>
          )}
        </div>
      </div>

      {/* Box convention guide */}
      <div style={{ background: '#f9f8f6', borderRadius: 10, padding: 12, fontSize: 11, color: '#666' }}>
        <strong>Box convention guide:</strong> A-RARE-01 (rare/valuable Tier A) · B-[era]-[##] (Tier B by decade) · C-BULK-01 (common Tier C) · HOLD-01 (awaiting decision) · SOLD-STAGING-01 (ready to ship)
      </div>
    </div>
  );
}

// ── Section 5: Condition + Value ───────────────────────────────────────────────

function ConditionSection({ data, onChange }: { data: Partial<ArchiveItem>; onChange: (d: Partial<ArchiveItem>) => void }) {
  const update = (field: keyof ArchiveItem, value: any) => onChange({ ...data, [field]: value });
  const CONDITIONS = [
    { score: 5, label: "Near Mint", desc: "No visible wear, clean pages, vibrant colors", color: '#16a34a' },
    { score: 4, label: "Excellent", desc: "Minor shelf wear, no creases or tears", color: '#22c55e' },
    { score: 3, label: "Good", desc: "Some wear, minor foxing or light creasing", color: '#f59e0b' },
    { score: 2, label: "Fair", desc: "Visible wear, small tears, foxing, writing", color: '#ef4444' },
    { score: 1, label: "Poor", desc: "Heavy damage, missing pages, major defects", color: '#991b1b' },
  ];
  const Tiers = ['A','B','C'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Step 5 — Condition & Tier</h2>
        <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
          Score condition against the reference issue. Assign tier based on historical significance.
        </p>
      </div>

      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 10 }}>Condition Score</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {CONDITIONS.map(c => (
            <button key={c.score} onClick={() => update('condition_score', c.score)}
              style={{
                padding: '8px 12px', borderRadius: 10, border: `2px solid ${data.condition_score === c.score ? c.color : '#e5e2dc'}`,
                background: data.condition_score === c.score ? c.color + '15' : '#fff',
                cursor: 'pointer', textAlign: 'left', flex: '1 1 140px',
              }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: data.condition_score === c.score ? c.color : '#1a1a1a' }}>
                {c.score} — {c.label}
              </div>
              <div style={{ fontSize: 10, color: '#888', marginTop: 2 }}>{c.desc}</div>
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
          <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8 }}>Checks</div>
          {[
            { field: 'has_address_label', label: 'Has address label' },
            { field: 'is_complete', label: 'Complete (no missing pages)' },
          ].map(({ field, label }) => {
            const val = (data as any)[field] as boolean;
            return (
              <label key={field} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, cursor: 'pointer' }}>
                <input type="checkbox" checked={val === true} onChange={e => update(field as keyof ArchiveItem, e.target.checked)}
                  style={{ width: 16, height: 16, cursor: 'pointer' }} />
                <span style={{ fontSize: 13 }}>{label}</span>
              </label>
            );
          })}
        </div>

        <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
          <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8 }}>Tier Assignment</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {Tiers.map(t => (
              <button key={t} onClick={() => update('tier', t)}
                style={{
                  padding: '8px 12px', borderRadius: 8, border: `2px solid ${data.tier === t ? TIER_COLORS[t] : '#e5e2dc'}`,
                  background: data.tier === t ? TIER_COLORS[t] + '15' : '#fff',
                  cursor: 'pointer', textAlign: 'left',
                }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontWeight: 700, color: TIER_COLORS[t], fontSize: 13 }}>Tier {t}</span>
                  <span style={{ fontSize: 11, color: '#888' }}>— {TIER_LABELS[t]}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
        <div style={{ marginTop: 12 }}>
          <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Defects</label>
          <input value={data.defects || ''} onChange={e => update('defects', e.target.value)}
            placeholder="e.g. spine crease, water stain on back cover, writing on page 5"
            style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 13 }} />
        </div>
        <div style={{ marginTop: 12 }}>
          <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Notes</label>
          <textarea value={data.notes || ''} onChange={e => update('notes', e.target.value)} rows={2}
            placeholder="Internal notes about this item..."
            style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 13, resize: 'vertical' }} />
        </div>
      </div>
    </div>
  );
}

function PricingSection({
  data,
  archiveId,
  identifyResult,
  confirmation,
  onChange,
}: {
  data: Partial<ArchiveItem>;
  archiveId: number | null;
  identifyResult: IdentifyResponse | null;
  confirmation: MatchConfirmation | null;
  onChange: (d: Partial<ArchiveItem>) => void;
}) {
  const [early, setEarly] = useState<PricingResult | null>(null);
  const [finalPricing, setFinalPricing] = useState<PricingResult | null>(null);
  const [compData, setCompData] = useState<any>(null);
  const [loadingAction, setLoadingAction] = useState('');
  const [error, setError] = useState('');
  const update = (field: keyof ArchiveItem, value: any) => onChange({ ...data, [field]: value });
  const aiRange = identifyResult?.ai_result?.recommended_price_range || {};

  const callPricing = async (mode: 'estimate' | 'final', acceptFinal = false) => {
    if (!archiveId) return;
    setLoadingAction(mode + (acceptFinal ? ':accept' : ''));
    setError('');
    try {
      const res = await fetch(`${AG_API}/${archiveId}/pricing/${mode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rough_comp_min: data.rough_comp_min || 0,
          rough_comp_max: data.rough_comp_max || 0,
          sale_plan: data.sale_plan || '',
          accept_final: acceptFinal,
        }),
      });
      const out = await res.json();
      if (!res.ok) throw new Error(out.detail || `Pricing failed with ${res.status}`);
      if (mode === 'estimate') setEarly(out);
      else setFinalPricing(out);
      if (acceptFinal) update('processed_status', 'VALUED');
    } catch (exc: any) {
      setError(exc?.message || 'Pricing request failed.');
    } finally {
      setLoadingAction('');
    }
  };

  const ResultBox = ({ label, result }: { label: string; result: PricingResult | null }) => result ? (
    <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 10, padding: 12, fontSize: 12, display: 'grid', gap: 5 }}>
      <div style={{ fontWeight: 800, color: '#1f2937' }}>{label}</div>
      <div><span style={{ color: '#888' }}>Type: </span>{result.pricing_type}</div>
      <div><span style={{ color: '#888' }}>Comp evidence: </span>{result.true_comps_available ? 'stored comps available' : 'needs comps / reference guide only'}</div>
      <div><span style={{ color: '#888' }}>Confidence: </span>{result.confidence || result.pricing_summary?.confidence || 'none'}</div>
      <div><span style={{ color: '#888' }}>Manual rough range: </span>${result.rough_comp_min || 0}–${result.rough_comp_max || 0}</div>
      <div><span style={{ color: '#888' }}>Recommended price: </span>{result.recommended_price ? `$${result.recommended_price}` : '—'}</div>
      <div style={{ color: '#666' }}>{result.message}</div>
      {(result.warnings || result.pricing_summary?.warnings || []).map((w: string) => <div key={w} style={{ color: '#92400e' }}>{w}</div>)}
    </div>
  ) : null;

  const researchComps = async () => {
    if (!archiveId) return;
    setLoadingAction('research-comps');
    setError('');
    try {
      const res = await fetch(`${AG_API}/${archiveId}/comps/research`, { method: 'POST' });
      const out = await res.json();
      if (!res.ok) throw new Error(out.detail || `Comp research failed with ${res.status}`);
      setCompData(out);
      setFinalPricing({ ...(finalPricing || {} as any), ...out.pricing_summary, pricing_summary: out.pricing_summary, stage: 'comp_research', true_comps_available: false, message: out.pricing_summary?.pricing_basis || out.note, rough_comp_min: data.rough_comp_min || 0, rough_comp_max: data.rough_comp_max || 0 });
    } catch (exc: any) {
      setError(exc?.message || 'Comp research failed.');
    } finally {
      setLoadingAction('');
    }
  };

  const calculatePricing = async () => {
    if (!archiveId) return;
    setLoadingAction('calculate-pricing');
    setError('');
    try {
      const res = await fetch(`${AG_API}/${archiveId}/pricing/calculate`, { method: 'POST' });
      const out = await res.json();
      if (!res.ok) throw new Error(out.detail || `Pricing calculation failed with ${res.status}`);
      setFinalPricing({ ...(finalPricing || {} as any), ...out, pricing_summary: out, stage: 'pricing_calculate', true_comps_available: (out.sold_comp_count || out.active_listing_count || out.dealer_listing_count) > 0, message: out.pricing_basis, rough_comp_min: data.rough_comp_min || 0, rough_comp_max: data.rough_comp_max || 0 });
    } catch (exc: any) {
      setError(exc?.message || 'Pricing calculation failed.');
    } finally {
      setLoadingAction('');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Pricing & Comps</h2>
        <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
          Pricing happens after condition. ArchiveForge stores source-labeled comp evidence and keeps DTM guide values separate from current sold comps.
        </p>
      </div>

      {error && (
        <div style={{ padding: 12, background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 10, fontSize: 12, color: '#991b1b' }}>
          <AlertTriangle size={13} style={{ display: 'inline', marginRight: 4 }} />
          {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
          <div style={{ fontSize: 13, fontWeight: 800, marginBottom: 8 }}>Early Estimate</div>
          <div style={{ fontSize: 12, color: '#666', lineHeight: 1.45 }}>
            Available after AI identify/reference confirmation. This is preliminary and should not override final condition-based pricing.
          </div>
          <div style={{ marginTop: 8, fontSize: 12 }}>
            <div><span style={{ color: '#888' }}>Match confirmed: </span>{confirmation?.status === 'confirmed' || confirmation?.status === 'manual' ? 'yes' : 'not yet'}</div>
            <div><span style={{ color: '#888' }}>AI price hint: </span>{aiRange.low || aiRange.high ? `$${aiRange.low || 0}–$${aiRange.high || 0}` : '—'}</div>
          </div>
          <button onClick={() => callPricing('estimate')} disabled={!archiveId || loadingAction !== ''}
            style={{ marginTop: 10, padding: '8px 12px', background: '#eef2ff', color: '#3730a3', border: '1px solid #c7d2fe', borderRadius: 8, fontSize: 12, fontWeight: 800, cursor: loadingAction ? 'wait' : 'pointer' }}>
            {loadingAction === 'estimate' ? 'Running…' : 'Run Early Estimate'}
          </button>
        </div>

        <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
          <div style={{ fontSize: 13, fontWeight: 800, marginBottom: 8 }}>Final Pricing</div>
          <div style={{ fontSize: 12, color: '#666', lineHeight: 1.45 }}>
            Use after condition score, defects, completeness, address-label status, and sale plan are entered.
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 10 }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: '#666' }}>
              Comp Range Min ($)
              <input type="number" value={data.rough_comp_min || ''} onChange={e => update('rough_comp_min', parseFloat(e.target.value) || 0)}
                placeholder="0" style={{ marginTop: 4, width: '100%', padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 13 }} />
            </label>
            <label style={{ fontSize: 11, fontWeight: 700, color: '#666' }}>
              Comp Range Max ($)
              <input type="number" value={data.rough_comp_max || ''} onChange={e => update('rough_comp_max', parseFloat(e.target.value) || 0)}
                placeholder="0" style={{ marginTop: 4, width: '100%', padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 13 }} />
            </label>
          </div>
          <label style={{ display: 'block', marginTop: 10, fontSize: 11, fontWeight: 700, color: '#666' }}>
            Sale Plan
            <input value={data.sale_plan || ''} onChange={e => update('sale_plan', e.target.value)}
              placeholder="e.g. list on eBay, list on AbeBooks, hold for convention"
              style={{ marginTop: 4, width: '100%', padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 13 }} />
          </label>
          <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
            <button onClick={() => callPricing('final')} disabled={!archiveId || loadingAction !== ''}
              style={{ padding: '8px 12px', background: '#fef9ec', color: '#92400e', border: '1px solid #fde68a', borderRadius: 8, fontSize: 12, fontWeight: 800, cursor: loadingAction ? 'wait' : 'pointer' }}>
              {loadingAction === 'final' ? 'Running…' : 'Run Final Pricing'}
            </button>
            <button onClick={() => callPricing('final', true)} disabled={!archiveId || loadingAction !== ''}
              style={{ padding: '8px 12px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 800, cursor: loadingAction ? 'wait' : 'pointer' }}>
              {loadingAction === 'final:accept' ? 'Accepting…' : 'Accept Final Price'}
            </button>
          </div>
        </div>
      </div>

      <ResultBox label="Early Estimate Result" result={early} />
      <ResultBox label="Final Pricing Result" result={finalPricing} />

      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14, display: 'grid', gap: 10 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 800 }}>Magazine Comps</div>
          <div style={{ fontSize: 11, color: '#777', marginTop: 2 }}>
            DTM guide values are reference-guide values, not current sold comps. Active listings are asking prices, not sold comps.
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button onClick={researchComps} disabled={!archiveId || loadingAction !== ''} style={{ padding: '8px 12px', background: '#ecfeff', color: '#155e75', border: '1px solid #bae6fd', borderRadius: 8, fontSize: 12, fontWeight: 800, cursor: loadingAction ? 'wait' : 'pointer' }}>
            {loadingAction === 'research-comps' ? 'Researching...' : 'Research Magazine Comps'}
          </button>
          <a href={archiveId ? `${AG_API}/${archiveId}/comps` : '#'} target="_blank" rel="noreferrer" style={{ padding: '8px 12px', background: '#fff', color: '#374151', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12, fontWeight: 800, textDecoration: 'none' }}>
            View Comp Links
          </a>
          <button onClick={calculatePricing} disabled={!archiveId || loadingAction !== ''} style={{ padding: '8px 12px', background: '#111827', color: '#fff', border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 800, cursor: loadingAction ? 'wait' : 'pointer' }}>
            {loadingAction === 'calculate-pricing' ? 'Calculating...' : 'Calculate Pricing'}
          </button>
          <button disabled style={{ padding: '8px 12px', background: '#f3f4f6', color: '#9ca3af', border: '1px solid #e5e7eb', borderRadius: 8, fontSize: 12, fontWeight: 800 }}>
            Add Manual Comp
          </button>
        </div>
        {compData?.stored_results?.length > 0 && (
          <div style={{ display: 'grid', gap: 5, fontSize: 11 }}>
            {compData.stored_results.slice(0, 8).map((comp: any) => (
              <div key={`${comp.id}-${comp.url}`} style={{ padding: 8, border: '1px solid #eee8df', borderRadius: 8 }}>
                <strong>{comp.result_type}</strong> · {comp.title || comp.query} {comp.url ? <a href={comp.url} target="_blank" rel="noreferrer" style={{ marginLeft: 6 }}>open</a> : null}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Section 6: Listing Builder ─────────────────────────────────────────────────

function ListingBuilderSection({ data, refIssue, archiveId, onSaved }: {
  data: Partial<ArchiveItem>;
  refIssue: LifeReferenceIssue | null;
  archiveId: number | null;
  onSaved: () => void;
}) {
  const [title, setTitle] = useState(data.listing_title || '');
  const [description, setDescription] = useState(data.listing_description || '');
  const [batchTag, setBatchTag] = useState(data.batch_tag || '');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Sync when data changes (e.g., navigating back)
  useEffect(() => { setTitle(data.listing_title || ''); }, [data.listing_title]);
  useEffect(() => { setDescription(data.listing_description || ''); }, [data.listing_description]);
  useEffect(() => { setBatchTag(data.batch_tag || ''); }, [data.batch_tag]);

  const generateFromData = useCallback(() => {
    const issueDate = data.issue_date || refIssue?.date || '';
    const year = issueDate ? issueDate.split('-')[0] : '';
    const subject = data.cover_subject || refIssue?.cover_subject || '';
    const condScore = data.condition_score || 3;
    const condLabels = ['','Poor','Fair','Good','Excellent','Near Mint'];
    const cond = condLabels[condScore] || 'Good';
    const tier = data.tier || refIssue?.tier_guidance || 'C';

    const genTitle = `LIFE Magazine ${year ? `(${year}) ` : ''}${subject} — ${cond} Condition ${tier !== 'C' ? `| ${tier} Tier` : ''}`.trim();
    const genDesc = [
      subject ? `LIFE Magazine feature: ${subject}.` : '',
      issueDate ? `Original issue date: ${issueDate}.` : '',
      `Volume ${data.volume || refIssue?.volume || '—'}, Issue ${data.issue_number || refIssue?.issue_number || '—'}.`,
      `Condition: ${cond}.`,
      data.has_address_label ? 'Features original mailing address label.' : '',
      data.is_complete ? 'Complete — no missing pages.' : 'Incomplete — see description.',
      data.defects ? `Defects: ${data.defects}.` : '',
      'All items are shipped in archival-quality packaging. Questions welcome.',
    ].filter(Boolean).join(' ');

    setTitle(genTitle);
    setDescription(genDesc);
  }, [data, refIssue]);

  const handleSave = async () => {
    if (!title.trim()) return;
    if (!archiveId) return;
    setSaving(true);
    try {
      const res = await fetch(`${AG_API}/archives/${archiveId}/save-draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ listing_title: title, listing_description: description, batch_tag: batchTag }),
      });
      if (res.ok) {
        setSaved(true);
        onSaved();
      }
    } catch { /* silent */ }
    setSaving(false);
  };

  const condLabels = ['','Poor','Fair','Good','Excellent','Near Mint'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Step 6 — Listing Builder</h2>
        <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
          Build the listing text. Auto-generate from your data, then refine. Saved as draft only — not published.
        </p>
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <button onClick={generateFromData}
          style={{ padding: '8px 16px', background: '#f5f3ef', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
          <RefreshCw size={13} /> Auto-fill from Archive Data
        </button>
        <span style={{ fontSize: 11, color: '#888' }}>Generates title and description from Steps 1–5</span>
      </div>

      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 16 }}>
        <div style={{ marginBottom: 12 }}>
          <label style={{ fontSize: 11, fontWeight: 700, color: '#666', display: 'block', marginBottom: 4 }}>Listing Title</label>
          <input value={title} onChange={e => setTitle(e.target.value)}
            placeholder="Auto-fill or type your own title..."
            style={{ width: '100%', padding: '10px 12px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 13 }} />
        </div>
        <div>
          <label style={{ fontSize: 11, fontWeight: 700, color: '#666', display: 'block', marginBottom: 4 }}>Description</label>
          <textarea value={description} onChange={e => setDescription(e.target.value)} rows={6}
            placeholder="Auto-fill or write your own description..."
            style={{ width: '100%', padding: '10px 12px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 13, resize: 'vertical' }} />
        </div>
        <div style={{ marginTop: 12 }}>
          <label style={{ fontSize: 11, fontWeight: 700, color: '#666', display: 'block', marginBottom: 4 }}>Batch Tag</label>
          <input value={batchTag} onChange={e => setBatchTag(e.target.value)}
            placeholder="e.g. LIFE-Q2-2026, estate-lot-01, convention-2026"
            style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 13 }} />
        </div>
      </div>

      {/* Item Specifics Preview */}
      {Object.keys(data).length > 0 && (
        <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
          <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8 }}>Item Specifics Preview</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 24px', fontSize: 12 }}>
            {[
              ['Format', 'Magazine'],
              ['Publication', 'LIFE'],
              ['Year', (data.issue_date || refIssue?.date || '').split('-')[0]],
              ['Issue Date', data.issue_date || refIssue?.date || ''],
              ['Volume', String(data.volume || refIssue?.volume || '')],
              ['Issue Number', String(data.issue_number || refIssue?.issue_number || '')],
              ['Cover Subject', data.cover_subject || refIssue?.cover_subject || ''],
              ['Condition', condLabels[data.condition_score || 3] || '—'],
              ['Tier', data.tier || refIssue?.tier_guidance || '—'],
              ['Address Label', data.has_address_label ? 'Yes' : 'No'],
              ['Complete', data.is_complete !== false ? 'Yes' : 'No'],
              ['Defects', data.defects || '—'],
              ['Comp Range', data.rough_comp_min && data.rough_comp_max ? `$${data.rough_comp_min}–$${data.rough_comp_max}` : '—'],
              ['Sale Plan', data.sale_plan || '—'],
              ['Batch Tag', batchTag || '—'],
            ].map(([k, v]) => v && v !== '—' && v !== '' ? (
              <div key={k}><span style={{ color: '#888' }}>{k}: </span><span style={{ fontWeight: 500 }}>{v}</span></div>
            ) : null)}
          </div>
        </div>
      )}

      <button onClick={handleSave} disabled={saving || !title.trim() || !archiveId}
        style={{ padding: '12px 24px', background: saved ? '#16a34a' : saving ? '#9ca3af' : '#06b6d4', color: '#fff', border: 'none', borderRadius: 10, fontSize: 14, fontWeight: 700, cursor: saving || !title.trim() || !archiveId ? 'wait' : 'pointer', display: 'flex', alignItems: 'center', gap: 8, alignSelf: 'flex-start' }}>
        {saved ? <><Check size={16} /> Draft Saved</> : saving ? <><Loader2 size={14} className="animate-spin" /> Saving...</> : <><List size={14} /> Save Draft & Continue</>}
      </button>
    </div>
  );
}

// ── Section 7: Review & Publish ─────────────────────────────────────────────────

function ReviewPublishSection({ archiveId, refIssue }: {
  archiveId: number | null;
  refIssue: LifeReferenceIssue | null;
}) {
  const [item, setItem] = useState<Partial<ArchiveItem>>({});
  const [photos, setPhotos] = useState<PhotoRecord[]>([]);
  const [loading, setLoading] = useState(true);
	  const [pushState, setPushState] = useState<'idle' | 'pushing' | 'success' | 'error'>('idle');
	  const [pushResult, setPushResult] = useState<any>(null);
	  const [pushError, setPushError] = useState('');
	  const [publishStatus, setPublishStatus] = useState<{
      publish_available: boolean;
      reason: string;
      action_label: string;
      target: string;
      approval_required?: boolean;
      missing_required_fields?: string[];
      invalid_required_fields?: string[];
      publish_mode?: string;
    } | null>(null);
  const [marketforgeCategoryId, setMarketforgeCategoryId] = useState('');
  const [marketforgeShipsFromZip, setMarketforgeShipsFromZip] = useState('');
  const [savingPublishFields, setSavingPublishFields] = useState(false);
  const [listingDraft, setListingDraft] = useState<ListingPacketDraft | null>(null);
  const [draftState, setDraftState] = useState<'idle' | 'creating' | 'success' | 'error'>('idle');
  const [draftError, setDraftError] = useState('');

  const load = useCallback(async () => {
    if (!archiveId) { setLoading(false); return; }
    setLoading(true);
	    try {
	      const [archRes, photoRes, publishRes, listingDraftRes] = await Promise.all([
	        fetch(`${AG_API}/archives/${archiveId}`),
	        fetch(`${AG_API}/uploads/${archiveId}`),
	        fetch(`${AG_API}/publish-status?archive_id=${archiveId}`),
	        fetch(`${AG_API}/${archiveId}/listing-draft`),
	      ]);
	      if (archRes.ok) {
          const archiveItem = await archRes.json();
          setItem(archiveItem);
          setMarketforgeCategoryId(archiveItem.marketforge_category_id || '');
          setMarketforgeShipsFromZip(archiveItem.marketforge_ships_from_zip || '');
        }
	      if (photoRes.ok) setPhotos((await photoRes.json()).photos || []);
	      if (publishRes.ok) setPublishStatus(await publishRes.json());
	      if (listingDraftRes.ok) {
	        const data = await listingDraftRes.json();
	        setListingDraft(data.draft || data);
	      } else if (listingDraftRes.status === 404 || listingDraftRes.status === 409) {
	        setListingDraft(null);
	      }
	    } catch { /* */ }
    setLoading(false);
  }, [archiveId]);

  useEffect(() => { load(); }, [load]);

  const validStatuses = ['READY_TO_LIST', 'LISTED'];
  const canPublish = item.processed_status && validStatuses.includes(item.processed_status);
  const hasTitle = !!(item.listing_title);
  const hasDescription = !!(item.listing_description);
	  const hasPhotos = photos.length > 0;
	  const publishUnavailable = publishStatus && publishStatus.publish_available === false;
  const missingRequiredFields = publishStatus?.missing_required_fields || [];
  const invalidRequiredFields = publishStatus?.invalid_required_fields || [];

	  const validationErrors: string[] = [];
	  if (publishUnavailable) validationErrors.push(publishStatus.reason || 'MarketForge publish is unavailable');
	  if (missingRequiredFields.length > 0) validationErrors.push(`Missing required MarketForge fields: ${missingRequiredFields.join(', ')}`);
	  if (invalidRequiredFields.length > 0) validationErrors.push(`Invalid MarketForge fields: ${invalidRequiredFields.join(', ')}`);
	  if (!canPublish) validationErrors.push(`Status must be ${validStatuses.join(' or ')} (currently ${item.processed_status || 'unset'})`);
	  if (!hasTitle) validationErrors.push('Listing title is blank — go back to Step 6 and save a draft');
	  if (!hasDescription) validationErrors.push('Listing description is blank — go back to Step 6 and save a draft');
	  if (!hasPhotos) validationErrors.push('No actual listing photos uploaded — go back to Step 3');

	  const draftPreview = listingDraft?.draft || listingDraft;
	  const draftId = listingDraft?.draft_id || draftPreview?.draft_id;
	  const draftStatus = listingDraft?.draft_status || draftPreview?.draft_status;
	  const draftTitle = listingDraft?.title || draftPreview?.title || item.listing_title || '';
	  const draftPrice = listingDraft?.recommended_price ?? draftPreview?.recommended_price ?? null;
	  const draftMissingFields = listingDraft?.missing_fields || draftPreview?.missing_fields || [];

	  const createListingDraft = async () => {
	    if (!archiveId) return;
	    setDraftState('creating');
	    setDraftError('');
	    try {
	      const res = await fetch(`${AG_API}/${archiveId}/create-listing-draft`, { method: 'POST' });
	      const data = await res.json().catch(() => ({}));
	      if (!res.ok) throw new Error(data.detail || `Failed to create listing draft (${res.status})`);
	      setListingDraft(data);
	      setDraftState('success');
	      await load();
	    } catch (e: any) {
	      setDraftState('error');
	      setDraftError(e?.message || 'Could not create listing draft');
	    }
	  };

  const savePublishFields = useCallback(async () => {
    if (!archiveId) return false;
    setSavingPublishFields(true);
    try {
      const res = await fetch(`${AG_API}/archives/${archiveId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          marketforge_category_id: marketforgeCategoryId.trim(),
          marketforge_ships_from_zip: marketforgeShipsFromZip.trim(),
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        throw new Error(err.detail || `Failed to save publish fields (${res.status})`);
      }
      await load();
      return true;
    } catch (e: any) {
      setPushState('error');
      setPushError(e?.message || 'Could not save publish fields');
      return false;
    } finally {
      setSavingPublishFields(false);
    }
  }, [archiveId, load, marketforgeCategoryId, marketforgeShipsFromZip]);

  const handlePublish = async () => {
    if (!archiveId) return;
    setPushState('pushing');
    setPushError('');
    setPushResult(null);
    try {
      const saved = await savePublishFields();
      if (!saved) {
        setPushState('error');
        return;
      }
      const res = await fetch(`${AG_API}/push/${archiveId}?approval_confirmed=true`, { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setPushState('success');
        setPushResult(data);
        await load();
      } else {
        setPushState('error');
        setPushError(data.detail || `HTTP ${res.status}: Push failed`);
      }
    } catch (e: any) {
      setPushState('error');
      setPushError(e.message || 'Network error');
    }
  };

  if (!archiveId) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Step 7 — Review & Publish</h2>
        <div style={{ padding: 24, background: '#fef9ec', border: '1px solid #fde68a', borderRadius: 10, fontSize: 13, color: '#92400e' }}>
          No archive record saved yet. Complete Steps 1–6 first.
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Step 7 — Review & Publish</h2>
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}><Loader2 size={20} className="animate-spin" style={{ color: '#06b6d4' }} /></div>
      </div>
    );
  }

  const item_specifics = item.item_specifics || {};
  const condLabels = ['','Poor','Fair','Good','Excellent','Near Mint'];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
	      <div>
	        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Step 7 — Review Listing Draft & Export</h2>
	        <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
	          Review the listing draft, create the handoff packet, then export. Publishing remains a separate explicit action.
	        </p>
	      </div>

      {/* Validation errors */}
      {validationErrors.length > 0 && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 10, padding: '12px 14px' }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#dc2626', marginBottom: 6 }}>Cannot publish — fix these issues first:</div>
          {validationErrors.map((err, i) => (
            <div key={i} style={{ fontSize: 12, color: '#991b1b', display: 'flex', gap: 6, alignItems: 'flex-start', marginBottom: 3 }}>
              <AlertTriangle size={12} style={{ marginTop: 2, flexShrink: 0 }} />
              {err}
            </div>
          ))}
        </div>
      )}

      {/* Publish status banner */}
      {(item.marketforge_push_status === 'pushed' || item.listing_status === 'pushed') && (
        <div style={{ background: '#f0fdf4', border: '1px solid #86efac', borderRadius: 10, padding: '12px 14px' }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#16a34a', display: 'flex', alignItems: 'center', gap: 6 }}>
            <CheckCircle size={15} /> Published to MarketForge
          </div>
          {item.marketforge_listing_id && (
            <div style={{ fontSize: 12, color: '#166534', marginTop: 4 }}>
              MarketForge listing ID: <span style={{ fontFamily: 'monospace' }}>{item.marketforge_listing_id}</span>
            </div>
          )}
          {item.marketforge_pushed_at && (
            <div style={{ fontSize: 11, color: '#166534', marginTop: 2 }}>
              Pushed at: {fmt(item.marketforge_pushed_at)}
            </div>
          )}
        </div>
      )}

      {(item.marketforge_push_status === 'failed' || item.listing_status === 'failed') && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 10, padding: '12px 14px' }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#dc2626', display: 'flex', alignItems: 'center', gap: 6 }}>
            <AlertTriangle size={15} /> Last publish attempt failed
          </div>
          {item.marketforge_error_message && (
            <div style={{ fontSize: 11, color: '#991b1b', marginTop: 4, fontFamily: 'monospace' }}>
              {item.marketforge_error_message}
            </div>
          )}
        </div>
      )}

      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: 12, fontWeight: 800, color: '#1a1a1a' }}>LISTING DRAFT & HANDOFF PACKET</div>
            <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
              Create a listing draft before exporting. Export packet is for manual handoff or outside listing. It does not publish to eBay.
            </div>
          </div>
          <button
            onClick={createListingDraft}
            disabled={draftState === 'creating'}
            style={{
              padding: '10px 12px', borderRadius: 9, fontSize: 12, fontWeight: 800,
              border: '1px solid #06b6d4', background: draftState === 'creating' ? '#e5e7eb' : '#ecfeff',
              color: draftState === 'creating' ? '#6b7280' : '#155e75',
              cursor: draftState === 'creating' ? 'wait' : 'pointer',
              display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            {draftState === 'creating' ? <><Loader2 size={14} className="animate-spin" /> Creating...</> : <><List size={14} /> Create Listing Draft</>}
          </button>
        </div>

        {draftState === 'error' && draftError && (
          <div style={{ padding: '9px 10px', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 8, fontSize: 12, color: '#991b1b' }}>
            <AlertTriangle size={12} style={{ display: 'inline', marginRight: 4 }} />
            {draftError}
          </div>
        )}

        {draftId ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>
            {[
              ['Draft created', `#${draftId}`],
              ['Draft status', draftStatus || 'draft'],
              ['Listing title', draftTitle || '—'],
              ['Suggested price', draftPrice ? `$${draftPrice}` : '—'],
            ].map(([label, value]) => (
              <div key={label} style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: 8, padding: 10 }}>
                <div style={{ fontSize: 10, color: '#6b7280', textTransform: 'uppercase', fontWeight: 700 }}>{label}</div>
                <div style={{ fontSize: 12, color: '#111827', fontWeight: 700, marginTop: 3, wordBreak: 'break-word' }}>{value}</div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: '9px 10px', background: '#fef9ec', border: '1px solid #fde68a', borderRadius: 8, fontSize: 12, color: '#92400e' }}>
            No listing packet draft exists yet. Create the draft after reviewing title, condition, and pricing.
          </div>
        )}

        {draftId && (
          <>
            <div>
              <div style={{ fontSize: 11, fontWeight: 800, color: '#666', marginBottom: 5 }}>MISSING FIELDS CHECKLIST</div>
              {draftMissingFields.length > 0 ? (
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {draftMissingFields.map((field: string) => (
                    <span key={field} style={{ fontSize: 11, color: '#92400e', background: '#fef3c7', border: '1px solid #fde68a', borderRadius: 999, padding: '4px 8px' }}>
                      {field}
                    </span>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: 12, color: '#166534' }}><CheckCircle size={12} style={{ display: 'inline', marginRight: 4 }} />No missing fields reported.</div>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 8 }}>
              <a href={`${AG_API}/${archiveId}/listing-packet.pdf`} target="_blank" rel="noreferrer"
                style={{ padding: '10px 12px', borderRadius: 9, fontSize: 12, fontWeight: 800, border: '1px solid #d1d5db', background: '#fff', color: '#374151', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, textDecoration: 'none' }}>
                <Download size={14} /> Export Listing Packet PDF
              </a>
              <a href={`${AG_API}/${archiveId}/listing-packet.pdf?include_images=true`} target="_blank" rel="noreferrer"
                style={{ padding: '10px 12px', borderRadius: 9, fontSize: 12, fontWeight: 800, border: '1px solid #bae6fd', background: '#ecfeff', color: '#155e75', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, textDecoration: 'none' }}>
                <Download size={14} /> Export Listing Packet PDF with Photos
              </a>
              <a href={`${AG_API}/${archiveId}/listing-packet.csv`} target="_blank" rel="noreferrer"
                style={{ padding: '10px 12px', borderRadius: 9, fontSize: 12, fontWeight: 800, border: '1px solid #d1d5db', background: '#fff', color: '#374151', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, textDecoration: 'none' }}>
                <Download size={14} /> Export Listing Packet CSV
              </a>
              <a href={`${AG_API}/${archiveId}/listing-packet.xlsx`} target="_blank" rel="noreferrer"
                style={{ padding: '10px 12px', borderRadius: 9, fontSize: 12, fontWeight: 800, border: '1px solid #d1d5db', background: '#fff', color: '#374151', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, textDecoration: 'none' }}>
                <Download size={14} /> Export Listing Packet XLSX
              </a>
              <a href={`${AG_API}/${archiveId}/listing-packet.xlsx?include_images=true`} target="_blank" rel="noreferrer"
                style={{ padding: '10px 12px', borderRadius: 9, fontSize: 12, fontWeight: 800, border: '1px solid #bae6fd', background: '#ecfeff', color: '#155e75', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, textDecoration: 'none' }}>
                <Download size={14} /> Export Listing Packet XLSX with Photos
              </a>
              <a href={`${AG_API}/${archiveId}/listing-packet.json`} target="_blank" rel="noreferrer"
                style={{ padding: '10px 12px', borderRadius: 9, fontSize: 12, fontWeight: 800, border: '1px solid #d1d5db', background: '#fff', color: '#374151', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, textDecoration: 'none' }}>
                <Download size={14} /> Export Listing Packet JSON
              </a>
            </div>
          </>
        )}

        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button disabled style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#f9fafb', color: '#9ca3af', fontSize: 12, fontWeight: 700, cursor: 'not-allowed' }}>
            Send to RelistApp - coming next
          </button>
          <button disabled style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#f9fafb', color: '#9ca3af', fontSize: 12, fontWeight: 700, cursor: 'not-allowed' }}>
            Create eBay Draft - coming next
          </button>
        </div>
      </div>

      {/* Two-column layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, alignItems: 'start' }}>
        {/* Left: listing details */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 16 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#888', marginBottom: 10 }}>LISTING DETAILS</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              <div>
                <div style={{ fontSize: 11, color: '#888' }}>Title</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>{item.listing_title || '—'}</div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: '#888' }}>Description</div>
                <div style={{ fontSize: 12, color: '#374151', maxHeight: 120, overflowY: 'auto' }}>{item.listing_description || '—'}</div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                {[
                  ['Tier', item.tier || '—'],
                  ['Condition', condLabels[item.condition_score || 3] || '—'],
                  ['Status', item.processed_status || '—'],
                ].map(([k, v]) => (
                  <div key={k}>
                    <div style={{ fontSize: 11, color: '#888' }}>{k}</div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{v}</div>
                  </div>
                ))}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                {[
                  ['Comp Range', item.rough_comp_min && item.rough_comp_max ? `$${item.rough_comp_min}–$${item.rough_comp_max}` : '—'],
                  ['Sale Plan', item.sale_plan || '—'],
                  ['Batch Tag', item.batch_tag || '—'],
                  ['Source Box', item.source_box_code || '—'],
                  ['Dest Box', item.processed_box_code || '—'],
                  ['Archive Location', item.archive_location || '—'],
                ].map(([k, v]) => (
                  <div key={k}>
                    <div style={{ fontSize: 11, color: '#888' }}>{k}</div>
                    <div style={{ fontSize: 12, fontWeight: 500, color: '#374151' }}>{v}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Item specifics */}
          <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#888', marginBottom: 8 }}>ITEM SPECIFICS</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 16px', fontSize: 11 }}>
              {Object.entries({
                Format: 'Magazine',
                Publication: 'LIFE',
                Year: item.issue_date ? item.issue_date.split('-')[0] : '',
                'Issue Date': item.issue_date || '',
                Volume: item.volume || '',
                'Issue Number': item.issue_number || '',
                'Cover Subject': item.cover_subject || '',
                ...item_specifics,
              }).filter(([, v]) => v).map(([k, v]) => (
                <div key={k}><span style={{ color: '#888' }}>{k}: </span><span style={{ fontWeight: 500 }}>{String(v)}</span></div>
              ))}
            </div>
          </div>
        </div>

	        {/* Right: photos preview */}
	        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
	          <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
	            <div style={{ fontSize: 12, fontWeight: 700, color: '#888', marginBottom: 10 }}>REFERENCE COVER</div>
	            {item.reference_cover_url || refIssue?.reference_cover_url ? (
	              <img
	                src={item.reference_cover_url || refIssue?.reference_cover_url}
	                alt="Selected LIFE reference cover"
	                style={{ width: '100%', maxHeight: 220, objectFit: 'contain', borderRadius: 8, border: '1px solid #e5e2dc', background: '#f9f8f6' }}
	              />
	            ) : (
	              <div style={{ height: 120, background: '#f5f3ef', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999', fontSize: 12 }}>
	                no cover image available
	              </div>
	            )}
	            <div style={{ marginTop: 8, fontSize: 10, color: '#888' }}>
	              Reference-only. MarketForge uses the actual listing photos below.
	            </div>
	          </div>
	          <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#888', marginBottom: 10 }}>ACTUAL LISTING PHOTOS ({photos.length})</div>
            {photos.length === 0 ? (
              <div style={{ height: 100, background: '#f9f8f6', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ccc', fontSize: 12, border: '1.5px dashed #e5e2dc' }}>
                No photos uploaded
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                {photos.map(p => (
                  <img key={p.id} src={`${AG_API}/photo/${p.id}`} alt={p.role}
                    style={{ width: '100%', aspectRatio: '4/3', objectFit: 'cover', borderRadius: 6, border: '1px solid #e5e2dc' }} />
                ))}
              </div>
            )}
            <div style={{ marginTop: 8, fontSize: 10, color: '#aaa' }}>
              These are the photos that will be pushed to MarketForge. Reference cover images are not included.
            </div>
          </div>

          {/* Publish actions */}
          <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 16 }}>
	            <div style={{ fontSize: 12, fontWeight: 700, color: '#888', marginBottom: 10 }}>MARKETFORGE PUBLISH STATUS</div>
            <a
              href={`${AG_API}/${archiveId}/export.pdf`}
              target="_blank"
              rel="noreferrer"
              style={{
                marginBottom: 10, width: '100%', padding: '10px 12px', borderRadius: 9, fontSize: 12, fontWeight: 800,
                border: '1px solid #d1d5db', background: '#fff', color: '#374151',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, textDecoration: 'none',
              }}
            >
              <Download size={14} /> Export Item PDF
            </a>
	            {publishStatus && (
	              <div style={{
	                marginBottom: 10, padding: '9px 10px', borderRadius: 8, fontSize: 11,
	                background: publishStatus.publish_available ? '#f0fdf4' : '#fef9ec',
	                border: `1px solid ${publishStatus.publish_available ? '#86efac' : '#fde68a'}`,
	                color: publishStatus.publish_available ? '#166534' : '#92400e',
	              }}>
	                {publishStatus.publish_available
	                  ? `Live target: ${publishStatus.target}`
	                  : `Publish unavailable: ${publishStatus.reason}`}
	              </div>
	            )}
            <div style={{ marginBottom: 10, display: 'grid', gap: 8 }}>
              <div>
                <div style={{ fontSize: 11, color: '#666', marginBottom: 3 }}>MarketForge Category ID (UUID)</div>
                <input
                  value={marketforgeCategoryId}
                  onChange={e => setMarketforgeCategoryId(e.target.value)}
                  placeholder="e.g. 00000000-0000-0000-0000-000000000000"
                  style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12 }}
                />
              </div>
              <div>
                <div style={{ fontSize: 11, color: '#666', marginBottom: 3 }}>Ships From ZIP (5 digits)</div>
                <input
                  value={marketforgeShipsFromZip}
                  onChange={e => setMarketforgeShipsFromZip(e.target.value)}
                  placeholder="e.g. 98101"
                  style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12 }}
                />
              </div>
              <button
                onClick={savePublishFields}
                disabled={savingPublishFields}
                style={{
                  padding: '8px 10px', borderRadius: 8, fontSize: 12, fontWeight: 600,
                  border: '1px solid #06b6d4', background: '#ecfeff', color: '#155e75',
                  cursor: savingPublishFields ? 'wait' : 'pointer',
                }}
              >
                {savingPublishFields ? 'Saving…' : 'Save Publish Fields'}
              </button>
            </div>
	            <button
	              onClick={handlePublish}
	              disabled={savingPublishFields || pushState === 'pushing' || validationErrors.length > 0}
              style={{
                width: '100%', padding: '12px', borderRadius: 10, fontSize: 14, fontWeight: 700,
                background: validationErrors.length > 0 ? '#e5e7eb' : '#16a34a',
                color: validationErrors.length > 0 ? '#9ca3af' : '#fff',
                border: 'none', cursor: validationErrors.length > 0 || savingPublishFields || pushState === 'pushing' ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              }}
            >
              {pushState === 'pushing' ? (
                <><Loader2 size={16} className="animate-spin" /> Pushing to MarketForge...</>
              ) : pushState === 'success' ? (
                <><CheckCircle size={16} /> Published Successfully</>
              ) : pushState === 'error' ? (
                <><AlertTriangle size={16} /> Try Again</>
              ) : (
	                <><Upload size={16} /> {publishStatus?.action_label || 'Publish to MarketForge'}</>
	              )}
	            </button>
            {pushState === 'error' && pushError && (
              <div style={{ marginTop: 8, fontSize: 11, color: '#dc2626', background: '#fef2f2', padding: '8px 10px', borderRadius: 6 }}>
                <AlertTriangle size={11} style={{ display: 'inline', marginRight: 4 }} />
                {pushError}
              </div>
            )}
            {pushState === 'success' && pushResult?.marketforge_listing_id && (
              <div style={{ marginTop: 8, fontSize: 11, color: '#16a34a', background: '#f0fdf4', padding: '8px 10px', borderRadius: 6 }}>
                <CheckCircle size={11} style={{ display: 'inline', marginRight: 4 }} />
                Listing ID: <span style={{ fontFamily: 'monospace' }}>{pushResult.marketforge_listing_id}</span>
              </div>
            )}
            {pushState === 'success' && !pushResult?.marketforge_listing_id && (
              <div style={{ marginTop: 8, fontSize: 11, color: '#16a34a', background: '#f0fdf4', padding: '8px 10px', borderRadius: 6 }}>
                <CheckCircle size={11} style={{ display: 'inline', marginRight: 4 }} />
                Push succeeded — listing ID will appear after MarketForge processes the request.
              </div>
            )}
            <div style={{ marginTop: 8, fontSize: 10, color: '#888' }}>
              Publishing is explicit — this button will not auto-publish.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Section 8: Inventory View ─────────────────────────────────────────────────

type SortKey = 'created_at' | 'processed_status' | 'source_box_code' | 'processed_box_code' | 'tier' | 'display_title' | 'issue_date';

function InventorySection() {
  const [items, setItems] = useState<ArchiveItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<any>(null);
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterTier, setFilterTier] = useState('all');
  const [filterSourceBox, setFilterSourceBox] = useState('all');
  const [filterProcessedBox, setFilterProcessedBox] = useState('all');
  const [filterListingStatus, setFilterListingStatus] = useState('all');
  const [hideTestRecords, setHideTestRecords] = useState(true);
  const [showNeedsReviewOnly, setShowNeedsReviewOnly] = useState(false);
  const [showNonLife, setShowNonLife] = useState(true);
  const [showAdReadyOnly, setShowAdReadyOnly] = useState(false);
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('created_at');
  const [sortAsc, setSortAsc] = useState(false);
  const [reboxItemId, setReboxItemId] = useState<number | null>(null);
  const [reboxBox, setReboxBox] = useState('');
  const [reboxLocation, setReboxLocation] = useState('');
  const [reboxing, setReboxing] = useState(false);
  const [reboxError, setReboxError] = useState('');
  const [photoDrawer, setPhotoDrawer] = useState<{ item: ArchiveItem; photos: any } | null>(null);
  const [photoLoading, setPhotoLoading] = useState(false);
  const [detailDrawer, setDetailDrawer] = useState<any | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [invRes, statsRes] = await Promise.all([
        fetch(`${AG_API}/archives?limit=200`),
        fetch(`${AG_API}/stats`),
      ]);
      const inv = await invRes.json();
      const st = await statsRes.json();
      setItems(inv.items || []);
      setStats({ ...st, inventory_counters: inv.counters || st.inventory_counters });
    } catch { /* */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  // Unique box codes for filter dropdowns
  const sourceBoxes = [...new Set(items.map(i => i.source_box_code).filter(Boolean))].sort();
  const processedBoxes = [...new Set(items.map(i => i.processed_box_code).filter(Boolean))].sort();

  const filtered = items.filter(item => {
    if (filterStatus !== 'all' && item.processed_status !== filterStatus) return false;
    if (filterTier !== 'all' && item.tier !== filterTier) return false;
    if (filterSourceBox !== 'all' && item.source_box_code !== filterSourceBox) return false;
    if (filterProcessedBox !== 'all' && item.processed_box_code !== filterProcessedBox) return false;
    if (filterListingStatus !== 'all' && (item.listing_status || 'none') !== filterListingStatus) return false;
    if (hideTestRecords && item.is_test_record) return false;
    if (!showNonLife && item.issue_info_status === 'completed' && !item.is_life_magazine) return false;
    if (showNeedsReviewOnly && !item.needs_review) return false;
    if (showAdReadyOnly && !item.ad_opportunity_ready) return false;
    const q = search.toLowerCase();
    const haystack = [item.display_title, item.short_description, item.cover_subject, item.issue_date, item.source_box_code, item.processed_box_code, item.listing_status, item.status_badges?.join(' ')].join(' ').toLowerCase();
    if (q && !haystack.includes(q)) return false;
    return true;
  });

  const sorted = [...filtered].sort((a, b) => {
    const aVal = (a as any)[sortKey] ?? '';
    const bVal = (b as any)[sortKey] ?? '';
    const cmp = String(aVal).localeCompare(String(bVal), undefined, { numeric: true });
    return sortAsc ? cmp : -cmp;
  });

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(a => !a);
    else { setSortKey(key); setSortAsc(false); }
  };

  const SortIcon = ({ k }: { k: SortKey }) => sortKey === k ? (sortAsc ? ' ↑' : ' ↓') : '';

  const openPhotos = async (item: ArchiveItem) => {
    setPhotoLoading(true);
    try {
      const res = await fetch(`${AG_API}/${item.id}/photos`);
      const out = await res.json();
      setPhotoDrawer({ item, photos: out.photos || {} });
    } catch {
      setPhotoDrawer({ item, photos: {} });
    } finally {
      setPhotoLoading(false);
    }
  };

  const openDetail = async (item: ArchiveItem) => {
    setDetailLoading(true);
    try {
      const res = await fetch(`${AG_API}/${item.id}/detail`);
      if (res.ok) {
        const data = await res.json();
        setDetailDrawer({ item, detail: data });
      }
    } catch {
      // non-critical
    } finally {
      setDetailLoading(false);
    }
  };

  const refreshOpenDetail = async () => {
    await load();
    const archiveId = detailDrawer?.item?.id || detailDrawer?.detail?.archive?.archive_id;
    if (!archiveId) return;
    try {
      const res = await fetch(`${AG_API}/${archiveId}/detail`);
      if (res.ok) {
        const data = await res.json();
        setDetailDrawer((prev: any) => prev ? { ...prev, detail: data, item: { ...prev.item, ...(data.archive || {}) } } : prev);
      }
    } catch {
      // non-critical refresh failure; keep current drawer open
    }
  };

  const handleRebox = async (itemId: number) => {
    if (!reboxBox.trim()) { setReboxError('Box code required'); return; }
    setReboxing(true);
    setReboxError('');
    try {
      const res = await fetch(`${AG_API}/archives/${itemId}/rebox`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ processed_box_code: reboxBox.trim(), archive_location: reboxLocation.trim() }),
      });
      if (res.ok) {
        setReboxItemId(null);
        setReboxBox('');
        setReboxLocation('');
        await load();
      } else {
        const err = await res.json().catch(() => ({ detail: 'Rebox failed' }));
        setReboxError(err.detail || 'Rebox failed');
      }
    } catch {
      setReboxError('Network error');
    }
    setReboxing(false);
  };

  const COLS: { key: keyof ArchiveItem | 'photo_count' | 'archive_location' | 'thumbnail_url' | 'status_badges'; label: string; width: number; sortable?: boolean }[] = [
    { key: 'id', label: 'ID', width: 45 },
    { key: 'thumbnail_url', label: 'Photo', width: 72 },
    { key: 'display_title', label: 'Title', width: 250, sortable: true },
    { key: 'issue_date', label: 'Date', width: 88 },
    { key: 'status_badges', label: 'Badges', width: 170 },
    { key: 'tier', label: 'Tier', width: 48, sortable: true },
    { key: 'photo_count', label: 'Photos', width: 62 },
    { key: 'ad_page_photo_count', label: 'Ad Pg', width: 58 },
    { key: 'source_box_code', label: 'Source Box', width: 92, sortable: true },
    { key: 'processed_box_code', label: 'Dest Box', width: 92, sortable: true },
    { key: 'archive_location', label: 'Location', width: 100 },
    { key: 'listing_status', label: 'Listing', width: 88 },
    { key: 'condition_score', label: 'Cond.', width: 50 },
    { key: 'final_price', label: 'Final Price', width: 80 },
    { key: 'rough_comp_min', label: 'Comp Min', width: 72 },
    { key: 'rough_comp_max', label: 'Comp Max', width: 72 },
    { key: 'created_at', label: 'Added', width: 86, sortable: true },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Archive Inventory</h2>
          <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>Physical archive view — source box tracking, status, and reboxing</p>
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <a href={`${AG_API}/inventory/export.csv`} style={{ padding: '7px 12px', background: '#fff', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, color: '#374151', textDecoration: 'none' }}>
            <Download size={12} /> Export Inventory CSV
          </a>
          <a href={`${AG_API}/inventory/export.csv?include_photos=true`} style={{ padding: '7px 12px', background: '#fff', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, color: '#374151', textDecoration: 'none' }}>
            <Download size={12} /> Export Inventory CSV with Photo Links
          </a>
          <a href={`${AG_API}/inventory/export.xlsx`} style={{ padding: '7px 12px', background: '#fff', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, color: '#374151', textDecoration: 'none' }}>
            <Download size={12} /> Export Inventory XLSX
          </a>
          <a href={`${AG_API}/inventory/export.xlsx?include_images=true`} style={{ padding: '7px 12px', background: '#fff', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, color: '#374151', textDecoration: 'none' }}>
            <Download size={12} /> Export Inventory XLSX with Thumbnails
          </a>
          <button onClick={load} style={{ padding: '7px 12px', background: '#fff', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
            <RefreshCw size={12} /> Refresh
          </button>
        </div>
      </div>

      {/* Stats row */}
      {stats && (
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {[
            { label: 'Total', value: stats.inventory_counters?.total_records ?? stats.total_items, color: '#1a1a1a' },
            { label: 'LIFE', value: stats.inventory_counters?.real_life_identified ?? 0, color: '#3b82f6' },
            { label: 'Issue Ready', value: stats.inventory_counters?.issue_info_completed ?? 0, color: '#10b981' },
            { label: 'Ad Ready', value: stats.inventory_counters?.ad_opportunities_ready ?? 0, color: '#06b6d4' },
            { label: 'Drafts', value: stats.inventory_counters?.listing_draft_saved ?? 0, color: '#f59e0b' },
            { label: 'Needs Review', value: stats.inventory_counters?.needs_review ?? 0, color: '#ef4444' },
            { label: 'Test', value: stats.inventory_counters?.test_records ?? 0, color: '#6b7280' },
            { label: 'Non-LIFE', value: stats.inventory_counters?.non_life ?? 0, color: '#9ca3af' },
          ].map(s => (
            <div key={s.label} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: '10px 14px', minWidth: 80, textAlign: 'center' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: s.color }}>{s.value}</div>
              <div style={{ fontSize: 10, color: '#888', marginTop: 2 }}>{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search subject, date, box..."
          style={{ padding: '7px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12, maxWidth: 200 }} />
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
          style={{ padding: '7px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12 }}>
          <option value="all">All Statuses</option>
          {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={filterTier} onChange={e => setFilterTier(e.target.value)}
          style={{ padding: '7px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12 }}>
          <option value="all">All Tiers</option>
          <option value="A">Tier A</option><option value="B">Tier B</option><option value="C">Tier C</option>
        </select>
        {sourceBoxes.length > 0 && (
          <select value={filterSourceBox} onChange={e => setFilterSourceBox(e.target.value)}
            style={{ padding: '7px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12 }}>
            <option value="all">All Source Boxes</option>
            {sourceBoxes.map(b => <option key={b} value={b}>{b}</option>)}
          </select>
        )}
        {processedBoxes.length > 0 && (
          <select value={filterProcessedBox} onChange={e => setFilterProcessedBox(e.target.value)}
            style={{ padding: '7px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12 }}>
            <option value="all">All Dest Boxes</option>
            {processedBoxes.map(b => <option key={b} value={b}>{b}</option>)}
          </select>
        )}
        <select value={filterListingStatus} onChange={e => setFilterListingStatus(e.target.value)}
          style={{ padding: '7px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12 }}>
          <option value="all">All Listing States</option>
          <option value="none">No Listing</option>
          <option value="draft">Draft Saved</option>
          <option value="ready">Ready to Publish</option>
          <option value="pushed">Published</option>
          <option value="failed">Publish Failed</option>
        </select>
        <label style={{ fontSize: 11, display: 'flex', alignItems: 'center', gap: 4 }}><input type="checkbox" checked={hideTestRecords} onChange={e => setHideTestRecords(e.target.checked)} /> Hide test records</label>
        <label style={{ fontSize: 11, display: 'flex', alignItems: 'center', gap: 4 }}><input type="checkbox" checked={showNeedsReviewOnly} onChange={e => setShowNeedsReviewOnly(e.target.checked)} /> Show needs review</label>
        <label style={{ fontSize: 11, display: 'flex', alignItems: 'center', gap: 4 }}><input type="checkbox" checked={showNonLife} onChange={e => setShowNonLife(e.target.checked)} /> Show non-LIFE</label>
        <label style={{ fontSize: 11, display: 'flex', alignItems: 'center', gap: 4 }}><input type="checkbox" checked={showAdReadyOnly} onChange={e => setShowAdReadyOnly(e.target.checked)} /> Show ad ready</label>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: '#888' }}>
          Showing {sorted.length} archived items
        </span>
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}><Loader2 size={20} className="animate-spin" style={{ color: '#06b6d4' }} /></div>
      ) : sorted.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999', background: '#fff', borderRadius: 10, border: '1px solid #e5e2dc' }}>
          No items found. Complete the intake wizard to add your first archive item.
        </div>
      ) : (
        <div style={{ overflowX: 'auto', background: '#fff', borderRadius: 12, border: '1px solid #e5e2dc' }}>
          <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse', minWidth: 1050 }}>
            <thead>
              <tr style={{ background: '#f5f3ef', borderBottom: '2px solid #e5e2dc' }}>
                {COLS.map(col => (
                  <th key={col.key}
                    style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 700, color: '#888', whiteSpace: 'nowrap', cursor: col.sortable ? 'pointer' : 'default' }}
                    onClick={() => col.sortable && handleSort(col.key as SortKey)}
                  >
                    {col.label}{col.sortable ? <SortIcon k={col.key as SortKey} /> : ''}
                  </th>
                ))}
                <th style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 700, color: '#888', whiteSpace: 'nowrap' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map(item => (
                <React.Fragment key={item.id}>
                  <tr style={{ borderBottom: '1px solid #f0ede6' }}
                    onMouseEnter={e => e.currentTarget.style.background = '#faf9f7'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    {COLS.map(col => {
                      const val = (item as any)[col.key];
                      let display: React.ReactNode = (val == null || val === '') ? '—' : val;
                      if (col.key === 'tier' && val) {
                        display = <span style={{ padding: '2px 7px', borderRadius: 6, fontWeight: 700, fontSize: 10, background: (TIER_COLORS[val] || '#666') + '20', color: TIER_COLORS[val] || '#666' }}>{val}</span>;
                      }
                      if (col.key === 'processed_status' && val) {
                        display = <span style={{ padding: '2px 7px', borderRadius: 6, fontWeight: 600, fontSize: 10, background: (STATUS_COLORS[val] || '#666') + '20', color: STATUS_COLORS[val] || '#666' }}>{val}</span>;
                      }
                      if (col.key === 'photo_count') {
                        const count = Number(val) || 0;
                        display = <span style={{ padding: '2px 7px', borderRadius: 6, fontWeight: 600, fontSize: 10, background: count > 0 ? '#d1fae5' : '#f3f4f6', color: count > 0 ? '#065f46' : '#9ca3af' }}>{count > 0 ? count : '—'}</span>;
                      }
                      if (col.key === 'thumbnail_url') {
                        display = item.thumbnail_url ? (
                          <button onClick={() => openDetail(item)} title="Open Record" style={{ border: 'none', background: 'transparent', padding: 0, cursor: 'pointer' }}>
                            <img src={`${API}${item.thumbnail_url.replace('/api/v1', '')}`} alt={item.display_title || 'front cover'} style={{ width: 54, height: 72, objectFit: 'cover', borderRadius: 6, border: '1px solid #e5e2dc', background: '#f3f4f6' }} />
                          </button>
                        ) : <button onClick={() => openDetail(item)} title="Open Record" style={{ border: '1px dashed #d1d5db', background: '#f9fafb', borderRadius: 6, width: 54, height: 40, fontSize: 10, color: '#9ca3af', cursor: 'pointer' }}>No photo</button>;
                      }
                      if (col.key === 'display_title') {
                        display = (
                          <div style={{ maxWidth: 250, whiteSpace: 'normal', lineHeight: 1.25 }}>
                            <button onClick={() => openDetail(item)} title="Open Record" style={{ border: 'none', background: 'transparent', padding: 0, cursor: 'pointer', textAlign: 'left', fontWeight: 700, color: '#06b6d4', textDecoration: 'underline', textDecorationStyle: 'dotted' }}>
                              {item.display_title || item.cover_subject || '—'}
                            </button>
                            <div style={{ fontSize: 10, color: '#888', fontWeight: 400 }}>{item.short_description || ''}</div>
                          </div>
                        );
                      }
                      if (col.key === 'status_badges') {
                        display = <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, maxWidth: 170 }}>
                          {(item.status_badges || []).slice(0, 5).map(badge => (
                            <span key={badge} style={{ padding: '2px 6px', borderRadius: 6, fontSize: 9, fontWeight: 800, background: badge === 'NEEDS REVIEW' ? '#fee2e2' : badge === 'AD READY' ? '#cffafe' : badge === 'TEST' ? '#f3f4f6' : '#e0f2fe', color: badge === 'NEEDS REVIEW' ? '#991b1b' : badge === 'TEST' ? '#6b7280' : '#075985' }}>{badge}</span>
                          ))}
                        </div>;
                      }
                      if (col.key === 'condition_score') {
                        display = val ? `${val}/5` : '—';
                      }
                      if (col.key === 'rough_comp_min' || col.key === 'rough_comp_max') {
                        display = val ? `$${Number(val).toFixed(0)}` : '—';
                      }
                      if (col.key === 'final_price') {
                        display = val ? <span style={{ fontWeight: 800, color: '#166534' }}>${Number(val).toFixed(2)}</span> : '—';
                      }
                      if (col.key === 'created_at') {
                        display = fmt(val);
                      }
                      if (col.key === 'source_box_code' && val) {
                        display = <span style={{ fontFamily: 'monospace', fontSize: 10, background: '#f5f3ef', padding: '2px 5px', borderRadius: 4 }}>{val}</span>;
                      }
                      if (col.key === 'processed_box_code' && val) {
                        display = <span style={{ fontFamily: 'monospace', fontSize: 10, background: '#ecfeff', padding: '2px 5px', borderRadius: 4, color: '#155e75' }}>{val}</span>;
                      }
                      if (col.key === 'listing_status') {
                        const ls = (val || 'none') as string;
                        const lsColor = PUSH_STATUS_COLORS[ls] || '#9ca3af';
                        const lsLabel = LISTING_STATUS_LABELS[ls] || ls;
                        display = (
                          <span style={{ padding: '2px 7px', borderRadius: 6, fontWeight: 600, fontSize: 10, background: lsColor + '20', color: lsColor }}>
                            {lsLabel}
                          </span>
                        );
                      }
                      return <td key={col.key} style={{ padding: '7px 10px', color: '#1a1a1a' }}>{display}</td>;
                    })}
                    <td style={{ padding: '7px 10px' }}>
                      {reboxItemId === item.id ? (
                        <div style={{ display: 'flex', gap: 4, alignItems: 'center', flexWrap: 'wrap' }}>
                          <input
                            value={reboxBox}
                            onChange={e => setReboxBox(e.target.value)}
                            placeholder="Dest box code"
                            style={{ padding: '3px 6px', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 11, width: 110 }}
                          />
                          <input
                            value={reboxLocation}
                            onChange={e => setReboxLocation(e.target.value)}
                            placeholder="Location"
                            style={{ padding: '3px 6px', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 11, width: 90 }}
                          />
                          <button
                            onClick={() => handleRebox(item.id)}
                            disabled={reboxing}
                            style={{ padding: '3px 7px', background: '#06b6d4', color: '#fff', border: 'none', borderRadius: 6, fontSize: 10, fontWeight: 600, cursor: reboxing ? 'wait' : 'pointer' }}
                          >
                            {reboxing ? '…' : 'Save'}
                          </button>
                          <button
                            onClick={() => { setReboxItemId(null); setReboxError(''); }}
                            style={{ padding: '3px 7px', background: '#fff', color: '#888', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 10, cursor: 'pointer' }}
                          >
                            Cancel
                          </button>
                          {reboxError && <div style={{ width: '100%', fontSize: 10, color: '#dc2626' }}>{reboxError}</div>}
                        </div>
                      ) : (
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          <button
                            onClick={() => openDetail(item)}
                            style={{ padding: '3px 8px', background: '#06b6d4', border: 'none', borderRadius: 6, fontSize: 10, fontWeight: 700, cursor: 'pointer', color: '#fff', display: 'flex', alignItems: 'center', gap: 3 }}
                          >
                            <Archive size={10} /> Open Record
                          </button>
                          <button
                            onClick={() => openPhotos(item)}
                            style={{ padding: '3px 8px', background: '#fff', border: '1px solid #bae6fd', borderRadius: 6, fontSize: 10, fontWeight: 700, cursor: 'pointer', color: '#155e75', display: 'flex', alignItems: 'center', gap: 3 }}
                          >
                            <Eye size={10} /> View Photos
                          </button>
                          {['PHOTOGRAPHED','VALUED','READY_TO_LIST','LISTED','HOLD'].includes(item.processed_status) && (
                            <button
                              onClick={() => { setReboxItemId(item.id); setReboxBox(item.processed_box_code || ''); setReboxLocation(item.archive_location || ''); setReboxError(''); }}
                              style={{ padding: '3px 8px', background: '#f5f3ef', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 10, fontWeight: 600, cursor: 'pointer', color: '#6b7280' }}
                            >
                              Rebox
                            </button>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {photoDrawer && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', zIndex: 50, display: 'flex', justifyContent: 'flex-end' }} onClick={() => setPhotoDrawer(null)}>
          <div style={{ width: 'min(720px, 96vw)', height: '100%', background: '#fff', boxShadow: '-12px 0 30px rgba(0,0,0,0.18)', padding: 18, overflowY: 'auto' }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 18 }}>{photoDrawer.item.display_title || `Archive #${photoDrawer.item.id}`}</h3>
                <div style={{ marginTop: 4, color: '#666', fontSize: 12 }}>
                  Issue info: {photoDrawer.item.issue_info_status || 'not_run'} · Ad opportunity: {photoDrawer.item.ad_opportunity_ready ? 'ready' : 'not ready'}
                </div>
              </div>
              <button onClick={() => setPhotoDrawer(null)} style={{ border: 'none', background: '#f3f4f6', borderRadius: 8, width: 32, height: 32, cursor: 'pointer' }}><X size={16} /></button>
            </div>
            {photoLoading ? <div style={{ padding: 30, color: '#888' }}>Loading photos...</div> : (
              <div style={{ display: 'grid', gap: 16, marginTop: 16 }}>
                <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                  {photoDrawer.item.front_photo_present && <span style={{ padding: '2px 7px', borderRadius: 6, background: '#d1fae5', color: '#065f46', fontSize: 10, fontWeight: 800 }}>Front photo present</span>}
                  {!photoDrawer.photos?.spine?.length && <span style={{ padding: '2px 7px', borderRadius: 6, background: '#fef3c7', color: '#92400e', fontSize: 10, fontWeight: 800 }}>Missing spine</span>}
                  {!photoDrawer.photos?.back?.length && <span style={{ padding: '2px 7px', borderRadius: 6, background: '#fef3c7', color: '#92400e', fontSize: 10, fontWeight: 800 }}>Missing back</span>}
                  {photoDrawer.photos?.defects?.length > 0 && <span style={{ padding: '2px 7px', borderRadius: 6, background: '#fee2e2', color: '#991b1b', fontSize: 10, fontWeight: 800 }}>Has defect photos</span>}
                  {photoDrawer.photos?.ad_pages?.length > 0 && <span style={{ padding: '2px 7px', borderRadius: 6, background: '#cffafe', color: '#155e75', fontSize: 10, fontWeight: 800 }}>Has ad-page photos</span>}
                  {photoDrawer.item.verified_ad_count ? <span style={{ padding: '2px 7px', borderRadius: 6, background: '#dcfce7', color: '#166534', fontSize: 10, fontWeight: 800 }}>{photoDrawer.item.verified_ad_count} verified ads</span> : null}
                </div>
                {(['front','spine','back','defects','label','ad_pages'] as const).map(role => {
                  const group = photoDrawer.photos?.[role] || [];
                  if (!group.length) return null;
                  return (
                    <div key={role}>
                      <div style={{ fontSize: 12, fontWeight: 800, color: '#374151', marginBottom: 8 }}>{role.replace('_', ' ').toUpperCase()}</div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 10 }}>
                        {group.map((p: any) => (
                          <div key={p.photo_id || p.id} style={{ border: '1px solid #e5e2dc', borderRadius: 8, padding: 8, display: 'grid', gap: 7 }}>
                            <img src={`${API}${(p.thumbnail_url || p.photo_url || '').replace('/api/v1', '')}`} alt={p.role} style={{ width: '100%', height: 180, objectFit: 'contain', background: '#f9fafb', borderRadius: 6 }} />
                            <div style={{ fontSize: 10, color: '#666' }}>{p.filename} · {p.file_size || p.file_size_bytes || 0} bytes</div>
                            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                              <a href={`${API}${(p.photo_url || '').replace('/api/v1', '')}`} target="_blank" rel="noreferrer" style={{ fontSize: 11 }}>Open full image</a>
                              <a href={`${API}${(p.photo_url || '').replace('/api/v1', '')}`} download style={{ fontSize: 11 }}>Download image</a>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <button disabled style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid #e5e7eb', background: '#f3f4f6', color: '#9ca3af', fontSize: 12 }}>Add more photos</button>
                  <button onClick={async () => { await fetch(`${AG_API}/identify?archive_id=${photoDrawer.item.id}`, { method: 'POST' }); }} style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid #bae6fd', background: '#ecfeff', color: '#155e75', fontSize: 12, cursor: 'pointer' }}>Re-run AI Identify on front cover</button>
                  <button onClick={async () => { await fetch(`${AG_API}/${photoDrawer.item.id}/ads/analyze`, { method: 'POST' }); }} style={{ padding: '8px 10px', borderRadius: 8, border: '1px solid #e5e2dc', background: '#fff', color: '#374151', fontSize: 12, cursor: 'pointer' }}>Analyze uploaded ad pages</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      {detailDrawer && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', zIndex: 50, display: 'flex', justifyContent: 'flex-end' }} onClick={() => setDetailDrawer(null)}>
          <div style={{ width: 'min(820px, 96vw)', height: '100%', background: '#fff', boxShadow: '-12px 0 30px rgba(0,0,0,0.18)', padding: 18, overflowY: 'auto' }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 14 }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 18 }}>{detailDrawer.item?.display_title || `Archive #${detailDrawer.item?.id}`}</h3>
                <div style={{ marginTop: 4, color: '#666', fontSize: 12 }}>Item Detail — {detailDrawer.detail?.archive?.tier || ''} tier</div>
              </div>
              <button onClick={() => setDetailDrawer(null)} style={{ border: 'none', background: '#f3f4f6', borderRadius: 8, width: 32, height: 32, cursor: 'pointer' }}><X size={16} /></button>
            </div>
            <ItemDetailDrawer detailItem={detailDrawer} onClose={() => setDetailDrawer(null)} onRefresh={refreshOpenDetail} />
          </div>
        </div>
      )}
    </div>
  );
}

// ── Item Detail Drawer ────────────────────────────────────────────────────────

type DetailTab = 'photos' | 'reference' | 'issue_info' | 'condition' | 'ads' | 'pricing' | 'listing' | 'lifecycle';

const ITEM_STATUS_OPTIONS = ['inventory', 'held', 'listed', 'sold', 'broken_for_ads', 'ads_only', 'archived', 'needs_review'];
const MARKETPLACE_STATUS_OPTIONS = ['not_listed', 'draft', 'listed', 'sold', 'cancelled'];
const AD_BREAKOUT_STATUS_OPTIONS = ['none', 'candidate', 'in_progress', 'ads_removed', 'ads_listed', 'complete'];
const LISTING_STATUS_OPTIONS = ['no_listing', 'draft_saved', 'ready_to_list', 'listed', 'sold', 'cancelled', 'needs_review'];
const CONDITION_SCORE_OPTIONS = [
  { value: '', label: 'Unknown' },
  { value: '5', label: '5 — Excellent' },
  { value: '4', label: '4 — Very Good' },
  { value: '3', label: '3 — Good' },
  { value: '2', label: '2 — Fair' },
  { value: '1', label: '1 — Poor' },
];
const COMMON_DEFECTS = ['edge wear', 'spine wear', 'cover crease', 'torn cover', 'detached cover', 'missing pages', 'writing/marking', 'mailing label', 'foxing/spots', 'water damage', 'musty odor', 'brittle pages', 'tape/repair', 'other'];
const ARCHIVE_PATCH_FIELDS = [
  'display_title', 'short_description', 'issue_date', 'cover_subject', 'notes',
  'condition_score', 'is_complete', 'has_address_label', 'defects',
  'rough_comp_min', 'rough_comp_max', 'final_price', 'sale_plan',
  'source_box_code', 'processed_box_code', 'archive_location', 'tier',
  'listing_status', 'listing_title', 'listing_description',
];

const selectStyle: React.CSSProperties = { width: '100%', padding: '6px 8px', border: '1px solid #e5e2dc', borderRadius: 7, fontSize: 11, background: '#fff' };
const inputStyle: React.CSSProperties = { width: '100%', padding: '6px 8px', border: '1px solid #e5e2dc', borderRadius: 7, fontSize: 11 };
const editLabelStyle: React.CSSProperties = { fontSize: 10, color: '#6b7280', marginBottom: 4, fontWeight: 700 };

function toNumberOrNull(value: any) {
  if (value === '' || value === null || value === undefined) return null;
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function appendUniqueText(current: string, next: string) {
  const value = (current || '').trim();
  if (!next.trim()) return value;
  if (value.toLowerCase().includes(next.toLowerCase())) return value;
  return value ? `${value}; ${next}` : next;
}

function ItemDetailDrawer({ detailItem, onClose, onRefresh }: { detailItem: any; onClose: () => void; onRefresh: () => void | Promise<void> }) {
  const [tab, setTab] = useState<DetailTab>('photos');
  const [editing, setEditing] = useState(false);
  const [editData, setEditData] = useState<Record<string, any>>({});
  const [saving, setSaving] = useState(false);
  const [editMsg, setEditMsg] = useState('');
  const [quickAction, setQuickAction] = useState('');
  const [pricingAction, setPricingAction] = useState('');
  const [selectedAction, setSelectedAction] = useState('');
  const [selectedActionTab, setSelectedActionTab] = useState('');
  const [actionPayload, setActionPayload] = useState<Record<string, any>>({});
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');
  const [descriptionStyle, setDescriptionStyle] = useState('concise');
  const [descriptionSuggestion, setDescriptionSuggestion] = useState<any>(null);
  const [candidateUploadId, setCandidateUploadId] = useState<number | null>(null);
  const [photoActionRole, setPhotoActionRole] = useState('front');
  const [lifecycleMsg, setLifecycleMsg] = useState('');
  const [lifecycleOp, setLifecycleOp] = useState(false);
  const d = detailItem?.detail || {};
  const arch = d.archive || {};
  const lc = d.lifecycle || {};
  const listing = d.listing_draft || {};

  const buildInitialEditData = () => ({
    display_title: arch.display_title || '',
    short_description: arch.short_description || '',
    issue_date: arch.issue_date || '',
    cover_subject: arch.cover_subject || arch.confirmed_cover_title || '',
    notes: arch.notes || '',
    condition_score: arch.condition_score || '',
    is_complete: !!arch.complete,
    completeness_status: arch.complete ? 'complete' : 'unknown',
    has_address_label: !!arch.address_label,
    address_label_status: arch.address_label ? 'present' : 'none',
    defects: arch.defects || '',
    rough_comp_min: arch.rough_comp_min || '',
    rough_comp_max: arch.rough_comp_max || '',
    final_price: arch.final_price || '',
    sale_plan: arch.sale_plan || '',
    pricing_notes: d.pricing_summary?.pricing_basis || '',
    source_box_code: arch.source_box || '',
    processed_box_code: arch.dest_box || '',
    archive_location: arch.location || '',
    tier: arch.tier || '',
    listing_status: arch.listing_status || 'no_listing',
    listing_title: listing.title || listing.listing_title || arch.listing_title || '',
    listing_description: listing.description || listing.listing_description || arch.listing_description || '',
    item_status: lc.item_status || 'inventory',
    marketplace_status: lc.marketplace_status || 'not_listed',
    ad_breakout_status: lc.ad_breakout_status || 'none',
    sold_price: lc.sold_price || '',
    sold_date: lc.sold_date || '',
    sold_platform: lc.sold_platform || '',
    disposition_notes: lc.disposition_notes || '',
  });

  const beginEditing = () => {
    setEditData(buildInitialEditData());
    setEditMsg('');
    setLifecycleMsg('');
    setEditing(true);
  };

  const saveEdit = async () => {
    setEditMsg('');
    setSaving(true);
    try {
      const patchPayload: Record<string, any> = {};
      ARCHIVE_PATCH_FIELDS.forEach(field => {
        if (!(field in editData)) return;
        let value = editData[field];
        if (['condition_score', 'rough_comp_min', 'rough_comp_max', 'final_price'].includes(field)) value = toNumberOrNull(value);
        if (field === 'is_complete' || field === 'has_address_label') value = !!value;
        patchPayload[field] = value;
      });
      const res = await fetch(`${AG_API}/${arch.archive_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patchPayload),
      });
      if (!res.ok) {
        const out = await res.json().catch(() => ({}));
        throw new Error(out.detail || `Save failed with HTTP ${res.status}`);
      }

      const lifecyclePayload: Record<string, any> = {
        item_status: editData.item_status || 'inventory',
        marketplace_status: editData.marketplace_status || 'not_listed',
        ad_breakout_status: editData.ad_breakout_status || 'none',
        notes: editData.disposition_notes || '',
      };
      const soldPrice = toNumberOrNull(editData.sold_price);
      if (soldPrice !== null) lifecyclePayload.sold_price = soldPrice;
      if (editData.sold_date) lifecyclePayload.sold_date = editData.sold_date;
      if (editData.sold_platform) lifecyclePayload.sold_platform = editData.sold_platform;
      const lifecycleChanged = ['item_status', 'marketplace_status', 'ad_breakout_status', 'sold_price', 'sold_date', 'sold_platform', 'disposition_notes']
        .some(field => String(editData[field] ?? '') !== String((lc as any)[field] ?? ''));
      if (lifecycleChanged) {
        const lcRes = await fetch(`${AG_API}/${arch.archive_id}/lifecycle`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(lifecyclePayload),
        });
        if (!lcRes.ok) {
          const out = await lcRes.json().catch(() => ({}));
          throw new Error(out.detail || `Lifecycle save failed with HTTP ${lcRes.status}`);
        }
      }
      setEditing(false);
      setEditMsg('Changes saved.');
      await onRefresh();
    } catch (exc: any) {
      setEditMsg(`Error: ${exc?.message || 'Save failed.'}`);
    } finally { setSaving(false); }
  };

  const doLifecycle = async (item_status: string, marketplace_status: string, ad_breakout_status: string, notes: string) => {
    setLifecycleOp(true);
    setLifecycleMsg('');
    try {
      const res = await fetch(`${AG_API}/${arch.archive_id}/lifecycle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_status, marketplace_status, ad_breakout_status, notes }),
      });
      if (res.ok) { setLifecycleMsg('Lifecycle updated.'); await onRefresh(); }
      else { const e = await res.json(); setLifecycleMsg('Error: ' + (e.detail || res.statusText)); }
    } catch { setLifecycleMsg('Network error.'); }
    setLifecycleOp(false);
  };

  const patchArchive = async (payload: Record<string, any>, message = 'Record updated.') => {
    const res = await fetch(`${AG_API}/${arch.archive_id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const out = await res.json().catch(() => ({}));
      throw new Error(out.detail || `Update failed with HTTP ${res.status}`);
    }
    setEditMsg(message);
    await onRefresh();
  };

  const acceptSuggestedFinalPrice = async (price: any, sourceLabel: string) => {
    const value = toNumberOrNull(price);
    if (value === null) {
      setEditMsg('Error: No suggested price is available.');
      return;
    }
    if (!window.confirm(`Use $${value.toFixed(2)} as final price? This is an internal ArchiveForge price only.`)) return;
    try {
      await patchArchive({ final_price: value, sale_plan: arch.sale_plan || `Owner accepted ${sourceLabel} as internal final price.` }, 'Final price updated.');
    } catch (exc: any) {
      setEditMsg(`Error: ${exc?.message || 'Could not update final price.'}`);
    }
  };

  const handlePricingAction = (value: string) => {
    setPricingAction(value);
    if (!value) return;
    const dtmAvg = d.life_master?.dtmagazine_average;
    const roughMin = toNumberOrNull(editData.rough_comp_min ?? arch.rough_comp_min);
    const roughMax = toNumberOrNull(editData.rough_comp_max ?? arch.rough_comp_max);
    const manualComp = (d.comps || []).find((c: any) => ['sold_comp', 'manual_reference', 'dealer_asking', 'active_listing'].includes(c.result_type) && (c.price || c.total_price));
    const dealer = d.dealer_reference?.asking_price;
    let nextPrice: number | null = null;
    let note = '';
    if (value === 'rough') nextPrice = roughMin !== null && roughMax !== null ? Number(((roughMin + roughMax) / 2).toFixed(2)) : roughMin ?? roughMax;
    if (value === 'dtm') nextPrice = toNumberOrNull(dtmAvg);
    if (value === 'manual_comp') nextPrice = toNumberOrNull(manualComp?.total_price ?? manualComp?.price);
    if (value === 'dealer') nextPrice = toNumberOrNull(dealer);
    if (value === 'needs_comps') {
      setEditData(ed => ({ ...ed, sale_plan: 'Needs more comps before final pricing.' }));
      return;
    }
    if (value === 'clear') {
      setEditData(ed => ({ ...ed, final_price: '' }));
      return;
    }
    if (value === 'manual' || value === 'guide_only') return;
    if (nextPrice === null) {
      setEditMsg('Error: No usable price found for that source.');
      return;
    }
    if (!window.confirm(`Use $${nextPrice.toFixed(2)} as final price? This is an internal ArchiveForge price only.`)) return;
    if (value === 'dtm') note = 'DTM reference guide accepted as temporary internal final price.';
    if (value === 'dealer') note = 'Dealer asking price accepted as internal final price; not sold-comp evidence.';
    if (value === 'manual_comp') note = 'Manual comp accepted as internal final price.';
    if (value === 'rough') note = 'Rough estimate accepted as internal final price.';
    setEditData(ed => ({ ...ed, final_price: nextPrice, pricing_notes: note, sale_plan: ed.sale_plan || note }));
  };

  const updateDefect = (defect: string, checked: boolean) => {
    setEditData(ed => {
      const existing = String(ed.defects || '');
      const parts = existing.split(';').map(part => part.trim()).filter(Boolean);
      const next = checked ? [...parts, defect] : parts.filter(part => part.toLowerCase() !== defect.toLowerCase());
      return { ...ed, defects: Array.from(new Set(next)).join('; ') };
    });
  };

  const applyQuickAction = async (action: string) => {
    setQuickAction('');
    setEditMsg('');
    const confirmInternal = (label: string) => window.confirm(`${label}?\n\nThis only updates ArchiveForge internal status. It does not publish or update marketplaces.`);
    try {
      if (action === 'needs_review' && confirmInternal('Mark this item needs review')) await doLifecycle('needs_review', 'not_listed', 'none', 'Flagged for review');
      if (action === 'held' && confirmInternal('Hold this item intact')) await doLifecycle('held', 'not_listed', 'none', 'Held intact');
      if (action === 'ready_to_list' && confirmInternal('Mark ready to list')) await patchArchive({ listing_status: 'ready_to_list', sale_plan: arch.sale_plan || 'List whole magazine' }, 'Marked ready to list.');
      if (action === 'draft_saved' && confirmInternal('Mark draft saved')) await patchArchive({ listing_status: 'draft_saved' }, 'Draft status saved.');
      if (action === 'listed' && confirmInternal('Mark listed internally')) await doLifecycle('listed', 'listed', 'none', 'Marked listed internally');
      if (action === 'sold' && confirmInternal('Mark sold internally')) {
        const soldPrice = window.prompt('Sold price, or leave blank if unknown:', String(lc.sold_price || ''));
        const soldDate = window.prompt('Sold date:', new Date().toISOString().slice(0, 10)) || new Date().toISOString().slice(0, 10);
        const platform = window.prompt('Sold platform/source:', lc.sold_platform || 'manual') || 'manual';
        await fetch(`${AG_API}/${arch.archive_id}/lifecycle`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ item_status: 'sold', marketplace_status: 'sold', ad_breakout_status: lc.ad_breakout_status || 'none', sold_price: toNumberOrNull(soldPrice), sold_date: soldDate, sold_platform: platform, notes: 'Marked sold internally' }),
        });
        await onRefresh();
      }
      if (action === 'ads_only' && confirmInternal('Use this item for ads only')) await doLifecycle('ads_only', 'not_listed', 'candidate', 'Use for ads only; ads remain unverified until photographed');
      if (action === 'broken_for_ads' && confirmInternal('Mark broken out for ads')) await doLifecycle('broken_for_ads', 'not_listed', 'ads_removed', 'Broken out for ads; verified ad pages still require photos');
      if (action === 'test_record' && confirmInternal('Mark as test record')) await patchArchive({ notes: appendUniqueText(arch.notes || '', 'TEST RECORD - exclude from business counts'), listing_status: 'needs_review' }, 'Marked as test record in notes.');
      if (action === 'archived' && confirmInternal('Mark archived')) await doLifecycle('archived', 'not_listed', 'none', 'Archived internally');
      if (action === 'request_photos' && confirmInternal('Request more photos')) await patchArchive({ notes: appendUniqueText(arch.notes || '', 'Request more photos: spine/back/defects as needed'), listing_status: 'needs_review' }, 'Photo request noted.');
      if (action === 'rerun_issue') {
        await fetch(`${AG_API}/${arch.archive_id}/resolve-issue-info`, { method: 'POST' });
        setEditMsg('Issue resolver started.');
        await onRefresh();
      }
      if (action === 'rerun_ads') {
        await fetch(`${AG_API}/${arch.archive_id}/ad-opportunity-check`, { method: 'POST' });
        setEditMsg('Ad opportunity prep requested.');
        await onRefresh();
      }
      if (action === 'refresh_draft') {
        await fetch(`${AG_API}/${arch.archive_id}/create-listing-draft`, { method: 'POST' });
        setEditMsg('Listing draft created/refreshed.');
        await onRefresh();
      }
      if (action === 'export_pdf' && EXPORT_URLS.pdf_with_images_url) window.open(EXPORT_URLS.pdf_with_images_url, '_blank', 'noopener,noreferrer');
    } catch (exc: any) {
      setEditMsg(`Error: ${exc?.message || 'Quick action failed.'}`);
    }
  };

  const suggestedUpdates = [
    ...(!d.photos?.spine?.length ? ['Request more photos: spine'] : []),
    ...(!d.photos?.back?.length ? ['Request more photos: back cover'] : []),
    ...(d.issue_info?.status === 'completed' && d.issue_info?.ad_opportunity_ready ? ['Photograph top ad candidates'] : []),
    ...(!(d.pricing_summary?.sold_comp_count > 0) ? ['Research comps or add manual comp'] : []),
    ...(!arch.final_price ? ['Set final price manually or accept a clearly labeled temporary reference value'] : []),
    ...(d.dealer_reference ? ['Review dealer asking price; it is not sold-comp evidence'] : []),
    ...((arch.notes || '').toLowerCase().includes('test') ? ['Keep test record excluded from business counts'] : []),
  ];

  const tabActionOptions: Record<string, { value: string; label: string }[]> = {
    photos: [
      { value: 'add_photo', label: 'Add photo' },
      { value: 'replace_front', label: 'Replace front cover with better photo' },
      { value: 'mark_primary', label: 'Mark selected photo as primary' },
      { value: 'remove_photo', label: 'Remove photo from active record' },
      { value: 'rerun_identify', label: 'Re-run AI Identify from front photo' },
      { value: 'export_manifest', label: 'Export photo manifest' },
    ],
    issue_info: [
      { value: 'rerun_issue', label: 'Re-run Issue Resolver' },
      { value: 'sync_master', label: 'Sync to LIFE Master' },
      { value: 'generate_description', label: 'Generate description' },
    ],
    condition: [
      { value: 'condition_excellent', label: 'Mark Excellent' },
      { value: 'condition_very_good', label: 'Mark Very Good' },
      { value: 'condition_good', label: 'Mark Good' },
      { value: 'condition_fair', label: 'Mark Fair' },
      { value: 'condition_poor', label: 'Mark Poor' },
      { value: 'condition_needs_review', label: 'Mark Needs Review' },
      { value: 'condition_vintage_wear', label: 'Apply common vintage wear defaults' },
      { value: 'condition_more_photos', label: 'Request more photos' },
    ],
    ads: [
      { value: 'rerun_ads', label: 'Re-run Ad Opportunity Prep' },
      { value: 'photograph_candidate', label: 'Photograph selected candidate' },
      { value: 'analyze_ads', label: 'Analyze uploaded ad pages' },
      { value: 'candidate_not_found', label: 'Mark candidate not found' },
      { value: 'candidate_ignore', label: 'Ignore candidate' },
      { value: 'research_ad_comps', label: 'Research ad comps' },
    ],
    pricing: [
      { value: 'research_magazine_comps', label: 'Research Magazine Comps' },
      { value: 'calculate_pricing', label: 'Calculate Pricing' },
      { value: 'set_final_price', label: 'Set Final Price Manually' },
      { value: 'use_dtm_price', label: 'Use DTM average as temporary internal price' },
      { value: 'clear_final_price', label: 'Clear Final Price' },
      { value: 'mark_needs_comps', label: 'Mark Needs Comps' },
    ],
    listing: [
      { value: 'refresh_draft', label: 'Create / Refresh Listing Draft' },
      { value: 'generate_listing_description', label: 'Generate listing description' },
      { value: 'short_to_listing', label: 'Use short description as listing description' },
      { value: 'export_pdf', label: 'Export PDF' },
      { value: 'export_pdf_photos', label: 'Export PDF with Photos' },
      { value: 'ready_to_list', label: 'Mark Ready to List' },
      { value: 'draft_saved', label: 'Mark Draft Saved' },
    ],
    lifecycle: [
      { value: 'held', label: 'Hold intact' },
      { value: 'ready_to_list', label: 'Mark ready to list' },
      { value: 'listed', label: 'Mark listed' },
      { value: 'sold', label: 'Mark sold' },
      { value: 'ads_only', label: 'Use for ads only' },
      { value: 'broken_for_ads', label: 'Mark broken out for ads' },
      { value: 'archived', label: 'Mark archived' },
      { value: 'needs_review', label: 'Mark needs review' },
      { value: 'test_record', label: 'Mark test record' },
    ],
  };

  const startTabAction = (action: string, actionTab = tab) => {
    if (!action) return;
    setSelectedAction(action);
    setSelectedActionTab(actionTab);
    setActionPayload({});
    setActionError('');
    setActionSuccess('');
    if (action === 'generate_description' || action === 'generate_listing_description') {
      setDescriptionStyle(action === 'generate_listing_description' ? 'ebay' : 'concise');
    }
  };

  const performContextAction = async () => {
    if (!selectedAction) return;
    setActionLoading(true);
    setActionError('');
    setActionSuccess('');
    try {
      if (selectedAction === 'rerun_identify') await fetch(`${AG_API}/identify?archive_id=${arch.archive_id}`, { method: 'POST' });
      else if (selectedAction === 'rerun_issue') await fetch(`${AG_API}/${arch.archive_id}/resolve-issue-info`, { method: 'POST' });
      else if (selectedAction === 'sync_master') await fetch(`${AG_API}/life-issues/${arch.archive_id}/sync-master`, { method: 'POST' });
      else if (selectedAction === 'rerun_ads') await fetch(`${AG_API}/${arch.archive_id}/ad-opportunity-check`, { method: 'POST' });
      else if (selectedAction === 'analyze_ads') await fetch(`${AG_API}/${arch.archive_id}/ads/analyze`, { method: 'POST' });
      else if (selectedAction === 'research_ad_comps') await fetch(`${AG_API}/${arch.archive_id}/ad-comps/research`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ provider: 'auto' }) });
      else if (selectedAction === 'research_magazine_comps') await fetch(`${AG_API}/${arch.archive_id}/comps/research`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ provider: 'auto' }) });
      else if (selectedAction === 'calculate_pricing') await fetch(`${AG_API}/${arch.archive_id}/pricing/calculate`, { method: 'POST' });
      else if (selectedAction === 'refresh_draft') await fetch(`${AG_API}/${arch.archive_id}/create-listing-draft`, { method: 'POST' });
      else if (selectedAction === 'export_pdf' && EXPORT_URLS.pdf_url) window.open(EXPORT_URLS.pdf_url, '_blank', 'noopener,noreferrer');
      else if (selectedAction === 'export_pdf_photos' && EXPORT_URLS.pdf_with_images_url) window.open(EXPORT_URLS.pdf_with_images_url, '_blank', 'noopener,noreferrer');
      else if (selectedAction === 'export_manifest') window.open(`${AG_API}/${arch.archive_id}/photos`, '_blank', 'noopener,noreferrer');
      else if (selectedAction === 'generate_description' || selectedAction === 'generate_listing_description') {
        const res = await fetch(`${AG_API}/${arch.archive_id}/description/generate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ style: descriptionStyle, include_condition: true, include_ad_notes: true, include_pricing_warning: selectedAction === 'generate_listing_description' }) });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || 'Description generation failed.');
        setDescriptionSuggestion(data);
        setActionSuccess('Description suggestion generated.');
        setActionLoading(false);
        return;
      } else if (selectedAction.startsWith('condition_')) {
        const conditionMap: Record<string, any> = {
          condition_excellent: { condition_score: 5 },
          condition_very_good: { condition_score: 4 },
          condition_good: { condition_score: 3 },
          condition_fair: { condition_score: 2 },
          condition_poor: { condition_score: 1 },
          condition_needs_review: { listing_status: 'needs_review', notes: appendUniqueText(arch.notes || '', 'Needs condition review') },
          condition_vintage_wear: { condition_score: 3, defects: appendUniqueText(arch.defects || '', 'edge wear; spine wear; cover crease'), notes: appendUniqueText(arch.notes || '', 'Typical age wear for vintage magazine') },
          condition_more_photos: { listing_status: 'needs_review', notes: appendUniqueText(arch.notes || '', 'Needs spine/back/defect photos') },
        };
        await patchArchive(conditionMap[selectedAction] || {}, 'Condition updated.');
      } else if (selectedAction === 'set_final_price') {
        const price = toNumberOrNull(window.prompt('Internal final price:', String(arch.final_price || '')));
        if (price === null) throw new Error('Final price required.');
        await patchArchive({ final_price: price }, 'Final price set.');
      } else if (selectedAction === 'use_dtm_price') {
        await patchArchive({ final_price: toNumberOrNull(d.life_master?.dtmagazine_average), sale_plan: arch.sale_plan || 'Owner accepted DTM guide as temporary internal price.' }, 'Final price set from DTM guide.');
      } else if (selectedAction === 'clear_final_price') {
        await patchArchive({ final_price: null }, 'Final price cleared.');
      } else if (selectedAction === 'mark_needs_comps') {
        await patchArchive({ sale_plan: 'Needs more comps before final pricing.' }, 'Marked needs comps.');
      } else if (selectedAction === 'short_to_listing') {
        await patchArchive({ listing_description: arch.short_description || '' }, 'Listing description updated from short description.');
      } else if (selectedAction === 'ready_to_list') {
        await patchArchive({ listing_status: 'ready_to_list' }, 'Marked ready to list.');
      } else if (selectedAction === 'draft_saved') {
        await patchArchive({ listing_status: 'draft_saved' }, 'Marked draft saved.');
      } else if (selectedAction === 'photograph_candidate') {
        setActionSuccess('Use the candidate upload control in the Ad Opportunities tab.');
        setActionLoading(false);
        return;
      } else if (['candidate_not_found', 'candidate_ignore'].includes(selectedAction)) {
        const cid = Number(actionPayload.candidate_id || candidateUploadId || d.ad_opportunities?.[0]?.id || 0);
        if (!cid) throw new Error('Select a candidate first.');
        await fetch(`${AG_API}/${arch.archive_id}/ad-opportunities/${cid}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ verification_status: selectedAction === 'candidate_not_found' ? 'not_found' : 'ignored', suggested_action: selectedAction === 'candidate_not_found' ? 'not_found' : 'ignore', user_notes: 'Updated from item detail drawer.' }) });
      } else if (['held', 'listed', 'sold', 'ads_only', 'broken_for_ads', 'archived', 'needs_review', 'test_record'].includes(selectedAction)) {
        const lifecycleMap: Record<string, [string, string, string, string]> = {
          held: ['held', 'not_listed', 'none', 'Held intact'],
          listed: ['listed', 'listed', 'none', 'Marked listed internally'],
          sold: ['sold', 'sold', 'none', 'Marked sold internally'],
          ads_only: ['ads_only', 'not_listed', 'candidate', 'Use for ads only'],
          broken_for_ads: ['broken_for_ads', 'not_listed', 'ads_removed', 'Broken out for ads'],
          archived: ['archived', 'not_listed', 'none', 'Archived internally'],
          needs_review: ['needs_review', 'not_listed', 'none', 'Needs review'],
          test_record: ['needs_review', 'not_listed', 'none', 'Marked test record'],
        };
        const [itemStatus, marketplaceStatus, adBreakoutStatus, notes] = lifecycleMap[selectedAction];
        await fetch(`${AG_API}/${arch.archive_id}/lifecycle`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ item_status: itemStatus, marketplace_status: marketplaceStatus, ad_breakout_status: adBreakoutStatus, notes }) });
        if (selectedAction === 'test_record') await patchArchive({ notes: appendUniqueText(arch.notes || '', 'TEST RECORD - exclude from business counts') }, 'Marked test record.');
      }
      setActionSuccess('Action completed.');
      setSelectedAction('');
      await onRefresh();
    } catch (exc: any) {
      setActionError(exc?.message || 'Action failed.');
    } finally {
      setActionLoading(false);
    }
  };

  const TABS: { key: DetailTab; label: string }[] = [
    { key: 'photos', label: 'Photos' },
    { key: 'reference', label: 'Reference' },
    { key: 'issue_info', label: 'Issue Info' },
    { key: 'condition', label: 'Condition' },
    { key: 'ads', label: 'Ad Opportunities' },
    { key: 'pricing', label: 'Pricing' },
    { key: 'listing', label: 'Listing' },
    { key: 'lifecycle', label: 'Lifecycle' },
  ];

  const EXPORT_URLS = d.exports || {};

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 60, display: 'flex', justifyContent: 'center', alignItems: 'center' }} onClick={onClose}>
      <div style={{ width: 'min(1100px, 96vw)', height: '92vh', background: '#fff', borderRadius: 16, boxShadow: '0 25px 60px rgba(0,0,0,0.25)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #e5e2dc', display: 'flex', gap: 14, alignItems: 'center', flexShrink: 0, background: '#fafaf8' }}>
          {d.photos?.front?.[0]?.thumbnail_url && (
            <img src={`${API}${d.photos.front[0].thumbnail_url.replace('/api/v1', '')}`} alt="cover" style={{ width: 52, height: 68, objectFit: 'cover', borderRadius: 6, border: '1px solid #e5e2dc', background: '#f3f4f6', flexShrink: 0 }} />
          )}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 700, fontSize: 16, color: '#1a1a1a', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {arch.display_title || arch.confirmed_cover_title || arch.cover_subject || `Archive #${arch.archive_id}`}
            </div>
            <div style={{ fontSize: 11, color: '#888', marginTop: 2 }}>
              #{arch.archive_id} &nbsp;·&nbsp; {arch.issue_date || '—'} &nbsp;·&nbsp; Tier {arch.tier || '—'} &nbsp;·&nbsp; {arch.status || '—'} &nbsp;·&nbsp; Final Price: {arch.final_price ? `$${Number(arch.final_price).toFixed(2)}` : '—'}
            </div>
            <div style={{ display: 'flex', gap: 5, marginTop: 5, flexWrap: 'wrap' }}>
              {arch.complete && <span style={{ padding: '1px 6px', borderRadius: 4, fontSize: 9, background: '#d1fae5', color: '#065f46', fontWeight: 700 }}>Complete</span>}
              {arch.address_label && <span style={{ padding: '1px 6px', borderRadius: 4, fontSize: 9, background: '#dbeafe', color: '#1e40af', fontWeight: 700 }}>Labeled</span>}
              {arch.tier && <span style={{ padding: '1px 6px', borderRadius: 4, fontSize: 9, background: '#fef3c7', color: '#92400e', fontWeight: 700 }}>Tier {arch.tier}</span>}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end', flexShrink: 0 }}>
            {EXPORT_URLS.pdf_url && (
              <a href={EXPORT_URLS.pdf_url} target="_blank" rel="noreferrer" style={{ padding: '6px 10px', background: '#fff', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 11, fontWeight: 600, color: '#374151', cursor: 'pointer', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}>
                <Download size={11} /> Export PDF
              </a>
            )}
            {EXPORT_URLS.pdf_with_images_url && (
              <a href={EXPORT_URLS.pdf_with_images_url} target="_blank" rel="noreferrer" style={{ padding: '6px 10px', background: '#fff', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 11, fontWeight: 600, color: '#374151', cursor: 'pointer', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}>
                <Download size={11} /> PDF+Photos
              </a>
            )}
            <select value={quickAction} onChange={e => { const action = e.target.value; setQuickAction(action); if (action) applyQuickAction(action); }} style={{ padding: '6px 9px', background: '#fff', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 11, fontWeight: 700, color: '#374151', cursor: 'pointer' }} aria-label="Quick Update">
              <option value="">Quick Update</option>
              <option value="needs_review">Mark Needs Review</option>
              <option value="held">Mark Held / Keep Intact</option>
              <option value="ready_to_list">Mark Ready to List</option>
              <option value="draft_saved">Mark Draft Saved</option>
              <option value="listed">Mark Listed</option>
              <option value="sold">Mark Sold</option>
              <option value="ads_only">Mark Use for Ads Only</option>
              <option value="broken_for_ads">Mark Broken Out for Ads</option>
              <option value="test_record">Mark Test Record</option>
              <option value="archived">Mark Archived</option>
              <option value="request_photos">Request More Photos</option>
              <option value="rerun_issue">Re-run Issue Resolver</option>
              <option value="rerun_ads">Re-run Ad Opportunity Prep</option>
              <option value="refresh_draft">Create / Refresh Listing Draft</option>
              <option value="export_pdf">Export PDF with Photos</option>
            </select>
            <button onClick={() => editing ? setEditing(false) : beginEditing()} style={{ padding: '6px 10px', background: editing ? '#06b6d4' : '#fff', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 11, fontWeight: 600, color: editing ? '#fff' : '#374151', cursor: 'pointer' }}>
              {editing ? 'Editing...' : 'Edit Record'}
            </button>
            <button onClick={onClose} style={{ border: 'none', background: '#f3f4f6', borderRadius: 8, width: 32, height: 32, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><X size={16} /></button>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: 2, padding: '8px 16px 0', borderBottom: '1px solid #e5e2dc', flexShrink: 0, overflowX: 'auto', background: '#fafaf8' }}>
          {TABS.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)} style={{ padding: '5px 12px', borderRadius: '8px 8px 0 0', border: 'none', borderBottom: tab === t.key ? '2px solid #06b6d4' : '2px solid transparent', background: tab === t.key ? '#fff' : 'transparent', color: tab === t.key ? '#06b6d4' : '#888', fontSize: 12, fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap' }}>
              {t.label}
            </button>
          ))}
        </div>

        {editMsg && (
          <div style={{ margin: '10px 20px 0', padding: '8px 10px', borderRadius: 8, fontSize: 11, background: editMsg.startsWith('Error') ? '#fee2e2' : '#d1fae5', color: editMsg.startsWith('Error') ? '#991b1b' : '#065f46', flexShrink: 0 }}>
            {editMsg}
          </div>
        )}

        <div style={{ margin: '10px 20px 0', display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', flexShrink: 0 }}>
          <select value="" onChange={e => startTabAction(e.target.value, tab)} style={{ padding: '7px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 11, fontWeight: 800, color: '#374151', background: '#fff' }}>
            <option value="">{TABS.find(t => t.key === tab)?.label || 'Tab'} Actions</option>
            {(tabActionOptions[tab] || []).map(action => <option key={action.value} value={action.value}>{action.label}</option>)}
          </select>
          {actionSuccess && <span style={{ fontSize: 11, color: '#166534', background: '#dcfce7', borderRadius: 999, padding: '4px 8px' }}>{actionSuccess}</span>}
          {actionError && <span style={{ fontSize: 11, color: '#991b1b', background: '#fee2e2', borderRadius: 999, padding: '4px 8px' }}>{actionError}</span>}
        </div>

        {selectedAction && (
          <div style={{ margin: '10px 20px 0', border: '1px solid #fbbf24', background: '#fffbeb', borderRadius: 10, padding: 12, display: 'grid', gap: 10, flexShrink: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start' }}>
              <div>
                <div style={{ fontSize: 12, fontWeight: 900, color: '#92400e' }}>Perform Action: {selectedAction.replace(/_/g, ' ')}</div>
                <div style={{ fontSize: 11, color: '#92400e', marginTop: 2 }}>This updates ArchiveForge internal records only. It does not publish or update marketplaces.</div>
              </div>
              <button onClick={() => { setSelectedAction(''); setActionPayload({}); setActionError(''); }} style={{ border: '1px solid #fcd34d', background: '#fff', color: '#92400e', borderRadius: 8, padding: '5px 9px', fontSize: 11, cursor: 'pointer' }}>Cancel</button>
            </div>
            {(selectedAction === 'generate_description' || selectedAction === 'generate_listing_description') && (
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                <select value={descriptionStyle} onChange={e => setDescriptionStyle(e.target.value)} style={selectStyle}>
                  <option value="concise">concise</option>
                  <option value="ebay">eBay listing</option>
                  <option value="collector">collector catalog</option>
                  <option value="condition">condition-focused</option>
                  <option value="ad_opportunity">ad-opportunity-focused</option>
                  <option value="premium">premium sales copy</option>
                </select>
              </div>
            )}
            {['candidate_not_found', 'candidate_ignore', 'photograph_candidate'].includes(selectedAction) && (
              <select value={actionPayload.candidate_id || ''} onChange={e => { setActionPayload(p => ({ ...p, candidate_id: e.target.value })); setCandidateUploadId(e.target.value ? Number(e.target.value) : null); }} style={selectStyle}>
                <option value="">Select ad candidate</option>
                {(d.ad_opportunities || []).map((candidate: any) => <option key={candidate.id} value={candidate.id}>{candidate.brand || candidate.category || candidate.product || `Candidate #${candidate.id}`}</option>)}
              </select>
            )}
            {['add_photo', 'replace_front', 'photograph_candidate'].includes(selectedAction) && (
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                <select value={selectedAction === 'photograph_candidate' ? 'ad_page' : photoActionRole} disabled={selectedAction === 'photograph_candidate'} onChange={e => setPhotoActionRole(e.target.value)} style={selectStyle}>
                  <option value="front">front cover</option><option value="spine">spine</option><option value="back">back cover</option><option value="defect">defect</option><option value="label">mailing label</option><option value="ad_page">ad page</option>
                </select>
                <label style={{ padding: '7px 10px', borderRadius: 8, border: '1px solid #06b6d4', background: '#ecfeff', color: '#155e75', fontSize: 11, fontWeight: 800, cursor: 'pointer' }}>
                  Upload / Take Photo
                  <input type="file" accept="image/*" capture="environment" style={{ display: 'none' }} onChange={async e => {
                    const file = e.target.files?.[0];
                    e.currentTarget.value = '';
                    if (!file) return;
                    const form = new FormData();
                    form.append('file', file);
                    if (photoActionRole === 'ad_page' || selectedAction === 'photograph_candidate') {
                      if (candidateUploadId) form.append('candidate_id', String(candidateUploadId));
                      await fetch(`${AG_API}/${arch.archive_id}/ad-pages/upload`, { method: 'POST', body: form });
                    } else {
                      form.append('role', selectedAction === 'replace_front' ? 'front' : photoActionRole);
                      await fetch(`${AG_API}/uploads/${arch.archive_id}`, { method: 'POST', body: form });
                    }
                    setActionSuccess(selectedAction === 'replace_front' ? 'Previous photo preserved; new photo marked primary.' : 'Photo uploaded.');
                    await onRefresh();
                  }} />
                </label>
              </div>
            )}
            {['mark_primary', 'remove_photo'].includes(selectedAction) && (
              <select value={actionPayload.photo_id || ''} onChange={e => setActionPayload(p => ({ ...p, photo_id: e.target.value }))} style={selectStyle}>
                <option value="">Select photo</option>
                {(['front','spine','back','defects','label'] as const).flatMap(role => ((d.photos || {})[role] || []).map((photo: any) => <option key={`${role}-${photo.photo_id || photo.id}`} value={photo.photo_id || photo.id}>{role}: {photo.filename || `photo #${photo.photo_id || photo.id}`}</option>))}
              </select>
            )}
            {descriptionSuggestion && (
              <div style={{ background: '#fff', border: '1px solid #fde68a', borderRadius: 8, padding: 10, display: 'grid', gap: 6 }}>
                <div style={{ fontSize: 11, fontWeight: 900, color: '#92400e' }}>AI Description Suggestions</div>
                <div style={{ fontSize: 11 }}><strong>Title:</strong> {descriptionSuggestion.title}</div>
                <div style={{ fontSize: 11 }}><strong>Short:</strong> {descriptionSuggestion.short_description}</div>
                <textarea readOnly value={descriptionSuggestion.listing_description || ''} rows={4} style={{ ...inputStyle, fontFamily: 'inherit' }} />
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  <button onClick={() => patchArchive({ short_description: descriptionSuggestion.short_description }, 'Short description updated.')} style={{ padding: '5px 8px', borderRadius: 7, border: '1px solid #86efac', background: '#f0fdf4', color: '#166534', fontSize: 11, fontWeight: 800, cursor: 'pointer' }}>Use as Short Description</button>
                  <button onClick={() => patchArchive({ listing_title: descriptionSuggestion.title, listing_description: descriptionSuggestion.listing_description }, 'Listing description updated.')} style={{ padding: '5px 8px', borderRadius: 7, border: '1px solid #86efac', background: '#f0fdf4', color: '#166534', fontSize: 11, fontWeight: 800, cursor: 'pointer' }}>Use as Listing Description</button>
                  <button onClick={() => navigator.clipboard?.writeText(descriptionSuggestion.listing_description || '')} style={{ padding: '5px 8px', borderRadius: 7, border: '1px solid #d1d5db', background: '#fff', color: '#374151', fontSize: 11, fontWeight: 800, cursor: 'pointer' }}>Copy</button>
                </div>
              </div>
            )}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {['mark_primary', 'remove_photo'].includes(selectedAction) ? (
                <button disabled={actionLoading || !actionPayload.photo_id} onClick={async () => {
                  setActionLoading(true); setActionError(''); setActionSuccess('');
                  try {
                    const url = selectedAction === 'remove_photo' ? `${AG_API}/${arch.archive_id}/photos/${actionPayload.photo_id}/remove` : `${AG_API}/${arch.archive_id}/photos/${actionPayload.photo_id}`;
                    await fetch(url, { method: selectedAction === 'remove_photo' ? 'POST' : 'PATCH', headers: selectedAction === 'remove_photo' ? undefined : { 'Content-Type': 'application/json' }, body: selectedAction === 'remove_photo' ? undefined : JSON.stringify({ is_primary: true }) });
                    setActionSuccess(selectedAction === 'remove_photo' ? 'Photo hidden from active record. Original file preserved.' : 'Photo marked primary.');
                    setSelectedAction('');
                    await onRefresh();
                  } catch (exc: any) { setActionError(exc?.message || 'Photo action failed.'); }
                  setActionLoading(false);
                }} style={{ padding: '7px 12px', borderRadius: 8, border: 'none', background: '#f59e0b', color: '#fff', fontSize: 11, fontWeight: 900, cursor: actionLoading ? 'wait' : 'pointer' }}>Perform Action</button>
              ) : (
                <button disabled={actionLoading || ['add_photo','replace_front'].includes(selectedAction)} onClick={performContextAction} style={{ padding: '7px 12px', borderRadius: 8, border: 'none', background: '#f59e0b', color: '#fff', fontSize: 11, fontWeight: 900, cursor: actionLoading ? 'wait' : 'pointer' }}>{actionLoading ? 'Working...' : 'Perform Action'}</button>
              )}
            </div>
          </div>
        )}

        {editing && (
          <div style={{ margin: '12px 20px 0', border: '1px solid #06b6d4', borderRadius: 12, background: '#f8feff', padding: 14, flexShrink: 0, maxHeight: '44vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 900, color: '#164e63' }}>Edit Record</div>
                <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>Internal ArchiveForge updates only. No marketplace publishing or write APIs.</div>
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button onClick={saveEdit} disabled={saving} style={{ padding: '7px 14px', background: '#06b6d4', color: '#fff', border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 800, cursor: saving ? 'wait' : 'pointer' }}>{saving ? 'Saving...' : 'Save Changes'}</button>
                <button onClick={() => { setEditing(false); setEditData({}); setEditMsg(''); }} style={{ padding: '7px 14px', background: '#fff', color: '#64748b', border: '1px solid #cbd5e1', borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: 'pointer' }}>Cancel</button>
              </div>
            </div>

            {suggestedUpdates.length > 0 && (
              <div style={{ background: '#fff', border: '1px solid #bae6fd', borderRadius: 10, padding: 10, marginBottom: 12 }}>
                <div style={{ fontSize: 11, fontWeight: 900, color: '#155e75', marginBottom: 6 }}>Suggested Updates</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {suggestedUpdates.map(s => <span key={s} style={{ padding: '4px 7px', borderRadius: 999, background: '#ecfeff', color: '#155e75', fontSize: 10, fontWeight: 700 }}>{s}</span>)}
                </div>
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12 }}>
              <section style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 900, color: '#374151', marginBottom: 10 }}>Basic Info</div>
                <label style={{ display: 'block', marginBottom: 8 }}><div style={editLabelStyle}>Display title</div><input value={editData.display_title ?? ''} onChange={e => setEditData(ed => ({ ...ed, display_title: e.target.value }))} style={inputStyle} /></label>
                <label style={{ display: 'block', marginBottom: 8 }}><div style={editLabelStyle}>Short description</div><textarea value={editData.short_description ?? ''} onChange={e => setEditData(ed => ({ ...ed, short_description: e.target.value }))} rows={2} style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }} /></label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <label><div style={editLabelStyle}>Issue date override</div><input value={editData.issue_date ?? ''} onChange={e => setEditData(ed => ({ ...ed, issue_date: e.target.value }))} style={inputStyle} /></label>
                  <label><div style={editLabelStyle}>Cover subject</div><input value={editData.cover_subject ?? ''} onChange={e => setEditData(ed => ({ ...ed, cover_subject: e.target.value }))} style={inputStyle} /></label>
                </div>
                <label style={{ display: 'block', marginTop: 8 }}><div style={editLabelStyle}>Notes</div><textarea value={editData.notes ?? ''} onChange={e => setEditData(ed => ({ ...ed, notes: e.target.value }))} rows={3} style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }} /></label>
              </section>

              <section style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 900, color: '#374151', marginBottom: 10 }}>Condition</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <label><div style={editLabelStyle}>Condition score</div><select value={String(editData.condition_score ?? '')} onChange={e => setEditData(ed => ({ ...ed, condition_score: e.target.value }))} style={selectStyle}>{CONDITION_SCORE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select></label>
                  <label><div style={editLabelStyle}>Completeness</div><select value={editData.completeness_status || 'unknown'} onChange={e => {
                    const val = e.target.value;
                    setEditData(ed => ({ ...ed, completeness_status: val, is_complete: val === 'complete', defects: ['missing_pages','missing_cover','loose_cover'].includes(val) ? appendUniqueText(ed.defects || '', val.replace('_', ' ')) : ed.defects }));
                  }} style={selectStyle}>
                    <option value="complete">Complete</option><option value="missing_pages">Missing pages</option><option value="missing_cover">Missing cover</option><option value="loose_cover">Loose cover</option><option value="unknown">Unknown</option>
                  </select></label>
                  <label><div style={editLabelStyle}>Address label</div><select value={editData.address_label_status || 'unknown'} onChange={e => {
                    const val = e.target.value;
                    setEditData(ed => ({ ...ed, address_label_status: val, has_address_label: val === 'present', defects: val === 'removed_damage' ? appendUniqueText(ed.defects || '', 'address label removed/damage') : ed.defects }));
                  }} style={selectStyle}>
                    <option value="none">No label</option><option value="present">Label present</option><option value="removed_damage">Label removed/damage</option><option value="unknown">Unknown</option>
                  </select></label>
                  <label><div style={editLabelStyle}>Tier</div><select value={editData.tier || ''} onChange={e => setEditData(ed => ({ ...ed, tier: e.target.value }))} style={selectStyle}><option value="">Unknown</option><option value="A">A</option><option value="B">B</option><option value="C">C</option></select></label>
                </div>
                <div style={{ marginTop: 8 }}>
                  <div style={editLabelStyle}>Common defects</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 4 }}>
                    {COMMON_DEFECTS.map(defect => {
                      const checked = String(editData.defects || '').toLowerCase().includes(defect.toLowerCase());
                      return <label key={defect} style={{ fontSize: 10, color: '#374151', display: 'flex', alignItems: 'center', gap: 4 }}><input type="checkbox" checked={checked} onChange={e => updateDefect(defect, e.target.checked)} /> {defect}</label>;
                    })}
                  </div>
                </div>
                <label style={{ display: 'block', marginTop: 8 }}><div style={editLabelStyle}>Defects / condition notes</div><textarea value={editData.defects ?? ''} onChange={e => setEditData(ed => ({ ...ed, defects: e.target.value }))} rows={2} style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }} /></label>
              </section>

              <section style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 900, color: '#374151', marginBottom: 10 }}>Pricing</div>
                <label style={{ display: 'block', marginBottom: 8 }}><div style={editLabelStyle}>Pricing action</div><select value={pricingAction} onChange={e => handlePricingAction(e.target.value)} style={selectStyle}>
                  <option value="">Choose pricing action</option>
                  <option value="guide_only">Keep reference guide price only</option>
                  <option value="rough">Set final price from rough estimate</option>
                  <option value="dtm">Set final price from DTM average</option>
                  <option value="manual_comp">Set final price from manual comp</option>
                  <option value="dealer">Set final price from dealer asking price</option>
                  <option value="needs_comps">Mark needs comps</option>
                  <option value="clear">Clear final price</option>
                  <option value="manual">Owner manual final price</option>
                </select></label>
                <div style={{ padding: '6px 8px', background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 7, color: '#9a3412', fontSize: 10, marginBottom: 8 }}>
                  DTM and dealer asking prices are not sold comps. Final price means owner/operator accepted.
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <label><div style={editLabelStyle}>Comp min</div><input type="number" step="0.01" value={editData.rough_comp_min ?? ''} onChange={e => setEditData(ed => ({ ...ed, rough_comp_min: e.target.value }))} style={inputStyle} /></label>
                  <label><div style={editLabelStyle}>Comp max</div><input type="number" step="0.01" value={editData.rough_comp_max ?? ''} onChange={e => setEditData(ed => ({ ...ed, rough_comp_max: e.target.value }))} style={inputStyle} /></label>
                  <label><div style={editLabelStyle}>Final price</div><input type="number" step="0.01" value={editData.final_price ?? ''} onChange={e => setEditData(ed => ({ ...ed, final_price: e.target.value }))} style={inputStyle} /></label>
                </div>
                <label style={{ display: 'block', marginTop: 8 }}><div style={editLabelStyle}>Pricing notes</div><textarea value={editData.pricing_notes ?? ''} onChange={e => setEditData(ed => ({ ...ed, pricing_notes: e.target.value }))} rows={2} style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }} /></label>
              </section>

              <section style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 900, color: '#374151', marginBottom: 10 }}>Inventory / Listing</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <label><div style={editLabelStyle}>Source box</div><input value={editData.source_box_code ?? ''} onChange={e => setEditData(ed => ({ ...ed, source_box_code: e.target.value }))} style={inputStyle} /></label>
                  <label><div style={editLabelStyle}>Destination box</div><input value={editData.processed_box_code ?? ''} onChange={e => setEditData(ed => ({ ...ed, processed_box_code: e.target.value }))} style={inputStyle} /></label>
                  <label><div style={editLabelStyle}>Archive location</div><input value={editData.archive_location ?? ''} onChange={e => setEditData(ed => ({ ...ed, archive_location: e.target.value }))} style={inputStyle} /></label>
                  <label><div style={editLabelStyle}>Listing status</div><select value={editData.listing_status || 'no_listing'} onChange={e => setEditData(ed => ({ ...ed, listing_status: e.target.value }))} style={selectStyle}>{LISTING_STATUS_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}</select></label>
                </div>
                <label style={{ display: 'block', marginTop: 8 }}><div style={editLabelStyle}>Sale plan</div><select value={editData.sale_plan || ''} onChange={e => {
                  const val = e.target.value;
                  setEditData(ed => ({ ...ed, sale_plan: val, item_status: val === 'Use for ad research only' ? 'ads_only' : val === 'Break out for ads' ? 'broken_for_ads' : val === 'Hold intact' ? 'held' : ed.item_status, ad_breakout_status: val === 'Break out for ads' ? 'in_progress' : val === 'Use for ad research only' ? 'candidate' : ed.ad_breakout_status }));
                }} style={selectStyle}>
                  <option value="">Select sale plan</option><option>List whole magazine</option><option>Hold intact</option><option>Use for ad research only</option><option>Break out for ads</option><option>Bundle with similar issues</option><option>Keep for collection/reference</option><option>Needs more comps</option><option>Needs more photos</option><option>Do not sell</option><option>Other/manual</option>
                </select></label>
              </section>

              <section style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 900, color: '#374151', marginBottom: 10 }}>Lifecycle / Disposition</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 8 }}>
                  <label><div style={editLabelStyle}>Item status</div><select value={editData.item_status || 'inventory'} onChange={e => setEditData(ed => ({ ...ed, item_status: e.target.value }))} style={selectStyle}>{ITEM_STATUS_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}</select></label>
                  <label><div style={editLabelStyle}>Marketplace status</div><select value={editData.marketplace_status || 'not_listed'} onChange={e => setEditData(ed => ({ ...ed, marketplace_status: e.target.value }))} style={selectStyle}>{MARKETPLACE_STATUS_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}</select></label>
                  <label><div style={editLabelStyle}>Ad breakout status</div><select value={editData.ad_breakout_status || 'none'} onChange={e => setEditData(ed => ({ ...ed, ad_breakout_status: e.target.value }))} style={selectStyle}>{AD_BREAKOUT_STATUS_OPTIONS.map(o => <option key={o} value={o}>{o}</option>)}</select></label>
                  <label><div style={editLabelStyle}>Sold price</div><input type="number" step="0.01" value={editData.sold_price ?? ''} onChange={e => setEditData(ed => ({ ...ed, sold_price: e.target.value }))} style={inputStyle} /></label>
                  <label><div style={editLabelStyle}>Sold date</div><input type="date" value={editData.sold_date ?? ''} onChange={e => setEditData(ed => ({ ...ed, sold_date: e.target.value }))} style={inputStyle} /></label>
                  <label><div style={editLabelStyle}>Sold platform</div><input value={editData.sold_platform ?? ''} onChange={e => setEditData(ed => ({ ...ed, sold_platform: e.target.value }))} style={inputStyle} /></label>
                </div>
                <label style={{ display: 'block', marginTop: 8 }}><div style={editLabelStyle}>Disposition notes</div><textarea value={editData.disposition_notes ?? ''} onChange={e => setEditData(ed => ({ ...ed, disposition_notes: e.target.value }))} rows={2} style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }} /></label>
              </section>

              <section style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 12, gridColumn: '1/-1' }}>
                <div style={{ fontSize: 12, fontWeight: 900, color: '#374151', marginBottom: 10 }}>Advanced Edit</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <label><div style={editLabelStyle}>Listing title</div><input value={editData.listing_title ?? ''} onChange={e => setEditData(ed => ({ ...ed, listing_title: e.target.value }))} style={inputStyle} /></label>
                  <label><div style={editLabelStyle}>Manual eBay handoff notes</div><input value={editData.disposition_notes ?? ''} onChange={e => setEditData(ed => ({ ...ed, disposition_notes: e.target.value }))} style={inputStyle} /></label>
                </div>
                <label style={{ display: 'block', marginTop: 8 }}><div style={editLabelStyle}>Listing description</div><textarea value={editData.listing_description ?? ''} onChange={e => setEditData(ed => ({ ...ed, listing_description: e.target.value }))} rows={4} style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }} /></label>
              </section>
            </div>
          </div>
        )}

        {/* Tab content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
          {/* PHOTOS TAB */}
          {tab === 'photos' && (
            <div style={{ display: 'grid', gap: 16 }}>
              {(['front', 'spine', 'back', 'defects', 'label', 'ad_pages'] as const).map(role => {
                const group: any[] = (d.photos || {})[role] || [];
                if (!group.length) return null;
                return (
                  <div key={role}>
                    <div style={{ fontSize: 12, fontWeight: 800, color: '#374151', marginBottom: 8, textTransform: 'capitalize' }}>{role.replace('_', ' ')} ({group.length})</div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 10 }}>
                      {group.map((p: any) => (
                        <div key={p.id || p.photo_id} style={{ border: '1px solid #e5e2dc', borderRadius: 8, padding: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
                          <img src={`${API}${(p.thumbnail_url || p.photo_url || '').replace('/api/v1', '')}`} alt={p.role} style={{ width: '100%', height: 180, objectFit: 'contain', background: '#f9fafb', borderRadius: 6 }} onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                          <div style={{ fontSize: 10, color: '#666' }}>{p.filename || p.original_name || `photo_${p.id || p.photo_id}`}</div>
                          <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                            <a href={`${API}${(p.photo_url || '').replace('/api/v1', '')}`} target="_blank" rel="noreferrer" style={{ fontSize: 10, color: '#06b6d4' }}>Open full image</a>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
              {Object.values(d.photos || {}).every((g: any) => !g.length) && (
                <div style={{ textAlign: 'center', color: '#888', padding: 30 }}>No photos uploaded.</div>
              )}
            </div>
          )}

          {/* REFERENCE TAB */}
          {tab === 'reference' && (
            <div style={{ display: 'grid', gap: 16 }}>
              {/* Google Books reference */}
              {d.reference_cover && (
                <div style={{ border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
                  <div style={{ fontSize: 12, fontWeight: 800, color: '#374151', marginBottom: 10 }}>Google Books Reference</div>
                  <div style={{ display: 'flex', gap: 14 }}>
                    {d.reference_cover.cover_image_url && (
                      <img src={d.reference_cover.cover_image_url} alt="Google Books reference" style={{ width: 120, height: 160, objectFit: 'contain', borderRadius: 6, border: '1px solid #e5e2dc', background: '#f9fafb' }} onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                    )}
                    <div style={{ flex: 1, fontSize: 11, color: '#666', display: 'grid', gap: 4 }}>
                      <div><span style={{ color: '#888' }}>Volume ID: </span><span style={{ fontFamily: 'monospace' }}>{d.reference_cover.volume_id}</span></div>
                      <div><span style={{ color: '#888' }}>Issue date: </span>{d.reference_cover.published_date || d.reference_cover.issue_date || '—'}</div>
                      <div><span style={{ color: '#888' }}>Title: </span>{d.reference_cover.title || '—'}</div>
                      <div><span style={{ color: '#888' }}>Confidence: </span>{d.reference_cover.match_confidence ? `${Math.round(d.reference_cover.match_confidence * 100)}%` : '—'}</div>
                    </div>
                  </div>
                  <div style={{ marginTop: 8, padding: '5px 8px', background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 6, fontSize: 10, color: '#9a3412' }}>Reference image — not your item photo</div>
                </div>
              )}
              {/* Dealer reference */}
              {d.dealer_reference && (
                <div style={{ border: '1px solid #fcd34d', borderRadius: 12, padding: 14, background: '#fffbeb' }}>
                  <div style={{ fontSize: 12, fontWeight: 800, color: '#92400e', marginBottom: 10 }}>Dealer Catalog Reference</div>
                  <div style={{ fontSize: 11, color: '#666', display: 'grid', gap: 4 }}>
                    <div><span style={{ color: '#888' }}>Source: </span><a href={d.dealer_reference.source_url} target="_blank" rel="noreferrer" style={{ color: '#06b6d4' }}>OriginalLifeMagazines.com</a></div>
                    <div><span style={{ color: '#888' }}>Issue date: </span>{d.dealer_reference.issue_date || '—'}</div>
                    <div><span style={{ color: '#888' }}>Title: </span>{d.dealer_reference.title || '—'}</div>
                    {d.dealer_reference.asking_price && (
                      <div><span style={{ color: '#92400e', fontWeight: 700 }}>Asking price: ${d.dealer_reference.asking_price}</span></div>
                    )}
                    <div><span style={{ color: '#888' }}>Confidence: </span>{d.dealer_reference.match_confidence ? `${Math.round(d.dealer_reference.match_confidence * 100)}%` : '—'}</div>
                  </div>
                  <div style={{ marginTop: 8, padding: '5px 8px', background: '#fef3c7', border: '1px solid #fcd34d', borderRadius: 6, fontSize: 10, color: '#92400e' }}>Dealer asking price — not sold comp evidence</div>
                </div>
              )}
              {!d.reference_cover && !d.dealer_reference && (
                <div style={{ textAlign: 'center', color: '#888', padding: 30 }}>No reference images available.</div>
              )}
            </div>
          )}

          {/* ISSUE INFO TAB */}
          {tab === 'issue_info' && (
            <div style={{ display: 'grid', gap: 14 }}>
              {d.issue_info?.status && d.issue_info.status !== 'not_run' ? (
                <>
                  <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, fontSize: 12 }}>
                    <InfoRow label="Status" value={d.issue_info.status} />
                    <InfoRow label="Confidence" value={d.issue_info.confidence ? `${Math.round(d.issue_info.confidence * 100)}%` : '—'} />
                    <InfoRow label="Issue date" value={d.issue_info.issue_date || '—'} />
                    <InfoRow label="Cover title" value={d.issue_info.cover_title || '—'} />
                    <InfoRow label="Detected subject" value={d.issue_info.detected_subject || '—'} />
                    <InfoRow label="Evidence grade" value={d.issue_info.evidence_grade || '—'} />
                    <InfoRow label="Google Books ID" value={d.issue_info.selected_google_books_volume_id || '—'} mono />
                    <InfoRow label="Evidence source" value={d.issue_info.evidence_source || '—'} />
                  </div>
                  {d.issue_info.visible_text?.length > 0 && (
                    <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
                      <div style={{ fontSize: 11, fontWeight: 800, color: '#374151', marginBottom: 8 }}>Visible Text ({d.issue_info.visible_text.length} items)</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                        {(d.issue_info.visible_text as string[]).map((t, i) => (
                          <span key={i} style={{ padding: '2px 8px', background: '#f3f4f6', borderRadius: 4, fontSize: 11, fontFamily: 'monospace' }}>{t}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {d.issue_info.stale_warning && (
                    <div style={{ padding: '8px 12px', background: '#fef3c7', border: '1px solid #fcd34d', borderRadius: 8, fontSize: 11, color: '#92400e' }}>{d.issue_info.stale_warning}</div>
                  )}
                  {d.life_master && (
                    <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
                      <div style={{ fontSize: 11, fontWeight: 800, color: '#374151', marginBottom: 8 }}>LIFE Issue Master</div>
                      <div style={{ fontSize: 11, color: '#666', display: 'grid', gap: 4 }}>
                        <InfoRow label="Date" value={d.life_master.normalized_date || '—'} />
                        <InfoRow label="Subject" value={d.life_master.cover_subject || d.life_master.description || '—'} />
                        <InfoRow label="Sources" value={d.life_master.source_count || '—'} />
                        <InfoRow label="DTM Low/High" value={d.life_master.dtmagazine_low && d.life_master.dtmagazine_high ? `$${d.life_master.dtmagazine_low} – $${d.life_master.dtmagazine_high}` : '—'} />
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div style={{ textAlign: 'center', color: '#888', padding: 30 }}>Issue Info Resolver not run.</div>
              )}
            </div>
          )}

          {/* CONDITION TAB */}
          {tab === 'condition' && (
            <div style={{ display: 'grid', gap: 14 }}>
              <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14, fontSize: 12 }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  <InfoRow label="Condition Score" value={arch.condition_score ? `${arch.condition_score}/5` : '—'} />
                  <InfoRow label="Complete" value={arch.complete ? 'Yes' : 'No'} />
                  <InfoRow label="Address Label" value={arch.address_label ? 'Present' : 'None'} />
                  <InfoRow label="Defects" value={arch.defects || 'None noted'} />
                </div>
              </div>
              {arch.notes && (
                <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
                  <div style={{ fontSize: 11, fontWeight: 800, color: '#374151', marginBottom: 6 }}>Notes</div>
                  <div style={{ fontSize: 11, color: '#666', whiteSpace: 'pre-wrap' }}>{arch.notes}</div>
                </div>
              )}
              {d.issue_info?.condition_notes && (
                <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
                  <div style={{ fontSize: 11, fontWeight: 800, color: '#374151', marginBottom: 6 }}>AI Condition Notes</div>
                  <div style={{ fontSize: 11, color: '#666', whiteSpace: 'pre-wrap' }}>{d.issue_info.condition_notes}</div>
                </div>
              )}
            </div>
          )}

          {/* ADS TAB */}
          {tab === 'ads' && (
            <div style={{ display: 'grid', gap: 14 }}>
              <div style={{ padding: '8px 12px', background: '#fef3c7', border: '1px solid #fcd34d', borderRadius: 8, fontSize: 11, color: '#92400e' }}>
                Ads are unverified until photographed in this physical copy.
              </div>
              {(d.ad_opportunities || []).length > 0 ? (
                (d.ad_opportunities as any[]).map((opp: any) => (
                  <div key={opp.id} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 12, fontSize: 11, display: 'grid', gap: 4 }}>
                    <div style={{ fontWeight: 700, fontSize: 12 }}>{opp.brand || opp.candidate_type || 'Unknown'}</div>
                    <div style={{ color: '#666' }}>{opp.product || opp.category || '—'}</div>
                    <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
                      <span style={{ padding: '1px 6px', borderRadius: 4, fontSize: 10, background: opp.verification_status === 'verified_in_copy' ? '#d1fae5' : '#f3f4f6', color: opp.verification_status === 'verified_in_copy' ? '#065f46' : '#888' }}>{opp.verification_status || 'unknown'}</span>
                      {opp.estimated_low && opp.estimated_high && <span style={{ color: '#666' }}>${opp.estimated_low}–${opp.estimated_high}</span>}
                    </div>
                    <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginTop: 6 }}>
                      <button onClick={() => { setTab('ads'); startTabAction('photograph_candidate', 'ads'); setActionPayload({ candidate_id: opp.id }); setCandidateUploadId(opp.id); }} style={{ padding: '4px 7px', borderRadius: 6, border: '1px solid #06b6d4', background: '#ecfeff', color: '#155e75', fontSize: 10, fontWeight: 800, cursor: 'pointer' }}>Photograph</button>
                      <button disabled={opp.verification_status === 'verified_in_copy'} onClick={async () => { await fetch(`${AG_API}/${arch.archive_id}/ad-opportunities/${opp.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ verification_status: 'not_found', suggested_action: 'not_found', user_notes: 'Updated from item detail drawer.' }) }); await onRefresh(); }} style={{ padding: '4px 7px', borderRadius: 6, border: '1px solid #e5e7eb', background: '#fff', color: '#6b7280', fontSize: 10, fontWeight: 700, cursor: 'pointer' }}>Mark not found</button>
                      <button disabled={opp.verification_status === 'verified_in_copy'} onClick={async () => { await fetch(`${AG_API}/${arch.archive_id}/ad-opportunities/${opp.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ verification_status: 'ignored', suggested_action: 'ignore', user_notes: 'Updated from item detail drawer.' }) }); await onRefresh(); }} style={{ padding: '4px 7px', borderRadius: 6, border: '1px solid #e5e7eb', background: '#fff', color: '#6b7280', fontSize: 10, fontWeight: 700, cursor: 'pointer' }}>Ignore</button>
                    </div>
                  </div>
                ))
              ) : (
                <div style={{ textAlign: 'center', color: '#888', padding: 30 }}>No ad opportunities found.</div>
              )}
              {d.ad_page_photos?.length > 0 && (
                <div>
                  <div style={{ fontSize: 12, fontWeight: 800, color: '#374151', marginBottom: 8 }}>Ad Page Photos ({d.ad_page_photos.length})</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 8 }}>
                    {(d.ad_page_photos as any[]).map((p: any) => (
                      <div key={p.id} style={{ border: '1px solid #e5e2dc', borderRadius: 6, padding: 6, textAlign: 'center' }}>
                        <div style={{ fontSize: 10, color: '#888', marginBottom: 4 }}>{p.page_number || p.filename}</div>
                        <div style={{ fontSize: 10, color: '#666' }}>{p.analysis_status || '—'}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* PRICING TAB */}
          {tab === 'pricing' && (
            <div style={{ display: 'grid', gap: 14 }}>
              <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14, fontSize: 12 }}>
                <div style={{ fontSize: 12, fontWeight: 800, color: '#374151', marginBottom: 10 }}>Pricing Summary</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <InfoRow label="Comp Min" value={arch.rough_comp_min ? `$${arch.rough_comp_min}` : '—'} />
                  <InfoRow label="Comp Max" value={arch.rough_comp_max ? `$${arch.rough_comp_max}` : '—'} />
                  <InfoRow label="Final Price" value={arch.final_price ? `$${arch.final_price}` : '—'} />
                  <InfoRow label="Pricing Type" value={d.pricing_summary?.pricing_type || '—'} />
                  <InfoRow label="True Comps" value={d.pricing_summary?.true_comps_available ? 'Available' : 'Not available'} />
                </div>
                {d.life_master && d.life_master.dtmagazine_low && (
                  <div style={{ marginTop: 10, padding: '8px 10px', background: '#f0fdf4', borderRadius: 8, fontSize: 11 }}>
                    <span style={{ color: '#166534' }}>DTM Reference: </span>
                    ${d.life_master.dtmagazine_low}–${d.life_master.dtmagazine_high} (avg ${d.life_master.dtmagazine_average})
                  </div>
                )}
                <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                  <button onClick={() => acceptSuggestedFinalPrice(d.pricing_summary?.recommended_price || d.life_master?.dtmagazine_average || arch.rough_comp_max || arch.rough_comp_min, d.pricing_summary?.pricing_type || 'reference value')} style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid #86efac', background: '#f0fdf4', color: '#166534', fontSize: 11, fontWeight: 800, cursor: 'pointer' }}>
                    Accept as Final Price
                  </button>
                  <span style={{ fontSize: 10, color: '#92400e' }}>Owner/operator acceptance only. Reference guide and dealer values are not sold comps.</span>
                </div>
              </div>
              {(d.comps || []).length > 0 && (
                <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
                  <div style={{ fontSize: 12, fontWeight: 800, color: '#374151', marginBottom: 8 }}>Comps ({d.comps.length})</div>
                  {(d.comps as any[]).slice(0, 10).map((c: any, i: number) => (
                    <div key={i} style={{ fontSize: 11, color: '#666', padding: '4px 0', borderBottom: '1px solid #f0f0f0', display: 'grid', gridTemplateColumns: '1fr auto', gap: 8 }}>
                      <span>{c.title || c.source || 'Comp'}</span>
                      <span style={{ fontWeight: 600 }}>{c.sold_price || c.asking_price ? `$${c.sold_price || c.asking_price}` : '—'}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* LISTING TAB */}
          {tab === 'listing' && (
            <div style={{ display: 'grid', gap: 14 }}>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {EXPORT_URLS.pdf_url && <a href={EXPORT_URLS.pdf_url} target="_blank" rel="noreferrer" style={{ padding: '7px 12px', background: '#fff', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 11, fontWeight: 600, color: '#374151', cursor: 'pointer', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}><Download size={11} /> Report PDF</a>}
                {EXPORT_URLS.pdf_with_images_url && <a href={EXPORT_URLS.pdf_with_images_url} target="_blank" rel="noreferrer" style={{ padding: '7px 12px', background: '#fff', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 11, fontWeight: 600, color: '#374151', cursor: 'pointer', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}><Download size={11} /> Report PDF+Photos</a>}
                {EXPORT_URLS.listing_packet_json_url && <a href={EXPORT_URLS.listing_packet_json_url} target="_blank" rel="noreferrer" style={{ padding: '7px 12px', background: '#fff', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 11, fontWeight: 600, color: '#374151', cursor: 'pointer', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}><Download size={11} /> JSON</a>}
                {EXPORT_URLS.listing_packet_xlsx_url && <a href={EXPORT_URLS.listing_packet_xlsx_url} target="_blank" rel="noreferrer" style={{ padding: '7px 12px', background: '#fff', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 11, fontWeight: 600, color: '#374151', cursor: 'pointer', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}><Download size={11} /> XLSX</a>}
              </div>
              {d.listing_draft ? (
                <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14, fontSize: 12 }}>
                  <div style={{ fontWeight: 800, color: '#374151', marginBottom: 8 }}>{d.listing_draft.listing_title || 'Untitled Draft'}</div>
                  {d.listing_draft.listing_description && (
                    <div style={{ fontSize: 11, color: '#666', whiteSpace: 'pre-wrap', marginTop: 8 }}>{d.listing_draft.listing_description}</div>
                  )}
                  <div style={{ marginTop: 8, fontSize: 11, color: '#888' }}>Draft ID: {d.listing_draft.draft_id || d.listing_draft.id || '—'} · Status: {arch.listing_status || '—'}</div>
                </div>
              ) : (
                <div style={{ textAlign: 'center', color: '#888', padding: 30 }}>No listing draft saved.</div>
              )}
              <div style={{ padding: '8px 12px', background: '#fef3c7', border: '1px solid #fcd34d', borderRadius: 8, fontSize: 11, color: '#92400e' }}>
                Internal listing draft — does not publish to eBay or any marketplace.
              </div>
            </div>
          )}

          {/* LIFECYCLE TAB */}
          {tab === 'lifecycle' && (
            <div style={{ display: 'grid', gap: 14 }}>
              {/* Status badges */}
              <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14, fontSize: 12, display: 'grid', gap: 8 }}>
                <div style={{ fontWeight: 800, color: '#374151', marginBottom: 4 }}>Current Status</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                  <InfoRow label="Item Status" value={lc.item_status || 'inventory'} />
                  <InfoRow label="Marketplace" value={lc.marketplace_status || 'not_listed'} />
                  <InfoRow label="Ad Breakout" value={lc.ad_breakout_status || 'none'} />
                  <InfoRow label="Sold Price" value={lc.sold_price ? `$${lc.sold_price}` : '—'} />
                  <InfoRow label="Sold Date" value={lc.sold_date || '—'} />
                  <InfoRow label="Sold Platform" value={lc.sold_platform || '—'} />
                </div>
                {lc.disposition_notes && (
                  <div style={{ fontSize: 11, color: '#666', marginTop: 4, whiteSpace: 'pre-wrap' }}>Notes: {lc.disposition_notes}</div>
                )}
              </div>
              {lifecycleMsg && <div style={{ padding: '6px 10px', background: lifecycleMsg.startsWith('Error') ? '#fee2e2' : '#d1fae5', borderRadius: 8, fontSize: 11, color: lifecycleMsg.startsWith('Error') ? '#991b1b' : '#065f46' }}>{lifecycleMsg}</div>}
              <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
                <div style={{ fontSize: 11, fontWeight: 800, color: '#374151', marginBottom: 8 }}>Quick Actions</div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', fontSize: 11 }}>
                  <button disabled={lifecycleOp} onClick={() => doLifecycle('held', 'draft', 'none', 'Held intact')} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid #e5e2dc', background: '#fff', color: '#374151', cursor: 'pointer', fontSize: 11 }}>Hold Intact</button>
                  <button disabled={lifecycleOp} onClick={() => doLifecycle('listed', 'listed', 'none', 'Marked as listed internally')} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid #e5e2dc', background: '#fff', color: '#374151', cursor: 'pointer', fontSize: 11 }}>Mark Listed</button>
                  <button disabled={lifecycleOp} onClick={() => doLifecycle('sold', 'sold', 'none', 'Marked sold')} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid #fca5a5', background: '#fff', color: '#991b1b', cursor: 'pointer', fontSize: 11 }}>Mark Sold</button>
                  <button disabled={lifecycleOp} onClick={() => doLifecycle('broken_for_ads', 'not_listed', 'in_progress', 'Broken out for ads')} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid #e5e2dc', background: '#fff', color: '#374151', cursor: 'pointer', fontSize: 11 }}>Broken for Ads</button>
                  <button disabled={lifecycleOp} onClick={() => doLifecycle('ads_only', 'not_listed', 'ads_listed', 'Used for ads only')} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid #e5e2dc', background: '#fff', color: '#374151', cursor: 'pointer', fontSize: 11 }}>Ads Only</button>
                  <button disabled={lifecycleOp} onClick={() => doLifecycle('needs_review', 'not_listed', 'none', 'Flagged for review')} style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid #fca5a5', background: '#fff', color: '#991b1b', cursor: 'pointer', fontSize: 11 }}>Needs Review</button>
                </div>
                <div style={{ marginTop: 8, padding: '6px 8px', background: '#fef3c7', borderRadius: 6, fontSize: 10, color: '#92400e' }}>
                  These actions update internal ArchiveForge status only — they do not publish or update any marketplace.
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// eslint-disable-next-line no-unused-vars
function InfoRow({ label, value, mono }: { label: string; value: string | number | null | undefined; mono?: boolean }) {
  return value !== undefined && value !== null && value !== '' ? (
    <div style={{ display: 'flex', gap: 6 }}>
      <span style={{ color: '#888', minWidth: 90 }}>{label}:</span>
      <span style={{ color: '#1a1a1a', fontFamily: mono ? 'monospace' : 'inherit', fontWeight: 500 }}>{value}</span>
    </div>
  ) : null;
}

function EditField({ label, field, arch, editData, setEditData, type }: { label: string; field: string; arch: any; editData: any; setEditData: any; type?: string }) {
  return (
    <div>
      <div style={{ fontSize: 10, color: '#888', marginBottom: 3 }}>{label}</div>
      <input type={type || 'text'} value={editData[field] ?? arch[field] ?? ''} onChange={e => setEditData((ed: Record<string, any>) => ({ ...ed, [field]: type === 'number' ? (e.target.value ? parseFloat(e.target.value) : null) : e.target.value }))}
        style={{ width: '100%', padding: '5px 8px', border: '1px solid #e5e2dc', borderRadius: 6, fontSize: 11 }} />
    </div>
  );
}

// ── Main ArchiveForgePage ─────────────────────────────────────────────────────

type WizardStep = 'start' | 'intake' | 'photos' | 'match' | 'ads' | 'archive' | 'condition' | 'pricing' | 'listing' | 'review' | 'inventory';

const STEP_ORDER: WizardStep[] = ['start','intake','photos','match','ads','archive','condition','pricing','listing','review','inventory'];
const STEP_LABELS: Record<WizardStep, string> = {
  start: 'Start',
  intake: 'Search Issue',
  photos: '1. Photos',
  match: '2. Confirm',
  ads: '3. Ads',
  archive: '4. Details',
  condition: '5. Condition',
  pricing: '6. Pricing',
  listing: '7. Listing',
  review: '8. Export/Review',
  inventory: 'Inventory',
};

export default function ArchiveForgePage() {
  const [step, setStep] = useState<WizardStep>('start');
  const [refIssue, setRefIssue] = useState<LifeReferenceIssue | null>(null);
  const [archiveData, setArchiveData] = useState<Partial<ArchiveItem>>({
    processed_status: 'RAW',
    condition_score: 3,
    tier: 'C',
    is_complete: true,
    actual_listing_images: [],
  });
  const [savedArchiveId, setSavedArchiveId] = useState<number | null>(null);
  const [identifyResult, setIdentifyResult] = useState<IdentifyResponse | null>(null);
  const [matchConfirmation, setMatchConfirmation] = useState<MatchConfirmation | null>(null);
  const [creatingArchive, setCreatingArchive] = useState(false);
  const [startError, setStartError] = useState('');

  const currentStepIdx = STEP_ORDER.indexOf(step);

  const createArchive = async (data: Partial<ArchiveItem> = archiveData): Promise<number | null> => {
    if (savedArchiveId) return savedArchiveId;
    setCreatingArchive(true);
    setStartError('');
    try {
      const res = await fetch(`${AG_API}/archives`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...data,
          actual_listing_images: [],
          has_address_label: data.has_address_label || false,
          is_complete: data.is_complete !== false,
        }),
      });
      const out = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(out.detail || `Archive create failed with ${res.status}`);
      setSavedArchiveId(out.id);
      return out.id;
    } catch (exc: any) {
      setStartError(exc?.message || 'Could not create archive record.');
      return null;
    } finally {
      setCreatingArchive(false);
    }
  };

  const handleStartWithPhoto = async () => {
    const nextData = {
      ...archiveData,
      issue_title: archiveData.issue_title || 'LIFE Magazine photo-first intake',
      processed_status: archiveData.processed_status || 'RAW',
    };
    setArchiveData(nextData);
    const id = await createArchive(nextData);
    if (id) setStep('photos');
  };

  const handleIdentified = async (ref: LifeReferenceIssue) => {
    const nextData = {
      ...archiveData,
      reference_issue_id: ref.id,
      reference_source: ref.source || '',
      google_books_volume_id: ref.google_books_volume_id || '',
      issue_title: ref.issue_title || 'LIFE',
      volume_label: ref.volume_label || '',
      cover_thumbnail_url: ref.cover_thumbnail_url || '',
      cover_preview_url: ref.cover_preview_url || '',
      search_query_used: ref.search_query_used || '',
      match_reason: ref.match_reason || '',
      issue_date: ref.date,
      volume: ref.volume || undefined,
      issue_number: ref.issue_number || undefined,
      cover_subject: ref.cover_subject,
      reference_cover_url: ref.reference_cover_url,
      tier: ref.tier_guidance,
      rough_comp_min: parseFloat(ref.rarity_notes.match(/\$([\d,]+)/)?.[1]?.replace(',','') || '0') || 0,
      rough_comp_max: parseFloat(ref.rarity_notes.match(/\$([\d,]+)–?\$?([\d,]+)/)?.[2]?.replace(',','') || '0') || 0,
    };
    setRefIssue(ref);
    setArchiveData(nextData);
    setMatchConfirmation(null);
    await createArchive(nextData);
    setStep('match');
  };

  const handleArchiveUpdate = async () => {
    const archiveId = savedArchiveId || await createArchive();
    if (!archiveId) return;
    try {
      await fetch(`${AG_API}/archives/${archiveId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          issue_date: archiveData.issue_date || '',
          cover_subject: archiveData.cover_subject || '',
          reference_cover_url: archiveData.reference_cover_url || '',
          condition_score: archiveData.condition_score,
          has_address_label: archiveData.has_address_label || false,
          is_complete: archiveData.is_complete !== false,
          defects: archiveData.defects || '',
          notes: archiveData.notes || '',
          tier: archiveData.tier,
          rough_comp_min: archiveData.rough_comp_min || 0,
          rough_comp_max: archiveData.rough_comp_max || 0,
          sale_plan: archiveData.sale_plan || '',
          source_box_code: archiveData.source_box_code || '',
          source_slot_position: archiveData.source_slot_position || '',
          processed_box_code: archiveData.processed_box_code || '',
          processed_status: archiveData.processed_status || 'RAW',
          archive_location: archiveData.archive_location || '',
        }),
      });
    } catch { /* silent */ }
  };

  const handleMatchConfirmed = (confirmation: MatchConfirmation) => {
    setMatchConfirmation(confirmation);
    setArchiveData(prev => ({
      ...prev,
      issue_date: confirmation.issue_date || prev.issue_date,
      cover_subject: confirmation.cover_title || prev.cover_subject,
      processed_status: prev.processed_status === 'RAW' ? 'IDENTIFIED' : prev.processed_status,
    }));
  };

  const navigate = async (direction: 'next' | 'prev') => {
    const idx = currentStepIdx;
    if (direction === 'next' && idx < STEP_ORDER.length - 1) {
      if (['archive', 'condition', 'pricing'].includes(step)) await handleArchiveUpdate();
      setStep(STEP_ORDER[idx + 1]);
    } else if (direction === 'prev' && idx > 0) {
      if (['listing', 'pricing'].includes(step)) await handleArchiveUpdate();
      setStep(STEP_ORDER[idx - 1]);
    }
  };

  const canGoNext = () => {
    if (step === 'start') return false;
    if (step === 'intake') return !!refIssue;
    if (step === 'match') return !!matchConfirmation;
    return true;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#faf9f7' }}>
      {/* Header */}
      <div style={{ padding: '14px 20px', background: '#fff', borderBottom: '1px solid #e5e2dc', display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
        <div style={{ width: 36, height: 36, background: '#06b6d4', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Archive size={18} color="#fff" />
        </div>
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>ArchiveForge</div>
          <div style={{ fontSize: 11, color: '#888' }}>LIFE Listing Engine — V1</div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          {STEP_ORDER.map((s, i) => (
            <button key={s} onClick={() => setStep(s)}
              style={{
                padding: '4px 10px', borderRadius: 20, fontSize: 10, fontWeight: 600, cursor: 'pointer',
                background: step === s ? '#06b6d4' : i <= currentStepIdx ? '#d1fae5' : '#f5f3ef',
                color: step === s ? '#fff' : i <= currentStepIdx ? '#065f46' : '#9ca3af',
                border: 'none',
              }}>
              {STEP_LABELS[s]}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '20px 24px' }}>
        {step === 'start' && (
          <StartSection
            onStartPhoto={handleStartWithPhoto}
            onSearchKnown={() => setStep('intake')}
            creating={creatingArchive}
            error={startError}
          />
        )}
        {step === 'intake' && <IntakeSection onIdentified={handleIdentified} />}
        {step === 'photos' && (
	          <PhotoSection
	            archiveId={savedArchiveId}
	            refIssue={refIssue}
	            identifyResult={identifyResult}
	            onIdentifyResult={(result) => {
	              setIdentifyResult(result);
	              setMatchConfirmation(null);
	            }}
	            onConfirmIssue={() => setStep('match')}
	          />
        )}
        {step === 'match' && (
          <ConfirmMatchSection
            archiveId={savedArchiveId}
            refIssue={refIssue}
            identifyResult={identifyResult}
            confirmation={matchConfirmation}
            onConfirmed={handleMatchConfirmed}
            onSearchAgain={() => setStep('intake')}
            onManual={() => setMatchConfirmation({ status: 'manual', source: 'manual' })}
          />
        )}
        {step === 'ads' && <AdOpportunitySection archiveId={savedArchiveId} />}
        {step === 'archive' && <ArchiveSection data={archiveData} archiveId={savedArchiveId} onChange={setArchiveData} />}
        {step === 'condition' && <ConditionSection data={archiveData} onChange={setArchiveData} />}
        {step === 'pricing' && (
          <PricingSection
            data={archiveData}
            archiveId={savedArchiveId}
            identifyResult={identifyResult}
            confirmation={matchConfirmation}
            onChange={setArchiveData}
          />
        )}
        {step === 'listing' && (
          <ListingBuilderSection
            data={archiveData}
            refIssue={refIssue}
            archiveId={savedArchiveId}
            onSaved={() => {}}
          />
        )}
        {step === 'review' && <ReviewPublishSection archiveId={savedArchiveId} refIssue={refIssue} />}
        {step === 'inventory' && <InventorySection />}
      </div>

      {/* Navigation */}
      <div style={{ padding: '14px 20px', background: '#fff', borderTop: '1px solid #e5e2dc', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
        <button onClick={() => navigate('prev')} disabled={currentStepIdx === 0}
          style={{ padding: '9px 18px', background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, fontSize: 13, cursor: currentStepIdx === 0 ? 'not-allowed' : 'pointer', color: currentStepIdx === 0 ? '#ccc' : '#666' }}>
          ← Back
        </button>

        <div style={{ fontSize: 12, color: '#888' }}>
          {step === 'inventory' ? (
            <span>Archive inventory — showing archived items</span>
          ) : (
            <span>{STEP_LABELS[step]}</span>
          )}
        </div>

        {step !== 'inventory' ? (
          <button onClick={() => navigate('next')}
            disabled={!canGoNext() && step !== 'listing'}
            style={{ padding: '9px 20px', background: canGoNext() ? '#06b6d4' : '#e5e2dc', color: '#fff', border: 'none', borderRadius: 10, fontSize: 13, fontWeight: 600, cursor: canGoNext() ? 'pointer' : 'not-allowed', display: 'flex', alignItems: 'center', gap: 6 }}>
            {step === 'condition' || step === 'pricing' ? 'Save & Continue →' : step === 'listing' ? 'Done' : <><ArrowRight size={14} /> Next</>}
          </button>
        ) : (
          <button onClick={() => setStep('start')}
            style={{ padding: '9px 18px', background: '#06b6d4', color: '#fff', border: 'none', borderRadius: 10, fontSize: 13, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Plus size={14} /> New Intake
          </button>
        )}
      </div>
    </div>
  );
}
