'use client';
import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { DeskId, BUSINESS_DESKS } from '@/lib/deskData';
import {
  ClipboardList, DollarSign, TrendingUp, Palette, Calculator,
  Users, Wrench, Headphones, Megaphone, Globe, Server, Scale, FlaskConical,
} from 'lucide-react';

const LUCIDE_MAP: Record<string, React.ComponentType<{ className?: string; style?: React.CSSProperties }>> = {
  ClipboardList, DollarSign, TrendingUp, Palette, Calculator,
  Users, Wrench, Headphones, Megaphone, Globe, Server, Scale, FlaskConical,
};

export default function DeskNav() {
  const router = useRouter();
  const pathname = usePathname();

  const activeDeskId = pathname?.startsWith('/desk/')
    ? pathname.split('/')[2] as DeskId
    : null;

  /* ── Keyboard shortcuts ── */
  useEffect(() => {
    const handle = (e: KeyboardEvent) => {
      // Skip if user is typing in an input
      if ((e.target as HTMLElement).tagName === 'INPUT' || (e.target as HTMLElement).tagName === 'TEXTAREA') return;

      const altMap: Record<string, DeskId> = {
        '1': 'operations', '2': 'finance', '3': 'sales', '4': 'design',
        '5': 'estimating', '6': 'clients', '7': 'contractors', '8': 'support',
        '9': 'marketing', '0': 'website',
      };
      const ctrlAltMap: Record<string, DeskId> = {
        '1': 'it', '2': 'legal', '3': 'lab',
      };

      if (e.altKey && !e.ctrlKey && altMap[e.key]) {
        e.preventDefault();
        router.push('/desk/' + altMap[e.key]);
      } else if (e.altKey && e.ctrlKey && ctrlAltMap[e.key]) {
        e.preventDefault();
        router.push('/desk/' + ctrlAltMap[e.key]);
      }
    };
    window.addEventListener('keydown', handle);
    return () => window.removeEventListener('keydown', handle);
  }, [router]);

  return (
    <div
      className="w-[54px] flex flex-col items-center py-2 gap-0.5 shrink-0 overflow-y-auto"
      style={{
        background: 'var(--void)',
        borderRight: '1px solid var(--border)',
      }}
    >
      {/* Home button */}
      <button
        onClick={() => router.push('/')}
        className="w-10 h-9 flex items-center justify-center rounded-lg mb-1 transition-all group relative"
        style={{
          background: !activeDeskId ? 'var(--gold-pale)' : 'transparent',
          borderLeft: !activeDeskId ? '2px solid var(--gold)' : '2px solid transparent',
        }}
        onMouseEnter={e => { if (activeDeskId) e.currentTarget.style.background = 'var(--hover)'; }}
        onMouseLeave={e => { if (activeDeskId) e.currentTarget.style.background = 'transparent'; }}
      >
        <span className="text-sm">🏠</span>
        <span
          className="absolute left-full ml-2 px-2 py-1 rounded-md text-[10px] font-medium whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50"
          style={{ background: 'var(--elevated)', color: 'var(--text-primary)', border: '1px solid var(--border)' }}
        >
          MAX Chat
        </span>
      </button>

      <div className="w-6 mx-auto my-1" style={{ borderTop: '1px solid var(--border)' }} />

      {BUSINESS_DESKS.map(desk => {
        const isActive = activeDeskId === desk.id;
        const Icon = LUCIDE_MAP[desk.lucideIcon];

        return (
          <button
            key={desk.id}
            onClick={() => {
              if (isActive) router.push('/');
              else router.push('/desk/' + desk.id);
            }}
            className="w-10 h-9 flex items-center justify-center rounded-lg transition-all group relative"
            style={{
              background: isActive ? `${desk.color}15` : 'transparent',
              borderLeft: isActive ? `2px solid ${desk.color}` : '2px solid transparent',
            }}
            onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = 'var(--hover)'; }}
            onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
          >
            {Icon ? (
              <Icon
                className="w-4 h-4"
                style={{ color: isActive ? desk.color : 'var(--text-secondary)' }}
              />
            ) : (
              <span className="text-sm">{desk.icon}</span>
            )}

            {/* Tooltip */}
            <span
              className="absolute left-full ml-2 px-2 py-1 rounded-md text-[10px] font-medium whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50"
              style={{ background: 'var(--elevated)', color: 'var(--text-primary)', border: '1px solid var(--border)' }}
            >
              {desk.name}
              <span className="ml-1.5 font-mono" style={{ color: 'var(--text-muted)' }}>
                {desk.shortcut}
              </span>
            </span>

            {/* Active dot */}
            {isActive && (
              <span
                className="absolute right-0.5 top-1/2 -translate-y-1/2 w-1 h-1 rounded-full"
                style={{ background: desk.color }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
