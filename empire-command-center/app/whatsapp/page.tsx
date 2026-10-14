'use client';

import { useEffect, useState } from 'react';
import { API } from '../lib/api';
import { useEdition } from '../lib/edition';
import { renderWhatsAppSetupPage } from '../lib/whatsappSetup';

export default function MaxineWhatsAppSetupPage() {
  const edition = useEdition();
  const [last4, setLast4] = useState<string[]>([]);

  useEffect(() => {
    fetch(`${API}/whatsapp/setup`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (Array.isArray(data?.owner_last4)) setLast4(data.owner_last4);
      })
      .catch(() => {});
  }, []);

  const html = renderWhatsAppSetupPage(edition, { ownerLast4: last4 });
  return (
    <div data-maxine-page>
      <nav aria-label="Maxine" style={{ padding: '12px 16px', fontFamily: 'Nunito, sans-serif' }}>
        <a href="/" style={{ color: '#D4A030', fontWeight: 700, marginRight: 16 }}>Centro de mando</a>
        <a href="/ayuda" style={{ color: '#D4A030', fontWeight: 700 }}>Ayuda</a>
      </nav>
      <div dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  );
}
