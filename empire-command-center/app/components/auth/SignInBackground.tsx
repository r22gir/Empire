'use client';

import { useEffect, useMemo, useState } from 'react';
import { SIGNIN_BACKGROUNDS } from '../../lib/signin-backgrounds';

function wrapDist(i: number, index: number, n: number): number {
  return Math.min((i - index + n) % n, (index - i + n) % n);
}

export default function SignInBackground() {
  const slides = SIGNIN_BACKGROUNDS.slides;
  const [index, setIndex] = useState(0);
  const [reduceMotion, setReduceMotion] = useState(false);
  const [loaded, setLoaded] = useState<Record<string, true>>({});

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const apply = () => setReduceMotion(mq.matches);
    apply();
    mq.addEventListener('change', apply);
    return () => mq.removeEventListener('change', apply);
  }, []);

  useEffect(() => {
    if (reduceMotion || slides.length < 2) return;
    const id = window.setInterval(() => {
      setIndex((i) => (i + 1) % slides.length);
    }, SIGNIN_BACKGROUNDS.intervalMs);
    return () => window.clearInterval(id);
  }, [reduceMotion, slides.length]);

  const shouldLoad = useMemo(() => {
    return slides.map((slide, i) => {
      if (reduceMotion) return i === 0;
      if (i === 0) return true;
      return wrapDist(i, index, slides.length) <= 1;
    });
  }, [index, reduceMotion, slides]);

  useEffect(() => {
    slides.forEach((slide, i) => {
      if (!shouldLoad[i] || loaded[slide.src]) return;
      const img = new Image();
      img.decoding = i === 0 ? 'sync' : 'async';
      img.src = slide.src;
      img.onload = () => setLoaded((prev) => ({ ...prev, [slide.src]: true }));
    });
  }, [loaded, shouldLoad, slides]);

  const active = slides[index] || slides[0];

  return (
    <div className="signin-bg" aria-hidden="true">
      {slides.map((slide, i) => {
        const on = reduceMotion ? i === 0 : i === index;
        const ready = loaded[slide.src] || i === 0;
        if (!shouldLoad[i] && !ready) return null;
        return (
          <div
            key={slide.src}
            className={`signin-bg-slide${on ? ' is-on' : ''}`}
          >
            <img
              src={slide.src}
              alt=""
              width={1080}
              height={1440}
              sizes="100vw"
              decoding={i === 0 ? 'sync' : 'async'}
              fetchPriority={i === 0 ? 'high' : 'low'}
              loading={i === 0 ? 'eager' : 'lazy'}
              draggable={false}
            />
          </div>
        );
      })}
      {active?.caption && (
        <p className="signin-bg-caption">{active.caption}</p>
      )}
    </div>
  );
}
