'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Users, Plus, Upload, AlertCircle, Crown } from 'lucide-react';
import { API } from '../../../lib/api';
import DataTable, { Column } from '../shared/DataTable';
import SearchBar from '../shared/SearchBar';
import StatusBadge from '../shared/StatusBadge';
import EmptyState from '../shared/EmptyState';

interface Customer {
  id: string;
  name: string;
  email: string;
  phone: string;
  total_revenue: number;
  quote_count: number;
  status: string;
}

function fmt(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(n);
}

interface CustomerListProps {
  onSelectCustomer?: (id: string) => void;
  business?: string;
}

export default function CustomerList({ onSelectCustomer }: CustomerListProps = {}) {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [importing, setImporting] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  const fetchCustomers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/crm/customers`);
      if (!res.ok) throw new Error(`Failed to load customers (${res.status})`);
      const data = await res.json();
      setCustomers(Array.isArray(data) ? data : data.items || []);
    } catch (err: any) {
      setError(err.message);
      setCustomers([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchCustomers(); }, [fetchCustomers]);

  const handleImport = async () => {
    setImporting(true);
    try {
      const res = await fetch(`${API}/crm/customers/import-from-quotes`, { method: 'POST' });
      if (!res.ok) throw new Error(`Import failed (${res.status})`);
      fetchCustomers();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setImporting(false);
    }
  };

  const filtered = useMemo(() => {
    if (!search.trim()) return customers;
    const q = search.toLowerCase();
    return customers.filter(c =>
      c.name?.toLowerCase().includes(q) ||
      c.email?.toLowerCase().includes(q) ||
      c.phone?.includes(q)
    );
  }, [customers, search]);

  const columns: Column[] = [
    {
      key: 'name', label: 'Name', sortable: true,
      render: (r) => (
        <div className="flex items-center gap-2">
          <span className="font-medium text-[#1a1a1a]">{r.name}</span>
          {(r.total_revenue || 0) > 10000 && (
            <span title="VIP Customer"><Crown size={14} className="text-[#b8960c]" /></span>
          )}
        </div>
      ),
    },
    { key: 'email', label: 'Email', sortable: true },
    { key: 'phone', label: 'Phone' },
    { key: 'total_revenue', label: 'Revenue', sortable: true, render: (r) => (
      <span className="font-bold text-[#22c55e]">{fmt(r.total_revenue || 0)}</span>
    )},
    { key: 'quote_count', label: 'Quotes', sortable: true, render: (r) => r.quote_count ?? 0 },
    { key: 'status', label: 'Status', sortable: true, render: (r) => <StatusBadge status={r.status || 'active'} /> },
  ];

  return (
    <div className="bg-[#faf9f7] min-h-screen">
      <div className="max-w-6xl mx-auto" style={{ padding: '24px 36px' }}>
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#fdf8eb] flex items-center justify-center">
              <Users size={20} className="text-[#b8960c]" />
            </div>
            <h1 className="text-xl font-bold text-[#1a1a1a]">Customers</h1>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleImport}
              disabled={importing}
              className="flex items-center gap-2 px-4 py-2.5 text-xs font-bold text-[#555] bg-[#faf9f7] border border-[#ece8e0] hover:bg-white rounded-xl transition-colors disabled:opacity-50 cursor-pointer"
            >
              <Upload size={16} /> {importing ? 'Importing...' : 'Import from Quotes'}
            </button>
            <button className="flex items-center gap-2 px-4 py-2.5 text-xs font-bold text-white bg-[#b8960c] hover:bg-[#a68500] rounded-xl transition-colors cursor-pointer">
              <Plus size={16} /> Add Customer
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-4 empire-card flat" style={{ padding: 12, borderColor: '#fca5a5', background: '#fef2f2' }}>
            <div className="flex items-center gap-2 text-sm text-red-700">
              <AlertCircle size={16} /> {error}
            </div>
          </div>
        )}

        {/* Search */}
        <div className="mb-5 max-w-sm">
          <SearchBar value={search} onChange={setSearch} placeholder="Search customers..." />
        </div>

        {/* Table */}
        {!loading && filtered.length === 0 && !error ? (
          <EmptyState
            icon={<Users size={40} />}
            title={search ? 'No customers match your search' : 'No customers yet'}
            description={search ? 'Try a different search term.' : 'Add a customer or import from your quotes.'}
            action={!search ? { label: 'Import from Quotes', onClick: handleImport } : undefined}
          />
        ) : (
          <DataTable
            columns={columns}
            data={filtered}
            loading={loading}
            onRowClick={(row) => onSelectCustomer ? onSelectCustomer(row.id) : setExpanded(expanded === row.id ? null : row.id)}
            emptyMessage="No customers found."
          />
        )}

        {/* Inline Expand */}
        {expanded && (() => {
          const cust = customers.find(c => c.id === expanded);
          if (!cust) return null;
          return (
            <div className="mt-3 empire-card flat" style={{ padding: 20 }}>
              <div className="flex items-center gap-2 mb-3">
                <h3 className="text-sm font-bold text-[#1a1a1a]">{cust.name}</h3>
                {(cust.total_revenue || 0) > 10000 && (
                  <span className="status-pill" style={{ backgroundColor: '#fdf8eb', color: '#b8960c', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    <Crown size={10} /> VIP
                  </span>
                )}
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                <div><span className="section-label" style={{ fontSize: 10 }}>Email</span><span className="text-[#555] block">{cust.email || '\u2014'}</span></div>
                <div><span className="section-label" style={{ fontSize: 10 }}>Phone</span><span className="text-[#555] block">{cust.phone || '\u2014'}</span></div>
                <div><span className="section-label" style={{ fontSize: 10 }}>Revenue</span><span className="text-[#555] block">{fmt(cust.total_revenue || 0)}</span></div>
                <div><span className="section-label" style={{ fontSize: 10 }}>Quotes</span><span className="text-[#555] block">{cust.quote_count ?? 0}</span></div>
              </div>
              <div className="mt-3">
                <a
                  href={`?customer=${cust.id}`}
                  className="text-xs text-[#b8960c] hover:underline font-bold"
                >
                  View Full Profile
                </a>
              </div>
            </div>
          );
        })()}
      </div>
    </div>
  );
}
