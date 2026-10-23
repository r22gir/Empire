'use client';

import { useCallback, useEffect, useRef, useState, type CSSProperties } from 'react';
import { LifeBuoy, Mic, Paperclip, Square, X } from 'lucide-react';
import { Message } from '../../lib/types';
import { filenameForMime, recorderFormat, sttLanguage } from '../../lib/voiceCapture';
import {
  HELP_FILE_ACCEPT,
  HELP_MAX_FILES,
  HelpTicket,
  attachmentUrl,
  createHelpTicket,
  currentHelpScreen,
  familyHelpLabels,
  fetchOwnTickets,
  lastClientError,
  formatHelpBytes,
  retryTranscript,
  validateHelpFile,
} from '../../lib/familyHelp';

type Props = {
  locale: string;
  messages: Message[];
  onReply?: (ticketId: string, body: string, author: string) => void;
};

export default function AskMaxHelp({ locale, messages, onReply }: Props) {
  const t = familyHelpLabels(locale);
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [voice, setVoice] = useState<Blob | null>(null);
  const [voiceName, setVoiceName] = useState('recording.webm');
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tickets, setTickets] = useState<HelpTicket[]>([]);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const seenReplies = useRef<Set<string>>(new Set());
  const primed = useRef(false);

  const refresh = useCallback(async () => {
    const rows = await fetchOwnTickets();
    setTickets(rows);
    for (const ticket of rows) {
      for (const reply of ticket.replies || []) {
        if (!primed.current) {
          seenReplies.current.add(reply.id);
          continue;
        }
        if (seenReplies.current.has(reply.id)) continue;
        seenReplies.current.add(reply.id);
        onReply?.(ticket.id, reply.body, reply.author);
      }
    }
    primed.current = true;
  }, [onReply]);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 20000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const stopRec = useCallback(() => {
    recorderRef.current?.stop();
    recorderRef.current = null;
    setRecording(false);
  }, []);

  const startRec = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const fmt = recorderFormat(navigator.userAgent, (mime) => MediaRecorder.isTypeSupported(mime));
      const rec = new MediaRecorder(stream, fmt.mimeType ? { mimeType: fmt.mimeType } : undefined);
      chunksRef.current = [];
      rec.ondataavailable = (ev) => { if (ev.data.size) chunksRef.current.push(ev.data); };
      rec.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: rec.mimeType || fmt.mimeType });
        setVoice(blob);
        setVoiceName(filenameForMime(blob.type || fmt.mimeType));
      };
      recorderRef.current = rec;
      rec.start();
      setRecording(true);
    } catch {
      setError(locale.startsWith('es') ? 'No pude usar el micrófono' : 'Microphone unavailable');
    }
  }, [locale]);

  const submit = async () => {
    if (busy) return;
    setBusy(true);
    setError(null);
    const history = messages.slice(-8).map((m) => ({ role: m.role, content: m.content }));
    const result = await createHelpTicket({
      message: text,
      history,
      files,
      voice,
      voiceName,
      language: sttLanguage(locale),
      currentScreen: currentHelpScreen('chat'),
      lastError: lastClientError(),
    });
    setBusy(false);
    if (!result.ok) {
      setError(typeof result.detail === 'string' ? result.detail : t.sending);
      return;
    }
    setText('');
    setFiles([]);
    setVoice(null);
    await refresh();
  };

  return (
    <>
      <button
        type="button"
        data-testid="pedir-ayuda"
        onClick={() => setOpen(true)}
        title={t.ask}
        aria-label={t.ask}
        style={{
          background: open ? '#d4a017' : 'none',
          border: open ? 'none' : '1px solid var(--border)',
          borderRadius: 6,
          color: open ? '#000' : 'var(--text)',
          cursor: 'pointer',
          padding: '6px 8px',
          minHeight: 44,
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          fontSize: 12,
          fontWeight: 700,
        }}
      >
        <LifeBuoy size={14} />
        {t.ask}
      </button>
      {open && (
        <div
          role="dialog"
          aria-label={t.title}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.45)',
            zIndex: 80,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 16,
          }}
        >
          <div style={{
            width: 'min(560px, 100%)',
            maxHeight: '90vh',
            overflow: 'auto',
            background: 'var(--card-bg, #111)',
            color: 'var(--text)',
            border: '1px solid var(--border)',
            borderRadius: 12,
            padding: 16,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <strong>{t.title}</strong>
              <button type="button" onClick={() => setOpen(false)} aria-label={t.close} style={{ background: 'none', border: 0, color: 'inherit', cursor: 'pointer' }}>
                <X size={16} />
              </button>
            </div>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 0 }}>{t.hint}</p>
            <p style={{ fontSize: 12, color: '#d4a017' }}>{t.attachmentWarning}</p>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={t.message}
              rows={4}
              style={{ width: '100%', resize: 'vertical', padding: 10, borderRadius: 8, border: '1px solid var(--border)', background: 'transparent', color: 'inherit' }}
            />
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', margin: '10px 0' }}>
              <button type="button" onClick={recording ? stopRec : startRec} style={chipStyle}>
                {recording ? <Square size={14} /> : <Mic size={14} />}
                {recording ? t.stopVoice : t.voice}
              </button>
              <label style={chipStyle}>
                <Paperclip size={14} /> {t.attach}
                <input
                  type="file"
                  multiple
                  hidden
                  accept={HELP_FILE_ACCEPT}
                  onChange={(e) => {
                    const picked = Array.from(e.target.files || []);
                    const kept: File[] = [];
                    const errors: string[] = [];
                    for (const file of picked) {
                      const check = validateHelpFile(file);
                      if (check.ok) kept.push(file);
                      else errors.push(`${file.name}: ${check.reason}`);
                    }
                    setFiles((prev) => [...prev, ...kept].slice(0, HELP_MAX_FILES));
                    setError(errors.length ? errors.join(' ') : null);
                    e.target.value = '';
                  }}
                />
              </label>
              <button type="button" onClick={submit} disabled={busy} style={{ ...chipStyle, background: '#d4a017', color: '#000', border: 'none' }}>
                {busy ? t.sending : t.send}
              </button>
            </div>
            {voice && <div style={{ fontSize: 12 }}>{t.transcript}: {voiceName} ({Math.round(voice.size / 1024)} KB)</div>}
            {files.length > 0 && (
              <div style={{ fontSize: 12 }}>
                {files.map((f) => `${f.name} (${formatHelpBytes(f.size)})`).join(', ')}
              </div>
            )}
            {error && <div style={{ color: '#f87171', fontSize: 13 }}>{error}</div>}
            <h4 style={{ margin: '16px 0 8px' }}>{t.replies}</h4>
            {tickets.length === 0 && <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>{t.empty}</p>}
            {tickets.map((ticket) => (
              <div key={ticket.id} data-testid="pedir-ayuda-thread" style={{ border: '1px solid var(--border)', borderRadius: 8, padding: 10, marginBottom: 8 }}>
                <div style={{ fontSize: 12, opacity: 0.7 }}>{ticket.id} · {ticket.status}</div>
                <div>{ticket.message}</div>
                {ticket.transcript ? <div style={{ fontSize: 13 }}><em>{t.transcript}:</em> {ticket.transcript}</div> : null}
                {ticket.transcript_pending ? (
                  <div style={{ fontSize: 13, marginTop: 6 }}>
                    <em>{t.transcriptPending}</em>
                    <button
                      type="button"
                      onClick={async () => {
                        await retryTranscript(ticket.id, false, locale);
                        await refresh();
                      }}
                      style={{ marginLeft: 8 }}
                    >
                      {t.retryTranscript}
                    </button>
                  </div>
                ) : null}
                {(ticket.attachments || []).map((att) => (
                  att.kind === 'voice'
                    ? <audio key={att.id} controls src={attachmentUrl(ticket.id, att.id, false)} style={{ width: '100%', marginTop: 6 }} />
                    : <a key={att.id} href={attachmentUrl(ticket.id, att.id, false)} target="_blank" rel="noreferrer" style={{ display: 'block', fontSize: 12 }}>{att.filename}</a>
                ))}
                {(ticket.replies || []).map((reply) => (
                  <div key={reply.id} style={{ marginTop: 8, padding: 8, background: 'rgba(212,160,23,0.12)', borderRadius: 6 }}>
                    <strong>{reply.author}</strong>
                    <div>{reply.body}</div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

const chipStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  padding: '8px 10px',
  borderRadius: 8,
  border: '1px solid var(--border)',
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 600,
};
