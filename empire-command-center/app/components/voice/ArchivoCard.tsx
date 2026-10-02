'use client';

import { useEdition } from '../../lib/edition';

export default function ArchivoCard() {
  const edition = useEdition();
  const folder = edition === 'maxine' ? 'Maxine' : 'Max-e';
  return (
    <a href="/archivo" style={{ display: 'block', background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14, textDecoration: 'none', color: '#1a1a1a', maxWidth: 420 }}>
      <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 0.4, color: '#b8960c' }}>ARCHIVO</div>
      <p style={{ fontSize: 13, color: '#444', margin: '6px 0 0' }}>
        La copia de trabajo queda en esta máquina. Cada persona conecta su propio Google Drive.
        La carpeta es {folder}/, ordenada por empresa, proyecto, cliente y fecha.
      </p>
    </a>
  );
}
