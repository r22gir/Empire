'use client';

import React from 'react';
import { useAudio } from '@/context/AudioContext';
import {
  Play, Pause, X, RotateCcw, RotateCw, ChevronUp, ChevronDown,
  Sparkles, Maximize2, Minimize2, FileText
} from 'lucide-react';

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function GlobalAudioPlayer() {
  const {
    currentTrack,
    isPlaying,
    elapsed,
    duration,
    playbackRate,
    isMinimized,
    isExpandedModal,
    togglePlay,
    seek,
    skip,
    setRate,
    setMinimized,
    setExpandedModal,
    closePlayer,
  } = useAudio();

  if (!currentTrack) return null;

  const progressPercent = duration > 0 ? (elapsed / duration) * 100 : 0;

  const cycleRate = () => {
    const rates = [1, 1.25, 1.5, 0.75];
    const nextIdx = (rates.indexOf(playbackRate) + 1) % rates.length;
    setRate(rates[nextIdx]);
  };

  return (
    <>
      {/* ── EXPANDED FULL IMMERSIVE MODAL (Mindvalley / Calm style) ── */}
      {isExpandedModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-hidden">
          {/* Blurred artwork background backdrop */}
          <div
            className="absolute inset-0 bg-cover bg-center filter blur-3xl scale-125 opacity-35 dark:opacity-25"
            style={{ backgroundImage: `url('/hero/nature-calm.jpg')` }}
          />
          <div className="absolute inset-0 bg-black/60 backdrop-blur-xl" />

          {/* Modal Container */}
          <div className="relative z-10 glass-card bg-white/90 dark:bg-[#14122B]/90 border border-white/20 dark:border-white/10 rounded-3xl max-w-lg w-full p-6 sm:p-8 shadow-2xl animate-fade-up max-h-[92vh] overflow-y-auto">
            {/* Top Bar */}
            <div className="flex items-center justify-between mb-4">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#E0A526]/15 border border-[#E0A526]/30 text-[11px] font-bold tracking-widest uppercase text-[#C68C14] dark:text-[#F2C14E]">
                <Sparkles size={12} /> Práctica Guiada
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setExpandedModal(false)}
                  className="p-2 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-[#5C544D] dark:text-[#B4ACC5] transition-colors"
                  aria-label="Minimizar reproductor"
                  title="Minimizar"
                >
                  <Minimize2 size={18} />
                </button>
                <button
                  onClick={closePlayer}
                  className="p-2 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-[#5C544D] dark:text-[#B4ACC5] transition-colors"
                  aria-label="Cerrar reproductor"
                  title="Cerrar"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Glowing Breathing Visualizer */}
            <div className="flex flex-col items-center text-center my-6">
              <div className="relative w-44 h-44 sm:w-52 sm:h-52 rounded-full flex items-center justify-center mb-6">
                {/* Aura rings */}
                <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-[#E0A526] via-[#F28C6B] to-[#7E9F84] opacity-40 blur-xl breathe-orb" />
                <div className="relative w-full h-full rounded-full p-1 bg-gradient-to-tr from-[#E0A526] via-[#F28C6B] to-[#7E9F84] shadow-2xl breathe-orb flex items-center justify-center overflow-hidden">
                  <div className="w-full h-full rounded-full bg-[#FFFDF9] dark:bg-[#0E0C1C] flex flex-col items-center justify-center p-6 text-center">
                    <span className="text-3xl mb-1">🌿</span>
                    <span className="text-[10px] font-extrabold uppercase tracking-widest text-[#E0A526] mb-1">
                      {currentTrack.theme}
                    </span>
                    <span className="text-xs text-[#5C544D] dark:text-[#B4ACC5] font-medium">
                      {isPlaying ? "Respira conscientemente" : "En pausa"}
                    </span>
                  </div>
                </div>
              </div>

              <h2 className="font-serif text-2xl sm:text-3xl font-bold text-[#1E1A17] dark:text-[#F6F3EE] mb-2 leading-snug">
                {currentTrack.title}
              </h2>
              <p className="text-sm font-semibold text-[#E0A526] mb-3">
                Guía: {currentTrack.coach}
              </p>
              {currentTrack.description && (
                <p className="text-xs text-[#5C544D] dark:text-[#B4ACC5] max-w-md leading-relaxed">
                  {currentTrack.description}
                </p>
              )}
            </div>

            {/* Scrubbing Bar */}
            <div className="mb-4">
              <input
                type="range"
                min="0"
                max={duration || 100}
                value={elapsed}
                onChange={(e) => seek(Number(e.target.value))}
                className="w-full h-2.5 bg-black/10 dark:bg-white/10 rounded-lg appearance-none cursor-pointer accent-[#E0A526] transition-all"
                aria-label="Barra de avance del audio"
              />
              <div className="flex justify-between text-xs font-semibold text-[#5C544D] dark:text-[#B4ACC5] mt-2">
                <span>{formatTime(elapsed)}</span>
                <span>{formatTime(duration)}</span>
              </div>
            </div>

            {/* Playback Controls */}
            <div className="flex items-center justify-center gap-4 sm:gap-6 my-4">
              <button
                onClick={cycleRate}
                className="text-xs font-bold px-3 py-1.5 rounded-full bg-black/5 dark:bg-white/10 hover:bg-[#E0A526]/20 text-[#1E1A17] dark:text-[#F6F3EE] transition-all"
                title="Velocidad de reproducción"
              >
                {playbackRate}x
              </button>

              <button
                onClick={() => skip(-15)}
                className="p-3 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-[#1E1A17] dark:text-[#F6F3EE] transition-transform active:scale-90"
                aria-label="Retroceder 15 segundos"
                title="Retroceder 15s"
              >
                <RotateCcw size={22} />
              </button>

              <button
                onClick={togglePlay}
                className="w-16 h-16 rounded-full bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-white flex items-center justify-center shadow-xl shadow-[#E0A526]/30 hover:scale-105 active:scale-95 transition-all duration-200"
                aria-label={isPlaying ? 'Pausar' : 'Reproducir'}
              >
                {isPlaying ? <Pause size={28} /> : <Play size={28} className="ml-1" />}
              </button>

              <button
                onClick={() => skip(15)}
                className="p-3 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-[#1E1A17] dark:text-[#F6F3EE] transition-transform active:scale-90"
                aria-label="Adelantar 15 segundos"
                title="Adelantar 15s"
              >
                <RotateCw size={22} />
              </button>

              <button
                onClick={() => setExpandedModal(false)}
                className="p-3 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-[#5C544D] dark:text-[#B4ACC5] transition-colors"
                aria-label="Cerrar vista inmersiva"
                title="Volver a la barra"
              >
                <Minimize2 size={20} />
              </button>
            </div>

            {/* Transcript */}
            {currentTrack.transcript && (
              <div className="mt-6 pt-5 border-t border-black/10 dark:border-white/10 text-left">
                <div className="flex items-center gap-1.5 text-xs font-bold text-[#E0A526] mb-2 uppercase tracking-wider">
                  <FileText size={14} /> Transcripción completa
                </div>
                <div className="text-xs text-[#5C544D] dark:text-[#B4ACC5] leading-relaxed max-h-36 overflow-y-auto p-3.5 bg-black/[0.03] dark:bg-white/[0.04] rounded-2xl border border-black/5 dark:border-white/5">
                  {currentTrack.transcript}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── PERSISTENT DOCKED BOTTOM BAR ── */}
      <div
        className={`fixed left-0 right-0 z-40 transition-all duration-300 ${
          isMinimized
            ? 'bottom-20 md:bottom-6 px-4 flex justify-end pointer-events-none'
            : 'bottom-16 md:bottom-0 bg-white/95 dark:bg-[#17142E]/95 backdrop-blur-xl border-t border-[#EFE6D8] dark:border-[#2B254E] shadow-[0_-8px_30px_rgba(0,0,0,0.08)]'
        }`}
      >
        {isMinimized ? (
          /* Minimized pill floating button */
          <div className="pointer-events-auto glass-card bg-white dark:bg-[#1E1B3A] border-2 border-[#E0A526] rounded-full p-2 flex items-center gap-3 shadow-2xl animate-float">
            <button
              onClick={togglePlay}
              className="w-10 h-10 rounded-full bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-white flex items-center justify-center shadow-md"
              aria-label={isPlaying ? 'Pausar' : 'Reproducir'}
            >
              {isPlaying ? <Pause size={18} /> : <Play size={18} className="ml-0.5" />}
            </button>
            <div
              onClick={() => setMinimized(false)}
              className="cursor-pointer pr-2 text-left"
            >
              <p className="text-xs font-bold text-[#1E1A17] dark:text-[#F6F3EE] truncate max-w-[130px]">
                {currentTrack.title}
              </p>
              <p className="text-[10px] font-semibold text-[#E0A526]">{formatTime(elapsed)} / {formatTime(duration)}</p>
            </div>
            <button
              onClick={() => setMinimized(false)}
              className="p-1 text-[#5C544D] dark:text-[#B4ACC5] hover:text-[#E0A526]"
              title="Expandir barra"
            >
              <ChevronUp size={16} />
            </button>
          </div>
        ) : (
          /* Full bottom player bar */
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2.5">
            {/* Top slim progress bar */}
            <div
              onClick={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const clickPos = (e.clientX - rect.left) / rect.width;
                seek(clickPos * duration);
              }}
              className="relative w-full h-1.5 bg-black/10 dark:bg-white/10 rounded-full mb-2 overflow-hidden cursor-pointer group"
              title="Avanzar a este punto"
            >
              <div
                className="h-full bg-gradient-to-r from-[#E0A526] via-[#F28C6B] to-[#7E9F84] rounded-full transition-all"
                style={{ width: `${progressPercent}%` }}
              />
            </div>

            <div className="flex items-center justify-between gap-4">
              {/* Left track details */}
              <div
                onClick={() => setExpandedModal(true)}
                className="flex items-center gap-3 cursor-pointer min-w-0 flex-1 sm:flex-initial group"
                title="Abrir vista inmersiva"
              >
                <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-[#E0A526] to-[#F28C6B] flex items-center justify-center text-white shrink-0 shadow-md group-hover:scale-105 transition-transform">
                  <Sparkles size={20} className={isPlaying ? 'animate-spin' : ''} />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-bold text-[#1E1A17] dark:text-[#F6F3EE] truncate group-hover:text-[#E0A526] transition-colors">
                    {currentTrack.title}
                  </p>
                  <p className="text-xs text-[#5C544D] dark:text-[#B4ACC5] truncate flex items-center gap-1.5">
                    <span>{currentTrack.coach}</span>
                    <span>•</span>
                    <span className="capitalize text-[#E0A526] font-semibold">{currentTrack.theme}</span>
                  </p>
                </div>
              </div>

              {/* Center Controls */}
              <div className="flex items-center gap-2 sm:gap-4 shrink-0">
                <button
                  onClick={() => skip(-15)}
                  className="p-2 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-[#5C544D] dark:text-[#B4ACC5] transition-colors"
                  aria-label="Retroceder 15s"
                  title="Retroceder 15s"
                >
                  <RotateCcw size={18} />
                </button>

                <button
                  onClick={togglePlay}
                  className="w-11 h-11 rounded-full bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-white flex items-center justify-center shadow-lg hover:scale-105 active:scale-95 transition-all"
                  aria-label={isPlaying ? 'Pausar' : 'Reproducir'}
                >
                  {isPlaying ? <Pause size={20} /> : <Play size={20} className="ml-0.5" />}
                </button>

                <button
                  onClick={() => skip(15)}
                  className="p-2 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-[#5C544D] dark:text-[#B4ACC5] transition-colors"
                  aria-label="Adelantar 15s"
                  title="Adelantar 15s"
                >
                  <RotateCw size={18} />
                </button>

                <div className="hidden sm:block text-xs font-semibold text-[#5C544D] dark:text-[#B4ACC5] min-w-[75px] text-center">
                  {formatTime(elapsed)} / {formatTime(duration)}
                </div>
              </div>

              {/* Right Tools */}
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={cycleRate}
                  className="hidden sm:block text-xs font-bold px-2.5 py-1 rounded-full bg-black/5 dark:bg-white/10 text-[#1E1A17] dark:text-[#F6F3EE] hover:bg-[#E0A526]/20 transition-colors"
                  title="Velocidad"
                >
                  {playbackRate}x
                </button>

                <button
                  onClick={() => setExpandedModal(true)}
                  className="p-2 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-[#5C544D] dark:text-[#B4ACC5] transition-colors"
                  aria-label="Expandir modal inmersivo"
                  title="Modo Inmersivo"
                >
                  <Maximize2 size={18} />
                </button>

                <button
                  onClick={() => setMinimized(true)}
                  className="p-2 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-[#5C544D] dark:text-[#B4ACC5] transition-colors"
                  aria-label="Minimizar barra"
                  title="Minimizar a píldora"
                >
                  <ChevronDown size={18} />
                </button>

                <button
                  onClick={closePlayer}
                  className="p-2 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-[#5C544D] dark:text-[#B4ACC5] transition-colors"
                  aria-label="Cerrar reproductor"
                  title="Cerrar"
                >
                  <X size={18} />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
