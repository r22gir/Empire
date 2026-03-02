'use client';
import { useState } from 'react';
import { type Job, type JobStatus } from '@/lib/deskData';
import { Calendar, User, Ruler, Scissors, FileText, StickyNote, Wrench, ClipboardList, ChevronRight, Plus, UserPlus, ExternalLink } from 'lucide-react';

const STATUS_COLORS: Record<JobStatus, string> = {
  New: 'var(--purple)', Cutting: 'var(--cyan)', Sewing: '#f59e0b',
  Installing: 'var(--gold)', Complete: '#22c55e',
};

const TIMELINE_STEPS: JobStatus[] = ['New', 'Cutting', 'Sewing', 'Installing', 'Complete'];

interface JobDetailProps {
  job: Job;
  onClientClick?: (clientName: string) => void;
  onMoveJob?: (jobId: string, newStatus: JobStatus) => void;
  onUpdateJob?: (jobId: string, updates: Partial<Job>) => void;
}

export default function JobDetail({ job, onClientClick, onMoveJob, onUpdateJob }: JobDetailProps) {
  const currentIdx = TIMELINE_STEPS.indexOf(job.status);
  const nextStatus = currentIdx < TIMELINE_STEPS.length - 1 ? TIMELINE_STEPS[currentIdx + 1] : null;

  const [showNoteInput, setShowNoteInput] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [showAssignInput, setShowAssignInput] = useState(false);
  const [assignText, setAssignText] = useState(job.assignedTo);

  const handleUpdateStatus = () => {
    if (nextStatus && onMoveJob) {
      onMoveJob(job.id, nextStatus);
    }
  };

  const handleAddNote = () => {
    if (noteText.trim() && onUpdateJob) {
      const existing = job.notes || '';
      const newNotes = existing ? `${existing}\n${noteText.trim()}` : noteText.trim();
      onUpdateJob(job.id, { notes: newNotes });
      setNoteText('');
      setShowNoteInput(false);
    }
  };

  const handleAssign = () => {
    if (assignText.trim() && onUpdateJob) {
      onUpdateJob(job.id, { assignedTo: assignText.trim() });
      setShowAssignInput(false);
    }
  };

  const handleViewQuote = () => {
    if (job.quoteId) {
      window.open(`/workroom?quote=${job.quoteId}`, '_blank');
    }
  };

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
          <p className="text-xs whitespace-pre-line" style={{ color: 'var(--text-secondary)' }}>{job.notes}</p>
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

      {/* Note input */}
      {showNoteInput && (
        <div className="rounded-lg p-3 space-y-2" style={{ background: 'var(--raised)', border: '1px solid var(--gold-border)' }}>
          <textarea
            value={noteText}
            onChange={e => setNoteText(e.target.value)}
            placeholder="Add a note..."
            rows={3}
            autoFocus
            className="w-full text-xs rounded-lg p-2 resize-none"
            style={{ background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border)', outline: 'none' }}
            onFocus={e => (e.currentTarget.style.borderColor = 'var(--gold-border)')}
            onBlur={e => (e.currentTarget.style.borderColor = 'var(--border)')}
          />
          <div className="flex gap-2 justify-end">
            <button onClick={() => { setShowNoteInput(false); setNoteText(''); }} className="text-[10px] px-3 py-1 rounded" style={{ color: 'var(--text-muted)' }}>Cancel</button>
            <button onClick={handleAddNote} className="text-[10px] px-3 py-1 rounded font-semibold" style={{ background: 'var(--gold)', color: '#000' }}>Save Note</button>
          </div>
        </div>
      )}

      {/* Assign input */}
      {showAssignInput && (
        <div className="rounded-lg p-3 space-y-2" style={{ background: 'var(--raised)', border: '1px solid var(--gold-border)' }}>
          <input
            value={assignText}
            onChange={e => setAssignText(e.target.value)}
            placeholder="Installer name..."
            autoFocus
            className="w-full text-xs rounded-lg p-2"
            style={{ background: 'var(--bg-secondary)', color: 'var(--text-primary)', border: '1px solid var(--border)', outline: 'none' }}
            onFocus={e => (e.currentTarget.style.borderColor = 'var(--gold-border)')}
            onBlur={e => (e.currentTarget.style.borderColor = 'var(--border)')}
            onKeyDown={e => { if (e.key === 'Enter') handleAssign(); if (e.key === 'Escape') setShowAssignInput(false); }}
          />
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowAssignInput(false)} className="text-[10px] px-3 py-1 rounded" style={{ color: 'var(--text-muted)' }}>Cancel</button>
            <button onClick={handleAssign} className="text-[10px] px-3 py-1 rounded font-semibold" style={{ background: 'var(--gold)', color: '#000' }}>Assign</button>
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="grid grid-cols-2 gap-2 pt-2">
        {/* Update Status */}
        <button
          onClick={handleUpdateStatus}
          disabled={!nextStatus}
          className="text-xs font-medium py-2 px-3 rounded-lg transition flex items-center justify-center gap-1.5"
          style={{
            background: nextStatus ? 'var(--gold-pale)' : 'var(--raised)',
            border: `1px solid ${nextStatus ? 'var(--gold-border)' : 'var(--border)'}`,
            color: nextStatus ? 'var(--gold)' : 'var(--text-muted)',
            cursor: nextStatus ? 'pointer' : 'default',
            opacity: nextStatus ? 1 : 0.5,
          }}
        >
          <ChevronRight className="w-3 h-3" />
          {nextStatus ? `Move to ${nextStatus}` : 'Complete'}
        </button>

        {/* Add Note */}
        <button
          onClick={() => setShowNoteInput(!showNoteInput)}
          className="text-xs font-medium py-2 px-3 rounded-lg transition flex items-center justify-center gap-1.5"
          style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold-border)'; e.currentTarget.style.color = 'var(--gold)'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
        >
          <Plus className="w-3 h-3" />
          Add Note
        </button>

        {/* Assign Installer */}
        <button
          onClick={() => { setAssignText(job.assignedTo); setShowAssignInput(!showAssignInput); }}
          className="text-xs font-medium py-2 px-3 rounded-lg transition flex items-center justify-center gap-1.5"
          style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold-border)'; e.currentTarget.style.color = 'var(--gold)'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
        >
          <UserPlus className="w-3 h-3" />
          Assign Installer
        </button>

        {/* View Quote */}
        <button
          onClick={handleViewQuote}
          className="text-xs font-medium py-2 px-3 rounded-lg transition flex items-center justify-center gap-1.5"
          style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold-border)'; e.currentTarget.style.color = 'var(--gold)'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
        >
          <ExternalLink className="w-3 h-3" />
          View Quote
        </button>
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
