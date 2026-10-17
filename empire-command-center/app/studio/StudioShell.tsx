'use client';
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Search, X } from 'lucide-react';
import { NAV_GROUPS, type NavItem } from '../components/layout/LeftNav';
import UniversalSearch from '../components/search/UniversalSearch';
import type { SearchHit } from '../lib/universal-search';
import { EDITION } from '../v3/edition';
import { API } from '../lib/api';
import { isPlannedModule, isSystemModule, navHref, type StudioTab } from './moduleHome';
import { StudioTabButtons } from './StudioTabs';
import './studio.css';

export interface StudioNavigate {
  tab?: StudioTab;
  product?: string;
  screen?: string;
  section?: string | null;
  ask?: string;
}

function itemHref(item: NavItem): string {
  return navHref(item);
}

export default function StudioShell({
  tab,
  title,
  onTab,
  onNavigate,
  onSearchOpen,
  children,
  showJobChrome,
}: {
  tab: StudioTab;
  title?: string;
  onTab: (tab: StudioTab) => void;
  onNavigate: (next: StudioNavigate | string) => void;
  onSearchOpen?: (hit: SearchHit) => void;
  children: ReactNode;
  showJobChrome?: boolean;
}) {
  const [sheet, setSheet] = useState<'plus' | 'system' | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        setSearchOpen((v) => !v);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const plusGroups = useMemo(
    () => NAV_GROUPS
      .map((g) => ({
        ...g,
        items: g.items.filter((it) => !isPlannedModule(it.id) && !isSystemModule(it.id)),
      }))
      .filter((g) => g.items.length),
    [],
  );
  const systemItems = useMemo(
    () => NAV_GROUPS.flatMap((g) => g.items).filter((it) => isSystemModule(it.id) || isPlannedModule(it.id)),
    [],
  );

  const pick = useCallback((item: NavItem) => {
    setSheet(null);
    onNavigate(itemHref(item));
  }, [onNavigate]);

  const openHit = (hit: SearchHit) => {
    setSearchOpen(false);
    if (onSearchOpen) {
      onSearchOpen(hit);
      return;
    }
    const href = hit.action?.href || hit.href;
    if (href) onNavigate(href);
  };

  const draftHit = async (hit: SearchHit) => {
    try {
      const res = await fetch(`${API}/universal-search/draft-reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mail_id: hit.action?.mail_id || '', source: hit.action?.source || 'gmail' }),
      });
      const data = await res.json().catch(() => ({}));
      onNavigate(data.href || '/?product=lead&section=approvals');
    } catch {
      onNavigate('/?product=lead&section=approvals');
    }
  };

  const heading = title || (tab === 'max' ? `${EDITION.assistantName.toUpperCase()} · LISTENING` : tab === 'today' ? 'Empire Workroom' : tab === 'work' ? 'Work' : 'Money');

  return (
    <div className="studio-shell v3" data-studio-shell data-max-home={tab === 'max' ? '' : undefined}>
      <header className="studio-band">
        <span className="e" aria-hidden="true">E</span>
        <span className="title">{heading}</span>
        <span className="grow" />
        <button type="button" className="icon" onClick={() => setSearchOpen(true)} aria-label="Search" data-testid="universal-search-trigger">
          <Search size={15} />
        </button>
        <button type="button" className="av" onClick={() => setSheet('plus')} aria-label="Modules and settings" data-testid="studio-avatar">
          {EDITION.ownerInitials}
        </button>
      </header>

      <div className="studio-main">
        <StudioTabButtons active={tab} onPick={onTab} className="studio-rail" />
        <div className="studio-content">{children}</div>
        {showJobChrome}
      </div>

      <StudioTabButtons active={tab} onPick={onTab} className="studio-tabbar" />

      {sheet && (
        <>
          <div className="studio-sheet-back" onClick={() => setSheet(null)} />
          <div className="studio-sheet" role="dialog" aria-label="Modules">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <h2>{sheet === 'system' ? 'System / Settings' : 'Modules'}</h2>
              <button type="button" className="icon" style={{ marginLeft: 'auto' }} onClick={() => setSheet(null)} aria-label="Close"><X size={14} /></button>
            </div>
            {sheet === 'plus' && plusGroups.map((g) => (
              <div key={g.key}>
                <div className="studio-grp">{g.label}</div>
                {g.items.map((it) => (
                  <button key={it.id} type="button" className="studio-mod" onClick={() => pick(it)}>
                    {it.icon}<span>{it.name}</span>
                  </button>
                ))}
              </div>
            ))}
            {sheet === 'plus' && (
              <button type="button" className="studio-mod" onClick={() => setSheet('system')}>
                <span>System / Settings</span>
                <span className="st">dev tools</span>
              </button>
            )}
            {sheet === 'system' && systemItems.map((it) => (
              <button key={it.id} type="button" className="studio-mod" onClick={() => pick(it)}>
                {it.icon}<span>{it.name}</span>
                {it.status !== 'active' ? <span className="st">{it.status}</span> : null}
              </button>
            ))}
            {sheet === 'system' && (
              <button type="button" className="studio-mod" onClick={() => { setSheet(null); onNavigate('/?screen=settings'); }}>
                <span>Trusted devices & sign-in</span>
              </button>
            )}
            {sheet === 'system' && (
              <a className="studio-mod" href="/classic">Classic Command Center</a>
            )}
          </div>
        </>
      )}

      <UniversalSearch
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        onOpen={openHit}
        onDraftReply={draftHit}
      />
    </div>
  );
}
