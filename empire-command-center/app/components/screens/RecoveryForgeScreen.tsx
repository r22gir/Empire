'use client';
import { useState, useEffect, useCallback } from 'react';
import { HardDrive, Play, Square, RefreshCw, Loader2, Search } from 'lucide-react';
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
  filename: string;
  image_url?: string;
  business: string;
  pre_tag: string;
  category: string;
  description: string;
  quality: string;
  social_ready: boolean;
  confidence?: number;
  classified_by: string;
  classified_path?: string;
  path?: string;
}

export default function RecoveryForgeScreen() {
  const [status, setStatus] = useState<RecoveryStatus | null>(null);
  const [images, setImages] = useState<RecoveryImage[]>([]);
  const [imageTotal, setImageTotal] = useState(0);
  const [businessFilter, setBusinessFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [serviceUp, setServiceUp] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchImages = useCallback(async () => {
    const params = new URLSearchParams({ limit: '36', analyzed_only: 'true' });
    if (businessFilter !== 'all') params.set('business', businessFilter);
    if (search.trim()) params.set('q', search.trim());
    const res = await fetch(`${API}/recovery/images?${params.toString()}`);
    if (!res.ok) return;
    const data = await res.json();
    setImages(data.images || []);
    setImageTotal(data.total || 0);
  }, [businessFilter, search]);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/recovery/status`);
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      }
    } catch {
      // API might be down
    }

    // Check if RecoveryForge web UI is up
    try {
      const res = await fetch('http://localhost:3077', { signal: AbortSignal.timeout(3000) });
      setServiceUp(res.ok || res.status === 404);
    } catch {
      setServiceUp(false);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  useEffect(() => {
    fetchImages().catch(() => {});
  }, [fetchImages]);

  const handleAction = async (action: 'start' | 'stop') => {
    setActionLoading(true);
    try {
      await fetch(`${API}/recovery/${action}`, { method: 'POST' });
      setTimeout(fetchStatus, 2000);
    } catch (e) {
      console.error('Action failed:', e);
    }
    setActionLoading(false);
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin" size={20} style={{ color: '#b8960c' }} />
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header + Status Bar */}
      <div className="flex flex-wrap items-center gap-3 px-4 sm:px-5 py-3" style={{
        background: '#faf9f7',
        borderBottom: '1px solid #ece8e0',
        flexShrink: 0,
      }}>
        <HardDrive size={20} style={{ color: '#b8960c' }} />
        <h2 className="text-sm sm:text-base" style={{ fontWeight: 700, color: '#1a1a1a', margin: 0 }}>
          RecoveryForge
        </h2>

        {status && (
          <>
            <div style={{
              marginLeft: 'auto',
              display: 'flex',
              alignItems: 'center',
              gap: 12,
              fontSize: 12,
              color: '#666',
            }}>
              <span style={{
                padding: '3px 10px',
                borderRadius: 20,
                fontSize: 11,
                fontWeight: 600,
                background: status.running ? '#dcfce7' : '#fef2f2',
                color: status.running ? '#16a34a' : '#dc2626',
              }}>
                {status.running ? 'Running' : 'Stopped'}
              </span>
              <span>{status.processed.toLocaleString()} / {status.total_images.toLocaleString()} images ({status.percentage}%)</span>
            </div>

            <button
              onClick={() => handleAction(status.running ? 'stop' : 'start')}
              disabled={actionLoading}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 14px',
                borderRadius: 8,
                border: 'none',
                background: status.running ? '#dc2626' : '#16a34a',
                color: '#fff',
                fontSize: 13,
                fontWeight: 600,
                cursor: 'pointer',
                opacity: actionLoading ? 0.6 : 1,
                minHeight: 44,
              }}
            >
              {actionLoading ? <Loader2 size={14} className="animate-spin" /> :
                status.running ? <Square size={14} /> : <Play size={14} />}
              {status.running ? 'Stop' : 'Start'}
            </button>
          </>
        )}

        <button
          onClick={fetchStatus}
          style={{
            background: 'none',
            border: '1px solid #ece8e0',
            borderRadius: 8,
            padding: '6px 10px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <RefreshCw size={14} style={{ color: '#999' }} />
        </button>
      </div>

      {/* Local classified image browser. This is the loaded, truthful RecoveryForge path. */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 18 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center', marginBottom: 14 }}>
          <div>
            <div style={{ fontSize: 15, fontWeight: 800, color: '#1a1a1a' }}>Analyzed Image Index</div>
            <div style={{ fontSize: 11, color: '#777' }}>
              {imageTotal.toLocaleString()} analyzed records from {status?.index_file || '/data/images/presorted_inventory.json'}
            </div>
          </div>
          <div style={{ marginLeft: 'auto', display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
            {['all', 'empire-workroom', 'woodcraft', 'general', 'ambiguous', 'personal'].map(f => (
              <button key={f} onClick={() => setBusinessFilter(f)} style={{
                padding: '6px 10px',
                borderRadius: 8,
                border: businessFilter === f ? '1.5px solid #b8960c' : '1px solid #e5e2dc',
                background: businessFilter === f ? '#fdf8eb' : '#fff',
                color: businessFilter === f ? '#96750a' : '#666',
                fontSize: 11,
                fontWeight: 700,
                cursor: 'pointer',
              }}>
                {f === 'all' ? 'All' : f.replace('-', ' ')}
              </button>
            ))}
            <div style={{ position: 'relative' }}>
              <Search size={13} style={{ position: 'absolute', left: 9, top: 9, color: '#999' }} />
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search filename, tag, description"
                style={{ padding: '7px 10px 7px 28px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12, minWidth: 220 }}
              />
            </div>
          </div>
        </div>

        {images.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
            {images.map((img) => (
              <div key={`${img.filename}-${img.classified_path || img.path || ''}`} style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 8, overflow: 'hidden' }}>
                {img.image_url ? (
                  <img src={`${API.replace('/api/v1', '')}${img.image_url}`} alt={img.filename} style={{ width: '100%', height: 150, objectFit: 'cover', background: '#f5f3ef' }} />
                ) : (
                  <div style={{ height: 150, background: '#f5f3ef' }} />
                )}
                <div style={{ padding: 10 }}>
                  <div title={img.filename} style={{ fontSize: 12, fontWeight: 800, color: '#1a1a1a', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{img.filename}</div>
                  <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', margin: '7px 0' }}>
                    <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 6, background: '#fdf8eb', color: '#96750a', fontWeight: 700 }}>{img.business}</span>
                    <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 6, background: '#f0fdf4', color: '#15803d', fontWeight: 700 }}>{img.category}</span>
                    {img.confidence !== undefined && img.confidence !== null && (
                      <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 6, background: '#eff6ff', color: '#2563eb', fontWeight: 700 }}>{Math.round(img.confidence * 100)}%</span>
                    )}
                  </div>
                  <div style={{ fontSize: 11, color: '#555', minHeight: 42, lineHeight: 1.35 }}>
                    {img.description || 'No generated description stored for this image.'}
                  </div>
                  <div style={{ marginTop: 8, fontSize: 10, color: '#999' }}>
                    {img.classified_by}{img.social_ready ? ' · social ready' : ''}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: 40, textAlign: 'center', color: '#999', background: '#fff', border: '1px solid #ece8e0', borderRadius: 8 }}>
            No analyzed RecoveryForge images matched the current filters.
          </div>
        )}

        {/* Optional external RecoveryForge web UI status. */}
        <div style={{ marginTop: 18, fontSize: 11, color: '#888' }}>
          External RecoveryForge UI on port 3077: {serviceUp ? 'reachable' : 'not running'}. The gallery above uses the loaded backend router and local classified image index.
        </div>
      </div>

    </div>
  );
}
