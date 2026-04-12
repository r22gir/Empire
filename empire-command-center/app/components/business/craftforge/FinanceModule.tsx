'use client';
import React, { useState, useEffect, useCallback } from 'react';
import { API } from '../../../lib/api';
import {
  DollarSign, TrendingUp, FileText, Receipt, CreditCard, Clock,
  Download, Send, CheckCircle, X, Loader2, Plus, Trash2, ShoppingCart
} from 'lucide-react';
import KPICard from '../shared/KPICard';
import DataTable, { Column } from '../shared/DataTable';
import StatusBadge from '../shared/StatusBadge';
import EmptyState from '../shared/EmptyState';

// ── Types ──────────────────────────────────────────────────────────────
interface FinanceDashboard {
  revenue: { mtd: number; ytd: number };
  expenses: { mtd: number; ytd: number; breakdown_mtd?: { category: string; total: number }[] };
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

interface LineItem {
  description: string;
  qty: number;
  rate: number;
  amount: number;
}

interface Expense {
  id: string;
  expense_date: string;
  vendor: string;
  category: string;
  amount: number;
  description: string;
}

type ActiveTab = 'invoices' | 'expenses';

const PAYMENT_METHODS = ['Cash', 'Check', 'Card', 'Zelle', 'Venmo', 'Wire', 'Crypto (USDT)', 'Crypto (BTC)'];

const EXPENSE_CATEGORIES = [
  'materials', 'hardware', 'tools', 'cnc_supplies', 'labor', 'shipping',
  'rent', 'utilities', 'marketing', 'vehicle', 'insurance', 'other',
];

const CATEGORY_LABELS: Record<string, string> = {
  materials: 'Materials',
  hardware: 'Hardware',
  tools: 'Tools',
  cnc_supplies: 'CNC Supplies',
  labor: 'Labor',
  shipping: 'Shipping',
  rent: 'Rent',
  utilities: 'Utilities',
  marketing: 'Marketing',
  vehicle: 'Vehicle',
  insurance: 'Insurance',
  other: 'Other',
};

const todayISO = () => {
  const d = new Date();
  return d.toISOString().slice(0, 10);
};

const fmt = (n: number) =>
  `$${Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

// ── Shared style constants ─────────────────────────────────────────────
const inputStyle: React.CSSProperties = {
  width: '100%', padding: '10px 14px', fontSize: 14,
  border: '1.5px solid #ddd', borderRadius: 8, marginBottom: 14,
  outline: 'none', boxSizing: 'border-box',
};

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 12, fontWeight: 600, color: '#555', marginBottom: 4,
};

// ── Component ──────────────────────────────────────────────────────────
export default function FinanceModule() {
  const [dashboard, setDashboard] = useState<FinanceDashboard | null>(null);
  const [designs, setDesigns] = useState<any[]>([]);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [payments, setPayments] = useState<any[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<ActiveTab>('invoices');

  // Payment modal state
  const [paymentModal, setPaymentModal] = useState<{ open: boolean; invoice: any | null }>({ open: false, invoice: null });
  const [paymentForm, setPaymentForm] = useState<PaymentForm>({ amount: '', method: 'Cash', reference: '', notes: '', date: todayISO() });
  const [submitting, setSubmitting] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Invoice creation modal state
  const [invoiceModal, setInvoiceModal] = useState(false);
  const [invCustomer, setInvCustomer] = useState('');
  const [invItems, setInvItems] = useState<LineItem[]>([{ description: '', qty: 1, rate: 0, amount: 0 }]);
  const [invTaxRate, setInvTaxRate] = useState('6');
  const [invNotes, setInvNotes] = useState('');
  const [invSaving, setInvSaving] = useState(false);
  const [invError, setInvError] = useState<string | null>(null);

  // Expense form state
  const [expDate, setExpDate] = useState(todayISO());
  const [expVendor, setExpVendor] = useState('');
  const [expCategory, setExpCategory] = useState('materials');
  const [expAmount, setExpAmount] = useState('');
  const [expDesc, setExpDesc] = useState('');
  const [expSaving, setExpSaving] = useState(false);
  const [expError, setExpError] = useState<string | null>(null);

  // ── Data fetching ──────────────────────────────────────────────────
  const fetchAll = useCallback(() => {
    setLoading(true);
    Promise.allSettled([
      fetch(`${API}/finance/dashboard`).then(r => r.json()),
      fetch(`${API}/craftforge/designs`).then(r => r.json()),
      fetch(`${API}/finance/invoices?business=woodcraft`).then(r => r.json()),
      fetch(`${API}/finance/payments?limit=10`).then(r => r.json()),
      fetch(`${API}/finance/expenses?limit=100&business=woodcraft`).then(r => r.json()),
    ]).then(([dashRes, desRes, invRes, payRes, expRes]) => {
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
      if (expRes.status === 'fulfilled') {
        const raw = expRes.value;
        setExpenses(Array.isArray(raw) ? raw : raw.expenses || []);
      }
      setLoading(false);
    });
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const refreshInvoices = useCallback(() => {
    fetch(`${API}/finance/invoices?business=woodcraft`).then(r => r.json()).then(raw => {
      setInvoices(Array.isArray(raw) ? raw : raw.invoices || []);
    }).catch(() => {});
    fetch(`${API}/finance/payments?limit=10`).then(r => r.json()).then(raw => {
      setPayments(Array.isArray(raw) ? raw : raw.payments || []);
    }).catch(() => {});
    fetch(`${API}/finance/dashboard`).then(r => r.json()).then(d => setDashboard(d)).catch(() => {});
  }, []);

  const refreshExpenses = useCallback(() => {
    fetch(`${API}/finance/expenses?limit=100&business=woodcraft`).then(r => r.json()).then(raw => {
      setExpenses(Array.isArray(raw) ? raw : raw.expenses || []);
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

  // Expense category summary
  const expenseByCat: Record<string, number> = {};
  expenses.forEach(e => {
    const cat = e.category || 'other';
    expenseByCat[cat] = (expenseByCat[cat] || 0) + Number(e.amount || 0);
  });
  const expenseTotalAll = Object.values(expenseByCat).reduce((a, b) => a + b, 0);

  // ── Invoice line item helpers ────────────────────────────────────────
  const updateLineItem = (idx: number, field: keyof LineItem, value: string | number) => {
    setInvItems(prev => {
      const next = [...prev];
      const item = { ...next[idx], [field]: value };
      if (field === 'qty' || field === 'rate') {
        item.amount = Number(item.qty) * Number(item.rate);
      }
      next[idx] = item;
      return next;
    });
  };

  const addLineItem = () => {
    setInvItems(prev => [...prev, { description: '', qty: 1, rate: 0, amount: 0 }]);
  };

  const removeLineItem = (idx: number) => {
    setInvItems(prev => prev.length > 1 ? prev.filter((_, i) => i !== idx) : prev);
  };

  const invSubtotal = invItems.reduce((sum, i) => sum + (Number(i.amount) || 0), 0);
  const invTaxAmt = invSubtotal * (parseFloat(invTaxRate) || 0) / 100;
  const invTotal = invSubtotal + invTaxAmt;

  // ── Create manual invoice ────────────────────────────────────────────
  const submitManualInvoice = async (status: 'draft' | 'sent') => {
    if (!invCustomer.trim()) { setInvError('Customer name is required'); return; }
    if (invItems.every(i => !i.description.trim())) { setInvError('Add at least one line item'); return; }
    setInvSaving(true);
    setInvError(null);
    try {
      const lineItems = invItems.filter(i => i.description.trim()).map(i => ({
        description: i.description,
        quantity: Number(i.qty),
        unit_price: Number(i.rate),
        total: Number(i.amount),
      }));
      const body = {
        customer_name: invCustomer.trim(),
        business_unit: 'woodcraft',
        subtotal: invSubtotal,
        tax_rate: (parseFloat(invTaxRate) || 0) / 100,
        line_items: lineItems,
        notes: invNotes || undefined,
        terms: 'Net 30',
      };
      const res = await fetch(`${API}/finance/invoices`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error('Failed to create invoice');
      const data = await res.json();

      // If status is 'sent', send it immediately
      if (status === 'sent' && data.invoice?.id) {
        await fetch(`${API}/finance/invoices/${data.invoice.id}/send`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        }).catch(() => {});
      }

      // Reset form
      setInvoiceModal(false);
      setInvCustomer('');
      setInvItems([{ description: '', qty: 1, rate: 0, amount: 0 }]);
      setInvTaxRate('6');
      setInvNotes('');
      refreshInvoices();
    } catch (e: any) {
      setInvError(e.message || 'Failed to create invoice');
    }
    setInvSaving(false);
  };

  // ── Create expense ───────────────────────────────────────────────────
  const submitExpense = async () => {
    if (!expAmount || parseFloat(expAmount) <= 0) { setExpError('Amount is required'); return; }
    setExpSaving(true);
    setExpError(null);
    try {
      const body = {
        category: expCategory,
        vendor: expVendor || undefined,
        description: expDesc || undefined,
        amount: parseFloat(expAmount),
        expense_date: expDate,
        business: 'woodcraft',
      };
      const res = await fetch(`${API}/finance/expenses`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error('Failed to save expense');
      // Reset form
      setExpVendor('');
      setExpAmount('');
      setExpDesc('');
      setExpDate(todayISO());
      setExpCategory('materials');
      refreshExpenses();
    } catch (e: any) {
      setExpError(e.message || 'Failed to save expense');
    }
    setExpSaving(false);
  };

  const deleteExpense = async (id: string) => {
    setActionLoading(`del-exp-${id}`);
    try {
      await fetch(`${API}/finance/expenses/${id}`, { method: 'DELETE' });
      refreshExpenses();
    } catch (e) { console.error('Delete expense failed:', e); }
    setActionLoading(null);
  };

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
    { key: 'total', label: 'Total', sortable: true, render: (row) => <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{fmt(row.total || row.amount || 0)}</span> },
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
    { key: 'total', label: 'Total', sortable: true, render: (row) => <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{fmt(row.total || row.amount || 0)}</span> },
    { key: 'paid', label: 'Paid', render: (row) => <span style={{ fontSize: 13, color: '#22c55e', fontWeight: 600 }}>{fmt(row.amount_paid || row.paid || 0)}</span> },
    { key: 'balance_due', label: 'Balance Due', sortable: true, render: (row) => {
      const bal = row.balance_due ?? (Number(row.total || 0) - Number(row.amount_paid || row.paid || 0));
      return <span style={{ fontSize: 13, fontWeight: 700, color: bal > 0 ? '#dc2626' : '#22c55e' }}>{fmt(bal)}</span>;
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
    { key: 'amount', label: 'Amount', sortable: true, render: (row) => <span style={{ fontSize: 13, fontWeight: 700, color: '#22c55e' }}>{fmt(row.amount || 0)}</span> },
    { key: 'method', label: 'Method', render: (row) => <span style={{ fontSize: 12, color: '#555' }}>{row.method || '--'}</span> },
    { key: 'reference', label: 'Reference', render: (row) => <span style={{ fontSize: 11, color: '#999', fontFamily: 'monospace' }}>{row.reference || '--'}</span> },
  ];

  const expenseColumns: Column[] = [
    { key: 'expense_date', label: 'Date', sortable: true, render: (row) => <span style={{ fontSize: 12, color: '#555' }} suppressHydrationWarning>{row.expense_date ? new Date(row.expense_date).toLocaleDateString() : '--'}</span> },
    { key: 'vendor', label: 'Vendor', sortable: true, render: (row) => <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{row.vendor || '--'}</span> },
    { key: 'category', label: 'Category', sortable: true, render: (row) => (
      <span style={{
        fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 4,
        background: '#fdf8eb', color: '#b8960c', border: '1px solid #ece8e0',
      }}>
        {CATEGORY_LABELS[row.category] || row.category || '--'}
      </span>
    )},
    { key: 'description', label: 'Description', render: (row) => <span style={{ fontSize: 12, color: '#555' }}>{row.description || '--'}</span> },
    { key: 'amount', label: 'Amount', sortable: true, render: (row) => <span style={{ fontSize: 13, fontWeight: 700, color: '#dc2626' }}>{fmt(row.amount || 0)}</span> },
    {
      key: '_actions', label: '', render: (row) => (
        <ActionBtn onClick={() => deleteExpense(row.id)} icon={<Trash2 size={12} />} label="Delete" loadingKey={`del-exp-${row.id}`} color="#dc2626" />
      ),
    },
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

  // ── Tab button helper ──────────────────────────────────────────────
  const TabBtn = ({ tab, label, icon }: { tab: ActiveTab; label: string; icon: React.ReactNode }) => (
    <button
      onClick={() => setActiveTab(tab)}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '8px 18px', fontSize: 13, fontWeight: 600,
        color: activeTab === tab ? '#b8960c' : '#888',
        background: activeTab === tab ? '#fdf8eb' : 'transparent',
        border: activeTab === tab ? '1.5px solid #b8960c' : '1.5px solid #ece8e0',
        borderRadius: 8, cursor: 'pointer',
        transition: 'all 0.15s ease',
      }}
    >
      {icon} {label}
    </button>
  );

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
          value={fmt(revenueMTD)}
          color="#22c55e"
        />
        <KPICard
          icon={<Receipt size={20} />}
          label="Outstanding Invoices"
          value={`${outstandingCount} / ${fmt(outstandingTotal)}`}
          color="#d97706"
        />
        <KPICard
          icon={<ShoppingCart size={20} />}
          label="Expenses MTD"
          value={fmt(expensesMTD)}
          color="#dc2626"
        />
        <KPICard
          icon={<DollarSign size={20} />}
          label="Net Profit MTD"
          value={fmt(netProfitMTD)}
          color={netProfitMTD >= 0 ? '#22c55e' : '#dc2626'}
        />
      </div>

      {/* ── Tab Navigation ────────────────────────────────────────── */}
      <div className="flex items-center gap-2 mb-5">
        <TabBtn tab="invoices" label="Invoices & Quotes" icon={<FileText size={14} />} />
        <TabBtn tab="expenses" label="Expenses" icon={<ShoppingCart size={14} />} />
      </div>

      {/* ═══════════════════════════════════════════════════════════ */}
      {/* ── INVOICES TAB ──────────────────────────────────────────── */}
      {/* ═══════════════════════════════════════════════════════════ */}
      {activeTab === 'invoices' && (
        <>
          {/* ── AR Aging ──────────────────────────────────────────── */}
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
                  {fmt(bucket.value)}
                </span>
              </div>
            ))}
          </div>

          {/* ── Open Quotes ───────────────────────────────────────── */}
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

          {/* ── Open Invoices ─────────────────────────────────────── */}
          <div className="flex items-center justify-between mb-2">
            <div className="section-label" style={{ marginBottom: 0 }}>Open Invoices</div>
            <button
              onClick={() => { setInvoiceModal(true); setInvError(null); }}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 6,
                padding: '6px 14px', fontSize: 12, fontWeight: 700,
                color: '#fff', background: '#b8960c', border: 'none',
                borderRadius: 8, cursor: 'pointer',
              }}
            >
              <Plus size={14} /> New Invoice
            </button>
          </div>
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

          {/* ── Recent Payments ───────────────────────────────────── */}
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
        </>
      )}

      {/* ═══════════════════════════════════════════════════════════ */}
      {/* ── EXPENSES TAB ──────────────────────────────────────────── */}
      {/* ═══════════════════════════════════════════════════════════ */}
      {activeTab === 'expenses' && (
        <>
          {/* ── Category Summary Cards ────────────────────────────── */}
          <div className="section-label mb-2">Expense Summary by Category</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, marginBottom: 24 }}>
            {Object.entries(expenseByCat)
              .sort(([, a], [, b]) => b - a)
              .map(([cat, total]) => (
                <div
                  key={cat}
                  className="empire-card flat"
                  style={{
                    padding: '12px 16px', minWidth: 140, flex: '0 0 auto',
                    borderLeft: '3px solid #b8960c',
                  }}
                >
                  <div style={{ fontSize: 11, fontWeight: 600, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                    {CATEGORY_LABELS[cat] || cat}
                  </div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', marginTop: 2 }}>
                    {fmt(total)}
                  </div>
                </div>
              ))}
            {expenseTotalAll > 0 && (
              <div
                className="empire-card flat"
                style={{
                  padding: '12px 16px', minWidth: 140, flex: '0 0 auto',
                  borderLeft: '3px solid #22c55e', background: '#fdf8eb',
                }}
              >
                <div style={{ fontSize: 11, fontWeight: 600, color: '#888', textTransform: 'uppercase', letterSpacing: 0.5 }}>
                  Total
                </div>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#b8960c', marginTop: 2 }}>
                  {fmt(expenseTotalAll)}
                </div>
              </div>
            )}
          </div>

          {/* ── Quick-Add Expense Form ────────────────────────────── */}
          <div className="section-label mb-2">Quick-Add Expense</div>
          <div className="empire-card flat" style={{ padding: '20px 24px', marginBottom: 24 }}>
            {expError && (
              <div style={{ fontSize: 12, color: '#dc2626', marginBottom: 12, padding: '8px 12px', background: '#fef2f2', borderRadius: 6 }}>
                {expError}
              </div>
            )}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 120px', gap: 12, marginBottom: 12 }}>
              <div>
                <label style={labelStyle}>Date *</label>
                <input
                  type="date"
                  value={expDate}
                  onChange={(e) => setExpDate(e.target.value)}
                  style={{ ...inputStyle, marginBottom: 0 }}
                />
              </div>
              <div>
                <label style={labelStyle}>Vendor</label>
                <input
                  type="text"
                  value={expVendor}
                  onChange={(e) => setExpVendor(e.target.value)}
                  placeholder="e.g. Home Depot"
                  style={{ ...inputStyle, marginBottom: 0 }}
                />
              </div>
              <div>
                <label style={labelStyle}>Category *</label>
                <select
                  value={expCategory}
                  onChange={(e) => setExpCategory(e.target.value)}
                  style={{ ...inputStyle, marginBottom: 0, background: '#fff' }}
                >
                  {EXPENSE_CATEGORIES.map(c => (
                    <option key={c} value={c}>{CATEGORY_LABELS[c] || c}</option>
                  ))}
                </select>
              </div>
              <div>
                <label style={labelStyle}>Amount ($) *</label>
                <input
                  type="number"
                  step="0.01"
                  value={expAmount}
                  onChange={(e) => setExpAmount(e.target.value)}
                  placeholder="0.00"
                  style={{ ...inputStyle, marginBottom: 0, fontWeight: 600 }}
                />
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 12, alignItems: 'end' }}>
              <div>
                <label style={labelStyle}>Description</label>
                <input
                  type="text"
                  value={expDesc}
                  onChange={(e) => setExpDesc(e.target.value)}
                  placeholder="What was this expense for?"
                  style={{ ...inputStyle, marginBottom: 0 }}
                />
              </div>
              <button
                onClick={submitExpense}
                disabled={expSaving || !expAmount || parseFloat(expAmount) <= 0}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  padding: '10px 20px', fontSize: 13, fontWeight: 700,
                  color: '#fff', background: '#b8960c', border: 'none',
                  borderRadius: 8, cursor: expSaving ? 'not-allowed' : 'pointer',
                  opacity: expSaving || !expAmount || parseFloat(expAmount) <= 0 ? 0.5 : 1,
                  height: 42,
                }}
              >
                {expSaving ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                {expSaving ? 'Saving...' : 'Add Expense'}
              </button>
            </div>
          </div>

          {/* ── Expense Table ─────────────────────────────────────── */}
          <div className="section-label mb-2">All Expenses</div>
          <div style={{ marginBottom: 24 }}>
            {expenses.length === 0 ? (
              <EmptyState
                icon={<ShoppingCart size={32} />}
                title="No expenses recorded"
                description="Add your first expense using the form above."
              />
            ) : (
              <DataTable columns={expenseColumns} data={expenses} />
            )}
          </div>
        </>
      )}

      {/* ══════════════════════════════════════════════════════════════ */}
      {/* ── NEW INVOICE MODAL ─────────────────────────────────────── */}
      {/* ══════════════════════════════════════════════════════════════ */}
      {invoiceModal && (
        <div
          style={{
            position: 'fixed', inset: 0, zIndex: 9999,
            background: 'rgba(0,0,0,0.45)', display: 'flex',
            alignItems: 'center', justifyContent: 'center',
          }}
          onClick={() => setInvoiceModal(false)}
        >
          <div
            style={{
              background: '#fff', borderRadius: 14, padding: '28px 32px',
              maxWidth: 680, width: '95%', maxHeight: '90vh', overflowY: 'auto',
              boxShadow: '0 20px 60px rgba(0,0,0,0.25)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-5">
              <h3 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }} className="flex items-center gap-2">
                <FileText size={18} className="text-[#b8960c]" /> New Invoice
              </h3>
              <button
                onClick={() => setInvoiceModal(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}
              >
                <X size={18} color="#999" />
              </button>
            </div>

            {invError && (
              <div style={{ fontSize: 12, color: '#dc2626', marginBottom: 12, padding: '8px 12px', background: '#fef2f2', borderRadius: 6 }}>
                {invError}
              </div>
            )}

            {/* Customer Name */}
            <label style={labelStyle}>Customer Name *</label>
            <input
              type="text"
              value={invCustomer}
              onChange={(e) => setInvCustomer(e.target.value)}
              placeholder="Customer or company name"
              style={{ ...inputStyle, fontWeight: 600 }}
            />

            {/* Line Items Table */}
            <label style={{ ...labelStyle, marginBottom: 8 }}>Line Items</label>
            <div style={{ border: '1px solid #ece8e0', borderRadius: 8, overflow: 'hidden', marginBottom: 14 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: '#faf9f7' }}>
                    <th style={{ padding: '8px 10px', textAlign: 'left', fontWeight: 600, color: '#555', fontSize: 11 }}>Description</th>
                    <th style={{ padding: '8px 10px', textAlign: 'center', fontWeight: 600, color: '#555', fontSize: 11, width: 70 }}>Qty</th>
                    <th style={{ padding: '8px 10px', textAlign: 'center', fontWeight: 600, color: '#555', fontSize: 11, width: 100 }}>Rate ($)</th>
                    <th style={{ padding: '8px 10px', textAlign: 'right', fontWeight: 600, color: '#555', fontSize: 11, width: 100 }}>Amount</th>
                    <th style={{ width: 36 }} />
                  </tr>
                </thead>
                <tbody>
                  {invItems.map((item, idx) => (
                    <tr key={idx} style={{ borderTop: '1px solid #ece8e0' }}>
                      <td style={{ padding: '6px 8px' }}>
                        <input
                          type="text"
                          value={item.description}
                          onChange={(e) => updateLineItem(idx, 'description', e.target.value)}
                          placeholder="Item description"
                          style={{ width: '100%', padding: '6px 8px', border: '1px solid #ddd', borderRadius: 4, fontSize: 13, outline: 'none', boxSizing: 'border-box' }}
                        />
                      </td>
                      <td style={{ padding: '6px 4px', textAlign: 'center' }}>
                        <input
                          type="number"
                          min="1"
                          value={item.qty}
                          onChange={(e) => updateLineItem(idx, 'qty', parseInt(e.target.value) || 1)}
                          style={{ width: 54, padding: '6px 4px', border: '1px solid #ddd', borderRadius: 4, fontSize: 13, textAlign: 'center', outline: 'none' }}
                        />
                      </td>
                      <td style={{ padding: '6px 4px', textAlign: 'center' }}>
                        <input
                          type="number"
                          step="0.01"
                          value={item.rate}
                          onChange={(e) => updateLineItem(idx, 'rate', parseFloat(e.target.value) || 0)}
                          style={{ width: 84, padding: '6px 4px', border: '1px solid #ddd', borderRadius: 4, fontSize: 13, textAlign: 'center', outline: 'none' }}
                        />
                      </td>
                      <td style={{ padding: '6px 8px', textAlign: 'right', fontWeight: 700, fontSize: 13, color: '#1a1a1a' }}>
                        {fmt(item.amount)}
                      </td>
                      <td style={{ padding: '6px 4px', textAlign: 'center' }}>
                        <button
                          onClick={() => removeLineItem(idx)}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 2, color: '#ccc' }}
                          title="Remove item"
                        >
                          <X size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <button
              onClick={addLineItem}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 4,
                padding: '5px 12px', fontSize: 12, fontWeight: 600,
                color: '#b8960c', background: '#fdf8eb', border: '1px solid #ece8e0',
                borderRadius: 6, cursor: 'pointer', marginBottom: 16,
              }}
            >
              <Plus size={12} /> Add Line Item
            </button>

            {/* Totals */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 14 }}>
              <div style={{ width: 260 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#555', marginBottom: 6 }}>
                  <span>Subtotal</span>
                  <span style={{ fontWeight: 600 }}>{fmt(invSubtotal)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 13, color: '#555', marginBottom: 6 }}>
                  <span className="flex items-center gap-2">
                    Tax
                    <input
                      type="number"
                      step="0.1"
                      value={invTaxRate}
                      onChange={(e) => setInvTaxRate(e.target.value)}
                      style={{ width: 50, padding: '2px 4px', border: '1px solid #ddd', borderRadius: 4, fontSize: 12, textAlign: 'center', outline: 'none' }}
                    />
                    %
                  </span>
                  <span style={{ fontWeight: 600 }}>{fmt(invTaxAmt)}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 16, fontWeight: 700, color: '#1a1a1a', borderTop: '2px solid #b8960c', paddingTop: 8 }}>
                  <span>Total</span>
                  <span>{fmt(invTotal)}</span>
                </div>
              </div>
            </div>

            {/* Notes */}
            <label style={labelStyle}>Notes (optional)</label>
            <textarea
              value={invNotes}
              onChange={(e) => setInvNotes(e.target.value)}
              rows={2}
              placeholder="Payment terms, project details, etc."
              style={{ ...inputStyle, resize: 'vertical' }}
            />

            {/* Action Buttons */}
            <div className="flex items-center gap-3" style={{ marginTop: 4 }}>
              <button
                onClick={() => submitManualInvoice('draft')}
                disabled={invSaving}
                style={{
                  flex: 1, padding: '12px 20px', fontSize: 14, fontWeight: 700,
                  color: '#b8960c', background: '#fdf8eb', border: '1.5px solid #b8960c',
                  borderRadius: 10, cursor: invSaving ? 'not-allowed' : 'pointer',
                  opacity: invSaving ? 0.5 : 1,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                }}
              >
                {invSaving ? <Loader2 size={16} className="animate-spin" /> : <FileText size={16} />}
                Save as Draft
              </button>
              <button
                onClick={() => submitManualInvoice('sent')}
                disabled={invSaving}
                style={{
                  flex: 1, padding: '12px 20px', fontSize: 14, fontWeight: 700,
                  color: '#fff', background: '#b8960c', border: 'none',
                  borderRadius: 10, cursor: invSaving ? 'not-allowed' : 'pointer',
                  opacity: invSaving ? 0.5 : 1,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                }}
              >
                {invSaving ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                Send Immediately
              </button>
            </div>
          </div>
        </div>
      )}

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
                Total: {fmt(paymentModal.invoice.total || 0)} | Paid: {fmt(paymentModal.invoice.paid || 0)} | Balance: {fmt(paymentModal.invoice.balance_due ?? (Number(paymentModal.invoice.total || 0) - Number(paymentModal.invoice.paid || 0)))}
              </span>
            </div>

            {/* Amount */}
            <label style={labelStyle}>Amount ($) *</label>
            <input
              type="number"
              step="0.01"
              value={paymentForm.amount}
              onChange={(e) => setPaymentForm(f => ({ ...f, amount: e.target.value }))}
              style={{ ...inputStyle, fontWeight: 600 }}
              placeholder="0.00"
            />

            {/* Method */}
            <label style={labelStyle}>Payment Method *</label>
            <select
              value={paymentForm.method}
              onChange={(e) => setPaymentForm(f => ({ ...f, method: e.target.value }))}
              style={{ ...inputStyle, background: '#fff' }}
            >
              {PAYMENT_METHODS.map(m => <option key={m} value={m}>{m}</option>)}
            </select>

            {/* Reference */}
            <label style={labelStyle}>Reference # (optional)</label>
            <input
              type="text"
              value={paymentForm.reference}
              onChange={(e) => setPaymentForm(f => ({ ...f, reference: e.target.value }))}
              style={inputStyle}
              placeholder="Check #, transaction ID, etc."
            />

            {/* Notes */}
            <label style={labelStyle}>Notes (optional)</label>
            <textarea
              value={paymentForm.notes}
              onChange={(e) => setPaymentForm(f => ({ ...f, notes: e.target.value }))}
              rows={2}
              style={{ ...inputStyle, resize: 'vertical' }}
              placeholder="Optional notes..."
            />

            {/* Date */}
            <label style={labelStyle}>Payment Date *</label>
            <input
              type="date"
              value={paymentForm.date}
              onChange={(e) => setPaymentForm(f => ({ ...f, date: e.target.value }))}
              style={{ ...inputStyle, marginBottom: 20 }}
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
