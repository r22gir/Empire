'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useAudio } from '@/context/AudioContext';
import { SAMPLE_TRACKS, COACHES } from '@/lib/amp-content';
import {
  Sparkles, Play, ArrowRight, CheckCircle2, Heart,
  Sun, Compass, Star
} from 'lucide-react';

const MOOD_OPTIONS = [
  { key: 'feliz', label: 'Feliz & Radiante', emoji: '😊', theme: 'abundancia' },
  { key: 'en_paz', label: 'En Paz & Calma', emoji: '😌', theme: 'gratitud' },
  { key: 'ansioso', label: 'Ansioso / Con Prisa', emoji: '😰', theme: 'ansiedad' },
  { key: 'triste', label: 'Nostálgico / Triste', emoji: '😔', theme: 'duelo' },
  { key: 'motivado', label: 'Con Energía / Motivado', emoji: '💪', theme: 'liderazgo' },
];

export default function HomePage() {
  const { playTrack } = useAudio();
  const [selectedMood, setSelectedMood] = useState<string | null>(null);
  const [recommendedTrack, setRecommendedTrack] = useState<typeof SAMPLE_TRACKS[0] | null>(null);

  const handleMoodSelect = (moodKey: string, theme: string) => {
    setSelectedMood(moodKey);
    const matched = SAMPLE_TRACKS.find(t => t.theme === theme) || SAMPLE_TRACKS[0];
    setRecommendedTrack(matched);
  };

  const featuredTrack = SAMPLE_TRACKS[0];

  return (
    <div className="flex flex-col min-h-screen">
      {/* ── IMMERSIVE HERO WITH BREATHING GRADIENT / FALLBACK ── */}
      <section className="relative overflow-hidden pt-12 pb-20 md:py-24 border-b border-[#F0E6D8] dark:border-[#2E2A54]">
        {/* Soft sunrise aura background */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#FFE3B3]/40 via-[#FFF9F1] to-[#E4EDE6]/30 dark:from-[#14122B] dark:via-[#1E1B3A] dark:to-[#3A2E6B]/30 -z-10" />
        <div className="absolute -top-24 right-10 w-96 h-96 bg-[#F28C6B]/15 rounded-full blur-3xl pointer-events-none -z-10" />
        <div className="absolute -bottom-24 left-10 w-96 h-96 bg-[#E0A526]/15 rounded-full blur-3xl pointer-events-none -z-10" />

        <div className="max-w-5xl mx-auto px-4 text-center">
          {/* Eyebrow badge */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#B8860B] dark:text-[#F2C14E] mb-6">
            <Sparkles size={14} /> El Portal de la Alegría
          </div>

          <h1 className="font-serif text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight text-[#2B2622] dark:text-[#F4EFE8] leading-[1.15] mb-6">
            Transforma tu mente, <br />
            <span className="gradient-text">un día a la vez.</span>
          </h1>

          <p className="text-lg md:text-xl text-[#6B625A] dark:text-[#B9B2C9] max-w-2xl mx-auto leading-relaxed mb-10">
            La fusión entre la profundidad del crecimiento personal y la calma diaria de la meditación guiada en español. Bienvenido a tu nuevo refugio de paz.
          </p>

          {/* Primary Call to Action */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-14">
            <Link
              href="/onboarding"
              className="w-full sm:w-auto px-8 py-4 rounded-2xl bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-[#2B2622] font-bold text-base shadow-lg shadow-[#E0A526]/20 hover:scale-105 transition-all text-center no-underline flex items-center justify-center gap-2"
            >
              Comienza tu Camino Gratis <ArrowRight size={18} />
            </Link>

            <button
              onClick={() => playTrack(featuredTrack)}
              className="w-full sm:w-auto px-6 py-4 rounded-2xl bg-white dark:bg-[#1E1B3A] border-2 border-[#E0A526]/30 hover:border-[#E0A526] text-[#2B2622] dark:text-[#F4EFE8] font-bold text-base transition-all flex items-center justify-center gap-2.5 shadow-sm"
            >
              <div className="w-7 h-7 rounded-full bg-[#E0A526] text-white flex items-center justify-center">
                <Play size={14} className="ml-0.5" />
              </div>
              Escuchar Meditación Destacada (5 min)
            </button>
          </div>

          {/* ── DIRECT HERO CHECK-IN: "¿CÓMO TE SIENTES HOY?" ── */}
          <div className="max-w-2xl mx-auto bg-white/90 dark:bg-[#1E1B3A]/90 backdrop-blur-md rounded-3xl p-6 sm:p-8 border border-[#F0E6D8] dark:border-[#2E2A54] shadow-xl text-left">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-[#E0A526]">
                  Práctica del Momento
                </p>
                <h2 className="font-serif text-xl sm:text-2xl font-bold text-[#2B2622] dark:text-[#F4EFE8]">
                  ¿Cómo te sientes hoy?
                </h2>
              </div>
              <div className="text-xs text-[#6B625A] dark:text-[#B9B2C9] bg-black/5 dark:bg-white/5 px-2.5 py-1 rounded-full">
                Sin registro previo
              </div>
            </div>

            <p className="text-sm text-[#6B625A] dark:text-[#B9B2C9] mb-5">
              Elige tu estado interior actual y te recomendaremos la práctica sonora ideal para transformar tu energía:
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 mb-6">
              {MOOD_OPTIONS.map((m) => {
                const isSelected = selectedMood === m.key;
                return (
                  <button
                    key={m.key}
                    onClick={() => handleMoodSelect(m.key, m.theme)}
                    className={`p-3 rounded-2xl border text-left transition-all flex items-center gap-2.5 ${
                      isSelected
                        ? 'border-[#E0A526] bg-[#E0A526]/10 text-[#B8860B] dark:text-[#F2C14E] shadow-sm'
                        : 'border-[#F0E6D8] dark:border-[#2E2A54] hover:bg-black/5 dark:hover:bg-white/5 text-[#2B2622] dark:text-[#F4EFE8]'
                    }`}
                  >
                    <span className="text-2xl">{m.emoji}</span>
                    <span className="text-xs font-semibold leading-tight">{m.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Instant recommendation panel */}
            {recommendedTrack && (
              <div className="p-4 rounded-2xl bg-[#FFE3B3]/25 dark:bg-[#14122B] border border-[#E0A526]/40 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-fade-up">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-[#E0A526] text-white">
                      Recomendada para ti
                    </span>
                    <span className="text-xs text-[#6B625A] dark:text-[#B9B2C9]">
                      {recommendedTrack.durationLabel}
                    </span>
                  </div>
                  <h4 className="font-serif font-bold text-base text-[#2B2622] dark:text-[#F4EFE8]">
                    {recommendedTrack.title}
                  </h4>
                  <p className="text-xs text-[#6B625A] dark:text-[#B9B2C9]">
                    Por {recommendedTrack.coach}
                  </p>
                </div>

                <button
                  onClick={() => playTrack(recommendedTrack)}
                  className="px-5 py-2.5 rounded-xl bg-[#E0A526] hover:bg-[#B8860B] text-white font-bold text-xs uppercase tracking-wider flex items-center gap-2 shrink-0 transition-colors shadow"
                >
                  <Play size={14} className="fill-white" /> Reproducir ahora
                </button>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── VALUE PROPOSITION & PILLARS ── */}
      <section className="py-16 md:py-20 max-w-6xl mx-auto px-4 w-full">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <p className="text-xs font-bold uppercase tracking-wider text-[#E0A526] mb-2">
            Metodología AMP
          </p>
          <h2 className="font-serif text-3xl md:text-4xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-4">
            Los 3 Pilares del Portal
          </h2>
          <p className="text-sm md:text-base text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed">
            Una estructura probada para armonizar tus pensamientos, sanar tus emociones y liderar tu propia existencia.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-white dark:bg-[#1E1B3A] p-8 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54] shadow-sm hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-2xl bg-[#E0A526]/15 text-[#E0A526] flex items-center justify-center mb-6">
              <Sun size={26} />
            </div>
            <h3 className="font-serif text-xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-3">
              1. Mentalidad Positiva
            </h3>
            <p className="text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed mb-4">
              Reprograma patrones de autoexigencia y desconfianza. Aprende a convertir cada obstáculo en un escalón de crecimiento personal.
            </p>
            <ul className="text-xs space-y-2 text-[#6B625A] dark:text-[#B9B2C9]">
              <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-[#E0A526]" /> Afirmaciones conscientes diarias</li>
              <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-[#E0A526]" /> Práctica constante de gratitud</li>
            </ul>
          </div>

          <div className="bg-white dark:bg-[#1E1B3A] p-8 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54] shadow-sm hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-2xl bg-[#7E9F84]/15 text-[#7E9F84] flex items-center justify-center mb-6">
              <Heart size={26} />
            </div>
            <h3 className="font-serif text-xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-3">
              2. Bienestar Emocional
            </h3>
            <p className="text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed mb-4">
              Vuelve al centro a través de la respiración consciente, la compasión ante el duelo y técnicas de alivio de estrés para conciliar el sueño.
            </p>
            <ul className="text-xs space-y-2 text-[#6B625A] dark:text-[#B9B2C9]">
              <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-[#7E9F84]" /> Meditaciones temáticas desde 5 min</li>
              <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-[#7E9F84]" /> Paisajes sonoros relajantes</li>
            </ul>
          </div>

          <div className="bg-white dark:bg-[#1E1B3A] p-8 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54] shadow-sm hover:shadow-md transition-shadow">
            <div className="w-12 h-12 rounded-2xl bg-[#F28C6B]/15 text-[#F28C6B] flex items-center justify-center mb-6">
              <Compass size={26} />
            </div>
            <h3 className="font-serif text-xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-3">
              3. Liderazgo con Propósito
            </h3>
            <p className="text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed mb-4">
              Inspirado en la filosofía de John Maxwell: antes de liderar equipos o familias, aprende a liderar tus propias decisiones con integridad.
            </p>
            <ul className="text-xs space-y-2 text-[#6B625A] dark:text-[#B9B2C9]">
              <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-[#F28C6B]" /> Retos estructurados de 21 días</li>
              <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-[#F28C6B]" /> Sesiones 1:1 y mentoría en vivo</li>
            </ul>
          </div>
        </div>
      </section>

      {/* ── FEATURED MEDITATIONS TRACKS ── */}
      <section className="py-16 bg-white dark:bg-[#1E1B3A] border-y border-[#F0E6D8] dark:border-[#2E2A54]">
        <div className="max-w-6xl mx-auto px-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-end justify-between gap-4 mb-10">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-[#E0A526] mb-1">
                Biblioteca Sonora
              </p>
              <h2 className="font-serif text-3xl font-bold text-[#2B2622] dark:text-[#F4EFE8]">
                Meditaciones Destacadas
              </h2>
            </div>
            <Link
              href="/biblioteca"
              className="text-sm font-bold text-[#E0A526] hover:text-[#B8860B] flex items-center gap-1"
            >
              Ver biblioteca completa →
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {SAMPLE_TRACKS.slice(0, 3).map((track) => (
              <div
                key={track.id}
                className="bg-[#FFF9F1] dark:bg-[#14122B] p-6 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54] flex flex-col justify-between group hover:border-[#E0A526] transition-all"
              >
                <div>
                  <div className="flex items-center justify-between text-xs mb-3">
                    <span className="font-bold px-2.5 py-1 rounded-full bg-[#E0A526]/15 text-[#B8860B] dark:text-[#F2C14E] uppercase tracking-wider">
                      {track.theme}
                    </span>
                    <span className="text-[#6B625A] dark:text-[#B9B2C9]">{track.durationLabel}</span>
                  </div>

                  <h3 className="font-serif text-lg font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-2 group-hover:text-[#E0A526] transition-colors">
                    {track.title}
                  </h3>
                  <p className="text-xs text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed mb-4">
                    {track.description}
                  </p>
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-[#F0E6D8] dark:border-[#2E2A54]">
                  <span className="text-xs font-semibold text-[#6B625A] dark:text-[#B9B2C9]">
                    {track.coach}
                  </span>
                  <button
                    onClick={() => playTrack(track)}
                    className="p-2.5 rounded-full bg-[#E0A526] text-white hover:scale-105 transition-transform"
                    aria-label={`Reproducir ${track.title}`}
                  >
                    <Play size={16} className="ml-0.5 fill-white" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── COACHES TEASER ── */}
      <section className="py-16 md:py-20 max-w-6xl mx-auto px-4 w-full">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <p className="text-xs font-bold uppercase tracking-wider text-[#E0A526] mb-2">
            Equipo Humano
          </p>
          <h2 className="font-serif text-3xl md:text-4xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-4">
            Tus Mentores y Guías
          </h2>
          <p className="text-sm md:text-base text-[#6B625A] dark:text-[#B9B2C9]">
            Acompañamiento cercano por profesionales con trayectorias en transformación personal, duelo, familia y liderazgo.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {COACHES.map((coach) => (
            <div
              key={coach.id}
              className="bg-white dark:bg-[#1E1B3A] rounded-3xl p-6 border border-[#F0E6D8] dark:border-[#2E2A54] text-center flex flex-col justify-between"
            >
              <div>
                <div className="w-24 h-24 mx-auto rounded-full overflow-hidden mb-4 border-2 border-[#E0A526]/30">
                  <img
                    src={coach.photoPlaceholder}
                    alt={coach.name}
                    className="w-full h-full object-cover"
                  />
                </div>
                <h3 className="font-serif text-lg font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-1">
                  {coach.name}
                </h3>
                <p className="text-xs text-[#E0A526] font-semibold mb-3">{coach.role}</p>
                <p className="text-xs text-[#6B625A] dark:text-[#B9B2C9] line-clamp-3 leading-relaxed mb-4">
                  {coach.bio}
                </p>
              </div>

              <Link
                href="/conocenos"
                className="text-xs font-bold text-[#E0A526] hover:underline"
              >
                Conocer historia →
              </Link>
            </div>
          ))}
        </div>

        <div className="text-center">
          <Link
            href="/conocenos"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-full border border-[#E0A526] text-[#B8860B] dark:text-[#F2C14E] font-bold text-sm hover:bg-[#E0A526]/10 transition-colors"
          >
            Ver perfiles completos y credenciales
          </Link>
        </div>
      </section>

      {/* ── TESTIMONIALS PLACEHOLDER ── */}
      <section className="py-16 bg-[#FFE3B3]/20 dark:bg-[#14122B] border-t border-[#F0E6D8] dark:border-[#2E2A54]">
        <div className="max-w-5xl mx-auto px-4">
          <div className="text-center mb-10">
            <span className="text-xs font-bold uppercase tracking-wider text-[#E0A526] block mb-2">
              Comunidad AMP
            </span>
            <h2 className="font-serif text-3xl font-bold text-[#2B2622] dark:text-[#F4EFE8]">
              Testimonios de Transformación
            </h2>
            <p className="text-xs text-[#6B625A] dark:text-[#B9B2C9] italic mt-1">
              (Espacio de testimonios reales de la comunidad en proceso de actualización)
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white dark:bg-[#1E1B3A] p-6 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54] shadow-sm">
              <div className="flex gap-1 text-[#E0A526] mb-3">
                {[...Array(5)].map((_, i) => <Star key={i} size={14} className="fill-[#E0A526]" />)}
              </div>
              <p className="text-xs sm:text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed italic mb-4">
                &ldquo;El reto de 21 días con Juan Diego cambió por completo cómo inicio mis mañanas. Pasé de la ansiedad constante a sentir que yo tengo el timón de mi mente.&rdquo;
              </p>
              <p className="text-xs font-bold text-[#2B2622] dark:text-[#F4EFE8]">— Carlos M., Cali</p>
            </div>

            <div className="bg-white dark:bg-[#1E1B3A] p-6 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54] shadow-sm">
              <div className="flex gap-1 text-[#E0A526] mb-3">
                {[...Array(5)].map((_, i) => <Star key={i} size={14} className="fill-[#E0A526]" />)}
              </div>
              <p className="text-xs sm:text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed italic mb-4">
                &ldquo;Las meditaciones de Andrea y las herramientas de crianza consciente trajeron una calma hermosa a mi hogar. Muy agradecida con este portal.&rdquo;
              </p>
              <p className="text-xs font-bold text-[#2B2622] dark:text-[#F4EFE8]">— Marcela P., Bogotá</p>
            </div>

            <div className="bg-white dark:bg-[#1E1B3A] p-6 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54] shadow-sm">
              <div className="flex gap-1 text-[#E0A526] mb-3">
                {[...Array(5)].map((_, i) => <Star key={i} size={14} className="fill-[#E0A526]" />)}
              </div>
              <p className="text-xs sm:text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed italic mb-4">
                &ldquo;Encontrar este espacio durante mi proceso de duelo con Lina fue un bálsamo. Saber que no estás sola hace toda la diferencia.&rdquo;
              </p>
              <p className="text-xs font-bold text-[#2B2622] dark:text-[#F4EFE8]">— Lucía G., Medellín</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── MEMBERSHIP CTA BANNER ── */}
      <section className="py-16 md:py-20 max-w-4xl mx-auto px-4 w-full text-center">
        <div className="bg-gradient-to-r from-[#FFE3B3] via-[#FAD4C0] to-[#E4EDE6] dark:from-[#1E1B3A] dark:to-[#3A2E6B] p-8 sm:p-12 rounded-3xl border border-[#E0A526]/30 shadow-xl">
          <span className="text-xs font-bold uppercase tracking-widest text-[#B8860B] dark:text-[#F2C14E] block mb-2">
            Membresía El Portal de la Alegría
          </span>
          <h2 className="font-serif text-3xl sm:text-4xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-4">
            Empieza hoy con 7 días de prueba gratis
          </h2>
          <p className="text-sm sm:text-base text-[#6B625A] dark:text-[#B9B2C9] max-w-xl mx-auto mb-8 leading-relaxed">
            Acceso ilimitado a toda la biblioteca de meditaciones guiadas, retos de transformación y descuentos exclusivos en sesiones individuales de coaching.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/membresia"
              className="px-8 py-3.5 rounded-full bg-[#2B2622] dark:bg-[#F2C14E] text-white dark:text-[#2B2622] font-bold text-sm shadow-md hover:scale-105 transition-transform"
            >
              Ver Planes y Suscribirme
            </Link>
            <Link
              href="/onboarding"
              className="px-6 py-3.5 rounded-full bg-white/80 dark:bg-white/10 text-[#2B2622] dark:text-[#F4EFE8] font-bold text-sm hover:bg-white"
            >
              Hacer el Quiz de Diagnóstico
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
