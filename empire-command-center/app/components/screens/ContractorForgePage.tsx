'use client';
import React, { useState, useEffect, useCallback } from 'react';
import {
  Hammer, LayoutDashboard, FolderKanban, Users, CalendarDays, LayoutTemplate,
  FileText, Star, DollarSign, Clock, CheckCircle, Wrench, Zap, TreePine,
  Droplets, Search, Plus, ChevronRight, ArrowUpRight, ArrowDownRight,
  AlertCircle, Eye, BookOpen, CreditCard, Loader2
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';

// ============ API ============

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// ============ NAV ============

const NAV_SECTIONS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'projects', label: 'Projects', icon: FolderKanban },
  { id: 'contractors', label: 'Contractors', icon: Users },
  { id: 'schedule', label: 'Schedule', icon: CalendarDays },
  { id: 'templates', label: 'Templates', icon: LayoutTemplate },
  { id: 'invoices', label: 'Invoices', icon: FileText },
  { id: 'payments', label: 'Payments', icon: CreditCard },
  { id: 'docs', label: 'Docs', icon: BookOpen },
] as const;

type Section = typeof NAV_SECTIONS[number]['id'];

const AMBER = '#d97706';
const AMBER_BG = '#fef3c7';
const AMBER_BORDER = '#fde68a';

// ============ TYPES ============

interface Project {
  id: string;
  name: string;
  client: string;
  contractor: string;
  status: string;
  date: string;
  amount: number;
}

interface Contractor {
  id: string;
  name: string;
  specialty: string;
  rating: number;
  availability: string;
  hourlyRate: number;
  jobsCompleted: number;
}

interface Invoice {
  id: string;
  client: string;
  job: string;
  amount: number;
  status: string;
  date: string;
}

// ============ CONFIG ============

const STATUS_CONFIG: Record<string, { bg: string; color: string; label: string }> = {
  scheduled: { bg: '#dbeafe', color: '#2563eb', label: 'Scheduled' },
  'in-progress': { bg: AMBER_BG, color: AMBER, label: 'In Progress' },
  completed: { bg: '#dcfce7', color: '#16a34a', label: 'Completed' },
  invoiced: { bg: '#ede9fe', color: '#7c3aed', label: 'Invoiced' },
};

const INVOICE_STATUS_CONFIG: Record<string, { bg: string; color: string; label: string }> = {
  draft: { bg: '#f3f4f6', color: '#6b7280', label: 'Draft' },
  sent: { bg: '#dbeafe', color: '#2563eb', label: 'Sent' },
  paid: { bg: '#dcfce7', color: '#16a34a', label: 'Paid' },
  overdue: { bg: '#fee2e2', color: '#dc2626', label: 'Overdue' },
};

const AVAILABILITY_CONFIG: Record<string, { bg: string; color: string }> = {
  Available: { bg: '#dcfce7', color: '#16a34a' },
  'On Job': { bg: AMBER_BG, color: AMBER },
  Off: { bg: '#f3f4f6', color: '#6b7280' },
};

// ============ SHARED COMPONENTS ============

function LoadingSpinner({ message }: { message?: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 48, color: '#999' }}>
      <Loader2 size={28} style={{ animation: 'spin 1s linear infinite', marginBottom: 12 }} />
      <div style={{ fontSize: 12 }}>{message || 'Loading...'}</div>
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 48, color: '#999' }}>
      <AlertCircle size={28} style={{ color: '#dc2626', marginBottom: 12 }} />
      <div style={{ fontSize: 13, fontWeight: 600, color: '#dc2626', marginBottom: 4 }}>Error loading data</div>
      <div style={{ fontSize: 12, color: '#999', marginBottom: 12 }}>{message}</div>
      {onRetry && (
        <button onClick={onRetry} style={{ padding: '6px 16px', borderRadius: 8, fontSize: 12, fontWeight: 600, background: AMBER, color: '#fff', border: 'none', cursor: 'pointer' }}>
          Retry
        </button>
      )}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 48, color: '#999' }}>
      <FolderKanban size={28} style={{ marginBottom: 12, opacity: 0.4 }} />
      <div style={{ fontSize: 12 }}>{message}</div>
    </div>
  );
}

