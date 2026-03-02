'use client';
import { KanbanBoard, type KanbanColumn } from '../shared';
import { type Job, type JobStatus, JOB_STATUSES } from '@/lib/deskData';

const STATUS_COLORS: Record<JobStatus, string> = {
  New:        'var(--purple)',
  Cutting:    'var(--cyan)',
  Sewing:     '#f59e0b',
  Installing: 'var(--gold)',
  Complete:   '#22c55e',
};

const STATUS_BG: Record<JobStatus, string> = {
  New:        'var(--purple-pale)',
  Cutting:    'rgba(34,211,238,0.08)',
  Sewing:     'rgba(245,158,11,0.08)',
  Installing: 'var(--gold-pale)',
  Complete:   'rgba(34,197,94,0.08)',
};

const COLUMNS: KanbanColumn[] = JOB_STATUSES.map(s => ({
  key: s, label: s, color: STATUS_COLORS[s],
}));

interface JobKanbanProps {
  jobs: Job[];
  onMoveJob: (jobId: string, newStatus: JobStatus) => void;
  onJobClick?: (job: Job) => void;
}

export default function JobKanban({ jobs, onMoveJob, onJobClick }: JobKanbanProps) {
  const today = new Date().toISOString().split('T')[0];

  return (
    <KanbanBoard
      columns={COLUMNS}
      items={jobs}
      getColumnKey={job => job.status}
      getItemId={job => job.id}
      onMoveItem={(id, col) => onMoveJob(id, col as JobStatus)}
      renderCard={job => (
        <div
          className="rounded-lg p-2.5 cursor-pointer transition"
          style={{ background: STATUS_BG[job.status], border: '1px solid var(--border)' }}
          onClick={() => onJobClick?.(job)}
          onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--gold-border)')}
          onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
        >
          <p className="text-xs font-medium mb-1" style={{ color: 'var(--text-primary)' }}>{job.name}</p>
          <p className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>{job.client}</p>
          <div className="flex items-center justify-between mt-2">
            <span
              className="text-[10px] font-mono"
              style={{ color: job.dueDate < today && job.status !== 'Complete' ? '#ef4444' : 'var(--text-muted)' }}
            >
              {job.dueDate}
            </span>
            <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{job.assignedTo}</span>
          </div>
        </div>
      )}
    />
  );
}
