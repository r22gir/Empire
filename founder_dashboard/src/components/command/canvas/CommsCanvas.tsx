'use client';
import { useState, useMemo } from 'react';
import {
  Phone, PhoneOff, Video, VideoOff, Mic, MicOff, MonitorUp,
  MessageSquare, Send, Reply, Forward, Archive, User, Clock,
  ChevronDown, FileText, PenLine,
} from 'lucide-react';

/* ── Types ────────────────────────────────────────────────────── */

export interface CallInfo {
  contactName: string;
  contactPhone?: string;
  type: 'video' | 'voice';
  status: 'ringing' | 'active' | 'ended';
  duration?: number;
  summary?: string;
  actionItems?: string[];
}

export interface ThreadMessage {
  id: string;
  sender: string;
  content: string;
  timestamp: string;
  isOwn: boolean;
  channel: 'telegram' | 'email' | 'sms' | 'whatsapp';
  read: boolean;
}

export interface CommsThread {
  contactName: string;
  channel: 'telegram' | 'email' | 'sms' | 'whatsapp';
  messages: ThreadMessage[];
  subject?: string;
}

export type CommsView = 'call' | 'thread' | 'draft';

interface Props {
  call?: CallInfo;
  thread?: CommsThread;
  draftContent?: string;
  view?: CommsView;
}

/* ── Call View ────────────────────────────────────────────────── */

