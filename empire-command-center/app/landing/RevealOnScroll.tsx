'use client';

import { useEffect } from 'react';

/**
 * R1X-PUB-EMPIREBOX: small client island.
 * One IntersectionObserver drives the scroll-reveal effect for every
 * element with a [data-reveal] attribute. Respects prefers-reduced-motion.
 * Returns null — contributes no layout cost.
 */
export default function RevealOnScroll() {
  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Respect prefers-reduced-motion: skip the animation entirely.
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      document
        .querySelectorAll<HTMLElement>('[data-reveal]')
        .forEach((el) => el.classList.add('is-revealed'));
      return;
    }

    const targets = document.querySelectorAll<HTMLElement>('[data-reveal]');
    if (targets.length === 0) return;

    if (!('IntersectionObserver' in window)) {
      targets.forEach((el) => el.classList.add('is-revealed'));
      return;
    }

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('is-revealed');
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.15, rootMargin: '0px 0px -10% 0px' }
    );

    targets.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  return null;
}
