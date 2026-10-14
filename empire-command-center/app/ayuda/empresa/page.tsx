'use client';

import { useEdition } from '../../lib/edition';
import { renderEmpresaGuidePage } from '../../lib/empresaGuide';

export default function AyudaEmpresa() {
  const html = renderEmpresaGuidePage(useEdition());
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}
