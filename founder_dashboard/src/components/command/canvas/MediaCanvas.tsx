'use client';
import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Play, Pause, Volume2, VolumeX, Maximize, Minimize,
  ExternalLink, SkipForward, SkipBack, PictureInPicture2,
  Gauge, List, RefreshCw, ArrowLeft, ArrowRight, Globe,
} from 'lucide-react';
import {
  extractYoutubeId, extractVimeoId, formatTime, PLAYBACK_SPEEDS,
  type MediaItem,
} from './MediaController';

interface Props {
  /** Media items to display */
  items: MediaItem[];
  /** Enable PiP toggle */
  onPipToggle?: (item: MediaItem) => void;
  /** Compact mode for inline rendering */
  inline?: boolean;
}

/* ── YouTube Embed Player ─────────────────────────────────────── */
function YouTubePlayer({ item, inline }: { item: MediaItem; inline?: boolean }) {
  const videoId = extractYoutubeId(item.url);
  if (!videoId) return null;

  const params = new URLSearchParams({
    autoplay: '0',
    rel: '0',
    modestbranding: '1',
  });
  if (item.timestamp) params.set('start', String(Math.floor(item.timestamp)));

  return (
    <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
      <div style={{ position: 'relative', paddingBottom: inline ? '45%' : '56.25%', height: 0 }}>
        <iframe
          src={`https://www.youtube-nocookie.com/embed/${videoId}?${params.toString()}`}
          style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 'none' }}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          title={item.title || 'YouTube video'}
        />
      </div>
      <MediaFooter item={item} />
    </div>
  );
}

/* ── Vimeo Embed Player ───────────────────────────────────────── */
function VimeoPlayer({ item, inline }: { item: MediaItem; inline?: boolean }) {
  const vimeoId = extractVimeoId(item.url);
  if (!vimeoId) return null;

  return (
    <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
      <div style={{ position: 'relative', paddingBottom: inline ? '45%' : '56.25%', height: 0 }}>
        <iframe
          src={`https://player.vimeo.com/video/${vimeoId}?badge=0&autopause=0`}
          style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 'none' }}
          allow="autoplay; fullscreen; picture-in-picture"
          allowFullScreen
          title={item.title || 'Vimeo video'}
        />
      </div>
      <MediaFooter item={item} />
    </div>
  );
}

