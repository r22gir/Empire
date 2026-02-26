'use client';
import { type Lead, type LeadStage } from '@/lib/deskData';
import { Phone, Mail, Calendar, DollarSign, MessageSquare, ArrowRight } from 'lucide-react';
import { StatusBadge } from '../shared';

const STAGE_COLOR: Record<LeadStage, string> = {
  'New Lead': 'var(--purple)', 'Quoted': 'var(--gold)', 'Follow-up': 'var(--cyan)',
  'Won': '#22c55e', 'Lost': '#ef4444',
};

const INTERACTION_ICON: Record<string, string> = {
  call: '📞', email: '📧', meeting: '🤝', text: '💬',
};

const fmt = (n: number) => '$' + n.toLocaleString();

interface LeadDetailProps {
  lead: Lead;
  onClientClick?: (clientName: string) => void;
}

export default function LeadDetail({ lead, onClientClick }: LeadDetailProps) {
  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <StatusBadge label={lead.stage} color={STAGE_COLOR[lead.stage]} />
        <span className="text-lg font-bold font-mono" style={{ color: 'var(--gold)' }}>{fmt(lead.estimatedValue)}</span>
      </div>

      {/* Contact info */}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <DollarSign className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
          <span className="text-[10px] w-20 shrink-0" style={{ color: 'var(--text-muted)' }}>Client</span>
          <button
            onClick={() => onClientClick?.(lead.client)}
            className="text-xs font-semibold transition"
            style={{ color: 'var(--gold)', cursor: 'pointer' }}
            onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
            onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
          >
            {lead.client}
          </button>
        </div>
        <InfoRow icon={Phone} label="Phone">{lead.phone}</InfoRow>
        <InfoRow icon={Mail} label="Email">{lead.email}</InfoRow>
        <InfoRow icon={MessageSquare} label="Project">{lead.projectType}</InfoRow>
        <InfoRow icon={Calendar} label="Last Contact">{lead.lastContact}</InfoRow>
      </div>

      {/* Notes */}
      {lead.notes && (
        <div className="rounded-lg p-3" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
          <p className="text-[10px] font-semibold mb-1" style={{ color: 'var(--gold)' }}>Notes</p>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{lead.notes}</p>
        </div>
      )}

      {/* Interaction history */}
      <div>
        <p className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--text-muted)' }}>Interaction History</p>
        <div className="space-y-2">
          {lead.interactions.map((int, i) => (
            <div key={i} className="flex gap-3 rounded-lg p-2.5" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
              <span className="text-sm shrink-0">{INTERACTION_ICON[int.type] || '📋'}</span>
              <div className="flex-1 min-w-0">
                <p className="text-xs" style={{ color: 'var(--text-primary)' }}>{int.summary}</p>
                <p className="text-[10px] font-mono mt-1" style={{ color: 'var(--text-muted)' }}>{int.date} · {int.type}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="grid grid-cols-2 gap-2 pt-2">
        <ActionBtn label="Move Stage" icon={ArrowRight} />
        <ActionBtn label="Log Interaction" icon={MessageSquare} />
        <ActionBtn label="Send Quote" icon={Mail} />
        <ActionBtn label="Schedule Follow-up" icon={Calendar} />
      </div>
    </div>
  );
}

function InfoRow({ icon: Icon, label, children }: { icon: typeof Phone; label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      <Icon className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
      <span className="text-[10px] w-20 shrink-0" style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span className="text-xs" style={{ color: 'var(--text-primary)' }}>{children}</span>
    </div>
  );
}

function ActionBtn({ label, icon: Icon }: { label: string; icon?: typeof Phone }) {
  return (
    <button
      className="text-xs font-medium py-2 px-3 rounded-lg transition flex items-center gap-1.5 justify-center"
      style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold-border)'; e.currentTarget.style.color = 'var(--gold)'; }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
    >
      {Icon && <Icon className="w-3 h-3" />}
      {label}
    </button>
  );
}
