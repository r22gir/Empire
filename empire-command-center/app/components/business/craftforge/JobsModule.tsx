'use client';
import React, { useState, useEffect, useCallback } from 'react';
import { API } from '../../../lib/api';
import {
  ClipboardList, Loader2, Clock, CheckCircle2, Play
} from 'lucide-react';
import DataTable, { Column } from '../shared/DataTable';
import StatusBadge from '../shared/StatusBadge';
import SearchBar from '../shared/SearchBar';
import EmptyState from '../shared/EmptyState';

const JOB_STATUSES = ['all', 'queued', 'cutting', 'printing', 'sanding', 'finishing', 'assembly', 'complete'] as const;

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  queued: { bg: '#f5f3ef', text: '#888' },
  cutting: { bg: '#eff6ff', text: '#2563eb' },
  printing: { bg: '#faf5ff', text: '#7c3aed' },
  sanding: { bg: '#fffbeb', text: '#d97706' },
  finishing: { bg: '#fdf8eb', text: '#b8960c' },
  assembly: { bg: '#f0fdf4', text: '#16a34a' },
  complete: { bg: '#f0fdf4', text: '#22c55e' },
  shipped: { bg: '#f0fdf4', text: '#22c55e' },
  cancelled: { bg: '#fef2f2', text: '#dc2626' },
};

const PRIORITY_ICONS: Record<string, { color: string; label: string }> = {
  low: { color: '#999', label: 'Low' },
  normal: { color: '#2563eb', label: 'Normal' },
  high: { color: '#d97706', label: 'High' },
  urgent: { color: '#dc2626', label: 'Urgent' },
};