function CallView({ call }: { call: CallInfo }) {
  const [micOn, setMicOn] = useState(true);
  const [camOn, setCamOn] = useState(call.type === 'video');
  const [sharing, setSharing] = useState(false);

  const formatDuration = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  if (call.status === 'ended') {
    return (
      <div className="rounded-xl overflow-hidden" style={{ border: '1px solid var(--border)' }}>
        <div className="px-4 py-3" style={{ background: 'var(--raised)', borderBottom: '1px solid var(--border)' }}>
          <div className="flex items-center gap-2">
            <Phone className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
            <span className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
              Call with {call.contactName}
            </span>
            <span className="text-[9px] px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444' }}>
              Ended
            </span>
          </div>
          {call.duration && (
            <span className="text-[10px] mt-1 block" style={{ color: 'var(--text-muted)' }}>
              Duration: {formatDuration(call.duration)}
            </span>
          )}
        </div>
        {call.summary && (
          <div className="px-4 py-3">
            <p className="text-[10px] font-semibold mb-1" style={{ color: 'var(--gold)' }}>Summary</p>
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{call.summary}</p>
          </div>
        )}
        {call.actionItems && call.actionItems.length > 0 && (
          <div className="px-4 py-3" style={{ borderTop: '1px solid var(--border)' }}>
            <p className="text-[10px] font-semibold mb-1.5" style={{ color: 'var(--purple)' }}>Action Items</p>
            <ul className="space-y-1">
              {call.actionItems.map((item, i) => (
                <li key={i} className="flex items-start gap-1.5 text-[11px]" style={{ color: 'var(--text-secondary)' }}>
                  <span className="text-[9px] mt-0.5" style={{ color: 'var(--gold)' }}>&#9679;</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      className="rounded-xl overflow-hidden flex flex-col"
      style={{ border: '1px solid var(--border)', minHeight: 320 }}
    >
      {/* Call display area */}
      <div
        className="flex-1 flex flex-col items-center justify-center gap-4 relative"
        style={{ background: 'linear-gradient(135deg, #0a0a1a 0%, #1a1030 100%)', minHeight: 200 }}
      >
        {/* Avatar */}
        <div
          className="w-20 h-20 rounded-full flex items-center justify-center text-2xl font-bold"
          style={{
            background: 'linear-gradient(135deg, var(--gold) 0%, var(--purple) 100%)',
            color: 'white',
            boxShadow: call.status === 'active' ? '0 0 30px rgba(212,175,55,0.3)' : 'none',
          }}
        >
          {call.contactName.charAt(0).toUpperCase()}
        </div>
        <div className="text-center">
          <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{call.contactName}</p>
          {call.contactPhone && (
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{call.contactPhone}</p>
          )}
          <p className="text-[10px] mt-1" style={{ color: call.status === 'ringing' ? 'var(--gold)' : '#22c55e' }}>
            {call.status === 'ringing' ? 'Ringing...' : 'Connected'}
          </p>
        </div>

        {/* Status indicator */}
        {call.status === 'ringing' && (
          <div className="flex gap-1.5">
            {[0, 1, 2].map(i => (
              <div
                key={i}
                className="w-2 h-2 rounded-full"
                style={{
                  background: 'var(--gold)',
                  animation: `comm-ring-pulse 1.5s ease-in-out ${i * 0.3}s infinite`,
                }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="flex items-center justify-center gap-3 px-4 py-3" style={{ background: 'var(--raised)', borderTop: '1px solid var(--border)' }}>
        <button
          onClick={() => setMicOn(!micOn)}
          className="w-10 h-10 rounded-full flex items-center justify-center transition"
          style={{ background: micOn ? 'var(--elevated)' : '#ef4444', color: micOn ? 'var(--text-secondary)' : 'white' }}
        >
          {micOn ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
        </button>

        {call.type === 'video' && (
          <button
            onClick={() => setCamOn(!camOn)}
            className="w-10 h-10 rounded-full flex items-center justify-center transition"
            style={{ background: camOn ? 'var(--elevated)' : '#ef4444', color: camOn ? 'var(--text-secondary)' : 'white' }}
          >
            {camOn ? <Video className="w-4 h-4" /> : <VideoOff className="w-4 h-4" />}
          </button>
        )}

        <button
          onClick={() => setSharing(!sharing)}
          className="w-10 h-10 rounded-full flex items-center justify-center transition"
          style={{ background: sharing ? 'var(--purple)' : 'var(--elevated)', color: sharing ? 'white' : 'var(--text-secondary)' }}
        >
          <MonitorUp className="w-4 h-4" />
        </button>

        <button
          className="w-12 h-12 rounded-full flex items-center justify-center transition"
          style={{ background: '#ef4444', color: 'white' }}
        >
          <PhoneOff className="w-5 h-5" />
        </button>
      </div>

      <style jsx>{`
        @keyframes comm-ring-pulse {
          0%, 100% { opacity: 0.3; transform: scale(0.8); }
          50% { opacity: 1; transform: scale(1.2); }
        }
      `}</style>
    </div>
  );
}

/* ── Thread View ──────────────────────────────────────────────── */

function ThreadView({ thread }: { thread: CommsThread }) {
  const [draftText, setDraftText] = useState('');

  const channelColors: Record<string, string> = {
    telegram: '#0088cc',
    email: '#D4AF37',
    sms: '#22c55e',
    whatsapp: '#25D366',
  };

  const channelIcons: Record<string, string> = {
    telegram: 'TG',
    email: 'EM',
    sms: 'SM',
    whatsapp: 'WA',
  };

  return (
    <div
      className="rounded-xl overflow-hidden flex flex-col"
      style={{ border: '1px solid var(--border)', maxHeight: 450 }}
    >
      {/* Thread header */}
      <div className="flex items-center justify-between px-3 py-2 shrink-0" style={{ background: 'var(--raised)', borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center gap-2">
          <div
            className="w-7 h-7 rounded-full flex items-center justify-center text-[9px] font-bold text-white"
            style={{ background: channelColors[thread.channel] || 'var(--purple)' }}
          >
            {channelIcons[thread.channel] || 'MSG'}
          </div>
          <div>
            <p className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>{thread.contactName}</p>
            {thread.subject && (
              <p className="text-[9px]" style={{ color: 'var(--text-muted)' }}>{thread.subject}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button className="p-1 rounded hover:bg-white/5 transition" style={{ color: 'var(--text-muted)' }} title="Reply">
            <Reply className="w-3.5 h-3.5" />
          </button>
          <button className="p-1 rounded hover:bg-white/5 transition" style={{ color: 'var(--text-muted)' }} title="Forward">
            <Forward className="w-3.5 h-3.5" />
          </button>
          <button className="p-1 rounded hover:bg-white/5 transition" style={{ color: 'var(--text-muted)' }} title="Archive">
            <Archive className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2" style={{ minHeight: 0 }}>
        {thread.messages.map(msg => (
          <div
            key={msg.id}
            className={`flex ${msg.isOwn ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className="max-w-[80%] rounded-xl px-3 py-2"
              style={{
                background: msg.isOwn
                  ? 'linear-gradient(135deg, rgba(212,175,55,0.15) 0%, rgba(139,92,246,0.15) 100%)'
                  : 'var(--elevated)',
                border: `1px solid ${msg.isOwn ? 'var(--gold-border)' : 'var(--border)'}`,
              }}
            >
              {!msg.isOwn && (
                <p className="text-[9px] font-semibold mb-0.5" style={{ color: channelColors[msg.channel] || 'var(--purple)' }}>
                  {msg.sender}
                </p>
              )}
              <p className="text-[11px] leading-relaxed" style={{ color: 'var(--text-primary)' }}>
                {msg.content}
              </p>
              <div className="flex items-center justify-end gap-1 mt-1">
                <Clock className="w-2.5 h-2.5" style={{ color: 'var(--text-muted)' }} />
                <span className="text-[8px]" style={{ color: 'var(--text-muted)' }}>{msg.timestamp}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Draft compose */}
      <div className="px-3 py-2 shrink-0" style={{ borderTop: '1px solid var(--border)', background: 'var(--raised)' }}>
        <div className="flex items-center gap-1.5 mb-1">
          <PenLine className="w-3 h-3" style={{ color: 'var(--gold)' }} />
          <span className="text-[9px] font-medium" style={{ color: 'var(--gold)' }}>MAX drafting reply...</span>
        </div>
        <div className="flex items-end gap-2">
          <textarea
            value={draftText}
            onChange={e => setDraftText(e.target.value)}
            placeholder="Type a reply..."
            className="flex-1 resize-none rounded-lg px-2.5 py-1.5 text-[11px] outline-none"
            style={{ background: 'var(--elevated)', color: 'var(--text-primary)', border: '1px solid var(--border)', minHeight: 32, maxHeight: 80, fontFamily: 'inherit' }}
            rows={1}
          />
          <button
            className="w-7 h-7 rounded-lg flex items-center justify-center transition shrink-0"
            style={{ background: draftText.trim() ? 'var(--gold)' : 'var(--elevated)', color: draftText.trim() ? '#0a0a0a' : 'var(--text-muted)' }}
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Main CommsCanvas ─────────────────────────────────────────── */

export default function CommsCanvas({ call, thread, draftContent, view }: Props) {
  // Auto-detect view
  const activeView = view || (call ? 'call' : thread ? 'thread' : 'draft');

  if (activeView === 'call' && call) {
    return <CallView call={call} />;
  }

  if ((activeView === 'thread' || activeView === 'draft') && thread) {
    return <ThreadView thread={thread} />;
  }

  // No comms data — show placeholder
  return (
    <div
      className="rounded-xl flex flex-col items-center justify-center gap-3 py-8"
      style={{ border: '1px solid var(--border)', background: 'var(--raised)' }}
    >
      <MessageSquare className="w-8 h-8 opacity-30" style={{ color: 'var(--gold)' }} />
      <p className="text-xs" style={{ color: 'var(--text-muted)' }}>No active communication</p>
    </div>
  );
}

/**
 * Parse MAX response for comms-related content.
 * Detects call summaries, message threads, draft responses.
 */
export function parseCommsFromContent(content: string): { call?: CallInfo; thread?: CommsThread } | null {
  // Detect call summary pattern
  const callMatch = content.match(/(?:call|called|phone call|video call)\s+(?:with\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/i);
  const summaryMatch = content.match(/(?:summary|notes|recap)[:\s]+(.+?)(?:\n|$)/i);
  const actionMatch = content.match(/(?:action items?|next steps?|to.?do)[:\s]*\n((?:[-*]\s+.+\n?)+)/i);

  if (callMatch) {
    const actionItems = actionMatch
      ? actionMatch[1].split('\n').map(l => l.replace(/^[-*]\s+/, '').trim()).filter(Boolean)
      : undefined;

    return {
      call: {
        contactName: callMatch[1],
        type: /video/i.test(content) ? 'video' : 'voice',
        status: 'ended',
        summary: summaryMatch ? summaryMatch[1].trim() : undefined,
        actionItems,
      },
    };
  }

  // Detect message thread pattern
  const threadMatch = content.match(/(?:message|telegram|email|text|sms)\s+(?:from|thread|conversation)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/i);
  if (threadMatch) {
    const channel = /telegram/i.test(content) ? 'telegram' as const :
                    /email/i.test(content) ? 'email' as const :
                    /sms|text/i.test(content) ? 'sms' as const : 'telegram' as const;

    return {
      thread: {
        contactName: threadMatch[1],
        channel,
        messages: [], // Will be populated from structured data
      },
    };
  }

  return null;
}
