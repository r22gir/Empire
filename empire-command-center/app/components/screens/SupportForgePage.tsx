'use client';
import { useState } from 'react';
import {
  Headphones, LayoutDashboard, Ticket, BookOpen, Users, BarChart3,
  Search, Filter, Clock, CheckCircle, AlertTriangle, AlertCircle,
  ArrowUp, ArrowDown, MessageSquare, ThumbsUp, Eye, Star,
  TrendingUp, Loader2, ChevronRight, Hash, Mail, Calendar, FileText, CreditCard,
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';

// ============ TYPES ============

type Tab = 'dashboard' | 'tickets' | 'knowledge' | 'customers' | 'reports' | 'payments' | 'docs';

type Priority = 'low' | 'medium' | 'high' | 'urgent';
type TicketStatus = 'open' | 'progress' | 'resolved' | 'closed';

interface SupportTicket {
  id: string;
  subject: string;
  customer: string;
  email: string;
  priority: Priority;
  status: TicketStatus;
  assigned: string;
  date: string;
  lastUpdate: string;
}

interface KBArticle {
  id: string;
  title: string;
  preview: string;
  category: string;
  views: number;
  helpful: number;
  updatedAt: string;
}

interface CustomerRecord {
  id: string;
  name: string;
  email: string;
  totalTickets: number;
  satisfaction: number;
  lastContact: string;
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

const KB_CATEGORIES = ['Getting Started', 'Billing', 'Technical', 'Account'];

// ============ MOCK DATA ============

const MOCK_TICKETS: SupportTicket[] = [
  { id: 'TK-1001', subject: "Can't log in", customer: 'Sarah Chen', email: 'sarah@example.com', priority: 'high', status: 'open', assigned: 'MAX', date: '2026-03-09', lastUpdate: '2 min ago' },
  { id: 'TK-1002', subject: 'Billing question', customer: 'James Miller', email: 'james@example.com', priority: 'medium', status: 'progress', assigned: 'Desk 3', date: '2026-03-08', lastUpdate: '1 hr ago' },
  { id: 'TK-1003', subject: 'API 500 errors', customer: 'Priya Patel', email: 'priya@devco.io', priority: 'urgent', status: 'open', assigned: 'MAX', date: '2026-03-09', lastUpdate: '5 min ago' },
  { id: 'TK-1004', subject: 'Feature request', customer: 'Tom Wilson', email: 'tom@startup.co', priority: 'low', status: 'resolved', assigned: 'Desk 7', date: '2026-03-07', lastUpdate: '1 day ago' },
  { id: 'TK-1005', subject: 'Password reset', customer: 'Lisa Park', email: 'lisa@mail.com', priority: 'medium', status: 'open', assigned: 'MAX', date: '2026-03-09', lastUpdate: '20 min ago' },
  { id: 'TK-1006', subject: 'Invoice not received', customer: 'David Kim', email: 'david@corp.net', priority: 'medium', status: 'progress', assigned: 'Desk 3', date: '2026-03-08', lastUpdate: '3 hrs ago' },
  { id: 'TK-1007', subject: 'Dashboard loading slow', customer: 'Emma Davis', email: 'emma@biz.org', priority: 'high', status: 'open', assigned: 'MAX', date: '2026-03-09', lastUpdate: '10 min ago' },
  { id: 'TK-1008', subject: 'Account deletion request', customer: 'Carlos Ruiz', email: 'carlos@web.io', priority: 'low', status: 'closed', assigned: 'Desk 5', date: '2026-03-05', lastUpdate: '4 days ago' },
];

const MOCK_ARTICLES: KBArticle[] = [
  { id: 'kb-1', title: 'Getting Started with EmpireBox', preview: 'Learn how to set up your account, configure your first workspace, and start using the platform in minutes.', category: 'Getting Started', views: 1243, helpful: 89, updatedAt: '2026-03-01' },
  { id: 'kb-2', title: 'Understanding Your Invoice', preview: 'A breakdown of how billing works, what each line item means, and how to update your payment method.', category: 'Billing', views: 876, helpful: 64, updatedAt: '2026-02-28' },
  { id: 'kb-3', title: 'API Authentication Guide', preview: 'How to generate API keys, authenticate requests, and troubleshoot common 401/403 errors.', category: 'Technical', views: 2105, helpful: 152, updatedAt: '2026-03-05' },
  { id: 'kb-4', title: 'Managing Team Members', preview: 'Add, remove, and manage roles for team members in your organization account.', category: 'Account', views: 654, helpful: 41, updatedAt: '2026-02-20' },
  { id: 'kb-5', title: 'Connecting Your Domain', preview: 'Step-by-step guide to pointing your custom domain to EmpireBox via Cloudflare or other DNS providers.', category: 'Getting Started', views: 987, helpful: 73, updatedAt: '2026-03-03' },
  { id: 'kb-6', title: 'Subscription Plans Explained', preview: 'Compare features across Starter, Professional, and Empire plans to find the right fit.', category: 'Billing', views: 1532, helpful: 98, updatedAt: '2026-03-07' },
  { id: 'kb-7', title: 'Webhook Configuration', preview: 'Set up webhooks to receive real-time notifications when events occur in your account.', category: 'Technical', views: 743, helpful: 55, updatedAt: '2026-02-25' },
  { id: 'kb-8', title: 'Two-Factor Authentication Setup', preview: 'Enable 2FA on your account using an authenticator app or SMS for added security.', category: 'Account', views: 1120, helpful: 82, updatedAt: '2026-03-04' },
];

const MOCK_CUSTOMERS: CustomerRecord[] = [
  { id: 'c-1', name: 'Sarah Chen', email: 'sarah@example.com', totalTickets: 3, satisfaction: 4.2, lastContact: '2026-03-09' },
  { id: 'c-2', name: 'James Miller', email: 'james@example.com', totalTickets: 7, satisfaction: 3.8, lastContact: '2026-03-08' },
  { id: 'c-3', name: 'Priya Patel', email: 'priya@devco.io', totalTickets: 12, satisfaction: 4.6, lastContact: '2026-03-09' },
  { id: 'c-4', name: 'Tom Wilson', email: 'tom@startup.co', totalTickets: 2, satisfaction: 5.0, lastContact: '2026-03-07' },
  { id: 'c-5', name: 'Lisa Park', email: 'lisa@mail.com', totalTickets: 1, satisfaction: 4.0, lastContact: '2026-03-09' },
  { id: 'c-6', name: 'David Kim', email: 'david@corp.net', totalTickets: 5, satisfaction: 3.5, lastContact: '2026-03-08' },
  { id: 'c-7', name: 'Emma Davis', email: 'emma@biz.org', totalTickets: 4, satisfaction: 4.4, lastContact: '2026-03-09' },
  { id: 'c-8', name: 'Carlos Ruiz', email: 'carlos@web.io', totalTickets: 1, satisfaction: 4.8, lastContact: '2026-03-05' },
];

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
  const openCount = MOCK_TICKETS.filter(t => t.status === 'open').length;
  const progressCount = MOCK_TICKETS.filter(t => t.status === 'progress').length;
  const resolvedCount = MOCK_TICKETS.filter(t => t.status === 'resolved').length;

  const priorityCounts = [
    { label: 'Urgent', count: MOCK_TICKETS.filter(t => t.priority === 'urgent').length, color: '#be185d' },
    { label: 'High', count: MOCK_TICKETS.filter(t => t.priority === 'high').length, color: '#dc2626' },
    { label: 'Medium', count: MOCK_TICKETS.filter(t => t.priority === 'medium').length, color: '#d97706' },
    { label: 'Low', count: MOCK_TICKETS.filter(t => t.priority === 'low').length, color: '#16a34a' },
  ];

  const recentTickets = [...MOCK_TICKETS].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 5);

  return (
    <div className="flex flex-col gap-6">
      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Open Tickets" value={openCount} sub={`${progressCount} in progress`} icon={Ticket} color={ACCENT} />
        <StatCard label="Avg Response Time" value="12 min" sub="Down 3 min from last week" icon={Clock} color="#2563eb" />
        <StatCard label="Satisfaction Score" value="94%" sub="Based on 156 ratings" icon={Star} color="#d97706" />
        <StatCard label="Resolved Today" value={resolvedCount} sub={`${MOCK_TICKETS.length} total tickets`} icon={CheckCircle} color="#16a34a" />
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Priority Chart */}
        <PriorityBar data={priorityCounts} />

        {/* Recent Tickets */}
        <div style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 12, padding: '20px 24px' }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Recent Tickets</div>
          <div className="flex flex-col gap-2">
            {recentTickets.map(t => (
              <div key={t.id} className="flex items-center justify-between" style={{ padding: '8px 0', borderBottom: '1px solid #f3f4f6' }}>
                <div className="flex items-center gap-3">
                  <Badge {...PRIORITY_COLORS[t.priority]} />
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>{t.subject}</div>
                    <div style={{ fontSize: 11, color: '#999' }}>{t.customer} - {t.lastUpdate}</div>
                  </div>
                </div>
                <Badge {...STATUS_COLORS[t.status]} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function TicketsTab() {
  const [search, setSearch] = useState('');
  const [filterPriority, setFilterPriority] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const filtered = MOCK_TICKETS.filter(t => {
    if (search && !t.subject.toLowerCase().includes(search.toLowerCase()) && !t.customer.toLowerCase().includes(search.toLowerCase()) && !t.id.toLowerCase().includes(search.toLowerCase())) return false;
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
            placeholder="Search tickets by ID, subject, or customer..."
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
              {['ID', 'Subject', 'Customer', 'Priority', 'Status', 'Assigned', 'Date'].map(h => (
                <th key={h} style={{ padding: '12px 16px', fontSize: 11, fontWeight: 600, color: '#999', textAlign: 'left', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map(t => (
              <tr key={t.id} style={{ borderBottom: '1px solid #f3f4f6' }} className="hover:bg-[#faf9f7] transition-colors cursor-pointer">
                <td style={{ padding: '12px 16px', fontSize: 13, fontWeight: 600, color: ACCENT }}>{t.id}</td>
                <td style={{ padding: '12px 16px', fontSize: 13, fontWeight: 500 }}>{t.subject}</td>
                <td style={{ padding: '12px 16px', fontSize: 13, color: '#555' }}>{t.customer}</td>
                <td style={{ padding: '12px 16px' }}><Badge {...PRIORITY_COLORS[t.priority]} /></td>
                <td style={{ padding: '12px 16px' }}><Badge {...STATUS_COLORS[t.status]} /></td>
                <td style={{ padding: '12px 16px', fontSize: 13, color: '#555' }}>{t.assigned}</td>
                <td style={{ padding: '12px 16px', fontSize: 13, color: '#999' }}>{t.date}</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={7} style={{ padding: 32, textAlign: 'center', color: '#999', fontSize: 13 }}>No tickets match your filters.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function KnowledgeBaseTab() {
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const [search, setSearch] = useState('');

  const filtered = MOCK_ARTICLES.filter(a => {
    if (activeCategory !== 'all' && a.category !== activeCategory) return false;
    if (search && !a.title.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="flex flex-col gap-4">
      {/* Category Tabs + Search */}
      <div className="flex items-center gap-3" style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 12, padding: '12px 20px' }}>
        <div className="flex items-center gap-2">
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
          {KB_CATEGORIES.map(cat => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              style={{
                padding: '6px 14px', borderRadius: 8, fontSize: 13, fontWeight: 500, border: 'none', cursor: 'pointer',
                background: activeCategory === cat ? ACCENT : 'transparent',
                color: activeCategory === cat ? '#fff' : '#555',
              }}
            >
              {cat}
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
      <div className="grid grid-cols-2 gap-4">
        {filtered.map(a => (
          <div key={a.id} style={{ background: '#fff', border: '1px solid #ece8e0', borderRadius: 12, padding: '20px 24px', cursor: 'pointer' }} className="hover:shadow-md transition-shadow">
            <div className="flex items-center gap-2 mb-3">
              <span style={{ background: `${ACCENT}18`, color: ACCENT, fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 99 }}>{a.category}</span>
              <span style={{ fontSize: 11, color: '#999' }}>Updated {a.updatedAt}</span>
            </div>
            <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 8, color: '#1a1a1a' }}>{a.title}</div>
            <div style={{ fontSize: 13, color: '#777', lineHeight: 1.5, marginBottom: 16 }}>{a.preview}</div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1" style={{ fontSize: 12, color: '#999' }}>
                <Eye size={13} /> {a.views.toLocaleString()} views
              </div>
              <div className="flex items-center gap-1" style={{ fontSize: 12, color: '#999' }}>
                <ThumbsUp size={13} /> {a.helpful} helpful
              </div>
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <div style={{ gridColumn: '1 / -1', padding: 32, textAlign: 'center', color: '#999', fontSize: 13 }}>No articles match your search.</div>
        )}
      </div>
    </div>
  );
}

function CustomersTab() {
  const [search, setSearch] = useState('');

  const filtered = MOCK_CUSTOMERS.filter(c => {
    if (search && !c.name.toLowerCase().includes(search.toLowerCase()) && !c.email.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const renderStars = (rating: number) => {
    const full = Math.floor(rating);
    return (
      <div className="flex items-center gap-0.5">
        {[...Array(5)].map((_, i) => (
          <Star key={i} size={13} fill={i < full ? '#d97706' : 'none'} style={{ color: i < full ? '#d97706' : '#ddd' }} />
        ))}
        <span style={{ fontSize: 12, color: '#777', marginLeft: 4 }}>{rating.toFixed(1)}</span>
      </div>
    );
  };

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
              {['Name', 'Email', 'Total Tickets', 'Satisfaction', 'Last Contact'].map(h => (
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
                <td style={{ padding: '12px 16px', fontSize: 13, color: '#555' }}>{c.email}</td>
                <td style={{ padding: '12px 16px', fontSize: 13, fontWeight: 600 }}>{c.totalTickets}</td>
                <td style={{ padding: '12px 16px' }}>{renderStars(c.satisfaction)}</td>
                <td style={{ padding: '12px 16px', fontSize: 13, color: '#999' }}>{c.lastContact}</td>
              </tr>
            ))}
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
              {MOCK_TICKETS.filter(t => t.status === 'open').length} Open
            </div>
            <div style={{ background: '#fef3c7', color: '#d97706', fontSize: 12, fontWeight: 600, padding: '4px 12px', borderRadius: 99 }}>
              {MOCK_TICKETS.filter(t => t.status === 'progress').length} In Progress
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
