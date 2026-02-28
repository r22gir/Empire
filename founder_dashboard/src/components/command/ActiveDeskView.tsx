'use client';
import { DeskId, BUSINESS_DESKS } from '@/lib/deskData';
import { DESK_COMPONENTS } from './deskComponentMap';
import DeskChat from '../desks/DeskChat';
import { ArrowLeft } from 'lucide-react';

interface Props {
  activeDesk: DeskId;
  onClose: () => void;
}

export default function ActiveDeskView({ activeDesk, onClose }: Props) {
  const DeskComponent = DESK_COMPONENTS[activeDesk];
  const deskDef = BUSINESS_DESKS.find(d => d.id === activeDesk);

  return (
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
          <span className="text-xl">{deskDef?.icon}</span>
          <div>
            <span className="font-bold text-sm text-gold-shimmer tracking-wide">
              {deskDef?.name} Desk
            </span>
            <span className="text-xs ml-2 font-light" style={{ color: 'var(--text-muted)' }}>
              {deskDef?.description}
            </span>
          </div>
        </div>
        <button
          onClick={onClose}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition"
          style={{ background: 'var(--raised)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--elevated)'; e.currentTarget.style.color = 'var(--gold)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'var(--raised)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
        >
          <ArrowLeft className="w-3 h-3" />
          Command Center
        </button>
      </div>

      {/* Desk content + chat */}
      <div className="flex-1 flex min-h-0">
        <div className="flex-1 min-h-0 relative overflow-hidden">
          <DeskComponent />
        </div>
        <DeskChat deskId={activeDesk} />
      </div>
    </div>
  );
}
