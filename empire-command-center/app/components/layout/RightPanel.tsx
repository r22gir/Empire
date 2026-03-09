'use client';
import { useState, useEffect, useCallback } from 'react';
import { Desk, ScreenMode, EcosystemProduct } from '../../lib/types';
import { API } from '../../lib/api';
import {
  Plus, Check, X, Loader2, ChevronDown, ChevronUp, Package, AlertTriangle,
  DollarSign, Users, TrendingUp, ClipboardList, FileText, Flag, Calendar,
  Zap, Sparkles, Send, BookOpen, Camera, CheckCircle2, Eye, ArrowRight,
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
}

export default function RightPanel({ desks, briefing, systemStats, activeScreen, activeProduct, activeSection, onScreenChange, onModuleClick }: Props) {
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
    const [quotes, invoices, customers, inventory, tickets, costs] = await Promise.all([
      safeFetch(`${API}/quotes`),
      safeFetch(`${API}/finance/invoices?limit=1`),
      safeFetch(`${API}/crm/customers?limit=1`),
      safeFetch(`${API}/inventory/items?limit=1`),
      safeFetch(`${API}/tickets/?status=open&limit=1`),
      safeFetch(`${API}/costs/overview?days=30`),
    ]);
    stats.quotes = quotes ? `${(quotes.quotes || []).filter((q: any) => q.status !== 'accepted').length} open` : 'Offline';
    stats.invoices = invoices ? `${invoices.total ?? 0} total` : 'Offline';
    stats.crm = customers ? `${customers.total ?? 0} contacts` : 'Offline';
    stats.inventory = inventory ? `${inventory.total ?? 0} items` : 'Offline';
    stats.tickets = tickets ? `${tickets.total ?? 0} open` : 'Offline';
    stats.costs = costs?.today?.cost_usd ? `$${costs.today.cost_usd.toFixed(2)} today` : 'Token tracking';
    stats.shipping = '--';
    stats.reports = 'Weekly ready';
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
        { id: 'shipping', label: 'Shipping', stat: moduleStats.shipping || '--' },
        { id: 'costs', label: 'Costs', stat: moduleStats.costs || '...' },
      ];
    }
    if (activeProduct === 'craft') {
      return [
        { id: 'inventory', label: 'Materials', stat: moduleStats.inventory || '...' },
        { id: 'quotes', label: 'Orders', stat: moduleStats.quotes || '...' },
        { id: 'costs', label: 'Costs', stat: moduleStats.costs || '...' },
      ];
    }
    // Owner/global view
    return [
      { id: 'quotes', label: 'Quotes', stat: moduleStats.quotes || '...' },
      { id: 'invoices', label: 'Invoices', stat: moduleStats.invoices || '...' },
      { id: 'crm', label: 'CRM', stat: moduleStats.crm || '...' },
      { id: 'inventory', label: 'Inventory', stat: moduleStats.inventory || '...' },
      { id: 'tickets', label: 'Tickets', stat: moduleStats.tickets || '...' },
      { id: 'reports', label: 'Reports', stat: moduleStats.reports || '...' },
    ];
  };

  return (
    <aside className="w-[320px] bg-[var(--panel)] border-l border-[var(--border)] flex flex-col shrink-0 overflow-y-auto p-4 gap-3">

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
            {activeProduct === 'workroom' ? 'Workroom Modules' : activeProduct === 'craft' ? 'WoodCraft Modules' : 'Quick Access'}
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
      </div>
    );
  }

  return null;
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
