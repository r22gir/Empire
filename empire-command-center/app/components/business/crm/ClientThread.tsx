'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Check, Loader2, MessageSquare, Send, ShieldAlert, X } from 'lucide-react';
import { API } from '../../../lib/api';

type Channel = 'whatsapp' | 'sms';

interface ThreadMessage {
  id: string;
  channel: Channel;
  direction: 'inbound' | 'outbound';
  body: string;
  status: string;
  created_at?: string;
  approved_by?: string | null;
  needs_owner_approval?: boolean;
  live_send?: boolean;
}

interface ClientThreadProps {
  customerId: string;
  customerName?: string;
}

const CHANNEL_LABEL: Record<Channel, string> = {
  whatsapp: 'WhatsApp',
  sms: 'SMS',
};

export default function ClientThread({ customerId, customerName }: ClientThreadProps) {
  const [messages, setMessages] = useState<ThreadMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [channel, setChannel] = useState<Channel>('sms');
  const [busyId, setBusyId] = useState<string | null>(null);
  const [composing, setComposing] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await fetch(`${API}/crm/customers/${customerId}/thread`, { cache: 'no-store' });
      if (!res.ok) throw new Error(`Failed to load thread (${res.status})`);
      const data = await res.json();
      setMessages(data.messages || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load thread');
    } finally {
      setLoading(false);
    }
  }, [customerId]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages.length]);

  const composeDraft = async () => {
    const body = draft.trim();
    if (!body) return;
    setComposing(true);
    setError(null);
    try {
      const res = await fetch(`${API}/crm/customers/${customerId}/thread/draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ body, channel }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Draft failed (${res.status})`);
      setDraft('');
      await load();
    } catch (err: any) {
      setError(err.message || 'Could not save draft');
    } finally {
      setComposing(false);
    }
  };

  const approve = async (messageId: string) => {
    setBusyId(messageId);
    setError(null);
    try {
      const res = await fetch(`${API}/crm/customers/${customerId}/thread/messages/${messageId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ owner_id: 'owner' }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Approve failed (${res.status})`);
      await load();
    } catch (err: any) {
      setError(err.message || 'Approve failed');
    } finally {
      setBusyId(null);
    }
  };

  const reject = async (messageId: string) => {
    setBusyId(messageId);
    setError(null);
    try {
      const res = await fetch(`${API}/crm/customers/${customerId}/thread/messages/${messageId}/reject`, {
        method: 'POST',
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Reject failed (${res.status})`);
      await load();
    } catch (err: any) {
      setError(err.message || 'Reject failed');
    } finally {
      setBusyId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 size={18} className="animate-spin text-[#b8960c]" />
      </div>
    );
  }

  return (
    <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #ece8e0', overflow: 'hidden' }}>
      <div style={{ padding: '14px 16px', borderBottom: '1px solid #ece8e0', display: 'flex', alignItems: 'center', gap: 8 }}>
        <MessageSquare size={16} style={{ color: '#b8960c' }} />
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, color: '#1a1a1a' }}>
            WhatsApp / SMS — {customerName || 'Client'}
          </div>
          <div style={{ fontSize: 11, color: '#888' }}>One thread. Incoming shown. Outgoing stays draft until you approve.</div>
        </div>
      </div>

      <div style={{ margin: 12, padding: '10px 12px', borderRadius: 10, background: '#fdf8eb', border: '1px solid #fde68a', display: 'flex', gap: 8, alignItems: 'flex-start' }}>
        <ShieldAlert size={14} style={{ color: '#b8960c', marginTop: 2 }} />
        <div style={{ fontSize: 12, color: '#7a5b00', lineHeight: 1.45 }}>
          No automatic replies. Each outbound message is a <strong>draft</strong>. Approve that message to sandbox-send it. Live WhatsApp/SMS is not sent from this screen.
        </div>
      </div>

      {error && (
        <div style={{ margin: '0 12px 12px', padding: '8px 10px', borderRadius: 8, background: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', fontSize: 12 }}>
          {error}
        </div>
      )}

      <div style={{ maxHeight: 420, overflowY: 'auto', padding: '8px 16px 16px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: '#aaa', fontSize: 13, padding: '28px 0' }}>
            No messages yet. Incoming WhatsApp/SMS will appear here.
          </div>
        )}
        {messages.map((m) => {
          const inbound = m.direction === 'inbound';
          const draftMsg = m.status === 'draft';
          return (
            <div key={m.id} style={{ display: 'flex', justifyContent: inbound ? 'flex-start' : 'flex-end' }}>
              <div style={{
                maxWidth: '78%',
                padding: '10px 12px',
                borderRadius: 12,
                background: inbound ? '#f5f3ef' : draftMsg ? '#fffbeb' : '#f0fdf4',
                border: `1px solid ${inbound ? '#ece8e0' : draftMsg ? '#fde68a' : '#bbf7d0'}`,
              }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: '#888', textTransform: 'uppercase', marginBottom: 4 }}>
                  {inbound ? 'Incoming' : 'Outgoing'} · {CHANNEL_LABEL[m.channel] || m.channel} · {m.status}
                </div>
                <div style={{ fontSize: 13, color: '#1a1a1a', whiteSpace: 'pre-wrap', lineHeight: 1.45 }}>{m.body}</div>
                {m.created_at && (
                  <div style={{ fontSize: 10, color: '#aaa', marginTop: 6 }}>
                    {new Date(m.created_at).toLocaleString()}
                    {m.approved_by ? ` · approved by ${m.approved_by}` : ''}
                  </div>
                )}
                {draftMsg && (
                  <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                    <button
                      onClick={() => approve(m.id)}
                      disabled={busyId === m.id}
                      className="flex items-center gap-1 cursor-pointer disabled:opacity-50"
                      style={{ minHeight: 36, padding: '0 12px', borderRadius: 8, background: '#b8960c', color: '#fff', border: 'none', fontSize: 12, fontWeight: 700 }}
                    >
                      {busyId === m.id ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />}
                      Approve to send
                    </button>
                    <button
                      onClick={() => reject(m.id)}
                      disabled={busyId === m.id}
                      className="flex items-center gap-1 cursor-pointer disabled:opacity-50"
                      style={{ minHeight: 36, padding: '0 12px', borderRadius: 8, background: '#fff', color: '#777', border: '1px solid #ece8e0', fontSize: 12, fontWeight: 700 }}
                    >
                      <X size={12} /> Reject
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      <div style={{ padding: 12, borderTop: '1px solid #ece8e0', background: '#faf9f7' }}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          {(['sms', 'whatsapp'] as Channel[]).map((ch) => (
            <button
              key={ch}
              onClick={() => setChannel(ch)}
              className="cursor-pointer"
              style={{
                minHeight: 32,
                padding: '0 12px',
                borderRadius: 999,
                border: '1px solid #ece8e0',
                background: channel === ch ? '#b8960c' : '#fff',
                color: channel === ch ? '#fff' : '#666',
                fontSize: 11,
                fontWeight: 700,
              }}
            >
              {CHANNEL_LABEL[ch]}
            </button>
          ))}
        </div>
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={3}
          placeholder="Write a reply. It will be saved as a draft — not sent."
          className="w-full px-3 py-2 text-sm rounded-xl border border-[#ece8e0] bg-white focus:border-[#b8960c] outline-none resize-y"
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
          <span style={{ fontSize: 11, color: '#999' }}>Saves as draft. Owner must approve this message before send.</span>
          <button
            onClick={composeDraft}
            disabled={composing || !draft.trim()}
            className="flex items-center gap-1 cursor-pointer disabled:opacity-50"
            style={{ minHeight: 40, padding: '0 16px', borderRadius: 10, background: '#1a1a1a', color: '#fff', border: 'none', fontSize: 13, fontWeight: 700 }}
          >
            {composing ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
            Save draft
          </button>
        </div>
      </div>
    </div>
  );
}
