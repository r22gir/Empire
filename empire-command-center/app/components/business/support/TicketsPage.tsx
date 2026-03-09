'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Headphones, Plus, X, Send, ChevronDown, AlertTriangle, Clock, CheckCircle2, Inbox } from 'lucide-react';
import { API } from '../../../lib/api';
import KPICard from '../shared/KPICard';
import DataTable, { Column } from '../shared/DataTable';
import SearchBar from '../shared/SearchBar';
import StatusBadge from '../shared/StatusBadge';
import EmptyState from '../shared/EmptyState';

const STATUS_TABS = ['all', 'open', 'in_progress', 'waiting', 'resolved', 'closed'] as const;
const PRIORITY_OPTIONS = ['all', 'urgent', 'high', 'normal', 'low'] as const;
const CHANNEL_OPTIONS = ['email', 'phone', 'chat', 'portal'] as const;

const PRIORITY_COLORS: Record<string, { bg: string; text: string }> = {
  urgent: { bg: '#fef2f2', text: '#dc2626' },
  high:   { bg: '#fff7ed', text: '#ea580c' },
  normal: { bg: '#eff6ff', text: '#2563eb' },
  low:    { bg: '#f0ede8', text: '#777' },
};

const TICKET_STATUS_MAP: Record<string, { bg: string; text: string }> = {
  open:        { bg: '#eff6ff', text: '#2563eb' },
  in_progress: { bg: '#faf5ff', text: '#7c3aed' },
  waiting:     { bg: '#fffbeb', text: '#d97706' },
  resolved:    { bg: '#f0fdf4', text: '#22c55e' },
  closed:      { bg: '#f0ede8', text: '#999' },
};

interface Ticket {
  id: string;
  subject: string;
  description?: string;
  status: string;
  priority: string;
  customer_name?: string;
  customer_id?: string;
  assigned_to?: string;
  channel?: string;
  created_at?: string;
  updated_at?: string;
  messages?: TicketMessage[];
}

interface TicketMessage {
  id: string;
  sender: string;
  content: string;
  created_at: string;
  is_staff?: boolean;
}

