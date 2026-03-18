'use client';
import { useState, useEffect, useCallback, useRef } from 'react';
import { API } from '../../../lib/api';
import {
  ClipboardList, Clock, Play, CheckCircle2, Plus, X, Loader2,
  AlertCircle, LayoutGrid, List, ChevronRight, Save,
  Scissors, Wrench, Eye, Truck, FileCheck, Receipt, Package,
  Calendar, MapPin, Timer, FileText
} from 'lucide-react';
import KPICard from '../shared/KPICard';
import DataTable, { Column } from '../shared/DataTable';
import StatusBadge from '../shared/StatusBadge';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Job {
  id: string;
  _id?: string;
  title: string;
  customer_name: string;
  type?: string;
  job_type?: string;
  status: string;
  priority?: string;
  scheduled_date?: string;
  due_date?: string;
  notes?: string;
  estimated_hours?: number;
  actual_hours?: number;
  total_cost?: number;
  address?: string;
  quote_id?: string;
}

// ---------------------------------------------------------------------------
// Kanban Stage Config
// ---------------------------------------------------------------------------

interface KanbanStage {
  key: string;
  label: string;
  color: string;
  bgLight: string;
  icon: React.ReactNode;
}

const KANBAN_STAGES: KanbanStage[] = [
  { key: 'pending_materials', label: 'Pending Materials', color: '#6b7280', bgLight: '#f3f4f6', icon: <Package size={14} /> },
  { key: 'cutting',          label: 'Cutting',           color: '#2563eb', bgLight: '#eff6ff', icon: <Scissors size={14} /> },
  { key: 'fabrication',      label: 'Fabrication',       color: '#d97706', bgLight: '#fffbeb', icon: <Wrench size={14} /> },
  { key: 'quality_check',    label: 'Quality Check',     color: '#7c3aed', bgLight: '#faf5ff', icon: <Eye size={14} /> },
  { key: 'ready_for_install',label: 'Ready for Install', color: '#22c55e', bgLight: '#f0fdf4', icon: <Truck size={14} /> },
  { key: 'installed',        label: 'Installed',         color: '#059669', bgLight: '#ecfdf5', icon: <FileCheck size={14} /> },
  { key: 'invoiced',         label: 'Invoiced',          color: '#b8960c', bgLight: '#fefce8', icon: <Receipt size={14} /> },
];

// Map API statuses to kanban stage keys
const STATUS_TO_STAGE: Record<string, string> = {
  pending:     'pending_materials',
  scheduled:   'cutting',
  in_progress: 'fabrication',
  completed:   'installed',
  // Direct matches
  pending_materials:  'pending_materials',
  cutting:            'cutting',
  fabrication:        'fabrication',
  quality_check:      'quality_check',
  ready_for_install:  'ready_for_install',
  installed:          'installed',
  invoiced:           'invoiced',
};

// Reverse: stage key -> status to PATCH
const STAGE_TO_STATUS: Record<string, string> = {
  pending_materials:  'pending_materials',
  cutting:            'cutting',
  fabrication:        'fabrication',
  quality_check:      'quality_check',
  ready_for_install:  'ready_for_install',
  installed:          'installed',
  invoiced:           'invoiced',
};

function getJobStage(job: Job): string {
  return STATUS_TO_STAGE[job.status] || 'pending_materials';
}

// ---------------------------------------------------------------------------
// Priority config
// ---------------------------------------------------------------------------

const PRIORITY_BORDER: Record<string, string> = {
  urgent: '#dc2626',
  high:   '#f97316',
  normal: '#d1d5db',
  low:    '#93c5fd',
};

