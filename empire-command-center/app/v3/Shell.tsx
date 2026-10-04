'use client';
// v3 shell pieces shared by the Max home and the Command Center pages:
// top band, launcher rail, businesses sheet (every module), phone tab bar.
import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import {
  Scissors, TreePine, Building2, Cpu, Target, Share2, Megaphone, DollarSign, MessageSquare, FileText, Activity, LayoutGrid,
  Bell, Layers, TrendingUp, CalendarDays, X,
} from 'lucide-react';
import { Orb } from './ui';
import { EDITION, SYSTEM_ITEM } from './edition';
import type { RailItem, RailKey } from './edition';
import ThemeToggle from '../components/ThemeToggle';

const RAIL_ICON: Record<RailKey, ReactNode> = {
  max: null, workroom: <Scissors size={16} strokeWidth={1.5} />, craft: <TreePine size={16} strokeWidth={1.5} />, construction: <Building2 size={16} strokeWidth={1.5} />,
  amp: <Cpu size={16} strokeWidth={1.5} />, lead: <Target size={16} strokeWidth={1.5} />, social: <Share2 size={16} strokeWidth={1.5} />, market: <Megaphone size={16} strokeWidth={1.5} />,
  finance: <DollarSign size={16} strokeWidth={1.5} />, comms: <MessageSquare size={16} strokeWidth={1.5} />, docs: <FileText size={16} strokeWidth={1.5} />, system: <Activity size={16} strokeWidth={1.5} />,
};

export function useClock(): Date | null {
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => { setNow(new Date()); const t = setInterval(() => setNow(new Date()), 30_000); return () => clearInterval(t); }, []);
  return now;
}

export function BandLogo({ href = '/' }: { href?: string }) {
  return (
    <>
      <a href={href} className="logo" aria-label="Empire home"><span className="v3-mono-e">E</span></a>
      <a href={href} className="v3-wm">EMPIRE</a>
    </>
  );
}

export function BandDate() {
  const now = useClock();
  if (!now) return <span className="d" />;
  const d = now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  const t = now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  return <span className="d"><b>{d}</b> · {t} ET</span>;
}

export function MaxPill({ href = '/?product=owner' }: { href?: string }) {
  return (
    <a href={href} className="v3-maxpill" title={`Open ${EDITION.assistantName} chat`} aria-label={`Open ${EDITION.assistantName} chat`}>
      <span className="em"><Orb size={30} /></span><span className="lbl">{EDITION.assistantName}</span>
    </a>
  );
}

export interface BandTab { key: string; label: string; href?: string; onClick?: () => void }

/** Fixed top band for full-page v3 screens (the Max home). */
export function V3Band({ tabs, active, notifications }: { tabs: BandTab[]; active: string; notifications?: number }) {
  return (
    <header className="v3-band">
      <BandLogo />
      <nav className="v3-tabs" aria-label="Sections">
        {tabs.map(t => t.href
          ? <a key={t.key} href={t.href} className={active === t.key ? 'on' : ''} aria-current={active === t.key ? 'page' : undefined}>{t.label}</a>
          : <button key={t.key} type="button" onClick={t.onClick} className={active === t.key ? 'on' : ''}>{t.label}</button>)}
      </nav>
      <div className="br">
        <BandDate />
        <ThemeToggle />
        <a href="/?screen=inbox" className="icon-btn" aria-label={`Notifications${notifications ? `: ${notifications} unread` : ''}`} title="Notifications">
          <Bell size={17} strokeWidth={1.5} />{notifications ? <span className="badge">{notifications > 9 ? '9+' : notifications}</span> : null}
        </a>
        <MaxPill />
        <span className="v3-av" aria-label={EDITION.ownerName}>{EDITION.ownerInitials}</span>
      </div>
    </header>
  );
}

