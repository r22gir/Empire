'use client';
import React, { useState } from 'react';
import {
  Hammer, LayoutDashboard, FolderKanban, Users, CalendarDays, LayoutTemplate,
  FileText, Star, DollarSign, Clock, CheckCircle, Wrench, Zap, TreePine,
  Droplets, Search, Plus, ChevronRight, ArrowUpRight, ArrowDownRight,
  AlertCircle, Eye, BookOpen, CreditCard
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';

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

// ============ MOCK DATA ============

const MOCK_PROJECTS = [
  { id: 'PRJ-001', name: 'Kitchen Rewire', client: 'Sarah Mitchell', contractor: 'Dave Kowalski', status: 'in-progress', date: '2026-03-09', amount: 4800 },
  { id: 'PRJ-002', name: 'Bathroom Remodel Plumbing', client: 'James Chen', contractor: 'Maria Lopez', status: 'scheduled', date: '2026-03-12', amount: 6200 },
  { id: 'PRJ-003', name: 'Backyard Patio Landscaping', client: 'Robert Hartley', contractor: 'Chris Meadows', status: 'completed', date: '2026-03-05', amount: 3500 },
  { id: 'PRJ-004', name: 'Full House Electrical Panel Upgrade', client: 'Linda Nguyen', contractor: 'Dave Kowalski', status: 'invoiced', date: '2026-03-01', amount: 8900 },
  { id: 'PRJ-005', name: 'Commercial HVAC Install', client: 'Apex Office Group', contractor: 'Tony Russo', status: 'in-progress', date: '2026-03-07', amount: 14200 },
  { id: 'PRJ-006', name: 'Deck Repair & Staining', client: 'Emily Watson', contractor: 'Chris Meadows', status: 'scheduled', date: '2026-03-15', amount: 2800 },
  { id: 'PRJ-007', name: 'Emergency Pipe Burst Repair', client: 'Mark Sullivan', contractor: 'Maria Lopez', status: 'completed', date: '2026-03-03', amount: 1200 },
  { id: 'PRJ-008', name: 'Sprinkler System Installation', client: 'Valley HOA', contractor: 'Chris Meadows', status: 'scheduled', date: '2026-03-18', amount: 5600 },
  { id: 'PRJ-009', name: 'Garage Subpanel Wiring', client: 'Tom Fischer', contractor: 'Dave Kowalski', status: 'in-progress', date: '2026-03-08', amount: 3100 },
  { id: 'PRJ-010', name: 'Water Heater Replacement', client: 'Ana Reyes', contractor: 'Maria Lopez', status: 'invoiced', date: '2026-02-28', amount: 2400 },
];

const MOCK_CONTRACTORS = [
  { id: 'C-001', name: 'Dave Kowalski', specialty: 'Electrical', rating: 4.9, availability: 'Available', hourlyRate: 95, jobsCompleted: 187 },
  { id: 'C-002', name: 'Maria Lopez', specialty: 'Plumbing', rating: 4.8, availability: 'On Job', hourlyRate: 85, jobsCompleted: 143 },
  { id: 'C-003', name: 'Chris Meadows', specialty: 'Landscaping', rating: 4.7, availability: 'Available', hourlyRate: 70, jobsCompleted: 112 },
  { id: 'C-004', name: 'Tony Russo', specialty: 'HVAC', rating: 4.6, availability: 'On Job', hourlyRate: 90, jobsCompleted: 98 },
  { id: 'C-005', name: 'Keisha Brown', specialty: 'General Contracting', rating: 4.9, availability: 'Available', hourlyRate: 80, jobsCompleted: 214 },
  { id: 'C-006', name: 'Jorge Ramirez', specialty: 'Roofing', rating: 4.5, availability: 'Off', hourlyRate: 75, jobsCompleted: 76 },
];

const MOCK_INVOICES = [
  { id: 'INV-2001', client: 'Linda Nguyen', job: 'Full House Electrical Panel Upgrade', amount: 8900, status: 'paid', date: '2026-03-02' },
  { id: 'INV-2002', client: 'Robert Hartley', job: 'Backyard Patio Landscaping', amount: 3500, status: 'paid', date: '2026-03-06' },
  { id: 'INV-2003', client: 'Mark Sullivan', job: 'Emergency Pipe Burst Repair', amount: 1200, status: 'overdue', date: '2026-03-04' },
  { id: 'INV-2004', client: 'Ana Reyes', job: 'Water Heater Replacement', amount: 2400, status: 'sent', date: '2026-03-01' },
  { id: 'INV-2005', client: 'Sarah Mitchell', job: 'Kitchen Rewire', amount: 4800, status: 'draft', date: '2026-03-09' },
  { id: 'INV-2006', client: 'Apex Office Group', job: 'Commercial HVAC Install (deposit)', amount: 7100, status: 'paid', date: '2026-02-25' },
  { id: 'INV-2007', client: 'Emily Watson', job: 'Deck Repair & Staining', amount: 2800, status: 'draft', date: '2026-03-15' },
];

const SCHEDULE_DAYS = ['Mon 3/9', 'Tue 3/10', 'Wed 3/11', 'Thu 3/12', 'Fri 3/13', 'Sat 3/14', 'Sun 3/15'];

const MOCK_SCHEDULE: Record<string, { time: string; job: string; contractor: string; color: string }[]> = {
  'Mon 3/9': [
    { time: '8:00 AM', job: 'Kitchen Rewire', contractor: 'Dave Kowalski', color: '#d97706' },
    { time: '9:00 AM', job: 'Commercial HVAC Install', contractor: 'Tony Russo', color: '#2563eb' },
  ],
  'Tue 3/10': [
    { time: '7:30 AM', job: 'Kitchen Rewire', contractor: 'Dave Kowalski', color: '#d97706' },
    { time: '10:00 AM', job: 'Garage Subpanel Wiring', contractor: 'Dave Kowalski', color: '#7c3aed' },
  ],
  'Wed 3/11': [
    { time: '8:00 AM', job: 'Commercial HVAC Install', contractor: 'Tony Russo', color: '#2563eb' },
    { time: '1:00 PM', job: 'Sprinkler System Quote', contractor: 'Chris Meadows', color: '#16a34a' },
  ],
  'Thu 3/12': [
    { time: '9:00 AM', job: 'Bathroom Remodel Plumbing', contractor: 'Maria Lopez', color: '#dc2626' },
    { time: '8:00 AM', job: 'Commercial HVAC Install', contractor: 'Tony Russo', color: '#2563eb' },
  ],
  'Fri 3/13': [
    { time: '8:00 AM', job: 'Bathroom Remodel Plumbing', contractor: 'Maria Lopez', color: '#dc2626' },
    { time: '11:00 AM', job: 'Deck Repair Estimate', contractor: 'Chris Meadows', color: '#16a34a' },
  ],
  'Sat 3/14': [
    { time: '9:00 AM', job: 'Deck Repair & Staining', contractor: 'Chris Meadows', color: '#16a34a' },
  ],
  'Sun 3/15': [],
};

const TEMPLATE_CARDS = [
  { id: 'luxeforge', name: 'LuxeForge', desc: 'High-end home renovation and design-build projects', icon: Star, color: '#b8960c', features: ['Design-build workflows', 'Material sourcing', 'Client mood boards', 'Premium invoicing'] },
  { id: 'electricforge', name: 'ElectricForge', desc: 'Residential & commercial electrical contractors', icon: Zap, color: '#d97706', features: ['Panel schedules', 'Permit tracking', 'Code compliance', 'Load calculations'] },
  { id: 'landscapeforge', name: 'LandscapeForge', desc: 'Landscaping, hardscaping, and irrigation businesses', icon: TreePine, color: '#16a34a', features: ['Seasonal scheduling', 'Property maps', 'Plant inventory', 'Maintenance plans'] },
  { id: 'plumbforge', name: 'PlumbForge', desc: 'Plumbing service and installation companies', icon: Droplets, color: '#2563eb', features: ['Emergency dispatch', 'Parts inventory', 'Fixture specs', 'Warranty tracking'] },
];

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
  const activeProjects = MOCK_PROJECTS.filter(p => p.status === 'in-progress').length;
  const totalContractors = MOCK_CONTRACTORS.length;
  const monthRevenue = MOCK_INVOICES.filter(i => i.status === 'paid').reduce((s, i) => s + i.amount, 0);
  const upcomingJobs = MOCK_PROJECTS.filter(p => p.status === 'scheduled').length;

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
        <KPI icon={<Users size={16} />} iconBg="#dbeafe" iconColor="#2563eb" label="Contractors" value={String(totalContractors)} sub={`${MOCK_CONTRACTORS.filter(c => c.availability === 'Available').length} available`} onClick={() => onNavigate('contractors')} />
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
            {MOCK_PROJECTS.slice(0, 5).map(p => (
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
            ))}
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
            {MOCK_CONTRACTORS.map(c => {
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
            })}
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
          {(MOCK_SCHEDULE['Mon 3/9'] || []).map((s, i) => (
            <div key={i} style={{ padding: '12px 16px', borderRadius: 12, border: `2px solid ${s.color}20`, background: `${s.color}08`, flex: 1 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: s.color, marginBottom: 4 }}>{s.time}</div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{s.job}</div>
              <div style={{ fontSize: 11, color: '#999' }}>{s.contractor}</div>
            </div>
          ))}
          {(!MOCK_SCHEDULE['Mon 3/9'] || MOCK_SCHEDULE['Mon 3/9'].length === 0) && (
            <div style={{ fontSize: 12, color: '#999', padding: 16 }}>No jobs scheduled today</div>
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

  const filtered = MOCK_PROJECTS.filter(p => {
    const matchSearch = !search || p.name.toLowerCase().includes(search.toLowerCase()) || p.client.toLowerCase().includes(search.toLowerCase()) || p.contractor.toLowerCase().includes(search.toLowerCase());
    const matchStatus = filterStatus === 'all' || p.status === filterStatus;
    return matchSearch && matchStatus;
  });

  return (
    <div style={{ padding: '24px 28px', maxWidth: 1100, margin: '0 auto' }}>
      <div className="flex items-center justify-between mb-5">
        <div>
          <div style={{ fontSize: 18, fontWeight: 800, color: '#1a1a1a' }}>Projects</div>
          <div style={{ fontSize: 12, color: '#999' }}>{MOCK_PROJECTS.length} total jobs</div>
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
          <div style={{ padding: 32, textAlign: 'center', color: '#999', fontSize: 12 }}>No projects match your filters</div>
        )}
      </div>
    </div>
  );
}

