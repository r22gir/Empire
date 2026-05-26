'use client';
import { useState, useEffect, useCallback } from 'react';
import { HardDrive, Play, Square, RefreshCw, Loader2, Search, ChevronLeft, ChevronRight, Check, X } from 'lucide-react';
import { API } from '../../lib/api';

interface MiniMaxAnalysis {
  analysis_status: string;
  provider: string;
  model: string;
  transport?: string;
  timestamp: string;
  stale: boolean;
  description: string;
  tags: string[];
  personal_work_classification: {
    classification: string;
    confidence: number;
    reason: string;
  };
  business_route: string;
  action_recommendation: string;
  image_quality_score: number;
  analysis_confidence: number;
  needs_manual_review: boolean;
  reason_for_manual_review: string | null;
}

interface MiniMaxQuotaStatus {
  recoveryforge_vision_bucket: string;
  recoveryforge_window_cap: number;
  recoveryforge_daily_soft_cap: number;
  current_window_used_by_recoveryforge: number;
  current_window_remaining_for_recoveryforge: number;
  current_window_reserved_for_general_use: number;
  daily_used_by_recoveryforge: number;
  daily_remaining_soft_cap: number;
  image_generation_bucket_total: number;
  image_generation_used_by_recoveryforge_batch: number;
  image_generation_reserved_for_quotes_and_mockups: boolean;
  recoveryforge_manual_mockup_cap: number;
  batch_chunk_limit: number;
  cap_reached: boolean;
  override_enabled: boolean;
  reset_window_hint: string;
  window_start_utc: string;
  server_date: string;
}

interface RecoveryStatus {
  total_images: number;
  processed: number;
  percentage: number;
  running: boolean;
  categories: Record<string, number>;
  stats?: Record<string, number>;
  index_file?: string;
  progress_file?: string;
  classified_dir?: string;
  minimax_quota?: MiniMaxQuotaStatus;
}

interface RecoveryImage {
  record_key: string;
  filename: string;
  image_url?: string;
  business: string;
  pre_tag: string;
  category: string;
  description: string;
  ocr_text?: string;
  quality: string;
  social_ready: boolean;
  in_social: boolean;
  reviewed: boolean;
  review_status: string;
  scrapped?: boolean;
  confidence?: number;
  classified_by: string;
  classified_path?: string;
  classified_exists?: boolean;
  classified_readable?: boolean;
  social_path?: string;
  social_exists?: boolean;
  path?: string;
  source_path?: string;
  source_exists?: boolean;
  source_readable?: boolean;
  minimax_analysis?: MiniMaxAnalysis;
  analysis_stale?: boolean;
  analysis_provider?: string;
  analysis_confidence?: number;
  needs_manual_review?: boolean;
  analyzed_at?: string;
  last_error?: string;
  // Phase 2B-A/B tag arrays
  object_tags?: string[];
  room_tags?: string[];
  material_tags?: string[];
  style_tags?: string[];
  people_tags?: string[];
  pet_tags?: string[];
  campaign_tags?: string[];
  business_domains?: string[];
  asset_tags?: string[];
  tags_manually_edited?: boolean;
  tags_updated_at?: string;
  tags_updated_by?: string;
}

interface ImageDetail {
  image: RecoveryImage;
  raw_metadata: Record<string, unknown>;
  tags: Record<string, unknown>;
  ocr_text?: string;
  minimax_analysis?: MiniMaxAnalysis;
  path_status?: Record<string, { path?: string | null; exists: boolean; readable: boolean; is_file: boolean; size_bytes?: number | null }>;
}

const BUSINESS_FILTERS = ['all', 'empire-workroom', 'woodcraft', 'general'];
const STATUS_FILTERS = [
  { value: 'all', label: 'All reviewed states' },
  { value: 'ambiguous', label: 'Ambiguous' },
  { value: 'personal', label: 'Personal' },
  { value: 'low_confidence', label: 'Low confidence' },
  { value: 'reviewed', label: 'Reviewed' },
  { value: 'unreviewed', label: 'Unreviewed' },
  { value: 'active', label: 'Active only' },
  { value: 'scrapped', label: 'Scrapped' },
];

function confidenceLabel(confidence: number | undefined) {
  if (confidence === undefined || confidence === null) return null;
  const pct = Math.round(confidence * 100);
  let level = 'low';
  let color = '#dc2626';
  if (confidence >= 0.85) { level = 'high'; color = '#16a34a'; }
  else if (confidence >= 0.65) { level = 'medium'; color = '#d97706'; }
  return { pct, level, color };
}

