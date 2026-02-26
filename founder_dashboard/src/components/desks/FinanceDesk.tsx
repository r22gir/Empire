'use client';
import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { MOCK_FINANCE, MOCK_TRANSACTIONS, MOCK_INVOICES, Invoice, Transaction } from '@/lib/deskData';
import { DollarSign, TrendingUp, FileText, PieChart } from 'lucide-react';
import { StatsBar, FilterTabs, TaskList, DetailPanel } from './shared';
import RevenueTrend from './finance/RevenueTrend';
import TransactionList from './finance/TransactionList';
import InvoiceTable from './finance/InvoiceTable';
import InvoiceDetail from './finance/InvoiceDetail';
import TransactionDetail from './finance/TransactionDetail';

const fmt = (n: number) => '$' + n.toLocaleString();

export default function FinanceDesk() {
  const [tab, setTab] = useState('overview');
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [selectedTransaction, setSelectedTransaction] = useState<Transaction | null>(null);
  const router = useRouter();
  const fin = MOCK_FINANCE;

  const handleClientClick = useCallback((clientName: string) => {
    router.push(`/desk/clients?filter=${encodeURIComponent(clientName)}`);
  }, [router]);

  const closePanel = useCallback(() => {
    setSelectedInvoice(null);
    setSelectedTransaction(null);
  }, []);

  const panelOpen = !!selectedInvoice || !!selectedTransaction;
  const panelTitle = selectedInvoice
    ? `Invoice ${selectedInvoice.id.toUpperCase()}`
    : selectedTransaction
      ? selectedTransaction.description
      : '';

  return (
    <div className="flex flex-col h-full">
      <div className="grid grid-cols-5 gap-3 p-4 shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
        {[
          { label: 'Revenue MTD', value: fmt(fin.revenueMTD), icon: DollarSign, color: 'var(--gold)' },
          { label: 'Revenue YTD', value: fmt(fin.revenueYTD), icon: TrendingUp, color: '#22c55e' },
          { label: 'Expenses MTD', value: fmt(fin.expensesMTD), icon: FileText, color: '#ef4444' },
          { label: 'Outstanding', value: fmt(fin.outstandingInvoices), icon: FileText, color: '#f59e0b' },
          { label: 'Profit Margin', value: (fin.profitMargin * 100).toFixed(1) + '%', icon: PieChart, color: 'var(--purple)' },
        ].map(c => (
          <div key={c.label} className="rounded-xl p-3" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <div className="flex items-center gap-2 mb-2">
              <c.icon className="w-4 h-4" style={{ color: c.color }} />
              <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>{c.label}</span>
            </div>
            <p className="text-lg font-bold" style={{ color: c.color }}>{c.value}</p>
          </div>
        ))}
      </div>

      <FilterTabs options={['overview', 'invoices', 'tasks']} active={tab} onChange={setTab} />

      <div className="flex-1 overflow-auto p-4">
        {tab === 'overview' && (
          <div className="grid grid-cols-2 gap-4 h-full">
            <RevenueTrend />
            <TransactionList transactions={MOCK_TRANSACTIONS} onTransactionClick={t => { setSelectedTransaction(t); setSelectedInvoice(null); }} />
          </div>
        )}
        {tab === 'invoices' && <InvoiceTable invoices={MOCK_INVOICES} onInvoiceClick={inv => { setSelectedInvoice(inv); setSelectedTransaction(null); }} selectedInvoiceId={selectedInvoice?.id} />}
        {tab === 'tasks' && <TaskList desk="finance" />}
      </div>

      <DetailPanel open={panelOpen} onClose={closePanel} title={panelTitle}>
        {selectedInvoice && <InvoiceDetail invoice={selectedInvoice} onClientClick={handleClientClick} />}
        {selectedTransaction && <TransactionDetail transaction={selectedTransaction} />}
      </DetailPanel>
    </div>
  );
}
