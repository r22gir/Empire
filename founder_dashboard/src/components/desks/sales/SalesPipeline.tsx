'use client';
import { type Lead, type LeadStage, LEAD_STAGES } from '@/lib/deskData';
import { Phone } from 'lucide-react';
import { type KanbanColumn } from '../shared';

const STAGE_COLORS: Record<LeadStage, string> = {
  'New Lead': 'var(--purple)', 'Quoted': 'var(--gold)', 'Follow-up': 'var(--cyan)',
  'Won': '#22c55e', 'Lost': '#ef4444',
};

const STAGE_BG: Record<LeadStage, string> = {
  'New Lead': 'var(--purple-pale)', 'Quoted': 'var(--gold-pale)',
  'Follow-up': 'rgba(34,211,238,0.07)', 'Won': 'rgba(34,197,94,0.07)',
  'Lost': 'rgba(239,68,68,0.07)',
};

const fmt = (n: number) => '$' + n.toLocaleString();

const COLUMNS: KanbanColumn[] = LEAD_STAGES.map(s => ({
  key: s, label: s, color: STAGE_COLORS[s],
}));

interface SalesPipelineProps {
  leads: Lead[];
}

export default function SalesPipeline({ leads }: SalesPipelineProps) {
  return (
    <div className="flex gap-3 h-full min-w-max">
      {COLUMNS.map(col => {
        const stage = col.key as LeadStage;
        const stageLeads = leads.filter(l => l.stage === stage);
        const stageTotal = stageLeads.reduce((s, l) => s + l.estimatedValue, 0);
        return (
          <div
            key={stage}
            className="w-[230px] flex flex-col rounded-xl shrink-0"
            style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
          >
            <div className="px-3 py-2.5 shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
              <div className="flex items-center gap-2 mb-1">
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: col.color }} />
                <span className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>{stage}</span>
                <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded-full font-mono" style={{ background: 'var(--raised)', color: 'var(--text-muted)' }}>
                  {stageLeads.length}
                </span>
              </div>
              <p className="text-[10px] font-mono" style={{ color: col.color }}>{fmt(stageTotal)}</p>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-2">
              {stageLeads.map(lead => (
                <div key={lead.id} className="rounded-lg p-2.5" style={{ background: STAGE_BG[stage], border: '1px solid var(--border)' }}>
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>{lead.client}</p>
                    <span className="text-[10px] font-mono font-semibold" style={{ color: 'var(--gold)' }}>{fmt(lead.estimatedValue)}</span>
                  </div>
                  <p className="text-[10px] mb-1.5" style={{ color: 'var(--text-secondary)' }}>{lead.projectType}</p>
                  <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{lead.notes}</p>
                  <div className="flex items-center justify-between mt-2 pt-1.5" style={{ borderTop: '1px solid var(--border)' }}>
                    <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>{lead.lastContact}</span>
                    <Phone className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
                  </div>
                </div>
              ))}
              {stageLeads.length === 0 && (
                <p className="text-[10px] text-center py-4" style={{ color: 'var(--text-muted)' }}>No leads</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