// ============ DATA FETCHING HELPERS ============

function mapJobToProject(job: Record<string, unknown>): Project {
  return {
    id: String(job.id || job.job_id || ''),
    name: String(job.name || job.title || job.job_name || ''),
    client: String(job.client || job.client_name || job.customer || ''),
    contractor: String(job.contractor || job.assigned_to || job.contractor_name || ''),
    status: String(job.status || 'scheduled'),
    date: String(job.date || job.start_date || job.created_at || '').slice(0, 10),
    amount: Number(job.amount || job.total || job.price || 0),
  };
}

function mapContactToContractor(contact: Record<string, unknown>): Contractor {
  return {
    id: String(contact.id || contact.contact_id || ''),
    name: String(contact.name || `${contact.first_name || ''} ${contact.last_name || ''}`.trim() || ''),
    specialty: String(contact.specialty || contact.category || contact.type || 'General'),
    rating: Number(contact.rating || 0),
    availability: String(contact.availability || contact.status || 'Off'),
    hourlyRate: Number(contact.hourly_rate || contact.hourlyRate || contact.rate || 0),
    jobsCompleted: Number(contact.jobs_completed || contact.jobsCompleted || contact.total_jobs || 0),
  };
}

function mapToInvoice(inv: Record<string, unknown>): Invoice {
  return {
    id: String(inv.id || inv.invoice_id || inv.invoice_number || ''),
    client: String(inv.client || inv.client_name || inv.customer || inv.customer_name || ''),
    job: String(inv.job || inv.job_name || inv.description || inv.title || ''),
    amount: Number(inv.amount || inv.total || inv.grand_total || 0),
    status: String(inv.status || 'draft'),
    date: String(inv.date || inv.invoice_date || inv.created_at || '').slice(0, 10),
  };
}

// ============ CUSTOM HOOKS ============

function useProjects() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/jobs/`);
      if (!res.ok) throw new Error(`Failed to fetch projects (${res.status})`);
      const data = await res.json();
      const items = Array.isArray(data) ? data : (data.items || data.jobs || data.results || []);
      setProjects(items.map(mapJobToProject));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setProjects([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);
  return { projects, loading, error, refetch: fetchProjects };
}

function useContractors() {
  const [contractors, setContractors] = useState<Contractor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchContractors = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/contacts/`);
      if (!res.ok) throw new Error(`Failed to fetch contractors (${res.status})`);
      const data = await res.json();
      const items = Array.isArray(data) ? data : (data.items || data.contacts || data.results || []);
      setContractors(items.map(mapContactToContractor));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setContractors([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchContractors(); }, [fetchContractors]);
  return { contractors, loading, error, refetch: fetchContractors };
}

