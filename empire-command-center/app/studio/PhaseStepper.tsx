'use client';
import { useMemo, useState } from 'react';
import { ChevronRight } from 'lucide-react';
import { KANBAN_STAGES, canonicalizeStage, nextStage, stageLabel } from './jobStages';

export default function PhaseStepper({
  currentStage,
  onMove,
  moving,
  tone = 'light',
}: {
  currentStage?: string | null;
  onMove: (stage: string) => void | Promise<void>;
  moving?: boolean;
  tone?: 'light' | 'dark';
}) {
  const current = canonicalizeStage(currentStage);
  const nxt = nextStage(current);
  const idx = useMemo(() => KANBAN_STAGES.findIndex((s) => s.key === current), [current]);
  const [pick, setPick] = useState('');
  const dark = tone === 'dark';

  return (
    <section
      className={`phase-stepper ${dark ? 'dark' : 'light'}`}
      data-testid="phase-stepper"
      aria-label="Job phases"
    >
      <div className="phase-stepper-track" role="list">
        {KANBAN_STAGES.map((s, i) => {
          const state = i < idx ? 'done' : i === idx ? 'current' : 'todo';
          return (
            <button
              key={s.key}
              type="button"
              role="listitem"
              className={`phase-step ${state}`}
              data-testid={`phase-step-${s.key}`}
              aria-current={state === 'current' ? 'step' : undefined}
              disabled={moving || s.key === current}
              onClick={() => onMove(s.key)}
              title={s.key === current ? `Current phase: ${s.label}` : `Move to ${s.label}`}
              style={{ ['--ph' as string]: s.color }}
            >
              <span className="dot" />
              <span className="lbl">{s.label}</span>
            </button>
          );
        })}
      </div>

      <div className="phase-stepper-actions">
        <button
          type="button"
          className="phase-next"
          data-testid="move-next-phase"
          disabled={!nxt || moving}
          onClick={() => nxt && onMove(nxt.key)}
        >
          {nxt ? `Move to next phase · ${nxt.label}` : 'Final phase'}
          {nxt ? <ChevronRight size={16} /> : null}
        </button>
        <label className="phase-pick">
          <span>Pick any phase</span>
          <select
            data-testid="pick-phase"
            value={pick}
            disabled={moving}
            onChange={(e) => {
              const v = e.target.value;
              setPick('');
              if (v && v !== current) onMove(v);
            }}
          >
            <option value="">Choose a phase…</option>
            {KANBAN_STAGES.map((s) => (
              <option key={s.key} value={s.key} disabled={s.key === current}>
                {s.label}{s.key === current ? ' (current)' : ''}
              </option>
            ))}
          </select>
        </label>
        <p className="phase-hint">
          Current: <strong>{stageLabel(current)}</strong>
          {nxt ? ` · Next: ${nxt.label}` : ' · Job is in the last phase'}
          {' · Tap a phase or use the button. Drag on the board is extra.'}
        </p>
      </div>
    </section>
  );
}
