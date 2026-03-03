'use client';
import { useState, useEffect, useCallback } from 'react';
import { API_URL } from '@/lib/api';
import {
  ArrowLeft, LayoutDashboard, FileText, Users, Palette, CalendarDays, Package,
  Plus, Eye, Send, Trash2, ExternalLink, ChevronRight, Clock, DollarSign,
  Briefcase, Phone, Mail, MapPin, Search,
} from 'lucide-react';
import QuoteBuilder from './QuoteBuilder';

type Tab = 'dashboard' | 'quotes' | 'customers' | 'mockup' | 'schedule' | 'materials';

const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
  { key: 'dashboard',  label: 'Dashboard',     icon: <LayoutDashboard className="w-3.5 h-3.5" /> },
  { key: 'quotes',     label: 'Quotes',        icon: <FileText className="w-3.5 h-3.5" /> },
  { key: 'customers',  label: 'Customers',     icon: <Users className="w-3.5 h-3.5" /> },
  { key: 'mockup',     label: 'Mockup Studio', icon: <Palette className="w-3.5 h-3.5" /> },
  { key: 'schedule',   label: 'Schedule',      icon: <CalendarDays className="w-3.5 h-3.5" /> },
  { key: 'materials',  label: 'Materials',     icon: <Package className="w-3.5 h-3.5" /> },
];

interface Props {
  onBack: () => void;
}

