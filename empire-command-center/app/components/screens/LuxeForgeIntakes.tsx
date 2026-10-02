'use client';

import { useCallback, useEffect, useState } from 'react';
import { API, API_BASE } from '../../lib/api';
import { isImageFile } from '../../lib/fileKind';

interface FabricFile {
  path?: string;
  original_name?: string;
}

interface Submission {
  id: string;
  intake_code?: string;
  name?: string;
  address?: string;
  status?: string;
  treatment?: string;
  notes?: string;
  rooms?: any[];
  photos?: any[];
  scans?: any[];
  measurements?: any[];
  photo_analysis?: any[];
  created_at?: string;
  contact?: { name?: string; email?: string; phone?: string; company?: string };
  fabrics?: any[];
  lead_id?: number | string | null;
  customer_id?: string | null;
  quote_id?: string | null;
  quote_number?: string | null;
}

function fileHref(path?: string): string {
  if (!path) return '';
  if (path.startsWith('http')) return path;
  return `${API_BASE}${path}`;
}

function FileThumb({ file }: { file: { path?: string; original_name?: string; filename?: string } }) {
  const name = file.original_name || file.filename || 'File';
  const href = fileHref(file.path);
  if (!href) return null;
  if (isImageFile(name) || isImageFile(file.path || '')) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" title={name}>
        <img src={href} alt={name} style={{ width: 64, height: 64, objectFit: 'cover', borderRadius: 8, border: '1px solid #ece8e0' }} />
      </a>
    );
  }
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12, color: '#b8960c', fontWeight: 700 }}>
      {name}
    </a>
  );
}

