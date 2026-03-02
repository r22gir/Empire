'use client';
import { type Invoice } from '@/lib/deskData';
import { Calendar, User, FileText, DollarSign } from 'lucide-react';
import { StatusBadge } from '../shared';

const STATUS_COLOR: Record<string, string> = {
  paid: '#22c55e', pending: '#f59e0b', overdue: '#ef4444',
};

const fmt = (n: number) => '$' + n.toLocaleString();

interface InvoiceDetailProps {
  invoice: Invoice;
  onClientClick?: (clientName: string) => void;
}

export default function InvoiceDetail({ invoice, onClientClick }: InvoiceDetailProps) {
  return (
    <div className="space-y-5">
      {/* Header info */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs" style={{ color: 'var(--text-muted)' }}>{invoice.id.toUpperCase()}</span>
          <StatusBadge label={invoice.status} color={STATUS_COLOR[invoice.status]} />
        </div>
        <span className="text-lg font-bold font-mono" style={{ color: 'var(--gold)' }}>{fmt(invoice.amount)}</span>
      </div>

      {/* Client + dates */}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <User className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
          <span className="text-[10px] w-16 shrink-0" style={{ color: 'var(--text-muted)' }}>Client</span>
          <button
            onClick={() => onClientClick?.(invoice.client)}
            className="text-xs font-semibold transition"
            style={{ color: 'var(--gold)', cursor: 'pointer' }}
            onMouseEnter={e => (e.currentTarget.style.textDecoration = 'underline')}
            onMouseLeave={e => (e.currentTarget.style.textDecoration = 'none')}
          >
            {invoice.client}
          </button>
        </div>
        <div className="flex items-center gap-3">
          <Calendar className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
          <span className="text-[10px] w-16 shrink-0" style={{ color: 'var(--text-muted)' }}>Due Date</span>
          <span className="text-xs font-mono" style={{ color: invoice.status === 'overdue' ? '#ef4444' : 'var(--text-primary)' }}>{invoice.dueDate}</span>
        </div>
        {invoice.paidDate && (
          <div className="flex items-center gap-3">
            <DollarSign className="w-3.5 h-3.5 shrink-0" style={{ color: '#22c55e' }} />
            <span className="text-[10px] w-16 shrink-0" style={{ color: 'var(--text-muted)' }}>Paid</span>
            <span className="text-xs font-mono" style={{ color: '#22c55e' }}>{invoice.paidDate}</span>
          </div>
        )}
      </div>

      {/* Line items table */}
      <div>
        <p className="text-[10px] uppercase tracking-wider mb-2" style={{ color: 'var(--text-muted)' }}>Line Items</p>
        <div className="rounded-lg overflow-hidden" style={{ border: '1px solid var(--border)' }}>
          <table className="w-full text-[11px]">
            <thead>
              <tr style={{ background: 'var(--elevated)' }}>
                <th className="text-left px-2.5 py-2 font-semibold" style={{ color: 'var(--gold)' }}>Description</th>
                <th className="text-right px-2.5 py-2 font-semibold w-10" style={{ color: 'var(--gold)' }}>Qty</th>
                <th className="text-right px-2.5 py-2 font-semibold w-16" style={{ color: 'var(--gold)' }}>Rate</th>
                <th className="text-right px-2.5 py-2 font-semibold w-16" style={{ color: 'var(--gold)' }}>Amount</th>
              </tr>
            </thead>
            <tbody>
              {invoice.lineItems.map((item, i) => (
                <tr key={i} style={{ borderTop: '1px solid var(--border)' }}>
                  <td className="px-2.5 py-1.5" style={{ color: 'var(--text-primary)' }}>{item.description}</td>
                  <td className="text-right px-2.5 py-1.5 font-mono" style={{ color: 'var(--text-secondary)' }}>{item.qty}</td>
                  <td className="text-right px-2.5 py-1.5 font-mono" style={{ color: 'var(--text-secondary)' }}>{fmt(item.rate)}</td>
                  <td className="text-right px-2.5 py-1.5 font-mono font-semibold" style={{ color: 'var(--text-primary)' }}>{fmt(item.amount)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr style={{ borderTop: '1px solid var(--border-strong)' }}>
                <td colSpan={3} className="text-right px-2.5 py-2 font-semibold" style={{ color: 'var(--gold)' }}>Total</td>
                <td className="text-right px-2.5 py-2 font-mono font-bold" style={{ color: 'var(--gold)' }}>{fmt(invoice.amount)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Notes */}
      {invoice.notes && (
        <div className="rounded-lg p-3" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
          <div className="flex items-center gap-1.5 mb-1.5">
            <FileText className="w-3 h-3" style={{ color: 'var(--gold)' }} />
            <span className="text-[10px] font-semibold" style={{ color: 'var(--gold)' }}>Notes</span>
          </div>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{invoice.notes}</p>
        </div>
      )}

      {/* Actions */}
      <div className="grid grid-cols-2 gap-2 pt-2">
        {invoice.status !== 'paid' && (
          <>
            <ActionBtn label="Send Reminder" />
            <ActionBtn label="Mark Paid" />
          </>
        )}
        <ActionBtn label="Download PDF" />
        <ActionBtn label="View Client" />
      </div>
    </div>
  );
}

function ActionBtn({ label }: { label: string }) {
  return (
    <button
      className="text-xs font-medium py-2 px-3 rounded-lg transition"
      style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold-border)'; e.currentTarget.style.color = 'var(--gold)'; }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
    >
      {label}
    </button>
  );
}
