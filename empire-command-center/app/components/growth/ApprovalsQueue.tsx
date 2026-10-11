'use client';
import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle, Copy, ExternalLink, Mail, MessageCircle, Image as ImageIcon, Clock, X, Send } from 'lucide-react';
import { API, API_BASE } from '../../lib/api';
import { Badge, Header, btn, card, ghost, input, muted, useIsMobile } from './shared';

const G = `${API}/growth`;
const KIND: Record<string, { label: string; bg: string; color: string; icon: any }> = {
  email: { label: 'Email', bg: '#dbeafe', color: '#1d4ed8', icon: Mail },
  ig_dm: { label: 'IG DM', bg: '#fce7f3', color: '#be185d', icon: MessageCircle },
  social_post: { label: 'Social post', bg: '#ede9fe', color: '#6d28d9', icon: ImageIcon },
  followup: { label: 'Follow-up', bg: '#fef3c7', color: '#b45309', icon: Clock },
};
const FILTERS = ['pending', 'sent', 'copied', 'dismissed', 'all'];

function mediaSrc(u: string) { return u.startsWith('http') ? u : `${API_BASE}${u}`; }

function Item({ it, onDone }: { it: any; onDone: (msg: string) => void }) {
  const [body, setBody] = useState(it.body || '');
  const [subject, setSubject] = useState(it.subject || '');
  const [to, setTo] = useState(it.to_address || '');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const k = KIND[it.kind] || KIND.followup;
  const isEmail = it.channel === 'email';
  const pending = it.status === 'pending';

  const approve = async () => {
    setBusy(true); setErr('');
    try {
      const r = await fetch(`${G}/approvals/${it.id}/approve`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirm: true, body, subject, to_address: to || undefined }) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || 'Failed');
      if (isEmail) onDone(d.sent ? `Sent to ${to}` : `Not sent: ${d.detail || 'send failed'}`);
      else {
        try { await navigator.clipboard.writeText(d.copy_text || body); } catch { /* clipboard blocked */ }
        if (d.open_url) window.open(d.open_url, '_blank', 'noopener');
        onDone('Copied. Paste it in the app that just opened.');
      }
    } catch (e: any) { setErr(e.message || String(e)); } finally { setBusy(false); }
  };
  const dismiss = async () => {
    setBusy(true);
    await fetch(`${G}/approvals/${it.id}/dismiss`, { method: 'POST' });
    setBusy(false); onDone('Dismissed');
  };

  return (
    <div style={{ ...card, display: 'flex', flexDirection: 'column', gap: 10 }} data-approval-id={it.id}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <Badge text={k.label} bg={k.bg} color={k.color} />
        <span style={{ fontWeight: 700, fontSize: 15, flex: 1, minWidth: 0, overflowWrap: 'anywhere' }}>{it.title || k.label}</span>
        {!pending && <Badge text={it.status} bg={it.status === 'sent' ? '#dcfce7' : '#f5f3ef'} color={it.status === 'sent' ? '#15803d' : '#666'} />}
      </div>
      <div style={{ ...muted, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        <span>From {it.created_by || 'max'}</span><span>·</span><span>{(it.created_at || '').slice(0, 16).replace('T', ' ')}</span>
        {it.source === 'campaign' && <><span>·</span><span>campaign step</span></>}
      </div>
      {isEmail && (
        <div style={{ display: 'grid', gap: 8 }}>
          <label style={muted}>To {it.to_name ? `(${it.to_name})` : ''}
            <input style={input} value={to} disabled={!pending} placeholder="name@company.com" onChange={e => setTo(e.target.value)} /></label>
          <label style={muted}>Subject<input style={input} value={subject} disabled={!pending} onChange={e => setSubject(e.target.value)} /></label>
        </div>
      )}
      {!isEmail && it.to_name && <div style={muted}>To: {it.to_name} {it.to_address}</div>}
      <textarea style={{ ...input, minHeight: 130, fontFamily: 'inherit', lineHeight: 1.45 }} value={body} disabled={!pending}
        onChange={e => setBody(e.target.value)} />
      {it.media_urls?.length > 0 && (
        <div style={{ display: 'flex', gap: 8, overflowX: 'auto' }}>
          {it.media_urls.map((u: string) => (
            <img key={u} src={mediaSrc(u)} alt="" style={{ width: 96, height: 96, objectFit: 'cover', borderRadius: 8, border: '1px solid #e5e2dc', flexShrink: 0 }} />
          ))}
        </div>
      )}
      {err && <div style={{ color: '#dc2626', fontSize: 13 }}>{err}</div>}
      {pending && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {isEmail ? (
            <button disabled={busy || !to} onClick={approve} style={{ ...btn('#16a34a'), opacity: busy || !to ? 0.6 : 1 }}>
              <Send size={15} /> {busy ? 'Sending…' : 'Approve & send email'}
            </button>
          ) : (
            <button disabled={busy} onClick={approve} style={btn('#7c3aed')}>
              <Copy size={15} /> Copy & open {it.channel === 'facebook' ? 'Facebook' : it.channel === 'sms' ? 'Messages' : 'Instagram'} <ExternalLink size={13} />
            </button>
          )}
          <button disabled={busy} onClick={dismiss} style={ghost}><X size={15} /> Dismiss</button>
        </div>
      )}
      {pending && !isEmail && <div style={muted}>Empire never posts or DMs for you. This copies the text and opens the app.</div>}
    </div>
  );
}

export default function ApprovalsQueue() {
  const [status, setStatus] = useState('pending');
  const [data, setData] = useState<any>({ items: [], counts: {} });
  const [toast, setToast] = useState('');
  const mobile = useIsMobile();
  const load = useCallback(() => {
    fetch(`${G}/approvals?status=${status}`).then(r => r.json()).then(setData).catch(() => {});
  }, [status]);
  useEffect(() => { load(); }, [load]);
  const done = (m: string) => { setToast(m); load(); setTimeout(() => setToast(''), 4000); };

  return (
    <div>
      <Header title="Approvals" subtitle="Every draft Max makes lands here: emails, Instagram DMs, social posts and follow-ups. Nothing goes out until you tap. Email sends through the existing Gmail path; Instagram and social are copy-and-open." />
      <div style={{ display: 'flex', gap: 6, overflowX: 'auto', marginBottom: 14, paddingBottom: 2 }}>
        {FILTERS.map(f => (
          <button key={f} onClick={() => setStatus(f)} style={{ ...ghost, padding: '6px 12px', minHeight: 34, whiteSpace: 'nowrap',
            background: status === f ? '#1d4ed8' : 'transparent', color: status === f ? '#fff' : 'inherit' }}>
            {f[0].toUpperCase() + f.slice(1)}{f !== 'all' && data.counts?.[f] ? ` (${data.counts[f]})` : ''}
          </button>
        ))}
      </div>
      {toast && <div style={{ ...card, background: '#dcfce7', color: '#15803d', marginBottom: 12, display: 'flex', gap: 8, alignItems: 'center' }}><CheckCircle size={16} /> {toast}</div>}
      {data.items.length === 0 ? (
        <div style={{ ...card, textAlign: 'center', color: '#888' }}>Nothing {status === 'all' ? '' : status} here.</div>
      ) : (
        <div style={{ display: 'grid', gap: 12, gridTemplateColumns: mobile ? 'minmax(0, 1fr)' : 'repeat(auto-fill, minmax(min(420px, 100%), 1fr))' }}>
          {data.items.map((it: any) => <Item key={`${it.id}-${it.status}`} it={it} onDone={done} />)}
        </div>
      )}
    </div>
  );
}
