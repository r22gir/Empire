'use client';
import { DataTable, StatusBadge, type Column } from '../shared';
import { type Invoice } from '@/lib/deskData';

const INVOICE_COLORS: Record<string, string> = {
  paid: '#22c55e', pending: '#f59e0b', overdue: '#ef4444',
};

const fmt = (n: number) => '$' + n.toLocaleString();

interface InvoiceTableProps {
  invoices: Invoice[];
  onInvoiceClick?: (invoice: Invoice) => void;
  selectedInvoiceId?: string;
}

export default function InvoiceTable({ invoices, onInvoiceClick, selectedInvoiceId }: InvoiceTableProps) {
  const columns: Column<Invoice>[] = [
    { key: 'id', label: 'Invoice', render: inv => <span className="font-mono" style={{ color: 'var(--text-muted)' }}>{inv.id.toUpperCase()}</span> },
    { key: 'client', label: 'Client' },
    { key: 'amount', label: 'Amount', render: inv => <span className="font-mono font-semibold" style={{ color: 'var(--gold)' }}>{fmt(inv.amount)}</span> },
    { key: 'status', label: 'Status', render: inv => <StatusBadge label={inv.status} color={INVOICE_COLORS[inv.status]} /> },
    { key: 'dueDate', label: 'Due Date', render: inv => <span className="font-mono" style={{ color: 'var(--text-muted)' }}>{inv.dueDate}</span> },
  ];

  return <DataTable columns={columns} data={invoices} getRowId={inv => inv.id} onRowClick={onInvoiceClick} selectedId={selectedInvoiceId} />;
}
