'use client';

import Link from 'next/link';

export default function VoiceHelpCard() {
  return (
    <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 16, maxWidth: 520 }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>Cómo usar la voz</div>
      <p style={{ fontSize: 13, color: '#444', margin: '8px 0 0', lineHeight: 1.45 }}>
        Mantén el micrófono, habla con naturalidad, revisa la transcripción, elige una opción y aprueba el borrador. Nada se envía solo.
      </p>
      <Link href="/ayuda/voz" style={{ display: 'inline-block', marginTop: 10, fontSize: 12, fontWeight: 700, color: '#b8960c' }}>
        Ver los pasos
      </Link>
    </div>
  );
}
