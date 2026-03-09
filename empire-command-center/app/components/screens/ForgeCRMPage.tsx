'use client';

import { useState, useEffect, lazy, Suspense } from 'react';
import {
  Users, Search, Plus, BarChart3, Target, FileText, Phone, Mail,
  Loader2, Crown, TrendingUp, UserPlus, DollarSign, Activity, BookOpen, CreditCard,
} from 'lucide-react';
import { API } from '../../lib/api';
import ProductDocs from '../business/docs/ProductDocs';
import PaymentModule from '../business/payments/PaymentModule';

const CustomerList = lazy(() => import('../business/crm/CustomerList'));
const CustomerDetail = lazy(() => import('../business/crm/CustomerDetail'));

const Loading = () => (
  <div className="flex-1 flex items-center justify-center py-16">
    <Loader2 size={20} className="animate-spin text-[#b8960c]" />
  </div>
);

const NAV = [
  { id: 'customers', label: 'All Customers', icon: <Users size={16} /> },
  { id: 'pipeline', label: 'Pipeline', icon: <Target size={16} /> },
  { id: 'add', label: 'Add Customer', icon: <UserPlus size={16} /> },
  { id: 'stats', label: 'Stats', icon: <BarChart3 size={16} /> },
  { id: 'payments', label: 'Payments', icon: <CreditCard size={16} /> },
  { id: 'docs', label: 'Docs', icon: <BookOpen size={16} /> },
];

