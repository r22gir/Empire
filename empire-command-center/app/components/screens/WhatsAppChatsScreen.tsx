'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  CheckCheck,
  MessageCircle,
  RefreshCw,
  Search,
  XCircle,
} from 'lucide-react';
import { API } from '../../lib/api';

const PIN_KEY = 'empire_whatsapp_founder_pin';

interface Conversation {
  wa_id: string;
  display_label: string;
  total_messages: number;
  last_timestamp: string;
  last_message: string;
  last_direction: string;
  last_status: string;
  last_error_code?: string;
  last_error?: string | null;
}

interface ChatMessage {
  id: number;
  wa_id: string;
  display_label: string;
  direction: string;
  timestamp: string;
  wa_message_id?: string;
  message_type: string;
  body?: string;
  caption?: string;
  transcript?: string;
  delivery_status?: string;
  error_code?: string;
  error_message?: string;
  metadata?: {
    documents?: { filename?: string; doc_id?: string }[];
    filename?: string;
    call_event?: string;
    voice_sent?: boolean;
  };
}

function storedPin(): string {
  if (typeof window === 'undefined') return '';
  return sessionStorage.getItem(PIN_KEY) || '';
}

function founderHeaders(pin: string): HeadersInit {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (pin) headers['X-Founder-Pin'] = pin;
  return headers;
}

