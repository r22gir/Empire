'use client';

import { useState } from 'react';
import { API } from '../../lib/api';

export type VoiceDraftView = {
  session_id?: string;
  status?: string;
  label?: string;
  transcript?: string;
  question?: string;
  missing?: string[];
  options?: { kind?: string; choices?: { id: string; label: string; summary?: string }[] } | null;
  draft?: { id: string; status: string; sent?: boolean; preview_path?: string } | null;
  sent?: boolean;
  error?: string;
};

export default function VoiceDraftPanel({
  view,
  onChange,
}: {
  view: VoiceDraftView | null;
  onChange: (next: VoiceDraftView) => void;
}) {
  const [note, setNote] = useState('');
  const [confirmSend, setConfirmSend] = useState(false);
  const [notice, setNotice] = useState('');
  if (!view) return null;

  async function post(path: string, body: object) {
    const res = await fetch(`${API}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'No se pudo guardar');
    return data;
  }

  return (
    <div style={{ margin: '0 12px 8px', background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 12 }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: '#b8960c' }}>Borrador · {view.label || 'Documento'} · DRAFT</div>
      {view.transcript ? (
        <p style={{ fontSize: 13, color: '#333', whiteSpace: 'pre-wrap' }}>{view.transcript}</p>
      ) : null}
      {view.question ? <p style={{ fontSize: 13, color: '#1a1a1a' }}>{view.question}</p> : null}
      {(view.missing || []).length > 0 ? (
        <p style={{ fontSize: 12, color: '#666' }}>Falta: {view.missing!.join(', ')}</p>
      ) : null}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {(view.options?.choices || []).slice(0, 3).map((choice) => (
          <button
            key={choice.id}
            type="button"
            onClick={async () => {
              const next = await post('/voice/documents/ingest', {
                transcript: '',
                session_id: view.session_id,
                channel: 'web',
                choice_id: choice.id,
              });
              onChange(next);
            }}
            style={{ border: '1px solid #e5e2dc', background: '#faf9f7', borderRadius: 8, padding: '6px 10px', cursor: 'pointer', fontSize: 12 }}
          >
            {choice.label}
          </button>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <input
          value={note}
          onChange={(event) => setNote(event.target.value)}
          placeholder="Agrega un dato o di listo"
          style={{ flex: 1, border: '1px solid #e5e2dc', borderRadius: 8, padding: '8px 10px', fontSize: 13 }}
        />
        <button
          type="button"
          onClick={async () => {
            const next = await post('/voice/documents/ingest', {
              transcript: note,
              session_id: view.session_id,
              channel: 'web',
            });
            setNote('');
            onChange(next);
          }}
          style={{ border: 'none', background: '#1a1a1a', color: '#fff', borderRadius: 8, padding: '8px 12px', cursor: 'pointer', fontSize: 12 }}
        >
          Agregar
        </button>
      </div>
      {view.draft ? (
        <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <a href={`${API}/voice/documents/drafts/${view.draft.id}/preview.pdf`} target="_blank" rel="noreferrer" style={{ fontSize: 12, color: '#b8960c' }}>
            Descargar PDF borrador
          </a>
          <a href={`${API}/voice/documents/drafts/${view.draft.id}/preview`} target="_blank" rel="noreferrer" style={{ fontSize: 12, color: '#b8960c' }}>
            Vista previa
          </a>
          <button
            type="button"
            onClick={async () => {
              await post(`/voice/documents/drafts/${view.draft!.id}/approve`, {});
              setNotice('Borrador aprobado. No se envió.');
              onChange({ ...view, draft: { ...view.draft!, status: 'approved', sent: false } });
            }}
            style={{ border: '1px solid #b8960c', background: '#fff', borderRadius: 8, padding: '6px 10px', cursor: 'pointer', fontSize: 12 }}
          >
            Aprobar borrador
          </button>
          <label style={{ fontSize: 12, color: '#444' }}>
            <input type="checkbox" checked={confirmSend} onChange={(event) => setConfirmSend(event.target.checked)} /> Confirmo el envío
          </label>
          <button
            type="button"
            onClick={async () => {
              const result = await post(`/voice/documents/drafts/${view.draft!.id}/send`, { confirm: confirmSend, channel: 'email' });
              setNotice(result.reason || 'No se envió.');
            }}
            style={{ border: '1px solid #e5e2dc', background: '#faf9f7', borderRadius: 8, padding: '6px 10px', cursor: 'pointer', fontSize: 12 }}
          >
            Enviar
          </button>
        </div>
      ) : null}
      {notice ? <p style={{ fontSize: 12, color: '#166534' }}>{notice}</p> : null}
      <p style={{ fontSize: 11, color: '#888', marginBottom: 0 }}>DRAFT. sent={String(view.sent === true)}. Nada sale sin tu confirmación.</p>
    </div>
  );
}
