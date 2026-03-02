'use client';
import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { MOCK_TICKETS, TICKET_STATUSES, SupportTicket, TicketStatus } from '@/lib/deskData';
import { Headphones, AlertTriangle, CheckCircle2, Clock } from 'lucide-react';
import { StatsBar, FilterTabs, StatusBadge, TaskList, DetailPanel } from './shared';
import TicketDetail from './support/TicketDetail';

const PRIORITY_COLOR: Record<string, string> = {
  high: '#ef4444',
  medium: '#f59e0b',
  low: '#22c55e',
};

const STATUS_COLOR: Record<TicketStatus, string> = {
  open: '#ef4444',
  in_progress: '#f59e0b',
  resolved: '#22c55e',
  closed: 'var(--text-muted)',
};

export default function SupportDesk() {
  const [tickets] = useState<SupportTicket[]>(MOCK_TICKETS);
  const [filter, setFilter] = useState<string>('all');
  const [selectedTicket, setSelectedTicket] = useState<SupportTicket | null>(null);
  const router = useRouter();

  const openCount = tickets.filter(t => t.status === 'open').length;
  const inProgress = tickets.filter(t => t.status === 'in_progress').length;
  const resolvedCount = tickets.filter(t => t.status === 'resolved').length;
  const filtered = filter === 'all' ? tickets : tickets.filter(t => t.status === filter);

  const handleClientClick = useCallback((clientName: string) => {
    router.push(`/desk/clients?filter=${encodeURIComponent(clientName)}`);
  }, [router]);

  return (
    <div className="flex flex-col h-full">
      <StatsBar items={[
        { label: 'Open Tickets', value: String(openCount), icon: AlertTriangle, color: '#ef4444' },
        { label: 'In Progress', value: String(inProgress), icon: Clock, color: '#f59e0b' },
        { label: 'Resolved', value: String(resolvedCount), icon: CheckCircle2, color: '#22c55e' },
      ]} />

      <FilterTabs options={['all', ...TICKET_STATUSES]} active={filter} onChange={setFilter} />

      <div className="flex-1 overflow-auto p-4">
        <div className="flex flex-col gap-4">
          <div className="space-y-2">
            {filtered.map(ticket => (
              <div
                key={ticket.id}
                className="rounded-xl p-4 transition cursor-pointer"
                style={{
                  background: selectedTicket?.id === ticket.id ? 'var(--gold-pale)' : 'var(--surface)',
                  border: selectedTicket?.id === ticket.id ? '1px solid var(--gold-border)' : '1px solid var(--border)',
                }}
                onClick={() => setSelectedTicket(ticket)}
                onMouseEnter={e => { if (selectedTicket?.id !== ticket.id) e.currentTarget.style.background = 'var(--hover)'; }}
                onMouseLeave={e => { if (selectedTicket?.id !== ticket.id) e.currentTarget.style.background = 'var(--surface)'; }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1.5">
                      <StatusBadge label={ticket.status.replace('_', ' ')} color={STATUS_COLOR[ticket.status]} />
                      <StatusBadge label={ticket.priority} color={PRIORITY_COLOR[ticket.priority]} />
                      <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>
                        {ticket.category}
                      </span>
                    </div>
                    <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{ticket.issue}</p>
                    <div className="flex items-center gap-3 mt-2">
                      <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Client: {ticket.client}</span>
                      <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>{ticket.createdAt}</span>
                    </div>
                  </div>
                  <Headphones className="w-4 h-4 shrink-0 ml-3" style={{ color: 'var(--text-muted)' }} />
                </div>
              </div>
            ))}
            {filtered.length === 0 && (
              <p className="text-center py-8 text-sm" style={{ color: 'var(--text-muted)' }}>No tickets match filter</p>
            )}
          </div>
          <TaskList desk="support" compact />
        </div>
      </div>

      <DetailPanel open={!!selectedTicket} onClose={() => setSelectedTicket(null)} title={selectedTicket ? `Ticket ${selectedTicket.id.toUpperCase()}` : ''}>
        {selectedTicket && <TicketDetail ticket={selectedTicket} onClientClick={handleClientClick} />}
      </DetailPanel>
    </div>
  );
}
