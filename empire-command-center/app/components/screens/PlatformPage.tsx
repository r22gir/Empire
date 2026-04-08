'use client';
import { useState, useEffect, useCallback } from 'react';
import { API, API_BASE } from '../../lib/api';
import {
  Server, Activity, Brain, Code, Shield, Cpu, HardDrive, Wifi, Database,
  Globe, ChevronDown, ChevronRight, Key, Lock, AlertTriangle, CheckCircle2,
  RefreshCw, Eye, EyeOff, Loader2, ExternalLink, Layers, Zap, BookOpen, CreditCard,
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';

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
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [showKeys, setShowKeys] = useState(false);

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

  const toggle = (key: string) => setExpanded(p => ({ ...p, [key]: !p[key] }));

  const cpu = data.system?.cpu?.percent ?? data.system?.cpu_percent ?? 0;
  const ram = data.system?.memory?.percent ?? 0;
  const disk = data.system?.disk?.percent ?? 0;
  const uptime = data.system?.uptime || data.report?.system?.uptime || (data.metrics?.uptime_seconds ? `${Math.floor(data.metrics.uptime_seconds / 3600)}h ${Math.floor((data.metrics.uptime_seconds % 3600) / 60)}m` : '--');
  const cpuCores = data.system?.cpu?.cores || '--';
  const ramTotal = data.system?.memory?.total_gb?.toFixed(1) || '--';
  const diskTotal = data.system?.disk?.total_gb?.toFixed(0) || '--';

  // AI models from live data
  const aiModels = data.models?.models || [];

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
      <div className="grid grid-cols-4 gap-3 mb-6">
        <HealthCard icon={<Cpu size={18} />} label="CPU" value={`${cpu}%`} sub={`${cpuCores} cores`} color={cpu > 80 ? '#dc2626' : cpu > 50 ? '#d97706' : '#16a34a'} />
        <HealthCard icon={<HardDrive size={18} />} label="RAM" value={`${ram}%`} sub={`${ramTotal} GB total`} color={ram > 85 ? '#dc2626' : ram > 60 ? '#d97706' : '#16a34a'} />
        <HealthCard icon={<Database size={18} />} label="Disk" value={`${disk}%`} sub={`${diskTotal} GB total`} color={disk > 90 ? '#dc2626' : disk > 70 ? '#d97706' : '#16a34a'} />
        <HealthCard icon={<Activity size={18} />} label="Uptime" value={uptime} sub="Since last boot" color="#2563eb" />
      </div>

      {/* ── SERVICE CONNECTIVITY ── */}
      <CollapsibleSection title="Service Connectivity" icon={<Wifi size={15} />} iconColor="#2563eb" expanded={expanded.svc} onToggle={() => toggle('svc')} count={connectivity.length || 7}>
        <div className="space-y-1.5">
          {connectivity.length > 0 ? connectivity.map((s: any, i: number) => (
            <div key={i} className="flex items-center justify-between" style={{ padding: '8px 10px', borderRadius: 10, border: '1px solid #ece8e0', background: '#faf9f7', cursor: 'pointer' }}
              onClick={() => { if (s.url) window.open(s.url, '_blank'); }}>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full" style={{ background: s.status === 'online' ? '#16a34a' : s.status === 'error' ? '#dc2626' : '#d8d3cb' }} />
                <span style={{ fontSize: 12, fontWeight: 500, color: '#1a1a1a' }}>{s.service}</span>
                <span style={{ fontSize: 9, fontFamily: 'monospace', color: '#aaa' }}>{s.url}</span>
              </div>
              <div className="flex items-center gap-2">
                {s.code && <span style={{ fontSize: 9, fontFamily: 'monospace', color: '#aaa' }}>{s.code}</span>}
                <span className={`status-pill ${s.status === 'online' ? 'ok' : s.status === 'error' ? 'overdue' : 'draft'}`}>{(s.status || '--').toUpperCase()}</span>
              </div>
            </div>
          )) : (
            <>
              {(() => {
                const ap = data.metrics?.active_ports || {};
                const portMap: Record<string, string> = { '8000': 'Backend API', '3005': 'Command Center', '11434': 'Ollama', '7878': 'OpenClaw', '3077': 'RecoveryForge' };
                const services = Object.keys(portMap).map(port => ({
                  name: ap[port] && typeof ap[port] === 'string' ? ap[port] : portMap[port],
                  port,
                  online: ap[port] !== undefined ? !!ap[port] : (port === '8000' || port === '3005' ? true : port === '11434' ? ollamaOnline : false),
                }));
                return services;
              })().map((s, i) => (
                <div key={i} className="flex items-center justify-between" style={{ padding: '8px 10px', borderRadius: 10, border: '1px solid #ece8e0', background: '#faf9f7' }}>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ background: s.online ? '#16a34a' : '#d8d3cb' }} />
                    <span style={{ fontSize: 12, fontWeight: 500, color: '#1a1a1a' }}>{s.name}</span>
                    <span style={{ fontSize: 9, fontFamily: 'monospace', color: '#aaa' }}>:{s.port}</span>
                  </div>
                  <span className={`status-pill ${s.online ? 'ok' : 'draft'}`}>{s.online ? 'ONLINE' : '--'}</span>
                </div>
              ))}
            </>
          )}
        </div>
      </CollapsibleSection>

      {/* ── AI MODELS ── */}
      <CollapsibleSection title="AI Models & Routing" icon={<Brain size={15} />} iconColor="#7c3aed" expanded={expanded.ai} onToggle={() => toggle('ai')} count={aiModels.length || 5}>
        <div className="space-y-1.5">
          {aiModels.length > 0 ? aiModels.map((m: any, i: number) => (
            <div key={i} className="flex items-center justify-between" style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', background: '#faf9f7' }}>
              <div>
                <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{m.name}</span>
                <span style={{ fontSize: 9, color: '#aaa', marginLeft: 8 }}>{m.type || 'cloud'}</span>
                {m.primary && <span style={{ fontSize: 8, color: '#b8960c', fontWeight: 700, marginLeft: 6, background: '#fdf8eb', padding: '1px 5px', borderRadius: 4 }}>PRIMARY</span>}
              </div>
              <span className={`status-pill ${m.available ? 'ok' : 'overdue'}`}>{m.available ? 'AVAILABLE' : 'UNAVAILABLE'}</span>
            </div>
          )) : (
            <div style={{ fontSize: 12, color: '#aaa', padding: 12 }}>Loading models from /max/models...</div>
          )}
        </div>
        <div style={{ marginTop: 12, padding: 12, borderRadius: 10, background: '#dbeafe', border: '1px solid #93c5fd' }}>
          <div className="section-label" style={{ color: '#2563eb', marginBottom: 4 }}>Routing Priority</div>
          <div style={{ fontSize: 12, color: '#555' }}>xAI Grok → Claude → Groq → OpenClaw → Ollama</div>
        </div>
      </CollapsibleSection>

      {/* ── GUARDRAILS ── */}
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

      {/* ── API KEYS ── */}
      <CollapsibleSection title="API Keys & Credentials" icon={<Key size={15} />} iconColor="#b8960c" expanded={expanded.keys} onToggle={() => toggle('keys')} count={apiKeys.length}>
        <div className="flex items-center justify-end mb-2">
          <button onClick={() => setShowKeys(!showKeys)} className="flex items-center gap-1 text-[10px] text-[#999] hover:text-[#555] cursor-pointer transition-colors"
            style={{ background: 'none', border: 'none' }}>
            {showKeys ? <EyeOff size={12} /> : <Eye size={12} />}
            {showKeys ? 'Hide names' : 'Show names'}
          </button>
        </div>
        <div className="space-y-1.5">
          {apiKeys.map((k, i) => {
            // Determine if likely configured based on live data
            const isSet = k.name === 'TELEGRAM_BOT_TOKEN' ? data.telegram?.bot_token_set
              : k.name === 'TELEGRAM_FOUNDER_CHAT_ID' ? data.telegram?.chat_id_set
              : k.name === 'XAI_API_KEY' ? aiModels.find((m: any) => m.id === 'grok')?.available
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

      {/* ── CORS & SECURITY ── */}
      <CollapsibleSection title="CORS & Security" icon={<Shield size={15} />} iconColor="#d97706" expanded={expanded.cors} onToggle={() => toggle('cors')} count={4}>
        <div className="space-y-1.5">
          <ConfigRow label="Allowed Origins" value={corsConfig.origins} warn={corsConfig.origins.includes('*')} />
          <ConfigRow label="Allow Credentials" value={corsConfig.credentials ? 'Yes' : 'No'} />
          <ConfigRow label="Allowed Methods" value={corsConfig.methods} warn={corsConfig.methods === '* (all)'} />
          <ConfigRow label="Allowed Headers" value={corsConfig.headers} warn={corsConfig.headers === '* (all)'} />
          <ConfigRow label="Auth Mode" value="None (local network only)" warn />
          <ConfigRow label="Database" value="SQLite (empirebox.db)" />
          <ConfigRow label="Telegram Bot" value={data.telegram?.configured ? 'Configured' : 'Not configured'} ok={data.telegram?.configured} />
        </div>
        {corsConfig.origins.includes('*') && (
          <div style={{ marginTop: 12, padding: 10, borderRadius: 10, background: '#fffbeb', border: '1px solid #fde68a', fontSize: 11 }}
            className="flex items-center gap-2">
            <AlertTriangle size={14} className="text-[#d97706] shrink-0" />
            <span style={{ color: '#92400e' }}>CORS is set to allow all origins (*). Configure CORS_ORIGINS env var for production.</span>
          </div>
        )}
      </CollapsibleSection>

      {/* ── API ROUTES ── */}
      <CollapsibleSection title="API Route Groups" icon={<Code size={15} />} iconColor="#b8960c" expanded={expanded.routes} onToggle={() => toggle('routes')} count={routeGroups.length}>
        <div className="space-y-1">
          {routeGroups.map((r, i) => {
            const mod = modules.find((m: any) => m.endpoint === r.prefix || m.name?.toLowerCase().includes(r.name.toLowerCase()));
            return (
              <div key={i} className="flex items-center justify-between" style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7', cursor: 'pointer' }}
                onClick={() => {
                window.open(`${API_BASE}/api/v1${r.prefix}`, '_blank');
              }}>
                <div className="flex items-center gap-2 min-w-0">
                  <span style={{ fontSize: 9, fontWeight: 700, fontFamily: 'monospace', padding: '2px 6px', borderRadius: 4, color: '#2563eb', background: '#dbeafe' }}>/api/v1</span>
                  <span style={{ fontSize: 11, fontFamily: 'monospace', fontWeight: 600, color: '#1a1a1a' }}>{r.prefix}</span>
                  <span style={{ fontSize: 10, color: '#999' }} className="truncate">{r.desc}</span>
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  {mod && <span className={`status-pill ${mod.status === 'active' ? 'ok' : mod.status === 'error' ? 'overdue' : 'draft'}`} style={{ fontSize: 8 }}>{mod.status?.toUpperCase() || 'OK'}</span>}
                  <ExternalLink size={10} className="text-[#ccc]" />
                </div>
              </div>
            );
          })}
        </div>
      </CollapsibleSection>

      {/* ── OLLAMA MODELS ── */}
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
            {ollamaOnline ? 'No models installed' : 'Ollama not reachable'}
          </div>
        )}
      </CollapsibleSection>

      {/* ── DOCKER PRODUCTS ── */}
      {dockerProducts.length > 0 && (
        <CollapsibleSection title="Docker Products" icon={<Globe size={15} />} iconColor="#7c3aed" expanded={expanded.docker} onToggle={() => toggle('docker')} count={dockerProducts.length}>
          <div className="space-y-1.5">
            {dockerProducts.map((p: any, i: number) => (
              <div key={i} className="flex items-center justify-between" style={{ padding: '8px 10px', borderRadius: 10, border: '1px solid #ece8e0', background: '#faf9f7' }}>
                <div className="flex items-center gap-2">
                  <span style={{ fontSize: 16 }}>{p.emoji || ''}</span>
                  <div>
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{p.name}</span>
                    <span style={{ fontSize: 9, fontFamily: 'monospace', color: '#aaa', marginLeft: 6 }}>:{p.port}</span>
                  </div>
                </div>
                <span className={`status-pill ${p.status === 'running' ? 'ok' : p.status === 'exited' ? 'overdue' : 'draft'}`}>
                  {(p.status || 'unknown').toUpperCase()}
                </span>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* ── BACKUP & BRAIN ── */}
      <CollapsibleSection title="Brain & Backup" icon={<Database size={15} />} iconColor="#2563eb" expanded={expanded.brain} onToggle={() => toggle('brain')} count={5}>
        <div className="space-y-1.5">
          <ConfigRow label="Brain Status" value={brainData.brain_online ? 'Online' : 'Offline'} ok={brainData.brain_online} />
          <ConfigRow label="Total Memories" value={String(memoryCount)} />
          <ConfigRow label="Storage Path" value={brainData.storage?.path || '--'} />
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

      {/* ── PAYMENTS ── */}
      <CollapsibleSection title="Payments" icon={<CreditCard size={15} />} iconColor="#16a34a" expanded={expanded.payments} onToggle={() => toggle('payments')}>
        <PaymentModule product="platform" />
      </CollapsibleSection>

      {/* ── DOCUMENTATION ── */}
      <CollapsibleSection title="Documentation" icon={<BookOpen size={15} />} iconColor="#7c3aed" expanded={expanded.docs} onToggle={() => toggle('docs')}>
        <ProductDocs product="platform" />
      </CollapsibleSection>

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
