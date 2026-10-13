'use client';

import OrganizerPage from '../components/screens/OrganizerPage';

export default function OrganizerRoute() {
  return (
    <div style={{ minHeight: '100vh', background: '#f5f3ef' }}>
      <nav style={{
        display: 'flex', gap: 14, alignItems: 'center', padding: '14px 20px',
        background: '#fff', borderBottom: '1px solid #e5e0d8',
      }}>
        <a href="/" style={{ color: '#1a1a2e', textDecoration: 'none', fontSize: 13, fontWeight: 800 }}>Command Center</a>
        <span style={{ color: '#ccc' }}>/</span>
        <span style={{ color: '#16a34a', fontSize: 13, fontWeight: 800 }}>Organizer</span>
        <span style={{ marginLeft: 'auto', fontSize: 11, color: '#888' }}>Sprint M · drafts only · owner sends</span>
      </nav>
      <OrganizerPage />
    </div>
  );
}
