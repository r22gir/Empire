'use client';
import { useState, useRef, useEffect, useCallback } from 'react';
import { Bell, ChevronDown, ExternalLink, Check } from 'lucide-react';
import { API } from '../../lib/api';

const MODELS = [
  { id: 'grok-3-fast', label: 'xAI Grok', desc: 'Primary · Fast', color: '#b8960c' },
  { id: 'claude-sonnet-4-6', label: 'Claude Sonnet', desc: 'Anthropic · Balanced', color: '#7c3aed' },
  { id: 'claude-opus-4-6', label: 'Claude Opus', desc: 'Anthropic · Advanced', color: '#9333ea' },
  { id: 'groq', label: 'Groq Llama 3.3', desc: 'Groq · 70B · Ultra-fast', color: '#f97316' },
  { id: 'llama3.1:8b', label: 'Llama 3.1 (Ollama)', desc: 'Local · 8B', color: '#06b6d4' },
  { id: 'auto', label: 'Auto', desc: 'Best available', color: '#22c55e' },
];
const MODEL_LABELS: Record<string, string> = Object.fromEntries(MODELS.map(m => [m.id, m.label]));

// Map notification sources to navigation targets
const NOTIF_NAV_MAP: Record<string, { product?: string; screen?: string }> = {
  quote: { product: 'workroom', screen: 'dashboard' },
  shipping: { product: 'workroom', screen: 'shipping' },
  invoice: { product: 'workroom', screen: 'dashboard' },
  desk: { screen: 'desks' },
  system: { product: 'platform', screen: 'dashboard' },
  telegram: { screen: 'telegram' },
  brain: { product: 'platform', screen: 'dashboard' },
  inventory: { product: 'workroom', screen: 'dashboard' },
  customer: { product: 'workroom', screen: 'dashboard' },
  social: { product: 'social', screen: 'dashboard' },
};

interface Notification {
  id: string;
  title: string;
  message: string;
  category: string;
  source: string;
  created_at: string;
  read: boolean;
  url?: string;
}

interface Props {
  onQuickSwitch: () => void;
  onClientView: () => void;
  onNavigate?: (product: string, screen: string) => void;
  services?: any;
}

