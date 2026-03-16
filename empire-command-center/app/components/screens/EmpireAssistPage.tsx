'use client';
import React, { useState, useEffect } from 'react';
import {
  Bot, Zap, FileText, Clock, Settings, Play, Pause, RotateCcw,
  Mail, FileDown, Share2, BarChart3, PenTool, Users, Hash,
  Sparkles, ChevronRight, Copy, Star, Activity, MessageSquare,
  Cpu, Thermometer, SlidersHorizontal, CheckCircle, AlertTriangle, BookOpen, CreditCard,
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';

const ACCENT = '#b8960c';
const ACCENT_BG = 'rgba(184,150,12,0.10)';
const ACCENT_BORDER = 'rgba(184,150,12,0.25)';

const NAV_SECTIONS = [
  { id: 'dashboard', label: 'Dashboard', icon: Activity },
  { id: 'automations', label: 'Automations', icon: Zap },
  { id: 'templates', label: 'Templates', icon: FileText },
  { id: 'history', label: 'History', icon: Clock },
  { id: 'settings', label: 'Settings', icon: Settings },
  { id: 'payments', label: 'Payments', icon: CreditCard },
  { id: 'docs', label: 'Docs', icon: BookOpen },
] as const;

type Section = typeof NAV_SECTIONS[number]['id'];

// ============ MOCK DATA ============

const MOCK_STATS = {
  requestsToday: 47,
  avgResponseTime: '1.2s',
  activeAutomations: 3,
  popularCommands: [
    { name: 'Draft Email', count: 18 },
    { name: 'Summarize Doc', count: 12 },
    { name: 'Generate Social Post', count: 9 },
    { name: 'Analyze Data', count: 5 },
    { name: 'Customer Response', count: 3 },
  ],
};

const MOCK_AUTOMATIONS = [
  {
    id: '1', name: 'New lead → Welcome email', trigger: 'New CRM Lead',
    action: 'Send welcome email via Mail', status: 'active' as const,
    lastRun: '2026-03-09 08:14', runCount: 142,
  },
  {
    id: '2', name: 'Invoice overdue → Reminder', trigger: 'Invoice 30+ days',
    action: 'Send reminder + Telegram alert', status: 'active' as const,
    lastRun: '2026-03-09 07:30', runCount: 67,
  },
  {
    id: '3', name: 'New order → Shipping label', trigger: 'Order confirmed',
    action: 'Generate shipping label via ShipForge', status: 'paused' as const,
    lastRun: '2026-03-08 22:10', runCount: 231,
  },
];

const MOCK_TEMPLATES = [
  { id: '1', name: 'Draft Email', description: 'Compose a professional email from a brief prompt', icon: Mail, category: 'Communication', useCount: 284 },
  { id: '2', name: 'Summarize Doc', description: 'Condense a long document into key points', icon: FileDown, category: 'Productivity', useCount: 197 },
  { id: '3', name: 'Generate Social Post', description: 'Create platform-optimized social media content', icon: Share2, category: 'Marketing', useCount: 156 },
  { id: '4', name: 'Analyze Data', description: 'Extract insights and trends from CSV or JSON data', icon: BarChart3, category: 'Analytics', useCount: 89 },
  { id: '5', name: 'Write Proposal', description: 'Generate a client proposal from project details', icon: PenTool, category: 'Sales', useCount: 73 },
  { id: '6', name: 'Customer Response', description: 'Draft a helpful reply to a customer inquiry', icon: Users, category: 'Support', useCount: 118 },
];

// History loaded from real API (token usage logs)

const MODELS = ['Grok', 'Claude', 'Ollama'] as const;

// ============ COMPONENT ============

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export default function EmpireAssistPage() {
  const [activeSection, setActiveSection] = useState<Section>('dashboard');
  const [automations, setAutomations] = useState(MOCK_AUTOMATIONS);
  const [defaultModel, setDefaultModel] = useState<string>('Grok');
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(2048);
  const [history, setHistory] = useState<Array<{id: string; timestamp: string; prompt: string; module: string; tokens: number; model: string}>>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    setHistoryLoading(true);
    fetch(`${API}/costs/recent?limit=20`)
      .then(r => r.json())
      .then(data => {
        const logs = (data.recent || data.logs || []).map((log: Record<string, unknown>, i: number) => ({
          id: String(i),
          timestamp: String(log.timestamp || '').slice(0, 16).replace('T', ' '),
          prompt: String(log.prompt || log.description || 'AI request'),
          module: String(log.desk || log.source || 'MAX'),
          tokens: Number(log.total_tokens || log.tokens || 0),
          model: String(log.model || 'unknown'),
        }));
        setHistory(logs);
      })
      .catch(() => setHistory([]))
      .finally(() => setHistoryLoading(false));
  }, []);

  const toggleAutomation = (id: string) => {
    setAutomations(prev => prev.map(a =>
      a.id === id ? { ...a, status: a.status === 'active' ? 'paused' as const : 'active' as const } : a
    ));
  };

  // ---- Sub-renders ----

  const renderDashboard = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
        {[
          { label: 'AI Requests Today', value: MOCK_STATS.requestsToday, icon: MessageSquare },
          { label: 'Avg Response Time', value: MOCK_STATS.avgResponseTime, icon: Clock },
          { label: 'Active Automations', value: MOCK_STATS.activeAutomations, icon: Zap },
        ].map(s => (
          <div key={s.label} style={{
            background: 'var(--card-bg, #111)', border: `1px solid ${ACCENT_BORDER}`,
            borderRadius: 12, padding: '20px 22px', display: 'flex', alignItems: 'center', gap: 16,
          }}>
            <div style={{ background: ACCENT_BG, borderRadius: 10, padding: 10 }}>
              <s.icon size={22} color={ACCENT} />
            </div>
            <div>
              <div style={{ fontSize: 26, fontWeight: 700, color: 'var(--text, #fff)' }}>{s.value}</div>
              <div style={{ fontSize: 12, color: 'var(--muted, #888)', marginTop: 2 }}>{s.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Popular commands */}
      <div style={{
        background: 'var(--card-bg, #111)', border: `1px solid ${ACCENT_BORDER}`,
        borderRadius: 12, padding: '20px 24px',
      }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: 'var(--text, #fff)', marginBottom: 16 }}>
          <Star size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} color={ACCENT} />
          Popular Commands
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {MOCK_STATS.popularCommands.map((cmd, i) => (
            <div key={cmd.name} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '8px 12px', borderRadius: 8,
              background: i === 0 ? ACCENT_BG : 'transparent',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 12, color: 'var(--muted, #888)', width: 20 }}>#{i + 1}</span>
                <span style={{ fontSize: 14, color: 'var(--text, #fff)' }}>{cmd.name}</span>
              </div>
              <span style={{
                fontSize: 12, fontWeight: 600, color: ACCENT,
                background: ACCENT_BG, padding: '2px 10px', borderRadius: 8,
              }}>{cmd.count} uses</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderAutomations = () => (
    <div style={{
      background: 'var(--card-bg, #111)', border: `1px solid ${ACCENT_BORDER}`,
      borderRadius: 12, overflow: 'hidden',
    }}>
      <div style={{ padding: '16px 24px', borderBottom: `1px solid ${ACCENT_BORDER}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: 'var(--text, #fff)' }}>
          <Zap size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} color={ACCENT} />
          Automations
        </h3>
        <span style={{ fontSize: 12, color: 'var(--muted, #888)' }}>{automations.filter(a => a.status === 'active').length} active</span>
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <thead>
          <tr style={{ borderBottom: `1px solid ${ACCENT_BORDER}` }}>
            {['Name', 'Trigger', 'Action', 'Status', 'Last Run', 'Runs'].map(h => (
              <th key={h} style={{ padding: '10px 16px', textAlign: 'left', color: 'var(--muted, #888)', fontWeight: 500, fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.5 }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {automations.map(a => (
            <tr key={a.id} style={{ borderBottom: `1px solid rgba(255,255,255,0.04)` }}>
              <td style={{ padding: '12px 16px', color: 'var(--text, #fff)', fontWeight: 500 }}>{a.name}</td>
              <td style={{ padding: '12px 16px', color: 'var(--muted, #888)' }}>{a.trigger}</td>
              <td style={{ padding: '12px 16px', color: 'var(--muted, #888)' }}>{a.action}</td>
              <td style={{ padding: '12px 16px' }}>
                <button
                  onClick={() => toggleAutomation(a.id)}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 6,
                    padding: '4px 12px', borderRadius: 20, border: 'none', cursor: 'pointer',
                    fontSize: 12, fontWeight: 600,
                    background: a.status === 'active' ? 'rgba(22,163,74,0.15)' : 'rgba(255,255,255,0.06)',
                    color: a.status === 'active' ? '#16a34a' : '#888',
                  }}
                >
                  {a.status === 'active' ? <Play size={11} /> : <Pause size={11} />}
                  {a.status === 'active' ? 'Active' : 'Paused'}
                </button>
              </td>
              <td style={{ padding: '12px 16px', color: 'var(--muted, #888)', fontSize: 12 }}>{a.lastRun}</td>
              <td style={{ padding: '12px 16px', color: ACCENT, fontWeight: 600 }}>{a.runCount}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const renderTemplates = () => (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
      {MOCK_TEMPLATES.map(t => (
        <div key={t.id} style={{
          background: 'var(--card-bg, #111)', border: `1px solid ${ACCENT_BORDER}`,
          borderRadius: 12, padding: '20px 22px',
          display: 'flex', flexDirection: 'column', gap: 12,
          cursor: 'pointer', transition: 'border-color 0.2s',
        }}
        onMouseEnter={e => (e.currentTarget.style.borderColor = ACCENT)}
        onMouseLeave={e => (e.currentTarget.style.borderColor = ACCENT_BORDER)}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ background: ACCENT_BG, borderRadius: 10, padding: 10 }}>
              <t.icon size={20} color={ACCENT} />
            </div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--text, #fff)' }}>{t.name}</div>
              <div style={{ fontSize: 11, color: ACCENT, fontWeight: 500 }}>{t.category}</div>
            </div>
          </div>
          <p style={{ fontSize: 13, color: 'var(--muted, #888)', lineHeight: 1.5, margin: 0 }}>{t.description}</p>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 'auto' }}>
            <span style={{ fontSize: 11, color: 'var(--muted, #888)' }}>
              <Hash size={11} style={{ verticalAlign: 'middle', marginRight: 3 }} />{t.useCount} uses
            </span>
            <button style={{
              background: ACCENT_BG, border: `1px solid ${ACCENT_BORDER}`, borderRadius: 8,
              padding: '4px 12px', fontSize: 12, color: ACCENT, cursor: 'pointer', fontWeight: 500,
            }}>
              Use <ChevronRight size={12} style={{ verticalAlign: 'middle' }} />
            </button>
          </div>
        </div>
      ))}
    </div>
  );

  const renderHistory = () => (
    <div style={{
      background: 'var(--card-bg, #111)', border: `1px solid ${ACCENT_BORDER}`,
      borderRadius: 12, overflow: 'hidden',
    }}>
      <div style={{ padding: '16px 24px', borderBottom: `1px solid ${ACCENT_BORDER}` }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: 'var(--text, #fff)', margin: 0 }}>
          <Clock size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} color={ACCENT} />
          Recent AI Interactions
        </h3>
      </div>
      {historyLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 32 }}>
          <div style={{ width: 32, height: 32, border: `2px solid ${ACCENT}`, borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
        </div>
      ) : history.length === 0 ? (
        <div style={{ padding: 32, textAlign: 'center', color: 'var(--muted, #888)', fontSize: 14 }}>No AI interactions yet</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {history.map((h, i) => (
            <div key={h.id} style={{
              display: 'grid', gridTemplateColumns: '130px 1fr 120px 80px 140px',
              alignItems: 'center', padding: '12px 24px', gap: 12,
              borderBottom: i < history.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none',
            }}>
              <span style={{ fontSize: 12, color: 'var(--muted, #888)', fontFamily: 'monospace' }}>{h.timestamp}</span>
              <span style={{ fontSize: 13, color: 'var(--text, #fff)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{h.prompt}</span>
              <span style={{
                fontSize: 11, fontWeight: 500, color: ACCENT,
                background: ACCENT_BG, padding: '2px 8px', borderRadius: 6, textAlign: 'center',
              }}>{h.module}</span>
              <span style={{ fontSize: 12, color: 'var(--muted, #888)', textAlign: 'right' }}>{h.tokens} tok</span>
              <span style={{
                fontSize: 11, color: 'var(--muted, #888)',
                background: 'rgba(255,255,255,0.04)', padding: '2px 8px', borderRadius: 6, textAlign: 'center',
                fontFamily: 'monospace',
              }}>{h.model}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  const renderSettings = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 600 }}>
      {/* Default Model */}
      <div style={{
        background: 'var(--card-bg, #111)', border: `1px solid ${ACCENT_BORDER}`,
        borderRadius: 12, padding: '20px 24px',
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text, #fff)', marginBottom: 14 }}>
          <Cpu size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} color={ACCENT} />
          Default AI Model
        </h3>
        <div style={{ display: 'flex', gap: 10 }}>
          {MODELS.map(m => (
            <button key={m} onClick={() => setDefaultModel(m)} style={{
              flex: 1, padding: '10px 16px', borderRadius: 10, cursor: 'pointer',
              fontSize: 13, fontWeight: 600, border: `1px solid ${defaultModel === m ? ACCENT : ACCENT_BORDER}`,
              background: defaultModel === m ? ACCENT_BG : 'transparent',
              color: defaultModel === m ? ACCENT : 'var(--muted, #888)',
              transition: 'all 0.2s',
            }}>
              {defaultModel === m && <CheckCircle size={13} style={{ marginRight: 5, verticalAlign: 'middle' }} />}
              {m}
            </button>
          ))}
        </div>
      </div>

      {/* Temperature */}
      <div style={{
        background: 'var(--card-bg, #111)', border: `1px solid ${ACCENT_BORDER}`,
        borderRadius: 12, padding: '20px 24px',
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text, #fff)', marginBottom: 14 }}>
          <Thermometer size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} color={ACCENT} />
          Temperature
          <span style={{ fontSize: 12, color: ACCENT, marginLeft: 10, fontWeight: 400 }}>{temperature.toFixed(1)}</span>
        </h3>
        <input
          type="range" min="0" max="2" step="0.1"
          value={temperature}
          onChange={e => setTemperature(parseFloat(e.target.value))}
          style={{ width: '100%', accentColor: ACCENT }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--muted, #888)', marginTop: 6 }}>
          <span>Precise (0.0)</span>
          <span>Creative (2.0)</span>
        </div>
      </div>

      {/* Max Tokens */}
      <div style={{
        background: 'var(--card-bg, #111)', border: `1px solid ${ACCENT_BORDER}`,
        borderRadius: 12, padding: '20px 24px',
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text, #fff)', marginBottom: 14 }}>
          <SlidersHorizontal size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} color={ACCENT} />
          Max Tokens
        </h3>
        <div style={{ display: 'flex', gap: 10 }}>
          {[512, 1024, 2048, 4096].map(t => (
            <button key={t} onClick={() => setMaxTokens(t)} style={{
              flex: 1, padding: '8px 10px', borderRadius: 8, cursor: 'pointer',
              fontSize: 13, fontWeight: 500, border: `1px solid ${maxTokens === t ? ACCENT : ACCENT_BORDER}`,
              background: maxTokens === t ? ACCENT_BG : 'transparent',
              color: maxTokens === t ? ACCENT : 'var(--muted, #888)',
              transition: 'all 0.2s',
            }}>
              {t.toLocaleString()}
            </button>
          ))}
        </div>
      </div>

      {/* Per-product AI config */}
      <div style={{
        background: 'var(--card-bg, #111)', border: `1px solid ${ACCENT_BORDER}`,
        borderRadius: 12, padding: '20px 24px',
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text, #fff)', marginBottom: 14 }}>
          <Settings size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} color={ACCENT} />
          Per-Product AI Config
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {[
            { product: 'WorkroomForge', model: 'Grok', temp: 0.5 },
            { product: 'CraftForge', model: 'Claude', temp: 0.8 },
            { product: 'SocialForge', model: 'Grok', temp: 0.9 },
            { product: 'ShipForge', model: 'Ollama', temp: 0.3 },
            { product: 'SupportForge', model: 'Claude', temp: 0.6 },
          ].map(cfg => (
            <div key={cfg.product} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '8px 12px', borderRadius: 8, background: 'rgba(255,255,255,0.02)',
            }}>
              <span style={{ fontSize: 13, color: 'var(--text, #fff)' }}>{cfg.product}</span>
              <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                <span style={{
                  fontSize: 11, color: ACCENT, background: ACCENT_BG,
                  padding: '2px 10px', borderRadius: 6, fontWeight: 500,
                }}>{cfg.model}</span>
                <span style={{ fontSize: 11, color: 'var(--muted, #888)' }}>temp: {cfg.temp}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const SECTION_RENDER: Record<Section, () => React.ReactNode> = {
    dashboard: renderDashboard,
    automations: renderAutomations,
    templates: renderTemplates,
    history: renderHistory,
    settings: renderSettings,
    payments: () => <PaymentModule product="assist" />,
    docs: () => <div style={{ padding: 24 }}><ProductDocs product="assist" /></div>,
  };

  return (
    <div style={{ display: 'flex', height: '100%', background: 'var(--chat-bg, #0a0a0a)' }}>
      {/* Left nav */}
      <div style={{
        width: 200, borderRight: `1px solid ${ACCENT_BORDER}`,
        display: 'flex', flexDirection: 'column', padding: '18px 0',
        background: 'var(--card-bg, #111)',
      }}>
        <div style={{
          padding: '0 18px 18px', borderBottom: `1px solid ${ACCENT_BORDER}`,
          marginBottom: 12, display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <div style={{ background: ACCENT_BG, borderRadius: 10, padding: 8 }}>
            <Bot size={20} color={ACCENT} />
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text, #fff)' }}>EmpireAssist</div>
            <div style={{ fontSize: 11, color: 'var(--muted, #888)' }}>AI Assistant</div>
          </div>
        </div>
        {NAV_SECTIONS.map(s => (
          <button
            key={s.id}
            onClick={() => setActiveSection(s.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '10px 18px', border: 'none', cursor: 'pointer',
              background: activeSection === s.id ? ACCENT_BG : 'transparent',
              color: activeSection === s.id ? ACCENT : 'var(--muted, #888)',
              fontSize: 13, fontWeight: activeSection === s.id ? 600 : 400,
              borderLeft: activeSection === s.id ? `3px solid ${ACCENT}` : '3px solid transparent',
              transition: 'all 0.15s',
            }}
          >
            <s.icon size={16} />
            {s.label}
          </button>
        ))}
      </div>

      {/* Main content */}
      <div style={{ flex: 1, padding: '24px 32px', overflowY: 'auto' }}>
        <div style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text, #fff)', margin: 0 }}>
            {NAV_SECTIONS.find(s => s.id === activeSection)?.label}
          </h2>
          <p style={{ fontSize: 13, color: 'var(--muted, #888)', marginTop: 4 }}>
            {activeSection === 'dashboard' && 'Overview of AI assistant activity and popular commands'}
            {activeSection === 'automations' && 'Manage AI-powered workflow automations'}
            {activeSection === 'templates' && 'Reusable AI prompt templates for common tasks'}
            {activeSection === 'history' && 'Recent AI interactions across all Empire products'}
            {activeSection === 'settings' && 'Configure default AI model, parameters, and per-product settings'}
          </p>
        </div>
        {SECTION_RENDER[activeSection]()}
      </div>
    </div>
  );
}
