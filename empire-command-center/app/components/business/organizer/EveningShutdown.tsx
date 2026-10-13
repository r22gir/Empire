'use client';

import React, { useMemo, useState } from 'react';
import { Moon, ArrowRight, Check } from 'lucide-react';
import {
  eveningShutdown,
  formatOrganizerTime,
  KIND_LABEL,
  themedSpaceStyle,
  type OrganizerItem,
  type OrganizerSpace,
  type OrgTheme,
  type ShutdownDestination,
} from '../../../lib/organizer-logic';

type Step = 'review' | 'move' | 'plan';

type MoveMap = Record<string, { destination: ShutdownDestination; later?: string }>;

export default function EveningShutdown({
  items,
  day,
  pack,
  spaces,
  theme,
  owner,
  assistant,
  onComplete,
  onOpenItem,
}: {
  items: OrganizerItem[];
  day: string;
  pack?: any;
  spaces: OrganizerSpace[];
  theme: OrgTheme;
  owner?: string;
  assistant?: string;
  onComplete: (payload: {
    notes: string;
    tomorrow_focus: string;
    tomorrow_space_id: string;
    moves: { id: string; destination: ShutdownDestination; due_at?: string }[];
  }) => void;
  onOpenItem: (item: OrganizerItem) => void;
}) {
  const computed = useMemo(() => eveningShutdown(items, day), [items, day]);
  const completed: OrganizerItem[] = pack?.completed || computed.completed;
  const unfinished: OrganizerItem[] = pack?.unfinished || computed.unfinished;
  const tomorrow: OrganizerItem[] = pack?.tomorrow_preview || computed.tomorrow_preview;
  const areas: string[] = pack?.areas || computed.areas;
  const [step, setStep] = useState<Step>('review');
  const [notes, setNotes] = useState('');
  const [focus, setFocus] = useState('');
  const [focusSpace, setFocusSpace] = useState(spaces[0]?.slug || 'personal');
  const [moves, setMoves] = useState<MoveMap>({});

  function setMove(id: string, destination: ShutdownDestination, later?: string) {
    setMoves((prev) => ({ ...prev, [id]: { destination, later } }));
  }

  function spaceOf(it: OrganizerItem) {
    return themedSpaceStyle(spaces.find((s) => s.slug === it.space_id) || it.space_id, theme);
  }

  const moveList = unfinished.map((it) => ({
    id: it.id,
    destination: moves[it.id]?.destination || 'tomorrow',
    due_at: moves[it.id]?.later,
  }));

  return (
    <div className="org-ritual org-card" data-evening-shutdown="1" data-ritual-step={step}>
      <header className="org-ritual-head">
        <Moon size={18} />
        <div>
          <h3>Evening shutdown</h3>
          <p>
            Review today, park what is unfinished, then set tomorrow — every business and life area,
            not Workroom alone. {assistant || 'Max'} drafts; nothing is sent without {owner || 'the owner'}&apos;s tap.
          </p>
        </div>
      </header>

      <ol className="org-ritual-steps">
        {(['review', 'move', 'plan'] as Step[]).map((s, i) => (
          <li key={s}>
            <button className={step === s ? 'on' : ''} onClick={() => setStep(s)}>
              <em>{i + 1}</em> {s === 'review' ? 'Review today' : s === 'move' ? 'Move unfinished' : 'Plan tomorrow'}
            </button>
          </li>
        ))}
      </ol>

      <div className="org-ritual-areas">
        {(areas.length ? areas : spaces.map((s) => s.slug)).map((slug) => {
          const st = themedSpaceStyle(spaces.find((s) => s.slug === slug) || slug, theme);
          return <span key={slug} style={{ borderColor: st.accent }}>{st.icon} {st.label}</span>;
        })}
        {!areas.length && <span>Quiet across every area</span>}
      </div>

      {step === 'review' && (
        <div className="org-ritual-grid">
          <section data-shutdown-col="completed">
            <h4>Done today <span>{completed.length}</span></h4>
            {completed.length === 0 && <div className="org-note">Nothing marked done yet — that is still a review.</div>}
            {completed.map((it) => (
              <button key={it.id} className="org-ritual-row" onClick={() => onOpenItem(it)}>
                <i style={{ background: spaceOf(it).accent }} />
                <b>{it.title}</b>
                <small>{spaceOf(it).label} · {KIND_LABEL[it.kind || it.type || ''] || it.kind}</small>
              </button>
            ))}
          </section>
          <section data-shutdown-col="unfinished">
            <h4>Still open <span>{unfinished.length}</span></h4>
            {unfinished.length === 0 && <div className="org-note">Today is clear. You can still set tomorrow.</div>}
            {unfinished.map((it) => (
              <button key={it.id} className="org-ritual-row" onClick={() => onOpenItem(it)}>
                <i style={{ background: spaceOf(it).accent }} />
                <b>{it.title}</b>
                <small>{spaceOf(it).label} · {formatOrganizerTime(it.due_at || it.start_time) || 'due'} · overdue or today</small>
              </button>
            ))}
          </section>
          <div className="org-ritual-actions">
            <button className="org-btn-gold" onClick={() => setStep('move')}>
              Continue to move unfinished <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {step === 'move' && (
        <div className="org-ritual-move" data-shutdown-col="move">
          <div className="org-note">Each leftover item needs a home: tomorrow, a later day, keep, or drop. Applies across every area.</div>
          {unfinished.length === 0 && <div className="org-note">Nothing to move.</div>}
          {unfinished.map((it) => {
            const pick = moves[it.id]?.destination || 'tomorrow';
            return (
              <div className="org-ritual-move-row" key={it.id}>
                <div>
                  <b>{it.title}</b>
                  <small>{spaceOf(it).label} · {KIND_LABEL[it.kind || it.type || ''] || it.kind}</small>
                </div>
                <div className="org-ritual-dest" role="group" aria-label={`Move ${it.title}`}>
                  {(['tomorrow', 'later', 'keep', 'drop'] as ShutdownDestination[]).map((d) => (
                    <button key={d} className={pick === d ? 'on' : ''} onClick={() => setMove(it.id, d, moves[it.id]?.later)}>
                      {d}
                    </button>
                  ))}
                </div>
                {pick === 'later' && (
                  <input
                    type="date"
                    value={(moves[it.id]?.later || '').slice(0, 10)}
                    onChange={(e) => setMove(it.id, 'later', e.target.value)}
                    aria-label={`Later date for ${it.title}`}
                  />
                )}
              </div>
            );
          })}
          <div className="org-ritual-actions">
            <button onClick={() => setStep('review')}>Back</button>
            <button className="org-btn-gold" onClick={() => setStep('plan')}>
              Plan tomorrow <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {step === 'plan' && (
        <div className="org-ritual-plan" data-shutdown-col="plan">
          <h4>Already on tomorrow <span>{tomorrow.length}</span></h4>
          {tomorrow.length === 0 && <div className="org-note">Tomorrow is open. Name one focus if you want it on the board.</div>}
          {tomorrow.map((it) => (
            <button key={it.id} className="org-ritual-row" onClick={() => onOpenItem(it)}>
              <i style={{ background: spaceOf(it).accent }} />
              <b>{it.title}</b>
              <small>{spaceOf(it).label} · {formatOrganizerTime(it.due_at || it.start_time)}</small>
            </button>
          ))}
          <label>Tomorrow&apos;s focus (optional)</label>
          <input value={focus} onChange={(e) => setFocus(e.target.value)} placeholder="One thing that would make tomorrow count" />
          <label>Area for that focus</label>
          <select value={focusSpace} onChange={(e) => setFocusSpace(e.target.value)}>
            {spaces.map((s) => <option key={s.slug} value={s.slug}>{s.label}</option>)}
          </select>
          <label>Note to self</label>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} placeholder="What mattered today. What to leave." />
          <div className="org-ritual-actions">
            <button onClick={() => setStep('move')}>Back</button>
            <button
              className="org-btn-gold"
              data-shutdown-complete="1"
              onClick={() => onComplete({
                notes,
                tomorrow_focus: focus,
                tomorrow_space_id: focusSpace,
                moves: moveList,
              })}
            >
              <Check size={14} /> Close the day
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
