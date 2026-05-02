'use client';

import { useEffect, useState } from 'react';

const V10_BACKEND = 'http://localhost:8010';

interface V10Status {
  status: string;
  provider_policy: {
    primary: string;
    minimax_configured: boolean;
    xai_disabled: boolean;
    xai_disabled_reason: string | null;
    ollama_disabled: boolean;
    ollama_disabled_reason: string | null;
    max_primary_provider_env: string | null;
  };
  current_commit: { hash: string; message: string } | null;
}

export default function V10Page() {
  const [health, setHealth] = useState<{ status: string } | null>(null);
  const [maxStatus, setMaxStatus] = useState<V10Status | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const [healthRes, statusRes] = await Promise.all([
          fetch(`${V10_BACKEND}/health`),
          fetch(`${V10_BACKEND}/api/v1/max/status`),
        ]);
        if (healthRes.ok) setHealth(await healthRes.json());
        if (statusRes.ok) setMaxStatus(await statusRes.json());
      } catch (e: any) {
        setError(e.message || 'Failed to connect to v10 backend');
      } finally {
        setLoading(false);
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  const provider = maxStatus?.provider_policy;
  const commit = maxStatus?.current_commit;

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 100%)',
      color: '#e0e0e0',
      fontFamily: 'monospace',
      padding: '2rem',
    }}>
      {/* Header */}
      <div style={{ borderBottom: '2px solid #ff6b35', paddingBottom: '1rem', marginBottom: '2rem' }}>
        <h1 style={{ color: '#ff6b35', fontSize: '2rem', margin: 0 }}>
          EmpireBox v10.0 Test Lane
        </h1>
        <p style={{ color: '#888', margin: '0.5rem 0 0 0' }}>
          This is the v10 test lane. It is NOT the live/canonical runtime.
        </p>
      </div>

      {/* Backend URL Banner */}
      <div style={{
        background: '#2a2a3e',
        border: '1px solid #ff6b35',
        borderRadius: '8px',
        padding: '1rem',
        marginBottom: '2rem',
        display: 'flex',
        gap: '2rem',
        alignItems: 'center',
        flexWrap: 'wrap',
      }}>
        <div>
          <span style={{ color: '#888' }}>Backend URL: </span>
          <a href={V10_BACKEND} style={{ color: '#ff6b35' }}>{V10_BACKEND}</a>
        </div>
        <div>
          <span style={{ color: '#888' }}>Branch: </span>
          <code style={{ color: '#4ecdc4' }}>feature/v10.0-test-lane</code>
        </div>
        <div>
          <span style={{ color: '#888' }}>Commit: </span>
          <code style={{ color: '#95a95a' }}>{commit?.hash || 'unknown'}</code>
        </div>
      </div>

      {loading && <p style={{ color: '#888' }}>Loading v10 backend status...</p>}

      {error && (
        <div style={{
          background: '#3e1a1a',
          border: '1px solid #ff4444',
          borderRadius: '8px',
          padding: '1rem',
          marginBottom: '2rem',
          color: '#ff6666',
        }}>
          ⚠ v10 backend is offline or unreachable: {error}
        </div>
      )}

      {/* Status Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '1.5rem',
        marginBottom: '2rem',
      }}>
        {/* Backend Health */}
        <div style={{
          background: '#1e1e32',
          border: '1px solid #333',
          borderRadius: '8px',
          padding: '1.5rem',
        }}>
          <h2 style={{ color: '#4ecdc4', marginTop: 0 }}>Backend Health</h2>
          <div style={{ fontSize: '2rem', color: health?.status === 'ok' ? '#22c55e' : '#ff6b35' }}>
            {health?.status === 'ok' ? '✓ Healthy' : '✗ Offline'}
          </div>
          <p style={{ color: '#666', marginBottom: 0 }}>
            Endpoint: <a href={`${V10_BACKEND}/health`} style={{ color: '#4ecdc4' }}>{V10_BACKEND}/health</a>
          </p>
        </div>

        {/* MAX Provider Policy */}
        <div style={{
          background: '#1e1e32',
          border: '1px solid #333',
          borderRadius: '8px',
          padding: '1.5rem',
        }}>
          <h2 style={{ color: '#4ecdc4', marginTop: 0 }}>MAX Provider Policy</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <div>
              <span style={{ color: '#888' }}>Primary: </span>
              <span style={{ color: '#22c55e', fontWeight: 'bold' }}>{provider?.primary || 'unknown'}</span>
            </div>
            <div>
              <span style={{ color: '#888' }}>MiniMax configured: </span>
              <span style={{ color: provider?.minimax_configured ? '#22c55e' : '#ff4444' }}>
                {provider?.minimax_configured ? '✓' : '✗'}
              </span>
            </div>
            <div>
              <span style={{ color: '#888' }}>xAI: </span>
              <span style={{ color: provider?.xai_disabled ? '#ff6b35' : '#22c55e' }}>
                {provider?.xai_disabled ? `disabled (${provider.xai_disabled_reason})` : 'enabled'}
              </span>
            </div>
            <div>
              <span style={{ color: '#888' }}>Ollama: </span>
              <span style={{ color: provider?.ollama_disabled ? '#ff6b35' : '#22c55e' }}>
                {provider?.ollama_disabled ? `disabled (${provider.ollama_disabled_reason})` : 'enabled'}
              </span>
            </div>
          </div>
        </div>

        {/* Runtime / Commit */}
        <div style={{
          background: '#1e1e32',
          border: '1px solid #333',
          borderRadius: '8px',
          padding: '1.5rem',
        }}>
          <h2 style={{ color: '#4ecdc4', marginTop: 0 }}>Runtime / Commit</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <div>
              <span style={{ color: '#888' }}>Hash: </span>
              <code style={{ color: '#95a95a' }}>{commit?.hash || 'unknown'}</code>
            </div>
            <div>
              <span style={{ color: '#888' }}>Message: </span>
              <span style={{ color: '#e0e0e0', fontSize: '0.85rem' }}>{commit?.message || 'unknown'}</span>
            </div>
            <div>
              <span style={{ color: '#888' }}>API env: </span>
              <code style={{ color: '#4ecdc4' }}>{provider?.max_primary_provider_env || 'unset'}</code>
            </div>
          </div>
        </div>

        {/* Links */}
        <div style={{
          background: '#1e1e32',
          border: '1px solid #333',
          borderRadius: '8px',
          padding: '1.5rem',
        }}>
          <h2 style={{ color: '#4ecdc4', marginTop: 0 }}>Links</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <a href={`${V10_BACKEND}/health`} target="_blank" style={{ color: '#4ecdc4' }}>
              → Health
            </a>
            <a href={`${V10_BACKEND}/api/v1/max/status`} target="_blank" style={{ color: '#4ecdc4' }}>
              → MAX Status
            </a>
            <a href={`${V10_BACKEND}/api/v1/max/chat`} target="_blank" style={{ color: '#4ecdc4' }}>
              → MAX Chat API
            </a>
            <a href="http://localhost:3005" target="_blank" style={{ color: '#ff6b35' }}>
              → Live Frontend (port 3005)
            </a>
          </div>
        </div>
      </div>

      {/* Warning Banner */}
      <div style={{
        background: '#2a1a0a',
        border: '1px solid #ff6b35',
        borderRadius: '8px',
        padding: '1rem',
        textAlign: 'center',
        color: '#ff6b35',
        fontWeight: 'bold',
      }}>
        ⚠ This is the v10 test lane. Data and state here may be reset at any time.
      </div>
    </div>
  );
}
