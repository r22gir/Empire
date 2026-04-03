'use client';
import React, { useState, useEffect } from 'react';
import { API } from '../../lib/api';
import { useJob, Job } from '../../hooks/useJob';
import {
  Briefcase, Plus, Search, Filter, ChevronRight, Clock, User,
  MapPin, DollarSign, FileText, Camera, Hammer, CheckCircle,
  AlertTriangle, ArrowRight, Calendar, Package, Eye
} from 'lucide-react';

const PIPELINE_STAGES = [
  { key: 'intake', label: 'Intake', color: '#6b7280' },
  { key: 'measuring', label: 'Measuring', color: '#3b82f6' },
  { key: 'designing', label: 'Designing', color: '#8b5cf6' },
  { key: 'quoting', label: 'Quoting', color: '#f59e0b' },
  { key: 'quoted', label: 'Quoted', color: '#eab308' },
  { key: 'approved', label: 'Approved', color: '#16a34a' },
  { key: 'in_production', label: 'Production', color: '#06b6d4' },
  { key: 'installing', label: 'Installing', color: '#2563eb' },
  { key: 'completed', label: 'Completed', color: '#059669' },
  { key: 'invoiced', label: 'Invoiced', color: '#b8960c' },
  { key: 'paid', label: 'Paid', color: '#16a34a' },
];

const STATUS_BADGE = (status: string) => {
  const stage = PIPELINE_STAGES.find(s => s.key === status) || { color: '#999', label: status };
  return (
    <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 8,
      background: `${stage.color}15`, color: stage.color }}>
      {stage.label}
    </span>
  );
};

interface JobsScreenProps {
  business?: string;
}

