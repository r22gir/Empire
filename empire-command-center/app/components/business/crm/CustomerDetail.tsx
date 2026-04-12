'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  ArrowLeft, User, DollarSign, FileText, CreditCard, MessageSquare,
  AlertCircle, Pencil, Save, X, Phone, Mail, MapPin, Building2,
  Tag, Crown, ClipboardList, Plus, Loader2, Printer, Send
} from 'lucide-react';
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
  company: string;
  type: string;
  tags: string[];
  total_revenue: number;
  lifetime_quotes: number;
  quote_count: number;
  invoice_count: number;
  last_activity: string;
  notes: string;
  source: string;
  business: string;
  created_at: string;
  updated_at: string;
  quotes: any[];
  invoices: any[];
  payments: any[];
  finance_ledger?: CustomerFinanceLedger;
}

interface CustomerFinanceLedger {
  business: string;
  invoices: any[];
  open_invoices?: any[];
  overdue_invoices?: any[];
  payments: any[];
  transactions: any[];
  collections?: any[];
  aging: Record<string, number>;
  summary: {
    invoice_count: number;
    payment_count: number;
    open_invoice_count: number;
    overdue_invoice_count: number;
    total_invoiced: number;
    total_paid: number;
    current_balance: number;
    overdue_balance: number;
    aging_total: number;
  };
}

function fmt(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(n);
}

function cleanName(raw: string): string {
  if (!raw) return '';
  return raw.replace(/^\\?"?|"?\\?$/g, '').replace(/^"|"$/g, '').trim();
}

function escapeHtml(raw: unknown): string {
  return String(raw ?? '').replace(/[&<>"']/g, char => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char] || char
  ));
}

function initials(name: string): string {
  const clean = cleanName(name);
  const parts = clean.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0][0].toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

const TYPE_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  designer:    { bg: '#fdf8eb', text: '#b8960c', label: 'Designer' },
  residential: { bg: '#eff6ff', text: '#2563eb', label: 'Residential' },
  commercial:  { bg: '#f0fdf4', text: '#16a34a', label: 'Commercial' },
  contractor:  { bg: '#fffbeb', text: '#d97706', label: 'Contractor' },
};

type Tab = 'overview' | 'quotes' | 'invoices' | 'payments' | 'notes';

