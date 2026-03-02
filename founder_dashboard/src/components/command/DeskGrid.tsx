'use client';
import { useEffect } from 'react';
import { DeskId, BUSINESS_DESKS } from '@/lib/deskData';
import { X, LayoutGrid } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSelectDesk: (id: DeskId) => void;
  activeDesk: DeskId | null;
}

export default function DeskGrid({ isOpen, onClose, onSelectDesk, activeDesk }: Props) {
  useEffect(() => {
    if (!isOpen) return;
    const handle = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handle);
    return () => window.removeEventListener('keydown', handle);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-8"
      style={{ background: 'rgba(5,5,13,0.88)', backdropFilter: 'blur(8px)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-5xl rounded-2xl overflow-hidden"
        style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-6 py-4"
          style={{ borderBottom: '1px solid var(--border)' }}
        >
          <div className="flex items-center gap-3">
            <LayoutGrid className="w-5 h-5" style={{ color: 'var(--gold)' }} />
            <h2 className="font-bold text-base text-gold-shimmer tracking-wide">AI DESKS</h2>
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              13 specialized workstations
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg transition"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--gold)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-secondary)')}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Grid */}
        <div className="p-6 grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-5 gap-3">
          {BUSINESS_DESKS.map((desk, i) => {
            const isActive = activeDesk === desk.id;
            return (
              <button
                key={desk.id}
                onClick={() => { onSelectDesk(desk.id); onClose(); }}
                className="desk-card-enter rounded-2xl p-4 flex flex-col items-center gap-2 transition-all text-center group"
                style={{
                  animationDelay: `${i * 30}ms`,
                  background: isActive ? `${desk.color}12` : 'var(--raised)',
                  border: `1px solid ${isActive ? desk.color : 'var(--border)'}`,
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = desk.color;
                  e.currentTarget.style.boxShadow = `0 0 20px ${desk.color}20`;
                  e.currentTarget.style.transform = 'translateY(-2px)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = isActive ? desk.color : 'var(--border)';
                  e.currentTarget.style.boxShadow = 'none';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}
              >
                <span className="text-3xl">{desk.icon}</span>
                <span className="text-xs font-semibold" style={{ color: desk.color }}>{desk.name}</span>
                <span className="text-[10px] leading-tight" style={{ color: 'var(--text-muted)' }}>
                  {desk.description}
                </span>
                <span
                  className="text-[9px] font-mono px-1.5 py-0.5 rounded mt-auto"
                  style={{ background: 'var(--elevated)', color: 'var(--text-muted)' }}
                >
                  {desk.shortcut}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
