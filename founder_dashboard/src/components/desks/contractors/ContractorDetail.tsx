'use client';
import { type Contractor } from '@/lib/deskData';
import { Phone, Star, Wrench, CheckCircle2, XCircle, DollarSign, Tag } from 'lucide-react';

const fmt = (n: number) => '$' + n.toLocaleString();

interface ContractorDetailProps {
  contractor: Contractor;
}

export default function ContractorDetail({ contractor }: ContractorDetailProps) {
  return (
    <div className="space-y-5">
      {/* Avatar + name */}
      <div className="flex items-center gap-4">
        <div className="w-14 h-14 rounded-full flex items-center justify-center text-xl font-bold shrink-0"
          style={{ background: 'rgba(249,115,22,0.15)', color: '#F97316' }}>
          {contractor.name.charAt(0)}
        </div>
        <div>
          <p className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>{contractor.name}</p>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{contractor.specialty}</p>
          <div className="flex items-center gap-1 mt-1">
            {contractor.available
              ? <><CheckCircle2 className="w-3.5 h-3.5" style={{ color: '#22c55e' }} /><span className="text-[10px]" style={{ color: '#22c55e' }}>Available</span></>
              : <><XCircle className="w-3.5 h-3.5" style={{ color: '#ef4444' }} /><span className="text-[10px]" style={{ color: '#ef4444' }}>Unavailable</span></>
            }
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { value: contractor.jobsCompleted, label: 'Jobs Done', color: 'var(--gold)' },
          { value: contractor.rating, label: 'Rating', color: '#F97316' },
          { value: `${fmt(contractor.rate)}/hr`, label: 'Rate', color: 'var(--purple)' },
        ].map(stat => (
          <div key={stat.label} className="rounded-lg p-2.5 text-center" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
            <p className="text-lg font-bold" style={{ color: stat.color }}>{stat.value}</p>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Contact */}
      <div className="flex items-center gap-3">
        <Phone className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
        <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{contractor.phone}</span>
      </div>

      {/* Skills */}
      <div>
        <div className="flex items-center gap-1.5 mb-2">
          <Tag className="w-3 h-3" style={{ color: 'var(--gold)' }} />
          <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Skills</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {contractor.skills.map(skill => (
            <span key={skill} className="text-[10px] px-2 py-0.5 rounded-full"
              style={{ background: 'var(--gold-pale)', color: 'var(--gold)', border: '1px solid var(--gold-border)' }}>
              {skill}
            </span>
          ))}
        </div>
      </div>

      {/* Notes */}
      {contractor.notes && (
        <div className="rounded-lg p-3" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
          <p className="text-[10px] font-semibold mb-1" style={{ color: 'var(--gold)' }}>Notes</p>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{contractor.notes}</p>
        </div>
      )}

      {/* Pay History */}
      <div>
        <div className="flex items-center gap-1.5 mb-2">
          <DollarSign className="w-3 h-3" style={{ color: '#22c55e' }} />
          <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Recent Pay History</span>
        </div>
        <div className="space-y-1.5">
          {contractor.payHistory.map((pay, i) => (
            <div key={i} className="flex items-center justify-between rounded-lg px-3 py-2" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
              <div>
                <p className="text-xs" style={{ color: 'var(--text-primary)' }}>{pay.job}</p>
                <p className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>{pay.date}</p>
              </div>
              <span className="text-xs font-mono font-semibold" style={{ color: '#22c55e' }}>{fmt(pay.amount)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Actions */}
      <div className="grid grid-cols-2 gap-2 pt-2">
        {['Schedule Job', 'Send Message', 'View All Pay', 'Edit Profile'].map(label => (
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
