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
      {/* ── EXPANDED FULL MODAL ── */}
      {isExpandedModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-[#FFF9F1] dark:bg-[#1E1B3A] border border-[#E0A526]/30 rounded-3xl max-w-lg w-full p-6 shadow-2xl relative animate-fade-up max-h-[90vh] overflow-y-auto">
            <button
              onClick={() => setExpandedModal(false)}
              className="absolute top-4 right-4 p-2 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-[#6B625A] dark:text-[#B9B2C9]"
              aria-label="Cerrar modal"
            >
              <X size={20} />
            </button>

            {/* Glowing artwork / Breathing orb */}
            <div className="flex flex-col items-center text-center my-6">
              <div className="w-40 h-40 rounded-full bg-gradient-to-tr from-[#E0A526] via-[#F28C6B] to-[#7E9F84] p-1.5 shadow-xl shadow-[#E0A526]/20 mb-6 breathe-orb flex items-center justify-center">
                <div className="w-full h-full rounded-full bg-[#FFF9F1] dark:bg-[#14122B] flex flex-col items-center justify-center p-4">
                  <Sparkles className="text-[#E0A526] mb-1" size={28} />
                  <span className="text-xs uppercase tracking-wider font-semibold text-[#6B625A] dark:text-[#B9B2C9]">
                    {currentTrack.theme}
                  </span>
                </div>
              </div>

              <h2 className="font-serif text-2xl font-bold text-[#2B2622] dark:text-[#F4EFE8] mb-1">
                {currentTrack.title}
              </h2>
              <p className="text-sm text-[#E0A526] font-semibold mb-2">
                Guía: {currentTrack.coach}
              </p>
              {currentTrack.description && (
                <p className="text-xs text-[#6B625A] dark:text-[#B9B2C9] max-w-sm">
                  {currentTrack.description}
                </p>
              )}
            </div>

            {/* Progress Scrubbing */}
            <div className="mb-4">
              <input
                type="range"
                min="0"
                max={duration}
                value={elapsed}
                onChange={(e) => seek(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-[#E0A526]"
                aria-label="Progreso del audio"
              />
              <div className="flex justify-between text-xs text-[#6B625A] dark:text-[#B9B2C9] mt-1">
                <span>{formatTime(elapsed)}</span>
                <span>{formatTime(duration)}</span>
              </div>
            </div>

            {/* Controls */}
            <div className="flex items-center justify-center gap-6 my-4">
              <button
                onClick={cycleRate}
                className="text-xs font-bold px-2.5 py-1 rounded-full bg-black/5 dark:bg-white/10 text-[#2B2622] dark:text-[#F4EFE8]"
                title="Velocidad"
              >
                {playbackRate}x
              </button>

              <button
                onClick={() => skip(-15)}
                className="p-3 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-[#2B2622] dark:text-[#F4EFE8]"
                aria-label="Retroceder 15 segundos"
              >
                <RotateCcw size={22} />
              </button>

              <button
                onClick={togglePlay}
                className="w-16 h-16 rounded-full bg-gradient-to-r from-[#E0A526] to-[#F28C6B] text-white flex items-center justify-center shadow-lg hover:scale-105 transition-transform"
                aria-label={isPlaying ? 'Pausar' : 'Reproducir'}
              >
                {isPlaying ? <Pause size={28} /> : <Play size={28} className="ml-1" />}
              </button>

              <button
                onClick={() => skip(15)}
                className="p-3 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-[#2B2622] dark:text-[#F4EFE8]"
                aria-label="Adelantar 15 segundos"
              >
                <RotateCw size={22} />
              </button>

              <button
                onClick={() => setExpandedModal(false)}
                className="p-3 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-[#2B2622] dark:text-[#F4EFE8]"
                aria-label="Minimizar reproductor"
              >
                <Minimize2 size={20} />
              </button>
            </div>

            {/* Transcript if available */}
            {currentTrack.transcript && (
              <div className="mt-6 pt-4 border-t border-black/10 dark:border-white/10 text-left">
                <div className="flex items-center gap-1.5 text-xs font-bold text-[#E0A526] mb-2 uppercase">
                  <FileText size={14} /> Transcripción accesible
                </div>
                <div className="text-xs text-[#6B625A] dark:text-[#B9B2C9] leading-relaxed max-h-32 overflow-y-auto p-2 bg-black/5 dark:bg-white/5 rounded-xl">
                  {currentTrack.transcript}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── PERSISTENT BOTTOM BAR ── */}
      <div
        className={`fixed left-0 right-0 z-40 transition-all duration-300 ${
          isMinimized
            ? 'bottom-16 md:bottom-4 px-4 flex justify-end pointer-events-none'
            : 'bottom-16 md:bottom-0 bg-white/95 dark:bg-[#1E1B3A]/95 backdrop-blur-lg border-t border-[#F0E6D8] dark:border-[#2E2A54] shadow-[0_-8px_24px_rgba(0,0,0,0.06)]'
        }`}
      >
        {isMinimized ? (
          /* Minimized pill floating button */
          <div className="pointer-events-auto bg-[#FFF9F1] dark:bg-[#1E1B3A] border-2 border-[#E0A526] rounded-full p-2 flex items-center gap-3 shadow-xl">
            <button
              onClick={togglePlay}
              className="w-10 h-10 rounded-full bg-[#E0A526] text-white flex items-center justify-center"
              aria-label={isPlaying ? 'Pausar' : 'Reproducir'}
            >
              {isPlaying ? <Pause size={18} /> : <Play size={18} className="ml-0.5" />}
            </button>
            <div
              onClick={() => setMinimized(false)}
              className="cursor-pointer pr-2 text-left"
            >
              <p className="text-xs font-bold text-[#2B2622] dark:text-[#F4EFE8] truncate max-w-[120px]">
                {currentTrack.title}
              </p>
              <p className="text-[10px] text-[#E0A526]">{formatTime(elapsed)} / {formatTime(duration)}</p>
            </div>
            <button
              onClick={() => setMinimized(false)}
              className="p-1 text-[#6B625A] dark:text-[#B9B2C9]"
              title="Expandir"
            >
              <ChevronUp size={16} />
            </button>
          </div>
        ) : (
          /* Full bottom player bar */
          <div className="max-w-6xl mx-auto px-4 py-2.5">
            {/* Top slim progress bar for scrub */}
            <div className="relative w-full h-1 bg-black/10 dark:bg-white/10 rounded-full mb-2 overflow-hidden cursor-pointer group">
              <div
                className="h-full bg-gradient-to-r from-[#E0A526] to-[#F28C6B] rounded-full"
                style={{ width: `${progressPercent}%` }}
              />
            </div>

            <div className="flex items-center justify-between gap-3">
              {/* Left track details */}
              <div
                onClick={() => setExpandedModal(true)}
                className="flex items-center gap-3 cursor-pointer min-w-0 flex-1 sm:flex-initial"
              >
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#E0A526] to-[#F28C6B] flex items-center justify-center text-white shrink-0 shadow">
                  <Sparkles size={18} />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-bold text-[#2B2622] dark:text-[#F4EFE8] truncate">
                    {currentTrack.title}
                  </p>
                  <p className="text-xs text-[#6B625A] dark:text-[#B9B2C9] truncate">
                    {currentTrack.coach} · {currentTrack.theme}
                  </p>
                </div>
              </div>

              {/* Center Controls */}
              <div className="flex items-center gap-2 sm:gap-4 shrink-0">
                <button
                  onClick={() => skip(-15)}
                  className="p-1.5 sm:p-2 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-[#6B625A] dark:text-[#B9B2C9]"
                  aria-label="Retroceder 15s"
                >
                  <RotateCcw size={18} />
                </button>

                <button
                  onClick={togglePlay}
                  className="w-10 h-10 sm:w-11 sm:h-11 rounded-full bg-[#E0A526] hover:bg-[#B8860B] text-white flex items-center justify-center shadow-md transition-colors"
                  aria-label={isPlaying ? 'Pausar' : 'Reproducir'}
                >
                  {isPlaying ? <Pause size={20} /> : <Play size={20} className="ml-0.5" />}
                </button>

                <button
                  onClick={() => skip(15)}
                  className="p-1.5 sm:p-2 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-[#6B625A] dark:text-[#B9B2C9]"
                  aria-label="Adelantar 15s"
                >
                  <RotateCw size={18} />
                </button>

                <div className="hidden sm:block text-xs font-medium text-[#6B625A] dark:text-[#B9B2C9] ml-2 w-20 text-right">
                  {formatTime(elapsed)} / {formatTime(duration)}
                </div>
              </div>

              {/* Right secondary controls */}
              <div className="flex items-center gap-1 sm:gap-2 shrink-0">
                <button
                  onClick={cycleRate}
                  className="text-xs font-bold px-2 py-0.5 rounded bg-black/5 dark:bg-white/10 text-[#2B2622] dark:text-[#F4EFE8]"
                  title="Velocidad"
                >
                  {playbackRate}x
                </button>

                <button
                  onClick={() => setExpandedModal(true)}
                  className="p-1.5 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-[#6B625A] dark:text-[#B9B2C9]"
                  title="Pantalla completa"
                >
                  <Maximize2 size={16} />
                </button>

                <button
                  onClick={() => setMinimized(true)}
                  className="p-1.5 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-[#6B625A] dark:text-[#B9B2C9]"
                  title="Minimizar"
                >
                  <ChevronDown size={18} />
                </button>

                <button
                  onClick={closePlayer}
                  className="p-1.5 rounded-full hover:bg-black/5 dark:hover:bg-white/10 text-[#6B625A] dark:text-[#B9B2C9]"
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
