'use client';
import { use } from 'react';
import { notFound } from 'next/navigation';
import { DeskId, BUSINESS_DESKS } from '@/lib/deskData';
import DeskNav from '@/components/desks/DeskNav';
import OperationsDesk from '@/components/desks/OperationsDesk';
import FinanceDesk from '@/components/desks/FinanceDesk';
import SalesDesk from '@/components/desks/SalesDesk';
import DesignDesk from '@/components/desks/DesignDesk';
import EstimatingDesk from '@/components/desks/EstimatingDesk';
import ClientsDesk from '@/components/desks/ClientsDesk';
import ContractorsDesk from '@/components/desks/ContractorsDesk';
import SupportDesk from '@/components/desks/SupportDesk';
import MarketingDesk from '@/components/desks/MarketingDesk';
import WebsiteDesk from '@/components/desks/WebsiteDesk';
import ITDesk from '@/components/desks/ITDesk';
import LegalDesk from '@/components/desks/LegalDesk';
import LabDesk from '@/components/desks/LabDesk';
import DeskChat from '@/components/desks/DeskChat';

const DESK_COMPONENTS: Record<DeskId, React.ComponentType> = {
  operations:  OperationsDesk,
  finance:     FinanceDesk,
  sales:       SalesDesk,
  design:      DesignDesk,
  estimating:  EstimatingDesk,
  clients:     ClientsDesk,
  contractors: ContractorsDesk,
  support:     SupportDesk,
  marketing:   MarketingDesk,
  website:     WebsiteDesk,
  it:          ITDesk,
  legal:       LegalDesk,
  lab:         LabDesk,
};

export default function DeskPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const deskId = id as DeskId;
  const deskDef = BUSINESS_DESKS.find(d => d.id === deskId);
  const DeskComponent = DESK_COMPONENTS[deskId];

  if (!deskDef || !DeskComponent) {
    notFound();
  }

  return (
    <div
      className="h-screen flex overflow-hidden empire-ambient"
      style={{ background: 'var(--void)', color: 'var(--text-primary)' }}
    >
      <DeskNav />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Desk header */}
        <div
          className="flex items-center justify-between px-5 shrink-0"
          style={{
            background: 'rgba(5,5,13,0.85)',
            borderBottom: '1px solid var(--border)',
            backdropFilter: 'blur(20px)',
            minHeight: '52px',
          }}
        >
          <div className="flex items-center gap-3">
            <span className="text-xl">{deskDef.icon}</span>
            <div>
              <span className="font-bold text-sm text-gold-shimmer tracking-wide">
                {deskDef.name} Desk
              </span>
              <span className="text-xs ml-2 font-light" style={{ color: 'var(--text-muted)' }}>
                {deskDef.description}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono px-2 py-0.5 rounded" style={{ background: 'var(--raised)', color: 'var(--text-muted)' }}>
              {deskDef.shortcut}
            </span>
          </div>
        </div>

        {/* Desk content + chat */}
        <div className="flex-1 flex min-h-0">
          <div className="flex-1 min-h-0">
            <DeskComponent />
          </div>
          <DeskChat deskId={deskId} />
        </div>
      </div>
    </div>
  );
}
