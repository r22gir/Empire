'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Play, Pause, X, ChevronUp, ChevronDown } from 'lucide-react';
import { PILLAR_CONFIG, type Pillar } from '@/lib/data';

interface AudioPlayerProps {
  title: string;
  description?: string;
  pillar?: string;
  audioUrl?: string;
  durationSeconds: number;
  contentText?: string;
  onClose: () => void;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function AudioPlayer({
  title,
  description,
  pillar,
  audioUrl,
  durationSeconds,
  contentText,
  onClose,
}: AudioPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [showContent, setShowContent] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const pillarConfig = pillar && pillar in PILLAR_CONFIG
    ? PILLAR_CONFIG[pillar as Pillar]
    : null;
  const pillarColor = pillarConfig?.color ?? '#D4A030';
  const pillarIcon = pillarConfig?.icon ?? '🌅';

  const progress = durationSeconds > 0 ? (elapsed / durationSeconds) * 100 : 0;

  const stop = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (audioRef.current) {
      audioRef.current.pause();
    }
  }, []);

  // Simulated playback timer (used when no audioUrl)
  useEffect(() => {
    if (!audioUrl && isPlaying) {
      intervalRef.current = setInterval(() => {
        setElapsed((prev) => {
          const next = prev + 1;
          if (next >= durationSeconds) {
            stop();
            setIsPlaying(false);
            // Auto-close after reaching end
            setTimeout(onClose, 1500);
            return durationSeconds;
          }
          return next;
        });
      }, 1000);
    } else if (!audioUrl && !isPlaying) {
      stop();
    }
    return () => stop();
  }, [isPlaying, audioUrl, durationSeconds, stop, onClose]);

  // Real audio playback
  useEffect(() => {
    if (audioUrl) {
      audioRef.current = new Audio(audioUrl);
      audioRef.current.addEventListener('timeupdate', () => {
        if (audioRef.current) setElapsed(audioRef.current.currentTime);
      });
      audioRef.current.addEventListener('ended', () => {
        setIsPlaying(false);
        setTimeout(onClose, 1500);
      });
    }
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, [audioUrl, onClose]);

  const togglePlay = () => {
    if (elapsed >= durationSeconds) return;
    if (audioUrl && audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
      } else {
        audioRef.current.play();
      }
    }
    setIsPlaying(!isPlaying);
  };

  const handleClose = () => {
    stop();
    setIsPlaying(false);
    onClose();
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 animate-fade-up">
      {/* Expandable content text section */}
      {contentText && showContent && (
        <div className="bg-white/95 backdrop-blur-md border-t border-gold-light/40 px-4 pt-4 pb-3 max-h-60 overflow-y-auto rounded-t-2xl shadow-lg mx-2 sm:mx-0">
          <p className="text-sm text-[#5C5650] leading-relaxed whitespace-pre-wrap">
            {contentText}
          </p>
        </div>
      )}

      {/* Player bar */}
      <div
        className={`bg-white border-t-2 shadow-[0_-4px_20px_rgba(0,0,0,0.08)] px-4 py-3 ${
          contentText && showContent ? '' : 'rounded-t-2xl'
        }`}
        style={{ borderTopColor: pillarColor }}
      >
        {/* No-audio notice */}
        {!audioUrl && (
          <p className="text-xs text-[#9B9590] text-center mb-2 italic">
            Meditaci&oacute;n guiada &mdash; lee el texto mientras meditas
          </p>
        )}

        {/* Progress bar */}
        <div className="relative w-full h-1.5 bg-sand rounded-full mb-3 overflow-hidden">
          <div
            className="absolute top-0 left-0 h-full rounded-full transition-all duration-700 ease-linear"
            style={{
              width: `${Math.min(progress, 100)}%`,
              background: `linear-gradient(90deg, ${pillarColor}, #D4A030)`,
            }}
          />
        </div>

        <div className="flex items-center gap-3">
          {/* Pillar indicator */}
          <div
            className="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center text-lg shadow-sm"
            style={{ backgroundColor: `${pillarColor}18` }}
          >
            {pillarIcon}
          </div>

          {/* Title & description */}
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-bold text-[#2D2A26] truncate">{title}</h4>
            {description && (
              <p className="text-xs text-[#9B9590] truncate">{description}</p>
            )}
          </div>

          {/* Time display */}
          <span className="text-xs font-mono text-[#9B9590] flex-shrink-0 tabular-nums">
            {formatTime(elapsed)} / {formatTime(durationSeconds)}
          </span>

          {/* Content toggle */}
          {contentText && (
            <button
              onClick={() => setShowContent(!showContent)}
              className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-[#9B9590] hover:text-gold-dark hover:bg-gold/10 transition-all"
              aria-label={showContent ? 'Ocultar texto' : 'Mostrar texto'}
            >
              {showContent ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
            </button>
          )}

          {/* Play / Pause */}
          <button
            onClick={togglePlay}
            disabled={elapsed >= durationSeconds}
            className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-white shadow-md transition-all active:scale-95 disabled:opacity-40"
            style={{
              background: `linear-gradient(135deg, ${pillarColor}, #D4A030)`,
            }}
            aria-label={isPlaying ? 'Pausar' : 'Reproducir'}
          >
            {isPlaying ? <Pause size={18} /> : <Play size={18} className="ml-0.5" />}
          </button>

          {/* Close */}
          <button
            onClick={handleClose}
            className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-[#9B9590] hover:text-red-400 hover:bg-red-50 transition-all"
            aria-label="Cerrar"
          >
            <X size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
