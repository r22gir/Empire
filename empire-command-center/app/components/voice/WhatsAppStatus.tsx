'use client';

import { useEffect, useState } from 'react';
import { API } from '../../lib/api';
import { useEdition } from '../../lib/edition';

type Status = {
  enabled?: boolean;
  status?: string;
  reason_es?: string;
  reason_en?: string;
  edition?: string;
  phone_number_id_last4?: string;
  owner_count?: number;
};

export default function WhatsAppStatus() {
  const edition = useEdition();
  const [status, setStatus] = useState<Status | null>(null);

  useEffect(() => {
    fetch(`${API}/whatsapp/status`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setStatus(data))
      .catch(() => setStatus(null));
  }, []);

  const spanish = edition === 'amp' || edition === 'maxine';
  const reason = status
    ? (spanish ? status.reason_es : status.reason_en)
    : (spanish ? 'No pude leer el estado de WhatsApp.' : 'WhatsApp status is unavailable.');
  const on = status?.enabled === true;
  return (
    <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14, maxWidth: 420 }}>
      <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 0.4, color: on ? '#16a34a' : '#888' }}>
        WHATSAPP · {on ? (spanish ? 'LISTO' : 'READY') : (spanish ? 'APAGADO' : 'OFF')}
      </div>
      <p style={{ fontSize: 13, color: '#444', margin: '6px 0 0' }}>{reason}</p>
      {status?.phone_number_id_last4 ? (
        <p style={{ fontSize: 12, color: '#888', margin: '6px 0 0' }}>
          {status.edition} · ···{status.phone_number_id_last4} · {status.owner_count || 0}
        </p>
      ) : null}
      {spanish ? (
        <p style={{ margin: '10px 0 0' }}>
          <a href="/amp/whatsapp" style={{ color: '#b8960c', fontWeight: 700, fontSize: 13 }}>Configurar WhatsApp</a>
          {' · '}
          <a href="/amp/whatsapp/chats" style={{ color: '#b8960c', fontWeight: 700, fontSize: 13 }}>Ver chats</a>
        </p>
      ) : null}
    </div>
  );
}
