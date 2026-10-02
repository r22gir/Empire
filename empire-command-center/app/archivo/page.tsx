'use client';

import { useEffect, useState } from 'react';
import { API } from '../lib/api';
import ProjectPhotos from '../components/voice/ProjectPhotos';

export default function ArchivoPage() {
  const [userId, setUserId] = useState('');
  const [status, setStatus] = useState('');
  const [enabled, setEnabled] = useState<boolean | null>(null);

  useEffect(() => {
    fetch(`${API}/files/drive/status`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!data) return;
        setEnabled(Boolean(data.enabled));
        if (!data.enabled && data.reason) setStatus(data.reason);
      })
      .catch(() => {});
  }, []);

  async function connect() {
    if (enabled === false) return;
    const res = await fetch(`${API}/files/drive/connect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, redirect_uri: window.location.origin + '/archivo' }),
    });
    const data = await res.json();
    setStatus(data.reason || (data.url ? 'Abre la cuenta de Google de este usuario.' : 'Sin conexión'));
    if (data.url) window.location.href = data.url;
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
      <button type="button" onClick={connect} disabled={enabled === false} style={{ marginTop: 8 }}>
        {enabled === false ? 'Drive apagado hasta tener credenciales' : 'Conectar mi Google Drive'}
      </button>
      <h2>Fotos de obra o de proyecto</h2>
      <ProjectPhotos />
      {status ? <p>{status}</p> : null}
    </main>
  );
}
