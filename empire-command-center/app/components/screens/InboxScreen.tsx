'use client';
import { useState, useEffect } from 'react';
import { API } from '../../lib/api';
import { Inbox, Bell, CheckCircle, Clock, AlertTriangle, RefreshCw, Filter } from 'lucide-react';

interface InboxItem {
  id: string;
  type: string;
  title: string;
  body: string;
  timestamp: string;
  read: boolean;
  priority?: 'high' | 'normal' | 'low';
  source?: string;
}

export default function InboxScreen() {
  const [items, setItems] = useState<InboxItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'unread' | 'high'>('all');
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    loadInbox();
  }, []);

  const loadInbox = async () => {
    setLoading(true);
    try {
      // Try notifications endpoint
      const res = await fetch(API + '/notifications');
      if (res.ok) {
        const data = await res.json();
        const notifs = data.notifications || data.items || data || [];
        setItems(notifs.map((n: any, i: number) => ({
          id: n.id || String(i),
          type: n.type || 'notification',
          title: n.title || n.subject || 'Notification',
          body: n.body || n.message || n.content || '',
          timestamp: n.timestamp || n.created_at || new Date().toISOString(),
          read: n.read || false,
          priority: n.priority || 'normal',
          source: n.source || n.desk || 'system',
        })));
      } else {
        // Fallback: build inbox from multiple sources
        const [quotesRes, desksRes] = await Promise.allSettled([
          fetch(API + '/quotes?limit=5').then(r => r.json()),
          fetch(API + '/max/desks/status').then(r => r.json()),
        ]);

        const inbox: InboxItem[] = [];

        if (quotesRes.status === 'fulfilled') {
          const quotes = quotesRes.value.quotes || quotesRes.value || [];
          quotes.filter((q: any) => q.status === 'draft' || q.status === 'sent').forEach((q: any, i: number) => {
            inbox.push({
              id: `q-${i}`,
              type: 'quote',
              title: `Quote ${q.quote_number} — ${q.customer_name}`,
              body: `$${(q.total || 0).toLocaleString()} · Status: ${q.status}`,
              timestamp: q.created_at || new Date().toISOString(),
              read: false,
              priority: q.total > 5000 ? 'high' : 'normal',
              source: 'workroom',
            });
          });
        }

        if (desksRes.status === 'fulfilled') {
          const statuses = desksRes.value.desks || [];
          statuses.filter((d: any) => d.current_task).forEach((d: any) => {
            inbox.push({
              id: `d-${d.id}`,
              type: 'desk',
              title: `${d.name} — Task in progress`,
              body: d.current_task?.description || 'Working...',
              timestamp: new Date().toISOString(),
              read: false,
              priority: 'normal',
              source: d.id,
            });
          });
        }

        // Always show some system items
        inbox.push(
          { id: 'sys-1', type: 'system', title: 'Empire Backend', body: 'All services running on port 8000', timestamp: new Date().toISOString(), read: true, priority: 'low', source: 'system' },
          { id: 'sys-2', type: 'system', title: 'Command Center', body: 'Running on port 3009', timestamp: new Date().toISOString(), read: true, priority: 'low', source: 'system' },
        );

        setItems(inbox);
      }
    } catch {
      setItems([
        { id: 'err', type: 'system', title: 'Could not load inbox', body: 'Backend may be offline', timestamp: new Date().toISOString(), read: false, priority: 'high', source: 'system' },
      ]);
    }
    setLoading(false);
  };

  const filtered = items.filter(item => {
    if (filter === 'unread') return !item.read;
    if (filter === 'high') return item.priority === 'high';
    return true;
  });

  const typeIcons: Record<string, string> = { quote: '💰', desk: '🤖', system: '⚙️', alert: '🔔', shipping: '🚚', notification: '📌' };
  const priorityColors: Record<string, string> = { high: '#dc2626', normal: '#b8960c', low: '#aaa' };

  return (
    <div className="flex-1 overflow-y-auto" style={{ padding: '28px 36px' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-[var(--radius)] flex items-center justify-center" style={{ background: 'var(--gold-light)' }}>
            <Inbox size={20} style={{ color: 'var(--gold)' }} />
          </div>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 600, color: 'var(--text)' }}>Inbox</h1>
            <p style={{ fontSize: 13, color: 'var(--dim)' }}>{items.filter(i => !i.read).length} unread · {items.length} total</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            {(['all', 'unread', 'high'] as const).map(f => (
              <button key={f} onClick={() => setFilter(f)}
                className={`filter-tab ${filter === f ? 'active' : ''}`}>
                {f === 'high' ? 'Priority' : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
          <button onClick={loadInbox}
            className="empire-card flat"
            style={{ padding: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center', width: 38, height: 38, cursor: 'pointer' }}>
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} style={{ color: 'var(--dim)' }} />
          </button>
        </div>
      </div>

      {/* Section label */}
      <div className="section-label" style={{ marginBottom: 12 }}>Messages</div>

      {/* Inbox items */}
      <div className="space-y-2">
        {filtered.map(item => (
          <div key={item.id}
            onClick={() => setExpanded(expanded === item.id ? null : item.id)}
            className={`empire-card ${!item.read ? 'active' : ''}`}
            style={{ padding: '14px 18px' }}>
            <div className="flex items-start gap-3">
              <span className="text-lg mt-0.5">{typeIcons[item.type] || '📌'}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span style={{ fontSize: 14, fontWeight: 600, color: !item.read ? 'var(--text)' : 'var(--dim)' }}>{item.title}</span>
                  {!item.read && <span className="w-2 h-2 rounded-full" style={{ background: 'var(--gold)' }} />}
                </div>
                <div style={{ fontSize: 12, color: 'var(--dim)', marginTop: 3 }}>{item.body}</div>
                {expanded === item.id && item.body.length > 50 && (
                  <div className="empire-card flat" style={{ marginTop: 10, padding: '10px 14px', fontSize: 12, color: 'var(--text-secondary)', cursor: 'default' }}>
                    {item.body}
                  </div>
                )}
                <div className="flex items-center gap-3 mt-2">
                  <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--faint)' }} suppressHydrationWarning>{formatTimestamp(item.timestamp)}</span>
                  <span className="status-pill" style={{
                    color: priorityColors[item.priority || 'normal'],
                    background: (priorityColors[item.priority || 'normal']) + '15',
                    padding: '2px 8px', fontSize: 10
                  }}>
                    {(item.priority || 'normal').toUpperCase()}
                  </span>
                  {item.source && <span style={{ fontSize: 10, color: 'var(--muted)' }}>via {item.source}</span>}
                </div>
              </div>
            </div>
          </div>
        ))}

        {filtered.length === 0 && !loading && (
          <div className="text-center py-16">
            <CheckCircle size={36} style={{ color: 'var(--faint)' }} className="mx-auto mb-3" />
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--muted)' }}>All caught up</div>
            <div style={{ fontSize: 12, color: 'var(--faint)', marginTop: 4 }}>No {filter === 'all' ? '' : filter + ' '}items</div>
          </div>
        )}

        {loading && (
          <div className="text-center py-10">
            <RefreshCw size={24} style={{ color: 'var(--faint)' }} className="mx-auto mb-2 animate-spin" />
            <div style={{ fontSize: 14, color: 'var(--muted)' }}>Loading inbox...</div>
          </div>
        )}
      </div>
    </div>
  );
}

function formatTimestamp(ts: string): string {
  try {
    const d = new Date(ts);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  } catch { return ts; }
}
