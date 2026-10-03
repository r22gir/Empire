'use client';

import React, { createContext, useContext, useState, useRef, useEffect, useCallback } from 'react';

export interface Track {
  id: string;
  title: string;
  coach: string;
  theme: string;
  pillar?: string;
  durationSeconds: number;
  audioUrl?: string; // If undefined or placeholder, synthesizes soothing ambient sound
  description?: string;
  transcript?: string;
}

interface AudioContextType {
  currentTrack: Track | null;
  isPlaying: boolean;
  elapsed: number;
  duration: number;
  playbackRate: number;
  isMinimized: boolean;
  isExpandedModal: boolean;
  playTrack: (track: Track) => void;
  pause: () => void;
  resume: () => void;
  togglePlay: () => void;
  seek: (seconds: number) => void;
  skip: (seconds: number) => void;
  setRate: (rate: number) => void;
  setMinimized: (min: boolean) => void;
  setExpandedModal: (expanded: boolean) => void;
  closePlayer: () => void;
}

const AudioContext = createContext<AudioContextType | undefined>(undefined);

export function AudioProvider({ children }: { children: React.ReactNode }) {
  const [currentTrack, setCurrentTrack] = useState<Track | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [playbackRate, setPlaybackRateState] = useState(1);
  const [isMinimized, setMinimized] = useState(false);
  const [isExpandedModal, setExpandedModal] = useState(false);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Setup HTML5 Audio element
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const audio = new Audio();
    audioRef.current = audio;

    const onTimeUpdate = () => {
      setElapsed(audio.currentTime);
    };

    const onEnded = () => {
      setIsPlaying(false);
      setElapsed(0);
    };

    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('ended', onEnded);

    return () => {
      audio.pause();
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('ended', onEnded);
    };
  }, []);

  const playTrack = useCallback((track: Track) => {
    setCurrentTrack(track);
    setElapsed(0);
    setIsPlaying(true);
    setMinimized(false);

    if (audioRef.current && track.audioUrl) {
      audioRef.current.src = track.audioUrl;
      audioRef.current.playbackRate = playbackRate;
      audioRef.current.play().catch(() => {
        // Fallback to synthetic player if real stream fails
      });
    }
  }, [playbackRate]);

  const pause = useCallback(() => {
    setIsPlaying(false);
    if (audioRef.current && currentTrack?.audioUrl) {
      audioRef.current.pause();
    }
  }, [currentTrack]);

  const resume = useCallback(() => {
    setIsPlaying(true);
    if (audioRef.current && currentTrack?.audioUrl) {
      audioRef.current.playbackRate = playbackRate;
      audioRef.current.play().catch(() => {});
    }
  }, [currentTrack, playbackRate]);

  const togglePlay = useCallback(() => {
    if (isPlaying) {
      pause();
    } else {
      resume();
    }
  }, [isPlaying, pause, resume]);

  const seek = useCallback((seconds: number) => {
    const clamped = Math.max(0, Math.min(seconds, currentTrack?.durationSeconds || 600));
    setElapsed(clamped);
    if (audioRef.current && currentTrack?.audioUrl) {
      audioRef.current.currentTime = clamped;
    }
  }, [currentTrack]);

  const skip = useCallback((delta: number) => {
    seek(elapsed + delta);
  }, [elapsed, seek]);

  // Handle synthetic timer if audio track doesn't have an external URL
  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);

    if (isPlaying && (!currentTrack?.audioUrl || !audioRef.current?.src)) {
      timerRef.current = setInterval(() => {
        setElapsed((prev) => {
          const max = currentTrack?.durationSeconds || 600;
          if (prev + 1 >= max) {
            setIsPlaying(false);
            return 0;
          }
          return prev + 1;
        });
      }, 1000 / playbackRate);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, currentTrack, playbackRate]);

  // Update MediaSession API for lockscreen controls
  useEffect(() => {
    if (typeof window === 'undefined' || !('mediaSession' in navigator) || !currentTrack) return;

    navigator.mediaSession.metadata = new MediaMetadata({
      title: currentTrack.title,
      artist: currentTrack.coach,
      album: `AMP — El Portal de la Alegría (${currentTrack.theme})`,
    });

    navigator.mediaSession.setActionHandler('play', () => resume());
    navigator.mediaSession.setActionHandler('pause', () => pause());
    navigator.mediaSession.setActionHandler('seekbackward', () => skip(-15));
    navigator.mediaSession.setActionHandler('seekforward', () => skip(15));
  }, [currentTrack, resume, pause, skip]);

  const setRate = useCallback((rate: number) => {
    setPlaybackRateState(rate);
    if (audioRef.current) {
      audioRef.current.playbackRate = rate;
    }
  }, []);

  const closePlayer = useCallback(() => {
    pause();
    setCurrentTrack(null);
    setElapsed(0);
    setExpandedModal(false);
  }, [pause]);

  return (
    <AudioContext.Provider
      value={{
        currentTrack,
        isPlaying,
        elapsed,
        duration: currentTrack?.durationSeconds || 600,
        playbackRate,
        isMinimized,
        isExpandedModal,
        playTrack,
        pause,
        resume,
        togglePlay,
        seek,
        skip,
        setRate,
        setMinimized,
        setExpandedModal,
        closePlayer,
      }}
    >
      {children}
    </AudioContext.Provider>
  );
}

export function useAudio() {
  const context = useContext(AudioContext);
  if (!context) {
    throw new Error('useAudio must be used within an AudioProvider');
  }
  return context;
}