// ============ CONTRACTORS ============

function ContractorsSection() {
  const [search, setSearch] = useState('');

  const filtered = MOCK_CONTRACTORS.filter(c =>
    !search || c.name.toLowerCase().includes(search.toLowerCase()) || c.specialty.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={{ padding: '24px 28px', maxWidth: 1100, margin: '0 auto' }}>
      <div className="flex items-center justify-between mb-5">
        <div>
          <div style={{ fontSize: 18, fontWeight: 800, color: '#1a1a1a' }}>Contractors</div>
          <div style={{ fontSize: 12, color: '#999' }}>{MOCK_CONTRACTORS.length} registered contractors</div>
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
        <div className="empire-card" style={{ padding: 32, textAlign: 'center', color: '#999', fontSize: 12 }}>No contractors match your search</div>
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
          <div style={{ fontSize: 12, color: '#999' }}>Week of March 9 - 15, 2026</div>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-3">
        {SCHEDULE_DAYS.map(day => {
          const jobs = MOCK_SCHEDULE[day] || [];
          const isToday = day === 'Mon 3/9';
          return (
            <div key={day} className="empire-card" style={{ padding: 0, overflow: 'hidden', border: isToday ? `2px solid ${AMBER}` : undefined }}>
              <div style={{ padding: '10px 12px', background: isToday ? AMBER_BG : '#f9f7f4', borderBottom: '1px solid #ece8e0', textAlign: 'center' }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: isToday ? AMBER : '#666' }}>{day}</div>
                {isToday && <div style={{ fontSize: 8, fontWeight: 700, color: AMBER, textTransform: 'uppercase', marginTop: 2 }}>Today</div>}
              </div>
              <div style={{ padding: 8, minHeight: 120 }}>
                {jobs.length === 0 && (
                  <div style={{ fontSize: 10, color: '#ccc', textAlign: 'center', marginTop: 24 }}>No jobs</div>
                )}
                {jobs.map((j, i) => (
                  <div key={i} style={{ padding: '8px 10px', borderRadius: 8, marginBottom: 6, background: `${j.color}10`, borderLeft: `3px solid ${j.color}` }}>
                    <div style={{ fontSize: 9, fontWeight: 700, color: j.color }}>{j.time}</div>
                    <div style={{ fontSize: 10, fontWeight: 600, color: '#1a1a1a', marginTop: 2 }}>{j.job}</div>
                    <div style={{ fontSize: 9, color: '#999' }}>{j.contractor}</div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
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

      <div className="grid grid-cols-2 gap-5">
        {TEMPLATE_CARDS.map(t => {
          const Icon = t.icon;
          return (
            <div key={t.id} className="empire-card" style={{ padding: '22px 24px', border: `1.5px solid ${t.color}30` }}>
              <div className="flex items-center gap-3 mb-3">
                <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: `${t.color}18` }}>
                  <Icon size={22} style={{ color: t.color }} />
                </div>
                <div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: '#1a1a1a' }}>{t.name}</div>
                  <div style={{ fontSize: 11, color: '#999' }}>{t.desc}</div>
                </div>
              </div>
              <div className="space-y-2 mb-4">
                {t.features.map((f, i) => (
                  <div key={i} className="flex items-center gap-2" style={{ fontSize: 12, color: '#555' }}>
                    <CheckCircle size={13} style={{ color: t.color }} /> {f}
                  </div>
                ))}
              </div>
              <button style={{ width: '100%', padding: '10px 0', borderRadius: 10, background: `${t.color}12`, color: t.color, fontSize: 12, fontWeight: 700, border: `1px solid ${t.color}30`, cursor: 'pointer' }}>
                Activate Template
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============ INVOICES ============

function InvoicesSection() {
  const [search, setSearch] = useState('');

  const filtered = MOCK_INVOICES.filter(inv =>
    !search || inv.client.toLowerCase().includes(search.toLowerCase()) || inv.job.toLowerCase().includes(search.toLowerCase()) || inv.id.toLowerCase().includes(search.toLowerCase())
  );

  const totalPaid = MOCK_INVOICES.filter(i => i.status === 'paid').reduce((s, i) => s + i.amount, 0);
  const totalOutstanding = MOCK_INVOICES.filter(i => i.status === 'sent' || i.status === 'overdue').reduce((s, i) => s + i.amount, 0);

  return (
    <div style={{ padding: '24px 28px', maxWidth: 1100, margin: '0 auto' }}>
      <div className="flex items-center justify-between mb-5">
        <div>
          <div style={{ fontSize: 18, fontWeight: 800, color: '#1a1a1a' }}>Invoices</div>
          <div style={{ fontSize: 12, color: '#999' }}>{MOCK_INVOICES.length} invoices &middot; ${totalPaid.toLocaleString()} collected &middot; ${totalOutstanding.toLocaleString()} outstanding</div>
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
          <div style={{ padding: 32, textAlign: 'center', color: '#999', fontSize: 12 }}>No invoices match your search</div>
        )}
      </div>
    </div>
  );
}
