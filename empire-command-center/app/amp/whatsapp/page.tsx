'use client';

import { useEffect, useState } from 'react';
import AmpNav from '../../components/amp/AmpNav';
import WhatsAppSecureKeys from '../../components/voice/WhatsAppSecureKeys';
import { API } from '../../lib/api';
import { useEdition } from '../../lib/edition';
import { FAMILY_LOGIN_PATH, familyAuthFailedStatus } from '../../lib/familyAuth';
import { renderWhatsAppSetupPage } from '../../lib/whatsappSetup';

export default function AmpWhatsAppSetupPage() {
  const edition = useEdition();
  const [last4, setLast4] = useState<string[]>([]);

  useEffect(() => {
    fetch(`${API}/whatsapp/setup`, { credentials: 'include', cache: 'no-store' })
      .then((res) => {
        if (familyAuthFailedStatus(res.status)) {
          window.location.replace(FAMILY_LOGIN_PATH);
          return null;
        }
        return res.ok ? res.json() : null;
      })
      .then((data) => {
        if (Array.isArray(data?.owner_last4)) setLast4(data.owner_last4);
      })
      .catch(() => {});
  }, []);

  const html = renderWhatsAppSetupPage(edition, { ownerLast4: last4 });
  return (
    <div data-amp-page>
      <AmpNav />
      <div dangerouslySetInnerHTML={{ __html: html }} />
      <WhatsAppSecureKeys />
    </div>
  );
}
