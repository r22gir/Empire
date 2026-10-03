'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useAudio } from '@/context/AudioContext';
import { SAMPLE_TRACKS, COACHES } from '@/lib/amp-content';
import {
  Sparkles, Play, Search, Filter,
  Clock
} from 'lucide-react';

const THEMES = [
  { key: 'all', label: 'Todos los Temas' },
  { key: 'ansiedad', label: 'Ansiedad & Calma' },
  { key: 'sueño', label: 'Sueño Profundo' },
  { key: 'gratitud', label: 'Gratitud' },
  { key: 'autoestima', label: 'Autoestima' },
  { key: 'duelo', label: 'Duelo & Pérdida' },
  { key: 'liderazgo', label: 'Liderazgo' },
];

const DURATIONS = [
  { key: 'all', label: 'Cualquier duración' },
  { key: 'short', label: 'Rápida (≤ 5 min)' },
  { key: 'medium', label: 'Media (6 – 12 min)' },
  { key: 'deep', label: 'Profunda (> 12 min)' },
];

export default function BibliotecaPage() {
  const { playTrack, currentTrack, isPlaying } = useAudio();
  const [selectedTheme, setSelectedTheme] = useState('all');
  const [selectedCoach, setSelectedCoach] = useState('all');
  const [selectedDuration, setSelectedDuration] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredTracks = SAMPLE_TRACKS.filter((track) => {
    if (selectedTheme !== 'all' && track.theme !== selectedTheme) return false;
    if (selectedCoach !== 'all' && track.coachId !== selectedCoach) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const match = track.title.toLowerCase().includes(q) ||
        track.description.toLowerCase().includes(q) ||
        track.coach.toLowerCase().includes(q);
      if (!match) return false;
    }
    if (selectedDuration === 'short' && track.durationSeconds > 300) return false;
    if (selectedDuration === 'medium' && (track.durationSeconds <= 300 || track.durationSeconds > 720)) return false;
    if (selectedDuration === 'deep' && track.durationSeconds <= 720) return false;
    return true;
  });

  return (
    <div className="max-w-6xl mx-auto px-4 py-10 md:py-14">
      {/* ── HEADER ── */}
      <div className="text-center max-w-3xl mx-auto mb-10">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#B8860B] dark:text-[#F2C14E] mb-3">
          <Sparkles size={14} /> Biblioteca Temática
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl md:text-5xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-4">
          Meditaciones y Audios Guiados
        </h1>
        <p className="text-sm sm:text-base text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed">
          Encuentra la práctica sonora ideal para tu momento: respiración para la ansiedad, afirmaciones de merecimiento, meditación matutina y paisajes para dormir.
        </p>
      </div>

      {/* ── SEARCH & FILTER CONTROLS ── */}
      <div className="bg-white dark:bg-[#1E1B3A] p-4 sm:p-6 rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54] shadow-sm mb-10 space-y-4">
        {/* Search input */}
        <div className="relative">
          <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#6B625A] dark:text-[#B9B2C9]" />
          <input
            type="text"
            placeholder="Buscar por título, coach o palabra clave..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-11 pr-4 py-3 rounded-2xl bg-[#FFF9F1] dark:bg-[#14122B] border border-[#F0E6D8] dark:border-[#2E2A54] text-sm text-[#2B2622] dark:text-[#F4EFE8] focus:outline-none focus:border-[#E0A526]"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-black/5 dark:border-white/5">
          <span className="text-xs font-bold text-[#6B625A] dark:text-[#B9B2C9] mr-1 flex items-center gap-1">
            <Filter size={12} /> Tema:
          </span>
          {THEMES.map((theme) => (
            <button
              key={theme.key}
              onClick={() => setSelectedTheme(theme.key)}
              className={`text-xs font-semibold px-3 py-1.5 rounded-full transition-all ${
                selectedTheme === theme.key
                  ? 'bg-[#E0A526] text-white shadow-sm'
                  : 'bg-black/5 dark:bg-white/5 text-[#6B625A] dark:text-[#B9B2C9] hover:bg-black/10'
              }`}
            >
              {theme.label}
            </button>
          ))}
        </div>

        {/* Coach filter & Duration filter */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
          <div>
            <label className="text-xs font-semibold text-[#6B625A] dark:text-[#B9B2C9] block mb-1">
              Guía / Coach:
            </label>
            <select
              value={selectedCoach}
              onChange={(e) => setSelectedCoach(e.target.value)}
              className="w-full py-2 px-3 rounded-xl bg-[#FFF9F1] dark:bg-[#14122B] border border-[#F0E6D8] dark:border-[#2E2A54] text-xs font-medium text-[#2B2622] dark:text-[#F4EFE8]"
            >
              <option value="all">Todos los Coaches</option>
              {COACHES.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-[#6B625A] dark:text-[#B9B2C9] block mb-1">
              Duración de la práctica:
            </label>
            <select
              value={selectedDuration}
              onChange={(e) => setSelectedDuration(e.target.value)}
              className="w-full py-2 px-3 rounded-xl bg-[#FFF9F1] dark:bg-[#14122B] border border-[#F0E6D8] dark:border-[#2E2A54] text-xs font-medium text-[#2B2622] dark:text-[#F4EFE8]"
            >
              {DURATIONS.map((d) => (
                <option key={d.key} value={d.key}>{d.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* ── TRACKS LIST / GRID ── */}
      {filteredTracks.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-[#1E1B3A] rounded-3xl border border-[#F0E6D8] dark:border-[#2E2A54]">
          <p className="text-sm font-semibold text-[#6B625A] dark:text-[#B9B2C9] mb-3">
            No encontramos prácticas con los filtros seleccionados.
          </p>
          <button
            onClick={() => { setSelectedTheme('all'); setSelectedCoach('all'); setSelectedDuration('all'); setSearchQuery(''); }}
            className="text-xs font-bold text-[#E0A526] hover:underline"
          >
            Restablecer filtros
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-16">
          {filteredTracks.map((track) => {
            const isCurrentPlaying = currentTrack?.id === track.id && isPlaying;
            return (
              <div
                key={track.id}
                className="bg-white dark:bg-[#1E1B3A] rounded-3xl p-6 border border-[#F0E6D8] dark:border-[#2E2A54] shadow-sm flex flex-col justify-between hover:border-[#E0A526] transition-all group"
              >
                <div>
                  <div className="flex items-center justify-between text-xs mb-3">
                    <span className="font-bold px-2.5 py-0.5 rounded-full bg-[#E0A526]/15 text-[#B8860B] dark:text-[#F2C14E] uppercase tracking-wider">
                      {track.theme}
                    </span>
                    <span className="text-[#6B625A] dark:text-[#B9B2C9] font-medium flex items-center gap-1">
                      <Clock size={12} /> {track.durationLabel}
                    </span>
                  </div>

                  <h3 className="font-serif text-lg font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-2 group-hover:text-[#E0A526] transition-colors leading-snug">
                    {track.title}
                  </h3>

                  <p className="text-xs text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed mb-4 line-clamp-2">
                    {track.description}
                  </p>
                </div>

                <div className="pt-4 border-t border-[#F0E6D8] dark:border-[#2E2A54] flex items-center justify-between">
                  <span className="text-xs font-semibold text-[#6B625A] dark:text-[#B9B2C9]">
                    Por {track.coach}
                  </span>

                  <button
                    onClick={() => playTrack(track)}
                    className={`px-4 py-2 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-all shadow-sm ${
                      isCurrentPlaying
                        ? 'bg-[#7E9F84] text-white'
                        : 'bg-[#E0A526] hover:bg-[#B8860B] text-white hover:scale-105'
                    }`}
                  >
                    <Play size={13} className="fill-white" />
                    {isCurrentPlaying ? 'Sonando' : 'Escuchar'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── GATED PREMIUM BANNER ── */}
      <div className="bg-gradient-to-r from-[#FFE3B3]/40 via-[#FFF9F1] to-[#FAD4C0]/40 dark:from-[#1E1B3A] dark:to-[#14122B] p-8 rounded-3xl border border-[#E0A526]/30 text-center max-w-2xl mx-auto">
        <Sparkles size={28} className="text-[#E0A526] mx-auto mb-3" />
        <h3 className="font-serif text-2xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-2">
          Desbloquea el Catálogo Completo
        </h3>
        <p className="text-xs sm:text-sm text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed mb-6">
          Más de 50 pistas y series guiadas para cada momento del día están disponibles para miembros de El Portal de la Alegría.
        </p>
        <Link
          href="/membresia"
          className="inline-flex px-8 py-3 rounded-full bg-[#E0A526] hover:bg-[#B8860B] text-white font-bold text-xs uppercase tracking-wider shadow transition-all"
        >
          Ver Membresía con 7 Días Gratis
        </Link>
      </div>
    </div>
  );
}
