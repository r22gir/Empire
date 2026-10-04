'use client';
import React, { useState, useEffect, lazy, Suspense } from 'react';
import { API } from '../../lib/api';
import {
  Scissors, DollarSign, ClipboardList, TrendingUp, Calendar, Users, Inbox,
  Package, FileText, Receipt, BarChart3, Truck, Headphones, Loader2, Zap, Camera, Lightbulb, Eye, ArrowLeft, Plus,
  CheckCircle2, Circle, Clock, Flag, Filter, Search, Sparkles, Send, X, Check, CreditCard, Ruler, Trash2, Briefcase
} from 'lucide-react';
import QuoteActions from '../business/quotes/QuoteActions';
import QuickQuoteBuilder from '../business/quotes/QuickQuoteBuilder';
import { QuickQuotePanel, QuotePhasePipeline } from '../business/quotes/QuotePipeline';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';
import YardageCalculator from '../business/quotes/YardageCalculator';
import { HudStage, HudHeader, GaugeRow, RadialGauge, HexTile, MaxStrip, HudPanel, StatusPill, SectionLabel, BackButton, Fade, CountUp, fmtMoney, daysSince, type MaxSuggestion, type HudChip } from '../cyber/hud';

// Lazy-load business modules (they'll be created by the build agents)
const FinanceDashboard = lazy(() => import('../business/finance/FinanceDashboard'));
const InvoiceList = lazy(() => import('../business/finance/InvoiceList'));
const ExpenseTracker = lazy(() => import('../business/finance/ExpenseTracker'));
const CustomerList = lazy(() => import('../business/crm/CustomerList'));
const CustomerDetail = lazy(() => import('../business/crm/CustomerDetail'));
const JobBoard = lazy(() => import('../business/jobs/JobBoard'));
const PhotoAnalysisPanel = lazy(() => import('../business/vision/PhotoAnalysisPanel'));
const InventorySection = lazy(() => import('../business/inventory/InventorySection'));
const QuoteReviewScreen = lazy(() => import('./QuoteReviewScreen'));
const QuoteBuilderScreen = lazy(() => import('./QuoteBuilderScreen'));
const TemplateModule = lazy(() => import('../business/templates/TemplateModule'));
const JobHub = lazy(() => import('../jobhub/JobHub'));

const NAV_SECTIONS = [
  { id: 'overview', label: 'Overview', icon: Scissors },
  { id: 'jobhub', label: 'Job hub', icon: Briefcase },
  { id: 'creations', label: 'Creations', icon: Lightbulb },
  { id: 'quotes', label: 'Quotes', icon: ClipboardList },
  { id: 'finance', label: 'Finance', icon: DollarSign },
  { id: 'invoices', label: 'Invoices', icon: FileText },
  { id: 'expenses', label: 'Expenses', icon: Receipt },
  { id: 'customers', label: 'Customers', icon: Users },
  { id: 'inventory', label: 'Inventory', icon: Package },
  { id: 'jobs', label: 'Jobs', icon: Calendar },
  { id: 'templates', label: 'Templates', icon: Ruler },
  { id: 'tasks', label: 'Tasks', icon: CheckCircle2 },
  { id: 'analysis', label: 'AI Analysis', icon: Camera },
  { id: 'payments', label: 'Payments', icon: CreditCard },
  { id: 'docs', label: 'Docs', icon: FileText },
] as const;

type Section = typeof NAV_SECTIONS[number]['id'];

interface WorkroomPageProps {
  initialSection?: string;
}

