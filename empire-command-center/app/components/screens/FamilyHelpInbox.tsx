'use client';

import { useCallback, useEffect, useState } from 'react';
import { LifeBuoy } from 'lucide-react';
import { useTranslation } from '../../lib/i18n';
import {
  HelpTicket,
  attachmentUrl,
  familyHelpLabels,
  fetchInbox,
  revealInboxAttachments,
  retryTranscript,
} from '../../lib/familyHelp';
import { API } from '../../lib/api';

const EDITION_LABEL: Record<string, string> = {
  amp: 'Max-e · Juan',
  maxine: 'Maxine · Camilo',
};

const CONFIRM_HEADER = { 'X-Family-Help-Confirm': 'si-enviar' };

export default function FamilyHelpInbox() {
  const { locale } = useTranslation();
  const t = familyHelpLabels(locale || 'es');
  const [tickets, setTickets] = useState<HelpTicket[]>([]);
  const [active, setActive] = useState<HelpTicket | null>(null);
  const [reply, setReply] = useState('');
  const [draft, setDraft] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>('all');

  const load = useCallback(async () => {
    const rows = await fetchInbox(filter === 'all' ? undefined : filter);
    setTickets(rows);
    setActive((cur) => (cur ? rows.find((row) => row.id === cur.id) || cur : rows[0] || null));
  }, [filter]);

  useEffect(() => { load(); }, [load]);

  const post = async (path: string, body: any, confirm = false) => {
    const res = await fetch(`${API}/family-help/inbox/${active?.id}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(confirm ? CONFIRM_HEADER : {}),
      },
      credentials: 'include',
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setError(data.detail || `HTTP ${res.status}`);
      return;
    }
    setError(null);
    if (data.draft) setDraft(data.draft);
    if (data.ticket) setActive(data.ticket);
    await load();
  };

  const openAttachments = async () => {
    if (!active) return;
    const ticket = await revealInboxAttachments(active.id);
    if (ticket) setActive(ticket);
    await load();
  };

  const retry = async () => {
    if (!active) return;
    const ticket = await retryTranscript(active.id, true, locale);
    if (ticket) setActive(ticket);
    await load();
  };

  return (
    <div style={{ display: 'flex', height: '100%', minHeight: 0, background: 'var(--chat-bg)' }}>
      <aside style={{ width: 320, borderRight: '1px solid var(--border)', overflow: 'auto', padding: 12 }}>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 16 }}>
          <LifeBuoy size={16} /> {t.inbox}
        </h2>
        <select value={filter} onChange={(e) => setFilter(e.target.value)} style={{ width: '100%', marginBottom: 10 }}>
          <option value="all">Max-e + Maxine</option>
          <option value="amp">Max-e · Juan</option>
          <option value="maxine">Maxine · Camilo</option>
        </select>
        {tickets.length === 0 && <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>{t.empty}</p>}
        {tickets.map((ticket) => (
          <button
            key={ticket.id}
            type="button"
            onClick={() => setActive(ticket)}
            style={{
              display: 'block',
              width: '100%',
              textAlign: 'left',
              marginBottom: 8,
              padding: 10,
              borderRadius: 8,
              border: ticket.id === active?.id ? '1px solid #d4a017' : '1px solid var(--border)',
              background: 'var(--card-bg)',
              color: 'inherit',
              cursor: 'pointer',
            }}
          >
            <div style={{ fontSize: 12, opacity: 0.7 }}>{EDITION_LABEL[ticket.edition] || ticket.edition} · {ticket.status}</div>
            <div style={{ fontWeight: 600 }}>{ticket.sender}</div>
            <div style={{ fontSize: 13 }}>{(ticket.message || ticket.transcript || '').slice(0, 90)}</div>
            {(ticket.attachment_count || ticket.attachments?.length) ? (
              <div style={{ fontSize: 11, opacity: 0.75, marginTop: 4 }}>
                {t.files}: {ticket.attachment_count || ticket.attachments?.length}
              </div>
            ) : null}
          </button>
        ))}
      </aside>
      <section style={{ flex: 1, overflow: 'auto', padding: 20 }}>
        {!active && <p>{t.empty}</p>}
        {active && (
          <>
            <div style={{ fontSize: 12, opacity: 0.7 }}>{active.id} · {EDITION_LABEL[active.edition]} · {active.status} · {active.created_at}</div>
            <h3 style={{ marginTop: 6 }}>{active.sender}</h3>
            <p>{active.message || '—'}</p>
            {active.transcript ? (
              <p><strong>{t.transcript}:</strong> {active.transcript}</p>
            ) : null}
            {active.transcript_pending ? (
              <div style={{ margin: '10px 0' }}>
                <strong>{t.transcriptPending}</strong>
                <button type="button" onClick={retry} style={{ marginLeft: 8 }}>{t.retryTranscript}</button>
              </div>
            ) : null}
            <p style={{ fontSize: 13, color: '#d4a017' }}>{t.attachmentWarning}</p>
            {active.attachments_hidden ? (
              <div style={{ margin: '10px 0' }}>
                <p>{t.hiddenAttachments} ({active.attachment_count || 0})</p>
                <button type="button" onClick={openAttachments}>{t.openAttachments}</button>
              </div>
            ) : (
              (active.attachments || []).map((att) => (
                att.kind === 'voice'
                  ? <div key={att.id} style={{ margin: '10px 0' }}>
                      <div style={{ fontSize: 12 }}>{t.play}</div>
                      <audio controls src={attachmentUrl(active.id, att.id, true)} style={{ width: '100%' }} />
                    </div>
                  : <a key={att.id} href={attachmentUrl(active.id, att.id, true)} target="_blank" rel="noreferrer" style={{ display: 'block', marginBottom: 6 }}>
                      {att.filename}{att.size ? ` (${Math.round(att.size / 1024)} KB)` : ''}
                    </a>
              ))
            )}
            {(active.context || []).length > 0 && (
              <details style={{ margin: '12px 0' }}>
                <summary>{t.context}</summary>
                {(active.context || []).map((turn, idx) => (
                  <p key={idx} style={{ fontSize: 13 }}><strong>{turn.role}:</strong> {turn.content}</p>
                ))}
              </details>
            )}
            {(active.replies || []).map((item) => (
              <div key={item.id} style={{ padding: 10, borderRadius: 8, background: 'rgba(212,160,23,0.12)', marginBottom: 8 }}>
                <strong>{item.author}</strong>
                <div>{item.body}</div>
                {item.usage_tokens ? (
                  <div style={{ fontSize: 12, opacity: 0.7 }}>{t.replyUsage}: ~{item.usage_tokens}</div>
                ) : null}
              </div>
            ))}
            {active.usage ? (
              <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                {t.replyUsage}: ~{active.usage.reply_tokens || 0} ({EDITION_LABEL[active.usage.charged_to || active.edition] || active.edition}). {t.usageNote}
              </p>
            ) : (
              <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>{t.usageNote}</p>
            )}
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>{t.needYes}</p>
            <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>{t.noApply}</p>
            {draft && (
              <textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={5} style={{ width: '100%', marginBottom: 8 }} />
            )}
            <textarea
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              placeholder={t.reply}
              rows={4}
              style={{ width: '100%' }}
            />
            {error && <div style={{ color: '#f87171' }}>{error}</div>}
            <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
              <button type="button" onClick={() => post('/draft', {})}>{t.draft}</button>
              <button
                type="button"
                data-family-help-confirm="si-enviar"
                onClick={() => post('/reply', { body: draft || reply, author: 'Max' }, true)}
                disabled={!(draft || reply).trim()}
              >
                {t.confirm}
              </button>
              <button type="button" onClick={() => post('/close', { status: 'closed' })}>{t.closedStatus}</button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