export default function RecoveryForgeScreen() {
  const [status, setStatus] = useState<RecoveryStatus | null>(null);
  const [images, setImages] = useState<RecoveryImage[]>([]);
  const [imageTotal, setImageTotal] = useState(0);
  const [completeness, setCompleteness] = useState<Record<string, number>>({});
  const [facets, setFacets] = useState<Record<string, Record<string, number>>>({});
  const [selected, setSelected] = useState<ImageDetail | null>(null);
  const [selectedLoading, setSelectedLoading] = useState(false);
  const [businessFilter, setBusinessFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [socialReady, setSocialReady] = useState('all');
  const [minConfidence, setMinConfidence] = useState('');
  const [sort, setSort] = useState('classified_at_desc');
  const [search, setSearch] = useState('');
  const [offset, setOffset] = useState(0);
  const [limit, setLimit] = useState(72);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [detailActionLoading, setDetailActionLoading] = useState(false);
  const [detailMessage, setDetailMessage] = useState<string | null>(null);
  const [customCategories, setCustomCategories] = useState<{slug: string; label: string; kind: string; source: string}[]>([]);
  const [addingCategory, setAddingCategory] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState('');
  const [scrapDialogOpen, setScrapDialogOpen] = useState(false);
  const [scrapMode, setScrapMode] = useState<'soft_delete' | 'delete_classified' | 'delete_all_copies'>('soft_delete');
  const [scrapReason, setScrapReason] = useState('unrelated');
  const [scrapConfirmText, setScrapConfirmText] = useState('');
  const [tagCategoryFilter, setTagCategoryFilter] = useState('all');
  const [tagFilterValue, setTagFilterValue] = useState('');

  const apiBase = API.replace('/api/v1', '');

  const fetchImages = useCallback(async () => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset), analyzed_only: 'true', sort });
    if (businessFilter !== 'all') params.set('business', businessFilter);
    if (categoryFilter !== 'all') params.set('category', categoryFilter);
    if (statusFilter !== 'all') params.set('status', statusFilter);
    if (socialReady !== 'all') params.set('social_ready', socialReady);
    if (minConfidence.trim()) params.set('min_confidence', minConfidence.trim());
    if (search.trim()) params.set('q', search.trim());
    if (tagCategoryFilter !== 'all' && tagFilterValue.trim()) {
      params.set('tag_category', tagCategoryFilter);
      params.set('tag', tagFilterValue.trim());
    }
    const res = await fetch(`${API}/recovery/images?${params.toString()}`);
    if (!res.ok) return;
    const data = await res.json();
    setImages(data.images || []);
    setImageTotal(data.total || 0);
    setCompleteness(data.completeness || {});
    setFacets(data.facets || {});
    setHasMore(Boolean(data.has_more));
  }, [businessFilter, categoryFilter, limit, minConfidence, offset, search, socialReady, sort, statusFilter, tagCategoryFilter, tagFilterValue]);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/recovery/status`);
      if (res.ok) setStatus(await res.json());
    } catch {
      // Backend status panel remains best-effort.
    }
    setLoading(false);
  }, []);

  const loadDetail = useCallback(async (image: RecoveryImage) => {
    setSelectedLoading(true);
    setDetailMessage(null);
    try {
      const res = await fetch(`${API}/recovery/images/${image.record_key}`);
      if (res.ok) setSelected(await res.json());
    } finally {
      setSelectedLoading(false);
    }
  }, []);

  const fetchCustomCategories = useCallback(async () => {
    try {
      const res = await fetch(`${API}/recovery/categories`);
      if (res.ok) {
        const data = await res.json();
        setCustomCategories(data.categories || []);
      }
    } catch {
      // categories load best-effort
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchCustomCategories();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus, fetchCustomCategories]);

  useEffect(() => {
    fetchImages().catch(() => {});
  }, [fetchImages]);

  const resetPaging = (fn: () => void) => {
    setOffset(0);
    fn();
  };

  const handleAction = async (action: 'start' | 'stop') => {
    setActionLoading(true);
    try {
      await fetch(`${API}/recovery/${action}`, { method: 'POST' });
      setTimeout(fetchStatus, 2000);
    } finally {
      setActionLoading(false);
    }
  };

  const reviewSelected = async (review_status: 'approved' | 'rejected' | 'reviewed') => {
    if (!selected) return;
    const image = selected.image;
    setDetailActionLoading(true);
    setDetailMessage(null);
    try {
      const res = await fetch(`${API}/recovery/images/${image.record_key}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          business: image.business,
          category: image.category,
          review_status,
          social_ready: review_status === 'approved' ? true : image.social_ready,
          copy_to_classified: true,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        await loadDetail(data.image);
        await fetchImages();
        setDetailMessage(`Selected image ${review_status}.`);
      } else {
        setDetailMessage(`Review update failed (${res.status}).`);
      }
    } finally {
      setDetailActionLoading(false);
    }
  };

  const createCustomCategory = async () => {
    const label = newCategoryName.trim();
    if (!label) return;
    setDetailActionLoading(true);
    try {
      const res = await fetch(`${API}/recovery/categories`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label, kind: 'category' }),
      });
      const data = await res.json();
      if (res.ok) {
        await fetchCustomCategories();
        setAddingCategory(false);
        setNewCategoryName('');
        if (selected) updateSelected('category', data.entry.label);
        setDetailMessage(`Category '${label}' created and selected.`);
      } else {
        setDetailMessage(`Failed to create category: ${typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)}`);
      }
    } finally {
      setDetailActionLoading(false);
    }
  };

  const scrapSelected = async () => {
    if (!selected) return;
    setDetailActionLoading(true);
    setDetailMessage(null);
    try {
      const payload: Record<string, unknown> = { mode: scrapMode, reason: scrapReason };
      if (scrapMode === 'delete_all_copies') {
        payload.confirm = true;
        payload.confirm_text = scrapConfirmText;
      }
      const res = await fetch(`${API}/recovery/images/${selected.image.record_key}/scrap`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.ok && data.status === 'scrapped') {
        setScrapDialogOpen(false);
        setScrapConfirmText('');
        await loadDetail(data.image);
        await fetchImages();
        setDetailMessage(`Image scrapped (${scrapMode}).`);
      } else {
        const err = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
        setDetailMessage(`Scrap failed: ${err}`);
      }
    } finally {
      setDetailActionLoading(false);
    }
  };

  const updateSelected = (key: 'business' | 'category', value: string) => {
    if (!selected) return;
    setSelected({ ...selected, image: { ...selected.image, [key]: value } });
  };

  const reanalyzeSelected = async () => {
    if (!selected) return;
    setDetailActionLoading(true);
    setDetailMessage('Re-analyzing selected image through MiniMax mmx vision...');
    try {
      const res = await fetch(`${API}/recovery/images/${selected.image.record_key}/reanalyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force: true }),
      });
      const data = await res.json().catch(() => null);
      if (res.ok && data?.image) {
        await loadDetail(data.image);
        await fetchImages();
        setDetailMessage(data.success ? 'MiniMax mmx vision re-analysis complete.' : `Re-analysis failed: ${data.analysis?.error || data.message || 'unknown error'}`);
      } else {
        const message = typeof data?.detail === 'string' ? data.detail : data?.detail?.error || data?.message || `HTTP ${res.status}`;
        setDetailMessage(`Re-analysis failed: ${message}`);
      }
    } finally {
      setDetailActionLoading(false);
    }
  };

  const saveSelectedTags = async (tagPayload: Record<string, string[]>) => {
    if (!selected) return;
    setDetailActionLoading(true);
    setDetailMessage(null);
    try {
      const res = await fetch(`${API}/recovery/images/${selected.image.record_key}/tags`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tagPayload),
      });
      const data = await res.json().catch(() => null);
      if (res.ok && data?.image) {
        await loadDetail(data.image);
        setDetailMessage(data.rejected_tags?.length ? `Tags saved. Rejected: ${data.rejected_tags.join(', ')}` : 'Tags saved.');
      } else {
        const msg = typeof data?.detail === 'string' ? data.detail : JSON.stringify(data?.detail);
        setDetailMessage(`Tag save failed: ${msg}`);
      }
    } finally {
      setDetailActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin" size={20} style={{ color: '#b8960c' }} />
      </div>
    );
  }

  const shownEnd = Math.min(offset + images.length, imageTotal);
  const facetCategories = Object.keys(facets.category || {}).sort();
  const customCategoryLabels = customCategories.filter(c => c.kind === 'category').map(c => c.label);
  const allCategoryOptions = Array.from(new Set([...facetCategories, ...customCategoryLabels])).sort();

  const classifierLabel = (classified_by: string | undefined) => {
    if (!classified_by || classified_by === 'none') return 'Unclassified';
    if (classified_by.startsWith('ollama-')) {
      const model = classified_by.replace('ollama-', '');
      if (model === 'moondream') return 'Moondream (Ollama)';
      if (model === 'llava') return 'LLaVA (Ollama)';
      return `${model} (Ollama)`;
    }
    return classified_by;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="flex flex-wrap items-center gap-3 px-4 sm:px-5 py-3" style={{ background: '#faf9f7', borderBottom: '1px solid #ece8e0', flexShrink: 0 }}>
        <HardDrive size={20} style={{ color: '#b8960c' }} />
        <h2 className="text-sm sm:text-base" style={{ fontWeight: 700, color: '#1a1a1a', margin: 0 }}>RecoveryForge Workbench</h2>
        {status && (
          <>
            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12, fontSize: 12, color: '#666' }}>
              <span style={{ padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600, background: status.running ? '#dcfce7' : '#fef2f2', color: status.running ? '#16a34a' : '#dc2626' }}>
                {status.running ? 'Running' : 'Stopped'}
              </span>
              <span>{status.processed.toLocaleString()} / {status.total_images.toLocaleString()} images ({status.percentage}%)</span>
            </div>
            {status.minimax_quota && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: '#888', padding: '4px 10px', background: status.minimax_quota.cap_reached ? '#fef2f2' : '#f0f9ff', borderRadius: 8, border: '1px solid', borderColor: status.minimax_quota.cap_reached ? '#fecaca' : '#bae6fd' }}>
                <span style={{ fontWeight: 700 }}>Vision:</span>
                <span>{status.minimax_quota.current_window_used_by_recoveryforge}/{status.minimax_quota.recoveryforge_window_cap}</span>
                <span style={{ color: '#999' }}>|</span>
                <span>{status.minimax_quota.current_window_remaining_for_recoveryforge} left</span>
                <span style={{ color: '#999' }}>|</span>
                <span style={{ fontWeight: 700 }}>Reserve:</span>
                <span>{status.minimax_quota.current_window_reserved_for_general_use} general-use</span>
                <span style={{ color: '#999' }}>|</span>
                <span style={{ color: status.minimax_quota.image_generation_reserved_for_quotes_and_mockups ? '#16a34a' : '#d97706', fontWeight: 700 }}>
                  {status.minimax_quota.image_generation_reserved_for_quotes_and_mockups ? 'IMG gen protected' : 'IMG gen exposed'}
                </span>
                {status.minimax_quota.cap_reached && <span style={{ color: '#dc2626', fontWeight: 700 }}> CAP REACHED</span>}
              </div>
            )}
            <button onClick={() => handleAction(status.running ? 'stop' : 'start')} disabled={actionLoading} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 8, border: 'none', background: status.running ? '#dc2626' : '#16a34a', color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer', opacity: actionLoading ? 0.6 : 1, minHeight: 44 }}>
              {actionLoading ? <Loader2 size={14} className="animate-spin" /> : status.running ? <Square size={14} /> : <Play size={14} />}
              {status.running ? 'Stop' : 'Start'}
            </button>
          </>
        )}
        <button onClick={() => { fetchStatus(); fetchImages(); }} style={{ background: 'none', border: '1px solid #ece8e0', borderRadius: 8, padding: '6px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
          <RefreshCw size={14} style={{ color: '#999' }} />
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: selected ? 'minmax(0, 1fr) minmax(340px, 400px)' : '1fr', gap: 12, minHeight: 0, flex: 1 }}>
        <div style={{ overflowY: 'auto', padding: 18, minWidth: 0 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 10, marginBottom: 14 }}>
            {[
              ['Analyzed', completeness.analyzed],
              ['Remaining', completeness.remaining],
              ['Low confidence', completeness.low_confidence],
              ['Ambiguous', completeness.ambiguous],
              ['Social-ready', completeness.social_ready],
              ['Reviewed', completeness.reviewed],
            ].map(([label, value]) => (
              <div key={String(label)} style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 8, padding: 12 }}>
                <div style={{ fontSize: 10, color: '#888', fontWeight: 800, textTransform: 'uppercase' }}>{label}</div>
                <div style={{ fontSize: 22, fontWeight: 900, color: '#1a1a1a', marginTop: 4 }}>{Number(value || 0).toLocaleString()}</div>
              </div>
            ))}
          </div>

          <div style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 8, padding: 12, marginBottom: 14 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
              <div style={{ position: 'relative', flex: '1 1 260px' }}>
                <Search size={13} style={{ position: 'absolute', left: 9, top: 10, color: '#999' }} />
                <input value={search} onChange={e => resetPaging(() => setSearch(e.target.value))} placeholder="Search filename, tag, path, description" style={{ width: '100%', padding: '8px 10px 8px 28px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12 }} />
              </div>
              <select value={businessFilter} onChange={e => resetPaging(() => setBusinessFilter(e.target.value))} style={selectStyle}>
                {BUSINESS_FILTERS.map(f => <option key={f} value={f}>{f === 'all' ? 'All business' : f}</option>)}
              </select>
              <select value={categoryFilter} onChange={e => resetPaging(() => setCategoryFilter(e.target.value))} style={selectStyle}>
                <option value="all">All categories</option>
                {allCategoryOptions.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
              <select value={statusFilter} onChange={e => resetPaging(() => setStatusFilter(e.target.value))} style={selectStyle}>
                {STATUS_FILTERS.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
              </select>
              <select value={socialReady} onChange={e => resetPaging(() => setSocialReady(e.target.value))} style={selectStyle}>
                <option value="all">Social-ready: all</option>
                <option value="true">Social-ready only</option>
                <option value="false">Not social-ready</option>
              </select>
              <input value={minConfidence} onChange={e => resetPaging(() => setMinConfidence(e.target.value))} placeholder="Min confidence" style={{ ...selectStyle, width: 120 }} />
              <select value={sort} onChange={e => resetPaging(() => setSort(e.target.value))} style={selectStyle}>
                <option value="classified_at_desc">Newest analyzed</option>
                <option value="confidence_asc">Confidence low-high</option>
                <option value="confidence_desc">Confidence high-low</option>
                <option value="filename_asc">Filename A-Z</option>
              </select>
              <select value={limit} onChange={e => resetPaging(() => setLimit(Number(e.target.value)))} style={selectStyle}>
                {[36, 72, 120].map(n => <option key={n} value={n}>{n} per page</option>)}
              </select>
              <select value={tagCategoryFilter} onChange={e => resetPaging(() => setTagCategoryFilter(e.target.value))} style={selectStyle}>
                <option value="all">Tag: all</option>
                {['object_tags','room_tags','material_tags','style_tags','people_tags','pet_tags','campaign_tags','business_domains','asset_tags'].map(t => <option key={t} value={t}>{t}</option>)}
              </select>
              {tagCategoryFilter !== 'all' && (
                <div style={{ display: 'flex', gap: 4 }}>
                  <input
                    value={tagFilterValue}
                    onChange={e => resetPaging(() => setTagFilterValue(e.target.value))}
                    placeholder="tag value"
                    style={{ ...selectStyle, width: 110 }}
                    onKeyDown={e => { if (e.key === 'Escape') { setTagFilterValue(''); setTagCategoryFilter('all'); } }}
                  />
                  {tagFilterValue && (
                    <button onClick={() => resetPaging(() => { setTagFilterValue(''); setTagCategoryFilter('all'); })} style={{ ...actionButtonStyle, fontSize: 10, padding: '8px 6px' }}>✕ clear</button>
                  )}
                </div>
              )}
            </div>
            <div style={{ marginTop: 9, fontSize: 11, color: '#777' }}>
              Showing {imageTotal ? offset + 1 : 0}-{shownEnd} of {imageTotal.toLocaleString()} filtered analyzed records from {status?.index_file || '/data/images/presorted_inventory.json'}
            </div>
          </div>

          {images.length > 0 ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
              {images.map((img) => (
                <button key={img.record_key} onClick={() => loadDetail(img)} style={{ textAlign: 'left', background: selected?.image.record_key === img.record_key ? '#fdf8eb' : '#fff', border: selected?.image.record_key === img.record_key ? '1.5px solid #b8960c' : '1px solid #ece8e0', borderRadius: 8, overflow: 'hidden', padding: 0, cursor: 'pointer' }}>
                  {img.image_url ? <img src={`${apiBase}${img.image_url}`} alt={img.filename} style={{ width: '100%', height: 150, objectFit: 'cover', background: '#f5f3ef' }} /> : <div style={{ height: 150, background: '#f5f3ef' }} />}
                  <div style={{ padding: 10 }}>
                    <div title={img.filename} style={{ fontSize: 12, fontWeight: 800, color: '#1a1a1a', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{img.filename}</div>
                    <TagRow img={img} />
                    <div style={{ fontSize: 11, color: '#555', minHeight: 42, lineHeight: 1.35 }}>{img.description || 'No generated description stored.'}</div>
                    <div style={{ marginTop: 8, fontSize: 10, color: '#999' }}>{classifierLabel(img.classified_by)}{img.reviewed ? ' · reviewed' : ''}{img.in_social ? ' · social asset' : ''}</div>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div style={{ padding: 40, textAlign: 'center', color: '#999', background: '#fff', border: '1px solid #ece8e0', borderRadius: 8 }}>No analyzed RecoveryForge images matched the current filters.</div>
          )}

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16 }}>
            <button onClick={() => setOffset(Math.max(0, offset - limit))} disabled={offset === 0} style={pageButtonStyle}><ChevronLeft size={14} /> Previous</button>
            <button onClick={() => setOffset(offset + limit)} disabled={!hasMore} style={pageButtonStyle}>Next <ChevronRight size={14} /></button>
          </div>
        </div>

        {selected && (
          <aside style={{ borderLeft: '1px solid #ece8e0', background: '#fff', overflowY: 'auto', padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center', marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 900, color: '#1a1a1a' }}>Image Detail</div>
                <div style={{ fontSize: 10, color: '#888' }}>{selected.image.record_key}</div>
              </div>
              <button onClick={() => setSelected(null)} style={{ border: '1px solid #ece8e0', background: '#fff', borderRadius: 8, padding: 7, cursor: 'pointer' }}><X size={14} /></button>
            </div>
            {selectedLoading ? <Loader2 className="animate-spin" size={18} /> : (
              <>
                {selected.image.image_url && <img src={`${apiBase}${selected.image.image_url}`} alt={selected.image.filename} style={{ width: '100%', maxHeight: 360, objectFit: 'contain', background: '#f5f3ef', borderRadius: 8, border: '1px solid #ece8e0' }} />}
                <h3 style={{ fontSize: 15, fontWeight: 900, margin: '12px 0 6px', wordBreak: 'break-word' }}>{selected.image.filename}</h3>
                <TagRow img={selected.image} />
                {(() => { const c = confidenceLabel(selected.image.confidence); return c ? (
                    <div style={{ marginTop: 8, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                      <span style={{ fontSize: 10, color: '#888', fontWeight: 700, textTransform: 'uppercase' }}>Classifier:</span>
                      <span style={{ fontSize: 11, color: '#333' }}>{classifierLabel(selected.image.classified_by)}</span>
                      <span style={{ fontSize: 9, padding: '2px 7px', borderRadius: 6, background: '#eff6ff', color: c.color, fontWeight: 800 }}>
                        {c.pct}% confidence ({c.level})
                      </span>
                      <span style={{ fontSize: 10, color: '#aaa' }}>{selected.image.reviewed ? '· reviewed' : '· unreviewed'}</span>
                    </div>
                  ) : null; })()}
                <DetailLabel label="Generated description" value={selected.image.description || 'No generated description stored.'} />
                <DetailLabel label="OCR text" value={selected.ocr_text || 'No OCR text stored in this record.'} />
                <DetailLabel label="Source path" value={selected.image.source_path || selected.image.path || 'Not stored'} mono />
                <PathBadge exists={selected.image.source_exists} readable={selected.image.source_readable} />
                <DetailLabel label="Classified path" value={selected.image.classified_path || 'Not copied to classified bucket'} mono />
                <PathBadge exists={selected.image.classified_exists} readable={selected.image.classified_readable} />
                <DetailLabel label="Social path" value={selected.image.social_path || 'Not approved as social asset'} mono />
                <PathBadge exists={selected.image.social_exists} readable={selected.image.social_exists} />
                <DetailLabel label="Provider / model" value={`${selected.image.analysis_provider || selected.minimax_analysis?.provider || selected.image.classified_by || 'none'}${selected.minimax_analysis?.model ? ` / ${selected.minimax_analysis.model}` : ''}${selected.minimax_analysis?.transport ? ` / ${selected.minimax_analysis.transport}` : ''}`} />
                <DetailLabel label="Last analyzed" value={selected.image.analyzed_at || selected.minimax_analysis?.timestamp || 'No analysis timestamp stored.'} />
                {selected.image.last_error && <DetailLabel label="Last analysis error" value={selected.image.last_error} />}
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
                  <a href={`${API}/recovery/images/${selected.image.record_key}/file?variant=source`} target="_blank" rel="noreferrer" style={{ ...linkButtonStyle, pointerEvents: selected.image.source_exists ? 'auto' : 'none', opacity: selected.image.source_exists ? 1 : 0.45 }}>Open original</a>
                  <a href={`${API}/recovery/images/${selected.image.record_key}/file?variant=classified`} target="_blank" rel="noreferrer" style={{ ...linkButtonStyle, pointerEvents: selected.image.classified_exists ? 'auto' : 'none', opacity: selected.image.classified_exists ? 1 : 0.45 }}>Open classified copy</a>
                </div>
                {detailMessage && (
                  <div style={{ marginTop: 10, padding: 8, borderRadius: 8, border: '1px solid #e5e2dc', background: '#faf9f7', fontSize: 11, color: detailMessage.includes('failed') ? '#b91c1c' : '#374151' }}>
                    {detailMessage}
                  </div>
                )}

                <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid #ece8e0' }}>
                  <div style={{ fontSize: 12, fontWeight: 900, marginBottom: 8 }}>Asset Tags</div>
                  <AssetTagsPanel img={selected.image} onSave={saveSelectedTags} />
                  <div style={{ fontSize: 10, color: '#888', marginTop: 4 }}>
                    {selected.image.tags_manually_edited ? `Manually edited · ${selected.image.tags_updated_at ? new Date(selected.image.tags_updated_at).toLocaleString() : ''}` : 'Tags are auto-extracted from image description and can be manually edited.'}
                  </div>
                </div>

                <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid #ece8e0' }}>
                  <div style={{ fontSize: 12, fontWeight: 900, marginBottom: 8 }}>Review Actions</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    <select value={selected.image.business} onChange={e => updateSelected('business', e.target.value)} style={selectStyle}>
                      {['empire-workroom', 'woodcraft', 'general', 'personal', 'ambiguous'].map(v => <option key={v} value={v}>{v}</option>)}
                    </select>
                    {addingCategory ? (
                      <div style={{ display: 'flex', gap: 4 }}>
                        <input
                          value={newCategoryName}
                          onChange={e => setNewCategoryName(e.target.value)}
                          placeholder="new category name"
                          style={{ ...selectStyle, flex: 1 }}
                          onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); createCustomCategory(); } if (e.key === 'Escape') { setAddingCategory(false); setNewCategoryName(''); } }}
                          autoFocus
                        />
                        <button onClick={createCustomCategory} disabled={detailActionLoading} style={{ ...actionButtonStyle, background: '#16a34a', color: '#fff', whiteSpace: 'nowrap' }}>Add</button>
                        <button onClick={() => { setAddingCategory(false); setNewCategoryName(''); }} style={{ ...actionButtonStyle }}>✕</button>
                      </div>
                    ) : (
                      <div style={{ display: 'flex', gap: 4 }}>
                        <input value={selected.image.category || ''} onChange={e => updateSelected('category', e.target.value)} placeholder="category" style={{ ...selectStyle, flex: 1 }} />
                        <button onClick={() => { setAddingCategory(true); setNewCategoryName(''); }} style={{ ...actionButtonStyle, fontSize: 11, padding: '8px 6px' }}>+ Add</button>
                      </div>
                    )}
                    <button onClick={reanalyzeSelected} disabled={detailActionLoading} style={{ ...actionButtonStyle, gridColumn: '1 / -1', background: '#1f2937', color: '#fff', opacity: detailActionLoading ? 0.65 : 1 }}><RefreshCw size={13} /> Re-analyze selected</button>
                    <button onClick={() => reviewSelected('approved')} disabled={detailActionLoading} style={{ ...actionButtonStyle, background: '#16a34a', color: '#fff', opacity: detailActionLoading ? 0.65 : 1 }}><Check size={13} /> Approve</button>
                    <button onClick={() => reviewSelected('rejected')} disabled={detailActionLoading} style={{ ...actionButtonStyle, background: '#dc2626', color: '#fff', opacity: detailActionLoading ? 0.65 : 1 }}><X size={13} /> Reject</button>
                    <button onClick={() => reviewSelected('reviewed')} disabled={detailActionLoading} style={{ ...actionButtonStyle, gridColumn: '1 / -1', opacity: detailActionLoading ? 0.65 : 1 }}>Save category / reclassify</button>
                    {selected.image.scrapped ? (
                      <div style={{ gridColumn: '1 / -1', padding: '8px 12px', borderRadius: 8, background: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', fontSize: 11, textAlign: 'center' }}>This image is scrapped</div>
                    ) : (
                      <button onClick={() => { setScrapDialogOpen(true); }} disabled={detailActionLoading} style={{ ...actionButtonStyle, gridColumn: '1 / -1', color: '#dc2626', opacity: detailActionLoading ? 0.65 : 1 }}>Scrap selected</button>
                    )}
                  </div>
                  <div style={{ marginTop: 8, fontSize: 10, color: '#888' }}>Reclassify updates the JSON index and safely copies to the selected classified bucket when supported. It does not delete the old source file.</div>
                </div>

                {selected.minimax_analysis && (
                  <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid #ece8e0' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <div style={{ fontSize: 12, fontWeight: 900 }}>MiniMax Analysis</div>
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        {selected.minimax_analysis.stale && (
                          <span style={{ fontSize: 9, padding: '2px 7px', borderRadius: 6, background: '#fef3c7', color: '#92400e', fontWeight: 800 }}>STALE</span>
                        )}
                        <span style={{ fontSize: 9, padding: '2px 7px', borderRadius: 6, background: '#f0f9ff', color: '#0369a1', fontWeight: 700 }}>
                          {selected.minimax_analysis.model}
                        </span>
                      </div>
                    </div>

                    <div style={{ fontSize: 10, color: '#666', lineHeight: 1.5, marginBottom: 8, padding: 8, background: '#faf9f7', borderRadius: 6, border: '1px solid #ece8e0' }}>
                      {selected.minimax_analysis.description || 'No description generated.'}
                    </div>

                    {selected.minimax_analysis.tags && selected.minimax_analysis.tags.length > 0 && (
                      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', marginBottom: 8 }}>
                        {selected.minimax_analysis.tags.map(tag => (
                          <span key={tag} style={{ fontSize: 9, padding: '2px 7px', borderRadius: 6, background: '#f5f3ef', color: '#666', border: '1px solid #e5e2dc' }}>{tag}</span>
                        ))}
                      </div>
                    )}

                    {selected.minimax_analysis.personal_work_classification && (
                      <div style={{ fontSize: 10, marginBottom: 4 }}>
                        <span style={{ color: '#888', fontWeight: 700 }}>Personal/Work: </span>
                        <span style={{ fontWeight: 800, color: selected.minimax_analysis.personal_work_classification.classification === 'work_related' ? '#16a34a' : selected.minimax_analysis.personal_work_classification.classification === 'personal' ? '#7c3aed' : '#d97706' }}>
                          {selected.minimax_analysis.personal_work_classification.classification}
                        </span>
                        <span style={{ color: '#aaa', marginLeft: 6 }}>{Math.round(selected.minimax_analysis.personal_work_classification.confidence * 100)}%</span>
                      </div>
                    )}

                    {selected.minimax_analysis.business_route && (
                      <div style={{ fontSize: 10, marginBottom: 4 }}>
                        <span style={{ color: '#888', fontWeight: 700 }}>Routes to: </span>
                        <span style={{ fontWeight: 800, color: '#b8960c' }}>{selected.minimax_analysis.business_route}</span>
                      </div>
                    )}

                    {selected.minimax_analysis.action_recommendation && (
                      <div style={{ fontSize: 10, marginBottom: 4 }}>
                        <span style={{ color: '#888', fontWeight: 700 }}>Action: </span>
                        <span style={{ fontWeight: 700, color: '#374151' }}>{selected.minimax_analysis.action_recommendation}</span>
                      </div>
                    )}

                    {selected.minimax_analysis.image_quality_score != null && (
                      <div style={{ fontSize: 10, marginBottom: 4 }}>
                        <span style={{ color: '#888', fontWeight: 700 }}>Quality: </span>
                        <span style={{ fontWeight: 800, color: selected.minimax_analysis.image_quality_score < 6 ? '#dc2626' : '#16a34a' }}>
                          {selected.minimax_analysis.image_quality_score}/10
                        </span>
                      </div>
                    )}

                    {selected.minimax_analysis.needs_manual_review && (
                      <div style={{ marginTop: 6, padding: 6, background: '#fef2f2', borderRadius: 6, border: '1px solid #fecaca', fontSize: 10, color: '#dc2626' }}>
                        Needs manual review{selected.minimax_analysis.reason_for_manual_review ? `: ${selected.minimax_analysis.reason_for_manual_review}` : ''}
                      </div>
                    )}
                  </div>
                )}

                <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid #ece8e0' }}>
                  <div style={{ fontSize: 12, fontWeight: 900, marginBottom: 8 }}>Raw Metadata JSON</div>
                  <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 10, background: '#111827', color: '#e5e7eb', borderRadius: 8, padding: 10, maxHeight: 320, overflow: 'auto' }}>{JSON.stringify(selected.raw_metadata, null, 2)}</pre>
                </div>
              </>
            )}
          </aside>
        )}
      </div>
    </div>
  );
}

const TAG_CATEGORY_GROUPS: { label: string; key: keyof RecoveryImage; bg: string; color: string }[] = [
  { label: 'Biz domain', key: 'business_domains', bg: '#fdf8eb', color: '#96750a' },
  { label: 'Objects',    key: 'object_tags',      bg: '#eff6ff', color: '#1d4ed8' },
  { label: 'Room',       key: 'room_tags',        bg: '#f0fdf4', color: '#15803d' },
  { label: 'Material',   key: 'material_tags',    bg: '#fef9e7', color: '#b45309' },
  { label: 'Style',      key: 'style_tags',        bg: '#fdf2f8', color: '#9d174d' },
  { label: 'People',    key: 'people_tags',        bg: '#f5f3ff', color: '#6d28d9' },
  { label: 'Pets',       key: 'pet_tags',          bg: '#ecfdf5', color: '#047857' },
  { label: 'Campaign',  key: 'campaign_tags',     bg: '#fff7ed', color: '#c2410c' },
  { label: 'Asset',     key: 'asset_tags',         bg: '#fafafa', color: '#374151' },
];

function AssetTagsPanel({ img, onSave }: { img: RecoveryImage; onSave: (payload: Record<string, string[]>) => void }) {
  const [localTags, setLocalTags] = useState<Record<string, string[]>>({});
  const [newTag, setNewTag] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    // Initialise local tag state from the current image record
    const initial: Record<string, string[]> = {};
    for (const g of TAG_CATEGORY_GROUPS) {
      const arr = img[g.key];
      initial[g.key] = Array.isArray(arr) ? [...arr] : [];
    }
    setLocalTags(initial);
    setNewTag({});
  }, [img.record_key]);

  const addTag = (key: string) => {
    const val = (newTag[key] || '').trim().toLowerCase().replace(/\s+/g, '-');
    if (!val) return;
    setLocalTags(prev => ({
      ...prev,
      [key]: prev[key] ? [...prev[key], val] : [val],
    }));
    setNewTag(prev => ({ ...prev, [key]: '' }));
  };

  const removeTag = (key: string, idx: number) => {
    setLocalTags(prev => ({
      ...prev,
      [key]: prev[key].filter((_, i) => i !== idx),
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try { await onSave(localTags); } finally { setSaving(false); }
  };

  const dirty = Object.keys(localTags).some(k =>
    JSON.stringify(localTags[k]) !== JSON.stringify(Array.isArray(img[k as keyof RecoveryImage]) ? img[k as keyof RecoveryImage] : [])
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {TAG_CATEGORY_GROUPS.map(group => {
        const tags = localTags[group.key] || [];
        return (
          <div key={group.key}>
            <div style={{ fontSize: 9, color: '#888', fontWeight: 900, textTransform: 'uppercase', marginBottom: 3 }}>
              {group.label}
            </div>
            <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
              {tags.length === 0 && (
                <span style={{ fontSize: 10, color: '#ccc' }}>—</span>
              )}
              {tags.map((tag, i) => (
                <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 10, padding: '2px 6px', borderRadius: 6, background: group.bg, color: group.color, border: `1px solid ${group.color}22` }}>
                  {tag}
                  <button onClick={() => removeTag(group.key, i)} style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, lineHeight: 1, color: group.color, opacity: 0.6, fontSize: 12 }}>✕</button>
                </span>
              ))}
              <input
                value={newTag[group.key] || ''}
                onChange={e => setNewTag(prev => ({ ...prev, [group.key]: e.target.value }))}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag(group.key); } }}
                placeholder="+ add"
                style={{ width: 60, fontSize: 10, padding: '2px 5px', border: '1px dashed #ccc', borderRadius: 4, outline: 'none' }}
              />
            </div>
          </div>
        );
      })}
      {dirty && (
        <button onClick={handleSave} disabled={saving} style={{ marginTop: 6, padding: '6px 12px', borderRadius: 8, border: 'none', background: '#16a34a', color: '#fff', fontSize: 11, fontWeight: 800, cursor: saving ? 'not-allowed' : 'pointer', opacity: saving ? 0.6 : 1 }}>
          {saving ? 'Saving…' : 'Save tags'}
        </button>
      )}
    </div>
  );
}

function TagRow({ img }: { img: RecoveryImage }) {
  return (
    <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', margin: '7px 0' }}>
      <span style={tagStyle('#fdf8eb', '#96750a')}>{img.business}</span>
      <span style={tagStyle('#f0fdf4', '#15803d')}>{img.category || 'misc'}</span>
      {(() => {
        const conf = confidenceLabel(img.confidence);
        return conf ? (
          <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 6, background: '#eff6ff', color: conf.color, fontWeight: 800 }}>
            {conf.pct}% conf ({conf.level})
          </span>
        ) : null;
      })()}
      {img.social_ready && <span style={tagStyle('#ecfdf5', '#047857')}>social-ready</span>}
      {img.review_status && img.review_status !== 'unreviewed' && <span style={tagStyle('#f5f3ff', '#6d28d9')}>{img.review_status}</span>}
    </div>
  );
}

function DetailLabel({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ marginTop: 10 }}>
      <div style={{ fontSize: 10, color: '#888', fontWeight: 900, textTransform: 'uppercase', marginBottom: 3 }}>{label}</div>
      <div style={{ fontSize: 12, color: '#333', lineHeight: 1.45, fontFamily: mono ? 'monospace' : 'inherit', wordBreak: 'break-word' }}>{value}</div>
    </div>
  );
}

function PathBadge({ exists, readable }: { exists?: boolean; readable?: boolean }) {
  const ok = Boolean(exists && readable);
  return (
    <div style={{ marginTop: 4, fontSize: 10, fontWeight: 800, color: ok ? '#15803d' : '#b91c1c' }}>
      {ok ? 'File exists and is readable' : exists ? 'File exists but is not readable' : 'File not found'}
    </div>
  );
}

const selectStyle: React.CSSProperties = {
  padding: '8px 10px',
  border: '1px solid #e5e2dc',
  borderRadius: 8,
  background: '#fff',
  fontSize: 12,
  minHeight: 36,
};

const pageButtonStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  padding: '8px 12px',
  border: '1px solid #e5e2dc',
  borderRadius: 8,
  background: '#fff',
  color: '#555',
  cursor: 'pointer',
};

const actionButtonStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 6,
  padding: '8px 10px',
  border: 'none',
  borderRadius: 8,
  background: '#f5f3ef',
  color: '#444',
  fontSize: 12,
  fontWeight: 800,
  cursor: 'pointer',
};

const linkButtonStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '7px 10px',
  border: '1px solid #e5e2dc',
  borderRadius: 8,
  background: '#fff',
  color: '#374151',
  fontSize: 11,
  fontWeight: 800,
  textDecoration: 'none',
};

function tagStyle(background: string, color: string): React.CSSProperties {
  return { fontSize: 9, padding: '2px 6px', borderRadius: 6, background, color, fontWeight: 800 };
}
