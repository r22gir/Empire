'use client';
import { type Job, type JobStatus } from '@/lib/deskData';
import { Calendar, User, Ruler, Scissors, FileText, StickyNote, Wrench, ClipboardList } from 'lucide-react';

const STATUS_COLORS: Record<JobStatus, string> = {
  New: 'var(--purple)', Cutting: 'var(--cyan)', Sewing: '#f59e0b',
  Installing: 'var(--gold)', Complete: '#22c55e',
};

const TIMELINE_STEPS: JobStatus[] = ['New', 'Cutting', 'Sewing', 'Installing', 'Complete'];

interface JobDetailProps {
  job: Job;
  onClientClick?: (clientName: string) => void;
}

export default function JobDetail({ job, onClientClick }: JobDetailProps) {
  const currentIdx = TIMELINE_STEPS.indexOf(job.status);

  return (
    <div className="space-y-5">
      {/* Timeline */}
      <div>
        <p className="text-[10px] uppercase tracking-wider mb-3" style={{ color: 'var(--text-muted)' }}>Production Timeline</p>
        <div className="flex items-center gap-1">
          {TIMELINE_STEPS.map((step, i) => {
            const done = i <= currentIdx;
            return (
              <div key={step} className="flex items-center gap-1 flex-1">
                <div className="flex flex-col items-center flex-1">
                  <div
                    className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold"
                    style={{
                      background: done ? STATUS_COLORS[step] : 'var(--raised)',
                      color: done ? '#fff' : 'var(--text-muted)',
                      border: done ? 'none' : '1px solid var(--border)',
                    }}
                  >
                    {i + 1}
                  </div>
                  <span className="text-[9px] mt-1" style={{ color: done ? 'var(--text-primary)' : 'var(--text-muted)' }}>{step}</span>
                </div>
                {i < TIMELINE_STEPS.length - 1 && (
                  <div className="h-0.5 flex-1 rounded" style={{ background: i < currentIdx ? STATUS_COLORS[TIMELINE_STEPS[i + 1]] : 'var(--border)', minWidth: 8 }} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Info grid */}
      <div className="space-y-3">
        <InfoRow icon={User} label="Client">
          <button
            onClick={() => onClientClick?.(job.client)}
            className="text-xs font-semibold transition"
            style={{ color: 'var(--gold)', cursor: 'pointer' }}
            onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
            onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
          >
            {job.client}
          </button>
        </InfoRow>
        <InfoRow icon={Scissors} label="Treatment">{job.treatmentType}</InfoRow>
        <InfoRow icon={ClipboardList} label="Fabric">{job.fabric}</InfoRow>
        <InfoRow icon={Ruler} label="Dimensions">{job.dimensions}</InfoRow>
        <InfoRow icon={Calendar} label="Order Date">{job.orderDate}</InfoRow>
        <InfoRow icon={Calendar} label="Due Date">
          <span style={{ color: job.dueDate < new Date().toISOString().split('T')[0] && job.status !== 'Complete' ? '#ef4444' : 'var(--text-primary)' }}>
            {job.dueDate}
          </span>
        </InfoRow>
        <InfoRow icon={Wrench} label="Assigned To">{job.assignedTo}</InfoRow>
        <InfoRow icon={FileText} label="Quote ID">
          <span className="font-mono" style={{ color: 'var(--purple)' }}>{job.quoteId}</span>
        </InfoRow>
      </div>

      {/* Notes */}
      {job.notes && (
        <div className="rounded-lg p-3" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
          <div className="flex items-center gap-1.5 mb-1.5">
            <StickyNote className="w-3 h-3" style={{ color: 'var(--gold)' }} />
            <span className="text-[10px] font-semibold" style={{ color: 'var(--gold)' }}>Notes</span>
          </div>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{job.notes}</p>
        </div>
      )}

      {/* Installer Notes */}
      {job.installerNotes && (
        <div className="rounded-lg p-3" style={{ background: 'rgba(249,115,22,0.06)', border: '1px solid rgba(249,115,22,0.15)' }}>
          <div className="flex items-center gap-1.5 mb-1.5">
            <Wrench className="w-3 h-3" style={{ color: '#F97316' }} />
            <span className="text-[10px] font-semibold" style={{ color: '#F97316' }}>Installer Notes</span>
          </div>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{job.installerNotes}</p>
        </div>
      )}

      {/* Action buttons */}
      <div className="grid grid-cols-2 gap-2 pt-2">
        {['Update Status', 'Add Note', 'Assign Installer', 'View Quote'].map(label => (
          <button
            key={label}
            className="text-xs font-medium py-2 px-3 rounded-lg transition"
            style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold-border)'; e.currentTarget.style.color = 'var(--gold)'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

function InfoRow({ icon: Icon, label, children }: { icon: typeof User; label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      <Icon className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
      <span className="text-[10px] w-20 shrink-0" style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span className="text-xs" style={{ color: 'var(--text-primary)' }}>{children}</span>
    </div>
  );
}