export default function TicketsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [priorityFilter, setPriorityFilter] = useState<string>('all');
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [showNewModal, setShowNewModal] = useState(false);

  const [endpointAvailable, setEndpointAvailable] = useState(true);

  const fetchTickets = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter !== 'all') params.set('status', statusFilter);
      if (priorityFilter !== 'all') params.set('priority', priorityFilter);
      params.set('limit', '100');
      const qs = params.toString();
      const res = await fetch(`${API}/tickets/${qs ? '?' + qs : ''}`);
      if (!res.ok) {
        if (res.status === 404 || res.status === 500) {
          setEndpointAvailable(false);
          setTickets([]);
          return;
        }
        throw new Error('Failed to fetch');
      }
      setEndpointAvailable(true);
      const data = await res.json();
      setTickets(data.tickets || data || []);
    } catch {
      setEndpointAvailable(false);
      setTickets([]);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, priorityFilter]);

  useEffect(() => { fetchTickets(); }, [fetchTickets]);

  const filtered = useMemo(() => {
    if (!search) return tickets;
    const q = search.toLowerCase();
    return tickets.filter(t =>
      (t.subject || '').toLowerCase().includes(q) ||
      (t.customer_name || '').toLowerCase().includes(q) ||
      (t.id || '').toLowerCase().includes(q)
    );
  }, [tickets, search]);

  const kpis = useMemo(() => {
    const open = tickets.filter(t => t.status === 'open').length;
    const inProgress = tickets.filter(t => t.status === 'in_progress').length;
    const today = new Date().toDateString();
    const resolvedToday = tickets.filter(t =>
      t.status === 'resolved' && t.updated_at && new Date(t.updated_at).toDateString() === today
    ).length;
    return { open, inProgress, resolvedToday };
  }, [tickets]);

  const columns: Column[] = [
    {
      key: 'id', label: 'ID', sortable: true,
      render: (row: Ticket) => (
        <span className="font-mono text-xs text-[#999]">{(row.id || '').slice(0, 8)}...</span>
      ),
    },
    { key: 'subject', label: 'Subject', sortable: true },
    { key: 'customer_name', label: 'Customer', sortable: true },
    {
      key: 'priority', label: 'Priority', sortable: true,
      render: (row: Ticket) => {
        const colors = PRIORITY_COLORS[row.priority] || PRIORITY_COLORS.normal;
        return (
          <span className="status-pill capitalize" style={{ backgroundColor: colors.bg, color: colors.text }}>
            {row.priority}
          </span>
        );
      },
    },
    {
      key: 'status', label: 'Status', sortable: true,
      render: (row: Ticket) => <StatusBadge status={row.status} colorMap={TICKET_STATUS_MAP} />,
    },
    {
      key: 'created_at', label: 'Created', sortable: true,
      render: (row: Ticket) => (
        <span className="text-xs text-[#999]" suppressHydrationWarning>
          {row.created_at ? new Date(row.created_at).toLocaleDateString() : '--'}
        </span>
      ),
    },
    {
      key: 'updated_at', label: 'Updated', sortable: true,
      render: (row: Ticket) => (
        <span className="text-xs text-[#999]" suppressHydrationWarning>
          {row.updated_at ? new Date(row.updated_at).toLocaleDateString() : '--'}
        </span>
      ),
    },
  ];

  return (
    <div className="max-w-6xl mx-auto" style={{ padding: '24px 36px' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#faf5ff] flex items-center justify-center">
            <Headphones size={20} className="text-[#7c3aed]" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[#1a1a1a]">Support Tickets</h1>
            <p className="text-[11px] text-[#999]">Manage customer support requests</p>
          </div>
        </div>
        <button
          onClick={() => setShowNewModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 text-xs font-bold text-white bg-[#7c3aed] rounded-xl hover:bg-[#6d28d9] transition-colors cursor-pointer"
        >
          <Plus size={16} /> New Ticket
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPICard icon={<Inbox size={18} />} label="Open Tickets" value={String(kpis.open)} color="#2563eb" />
        <KPICard icon={<Clock size={18} />} label="In Progress" value={String(kpis.inProgress)} color="#7c3aed" />
        <KPICard icon={<CheckCircle2 size={18} />} label="Resolved Today" value={String(kpis.resolvedToday)} color="#22c55e" />
        <KPICard icon={<AlertTriangle size={18} />} label="Avg Response Time" value="--" color="#b8960c" />
      </div>

      {/* Status Tabs */}
      <div className="flex items-center gap-1 mb-5 empire-card flat" style={{ padding: 4, width: 'fit-content' }}>
        {STATUS_TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setStatusFilter(tab)}
            className={`filter-tab ${statusFilter === tab ? 'active' : ''}`}
            style={{ textTransform: 'capitalize' }}
          >
            {tab.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      {/* Priority Filter + Search */}
      <div className="flex items-center gap-3 mb-5">
        <select
          value={priorityFilter}
          onChange={e => setPriorityFilter(e.target.value)}
          className="px-3 py-2.5 border border-[#ece8e0] rounded-[14px] text-xs bg-[#faf9f7] outline-none focus:border-[#b8960c] transition-colors"
        >
          {PRIORITY_OPTIONS.map(p => (
            <option key={p} value={p}>{p === 'all' ? 'All Priorities' : p.charAt(0).toUpperCase() + p.slice(1)}</option>
          ))}
        </select>
        <div className="flex-1 max-w-xs">
          <SearchBar value={search} onChange={setSearch} placeholder="Search tickets..." />
        </div>
      </div>

      {/* Table */}
      <DataTable
        columns={columns}
        data={filtered}
        loading={loading}
        onRowClick={setSelectedTicket}
        emptyMessage={endpointAvailable ? "No tickets found." : "Connect backend endpoint to enable tickets."}
      />

      {/* Ticket Detail Panel */}
      {selectedTicket && (
        <TicketDetailPanel
          ticket={selectedTicket}
          onClose={() => setSelectedTicket(null)}
          onUpdate={fetchTickets}
        />
      )}

      {/* New Ticket Modal */}
      {showNewModal && (
        <NewTicketModal
          onClose={() => setShowNewModal(false)}
          onCreated={() => { setShowNewModal(false); fetchTickets(); }}
        />
      )}
    </div>
  );
}

// ── Ticket Detail Panel ─────────────────────────────────────────────

function TicketDetailPanel({ ticket, onClose, onUpdate }: { ticket: Ticket; onClose: () => void; onUpdate: () => void }) {
  const [detail, setDetail] = useState<Ticket>(ticket);
  const [messages, setMessages] = useState<TicketMessage[]>([]);
  const [reply, setReply] = useState('');
  const [sending, setSending] = useState(false);
  const [status, setStatus] = useState(ticket.status);
  const [loadingMessages, setLoadingMessages] = useState(true);

  useEffect(() => {
    fetch(`${API}/tickets/${ticket.id}`)
      .then(r => r.json())
      .then(data => {
        setDetail(data);
        setStatus(data.status || ticket.status);
        setMessages(data.messages || []);
        setLoadingMessages(false);
      })
      .catch(() => setLoadingMessages(false));
  }, [ticket.id, ticket.status]);

  const handleStatusChange = async (newStatus: string) => {
    setStatus(newStatus);
    try {
      await fetch(`${API}/tickets/${ticket.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      onUpdate();
    } catch {}
  };

  const handleReply = async () => {
    if (!reply.trim() || sending) return;
    setSending(true);
    try {
      const res = await fetch(`${API}/tickets/${ticket.id}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: reply, sender: 'staff', is_staff: true }),
      });
      if (res.ok) {
        const msg = await res.json();
        setMessages(prev => [...prev, msg]);
        setReply('');
      }
    } catch {} finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={onClose}>
      <div className="empire-card" style={{ padding: 0, width: '100%', maxWidth: 672, maxHeight: '85vh', display: 'flex', flexDirection: 'column', boxShadow: '0 20px 60px rgba(0,0,0,0.12)' }} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between" style={{ padding: '16px 24px', borderBottom: '1px solid #ece8e0' }}>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-bold text-[#1a1a1a] truncate">{detail.subject}</h3>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-[10px] font-mono text-[#999]">{detail.id}</span>
              <StatusBadge status={detail.status} colorMap={TICKET_STATUS_MAP} />
              <span className="status-pill capitalize" style={{ backgroundColor: (PRIORITY_COLORS[detail.priority] || PRIORITY_COLORS.normal).bg, color: (PRIORITY_COLORS[detail.priority] || PRIORITY_COLORS.normal).text, fontSize: 10 }}>
                {detail.priority}
              </span>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-[#f0ede8] transition-colors cursor-pointer">
            <X size={18} className="text-[#999]" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto" style={{ padding: '16px 24px' }}>
          {/* Description */}
          {detail.description && (
            <div className="mb-4 empire-card flat" style={{ padding: 14 }}>
              <div className="section-label" style={{ marginBottom: 4, fontSize: 10 }}>Description</div>
              <p className="text-sm text-[#555]">{detail.description}</p>
            </div>
          )}

          {/* Meta */}
          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="text-xs">
              <span className="section-label" style={{ fontSize: 10 }}>Assigned To</span>
              <span className="text-[#555] block">{detail.assigned_to || 'Unassigned'}</span>
            </div>
            <div className="text-xs">
              <span className="section-label" style={{ fontSize: 10 }}>Channel</span>
              <span className="text-[#555] capitalize block">{detail.channel || '--'}</span>
            </div>
            <div className="text-xs">
              <span className="section-label" style={{ fontSize: 10 }}>Customer</span>
              <span className="text-[#555] block">{detail.customer_name || '--'}</span>
            </div>
          </div>

          {/* Status Change */}
          <div className="mb-4">
            <label className="section-label" style={{ fontSize: 10, display: 'block' }}>Change Status</label>
            <select
              value={status}
              onChange={e => handleStatusChange(e.target.value)}
              className="px-3 py-2 border border-[#ece8e0] rounded-[14px] text-xs bg-[#faf9f7] outline-none focus:border-[#7c3aed] w-48 transition-colors"
            >
              {STATUS_TABS.filter(s => s !== 'all').map(s => (
                <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>

          {/* Messages */}
          <div className="mb-2">
            <div className="section-label" style={{ fontSize: 10 }}>Messages</div>
            {loadingMessages ? (
              <div className="flex items-center justify-center py-8">
                <div className="w-5 h-5 border-2 border-[#7c3aed] border-t-transparent rounded-full animate-spin" />
              </div>
            ) : messages.length === 0 ? (
              <p className="text-xs text-[#999] text-center py-4">No messages yet</p>
            ) : (
              <div className="space-y-2">
                {messages.map((msg, i) => (
                  <div key={msg.id || i} className={`flex ${msg.is_staff ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[75%] rounded-xl px-3.5 py-2.5 ${
                      msg.is_staff
                        ? 'bg-[#7c3aed] text-white'
                        : 'bg-[#faf9f7] text-[#555] border border-[#ece8e0]'
                    }`}>
                      <div className="text-[10px] font-bold mb-0.5 opacity-70">{msg.sender || (msg.is_staff ? 'Staff' : 'Customer')}</div>
                      <p className="text-sm">{msg.content}</p>
                      <div className="text-[9px] mt-1 opacity-50" suppressHydrationWarning>
                        {msg.created_at ? new Date(msg.created_at).toLocaleString() : ''}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Reply Input */}
        <div className="flex items-center gap-2" style={{ padding: '12px 24px', borderTop: '1px solid #ece8e0' }}>
          <input
            type="text"
            value={reply}
            onChange={e => setReply(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleReply()}
            placeholder="Type a reply..."
            className="flex-1 px-3.5 py-2.5 text-sm border border-[#ece8e0] rounded-[14px] bg-[#faf9f7] outline-none focus:border-[#7c3aed] transition-colors"
          />
          <button
            onClick={handleReply}
            disabled={!reply.trim() || sending}
            className="flex items-center gap-1 px-4 py-2.5 text-xs font-bold text-white bg-[#7c3aed] rounded-xl hover:bg-[#6d28d9] disabled:opacity-50 transition-colors cursor-pointer"
          >
            <Send size={14} /> {sending ? 'Sending...' : 'Reply'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── New Ticket Modal ────────────────────────────────────────────────

function NewTicketModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('normal');
  const [channel, setChannel] = useState('email');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!subject.trim()) { setError('Subject is required'); return; }
    setSaving(true);
    setError('');
    try {
      const res = await fetch(`${API}/tickets/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subject, description, priority, channel }),
      });
      if (!res.ok) throw new Error('Failed to create ticket');
      onCreated();
    } catch {
      setError('Failed to create ticket');
      setSaving(false);
    }
  };

  const inputClass = "w-full px-3.5 py-2.5 text-sm border border-[#ece8e0] rounded-[14px] bg-[#faf9f7] outline-none focus:border-[#7c3aed] transition-colors";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={onClose}>
      <div className="empire-card" style={{ padding: 0, width: '100%', maxWidth: 448, boxShadow: '0 20px 60px rgba(0,0,0,0.12)' }} onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between" style={{ padding: '16px 24px', borderBottom: '1px solid #ece8e0' }}>
          <h3 className="text-sm font-bold text-[#1a1a1a]">New Ticket</h3>
          <button onClick={onClose} className="p-1.5 rounded-xl hover:bg-[#f0ede8] transition-colors cursor-pointer">
            <X size={18} className="text-[#999]" />
          </button>
        </div>
        <div style={{ padding: '16px 24px' }} className="space-y-4">
          {error && (
            <div className="text-xs text-red-600 bg-[#fef2f2] px-3.5 py-2.5 rounded-xl">{error}</div>
          )}
          <div>
            <label className="section-label" style={{ fontSize: 10 }}>Subject</label>
            <input type="text" value={subject} onChange={e => setSubject(e.target.value)} className={inputClass} placeholder="Ticket subject..." />
          </div>
          <div>
            <label className="section-label" style={{ fontSize: 10 }}>Description</label>
            <textarea value={description} onChange={e => setDescription(e.target.value)} rows={3} className={`${inputClass} resize-none`} placeholder="Describe the issue..." />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="section-label" style={{ fontSize: 10 }}>Priority</label>
              <select value={priority} onChange={e => setPriority(e.target.value)} className={inputClass}>
                <option value="urgent">Urgent</option>
                <option value="high">High</option>
                <option value="normal">Normal</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div>
              <label className="section-label" style={{ fontSize: 10 }}>Channel</label>
              <select value={channel} onChange={e => setChannel(e.target.value)} className={inputClass}>
                {CHANNEL_OPTIONS.map(c => (
                  <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
        <div className="flex items-center justify-end gap-2" style={{ padding: '12px 24px', borderTop: '1px solid #ece8e0' }}>
          <button onClick={onClose} className="px-4 py-2 text-xs font-medium text-[#999] hover:text-[#555] transition-colors cursor-pointer">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="px-4 py-2.5 text-xs font-bold text-white bg-[#7c3aed] rounded-xl hover:bg-[#6d28d9] disabled:opacity-50 transition-colors cursor-pointer"
          >
            {saving ? 'Creating...' : 'Create Ticket'}
          </button>
        </div>
      </div>
    </div>
  );
}
