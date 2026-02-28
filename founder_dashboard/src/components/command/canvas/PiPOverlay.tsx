'use client';
import { useState, useRef, useCallback, useEffect } from 'react';
import { X, Maximize2, Minimize2, GripHorizontal } from 'lucide-react';
import { extractYoutubeId, extractVimeoId, type MediaItem } from './MediaController';

type Corner = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';

interface Props {
  item: MediaItem;
  onClose: () => void;
  onExpand: () => void;
}

const CORNER_POSITIONS: Record<Corner, { top?: number; bottom?: number; left?: number; right?: number }> = {
  'top-left':     { top: 60, left: 12 },
  'top-right':    { top: 60, right: 12 },
  'bottom-left':  { bottom: 80, left: 12 },
  'bottom-right': { bottom: 80, right: 12 },
};

const PIP_SIZES = { sm: { w: 240, h: 135 }, md: { w: 320, h: 180 }, lg: { w: 420, h: 236 } };

export default function PiPOverlay({ item, onClose, onExpand }: Props) {
  const [corner, setCorner] = useState<Corner>('bottom-right');
  const [size, setSize] = useState<'sm' | 'md' | 'lg'>('md');
  const [dragging, setDragging] = useState(false);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const dragStart = useRef({ x: 0, y: 0 });

  const dims = PIP_SIZES[size];

  // Snap to nearest corner when drag ends
  const snapToCorner = useCallback((x: number, y: number) => {
    const midX = window.innerWidth / 2;
    const midY = window.innerHeight / 2;
    const newCorner: Corner =
      x < midX
        ? (y < midY ? 'top-left' : 'bottom-left')
        : (y < midY ? 'top-right' : 'bottom-right');
    setCorner(newCorner);
    setPos(null);
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setDragging(true);
    const rect = containerRef.current?.getBoundingClientRect();
    if (rect) {
      dragStart.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    }
  }, []);

  useEffect(() => {
    if (!dragging) return;

    const handleMove = (e: MouseEvent) => {
      setPos({
        x: e.clientX - dragStart.current.x,
        y: e.clientY - dragStart.current.y,
      });
    };

    const handleUp = (e: MouseEvent) => {
      setDragging(false);
      snapToCorner(e.clientX, e.clientY);
    };

    window.addEventListener('mousemove', handleMove);
    window.addEventListener('mouseup', handleUp);
    return () => {
      window.removeEventListener('mousemove', handleMove);
      window.removeEventListener('mouseup', handleUp);
    };
  }, [dragging, snapToCorner]);

  // Cycle size on double-click
  const cycleSize = useCallback(() => {
    setSize(s => s === 'sm' ? 'md' : s === 'md' ? 'lg' : 'sm');
  }, []);

  // Render content
  function renderContent() {
    if (item.type === 'youtube') {
      const videoId = extractYoutubeId(item.url);
      if (videoId) {
        return (
          <iframe
            src={`https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1`}
            className="w-full h-full border-none rounded-b-xl"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            title="PiP"
          />
        );
      }
    }
    if (item.type === 'vimeo') {
      const vimeoId = extractVimeoId(item.url);
      if (vimeoId) {
        return (
          <iframe
            src={`https://player.vimeo.com/video/${vimeoId}?autoplay=1`}
            className="w-full h-full border-none rounded-b-xl"
            allow="autoplay; fullscreen; picture-in-picture"
            allowFullScreen
            title="PiP"
          />
        );
      }
    }
    if (item.type === 'video' || item.type === 'stream') {
      return (
        <video
          src={item.url}
          className="w-full h-full object-cover rounded-b-xl"
          autoPlay
          muted
          controls
        />
      );
    }
    // iframe fallback
    return (
      <iframe
        src={item.url}
        className="w-full h-full border-none rounded-b-xl"
        sandbox="allow-scripts allow-same-origin"
        title="PiP"
      />
    );
  }

  const posStyle: React.CSSProperties = pos
    ? { left: pos.x, top: pos.y, position: 'fixed' }
    : {
        position: 'fixed',
        ...CORNER_POSITIONS[corner],
        transition: dragging ? 'none' : 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      };

  return (
    <div
      ref={containerRef}
      className="z-50 rounded-xl overflow-hidden shadow-2xl"
      style={{
        ...posStyle,
        width: dims.w,
        height: dims.h + 28, // +28 for title bar
        border: '1px solid var(--gold-border)',
        boxShadow: '0 10px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(212,175,55,0.15)',
        cursor: dragging ? 'grabbing' : 'default',
      }}
    >
      {/* Title bar */}
      <div
        className="flex items-center justify-between px-2 py-1 cursor-grab active:cursor-grabbing"
        style={{ background: 'var(--void)', borderBottom: '1px solid var(--border)', height: 28 }}
        onMouseDown={handleMouseDown}
        onDoubleClick={cycleSize}
      >
        <div className="flex items-center gap-1.5 flex-1 min-w-0">
          <GripHorizontal className="w-3 h-3 shrink-0" style={{ color: 'var(--text-muted)' }} />
          <span className="text-[9px] truncate" style={{ color: 'var(--text-secondary)' }}>
            {item.title || 'PiP'}
          </span>
        </div>
        <div className="flex items-center gap-0.5 shrink-0">
          <button
            onClick={onExpand}
            className="p-0.5 rounded hover:bg-white/10 transition"
            style={{ color: 'var(--text-muted)' }}
            title="Expand"
          >
            <Maximize2 className="w-3 h-3" />
          </button>
          <button
            onClick={onClose}
            className="p-0.5 rounded hover:bg-red-500/20 transition"
            style={{ color: 'var(--text-muted)' }}
            title="Close"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div style={{ height: dims.h, background: '#000' }}>
        {renderContent()}
      </div>
    </div>
  );
}
