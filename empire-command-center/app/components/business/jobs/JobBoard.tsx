'use client';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { API } from '../../../lib/api';
import { useJob } from '../../../hooks/useJob';
import JobFolderModal, { JobFolderTab } from '../../jobs/JobFolderModal';
import { openRecord } from '../../docs/recordBus';
import { readTheme, EmpireTheme } from '../../ThemeToggle';
import {
  ClipboardList, Clock, Play, CheckCircle2, Plus, X, Loader2,
  AlertCircle, LayoutGrid, List, ChevronRight, Save,
  Scissors, Wrench, Eye, Truck, FileCheck, Receipt, Package,
  Calendar, MapPin, Timer, FileText, DollarSign, FolderOpen,
  ArrowRight, ShieldCheck, ChevronLeft, RefreshCw
} from 'lucide-react';
import KPICard from '../shared/KPICard';
import DataTable, { Column } from '../shared/DataTable';
import StatusBadge from '../shared/StatusBadge';

// ---------------------------------------------------------------------------
// 11 Canonical Kanban Stages
// ---------------------------------------------------------------------------

interface KanbanStageSpec {
  key: string;
  label: string;
  color: string;
  bgLight: string;
}

export const KANBAN_STAGES: KanbanStageSpec[] = [
  { key: 'lead',             label: 'Lead',                  color: '#64748b', bgLight: '#f1f5f9' },
  { key: 'estimate_sent',    label: 'Estimate sent',         color: '#3b82f6', bgLight: '#eff6ff' },
  { key: 'deposit_paid',     label: 'Approved/Deposit paid', color: '#10b981', bgLight: '#ecfdf5' },
  { key: 'fabric_ordered',   label: 'Fabric ordered',        color: '#8b5cf6', bgLight: '#f5f3ff' },
  { key: 'fabric_picked_up', label: 'Fabric picked up',      color: '#d97706', bgLight: '#fffbeb' },
  { key: 'in_production',    label: 'In production',         color: '#06b6d4', bgLight: '#ecfeff' },
  { key: 'ready',            label: 'Ready',                 color: '#22c55e', bgLight: '#f0fdf4' },
  { key: 'scheduled',        label: 'Scheduled',             color: '#6366f1', bgLight: '#eef2ff' },
  { key: 'installed',        label: 'Installed/Delivered',   color: '#059669', bgLight: '#ecfdf5' },
  { key: 'final_invoice',    label: 'Final invoice',         color: '#b8960c', bgLight: '#fefce8' },
  { key: 'paid_closed',      label: 'Paid/Closed',           color: '#15803d', bgLight: '#f0fdf4' },
];

export interface PaymentStrip {
  paid: number;
  balance: number;
  total: number;
  status: string;
}

export interface JobCardData {
  id: string | number;
  _id?: string;
  job_number?: string;
  customer_id?: string | number;
  client_id?: string | number;
  quote_id?: string | number;
  client_name?: string;
  customer_name?: string;
  title?: string;
  type?: string;
  job_type?: string;
  status: string;
  canonical_stage?: string;
  next_action?: string;
  estimated_value?: number;
  quoted_amount?: number;
  total_cost?: number;
  payment_strip?: PaymentStrip;
  pickup_delivery_date?: string;
  scheduled_date?: string;
  due_date?: string;
  notes?: string;
  address?: string;
}

interface KanbanApiResponse {
  columns: {
    key: string;
    title: string;
    count: number;
    total_value: number;
    jobs: JobCardData[];
  }[];
  total_jobs: number;
  total_value: number;
}