export default function WorkroomPage({ initialSection }: WorkroomPageProps) {
  const openQuickQuote = initialSection === 'quick-quote';
  const [section, setSection] = useState<Section>(openQuickQuote ? 'quotes' : ((initialSection as Section) || 'overview'));
  const [quotes, setQuotes] = useState<any[]>([]);
  const [stats, setStats] = useState({ pipeline: 0, openQuotes: 0, accepted: 0 });
  const [selectedCustomer, setSelectedCustomer] = useState<string | null>(null);
  const [initialQuoteId, setInitialQuoteId] = useState<string | null>(null);
  // Bumped on every sidebar tab click so re-clicking Quotes remounts
  // QuotesSection and returns to the list instead of a stale detail view.
  const [navKey, setNavKey] = useState(0);

  // Sync section when initialSection prop changes (e.g. from module click)
  useEffect(() => {
    if (initialSection === 'quick-quote') setSection('quotes');
    else if (initialSection) setSection(initialSection as Section);
  }, [initialSection]);

  useEffect(() => {
    fetch(API + '/quotes-v2?limit=100&business_unit=workroom').then(r => r.json()).then(data => {
      const raw = data.quotes || data || [];
      const q = Array.isArray(raw) ? raw : [];
      setQuotes(q);
      setStats({
        pipeline: q.reduce((s: number, x: any) => s + (x.total || 0), 0),
        openQuotes: q.filter((x: any) => x.status !== 'accepted').length,
        accepted: q.filter((x: any) => x.status === 'accepted').length,
      });
    }).catch(() => {});
  }, []);

  const Loading = () => (
    <div className="flex-1 flex items-center justify-center py-20">
      <Loader2 size={24} className="text-[#16a34a] animate-spin" />
    </div>
  );

  const renderContent = () => {
    // Customer detail view
    if (selectedCustomer) {
      return (
        <Suspense fallback={<Loading />}>
          <CustomerDetail customerId={selectedCustomer} onBack={() => setSelectedCustomer(null)} />
        </Suspense>
      );
    }

    switch (section) {
      case 'finance':
        return <Suspense fallback={<Loading />}><FinanceDashboard onSelectCustomer={(id) => setSelectedCustomer(id)} /></Suspense>;
      case 'invoices':
        return <Suspense fallback={<Loading />}><InvoiceList /></Suspense>;
      case 'expenses':
        return <Suspense fallback={<Loading />}><ExpenseTracker /></Suspense>;
      case 'customers':
        return (
          <Suspense fallback={<Loading />}>
            <CustomerList onSelectCustomer={(id) => setSelectedCustomer(id)} business="workroom" />
          </Suspense>
        );
      case 'quotes':
        return <QuotesSection key={navKey} quotes={quotes} initialQuoteId={initialQuoteId} onClearInitial={() => setInitialQuoteId(null)} startQuickQuote={openQuickQuote} />;
      case 'inventory':
        return <Suspense fallback={<Loading />}><InventorySection /></Suspense>;
      case 'jobhub':
        return <Suspense fallback={<Loading />}><JobHub /></Suspense>;
      case 'jobs':
        return <Suspense fallback={<Loading />}><JobBoard /></Suspense>;
      case 'templates':
        return <Suspense fallback={<Loading />}><TemplateModule /></Suspense>;
      case 'tasks':
        return <TasksSection />;
      case 'analysis':
        return (
          <Suspense fallback={<Loading />}>
            <div style={{ maxWidth: 960, margin: '0 auto' }} className="px-4 sm:px-9 py-6">
              <div className="flex items-center gap-3 mb-5">
                <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }} className="flex items-center gap-2">
                  <Camera size={20} className="text-[#7c3aed]" /> AI Photo Analysis
                </h2>
              </div>
              <PhotoAnalysisPanel />
            </div>
          </Suspense>
        );
      case 'creations':
        return <CreationsSection />;
      case 'payments':
        return <PaymentModule product="workroom" />;
      case 'docs':
        return <div style={{ padding: 24 }}><ProductDocs product="workroom" /></div>;
      default:
        return <OverviewSection quotes={quotes} stats={stats} onNavigate={setSection} onSelectQuote={(id) => { setInitialQuoteId(id); setSection('quotes'); }} />;
    }
  };

  return (
    <div className="flex-1 flex flex-col sm:flex-row overflow-hidden">
      {/* Sidebar nav — angular neon tabs */}
      <nav className="cy-subnav sm:w-[200px] w-full sm:border-r border-b sm:border-b-0" style={{ flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
        <div className="cy-subnav-brand">
          <span className="cy-plate-ico" style={{ width: 34, height: 34 }}><Scissors size={16} /></span>
          <div>
            <b>Workroom</b>
            <small>Drapery & Upholstery</small>
          </div>
        </div>
        <div className="cy-subnav-list flex-1 overflow-x-auto sm:overflow-x-hidden overflow-y-auto">
          <div className="flex sm:flex-col flex-row gap-1.5 sm:flex-nowrap flex-nowrap sm:w-auto w-max">
            <a href="/workroom/capture" className="cy-tab is-alert-soft" style={{ textDecoration: 'none' }}>
              <span className="cy-tab-ico" style={{ color: 'var(--cy-teal)' }}><Inbox size={15} /></span>
              <span className="cy-tab-label">Inbox capture</span>
            </a>
            {NAV_SECTIONS.map((nav, ni) => {
              const Icon = nav.icon;
              const isActive = section === nav.id && !selectedCustomer;
              return (
                <button key={nav.id}
                  onClick={() => { setSection(nav.id); setSelectedCustomer(null); setNavKey(k => k + 1); }}
                  className={`cy-tab${isActive ? ' is-active' : ''}`}
                  aria-current={isActive ? 'page' : undefined}
                >
                  <span className="cy-tab-ico"><Icon size={15} /></span>
                  <span className="cy-tab-label">{nav.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Main content */}
      <div className="cy-module-scroll flex-1 overflow-y-auto">
        {renderContent()}
      </div>
    </div>
  );
}

// -- Overview Section --

function OverviewSection({ quotes, stats, onNavigate, onSelectQuote }: { quotes: any[]; stats: any; onNavigate: (s: Section) => void; onSelectQuote?: (id: string) => void }) {
  const [customers, setCustomers] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [finance, setFinance] = useState<any>(null);
  const [inventory, setInventory] = useState<any>(null);

  useEffect(() => {
    // Fetch real data for dashboard
    fetch(`${API}/crm/customers?limit=5&sort_by=updated_at&sort_dir=desc&business=workroom`).then(r => r.json()).then(d => setCustomers(d.customers || [])).catch(() => {});
    fetch(`${API}/jobs/?business=workroom`).then(r => r.json()).then(d => setJobs(Array.isArray(d) ? d : d.jobs || [])).catch(() => {});
    fetch(`${API}/finance/dashboard?range=this_month&business=workroom`).then(r => r.json()).then(d => setFinance(d)).catch(() => {});
    fetch(`${API}/inventory/dashboard?business=workroom`).then(r => r.json()).then(d => setInventory(d)).catch(() => {});
  }, []);

  const activeJobs = jobs.filter(j => j.status !== 'completed' && j.status !== 'cancelled');
  const completedJobs = jobs.filter(j => j.status === 'completed');
  const overdueJobs = jobs.filter(j => j.due_date && new Date(j.due_date) < new Date() && j.status !== 'completed');

  // Job stage counts for at-a-glance
  const stageCounts = {
    pending: jobs.filter(j => j.status === 'pending').length,
    scheduled: jobs.filter(j => j.status === 'scheduled').length,
    in_progress: jobs.filter(j => j.status === 'in_progress').length,
    completed: completedJobs.length,
  };

  // Build activity feed from quotes + jobs
  const activities: { text: string; time: string; color: string; icon: React.ReactNode; open: () => void; label: string }[] = [];
  quotes.slice(0, 5).forEach(q => {
    activities.push({
      text: `Quote ${q.quote_number || 'Q'} ${q.status === 'accepted' ? 'accepted by' : q.status === 'sent' ? 'sent to' : 'created for'} ${q.customer_name || 'Customer'} — $${(q.total || 0).toLocaleString()}`,
      time: q.created_at || q.updated_at || '',
      color: q.status === 'accepted' ? '#16a34a' : q.status === 'sent' ? '#2563eb' : '#b8960c',
      icon: <ClipboardList size={14} />,
      open: () => onSelectQuote?.(q.id), label: `Open quote ${q.quote_number || ''}`,
    });
  });
  jobs.slice(0, 3).forEach(j => {
    activities.push({
      text: `Job "${j.title}" ${j.status === 'completed' ? 'completed' : j.status === 'in_progress' ? 'in progress' : 'created'} — ${j.customer_name || 'Customer'}`,
      time: j.updated_at || j.created_at || '',
      color: j.status === 'completed' ? '#16a34a' : j.status === 'in_progress' ? '#d97706' : '#777',
      icon: <Calendar size={14} />,
      open: () => (j.quote_id ? onSelectQuote?.(j.quote_id) : onNavigate('jobs')), label: j.quote_id ? `Open the quote for ${j.title || 'this job'}` : `Open job board for ${j.title || 'this job'}`,
    });
  });
  activities.sort((a, b) => (b.time || '').localeCompare(a.time || ''));

  const revenue = finance?.revenue?.amount || stats.pipeline || 0;
  const customerCount = finance?.customers?.total || customers.length || 0;
  const acceptedValue = quotes.filter(q => q.status === 'accepted').reduce((t, q) => t + (q.total || 0), 0);
  const drafts = quotes.filter(q => q.status === 'draft');
  const staleSent = quotes
    .filter(q => q.status === 'sent' && (daysSince(q.updated_at || q.created_at) ?? 0) >= 7)
    .sort((a, b) => (a.updated_at || a.created_at || '').localeCompare(b.updated_at || b.created_at || ''));
  const lowStock = Number(inventory?.low_stock_count || 0);
  const loaded = quotes.length > 0 || jobs.length > 0;

  const chips: HudChip[] = [
    { label: 'Live data', tone: 'teal', live: true },
    { label: `${quotes.length} quotes loaded`, tone: 'cyan' },
    overdueJobs.length > 0 ? { label: `${overdueJobs.length} jobs overdue`, tone: 'mag', live: true } : { label: 'Jobs on track', tone: 'teal' },
    lowStock > 0 ? { label: `${lowStock} low stock`, tone: 'amber' } : { label: 'Stock OK', tone: 'muted' },
  ];

  const sugg: MaxSuggestion[] = [];
  if (staleSent.length > 0) {
    const q = staleSent[0];
    sugg.push({ id: 'stale', tone: 'mag', title: 'Quote follow-up', actionLabel: 'Open quote', onAction: () => onSelectQuote?.(q.id),
      text: `${staleSent.length} sent quote${staleSent.length > 1 ? 's' : ''} with no reply in 7+ days. Oldest: ${q.quote_number || 'quote'} · ${q.customer_name || 'customer'} · ${fmtMoney(q.total || 0)}.`,
      source: 'quotes-v2 · status sent' });
  }
  if (drafts.length > 0) {
    sugg.push({ id: 'drafts', tone: 'cyan', title: 'Drafts ready to review', actionLabel: 'Review drafts', onAction: () => onNavigate('quotes'),
      text: `${drafts.length} draft quote${drafts.length > 1 ? 's' : ''} worth ${fmtMoney(drafts.reduce((t, q) => t + (q.total || 0), 0))} waiting to be approved and sent.`,
      source: 'quotes-v2 · status draft' });
  }
  if (overdueJobs.length > 0) {
    sugg.push({ id: 'jobs', tone: 'amber', title: 'Overdue jobs', actionLabel: 'Open job board', onAction: () => onNavigate('jobs'),
      text: `${overdueJobs.length} job${overdueJobs.length > 1 ? 's are' : ' is'} past due: ${overdueJobs.slice(0, 2).map(j => j.title).join(', ')}.`, source: 'jobs · due_date' });
  }
  if (lowStock > 0) {
    sugg.push({ id: 'stock', tone: 'amber', title: 'Reorder fabric', actionLabel: 'Open inventory', onAction: () => onNavigate('inventory'),
      text: `${lowStock} inventory item${lowStock > 1 ? 's are' : ' is'} below reorder level.`, source: 'inventory/dashboard' });
  }

  const stageTiles = [
    { label: 'Pending', count: stageCounts.pending, tone: 'muted' as const },
    { label: 'Scheduled', count: stageCounts.scheduled, tone: 'blue' as const },
    { label: 'In progress', count: stageCounts.in_progress, tone: 'amber' as const },
    { label: 'Completed', count: stageCounts.completed, tone: 'teal' as const },
  ];

  return (
    <HudStage>
      <HudHeader
        icon={<Scissors size={20} />}
        title="Empire Workroom"
        subtitle={<span suppressHydrationWarning>Custom drapery & upholstery · {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}</span>}
        chips={chips}
        actions={<>
          <button type="button" className="cy-btn is-primary" onClick={() => onNavigate('quotes')}><Plus size={14} /> New Quote</button>
          <button type="button" className="cy-btn" onClick={() => onNavigate('customers')}><Users size={14} /> New Customer</button>
          <button type="button" className="cy-btn" onClick={() => onNavigate('jobs')}><Calendar size={14} /> New Job</button>
          <button type="button" className="cy-btn" onClick={() => onNavigate('invoices')}><FileText size={14} /> Send Invoice</button>
        </>}
      />

      <GaugeRow>
        <RadialGauge i={0} label="Revenue pipeline" value={revenue} format={n => fmtMoney(n)} tone="cyan"
          fraction={stats.pipeline > 0 ? acceptedValue / stats.pipeline : null} ringLabel={stats.pipeline > 0 ? `${Math.round((acceptedValue / stats.pipeline) * 100)}%` : undefined}
          sub={`${quotes.length} quotes total · ring = share accepted`} onClick={() => onNavigate('quotes')} icon={<DollarSign size={20} />} />
        <RadialGauge i={1} label="Active jobs" value={activeJobs.length} tone={overdueJobs.length > 0 ? 'mag' : 'teal'}
          fraction={jobs.length > 0 ? activeJobs.length / jobs.length : null}
          sub={overdueJobs.length > 0 ? `${overdueJobs.length} overdue · of ${jobs.length} jobs` : `On track · of ${jobs.length} jobs`} onClick={() => onNavigate('jobs')} icon={<Calendar size={20} />} />
        <RadialGauge i={2} label="Open quotes" value={stats.openQuotes} tone="amber"
          fraction={quotes.length > 0 ? stats.openQuotes / quotes.length : null}
          sub={`${fmtMoney(stats.pipeline)} value`} onClick={() => onNavigate('quotes')} icon={<ClipboardList size={20} />} />
        <RadialGauge i={3} label="Customers" value={customerCount} tone="violet" fraction={null}
          sub={`${customers.length} recently active`} onClick={() => onNavigate('customers')} icon={<Users size={20} />} />
      </GaugeRow>

      <MaxStrip items={sugg} loading={!loaded} empty="All clear — no stale quotes, overdue jobs or low stock." />

      {jobs.length > 0 && (
        <Fade i={3} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <SectionLabel>Jobs at a glance</SectionLabel>
          <div className="cy-hexrow">
            {stageTiles.map(st => <HexTile key={st.label} label={st.label} value={st.count} tone={st.tone} onClick={() => onNavigate('jobs')} />)}
            {overdueJobs.length > 0 && <HexTile label="Overdue" value={overdueJobs.length} tone="mag" onClick={() => onNavigate('jobs')} />}
          </div>
        </Fade>
      )}

      <div className="cy-grid2">
        <HudPanel i={4} title="Recent activity" icon={<TrendingUp size={14} />} style={{ minHeight: 280 }}>
          <div className="cy-list">
            {activities.slice(0, 6).map((a, i) => (
              <button type="button" key={i} className="cy-row" onClick={a.open} aria-label={a.label} title={a.label}>
                <span className="cy-row-ico" style={{ color: a.color }}>{a.icon}</span>
                <div className="cy-row-main">
                  <div className="cy-row-title" style={{ whiteSpace: 'normal' }}>{a.text}</div>
                  {a.time && <div className="cy-row-sub" suppressHydrationWarning>{new Date(a.time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</div>}
                </div>
              </button>
            ))}
            {activities.length === 0 && <div className="cy-nodata">SIN DATOS · NO DATA<span>No recent quote or job activity</span></div>}
          </div>
        </HudPanel>

        <HudPanel i={5} title="Recent quotes" icon={<ClipboardList size={14} />} style={{ minHeight: 280 }}
          actions={<button type="button" className="cy-btn is-sm" onClick={() => onNavigate('quotes')}>All quotes →</button>}>
          <div className="cy-list">
            {quotes.slice(0, 6).map((q, i) => (
              <button type="button" key={i} onClick={() => onSelectQuote?.(q.id)} className="cy-row">
                <div className="cy-row-main">
                  <div className="cy-row-title cy-mono">{q.quote_number || `Q-${i + 1}`}</div>
                  <div className="cy-row-sub">{q.customer_name || 'Customer'}</div>
                </div>
                <div className="cy-row-end">
                  <span className="cy-money">{fmtMoney(q.total || 0, (q.total || 0) % 1 !== 0)}</span>
                  <StatusPill status={q.status} />
                </div>
              </button>
            ))}
            {quotes.length === 0 && <div className="cy-nodata">SIN DATOS · NO DATA<span>No quotes yet</span></div>}
          </div>
        </HudPanel>
      </div>

      <div className="cy-grid2">
        <HudPanel i={6} title="Inventory" icon={<Package size={14} />}>
          <div className="cy-hexrow" style={{ justifyContent: 'space-around', marginBottom: 10 }}>
            <HexTile label="Items" value={inventory ? Number(inventory.total_items || 0) : null} tone="teal" onClick={() => onNavigate('inventory')} />
            <HexTile label="Low stock" value={inventory ? lowStock : null} tone={lowStock > 0 ? 'amber' : 'muted'} onClick={() => onNavigate('inventory')} />
            <div className="cy-hex t-cyan" role="button" tabIndex={0} style={{ cursor: 'pointer' }} onClick={() => onNavigate('inventory')} onKeyDown={e => { if (e.key === 'Enter') onNavigate('inventory'); }}><b style={{ fontSize: 15 }}>{inventory ? <CountUp value={Number(inventory.total_value || 0)} format={n => fmtMoney(n)} /> : '—'}</b><span>Value</span></div>
          </div>
          <button type="button" className={`cy-btn${lowStock > 0 ? ' is-pulse' : ''}`} style={{ width: '100%' }} onClick={() => onNavigate('inventory')}>
            {lowStock > 0 ? `${lowStock} items need reorder` : 'View all inventory'}
          </button>
        </HudPanel>

        <HudPanel i={7} title="Business summary" icon={<BarChart3 size={14} />}>
          <div className="cy-kvlist">
            <div className="cy-kv" style={{ ['--g' as any]: '#00e5ff' }}>Total pipeline <b><CountUp value={stats.pipeline} format={n => fmtMoney(n)} /></b></div>
            <div className="cy-kv" style={{ ['--g' as any]: '#ffc857' }}>Open quotes <b><CountUp value={stats.openQuotes} /></b></div>
            <div className="cy-kv" style={{ ['--g' as any]: '#14f1c6' }}>Accepted quotes <b><CountUp value={stats.accepted} /></b></div>
            <div className="cy-kv" style={{ ['--g' as any]: '#5cc8ff' }}>Active jobs <b><CountUp value={activeJobs.length} /></b></div>
          </div>
          <button type="button" className="cy-btn" style={{ width: '100%', marginTop: 12 }} onClick={() => onNavigate('finance')}>View full financial dashboard</button>
        </HudPanel>
      </div>
    </HudStage>
  );
}

// -- Quotes Section --

const QUOTES_PAGE_SIZE = 100;

function QuotesSection({ quotes: initialQuotes, initialQuoteId, onClearInitial, startQuickQuote }: { quotes: any[]; initialQuoteId?: string | null; onClearInitial?: () => void; startQuickQuote?: boolean }) {
  const [business, setBusiness] = useState<'workroom' | 'woodcraft'>(() => {
    if (typeof window === 'undefined') return 'workroom';
    return new URLSearchParams(window.location.search).get('business') === 'woodcraft' ? 'woodcraft' : 'workroom';
  });
  const [quotes, setQuotes] = useState(() => (
    typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('business') === 'woodcraft'
      ? []
      : initialQuotes
  ));
  // Backend caps limit at quote_service.MAX_LIST_QUOTES_LIMIT (500); older
  // quotes past the first page (e.g. EST-2026-007, EST-2026-291) are
  // reached via "Load more" using `total` from the list response.
  const [totalQuotes, setTotalQuotes] = useState<number | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [showQuickQuote, setShowQuickQuote] = useState(!!startQuickQuote);
  const [showQuickCalc, setShowQuickCalc] = useState(false);
  const [pipelineQuoteId, setPipelineQuoteId] = useState<string | null>(null);
  const [analyzingQuoteId, setAnalyzingQuoteId] = useState<string | null>(null);
  const [viewingQuoteId, setViewingQuoteId] = useState<string | null>(initialQuoteId || null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [showBuilder, setShowBuilder] = useState(false);
  const [builderQuoteId, setBuilderQuoteId] = useState<string | null>(null);

  useEffect(() => {
    fetch(API + `/quotes-v2?limit=${QUOTES_PAGE_SIZE}&offset=0&business_unit=${business}`).then(r => r.json()).then(data => {
      const raw = data.quotes || data || [];
      setQuotes(Array.isArray(raw) ? raw : []);
      setTotalQuotes(typeof data.total === 'number' ? data.total : null);
    }).catch(() => {});
  }, [business]);
  useEffect(() => { if (startQuickQuote) setShowQuickQuote(true); }, [startQuickQuote]);

  const loadMoreQuotes = () => {
    setLoadingMore(true);
    fetch(API + `/quotes-v2?limit=${QUOTES_PAGE_SIZE}&offset=${quotes.length}&business_unit=${business}`)
      .then(r => r.json())
      .then(data => {
        const raw = data.quotes || data || [];
        setQuotes(prev => [...prev, ...(Array.isArray(raw) ? raw : [])]);
        setTotalQuotes(typeof data.total === 'number' ? data.total : null);
      })
      .catch(() => {})
      .finally(() => setLoadingMore(false));
  };

  const filtered = quotes.filter(q => {
    if (filter !== 'all' && q.status !== filter) return false;
    if (search && !((q.customer_name || '').toLowerCase().includes(search.toLowerCase()) ||
                    (q.quote_number || '').toLowerCase().includes(search.toLowerCase()) ||
                    (q.intake_code || '').toLowerCase().includes(search.toLowerCase()))) return false;
    return true;
  });

  const refetchQuotes = () => {
    fetch(API + `/quotes-v2?limit=${QUOTES_PAGE_SIZE}&offset=0&business_unit=${business}`).then(r => r.json()).then(data => {
      const raw = data.quotes || data || [];
      setQuotes(Array.isArray(raw) ? raw : []);
      setTotalQuotes(typeof data.total === 'number' ? data.total : null);
    }).catch(() => {});
  };

  const toggleSelect = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === filtered.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(filtered.map(q => q.id)));
    }
  };

  const bulkDelete = async () => {
    if (selected.size === 0) return;
    if (!confirm(`Delete ${selected.size} quote${selected.size > 1 ? 's' : ''}? This cannot be undone.`)) return;
    setDeleting(true);
    for (const id of selected) {
      try {
        await fetch(`${API}/quotes-v2/${id}`, { method: 'DELETE' });
      } catch { /* skip failed */ }
    }
    setSelected(new Set());
    setDeleting(false);
    refetchQuotes();
  };

  // Auto-open quote from external navigation
  useEffect(() => {
    if (initialQuoteId) {
      setViewingQuoteId(initialQuoteId);
      onClearInitial?.();
    }
  }, [initialQuoteId]);

  const filters = ['all', 'draft', 'sent', 'accepted', 'proposal'];

  // QuoteBuilder view
  if (showBuilder) {
    return (
      <Suspense fallback={<div className="flex items-center justify-center py-20"><Loader2 size={24} className="text-[#b8960c] animate-spin" /></div>}>
        <QuoteBuilderScreen onBack={() => { setShowBuilder(false); setBuilderQuoteId(null); }} editQuoteId={builderQuoteId || undefined} />
      </Suspense>
    );
  }

  // Viewing a specific quote — show full review
  if (viewingQuoteId) {
    return (
      <HudStage wide>
        <div><BackButton onClick={() => setViewingQuoteId(null)}>Back to Quotes</BackButton></div>
        <Suspense fallback={<div className="cy-nodata">LOADING QUOTE…</div>}>
          <QuoteReviewScreen quoteId={viewingQuoteId} onOpenBuilder={() => { setBuilderQuoteId(viewingQuoteId); setViewingQuoteId(null); setShowBuilder(true); }} />
        </Suspense>
      </HudStage>
    );
  }

  const countOf = (st: string) => quotes.filter(q => q.status === st).length;
  const pipelineValue = quotes.reduce((t, q) => t + (q.total || 0), 0);
  const draftCount = countOf('draft');
  const sentCount = countOf('sent');
  const acceptedCount = countOf('accepted');
  const decided = acceptedCount + countOf('rejected') + countOf('declined');
  const staleSent = quotes
    .filter(q => q.status === 'sent' && (daysSince(q.updated_at || q.created_at) ?? 0) >= 7)
    .sort((x, y) => (x.updated_at || x.created_at || '').localeCompare(y.updated_at || y.created_at || ''));
  const loadedOf = totalQuotes !== null && totalQuotes > quotes.length ? ` of ${quotes.length} loaded` : '';
  const qChips: HudChip[] = [
    { label: 'Live', tone: 'teal', live: true },
    { label: business === 'workroom' ? 'Workroom' : 'WoodCraft', tone: 'cyan' },
    { label: `${totalQuotes ?? quotes.length} total`, tone: 'muted' },
    ...(filter !== 'all' || search ? [{ label: `${filtered.length} shown`, tone: 'violet' as const }] : []),
    ...(selected.size > 0 ? [{ label: `${selected.size} selected`, tone: 'mag' as const, live: true }] : []),
  ];
  const qSugg: MaxSuggestion[] = [];
  if (staleSent.length > 0) {
    const q = staleSent[0];
    qSugg.push({ id: 'stale', tone: 'mag', title: 'Chase silent quotes', actionLabel: `Open ${q.quote_number || 'quote'}`, onAction: () => setViewingQuoteId(q.id),
      text: `${staleSent.length} sent quote${staleSent.length > 1 ? 's' : ''} with no reply for 7+ days. Oldest: ${q.customer_name || 'customer'} · ${fmtMoney(q.total || 0)} · ${daysSince(q.updated_at || q.created_at)}d.`,
      source: 'status sent · last update' });
  }
  if (draftCount > 0) {
    const dv = quotes.filter(q => q.status === 'draft').reduce((t, q) => t + (q.total || 0), 0);
    qSugg.push({ id: 'drafts', tone: 'cyan', title: 'Send your drafts', actionLabel: 'Show drafts', onAction: () => setFilter('draft'),
      text: `${draftCount} draft${draftCount > 1 ? 's' : ''} worth ${fmtMoney(dv)} not sent yet${loadedOf}.`, source: 'status draft' });
  }
  if (acceptedCount > 0) {
    qSugg.push({ id: 'acc', tone: 'teal', title: 'Turn wins into invoices', actionLabel: 'Show accepted', onAction: () => setFilter('accepted'),
      text: `${acceptedCount} accepted quote${acceptedCount > 1 ? 's' : ''}${loadedOf}. Check that each one has a deposit invoice.`, source: 'status accepted' });
  }

  return (
    <HudStage wide>
      <HudHeader
        icon={<ClipboardList size={20} />}
        title="Quotes"
        subtitle="Estimates · approvals · pipeline"
        chips={qChips}
        actions={<>
          <div className="cy-seg" role="group" aria-label="Business">
            {(['workroom', 'woodcraft'] as const).map(key => (
              <button key={key} type="button" onClick={() => setBusiness(key)} className={`cy-btn is-sm${business === key ? ' is-active' : ''}`} aria-pressed={business === key}>
                {key === 'workroom' ? 'Workroom' : 'WoodCraft'}
              </button>
            ))}
          </div>
          <button type="button" onClick={() => setShowBuilder(true)} className="cy-btn is-primary"><Plus size={14} /> New Quote</button>
          <button type="button" onClick={() => setShowQuickQuote(!showQuickQuote)} className={`cy-btn${showQuickQuote ? ' is-active' : ''}`}><Zap size={14} /> Quick Quote</button>
          <button type="button" onClick={() => setShowQuickCalc(!showQuickCalc)} className={`cy-btn is-teal${showQuickCalc ? ' is-active' : ''}`}><Ruler size={14} /> Yardage Calc</button>
        </>}
      />

      <GaugeRow>
        <RadialGauge i={0} label="Total quotes" value={totalQuotes ?? quotes.length} tone="cyan" fraction={null} icon={<ClipboardList size={20} />}
          sub={totalQuotes !== null && totalQuotes > quotes.length ? `${quotes.length} loaded` : 'all loaded'} onClick={() => setFilter('all')} />
        <RadialGauge i={1} label="Pipeline value" value={pipelineValue} format={n => fmtMoney(n)} tone="teal" fraction={null} icon={<DollarSign size={20} />}
          sub={`sum of ${quotes.length} loaded`} />
        <RadialGauge i={2} label="Drafts" value={draftCount} tone="muted" fraction={quotes.length ? draftCount / quotes.length : null}
          sub="not sent yet" onClick={() => setFilter('draft')} />
        <RadialGauge i={3} label="Awaiting reply" value={sentCount} tone={staleSent.length > 0 ? 'mag' : 'blue'} fraction={quotes.length ? sentCount / quotes.length : null}
          sub={staleSent.length > 0 ? `${staleSent.length} silent 7d+` : 'sent'} onClick={() => setFilter('sent')} />
        <RadialGauge i={4} label="Accepted" value={acceptedCount} tone="teal" fraction={decided > 0 ? acceptedCount / decided : null}
          ringLabel={decided > 0 ? `${Math.round((acceptedCount / decided) * 100)}%` : undefined}
          sub={decided > 0 ? 'win rate of decided' : 'no decisions yet'} onClick={() => setFilter('accepted')} icon={<CheckCircle2 size={20} />} />
      </GaugeRow>

      <MaxStrip items={qSugg} loading={quotes.length === 0 && totalQuotes === null} empty="No stale or unsent quotes in the loaded list." />

      {/* Quick Quote Builder (photo-based) */}
      {showQuickQuote && (
        <Fade className="cy-tool-host"><QuickQuoteBuilder onClose={() => setShowQuickQuote(false)} /></Fade>
      )}

      {/* Yardage Calculator (the $199/mo feature) */}
      {showQuickCalc && (
        <Fade className="cy-tool-host"><YardageCalculator onClose={() => setShowQuickCalc(false)} /></Fade>
      )}

      {/* Phase Pipeline (when a quote is selected for pipeline review) */}
      {pipelineQuoteId && (
        <HudPanel i={0} title="Phase pipeline" icon={<TrendingUp size={14} />}
          actions={<button type="button" onClick={() => setPipelineQuoteId(null)} className="cy-btn is-sm"><X size={12} /> Close</button>}>
          <div className="cy-tool-host"><QuotePhasePipeline quoteId={pipelineQuoteId} /></div>
        </HudPanel>
      )}

      <HudPanel i={3} title={<>Quote register <span className="cy-mono" style={{ color: 'var(--cy-faint)', fontSize: 10 }}>[{filtered.length}]</span></>} icon={<ClipboardList size={14} />}
        actions={
          <div className="cy-tablebar">
            <label className="cy-search">
              <Search size={13} aria-hidden />
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search customer, quote #, intake…" aria-label="Search quotes" className="cy-input" />
            </label>
          </div>
        }>
        {/* Filter tabs + bulk actions */}
        <div className="cy-filterbar">
          {filters.map(f => (
            <button key={f} type="button" onClick={() => setFilter(f)} className={`cy-btn is-sm${filter === f ? ' is-active' : ''}`} aria-pressed={filter === f}>
              {f === 'all' ? 'All status' : f.charAt(0).toUpperCase() + f.slice(1)}
              <span className="cy-mono cy-count">{f === 'all' ? quotes.length : countOf(f)}</span>
            </button>
          ))}
          {selected.size > 0 && (
            <button type="button" onClick={bulkDelete} disabled={deleting} className="cy-btn is-danger" style={{ marginLeft: 'auto' }}>
              {deleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
              Delete {selected.size} selected
            </button>
          )}
        </div>

        <div className="cy-tablewrap">
        <table className="cy-hudtable is-cards-sm">
          <thead>
            <tr>
              <th style={{ width: 36 }}>
                <input type="checkbox" aria-label="Select all quotes"
                  checked={filtered.length > 0 && selected.size === filtered.length}
                  onChange={toggleSelectAll} className="cy-check" />
              </th>
              <th>Quote #</th>
              <th>Customer</th>
              <th className="is-num">Total</th>
              <th>Status</th>
              <th>Date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((q, i) => (
              <React.Fragment key={i}>
                <tr className={`cy-trow${selected.has(q.id) ? ' is-selected' : ''}`} onClick={() => setViewingQuoteId(q.id)}>
                  <td onClick={e => e.stopPropagation()}>
                    <input type="checkbox" aria-label={`Select ${q.quote_number || 'quote'}`} checked={selected.has(q.id)} onChange={() => toggleSelect(q.id)} className="cy-check" />
                  </td>
                  <td className="is-id">{q.quote_number || `Q-${i + 1}`}</td>
                  <td className="is-cust">
                    {q.customer_name || '--'}
                    {q.intake_code && <span className="cy-spill t-violet" style={{ marginLeft: 6 }}>{q.intake_code}</span>}
                  </td>
                  <td className="is-num cy-money">{fmtMoney(q.total || 0, (q.total || 0) % 1 !== 0)}</td>
                  <td><StatusPill status={q.status} /></td>
                  <td className="is-date" suppressHydrationWarning>
                    {q.created_at ? new Date(q.created_at).toLocaleDateString() : '--'}
                  </td>
                  <td>
                    <div className="cy-rowactions">
                      <button type="button" onClick={() => setViewingQuoteId(q.id)} title="View Quote" aria-label="View quote" className="cy-btn cy-iconbtn">
                        <Eye size={14} />
                      </button>
                      <QuoteActions quoteId={q.id} status={q.status || 'draft'} compact onAction={(action) => { if (action === 'delete') refetchQuotes(); }} />
                      <button type="button" onClick={(e) => { e.stopPropagation(); setPipelineQuoteId(pipelineQuoteId === q.id ? null : q.id); }}
                        title="Phase Pipeline" aria-label="Phase pipeline" className={`cy-btn cy-iconbtn is-teal${pipelineQuoteId === q.id ? ' is-active' : ''}`}>
                        <TrendingUp size={14} />
                      </button>
                      <button type="button" onClick={(e) => { e.stopPropagation(); setAnalyzingQuoteId(analyzingQuoteId === q.id ? null : q.id); }}
                        title="AI Photo Analysis" aria-label="AI photo analysis" className={`cy-btn cy-iconbtn is-violet${analyzingQuoteId === q.id ? ' is-active' : ''}`}>
                        <Camera size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
                {analyzingQuoteId === q.id && (
                  <tr className="cy-trow-detail">
                    <td colSpan={7} style={{ padding: 0 }}>
                      <div className="cy-tool-host" style={{ padding: '16px 20px' }}>
                        <Suspense fallback={<div className="cy-nodata">LOADING ANALYSIS…</div>}>
                          <PhotoAnalysisPanel compact onAnalysisComplete={(type: string, data: any) => {
                            void(type); void(data); // Analysis complete for quote
                          }} />
                        </Suspense>
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
        </div>
        {filtered.length === 0 && (
          <div className="cy-nodata">SIN DATOS · NO DATA<span>No quotes match this view</span></div>
        )}
        {totalQuotes !== null && quotes.length < totalQuotes && (
          <div style={{ textAlign: 'center', padding: '16px 0 4px' }}>
            <button type="button" onClick={loadMoreQuotes} disabled={loadingMore} className="cy-btn">
              {loadingMore ? 'Loading…' : <>Load more <span className="cy-mono">({quotes.length} of {totalQuotes})</span></>}
            </button>
          </div>
        )}
      </HudPanel>
    </HudStage>
  );
}

// -- Tasks Section --

const TASK_DESKS = [
  { id: '', label: 'All Desks' },
  { id: 'forge', label: 'Forge (Workroom)' },
  { id: 'sales', label: 'Sales' },
  { id: 'support', label: 'Support' },
  { id: 'marketing', label: 'Marketing' },
  { id: 'finance', label: 'Finance' },
  { id: 'it', label: 'IT' },
  { id: 'lab', label: 'Lab (R&D)' },
  { id: 'contractors', label: 'Contractors' },
];

const PRIORITY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  urgent: { bg: '#fef2f2', text: '#dc2626', border: '#fecaca' },
  high: { bg: '#fff7ed', text: '#d97706', border: '#fed7aa' },
  normal: { bg: '#fdf8eb', text: '#b8960c', border: '#f5ecd0' },
  low: { bg: '#f9fafb', text: '#6b7280', border: '#e5e7eb' },
};

function TasksSection() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'pending' | 'done'>('all');
  const [deskFilter, setDeskFilter] = useState('');
  const [search, setSearch] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newPriority, setNewPriority] = useState('normal');
  const [newDesk, setNewDesk] = useState('');
  const [newDue, setNewDue] = useState('');
  const [saving, setSaving] = useState(false);
  const [viewingTask, setViewingTask] = useState<any>(null);

  const fetchTasks = async () => {
    try {
      const res = await fetch(`${API}/tasks/?limit=50&business=workroom`);
      if (res.ok) {
        const data = await res.json();
        setTasks(data.tasks || data || []);
      }
    } catch { /* */ }
    setLoading(false);
  };

  useEffect(() => { fetchTasks(); }, []);

  const toggleTask = async (task: any) => {
    const newStatus = task.status === 'done' ? 'todo' : 'done';
    try {
      const res = await fetch(`${API}/tasks/${task.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        setTasks(prev => prev.map(t => t.id === task.id ? { ...t, status: newStatus } : t));
      }
    } catch { /* */ }
  };

  const fetchTaskDetail = async (taskId: string) => {
    try {
      const res = await fetch(`${API}/tasks/${taskId}`);
      if (res.ok) {
        const data = await res.json();
        setViewingTask(data.task || data);
      }
    } catch { /* */ }
  };

  const addTask = async () => {
    if (!newTitle.trim()) return;
    setSaving(true);
    try {
      const body: any = { title: newTitle.trim(), priority: newPriority, business: 'workroom' };
      if (newDesc.trim()) body.description = newDesc.trim();
      if (newDesk) body.desk = newDesk;
      if (newDue) body.due_date = newDue;
      if (newDesk) {
        fetch(`${API}/max/ai-desks/tasks`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: newTitle.trim(), description: newDesc.trim() || newTitle.trim(), priority: newPriority, source: 'founder' }),
        }).catch(() => {});
      }
      const res = await fetch(`${API}/tasks/`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const saved = await res.json();
        setTasks(prev => [saved, ...prev]);
        setNewTitle(''); setNewDesc(''); setNewPriority('normal'); setNewDesk(''); setNewDue('');
        setShowForm(false);
      }
    } catch { /* */ }
    setSaving(false);
  };

  const filtered = tasks.filter(t => {
    const isDone = t.status === 'done';
    if (filter === 'pending' && isDone) return false;
    if (filter === 'done' && !isDone) return false;
    if (deskFilter && t.desk !== deskFilter) return false;
    if (search && !(t.title || '').toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const pending = tasks.filter(t => t.status !== 'done');
  const done = tasks.filter(t => t.status === 'done');
  const urgent = tasks.filter(t => t.priority === 'urgent' && t.status !== 'done');

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }} className="px-4 sm:px-9 py-6">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#fdf8eb] flex items-center justify-center">
            <CheckCircle2 size={20} className="text-[#b8960c]" />
          </div>
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>Tasks</h2>
            <p style={{ fontSize: 13, color: '#aaa', margin: 0 }}>{pending.length} pending · {done.length} completed</p>
          </div>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1.5 cursor-pointer font-bold transition-all hover:bg-[#a08509]"
          style={{ minHeight: 44, padding: '0 14px', fontSize: 13, borderRadius: 10, background: '#b8960c', color: '#fff', border: 'none' }}
        >
          <Plus size={14} /> New Task
        </button>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
        <div className="empire-card" style={{ textAlign: 'center', padding: '14px 10px' }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#b8960c' }}>{pending.length}</div>
          <div style={{ fontSize: 11, color: '#999', fontWeight: 600 }}>Pending</div>
        </div>
        <div className="empire-card" style={{ textAlign: 'center', padding: '14px 10px' }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#dc2626' }}>{urgent.length}</div>
          <div style={{ fontSize: 10, color: '#999', fontWeight: 600 }}>Urgent</div>
        </div>
        <div className="empire-card" style={{ textAlign: 'center', padding: '14px 10px' }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#16a34a' }}>{done.length}</div>
          <div style={{ fontSize: 10, color: '#999', fontWeight: 600 }}>Completed</div>
        </div>
        <div className="empire-card" style={{ textAlign: 'center', padding: '14px 10px' }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: '#2563eb' }}>{tasks.length}</div>
          <div style={{ fontSize: 10, color: '#999', fontWeight: 600 }}>Total</div>
        </div>
      </div>

      {/* New Task Form */}
      {showForm && (
        <div className="empire-card mb-5" style={{ borderColor: '#f0e6c0' }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#b8960c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12 }}>New Task</div>
          <input
            value={newTitle} onChange={e => setNewTitle(e.target.value)}
            placeholder="What needs to be done?"
            autoFocus
            className="form-input mb-3"
            style={{ fontSize: 15, fontWeight: 600 }}
          />
          <textarea
            value={newDesc} onChange={e => setNewDesc(e.target.value)}
            placeholder="Add details or context..."
            rows={2}
            className="form-input mb-3"
            style={{ resize: 'none' }}
          />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3">
            <div>
              <label style={{ fontSize: 9, fontWeight: 700, color: '#999', textTransform: 'uppercase', display: 'block', marginBottom: 4 }}>Priority</label>
              <div className="flex gap-1">
                {(['urgent', 'high', 'normal', 'low'] as const).map(p => (
                  <button key={p} onClick={() => setNewPriority(p)}
                    className="cursor-pointer transition-all"
                    style={{
                      flex: 1, padding: '5px 2px', borderRadius: 6, fontSize: 9, fontWeight: 700,
                      textTransform: 'capitalize', border: '1.5px solid',
                      borderColor: newPriority === p ? PRIORITY_COLORS[p].text : '#ece8e0',
                      background: newPriority === p ? PRIORITY_COLORS[p].bg : '#faf9f7',
                      color: newPriority === p ? PRIORITY_COLORS[p].text : '#999',
                    }}>
                    {p}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label style={{ fontSize: 9, fontWeight: 700, color: '#999', textTransform: 'uppercase', display: 'block', marginBottom: 4 }}>Assign Desk</label>
              <select value={newDesk} onChange={e => setNewDesk(e.target.value)}
                className="form-input" style={{ fontSize: 11, padding: '6px 8px' }}>
                <option value="">Auto-assign</option>
                {TASK_DESKS.slice(1).map(d => <option key={d.id} value={d.id}>{d.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: 9, fontWeight: 700, color: '#999', textTransform: 'uppercase', display: 'block', marginBottom: 4 }}>Due Date</label>
              <input type="date" value={newDue} onChange={e => setNewDue(e.target.value)}
                className="form-input" style={{ fontSize: 11, padding: '6px 8px' }} />
            </div>
          </div>
          {newDesk && (
            <div style={{ fontSize: 10, color: '#b8960c', marginBottom: 10, display: 'flex', alignItems: 'center', gap: 4 }}>
              <Sparkles size={10} /> AI agent will work on this task automatically
            </div>
          )}
          <div className="flex items-center justify-end gap-2">
            <button onClick={() => setShowForm(false)} className="cursor-pointer"
              style={{ padding: '8px 14px', fontSize: 12, fontWeight: 600, borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7', color: '#777' }}>
              Cancel
            </button>
            <button onClick={addTask} disabled={!newTitle.trim() || saving} className="cursor-pointer disabled:opacity-50"
              style={{ padding: '8px 18px', fontSize: 12, fontWeight: 700, borderRadius: 8, border: 'none', background: '#b8960c', color: '#fff', display: 'flex', alignItems: 'center', gap: 6 }}>
              {saving ? <><Loader2 size={13} className="animate-spin" /> Saving...</> : <><Send size={13} /> Create</>}
            </button>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 gap-3">
        <div className="flex flex-wrap gap-1">
          {(['all', 'pending', 'done'] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`filter-tab ${filter === f ? 'active' : ''}`}>
              {f === 'all' ? 'All' : f === 'pending' ? 'Pending' : 'Completed'}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <select value={deskFilter} onChange={e => setDeskFilter(e.target.value)}
            style={{ padding: '6px 10px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 11, background: '#fff', cursor: 'pointer' }}>
            {TASK_DESKS.map(d => <option key={d.id} value={d.id}>{d.label}</option>)}
          </select>
          <div style={{ position: 'relative' }}>
            <Search size={13} style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)', color: '#ccc' }} />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search tasks..."
              style={{ padding: '6px 10px 6px 26px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 11, background: '#fff', width: 160 }}
              className="focus:border-[#b8960c]" />
          </div>
        </div>
      </div>

      {/* Tasks List */}
      {loading ? (
        <div className="flex items-center justify-center py-20"><Loader2 size={24} className="text-[#b8960c] animate-spin" /></div>
      ) : filtered.length > 0 ? (
        <div className="flex flex-col gap-2">
          {filtered.map((task: any) => {
            const isDone = task.status === 'done';
            const pc = PRIORITY_COLORS[task.priority] || PRIORITY_COLORS.normal;
            return (
              <div key={task.id} className="empire-card transition-all hover:border-[#f0e6c0] cursor-pointer"
                onClick={() => fetchTaskDetail(task.id)}
                style={{ opacity: isDone ? 0.6 : 1, borderLeftWidth: 3, borderLeftColor: pc.text }}>
                <div className="flex items-center gap-3">
                  <button onClick={(e) => { e.stopPropagation(); toggleTask(task); }} className="cursor-pointer shrink-0" style={{ background: 'none', border: 'none', padding: 0 }}>
                    {isDone
                      ? <CheckCircle2 size={20} className="text-[#16a34a]" />
                      : <Circle size={20} style={{ color: pc.text }} />
                    }
                  </button>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span style={{ fontSize: 13, fontWeight: isDone ? 400 : 600, color: isDone ? '#999' : '#1a1a1a', textDecoration: isDone ? 'line-through' : 'none' }} className="truncate">
                        {task.title}
                      </span>
                    </div>
                    {task.description && (
                      <div style={{ fontSize: 11, color: '#999', marginTop: 2 }} className="truncate">{task.description}</div>
                    )}
                    <div className="flex items-center gap-2 mt-1.5">
                      <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', padding: '2px 6px', borderRadius: 4, background: pc.bg, color: pc.text, border: `1px solid ${pc.border}` }}>
                        {task.priority || 'normal'}
                      </span>
                      {task.desk && (
                        <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', padding: '2px 6px', borderRadius: 4, background: '#eff6ff', color: '#2563eb', border: '1px solid #bfdbfe' }}>
                          {task.desk}
                        </span>
                      )}
                      {task.due_date && (
                        <span style={{ fontSize: 9, color: '#999', display: 'flex', alignItems: 'center', gap: 3 }}>
                          <Clock size={9} /> {new Date(task.due_date).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                  {task.created_at && (
                    <span style={{ fontSize: 9, color: '#ccc', flexShrink: 0 }}>
                      {new Date(task.created_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16">
          <CheckCircle2 size={40} className="text-[#e5e0d8] mb-3" />
          <div style={{ fontSize: 15, fontWeight: 600, color: '#999' }}>
            {filter === 'done' ? 'No completed tasks' : filter === 'pending' ? 'All caught up!' : 'No tasks yet'}
          </div>
          <div style={{ fontSize: 12, color: '#ccc', marginTop: 4 }}>
            {filter === 'all' ? 'Create your first task to get started' : 'Try a different filter'}
          </div>
        </div>
      )}

      {/* Task Detail Modal */}
      {viewingTask && (
        <div className="fixed inset-0 flex items-center justify-center z-50 p-8" style={{ background: 'rgba(0,0,0,0.4)' }} onClick={() => setViewingTask(null)}>
          <div style={{ background: '#fff', borderRadius: 16, maxWidth: '38rem', width: '100%', maxHeight: '85vh', overflowY: 'auto', boxShadow: '0 20px 60px rgba(0,0,0,0.15)' }}
            onClick={e => e.stopPropagation()}>
            <div className="flex items-start justify-between" style={{ padding: '24px 24px 16px', borderBottom: '1px solid #ece8e0' }}>
              <div className="flex-1 min-w-0 pr-4">
                <h3 style={{ fontSize: 18, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>{viewingTask.title}</h3>
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  {viewingTask.priority && (() => {
                    const pc = PRIORITY_COLORS[viewingTask.priority] || PRIORITY_COLORS.normal;
                    return <span style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', padding: '3px 8px', borderRadius: 6, background: pc.bg, color: pc.text, border: `1px solid ${pc.border}` }}>{viewingTask.priority}</span>;
                  })()}
                  <span style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', padding: '3px 8px', borderRadius: 6, background: viewingTask.status === 'done' ? '#f0fdf4' : '#fdf8eb', color: viewingTask.status === 'done' ? '#16a34a' : '#b8960c', border: `1px solid ${viewingTask.status === 'done' ? '#bbf7d0' : '#f0e6c0'}` }}>
                    {(viewingTask.status || 'todo').replace('_', ' ')}
                  </span>
                  {viewingTask.desk && (
                    <span style={{ fontSize: 9, fontWeight: 700, textTransform: 'uppercase', padding: '3px 8px', borderRadius: 6, background: '#eff6ff', color: '#2563eb', border: '1px solid #bfdbfe' }}>{viewingTask.desk}</span>
                  )}
                </div>
              </div>
              <button onClick={() => setViewingTask(null)} className="cursor-pointer hover:bg-[#f5f3ef] transition-colors" style={{ padding: 8, borderRadius: 8, color: '#999', background: 'none', border: 'none' }}>
                <X size={20} />
              </button>
            </div>

            <div className="space-y-4" style={{ padding: 24 }}>
              {viewingTask.description && (
                <div>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>Description</div>
                  <p style={{ fontSize: 13, color: '#555', lineHeight: 1.6, margin: 0 }}>{viewingTask.description}</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                {viewingTask.assigned_to && (
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>Assigned To</div>
                    <div style={{ fontSize: 13, color: '#555' }}>{viewingTask.assigned_to}</div>
                  </div>
                )}
                {viewingTask.created_by && (
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>Created By</div>
                    <div style={{ fontSize: 13, color: '#555' }}>{viewingTask.created_by}</div>
                  </div>
                )}
                {viewingTask.due_date && (
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>Due Date</div>
                    <div style={{ fontSize: 13, color: '#555' }}>{new Date(viewingTask.due_date).toLocaleDateString()}</div>
                  </div>
                )}
                {viewingTask.created_at && (
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>Created</div>
                    <div style={{ fontSize: 13, color: '#555' }} suppressHydrationWarning>{new Date(viewingTask.created_at).toLocaleString()}</div>
                  </div>
                )}
                {viewingTask.completed_at && (
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>Completed</div>
                    <div style={{ fontSize: 13, color: '#555' }} suppressHydrationWarning>{new Date(viewingTask.completed_at).toLocaleString()}</div>
                  </div>
                )}
              </div>

              {viewingTask.tags && viewingTask.tags.length > 0 && (
                <div>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>Tags</div>
                  <div className="flex flex-wrap gap-1.5">
                    {viewingTask.tags.map((tag: string) => (
                      <span key={tag} style={{ fontSize: 10, padding: '3px 8px', borderRadius: 6, background: '#f5f3ef', color: '#777', border: '1px solid #ece8e0' }}>{tag}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Activity log */}
              {viewingTask.activity && viewingTask.activity.length > 0 && (
                <div>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>Activity</div>
                  <div className="flex flex-col gap-1.5">
                    {viewingTask.activity.map((a: any, i: number) => (
                      <div key={i} className="flex items-start gap-3" style={{ padding: '8px 12px', borderRadius: 10, background: '#faf9f7', border: '1px solid #ece8e0' }}>
                        <span className="w-2 h-2 rounded-full mt-1.5 shrink-0" style={{ background: a.action === 'completed' ? '#16a34a' : a.action === 'created' ? '#2563eb' : '#b8960c' }} />
                        <div className="flex-1 min-w-0">
                          <span style={{ fontSize: 12, fontWeight: 600, color: '#555' }}>{a.action}</span>
                          {a.detail && <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>{a.detail}</div>}
                          <div style={{ fontSize: 9, fontFamily: 'monospace', color: '#ccc', marginTop: 4 }} suppressHydrationWarning>
                            {a.created_at ? new Date(a.created_at).toLocaleString() : ''}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Subtasks */}
              {viewingTask.subtasks && viewingTask.subtasks.length > 0 && (
                <div>
                  <div style={{ fontSize: 10, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>Subtasks</div>
                  <div className="flex flex-col gap-1">
                    {viewingTask.subtasks.map((st: any) => (
                      <div key={st.id} className="flex items-center gap-2" style={{ padding: '6px 10px', borderRadius: 8, background: '#faf9f7', border: '1px solid #ece8e0' }}>
                        {st.status === 'done'
                          ? <CheckCircle2 size={14} className="text-[#16a34a] shrink-0" />
                          : <Circle size={14} className="text-[#ccc] shrink-0" />
                        }
                        <span style={{ fontSize: 12, color: st.status === 'done' ? '#999' : '#555', textDecoration: st.status === 'done' ? 'line-through' : 'none' }}>{st.title}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Toggle status button */}
              <div className="flex justify-end pt-2">
                <button
                  onClick={() => {
                    toggleTask(viewingTask);
                    setViewingTask((prev: any) => prev ? { ...prev, status: prev.status === 'done' ? 'todo' : 'done' } : null);
                  }}
                  className="cursor-pointer transition-all hover:brightness-95"
                  style={{
                    padding: '10px 20px', borderRadius: 10, fontSize: 13, fontWeight: 600, border: 'none',
                    background: viewingTask.status === 'done' ? '#fdf8eb' : '#f0fdf4',
                    color: viewingTask.status === 'done' ? '#b8960c' : '#16a34a',
                  }}>
                  {viewingTask.status === 'done' ? 'Mark as To Do' : 'Mark as Done'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// -- Shared Components --

function KPI({ icon, iconBg, iconColor, label, value, sub, onClick }: {
  icon: React.ReactNode; iconBg: string; iconColor: string; label: string; value: string; sub: string; onClick?: () => void;
}) {
  return (
    <div onClick={onClick} className="empire-card" style={{ cursor: onClick ? 'pointer' : 'default' }}>
      <div className="flex items-center justify-between mb-2">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: iconBg, color: iconColor }}>{icon}</div>
      </div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
      <div style={{ fontSize: 10, color: '#aaa', marginTop: 2 }}>{sub}</div>
    </div>
  );
}

function QuickLink({ icon, label, desc, color, onClick }: {
  icon: React.ReactNode; label: string; desc: string; color: string; onClick: () => void;
}) {
  return (
    <button onClick={onClick} className="empire-card" style={{ textAlign: 'left', cursor: 'pointer', width: '100%', border: '1px solid #ece8e0' }}>
      <div className="flex items-center gap-2 mb-1">
        <span style={{ color }}>{icon}</span>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{label}</span>
      </div>
      <div style={{ fontSize: 10, color: '#777' }}>{desc}</div>
    </button>
  );
}

function InfoRow({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="flex items-center justify-between" style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0', background: '#faf9f7' }}>
      <span style={{ fontSize: 12, color: '#555' }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: 700, color }}>{value}</span>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const s = status || 'draft';
  const map: Record<string, string> = {
    draft: 'draft', sent: 'open', accepted: 'paid', rejected: 'overdue',
    proposal: 'vip', paid: 'paid', overdue: 'overdue', partial: 'transit',
  };
  return <span className={`status-pill ${map[s] || 'draft'}`}>{s.toUpperCase()}</span>;
}

function CreationsSection() {
  const [ideas, setIdeas] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(false);
  }, []);

  const catColors: Record<string, { bg: string; text: string }> = {
    product: { bg: '#fdf4ff', text: '#7c3aed' },
    feature: { bg: '#eff6ff', text: '#2563eb' },
    business: { bg: '#fef3c7', text: '#d97706' },
    design: { bg: '#fce7f3', text: '#ec4899' },
    marketing: { bg: '#dcfce7', text: '#16a34a' },
  };

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }} className="px-4 sm:px-9 py-6">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#fdf4ff] flex items-center justify-center">
            <Lightbulb size={20} className="text-[#7c3aed]" />
          </div>
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>Creations Lab</h2>
            <p style={{ fontSize: 13, color: '#aaa', margin: 0 }}>Innovation &amp; R&amp;D</p>
          </div>
        </div>
        <button
          disabled
          title="Ideas storage is not connected yet."
          className="flex items-center gap-1.5 cursor-not-allowed"
          style={{
            padding: '10px 18px', fontSize: 13, fontWeight: 700, color: '#fff', borderRadius: 12, border: 'none',
            background: '#9ca3af',
            opacity: 0.75,
          }}
        >
          <Lightbulb size={16} /> Storage not connected
        </button>
      </div>

      {/* Ideas list */}
      {!loading && ideas.length > 0 && (
        <div className="flex flex-col gap-3">
          {ideas.map((idea: any, i: number) => {
            const cat = catColors[idea.category] || catColors.product;
            return (
              <div key={idea.id || i} className="empire-card" style={{ cursor: 'pointer' }}>
                <div className="flex items-center gap-2 mb-2">
                  <span className="status-pill" style={{ background: cat.bg, color: cat.text, fontSize: 9 }}>{idea.category || 'product'}</span>
                  {idea.created_at && <span style={{ fontSize: 10, color: '#bbb' }}>{new Date(idea.created_at).toLocaleDateString()}</span>}
                </div>
                <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>{idea.title}</div>
                {idea.description && <div style={{ fontSize: 12, color: '#777', lineHeight: 1.5 }}>{idea.description}</div>}
              </div>
            );
          })}
        </div>
      )}

      {/* Empty */}
      {!loading && ideas.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="w-16 h-16 rounded-2xl bg-[#fdf4ff] flex items-center justify-center mb-4">
            <Lightbulb size={32} className="text-[#d8b4fe]" />
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, color: '#999', marginBottom: 4 }}>Ideas storage is not connected</div>
          <div style={{ fontSize: 13, color: '#777', marginBottom: 16, maxWidth: 420, textAlign: 'center' }}>
            Creations Lab has no active `/ideas` backend route yet. Use MAX or Tasks for idea capture until this module is wired to storage.
          </div>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={24} className="animate-spin text-[#7c3aed]" />
        </div>
      )}
    </div>
  );
}

function ComingSoon({ title, description, icon }: { title: string; description: string; icon: React.ReactNode }) {
  return (
    <div style={{ maxWidth: 960, margin: '0 auto', display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 400 }} className="px-4 sm:px-9 py-6">
      <div className="text-center">
        <div style={{ color: '#d8d3cb', marginBottom: 12 }}>{icon}</div>
        <div style={{ fontSize: 18, fontWeight: 700, color: '#aaa' }}>{title}</div>
        <div style={{ fontSize: 13, color: '#ccc', marginTop: 4 }}>{description}</div>
      </div>
    </div>
  );
}
