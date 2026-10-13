'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  LifeBuoy, Paperclip, Send, Link2, CheckCircle2, Clock,
  CircleDot, Sparkles, RefreshCw, ExternalLink, ListTodo,
} from 'lucide-react';
import {
  HelpTicket, LOG_STATUSES, LogStatus, REQUEST_TYPES, RequestType,
  STATUS_LABEL, TYPE_LABEL, addWorkLog, attachmentUrl, createOrganizerTask,
  fetchInbox, fetchTicket, fetchUnreadCount, patchRequest, replyTicket,
  statusOf, typeOf, whoLabel,
} from '../../lib/familyHelp';

const ACCENT = '#b8960c';
const ACCENT_BG = 'rgba(184,150,12,0.12)';
const ACCENT_BORDER = 'rgba(184,150,12,0.28)';

const STATUS_TONE: Record<LogStatus, { bg: string; color: string }> = {
  new: { bg: 'rgba(184,150,12,0.16)', color: '#e8c547' },
  planned: { bg: 'rgba(37,99,235,0.16)', color: '#60a5fa' },
  in_progress: { bg: 'rgba(124,58,237,0.16)', color: '#c4b5fd' },
  done: { bg: 'rgba(22,163,74,0.16)', color: '#4ade80' },
  declined: { bg: 'rgba(239,68,68,0.14)', color: '#f87171' },
};

const TYPE_TONE: Record<RequestType, { bg: string; color: string }> = {
  adjust: { bg: 'rgba(184,150,12,0.14)', color: ACCENT },
  fix: { bg: 'rgba(239,68,68,0.14)', color: '#f87171' },
  create: { bg: 'rgba(22,163,74,0.14)', color: '#4ade80' },
};

function formatWhen(iso?: string): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 16).replace('T', ' ');
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' });
}

function Badge({ text, bg, color }: { text: string; bg: string; color: string }) {
  return (
    <span style={{
      fontSize: 11, fontWeight: 700, letterSpacing: 0.2, padding: '3px 8px',
      borderRadius: 999, background: bg, color, whiteSpace: 'nowrap',
    }}>{text}</span>
  );
}

