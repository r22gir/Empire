'use client';
import { useState, useEffect } from 'react';
import { API } from '../../../lib/api';
import {
  ClipboardList, Clock, Play, CheckCircle2, Plus, X, Loader2,
  ChevronDown, ChevronUp, AlertCircle
} from 'lucide-react';
import KPICard from '../shared/KPICard';
import DataTable, { Column } from '../shared/DataTable';
import StatusBadge from '../shared/StatusBadge';

const STATUS_TABS = ['all', 'pending', 'scheduled', 'in_progress', 'completed'] as const;

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  pending:     { bg: '#f0ede8', text: '#777' },
  scheduled:   { bg: '#eff6ff', text: '#2563eb' },
  in_progress: { bg: '#fffbeb', text: '#d97706' },
  completed:   { bg: '#f0fdf4', text: '#22c55e' },
  cancelled:   { bg: '#fef2f2', text: '#dc2626' },
};

export default function JobBoard() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showModal, setShowModal] = useState(false);
  const [quoteId, setQuoteId] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');

  const fetchJobs = () => {
    setLoading(true);
    fetch(`${API}/jobs/`)
      .then(r => r.json())
      .then(data => {
        setJobs(Array.isArray(data) ? data : data.jobs || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => { fetchJobs(); }, []);

  const filtered = statusFilter === 'all'
    ? jobs
    : jobs.filter(j => j.status === statusFilter);

  const totalJobs = jobs.length;
  const scheduled = jobs.filter(j => j.status === 'scheduled').length;
  const inProgress = jobs.filter(j => j.status === 'in_progress').length;
  const completed = jobs.filter(j => j.status === 'completed').length;

  const handleCreateFromQuote = async () => {
    if (!quoteId.trim()) return;
    setCreating(true);
    setCreateError('');
    try {
      const res = await fetch(`${API}/jobs/from-quote/${quoteId.trim()}`, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `Error ${res.status}` }));
        throw new Error(err.detail || `Error ${res.status}`);
      }
      setShowModal(false);
      setQuoteId('');
      fetchJobs();
    } catch (e: any) {
      setCreateError(e.message || 'Failed to create job');
    } finally {
      setCreating(false);
    }
  };

  const columns: Column[] = [
    { key: 'title', label: 'Title', sortable: true, render: (row) => <span className="text-sm font-bold text-[#1a1a1a]">{row.title || '--'}</span> },
    { key: 'customer_name', label: 'Customer', sortable: true },
    { key: 'type', label: 'Type', sortable: true, render: (row) => <span className="text-xs text-[#555] capitalize">{row.type || row.job_type || '--'}</span> },
    {
      key: 'priority', label: 'Priority', sortable: true,
      render: (row) => {
        const p = (row.priority || 'normal').toLowerCase();
        const colorMap: Record<string, { bg: string; text: string }> = {
          high: { bg: '#fef2f2', text: '#dc2626' },
          urgent: { bg: '#fef2f2', text: '#dc2626' },
          normal: { bg: '#f0ede8', text: '#777' },
          low: { bg: '#eff6ff', text: '#2563eb' },
        };
        const c = colorMap[p] || colorMap.normal;
        return <span className="status-pill capitalize" style={{ backgroundColor: c.bg, color: c.text }}>{p}</span>;
      },
    },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status || 'pending'} colorMap={STATUS_COLORS} /> },
    {
      key: 'scheduled_date', label: 'Scheduled', sortable: true,
      render: (row) => <span className="text-xs text-[#999]" suppressHydrationWarning>{row.scheduled_date ? new Date(row.scheduled_date).toLocaleDateString() : '--'}</span>,
    },
    {
      key: 'due_date', label: 'Due Date', sortable: true,
      render: (row) => <span className="text-xs text-[#999]" suppressHydrationWarning>{row.due_date ? new Date(row.due_date).toLocaleDateString() : '--'}</span>,
    },
  ];

  return (
    <div className="max-w-5xl mx-auto" style={{ padding: '24px 36px' }}>
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-xl font-bold text-[#1a1a1a] flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-[#f0fdf4] flex items-center justify-center">
            <ClipboardList size={18} className="text-[#22c55e]" />
          </div>
          Job Board
        </h2>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-1.5 px-4 py-2.5 text-xs font-bold text-white bg-[#22c55e] rounded-xl hover:bg-[#16a34a] transition-colors cursor-pointer"
        >
          <Plus size={14} /> Create from Quote
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPICard icon={<ClipboardList size={18} />} label="Total Jobs" value={loading ? '...' : String(totalJobs)} color="#22c55e" />
        <KPICard icon={<Clock size={18} />} label="Scheduled" value={loading ? '...' : String(scheduled)} color="#2563eb" />
        <KPICard icon={<Play size={18} />} label="In Progress" value={loading ? '...' : String(inProgress)} color="#d97706" />
        <KPICard icon={<CheckCircle2 size={18} />} label="Completed" value={loading ? '...' : String(completed)} color="#22c55e" />
      </div>

      {/* Status filter tabs */}
      <div className="flex items-center gap-1 mb-5 empire-card flat" style={{ padding: 4, width: 'fit-content' }}>
        {STATUS_TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setStatusFilter(tab)}
            className={`filter-tab ${statusFilter === tab ? 'active' : ''}`}
            style={{ textTransform: 'capitalize' }}
          >
            {tab === 'in_progress' ? 'In Progress' : tab}
          </button>
        ))}
      </div>

      {/* DataTable with expandable rows */}
      <DataTable
        columns={columns}
        data={filtered}
        loading={loading}
        emptyMessage="No jobs found."
        onRowClick={(row) => setExpandedId(expandedId === (row.id || row._id) ? null : (row.id || row._id))}
      />

      {/* Expanded detail rows */}
      {expandedId && (() => {
        const job = filtered.find(j => (j.id || j._id) === expandedId);
        if (!job) return null;
        return (
          <div className="mt-3 empire-card flat" style={{ padding: 20 }}>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-bold text-[#1a1a1a]">{job.title} - Details</h4>
              <button onClick={() => setExpandedId(null)} className="text-[#bbb] hover:text-[#555] cursor-pointer transition-colors">
                <X size={16} />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <div className="section-label" style={{ fontSize: 10 }}>Notes</div>
                <div className="text-[#555] p-3 bg-[#faf9f7] rounded-xl border border-[#ece8e0] min-h-[40px]">{job.notes || 'No notes.'}</div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between p-3 bg-[#faf9f7] rounded-xl border border-[#ece8e0]">
                  <span className="text-[#999]">Hours Estimated</span>
                  <span className="font-bold text-[#1a1a1a]">{job.estimated_hours ?? '--'}</span>
                </div>
                <div className="flex justify-between p-3 bg-[#faf9f7] rounded-xl border border-[#ece8e0]">
                  <span className="text-[#999]">Hours Logged</span>
                  <span className="font-bold text-[#1a1a1a]">{job.actual_hours ?? '--'}</span>
                </div>
                <div className="flex justify-between p-3 bg-[#faf9f7] rounded-xl border border-[#ece8e0]">
                  <span className="text-[#999]">Total Cost</span>
                  <span className="font-bold text-[#b8960c]">{job.total_cost != null ? `$${Number(job.total_cost).toLocaleString()}` : '--'}</span>
                </div>
                {job.address && (
                  <div className="flex justify-between p-3 bg-[#faf9f7] rounded-xl border border-[#ece8e0]">
                    <span className="text-[#999]">Address</span>
                    <span className="font-medium text-[#555]">{job.address}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        );
      })()}

      {/* Create from Quote Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="empire-card" style={{ padding: 24, width: '100%', maxWidth: 384, boxShadow: '0 20px 60px rgba(0,0,0,0.12)' }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-[#1a1a1a]">Create Job from Quote</h3>
              <button onClick={() => { setShowModal(false); setCreateError(''); }} className="text-[#bbb] hover:text-[#555] cursor-pointer transition-colors">
                <X size={18} />
              </button>
            </div>
            <div className="mb-4">
              <label className="section-label" style={{ fontSize: 10 }}>Quote ID</label>
              <input
                type="text"
                value={quoteId}
                onChange={e => setQuoteId(e.target.value)}
                placeholder="Enter quote ID..."
                className="w-full px-3.5 py-2.5 text-sm border border-[#ece8e0] rounded-[14px] bg-[#faf9f7] text-[#1a1a1a] placeholder-[#bbb] focus:outline-none focus:border-[#22c55e] transition-colors"
              />
            </div>
            {createError && (
              <div className="mb-3 flex items-center gap-2 p-3 rounded-xl" style={{ background: '#fef2f2', border: '1px solid #fca5a5' }}>
                <AlertCircle size={14} className="text-red-500 shrink-0" />
                <span className="text-xs text-red-600">{createError}</span>
              </div>
            )}
            <div className="flex justify-end gap-2">
              <button onClick={() => { setShowModal(false); setCreateError(''); }} className="px-3.5 py-2.5 text-xs font-medium text-[#999] border border-[#ece8e0] rounded-xl hover:bg-[#faf9f7] transition-colors cursor-pointer">
                Cancel
              </button>
              <button
                onClick={handleCreateFromQuote}
                disabled={creating || !quoteId.trim()}
                className="flex items-center gap-1.5 px-4 py-2.5 text-xs font-bold text-white bg-[#22c55e] rounded-xl hover:bg-[#16a34a] transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {creating && <Loader2 size={12} className="animate-spin" />}
                Create Job
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
