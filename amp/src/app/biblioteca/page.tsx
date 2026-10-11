'use client';

import React, { useState } from 'react';
import { useAudio } from '@/context/AudioContext';
import { SAMPLE_TRACKS, COACHES, THEME_CATEGORIES } from '@/lib/amp-content';
import {
  Sparkles, Play, Pause, Search, Filter,
  Clock, Lock
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
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 md:py-16">
      {/* ── HEADER ── */}
      <div className="text-center max-w-3xl mx-auto mb-12">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-xs font-bold uppercase tracking-wider text-[#C68C14] dark:text-[#F2C14E] mb-3">
          <Sparkles size={14} /> Biblioteca Sonora Inmersiva
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl md:text-5xl font-bold text-[#1E1A17] dark:text-[#F6F3EE] mb-4">
          Meditaciones y Audios Guiados
        </h1>
        <p className="text-sm sm:text-base text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed">
          Encuentra la práctica sonora ideal para tu momento: respiración para la ansiedad, afirmaciones de merecimiento, meditación matutina y paisajes para dormir.
        </p>
      </div>

      {/* ── VISUAL THEME TILES (Calm / Headspace photographic category selector) ── */}
      <div className="mb-10">
        <p className="text-xs font-bold uppercase tracking-wider text-[#5C544D] dark:text-[#B4ACC5] mb-4">
          Explorar por ambiente temático:
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {THEME_CATEGORIES.map((cat) => {
            const isSelected = selectedTheme === cat.key;
            return (
              <button
                key={cat.key}
                onClick={() => setSelectedTheme(isSelected ? 'all' : cat.key)}
                className={`group relative rounded-2xl overflow-hidden aspect-[4/3] p-3 text-left flex flex-col justify-end transition-all ${
                  isSelected ? 'ring-4 ring-[#E0A526] scale-102' : 'hover:scale-102 opacity-85 hover:opacity-100'
                }`}
              >
                <img
                  src={cat.image}
                  alt={cat.title}
                  className="absolute inset-0 w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/40 to-transparent" />
                <div className="relative z-10 text-white">
                  <p className="text-[11px] font-bold leading-tight drop-shadow-sm">
                    {cat.title}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── SEARCH & FILTER CONTROLS ── */}
      <div className="glass-card p-5 sm:p-6 rounded-3xl border border-[#EFE6D8] dark:border-[#2B254E] shadow-sm mb-12 space-y-4">
        {/* Search input */}
        <div className="relative">
          <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#5C544D] dark:text-[#B4ACC5]" />
          <input
            type="text"
            placeholder="Buscar por título, coach o palabra clave..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-11 pr-4 py-3 rounded-2xl bg-[#FFFDF9] dark:bg-[#0E0C1C] border border-[#EFE6D8] dark:border-[#2B254E] text-sm text-[#1E1A17] dark:text-[#F6F3EE] focus:outline-none focus:border-[#E0A526]"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-black/5 dark:border-white/5">
          <span className="text-xs font-bold text-[#5C544D] dark:text-[#B4ACC5] mr-1 flex items-center gap-1">
            <Filter size={12} /> Filtro:
          </span>
          {THEMES.map((theme) => (
            <button
              key={theme.key}
              onClick={() => setSelectedTheme(theme.key)}
              className={`text-xs font-semibold px-3 py-1.5 rounded-full transition-all ${
                selectedTheme === theme.key
                  ? 'bg-[#E0A526] text-white shadow-sm'
                  : 'bg-black/5 dark:bg-white/5 text-[#5C544D] dark:text-[#B4ACC5] hover:bg-black/10'
              }`}
            >
              {theme.label}
            </button>
          ))}
        </div>

        {/* Coach filter & Duration filter */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
          <div>
            <label className="text-xs font-semibold text-[#5C544D] dark:text-[#B4ACC5] block mb-1">
              Guía / Coach:
            </label>
            <select
              value={selectedCoach}
              onChange={(e) => setSelectedCoach(e.target.value)}
              className="w-full py-2.5 px-3 rounded-xl bg-[#FFFDF9] dark:bg-[#0E0C1C] border border-[#EFE6D8] dark:border-[#2B254E] text-xs font-medium text-[#1E1A17] dark:text-[#F6F3EE]"
            >
              <option value="all">Todos los Coaches</option>
              {COACHES.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-[#5C544D] dark:text-[#B4ACC5] block mb-1">
              Duración de la práctica:
            </label>
            <select
              value={selectedDuration}
              onChange={(e) => setSelectedDuration(e.target.value)}
              className="w-full py-2.5 px-3 rounded-xl bg-[#FFFDF9] dark:bg-[#0E0C1C] border border-[#EFE6D8] dark:border-[#2B254E] text-xs font-medium text-[#1E1A17] dark:text-[#F6F3EE]"
            >
              {DURATIONS.map((d) => (
                <option key={d.key} value={d.key}>{d.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* ── TRACKS LIST / GRID WITH PHOTO COVERS ── */}
      {filteredTracks.length === 0 ? (
        <div className="text-center py-16 glass-card rounded-3xl border border-[#EFE6D8] dark:border-[#2B254E]">
          <p className="text-sm font-semibold text-[#5C544D] dark:text-[#B4ACC5] mb-3">
            No encontramos prácticas con los filtros seleccionados.
          </p>
          <button
            onClick={() => { setSelectedTheme('all'); setSelectedCoach('all'); setSelectedDuration('all'); setSearchQuery(''); }}
            className="text-xs font-bold text-[#E0A526] hover:underline"
          >
            Limpiar todos los filtros
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTracks.map((track) => {
            const isCurrentPlaying = currentTrack?.id === track.id && isPlaying;
            const isCurrentTrack = currentTrack?.id === track.id;

            return (
              <div
                key={track.id}
                className={`glass-card rounded-3xl overflow-hidden border transition-all duration-300 flex flex-col justify-between group ${
                  isCurrentTrack
                    ? 'border-[#E0A526] shadow-lg ring-2 ring-[#E0A526]/20'
                    : 'border-[#EFE6D8] dark:border-[#2B254E] hover:border-[#E0A526]/50 shadow-sm hover:shadow-xl'
                }`}
              >
                {/* Visual Cover Thumbnail */}
                <div className="relative aspect-[16/9] overflow-hidden">
                  <img
                    src={track.imageCover}
                    alt={track.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/20" />

                  <div className="absolute top-3 left-3">
                    <span className="text-[10px] font-extrabold px-2.5 py-1 rounded-full uppercase tracking-wider bg-black/60 text-[#FFE3B3] backdrop-blur-md">
                      {track.theme}
                    </span>
                  </div>

                  <div className="absolute bottom-3 left-3 right-3 flex justify-between items-center text-xs text-white">
                    <span className="flex items-center gap-1 font-medium">
                      <Clock size={12} /> {track.durationLabel}
                    </span>
                    {track.premium && (
                      <span className="flex items-center gap-1 text-[#FFE3B3] font-bold text-[10px] uppercase">
                        <Lock size={11} /> Premium
                      </span>
                    )}
                  </div>
                </div>

                {/* Content */}
                <div className="p-5 flex-1 flex flex-col justify-between">
                  <div>
                    <h3 className="font-serif text-lg font-bold text-[#1E1A17] dark:text-[#F6F3EE] mb-2 leading-snug group-hover:text-[#E0A526] transition-colors">
                      {track.title}
                    </h3>
                    <p className="text-xs text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed line-clamp-2 mb-4">
                      {track.description}
                    </p>
                  </div>

                  <div className="pt-4 border-t border-black/5 dark:border-white/5 flex items-center justify-between">
                    <div>
                      <p className="text-[10px] uppercase tracking-wider text-[#5C544D] dark:text-[#B4ACC5]">
                        Guía
                      </p>
                      <p className="text-xs font-bold text-[#1E1A17] dark:text-[#F6F3EE]">
                        {track.coach}
                      </p>
                    </div>

                    <button
                      onClick={() => playTrack(track)}
                      className={`px-4 py-2 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 shadow transition-all ${
                        isCurrentPlaying
                          ? 'bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-white shadow-lg animate-pulse'
                          : 'bg-[#E0A526] hover:bg-[#C68C14] text-white'
                      }`}
                    >
                      {isCurrentPlaying ? (
                        <>
                          <Pause size={14} /> Pausar
                        </>
                      ) : (
                        <>
                          <Play size={14} className="fill-current" /> Escuchar
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