/* ── HTML5 Video Player with Full Controls ────────────────────── */
function NativeVideoPlayer({ item, onPipToggle, inline }: {
  item: MediaItem;
  onPipToggle?: (item: MediaItem) => void;
  inline?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.8);
  const [muted, setMuted] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [showSpeed, setShowSpeed] = useState(false);
  const [loading, setLoading] = useState(true);

  const toggle = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) { v.play(); setPlaying(true); }
    else { v.pause(); setPlaying(false); }
  }, []);

  const seek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = parseFloat(e.target.value);
  }, []);

  const changeVolume = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const v = videoRef.current;
    if (!v) return;
    const vol = parseFloat(e.target.value);
    v.volume = vol;
    setVolume(vol);
    if (vol > 0) setMuted(false);
  }, []);

  const changeSpeed = useCallback((s: number) => {
    const v = videoRef.current;
    if (!v) return;
    v.playbackRate = s;
    setSpeed(s);
    setShowSpeed(false);
  }, []);

  const skip = useCallback((delta: number) => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = Math.max(0, Math.min(v.duration, v.currentTime + delta));
  }, []);

  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    const onTime = () => setCurrentTime(v.currentTime);
    const onDur = () => { setDuration(v.duration); setLoading(false); };
    const onEnd = () => setPlaying(false);
    const onWait = () => setLoading(true);
    const onCanPlay = () => setLoading(false);
    v.addEventListener('timeupdate', onTime);
    v.addEventListener('loadedmetadata', onDur);
    v.addEventListener('ended', onEnd);
    v.addEventListener('waiting', onWait);
    v.addEventListener('canplay', onCanPlay);
    return () => {
      v.removeEventListener('timeupdate', onTime);
      v.removeEventListener('loadedmetadata', onDur);
      v.removeEventListener('ended', onEnd);
      v.removeEventListener('waiting', onWait);
      v.removeEventListener('canplay', onCanPlay);
    };
  }, []);

  return (
    <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)', background: '#000' }}>
      {/* Video element */}
      <div className="relative cursor-pointer" onClick={toggle}>
        <video
          ref={videoRef}
          src={item.url}
          className="w-full"
          style={{ maxHeight: inline ? 300 : 450 }}
          preload="metadata"
        />
        {!playing && !loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/30">
            <div className="w-14 h-14 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
              <Play className="w-6 h-6 text-white ml-1" />
            </div>
          </div>
        )}
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/30">
            <RefreshCw className="w-6 h-6 text-white animate-spin" />
          </div>
        )}
      </div>

      {/* Controls bar */}
      <div className="px-3 py-2 space-y-1.5" style={{ background: 'var(--raised)' }}>
        {/* Progress bar */}
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-mono min-w-[40px]" style={{ color: 'var(--text-muted)' }}>
            {formatTime(currentTime)}
          </span>
          <input
            type="range"
            min={0}
            max={duration || 100}
            value={currentTime}
            onChange={seek}
            className="flex-1 h-1 appearance-none rounded-full cursor-pointer"
            style={{ background: `linear-gradient(to right, var(--gold) ${(currentTime / (duration || 1)) * 100}%, var(--border) 0%)` }}
          />
          <span className="text-[9px] font-mono min-w-[40px] text-right" style={{ color: 'var(--text-muted)' }}>
            {formatTime(duration)}
          </span>
        </div>

        {/* Controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1">
            <button onClick={() => skip(-10)} className="p-1 rounded hover:bg-white/5 transition" style={{ color: 'var(--text-secondary)' }}>
              <SkipBack className="w-3.5 h-3.5" />
            </button>
            <button onClick={toggle} className="p-1.5 rounded-lg hover:bg-white/10 transition" style={{ color: 'var(--gold)' }}>
              {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            </button>
            <button onClick={() => skip(10)} className="p-1 rounded hover:bg-white/5 transition" style={{ color: 'var(--text-secondary)' }}>
              <SkipForward className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex items-center gap-1.5">
            {/* Volume */}
            <button
              onClick={() => { setMuted(!muted); if (videoRef.current) videoRef.current.muted = !muted; }}
              className="p-1 rounded hover:bg-white/5 transition"
              style={{ color: 'var(--text-secondary)' }}
            >
              {muted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
            </button>
            <input
              type="range"
              min={0}
              max={1}
              step={0.05}
              value={muted ? 0 : volume}
              onChange={changeVolume}
              className="w-16 h-1 appearance-none rounded-full cursor-pointer"
              style={{ background: `linear-gradient(to right, var(--text-secondary) ${(muted ? 0 : volume) * 100}%, var(--border) 0%)` }}
            />

            {/* Speed */}
            <div className="relative">
              <button
                onClick={() => setShowSpeed(!showSpeed)}
                className="p-1 rounded hover:bg-white/5 transition text-[9px] font-mono"
                style={{ color: speed !== 1 ? 'var(--gold)' : 'var(--text-secondary)' }}
              >
                {speed}x
              </button>
              {showSpeed && (
                <div
                  className="absolute bottom-full right-0 mb-1 rounded-lg p-1 shadow-lg z-20"
                  style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
                >
                  {PLAYBACK_SPEEDS.map(s => (
                    <button
                      key={s}
                      onClick={() => changeSpeed(s)}
                      className="block w-full text-left px-2 py-0.5 text-[10px] rounded hover:bg-white/5 transition"
                      style={{ color: s === speed ? 'var(--gold)' : 'var(--text-secondary)' }}
                    >
                      {s}x
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* PiP */}
            {onPipToggle && (
              <button
                onClick={() => onPipToggle(item)}
                className="p-1 rounded hover:bg-white/5 transition"
                style={{ color: 'var(--text-secondary)' }}
                title="Picture-in-Picture"
              >
                <PictureInPicture2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>

      {item.title && <MediaFooter item={item} />}
    </div>
  );
}

/* ── iframe Embed (generic web content) ───────────────────────── */
function IframeEmbed({ item, inline }: { item: MediaItem; inline?: boolean }) {
  const [loading, setLoading] = useState(true);

  return (
    <div className="rounded-xl overflow-hidden flex flex-col" style={{ border: '1px solid var(--border)', height: inline ? 350 : 450 }}>
      {/* Browser bar */}
      <div className="flex items-center gap-2 px-3 py-1.5 shrink-0" style={{ background: 'var(--raised)', borderBottom: '1px solid var(--border)' }}>
        <Globe className="w-3 h-3 shrink-0" style={{ color: 'var(--text-muted)' }} />
        <div
          className="flex-1 text-[10px] font-mono truncate px-2 py-0.5 rounded"
          style={{ background: 'var(--elevated)', color: 'var(--text-secondary)' }}
        >
          {item.url}
        </div>
        <a
          href={item.url}
          target="_blank"
          rel="noreferrer"
          className="p-0.5 rounded hover:bg-white/5 transition"
          style={{ color: 'var(--text-muted)' }}
        >
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>

      {/* iframe */}
      <div className="flex-1 relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center" style={{ background: 'var(--elevated)' }}>
            <RefreshCw className="w-5 h-5 animate-spin" style={{ color: 'var(--text-muted)' }} />
          </div>
        )}
        <iframe
          src={item.url}
          className="w-full h-full border-none"
          onLoad={() => setLoading(false)}
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
          title={item.title || 'Embedded content'}
        />
      </div>
    </div>
  );
}

/* ── Shared footer ────────────────────────────────────────────── */
function MediaFooter({ item }: { item: MediaItem }) {
  return (
    <div className="px-3 py-1.5 flex items-center justify-between" style={{ background: 'var(--raised)', borderTop: '1px solid var(--border)' }}>
      <span className="text-[10px] font-medium truncate flex-1" style={{ color: 'var(--text-secondary)' }}>
        {item.title || item.url}
      </span>
      <a
        href={item.url}
        target="_blank"
        rel="noreferrer"
        className="text-[10px] flex items-center gap-1 hover:underline shrink-0 ml-2"
        style={{ color: 'var(--text-muted)' }}
      >
        Open <ExternalLink className="w-3 h-3" />
      </a>
    </div>
  );
}

/* ── Playlist sidebar ─────────────────────────────────────────── */
function PlaylistPanel({ items, activeIdx, onSelect }: {
  items: MediaItem[];
  activeIdx: number;
  onSelect: (idx: number) => void;
}) {
  if (items.length <= 1) return null;

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{ border: '1px solid var(--border)', maxHeight: 250 }}
    >
      <div className="px-3 py-1.5 flex items-center gap-1.5" style={{ background: 'var(--raised)', borderBottom: '1px solid var(--border)' }}>
        <List className="w-3 h-3" style={{ color: 'var(--gold)' }} />
        <span className="text-[10px] font-medium" style={{ color: 'var(--text-secondary)' }}>
          Playlist ({items.length})
        </span>
      </div>
      <div className="overflow-y-auto" style={{ maxHeight: 200 }}>
        {items.map((item, i) => (
          <button
            key={item.id}
            onClick={() => onSelect(i)}
            className="w-full flex items-center gap-2 px-3 py-1.5 text-left hover:bg-white/5 transition"
            style={{
              background: i === activeIdx ? 'rgba(212,175,55,0.08)' : 'transparent',
              borderBottom: '1px solid var(--border)',
            }}
          >
            {item.thumbnail ? (
              <img src={item.thumbnail} alt="" className="w-10 h-7 object-cover rounded shrink-0" />
            ) : (
              <div className="w-10 h-7 rounded bg-white/5 flex items-center justify-center shrink-0">
                <Play className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-[10px] truncate" style={{ color: i === activeIdx ? 'var(--gold)' : 'var(--text-secondary)' }}>
                {item.title || item.url}
              </p>
              <p className="text-[8px]" style={{ color: 'var(--text-muted)' }}>{item.type}</p>
            </div>
            {i === activeIdx && (
              <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: 'var(--gold)' }} />
            )}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ── Main MediaCanvas ─────────────────────────────────────────── */
export default function MediaCanvas({ items, onPipToggle, inline }: Props) {
  const [activeIdx, setActiveIdx] = useState(0);

  if (items.length === 0) return null;
  const current = items[activeIdx] || items[0];

  function renderPlayer(item: MediaItem) {
    switch (item.type) {
      case 'youtube':
        return <YouTubePlayer item={item} inline={inline} />;
      case 'vimeo':
        return <VimeoPlayer item={item} inline={inline} />;
      case 'video':
      case 'audio':
      case 'stream':
        return <NativeVideoPlayer item={item} onPipToggle={onPipToggle} inline={inline} />;
      case 'iframe':
        return <IframeEmbed item={item} inline={inline} />;
      default:
        return <IframeEmbed item={item} inline={inline} />;
    }
  }

  return (
    <div className={`flex flex-col gap-2 ${inline ? 'my-2' : ''}`}>
      {renderPlayer(current)}
      <PlaylistPanel items={items} activeIdx={activeIdx} onSelect={setActiveIdx} />
    </div>
  );
}
