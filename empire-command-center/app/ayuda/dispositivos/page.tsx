'use client';

import { useEdition } from '../../lib/edition';
import { renderDeviceAccessPage } from '../../lib/deviceAccess';

export default function ComoConectarte() {
  const html = renderDeviceAccessPage(useEdition());
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}
