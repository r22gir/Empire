'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  CheckCheck,
  Copy,
  Download,
  FileText,
  FolderInput,
  MessageCircle,
  Printer,
  RefreshCw,
  Search,
  X,
  XCircle,
} from 'lucide-react';
import { API } from '../../lib/api';

const PIN_KEY = 'empire_whatsapp_founder_pin';

interface Conversation {
  wa_id: string;
  display_label: string;
  total_messages: number;
  last_timestamp: string;
  last_message: string;
  last_direction: string;
  last_status: string;
  last_error_code?: string;
  last_error?: string | null;
  active_job?: { job_slug?: string; client_name?: string } | null;
}

interface Attachment {
  id: number;
  filename: string;
  mime_type?: string;
  size_bytes?: number;
  media_type: string;
  doc_id?: string;
  job_slug?: string;
  filed_path?: string;
  filing_status?: string;
  has_file?: boolean;
}

interface ChatMessage {
  id: number;
  wa_id: string;
  display_label: string;
  direction: string;
  timestamp: string;
  wa_message_id?: string;
  message_type: string;
  body?: string;
  caption?: string;
  transcript?: string;
  delivery_status?: string;
  error_code?: string;
  error_message?: string;
  attachments?: Attachment[];
  metadata?: {
    documents?: { filename?: string; doc_id?: string }[];
    filename?: string;
    call_event?: string;
    voice_sent?: boolean;
  };
}

interface JobOption {
  slug: string;
  client_name: string;
}

function storedPin(): string {
  if (typeof window === 'undefined') return '';
  return sessionStorage.getItem(PIN_KEY) || '';
}

function founderHeaders(pin: string): HeadersInit {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (pin) headers['X-Founder-Pin'] = pin;
  return headers;
}

