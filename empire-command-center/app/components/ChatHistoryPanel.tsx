'use client';
import { useState, useEffect, useCallback } from 'react';
import { X, Plus, Clock, MessageSquare, Mail, Search, Pin, Trash2 } from 'lucide-react';
import { API } from '../lib/api';

interface ChatEntry {
  id: string;
  title: string;
  preview: string;
  timestamp: string;
  messageCount?: number;
  pinned?: boolean;
  channel?: string;
}

interface EmailEntry {
  id: string;
  from: string;
  subject: string;
  date: string;
  preview: string;
  unread: boolean;
}

interface Props {
  open: boolean;
  onClose: () => void;
  onLoadChat: (chatId: string) => void;
  onNewChat: () => void;
}

type Tab = 'web' | 'telegram' | 'email';

export default function ChatHistoryPanel({ open, onClose, onLoadChat, onNewChat }: Props) {
  const [tab, setTab] = useState<Tab>('web');
  const [webChats, setWebChats] = useState<ChatEntry[]>([]);
  const [telegramChats, setTelegramChats] = useState<ChatEntry[]>([]);
  const [emails, setEmails] = useState<EmailEntry[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchWebChats = useCallback(async () => {
    try {
      const res = await fetch(API + '/chats/list');
      if (res.ok) {
        const data = await res.json();
        setWebChats((data.chats || []).map((c: any) => ({
          id: c.id,
          title: c.title || 'Untitled',
          preview: c.preview || '',
          timestamp: c.updated_at || c.created_at || '',
          messageCount: c.message_count || 0,
          pinned: c.pinned || false,
          channel: 'web',
        })));
      }
    } catch { /* silent */ }
  }, []);

  const fetchTelegramChats = useCallback(async () => {
    try {
      const res = await fetch(API + '/max/telegram/history?limit=20');
      if (res.ok) {
        const data = await res.json();
        const msgs = data.messages || data.history || [];
        if (msgs.length > 0) {
          setTelegramChats([{
            id: 'telegram-main',
            title: 'Telegram Chat',
            preview: msgs[0]?.content?.slice(0, 100) || '',
            timestamp: msgs[0]?.timestamp || '',
            messageCount: msgs.length,
            channel: 'telegram',
          }]);
        }
      }
    } catch { /* silent */ }
  }, []);

  const fetchEmails = useCallback(async () => {
    try {
      const res = await fetch(API + '/max/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: '{"tool":"check_email","limit":10,"unread_only":false}',
          channel: 'system',
        }),
      });
      // Fallback: direct tool call endpoint if available
    } catch { /* silent */ }

    // Use direct Gmail endpoint
    try {
      const res = await fetch(API + '/max/gmail/inbox?limit=10');
      if (res.ok) {
        const data = await res.json();
        setEmails(data.emails || []);
        setUnreadCount(data.unread_total || 0);
      }
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    Promise.all([fetchWebChats(), fetchTelegramChats(), fetchEmails()])
      .finally(() => setLoading(false));
  }, [open, fetchWebChats, fetchTelegramChats, fetchEmails]);

  const handleSearch = useCallback(async () => {
    if (!search.trim()) { fetchWebChats(); return; }
    try {
      const res = await fetch(API + `/chats/search?q=${encodeURIComponent(search)}`);
      if (res.ok) {
        const data = await res.json();
        setWebChats((data.results || []).map((c: any) => ({
          id: c.id,
          title: c.title || 'Untitled',
          preview: c.matching_messages?.[0]?.snippet || '',
          timestamp: c.updated_at || '',
          messageCount: c.message_count || 0,
          channel: 'web',
        })));
      }
    } catch { /* silent */ }
  }, [search, fetchWebChats]);

  const handlePin = useCallback(async (chatId: string, pinned: boolean) => {
    try {
      await fetch(API + `/chats/${chatId}/pin`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pinned: !pinned }),
      });
      fetchWebChats();
    } catch { /* silent */ }
  }, [fetchWebChats]);

  const handleDelete = useCallback(async (chatId: string) => {
    try {
      await fetch(API + `/chats/${chatId}`, { method: 'DELETE' });
      fetchWebChats();
    } catch { /* silent */ }
  }, [fetchWebChats]);

  const formatDate = (ts: string) => {
    if (!ts) return '';
    try {
      const d = new Date(ts);
      const now = new Date();
      const diff = now.getTime() - d.getTime();
      if (diff < 86400000) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      if (diff < 604800000) return d.toLocaleDateString([], { weekday: 'short' });
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch { return ts.slice(0, 10); }
  };

  if (!open) return null;

  const TABS: { key: Tab; label: string; icon: any; count?: number }[] = [
    { key: 'web', label: 'WEB', icon: MessageSquare, count: webChats.length },
    { key: 'telegram', label: 'TG', icon: MessageSquare, count: telegramChats.length },
    { key: 'email', label: 'EMAIL', icon: Mail, count: unreadCount },
  ];

  return (
    <div style={{
      position: 'absolute', top: 0, right: 0, bottom: 0,
      width: '100%', maxWidth: 360,
      background: '#111',
      borderLeft: '1px solid #333',
      display: 'flex', flexDirection: 'column',
      zIndex: 50,
      animation: 'slideIn 0.2s ease-out',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 16px',
        borderBottom: '1px solid #333',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Clock size={16} color="#d4a017" />
          <span style={{ fontWeight: 700, fontSize: 14, color: '#fff' }}>History</span>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => { onNewChat(); onClose(); }}
            style={{
              background: '#d4a017', color: '#000', border: 'none', borderRadius: 6,
              padding: '6px 12px', fontSize: 12, fontWeight: 700, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 4,
              minHeight: 44, minWidth: 44,
            }}
          >
            <Plus size={14} /> New
          </button>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: '1px solid #444', borderRadius: 6,
              color: '#999', cursor: 'pointer', padding: '6px 8px',
              minHeight: 44, minWidth: 44,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
          >
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{
        display: 'flex', borderBottom: '1px solid #333',
        flexShrink: 0,
      }}>
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            style={{
              flex: 1, padding: '10px 0',
              background: tab === t.key ? '#1a1a1a' : 'transparent',
              border: 'none',
              borderBottom: tab === t.key ? '2px solid #d4a017' : '2px solid transparent',
              color: tab === t.key ? '#d4a017' : '#888',
              fontSize: 12, fontWeight: 700, letterSpacing: 1,
              cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
              minHeight: 44,
            }}
          >
            {t.label}
            {(t.count ?? 0) > 0 && (
              <span style={{
                fontSize: 10, background: tab === t.key ? '#d4a017' : '#444',
                color: tab === t.key ? '#000' : '#ccc',
                borderRadius: 10, padding: '1px 6px', fontWeight: 800,
              }}>
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Search (web tab only) */}
      {tab === 'web' && (
        <div style={{ padding: '8px 12px', borderBottom: '1px solid #222', flexShrink: 0 }}>
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              placeholder="Search chats..."
              style={{
                flex: 1, background: '#1a1a1a', border: '1px solid #333',
                borderRadius: 6, padding: '8px 10px', color: '#fff', fontSize: 13,
                outline: 'none', minHeight: 44,
              }}
            />
            <button onClick={handleSearch} style={{
              background: '#222', border: '1px solid #333', borderRadius: 6,
              padding: '0 10px', cursor: 'pointer', color: '#999',
              minHeight: 44, minWidth: 44,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Search size={14} />
            </button>
          </div>
        </div>
      )}

      {/* List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '4px 0' }}>
        {loading && (
          <div style={{ textAlign: 'center', padding: 20, color: '#666', fontSize: 13 }}>
            Loading...
          </div>
        )}

        {/* Web chats */}
        {tab === 'web' && !loading && webChats.map(chat => (
          <div
            key={chat.id}
            onClick={() => { onLoadChat(chat.id); onClose(); }}
            style={{
              padding: '12px 16px',
              borderBottom: '1px solid #1a1a1a',
              cursor: 'pointer',
              minHeight: 44,
              transition: 'background 0.15s',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = '#1a1a1a')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <span style={{
                fontSize: 13, fontWeight: 600, color: '#eee',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                maxWidth: '70%',
              }}>
                {chat.pinned && <Pin size={10} style={{ color: '#d4a017', marginRight: 4 }} />}
                {chat.title}
              </span>
              <span style={{ fontSize: 11, color: '#666' }}>{formatDate(chat.timestamp)}</span>
            </div>
            <div style={{
              fontSize: 12, color: '#888',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              {chat.preview}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
              <span style={{ fontSize: 11, color: '#555' }}>
                {chat.messageCount} messages
              </span>
              <div style={{ display: 'flex', gap: 8 }} onClick={e => e.stopPropagation()}>
                <button
                  onClick={() => handlePin(chat.id, !!chat.pinned)}
                  style={{
                    background: 'none', border: 'none', cursor: 'pointer', padding: 2,
                    color: chat.pinned ? '#d4a017' : '#555',
                  }}
                >
                  <Pin size={12} />
                </button>
                <button
                  onClick={() => handleDelete(chat.id)}
                  style={{
                    background: 'none', border: 'none', cursor: 'pointer', padding: 2,
                    color: '#555',
                  }}
                >
                  <Trash2 size={12} />
                </button>
              </div>
            </div>
          </div>
        ))}

        {tab === 'web' && !loading && webChats.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40, color: '#555', fontSize: 13 }}>
            No conversations yet
          </div>
        )}

        {/* Telegram */}
        {tab === 'telegram' && !loading && telegramChats.map(chat => (
          <div
            key={chat.id}
            style={{
              padding: '12px 16px',
              borderBottom: '1px solid #1a1a1a',
              minHeight: 44,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#eee' }}>{chat.title}</span>
              <span style={{ fontSize: 11, color: '#666' }}>{formatDate(chat.timestamp)}</span>
            </div>
            <div style={{ fontSize: 12, color: '#888', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {chat.preview}
            </div>
            <span style={{ fontSize: 11, color: '#555' }}>{chat.messageCount} messages</span>
          </div>
        ))}

        {tab === 'telegram' && !loading && telegramChats.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40, color: '#555', fontSize: 13 }}>
            No Telegram history
          </div>
        )}

        {/* Email */}
        {tab === 'email' && !loading && emails.map(email => (
          <div
            key={email.id}
            style={{
              padding: '12px 16px',
              borderBottom: '1px solid #1a1a1a',
              minHeight: 44,
              borderLeft: email.unread ? '3px solid #d4a017' : '3px solid transparent',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{
                fontSize: 13, fontWeight: email.unread ? 700 : 500, color: '#eee',
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                maxWidth: '70%',
              }}>
                {email.subject}
              </span>
              <span style={{ fontSize: 11, color: '#666' }}>{formatDate(email.date)}</span>
            </div>
            <div style={{ fontSize: 12, color: '#999', marginBottom: 2 }}>{email.from}</div>
            <div style={{
              fontSize: 12, color: '#666',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}>
              {email.preview}
            </div>
          </div>
        ))}

        {tab === 'email' && !loading && emails.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40, color: '#555', fontSize: 13 }}>
            No emails found
          </div>
        )}
      </div>

      <style>{`
        @keyframes slideIn {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
      `}</style>
    </div>
  );
}
