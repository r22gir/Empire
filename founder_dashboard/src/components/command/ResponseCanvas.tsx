'use client';
import { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check, ChevronUp, ChevronDown, ExternalLink } from 'lucide-react';

// Canvas sub-components
import { analyzeContent, shouldReanalyze, type AnalysisResult, type CanvasMode } from './canvas/ContentAnalyzer';
import AvatarDisplay from './canvas/AvatarDisplay';
import ChartCanvas from './canvas/ChartCanvas';
import MetricCard from './canvas/MetricCard';
import QuoteCallout from './canvas/QuoteCallout';
import ImageCanvas from './canvas/ImageCanvas';
import WebPreviewCanvas from './canvas/WebPreviewCanvas';
import DocumentCanvas from './canvas/DocumentCanvas';
import SplitCanvas from './canvas/SplitCanvas';
import CanvasTransition from './canvas/CanvasTransition';

/* ── Code Block with Copy + Collapse ────────────────────────── */
function CodeBlock({ children, className }: { children: string; className?: string }) {
  const [copied, setCopied] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const lang = className?.replace('language-', '') || '';
  const lines = children.split('\n');
  const isLong = lines.length > 20;

  const copy = () => {
    navigator.clipboard.writeText(children);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="relative group my-2 rounded-xl overflow-hidden" style={{ background: 'var(--elevated)', border: '1px solid var(--purple-border)' }}>
      <div className="flex items-center justify-between px-3 py-1" style={{ background: 'rgba(139,92,246,0.06)', borderBottom: '1px solid var(--purple-border)' }}>
        <span className="text-[9px] font-mono" style={{ color: 'var(--purple)' }}>{lang || 'code'}</span>
        <div className="flex gap-1">
          {isLong && (
            <button onClick={() => setCollapsed(!collapsed)} className="p-0.5" style={{ color: 'var(--text-muted)' }}>
              {collapsed ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
            </button>
          )}
          <button onClick={copy} className="p-0.5" style={{ color: copied ? '#22c55e' : 'var(--text-muted)' }}>
            {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
          </button>
        </div>
      </div>
      <pre className={`px-3 py-2 overflow-x-auto text-[12px] leading-relaxed font-mono ${collapsed ? 'max-h-10 overflow-hidden' : ''}`} style={{ color: '#c4b0ff', margin: 0 }}>
        <code>{children}</code>
      </pre>
    </div>
  );
}

/* ── Mode indicator badge ───────────────────────────────────── */
function ModeBadge({ mode }: { mode: CanvasMode }) {
  if (mode === 'avatar') return null;

  const labels: Record<string, string> = {
    chart: 'Chart',
    document: 'Document',
    web: 'Web',
    image: 'Image',
    split: 'Multi',
    presentation: 'Slides',
    media: 'Media',
    comms: 'Comms',
    workspace: 'Workspace',
  };

  const colors: Record<string, string> = {
    chart: 'var(--gold)',
    document: '#3b82f6',
    web: '#22D3EE',
    image: '#D946EF',
    split: 'var(--purple)',
    media: '#ef4444',
  };

  return (
    <span
      className="text-[8px] px-1.5 py-0.5 rounded-full font-medium"
      style={{
        background: `${colors[mode] || 'var(--gold)'}15`,
        color: colors[mode] || 'var(--gold)',
        border: `1px solid ${colors[mode] || 'var(--gold)'}30`,
      }}
    >
      {labels[mode] || mode}
    </span>
  );
}

/* ── Markdown Text Renderer (shared between modes) ──────────── */
function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="chat-markdown">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            const codeStr = String(children).replace(/\n$/, '');
            if (match || codeStr.includes('\n')) {
              return <CodeBlock className={className}>{codeStr}</CodeBlock>;
            }
            return <code className={className} {...props}>{children}</code>;
          },
          pre({ children }) {
            return <>{children}</>;
          },
          img({ src, alt }) {
            if (!src) return null;
            return (
              <ImageCanvas
                images={[{ src, alt: alt || undefined }]}
                inline
              />
            );
          },
          a({ href, children }) {
            const isImage = href && /\.(png|jpg|jpeg|gif|webp|svg)(\?.*)?$/i.test(href);
            if (isImage) {
              return <ImageCanvas images={[{ src: href, alt: String(children) }]} inline />;
            }
            return (
              <a href={href || '#'} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5">
                {children} <ExternalLink className="w-2.5 h-2.5 inline" />
              </a>
            );
          },
          table({ children }) {
            return (
              <div className="overflow-x-auto my-2">
                <table>{children}</table>
              </div>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

/* ── Main ResponseCanvas — Mode Orchestrator ────────────────── */
interface Props {
  content: string;
  isStreaming: boolean;
}

export default function ResponseCanvas({ content, isStreaming }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showScrollTop, setShowScrollTop] = useState(false);
  const userScrolled = useRef(false);
  const lastAnalyzed = useRef('');
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);

  /* ── Content analysis (runs during streaming) ─────────────── */
  useEffect(() => {
    if (!content) {
      setAnalysis(null);
      lastAnalyzed.current = '';
      return;
    }

    // During streaming, only re-analyze when significant changes occur
    if (isStreaming && !shouldReanalyze(lastAnalyzed.current, content)) {
      return;
    }

    const result = analyzeContent(content);
    setAnalysis(result);
    lastAnalyzed.current = content;
  }, [content, isStreaming]);

  // Force final analysis when streaming ends
  useEffect(() => {
    if (!isStreaming && content) {
      const result = analyzeContent(content);
      setAnalysis(result);
      lastAnalyzed.current = content;
    }
  }, [isStreaming, content]);

  /* ── Auto-scroll during streaming ─────────────────────────── */
  useEffect(() => {
    if (isStreaming && scrollRef.current && !userScrolled.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [isStreaming, content]);

  const handleScroll = useCallback(() => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const atBottom = scrollHeight - scrollTop - clientHeight < 50;
    userScrolled.current = !atBottom;
    setShowScrollTop(scrollTop > 200);
  }, []);

  useEffect(() => {
    if (isStreaming) userScrolled.current = false;
  }, [isStreaming]);

  const scrollToTop = () => {
    scrollRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  };

  /* ── Determine avatar state ───────────────────────────────── */
  const avatarState = useMemo(() => {
    if (!isStreaming && !content) return 'idle' as const;
    if (isStreaming && !content) return 'thinking' as const;
    if (isStreaming) return 'speaking' as const;
    return 'done' as const;
  }, [isStreaming, content]);

  const mode = analysis?.primaryMode || 'avatar';

  /* ── Render structured content above/below markdown ───────── */
  function renderStructuredContent() {
    if (!analysis) return null;

    const elements: React.ReactNode[] = [];

    // Metrics at the top
    if (analysis.metrics.length >= 2) {
      elements.push(<MetricCard key="metrics" metrics={analysis.metrics} />);
    }

    // Charts
    if (analysis.charts.length > 0) {
      elements.push(<ChartCanvas key="charts" charts={analysis.charts} inline />);
    }

    // Web previews
    if (analysis.webPreviews.length > 0) {
      elements.push(<WebPreviewCanvas key="web" previews={analysis.webPreviews} inline />);
    }

    // Standalone images (not inline markdown images)
    if (analysis.images.length > 1) {
      elements.push(<ImageCanvas key="images" images={analysis.images} inline />);
    }

    // Quotes
    if (analysis.quotes.length > 0) {
      elements.push(<QuoteCallout key="quotes" quotes={analysis.quotes} />);
    }

    return elements.length > 0 ? <div className="flex flex-col gap-3 mb-3">{elements}</div> : null;
  }

  /* ── Render the canvas ────────────────────────────────────── */
  return (
    <div className="relative flex-1 min-h-0">
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="h-full overflow-y-auto px-4 py-2"
      >
        {/* Empty state with avatar */}
        {!content && !isStreaming && (
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <AvatarDisplay state="idle" size="lg" />
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Ready. Type below to talk to MAX.
            </p>
          </div>
        )}

        {/* Thinking state */}
        {isStreaming && !content && (
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <AvatarDisplay state="thinking" size="lg" />
            <p className="text-sm animate-pulse" style={{ color: 'var(--purple)' }}>
              MAX is thinking...
            </p>
          </div>
        )}

        {/* Content rendering */}
        {content && (
          <CanvasTransition mode={mode}>
            <div>
              {/* Mode badge + avatar when in special modes */}
              {mode !== 'avatar' && (
                <div className="flex items-center gap-2 mb-3">
                  <AvatarDisplay state={avatarState} size="sm" />
                  <ModeBadge mode={mode} />
                </div>
              )}

              {/* Structured content (charts, metrics, previews) rendered above text */}
              {renderStructuredContent()}

              {/* Main markdown text */}
              <MarkdownContent content={content} />

              {/* Streaming cursor */}
              {isStreaming && <span className="streaming-cursor" />}
            </div>
          </CanvasTransition>
        )}
      </div>

      {/* Scroll-to-top button */}
      {showScrollTop && (
        <button
          onClick={scrollToTop}
          className="absolute bottom-3 right-3 w-7 h-7 rounded-full flex items-center justify-center transition"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-muted)', zIndex: 10 }}
        >
          <ChevronUp className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
