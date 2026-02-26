'use client';
import { useState } from 'react';
import { MOCK_CLIENTS, Client } from '@/lib/deskData';
import { Users, Phone, Mail, MapPin } from 'lucide-react';
import { StatsBar, SearchInput, DataTable, StatusBadge, type Column, TaskList } from './shared';

const STATUS_COLORS: Record<string, string> = {
  active: '#22c55e', prospect: '#8b5cf6', inactive: '#78716c',
};

const fmt = (n: number) => '$' + n.toLocaleString();

export default function ClientsDesk() {
  const [clients] = useState<Client[]>(MOCK_CLIENTS);
  const [search, setSearch] = useState('');
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);

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

      <div className="flex-1 overflow-auto p-4 flex gap-4">
        <div className="flex-1 flex flex-col gap-4">
          <DataTable columns={columns} data={filtered} getRowId={c => c.id}
            onRowClick={c => setSelectedClient(c)} selectedId={selectedClient?.id} />
          <TaskList desk="clients" compact />
        </div>

        {selectedClient && (
          <div className="w-[280px] shrink-0 rounded-xl p-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold" style={{ background: 'rgba(6,182,212,0.15)', color: '#06B6D4' }}>
                {selectedClient.name.charAt(0)}
              </div>
              <div>
                <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{selectedClient.name}</p>
                <StatusBadge label={selectedClient.status} color={STATUS_COLORS[selectedClient.status]} />
              </div>
            </div>
            <div className="space-y-3">
              {[
                { icon: Mail, label: selectedClient.email },
                { icon: Phone, label: selectedClient.phone },
                { icon: MapPin, label: selectedClient.address },
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-2">
                  <item.icon className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
                  <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{item.label}</span>
                </div>
              ))}
            </div>
            <div className="mt-4 pt-4 grid grid-cols-2 gap-3" style={{ borderTop: '1px solid var(--border)' }}>
              <div className="rounded-lg p-2.5 text-center" style={{ background: 'var(--raised)' }}>
                <p className="text-lg font-bold" style={{ color: 'var(--gold)' }}>{selectedClient.totalJobs}</p>
                <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>Jobs</p>
              </div>
              <div className="rounded-lg p-2.5 text-center" style={{ background: 'var(--raised)' }}>
                <p className="text-lg font-bold" style={{ color: '#22c55e' }}>{fmt(selectedClient.totalSpent)}</p>
                <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>Revenue</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
