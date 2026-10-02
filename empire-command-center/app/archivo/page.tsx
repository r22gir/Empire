'use client';

import { useState } from 'react';
import { API } from '../lib/api';

export default function ArchivoPage() {
  const [userId, setUserId] = useState('');
  const [status, setStatus] = useState('');
  const [project, setProject] = useState('');
  const [lot, setLot] = useState('');
  const [stage, setStage] = useState('');
  const [timeline, setTimeline] = useState<string>('');

  async function connect() {
    const res = await fetch(`${API}/files/drive/connect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, redirect_uri: window.location.origin + '/archivo' }),
    });
    const data = await res.json();
    setStatus(data.reason || (data.url ? 'Abre la cuenta de Google de este usuario.' : 'Sin conexión'));
    if (data.url) window.location.href = data.url;
  }

  async function upload(file: File) {
    const body = new FormData();
    body.append('file', file);
    body.append('project', project);
    body.append('lot', lot);
    body.append('stage', stage);
    body.append('source', 'upload');
    const res = await fetch(`${API}/photos/intake`, { method: 'POST', body });
    const data = await res.json();
    setTimeline(data.id ? `Foto guardada en la copia de trabajo: ${data.id}` : (data.detail || 'No se guardó'));
  }

  async function loadTimeline() {
    const res = await fetch(`${API}/photos/timeline?project=${encodeURIComponent(project)}`);
    const data = await res.json();
    const lines = (data.items || []).map((item: { created_at: string; stage: string; lot: string; filename: string }) =>
      `${item.created_at} · lote ${item.lot || '—'} · ${item.stage || 'sin etapa'} · ${item.filename}`
    );
    setTimeline(lines.join('\n') || 'Sin fotos en este proyecto');
  }

  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: 24, fontFamily: 'Inter, sans-serif', color: '#1a1a1a' }}>
      <p style={{ color: '#b8960c', fontWeight: 700, fontSize: 12 }}>MAX-E · MAXINE</p>
      <h1>Archivo</h1>
      <p>
        La copia de trabajo se queda en esta máquina. El archivo de Drive es la cuenta de Google de cada usuario, nunca una cuenta compartida.
        Cada noche se prepara una exportación de la base y los documentos. Si esa persona conectó su Drive, el destino es la carpeta Max-e/ o Maxine/, ordenada por empresa, proyecto, cliente y fecha.
      </p>
      <label style={{ display: 'block', marginTop: 12 }}>
        Correo de este usuario
        <input value={userId} onChange={(event) => setUserId(event.target.value)} style={{ display: 'block', width: '100%', marginTop: 4, padding: 8 }} />
      </label>
      <button type="button" onClick={connect} style={{ marginTop: 8 }}>Conectar mi Google Drive</button>
      <h2>Fotos de obra o de proyecto</h2>
      <p>Sube una foto, mándala por el chat, o elige elementos en Google Photos. Solo entran las que la persona selecciona.</p>
      <div style={{ display: 'grid', gap: 8, gridTemplateColumns: '1fr 1fr 1fr' }}>
        <input placeholder="Proyecto" value={project} onChange={(event) => setProject(event.target.value)} />
        <input placeholder="Lote" value={lot} onChange={(event) => setLot(event.target.value)} />
        <input placeholder="Etapa" value={stage} onChange={(event) => setStage(event.target.value)} />
      </div>
      <input type="file" accept="image/*" style={{ marginTop: 8 }} onChange={(event) => { const file = event.target.files?.[0]; if (file) upload(file); }} />
      <button type="button" onClick={loadTimeline} style={{ marginLeft: 8 }}>Ver línea de tiempo</button>
      {status ? <p>{status}</p> : null}
      {timeline ? <pre style={{ whiteSpace: 'pre-wrap' }}>{timeline}</pre> : null}
    </main>
  );
}
