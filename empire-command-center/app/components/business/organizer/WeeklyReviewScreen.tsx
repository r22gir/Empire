'use client';

import React from 'react';
import { ListChecks } from 'lucide-react';
import {
  KIND_LABEL,
  themedSpaceStyle,
  weeklyReview,
  type OrganizerItem,
  type OrganizerSpace,
  type OrgTheme,
} from '../../../lib/organizer-logic';

const BUCKETS = [
  { id: 'wins', label: 'This week’s wins' },
  { id: 'slipped', label: 'Slipped' },
  { id: 'stuck', label: 'Stuck (7+ days)' },
  { id: 'next_week', label: 'Next week' },
] as const;

export default function WeeklyReviewScreen({
  items,
  day,
  pack,
  spaces,
  theme,
  onOpenItem,
  renderExtra,
}: {
  items: OrganizerItem[];
  day: string;
  pack?: any;
  spaces: OrganizerSpace[];
  theme: OrgTheme;
  onOpenItem: (item: OrganizerItem) => void;
  renderExtra?: (item: OrganizerItem) => React.ReactNode;
}) {
  const computed = weeklyReview(items, day);
  return (
    <div className="org-review org-card org-weekly" data-weekly-review="1">
      <header className="org-ritual-head">
        <ListChecks size={18} />
        <div>
          <h3>Weekly review</h3>
          <p>
            Wins, slips, stuck work, and next week — across every business and life area.
            Family and personal stay on this edition. Workroom is one column, not the whole week.
          </p>
        </div>
      </header>
      <div className="org-ritual-areas">
        {spaces.map((s) => {
          const st = themedSpaceStyle(s, theme);
          const n = BUCKETS.reduce((sum, b) => sum + ((pack?.by_space?.[b.id]?.[s.slug] || computed.by_space[b.id]?.[s.slug] || []).length), 0);
          return (
            <span key={s.slug} style={{ borderColor: st.accent }}>
              {st.icon} {st.label}{n ? ` · ${n}` : ''}
            </span>
          );
        })}
      </div>
      <div className="org-weekly-grid">
        {BUCKETS.map((bucket) => {
          const rows = (pack?.[bucket.id] || computed[bucket.id]) as OrganizerItem[];
          return (
            <section key={bucket.id} className="org-review-col" data-review={bucket.id}>
              <h4>{bucket.label} <span>{rows.length}</span></h4>
              {rows.length === 0 && <div className="org-note">None.</div>}
              {rows.map((it) => {
                const st = themedSpaceStyle(spaces.find((s) => s.slug === it.space_id) || it.space_id, theme);
                return (
                  <div className="org-row" key={it.id} onClick={() => onOpenItem(it)}>
                    <span className="tm" style={{ color: st.accent }}>{(it.due_at || it.start_time || '').slice(5, 10) || '—'}</span>
                    <span>
                      <b>{it.title}</b>
                      <small>{st.label} · {KIND_LABEL[it.kind || it.type || ''] || it.kind}</small>
                      {renderExtra?.(it)}
                    </span>
                  </div>
                );
              })}
            </section>
          );
        })}
      </div>
    </div>
  );
}
