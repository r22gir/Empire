'use client';
import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  ChevronLeft, ChevronRight, Play, Pause, Presentation,
  Maximize, Minimize,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { AnalysisResult } from './ContentAnalyzer';
import ChartCanvas from './ChartCanvas';
import MetricCard from './MetricCard';
import ImageCanvas from './ImageCanvas';
import WebPreviewCanvas from './WebPreviewCanvas';

export interface Slide {
  title: string;
  content: string;
  type: 'text' | 'chart' | 'metrics' | 'image' | 'web' | 'mixed';
  /** Portion of the analysis relevant to this slide */
  analysisSlice?: Partial<AnalysisResult>;
}

interface Props {
  slides: Slide[];
  /** Auto-advance interval in ms (0 = manual only) */
  autoAdvance?: number;
  isStreaming?: boolean;
}

/**
 * Parse content into slides.
 * Splits on ## headings or --- dividers to create individual slides.
 */
export function parseSlides(content: string, analysis?: AnalysisResult): Slide[] {
  const slides: Slide[] = [];

  // Split on ## headings or --- horizontal rules
  const sections = content.split(/(?=^##\s)|(?=^---$)/m).filter(s => s.trim());

  if (sections.length <= 1) {
    // Not enough structure for slides — create a single slide
    return [{
      title: 'Overview',
      content: content,
      type: 'text',
    }];
  }

  for (const section of sections) {
    const trimmed = section.trim();
    if (trimmed === '---') continue;

    // Extract title from heading
    const headingMatch = trimmed.match(/^##\s+(.+)/m);
    const title = headingMatch ? headingMatch[1].trim() : 'Slide';
    const body = headingMatch ? trimmed.replace(/^##\s+.+\n?/, '').trim() : trimmed;

    // Determine slide type
    let type: Slide['type'] = 'text';
    if (/\|.+\|/.test(body) && /\|[\s:-]+\|/.test(body)) type = 'chart';
    else if (/\*\*[^*]+\*\*[:\s]+\$?[\d,]/.test(body)) type = 'metrics';
    else if (/!\[/.test(body)) type = 'image';
    else if (/https?:\/\//.test(body)) type = 'web';

    slides.push({ title, content: body, type });
  }

  return slides;
}

/**
 * Detect if content looks like a presentation / briefing.
 * Returns true if content has 3+ ## sections or explicit presentation markers.
 */
export function isPresentationContent(content: string): boolean {
  // Explicit markers
  if (/morning briefing|daily report|presentation|slide/i.test(content.slice(0, 200))) {
    return true;
  }

  // Count ## headings
  const headings = content.match(/^##\s+/gm);
  if (headings && headings.length >= 3) return true;

  // Count --- dividers
  const dividers = content.match(/^---$/gm);
  if (dividers && dividers.length >= 2) return true;

  return false;
}

export default function PresentationCanvas({ slides, autoAdvance = 0, isStreaming }: Props) {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [isPlaying, setIsPlaying] = useState(autoAdvance > 0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const total = slides.length;

  // Clamp index
  useEffect(() => {
    if (currentIdx >= slides.length) {
      setCurrentIdx(Math.max(0, slides.length - 1));
    }
  }, [slides.length, currentIdx]);

  // Auto-advance
  useEffect(() => {
    if (!isPlaying || autoAdvance <= 0 || isStreaming) return;
    const timer = setInterval(() => {
      setCurrentIdx(prev => {
        if (prev >= total - 1) { setIsPlaying(false); return prev; }
        return prev + 1;
      });
    }, autoAdvance);
    return () => clearInterval(timer);
  }, [isPlaying, autoAdvance, total, isStreaming]);

  const goNext = useCallback(() => {
    setCurrentIdx(prev => Math.min(prev + 1, total - 1));
  }, [total]);

  const goPrev = useCallback(() => {
    setCurrentIdx(prev => Math.max(prev - 1, 0));
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); goNext(); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); goPrev(); }
      if (e.key === 'Escape') setIsFullscreen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [goNext, goPrev]);

  if (slides.length === 0) return null;
  const slide = slides[currentIdx];

  const containerClass = isFullscreen
    ? 'fixed inset-0 z-50 flex flex-col'
    : 'flex flex-col rounded-xl overflow-hidden';

  return (
    <div
      className={containerClass}
      style={{
        background: 'var(--void)',
        border: isFullscreen ? 'none' : '1px solid var(--border)',
        minHeight: isFullscreen ? '100vh' : 350,
      }}
    >
      {/* Top bar */}
      <div
        className="flex items-center justify-between px-4 py-2 shrink-0"
        style={{ borderBottom: '1px solid var(--border)', background: 'var(--raised)' }}
      >
        <div className="flex items-center gap-2">
          <Presentation className="w-4 h-4" style={{ color: 'var(--gold)' }} />
          <span className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>
            {slide.title}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>
            {currentIdx + 1} / {total}
          </span>
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1 rounded hover:bg-white/5 transition"
            style={{ color: 'var(--text-muted)' }}
          >
            {isFullscreen ? <Minimize className="w-3.5 h-3.5" /> : <Maximize className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      {/* Slide content */}
      <div className="flex-1 overflow-auto px-6 py-4" style={{ minHeight: 0 }}>
        <div
          style={{
            opacity: 1,
            animation: 'slide-fade-in 0.3s ease',
          }}
          key={currentIdx}
        >
          {/* Render type-specific content */}
          {slide.type === 'chart' && slide.analysisSlice?.charts && (
            <ChartCanvas charts={slide.analysisSlice.charts} inline />
          )}
          {slide.type === 'metrics' && slide.analysisSlice?.metrics && (
            <MetricCard metrics={slide.analysisSlice.metrics} />
          )}
          {slide.type === 'image' && slide.analysisSlice?.images && (
            <ImageCanvas images={slide.analysisSlice.images} inline />
          )}
          {slide.type === 'web' && slide.analysisSlice?.webPreviews && (
            <WebPreviewCanvas previews={slide.analysisSlice.webPreviews} inline />
          )}

          {/* Always render markdown content */}
          <div className="chat-markdown mt-2" style={{ fontSize: isFullscreen ? 16 : 14 }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {slide.content}
            </ReactMarkdown>
          </div>
        </div>
      </div>

      {/* Bottom controls */}
      <div
        className="flex items-center justify-between px-4 py-2 shrink-0"
        style={{ borderTop: '1px solid var(--border)', background: 'var(--raised)' }}
      >
        {/* Navigation */}
        <div className="flex items-center gap-1">
          <button
            onClick={goPrev}
            disabled={currentIdx === 0}
            className="p-1.5 rounded-lg hover:bg-white/5 transition disabled:opacity-30"
            style={{ color: 'var(--text-secondary)' }}
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="p-1.5 rounded-lg hover:bg-white/10 transition"
            style={{ color: 'var(--gold)' }}
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>
          <button
            onClick={goNext}
            disabled={currentIdx >= total - 1}
            className="p-1.5 rounded-lg hover:bg-white/5 transition disabled:opacity-30"
            style={{ color: 'var(--text-secondary)' }}
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>

        {/* Progress dots */}
        <div className="flex items-center gap-1">
          {slides.map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrentIdx(i)}
              className="transition-all"
              style={{
                width: i === currentIdx ? 16 : 6,
                height: 6,
                borderRadius: 3,
                background: i === currentIdx ? 'var(--gold)' :
                            i < currentIdx ? 'var(--purple)' : 'var(--border)',
              }}
            />
          ))}
        </div>

        {/* Slide type label */}
        <span
          className="text-[9px] px-1.5 py-0.5 rounded-full font-medium"
          style={{
            background: 'var(--gold-pale)',
            color: 'var(--gold)',
            border: '1px solid var(--gold-border)',
          }}
        >
          {slide.type === 'chart' ? 'Data' :
           slide.type === 'metrics' ? 'KPIs' :
           slide.type === 'image' ? 'Visual' :
           slide.type === 'web' ? 'Web' : 'Text'}
        </span>
      </div>

      <style jsx>{`
        @keyframes slide-fade-in {
          from { opacity: 0; transform: translateX(20px); }
          to { opacity: 1; transform: translateX(0); }
        }
      `}</style>
    </div>
  );
}
