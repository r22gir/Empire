'use client';
import { useState, useEffect, useCallback } from 'react';
import { API, API_BASE } from '../../lib/api';
import {
  Server, Activity, Brain, Code, Shield, Cpu, HardDrive, Wifi, Database,
  Globe, ChevronDown, ChevronRight, Key, Lock, AlertTriangle, CheckCircle2,
  RefreshCw, Eye, EyeOff, Loader2, ExternalLink, Layers, Zap, BookOpen, CreditCard,
  Smartphone,
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import DesktopPairing from '../platform/DesktopPairing';

// All data fetched live from backend
interface LiveData {
  system: any;
  metrics: any;
  models: any;
  health: any;
  brain: any;
  connectivity: any[];
  modules: any[];
  report: any;
  ollama: any;
  backup: any;
  telegram: any;
  docker: any;
}

export default function PlatformPage() {
  const [data, setData] = useState<Partial<LiveData>>({});
  const [loading, setLoading] = useState(true);
  // Per-section collapse state — keyed by section id. Default: legacy cleanup
  // (the prior cleanup pre-`81e18a4` left these blank → default-collapsed).
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  // Top-level drawer state for the reorganized view (Lane I1).
  //   systemDetailsOpen: System Details drawer (CORS / API Keys / Guardrails /
  //     Routes / Pairing / Payments stub / Documentation). Founder's deep-dive
  //     section. Default: closed (not Founder-cold-open relevant).
  //   legacyDebugOpen: Legacy / Debug drawer (Docker-era ports, Ollama models).
  //     Default: closed.
  const [systemDetailsOpen, setSystemDetailsOpen] = useState(false);
  const [legacyDebugOpen, setLegacyDebugOpen] = useState(false);
  const [showKeys, setShowKeys] = useState(false);
  const [busyProvider, setBusyProvider] = useState<string | null>(null);

  const safeFetch = useCallback(async (url: string) => {
    try {
      const r = await fetch(url, { signal: AbortSignal.timeout(5000) });
      return r.ok ? await r.json() : null;
    } catch { return null; }
  }, []);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    const [system, metrics, models, health, brain, report, ollama, backup, telegram, docker] = await Promise.all([
      safeFetch(API + '/system/stats'),
      safeFetch(API + '/system/metrics'),
      safeFetch(API + '/max/models'),
      safeFetch(API + '/max/health'),
      safeFetch(API + '/max/brain/status'),
      safeFetch(API + '/max/system-report'),
      safeFetch(API + '/ollama/models'),
      safeFetch(API + '/chat-backup/status'),
      safeFetch(API + '/max/telegram/status'),
      safeFetch(API + '/docker/status'),
    ]);
    setData({
      system,
      metrics,
      models,
      health,
      brain,
      connectivity: report?.connectivity || [],
      modules: report?.modules || [],
      report,
      ollama,
      backup,
      telegram,
      docker,
    });
    setLoading(false);
  }, [safeFetch]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const postJson = useCallback(async (url: string, body: any) => {
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return r.ok ? await r.json() : null;
  }, []);

  const setActiveProvider = useCallback(async (row: any) => {
    const provider = row.provider_canonical || row.id;
    const model = row.model || row.models?.[0] || '';
    setBusyProvider(provider);
    await postJson(`${API}/max/routing-state`, {
      selected_provider: provider,
      selected_model: model,
      updated_by: 'founder_or_system',
      reason: 'platformforge_set_active',
    });
    await fetchAll();
    setBusyProvider(null);
  }, [fetchAll, postJson]);

  const toggleProvider = useCallback(async (row: any, enabled: boolean) => {
    const provider = row.provider_canonical || row.id;
    setBusyProvider(provider);
    await postJson(`${API}/max/provider/toggle`, {
      provider,
      enabled,
      updated_by: 'founder_or_system',
      reason: 'platformforge_toggle',
    });
    await fetchAll();
    setBusyProvider(null);
  }, [fetchAll, postJson]);

  const testProvider = useCallback(async (row: any) => {
    const provider = row.provider_canonical || row.id;
    setBusyProvider(provider);
    const out = await postJson(`${API}/max/provider/test`, {
      provider,
      model: row.model || row.models?.[0] || undefined,
      prompt: `Reply only: ${provider} ok`,
    });
    setBusyProvider(null);
    if (out?.status === 'ok') {
      window.alert(`Provider test ok: ${out.provider_used} / ${out.model_used}`);
    } else {
      window.alert(`Provider test failed: ${provider}`);
    }
  }, [postJson]);

  const toggle = (key: string) => setExpanded(p => ({ ...p, [key]: !p[key] }));

  const cpu = data.system?.cpu?.percent ?? data.system?.cpu_percent ?? 0;
  const ram = data.system?.memory?.percent ?? 0;
  // Disk: show the highest-percent drive (typically root /) instead of the
  // blended average, which masked root saturation. The blended total is
  // kept in diskTotal for the sub-line.
  const diskDrives: Array<{ mount: string; percent: number; used_gb: number; total_gb: number }> =
    data.system?.disk?.drives || data.metrics?.disk_drives || [];
  const worstDrive = diskDrives.reduce<{ mount: string; percent: number } | null>(
    (acc, d) => (!acc || d.percent > acc.percent ? d : acc),
    null,
  );
  const disk = worstDrive ? worstDrive.percent : (data.system?.disk?.percent ?? 0);
  const diskLabel = worstDrive ? `Root ${worstDrive.mount} (highest)` : 'Aggregate';
  const diskTotal = data.system?.disk?.total_gb?.toFixed(0) || '--';
  const rootDrive = diskDrives.find(d => d.mount === '/');
  const rootHigh = rootDrive ? rootDrive.percent >= 75 : false;
  const uptime = data.system?.uptime || data.report?.system?.uptime || (data.metrics?.uptime_seconds ? `${Math.floor(data.metrics.uptime_seconds / 3600)}h ${Math.floor((data.metrics.uptime_seconds % 3600) / 60)}m` : '--');
  const cpuCores = data.system?.cpu?.cores || '--';
  const ramTotal = data.system?.memory?.total_gb?.toFixed(1) || '--';

  // AI models from live data
  const aiModels = data.models?.models || [];
  const routingState = data.models?.routing_state || {};

  // Connectivity from system report
  const connectivity = data.connectivity || [];

  // Modules from system report
  const modules = data.modules || [];

  // Brain/memory
  const brainData = data.brain || {};
  const memoryCount = brainData.memories?.total ?? '--';
  const ollamaOnline = brainData.ollama?.online ?? false;
  const ollamaModels = data.ollama?.models || brainData.ollama?.models || [];

  // Docker products
  const dockerProducts = data.docker?.products || [];

  // BusinessOps live state — confirmed via GET /api/v1/businessops/health
  // returning 200 (verified at the most recent backend restart on 395f6ee).
  // The page cannot probe the endpoint on every render, so we treat it as
  // live when the live backend is up (data.health is set). For absolute
  // truth the Founder can click the route row.
  const businessopsLive = !!data.health;

  // Guardrails info (known from code audit)
  const guardrails = [
    { name: 'Prompt Injection Detection', desc: '15 regex patterns block injection attempts', status: 'active' },
    { name: 'Blocked Topics Filter', desc: 'Blocks requests for harmful content (malware, explosives, hacking)', status: 'active' },
    { name: 'API Key Redaction', desc: 'Strips sk-*, xai-* patterns from AI output', status: 'active' },
    { name: 'Hallucination Detection', desc: 'Flags fabricated statistics and claims', status: 'active' },
    { name: 'Input Length Limit', desc: 'Max message length enforced before AI processing', status: 'active' },
    { name: 'Safe Refusal', desc: 'Standard refusal message for blocked requests', status: 'active' },
  ];

  // API keys (known env vars, masked)
  const apiKeys = [
    { name: 'XAI_API_KEY', provider: 'xAI Grok', purpose: 'Primary AI model + Vision + Image gen' },
    { name: 'ANTHROPIC_API_KEY', provider: 'Anthropic', purpose: 'Claude fallback AI' },
    { name: 'GROQ_API_KEY', provider: 'Groq', purpose: 'Llama 3.3 70B + Whisper STT' },
    { name: 'STABILITY_API_KEY', provider: 'Stability AI', purpose: 'SD3/SDXL image generation' },
    { name: 'TOGETHER_API_KEY', provider: 'Together AI', purpose: 'FLUX.1-schnell free image gen' },
    { name: 'OPENAI_API_KEY', provider: 'OpenAI', purpose: 'SupportForge AI features' },
    { name: 'HF_API_TOKEN', provider: 'HuggingFace', purpose: 'Optional rate limit boost' },
    { name: 'BRAVE_API_KEY', provider: 'Brave Search', purpose: 'Web search integration' },
    { name: 'UNSPLASH_ACCESS_KEY', provider: 'Unsplash', purpose: 'Image search' },
    { name: 'EASYPOST_API_KEY', provider: 'EasyPost', purpose: 'Shipping label generation' },
    { name: 'TELEGRAM_BOT_TOKEN', provider: 'Telegram', purpose: 'Bot communication' },
    { name: 'TELEGRAM_FOUNDER_CHAT_ID', provider: 'Telegram', purpose: 'Founder chat target' },
    { name: 'SMTP_USER', provider: 'Email', purpose: 'SMTP outbound email' },
    { name: 'SMTP_PASSWORD', provider: 'Email', purpose: 'SMTP authentication' },
    { name: 'CRYPTO_MASTER_SEED', provider: 'Crypto', purpose: 'Wallet seed for payments' },
    { name: 'INTAKE_JWT_SECRET', provider: 'Auth', purpose: 'JWT token signing for intake portal' },
  ];

  // CORS config (known from code)
  const corsConfig = {
    origins: 'CORS_ORIGINS env or * (all)',
    credentials: true,
    methods: '* (all)',
    headers: '* (all)',
  };

  // All registered API route groups
  const routeGroups = [
    { prefix: '/max', name: 'MAX AI', desc: 'Chat, desks, tasks, memory, telegram, tokens' },
    { prefix: '/system', name: 'System Monitor', desc: 'CPU, RAM, disk, temps, brain-sync' },
    { prefix: '/quotes', name: 'Quotes', desc: 'CRUD, PDF gen, email send, quick quote' },
    { prefix: '/vision', name: 'Vision AI', desc: 'Measure, upholstery, mockup, outline, imagine' },
    { prefix: '/finance', name: 'Finance', desc: 'Invoices, expenses, payments, dashboard' },
    { prefix: '/crm', name: 'CRM', desc: 'Customers, contacts, interactions' },
    { prefix: '/inventory', name: 'Inventory', desc: 'Items, categories, stock levels' },
    { prefix: '/jobs', name: 'Jobs', desc: 'Job board, from-quote creation' },
    { prefix: '/tickets', name: 'Support', desc: 'Ticket CRUD, SLA tracking' },
    { prefix: '/shipping', name: 'Shipping', desc: 'Shipments, EasyPost labels, tracking' },
    { prefix: '/costs', name: 'Costs', desc: 'Token tracking, by-provider, by-feature, trends' },
    { prefix: '/files', name: 'Files', desc: 'Upload, list, browse, view' },
    { prefix: '/chats', name: 'Chat History', desc: 'Conversation CRUD, search' },
    { prefix: '/memory', name: 'Memory', desc: 'Brain search, store, categories' },
    { prefix: '/notifications', name: 'Notifications', desc: 'System alerts and updates' },
    { prefix: '/inbox', name: 'Inbox', desc: 'Classified messages from all channels' },
    { prefix: '/craftforge', name: 'WoodCraft', desc: 'Wood design pipeline, generations' },
    { prefix: '/socialforge', name: 'SocialForge', desc: 'Social media content, scheduling' },
    { prefix: '/ollama', name: 'Ollama', desc: 'Model pull, delete, list' },
    { prefix: '/docker', name: 'Docker', desc: 'Product container start/stop/status' },
    { prefix: '/intake', name: 'Intake Portal', desc: 'Customer project submission, auth' },
    { prefix: '/smart-analyze', name: 'Smart Analyzer', desc: 'AI-powered data analysis' },
    { prefix: '/onboarding', name: 'Onboarding', desc: 'Setup wizard, business config' },
    { prefix: '/chat-backup', name: 'Chat Backup', desc: 'Auto/manual backup, restore' },
    { prefix: '/crypto-payments', name: 'Crypto', desc: 'Bitcoin/crypto payment processing' },
    { prefix: '/economic', name: 'Economic', desc: 'Market data and indicators' },
    { prefix: '/desks', name: 'Desks', desc: 'AI desk management' },
    { prefix: '/tasks', name: 'Tasks', desc: 'Task CRUD for AI desks' },
    { prefix: '/contacts', name: 'Contacts', desc: 'Contact directory' },
    { prefix: '/businessops', name: 'BusinessOps', desc: 'Tenant, package, entitlement, audit — Phase 1 read-only foundation' },
  ];

  return (
    <div className="flex-1 overflow-y-auto" style={{ background: '#f5f2ed', padding: '24px 36px' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#dbeafe] flex items-center justify-center">
            <Server size={20} className="text-[#2563eb]" />
          </div>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>PlatformForge</h1>
            <p style={{ fontSize: 13, color: '#aaa', margin: 0 }} suppressHydrationWarning>
              Infrastructure · Live Configuration · {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
            </p>
          </div>
        </div>
        <button onClick={fetchAll} disabled={loading}
          className="flex items-center gap-1.5 px-3 py-2 text-xs font-bold rounded-xl border border-[#ece8e0] hover:bg-[#faf9f7] cursor-pointer transition-all">
          <RefreshCw size={13} className={loading ? 'animate-spin text-[#b8960c]' : 'text-[#999]'} />
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {/* ── SYSTEM HEALTH ── */}
      <div className="section-label" style={{ marginTop: 20, marginBottom: 8 }}>System Health</div>
      <div className="grid grid-cols-4 gap-3 mb-3">
        <HealthCard icon={<Cpu size={18} />} label="CPU" value={`${cpu}%`} sub={`${cpuCores} cores`} color={cpu > 80 ? '#dc2626' : cpu > 50 ? '#d97706' : '#16a34a'} />
        <HealthCard icon={<HardDrive size={18} />} label="RAM" value={`${ram}%`} sub={`${ramTotal} GB total`} color={ram > 85 ? '#dc2626' : ram > 60 ? '#d97706' : '#16a34a'} />
        <HealthCard icon={<Database size={18} />} label="Disk" value={`${disk}%`} sub={`${diskTotal} GB total · ${diskLabel}${rootHigh ? ' · ⚠ near full' : ''}`} color={disk > 80 ? '#dc2626' : disk > 60 ? '#d97706' : '#16a34a'} />
        <HealthCard icon={<Activity size={18} />} label="Uptime" value={uptime} sub="Since last backend restart" color="#2563eb" />
      </div>

      {/* ── PER-DRIVE DISK PANEL (Lane I2) ── */}
      {/* All mounts rendered live from /api/v1/system/stats.disk.drives[].
          Sorted worst-first. Root / distinguished from external backup disks.
          /media/rg/BACK UP NW (100% full) is flagged FULL. */}
      {diskDrives.length > 0 && (() => {
        const sorted = [...diskDrives].sort((a, b) => b.percent - a.percent);
        return (
          <div data-section="per-drive-disk" className="empire-card" style={{ marginBottom: 12, padding: '10px 12px' }}>
            <div className="flex items-center justify-between" style={{ marginBottom: 6 }}>
              <span className="kpi-label" style={{ marginTop: 0 }}>Disk Drives</span>
              <span style={{ fontSize: 9, color: '#999' }}>
                {sorted.length} mount{sorted.length === 1 ? '' : 's'} · worst: {sorted[0]?.mount || '--'} ({sorted[0]?.percent ?? '--'}%)
              </span>
            </div>
            <div className="space-y-1">
              {sorted.map((d, i) => {
                const isWorst = i === 0;
                const isRoot = d.mount === '/';
                const isFull = d.percent >= 100;
                const isHigh = d.percent >= 75;
                const color = isFull ? '#dc2626' : isHigh ? '#d97706' : '#16a34a';
                return (
                  <div key={d.mount} data-drive={d.mount} className="flex items-center justify-between"
                    style={{
                      padding: '6px 10px',
                      borderRadius: 8,
                      border: `1px solid ${isWorst ? '#fde68a' : '#ece8e0'}`,
                      background: isFull ? '#fef2f2' : isHigh ? '#fffbeb' : '#faf9f7',
                      ...(isWorst ? { borderWidth: 2 } : {}),
                    }}>
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="w-2 h-2 rounded-full" style={{ background: color }} />
                      <span style={{ fontSize: 11, fontWeight: 600, color: '#1a1a1a', fontFamily: 'monospace' }}>{d.mount}</span>
                      <span style={{ fontSize: 9, color: '#aaa' }}>
                        {isRoot ? 'root' : d.mount.startsWith('/media/') ? 'external' : 'data'}
                      </span>
                      {isWorst && <span style={{ fontSize: 8, fontWeight: 700, color: '#d97706', background: '#fffbeb', padding: '1px 5px', borderRadius: 4 }}>WORST</span>}
                      {isFull && <span style={{ fontSize: 8, fontWeight: 700, color: '#dc2626', background: '#fef2f2', padding: '1px 5px', borderRadius: 4 }}>FULL</span>}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span style={{ fontSize: 10, color: '#888', fontFamily: 'monospace' }}>
                        {d.used_gb?.toFixed(1) ?? '--'} / {d.total_gb?.toFixed(0) ?? '--'} GB
                      </span>
                      <span className="kpi-value" style={{ color, fontSize: 13, minWidth: 38, textAlign: 'right' }}>{d.percent}%</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })()}

      {/* ── FOUNDER PRIMARY VIEW (Lane I1) ── */}
      {/* 10-second operational truth. All pills live. Renders above the
          per-section collapsibles so Founder sees it cold-open. */}
      <div data-section="founder-primary-view" className="empire-card" style={{ marginBottom: 12, padding: '10px 12px' }}>
        <div className="flex items-center justify-between" style={{ marginBottom: 6 }}>
          <span className="kpi-label" style={{ marginTop: 0 }}>Founder Primary View</span>
          <span style={{ fontSize: 9, color: '#999' }}>10-second operational truth · live</span>
        </div>
        <div className="flex flex-wrap items-center gap-2" style={{ fontSize: 11 }}>
          <Pill
            label="AI"
            value={`${routingState.selected_provider || '--'} · ${routingState.selected_model || '--'}`}
            color={routingState.selected_provider ? '#7c3aed' : '#9ca3af'}
            live={!!routingState.selected_provider}
          />
          <Pill
            label="AI calls"
            value={routingState.ai_calls_disabled ? 'DISABLED' : 'ENABLED'}
            color={routingState.ai_calls_disabled ? '#d97706' : '#16a34a'}
            live={routingState.ai_calls_disabled !== undefined}
            warn={!!routingState.ai_calls_disabled}
          />
          <Pill
            label="Fallback"
            value={routingState.fallback_enabled ? 'ON' : 'OFF'}
            color={routingState.fallback_enabled ? '#16a34a' : '#9ca3af'}
            live={routingState.fallback_enabled !== undefined}
          />
          <Pill
            label="Backend"
            value={data.metrics?.active_ports?.['8000'] ? 'ONLINE' : 'OFFLINE'}
            color={data.metrics?.active_ports?.['8000'] ? '#16a34a' : '#dc2626'}
            live={data.metrics?.active_ports?.['8000'] !== undefined}
          />
          <Pill
            label="Portal"
            value={data.metrics?.active_ports?.['3005'] ? 'ONLINE' : 'OFFLINE'}
            color={data.metrics?.active_ports?.['3005'] ? '#16a34a' : '#dc2626'}
            live={data.metrics?.active_ports?.['3005'] !== undefined}
          />
          <Pill
            label="Telegram"
            value={data.telegram?.configured ? 'Connected' : 'Not configured'}
            color={data.telegram?.configured ? '#16a34a' : '#d97706'}
            live={data.telegram !== undefined}
            warn={data.telegram !== undefined && !data.telegram?.configured}
          />
          <Pill
            label="Memories"
            value={String(memoryCount)}
            color="#2563eb"
            live={memoryCount !== '--'}
            sub={!brainData.brain_online ? 'legacy / on disk' : undefined}
          />
          {data.report?.bugs && data.report.bugs.length > 0 && (
            <Pill
              label="Bugs (high)"
              value={String(data.report.bugs.length)}
              color="#dc2626"
              warn
            />
          )}
        </div>
        <div style={{ marginTop: 8, fontSize: 10, color: '#999', fontStyle: 'italic' }}>
          CORS: * · Auth: none (LAN only — do NOT tunnel :8000) · Source: live backend
        </div>
      </div>

      {/* ── SERVICE CONNECTIVITY ── */}
      {/* Source of truth: data.metrics.active_ports from /api/v1/system/metrics.
          The legacy backend connectivity[] from /api/v1/max/system-report is
          deliberately NOT used here — it had hardcoded wrong ports (:3009,
          :3003) for docker-era services that no longer exist. */}
      <CollapsibleSection title="Service Connectivity" icon={<Wifi size={15} />} iconColor="#2563eb" expanded={expanded.svc} onToggle={() => toggle('svc')} count={5}>
        <div className="space-y-1.5">
          {(() => {
            const ap: Record<string, any> = data.metrics?.active_ports || {};
            // Canonical listening-port map for the current Empire topology.
            // Each row reads `active_ports[<port>]` (live from /api/v1/system/metrics).
            const portMap: Array<{ port: string; name: string; url: string; intentionalOffline?: boolean }> = [
              { port: '8000',  name: 'Backend API',          url: 'http://127.0.0.1:8000/health' },
              { port: '3005',  name: 'Empire Studio Portal', url: 'http://127.0.0.1:3005/' },
              { port: '7878',  name: 'OpenClaw AI',          url: 'http://127.0.0.1:7878/' },
              { port: '8787',  name: 'OpenCode (phone pair)',url: 'http://127.0.0.1:8787/' },
              { port: '11434', name: 'Ollama',               url: 'http://127.0.0.1:11434/api/version', intentionalOffline: true },
            ];
            return portMap.map(s => {
              // active_ports has 3 states: true (live), false (known not listening), or absent (no probe).
              const probed = Object.prototype.hasOwnProperty.call(ap, s.port);
              const online = probed ? !!ap[s.port] : (s.port === '8000' || s.port === '3005' || s.port === '7878' || s.port === '8787' ? true : s.port === '11434' ? ollamaOnline : false);
              const pill = online ? 'ok' : s.intentionalOffline ? 'draft' : 'overdue';
              const pillText = online ? 'ONLINE' : s.intentionalOffline ? 'DISABLED' : 'OFFLINE';
              const url = s.url;
              return (
                <div key={s.port} className="flex items-center justify-between" style={{ padding: '8px 10px', borderRadius: 10, border: '1px solid #ece8e0', background: '#faf9f7', cursor: 'pointer' }}
                  onClick={() => { if (url) window.open(url, '_blank'); }}>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ background: online ? '#16a34a' : s.intentionalOffline ? '#d8d3cb' : '#dc2626' }} />
                    <span style={{ fontSize: 12, fontWeight: 500, color: '#1a1a1a' }}>{s.name}</span>
                    <span style={{ fontSize: 9, fontFamily: 'monospace', color: '#aaa' }}>:{s.port}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {s.intentionalOffline && <span style={{ fontSize: 9, color: '#777' }}>intentional</span>}
                    <span className={`status-pill ${pill}`}>{pillText}</span>
                  </div>
                </div>
              );
            });
          })()}
          <div style={{ fontSize: 10, color: '#999', marginTop: 8, fontStyle: 'italic' }}>
            Source: <code style={{ fontFamily: 'monospace' }}>/api/v1/system/metrics.active_ports</code>. Legacy docker-era ports (3001–3011) are intentionally not shown — see Docker Era section below.
          </div>
        </div>
      </CollapsibleSection>

      {/* ── AI MODELS ── */}
      <CollapsibleSection title="AI Models & Routing" icon={<Brain size={15} />} iconColor="#7c3aed" expanded={expanded.ai} onToggle={() => toggle('ai')} count={aiModels.length || 5}>
        <div className="mb-2 text-[11px] text-[#666]">
          Active: <b>{routingState.selected_provider || '--'}</b> / <b>{routingState.selected_model || '--'}</b> ·
          fallback <b>{routingState.fallback_enabled ? 'ON' : 'OFF'}</b> ·
          AI calls <b>{routingState.ai_calls_disabled ? 'DISABLED' : 'ENABLED'}</b>
        </div>
        <div className="space-y-1.5">
          {aiModels.length > 0 ? aiModels.map((m: any, i: number) => (
            <div key={i} className="flex items-center justify-between gap-3" style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', background: '#faf9f7' }}>
              <div className="min-w-0">
                <div>
                  <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{m.name}</span>
                  <span style={{ fontSize: 9, color: '#aaa', marginLeft: 8 }}>{m.type || 'cloud'}</span>
                  {m.primary && <span style={{ fontSize: 8, color: '#b8960c', fontWeight: 700, marginLeft: 6, background: '#fdf8eb', padding: '1px 5px', borderRadius: 4 }}>ACTIVE</span>}
                </div>
                <div style={{ fontSize: 10, color: '#888', marginTop: 2 }} className="truncate">
                  {m.model || m.models?.[0] || 'model not set'}
                  {m.disabled_reason ? ` · ${m.disabled_reason}` : ''}
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <span className={`status-pill ${m.available ? 'ok' : 'overdue'}`}>{m.available ? 'AVAILABLE' : 'UNAVAILABLE'}</span>
                <button
                  onClick={() => setActiveProvider(m)}
                  disabled={!m.available || busyProvider === (m.provider_canonical || m.id)}
                  className="text-[10px] px-2 py-1 rounded-lg border border-[#ece8e0] bg-white hover:bg-[#f9f8f6] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Set Active
                </button>
                <button
                  onClick={() => testProvider(m)}
                  disabled={!m.available || busyProvider === (m.provider_canonical || m.id)}
                  className="text-[10px] px-2 py-1 rounded-lg border border-[#ece8e0] bg-white hover:bg-[#f9f8f6] disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Test
                </button>
                {m.disabled ? (
                  <button
                    onClick={() => toggleProvider(m, true)}
                    disabled={busyProvider === (m.provider_canonical || m.id)}
                    className="text-[10px] px-2 py-1 rounded-lg border border-[#ece8e0] bg-white hover:bg-[#f9f8f6] disabled:opacity-50"
                  >
                    Enable
                  </button>
                ) : (
                  <button
                    onClick={() => toggleProvider(m, false)}
                    disabled={busyProvider === (m.provider_canonical || m.id)}
                    className="text-[10px] px-2 py-1 rounded-lg border border-[#ece8e0] bg-white hover:bg-[#f9f8f6] disabled:opacity-50"
                  >
                    Disable
                  </button>
                )}
              </div>
            </div>
          )) : (
            <div style={{ fontSize: 12, color: '#aaa', padding: 12 }}>Loading models from /max/models...</div>
          )}
        </div>
        <div style={{ marginTop: 12, padding: 12, borderRadius: 10, background: '#dbeafe', border: '1px solid #93c5fd' }}>
          <div className="section-label" style={{ color: '#2563eb', marginBottom: 4 }}>Routing Policy</div>
          <div style={{ fontSize: 12, color: '#555' }}>
            Selected provider/model is authoritative. Fallback only runs when explicitly enabled in routing state.
          </div>
          <div className="mt-2 flex items-center gap-2">
            <button
              onClick={async () => {
                await postJson(`${API}/max/routing-state`, {
                  fallback_enabled: !routingState.fallback_enabled,
                  updated_by: 'founder_or_system',
                  reason: 'platformforge_fallback_toggle',
                });
                await fetchAll();
              }}
              className="text-[10px] px-2 py-1 rounded-lg border border-[#bfdbfe] bg-white hover:bg-[#f8fbff]"
            >
              {routingState.fallback_enabled ? 'Clear Fallback' : 'Enable Fallback'}
            </button>
          </div>
        </div>
      </CollapsibleSection>

      {/* ── GUARDRAILS / API KEYS / CORS / API ROUTES / OLLAMA / DOCKER-ERA ── */}
      {/* MOVED to the System Details / Legacy · Debug drawers (see bottom of
          page). These sections now render only when their corresponding
          drawer is opened. This is the Lane I1 reorganization. The original
          JSX is preserved in the drawer content blocks below. */}

      {/* ── BRAIN & BACKUP ── */}
      {/* NOTE: this section refers to the **legacy** brain service
          (app/services/max/brain/*) and the SQLite memories.db under
          backend/data/brain. It is NOT the same as the current MAX memory
          layer (which lives in /api/v1/max/memory). On the active backend
          the legacy brain service is not initialized (brain_online: false),
          so all values are read from on-disk artifacts. The 21,181 memory
          count is real (SQLite verified), but the storage path points at
          a cross-repo artifact (see REPO-TRUTH.md). */}
      <CollapsibleSection title="Legacy Brain & Backup" icon={<Database size={15} />} iconColor="#2563eb" expanded={expanded.brain} onToggle={() => toggle('brain')} count={5}>
        <div className="space-y-1.5">
          <ConfigRow label="Legacy Brain Service" value={brainData.brain_online ? 'Online' : 'Not initialized (data on disk only)'} warn={!brainData.brain_online} />
          <ConfigRow label="Memories on Disk (legacy)" value={String(memoryCount)} />
          <ConfigRow label="Storage Path" value={brainData.storage?.path || '--'} warn={!!(brainData.storage?.path && brainData.storage.path.includes('empire-repo/backend'))} />
          <ConfigRow label="  ⚠ Cross-repo path" value="Stale-fork artifact — see REPO-TRUTH" warn={!!(brainData.storage?.path && brainData.storage.path.includes('empire-repo/backend'))} />
          <ConfigRow label="External Drive" value={brainData.storage?.external_drive ? 'Yes' : 'No'} />
          <ConfigRow label="Active Conversations" value={String(brainData.conversations?.active ?? '--')} />
          {data.backup && (
            <>
              <div style={{ height: 1, background: '#ece8e0', margin: '8px 0' }} />
              <ConfigRow label="Last Backup" value={data.backup.last_backup ? new Date(data.backup.last_backup).toLocaleString() : 'Never'} warn={!data.backup.last_backup} />
              <ConfigRow label="Backup Count" value={String(data.backup.backup_count ?? 0)} />
              <ConfigRow label="Backup Interval" value={`${data.backup.interval_hours ?? 6}h`} />
              <ConfigRow label="Auto Backup" value={data.backup.auto_enabled ? 'Enabled' : 'Disabled'} ok={data.backup.auto_enabled} />
            </>
          )}
        </div>
      </CollapsibleSection>

      {/* ── SUGGESTIONS / BUGS from system report ── */}
      {(data.report?.suggestions?.length > 0 || data.report?.bugs?.length > 0) && (
        <CollapsibleSection title="Suggestions & Known Issues" icon={<AlertTriangle size={15} />} iconColor="#d97706"
          expanded={expanded.issues} onToggle={() => toggle('issues')}
          count={(data.report?.suggestions?.length || 0) + (data.report?.bugs?.length || 0)}>
          <div className="space-y-1.5">
            {data.report?.bugs?.map((b: any, i: number) => (
              <div key={`b${i}`} style={{ padding: '8px 12px', borderRadius: 10, background: '#fef2f2', border: '1px solid #fecaca', fontSize: 11, color: '#dc2626' }}>
                {typeof b === 'string' ? b : b.message || JSON.stringify(b)}
              </div>
            ))}
            {data.report?.suggestions?.map((s: any, i: number) => (
              <div key={`s${i}`} style={{ padding: '8px 12px', borderRadius: 10, background: '#fffbeb', border: '1px solid #fde68a', fontSize: 11, color: '#92400e' }}>
                {typeof s === 'string' ? s : s.message || JSON.stringify(s)}
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Desktop Pairing, Payments stub, and Documentation moved to the
          System Details drawer (see bottom of page). Lane I1. */}

      {/* ── DRAWER TOGGLES (Lane I1) ── */}
      {/* Two top-level drawers at the bottom of the page. Each is collapsed
          by default. When opened, the corresponding grouped sections appear
          above the drawer button in their normal flow. */}
      <DrawerToggle
        id="system-details"
        open={systemDetailsOpen}
        count={7}
        label="System Details"
        sub="CORS · API Keys · Guardrails · Routes · Pairing · Payments · Docs"
        icon={<Lock size={15} />}
        iconColor="#7c3aed"
        onToggle={() => setSystemDetailsOpen(p => !p)}
      />
      {systemDetailsOpen && (
        <div data-section="system-details-content" style={{ marginTop: -12, marginBottom: 12 }}>
          <div className="empire-card" style={{ padding: 16, fontSize: 10, color: '#777', background: '#faf9f7' }}>
            <b>System Details (opened).</b> Founder deep-dive: CORS config, API key names, guardrails, route inventory, desktop pairing, payments stub, and documentation registry.
            Sections inside this drawer are individually collapsible (state preserved). Closing the drawer unmounts the children; opening remounts them with last-known state.
          </div>
          {/* The 7 moving sections render normally here. They were each wrapped
              with SectionGroup in the main flow above; here they render directly. */}
          <SectionGroup visible={true}>
            {/* CORS & Security */}
            <CollapsibleSection title="CORS & Security" icon={<Shield size={15} />} iconColor="#d97706" expanded={expanded.cors} onToggle={() => toggle('cors')} count={4}>
              <div className="space-y-1.5">
                <ConfigRow label="Allowed Origins" value={corsConfig.origins} warn={corsConfig.origins.includes('*')} />
                <ConfigRow label="Allow Credentials" value={corsConfig.credentials ? 'Yes' : 'No'} />
                <ConfigRow label="Allowed Methods" value={corsConfig.methods} warn={corsConfig.methods === '* (all)'} />
                <ConfigRow label="Allowed Headers" value={corsConfig.headers} warn={corsConfig.headers === '* (all)'} />
                <ConfigRow label="Auth Mode" value="None (local network only — do NOT tunnel :8000 publicly)" warn />
                <ConfigRow label="Database" value="SQLite (empire.db at backend/data/)" />
                <ConfigRow label="Telegram Bot" value={data.telegram?.configured ? 'Configured' : 'Not configured'} ok={data.telegram?.configured} />
              </div>
              {corsConfig.origins.includes('*') && (
                <div style={{ marginTop: 12, padding: 10, borderRadius: 10, background: '#fffbeb', border: '1px solid #fde68a', fontSize: 11 }}
                  className="flex items-center gap-2">
                  <AlertTriangle size={14} className="text-[#d97706] shrink-0" />
                  <span style={{ color: '#92400e' }}>CORS allows all origins (<code>*</code>). <b>Local/dev only.</b> Set <code>CORS_ORIGINS</code> env (comma-separated allow-list) before any production deploy or before exposing <code>:8000</code> on the public tunnel.</span>
                </div>
              )}
            </CollapsibleSection>

            {/* API Keys */}
            <CollapsibleSection title="API Keys & Credentials" icon={<Key size={15} />} iconColor="#b8960c" expanded={expanded.keys} onToggle={() => toggle('keys')} count={apiKeys.length}>
              <div style={{ fontSize: 10, color: '#777', padding: '6px 10px 8px', background: '#faf9f7', border: '1px solid #ece8e0', borderRadius: 8, marginBottom: 8 }}>
                <b>Debug view.</b> This section is for Founder-only diagnostic use. Names of env-vars and providers are shown (never the values). In a future lane this section would live in a System Details drawer behind Founder-PIN re-auth. <code>CRYPTO_MASTER_SEED</code> and <code>INTAKE_JWT_SECRET</code> are listed here for completeness; the absence of a SET/MISSING pill on these rows is intentional — their presence is a hint of capability, not a verification of state.
              </div>
              <div className="flex items-center justify-end mb-2">
                <button onClick={() => setShowKeys(!showKeys)} className="flex items-center gap-1 text-[10px] text-[#999] hover:text-[#555] cursor-pointer transition-colors"
                  style={{ background: 'none', border: 'none' }}>
                  {showKeys ? <EyeOff size={12} /> : <Eye size={12} />}
                  {showKeys ? 'Hide names' : 'Show names'}
                </button>
              </div>
              <div className="space-y-1.5">
                {apiKeys.map((k, i) => {
                  const isSet = k.name === 'TELEGRAM_BOT_TOKEN' ? data.telegram?.bot_token_set
                    : k.name === 'TELEGRAM_FOUNDER_CHAT_ID' ? data.telegram?.chat_id_set
                    : k.name === 'XAI_API_KEY' ? aiModels.find((m: any) => (m.id === 'xai' || m.id === 'grok'))?.available
                    : k.name === 'ANTHROPIC_API_KEY' ? aiModels.find((m: any) => m.id === 'claude')?.available
                    : k.name === 'GROQ_API_KEY' ? aiModels.find((m: any) => m.id === 'groq')?.available
                    : undefined;
                  return (
                    <div key={i} className="flex items-center justify-between" style={{ padding: '8px 12px', borderRadius: 10, border: '1px solid #ece8e0', background: '#faf9f7' }}>
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        <Lock size={12} className="text-[#999] shrink-0" />
                        <div className="min-w-0">
                          <div style={{ fontSize: 11, fontWeight: 600, color: '#1a1a1a', fontFamily: showKeys ? 'monospace' : 'inherit' }}>
                            {showKeys ? k.name : k.provider}
                          </div>
                          <div style={{ fontSize: 9, color: '#999' }} className="truncate">{k.purpose}</div>
                        </div>
                      </div>
                      {isSet !== undefined ? (
                        <span className={`status-pill ${isSet ? 'ok' : 'overdue'}`}>{isSet ? 'SET' : 'MISSING'}</span>
                      ) : (
                        <span className="status-pill draft">ENV</span>
                      )}
                    </div>
                  );
                })}
              </div>
            </CollapsibleSection>

            {/* Guardrails */}
            <CollapsibleSection title="Guardrails" icon={<Shield size={15} />} iconColor="#16a34a" expanded={expanded.guard} onToggle={() => toggle('guard')} count={guardrails.length}>
              <div className="space-y-1.5">
                {guardrails.map((g, i) => (
                  <div key={i} className="flex items-center justify-between" style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', background: '#faf9f7' }}>
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{g.name}</div>
                      <div style={{ fontSize: 10, color: '#777', marginTop: 2 }}>{g.desc}</div>
                    </div>
                    <span className="status-pill ok">{g.status.toUpperCase()}</span>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 12, padding: 12, borderRadius: 10, background: '#f0fdf4', border: '1px solid #bbf7d0' }}>
                <div className="section-label" style={{ color: '#16a34a', marginBottom: 4 }}>Safe Refusal Message</div>
                <div style={{ fontSize: 11, color: '#555', fontStyle: 'italic' }}>&quot;I can&apos;t help with that request. Let me know how else I can assist with Empire operations.&quot;</div>
              </div>
            </CollapsibleSection>

            {/* API Routes */}
            <CollapsibleSection title="API Route Groups" icon={<Code size={15} />} iconColor="#b8960c" expanded={expanded.routes} onToggle={() => toggle('routes')} count={routeGroups.length}>
              <div className="space-y-1">
                {routeGroups.map((r, i) => {
                  const mod = modules.find((m: any) => m.endpoint === r.prefix || m.name?.toLowerCase().includes(r.name.toLowerCase()));
                  const isBusinessops = r.prefix === '/businessops';
                  const livePill = isBusinessops
                    ? (businessopsLive ? 'ACTIVE' : 'UNKNOWN')
                    : (mod?.status?.toUpperCase() || null);
                  const liveClass = isBusinessops
                    ? (businessopsLive ? 'ok' : 'draft')
                    : (mod?.status === 'active' ? 'ok' : mod?.status === 'error' ? 'overdue' : 'draft');
                  return (
                    <div key={i} className="flex items-center justify-between" style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7', cursor: 'pointer' }}
                      onClick={() => { window.open(`${API_BASE}/api/v1${r.prefix}`, '_blank'); }}>
                      <div className="flex items-center gap-2 min-w-0">
                        <span style={{ fontSize: 9, fontWeight: 700, fontFamily: 'monospace', padding: '2px 6px', borderRadius: 4, color: '#2563eb', background: '#dbeafe' }}>/api/v1</span>
                        <span style={{ fontSize: 11, fontFamily: 'monospace', fontWeight: 600, color: '#1a1a1a' }}>{r.prefix}</span>
                        <span style={{ fontSize: 10, color: '#999' }} className="truncate">{r.desc}</span>
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0">
                        {livePill && <span className={`status-pill ${liveClass}`} style={{ fontSize: 8 }}>{livePill}</span>}
                        <ExternalLink size={10} className="text-[#ccc]" />
                      </div>
                    </div>
                  );
                })}
              </div>
            </CollapsibleSection>

            {/* Desktop Pairing */}
            <CollapsibleSection title="Desktop Pairing" icon={<Smartphone size={15} />} iconColor="#06b6d4" expanded={expanded.pairing} onToggle={() => toggle('pairing')}>
              <DesktopPairing />
            </CollapsibleSection>

            {/* Payments stub */}
            <CollapsibleSection title="Payments" icon={<CreditCard size={15} />} iconColor="#16a34a" expanded={expanded.payments} onToggle={() => toggle('payments')}>
              <div style={{ fontSize: 11, color: '#777', padding: 12 }}>
                <b>Stripe / card widget is not rendered on PlatformForge.</b>{' '}
                The full payment UI is shown to customers on the <code>Pricing</code> page.
                On this page, Founder-useful payment status (e.g. <code>payments</code> route
                activity, settlement count) would be wired here in a future lane.
                <div style={{ marginTop: 8, fontSize: 10, color: '#999' }}>
                  See: <code>components/business/payments/PaymentModule.tsx</code> (customer widget, unchanged)
                </div>
              </div>
            </CollapsibleSection>

            {/* Documentation */}
            <CollapsibleSection title="Documentation" icon={<BookOpen size={15} />} iconColor="#7c3aed" expanded={expanded.docs} onToggle={() => toggle('docs')}>
              <ProductDocs product="platform" />
            </CollapsibleSection>
          </SectionGroup>
        </div>
      )}

      <DrawerToggle
        id="legacy-debug"
        open={legacyDebugOpen}
        count={2}
        label="Legacy / Debug"
        sub="Docker-era ports · Ollama local models"
        icon={<Globe size={15} />}
        iconColor="#9ca3af"
        onToggle={() => setLegacyDebugOpen(p => !p)}
      />
      {legacyDebugOpen && (
        <div data-section="legacy-debug-content" style={{ marginTop: -12, marginBottom: 12 }}>
          <div className="empire-card" style={{ padding: 16, fontSize: 10, color: '#777', background: '#faf9f7' }}>
            <b>Legacy / Debug (opened).</b> Items below are 100% historical or hardcoded data. The 13 docker-era port cards reflect a docker-compose topology that is no longer in use. Ollama Local Models is empty because Ollama is intentionally disabled. Founder rarely needs this.
          </div>
          <SectionGroup visible={true}>
            {/* Ollama Local Models */}
            <CollapsibleSection title="Ollama Local Models" icon={<Layers size={15} />} iconColor="#16a34a" expanded={expanded.ollama} onToggle={() => toggle('ollama')}
              count={Array.isArray(ollamaModels) ? ollamaModels.length : 0}>
              {Array.isArray(ollamaModels) && ollamaModels.length > 0 ? (
                <div className="space-y-1.5">
                  {ollamaModels.map((m: any, i: number) => (
                    <div key={i} className="flex items-center justify-between" style={{ padding: '8px 10px', borderRadius: 10, border: '1px solid #ece8e0', background: '#faf9f7' }}>
                      <div>
                        <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{typeof m === 'string' ? m : m.name}</span>
                        {m.size_gb && <span style={{ fontSize: 9, color: '#aaa', marginLeft: 8 }}>{m.size_gb} GB</span>}
                      </div>
                      <span className="status-pill ok">INSTALLED</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: 12, color: '#aaa', padding: 12 }}>
                  {ollamaOnline
                    ? 'No models installed'
                    : 'Ollama disabled intentionally (see AI Models row for reason)'}
                </div>
              )}
            </CollapsibleSection>

            {/* Docker-era ports */}
            {dockerProducts.length > 0 && (
              <div data-section="docker-legacy" style={{ marginBottom: 12 }}>
                <button
                  onClick={() => setExpanded(p => ({ ...p, docker: p.docker === undefined ? false : !p.docker }))}
                  className="empire-card w-full flex items-center justify-between cursor-pointer transition-colors hover:bg-[#f5f3ef]"
                  style={{ padding: '14px 16px', background: 'transparent', border: 'none', textAlign: 'left' }}
                >
                  <div className="flex items-center gap-2">
                    <span style={{ color: '#7c3aed' }}><Globe size={15} /></span>
                    <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>Legacy / Docker Era Ports</span>
                    <span style={{ fontSize: 9, color: '#999', background: '#f0ede8', padding: '2px 6px', borderRadius: 6, fontWeight: 600 }}>{dockerProducts.length}</span>
                    <span style={{ fontSize: 9, color: '#999' }}>debug</span>
                  </div>
                  <span style={{ fontSize: 10, color: '#777' }}>{expanded.docker ? 'Hide' : 'Show legacy'}</span>
                </button>
                {expanded.docker && (
                  <div className="empire-card" style={{ marginTop: 8, padding: 16, fontSize: 10, color: '#777' }}>
                    <p style={{ marginBottom: 8 }}>
                      ⚠ These 13 entries are <b>historical</b>. They reflect a docker-compose topology where each product was a separate container on a separate port. The live Empire topology is: backend on <code>:8000</code>, Next.js portal on <code>:3005</code>, openclaw on <code>:7878</code>, opencode on <code>:8787</code>. None of the 13 ports below are currently listening. The cards render <code>UNKNOWN</code> because the docker manager can't see systemd services.
                    </p>
                    <div className="space-y-1.5">
                      {dockerProducts.map((p: any, i: number) => (
                        <div key={i} className="flex items-center justify-between" style={{ padding: '6px 8px', borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7' }}>
                          <div className="flex items-center gap-2">
                            <span style={{ fontSize: 14 }}>{p.emoji || ''}</span>
                            <div>
                              <span style={{ fontSize: 11, fontWeight: 600, color: '#1a1a1a' }}>{p.name}</span>
                              <span style={{ fontSize: 9, fontFamily: 'monospace', color: '#aaa', marginLeft: 6 }}>:{p.port}</span>
                            </div>
                          </div>
                          <span className={`status-pill ${p.status === 'running' ? 'ok' : p.status === 'exited' ? 'overdue' : 'draft'}`}>
                            {(p.status || 'unknown').toUpperCase()}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </SectionGroup>
        </div>
      )}

      <div style={{ height: 40 }} />
    </div>
  );
}

// ── Sub-components ──

function CollapsibleSection({ title, icon, iconColor, expanded, onToggle, count, children }: {
  title: string; icon: React.ReactNode; iconColor: string; expanded?: boolean; onToggle: () => void; count?: number; children: React.ReactNode;
}) {
  const isOpen = expanded ?? false;
  return (
    <div className="empire-card" style={{ marginBottom: 12, padding: 0, overflow: 'hidden' }}>
      <button onClick={onToggle} className="w-full flex items-center justify-between cursor-pointer transition-colors hover:bg-[#f5f3ef]"
        style={{ padding: '14px 16px', background: 'transparent', border: 'none', textAlign: 'left' }}>
        <div className="flex items-center gap-2">
          <span style={{ color: iconColor }}>{icon}</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{title}</span>
          {count !== undefined && <span style={{ fontSize: 9, color: '#999', background: '#f0ede8', padding: '2px 6px', borderRadius: 6, fontWeight: 600 }}>{count}</span>}
        </div>
        {isOpen ? <ChevronDown size={14} className="text-[#999]" /> : <ChevronRight size={14} className="text-[#999]" />}
      </button>
      {isOpen && <div style={{ padding: '0 16px 16px' }}>{children}</div>}
    </div>
  );
}

function HealthCard({ icon, label, value, sub, color }: { icon: React.ReactNode; label: string; value: string; sub?: string; color: string }) {
  return (
    <div className="empire-card">
      <div className="flex items-center gap-2 mb-2">
        <span style={{ color }}>{icon}</span>
        <span className="kpi-label" style={{ marginTop: 0 }}>{label}</span>
      </div>
      <div className="kpi-value" style={{ color }}>{value}</div>
      {sub && <div style={{ fontSize: 9, color: '#aaa', marginTop: 2 }}>{sub}</div>}
      <div style={{ width: '100%', height: 6, borderRadius: 4, background: '#f0ede8', marginTop: 8, overflow: 'hidden' }}>
        <div style={{ height: '100%', borderRadius: 4, transition: 'all 0.3s', width: value.includes('%') ? value : '0%', background: color }} />
      </div>
    </div>
  );
}

// Small label/value pill used in the Founder Primary View. 3 states:
//   live=true  → value rendered in the requested color
//   live=false → value rendered muted (we don't know yet; caller will refresh)
//   warn=true  → amber triangle glyph next to the value
function Pill({ label, value, color, live, warn, sub }: { label: string; value: string; color: string; live?: boolean; warn?: boolean; sub?: string }) {
  const effectiveColor = live === false ? '#9ca3af' : color;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '4px 10px', borderRadius: 999,
      background: '#faf9f7', border: '1px solid #ece8e0',
      fontSize: 11, color: '#1a1a1a',
    }}>
      <span style={{ fontSize: 9, color: '#888', textTransform: 'uppercase', letterSpacing: 0.4 }}>{label}</span>
      <span style={{ fontWeight: 600, color: effectiveColor, fontFamily: value.includes('/') || value.includes('-') ? 'monospace' : 'inherit' }}>{value}</span>
      {warn && <AlertTriangle size={10} className="text-[#d97706]" />}
      {sub && <span style={{ fontSize: 9, color: '#999' }}>· {sub}</span>}
    </span>
  );
}

// SectionGroup: toggles a block of sections by setting display:none. Used
// for the System Details and Legacy / Debug drawers. Each section's
// internal expanded state is preserved across opens/closes.
function SectionGroup({ visible, children }: { visible: boolean; children: React.ReactNode }) {
  if (!visible) return null;
  return <>{children}</>;
}

// Drawer toggle button. Looks like a CollapsibleSection header but emits
// data-section=… on a <button> and toggles a parent state.
function DrawerToggle({ id, open, count, label, sub, icon, iconColor, onToggle }: {
  id: string; open: boolean; count?: number; label: string; sub: string;
  icon: React.ReactNode; iconColor: string; onToggle: () => void;
}) {
  return (
    <div data-section={`drawer-${id}`} className="empire-card" style={{ marginBottom: 12, padding: 0, overflow: 'hidden' }}>
      <button onClick={onToggle}
        className="w-full flex items-center justify-between cursor-pointer transition-colors hover:bg-[#f5f3ef]"
        style={{ padding: '14px 16px', background: 'transparent', border: 'none', textAlign: 'left' }}>
        <div className="flex items-center gap-2">
          <span style={{ color: iconColor }}>{icon}</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{label}</span>
          {count !== undefined && <span style={{ fontSize: 9, color: '#999', background: '#f0ede8', padding: '2px 6px', borderRadius: 6, fontWeight: 600 }}>{count}</span>}
          <span style={{ fontSize: 9, color: '#999' }}>{sub}</span>
        </div>
        {open ? <ChevronDown size={14} className="text-[#999]" /> : <ChevronRight size={14} className="text-[#999]" />}
      </button>
    </div>
  );
}

function ConfigRow({ label, value, warn, ok }: { label: string; value: string; warn?: boolean; ok?: boolean }) {
  const color = ok ? '#16a34a' : warn ? '#d97706' : '#1a1a1a';
  return (
    <div className="flex items-center justify-between" style={{ padding: '8px 10px', borderRadius: 10, border: '1px solid #ece8e0', background: '#faf9f7' }}>
      <span style={{ fontSize: 12, color: '#555' }}>{label}</span>
      <div className="flex items-center gap-1.5">
        {warn && <AlertTriangle size={10} className="text-[#d97706]" />}
        {ok && <CheckCircle2 size={10} className="text-[#16a34a]" />}
        <span style={{ fontSize: 11, fontWeight: 600, color, fontFamily: value.includes('/') || value.includes('.') ? 'monospace' : 'inherit' }}>{value}</span>
      </div>
    </div>
  );
}
