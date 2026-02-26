'use client';
import { useState } from 'react';
import { MOCK_JOBS, JOB_STATUSES, Job, JobStatus } from '@/lib/deskData';
import { Clock, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { StatsBar } from './shared';
import { TaskList } from './shared';
import JobKanban from './operations/JobKanban';
import JobTable from './operations/JobTable';

export default function OperationsDesk() {
  const [jobs, setJobs] = useState<Job[]>(MOCK_JOBS);
  const [view, setView] = useState<'kanban' | 'table'>('kanban');

  const today = new Date().toISOString().split('T')[0];
  const jobsToday = jobs.filter(j => j.dueDate === today).length;
  const overdue = jobs.filter(j => j.dueDate < today && j.status !== 'Complete').length;
  const thisWeek = jobs.filter(j => {
    const d = new Date(j.dueDate);
    const weekEnd = new Date();
    weekEnd.setDate(weekEnd.getDate() + (7 - weekEnd.getDay()));
    return d <= weekEnd && j.status !== 'Complete';
  }).length;

  const moveJob = (jobId: string, newStatus: JobStatus) => {
    setJobs(prev => prev.map(j => j.id === jobId ? { ...j, status: newStatus } : j));
  };

  return (
    <div className="flex flex-col h-full">
      <StatsBar
        items={[
          { label: 'Due Today', value: jobsToday, icon: Clock, color: 'var(--gold)' },
          { label: 'Overdue', value: overdue, icon: AlertTriangle, color: '#ef4444' },
          { label: 'This Week', value: thisWeek, icon: CheckCircle2, color: 'var(--purple)' },
        ]}
        rightSlot={
          <div className="flex items-center gap-1">
            {(['kanban', 'table'] as const).map(v => (
              <button key={v} onClick={() => setView(v)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium transition capitalize"
                style={{
                  background: view === v ? 'var(--gold-pale)' : 'transparent',
                  color: view === v ? 'var(--gold)' : 'var(--text-muted)',
                  border: view === v ? '1px solid var(--gold-border)' : '1px solid transparent',
                }}
              >{v}</button>
            ))}
          </div>
        }
      />
      <div className="flex-1 overflow-auto p-4">
        {view === 'kanban' ? <JobKanban jobs={jobs} onMoveJob={moveJob} /> : <JobTable jobs={jobs} />}
      </div>
      <div className="p-4 pt-0">
        <TaskList desk="operations" compact />
      </div>
    </div>
  );
}
