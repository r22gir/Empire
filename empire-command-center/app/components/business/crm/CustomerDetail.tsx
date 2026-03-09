'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { ArrowLeft, User, DollarSign, FileText, CreditCard, MessageSquare, AlertCircle } from 'lucide-react';
import { API } from '../../../lib/api';
import DataTable, { Column } from '../shared/DataTable';
import KPICard from '../shared/KPICard';
import StatusBadge from '../shared/StatusBadge';
import EmptyState from '../shared/EmptyState';

interface CustomerDetailProps {
  customerId: string;
  onBack?: () => void;
}

interface CustomerInfo {
  id: string;
  name: string;
  email: string;
  phone: string;
  address: string;
  total_revenue: number;
  quote_count: number;
  invoice_count: number;
  last_activity: string;
  notes: string;
}

function fmt(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(n);
}

type Tab = 'quotes' | 'invoices' | 'payments' | 'notes';

export default function CustomerDetail({ customerId, onBack }: CustomerDetailProps) {
  const [customer, setCustomer] = useState<CustomerInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('quotes');
  const [tabData, setTabData] = useState<any[]>([]);
  const [tabLoading, setTabLoading] = useState(false);

  const fetchCustomer = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/crm/customers/${customerId}`);
      if (!res.ok) throw new Error(`Failed to load customer (${res.status})`);
      setCustomer(await res.json());
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  const fetchTabData = useCallback(async (t: Tab) => {
    if (t === 'notes') {
      setTabData([]);
      return;
    }
    setTabLoading(true);
    try {
      const endpoint = t === 'payments' ? 'invoices' : t;
      const res = await fetch(`${API}/crm/customers/${customerId}/${endpoint}`);
      if (!res.ok) throw new Error(`Failed to load ${t}`);
      const data = await res.json();
      setTabData(Array.isArray(data) ? data : data.items || []);
    } catch {
      setTabData([]);
    } finally {
      setTabLoading(false);
    }
  }, [customerId]);

  useEffect(() => { fetchCustomer(); }, [fetchCustomer]);
  useEffect(() => { fetchTabData(tab); }, [tab, fetchTabData]);

  const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: 'quotes', label: 'Quotes', icon: <FileText size={14} /> },
    { key: 'invoices', label: 'Invoices', icon: <FileText size={14} /> },
    { key: 'payments', label: 'Payments', icon: <CreditCard size={14} /> },
    { key: 'notes', label: 'Notes', icon: <MessageSquare size={14} /> },
  ];

  const quoteColumns: Column[] = [
    { key: 'quote_number', label: 'Quote #', sortable: true },
    { key: 'description', label: 'Description' },
    { key: 'amount', label: 'Amount', sortable: true, render: (r) => <span className="font-bold text-[#1a1a1a]">{fmt(r.amount || r.total || 0)}</span> },
    { key: 'date', label: 'Date', sortable: true, render: (r) => (
      <span className="text-xs text-[#999]" suppressHydrationWarning>{(r.date || r.created_at) ? new Date(r.date || r.created_at).toLocaleDateString() : '\u2014'}</span>
    )},
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status || 'draft'} /> },
  ];

  const invoiceColumns: Column[] = [
    { key: 'invoice_number', label: 'Invoice #', sortable: true },
    { key: 'amount', label: 'Amount', sortable: true, render: (r) => <span className="font-bold">{fmt(r.amount || 0)}</span> },
    { key: 'balance', label: 'Balance', sortable: true, render: (r) => <span className="font-bold text-[#b8960c]">{fmt(r.balance ?? r.amount ?? 0)}</span> },
    { key: 'due_date', label: 'Due Date', sortable: true, render: (r) => (
      <span className="text-xs text-[#999]" suppressHydrationWarning>{r.due_date ? new Date(r.due_date).toLocaleDateString() : '\u2014'}</span>
    )},
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status || 'draft'} /> },
  ];

  const paymentColumns: Column[] = [
    { key: 'payment_date', label: 'Date', sortable: true, render: (r) => (
      <span className="text-xs text-[#999]" suppressHydrationWarning>{(r.payment_date || r.date) ? new Date(r.payment_date || r.date).toLocaleDateString() : '\u2014'}</span>
    )},
    { key: 'amount', label: 'Amount', sortable: true, render: (r) => (
      <span className="text-[#22c55e] font-bold">{fmt(r.amount || 0)}</span>
    )},
    { key: 'method', label: 'Method' },
    { key: 'reference', label: 'Reference' },
  ];

  const columnsMap: Record<Tab, Column[]> = {
    quotes: quoteColumns,
    invoices: invoiceColumns,
    payments: paymentColumns,
    notes: [],
  };

  if (loading) {
    return (
      <div className="bg-[#faf9f7] min-h-screen">
        <div className="max-w-6xl mx-auto" style={{ padding: '24px 36px' }}>
          <div className="animate-pulse space-y-4">
            <div className="h-6 bg-[#ece8e0] rounded-xl w-48" />
            <div className="h-4 bg-[#ece8e0] rounded-xl w-64" />
            <div className="grid grid-cols-4 gap-4">
              {[1, 2, 3, 4].map(i => <div key={i} className="h-24 bg-[#ece8e0] rounded-[14px]" />)}
            </div>
            <div className="h-64 bg-[#ece8e0] rounded-[14px]" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !customer) {
    return (
      <div className="bg-[#faf9f7] min-h-screen">
        <div className="max-w-6xl mx-auto" style={{ padding: '24px 36px' }}>
          {onBack && (
            <button onClick={onBack} className="flex items-center gap-1 text-sm text-[#999] hover:text-[#555] mb-4 cursor-pointer transition-colors">
              <ArrowLeft size={16} /> Back to Customers
            </button>
          )}
          <div className="empire-card flat" style={{ padding: 16, borderColor: '#fca5a5', background: '#fef2f2' }}>
            <div className="flex items-center gap-2 text-sm text-red-700">
              <AlertCircle size={16} /> {error || 'Customer not found'}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#faf9f7] min-h-screen">
      <div className="max-w-6xl mx-auto" style={{ padding: '24px 36px' }}>
        {/* Back + Header */}
        {onBack && (
          <button onClick={onBack} className="flex items-center gap-1 text-sm text-[#999] hover:text-[#555] mb-4 cursor-pointer transition-colors">
            <ArrowLeft size={16} /> Back to Customers
          </button>
        )}

        <div className="flex items-start gap-4 mb-6">
          <div className="w-12 h-12 rounded-full bg-[#fdf8eb] flex items-center justify-center shrink-0">
            <User size={24} className="text-[#b8960c]" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[#1a1a1a]">{customer.name}</h1>
            <div className="flex flex-wrap gap-4 mt-1 text-sm text-[#999]">
              {customer.email && <span>{customer.email}</span>}
              {customer.phone && <span>{customer.phone}</span>}
              {customer.address && <span>{customer.address}</span>}
            </div>
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <KPICard icon={<DollarSign size={20} />} label="Total Revenue" value={fmt(customer.total_revenue || 0)} color="#22c55e" />
          <KPICard icon={<FileText size={20} />} label="Quotes" value={String(customer.quote_count ?? 0)} color="#2563eb" />
          <KPICard icon={<FileText size={20} />} label="Invoices" value={String(customer.invoice_count ?? 0)} color="#b8960c" />
          <KPICard icon={<MessageSquare size={20} />} label="Last Activity" value={customer.last_activity ? new Date(customer.last_activity).toLocaleDateString() : 'N/A'} color="#6b7280" />
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 mb-5 empire-card flat" style={{ padding: 4, width: 'fit-content' }}>
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`filter-tab ${tab === t.key ? 'active' : ''}`}
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        {tab === 'notes' ? (
          <div className="empire-card flat" style={{ padding: 20 }}>
            <p className="text-sm text-[#555] whitespace-pre-wrap">{customer.notes || 'No notes for this customer.'}</p>
          </div>
        ) : (
          tabData.length === 0 && !tabLoading ? (
            <EmptyState
              icon={tab === 'quotes' ? <FileText size={40} /> : tab === 'invoices' ? <FileText size={40} /> : <CreditCard size={40} />}
              title={`No ${tab} found`}
              description={`This customer has no ${tab} on record.`}
            />
          ) : (
            <DataTable
              columns={columnsMap[tab]}
              data={tabData}
              loading={tabLoading}
              emptyMessage={`No ${tab} found.`}
            />
          )
        )}
      </div>
    </div>
  );
}
