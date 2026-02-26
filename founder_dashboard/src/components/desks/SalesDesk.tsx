'use client';
import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { MOCK_LEADS, Lead } from '@/lib/deskData';
import { Users, Target, TrendingUp, Phone } from 'lucide-react';
import { StatsBar, TaskList, DetailPanel } from './shared';
import SalesPipeline from './sales/SalesPipeline';
import LeadDetail from './sales/LeadDetail';

const fmt = (n: number) => '$' + n.toLocaleString();

export default function SalesDesk() {
  const [leads] = useState<Lead[]>(MOCK_LEADS);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const router = useRouter();

  const wonLeads = leads.filter(l => l.stage === 'Won');
  const lostLeads = leads.filter(l => l.stage === 'Lost');
  const total = wonLeads.length + lostLeads.length;
  const convRate = total > 0 ? ((wonLeads.length / total) * 100).toFixed(0) : '0';
  const avgQuote = leads.length > 0 ? Math.round(leads.reduce((s, l) => s + l.estimatedValue, 0) / leads.length) : 0;
  const newLeads = leads.filter(l => l.stage === 'New Lead').length;
  const pipelineVal = leads.filter(l => l.stage !== 'Won' && l.stage !== 'Lost').reduce((s, l) => s + l.estimatedValue, 0);

  const handleClientClick = useCallback((clientName: string) => {
    router.push(`/desk/clients?filter=${encodeURIComponent(clientName)}`);
  }, [router]);

  return (
    <div className="flex flex-col h-full">
      <StatsBar items={[
        { label: 'Conversion Rate', value: convRate + '%', icon: Target, color: '#22c55e' },
        { label: 'Avg Quote Value', value: fmt(avgQuote), icon: TrendingUp, color: 'var(--gold)' },
        { label: 'New Leads', value: String(newLeads), icon: Users, color: 'var(--purple)' },
        { label: 'Pipeline Value', value: fmt(pipelineVal), icon: Phone, color: 'var(--cyan)' },
      ]} />
      <div className="flex-1 overflow-auto p-4">
        <SalesPipeline leads={leads} onLeadClick={lead => setSelectedLead(lead)} />
      </div>
      <div className="p-4 pt-0">
        <TaskList desk="sales" compact />
      </div>

      <DetailPanel open={!!selectedLead} onClose={() => setSelectedLead(null)} title={selectedLead ? `${selectedLead.client} — ${selectedLead.projectType}` : ''}>
        {selectedLead && <LeadDetail lead={selectedLead} onClientClick={handleClientClick} />}
      </DetailPanel>
    </div>
  );
}