export default function JobsModule() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [updating, setUpdating] = useState<string | null>(null);

  const fetchJobs = useCallback(() => {
    setLoading(true);
    const url = statusFilter !== 'all'
      ? `${API}/craftforge/jobs?status=${statusFilter}`
      : `${API}/craftforge/jobs`;
    fetch(url)
      .then(r => r.json())
      .then(data => {
        setJobs(Array.isArray(data) ? data : data.jobs || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [statusFilter]);

  useEffect(() => { fetchJobs(); }, [fetchJobs]);

  const updateStatus = async (jobId: string, newStatus: string) => {
    setUpdating(jobId);
    try {
      await fetch(`${API}/craftforge/jobs/${jobId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      fetchJobs();
    } catch (e) {
      console.error('Job update failed:', e);
    } finally {
      setUpdating(null);
    }
  };

  const getNextStatus = (current: string): string | null => {
    const flow = ['queued', 'cutting', 'sanding', 'finishing', 'assembly', 'complete'];
    const idx = flow.indexOf(current);
    if (idx >= 0 && idx < flow.length - 1) return flow[idx + 1];
    return null;
  };

  const filtered = jobs.filter(j => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (j.customer_name || '').toLowerCase().includes(q) ||
           (j.job_number || '').toLowerCase().includes(q) ||
           (j.description || '').toLowerCase().includes(q);
  });

  const columns: Column[] = [
    { key: 'job_number', label: '#', sortable: true, render: (row) => <span style={{ fontSize: 12, fontWeight: 700, color: '#b8960c', fontFamily: 'monospace' }}>{row.job_number || '--'}</span> },
    { key: 'customer_name', label: 'Customer', sortable: true, render: (row) => <span style={{ fontSize: 13, fontWeight: 600, color: '#1a1a1a' }}>{row.customer_name || '--'}</span> },
    { key: 'description', label: 'Description', render: (row) => <span style={{ fontSize: 12, color: '#555' }} className="truncate block max-w-[200px]">{row.description || '--'}</span> },
    { key: 'machine', label: 'Machine', render: (row) => <span style={{ fontSize: 12, color: '#777' }}>{row.machine || '--'}</span> },
    {
      key: 'priority', label: 'Priority',
      render: (row) => {
        const p = PRIORITY_ICONS[row.priority] || PRIORITY_ICONS.normal;
        return <span style={{ fontSize: 11, fontWeight: 700, color: p.color }}>{p.label}</span>;
      },
    },
    { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status || 'queued'} colorMap={STATUS_COLORS} /> },
    {
      key: 'estimated_time_min', label: 'Est. Time',
      render: (row) => {
        const mins = row.estimated_time_min || 0;
        if (mins === 0) return <span style={{ fontSize: 12, color: '#999' }}>--</span>;
        const hrs = Math.floor(mins / 60);
        const rem = Math.round(mins % 60);
        return <span style={{ fontSize: 12, color: '#555' }}>{hrs > 0 ? `${hrs}h ${rem}m` : `${rem}m`}</span>;
      },
    },
    {
      key: 'due_date', label: 'Due',
      render: (row) => {
        if (!row.due_date) return <span style={{ fontSize: 11, color: '#999' }}>--</span>;
        const due = new Date(row.due_date);
        const now = new Date();
        const isOverdue = due < now && row.status !== 'complete';
        return <span style={{ fontSize: 11, fontWeight: isOverdue ? 700 : 400, color: isOverdue ? '#dc2626' : '#777' }} suppressHydrationWarning>{due.toLocaleDateString()}</span>;
      },
    },
    {
      key: 'actions', label: '',
      render: (row) => {
        const next = getNextStatus(row.status);
        if (!next || row.status === 'complete') return null;
        return (
          <button
            onClick={(e) => { e.stopPropagation(); updateStatus(row.id, next); }}
            disabled={updating === row.id}
            className="flex items-center gap-1 text-[11px] font-bold text-[#b8960c] hover:text-[#a68500] cursor-pointer transition-colors"
            style={{ background: 'none', border: 'none', whiteSpace: 'nowrap' }}
          >
            {updating === row.id ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
            {next.charAt(0).toUpperCase() + next.slice(1)}
          </button>
        );
      },
    },
  ];

  // Summary stats
  const queued = jobs.filter(j => j.status === 'queued').length;
  const inProgress = jobs.filter(j => ['cutting', 'printing', 'sanding', 'finishing', 'assembly'].includes(j.status)).length;
  const completed = jobs.filter(j => j.status === 'complete').length;

  return (
    <div style={{ maxWidth: 1060, margin: '0 auto', padding: '24px 36px' }}>
      <div className="flex items-center justify-between mb-4">
        <h2 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }} className="flex items-center gap-2">
          <ClipboardList size={20} className="text-[#b8960c]" /> Production Jobs
        </h2>
        <div className="w-56">
          <SearchBar value={search} onChange={setSearch} placeholder="Search jobs..." />
        </div>
      </div>

      {/* Summary pills */}
      <div className="flex gap-3 mb-4">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" style={{ background: '#f5f3ef', border: '1px solid #ece8e0' }}>
          <Clock size={13} className="text-[#888]" />
          <span style={{ fontSize: 12, fontWeight: 600, color: '#555' }}>{queued} queued</span>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" style={{ background: '#eff6ff', border: '1px solid #bfdbfe' }}>
          <Play size={13} className="text-[#2563eb]" />
          <span style={{ fontSize: 12, fontWeight: 600, color: '#2563eb' }}>{inProgress} in progress</span>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" style={{ background: '#f0fdf4', border: '1px solid #bbf7d0' }}>
          <CheckCircle2 size={13} className="text-[#22c55e]" />
          <span style={{ fontSize: 12, fontWeight: 600, color: '#22c55e' }}>{completed} complete</span>
        </div>
      </div>

      {/* Status filter tabs */}
      <div className="flex gap-2 mb-4 flex-wrap">
        {JOB_STATUSES.map(s => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`filter-tab capitalize ${statusFilter === s ? 'active' : ''}`}
          >
            {s === 'all' ? 'All' : s}
          </button>
        ))}
      </div>

      <DataTable columns={columns} data={filtered} loading={loading} emptyMessage="No production jobs found. Jobs are created from design quotes." />
    </div>
  );
}
