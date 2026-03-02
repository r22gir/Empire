'use client';
import { useState } from 'react';
import { MOCK_CONTRACTORS, Contractor } from '@/lib/deskData';
import { Wrench, Star, CheckCircle2, XCircle } from 'lucide-react';
import { StatsBar, TaskList, DetailPanel } from './shared';
import ContractorDetail from './contractors/ContractorDetail';

const fmt = (n: number) => '$' + n.toLocaleString();

export default function ContractorsDesk() {
  const [contractors] = useState<Contractor[]>(MOCK_CONTRACTORS);
  const [selected, setSelected] = useState<Contractor | null>(null);

  const available = contractors.filter(c => c.available).length;
  const avgRate = Math.round(contractors.reduce((s, c) => s + c.rate, 0) / contractors.length);
  const totalJobs = contractors.reduce((s, c) => s + c.jobsCompleted, 0);

  return (
    <div className="flex flex-col h-full">
      <StatsBar items={[
        { label: 'Available', value: `${available}/${contractors.length}`, icon: CheckCircle2, color: '#22c55e' },
        { label: 'Avg Rate', value: `${fmt(avgRate)}/hr`, icon: Wrench, color: '#F97316' },
        { label: 'Total Jobs Done', value: String(totalJobs), icon: Star, color: 'var(--gold)' },
      ]} />

      <div className="flex-1 overflow-auto p-4">
        <div className="space-y-2">
          {contractors.map(c => (
            <div key={c.id} onClick={() => setSelected(c)}
              className="rounded-xl p-3 flex items-center gap-4 cursor-pointer transition"
              style={{
                background: selected?.id === c.id ? 'var(--gold-pale)' : 'var(--surface)',
                border: selected?.id === c.id ? '1px solid var(--gold-border)' : '1px solid var(--border)',
              }}
              onMouseEnter={e => { if (selected?.id !== c.id) e.currentTarget.style.background = 'var(--hover)'; }}
              onMouseLeave={e => { if (selected?.id !== c.id) e.currentTarget.style.background = 'var(--surface)'; }}
            >
              <div className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold shrink-0"
                style={{ background: 'rgba(249,115,22,0.15)', color: '#F97316' }}>
                {c.name.charAt(0)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{c.name}</p>
                <p className="text-[10px]" style={{ color: 'var(--text-secondary)' }}>{c.specialty}</p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <div className="flex items-center gap-0.5">
                  <Star className="w-3 h-3" style={{ color: 'var(--gold)', fill: 'var(--gold)' }} />
                  <span className="text-xs font-mono" style={{ color: 'var(--gold)' }}>{c.rating}</span>
                </div>
                <span className="text-xs font-mono font-semibold" style={{ color: '#F97316' }}>{fmt(c.rate)}/hr</span>
                {c.available ? <CheckCircle2 className="w-4 h-4" style={{ color: '#22c55e' }} /> : <XCircle className="w-4 h-4" style={{ color: '#ef4444' }} />}
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4">
          <TaskList desk="contractors" compact />
        </div>
      </div>

      <DetailPanel open={!!selected} onClose={() => setSelected(null)} title={selected?.name || ''}>
        {selected && <ContractorDetail contractor={selected} />}
      </DetailPanel>
    </div>
  );
}
