'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';

const API_BASE = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
  ? 'https://api.empirebox.store'
  : 'http://localhost:8000';

interface PresentationData {
  id: string;
  client_name: string;
  project_address: string;
  room: string;
  job_description: string;
  drawings: { svg: string; item_name: string; item_type: string }[];
  quote_data: any;
  status: string;
  created_at: string;
}

export default function ClientPresentationPage() {
  const params = useParams();
  const id = params.id as string;
  const [data, setData] = useState<PresentationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    fetch(`${API_BASE}/api/v1/presentations/${id}`)
      .then(r => {
        if (!r.ok) throw new Error('Presentation not found');
        return r.json();
      })
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });

    // Track view
    fetch(`${API_BASE}/api/v1/presentations/${id}/viewed`, { method: 'POST' }).catch(() => {});
  }, [id]);

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: '#faf9f7', fontFamily: 'system-ui' }}>
      <div style={{ textAlign: 'center', color: '#999' }}>Loading presentation...</div>
    </div>
  );

  if (error || !data) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: '#faf9f7', fontFamily: 'system-ui' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 48, marginBottom: 16 }}>🏛️</div>
        <div style={{ fontSize: 18, fontWeight: 600, color: '#333', marginBottom: 8 }}>Presentation Not Found</div>
        <div style={{ fontSize: 13, color: '#999' }}>This link may have expired or been removed.</div>
      </div>
    </div>
  );

  return (
    <div style={{ minHeight: '100vh', background: '#faf9f7', fontFamily: 'system-ui' }}>
      {/* Header */}
      <div style={{ background: '#1a1a1a', color: '#fff', padding: '24px 32px', textAlign: 'center' }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: '#b8960c', letterSpacing: 2, marginBottom: 4 }}>EMPIRE WORKROOM</div>
        <div style={{ fontSize: 22, fontWeight: 700, marginBottom: 4 }}>Design Presentation</div>
        <div style={{ fontSize: 13, color: '#999' }}>{data.client_name} — {data.project_address}</div>
        {data.room && <div style={{ fontSize: 11, color: '#777', marginTop: 2 }}>{data.room} • {data.job_description}</div>}
      </div>

      {/* Content */}
      <div style={{ maxWidth: 900, margin: '0 auto', padding: '24px 20px' }}>
        {/* Drawings */}
        {data.drawings?.map((d, i) => (
          <div key={i} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 20, marginBottom: 20 }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#b8960c', marginBottom: 12, textTransform: 'uppercase' }}>
              {d.item_name || d.item_type || `Drawing ${i + 1}`}
            </div>
            <div dangerouslySetInnerHTML={{ __html: d.svg }} style={{ width: '100%', overflow: 'auto' }} />
          </div>
        ))}

        {/* Quote Summary */}
        {data.quote_data && (
          <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 20, marginBottom: 20 }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#b8960c', marginBottom: 12 }}>QUOTE SUMMARY</div>
            {data.quote_data.line_items?.map((item: any, i: number) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #f0ede6', fontSize: 13 }}>
                <span>{item.description}</span>
                <span style={{ fontWeight: 600 }}>${(item.amount || 0).toFixed(2)}</span>
              </div>
            ))}
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', fontSize: 18, fontWeight: 700, color: '#b8960c', borderTop: '2px solid #b8960c', marginTop: 8 }}>
              <span>Total</span>
              <span>${(data.quote_data.total || 0).toFixed(2)}</span>
            </div>
          </div>
        )}

        {/* Footer */}
        <div style={{ textAlign: 'center', padding: '20px 0', color: '#999', fontSize: 11 }}>
          <div>Empire Workroom • 5124 Frolich Ln, Hyattsville, MD 20781 • (703) 213-6484</div>
          <div style={{ marginTop: 4 }}>Generated {new Date(data.created_at).toLocaleDateString()}</div>
        </div>
      </div>
    </div>
  );
}
