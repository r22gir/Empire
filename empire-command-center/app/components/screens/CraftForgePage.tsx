'use client';
import { useState, useEffect, lazy, Suspense } from 'react';
import { API } from '../../lib/api';
import {
  Hammer, PenTool, ClipboardList, Package, Users, Layout,
  DollarSign, TrendingUp, Loader2, Plus, Search, FileText, CreditCard
} from 'lucide-react';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';
import KPICard from '../business/shared/KPICard';
import DataTable, { Column } from '../business/shared/DataTable';
import StatusBadge from '../business/shared/StatusBadge';
import SearchBar from '../business/shared/SearchBar';
import EmptyState from '../business/shared/EmptyState';

const JobBoard = lazy(() => import('../business/jobs/JobBoard'));
const CalendarView = lazy(() => import('../business/jobs/CalendarView'));

const NAV_SECTIONS = [
  { id: 'overview', label: 'Overview', icon: Hammer },
  { id: 'designs', label: 'Designs', icon: PenTool },
  { id: 'jobs', label: 'Job Board', icon: ClipboardList },
  { id: 'inventory', label: 'Materials', icon: Package },
  { id: 'customers', label: 'Customers', icon: Users },
  { id: 'templates', label: 'Templates', icon: Layout },
  { id: 'payments', label: 'Payments', icon: CreditCard },
  { id: 'docs', label: 'Docs', icon: FileText },
] as const;

type Section = typeof NAV_SECTIONS[number]['id'];

