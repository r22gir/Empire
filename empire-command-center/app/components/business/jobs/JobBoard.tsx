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
  pending:     { bg: 'bg-gray-100',   text: 'text-gray-600' },
  scheduled:   { bg: 'bg-blue-50',    text: 'text-blue-700' },
  in_progress: { bg: 'bg-amber-50',   text: 'text-amber-700' },
  completed:   { bg: 'bg-green-50',   text: 'text-green-700' },
  cancelled:   { bg: 'bg-red-50',     text: 'text-red-700' },
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
    { key: 'title', label: 'Title', sortable: true, render: (row) => <span className="text-sm font-semibold text-[#1a1a1a]">{row.title || '--'}</span> },
    { key: 'customer_name', label: 'Customer', sortable: true },
    { key: 'type', label: 'Type', sortable: true, render: (row) => <span className="text-xs text-[#555] capitalize">{row.type || row.job_type || '--'}</span> },
    {
      key: 'priority', label: 'Priority', sortable: true,
      render: (row) => {
        const p = (row.priority || 'normal').toLowerCase();
        const colors: Record<string, string> = { high: 'text-red-600 bg-red-50', urgent: 'text-red-700 bg-red-100', normal: 'text-gray-600 bg-gray-100', low: 'text-blue-600 bg-blue-50' };
        return <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full capitalize ${colors[p] || colors.normal}`}>{p}</span>;
      },
    },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status || 'pending'} colorMap={STATUS_COLORS} /> },
    {
      key: 'scheduled_date', label: 'Scheduled', sortable: true,
      render: (row) => <span className="text-xs text-[#777]" suppressHydrationWarning>{row.scheduled_date ? new Date(row.scheduled_date).toLocaleDateString() : '--'}</span>,
    },
    {
      key: 'due_date', label: 'Due Date', sortable: true,
      render: (row) => <span className="text-xs text-[#777]" suppressHydrationWarning>{row.due_date ? new Date(row.due_date).toLocaleDateString() : '--'}</span>,
    },
  ];

  return (
    <div className="max-w-5xl mx-auto px-8 py-6">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-lg font-bold text-[#1a1a1a] flex items-center gap-2">
          <ClipboardList size={20} className="text-[#16a34a]" /> Job Board
        </h2>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-1.5 px-3 py-2 text-xs font-bold text-white bg-[#16a34a] rounded-lg hover:bg-[#15803d] transition-colors cursor-pointer"
        >
          <Plus size={14} /> Create from Quote
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPICard icon={<ClipboardList size={18} />} label="Total Jobs" value={loading ? '...' : String(totalJobs)} color="#16a34a" />
        <KPICard icon={<Clock size={18} />} label="Scheduled" value={loading ? '...' : String(scheduled)} color="#2563eb" />
        <KPICard icon={<Play size={18} />} label="In Progress" value={loading ? '...' : String(inProgress)} color="#d97706" />
        <KPICard icon={<CheckCircle2 size={18} />} label="Completed" value={loading ? '...' : String(completed)} color="#16a34a" />
      </div>

      {/* Status filter tabs */}
      <div className="flex items-center gap-1 mb-4 bg-white border border-[#ece8e1] rounded-lg p-1 w-fit">
        {STATUS_TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setStatusFilter(tab)}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors cursor-pointer capitalize ${
              statusFilter === tab
                ? 'bg-[#16a34a] text-white'
                : 'text-[#777] hover:bg-[#f5f3ef] hover:text-[#1a1a1a]'
            }`}
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
          <div className="mt-2 bg-white border border-[#ece8e1] rounded-lg p-5 animate-in slide-in-from-top-2">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-bold text-[#1a1a1a]">{job.title} - Details</h4>
              <button onClick={() => setExpandedId(null)} className="text-[#999] hover:text-[#555] cursor-pointer">
                <X size={16} />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-4 text-xs">
              <div>
                <div className="text-[10px] font-bold text-[#999] uppercase mb-1">Notes</div>
                <div className="text-[#555] p-2 bg-[#faf9f7] rounded border border-[#ece8e1] min-h-[40px]">{job.notes || 'No notes.'}</div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between p-2 bg-[#faf9f7] rounded border border-[#ece8e1]">
                  <span className="text-[#777]">Hours Estimated</span>
                  <span className="font-bold text-[#1a1a1a]">{job.estimated_hours ?? '--'}</span>
                </div>
                <div className="flex justify-between p-2 bg-[#faf9f7] rounded border border-[#ece8e1]">
                  <span className="text-[#777]">Hours Logged</span>
                  <span className="font-bold text-[#1a1a1a]">{job.actual_hours ?? '--'}</span>
                </div>
                <div className="flex justify-between p-2 bg-[#faf9f7] rounded border border-[#ece8e1]">
                  <span className="text-[#777]">Total Cost</span>
                  <span className="font-bold text-[#b8960c]">{job.total_cost != null ? `$${Number(job.total_cost).toLocaleString()}` : '--'}</span>
                </div>
                {job.address && (
                  <div className="flex justify-between p-2 bg-[#faf9f7] rounded border border-[#ece8e1]">
                    <span className="text-[#777]">Address</span>
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
          <div className="bg-white rounded-xl border border-[#e5e0d8] shadow-xl w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-[#1a1a1a]">Create Job from Quote</h3>
              <button onClick={() => { setShowModal(false); setCreateError(''); }} className="text-[#999] hover:text-[#555] cursor-pointer">
                <X size={18} />
              </button>
            </div>
            <div className="mb-4">
              <label className="block text-xs font-medium text-[#555] mb-1">Quote ID</label>
              <input
                type="text"
                value={quoteId}
                onChange={e => setQuoteId(e.target.value)}
                placeholder="Enter quote ID..."
                className="w-full px-3 py-2 text-sm border border-[#ece8e1] rounded-lg bg-white text-gray-700 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#16a34a]/30 focus:border-[#16a34a] transition-colors"
              />
            </div>
            {createError && (
              <div className="mb-3 flex items-center gap-2 p-2 rounded-lg bg-red-50 border border-red-200">
                <AlertCircle size={14} className="text-red-500 shrink-0" />
                <span className="text-xs text-red-600">{createError}</span>
              </div>
            )}
            <div className="flex justify-end gap-2">
              <button onClick={() => { setShowModal(false); setCreateError(''); }} className="px-3 py-2 text-xs font-medium text-[#555] border border-[#ece8e1] rounded-lg hover:bg-[#f5f3ef] transition-colors cursor-pointer">
                Cancel
              </button>
              <button
                onClick={handleCreateFromQuote}
                disabled={creating || !quoteId.trim()}
                className="flex items-center gap-1.5 px-3 py-2 text-xs font-bold text-white bg-[#16a34a] rounded-lg hover:bg-[#15803d] transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
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
