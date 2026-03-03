'use client';
import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { MOCK_CLIENTS, Client } from '@/lib/deskData';
import { Users, Phone, Mail } from 'lucide-react';
import { StatsBar, SearchInput, DataTable, StatusBadge, type Column, TaskList, DetailPanel } from './shared';
import ClientDetail from './clients/ClientDetail';

const STATUS_COLORS: Record<string, string> = {
  active: '#22c55e', prospect: '#8b5cf6', inactive: '#78716c',
};

const fmt = (n: number) => '$' + n.toLocaleString();

export default function ClientsDesk() {
  const [clients, setClients] = useState<Client[]>(MOCK_CLIENTS);
  const [search, setSearch] = useState('');
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);

  const handleClientUpdated = (updated: Client) => {
    setClients(prev => prev.map(c => c.id === updated.id ? updated : c));
    setSelectedClient(updated);
  };
  const searchParams = useSearchParams();

  // Handle cross-desk navigation: pre-filter and auto-select from query param
  useEffect(() => {
    const filterParam = searchParams.get('filter');
    if (filterParam) {
      setSearch(filterParam);
      const match = clients.find(c => c.name.toLowerCase() === filterParam.toLowerCase());
      if (match) setSelectedClient(match);
    }
  }, [searchParams, clients]);

  const filtered = clients.filter(c =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.email.toLowerCase().includes(search.toLowerCase())
  );

  const totalClients = clients.filter(c => c.status === 'active').length;
  const totalRevenue = clients.reduce((s, c) => s + c.totalSpent, 0);
  const prospects = clients.filter(c => c.status === 'prospect').length;

  const columns: Column<Client>[] = [
    { key: 'name', label: 'Client', render: c => <span className="font-medium">{c.name}</span> },
    { key: 'phone', label: 'Contact', render: c => <span style={{ color: 'var(--text-secondary)' }}>{c.phone}</span> },
    { key: 'status', label: 'Status', render: c => <StatusBadge label={c.status} color={STATUS_COLORS[c.status]} /> },
    { key: 'totalJobs', label: 'Jobs', render: c => <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>{c.totalJobs}</span> },
    { key: 'totalSpent', label: 'Revenue', render: c => <span className="font-mono font-semibold" style={{ color: 'var(--gold)' }}>{fmt(c.totalSpent)}</span> },
    { key: 'lastContact', label: 'Last Contact', render: c => <span className="font-mono" style={{ color: 'var(--text-muted)' }}>{c.lastContact}</span> },
  ];

  return (
    <div className="flex flex-col h-full">
      <StatsBar items={[
        { label: 'Active Clients', value: String(totalClients), icon: Users, color: '#06B6D4' },
        { label: 'Total Revenue', value: fmt(totalRevenue), icon: Phone, color: 'var(--gold)' },
        { label: 'Prospects', value: String(prospects), icon: Mail, color: 'var(--purple)' },
      ]} />

      <div className="px-4 pt-3 pb-2 shrink-0">
        <SearchInput value={search} onChange={setSearch} placeholder="Search clients..." />
      </div>

      <div className="flex-1 overflow-auto p-4">
        <div className="flex flex-col gap-4">
          <DataTable columns={columns} data={filtered} getRowId={c => c.id}
            onRowClick={c => setSelectedClient(c)} selectedId={selectedClient?.id} />
          <TaskList desk="clients" compact />
        </div>
      </div>

      <DetailPanel open={!!selectedClient} onClose={() => setSelectedClient(null)} title={selectedClient?.name || ''}>
        {selectedClient && <ClientDetail client={selectedClient} onClientUpdated={handleClientUpdated} />}
      </DetailPanel>
    </div>
  );
}
