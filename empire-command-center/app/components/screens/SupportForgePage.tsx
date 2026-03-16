'use client';
import { useState, useEffect, useCallback } from 'react';
import {
  Headphones, LayoutDashboard, Ticket, BookOpen, Users, BarChart3,
  Search, Filter, Clock, CheckCircle, AlertTriangle, AlertCircle,
  ArrowUp, ArrowDown, MessageSquare, ThumbsUp, Eye, Star,
  TrendingUp, Loader2, ChevronRight, Hash, Mail, Calendar, FileText, CreditCard,
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';

// ============ API ============

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// ============ TYPES ============

type Tab = 'dashboard' | 'tickets' | 'knowledge' | 'customers' | 'reports' | 'payments' | 'docs';

type Priority = 'low' | 'medium' | 'high' | 'urgent';
type TicketStatus = 'open' | 'progress' | 'resolved' | 'closed';

interface SupportTicket {
  id: string;
  ticket_number: number;
  subject: string;
  customer_id: string;
  assigned_agent_id: string | null;
  priority: Priority;
  status: TicketStatus;
  channel: string;
  tags: string[];
  category: string | null;
  created_at: string;
  updated_at: string | null;
}

interface KBArticle {
  id: string;
  title: string;
  slug: string;
  content: string;
  content_html: string;
  category_id: string | null;
  tags: string[];
  status: string;
  view_count: number;
  helpful_count: number;
  not_helpful_count: number;
  created_at: string;
  updated_at: string | null;
}

interface KBCategory {
  id: string;
  name: string;
  slug: string;
  description: string | null;
}

interface CustomerRecord {
  id: string | number;
  name: string;
  email: string | null;
  phone: string | null;
  company: string | null;
  type: string;
  tags: string[];
  source: string;
  created_at: string;
  updated_at: string | null;
}

// ============ DATA HOOKS ============

function useTickets() {
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    fetch(`${API}/tickets/?per_page=100`)
      .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json(); })
      .then(data => setTickets(data.tickets ?? []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { refresh(); }, [refresh]);
  return { tickets, loading, error, refresh };
}

function useArticles() {
  const [articles, setArticles] = useState<KBArticle[]>([]);
  const [categories, setCategories] = useState<KBCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      fetch(`${API}/kb/articles?per_page=100`).then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json(); }),
      fetch(`${API}/kb/categories`).then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json(); }),
    ])
      .then(([artData, catData]) => {
        setArticles(artData.articles ?? []);
        setCategories(Array.isArray(catData) ? catData : []);
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { refresh(); }, [refresh]);
  return { articles, categories, loading, error, refresh };
}

function useCustomers() {
  const [customers, setCustomers] = useState<CustomerRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    fetch(`${API}/crm/customers?limit=200`)
      .then(r => { if (!r.ok) throw new Error(`${r.status}`); return r.json(); })
      .then(data => setCustomers(data.customers ?? []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { refresh(); }, [refresh]);
  return { customers, loading, error, refresh };
}

// ============ LOADING / ERROR HELPERS ============

function LoadingSpinner({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3" style={{ padding: 48 }}>
      <Loader2 size={28} className="animate-spin" style={{ color: '#7c3aed' }} />
      <span style={{ fontSize: 13, color: '#999' }}>{label || 'Loading...'}</span>
    </div>
  );
}

function ErrorBanner({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-center gap-3" style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 12, padding: '14px 20px' }}>
      <AlertCircle size={18} style={{ color: '#dc2626' }} />
      <span style={{ fontSize: 13, color: '#dc2626', flex: 1 }}>Failed to load data: {message}</span>
      {onRetry && (
        <button onClick={onRetry} style={{ fontSize: 12, fontWeight: 600, color: '#7c3aed', background: 'none', border: 'none', cursor: 'pointer' }}>
          Retry
        </button>
      )}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2" style={{ padding: 48 }}>
      <span style={{ fontSize: 13, color: '#999' }}>{message}</span>
    </div>
  );
}

// ============ CONSTANTS ============

const ACCENT = '#7c3aed';

const PRIORITY_COLORS: Record<Priority, { bg: string; text: string; label: string }> = {
  low:    { bg: '#dcfce7', text: '#16a34a', label: 'Low' },
  medium: { bg: '#fef3c7', text: '#d97706', label: 'Medium' },
  high:   { bg: '#fee2e2', text: '#dc2626', label: 'High' },
  urgent: { bg: '#fce7f3', text: '#be185d', label: 'Urgent' },
};

const STATUS_COLORS: Record<TicketStatus, { bg: string; text: string; label: string }> = {
  open:     { bg: '#dbeafe', text: '#2563eb', label: 'Open' },
  progress: { bg: '#fef3c7', text: '#d97706', label: 'In Progress' },
  resolved: { bg: '#dcfce7', text: '#16a34a', label: 'Resolved' },
  closed:   { bg: '#f3f4f6', text: '#6b7280', label: 'Closed' },
};

// ============ HELPERS ============

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '--';
  return new Date(iso).toLocaleDateString('en-CA');
}

