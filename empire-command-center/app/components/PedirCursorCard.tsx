'use client';

import { isFamilyEdition } from '../lib/edition';
import { PEDIR_CURSOR_NOTE } from '../lib/pedirCursorCopy';

export default function PedirCursorCard() {
  const family = isFamilyEdition();
  if (!family) return null;
  return (
    <section
      aria-label="Pedir a Cursor"
      style={{
        background: '#fff',
        border: '1px solid #e5e2dc',
        borderRadius: 12,
        padding: '12px 14px',
        minWidth: 220,
        maxWidth: 360,
      }}
    >
      <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: 0.6, color: '#9a7b2f' }}>PEDIR A CURSOR</div>
      <p style={{ margin: '6px 0 0', fontSize: 12, color: '#5C5650' }}>{PEDIR_CURSOR_NOTE}</p>
      <a
        href="/pedir-cursor"
        style={{ display: 'inline-block', marginTop: 8, fontSize: 12, color: '#9a7b2f', fontWeight: 700 }}
      >
        Pedir a Cursor
      </a>
    </section>
  );
}
