'use client';
import { useState, useEffect, lazy, Suspense } from 'react';
import { API } from '../../lib/api';
import {
  Scissors, DollarSign, ClipboardList, TrendingUp, Calendar, Users,
  Package, FileText, Receipt, BarChart3, Truck, Headphones, Loader2
} from 'lucide-react';
import QuoteActions from '../business/quotes/QuoteActions';

// Lazy-load business modules (they'll be created by the build agents)
const FinanceDashboard = lazy(() => import('../business/finance/FinanceDashboard'));
const InvoiceList = lazy(() => import('../business/finance/InvoiceList'));
const ExpenseTracker = lazy(() => import('../business/finance/ExpenseTracker'));
const CustomerList = lazy(() => import('../business/crm/CustomerList'));
const CustomerDetail = lazy(() => import('../business/crm/CustomerDetail'));
const JobBoard = lazy(() => import('../business/jobs/JobBoard'));

const NAV_SECTIONS = [
  { id: 'overview', label: 'Overview', icon: Scissors },
  { id: 'finance', label: 'Finance', icon: DollarSign },
  { id: 'invoices', label: 'Invoices', icon: FileText },
  { id: 'expenses', label: 'Expenses', icon: Receipt },
  { id: 'customers', label: 'Customers', icon: Users },
  { id: 'quotes', label: 'Quotes', icon: ClipboardList },
  { id: 'inventory', label: 'Inventory', icon: Package },
  { id: 'jobs', label: 'Jobs', icon: Calendar },
] as const;

type Section = typeof NAV_SECTIONS[number]['id'];