export default function ForgeCRMPage() {
  const [section, setSection] = useState('customers');
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);
  const [pipeline, setPipeline] = useState<any>(null);
  const [stats, setStats] = useState({ total: 0, revenue: 0, avgQuotes: 0, sources: {} as Record<string, number> });
  const [customers, setCustomers] = useState<any[]>([]);

  // New customer form
  const [newCustomer, setNewCustomer] = useState({ name: '', email: '', phone: '', address: '', company: '', type: 'residential', source: 'direct', notes: '' });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    // Fetch pipeline
    fetch(`${API}/crm/pipeline`).then(r => r.json()).then(setPipeline).catch(() => {});
    // Fetch customers for stats
    fetch(`${API}/crm/customers?limit=500`).then(r => r.json()).then(data => {
      const custs = data.customers || [];
      setCustomers(custs);
      const totalRev = custs.reduce((s: number, c: any) => s + (c.total_revenue || 0), 0);
      const totalQuotes = custs.reduce((s: number, c: any) => s + (c.lifetime_quotes || c.quote_count || 0), 0);
      const sources: Record<string, number> = {};
      custs.forEach((c: any) => { sources[c.source || 'direct'] = (sources[c.source || 'direct'] || 0) + 1; });
      setStats({ total: custs.length, revenue: totalRev, avgQuotes: custs.length ? Math.round(totalQuotes / custs.length * 10) / 10 : 0, sources });
    }).catch(() => {});
  }, []);

  const handleAddCustomer = async () => {
    if (!newCustomer.name.trim()) return;
    setSaving(true);
    try {
      const res = await fetch(`${API}/crm/customers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newCustomer),
      });
      if (res.ok) {
        const data = await res.json();
        setNewCustomer({ name: '', email: '', phone: '', address: '', company: '', type: 'residential', source: 'direct', notes: '' });
        setSelectedCustomerId(data.customer?.id || null);
        setSection('customers');
      }
    } catch { /* */ }
    setSaving(false);
  };

  const renderSection = () => {
    // Customer detail view
    if (selectedCustomerId) {
      return (
        <Suspense fallback={<Loading />}>
          <CustomerDetail
            customerId={selectedCustomerId}
            onBack={() => setSelectedCustomerId(null)}
          />
        </Suspense>
      );
    }

    switch (section) {
      case 'customers':
        return (
          <Suspense fallback={<Loading />}>
            <CustomerList onSelectCustomer={(id) => setSelectedCustomerId(id)} />
          </Suspense>
        );

      case 'pipeline':
        return (
          <div style={{ maxWidth: 900, margin: '0 auto' }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }}>Sales Pipeline</h2>
            {pipeline ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {Object.entries(pipeline.pipeline || {}).map(([status, data]: [string, any]) => (
                  <div key={status} className="empire-card flat" style={{ padding: '14px 18px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <div style={{
                          width: 10, height: 10, borderRadius: '50%',
                          background: status === 'accepted' ? '#16a34a' : status === 'sent' ? '#2563eb' : status === 'draft' ? '#b8960c' : '#999',
                        }} />
                        <span style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a', textTransform: 'capitalize' }}>{status}</span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <span style={{ fontSize: 12, color: '#777' }}>{data.count} quote{data.count !== 1 ? 's' : ''}</span>
                        <span style={{ fontSize: 14, fontWeight: 700, color: '#16a34a' }}>
                          ${(data.total_value || 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                        </span>
                      </div>
                    </div>
                    {/* Progress bar */}
                    <div style={{ height: 6, borderRadius: 3, background: '#ece8e0' }}>
                      <div style={{
                        height: '100%', borderRadius: 3, transition: 'width 0.6s ease',
                        width: `${pipeline.total_quotes ? (data.count / pipeline.total_quotes) * 100 : 0}%`,
                        background: status === 'accepted' ? '#16a34a' : status === 'sent' ? '#2563eb' : status === 'draft' ? '#b8960c' : '#999',
                      }} />
                    </div>
                    {/* Quote list */}
                    {data.quotes?.slice(0, 5).map((q: any) => (
                      <div key={q.id || q.quote_number} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #f5f3ef', marginTop: 4 }}>
                        <span style={{ fontSize: 11, color: '#555' }}>{q.customer_name || 'Unknown'}</span>
                        <span style={{ fontSize: 11, fontWeight: 600, color: '#1a1a1a' }}>{q.quote_number}</span>
                        <span style={{ fontSize: 11, fontWeight: 700, color: '#b8960c' }}>${(q.total || 0).toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                ))}
                <div style={{ textAlign: 'center', padding: '12px', fontSize: 12, color: '#999' }}>
                  Total: {pipeline.total_quotes || 0} quotes
                </div>
              </div>
            ) : (
              <Loading />
            )}
          </div>
        );

      case 'add':
        return (
          <div style={{ maxWidth: 600, margin: '0 auto' }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }}>Add New Customer</h2>
            <div className="empire-card flat" style={{ padding: '20px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                {/* Name */}
                <div style={{ gridColumn: '1 / -1' }}>
                  <label style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 4 }}>Name *</label>
                  <input value={newCustomer.name} onChange={e => setNewCustomer(p => ({ ...p, name: e.target.value }))}
                    placeholder="Customer name" className="w-full outline-none focus:border-[#b8960c] transition-colors"
                    style={{ padding: '10px 14px', fontSize: 13, border: '1px solid #ece8e0', borderRadius: 10, background: '#faf9f7' }} />
                </div>
                {/* Email */}
                <div>
                  <label style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 4 }}>Email</label>
                  <input value={newCustomer.email} onChange={e => setNewCustomer(p => ({ ...p, email: e.target.value }))}
                    placeholder="email@example.com" className="w-full outline-none focus:border-[#b8960c] transition-colors"
                    style={{ padding: '10px 14px', fontSize: 13, border: '1px solid #ece8e0', borderRadius: 10, background: '#faf9f7' }} />
                </div>
                {/* Phone */}
                <div>
                  <label style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 4 }}>Phone</label>
                  <input value={newCustomer.phone} onChange={e => setNewCustomer(p => ({ ...p, phone: e.target.value }))}
                    placeholder="(555) 123-4567" className="w-full outline-none focus:border-[#b8960c] transition-colors"
                    style={{ padding: '10px 14px', fontSize: 13, border: '1px solid #ece8e0', borderRadius: 10, background: '#faf9f7' }} />
                </div>
                {/* Address */}
                <div style={{ gridColumn: '1 / -1' }}>
                  <label style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 4 }}>Address</label>
                  <input value={newCustomer.address} onChange={e => setNewCustomer(p => ({ ...p, address: e.target.value }))}
                    placeholder="123 Main St, City, ST 12345" className="w-full outline-none focus:border-[#b8960c] transition-colors"
                    style={{ padding: '10px 14px', fontSize: 13, border: '1px solid #ece8e0', borderRadius: 10, background: '#faf9f7' }} />
                </div>
                {/* Company */}
                <div>
                  <label style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 4 }}>Company</label>
                  <input value={newCustomer.company} onChange={e => setNewCustomer(p => ({ ...p, company: e.target.value }))}
                    placeholder="Company name" className="w-full outline-none focus:border-[#b8960c] transition-colors"
                    style={{ padding: '10px 14px', fontSize: 13, border: '1px solid #ece8e0', borderRadius: 10, background: '#faf9f7' }} />
                </div>
                {/* Type */}
                <div>
                  <label style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 4 }}>Type</label>
                  <select value={newCustomer.type} onChange={e => setNewCustomer(p => ({ ...p, type: e.target.value }))}
                    className="w-full outline-none focus:border-[#b8960c] transition-colors cursor-pointer"
                    style={{ padding: '10px 14px', fontSize: 13, border: '1px solid #ece8e0', borderRadius: 10, background: '#faf9f7' }}>
                    <option value="residential">Residential</option>
                    <option value="commercial">Commercial</option>
                    <option value="designer">Designer</option>
                    <option value="contractor">Contractor</option>
                  </select>
                </div>
                {/* Source */}
                <div>
                  <label style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 4 }}>Source</label>
                  <select value={newCustomer.source} onChange={e => setNewCustomer(p => ({ ...p, source: e.target.value }))}
                    className="w-full outline-none focus:border-[#b8960c] transition-colors cursor-pointer"
                    style={{ padding: '10px 14px', fontSize: 13, border: '1px solid #ece8e0', borderRadius: 10, background: '#faf9f7' }}>
                    <option value="direct">Direct</option>
                    <option value="referral">Referral</option>
                    <option value="website">Website</option>
                    <option value="marketplace">Marketplace</option>
                  </select>
                </div>
                {/* Notes */}
                <div style={{ gridColumn: '1 / -1' }}>
                  <label style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'block', marginBottom: 4 }}>Notes</label>
                  <textarea value={newCustomer.notes} onChange={e => setNewCustomer(p => ({ ...p, notes: e.target.value }))}
                    placeholder="Additional notes..." rows={3} className="w-full outline-none focus:border-[#b8960c] transition-colors resize-none"
                    style={{ padding: '10px 14px', fontSize: 13, border: '1px solid #ece8e0', borderRadius: 10, background: '#faf9f7' }} />
                </div>
              </div>
              <button
                onClick={handleAddCustomer}
                disabled={!newCustomer.name.trim() || saving}
                className="w-full flex items-center justify-center gap-2 cursor-pointer font-bold transition-all hover:brightness-110 disabled:opacity-50 active:scale-[0.98]"
                style={{ marginTop: 16, height: 44, borderRadius: 10, background: '#b8960c', color: '#fff', border: 'none', fontSize: 13 }}
              >
                {saving ? <><Loader2 size={16} className="animate-spin" /> Saving...</> : <><UserPlus size={16} /> Add Customer</>}
              </button>
            </div>
          </div>
        );

      case 'payments':
        return <PaymentModule product="crm" />;

      case 'docs':
        return <div style={{ padding: 24 }}><ProductDocs product="crm" /></div>;

      case 'stats':
        return (
          <div style={{ maxWidth: 900, margin: '0 auto' }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', marginBottom: 16 }}>CRM Statistics</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
              <div className="empire-card flat" style={{ padding: '16px 14px', textAlign: 'center' }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: '#b8960c' }}>{stats.total}</div>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: 4 }}>Total Customers</div>
              </div>
              <div className="empire-card flat" style={{ padding: '16px 14px', textAlign: 'center' }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: '#16a34a' }}>${stats.revenue.toLocaleString()}</div>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: 4 }}>Total Revenue</div>
              </div>
              <div className="empire-card flat" style={{ padding: '16px 14px', textAlign: 'center' }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: '#2563eb' }}>{stats.avgQuotes}</div>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: 4 }}>Avg Quotes/Customer</div>
              </div>
              <div className="empire-card flat" style={{ padding: '16px 14px', textAlign: 'center' }}>
                <div style={{ fontSize: 28, fontWeight: 700, color: '#7c3aed' }}>{customers.filter(c => (c.total_revenue || 0) > 10000).length}</div>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#777', textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: 4 }}>VIP Customers</div>
              </div>
            </div>

            {/* Sources breakdown */}
            <div className="empire-card flat" style={{ padding: '20px' }}>
              <div className="section-label" style={{ marginBottom: 12 }}>Customer Sources</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                {Object.entries(stats.sources).map(([source, count]) => (
                  <div key={source} style={{ padding: 12, borderRadius: 10, background: '#faf9f7', border: '1px solid #ece8e0', textAlign: 'center' }}>
                    <div style={{ fontSize: 20, fontWeight: 700, color: '#b8960c' }}>{count}</div>
                    <div style={{ fontSize: 11, fontWeight: 600, color: '#777', textTransform: 'capitalize' }}>{source}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Top customers */}
            <div className="empire-card flat" style={{ padding: '20px', marginTop: 12 }}>
              <div className="section-label" style={{ marginBottom: 12 }}>Top Customers by Revenue</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {[...customers].sort((a, b) => (b.total_revenue || 0) - (a.total_revenue || 0)).slice(0, 10).map((c, i) => (
                  <div
                    key={c.id}
                    onClick={() => { setSelectedCustomerId(c.id); setSection('customers'); }}
                    className="cursor-pointer hover:bg-[#faf9f7] transition-colors"
                    style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px', borderRadius: 8, borderBottom: '1px solid #f5f3ef' }}
                  >
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#bbb', width: 24 }}>#{i + 1}</span>
                    <div style={{
                      width: 28, height: 28, borderRadius: '50%',
                      background: (c.total_revenue || 0) > 10000 ? '#b8960c' : '#ece8e0',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 11, fontWeight: 700, color: (c.total_revenue || 0) > 10000 ? '#fff' : '#777',
                    }}>
                      {(c.total_revenue || 0) > 10000 ? <Crown size={14} /> : c.name?.charAt(0)?.toUpperCase()}
                    </div>
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a', flex: 1 }}>{c.name}</span>
                    <span style={{ fontSize: 13, fontWeight: 700, color: '#16a34a' }}>${(c.total_revenue || 0).toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Sidebar */}
      <div
        className="border-r border-[var(--border)] bg-[var(--panel)] shrink-0 overflow-y-auto"
        style={{ width: 210, padding: '16px 10px' }}
      >
        <div className="flex items-center gap-2 px-2 mb-4">
          <Users size={20} className="text-[#b8960c]" />
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>ForgeCRM</div>
            <div style={{ fontSize: 10, color: '#999' }}>Customer Management</div>
          </div>
        </div>

        {NAV.map(item => {
          const active = section === item.id && !selectedCustomerId;
          return (
            <button
              key={item.id}
              onClick={() => { setSection(item.id); setSelectedCustomerId(null); }}
              className="w-full flex items-center gap-2.5 cursor-pointer transition-all"
              style={{
                padding: '10px 12px', borderRadius: 10, marginBottom: 2, border: 'none', textAlign: 'left',
                background: active ? '#b8960c10' : 'transparent',
                color: active ? '#b8960c' : '#777',
                fontWeight: active ? 700 : 500,
                fontSize: 13,
              }}
            >
              <span style={{ color: active ? '#b8960c' : '#bbb' }}>{item.icon}</span>
              {item.label}
            </button>
          );
        })}

        {/* Quick Stats */}
        <div style={{ marginTop: 20, padding: '12px', borderRadius: 10, background: '#fdf8e8', border: '1px solid #fde68a' }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: '#b8960c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
            Quick Stats
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: '#777' }}>Customers</span>
              <span style={{ fontWeight: 700, color: '#1a1a1a' }}>{stats.total}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: '#777' }}>Revenue</span>
              <span style={{ fontWeight: 700, color: '#16a34a' }}>${stats.revenue.toLocaleString()}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: '#777' }}>VIP</span>
              <span style={{ fontWeight: 700, color: '#b8960c' }}>{customers.filter(c => (c.total_revenue || 0) > 10000).length}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto" style={{ padding: '24px 36px' }}>
        {renderSection()}
      </div>
    </div>
  );
}