export default function LuxeForgeIntakes({
  onOpenQuote,
  onOpenCustomer,
}: {
  onOpenQuote?: (quoteId: string) => void;
  onOpenCustomer?: (customerId: string) => void;
}) {
  const [rows, setRows] = useState<Submission[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    fetch(`${API}/intake/owner/submissions`)
      .then(async res => {
        if (!res.ok) throw new Error(`Could not load intakes (${res.status})`);
        return res.json();
      })
      .then(data => {
        setRows(Array.isArray(data.submissions) ? data.submissions : []);
        setError(null);
      })
      .catch(err => setError(err.message || 'Could not load intakes'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }} className="px-4 sm:px-9 py-6">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 8 }}>
        <h2 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>LuxeForge Intakes</h2>
        <button type="button" onClick={load} style={{ border: '1px solid #ece8e0', background: '#fff', borderRadius: 8, padding: '6px 12px', fontSize: 12, cursor: 'pointer' }}>
          Refresh
        </button>
      </div>
      <p style={{ fontSize: 13, color: '#666', marginTop: 0, marginBottom: 16 }}>
        Designer submissions from luxe.empirebox.store. Each one is stored with the project, then linked to a CRM lead and a Workroom quote draft. The draft is not sent to the customer.
      </p>
      {loading && <p style={{ fontSize: 13, color: '#888' }}>Loading intakes…</p>}
      {error && <p style={{ fontSize: 13, color: '#dc2626' }}>{error}</p>}
      {!loading && !error && rows.length === 0 && (
        <p style={{ fontSize: 13, color: '#888' }}>No designer intakes yet.</p>
      )}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {rows.map(row => {
          const files = [
            ...(row.photos || []),
            ...(row.scans || []),
          ];
          return (
            <article key={row.id} style={{ border: '1px solid #ece8e0', borderRadius: 12, background: '#fff', padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 700, color: '#1a1a1a' }}>{row.name || 'Untitled project'}</div>
                  <div style={{ fontSize: 12, color: '#888', marginTop: 2 }}>
                    {row.intake_code} · {row.status} · {row.treatment || 'No treatment listed'}
                  </div>
                </div>
                <div style={{ fontSize: 12, color: '#666', textAlign: 'right' }}>
                  <div>{row.contact?.name || 'Unknown contact'}</div>
                  <div>{row.contact?.email}</div>
                  {row.contact?.phone && <div>{row.contact.phone}</div>}
                  {row.contact?.company && <div>{row.contact.company}</div>}
                </div>
              </div>
              {row.address && <p style={{ fontSize: 12, color: '#666', margin: '8px 0 0' }}>{row.address}</p>}
              {Array.isArray(row.rooms) && row.rooms.length > 0 && (
                <ul style={{ margin: '10px 0 0', paddingLeft: 18, fontSize: 13, color: '#333' }}>
                  {row.rooms.map((room, i) => (
                    <li key={i}>
                      {[room?.name || room?.room, room?.treatment, room?.description].filter(Boolean).join(' — ')}
                    </li>
                  ))}
                </ul>
              )}
              {Array.isArray(row.fabrics) && row.fabrics.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#b8960c', letterSpacing: '0.04em' }}>FABRIC</div>
                  {row.fabrics.map((fabric, i) => {
                    const swatches: FabricFile[] = Array.isArray(fabric.swatch_files) ? fabric.swatch_files : [];
                    const legacy = fabric.swatch_photo_path && !swatches.some(f => f.path === fabric.swatch_photo_path)
                      ? [{ path: fabric.swatch_photo_path, original_name: 'swatch' }]
                      : [];
                    return (
                      <div key={fabric.id || i} style={{ marginTop: 8, fontSize: 13, color: '#333' }}>
                        <div>
                          {(fabric.item_name || fabric.room_name || 'Item')} · {fabric.fabric_preference || 'not sure'}
                          {fabric.fabric_name ? ` · ${fabric.fabric_name}` : ''}
                          {fabric.fabric_code ? ` · ${fabric.fabric_code}` : ''}
                          {fabric.color_pattern ? ` · ${fabric.color_pattern}` : ''}
                        </div>
                        {fabric.supplier_url && (
                          <a href={fabric.supplier_url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12, color: '#b8960c' }}>Supplier link</a>
                        )}
                        {fabric.client_notes && <div style={{ fontSize: 12, color: '#666' }}>{fabric.client_notes}</div>}
                        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 6 }}>
                          {[...swatches, ...legacy].map((file, n) => <FileThumb key={n} file={file} />)}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
              {files.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#666', letterSpacing: '0.04em' }}>PHOTOS AND FILES</div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 6 }}>
                    {files.map((file, i) => <FileThumb key={i} file={file} />)}
                  </div>
                </div>
              )}
              {Array.isArray(row.photo_analysis) && row.photo_analysis.some((note) => note?.overall_notes || note?.items) && (
                <div style={{ marginTop: 12, background: '#faf9f7', borderRadius: 8, padding: 10 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: '#666' }}>PHOTO NOTES (OWNER ONLY)</div>
                  {row.photo_analysis.filter((note) => note?.overall_notes || note?.items).map((note, i) => (
                    <p key={i} style={{ fontSize: 12, color: '#444', margin: '6px 0 0', whiteSpace: 'pre-wrap' }}>
                      {(note.filename ? `${note.filename}: ` : '') + (note.overall_notes || note.detail || note.status || 'Noted')}
                    </p>
                  ))}
                </div>
              )}
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 12, fontSize: 13 }}>
                {row.lead_id ? (
                  <a href={`/?product=lead`} style={{ color: '#2563eb', fontWeight: 700 }}>Lead #{row.lead_id}</a>
                ) : (
                  <span style={{ color: '#999' }}>No lead yet</span>
                )}
                {row.quote_id ? (
                  onOpenQuote ? (
                    <button type="button" onClick={() => onOpenQuote(row.quote_id as string)} style={{ background: 'none', border: 'none', color: '#16a34a', fontWeight: 700, cursor: 'pointer', padding: 0 }}>
                      Quote {row.quote_number || row.quote_id}
                    </button>
                  ) : (
                    <a href={`/?product=workroom&section=quotes&quote=${encodeURIComponent(row.quote_id)}`} style={{ color: '#16a34a', fontWeight: 700 }}>
                      Quote {row.quote_number || row.quote_id}
                    </a>
                  )
                ) : (
                  <span style={{ color: '#999' }}>No quote yet</span>
                )}
                {row.customer_id && (
                  onOpenCustomer ? (
                    <button type="button" onClick={() => onOpenCustomer(row.customer_id as string)} style={{ background: 'none', border: 'none', color: '#b8960c', fontWeight: 700, cursor: 'pointer', padding: 0 }}>
                      CRM contact
                    </button>
                  ) : (
                    <a href="/?product=crm" style={{ color: '#b8960c', fontWeight: 700 }}>CRM contact</a>
                  )
                )}
              </div>
              {row.notes && <p style={{ fontSize: 12, color: '#666', marginBottom: 0 }}>{row.notes}</p>}
            </article>
          );
        })}
      </div>
    </div>
  );
}
