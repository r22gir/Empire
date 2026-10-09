'use client';
import { useState } from 'react';
import { useJob } from '../hooks/useJob';
import { X, RefreshCw, Briefcase, FolderOpen } from 'lucide-react';
import JobFolderModal from './jobs/JobFolderModal';

export default function ActiveJobBanner() {
  const { activeJob, clearJob } = useJob();
  const [folderOpen, setFolderOpen] = useState(false);

  if (!activeJob) return null;

  return (
    <>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '6px 16px',
          background: '#121214',
          borderBottom: '2px solid #b8960c',
          fontSize: 11,
          color: '#fff',
          fontWeight: 600,
          flexWrap: 'wrap',
        }}
      >
        <span
          style={{
            background: 'linear-gradient(135deg, #b8960c, #d4af37)',
            color: '#121214',
            padding: '2px 6px',
            borderRadius: '4px',
            fontSize: '9px',
            fontWeight: 800,
          }}
        >
          ACTIVE JOB
        </span>

        <button
          type="button"
          onClick={() => setFolderOpen(true)}
          style={{
            background: 'none',
            border: 'none',
            color: '#fff',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 11,
            fontWeight: 700,
            padding: 0,
          }}
        >
          <span>{activeJob.job_number} — {activeJob.client_name}</span>
          {activeJob.room && <span style={{ color: '#b8960c' }}>| {activeJob.room}</span>}
          <FolderOpen size={13} color="#b8960c" />
        </button>

        <span
          style={{
            padding: '1px 6px',
            borderRadius: 4,
            background: '#222',
            color: '#b8960c',
            border: '1px solid #444',
            fontSize: 9,
            textTransform: 'uppercase',
          }}
        >
          {activeJob.pipeline_stage || activeJob.status}
        </span>

        <div style={{ flex: 1 }} />

        <button
          type="button"
          onClick={() => setFolderOpen(true)}
          style={{
            minHeight: '28px',
            background: '#222',
            border: '1px solid #b8960c',
            color: '#b8960c',
            borderRadius: 6,
            padding: '2px 8px',
            fontSize: 10,
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          Open Folder
        </button>

        <button
          type="button"
          onClick={clearJob}
          title="Close active job context"
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: '#888',
            padding: 4,
            minHeight: '28px',
            minWidth: '28px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <X size={14} />
        </button>
      </div>

      {folderOpen && (
        <JobFolderModal
          jobId={activeJob.id}
          isOpen={folderOpen}
          onClose={() => setFolderOpen(false)}
        />
      )}
    </>
  );
}
