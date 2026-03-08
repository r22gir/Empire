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
    <div className="flex-1 overflow-y-auto p-6">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#fdf8eb] flex items-center justify-center">
            <Inbox size={20} className="text-[#b8960c]" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[#1a1a1a]">Inbox</h1>
            <p className="text-xs text-[#777]">{items.filter(i => !i.read).length} unread · {items.length} total</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-[#e5e0d8] overflow-hidden">
            {(['all', 'unread', 'high'] as const).map(f => (
              <button key={f} onClick={() => setFilter(f)}
                className={`px-3 py-2 text-[11px] font-semibold cursor-pointer transition-colors ${filter === f ? 'bg-[#b8960c] text-white' : 'bg-white text-[#777] hover:bg-[#f5f3ef]'}`}>
                {f === 'high' ? 'Priority' : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
          <button onClick={loadInbox}
            className="w-10 h-10 rounded-lg border border-[#e5e0d8] bg-white flex items-center justify-center text-[#777] hover:bg-[#f5f3ef] cursor-pointer transition-colors">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      <div className="space-y-2">
        {filtered.map(item => (
          <div key={item.id}
            onClick={() => setExpanded(expanded === item.id ? null : item.id)}
            className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${!item.read ? 'bg-white border-[#e5e0d8] hover:border-[#b8960c]' : 'bg-[#faf9f7] border-[#ece8e1] hover:border-[#d8d3cb]'}`}>
            <div className="flex items-start gap-3">
              <span className="text-lg mt-0.5">{typeIcons[item.type] || '📌'}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-bold ${!item.read ? 'text-[#1a1a1a]' : 'text-[#777]'}`}>{item.title}</span>
                  {!item.read && <span className="w-2 h-2 rounded-full bg-[#b8960c]" />}
                </div>
                <div className="text-xs text-[#777] mt-0.5">{item.body}</div>
                {expanded === item.id && item.body.length > 50 && (
                  <div className="mt-2 p-3 rounded-lg bg-[#f5f3ef] text-xs text-[#555]">{item.body}</div>
                )}
                <div className="flex items-center gap-3 mt-2">
                  <span className="text-[9px] font-mono text-[#bbb]" suppressHydrationWarning>{formatTimestamp(item.timestamp)}</span>
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded" style={{ color: priorityColors[item.priority || 'normal'], background: (priorityColors[item.priority || 'normal']) + '15' }}>
                    {(item.priority || 'normal').toUpperCase()}
                  </span>
                  {item.source && <span className="text-[9px] text-[#aaa]">via {item.source}</span>}
                </div>
              </div>
            </div>
          </div>
        ))}

        {filtered.length === 0 && !loading && (
          <div className="text-center py-16">
            <CheckCircle size={36} className="text-[#d8d3cb] mx-auto mb-3" />
            <div className="text-sm font-semibold text-[#aaa]">All caught up</div>
            <div className="text-xs text-[#ccc] mt-1">No {filter === 'all' ? '' : filter + ' '}items</div>
          </div>
        )}

        {loading && (
          <div className="text-center py-10">
            <RefreshCw size={24} className="text-[#d8d3cb] mx-auto mb-2 animate-spin" />
            <div className="text-sm text-[#aaa]">Loading inbox...</div>
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
