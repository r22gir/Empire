'use client';
import React, { useState } from 'react';
import {
  Target, LayoutDashboard, Kanban, Users, Megaphone, BarChart3,
  Plus, Search, Phone, Mail, Building, Globe, Share2, Snowflake,
  ArrowRight, DollarSign, TrendingUp, UserPlus, Filter,
  ChevronDown, ChevronUp, Eye, Clock, CheckCircle, XCircle,
  Star, Zap, PieChart, Funnel, BookOpen, CreditCard
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';

// ============ NAV ============

const NAV_SECTIONS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'pipeline', label: 'Pipeline', icon: Kanban },
  { id: 'leads', label: 'Leads', icon: Users },
  { id: 'campaigns', label: 'Campaigns', icon: Megaphone },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'payments', label: 'Payments', icon: CreditCard },
  { id: 'docs', label: 'Docs', icon: BookOpen },
] as const;

type Section = typeof NAV_SECTIONS[number]['id'];

// ============ TYPES ============

type LeadSource = 'website' | 'referral' | 'social' | 'cold';
type LeadStatus = 'new' | 'contacted' | 'qualified' | 'proposal' | 'won' | 'lost';
type CampaignType = 'email' | 'sms' | 'social';
type CampaignStatus = 'active' | 'paused' | 'completed' | 'draft';

interface Lead {
  id: string;
  name: string;
  email: string;
  phone: string;
  company: string;
  source: LeadSource;
  score: number;
  status: LeadStatus;
  value: number;
  date: string;
  daysInStage: number;
}

interface Campaign {
  id: string;
  name: string;
  type: CampaignType;
  status: CampaignStatus;
  sent: number;
  opened: number;
  clicked: number;
  converted: number;
}

// ============ MOCK DATA ============

const MOCK_LEADS: Lead[] = [
  { id: 'L001', name: 'Sarah Chen', email: 'sarah@techvista.io', phone: '(202) 555-0147', company: 'TechVista Solutions', source: 'website', score: 92, status: 'qualified', value: 45000, date: '2026-03-07', daysInStage: 3 },
  { id: 'L002', name: 'Marcus Williams', email: 'marcus@greenleaf.co', phone: '(301) 555-0283', company: 'GreenLeaf Partners', source: 'referral', score: 87, status: 'proposal', value: 78000, date: '2026-03-05', daysInStage: 5 },
  { id: 'L003', name: 'Priya Patel', email: 'priya@novahealth.com', phone: '(703) 555-0391', company: 'Nova Health Systems', source: 'social', score: 74, status: 'contacted', value: 32000, date: '2026-03-08', daysInStage: 2 },
  { id: 'L004', name: 'James O\'Brien', email: 'james@obrien-law.com', phone: '(202) 555-0512', company: 'O\'Brien Legal Group', source: 'cold', score: 45, status: 'new', value: 15000, date: '2026-03-09', daysInStage: 1 },
  { id: 'L005', name: 'Diana Rodriguez', email: 'diana@meridiandev.com', phone: '(571) 555-0644', company: 'Meridian Development', source: 'website', score: 96, status: 'won', value: 120000, date: '2026-02-20', daysInStage: 0 },
  { id: 'L006', name: 'Kevin Nguyen', email: 'kevin@blueocean.tech', phone: '(240) 555-0777', company: 'Blue Ocean Tech', source: 'referral', score: 81, status: 'qualified', value: 55000, date: '2026-03-06', daysInStage: 4 },
  { id: 'L007', name: 'Amanda Foster', email: 'amanda@peakretail.com', phone: '(202) 555-0888', company: 'Peak Retail Group', source: 'social', score: 63, status: 'contacted', value: 28000, date: '2026-03-07', daysInStage: 3 },
  { id: 'L008', name: 'Robert Kim', email: 'robert@capitalcraft.io', phone: '(301) 555-0199', company: 'Capital Craft Studios', source: 'website', score: 88, status: 'proposal', value: 92000, date: '2026-03-01', daysInStage: 8 },
  { id: 'L009', name: 'Lisa Hernandez', email: 'lisa@solarvolt.com', phone: '(703) 555-0321', company: 'SolarVolt Energy', source: 'cold', score: 35, status: 'lost', value: 60000, date: '2026-02-15', daysInStage: 0 },
  { id: 'L010', name: 'Tom Bradley', email: 'tom@urbanbuild.co', phone: '(571) 555-0456', company: 'UrbanBuild Construction', source: 'referral', score: 79, status: 'new', value: 42000, date: '2026-03-09', daysInStage: 1 },
  { id: 'L011', name: 'Rachel Green', email: 'rachel@brightwaters.com', phone: '(202) 555-0567', company: 'Brightwaters Consulting', source: 'website', score: 91, status: 'won', value: 85000, date: '2026-02-25', daysInStage: 0 },
  { id: 'L012', name: 'David Park', email: 'david@nexgenai.io', phone: '(240) 555-0678', company: 'NexGen AI Labs', source: 'social', score: 70, status: 'contacted', value: 38000, date: '2026-03-08', daysInStage: 2 },
];