function timeAgo(iso: string | null | undefined): string {
  if (!iso) return '--';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hr${hrs > 1 ? 's' : ''} ago`;
  const days = Math.floor(hrs / 24);
  return `${days} day${days > 1 ? 's' : ''} ago`;
}

function stripHtml(html: string): string {
  if (typeof document !== 'undefined') {
    const tmp = document.createElement('div');
    tmp.innerHTML = html;
    return tmp.textContent || tmp.innerText || '';
  }
  return html.replace(/<[^>]*>/g, '');
}

// ============ HELPER COMPONENTS ============

function StatCard({ label, value, sub, icon: Icon, color }: { label: string; value: string | number; sub?: string; icon: any; color: string }) {
  return (
    <div style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 12, padding: '20px 24px' }}>
      <div className="flex items-center justify-between mb-3">
        <span style={{ fontSize: 13, color: '#777' }}>{label}</span>
        <div style={{ width: 36, height: 36, borderRadius: 10, background: `${color}18`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon size={18} style={{ color }} />
        </div>
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color: '#1a1a1a' }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

function Badge({ bg, text, label }: { bg: string; text: string; label: string }) {
  return (
    <span style={{ background: bg, color: text, fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 99, whiteSpace: 'nowrap' }}>
      {label}
    </span>
  );
}

function PriorityBar({ data }: { data: { label: string; count: number; color: string }[] }) {
  const total = data.reduce((s, d) => s + d.count, 0);
  return (
    <div style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 12, padding: '20px 24px' }}>
      <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Tickets by Priority</div>
      <div className="flex flex-col gap-3">
        {data.map(d => (
          <div key={d.label}>
            <div className="flex items-center justify-between mb-1">
              <span style={{ fontSize: 13, color: '#555' }}>{d.label}</span>
              <span style={{ fontSize: 13, fontWeight: 600 }}>{d.count}</span>
            </div>
            <div style={{ height: 8, background: '#f3f4f6', borderRadius: 99, overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${total ? (d.count / total) * 100 : 0}%`, background: d.color, borderRadius: 99, transition: 'width 0.5s ease' }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============ TAB CONTENT ============

