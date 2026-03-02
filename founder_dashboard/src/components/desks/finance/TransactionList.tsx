'use client';
import { type Transaction } from '@/lib/deskData';

const fmt = (n: number) => '$' + n.toLocaleString();

interface TransactionListProps {
  transactions: Transaction[];
  onTransactionClick?: (transaction: Transaction) => void;
}

export default function TransactionList({ transactions, onTransactionClick }: TransactionListProps) {
  return (
    <div className="rounded-xl flex flex-col" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      <p className="text-xs font-semibold px-4 pt-3 pb-2" style={{ color: 'var(--gold)' }}>Recent Transactions</p>
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {transactions.map(t => (
          <div
            key={t.id}
            className="flex items-center gap-3 px-2 py-2 rounded-lg transition cursor-pointer"
            onClick={() => onTransactionClick?.(t)}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--hover)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            <span
              className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold shrink-0"
              style={{
                background: t.type === 'income' ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                color: t.type === 'income' ? '#22c55e' : '#ef4444',
              }}
            >
              {t.type === 'income' ? '+' : '\u2212'}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-xs truncate" style={{ color: 'var(--text-primary)' }}>{t.description}</p>
              <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{t.date} · {t.category}</p>
            </div>
            <span
              className="text-xs font-mono font-semibold shrink-0"
              style={{ color: t.type === 'income' ? '#22c55e' : '#ef4444' }}
            >
              {t.type === 'income' ? '+' : '\u2212'}{fmt(t.amount)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
