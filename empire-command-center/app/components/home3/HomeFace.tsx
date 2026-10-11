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

export type HomeFaceHandle = { start: () => void };

type Phase = 'orb' | 'ready' | 'live';

const HomeFace = forwardRef<HomeFaceHandle, { size?: number }>(function HomeFace({ size = 176 }, ref) {
  const edition = resolveAvatarEdition(null, EDITION);
  const [phase, setPhase] = useState<Phase>('orb');
  const [minutes, setMinutes] = useState('');
  const [hint, setHint] = useState('Tap to start face');
  const started = useRef(false);

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
        setPhase(enabled ? 'ready' : 'orb');
        setHint(enabled ? 'Tap to start face' : '');
      } catch {
        if (!stop) {
          setPhase('orb');
          setHint('');
        }
      }
    };
    load();
    return () => { stop = true; };
  }, [edition]);

  const start = useCallback(() => {
    if (started.current) return;
    started.current = true;
    setPhase('live');
  }, []);

  useImperativeHandle(ref, () => ({ start }), [start]);

  useEffect(() => {
    const onMsg = (event: MessageEvent) => {
      if (event.data?.type !== 'avatar-status' && event.data?.type !== 'avatar-loaded') return;
      const renderer = event.data.renderer;
      const ok = event.data.success !== false && renderer === 'simli';
      if (!ok && started.current) {
        started.current = false;
        setPhase(hint ? 'ready' : 'orb');
      }
    };
    window.addEventListener('message', onMsg);
    return () => window.removeEventListener('message', onMsg);
  }, [hint]);

  const showOrb = phase !== 'live';
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
        {showOrb && hint ? (
          <button type="button" className="mh-face-tap" onClick={start} aria-label="Start talking face">
            {hint}
          </button>
        ) : null}
      </div>
      {minutes ? <div className="mh-minutes" data-testid="mh-minutes">{minutes}</div> : null}
    </div>
  );
});

HomeFace.displayName = 'HomeFace';
export default HomeFace;
