'use client';

import { useState } from 'react';
import { API } from '../../lib/api';

export default function ProjectPhotos({ initialProject = '' }: { initialProject?: string }) {
  const [project, setProject] = useState(initialProject);
  const [lot, setLot] = useState('');
  const [stage, setStage] = useState('');
  const [timeline, setTimeline] = useState('');

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
    <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 }}>
      <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 0.4, color: '#b8960c' }}>FOTOS DEL PROYECTO</div>
      <p style={{ fontSize: 13, color: '#444' }}>
        Sube una foto o mándala por el chat. Google Photos solo entra si la persona elige los elementos en el selector.
        Cada foto queda en el proyecto, el lote y la etapa.
      </p>
      <div style={{ display: 'grid', gap: 8, gridTemplateColumns: '1fr 1fr 1fr' }}>
        <input placeholder="Proyecto" value={project} onChange={(event) => setProject(event.target.value)} />
        <input placeholder="Lote" value={lot} onChange={(event) => setLot(event.target.value)} />
        <input placeholder="Etapa" value={stage} onChange={(event) => setStage(event.target.value)} />
      </div>
      <input type="file" accept="image/*" style={{ marginTop: 8 }} onChange={(event) => { const file = event.target.files?.[0]; if (file && project) upload(file); }} />
      <button type="button" onClick={loadTimeline} style={{ marginLeft: 8 }}>Ver línea de tiempo</button>
      {timeline ? <pre style={{ whiteSpace: 'pre-wrap' }}>{timeline}</pre> : null}
    </div>
  );
}
