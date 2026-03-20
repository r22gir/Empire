'use client';
import React, { useState, useEffect, lazy, Suspense } from 'react';
import { API } from '../../lib/api';
import {
  Scissors, DollarSign, ClipboardList, TrendingUp, Calendar, Users,
  Package, FileText, Receipt, BarChart3, Truck, Headphones, Loader2, Zap, Camera, Lightbulb, Eye, ArrowLeft, Plus,
  CheckCircle2, Circle, Clock, Flag, Filter, Search, Sparkles, Send, X, Check, CreditCard, Ruler
} from 'lucide-react';
import QuoteActions from '../business/quotes/QuoteActions';
import QuickQuoteBuilder from '../business/quotes/QuickQuoteBuilder';
import { QuickQuotePanel, QuotePhasePipeline } from '../business/quotes/QuotePipeline';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';
import YardageCalculator from '../business/quotes/YardageCalculator';

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

const NAV_SECTIONS = [
  { id: 'overview', label: 'Overview', icon: Scissors },
  { id: 'creations', label: 'Creations', icon: Lightbulb },
  { id: 'quotes', label: 'Quotes', icon: ClipboardList },
  { id: 'finance', label: 'Finance', icon: DollarSign },
  { id: 'invoices', label: 'Invoices', icon: FileText },
  { id: 'expenses', label: 'Expenses', icon: Receipt },
  { id: 'customers', label: 'Customers', icon: Users },
  { id: 'inventory', label: 'Inventory', icon: Package },
  { id: 'jobs', label: 'Jobs', icon: Calendar },
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
  const [section, setSection] = useState<Section>((initialSection as Section) || 'overview');
  const [quotes, setQuotes] = useState<any[]>([]);
  const [stats, setStats] = useState({ pipeline: 0, openQuotes: 0, accepted: 0 });
  const [selectedCustomer, setSelectedCustomer] = useState<string | null>(null);
  const [initialQuoteId, setInitialQuoteId] = useState<string | null>(null);

  // Sync section when initialSection prop changes (e.g. from module click)
  useEffect(() => {
    if (initialSection) {
      setSection(initialSection as Section);
    }
  }, [initialSection]);

  useEffect(() => {
    fetch(API + '/quotes?limit=20').then(r => r.json()).then(data => {
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
        return <Suspense fallback={<Loading />}><FinanceDashboard /></Suspense>;
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
        return <QuotesSection quotes={quotes} initialQuoteId={initialQuoteId} onClearInitial={() => setInitialQuoteId(null)} />;
      case 'inventory':
        return <Suspense fallback={<Loading />}><InventorySection /></Suspense>;
      case 'jobs':
        return <Suspense fallback={<Loading />}><JobBoard /></Suspense>;
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
      {/* Sidebar nav */}
      <nav className="sm:w-[200px] w-full sm:border-r border-b sm:border-b-0" style={{ background: '#fff', borderColor: '#ece8e0', flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '18px 16px', borderBottom: '1px solid #ece8e0' }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#dcfce7] flex items-center justify-center">
              <Scissors size={18} className="text-[#16a34a]" />
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>Workroom</div>
              <div style={{ fontSize: 10, color: '#999' }}>Drapery & Upholstery</div>
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-x-auto sm:overflow-x-hidden overflow-y-auto" style={{ padding: '10px 10px' }}>
          <div className="flex sm:flex-col flex-row gap-1.5 sm:flex-nowrap flex-nowrap sm:w-auto w-max">
            {NAV_SECTIONS.map(nav => {
              const Icon = nav.icon;
              const isActive = section === nav.id && !selectedCustomer;
              return (
                <button key={nav.id}
                  onClick={() => { setSection(nav.id); setSelectedCustomer(null); }}
                  className="w-full flex items-center gap-3 text-left cursor-pointer transition-all"
                  style={{
                    padding: '10px 14px',
                    borderRadius: 12,
                    fontSize: 13,
                    fontWeight: isActive ? 700 : 500,
                    background: isActive ? '#dcfce7' : 'transparent',
                    color: isActive ? '#16a34a' : '#666',
                    border: isActive ? '1.5px solid #bbf7d0' : '1.5px solid transparent',
                  }}
                  onMouseEnter={e => { if (!isActive) { e.currentTarget.style.background = '#f5f3ef'; e.currentTarget.style.borderColor = '#ece8e0'; } }}
                  onMouseLeave={e => { if (!isActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'transparent'; } }}
                >
                  <Icon size={17} />
                  {nav.label}
                </button>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto" style={{ background: '#f5f2ed' }}>
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
    fetch(`${API}/crm/customers?limit=5&sort_by=updated_at&sort_dir=desc`).then(r => r.json()).then(d => setCustomers(d.customers || [])).catch(() => {});
    fetch(`${API}/jobs/`).then(r => r.json()).then(d => setJobs(Array.isArray(d) ? d : d.jobs || [])).catch(() => {});
    fetch(`${API}/finance/dashboard?range=this_month`).then(r => r.json()).then(d => setFinance(d)).catch(() => {});
    fetch(`${API}/inventory/dashboard`).then(r => r.json()).then(d => setInventory(d)).catch(() => {});
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
  const activities: { text: string; time: string; color: string; icon: React.ReactNode }[] = [];
  quotes.slice(0, 5).forEach(q => {
    activities.push({
      text: `Quote ${q.quote_number || 'Q'} ${q.status === 'accepted' ? 'accepted by' : q.status === 'sent' ? 'sent to' : 'created for'} ${q.customer_name || 'Customer'} — $${(q.total || 0).toLocaleString()}`,
      time: q.created_at || q.updated_at || '',
      color: q.status === 'accepted' ? '#16a34a' : q.status === 'sent' ? '#2563eb' : '#b8960c',
      icon: <ClipboardList size={14} />,
    });
  });
  jobs.slice(0, 3).forEach(j => {
    activities.push({
      text: `Job "${j.title}" ${j.status === 'completed' ? 'completed' : j.status === 'in_progress' ? 'in progress' : 'created'} — ${j.customer_name || 'Customer'}`,
      time: j.updated_at || j.created_at || '',
      color: j.status === 'completed' ? '#16a34a' : j.status === 'in_progress' ? '#d97706' : '#777',
      icon: <Calendar size={14} />,
    });
  });
  activities.sort((a, b) => (b.time || '').localeCompare(a.time || ''));

  const revenue = finance?.revenue?.amount || stats.pipeline || 0;
  const customerCount = finance?.customers?.total || customers.length || 0;

  return (
    <div style={{ maxWidth: 1060, margin: '0 auto' }} className="px-4 sm:px-9 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-3">
          <h1 style={{ fontSize: 24, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>Empire Workroom</h1>
          <span style={{ fontSize: 11, color: '#b8960c', fontWeight: 600, padding: '3px 10px', borderRadius: 20, background: '#fdf8eb', border: '1px solid #f0e6c0' }}>
            Custom Drapery & Upholstery
          </span>
        </div>
        <span style={{ fontSize: 13, color: '#aaa' }} suppressHydrationWarning>
          {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
        </span>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 mb-6">
        <KPI icon={<DollarSign size={18} />} iconBg="#fdf8eb" iconColor="#b8960c" label="Revenue Pipeline" value={`$${revenue.toLocaleString()}`} sub={`${quotes.length} quotes total`} onClick={() => onNavigate('quotes')} />
        <KPI icon={<Calendar size={18} />} iconBg="#eff6ff" iconColor="#2563eb" label="Active Jobs" value={String(activeJobs.length)} sub={overdueJobs.length > 0 ? `${overdueJobs.length} overdue` : 'On track'} onClick={() => onNavigate('jobs')} />
        <KPI icon={<ClipboardList size={18} />} iconBg="#fef3c7" iconColor="#d97706" label="Open Quotes" value={String(stats.openQuotes)} sub={`$${stats.pipeline.toLocaleString()} value`} onClick={() => onNavigate('quotes')} />
        <KPI icon={<Users size={18} />} iconBg="#dcfce7" iconColor="#16a34a" label="Customers" value={String(customerCount)} sub={`${customers.length} recent`} onClick={() => onNavigate('customers')} />
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-3 mb-6">
        <button onClick={() => onNavigate('quotes')} className="flex items-center gap-2 cursor-pointer hover:brightness-95 transition-all active:scale-[0.98]"
          style={{ minHeight: 44, padding: '0 20px', fontSize: 13, fontWeight: 700, borderRadius: 12, background: '#b8960c', color: '#fff', border: 'none', boxShadow: '0 2px 8px rgba(184,150,12,0.3)' }}>
          <Plus size={16} /> New Quote
        </button>
        <button onClick={() => onNavigate('customers')} className="flex items-center gap-2 cursor-pointer hover:brightness-95 transition-all active:scale-[0.98]"
          style={{ minHeight: 44, padding: '0 20px', fontSize: 13, fontWeight: 700, borderRadius: 12, background: '#b8960c', color: '#fff', border: 'none', boxShadow: '0 2px 8px rgba(184,150,12,0.3)' }}>
          <Users size={16} /> New Customer
        </button>
        <button onClick={() => onNavigate('jobs')} className="flex items-center gap-2 cursor-pointer hover:bg-[#f5f3ef] transition-all"
          style={{ minHeight: 44, padding: '0 20px', fontSize: 13, fontWeight: 700, borderRadius: 12, background: '#fff', color: '#555', border: '1.5px solid #ece8e0' }}>
          <Calendar size={16} /> New Job
        </button>
        <button onClick={() => onNavigate('invoices')} className="flex items-center gap-2 cursor-pointer hover:bg-[#f5f3ef] transition-all"
          style={{ minHeight: 44, padding: '0 20px', fontSize: 13, fontWeight: 700, borderRadius: 12, background: '#fff', color: '#555', border: '1.5px solid #ece8e0' }}>
          <FileText size={16} /> Send Invoice
        </button>
      </div>

      {/* Jobs at a Glance */}
      {jobs.length > 0 && (
        <div className="mb-6">
          <div className="section-label" style={{ marginBottom: 10 }}>Jobs at a Glance</div>
          <div className="flex gap-3 flex-wrap">
            {[
              { label: 'Pending', count: stageCounts.pending, color: '#777', bg: '#f0ede8' },
              { label: 'Scheduled', count: stageCounts.scheduled, color: '#2563eb', bg: '#eff6ff' },
              { label: 'In Progress', count: stageCounts.in_progress, color: '#d97706', bg: '#fffbeb' },
              { label: 'Completed', count: stageCounts.completed, color: '#16a34a', bg: '#f0fdf4' },
            ].map(stage => (
              <button key={stage.label} onClick={() => onNavigate('jobs')}
                className="cursor-pointer hover:shadow-md transition-all"
                style={{ padding: '12px 20px', borderRadius: 12, background: stage.bg, border: 'none', minWidth: 100, textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: stage.color }}>{stage.count}</div>
                <div style={{ fontSize: 11, fontWeight: 600, color: stage.color, opacity: 0.8 }}>{stage.label}</div>
              </button>
            ))}
            {overdueJobs.length > 0 && (
              <button onClick={() => onNavigate('jobs')}
                className="cursor-pointer hover:shadow-md transition-all"
                style={{ padding: '12px 20px', borderRadius: 12, background: '#fef2f2', border: '1.5px solid #fecaca', minWidth: 100, textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 700, color: '#dc2626' }}>{overdueJobs.length}</div>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#dc2626' }}>Overdue</div>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        {/* Recent Activity Feed */}
        <div className="empire-card" style={{ minHeight: 280 }}>
          <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 14 }} className="flex items-center gap-2">
            <TrendingUp size={15} className="text-[#b8960c]" /> Recent Activity
          </h3>
          <div className="space-y-2">
            {activities.slice(0, 6).map((a, i) => (
              <div key={i} className="flex items-start gap-3" style={{ padding: '10px 12px', borderRadius: 10, background: '#faf9f7', border: '1px solid #ece8e0' }}>
                <span className="mt-0.5 shrink-0" style={{ color: a.color }}>{a.icon}</span>
                <div className="flex-1 min-w-0">
                  <div style={{ fontSize: 12, color: '#555', lineHeight: 1.4 }}>{a.text}</div>
                  {a.time && (
                    <div style={{ fontSize: 9, color: '#bbb', marginTop: 3 }} suppressHydrationWarning>
                      {new Date(a.time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {activities.length === 0 && (
              <div style={{ fontSize: 12, color: '#aaa', textAlign: 'center', padding: '24px 0' }}>No recent activity</div>
            )}
          </div>
        </div>

        {/* Recent Quotes */}
        <div className="empire-card" style={{ minHeight: 280 }}>
          <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 14 }} className="flex items-center gap-2">
            <ClipboardList size={15} className="text-[#b8960c]" /> Recent Quotes
          </h3>
          <div className="space-y-2">
            {quotes.slice(0, 6).map((q, i) => (
              <div key={i} onClick={() => onSelectQuote?.(q.id)} style={{ padding: '10px 12px', borderRadius: 10, border: '1px solid #ece8e0' }} className="hover:border-[#b8960c] hover:bg-[#fdf8eb] transition-all cursor-pointer flex items-center justify-between">
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{q.quote_number || `Q-${i + 1}`}</div>
                  <div style={{ fontSize: 10, color: '#777' }}>{q.customer_name || 'Customer'}</div>
                </div>
                <div className="text-right">
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#b8960c' }}>${(q.total || 0).toLocaleString()}</div>
                  <StatusBadge status={q.status} />
                </div>
              </div>
            ))}
            {quotes.length === 0 && <div style={{ fontSize: 12, color: '#aaa', textAlign: 'center', padding: '24px 0' }}>No quotes yet</div>}
          </div>
        </div>
      </div>

      {/* Bottom Row: Inventory + Business Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Inventory Summary */}
        <div className="empire-card">
          <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 14 }} className="flex items-center gap-2">
            <Package size={15} className="text-[#16a34a]" /> Inventory
          </h3>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <div style={{ textAlign: 'center', padding: '10px 6px', borderRadius: 10, background: '#f0fdf4', border: '1px solid #bbf7d0' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#16a34a' }}>{inventory?.total_items || 0}</div>
              <div style={{ fontSize: 9, fontWeight: 600, color: '#16a34a', opacity: 0.8 }}>Items</div>
            </div>
            <div style={{ textAlign: 'center', padding: '10px 6px', borderRadius: 10, background: inventory?.low_stock_count > 0 ? '#fffbeb' : '#faf9f7', border: `1px solid ${inventory?.low_stock_count > 0 ? '#fde68a' : '#ece8e0'}` }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: inventory?.low_stock_count > 0 ? '#d97706' : '#777' }}>{inventory?.low_stock_count || 0}</div>
              <div style={{ fontSize: 9, fontWeight: 600, color: inventory?.low_stock_count > 0 ? '#d97706' : '#999' }}>Low Stock</div>
            </div>
            <div style={{ textAlign: 'center', padding: '10px 6px', borderRadius: 10, background: '#faf9f7', border: '1px solid #ece8e0' }}>
              <div style={{ fontSize: 20, fontWeight: 700, color: '#b8960c' }}>${(inventory?.total_value || 0).toLocaleString()}</div>
              <div style={{ fontSize: 9, fontWeight: 600, color: '#999' }}>Value</div>
            </div>
          </div>
          {inventory?.low_stock_count > 0 && (
            <button onClick={() => onNavigate('inventory')} className="w-full cursor-pointer hover:bg-[#fef3c7] transition-colors"
              style={{ padding: '8px 12px', borderRadius: 8, background: '#fffbeb', border: '1px solid #fde68a', fontSize: 11, fontWeight: 600, color: '#d97706', textAlign: 'center' }}>
              {inventory.low_stock_count} items need reorder
            </button>
          )}
          {!inventory?.low_stock_count && (
            <button onClick={() => onNavigate('inventory')} className="w-full cursor-pointer hover:bg-[#f5f3ef] transition-colors"
              style={{ padding: '8px 12px', borderRadius: 8, background: '#faf9f7', border: '1px solid #ece8e0', fontSize: 11, fontWeight: 600, color: '#777', textAlign: 'center' }}>
              View All Inventory
            </button>
          )}
        </div>

        {/* Business Summary */}
        <div className="empire-card">
          <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 14 }} className="flex items-center gap-2">
            <BarChart3 size={15} className="text-[#7c3aed]" /> Business Summary
          </h3>
          <div className="space-y-2">
            <InfoRow label="Total Pipeline" value={`$${stats.pipeline.toLocaleString()}`} color="#b8960c" />
            <InfoRow label="Open Quotes" value={String(stats.openQuotes)} color="#d97706" />
            <InfoRow label="Accepted Quotes" value={String(stats.accepted)} color="#16a34a" />
            <InfoRow label="Active Jobs" value={String(activeJobs.length)} color="#2563eb" />
          </div>
          <button onClick={() => onNavigate('finance')} className="w-full cursor-pointer hover:bg-[#f5f3ef] transition-colors mt-3"
            style={{ padding: '8px 12px', borderRadius: 8, background: '#faf9f7', border: '1px solid #ece8e0', fontSize: 11, fontWeight: 600, color: '#777', textAlign: 'center' }}>
            View Full Financial Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}

// -- Quotes Section --

function QuotesSection({ quotes, initialQuoteId, onClearInitial }: { quotes: any[]; initialQuoteId?: string | null; onClearInitial?: () => void }) {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const [showQuickQuote, setShowQuickQuote] = useState(false);
  const [showQuickCalc, setShowQuickCalc] = useState(false);
  const [pipelineQuoteId, setPipelineQuoteId] = useState<string | null>(null);
  const [analyzingQuoteId, setAnalyzingQuoteId] = useState<string | null>(null);
  const [viewingQuoteId, setViewingQuoteId] = useState<string | null>(initialQuoteId || null);

  // Auto-open quote from external navigation
  useEffect(() => {
    if (initialQuoteId) {
      setViewingQuoteId(initialQuoteId);
      onClearInitial?.();
    }
  }, [initialQuoteId]);
  const [showBuilder, setShowBuilder] = useState(false);
  const filtered = quotes.filter(q => {
    if (filter !== 'all' && q.status !== filter) return false;
    if (search && !((q.customer_name || '').toLowerCase().includes(search.toLowerCase()) ||
                    (q.quote_number || '').toLowerCase().includes(search.toLowerCase()) ||
                    (q.intake_code || '').toLowerCase().includes(search.toLowerCase()))) return false;
    return true;
  });

  const filters = ['all', 'draft', 'sent', 'accepted', 'proposal'];

  // QuoteBuilder view
  if (showBuilder) {
    return (
      <Suspense fallback={<div className="flex items-center justify-center py-20"><Loader2 size={24} className="text-[#b8960c] animate-spin" /></div>}>
        <QuoteBuilderScreen onBack={() => setShowBuilder(false)} />
      </Suspense>
    );
  }

  // Viewing a specific quote — show full review
  if (viewingQuoteId) {
    return (
      <div style={{ maxWidth: 960, margin: '0 auto' }} className="px-4 sm:px-9 py-6">
        <button
          onClick={() => setViewingQuoteId(null)}
          className="flex items-center gap-2 cursor-pointer mb-4 transition-colors hover:text-[#b8960c]"
          style={{ background: 'none', border: 'none', fontSize: 13, fontWeight: 600, color: '#777', padding: 0 }}
        >
          <ArrowLeft size={16} /> Back to Quotes
        </button>
        <Suspense fallback={<div className="flex items-center justify-center py-20"><Loader2 size={24} className="text-[#b8960c] animate-spin" /></div>}>
          <QuoteReviewScreen quoteId={viewingQuoteId} onOpenBuilder={() => { setViewingQuoteId(null); setShowBuilder(true); }} />
        </Suspense>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 960, margin: '0 auto' }} className="px-4 sm:px-9 py-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-5 gap-3">
        <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }} className="flex items-center gap-2">
          <ClipboardList size={20} className="text-[#b8960c]" /> Quotes
        </h2>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setShowBuilder(true)}
            className="flex items-center gap-1.5 cursor-pointer font-bold transition-all hover:bg-[#a08509]"
            style={{ minHeight: 44, padding: '0 14px', fontSize: 13, borderRadius: 10, background: '#b8960c', color: '#fff', border: 'none' }}
          >
            <Plus size={14} /> New Quote
          </button>
          <button
            onClick={() => setShowQuickQuote(!showQuickQuote)}
            className="flex items-center gap-1.5 cursor-pointer font-bold transition-all hover:border-[#b8960c] hover:text-[#b8960c]"
            style={{ minHeight: 44, padding: '0 14px', fontSize: 13, borderRadius: 10, background: '#faf9f7', color: '#555', border: '1.5px solid #ece8e0' }}
          >
            <Zap size={14} /> Quick Quote
          </button>
          <button
            onClick={() => setShowQuickCalc(!showQuickCalc)}
            className="flex items-center gap-1.5 cursor-pointer font-bold transition-all hover:border-[#16a34a] hover:text-[#16a34a]"
            style={{ minHeight: 44, padding: '0 14px', fontSize: 13, borderRadius: 10, background: '#faf9f7', color: '#555', border: '1.5px solid #ece8e0' }}
          >
            <Ruler size={14} /> Yardage Calc
          </button>
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search quotes..."
            style={{ padding: '8px 12px', border: '1px solid #ece8e0', borderRadius: 10, fontSize: 13, background: '#fff', outline: 'none', minHeight: 44 }}
            className="focus:border-[#b8960c] w-full sm:w-[200px]" />
        </div>
      </div>

      {/* Quick Quote Builder (photo-based) */}
      {showQuickQuote && (
        <div style={{ marginBottom: 20 }}>
          <QuickQuoteBuilder onClose={() => setShowQuickQuote(false)} />
        </div>
      )}

      {/* Yardage Calculator (the $199/mo feature) */}
      {showQuickCalc && (
        <div style={{ marginBottom: 20 }}>
          <YardageCalculator onClose={() => setShowQuickCalc(false)} />
        </div>
      )}

      {/* Phase Pipeline (when a quote is selected for pipeline review) */}
      {pipelineQuoteId && (
        <div style={{ marginBottom: 20 }}>
          <div className="flex items-center justify-between mb-2">
            <span style={{ fontSize: 11, fontWeight: 600, color: '#777' }}>Phase Pipeline</span>
            <button onClick={() => setPipelineQuoteId(null)}
              className="cursor-pointer" style={{ background: 'none', border: 'none', fontSize: 11, color: '#999' }}>
              <X size={14} /> Close
            </button>
          </div>
          <QuotePhasePipeline quoteId={pipelineQuoteId} />
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex flex-wrap gap-1 mb-4">
        {filters.map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className={`filter-tab ${filter === f ? 'active' : ''}`}>
            {f === 'all' ? 'All Status' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto">
      <table className="empire-table">
        <thead>
          <tr>
            <th>Quote #</th>
            <th>Customer</th>
            <th style={{ textAlign: 'right' }}>Total</th>
            <th>Status</th>
            <th>Date</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((q, i) => (
            <React.Fragment key={i}>
              <tr className="cursor-pointer hover:bg-[#fdf8eb] transition-colors" onClick={() => setViewingQuoteId(q.id)}>
                <td style={{ fontWeight: 600, color: '#1a1a1a' }}>{q.quote_number || `Q-${i + 1}`}</td>
                <td>
                  {q.customer_name || '--'}
                  {q.intake_code && (
                    <span style={{ marginLeft: 6, fontSize: 9, padding: '1px 6px', borderRadius: 6, background: '#eff6ff', border: '1px solid #bfdbfe', color: '#2563eb', fontWeight: 600 }}>
                      {q.intake_code}
                    </span>
                  )}
                </td>
                <td style={{ fontWeight: 700, color: '#b8960c', textAlign: 'right' }}>${(q.total || 0).toLocaleString()}</td>
                <td><StatusBadge status={q.status} /></td>
                <td style={{ fontFamily: 'monospace', color: '#999', fontSize: 10 }} suppressHydrationWarning>
                  {q.created_at ? new Date(q.created_at).toLocaleDateString() : '--'}
                </td>
                <td>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setViewingQuoteId(q.id)}
                      title="View Quote"
                      className="inline-flex items-center justify-center transition-all cursor-pointer"
                      style={{ width: 32, height: 32, borderRadius: 10, backgroundColor: '#fff', color: '#b8960c', border: '1px solid #ece8e0' }}
                      onMouseEnter={e => { e.currentTarget.style.backgroundColor = '#b8960c'; e.currentTarget.style.color = '#fff'; e.currentTarget.style.borderColor = '#b8960c'; }}
                      onMouseLeave={e => { e.currentTarget.style.backgroundColor = '#fff'; e.currentTarget.style.color = '#b8960c'; e.currentTarget.style.borderColor = '#ece8e0'; }}
                    >
                      <Eye size={14} />
                    </button>
                    <QuoteActions quoteId={q.id} status={q.status || 'draft'} compact />
                    <button
                      onClick={(e) => { e.stopPropagation(); setPipelineQuoteId(pipelineQuoteId === q.id ? null : q.id); }}
                      title="Phase Pipeline"
                      className="inline-flex items-center justify-center w-8 h-8 rounded-[10px] border border-[#ece8e0] hover:border-[#16a34a] hover:bg-[#f0fdf4] transition-all cursor-pointer"
                    >
                      <TrendingUp size={14} className="text-[#16a34a]" />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); setAnalyzingQuoteId(analyzingQuoteId === q.id ? null : q.id); }}
                      title="AI Photo Analysis"
                      className="inline-flex items-center justify-center w-8 h-8 rounded-[10px] border border-[#ece8e0] hover:border-[#7c3aed] hover:bg-[#f5f0ff] transition-all cursor-pointer"
                    >
                      <Camera size={14} className="text-[#7c3aed]" />
                    </button>
                  </div>
                </td>
              </tr>
              {analyzingQuoteId === q.id && (
                <tr>
                  <td colSpan={6} style={{ padding: 0 }}>
                    <div style={{ padding: '16px 20px', background: '#faf9f7', borderTop: '1px solid #ece8e0' }}>
                      <Suspense fallback={<div className="flex items-center justify-center py-8"><Loader2 size={20} className="text-[#7c3aed] animate-spin" /></div>}>
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
        <div style={{ textAlign: 'center', padding: '40px 0', fontSize: 13, color: '#aaa' }}>No quotes found</div>
      )}
    </div>
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
      const res = await fetch(`${API}/tasks/?limit=50`);
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
      const body: any = { title: newTitle.trim(), priority: newPriority };
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
  const [showForm, setShowForm] = useState(false);
  const [newIdea, setNewIdea] = useState({ title: '', description: '', category: 'product' });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/ideas/`)
      .then(r => r.ok ? r.json() : { ideas: [] })
      .then(data => { setIdeas(data.ideas || data || []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!newIdea.title.trim()) return;
    try {
      const res = await fetch(`${API}/ideas/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newIdea),
      });
      if (res.ok) {
        const saved = await res.json();
        setIdeas(prev => [saved, ...prev]);
        setNewIdea({ title: '', description: '', category: 'product' });
        setShowForm(false);
      }
    } catch { /* */ }
  };

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
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-1.5 cursor-pointer hover:brightness-110 transition-all active:scale-[0.97]"
          style={{
            padding: '10px 18px', fontSize: 13, fontWeight: 700, color: '#fff', borderRadius: 12, border: 'none',
            background: 'linear-gradient(135deg, #7c3aed, #ec4899)',
            boxShadow: '0 2px 10px rgba(124,58,237,0.3)',
          }}
        >
          <Lightbulb size={16} /> New Idea
        </button>
      </div>

      {/* New Idea Form */}
      {showForm && (
        <div className="empire-card mb-5" style={{ borderColor: '#e9d5ff' }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#7c3aed', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>New Idea</div>
          <input
            value={newIdea.title}
            onChange={e => setNewIdea(f => ({ ...f, title: e.target.value }))}
            placeholder="Idea title..."
            className="form-input mb-3"
            style={{ fontSize: 15, fontWeight: 600 }}
          />
          <textarea
            value={newIdea.description}
            onChange={e => setNewIdea(f => ({ ...f, description: e.target.value }))}
            placeholder="Describe your idea..."
            rows={3}
            className="form-input mb-3"
            style={{ resize: 'none' }}
          />
          <div className="flex items-center gap-3">
            <select
              value={newIdea.category}
              onChange={e => setNewIdea(f => ({ ...f, category: e.target.value }))}
              className="form-input"
              style={{ width: 'auto' }}
            >
              <option value="product">Product</option>
              <option value="feature">Feature</option>
              <option value="business">Business</option>
              <option value="design">Design</option>
              <option value="marketing">Marketing</option>
            </select>
            <div className="flex-1" />
            <button onClick={() => setShowForm(false)} className="cursor-pointer" style={{ padding: '8px 14px', fontSize: 12, fontWeight: 600, borderRadius: 8, border: '1px solid #ece8e0', background: '#faf9f7', color: '#777' }}>Cancel</button>
            <button onClick={handleSave} disabled={!newIdea.title.trim()} className="cursor-pointer disabled:opacity-50" style={{ padding: '8px 16px', fontSize: 12, fontWeight: 700, borderRadius: 8, border: 'none', background: '#7c3aed', color: '#fff' }}>Save Idea</button>
          </div>
        </div>
      )}

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
      {!loading && ideas.length === 0 && !showForm && (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="w-16 h-16 rounded-2xl bg-[#fdf4ff] flex items-center justify-center mb-4">
            <Lightbulb size={32} className="text-[#d8b4fe]" />
          </div>
          <div style={{ fontSize: 18, fontWeight: 700, color: '#999', marginBottom: 4 }}>No ideas yet</div>
          <div style={{ fontSize: 13, color: '#bbb', marginBottom: 16 }}>Capture your innovations and product ideas</div>
          <button
            onClick={() => setShowForm(true)}
            className="cursor-pointer hover:brightness-110 transition-all"
            style={{
              padding: '12px 24px', fontSize: 14, fontWeight: 700, color: '#fff', borderRadius: 14, border: 'none',
              background: 'linear-gradient(135deg, #7c3aed, #ec4899)',
            }}
          >
            Add First Idea
          </button>
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