function formatWhen(value?: string): string {
  if (!value) return '';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  return sameDay
    ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function StatusTicks({ status, failed }: { status?: string; failed?: boolean }) {
  if (failed || status === 'failed') {
    return <XCircle size={13} color="#f87171" />;
  }
  if (status === 'read') {
    return <CheckCheck size={13} color="#d4b84a" />;
  }
  if (status === 'delivered') {
    return <CheckCheck size={13} color="#9ca3af" />;
  }
  if (status === 'sent') {
    return <Check size={13} color="#9ca3af" />;
  }
  return null;
}

export default function WhatsAppChatsScreen() {
  const [pin, setPin] = useState(storedPin);
  const [pinDraft, setPinDraft] = useState('');
  const [needsPin, setNeedsPin] = useState(!storedPin());
  const [pinError, setPinError] = useState('');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [total, setTotal] = useState(0);
  const [listQuery, setListQuery] = useState('');
  const [threadQuery, setThreadQuery] = useState('');
  const [hits, setHits] = useState<ChatMessage[]>([]);
  const [loadingList, setLoadingList] = useState(false);
  const [loadingThread, setLoadingThread] = useState(false);
  const [narrow, setNarrow] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const check = () => setNarrow(window.innerWidth < 768);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  const loadList = useCallback(async (founderPin: string) => {
    setLoadingList(true);
    setError('');
    try {
      const res = await fetch(`${API}/whatsapp/chats`, {
        headers: founderHeaders(founderPin),
        cache: 'no-store',
      });
      if (res.status === 403 || res.status === 503) {
        setNeedsPin(true);
        setPinError(res.status === 503 ? 'Founder PIN is not configured on this host.' : 'Founder PIN required.');
        return;
      }
      if (!res.ok) throw new Error(`Could not load chats (${res.status})`);
      const data = await res.json();
      setConversations(data.conversations || []);
      setNeedsPin(false);
      setPinError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load chats');
    } finally {
      setLoadingList(false);
    }
  }, []);

  const loadThread = useCallback(async (waId: string, founderPin: string, q = '') => {
    setLoadingThread(true);
    try {
      const params = new URLSearchParams({ limit: '100', offset: '0' });
      if (q.trim()) params.set('q', q.trim());
      const res = await fetch(`${API}/whatsapp/chats/${encodeURIComponent(waId)}/messages?${params}`, {
        headers: founderHeaders(founderPin),
        cache: 'no-store',
      });
      if (!res.ok) throw new Error(`Could not load messages (${res.status})`);
      const data = await res.json();
      setMessages(data.messages || []);
      setTotal(data.total || 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load messages');
    } finally {
      setLoadingThread(false);
    }
  }, []);

  useEffect(() => {
    if (pin && !needsPin) loadList(pin);
  }, [pin, needsPin, loadList]);

  useEffect(() => {
    if (pin && selectedId) loadThread(selectedId, pin, threadQuery);
  }, [pin, selectedId, threadQuery, loadThread]);

  useEffect(() => {
    if (!pin || listQuery.trim().length < 2) {
      setHits([]);
      return;
    }
    const handle = setTimeout(async () => {
      try {
        const res = await fetch(
          `${API}/whatsapp/chats/search?q=${encodeURIComponent(listQuery.trim())}&limit=30`,
          { headers: founderHeaders(pin), cache: 'no-store' },
        );
        if (!res.ok) return;
        const data = await res.json();
        setHits(data.messages || []);
      } catch {
        setHits([]);
      }
    }, 250);
    return () => clearTimeout(handle);
  }, [listQuery, pin]);

  const filteredConversations = useMemo(() => {
    const q = listQuery.trim().toLowerCase();
    if (!q) return conversations;
    return conversations.filter((c) =>
      `${c.display_label} ${c.wa_id} ${c.last_message}`.toLowerCase().includes(q),
    );
  }, [conversations, listQuery]);

  const selected = conversations.find((c) => c.wa_id === selectedId) || null;
  const showList = !narrow || !selectedId;
  const showThread = !narrow || !!selectedId;

  const unlock = () => {
    const next = pinDraft.trim();
    if (!next) {
      setPinError('Enter the founder PIN.');
      return;
    }
    sessionStorage.setItem(PIN_KEY, next);
    setPin(next);
    setNeedsPin(false);
    setPinError('');
    loadList(next);
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        minHeight: 0,
        background: '#11100e',
        color: '#f5f2ed',
      }}
    >
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '12px 16px',
          borderBottom: '1px solid #2a261c',
          background: '#16140f',
        }}
      >
        <MessageCircle size={18} color="#d4b84a" />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 11, letterSpacing: 1.2, textTransform: 'uppercase', color: '#d4b84a', fontWeight: 700 }}>
            Channels
          </div>
          <h1 style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>WhatsApp Chats</h1>
        </div>
        <button
          onClick={() => pin && loadList(pin)}
          style={{
            background: 'transparent',
            border: '1px solid #3a3424',
            color: '#d4b84a',
            borderRadius: 8,
            width: 36,
            height: 36,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
          }}
          aria-label="Refresh chats"
        >
          <RefreshCw size={14} />
        </button>
      </header>

      {needsPin && (
        <div style={{ padding: 16, borderBottom: '1px solid #2a261c' }}>
          <div style={{ fontSize: 13, color: '#c4b99a', marginBottom: 8 }}>
            Founder PIN is required to read this edition&apos;s WhatsApp log.
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <input
              type="password"
              value={pinDraft}
              onChange={(e) => setPinDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') unlock(); }}
              placeholder="Founder PIN"
              autoComplete="off"
              style={{
                flex: '1 1 160px',
                minHeight: 40,
                borderRadius: 8,
                border: '1px solid #3a3424',
                background: '#1c1914',
                color: '#f5f2ed',
                padding: '0 12px',
              }}
            />
            <button
              onClick={unlock}
              style={{
                minHeight: 40,
                padding: '0 16px',
                borderRadius: 8,
                border: 'none',
                background: '#b8960c',
                color: '#11100e',
                fontWeight: 700,
                cursor: 'pointer',
              }}
            >
              Unlock
            </button>
          </div>
          {pinError && <div style={{ color: '#f87171', fontSize: 12, marginTop: 8 }}>{pinError}</div>}
        </div>
      )}

      {error && (
        <div style={{ padding: '8px 16px', color: '#f87171', fontSize: 13 }}>{error}</div>
      )}

      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        {showList && (
          <aside
            style={{
              width: narrow ? '100%' : 320,
              borderRight: narrow ? 'none' : '1px solid #2a261c',
              display: 'flex',
              flexDirection: 'column',
              minHeight: 0,
              background: '#14120e',
            }}
          >
            <div style={{ padding: 12, borderBottom: '1px solid #2a261c' }}>
              <div style={{ position: 'relative' }}>
                <Search size={14} color="#d4b84a" style={{ position: 'absolute', left: 10, top: 12 }} />
                <input
                  value={listQuery}
                  onChange={(e) => setListQuery(e.target.value)}
                  placeholder="Search chats or text"
                  style={{
                    width: '100%',
                    minHeight: 40,
                    padding: '0 12px 0 32px',
                    borderRadius: 8,
                    border: '1px solid #3a3424',
                    background: '#1c1914',
                    color: '#f5f2ed',
                  }}
                />
              </div>
            </div>
            <div style={{ overflowY: 'auto', flex: 1 }}>
              {loadingList && (
                <div style={{ padding: 16, color: '#9ca3af', fontSize: 13 }}>Loading…</div>
              )}
              {!loadingList && filteredConversations.length === 0 && (
                <div style={{ padding: 16, color: '#9ca3af', fontSize: 13 }}>
                  No WhatsApp conversations in this edition yet.
                </div>
              )}
              {filteredConversations.map((c) => {
                const failed = c.last_status === 'failed';
                const active = c.wa_id === selectedId;
                return (
                  <button
                    key={c.wa_id}
                    onClick={() => { setSelectedId(c.wa_id); setThreadQuery(''); }}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      padding: '12px 14px',
                      border: 'none',
                      borderBottom: '1px solid #241f16',
                      background: active ? '#2a2410' : 'transparent',
                      color: '#f5f2ed',
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                      <strong style={{ color: '#d4b84a', fontSize: 14 }}>{c.display_label}</strong>
                      <span style={{ fontSize: 11, color: '#8b8373' }}>{formatWhen(c.last_timestamp)}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                      <StatusTicks status={c.last_status} failed={failed} />
                      <span style={{ fontSize: 12, color: failed ? '#f87171' : '#c4b99a', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {c.last_direction === 'outbound' ? 'Max: ' : ''}{c.last_message}
                      </span>
                    </div>
                    {failed && (
                      <div style={{ fontSize: 11, color: '#f87171', marginTop: 4 }}>
                        Delivery failed{c.last_error_code ? ` · ${c.last_error_code}` : ''}
                      </div>
                    )}
                  </button>
                );
              })}
              {hits.length > 0 && (
                <div style={{ padding: '10px 14px', borderTop: '1px solid #2a261c' }}>
                  <div style={{ fontSize: 10, letterSpacing: 1, textTransform: 'uppercase', color: '#d4b84a', marginBottom: 8 }}>
                    Text matches
                  </div>
                  {hits.map((hit) => (
                    <button
                      key={`${hit.id}-${hit.wa_id}`}
                      onClick={() => { setSelectedId(hit.wa_id); setThreadQuery(listQuery); }}
                      style={{
                        width: '100%',
                        textAlign: 'left',
                        background: 'transparent',
                        border: 'none',
                        color: '#c4b99a',
                        padding: '8px 0',
                        cursor: 'pointer',
                        fontSize: 12,
                      }}
                    >
                      <div style={{ color: '#d4b84a' }}>{hit.display_label}</div>
                      <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {hit.body || hit.caption || `[${hit.message_type}]`}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </aside>
        )}

        {showThread && (
          <section style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <div
              style={{
                padding: '12px 16px',
                borderBottom: '1px solid #2a261c',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                background: '#16140f',
              }}
            >
              {narrow && (
                <button
                  onClick={() => setSelectedId(null)}
                  style={{ background: 'transparent', border: 'none', color: '#d4b84a', cursor: 'pointer' }}
                  aria-label="Back to chats"
                >
                  <ArrowLeft size={18} />
                </button>
              )}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 700 }}>{selected?.display_label || 'Select a conversation'}</div>
                {selected && (
                  <div style={{ fontSize: 11, color: '#8b8373' }}>
                    {selected.wa_id} · {total} messages · view only
                  </div>
                )}
              </div>
              {selected && (
                <input
                  value={threadQuery}
                  onChange={(e) => setThreadQuery(e.target.value)}
                  placeholder="Find in thread"
                  style={{
                    minHeight: 36,
                    width: narrow ? 120 : 180,
                    borderRadius: 8,
                    border: '1px solid #3a3424',
                    background: '#1c1914',
                    color: '#f5f2ed',
                    padding: '0 10px',
                  }}
                />
              )}
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
              {!selected && (
                <div style={{ color: '#8b8373', fontSize: 14, padding: 24 }}>
                  Choose a sender on the left. This page does not send or edit messages.
                </div>
              )}
              {loadingThread && selected && (
                <div style={{ color: '#9ca3af', fontSize: 13 }}>Loading thread…</div>
              )}
              {selected && messages.map((m) => {
                const outbound = m.direction === 'outbound';
                const failed = m.delivery_status === 'failed';
                const docs = m.metadata?.documents || [];
                return (
                  <div
                    key={m.id}
                    style={{
                      display: 'flex',
                      justifyContent: outbound ? 'flex-end' : 'flex-start',
                      marginBottom: 12,
                    }}
                  >
                    <div
                      style={{
                        maxWidth: '86%',
                        padding: '10px 12px',
                        borderRadius: outbound ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
                        background: outbound ? '#2a2410' : '#1c1914',
                        border: failed ? '1px solid #7f1d1d' : '1px solid #3a3424',
                      }}
                    >
                      <div style={{ fontSize: 10, color: '#d4b84a', fontWeight: 700, marginBottom: 4 }}>
                        {outbound ? 'MAX' : m.display_label} · {m.message_type}
                      </div>
                      <div style={{ fontSize: 14, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                        {m.body || m.caption || `[${m.message_type}]`}
                      </div>
                      {m.transcript && (
                        <div style={{ fontSize: 12, color: '#c4b99a', marginTop: 6 }}>
                          Transcript: {m.transcript}
                        </div>
                      )}
                      {docs.length > 0 && (
                        <div style={{ marginTop: 8, fontSize: 12, color: '#d4b84a' }}>
                          {docs.map((d, i) => (
                            <div key={`${d.filename}-${i}`}>
                              Document {d.filename || 'file'}
                              {d.doc_id ? ` · ${d.doc_id}` : ''}
                            </div>
                          ))}
                        </div>
                      )}
                      {failed && (
                        <div
                          style={{
                            marginTop: 8,
                            padding: 8,
                            borderRadius: 8,
                            background: '#3f1212',
                            color: '#fecaca',
                            fontSize: 12,
                            display: 'flex',
                            gap: 6,
                            alignItems: 'flex-start',
                          }}
                        >
                          <AlertTriangle size={13} />
                          <span>
                            Delivery failed
                            {m.error_code ? ` · Meta ${m.error_code}` : ''}
                            {m.error_message ? ` — ${m.error_message}` : ''}
                          </span>
                        </div>
                      )}
                      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 6, marginTop: 6 }}>
                        <span style={{ fontSize: 10, color: '#8b8373' }}>{formatWhen(m.timestamp)}</span>
                        {outbound && <StatusTicks status={m.delivery_status} failed={failed} />}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
