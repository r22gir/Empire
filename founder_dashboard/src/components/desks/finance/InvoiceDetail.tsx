'use client';
import { type Invoice } from '@/lib/deskData';
import { Calendar, User, FileText, DollarSign, Download } from 'lucide-react';
import { StatusBadge } from '../shared';

const STATUS_COLOR: Record<string, string> = {
  paid: '#22c55e', pending: '#f59e0b', overdue: '#ef4444',
};

const fmt = (n: number) => '$' + n.toLocaleString();

function downloadInvoicePdf(inv: Invoice) {
  const rows = inv.lineItems.map(item =>
    `<tr><td style="padding:8px;border-bottom:1px solid #eee">${item.description}</td>
     <td style="padding:8px;border-bottom:1px solid #eee;text-align:center">${item.qty}</td>
     <td style="padding:8px;border-bottom:1px solid #eee;text-align:right">${fmt(item.rate)}</td>
     <td style="padding:8px;border-bottom:1px solid #eee;text-align:right;font-weight:600">${fmt(item.amount)}</td></tr>`
  ).join('');

  const statusColor = STATUS_COLOR[inv.status] || '#666';
  const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Invoice ${inv.id.toUpperCase()}</title>
<style>@page{size:letter;margin:0.6in}body{font-family:'Helvetica Neue',Arial,sans-serif;color:#222;max-width:750px;margin:0 auto;font-size:13px;line-height:1.5}
table{width:100%;border-collapse:collapse}th{background:#1a1a2e;color:#D4AF37;padding:8px;text-align:left;font-size:0.8em;text-transform:uppercase;letter-spacing:0.5px}</style></head><body>
<div style="border-bottom:3px solid #D4AF37;padding-bottom:14px;margin-bottom:20px;display:flex;justify-content:space-between;align-items:flex-start">
  <div><h1 style="margin:0;font-size:28px;color:#1a1a2e">Empire</h1><p style="margin:4px 0 0;color:#888;font-size:0.85em">Custom Window Treatments & Upholstery</p></div>
  <div style="text-align:right"><div style="background:#1a1a2e;color:#D4AF37;padding:8px 16px;border-radius:6px;font-weight:700;font-size:1.1em;display:inline-block;margin-bottom:8px">INVOICE</div>
  <p style="margin:3px 0;font-weight:600">${inv.id.toUpperCase()}</p>
  <p style="margin:3px 0;color:#666;font-size:0.85em">Due: ${inv.dueDate}</p>
  ${inv.paidDate ? `<p style="margin:3px 0;color:#22c55e;font-size:0.85em;font-weight:600">Paid: ${inv.paidDate}</p>` : ''}
  <p style="margin:3px 0"><span style="display:inline-block;padding:2px 10px;border-radius:4px;font-size:0.8em;font-weight:600;color:white;background:${statusColor}">${inv.status.toUpperCase()}</span></p>
  </div></div>
<div style="padding:14px 18px;background:#f8f8f8;border-radius:8px;border:1px solid #eee;margin-bottom:20px">
  <p style="margin:0 0 4px;font-size:0.75em;text-transform:uppercase;letter-spacing:0.5px;color:#999;font-weight:600">Bill To</p>
  <p style="margin:0;font-weight:700;font-size:1.05em;color:#1a1a2e">${inv.client}</p>
</div>
<table><thead><tr><th>Description</th><th style="text-align:center;width:60px">Qty</th><th style="text-align:right;width:80px">Rate</th><th style="text-align:right;width:90px">Amount</th></tr></thead>
<tbody>${rows}</tbody>
<tfoot><tr><td colspan="3" style="padding:12px 8px;text-align:right;border-top:3px solid #D4AF37"><strong style="font-size:1.1em;color:#1a1a2e">Total</strong></td>
<td style="padding:12px 8px;text-align:right;border-top:3px solid #D4AF37"><strong style="font-size:1.2em;color:#D4AF37">${fmt(inv.amount)}</strong></td></tr></tfoot></table>
${inv.notes ? `<div style="margin-top:20px;padding:12px 16px;background:#fafafa;border-radius:8px;border:1px solid #eee"><strong>Notes:</strong> ${inv.notes}</div>` : ''}
<div style="margin-top:40px;padding-top:12px;border-top:1px solid #eee;text-align:center;color:#aaa;font-size:0.72em">Empire &middot; Custom Window Treatments & Upholstery</div>
</body></html>`;

  const w = window.open('', '_blank');
  if (w) {
    w.document.write(html);
    w.document.close();
    setTimeout(() => w.print(), 300);
  }
}

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
        <ActionBtn label="Download PDF" icon={<Download className="w-3 h-3" />} onClick={() => downloadInvoicePdf(invoice)} />
        <ActionBtn label="View Client" onClick={() => onClientClick?.(invoice.client)} />
      </div>
    </div>
  );
}

function ActionBtn({ label, icon, onClick }: { label: string; icon?: React.ReactNode; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      className="text-xs font-medium py-2 px-3 rounded-lg transition flex items-center justify-center gap-1.5"
      style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold-border)'; e.currentTarget.style.color = 'var(--gold)'; }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
    >
      {icon}{label}
    </button>
  );
}
