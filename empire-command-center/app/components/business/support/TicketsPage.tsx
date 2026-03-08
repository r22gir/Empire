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

const PRIORITY_COLORS: Record<string, string> = {
  urgent: 'text-red-600 bg-red-50',
  high: 'text-orange-600 bg-orange-50',
  normal: 'text-blue-600 bg-blue-50',
  low: 'text-gray-500 bg-gray-100',
};

const TICKET_STATUS_MAP: Record<string, { bg: string; text: string }> = {
  open: { bg: 'bg-blue-50', text: 'text-blue-700' },
  in_progress: { bg: 'bg-purple-50', text: 'text-purple-700' },
  waiting: { bg: 'bg-amber-50', text: 'text-amber-700' },
  resolved: { bg: 'bg-green-50', text: 'text-green-700' },
  closed: { bg: 'bg-gray-100', text: 'text-gray-500' },
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

  const fetchTickets = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter !== 'all') params.set('status', statusFilter);
      if (priorityFilter !== 'all') params.set('priority', priorityFilter);
      params.set('limit', '100');
      const qs = params.toString();
      const res = await fetch(`${API}/tickets/${qs ? '?' + qs : ''}`);
      if (!res.ok) throw new Error('Failed to fetch');
      const data = await res.json();
      setTickets(data.tickets || data || []);
    } catch {
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
        <span className="font-mono text-xs text-gray-500">{(row.id || '').slice(0, 8)}...</span>
      ),
    },
    { key: 'subject', label: 'Subject', sortable: true },
    { key: 'customer_name', label: 'Customer', sortable: true },
    {
      key: 'priority', label: 'Priority', sortable: true,
      render: (row: Ticket) => {
        const cls = PRIORITY_COLORS[row.priority] || PRIORITY_COLORS.normal;
        return (
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize ${cls}`}>
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
        <span className="text-xs text-gray-500" suppressHydrationWarning>
          {row.created_at ? new Date(row.created_at).toLocaleDateString() : '--'}
        </span>
      ),
    },
    {
      key: 'updated_at', label: 'Updated', sortable: true,
      render: (row: Ticket) => (
        <span className="text-xs text-gray-500" suppressHydrationWarning>
          {row.updated_at ? new Date(row.updated_at).toLocaleDateString() : '--'}
        </span>
      ),
    },
  ];

  return (
    <div className="max-w-6xl mx-auto px-8 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-purple-50 flex items-center justify-center">
            <Headphones size={20} className="text-[#7c3aed]" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[#1a1a1a]">Support Tickets</h1>
            <p className="text-xs text-gray-400">Manage customer support requests</p>
          </div>
        </div>
        <button
          onClick={() => setShowNewModal(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-[#7c3aed] rounded-lg hover:bg-[#6d28d9] transition-colors"
        >
          <Plus size={16} /> New Ticket
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <KPICard icon={<Inbox size={18} />} label="Open Tickets" value={String(kpis.open)} color="#3b82f6" />
        <KPICard icon={<Clock size={18} />} label="In Progress" value={String(kpis.inProgress)} color="#7c3aed" />
        <KPICard icon={<CheckCircle2 size={18} />} label="Resolved Today" value={String(kpis.resolvedToday)} color="#16a34a" />
        <KPICard icon={<AlertTriangle size={18} />} label="Avg Response Time" value="--" color="#b8960c" />
      </div>

      {/* Status Tabs */}
      <div className="flex items-center gap-1 mb-4 border-b border-[#ece8e1]">
        {STATUS_TABS.map(tab => (
          <button
            key={tab}
            onClick={() => setStatusFilter(tab)}
            className={`px-4 py-2 text-xs font-medium capitalize transition-colors border-b-2 ${
              statusFilter === tab
                ? 'text-[#7c3aed] border-[#7c3aed]'
                : 'text-gray-400 border-transparent hover:text-gray-600'
            }`}
          >
            {tab.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      {/* Priority Filter + Search */}
      <div className="flex items-center gap-3 mb-4">
        <select
          value={priorityFilter}
          onChange={e => setPriorityFilter(e.target.value)}
          className="px-3 py-2 border border-[#ece8e1] rounded-lg text-xs bg-white outline-none focus:border-[#b8960c]"
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
        emptyMessage="No tickets found."
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
    // Fetch ticket detail
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
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#ece8e1]">
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-bold text-[#1a1a1a] truncate">{detail.subject}</h3>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-[10px] font-mono text-gray-400">{detail.id}</span>
              <StatusBadge status={detail.status} colorMap={TICKET_STATUS_MAP} />
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium capitalize ${PRIORITY_COLORS[detail.priority] || PRIORITY_COLORS.normal}`}>
                {detail.priority}
              </span>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 transition-colors">
            <X size={18} className="text-gray-400" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {/* Description */}
          {detail.description && (
            <div className="mb-4 p-3 rounded-lg bg-[#faf9f7] border border-[#ece8e1]">
              <div className="text-[10px] font-bold text-gray-400 uppercase mb-1">Description</div>
              <p className="text-sm text-gray-700">{detail.description}</p>
            </div>
          )}

          {/* Meta */}
          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="text-xs">
              <span className="text-gray-400 block text-[10px] uppercase font-bold">Assigned To</span>
              <span className="text-gray-700">{detail.assigned_to || 'Unassigned'}</span>
            </div>
            <div className="text-xs">
              <span className="text-gray-400 block text-[10px] uppercase font-bold">Channel</span>
              <span className="text-gray-700 capitalize">{detail.channel || '--'}</span>
            </div>
            <div className="text-xs">
              <span className="text-gray-400 block text-[10px] uppercase font-bold">Customer</span>
              <span className="text-gray-700">{detail.customer_name || '--'}</span>
            </div>
          </div>

          {/* Status Change */}
          <div className="mb-4">
            <label className="text-[10px] font-bold text-gray-400 uppercase block mb-1">Change Status</label>
            <select
              value={status}
              onChange={e => handleStatusChange(e.target.value)}
              className="px-3 py-2 border border-[#ece8e1] rounded-lg text-xs bg-white outline-none focus:border-[#7c3aed] w-48"
            >
              {STATUS_TABS.filter(s => s !== 'all').map(s => (
                <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>

          {/* Messages */}
          <div className="mb-2">
            <div className="text-[10px] font-bold text-gray-400 uppercase mb-2">Messages</div>
            {loadingMessages ? (
              <div className="flex items-center justify-center py-8">
                <div className="w-5 h-5 border-2 border-[#7c3aed] border-t-transparent rounded-full animate-spin" />
              </div>
            ) : messages.length === 0 ? (
              <p className="text-xs text-gray-400 text-center py-4">No messages yet</p>
            ) : (
              <div className="space-y-2">
                {messages.map((msg, i) => (
                  <div key={msg.id || i} className={`flex ${msg.is_staff ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[75%] rounded-lg px-3 py-2 ${
                      msg.is_staff
                        ? 'bg-[#7c3aed] text-white'
                        : 'bg-[#f5f3ef] text-gray-700 border border-[#ece8e1]'
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
        <div className="px-6 py-3 border-t border-[#ece8e1] flex items-center gap-2">
          <input
            type="text"
            value={reply}
            onChange={e => setReply(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleReply()}
            placeholder="Type a reply..."
            className="flex-1 px-3 py-2 text-sm border border-[#ece8e1] rounded-lg bg-white outline-none focus:border-[#7c3aed]"
          />
          <button
            onClick={handleReply}
            disabled={!reply.trim() || sending}
            className="flex items-center gap-1 px-4 py-2 text-sm font-medium text-white bg-[#7c3aed] rounded-lg hover:bg-[#6d28d9] disabled:opacity-50 transition-colors"
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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#ece8e1]">
          <h3 className="text-sm font-bold text-[#1a1a1a]">New Ticket</h3>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 transition-colors">
            <X size={18} className="text-gray-400" />
          </button>
        </div>
        <div className="px-6 py-4 space-y-4">
          {error && (
            <div className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</div>
          )}
          <div>
            <label className="text-[10px] font-bold text-gray-400 uppercase block mb-1">Subject</label>
            <input
              type="text"
              value={subject}
              onChange={e => setSubject(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-[#ece8e1] rounded-lg bg-white outline-none focus:border-[#7c3aed]"
              placeholder="Ticket subject..."
            />
          </div>
          <div>
            <label className="text-[10px] font-bold text-gray-400 uppercase block mb-1">Description</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 text-sm border border-[#ece8e1] rounded-lg bg-white outline-none focus:border-[#7c3aed] resize-none"
              placeholder="Describe the issue..."
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] font-bold text-gray-400 uppercase block mb-1">Priority</label>
              <select
                value={priority}
                onChange={e => setPriority(e.target.value)}
                className="w-full px-3 py-2 border border-[#ece8e1] rounded-lg text-xs bg-white outline-none focus:border-[#7c3aed]"
              >
                <option value="urgent">Urgent</option>
                <option value="high">High</option>
                <option value="normal">Normal</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div>
              <label className="text-[10px] font-bold text-gray-400 uppercase block mb-1">Channel</label>
              <select
                value={channel}
                onChange={e => setChannel(e.target.value)}
                className="w-full px-3 py-2 border border-[#ece8e1] rounded-lg text-xs bg-white outline-none focus:border-[#7c3aed]"
              >
                {CHANNEL_OPTIONS.map(c => (
                  <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 px-6 py-4 border-t border-[#ece8e1]">
          <button onClick={onClose} className="px-4 py-2 text-xs font-medium text-gray-500 hover:text-gray-700 transition-colors">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="px-4 py-2 text-xs font-medium text-white bg-[#7c3aed] rounded-lg hover:bg-[#6d28d9] disabled:opacity-50 transition-colors"
          >
            {saving ? 'Creating...' : 'Create Ticket'}
          </button>
        </div>
      </div>
    </div>
  );
}
