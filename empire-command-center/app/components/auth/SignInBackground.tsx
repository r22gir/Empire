'use client';

import { useEffect, useState } from 'react';
import { SIGNIN_BACKGROUNDS } from '../../lib/signin-backgrounds';

export default function SignInBackground() {
  const slides = SIGNIN_BACKGROUNDS.slides;
  const [index, setIndex] = useState(0);
  const [reduceMotion, setReduceMotion] = useState(false);

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

  const active = slides[index] || slides[0];

  return (
    <div className="signin-bg" aria-hidden="true">
      {slides.map((slide, i) => {
        const on = reduceMotion ? i === 0 : i === index;
        return (
          <div
            key={slide.src}
            className={`signin-bg-slide${on ? ' is-on' : ''}`}
          >
            <img
              src={slide.src}
              alt=""
              width={1600}
              height={900}
              decoding={i === 0 ? 'sync' : 'async'}
              fetchPriority={i === 0 ? 'high' : 'low'}
              draggable={false}
            />
            {slide.diagram && (
              <img
                src={slide.diagram}
                alt=""
                className="signin-bg-diagram"
                width={280}
                height={200}
                decoding="async"
                fetchPriority="low"
                draggable={false}
              />
            )}
          </div>
        );
      })}
      {active?.caption && (
        <p className="signin-bg-caption">{active.caption}</p>
      )}
    </div>
  );
}