export default function WorkroomPage() {
  const [section, setSection] = useState<Section>('overview');
  const [quotes, setQuotes] = useState<any[]>([]);
  const [stats, setStats] = useState({ pipeline: 0, openQuotes: 0, accepted: 0 });
  const [selectedCustomer, setSelectedCustomer] = useState<string | null>(null);

  useEffect(() => {
    fetch(API + '/quotes?limit=20').then(r => r.json()).then(data => {
      const q = data.quotes || data || [];
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
            <CustomerList onSelectCustomer={(id) => setSelectedCustomer(id)} />
          </Suspense>
        );
      case 'quotes':
        return <QuotesSection quotes={quotes} />;
      case 'inventory':
        return <ComingSoon title="Inventory" description="Fabric, hardware, and materials tracking — coming next." icon={<Package size={32} />} />;
      case 'jobs':
        return <Suspense fallback={<Loading />}><JobBoard /></Suspense>;
      default:
        return <OverviewSection quotes={quotes} stats={stats} onNavigate={setSection} />;
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Sidebar nav */}
      <nav className="w-48 bg-white border-r border-[#e5e0d8] shrink-0 flex flex-col">
        <div className="px-4 py-4 border-b border-[#ece8e1]">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[#dcfce7] flex items-center justify-center">
              <Scissors size={16} className="text-[#16a34a]" />
            </div>
            <div>
              <div className="text-sm font-bold text-[#1a1a1a]">Workroom</div>
              <div className="text-[9px] text-[#999]">Drapery & Upholstery</div>
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto py-2">
          {NAV_SECTIONS.map(nav => {
            const Icon = nav.icon;
            const isActive = section === nav.id && !selectedCustomer;
            return (
              <button key={nav.id}
                onClick={() => { setSection(nav.id); setSelectedCustomer(null); }}
                className={`w-full flex items-center gap-2.5 px-4 py-2.5 text-left text-xs font-medium cursor-pointer transition-all ${
                  isActive
                    ? 'bg-[#dcfce7] text-[#16a34a] font-bold border-r-2 border-[#16a34a]'
                    : 'text-[#777] hover:bg-[#f5f3ef] hover:text-[#1a1a1a]'
                }`}>
                <Icon size={15} />
                {nav.label}
              </button>
            );
          })}
        </div>
      </nav>

      {/* Main content */}
      <div className="flex-1 overflow-y-auto bg-[#faf9f7]">
        {renderContent()}
      </div>
    </div>
  );
}

// ── Overview Section ────────────────────────────────────────────────────

function OverviewSection({ quotes, stats, onNavigate }: { quotes: any[]; stats: any; onNavigate: (s: Section) => void }) {
  return (
    <div className="max-w-5xl mx-auto px-8 py-6">
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-xl font-bold text-[#1a1a1a]">Empire Workroom</h1>
        <span className="text-xs text-[#999]" suppressHydrationWarning>
          {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
        </span>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPI icon={<DollarSign size={18} />} iconBg="#fdf8eb" iconColor="#b8960c" label="Pipeline" value={`$${stats.pipeline.toLocaleString()}`} sub={`${quotes.length} quotes`} onClick={() => onNavigate('quotes')} />
        <KPI icon={<ClipboardList size={18} />} iconBg="#fef3c7" iconColor="#d97706" label="Open Quotes" value={String(stats.openQuotes)} sub="Awaiting approval" onClick={() => onNavigate('quotes')} />
        <KPI icon={<TrendingUp size={18} />} iconBg="#dcfce7" iconColor="#16a34a" label="Accepted" value={String(stats.accepted)} sub="Ready to produce" />
        <KPI icon={<Calendar size={18} />} iconBg="#ede9fe" iconColor="#7c3aed" label="In Production" value="--" sub="Active jobs" onClick={() => onNavigate('jobs')} />
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <QuickLink icon={<DollarSign size={18} />} label="Finance Dashboard" desc="Revenue, expenses, P&L" color="#16a34a" onClick={() => onNavigate('finance')} />
        <QuickLink icon={<FileText size={18} />} label="Invoices" desc="Create & manage invoices" color="#b8960c" onClick={() => onNavigate('invoices')} />
        <QuickLink icon={<Users size={18} />} label="Customers" desc="CRM & client directory" color="#2563eb" onClick={() => onNavigate('customers')} />
      </div>

      {/* Recent Quotes + Stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white border border-[#e5e0d8] rounded-xl p-5">
          <h3 className="text-sm font-bold text-[#1a1a1a] mb-3 flex items-center gap-2">
            <ClipboardList size={15} className="text-[#b8960c]" /> Recent Quotes
          </h3>
          <div className="space-y-2">
            {quotes.slice(0, 5).map((q, i) => (
              <div key={i} className="flex items-center justify-between p-3 rounded-lg border border-[#ece8e1] hover:border-[#b8960c] hover:bg-[#fdf8eb] transition-all cursor-pointer">
                <div>
                  <div className="text-xs font-semibold text-[#1a1a1a]">{q.quote_number || `Q-${i + 1}`}</div>
                  <div className="text-[10px] text-[#777]">{q.customer_name || 'Customer'}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-[#b8960c]">${(q.total || 0).toLocaleString()}</div>
                  <StatusBadge status={q.status} />
                </div>
              </div>
            ))}
            {quotes.length === 0 && <div className="text-xs text-[#aaa] text-center py-4">No quotes yet</div>}
          </div>
        </div>

        <div className="bg-white border border-[#e5e0d8] rounded-xl p-5">
          <h3 className="text-sm font-bold text-[#1a1a1a] mb-3 flex items-center gap-2">
            <Package size={15} className="text-[#16a34a]" /> Business Summary
          </h3>
          <div className="space-y-2">
            <InfoRow label="Total Pipeline" value={`$${stats.pipeline.toLocaleString()}`} color="#b8960c" />
            <InfoRow label="Open Quotes" value={String(stats.openQuotes)} color="#d97706" />
            <InfoRow label="Accepted" value={String(stats.accepted)} color="#16a34a" />
            <InfoRow label="Active Customers" value={String(new Set(quotes.map(q => q.customer_name)).size)} color="#7c3aed" />
          </div>
          <div className="mt-4 p-3 rounded-lg bg-[#f0fdf4] border border-[#bbf7d0]">
            <div className="text-[10px] font-bold text-[#16a34a] mb-1">QUICK ACTIONS</div>
            <div className="flex flex-wrap gap-2 mt-2">
              <button onClick={() => onNavigate('invoices')} className="text-[10px] px-3 py-1.5 rounded-lg bg-[#b8960c] text-white font-bold cursor-pointer hover:opacity-90 transition-opacity">
                New Invoice
              </button>
              <button onClick={() => onNavigate('customers')} className="text-[10px] px-3 py-1.5 rounded-lg border border-[#ece8e1] text-[#555] font-bold cursor-pointer hover:bg-[#f5f3ef] transition-colors">
                View Customers
              </button>
              <button onClick={() => onNavigate('finance')} className="text-[10px] px-3 py-1.5 rounded-lg border border-[#ece8e1] text-[#555] font-bold cursor-pointer hover:bg-[#f5f3ef] transition-colors">
                P&L Report
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Quotes Section ──────────────────────────────────────────────────────

function QuotesSection({ quotes }: { quotes: any[] }) {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');
  const filtered = quotes.filter(q => {
    if (filter !== 'all' && q.status !== filter) return false;
    if (search && !((q.customer_name || '').toLowerCase().includes(search.toLowerCase()) ||
                    (q.quote_number || '').toLowerCase().includes(search.toLowerCase()))) return false;
    return true;
  });

  return (
    <div className="max-w-5xl mx-auto px-8 py-6">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-lg font-bold text-[#1a1a1a] flex items-center gap-2">
          <ClipboardList size={20} className="text-[#b8960c]" /> Quotes
        </h2>
        <div className="flex items-center gap-2">
          <select value={filter} onChange={e => setFilter(e.target.value)}
            className="px-3 py-2 border border-[#e5e0d8] rounded-lg text-xs bg-white outline-none">
            <option value="all">All Status</option>
            <option value="draft">Draft</option>
            <option value="sent">Sent</option>
            <option value="accepted">Accepted</option>
            <option value="proposal">Proposal</option>
          </select>
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search quotes..."
            className="px-3 py-2 border border-[#e5e0d8] rounded-lg text-xs bg-white outline-none w-48 focus:border-[#b8960c]" />
        </div>
      </div>
      <div className="bg-white border border-[#e5e0d8] rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[#ece8e1] bg-[#faf9f7]">
              <th className="text-left px-4 py-3 text-[10px] font-bold text-[#999] uppercase">Quote #</th>
              <th className="text-left px-4 py-3 text-[10px] font-bold text-[#999] uppercase">Customer</th>
              <th className="text-right px-4 py-3 text-[10px] font-bold text-[#999] uppercase">Total</th>
              <th className="text-left px-4 py-3 text-[10px] font-bold text-[#999] uppercase">Status</th>
              <th className="text-left px-4 py-3 text-[10px] font-bold text-[#999] uppercase">Date</th>
              <th className="text-left px-4 py-3 text-[10px] font-bold text-[#999] uppercase">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((q, i) => (
              <tr key={i} className="border-b border-[#f0ede8] hover:bg-[#fdf8eb] transition-colors">
                <td className="px-4 py-3 text-xs font-semibold text-[#1a1a1a]">{q.quote_number || `Q-${i + 1}`}</td>
                <td className="px-4 py-3 text-xs text-[#555]">{q.customer_name || '--'}</td>
                <td className="px-4 py-3 text-xs font-bold text-[#b8960c] text-right">${(q.total || 0).toLocaleString()}</td>
                <td className="px-4 py-3"><StatusBadge status={q.status} /></td>
                <td className="px-4 py-3 text-[10px] font-mono text-[#999]" suppressHydrationWarning>
                  {q.created_at ? new Date(q.created_at).toLocaleDateString() : '--'}
                </td>
                <td className="px-4 py-3">
                  <QuoteActions quoteId={q.id} status={q.status || 'draft'} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="text-center py-10 text-sm text-[#aaa]">No quotes found</div>
        )}
      </div>
    </div>
  );
}

// ── Shared Components ───────────────────────────────────────────────────

function KPI({ icon, iconBg, iconColor, label, value, sub, onClick }: {
  icon: React.ReactNode; iconBg: string; iconColor: string; label: string; value: string; sub: string; onClick?: () => void;
}) {
  return (
    <div onClick={onClick}
      className={`bg-white border border-[#e5e0d8] rounded-xl p-4 transition-all ${onClick ? 'cursor-pointer hover:shadow-lg hover:border-[#b8960c]' : ''}`}>
      <div className="flex items-center justify-between mb-2">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: iconBg, color: iconColor }}>{icon}</div>
      </div>
      <div className="text-2xl font-bold text-[#1a1a1a]">{value}</div>
      <div className="text-[10px] text-[#777] font-medium mt-0.5">{label}</div>
      <div className="text-[9px] text-[#aaa] mt-0.5">{sub}</div>
    </div>
  );
}

function QuickLink({ icon, label, desc, color, onClick }: {
  icon: React.ReactNode; label: string; desc: string; color: string; onClick: () => void;
}) {
  return (
    <button onClick={onClick}
      className="bg-white border border-[#e5e0d8] rounded-xl p-4 text-left cursor-pointer hover:shadow-lg hover:border-[#b8960c] transition-all w-full group">
      <div className="flex items-center gap-2 mb-1">
        <span style={{ color }}>{icon}</span>
        <span className="text-sm font-bold text-[#1a1a1a] group-hover:text-[#b8960c] transition-colors">{label}</span>
      </div>
      <div className="text-[10px] text-[#777]">{desc}</div>
    </button>
  );
}

function InfoRow({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="flex items-center justify-between p-3 rounded-lg border border-[#ece8e1] bg-[#faf9f7]">
      <span className="text-xs text-[#555]">{label}</span>
      <span className="text-sm font-bold" style={{ color }}>{value}</span>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const s = status || 'draft';
  const colors: Record<string, string> = {
    draft: 'bg-[#f5f3ef] text-[#777]',
    sent: 'bg-[#dbeafe] text-[#2563eb]',
    accepted: 'bg-[#dcfce7] text-[#16a34a]',
    rejected: 'bg-[#fee2e2] text-[#dc2626]',
    proposal: 'bg-[#ede9fe] text-[#7c3aed]',
    paid: 'bg-[#dcfce7] text-[#16a34a]',
    overdue: 'bg-[#fee2e2] text-[#dc2626]',
    partial: 'bg-[#fef3c7] text-[#d97706]',
  };
  return <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${colors[s] || colors.draft}`}>{s.toUpperCase()}</span>;
}

function ComingSoon({ title, description, icon }: { title: string; description: string; icon: React.ReactNode }) {
  return (
    <div className="max-w-5xl mx-auto px-8 py-6 flex items-center justify-center min-h-[400px]">
      <div className="text-center">
        <div className="text-[#d8d3cb] mb-3">{icon}</div>
        <div className="text-lg font-bold text-[#aaa]">{title}</div>
        <div className="text-sm text-[#ccc] mt-1">{description}</div>
      </div>
    </div>
  );
}
