'use client';
import { type Transaction } from '@/lib/deskData';
import { Calendar, Tag, FileText, Link2, StickyNote } from 'lucide-react';

const fmt = (n: number) => '$' + n.toLocaleString();

interface TransactionDetailProps {
  transaction: Transaction;
}

export default function TransactionDetail({ transaction }: TransactionDetailProps) {
  const isIncome = transaction.type === 'income';
  const typeColor = isIncome ? '#22c55e' : '#ef4444';

  return (
    <div className="space-y-5">
      {/* Amount header */}
      <div className="text-center py-3">
        <span className="text-2xl font-bold font-mono" style={{ color: typeColor }}>
          {isIncome ? '+' : '\u2212'}{fmt(transaction.amount)}
        </span>
        <div className="mt-1">
          <span
            className="text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase"
            style={{ background: `${typeColor}18`, color: typeColor }}
          >
            {transaction.type}
          </span>
        </div>
      </div>

      {/* Details */}
      <div className="space-y-3">
        <InfoRow icon={FileText} label="Description">{transaction.description}</InfoRow>
        <InfoRow icon={Calendar} label="Date">{transaction.date}</InfoRow>
        <InfoRow icon={Tag} label="Category">{transaction.category}</InfoRow>
        <InfoRow icon={Link2} label="Related Job">
          {transaction.relatedJob ? (
            <span className="font-mono" style={{ color: 'var(--purple)' }}>{transaction.relatedJob}</span>
          ) : (
            <span style={{ color: 'var(--text-muted)' }}>None</span>
          )}
        </InfoRow>
        <InfoRow icon={FileText} label="Receipt">
          <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>{transaction.receipt}</span>
        </InfoRow>
      </div>

      {/* Notes */}
      {transaction.notes && (
        <div className="rounded-lg p-3" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
          <div className="flex items-center gap-1.5 mb-1.5">
            <StickyNote className="w-3 h-3" style={{ color: 'var(--gold)' }} />
            <span className="text-[10px] font-semibold" style={{ color: 'var(--gold)' }}>Notes</span>
          </div>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{transaction.notes}</p>
        </div>
      )}

      {/* Actions */}
      <div className="grid grid-cols-2 gap-2 pt-2">
        <ActionBtn label="View Receipt" />
        <ActionBtn label="Edit Category" />
      </div>
    </div>
  );
}

function InfoRow({ icon: Icon, label, children }: { icon: typeof Calendar; label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3">
      <Icon className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
      <span className="text-[10px] w-20 shrink-0" style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span className="text-xs" style={{ color: 'var(--text-primary)' }}>{children}</span>
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
