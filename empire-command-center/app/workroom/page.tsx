'use client';
import React, { useState, useEffect } from 'react';
import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd';
import type { DraggableProvided, DroppableProvided } from '@hello-pangea/dnd';
import {
  Clock, DollarSign, Users, BarChart3, Search, Plus,
  Send, FileText, Download, RefreshCw, ChevronRight
} from 'lucide-react';
import { EmpireShell } from '../components/ui/EmpireShell';
import { EmpireDataPanel } from '../components/ui/EmpireDataPanel';
import { EmpireStatusPill } from '../components/ui/EmpireStatusPill';

const API = 'http://localhost:8000/api/v1';

interface Job {
  id: string;
  title: string;
  client: string;
  status: 'prospect' | 'quote_sent' | 'approved' | 'in_production' | 'complete';
  urgency: 'red' | 'amber' | 'green';
  amount?: number;
  created_at?: string;
}

interface Customer {
  id: string;
  name: string;
  lastActivity: string;
  type: 'email' | 'call' | 'visit';
}

const COLUMNS = [
  { id: 'prospect', label: 'Prospect' },
  { id: 'quote_sent', label: 'Quote Sent' },
  { id: 'approved', label: 'Approved' },
  { id: 'in_production', label: 'In Production' },
  { id: 'complete', label: 'Complete' },
] as const;

const DEFAULT_JOBS: Job[] = [
  { id: '1', title: 'Drapery Installation', client: 'Alex Morgan', status: 'approved', urgency: 'green', amount: 3200, created_at: '2024-04-20' },
  { id: '2', title: 'Roman Shades', client: 'Sarah Chen', status: 'in_production', urgency: 'amber', amount: 1800, created_at: '2024-04-18' },
  { id: '3', title: 'Upholstery - Sofa', client: 'James Park', status: 'prospect', urgency: 'red', amount: 4500, created_at: '2024-04-25' },
  { id: '4', title: 'Cornice Build', client: 'Lisa Wong', status: 'quote_sent', urgency: 'green', amount: 890, created_at: '2024-04-22' },
  { id: '5', title: 'Banquette Cushions', client: 'Mike Johnson', status: 'complete', urgency: 'green', amount: 2400, created_at: '2024-04-15' },
  { id: '6', title: 'Pillow Set', client: 'Emma Davis', status: 'in_production', urgency: 'amber', amount: 620, created_at: '2024-04-21' },
  { id: '7', title: 'Drapery - Bay Window', client: 'Tom Wilson', status: 'approved', urgency: 'red', amount: 3800, created_at: '2024-04-24' },
  { id: '8', title: 'Sheer Drapery', client: 'Anna Lee', status: 'prospect', urgency: 'green', amount: 1200, created_at: '2024-04-26' },
];

const DEFAULT_CUSTOMERS: Customer[] = [
  { id: '1', name: 'Alex Morgan', lastActivity: '2h ago', type: 'email' },
  { id: '2', name: 'Sarah Chen', lastActivity: '1d ago', type: 'call' },
  { id: '3', name: 'James Park', lastActivity: '3d ago', type: 'visit' },
  { id: '4', name: 'Lisa Wong', lastActivity: '5d ago', type: 'email' },
];