/** Left launcher rail. In the Command Center, onGo keeps navigation in-app; on full pages the links navigate. */
export function V3Rail({ active, onGo, onAll, badges = {}, className = '' }: {
  active?: RailKey | string | null; onGo?: (item: RailItem) => void; onAll: () => void; badges?: Partial<Record<RailKey, boolean>>; className?: string;
}) {
  const go = (it: RailItem) => (e: React.MouseEvent) => { if (onGo) { e.preventDefault(); onGo(it); } };
  const Ri = ({ it, icon }: { it: RailItem; icon: ReactNode }) => (
    <a href={it.href} onClick={go(it)} className={`v3-ri${active === it.key ? ' on' : ''}`} title={it.hint} aria-current={active === it.key ? 'page' : undefined}>
      <span className="g">{icon}</span><span>{it.label}</span>{badges[it.key] ? <b aria-label="needs attention" /> : null}
    </a>
  );
  return (
    <nav className={`v3-rail ${className}`} aria-label="Modules">
      <a href="/" className={`v3-ri${active === 'max' ? ' on' : ''}`} title={`${EDITION.assistantName} home`} aria-current={active === 'max' ? 'page' : undefined}>
        <span className="g"><Orb size={24} /></span><span>{EDITION.assistantName}</span>
      </a>
      <div className="v3-rsep" /><div className="v3-rlab">FORGES</div>
      {EDITION.rail.map(it => <Ri key={it.key} it={it} icon={RAIL_ICON[it.key]} />)}
      <button type="button" className="v3-ri" onClick={onAll} title="All modules"><span className="g"><LayoutGrid size={16} strokeWidth={1.5} /></span><span>All</span></button>
      <div className="grow"><Ri it={SYSTEM_ITEM} icon={RAIL_ICON.system} /></div>
    </nav>
  );
}

export interface SheetModule { id: string; name: string; icon: ReactNode; status?: string; href: string; onPick?: () => void; on?: boolean }
export interface SheetGroup { key: string; label: string; items: SheetModule[] }

/** Every module, one click away (the rail only shows the main forges). */
export function BusinessesSheet({ open, onClose, groups }: { open: boolean; onClose: () => void; groups: SheetGroup[] }) {
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <>
      <div className="v3-sheet-back" onClick={onClose} />
      <div className="v3-sheet" role="dialog" aria-modal="true" aria-label="All businesses and modules">
        <div className="hd"><h2 className="v3-disp">Businesses</h2><span className="v3-kick">All modules</span>
          <button type="button" className="v3-ib" style={{ marginLeft: 'auto' }} onClick={onClose} aria-label="Close"><X size={14} /></button></div>
        {groups.map(g => (
          <div key={g.key} className="grp">
            <div className="v3-kick">{g.label}</div>
            <div className="grid">
              {g.items.map(m => (
                <a key={m.id} href={m.href} className={`v3-mod${m.on ? ' on' : ''}`} onClick={e => { if (m.onPick) { e.preventDefault(); m.onPick(); onClose(); } }}>
                  <span className="gl">{m.icon}</span><span className="nm">{m.name}</span>
                  {m.status && m.status !== 'active' ? <span className="st">{m.status === 'planned' ? 'soon' : m.status}</span> : null}
                </a>
              ))}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

/** Phone tab bar for the Max home. */
export function V3TabBar({ active, onPick, todayBadge }: { active: string; onPick: (k: string) => void; todayBadge?: number }) {
  const tabs: { k: string; label: string; icon: ReactNode }[] = [
    { k: 'max', label: EDITION.assistantName, icon: <Orb size={24} /> },
    { k: 'research', label: 'Research', icon: <Layers size={21} strokeWidth={1.5} /> },
    { k: 'growth', label: 'Growth', icon: <TrendingUp size={21} strokeWidth={1.5} /> },
    { k: 'today', label: 'Today', icon: <CalendarDays size={21} strokeWidth={1.5} /> },
    { k: 'businesses', label: 'Businesses', icon: <LayoutGrid size={21} strokeWidth={1.5} /> },
  ];
  return (
    <nav className="v3-tabbar" aria-label="Home sections">
      {tabs.map(t => (
        <button key={t.k} type="button" className={`v3-tb${active === t.k ? ' on' : ''}`} onClick={() => onPick(t.k)} aria-current={active === t.k ? 'true' : undefined}>
          {t.icon}{t.k === 'today' && todayBadge ? <span className="bd">{todayBadge}</span> : null}{t.label}
        </button>
      ))}
    </nav>
  );
}
