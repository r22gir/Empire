'use client';
import { EXAMPLE_MARK, useExampleMode } from './exampleData';
import { useStudioMoney } from './useStudioMoney';

export default function MoneyHome({ onOpen }: { onOpen: (href: string) => void }) {
  const example = useExampleMode();
  const { figures: money } = useStudioMoney();

  return (
    <section data-testid="studio-money" aria-label="Money">
      <header style={{ marginBottom: 16 }}>
        <h1 className="v3-disp" style={{ fontSize: 28, margin: 0 }}>Money</h1>
        <p className="studio-ex" style={{ marginTop: 6 }}>EmpirePay · invoices · deposits{example ? ` · ${EXAMPLE_MARK}` : ''}</p>
      </header>
      <article className="studio-card">
        <div className="studio-money">
          <div><label>To collect</label><b data-testid="studio-money-collect">{money.toCollect}</b></div>
          <div><label>Deposits due</label><b data-testid="studio-money-deposits">{money.depositsDue}</b></div>
          <div><label>Paid MTD</label><b data-testid="studio-money-paid">{money.paidMtd}</b></div>
        </div>
      </article>
      <div className="studio-cards" style={{ marginTop: 14 }}>
        {[
          { label: 'EmpirePay', href: '/?product=pay', hint: 'Pay links, deposits, collected' },
          { label: 'Invoices', href: '/?screen=invoices', hint: 'A/R, overdue, drafts' },
          { label: 'Workroom finance', href: '/?product=workroom&section=finance', hint: 'Finance · expenses · payments' },
        ].map((row) => (
          <button key={row.label} type="button" className="studio-row" onClick={() => onOpen(row.href)} style={{ background: 'var(--st-card)', border: '1px solid var(--st-line)', borderRadius: 16, padding: '14px 16px' }}>
            <span style={{ flex: 1 }}>
              <b>{row.label}</b>
              <span style={{ display: 'block' }}>{row.hint}</span>
            </span>
            <span>›</span>
          </button>
        ))}
      </div>
    </section>
  );
}
