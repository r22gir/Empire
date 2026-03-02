'use client';
/**
 * MediaController — Universal media state management for canvas.
 * Provides shared state for play/pause, volume, speed, PiP, fullscreen
 * across MediaCanvas, PiPOverlay, and any media-playing component.
 */
import { createContext, useContext, useCallback, useRef } from 'react';

export interface MediaItem {
  id: string;
  type: 'youtube' | 'vimeo' | 'video' | 'audio' | 'iframe' | 'stream';
  url: string;
  title?: string;
  thumbnail?: string;
  duration?: number;
  timestamp?: number;  // Start at specific time
}

export interface MediaState {
  /** Currently active media item */
  current: MediaItem | null;
  /** Playlist queue */
  playlist: MediaItem[];
  /** Playback state */
  playing: boolean;
  /** Volume 0-1 */
  volume: number;
  /** Muted */
  muted: boolean;
  /** Playback speed */
  speed: number;
  /** Current time in seconds */
  currentTime: number;
  /** Total duration in seconds */
  duration: number;
  /** Is in PiP mode */
  pip: boolean;
  /** Is fullscreen */
  fullscreen: boolean;
  /** Is loading */
  loading: boolean;
}

export interface MediaActions {
  play: (item?: MediaItem) => void;
  pause: () => void;
  toggle: () => void;
  seek: (time: number) => void;
  setVolume: (vol: number) => void;
  toggleMute: () => void;
  setSpeed: (speed: number) => void;
  togglePip: () => void;
  toggleFullscreen: () => void;
  addToPlaylist: (item: MediaItem) => void;
  next: () => void;
  previous: () => void;
  clear: () => void;
  updateTime: (time: number, duration: number) => void;
  setLoading: (loading: boolean) => void;
}

export const DEFAULT_MEDIA_STATE: MediaState = {
  current: null,
  playlist: [],
  playing: false,
  volume: 0.8,
  muted: false,
  speed: 1,
  currentTime: 0,
  duration: 0,
  pip: false,
  fullscreen: false,
  loading: false,
};

export const MediaContext = createContext<{
  state: MediaState;
  actions: MediaActions;
} | null>(null);

export function useMedia() {
  const ctx = useContext(MediaContext);
  if (!ctx) {
    // Return a no-op version when outside provider
    return {
      state: DEFAULT_MEDIA_STATE,
      actions: {
        play: () => {},
        pause: () => {},
        toggle: () => {},
        seek: () => {},
        setVolume: () => {},
        toggleMute: () => {},
        setSpeed: () => {},
        togglePip: () => {},
        toggleFullscreen: () => {},
        addToPlaylist: () => {},
        next: () => {},
        previous: () => {},
        clear: () => {},
        updateTime: () => {},
        setLoading: () => {},
      } as MediaActions,
    };
  }
  return ctx;
}

/** Extract YouTube video ID from URL */
export function extractYoutubeId(url: string): string | null {
  const match = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]+)/);
  return match ? match[1] : null;
}

/** Extract Vimeo video ID from URL */
export function extractVimeoId(url: string): string | null {
  const match = url.match(/vimeo\.com\/(\d+)/);
  return match ? match[1] : null;
}

/** Classify a URL into a MediaItem */
export function urlToMediaItem(url: string, title?: string): MediaItem | null {
  const id = Math.random().toString(36).slice(2, 10);

  const youtubeId = extractYoutubeId(url);
  if (youtubeId) {
    return {
      id,
      type: 'youtube',
      url,
      title: title || `YouTube: ${youtubeId}`,
      thumbnail: `https://img.youtube.com/vi/${youtubeId}/mqdefault.jpg`,
    };
  }

  const vimeoId = extractVimeoId(url);
  if (vimeoId) {
    return { id, type: 'vimeo', url, title: title || `Vimeo: ${vimeoId}` };
  }

  if (/\.(mp4|webm|ogg|mov)(\?.*)?$/i.test(url)) {
    return { id, type: 'video', url, title: title || url.split('/').pop() || 'Video' };
  }

  if (/\.(mp3|wav|m4a|aac|flac|ogg)(\?.*)?$/i.test(url)) {
    return { id, type: 'audio', url, title: title || url.split('/').pop() || 'Audio' };
  }

  // Live streams
  if (/\.(m3u8|mpd)(\?.*)?$/i.test(url) || /rtsp:\/\//i.test(url)) {
    return { id, type: 'stream', url, title: title || 'Live Stream' };
  }

  return null;
}

/** Format seconds as MM:SS or HH:MM:SS */
export function formatTime(seconds: number): string {
  if (!seconds || !isFinite(seconds)) return '0:00';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

/** Available playback speeds */
export const PLAYBACK_SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 2];