function DashboardTab() {
  const { tickets, loading, error, refresh } = useTickets();

  if (loading) return <LoadingSpinner label="Loading dashboard..." />;
  if (error) return <ErrorBanner message={error} onRetry={refresh} />;

  const openCount = tickets.filter(t => t.status === 'open').length;
  const progressCount = tickets.filter(t => t.status === 'progress').length;
  const resolvedCount = tickets.filter(t => t.status === 'resolved').length;

  const priorityCounts = [
    { label: 'Urgent', count: tickets.filter(t => t.priority === 'urgent').length, color: '#be185d' },
    { label: 'High', count: tickets.filter(t => t.priority === 'high').length, color: '#dc2626' },
    { label: 'Medium', count: tickets.filter(t => t.priority === 'medium').length, color: '#d97706' },
    { label: 'Low', count: tickets.filter(t => t.priority === 'low').length, color: '#16a34a' },
  ];

  const recentTickets = [...tickets].sort((a, b) => (b.created_at || '').localeCompare(a.created_at || '')).slice(0, 5);

  return (
    <div className="flex flex-col gap-6">
      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Open Tickets" value={openCount} sub={`${progressCount} in progress`} icon={Ticket} color={ACCENT} />
        <StatCard label="Avg Response Time" value="--" sub="Calculated from ticket data" icon={Clock} color="#2563eb" />
        <StatCard label="Total Tickets" value={tickets.length} sub={`${resolvedCount} resolved`} icon={Star} color="#d97706" />
        <StatCard label="Resolved" value={resolvedCount} sub={`${tickets.length} total tickets`} icon={CheckCircle} color="#16a34a" />
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Priority Chart */}
        <PriorityBar data={priorityCounts} />

        {/* Recent Tickets */}
        <div style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 12, padding: '20px 24px' }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Recent Tickets</div>
          {recentTickets.length === 0 ? (
            <EmptyState message="No tickets yet." />
          ) : (
            <div className="flex flex-col gap-2">
              {recentTickets.map(t => (
                <div key={t.id} className="flex items-center justify-between" style={{ padding: '8px 0', borderBottom: '1px solid #f3f4f6' }}>
                  <div className="flex items-center gap-3">
                    <Badge {...(PRIORITY_COLORS[t.priority] || PRIORITY_COLORS.medium)} />
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 500 }}>{t.subject}</div>
                      <div style={{ fontSize: 11, color: '#999' }}>TK-{t.ticket_number} - {timeAgo(t.updated_at || t.created_at)}</div>
                    </div>
                  </div>
                  <Badge {...(STATUS_COLORS[t.status] || STATUS_COLORS.open)} />
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function TicketsTab() {
  const { tickets, loading, error, refresh } = useTickets();
  const [search, setSearch] = useState('');
  const [filterPriority, setFilterPriority] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  if (loading) return <LoadingSpinner label="Loading tickets..." />;
  if (error) return <ErrorBanner message={error} onRetry={refresh} />;

  const filtered = tickets.filter(t => {
    const q = search.toLowerCase();
    if (search && !t.subject.toLowerCase().includes(q) && !`TK-${t.ticket_number}`.toLowerCase().includes(q) && !(t.channel || '').toLowerCase().includes(q)) return false;
    if (filterPriority !== 'all' && t.priority !== filterPriority) return false;
    if (filterStatus !== 'all' && t.status !== filterStatus) return false;
    return true;
  });

  return (
    <div className="flex flex-col gap-4">
      {/* Filter Bar */}
      <div className="flex items-center gap-3" style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 12, padding: '12px 20px' }}>
        <div className="flex items-center gap-2 flex-1" style={{ background: '#f5f2ed', borderRadius: 8, padding: '6px 12px' }}>
          <Search size={14} style={{ color: '#999' }} />
          <input
            type="text"
            placeholder="Search tickets by ID, subject, or channel..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ background: 'transparent', border: 'none', outline: 'none', fontSize: 13, width: '100%', color: '#333' }}
          />
        </div>
        <select
          value={filterPriority}
          onChange={e => setFilterPriority(e.target.value)}
          style={{ background: '#f5f2ed', border: 'none', borderRadius: 8, padding: '8px 12px', fontSize: 13, color: '#555', cursor: 'pointer' }}
        >
          <option value="all">All Priorities</option>
          <option value="urgent">Urgent</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
        <select
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
          style={{ background: '#f5f2ed', border: 'none', borderRadius: 8, padding: '8px 12px', fontSize: 13, color: '#555', cursor: 'pointer' }}
        >
          <option value="all">All Statuses</option>
          <option value="open">Open</option>
          <option value="progress">In Progress</option>
          <option value="resolved">Resolved</option>
          <option value="closed">Closed</option>
        </select>
      </div>

      {/* Tickets Table */}
      <div style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 12, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#faf9f7', borderBottom: '1px solid #ece8e0' }}>
              {['ID', 'Subject', 'Channel', 'Priority', 'Status', 'Category', 'Date'].map(h => (
                <th key={h} style={{ padding: '12px 16px', fontSize: 11, fontWeight: 600, color: '#999', textAlign: 'left', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map(t => (
              <tr key={t.id} style={{ borderBottom: '1px solid #f3f4f6' }} className="hover:bg-[#faf9f7] transition-colors cursor-pointer">
                <td style={{ padding: '12px 16px', fontSize: 13, fontWeight: 600, color: ACCENT }}>TK-{t.ticket_number}</td>
                <td style={{ padding: '12px 16px', fontSize: 13, fontWeight: 500 }}>{t.subject}</td>
                <td style={{ padding: '12px 16px', fontSize: 13, color: '#555' }}>{t.channel || '--'}</td>
                <td style={{ padding: '12px 16px' }}><Badge {...(PRIORITY_COLORS[t.priority] || PRIORITY_COLORS.medium)} /></td>
                <td style={{ padding: '12px 16px' }}><Badge {...(STATUS_COLORS[t.status] || STATUS_COLORS.open)} /></td>
                <td style={{ padding: '12px 16px', fontSize: 13, color: '#555' }}>{t.category || '--'}</td>
                <td style={{ padding: '12px 16px', fontSize: 13, color: '#999' }}>{formatDate(t.created_at)}</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={7} style={{ padding: 32, textAlign: 'center', color: '#999', fontSize: 13 }}>
                  {tickets.length === 0 ? 'No tickets yet.' : 'No tickets match your filters.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function KnowledgeBaseTab() {
  const { articles, categories, loading, error, refresh } = useArticles();
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const [search, setSearch] = useState('');

  if (loading) return <LoadingSpinner label="Loading knowledge base..." />;
  if (error) return <ErrorBanner message={error} onRetry={refresh} />;

  const catMap = Object.fromEntries(categories.map(c => [c.id, c.name]));

  const filtered = articles.filter(a => {
    if (activeCategory !== 'all' && a.category_id !== activeCategory) return false;
    if (search && !a.title.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="flex flex-col gap-4">
      {/* Category Tabs + Search */}
      <div className="flex items-center gap-3 flex-wrap" style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 12, padding: '12px 20px' }}>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setActiveCategory('all')}
            style={{
              padding: '6px 14px', borderRadius: 8, fontSize: 13, fontWeight: 500, border: 'none', cursor: 'pointer',
              background: activeCategory === 'all' ? ACCENT : 'transparent',
              color: activeCategory === 'all' ? '#fff' : '#555',
            }}
          >
            All
          </button>
          {categories.map(cat => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              style={{
                padding: '6px 14px', borderRadius: 8, fontSize: 13, fontWeight: 500, border: 'none', cursor: 'pointer',
                background: activeCategory === cat.id ? ACCENT : 'transparent',
                color: activeCategory === cat.id ? '#fff' : '#555',
              }}
            >
              {cat.name}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <div className="flex items-center gap-2" style={{ background: '#f5f2ed', borderRadius: 8, padding: '6px 12px' }}>
          <Search size={14} style={{ color: '#999' }} />
          <input
            type="text"
            placeholder="Search articles..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ background: 'transparent', border: 'none', outline: 'none', fontSize: 13, width: 180, color: '#333' }}
          />
        </div>
      </div>

      {/* Articles Grid */}
      {filtered.length === 0 ? (
        <EmptyState message={articles.length === 0 ? 'No articles yet.' : 'No articles match your search.'} />
      ) : (
        <div className="grid grid-cols-2 gap-4">
          {filtered.map(a => {
            const preview = a.content ? stripHtml(a.content).slice(0, 160) : '';
            const categoryName = a.category_id ? (catMap[a.category_id] || 'Uncategorized') : 'Uncategorized';
            return (
              <div key={a.id} style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 12, padding: '20px 24px', cursor: 'pointer' }} className="hover:shadow-md transition-shadow">
                <div className="flex items-center gap-2 mb-3">
                  <span style={{ background: `${ACCENT}18`, color: ACCENT, fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 99 }}>{categoryName}</span>
                  <span style={{ fontSize: 11, color: '#999' }}>Updated {formatDate(a.updated_at || a.created_at)}</span>
                </div>
                <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 8, color: '#1a1a1a' }}>{a.title}</div>
                <div style={{ fontSize: 13, color: '#777', lineHeight: 1.5, marginBottom: 16 }}>{preview || 'No preview available.'}</div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-1" style={{ fontSize: 12, color: '#999' }}>
                    <Eye size={13} /> {a.view_count.toLocaleString()} views
                  </div>
                  <div className="flex items-center gap-1" style={{ fontSize: 12, color: '#999' }}>
                    <ThumbsUp size={13} /> {a.helpful_count} helpful
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function CustomersTab() {
  const { customers, loading, error, refresh } = useCustomers();
  const [search, setSearch] = useState('');

  if (loading) return <LoadingSpinner label="Loading customers..." />;
  if (error) return <ErrorBanner message={error} onRetry={refresh} />;

  const filtered = customers.filter(c => {
    if (search && !c.name.toLowerCase().includes(search.toLowerCase()) && !(c.email || '').toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3" style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 12, padding: '12px 20px' }}>
        <div className="flex items-center gap-2 flex-1" style={{ background: '#f5f2ed', borderRadius: 8, padding: '6px 12px' }}>
          <Search size={14} style={{ color: '#999' }} />
          <input
            type="text"
            placeholder="Search customers by name or email..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ background: 'transparent', border: 'none', outline: 'none', fontSize: 13, width: '100%', color: '#333' }}
          />
        </div>
      </div>

      <div style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 12, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#faf9f7', borderBottom: '1px solid #ece8e0' }}>
              {['Name', 'Email', 'Phone', 'Company', 'Type', 'Added'].map(h => (
                <th key={h} style={{ padding: '12px 16px', fontSize: 11, fontWeight: 600, color: '#999', textAlign: 'left', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map(c => (
              <tr key={c.id} style={{ borderBottom: '1px solid #f3f4f6' }} className="hover:bg-[#faf9f7] transition-colors cursor-pointer">
                <td style={{ padding: '12px 16px', fontSize: 13, fontWeight: 500 }}>
                  <div className="flex items-center gap-2">
                    <div style={{ width: 28, height: 28, borderRadius: '50%', background: `${ACCENT}18`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Users size={13} style={{ color: ACCENT }} />
                    </div>
                    {c.name}
                  </div>
                </td>
                <td style={{ padding: '12px 16px', fontSize: 13, color: '#555' }}>{c.email || '--'}</td>
                <td style={{ padding: '12px 16px', fontSize: 13, color: '#555' }}>{c.phone || '--'}</td>
                <td style={{ padding: '12px 16px', fontSize: 13, color: '#555' }}>{c.company || '--'}</td>
                <td style={{ padding: '12px 16px' }}>
                  <span style={{ background: '#f3f4f6', color: '#555', fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 99 }}>
                    {c.type}
                  </span>
                </td>
                <td style={{ padding: '12px 16px', fontSize: 13, color: '#999' }}>{formatDate(c.created_at)}</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} style={{ padding: 32, textAlign: 'center', color: '#999', fontSize: 13 }}>
                  {customers.length === 0 ? 'No customers yet.' : 'No customers match your search.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ReportsTab() {
  const resolutionData = [
    { label: 'Under 1 hour', count: 34, pct: 42 },
    { label: '1-4 hours', count: 22, pct: 27 },
    { label: '4-24 hours', count: 18, pct: 22 },
    { label: 'Over 24 hours', count: 7, pct: 9 },
  ];

  const volumeData = [
    { day: 'Mon', count: 12 },
    { day: 'Tue', count: 18 },
    { day: 'Wed', count: 15 },
    { day: 'Thu', count: 22 },
    { day: 'Fri', count: 19 },
    { day: 'Sat', count: 8 },
    { day: 'Sun', count: 5 },
  ];
  const maxVolume = Math.max(...volumeData.map(d => d.count));

  const topIssues = [
    { issue: 'Login / Authentication', count: 28, trend: 'up' as const },
    { issue: 'Billing & Payments', count: 19, trend: 'down' as const },
    { issue: 'API Errors (5xx)', count: 15, trend: 'up' as const },
    { issue: 'Account Settings', count: 11, trend: 'down' as const },
    { issue: 'Performance Issues', count: 8, trend: 'up' as const },
  ];

  return (
    <div className="flex flex-col gap-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Avg Resolution Time" value="2.4 hrs" sub="Target: under 4 hrs" icon={Clock} color={ACCENT} />
        <StatCard label="Total Tickets (Week)" value="81" sub="Up 12% from last week" icon={Ticket} color="#2563eb" />
        <StatCard label="First-Contact Resolution" value="67%" sub="Goal: 75%" icon={CheckCircle} color="#16a34a" />
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Resolution Time */}
        <div style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 12, padding: '20px 24px' }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Resolution Time Breakdown</div>
          <div className="flex flex-col gap-3">
            {resolutionData.map(d => (
              <div key={d.label}>
                <div className="flex items-center justify-between mb-1">
                  <span style={{ fontSize: 13, color: '#555' }}>{d.label}</span>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{d.count} ({d.pct}%)</span>
                </div>
                <div style={{ height: 8, background: '#f3f4f6', borderRadius: 99, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${d.pct}%`, background: ACCENT, borderRadius: 99, transition: 'width 0.5s ease' }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Weekly Volume */}
        <div style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 12, padding: '20px 24px' }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Ticket Volume (This Week)</div>
          <div className="flex items-end gap-3" style={{ height: 140 }}>
            {volumeData.map(d => (
              <div key={d.day} className="flex-1 flex flex-col items-center gap-1">
                <span style={{ fontSize: 11, fontWeight: 600, color: '#555' }}>{d.count}</span>
                <div style={{
                  width: '100%', height: `${(d.count / maxVolume) * 100}%`, minHeight: 8,
                  background: `linear-gradient(180deg, ${ACCENT}, ${ACCENT}88)`, borderRadius: 6,
                }} />
                <span style={{ fontSize: 11, color: '#999' }}>{d.day}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Top Issues */}
      <div style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 12, padding: '20px 24px' }}>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Top Issues</div>
        <div className="flex flex-col gap-2">
          {topIssues.map((issue, i) => (
            <div key={issue.issue} className="flex items-center justify-between" style={{ padding: '10px 0', borderBottom: i < topIssues.length - 1 ? '1px solid #f3f4f6' : 'none' }}>
              <div className="flex items-center gap-3">
                <span style={{ fontSize: 14, fontWeight: 700, color: ACCENT, width: 24 }}>#{i + 1}</span>
                <span style={{ fontSize: 13, fontWeight: 500 }}>{issue.issue}</span>
              </div>
              <div className="flex items-center gap-3">
                <span style={{ fontSize: 13, fontWeight: 600 }}>{issue.count} tickets</span>
                {issue.trend === 'up' ? (
                  <ArrowUp size={14} style={{ color: '#dc2626' }} />
                ) : (
                  <ArrowDown size={14} style={{ color: '#16a34a' }} />
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============ MAIN COMPONENT ============

const NAV_TABS: { id: Tab; label: string; icon: any }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'tickets', label: 'Tickets', icon: Ticket },
  { id: 'knowledge', label: 'Knowledge Base', icon: BookOpen },
  { id: 'customers', label: 'Customers', icon: Users },
  { id: 'reports', label: 'Reports', icon: BarChart3 },
  { id: 'payments', label: 'Payments', icon: CreditCard },
  { id: 'docs', label: 'Docs', icon: FileText },
];

export default function SupportForgePage() {
  const [tab, setTab] = useState<Tab>('dashboard');
  const { tickets: headerTickets } = useTickets();

  const renderTab = () => {
    switch (tab) {
      case 'dashboard': return <DashboardTab />;
      case 'tickets': return <TicketsTab />;
      case 'knowledge': return <KnowledgeBaseTab />;
      case 'customers': return <CustomersTab />;
      case 'reports': return <ReportsTab />;
      case 'payments': return <PaymentModule product="support" />;
      case 'docs': return <div style={{ padding: 24 }}><ProductDocs product="support" /></div>;
    }
  };

  return (
    <div className="h-full flex flex-col overflow-auto" style={{ background: '#f5f2ed' }}>
      {/* Header */}
      <div style={{ background: '#faf9f7', borderBottom: '1px solid #ece8e0', padding: '16px 36px' }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `linear-gradient(135deg, ${ACCENT}, #a855f7)` }}>
              <Headphones size={18} className="text-white" />
            </div>
            <div>
              <div style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a' }}>SupportForge</div>
              <div style={{ fontSize: 12, color: '#999' }}>Customer Support Management</div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div style={{ background: '#dcfce7', color: '#16a34a', fontSize: 12, fontWeight: 600, padding: '4px 12px', borderRadius: 99 }}>
              {headerTickets.filter(t => t.status === 'open').length} Open
            </div>
            <div style={{ background: '#fef3c7', color: '#d97706', fontSize: 12, fontWeight: 600, padding: '4px 12px', borderRadius: 99 }}>
              {headerTickets.filter(t => t.status === 'progress').length} In Progress
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 mt-4">
          {NAV_TABS.map(t => {
            const Icon = t.icon;
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  padding: '8px 16px', borderRadius: 8, fontSize: 13, fontWeight: 500,
                  border: 'none', cursor: 'pointer', transition: 'all 0.15s ease',
                  background: active ? ACCENT : 'transparent',
                  color: active ? '#fff' : '#777',
                }}
              >
                <Icon size={15} />
                {t.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <div style={{ padding: '24px 36px', flex: 1 }}>
        {renderTab()}
      </div>
    </div>
  );
}
