'use client';
import { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check, ChevronUp, ChevronDown, ExternalLink, BarChart3, X } from 'lucide-react';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';

/* ── Theme colors for charts ────────────────────────────────── */
const CHART_COLORS = ['#D4AF37', '#8B5CF6', '#22D3EE', '#D946EF', '#22c55e', '#f59e0b'];
const TOOLTIP_STYLE = {
  contentStyle: { background: '#0a0a1a', border: '1px solid rgba(212,175,55,0.2)', borderRadius: 8, fontSize: 12 },
  labelStyle: { color: '#D4AF37' },
};

/* ── Parse markdown table into chart data ───────────────────── */
function parseTableToChartData(raw: string): { headers: string[]; rows: Record<string, string | number>[] } | null {
  const lines = raw.trim().split('\n').filter(l => l.trim());
  if (lines.length < 3) return null;
  const headerLine = lines[0];
  const sepLine = lines[1];
  if (!sepLine.match(/^[\s|:-]+$/)) return null;
  const headers = headerLine.split('|').map(h => h.trim()).filter(Boolean);
  if (headers.length < 2) return null;
  const rows: Record<string, string | number>[] = [];
  for (let i = 2; i < lines.length; i++) {
    const cells = lines[i].split('|').map(c => c.trim()).filter(Boolean);
    if (cells.length < 2) continue;
    const row: Record<string, string | number> = {};
    headers.forEach((h, idx) => {
      const val = cells[idx] || '';
      const num = parseFloat(val.replace(/[,$%]/g, ''));
      row[h] = isNaN(num) ? val : num;
    });
    rows.push(row);
  }
  return rows.length > 0 ? { headers, rows } : null;
}

