'use client';

import { useEdition } from '../../lib/edition';
import { renderWhatsAppSetupPage } from '../../lib/whatsappSetup';

export default function AyudaWhatsApp() {
  const html = renderWhatsAppSetupPage(useEdition());
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}
