'use client';
import React, { useState, useEffect, lazy, Suspense } from 'react';
import { API } from '../../lib/api';
import {
  Hammer, PenTool, ClipboardList, Package, Users, DollarSign,
  TrendingUp, Loader2, FileText, CreditCard, Wrench
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';
import DataTable, { Column } from '../business/shared/DataTable';
import StatusBadge from '../business/shared/StatusBadge';
import EmptyState from '../business/shared/EmptyState';

// Lazy-load sub-modules (split to keep each file manageable)
const QuoteBuilderSection = lazy(() => import('../business/craftforge/QuoteBuilderSection'));
const InventoryModule = lazy(() => import('../business/craftforge/InventoryModule'));
const CRMModule = lazy(() => import('../business/craftforge/CRMModule'));
const FinanceModule = lazy(() => import('../business/craftforge/FinanceModule'));
const JobsModule = lazy(() => import('../business/craftforge/JobsModule'));

const NAV_SECTIONS = [
  { id: 'overview', label: 'Overview', icon: Hammer },
  { id: 'quotes', label: 'Quote Builder', icon: PenTool },
  { id: 'inventory', label: 'Inventory', icon: Package },
  { id: 'customers', label: 'Customers', icon: Users },
  { id: 'finance', label: 'Finance', icon: DollarSign },
  { id: 'jobs', label: 'Jobs', icon: ClipboardList },
  { id: 'payments', label: 'Payments', icon: CreditCard },
  { id: 'docs', label: 'Docs', icon: FileText },
] as const;

type Section = typeof NAV_SECTIONS[number]['id'];

interface CraftForgePageProps {
  initialSection?: string;
}

export default function WoodCraftPage({ initialSection }: CraftForgePageProps) {
  const [section, setSection] = useState<Section>((initialSection as Section) || 'overview');

  useEffect(() => {
    if (initialSection) setSection(initialSection as Section);
  }, [initialSection]);

  const Loading = () => (
    <div className="flex-1 flex items-center justify-center py-20">
      <Loader2 size={24} className="text-[#b8960c] animate-spin" />
    </div>
  );

  const renderContent = () => {
    switch (section) {
      case 'quotes':
        return <Suspense fallback={<Loading />}><QuoteBuilderSection /></Suspense>;
      case 'inventory':
        return <Suspense fallback={<Loading />}><InventoryModule /></Suspense>;
      case 'customers':
        return <Suspense fallback={<Loading />}><CRMModule onNavigate={(s) => setSection(s as Section)} /></Suspense>;
      case 'finance':
        return <Suspense fallback={<Loading />}><FinanceModule /></Suspense>;
      case 'jobs':
        return <Suspense fallback={<Loading />}><JobsModule /></Suspense>;
      case 'payments':
        return <PaymentModule product="craft" />;
      case 'docs':
        return <div style={{ padding: 24 }}><ProductDocs product="craft" /></div>;
      default:
        return <OverviewSection onNavigate={setSection} />;
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Sidebar nav -- gold theme */}
      <nav style={{ width: 200, background: '#fff', borderRight: '1px solid #ece8e0', flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '18px 16px', borderBottom: '1px solid #ece8e0' }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: '#fdf8eb', color: '#b8960c' }}>
              <Hammer size={18} />
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>WoodCraft</div>
              <div style={{ fontSize: 10, color: '#999' }}>CNC & Fabrication</div>
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
                    padding: '10px 14px',
                    borderRadius: 12,
                    fontSize: 13,
                    fontWeight: isActive ? 700 : 500,
                    background: isActive ? '#fdf8eb' : 'transparent',
                    color: isActive ? '#b8960c' : '#666',
                    border: isActive ? '1.5px solid #f0e6c0' : '1.5px solid transparent',
                    minHeight: 44,
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

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
//  Overview Section
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function OverviewSection({ onNavigate }: { onNavigate: (s: Section) => void }) {
  const [dashboard, setDashboard] = useState<any>(null);
  const [recentJobs, setRecentJobs] = useState<any[]>([]);
  const [recentDesigns, setRecentDesigns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([
      fetch(`${API}/craftforge/dashboard`).then(r => r.json()),
      fetch(`${API}/craftforge/jobs?limit=5`).then(r => r.json()),
      fetch(`${API}/craftforge/designs?limit=5`).then(r => r.json()),
    ]).then(([dashRes, jobsRes, designsRes]) => {
      if (dashRes.status === 'fulfilled') setDashboard(dashRes.value);
      if (jobsRes.status === 'fulfilled') {
        const raw = jobsRes.value;
        setRecentJobs(Array.isArray(raw) ? raw : raw.jobs || []);
      }
      if (designsRes.status === 'fulfilled') {
        const raw = designsRes.value;
        setRecentDesigns(Array.isArray(raw) ? raw : raw.designs || []);
      }
      setLoading(false);
    });
  }, []);

  const d = dashboard || {};
  const jobStats = d.jobs || {};
  const invStats = d.inventory || {};
  const machines = d.machines || {};

  const jobColumns: Column[] = [
    { key: 'job_number', label: '#', render: (row) => <span style={{ fontSize: 12, fontWeight: 700, color: '#b8960c', fontFamily: 'monospace' }}>{row.job_number || '--'}</span> },
    { key: 'customer_name', label: 'Customer', sortable: true },
    { key: 'machine', label: 'Machine' },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status || 'queued'} /> },
    { key: 'due_date', label: 'Due', render: (row) => <span style={{ fontSize: 11, color: '#777' }} suppressHydrationWarning>{row.due_date ? new Date(row.due_date).toLocaleDateString() : '--'}</span> },
  ];

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
      <div className="flex items-center gap-3 mb-1">
        <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>WoodCraft</h1>
        <span style={{ fontSize: 13, color: '#aaa' }} suppressHydrationWarning>
          {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
        </span>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-3 mt-5 mb-6">
        <div className="empire-card flat">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-2" style={{ background: '#fdf8eb', color: '#b8960c' }}>
            <DollarSign size={18} />
          </div>
          <div className="kpi-value gold">{loading ? '...' : `$${Number(d.pipeline || 0).toLocaleString()}`}</div>
          <div className="kpi-label">Pipeline</div>
        </div>
        <div className="empire-card flat">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-2" style={{ background: '#f0fdf4', color: '#22c55e' }}>
            <TrendingUp size={18} />
          </div>
          <div className="kpi-value green">{loading ? '...' : `$${Number(d.revenue || 0).toLocaleString()}`}</div>
          <div className="kpi-label">Revenue</div>
        </div>
        <div className="empire-card flat">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-2" style={{ background: '#eff6ff', color: '#2563eb' }}>
            <ClipboardList size={18} />
          </div>
          <div className="kpi-value blue">{loading ? '...' : String(jobStats.active || 0)}</div>
          <div className="kpi-label">Active Jobs</div>
        </div>
        <div className="empire-card flat">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-2" style={{ background: invStats.low_stock > 0 ? '#fef2f2' : '#fdf8eb', color: invStats.low_stock > 0 ? '#dc2626' : '#b8960c' }}>
            <Package size={18} />
          </div>
          <div className={`kpi-value ${invStats.low_stock > 0 ? 'red' : 'gold'}`}>{loading ? '...' : String(invStats.low_stock || 0)}</div>
          <div className="kpi-label">Low Stock</div>
        </div>
      </div>

      {/* Machine Status + Design Stats */}
      <div className="grid grid-cols-2 gap-3 mb-6">
        {/* Machine status */}
        <div className="empire-card flat">
          <div className="section-label mb-3">Machines</div>
          {Object.entries(machines).map(([name, info]: [string, any]) => (
            <div key={name} className="flex items-center justify-between py-2" style={{ borderBottom: '1px solid #f5f2ed' }}>
              <div className="flex items-center gap-2">
                <Wrench size={14} className="text-[#b8960c]" />
                <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{name}</span>
              </div>
              <div className="flex items-center gap-3">
                <span style={{ fontSize: 11, color: '#777' }}>{info.queued_jobs || 0} queued</span>
                <span className="status-pill" style={{
                  fontSize: 10,
                  background: info.status === 'idle' ? '#f0fdf4' : '#eff6ff',
                  color: info.status === 'idle' ? '#22c55e' : '#2563eb',
                }}>
                  {info.status || 'idle'}
                </span>
              </div>
            </div>
          ))}
          {Object.keys(machines).length === 0 && (
            <div style={{ fontSize: 12, color: '#999', padding: '8px 0' }}>No machine data available.</div>
          )}
        </div>

        {/* Design breakdown */}
        <div className="empire-card flat">
          <div className="section-label mb-3">Designs by Category</div>
          {d.designs_by_category && Object.entries(d.designs_by_category).map(([cat, count]: [string, any]) => (
            <div key={cat} className="flex items-center justify-between py-2" style={{ borderBottom: '1px solid #f5f2ed' }}>
              <span style={{ fontSize: 13, color: '#555' }} className="capitalize">{cat.replace('-', ' ')}</span>
              <span style={{ fontSize: 13, fontWeight: 700, color: '#b8960c' }}>{count}</span>
            </div>
          ))}
          {(!d.designs_by_category || Object.keys(d.designs_by_category).length === 0) && (
            <div style={{ fontSize: 12, color: '#999', padding: '8px 0' }}>No designs yet.</div>
          )}
        </div>
      </div>

      {/* Quick access */}
      <div className="section-label mb-2">Quick Access</div>
      <div className="grid grid-cols-3 gap-3 mb-6">
        <QuickLink icon={<PenTool size={18} />} label="New Quote" desc="Create a design quote" color="#b8960c" onClick={() => onNavigate('quotes')} />
        <QuickLink icon={<ClipboardList size={18} />} label="Job Board" desc="Production tracking" color="#2563eb" onClick={() => onNavigate('jobs')} />
        <QuickLink icon={<Package size={18} />} label="Inventory" desc="Materials & stock levels" color="#22c55e" onClick={() => onNavigate('inventory')} />
      </div>

      {/* Recent Jobs */}
      <div className="section-label mb-2">Recent Jobs</div>
      <div className="empire-card flat mb-6">
        <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 12 }} className="flex items-center gap-2">
          <ClipboardList size={15} className="text-[#b8960c]" /> Recent Jobs
        </h3>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 size={20} className="text-[#b8960c] animate-spin" />
          </div>
        ) : recentJobs.length === 0 ? (
          <EmptyState
            icon={<ClipboardList size={32} />}
            title="No jobs yet"
            description="Jobs will appear here once created from design quotes."
          />
        ) : (
          <DataTable columns={jobColumns} data={recentJobs.slice(0, 5)} />
        )}
      </div>

      {/* Recent Designs */}
      <div className="section-label mb-2">Recent Designs</div>
      {loading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 size={20} className="text-[#b8960c] animate-spin" />
        </div>
      ) : recentDesigns.length === 0 ? (
        <EmptyState
          icon={<PenTool size={32} />}
          title="No designs yet"
          description="Create your first design quote to get started."
          action={{ label: 'Create Quote', onClick: () => onNavigate('quotes') }}
        />
      ) : (
        <div className="grid grid-cols-3 gap-4">
          {recentDesigns.slice(0, 6).map((des, i) => (
            <div key={des.id || i} className="empire-card" style={{ cursor: 'pointer' }} onClick={() => onNavigate('quotes')}>
              <div className="flex items-center justify-between mb-2">
                <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }} className="truncate">{des.name || 'Untitled'}</span>
                <StatusBadge status={des.status || 'concept'} />
              </div>
              <div className="space-y-1">
                {des.customer_name && <div style={{ fontSize: 10, color: '#777' }}><span style={{ fontWeight: 600, color: '#555' }}>Customer:</span> {des.customer_name}</div>}
                {des.category && <div style={{ fontSize: 10, color: '#777' }}><span style={{ fontWeight: 600, color: '#555' }}>Type:</span> <span className="capitalize">{des.category.replace('-', ' ')}</span></div>}
                {des.total != null && <div style={{ fontSize: 10, color: '#777' }}><span style={{ fontWeight: 600, color: '#555' }}>Total:</span> <span style={{ fontWeight: 700, color: '#b8960c' }}>${Number(des.total).toFixed(2)}</span></div>}
              </div>
              <div style={{ marginTop: 12, paddingTop: 8, borderTop: '1px solid #ece8e0' }} className="flex items-center justify-between">
                <span style={{ fontSize: 9, color: '#aaa' }} suppressHydrationWarning>
                  {des.created_at ? new Date(des.created_at).toLocaleDateString() : '--'}
                </span>
                <span style={{ fontSize: 9, color: '#bbb', fontFamily: 'monospace' }}>{des.design_number || ''}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Shared quick-link card ──

function QuickLink({ icon, label, desc, color, onClick }: {
  icon: React.ReactNode; label: string; desc: string; color: string; onClick: () => void;
}) {
  return (
    <button onClick={onClick} className="empire-card" style={{ textAlign: 'left', cursor: 'pointer', width: '100%', minHeight: 44 }}>
      <div className="flex items-center gap-2 mb-1">
        <span style={{ color }}>{icon}</span>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{label}</span>
      </div>
      <div style={{ fontSize: 10, color: '#777' }}>{desc}</div>
    </button>
  );
}
