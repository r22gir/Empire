'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useAudio } from '@/context/AudioContext';
import { SAMPLE_TRACKS, COACHES, PROGRAMS, THEME_CATEGORIES } from '@/lib/amp-content';
import {
  Sparkles, Play, ArrowRight,
  Compass, Star, Users, Clock, BookOpen
} from 'lucide-react';

const MOOD_OPTIONS = [
  { key: 'feliz', label: 'Feliz & Radiante', emoji: '😊', theme: 'abundancia' },
  { key: 'en_paz', label: 'En Paz & Calma', emoji: '😌', theme: 'gratitud' },
  { key: 'ansioso', label: 'Ansioso / Con Prisa', emoji: '😰', theme: 'ansiedad' },
  { key: 'triste', label: 'Nostálgico / Triste', emoji: '😔', theme: 'duelo' },
  { key: 'motivado', label: 'Con Energía / Motivado', emoji: '💪', theme: 'liderazgo' },
];

const PRESS_LOGOS = [
  { name: 'Mindvalley Alumni', desc: 'Metodología Consciente' },
  { name: 'ICF Coaches', desc: 'Estándar Internacional' },
  { name: 'Podcast Positivo', desc: '+150 Episodios' },
  { name: 'Comunidad Hispana', desc: '14 Países' },
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
      {/* ── 1. FULL-BLEED CINEMATIC HERO (Mindvalley / Calm style) ── */}
      <section className="relative overflow-hidden pt-12 pb-24 md:pt-20 md:pb-32 border-b border-[#EFE6D8] dark:border-[#2B254E]">
        {/* Cinematic Background Layer with Overlay */}
        <div className="absolute inset-0 -z-20 overflow-hidden">
          <div
            className="w-full h-full bg-cover bg-center transition-transform duration-1000 scale-105"
            style={{ backgroundImage: `url('/hero/sunrise-hero.jpg')` }}
          />
          {/* Multi-layered gradient veil for text legibility and brand warmth */}
          <div className="absolute inset-0 bg-[#FFFDF9]/90 dark:bg-[#0E0C1C]/92 md:bg-gradient-to-b md:from-[#FFFDF9]/92 md:via-[#FFFDF9]/85 md:to-[#FFFDF9] md:dark:from-[#0E0C1C]/92 md:dark:via-[#0E0C1C]/88 md:dark:to-[#0E0C1C]" />
          <div className="absolute inset-0 bg-gradient-to-r from-[#E0A526]/15 via-transparent to-[#F28C6B]/20" />
        </div>

        {/* Ambient floating orbs */}
        <div className="absolute -top-32 right-1/4 w-96 h-96 bg-[#F28C6B]/20 rounded-full blur-3xl pointer-events-none -z-10 breathe-orb" />
        <div className="absolute -bottom-24 left-1/4 w-96 h-96 bg-[#E0A526]/20 rounded-full blur-3xl pointer-events-none -z-10 breathe-orb" />

        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
          {/* Eyebrow badge */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/80 dark:bg-white/10 backdrop-blur-md border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#C68C14] dark:text-[#F2C14E] shadow-sm mb-6 animate-fade-up">
            <Sparkles size={14} /> El Portal de la Alegría · Actitud Mental Positiva
          </div>

          <h1 className="font-serif text-4xl sm:text-6xl md:text-7xl font-extrabold tracking-tight text-[#1E1A17] dark:text-[#F6F3EE] leading-[1.1] mb-6 max-w-4xl mx-auto">
            Transforma tu mente, <br className="hidden sm:inline" />
            <span className="gradient-text">un día a la vez.</span>
          </h1>

          <p className="text-lg sm:text-xl md:text-2xl text-[#5C544D] dark:text-[#B4ACC5] max-w-3xl mx-auto leading-relaxed mb-10 font-normal">
            La profundidad transformadora del coaching de vida y la serenidad diaria de la meditación guiada en español. Sin algoritmos fríos: guiado por mentores reales que caminan a tu lado.
          </p>

          {/* Action buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
            <Link
              href="/onboarding"
              className="w-full sm:w-auto px-8 py-4 rounded-full bg-gradient-to-r from-[#E0A526] via-[#F28C6B] to-[#E0A526] bg-[length:200%_auto] hover:bg-right text-white font-bold text-base shadow-xl shadow-[#E0A526]/30 hover:scale-105 active:scale-95 transition-all duration-300 no-underline inline-flex items-center justify-center gap-2"
            >
              Comienza tu Camino Gratis <ArrowRight size={18} />
            </Link>

            <button
              onClick={() => playTrack(featuredTrack)}
              className="w-full sm:w-auto px-7 py-4 rounded-full bg-white/90 dark:bg-white/10 backdrop-blur-md border border-[#E0A526]/40 hover:border-[#E0A526] text-[#1E1A17] dark:text-[#F6F3EE] font-bold text-base shadow-md hover:bg-[#E0A526]/10 transition-all duration-200 inline-flex items-center justify-center gap-3"
            >
              <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-[#E0A526] to-[#F28C6B] flex items-center justify-center text-white">
                <Play size={14} className="ml-0.5 fill-current" />
              </div>
              <span>Escuchar Meditación Destacada (5 min)</span>
            </button>
          </div>

          {/* ── DIRECT HERO CHECK-IN: ¿CÓMO TE SIENTES HOY? ── */}
          <div className="max-w-2xl mx-auto glass-card rounded-3xl p-6 sm:p-8 shadow-2xl border border-white/40 dark:border-white/10 text-left">
            <div className="flex items-center justify-between mb-4">
              <div>
                <span className="text-[11px] font-extrabold uppercase tracking-widest text-[#E0A526] block">
                  Práctica del Momento
                </span>
                <h2 className="font-serif text-xl sm:text-2xl font-bold text-[#1E1A17] dark:text-[#F6F3EE]">
                  ¿Cómo te sientes hoy?
                </h2>
              </div>
              <span className="text-xs px-3 py-1 rounded-full bg-black/5 dark:bg-white/10 text-[#5C544D] dark:text-[#B4ACC5] font-semibold">
                Sin registro previo
              </span>
            </div>

            <p className="text-xs sm:text-sm text-[#5C544D] dark:text-[#B4ACC5] mb-5">
              Elige tu estado interior actual y te recomendaremos la práctica sonora ideal para transformar tu energía en minutos:
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 mb-6">
              {MOOD_OPTIONS.map((mood) => {
                const isSelected = selectedMood === mood.key;
                return (
                  <button
                    key={mood.key}
                    onClick={() => handleMoodSelect(mood.key, mood.theme)}
                    className={`flex items-center gap-2.5 p-3 rounded-2xl border text-xs sm:text-sm font-semibold transition-all duration-200 ${
                      isSelected
                        ? 'border-[#E0A526] bg-[#E0A526]/15 text-[#C68C14] dark:text-[#F2C14E] shadow-sm scale-102'
                        : 'border-[#EFE6D8] dark:border-[#2B254E] hover:border-[#E0A526]/50 bg-white/60 dark:bg-white/5 text-[#1E1A17] dark:text-[#F6F3EE]'
                    }`}
                  >
                    <span className="text-lg">{mood.emoji}</span>
                    <span className="truncate">{mood.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Immediate recommendation preview */}
            {recommendedTrack && (
              <div className="p-4 rounded-2xl bg-gradient-to-r from-[#E0A526]/10 via-[#F28C6B]/10 to-transparent border border-[#E0A526]/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 animate-fade-up">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#E0A526] to-[#F28C6B] flex items-center justify-center text-white shrink-0">
                    <Sparkles size={18} />
                  </div>
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wider text-[#E0A526]">
                      Sugerencia para ti:
                    </p>
                    <p className="text-sm font-bold text-[#1E1A17] dark:text-[#F6F3EE]">
                      {recommendedTrack.title}
                    </p>
                    <p className="text-xs text-[#5C544D] dark:text-[#B4ACC5]">
                      Por {recommendedTrack.coach} · {recommendedTrack.durationLabel}
                    </p>
                  </div>
                </div>

                <button
                  onClick={() => playTrack(recommendedTrack)}
                  className="w-full sm:w-auto px-5 py-2.5 rounded-full bg-[#E0A526] hover:bg-[#C68C14] text-white text-xs font-bold uppercase tracking-wider flex items-center justify-center gap-2 shadow-md transition-colors"
                >
                  <Play size={14} className="fill-current" /> Reproducir Ahora
                </button>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── 2. SOCIAL PROOF & CREDIBILITY BAND ── */}
      <section className="py-10 bg-[#FDF8F0] dark:bg-[#141129] border-b border-[#EFE6D8] dark:border-[#2B254E]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p className="text-center text-xs font-bold uppercase tracking-widest text-[#5C544D] dark:text-[#B4ACC5] mb-6">
            Comunidad & Metodología Avalada en Toda Hispanoamérica
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
            {PRESS_LOGOS.map((item, idx) => (
              <div key={idx} className="p-3">
                <div className="font-serif font-bold text-base md:text-lg text-[#1E1A17] dark:text-[#F6F3EE]">
                  {item.name}
                </div>
                <div className="text-xs text-[#E0A526] font-semibold mt-0.5">
                  {item.desc}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 3. TEACHER-FORWARD ROSTER (Mindvalley Style) ── */}
      <section className="py-20 md:py-28 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#C68C14] dark:text-[#F2C14E] mb-3">
            <Users size={14} /> Equipo de Guías Oficiales
          </div>
          <h2 className="font-serif text-3xl sm:text-5xl font-bold text-[#1E1A17] dark:text-[#F6F3EE] mb-4">
            Aprende con Mentores con Experiencia Real de Vida
          </h2>
          <p className="text-base text-[#5C544D] dark:text-[#B4ACC5]">
            Cada uno de nuestros cuatro coaches aporta una maestría particular para acompañarte en cada estación de tu desarrollo personal.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          {COACHES.map((coach) => (
            <div
              key={coach.id}
              className="glass-card rounded-3xl overflow-hidden border border-[#EFE6D8] dark:border-[#2B254E] hover:border-[#E0A526]/50 shadow-lg hover:shadow-2xl transition-all duration-300 flex flex-col group"
            >
              {/* Photo with overlay & badge */}
              <div className="relative aspect-[4/5] overflow-hidden bg-gray-100 dark:bg-gray-800">
                <img
                  src={coach.photoLocal}
                  alt={`Fotografía oficial de ${coach.name}`}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
                <div className="absolute bottom-4 left-4 right-4 text-white">
                  <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-[#E0A526] text-white mb-1">
                    {coach.id === 'juan-diego' ? 'Fundador' : 'Mentora'}
                  </span>
                  <h3 className="font-serif text-xl font-bold leading-tight">
                    {coach.name}
                  </h3>
                  <p className="text-xs text-[#FFE3B3] font-medium line-clamp-1">
                    {coach.role}
                  </p>
                </div>
              </div>

              {/* Body */}
              <div className="p-5 flex-1 flex flex-col justify-between">
                <p className="text-xs text-[#5C544D] dark:text-[#B4ACC5] italic mb-4 line-clamp-2">
                  &ldquo;{coach.tagline}&rdquo;
                </p>

                <div className="space-y-3">
                  <div className="flex flex-wrap gap-1">
                    {coach.specialties.slice(0, 2).map((s, idx) => (
                      <span key={idx} className="text-[10px] px-2 py-0.5 rounded-md bg-black/5 dark:bg-white/10 text-[#1E1A17] dark:text-[#F6F3EE] font-medium">
                        {s}
                      </span>
                    ))}
                  </div>

                  <Link
                    href={`/conocenos#${coach.id}`}
                    className="w-full py-2.5 rounded-xl border border-[#E0A526]/40 hover:bg-[#E0A526] hover:text-white text-[#C68C14] dark:text-[#F2C14E] text-xs font-bold uppercase tracking-wider text-center block transition-all no-underline"
                  >
                    Ver Perfil & Biografía
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── 4. PROGRAMAS & RETOS (Mindvalley Course Cards) ── */}
      <section className="py-20 bg-[#FDF8F0] dark:bg-[#120F26] border-y border-[#EFE6D8] dark:border-[#2B254E]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row md:items-end justify-between mb-14">
            <div>
              <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#C68C14] dark:text-[#F2C14E] mb-3">
                <BookOpen size={14} /> Programas Estructurados
              </div>
              <h2 className="font-serif text-3xl sm:text-4xl md:text-5xl font-bold text-[#1E1A17] dark:text-[#F6F3EE]">
                Cursos & Retos de 21 Días
              </h2>
            </div>
            <Link
              href="/biblioteca"
              className="mt-4 md:mt-0 text-sm font-bold text-[#E0A526] hover:text-[#C68C14] inline-flex items-center gap-1 no-underline"
            >
              Explorar todo el catálogo <ArrowRight size={16} />
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {PROGRAMS.map((prog) => (
              <div
                key={prog.id}
                className="glass-card rounded-3xl overflow-hidden border border-[#EFE6D8] dark:border-[#2B254E] hover:border-[#E0A526] shadow-md hover:shadow-xl transition-all duration-300 flex flex-col group"
              >
                {/* Cover art */}
                <div className="relative aspect-video overflow-hidden">
                  <img
                    src={prog.coverImage}
                    alt={prog.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent" />
                  <div className="absolute top-3 left-3">
                    <span className="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-black/60 text-white backdrop-blur-md">
                      {prog.level}
                    </span>
                  </div>
                  <div className="absolute bottom-3 left-3 right-3 flex justify-between text-xs text-white font-medium">
                    <span className="flex items-center gap-1"><Clock size={12} /> {prog.durationWeeks} semanas</span>
                    <span className="flex items-center gap-1"><BookOpen size={12} /> {prog.lessonsCount} lecciones</span>
                  </div>
                </div>

                {/* Content */}
                <div className="p-5 flex-1 flex flex-col justify-between">
                  <div>
                    <p className="text-[11px] font-bold uppercase tracking-wider text-[#E0A526] mb-1">
                      Mentor: {prog.coach}
                    </p>
                    <h3 className="font-serif font-bold text-lg text-[#1E1A17] dark:text-[#F6F3EE] mb-2 leading-snug">
                      {prog.title}
                    </h3>
                    <p className="text-xs text-[#5C544D] dark:text-[#B4ACC5] line-clamp-2">
                      {prog.tagline}
                    </p>
                  </div>

                  <div className="pt-4 mt-4 border-t border-black/5 dark:border-white/5">
                    <Link
                      href="/membresia"
                      className="text-xs font-bold text-[#E0A526] hover:text-[#C68C14] flex items-center justify-between no-underline"
                    >
                      <span>Incluido en Membresía</span>
                      <ArrowRight size={14} />
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 5. BIBLIOTECA CATEGORIES TILES (Calm / Headspace photographic tiles) ── */}
      <section className="py-20 md:py-28 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#C68C14] dark:text-[#F2C14E] mb-3">
            <Compass size={14} /> Biblioteca Temática
          </div>
          <h2 className="font-serif text-3xl sm:text-5xl font-bold text-[#1E1A17] dark:text-[#F6F3EE] mb-4">
            Audios Guiados por Estado de Vida
          </h2>
          <p className="text-base text-[#5C544D] dark:text-[#B4ACC5]">
            Navega por las categorías sonoras diseñadas para sostener tu mente a lo largo de las horas del día y la noche.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {THEME_CATEGORIES.map((cat) => (
            <Link
              key={cat.key}
              href={`/biblioteca?tema=${cat.key}`}
              className="group relative rounded-3xl overflow-hidden aspect-[16/10] shadow-lg hover:shadow-2xl transition-all duration-300 no-underline"
            >
              {/* Background photo */}
              <img
                src={cat.image}
                alt={cat.title}
                className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
              />
              {/* Overlay Gradient */}
              <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent" />

              {/* Text */}
              <div className="absolute inset-0 p-6 flex flex-col justify-end text-white">
                <span className="text-[11px] font-extrabold uppercase tracking-widest text-[#FFE3B3] mb-1">
                  {cat.trackCount} prácticas grabadas
                </span>
                <h3 className="font-serif text-2xl font-bold mb-1 group-hover:text-[#FFE3B3] transition-colors">
                  {cat.title}
                </h3>
                <p className="text-xs text-gray-200 line-clamp-2">
                  {cat.description}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* ── 6. TESTIMONIOS CON AVATARES & HISTORIAS REALES ── */}
      <section className="py-20 bg-[#FDF8F0] dark:bg-[#120F26] border-t border-[#EFE6D8] dark:border-[#2B254E]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#C68C14] dark:text-[#F2C14E] mb-3">
              <Star size={14} /> Transformación Comprobada
            </div>
            <h2 className="font-serif text-3xl sm:text-4xl font-bold text-[#1E1A17] dark:text-[#F6F3EE] mb-3">
              Voces de Quienes Ya Viven con Alegría
            </h2>
            <p className="text-sm text-[#5C544D] dark:text-[#B4ACC5]">
              Personas y líderes que han integrado las micro-prácticas diarias de AMP en su rutina.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                quote: "El acompañamiento de Juan Diego me permitió desarmar el miedo al fracaso en mi empresa y liderar a mi equipo desde la calma y la convicción.",
                author: "Carlos E. Restrepo",
                role: "Empresario & Emprendedor",
                city: "Medellín, Colombia",
                avatar: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=200&auto=format&fit=crop&q=80",
              },
              {
                quote: "Los talleres de crianza con Andrea salvaron la relación con mis dos hijos adolescentes. Pasamos de las discusiones diarias a escucharnos con genuino amor.",
                author: "Marcela Domínguez",
                role: "Madre de familia y docente",
                city: "Bogotá, Colombia",
                avatar: "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=200&auto=format&fit=crop&q=80",
              },
              {
                quote: "Tras mi separación sentí que no quedaba nada de mí. Las sesiones y audios de sanación de Dericielo me devolvieron la sonrisa y el amor propio.",
                author: "Patricia Henao",
                role: "Arquitecta",
                city: "Miami, FL",
                avatar: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=200&auto=format&fit=crop&q=80",
              },
            ].map((t, idx) => (
              <div
                key={idx}
                className="glass-card rounded-3xl p-6 sm:p-8 border border-[#EFE6D8] dark:border-[#2B254E] flex flex-col justify-between shadow-md"
              >
                <div>
                  <div className="flex gap-1 text-[#E0A526] mb-4">
                    {[...Array(5)].map((_, i) => (
                      <Star key={i} size={16} className="fill-current" />
                    ))}
                  </div>
                  <p className="text-sm text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed italic mb-6">
                    &ldquo;{t.quote}&rdquo;
                  </p>
                </div>

                <div className="flex items-center gap-3 pt-4 border-t border-black/5 dark:border-white/5">
                  <img
                    src={t.avatar}
                    alt={t.author}
                    className="w-11 h-11 rounded-full object-cover ring-2 ring-[#E0A526]/30"
                  />
                  <div>
                    <p className="text-sm font-bold text-[#1E1A17] dark:text-[#F6F3EE]">
                      {t.author}
                    </p>
                    <p className="text-xs text-[#5C544D] dark:text-[#B4ACC5]">
                      {t.role} · {t.city}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 7. STICKY MOBILE CTA BANNER ── */}
      <div className="md:hidden fixed bottom-16 left-0 right-0 z-30 p-3 bg-white/95 dark:bg-[#14122B]/95 backdrop-blur-md border-t border-[#EFE6D8] dark:border-[#2B254E] shadow-lg flex items-center justify-between gap-3">
        <div className="text-left">
          <p className="text-xs font-bold text-[#1E1A17] dark:text-[#F6F3EE]">El Portal de la Alegría</p>
          <p className="text-[10px] text-[#E0A526] font-semibold">Prueba gratuita de 7 días</p>
        </div>
        <Link
          href="/onboarding"
          className="px-4 py-2 rounded-full bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-white text-xs font-bold uppercase tracking-wider no-underline shadow-md"
        >
          Empezar Gratis
        </Link>
      </div>

      {/* ── 8. FINAL CALL TO ACTION ── */}
      <section className="py-24 relative overflow-hidden bg-gradient-to-br from-[#14122B] via-[#1E1B3A] to-[#2B254E] text-white text-center">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 relative z-10">
          <div className="w-16 h-16 mx-auto rounded-3xl bg-gradient-to-tr from-[#E0A526] to-[#F28C6B] flex items-center justify-center mb-6 shadow-2xl breathe-orb">
            <Sparkles size={32} />
          </div>

          <h2 className="font-serif text-3xl sm:text-5xl md:text-6xl font-bold mb-6">
            Tu tranquilidad no puede esperar a que todo sea perfecto.
          </h2>
          <p className="text-base sm:text-xl text-[#B9B2C9] max-w-2xl mx-auto mb-10 leading-relaxed font-normal">
            Únete a la membresía de Actitud Mental Positiva hoy mismo. Empieza con 7 días sin costo y descubre el poder de una mente en paz.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/membresia"
              className="w-full sm:w-auto px-8 py-4 rounded-full bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-white font-bold text-base shadow-xl hover:scale-105 active:scale-95 transition-all no-underline"
            >
              Comenzar Membresía con 7 Días Gratis
            </Link>
            <Link
              href="/conocenos"
              className="w-full sm:w-auto px-7 py-4 rounded-full bg-white/10 hover:bg-white/20 border border-white/20 text-white font-bold text-base transition-all no-underline"
            >
              Conoce a los Mentores
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
