'use client';
import { useState, useRef, useEffect, useCallback } from 'react';
import { Bell, ChevronDown, Check, ArrowLeft } from 'lucide-react';
import { API } from '../../lib/api';
import LanguageSwitcher from '../LanguageSwitcher';
import ThemeToggle from '../ThemeToggle';
import { EDITION } from '../../v3/edition';

type ProviderRow = {
  id: string;
  name: string;
  provider_canonical?: string;
  models?: string[];
  model?: string;
  available?: boolean;
  configured?: boolean;
  disabled?: boolean;
  disabled_reason?: string | null;
  selected?: boolean;
  primary?: boolean;
  type?: string;
};

const PROVIDER_COLORS: Record<string, string> = {
  minimax: '#b8960c',
  deepseek: '#2563eb',
  qwen: '#06b6d4',
  openrouter: '#0ea5e9',
  groq: '#f97316',
  claude: '#7c3aed',
  openai: '#10b981',
  gemini: '#16a34a',
  xai: '#ef4444',
  ollama: '#0f766e',
  openclaw: '#6b7280',
};

const DISABLED_REASON_LABELS: Record<string, string> = {
  missing_key: 'Missing key',
  disabled_by_kill_switch: 'Kill switch',
  disabled_by_platformforge: 'Disabled',
  ai_calls_disabled: 'AI calls off',
  local_service_unavailable: 'Local service unavailable',
};

const FALLBACK_PROVIDER_MODELS: Record<string, string[]> = {
  groq: [
    'llama-3.3-70b-versatile',
    'llama-3.1-8b-instant',
    'openai/gpt-oss-120b',
    'openai/gpt-oss-20b',
    'qwen/qwen3.8-27b',
  ],
  gemini: [
    'gemini-2.5-flash',
    'gemini-2.5-flash-lite',
    'gemini-3.5-flash',
  ],
  openrouter: [
    'openai/gpt-4o-mini',
    'anthropic/claude-3.5-sonnet',
    'nvidia/nemotron-3-super-120b-a12b:free',
    'google/gemma-4-31b-it:free',
    'cohere/north-mini-code:free',
    'openrouter/free',
  ],
  minimax: ['MiniMax-M3'],
  deepseek: ['deepseek-chat', 'deepseek-reasoner'],
  qwen: ['qwen-plus', 'qwen-max'],
  claude: ['claude-sonnet-4-6', 'claude-opus-4-6'],
  openai: ['gpt-4o', 'gpt-4o-mini'],
  xai: ['grok-3', 'grok-2-vision-1212'],
};

function isFreeTierModel(modelName: string): boolean {
  if (!modelName) return false;
  const m = modelName.toLowerCase();
  if (m.endsWith(':free')) return true;
  if (m.includes('gpt-oss-120b') || m.includes('gpt-oss-20b') || m.includes('gpt-oss')) return true;
  if (m.includes('qwen3.8-27b') || m.includes('qwen3.8')) return true;
  if (m.includes('gemini-2.5-flash-lite') || m.includes('gemini-3.5-flash') || m.includes('gemini-2.5-flash')) return true;
  if (m.includes('openrouter/free')) return true;
  return false;
}

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
  onBack?: () => void; // N2: Global Back button
  canGoBack?: boolean; // N2: false when history is empty (button still visible but disabled)
  services?: any;
}

