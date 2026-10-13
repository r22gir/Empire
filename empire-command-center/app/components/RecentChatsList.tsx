'use client';
import { useEffect, useState } from 'react';
import { Clock, ChevronRight } from 'lucide-react';
import { API } from '../lib/api';
import { useTranslation } from '../lib/i18n';

interface ChatEntry {
  id: string;
  title: string;
  preview: string;
  timestamp: string;
}

interface Props {
  onLoadChat?: (chatId: string) => void;
  onOpenHistory: () => void;
}

function formatWhen(ts: string) {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) return ts.slice(0, 16);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 86400000) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (diff < 604800000) return d.toLocaleDateString([], { weekday: 'short' });
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  } catch {
    return ts.slice(0, 10);
  }
}

export default function RecentChatsList({ onLoadChat, onOpenHistory }: Props) {
  const { t } = useTranslation();
  const [chats, setChats] = useState<ChatEntry[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(API + '/chats/list', { credentials: 'include', cache: 'no-store' })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (cancelled || !data) return;
        const items = (data.chats || []).slice(0, 5).map((c: any) => ({
          id: c.id,
          title: c.title || 'Untitled',
          preview: c.preview || '',
          timestamp: c.updated_at || c.created_at || '',
        }));
        setChats(items);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!loaded) return null;

  return (
    <div
      data-testid="chat-recent-list"
      style={{
        margin: '8px 0 16px',
        padding: 12,
        borderRadius: 16,
        background: '#fff',
        border: '1px solid var(--border)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8, gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          <Clock size={14} color="#b8960c" />
          <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--text)' }}>
            {t('max.recent_chats')}
          </span>
        </div>
        <button
          type="button"
          onClick={onOpenHistory}
          style={{
            background: 'none',
            border: 'none',
            color: '#b8960c',
            fontSize: 12,
            fontWeight: 700,
            cursor: 'pointer',
            minHeight: 44,
            padding: '0 8px',
            flexShrink: 0,
          }}
        >
          {t('max.see_all_history')}
        </button>
      </div>
      {chats.length === 0 ? (
        <div style={{ fontSize: 13, color: 'var(--text-muted)', padding: '8px 2px 4px' }}>
          {t('max.no_recent_chats')}
        </div>
      ) : (
        chats.map((chat) => (
          <button
            key={chat.id}
            type="button"
            onClick={() => onLoadChat?.(chat.id)}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              textAlign: 'left',
              background: '#faf9f7',
              border: '1px solid #eeeae3',
              borderRadius: 12,
              padding: '12px 12px',
              marginBottom: 8,
              cursor: 'pointer',
              minHeight: 56,
            }}
          >
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 2 }}>
                <span style={{
                  fontSize: 14,
                  fontWeight: 700,
                  color: 'var(--text)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>
                  {chat.title}
                </span>
                <span style={{ fontSize: 11, color: '#888', flexShrink: 0 }}>{formatWhen(chat.timestamp)}</span>
              </div>
              <div style={{
                fontSize: 12,
                color: '#777',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {chat.preview}
              </div>
            </div>
            <ChevronRight size={16} color="#bbb" />
          </button>
        ))
      )}
    </div>
  );
}
