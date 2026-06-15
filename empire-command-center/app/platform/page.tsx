'use client';
import PlatformPage from '../components/screens/PlatformPage';

export default function Page() {
  return (
    <div
      data-platform-page
      style={{
        background: '#f5f2ed',
        minHeight: '100dvh',
        paddingBottom: 'calc(env(safe-area-inset-bottom) + 24px)',
      }}
    >
      <PlatformPage />
    </div>
  );
}