export default function JobsScreen({ business }: JobsScreenProps) {
  const [view, setView] = useState<'pipeline' | 'list'>('list');
  const [jobs, setJobs] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<any>(null);
  const { setActiveJob } = useJob();

  useEffect(() => {
    const url = search
      ? `${API}/jobs/search?q=${encodeURIComponent(search)}`
      : `${API}/jobs`;
    fetch(url).then(r => r.json()).then(d => setJobs(d.jobs || d || [])).catch(() => {});
  }, [search]);

  const filteredJobs = business
    ? jobs.filter((j: any) => j.business_unit === business)
    : jobs;

  return (
    <div style={{ padding: '20px 24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Jobs</h2>
          <p style={{ fontSize: 12, color: '#888', marginTop: 2 }}>{filteredJobs.length} jobs total</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => setView(view === 'pipeline' ? 'list' : 'pipeline')}
            style={{ fontSize: 11, padding: '6px 12px', border: '1px solid #e5e2dc', borderRadius: 6,
              background: '#fff', cursor: 'pointer', fontWeight: 500 }}>
            {view === 'pipeline' ? 'List View' : 'Pipeline View'}
          </button>
          <button style={{ fontSize: 11, padding: '6px 14px', background: '#b8960c', color: '#fff',
            border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
            <Plus size={12} /> New Job
          </button>
        </div>
      </div>

      {/* Search */}
      <div style={{ position: 'relative', marginBottom: 16, maxWidth: 400 }}>
        <Search size={14} style={{ position: 'absolute', left: 10, top: 9, color: '#999' }} />
        <input value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search jobs, clients, fabric codes..."
          style={{ width: '100%', padding: '7px 8px 7px 30px', border: '1px solid #e5e2dc', borderRadius: 8, fontSize: 12 }} />
      </div>

      {view === 'pipeline' ? (
        /* Pipeline / Kanban view */
        <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 12 }}>
          {PIPELINE_STAGES.map(stage => {
            const cards = filteredJobs.filter((j: any) => (j.status || j.pipeline_stage) === stage.key);
            const total = cards.reduce((s: number, j: any) => s + (j.estimated_value || j.quoted_amount || 0), 0);
            return (
              <div key={stage.key} style={{ minWidth: 200, background: '#f5f3ef', borderRadius: 10, padding: 10, flex: 1 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: stage.color, marginBottom: 4, display: 'flex', justifyContent: 'space-between' }}>
                  {stage.label} <span style={{ color: '#999' }}>{cards.length}</span>
                </div>
                {total > 0 && <div style={{ fontSize: 9, color: '#b8960c', fontWeight: 600, marginBottom: 6 }}>${total.toLocaleString()}</div>}
                {cards.length === 0 ? <div style={{ fontSize: 10, color: '#ccc', textAlign: 'center', padding: 12 }}>—</div> : cards.map((job: any) => (
                  <div key={job.id} onClick={() => { setSelected(job); setActiveJob(job); }}
                    style={{ background: '#fff', borderRadius: 8, padding: 10, marginBottom: 6, border: '1px solid #e5e2dc', fontSize: 11, cursor: 'pointer' }}>
                    <div style={{ fontWeight: 600 }}>{job.client_name || job.title}</div>
                    <div style={{ color: '#888', fontSize: 10 }}>{job.job_number} • {job.room || ''}</div>
                    {(job.estimated_value || job.quoted_amount) > 0 && (
                      <div style={{ color: '#b8960c', fontWeight: 600, fontSize: 10, marginTop: 2 }}>${(job.estimated_value || job.quoted_amount || 0).toLocaleString()}</div>
                    )}
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      ) : (
        /* List view */
        <div>
          {filteredJobs.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>No jobs found. Create your first job.</div>
          ) : (
            <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
              <thead><tr style={{ borderBottom: '2px solid #e5e2dc', textAlign: 'left' }}>
                <th style={{ padding: 8 }}>Job #</th>
                <th style={{ padding: 8 }}>Client</th>
                <th style={{ padding: 8 }}>Title / Room</th>
                <th style={{ padding: 8 }}>Status</th>
                <th style={{ padding: 8 }}>Value</th>
                <th style={{ padding: 8 }}>Date</th>
              </tr></thead>
              <tbody>{filteredJobs.map((job: any) => (
                <tr key={job.id} onClick={() => { setSelected(job); setActiveJob(job); }}
                  style={{ borderBottom: '1px solid #f0ede6', cursor: 'pointer' }}
                  onMouseEnter={e => (e.currentTarget.style.background = '#fdf8eb')}
                  onMouseLeave={e => (e.currentTarget.style.background = '')}>
                  <td style={{ padding: 8, fontFamily: 'monospace', fontSize: 11, color: '#b8960c', fontWeight: 600 }}>{job.job_number || `JOB-${job.id}`}</td>
                  <td style={{ padding: 8, fontWeight: 500 }}>{job.client_name || job.title}</td>
                  <td style={{ padding: 8, color: '#666' }}>{job.room || job.description?.slice(0, 40) || '—'}</td>
                  <td style={{ padding: 8 }}>{STATUS_BADGE(job.status || job.pipeline_stage || 'intake')}</td>
                  <td style={{ padding: 8, fontWeight: 600 }}>{(job.estimated_value || job.quoted_amount) ? `$${(job.estimated_value || job.quoted_amount).toLocaleString()}` : '—'}</td>
                  <td style={{ padding: 8, color: '#888', fontSize: 11 }}>{job.created_at?.slice(0, 10) || '—'}</td>
                </tr>
              ))}</tbody>
            </table>
          )}
        </div>
      )}

      {/* Job detail side panel */}
      {selected && (
        <div style={{
          position: 'fixed', right: 0, top: 0, bottom: 0, width: 400, background: '#fff',
          borderLeft: '1px solid #e5e2dc', boxShadow: '-4px 0 20px rgba(0,0,0,0.1)',
          zIndex: 500, overflowY: 'auto', padding: 20,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>{selected.job_number || `JOB-${selected.id}`}</h3>
            <button onClick={() => setSelected(null)} style={{ background: '#f5f3ef', border: 'none', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', fontSize: 11 }}>Close</button>
          </div>

          {/* Client info */}
          <div style={{ background: '#fdf8eb', borderRadius: 8, padding: 12, marginBottom: 12, fontSize: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 4 }}><User size={12} style={{ verticalAlign: 'text-bottom' }} /> {selected.client_name || selected.title}</div>
            {selected.client_email && <div style={{ color: '#666' }}>{selected.client_email}</div>}
            {selected.client_phone && <div style={{ color: '#666' }}>{selected.client_phone}</div>}
            {(selected.client_address || selected.address) && <div style={{ color: '#666' }}><MapPin size={10} /> {selected.client_address || selected.address}</div>}
          </div>

          {/* Status */}
          <div style={{ marginBottom: 12 }}>
            <span style={{ fontSize: 10, fontWeight: 600, color: '#888' }}>STATUS</span>
            <div style={{ marginTop: 4 }}>{STATUS_BADGE(selected.status || 'intake')}</div>
          </div>

          {/* Room / Description */}
          {(selected.room || selected.description) && (
            <div style={{ marginBottom: 12, fontSize: 12 }}>
              <span style={{ fontSize: 10, fontWeight: 600, color: '#888' }}>JOB DETAILS</span>
              {selected.room && <div style={{ marginTop: 4 }}><strong>Room:</strong> {selected.room}</div>}
              {selected.description && <div style={{ color: '#666', marginTop: 2 }}>{selected.description}</div>}
            </div>
          )}

          {/* Financial */}
          <div style={{ marginBottom: 12, fontSize: 12 }}>
            <span style={{ fontSize: 10, fontWeight: 600, color: '#888' }}>FINANCIAL</span>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginTop: 6 }}>
              <div style={{ background: '#f5f3ef', borderRadius: 6, padding: 8 }}>
                <div style={{ fontSize: 9, color: '#888' }}>ESTIMATED</div>
                <div style={{ fontWeight: 700, color: '#b8960c' }}>${(selected.estimated_value || 0).toLocaleString()}</div>
              </div>
              <div style={{ background: '#f5f3ef', borderRadius: 6, padding: 8 }}>
                <div style={{ fontSize: 9, color: '#888' }}>PAID</div>
                <div style={{ fontWeight: 700, color: '#16a34a' }}>${(selected.paid_amount || 0).toLocaleString()}</div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 16 }}>
            <button style={{ fontSize: 10, padding: '6px 12px', background: '#b8960c', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}>Create Quote</button>
            <button style={{ fontSize: 10, padding: '6px 12px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}>Create Invoice</button>
            <button style={{ fontSize: 10, padding: '6px 12px', background: '#f5f3ef', color: '#666', border: 'none', borderRadius: 6, cursor: 'pointer' }}>Generate Drawing</button>
          </div>
        </div>
      )}
    </div>
  );
}