export default function EmpireAssistPage() {
  const [tickets, setTickets] = useState<HelpTicket[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [active, setActive] = useState<HelpTicket | null>(null);
  const [filter, setFilter] = useState<'all' | 'amp' | 'maxine'>('all');
  const [statusFilter, setStatusFilter] = useState<'all' | LogStatus>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reply, setReply] = useState('');
  const [logBody, setLogBody] = useState('');
  const [logHref, setLogHref] = useState('');
  const [busy, setBusy] = useState(false);
  const [unread, setUnread] = useState(0);

  const load = useCallback(async (keepId?: string | null) => {
    setLoading(true);
    try {
      const rows = await fetchInbox(filter === 'all' ? undefined : filter);
      setTickets(rows);
      const count = await fetchUnreadCount();
      setUnread(count);
      const want = keepId ?? activeId;
      const next = (want && rows.find((r) => r.id === want)) || rows[0] || null;
      setActiveId(next?.id || null);
      if (next) {
        const detail = await fetchTicket(next.id);
        setActive(detail || next);
      } else {
        setActive(null);
      }
      setError(null);
    } catch (err: any) {
      setError(err?.message || 'Could not load family requests');
    } finally {
      setLoading(false);
    }
  }, [filter, activeId]);

  useEffect(() => { load(null); }, [filter]); // eslint-disable-line react-hooks/exhaustive-deps

  const visible = useMemo(() => {
    return tickets.filter((t) => statusFilter === 'all' || statusOf(t) === statusFilter);
  }, [tickets, statusFilter]);

  const open = async (ticket: HelpTicket) => {
    setActiveId(ticket.id);
    setReply('');
    setLogBody('');
    setLogHref('');
    const detail = await fetchTicket(ticket.id);
    setActive(detail || ticket);
    const rows = await fetchInbox(filter === 'all' ? undefined : filter);
    setTickets(rows);
    setUnread(await fetchUnreadCount());
  };

  const act = async (fn: () => Promise<HelpTicket | null | void>) => {
    setBusy(true);
    setError(null);
    try {
      const ticket = await fn();
      if (ticket) setActive(ticket);
      await load(ticket?.id || activeId);
    } catch (err: any) {
      setError(err?.message || 'Action failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      data-testid="empire-assist-family-requests"
      style={{ display: 'flex', height: '100%', minHeight: 0, background: 'var(--chat-bg, #0b0f14)', color: 'var(--text, #f5f5f0)' }}
    >
      <aside style={{
        width: 360, maxWidth: '42%', borderRight: `1px solid ${ACCENT_BORDER}`,
        display: 'flex', flexDirection: 'column', background: 'var(--card-bg, #11151c)', minWidth: 280,
      }}>
        <div style={{ padding: '18px 18px 12px', borderBottom: `1px solid ${ACCENT_BORDER}` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
            <div style={{ background: ACCENT_BG, borderRadius: 10, padding: 8 }}>
              <LifeBuoy size={18} color={ACCENT} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 15, fontWeight: 700 }}>Empire Assist: Family Requests</div>
              <div style={{ fontSize: 11, color: 'var(--muted, #8b8b80)' }}>Juan / Max-e · Camilo / Maxine</div>
            </div>
            {unread > 0 && (
              <span
                data-testid="family-unread-badge"
                aria-label={`${unread} unread family requests`}
                style={{
                  minWidth: 22, height: 22, borderRadius: 999, background: ACCENT, color: '#1a1403',
                  fontSize: 11, fontWeight: 800, display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  padding: '0 7px',
                }}
              >{unread > 99 ? '99+' : unread}</span>
            )}
          </div>
          <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
            {([
              ['all', 'All'],
              ['amp', 'Juan'],
              ['maxine', 'Camilo'],
            ] as const).map(([id, label]) => (
              <button key={id} type="button" onClick={() => setFilter(id)} style={{
                flex: 1, padding: '7px 8px', borderRadius: 8, cursor: 'pointer', fontSize: 12, fontWeight: 600,
                border: `1px solid ${filter === id ? ACCENT : ACCENT_BORDER}`,
                background: filter === id ? ACCENT_BG : 'transparent',
                color: filter === id ? ACCENT : 'var(--muted, #8b8b80)',
              }}>{label}</button>
            ))}
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}
            style={{
              width: '100%', marginTop: 8, padding: '7px 8px', borderRadius: 8, fontSize: 12,
              background: '#0b0f14', color: 'inherit', border: `1px solid ${ACCENT_BORDER}`,
            }}
          >
            <option value="all">Every status</option>
            {LOG_STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
          </select>
        </div>
        <div style={{ flex: 1, overflow: 'auto', padding: 10 }}>
          {loading && <div style={{ padding: 16, fontSize: 13, color: 'var(--muted, #8b8b80)' }}>Loading requests…</div>}
          {!loading && visible.length === 0 && (
            <div style={{ padding: 18, fontSize: 13, color: 'var(--muted, #8b8b80)', lineHeight: 1.5 }}>
              No family requests yet. When Juan or Camilo tap Pedir ayuda a Max, they land here.
            </div>
          )}
          {visible.map((ticket) => {
            const on = ticket.id === activeId;
            const st = statusOf(ticket);
            const ty = typeOf(ticket);
            return (
              <button
                key={`${ticket.edition}-${ticket.id}`}
                type="button"
                onClick={() => open(ticket)}
                data-ticket-id={ticket.id}
                style={{
                  display: 'block', width: '100%', textAlign: 'left', marginBottom: 8, padding: 12,
                  borderRadius: 12, cursor: 'pointer',
                  border: on ? `1px solid ${ACCENT}` : '1px solid rgba(255,255,255,0.06)',
                  background: on ? ACCENT_BG : 'rgba(255,255,255,0.02)',
                  color: 'inherit',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 4 }}>
                  <span style={{ fontSize: 12, color: ACCENT, fontWeight: 700 }}>{whoLabel(ticket)}</span>
                  <span style={{ fontSize: 11, color: 'var(--muted, #8b8b80)' }}>{formatWhen(ticket.created_at)}</span>
                </div>
                <div style={{ fontSize: 13, fontWeight: 600, lineHeight: 1.35, marginBottom: 8 }}>
                  {(ticket.summary || ticket.message || ticket.transcript || ticket.id).slice(0, 110)}
                </div>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                  <Badge text={TYPE_LABEL[ty]} bg={TYPE_TONE[ty].bg} color={TYPE_TONE[ty].color} />
                  <Badge text={STATUS_LABEL[st]} bg={STATUS_TONE[st].bg} color={STATUS_TONE[st].color} />
                  {(ticket.attachment_count || ticket.attachments?.length) ? (
                    <span style={{ fontSize: 11, color: 'var(--muted, #8b8b80)', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                      <Paperclip size={11} />{ticket.attachment_count || ticket.attachments?.length}
                    </span>
                  ) : null}
                  {ticket.unread && <CircleDot size={11} color={ACCENT} aria-label="Unread" />}
                </div>
              </button>
            );
          })}
        </div>
      </aside>

      <section style={{ flex: 1, minWidth: 0, overflow: 'auto', padding: '22px 28px 40px' }}>
        {!active && !loading && (
          <div style={{ color: 'var(--muted, #8b8b80)', fontSize: 14, maxWidth: 520, lineHeight: 1.6 }}>
            Family requests from Juan (Max-e) and Camilo (Maxine) show here. Type is suggested by Max
            (Adjust / Fix / Create) and you can change it. Status and the work log stay on Studio —
            the family help.db is never written.
          </div>
        )}
        {active && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 860 }}>
            <header>
              <div style={{ fontSize: 12, color: 'var(--muted, #8b8b80)', marginBottom: 6 }}>
                {active.id} · {formatWhen(active.created_at)}
              </div>
              <h2 style={{ margin: 0, fontSize: 22, fontWeight: 700 }}>{whoLabel(active)}</h2>
              <p style={{ margin: '8px 0 0', fontSize: 15, lineHeight: 1.55, whiteSpace: 'pre-wrap' }}>
                {active.message || active.transcript || '—'}
              </p>
              {active.transcript && active.message ? (
                <p style={{ margin: '8px 0 0', fontSize: 13, color: 'var(--muted, #8b8b80)' }}>
                  <strong>Transcript.</strong> {active.transcript}
                </p>
              ) : null}
            </header>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <label style={fieldBox}>
                <span style={fieldLabel}><Sparkles size={12} /> Type · Max suggested {TYPE_LABEL[active.type_suggested || typeOf(active)]}</span>
                <select
                  value={typeOf(active)}
                  disabled={busy}
                  onChange={(e) => act(() => patchRequest(active.edition, active.id, { type: e.target.value as RequestType }))}
                  style={selectStyle}
                >
                  {REQUEST_TYPES.map((t) => <option key={t} value={t}>{TYPE_LABEL[t]}</option>)}
                </select>
              </label>
              <label style={fieldBox}>
                <span style={fieldLabel}><Clock size={12} /> Status</span>
                <select
                  value={statusOf(active)}
                  disabled={busy}
                  onChange={(e) => act(() => patchRequest(active.edition, active.id, { status: e.target.value as LogStatus }))}
                  style={selectStyle}
                >
                  {LOG_STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
                </select>
              </label>
            </div>

            <div style={card}>
              <div style={cardTitle}><Paperclip size={14} color={ACCENT} /> Attachments</div>
              {!(active.attachments || []).length && (
                <div style={{ fontSize: 13, color: 'var(--muted, #8b8b80)' }}>No attachments.</div>
              )}
              {(active.attachments || []).map((att) => (
                att.kind === 'voice' ? (
                  <div key={att.id} style={{ margin: '8px 0' }}>
                    <div style={{ fontSize: 12, marginBottom: 4 }}>{att.filename}</div>
                    <audio controls src={attachmentUrl(active.id, att.id)} style={{ width: '100%' }} />
                  </div>
                ) : (
                  <a
                    key={att.id}
                    href={attachmentUrl(active.id, att.id)}
                    target="_blank"
                    rel="noreferrer"
                    style={{ display: 'flex', alignItems: 'center', gap: 8, color: ACCENT, fontSize: 13, marginBottom: 6 }}
                  >
                    <Paperclip size={13} /> {att.filename}
                  </a>
                )
              ))}
            </div>

            {(active.replies || []).length > 0 && (
              <div style={card}>
                <div style={cardTitle}><Send size={14} color={ACCENT} /> Replies already sent</div>
                {(active.replies || []).map((item) => (
                  <div key={item.id} style={{ padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                    <div style={{ fontSize: 12, color: ACCENT, fontWeight: 700 }}>{item.author} · {formatWhen(item.created_at)}</div>
                    <div style={{ fontSize: 13, marginTop: 4, whiteSpace: 'pre-wrap' }}>{item.body}</div>
                  </div>
                ))}
              </div>
            )}

            <div style={card}>
              <div style={cardTitle}><CheckCircle2 size={14} color={ACCENT} /> What was done</div>
              {(active.log || []).length === 0 && (
                <div style={{ fontSize: 13, color: 'var(--muted, #8b8b80)', marginBottom: 10 }}>
                  Nothing logged yet. Add a note, PR link, or Organizer task.
                </div>
              )}
              {(active.log || []).map((entry) => (
                <div key={entry.id} style={{ padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.04)', fontSize: 13 }}>
                  <div style={{ fontSize: 11, color: 'var(--muted, #8b8b80)', marginBottom: 2 }}>
                    {entry.kind} · {formatWhen(entry.created_at)}
                  </div>
                  <div>{entry.body}</div>
                  {entry.href && (
                    <a href={entry.href} target={entry.href.startsWith('/') ? undefined : '_blank'} rel="noreferrer" style={{ color: ACCENT, display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 4 }}>
                      <ExternalLink size={12} /> {entry.href_label || entry.href}
                    </a>
                  )}
                </div>
              ))}
              <div style={{ display: 'grid', gap: 8, marginTop: 12 }}>
                <textarea
                  value={logBody}
                  onChange={(e) => setLogBody(e.target.value)}
                  placeholder="What you did — and a PR or task link if there is one"
                  rows={3}
                  style={areaStyle}
                />
                <input
                  value={logHref}
                  onChange={(e) => setLogHref(e.target.value)}
                  placeholder="https://github.com/…/pull/123 or /?screen=tasks&id=…"
                  style={inputStyle}
                />
                <button
                  type="button"
                  disabled={busy || !logBody.trim()}
                  onClick={() => act(() => addWorkLog(active.edition, active.id, {
                    body: logBody,
                    href: logHref || undefined,
                    href_label: logHref ? 'Open link' : undefined,
                    kind: logHref ? 'pr' : 'note',
                  }))}
                  style={btn(ACCENT)}
                >
                  <Link2 size={14} /> Add to log
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button
                type="button"
                disabled={busy}
                onClick={() => act(async () => {
                  const result = await createOrganizerTask(active.edition, active.id);
                  return result.ticket;
                })}
                style={btn('#2563eb')}
              >
                <ListTodo size={14} /> Create Organizer task
              </button>
              <button type="button" disabled={busy} onClick={() => load(active.id)} style={ghostBtn}>
                <RefreshCw size={14} /> Refresh
              </button>
            </div>

            <div style={card}>
              <div style={cardTitle}><Send size={14} color={ACCENT} /> Reply to the family chat</div>
              <textarea
                value={reply}
                onChange={(e) => setReply(e.target.value)}
                placeholder="Reply Juan or Camilo will see in Max-e / Maxine"
                rows={4}
                style={areaStyle}
              />
              <button
                type="button"
                disabled={busy || !reply.trim()}
                onClick={() => act(async () => {
                  const ticket = await replyTicket(active.id, reply);
                  setReply('');
                  return ticket;
                })}
                style={{ ...btn(ACCENT), marginTop: 10 }}
              >
                <Send size={14} /> Send reply
              </button>
            </div>

            {error && <div style={{ color: '#f87171', fontSize: 13 }}>{error}</div>}
          </div>
        )}
      </section>
    </div>
  );
}

const card: React.CSSProperties = {
  background: 'rgba(255,255,255,0.025)',
  border: `1px solid ${ACCENT_BORDER}`,
  borderRadius: 12,
  padding: 16,
};
const cardTitle: React.CSSProperties = {
  display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 700, marginBottom: 10, color: '#f5f5f0',
};
const fieldBox: React.CSSProperties = { ...card, display: 'flex', flexDirection: 'column', gap: 8 };
const fieldLabel: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11, fontWeight: 700,
  color: 'var(--muted, #8b8b80)', textTransform: 'uppercase', letterSpacing: 0.4,
};
const selectStyle: React.CSSProperties = {
  width: '100%', padding: '8px 10px', borderRadius: 8, fontSize: 14,
  background: '#0b0f14', color: 'inherit', border: `1px solid ${ACCENT_BORDER}`,
};
const inputStyle: React.CSSProperties = {
  width: '100%', boxSizing: 'border-box', padding: '9px 10px', borderRadius: 8, fontSize: 13,
  background: '#0b0f14', color: 'inherit', border: `1px solid ${ACCENT_BORDER}`,
};
const areaStyle: React.CSSProperties = { ...inputStyle, resize: 'vertical', fontFamily: 'inherit' };

function btn(bg: string): React.CSSProperties {
  return {
    display: 'inline-flex', alignItems: 'center', gap: 6, padding: '9px 13px', borderRadius: 8,
    border: 'none', background: bg, color: '#fff', fontSize: 13, fontWeight: 600, cursor: 'pointer',
  };
}
const ghostBtn: React.CSSProperties = {
  ...btn('transparent'),
  color: 'inherit',
  border: `1px solid ${ACCENT_BORDER}`,
};
