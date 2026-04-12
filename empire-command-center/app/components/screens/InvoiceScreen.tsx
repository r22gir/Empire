'use client';
import React, { useState, useEffect } from 'react';
import { API } from '../../lib/api';
import {
  FileText, Plus, Search, DollarSign, Send, Download, AlertTriangle,
  CheckCircle, Clock, CreditCard, Eye, Filter
} from 'lucide-react';

const STATUS_CONFIG: Record<string, { bg: string; color: string; label: string }> = {
  draft: { bg: '#f3f4f6', color: '#6b7280', label: 'Draft' },
  sent: { bg: '#dbeafe', color: '#2563eb', label: 'Sent' },
  viewed: { bg: '#fef3c7', color: '#d97706', label: 'Viewed' },
  partial: { bg: '#fed7aa', color: '#ea580c', label: 'Partial' },
  paid: { bg: '#dcfce7', color: '#16a34a', label: 'Paid' },
  overdue: { bg: '#fef2f2', color: '#dc2626', label: 'Overdue' },
  cancelled: { bg: '#f5f3ef', color: '#999', label: 'Cancelled' },
};

export default function InvoiceScreen() {
  const [invoices, setInvoices] = useState<any[]>([]);
  const [filter, setFilter] = useState('all');
  const [summary, setSummary] = useState<any>({});

  useEffect(() => {
    fetch(`${API}/finance/invoices`).then(r => r.json()).then(d => {
      const items = Array.isArray(d) ? d : d.invoices || d.items || [];
      setInvoices(items);
      setSummary({
        total_invoiced: items.reduce((sum: number, inv: any) => sum + (inv.total || inv.amount || 0), 0),
        total_collected: items.reduce((sum: number, inv: any) => sum + (inv.amount_paid || inv.paid_amount || 0), 0),
        total_outstanding: items.reduce((sum: number, inv: any) => sum + (inv.balance_due ?? inv.balance ?? 0), 0),
        total_overdue: items.filter((inv: any) => inv.status === 'overdue').reduce((sum: number, inv: any) => sum + (inv.balance_due ?? inv.balance ?? 0), 0),
      });
    }).catch(() => {});
  }, []);

  const filtered = filter === 'all' ? invoices : invoices.filter((i: any) => i.status === filter || i.payment_status === filter);

  return (
    <div style={{ padding: '20px 24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>Invoices</h2>
          <p style={{ fontSize: 12, color: '#888', marginTop: 2 }}>{invoices.length} invoices</p>
        </div>
        <button style={{ fontSize: 11, padding: '6px 14px', background: '#16a34a', color: '#fff',
          border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
          <Plus size={12} /> New Invoice
        </button>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
        {[
          { label: 'Total Invoiced', value: `$${(summary.total_invoiced || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`, color: '#b8960c' },
          { label: 'Collected', value: `$${(summary.total_collected || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`, color: '#16a34a' },
          { label: 'Outstanding', value: `$${(summary.total_outstanding || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`, color: '#f59e0b' },
          { label: 'Overdue', value: `$${(summary.total_overdue || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}`, color: '#dc2626' },
        ].map((kpi, i) => (
          <div key={i} style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: '14px 18px', flex: 1, minWidth: 130 }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: '#888', textTransform: 'uppercase' }}>{kpi.label}</div>
            <div style={{ fontSize: 20, fontWeight: 700, color: kpi.color, marginTop: 4 }}>{kpi.value}</div>
          </div>
        ))}
      </div>

      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 14 }}>
        {['all', 'draft', 'sent', 'partial', 'paid', 'overdue'].map(s => (
          <button key={s} onClick={() => setFilter(s)} style={{
            fontSize: 10, padding: '4px 12px', borderRadius: 12, cursor: 'pointer',
            border: filter === s ? '2px solid #16a34a' : '1px solid #e5e2dc',
            background: filter === s ? '#f0fdf4' : '#fff', color: filter === s ? '#16a34a' : '#666',
            fontWeight: filter === s ? 600 : 400,
          }}>
            {s === 'all' ? 'All' : (STATUS_CONFIG[s]?.label || s)} ({s === 'all' ? invoices.length : invoices.filter((i: any) => i.status === s || i.payment_status === s).length})
          </button>
        ))}
      </div>

      {/* Invoice table */}
      {filtered.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>No invoices found.</div>
      ) : (
        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
          <thead><tr style={{ borderBottom: '2px solid #e5e2dc', textAlign: 'left' }}>
            <th style={{ padding: 8 }}>Invoice #</th>
            <th style={{ padding: 8 }}>Client</th>
            <th style={{ padding: 8 }}>Amount</th>
            <th style={{ padding: 8 }}>Paid</th>
            <th style={{ padding: 8 }}>Balance</th>
            <th style={{ padding: 8 }}>Status</th>
            <th style={{ padding: 8 }}>Date</th>
            <th style={{ padding: 8 }}>Actions</th>
          </tr></thead>
          <tbody>{filtered.map((inv: any) => {
            const sc = STATUS_CONFIG[inv.status || inv.payment_status] || STATUS_CONFIG.draft;
            return (
              <tr key={inv.id} style={{ borderBottom: '1px solid #f0ede6' }}>
                <td style={{ padding: 8, fontFamily: 'monospace', fontSize: 11, fontWeight: 600 }}>{inv.invoice_number}</td>
                <td style={{ padding: 8, fontWeight: 500 }}>{inv.customer_name || inv.client_name || '—'}</td>
                <td style={{ padding: 8, fontWeight: 600 }}>${(inv.total || 0).toFixed(2)}</td>
                <td style={{ padding: 8, color: '#16a34a' }}>${(inv.amount_paid || inv.paid_amount || 0).toFixed(2)}</td>
                <td style={{ padding: 8, color: (inv.balance_due || 0) > 0 ? '#dc2626' : '#16a34a', fontWeight: 600 }}>
                  ${((inv.balance_due ?? inv.balance) ?? (inv.total || 0) - (inv.amount_paid || inv.paid_amount || 0)).toFixed(2)}
                </td>
                <td style={{ padding: 8 }}>
                  <span style={{ fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 8, background: sc.bg, color: sc.color }}>{sc.label}</span>
                </td>
                <td style={{ padding: 8, color: '#888', fontSize: 11 }}>{(inv.invoice_date || inv.created_at)?.slice(0, 10)}</td>
                <td style={{ padding: 8 }}>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <button title="Download PDF" style={{ padding: 4, background: '#f5f3ef', border: 'none', borderRadius: 4, cursor: 'pointer' }}
                      onClick={() => window.open(`${API}/finance/invoices/${inv.id}/pdf`, '_blank')}>
                      <Download size={12} />
                    </button>
                    <button title="Send to Client" style={{ padding: 4, background: '#f5f3ef', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
                      <Send size={12} />
                    </button>
                    <button title="Record Payment" style={{ padding: 4, background: '#f0fdf4', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
                      <CreditCard size={12} style={{ color: '#16a34a' }} />
                    </button>
                  </div>
                </td>
              </tr>
            );
          })}</tbody>
        </table>
      )}
    </div>
  );
}