export default function WorkroomPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [customerSearch, setCustomerSearch] = useState('');
  const [customers] = useState<Customer[]>(DEFAULT_CUSTOMERS);

  useEffect(() => {
    fetch(`${API}/workroom/jobs`)
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (d?.jobs) setJobs(d.jobs);
        else setJobs(DEFAULT_JOBS);
      })
      .catch(() => setJobs(DEFAULT_JOBS))
      .finally(() => setLoading(false));
  }, []);

  const onDragEnd = (result: DropResult) => {
    const { source, destination, draggableId } = result;
    if (!destination || (source.droppableId === destination.droppableId && source.index === destination.index)) return;

    setJobs(prev => {
      const updated = prev.map(job => {
        if (job.id === draggableId) {
          return { ...job, status: destination.droppableId as Job['status'] };
        }
        return job;
      });

      // Persist to backend
      const movedJob = updated.find(j => j.id === draggableId);
      if (movedJob) {
        fetch(`${API}/workroom/jobs/${draggableId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: movedJob.status }),
        }).catch(() => {});
      }
      return updated;
    });
  };

  const jobsByColumn = (status: string) => jobs.filter(j => j.status === status);

  const pendingQuotes = jobs.filter(j => j.status === 'prospect' || j.status === 'quote_sent').length;
  const activeJobs = jobs.filter(j => j.status === 'approved' || j.status === 'in_production').length;
  const revenue = jobs.filter(j => j.status === 'complete').reduce((s, j) => s + (j.amount || 0), 0);

  const filteredCustomers = customers.filter(c =>
    c.name.toLowerCase().includes(customerSearch.toLowerCase())
  );

  return (
    <EmpireShell commitHash="f535d53">
      <div className="animated-gradient" style={{ padding: 'var(--space-6)' }}>
        {/* Top Stats Bar */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 'var(--space-4)',
          marginBottom: 'var(--space-4)',
        }}>
          {[
            { label: 'Pending Quotes', value: pendingQuotes.toString(), icon: <Clock size={16} />, color: 'warning' },
            { label: 'Active Jobs', value: activeJobs.toString(), icon: <BarChart3 size={16} />, color: 'info' },
            { label: 'Revenue', value: `$${revenue.toLocaleString()}`, icon: <DollarSign size={16} />, color: 'success' },
            { label: 'Collection Rate', value: '96.3%', icon: <Users size={16} />, color: 'success' },
          ].map((s) => (
            <div key={s.label} className="glass-premium" style={{
              padding: 'var(--space-4)',
              borderRadius: 'var(--radius-lg)',
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-3)',
            }}>
              <span style={{ color: `var(--${s.color})` }}>{s.icon}</span>
              <div>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px' }}>{s.label}</p>
                <p style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--text-primary)' }}>{s.value}</p>
              </div>
            </div>
          ))}
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 280px',
          gap: 'var(--space-4)',
        }}>
          {/* Kanban Board */}
          <EmpireDataPanel title="Job Board" subtitle="Internal Kanban" glass noPadding>
            <div style={{
              display: 'flex',
              gap: 'var(--space-3)',
              overflowX: 'auto',
              padding: 'var(--space-4)',
              minHeight: 500,
            }}>
              <DragDropContext onDragEnd={onDragEnd}>
                {COLUMNS.map((col) => (
                  <div key={col.id} style={{ minWidth: 220, flex: 1 }}>
                    <Droppable droppableId={col.id}>
                      {(provided: DroppableProvided, snapshot: any) => (
                        <div
                          ref={provided.innerRef}
                          {...provided.droppableProps}
                          className="glass-premium"
                          style={{
                            minHeight: 460,
                            padding: 'var(--space-3)',
                            borderRadius: 'var(--radius-lg)',
                            background: snapshot.isDraggingOver
                              ? 'rgba(99,102,241,0.15)'
                              : 'rgba(30,41,59,0.5)',
                            transition: 'background 0.2s',
                          }}
                        >
                          <div style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            marginBottom: 'var(--space-3)',
                          }}>
                            <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                              {col.label}
                            </span>
                            <span style={{
                              fontSize: 'var(--text-xs)',
                              fontWeight: 700,
                              background: 'rgba(255,255,255,0.08)',
                              color: 'var(--text-muted)',
                              padding: '1px 6px',
                              borderRadius: 'var(--radius-full)',
                            }}>
                              {jobsByColumn(col.id).length}
                            </span>
                          </div>

                          {jobsByColumn(col.id).map((job, index) => (
                            <Draggable key={job.id} draggableId={job.id} index={index}>
                              {(provided: DraggableProvided, snapshot: any) => (
                                <div
                                  ref={provided.innerRef}
                                  {...provided.draggableProps}
                                  {...provided.dragHandleProps}
                                  className="glass-premium"
                                  style={{
                                    padding: 'var(--space-3)',
                                    marginBottom: 'var(--space-2)',
                                    borderRadius: 'var(--radius-md)',
                                    cursor: 'grab',
                                    transform: snapshot.isDragging ? 'rotate(2deg)' : 'none',
                                    boxShadow: snapshot.isDragging
                                      ? '0 8px 24px rgba(0,0,0,0.5)'
                                      : 'none',
                                    ...provided.draggableProps.style,
                                  }}
                                >
                                  <p style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
                                    {job.title}
                                  </p>
                                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 6 }}>
                                    {job.client}
                                  </p>
                                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <EmpireStatusPill
                                      status={job.urgency === 'green' ? 'success' : job.urgency === 'amber' ? 'warning' : 'error'}
                                      label={job.urgency}
                                      size="sm"
                                    />
                                    {job.amount && (
                                      <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--accent-primary)' }}>
                                        ${job.amount.toLocaleString()}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              )}
                            </Draggable>
                          ))}
                          {provided.placeholder}
                        </div>
                      )}
                    </Droppable>
                  </div>
                ))}
              </DragDropContext>
            </div>
          </EmpireDataPanel>

          {/* Right Sidebar: CRM */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            <EmpireDataPanel title="Customers" subtitle="Recent" glass>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: 'var(--space-2)',
                marginBottom: 'var(--space-3)',
              }}>
                <Search size={12} style={{ color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  placeholder="Search..."
                  value={customerSearch}
                  onChange={(e) => setCustomerSearch(e.target.value)}
                  style={{
                    flex: 1,
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-primary)',
                    fontSize: 'var(--text-xs)',
                    outline: 'none',
                  }}
                />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {filteredCustomers.map((c) => (
                  <div key={c.id} style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: 'var(--space-2)',
                    background: 'rgba(255,255,255,0.04)',
                    borderRadius: 'var(--radius-sm)',
                  }}>
                    <span style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--text-primary)' }}>{c.name}</span>
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{c.lastActivity}</span>
                  </div>
                ))}
              </div>
            </EmpireDataPanel>

            <EmpireDataPanel title="Activity" subtitle="Recent" glass>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {[
                  { text: 'Email sent to Alex Morgan', time: '2h ago', icon: <Send size={12} /> },
                  { text: 'Call with Sarah Chen', time: '1d ago', icon: <Users size={12} /> },
                  { text: 'Visit from James Park', time: '3d ago', icon: <Users size={12} /> },
                ].map((a, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <span style={{ color: 'var(--accent-primary)' }}>{a.icon}</span>
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', flex: 1 }}>{a.text}</span>
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{a.time}</span>
                  </div>
                ))}
              </div>
            </EmpireDataPanel>
          </div>
        </div>

        {/* Bottom Action Bar */}
        <div style={{
          display: 'flex',
          gap: 'var(--space-3)',
          marginTop: 'var(--space-4)',
        }}>
          {[
            { label: 'New Quote', icon: <Plus size={14} />, variant: 'primary' as const },
            { label: 'New Job', icon: <Plus size={14} />, variant: 'secondary' as const },
            { label: 'Send Reminder', icon: <Send size={14} />, variant: 'secondary' as const },
            { label: 'Export Report', icon: <Download size={14} />, variant: 'secondary' as const },
          ].map((action) => (
            <button
              key={action.label}
              className={action.variant === 'primary' ? 'button-glow' : ''}
              style={{
                padding: 'var(--space-2) var(--space-4)',
                background: action.variant === 'primary'
                  ? 'var(--accent-primary)'
                  : 'rgba(255,255,255,0.06)',
                border: action.variant === 'secondary'
                  ? '1px solid rgba(255,255,255,0.12)'
                  : 'none',
                borderRadius: 'var(--radius-md)',
                color: '#fff',
                fontWeight: 500,
                fontSize: 'var(--text-sm)',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
              }}
            >
              {action.icon}
              {action.label}
            </button>
          ))}
        </div>
      </div>
    </EmpireShell>
  );
}