const MOCK_CAMPAIGNS: Campaign[] = [
  { id: 'C001', name: 'Spring LLC Formation Push', type: 'email', status: 'active', sent: 2450, opened: 892, clicked: 234, converted: 18 },
  { id: 'C002', name: 'Referral Partner Outreach', type: 'email', status: 'active', sent: 580, opened: 312, clicked: 89, converted: 12 },
  { id: 'C003', name: 'Tax Season Reminder', type: 'sms', status: 'completed', sent: 1200, opened: 1080, clicked: 156, converted: 24 },
  { id: 'C004', name: 'LinkedIn B2B Campaign', type: 'social', status: 'active', sent: 3200, opened: 1450, clicked: 420, converted: 31 },
  { id: 'C005', name: 'Cold Outreach — Real Estate', type: 'email', status: 'paused', sent: 850, opened: 204, clicked: 38, converted: 3 },
  { id: 'C006', name: 'New Service Announcement', type: 'sms', status: 'draft', sent: 0, opened: 0, clicked: 0, converted: 0 },
];

// ============ HELPERS ============

const ACCENT = '#16a34a';
const ACCENT_BG = '#dcfce7';
const ACCENT_BORDER = '#bbf7d0';

const SOURCE_CONFIG: Record<LeadSource, { icon: React.ElementType; color: string; bg: string; label: string }> = {
  website: { icon: Globe, color: '#2563eb', bg: '#dbeafe', label: 'Website' },
  referral: { icon: Users, color: '#7c3aed', bg: '#ede9fe', label: 'Referral' },
  social: { icon: Share2, color: '#ec4899', bg: '#fce7f3', label: 'Social' },
  cold: { icon: Snowflake, color: '#6b7280', bg: '#f3f4f6', label: 'Cold' },
};

const STATUS_CONFIG: Record<LeadStatus, { color: string; bg: string; label: string }> = {
  new: { color: '#2563eb', bg: '#dbeafe', label: 'New' },
  contacted: { color: '#b8960c', bg: '#fdf8eb', label: 'Contacted' },
  qualified: { color: '#7c3aed', bg: '#ede9fe', label: 'Qualified' },
  proposal: { color: '#ea580c', bg: '#fff7ed', label: 'Proposal' },
  won: { color: '#16a34a', bg: '#dcfce7', label: 'Won' },
  lost: { color: '#dc2626', bg: '#fee2e2', label: 'Lost' },
};

const CAMPAIGN_STATUS_CONFIG: Record<CampaignStatus, { color: string; bg: string; label: string }> = {
  active: { color: '#16a34a', bg: '#dcfce7', label: 'Active' },
  paused: { color: '#b8960c', bg: '#fdf8eb', label: 'Paused' },
  completed: { color: '#2563eb', bg: '#dbeafe', label: 'Completed' },
  draft: { color: '#6b7280', bg: '#f3f4f6', label: 'Draft' },
};

const CAMPAIGN_TYPE_CONFIG: Record<CampaignType, { color: string; label: string }> = {
  email: { color: '#2563eb', label: 'Email' },
  sms: { color: '#16a34a', label: 'SMS' },
  social: { color: '#ec4899', label: 'Social' },
};

function scoreColor(score: number): { color: string; bg: string } {
  if (score >= 80) return { color: '#16a34a', bg: '#dcfce7' };
  if (score >= 60) return { color: '#b8960c', bg: '#fdf8eb' };
  if (score >= 40) return { color: '#ea580c', bg: '#fff7ed' };
  return { color: '#dc2626', bg: '#fee2e2' };
}

function formatCurrency(v: number): string {
  return '$' + v.toLocaleString();
}

// ============ KPI CARD ============

function KPI({ icon, iconBg, iconColor, label, value, sub }: {
  icon: React.ReactNode; iconBg: string; iconColor: string; label: string; value: string; sub: string;
}) {
  return (
    <div className="empire-card" style={{ padding: '16px 18px' }}>
      <div className="flex items-center gap-3 mb-2">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: iconBg, color: iconColor }}>{icon}</div>
        <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, color: '#999' }}>{label}</span>
      </div>
      <div style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a' }}>{value}</div>
      <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>{sub}</div>
    </div>
  );
}

// ============ STATUS BADGE ============

