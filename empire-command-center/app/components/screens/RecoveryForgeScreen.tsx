'use client';
import { useState, useEffect, useCallback } from 'react';
import { HardDrive, Play, Square, RefreshCw, Loader2, Search, ChevronLeft, ChevronRight, Check, X } from 'lucide-react';
import { API } from '../../lib/api';

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
  confidence?: number;
  classified_by: string;
  classified_path?: string;
  social_path?: string;
  path?: string;
}

interface ImageDetail {
  image: RecoveryImage;
  raw_metadata: Record<string, unknown>;
  tags: Record<string, unknown>;
  ocr_text?: string;
}

const BUSINESS_FILTERS = ['all', 'empire-workroom', 'woodcraft', 'general'];
const STATUS_FILTERS = [
  { value: 'all', label: 'All reviewed states' },
  { value: 'ambiguous', label: 'Ambiguous' },
  { value: 'personal', label: 'Personal' },
  { value: 'low_confidence', label: 'Low confidence' },
  { value: 'reviewed', label: 'Reviewed' },
  { value: 'unreviewed', label: 'Unreviewed' },
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
  const [serviceUp, setServiceUp] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const apiBase = API.replace('/api/v1', '');

  const fetchImages = useCallback(async () => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset), analyzed_only: 'true', sort });
    if (businessFilter !== 'all') params.set('business', businessFilter);
    if (categoryFilter !== 'all') params.set('category', categoryFilter);
    if (statusFilter !== 'all') params.set('status', statusFilter);
    if (socialReady !== 'all') params.set('social_ready', socialReady);
    if (minConfidence.trim()) params.set('min_confidence', minConfidence.trim());
    if (search.trim()) params.set('q', search.trim());
    const res = await fetch(`${API}/recovery/images?${params.toString()}`);
    if (!res.ok) return;
    const data = await res.json();
    setImages(data.images || []);
    setImageTotal(data.total || 0);
    setCompleteness(data.completeness || {});
    setFacets(data.facets || {});
    setHasMore(Boolean(data.has_more));
  }, [businessFilter, categoryFilter, limit, minConfidence, offset, search, socialReady, sort, statusFilter]);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/recovery/status`);
      if (res.ok) setStatus(await res.json());
    } catch {
      // Backend status panel remains best-effort.
    }

    try {
      const res = await fetch('http://localhost:3077', { signal: AbortSignal.timeout(3000) });
      setServiceUp(res.ok || res.status === 404);
    } catch {
      setServiceUp(false);
    }
    setLoading(false);
  }, []);

  const loadDetail = useCallback(async (image: RecoveryImage) => {
    setSelectedLoading(true);
    try {
      const res = await fetch(`${API}/recovery/images/${image.record_key}`);
      if (res.ok) setSelected(await res.json());
    } finally {
      setSelectedLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

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
    }
  };

  const updateSelected = (key: 'business' | 'category', value: string) => {
    if (!selected) return;
    setSelected({ ...selected, image: { ...selected.image, [key]: value } });
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin" size={20} style={{ color: '#b8960c' }} />
      </div>
    );
  }

  const shownEnd = Math.min(offset + images.length, imageTotal);
  const categories = Object.keys(facets.category || {}).sort();

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

      <div style={{ display: 'grid', gridTemplateColumns: selected ? 'minmax(0, 1fr) 420px' : '1fr', gap: 0, minHeight: 0, flex: 1 }}>
        <div style={{ overflowY: 'auto', padding: 18 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 10, marginBottom: 14 }}>
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
                {categories.map(c => <option key={c} value={c}>{c}</option>)}
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
            <div style={{ fontSize: 11, color: '#777' }}>External UI on port 3077: {serviceUp ? 'reachable' : 'not running'}. This workbench uses the loaded backend router.</div>
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
                {(() => {
                  const conf = confidenceLabel(selected.image.confidence);
                  return (
                    <div style={{ marginTop: 8, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                      <span style={{ fontSize: 10, color: '#888', fontWeight: 700, textTransform: 'uppercase' }}>Classifier:</span>
                      <span style={{ fontSize: 11, color: '#333' }}>{classifierLabel(selected.image.classified_by)}</span>
                      {conf && (
                        <span style={{ fontSize: 9, padding: '2px 7px', borderRadius: 6, background: '#eff6ff', color: conf.color, fontWeight: 800 }}>
                          {conf.pct}% confidence ({conf.level})
                        </span>
                      )}
                      <span style={{ fontSize: 10, color: '#aaa' }}>{selected.image.reviewed ? '· reviewed' : '· unreviewed'}</span>
                    </div>
                  );
                })()}
                <DetailLabel label="Generated description" value={selected.image.description || 'No generated description stored.'} />
                <DetailLabel label="OCR text" value={selected.ocr_text || 'No OCR text stored in this record.'} />
                <DetailLabel label="Source path" value={selected.image.path || 'Not stored'} mono />
                <DetailLabel label="Classified path" value={selected.image.classified_path || 'Not copied to classified bucket'} mono />
                <DetailLabel label="Social path" value={selected.image.social_path || 'Not approved as social asset'} mono />

                <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid #ece8e0' }}>
                  <div style={{ fontSize: 12, fontWeight: 900, marginBottom: 8 }}>Review Actions</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    <select value={selected.image.business} onChange={e => updateSelected('business', e.target.value)} style={selectStyle}>
                      {['empire-workroom', 'woodcraft', 'general', 'personal', 'ambiguous'].map(v => <option key={v} value={v}>{v}</option>)}
                    </select>
                    <input value={selected.image.category || ''} onChange={e => updateSelected('category', e.target.value)} placeholder="category" style={selectStyle} />
                    <button onClick={() => reviewSelected('approved')} style={{ ...actionButtonStyle, background: '#16a34a', color: '#fff' }}><Check size={13} /> Approve</button>
                    <button onClick={() => reviewSelected('rejected')} style={{ ...actionButtonStyle, background: '#dc2626', color: '#fff' }}><X size={13} /> Reject</button>
                    <button onClick={() => reviewSelected('reviewed')} style={{ ...actionButtonStyle, gridColumn: '1 / -1' }}>Mark reviewed / reclassify</button>
                  </div>
                  <div style={{ marginTop: 8, fontSize: 10, color: '#888' }}>Reclassify updates the JSON index and safely copies to the selected classified bucket when supported. It does not delete the old source file.</div>
                </div>

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

function tagStyle(background: string, color: string): React.CSSProperties {
  return { fontSize: 9, padding: '2px 6px', borderRadius: 6, background, color, fontWeight: 800 };
}
