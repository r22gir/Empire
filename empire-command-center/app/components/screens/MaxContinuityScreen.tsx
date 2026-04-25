'use client';

import ContinuityPanel from '../ContinuityPanel';

export default function MaxContinuityScreen() {
  return (
    <div style={{ padding: '20px 24px', maxWidth: 1100, width: '100%', margin: '0 auto' }}>
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 10, fontWeight: 900, letterSpacing: 1, textTransform: 'uppercase', color: 'var(--muted)' }}>
          Infrastructure / Utilities
        </div>
        <h1 style={{ margin: '4px 0 2px', fontSize: 22, fontWeight: 800, color: 'var(--text)' }}>
          MAX Continuity
        </h1>
        <div style={{ fontSize: 13, color: 'var(--muted)' }}>
          Runtime truth, handoff state, OpenClaw gate health, and recent MAX evaluation signals.
        </div>
      </div>

      <ContinuityPanel mode="full" />
    </div>
  );
}