export default function TopBar({ onQuickSwitch, onClientView, onNavigate, services }: Props) {
  const [showNotifs, setShowNotifs] = useState(false);
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [selectedModel, setSelectedModel] = useState('grok-3-fast');
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const notifRef = useRef<HTMLDivElement>(null);
  const modelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setShowNotifs(false);
      if (modelRef.current && !modelRef.current.contains(e.target as Node)) setShowModelPicker(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Fetch notifications
  const fetchNotifs = useCallback(async () => {
    try {
      const res = await fetch(`${API}/notifications`);
      if (res.ok) {
        const data = await res.json();
        setNotifications((data.notifications || data || []).slice(0, 20));
      }
    } catch { /* offline */ }
  }, []);

  useEffect(() => {
    fetchNotifs();
    const iv = setInterval(fetchNotifs, 30000);
    return () => clearInterval(iv);
  }, [fetchNotifs]);

  const unreadCount = notifications.filter(n => !n.read).length;

  const markRead = async (id: string) => {
    try {
      await fetch(`${API}/notifications/${id}/read`, { method: 'PATCH' });
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
    } catch { /* */ }
  };

  const handleNotifClick = (notif: Notification) => {
    markRead(notif.id);
    // Navigate based on notification category/source
    const cat = (notif.category || notif.source || '').toLowerCase();
    for (const [key, nav] of Object.entries(NOTIF_NAV_MAP)) {
      if (cat.includes(key) || (notif.title || '').toLowerCase().includes(key)) {
        onNavigate?.(nav.product || 'owner', nav.screen || 'dashboard');
        setShowNotifs(false);
        return;
      }
    }
    // Default: close dropdown
    setShowNotifs(false);
  };

  const formatTime = (ts: string) => {
    if (!ts) return '';
    const diff = Date.now() - new Date(ts).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'now';
    if (mins < 60) return `${mins}m`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h`;
    return `${Math.floor(hrs / 24)}d`;
  };

  // Fallback notifications if API returns none
  const displayNotifs = notifications.length > 0 ? notifications : [
    { id: '1', title: 'Maria — New Quote', message: 'Request for living room valances', category: 'quote', source: 'Empire', created_at: '', read: false },
    { id: '2', title: 'Emily — Shipping', message: 'Valance order picked up', category: 'shipping', source: 'Empire', created_at: '', read: false },
    { id: '3', title: 'Aria Desk', message: 'Instagram post drafted', category: 'desk', source: 'Empire', created_at: '', read: true },
    { id: '4', title: 'System', message: 'All services healthy', category: 'system', source: 'Empire', created_at: '', read: true },
  ];

  const catColor = (cat: string): string => {
    const c = cat.toLowerCase();
    if (c.includes('quote')) return '#b8960c';
    if (c.includes('ship')) return '#2563eb';
    if (c.includes('desk') || c.includes('social')) return '#ec4899';
    if (c.includes('system') || c.includes('brain')) return '#16a34a';
    if (c.includes('telegram')) return '#06b6d4';
    return '#777';
  };

  return (
    <header className="h-[56px] bg-[var(--panel)] border-b border-[var(--border)] flex items-center justify-between px-3 md:px-6 shrink-0 z-50">
      {/* Logo */}
      <div className="text-[16px] font-bold tracking-[3px] text-[var(--text)]">
        <span className="text-[var(--gold)]">E</span>MPIRE
      </div>

      {/* Search — hidden on mobile */}
      <button
        onClick={onQuickSwitch}
        className="hidden md:flex items-center gap-2 bg-[#f5f3ef] border border-[var(--border)] rounded-[var(--radius)] px-5 py-[10px] w-[320px] text-[13px] text-[var(--faint)] cursor-pointer hover:border-[var(--border-h)] transition-colors"
      >
        <span className="text-[11px] font-mono">⌘K</span>
        <span>Search anything...</span>
      </button>

      {/* Right controls */}
      <div className="flex items-center gap-2 md:gap-3">
        {/* Model selector — hidden on mobile */}
        <div ref={modelRef} className="relative hidden md:block">
          <button
            onClick={() => setShowModelPicker(!showModelPicker)}
            className="empire-card flex items-center gap-2 !py-2 !px-3 text-[11px] font-bold font-mono"
          >
            <span className="w-2 h-2 rounded-full" style={{ background: MODELS.find(m => m.id === selectedModel)?.color || '#b8960c' }} />
            <span style={{ color: MODELS.find(m => m.id === selectedModel)?.color || '#b8960c' }}>
              {MODEL_LABELS[selectedModel] || selectedModel}
            </span>
            <ChevronDown size={12} className="text-[var(--faint)]" />
          </button>
          {showModelPicker && (
            <div className="absolute top-[46px] right-0 w-[220px] bg-[var(--panel)] border border-[var(--border)] rounded-[var(--radius)] shadow-[0_8px_30px_rgba(0,0,0,0.12)] z-[200] overflow-hidden py-1">
              {MODELS.map(m => (
                <button key={m.id}
                  onClick={() => { setSelectedModel(m.id); setShowModelPicker(false); }}
                  className={`w-full text-left px-3 py-2.5 text-[11px] flex items-center gap-2 transition-colors cursor-pointer ${selectedModel === m.id ? 'bg-[var(--card-bg)]' : 'hover:bg-[var(--hover)]'}`}>
                  <span className="w-2 h-2 rounded-full" style={{ background: m.color }} />
                  <div>
                    <div className="font-bold" style={{ color: m.color }}>{m.label}</div>
                    <div className="text-[9px] text-[var(--muted)]">{m.desc}</div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Notifications */}
        <div ref={notifRef} className="relative">
          <button
            onClick={() => setShowNotifs(!showNotifs)}
            className="empire-card !p-2 relative"
          >
            <Bell size={16} className="text-[var(--dim)]" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 bg-[#dc2626] text-white text-[8px] font-bold w-4 h-4 rounded-full flex items-center justify-center">{unreadCount}</span>
            )}
          </button>
          {showNotifs && (
            <div className="absolute top-[46px] right-0 w-[calc(100vw-24px)] md:w-[380px] max-w-[380px] bg-[var(--panel)] border border-[var(--border)] rounded-2xl shadow-[0_12px_40px_rgba(0,0,0,0.15)] z-[200] overflow-hidden">
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
                <div className="flex items-center gap-2">
                  <span className="text-[14px] font-bold text-[var(--text)]">Notifications</span>
                  {unreadCount > 0 && (
                    <span className="text-[10px] font-bold text-white bg-[#dc2626] px-2 py-0.5 rounded-full">{unreadCount} new</span>
                  )}
                </div>
                <button
                  onClick={() => displayNotifs.forEach(n => markRead(n.id))}
                  className="text-[11px] text-[var(--gold)] font-semibold cursor-pointer hover:underline"
                >
                  Mark all read
                </button>
              </div>

              {/* Notification list */}
              <div className="max-h-[420px] overflow-y-auto">
                {displayNotifs.map(n => {
                  const color = catColor(n.category || n.source);
                  return (
                    <div
                      key={n.id}
                      onClick={() => handleNotifClick(n)}
                      className={`px-4 py-3 cursor-pointer transition-all border-b border-[var(--border)] hover:bg-[var(--hover)] ${!n.read ? 'bg-[#fdf8eb]' : ''}`}
                    >
                      <div className="flex items-start gap-3">
                        {/* Color dot */}
                        <div className="mt-1.5 shrink-0">
                          <span className="w-2 h-2 rounded-full block" style={{ background: !n.read ? color : '#ddd' }} />
                        </div>

                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-0.5">
                            <span className="text-[12px] font-bold text-[var(--text)] truncate">{n.title}</span>
                            <span className="status-pill" style={{ background: `${color}15`, color, fontSize: 8, padding: '1px 6px' }}>
                              {n.category || n.source || 'update'}
                            </span>
                          </div>
                          <div className="text-[11px] text-[var(--dim)] leading-snug truncate">{n.message}</div>
                        </div>

                        {/* Time + read indicator */}
                        <div className="flex flex-col items-end gap-1 shrink-0">
                          <span className="text-[9px] text-[var(--faint)] font-mono whitespace-nowrap">
                            {n.created_at ? formatTime(n.created_at) : ''}
                          </span>
                          {!n.read && (
                            <button
                              onClick={(e) => { e.stopPropagation(); markRead(n.id); }}
                              className="text-[var(--faint)] hover:text-[var(--gold)] cursor-pointer"
                              title="Mark as read"
                            >
                              <Check size={12} />
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}

                {displayNotifs.length === 0 && (
                  <div className="py-10 text-center">
                    <Bell size={24} className="text-[#ddd] mx-auto mb-2" />
                    <div className="text-[12px] text-[var(--faint)]">No notifications</div>
                  </div>
                )}
              </div>

              {/* Footer */}
              <div className="px-4 py-2.5 border-t border-[var(--border)] text-center">
                <button className="text-[11px] text-[var(--gold)] font-semibold cursor-pointer hover:underline">
                  View all notifications
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Settings */}
        <button onClick={onClientView} className="empire-card !p-2">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[var(--dim)]">
            <circle cx="12" cy="12" r="3"/><path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72 1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
          </svg>
        </button>

        {/* Avatar */}
        <div className="w-[36px] h-[36px] rounded-[12px] bg-[var(--gold)] text-white flex items-center justify-center text-[12px] font-bold cursor-pointer">
          RG
        </div>
      </div>
    </header>
  );
}
