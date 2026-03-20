'use client';
import React, { useState, useEffect, useCallback } from 'react';
import { API } from '../../../lib/api';
import {
  DollarSign, TrendingUp, FileText, Receipt, CreditCard, Clock,
  Download, Send, CheckCircle, X, Loader2, Plus
} from 'lucide-react';
import KPICard from '../shared/KPICard';
import DataTable, { Column } from '../shared/DataTable';
import StatusBadge from '../shared/StatusBadge';
import EmptyState from '../shared/EmptyState';

// ── Types ──────────────────────────────────────────────────────────────
interface FinanceDashboard {
  revenue: { mtd: number; ytd: number };
  expenses: { mtd: number; ytd: number };
  outstanding: { total: number; count: number };
  accounts_receivable_aging: {
    '0_30': number;
    '31_60': number;
    '61_90': number;
    '90_plus': number;
  };
  recent_invoices: any[];
}

interface PaymentForm {
  amount: string;
  method: string;
  reference: string;
  notes: string;
  date: string;
}

const PAYMENT_METHODS = ['Cash', 'Check', 'Card', 'Zelle', 'Venmo', 'Wire'];

const todayISO = () => {
  const d = new Date();
  return d.toISOString().slice(0, 10);
};

// ── Component ──────────────────────────────────────────────────────────
export default function FinanceModule() {
  const [dashboard, setDashboard] = useState<FinanceDashboard | null>(null);
  const [designs, setDesigns] = useState<any[]>([]);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [payments, setPayments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Payment modal state
  const [paymentModal, setPaymentModal] = useState<{ open: boolean; invoice: any | null }>({ open: false, invoice: null });
  const [paymentForm, setPaymentForm] = useState<PaymentForm>({ amount: '', method: 'Cash', reference: '', notes: '', date: todayISO() });
  const [submitting, setSubmitting] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // ── Data fetching ──────────────────────────────────────────────────
  const fetchAll = useCallback(() => {
    setLoading(true);
    Promise.allSettled([
      fetch(`${API}/finance/dashboard`).then(r => r.json()),
      fetch(`${API}/craftforge/designs`).then(r => r.json()),
      fetch(`${API}/finance/invoices`).then(r => r.json()),
      fetch(`${API}/finance/payments?limit=10`).then(r => r.json()),
    ]).then(([dashRes, desRes, invRes, payRes]) => {
      if (dashRes.status === 'fulfilled') setDashboard(dashRes.value);
      if (desRes.status === 'fulfilled') {
        const raw = desRes.value;
        setDesigns(Array.isArray(raw) ? raw : raw.designs || []);
      }
      if (invRes.status === 'fulfilled') {
        const raw = invRes.value;
        setInvoices(Array.isArray(raw) ? raw : raw.invoices || []);
      }
      if (payRes.status === 'fulfilled') {
        const raw = payRes.value;
        setPayments(Array.isArray(raw) ? raw : raw.payments || []);
      }
      setLoading(false);
    });
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const refreshInvoices = useCallback(() => {
    fetch(`${API}/finance/invoices`).then(r => r.json()).then(raw => {
      setInvoices(Array.isArray(raw) ? raw : raw.invoices || []);
    }).catch(() => {});
    fetch(`${API}/finance/payments?limit=10`).then(r => r.json()).then(raw => {
      setPayments(Array.isArray(raw) ? raw : raw.payments || []);
    }).catch(() => {});
    fetch(`${API}/finance/dashboard`).then(r => r.json()).then(d => setDashboard(d)).catch(() => {});
  }, []);

  // ── Derived data ───────────────────────────────────────────────────
  const revenueMTD = dashboard?.revenue?.mtd ?? 0;
  const expensesMTD = dashboard?.expenses?.mtd ?? 0;
  const netProfitMTD = revenueMTD - expensesMTD;
  const outstandingCount = dashboard?.outstanding?.count ?? 0;
  const outstandingTotal = dashboard?.outstanding?.total ?? 0;
  const aging = dashboard?.accounts_receivable_aging ?? { '0_30': 0, '31_60': 0, '61_90': 0, '90_plus': 0 };

  const excludedStatuses = ['complete', 'completed', 'cancelled', 'invoiced'];
  const openQuotes = designs.filter(d => !excludedStatuses.includes((d.status || '').toLowerCase()));
  const openInvoices = invoices.filter(i => !['paid', 'cancelled'].includes((i.status || '').toLowerCase()));

  // ── Actions ────────────────────────────────────────────────────────
  const handleAcceptQuote = async (design: any) => {
    setActionLoading(`accept-${design.id}`);
    try {
      await fetch(`${API}/craftforge/designs/${design.id}/accept`, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
      fetchAll();
    } catch (e) { console.error('Accept failed:', e); }
    setActionLoading(null);
  };

  const handleCreateInvoice = async (design: any) => {
    setActionLoading(`invoice-${design.id}`);
    try {
      await fetch(`${API}/craftforge/designs/${design.id}/create-invoice`, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
      fetchAll();
    } catch (e) { console.error('Create invoice failed:', e); }
    setActionLoading(null);
  };

  const handleDownloadQuotePDF = async (design: any) => {
    setActionLoading(`pdf-${design.id}`);
    try {
      const res = await fetch(`${API}/craftforge/designs/${design.id}/pdf`, { method: 'POST' });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `quote-${design.id}.pdf`; a.click();
        URL.revokeObjectURL(url);
      }
    } catch (e) { console.error('PDF download failed:', e); }
    setActionLoading(null);
  };

  const handleSendInvoice = async (invoice: any) => {
    setActionLoading(`send-${invoice.id}`);
    try {
      await fetch(`${API}/finance/invoices/${invoice.id}/send`, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
      refreshInvoices();
    } catch (e) { console.error('Send invoice failed:', e); }
    setActionLoading(null);
  };

  const handleDownloadInvoicePDF = async (invoice: any) => {
    setActionLoading(`ipdf-${invoice.id}`);
    try {
      const res = await fetch(`${API}/finance/invoices/${invoice.id}/pdf`);
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `invoice-${invoice.invoice_number || invoice.id}.pdf`; a.click();
        URL.revokeObjectURL(url);
      }
    } catch (e) { console.error('Invoice PDF download failed:', e); }
    setActionLoading(null);
  };

  const openPaymentModal = (invoice: any) => {
    setPaymentForm({
      amount: String(Number(invoice.balance_due ?? (invoice.total || 0) - (invoice.paid || 0)).toFixed(2)),
      method: 'Cash',
      reference: '',
      notes: '',
      date: todayISO(),
    });
    setPaymentModal({ open: true, invoice });
  };

  const submitPayment = async () => {
    if (!paymentModal.invoice) return;
    setSubmitting(true);
    try {
      const body = {
        amount: parseFloat(paymentForm.amount),
        method: paymentForm.method.toLowerCase(),
        reference: paymentForm.reference || undefined,
        notes: paymentForm.notes || undefined,
        payment_date: paymentForm.date,
      };
      await fetch(`${API}/finance/invoices/${paymentModal.invoice.id}/payment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      setPaymentModal({ open: false, invoice: null });
      refreshInvoices();
    } catch (e) {
      console.error('Payment failed:', e);
    }
    setSubmitting(false);
  };

  // ── Action button helper ───────────────────────────────────────────
  const ActionBtn = ({ onClick, icon, label, loadingKey, color = '#b8960c' }: { onClick: () => void; icon: React.ReactNode; label: string; loadingKey: string; color?: string }) => (
    <button
      onClick={(e) => { e.stopPropagation(); onClick(); }}
      disabled={actionLoading === loadingKey}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 4, padding: '4px 10px',
        fontSize: 11, fontWeight: 600, color, background: `${color}10`,
        border: `1px solid ${color}30`, borderRadius: 6, cursor: 'pointer',
        opacity: actionLoading === loadingKey ? 0.5 : 1,
      }}
      title={label}
    >
      {actionLoading === loadingKey ? <Loader2 size={12} className="animate-spin" /> : icon}
      {label}
    </button>
  );

  // ── Table columns ──────────────────────────────────────────────────
  const quoteColumns: Column[] = [
    { key: 'id', label: '#', sortable: true, render: (row) => <span style={{ fontSize: 12, fontWeight: 700, color: '#b8960c', fontFamily: 'monospace' }}>{row.design_number || row.id?.slice(0, 8) || '--'}</span> },
    { key: 'customer_name', label: 'Customer', sortable: true, render: (row) => <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{row.customer_name || row.customer || '--'}</span> },
    { key: 'project_name', label: 'Project', sortable: true, render: (row) => <span style={{ fontSize: 13, color: '#444' }}>{row.project_name || row.name || row.title || '--'}</span> },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status || 'draft'} /> },
    { key: 'total', label: 'Total', sortable: true, render: (row) => <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>${Number(row.total || row.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span> },
    { key: 'created_at', label: 'Created', render: (row) => <span style={{ fontSize: 11, color: '#999' }} suppressHydrationWarning>{row.created_at ? new Date(row.created_at).toLocaleDateString() : '--'}</span> },
    {
      key: '_actions', label: 'Actions', render: (row) => (
        <div className="flex items-center gap-1.5 flex-wrap">
          <ActionBtn onClick={() => handleAcceptQuote(row)} icon={<CheckCircle size={12} />} label="Accept" loadingKey={`accept-${row.id}`} color="#22c55e" />
          <ActionBtn onClick={() => handleCreateInvoice(row)} icon={<Receipt size={12} />} label="Create Invoice" loadingKey={`invoice-${row.id}`} />
          <ActionBtn onClick={() => handleDownloadQuotePDF(row)} icon={<Download size={12} />} label="Download PDF" loadingKey={`pdf-${row.id}`} color="#2563eb" />
        </div>
      ),
    },
  ];

  const invoiceColumns: Column[] = [
    { key: 'invoice_number', label: 'Invoice #', sortable: true, render: (row) => <span style={{ fontSize: 12, fontWeight: 700, color: '#b8960c', fontFamily: 'monospace' }}>{row.invoice_number || row.id?.slice(0, 8) || '--'}</span> },
    { key: 'customer_name', label: 'Customer', sortable: true, render: (row) => <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{row.customer_name || '--'}</span> },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status || 'draft'} /> },
    { key: 'total', label: 'Total', sortable: true, render: (row) => <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>${Number(row.total || row.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span> },
    { key: 'paid', label: 'Paid', render: (row) => <span style={{ fontSize: 13, color: '#22c55e', fontWeight: 600 }}>${Number(row.amount_paid || row.paid || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span> },
    { key: 'balance_due', label: 'Balance Due', sortable: true, render: (row) => {
      const bal = row.balance_due ?? (Number(row.total || 0) - Number(row.amount_paid || row.paid || 0));
      return <span style={{ fontSize: 13, fontWeight: 700, color: bal > 0 ? '#dc2626' : '#22c55e' }}>${Number(bal).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>;
    }},
    { key: 'due_date', label: 'Due Date', sortable: true, render: (row) => {
      const overdue = row.due_date && new Date(row.due_date) < new Date() && (row.status || '').toLowerCase() !== 'paid';
      return <span style={{ fontSize: 11, color: overdue ? '#dc2626' : '#777', fontWeight: overdue ? 700 : 400 }} suppressHydrationWarning>{row.due_date ? new Date(row.due_date).toLocaleDateString() : '--'}</span>;
    }},
    {
      key: '_actions', label: 'Actions', render: (row) => (
        <div className="flex items-center gap-1.5 flex-wrap">
          <ActionBtn onClick={() => openPaymentModal(row)} icon={<CreditCard size={12} />} label="Record Payment" loadingKey={`pay-${row.id}`} color="#22c55e" />
          <ActionBtn onClick={() => handleSendInvoice(row)} icon={<Send size={12} />} label="Send" loadingKey={`send-${row.id}`} />
          <ActionBtn onClick={() => handleDownloadInvoicePDF(row)} icon={<Download size={12} />} label="PDF" loadingKey={`ipdf-${row.id}`} color="#2563eb" />
        </div>
      ),
    },
  ];

  const paymentColumns: Column[] = [
    { key: 'payment_date', label: 'Date', sortable: true, render: (row) => <span style={{ fontSize: 12, color: '#555' }} suppressHydrationWarning>{row.payment_date ? new Date(row.payment_date).toLocaleDateString() : row.created_at ? new Date(row.created_at).toLocaleDateString() : '--'}</span> },
    { key: 'invoice_number', label: 'Invoice #', render: (row) => <span style={{ fontSize: 12, fontWeight: 700, color: '#b8960c', fontFamily: 'monospace' }}>{row.invoice_number || '--'}</span> },
    { key: 'amount', label: 'Amount', sortable: true, render: (row) => <span style={{ fontSize: 13, fontWeight: 700, color: '#22c55e' }}>${Number(row.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span> },
    { key: 'method', label: 'Method', render: (row) => <span style={{ fontSize: 12, color: '#555' }}>{row.method || '--'}</span> },
    { key: 'reference', label: 'Reference', render: (row) => <span style={{ fontSize: 11, color: '#999', fontFamily: 'monospace' }}>{row.reference || '--'}</span> },
  ];

  // ── AR Aging bar ───────────────────────────────────────────────────
  const agingBuckets = [
    { label: '0-30 days', value: aging['0_30'] || 0, color: '#22c55e' },
    { label: '31-60 days', value: aging['31_60'] || 0, color: '#d97706' },
    { label: '61-90 days', value: aging['61_90'] || 0, color: '#dc2626' },
    { label: '90+ days', value: aging['90_plus'] || 0, color: '#7f1d1d' },
  ];
  const agingMax = Math.max(...agingBuckets.map(b => b.value), 1);

  // ── Loading state ──────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={24} className="text-[#b8960c] animate-spin" />
      </div>
    );
  }

  // ── Render ─────────────────────────────────────────────────────────
  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
      <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0, marginBottom: 20 }} className="flex items-center gap-2">
        <DollarSign size={20} className="text-[#b8960c]" /> WoodCraft Finance
      </h2>

      {/* ── KPI Cards ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        <KPICard
          icon={<TrendingUp size={20} />}
          label="Revenue This Month"
          value={`$${Number(revenueMTD).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          color="#22c55e"
        />
        <KPICard
          icon={<Receipt size={20} />}
          label="Outstanding Invoices"
          value={`${outstandingCount} / $${Number(outstandingTotal).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          color="#d97706"
        />
        <KPICard
          icon={<FileText size={20} />}
          label="Open Quotes"
          value={`${openQuotes.length}`}
          color="#2563eb"
        />
        <KPICard
          icon={<DollarSign size={20} />}
          label="Net Profit MTD"
          value={`$${Number(netProfitMTD).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          color={netProfitMTD >= 0 ? '#22c55e' : '#dc2626'}
        />
      </div>

      {/* ── AR Aging ──────────────────────────────────────────────── */}
      <div className="section-label mb-2">Accounts Receivable Aging</div>
      <div className="empire-card flat" style={{ padding: '20px 24px', marginBottom: 24 }}>
        {agingBuckets.map((bucket) => (
          <div key={bucket.label} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#555', width: 90, flexShrink: 0, textAlign: 'right' }}>{bucket.label}</span>
            <div style={{ flex: 1, height: 22, background: '#f0ede8', borderRadius: 6, overflow: 'hidden', position: 'relative' }}>
              <div style={{
                width: `${Math.max((bucket.value / agingMax) * 100, bucket.value > 0 ? 3 : 0)}%`,
                height: '100%',
                background: bucket.color,
                borderRadius: 6,
                transition: 'width 0.5s ease',
              }} />
            </div>
            <span style={{ fontSize: 13, fontWeight: 700, color: bucket.value > 0 ? bucket.color : '#999', width: 100, textAlign: 'right' }}>
              ${Number(bucket.value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
        ))}
      </div>

      {/* ── Open Quotes ───────────────────────────────────────────── */}
      <div className="section-label mb-2">Open Quotes</div>
      <div style={{ marginBottom: 24 }}>
        {openQuotes.length === 0 ? (
          <EmptyState
            icon={<FileText size={32} />}
            title="No open quotes"
            description="All quotes have been completed, invoiced, or cancelled."
          />
        ) : (
          <DataTable
            columns={quoteColumns}
            data={openQuotes}
            onRowClick={(row) => console.log('Quote clicked:', row)}
          />
        )}
      </div>

      {/* ── Open Invoices ─────────────────────────────────────────── */}
      <div className="section-label mb-2">Open Invoices</div>
      <div style={{ marginBottom: 24 }}>
        {openInvoices.length === 0 ? (
          <EmptyState
            icon={<Receipt size={32} />}
            title="No open invoices"
            description="All invoices have been paid or cancelled."
          />
        ) : (
          <DataTable
            columns={invoiceColumns}
            data={openInvoices}
            onRowClick={(row) => console.log('Invoice clicked:', row)}
          />
        )}
      </div>

      {/* ── Recent Payments ───────────────────────────────────────── */}
      <div className="section-label mb-2">Recent Payments</div>
      <div style={{ marginBottom: 24 }}>
        {payments.length === 0 ? (
          <EmptyState
            icon={<CreditCard size={32} />}
            title="No recent payments"
            description="Payments will appear here once recorded."
          />
        ) : (
          <DataTable columns={paymentColumns} data={payments} />
        )}
      </div>

      {/* ── Record Payment Modal ──────────────────────────────────── */}
      {paymentModal.open && paymentModal.invoice && (
        <div
          style={{
            position: 'fixed', inset: 0, zIndex: 9999,
            background: 'rgba(0,0,0,0.45)', display: 'flex',
            alignItems: 'center', justifyContent: 'center',
          }}
          onClick={() => setPaymentModal({ open: false, invoice: null })}
        >
          <div
            style={{
              background: '#fff', borderRadius: 14, padding: '28px 32px',
              maxWidth: 480, width: '90%', boxShadow: '0 20px 60px rgba(0,0,0,0.25)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-5">
              <h3 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }} className="flex items-center gap-2">
                <CreditCard size={18} className="text-[#b8960c]" /> Record Payment
              </h3>
              <button
                onClick={() => setPaymentModal({ open: false, invoice: null })}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}
              >
                <X size={18} color="#999" />
              </button>
            </div>

            <div style={{ fontSize: 13, color: '#555', marginBottom: 20, padding: '10px 14px', background: '#f8f7f4', borderRadius: 8 }}>
              Invoice <strong style={{ color: '#b8960c' }}>{paymentModal.invoice.invoice_number || paymentModal.invoice.id?.slice(0, 8)}</strong>
              {' '}&mdash;{' '}
              <strong>{paymentModal.invoice.customer_name || 'Customer'}</strong>
              <br />
              <span style={{ fontSize: 12, color: '#777' }}>
                Total: ${Number(paymentModal.invoice.total || 0).toFixed(2)} | Paid: ${Number(paymentModal.invoice.paid || 0).toFixed(2)} | Balance: ${Number(paymentModal.invoice.balance_due ?? (Number(paymentModal.invoice.total || 0) - Number(paymentModal.invoice.paid || 0))).toFixed(2)}
              </span>
            </div>

            {/* Amount */}
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#555', marginBottom: 4 }}>Amount ($) *</label>
            <input
              type="number"
              step="0.01"
              value={paymentForm.amount}
              onChange={(e) => setPaymentForm(f => ({ ...f, amount: e.target.value }))}
              style={{
                width: '100%', padding: '10px 14px', fontSize: 14, fontWeight: 600,
                border: '1.5px solid #ddd', borderRadius: 8, marginBottom: 14,
                outline: 'none', boxSizing: 'border-box',
              }}
              placeholder="0.00"
            />

            {/* Method */}
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#555', marginBottom: 4 }}>Payment Method *</label>
            <select
              value={paymentForm.method}
              onChange={(e) => setPaymentForm(f => ({ ...f, method: e.target.value }))}
              style={{
                width: '100%', padding: '10px 14px', fontSize: 14,
                border: '1.5px solid #ddd', borderRadius: 8, marginBottom: 14,
                outline: 'none', background: '#fff', boxSizing: 'border-box',
              }}
            >
              {PAYMENT_METHODS.map(m => <option key={m} value={m}>{m}</option>)}
            </select>

            {/* Reference */}
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#555', marginBottom: 4 }}>Reference # (optional)</label>
            <input
              type="text"
              value={paymentForm.reference}
              onChange={(e) => setPaymentForm(f => ({ ...f, reference: e.target.value }))}
              style={{
                width: '100%', padding: '10px 14px', fontSize: 14,
                border: '1.5px solid #ddd', borderRadius: 8, marginBottom: 14,
                outline: 'none', boxSizing: 'border-box',
              }}
              placeholder="Check #, transaction ID, etc."
            />

            {/* Notes */}
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#555', marginBottom: 4 }}>Notes (optional)</label>
            <textarea
              value={paymentForm.notes}
              onChange={(e) => setPaymentForm(f => ({ ...f, notes: e.target.value }))}
              rows={2}
              style={{
                width: '100%', padding: '10px 14px', fontSize: 14,
                border: '1.5px solid #ddd', borderRadius: 8, marginBottom: 14,
                outline: 'none', resize: 'vertical', boxSizing: 'border-box',
              }}
              placeholder="Optional notes..."
            />

            {/* Date */}
            <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#555', marginBottom: 4 }}>Payment Date *</label>
            <input
              type="date"
              value={paymentForm.date}
              onChange={(e) => setPaymentForm(f => ({ ...f, date: e.target.value }))}
              style={{
                width: '100%', padding: '10px 14px', fontSize: 14,
                border: '1.5px solid #ddd', borderRadius: 8, marginBottom: 20,
                outline: 'none', boxSizing: 'border-box',
              }}
            />

            {/* Submit */}
            <button
              onClick={submitPayment}
              disabled={submitting || !paymentForm.amount || parseFloat(paymentForm.amount) <= 0}
              style={{
                width: '100%', padding: '12px 20px', fontSize: 14, fontWeight: 700,
                color: '#fff', background: '#b8960c', border: 'none', borderRadius: 10,
                cursor: submitting ? 'not-allowed' : 'pointer',
                opacity: submitting || !paymentForm.amount || parseFloat(paymentForm.amount) <= 0 ? 0.5 : 1,
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              }}
            >
              {submitting ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle size={16} />}
              {submitting ? 'Recording...' : 'Record Payment'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
