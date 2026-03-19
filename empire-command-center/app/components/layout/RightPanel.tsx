'use client';
import { useState, useEffect, useCallback } from 'react';
import { Desk, ScreenMode, EcosystemProduct } from '../../lib/types';
import { API } from '../../lib/api';
import {
  Plus, Check, X, Loader2, ChevronDown, ChevronUp, Package, AlertTriangle,
  DollarSign, Users, TrendingUp, ClipboardList, FileText, Flag, Calendar,
  Zap, Sparkles, Send, BookOpen, Camera, CheckCircle2, Eye, ArrowRight,
  Bot, Hammer, ShoppingBag, Megaphone, Headphones, BadgeDollarSign, PieChart,
  Wrench, Monitor, Globe, Scale, FlaskConical, Shield, Sun, BarChart3, Building2,
} from 'lucide-react';

interface Props {
  desks: Desk[];
  briefing: string;
  systemStats?: any;
  activeScreen: ScreenMode;
  activeProduct: EcosystemProduct;
  activeSection?: string | null;
  onScreenChange: (screen: ScreenMode) => void;
  onModuleClick: (module: string) => void;
  onDeskSelect?: (deskId: string) => void;
}

export default function RightPanel({ desks, briefing, systemStats, activeScreen, activeProduct, activeSection, onScreenChange, onModuleClick, onDeskSelect }: Props) {
  const [activeModule, setActiveModule] = useState<string | null>(null);
  const [moduleStats, setModuleStats] = useState<Record<string, string>>({});
  const [tgStatus, setTgStatus] = useState<{ configured: boolean } | null>(null);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [contextData, setContextData] = useState<any>(null);

  const safeFetch = useCallback(async (url: string) => {
    try { const r = await fetch(url); if (!r.ok) return null; return await r.json(); } catch { return null; }
  }, []);

  // Toggle collapse
  const toggle = (key: string) => setCollapsed(c => ({ ...c, [key]: !c[key] }));

  // (Tasks moved to dedicated WorkroomPage Tasks tab)

  // Fetch context-specific data based on active view
  const fetchContextData = useCallback(async () => {
    const section = activeSection || '';

    if (activeProduct === 'workroom' && section === 'inventory') {
      const data = await safeFetch(`${API}/inventory/dashboard`);
      setContextData({ type: 'inventory', data });
    } else if (activeProduct === 'workroom' && (section === 'quotes' || section === '')) {
      const data = await safeFetch(`${API}/quotes`);
      setContextData({ type: 'quotes', data });
    } else if (activeProduct === 'workroom' && section === 'customers') {
      const data = await safeFetch(`${API}/crm/customers?limit=5`);
      setContextData({ type: 'customers', data });
    } else if (activeProduct === 'workroom' && section === 'finance') {
      const data = await safeFetch(`${API}/finance/dashboard`);
      setContextData({ type: 'finance', data });
    } else if (activeProduct === 'owner') {
      const [quotes, customers] = await Promise.all([
        safeFetch(`${API}/quotes`),
        safeFetch(`${API}/crm/customers?limit=3`),
      ]);
      setContextData({ type: 'owner', quotes, customers });
    } else {
      setContextData(null);
    }
  }, [activeProduct, activeSection, safeFetch]);

  // Fetch module stats
  const fetchModuleStats = useCallback(async () => {
    const stats: Record<string, string> = {};
    const [quotes, invoices, customers, inventory, tickets, costs, tasksDash] = await Promise.all([
      safeFetch(`${API}/quotes`),
      safeFetch(`${API}/finance/invoices?limit=1`),
      safeFetch(`${API}/crm/customers?limit=1`),
      safeFetch(`${API}/inventory/items?limit=1`),
      safeFetch(`${API}/tickets/?status=open&limit=1`),
      safeFetch(`${API}/costs/overview?days=30`),
      safeFetch(`${API}/tasks/dashboard`),
    ]);
    stats.quotes = quotes ? `${(quotes.quotes || []).filter((q: any) => q.status !== 'accepted').length} open` : 'Offline';
    stats.invoices = invoices ? `${invoices.total ?? 0} total` : 'Offline';
    stats.crm = customers ? `${customers.total ?? 0} contacts` : 'Offline';
    stats.inventory = inventory ? `${inventory.total ?? 0} items` : 'Offline';
    stats.tickets = tickets ? `${tickets.total ?? 0} open` : 'Offline';
    stats.costs = costs?.today?.cost_usd ? `$${costs.today.cost_usd.toFixed(2)} today` : 'Token tracking';
    stats.shipping = '--';
    stats.reports = 'Weekly ready';
    if (tasksDash?.totals) {
      const active = (tasksDash.totals.todo || 0) + (tasksDash.totals.in_progress || 0) + (tasksDash.totals.waiting || 0);
      stats.tasks = `${active} active`;
    } else {
      stats.tasks = '--';
    }
    setModuleStats(stats);
  }, [safeFetch]);

  useEffect(() => {
    fetchModuleStats();
    fetchContextData();
    fetch(API + '/max/telegram/status').then(r => r.ok ? r.json() : null).then(d => { if (d) setTgStatus(d); }).catch(() => {});
    const iv = setInterval(() => { fetchModuleStats(); fetchContextData(); }, 60000);
    return () => clearInterval(iv);
  }, [fetchModuleStats, fetchContextData]);

  // Re-fetch context when view changes
  useEffect(() => { fetchContextData(); }, [activeProduct, activeSection, fetchContextData]);

  const handleModuleClick = (moduleId: string) => {
    setActiveModule(moduleId === activeModule ? null : moduleId);
    onModuleClick(moduleId);
  };

  // (Task management moved to WorkroomPage Tasks tab)

  // Business-specific modules
  const getModules = () => {
    if (activeProduct === 'workroom') {
      return [
        { id: 'quotes', label: 'Quotes', stat: moduleStats.quotes || '...' },
        { id: 'invoices', label: 'Invoices', stat: moduleStats.invoices || '...' },
        { id: 'crm', label: 'CRM', stat: moduleStats.crm || '...' },
        { id: 'inventory', label: 'Inventory', stat: moduleStats.inventory || '...' },
        { id: 'tasks', label: 'Tasks', stat: moduleStats.tasks || '...' },
        { id: 'shipping', label: 'Shipping', stat: moduleStats.shipping || '--' },
        { id: 'costs', label: 'Costs', stat: moduleStats.costs || '...' },
      ];
    }
    if (activeProduct === 'craft') {
      return [
        { id: 'craft-crm', label: 'CRM', stat: moduleStats.crm || '...' },
        { id: 'inventory', label: 'Materials', stat: moduleStats.inventory || '...' },
        { id: 'quotes', label: 'Orders', stat: moduleStats.quotes || '...' },
        { id: 'tasks', label: 'Tasks', stat: moduleStats.tasks || '...' },
        { id: 'costs', label: 'Costs', stat: moduleStats.costs || '...' },
      ];
    }
    // MAX Desk / Owner — empire-wide overview
    return [
      { id: 'empire-crm', label: 'CRM', stat: moduleStats.crm || '...' },
      { id: 'tasks', label: 'Tasks', stat: moduleStats.tasks || '...' },
      { id: 'costs', label: 'AI Costs', stat: moduleStats.costs || '...' },
      { id: 'tickets', label: 'Tickets', stat: moduleStats.tickets || '...' },
      { id: 'reports', label: 'Reports', stat: moduleStats.reports || '...' },
    ];
  };

  return (
    <aside className="w-[320px] h-full bg-[var(--panel)] border-l border-[var(--border)] flex flex-col shrink-0 overflow-y-auto p-4 gap-3">

      {/* ── v6.0 INTELLIGENCE CARDS ── */}
      <IntelligenceCards collapsed={!!collapsed.intelligence} onToggle={() => toggle('intelligence')} />

      {/* ── CONTEXT-AWARE SECTION ── */}
      {contextData?.type === 'inventory' && contextData.data && (
        <InventoryContext data={contextData.data} />
      )}
      {contextData?.type === 'quotes' && contextData.data && (
        <QuotesContext data={contextData.data} />
      )}
      {contextData?.type === 'customers' && contextData.data && (
        <CustomersContext data={contextData.data} />
      )}
      {contextData?.type === 'finance' && contextData.data && (
        <FinanceContext data={contextData.data} />
      )}
      {contextData?.type === 'owner' && (
        <OwnerContext quotes={contextData.quotes} customers={contextData.customers} />
      )}

      {/* ── NAVIGATION HELPERS (context-aware) ── */}
      <NavigationHelper activeProduct={activeProduct} activeSection={activeSection} onScreenChange={onScreenChange} onModuleClick={onModuleClick} />

      {/* ── AI DESKS (collapsible) ── */}
      <AIDesksPanel
        desks={desks}
        collapsed={!!collapsed.aidesks}
        onToggle={() => toggle('aidesks')}
        onScreenChange={onScreenChange}
        onDeskSelect={onDeskSelect}
      />

      {/* ── TELEGRAM (collapsible) ── */}
      <div>
        <button onClick={() => toggle('telegram')} className="flex items-center justify-between w-full mb-2 cursor-pointer">
          <span className="section-label">Telegram</span>
          <div className="flex items-center gap-2">
            {!collapsed.telegram && (
              <span onClick={(e) => { e.stopPropagation(); onScreenChange('telegram'); }} className="text-[11px] text-[var(--gold)] font-semibold hover:underline">Open →</span>
            )}
            {collapsed.telegram ? <ChevronDown size={12} className="text-[#ccc]" /> : <ChevronUp size={12} className="text-[#ccc]" />}
          </div>
        </button>
        {!collapsed.telegram && (
          <div className="empire-card" onClick={() => onScreenChange('telegram')} style={{ cursor: 'pointer' }}>
            <div className="flex items-center gap-[10px]">
              <span className={`w-2 h-2 rounded-full shrink-0 ${tgStatus?.configured ? 'bg-[var(--green)]' : 'bg-[#dc2626]'}`} />
              <div className="flex-1 min-w-0">
                <div className="text-[12px] font-semibold text-[var(--text)]">MAX Bot</div>
                <div className="text-[10px] text-[var(--muted)] truncate">
                  {tgStatus === null ? 'Checking...' : tgStatus.configured ? 'Connected' : 'Not configured'}
                </div>
              </div>
              <span className={`status-pill ${tgStatus?.configured ? 'ok' : 'overdue'}`} style={{ fontSize: 9 }}>
                {tgStatus?.configured ? 'LIVE' : 'OFF'}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* ── MODULES (collapsible, business-specific) ── */}
      <div>
        <button onClick={() => toggle('modules')} className="flex items-center justify-between w-full mb-2 cursor-pointer">
          <span className="section-label">
            {activeProduct === 'workroom' ? 'Workroom' : activeProduct === 'craft' ? 'WoodCraft' : 'MAX Desk'}
          </span>
          {collapsed.modules ? <ChevronDown size={12} className="text-[#ccc]" /> : <ChevronUp size={12} className="text-[#ccc]" />}
        </button>
        {!collapsed.modules && (
          <div className="grid grid-cols-2 gap-2">
            {getModules().map(m => (
              <div key={m.id} onClick={() => handleModuleClick(m.id)}
                className={`empire-card cursor-pointer ${activeModule === m.id ? 'active' : ''}`}>
                <div className="text-[12px] font-semibold text-[var(--text)]">{m.label}</div>
                <div className="text-[10px] text-[var(--muted)] mt-1">{m.stat}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}

/* ═══════════════════════════════════════════
   Context-Aware Sidebar Panels
   ═══════════════════════════════════════════ */

function InventoryContext({ data }: { data: any }) {
  const categories = data.by_category ? Object.entries(data.by_category) : [];
  return (
    <div>
      <div className="section-label mb-2">Inventory Overview</div>
      <div className="grid grid-cols-2 gap-2 mb-3">
        <MiniKPI label="Total Value" value={`$${(data.total_value || 0).toLocaleString()}`} color="#b8960c" />
        <MiniKPI label="Low Stock" value={String(data.low_stock_count || 0)} color={data.low_stock_count > 0 ? '#d97706' : '#16a34a'} />
        <MiniKPI label="Items" value={String(data.total_items || 0)} color="#2563eb" />
        <MiniKPI label="Vendors" value={String(data.vendor_count || 0)} color="#7c3aed" />
      </div>
      {categories.length > 0 && (
        <>
          <div style={{ fontSize: 9, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>By Category</div>
          <div className="flex flex-col gap-1">
            {categories.map(([cat, info]: [string, any]) => (
              <div key={cat} className="flex items-center justify-between" style={{ padding: '6px 10px', borderRadius: 8, background: '#faf9f7', border: '1px solid #ece8e0' }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: '#555', textTransform: 'capitalize' }}>{cat}</span>
                <div className="flex items-center gap-3">
                  <span style={{ fontSize: 10, color: '#999' }}>{info.count} items</span>
                  {info.low_stock > 0 && (
                    <span style={{ fontSize: 9, fontWeight: 700, color: '#d97706' }}>
                      <AlertTriangle size={9} className="inline" /> {info.low_stock}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function QuotesContext({ data }: { data: any }) {
  const quotes = data?.quotes || [];
  const total = quotes.reduce((s: number, q: any) => s + (q.total || 0), 0);
  const open = quotes.filter((q: any) => q.status !== 'accepted' && q.status !== 'paid').length;
  const accepted = quotes.filter((q: any) => q.status === 'accepted' || q.status === 'paid').length;
  return (
    <div>
      <div className="section-label mb-2">Quote Pipeline</div>
      <div className="grid grid-cols-2 gap-2 mb-3">
        <MiniKPI label="Pipeline" value={`$${total.toLocaleString()}`} color="#b8960c" />
        <MiniKPI label="Open" value={String(open)} color="#d97706" />
        <MiniKPI label="Won" value={String(accepted)} color="#16a34a" />
        <MiniKPI label="Total" value={String(quotes.length)} color="#2563eb" />
      </div>
      {quotes.slice(0, 3).map((q: any) => (
        <div key={q.id || q.quote_number} className="flex items-center justify-between mb-1"
          style={{ padding: '6px 10px', borderRadius: 8, background: '#faf9f7', border: '1px solid #ece8e0' }}>
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#1a1a1a' }}>{q.customer_name || 'Customer'}</div>
            <div style={{ fontSize: 9, color: '#bbb' }}>{q.quote_number}</div>
          </div>
          <span style={{ fontSize: 12, fontWeight: 700, color: '#b8960c' }}>${(q.total || 0).toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
}

function CustomersContext({ data }: { data: any }) {
  const customers = data?.customers || [];
  return (
    <div>
      <div className="section-label mb-2">Recent Customers</div>
      <MiniKPI label="Total Contacts" value={String(data?.total || customers.length)} color="#2563eb" />
      <div className="flex flex-col gap-1 mt-2">
        {customers.slice(0, 4).map((c: any) => (
          <div key={c.id} style={{ padding: '6px 10px', borderRadius: 8, background: '#faf9f7', border: '1px solid #ece8e0' }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#1a1a1a' }}>{c.name}</div>
            <div style={{ fontSize: 9, color: '#bbb' }}>{c.email || c.phone || c.type || 'Customer'}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function FinanceContext({ data }: { data: any }) {
  return (
    <div>
      <div className="section-label mb-2">Financial Summary</div>
      <div className="grid grid-cols-2 gap-2">
        <MiniKPI label="Revenue" value={`$${(data?.total_revenue || 0).toLocaleString()}`} color="#16a34a" />
        <MiniKPI label="Expenses" value={`$${(data?.total_expenses || 0).toLocaleString()}`} color="#dc2626" />
        <MiniKPI label="Outstanding" value={`$${(data?.outstanding || 0).toLocaleString()}`} color="#d97706" />
        <MiniKPI label="Overdue" value={`$${(data?.overdue || 0).toLocaleString()}`} color="#dc2626" />
      </div>
    </div>
  );
}

function OwnerContext({ quotes, customers }: { quotes: any; customers: any }) {
  const allQuotes = quotes?.quotes || [];
  const pipeline = allQuotes.reduce((s: number, q: any) => s + (q.total || 0), 0);
  const totalCustomers = customers?.total ?? 0;
  return (
    <div>
      <div className="section-label mb-2">Empire Overview</div>
      <div className="grid grid-cols-2 gap-2 mb-2">
        <MiniKPI label="Pipeline" value={`$${pipeline.toLocaleString()}`} color="#b8960c" />
        <MiniKPI label="Quotes" value={String(allQuotes.length)} color="#2563eb" />
        <MiniKPI label="Contacts" value={String(totalCustomers)} color="#7c3aed" />
        <MiniKPI label="Businesses" value="3" color="#16a34a" />
      </div>
    </div>
  );
}

function MiniKPI({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ padding: '8px 10px', borderRadius: 10, background: '#faf9f7', border: '1px solid #ece8e0' }}>
      <div style={{ fontSize: 9, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</div>
      <div style={{ fontSize: 15, fontWeight: 700, color, marginTop: 2 }}>{value}</div>
    </div>
  );
}

/* ═══════════════════════════════════════════
   Context-Aware Navigation Helper
   Shows relevant shortcuts, history, and actions
   based on what the user is viewing
   ═══════════════════════════════════════════ */

function NavigationHelper({ activeProduct, activeSection, onScreenChange, onModuleClick }: {
  activeProduct: EcosystemProduct;
  activeSection?: string | null;
  onScreenChange: (screen: ScreenMode) => void;
  onModuleClick: (module: string) => void;
}) {
  const [analysisHistory, setAnalysisHistory] = useState<any[]>([]);
  const [recentTasks, setRecentTasks] = useState<any[]>([]);

  useEffect(() => {
    // Fetch analysis history when on vision/analysis screens
    if (activeProduct === 'vision' || activeSection === 'analysis') {
      fetch(`${API}/vision/history?limit=8`)
        .then(r => r.ok ? r.json() : { jobs: [] })
        .then(data => setAnalysisHistory(data.jobs || data || []))
        .catch(() => setAnalysisHistory([]));
    }
    // Always fetch a few recent tasks for quick reference
    fetch(`${API}/tasks/?limit=4`)
      .then(r => r.ok ? r.json() : { tasks: [] })
      .then(data => setRecentTasks((data.tasks || []).filter((t: any) => t.status !== 'done').slice(0, 3)))
      .catch(() => {});
  }, [activeProduct, activeSection]);

  // AI Analysis context — show analysis history
  if (activeProduct === 'vision' || activeSection === 'analysis') {
    return (
      <div>
        <div className="section-label mb-2">Analysis History</div>
        {analysisHistory.length > 0 ? (
          <div className="flex flex-col gap-1.5">
            {analysisHistory.map((job: any, i: number) => (
              <div key={job.id || i} className="empire-card" style={{ padding: '8px 10px' }}>
                <div className="flex items-center gap-2">
                  <Camera size={12} className="text-[#7c3aed] shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div style={{ fontSize: 11, fontWeight: 600, color: '#1a1a1a' }} className="truncate">
                      {job.customer_name || job.type || `Analysis #${i + 1}`}
                    </div>
                    <div style={{ fontSize: 9, color: '#999' }}>
                      {job.type || 'measure'} · {job.photos_count || 1} photo{(job.photos_count || 1) > 1 ? 's' : ''}
                    </div>
                  </div>
                  <span className={`status-pill ${job.status === 'completed' ? 'ok' : job.status === 'error' ? 'overdue' : 'transit'}`} style={{ fontSize: 8 }}>
                    {(job.status || 'done').toUpperCase()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ padding: '12px 10px', borderRadius: 10, background: '#faf5ff', border: '1px solid #e9d5ff', textAlign: 'center' }}>
            <Camera size={20} className="text-[#d8b4fe] mx-auto mb-1" />
            <div style={{ fontSize: 11, color: '#999' }}>No analyses yet</div>
            <div style={{ fontSize: 9, color: '#ccc' }}>Upload a photo to get started</div>
          </div>
        )}
        <div className="mt-3">
          <div style={{ fontSize: 9, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>Quick Actions</div>
          <div className="flex flex-col gap-1">
            <SidebarAction label="New Measurement" icon={<Camera size={12} />} color="#7c3aed" />
            <SidebarAction label="Design Mockup" icon={<Sparkles size={12} />} color="#b8960c" />
            <SidebarAction label="View All Quotes" icon={<ClipboardList size={12} />} color="#16a34a" onClick={() => onModuleClick('quotes')} />
          </div>
        </div>
      </div>
    );
  }

  // Tasks context — show task stats
  if (activeSection === 'tasks') {
    return (
      <div>
        <div className="section-label mb-2">Task Tips</div>
        <div className="flex flex-col gap-1.5">
          <div style={{ padding: '10px 12px', borderRadius: 10, background: '#fdf8eb', border: '1px solid #f0e6c0' }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#b8960c', marginBottom: 4 }}>Assign to AI Desks</div>
            <div style={{ fontSize: 10, color: '#999', lineHeight: 1.4 }}>Tasks assigned to a desk will be automatically processed by the AI desk agent.</div>
          </div>
          <div style={{ padding: '10px 12px', borderRadius: 10, background: '#f0fdf4', border: '1px solid #bbf7d0' }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#16a34a', marginBottom: 4 }}>Priority Levels</div>
            <div style={{ fontSize: 10, color: '#999', lineHeight: 1.4 }}>Urgent tasks trigger notifications. High priority tasks appear at the top of desk queues.</div>
          </div>
        </div>
        <div className="mt-3">
          <div style={{ fontSize: 9, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>Suggested</div>
          <div className="flex flex-col gap-1">
            <SidebarAction label="Follow up pending quotes" icon={<ClipboardList size={12} />} color="#d97706" />
            <SidebarAction label="Review intake submissions" icon={<FileText size={12} />} color="#2563eb" />
            <SidebarAction label="Check low stock items" icon={<Package size={12} />} color="#dc2626" />
          </div>
        </div>
      </div>
    );
  }

  // Default — show recent tasks compact + quick navigation
  if (activeProduct === 'workroom' || activeProduct === 'owner') {
    return (
      <div>
        {recentTasks.length > 0 && (
          <>
            <div className="section-label mb-2">Pending Tasks</div>
            <div className="flex flex-col gap-1 mb-3">
              {recentTasks.map((t: any) => (
                <div key={t.id} className="flex items-center gap-2" style={{ padding: '6px 10px', borderRadius: 8, background: '#faf9f7', border: '1px solid #ece8e0' }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: t.priority === 'urgent' ? '#dc2626' : t.priority === 'high' ? '#d97706' : '#b8960c', flexShrink: 0 }} />
                  <span style={{ fontSize: 10, color: '#555', fontWeight: 500 }} className="truncate">{t.title}</span>
                </div>
              ))}
              <button onClick={() => onModuleClick('tasks')} style={{ fontSize: 10, color: '#b8960c', fontWeight: 600, background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left', padding: '4px 10px' }}>
                View all tasks →
              </button>
            </div>
          </>
        )}
        <div className="mt-2">
          <div style={{ fontSize: 9, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>Settings</div>
          <div className="flex flex-col gap-1">
            <SidebarAction label="Business Profile" icon={<Building2 size={12} />} color="#b8960c" onClick={() => onScreenChange('business-profile')} />
          </div>
        </div>
      </div>
    );
  }

  return null;
}

/* ═══════════════════════════════════════════
   AI Desks — Sidebar Navigator
   Compact list, clicks open detail in center screen
   ═══════════════════════════════════════════ */

const SIDEBAR_DESK_ICONS: Record<string, { text: string; Icon: React.ComponentType<any> }> = {
  forge:       { text: '#16a34a', Icon: Hammer },
  market:      { text: '#2563eb', Icon: ShoppingBag },
  marketing:   { text: '#ec4899', Icon: Megaphone },
  support:     { text: '#7c3aed', Icon: Headphones },
  sales:       { text: '#b8960c', Icon: BadgeDollarSign },
  finance:     { text: '#d97706', Icon: PieChart },
  clients:     { text: '#0891b2', Icon: Users },
  contractors: { text: '#b45309', Icon: Wrench },
  it:          { text: '#0284c7', Icon: Monitor },
  website:     { text: '#db2777', Icon: Globe },
  legal:       { text: '#64748b', Icon: Scale },
  lab:         { text: '#a16207', Icon: FlaskConical },
};

function AIDesksPanel({ desks, collapsed, onToggle, onScreenChange, onDeskSelect }: {
  desks: Desk[];
  collapsed: boolean;
  onToggle: () => void;
  onScreenChange: (screen: ScreenMode) => void;
  onDeskSelect?: (deskId: string) => void;
}) {
  const [listExpanded, setListExpanded] = useState(false);
  const busyCount = desks.filter(d => d.status === 'busy').length;

  const handleDeskClick = (deskId: string) => {
    if (onDeskSelect) onDeskSelect(deskId);
    else onScreenChange('desks');
  };

  return (
    <div>
      <button onClick={onToggle} className="flex items-center justify-between w-full mb-2 cursor-pointer">
        <span className="section-label">AI Desks</span>
        <div className="flex items-center gap-2">
          {!collapsed && (
            <span onClick={(e) => { e.stopPropagation(); onScreenChange('desks'); }}
              className="text-[11px] text-[var(--gold)] font-semibold hover:underline cursor-pointer">Open →</span>
          )}
          {collapsed ? <ChevronDown size={12} className="text-[#ccc]" /> : <ChevronUp size={12} className="text-[#ccc]" />}
        </div>
      </button>
      {!collapsed && (
        <>
          {/* Summary card */}
          <div className="empire-card" onClick={() => onScreenChange('desks')} style={{ cursor: 'pointer' }}>
            <div className="flex items-center gap-[10px]">
              <span className={`w-2 h-2 rounded-full shrink-0 ${busyCount > 0 ? 'bg-[#d97706]' : 'bg-[var(--green)]'}`} />
              <div className="flex-1 min-w-0">
                <div className="text-[12px] font-semibold text-[var(--text)]">{desks.length} AI Agents</div>
                <div className="text-[10px] text-[var(--muted)] truncate">
                  {busyCount > 0 ? `${busyCount} busy` : 'All idle'}
                </div>
              </div>
              <span className={`status-pill ${busyCount > 0 ? 'transit' : 'ok'}`} style={{ fontSize: 9 }}>
                {busyCount > 0 ? 'BUSY' : 'READY'}
              </span>
            </div>
          </div>

          {/* Collapsible agent list */}
          <button onClick={() => setListExpanded(!listExpanded)}
            className="flex items-center justify-between w-full cursor-pointer mt-1 px-1"
            style={{ background: 'none', border: 'none', padding: '4px 4px' }}>
            <span style={{ fontSize: 10, fontWeight: 600, color: '#999' }}>{listExpanded ? 'Hide agents' : 'Show agents'}</span>
            {listExpanded ? <ChevronUp size={10} className="text-[#ccc]" /> : <ChevronDown size={10} className="text-[#ccc]" />}
          </button>

          {listExpanded && (
            <div className="flex flex-col gap-0.5">
              {desks.map(d => {
                const cfg = SIDEBAR_DESK_ICONS[d.id] || SIDEBAR_DESK_ICONS.lab;
                const DIcon = cfg.Icon;
                const deskData = d as any;
                return (
                  <div key={d.id}
                    onClick={() => handleDeskClick(d.id)}
                    className="flex items-center gap-2.5 cursor-pointer rounded-lg px-2 transition-colors hover:bg-[var(--hover)]"
                    style={{ height: 34 }}>
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ background: d.status === 'busy' ? '#d97706' : 'var(--green)' }} />
                    <DIcon size={14} style={{ color: cfg.text }} className="shrink-0" />
                    <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--text)' }} className="truncate flex-1">
                      {deskData.agent_name || d.name}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function SidebarAction({ label, icon, color, onClick }: { label: string; icon: React.ReactNode; color: string; onClick?: () => void }) {
  return (
    <button onClick={onClick} className="w-full flex items-center gap-2 cursor-pointer transition-all hover:bg-[#f5f3ef]"
      style={{ padding: '7px 10px', borderRadius: 8, background: 'transparent', border: '1px solid #ece8e0', textAlign: 'left', fontSize: 11, fontWeight: 500, color: '#555' }}>
      <span style={{ color }}>{icon}</span>
      {label}
    </button>
  );
}

/* ═══════════════════════════════════════════
   v6.0 Intelligence Cards
   Morning brief, weekly report, security, cost-per-desk
   ═══════════════════════════════════════════ */

function IntelligenceCards({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const [brief, setBrief] = useState<any>(null);
  const [weekly, setWeekly] = useState<any>(null);
  const [security, setSecurity] = useState<any>(null);
  const [costPerDesk, setCostPerDesk] = useState<any>(null);
  const [generating, setGenerating] = useState(false);
  const [expandedCard, setExpandedCard] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    const [b, w, s, c] = await Promise.allSettled([
      fetch(`${API}/max/intelligence/brief`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/max/intelligence/weekly`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/max/security/stats`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/max/intelligence/cost-per-desk`).then(r => r.ok ? r.json() : null),
    ]);
    if (b.status === 'fulfilled') setBrief(b.value);
    if (w.status === 'fulfilled') setWeekly(w.value);
    if (s.status === 'fulfilled') setSecurity(s.value);
    if (c.status === 'fulfilled') setCostPerDesk(c.value);
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const generateBrief = async () => {
    setGenerating(true);
    try {
      const r = await fetch(`${API}/max/intelligence/brief/generate`, { method: 'POST' });
      if (r.ok) { setTimeout(fetchAll, 1000); }
    } catch { /* silent */ }
    setGenerating(false);
  };

  const toggleCard = (key: string) => setExpandedCard(expandedCard === key ? null : key);

  const briefDate = brief?.generated_at ? new Date(brief.generated_at).toLocaleDateString([], { month: 'short', day: 'numeric' }) : null;
  const weeklyDate = weekly?.generated_at ? new Date(weekly.generated_at).toLocaleDateString([], { month: 'short', day: 'numeric' }) : null;
  const desks = costPerDesk?.desks || [];
  const totalCost = costPerDesk?.total_cost_30d ?? desks.reduce((s: number, d: any) => s + (d.cost_usd || 0), 0);

  return (
    <div>
      <button onClick={onToggle} className="flex items-center justify-between w-full mb-2 cursor-pointer">
        <span className="section-label">Intelligence</span>
        <div className="flex items-center gap-2">
          {!collapsed && (
            <span onClick={(e) => { e.stopPropagation(); generateBrief(); }}
              className="text-[11px] text-[var(--gold)] font-semibold hover:underline cursor-pointer">
              {generating ? 'Generating...' : 'Refresh'}
            </span>
          )}
          {collapsed ? <ChevronDown size={12} className="text-[#ccc]" /> : <ChevronUp size={12} className="text-[#ccc]" />}
        </div>
      </button>

      {!collapsed && (
        <div className="flex flex-col gap-2">

          {/* Morning Brief */}
          <div className="empire-card" style={{ padding: '10px 12px', cursor: 'pointer' }} onClick={() => toggleCard('brief')}>
            <div className="flex items-center gap-2">
              <Sun size={14} style={{ color: '#d97706' }} />
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', flex: 1 }}>Morning Brief</span>
              {briefDate && <span style={{ fontSize: 9, color: 'var(--faint)', fontFamily: 'monospace' }}>{briefDate}</span>}
            </div>
            {expandedCard === 'brief' && brief && (
              <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {brief.sections ? (
                  Object.entries(brief.sections).map(([key, val]: [string, any]) => (
                    <div key={key} style={{ marginBottom: 6 }}>
                      <div style={{ fontSize: 9, fontWeight: 700, color: '#999', textTransform: 'uppercase' }}>{key.replace(/_/g, ' ')}</div>
                      <div style={{ fontSize: 10, color: '#555' }}>
                        {typeof val === 'string' ? val : typeof val === 'object' ? JSON.stringify(val, null, 1).slice(0, 200) : String(val)}
                      </div>
                    </div>
                  ))
                ) : brief.message ? (
                  <div style={{ fontSize: 10, color: '#555' }}>{String(brief.message).slice(0, 300)}</div>
                ) : (
                  <div style={{ fontSize: 10, color: '#999' }}>No brief data. Click Refresh to generate.</div>
                )}
              </div>
            )}
            {expandedCard !== 'brief' && brief?.sections && (
              <div style={{ fontSize: 10, color: 'var(--dim)', marginTop: 4 }}>
                {Object.keys(brief.sections).length} sections
              </div>
            )}
            {!brief && (
              <div style={{ fontSize: 10, color: 'var(--faint)', marginTop: 4 }}>Not generated yet</div>
            )}
          </div>

          {/* Weekly Report */}
          <div className="empire-card" style={{ padding: '10px 12px', cursor: 'pointer' }} onClick={() => toggleCard('weekly')}>
            <div className="flex items-center gap-2">
              <BarChart3 size={14} style={{ color: '#2563eb' }} />
              <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', flex: 1 }}>Weekly Report</span>
              {weeklyDate && <span style={{ fontSize: 9, color: 'var(--faint)', fontFamily: 'monospace' }}>{weeklyDate}</span>}
            </div>
            {expandedCard === 'weekly' && weekly && (
              <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {weekly.sections ? (
                  Object.entries(weekly.sections).slice(0, 4).map(([key, val]: [string, any]) => (
                    <div key={key} style={{ marginBottom: 6 }}>
                      <div style={{ fontSize: 9, fontWeight: 700, color: '#999', textTransform: 'uppercase' }}>{key.replace(/_/g, ' ')}</div>
                      <div style={{ fontSize: 10, color: '#555' }}>
                        {typeof val === 'string' ? val.slice(0, 150) : typeof val === 'object' ? JSON.stringify(val, null, 1).slice(0, 150) : String(val)}
                      </div>
                    </div>
                  ))
                ) : weekly.message ? (
                  <div style={{ fontSize: 10, color: '#555' }}>{String(weekly.message).slice(0, 300)}</div>
                ) : (
                  <div style={{ fontSize: 10, color: '#999' }}>No report data yet.</div>
                )}
              </div>
            )}
            {!weekly && (
              <div style={{ fontSize: 10, color: 'var(--faint)', marginTop: 4 }}>Next: Monday 8:00 AM</div>
            )}
          </div>

          {/* Security Stats */}
          {security && (
            <div className="empire-card" style={{ padding: '10px 12px', cursor: 'pointer' }} onClick={() => toggleCard('security')}>
              <div className="flex items-center gap-2">
                <Shield size={14} style={{ color: security.threats_blocked > 0 ? '#dc2626' : '#16a34a' }} />
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', flex: 1 }}>Security</span>
                <span style={{
                  fontSize: 9, fontWeight: 700, padding: '2px 8px', borderRadius: 9,
                  background: security.threats_blocked > 0 ? '#fef2f2' : '#f0fdf4',
                  color: security.threats_blocked > 0 ? '#dc2626' : '#16a34a',
                }}>
                  {security.threats_blocked > 0 ? `${security.threats_blocked} blocked` : 'Clear'}
                </span>
              </div>
              {expandedCard === 'security' && (
                <div className="grid grid-cols-2 gap-2 mt-2">
                  <MiniKPI label="Scanned" value={String(security.total_scanned || 0)} color="#2563eb" />
                  <MiniKPI label="Blocked" value={String(security.threats_blocked || 0)} color="#dc2626" />
                  <MiniKPI label="Sessions" value={String(security.active_sessions || 0)} color="#7c3aed" />
                  <MiniKPI label="Rate Limits" value={String(security.rate_limited || 0)} color="#d97706" />
                </div>
              )}
            </div>
          )}

          {/* Cost Per Desk */}
          {desks.length > 0 && (
            <div className="empire-card" style={{ padding: '10px 12px', cursor: 'pointer' }} onClick={() => toggleCard('costs')}>
              <div className="flex items-center gap-2">
                <DollarSign size={14} style={{ color: '#b8960c' }} />
                <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', flex: 1 }}>AI Costs (30d)</span>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#b8960c' }}>${totalCost.toFixed(2)}</span>
              </div>
              {expandedCard === 'costs' && (
                <div className="flex flex-col gap-1 mt-2">
                  {desks.filter((d: any) => d.cost_usd > 0).sort((a: any, b: any) => b.cost_usd - a.cost_usd).map((d: any) => (
                    <div key={d.desk} className="flex items-center justify-between" style={{ padding: '4px 8px', borderRadius: 6, background: '#faf9f7' }}>
                      <span style={{ fontSize: 10, fontWeight: 600, color: '#555', textTransform: 'capitalize' }}>{d.desk}</span>
                      <div className="flex items-center gap-2">
                        <span style={{ fontSize: 9, color: '#999' }}>{d.calls} calls</span>
                        <span style={{ fontSize: 10, fontWeight: 700, color: '#b8960c' }}>${d.cost_usd.toFixed(3)}</span>
                      </div>
                    </div>
                  ))}
                  {desks.filter((d: any) => d.cost_usd > 0).length === 0 && (
                    <div style={{ fontSize: 10, color: '#999', textAlign: 'center', padding: 4 }}>No desk costs recorded</div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
