'use client';

import { useEffect, useId, useRef } from 'react';
import {
  WELCOME_SKIP_ARIA,
  WELCOME_SKIP_LABEL,
  autoAdvanceEnabled,
  isLastSlide,
  nextSlideIndex,
  prevSlideIndex,
  sanitizeWelcomeImage,
} from '../../lib/familyWelcome';
import './familyWelcome.css';

export type WelcomeSlide = {
  id: string;
  title: string;
  body: string;
  image?: string | null;
};

type Props = {
  assistant: string;
  slides: WelcomeSlide[];
  index: number;
  playing: boolean;
  reducedMotion: boolean;
  intervalMs: number;
  onIndex: (index: number) => void;
  onPlaying: (playing: boolean) => void;
  onDismiss: () => void;
};

export default function FamilyWelcomeOverlay({
  assistant,
  slides,
  index,
  playing,
  reducedMotion,
  intervalMs,
  onIndex,
  onPlaying,
  onDismiss,
}: Props) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const slide = slides[index] || slides[0];
  const total = slides.length || 1;
  const last = isLastSlide(index, total);
  const image = sanitizeWelcomeImage(slide?.image);
  const mark = (assistant || 'M').trim().charAt(0).toUpperCase();

  useEffect(() => {
    dialogRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!autoAdvanceEnabled(reducedMotion, playing) || !slide) return;
    const timer = window.setTimeout(() => {
      if (last) onDismiss();
      else onIndex(nextSlideIndex(index, total));
    }, intervalMs);
    return () => window.clearTimeout(timer);
  }, [index, intervalMs, last, onDismiss, onIndex, playing, reducedMotion, slide, total]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault();
        onDismiss();
      } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        if (last) onDismiss();
        else onIndex(nextSlideIndex(index, total));
      } else if (event.key === 'ArrowLeft') {
        event.preventDefault();
        onIndex(prevSlideIndex(index));
      } else if (event.key === ' ') {
        event.preventDefault();
        onPlaying(!playing);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [index, last, onDismiss, onIndex, onPlaying, playing, total]);

  if (!slide) return null;

  return (
    <div className="family-welcome" data-testid="family-welcome-overlay">
      <div
        ref={dialogRef}
        className="family-welcome-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
      >
        <div className="family-welcome-slide" aria-live="polite">
          <div className="family-welcome-visual" aria-hidden={image ? undefined : true}>
            {image ? (
              <img src={image} alt="" />
            ) : (
              <span className="family-welcome-mark">{mark}</span>
            )}
          </div>
          <div className="family-welcome-copy">
            <p className="family-welcome-kicker">{assistant}</p>
            <h2 id={titleId} className="family-welcome-title">{slide.title}</h2>
            <p className="family-welcome-body">{slide.body}</p>
          </div>
        </div>
        <div className="family-welcome-controls">
          <div className="family-welcome-dots" role="tablist" aria-label="Diapositivas">
            {slides.map((item, slideIndex) => (
              <button
                key={item.id || slideIndex}
                type="button"
                className="family-welcome-dot"
                aria-label={`Ir a la diapositiva ${slideIndex + 1}`}
                aria-current={slideIndex === index || undefined}
                onClick={() => onIndex(slideIndex)}
              />
            ))}
          </div>
          <span className="family-welcome-count">{index + 1} / {total}</span>
          <button type="button" className="family-welcome-btn" onClick={() => onIndex(prevSlideIndex(index))} disabled={index === 0}>
            Atrás
          </button>
          <button
            type="button"
            className="family-welcome-btn"
            onClick={() => onPlaying(!playing)}
            aria-pressed={playing}
          >
            {playing && !reducedMotion ? 'Pausa' : 'Reproducir'}
          </button>
          <button
            type="button"
            className="family-welcome-btn"
            data-primary="true"
            onClick={() => (last ? onDismiss() : onIndex(nextSlideIndex(index, total)))}
          >
            {last ? 'Empezar' : 'Siguiente'}
          </button>
          <button
            type="button"
            className="family-welcome-btn"
            data-skip="true"
            aria-label={WELCOME_SKIP_ARIA}
            onClick={onDismiss}
          >
            {WELCOME_SKIP_LABEL}
          </button>
        </div>
      </div>
    </div>
  );
}
