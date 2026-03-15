'use client';
import React, { useState, useEffect } from 'react';
import { API } from '../../../lib/api';
import {
  DollarSign, TrendingUp, TrendingDown, FileText, Receipt, Loader2, BarChart3
} from 'lucide-react';
import KPICard from '../shared/KPICard';
import DataTable, { Column } from '../shared/DataTable';
import StatusBadge from '../shared/StatusBadge';
import EmptyState from '../shared/EmptyState';

export default function FinanceModule() {
  const [dashboard, setDashboard] = useState<any>(null);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([
      fetch(`${API}/finance/dashboard`).then(r => r.json()),
      fetch(`${API}/finance/invoices`).then(r => r.json()),
    ]).then(([dashRes, invRes]) => {
      if (dashRes.status === 'fulfilled') setDashboard(dashRes.value);
      if (invRes.status === 'fulfilled') {
        const raw = invRes.value;
        setInvoices(Array.isArray(raw) ? raw : raw.invoices || []);
      }
      setLoading(false);
    });
  }, []);

  // Also pull CraftForge-specific dashboard for revenue
  const [cfDashboard, setCfDashboard] = useState<any>(null);
  useEffect(() => {
    fetch(`${API}/craftforge/dashboard`)
      .then(r => r.json())
      .then(data => setCfDashboard(data))
      .catch(() => {});
  }, []);

  const revenue = cfDashboard?.revenue || dashboard?.revenue_mtd || 0;
  const pipeline = cfDashboard?.pipeline || 0;
  const expenses = dashboard?.expenses_mtd || 0;
  const profitMargin = revenue > 0 ? ((revenue - expenses) / revenue * 100) : 0;
  const outstanding = invoices.filter(i => i.status === 'sent' || i.status === 'overdue')
    .reduce((sum: number, i: any) => sum + (i.total || i.amount || 0), 0);

  const invoiceColumns: Column[] = [
    { key: 'invoice_number', label: '#', sortable: true, render: (row) => <span style={{ fontSize: 12, fontWeight: 700, color: '#b8960c', fontFamily: 'monospace' }}>{row.invoice_number || row.id?.slice(0, 8) || '--'}</span> },
    { key: 'customer_name', label: 'Customer', sortable: true, render: (row) => <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{row.customer_name || '--'}</span> },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status || 'draft'} /> },
    { key: 'total', label: 'Amount', sortable: true, render: (row) => <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>${Number(row.total || row.amount || 0).toFixed(2)}</span> },
    { key: 'due_date', label: 'Due', render: (row) => <span style={{ fontSize: 11, color: '#777' }} suppressHydrationWarning>{row.due_date ? new Date(row.due_date).toLocaleDateString() : '--'}</span> },
    { key: 'created_at', label: 'Created', render: (row) => <span style={{ fontSize: 11, color: '#999' }} suppressHydrationWarning>{row.created_at ? new Date(row.created_at).toLocaleDateString() : '--'}</span> },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={24} className="text-[#b8960c] animate-spin" />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
      <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0, marginBottom: 20 }} className="flex items-center gap-2">
        <DollarSign size={20} className="text-[#b8960c]" /> Finance
      </h2>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <KPICard
          icon={<TrendingUp size={20} />}
          label="Revenue"
          value={`$${Number(revenue).toLocaleString()}`}
          color="#22c55e"
        />
        <KPICard
          icon={<TrendingDown size={20} />}
          label="Expenses"
          value={`$${Number(expenses).toLocaleString()}`}
          color="#dc2626"
        />
        <KPICard
          icon={<BarChart3 size={20} />}
          label="Profit Margin"
          value={`${profitMargin.toFixed(1)}%`}
          color={profitMargin > 0 ? '#22c55e' : '#dc2626'}
        />
        <KPICard
          icon={<Receipt size={20} />}
          label="Outstanding"
          value={`$${Number(outstanding).toLocaleString()}`}
          color="#d97706"
        />
      </div>

      {/* Pipeline info from CraftForge dashboard */}
      {cfDashboard && (
        <div className="grid grid-cols-3 gap-3 mb-6">
          <div className="empire-card flat">
            <div className="kpi-label">Pipeline Value</div>
            <div className="kpi-value gold">${Number(pipeline).toLocaleString()}</div>
          </div>
          <div className="empire-card flat">
            <div className="kpi-label">Total Designs</div>
            <div className="kpi-value">{cfDashboard.total_designs || 0}</div>
          </div>
          <div className="empire-card flat">
            <div className="kpi-label">Inventory Value</div>
            <div className="kpi-value">${Number(cfDashboard.inventory?.total_value || 0).toLocaleString()}</div>
          </div>
        </div>
      )}

      {/* Invoices */}
      <div className="section-label mb-2">Invoices</div>
      {invoices.length === 0 ? (
        <EmptyState
          icon={<FileText size={32} />}
          title="No invoices yet"
          description="Invoices will appear here once created from quotes or manually."
        />
      ) : (
        <DataTable columns={invoiceColumns} data={invoices} />
      )}
    </div>
  );
}