export default function TopBar({ onQuickSwitch, onClientView, onNavigate, onBack, canGoBack = true }: Props) {
  const [showNotifs, setShowNotifs] = useState(false);
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [expandedProvider, setExpandedProvider] = useState<string | null>(null);
  const [providerRows, setProviderRows] = useState<ProviderRow[]>([]);
  const [selectedProvider, setSelectedProvider] = useState('minimax');
  const [selectedModelName, setSelectedModelName] = useState('MiniMax-M3');
  const [switchingProvider, setSwitchingProvider] = useState(false);
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

  const fetchRoutingModels = useCallback(async () => {
    try {
      const res = await fetch(`${API}/max/models`, { cache: 'no-store' });
      if (!res.ok) return;
      const data = await res.json();
      const models = (data?.models || []) as ProviderRow[];
      setProviderRows(models);
      const selected = models.find(m => m.selected || m.primary) || models[0];
      const state = data?.routing_state || {};
      if (state?.selected_provider) setSelectedProvider(state.selected_provider);
      else if (selected?.provider_canonical) setSelectedProvider(selected.provider_canonical);
      if (state?.selected_model) setSelectedModelName(state.selected_model);
      else if (selected?.model) setSelectedModelName(selected.model);
    } catch { /* offline */ }
  }, []);

  useEffect(() => {
    fetchRoutingModels();
    const iv = setInterval(fetchRoutingModels, 45000);
    return () => clearInterval(iv);
  }, [fetchRoutingModels]);

  const switchProvider = useCallback(async (provider: ProviderRow, specificModel?: string) => {
    if (switchingProvider || provider.disabled || !provider.available) return;
    setSwitchingProvider(true);
    try {
      const targetProvider = provider.provider_canonical || provider.id;
      const targetModel = specificModel || provider.model || provider.models?.[0] || '';
      const res = await fetch(`${API}/max/routing-state`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          selected_provider: targetProvider,
          selected_model: targetModel,
          updated_by: 'founder_or_system',
          reason: 'topbar_selector_switch',
        }),
      });
      if (res.ok) {
        setSelectedProvider(targetProvider);
        setSelectedModelName(targetModel || selectedModelName);
        setShowModelPicker(false);
        await fetchRoutingModels();
      }
    } catch { /* offline */ }
    finally {
      setSwitchingProvider(false);
    }
  }, [fetchRoutingModels, selectedModelName, switchingProvider]);

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

  // Real notifications only (the old sample "Maria — New Quote" placeholders are gone;
  // an empty list shows "No notifications").
  const displayNotifs = notifications;

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
    <header className="v3-band app">
      {/* Logo: mono-E + wordmark (design system v3). "/" is the Max home. */}
      <a href="/" className="logo" title="Max home" aria-label="Empire — Max home"><span className="v3-mono-e">E</span></a>
      <a href="/" className="v3-wm" tabIndex={-1} aria-hidden="true">EMPIRE</a>

      {/* N2: Global Back button. Always visible per Founder spec.
          - Desktop: text label "← Back"
          - Mobile (<768px): icon-only
          - Disabled state (canGoBack === false): history is empty; click still falls back
            to Owner's Desk in page.tsx (it's a no-op visually, but the button is
            still clickable so the user always has a "go home" affordance). */}
      {onBack && (
        <button
          onClick={onBack}
          className={`v3-back${canGoBack ? '' : ' is-off'}`}
          title={canGoBack ? 'Back to previous screen' : 'No previous screen — clicking returns to Owner’s Desk'}
          aria-label="Back"
        >
          <ArrowLeft size={14} />
          <span className="lbl">Back</span>
        </button>
      )}

      {/* Search — hidden on mobile */}
      <button
        onClick={onQuickSwitch}
        className="v3-search"
      >
        <span>Search anything…</span>
        <kbd>⌘K</kbd>
      </button>

      {/* Right controls */}
      <div className="br">
        {/* Model selector — visible on all widths (compact on mobile) */}
        <div ref={modelRef} className="relative">
          <button
            onClick={() => setShowModelPicker(!showModelPicker)}
            className="v3-modelbtn"
            aria-label={`Current model: ${selectedProvider} ${selectedModelName}. Click to switch.`}
            title={`${selectedProvider} · ${selectedModelName}`}
          >
            <span className="w-2 h-2 rounded-full shrink-0" style={{ background: PROVIDER_COLORS[selectedProvider] || '#b8960c' }} />
            <span className="prov">{selectedProvider}</span>
            <span className="mdl">· {selectedModelName}</span>
            <ChevronDown size={12} className="chev" />
          </button>
          {showModelPicker && (
            <div className="absolute top-[46px] right-0 w-[calc(100vw-24px)] sm:w-[380px] max-w-[420px] bg-[#121417] border border-[#b8960c]/40 rounded-2xl shadow-[0_16px_48px_rgba(0,0,0,0.5)] z-[200] overflow-hidden flex flex-col max-h-[82vh]">
              {/* Black & Gold header */}
              <div className="px-4 py-3 border-b border-[#242830] bg-[#0d0f12] flex items-center justify-between shrink-0">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-[#b8960c]" />
                  <span className="text-[11px] font-bold tracking-wider uppercase text-[#d4b84a]">
                    AI Provider & Model Router
                  </span>
                </div>
                <span className="text-[9px] font-mono text-[#888] truncate max-w-[150px]">
                  {selectedProvider} · {selectedModelName}
                </span>
              </div>

              {/* Provider List with Sub-Picker */}
              <div className="overflow-y-auto divide-y divide-[#1e2229] py-1 flex-1">
                {providerRows.map((row) => {
                  const canonical = row.provider_canonical || row.id;
                  const isSelected = canonical === selectedProvider;
                  const color = PROVIDER_COLORS[canonical] || '#6b7280';
                  const models = (row.models && row.models.length > 0)
                    ? row.models
                    : (FALLBACK_PROVIDER_MODELS[canonical] || (row.model ? [row.model] : []));
                  const isExpanded = expandedProvider === canonical || (expandedProvider === null && isSelected);
                  const unavailable = !!row.disabled || !row.available;
                  const disabledReason = row.disabled_reason ? (DISABLED_REASON_LABELS[row.disabled_reason] || row.disabled_reason) : '';
                  const hasFree = models.some(isFreeTierModel);

                  return (
                    <div key={canonical} className={`transition-colors ${isSelected ? 'bg-[#181b22]' : 'hover:bg-[#15181d]'}`}>
                      {/* Provider Row Header */}
                      <div className="px-3 py-2 flex items-center justify-between gap-2">
                        <button
                          onClick={() => switchProvider(row)}
                          disabled={unavailable || switchingProvider}
                          className={`flex items-center gap-2 text-left min-w-0 flex-1 ${unavailable ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                          title={disabledReason || ''}
                        >
                          <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: color }} />
                          <div className="min-w-0">
                            <div className="font-bold text-[12px] text-white flex items-center gap-1.5 truncate">
                              <span>{row.name || canonical}</span>
                              {isSelected && (
                                <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-[#b8960c]/20 text-[#d4b84a] border border-[#b8960c]/40">
                                  ACTIVE
                                </span>
                              )}
                              {hasFree && (
                                <span className="text-[8px] font-mono px-1 py-0.2 rounded bg-[#16a34a]/20 text-[#22c55e] border border-[#16a34a]/30">
                                  FREE TIERS
                                </span>
                              )}
                            </div>
                            <div className="text-[10px] text-[#888] font-mono truncate">
                              {row.model || models[0] || 'default model'}
                              {unavailable ? ` · ${disabledReason || 'unavailable'}` : ''}
                            </div>
                          </div>
                        </button>

                        {/* Expand / Collapse sub-picker button */}
                        {models.length > 0 && (
                          <button
                            onClick={() => setExpandedProvider(isExpanded ? '' : canonical)}
                            className="p-1.5 rounded-lg text-[#888] hover:text-[#d4b84a] hover:bg-[#20252e] transition-colors cursor-pointer shrink-0"
                            title="Toggle models sub-picker"
                            aria-label="Toggle models"
                          >
                            <ChevronDown
                              size={14}
                              className={`transition-transform duration-200 ${isExpanded ? 'rotate-180 text-[#d4b84a]' : ''}`}
                            />
                          </button>
                        )}
                      </div>

                      {/* Models Sub-Picker */}
                      {isExpanded && models.length > 0 && (
                        <div className="px-2.5 pb-2.5 pt-1 space-y-1 bg-[#0f1115]">
                          <div className="text-[9px] font-bold uppercase tracking-wider text-[#777] px-2 pt-0.5 flex justify-between items-center">
                            <span>Available Models ({models.length})</span>
                            <span className="font-mono text-[8px] text-[#555]">Click to select</span>
                          </div>
                          {models.map((modelName) => {
                            const isModelSelected = isSelected && selectedModelName === modelName;
                            const isFree = isFreeTierModel(modelName);

                            return (
                              <button
                                key={modelName}
                                onClick={() => switchProvider(row, modelName)}
                                disabled={unavailable || switchingProvider}
                                className={`w-full text-left p-2 rounded-xl transition-all border ${
                                  isModelSelected
                                    ? 'bg-[#1c2029] border-[#b8960c] text-white shadow-sm'
                                    : 'bg-[#14171d] border-[#22262f] hover:border-[#383e4c] text-[#ccc] hover:text-white'
                                } ${unavailable ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}`}
                              >
                                <div className="flex items-center justify-between gap-2">
                                  <span className="font-mono text-[11px] font-bold truncate">
                                    {modelName}
                                  </span>
                                  {isFree ? (
                                    <span className="text-[8px] font-bold px-1.5 py-0.5 rounded bg-[#16a34a]/25 text-[#22c55e] border border-[#16a34a]/40 uppercase shrink-0">
                                      FREE
                                    </span>
                                  ) : (
                                    <span className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-[#242832] text-[#999] shrink-0">
                                      PAID
                                    </span>
                                  )}
                                </div>

                                {isFree ? (
                                  <div className="mt-1 space-y-0.5">
                                    <div className="text-[10px] font-mono font-semibold text-[#b8960c]">
                                      $0 · limits
                                    </div>
                                    <div className="text-[9px] text-[#fca5a5] flex items-center gap-1 font-medium">
                                      <span>✕</span>
                                      <span>not for quotes, invoices or client replies</span>
                                    </div>
                                  </div>
                                ) : (
                                  <div className="mt-0.5 text-[9px] text-[#777] font-mono">
                                    Standard provider API rates apply
                                  </div>
                                )}
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
                {providerRows.length === 0 && (
                  <div className="px-3 py-4 text-center text-[10px] text-[var(--muted)]">No providers loaded</div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Dark / Gold theme (per device) */}
        <ThemeToggle />

        {/* Language Switcher */}
        <LanguageSwitcher />

        {/* Notifications */}
        <div ref={notifRef} className="relative">
          <button
            onClick={() => setShowNotifs(!showNotifs)}
            className="icon-btn"
            aria-label={`Notifications${unreadCount ? `: ${unreadCount} unread` : ''}`}
          >
            <Bell size={17} strokeWidth={1.5} />
            {unreadCount > 0 && <span className="badge">{unreadCount > 9 ? '9+' : unreadCount}</span>}
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
        <button onClick={onClientView} className="icon-btn hide-sm" aria-label="Client view (hide internal data)" title="Client view">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="3"/><path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72 1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
          </svg>
        </button>

        {/* Avatar */}
        <span className="v3-av" aria-label={EDITION.ownerName}>{EDITION.ownerInitials}</span>
      </div>
    </header>
  );
}