function getPriorityColor(priority?: string): string {
  const p = (priority || 'normal').toLowerCase();
  return PRIORITY_BORDER[p] || PRIORITY_BORDER.normal;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getDueCountdown(due?: string): { text: string; overdue: boolean } | null {
  if (!due) return null;
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  const d = new Date(due);
  d.setHours(0, 0, 0, 0);
  const diffMs = d.getTime() - now.getTime();
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return { text: 'OVERDUE', overdue: true };
  if (diffDays === 0) return { text: 'Today', overdue: false };
  if (diffDays === 1) return { text: '1 day', overdue: false };
  return { text: `${diffDays} days`, overdue: false };
}

function getJobId(job: Job): string {
  return job.id || job._id || '';
}

// ---------------------------------------------------------------------------
// Status tabs for list view
// ---------------------------------------------------------------------------

const STATUS_TABS = ['all', 'pending', 'scheduled', 'in_progress', 'completed'] as const;

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  pending:     { bg: '#f0ede8', text: '#777' },
  scheduled:   { bg: '#eff6ff', text: '#2563eb' },
  in_progress: { bg: '#fffbeb', text: '#d97706' },
  completed:   { bg: '#f0fdf4', text: '#22c55e' },
  cancelled:   { bg: '#fef2f2', text: '#dc2626' },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function JobBoard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'kanban' | 'list'>('kanban');

  // List view state
  const [statusFilter, setStatusFilter] = useState<string>('all');

  // Create from quote modal
  const [showModal, setShowModal] = useState(false);
  const [quoteId, setQuoteId] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');

  // Job detail slide-out
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [detailNotes, setDetailNotes] = useState('');
  const [detailActualHours, setDetailActualHours] = useState('');
  const [savingDetail, setSavingDetail] = useState(false);

  // Drag state
  const [dragJobId, setDragJobId] = useState<string | null>(null);
  const [dragOverStage, setDragOverStage] = useState<string | null>(null);

  // -----------------------------------------------------------------------
  // Data fetching
  // -----------------------------------------------------------------------

  const fetchJobs = useCallback(() => {
    setLoading(true);
    fetch(`${API}/jobs/`)
      .then(r => r.json())
      .then(data => {
        setJobs(Array.isArray(data) ? data : data.jobs || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => { fetchJobs(); }, [fetchJobs]);

  // -----------------------------------------------------------------------
  // KPI calculations
  // -----------------------------------------------------------------------

  const totalJobs = jobs.length;
  const inProgressCount = jobs.filter(j => {
    const s = getJobStage(j);
    return ['cutting', 'fabrication', 'quality_check', 'ready_for_install'].includes(s);
  }).length;
  const completedCount = jobs.filter(j => {
    const s = getJobStage(j);
    return ['installed', 'invoiced'].includes(s);
  }).length;
  const overdueCount = jobs.filter(j => {
    const c = getDueCountdown(j.due_date);
    return c?.overdue;
  }).length;

  // -----------------------------------------------------------------------
  // Drag & Drop handlers
  // -----------------------------------------------------------------------

  const handleDragStart = (e: React.DragEvent, jobId: string) => {
    setDragJobId(jobId);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', jobId);
  };

  const handleDragOver = (e: React.DragEvent, stageKey: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverStage(stageKey);
  };

  const handleDragLeave = () => {
    setDragOverStage(null);
  };

  const handleDrop = async (e: React.DragEvent, stageKey: string) => {
    e.preventDefault();
    setDragOverStage(null);
    const jobId = e.dataTransfer.getData('text/plain') || dragJobId;
    setDragJobId(null);
    if (!jobId) return;

    const job = jobs.find(j => getJobId(j) === jobId);
    if (!job) return;
    if (getJobStage(job) === stageKey) return;

    const newStatus = STAGE_TO_STATUS[stageKey] || stageKey;

    // Optimistic update
    setJobs(prev => prev.map(j =>
      getJobId(j) === jobId ? { ...j, status: newStatus } : j
    ));

    try {
      const res = await fetch(`${API}/jobs/${jobId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (!res.ok) {
        // Revert on failure
        fetchJobs();
      }
    } catch {
      fetchJobs();
    }
  };

  const handleDragEnd = () => {
    setDragJobId(null);
    setDragOverStage(null);
  };

  // -----------------------------------------------------------------------
  // Create from Quote
  // -----------------------------------------------------------------------

  const handleCreateFromQuote = async () => {
    if (!quoteId.trim()) return;
    setCreating(true);
    setCreateError('');
    try {
      const res = await fetch(`${API}/jobs/from-quote/${quoteId.trim()}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
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

  // -----------------------------------------------------------------------
  // Job Detail slide-out
  // -----------------------------------------------------------------------

  const openJobDetail = (job: Job) => {
    setSelectedJob(job);
    setDetailNotes(job.notes || '');
    setDetailActualHours(job.actual_hours != null ? String(job.actual_hours) : '');
  };

  const closeJobDetail = () => {
    setSelectedJob(null);
  };

  const saveJobDetail = async () => {
    if (!selectedJob) return;
    setSavingDetail(true);
    try {
      const body: any = { notes: detailNotes };
      if (detailActualHours.trim()) {
        body.actual_hours = parseFloat(detailActualHours);
      }
      const res = await fetch(`${API}/jobs/${getJobId(selectedJob)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        fetchJobs();
        const updated = await res.json();
        setSelectedJob(prev => prev ? { ...prev, ...updated, notes: detailNotes, actual_hours: body.actual_hours ?? prev.actual_hours } : null);
      }
    } catch { /* silent */ } finally {
      setSavingDetail(false);
    }
  };

  const quickChangeStatus = async (newStatus: string) => {
    if (!selectedJob) return;
    try {
      const res = await fetch(`${API}/jobs/${getJobId(selectedJob)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        setSelectedJob(prev => prev ? { ...prev, status: newStatus } : null);
        setJobs(prev => prev.map(j =>
          getJobId(j) === getJobId(selectedJob) ? { ...j, status: newStatus } : j
        ));
      }
    } catch { /* silent */ }
  };

  // -----------------------------------------------------------------------
  // List view config (preserved from original)
  // -----------------------------------------------------------------------

  const filtered = statusFilter === 'all'
    ? jobs
    : jobs.filter(j => j.status === statusFilter);

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

  // -----------------------------------------------------------------------
  // Render
  // -----------------------------------------------------------------------

  return (
    <div style={{ padding: '24px 36px', background: '#f5f3ef', minHeight: '100vh' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-xl font-bold text-[#1a1a1a] flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-[#f0fdf4] flex items-center justify-center">
            <ClipboardList size={18} className="text-[#22c55e]" />
          </div>
          Job Board
        </h2>
        <div className="flex items-center gap-3">
          {/* View toggle */}
          <div className="flex items-center rounded-xl overflow-hidden border border-[#ece8e0]" style={{ height: 44 }}>
            <button
              onClick={() => setView('kanban')}
              className="flex items-center gap-1.5 px-4 text-xs font-bold transition-colors cursor-pointer"
              style={{
                height: '100%',
                background: view === 'kanban' ? '#b8960c' : '#fff',
                color: view === 'kanban' ? '#fff' : '#777',
              }}
            >
              <LayoutGrid size={14} /> Kanban
            </button>
            <button
              onClick={() => setView('list')}
              className="flex items-center gap-1.5 px-4 text-xs font-bold transition-colors cursor-pointer"
              style={{
                height: '100%',
                background: view === 'list' ? '#b8960c' : '#fff',
                color: view === 'list' ? '#fff' : '#777',
              }}
            >
              <List size={14} /> List
            </button>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1.5 px-4 text-xs font-bold text-white rounded-xl hover:bg-[#16a34a] transition-colors cursor-pointer"
            style={{ height: 44, background: '#22c55e' }}
          >
            <Plus size={14} /> Create from Quote
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPICard icon={<ClipboardList size={18} />} label="Total Jobs" value={loading ? '...' : String(totalJobs)} color="#b8960c" />
        <KPICard icon={<Play size={18} />} label="In Progress" value={loading ? '...' : String(inProgressCount)} color="#2563eb" />
        <KPICard icon={<CheckCircle2 size={18} />} label="Completed" value={loading ? '...' : String(completedCount)} color="#22c55e" />
        <KPICard icon={<AlertCircle size={18} />} label="Overdue" value={loading ? '...' : String(overdueCount)} color="#dc2626" />
      </div>

      {/* ================================================================= */}
      {/* KANBAN VIEW                                                        */}
      {/* ================================================================= */}
      {view === 'kanban' && (
        <div style={{ display: 'flex', gap: 12, overflowX: 'auto', paddingBottom: 16 }}>
          {KANBAN_STAGES.map(stage => {
            const stageJobs = jobs.filter(j => getJobStage(j) === stage.key);
            const isDragOver = dragOverStage === stage.key;
            return (
              <div
                key={stage.key}
                onDragOver={(e) => handleDragOver(e, stage.key)}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(e, stage.key)}
                style={{
                  flex: '1 1 0',
                  minWidth: 220,
                  maxWidth: 280,
                  display: 'flex',
                  flexDirection: 'column',
                }}
              >
                {/* Column header */}
                <div
                  style={{
                    background: '#fff',
                    borderRadius: '12px 12px 0 0',
                    borderTop: `3px solid ${stage.color}`,
                    padding: '12px 14px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div className="flex items-center gap-2">
                    <span style={{ color: stage.color }}>{stage.icon}</span>
                    <span className="text-xs font-bold text-[#1a1a1a]">{stage.label}</span>
                  </div>
                  <span
                    className="text-[10px] font-bold"
                    style={{
                      background: stage.bgLight,
                      color: stage.color,
                      padding: '2px 8px',
                      borderRadius: 20,
                    }}
                  >
                    {stageJobs.length}
                  </span>
                </div>

                {/* Cards container */}
                <div
                  style={{
                    flex: 1,
                    background: isDragOver ? stage.bgLight : '#f0ede8',
                    borderRadius: '0 0 12px 12px',
                    padding: 8,
                    minHeight: 120,
                    transition: 'background 0.15s ease',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 8,
                  }}
                >
                  {loading ? (
                    <>
                      {[1, 2].map(i => (
                        <div key={i} style={{ background: '#fff', borderRadius: 12, padding: 14, opacity: 0.5 }}>
                          <div className="h-3 bg-[#ece8e0] rounded animate-pulse mb-2" style={{ width: '70%' }} />
                          <div className="h-2 bg-[#ece8e0] rounded animate-pulse" style={{ width: '50%' }} />
                        </div>
                      ))}
                    </>
                  ) : (
                    stageJobs.map(job => {
                      const countdown = getDueCountdown(job.due_date);
                      const serviceType = job.type || job.job_type || '';
                      const isDragging = dragJobId === getJobId(job);
                      return (
                        <div
                          key={getJobId(job)}
                          draggable
                          onDragStart={(e) => handleDragStart(e, getJobId(job))}
                          onDragEnd={handleDragEnd}
                          onClick={() => openJobDetail(job)}
                          style={{
                            background: '#fff',
                            borderRadius: 12,
                            padding: '12px 14px',
                            boxShadow: isDragging
                              ? '0 8px 24px rgba(0,0,0,0.15)'
                              : '0 1px 3px rgba(0,0,0,0.06)',
                            borderLeft: `4px solid ${getPriorityColor(job.priority)}`,
                            cursor: 'grab',
                            opacity: isDragging ? 0.5 : 1,
                            transition: 'box-shadow 0.15s ease, opacity 0.15s ease',
                          }}
                        >
                          <div className="text-sm font-bold text-[#1a1a1a] mb-1 truncate">
                            {job.customer_name || 'Unknown'}
                          </div>
                          {job.title && (
                            <div className="text-[11px] text-[#777] mb-2 truncate">
                              {job.title}
                            </div>
                          )}
                          <div className="flex items-center justify-between gap-2">
                            {serviceType && (
                              <span
                                className="text-[10px] font-semibold capitalize truncate"
                                style={{
                                  background: '#f0ede8',
                                  color: '#777',
                                  padding: '2px 8px',
                                  borderRadius: 6,
                                  maxWidth: '60%',
                                }}
                              >
                                {serviceType}
                              </span>
                            )}
                            {countdown && (
                              <span
                                className="text-[10px] font-bold whitespace-nowrap"
                                style={{
                                  color: countdown.overdue ? '#dc2626' : '#777',
                                  background: countdown.overdue ? '#fef2f2' : 'transparent',
                                  padding: countdown.overdue ? '2px 6px' : 0,
                                  borderRadius: 6,
                                }}
                                suppressHydrationWarning
                              >
                                {countdown.overdue ? 'OVERDUE' : countdown.text}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                  {!loading && stageJobs.length === 0 && (
                    <div className="flex items-center justify-center text-[11px] text-[#bbb]" style={{ minHeight: 60 }}>
                      No jobs
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ================================================================= */}
      {/* LIST VIEW                                                          */}
      {/* ================================================================= */}
      {view === 'list' && (
        <>
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

          <DataTable
            columns={columns}
            data={filtered}
            loading={loading}
            emptyMessage="No jobs found."
            onRowClick={(row) => openJobDetail(row)}
          />
        </>
      )}

      {/* ================================================================= */}
      {/* JOB DETAIL SLIDE-OUT                                               */}
      {/* ================================================================= */}
      {selectedJob && (
        <>
          {/* Backdrop */}
          <div
            onClick={closeJobDetail}
            style={{
              position: 'fixed', inset: 0, zIndex: 40,
              background: 'rgba(0,0,0,0.3)',
              transition: 'opacity 0.2s ease',
            }}
          />
          {/* Panel */}
          <div
            style={{
              position: 'fixed', top: 0, right: 0, bottom: 0,
              width: '100%', maxWidth: 480,
              zIndex: 50,
              background: '#fff',
              boxShadow: '-8px 0 30px rgba(0,0,0,0.1)',
              overflowY: 'auto',
              padding: 28,
            }}
          >
            {/* Close */}
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-base font-bold text-[#1a1a1a] truncate pr-4">
                {selectedJob.title || selectedJob.customer_name}
              </h3>
              <button
                onClick={closeJobDetail}
                className="text-[#bbb] hover:text-[#555] cursor-pointer transition-colors shrink-0"
              >
                <X size={20} />
              </button>
            </div>

            {/* Status breadcrumb */}
            <div className="mb-6">
              <div className="text-[10px] font-bold text-[#999] uppercase tracking-wider mb-2">Progress</div>
              <div className="flex items-center gap-0 overflow-x-auto pb-1">
                {KANBAN_STAGES.map((stage, idx) => {
                  const currentStageIdx = KANBAN_STAGES.findIndex(s => s.key === getJobStage(selectedJob));
                  const isActive = idx <= currentStageIdx;
                  const isCurrent = idx === currentStageIdx;
                  return (
                    <div key={stage.key} className="flex items-center shrink-0">
                      <div
                        className="flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-bold"
                        style={{
                          background: isCurrent ? stage.color : isActive ? stage.bgLight : '#f5f3ef',
                          color: isCurrent ? '#fff' : isActive ? stage.color : '#ccc',
                          transition: 'all 0.15s ease',
                        }}
                      >
                        {stage.icon}
                        <span className="hidden sm:inline">{stage.label.split(' ')[0]}</span>
                      </div>
                      {idx < KANBAN_STAGES.length - 1 && (
                        <ChevronRight size={12} className="mx-0.5 text-[#ddd] shrink-0" />
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Quick status change */}
            <div className="mb-6">
              <div className="text-[10px] font-bold text-[#999] uppercase tracking-wider mb-2">Quick Status</div>
              <div className="flex flex-wrap gap-1.5">
                {KANBAN_STAGES.map(stage => {
                  const isCurrentStage = getJobStage(selectedJob) === stage.key;
                  return (
                    <button
                      key={stage.key}
                      onClick={() => quickChangeStatus(STAGE_TO_STATUS[stage.key])}
                      className="text-[10px] font-bold px-3 py-1.5 rounded-lg cursor-pointer transition-all"
                      style={{
                        background: isCurrentStage ? stage.color : stage.bgLight,
                        color: isCurrentStage ? '#fff' : stage.color,
                        border: `1px solid ${isCurrentStage ? stage.color : 'transparent'}`,
                      }}
                    >
                      {stage.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Info grid */}
            <div className="space-y-3 mb-6">
              <div className="grid grid-cols-2 gap-3">
                <InfoRow icon={<ClipboardList size={13} />} label="Customer" value={selectedJob.customer_name || '--'} />
                <InfoRow icon={<FileText size={13} />} label="Type" value={selectedJob.type || selectedJob.job_type || '--'} />
                <InfoRow icon={<Calendar size={13} />} label="Scheduled" value={selectedJob.scheduled_date ? new Date(selectedJob.scheduled_date).toLocaleDateString() : '--'} />
                <InfoRow icon={<Calendar size={13} />} label="Due Date" value={selectedJob.due_date ? new Date(selectedJob.due_date).toLocaleDateString() : '--'} />
                <InfoRow icon={<MapPin size={13} />} label="Address" value={selectedJob.address || '--'} />
                <InfoRow
                  icon={<Receipt size={13} />}
                  label="Total Cost"
                  value={selectedJob.total_cost != null ? `$${Number(selectedJob.total_cost).toLocaleString()}` : '--'}
                  valueColor="#b8960c"
                />
              </div>
              {selectedJob.quote_id && (
                <InfoRow icon={<FileText size={13} />} label="Quote ID" value={selectedJob.quote_id} />
              )}
            </div>

            {/* Time tracking */}
            <div className="mb-6">
              <div className="text-[10px] font-bold text-[#999] uppercase tracking-wider mb-2">Time Tracking</div>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-xl border border-[#ece8e0] bg-[#faf9f7]">
                  <div className="text-[10px] text-[#999] mb-1">Estimated Hours</div>
                  <div className="text-sm font-bold text-[#1a1a1a]">
                    <Timer size={13} className="inline mr-1 text-[#999]" />
                    {selectedJob.estimated_hours ?? '--'}
                  </div>
                </div>
                <div className="p-3 rounded-xl border border-[#ece8e0] bg-[#faf9f7]">
                  <div className="text-[10px] text-[#999] mb-1">Actual Hours</div>
                  <input
                    type="number"
                    value={detailActualHours}
                    onChange={(e) => setDetailActualHours(e.target.value)}
                    placeholder="0"
                    className="w-full text-sm font-bold text-[#1a1a1a] bg-transparent outline-none"
                    step="0.5"
                    min="0"
                  />
                </div>
              </div>
              {/* Progress bar */}
              {selectedJob.estimated_hours != null && selectedJob.estimated_hours > 0 && (
                <div className="mt-2">
                  <div className="h-2 rounded-full bg-[#ece8e0] overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${Math.min(100, ((parseFloat(detailActualHours) || 0) / selectedJob.estimated_hours) * 100)}%`,
                        background: (parseFloat(detailActualHours) || 0) > selectedJob.estimated_hours ? '#dc2626' : '#22c55e',
                      }}
                    />
                  </div>
                  <div className="text-[10px] text-[#999] mt-1" suppressHydrationWarning>
                    {Math.round(((parseFloat(detailActualHours) || 0) / selectedJob.estimated_hours) * 100)}% of estimate
                  </div>
                </div>
              )}
            </div>

            {/* Notes */}
            <div className="mb-6">
              <div className="text-[10px] font-bold text-[#999] uppercase tracking-wider mb-2">Notes</div>
              <textarea
                value={detailNotes}
                onChange={(e) => setDetailNotes(e.target.value)}
                rows={4}
                className="w-full px-3.5 py-2.5 text-sm border border-[#ece8e0] rounded-xl bg-[#faf9f7] text-[#1a1a1a] placeholder-[#bbb] focus:outline-none focus:border-[#b8960c] transition-colors resize-none"
                placeholder="Add job notes..."
              />
            </div>

            {/* Save button */}
            <button
              onClick={saveJobDetail}
              disabled={savingDetail}
              className="flex items-center justify-center gap-2 w-full text-xs font-bold text-white rounded-xl hover:opacity-90 transition-all cursor-pointer disabled:opacity-50"
              style={{ height: 44, background: '#b8960c' }}
            >
              {savingDetail ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
              Save Changes
            </button>
          </div>
        </>
      )}

      {/* ================================================================= */}
      {/* CREATE FROM QUOTE MODAL                                            */}
      {/* ================================================================= */}
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
              <button onClick={() => { setShowModal(false); setCreateError(''); }} className="px-3.5 py-2.5 text-xs font-medium text-[#999] border border-[#ece8e0] rounded-xl hover:bg-[#faf9f7] transition-colors cursor-pointer" style={{ height: 44 }}>
                Cancel
              </button>
              <button
                onClick={handleCreateFromQuote}
                disabled={creating || !quoteId.trim()}
                className="flex items-center gap-1.5 px-4 text-xs font-bold text-white bg-[#22c55e] rounded-xl hover:bg-[#16a34a] transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ height: 44 }}
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

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function InfoRow({ icon, label, value, valueColor }: {
  icon: React.ReactNode;
  label: string;
  value: string;
  valueColor?: string;
}) {
  return (
    <div className="flex items-start gap-2 p-3 rounded-xl border border-[#ece8e0] bg-[#faf9f7]">
      <span className="text-[#bbb] mt-0.5 shrink-0">{icon}</span>
      <div className="min-w-0">
        <div className="text-[10px] text-[#999]">{label}</div>
        <div className="text-xs font-medium truncate" style={{ color: valueColor || '#1a1a1a' }}>{value}</div>
      </div>
    </div>
  );
}
