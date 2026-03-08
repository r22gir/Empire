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
    { key: 'amount', label: 'Amount', sortable: true, render: (r) => fmt(r.amount || r.total || 0) },
    { key: 'date', label: 'Date', sortable: true, render: (r) => (
      <span suppressHydrationWarning>{(r.date || r.created_at) ? new Date(r.date || r.created_at).toLocaleDateString() : '—'}</span>
    )},
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status || 'draft'} /> },
  ];

  const invoiceColumns: Column[] = [
    { key: 'invoice_number', label: 'Invoice #', sortable: true },
    { key: 'amount', label: 'Amount', sortable: true, render: (r) => fmt(r.amount || 0) },
    { key: 'balance', label: 'Balance', sortable: true, render: (r) => fmt(r.balance ?? r.amount ?? 0) },
    { key: 'due_date', label: 'Due Date', sortable: true, render: (r) => (
      <span suppressHydrationWarning>{r.due_date ? new Date(r.due_date).toLocaleDateString() : '—'}</span>
    )},
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status || 'draft'} /> },
  ];

  const paymentColumns: Column[] = [
    { key: 'payment_date', label: 'Date', sortable: true, render: (r) => (
      <span suppressHydrationWarning>{(r.payment_date || r.date) ? new Date(r.payment_date || r.date).toLocaleDateString() : '—'}</span>
    )},
    { key: 'amount', label: 'Amount', sortable: true, render: (r) => (
      <span className="text-green-600 font-medium">{fmt(r.amount || 0)}</span>
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
        <div className="max-w-6xl mx-auto px-8 py-6">
          <div className="animate-pulse space-y-4">
            <div className="h-6 bg-gray-200 rounded w-48" />
            <div className="h-4 bg-gray-200 rounded w-64" />
            <div className="grid grid-cols-4 gap-4">
              {[1, 2, 3, 4].map(i => <div key={i} className="h-24 bg-gray-200 rounded-lg" />)}
            </div>
            <div className="h-64 bg-gray-200 rounded-lg" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !customer) {
    return (
      <div className="bg-[#faf9f7] min-h-screen">
        <div className="max-w-6xl mx-auto px-8 py-6">
          {onBack && (
            <button onClick={onBack} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
              <ArrowLeft size={16} /> Back to Customers
            </button>
          )}
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-sm text-red-700">
            <AlertCircle size={16} /> {error || 'Customer not found'}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#faf9f7] min-h-screen">
      <div className="max-w-6xl mx-auto px-8 py-6">
        {/* Back + Header */}
        {onBack && (
          <button onClick={onBack} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4">
            <ArrowLeft size={16} /> Back to Customers
          </button>
        )}

        <div className="flex items-start gap-4 mb-6">
          <div className="w-12 h-12 rounded-full bg-[#b8960c]/10 flex items-center justify-center shrink-0">
            <User size={24} className="text-[#b8960c]" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-800">{customer.name}</h1>
            <div className="flex flex-wrap gap-4 mt-1 text-sm text-gray-500">
              {customer.email && <span>{customer.email}</span>}
              {customer.phone && <span>{customer.phone}</span>}
              {customer.address && <span>{customer.address}</span>}
            </div>
          </div>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <KPICard
            icon={<DollarSign size={20} />}
            label="Total Revenue"
            value={fmt(customer.total_revenue || 0)}
            color="#16a34a"
          />
          <KPICard
            icon={<FileText size={20} />}
            label="Quotes"
            value={String(customer.quote_count ?? 0)}
            color="#2563eb"
          />
          <KPICard
            icon={<FileText size={20} />}
            label="Invoices"
            value={String(customer.invoice_count ?? 0)}
            color="#b8960c"
          />
          <KPICard
            icon={<MessageSquare size={20} />}
            label="Last Activity"
            value={customer.last_activity ? new Date(customer.last_activity).toLocaleDateString() : 'N/A'}
            color="#6b7280"
          />
        </div>

        {/* Tabs */}
        <div className="border-b border-[#ece8e1] mb-4">
          <div className="flex gap-1">
            {TABS.map(t => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
                  tab === t.key
                    ? 'border-[#b8960c] text-[#b8960c]'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {t.icon} {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        {tab === 'notes' ? (
          <div className="bg-white border border-[#ece8e1] rounded-lg p-4">
            <p className="text-sm text-gray-600 whitespace-pre-wrap">{customer.notes || 'No notes for this customer.'}</p>
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