function Badge({ label, color, bg }: { label: string; color: string; bg: string }) {
  return (
    <span style={{
      display: 'inline-block', padding: '3px 10px', borderRadius: 99,
      fontSize: 11, fontWeight: 600, color, background: bg,
    }}>{label}</span>
  );
}

// ============ DASHBOARD SECTION ============

function DashboardSection() {
  const totalLeads = MOCK_LEADS.length;
  const wonLeads = MOCK_LEADS.filter(l => l.status === 'won').length;
  const conversionRate = Math.round((wonLeads / totalLeads) * 100);
  const pipelineValue = MOCK_LEADS.filter(l => !['won', 'lost'].includes(l.status)).reduce((s, l) => s + l.value, 0);
  const totalWonValue = MOCK_LEADS.filter(l => l.status === 'won').reduce((s, l) => s + l.value, 0);

  const sourceCounts = MOCK_LEADS.reduce((acc, l) => {
    acc[l.source] = (acc[l.source] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const recentLeads = [...MOCK_LEADS].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 5);

  return (
    <div style={{ padding: 24 }}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a' }}>LeadForge Dashboard</h1>
          <p style={{ fontSize: 12, color: '#999', marginTop: 2 }}>Lead generation and pipeline management</p>
        </div>
        <button className="empire-btn" style={{ background: ACCENT, color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 10, fontSize: 13, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
          <Plus size={15} /> Add Lead
        </button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPI icon={<Users size={17} />} iconBg={ACCENT_BG} iconColor={ACCENT} label="Total Leads" value={totalLeads.toString()} sub="+3 this week" />
        <KPI icon={<TrendingUp size={17} />} iconBg="#dbeafe" iconColor="#2563eb" label="Conversion Rate" value={`${conversionRate}%`} sub={`${wonLeads} of ${totalLeads} converted`} />
        <KPI icon={<DollarSign size={17} />} iconBg="#fdf8eb" iconColor="#b8960c" label="Pipeline Value" value={formatCurrency(pipelineValue)} sub={`${MOCK_LEADS.filter(l => !['won', 'lost'].includes(l.status)).length} active deals`} />
        <KPI icon={<CheckCircle size={17} />} iconBg="#ede9fe" iconColor="#7c3aed" label="Won Revenue" value={formatCurrency(totalWonValue)} sub="Closed deals" />
      </div>

      {/* Leads by Source + Recent Leads */}
      <div className="grid grid-cols-2 gap-4">
        {/* Leads by Source */}
        <div className="empire-card" style={{ padding: '18px 20px' }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }}>Leads by Source</h3>
          <div className="flex flex-col gap-3">
            {(Object.keys(SOURCE_CONFIG) as LeadSource[]).map(src => {
              const cfg = SOURCE_CONFIG[src];
              const Icon = cfg.icon;
              const count = sourceCounts[src] || 0;
              const pct = Math.round((count / totalLeads) * 100);
              return (
                <div key={src} className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: cfg.bg, color: cfg.color }}>
                    <Icon size={15} />
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between mb-1">
                      <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{cfg.label}</span>
                      <span style={{ fontSize: 12, fontWeight: 700, color: cfg.color }}>{count} ({pct}%)</span>
                    </div>
                    <div style={{ height: 6, borderRadius: 3, background: '#f3f4f6', overflow: 'hidden' }}>
                      <div style={{ width: `${pct}%`, height: '100%', borderRadius: 3, background: cfg.color, transition: 'width 0.5s' }} />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Recent Leads */}
        <div className="empire-card" style={{ padding: '18px 20px' }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }}>Recent Leads</h3>
          <div className="flex flex-col gap-2">
            {recentLeads.map(lead => (
              <div key={lead.id} className="flex items-center gap-3" style={{ padding: '8px 10px', borderRadius: 8, background: '#fafaf8' }}>
                <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ background: ACCENT_BG, color: ACCENT, fontSize: 12, fontWeight: 700 }}>
                  {lead.name.split(' ').map(n => n[0]).join('')}
                </div>
                <div className="flex-1 min-w-0">
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{lead.name}</div>
                  <div style={{ fontSize: 10, color: '#999' }}>{lead.company}</div>
                </div>
                <Badge {...STATUS_CONFIG[lead.status]} />
                <span style={{ fontSize: 12, fontWeight: 700, color: '#1a1a1a' }}>{formatCurrency(lead.value)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============ PIPELINE SECTION ============

function PipelineSection() {
  const columns: { status: LeadStatus; label: string; color: string }[] = [
    { status: 'new', label: 'New', color: '#2563eb' },
    { status: 'contacted', label: 'Contacted', color: '#b8960c' },
    { status: 'qualified', label: 'Qualified', color: '#7c3aed' },
    { status: 'proposal', label: 'Proposal', color: '#ea580c' },
    { status: 'won', label: 'Won', color: '#16a34a' },
    { status: 'lost', label: 'Lost', color: '#dc2626' },
  ];

  return (
    <div style={{ padding: 24 }}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a' }}>Pipeline</h1>
          <p style={{ fontSize: 12, color: '#999', marginTop: 2 }}>Visual kanban view of your sales pipeline</p>
        </div>
      </div>

      <div className="flex gap-3" style={{ overflowX: 'auto', paddingBottom: 8 }}>
        {columns.map(col => {
          const leads = MOCK_LEADS.filter(l => l.status === col.status);
          const colValue = leads.reduce((s, l) => s + l.value, 0);
          return (
            <div key={col.status} style={{ minWidth: 220, flex: '1 0 220px' }}>
              {/* Column header */}
              <div className="flex items-center justify-between mb-3" style={{ padding: '0 4px' }}>
                <div className="flex items-center gap-2">
                  <div style={{ width: 8, height: 8, borderRadius: 4, background: col.color }} />
                  <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{col.label}</span>
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#999', background: '#f3f4f6', padding: '1px 7px', borderRadius: 99 }}>{leads.length}</span>
                </div>
                <span style={{ fontSize: 10, fontWeight: 600, color: col.color }}>{formatCurrency(colValue)}</span>
              </div>

              {/* Cards */}
              <div className="flex flex-col gap-2">
                {leads.length === 0 && (
                  <div style={{ padding: 20, textAlign: 'center', color: '#ccc', fontSize: 11, border: '2px dashed #e5e7eb', borderRadius: 10 }}>
                    No leads
                  </div>
                )}
                {leads.map(lead => {
                  const srcCfg = SOURCE_CONFIG[lead.source];
                  const SrcIcon = srcCfg.icon;
                  return (
                    <div key={lead.id} className="empire-card" style={{ padding: '14px 16px', cursor: 'pointer' }}
                      onMouseEnter={e => { e.currentTarget.style.borderColor = col.color; e.currentTarget.style.boxShadow = `0 2px 8px ${col.color}20`; }}
                      onMouseLeave={e => { e.currentTarget.style.borderColor = '#ece8e0'; e.currentTarget.style.boxShadow = 'none'; }}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-6 h-6 rounded-full flex items-center justify-center" style={{ background: ACCENT_BG, color: ACCENT, fontSize: 9, fontWeight: 700 }}>
                          {lead.name.split(' ').map(n => n[0]).join('')}
                        </div>
                        <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a', flex: 1 }}>{lead.name}</span>
                      </div>
                      <div style={{ fontSize: 11, color: '#666', marginBottom: 6 }}>{lead.company}</div>
                      <div className="flex items-center justify-between">
                        <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{formatCurrency(lead.value)}</span>
                        <div className="flex items-center gap-2">
                          <span style={{ fontSize: 9, padding: '2px 6px', borderRadius: 6, background: srcCfg.bg, color: srcCfg.color, fontWeight: 600 }}>
                            {srcCfg.label}
                          </span>
                        </div>
                      </div>
                      {lead.daysInStage > 0 && (
                        <div className="flex items-center gap-1 mt-2" style={{ fontSize: 10, color: '#999' }}>
                          <Clock size={10} /> {lead.daysInStage}d in stage
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============ LEADS SECTION ============

function LeadsSection() {
  const [search, setSearch] = useState('');
  const [filterSource, setFilterSource] = useState<LeadSource | 'all'>('all');
  const [filterStatus, setFilterStatus] = useState<LeadStatus | 'all'>('all');
  const [sortField, setSortField] = useState<'score' | 'date' | 'value'>('date');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  let filtered = MOCK_LEADS.filter(l => {
    if (search && !l.name.toLowerCase().includes(search.toLowerCase()) && !l.company.toLowerCase().includes(search.toLowerCase()) && !l.email.toLowerCase().includes(search.toLowerCase())) return false;
    if (filterSource !== 'all' && l.source !== filterSource) return false;
    if (filterStatus !== 'all' && l.status !== filterStatus) return false;
    return true;
  });

  filtered.sort((a, b) => {
    const m = sortDir === 'asc' ? 1 : -1;
    if (sortField === 'score') return (a.score - b.score) * m;
    if (sortField === 'value') return (a.value - b.value) * m;
    return a.date.localeCompare(b.date) * m;
  });

  const toggleSort = (field: 'score' | 'date' | 'value') => {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('desc'); }
  };

  const SortIcon = ({ field }: { field: 'score' | 'date' | 'value' }) => {
    if (sortField !== field) return null;
    return sortDir === 'desc' ? <ChevronDown size={12} /> : <ChevronUp size={12} />;
  };

  return (
    <div style={{ padding: 24 }}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a' }}>Leads</h1>
          <p style={{ fontSize: 12, color: '#999', marginTop: 2 }}>{filtered.length} leads found</p>
        </div>
        <button className="empire-btn" style={{ background: ACCENT, color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 10, fontSize: 13, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
          <Plus size={15} /> Add Lead
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <div style={{ position: 'relative', flex: 1, maxWidth: 300 }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#999' }} />
          <input
            type="text" placeholder="Search leads..." value={search} onChange={e => setSearch(e.target.value)}
            style={{ width: '100%', padding: '8px 12px 8px 32px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 12, background: '#fff', outline: 'none' }}
          />
        </div>
        <select value={filterSource} onChange={e => setFilterSource(e.target.value as any)}
          style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 12, background: '#fff', cursor: 'pointer' }}>
          <option value="all">All Sources</option>
          <option value="website">Website</option>
          <option value="referral">Referral</option>
          <option value="social">Social</option>
          <option value="cold">Cold</option>
        </select>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value as any)}
          style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #ece8e0', fontSize: 12, background: '#fff', cursor: 'pointer' }}>
          <option value="all">All Statuses</option>
          <option value="new">New</option>
          <option value="contacted">Contacted</option>
          <option value="qualified">Qualified</option>
          <option value="proposal">Proposal</option>
          <option value="won">Won</option>
          <option value="lost">Lost</option>
        </select>
      </div>

      {/* Table */}
      <div className="empire-card" style={{ overflow: 'hidden' }}>
        <table className="empire-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #ece8e0' }}>
              <th style={thStyle}>Name</th>
              <th style={thStyle}>Email</th>
              <th style={thStyle}>Phone</th>
              <th style={thStyle}>Company</th>
              <th style={thStyle}>Source</th>
              <th style={{ ...thStyle, cursor: 'pointer' }} onClick={() => toggleSort('score')}>
                <span className="flex items-center gap-1">Score <SortIcon field="score" /></span>
              </th>
              <th style={thStyle}>Status</th>
              <th style={{ ...thStyle, cursor: 'pointer' }} onClick={() => toggleSort('value')}>
                <span className="flex items-center gap-1">Value <SortIcon field="value" /></span>
              </th>
              <th style={{ ...thStyle, cursor: 'pointer' }} onClick={() => toggleSort('date')}>
                <span className="flex items-center gap-1">Date <SortIcon field="date" /></span>
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(lead => {
              const srcCfg = SOURCE_CONFIG[lead.source];
              const SrcIcon = srcCfg.icon;
              const sc = scoreColor(lead.score);
              const stCfg = STATUS_CONFIG[lead.status];
              return (
                <tr key={lead.id} style={{ borderBottom: '1px solid #f3f4f6' }}
                  onMouseEnter={e => { e.currentTarget.style.background = '#fafaf8'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
                >
                  <td style={tdStyle}>
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full flex items-center justify-center" style={{ background: ACCENT_BG, color: ACCENT, fontSize: 10, fontWeight: 700, flexShrink: 0 }}>
                        {lead.name.split(' ').map(n => n[0]).join('')}
                      </div>
                      <span style={{ fontWeight: 600 }}>{lead.name}</span>
                    </div>
                  </td>
                  <td style={tdStyle}><span style={{ color: '#666' }}>{lead.email}</span></td>
                  <td style={tdStyle}><span style={{ color: '#666' }}>{lead.phone}</span></td>
                  <td style={tdStyle}><span style={{ fontWeight: 500 }}>{lead.company}</span></td>
                  <td style={tdStyle}>
                    <span className="flex items-center gap-1" style={{ fontSize: 11, padding: '2px 8px', borderRadius: 6, background: srcCfg.bg, color: srcCfg.color, fontWeight: 600, display: 'inline-flex' }}>
                      <SrcIcon size={11} /> {srcCfg.label}
                    </span>
                  </td>
                  <td style={tdStyle}>
                    <span style={{ fontSize: 12, fontWeight: 700, padding: '3px 10px', borderRadius: 99, background: sc.bg, color: sc.color }}>
                      {lead.score}
                    </span>
                  </td>
                  <td style={tdStyle}><Badge {...stCfg} /></td>
                  <td style={tdStyle}><span style={{ fontWeight: 600 }}>{formatCurrency(lead.value)}</span></td>
                  <td style={tdStyle}><span style={{ color: '#999' }}>{lead.date}</span></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const thStyle: React.CSSProperties = {
  textAlign: 'left', padding: '10px 12px', fontSize: 10, fontWeight: 700,
  textTransform: 'uppercase', letterSpacing: 0.8, color: '#999',
};
const tdStyle: React.CSSProperties = {
  padding: '10px 12px', fontSize: 12, color: '#1a1a1a', whiteSpace: 'nowrap',
};

// ============ CAMPAIGNS SECTION ============

function CampaignsSection() {
  return (
    <div style={{ padding: 24 }}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a' }}>Campaigns</h1>
          <p style={{ fontSize: 12, color: '#999', marginTop: 2 }}>Email, SMS, and social outreach campaigns</p>
        </div>
        <button className="empire-btn" style={{ background: ACCENT, color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 10, fontSize: 13, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}>
          <Plus size={15} /> New Campaign
        </button>
      </div>

      {/* Summary KPIs */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPI icon={<Megaphone size={17} />} iconBg={ACCENT_BG} iconColor={ACCENT} label="Active Campaigns" value={MOCK_CAMPAIGNS.filter(c => c.status === 'active').length.toString()} sub="Running now" />
        <KPI icon={<Mail size={17} />} iconBg="#dbeafe" iconColor="#2563eb" label="Total Sent" value={MOCK_CAMPAIGNS.reduce((s, c) => s + c.sent, 0).toLocaleString()} sub="All campaigns" />
        <KPI icon={<Eye size={17} />} iconBg="#fdf8eb" iconColor="#b8960c" label="Avg Open Rate" value={`${Math.round((MOCK_CAMPAIGNS.filter(c => c.sent > 0).reduce((s, c) => s + (c.opened / c.sent), 0) / MOCK_CAMPAIGNS.filter(c => c.sent > 0).length) * 100)}%`} sub="Across active" />
        <KPI icon={<CheckCircle size={17} />} iconBg="#ede9fe" iconColor="#7c3aed" label="Total Converted" value={MOCK_CAMPAIGNS.reduce((s, c) => s + c.converted, 0).toString()} sub="From all campaigns" />
      </div>

      {/* Table */}
      <div className="empire-card" style={{ overflow: 'hidden' }}>
        <table className="empire-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #ece8e0' }}>
              <th style={thStyle}>Campaign</th>
              <th style={thStyle}>Type</th>
              <th style={thStyle}>Status</th>
              <th style={thStyle}>Sent</th>
              <th style={thStyle}>Opened</th>
              <th style={thStyle}>Clicked</th>
              <th style={thStyle}>Converted</th>
              <th style={thStyle}>Conv. Rate</th>
            </tr>
          </thead>
          <tbody>
            {MOCK_CAMPAIGNS.map(camp => {
              const typeCfg = CAMPAIGN_TYPE_CONFIG[camp.type];
              const stCfg = CAMPAIGN_STATUS_CONFIG[camp.status];
              const convRate = camp.sent > 0 ? ((camp.converted / camp.sent) * 100).toFixed(1) : '0.0';
              return (
                <tr key={camp.id} style={{ borderBottom: '1px solid #f3f4f6' }}
                  onMouseEnter={e => { e.currentTarget.style.background = '#fafaf8'; }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
                >
                  <td style={tdStyle}><span style={{ fontWeight: 600 }}>{camp.name}</span></td>
                  <td style={tdStyle}>
                    <span style={{ fontSize: 11, fontWeight: 600, color: typeCfg.color }}>{typeCfg.label}</span>
                  </td>
                  <td style={tdStyle}><Badge {...stCfg} /></td>
                  <td style={tdStyle}>{camp.sent.toLocaleString()}</td>
                  <td style={tdStyle}>{camp.opened.toLocaleString()}</td>
                  <td style={tdStyle}>{camp.clicked.toLocaleString()}</td>
                  <td style={tdStyle}><span style={{ fontWeight: 700, color: ACCENT }}>{camp.converted}</span></td>
                  <td style={tdStyle}>
                    <span style={{ fontWeight: 600, color: parseFloat(convRate) >= 2 ? ACCENT : '#b8960c' }}>{convRate}%</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ============ ANALYTICS SECTION ============

function AnalyticsSection() {
  const totalLeads = MOCK_LEADS.length;
  const sourceCounts = MOCK_LEADS.reduce((acc, l) => {
    acc[l.source] = (acc[l.source] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Funnel data
  const funnelStages = [
    { label: 'Total Leads', count: totalLeads, color: '#2563eb' },
    { label: 'Contacted', count: MOCK_LEADS.filter(l => !['new'].includes(l.status)).length, color: '#b8960c' },
    { label: 'Qualified', count: MOCK_LEADS.filter(l => ['qualified', 'proposal', 'won'].includes(l.status)).length, color: '#7c3aed' },
    { label: 'Proposal', count: MOCK_LEADS.filter(l => ['proposal', 'won'].includes(l.status)).length, color: '#ea580c' },
    { label: 'Won', count: MOCK_LEADS.filter(l => l.status === 'won').length, color: '#16a34a' },
  ];

  // Revenue by source
  const revenueBySource = MOCK_LEADS.filter(l => l.status === 'won').reduce((acc, l) => {
    acc[l.source] = (acc[l.source] || 0) + l.value;
    return acc;
  }, {} as Record<string, number>);
  const totalRevenue = Object.values(revenueBySource).reduce((s, v) => s + v, 0);

  return (
    <div style={{ padding: 24 }}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: '#1a1a1a' }}>Analytics</h1>
          <p style={{ fontSize: 12, color: '#999', marginTop: 2 }}>Lead performance and revenue attribution</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Lead Sources Pie (visual bar representation) */}
        <div className="empire-card" style={{ padding: '20px 22px' }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>Lead Sources Distribution</h3>
          <p style={{ fontSize: 11, color: '#999', marginBottom: 16 }}>Where your leads come from</p>

          {/* Visual pie chart using CSS */}
          <div className="flex items-center gap-6">
            <div style={{ width: 140, height: 140, borderRadius: '50%', position: 'relative', flexShrink: 0,
              background: (() => {
                const sources = Object.entries(sourceCounts);
                let gradientParts: string[] = [];
                let cumPct = 0;
                sources.forEach(([src, count]) => {
                  const pct = (count / totalLeads) * 100;
                  const cfg = SOURCE_CONFIG[src as LeadSource];
                  gradientParts.push(`${cfg.color} ${cumPct}% ${cumPct + pct}%`);
                  cumPct += pct;
                });
                return `conic-gradient(${gradientParts.join(', ')})`;
              })()
            }}>
              <div style={{ position: 'absolute', inset: 30, borderRadius: '50%', background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <span style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a' }}>{totalLeads}</span>
              </div>
            </div>
            <div className="flex flex-col gap-3 flex-1">
              {(Object.keys(SOURCE_CONFIG) as LeadSource[]).map(src => {
                const cfg = SOURCE_CONFIG[src];
                const count = sourceCounts[src] || 0;
                return (
                  <div key={src} className="flex items-center gap-2">
                    <div style={{ width: 10, height: 10, borderRadius: 3, background: cfg.color, flexShrink: 0 }} />
                    <span style={{ fontSize: 12, color: '#666', flex: 1 }}>{cfg.label}</span>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#1a1a1a' }}>{count}</span>
                    <span style={{ fontSize: 11, color: '#999' }}>({Math.round((count / totalLeads) * 100)}%)</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Conversion Funnel */}
        <div className="empire-card" style={{ padding: '20px 22px' }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>Conversion Funnel</h3>
          <p style={{ fontSize: 11, color: '#999', marginBottom: 16 }}>Lead progression through stages</p>

          <div className="flex flex-col gap-3">
            {funnelStages.map((stage, i) => {
              const widthPct = Math.max(15, (stage.count / totalLeads) * 100);
              const convFromPrev = i > 0 ? Math.round((stage.count / funnelStages[i - 1].count) * 100) : 100;
              return (
                <div key={stage.label}>
                  <div className="flex items-center justify-between mb-1">
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{stage.label}</span>
                    <div className="flex items-center gap-2">
                      <span style={{ fontSize: 12, fontWeight: 700, color: stage.color }}>{stage.count}</span>
                      {i > 0 && (
                        <span style={{ fontSize: 10, color: '#999' }}>({convFromPrev}% from prev)</span>
                      )}
                    </div>
                  </div>
                  <div style={{ height: 24, borderRadius: 6, background: '#f3f4f6', overflow: 'hidden' }}>
                    <div style={{
                      width: `${widthPct}%`, height: '100%', borderRadius: 6,
                      background: stage.color, transition: 'width 0.5s',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <span style={{ fontSize: 10, fontWeight: 700, color: '#fff' }}>{Math.round(widthPct)}%</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Revenue Attribution */}
        <div className="empire-card" style={{ padding: '20px 22px' }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>Revenue Attribution</h3>
          <p style={{ fontSize: 11, color: '#999', marginBottom: 16 }}>Won revenue by lead source</p>

          {totalRevenue === 0 ? (
            <div style={{ padding: 30, textAlign: 'center', color: '#ccc', fontSize: 12 }}>No won deals yet</div>
          ) : (
            <div className="flex flex-col gap-3">
              {(Object.keys(SOURCE_CONFIG) as LeadSource[]).map(src => {
                const cfg = SOURCE_CONFIG[src];
                const rev = revenueBySource[src] || 0;
                const pct = totalRevenue > 0 ? Math.round((rev / totalRevenue) * 100) : 0;
                return (
                  <div key={src}>
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <div style={{ width: 10, height: 10, borderRadius: 3, background: cfg.color, flexShrink: 0 }} />
                        <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{cfg.label}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span style={{ fontSize: 12, fontWeight: 700, color: cfg.color }}>{formatCurrency(rev)}</span>
                        <span style={{ fontSize: 10, color: '#999' }}>({pct}%)</span>
                      </div>
                    </div>
                    <div style={{ height: 8, borderRadius: 4, background: '#f3f4f6', overflow: 'hidden' }}>
                      <div style={{ width: `${pct}%`, height: '100%', borderRadius: 4, background: cfg.color, transition: 'width 0.5s' }} />
                    </div>
                  </div>
                );
              })}
              <div style={{ marginTop: 8, paddingTop: 12, borderTop: '1px solid #ece8e0' }} className="flex items-center justify-between">
                <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>Total Won Revenue</span>
                <span style={{ fontSize: 16, fontWeight: 700, color: ACCENT }}>{formatCurrency(totalRevenue)}</span>
              </div>
            </div>
          )}
        </div>

        {/* Key Metrics */}
        <div className="empire-card" style={{ padding: '20px 22px' }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', marginBottom: 4 }}>Key Metrics</h3>
          <p style={{ fontSize: 11, color: '#999', marginBottom: 16 }}>Performance indicators</p>

          {(() => {
            const avgScore = Math.round(MOCK_LEADS.reduce((s, l) => s + l.score, 0) / totalLeads);
            const avgValue = Math.round(MOCK_LEADS.reduce((s, l) => s + l.value, 0) / totalLeads);
            const avgDays = Math.round(MOCK_LEADS.filter(l => l.daysInStage > 0).reduce((s, l) => s + l.daysInStage, 0) / MOCK_LEADS.filter(l => l.daysInStage > 0).length);
            const winRate = Math.round((MOCK_LEADS.filter(l => l.status === 'won').length / MOCK_LEADS.filter(l => ['won', 'lost'].includes(l.status)).length) * 100);

            const metrics = [
              { label: 'Average Lead Score', value: avgScore.toString(), sub: 'Out of 100', color: '#2563eb' },
              { label: 'Average Deal Value', value: formatCurrency(avgValue), sub: 'Per lead', color: '#b8960c' },
              { label: 'Avg Days in Stage', value: `${avgDays} days`, sub: 'Active leads', color: '#7c3aed' },
              { label: 'Win Rate', value: `${winRate}%`, sub: 'Won vs Lost', color: ACCENT },
            ];

            return (
              <div className="flex flex-col gap-4">
                {metrics.map(m => (
                  <div key={m.label} className="flex items-center gap-3" style={{ padding: '10px 12px', borderRadius: 8, background: '#fafaf8' }}>
                    <div style={{ width: 4, height: 32, borderRadius: 2, background: m.color, flexShrink: 0 }} />
                    <div className="flex-1">
                      <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: 0.8, color: '#999' }}>{m.label}</div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a' }}>{m.value}</div>
                    </div>
                    <span style={{ fontSize: 10, color: '#999' }}>{m.sub}</span>
                  </div>
                ))}
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}

// ============ MAIN EXPORT ============

export default function LeadForgePage() {
  const [section, setSection] = useState<Section>('dashboard');

  const renderContent = () => {
    switch (section) {
      case 'dashboard': return <DashboardSection />;
      case 'pipeline': return <PipelineSection />;
      case 'leads': return <LeadsSection />;
      case 'campaigns': return <CampaignsSection />;
      case 'analytics': return <AnalyticsSection />;
      case 'payments': return <PaymentModule product="lead" />;
      case 'docs': return <div style={{ padding: 24 }}><ProductDocs product="lead" /></div>;
      default: return <DashboardSection />;
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      <nav style={{ width: 200, background: '#fff', borderRight: '1px solid #ece8e0', flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '18px 16px', borderBottom: '1px solid #ece8e0' }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#dcfce7] flex items-center justify-center">
              <Target size={18} className="text-[#16a34a]" />
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>LeadForge</div>
              <div style={{ fontSize: 10, color: '#999' }}>Lead Generation</div>
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
                    background: isActive ? ACCENT_BG : 'transparent',
                    color: isActive ? ACCENT : '#666',
                    border: isActive ? `1.5px solid ${ACCENT_BORDER}` : '1.5px solid transparent',
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
