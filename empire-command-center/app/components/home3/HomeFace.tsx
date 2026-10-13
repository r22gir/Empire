'use client';
/**
 * Max-home talking face. Reuses /avatar.html + /api/v1/avatar/simli.
 * The session starts only on a user tap so idle minutes are not burned.
 * Missing key or a failed session falls back to the decorative Orb — no console noise.
 */
import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { Orb } from '../../v3/ui';
import { API } from '../../lib/api';
import { EDITION } from '../../v3/edition';
import { avatarFrameSrc, resolveAvatarEdition } from '../../lib/avatarEdition';
import {
  HOME_FACE_LOAD_TIMEOUT_MS,
  HOME_FACE_UNAVAILABLE,
  applyHomeFaceMessage,
  applyHomeFaceTimeout,
  startHomeFace,
  type HomeFacePhase,
  type HomeFaceView,
} from './homeFaceMessages';

export type HomeFaceHandle = { start: () => void };

const HomeFace = forwardRef<HomeFaceHandle, { size?: number }>(function HomeFace({ size = 176 }, ref) {
  const edition = resolveAvatarEdition(null, EDITION);
  const [phase, setPhase] = useState<HomeFacePhase>('orb');
  const [minutes, setMinutes] = useState('');
  const [hint, setHint] = useState('');
  const view = useRef<HomeFaceView>({ phase: 'orb', started: false, loaded: false, hint: '' });

  const commit = useCallback((next: HomeFaceView) => {
    view.current = next;
    setPhase(next.phase);
    setHint(next.hint);
  }, []);

  useEffect(() => {
    let stop = false;
    const load = async () => {
      try {
        const [statusRes, usageRes] = await Promise.all([
          fetch(`${API}/avatar/simli/status?edition=${encodeURIComponent(edition)}`, { signal: AbortSignal.timeout(4000) }),
          fetch(`${API}/avatar/simli/usage?edition=${encodeURIComponent(edition)}`, { signal: AbortSignal.timeout(4000) }),
        ]);
        if (stop) return;
        let enabled = false;
        if (statusRes.ok) {
          const status = await statusRes.json();
          enabled = !!status.enabled;
        }
        if (usageRes.ok) {
          const usage = await usageRes.json();
          if (usage.simli_enabled) {
            setMinutes(`Simli ${(Number(usage.minutes) || 0).toFixed(2)} min`);
          } else if (typeof usage.minutes === 'number') {
            setMinutes(`${Number(usage.minutes).toFixed(2)} min used`);
          }
        }
        if (view.current.started) return;
        const nextHint = enabled ? 'Tap to start face' : '';
        commit({
          phase: enabled ? 'ready' : 'orb',
          started: false,
          loaded: false,
          hint: nextHint,
        });
      } catch {
        if (!stop && !view.current.started) {
          commit({ phase: 'orb', started: false, loaded: false, hint: '' });
        }
      }
    };
    load();
    return () => { stop = true; };
  }, [edition, commit]);

  const start = useCallback(() => {
    commit(startHomeFace(view.current));
  }, [commit]);

  useImperativeHandle(ref, () => ({ start }), [start]);

  useEffect(() => {
    const onMsg = (event: MessageEvent) => {
      if (!view.current.started) return;
      commit(applyHomeFaceMessage(view.current, event.data || {}));
    };
    window.addEventListener('message', onMsg);
    return () => window.removeEventListener('message', onMsg);
  }, [commit]);

  useEffect(() => {
    if (phase !== 'live') return;
    const timer = window.setTimeout(() => {
      commit(applyHomeFaceTimeout(view.current, HOME_FACE_LOAD_TIMEOUT_MS));
    }, HOME_FACE_LOAD_TIMEOUT_MS);
    return () => window.clearTimeout(timer);
  }, [phase, commit]);

  const showOrb = phase !== 'live';
  const unavailable = hint === HOME_FACE_UNAVAILABLE;
  return (
    <div className="mh-face-wrap">
      <div className="mh-face" data-testid="mh-face" data-phase={phase} data-edition={edition}>
        {phase === 'live' ? (
          <iframe
            src={avatarFrameSrc(edition, { fallback: 'none' })}
            title={`${edition} talking face`}
            allow="autoplay"
          />
        ) : (
          <Orb size={size} />
        )}
        {showOrb && hint && !unavailable ? (
          <button type="button" className="mh-face-tap" onClick={start} aria-label="Start talking face">
            {hint}
          </button>
        ) : null}
      </div>
      {unavailable ? (
        <button
          type="button"
          className="mh-face-note"
          onClick={start}
          data-testid="mh-face-retry"
          aria-label={HOME_FACE_UNAVAILABLE}
        >
          {HOME_FACE_UNAVAILABLE}
        </button>
      ) : null}
      {minutes ? <div className="mh-minutes" data-testid="mh-minutes">{minutes}</div> : null}
    </div>
  );
});

HomeFace.displayName = 'HomeFace';
export default HomeFace;