export default function WorkroomForgeWorkspace({ onBack }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard');
  const [quotes, setQuotes] = useState<any[]>([]);
  const [showQuoteBuilder, setShowQuoteBuilder] = useState(false);

  const fetchQuotes = useCallback(async () => {
    try {
      const res = await fetch(API_URL + '/quotes');
      const data = await res.json();
      setQuotes(data.quotes || []);
    } catch { /* */ }
  }, []);

  useEffect(() => { fetchQuotes(); }, [fetchQuotes]);

  return (
    <div className="flex-1 flex min-h-0 overflow-hidden">
      {/* Sidebar nav */}
      <div className="shrink-0 flex flex-col" style={{ width: 180, borderRight: '1px solid var(--border)', background: 'var(--surface)' }}>
        {/* Header */}
        <div className="px-3 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 mb-2 text-xs transition"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={e => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
          >
            <ArrowLeft className="w-3 h-3" /> Back
          </button>
          <div className="flex items-center gap-2">
            <span className="text-lg">🪡</span>
            <span className="text-sm font-semibold" style={{ color: '#D4AF37' }}>WorkroomForge</span>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex-1 py-2 space-y-0.5">
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => { setActiveTab(t.key); setShowQuoteBuilder(false); }}
              className="w-full flex items-center gap-2.5 px-3 py-2 text-xs font-medium transition"
              style={{
                background: activeTab === t.key ? 'var(--gold-pale)' : 'transparent',
                color: activeTab === t.key ? 'var(--gold)' : 'var(--text-secondary)',
                borderLeft: `2px solid ${activeTab === t.key ? 'var(--gold)' : 'transparent'}`,
              }}
              onMouseEnter={e => { if (activeTab !== t.key) e.currentTarget.style.background = 'var(--hover)'; }}
              onMouseLeave={e => { if (activeTab !== t.key) e.currentTarget.style.background = 'transparent'; }}
            >
              {t.icon} {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 min-h-0 overflow-hidden">
        {activeTab === 'dashboard' && <DashboardTab quotes={quotes} onTabChange={setActiveTab} />}
        {activeTab === 'quotes' && (
          showQuoteBuilder
            ? <QuoteBuilder onClose={() => { setShowQuoteBuilder(false); fetchQuotes(); }} />
            : <QuotesTab quotes={quotes} onRefresh={fetchQuotes} onNewQuote={() => setShowQuoteBuilder(true)} />
        )}
        {activeTab === 'customers' && <CustomersTab />}
        {activeTab === 'mockup' && <MockupTab />}
        {activeTab === 'schedule' && <ScheduleTab />}
        {activeTab === 'materials' && <MaterialsTab />}
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════
   TAB: Dashboard
   ═══════════════════════════════════════════════════════════════ */
function DashboardTab({ quotes, onTabChange }: { quotes: any[]; onTabChange: (t: Tab) => void }) {
  const activeJobs = quotes.filter(q => q.status === 'accepted').length;
  const pendingQuotes = quotes.filter(q => q.status === 'draft' || q.status === 'sent').length;
  const totalRevenue = quotes.filter(q => q.status === 'accepted').reduce((s: number, q: any) => s + (q.total || 0), 0);
  const recentQuotes = quotes.slice(0, 5);

  const stats = [
    { label: 'Active Jobs', value: activeJobs, icon: <Briefcase className="w-4 h-4" />, color: '#22c55e' },
    { label: 'Pending Quotes', value: pendingQuotes, icon: <FileText className="w-4 h-4" />, color: '#f59e0b' },
    { label: 'Revenue', value: `$${totalRevenue.toLocaleString()}`, icon: <DollarSign className="w-4 h-4" />, color: '#D4AF37' },
    { label: 'Total Quotes', value: quotes.length, icon: <FileText className="w-4 h-4" />, color: '#8B5CF6' },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Dashboard</h3>

      {/* Stats cards */}
      <div className="grid grid-cols-4 gap-3">
        {stats.map(s => (
          <div key={s.label} className="rounded-xl p-3" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <div className="flex items-center justify-between mb-2">
              <span style={{ color: s.color }}>{s.icon}</span>
            </div>
            <p className="text-lg font-bold font-mono" style={{ color: 'var(--text-primary)' }}>{s.value}</p>
            <p className="text-[10px] mt-0.5" style={{ color: 'var(--text-muted)' }}>{s.label}</p>
          </div>
        ))}
      </div>

      {/* Recent quotes */}
      <div className="rounded-xl" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
        <div className="flex items-center justify-between px-4 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
          <h4 className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>Recent Quotes</h4>
          <button onClick={() => onTabChange('quotes')} className="text-[10px] flex items-center gap-1" style={{ color: 'var(--gold)' }}>
            View all <ChevronRight className="w-3 h-3" />
          </button>
        </div>
        {recentQuotes.length === 0 ? (
          <p className="text-xs text-center py-6" style={{ color: 'var(--text-muted)' }}>No quotes yet. Create your first estimate!</p>
        ) : (
          <div>
            {recentQuotes.map(q => (
              <div key={q.id} className="flex items-center gap-3 px-4 py-2.5 transition" style={{ borderBottom: '1px solid var(--border)' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--hover)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${
                  q.status === 'accepted' ? 'text-green-400' : q.status === 'sent' ? 'text-blue-400' : 'text-yellow-400'
                }`} style={{ background: q.status === 'accepted' ? 'rgba(34,197,94,0.12)' : q.status === 'sent' ? 'rgba(59,130,246,0.12)' : 'rgba(245,158,11,0.12)' }}>
                  {q.status}
                </span>
                <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>{q.quote_number}</span>
                <span className="flex-1 text-xs truncate" style={{ color: 'var(--text-primary)' }}>{q.customer_name}</span>
                <span className="text-xs font-mono font-semibold" style={{ color: 'var(--gold)' }}>${(q.total || 0).toFixed(2)}</span>
                <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{q.created_at?.slice(0, 10)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Upcoming installs */}
      <div className="rounded-xl p-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
        <h4 className="text-xs font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Upcoming Installations</h4>
        {quotes.filter(q => q.install_date).length === 0 ? (
          <p className="text-xs text-center py-4" style={{ color: 'var(--text-muted)' }}>No installations scheduled</p>
        ) : (
          <div className="space-y-2">
            {quotes.filter(q => q.install_date).slice(0, 5).map(q => (
              <div key={q.id} className="flex items-center gap-3 px-3 py-2 rounded-lg" style={{ background: 'var(--raised)' }}>
                <Clock className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--gold)' }} />
                <span className="text-xs flex-1" style={{ color: 'var(--text-primary)' }}>{q.customer_name} — {q.project_name || 'Project'}</span>
                <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>{q.install_date?.slice(0, 10)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════
   TAB: Quotes
   ═══════════════════════════════════════════════════════════════ */
function QuotesTab({ quotes, onRefresh, onNewQuote }: { quotes: any[]; onRefresh: () => void; onNewQuote: () => void }) {
  const [filter, setFilter] = useState('all');

  const filtered = filter === 'all' ? quotes : quotes.filter(q => q.status === filter);

  const statusCounts: Record<string, number> = {};
  quotes.forEach(q => { statusCounts[q.status] = (statusCounts[q.status] || 0) + 1; });

  const viewPdf = async (id: string) => {
    try {
      const res = await fetch(API_URL + `/quotes/${id}/pdf`, { method: 'POST' });
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    } catch (e) { console.error('PDF preview failed:', e); }
  };

  const deleteQuote = async (id: string) => {
    if (!confirm('Delete this quote?')) return;
    try {
      await fetch(API_URL + `/quotes/${id}`, { method: 'DELETE' });
      onRefresh();
    } catch { /* */ }
  };

  const sendQuote = async (id: string) => {
    try {
      await fetch(API_URL + `/quotes/${id}/send`, { method: 'POST' });
      onRefresh();
    } catch { /* */ }
  };

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      {/* Toolbar */}
      <div className="shrink-0 flex items-center justify-between px-4 py-2" style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center gap-1.5">
          <button onClick={() => setFilter('all')}
            className="px-2 py-1 rounded-lg text-[10px] font-medium transition"
            style={{ background: filter === 'all' ? 'var(--gold)' : 'var(--raised)', color: filter === 'all' ? '#0a0a0a' : 'var(--text-muted)' }}>
            All ({quotes.length})
          </button>
          {['draft', 'sent', 'accepted'].map(s => (
            <button key={s} onClick={() => setFilter(s)}
              className="px-2 py-1 rounded-lg text-[10px] font-medium transition capitalize"
              style={{ background: filter === s ? 'var(--gold)' : 'var(--raised)', color: filter === s ? '#0a0a0a' : 'var(--text-muted)' }}>
              {s} ({statusCounts[s] || 0})
            </button>
          ))}
        </div>
        <button onClick={onNewQuote}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold transition"
          style={{ background: 'var(--gold)', color: '#0a0a0a' }}>
          <Plus className="w-3.5 h-3.5" /> New Quote
        </button>
      </div>

      {/* Quote list */}
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3">
            <FileText className="w-8 h-8" style={{ color: 'var(--text-muted)' }} />
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No quotes found</p>
            <button onClick={onNewQuote}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold"
              style={{ background: 'var(--gold)', color: '#0a0a0a' }}>
              <Plus className="w-3.5 h-3.5" /> Create First Quote
            </button>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                {['Status', 'Number', 'Customer', 'Project', 'Total', 'Date', 'Actions'].map(h => (
                  <th key={h} className="text-[10px] font-semibold uppercase text-left px-4 py-2" style={{ color: 'var(--text-muted)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(q => (
                <tr key={q.id} className="transition"
                  style={{ borderBottom: '1px solid var(--border)' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--hover)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <td className="px-4 py-2.5">
                    <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${
                      q.status === 'accepted' ? 'text-green-400' : q.status === 'sent' ? 'text-blue-400' : 'text-yellow-400'
                    }`} style={{
                      background: q.status === 'accepted' ? 'rgba(34,197,94,0.12)' : q.status === 'sent' ? 'rgba(59,130,246,0.12)' : 'rgba(245,158,11,0.12)',
                    }}>{q.status}</span>
                  </td>
                  <td className="px-4 py-2.5 text-xs font-mono" style={{ color: 'var(--text-muted)' }}>{q.quote_number}</td>
                  <td className="px-4 py-2.5 text-xs" style={{ color: 'var(--text-primary)' }}>{q.customer_name}</td>
                  <td className="px-4 py-2.5 text-xs truncate max-w-[150px]" style={{ color: 'var(--text-secondary)' }}>{q.project_name || '—'}</td>
                  <td className="px-4 py-2.5 text-xs font-mono font-semibold" style={{ color: 'var(--gold)' }}>${(q.total || 0).toFixed(2)}</td>
                  <td className="px-4 py-2.5 text-[10px]" style={{ color: 'var(--text-muted)' }}>{q.created_at?.slice(0, 10)}</td>
                  <td className="px-4 py-2.5">
                    <div className="flex gap-1">
                      <button onClick={() => viewPdf(q.id)} className="p-1 rounded transition" style={{ color: 'var(--text-muted)' }}
                        title="View PDF"><Eye className="w-3.5 h-3.5" /></button>
                      {q.status === 'draft' && (
                        <button onClick={() => sendQuote(q.id)} className="p-1 rounded transition" style={{ color: '#3b82f6' }}
                          title="Mark as sent"><Send className="w-3.5 h-3.5" /></button>
                      )}
                      <button onClick={() => deleteQuote(q.id)} className="p-1 rounded transition" style={{ color: 'var(--text-muted)' }}
                        title="Delete"><Trash2 className="w-3.5 h-3.5" /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════
   TAB: Customers
   ═══════════════════════════════════════════════════════════════ */
function CustomersTab() {
  const [customers] = useState<any[]>([]);
  const [search, setSearch] = useState('');

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      {/* Toolbar */}
      <div className="shrink-0 flex items-center justify-between px-4 py-2" style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center gap-2 flex-1 max-w-sm">
          <Search className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
          <input
            type="text" placeholder="Search customers…" value={search}
            onChange={e => setSearch(e.target.value)}
            className="flex-1 bg-transparent text-xs outline-none" style={{ color: 'var(--text-primary)' }}
          />
        </div>
        <button className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold transition"
          style={{ background: 'var(--gold)', color: '#0a0a0a' }}>
          <Plus className="w-3.5 h-3.5" /> Add Customer
        </button>
      </div>

      {/* Customer list */}
      <div className="flex-1 overflow-y-auto p-4">
        {customers.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3">
            <Users className="w-8 h-8" style={{ color: 'var(--text-muted)' }} />
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No customers yet</p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Customers are auto-created when you save a quote</p>
          </div>
        ) : (
          <div className="space-y-2">
            {customers.map((c: any) => (
              <div key={c.id} className="flex items-center gap-4 px-4 py-3 rounded-xl transition"
                style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
                <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold"
                  style={{ background: 'var(--gold-pale)', color: 'var(--gold)' }}>
                  {c.name?.[0]?.toUpperCase() || '?'}
                </div>
                <div className="flex-1">
                  <p className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>{c.name}</p>
                  <div className="flex gap-3 mt-0.5">
                    {c.email && <span className="text-[10px] flex items-center gap-1" style={{ color: 'var(--text-muted)' }}><Mail className="w-2.5 h-2.5" />{c.email}</span>}
                    {c.phone && <span className="text-[10px] flex items-center gap-1" style={{ color: 'var(--text-muted)' }}><Phone className="w-2.5 h-2.5" />{c.phone}</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════
   TAB: Mockup Studio (Placeholder)
   ═══════════════════════════════════════════════════════════════ */
function MockupTab() {
  return (
    <div className="flex-1 flex items-center justify-center p-8">
      <div className="text-center max-w-sm">
        <span className="text-4xl block mb-3">🎨</span>
        <h3 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Visual Mockup Studio</h3>
        <p className="text-xs mb-4" style={{ color: 'var(--text-muted)' }}>
          Upload a room photo and see your drapery designs overlaid in real-time.
          AI-powered measurement extraction and fabric visualization.
        </p>
        <div className="rounded-xl p-3 text-left space-y-1.5" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          {['Photo upload & room detection', 'AI measurement extraction', 'Fabric overlay visualization', 'Customer-ready mockup export', 'Integration with quote system'].map(f => (
            <div key={f} className="flex items-center gap-2 text-[11px]" style={{ color: 'var(--text-secondary)' }}>
              <div className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: 'var(--gold)', opacity: 0.4 }} />
              {f}
            </div>
          ))}
        </div>
        <p className="text-[10px] mt-3" style={{ color: 'var(--text-muted)' }}>Connect to Visual Mockup Engine — Coming Soon</p>
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════
   TAB: Schedule
   ═══════════════════════════════════════════════════════════════ */
function ScheduleTab() {
  const today = new Date();
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(today);
    d.setDate(d.getDate() + i);
    return d;
  });

  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      {/* Week header */}
      <div className="shrink-0 flex items-center justify-between px-4 py-2" style={{ borderBottom: '1px solid var(--border)' }}>
        <h4 className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>
          Week of {today.toLocaleDateString([], { month: 'long', day: 'numeric', year: 'numeric' })}
        </h4>
        <button className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold transition"
          style={{ background: 'var(--gold)', color: '#0a0a0a' }}>
          <Plus className="w-3.5 h-3.5" /> Add Event
        </button>
      </div>

      {/* Week view */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-2">
          {days.map(d => {
            const isToday = d.toDateString() === today.toDateString();
            return (
              <div key={d.toISOString()} className="rounded-xl p-3" style={{
                background: isToday ? 'var(--gold-pale)' : 'var(--surface)',
                border: `1px solid ${isToday ? 'var(--gold-border)' : 'var(--border)'}`,
              }}>
                <div className="flex items-center gap-3 mb-1">
                  <span className="text-xs font-semibold w-8" style={{ color: isToday ? 'var(--gold)' : 'var(--text-primary)' }}>
                    {dayNames[d.getDay()]}
                  </span>
                  <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                    {d.toLocaleDateString([], { month: 'short', day: 'numeric' })}
                  </span>
                  {isToday && <span className="text-[9px] font-bold px-1.5 py-0.5 rounded" style={{ background: 'var(--gold)', color: '#0a0a0a' }}>TODAY</span>}
                </div>
                <p className="text-[10px] pl-11" style={{ color: 'var(--text-muted)' }}>No events scheduled</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════
   TAB: Materials
   ═══════════════════════════════════════════════════════════════ */
function MaterialsTab() {
  const categories = [
    { name: 'Fabrics', icon: '🧵', count: 0, color: '#D4AF37' },
    { name: 'Linings', icon: '📋', count: 0, color: '#8B5CF6' },
    { name: 'Hardware', icon: '🔩', count: 0, color: '#22D3EE' },
    { name: 'Trims', icon: '✂️', count: 0, color: '#D946EF' },
  ];

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      <div className="shrink-0 flex items-center justify-between px-4 py-2" style={{ borderBottom: '1px solid var(--border)' }}>
        <h4 className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>Materials Inventory</h4>
        <button className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold transition"
          style={{ background: 'var(--gold)', color: '#0a0a0a' }}>
          <Plus className="w-3.5 h-3.5" /> Add Material
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {/* Category cards */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          {categories.map(c => (
            <div key={c.name} className="rounded-xl p-4 transition cursor-pointer"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = c.color)}
              onMouseLeave={e => (e.currentTarget.style.borderColor = 'var(--border)')}
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">{c.icon}</span>
                <div>
                  <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{c.name}</p>
                  <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{c.count} items</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Supplier contacts */}
        <div className="rounded-xl p-4" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          <h5 className="text-xs font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Supplier Contacts</h5>
          <p className="text-xs text-center py-4" style={{ color: 'var(--text-muted)' }}>
            Add your fabric suppliers, hardware vendors, and material contacts
          </p>
          <button className="w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition"
            style={{ background: 'var(--raised)', color: 'var(--gold)', border: '1px solid var(--gold-border)' }}>
            <Plus className="w-3 h-3" /> Add Supplier
          </button>
        </div>
      </div>
    </div>
  );
}
