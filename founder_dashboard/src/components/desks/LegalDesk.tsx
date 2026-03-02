'use client';
import { useState } from 'react';
import { Scale, FileText, AlertTriangle } from 'lucide-react';
import { StatsBar, FilterTabs, StatusBadge, TaskList } from './shared';

type DocStatus = 'active' | 'expiring' | 'expired' | 'draft';

interface LegalDoc {
  id: string;
  title: string;
  type: string;
  status: DocStatus;
  expiresAt: string;
  lastReviewed: string;
}

const STATUS_COLOR: Record<DocStatus, string> = {
  active: '#22c55e',
  expiring: '#f59e0b',
  expired: '#ef4444',
  draft: 'var(--text-muted)',
};

const MOCK_DOCS: LegalDoc[] = [
  { id: 'ld1', title: 'Standard Client Contract',       type: 'Contract',   status: 'active',   expiresAt: '2027-01-15', lastReviewed: '2026-01-10' },
  { id: 'ld2', title: 'Installer Subcontractor Agreement', type: 'Agreement', status: 'active',   expiresAt: '2026-12-31', lastReviewed: '2025-12-20' },
  { id: 'ld3', title: 'General Liability Insurance',    type: 'Insurance',  status: 'active',   expiresAt: '2026-08-15', lastReviewed: '2026-02-01' },
  { id: 'ld4', title: 'Workers Comp Policy',             type: 'Insurance',  status: 'expiring', expiresAt: '2026-03-30', lastReviewed: '2025-09-15' },
  { id: 'ld5', title: 'LLC Operating Agreement',         type: 'Corporate',  status: 'active',   expiresAt: '',           lastReviewed: '2025-06-10' },
  { id: 'ld6', title: 'Website Terms of Service',        type: 'Compliance', status: 'draft',    expiresAt: '',           lastReviewed: '' },
  { id: 'ld7', title: 'Privacy Policy',                  type: 'Compliance', status: 'active',   expiresAt: '',           lastReviewed: '2025-11-20' },
  { id: 'ld8', title: 'Vendor NDA Template',             type: 'Agreement',  status: 'active',   expiresAt: '2027-06-01', lastReviewed: '2026-01-15' },
  { id: 'ld9', title: 'Commercial Property Lease',       type: 'Lease',      status: 'expiring', expiresAt: '2026-04-30', lastReviewed: '2025-10-01' },
];

export default function LegalDesk() {
  const [docs] = useState<LegalDoc[]>(MOCK_DOCS);
  const [filter, setFilter] = useState<string>('all');

  const active = docs.filter(d => d.status === 'active').length;
  const expiring = docs.filter(d => d.status === 'expiring').length;
  const drafts = docs.filter(d => d.status === 'draft').length;
  const filtered = filter === 'all' ? docs : docs.filter(d => d.status === filter);

  return (
    <div className="flex flex-col h-full">
      <StatsBar items={[
        { label: 'Active Docs', value: String(active), icon: FileText, color: '#22c55e' },
        { label: 'Expiring Soon', value: String(expiring), icon: AlertTriangle, color: '#f59e0b' },
        { label: 'Drafts', value: String(drafts), icon: Scale, color: 'var(--text-muted)' },
      ]} />

      <FilterTabs options={['all', 'active', 'expiring', 'expired', 'draft']} active={filter} onChange={setFilter} />

      <div className="flex-1 overflow-auto p-4 flex gap-4">
        <div className="flex-1 flex flex-col gap-4">
          <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
            <table className="w-full text-xs">
              <thead>
                <tr style={{ background: 'var(--elevated)' }}>
                  {['Document', 'Type', 'Status', 'Expires', 'Last Reviewed'].map(h => (
                    <th key={h} className="text-left px-4 py-2.5 font-semibold" style={{ color: 'var(--gold)', borderBottom: '1px solid var(--border)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map(doc => (
                  <tr
                    key={doc.id}
                    className="transition"
                    style={{ borderBottom: '1px solid var(--border)' }}
                    onMouseEnter={e => (e.currentTarget.style.background = 'var(--hover)')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td className="px-4 py-2.5 font-medium flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                      <FileText className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
                      {doc.title}
                    </td>
                    <td className="px-4 py-2.5" style={{ color: 'var(--text-secondary)' }}>{doc.type}</td>
                    <td className="px-4 py-2.5">
                      <StatusBadge label={doc.status} color={STATUS_COLOR[doc.status]} />
                    </td>
                    <td className="px-4 py-2.5 font-mono" style={{ color: doc.status === 'expiring' ? '#f59e0b' : 'var(--text-muted)' }}>
                      {doc.expiresAt || '—'}
                    </td>
                    <td className="px-4 py-2.5 font-mono" style={{ color: 'var(--text-muted)' }}>
                      {doc.lastReviewed || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {filtered.length === 0 && (
            <p className="text-center py-8 text-sm" style={{ color: 'var(--text-muted)' }}>No documents match filter</p>
          )}
          <TaskList desk="legal" compact />
        </div>
      </div>
    </div>
  );
}
