'use client';
import { DataTable, StatusBadge, type Column } from '../shared';
import { type Job, type JobStatus } from '@/lib/deskData';

const STATUS_COLORS: Record<JobStatus, string> = {
  New: 'var(--purple)', Cutting: 'var(--cyan)', Sewing: '#f59e0b',
  Installing: 'var(--gold)', Complete: '#22c55e',
};

interface JobTableProps {
  jobs: Job[];
}

export default function JobTable({ jobs }: JobTableProps) {
  const today = new Date().toISOString().split('T')[0];

  const columns: Column<Job>[] = [
    { key: 'name', label: 'Job', render: j => <span style={{ color: 'var(--text-primary)' }}>{j.name}</span> },
    { key: 'client', label: 'Client', render: j => <span style={{ color: 'var(--text-secondary)' }}>{j.client}</span> },
    { key: 'status', label: 'Status', render: j => <StatusBadge label={j.status} color={STATUS_COLORS[j.status]} /> },
    {
      key: 'dueDate', label: 'Due Date',
      render: j => (
        <span className="font-mono" style={{ color: j.dueDate < today && j.status !== 'Complete' ? '#ef4444' : 'var(--text-muted)' }}>
          {j.dueDate}
        </span>
      ),
    },
    { key: 'assignedTo', label: 'Assigned', render: j => <span style={{ color: 'var(--text-secondary)' }}>{j.assignedTo}</span> },
  ];

  return <DataTable columns={columns} data={jobs} getRowId={j => j.id} />;
}