export default function CustomerDetail({ customerId, onBack }: CustomerDetailProps) {
  const [customer, setCustomer] = useState<CustomerInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('overview');
  const [tabData, setTabData] = useState<any[]>([]);
  const [tabLoading, setTabLoading] = useState(false);
  const [financeLedger, setFinanceLedger] = useState<CustomerFinanceLedger | null>(null);
  const [collectionBusy, setCollectionBusy] = useState(false);
  const [collectionMessage, setCollectionMessage] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({ name: '', email: '', phone: '', address: '', company: '', notes: '', type: '' });
  const [saving, setSaving] = useState(false);

  const fetchCustomer = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/crm/customers/${customerId}`);
      if (!res.ok) throw new Error(`Failed to load customer (${res.status})`);
      const data = await res.json();
      const c = data.customer || data;
      // Parse tags if string
      if (typeof c.tags === 'string') {
        try { c.tags = JSON.parse(c.tags); } catch { c.tags = []; }
      }
      const businessParam = c.business && c.business !== 'empire' ? `?business=${encodeURIComponent(c.business)}` : '';
      const ledgerRes = await fetch(`${API}/finance/customers/${customerId}/ledger${businessParam}`);
      if (ledgerRes.ok) {
        const ledger = await ledgerRes.json();
        setFinanceLedger(ledger);
        c.finance_ledger = ledger;
        c.invoices = ledger.invoices || c.invoices || [];
        c.payments = ledger.payments || c.payments || [];
        c.total_revenue = ledger.summary?.total_paid ?? c.total_revenue;
      } else {
        setFinanceLedger(null);
      }
      setCustomer(c);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  const fetchTabData = useCallback(async (t: Tab) => {
    if (t === 'notes' || t === 'overview') {
      setTabData([]);
      return;
    }
    setTabLoading(true);
    try {
      if (t === 'payments' || t === 'invoices') {
        const res = await fetch(`${API}/finance/customers/${customerId}/ledger`);
        if (!res.ok) throw new Error(`Failed to load ${t}`);
        const data = await res.json();
        setFinanceLedger(data);
        setTabData(t === 'payments' ? data.payments || [] : data.invoices || []);
        return;
      }
      const res = await fetch(`${API}/crm/customers/${customerId}/${t}`);
      if (!res.ok) throw new Error(`Failed to load ${t}`);
      const data = await res.json();
      setTabData(Array.isArray(data) ? data : data.quotes || data.invoices || data.payments || data.items || []);
    } catch {
      setTabData([]);
    } finally {
      setTabLoading(false);
    }
  }, [customerId]);

  useEffect(() => { fetchCustomer(); }, [fetchCustomer]);
  useEffect(() => { fetchTabData(tab); }, [tab, fetchTabData]);

  const startEdit = () => {
    if (!customer) return;
    setEditForm({
      name: cleanName(customer.name),
      email: customer.email || '',
      phone: customer.phone || '',
      address: customer.address || '',
      company: cleanName(customer.company || ''),
      notes: customer.notes || '',
      type: customer.type || 'residential',
    });
    setEditing(true);
  };

  const saveEdit = async () => {
    if (!customer) return;
    setSaving(true);
    try {
      const res = await fetch(`${API}/crm/customers/${customerId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editForm),
      });
      if (res.ok) {
        const updated = await res.json();
        const u = updated.customer || updated;
        setCustomer({ ...customer, ...editForm, ...u });
        setEditing(false);
      }
    } catch { /* ignore */ }
    setSaving(false);
  };

  const statementUrl = () => {
    const business = financeLedger?.business || customer?.business || '';
    const suffix = business && business !== 'empire' ? `?business=${encodeURIComponent(business)}` : '';
    return `${API}/finance/customers/${customerId}/statement${suffix}`;
  };

  const handleExportStatement = () => {
    window.open(statementUrl(), '_blank');
  };

  const handlePrintStatement = () => {
    if (!customer) return;
    const ledger = financeLedger || customer.finance_ledger;
    if (!ledger) return;
    const popup = window.open('', '_blank');
    if (!popup) return;
    const rows = (ledger.transactions || []).map((txn: any) => `
      <tr>
        <td>${txn.date ? new Date(txn.date).toLocaleDateString() : ''}</td>
        <td>${txn.type === 'payment' ? 'Payment' : 'Invoice'} ${escapeHtml(txn.invoice_number)}</td>
        <td>${escapeHtml(txn.reference || txn.status || '')}</td>
        <td style="text-align:right">${txn.type === 'payment' ? '-' : ''}${fmt(txn.amount || 0)}</td>
        <td style="text-align:right">${fmt(txn.running_balance || 0)}</td>
      </tr>
    `).join('');
    const safeName = escapeHtml(cleanName(customer.name));
    const safeEmail = escapeHtml(customer.email || '');
    const safeBusiness = escapeHtml(ledger.business || 'all');
    popup.document.write(`
      <html><head><title>Customer Statement - ${safeName}</title>
      <style>
        body{font-family:Arial,sans-serif;padding:32px;color:#1a1a1a}
        h1{font-size:22px;margin:0 0 6px} h2{font-size:14px;margin:24px 0 8px}
        table{width:100%;border-collapse:collapse;margin-top:12px}
        th,td{border-bottom:1px solid #ddd;padding:8px;font-size:12px;text-align:left}
        th{background:#f5f3ef}
        .summary{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0}
        .box{border:1px solid #ddd;padding:12px;border-radius:8px}.label{font-size:10px;color:#777;text-transform:uppercase}.value{font-size:16px;font-weight:700}
      </style></head><body>
        <h1>Customer Statement</h1>
        <div>${safeName}${safeEmail ? ` - ${safeEmail}` : ''}</div>
        <div>Business: ${safeBusiness} | As of ${new Date().toLocaleDateString()}</div>
        <div class="summary">
          <div class="box"><div class="label">Invoiced</div><div class="value">${fmt(ledger.summary.total_invoiced || 0)}</div></div>
          <div class="box"><div class="label">Paid</div><div class="value">${fmt(ledger.summary.total_paid || 0)}</div></div>
          <div class="box"><div class="label">Balance</div><div class="value">${fmt(ledger.summary.current_balance || 0)}</div></div>
          <div class="box"><div class="label">Overdue</div><div class="value">${fmt(ledger.summary.overdue_balance || 0)}</div></div>
        </div>
        <h2>Statement Activity</h2>
        <table><thead><tr><th>Date</th><th>Type</th><th>Status/Reference</th><th>Amount</th><th>Balance</th></tr></thead><tbody>${rows}</tbody></table>
      </body></html>
    `);
    popup.document.close();
    popup.print();
  };

  const handleLogReminder = async () => {
    if (!customer) return;
    setCollectionBusy(true);
    setCollectionMessage(null);
    try {
      const res = await fetch(`${API}/finance/customers/${customerId}/collections/reminder`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          business: financeLedger?.business || customer.business,
          action: 'reminder_logged',
          notes: 'Reminder logged from customer finance statement.',
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Failed to log reminder (${res.status})`);
      setFinanceLedger(data.statement);
      setCustomer({ ...customer, finance_ledger: data.statement, invoices: data.statement.invoices || [], payments: data.statement.payments || [] });
      setCollectionMessage('Reminder logged. No email was sent.');
    } catch (err: any) {
      setCollectionMessage(err.message || 'Failed to log reminder');
    } finally {
      setCollectionBusy(false);
    }
  };

  const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: 'overview', label: 'Overview', icon: <User size={14} /> },
    { key: 'quotes', label: 'Quotes', icon: <ClipboardList size={14} /> },
    { key: 'invoices', label: 'Invoices', icon: <FileText size={14} /> },
    { key: 'payments', label: 'Payments', icon: <CreditCard size={14} /> },
    { key: 'notes', label: 'Notes', icon: <MessageSquare size={14} /> },
  ];

  const quoteColumns: Column[] = [
    { key: 'quote_number', label: 'Quote #', sortable: true },
    { key: 'customer_name', label: 'Description', render: (r) => <span className="text-sm text-[#555]">{r.customer_name || '—'}</span> },
    { key: 'total', label: 'Amount', sortable: true, render: (r) => <span className="font-bold text-[#b8960c]">{fmt(r.total || r.amount || 0)}</span> },
    { key: 'rooms', label: 'Rooms', render: (r) => <span className="text-xs text-[#999]">{r.rooms || 0}</span> },
    { key: 'created_at', label: 'Date', sortable: true, render: (r) => (
      <span className="text-xs text-[#999]" suppressHydrationWarning>{(r.created_at) ? new Date(r.created_at).toLocaleDateString() : '—'}</span>
    )},
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status || 'draft'} /> },
  ];

  const invoiceColumns: Column[] = [
    { key: 'invoice_number', label: 'Invoice #', sortable: true },
    { key: 'invoice_stage', label: 'Stage', render: (r) => <span className="text-xs text-[#999]">{r.invoice_stage || 'manual'}</span> },
    { key: 'amount', label: 'Amount', sortable: true, render: (r) => <span className="font-bold">{fmt(r.total ?? r.amount ?? 0)}</span> },
    { key: 'balance', label: 'Balance', sortable: true, render: (r) => <span className="font-bold text-[#b8960c]">{fmt(r.balance_due ?? r.balance ?? r.total ?? 0)}</span> },
    { key: 'due_date', label: 'Due Date', sortable: true, render: (r) => (
      <span className="text-xs text-[#999]" suppressHydrationWarning>{r.due_date ? new Date(r.due_date).toLocaleDateString() : '—'}</span>
    )},
    { key: 'status', label: 'Status', render: (r) => <StatusBadge status={r.status || 'draft'} /> },
  ];

  const paymentColumns: Column[] = [
    { key: 'payment_date', label: 'Date', sortable: true, render: (r) => (
      <span className="text-xs text-[#999]" suppressHydrationWarning>{(r.payment_date || r.date) ? new Date(r.payment_date || r.date).toLocaleDateString() : '—'}</span>
    )},
    { key: 'amount', label: 'Amount', sortable: true, render: (r) => (
      <span className="text-[#22c55e] font-bold">{fmt(r.amount || 0)}</span>
    )},
    { key: 'invoice_number', label: 'Invoice #' },
    { key: 'method', label: 'Method' },
    { key: 'reference', label: 'Reference' },
  ];

  const columnsMap: Record<Tab, Column[]> = {
    overview: [],
    quotes: quoteColumns,
    invoices: invoiceColumns,
    payments: paymentColumns,
    notes: [],
  };

  if (loading) {
    return (
      <div style={{ backgroundColor: '#f5f3ef', minHeight: '100vh' }}>
        <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
          <div className="animate-pulse space-y-4">
            <div className="h-6 bg-[#ece8e0] rounded-xl w-48" />
            <div className="h-4 bg-[#ece8e0] rounded-xl w-64" />
            <div className="grid grid-cols-4 gap-4">
              {[1, 2, 3, 4].map(i => <div key={i} className="h-24 bg-[#ece8e0] rounded-[14px]" />)}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !customer) {
    return (
      <div style={{ backgroundColor: '#f5f3ef', minHeight: '100vh' }}>
        <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
          {onBack && (
            <button onClick={onBack} className="flex items-center gap-1 text-sm text-[#999] hover:text-[#555] mb-4 cursor-pointer transition-colors" style={{ background: 'none', border: 'none' }}>
              <ArrowLeft size={16} /> Back to Customers
            </button>
          )}
          <div style={{ padding: 16, borderRadius: 12, background: '#fef2f2', border: '1px solid #fca5a5' }}>
            <div className="flex items-center gap-2 text-sm" style={{ color: '#b91c1c' }}>
              <AlertCircle size={16} /> {error || 'Customer not found'}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const name = cleanName(customer.name);
  const company = cleanName(customer.company || '');
  const showCompany = company && company.toLowerCase() !== name.toLowerCase();
  const typeStyle = TYPE_STYLES[customer.type?.toLowerCase()] || TYPE_STYLES.residential;

  // Get data from the customer detail endpoint (which includes quotes, invoices, payments inline)
  const custQuotes = customer.quotes || [];
  const ledger = financeLedger || customer.finance_ledger || null;
  const custInvoices = ledger?.invoices || customer.invoices || [];
  const custPayments = ledger?.payments || customer.payments || [];
  const ledgerSummary = ledger?.summary;
  const totalQuoteValue = custQuotes.reduce((sum: number, q: any) => sum + (q.total || 0), 0);

  return (
    <div style={{ backgroundColor: '#f5f3ef', minHeight: '100vh' }}>
      <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
        {/* Back */}
        {onBack && (
          <button onClick={onBack} className="flex items-center gap-1 text-sm text-[#999] hover:text-[#555] mb-5 cursor-pointer transition-colors" style={{ background: 'none', border: 'none' }}>
            <ArrowLeft size={16} /> Back to Customers
          </button>
        )}

        {/* Header Card */}
        <div style={{ background: '#fff', borderRadius: 16, border: '1px solid #ece8e0', padding: '24px 28px', marginBottom: 20, boxShadow: '0 1px 3px rgba(0,0,0,0.04)' }}>
          <div className="flex items-start gap-5">
            {/* Avatar */}
            <div style={{
              width: 64, height: 64, borderRadius: '50%',
              backgroundColor: typeStyle.bg, color: typeStyle.text,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 22, fontWeight: 800, flexShrink: 0, letterSpacing: 0.5,
            }}>
              {initials(customer.name)}
            </div>

            {editing ? (
              <div className="flex-1 space-y-3">
                <input value={editForm.name} onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))}
                  className="w-full px-3 py-2 text-lg font-bold rounded-xl border border-[#ece8e0] bg-[#faf9f7] focus:border-[#b8960c] outline-none" placeholder="Name" />
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <input value={editForm.company} onChange={e => setEditForm(f => ({ ...f, company: e.target.value }))}
                    className="px-3 py-2 text-sm rounded-xl border border-[#ece8e0] bg-[#faf9f7] focus:border-[#b8960c] outline-none" placeholder="Company" />
                  <select value={editForm.type} onChange={e => setEditForm(f => ({ ...f, type: e.target.value }))}
                    className="px-3 py-2 text-sm rounded-xl border border-[#ece8e0] bg-[#faf9f7] focus:border-[#b8960c] outline-none">
                    <option value="residential">Residential</option>
                    <option value="designer">Designer</option>
                    <option value="commercial">Commercial</option>
                    <option value="contractor">Contractor</option>
                  </select>
                  <input value={editForm.email} onChange={e => setEditForm(f => ({ ...f, email: e.target.value }))}
                    className="px-3 py-2 text-sm rounded-xl border border-[#ece8e0] bg-[#faf9f7] focus:border-[#b8960c] outline-none" placeholder="Email" />
                  <input value={editForm.phone} onChange={e => setEditForm(f => ({ ...f, phone: e.target.value }))}
                    className="px-3 py-2 text-sm rounded-xl border border-[#ece8e0] bg-[#faf9f7] focus:border-[#b8960c] outline-none" placeholder="Phone" />
                </div>
                <input value={editForm.address} onChange={e => setEditForm(f => ({ ...f, address: e.target.value }))}
                  className="w-full px-3 py-2 text-sm rounded-xl border border-[#ece8e0] bg-[#faf9f7] focus:border-[#b8960c] outline-none" placeholder="Address" />
                <div className="flex gap-2">
                  <button onClick={saveEdit} disabled={saving}
                    className="flex items-center gap-2 cursor-pointer transition-colors"
                    style={{ minHeight: 44, padding: '0 20px', borderRadius: 12, background: '#b8960c', color: '#fff', border: 'none', fontSize: 13, fontWeight: 700 }}>
                    {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />} {saving ? 'Saving...' : 'Save'}
                  </button>
                  <button onClick={() => setEditing(false)}
                    className="flex items-center gap-2 cursor-pointer transition-colors"
                    style={{ minHeight: 44, padding: '0 20px', borderRadius: 12, background: '#faf9f7', color: '#777', border: '1px solid #ece8e0', fontSize: 13, fontWeight: 700 }}>
                    <X size={14} /> Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex-1">
                <div className="flex items-center gap-3 flex-wrap">
                  <h1 style={{ fontSize: 22, fontWeight: 800, color: '#1a1a1a', margin: 0 }}>{name}</h1>
                  {(customer.total_revenue || 0) > 10000 && <Crown size={18} style={{ color: '#b8960c' }} />}
                  <span style={{
                    display: 'inline-block', padding: '3px 14px', borderRadius: 999,
                    fontSize: 12, fontWeight: 700, backgroundColor: typeStyle.bg, color: typeStyle.text,
                  }}>
                    {typeStyle.label}
                  </span>
                  <button onClick={startEdit} className="p-2 rounded-lg text-[#999] hover:text-[#b8960c] hover:bg-[#fdf8eb] transition-colors cursor-pointer" style={{ background: 'none', border: 'none' }} title="Edit customer">
                    <Pencil size={16} />
                  </button>
                </div>

                {showCompany && (
                  <div className="flex items-center gap-2 mt-2" style={{ fontSize: 14, color: '#666' }}>
                    <Building2 size={14} /> {company}
                  </div>
                )}

                <div className="flex items-center gap-5 mt-3 flex-wrap" style={{ fontSize: 13, color: '#888' }}>
                  {customer.email && <span className="flex items-center gap-1.5"><Mail size={13} /> {customer.email}</span>}
                  {customer.phone && <span className="flex items-center gap-1.5"><Phone size={13} /> {customer.phone}</span>}
                  {customer.address && <span className="flex items-center gap-1.5"><MapPin size={13} /> {customer.address}</span>}
                </div>

                {/* Tags */}
                {customer.tags && customer.tags.length > 0 && (
                  <div className="flex items-center gap-2 mt-3 flex-wrap">
                    <Tag size={12} style={{ color: '#bbb' }} />
                    {customer.tags.map((tag: string) => (
                      <span key={tag} style={{
                        fontSize: 11, padding: '2px 10px', borderRadius: 999,
                        background: '#f5f3ef', color: '#777', border: '1px solid #ece8e0',
                      }}>{tag}</span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-5">
          <KPICard icon={<DollarSign size={20} />} label="Total Paid" value={fmt(ledgerSummary?.total_paid ?? customer.total_revenue ?? 0)} color="#16a34a" />
          <KPICard icon={<ClipboardList size={20} />} label="Quotes" value={String(custQuotes.length || customer.lifetime_quotes || 0)} color="#b8960c" />
          <KPICard icon={<FileText size={20} />} label="Open Balance" value={fmt(ledgerSummary?.current_balance ?? 0)} color="#ea580c" />
          <KPICard icon={<DollarSign size={20} />} label="Aging" value={fmt(ledgerSummary?.aging_total ?? 0)} color="#7c3aed" />
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 mb-5" style={{ padding: 4, width: 'fit-content', background: '#fff', borderRadius: 12, border: '1px solid #ece8e0' }}>
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
        {tab === 'overview' ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Recent Quotes */}
            <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #ece8e0', padding: 20 }}>
              <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
                <ClipboardList size={15} style={{ color: '#b8960c' }} /> Recent Quotes
              </h3>
              {custQuotes.length > 0 ? (
                <div className="space-y-2">
                  {custQuotes.slice(0, 5).map((q: any, i: number) => (
                    <div key={i} style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{q.quote_number || `Q-${i + 1}`}</div>
                        <div style={{ fontSize: 10, color: '#999' }} suppressHydrationWarning>
                          {q.created_at ? new Date(q.created_at).toLocaleDateString() : ''}
                        </div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: 13, fontWeight: 700, color: '#b8960c' }}>{fmt(q.total || 0)}</div>
                        <StatusBadge status={q.status || 'draft'} />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: 13, color: '#aaa', textAlign: 'center', padding: '20px 0' }}>No quotes yet</div>
              )}
            </div>

            {/* Contact & Details */}
            <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #ece8e0', padding: 20 }}>
              <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
                <User size={15} style={{ color: '#2563eb' }} /> Contact Details
              </h3>
              <div className="space-y-3">
                <DetailRow label="Type" value={typeStyle.label} />
                <DetailRow label="Email" value={customer.email || '—'} />
                <DetailRow label="Phone" value={customer.phone || '—'} />
                <DetailRow label="Address" value={customer.address || '—'} />
                <DetailRow label="Company" value={showCompany ? company : '—'} />
                <DetailRow label="Source" value={customer.source || '—'} />
                <DetailRow label="Created" value={customer.created_at ? new Date(customer.created_at).toLocaleDateString() : '—'} />
              </div>
              {customer.notes && (
                <div style={{ marginTop: 16, padding: 12, borderRadius: 10, background: '#faf9f7', border: '1px solid #ece8e0' }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 6 }}>Notes</div>
                  <div style={{ fontSize: 13, color: '#555', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>{customer.notes}</div>
                </div>
              )}
            </div>

            {/* Finance Statement */}
            <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #ece8e0', padding: 20 }}>
              <div className="flex items-center justify-between gap-3 mb-3">
                <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <DollarSign size={15} style={{ color: '#16a34a' }} /> Finance Statement
                </h3>
                <div className="flex items-center gap-2 flex-wrap justify-end">
                  <button onClick={handleExportStatement} className="flex items-center gap-1 cursor-pointer" style={{ fontSize: 11, fontWeight: 700, color: '#555', background: '#faf9f7', border: '1px solid #ece8e0', borderRadius: 8, padding: '7px 10px' }}>
                    <FileText size={12} /> Export JSON
                  </button>
                  <button onClick={handlePrintStatement} className="flex items-center gap-1 cursor-pointer" style={{ fontSize: 11, fontWeight: 700, color: '#555', background: '#faf9f7', border: '1px solid #ece8e0', borderRadius: 8, padding: '7px 10px' }}>
                    <Printer size={12} /> Print
                  </button>
                  <button onClick={handleLogReminder} disabled={collectionBusy || !ledgerSummary?.current_balance} className="flex items-center gap-1 cursor-pointer disabled:opacity-50" style={{ fontSize: 11, fontWeight: 700, color: '#fff', background: '#b8960c', border: '1px solid #b8960c', borderRadius: 8, padding: '7px 10px' }}>
                    {collectionBusy ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />} Log Reminder
                  </button>
                </div>
              </div>
              {collectionMessage && (
                <div style={{ fontSize: 12, color: collectionMessage.includes('Failed') ? '#b91c1c' : '#166534', background: collectionMessage.includes('Failed') ? '#fef2f2' : '#f0fdf4', border: `1px solid ${collectionMessage.includes('Failed') ? '#fecaca' : '#bbf7d0'}`, borderRadius: 8, padding: '8px 10px', marginBottom: 12 }}>
                  {collectionMessage}
                </div>
              )}
              <div className="grid grid-cols-2 gap-3 mb-4">
                <DetailRow label="Business" value={ledger?.business || customer.business || 'all'} />
                <DetailRow label="Invoiced" value={fmt(ledgerSummary?.total_invoiced ?? 0)} />
                <DetailRow label="Paid" value={fmt(ledgerSummary?.total_paid ?? 0)} />
                <DetailRow label="Balance" value={fmt(ledgerSummary?.current_balance ?? 0)} />
                <DetailRow label="Open Invoices" value={String(ledgerSummary?.open_invoice_count ?? 0)} />
                <DetailRow label="Overdue" value={fmt(ledgerSummary?.overdue_balance ?? 0)} />
              </div>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 8 }}>Aging Contribution</div>
              <div className="grid grid-cols-4 gap-2 mb-4">
                {['0_30', '31_60', '61_90', '90_plus'].map(bucket => (
                  <div key={bucket} style={{ padding: 10, borderRadius: 10, background: '#faf9f7', border: '1px solid #ece8e0' }}>
                    <div style={{ fontSize: 10, color: '#999', fontWeight: 700 }}>{bucket.replace('_', '-')}</div>
                    <div style={{ fontSize: 13, color: '#1a1a1a', fontWeight: 800 }}>{fmt(ledger?.aging?.[bucket] ?? 0)}</div>
                  </div>
                ))}
              </div>
              <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 8 }}>Recent Activity</div>
              {(ledger?.transactions || []).length > 0 ? (
                <div className="space-y-2">
                  {(ledger?.transactions || []).slice(0, 6).map((txn: any) => (
                    <div key={txn.id} style={{ padding: '9px 10px', borderRadius: 10, border: '1px solid #ece8e0', display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                      <div>
                        <div style={{ fontSize: 12, color: '#1a1a1a', fontWeight: 700 }}>{txn.type === 'payment' ? 'Payment' : 'Invoice'} {txn.invoice_number || ''}</div>
                        <div style={{ fontSize: 10, color: '#999' }}>{txn.date ? new Date(txn.date).toLocaleDateString() : 'No date'} {txn.reference ? `- ${txn.reference}` : ''}</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: 13, color: txn.type === 'payment' ? '#16a34a' : '#1a1a1a', fontWeight: 800 }}>{txn.type === 'payment' ? '-' : ''}{fmt(txn.amount || 0)}</div>
                        <div style={{ fontSize: 10, color: '#999' }}>Balance {fmt(txn.running_balance || 0)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: 13, color: '#aaa', textAlign: 'center', padding: '16px 0' }}>No finance activity yet</div>
              )}
              {(ledger?.collections || []).length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', marginBottom: 8 }}>Collections History</div>
                  <div className="space-y-2">
                    {(ledger?.collections || []).slice(0, 4).map((event: any) => (
                      <div key={event.id} style={{ padding: '8px 10px', borderRadius: 8, background: '#faf9f7', border: '1px solid #ece8e0', fontSize: 12, color: '#555' }}>
                        <strong>{event.action}</strong> - {event.created_at ? new Date(event.created_at).toLocaleString() : ''}
                        <span style={{ float: 'right', fontWeight: 700 }}>{fmt(event.open_balance || 0)}</span>
                        {event.notes && <div style={{ color: '#999', fontSize: 11, marginTop: 3 }}>{event.notes}</div>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : tab === 'notes' ? (
          <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #ece8e0', padding: 20 }}>
            {editing ? (
              <textarea value={editForm.notes} onChange={e => setEditForm(f => ({ ...f, notes: e.target.value }))}
                rows={8} className="w-full px-3 py-3 text-sm rounded-xl border border-[#ece8e0] bg-[#faf9f7] focus:border-[#b8960c] outline-none resize-y"
                placeholder="Add notes about this customer..." />
            ) : (
              <>
                <div className="flex items-center justify-between mb-4">
                  <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Customer Notes</h3>
                  <button onClick={startEdit} className="flex items-center gap-1 cursor-pointer transition-colors"
                    style={{ fontSize: 12, fontWeight: 600, color: '#b8960c', background: 'none', border: 'none' }}>
                    <Pencil size={12} /> Edit
                  </button>
                </div>
                <p style={{ fontSize: 14, color: '#555', whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{customer.notes || 'No notes for this customer. Click Edit to add notes.'}</p>
              </>
            )}
          </div>
        ) : (
          (() => {
            // Use inline data from customer detail if available, otherwise use fetched tab data
            let data = tabData;
            if (tab === 'quotes' && data.length === 0 && custQuotes.length > 0) data = custQuotes;
            if (tab === 'invoices' && data.length === 0 && custInvoices.length > 0) data = custInvoices;
            if (tab === 'payments' && data.length === 0 && custPayments.length > 0) data = custPayments;

            return data.length === 0 && !tabLoading ? (
              <EmptyState
                icon={tab === 'quotes' ? <ClipboardList size={40} /> : tab === 'invoices' ? <FileText size={40} /> : <CreditCard size={40} />}
                title={`No ${tab} found`}
                description={`This customer has no ${tab} on record.`}
              />
            ) : (
              <DataTable
                columns={columnsMap[tab]}
                data={data}
                loading={tabLoading}
                emptyMessage={`No ${tab} found.`}
              />
            );
          })()
        )}
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between" style={{ padding: '8px 0', borderBottom: '1px solid #f5f3ef' }}>
      <span style={{ fontSize: 12, color: '#999', fontWeight: 600 }}>{label}</span>
      <span style={{ fontSize: 13, color: '#555' }}>{value}</span>
    </div>
  );
}