export default function WoodCraftPage() {
  const [section, setSection] = useState<Section>('overview');

  const Loading = () => (
    <div className="flex-1 flex items-center justify-center py-20">
      <Loader2 size={24} className="text-[#16a34a] animate-spin" />
    </div>
  );

  const renderContent = () => {
    switch (section) {
      case 'designs':
        return <DesignsSection />;
      case 'jobs':
        return <Suspense fallback={<Loading />}><JobBoard /></Suspense>;
      case 'inventory':
        return <MaterialsSection />;
      case 'customers':
        return <CustomersSection />;
      case 'templates':
        return <ComingSoon title="Templates" description="Design templates and presets for CNC, 3D printing, and woodworking -- coming soon." icon={<Layout size={32} />} />;
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
      {/* Sidebar nav */}
      <nav style={{ width: 192, background: '#fff', borderRight: '1px solid #ece8e0', flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '16px', borderBottom: '1px solid #ece8e0' }}>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[#dcfce7] flex items-center justify-center">
              <Hammer size={16} className="text-[#16a34a]" />
            </div>
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>WoodCraft</div>
              <div style={{ fontSize: 9, color: '#999' }}>CNC & Fabrication</div>
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto py-2">
          {NAV_SECTIONS.map(nav => {
            const Icon = nav.icon;
            const isActive = section === nav.id;
            return (
              <button key={nav.id}
                onClick={() => setSection(nav.id)}
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
      <div className="flex-1 overflow-y-auto" style={{ background: '#f5f2ed' }}>
        {renderContent()}
      </div>
    </div>
  );
}

// -- Overview Section --

function OverviewSection({ onNavigate }: { onNavigate: (s: Section) => void }) {
  const [jobs, setJobs] = useState<any[]>([]);
  const [designs, setDesigns] = useState<any[]>([]);
  const [inventory, setInventory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([
      fetch(`${API}/craftforge/jobs`).then(r => r.json()),
      fetch(`${API}/craftforge/designs`).then(r => r.json()),
      fetch(`${API}/inventory/items?business=craftforge`).then(r => r.json()),
    ]).then(([jobsRes, designsRes, invRes]) => {
      if (jobsRes.status === 'fulfilled') setJobs(Array.isArray(jobsRes.value) ? jobsRes.value : jobsRes.value.jobs || []);
      if (designsRes.status === 'fulfilled') setDesigns(Array.isArray(designsRes.value) ? designsRes.value : designsRes.value.designs || []);
      if (invRes.status === 'fulfilled') {
        const items = Array.isArray(invRes.value) ? invRes.value : invRes.value.items || [];
        setInventory(items);
      }
      setLoading(false);
    });
  }, []);

  const activeJobs = jobs.filter(j => j.status === 'in_progress' || j.status === 'scheduled').length;
  const lowStock = inventory.filter(i => i.quantity != null && i.min_stock != null && i.quantity < i.min_stock).length;
  const revenue = jobs.reduce((sum: number, j: any) => sum + (j.total_cost || j.revenue || 0), 0);

  const recentJobColumns: Column[] = [
    { key: 'title', label: 'Job', sortable: true },
    { key: 'customer_name', label: 'Customer', sortable: true },
    { key: 'type', label: 'Type' },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status || 'pending'} /> },
    { key: 'due_date', label: 'Due', render: (row) => <span style={{ fontSize: 12, color: '#777' }} suppressHydrationWarning>{row.due_date ? new Date(row.due_date).toLocaleDateString() : '--'}</span> },
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
        <div className="empire-card">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-2" style={{ background: '#dcfce7', color: '#16a34a' }}><ClipboardList size={18} /></div>
          <div className="kpi-value green">{loading ? '...' : String(activeJobs)}</div>
          <div className="kpi-label">Active Jobs</div>
        </div>
        <div className="empire-card">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-2" style={{ background: '#dbeafe', color: '#2563eb' }}><PenTool size={18} /></div>
          <div className="kpi-value blue">{loading ? '...' : String(designs.length)}</div>
          <div className="kpi-label">Designs</div>
        </div>
        <div className="empire-card">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-2" style={{ background: lowStock > 0 ? '#fee2e2' : '#dcfce7', color: lowStock > 0 ? '#dc2626' : '#16a34a' }}><Package size={18} /></div>
          <div className={`kpi-value ${lowStock > 0 ? 'red' : 'green'}`}>{loading ? '...' : String(lowStock)}</div>
          <div className="kpi-label">Low Stock</div>
        </div>
        <div className="empire-card">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-2" style={{ background: '#fdf8eb', color: '#b8960c' }}><DollarSign size={18} /></div>
          <div className="kpi-value gold">{loading ? '...' : `$${revenue.toLocaleString()}`}</div>
          <div className="kpi-label">Revenue</div>
        </div>
      </div>

      {/* Quick links */}
      <div className="section-label" style={{ marginBottom: 8 }}>Quick Access</div>
      <div className="grid grid-cols-3 gap-3 mb-6">
        <QuickLink icon={<PenTool size={18} />} label="New Design" desc="Create a new design file" color="#2563eb" onClick={() => onNavigate('designs')} />
        <QuickLink icon={<ClipboardList size={18} />} label="Job Board" desc="View and manage all jobs" color="#16a34a" onClick={() => onNavigate('jobs')} />
        <QuickLink icon={<Package size={18} />} label="Materials" desc="Inventory and stock levels" color="#b8960c" onClick={() => onNavigate('inventory')} />
      </div>

      {/* Recent Jobs */}
      <div className="section-label" style={{ marginBottom: 8 }}>Recent Jobs</div>
      <div className="empire-card">
        <h3 style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a', marginBottom: 12 }} className="flex items-center gap-2">
          <ClipboardList size={15} className="text-[#16a34a]" /> Recent Jobs
        </h3>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 size={20} className="text-[#16a34a] animate-spin" />
          </div>
        ) : jobs.length === 0 ? (
          <EmptyState
            icon={<ClipboardList size={32} />}
            title="No jobs yet"
            description="Jobs will appear here once created from quotes or manually added."
          />
        ) : (
          <DataTable columns={recentJobColumns} data={jobs.slice(0, 5)} />
        )}
      </div>
    </div>
  );
}

// -- Designs Section --

function DesignsSection() {
  const [designs, setDesigns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetch(`${API}/craftforge/designs`)
      .then(r => r.json())
      .then(data => {
        setDesigns(Array.isArray(data) ? data : data.designs || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const filtered = designs.filter(d => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (d.name || '').toLowerCase().includes(q) ||
           (d.type || '').toLowerCase().includes(q) ||
           (d.material || '').toLowerCase().includes(q);
  });

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
      <div className="flex items-center justify-between mb-5">
        <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }} className="flex items-center gap-2">
          <PenTool size={20} className="text-[#16a34a]" /> Designs
        </h2>
        <div className="flex items-center gap-3">
          <div className="w-64">
            <SearchBar value={search} onChange={setSearch} placeholder="Search designs..." />
          </div>
          <button style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 12px', fontSize: 12, fontWeight: 700, color: '#fff', background: '#16a34a', borderRadius: 10, border: 'none', cursor: 'pointer' }} className="hover:bg-[#15803d] transition-colors">
            <Plus size={14} /> New Design
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 size={24} className="text-[#16a34a] animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<PenTool size={32} />}
          title="No designs found"
          description={search ? 'Try adjusting your search terms.' : 'Create your first design to get started.'}
        />
      ) : (
        <div className="grid grid-cols-3 gap-4">
          {filtered.map((d, i) => (
            <div key={d.id || i} className="empire-card" style={{ cursor: 'pointer' }}>
              <div className="flex items-center justify-between mb-2">
                <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }} className="truncate">{d.name || 'Untitled'}</span>
                <StatusBadge status={d.status || 'draft'} />
              </div>
              <div className="space-y-1">
                {d.type && <div style={{ fontSize: 10, color: '#777' }}><span style={{ fontWeight: 600, color: '#555' }}>Type:</span> {d.type}</div>}
                {d.material && <div style={{ fontSize: 10, color: '#777' }}><span style={{ fontWeight: 600, color: '#555' }}>Material:</span> {d.material}</div>}
                {d.dimensions && <div style={{ fontSize: 10, color: '#777' }}><span style={{ fontWeight: 600, color: '#555' }}>Dims:</span> {d.dimensions}</div>}
              </div>
              <div style={{ marginTop: 12, paddingTop: 8, borderTop: '1px solid #ece8e0' }}>
                <span style={{ fontSize: 9, color: '#aaa' }} suppressHydrationWarning>
                  {d.created_at ? new Date(d.created_at).toLocaleDateString() : '--'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// -- Materials/Inventory Section --

function MaterialsSection() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/inventory/items?business=craftforge`)
      .then(r => r.json())
      .then(data => {
        setItems(Array.isArray(data) ? data : data.items || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const columns: Column[] = [
    { key: 'name', label: 'Name', sortable: true },
    { key: 'sku', label: 'SKU', sortable: true },
    { key: 'category', label: 'Category', sortable: true },
    {
      key: 'quantity', label: 'Qty', sortable: true,
      render: (row) => {
        const isLow = row.quantity != null && row.min_stock != null && row.quantity < row.min_stock;
        return <span style={{ fontSize: 13, fontWeight: 700, color: isLow ? '#dc2626' : '#1a1a1a' }}>{row.quantity ?? '--'}</span>;
      },
    },
    { key: 'unit', label: 'Unit' },
    {
      key: 'min_stock', label: 'Min Stock',
      render: (row) => <span style={{ fontSize: 12, color: '#777' }}>{row.min_stock ?? '--'}</span>,
    },
    {
      key: 'cost', label: 'Cost', sortable: true,
      render: (row) => <span style={{ fontSize: 12, fontWeight: 600, color: '#b8960c' }}>{row.cost != null ? `$${Number(row.cost).toFixed(2)}` : '--'}</span>,
    },
  ];

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
      <div className="flex items-center justify-between mb-5">
        <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }} className="flex items-center gap-2">
          <Package size={20} className="text-[#16a34a]" /> Materials
        </h2>
        <button style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 12px', fontSize: 12, fontWeight: 700, color: '#fff', background: '#16a34a', borderRadius: 10, border: 'none', cursor: 'pointer' }} className="hover:bg-[#15803d] transition-colors">
          <Plus size={14} /> Add Item
        </button>
      </div>

      <DataTable columns={columns} data={items} loading={loading} emptyMessage="No materials found. Add inventory items to track stock levels." />
    </div>
  );
}

// -- Customers Section --

function CustomersSection() {
  const [customers, setCustomers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/craftforge/customers`)
      .then(r => r.json())
      .then(data => {
        setCustomers(Array.isArray(data) ? data : data.customers || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const columns: Column[] = [
    { key: 'name', label: 'Name', sortable: true, render: (row) => <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{row.name || row.customer_name || '--'}</span> },
    { key: 'email', label: 'Email', sortable: true },
    { key: 'phone', label: 'Phone' },
    { key: 'total_orders', label: 'Orders', sortable: true, render: (row) => <span style={{ fontSize: 12, fontWeight: 700, color: '#16a34a' }}>{row.total_orders ?? row.order_count ?? '--'}</span> },
    { key: 'total_spent', label: 'Total Spent', sortable: true, render: (row) => <span style={{ fontSize: 12, fontWeight: 600, color: '#b8960c' }}>{row.total_spent != null ? `$${Number(row.total_spent).toLocaleString()}` : '--'}</span> },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status || 'active'} /> },
  ];

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px' }}>
      <div className="flex items-center justify-between mb-5">
        <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }} className="flex items-center gap-2">
          <Users size={20} className="text-[#16a34a]" /> Customers
        </h2>
      </div>

      <DataTable columns={columns} data={customers} loading={loading} emptyMessage="No customers found." />
    </div>
  );
}

// -- Shared Components --

function QuickLink({ icon, label, desc, color, onClick }: {
  icon: React.ReactNode; label: string; desc: string; color: string; onClick: () => void;
}) {
  return (
    <button onClick={onClick} className="empire-card" style={{ textAlign: 'left', cursor: 'pointer', width: '100%' }}>
      <div className="flex items-center gap-2 mb-1">
        <span style={{ color }}>{icon}</span>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>{label}</span>
      </div>
      <div style={{ fontSize: 10, color: '#777' }}>{desc}</div>
    </button>
  );
}

function ComingSoon({ title, description, icon }: { title: string; description: string; icon: React.ReactNode }) {
  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '24px 36px', display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 400 }}>
      <div className="text-center">
        <div style={{ color: '#d8d3cb', marginBottom: 12 }}>{icon}</div>
        <div style={{ fontSize: 18, fontWeight: 700, color: '#aaa' }}>{title}</div>
        <div style={{ fontSize: 13, color: '#ccc', marginTop: 4 }}>{description}</div>
      </div>
    </div>
  );
}
