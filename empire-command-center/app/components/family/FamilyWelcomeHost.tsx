'use client';

import { useCallback, useEffect, useState } from 'react';
import { editionFromEnv } from '../../lib/edition';
import {
  DEFAULT_INTERVAL_MS,
  WELCOME_REPLAY_EVENT,
  clearWelcomeReplayQuery,
  defaultWelcomeDeck,
  replayRequested,
  shouldShowFamilyWelcome,
  welcomePayloadLooksPrivate,
} from '../../lib/familyWelcome';
import FamilyWelcomeOverlay, { type WelcomeSlide } from './FamilyWelcomeOverlay';

type WelcomeState = {
  assistant: string;
  slides: WelcomeSlide[];
  intervalMs: number;
  seen: boolean;
};

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export default function FamilyWelcomeHost() {
  const [payload, setPayload] = useState<WelcomeState | null>(null);
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [reducedMotion, setReducedMotion] = useState(false);

  const close = useCallback(async () => {
    setOpen(false);
    setIndex(0);
    clearWelcomeReplayQuery();
    try {
      await fetch('/api/v1/welcome/seen', { method: 'POST', credentials: 'include' });
    } catch {
      // Seen is server-side; a failed mark still leaves the overlay closed this session.
    }
    setPayload((current) => (current ? { ...current, seen: true } : current));
  }, []);

  useEffect(() => {
    const edition = editionFromEnv();
    const host = typeof window !== 'undefined' ? window.location.hostname : '';
    const path = typeof window !== 'undefined' ? window.location.pathname : '/';
    const wantReplay = replayRequested(typeof window !== 'undefined' ? window.location.search : '');
    // replay:true only asks "is this a family surface that may show the overlay?"
    if (!shouldShowFamilyWelcome({ edition, host, pathname: path, seen: false, replay: true })) {
      return;
    }
    let cancelled = false;
    const reduced = prefersReducedMotion();
    setReducedMotion(reduced);
    setPlaying(!reduced);

    fetch('/api/v1/welcome', { credentials: 'include', cache: 'no-store' })
      .then(async (res) => {
        if (!res.ok) return null;
        const body = await res.json().catch(() => null);
        return welcomePayloadLooksPrivate(body) ? body : null;
      })
      .then((body) => {
        if (cancelled || !body) return;
        const next: WelcomeState = {
          assistant: String(body.assistant || defaultWelcomeDeck(edition).assistant),
          slides: Array.isArray(body.slides) && body.slides.length
            ? body.slides
            : defaultWelcomeDeck(edition).slides,
          intervalMs: Number(body.interval_ms) || DEFAULT_INTERVAL_MS,
          seen: Boolean(body.seen),
        };
        setPayload(next);
        const show = shouldShowFamilyWelcome({
          edition,
          host,
          pathname: path,
          seen: next.seen,
          replay: wantReplay,
        });
        setOpen(show);
      })
      .catch(() => {});

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    function onReplay() {
      const edition = editionFromEnv();
      const host = window.location.hostname;
      const path = window.location.pathname;
      if (!shouldShowFamilyWelcome({ edition, host, pathname: path, seen: true, replay: true })) return;
      setIndex(0);
      setPlaying(!prefersReducedMotion());
      setOpen(true);
      if (!payload) {
        const deck = defaultWelcomeDeck(edition);
        setPayload({
          assistant: deck.assistant,
          slides: deck.slides,
          intervalMs: deck.interval_ms || DEFAULT_INTERVAL_MS,
          seen: true,
        });
      }
    }
    window.addEventListener(WELCOME_REPLAY_EVENT, onReplay);
    return () => window.removeEventListener(WELCOME_REPLAY_EVENT, onReplay);
  }, [payload]);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const onChange = () => {
      const reduced = media.matches;
      setReducedMotion(reduced);
      if (reduced) setPlaying(false);
    };
    media.addEventListener('change', onChange);
    return () => media.removeEventListener('change', onChange);
  }, []);

  if (!open || !payload) return null;

  return (
    <FamilyWelcomeOverlay
      assistant={payload.assistant}
      slides={payload.slides}
      index={index}
      playing={playing}
      reducedMotion={reducedMotion}
      intervalMs={payload.intervalMs}
      onIndex={setIndex}
      onPlaying={setPlaying}
      onDismiss={close}
    />
  );
}
