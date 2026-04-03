'use client';
import { useJob } from '../hooks/useJob';
import { X, RefreshCw, Briefcase } from 'lucide-react';

export default function ActiveJobBanner() {
  const { activeJob, clearJob } = useJob();

  if (!activeJob) return null;

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '6px 16px', background: '#fdf8eb', borderBottom: '1px solid #f0e6c0',
      fontSize: 11, color: '#96750a', fontWeight: 600,
    }}>
      <Briefcase size={12} />
      <span>Active Job: {activeJob.job_number} — {activeJob.client_name}</span>
      {activeJob.room && <span style={{ color: '#b8960c' }}>| {activeJob.room}</span>}
      <span style={{
        marginLeft: 4, padding: '1px 6px', borderRadius: 4,
        background: '#f0e6c0', fontSize: 9, textTransform: 'uppercase',
      }}>
        {activeJob.status}
      </span>
      <div style={{ flex: 1 }} />
      <button onClick={clearJob} title="Close active job"
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#b8960c', padding: 2 }}>
        <X size={12} />
      </button>
    </div>
  );
}
