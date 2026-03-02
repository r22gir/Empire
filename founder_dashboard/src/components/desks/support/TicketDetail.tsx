'use client';
import { type SupportTicket, type TicketStatus } from '@/lib/deskData';
import { User, Clock, Tag, AlertTriangle, MessageSquare } from 'lucide-react';
import { StatusBadge } from '../shared';

const PRIORITY_COLOR: Record<string, string> = {
  high: '#ef4444', medium: '#f59e0b', low: '#22c55e',
};

const STATUS_COLOR: Record<TicketStatus, string> = {
  open: '#ef4444', in_progress: '#f59e0b', resolved: '#22c55e', closed: 'var(--text-muted)',
};

interface TicketDetailProps {
  ticket: SupportTicket;
  onClientClick?: (clientName: string) => void;
}

export default function TicketDetail({ ticket, onClientClick }: TicketDetailProps) {
  return (
    <div className="space-y-5">
      {/* Status + priority */}
      <div className="flex items-center gap-2">
        <StatusBadge label={ticket.status.replace('_', ' ')} color={STATUS_COLOR[ticket.status]} />
        <StatusBadge label={ticket.priority} color={PRIORITY_COLOR[ticket.priority]} />
        <span className="text-[10px] font-mono ml-auto" style={{ color: 'var(--text-muted)' }}>{ticket.id.toUpperCase()}</span>
      </div>

      {/* Issue */}
      <div className="rounded-lg p-3" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
        <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{ticket.issue}</p>
      </div>

      {/* Details */}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <User className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
          <span className="text-[10px] w-20 shrink-0" style={{ color: 'var(--text-muted)' }}>Client</span>
          <button
            onClick={() => onClientClick?.(ticket.client)}
            className="text-xs font-semibold transition"
            style={{ color: 'var(--gold)', cursor: 'pointer' }}
            onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
            onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
          >
            {ticket.client}
          </button>
        </div>
        <InfoRow icon={Tag} label="Category">{ticket.category}</InfoRow>
        <InfoRow icon={Clock} label="Created">{ticket.createdAt}</InfoRow>
        <InfoRow icon={User} label="Assigned To">{ticket.assignedTo}</InfoRow>
      </div>

      {/* Resolution history timeline */}
      <div>
        <p className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--text-muted)' }}>Resolution History</p>
        <div className="relative pl-4">
          <div className="absolute left-[5px] top-0 bottom-0 w-px" style={{ background: 'var(--border)' }} />
          {ticket.resolutionHistory.map((entry, i) => (
            <div key={i} className="relative mb-3 last:mb-0">
              <div className="absolute -left-4 top-1 w-2.5 h-2.5 rounded-full"
                style={{ background: i === ticket.resolutionHistory.length - 1 ? 'var(--gold)' : 'var(--text-muted)', border: '2px solid var(--surface)' }} />
              <div className="rounded-lg p-2.5 ml-1" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
                <p className="text-xs" style={{ color: 'var(--text-primary)' }}>{entry.action}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>{entry.date}</span>
                  <span className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>{entry.by}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="grid grid-cols-2 gap-2 pt-2">
        {['Reply to Client', 'Update Status', 'Reassign', 'Escalate'].map(label => (
          <button key={label}
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
