'use client';
import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { TrendingUp, DollarSign, Clock, AlertTriangle } from 'lucide-react';
import { EmpireShell } from '../components/ui/EmpireShell';
import { EmpireDataPanel } from '../components/ui/EmpireDataPanel';
import { EmpireStatusPill } from '../components/ui/EmpireStatusPill';

const API = 'http://localhost:8000/api/v1';

interface Invoice {
  id: string;
  client: string;
  amount: number;
  status: 'paid' | 'partial' | 'overdue';
  date: string;
}

interface FinanceStats {
  ytd_revenue?: number;
  yoy_growth?: number;
  run_rate?: number;
}

export default function FinancePage() {
  const [activeTab, setActiveTab] = useState<'all' | 'paid' | 'overdue'>('all');
  const [stats, setStats] = useState<FinanceStats>({});
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/finance/stats`)
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setStats(d); })
      .catch(() => {});

    fetch(`${API}/invoices`)
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (d?.invoices) setInvoices(d.invoices);
        else setInvoices(getDefaultInvoices());
      })
      .catch(() => { setInvoices(getDefaultInvoices()); })
      .finally(() => setLoading(false));
  }, []);

  const ytd = stats.ytd_revenue ?? 47200;
  const yoy = stats.yoy_growth ?? 12.4;
  const runRate = stats.run_rate ?? 3800000;
  const outstanding = invoices.filter(i => i.status !== 'paid').reduce((s, i) => s + i.amount, 0);

  const revenueData = [
    { month: 'Jan', revenue: 32000 },
    { month: 'Feb', revenue: 38000 },
    { month: 'Mar', revenue: 41000 },
    { month: 'Apr', revenue: 47200 },
  ];

  const plData = [
    { name: 'Gross Revenue', value: 10, fill: 'var(--success)' },
    { name: 'COGS', value: 20, fill: 'var(--error)' },
    { name: 'OpEx', value: 20, fill: 'var(--warning)' },
    { name: 'Net Profit', value: 23, fill: 'var(--accent-primary)' },
  ];

  const expenseData = [
    { name: 'Materials', value: 32, fill: '#6366f1' },
    { name: 'Labor', value: 41, fill: '#8b5cf6' },
    { name: 'Shipping', value: 15, fill: '#f59e0b' },
    { name: 'Software', value: 12, fill: '#10b981' },
  ];

  const filteredInvoices = invoices.filter(i => {
    if (activeTab === 'all') return true;
    if (activeTab === 'paid') return i.status === 'paid';
    return i.status === 'overdue';
  });

  return (
    <EmpireShell commitHash="f535d53">
      <div className="animated-gradient" style={{ padding: 'var(--space-6)' }}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: '2fr 1fr',
          gap: 'var(--space-4)',
          marginBottom: 'var(--space-4)',
        }}>
          {/* Revenue Overview — 2/3 */}
          <EmpireDataPanel title="Revenue Overview" subtitle="YTD performance" glass>
            <div style={{ height: 200 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={revenueData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="month" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                  <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                  <Tooltip contentStyle={{ background: 'var(--panel-bg)', border: '1px solid var(--border-subtle)', borderRadius: 8 }} />
                  <Line type="monotone" dataKey="revenue" stroke="var(--accent-primary)" strokeWidth={2} dot={{ fill: 'var(--accent-primary)' }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-4)', marginTop: 'var(--space-4)' }}>
              {[
                { label: 'YTD Revenue', value: `$${(ytd / 1000).toFixed(1)}K` },
                { label: 'vs Last Year', value: `+${yoy}%`, color: 'var(--success)' },
                { label: 'Run Rate', value: `$${(runRate / 1000000).toFixed(1)}M` },
              ].map(s => (
                <div key={s.label} style={{ flex: 1, textAlign: 'center', padding: 'var(--space-3)', background: 'rgba(255,255,255,0.04)', borderRadius: 'var(--radius-md)' }}>
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 2 }}>{s.label}</p>
                  <p style={{ fontSize: 'var(--text-lg)', fontWeight: 700, color: s.color || 'var(--text-primary)' }}>{s.value}</p>
                </div>
              ))}
            </div>
          </EmpireDataPanel>

          {/* Invoices — 1/3 */}
          <EmpireDataPanel title="Invoices" subtitle="Recent invoices" glass>
            {/* Tabs */}
            <div style={{ display: 'flex', gap: 'var(--space-2)', marginBottom: 'var(--space-3)' }}>
              {(['all', 'paid', 'overdue'] as const).map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  style={{
                    flex: 1,
                    padding: '4px 8px',
                    background: activeTab === tab ? 'var(--accent-primary)' : 'rgba(255,255,255,0.06)',
                    border: 'none',
                    borderRadius: 'var(--radius-sm)',
                    color: activeTab === tab ? '#fff' : 'var(--text-muted)',
                    fontSize: 'var(--text-xs)',
                    fontWeight: activeTab === tab ? 600 : 400,
                    cursor: 'pointer',
                    textTransform: 'capitalize',
                  }}
                >
                  {tab}
                </button>
              ))}
            </div>

            {/* Invoice list */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', maxHeight: 260, overflowY: 'auto' }}>
              {loading ? (
                <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>Loading...</p>
              ) : filteredInvoices.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>No invoices</p>
              ) : filteredInvoices.map(inv => (
                <div key={inv.id} style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: 'var(--space-2)',
                  background: 'rgba(255,255,255,0.04)',
                  borderRadius: 'var(--radius-sm)',
                }}>
                  <div>
                    <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-primary)' }}>{inv.id}</p>
                    <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{inv.client}</p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-primary)' }}>${inv.amount.toLocaleString()}</p>
                    <EmpireStatusPill
                      status={inv.status === 'paid' ? 'success' : inv.status === 'overdue' ? 'error' : 'warning'}
                      label={inv.status}
                      size="sm"
                    />
                  </div>
                </div>
              ))}
            </div>

            <div style={{
              marginTop: 'var(--space-3)',
              padding: 'var(--space-3)',
              background: 'rgba(245,158,11,0.1)',
              border: '1px solid var(--warning-border)',
              borderRadius: 'var(--radius-md)',
            }}>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--warning)' }}>
                Total Outstanding: <strong>${outstanding.toLocaleString()}</strong>
              </p>
            </div>
          </EmpireDataPanel>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 'var(--space-4)',
        }}>
          {/* P&L Summary */}
          <EmpireDataPanel title="P&L Summary" subtitle="Profit & Loss breakdown" glass>
            <div style={{ height: 180 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={plData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} unit="%" />
                  <YAxis type="category" dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} width={80} />
                  <Tooltip contentStyle={{ background: 'var(--panel-bg)', border: '1px solid var(--border-subtle)', borderRadius: 8 }} />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                    {plData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', marginTop: 'var(--space-3)' }}>
              {plData.map(item => (
                <div key={item.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <div style={{ width: 8, height: 8, borderRadius: 2, background: item.fill }} />
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>{item.name}</span>
                  </div>
                  <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-primary)' }}>{item.value}%</span>
                </div>
              ))}
              <div style={{ borderTop: '1px solid var(--border-accent)', paddingTop: 'var(--space-2)', display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-primary)' }}>Net Margin</span>
                <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--accent-primary)' }}>23%</span>
              </div>
            </div>
          </EmpireDataPanel>

          {/* Expenses Tracker */}
          <EmpireDataPanel title="Expenses Tracker" subtitle="Cost distribution" glass>
            <div style={{ height: 180 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={expenseData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                    {expenseData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: 'var(--panel-bg)', border: '1px solid var(--border-subtle)', borderRadius: 8 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', marginTop: 'var(--space-3)' }}>
              {expenseData.map(item => (
                <div key={item.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <div style={{ width: 8, height: 8, borderRadius: 2, background: item.fill }} />
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>{item.name}</span>
                  </div>
                  <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-primary)' }}>{item.value}%</span>
                </div>
              ))}
            </div>
          </EmpireDataPanel>
        </div>
      </div>
    </EmpireShell>
  );
}

function getDefaultInvoices(): Invoice[] {
  return [
    { id: 'INV-2024-08765', client: 'Alex Morgan', amount: 3063, status: 'paid', date: '2024-04-26' },
    { id: 'INV-2024-08764', client: 'Sarah Chen', amount: 4200, status: 'paid', date: '2024-04-20' },
    { id: 'INV-2024-08763', client: 'James Park', amount: 1850, status: 'overdue', date: '2024-03-15' },
    { id: 'INV-2024-08762', client: 'Lisa Wong', amount: 2900, status: 'partial', date: '2024-04-10' },
    { id: 'INV-2024-08761', client: 'Mike Johnson', amount: 3100, status: 'paid', date: '2024-04-05' },
  ];
}
