'use client';
import { useState, useEffect, useCallback } from 'react';
import { X, Printer, Download, Loader2, ExternalLink, ChevronDown, ChevronUp, Send } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts';
import { API_URL } from '@/lib/api';

const CHART_COLORS = ['#D4AF37', '#8B5CF6', '#22D3EE', '#D946EF', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4'];

interface PresentationSection {
  heading: string;
  content: string;
  type: 'text' | 'bullets' | 'highlight';
}

interface PresentationImage {
  url: string;
  alt: string;
  credit: string;
  credit_url?: string;
  unsplash_url?: string;
}

interface PresentationChart {
  title: string;
  type: 'bar' | 'line' | 'pie';
  headers: string[];
  rows: (string | number)[][];
}

interface PresentationSource {
  title: string;
  url: string;
  description: string;
}

interface PresentationVideo {
  title: string;
  url: string;
  thumbnail: string;
  duration: string;
  publisher: string;
}

interface PresentationData {
  title: string;
  subtitle: string;
  sections: PresentationSection[];
  images: PresentationImage[];
  videos: PresentationVideo[];
  charts: PresentationChart[];
  sources: PresentationSource[];
  model_used: string;
  generated_at: string;
}

interface Props {
  topic: string;
  sourceContent?: string;
  onClose: () => void;
}

export default function PresentationModal({ topic, sourceContent, onClose }: Props) {
  const [data, setData] = useState<PresentationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    (async () => {
      try {
        const res = await fetch(API_URL + '/max/present', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ topic, source_content: sourceContent }),
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`API ${res.status}`);
        const json = await res.json();
        setData(json);
      } catch (e: any) {
        if (e.name !== 'AbortError') setError(e.message || 'Failed to generate presentation');
      } finally {
        setLoading(false);
      }
    })();

    return () => controller.abort();
  }, [topic, sourceContent]);

  /* Escape key closes */
  useEffect(() => {
    const handle = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handle);
    return () => window.removeEventListener('keydown', handle);
  }, [onClose]);

  const [pdfLoading, setPdfLoading] = useState(false);
  const [tgLoading, setTgLoading] = useState(false);
  const [tgSent, setTgSent] = useState(false);

  /* Download as PDF */
  const handlePDF = useCallback(async () => {
    if (!data) return;
    setPdfLoading(true);
    try {
      const res = await fetch(API_URL + '/max/present/pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error(`PDF failed: ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${data.title.replace(/[^a-zA-Z0-9 ]/g, '').replace(/\s+/g, '-').toLowerCase()}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) { console.error('PDF download error:', e); }
    finally { setPdfLoading(false); }
  }, [data]);

  /* Send to Telegram */
  const handleTelegram = useCallback(async () => {
    if (!data) return;
    setTgLoading(true);
    try {
      const res = await fetch(API_URL + '/max/present/telegram', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!res.ok) throw new Error(`Telegram failed: ${res.status}`);
      const result = await res.json();
      if (result.telegram_sent) setTgSent(true);
    } catch (e) { console.error('Telegram send error:', e); }
    finally { setTgLoading(false); }
  }, [data]);

  /* Print / Export */
  const handlePrint = useCallback(() => {
    if (!data) return;
    const win = window.open('', '_blank');
    if (!win) return;
    win.document.write(`<!DOCTYPE html><html><head><title>${data.title}</title>
      <style>
        body { font-family: 'Segoe UI', system-ui, sans-serif; max-width: 900px; margin: 0 auto; padding: 40px; color: #1a1a2e; }
        h1 { color: #D4AF37; border-bottom: 2px solid #D4AF37; padding-bottom: 12px; }
        h2 { color: #8B5CF6; margin-top: 32px; }
        .highlight { background: #f5f0e1; border-left: 4px solid #D4AF37; padding: 16px; margin: 16px 0; border-radius: 4px; }
        .source { color: #666; font-size: 14px; margin: 4px 0; }
        .image-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin: 20px 0; }
        .image-grid img { width: 100%; border-radius: 8px; }
        .credit { font-size: 11px; color: #999; }
        .footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #ddd; font-size: 12px; color: #999; }
      </style>
    </head><body>
      <h1>${data.title}</h1>
      <p style="color: #666; font-size: 18px;">${data.subtitle}</p>
      ${data.sections.map(s =>
        s.type === 'highlight'
          ? `<div class="highlight"><h2>${s.heading}</h2><p>${s.content}</p></div>`
          : `<h2>${s.heading}</h2><div>${s.content.replace(/\n/g, '<br>')}</div>`
      ).join('')}
      ${data.images.length > 0 ? `<div class="image-grid">${data.images.map(img =>
        `<div><img src="${img.url}" alt="${img.alt}"><p class="credit">Photo by <a href="${img.credit_url || '#'}">${img.credit}</a> on <a href="${img.unsplash_url || 'https://unsplash.com/?utm_source=empirebox&utm_medium=referral'}">Unsplash</a></p></div>`
      ).join('')}</div>` : ''}
      ${data.sources.length > 0 ? `<h2>Sources</h2>${data.sources.map((s, i) =>
        `<p class="source">${i + 1}. <a href="${s.url}">${s.title}</a> — ${s.description}</p>`
      ).join('')}` : ''}
      <div class="footer">Generated by MAX AI · ${new Date(data.generated_at).toLocaleString()} · ${data.model_used}</div>
    </body></html>`);
    win.document.close();
    win.print();
  }, [data]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(5,5,13,0.92)' }}>
      <div
        className="w-full h-full max-w-5xl max-h-[95vh] mx-4 my-2 flex flex-col rounded-2xl overflow-hidden"
        style={{ background: 'var(--glass-bg-solid, #0a0a1a)', border: '1px solid var(--glass-border)' }}
      >
        {/* Header */}
        <div
          className="shrink-0 px-6 py-4 flex items-center justify-between"
          style={{
            background: 'linear-gradient(135deg, rgba(212,175,55,0.12) 0%, rgba(139,92,246,0.12) 100%)',
            borderBottom: '1px solid var(--glass-border)',
          }}
        >
          <div className="flex-1 min-w-0">
            {loading ? (
              <div className="flex items-center gap-3">
                <Loader2 className="w-5 h-5 animate-spin" style={{ color: 'var(--gold)' }} />
                <span className="text-sm" style={{ color: 'var(--gold)' }}>Generating presentation...</span>
              </div>
            ) : data ? (
              <>
                <h1 className="text-lg font-bold truncate" style={{ color: 'var(--gold)' }}>{data.title}</h1>
                <p className="text-xs mt-0.5 truncate" style={{ color: 'var(--text-secondary)' }}>{data.subtitle}</p>
              </>
            ) : null}
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg flex items-center justify-center ml-3 transition"
            style={{ color: 'var(--text-muted)', border: '1px solid var(--glass-border)' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.15)'; e.currentTarget.style.color = '#ef4444'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)'; }}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {loading && (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <div className="w-16 h-16 rounded-full flex items-center justify-center" style={{ background: 'linear-gradient(135deg, rgba(212,175,55,0.2) 0%, rgba(139,92,246,0.2) 100%)' }}>
                <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'var(--gold)' }} />
              </div>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>MAX is building your presentation on "{topic}"...</p>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center justify-center h-full gap-3">
              <p className="text-sm" style={{ color: '#ef4444' }}>Failed to generate presentation</p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{error}</p>
            </div>
          )}

          {data && (
            <div className="space-y-6 max-w-3xl mx-auto">
              {/* Sections */}
              {data.sections.map((section, i) => (
                <div key={i}>
                  {section.type === 'highlight' ? (
                    <div
                      className="rounded-xl p-5"
                      style={{
                        background: 'linear-gradient(135deg, rgba(212,175,55,0.08) 0%, rgba(139,92,246,0.08) 100%)',
                        border: '1px solid var(--gold-border, rgba(212,175,55,0.2))',
                      }}
                    >
                      <h2 className="text-sm font-bold mb-2" style={{ color: 'var(--gold)' }}>{section.heading}</h2>
                      <div className="text-sm leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{section.content}</ReactMarkdown>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <h2 className="text-sm font-bold mb-2" style={{ color: 'var(--purple)' }}>{section.heading}</h2>
                      <div className="text-sm leading-relaxed chat-markdown" style={{ color: 'var(--text-primary)' }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{section.content}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {/* Images */}
              {data.images.length > 0 && (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {data.images.map((img, i) => (
                    <div key={i} className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--glass-border)' }}>
                      <img src={img.url} alt={img.alt} className="w-full h-40 object-cover" loading="lazy" />
                      <p className="text-[10px] px-2 py-1 truncate" style={{ color: 'var(--text-muted)', background: 'var(--raised)' }}>
                        Photo by{' '}
                        <a href={img.credit_url || '#'} target="_blank" rel="noreferrer" style={{ color: 'var(--cyan)' }} className="hover:underline">
                          {img.credit}
                        </a>
                        {' on '}
                        <a href={img.unsplash_url || 'https://unsplash.com/?utm_source=empirebox&utm_medium=referral'} target="_blank" rel="noreferrer" style={{ color: 'var(--cyan)' }} className="hover:underline">
                          Unsplash
                        </a>
                      </p>
                    </div>
                  ))}
                </div>
              )}

              {/* Videos */}
              {data.videos?.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold mb-3 uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Video Clips</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {data.videos.map((vid, i) => (
                      <a
                        key={i}
                        href={vid.url}
                        target="_blank"
                        rel="noreferrer"
                        className="rounded-xl overflow-hidden flex gap-3 transition group"
                        style={{ background: 'var(--elevated)', border: '1px solid var(--glass-border)' }}
                      >
                        {vid.thumbnail && (
                          <div className="shrink-0 w-32 h-20 relative">
                            <img src={vid.thumbnail} alt={vid.title} className="w-full h-full object-cover" />
                            {vid.duration && (
                              <span className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded text-[9px] font-mono" style={{ background: 'rgba(0,0,0,0.8)', color: '#fff' }}>{vid.duration}</span>
                            )}
                          </div>
                        )}
                        <div className="py-2 pr-3 min-w-0 flex flex-col justify-center">
                          <p className="text-xs font-medium truncate group-hover:underline" style={{ color: 'var(--text-primary)' }}>{vid.title}</p>
                          {vid.publisher && <p className="text-[10px] mt-0.5" style={{ color: 'var(--text-muted)' }}>{vid.publisher}</p>}
                        </div>
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Charts */}
              {data.charts.map((chart, i) => (
                <PresentationChartBlock key={i} chart={chart} />
              ))}

              {/* Sources */}
              {data.sources.length > 0 && (
                <div className="pt-4" style={{ borderTop: '1px solid var(--glass-border)' }}>
                  <h3 className="text-xs font-bold mb-3 uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Sources</h3>
                  <div className="space-y-2">
                    {data.sources.map((source, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs">
                        <span className="shrink-0 font-mono" style={{ color: 'var(--gold)' }}>{i + 1}.</span>
                        <div className="min-w-0">
                          <a
                            href={source.url}
                            target="_blank"
                            rel="noreferrer"
                            className="font-medium inline-flex items-center gap-1 hover:underline"
                            style={{ color: 'var(--cyan)' }}
                          >
                            {source.title} <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                          <p className="mt-0.5" style={{ color: 'var(--text-secondary)' }}>{source.description}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        {data && (
          <div
            className="shrink-0 px-6 py-3 flex items-center justify-between"
            style={{ borderTop: '1px solid var(--glass-border)', background: 'var(--raised)' }}
          >
            <div className="flex items-center gap-2">
              <button
                onClick={handlePDF}
                disabled={pdfLoading}
                className="px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition"
                style={{ background: 'linear-gradient(135deg, rgba(212,175,55,0.15), rgba(139,92,246,0.15))', color: 'var(--gold)', border: '1px solid rgba(212,175,55,0.3)' }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold)'; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(212,175,55,0.3)'; }}
              >
                {pdfLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />} PDF
              </button>
              <button
                onClick={handleTelegram}
                disabled={tgLoading || tgSent}
                className="px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition"
                style={{ background: tgSent ? 'rgba(34,197,94,0.15)' : 'rgba(34,211,238,0.1)', color: tgSent ? '#22c55e' : 'var(--cyan)', border: `1px solid ${tgSent ? 'rgba(34,197,94,0.3)' : 'rgba(34,211,238,0.2)'}` }}
              >
                {tgLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />} {tgSent ? 'Sent' : 'Telegram'}
              </button>
              <button
                onClick={handlePrint}
                className="px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition"
                style={{ background: 'var(--elevated)', color: 'var(--text-secondary)', border: '1px solid var(--glass-border)' }}
                onMouseEnter={e => { e.currentTarget.style.color = 'var(--text-primary)'; }}
                onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-secondary)'; }}
              >
                <Printer className="w-3.5 h-3.5" /> Print
              </button>
            </div>
            <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>
              MAX AI · {data.model_used}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Chart renderer for presentation data ──────────────────── */
function PresentationChartBlock({ chart }: { chart: PresentationChart }) {
  const labelKey = chart.headers[0];
  const valueKeys = chart.headers.slice(1);

  const chartData = chart.rows.map(row => {
    const obj: Record<string, string | number> = {};
    chart.headers.forEach((h, i) => { obj[h] = row[i]; });
    return obj;
  });

  return (
    <div className="rounded-xl p-4" style={{ background: 'var(--elevated)', border: '1px solid var(--glass-border)' }}>
      <h3 className="text-xs font-bold mb-3" style={{ color: 'var(--gold)' }}>{chart.title}</h3>
      <ResponsiveContainer width="100%" height={220}>
        {chart.type === 'pie' ? (
          <PieChart>
            <Pie data={chartData} dataKey={valueKeys[0]} nameKey={labelKey} cx="50%" cy="50%" outerRadius={80} label>
              {chartData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
            </Pie>
            <Tooltip contentStyle={{ background: '#0a0a1a', border: '1px solid rgba(212,175,55,0.2)', borderRadius: 8, fontSize: 12, color: '#e4e4e8' }} />
            <Legend />
          </PieChart>
        ) : chart.type === 'line' ? (
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey={labelKey} tick={{ fill: '#888', fontSize: 11 }} />
            <YAxis tick={{ fill: '#888', fontSize: 11 }} />
            <Tooltip contentStyle={{ background: '#0a0a1a', border: '1px solid rgba(212,175,55,0.2)', borderRadius: 8, fontSize: 12, color: '#e4e4e8' }} />
            <Legend />
            {valueKeys.map((k, i) => <Line key={k} type="monotone" dataKey={k} stroke={CHART_COLORS[i % CHART_COLORS.length]} strokeWidth={2} dot={{ r: 3 }} />)}
          </LineChart>
        ) : (
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey={labelKey} tick={{ fill: '#888', fontSize: 11 }} />
            <YAxis tick={{ fill: '#888', fontSize: 11 }} />
            <Tooltip contentStyle={{ background: '#0a0a1a', border: '1px solid rgba(212,175,55,0.2)', borderRadius: 8, fontSize: 12, color: '#e4e4e8' }} />
            <Legend />
            {valueKeys.map((k, i) => <Bar key={k} dataKey={k} fill={CHART_COLORS[i % CHART_COLORS.length]} radius={[4, 4, 0, 0]} />)}
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
