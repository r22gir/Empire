'use client';
import { useState, useEffect } from 'react';
import { type Client, MOCK_JOBS } from '@/lib/deskData';
import { Mail, Phone, MapPin, Briefcase, DollarSign, Calendar, FileText, Eye, Check, X, Pencil, ExternalLink } from 'lucide-react';
import { StatusBadge } from '../shared';
import { API_URL } from '@/lib/api';

const STATUS_COLORS: Record<string, string> = {
  active: '#22c55e', prospect: '#8b5cf6', inactive: '#78716c',
};

const fmt = (n: number) => '$' + n.toLocaleString();

interface Quote {
  id: string;
  quote_number: string;
  customer_name: string;
  project_name?: string;
  total: number;
  status: string;
  created_at: string;
}

interface ClientDetailProps {
  client: Client;
  onClientUpdated?: (updated: Client) => void;
}

export default function ClientDetail({ client, onClientUpdated }: ClientDetailProps) {
  const clientJobs = MOCK_JOBS.filter(j => j.client === client.name);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', phone: '', address: '' });
  const [showInvoices, setShowInvoices] = useState(false);
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [loadingQuotes, setLoadingQuotes] = useState(false);

  // Reset state when client changes
  useEffect(() => {
    setEditing(false);
    setShowInvoices(false);
    setQuotes([]);
  }, [client.id]);

  const startEdit = () => {
    setForm({ name: client.name, email: client.email, phone: client.phone, address: client.address });
    setEditing(true);
  };

  const saveEdit = () => {
    if (!form.name.trim()) return;
    const updated = { ...client, ...form, name: form.name.trim() };
    onClientUpdated?.(updated);
    setEditing(false);
  };

  const loadInvoices = async () => {
    if (showInvoices) { setShowInvoices(false); return; }
    setLoadingQuotes(true);
    setShowInvoices(true);
    try {
      const res = await fetch(`${API_URL}/quotes/`);
      if (res.ok) {
        const data = await res.json();
        const allQuotes: Quote[] = data.quotes || data || [];
        const clientQuotes = allQuotes.filter((q: Quote) =>
          q.customer_name?.toLowerCase().includes(client.name.toLowerCase())
        );
        setQuotes(clientQuotes);
      }
    } catch { /* */ }
    setLoadingQuotes(false);
  };

  const viewPdf = async (id: string) => {
    try {
      const res = await fetch(`${API_URL}/quotes/${id}/pdf`, { method: 'POST' });
      if (!res.ok) return;
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    } catch { /* */ }
  };

  return (
    <div className="space-y-5">
      {/* Avatar + status */}
      <div className="flex items-center gap-4">
        <div className="w-14 h-14 rounded-full flex items-center justify-center text-xl font-bold shrink-0"
          style={{ background: 'rgba(6,182,212,0.15)', color: '#06B6D4' }}>
          {client.name.charAt(0)}
        </div>
        <div>
          <p className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>{client.name}</p>
          <StatusBadge label={client.status} color={STATUS_COLORS[client.status]} />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { value: client.totalJobs, label: 'Jobs', color: 'var(--gold)' },
          { value: fmt(client.totalSpent), label: 'Total Spent', color: '#22c55e' },
          { value: client.lastContact, label: 'Last Contact', color: 'var(--text-secondary)' },
        ].map(stat => (
          <div key={stat.label} className="rounded-lg p-2.5 text-center" style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
            <p className="text-sm font-bold" style={{ color: stat.color }}>{stat.value}</p>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Contact info — view or edit */}
      {editing ? (
        <div className="space-y-2 p-3 rounded-lg" style={{ background: 'var(--raised)', border: '1px solid var(--gold-border)' }}>
          <p className="text-[10px] uppercase tracking-wider font-semibold" style={{ color: 'var(--gold)' }}>Edit Profile</p>
          {(['name', 'email', 'phone', 'address'] as const).map(field => (
            <div key={field}>
              <label className="text-[10px] capitalize" style={{ color: 'var(--text-muted)' }}>{field}</label>
              <input
                value={form[field]}
                onChange={e => setForm({ ...form, [field]: e.target.value })}
                className="w-full rounded px-2 py-1 text-xs outline-none"
                style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
                onFocus={e => (e.currentTarget.style.borderColor = 'var(--gold)')}
                onBlur={e => (e.currentTarget.style.borderColor = 'var(--border)')}
              />
            </div>
          ))}
          <div className="flex gap-2 pt-1">
            <button onClick={saveEdit} className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[10px] font-semibold"
              style={{ background: 'var(--gold)', color: '#0a0a0a' }}>
              <Check className="w-3 h-3" /> Save
            </button>
            <button onClick={() => setEditing(false)} className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[10px]"
              style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}>
              <X className="w-3 h-3" /> Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <Mail className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{client.email}</span>
          </div>
          <div className="flex items-center gap-3">
            <Phone className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{client.phone}</span>
          </div>
          <div className="flex items-center gap-3">
            <MapPin className="w-3.5 h-3.5 shrink-0" style={{ color: 'var(--text-muted)' }} />
            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>{client.address}</span>
          </div>
        </div>
      )}

      {/* Past jobs */}
      {clientJobs.length > 0 && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <Briefcase className="w-3 h-3" style={{ color: 'var(--gold)' }} />
            <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Jobs</span>
          </div>
          <div className="space-y-1.5">
            {clientJobs.map(job => (
              <div key={job.id} className="flex items-center justify-between rounded-lg px-3 py-2"
                style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
                <div>
                  <p className="text-xs" style={{ color: 'var(--text-primary)' }}>{job.name}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{job.treatmentType}</span>
                    <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>{job.dueDate}</span>
                  </div>
                </div>
                <StatusBadge label={job.status} color={
                  job.status === 'Complete' ? '#22c55e' : job.status === 'New' ? 'var(--purple)' : 'var(--gold)'
                } />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Invoices / Quotes section */}
      {showInvoices && (
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <FileText className="w-3 h-3" style={{ color: 'var(--gold)' }} />
            <span className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Quotes & Invoices</span>
          </div>
          {loadingQuotes ? (
            <p className="text-xs text-center py-3" style={{ color: 'var(--text-muted)' }}>Loading...</p>
          ) : quotes.length === 0 ? (
            <p className="text-xs text-center py-3" style={{ color: 'var(--text-muted)' }}>No quotes found for {client.name}</p>
          ) : (
            <div className="space-y-1.5 max-h-40 overflow-y-auto">
              {quotes.map(q => (
                <div key={q.id} className="flex items-center justify-between rounded-lg px-3 py-2 group"
                  style={{ background: 'var(--raised)', border: '1px solid var(--border)' }}>
                  <div className="min-w-0">
                    <p className="text-xs font-mono truncate" style={{ color: 'var(--text-primary)' }}>{q.quote_number}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{q.project_name || 'Quote'}</span>
                      <span className="text-[10px] font-mono" style={{ color: 'var(--text-muted)' }}>{q.created_at?.slice(0, 10)}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs font-mono font-semibold" style={{ color: 'var(--gold)' }}>${(q.total || 0).toFixed(2)}</span>
                    <button onClick={() => viewPdf(q.id)} className="p-1 rounded transition opacity-0 group-hover:opacity-100"
                      style={{ color: 'var(--text-muted)' }} title="View PDF">
                      <Eye className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="grid grid-cols-2 gap-2 pt-2">
        <button
          onClick={() => window.open(`mailto:${client.email}`, '_blank')}
          className="text-xs font-medium py-2 px-3 rounded-lg transition"
          style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold-border)'; e.currentTarget.style.color = 'var(--gold)'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
        >
          Send Email
        </button>
        <button
          onClick={() => window.open(`/workroom?client=${encodeURIComponent(client.name)}`, '_blank')}
          className="text-xs font-medium py-2 px-3 rounded-lg transition"
          style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold-border)'; e.currentTarget.style.color = 'var(--gold)'; }}
          onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
        >
          Create Job
        </button>
        <button
          onClick={loadInvoices}
          className="text-xs font-medium py-2 px-3 rounded-lg transition"
          style={{
            background: showInvoices ? 'var(--gold-pale)' : 'var(--raised)',
            border: `1px solid ${showInvoices ? 'var(--gold-border)' : 'var(--border)'}`,
            color: showInvoices ? 'var(--gold)' : 'var(--text-secondary)',
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold-border)'; e.currentTarget.style.color = 'var(--gold)'; }}
          onMouseLeave={e => { if (!showInvoices) { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)'; } }}
        >
          View Invoices
        </button>
        <button
          onClick={startEdit}
          className="text-xs font-medium py-2 px-3 rounded-lg transition"
          style={{
            background: editing ? 'var(--gold-pale)' : 'var(--raised)',
            border: `1px solid ${editing ? 'var(--gold-border)' : 'var(--border)'}`,
            color: editing ? 'var(--gold)' : 'var(--text-secondary)',
          }}
          onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold-border)'; e.currentTarget.style.color = 'var(--gold)'; }}
          onMouseLeave={e => { if (!editing) { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)'; } }}
        >
          Edit Profile
        </button>
      </div>
    </div>
  );
}
