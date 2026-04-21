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

// ── Types ──────────────────────────────────────────────────────────────────────

interface LifeReferenceIssue {
  id: string;
  date: string;
  volume: number;
  issue_number: number;
  cover_subject: string;
  reference_cover_url: string;
  rarity_notes: string;
  tier_guidance: string;
  keywords: string;
  match_score?: number;
}

interface ArchiveItem {
  id: number;
  reference_issue_id: string;
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
  condition_score: number;
  has_address_label: boolean;
  is_complete: boolean;
  defects: string;
  notes: string;
  tier: string;
  rough_comp_min: number;
  rough_comp_max: number;
  sale_plan: string;
  listing_title: string;
  listing_description: string;
  item_specifics: Record<string, string>;
  batch_tag: string;
  listing_status: string;
  marketforge_listing_id: string;
  marketforge_push_status: string;
  marketforge_pushed_at: string;
  marketforge_error_message: string;
  created_at: string;
  updated_at: string;
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

interface PhotoRecord {
  id: number;
  archive_id: number;
  role: string;
  filename: string;
  original_name: string;
  file_path: string;
  created_at: string;
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

// ── Section 1: Intake / Search ────────────────────────────────────────────────

function IntakeSection({ onIdentified }: { onIdentified: (ref: LifeReferenceIssue) => void }) {
  const [q, setQ] = useState('');
  const [results, setResults] = useState<LifeReferenceIssue[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const doSearch = useCallback(async () => {
    if (!q.trim()) return;
    setLoading(true);
    try {
      const r = await fetch(`${AG_API}/reference?q=${encodeURIComponent(q)}`);
      const d = await r.json();
      setResults(d.results || []);
    } catch { setResults([]); }
    setLoading(false);
    setSearched(true);
  }, [q]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Step 1 — Identify the Issue</h2>
        <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
          Search by date, volume/issue number, or cover subject keyword. LIFE magazine ran 1936–1972.
        </p>
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <input
          value={q} onChange={e => setQ(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && doSearch()}
          placeholder="e.g. 1969 moon landing, Nov 1963, vol 11 issue 25..."
          style={{ flex: 1, padding: '10px 14px', border: '1.5px solid #e5e2dc', borderRadius: 10, fontSize: 13, outline: 'none' }}
        />
        <button onClick={doSearch} disabled={loading}
          style={{ padding: '10px 18px', background: loading ? '#9ca3af' : '#06b6d4', color: '#fff', border: 'none', borderRadius: 10, fontWeight: 600, fontSize: 13, cursor: loading ? 'wait' : 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />} Search
        </button>
      </div>

      {searched && results.length === 0 && (
        <div style={{ padding: 24, textAlign: 'center', color: '#999', background: '#fff', borderRadius: 10, border: '1px solid #e5e2dc' }}>
          No reference issues matched "{q}". Try a different date, volume, or keyword.
        </div>
      )}

      {results.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {results.map(ref => (
            <div key={ref.id} style={{
              background: '#fff', border: `1.5px solid ${ref.match_score && ref.match_score > 0.5 ? '#06b6d4' : '#e5e2dc'}`,
              borderRadius: 12, padding: 14, cursor: 'pointer',
              transition: 'all 0.15s',
            }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = '#06b6d4')}
              onMouseLeave={e => (e.currentTarget.style.borderColor = ref.match_score && ref.match_score > 0.5 ? '#06b6d4' : '#e5e2dc')}
              onClick={() => onIdentified(ref)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontWeight: 700, fontSize: 14 }}>{ref.cover_subject}</span>
                    <span style={{ fontSize: 11, padding: '2px 8px', background: '#f5f3ef', borderRadius: 6, color: '#888' }}>
                      Vol {ref.volume}, No. {ref.issue_number}
                    </span>
                    <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 6, fontWeight: 700,
                      background: TIER_COLORS[ref.tier_guidance] + '20',
                      color: TIER_COLORS[ref.tier_guidance] }}>
                      {ref.tier_guidance}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: '#888' }}>
                    {ref.date} — {ref.rarity_notes}
                  </div>
                  {ref.match_score !== undefined && (
                    <div style={{ marginTop: 4, fontSize: 11, color: ref.match_score > 0.5 ? '#16a34a' : '#888' }}>
                      Match confidence: {Math.round(ref.match_score * 100)}%
                    </div>
                  )}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <button style={{ padding: '6px 14px', background: '#06b6d4', color: '#fff', border: 'none', borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: 'pointer' }}>
                    Use This Issue
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ padding: 12, background: '#fef9ec', borderRadius: 10, border: '1px solid #fde68a', fontSize: 12, color: '#92400e' }}>
        <strong>Sample data only</strong> — Reference issues above are canonical historical examples with researched values.
        Upload your actual item photos in Step 3 before listing.
      </div>
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
              ["Volume", String(ref_issue.volume)],
              ["Issue #", String(ref_issue.issue_number)],
              ["Tier", ref_issue.tier_guidance],
              ["Match confidence", ref_issue.match_score ? `${Math.round(ref_issue.match_score * 100)}%` : 'N/A'],
            ].map(([label, value]) => (
              <div key={label}><span style={{ color: '#888' }}>{label}: </span><span style={{ fontWeight: 600 }}>{value}</span></div>
            ))}
          </div>
          <div style={{ marginTop: 10, fontSize: 12, color: '#666', fontStyle: 'italic' }}>
            "{ref_issue.rarity_notes}"
          </div>
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

function PhotoSection({
  archiveId,
  refIssue,
}: {
  archiveId: number | null;
  refIssue: LifeReferenceIssue | null;
}) {
  const [photos, setPhotos] = useState<PhotoRecord[]>([]);
  const [uploadingRole, setUploadingRole] = useState<string | null>(null);

  const loadPhotos = useCallback(async () => {
    if (!archiveId) return;
    try {
      const r = await fetch(`${AG_API}/uploads/${archiveId}`);
      const d = await r.json();
      setPhotos(d.photos || []);
    } catch { /* silent */ }
  }, [archiveId]);

  useEffect(() => { loadPhotos(); }, [loadPhotos]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>, role: string) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    if (!archiveId) return;
    setUploadingRole(role);
    for (let i = 0; i < files.length; i++) {
      const formData = new FormData();
      formData.append('file', files[i]);
      formData.append('role', role);
      try {
        await fetch(`${AG_API}/uploads/${archiveId}`, { method: 'POST', body: formData });
      } catch { /* silent */ }
    }
    await loadPhotos();
    setUploadingRole(null);
    if (e.target) e.target.value = '';
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
                  <label style={{
                    padding: '3px 8px', background: archiveId ? '#06b6d4' : '#d1d5db', color: '#fff',
                    borderRadius: 5, fontSize: 10, fontWeight: 600,
                    cursor: archiveId ? 'pointer' : 'not-allowed', display: 'flex', alignItems: 'center', gap: 4,
                  }}>
                    {isUploading ? <Loader2 size={10} className="animate-spin" /> : <Upload size={10} />} Add
                    <input type="file" accept="image/*" multiple style={{ display: 'none' }} disabled={!archiveId}
                      onChange={e => handleUpload(e, role.key)} />
                  </label>
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
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
          <div>
            <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Comp Range Min ($)</label>
            <input type="number" value={data.rough_comp_min || ''} onChange={e => update('rough_comp_min', parseFloat(e.target.value) || 0)}
              placeholder="0" style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 13 }} />
          </div>
          <div>
            <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Comp Range Max ($)</label>
            <input type="number" value={data.rough_comp_max || ''} onChange={e => update('rough_comp_max', parseFloat(e.target.value) || 0)}
              placeholder="0" style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 13 }} />
          </div>
        </div>
        <div>
          <label style={{ fontSize: 11, fontWeight: 600, color: '#666', display: 'block', marginBottom: 4 }}>Sale Plan</label>
          <input value={data.sale_plan || ''} onChange={e => update('sale_plan', e.target.value)}
            placeholder="e.g. list on eBay, list on AbeBooks, hold for convention"
            style={{ width: '100%', padding: '8px 10px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 13 }} />
        </div>
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

  const load = useCallback(async () => {
    if (!archiveId) { setLoading(false); return; }
    setLoading(true);
    try {
      const [archRes, photoRes] = await Promise.all([
        fetch(`${AG_API}/archives/${archiveId}`),
        fetch(`${AG_API}/uploads/${archiveId}`),
      ]);
      if (archRes.ok) setItem(await archRes.json());
      if (photoRes.ok) setPhotos((await photoRes.json()).photos || []);
    } catch { /* */ }
    setLoading(false);
  }, [archiveId]);

  useEffect(() => { load(); }, [load]);

  const validStatuses = ['READY_TO_LIST', 'LISTED'];
  const canPublish = item.processed_status && validStatuses.includes(item.processed_status);
  const hasTitle = !!(item.listing_title);
  const hasDescription = !!(item.listing_description);
  const hasPhotos = photos.length > 0;

  const validationErrors: string[] = [];
  if (!canPublish) validationErrors.push(`Status must be ${validStatuses.join(' or ')} (currently ${item.processed_status || 'unset'})`);
  if (!hasTitle) validationErrors.push('Listing title is blank — go back to Step 6 and save a draft');
  if (!hasDescription) validationErrors.push('Listing description is blank — go back to Step 6 and save a draft');
  if (!hasPhotos) validationErrors.push('No actual listing photos uploaded — go back to Step 3');

  const handlePublish = async () => {
    if (!archiveId) return;
    setPushState('pushing');
    setPushError('');
    setPushResult(null);
    try {
      const res = await fetch(`${AG_API}/push/${archiveId}`, { method: 'POST' });
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
        <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Step 7 — Review & Publish</h2>
        <p style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
          Review the final listing before pushing to MarketForge. Explicit action required — no auto-publish.
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
            <div style={{ fontSize: 12, fontWeight: 700, color: '#888', marginBottom: 10 }}>PUBLISH TO MARKETFORGE</div>
            <button
              onClick={handlePublish}
              disabled={pushState === 'pushing' || validationErrors.length > 0}
              style={{
                width: '100%', padding: '12px', borderRadius: 10, fontSize: 14, fontWeight: 700,
                background: validationErrors.length > 0 ? '#e5e7eb' : '#16a34a',
                color: validationErrors.length > 0 ? '#9ca3af' : '#fff',
                border: 'none', cursor: validationErrors.length > 0 || pushState === 'pushing' ? 'not-allowed' : 'pointer',
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
                <><Upload size={16} /> Publish to MarketForge</>
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

type SortKey = 'created_at' | 'processed_status' | 'source_box_code' | 'processed_box_code' | 'tier';

function InventorySection() {
  const [items, setItems] = useState<ArchiveItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<any>(null);
  const [filterStatus, setFilterStatus] = useState('all');
  const [filterTier, setFilterTier] = useState('all');
  const [filterSourceBox, setFilterSourceBox] = useState('all');
  const [filterProcessedBox, setFilterProcessedBox] = useState('all');
  const [filterListingStatus, setFilterListingStatus] = useState('all');
  const [search, setSearch] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('created_at');
  const [sortAsc, setSortAsc] = useState(false);
  const [reboxItemId, setReboxItemId] = useState<number | null>(null);
  const [reboxBox, setReboxBox] = useState('');
  const [reboxLocation, setReboxLocation] = useState('');
  const [reboxing, setReboxing] = useState(false);
  const [reboxError, setReboxError] = useState('');

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
      setStats(st);
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
    const q = search.toLowerCase();
    if (q && !item.cover_subject?.toLowerCase().includes(q) && !item.issue_date?.includes(q) && !item.source_box_code?.toLowerCase().includes(q) && !item.processed_box_code?.toLowerCase().includes(q) && !(item.listing_status || '').includes(q)) return false;
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

  const COLS: { key: keyof ArchiveItem | 'photo_count' | 'archive_location'; label: string; width: number; sortable?: boolean }[] = [
    { key: 'id', label: 'ID', width: 45 },
    { key: 'issue_date', label: 'Date', width: 88 },
    { key: 'cover_subject', label: 'Cover', width: 170 },
    { key: 'tier', label: 'Tier', width: 48, sortable: true },
    { key: 'processed_status', label: 'Status', width: 105, sortable: true },
    { key: 'photo_count', label: 'Photos', width: 62 },
    { key: 'source_box_code', label: 'Source Box', width: 92, sortable: true },
    { key: 'processed_box_code', label: 'Dest Box', width: 92, sortable: true },
    { key: 'archive_location', label: 'Location', width: 100 },
    { key: 'listing_status', label: 'Listing', width: 88 },
    { key: 'condition_score', label: 'Cond.', width: 50 },
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
        <button onClick={load} style={{ padding: '7px 12px', background: '#fff', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
          <RefreshCw size={12} /> Refresh
        </button>
      </div>

      {/* Stats row */}
      {stats && (
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {[
            { label: 'Total', value: stats.total_items, color: '#1a1a1a' },
            { label: 'Valued', value: stats.valued_items, color: '#16a34a' },
            ...Object.entries(stats.by_status || {}).map(([s, c]) => ({ label: s, value: c as number, color: STATUS_COLORS[s] || '#666' })),
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
        <span style={{ marginLeft: 'auto', fontSize: 11, color: '#888' }}>
          {sorted.length} of {items.length} items
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
                        display = <span style={{ padding: '2px 7px', borderRadius: 6, fontWeight: 600, fontSize: 10, background: count > 0 ? '#d1fae5' : '#f3f4f6', color: count > 0 ? '#065f46' : '#9ca3af' }}>{count > 0 ? `📷 ${count}` : '—'}</span>;
                      }
                      if (col.key === 'condition_score') {
                        display = val ? `${val}/5` : '—';
                      }
                      if (col.key === 'rough_comp_min' || col.key === 'rough_comp_max') {
                        display = val ? `$${Number(val).toFixed(0)}` : '—';
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
                        <div style={{ display: 'flex', gap: 4 }}>
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
    </div>
  );
}

// ── Main ArchiveForgePage ─────────────────────────────────────────────────────

type WizardStep = 'intake' | 'reference' | 'photos' | 'archive' | 'condition' | 'listing' | 'review' | 'inventory';

const STEP_ORDER: WizardStep[] = ['intake','reference','photos','archive','condition','listing','review','inventory'];
const STEP_LABELS: Record<WizardStep, string> = {
  intake: '1. Identify',
  reference: '2. Reference',
  photos: '3. Photos',
  archive: '4. Archive',
  condition: '5. Condition',
  listing: '6. Listing',
  review: '7. Review',
  inventory: 'Inventory',
};

export default function ArchiveForgePage() {
  const [step, setStep] = useState<WizardStep>('intake');
  const [refIssue, setRefIssue] = useState<LifeReferenceIssue | null>(null);
  const [archiveData, setArchiveData] = useState<Partial<ArchiveItem>>({
    processed_status: 'RAW',
    condition_score: 3,
    tier: 'C',
    is_complete: true,
    actual_listing_images: [],
  });
  const [savedArchiveId, setSavedArchiveId] = useState<number | null>(null);

  const currentStepIdx = STEP_ORDER.indexOf(step);

  const handleIdentified = (ref: LifeReferenceIssue) => {
    setRefIssue(ref);
    setArchiveData(prev => ({
      ...prev,
      reference_issue_id: ref.id,
      issue_date: ref.date,
      volume: ref.volume,
      issue_number: ref.issue_number,
      cover_subject: ref.cover_subject,
      reference_cover_url: ref.reference_cover_url,
      tier: ref.tier_guidance,
      rough_comp_min: parseFloat(ref.rarity_notes.match(/\$([\d,]+)/)?.[1]?.replace(',','') || '0') || 0,
      rough_comp_max: parseFloat(ref.rarity_notes.match(/\$([\d,]+)–?\$?([\d,]+)/)?.[2]?.replace(',','') || '0') || 0,
    }));
    setStep('reference');
  };

  // Create archive record (POST) — called when moving from reference → photos
  const handleArchiveSave = async () => {
    if (savedArchiveId) return; // already created
    try {
      const res = await fetch(`${AG_API}/archives`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...archiveData,
          actual_listing_images: [],
          has_address_label: archiveData.has_address_label || false,
          is_complete: archiveData.is_complete !== false,
        }),
      });
      if (res.ok) {
        const d = await res.json();
        setSavedArchiveId(d.id);
      }
    } catch { /* silent */ }
  };

  // Update archive record (PATCH) — called when moving from condition → listing
  const handleArchiveUpdate = async () => {
    if (!savedArchiveId) { await handleArchiveSave(); return; }
    try {
      await fetch(`${AG_API}/archives/${savedArchiveId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
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

  const navigate = (direction: 'next' | 'prev') => {
    const idx = currentStepIdx;
    if (direction === 'next' && idx < STEP_ORDER.length - 1) {
      // Create archive record when entering photos step (needed for uploads)
      if (step === 'reference') handleArchiveSave();
      // Persist condition/box data when leaving condition step
      if (step === 'condition') handleArchiveUpdate();
      setStep(STEP_ORDER[idx + 1]);
    } else if (direction === 'prev' && idx > 0) {
      // Persist condition/box data before going back
      if (step === 'listing') handleArchiveUpdate();
      setStep(STEP_ORDER[idx - 1]);
    }
  };

  const canGoNext = () => {
    if (step === 'intake') return !!refIssue;
    if (step === 'reference') return !!refIssue;
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
        {step === 'intake' && <IntakeSection onIdentified={handleIdentified} />}
        {step === 'reference' && refIssue && <ReferenceSection ref_issue={refIssue} />}
        {step === 'photos' && <PhotoSection archiveId={savedArchiveId} refIssue={refIssue} />}
        {step === 'archive' && <ArchiveSection data={archiveData} archiveId={savedArchiveId} onChange={setArchiveData} />}
        {step === 'condition' && <ConditionSection data={archiveData} onChange={setArchiveData} />}
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
            <span>Archive inventory — {savedArchiveId ? `last saved as #${savedArchiveId}` : 'no items saved yet'}</span>
          ) : (
            <span>Step {currentStepIdx + 1} of {STEP_ORDER.length - 1}: {STEP_LABELS[step]}</span>
          )}
        </div>

        {step !== 'inventory' ? (
          <button onClick={() => navigate('next')}
            disabled={!canGoNext() && step !== 'listing'}
            style={{ padding: '9px 20px', background: canGoNext() ? '#06b6d4' : '#e5e2dc', color: '#fff', border: 'none', borderRadius: 10, fontSize: 13, fontWeight: 600, cursor: canGoNext() ? 'pointer' : 'not-allowed', display: 'flex', alignItems: 'center', gap: 6 }}>
            {step === 'condition' ? 'Save & Continue →' : step === 'listing' ? 'Done' : <><ArrowRight size={14} /> Next</>}
          </button>
        ) : (
          <button onClick={() => setStep('intake')}
            style={{ padding: '9px 18px', background: '#06b6d4', color: '#fff', border: 'none', borderRadius: 10, fontSize: 13, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Plus size={14} /> New Intake
          </button>
        )}
      </div>
    </div>
  );
}