function useInvoices() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchInvoices = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/finance/invoices`);
      if (!res.ok) throw new Error(`Failed to fetch invoices (${res.status})`);
      const data = await res.json();
      const items = Array.isArray(data) ? data : (data.items || data.invoices || data.results || []);
      setInvoices(items.map(mapToInvoice));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setInvoices([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchInvoices(); }, [fetchInvoices]);
  return { invoices, loading, error, refetch: fetchInvoices };
}

// ============ MAIN COMPONENT ============

export default function ContractorForgePage() {
  const [section, setSection] = useState<Section>('dashboard');

  const renderContent = () => {
    switch (section) {
      case 'dashboard': return <DashboardSection onNavigate={setSection} />;
      case 'projects': return <ProjectsSection />;
      case 'contractors': return <ContractorsSection />;
      case 'schedule': return <ScheduleSection />;
      case 'templates': return <TemplatesSection />;
      case 'invoices': return <InvoicesSection />;
      case 'payments': return <PaymentModule product="contractor" />;
      case 'docs': return <div style={{ padding: 24 }}><ProductDocs product="contractor" /></div>;
      default: return <DashboardSection onNavigate={setSection} />;
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      <nav style={{ width: 200, background: '#fff', borderRight: '1px solid #ece8e0', flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '18px 16px', borderBottom: '1px solid #ece8e0' }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: AMBER_BG }}>
              <Hammer size={18} style={{ color: AMBER }} />
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>ContractorForge</div>
              <div style={{ fontSize: 10, color: '#999' }}>Service Business</div>
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto" style={{ padding: '10px 10px' }}>
          <div className="flex flex-col gap-1.5">
            {NAV_SECTIONS.map(nav => {
              const Icon = nav.icon;
              const isActive = section === nav.id;
              return (
                <button key={nav.id}
                  onClick={() => setSection(nav.id)}
                  className="w-full flex items-center gap-3 text-left cursor-pointer transition-all"
                  style={{
                    padding: '10px 14px', borderRadius: 12, fontSize: 13,
                    fontWeight: isActive ? 700 : 500,
                    background: isActive ? AMBER_BG : 'transparent',
                    color: isActive ? AMBER : '#666',
                    border: isActive ? `1.5px solid ${AMBER_BORDER}` : '1.5px solid transparent',
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
      <div className="flex-1 overflow-y-auto" style={{ background: '#f5f2ed' }}>
        {renderContent()}
      </div>
    </div>
  );
}

// ============ KPI CARD ============

function KPI({ icon, iconBg, iconColor, label, value, sub, onClick }: {
  icon: React.ReactNode; iconBg: string; iconColor: string; label: string; value: string; sub: string; onClick?: () => void;
}) {
  return (
    <div onClick={onClick} className="empire-card" style={{ cursor: onClick ? 'pointer' : 'default', padding: '16px 18px' }}>
      <div className="flex items-center gap-3 mb-2">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: iconBg, color: iconColor }}>{icon}</div>
        <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', letterSpacing: 0.5 }}>{label}</div>
      </div>
      <div style={{ fontSize: 22, fontWeight: 800, color: '#1a1a1a', marginBottom: 2 }}>{value}</div>
      <div style={{ fontSize: 11, color: '#999' }}>{sub}</div>
    </div>
  );
}

// ============ STATUS BADGE ============

function StatusBadge({ status, config }: { status: string; config: Record<string, { bg: string; color: string; label: string }> }) {
  const s = config[status] || { bg: '#f3f4f6', color: '#6b7280', label: status };
  return (
    <span style={{ padding: '3px 10px', borderRadius: 99, fontSize: 10, fontWeight: 700, background: s.bg, color: s.color }}>
      {s.label}
    </span>
  );
}

// ============ DASHBOARD ============

function DashboardSection({ onNavigate }: { onNavigate: (s: Section) => void }) {
  const { projects, loading: loadingProjects, error: errorProjects, refetch: refetchProjects } = useProjects();
  const { contractors, loading: loadingContractors, error: errorContractors, refetch: refetchContractors } = useContractors();
  const { invoices, loading: loadingInvoices, error: errorInvoices, refetch: refetchInvoices } = useInvoices();

  const loading = loadingProjects || loadingContractors || loadingInvoices;

  const activeProjects = projects.filter(p => p.status === 'in-progress').length;
  const totalContractors = contractors.length;
  const monthRevenue = invoices.filter(i => i.status === 'paid').reduce((s, i) => s + i.amount, 0);
  const upcomingJobs = projects.filter(p => p.status === 'scheduled').length;

  if (loading) {
    return <LoadingSpinner message="Loading dashboard..." />;
  }

  return (
    <div style={{ padding: '24px 28px', maxWidth: 1100, margin: '0 auto' }}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <div style={{ fontSize: 20, fontWeight: 800, color: '#1a1a1a' }}>ContractorForge Dashboard</div>
          <div style={{ fontSize: 12, color: '#999' }}>Manage projects, contractors, and invoices</div>
        </div>
        <button style={{ padding: '8px 16px', borderRadius: 10, background: AMBER, color: '#fff', fontSize: 12, fontWeight: 700, border: 'none', cursor: 'pointer' }}
          className="flex items-center gap-2">
          <Plus size={14} /> New Project
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPI icon={<FolderKanban size={16} />} iconBg={AMBER_BG} iconColor={AMBER} label="Active Projects" value={String(activeProjects)} sub="currently in progress" onClick={() => onNavigate('projects')} />
        <KPI icon={<Users size={16} />} iconBg="#dbeafe" iconColor="#2563eb" label="Contractors" value={String(totalContractors)} sub={`${contractors.filter(c => c.availability === 'Available').length} available`} onClick={() => onNavigate('contractors')} />
        <KPI icon={<DollarSign size={16} />} iconBg="#dcfce7" iconColor="#16a34a" label="Monthly Revenue" value={`$${monthRevenue.toLocaleString()}`} sub="from paid invoices" onClick={() => onNavigate('invoices')} />
        <KPI icon={<CalendarDays size={16} />} iconBg="#ede9fe" iconColor="#7c3aed" label="Upcoming Jobs" value={String(upcomingJobs)} sub="scheduled this week" onClick={() => onNavigate('schedule')} />
      </div>

      {/* Recent Projects */}
      <div className="grid grid-cols-2 gap-5">
        <div className="empire-card" style={{ padding: '18px 20px' }}>
          <div className="flex items-center justify-between mb-4">
            <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>Recent Projects</div>
            <button onClick={() => onNavigate('projects')} style={{ fontSize: 11, color: AMBER, fontWeight: 600, background: 'none', border: 'none', cursor: 'pointer' }}
              className="flex items-center gap-1">View All <ChevronRight size={12} /></button>
          </div>
          <div className="space-y-2">
            {errorProjects ? (
              <ErrorState message={errorProjects} onRetry={refetchProjects} />
            ) : projects.length === 0 ? (
              <EmptyState message="No projects yet" />
            ) : (
              projects.slice(0, 5).map(p => (
                <div key={p.id} className="flex items-center justify-between" style={{ padding: '10px 12px', borderRadius: 10, background: '#f9f7f4', border: '1px solid #ece8e0' }}>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{p.name}</div>
                    <div style={{ fontSize: 10, color: '#999' }}>{p.client} &middot; {p.contractor}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div style={{ fontSize: 12, fontWeight: 700, color: '#1a1a1a' }}>${p.amount.toLocaleString()}</div>
                    <StatusBadge status={p.status} config={STATUS_CONFIG} />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Contractor Availability */}
        <div className="empire-card" style={{ padding: '18px 20px' }}>
          <div className="flex items-center justify-between mb-4">
            <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>Contractor Availability</div>
            <button onClick={() => onNavigate('contractors')} style={{ fontSize: 11, color: AMBER, fontWeight: 600, background: 'none', border: 'none', cursor: 'pointer' }}
              className="flex items-center gap-1">View All <ChevronRight size={12} /></button>
          </div>
          <div className="space-y-2">
            {errorContractors ? (
              <ErrorState message={errorContractors} onRetry={refetchContractors} />
            ) : contractors.length === 0 ? (
              <EmptyState message="No contractors yet" />
            ) : (
              contractors.map(c => {
                const avail = AVAILABILITY_CONFIG[c.availability] || AVAILABILITY_CONFIG['Off'];
                return (
                  <div key={c.id} className="flex items-center justify-between" style={{ padding: '10px 12px', borderRadius: 10, background: '#f9f7f4', border: '1px solid #ece8e0' }}>
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ background: AMBER_BG, color: AMBER, fontSize: 11, fontWeight: 700 }}>
                        {c.name.split(' ').map(n => n[0]).join('')}
                      </div>
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{c.name}</div>
                        <div style={{ fontSize: 10, color: '#999' }}>{c.specialty}</div>
                      </div>
                    </div>
                    <span style={{ padding: '3px 10px', borderRadius: 99, fontSize: 10, fontWeight: 700, background: avail.bg, color: avail.color }}>
                      {c.availability}
                    </span>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Today's Schedule Preview */}
      <div className="empire-card mt-5" style={{ padding: '18px 20px' }}>
        <div className="flex items-center justify-between mb-4">
          <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>Today&apos;s Schedule</div>
          <button onClick={() => onNavigate('schedule')} style={{ fontSize: 11, color: AMBER, fontWeight: 600, background: 'none', border: 'none', cursor: 'pointer' }}
            className="flex items-center gap-1">Full Week <ChevronRight size={12} /></button>
        </div>
        <div className="flex gap-3">
          {projects.filter(p => p.status === 'in-progress' || p.status === 'scheduled').length === 0 ? (
            <div style={{ fontSize: 12, color: '#999', padding: 16 }}>No jobs scheduled today</div>
          ) : (
            projects.filter(p => p.status === 'in-progress' || p.status === 'scheduled').slice(0, 3).map((p, i) => {
              const colors = [AMBER, '#2563eb', '#16a34a', '#dc2626', '#7c3aed'];
              const color = colors[i % colors.length];
              return (
                <div key={p.id} style={{ padding: '12px 16px', borderRadius: 12, border: `2px solid ${color}20`, background: `${color}08`, flex: 1 }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: color, marginBottom: 4 }}>{p.date}</div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{p.name}</div>
                  <div style={{ fontSize: 11, color: '#999' }}>{p.contractor}</div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

// ============ PROJECTS ============

function ProjectsSection() {
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const { projects, loading, error, refetch } = useProjects();

  const filtered = projects.filter(p => {
    const matchSearch = !search || p.name.toLowerCase().includes(search.toLowerCase()) || p.client.toLowerCase().includes(search.toLowerCase()) || p.contractor.toLowerCase().includes(search.toLowerCase());
    const matchStatus = filterStatus === 'all' || p.status === filterStatus;
    return matchSearch && matchStatus;
  });

  return (
    <div style={{ padding: '24px 28px', maxWidth: 1100, margin: '0 auto' }}>
      <div className="flex items-center justify-between mb-5">
        <div>
          <div style={{ fontSize: 18, fontWeight: 800, color: '#1a1a1a' }}>Projects</div>
          <div style={{ fontSize: 12, color: '#999' }}>{projects.length} total jobs</div>
        </div>
        <button style={{ padding: '8px 16px', borderRadius: 10, background: AMBER, color: '#fff', fontSize: 12, fontWeight: 700, border: 'none', cursor: 'pointer' }}
          className="flex items-center gap-2">
          <Plus size={14} /> New Project
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex items-center gap-2" style={{ background: '#fff', borderRadius: 10, padding: '8px 14px', border: '1px solid #ece8e0', flex: 1 }}>
          <Search size={14} className="text-[#999]" />
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search projects, clients, contractors..."
            style={{ border: 'none', outline: 'none', fontSize: 12, background: 'transparent', width: '100%', color: '#1a1a1a' }} />
        </div>
        <div className="flex gap-1">
          {['all', 'scheduled', 'in-progress', 'completed', 'invoiced'].map(s => (
            <button key={s} onClick={() => setFilterStatus(s)}
              style={{ padding: '6px 12px', borderRadius: 8, fontSize: 11, fontWeight: filterStatus === s ? 700 : 500, background: filterStatus === s ? AMBER_BG : '#fff', color: filterStatus === s ? AMBER : '#666', border: filterStatus === s ? `1px solid ${AMBER_BORDER}` : '1px solid #ece8e0', cursor: 'pointer' }}>
              {s === 'all' ? 'All' : (STATUS_CONFIG[s]?.label || s)}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <LoadingSpinner message="Loading projects..." />
      ) : error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : (
        <div className="empire-card" style={{ padding: 0, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f9f7f4', borderBottom: '1px solid #ece8e0' }}>
                {['Job Name', 'Client', 'Contractor', 'Status', 'Date', 'Amount'].map(h => (
                  <th key={h} style={{ padding: '10px 16px', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', textAlign: 'left', letterSpacing: 0.5 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(p => (
                <tr key={p.id} style={{ borderBottom: '1px solid #f0ede8' }} className="hover:bg-[#f9f7f4] transition-colors">
                  <td style={{ padding: '12px 16px' }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{p.name}</div>
                    <div style={{ fontSize: 10, color: '#999' }}>{p.id}</div>
                  </td>
                  <td style={{ padding: '12px 16px', fontSize: 12, color: '#444' }}>{p.client}</td>
                  <td style={{ padding: '12px 16px', fontSize: 12, color: '#444' }}>{p.contractor}</td>
                  <td style={{ padding: '12px 16px' }}><StatusBadge status={p.status} config={STATUS_CONFIG} /></td>
                  <td style={{ padding: '12px 16px', fontSize: 12, color: '#666' }}>{p.date}</td>
                  <td style={{ padding: '12px 16px', fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>${p.amount.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <div style={{ padding: 32, textAlign: 'center', color: '#999', fontSize: 12 }}>
              {projects.length === 0 ? 'No projects yet' : 'No projects match your filters'}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ============ CONTRACTORS ============

function ContractorsSection() {
  const [search, setSearch] = useState('');
  const { contractors, loading, error, refetch } = useContractors();

  const filtered = contractors.filter(c =>
    !search || c.name.toLowerCase().includes(search.toLowerCase()) || c.specialty.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={{ padding: '24px 28px', maxWidth: 1100, margin: '0 auto' }}>
      <div className="flex items-center justify-between mb-5">
        <div>
          <div style={{ fontSize: 18, fontWeight: 800, color: '#1a1a1a' }}>Contractors</div>
          <div style={{ fontSize: 12, color: '#999' }}>{contractors.length} registered contractors</div>
        </div>
        <button style={{ padding: '8px 16px', borderRadius: 10, background: AMBER, color: '#fff', fontSize: 12, fontWeight: 700, border: 'none', cursor: 'pointer' }}
          className="flex items-center gap-2">
          <Plus size={14} /> Add Contractor
        </button>
      </div>

      <div className="flex items-center gap-2 mb-4" style={{ background: '#fff', borderRadius: 10, padding: '8px 14px', border: '1px solid #ece8e0', maxWidth: 400 }}>
        <Search size={14} className="text-[#999]" />
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search by name or specialty..."
          style={{ border: 'none', outline: 'none', fontSize: 12, background: 'transparent', width: '100%', color: '#1a1a1a' }} />
      </div>

      {loading ? (
        <LoadingSpinner message="Loading contractors..." />
      ) : error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4">
            {filtered.map(c => {
              const avail = AVAILABILITY_CONFIG[c.availability] || AVAILABILITY_CONFIG['Off'];
              return (
                <div key={c.id} className="empire-card" style={{ padding: '18px 20px' }}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: AMBER_BG, color: AMBER, fontSize: 13, fontWeight: 700 }}>
                        {c.name.split(' ').map(n => n[0]).join('')}
                      </div>
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>{c.name}</div>
                        <div style={{ fontSize: 11, color: '#999' }}>{c.specialty}</div>
                      </div>
                    </div>
                    <span style={{ padding: '3px 10px', borderRadius: 99, fontSize: 10, fontWeight: 700, background: avail.bg, color: avail.color }}>
                      {c.availability}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-3" style={{ borderTop: '1px solid #ece8e0', paddingTop: 12 }}>
                    <div>
                      <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999' }}>Rating</div>
                      <div className="flex items-center gap-1" style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>
                        <Star size={12} fill="#d97706" style={{ color: '#d97706' }} /> {c.rating}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999' }}>Rate</div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>${c.hourlyRate}/hr</div>
                    </div>
                    <div>
                      <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999' }}>Jobs Done</div>
                      <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{c.jobsCompleted}</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          {filtered.length === 0 && (
            <div className="empire-card" style={{ padding: 32, textAlign: 'center', color: '#999', fontSize: 12 }}>
              {contractors.length === 0 ? 'No contractors yet' : 'No contractors match your search'}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ============ SCHEDULE ============

function ScheduleSection() {
  return (
    <div style={{ padding: '24px 28px', maxWidth: 1100, margin: '0 auto' }}>
      <div className="flex items-center justify-between mb-5">
        <div>
          <div style={{ fontSize: 18, fontWeight: 800, color: '#1a1a1a' }}>Weekly Schedule</div>
          <div style={{ fontSize: 12, color: '#999' }}>Schedule view</div>
        </div>
      </div>

      <div className="empire-card" style={{ padding: 48, textAlign: 'center' }}>
        <CalendarDays size={32} style={{ color: '#ccc', margin: '0 auto 12px' }} />
        <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>No schedule entries yet</div>
        <div style={{ fontSize: 12, color: '#999' }}>Schedule data will appear here once jobs are assigned dates and times.</div>
      </div>
    </div>
  );
}

// ============ TEMPLATES ============

function TemplatesSection() {
  return (
    <div style={{ padding: '24px 28px', maxWidth: 1100, margin: '0 auto' }}>
      <div className="mb-5">
        <div style={{ fontSize: 18, fontWeight: 800, color: '#1a1a1a' }}>Industry Templates</div>
        <div style={{ fontSize: 12, color: '#999' }}>Pre-configured setups for common service businesses</div>
      </div>

      <div className="empire-card" style={{ padding: 48, textAlign: 'center' }}>
        <LayoutTemplate size={32} style={{ color: '#ccc', margin: '0 auto 12px' }} />
        <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>No templates yet</div>
        <div style={{ fontSize: 12, color: '#999' }}>Templates will be available here once they are configured.</div>
      </div>
    </div>
  );
}

// ============ INVOICES ============

function InvoicesSection() {
  const [search, setSearch] = useState('');
  const { invoices, loading, error, refetch } = useInvoices();

  const filtered = invoices.filter(inv =>
    !search || inv.client.toLowerCase().includes(search.toLowerCase()) || inv.job.toLowerCase().includes(search.toLowerCase()) || inv.id.toLowerCase().includes(search.toLowerCase())
  );

  const totalPaid = invoices.filter(i => i.status === 'paid').reduce((s, i) => s + i.amount, 0);
  const totalOutstanding = invoices.filter(i => i.status === 'sent' || i.status === 'overdue').reduce((s, i) => s + i.amount, 0);

  return (
    <div style={{ padding: '24px 28px', maxWidth: 1100, margin: '0 auto' }}>
      <div className="flex items-center justify-between mb-5">
        <div>
          <div style={{ fontSize: 18, fontWeight: 800, color: '#1a1a1a' }}>Invoices</div>
          <div style={{ fontSize: 12, color: '#999' }}>{invoices.length} invoices &middot; ${totalPaid.toLocaleString()} collected &middot; ${totalOutstanding.toLocaleString()} outstanding</div>
        </div>
        <button style={{ padding: '8px 16px', borderRadius: 10, background: AMBER, color: '#fff', fontSize: 12, fontWeight: 700, border: 'none', cursor: 'pointer' }}
          className="flex items-center gap-2">
          <Plus size={14} /> New Invoice
        </button>
      </div>

      <div className="flex items-center gap-2 mb-4" style={{ background: '#fff', borderRadius: 10, padding: '8px 14px', border: '1px solid #ece8e0', maxWidth: 400 }}>
        <Search size={14} className="text-[#999]" />
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search invoices..."
          style={{ border: 'none', outline: 'none', fontSize: 12, background: 'transparent', width: '100%', color: '#1a1a1a' }} />
      </div>

      {loading ? (
        <LoadingSpinner message="Loading invoices..." />
      ) : error ? (
        <ErrorState message={error} onRetry={refetch} />
      ) : (
        <div className="empire-card" style={{ padding: 0, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f9f7f4', borderBottom: '1px solid #ece8e0' }}>
                {['Invoice ID', 'Client', 'Job', 'Amount', 'Status', 'Date'].map(h => (
                  <th key={h} style={{ padding: '10px 16px', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', color: '#999', textAlign: 'left', letterSpacing: 0.5 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(inv => (
                <tr key={inv.id} style={{ borderBottom: '1px solid #f0ede8' }} className="hover:bg-[#f9f7f4] transition-colors">
                  <td style={{ padding: '12px 16px', fontSize: 12, fontWeight: 600, color: AMBER }}>{inv.id}</td>
                  <td style={{ padding: '12px 16px', fontSize: 12, color: '#444' }}>{inv.client}</td>
                  <td style={{ padding: '12px 16px', fontSize: 12, color: '#444' }}>{inv.job}</td>
                  <td style={{ padding: '12px 16px', fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>${inv.amount.toLocaleString()}</td>
                  <td style={{ padding: '12px 16px' }}><StatusBadge status={inv.status} config={INVOICE_STATUS_CONFIG} /></td>
                  <td style={{ padding: '12px 16px', fontSize: 12, color: '#666' }}>{inv.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <div style={{ padding: 32, textAlign: 'center', color: '#999', fontSize: 12 }}>
              {invoices.length === 0 ? 'No invoices yet' : 'No invoices match your search'}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
