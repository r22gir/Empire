'use client';
import { useState, useMemo } from 'react';
import {
  Terminal, Code2, Palette, FileText, Calendar,
  ChevronLeft, ChevronRight, Clock, MapPin,
  Plus, Copy, Check, Play, Square,
} from 'lucide-react';

/* ── Types ────────────────────────────────────────────────────── */

export type WorkspaceTab = 'code' | 'mockup' | 'quote' | 'calendar';

export interface CodeBlock {
  lang: string;
  code: string;
  filename?: string;
}

export interface TerminalOutput {
  command?: string;
  output: string;
  status: 'running' | 'success' | 'error';
}

export interface CalendarEvent {
  id: string;
  title: string;
  date: string;       // YYYY-MM-DD
  time?: string;       // HH:MM
  duration?: number;   // minutes
  type: 'install' | 'meeting' | 'delivery' | 'quote' | 'other';
  location?: string;
}

export interface QuoteLine {
  description: string;
  quantity: number;
  unitPrice: number;
}

export interface QuotePreview {
  customer: string;
  lines: QuoteLine[];
  subtotal: number;
  tax: number;
  total: number;
  status: 'draft' | 'sent' | 'accepted';
}

interface Props {
  /** Active tab (auto-detected if not specified) */
  tab?: WorkspaceTab;
  /** Code blocks from analysis */
  codeBlocks?: CodeBlock[];
  /** Terminal output lines */
  terminalOutput?: TerminalOutput[];
  /** Calendar events */
  events?: CalendarEvent[];
  /** Quote preview data */
  quote?: QuotePreview;
  /** Whether content is still streaming */
  isStreaming?: boolean;
}

/* ── Code/Terminal View ───────────────────────────────────────── */