export default function JobBoard({
  business,
  initialJobId,
  initialJobTab,
}: {
  business?: string;
  initialJobId?: string | number | null;
  initialJobTab?: JobFolderTab;
} = {}) {
  const [boardData, setBoardData] = useState<KanbanApiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'kanban' | 'list'>('kanban');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [draggedJobId, setDraggedJobId] = useState<string | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);

  // Theme support
  const [theme, setTheme] = useState<EmpireTheme>(readTheme());
  useEffect(() => {
    setTheme(readTheme());
    const sync = () => setTheme(readTheme());
    window.addEventListener('empire-theme', sync);
    return () => window.removeEventListener('empire-theme', sync);
  }, []);
  const isDark = theme === 'dark';
  const accentColor = isDark ? '#22d3ee' : '#b8960c';
  const badgeBg = isDark ? 'linear-gradient(135deg, #0891b2, #22d3ee)' : 'linear-gradient(135deg, #b8960c, #d4af37)';
  const badgeText = isDark ? '#06131a' : '#121214';
  const cardBg = isDark ? '#121821' : '#ffffff';
  const headerBg = isDark ? '#0b0f14' : '#121214';
  const headerBorder = `2px solid ${accentColor}`;
  const borderLine = isDark ? 'rgba(255, 255, 255, 0.1)' : '#ece8e0';

  // Per-job folder modal state
  const [selectedJobIdForFolder, setSelectedJobIdForFolder] = useState<string | number | null>(initialJobId || null);
  const [folderInitialTab, setFolderInitialTab] = useState<JobFolderTab>(initialJobTab || 'estimates');
  const [isFolderOpen, setIsFolderOpen] = useState(Boolean(initialJobId));

  useEffect(() => {
    if (initialJobId) {
      setSelectedJobIdForFolder(initialJobId);
      if (initialJobTab) setFolderInitialTab(initialJobTab);
      setIsFolderOpen(true);
    }
  }, [initialJobId, initialJobTab]);

  // Quick switch active job in Max context
  const { setActiveJob, activeJob } = useJob();

  const fetchKanban = useCallback(async () => {
    try {
      const q = business ? `?business=${encodeURIComponent(business)}` : '';
      const res = await fetch(`${API}/jobs/kanban${q}`);
      if (res.ok) {
        const data = await res.json();
        setBoardData(data);
      }
    } catch (e) {
      console.error('Failed to load kanban:', e);
    } finally {
      setLoading(false);
    }
  }, [business]);

  useEffect(() => {
    fetchKanban();
  }, [fetchKanban]);

  const allJobs: JobCardData[] = React.useMemo(() => {
    if (!boardData?.columns) return [];
    return boardData.columns.flatMap(c => c.jobs);
  }, [boardData]);

  const handleDragStart = (e: React.DragEvent, jobId: string | number) => {
    setDraggedJobId(String(jobId));
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(jobId));
  };

  const handleDragOver = (e: React.DragEvent, colKey: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverColumn(colKey);
  };

  const handleDragLeave = () => {
    setDragOverColumn(null);
  };

  const handleDrop = async (e: React.DragEvent, targetStageKey: string) => {
    e.preventDefault();
    setDragOverColumn(null);
    const jobId = e.dataTransfer.getData('text/plain') || draggedJobId;
    setDraggedJobId(null);
    if (!jobId) return;

    // Optimistically update column position in state
    if (boardData) {
      const nextCols = boardData.columns.map(col => {
        const movingJob = col.jobs.find(j => String(j.id) === String(jobId));
        return {
          ...col,
          jobs: col.jobs.filter(j => String(j.id) !== String(jobId)),
        };
      });

      const foundJob = allJobs.find(j => String(j.id) === String(jobId));
      if (foundJob) {
        const updatedJob = { ...foundJob, canonical_stage: targetStageKey, status: targetStageKey };
        const targetCol = nextCols.find(c => c.key === targetStageKey);
        if (targetCol) {
          targetCol.jobs.push(updatedJob);
          targetCol.count = targetCol.jobs.length;
        }
        setBoardData({
          ...boardData,
          columns: nextCols,
        });
      }
    }

    // Call API to persist stage change
    try {
      const res = await fetch(`${API}/jobs/${jobId}/stage`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stage: targetStageKey }),
      });
      if (!res.ok) {
        fetchKanban();
      }
    } catch {
      fetchKanban();
    }
  };

  const openJobFolder = (job: JobCardData, tab: JobFolderTab = 'estimates') => {
    setSelectedJobIdForFolder(job.id);
    setFolderInitialTab(tab);
    setIsFolderOpen(true);
    // Also set as active job for context
    setActiveJob(job as any);
  };

  // Mobile horizontal scroll helper
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const scrollLeft = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollBy({ left: -300, behavior: 'smooth' });
    }
  };

  const scrollRight = () => {
    if (scrollContainerRef.current) {
      scrollContainerRef.current.scrollBy({ left: 300, behavior: 'smooth' });
    }
  };

  return (
    <div
      data-jobs-scrollable="true"
      style={{
        padding: '16px 20px',
        backgroundColor: '#f5f2ed',
        minHeight: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        overflowY: 'auto',
      }}
    >
      {/* Top Header Banner: Theme-aware branding */}
      <div
        style={{
          background: headerBg,
          color: '#fff',
          borderRadius: '14px',
          padding: '16px 20px',
          borderBottom: headerBorder,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span
              style={{
                background: badgeBg,
                color: badgeText,
                fontSize: '11px',
                fontWeight: 800,
                padding: '4px 10px',
                borderRadius: '6px',
                letterSpacing: '0.5px',
              }}
            >
              EMPIRE WORKROOM
            </span>
            <h1 style={{ fontSize: '20px', fontWeight: 800, margin: 0, color: '#fff' }}>
              Job Board (Kanban)
            </h1>
          </div>
          <p style={{ fontSize: '12px', color: '#aaa', margin: '4px 0 0 0' }}>
            Live jobs pipeline across 11 stages. Tap any card or metric to open complete file folder.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {/* View toggle (min 44px tap targets) */}
          <div style={{ display: 'flex', background: isDark ? '#1a222f' : '#222', borderRadius: '8px', padding: '2px', border: `1px solid ${borderLine}` }}>
            <button
              type="button"
              onClick={() => setView('kanban')}
              style={{
                minHeight: '44px',
                padding: '6px 16px',
                borderRadius: '6px',
                border: 'none',
                background: view === 'kanban' ? accentColor : 'transparent',
                color: view === 'kanban' ? (isDark ? '#06131a' : '#121214') : '#888',
                fontWeight: 700,
                fontSize: '12px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              Kanban
            </button>
            <button
              type="button"
              onClick={() => setView('list')}
              style={{
                minHeight: '44px',
                padding: '6px 16px',
                borderRadius: '6px',
                border: 'none',
                background: view === 'list' ? accentColor : 'transparent',
                color: view === 'list' ? (isDark ? '#06131a' : '#121214') : '#888',
                fontWeight: 700,
                fontSize: '12px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              List View
            </button>
          </div>

          <button
            type="button"
            onClick={fetchKanban}
            title="Refresh jobs"
            style={{
              minHeight: '44px',
              minWidth: '44px',
              background: isDark ? '#1a222f' : '#222',
              border: `1px solid ${borderLine}`,
              borderRadius: '8px',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
            }}
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {/* KPI Stats Bar with QuickBooks-style drilldowns */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 12,
        }}
      >
        <div
          onClick={() => setStatusFilter('all')}
          style={{ background: cardBg, padding: '12px 16px', borderRadius: '12px', border: `1px solid ${borderLine}`, cursor: 'pointer' }}
          title="Click to show all jobs"
        >
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#888' }}>TOTAL LIVE JOBS</div>
          <div style={{ fontSize: '22px', fontWeight: 800, color: isDark ? '#f4f7fa' : '#1a1a1a', marginTop: 2 }}>
            {boardData?.total_jobs ?? allJobs.length}
          </div>
        </div>
        <div
          onClick={() => openRecord({ type: 'quote', id: 'pipeline' })}
          style={{ background: cardBg, padding: '12px 16px', borderRadius: '12px', border: `1px solid ${borderLine}`, cursor: 'pointer' }}
          title="Click to view quotes pipeline"
        >
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#888' }}>PIPELINE VALUE</div>
          <div style={{ fontSize: '22px', fontWeight: 800, color: accentColor, marginTop: 2 }}>
            ${Number(boardData?.total_value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>
        <div
          onClick={() => setStatusFilter('in_production')}
          style={{ background: cardBg, padding: '12px 16px', borderRadius: '12px', border: `1px solid ${borderLine}`, cursor: 'pointer' }}
          title="Click to filter jobs in production"
        >
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#888' }}>IN PRODUCTION</div>
          <div style={{ fontSize: '22px', fontWeight: 800, color: '#06b6d4', marginTop: 2 }}>
            {allJobs.filter(j => j.canonical_stage === 'in_production' || j.status === 'in_production').length}
          </div>
        </div>
        <div
          onClick={() => {
            if (activeJob) openJobFolder(activeJob as any);
          }}
          style={{ background: cardBg, padding: '12px 16px', borderRadius: '12px', border: `1px solid ${borderLine}`, cursor: activeJob ? 'pointer' : 'default' }}
          title={activeJob ? "Click to open active job folder" : undefined}
        >
          <div style={{ fontSize: '11px', fontWeight: 600, color: '#888' }}>ACTIVE MAX CHAT JOB</div>
          <div style={{ fontSize: '13px', fontWeight: 700, color: activeJob ? '#16a34a' : '#888', marginTop: 6, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {activeJob ? `${activeJob.client_name || activeJob.job_number}` : 'None selected'}
          </div>
        </div>
      </div>

      {/* View: KANBAN BOARD */}
      {view === 'kanban' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {/* Mobile column scroll guidance */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '11px', color: '#777', fontWeight: 600 }}>
              11 Pipeline Stages • Swipe sideways on phone or drag on desktop
            </span>
            <div style={{ display: 'flex', gap: 6 }}>
              <button
                type="button"
                onClick={scrollLeft}
                style={{
                  minHeight: '44px',
                  minWidth: '44px',
                  background: '#fff',
                  border: '1px solid #ece8e0',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                }}
              >
                <ChevronLeft size={16} />
              </button>
              <button
                type="button"
                onClick={scrollRight}
                style={{
                  minHeight: '44px',
                  minWidth: '44px',
                  background: '#fff',
                  border: '1px solid #ece8e0',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                }}
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>

          {/* Swipeable Columns Container (Mobile-first 390px scroll snap) */}
          <div
            ref={scrollContainerRef}
            style={{
              display: 'flex',
              gap: '12px',
              overflowX: 'auto',
              scrollSnapType: 'x mandatory',
              WebkitOverflowScrolling: 'touch',
              paddingBottom: '20px',
              scrollbarWidth: 'thin',
            }}
          >
            {KANBAN_STAGES.map((stage) => {
              const colData = boardData?.columns?.find(c => c.key === stage.key);
              const jobs = colData?.jobs || allJobs.filter(j => (j.canonical_stage || j.status) === stage.key);
              const colValue = colData?.total_value ?? jobs.reduce((acc, j) => acc + (j.estimated_value || j.quoted_amount || 0), 0);
              const isOver = dragOverColumn === stage.key;

              return (
                <div
                  key={stage.key}
                  onDragOver={(e) => handleDragOver(e, stage.key)}
                  onDragLeave={handleDragLeave}
                  onDrop={(e) => handleDrop(e, stage.key)}
                  style={{
                    flex: '0 0 290px',
                    width: '290px',
                    minWidth: '280px',
                    maxWidth: '320px',
                    scrollSnapAlign: 'start',
                    background: isOver ? '#fefce8' : '#faf9f7',
                    borderRadius: '14px',
                    border: isOver ? '2px dashed #b8960c' : '1px solid #ece8e0',
                    display: 'flex',
                    flexDirection: 'column',
                    maxHeight: '75vh',
                    transition: 'background-color 0.15s ease',
                  }}
                >
                  {/* Column Header */}
                  <div
                    style={{
                      padding: '12px 14px',
                      borderBottom: '1px solid #ece8e0',
                      background: '#fff',
                      borderTopLeftRadius: '14px',
                      borderTopRightRadius: '14px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span style={{ width: 8, height: 8, borderRadius: '50%', background: stage.color }} />
                        <span style={{ fontSize: '12px', fontWeight: 700, color: '#1a1a1a' }}>
                          {stage.label}
                        </span>
                      </div>
                      <span
                        style={{
                          fontSize: '11px',
                          fontWeight: 700,
                          background: `${stage.color}18`,
                          color: stage.color,
                          padding: '1px 7px',
                          borderRadius: '10px',
                        }}
                      >
                        {jobs.length}
                      </span>
                    </div>
                    {colValue > 0 && (
                      <div style={{ fontSize: '11px', fontWeight: 600, color: '#b8960c', marginTop: 4 }}>
                        ${colValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </div>
                    )}
                  </div>

                  {/* Cards container */}
                  <div
                    style={{
                      padding: '10px',
                      overflowY: 'auto',
                      flex: 1,
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '10px',
                    }}
                  >
                    {loading ? (
                      <div style={{ textAlign: 'center', padding: '20px', color: '#999', fontSize: '12px' }}>
                        Loading...
                      </div>
                    ) : jobs.length === 0 ? (
                      <div
                        style={{
                          textAlign: 'center',
                          padding: '30px 10px',
                          color: '#bbb',
                          fontSize: '11px',
                          border: '1px dashed #e5e2dc',
                          borderRadius: '10px',
                        }}
                      >
                        Drop job here
                      </div>
                    ) : (
                      jobs.map((job) => {
                        const clientName = job.client_name || job.customer_name || 'Client';
                        const jobName = job.title || job.job_number || `JOB-${job.id}`;
                        const value = job.estimated_value || job.quoted_amount || 0;
                        const payment = job.payment_strip || {
                          paid: 0,
                          balance: value,
                          total: value,
                          status: 'unpaid',
                        };
                        const isDragging = draggedJobId === String(job.id);
                        const isCurrentlyActiveInChat = activeJob && String(activeJob.id) === String(job.id);

                        return (
                          <div
                            key={job.id}
                            draggable
                            onDragStart={(e) => handleDragStart(e, job.id)}
                            onClick={() => openJobFolder(job)}
                            style={{
                              background: '#fff',
                              borderRadius: '12px',
                              padding: '12px 14px',
                              border: isCurrentlyActiveInChat ? '2px solid #b8960c' : '1px solid #ece8e0',
                              borderLeft: `4px solid ${stage.color}`,
                              boxShadow: isDragging
                                ? '0 10px 25px rgba(0,0,0,0.2)'
                                : '0 2px 6px rgba(0,0,0,0.04)',
                              cursor: 'pointer',
                              opacity: isDragging ? 0.4 : 1,
                              transition: 'transform 0.15s ease, box-shadow 0.15s ease',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '8px',
                            }}
                          >
                            {/* Card Top: Client & Job Name */}
                            <div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    if (job.customer_id) {
                                      openRecord({ type: 'customer', id: String(job.customer_id) });
                                    } else {
                                      openJobFolder(job);
                                    }
                                  }}
                                  style={{
                                    background: 'none',
                                    border: 'none',
                                    padding: 0,
                                    margin: 0,
                                    fontSize: '13px',
                                    fontWeight: 700,
                                    color: isDark ? '#f4f7fa' : '#1a1a1a',
                                    textAlign: 'left',
                                    cursor: 'pointer',
                                    textDecoration: job.customer_id ? 'underline' : 'none',
                                    textDecorationColor: accentColor,
                                  }}
                                >
                                  {clientName}
                                </button>
                                {isCurrentlyActiveInChat && (
                                  <span
                                    title="Active with Max"
                                    style={{
                                      fontSize: '9px',
                                      fontWeight: 800,
                                      background: '#16a34a',
                                      color: '#fff',
                                      padding: '1px 5px',
                                      borderRadius: '4px',
                                    }}
                                  >
                                    MAX
                                  </span>
                                )}
                              </div>
                              <div style={{ fontSize: '11px', color: '#666', marginTop: 2 }}>
                                {jobName}
                              </div>
                            </div>

                            {/* Next Action Chip */}
                            {job.next_action && (
                              <div
                                style={{
                                  background: isDark ? '#161f2c' : '#faf9f7',
                                  border: `1px solid ${borderLine}`,
                                  borderRadius: '6px',
                                  padding: '4px 8px',
                                  fontSize: '11px',
                                  color: isDark ? '#f4f7fa' : '#444',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: 4,
                                }}
                              >
                                <span style={{ color: accentColor, fontWeight: 700 }}>Next:</span>
                                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                  {job.next_action}
                                </span>
                              </div>
                            )}

                            {/* Pickup / Delivery date chip */}
                            {(job.pickup_delivery_date || job.due_date || job.scheduled_date) && (
                              <div
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: 4,
                                  fontSize: '10px',
                                  color: '#777',
                                }}
                              >
                                <Clock size={11} color={accentColor} />
                                <span>{job.pickup_delivery_date || job.due_date || job.scheduled_date}</span>
                              </div>
                            )}

                            {/* Payment Strip: Paid / Balance with drill-downs */}
                            <div
                              style={{
                                borderTop: `1px solid ${borderLine}`,
                                paddingTop: '8px',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                fontSize: '11px',
                              }}
                            >
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  openJobFolder(job, 'estimates');
                                }}
                                title="View estimates"
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  padding: 0,
                                  margin: 0,
                                  cursor: 'pointer',
                                  textAlign: 'left',
                                }}
                              >
                                <span style={{ color: '#888', fontSize: '10px' }}>Value: </span>
                                <strong style={{ color: isDark ? '#f4f7fa' : '#1a1a1a' }}>
                                  ${Number(value).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                                </strong>
                              </button>

                              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    openJobFolder(job, 'payments');
                                  }}
                                  title="View payments"
                                  style={{
                                    fontSize: '10px',
                                    fontWeight: 700,
                                    color: payment.paid > 0 ? '#16a34a' : '#888',
                                    background: payment.paid > 0 ? (isDark ? 'rgba(34, 197, 94, 0.2)' : '#ecfdf5') : (isDark ? 'rgba(255,255,255,0.05)' : '#f5f3ef'),
                                    padding: '3px 8px',
                                    borderRadius: '4px',
                                    border: 'none',
                                    cursor: 'pointer',
                                  }}
                                >
                                  Pd: ${Number(payment.paid || 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                                </button>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    openJobFolder(job, 'invoices');
                                  }}
                                  title="View balance & invoices"
                                  style={{
                                    fontSize: '10px',
                                    fontWeight: 700,
                                    color: payment.balance > 0 ? accentColor : '#16a34a',
                                    background: payment.balance > 0 ? (isDark ? 'rgba(34, 211, 238, 0.15)' : '#fefce8') : (isDark ? 'rgba(34, 197, 94, 0.2)' : '#ecfdf5'),
                                    padding: '3px 8px',
                                    borderRadius: '4px',
                                    border: 'none',
                                    cursor: 'pointer',
                                  }}
                                >
                                  Bal: ${Number(payment.balance || 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                                </button>
                              </div>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* View: LIST VIEW */}
      {view === 'list' && (
        <div style={{ background: '#fff', borderRadius: '14px', border: '1px solid #ece8e0', padding: '16px', overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ece8e0', textAlign: 'left', color: '#888', fontSize: '11px' }}>
                <th style={{ padding: '10px' }}>Job #</th>
                <th style={{ padding: '10px' }}>Client</th>
                <th style={{ padding: '10px' }}>Title</th>
                <th style={{ padding: '10px' }}>Stage</th>
                <th style={{ padding: '10px' }}>Next Action</th>
                <th style={{ padding: '10px' }}>Total</th>
                <th style={{ padding: '10px' }}>Paid</th>
                <th style={{ padding: '10px' }}>Balance</th>
                <th style={{ padding: '10px' }}>Date</th>
              </tr>
            </thead>
            <tbody>
              {allJobs.map((job) => {
                const stage = KANBAN_STAGES.find(s => s.key === (job.canonical_stage || job.status));
                const payment = job.payment_strip || { paid: 0, balance: 0, total: 0 };
                return (
                  <tr
                    key={job.id}
                    onClick={() => openJobFolder(job)}
                    style={{ borderBottom: '1px solid #f5f2ed', cursor: 'pointer' }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = '#fdf8eb')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = '')}
                  >
                    <td style={{ padding: '10px', fontFamily: 'monospace', fontWeight: 700, color: '#b8960c' }}>
                      {job.job_number || `JOB-${job.id}`}
                    </td>
                    <td style={{ padding: '10px', fontWeight: 600 }}>
                      {job.client_name || job.customer_name}
                    </td>
                    <td style={{ padding: '10px', color: '#555' }}>
                      {job.title || '—'}
                    </td>
                    <td style={{ padding: '10px' }}>
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '8px',
                          background: `${stage?.color || '#888'}18`,
                          color: stage?.color || '#888',
                        }}
                      >
                        {stage?.label || job.status}
                      </span>
                    </td>
                    <td style={{ padding: '10px', color: '#555' }}>
                      {job.next_action || '—'}
                    </td>
                    <td style={{ padding: '10px', fontWeight: 600 }}>
                      ${Number(job.estimated_value || job.quoted_amount || 0).toLocaleString()}
                    </td>
                    <td style={{ padding: '10px', color: '#16a34a', fontWeight: 600 }}>
                      ${Number(payment.paid || 0).toLocaleString()}
                    </td>
                    <td style={{ padding: '10px', color: '#b8960c', fontWeight: 600 }}>
                      ${Number(payment.balance || 0).toLocaleString()}
                    </td>
                    <td style={{ padding: '10px', color: '#888' }}>
                      {job.pickup_delivery_date || job.due_date || '—'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Per-Job Document Folder Modal */}
      {selectedJobIdForFolder && (
        <JobFolderModal
          jobId={selectedJobIdForFolder}
          initialTab={folderInitialTab}
          isOpen={isFolderOpen}
          onClose={() => {
            setIsFolderOpen(false);
            setSelectedJobIdForFolder(null);
          }}
          onJobUpdated={fetchKanban}
        />
      )}
    </div>
  );
}
