'use client';

import { useEffect, useMemo, useState } from 'react';
import { API } from '../../lib/api';

type MemoryMessage = {
  id: string;
  channel: string;
  direction: string;
  sender: string;
  recipient: string;
  thread_id: string;
  source_message_id?: string;
  subject?: string;
  body: string;
  message_text: string;
  attachment_refs: any[];
  extracted_content?: string;
  summary?: string;
  created_at?: string;
  founder_verified: boolean;
  linked_refs: any[];
};

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'web_chat', label: 'Web' },
  { id: 'telegram', label: 'Telegram' },
  { id: 'email', label: 'Email' },
  { id: 'attachments', label: 'Attachments' },
  { id: 'founder-only', label: 'Founder only' },
];

function safeList(value: any): any[] {
  if (!value) return [];
  if (Array.isArray(value)) return value;
  return [value];
}

function labelAttachment(ref: any): string {
  if (!ref) return '';
  if (typeof ref === 'string') return ref;
  return ref.ref || ref.filename || ref.name || ref.url || JSON.stringify(ref);
}

export default function MemoryBankScreen() {
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<MemoryMessage[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const selected = useMemo(
    () => messages.find(m => m.id === selectedId) || messages[0] || null,
    [messages, selectedId],
  );
  const threadMessages = useMemo(
    () => selected ? messages.filter(m => m.thread_id === selected.thread_id) : [],
    [messages, selected],
  );

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError('');
      const params = new URLSearchParams();
      params.set('limit', '150');
      if (query.trim()) params.set('q', query.trim());
      if (filter === 'founder-only') {
        params.set('channel', 'all');
        params.set('founder_only', 'true');
      } else {
        params.set('channel', filter);
      }
      try {
        const res = await fetch(`${API}/chats/memory-bank?${params.toString()}`);
        if (!res.ok) throw new Error(`Memory Bank ${res.status}`);
        const data = await res.json();
        const nextMessages = data.messages || [];
        setMessages(nextMessages);
        setSelectedId(current => current && nextMessages.some((m: MemoryMessage) => m.id === current)
          ? current
          : nextMessages[0]?.id || null);
      } catch (exc: any) {
        setError(exc?.message || 'Memory Bank unavailable');
      } finally {
        setLoading(false);
      }
    };
    const timer = setTimeout(load, 180);
    return () => clearTimeout(timer);
  }, [filter, query]);

  return (
    <div data-testid="max-memory-bank" style={{ height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column', background: 'var(--chat-bg)' }}>
      <div style={{ padding: '18px 22px', borderBottom: '1px solid var(--border)', background: 'var(--card-bg)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: 1.4, color: 'var(--muted)', textTransform: 'uppercase' }}>Founder {'>'} MAX</div>
            <h1 style={{ margin: '4px 0 0', fontSize: 24, fontWeight: 900, color: 'var(--text)' }}>MAX Memory Bank</h1>
            <p style={{ margin: '6px 0 0', fontSize: 13, color: 'var(--muted)' }}>
              Web chat, Telegram, email, attachments, and linked execution refs in one ledger.
            </p>
          </div>
          <div style={{ minWidth: 260, flex: '0 1 360px' }}>
            <input
              data-testid="max-memory-search"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search messages, subjects, extracted text"
              style={{
                width: '100%',
                height: 40,
                borderRadius: 8,
                border: '1px solid var(--border)',
                background: '#fff',
                padding: '0 12px',
                color: 'var(--text)',
                fontSize: 13,
              }}
            />
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 14 }}>
          {FILTERS.map(item => (
            <button
              key={item.id}
              data-testid={`memory-filter-${item.id}`}
              onClick={() => setFilter(item.id)}
              style={{
                border: '1px solid ' + (filter === item.id ? '#b8960c' : 'var(--border)'),
                background: filter === item.id ? '#fdf8eb' : '#fff',
                color: filter === item.id ? '#7a5d00' : 'var(--text)',
                borderRadius: 8,
                padding: '7px 10px',
                fontSize: 12,
                fontWeight: 800,
                cursor: 'pointer',
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, minHeight: 0, display: 'grid', gridTemplateColumns: 'minmax(280px, 420px) minmax(0, 1fr)' }}>
        <div style={{ overflowY: 'auto', borderRight: '1px solid var(--border)', background: '#fff' }}>
          {loading && <div style={{ padding: 18, color: 'var(--muted)', fontSize: 13 }}>Loading Memory Bank...</div>}
          {error && <div style={{ padding: 18, color: '#b91c1c', fontSize: 13 }}>{error}</div>}
          {!loading && !error && messages.length === 0 && (
            <div style={{ padding: 18, color: 'var(--muted)', fontSize: 13 }}>No messages found.</div>
          )}
          {messages.map(message => {
            const attachments = safeList(message.attachment_refs);
            const isSelected = selected?.id === message.id;
            return (
              <button
                key={message.id}
                data-testid={`memory-message-${message.channel}`}
                onClick={() => setSelectedId(message.id)}
                style={{
                  width: '100%',
                  textAlign: 'left',
                  border: 'none',
                  borderBottom: '1px solid var(--border)',
                  background: isSelected ? '#fdf8eb' : '#fff',
                  padding: '13px 14px',
                  cursor: 'pointer',
                }}
              >
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 10, fontWeight: 900, color: '#7a5d00', textTransform: 'uppercase' }}>{message.channel}</span>
                  <span style={{ fontSize: 10, color: 'var(--muted)' }}>{message.direction}</span>
                  {message.founder_verified && <span style={{ fontSize: 10, color: '#15803d', fontWeight: 800 }}>founder</span>}
                  {attachments.length > 0 && <span data-testid="memory-attachment-badge" style={{ fontSize: 10, color: '#1d4ed8', fontWeight: 800 }}>attachment</span>}
                </div>
                <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {message.subject || message.summary || message.message_text || '(empty)'}
                </div>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {message.sender} to {message.recipient}
                </div>
              </button>
            );
          })}
        </div>

        <div data-testid="memory-thread-detail" style={{ overflowY: 'auto', padding: 22 }}>
          {!selected && <div style={{ color: 'var(--muted)', fontSize: 13 }}>Select a Memory Bank message.</div>}
          {selected && (
            <>
              <div style={{ marginBottom: 18 }}>
                <div style={{ fontSize: 11, fontWeight: 900, color: '#7a5d00', textTransform: 'uppercase' }}>{selected.channel} thread</div>
                <h2 style={{ margin: '4px 0', fontSize: 20, fontWeight: 900, color: 'var(--text)' }}>{selected.subject || 'Message thread'}</h2>
                <div style={{ fontSize: 12, color: 'var(--muted)' }}>
                  Thread {selected.thread_id} · {selected.created_at || 'time unknown'}
                </div>
              </div>

              {threadMessages.map(message => {
                const attachments = safeList(message.attachment_refs);
                const links = safeList(message.linked_refs);
                return (
                  <article
                    key={message.id}
                    style={{
                      border: '1px solid var(--border)',
                      borderRadius: 8,
                      background: '#fff',
                      padding: 14,
                      marginBottom: 12,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', marginBottom: 8 }}>
                      <strong style={{ fontSize: 13, color: 'var(--text)' }}>{message.sender} to {message.recipient}</strong>
                      <span style={{ fontSize: 11, color: 'var(--muted)' }}>{message.created_at}</span>
                    </div>
                    <p style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.55, color: 'var(--text)', margin: 0 }}>
                      {message.message_text || message.summary || '(empty message)'}
                    </p>
                    {message.extracted_content && (
                      <div style={{ marginTop: 12, padding: 10, borderRadius: 8, background: '#f8fafc', fontSize: 12, color: 'var(--text)' }}>
                        <strong>Extracted content</strong>
                        <div style={{ whiteSpace: 'pre-wrap', marginTop: 4 }}>{message.extracted_content}</div>
                      </div>
                    )}
                    {attachments.length > 0 && (
                      <div data-testid="memory-attachment-list" style={{ marginTop: 12 }}>
                        <strong style={{ fontSize: 12, color: 'var(--text)' }}>Attachments</strong>
                        {attachments.map((attachment, index) => (
                          <div key={index} style={{ fontSize: 12, color: '#1d4ed8', marginTop: 4 }}>
                            {labelAttachment(attachment)}
                          </div>
                        ))}
                      </div>
                    )}
                    {links.length > 0 && (
                      <div style={{ marginTop: 12 }}>
                        <strong style={{ fontSize: 12, color: 'var(--text)' }}>Linked refs</strong>
                        {links.map((link, index) => (
                          <div key={index} style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>
                            {typeof link === 'string' ? link : JSON.stringify(link)}
                          </div>
                        ))}
                      </div>
                    )}
                  </article>
                );
              })}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