function formatWhen(value?: string): string {
  if (!value) return '';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  return sameDay
    ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function StatusTicks({ status, failed }: { status?: string; failed?: boolean }) {
  if (failed || status === 'failed') return <XCircle size={13} color="#f87171" />;
  if (status === 'read') return <CheckCheck size={13} color="#d4b84a" />;
  if (status === 'delivered') return <CheckCheck size={13} color="#9ca3af" />;
  if (status === 'sent') return <Check size={13} color="#9ca3af" />;
  return null;
}

async function fetchBlob(url: string, pin: string): Promise<Blob> {
  const res = await fetch(url, { headers: founderHeaders(pin), cache: 'no-store' });
  if (!res.ok) throw new Error(`Download failed (${res.status})`);
  return res.blob();
}

function AuthMedia({
  url,
  pin,
  kind,
  alt,
  onClick,
}: {
  url: string;
  pin: string;
  kind: 'image' | 'audio';
  alt?: string;
  onClick?: () => void;
}) {
  const [src, setSrc] = useState('');
  useEffect(() => {
    let revoked = '';
    fetchBlob(url, pin).then((blob) => {
      revoked = URL.createObjectURL(blob);
      setSrc(revoked);
    }).catch(() => setSrc(''));
    return () => { if (revoked) URL.revokeObjectURL(revoked); };
  }, [url, pin]);
  if (!src) return null;
  if (kind === 'audio') return <audio controls src={src} style={{ width: '100%', marginTop: 4 }} />;
  return (
    <button onClick={onClick} style={{ display: 'block', padding: 0, border: 'none', background: 'transparent', cursor: 'pointer' }}>
      <img src={src} alt={alt || ''} style={{ maxWidth: 220, maxHeight: 160, borderRadius: 8, display: 'block' }} />
    </button>
  );
}

function saveBlob(blob: Blob, filename: string) {
  const href = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = href;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(href);
}

function AttachmentBlock({
  att,
  pin,
  jobs,
  onRefile,
  onOpenImage,
}: {
  att: Attachment;
  pin: string;
  jobs: JobOption[];
  onRefile: (id: number, slug: string) => void;
  onOpenImage: (id: number, filename: string) => void;
}) {
  const [slug, setSlug] = useState(att.job_slug || '');
  const mediaUrl = `${API}/whatsapp/media/${att.id}`;
  const isImage = (att.media_type === 'image' || att.media_type === 'photo' || (att.mime_type || '').startsWith('image/'))
    && att.media_type !== 'sticker';
  const isAudio = att.media_type === 'voice' || att.media_type === 'audio' || (att.mime_type || '').startsWith('audio/');
  const isDoc = att.media_type === 'document' || (att.mime_type || '').includes('pdf');

  const download = async () => {
    const blob = await fetchBlob(mediaUrl, pin);
    saveBlob(blob, att.filename || 'attachment');
  };

  return (
    <div style={{ marginTop: 8, padding: 8, borderRadius: 8, background: '#18150f', border: '1px solid #3a3424' }}>
      {isImage && att.has_file && (
        <AuthMedia url={mediaUrl} pin={pin} kind="image" alt={att.filename} onClick={() => onOpenImage(att.id, att.filename)} />
      )}
      {isAudio && att.has_file && (
        <AuthMedia url={mediaUrl} pin={pin} kind="audio" />
      )}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', marginTop: 6, fontSize: 12, color: '#d4b84a' }}>
        <span>{att.filename}{att.doc_id ? ` · ${att.doc_id}` : ''}</span>
        {att.filing_status === 'inbox' && <span style={{ color: '#fbbf24' }}>inbox</span>}
        {att.job_slug && <span>filed · {att.job_slug}</span>}
        <button onClick={download} style={iconBtn} aria-label="Download attachment"><Download size={13} /> Save</button>
        {isDoc && (
          <button
            onClick={async () => {
              const blob = await fetchBlob(mediaUrl, pin);
              const href = URL.createObjectURL(blob);
              window.open(href, '_blank', 'noopener');
            }}
            style={iconBtn}
          >
            <FileText size={13} /> Open
          </button>
        )}
      </div>
      <div className="no-print" style={{ display: 'flex', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
        <select
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
          style={{ minHeight: 32, background: '#1c1914', color: '#f5f2ed', border: '1px solid #3a3424', borderRadius: 6 }}
        >
          <option value="">Move to job…</option>
          {jobs.map((j) => (
            <option key={j.slug} value={j.slug}>{j.client_name} ({j.slug})</option>
          ))}
        </select>
        <button
          disabled={!slug}
          onClick={() => slug && onRefile(att.id, slug)}
          style={{ ...iconBtn, opacity: slug ? 1 : 0.5 }}
        >
          <FolderInput size={13} /> File
        </button>
      </div>
    </div>
  );
}

const iconBtn: Record<string, string | number> = {
  background: 'transparent',
  border: '1px solid #3a3424',
  color: '#d4b84a',
  borderRadius: 6,
  minHeight: 32,
  padding: '0 8px',
  display: 'inline-flex',
  alignItems: 'center',
  gap: 4,
  cursor: 'pointer',
  fontSize: 12,
};

export default function WhatsAppChatsScreen() {
  const [pin, setPin] = useState(storedPin);
  const [pinDraft, setPinDraft] = useState('');
  const [needsPin, setNeedsPin] = useState(!storedPin());
  const [pinError, setPinError] = useState('');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [total, setTotal] = useState(0);
  const [listQuery, setListQuery] = useState('');
  const [threadQuery, setThreadQuery] = useState('');
  const [hits, setHits] = useState<ChatMessage[]>([]);
  const [loadingList, setLoadingList] = useState(false);
  const [loadingThread, setLoadingThread] = useState(false);
  const [narrow, setNarrow] = useState(false);
  const [error, setError] = useState('');
  const [jobs, setJobs] = useState<JobOption[]>([]);
  const [lightbox, setLightbox] = useState<{ id: number; filename: string; src: string } | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const check = () => setNarrow(window.innerWidth < 768);
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  const loadList = useCallback(async (founderPin: string) => {
    setLoadingList(true);
    setError('');
    try {
      const res = await fetch(`${API}/whatsapp/chats`, {
        headers: founderHeaders(founderPin),
        cache: 'no-store',
      });
      if (res.status === 403 || res.status === 503) {
        setNeedsPin(true);
        setPinError(res.status === 503 ? 'Founder PIN is not configured on this host.' : 'Founder PIN required.');
        return;
      }
      if (!res.ok) throw new Error(`Could not load chats (${res.status})`);
      const data = await res.json();
      setConversations(data.conversations || []);
      setNeedsPin(false);
      setPinError('');
      const jobsRes = await fetch(`${API}/whatsapp/jobs`, { headers: founderHeaders(founderPin), cache: 'no-store' });
      if (jobsRes.ok) {
        const jobData = await jobsRes.json();
        setJobs(jobData.jobs || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load chats');
    } finally {
      setLoadingList(false);
    }
  }, []);

  const loadThread = useCallback(async (waId: string, founderPin: string, q = '') => {
    setLoadingThread(true);
    try {
      const params = new URLSearchParams({ limit: '100', offset: '0' });
      if (q.trim()) params.set('q', q.trim());
      const res = await fetch(`${API}/whatsapp/chats/${encodeURIComponent(waId)}/messages?${params}`, {
        headers: founderHeaders(founderPin),
        cache: 'no-store',
      });
      if (!res.ok) throw new Error(`Could not load messages (${res.status})`);
      const data = await res.json();
      setMessages(data.messages || []);
      setTotal(data.total || 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load messages');
    } finally {
      setLoadingThread(false);
    }
  }, []);

  useEffect(() => {
    if (pin && !needsPin) loadList(pin);
  }, [pin, needsPin, loadList]);

  useEffect(() => {
    if (pin && selectedId) loadThread(selectedId, pin, threadQuery);
  }, [pin, selectedId, threadQuery, loadThread]);

  useEffect(() => {
    if (!pin || listQuery.trim().length < 2) {
      setHits([]);
      return;
    }
    const handle = setTimeout(async () => {
      try {
        const res = await fetch(
          `${API}/whatsapp/chats/search?q=${encodeURIComponent(listQuery.trim())}&limit=30`,
          { headers: founderHeaders(pin), cache: 'no-store' },
        );
        if (!res.ok) return;
        const data = await res.json();
        setHits(data.messages || []);
      } catch {
        setHits([]);
      }
    }, 250);
    return () => clearTimeout(handle);
  }, [listQuery, pin]);

  const filteredConversations = useMemo(() => {
    const q = listQuery.trim().toLowerCase();
    if (!q) return conversations;
    return conversations.filter((c) =>
      `${c.display_label} ${c.wa_id} ${c.last_message}`.toLowerCase().includes(q),
    );
  }, [conversations, listQuery]);

  const selected = conversations.find((c) => c.wa_id === selectedId) || null;
  const showList = !narrow || !selectedId;
  const showThread = !narrow || !!selectedId;

  const unlock = () => {
    const next = pinDraft.trim();
    if (!next) {
      setPinError('Enter the founder PIN.');
      return;
    }
    sessionStorage.setItem(PIN_KEY, next);
    setPin(next);
    setNeedsPin(false);
    setPinError('');
    loadList(next);
  };

  const refile = async (attachmentId: number, jobSlug: string) => {
    const res = await fetch(`${API}/whatsapp/attachments/${attachmentId}/refile`, {
      method: 'POST',
      headers: founderHeaders(pin),
      body: JSON.stringify({ job_slug: jobSlug }),
    });
    if (!res.ok) {
      setError('Could not move that file to the job folder.');
      return;
    }
    if (selectedId) loadThread(selectedId, pin, threadQuery);
    loadList(pin);
  };

  const copyChat = async () => {
    if (!selectedId) return;
    const res = await fetch(`${API}/whatsapp/chats/${encodeURIComponent(selectedId)}/copy`, {
      headers: founderHeaders(pin),
      cache: 'no-store',
    });
    if (!res.ok) return;
    const data = await res.json();
    await navigator.clipboard.writeText(data.text || '');
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const exportPdf = async () => {
    if (!selectedId) return;
    const blob = await fetchBlob(`${API}/whatsapp/chats/${encodeURIComponent(selectedId)}/export?format=pdf`, pin);
    saveBlob(blob, `whatsapp-${selected?.display_label || selectedId}.pdf`);
  };

  return (
    <div
      className="wa-chats"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        minHeight: 0,
        background: '#11100e',
        color: '#f5f2ed',
      }}
    >
      <style>{`
        @media print {
          .no-print, aside, .wa-chats header button, .wa-chats header input { display: none !important; }
          .wa-chats { background: #fff !important; color: #111 !important; height: auto !important; }
          .wa-thread { overflow: visible !important; }
        }
      `}</style>
      <header
        className="no-print"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '12px 16px',
          borderBottom: '1px solid #2a261c',
          background: '#16140f',
        }}
      >
        <MessageCircle size={18} color="#d4b84a" />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 11, letterSpacing: 1.2, textTransform: 'uppercase', color: '#d4b84a', fontWeight: 700 }}>
            Channels
          </div>
          <h1 style={{ fontSize: 18, fontWeight: 800, margin: 0 }}>WhatsApp Chats</h1>
        </div>
        <button onClick={() => pin && loadList(pin)} style={iconBtn} aria-label="Refresh chats">
          <RefreshCw size={14} />
        </button>
      </header>

      {needsPin && (
        <div className="no-print" style={{ padding: 16, borderBottom: '1px solid #2a261c' }}>
          <div style={{ fontSize: 13, color: '#c4b99a', marginBottom: 8 }}>
            Founder PIN is required to read this edition&apos;s WhatsApp log.
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <input
              type="password"
              value={pinDraft}
              onChange={(e) => setPinDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') unlock(); }}
              placeholder="Founder PIN"
              autoComplete="off"
              style={{
                flex: '1 1 160px',
                minHeight: 40,
                borderRadius: 8,
                border: '1px solid #3a3424',
                background: '#1c1914',
                color: '#f5f2ed',
                padding: '0 12px',
              }}
            />
            <button
              onClick={unlock}
              style={{ minHeight: 40, padding: '0 16px', borderRadius: 8, border: 'none', background: '#b8960c', color: '#11100e', fontWeight: 700, cursor: 'pointer' }}
            >
              Unlock
            </button>
          </div>
          {pinError && <div style={{ color: '#f87171', fontSize: 12, marginTop: 8 }}>{pinError}</div>}
        </div>
      )}

      {error && (
        <div className="no-print" style={{ padding: '8px 16px', color: '#f87171', fontSize: 13 }}>{error}</div>
      )}

      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        {showList && (
          <aside
            className="no-print"
            style={{
              width: narrow ? '100%' : 320,
              borderRight: narrow ? 'none' : '1px solid #2a261c',
              display: 'flex',
              flexDirection: 'column',
              minHeight: 0,
              background: '#14120e',
            }}
          >
            <div style={{ padding: 12, borderBottom: '1px solid #2a261c' }}>
              <div style={{ position: 'relative' }}>
                <Search size={14} color="#d4b84a" style={{ position: 'absolute', left: 10, top: 12 }} />
                <input
                  value={listQuery}
                  onChange={(e) => setListQuery(e.target.value)}
                  placeholder="Search chats or text"
                  style={{
                    width: '100%',
                    minHeight: 40,
                    padding: '0 12px 0 32px',
                    borderRadius: 8,
                    border: '1px solid #3a3424',
                    background: '#1c1914',
                    color: '#f5f2ed',
                  }}
                />
              </div>
            </div>
            <div style={{ overflowY: 'auto', flex: 1 }}>
              {loadingList && <div style={{ padding: 16, color: '#9ca3af', fontSize: 13 }}>Loading…</div>}
              {!loadingList && filteredConversations.length === 0 && (
                <div style={{ padding: 16, color: '#9ca3af', fontSize: 13 }}>
                  No WhatsApp conversations in this edition yet.
                </div>
              )}
              {filteredConversations.map((c) => {
                const failed = c.last_status === 'failed';
                const active = c.wa_id === selectedId;
                return (
                  <button
                    key={c.wa_id}
                    onClick={() => { setSelectedId(c.wa_id); setThreadQuery(''); }}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      padding: '12px 14px',
                      border: 'none',
                      borderBottom: '1px solid #241f16',
                      background: active ? '#2a2410' : 'transparent',
                      color: '#f5f2ed',
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                      <strong style={{ color: '#d4b84a', fontSize: 14 }}>{c.display_label}</strong>
                      <span style={{ fontSize: 11, color: '#8b8373' }}>{formatWhen(c.last_timestamp)}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                      <StatusTicks status={c.last_status} failed={failed} />
                      <span style={{ fontSize: 12, color: failed ? '#f87171' : '#c4b99a', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {c.last_direction === 'outbound' ? 'Max: ' : ''}{c.last_message}
                      </span>
                    </div>
                    {c.active_job?.job_slug && (
                      <div style={{ fontSize: 10, color: '#d4b84a', marginTop: 4 }}>Job {c.active_job.job_slug}</div>
                    )}
                    {failed && (
                      <div style={{ fontSize: 11, color: '#f87171', marginTop: 4 }}>
                        Delivery failed{c.last_error_code ? ` · ${c.last_error_code}` : ''}
                      </div>
                    )}
                  </button>
                );
              })}
              {hits.length > 0 && (
                <div style={{ padding: '10px 14px', borderTop: '1px solid #2a261c' }}>
                  <div style={{ fontSize: 10, letterSpacing: 1, textTransform: 'uppercase', color: '#d4b84a', marginBottom: 8 }}>
                    Text matches
                  </div>
                  {hits.map((hit) => (
                    <button
                      key={`${hit.id}-${hit.wa_id}`}
                      onClick={() => { setSelectedId(hit.wa_id); setThreadQuery(listQuery); }}
                      style={{ width: '100%', textAlign: 'left', background: 'transparent', border: 'none', color: '#c4b99a', padding: '8px 0', cursor: 'pointer', fontSize: 12 }}
                    >
                      <div style={{ color: '#d4b84a' }}>{hit.display_label}</div>
                      <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {hit.body || hit.caption || `[${hit.message_type}]`}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </aside>
        )}

        {showThread && (
          <section style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <div
              style={{
                padding: '12px 16px',
                borderBottom: '1px solid #2a261c',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                background: '#16140f',
                flexWrap: 'wrap',
              }}
            >
              {narrow && (
                <button onClick={() => setSelectedId(null)} className="no-print" style={{ background: 'transparent', border: 'none', color: '#d4b84a', cursor: 'pointer' }} aria-label="Back to chats">
                  <ArrowLeft size={18} />
                </button>
              )}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 700 }}>{selected?.display_label || 'Select a conversation'}</div>
                {selected && (
                  <div style={{ fontSize: 11, color: '#8b8373' }}>
                    {selected.wa_id} · {total} messages · {selected.active_job?.job_slug ? `job ${selected.active_job.job_slug}` : 'view only'}
                  </div>
                )}
              </div>
              {selected && (
                <>
                  <input
                    className="no-print"
                    value={threadQuery}
                    onChange={(e) => setThreadQuery(e.target.value)}
                    placeholder="Find in thread"
                    style={{ minHeight: 36, width: narrow ? 110 : 160, borderRadius: 8, border: '1px solid #3a3424', background: '#1c1914', color: '#f5f2ed', padding: '0 10px' }}
                  />
                  <button className="no-print" onClick={copyChat} style={iconBtn} aria-label="Copy conversation">
                    <Copy size={13} /> {copied ? 'Copied' : 'Copy'}
                  </button>
                  <button className="no-print" onClick={exportPdf} style={iconBtn} aria-label="Export chat as PDF">
                    <FileText size={13} /> PDF
                  </button>
                  <button className="no-print" onClick={() => window.print()} style={iconBtn} aria-label="Print conversation">
                    <Printer size={13} /> Print
                  </button>
                </>
              )}
            </div>

            <div className="wa-thread" style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
              {!selected && (
                <div style={{ color: '#8b8373', fontSize: 14, padding: 24 }}>
                  Choose a sender on the left. This page does not send or share messages.
                </div>
              )}
              {loadingThread && selected && (
                <div style={{ color: '#9ca3af', fontSize: 13 }}>Loading thread…</div>
              )}
              {selected && messages.map((m) => {
                const outbound = m.direction === 'outbound';
                const failed = m.delivery_status === 'failed';
                const docs = m.metadata?.documents || [];
                return (
                  <div
                    key={m.id}
                    style={{ display: 'flex', justifyContent: outbound ? 'flex-end' : 'flex-start', marginBottom: 12 }}
                  >
                    <div
                      style={{
                        maxWidth: '86%',
                        padding: '10px 12px',
                        borderRadius: outbound ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
                        background: outbound ? '#2a2410' : '#1c1914',
                        border: failed ? '1px solid #7f1d1d' : '1px solid #3a3424',
                      }}
                    >
                      <div style={{ fontSize: 10, color: '#d4b84a', fontWeight: 700, marginBottom: 4 }}>
                        {outbound ? 'MAX' : m.display_label} · {m.message_type}
                      </div>
                      <div style={{ fontSize: 14, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                        {m.body || m.caption || `[${m.message_type}]`}
                      </div>
                      {m.transcript && (
                        <div style={{ fontSize: 12, color: '#c4b99a', marginTop: 6 }}>
                          Transcript: {m.transcript}
                        </div>
                      )}
                      {(m.attachments || []).map((att) => (
                        <AttachmentBlock
                          key={att.id}
                          att={att}
                          pin={pin}
                          jobs={jobs}
                          onRefile={refile}
                          onOpenImage={async (id, filename) => {
                            try {
                              const blob = await fetchBlob(`${API}/whatsapp/media/${id}`, pin);
                              setLightbox({ id, filename, src: URL.createObjectURL(blob) });
                            } catch {
                              setError('Could not open that photo.');
                            }
                          }}
                        />
                      ))}
                      {docs.length > 0 && !(m.attachments || []).length && (
                        <div style={{ marginTop: 8, fontSize: 12, color: '#d4b84a' }}>
                          {docs.map((d, i) => (
                            <div key={`${d.filename}-${i}`}>
                              Document {d.filename || 'file'}{d.doc_id ? ` · ${d.doc_id}` : ''}
                            </div>
                          ))}
                        </div>
                      )}
                      {failed && (
                        <div style={{ marginTop: 8, padding: 8, borderRadius: 8, background: '#3f1212', color: '#fecaca', fontSize: 12, display: 'flex', gap: 6 }}>
                          <AlertTriangle size={13} />
                          <span>
                            Delivery failed
                            {m.error_code ? ` · Meta ${m.error_code}` : ''}
                            {m.error_message ? ` — ${m.error_message}` : ''}
                          </span>
                        </div>
                      )}
                      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 6, marginTop: 6 }}>
                        <span style={{ fontSize: 10, color: '#8b8373' }}>{formatWhen(m.timestamp)}</span>
                        {outbound && <StatusTicks status={m.delivery_status} failed={failed} />}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}
      </div>

      {lightbox && (
        <div
          className="no-print"
          onClick={() => { URL.revokeObjectURL(lightbox.src); setLightbox(null); }}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)', zIndex: 80, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}
        >
          <button onClick={() => { URL.revokeObjectURL(lightbox.src); setLightbox(null); }} style={{ position: 'absolute', top: 16, right: 16, ...iconBtn }} aria-label="Close image">
            <X size={16} />
          </button>
          <img
            src={lightbox.src}
            alt={lightbox.filename}
            style={{ maxWidth: '96%', maxHeight: '90%', borderRadius: 8 }}
          />
        </div>
      )}
    </div>
  );
}