function CodeTerminalView({ codeBlocks, terminalOutput, isStreaming }: {
  codeBlocks?: CodeBlock[];
  terminalOutput?: TerminalOutput[];
  isStreaming?: boolean;
}) {
  const [activeFile, setActiveFile] = useState(0);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [showTerminal, setShowTerminal] = useState(!!(terminalOutput && terminalOutput.length > 0));

  const blocks = codeBlocks || [];

  const copyCode = (idx: number) => {
    if (blocks[idx]) {
      navigator.clipboard.writeText(blocks[idx].code);
      setCopiedIdx(idx);
      setTimeout(() => setCopiedIdx(null), 1500);
    }
  };

  return (
    <div className="flex flex-col rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)', minHeight: 300 }}>
      {/* File tabs */}
      {blocks.length > 0 && (
        <div className="flex items-center gap-0.5 px-2 py-1 overflow-x-auto shrink-0" style={{ background: 'rgba(139,92,246,0.04)', borderBottom: '1px solid var(--border)' }}>
          {blocks.map((block, i) => (
            <button
              key={i}
              onClick={() => { setActiveFile(i); setShowTerminal(false); }}
              className="px-2.5 py-1 rounded-t text-[10px] font-mono whitespace-nowrap transition"
              style={{
                background: activeFile === i && !showTerminal ? 'var(--elevated)' : 'transparent',
                color: activeFile === i && !showTerminal ? 'var(--purple)' : 'var(--text-muted)',
                borderBottom: activeFile === i && !showTerminal ? '2px solid var(--purple)' : '2px solid transparent',
              }}
            >
              <Code2 className="w-3 h-3 inline mr-1" />
              {block.filename || `${block.lang || 'code'}`}
            </button>
          ))}
          {terminalOutput && terminalOutput.length > 0 && (
            <button
              onClick={() => setShowTerminal(true)}
              className="px-2.5 py-1 rounded-t text-[10px] font-mono whitespace-nowrap transition"
              style={{
                background: showTerminal ? 'var(--elevated)' : 'transparent',
                color: showTerminal ? '#22c55e' : 'var(--text-muted)',
                borderBottom: showTerminal ? '2px solid #22c55e' : '2px solid transparent',
              }}
            >
              <Terminal className="w-3 h-3 inline mr-1" />
              Terminal
            </button>
          )}
        </div>
      )}

      {/* Content area */}
      <div className="flex-1 overflow-auto" style={{ background: '#0d0d1a' }}>
        {showTerminal && terminalOutput ? (
          <div className="p-3 font-mono text-[11px] leading-relaxed space-y-2">
            {terminalOutput.map((line, i) => (
              <div key={i}>
                {line.command && (
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span style={{ color: '#22c55e' }}>$</span>
                    <span style={{ color: 'var(--text-primary)' }}>{line.command}</span>
                    {line.status === 'running' && isStreaming && (
                      <span className="animate-pulse text-[9px]" style={{ color: 'var(--gold)' }}>running</span>
                    )}
                  </div>
                )}
                <pre
                  className="whitespace-pre-wrap pl-4"
                  style={{
                    color: line.status === 'error' ? '#ef4444' :
                           line.status === 'success' ? '#22c55e' : 'var(--text-secondary)',
                    margin: 0,
                  }}
                >
                  {line.output}
                </pre>
              </div>
            ))}
            {isStreaming && (
              <div className="flex items-center gap-1.5">
                <span style={{ color: '#22c55e' }}>$</span>
                <span className="w-2 h-4 bg-green-400 animate-pulse" />
              </div>
            )}
          </div>
        ) : blocks.length > 0 ? (
          <div className="relative">
            <button
              onClick={() => copyCode(activeFile)}
              className="absolute top-2 right-2 p-1 rounded hover:bg-white/10 transition z-10"
              style={{ color: copiedIdx === activeFile ? '#22c55e' : 'var(--text-muted)' }}
            >
              {copiedIdx === activeFile ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
            <pre className="p-3 overflow-x-auto text-[11px] leading-relaxed font-mono" style={{ color: '#c4b0ff', margin: 0 }}>
              <code>{blocks[activeFile]?.code || ''}</code>
            </pre>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full py-12">
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No code content</p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Mockup Studio View ───────────────────────────────────────── */

function MockupStudioView() {
  return (
    <div
      className="rounded-xl flex flex-col items-center justify-center gap-4 py-12"
      style={{ border: '1px solid var(--border)', background: 'var(--raised)', minHeight: 300 }}
    >
      <div
        className="w-16 h-16 rounded-xl flex items-center justify-center"
        style={{ background: 'linear-gradient(135deg, rgba(217,70,239,0.15) 0%, rgba(212,175,55,0.15) 100%)', border: '1px solid rgba(217,70,239,0.2)' }}
      >
        <Palette className="w-8 h-8" style={{ color: '#D946EF' }} />
      </div>
      <div className="text-center">
        <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Mockup Studio</p>
        <p className="text-[10px] mt-1 max-w-xs" style={{ color: 'var(--text-muted)' }}>
          Upload photos, apply fabric renders, segment rooms — coming with CraftForge integration
        </p>
      </div>
      <div className="flex gap-2">
        {['Upload Photo', 'AI Segment', 'Apply Fabric'].map(action => (
          <button
            key={action}
            className="px-3 py-1.5 rounded-lg text-[10px] font-medium transition opacity-50 cursor-not-allowed"
            style={{ background: 'var(--elevated)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}
            disabled
          >
            {action}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ── Quote Builder Live View ──────────────────────────────────── */

function QuoteBuilderView({ quote }: { quote?: QuotePreview }) {
  if (!quote) {
    return (
      <div
        className="rounded-xl flex flex-col items-center justify-center gap-3 py-8"
        style={{ border: '1px solid var(--border)', background: 'var(--raised)' }}
      >
        <FileText className="w-8 h-8 opacity-30" style={{ color: 'var(--gold)' }} />
        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No quote in progress</p>
      </div>
    );
  }

  const statusColors: Record<string, string> = {
    draft: 'var(--text-muted)',
    sent: '#3b82f6',
    accepted: '#22c55e',
  };

  return (
    <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2" style={{ background: 'var(--raised)', borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4" style={{ color: 'var(--gold)' }} />
          <span className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>
            Quote for {quote.customer}
          </span>
        </div>
        <span
          className="text-[9px] px-1.5 py-0.5 rounded-full font-medium"
          style={{ background: `${statusColors[quote.status]}15`, color: statusColors[quote.status] }}
        >
          {quote.status.toUpperCase()}
        </span>
      </div>

      {/* Line items */}
      <div className="overflow-x-auto">
        <table className="w-full text-[11px]" style={{ color: 'var(--text-secondary)' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)' }}>
              <th className="px-4 py-1.5 text-left font-medium" style={{ color: 'var(--text-muted)' }}>Description</th>
              <th className="px-3 py-1.5 text-right font-medium" style={{ color: 'var(--text-muted)' }}>Qty</th>
              <th className="px-3 py-1.5 text-right font-medium" style={{ color: 'var(--text-muted)' }}>Unit Price</th>
              <th className="px-4 py-1.5 text-right font-medium" style={{ color: 'var(--text-muted)' }}>Total</th>
            </tr>
          </thead>
          <tbody>
            {quote.lines.map((line, i) => (
              <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                <td className="px-4 py-1.5">{line.description}</td>
                <td className="px-3 py-1.5 text-right">{line.quantity}</td>
                <td className="px-3 py-1.5 text-right">${line.unitPrice.toFixed(2)}</td>
                <td className="px-4 py-1.5 text-right font-medium" style={{ color: 'var(--text-primary)' }}>
                  ${(line.quantity * line.unitPrice).toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Totals */}
      <div className="px-4 py-2 space-y-1" style={{ background: 'var(--raised)', borderTop: '1px solid var(--border)' }}>
        <div className="flex justify-between text-[10px]" style={{ color: 'var(--text-muted)' }}>
          <span>Subtotal</span>
          <span>${quote.subtotal.toFixed(2)}</span>
        </div>
        <div className="flex justify-between text-[10px]" style={{ color: 'var(--text-muted)' }}>
          <span>Tax</span>
          <span>${quote.tax.toFixed(2)}</span>
        </div>
        <div className="flex justify-between text-xs font-bold pt-1" style={{ borderTop: '1px solid var(--border)', color: 'var(--gold)' }}>
          <span>Total</span>
          <span>${quote.total.toFixed(2)}</span>
        </div>
      </div>
    </div>
  );
}

/* ── Calendar View ────────────────────────────────────────────── */

function CalendarView({ events }: { events?: CalendarEvent[] }) {
  const [weekOffset, setWeekOffset] = useState(0);

  const days = useMemo(() => {
    const today = new Date();
    today.setDate(today.getDate() + weekOffset * 7);
    const startOfWeek = new Date(today);
    startOfWeek.setDate(today.getDate() - today.getDay());

    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(startOfWeek);
      d.setDate(startOfWeek.getDate() + i);
      return {
        date: d,
        dateStr: d.toISOString().split('T')[0],
        dayName: d.toLocaleDateString('en-US', { weekday: 'short' }),
        dayNum: d.getDate(),
        isToday: d.toDateString() === new Date().toDateString(),
      };
    });
  }, [weekOffset]);

  const eventsByDate = useMemo(() => {
    const map: Record<string, CalendarEvent[]> = {};
    (events || []).forEach(e => {
      if (!map[e.date]) map[e.date] = [];
      map[e.date].push(e);
    });
    return map;
  }, [events]);

  const typeColors: Record<string, string> = {
    install: '#D4AF37',
    meeting: '#8B5CF6',
    delivery: '#22c55e',
    quote: '#3b82f6',
    other: 'var(--text-muted)',
  };

  return (
    <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2" style={{ background: 'var(--raised)', borderBottom: '1px solid var(--border)' }}>
        <button
          onClick={() => setWeekOffset(w => w - 1)}
          className="p-1 rounded hover:bg-white/5 transition"
          style={{ color: 'var(--text-muted)' }}
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <div className="flex items-center gap-2">
          <Calendar className="w-3.5 h-3.5" style={{ color: 'var(--gold)' }} />
          <span className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>
            {days[0].date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
          </span>
          {weekOffset !== 0 && (
            <button
              onClick={() => setWeekOffset(0)}
              className="text-[9px] px-1.5 py-0.5 rounded hover:bg-white/5 transition"
              style={{ color: 'var(--gold)' }}
            >
              Today
            </button>
          )}
        </div>
        <button
          onClick={() => setWeekOffset(w => w + 1)}
          className="p-1 rounded hover:bg-white/5 transition"
          style={{ color: 'var(--text-muted)' }}
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Week grid */}
      <div className="grid grid-cols-7">
        {days.map(day => {
          const dayEvents = eventsByDate[day.dateStr] || [];
          return (
            <div
              key={day.dateStr}
              className="flex flex-col min-h-[90px] p-1.5"
              style={{
                borderRight: '1px solid var(--border)',
                borderBottom: '1px solid var(--border)',
                background: day.isToday ? 'rgba(212,175,55,0.04)' : 'transparent',
              }}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[9px] font-medium" style={{ color: 'var(--text-muted)' }}>
                  {day.dayName}
                </span>
                <span
                  className={`text-[10px] font-bold ${day.isToday ? 'w-5 h-5 rounded-full flex items-center justify-center' : ''}`}
                  style={{
                    color: day.isToday ? '#0a0a0a' : 'var(--text-secondary)',
                    background: day.isToday ? 'var(--gold)' : 'transparent',
                  }}
                >
                  {day.dayNum}
                </span>
              </div>
              <div className="space-y-0.5 flex-1">
                {dayEvents.map(evt => (
                  <div
                    key={evt.id}
                    className="px-1 py-0.5 rounded text-[8px] truncate cursor-default"
                    style={{
                      background: `${typeColors[evt.type] || 'var(--text-muted)'}15`,
                      color: typeColors[evt.type] || 'var(--text-muted)',
                      borderLeft: `2px solid ${typeColors[evt.type] || 'var(--text-muted)'}`,
                    }}
                    title={`${evt.time || ''} ${evt.title}${evt.location ? ` @ ${evt.location}` : ''}`}
                  >
                    {evt.time && <span className="font-mono mr-0.5">{evt.time}</span>}
                    {evt.title}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-3 px-3 py-1.5" style={{ background: 'var(--raised)', borderTop: '1px solid var(--border)' }}>
        {Object.entries(typeColors).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full" style={{ background: color }} />
            <span className="text-[8px] capitalize" style={{ color: 'var(--text-muted)' }}>{type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Tab Selector ─────────────────────────────────────────────── */

const TAB_CONFIG: { id: WorkspaceTab; icon: typeof Terminal; label: string; color: string }[] = [
  { id: 'code', icon: Terminal, label: 'Code', color: 'var(--purple)' },
  { id: 'mockup', icon: Palette, label: 'Mockup', color: '#D946EF' },
  { id: 'quote', icon: FileText, label: 'Quote', color: 'var(--gold)' },
  { id: 'calendar', icon: Calendar, label: 'Calendar', color: '#22D3EE' },
];

/* ── Main WorkspaceCanvas ─────────────────────────────────────── */

export default function WorkspaceCanvas({ tab, codeBlocks, terminalOutput, events, quote, isStreaming }: Props) {
  const autoTab = useMemo((): WorkspaceTab => {
    if (tab) return tab;
    if (codeBlocks && codeBlocks.length > 0) return 'code';
    if (terminalOutput && terminalOutput.length > 0) return 'code';
    if (quote) return 'quote';
    if (events && events.length > 0) return 'calendar';
    return 'code';
  }, [tab, codeBlocks, terminalOutput, quote, events]);

  const [activeTab, setActiveTab] = useState<WorkspaceTab>(autoTab);

  return (
    <div className="flex flex-col gap-2">
      {/* Tab bar */}
      <div className="flex items-center gap-1">
        {TAB_CONFIG.map(t => {
          const Icon = t.icon;
          const isActive = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-medium transition"
              style={{
                background: isActive ? `${t.color}15` : 'var(--elevated)',
                color: isActive ? t.color : 'var(--text-muted)',
                border: `1px solid ${isActive ? `${t.color}30` : 'var(--border)'}`,
              }}
            >
              <Icon className="w-3 h-3" />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      {activeTab === 'code' && (
        <CodeTerminalView codeBlocks={codeBlocks} terminalOutput={terminalOutput} isStreaming={isStreaming} />
      )}
      {activeTab === 'mockup' && <MockupStudioView />}
      {activeTab === 'quote' && <QuoteBuilderView quote={quote} />}
      {activeTab === 'calendar' && <CalendarView events={events} />}
    </div>
  );
}

/**
 * Detect workspace-related content in MAX response.
 */
export function isWorkspaceContent(content: string, hasCode: boolean, codeBlockCount: number): boolean {
  // Multiple code blocks suggest a workspace view
  if (codeBlockCount >= 2) return true;
  // Terminal output patterns
  if (/^\$\s+/m.test(content)) return true;
  // Build/compile output
  if (/(?:build|compile|deploy|npm|pip|cargo)\s+(?:success|fail|error|complete)/i.test(content)) return true;
  // Quote builder references
  if (/(?:quote|estimate)\s+(?:for|builder|preview)/i.test(content) && /\$[\d,]+/.test(content)) return true;
  // Calendar/schedule references
  if (/(?:schedule|calendar|appointments?|installs?)\s+(?:for|this|next)\s+(?:week|month|today)/i.test(content)) return true;

  return false;
}