/* ── Inline Chart Component ─────────────────────────────────── */
function InlineChart({ data, headers }: { data: Record<string, string | number>[]; headers: string[] }) {
  const [chartType, setChartType] = useState<'bar' | 'line' | 'pie'>('bar');
  const [show, setShow] = useState(false);
  const labelKey = headers[0];
  const valueKeys = headers.slice(1).filter(h => data.some(d => typeof d[h] === 'number'));
  if (valueKeys.length === 0) return null;

  return (
    <div className="my-2">
      {!show ? (
        <button
          onClick={() => setShow(true)}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-medium transition"
          style={{ background: 'var(--gold-pale)', color: 'var(--gold)', border: '1px solid var(--gold-border)' }}
        >
          <BarChart3 className="w-3 h-3" /> View as chart
        </button>
      ) : (
        <div className="rounded-xl p-3" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex gap-1">
              {(['bar', 'line', 'pie'] as const).map(t => (
                <button
                  key={t}
                  onClick={() => setChartType(t)}
                  className="px-2 py-0.5 rounded text-[9px] font-medium transition"
                  style={{
                    background: chartType === t ? 'var(--gold)' : 'var(--elevated)',
                    color: chartType === t ? '#0a0a0a' : 'var(--text-muted)',
                  }}
                >
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>
            <button onClick={() => setShow(false)} className="p-0.5" style={{ color: 'var(--text-muted)' }}>
              <X className="w-3 h-3" />
            </button>
          </div>
          <div style={{ width: '100%', height: 180 }}>
            <ResponsiveContainer>
              {chartType === 'pie' ? (
                <PieChart>
                  <Pie
                    data={data}
                    dataKey={valueKeys[0]}
                    nameKey={labelKey}
                    cx="50%" cy="50%"
                    outerRadius={65}
                    label={({ name }) => name}
                    fontSize={10}
                  >
                    {data.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
                  </Pie>
                  <Tooltip {...TOOLTIP_STYLE} />
                </PieChart>
              ) : chartType === 'line' ? (
                <LineChart data={data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(212,175,55,0.08)" />
                  <XAxis dataKey={labelKey} tick={{ fill: '#8888A8', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#8888A8', fontSize: 10 }} />
                  <Tooltip {...TOOLTIP_STYLE} />
                  {valueKeys.map((k, i) => (
                    <Line key={k} type="monotone" dataKey={k} stroke={CHART_COLORS[i % CHART_COLORS.length]} strokeWidth={2} dot={{ r: 3 }} />
                  ))}
                </LineChart>
              ) : (
                <BarChart data={data}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(212,175,55,0.08)" />
                  <XAxis dataKey={labelKey} tick={{ fill: '#8888A8', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#8888A8', fontSize: 10 }} />
                  <Tooltip {...TOOLTIP_STYLE} />
                  {valueKeys.map((k, i) => (
                    <Bar key={k} dataKey={k} fill={CHART_COLORS[i % CHART_COLORS.length]} radius={[4, 4, 0, 0]} />
                  ))}
                </BarChart>
              )}
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}

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

/* ── Inline Image Preview ───────────────────────────────────── */
function InlineImage({ src, alt }: { src: string; alt?: string }) {
  const [expanded, setExpanded] = useState(false);
  const [error, setError] = useState(false);

  if (error) return null;

  return (
    <>
      <div
        className="my-2 inline-block rounded-xl overflow-hidden cursor-pointer transition"
        style={{ border: '1px solid var(--border)', maxWidth: '100%' }}
        onClick={() => setExpanded(true)}
      >
        <img
          src={src}
          alt={alt || ''}
          loading="lazy"
          onError={() => setError(true)}
          className="max-w-full rounded-xl"
          style={{ maxHeight: 300 }}
        />
        {alt && <p className="px-2 py-1 text-[10px]" style={{ color: 'var(--text-muted)', background: 'var(--raised)' }}>{alt}</p>}
      </div>
      {expanded && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 cursor-pointer"
          onClick={() => setExpanded(false)}
        >
          <img src={src} alt={alt || ''} className="max-w-[90vw] max-h-[90vh] object-contain rounded-xl" />
        </div>
      )}
    </>
  );
}

/* ── Table wrapper that detects chart-able data ─────────────── */
function TableWrapper({ children, raw }: { children: React.ReactNode; raw?: string }) {
  const chartData = raw ? parseTableToChartData(raw) : null;
  return (
    <>
      <div className="overflow-x-auto my-2">{children}</div>
      {chartData && <InlineChart data={chartData.rows} headers={chartData.headers} />}
    </>
  );
}

/* ── Main ResponseCanvas Component ──────────────────────────── */
interface Props {
  content: string;
  isStreaming: boolean;
}

export default function ResponseCanvas({ content, isStreaming }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showScrollTop, setShowScrollTop] = useState(false);
  const userScrolled = useRef(false);

  /* Auto-scroll during streaming */
  useEffect(() => {
    if (isStreaming && scrollRef.current && !userScrolled.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [isStreaming, content]);

  /* Detect manual scroll */
  const handleScroll = useCallback(() => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const atBottom = scrollHeight - scrollTop - clientHeight < 50;
    userScrolled.current = !atBottom;
    setShowScrollTop(scrollTop > 200);
  }, []);

  /* Reset scroll tracking on new stream */
  useEffect(() => {
    if (isStreaming) userScrolled.current = false;
  }, [isStreaming]);

  const scrollToTop = () => {
    scrollRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  };

  /* Extract raw table blocks for chart detection */
  const tableBlocks = useMemo(() => {
    const blocks: string[] = [];
    const regex = /(\|.+\|\n\|[\s|:-]+\|\n(?:\|.+\|\n?)+)/g;
    let match;
    while ((match = regex.exec(content)) !== null) {
      blocks.push(match[1]);
    }
    return blocks;
  }, [content]);

  let tableIndex = 0;

  return (
    <div className="relative flex-1 min-h-0">
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="h-full overflow-y-auto px-4 py-2"
      >
        {!content && !isStreaming && (
          <div className="flex flex-col items-center justify-center h-full gap-2">
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Ready. Type below to talk to MAX.</p>
          </div>
        )}

        {content && (
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
                  return src ? <InlineImage src={src} alt={alt || undefined} /> : null;
                },
                a({ href, children }) {
                  const isImage = href && /\.(png|jpg|jpeg|gif|webp|svg)(\?.*)?$/i.test(href);
                  if (isImage) {
                    return <InlineImage src={href} alt={String(children)} />;
                  }
                  return (
                    <a href={href || '#'} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5">
                      {children} <ExternalLink className="w-2.5 h-2.5 inline" />
                    </a>
                  );
                },
                table({ children }) {
                  const raw = tableBlocks[tableIndex] || undefined;
                  tableIndex++;
                  return <TableWrapper raw={raw}>{<table>{children}</table>}</TableWrapper>;
                },
              }}
            >
              {content}
            </ReactMarkdown>
            {isStreaming && <span className="streaming-cursor" />}
          </div>
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
