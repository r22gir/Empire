'use client';
import { type Client, MOCK_JOBS } from '@/lib/deskData';
import { Mail, Phone, MapPin, Briefcase, DollarSign, Calendar } from 'lucide-react';
import { StatusBadge } from '../shared';

const STATUS_COLORS: Record<string, string> = {
  active: '#22c55e', prospect: '#8b5cf6', inactive: '#78716c',
};

const fmt = (n: number) => '$' + n.toLocaleString();

interface ClientDetailProps {
  client: Client;
}

export default function ClientDetail({ client }: ClientDetailProps) {
  const clientJobs = MOCK_JOBS.filter(j => j.client === client.name);

  return (
    <div className="space-y-5">
      {/* Avatar + status */}
      <div className="flex items-center gap-4">
        <div className="w-14 h-14 rounded-full flex items-center justify-center text-xl font-bold shrink-0"
          style={{ background: 'rgba(6,182,212,0.15)', color: '#06B6D4' }}>
          {client.name.charAt(0)}
        </div>
        <div>
          <p className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>{client.name}</p>
          <StatusBadge label={client.status} color={STATUS_COLORS[client.status]} />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { value: client.totalJobs, label: 'Jobs', color: 'var(--gold)' },
          { value: fmt(client.totalSpent), label: 'Total Spent', color: '#22c55e' },
          { value: client.lastContact, label: 'Last Contact', color: 'var(--text-secondary)' },
        ].map(stat => (
          <div key={stat.label} className="rounded-lg p-2.5 text-center" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
            <p className="text-sm font-bold" style={{ color: stat.color }}>{stat.value}</p>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Contact info */}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <Mail className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
          <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{client.email}</span>
        </div>
        <div className="flex items-center gap-3">
          <Phone className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
          <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{client.phone}</span>
        </div>
        <div className="flex items-center gap-3">
          <MapPin className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
          <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{client.address}</span>
        </div>
      </div>

      {/* Past jobs */}
      {clientJobs.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <Briefcase className="w-3 h-3" style={{ color: 'var(--gold)' }} />
            <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Jobs</span>
          </div>
          <div className="space-y-1.5">
            {clientJobs.map(job => (
              <div key={job.id} className="flex items-center justify-between rounded-lg px-3 py-2"
                style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
                <div>
                  <p className="text-xs" style={{ color: 'var(--text-primary)' }}>{job.name}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{job.treatmentType}</span>
                    <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>{job.dueDate}</span>
                  </div>
                </div>
                <StatusBadge label={job.status} color={
                  job.status === 'Complete' ? '#22c55e' : job.status === 'New' ? 'var(--purple)' : 'var(--gold)'
                } />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="grid grid-cols-2 gap-2 pt-2">
        {['Send Email', 'Create Job', 'View Invoices', 'Edit Profile'].map(label => (
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
